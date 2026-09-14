"""Persistência dos artefatos de uma execução em `output/<data>-<slug>/` com suporte a ADK Artifacts e links Figma."""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.callbacks import extrair_slug
from config import get_settings

logger = logging.getLogger("artifacts")

# Ordem e nome de arquivo por chave de estado
ARTIFACT_FILES = [
    ("one_pager", "produto/00-one-pager.md"),
    ("gate_estrutural_report", "produto/01-gate-estrutural.md"),
    ("avaliacao_pedagogica_report", "produto/02-avaliacao-pedagogica.md"),
    ("experiencia_aluno_report", "produto/03-experiencia-aluno.md"),
    ("gate_final_report", "produto/04-gate-final.md"),
    ("spec_missao", "produto/05-spec-missao.md"),
    ("brief_oficio", "design/01-briefing-oficio.md"),
    ("jornada_telas", "design/02-jornada-telas.md"),
    ("fluxo_arestas", "design/03-fluxo-arestas.md"),
    ("copy_strings", "design/04-copy-strings.md"),
    ("camada_caa", "design/04b-camada-caa.md"),
    ("wireframes_cobertura", "design/05-wireframes-cobertura.md"),
    ("copy_strings_revisada", "design/06-copy-strings-revisada.md"),
    ("qa_entregaveis_report", "design/07-qa-entregaveis.md"),
    ("handoff_dev", "dev/01-handoff-dev.md"),
    ("brief_assets", "dev/01b-brief-assets.md"),
    ("validacao_produto_narrativa", "dev/02a-banca-produto-narrativa.md"),
    ("validacao_design_imersao", "dev/02b-banca-design-imersao.md"),
    ("validacao_pedagogia_bncc", "dev/02c-banca-pedagogia-bncc.md"),
    ("validacao_dados_lgpd", "dev/02d-banca-dados-lgpd.md"),
    ("validacao_tecnica_arquitetura", "dev/02e-banca-tecnica-arquitetura.md"),
    ("validacao_dev_report", "dev/03-banca-consolidada.md"),
    ("prd_final", "PRD.md"),
    ("aprendizado_registro", "aprendizado.md"),
]

STAGE_NAMES = {
    "produto": "🧭 Produto",
    "design": "🎨 Design",
    "dev": "🛠️ Dev",
    "figma": "🎨 Figma",
}

FIGMA_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?figma\.com/(?:file|design|board)/([a-zA-Z0-9]+)(?:/[^ \n\r\t\)\"\`\<\>]+)?",
    re.IGNORECASE,
)


def _safe(name: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-") or "missao"


def extract_figma_links(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extrai URLs, fileKeys e referências ao Figma/FigJam das saídas dos agentes."""
    found_urls: Dict[str, Dict[str, Any]] = {}

    keys_to_scan = [
        "jornada_telas",
        "fluxo_arestas",
        "wireframes_cobertura",
        "qa_entregaveis_report",
        "brief_oficio",
        "spec_missao",
        "prd_final",
    ]

    for key in keys_to_scan:
        content = state.get(key)
        if not content or not isinstance(content, str):
            continue

        for line in content.splitlines():
            matches = FIGMA_URL_PATTERN.finditer(line)
            for m in matches:
                url = m.group(0).rstrip(".,;:)")
                file_key = m.group(1)

                # Extrai node-id se houver
                node_match = re.search(r"node-id=([a-zA-Z0-9%:-]+)", line)
                node_id = node_match.group(1) if node_match else None

                # Se já temos esse arquivo e a ocorrência atual não tem node_id, mantém a existente
                if file_key in found_urls and not node_id:
                    continue

                # Tenta inferir título do link
                title = "Link Figma"
                if "board" in url or "figjam" in url.lower() or "jornada" in line.lower():
                    title = "Board no FigJam (Jornada)"
                elif "fluxo" in line.lower():
                    title = "Diagrama de Fluxo (FigJam)"
                elif "wireframe" in line.lower() or "design" in url:
                    title = "Wireframes no Figma"
                elif "ds" in line.lower() or "design system" in line.lower():
                    title = "Design System Unooria"

                found_urls[file_key] = {
                    "url": url,
                    "file_key": file_key,
                    "node_id": node_id,
                    "title": title,
                    "source_agent_key": key,
                    "snippet": line.strip()[:160],
                }

    return list(found_urls.values())


def generate_artifact_manifest(run_dir: Path) -> List[Dict[str, Any]]:
    """Gera um manifesto descritivo de todos os artefatos salvos em `run_dir`."""
    manifest: List[Dict[str, Any]] = []

    for path in sorted(run_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(run_dir).as_posix()
        if rel.startswith(".") or rel == "manifesto-artefatos.json":
            continue

        size = path.stat().st_size
        size_str = f"{size / 1024:.1f} KB" if size >= 1024 else f"{size} B"

        # Categoria
        parts = rel.split("/")
        category = "Raiz"
        if len(parts) > 1:
            category = STAGE_NAMES.get(parts[0], parts[0].capitalize())

        mime_type, _ = mimetypes.guess_type(path.name)
        if not mime_type:
            mime_type = "text/markdown" if path.suffix == ".md" else "application/json"

        manifest.append(
            {
                "path": rel,
                "filename": path.name,
                "category": category,
                "size_bytes": size,
                "size_str": size_str,
                "mime_type": mime_type,
            }
        )

    return manifest


async def _save_adk_artifacts(
    run_dir: Path,
    app_name: str,
    user_id: str,
    session_id: str,
    artifact_service: Any,
) -> int:
    """Registra artefatos no FileArtifactService do Google ADK."""
    if not artifact_service:
        return 0

    from google.genai import types

    count = 0
    for path in run_dir.rglob("*"):
        if not path.is_file() or path.name.startswith("."):
            continue
        rel = path.relative_to(run_dir).as_posix()
        mime_type, _ = mimetypes.guess_type(path.name)
        mime_type = mime_type or ("text/markdown" if path.suffix == ".md" else "application/octet-stream")

        try:
            data = path.read_bytes()
            part = types.Part.from_bytes(data=data, mime_type=mime_type)
            await artifact_service.save_artifact(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                filename=rel,
                artifact=part,
            )
            count += 1
        except Exception as exc:
            logger.debug("Aviso ao registrar artefato ADK %s: %s", rel, exc)

    return count


def save_run_artifacts(
    state: Dict[str, Any],
    session_id: str,
    prompt: str = "",
    artifact_service: Optional[Any] = None,
    app_name: str = "GeradorMissoesUnooria",
    user_id: str = "usuario",
) -> Optional[Path]:
    """Grava cada saída do pipeline como Markdown, links do Figma, manifesto e estado completo em JSON."""
    settings = get_settings()
    base = settings.output_path
    slug = extrair_slug(str(state.get("spec_missao") or state.get("one_pager") or "")) or _safe(session_id[:12])
    run_dir = base / f"{time.strftime('%Y%m%d-%H%M%S')}-{_safe(slug)}"
    run_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    for key, rel in ARTIFACT_FILES:
        value = state.get(key)
        if not value:
            continue
        path = run_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        text = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False)
        path.write_text(text.strip() + "\n", encoding="utf-8")
        written += 1

    # Extrai e grava links do Figma/FigJam encontrados nos artefatos
    figma_links = extract_figma_links(state)
    if figma_links:
        figma_dir = run_dir / "figma"
        figma_dir.mkdir(parents=True, exist_ok=True)
        (figma_dir / "figma-links.json").write_text(
            json.dumps(figma_links, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        md_lines = ["# 🎨 Links e Artefatos do Figma\n"]
        for link in figma_links:
            md_lines.append(f"### [{link['title']}]({link['url']})")
            md_lines.append(f"- **URL:** `{link['url']}`")
            md_lines.append(f"- **FileKey:** `{link['file_key']}`")
            if link.get("node_id"):
                md_lines.append(f"- **Node ID:** `{link['node_id']}`")
            md_lines.append(f"- **Origem:** `{link['source_agent_key']}`\n")
        (figma_dir / "figma-links.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    # Estado serializável
    serializable = {k: v for k, v in state.items() if not str(k).startswith("temp:")}
    (run_dir / "estado.json").write_text(
        json.dumps(serializable, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )

    if prompt:
        (run_dir / "briefing-original.md").write_text(prompt.strip() + "\n", encoding="utf-8")

    # Manifesto de artefatos
    manifest = generate_artifact_manifest(run_dir)
    (run_dir / "manifesto-artefatos.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Registro no FileArtifactService do ADK caso fornecido
    if artifact_service:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Agenda no loop corrente se async
                asyncio.create_task(
                    _save_adk_artifacts(run_dir, app_name, user_id, session_id, artifact_service)
                )
            else:
                loop.run_until_complete(
                    _save_adk_artifacts(run_dir, app_name, user_id, session_id, artifact_service)
                )
        except Exception as exc:
            logger.debug("Não foi possível registrar no serviço ADK de forma síncrona: %s", exc)

    return run_dir if written else run_dir
