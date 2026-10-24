"""Agentes determinísticos (sem LLM) que leem o envelope de um gate e roteiam o pipeline.

`EnvelopeGateAgent` é um BaseAgent que:
  1. lê o relatório gravado em `state[report_key]`;
  2. extrai o envelope JSON e infere o status (aprovado | bloqueado | indefinido);
  3. grava `state[status_key]`, `state[status_key + "_envelope"]` e, se configurado,
     incrementa um contador de rodadas;
  4. quando dentro de um LoopAgent, encerra o loop (escalate) ao aprovar ou ao
     esgotar as rodadas; quando o gate falha em modo estrito, marca o pipeline
     como bloqueado para que os agentes a jusante sejam pulados.

`SecaoSplitAgent` é um BaseAgent que copia seções (delimitadas por headings) de um
relatório para chaves próprias do estado — usado depois de agentes que emitem mais de
um documento numa única resposta (D0: spec consolidada + relatório de lacunas; D9:
spec com bloco 14). Lê o envelope e grava um status **informativo**; nunca bloqueia.

`BnccCheckAgent` é um BaseAgent que confere o bloco 11 da spec contra a lista oficial da
BNCC Computação (`tools/bncc.py`): código existe, é do ano da missão, e há letramento
digital. Não conforme → bloqueia o pipeline (design e dev pulados) quando `estrito`.

`RastroCheckAgent` generaliza o padrão para as verificações de `tools/rastro.py`
(`lacunas` · `manifesto` · `telemetria`): status `aprovado | amarelo | bloqueado`; bloqueado
trava o pipeline quando `estrito`; amarelo (só pendência de plataforma) segue e o PRD sai 🟡.
"""

from __future__ import annotations

import json
import re
from typing import Any, AsyncGenerator, Dict, List, Optional

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.utils.context_utils import Aclosing
from google.genai import types
from pydantic import Field
from typing_extensions import override

from tools.bncc import relatorio_markdown, validar_spec
from tools.contrato_produto import relatorio_markdown as relatorio_contrato_produto
from tools.contrato_produto import validar_one_pager
from tools.rastro import (
    relatorio_lacunas,
    relatorio_manifesto,
    relatorio_prd,
    relatorio_telemetria,
    validar_manifesto,
    validar_prd,
    validar_telemetria,
    varrer_lacunas,
)

from .callbacks import (
    KEY_AGENTES_DEGRADADOS,
    KEY_DEGRADACOES,
    KEY_HERANCA,
    KEY_MODO_CORRECAO,
    KEY_PIPELINE_BLOQUEADO,
    KEY_PIPELINE_MOTIVO,
    STATUS_APROVADO,
    STATUS_BLOQUEADO,
    extrair_envelope,
    extrair_slug,
    status_registrado,
    inferir_status,
    texto_de_heranca,
)


#: Quantos agentes já foram reexecutados por retrabalho nesta execução.
KEY_REEXECUCOES = "reexecucoes"


def orcamento_disponivel(state, quantos: int) -> bool:
    """Cabe mais uma rodada de retrabalho no orçamento da execução?

    Cada loop tem seu teto, mas os tetos somam: design 2 × banca 2 × handoff 2 já são
    muitas reexecuções numa missão ruim. O orçamento global é o freio que impede a soma
    de virar uma conta imprevisível.
    """
    from config import get_settings

    gastos = int(state.get(KEY_REEXECUCOES, 0) or 0)
    return gastos + quantos <= get_settings().orcamento_reexecucoes


def limpar_degradacao(state, delta: Dict[str, Any], gate: str) -> None:
    """Apaga a reprovação de um gate que passou a aprovar.

    Antes dos loops de correção isto não fazia falta: reprovou, parou. Agora um gate pode
    reprovar na rodada 1 e aprovar na 2, e a marca da primeira não pode sobreviver — senão
    a missão consertada sai com veredito de reprovada e tudo a jusante vira `[PROVISÓRIO]`
    sem motivo.
    """
    anteriores = list(state.get(KEY_DEGRADACOES) or [])
    restantes = [d for d in anteriores if (d or {}).get("gate") != gate]
    if len(restantes) == len(anteriores):
        return
    delta[KEY_DEGRADACOES] = restantes
    delta[KEY_HERANCA] = texto_de_heranca(restantes)
    if not restantes:
        delta[KEY_PIPELINE_BLOQUEADO] = False
        delta[KEY_PIPELINE_MOTIVO] = ""
        # Sem reprovação viva, ninguém construiu sobre base reprovada: na geração de 23/09 o PRD
        # reprovou no kpis-check da rodada 1, aprovou na 2, e o dossiê seguia listando o redator
        # e os dois gates como "saiu provisório" numa execução sem nenhum impedimento.
        delta[KEY_AGENTES_DEGRADADOS] = []


def registrar_degradacao(state, delta: Dict[str, Any], gate: str, motivo: str) -> None:
    """Anota a reprovação e reescreve o aviso de herança para os agentes a jusante.

    Não interrompe nada: a esteira segue até o fim justamente para que o diagnóstico final
    tenha todos os insumos. `KEY_PIPELINE_BLOQUEADO` continua existindo, mas só como
    veredito da execução — não como ordem de parada.
    """
    # Um gate tem UMA reprovação vigente: a rodada nova substitui a anterior. Acumulando, a exp01ef1b
    # (07/10/2026) saiu com "telemetria reprovado (4 lacunas)" de motivo, quando a rodada final tinha 2.
    anteriores = [d for d in state.get(KEY_DEGRADACOES) or [] if d.get("gate") != gate]
    anteriores.append({"gate": gate, "motivo": motivo})
    delta[KEY_DEGRADACOES] = anteriores
    delta[KEY_HERANCA] = texto_de_heranca(anteriores)
    delta[KEY_PIPELINE_BLOQUEADO] = True
    # O motivo é o do primeiro gate que reprovou, na rodada mais recente dele; a lista fica em KEY_DEGRADACOES.
    atual = str(state.get(KEY_PIPELINE_MOTIVO) or "")
    if not atual or atual.startswith(gate):
        delta[KEY_PIPELINE_MOTIVO] = motivo


class EnvelopeGateAgent(BaseAgent):
    """Lê o veredito de um relatório e decide se o pipeline segue, repete ou para."""

    report_key: str
    status_key: str
    rotulo: str = "Gate"
    round_key: Optional[str] = None
    max_rounds: int = 1
    escalate_on_approve: bool = False
    block_pipeline_on_fail: bool = True
    #: Os documentos que o gate avalia (chaves do estado). Com eles, a citação de cada achado bloqueante é conferida
    #: (`tools/citacoes.py`): a que não existe rebaixa o achado, e se todos os bloqueios caem, o veredito vira 🟡.
    documentos: List[str] = Field(default_factory=list)

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        relatorio = str(state.get(self.report_key, "") or "")
        envelope = extrair_envelope(relatorio)
        status = inferir_status(relatorio, envelope)
        nota_citacao = ""
        if self.documentos and envelope and isinstance(envelope.get("achados"), list) and status == STATUS_BLOQUEADO:
            from tools import citacoes

            bloqueios = [a for a in envelope["achados"] if isinstance(a, dict) and citacoes.bloqueante(a)]
            rebaixados = citacoes.conferir(envelope["achados"], citacoes.texto_dos_documentos(state, self.documentos))
            if rebaixados:
                nota_citacao = (f"\n\n---\n> ⚖️ **Citação conferida em código:** {len(rebaixados)} de {len(bloqueios)} "
                                "bloqueio(s) citavam trecho que não existe no documento avaliado e foram rebaixados a "
                                "atenção (`citacao_nao_confere`).")
                if len(rebaixados) == len(bloqueios):
                    # nenhum bloqueio comprovado sobrou: o 🔴 era do juiz, não do documento
                    envelope = {**envelope, "status": "amarelo", "veredito_original": envelope.get("status")}
                    status = STATUS_APROVADO
                relatorio += nota_citacao + "\n\n```json\n" + json.dumps(envelope, ensure_ascii=False) + "\n```\n"
        # Relatório vazio, truncado ou sem veredito legível é BLOQUEIO, sempre. O QA de design
        # e a banca de dev optavam pelo contrário (`treat_indefinido_as_blocked=False`) e, com
        # isso, uma resposta que não chegou valia aprovação: é o pior erro possível num gate,
        # porque não deixa rastro no dossiê. O motivo é registrado à parte para separar
        # "reprovou" de "não respondeu" — são defeitos diferentes, com donos diferentes.
        truncado = status not in (STATUS_APROVADO, STATUS_BLOQUEADO)
        if truncado:
            status = STATUS_BLOQUEADO

        rodada = int(state.get(self.round_key, 0) or 0) + 1 if self.round_key else 1
        # O ROTEAMENTO usa `status` (binário: a esteira segue ou não). O DOSSIÊ usa o veredito
        # como ele foi dado: gravar "aprovado" onde o juiz escreveu 🟡 apagava a ressalva, e em
        # 14 execuções nenhum gate de LLM apareceu amarelo embora os relatórios estivessem
        # cheios de amarelo. O que o time lia era um verde que o juiz não deu.
        registrado = STATUS_BLOQUEADO if truncado else status_registrado(relatorio, envelope)
        delta = {self.status_key: registrado, f"{self.status_key}_envelope": envelope or {}}
        if nota_citacao:
            delta[self.report_key] = relatorio
        if self.round_key:
            delta[self.round_key] = rodada

        esgotou = rodada >= self.max_rounds
        escalate = False
        if status == STATUS_APROVADO:
            msg = f"✅ {self.rotulo}: aprovado" + (f" na rodada {rodada}." if self.round_key else ".")
            limpar_degradacao(state, delta, self.rotulo)
            escalate = self.escalate_on_approve
        else:
            bloqueia_agora = self.block_pipeline_on_fail and (esgotou or not self.round_key)
            if self.round_key and not esgotou:
                msg = (
                    f"🔁 {self.rotulo}: bloqueado na rodada {rodada}/{self.max_rounds} — "
                    f"o revisor aplicará as correções e o gate será reexecutado."
                )
            elif bloqueia_agora:
                msg = (
                    f"⛔ {self.rotulo}: reprovado"
                    + (f" após {rodada} rodada(s)" if self.round_key else "")
                    + ". A esteira segue até o fim: o que derivar daqui sai marcado "
                    "`[PROVISÓRIO]` e o diagnóstico final registra o que travou e de quem é."
                )
                motivo = (f"{self.rotulo}: relatório vazio ou sem veredito legível"
                          if truncado else f"{self.rotulo} reprovado")
                registrar_degradacao(state, delta, self.rotulo, motivo)
            else:
                msg = (
                    f"⚠️ {self.rotulo}: reprovado"
                    + (f" após {rodada} rodada(s)" if self.round_key else "")
                    + ". Modo estrito desligado — segue como ressalva e entra no PRD."
                )
            # `escalate` serve para sair de um LoopAgent, nunca para abortar a esteira:
            # num SequentialAgent ele pularia todo o resto da etapa.
            escalate = bool(self.round_key) and esgotou

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=msg)]),
            actions=EventActions(state_delta=delta, escalate=escalate or None),
        )


def extrair_secao(texto: str, inicio: str, fim: Optional[str] = None) -> Optional[str]:
    """Devolve o trecho entre o heading `inicio` (regex, multiline) e o heading `fim` (ou o fim do texto)."""
    m = re.search(inicio, texto, re.MULTILINE)
    if not m:
        return None
    start = m.end()
    end = len(texto)
    if fim:
        m2 = re.search(fim, texto[start:], re.MULTILINE)
        if m2:
            end = start + m2.start()
    return texto[start:end].strip()


_RE_CERCA_ANTES_DO_TITULO = re.compile(r"^```[\w-]*[ \t]*\n(?=\s*# )", re.MULTILINE)
_RE_RABO_DE_SEPARADOR = re.compile(r"(?:\n[ \t]*(?:-{3,}|\*{3,})?[ \t]*)+\Z")


def documento_sem_moldura(secao: str) -> str:
    """O documento sem a frase de abertura do agente e sem a cerca ```markdown que o envolve.

    O D0 escrevia «Abaixo segue a especificação técnica consolidada…» e a spec dentro de uma cerca; o split gravava as
    duas coisas em `spec_missao`. O D9 escrevia outra frase de abertura, a preservação acusava a do D0 como linha perdida,
    o retrabalho devolvia a frase e o ciclo recomeçava — a exp06ef1b (09/10/2026) terminou o design 🔴 por isso. Só age
    quando a cerca abre antes do título `# ` e nada antes dela é título: a frase é do agente, não do documento.
    """
    t = (secao or "").strip()
    m = _RE_CERCA_ANTES_DO_TITULO.search(t)
    if not m or m.start() > 1500 or re.search(r"^#{1,6}\s", t[:m.start()], re.MULTILINE):
        return secao
    from pipeline.artifacts import desembrulhar_cerca

    miolo = _RE_RABO_DE_SEPARADOR.sub("", t[m.start():]).strip()
    limpo = desembrulhar_cerca(miolo)
    return limpo.strip() if limpo != miolo else secao


def _bloco(documento: str, titulo: str) -> str:
    """O bloco cujo título casa `titulo` (regex de linha) — dele até o próximo `## ` ou o fim; "" sem ele."""
    m = re.search(titulo, documento or "", re.MULTILINE)
    if not m:
        return ""
    fim = re.search(r"^## ", documento[m.end():], re.MULTILINE)
    return documento[m.start():m.end() + fim.start()] if fim else documento[m.start():]


def _cita_texto_do_po(linha: str, state: Dict[str, Any]) -> bool:
    """A linha traz um texto que um pedido do PO pôs entre aspas para trocar (sem os relatos de gate que ele colou)."""
    from tools.fidelidade import sem_relatos_de_gate

    pedidos = " ".join(sem_relatos_de_gate(str(p.get("texto") or "")) for p in state.get("pedidos_do_po") or []
                       if isinstance(p, dict))
    citados = {c.strip().lower() for c in re.findall(r"[“\"«]([^”\"»\n]{4,80})[”\"»]", pedidos)}
    alvo = (linha or "").lower()
    return any(c in alvo for c in citados)


def _sem_bloco(documento: str, titulo: str) -> str:
    """O documento sem o bloco cujo título casa `titulo` (regex de linha) — dele até o próximo `## ` ou o fim."""
    m = re.search(titulo, documento or "", re.MULTILINE)
    if not m:
        return documento
    fim = re.search(r"^## ", documento[m.end():], re.MULTILINE)
    antes = documento[:m.start()].rstrip()
    depois = documento[m.end() + fim.start():].lstrip() if fim else ""
    if antes and depois:
        return antes + "\n\n" + depois + "\n"
    elif antes:
        return antes + "\n"
    elif depois:
        return depois + "\n"
    return "\n"


def _secoes(documento: str) -> Dict[str, str]:
    """`{chave: corpo}` das seções `## ` do documento — do título até o próximo `## ` ou o fim —, mais o preâmbulo
    (chave `""`, o que vem antes da primeira). A chave é o número do bloco (`## 6. Tetos` → `"6"`) ou o título sem
    acento e em minúsculas (`## Glossário canônico` → `"glossario canonico"`): o glossário é texto do Gate 0 como os
    blocos 0–12, e a troca do rótulo «Publicar no Álbum» na exp02ef1b (23/10/2026) foi feita justamente nele."""
    import unicodedata

    secoes: Dict[str, str] = {}
    marcas = list(re.finditer(r"^##\s+(.*)$", documento or "", re.MULTILINE))
    if marcas and documento[:marcas[0].start()].strip():
        secoes[""] = documento[:marcas[0].start()]
    elif not marcas and (documento or "").strip():
        secoes[""] = documento
    for i, m in enumerate(marcas):
        fim = marcas[i + 1].start() if i + 1 < len(marcas) else len(documento)
        numero = re.match(r"\**\s*(\d{1,2})\b", m.group(1))
        chave = numero.group(1) if numero else " ".join(re.sub(r"[^a-z0-9]+", " ", "".join(
            c for c in unicodedata.normalize("NFD", m.group(1).lower()) if unicodedata.category(c) != "Mn")).split())
        secoes.setdefault(chave, documento[m.start():fim])
    return secoes


def _linhas_normalizadas(corpo: str) -> List[str]:
    """As linhas com conteúdo, sem espaço sobrando e sem régua (`---`): cópia por modelo que só mexe em espaço ou põe um
    separador antes do bloco 13 não é mudança (era o único «diff» do glossário em 53e011b6 e 76d9af6e)."""
    return [" ".join(l.split()) for l in (corpo or "").splitlines()
            if l.strip() and not re.fullmatch(r"\s*(?:-{3,}|\*{3,}|_{3,})\s*", l)]


#: A marca que o D0 punha na linha do `[ABERTO …]` que fechou: ` — Resolvido em [D0-9]`.
_RE_MARCA_RESOLVIDO = re.compile(r"\s*[—–-]?\s*\(?resolvid[oa]s?\s+(?:em|no|na|pel[oa])\s*\[?\s*D0-0*(\d+)\s*\]?\)?\.?",
                                 re.IGNORECASE)


def _recolher_marcas_resolvido(aceita: str, nova: str) -> tuple:
    """`(nova_sem_marcas, mapa)`: as marcas «Resolvido em [D0-n]» que a nova acrescentou a linhas da aceita saem da
    linha e viram linhas do mapa célula → D0 (`(marcador, n)`), que mora no bloco 13.

    A spec é montada em código desde 23/10/2026 (plano «Produto dono do contrato», PR 2): o texto do Gate 0 não muda
    mais, nem pela marca. O D0 que ainda a escrever não muda o Gate 0 — a marca vai para o mapa, que o rastro lê
    (`tools/rastro.mapa_celula_d0`)."""
    from tools.rastro import marcadores_de_lacuna

    def celula(limpa: str) -> List[str]:
        # o marcador que o rastro lê; sem ele, o [PARÂMETRO]/[PROPOSTA] ou o começo da linha, para quem lê o mapa
        achados = marcadores_de_lacuna(limpa) or re.findall(r"\[(?:PAR[ÂA]METRO|PROPOSTA)[^\]\n]{0,300}\]", limpa)
        return achados or [" ".join(limpa.strip(" |").replace("|", "·").split())[:120]]

    da_aceita = set(_linhas_normalizadas(aceita))
    mapa: List[tuple] = []
    saida: List[str] = []
    for linha in (nova or "").splitlines():
        m = _RE_MARCA_RESOLVIDO.search(linha)
        if m:
            limpa = (linha[:m.start()] + linha[m.end():]).rstrip()
            if " ".join(limpa.split()) in da_aceita:
                for marcador in celula(limpa):
                    if (marcador, int(m.group(1))) not in mapa:
                        mapa.append((marcador, int(m.group(1))))
                linha = limpa
        saida.append(linha)
    return "\n".join(saida), mapa


def tabela_do_mapa(mapa: List[tuple]) -> str:
    """O mapa célula → D0 em Markdown, no formato que o rastro lê."""
    return ("### Mapa célula → D0\n\n| Marcador da spec do Gate 0 | Decisão |\n|---|---|\n"
            + "".join(f"| `{marcador.replace('|', '·').replace('`', '')}` | [D0-{n}] |\n" for marcador, n in mapa))


def _inserir_bloco(base: str, bloco: str, titulo: str, proprio: Optional[str]) -> str:
    """`base` com `bloco` no lugar do bloco `titulo`; sem ele, antes do primeiro bloco de número maior, ou no fim.

    O bloco 13 vai antes do 14: no retrabalho só o D0 roda, e a spec do D9 já tem o bloco 14 (exp03ef1b, 23/10/2026)."""
    atual = _bloco(base, titulo)
    if atual.strip():
        return base.replace(atual.rstrip(), bloco.strip(), 1)
    if proprio and proprio.isdigit():
        for m in re.finditer(r"^##\s*\**\s*(\d{1,2})\b.*$", base, re.MULTILINE):
            if int(m.group(1)) > int(proprio):
                return base[:m.start()].rstrip() + "\n\n" + bloco.strip() + "\n\n" + base[m.start():].lstrip()
    return base.rstrip() + "\n\n" + bloco.strip() + "\n"


def bloco0_pode_mudar(envelope: Optional[Dict[str, Any]]) -> bool:
    """O D9 só muda o bloco 0 quando o ambiente é `novo`/`existente` e o Gate 0 aceitou a `[RS-AMB]`."""
    env = envelope or {}
    respec = env.get("respec") if isinstance(env.get("respec"), dict) else {}
    return (str(env.get("status") or "").lower() in ("novo", "existente")
            and str(respec.get("id") or "").upper() == "RS-AMB"
            and str(respec.get("status") or "").lower() == "aceito")


#: Blocos da spec que não são texto do Gate 0: o 13 é do D0 e o 14 é do D9.
BLOCOS_DO_DESIGN = ("13", "14")


def montar_sobre_aceita(aceita: str, nova: str, titulo: str, bloco0_aceito: bool = False,
                        avisos: Optional[List[Dict[str, Any]]] = None, autor: str = "D9",
                        agente: str = "ambiente-simulado", estrito: bool = False,
                        estado: Optional[Dict[str, Any]] = None) -> str:
    """A versão aceita com o bloco `titulo` tirado da nova; o resto da nova é descartado.

    O D9 acrescenta o bloco 14 e recopiava, por modelo, os 60 KB dos blocos 0–13 do D0. Na exp06ef1b (09/10/2026)
    o D0 traduziu «refresh token» para «chave de renovação» e o D9, partindo da própria versão anterior, manteve o
    inglês: a preservação acusou, com razão, e o design terminou 🔴 duas vezes. Cópia literal é trabalho de código.
    Sem o bloco na nova, devolve a nova como veio — a preservação confere a cópia como antes.

    Desde 23/10/2026 o D0 também passa por aqui (bloco 13): a spec é a do Gate 0 + 13 + 14, montada em código. Antes, o
    D0 reemitia a spec inteira, a preservação acusava linhas-perdidas, a base preservada era a do Gate 0, e o D9 montava
    por cima dela — o bloco 13 sumiu em 60cfa7f4 e 4fd72a9a, e o PRD da 4fd72a9a citava D0-1 e D0-6 de uma spec sem
    nenhum (plano «Produto dono do contrato», PR 2). As marcas «Resolvido em [D0-n]» que a nova acrescentar ao texto do
    Gate 0 viram o mapa célula → D0 no fim do bloco 13 (`_recolher_marcas_resolvido`).

    Única exceção: o bloco 0 da nova entra quando `bloco0_aceito` (`bloco0_pode_mudar`: ambiente novo ou existente
    com a `[RS-AMB]` aceita). Qualquer outra diferença nas seções copiadas é descartada e vai para `avisos`, com o que
    mudou — antes era descartada em silêncio (plano padrão ouro, 2.5):
    - no texto do Gate 0 (preâmbulo, blocos 0–12, glossário), como `[ABERTO — dono: PO]`: a mudança é de produto, e só o
      PO a decide. Até a rota de produto do PR 5, aparece no cartão do parecer de design (`decisao_humana`) e só
      bloqueia com ESTEIRA_ESTRITA (`estrito`);
    - no bloco do outro autor do design (13 ou 14), como 🟡 «alterou fora do bloco».
    """
    m = re.search(titulo, nova or "", re.MULTILINE)
    if not m:
        return nova
    fim = re.search(r"^## ", nova[m.end():], re.MULTILINE)
    bloco = nova[m.start():m.end() + fim.start()] if fim else nova[m.start():]
    proprio = (re.search(r"(\d{1,2})", titulo) or [None, None])[1]

    mapa: List[tuple] = []
    if proprio == "13":
        nova, mapa = _recolher_marcas_resolvido(aceita, nova)
        if mapa:
            bloco = bloco.rstrip() + "\n\n" + tabela_do_mapa(mapa)
    base = aceita
    dos_aceitos, dos_novos = _secoes(aceita), _secoes(nova)
    for chave, corpo_aceito in dos_aceitos.items():
        corpo_novo = dos_novos.get(chave)
        if chave == proprio or corpo_novo is None or not corpo_novo.strip():
            continue
        antes, depois = _linhas_normalizadas(corpo_aceito), _linhas_normalizadas(corpo_novo)
        if antes == depois:
            continue
        if chave == "0" and bloco0_aceito:
            base = base.replace(corpo_aceito.rstrip(), corpo_novo.rstrip(), 1)
            continue
        if avisos is None:
            continue
        import difflib

        diff = [l for l in difflib.unified_diff(antes, depois, lineterm="", n=0)
                if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        if not chave and not any(l.startswith("-") for l in diff):
            continue  # frase do agente antes da spec («Abaixo é emitida a especificação…», 4fd72a9a): não é o Gate 0
        nome = f"o bloco {chave}" if chave.isdigit() else ("o cabeçalho" if not chave else f"a seção «{chave}»")
        if chave in BLOCOS_DO_DESIGN:
            avisos.append({
                "severidade": "atencao", "codigo": "alterou-fora-do-proprio-bloco", "etapa": "design",
                "agente_responsavel": agente,
                "resumo": (f"{autor} alterou fora do bloco {proprio or titulo}: {nome} veio diferente do aceito e a "
                           "mudança foi descartada:\n" + "\n".join(f"    {l[:200]}" for l in diff[:15])),
            })
            continue
        # Texto do Gate 0: quem muda é o PO. A troca que um pedido do PO fez em design também vem para cá — o pedido
        # vale, mas no documento de produto (plano, D4 e D11); até o PR 5 o caminho é devolver a Produto.
        a_pedido = [l for l in diff if l.startswith("-") and _cita_texto_do_po(l, estado or {})]
        from tools.fechar_contrato import trocas_de_linhas

        avisos.append({
            "severidade": "bloqueio" if estrito else "decisao_humana", "codigo": "alterou-fora-do-proprio-bloco",
            "etapa": "design", "agente_responsavel": "PO", "autor": agente, "aberto_dono_po": True,
            # as trocas por linha, para o de acordo de produto gravá-las se o PO aceitar (plano, PR 3): devolvida a
            # Produto, a missão mostra a mudança na lista do cartão, e o «aceitar» a põe no texto do Gate 0
            "bloco": chave, "trocas": trocas_de_linhas(antes, depois),
            "resumo": (f"[ABERTO — dono: PO: {autor} quis mudar {nome} da spec do Gate 0, e a spec é montada em código — a "
                       "mudança não entrou]. O texto de produto só muda em produto: se ela deve valer, devolva a "
                       "Produto com a decisão"
                       + (" (a linha trazia um texto que o PO mandou trocar em design)" if a_pedido else "")
                       + (". Com ESTEIRA_ESTRITA, o de acordo de design espera essa decisão" if estrito else "")
                       + (" (o bloco 0 só muda por `[RS-AMB]` aceita)" if chave == "0" else "")
                       + ":\n" + "\n".join(f"    {l[:200]}" for l in diff[:15])
                       + (f"\n    … e mais {len(diff) - 15} linha(s)" if len(diff) > 15 else "")),
        })
    novas = [c for c in dos_novos if c not in dos_aceitos and c != proprio and c and dos_novos[c].strip()]
    if novas and avisos is not None:
        avisos.append({
            "severidade": "atencao", "codigo": "alterou-fora-do-proprio-bloco", "etapa": "design",
            "agente_responsavel": agente,
            "resumo": (f"{autor} trouxe seção(ões) que a spec aceita não tem, fora do bloco {proprio or titulo}, e elas "
                       "foram descartadas: " + ", ".join(f"«{c}»" for c in novas[:8])),
        })
    return _inserir_bloco(base, bloco, titulo, proprio)


def _instabilidade(state: Dict[str, Any], ex: Dict[str, Any], secao: str) -> Optional[Dict[str, Any]]:
    """Achado `autor-instavel` quando a seção perdeu linhas da versão da execução anterior (`estavel_contra`)."""
    from pipeline.reexecucao import KEY_ETAPA_DA_CORRECAO, PREFIXO_VERSAO_ANTERIOR
    from tools.preservacao import linhas_perdidas

    fonte = str(ex["estavel_contra"])
    anterior = str(state.get(f"{PREFIXO_VERSAO_ANTERIOR}{fonte}") or "")
    antes = extrair_secao(anterior, ex["inicio"], ex.get("fim")) if anterior.strip() else None
    if not antes:
        return None
    antes = documento_sem_moldura(antes)
    if ex.get("bloco_proprio"):
        # o autor que escreve um bloco só responde por ele: a versão anterior do D0 trazia a spec inteira, e a nova só
        # o bloco 13 — comparar as duas inteiras acusaria o texto do Gate 0, que ele não escreve mais (23/10/2026)
        antes = _bloco(antes, ex["bloco_proprio"])
        if not antes.strip():
            return None
    sumiram = linhas_perdidas(antes, secao)
    if not sumiram:
        return None
    # spec do Gate 0 refeita (produto/spec reexecutados), retrabalho por achado de gate nesta execução ou pedido de
    # correção de design: a mudança pode ter motivo
    com_motivo = bool(str(state.get("tickets_retrabalho") or "").strip()) or bool(str(state.get(f"{PREFIXO_VERSAO_ANTERIOR}spec_missao") or "").strip()) or (
        str(state.get(KEY_ETAPA_DA_CORRECAO) or "") == "design" and str(state.get("pedido_correcao") or "").strip())
    return {
        "severidade": "atencao" if com_motivo else "bloqueio", "codigo": "autor-instavel", "etapa": "design",
        "agente_responsavel": ex.get("preservar") or fonte,
        "resumo": (f"`{ex['chave']}` perdeu {len(sumiram)} linha(s) da versão da execução anterior"
                   + (" — confira se o motivo do refazer as cobre" if com_motivo else
                      ", sem pedido de correção e sem mudança a montante. Devolva cada uma como estava")
                   + ":\n" + "\n".join(f"    - «{l[:200]}»" for l in sumiram[:15])),
    }


#: `base_preservada_<chave>`: a versão aceita de um documento cuja reescrita perdeu linhas (`SecaoSplitAgent`).
PREFIXO_BASE_PRESERVADA = "base_preservada_"


class SecaoSplitAgent(BaseAgent):
    """Copia seções de um relatório para chaves próprias do estado e registra um status informativo.

    Cada item de `extracoes` é um dict:
      chave         → chave do estado que recebe a seção
      inicio        → regex (multiline) do heading que abre a seção; o texto começa depois dele
      fim           → regex (multiline) do heading que fecha a seção (opcional)
      exigir        → regex que a seção precisa conter para ser aceita (opcional)
      minimo_chars  → tamanho mínimo aceito (padrão 0)
      minimo_fracao → fração mínima do tamanho do valor ATUAL de `chave` (padrão 0 = desligado).
                      Protege contra o agente devolver só o pedaço novo no lugar do documento
                      inteiro: a spec consolidada é a spec ANTERIOR mais um bloco, então nunca
                      encolhe. Sem isso, o D9 já substituiu uma spec de 35 KB por um fragmento
                      de 5 KB, e o dev perdeu a ficha do manifesto e todos os blocos.
      backup        → chave onde o valor anterior de `chave` é preservado antes de sobrescrever (opcional)
      preservar     → dono do conserto (slug de retrabalho) quando uma linha do documento ATUAL some
                      do novo (`tools/preservacao.linhas_perdidas`). O D0 da exp06ef1b apagou a
                      pergunta 3 do debate e passou: o tamanho não encolheu o bastante (07/10/2026).
      estavel_contra → chave autoral cuja versão de antes do refazer (`versao_anterior_<chave>`) traz a mesma
                      seção: o que ela tinha e a nova não tem é instabilidade do autor. Na exp06ef1b o D0 traduziu
                      o próprio texto num refazer sem pedido. Sem nada mudado a montante (spec do Gate 0) e sem
                      pedido de correção de design, é bloqueio; com motivo, 🟡 com as linhas (plano padrão ouro, 2.7).
      bloco_proprio → regex do título do único bloco que este autor escreve (`^## 13` do D0, `^## 14` do D9): o
                      documento gravado é a versão aceita com esse bloco trocado pelo da nova — o resto da nova é
                      descartado, e a preservação confere só o que não é dele (`montar_sobre_aceita`). A mudança no
                      texto do Gate 0 vira `[ABERTO — dono: PO]` no cartão do parecer (bloqueio só com `estrito`).
      bloco_obrigatorio → sem o `bloco_proprio` na nova, a chave fica como estava e o achado é bloqueio: o D0 sem o
                      bloco 13 deixava a jusante citando [D0-n] que a spec não tem (60cfa7f4 e 4fd72a9a, 23/10/2026).
      autor         → nome do autor nos achados («D0», «D9»).
      bloco_autoral → regex do título do bloco que este autor escreve inteiro, num documento em que ele também mexe
                      fora dele: a preservação não confere esse bloco, e o resto da nova versão é gravado como veio.
                      Na exp02em1b (22/10/2026) a rodada 1 do D0, reprovada, virou a base, e a rodada 2 foi acusada de
                      apagar o [D0-7] que ela mesma escrevera. O D0 passou a `bloco_proprio` em 23/10/2026.

    Seção ausente, curta ou sem o conteúdo exigido → a chave é mantida como está e o evento avisa.
    """

    source_key: str
    status_key: str
    rotulo: str = "Split"
    extracoes: List[Dict[str, Any]] = Field(default_factory=list)
    #: a fonte é um documento, não um veredito (o one-pager do A014): não há envelope a ler, e
    #: procurá-lo gerava um `envelope-ilegivel` em toda execução
    fonte_sem_veredito: bool = False
    #: ESTEIRA_ESTRITA: a mudança no texto do Gate 0 (`[ABERTO — dono: PO]`) bloqueia; sem ela, é decisão humana 🟡
    estrito: bool = False

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        texto = str(state.get(self.source_key, "") or "")
        delta: Dict[str, Any] = {}
        linhas: List[str] = []

        if not texto.strip():
            # O status era simplesmente NÃO GRAVADO, e `tools/diagnostico.py` pula gate ausente
            # do estado: o D0 e o D9 truncados **sumiam do dossiê**, sem linha, sem achado e sem
            # veredito. Uma resposta que não chegou é bloqueio, e precisa aparecer.
            linhas.append(f"⛔ {self.rotulo}: `{self.source_key}` vazio — o agente não respondeu.")
            delta[self.status_key] = STATUS_BLOQUEADO
            delta[f"{self.status_key}_envelope"] = {
                "status": "bloqueado",
                "achados": [{
                    "severidade": "bloqueio", "codigo": "fonte-vazia",
                    "agente_responsavel": self.name,
                    "resumo": f"`{self.source_key}` chegou vazio: o agente não produziu resposta.",
                }],
            }
        else:
            faltou: List[tuple] = []
            perdidas: List[Dict[str, Any]] = []
            fora_do_bloco: List[Dict[str, Any]] = []
            instaveis: List[Dict[str, Any]] = []
            for ex in self.extracoes:
                chave = ex["chave"]
                secao = extrair_secao(texto, ex["inicio"], ex.get("fim"))
                if secao is not None:
                    secao = documento_sem_moldura(secao)
                proprio = ex.get("bloco_proprio")
                bruta = secao or ""  # o que o autor escreveu, antes da montagem
                aceita = str(state.get(f"{PREFIXO_BASE_PRESERVADA}{chave}") or "") or str(state.get(chave) or "")
                sem_o_proprio = bool(secao is not None and proprio and ex.get("bloco_obrigatorio")
                                     and not re.search(proprio, secao, re.MULTILINE))
                if secao is not None and proprio and aceita.strip() and not sem_o_proprio:
                    env_fonte = None if self.fonte_sem_veredito else extrair_envelope(texto)
                    secao = montar_sobre_aceita(documento_sem_moldura(aceita), secao, proprio,
                                                bloco0_aceito=bloco0_pode_mudar(env_fonte), avisos=fora_do_bloco,
                                                autor=ex.get("autor", "D9"), agente=ex.get("preservar") or self.name,
                                                estrito=self.estrito, estado=state)
                motivo: Optional[str] = None
                if sem_o_proprio:
                    motivo = "a resposta não traz o bloco próprio do autor"
                    perdidas.append({
                        "severidade": "bloqueio", "codigo": "bloco-proprio-ausente", "etapa": "design",
                        "agente_responsavel": ex.get("preservar") or self.name,
                        "resumo": (f"{ex.get('autor', self.rotulo)} respondeu sem o bloco que só ele escreve "
                                   f"(`{proprio}`): `{chave}` ficou como estava, e quem citar a jusante uma decisão "
                                   "dele cita o que a spec não tem. Reemita o bloco inteiro."),
                    })
                elif secao is None:
                    motivo = "seção não encontrada no relatório"
                elif len(secao) < int(ex.get("minimo_chars", 0) or 0):
                    motivo = f"seção curta demais ({len(secao)} caracteres)"
                elif ex.get("exigir") and not re.search(ex["exigir"], secao, re.MULTILINE | re.IGNORECASE):
                    motivo = "seção sem o conteúdo exigido"
                else:
                    fracao = float(ex.get("minimo_fracao", 0) or 0)
                    atual = len(str(state.get(chave, "") or ""))
                    if fracao and atual and len(secao) < fracao * atual:
                        motivo = (
                            f"seção com {len(secao)} caracteres contra {atual} do documento atual "
                            f"({len(secao) / atual:.0%}) — parece o pedaço novo, não o documento consolidado"
                        )
                if motivo:
                    linhas.append(f"⚠️ `{chave}` mantido como estava — {motivo}.")
                    if ex.get("ausencia_vira_ressalva"):
                        faltou.append((chave, motivo))
                    continue
                backup = ex.get("backup")
                if backup and state.get(chave) and not state.get(backup):
                    delta[backup] = state.get(chave)
                if ex.get("carregar_blocos") and aceita.strip():
                    # O bloco de outro autor que esta reescrita omitiu volta como estava: no retrabalho só o D0 roda,
                    # e o bloco 14 do D9 sumia da spec (exp03ef1b, 23/10/2026) — ninguém o regravava.
                    for regex in ex["carregar_blocos"]:
                        if not re.search(regex, secao, re.MULTILINE):
                            bloco = _bloco(documento_sem_moldura(aceita), regex)
                            if bloco:
                                secao = secao.rstrip() + "\n\n" + bloco.strip() + "\n"
                                linhas.append(f"↩️ `{chave}`: bloco de outro autor que a reescrita omitiu carregado da versão aceita.")
                if ex.get("preservar") and str(state.get(chave) or "").strip():
                    from tools.preservacao import linhas_perdidas

                    # A comparação é contra a última versão ACEITA. A reescrita reprovada também é gravada (a
                    # jusante precisa do bloco novo), e virava a base da rodada seguinte: na exp06ef1b (09/10/2026)
                    # o D9 trocou as palavras do [D0-3], foi reprovado, devolveu o texto literal do D0 — e a
                    # rodada 2 o acusou de apagar a troca que a rodada 1 tinha feito.
                    chave_base = f"{PREFIXO_BASE_PRESERVADA}{chave}"
                    base = str(state.get(chave_base) or "") or str(state.get(chave))
                    comparada = documento_sem_moldura(base)
                    if proprio or ex.get("bloco_autoral"):
                        # o bloco do próprio autor ele pode reescrever; o resto é o que veio antes dele
                        comparada = _sem_bloco(comparada, proprio or ex["bloco_autoral"])
                    sumiram = linhas_perdidas(comparada, secao)
                    # A linha que tinha um texto que o PO mandou trocar muda por ordem dele: é atenção, não perda.
                    # Na exp02ef1b (23/10/2026) o PO trocou «Publicar no Álbum» por «Colocar no álbum» e a linha do
                    # glossário da spec, trocada, bloqueava — um gate mandava trocar e o outro proibia.
                    pedidas = [l for l in sumiram if _cita_texto_do_po(l, state)]
                    sumiram = [l for l in sumiram if l not in pedidas]
                    if pedidas:
                        instaveis.append({
                            "severidade": "atencao", "codigo": "linha-trocada-a-pedido", "etapa": "design",
                            "agente_responsavel": ex["preservar"],
                            "resumo": (f"`{chave}`: {len(pedidas)} linha(s) do documento anterior mudaram porque traziam um "
                                       "texto que o PO mandou trocar — confira se a troca está certa:\n"
                                       + "\n".join(f"    - «{l[:200]}»" for l in pedidas[:10])),
                        })
                    delta[chave_base] = base if sumiram else ""
                    if sumiram:
                        perdidas.append({
                            "severidade": "bloqueio", "codigo": "linhas-perdidas", "etapa": "design",
                            "agente_responsavel": ex["preservar"],
                            "resumo": (f"`{chave}` reescrito sem {len(sumiram)} linha(s) do documento anterior — o que "
                                       "o autor de antes escreveu não pode sumir na consolidação. Devolva cada uma, "
                                       "no mesmo lugar:\n" + "\n".join(f"    - «{l[:200]}»" for l in sumiram[:15])),
                        })
                        linhas.append(f"⛔ `{chave}`: {len(sumiram)} linha(s) do documento anterior sumiram na reescrita.")
                if ex.get("estavel_contra"):
                    achado = _instabilidade(state, ex, _bloco(bruta, proprio) if proprio else secao)
                    if achado:
                        (perdidas if achado["severidade"] == "bloqueio" else instaveis).append(achado)
                        linhas.append(f"{'⛔' if achado['severidade'] == 'bloqueio' else '🟡'} `{chave}`: mudou contra "
                                      "a versão da execução anterior.")
                delta[chave] = secao
                linhas.append(f"✅ `{chave}` gravado a partir de `{self.source_key}` ({len(secao)} caracteres).")

            envelope = None if self.fonte_sem_veredito else extrair_envelope(texto)
            status = STATUS_APROVADO if self.fonte_sem_veredito else inferir_status(texto, envelope)
            ilegivel = status not in (STATUS_APROVADO, STATUS_BLOQUEADO)
            if ilegivel:
                status = STATUS_APROVADO  # o split é informativo: o conteúdo veio, o veredito não
            delta[self.status_key] = (STATUS_APROVADO if ilegivel or self.fonte_sem_veredito
                                      else status_registrado(texto, envelope))
            env = dict(envelope or {})
            if ilegivel:
                env.setdefault("achados", []).append({
                    "severidade": "atencao", "codigo": "envelope-ilegivel",
                    "agente_responsavel": self.name,
                    "resumo": f"{self.rotulo} respondeu sem envelope legível — o conteúdo foi extraído, o veredito não.",
                })
            # Seção que o documento TINHA de trazer e não trouxe: o status vinha do envelope da
            # fonte (o one-pager, "aprovado"), e a ausência ficava só no log — no dossiê, verde.
            # Era o GAP-09 (brief de escopo evaporado) com cara de sucesso.
            if faltou:
                if delta[self.status_key] != STATUS_BLOQUEADO:
                    delta[self.status_key] = "amarelo"
                for chave, motivo in faltou:
                    env.setdefault("achados", []).append({
                        "severidade": "atencao", "codigo": "secao-ausente",
                        "agente_responsavel": self.name,
                        "resumo": f"`{chave}` não veio em `{self.source_key}`: {motivo}.",
                    })
            # lacuna de mecânica ou currículo é decisão humana: o D0 não a fecha em verde
            if self.source_key == "fechamento_lacunas":
                from tools.decisoes import (decisoes_d0_de_produto, lacunas_fechadas_pelo_agente,
                                            lacunas_fechadas_pelo_parecer, tabela_de_classes)
                from tools.propagacao import spec_de_produto

                # a tabela do Passo 2 está na resposta inteira; a fonte que cita parecer é conferida contra estes
                pareceres = str(state.get("notas_de_passagem") or "") + json.dumps(
                    state.get("pedidos_do_po") or [], ensure_ascii=False, default=str)
                fechadas = lacunas_fechadas_pelo_agente(texto, pareceres)
                pelo_parecer = lacunas_fechadas_pelo_parecer(texto, pareceres)
                # e todo [D0-n] que fecha [PARÂMETRO] ou promove [PROPOSTA] do Gate 0, qualquer que seja a classe
                spec_gate0 = str(state.get("spec_missao_gate0") or delta.get("spec_missao_gate0")
                                 or spec_de_produto(str(state.get("spec_missao") or "")))
                marcador_sem, marcador_pelo = decisoes_d0_de_produto(
                    texto, envelope, spec_gate0, pareceres, classes_na_tabela=tabela_de_classes(texto))
                fechadas += marcador_sem
                pelo_parecer += marcador_pelo
                if pelo_parecer:
                    # como `decisao-atribuida-ao-po` com registro: o código não sabe se o parecer diz isto
                    if delta[self.status_key] != STATUS_BLOQUEADO:
                        delta[self.status_key] = "amarelo"
                    linhas.append(f"🟡 {len(pelo_parecer)} decisão(ões) de produto aplicada(s) pelo D0 a partir do parecer do PO.")
                    env.setdefault("achados", []).append({
                        "severidade": "atencao", "codigo": "mecanica-pelo-parecer", "etapa": "design",
                        "agente_responsavel": "fecha-lacunas",
                        "resumo": ("Lacuna de produto (mecânica, currículo, [PARÂMETRO] ou [PROPOSTA] do Gate 0) fechada "
                                   "pelo D0 com base no parecer do PO. O código não sabe se o parecer diz isto — confira "
                                   "antes do de acordo:\n" + "\n".join(f"    - {l}" for l in pelo_parecer[:10])),
                    })
                if fechadas:
                    perdidas.append({
                        "severidade": "bloqueio", "codigo": "decisao-de-produto-pelo-agente", "etapa": "design",
                        "agente_responsavel": "fecha-lacunas",
                        "resumo": ("Decisão de produto fechada pelo D0 sem parecer datado do PO: classe de produto "
                                   "(`mecanica*`, `curriculo*`, `parametro*` ou fora da lista) ou [PARÂMETRO]/[PROPOSTA] da "
                                   "spec do Gate 0, inclusive em duração, dados e acessibilidade. Reabra cada uma como "
                                   "`[ABERTO — dono: PO: …]` no bloco 13, com a sugestão e as alternativas, sem decidir:\n"
                                   + "\n".join(f"    - {l}" for l in fechadas[:12])
                                   + (f"\n    - … e mais {len(fechadas) - 12}" if len(fechadas) > 12 else "")),
                    })
            if fora_do_bloco:
                if delta[self.status_key] != STATUS_BLOQUEADO:
                    delta[self.status_key] = "amarelo"
                env.setdefault("achados", []).extend(a for a in fora_do_bloco if a["severidade"] != "bloqueio")
                perdidas.extend(a for a in fora_do_bloco if a["severidade"] == "bloqueio")
                abertos = [a for a in fora_do_bloco if a.get("aberto_dono_po")]
                if abertos:
                    # a mudança no texto do Gate 0 é decisão do PO: o cartão do parecer abre o achado
                    env["precisa_humano"] = True
                    linhas.append(f"🧑 {len(abertos)} mudança(s) no texto do Gate 0 descartada(s) — `[ABERTO — dono: PO]` "
                                  "no cartão do parecer de design.")
                outros = len(fora_do_bloco) - len(abertos)
                if outros:
                    linhas.append(f"🟡 {outros} bloco(s) alterado(s) fora do bloco próprio — descartado(s), ver achados.")
            if instaveis:
                if delta[self.status_key] != STATUS_BLOQUEADO:
                    delta[self.status_key] = "amarelo"
                env.setdefault("achados", []).extend(instaveis)
            if perdidas:
                delta[self.status_key] = STATUS_BLOQUEADO
                env["status"] = "bloqueado"
                env.setdefault("achados", []).extend(perdidas)
            delta[f"{self.status_key}_envelope"] = env
            bruto = (envelope or {}).get("status") or status
            icone = "🔴" if status == STATUS_BLOQUEADO else "🟢"
            linhas.append(f"{icone} {self.rotulo}: status `{bruto}` (informativo — o pipeline segue).")

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text="\n".join(linhas))]),
            actions=EventActions(state_delta=delta),
        )



class ArtefatosDesignAgent(BaseAgent):
    """Determinístico: separa o protótipo do relatório, colhe os links do Stitch e monta os diagramas.

    Três coisas que não precisam de modelo e não podem passar por ele:

    - o HTML do protótipo tem dezenas de KB e não pode entrar no prompt do QA nem do
      PRD, então é separado do relatório que o acompanha;
    - os links do Stitch vêm da api, não da memória do agente;
    - a folha de diagramas é remontagem do Mermaid que a jornada e o fluxo já
      escreveram.
    """

    prototipo_key: str = "prototipo_html"
    arquivo_key: str = "prototipo_arquivo"
    relatorio_key: str = "prototipo_relatorio"
    links_key: str = "stitch_links"
    diagramas_key: str = "diagramas_html"
    fonte_wireframes: str = "wireframes_cobertura"
    #: Telas no Stitch × inventário da jornada. Na exp09ef1b o Stitch tinha 6 das 16 telas e o QA escreveu
    #: "todas as 16 telas ativas"; aqui só se avisava a falta de `E0-PROF`. Menos telas que o inventário
    #: bloqueia, com dono `telas` — o `A089QaAfirmacoes` leva o ticket ao retrabalho.
    status_key: str = "stitch_status"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from tools.artefatos_html import extrair_prototipo, montar_folha_de_diagramas

        state = ctx.session.state
        delta: Dict[str, Any] = {}
        linhas: List[str] = []
        titulo = extrair_slug(str(state.get("spec_missao", "") or "")) or "missão"

        documento, relatorio = extrair_prototipo(str(state.get(self.prototipo_key, "") or ""))
        if documento:
            delta[self.arquivo_key] = documento
            delta[self.relatorio_key] = relatorio
            linhas.append(f"🖥️ Protótipo separado: {len(documento) // 1024} KB de HTML + relatório.")
        elif state.get(self.prototipo_key):
            delta[self.relatorio_key] = str(state.get(self.prototipo_key))
            linhas.append("⚠️ Não achei um documento HTML na saída do protótipo — guardei tudo como relatório.")

        diagramas = montar_folha_de_diagramas(titulo, state.get("jornada_telas"), state.get("fluxo_arestas"))
        if diagramas:
            delta[self.diagramas_key] = diagramas
            linhas.append("🗺️ Folha de diagramas montada a partir do Mermaid da jornada e do fluxo.")

        try:
            from config import get_settings
            from tools.stitch_cliente import (
                coletar_links,
                extrair_project_id,
                extrair_screen_ids,
                montar_folha_de_links,
            )

            if get_settings().is_stitch_enabled:
                relatorio = str(state.get(self.fonte_wireframes, "") or "")
                pid = str(state.get("stitch_project_id") or "") or extrair_project_id(relatorio)
                if pid:
                    from tools.stitch_geracao import rotulos

                    # e as telas que a geração registrou: a listagem do Stitch já voltou parcial (exp06ef1b, 09/10/2026)
                    registro = state.get("stitch_geracao") or {}
                    esperados = extrair_screen_ids(relatorio) + [str(v.get("screen_id") or "") for v in registro.values()
                                                                 if isinstance(v, dict)]
                    dados = coletar_links(pid, limite=1000, ids_de_reserva=esperados)
                    # a tela gerada pela esteira leva o nome do inventário (`E2-ALU-01 — padrão`), não o título
                    # que o Stitch inventou: é por ele que a cobertura e o pedagógico acham cada tela
                    nomes = rotulos(state.get("stitch_geracao") or {})
                    for tela in dados["telas"]:
                        if tela.get("id") in nomes:
                            tela["titulo"] = nomes[tela["id"]]
                    # Com registro, a entrega é só a versão atual de cada tela: o Stitch não apaga a anterior, e a
                    # folha (que vai ao PRD) listava as duas misturadas. As antigas ficam contadas, sem ID de tela,
                    # para não contarem como cobertura (decisão do usuário, 08/10/2026).
                    anteriores = 0
                    if nomes:
                        anteriores = sum(1 for t in dados["telas"] if t.get("id") not in nomes)
                        dados = {**dados, "telas": [t for t in dados["telas"] if t.get("id") in nomes]}
                    delta[self.links_key] = montar_folha_de_links(dados, titulo)
                    if anteriores:
                        delta[self.links_key] += (
                            f"\n## Versões anteriores no projeto\n\n{anteriores} tela(s) do projeto são versões anteriores "
                            "de telas refeitas, ou telas que saíram do inventário. Continuam no Stitch — o título da "
                            "atual leva `· vN` — e não entram nesta entrega.\n")
                    linhas.append(f"🔗 Stitch: {len(dados['telas'])} tela(s) no projeto `{pid}` — link no relatório e no PRD.")
                    from tools.afirmacoes import cobertura_stitch

                    cob = cobertura_stitch(delta[self.links_key], str(state.get("jornada_telas", "") or ""),
                                           recusa=str(state.get("stitch_geracao_recusa") or ""))
                    delta[self.status_key] = cob["status"]
                    delta[f"{self.status_key}_envelope"] = {"agente": "stitch-cobertura", "status": cob["status"],
                                                            "achados": cob["achados"], "precisa_humano": False}
                    for a in cob["achados"]:
                        linhas.append(f"⛔ {a['resumo']}")
                    if dados["telas"] and not any("E0-PROF" in (t.get("titulo") or "").upper() for t in dados["telas"]):
                        # A folha já carrega o marcador `[LACUNA — dono: telas]`; aqui só se avisa.
                        linhas.append("⚠️ Nenhuma tela do preparo do professor (`E0-PROF-*`) no Stitch — lacuna registrada na folha com dono `telas`.")
                else:
                    # Sem projeto não há o que conferir — e era assim que o Stitch vazio passava. Com o
                    # Stitch ligado, relatório sem projectId é bloqueio com dono `telas`.
                    resumo = ("O Stitch está ligado e o relatório de wireframes não traz o identificador do projeto "
                              "(`projects/<id>`): nenhuma tela pode ser conferida. Crie ou reaproveite o projeto e "
                              "gere todas as telas do inventário nele.")
                    achado = {"severidade": "bloqueio", "codigo": "stitch-sem-projeto", "etapa": "design",
                              "agente_responsavel": "telas", "resumo": resumo}
                    delta[self.status_key] = "bloqueado"
                    delta[f"{self.status_key}_envelope"] = {"agente": "stitch-cobertura", "status": "bloqueado",
                                                            "achados": [achado], "precisa_humano": False}
                    linhas.append(f"⛔ {resumo}")
        except Exception as exc:  # a coleta é conveniência: nunca derruba a esteira
            linhas.append(f"⚠️ Não consegui colher os links do Stitch: {exc}")

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text="\n".join(linhas) or "Nada a coletar.")]),
            actions=EventActions(state_delta=delta),
        )


class QaAfirmacoesAgent(BaseAgent):
    """Confere em código as contagens de telas e os nomes de arquivo que o QA de design escreveu.

    Na exp09ef1b o QA aprovou o design escrevendo "todas as 16 telas ativas e vinculadas" ao lado do
    link do Stitch — o projeto tinha 6 — e apontou o protótipo em `design/08-prototipo-navegavel.html`,
    arquivo que a esteira não grava. Roda entre o QA e o veredito: afirmação que não bate, ou Stitch
    com menos telas que o inventário (`stitch_status`), reescreve o envelope do QA como bloqueado e
    acrescenta os tickets — o do Stitch com dono `telas`, para o retrabalho desenhar o que falta.
    O próprio veredito vai para `qa_afirmacoes_status`, no dossiê.
    """

    report_key: str = "qa_afirmacoes_report"
    status_key: str = "qa_afirmacoes_status"
    qa_key: str = "qa_entregaveis_report"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from tools import afirmacoes as af

        state = ctx.session.state
        qa = str(state.get(self.qa_key, "") or "")
        # o envelope da rodada anterior ainda está no estado: o que ele acusou, o QA desta rodada pode relatar
        resultado = af.conferir_qa(qa, str(state.get("stitch_links", "") or ""), str(state.get("jornada_telas", "") or ""),
                                   str(state.get("prototipo_arquivo", "") or ""),
                                   ja_apontados=af.arquivos_apontados(state.get(f"{self.status_key}_envelope")))
        missao = extrair_slug(str(state.get("spec_missao") or "")) or ""
        relatorio = af.relatorio(resultado, missao)
        delta: Dict[str, Any] = {self.report_key: relatorio, self.status_key: resultado["status"],
                                 f"{self.status_key}_envelope": extrair_envelope(relatorio) or {}}
        tickets = list(resultado["achados"])
        # Stitch e cobertura de telas por ID: o bloqueio deles vira ticket com o dono do conserto
        # e os de lint, consistência e preservação da spec: dependiam de o QA ler o relatório e escrever o
        # ticket, e o protótipo nem tinha rota (auditoria de 07/10/2026)
        for chave in ("stitch_status", "cobertura_telas_status", "prototipo_lint_status", "consistencia_status",
                      "lacunas_status", "ambiente_status", "conteudo_aprovado_spec_design_status",
                      "banca_design_status"):
            if str(state.get(chave, "")) == "bloqueado":
                envelope_gate = state.get(f"{chave}_envelope") or {}
                for a in envelope_gate.get("achados") or []:
                    if a.get("severidade") != "bloqueio":
                        continue
                    if chave in ("lacunas_status", "ambiente_status") and a.get("codigo") not in (
                            "linhas-perdidas", "decisao-de-produto-pelo-agente", "bloco-proprio-ausente"):
                        # o resto do envelope do D0/D9 é do autor, não do código; e a mudança no texto do Gate 0
                        # (`[ABERTO — dono: PO]`) é do PO: outra rodada do autor não a resolve
                        continue
                    tickets.append(a)
        envelope = extrair_envelope(qa)
        if tickets and envelope is not None:
            novo = dict(envelope)
            novo["status"], novo["veredito"] = "bloqueado", "vermelho"
            novo["achados"] = list(envelope.get("achados") or []) + [
                {"id": f"QA-A{i}", **a} for i, a in enumerate(tickets, 1)]
            delta[self.qa_key] = (qa.rstrip() + "\n\n## Afirmações conferidas em código (A089)\n\n"
                                  # o achado da banca vem com `id` (DES-06), sem `codigo` (exp03em1b, 22/10/2026)
                                  + "\n".join(f"- ⛔ `{a.get('codigo') or a.get('id') or 'achado'}` — {a.get('resumo', '')}"
                                              for a in tickets)
                                  + "\n\nO veredito acima foi reescrito: aprovar com uma contagem que não bate é aprovar "
                                    "o que ninguém viu.\n\n```json\n" + json.dumps(novo, ensure_ascii=False) + "\n```\n")
        msg = ("✅ Afirmações do QA: contagens e arquivos batem." if not tickets else
               f"⛔ Afirmações do QA: {len(tickets)} divergência(s) — o veredito do QA foi reescrito como bloqueado.\n"
               + "\n".join(f"- {a['resumo'][:200]}" for a in tickets))
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    content=types.Content(role="model", parts=[types.Part(text=msg)]),
                    actions=EventActions(state_delta=delta))


class EspelhoMiroAgent(BaseAgent):
    """Determinístico: espelha no Miro o Mermaid que a jornada e o fluxo já escreveram.

    Separado do `ArtefatosDesignAgent` por dois motivos práticos. O primeiro é
    idempotência: o board tem de ser o mesmo entre as rodadas de QA, o que exige guardar
    os identificadores dos widgets e reenviá-los — sem isso, três rodadas produzem três
    pares de diagramas no mesmo board. O segundo é que a folha de diagramas e o
    protótipo têm de sair sempre, enquanto o espelho é condicional à conexão.

    O board é **espelho**, nunca fonte: quem manda é o Mermaid versionado. Por isso todo
    o corpo roda sob `try/except` e, quando o Miro não responde, grava-se a folha de
    indisponibilidade em vez de nada — artefato ausente vira achado no QA, e uma
    integração desligada não é defeito da missão.
    """

    jornada_key: str = "jornada_telas"
    fluxo_key: str = "fluxo_arestas"
    links_key: str = "miro_links"
    board_key: str = "miro_board"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from config import get_settings
        from tools.miro_cliente import (
            folha_de_indisponibilidade,
            montar_folha_de_links,
            motivo_de_indisponibilidade,
            publicar_diagramas,
        )

        state = ctx.session.state
        delta: Dict[str, Any] = {}
        titulo = extrair_slug(str(state.get("spec_missao", "") or "")) or "missão"

        jornada = str(state.get(self.jornada_key, "") or "")
        fluxo = str(state.get(self.fluxo_key, "") or "")

        if not get_settings().is_miro_enabled:
            delta[self.links_key] = folha_de_indisponibilidade("MIRO_MODE=off", titulo)
            mensagem = "⚪ Miro desligado — a folha registra a ausência e a esteira segue."
        elif not (jornada or fluxo):
            delta[self.links_key] = folha_de_indisponibilidade("jornada e fluxo vazios", titulo)
            mensagem = "⚠️ Nada a espelhar: jornada e fluxo não produziram diagrama."
        else:
            try:
                dados = publicar_diagramas(titulo, jornada, fluxo, board=state.get(self.board_key))
                delta[self.links_key] = montar_folha_de_links(dados, titulo)
                delta[self.board_key] = {"url_board": dados["url_board"], "widgets": dados["widgets"]}
                mensagem = f"🪞 Miro: {len(dados['diagramas'])} diagrama(s) — board {dados['modo']} em {dados['url_board']}"
                if dados["ressalvas"]:
                    mensagem += "\n" + "\n".join(f"⚠️ {r}" for r in dados["ressalvas"])
            except Exception as exc:  # o espelho é conveniência: nunca derruba a esteira
                motivo = motivo_de_indisponibilidade(exc)
                delta[self.links_key] = folha_de_indisponibilidade(motivo, titulo)
                mensagem = f"⚠️ Não consegui espelhar no Miro: {motivo}"

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=mensagem)]),
            actions=EventActions(state_delta=delta),
        )


class BnccCheckAgent(BaseAgent):
    """Gate determinístico de conformidade com a BNCC Computação, aplicado à spec.

    Três regras mecânicas (ver `tools/bncc.py`): todo código do bloco 11 existe na lista
    oficial; todo código é compatível com a série do bloco 0; há pelo menos uma habilidade
    de letramento digital. Falha em qualquer uma → `bncc_status = bloqueado`; com `estrito`,
    o pipeline é marcado como bloqueado e design/dev são pulados.
    """

    spec_key: str = "spec_missao"
    report_key: str = "bncc_report"
    status_key: str = "bncc_status"
    rotulo: str = "Conformidade BNCC Computação"
    estrito: bool = True

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        spec = str(state.get(self.spec_key, "") or "")
        missao = extrair_slug(spec) or ""
        # o material anexado entra porque a spec pode citar o texto da habilidade como está nele
        resultado = validar_spec(spec, str(state.get("material_anexado") or ""))
        relatorio = relatorio_markdown(resultado, missao)
        status = STATUS_APROVADO if resultado["status"] == "aprovado" else STATUS_BLOQUEADO

        delta: Dict[str, Any] = {
            self.report_key: relatorio,
            self.status_key: status,
            f"{self.status_key}_envelope": extrair_envelope(relatorio) or {},
        }
        bloqueios = [a for a in resultado["achados"] if a["severidade"] == "bloqueio"]
        if status == STATUS_APROVADO:
            msg = (
                f"✅ {self.rotulo}: conforme — {len(resultado['codigos'])} código(s) do bloco 11 existem, "
                f"são da série identificada e incluem letramento digital."
            )
            limpar_degradacao(state, delta, self.rotulo)
        else:
            itens = "\n".join(f"- ⛔ {a['resumo']}" for a in bloqueios)
            if self.estrito:
                registrar_degradacao(
                    state, delta, self.rotulo,
                    f"{self.rotulo} reprovada ({len(bloqueios)} achado(s))",
                )
                msg = (
                    f"⛔ {self.rotulo}: reprovada — {len(bloqueios)} achado(s). "
                    f"Design e dev seguem, marcando `[PROVISÓRIO]` o que depender do currículo.\n{itens}"
                )
            else:
                msg = f"⚠️ {self.rotulo}: {len(bloqueios)} achado(s) — modo não estrito, segue como ressalva.\n{itens}"

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=msg)]),
            actions=EventActions(state_delta=delta),
        )


class StitchGeracaoAgent(BaseAgent):
    """Determinístico: gera no Stitch toda (tela, estado) que o agente de telas especificou (`tools/stitch_geracao.py`).

    O agente de telas gerava no Stitch dentro da própria resposta: priorizava, batia no teto de resposta de
    ferramenta e escrevia screenId que o projeto não tinha (auditoria de 07/10/2026). Agora ele só escreve a
    tabela «Geração no Stitch»; o código gera todas as linhas — e as do inventário que a tabela esqueceu —,
    em paralelo, e registra o screenId que o Stitch devolveu. A seção «Telas geradas no Stitch (esteira)»
    vai para o fim da cobertura dos wireframes, que o resto da esteira lê.
    """

    relatorio_key: str = "wireframes_cobertura"
    projeto_key: str = "stitch_project_id"
    design_system_key: str = "stitch_design_system"
    registro_key: str = "stitch_geracao"
    titulo_secao: str = "## Telas geradas no Stitch (esteira)"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        import asyncio

        from config import get_settings
        from tools import stitch_geracao as sg
        from tools.stitch_cliente import chamar, extrair_project_id

        state = ctx.session.state
        s = get_settings()
        relatorio = str(state.get(self.relatorio_key) or "")
        if not s.is_stitch_enabled or not relatorio.strip():
            motivo = "Stitch desligado" if not s.is_stitch_enabled else "sem cobertura dos wireframes"
            yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                        content=types.Content(role="model", parts=[types.Part(text=f"⏭️ Geração no Stitch: {motivo}.")]))
            return

        corpo = relatorio.split(self.titulo_secao)[0].rstrip()  # a seção da rodada anterior sai antes de escrever a nova
        spec = str(state.get("spec_missao") or "")
        desktop = bool(re.search(r"viewport\W{0,6}:\W{0,3}desktop", spec, re.I))
        itens = sg.completar(sg.itens_do_relatorio(corpo), str(state.get("jornada_telas") or ""), desktop_padrao=desktop)
        projeto = str(state.get(self.projeto_key) or "") or extrair_project_id(str(state.get("stitch_links") or "")) or None
        titulo = f"{extrair_slug(spec) or 'missão'} — wireframes lo-fi"

        def chamar_com_prazo(ferramenta: str, argumentos: Dict[str, Any]) -> Dict[str, Any]:
            prazo = s.stitch_prazo_geracao_s if ferramenta == "generate_screen_from_text" else 120
            return chamar(ferramenta, argumentos, timeout=prazo)

        try:
            saida = await asyncio.to_thread(
                sg.gerar, itens, dict(state.get(self.registro_key) or {}), projeto=projeto,
                design_system=str(state.get(self.design_system_key) or "") or None, titulo_projeto=titulo,
                chamar=chamar_com_prazo, paralelo=s.stitch_paralelo)
        except Exception as exc:  # projeto que não se cria não derruba a etapa: a cobertura conta o que faltou
            yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                        content=types.Content(role="model", parts=[types.Part(text=f"⚠️ Geração no Stitch falhou: {exc}")]))
            return

        from tools.stitch_mcp import url_do_projeto

        delta = {
            self.projeto_key: saida["projeto"],
            self.design_system_key: saida["design_system"] or "",
            self.registro_key: saida["registro"],
            self.relatorio_key: corpo + "\n\n" + sg.relatorio(saida, url_do_projeto(saida["projeto"])),
            # a cobertura do A080 lê: falta por recusa do Stitch (cota) é pendência externa, não retrabalho de telas
            "stitch_geracao_recusa": sg.recusa_da_geracao(saida),
        }
        faltaram = [r for r in saida["resultado"] if not r["screen_id"]]
        msg = (f"🖼️ Stitch: {len(saida['resultado']) - len(faltaram)} de {len(saida['resultado'])} (tela, estado) no projeto "
               f"`{saida['projeto']}`" + (f" — faltaram {', '.join(sg.titulo(r) for r in faltaram)}" if faltaram else "") + ".")
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    content=types.Content(role="model", parts=[types.Part(text=msg)]),
                    actions=EventActions(state_delta=delta))


class RastreabilidadeAgent(BaseAgent):
    """Determinístico: a matriz requisito do produto × artefato (`tools/rastreabilidade.py`).

    Cada gate conferia um par de documentos; ninguém respondia, num lugar que o PO lê, se o que o produto
    especificou chegou inteiro ao fim. Roda no fim do design (o que já existe; o resto fica `—`) e no fim
    do dev, e vai ao dossiê e aos artefatos da sessão. Não reprova sozinho: cada perda já tem o gate do seu
    documento, com dono e loop — a matriz é o que mostra que nenhuma passou.
    """

    report_key: str = "rastreabilidade_report"
    status_key: str = "rastreabilidade_status"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from tools import rastreabilidade as rb

        state = ctx.session.state
        resultado = rb.matriz(dict(state))
        missao = extrair_slug(str(state.get("spec_missao") or state.get("one_pager") or "")) or ""
        delta = {
            self.report_key: rb.relatorio(resultado, missao),
            self.status_key: resultado["status"],
            f"{self.status_key}_envelope": {"agente": rb.AGENTE, "status": resultado["status"],
                                            "achados": resultado["achados"], "precisa_humano": False},
        }
        marca = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}[resultado["status"]]
        msg = (f"{marca} Rastreabilidade: {len(resultado['requisitos'])} requisito(s) do produto conferidos em cada artefato"
               + "".join(f"\n- {'⛔' if a['severidade'] == 'bloqueio' else '⚠️'} {a['resumo'][:200]}"
                         for a in resultado["achados"][:12]))
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    content=types.Content(role="model", parts=[types.Part(text=msg)]),
                    actions=EventActions(state_delta=delta))


class CopyPreservadaAgent(BaseAgent):
    """Determinístico: o que a passada 1 da copy escreveu e a revisão não reemitiu volta, sem mudança.

    O prompt da revisão manda reemitir prompts, schemas, banco curado e o roteiro do podcast "da passada 1,
    sem mudança" — e nas 8 sessões do bucket com design a revisão os descartou. O PRD, o brief e o banco
    leem só a revisada. Copiar sem mudança é trabalho do código: aqui as seções faltantes são reanexadas
    (`tools/preservacao.reanexar_secoes`) e o evento diz quais.
    """

    antes_key: str = "copy_strings"
    depois_key: str = "copy_strings_revisada"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from tools.preservacao import reanexar_secoes

        state = ctx.session.state
        antes, depois = str(state.get(self.antes_key) or ""), str(state.get(self.depois_key) or "")
        if not antes.strip() or not depois.strip():
            return
        r = reanexar_secoes(antes, depois)
        if not r["reanexadas"]:
            msg, delta = "✅ Copy revisada: nenhuma seção da passada 1 ficou para trás.", {}
        else:
            msg = f"📌 Copy revisada: reanexadas da passada 1, sem mudança — {', '.join(r['reanexadas'])}."
            delta = {self.depois_key: r["texto"]}
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    content=types.Content(role="model", parts=[types.Part(text=msg)]),
                    actions=EventActions(state_delta=delta))


class CoberturaTelasAgent(BaseAgent):
    """Determinístico: toda tela do inventário da jornada em todo artefato que a desenha, por ID.

    A auditoria de 07/10/2026 achou o Stitch com 27% a 68% das telas — o prompt mandava priorizar — e
    o protótipo com um quadro por tela em vez de um por estado, enquanto os gates aprovavam: comparavam
    contagem, não IDs. Aqui a lista vem da tabela «Seção 3» da jornada (`tools/telas.py`) e cada
    derivado (fluxo, copy revisada, cobertura, protótipo) é conferido por conjunto; cada falta sai com o
    dono do conserto, e o `A089QaAfirmacoes` a leva ao retrabalho.
    """

    report_key: str = "cobertura_telas_report"
    status_key: str = "cobertura_telas_status"
    rotulo: str = "Cobertura de telas"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from tools import telas

        state = ctx.session.state
        resultado = telas.cobertura(dict(state))
        missao = extrair_slug(str(state.get("spec_missao") or state.get("one_pager") or "")) or ""
        delta = {
            self.report_key: telas.relatorio(resultado, missao),
            self.status_key: resultado["status"],
            f"{self.status_key}_envelope": {"agente": telas.AGENTE, "status": resultado["status"],
                                            "achados": resultado["achados"], "precisa_humano": False},
        }
        n = len(resultado["inventario"]["telas"])
        marca = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}[resultado["status"]]
        msg = f"{marca} {self.rotulo}: {n} tela(s) no inventário." + "".join(
            f"\n- {'⛔' if a['severidade'] == 'bloqueio' else '⚠️'} [{a['agente_responsavel']}] {a['resumo'][:220]}"
            for a in resultado["achados"])
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    content=types.Content(role="model", parts=[types.Part(text=msg)]),
                    actions=EventActions(state_delta=delta))


class PrototipoLintAgent(BaseAgent):
    """Determinístico: confere o HTML do protótipo contra o inventário de telas da jornada.

    O QA de design julgava o protótipo lendo o RELATÓRIO do agente que o construiu — nenhuma
    conferência tocava o arquivo. Um protótipo com metade das telas, com `TODO` na tela de pico
    ou que nem abre passava, desde que o relatório dissesse que estava pronto.

    As perguntas aqui são de fato (o arquivo abre? as telas declaradas estão nele? sobrou
    marcador de rascunho?) e por isso cabem em código; julgar se a tela está BOA continua com
    o QA. Informativo: alimenta o QA, não trava a esteira sozinho.
    """

    arquivo_key: str = "prototipo_arquivo"
    inventario_key: str = "jornada_telas"
    telas_key: str = "wireframes_cobertura"
    report_key: str = "prototipo_lint_report"
    status_key: str = "prototipo_lint_status"
    rotulo: str = "Lint do protótipo"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        import re as _re
        from tools import prototipo as lint

        state = ctx.session.state
        html = str(state.get(self.arquivo_key, "") or "")
        inventario = str(state.get(self.inventario_key, "") or "")
        declaradas = sorted(set(_re.findall(r"\bE\d-(?:ALU|PROF|SIS)-\d{2}\b", inventario)))

        resultado = lint.validar(html, declaradas)
        # A coluna `Componentes do DS` das telas, contra o inventário do storybook: fato conferível,
        # que o QA recebia como afirmação (32% eram nomes que o DS não tem).
        from tools.componentes_ds import validar as validar_componentes
        resultado["achados"] += validar_componentes(str(state.get(self.telas_key, "") or ""),
                                                    str(state.get("spec_missao", "") or ""))
        for a in resultado["achados"]:  # sem dono o ticket ia para "sem rota"
            a.setdefault("agente_responsavel", "telas" if a.get("codigo") == "componente-inexistente" else "prototipo")
        if any(a["severidade"] == "bloqueio" for a in resultado["achados"]):
            resultado["status"] = "bloqueado"
        elif resultado["achados"] and resultado["status"] == "aprovado":
            resultado["status"] = "amarelo"
        delta = {
            self.report_key: lint.relatorio(resultado, extrair_slug(str(state.get("spec_missao") or state.get("one_pager") or "")) or ""),
            self.status_key: resultado["status"],
            f"{self.status_key}_envelope": {"agente": lint.AGENTE, "status": resultado["status"],
                                            "achados": resultado["achados"]},
        }
        marca = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}[resultado["status"]]
        msg = (f"{marca} {self.rotulo}: {len(resultado['telas'])} tela(s) no arquivo"
               + (f" contra {len(declaradas)} declaradas" if declaradas else "")
               + (f" · {len(resultado['achados'])} achado(s)" if resultado["achados"] else ""))

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=msg)]),
            actions=EventActions(state_delta=delta),
        )


class EscopoBancaAgent(BaseAgent):
    """Grava em `escopo_banca` onde a banca está rodando e o que ela pode fazer ali (`tools/banca.ESCOPOS`).

    Os prompts das dimensões são os mesmos nas quatro posições — fim de produto, fim de design, entrada do dev e dev —
    e leem `{escopo_banca?}`. Roda logo antes das dimensões, porque a chave é a mesma para todas as posições."""

    posicao: str

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from tools import banca as bnc

        texto = bnc.ESCOPOS[self.posicao]
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    actions=EventActions(state_delta={bnc.KEY_ESCOPO: texto}))


class ConsolidacaoBancaAgent(BaseAgent):
    """Determinístico: o veredito da banca é a pior das cinco dimensões, contada em código.

    Era um `LlmAgent` cuja própria descrição prometia "veredito determinístico 🟢/🟡/🔴". Em 14
    execuções leu 122 achados e aprovou 14 vezes — e a lista de bloqueantes que ele carregava
    no prompt omitia `DES-14` (visão do professor completa), que os critérios declaram
    bloqueante desde 22/09/2026. A visão do professor podia faltar inteira e a banca liberava.

    A lista agora é lida dos próprios arquivos de `references/criterios-dev/`: não há segunda
    cópia para divergir. Dimensão sem envelope legível **bloqueia** — uma das cinco não ter
    respondido é exatamente o caso em que aprovar é mais caro.
    """

    fontes: List[str] = Field(default_factory=list)
    report_key: str = "validacao_dev_report"
    status_key: str = "dev_status"
    rotulo: str = "Banca de dev"
    #: Grava o status aqui mesmo. A banca de dev tem um gate de envelope depois (A111) que o grava; as bancas de fim
    #: de produto, fim de design e entrada do dev não têm.
    gravar_status: bool = False
    titulo: str = "Validação de insumos"
    #: Nome da etapa → chave do envelope da banca dela. Na entrada do dev, o critério que reprova aqui e passou na
    #: etapa vai a uma seção própria do relatório (decisão do usuário, 08/10/2026).
    comparar_com: Dict[str, str] = Field(default_factory=dict)

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from tools import banca as bnc

        state = ctx.session.state
        missao = extrair_slug(str(state.get("spec_missao") or state.get("one_pager") or "")) or ""
        envelopes = {chave: extrair_envelope(str(state.get(chave, "") or "")) for chave in self.fontes}
        from tools.citacoes import texto_dos_documentos

        resultado = bnc.consolidar(envelopes, texto_dos_documentos(state, bnc.DOCUMENTOS_DA_BANCA))
        divergencias = bnc.divergencias_com_etapas(
            resultado, {nome: state.get(chave) for nome, chave in self.comparar_com.items()}) if self.comparar_com else []
        texto = bnc.relatorio(resultado, missao, self.titulo, divergencias)

        delta = {
            self.report_key: texto,
            f"{self.status_key}_envelope": {"agente": bnc.AGENTE, "status": resultado["status"],
                                            "achados": resultado["achados"], "divergencias": divergencias},
        }
        if self.gravar_status:
            delta[self.status_key] = resultado["status"]
        marca = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}[resultado["status"]]
        dims = " · ".join(f"{k.replace('validacao_', '')}: {marca_d}"
                          for k, marca_d in ((k, {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}[v["status"]])
                                             for k, v in resultado["por_dimensao"].items()))
        msg = f"{marca} {self.rotulo}: {resultado['status']} — {dims}"

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=msg)]),
            actions=EventActions(state_delta=delta),
        )


def _pedidos_de_produto(state: Any) -> str:
    """Os pedidos do PO que produto atende — os de refazer registrados e o da execução corrente — num texto só."""
    registrados = [str(p.get("texto") or "") for p in (state.get("pedidos_do_po") or [])
                   if isinstance(p, dict) and str(p.get("etapa") or "") in ("produto", "")]
    from pipeline.reexecucao import texto_do_pedido

    return "\n\n".join(registrados + [texto_do_pedido(str(state.get("pedido_correcao", "") or ""))]).strip()


class DocumentoAusente(RuntimeError):
    """O autor de um documento obrigatório terminou sem texto, mesmo depois de chamado de novo."""


class DocumentoObrigatorioAgent(BaseAgent):
    """Para a etapa, com mensagem que se lê, quando um documento de que o resto depende não existe.

    Na exp03ef1b (08/10/2026) o A014 terminou sem texto duas vezes; a esteira seguiu e o gate estrutural quebrou ao
    montar o prompt com "Context variable not found: `one_pager`" — e o PO viu só isso. Aqui a parada é no lugar
    certo e diz quem ficou mudo. Fica depois do loop que já chamou o autor de novo.
    """

    chave: str
    autor: str

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        if not str(ctx.session.state.get(self.chave, "") or "").strip():
            from agents.callbacks import PREFIXO_BLOQUEIO_MODELO

            corte = str(ctx.session.state.get(f"{PREFIXO_BLOQUEIO_MODELO}{self.autor}") or "")
            motivo = (" O modelo cortou a resposta" + (" pelo filtro de recitação (texto publicado transcrito por extenso)"
                                                      if "recitação" in corte else "") + ".") if corte else ""
            raise DocumentoAusente(
                f"o agente {self.autor} terminou sem texto nas duas tentativas, e sem `{self.chave}` a etapa não "
                f"continua.{motivo} Nada foi alterado; tente de novo — se repetir, veja o relatório de execução")
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    content=types.Content(role="model", parts=[types.Part(text=f"✅ `{self.chave}` presente.")]))


class RastroCheckAgent(BaseAgent):
    """Gate determinístico de rastro: `modo` decide a verificação de `tools/rastro.py`.

    - ``lacunas``: varre `fontes` (documentos do estado) atrás de marcadores de lacuna e
      atribui cada um a `input · produto · design · dev · plataforma`;
    - ``manifesto``: ficha do manifesto no bloco 0 da spec (`spec_key`);
    - ``telemetria``: contrato de evento e proibições de arquitetura no handoff (`fonte_key`).

    `bloqueado` + `estrito` → pipeline bloqueado (jusante pulado). `amarelo` segue.
    """

    modo: str  # lacunas | manifesto | telemetria | evidencia | evidencia_one_pager | perguntas | kpis | prd | one_pager | consistencia | conteudo | aprovado_spec | aprovado_prd | aprovado_pedagogico | aprovado_resumido | aprovado_spec_design
    report_key: str
    status_key: str
    rotulo: str = "Rastro"
    estrito: bool = True
    spec_key: str = "spec_missao"
    fonte_key: str = "handoff_dev"
    fontes: List[Dict[str, str]] = Field(default_factory=list)
    agente: str = "rastro-lacunas"
    #: Modo `lacunas`: a etapa que roda o rastro (`produto` · `design` · `dev`). Ela só bloqueia
    #: pelo que é dela; o de outra etapa sai 🟡 (`tools/rastro._severidade_na_etapa`).
    etapa: Optional[str] = None

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        missao = extrair_slug(str(state.get("spec_missao") or state.get("one_pager") or "")) or ""
        if self.modo == "one_pager":
            from tools import decisoes

            # Roda antes do gate estrutural, a cada rodada: contrato de plataforma (canal de
            # sala, estado no servidor), SAEB no ano certo e origem dos números. Não bloqueia
            # sozinho — o gate converte cada achado em ❌ pelo critério e o revisor aplica.
            resultado = validar_one_pager(
                str(state.get("one_pager", "") or ""),
                nucleo=str(state.get("nucleo_narrativo", "") or ""),
                briefing=str(state.get("briefing", "") or ""),
                registro_do_po=decisoes.ha_registro_do_po(dict(state)),
                one_pager_po=str(state.get("one_pager_po", "") or ""),
                pedidos=_pedidos_de_produto(state),
                decisoes_do_po=state.get("decisoes_do_po") or [],
            )
            relatorio = relatorio_contrato_produto(resultado, missao)
        elif self.modo == "manifesto":
            # o briefing entra para conferir a seção do DS que ele fixou (exp03ef1b, 07/10/2026)
            resultado = validar_manifesto(str(state.get(self.spec_key, "") or ""),
                                          briefing=str(state.get("briefing", "") or ""),
                                          one_pager_po=str(state.get("one_pager_po", "") or ""))
            relatorio = relatorio_manifesto(resultado, missao)
        elif self.modo == "telemetria":
            resultado = validar_telemetria(str(state.get(self.fonte_key, "") or ""))
            relatorio = relatorio_telemetria(resultado, missao, rodada=int(state.get("handoff_rodada", 0) or 0) + 1)
        elif self.modo == "evidencia":
            # Coerência pedagógica do bloco 9/11 da spec: grau `scored` com dois sinais, toda
            # habilidade com momento em tela e medida ligada, gabarito declarado no servidor.
            from tools import evidencia as ev

            resultado = ev.validar(str(state.get(self.spec_key, "") or ""))
            relatorio = ev.relatorio(resultado, missao)
        elif self.modo == "evidencia_one_pager":
            # O §12a onde ele nasce, a cada rodada dos comitês: forma antes de voto (comitês de 15/10/2026).
            from tools import evidencia as ev

            resultado = ev.conferir_one_pager(str(state.get("one_pager", "") or ""))
            relatorio = ev.relatorio_one_pager(resultado, missao)
        elif self.modo == "perguntas":
            # As cinco perguntas de produto do sub-bloco 9f, onde a pergunta NASCE. Conferir aqui
            # custa uma reescrita da spec; deixar passar custa o PRD inteiro duas etapas adiante.
            from tools import kpis as kp

            resultado = kp.validar_9f(str(state.get(self.spec_key, "") or ""))
            relatorio = kp.relatorio_9f(resultado, missao)
        elif self.modo == "kpis":
            # Coerência KPI ↔ evento ↔ tela no PRD.
            from tools import kpis as kp

            resultado = kp.validar_kpis(str(state.get("prd_final", "") or ""),
                                        str(state.get(self.spec_key, "") or ""),
                                        one_pager=str(state.get("one_pager", "") or ""))
            relatorio = kp.relatorio(resultado, missao)
        elif self.modo == "consistencia":
            # Jornada, fluxo, copy revisada e protótipo contra o glossário canônico da spec. O mesmo
            # órgão com quatro nomes e o beneficiário de 14 anos virando coordenador (exp09ef1b) eram
            # defeitos de documento lido sozinho: cada um estava bem escrito, nenhum batia com o outro.
            from tools import consistencia as cons

            from tools import conteudo_aprovado as ca

            resultado = cons.validar_estado(dict(state))
            # e o texto que o PO aprovou palavra por palavra — Canal B e debate — chegou literal à copy
            # (a exp01ef1b chegou a dev com a pergunta 1 do debate reescrita, 07/10/2026)
            resultado["achados"] += ca.validar_copy(str(state.get("copy_strings_revisada", "") or ""),
                                                    str(state.get("one_pager", "") or ""))
            # e o Canal B na prancha CAA e nas telas do protótipo (só a copy era conferida)
            resultado["achados"] += ca.validar_literais_design(str(state.get("camada_caa", "") or ""),
                                                               str(state.get("prototipo_arquivo", "") or ""),
                                                               str(state.get("one_pager", "") or ""))
            if any(a["severidade"] == "bloqueio" for a in resultado["achados"]):
                resultado["status"] = "bloqueado"
            elif resultado["achados"] and resultado["status"] == "aprovado":
                # o texto de tela do §4 reescrito é 🟡: sem isto o achado ia ao relatório com a etapa ✅
                resultado["status"] = "amarelo"
            relatorio = cons.relatorio(resultado, missao)
        elif self.modo == "conteudo":
            # O banco escrito contra o brief que o declara, e o Status do brief contra o vocabulário: na
            # exp09ef1b o brief dizia "Homologado" para um banco que ninguém escreveu.
            from tools import conteudo as ct
            from tools.consistencia import validar as validar_glossario

            spec = str(state.get(self.spec_key, "") or "")
            banco = str(state.get("banco_conteudo", "") or "")
            resultado = ct.validar(str(state.get("brief_assets", "") or ""), banco, spec)
            # o banco escreve nomes, idades e números: o mesmo glossário que confere a copy o confere
            resultado["achados"] += validar_glossario(spec, {"banco de conteúdo": banco}, exigir_glossario=False,
                                                      etapa="dev", aprovado=str(state.get("one_pager", "") or ""))["achados"]
            # o roteiro do podcast que vai para gravação é o do PO (o banco da exp01ef1b escreveu outro)
            from tools import conteudo_aprovado as ca

            resultado["achados"] += ca.validar_banco(banco, str(state.get("one_pager", "") or ""))
            # missão de chat: a árvore de intenções que o interlocutor simulado responde (auditoria de 08/10/2026)
            from tools.prd_codavel import validar_intencoes

            resultado["achados"] += [{**a, "etapa": "dev"} for a in validar_intencoes(banco, spec)]
            if any(a["severidade"] == "bloqueio" for a in resultado["achados"]):
                resultado["status"] = "bloqueado"
            elif resultado["achados"] and resultado["status"] == "aprovado":
                resultado["status"] = "amarelo"
            relatorio = ct.relatorio(resultado, missao)
        elif self.modo == "prd":
            # Dois exames no mesmo passo: os marcadores que o redator deixou (lacunas) e as
            # contradições que ele não viu (consistência). Um PRD pode não ter lacuna nenhuma e
            # ainda declarar dois prefixos de tabela ou deixar um requisito P0 sem teste — e é o
            # segundo caso que faz quem codifica escolher um caminho ao acaso.
            r_lacunas = varrer_lacunas(self.fontes, dict(state))
            r_consistencia = validar_prd(str(state.get("prd_final", "") or ""),
                                         spec=str(state.get(self.spec_key, "") or ""),
                                         banco=str(state.get("banco_conteudo", "") or ""),
                                         aprovado=str(state.get("one_pager", "") or ""))
            # O PRD contra o design da mesma sessão (exp01ef1b, 07/10/2026: 0 de 90 chaves de copy, 1 de 28
            # assets, 0 de 17 estados, status de gate escrito pelo redator): tela, chave, asset, estado,
            # status de gate, critério dos P0, schema citado e proposta da spec (`tools/cobertura_design.py`).
            from tools import cobertura_design as cdz

            r_design = cdz.validar(str(state.get("prd_final", "") or ""),
                                   {**dict(state), "spec_missao": state.get(self.spec_key, "")})
            # O PRD dá para codar: rotas do molde com Zod e erros, IA com prompt e schema, DDL, ficha de evidência com
            # regra sobre colunas e a árvore do chat (`tools/prd_codavel.py`, auditoria de 08/10/2026)
            from tools import prd_codavel as pc

            r_codavel = pc.validar(str(state.get("prd_final", "") or ""), str(state.get(self.spec_key, "") or ""),
                                   str(state.get("banco_conteudo", "") or ""), handoff=str(state.get("handoff_dev", "") or ""))
            ordem = ("bloqueado", "amarelo", "aprovado")
            resultado = {
                "status": min((r_lacunas["status"], r_design["status"], r_consistencia["status"], r_codavel["status"]),
                              key=ordem.index),
                "achados": (list(r_lacunas["achados"]) + list(r_design["achados"]) + list(r_consistencia["achados"])
                            + list(r_codavel["achados"])),
            }
            relatorio = (
                relatorio_lacunas(r_lacunas, self.rotulo, missao, agente=self.agente)
                + "\n\n---\n\n" + cdz.relatorio(r_design, missao)
                + "\n\n---\n\n" + pc.relatorio(r_codavel, missao)
                + "\n\n---\n\n" + relatorio_prd(r_consistencia, missao)
                # o envelope é o ÚLTIMO bloco json: o combinado, para o dossiê ver os três exames
                + "\n\n```json\n" + json.dumps({"agente": "prd-check", "missao": missao, "status": resultado["status"],
                                                 "achados": resultado["achados"]}, ensure_ascii=False) + "\n```\n"
            )
        elif self.modo in ("aprovado_spec", "aprovado_prd", "aprovado_pedagogico", "aprovado_resumido"):
            # O documento contra o one-pager que o PO aprovou: habilidades, tempo em tela, podcast e, no
            # PRD e no pedagógico, os caminhos de artefato. A exp06ef1b perdeu uma habilidade e cinco
            # minutos de tela na spec, e o PRD seguiu a spec sem nenhum gate acusar (06/10/2026).
            from pipeline.artifacts import caminhos_de_artefato
            from tools import conteudo_aprovado as ca

            one_pager = str(state.get("one_pager", "") or "")
            spec = str(state.get(self.spec_key, "") or "")
            if self.modo == "aprovado_spec":
                resultado, documento = ca.validar_spec(spec, one_pager), "spec"
                # o glossário que a spec escreve não pode proibir o que o PO escreveu (exp01ef1b, 08/10/2026: proibiu
                # o título e uma fala do podcast aprovados, e o design bloqueou por obedecer ou por desobedecer)
                from tools.consistencia import glossario_contra_o_aprovado

                conflitos = glossario_contra_o_aprovado(spec, one_pager)
                if conflitos:
                    resultado = {**resultado, "status": "bloqueado", "achados": resultado["achados"] + conflitos}
            elif self.modo == "aprovado_prd":
                resultado = ca.validar_prd(str(state.get("prd_final", "") or ""), spec, one_pager,
                                           caminhos_de_artefato())
                documento = "PRD"
            elif self.modo == "aprovado_resumido":
                # o resumido é o que o time de produto lê para aprovar; nada o comparava ao canônico (07/10/2026)
                resultado = ca.validar_resumido(str(state.get("one_pager_resumido", "") or ""), spec, one_pager)
                documento = "one-pager resumido"
            else:
                resultado = ca.validar_pedagogico(str(state.get("one_pager_pedagogico", "") or ""), spec,
                                                  one_pager, caminhos_de_artefato())
                documento = "one-pager pedagógico"
            # quem decidiu: decisão atribuída ao PO sem registro dele bloqueia; proposta do agente
            # deixa a etapa 🟡 (exp03ef1b, 07/10/2026: "aprovado pelo PO" sem parecer nenhum)
            from tools import decisoes as dec

            chave = {"aprovado_spec": self.spec_key, "aprovado_prd": "prd_final",
                     "aprovado_resumido": "one_pager_resumido"}.get(self.modo, "one_pager_pedagogico")
            resultado = dec.com_achados(resultado, dec.achados(
                str(state.get(chave, "") or ""), f"A {documento}" if documento == "spec" else f"O {documento}",
                dec.ha_registro_do_po(dict(state)),
                etapa="produto" if self.modo in ("aprovado_spec", "aprovado_resumido") else "dev"))
            relatorio = ca.relatorio(resultado, documento, missao)
        elif self.modo == "one_pager_po":
            # O one-pager que o PO anexou é a missão: cada trecho dele está no gerado, ou saiu porque o pedido
            # mandou (exp06ef1b, 08/10/2026: 253 de 304 trechos reescritos num pedido de três correções).
            from tools import one_pager_po as op

            # o brief de escopo sai do `one_pager` antes do gate estrutural (A023BriefEscopoSplit): o do PO é conferido
            # contra os dois juntos, senão as linhas do brief dele contariam como perdidas
            gerado = "\n\n".join(str(state.get(k, "") or "") for k in ("one_pager", "brief_escopo"))
            from tools.comite import texto_votos

            resultado = op.conferir(str(state.get("one_pager_po", "") or ""), gerado,
                                    briefing=str(state.get("briefing", "") or ""), pedidos=_pedidos_de_produto(state),
                                    votos=texto_votos(state))
            relatorio = op.relatorio(resultado, missao)
        elif self.modo == "aprovado_spec_design":
            # a spec que o D0 e o D9 reescreveram: só o que eles pioraram, com o dono do D0 (07/10/2026)
            from tools import conteudo_aprovado as ca

            resultado = ca.validar_spec_consolidada(str(state.get(self.spec_key, "") or ""),
                                                    str(state.get("spec_missao_gate0", "") or ""),
                                                    str(state.get("one_pager", "") or ""))
            relatorio = ca.relatorio(resultado, "spec consolidada", missao)
        else:
            resultado = varrer_lacunas(self.fontes, dict(state), etapa_corrente=self.etapa)
            relatorio = relatorio_lacunas(resultado, self.rotulo, missao, agente=self.agente)

        status = resultado["status"]  # aprovado | amarelo | bloqueado
        delta: Dict[str, Any] = {
            self.report_key: relatorio,
            self.status_key: status,
            f"{self.status_key}_envelope": extrair_envelope(relatorio) or {},
        }
        bloqueios = [a for a in resultado["achados"] if a["severidade"] == "bloqueio"]
        avisos = [a for a in resultado["achados"] if a["severidade"] != "bloqueio"]
        if status == "aprovado":
            msg = f"✅ {self.rotulo}: conforme."
            limpar_degradacao(state, delta, self.rotulo)
        elif self.modo == "one_pager":
            # Aqui o veredito é do gate estrutural; este nó só entrega a lista para ele aplicar.
            todos = bloqueios + avisos
            msg = f"{'⛔' if bloqueios else '🟡'} {self.rotulo}: {len(todos)} achado(s) para o gate estrutural aplicar e o revisor corrigir.\n" + "\n".join(
                f"- {'⛔' if a['severidade'] == 'bloqueio' else '⚠️'} {(a.get('resumo') or '').split(chr(10))[0]}" for a in todos
            )
        elif status == "amarelo":
            # Amarelo é "passa com ressalvas": o gate deixou de reprovar. Se ele reprovou numa
            # rodada anterior do mesmo loop (PRD 🔴 na 1, 🟡 na 2), a marca precisa cair aqui
            # também — senão a execução sai `pipeline_bloqueado` com zero impedimento e o
            # diagnóstico lista o PRD como provisório (visto em 2026-09-21, exp06ef1b).
            limpar_degradacao(state, delta, self.rotulo)
            msg = f"🟡 {self.rotulo}: {len(avisos)} pendência(s) que não são desta etapa fechar — a esteira segue 🟡, não verde.\n" + "\n".join(f"- ⚠️ {a.get('resumo') or a.get('trecho', '')}" for a in avisos)
        else:
            itens = "\n".join(f"- ⛔ [{a.get('etapa', 'dev')}] {a.get('resumo') or a.get('trecho', '')}" for a in bloqueios)
            if self.estrito:
                registrar_degradacao(
                    state, delta, self.rotulo,
                    f"{self.rotulo} reprovado ({len(bloqueios)} lacuna(s))",
                )
                msg = (
                    f"⛔ {self.rotulo}: reprovado — {len(bloqueios)} lacuna(s). "
                    f"O PRD sai mesmo assim, marcado, e o diagnóstico final lista cada lacuna com o dono.\n{itens}"
                )
            else:
                msg = f"⚠️ {self.rotulo}: {len(bloqueios)} lacuna(s) — modo não estrito, segue como ressalva.\n{itens}"

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=msg)]),
            actions=EventActions(state_delta=delta),
        )


class AnexoAprovadoAgent(BaseAgent):
    """Cola no fim de `chave` as seções do one-pager aprovado, literais (`tools/conteudo_aprovado.py`).

    Roda depois do loop do documento, para os gates do loop lerem só o que o redator escreveu. Troca
    o anexo de uma execução anterior em vez de somar outro. Documento vazio ou mensagem de pulo do
    ADK não recebe anexo: o PRD de um pipeline bloqueado continua sendo só o aviso.
    """

    chave: str
    secoes: List[int] = Field(default_factory=list)
    rotulo: str = "Anexo do conteúdo aprovado"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from pipeline.artifacts import e_mensagem_de_pulo
        from tools import conteudo_aprovado as ca

        state = ctx.session.state
        documento = state.get(self.chave)
        one_pager = str(state.get("one_pager", "") or "")
        delta: Dict[str, Any] = {}
        if not documento or e_mensagem_de_pulo(documento):
            msg = f"⏭️ {self.rotulo}: sem documento para anexar."
        else:
            from pipeline.artifacts import desembrulhar_cerca

            # a cerca ```markdown em volta do documento sai antes: anexo colado depois dela impedia a gravação de
            # reconhecer o invólucro, e o arquivo abria como bloco de código
            novo = ca.com_anexo(desembrulhar_cerca(str(documento)), one_pager, self.secoes)
            delta[self.chave] = novo
            msg = (f"📎 {self.rotulo}: seções {', '.join(f'§{n}' for n in self.secoes)} do one-pager aprovado, literais."
                   if ca.TITULO_ANEXO in novo else f"⚠️ {self.rotulo}: o one-pager não tem nenhuma das seções.")
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=msg)]),
            actions=EventActions(state_delta=delta),
        )


class ConteudoAprovadoAgent(BaseAgent):
    """Grava em `conteudo_aprovado` as seções literais do one-pager aprovado (`tools/conteudo_aprovado.py`).

    Seis agentes de design e de dev — fluxo, CAA, telas, revisão da copy, QA e banco de conteúdo — não
    recebiam o one-pager: o que a spec não trazia não existia para eles. Na exp01ef1b (07/10/2026) as
    travas do professor, o podcast e a redação do debate se perderam nesse caminho. Roda no começo do
    design e do dev, para valer também quando só uma das etapas é refeita.
    """

    chave: str = "conteudo_aprovado"
    secoes: List[int] = Field(default_factory=list)
    #: Onde guardar o retrato das seções aprovadas que esta etapa leu. Na execução seguinte da etapa, o que mudou
    #: entre o retrato e o one-pager atual vai para `mudancas_no_aprovado`, que os autores recebem junto da versão
    #: anterior (`agents/base.py`). A chave fica fora das listas de limpeza: tem de sobreviver ao refazer de produto.
    chave_base: str = ""

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from tools import conteudo_aprovado as ca

        state = ctx.session.state
        literal = ca.secoes_literais(str(state.get("one_pager", "") or ""), self.secoes)
        texto = ca.NOTA_CONTEUDO_APROVADO + "\n\n" + literal if literal else ""
        delta: Dict[str, Any] = {self.chave: texto}
        msg = (f"📎 Conteúdo aprovado: §{', §'.join(str(n) for n in self.secoes)} do one-pager, literais, para os agentes "
               f"que não leem o one-pager." if texto else "⏭️ Conteúdo aprovado: one-pager sem as seções.")
        if self.chave_base:
            mudancas = ca.mudancas_no_aprovado(str(state.get(self.chave_base, "") or ""), literal)
            delta[ca.KEY_MUDANCAS] = mudancas
            if literal:
                delta[self.chave_base] = literal
            if mudancas:
                msg += (f" O one-pager mudou desde a última execução desta etapa: {mudancas.count(chr(10) + '- ')} "
                        "linha(s) vão aos autores junto da versão anterior deles.")
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=msg)]),
            actions=EventActions(state_delta=delta),
        )


class JuizDeAchadosAgent(BaseAgent):
    """O regex acha, o LLM decide, o código confere a citação (`tools/juiz_achados.py`).

    Roda logo depois de um gate determinístico. Se ele emitiu achado do tipo "afirma ou cita para
    vedar?", separa as linhas que o dispararam, pergunta ao juiz (o sub-agente) e retira o achado
    só quando o juiz julga todas como citação para descartar E cada citação existe no documento.
    Sem candidato, o juiz não roda — não custa chamada. Nunca cria achado.
    """

    status_key: str
    report_key: str
    fonte_key: str
    gate_rotulo: str = ""
    rotulo: str = "Juiz de achados"
    entrada_key: str = "juiz_achados_entrada"
    saida_key: str = ""  # vazio: o `output_key` do juiz

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from tools import juiz_achados as ja

        state = ctx.session.state
        relatorio = str(state.get(self.report_key, "") or "")
        envelope = dict(state.get(f"{self.status_key}_envelope") or extrair_envelope(relatorio) or {})
        achados = [a for a in (envelope.get("achados") or []) if isinstance(a, dict)]
        documento = str(state.get(self.fonte_key, "") or "")
        cands = ja.candidatos(achados, documento)
        if not cands or not self.sub_agents:
            return

        entrada = json.dumps(cands, ensure_ascii=False, indent=1)
        state[self.entrada_key] = entrada
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    actions=EventActions(state_delta={self.entrada_key: entrada}))
        juiz = self.sub_agents[0]
        async for evento in juiz.run_async(ctx):
            yield evento
        saida = str(ctx.session.state.get(self.saida_key or getattr(juiz, "output_key", "") or "", "") or "")

        ficam, retirados = ja.aplicar(achados, cands, saida, documento)
        delta: Dict[str, Any] = {self.entrada_key: ""}
        if retirados:
            status = ja.status_de(ficam)
            envelope.update(status=status, achados=ficam)
            delta.update({
                self.status_key: status,
                f"{self.status_key}_envelope": envelope,
                self.report_key: ja.reescrever_relatorio(relatorio, envelope, retirados),
            })
            if status != "bloqueado" and self.gate_rotulo:
                limpar_degradacao(state, delta, self.gate_rotulo)
            msg = (f"⚖️ {self.rotulo}: {len(retirados)} achado(s) retirado(s) — o texto cita para vedar "
                   f"({', '.join(r['codigo'] for r in retirados)}). Status: {status}.")
        else:
            msg = f"⚖️ {self.rotulo}: {len(cands)} candidato(s) julgado(s); nenhum retirado."
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    content=types.Content(role="model", parts=[types.Part(text=msg)]),
                    actions=EventActions(state_delta=delta))


class FidelidadeCheckAgent(BaseAgent):
    """O que o PO pediu e o briefing fixou está nos documentos? (`tools/fidelidade.py`)

    O código monta o checklist — TRAVAS, AJUSTES e perguntas de VALIDAÇÃO de todos os pedidos de
    refazer, frases entre aspas, e o direcionamento, os passos e os elementos fixos do briefing —, o
    juiz (sub-agente) responde item a item com citação, e o código confere frase literal e citação. O
    intérprete (segundo sub-agente, opcional) lê só o pedido e separa o texto ditado do texto a tirar.
    Sem nada a conferir, o juiz não roda. Pedido do PO sem prova é 🔴: no fim de produto, isso
    recusa o *de acordo*; no laço do núcleo, devolve o núcleo ao autor com o relatório.
    """

    status_key: str
    report_key: str
    rotulo: str = "Fidelidade ao pedido do PO e ao briefing"
    onde: str = ""
    documentos: List[str] = Field(default_factory=lambda: ["nucleo_narrativo", "one_pager", "spec_missao"])
    #: Os documentos são só parte do que o pedido cobre (o núcleo): sem prova é 🟡, só violação bloqueia.
    parcial: bool = False
    entrada_key: str = "fidelidade_entrada"
    documentos_key: str = "fidelidade_documentos"
    interpretacao_entrada_key: str = "interpretacao_entrada"
    #: Só os pedidos de refazer destas etapas (`pedidos_do_po[].etapa`; `""` = registro antigo, sem etapa); vazio =
    #: todos. Até 07/10/2026 o checklist de produto juntava os refazer de todas as etapas — o «AJUSTE 1 — botão da
    #: E3-ALU-02» pedido ao design reprovava o núcleo num refazer de produto seguinte —, e um refazer de design ou
    #: de dev não era conferido em lugar nenhum. Agora cada etapa confere o que foi pedido a ela.
    etapas_pedido: List[str] = Field(default_factory=list)
    #: O `pedido_correcao` corrente entra no checklist. Fora em design e dev: a correção de produto atravessa as
    #: etapas seguintes na mesma execução, e julgar documento de design por pedido de produto bloquearia o que não
    #: é dele.
    incluir_corrente: bool = True
    #: O briefing entra no checklist só em produto: é lá que ele vira missão.
    com_briefing: bool = True
    #: A etapa que os achados levam.
    etapa: str = "produto"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from tools import fidelidade as fid

        state = ctx.session.state
        registrados = [p for p in (state.get("pedidos_do_po") or []) if isinstance(p, dict)]
        if self.etapas_pedido:
            registrados = [p for p in registrados if str(p.get("etapa") or "") in self.etapas_pedido]
        pedidos = [(str(p.get("origem") or "pedido"), str(p.get("texto") or "")) for p in registrados]
        from pipeline.reexecucao import texto_do_pedido

        # só o que o PO escreveu: o cabeçalho da esteira entrava no checklist como se fosse o pedido dele
        corrente = texto_do_pedido(str(state.get("pedido_correcao", "") or ""))
        # Em design e dev o pedido corrente entra só quando a correção começou nesta etapa (`etapa_da_correcao`, gravada
        # por `pipeline.reexecucao.preparar_estado`): a correção pela triagem não vira parecer e não está em
        # `pedidos_do_po`; a de produto atravessa design e dev na mesma execução e não é deles (auditoria do PR #32).
        corrente_e_daqui = self.incluir_corrente or str(state.get("etapa_da_correcao") or "") in self.etapas_pedido
        if (corrente_e_daqui and corrente.strip()
                and not any(_norm_simples(t)[:200] in _norm_simples(corrente) for _, t in pedidos)):
            pedidos.append(("pedido de correção desta execução", corrente))
        itens = fid.montar_checklist(pedidos, str(state.get("briefing", "") or "") if self.com_briefing else "")
        docs = {k: str(state.get(k, "") or "") for k in self.documentos if str(state.get(k, "") or "").strip()}
        missao = extrair_slug(docs.get("spec_missao", "") or docs.get("nucleo_narrativo", "")) or ""

        saida = ""
        julgaveis = fid.para_o_juiz(itens)
        if julgaveis and docs and self.sub_agents:
            entrada = json.dumps(julgaveis, ensure_ascii=False, indent=1)
            corpo = "\n\n".join(f"### Documento `{k}`\n\n{v}" for k, v in docs.items())
            state[self.entrada_key] = entrada
            state[self.documentos_key] = corpo
            yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                        actions=EventActions(state_delta={self.entrada_key: entrada, self.documentos_key: corpo}))
            juiz = self.sub_agents[0]
            async for evento in juiz.run_async(ctx):
                yield evento
            saida = str(ctx.session.state.get(getattr(juiz, "output_key", "") or "", "") or "")

        # O intérprete lê só o pedido e diz que texto o PO mandou pôr e tirar — qualquer que seja o verbo, com ou sem
        # aspas; o código confere cada trecho no item e no documento (`tools.fidelidade.interpretacao`).
        lidos: Dict[str, Dict[str, Any]] = {}
        do_po = fid.para_o_interprete(itens)
        if do_po and docs and len(self.sub_agents) > 1:
            entrada_po = json.dumps(do_po, ensure_ascii=False, indent=1)
            state[self.interpretacao_entrada_key] = entrada_po
            yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                        actions=EventActions(state_delta={self.interpretacao_entrada_key: entrada_po}))
            interprete = self.sub_agents[1]
            async for evento in interprete.run_async(ctx):
                yield evento
            lidos = fid.interpretacao(
                str(ctx.session.state.get(getattr(interprete, "output_key", "") or "", "") or ""), itens)

        from pipeline.reexecucao import PREFIXO_VERSAO_ANTERIOR

        anteriores = {k: str(state.get(f"{PREFIXO_VERSAO_ANTERIOR}{k}") or "") for k in docs}
        # Numa correção, a ordem de não mexer de outra rodada não trava o pedido desta; na pontual, as trocas aplicadas
        # provam em código o que ficou como estava (`tools.fidelidade.aplicar`).
        correntes = ({o for o, t in pedidos if _norm_simples(t)[:200] in _norm_simples(corrente)}
                     | {"pedido de correção desta execução"}) if corrente.strip() else None
        edicoes = (list(state.get("edicoes_pontuais") or [])
                   if state.get(KEY_MODO_CORRECAO) == "pontual" else None)
        resultado = fid.aplicar(itens, saida, docs, etapa=self.etapa, parcial=self.parcial, anteriores=anteriores,
                                edicoes=edicoes, origens_correntes=correntes, interpretacao=lidos)
        relatorio = fid.relatorio(resultado, itens, missao, self.onde)
        envelope = extrair_envelope(relatorio) or {}
        bloqueios = sum(1 for a in resultado["achados"] if a["severidade"] == "bloqueio")
        icone = {"aprovado": "✅", "amarelo": "🟡", "bloqueado": "⛔"}[resultado["status"]]
        msg = (f"{icone} {self.rotulo}{f' ({self.onde})' if self.onde else ''}: {len(itens)} item(ns), "
               f"{len(resultado['conferidos'])} com prova, {bloqueios} bloqueio(s), "
               f"{len(resultado['achados']) - bloqueios} outro(s) achado(s).")
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    content=types.Content(role="model", parts=[types.Part(text=msg)]),
                    actions=EventActions(state_delta={
                        self.report_key: relatorio,
                        self.status_key: resultado["status"],
                        f"{self.status_key}_envelope": envelope,
                        self.entrada_key: "",
                        self.documentos_key: "",
                        self.interpretacao_entrada_key: "",
                    }))


def _bloco_com(texto: str, campo: str) -> Dict[str, Any]:
    """O último objeto JSON do texto que tem `campo` — em bloco ```json ou solto. O `extrair_envelope` só aceita
    envelope de gate (com `status`), e a resposta de um juiz não tem."""
    candidatos = re.findall(r"```(?:json)?\s*(.*?)```", texto or "", re.S) + [(texto or "").strip()]
    for bruto in reversed(candidatos):
        try:
            dados = json.loads(bruto)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(dados, dict) and campo in dados:
            return dados
    return {}


class JuizDeContradicoesAgent(BaseAgent):
    """O documento contradiz o conteúdo aprovado? O juiz cita os dois lados; o código confere as duas citações.

    A conferência do PRD em código pega o que tem estrutura — habilidade, tempo, texto literal reescrito. A mecânica
    («o estudante pode voltar», «o professor libera depois da votação») não tem: o corpo do PRD podia contradizer o
    anexo que a esteira cola no fim, que se declara prevalente, e ninguém via (decisão do usuário, 08/10/2026: «prefiro
    pecar pelo excesso»). Contradição com as duas citações conferidas é bloqueio para o autor; sem prova, é descartada
    e aparece no relatório como não comprovada.
    """

    documento_key: str
    referencia_key: str
    report_key: str
    status_key: str
    dono: str
    rotulo: str = "Coerência com o conteúdo aprovado"
    entrada_documento_key: str = "contradicoes_documento"
    entrada_referencia_key: str = "contradicoes_referencia"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from tools.conteudo_aprovado import remover_anexo
        from tools.fidelidade import _citacao_confere, _norm

        state = ctx.session.state
        documento = remover_anexo(str(state.get(self.documento_key, "") or ""))
        referencia = str(state.get(self.referencia_key, "") or "")
        saida = ""
        if documento.strip() and referencia.strip() and self.sub_agents:
            state[self.entrada_documento_key], state[self.entrada_referencia_key] = documento, referencia
            yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                        actions=EventActions(state_delta={self.entrada_documento_key: documento,
                                                          self.entrada_referencia_key: referencia}))
            juiz = self.sub_agents[0]
            async for evento in juiz.run_async(ctx):
                yield evento
            saida = str(ctx.session.state.get(getattr(juiz, "output_key", "") or "", "") or "")

        envelope_juiz = _bloco_com(saida, "contradicoes")
        doc_norm, ref_norm = _norm(documento), _norm(referencia)
        achados: List[Dict[str, str]] = []
        sem_prova: List[str] = []
        for c in envelope_juiz.get("contradicoes") or []:
            if not isinstance(c, dict):
                continue
            no_doc, na_ref = str(c.get("citacao_documento") or ""), str(c.get("citacao_referencia") or "")
            if _citacao_confere(no_doc, doc_norm) and _citacao_confere(na_ref, ref_norm):
                achados.append({
                    "severidade": "bloqueio", "codigo": f"contradicao-{c.get('tipo') or 'mecanica'}", "etapa": "dev",
                    "agente_responsavel": self.dono,
                    "resumo": (f"O documento diz «{no_doc[:160]}» e o conteúdo aprovado diz «{na_ref[:160]}». "
                               f"{str(c.get('explicacao') or '').strip()} Siga o aprovado; se a plataforma não permite, "
                               "registre a divergência na seção 19 com dono `produto`."),
                })
            else:
                sem_prova.append(f"«{no_doc[:120]}» × «{na_ref[:120]}»")
        # Sem resposta legível do juiz — ou sem documento, ou sem conteúdo aprovado para comparar —, nada foi conferido:
        # 🟡, nunca 🟢. Até 08/10/2026 o juiz que falhava aprovava o PRD (auditoria do padrão ouro).
        conferido = bool(documento.strip() and referencia.strip()) and isinstance(envelope_juiz.get("contradicoes"), list)
        status = "bloqueado" if achados else ("aprovado" if conferido else "amarelo")
        veredito = ("🔴 CONTRADIZ O APROVADO" if achados else "🟢 SEM CONTRADIÇÃO COMPROVADA" if conferido
                    else "🟡 NÃO CONFERIDO — o juiz não devolveu a lista de contradições, ou faltou documento ou "
                         "conteúdo aprovado para comparar")
        missao = extrair_slug(str(state.get("spec_missao") or state.get("one_pager") or "")) or ""
        linhas = [f"# {self.rotulo} — {missao or 'missão'}", "",
                  f"**Veredito: {veredito}**", "",
                  "O juiz aponta onde o corpo afirma o contrário do conteúdo aprovado, citando os dois lados; o código "
                  "confere as duas citações. Contradição sem prova é descartada.", ""]
        if achados:
            linhas += ["## Contradições comprovadas", ""] + [f"- ⛔ `{a['codigo']}` — {a['resumo']}" for a in achados] + [""]
        if sem_prova:
            linhas += ["## Apontadas sem prova (descartadas)", ""] + [f"- {s}" for s in sem_prova] + [""]
        envelope = {"agente": "juiz-de-contradicoes", "missao": missao, "status": status, "achados": achados}
        linhas += ["```json", json.dumps(envelope, ensure_ascii=False), "```"]
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    content=types.Content(role="model", parts=[types.Part(text=(
                        f"{'⛔' if achados else '✅' if conferido else '🟡'} {self.rotulo}: {len(achados)} contradição(ões) "
                        f"comprovada(s), {len(sem_prova)} sem prova{'' if conferido else ' — não conferido'}."))]),
                    actions=EventActions(state_delta={
                        self.report_key: "\n".join(linhas), self.status_key: status,
                        f"{self.status_key}_envelope": envelope,
                        self.entrada_documento_key: "", self.entrada_referencia_key: "",
                    }))


def _norm_simples(texto: str) -> str:
    return re.sub(r"\s+", " ", (texto or "").lower()).strip()


#: Tickets que um gate emitiu e nenhum agente pôde executar. O dossiê os lista como pendência humana.
KEY_TICKETS_SEM_ROTA = "tickets_sem_rota"


class DespachoTicketsAgent(BaseAgent):
    """Re-executa **apenas** os agentes endereçados pelos tickets de um gate.

    O QA de entregáveis (D7) já escreve cada ticket com um dono (`agente_responsavel`
    no envelope) e declara a ordem em que dois donos se resolvem. O que faltava era
    quem executa esse despacho: sem ele, o gate emite "rodada 1", endereça tickets e
    ninguém os aplica — o relatório vira documento, não correção.

    Este agente fecha o ciclo, e o faz **seletivamente**: reexecutar a etapa inteira
    para consertar uma string custaria todas as chamadas de MCP de novo. Só roda
    quem tem ticket, na ordem de precedência declarada no prompt do gate.

    - `mapa`: slug do envelope → `name` do sub-agente de correção, ou **lista** de nomes
      quando o conserto exige mais de um passo (o D0 e o D9 emitem dois documentos numa
      resposta só, então precisam do `SecaoSplitAgent` logo atrás para a correção chegar
      à spec — sem isso o agente reescreve e ninguém lê).
    - `posfixo`: nomes que rodam depois de **qualquer** retrabalho. É o que mantém o
      protótipo coerente: ele deriva de jornada, copy, CAA e telas, e auditar um protótipo
      construído sobre a versão anterior é pior que não auditar.
    - `ordem`: slugs na ordem em que devem rodar quando há mais de um dono.
    - `externos`: slugs que pertencem a outra etapa (ex.: `gate-estrutural`); não são
      reexecutados aqui — viram pendência humana registrada no relatório.
    - `tickets_key`: chave de estado onde cada agente lê os tickets dirigidos a ele.
    """

    report_key: str
    rotulo: str = "Retrabalho"
    mapa: Dict[str, Any] = Field(default_factory=dict)
    ordem: List[str] = Field(default_factory=list)
    externos: List[str] = Field(default_factory=list)
    posfixo: List[str] = Field(default_factory=list)
    #: `dono → agentes` que rodam depois do conserto SÓ quando aquele dono foi acionado. A banca de dev
    #: manda refazer jornada, telas ou copy, e nada refazia o protótipo, as conferências e o handoff que
    #: derivam deles (auditoria de 07/10/2026); um posfixo incondicional refaria o protótipo até por uma
    #: correção de handoff.
    posfixo_por_dono: Dict[str, List[str]] = Field(default_factory=dict)
    severidades: List[str] = Field(default_factory=lambda: ["bloqueio"])
    tickets_key: str = "tickets_retrabalho"

    def _sem_rota(self, achado: Dict[str, Any], dono: str, motivo: str) -> Dict[str, str]:
        return {
            "gate": self.rotulo,
            "id": str(achado.get("id") or achado.get("codigo") or "—"),
            "dono": dono,
            "motivo": motivo,
            "resumo": str(achado.get("resumo") or "")[:300],
        }

    def _formatar(self, achados: List[Dict[str, Any]]) -> str:
        linhas = ["## Tickets do QA endereçados a você nesta rodada", ""]
        for a in achados:
            cod = a.get("codigo") or a.get("id") or "—"
            classe = a.get("classe") or ""
            resumo = a.get("resumo") or ""
            linhas.append(f"- **{a.get('id', '?')}** · `{cod}`{f' · {classe}' if classe else ''} — {resumo}")
            # o ONDE e o COMO do QA chegavam só na seção `## Tickets` do relatório, que nenhum autor
            # lê: o ticket ia em uma linha e o autor adivinhava o conserto (auditoria de 07/10/2026)
            for campo, rotulo in (("onde", "Onde"), ("por_que", "Por quê"), ("como", "Como"), ("trecho", "Trecho")):
                valor = str(a.get(campo) or "").strip()
                if valor:
                    linhas.append(f"  - {rotulo}: {valor}")
        linhas.append("")
        linhas.append(
            "Corrija **exatamente** estes pontos e reemita o seu documento completo. "
            "Não redesenhe o que não foi apontado; não amplie escopo."
        )
        return "\n".join(linhas)

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        relatorio = str(state.get(self.report_key, "") or "")
        envelope = extrair_envelope(relatorio) or {}
        status = inferir_status(relatorio, envelope)

        if status == STATUS_APROVADO:
            return

        from tools.rastro import normalizar_dono

        por_slug: Dict[str, List[Dict[str, Any]]] = {}
        pendentes_externos: List[str] = []
        # Ticket que ninguém pode executar. Antes eram três descartes silenciosos — sem dono,
        # dono com nome que o mapa não conhece, e agente de retrabalho ausente —, e o 🔴 do
        # gate voltava na rodada seguinte sem que alguém soubesse que o conserto não saiu.
        sem_rota: List[Dict[str, str]] = []
        for achado in envelope.get("achados") or []:
            if not isinstance(achado, dict):
                continue
            if str(achado.get("severidade", "")).strip().lower() not in self.severidades:
                continue
            escrito = str(achado.get("agente_responsavel") or "").strip()
            slug = normalizar_dono(escrito)
            if not slug or slug in ("null", "none"):
                sem_rota.append(self._sem_rota(achado, escrito, "o gate não disse quem conserta"))
                continue
            if slug in self.externos:
                pendentes_externos.append(f"`{achado.get('id', '?')}` → `{slug}`")
                continue
            if slug in self.mapa:
                por_slug.setdefault(slug, []).append(achado)
            else:
                sem_rota.append(self._sem_rota(achado, escrito, "nenhum agente desta etapa atende por esse dono"))

        slugs_na_ordem = [s for s in self.ordem if s in por_slug]
        slugs_na_ordem += [s for s in por_slug if s not in slugs_na_ordem]

        # cada slug vira a cadeia de agentes que o conserto exige, sem repetir nome
        nomes_na_ordem: List[str] = []
        autores: set = set()
        por_agente: Dict[str, List[Dict[str, Any]]] = {}
        existentes = {s.name for s in self.sub_agents}
        for slug in slugs_na_ordem:
            alvo = self.mapa[slug]
            cadeia = [alvo] if isinstance(alvo, str) else list(alvo)
            ausentes = [n for n in cadeia if n not in existentes]
            if ausentes:
                for achado in por_slug[slug]:
                    sem_rota.append(self._sem_rota(
                        achado, slug, f"o agente de retrabalho {', '.join(ausentes)} não existe nesta etapa"))
                continue
            autores.add(cadeia[0])  # o autor do conserto; o resto da cadeia confere ou deriva
            for nome in cadeia:
                if nome not in nomes_na_ordem:
                    nomes_na_ordem.append(nome)
                por_agente.setdefault(nome, []).extend(por_slug[slug])

        delta_sem_rota: Dict[str, Any] = {}
        if sem_rota:
            registrados = list(state.get(KEY_TICKETS_SEM_ROTA) or [])
            vistos = {(r.get("gate"), r.get("id"), r.get("dono")) for r in registrados}
            for r in sem_rota:
                if (r["gate"], r["id"], r["dono"]) not in vistos:
                    registrados.append(r)
                    vistos.add((r["gate"], r["id"], r["dono"]))
            state[KEY_TICKETS_SEM_ROTA] = registrados
            delta_sem_rota = {KEY_TICKETS_SEM_ROTA: registrados}
        aviso_sem_rota = (" Sem quem execute (vai ao dossiê como pendência humana): "
                          + ", ".join(f"`{r['id']}` → `{r['dono'] or '—'}` ({r['motivo']})" for r in sem_rota)
                          + ".") if sem_rota else ""

        if not nomes_na_ordem:
            msg = f"⏭️ {self.rotulo}: nenhum ticket com dono executável nesta etapa."
            if pendentes_externos:
                msg += " Devolução a outra etapa: " + ", ".join(pendentes_externos) + "."
            msg += aviso_sem_rota
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                content=types.Content(role="model", parts=[types.Part(text=msg)]),
                actions=EventActions(state_delta=delta_sem_rota),
            )
            return

        derivados = [n for s in slugs_na_ordem for n in self.posfixo_por_dono.get(s, [])]
        for nome in derivados + list(self.posfixo):
            if nome not in nomes_na_ordem:
                nomes_na_ordem.append(nome)
                por_agente.setdefault(nome, [])

        # O orçamento é de chamadas de modelo: os determinísticos do posfixo (artefatos, lint, cobertura,
        # Miro) não custam nada e contavam como reexecução — com quatro donos, o orçamento estourava
        # antes de qualquer conserto (auditoria de 07/10/2026).
        from google.adk.agents.llm_agent import LlmAgent

        # Conta o autor de cada conserto e quem chama modelo. Até 07/10/2026 a conta só isentava o `posfixo`, e os determinísticos do
        # `posfixo_por_dono` da banca contavam. A correção de 07/10 ainda contava a cadeia inteira de cada dono
        # ("quem recebeu ticket conta sempre"): o dono `ambiente-simulado` é D9 + split + spec consolidada, e o
        # `telas` é telas + Stitch. Na exp01ef1b (08/10/2026, primeira execução real) a conta deu 11 contra o
        # orçamento de 8, com 7 chamadas de modelo de fato — e nenhum conserto rodou nas duas rodadas.
        def _chama_modelo(agente) -> bool:
            return agente is not None and (isinstance(agente, LlmAgent)
                                           or any(_chama_modelo(f) for f in (getattr(agente, "sub_agents", None) or [])))

        llm = sum(1 for n in nomes_na_ordem
                  if n in autores or _chama_modelo(next((s for s in self.sub_agents if s.name == n), None)))
        if not orcamento_disponivel(state, llm):
            gastos = int(state.get(KEY_REEXECUCOES, 0) or 0)
            # Cada conserto pulado vai ao dossiê como pendência humana, com o dono. A mensagem prometia isso e nada
            # o gravava: o redator do PRD seguia sem saber que a banca tinha pedido o conserto.
            registrados = list(state.get(KEY_TICKETS_SEM_ROTA) or [])
            vistos = {(r.get("gate"), r.get("id"), r.get("dono")) for r in registrados}
            for slug in slugs_na_ordem:
                for achado in por_slug.get(slug) or []:
                    r = self._sem_rota(achado, slug, "orçamento de retrabalho esgotado nesta execução")
                    if (r["gate"], r["id"], r["dono"]) not in vistos:
                        registrados.append(r)
                        vistos.add((r["gate"], r["id"], r["dono"]))
            state[KEY_TICKETS_SEM_ROTA] = registrados
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                content=types.Content(role="model", parts=[types.Part(text=(
                    f"⛔ {self.rotulo}: orçamento de retrabalho esgotado ({gastos} agente(s) já reexecutado(s) "
                    f"nesta execução). Os {len(nomes_na_ordem)} conserto(s) desta rodada ficam para uma pessoa; "
                    "a esteira segue e o diagnóstico final lista cada um com o dono."
                ))]),
                actions=EventActions(state_delta={KEY_PIPELINE_BLOQUEADO: True, KEY_TICKETS_SEM_ROTA: registrados}),
            )
            return

        resumo = ", ".join(f"{n} ({len(por_agente[n])})" for n in nomes_na_ordem)
        aviso = f"🔁 {self.rotulo}: reexecutando {len(nomes_na_ordem)} agente(s) com ticket — {resumo}."
        if pendentes_externos:
            aviso += " Fora desta etapa (não reexecutado): " + ", ".join(pendentes_externos) + "."
        aviso += aviso_sem_rota
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=aviso)]),
            actions=EventActions(state_delta=delta_sem_rota),
        )

        for nome in nomes_na_ordem:
            sub = next((s for s in self.sub_agents if s.name == nome), None)
            if sub is None:
                continue
            achados_do_agente = por_agente.get(nome) or []
            tickets = (
                self._formatar(achados_do_agente)
                if achados_do_agente
                else "## Reconstrução\n\nUm documento do qual você deriva mudou nesta rodada. "
                     "Refaça o seu a partir da versão nova, sem alterar nada além do que a mudança exigir."
            )
            state[self.tickets_key] = tickets
            # A versão que o autor escreveu nesta execução vai como base: sem ela, "corrija exatamente
            # estes pontos" virava reescrever do zero — o retrabalho das telas da exp09ef1b abriu outro
            # projeto no Stitch e perdeu E0-PROF-02/04 (auditoria de 07/10/2026).
            from pipeline.reexecucao import CHAVES_AUTORAIS, PREFIXO_ANTERIOR, bloco_versao_anterior

            chave = getattr(sub, "output_key", None) or ""
            anterior = f"{PREFIXO_ANTERIOR}{chave}" if chave in CHAVES_AUTORAIS else ""
            delta_ticket: Dict[str, Any] = {self.tickets_key: tickets}
            # a base do refazer (`preparar_estado`) volta depois do autor: zerá-la apagava a versão anterior
            base_do_refazer = str(state.get(anterior) or "") if anterior else ""
            if anterior and str(state.get(chave) or "").strip():
                delta_ticket[anterior] = bloco_versao_anterior(chave, str(state.get(chave)))
                state[anterior] = delta_ticket[anterior]
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                actions=EventActions(state_delta=delta_ticket),
            )
            async for evento in sub.run_async(ctx):
                yield evento
            if anterior and anterior in delta_ticket:
                state[anterior] = base_do_refazer
                yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                            actions=EventActions(state_delta={anterior: base_do_refazer}))

        state[self.tickets_key] = ""
        gastos = int(state.get(KEY_REEXECUCOES, 0) or 0) + llm
        state[KEY_REEXECUCOES] = gastos
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            actions=EventActions(state_delta={self.tickets_key: "", KEY_REEXECUCOES: gastos}),
        )


class VizinhasCatalogoAgent(BaseAgent):
    """Põe as missões já geradas na frente de quem está inventando uma nova.

    Antes disto, o agente que inventa a missão não via o catálogo: o primeiro a consultá-lo rodava
    três agentes depois, com o one-pager inteiro escrito, e os critérios 2.5 e 2.8 são desejáveis.
    Aqui a comparação chega antes de existir one-pager.

    Roda duas vezes na etapa de produto. **Antes do loop**, quando só há briefing, filtra pelo ano
    declarado. **Dentro do loop**, depois do núcleo, refiltra pelo que a missão realmente é
    (ambiente, eixo, descoberta) — é essa lista que a verificação V5 do micro-gate julga.

    A recuperação é mecânica e ordena por semelhança lexical; **quem reprova é o V5**, aplicando o
    teste de 2 frases. Linha do índice com campo por preencher não sustenta reprovação, e o texto
    abaixo diz isso ao avaliador.
    """

    limite: int = 5

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from tools import catalogo as cat

        state = dict(ctx.session.state)
        nucleo = str(state.get("nucleo_narrativo") or "")
        try:
            indice = cat.carregar()
            if nucleo.strip():
                ficha, fonte = cat.ficha_da_execucao(state, sessao=""), "núcleo narrativo"
            else:
                from tools.bncc import extrair_serie

                briefing = str(state.get("briefing") or "")[:6000]
                serie = extrair_serie(briefing)
                ano = f"{min(serie['anos'])}EF" if serie["anos"] else ("EM" if serie["em"] else "")
                ficha = {"ano": ano, "ambiente": cat._ambiente(briefing), "eixo": "",
                         "descoberta": "", "tipo_decisao": "", "sessao": ""}
                fonte = "briefing"
            proximas = cat.vizinhas(ficha, indice, n=self.limite)
            total = len(indice.get("missoes", []))
            # A base do V5, conferida AQUI e não no registro do fim da esteira: o aviso existia
            # e só aparecia no relatório do catálogo, que roda depois do dossiê — nem o micro-gate
            # que julga a semelhança nem quem lê o diagnóstico ficavam sabendo.
            saude = cat.saude_do_indice(indice)
            aviso = cat.aviso_de_indice_cego(saude)

            if not proximas:
                texto = (f"_Nenhuma missão próxima no índice ({total} registrada(s) ao todo, filtro pelo {fonte}: "
                         f"ano, ambiente e eixo). Não há repetição a evitar — mas também não há comparação possível._")
            else:
                texto = "\n".join([
                    f"Missões **já geradas** que mais se aproximam desta (memória do gerador · {total} no índice · filtro pelo {fonte}):",
                    "",
                    cat.tabela_markdown(proximas, com_semelhanca=True),
                    "",
                    "A coluna **Semelhança** é lexical: ela ordena, não decide. Duas missões podem dizer a mesma coisa "
                    "com outras palavras e aparecer como `baixa`. Julgue pelo conteúdo.",
                    "Linha com campo `—` ou `[preencher…]` **não sustenta reprovação**: registre como lacuna de catálogo e siga.",
                ])
            msg = f"🗂️ Catálogo: {len(proximas)} missão(ões) próxima(s) de {total} no índice (por {fonte})."
            if aviso:
                texto = aviso + "\n\n" + texto
                msg += "\n" + aviso.lstrip("> ")
            achados = []
            if saude.get("fora_do_indice"):
                achados.append({"severidade": "atencao", "codigo": "indice-defasado", "agente_responsavel": "produto",
                                 "resumo": f"{len(saude['fora_do_indice'])} missão(ões) gerada(s) fora do índice: "
                                           + ", ".join(saude["fora_do_indice"][:8])})
            if saude["total"] and saude["fracao_cega"] >= 0.5:
                achados.append({"severidade": "atencao", "codigo": "indice-cego", "agente_responsavel": "produto",
                                 "resumo": f"{saude['cegas']} de {saude['total']} fichas sem campo de comparação: o V5 não as julga."})
            status = "amarelo" if (aviso or achados) else "aprovado"
            envelope = {"agente": "catalogo-indice", "status": status, "achados": achados,
                        "total": saude["total"], "uteis": saude["uteis"]}
        except Exception as exc:  # memória é conveniência: nunca derruba a esteira
            texto = f"_Índice de missões indisponível nesta execução ({exc}). Sem comparação com missões anteriores._"
            msg = f"⚠️ Catálogo: não consegui ler o índice ({exc})."
            status = "amarelo"
            envelope = {"agente": "catalogo-indice", "status": status, "achados": [{
                "severidade": "atencao", "codigo": "indice-ilegivel", "agente_responsavel": "produto",
                "resumo": f"índice de missões ilegível: {exc}"}]}

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=msg)]),
            actions=EventActions(state_delta={"missoes_vizinhas": texto,
                                              "catalogo_indice_status": status,
                                              "catalogo_indice_status_envelope": envelope}),
        )


class RegistroCatalogoAgent(BaseAgent):
    """Registra a missão desta execução na memória do gerador, ao fim da esteira.

    Fecha o laço que estava aberto: o agente 51 propunha a linha do catálogo e ninguém a aplicava,
    e as sessões salvas — que contêm toda missão já gerada — não eram lidas entre execuções. Aqui a
    ficha é extraída do estado (mecânica, da spec e do núcleo; de julgamento, da linha que o 51
    escreveu) e comparada com o índice.

    **Calcula e reporta; quem persiste é o runner**, depois de `save_run_artifacts`, porque só lá
    existe o nome da pasta desta sessão — que é a chave da entrada. O agente grava a ficha em
    `ficha_catalogo_dados` para o runner usar.

    O registro é **fato, não juízo**: toda execução entra, inclusive a bloqueada — senão a mesma
    ideia volta a ser gerada. Promover para `aprovada` é ato humano.
    """

    status_key: str = "catalogo_status"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from tools import catalogo as cat

        state = dict(ctx.session.state)
        missao = extrair_slug(str(state.get("spec_missao") or state.get("one_pager") or ""))
        try:
            ficha = cat.ficha_da_execucao(state, sessao="")
            # `gravar_arquivo=False`: o índice em disco é do runner, que sabe o nome da pasta.
            resultado = cat.registrar(ficha, indice=cat.carregar(), gravar_arquivo=False)
            texto = cat.relatorio_markdown(resultado, missao)
            delta = {
                "ficha_catalogo": texto,
                "ficha_catalogo_dados": resultado["ficha"],
                self.status_key: resultado["status"],
                f"{self.status_key}_envelope": {"agente": cat.AGENTE, "missao": missao,
                                                "status": resultado["status"],
                                                "achados": resultado["achados"]},
            }
            msg = f"🗂️ Catálogo: missão registrada como `{resultado['ficha'].get('status')}` · {resultado['total']} no índice."
            if resultado["achados"]:
                msg += "\n" + "\n".join(f"- ⚠️ {a['resumo'][:120]}" for a in resultado["achados"])
        except Exception as exc:  # o registro é memória, não gate: nunca derruba a execução
            # Mas falhar não é aprovar. Gravar `aprovado` numa exceção faz o dossiê dizer que a
            # missão entrou no índice quando ela não entrou — e o gate de semelhança da próxima
            # execução compara contra um catálogo que não a tem. 🟡 diz a verdade e não trava.
            delta = {
                self.status_key: "amarelo",
                f"{self.status_key}_envelope": {"agente": cat.AGENTE, "status": "amarelo", "achados": [{
                    "severidade": "atencao", "codigo": "catalogo-indisponivel",
                    "agente_responsavel": "catalogo",
                    "resumo": f"A missão não foi registrada no índice ({exc}): a próxima execução "
                              f"não a terá como vizinha na verificação de semelhança.",
                }]},
            }
            msg = f"⚠️ Catálogo: não consegui montar a ficha desta missão ({exc}). A execução segue, e o dossiê registra a falta."

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=msg)]),
            actions=EventActions(state_delta=delta),
        )


class DiagnosticoAgent(BaseAgent):
    """Fecha a execução com o dossiê do que passou, do que passou com ressalva e do que travou.

    Roda **sempre**, e é o único que não depende de nenhum agente ter dado certo: lê os
    envelopes que os gates já gravaram no estado (`tools/diagnostico.py`). Como a esteira
    deixou de abortar na primeira reprovação, este é o documento que diz onde atuar sem
    obrigar ninguém a abrir doze artefatos e o `estado.json`.
    """

    status_key: str = "diagnostico_status"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from pipeline.artifacts import ARTIFACT_FILES
        from tools.diagnostico import artefatos_esperados, coletar, envelope, relatorio_markdown

        state = dict(ctx.session.state)
        missao = extrair_slug(str(state.get("spec_missao") or state.get("one_pager") or ""))
        dossie = coletar(state)
        artefatos = artefatos_esperados(state, ARTIFACT_FILES)
        texto = relatorio_markdown(dossie, missao, artefatos, state=state)
        env = envelope(dossie, missao)

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=texto)]),
            actions=EventActions(
                state_delta={
                    "diagnostico_execucao": texto + "\n```json\n" + json.dumps(env, ensure_ascii=False) + "\n```\n",
                    self.status_key: env["status"],
                    f"{self.status_key}_envelope": env,
                }
            ),
        )


class MecanicaCheckAgent(BaseAgent):
    """Refaz a conta da virada a partir da tabela 1.3 do núcleo (`tools/mecanica.py`). Determinístico.

    Roda no laço do núcleo, junto do micro-gate e da profundidade: conta que não fecha devolve o núcleo
    ao autor com o ranking calculado. Não registra degradação — o freio é o parecer humano.
    """

    report_key: str = "mecanica_report"
    status_key: str = "mecanica_status"
    #: O documento que traz a tabela 1.3. Nos comitês é o `one_pager`: o autor pode ter mudado a mecânica depois do
    #: loop do núcleo, e a conta é refeita sobre a versão que o comitê julga.
    chave: str = "nucleo_narrativo"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from tools import mecanica as mec

        nucleo = str(ctx.session.state.get(self.chave, "") or "")
        resultado = mec.validar(nucleo)
        relatorio = mec.relatorio(resultado, extrair_slug(nucleo) or "")
        icone = {"aprovado": "✅", "amarelo": "🟡", "bloqueado": "⛔"}[resultado["status"]]
        calc = resultado.get("calculo") or {}
        resumo = (f" Antes: {calc['antes'][0][0]}; depois: {calc['depois'][0][0]}." if calc.get("antes") and calc.get("depois") else "")
        msg = f"{icone} Conta da virada: {len(resultado['achados'])} achado(s).{resumo}"
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    content=types.Content(role="model", parts=[types.Part(text=msg)]),
                    actions=EventActions(state_delta={
                        self.report_key: relatorio,
                        self.status_key: resultado["status"],
                        f"{self.status_key}_envelope": extrair_envelope(relatorio) or {},
                    }))


class CoberturaConceitualAgent(BaseAgent):
    """Confere o núcleo contra o mapa conceitual do material, a cada rodada do loop do núcleo.

    Roda antes do micro-gate e do juiz de profundidade, e não emite status próprio: o resultado
    vai para `cobertura_resultado`, que o `ProfundidadeCheckAgent` funde ao veredito do juiz. Um
    semáforo à parte repetiria o mesmo 🔴 duas vezes no cartão do parecer.
    """

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from tools import profundidade as prof

        state = ctx.session.state
        nucleo = str(state.get("nucleo_narrativo", "") or "")
        resultado = prof.validar_cobertura(nucleo, str(state.get("mapa_conceitual", "") or ""),
                                           str(state.get("material_anexado", "") or ""))
        relatorio = prof.relatorio_cobertura(resultado, extrair_slug(nucleo) or "")
        bloqueios = [a for a in resultado["achados"] if a["severidade"] == "bloqueio"]
        icone = {"aprovado": "✅", "amarelo": "🟡", "bloqueado": "⛔"}[resultado["status"]]
        msg = (f"{icone} Cobertura conceitual: {len(resultado['cobertos'])} conceito(s) do material vivido(s) em tela, "
               f"{len(bloqueios)} bloqueio(s), {len(resultado['achados']) - len(bloqueios)} ressalva(s).")
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=msg)]),
            actions=EventActions(state_delta={
                "cobertura_report": relatorio,
                "cobertura_resultado": {"status": resultado["status"], "achados": resultado["achados"],
                                        "cobertos": resultado["cobertos"]},
            }),
        )


class ProfundidadeCheckAgent(BaseAgent):
    """Veredito de profundidade contado em código: notas do juiz + cobertura determinística.

    O juiz de profundidade dá nota de 1 a 4 em seis dimensões; o status sai das notas
    (`tools/profundidade.py::veredito_por_notas`), não do que o juiz escreveu no campo `status` —
    um juiz que escreve "aprovado" com o ápice em 2 não aprova. Cobertura bloqueada bloqueia.

    Não registra degradação: como no micro-gate, a esteira segue e o problema fica à vista. O
    freio é o parecer humano — com este gate em 🔴, o *de acordo* de produto é recusado.
    """

    report_key: str = "profundidade_report"
    status_key: str = "profundidade_status"
    round_key: str = "profundidade_rodada"
    rotulo: str = "Profundidade pedagógica"
    max_rounds: int = 2

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from config import get_settings
        from tools import profundidade as prof

        state = ctx.session.state
        resultado = prof.consolidar(str(state.get(self.report_key, "") or ""),
                                    dict(state.get("cobertura_resultado") or {}))
        rodada = int(state.get(self.round_key, 0) or 0) + 1
        # Só na última rodada: antes dela, o 🔴 é o que devolve o núcleo ao autor.
        if resultado["status"] == "bloqueado" and rodada >= self.max_rounds and not get_settings().profundidade_estrita:
            resultado["status"] = "amarelo"
            resultado["achados"].append({
                "severidade": "atencao", "codigo": "profundidade-nao-estrita", "etapa": "produto",
                "agente_responsavel": "produto",
                "resumo": "A profundidade reprovou nas notas, e PROFUNDIDADE_ESTRITA=false rebaixou o 🔴 a 🟡: "
                          "os cortes ainda estão em calibração. Leia as notas antes do de acordo.",
            })
        envelope = {"agente": prof.AGENTE_JUIZ, "status": resultado["status"], "rodada": rodada,
                    "notas": resultado["notas"], "aha_em_uma_frase": resultado["aha_em_uma_frase"],
                    "ponto_mais_fraco": resultado["ponto_mais_fraco"], "achados": resultado["achados"]}
        notas = prof.linha_de_notas(resultado["notas"]) if resultado["notas"] else "sem notas"
        icone = {"aprovado": "✅", "amarelo": "🟡", "bloqueado": "⛔"}[resultado["status"]]
        msg = f"{icone} {self.rotulo}: `{resultado['status']}` na rodada {rodada} — {notas}."
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=msg)]),
            actions=EventActions(state_delta={self.status_key: resultado["status"],
                                              f"{self.status_key}_envelope": envelope,
                                              self.round_key: rodada}),
        )


PREFIXO_RODADA_ANTERIOR = "rodada_anterior_"


def bloco_versao_da_rodada(chave: str, documento: str) -> str:
    """Valor de `rodada_anterior_<chave>`: a versão que o autor escreveu na rodada que o gate reprovou."""
    return "\n".join([
        "## Sua versão da rodada anterior deste loop",
        "",
        "O gate reprovou a versão abaixo, que você escreveu na rodada anterior. **Parta dela**: corrija exatamente o que "
        "os relatórios desta instrução apontam e mantenha o resto palavra por palavra — o que já passou não pode mudar "
        "sem motivo, porque nenhum gate o confere de novo. Reemita o documento inteiro.",
        "",
        f'<versao_da_rodada chave="{chave}">',
        documento,
        "</versao_da_rodada>",
    ])


#: `retrabalho_<chave>`: o que os gates reprovaram na rodada, enquanto o loop repete.
PREFIXO_RETRABALHO = "retrabalho_"


def motivos_do_retrabalho(state: Dict[str, Any], reprovados: List[str]) -> str:
    """Os relatórios dos gates reprovados na rodada, como pedido de correção para o editor de trocas."""
    from tools import citacoes

    blocos = ["Os gates desta rodada reprovaram o documento. Corrija exatamente o que eles apontam, com o mínimo de "
              "trocas; o que eles não apontam já passou e não pode mudar.", ""]
    for k in reprovados:
        relatorio = str(state.get(k[: -len("_status")] + "_report") or "").strip() if k.endswith("_status") else ""
        envelope = state.get(f"{k}_envelope")
        bloqueios = [a for a in ((envelope or {}).get("achados") or []) if isinstance(a, dict) and citacoes.bloqueante(a)]
        blocos.append(f"### Gate `{k}`")
        blocos += [f"- {a.get('codigo') or a.get('id') or 'achado'}: {a.get('resumo') or ''}"
                   + (f" — trecho: «{citacoes.citacao(a)}»" if citacoes.citacao(a) else "") for a in bloqueios]
        if relatorio:
            blocos += ["", relatorio[:8000]]
        blocos.append("")
    return "\n".join(blocos).strip()


class SaidaDeLoopAgent(BaseAgent):
    """Encerra um `LoopAgent` quando todos os gates da rodada passaram — ou quando o teto caiu.

    Os gates determinísticos (`BnccCheckAgent`, `RastroCheckAgent`) sabem julgar, mas não
    sabem rotear: cada um lê uma coisa e grava um status. Este agente lê o conjunto e toma
    a única decisão que falta — repetir ou seguir.

    É o que transforma "o gate reprovou" em "o autor do documento reescreve e o gate confere
    de novo", sem depender de o modelo decidir isso por conta própria dentro do prompt.
    """

    status_keys: List[str] = Field(default_factory=list)
    rodada_key: str = ""
    max_rounds: int = 2
    rotulo: str = "Loop"
    #: Status que contam como "pode seguir". `amarelo` é pendência de plataforma: repetir não resolve.
    aceitos: List[str] = Field(default_factory=lambda: ["aprovado", "amarelo"])
    #: `status_key → campo do envelope` que, maior que zero, reprova mesmo com status aceito. O parecer
    #: "ADEQUADA COM AJUSTES" é `aprovado_com_ressalvas` com `ajustes_exigidos: 3`, e o loop encerrava
    #: sem o revisor aplicar nenhum — o gate final da exp03ef1b reprovou depois pelo ajuste que ficou.
    envelope_exige: Dict[str, str] = Field(default_factory=dict)
    #: Os documentos que o autor do loop escreve: quando o loop repete, a versão desta rodada vai a ele em
    #: `rodada_anterior_<chave>` (`agents/base.py`).
    autor_keys: List[str] = Field(default_factory=list)

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        rodada = int(state.get(self.rodada_key, 0) or 0) + 1
        # Chave ausente conta como REPROVADA. O `k in state` fazia o loop encerrar com
        # aprovação quando o gate a montante não tinha escrito nada — e era o caso do
        # `adequacao_status`, que nenhum agente gravava: o `A033AdequacaoCheck` aprovava
        # sempre, sobre uma chave que nunca existiu.
        reprovados = [
            k for k in self.status_keys
            if str(state.get(k, "")).strip().lower() not in self.aceitos
        ]
        for k, campo in self.envelope_exige.items():
            envelope = state.get(f"{k}_envelope") or {}
            try:
                exigidos = int(envelope.get(campo) or 0) if isinstance(envelope, dict) else 0
            except (TypeError, ValueError):
                exigidos = 0
            if exigidos > 0 and k not in reprovados:
                reprovados.append(k)
        esgotou = rodada >= self.max_rounds
        delta: Dict[str, Any] = {self.rodada_key: rodada}

        if not reprovados:
            msg = f"✅ {self.rotulo}: tudo conforme na rodada {rodada}."
            escalate = True
        elif esgotou:
            nomes = ", ".join(f"`{k}`" for k in reprovados)
            msg = (
                f"⛔ {self.rotulo}: {len(reprovados)} gate(s) ainda reprovado(s) após {rodada} rodada(s) — {nomes}. "
                "Não há mais rodada: a esteira segue e o diagnóstico final registra o que ficou."
            )
            escalate = True
        else:
            nomes = ", ".join(f"`{k}`" for k in reprovados)
            msg = (
                f"🔁 {self.rotulo}: rodada {rodada}/{self.max_rounds} — {nomes} reprovado(s). "
                "O autor do documento recebe o relatório e reescreve."
            )
            escalate = False

        # A versão desta rodada vai ao autor na seguinte, para ele corrigir em vez de reescrever do zero: só o que o
        # gate confere ficava protegido entre rodadas, e o resto podia mudar sem ninguém ver (auditoria de 07/10/2026).
        # Ao sair do loop, a chave some.
        for chave in self.autor_keys:
            documento = str(state.get(chave, "") or "").strip()
            delta[f"{PREFIXO_RODADA_ANTERIOR}{chave}"] = (
                bloco_versao_da_rodada(chave, documento) if documento and not escalate else "")
            # O que os gates reprovaram, para o retrabalho por trocas (`agents.callbacks.retrabalhar_por_trocas`): na
            # rodada seguinte o documento é corrigido trecho a trecho, e o que já passou não muda.
            delta[f"{PREFIXO_RETRABALHO}{chave}"] = (
                motivos_do_retrabalho(state, reprovados) if documento and not escalate else "")

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=msg)]),
            actions=EventActions(state_delta=delta, escalate=escalate or None),
        )


class ComiteVotosAgent(BaseAgent):
    """Conta os votos de um painel do comitê pedagógico (`tools/comite.py`). Determinístico.

    Três juízes votam em paralelo; este agente lê os três relatórios, confere no documento julgado a citação de cada
    bloqueio e grava o veredito: unanimidade aprova; sem ela, a missão volta a quem a escreve (A004 e A014), e na última
    rodada segue com 🟡 e os votos vencidos à vista. Não registra degradação — o 🟡 do teto vai ao parecer do PO.
    """

    #: chave de saída de cada juiz → rótulo dele no relatório
    fontes: Dict[str, str] = Field(default_factory=dict)
    #: onde a citação de cada bloqueio é conferida
    documentos: List[str] = Field(default_factory=lambda: ["nucleo_narrativo", "one_pager", "brief_escopo"])
    report_key: str
    status_key: str
    round_key: str
    max_rounds: int = 5
    rotulo: str = "Comitê"
    titulo: str = "Comitê pedagógico"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from tools import citacoes, comite

        state = ctx.session.state
        rodada = int(state.get(self.round_key, 0) or 0) + 1
        resultado = comite.consolidar({k: str(state.get(k, "") or "") for k in self.fontes},
                                      citacoes.texto_dos_documentos(state, self.documentos), rodada, self.max_rounds)
        missao = extrair_slug(str(state.get("one_pager") or state.get("nucleo_narrativo") or "")) or ""
        relatorio = comite.relatorio(resultado, self.titulo, self.fontes, missao)
        n = len(resultado["votos"])
        icone = {"aprovado": "✅", "amarelo": "🟡", "bloqueado": "🔁"}[resultado["status"]]
        msg = (f"{icone} {self.rotulo}: {n - resultado['contra']} de {n} aprovam na rodada "
               f"{rodada}/{self.max_rounds} — `{resultado['status']}`.")
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=msg)]),
            actions=EventActions(state_delta={self.report_key: relatorio,
                                              self.status_key: resultado["status"],
                                              f"{self.status_key}_envelope": comite.envelope(resultado),
                                              self.round_key: rodada}),
        )


class LinhaDeBaseAgent(BaseAgent):
    """Fim da etapa na correção pontual: cada bloqueio dos gates contra o veredito de antes (`tools/linha_de_base.py`).

    Determinístico. Só entra na árvore no modo pontual (`pipeline.orchestrator.create_mission_orchestrator`); fora dele,
    sem `modo_correcao`, não faz nada. Rebaixa a 🟡 o bloqueio que cita trecho que a correção não tocou e que o gate
    não acusava antes, mantém o que já bloqueava e o que a correção causou, e grava o relatório que o PO lê.
    """

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        from pipeline.reexecucao import CHAVES_POR_ETAPA
        from tools import edicao_pontual, linha_de_base

        state = ctx.session.state
        if state.get(KEY_MODO_CORRECAO) != "pontual":
            return
        etapa = str(state.get("etapa_da_correcao") or "")
        chaves = sorted(k for k in CHAVES_POR_ETAPA.get(etapa, ()) if k.endswith("_status") and k in state)
        from pipeline.reexecucao import PREFIXO_VERSAO_ANTERIOR

        edicoes = list(state.get("edicoes_pontuais") or [])
        anteriores = {e.get("documento"): str(state.get(PREFIXO_VERSAO_ANTERIOR + str(e.get("documento"))) or "")
                      for e in edicoes}
        delta, linhas = linha_de_base.aplicar(dict(state), dict(state.get(linha_de_base.KEY_LINHA_DE_BASE) or {}),
                                              edicoes, chaves, anteriores=anteriores)
        missao = extrair_slug(str(state.get("spec_missao") or state.get("one_pager") or "")) or ""
        delta[linha_de_base.KEY_LINHA_DE_BASE_REPORT] = linha_de_base.relatorio(
            linhas, edicao_pontual.resumo(edicoes), missao)
        delta["linha_de_base_linhas"] = linhas
        novos = len(linha_de_base.bloqueios_novos(linhas))
        rebaixados = sum(1 for l in linhas if l["origem"] in (linha_de_base.TEXTO_INALTERADO,
                                                                linha_de_base.FORA_DA_CORRECAO))
        msg = (f"📏 Linha de base: {len(linhas)} bloqueio(s) nos gates — {rebaixados} não ligados às trocas "
               f"(rebaixados a 🟡), {novos} causados pela correção.")
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    content=types.Content(role="model", parts=[types.Part(text=msg)]),
                    actions=EventActions(state_delta=delta))


#: Atributos em que um agente guarda o contador de rodada que lê e incrementa.
_CAMPOS_DE_RODADA = ("round_key", "rodada_key")


def chaves_de_rodada(agente: BaseAgent) -> List[str]:
    """Os contadores de rodada de um agente e de toda a árvore abaixo dele."""
    chaves: List[str] = []
    for campo in _CAMPOS_DE_RODADA:
        valor = getattr(agente, campo, "")
        if isinstance(valor, str) and valor:
            chaves.append(valor)
    for sub in agente.sub_agents:
        chaves += chaves_de_rodada(sub)
    return list(dict.fromkeys(chaves))


class LoopIsolado(BaseAgent):
    """Roda um loop dentro de outro sem que a saída de um encerre o outro.

    O `LoopAgent` do ADK encerra quando QUALQUER evento de um subagente traz `escalate`
    (`google/adk/agents/loop_agent.py`), e o loop interno repassa o evento da saída dele. Sem isolar, o comitê dos
    canais terminaria no instante em que o loop do núcleo aprovasse. Este agente repassa uma cópia de cada evento sem
    `escalate` — o original, que o loop interno ainda lê depois do `yield`, fica intacto.

    E zera, antes de cada volta, os contadores de rodada da árvore interna: eles vivem no estado da sessão, e na segunda
    volta do comitê o núcleo entraria com as rodadas esgotadas e sairia sem deixar o autor corrigir nada.
    """

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        interno = self.sub_agents[0]
        state = ctx.session.state
        sujos = {k: 0 for k in chaves_de_rodada(interno) if int(state.get(k, 0) or 0)}
        if sujos:
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                content=types.Content(role="model", parts=[types.Part(
                    text=f"🔁 {interno.name}: nova volta, contadores de rodada zerados.")]),
                actions=EventActions(state_delta=sujos),
            )
        async with Aclosing(interno.run_async(ctx)) as agen:
            async for event in agen:
                if event.actions and event.actions.escalate:
                    copia = event.model_copy()
                    copia.actions = event.actions.model_copy(update={"escalate": None})
                    yield copia
                else:
                    yield event


def isolar(loop: BaseAgent) -> LoopIsolado:
    """`LoopIsolado` com o nome do loop que ele envolve."""
    return LoopIsolado(name=f"{loop.name}Isolado", description=f"{loop.description} (isolado: dentro de outro loop)",
                       sub_agents=[loop])
