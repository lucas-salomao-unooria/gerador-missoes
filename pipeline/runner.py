"""Execução assíncrona do pipeline (Google ADK Runner) com streaming de eventos para a UI.

Separa o fluxo de pensamento (thoughts) da saída de cada agente, acompanha o status dos
gates gravado no estado e persiste os artefatos em `output/` ao final.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from google.adk.artifacts import FileArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.callbacks import KEY_PIPELINE_BLOQUEADO, KEY_PIPELINE_MOTIVO
from config import get_settings
from pipeline.artifacts import (
    e_mensagem_de_pulo,
    generate_artifact_manifest,
    save_run_artifacts,
)
from pipeline.orchestrator import FINAL_OUTPUT_KEY, create_mission_orchestrator
from tools.doc_parser import DocumentBatch

logger = logging.getLogger("pipeline_runner")

STATUS_KEYS = [
    "catalogo_indice_status",
    "micro_gate_status",
    "micro_gate_rodada",
    "gate_estrutural_status",
    "gate_estrutural_rodada",
    "avaliacao_status", "experiencia_status", "adequacao_status", "gate_final_status",
    "bncc_status",
    "lacunas_status",
    "ambiente_status",
    "design_status", "prototipo_lint_status", "brief_escopo_status",
    "manifesto_status", "evidencia_status", "evidencia_report",
    "perguntas_status", "perguntas_report",
    "juiz_perguntas_status", "juiz_perguntas_rodada",
    "telemetria_status",
    "rastro_spec_status", "rastro_design_status",
    "rastro_lacunas_status",
    "dev_status",
    "prd_status", "kpis_status", "kpis_report",
    "diagnostico_status", "tickets_sem_rota",
    KEY_PIPELINE_BLOQUEADO,
    KEY_PIPELINE_MOTIVO,
]


@dataclass
class PipelineExecutionResult:
    """Resultado completo da execução do pipeline."""

    session_id: str
    user_id: str
    prompt: str
    final_output: str
    step_outputs: Dict[str, str] = field(default_factory=dict)
    step_thoughts: Dict[str, str] = field(default_factory=dict)
    attached_files: List[str] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)
    events_log: List[Dict[str, Any]] = field(default_factory=list)
    artifacts_manifest: List[Dict[str, Any]] = field(default_factory=list)
    duration_seconds: float = 0.0
    status: str = "success"
    error_message: Optional[str] = None
    output_dir: Optional[str] = None

    @property
    def gates(self) -> Dict[str, Any]:
        return {k: self.state.get(k) for k in STATUS_KEYS if k in self.state}

    @property
    def has_blocked_gate(self) -> bool:
        return any(
            str(v).strip().lower() in ("bloqueado", "blocked", "reprovado", "vermelho", "🔴")
            for v in self.gates.values()
        )

    @property
    def bloqueado(self) -> bool:
        return bool(self.state.get(KEY_PIPELINE_BLOQUEADO)) or self.status in ("blocked", "bloqueado")

    @property
    def bypassed(self) -> bool:
        return not self.bloqueado and (self.status == "bypassed" or self.has_blocked_gate)

    @property
    def prd_gerado(self) -> Optional[str]:
        """O PRD, quando ele existe de fato — não a mensagem de pulo do agente."""
        prd = self.state.get("prd_final")
        return None if not prd or e_mensagem_de_pulo(prd) else prd

    @property
    def gate_que_bloqueou(self) -> Optional[str]:
        """O motivo registrado pelo primeiro gate a bloquear, para a tela não inventar culpado."""
        return self.state.get(KEY_PIPELINE_MOTIVO) or None

    @property
    def status_icon(self) -> str:
        if self.bloqueado:
            return "🔴"
        if self.bypassed:
            return "🟡"
        if self.status in ("success", "aprovado"):
            return "🟢"
        return "⚪"


def _perguntas_do_po(briefing: str) -> str:
    """Bloco `## Perguntas de produto` do briefing. Falha aqui nunca derruba a execução."""
    try:
        from tools.kpis import extrair_perguntas_do_briefing

        return extrair_perguntas_do_briefing(briefing)
    except Exception:  # pragma: no cover - conveniência
        return ""


def build_user_message(prompt: str, doc_batch: Optional[DocumentBatch]) -> types.Content:
    """Mensagem do usuário: texto (+ documentos de texto inline) e PDFs como Parts binárias.

    DOCX, Markdown e TXT entram no próprio texto; o PDF vai como Part nativa (o modelo lê o
    arquivo), então o texto extraído dele não é repetido aqui.
    """
    enriched_prompt = prompt
    parts: List[types.Part] = []

    if doc_batch and doc_batch.documents:
        blocos = [
            f"### 📄 Documento de apoio ({doc.file_type.upper()}): {doc.name}\n\n{doc.markdown_text}"
            for doc in doc_batch.documents
            if not doc.is_native_pdf and doc.markdown_text
        ]
        if blocos:
            enriched_prompt = (
                f"{prompt}\n\n---\n## 📎 Documentos de apoio anexados (texto)\n\n"
                + "\n\n".join(blocos)
            )

    parts.append(types.Part.from_text(text=enriched_prompt))

    if doc_batch and doc_batch.documents:
        for doc in doc_batch.documents:
            if doc.is_native_pdf and doc.pdf_bytes:
                parts.append(types.Part.from_bytes(data=doc.pdf_bytes, mime_type="application/pdf"))

    return types.Content(role="user", parts=parts)


_build_user_message = build_user_message  # nome antigo, mantido para quem já importava


#: Cabeçalho do material guardado quando ele volta à mensagem numa correção de produto.
CABECALHO_MATERIAL_GUARDADO = "## 📎 Documentos de apoio anexados (texto) — guardados da geração original"


def mensagem_do_usuario(prompt: str, doc_batch: Optional[DocumentBatch],
                        initial_state: Optional[Dict[str, Any]], stages: Optional[List[str]]) -> types.Content:
    """A mensagem que o núcleo narrativo lê — o único agente que a lê.

    Numa correção que refaz produto não há anexo novo: sem remontar o material guardado da
    geração original, o núcleo seria refeito sem o material do Entre Redes que o gerou.
    """
    material_salvo = str((initial_state or {}).get("material_anexado") or "")
    if not doc_batch and material_salvo and "produto" in (stages or []):
        return build_user_message(f"{prompt}\n\n---\n{CABECALHO_MATERIAL_GUARDADO}\n\n{material_salvo}", None)
    return build_user_message(prompt, doc_batch)


def material_dos_anexos(doc_batch: Optional[DocumentBatch]) -> str:
    """O texto integral de cada anexo, para o estado — sem limite de tamanho, de propósito.

    Até 23/09/2026 o conteúdo dos anexos existia só na mensagem, e só o núcleo narrativo a lê.
    A spec, a avaliação pedagógica e o one-pager resumido são instruídos a usar o material do
    Entre Redes como fonte primária de código BNCC e componente curricular e nunca o viam: 5 das
    7 sessões que anexaram o material entregaram um resumido dizendo "material não anexado". E
    a sessão guardava só os nomes, então uma correção que refizesse produto perdia o material.
    O PDF vai ao modelo como arquivo; aqui entra o texto extraído dele, que é o que um agente
    sem a mensagem consegue ler.
    """
    if not doc_batch or not doc_batch.documents:
        return ""
    blocos: List[str] = []
    for doc in doc_batch.documents:
        texto = (doc.markdown_text or "").strip()
        if texto:
            blocos.append(f"### 📄 Documento de apoio ({doc.file_type.upper()}): {doc.name}\n\n{texto}")
        else:
            blocos.append(f"### 📄 {doc.name} — anexado, mas sem texto extraível (PDF digitalizado?). "
                          "O conteúdo não pôde ser guardado; considere só o que o briefing diz sobre ele.")
    return "\n\n".join(blocos)


def catalogo_para_prompt() -> str:
    """O índice de missões geradas, em tabela, para os prompts que comparam com o catálogo."""
    try:
        from tools.catalogo import carregar, tabela_markdown

        return tabela_markdown(carregar().get("missoes", []))
    except Exception:  # memória é conveniência: sem índice, os prompts seguem com o markdown
        return ""


def briefing_inicial(initial_state: Optional[Dict[str, Any]], prompt: str) -> str:
    """O `briefing` da sessão: o salvo vence o `prompt`.

    Numa execução nova não há estado salvo e o prompt é o briefing. Numa correção o estado
    traz o briefing original e o `prompt` repete-o; o pedido de correção viaja noutra chave
    (`pedido_correcao`), nunca por aqui — senão `{briefing?}` e `briefing-original.md` passariam
    a descrever a correção em vez da missão.
    """
    return str((initial_state or {}).get("briefing") or prompt or "")


def _pick_final_output(state: Dict[str, Any], step_outputs: Dict[str, str], fallback: str) -> str:
    """PRD quando existe; senão o relatório mais relevante do ponto onde o pipeline parou."""
    for key in (FINAL_OUTPUT_KEY, "gate_final_report", "gate_estrutural_report", "spec_missao"):
        value = state.get(key)
        if value:
            return str(value)
    return fallback


async def run_orchestrator_pipeline_stream(
    prompt: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    orchestrator_name: str = "MissionPipelineOrchestrator",
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
    modo_estrito: Optional[bool] = None,
    stages: Optional[List[str]] = None,
    doc_batch: Optional[DocumentBatch] = None,
    save_artifacts: bool = True,
    initial_state: Optional[Dict[str, Any]] = None,
    run_dir: Optional[Path] = None,
    registrar_conversa: bool = True,
    com_transversal: bool = True,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Executa o pipeline e emite eventos: pipeline_started, agent_started, agent_chunk,
    agent_thought_chunk, gate_status, pipeline_completed | pipeline_error."""
    settings = get_settings()
    user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"
    session_id = session_id or f"session_{uuid.uuid4().hex[:8]}"
    start_time = time.time()
    attached_names = [d.name for d in doc_batch.documents] if doc_batch else []

    yield {
        "type": "pipeline_started",
        "user_id": user_id,
        "session_id": session_id,
        "prompt": prompt,
        "attached_files": attached_names,
        "timestamp": start_time,
    }

    try:
        orchestrator = create_mission_orchestrator(
            name=orchestrator_name,
            thinking_budget=thinking_budget,
            include_thoughts=include_thoughts,
            modo_estrito=modo_estrito,
            stages=stages,
            com_transversal=com_transversal,
        )
        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name=orchestrator_name,
            user_id=user_id,
            session_id=session_id,
            # `briefing` alimenta o `{briefing?}` do P0b, que não vê a mensagem original
            # `initial_state` reexecuta uma etapa sobre o estado salvo de uma execução anterior
            # (`scripts/rerodar_etapa.py`): produto e design ficam fixos e só a etapa pedida roda.
            state={
                **(initial_state or {}),
                "briefing": briefing_inicial(initial_state, prompt),
                # O texto integral dos anexos: o salvo vence, porque numa correção não há anexo
                # novo — o material da geração original é o que vale.
                "material_anexado": str((initial_state or {}).get("material_anexado") or "")
                                    or material_dos_anexos(doc_batch),
                # O PO declara as perguntas de produto no briefing, em português; a esteira as
                # normaliza para a tabela do sub-bloco 9f. Sem o bloco, fica vazio e o agente
                # propõe, marcando `[PROPOSTA — validar com PO]` — proposta não bloqueia.
                "perguntas_po": _perguntas_do_po(briefing_inicial(initial_state, prompt)),
                # A memória do gerador chega aos prompts pelo estado, não por include: o índice vive
                # no bucket (`output/`), que persiste, enquanto `prompts/` vem da imagem do container.
                "catalogo_missoes": catalogo_para_prompt(),
            },
        )
        adk_artifacts_dir = settings.output_path / ".adk_artifacts"
        adk_artifacts_dir.mkdir(parents=True, exist_ok=True)
        artifact_service = FileArtifactService(adk_artifacts_dir)

        runner = Runner(
            app_name=orchestrator_name,
            agent=orchestrator,
            session_service=session_service,
            artifact_service=artifact_service,
        )
        user_message = mensagem_do_usuario(prompt, doc_batch, initial_state, stages)

        step_outputs: Dict[str, str] = {}
        step_thoughts: Dict[str, str] = {}
        events_log: List[Dict[str, Any]] = []
        final_text = ""
        current_agent: Optional[str] = None
        known_status: Dict[str, Any] = {}
        # Custo por agente. O `usage_metadata` de cada evento era descartado, então ninguém
        # sabia quanto custa gerar uma missão nem qual agente pesa — e sem isso não há como
        # decidir onde cortar contexto, nem justificar o gasto.
        tokens_por_agente: Dict[str, Dict[str, int]] = {}

        async for event in runner.run_async(user_id=user_id, session_id=session.id, new_message=user_message):
            author = getattr(event, "author", None) or "Orchestrator"

            uso = getattr(event, "usage_metadata", None)
            if uso is not None:
                reg = tokens_por_agente.setdefault(author, {"entrada": 0, "saida": 0, "pensamento": 0, "chamadas": 0})
                reg["entrada"] += int(getattr(uso, "prompt_token_count", 0) or 0)
                reg["saida"] += int(getattr(uso, "candidates_token_count", 0) or 0)
                reg["pensamento"] += int(getattr(uso, "thoughts_token_count", 0) or 0)
                reg["chamadas"] += 1

            if author != current_agent and author != "user":
                current_agent = author
                yield {"type": "agent_started", "agent_name": author, "timestamp": time.time()}

            thought_parts: List[str] = []
            output_parts: List[str] = []
            tool_calls: List[str] = []
            content = getattr(event, "content", None)
            if content and getattr(content, "parts", None):
                for part in content.parts:
                    text = getattr(part, "text", "") or ""
                    if getattr(part, "thought", False) and text:
                        thought_parts.append(text)
                    elif text:
                        output_parts.append(text)
                    fc = getattr(part, "function_call", None)
                    if fc is not None and getattr(fc, "name", None):
                        tool_calls.append(fc.name)

            if tool_calls:
                yield {"type": "agent_tool_call", "agent_name": author, "tools": tool_calls, "timestamp": time.time()}

            chunk_thought = "".join(thought_parts)
            chunk_output = "".join(output_parts)

            if chunk_thought:
                step_thoughts[author] = step_thoughts.get(author, "") + chunk_thought
                yield {
                    "type": "agent_thought_chunk",
                    "agent_name": author,
                    "thought": chunk_thought,
                    "accumulated_thoughts": step_thoughts[author],
                    "timestamp": time.time(),
                }

            if chunk_output:
                # eventos parciais (streaming) acumulam; eventos finais substituem
                if getattr(event, "partial", False):
                    step_outputs[author] = step_outputs.get(author, "") + chunk_output
                else:
                    step_outputs[author] = chunk_output
                final_text = chunk_output
                yield {
                    "type": "agent_chunk",
                    "agent_name": author,
                    "chunk": chunk_output,
                    "accumulated": step_outputs[author],
                    "timestamp": time.time(),
                }

            # mudanças de status dos gates (state_delta dos EnvelopeGateAgent)
            delta = getattr(getattr(event, "actions", None), "state_delta", None) or {}
            status_delta = {k: v for k, v in delta.items() if k in STATUS_KEYS}
            if status_delta:
                known_status.update(status_delta)
                yield {"type": "gate_status", "agent_name": author, "status": dict(known_status), "timestamp": time.time()}

            events_log.append(
                {
                    "author": author,
                    "has_thoughts": bool(chunk_thought),
                    "tools": tool_calls,
                    "text_preview": (chunk_output or chunk_thought)[:120],
                    "timestamp": time.time(),
                }
            )

        final_session = await session_service.get_session(
            app_name=orchestrator_name, user_id=user_id, session_id=session.id
        )
        final_state = dict(final_session.state) if final_session else {}
        duration = time.time() - start_time

        # Bloco de execução: o que torna uma execução reproduzível e comparável com a seguinte.
        # Sem ele não havia como responder "quanto custa gerar uma missão", "qual agente pesa"
        # nem "estamos melhorando?" — os mesmos ~20 achados reapareciam sessão após sessão e
        # nada media a tendência.
        totais = {
            "entrada": sum(v["entrada"] for v in tokens_por_agente.values()),
            "saida": sum(v["saida"] for v in tokens_por_agente.values()),
            "pensamento": sum(v["pensamento"] for v in tokens_por_agente.values()),
            "chamadas": sum(v["chamadas"] for v in tokens_por_agente.values()),
        }
        settings_exec = get_settings()
        final_state["execucao"] = {
            "modelo": settings_exec.gemini_model,
            "modelo_prd": settings_exec.gemini_model_prd,
            "seed_juiz": settings_exec.seed_juiz,
            "temperatura_juiz": settings_exec.temperatura_juiz,
            "duracao_s": round(duration, 1),
            "tokens": totais,
            "tokens_por_agente": dict(sorted(tokens_por_agente.items(),
                                             key=lambda kv: -(kv[1]["entrada"] + kv[1]["saida"]))),
        }

        output_dir: Optional[Path] = None
        artifacts_manifest: List[Dict[str, Any]] = []
        if save_artifacts:
            try:
                output_dir = save_run_artifacts(
                    state=final_state,
                    session_id=session_id,
                    prompt=prompt,
                    artifact_service=artifact_service,
                    app_name=orchestrator_name,
                    user_id=user_id,
                    run_dir=run_dir,
                )
                if output_dir:
                    artifacts_manifest = generate_artifact_manifest(output_dir)
                if output_dir and com_transversal:
                    # Catálogo e histórico são da missão inteira: com parecer humano a esteira roda
                    # uma etapa por vez, e só a rodada final (a transversal) registra — senão cada
                    # etapa viraria uma linha no histórico, e uma ficha velha no estado seria
                    # registrada de novo a cada passagem.
                    # Memória entre execuções: só aqui existe o nome da pasta, que é a chave da
                    # entrada no índice. Falhar aqui não pode custar a execução inteira.
                    try:
                        from tools.catalogo import registrar as registrar_no_catalogo

                        ficha = final_state.get("ficha_catalogo_dados")
                        if isinstance(ficha, dict):
                            registrar_no_catalogo({**ficha, "sessao": output_dir.name})
                    except Exception as exc:  # pragma: no cover - disco
                        logger.warning("Falha ao registrar a missão no catálogo: %s", exc)
                    # Série temporal: os mesmos ~20 identificadores de achado reapareciam
                    # sessão após sessão e nada media a tendência. Uma linha por execução,
                    # append-only, ao lado do índice. Falhar aqui também não custa a execução.
                    try:
                        from tools.historico import registrar as registrar_no_historico

                        registrar_no_historico(final_state, sessao=output_dir.name)
                    except Exception as exc:  # pragma: no cover - disco
                        logger.warning("Falha ao registrar no histórico: %s", exc)
            except Exception as exc:  # pragma: no cover - disco
                logger.warning("Falha ao gravar artefatos: %s", exc)

        is_blocked = bool(final_state.get(KEY_PIPELINE_BLOQUEADO))
        gates_dict = {k: final_state.get(k) for k in STATUS_KEYS if k in final_state}
        has_blocked_gate = any(
            str(v).strip().lower() in ("bloqueado", "blocked", "reprovado", "vermelho", "🔴")
            for v in gates_dict.values()
        )

        if is_blocked:
            run_status = "blocked"
        elif has_blocked_gate:
            run_status = "bypassed"
        else:
            run_status = "success"

        result = PipelineExecutionResult(
            session_id=session_id,
            user_id=user_id,
            prompt=prompt,
            final_output=_pick_final_output(final_state, step_outputs, final_text),
            step_outputs=step_outputs,
            step_thoughts=step_thoughts,
            attached_files=attached_names,
            state=final_state,
            events_log=events_log,
            artifacts_manifest=artifacts_manifest,
            duration_seconds=duration,
            status=run_status,
            output_dir=str(output_dir) if output_dir else None,
        )

        # A correção de uma sessão (`pipeline/reexecucao.py`) grava a conversa por conta própria,
        # preservando histórico e data: aqui ela pede `registrar_conversa=False`.
        if output_dir and save_artifacts and registrar_conversa:
            try:
                from pipeline.session_store import save_session_record
                assistant_msg = (
                    "🟡 **PRD gerado com ressalvas (gates bypassados).** Veja as abas abaixo."
                    if result.bypassed and result.state.get("prd_final")
                    else (result.state.get("prd_final") and "📘 **PRD gerado.** Veja as abas abaixo." or result.final_output)
                )
                initial_msgs = [
                    {"role": "user", "content": prompt},
                    {
                        "role": "assistant",
                        "content": assistant_msg,
                    },
                ]
                save_session_record(
                    run_dir=output_dir,
                    session_id=session_id,
                    user_id=user_id,
                    prompt=prompt,
                    result=result,
                    messages=initial_msgs,
                    attached_files=attached_names,
                )
            except Exception as exc:
                logger.warning("Falha ao registrar histórico de conversa: %s", exc)

        yield {"type": "pipeline_completed", "result": result, "duration": duration, "timestamp": time.time()}

    except Exception as exc:
        duration = time.time() - start_time
        logger.exception("Erro durante execução do pipeline ADK: %s", exc)
        error_result = PipelineExecutionResult(
            session_id=session_id,
            user_id=user_id,
            prompt=prompt,
            final_output=f"❌ Erro na execução do pipeline: {exc}",
            duration_seconds=duration,
            status="error",
            error_message=str(exc),
        )
        yield {"type": "pipeline_error", "error": str(exc), "result": error_result, "duration": duration, "timestamp": time.time()}


def run_orchestrator_pipeline_sync(
    prompt: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    **kwargs: Any,
) -> PipelineExecutionResult:
    """Helper síncrono para execução em linha de comando."""

    async def _runner() -> PipelineExecutionResult:
        last: Optional[PipelineExecutionResult] = None
        async for event in run_orchestrator_pipeline_stream(prompt=prompt, user_id=user_id, session_id=session_id, **kwargs):
            if event["type"] in ("pipeline_completed", "pipeline_error"):
                last = event["result"]
        return last or PipelineExecutionResult(
            session_id=session_id or "unknown",
            user_id=user_id or "unknown",
            prompt=prompt,
            final_output="Nenhum evento final retornado.",
            status="error",
        )

    return asyncio.run(_runner())
