"""Integração com o Figma via Model Context Protocol (MCP) no Google ADK.

Três modos, escolhidos por `FIGMA_MCP_MODE`:

- ``remote``  → servidor oficial ``https://mcp.figma.com/mcp`` (Streamable HTTP, OAuth 2.1).
                É o único modo com **escrita** (``use_figma``, ``create_new_file``,
                ``generate_diagram``) e com FigJam. O token OAuth é obtido uma vez por
                ``python scripts/figma_oauth.py`` e renovado automaticamente pelo
                ``header_provider`` abaixo. Alternativa: ``FIGMA_MCP_BEARER_TOKEN`` estático.
- ``desktop`` → servidor local do app Figma Desktop (``http://127.0.0.1:3845/mcp``), sem auth.
                Leitura de design; escrita depende da versão do app.
- ``stdio``   → ``figma-developer-mcp`` via ``npx`` (comunidade, só leitura, usa PAT).
- ``off``     → nenhum toolset; os agentes de design produzem os artefatos em Markdown/Mermaid.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from mcp import StdioServerParameters

from config import PROJECT_ROOT, get_settings

logger = logging.getLogger("figma_mcp")

# Ferramentas do servidor oficial do Figma, agrupadas por uso.
FIGMA_TOOLS_READ = [
    "get_design_context",
    "get_screenshot",
    "get_metadata",
    "get_variable_defs",
    "get_figjam",
    "get_libraries",
    "search_design_system",
    "whoami",
]
FIGMA_TOOLS_SKILLS = ["get_figma_skill", "read_skill_uri"]
FIGMA_TOOLS_WRITE = ["create_new_file", "use_figma", "generate_diagram", "upload_assets"]

FIGMA_TOOLS_JORNADA = FIGMA_TOOLS_SKILLS + ["whoami", "create_new_file", "use_figma", "get_figjam", "get_screenshot"]
FIGMA_TOOLS_FLUXO = FIGMA_TOOLS_SKILLS + ["use_figma", "generate_diagram", "get_figjam", "get_screenshot"]
FIGMA_TOOLS_WIREFRAMES = FIGMA_TOOLS_SKILLS + [
    "whoami",
    "create_new_file",
    "use_figma",
    "search_design_system",
    "get_libraries",
    "get_variable_defs",
    "get_metadata",
    "get_screenshot",
]
FIGMA_TOOLS_QA = FIGMA_TOOLS_SKILLS + [
    "get_design_context",
    "get_screenshot",
    "get_metadata",
    "get_variable_defs",
    "get_figjam",
    "use_figma",
]


# --------------------------------------------------------------------------- OAuth
class FigmaOAuthTokenStore:
    """Lê (e renova) os tokens OAuth gravados por ``scripts/figma_oauth.py``."""

    def __init__(self, path: Path):
        self.path = path

    def load(self) -> Optional[Dict[str, Any]]:
        if not self.path.exists():
            return None
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - arquivo corrompido
            logger.warning("Arquivo de tokens do Figma ilegível (%s): %s", self.path, exc)
            return None

    def save(self, data: Dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def access_token(self) -> str:
        data = self.load()
        if not data:
            return ""
        tokens = data.get("tokens") or {}
        expires_at = data.get("expires_at")
        if expires_at and time.time() > float(expires_at) - 60 and tokens.get("refresh_token"):
            refreshed = self._refresh(data)
            if refreshed:
                return refreshed
        return tokens.get("access_token", "")

    def _refresh(self, data: Dict[str, Any]) -> str:
        try:
            import httpx  # dependência transitiva do mcp

            token_endpoint = data.get("token_endpoint")
            client_info = data.get("client_info") or {}
            tokens = data.get("tokens") or {}
            if not token_endpoint or not tokens.get("refresh_token"):
                return ""
            payload = {
                "grant_type": "refresh_token",
                "refresh_token": tokens["refresh_token"],
                "client_id": client_info.get("client_id", ""),
            }
            if client_info.get("client_secret"):
                payload["client_secret"] = client_info["client_secret"]
            resp = httpx.post(token_endpoint, data=payload, timeout=30)
            resp.raise_for_status()
            novo = resp.json()
            tokens.update({k: v for k, v in novo.items() if k in ("access_token", "refresh_token", "expires_in", "scope", "token_type")})
            data["tokens"] = tokens
            if novo.get("expires_in"):
                data["expires_at"] = time.time() + float(novo["expires_in"])
            self.save(data)
            logger.info("Token OAuth do Figma renovado.")
            return tokens.get("access_token", "")
        except Exception as exc:  # pragma: no cover - rede
            logger.warning("Falha ao renovar token OAuth do Figma: %s", exc)
            return ""


def _remote_header_provider(context: ReadonlyContext) -> Dict[str, str]:
    """Monta o header Authorization a cada sessão MCP (token estático ou OAuth renovável)."""
    settings = get_settings()
    if settings.figma_mcp_bearer_token:
        return {"Authorization": f"Bearer {settings.figma_mcp_bearer_token}"}
    store = FigmaOAuthTokenStore(PROJECT_ROOT / settings.figma_mcp_oauth_tokens_file)
    token = store.access_token()
    return {"Authorization": f"Bearer {token}"} if token else {}


# ------------------------------------------------------------------------ Toolsets
def get_figma_toolset(tool_filter: Optional[List[str]] = None) -> Optional[McpToolset]:
    """Instancia o McpToolset do Figma conforme ``FIGMA_MCP_MODE``. Retorna ``None`` em ``off``."""
    settings = get_settings()
    mode = settings.figma_mcp_mode

    if mode == "off":
        return None

    if mode == "remote":
        logger.info("Figma MCP remoto: %s", settings.figma_mcp_remote_url)
        return McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=settings.figma_mcp_remote_url,
                timeout=settings.mcp_timeout_seconds,
                sse_read_timeout=settings.mcp_read_timeout_seconds,
            ),
            header_provider=_remote_header_provider,
            tool_filter=tool_filter,
        )

    if mode == "desktop":
        logger.info("Figma MCP desktop: %s", settings.figma_mcp_desktop_url)
        return McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=settings.figma_mcp_desktop_url,
                timeout=settings.mcp_timeout_seconds,
                sse_read_timeout=settings.mcp_read_timeout_seconds,
            ),
            tool_filter=tool_filter,
        )

    if mode == "stdio":
        env_vars = dict(os.environ)
        if settings.figma_api_key:
            env_vars["FIGMA_API_KEY"] = settings.figma_api_key
            env_vars["FIGMA_PERSONAL_ACCESS_TOKEN"] = settings.figma_api_key
        logger.info("Figma MCP stdio: %s %s", settings.figma_mcp_command, settings.figma_mcp_args)
        return McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=settings.figma_mcp_command,
                    args=settings.figma_mcp_args,
                    env=env_vars,
                ),
                timeout=settings.mcp_timeout_seconds,
            ),
            # o servidor da comunidade só expõe get_figma_data / download_figma_images
            tool_filter=None,
        )

    logger.warning("FIGMA_MCP_MODE desconhecido (%s); Figma desligado.", mode)
    return None


def figma_tools_or_empty(tool_filter: Optional[List[str]] = None) -> List[Any]:
    """Lista de tools para um agente: [toolset] ou [] quando o Figma está desligado."""
    toolset = get_figma_toolset(tool_filter)
    return [toolset] if toolset is not None else []
