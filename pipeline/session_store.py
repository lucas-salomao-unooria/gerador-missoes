"""Armazenamento e gerenciamento persistente de sessões e histórico de conversas."""

from __future__ import annotations

import io
import json
import logging
import os
import re
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import get_settings
from pipeline.artifacts import ARTIFACT_FILES, extract_figma_links, extrair_slug

logger = logging.getLogger("session_store")


def _safe_str(val: Any) -> str:
    return str(val) if val is not None else ""


def extrair_titulo_missao(state: Dict[str, Any], fallback: str = "Missão Sem Título") -> str:
    """Extrai o título amigável da missão a partir do one-pager ou spec."""
    spec = _safe_str(state.get("spec_missao") or state.get("one_pager"))
    if not spec:
        return fallback

    # Procura 'Nome que o estudante vê: ...'
    m_nome = re.search(r"\*?\*?Nome que o estudante vê:\*?\*?\s*([^\n\r]+)", spec, re.IGNORECASE)
    if m_nome:
        clean = m_nome.group(1).strip().strip("*_`\"'")
        if clean:
            return clean

    # Procura '# One-pager — ...' ou '# Spec — ...'
    m_header = re.search(r"^#\s+(?:One-pager|Spec)\s+[—-]\s+([^\n\r]+)", spec, re.MULTILINE | re.IGNORECASE)
    if m_header:
        clean = m_header.group(1).strip().strip("*_`\"'")
        # remove versão no final ex: v1.0
        clean = re.sub(r"\s+v\d+(?:\.\d+)?.*$", "", clean).strip()
        if clean:
            return clean

    slug = extrair_slug(spec)
    return slug or fallback


def list_saved_sessions() -> List[Dict[str, Any]]:
    """Lista todas as sessões salvas em `output/`, ordenadas pela mais recente."""
    settings = get_settings()
    base_dir = settings.output_path

    if not base_dir.exists():
        return []

    sessions: List[Dict[str, Any]] = []

    for entry in base_dir.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            continue

        estado_file = entry / "estado.json"
        conversa_file = entry / "conversa.json"

        # Carrega dados do estado ou da conversa salva
        state: Dict[str, Any] = {}
        conversa_data: Dict[str, Any] = {}

        if conversa_file.exists():
            try:
                conversa_data = json.loads(conversa_file.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Falha ao ler %s: %s", conversa_file, exc)

        if estado_file.exists():
            try:
                state = json.loads(estado_file.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Falha ao ler %s: %s", estado_file, exc)

        # Determina o título
        title = conversa_data.get("title") or extrair_titulo_missao(state, fallback=entry.name)
        slug = conversa_data.get("slug") or extrair_slug(str(state.get("spec_missao") or state.get("one_pager") or "")) or entry.name

        # Timestamp de criação
        timestamp_str = conversa_data.get("created_at")
        if not timestamp_str:
            # Tenta extrair da pasta YYYYMMDD-HHMMSS
            m_time = re.match(r"^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})", entry.name)
            if m_time:
                y, m, d, h, mi, s = m_time.groups()
                timestamp_str = f"{d}/{m}/{y} {h}:{mi}"
            else:
                mtime = entry.stat().st_mtime
                timestamp_str = time.strftime("%d/%m/%Y %H:%M", time.localtime(mtime))

        # Status
        status = conversa_data.get("status")
        if not status:
            if state.get("pipeline_bloqueado"):
                status = "bloqueado"
            elif (entry / "PRD.md").exists() or state.get("prd_final"):
                status = "aprovado"
            elif (entry / "produto/04-gate-final.md").exists():
                status = "bloqueado"
            else:
                status = "indefinido"

        status_icon = "🟢" if status in ("aprovado", "success") else ("🔴" if status in ("bloqueado", "blocked") else "⚪")

        # Prompt original
        prompt = conversa_data.get("prompt") or ""
        if not prompt and (entry / "briefing-original.md").exists():
            try:
                prompt = (entry / "briefing-original.md").read_text(encoding="utf-8").strip()
            except Exception:
                prompt = ""

        # Contagem de arquivos úteis
        md_files = list(entry.glob("**/*.md"))

        sessions.append(
            {
                "dir_name": entry.name,
                "path": str(entry),
                "title": title,
                "slug": slug,
                "session_id": conversa_data.get("session_id") or entry.name,
                "created_at": timestamp_str,
                "status": status,
                "status_icon": status_icon,
                "has_prd": (entry / "PRD.md").exists(),
                "prompt": prompt,
                "files_count": len(md_files),
                "mtime": entry.stat().st_mtime,
            }
        )

    # Ordena decrescente pelo tempo de modificação
    sessions.sort(key=lambda s: s["mtime"], reverse=True)
    return sessions


def load_saved_session(dir_name_or_id: str) -> Optional[Tuple[List[Dict[str, Any]], Any, Dict[str, Any]]]:
    """Carrega uma sessão salva do disco.
    
    Retorna uma tupla (messages, pipeline_result, metadata) ou None se não encontrada.
    """
    settings = get_settings()
    base_dir = settings.output_path

    target_dir = base_dir / dir_name_or_id
    if not target_dir.exists():
        # Busca por session_id
        for d in base_dir.iterdir():
            if d.is_dir() and dir_name_or_id in d.name:
                target_dir = d
                break

    if not target_dir.exists() or not target_dir.is_dir():
        return None

    state: Dict[str, Any] = {}
    estado_file = target_dir / "estado.json"
    if estado_file.exists():
        try:
            state = json.loads(estado_file.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Falha ao carregar estado de %s: %s", estado_file, exc)

    conversa_data: Dict[str, Any] = {}
    conversa_file = target_dir / "conversa.json"
    if conversa_file.exists():
        try:
            conversa_data = json.loads(conversa_file.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Falha ao carregar conversa de %s: %s", conversa_file, exc)

    prompt = conversa_data.get("prompt") or ""
    if not prompt and (target_dir / "briefing-original.md").exists():
        try:
            prompt = (target_dir / "briefing-original.md").read_text(encoding="utf-8").strip()
        except Exception:
            prompt = ""

    # Constrói step_outputs a partir dos arquivos salvos se não estiver no conversa_data
    step_outputs = conversa_data.get("step_outputs", {})
    if not step_outputs:
        for key, rel in ARTIFACT_FILES:
            fpath = target_dir / rel
            if fpath.exists():
                try:
                    step_outputs[key] = fpath.read_text(encoding="utf-8")
                except Exception:
                    pass

    # Importa PipelineExecutionResult tardiamente para evitar imports circulares
    from pipeline.runner import PipelineExecutionResult

    final_output = state.get("prd_final") or state.get("spec_missao") or state.get("gate_final_report") or ""
    status = conversa_data.get("status") or ("blocked" if state.get("pipeline_bloqueado") else "success")

    result = PipelineExecutionResult(
        session_id=conversa_data.get("session_id") or target_dir.name,
        user_id=conversa_data.get("user_id") or "saved_user",
        prompt=prompt,
        final_output=final_output,
        step_outputs=step_outputs,
        step_thoughts=conversa_data.get("step_thoughts", {}),
        attached_files=conversa_data.get("attached_files", []),
        state=state,
        duration_seconds=conversa_data.get("duration_seconds", 0.0),
        status=status,
        output_dir=str(target_dir),
    )

    # Reconstrói messages
    messages: List[Dict[str, Any]] = []
    if conversa_data.get("messages"):
        for m in conversa_data["messages"]:
            messages.append({
                "role": m.get("role", "user"),
                "content": m.get("content", ""),
                "pipeline_result": result if m.get("role") == "assistant" else None,
            })
    else:
        # Reconstrói mensagens padrão se não havia conversa.json
        if prompt:
            messages.append({"role": "user", "content": prompt})
        summary = state.get("prd_final") and "📘 **PRD gerado.** Veja as abas abaixo." or final_output
        messages.append({
            "role": "assistant",
            "content": summary if len(summary) < 4000 else "Resultado do pipeline:",
            "pipeline_result": result,
        })

    metadata = {
        "dir_name": target_dir.name,
        "path": str(target_dir),
        "title": conversa_data.get("title") or extrair_titulo_missao(state, target_dir.name),
        "slug": conversa_data.get("slug") or extrair_slug(str(state.get("spec_missao") or "")),
        "session_id": result.session_id,
        "status": status,
        "created_at": conversa_data.get("created_at"),
    }

    return messages, result, metadata


def save_session_record(
    run_dir: Path,
    session_id: str,
    user_id: str,
    prompt: str,
    result: Any,
    messages: List[Dict[str, Any]],
    attached_files: Optional[List[str]] = None,
) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    state = getattr(result, "state", {}) or {}
    if not state and (run_dir / "estado.json").exists():
        try:
            state = json.loads((run_dir / "estado.json").read_text(encoding="utf-8"))
        except Exception:
            state = {}

    title = extrair_titulo_missao(state, fallback=prompt[:60].strip() or "Missão")
    slug = extrair_slug(str(state.get("spec_missao") or state.get("one_pager") or "")) or session_id[:12]

    # Serializa mensagens sem o pipeline_result interno
    serializable_messages = []
    for m in messages:
        serializable_messages.append({
            "role": m.get("role", "user"),
            "content": m.get("content", ""),
        })

    data = {
        "session_id": session_id,
        "user_id": user_id,
        "title": title,
        "slug": slug,
        "created_at": time.strftime("%d/%m/%Y %H:%M:%S"),
        "prompt": prompt,
        "attached_files": attached_files or getattr(result, "attached_files", []),
        "status": getattr(result, "status", "success"),
        "duration_seconds": getattr(result, "duration_seconds", 0.0),
        "gates": getattr(result, "gates", {}),
        "messages": serializable_messages,
        "step_thoughts": getattr(result, "step_thoughts", {}),
    }

    conversa_path = run_dir / "conversa.json"
    conversa_path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return conversa_path


def delete_saved_session(dir_name_or_id: str) -> bool:
    """Remove o diretório de uma sessão salva."""
    settings = get_settings()
    base_dir = settings.output_path

    target_dir = base_dir / dir_name_or_id
    if not target_dir.exists():
        for d in base_dir.iterdir():
            if d.is_dir() and dir_name_or_id in d.name:
                target_dir = d
                break

    if target_dir.exists() and target_dir.is_dir():
        try:
            shutil.rmtree(target_dir)
            return True
        except Exception as exc:
            logger.error("Erro ao deletar sessão %s: %s", target_dir, exc)
            return False
    return False


def create_session_zip(run_dir_path: str | Path) -> bytes:
    """Gera um arquivo ZIP em memória com todos os artefatos da missão."""
    run_dir = Path(run_dir_path)
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in run_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                rel_path = file_path.relative_to(run_dir)
                zf.write(file_path, arcname=str(rel_path))

    buffer.seek(0)
    return buffer.getvalue()
