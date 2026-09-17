"""Integração com o Google Stitch via Model Context Protocol (MCP) no Google ADK.

O Stitch (Google Labs) gera telas de interface a partir de descrição em texto e as
publica num projeto navegável. Aqui ele ocupa o lugar que o Figma ocupava no D5
(wireframes) e no D7 (conferência), com uma diferença que precisa estar clara para
quem lê o PRD: **o Stitch não lê o Design System da Unooria**. O que ele devolve é
referência visual navegável, não especificação de componente. A especificação
continua sendo o Markdown de cobertura, que nomeia os componentes do DS.

Dois modos, escolhidos por ``STITCH_MCP_MODE``:

- ``remote``  → endpoint MCP oficial ``https://stitch.googleapis.com/mcp``, com
                ``X-Goog-Api-Key``. É o caminho direto, sem Node no meio.
- ``proxy``   → ``npx @_davideast/stitch-mcp proxy`` por stdio. Existe por um motivo
                concreto: o backend do Stitch devolve schemas com ``$ref`` para
                ``$defs`` que ele mesmo omite, e o proxy os conserta antes de o
                cliente validar. Se o modo ``remote`` falhar ao listar ferramentas,
                é quase certo que seja isso — troque para ``proxy``.
                **Armadilha conhecida:** o proxy lê o `.env` da pasta onde roda e
                quebra com "invalid character 'd'" se o arquivo tiver algo que ele
                não saiba interpretar. Este repositório TEM `.env` na raiz.
- ``off``     → nenhum toolset; o D5 entrega a cobertura em Markdown, que é o que os
                agentes seguintes consomem de qualquer forma.

As ferramentas pesadas do Stitch (código HTML da tela, imagem em base64, download de
asset) **não são expostas de propósito**: o agente precisa do link, não do arquivo, e
foi resposta de ferramenta desse tamanho que estourou o teto de contexto do modelo na
etapa de jornada. Ver `agents/callbacks.py`.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from mcp import StdioServerParameters

from config import get_settings

logger = logging.getLogger("stitch_mcp")

#: Construção: criar o projeto, ensinar a ele a escala de cinza e gerar uma tela por
#: estado. Conferido contra o servidor em 2026-09-17 (15 ferramentas publicadas).
#:
#: O caminho que funciona, nesta ordem: `create_project` → `upload_design_md` com os
#: nove tokens → `list_design_systems` para pegar o `assetId` que o Stitch montou →
#: `generate_screen_from_text` passando esse `designSystem` em toda tela. Sem o
#: `designSystem`, cada tela sai com um tema diferente.
STITCH_TOOLS_WIREFRAMES = [
    "create_project",
    "list_projects",
    "get_project",
    "upload_design_md",
    "create_design_system",
    "list_design_systems",
    "apply_design_system",
    "generate_screen_from_text",
    "edit_screens",
    "list_screens",
    "get_screen",
]

#: Conferência: só leitura.
STITCH_TOOLS_QA = ["list_projects", "get_project", "list_screens", "get_screen", "list_design_systems"]

#: Não expostas de propósito:
#: - `delete_project` é destrutivo e nenhum agente precisa apagar nada;
#: - `generate_variants` multiplica o custo de geração sem servir a wireframe lo-fi;
#: - `update_design_system` e `create_design_system_from_design_md` sobrepõem o
#:   caminho do `upload_design_md`, que já é o mais simples.
STITCH_TOOLS_FORA = [
    "delete_project",
    "generate_variants",
    "update_design_system",
    "create_design_system_from_design_md",
]


def _remote_header_provider(context: ReadonlyContext) -> Dict[str, str]:
    """Autenticação do endpoint oficial: chave de API no header, como o SDK faz."""
    settings = get_settings()
    if settings.stitch_api_key:
        return {"X-Goog-Api-Key": settings.stitch_api_key}
    if settings.stitch_access_token:
        headers = {"Authorization": f"Bearer {settings.stitch_access_token}"}
        if settings.stitch_quota_project_id:
            headers["X-Goog-User-Project"] = settings.stitch_quota_project_id
        return headers
    return {}


def get_stitch_toolset(tool_filter: Optional[List[str]] = None) -> Optional[McpToolset]:
    """Instancia o McpToolset do Stitch conforme ``STITCH_MCP_MODE``. ``None`` em ``off``."""
    settings = get_settings()
    mode = settings.stitch_mcp_mode

    if mode == "off":
        return None

    if mode == "remote":
        if not (settings.stitch_api_key or settings.stitch_access_token):
            logger.warning("STITCH_MCP_MODE=remote sem STITCH_API_KEY; Stitch desligado.")
            return None
        logger.info("Stitch MCP remoto: %s", settings.stitch_mcp_remote_url)
        return McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=settings.stitch_mcp_remote_url,
                timeout=settings.mcp_timeout_seconds,
                sse_read_timeout=settings.mcp_read_timeout_seconds,
            ),
            header_provider=_remote_header_provider,
            tool_filter=tool_filter,
        )

    if mode == "proxy":
        env_vars = dict(os.environ)
        if settings.stitch_api_key:
            env_vars["STITCH_API_KEY"] = settings.stitch_api_key
        logger.info("Stitch MCP proxy: %s %s", settings.stitch_mcp_command, settings.stitch_mcp_args)
        return McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=settings.stitch_mcp_command,
                    args=settings.stitch_mcp_args,
                    env=env_vars,
                ),
                timeout=settings.mcp_timeout_seconds,
            ),
            tool_filter=tool_filter,
        )

    logger.warning("STITCH_MCP_MODE desconhecido (%s); Stitch desligado.", mode)
    return None


def stitch_tools_or_empty(tool_filter: Optional[List[str]] = None) -> List[Any]:
    """Lista de tools para um agente: ``[toolset]`` ou ``[]`` quando o Stitch está desligado."""
    toolset = get_stitch_toolset(tool_filter)
    return [toolset] if toolset is not None else []


def url_do_projeto(project_id: str) -> str:
    """URL pública do projeto, para o relatório e o PRD."""
    base = get_settings().stitch_project_url_base.rstrip("/")
    return f"{base}/{project_id}"
