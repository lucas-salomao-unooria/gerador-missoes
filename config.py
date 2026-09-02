"""Módulo de configuração centralizada da aplicação (Padrão Ouro).
Carrega e valida configurações de ambiente para Google ADK, modelos Gemini e Figma MCP.
"""

from functools import lru_cache
import os
from typing import List
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Carrega variáveis do .env no início
load_dotenv(override=False)


class AppSettings(BaseSettings):
    """Configurações da aplicação e dos agentes ADK."""

    app_name: str = "MissionPipelineOrchestrator"
    app_version: str = "1.0.0"

    # Configuração do Google Gemini / ADK
    google_api_key: str = Field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", ""),
        description="Chave de API do Google Gemini",
    )
    gemini_model: str = Field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.7-flash"),
        description="Modelo padrão Gemini para os agentes",
    )
    thinking_budget: int = Field(
        default_factory=lambda: int(os.getenv("THINKING_BUDGET", "2048")),
        description="Orçamento em tokens para pensamento analítico (0 = off, -1 = dinâmico, >0 = tokens fixos)",
    )
    include_thoughts: bool = Field(
        default_factory=lambda: os.getenv("INCLUDE_THOUGHTS", "true").lower() in ("true", "1", "yes"),
        description="Expor e registrar o fluxo de pensamento dos agentes",
    )

    # Configurações do Figma e MCP
    figma_api_key: str = Field(
        default_factory=lambda: os.getenv("FIGMA_API_KEY", "")
        or os.getenv("FIGMA_PERSONAL_ACCESS_TOKEN", ""),
        description="Token de Acesso Pessoal da API do Figma",
    )
    figma_mcp_command: str = Field(
        default_factory=lambda: os.getenv("FIGMA_MCP_COMMAND", "npx"),
        description="Comando executável para o MCP do Figma",
    )
    figma_mcp_args_raw: str = Field(
        default_factory=lambda: os.getenv(
            "FIGMA_MCP_ARGS", "-y,figma-developer-mcp,--stdio"
        ),
        description="Argumentos separados por vírgula para o servidor MCP do Figma",
    )
    enable_figma_mcp_mock_fallback: bool = Field(
        default_factory=lambda: os.getenv(
            "ENABLE_FIGMA_MCP_MOCK_FALLBACK", "true"
        ).lower()
        in ("true", "1", "yes"),
        description="Permitir fallback gracioso caso o MCP do Figma não consiga se conectar",
    )

    # Pasta de destino padrão no Figma / FigJam
    figma_default_folder_url: str = Field(
        default_factory=lambda: os.getenv(
            "FIGMA_DEFAULT_FOLDER_URL",
            "https://www.figma.com/files/team/1669801444374741311/folder/648533591?fuid=1669362530798509991",
        ),
        description="URL da pasta destino no Figma/FigJam para geração de artefatos",
    )
    figma_folder_id: str = Field(
        default_factory=lambda: os.getenv("FIGMA_FOLDER_ID", "648533591"),
        description="ID da pasta/projeto no Figma",
    )
    figma_team_id: str = Field(
        default_factory=lambda: os.getenv("FIGMA_TEAM_ID", "1669801444374741311"),
        description="ID do time no Figma",
    )

    # Timeouts
    mcp_timeout_seconds: int = Field(default=30, description="Timeout para requisições MCP")

    @property
    def figma_mcp_args(self) -> List[str]:
        """Retorna os argumentos do comando MCP como lista."""
        if not self.figma_mcp_args_raw:
            return ["-y", "figma-developer-mcp", "--stdio"]
        return [arg.strip() for arg in self.figma_mcp_args_raw.split(",") if arg.strip()]

    def is_gemini_configured(self) -> bool:
        """Verifica se a API Key do Gemini está presente."""
        return bool(self.google_api_key and not self.google_api_key.startswith("SUA_CHAVE"))

    def is_figma_configured(self) -> bool:
        """Verifica se a chave do Figma está presente."""
        return bool(self.figma_api_key and len(self.figma_api_key) > 10)


def get_settings() -> AppSettings:
    """Retorna instância das configurações atualizadas."""
    return AppSettings()
