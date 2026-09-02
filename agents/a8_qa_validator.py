"""Agente 8: Auditor de QA, Consistência e Relatório de Validação."""

from typing import Optional
from google.adk.agents.llm_agent import LlmAgent
from prompts import load_prompt
from .base import create_llm_agent


def get_qa_validator_agent(
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
) -> LlmAgent:
    """Retorna o Agente 8 do pipeline com prompt carregado de prompts/a8_qa_validator.md."""
    instruction = load_prompt("a8_qa_validator.md")
    return create_llm_agent(
        name="QAValidatorAgent",
        description="Audita rigorosamente as entregas das etapas anteriores, validando consistência e conformidade.",
        instruction=instruction,
        output_key="final_delivery_report",
        thinking_budget=thinking_budget,
        include_thoughts=include_thoughts,
    )
