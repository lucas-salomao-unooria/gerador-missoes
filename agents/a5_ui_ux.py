"""Agente 5: Designer de Interfaces e Fluxo UI/UX."""

from typing import Optional
from google.adk.agents.llm_agent import LlmAgent
from prompts import load_prompt
from .base import create_llm_agent


def get_ui_ux_designer_agent(
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
) -> LlmAgent:
    """Retorna o Agente 5 do pipeline com prompt carregado de prompts/a5_ui_ux.md."""
    instruction = load_prompt("a5_ui_ux.md")
    return create_llm_agent(
        name="UIUXDesignerAgent",
        description="Mapeia o fluxo de telas da missão, elementos visuais de HUD e estados de interface.",
        instruction=instruction,
        output_key="ui_ux_flow",
        thinking_budget=thinking_budget,
        include_thoughts=include_thoughts,
    )
