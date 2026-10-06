"""Pacote de prompts dos agentes (Markdown) e utilitários de carga."""

from . import base_plataforma
from .loader import (
    PROMPTS_DIR,
    REFERENCES_DIR,
    get_prompt_raw,
    list_prompt_files,
    list_state_variables,
    load_prompt,
    resolve_includes,
    save_prompt,
)

__all__ = [
    "PROMPTS_DIR",
    "REFERENCES_DIR",
    "get_prompt_raw",
    "list_prompt_files",
    "list_state_variables",
    "load_prompt",
    "resolve_includes",
    "save_prompt",
    "base_plataforma",
]
