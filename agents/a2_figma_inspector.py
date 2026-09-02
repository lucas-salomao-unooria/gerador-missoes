"""Agente 2: Inspetor e Integrador Figma (Equipado com Figma Developer MCP)."""

import os
from typing import Any, List, Optional
from google.adk.agents.llm_agent import LlmAgent
from config import get_settings
from prompts import load_prompt
from tools.figma_mcp import get_figma_toolset
from .base import create_llm_agent


def get_figma_inspector_agent(
    tools: Optional[List[Any]] = None,
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
) -> LlmAgent:
    """Retorna o Agente 2 do pipeline equipado com o Toolset do Figma Developer MCP e prompt de prompts/a2_figma_inspector.md."""
    settings = get_settings()
    folder_url_default = "https://www.figma.com/files/team/1669801444374741311/folder/648533591?fuid=1669362530798509991"
    folder_url = getattr(settings, "figma_default_folder_url", os.getenv("FIGMA_DEFAULT_FOLDER_URL", folder_url_default))
    folder_id = getattr(settings, "figma_folder_id", os.getenv("FIGMA_FOLDER_ID", "648533591"))
    team_id = getattr(settings, "figma_team_id", os.getenv("FIGMA_TEAM_ID", "1669801444374741311"))

    instruction = load_prompt(
        "a2_figma_inspector.md",
        figma_folder_url=folder_url,
        figma_folder_id=folder_id,
        figma_team_id=team_id,
    )

    if tools is None:
        figma_toolset = get_figma_toolset()
        tools_list = [figma_toolset]
    else:
        tools_list = tools

    return create_llm_agent(
        name="FigmaInspectorAgent",
        description="Agente integrado ao Figma Developer MCP (get_figma_data, download_figma_images) para inspeção e extração de dados de design na pasta configurada.",
        instruction=instruction,
        output_key="figma_design_context",
        tools=tools_list,
        thinking_budget=thinking_budget,
        include_thoughts=include_thoughts,
    )
