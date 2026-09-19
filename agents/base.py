"""Fábrica padronizada de LlmAgent para o pipeline (Google ADK)."""

from __future__ import annotations

import time
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
    include_contents: str = "none",
    before_agent_callback: Any = None,
    after_agent_callback: Any = None,
    before_tool_callback: Any = None,
    after_tool_callback: Any = None,
) -> LlmAgent:
    """Cria um LlmAgent com ThinkingConfig e callbacks padronizados.

    Args:
        name: identificador único do agente (usado como `author` dos eventos).
        instruction: prompt de sistema; `{chave}` é interpolada do session.state pelo ADK.
        description: propósito do agente (observabilidade).
        output_key: chave do session.state onde a resposta final é gravada.
        tools: ferramentas/toolsets (ex.: McpToolset do Stitch).
        model: modelo Gemini (padrão: AppSettings.gemini_model).
        thinking_budget / include_thoughts: controle de raciocínio.
        include_contents: 'none' (padrão — o agente trabalha só com a instrução interpolada
            e o turno corrente) ou 'default' (recebe o histórico completo da conversa).
        before_agent_callback / after_agent_callback: callbacks do ADK.
        before_tool_callback / after_tool_callback: idem para ferramentas. Quando há
            `tools` e nada é passado, entram os limitadores de contexto de
            `agents.callbacks` — resposta de ferramenta MCP é a maior fonte de estouro
            do teto do modelo, e o histórico de chamada não é descartado por
            `include_contents="none"`.
    """
    settings = get_settings()
    selected_model = model or settings.gemini_model

    t_budget = thinking_budget if thinking_budget is not None else settings.thinking_budget
    inc_thoughts = include_thoughts if include_thoughts is not None else settings.include_thoughts

    kwargs: dict[str, Any] = {
        "name": name,
        "model": selected_model,
        # O bloco de herança entra em TODOS os agentes de uma vez, em vez de ser repetido em
        # ~30 prompts. Fica vazio na execução saudável; quando um gate reprova, é por ele que
        # o agente a jusante descobre que constrói sobre base reprovada — e é o que permite a
        # esteira seguir até o fim sem fingir que está tudo certo.
        "instruction": (
            instruction.strip()
            + "\n\n---\n## Herança desta execução\n\n{heranca_degradada?}\n"
            + f"\n---\nData de hoje: {time.strftime('%Y-%m-%d')}. Use esta data em cabeçalhos, changelogs e frontmatter."
        ),
        "description": description.strip(),
        "include_contents": include_contents,
    }

    thinking_params: dict[str, Any] = {}
    if t_budget is not None:
        thinking_params["thinking_budget"] = t_budget
    if inc_thoughts is not None:
        thinking_params["include_thoughts"] = inc_thoughts
    if thinking_params:
        kwargs["generate_content_config"] = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(**thinking_params)
        )

    if output_key:
        kwargs["output_key"] = output_key
    if tools:
        kwargs["tools"] = tools
        # Contenção padrão: sem ela, um agente que constrói artefato por MCP acumula
        # dezenas de respostas de ferramenta, dumps e imagens no mesmo turno, e o
        # modelo recusa a requisição com 400.
        from agents.callbacks import barrar_ferramenta_sem_orcamento, limitar_resposta_de_ferramenta

        kwargs["before_tool_callback"] = before_tool_callback or barrar_ferramenta_sem_orcamento
        kwargs["after_tool_callback"] = after_tool_callback or limitar_resposta_de_ferramenta
    else:
        if before_tool_callback is not None:
            kwargs["before_tool_callback"] = before_tool_callback
        if after_tool_callback is not None:
            kwargs["after_tool_callback"] = after_tool_callback
    if before_agent_callback is not None:
        kwargs["before_agent_callback"] = before_agent_callback
    if after_agent_callback is not None:
        kwargs["after_agent_callback"] = after_agent_callback

    return LlmAgent(**kwargs)
