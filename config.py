"""Configuração centralizada do Gerador de Missões Unooria (Google ADK).

Carrega e valida variáveis de ambiente para os modelos Gemini, o MCP do Stitch,
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


def _detect_stitch_mode() -> str:
    """`auto` (padrão): liga o modo remoto quando há chave, senão desliga."""
    modo = os.getenv("STITCH_MCP_MODE", "auto").strip().lower()
    if modo != "auto":
        return modo
    return "remote" if os.getenv("STITCH_API_KEY") or os.getenv("STITCH_ACCESS_TOKEN") else "off"




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
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        description="Modelo padrão para os agentes",
    )
    gemini_model_prd: str = Field(
        default_factory=lambda: os.getenv("GEMINI_MODEL_PRD", "") or os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
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
    # Os três modos estritos NÃO interrompem mais a esteira: a execução vai sempre até o fim, para
    # que o diagnóstico final tenha todos os insumos. O que eles controlam é a severidade — com
    # estrito, o gate reprovado marca a herança como degradada, tudo que deriva dele sai
    # `[PROVISÓRIO]` e o veredito final é 🔴; sem estrito, o mesmo achado vira ressalva 🟡.
    esteira_estrita: bool = Field(
        default_factory=lambda: _env_bool("ESTEIRA_ESTRITA", "true"),
        description="Se true, QA de design 🔴, banca de dev 🔴 e os gates de rastro (manifesto, telemetria, lacunas) marcam a herança como degradada e o PRD sai 🔴; lacuna de plataforma só deixa o PRD 🟡",
    )
    bncc_check_estrito: bool = Field(
        default_factory=lambda: _env_bool("BNCC_CHECK_ESTRITO", "true"),
        description="Se true, spec com habilidade BNCC inexistente, de outro ano ou sem letramento digital marca a herança como degradada em design e dev",
    )
    produto_modo_estrito: bool = Field(
        default_factory=lambda: _env_bool("PRODUTO_MODO_ESTRITO", "true"),
        description="Se verdadeiro, missão reprovada nos gates de produto marca a herança como degradada para design e dev",
    )
    gate_estrutural_max_rodadas: int = Field(
        default_factory=lambda: int(os.getenv("GATE_ESTRUTURAL_MAX_RODADAS", "3")),
        description="Rodadas máximas do loop gate estrutural ↔ revisor do one-pager",
    )
    spec_max_rodadas: int = Field(
        default_factory=lambda: int(os.getenv("SPEC_MAX_RODADAS", "2")),
        description="Rodadas máximas do loop spec ↔ conformidade BNCC e ficha do manifesto. 1 = sem correção automática",
    )
    handoff_max_rodadas: int = Field(
        default_factory=lambda: int(os.getenv("HANDOFF_MAX_RODADAS", "2")),
        description="Rodadas máximas do loop handoff de dev ↔ contrato de telemetria. 1 = sem correção automática",
    )
    banca_max_rodadas: int = Field(
        default_factory=lambda: int(os.getenv("BANCA_MAX_RODADAS", "2")),
        description="Rodadas máximas do loop banca de dev ↔ retrabalho do dono do achado (inclusive donos da etapa de design). 1 = sem correção automática",
    )
    prd_max_rodadas: int = Field(
        default_factory=lambda: int(os.getenv("PRD_MAX_RODADAS", "2")),
        description="Rodadas máximas do loop redator do PRD ↔ gate de consistência do PRD. 1 = sem correção automática",
    )
    orcamento_reexecucoes: int = Field(
        default_factory=lambda: int(os.getenv("ORCAMENTO_REEXECUCOES", "8")),
        description="Teto de agentes reexecutados por retrabalho na execução inteira, somando todos os loops. Estourado, a esteira para de tentar, marca pendência humana e segue até o fim",
    )
    avaliacoes_max_rodadas: int = Field(
        default_factory=lambda: int(os.getenv("AVALIACOES_MAX_RODADAS", "1")),
        description="Rodadas do loop avaliações ↔ revisor do one-pager movido pelo parecer de adequação. 1 = sem correção automática (padrão, porque uma rodada extra reexecuta os três avaliadores)",
    )
    qa_design_max_rodadas: int = Field(
        default_factory=lambda: int(os.getenv("QA_DESIGN_MAX_RODADAS", "2")),
        description="Rodadas máximas do loop QA de entregáveis ↔ retrabalho dos agentes com ticket. 1 = uma passada só, sem retrabalho",
    )
    output_dir: str = Field(
        default_factory=lambda: os.getenv("OUTPUT_DIR", "output"),
        description="Pasta onde os artefatos de cada execução são gravados",
    )

    # ------------------------------------------------------------------- MCP
    mcp_timeout_seconds: int = Field(default_factory=lambda: int(os.getenv("MCP_TIMEOUT_SECONDS", "60")))
    mcp_read_timeout_seconds: int = Field(default_factory=lambda: int(os.getenv("MCP_READ_TIMEOUT_SECONDS", "600")))

    # ----------------------------------------------------------- Google Stitch
    # Gera as telas do D5 e serve de conferência ao D7. O endpoint
    # MCP é oficial (`stitch.googleapis.com/mcp`) e autentica por chave de API.
    stitch_mcp_mode: str = Field(
        default_factory=lambda: _detect_stitch_mode(),
        description="off | remote (stitch.googleapis.com/mcp, X-Goog-Api-Key) | proxy (npx @_davideast/stitch-mcp, conserta os schemas)",
    )
    stitch_api_key: str = Field(
        default_factory=lambda: os.getenv("STITCH_API_KEY", ""),
        description="Chave de API do Stitch (Google Labs). Não expira e dispensa projeto no Google Cloud",
    )
    stitch_access_token: str = Field(default_factory=lambda: os.getenv("STITCH_ACCESS_TOKEN", ""))
    stitch_quota_project_id: str = Field(default_factory=lambda: os.getenv("STITCH_QUOTA_PROJECT_ID", ""))
    stitch_mcp_remote_url: str = Field(
        default_factory=lambda: os.getenv("STITCH_MCP_REMOTE_URL", "https://stitch.googleapis.com/mcp"),
    )
    stitch_mcp_command: str = Field(default_factory=lambda: os.getenv("STITCH_MCP_COMMAND", "npx"))
    stitch_mcp_args_raw: str = Field(
        default_factory=lambda: os.getenv("STITCH_MCP_ARGS", "-y,@_davideast/stitch-mcp,proxy"),
    )
    stitch_project_url_base: str = Field(
        default_factory=lambda: os.getenv("STITCH_PROJECT_URL_BASE", "https://stitch.withgoogle.com/projects"),
        description="Base da URL pública de um projeto, usada nos relatórios e no PRD",
    )

    # Google Drive (relatório de lacunas do D0 em Google Docs — sem toolset ainda; o prompt tem fallback)
    gdrive_folder_url: str = Field(
        default_factory=lambda: os.getenv("GDRIVE_FOLDER_URL", ""),
        description="URL da pasta do Google Drive onde o D0 gravaria o relatório de lacunas como Google Docs",
    )

    # ----------------------------------------------------------- Derivados
    @property
    def pipeline_stages(self) -> List[str]:
        stages = [s.strip().lower() for s in self.pipeline_stages_raw.split(",") if s.strip()]
        return [s for s in stages if s in ("produto", "design", "dev")] or ["produto", "design", "dev"]

    @property
    def stitch_mcp_args(self) -> List[str]:
        if not self.stitch_mcp_args_raw:
            return ["-y", "@_davideast/stitch-mcp", "proxy"]
        return [a.strip() for a in self.stitch_mcp_args_raw.split(",") if a.strip()]

    @property
    def is_stitch_enabled(self) -> bool:
        return self.stitch_mcp_mode in ("remote", "proxy")

    @property
    def stitch_status_label(self) -> str:
        if self.stitch_mcp_mode == "off":
            return "⚪ Desligado (defina STITCH_API_KEY)"
        if self.stitch_mcp_mode == "remote":
            return "🟢 Remoto (chave de API)" if self.stitch_api_key else "🔴 Remoto sem STITCH_API_KEY"
        if self.stitch_mcp_mode == "proxy":
            return "🟢 Proxy (npx @_davideast/stitch-mcp)"
        return f"🔴 Modo desconhecido ({self.stitch_mcp_mode})"


    @property
    def output_path(self) -> Path:
        path = Path(self.output_dir)
        return path if path.is_absolute() else PROJECT_ROOT / path

    def is_gemini_configured(self) -> bool:
        return bool(self.google_api_key and not self.google_api_key.startswith("SUA_CHAVE"))




def get_settings() -> AppSettings:
    """Retorna uma instância atualizada das configurações (relê o ambiente)."""
    return AppSettings()
