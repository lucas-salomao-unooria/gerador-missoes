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
    KEY_PIPELINE_BLOQUEADO,
    KEY_PIPELINE_MOTIVO,
    STATUS_APROVADO,
    STATUS_BLOQUEADO,
    extrair_envelope,
    extrair_slug,
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


def registrar_degradacao(state, delta: Dict[str, Any], gate: str, motivo: str) -> None:
    """Anota a reprovação e reescreve o aviso de herança para os agentes a jusante.

    Não interrompe nada: a esteira segue até o fim justamente para que o diagnóstico final
    tenha todos os insumos. `KEY_PIPELINE_BLOQUEADO` continua existindo, mas só como
    veredito da execução — não como ordem de parada.
    """
    anteriores = list(state.get(KEY_DEGRADACOES) or [])
    anteriores.append({"gate": gate, "motivo": motivo})
    delta[KEY_DEGRADACOES] = anteriores
    delta[KEY_HERANCA] = texto_de_heranca(anteriores)
    delta[KEY_PIPELINE_BLOQUEADO] = True
    # O motivo original é o primeiro; a lista completa fica em KEY_DEGRADACOES.
    if not state.get(KEY_PIPELINE_MOTIVO):
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
    treat_indefinido_as_blocked: bool = True

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        relatorio = str(state.get(self.report_key, "") or "")
        envelope = extrair_envelope(relatorio)
        status = inferir_status(relatorio, envelope)
        if status not in (STATUS_APROVADO, STATUS_BLOQUEADO):
            status = STATUS_BLOQUEADO if self.treat_indefinido_as_blocked else STATUS_APROVADO

        rodada = int(state.get(self.round_key, 0) or 0) + 1 if self.round_key else 1
        delta = {self.status_key: status, f"{self.status_key}_envelope": envelope or {}}
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
                registrar_degradacao(state, delta, self.rotulo, f"{self.rotulo} reprovado")
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

    Seção ausente, curta ou sem o conteúdo exigido → a chave é mantida como está e o evento avisa.
    """

    source_key: str
    status_key: str
    rotulo: str = "Split"
    extracoes: List[Dict[str, Any]] = Field(default_factory=list)

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        texto = str(state.get(self.source_key, "") or "")
        delta: Dict[str, Any] = {}
        linhas: List[str] = []

        if not texto.strip():
            linhas.append(f"⏭️ {self.rotulo}: `{self.source_key}` vazio — nada a extrair.")
        else:
            for ex in self.extracoes:
                chave = ex["chave"]
                secao = extrair_secao(texto, ex["inicio"], ex.get("fim"))
                motivo: Optional[str] = None
                if secao is None:
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
                    continue
                backup = ex.get("backup")
                if backup and state.get(chave) and not state.get(backup):
                    delta[backup] = state.get(chave)
                delta[chave] = secao
                linhas.append(f"✅ `{chave}` gravado a partir de `{self.source_key}` ({len(secao)} caracteres).")

            envelope = extrair_envelope(texto)
            status = inferir_status(texto, envelope)
            if status not in (STATUS_APROVADO, STATUS_BLOQUEADO):
                status = STATUS_APROVADO
            delta[self.status_key] = status
            delta[f"{self.status_key}_envelope"] = envelope or {}
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
                pid = extrair_project_id(relatorio)
                if pid:
                    # Os ids do relatório só são usados se o `list_screens` vier vazio.
                    dados = coletar_links(pid, ids_de_reserva=extrair_screen_ids(relatorio))
                    delta[self.links_key] = montar_folha_de_links(dados, titulo)
                    linhas.append(f"🔗 Stitch: {len(dados['telas'])} tela(s) no projeto `{pid}` — link no relatório e no PRD.")
                    if dados["telas"] and not any("E0-PROF" in (t.get("titulo") or "").upper() for t in dados["telas"]):
                        # A folha já carrega o marcador `[LACUNA — dono: telas]`; aqui só se avisa.
                        linhas.append("⚠️ Nenhuma tela do preparo do professor (`E0-PROF-*`) no Stitch — lacuna registrada na folha com dono `telas`.")
                else:
                    linhas.append("⚠️ Stitch ligado, mas o relatório de wireframes não trouxe o identificador do projeto.")
        except Exception as exc:  # a coleta é conveniência: nunca derruba a esteira
            linhas.append(f"⚠️ Não consegui colher os links do Stitch: {exc}")

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text="\n".join(linhas) or "Nada a coletar.")]),
            actions=EventActions(state_delta=delta),
        )


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
        resultado = validar_spec(spec)
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


class RastroCheckAgent(BaseAgent):
    """Gate determinístico de rastro: `modo` decide a verificação de `tools/rastro.py`.

    - ``lacunas``: varre `fontes` (documentos do estado) atrás de marcadores de lacuna e
      atribui cada um a `input · produto · design · dev · plataforma`;
    - ``manifesto``: ficha do manifesto no bloco 0 da spec (`spec_key`);
    - ``telemetria``: contrato de evento e proibições de arquitetura no handoff (`fonte_key`).

    `bloqueado` + `estrito` → pipeline bloqueado (jusante pulado). `amarelo` segue.
    """

    modo: str  # lacunas | manifesto | telemetria | prd | one_pager
    report_key: str
    status_key: str
    rotulo: str = "Rastro"
    estrito: bool = True
    spec_key: str = "spec_missao"
    fonte_key: str = "handoff_dev"
    fontes: List[Dict[str, str]] = Field(default_factory=list)
    agente: str = "rastro-lacunas"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        missao = extrair_slug(str(state.get("spec_missao") or state.get("one_pager") or "")) or ""
        if self.modo == "one_pager":
            # Roda antes do gate estrutural, a cada rodada: contrato de plataforma (canal de
            # sala, estado no servidor), SAEB no ano certo e origem dos números. Não bloqueia
            # sozinho — o gate converte cada achado em ❌ pelo critério e o revisor aplica.
            resultado = validar_one_pager(
                str(state.get("one_pager", "") or ""),
                nucleo=str(state.get("nucleo_narrativo", "") or ""),
                briefing=str(state.get("briefing", "") or ""),
            )
            relatorio = relatorio_contrato_produto(resultado, missao)
        elif self.modo == "manifesto":
            resultado = validar_manifesto(str(state.get(self.spec_key, "") or ""))
            relatorio = relatorio_manifesto(resultado, missao)
        elif self.modo == "telemetria":
            resultado = validar_telemetria(str(state.get(self.fonte_key, "") or ""))
            relatorio = relatorio_telemetria(resultado, missao)
        elif self.modo == "prd":
            # Dois exames no mesmo passo: os marcadores que o redator deixou (lacunas) e as
            # contradições que ele não viu (consistência). Um PRD pode não ter lacuna nenhuma e
            # ainda declarar dois prefixos de tabela ou deixar um requisito P0 sem teste — e é o
            # segundo caso que faz quem codifica escolher um caminho ao acaso.
            r_lacunas = varrer_lacunas(self.fontes, dict(state))
            r_consistencia = validar_prd(str(state.get("prd_final", "") or ""))
            relatorio = (
                relatorio_lacunas(r_lacunas, self.rotulo, missao, agente=self.agente)
                + "\n\n---\n\n"
                + relatorio_prd(r_consistencia, missao)
            )
            ordem = ("bloqueado", "amarelo", "aprovado")
            resultado = {
                "status": min((r_lacunas["status"], r_consistencia["status"]), key=ordem.index),
                "achados": list(r_lacunas["achados"]) + list(r_consistencia["achados"]),
            }
        else:
            resultado = varrer_lacunas(self.fontes, dict(state))
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
            msg = f"🟡 {self.rotulo}: {len(avisos)} pendência(s) de plataforma — o pipeline segue e o PRD sai 🟡, não verde.\n" + "\n".join(f"- ⚠️ {a.get('resumo') or a.get('trecho', '')}" for a in avisos)
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
    severidades: List[str] = Field(default_factory=lambda: ["bloqueio"])
    tickets_key: str = "tickets_retrabalho"

    def _formatar(self, achados: List[Dict[str, Any]]) -> str:
        linhas = ["## Tickets do QA endereçados a você nesta rodada", ""]
        for a in achados:
            cod = a.get("codigo") or a.get("id") or "—"
            classe = a.get("classe") or ""
            resumo = a.get("resumo") or ""
            linhas.append(f"- **{a.get('id', '?')}** · `{cod}`{f' · {classe}' if classe else ''} — {resumo}")
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

        por_slug: Dict[str, List[Dict[str, Any]]] = {}
        pendentes_externos: List[str] = []
        for achado in envelope.get("achados") or []:
            if not isinstance(achado, dict):
                continue
            if str(achado.get("severidade", "")).strip().lower() not in self.severidades:
                continue
            slug = str(achado.get("agente_responsavel") or "").strip().lower()
            if not slug or slug in ("null", "none"):
                continue
            if slug in self.externos:
                pendentes_externos.append(f"`{achado.get('id', '?')}` → `{slug}`")
                continue
            if slug in self.mapa:
                por_slug.setdefault(slug, []).append(achado)

        slugs_na_ordem = [s for s in self.ordem if s in por_slug]
        slugs_na_ordem += [s for s in por_slug if s not in slugs_na_ordem]

        # cada slug vira a cadeia de agentes que o conserto exige, sem repetir nome
        nomes_na_ordem: List[str] = []
        por_agente: Dict[str, List[Dict[str, Any]]] = {}
        for slug in slugs_na_ordem:
            alvo = self.mapa[slug]
            for nome in ([alvo] if isinstance(alvo, str) else list(alvo)):
                if nome not in nomes_na_ordem:
                    nomes_na_ordem.append(nome)
                por_agente.setdefault(nome, []).extend(por_slug[slug])

        if not nomes_na_ordem:
            msg = f"⏭️ {self.rotulo}: nenhum ticket com dono executável nesta etapa."
            if pendentes_externos:
                msg += " Devolução a outra etapa: " + ", ".join(pendentes_externos) + "."
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                content=types.Content(role="model", parts=[types.Part(text=msg)]),
            )
            return

        for nome in self.posfixo:
            if nome not in nomes_na_ordem:
                nomes_na_ordem.append(nome)
                por_agente.setdefault(nome, [])

        if not orcamento_disponivel(state, len(nomes_na_ordem)):
            gastos = int(state.get(KEY_REEXECUCOES, 0) or 0)
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                content=types.Content(role="model", parts=[types.Part(text=(
                    f"⛔ {self.rotulo}: orçamento de retrabalho esgotado ({gastos} agente(s) já reexecutado(s) "
                    f"nesta execução). Os {len(nomes_na_ordem)} conserto(s) desta rodada ficam para uma pessoa; "
                    "a esteira segue e o diagnóstico final lista cada um com o dono."
                ))]),
                actions=EventActions(state_delta={KEY_PIPELINE_BLOQUEADO: True}),
            )
            return

        resumo = ", ".join(f"{n} ({len(por_agente[n])})" for n in nomes_na_ordem)
        aviso = f"🔁 {self.rotulo}: reexecutando {len(nomes_na_ordem)} agente(s) com ticket — {resumo}."
        if pendentes_externos:
            aviso += " Fora desta etapa (não reexecutado): " + ", ".join(pendentes_externos) + "."
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=aviso)]),
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
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                actions=EventActions(state_delta={self.tickets_key: tickets}),
            )
            async for evento in sub.run_async(ctx):
                yield evento

        state[self.tickets_key] = ""
        gastos = int(state.get(KEY_REEXECUCOES, 0) or 0) + len(nomes_na_ordem)
        state[KEY_REEXECUCOES] = gastos
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            actions=EventActions(state_delta={self.tickets_key: "", KEY_REEXECUCOES: gastos}),
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
            delta = {self.status_key: "aprovado"}
            msg = f"⚠️ Catálogo: não consegui montar a ficha desta missão ({exc}). A execução segue."

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
        texto = relatorio_markdown(dossie, missao, artefatos)
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

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        rodada = int(state.get(self.rodada_key, 0) or 0) + 1
        reprovados = [
            k for k in self.status_keys
            if str(state.get(k, "")).strip().lower() not in self.aceitos and k in state
        ]
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

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=msg)]),
            actions=EventActions(state_delta=delta, escalate=escalate or None),
        )
