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

import re
from typing import Any, AsyncGenerator, Dict, List, Optional

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types
from pydantic import Field
from typing_extensions import override

from tools.bncc import relatorio_markdown, validar_spec
from tools.rastro import (
    relatorio_lacunas,
    relatorio_manifesto,
    relatorio_telemetria,
    validar_manifesto,
    validar_telemetria,
    varrer_lacunas,
)

from .callbacks import (
    KEY_PIPELINE_BLOQUEADO,
    KEY_PIPELINE_MOTIVO,
    STATUS_APROVADO,
    STATUS_BLOQUEADO,
    extrair_envelope,
    extrair_slug,
    inferir_status,
)


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
                    f"⛔ {self.rotulo}: bloqueado"
                    + (f" após {rodada} rodada(s)" if self.round_key else "")
                    + ". Modo estrito ativo — design e dev não serão executados. "
                    "Veja o alerta e o relatório executivo do gate."
                )
                delta[KEY_PIPELINE_BLOQUEADO] = True
                delta[KEY_PIPELINE_MOTIVO] = f"{self.rotulo} bloqueado"
                escalate = True
            else:
                msg = (
                    f"⚠️ {self.rotulo}: bloqueado"
                    + (f" após {rodada} rodada(s)" if self.round_key else "")
                    + ". Modo estrito desligado — o pipeline segue e o PRD registrará as pendências."
                )
                escalate = bool(self.round_key)

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
        else:
            itens = "\n".join(f"- ⛔ {a['resumo']}" for a in bloqueios)
            if self.estrito:
                delta[KEY_PIPELINE_BLOQUEADO] = True
                delta[KEY_PIPELINE_MOTIVO] = f"{self.rotulo} bloqueada ({len(bloqueios)} achado(s))"
                msg = (
                    f"⛔ {self.rotulo}: bloqueada — {len(bloqueios)} achado(s). "
                    f"A esteira para aqui; design e dev não serão executados.\n{itens}"
                )
            else:
                msg = f"⚠️ {self.rotulo}: {len(bloqueios)} achado(s) — modo não estrito, o pipeline segue.\n{itens}"

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

    modo: str  # lacunas | manifesto | telemetria
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
        missao = extrair_slug(str(state.get("spec_missao", "") or "")) or ""
        if self.modo == "manifesto":
            resultado = validar_manifesto(str(state.get(self.spec_key, "") or ""))
            relatorio = relatorio_manifesto(resultado, missao)
        elif self.modo == "telemetria":
            resultado = validar_telemetria(str(state.get(self.fonte_key, "") or ""))
            relatorio = relatorio_telemetria(resultado, missao)
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
        elif status == "amarelo":
            msg = f"🟡 {self.rotulo}: {len(avisos)} pendência(s) de plataforma — o pipeline segue e o PRD sai 🟡, não verde.\n" + "\n".join(f"- ⚠️ {a.get('resumo') or a.get('trecho', '')}" for a in avisos)
        else:
            itens = "\n".join(f"- ⛔ [{a.get('etapa', 'dev')}] {a.get('resumo') or a.get('trecho', '')}" for a in bloqueios)
            if self.estrito:
                delta[KEY_PIPELINE_BLOQUEADO] = True
                delta[KEY_PIPELINE_MOTIVO] = f"{self.rotulo} bloqueado ({len(bloqueios)} lacuna(s))"
                msg = f"⛔ {self.rotulo}: bloqueado — {len(bloqueios)} lacuna(s). A esteira para aqui; o PRD não sai.\n{itens}"
            else:
                msg = f"⚠️ {self.rotulo}: {len(bloqueios)} lacuna(s) — modo não estrito, o pipeline segue.\n{itens}"

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=msg)]),
            actions=EventActions(state_delta=delta),
        )
