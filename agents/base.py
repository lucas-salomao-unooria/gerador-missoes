"""Utilitários base e fábricas para criação de LLM Agents do Google ADK."""

from typing import Any, List, Optional
from google.adk.agents.llm_agent import LlmAgent
from google.genai import types
from config import get_settings


def create_llm_agent(
    name: str,
    instruction: str,
    description: str,
    output_key: Optional[str] = None,
    tools: Optional[List[Any]] = None,
    model: Optional[str] = None,
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
) -> LlmAgent:
    """Cria uma instância padronizada de LlmAgent para o pipeline ADK com controle de Thinking.

    Args:
        name: Identificador único do agente no pipeline.
        instruction: Prompt / instrução do sistema com suporte a interpolação {state_key}.
        description: Descrição do propósito do agente para observabilidade e orquestração.
        output_key: Chave de estado onde o resultado será armazenado para agentes seguintes.
        tools: Lista de ferramentas ou Toolsets (ex: McpToolset) disponíveis para o agente.
        model: Nome do modelo Gemini (caso não informado, usa o valor de AppSettings).
        thinking_budget: Orçamento de tokens para raciocínio (0=off, -1=auto, >0=tokens).
        include_thoughts: Se True, expõe os passos de pensamento Chain-of-Thought.

    Returns:
        Instância configurada de LlmAgent.
    """
    settings = get_settings()
    selected_model = model or getattr(settings, "gemini_model", "gemini-3.7-flash")

    # Configurações de Thinking (Raciocínio)
    t_budget = thinking_budget if thinking_budget is not None else getattr(settings, "thinking_budget", 2048)
    inc_thoughts = include_thoughts if include_thoughts is not None else getattr(settings, "include_thoughts", True)

    agent_kwargs: dict[str, Any] = {
        "name": name,
        "model": selected_model,
        "instruction": instruction.strip(),
        "description": description.strip(),
    }

    # Configuração de Geração com ThinkingConfig para Gemini 3.7 Flash
    thinking_params: dict[str, Any] = {}
    if t_budget is not None:
        thinking_params["thinking_budget"] = t_budget
    if inc_thoughts is not None:
        thinking_params["include_thoughts"] = inc_thoughts

    if thinking_params:
        agent_kwargs["generate_content_config"] = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(**thinking_params)
        )

    if output_key:
        agent_kwargs["output_key"] = output_key

    if tools:
        agent_kwargs["tools"] = tools

    return LlmAgent(**agent_kwargs)
