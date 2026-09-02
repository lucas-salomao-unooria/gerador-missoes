"""Agente 3: Arquiteto da Missão e Narrativa."""

from typing import Optional
from google.adk.agents.llm_agent import LlmAgent
from prompts import load_prompt
from .base import create_llm_agent


def get_mission_architect_agent(
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
) -> LlmAgent:
    """Retorna o Agente 3 do pipeline com prompt carregado de prompts/a3_mission_architect.md."""
    instruction = load_prompt("a3_mission_architect.md")
    return create_llm_agent(
        name="MissionArchitectAgent",
        description="Elabora o roteiro, narrativa, fases de progressão e matriz de objetivos da missão.",
        instruction=instruction,
        output_key="mission_architecture",
        thinking_budget=thinking_budget,
        include_thoughts=include_thoughts,
    )
