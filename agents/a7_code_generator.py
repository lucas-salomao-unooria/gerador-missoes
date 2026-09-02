"""Agente 7: Gerador de Código e Configurações Executáveis."""

from typing import Optional
from google.adk.agents.llm_agent import LlmAgent
from prompts import load_prompt
from .base import create_llm_agent


def get_code_generator_agent(
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
) -> LlmAgent:
    """Retorna o Agente 7 do pipeline com prompt carregado de prompts/a7_code_generator.md."""
    instruction = load_prompt("a7_code_generator.md")
    return create_llm_agent(
        name="CodeGeneratorAgent",
        description="Gera código fonte Python executável da missão, schemas JSON e testes unitários.",
        instruction=instruction,
        output_key="generated_implementation",
        thinking_budget=thinking_budget,
        include_thoughts=include_thoughts,
    )
