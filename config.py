"""Configuração centralizada do Gerador de Missões Unooria (Google ADK).

Carrega e valida variáveis de ambiente para os modelos Gemini, o MCP do Figma,
a política dos gates e a persistência dos artefatos gerados.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv(override=False)

PROJECT_ROOT = Path(__file__).resolve().parent


def _env_bool(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in ("true", "1", "yes", "sim")


class AppSettings(BaseSettings):
    """Configurações da aplicação e dos agentes ADK."""

    app_name: str = "GeradorMissoesUnooria"
    app_version: str = "2.0.0"

    # ------------------------------------------------------------------ Gemini
    google_api_key: str = Field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", ""),
        description="Chave de API do Google Gemini",
    )
    gemini_model: str = Field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.7-flash"),
        description="Modelo padrão para os agentes",
    )
    gemini_model_prd: str = Field(
        default_factory=lambda: os.getenv("GEMINI_MODEL_PRD", "") or os.getenv("GEMINI_MODEL", "gemini-3.7-flash"),
        description="Modelo usado pelo redator do PRD (pode ser mais forte que o padrão)",
    )
    thinking_budget: int = Field(
        default_factory=lambda: int(os.getenv("THINKING_BUDGET", "2048")),
        description="Orçamento de raciocínio (0 = off, -1 = dinâmico, >0 = tokens)",
    )
    include_thoughts: bool = Field(
        default_factory=lambda: _env_bool("INCLUDE_THOUGHTS", "true"),
        description="Expor o fluxo de pensamento dos agentes",
    )

    # ------------------------------------------------------------- Pipeline
    pipeline_stages_raw: str = Field(
        default_factory=lambda: os.getenv("PIPELINE_STAGES", "produto,design,dev"),
        description="Etapas ativas do pipeline, separadas por vírgula (produto, design, dev)",
    )
    produto_modo_estrito: bool = Field(
        default_factory=lambda: _env_bool("PRODUTO_MODO_ESTRITO", "true"),
        description="Se verdadeiro, missão bloqueada nos gates de produto interrompe design e dev",
    )
    gate_estrutural_max_rodadas: int = Field(
        default_factory=lambda: int(os.getenv("GATE_ESTRUTURAL_MAX_RODADAS", "3")),
        description="Rodadas máximas do loop gate estrutural ↔ revisor do one-pager",
    )
    output_dir: str = Field(
        default_factory=lambda: os.getenv("OUTPUT_DIR", "output"),
        description="Pasta onde os artefatos de cada execução são gravados",
    )

    # ------------------------------------------------------------ Figma MCP
    figma_mcp_mode: str = Field(
        default_factory=lambda: os.getenv("FIGMA_MCP_MODE", "off").strip().lower(),
        description="off | remote (mcp.figma.com, OAuth) | desktop (app Figma local) | stdio (figma-developer-mcp, só leitura)",
    )
    figma_mcp_remote_url: str = Field(
        default_factory=lambda: os.getenv("FIGMA_MCP_REMOTE_URL", "https://mcp.figma.com/mcp"),
    )
    figma_mcp_desktop_url: str = Field(
        default_factory=lambda: os.getenv("FIGMA_MCP_DESKTOP_URL", "http://127.0.0.1:3845/mcp"),
    )
    figma_mcp_bearer_token: str = Field(
        default_factory=lambda: os.getenv("FIGMA_MCP_BEARER_TOKEN", ""),
        description="Bearer estático para o MCP remoto (alternativa ao arquivo de tokens OAuth)",
    )
    figma_mcp_oauth_tokens_file: str = Field(
        default_factory=lambda: os.getenv("FIGMA_MCP_OAUTH_TOKENS_FILE", ".figma_mcp_tokens.json"),
        description="Arquivo gerado por scripts/figma_oauth.py com os tokens OAuth do MCP remoto",
    )
    figma_api_key: str = Field(
        default_factory=lambda: os.getenv("FIGMA_API_KEY", "") or os.getenv("FIGMA_PERSONAL_ACCESS_TOKEN", ""),
        description="Personal Access Token do Figma (usado só pelo modo stdio)",
    )
    figma_mcp_command: str = Field(default_factory=lambda: os.getenv("FIGMA_MCP_COMMAND", "npx"))
    figma_mcp_args_raw: str = Field(
        default_factory=lambda: os.getenv("FIGMA_MCP_ARGS", "-y,figma-developer-mcp,--stdio"),
    )
    mcp_timeout_seconds: int = Field(default_factory=lambda: int(os.getenv("MCP_TIMEOUT_SECONDS", "60")))
    mcp_read_timeout_seconds: int = Field(default_factory=lambda: int(os.getenv("MCP_READ_TIMEOUT_SECONDS", "600")))

    # Contexto Figma da Unooria
    figma_default_folder_url: str = Field(
        default_factory=lambda: os.getenv("FIGMA_DEFAULT_FOLDER_URL", ""),
        description="URL da pasta/projeto do Figma onde os arquivos das missões são criados",
    )
    figma_ds_file_key: str = Field(
        default_factory=lambda: os.getenv("FIGMA_DS_FILE_KEY", "mPw4Hhx9ptkgcHtySaSilO"),
        description="fileKey do Design System Unooria (tokens e componentes)",
    )
    figma_ds_v02_file_key: str = Field(
        default_factory=lambda: os.getenv("FIGMA_DS_V02_FILE_KEY", "i0HRQSBtQQ9ZXDYiJPRnGv"),
        description="fileKey do Unooria_DS_v0.2",
    )

    # ----------------------------------------------------------- Derivados
    @property
    def pipeline_stages(self) -> List[str]:
        stages = [s.strip().lower() for s in self.pipeline_stages_raw.split(",") if s.strip()]
        return [s for s in stages if s in ("produto", "design", "dev")] or ["produto", "design", "dev"]

    @property
    def figma_mcp_args(self) -> List[str]:
        if not self.figma_mcp_args_raw:
            return ["-y", "figma-developer-mcp", "--stdio"]
        return [a.strip() for a in self.figma_mcp_args_raw.split(",") if a.strip()]

    @property
    def output_path(self) -> Path:
        path = Path(self.output_dir)
        return path if path.is_absolute() else PROJECT_ROOT / path

    def is_gemini_configured(self) -> bool:
        return bool(self.google_api_key and not self.google_api_key.startswith("SUA_CHAVE"))

    def is_figma_enabled(self) -> bool:
        return self.figma_mcp_mode in ("remote", "desktop", "stdio")

    def figma_status_label(self) -> str:
        mode = self.figma_mcp_mode
        if mode == "off":
            return "⚪ Desligado (artefatos de design em Markdown/Mermaid)"
        if mode == "remote":
            tokens = (PROJECT_ROOT / self.figma_mcp_oauth_tokens_file).exists() or bool(self.figma_mcp_bearer_token)
            return "🟢 Remoto (OAuth)" if tokens else "🟡 Remoto sem token — rode `python scripts/figma_oauth.py`"
        if mode == "desktop":
            return f"🟢 Desktop ({self.figma_mcp_desktop_url})"
        if mode == "stdio":
            return "🟡 stdio (figma-developer-mcp, só leitura)" if self.figma_api_key else "🔴 stdio sem FIGMA_API_KEY"
        return f"🔴 Modo desconhecido: {mode}"


def get_settings() -> AppSettings:
    """Retorna uma instância atualizada das configurações (relê o ambiente)."""
    return AppSettings()
