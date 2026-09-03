"""Persistência dos artefatos de uma execução em `output/<data>-<slug>/`."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

from agents.callbacks import extrair_slug
from config import get_settings

# ordem e nome de arquivo por chave de estado
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


def _safe(name: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-") or "missao"


def save_run_artifacts(state: Dict[str, Any], session_id: str, prompt: str = "") -> Optional[Path]:
    """Grava cada saída do pipeline como Markdown e o estado completo em JSON."""
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

    serializable = {k: v for k, v in state.items() if not str(k).startswith("temp:")}
    (run_dir / "estado.json").write_text(
        json.dumps(serializable, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    if prompt:
        (run_dir / "briefing-original.md").write_text(prompt.strip() + "\n", encoding="utf-8")
    return run_dir if written else run_dir
