"""Agente 1: Analisador de Requisitos e Escopo da Missão."""

from typing import Optional
from google.adk.agents.llm_agent import LlmAgent
from prompts import load_prompt
from .base import create_llm_agent


def get_requirements_agent(
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
) -> LlmAgent:
    """Retorna o Agente 1 do pipeline com prompt carregado de prompts/a1_requirements.md."""
    instruction = load_prompt("a1_requirements.md")
    return create_llm_agent(
        name="RequirementsAgent",
        description="Analisa a intenção do usuário e gera a especificação estruturada de requisitos.",
        instruction=instruction,
        output_key="requirements_spec",
        thinking_budget=thinking_budget,
        include_thoughts=include_thoughts,
    )
