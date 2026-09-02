"""Agente 6: Arquiteto de Software e Blueprint Técnico."""

from typing import Optional
from google.adk.agents.llm_agent import LlmAgent
from prompts import load_prompt
from .base import create_llm_agent


def get_tech_architect_agent(
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
) -> LlmAgent:
    """Retorna o Agente 6 do pipeline com prompt carregado de prompts/a6_tech_architect.md."""
    instruction = load_prompt("a6_tech_architect.md")
    return create_llm_agent(
        name="TechArchitectAgent",
        description="Projeta a arquitetura técnica, schemas de dados (JSON/Pydantic), APIs e barramento de eventos.",
        instruction=instruction,
        output_key="technical_blueprint",
        thinking_budget=thinking_budget,
        include_thoughts=include_thoughts,
    )
