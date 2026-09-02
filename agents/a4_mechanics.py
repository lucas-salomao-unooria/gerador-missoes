"""Agente 4: Motor de Regras e Mecânicas de Jogo."""

from typing import Optional
from google.adk.agents.llm_agent import LlmAgent
from prompts import load_prompt
from .base import create_llm_agent


def get_mechanics_agent(
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
) -> LlmAgent:
    """Retorna o Agente 4 do pipeline com prompt carregado de prompts/a4_mechanics.md."""
    instruction = load_prompt("a4_mechanics.md")
    return create_llm_agent(
        name="MechanicsAgent",
        description="Estrutura a máquina de estados, regras de progressão, scoring e condições de vitória/derrota.",
        instruction=instruction,
        output_key="game_mechanics",
        thinking_budget=thinking_budget,
        include_thoughts=include_thoughts,
    )
