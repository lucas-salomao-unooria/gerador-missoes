"""Ferramentas dos agentes do Google ADK (MCP do Figma, parser de documentos)."""

from .figma_mcp import (
    FIGMA_TOOLS_FLUXO,
    FIGMA_TOOLS_JORNADA,
    FIGMA_TOOLS_QA,
    FIGMA_TOOLS_WIREFRAMES,
    figma_tools_or_empty,
    get_figma_toolset,
)

__all__ = [
    "FIGMA_TOOLS_FLUXO",
    "FIGMA_TOOLS_JORNADA",
    "FIGMA_TOOLS_QA",
    "FIGMA_TOOLS_WIREFRAMES",
    "figma_tools_or_empty",
    "get_figma_toolset",
]
