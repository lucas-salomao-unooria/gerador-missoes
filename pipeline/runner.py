"""Módulo de execução assíncrona do Pipeline Orquestrador do Google ADK.
Gerencia sessões, dispara a execução sequencial dos 8 agentes e emite eventos em tempo real para a UI,
incluindo separação do fluxo de pensamento (Thinking / Chain-of-Thought) do Gemini 3.7 Flash.
"""

import asyncio
from dataclasses import dataclass, field
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
import uuid
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from tools.doc_parser import DocumentBatch

logger = logging.getLogger("pipeline_runner")


@dataclass
class PipelineExecutionResult:
    """Resultado completo da execução do pipeline orquestrador."""

    session_id: str
    user_id: str
    prompt: str
    final_output: str
    step_outputs: Dict[str, str] = field(default_factory=dict)
    step_thoughts: Dict[str, str] = field(default_factory=dict)
    attached_files: List[str] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)
    events_log: List[Dict[str, Any]] = field(default_factory=list)
    duration_seconds: float = 0.0
    status: str = "success"
    error_message: Optional[str] = None


async def run_orchestrator_pipeline_stream(
    prompt: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    orchestrator_name: str = "MissionPipelineOrchestrator",
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
    doc_batch: Optional[DocumentBatch] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Executa o pipeline orquestrador de 8 agentes via Google ADK e emite eventos em streaming.

    Suporta entrada multimodal nativa de arquivos PDF e enriquecimento textual de arquivos DOCX.
    """
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
        # 1. Instancia o Orquestrador Sequencial e o Serviço de Sessão com os limites configurados
        orchestrator = create_mission_orchestrator(
            name=orchestrator_name,
            thinking_budget=thinking_budget,
            include_thoughts=include_thoughts,
        )
        session_service = InMemorySessionService()

        # 2. Cria a sessão no ADK
        session = await session_service.create_session(
            app_name=orchestrator_name,
            user_id=user_id,
            session_id=session_id,
            state={},
        )

        # 3. Prepara o Runner oficial do ADK
        runner = Runner(
            app_name=orchestrator_name,
            agent=orchestrator,
            session_service=session_service,
        )

        # 4. Formata a mensagem do usuário (Suporte Multimodal a PDF + DOCX)
        user_parts: List[types.Part] = []
        enriched_prompt = prompt

        if doc_batch and doc_batch.documents:
            docx_blocks = []
            for doc in doc_batch.documents:
                if not doc.is_native_pdf and doc.markdown_text:
                    docx_blocks.append(f"### 📄 Documento de Apoio (Word/DOCX): {doc.name}\n\n{doc.markdown_text}")

            if docx_blocks:
                enriched_prompt = (
                    f"{prompt}\n\n"
                    f"---\n"
                    f"## 📎 Documentos de Apoio Anexados (Convertidos do Word):\n"
                    + "\n\n".join(docx_blocks)
                )

        user_parts.append(types.Part.from_text(text=enriched_prompt))

        # Injeta PDFs NATIVAMENTE como Parts binárias (visão computacional + layout)
        if doc_batch and doc_batch.documents:
            for doc in doc_batch.documents:
                if doc.is_native_pdf and doc.pdf_bytes:
                    user_parts.append(
                        types.Part.from_bytes(
                            data=doc.pdf_bytes,
                            mime_type="application/pdf",
                        )
                    )

        user_message = types.Content(
            role="user",
            parts=user_parts,
        )

        step_outputs: Dict[str, str] = {}
        step_thoughts: Dict[str, str] = {}
        events_log: List[Dict[str, Any]] = []
        final_text = ""
        current_agent: Optional[str] = None

        # 5. Executa assincronamente e processa os eventos dos subagentes
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=user_message,
        ):
            event_author = getattr(event, "author", None) or "Orchestrator"

            # Notifica início de um novo agente
            if event_author and event_author != current_agent and event_author != "user":
                current_agent = event_author
                yield {
                    "type": "agent_started",
                    "agent_name": current_agent,
                    "timestamp": time.time(),
                }

            # Extração separada de Pensamentos (Thoughts) vs Saída Final (Output)
            thought_text_parts = []
            output_text_parts = []

            if hasattr(event, "content") and event.content and hasattr(event.content, "parts"):
                for part in event.content.parts:
                    part_text = getattr(part, "text", "") or ""
                    is_thought = getattr(part, "thought", False)

                    if is_thought and part_text:
                        thought_text_parts.append(part_text)
                    elif part_text:
                        output_text_parts.append(part_text)

            chunk_thought = "".join(thought_text_parts)
            chunk_output = "".join(output_text_parts)

            # Emite eventos de pensamento
            if chunk_thought:
                if event_author:
                    step_thoughts[event_author] = (
                        step_thoughts.get(event_author, "") + chunk_thought
                    )
                yield {
                    "type": "agent_thought_chunk",
                    "agent_name": event_author,
                    "thought": chunk_thought,
                    "accumulated_thoughts": step_thoughts.get(event_author, ""),
                    "timestamp": time.time(),
                }

            # Emite eventos de resposta
            if chunk_output:
                if event_author:
                    step_outputs[event_author] = (
                        step_outputs.get(event_author, "") + chunk_output
                    )
                final_text = chunk_output

                yield {
                    "type": "agent_chunk",
                    "agent_name": event_author,
                    "chunk": chunk_output,
                    "accumulated": step_outputs.get(event_author, ""),
                    "timestamp": time.time(),
                }

            # Registra no log estruturado de eventos
            events_log.append(
                {
                    "author": event_author,
                    "has_thoughts": bool(chunk_thought),
                    "text_preview": (chunk_output or chunk_thought)[:100],
                    "timestamp": time.time(),
                }
            )

        # 6. Recupera o estado final acumulado da sessão
        final_session = await session_service.get_session(
            app_name=orchestrator_name,
            user_id=user_id,
            session_id=session.id,
        )
        final_state = final_session.state if final_session else {}

        duration = time.time() - start_time

        # Se houver relatório final em QAValidatorAgent ou no output_key final, usa como final_output principal
        if "final_delivery_report" in final_state:
            final_output = str(final_state["final_delivery_report"])
        elif "QAValidatorAgent" in step_outputs:
            final_output = step_outputs["QAValidatorAgent"]
        else:
            final_output = final_text

        result = PipelineExecutionResult(
            session_id=session_id,
            user_id=user_id,
            prompt=prompt,
            final_output=final_output,
            step_outputs=step_outputs,
            step_thoughts=step_thoughts,
            attached_files=attached_names,
            state=final_state,
            events_log=events_log,
            duration_seconds=duration,
            status="success",
        )

        yield {
            "type": "pipeline_completed",
            "result": result,
            "duration": duration,
            "timestamp": time.time(),
        }

    except Exception as exc:
        duration = time.time() - start_time
        logger.exception(f"Erro durante execução do pipeline ADK: {exc}")
        
        error_result = PipelineExecutionResult(
            session_id=session_id,
            user_id=user_id,
            prompt=prompt,
            final_output=f"❌ Erro na execução do pipeline: {str(exc)}",
            duration_seconds=duration,
            status="error",
            error_message=str(exc),
        )

        yield {
            "type": "pipeline_error",
            "error": str(exc),
            "result": error_result,
            "duration": duration,
            "timestamp": time.time(),
        }


def run_orchestrator_pipeline_sync(
    prompt: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> PipelineExecutionResult:
    """Helper síncrono para execução do pipeline em testes de linha de comando."""

    async def _runner() -> PipelineExecutionResult:
        last_result: Optional[PipelineExecutionResult] = None
        async for event in run_orchestrator_pipeline_stream(
            prompt=prompt, user_id=user_id, session_id=session_id
        ):
            if event["type"] in ("pipeline_completed", "pipeline_error"):
                last_result = event["result"]
        return last_result or PipelineExecutionResult(
            session_id=session_id or "unknown",
            user_id=user_id or "unknown",
            prompt=prompt,
            final_output="Nenhum evento final retornado.",
            status="error",
        )

    return asyncio.run(_runner())
