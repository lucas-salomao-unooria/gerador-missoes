"""Agente TRANSVERSAL — aprendizado (memória do processo).

Roda ao final do pipeline e registra: linha do catálogo, padrões aprendidos,
lacunas com dono e classe, candidatos a critério e propostas de emenda.
Nunca edita prompt de agente; escreve propostas para `prompts/references/`.
"""

from __future__ import annotations

from typing import Optional

from google.adk.agents.llm_agent import LlmAgent

from agents.base import create_llm_agent
from prompts import load_prompt


def get_aprendizado_agent(
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
) -> LlmAgent:
    return create_llm_agent(
        name="AprendizadoAgent",
        description="Registra o que a execução ensinou: catálogo, padrões, lacunas por classe e candidatos a critério.",
        instruction=load_prompt("transversal/t_aprendizado.md"),
        output_key="aprendizado_registro",
        thinking_budget=thinking_budget,
        include_thoughts=include_thoughts,
    )


TRANSVERSAL_METADATA = [
    {"id": "AprendizadoAgent", "name": "T · Aprendizado", "icon": "🧠", "output_key": "aprendizado_registro", "prompt_file": "transversal/t_aprendizado.md", "description": "Catálogo, padrões aprendidos, lacunas com dono/classe, candidatos a critério."},
]
