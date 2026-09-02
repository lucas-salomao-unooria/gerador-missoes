"""Módulo de integração com o Figma via Model Context Protocol (MCP) no Google ADK.
Instancia o McpToolset oficial do ADK conectado ao servidor figma-developer-mcp via Stdio.
"""

import logging
import os
from mcp import StdioServerParameters
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from config import get_settings

logger = logging.getLogger("figma_mcp")


def get_figma_toolset() -> McpToolset:
    """Instancia o McpToolset do Google ADK para o servidor MCP do Figma.
    
    Executa o servidor figma-developer-mcp via npx em modo stdio,
    expondo as ferramentas nativas do MCP:
      - get_figma_data(fileKey, nodeId, depth)
      - download_figma_images(fileKey, nodes, localPath, pngScale)
    """
    settings = get_settings()

    # Prepara as variáveis de ambiente necessárias para o subprocesso
    env_vars = dict(os.environ)
    figma_key = settings.figma_api_key or os.getenv("FIGMA_API_KEY", "")
    if figma_key:
        env_vars["FIGMA_API_KEY"] = figma_key
        env_vars["FIGMA_PERSONAL_ACCESS_TOKEN"] = figma_key

    logger.info(
        f"Instanciando Figma McpToolset: comando={settings.figma_mcp_command}, "
        f"args={settings.figma_mcp_args}"
    )

    server_params = StdioServerParameters(
        command=settings.figma_mcp_command,
        args=settings.figma_mcp_args,
        env=env_vars,
    )

    toolset = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=server_params,
            timeout=settings.mcp_timeout_seconds,
        )
    )

    return toolset
