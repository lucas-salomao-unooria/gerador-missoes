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


def _detect_miro_mode() -> str:
    """`auto` (padrão) → `remote`.

    Diferente do Stitch, não há credencial no ambiente para consultar: o MCP do Miro
    emite o próprio client por registro dinâmico e a autorização acontece no navegador.
    Quem sabe se existe conexão é o arquivo de tokens, e esta função é deliberadamente
    pura — `tools.miro_oauth.status_label()` é que lê o disco. Sem conexão, a publicação
    registra "MIRO: indisponível" e a esteira segue.
    """
    modo = os.getenv("MIRO_MODE", "auto").strip().lower()
    return "remote" if modo == "auto" else modo




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
        default_factory=lambda: int(os.getenv("THINKING_BUDGET", "8192")),
        description="Orçamento de raciocínio (0 = off, -1 = dinâmico, >0 = tokens)",
    )
    include_thoughts: bool = Field(
        default_factory=lambda: _env_bool("INCLUDE_THOUGHTS", "true"),
        description="Expor o fluxo de pensamento dos agentes",
    )
    temperatura_juiz: float = Field(
        default_factory=lambda: float(os.getenv("TEMPERATURA_JUIZ", "0.1")),
        description="Amostragem dos agentes que emitem veredito. Baixa, não zero: com thinking "
                    "ligado a temperatura afeta sobretudo a verbalização, e 0 não compra "
                    "determinismo — quem compra é o seed.",
    )
    seed_juiz: int = Field(
        default_factory=lambda: int(os.getenv("SEED_JUIZ", "20260923")),
        description="Seed fixo dos juízes: dois gates sobre o mesmo artefato devem dar o mesmo "
                    "veredito, senão não há como medir se uma mudança de critério funcionou.",
    )
    # OpenAPI da plataforma servido pela api, para o gate de rotas (`tools/rotas_plataforma.py`).
    # Vazio: usa o `openapi-rotas.json` da base da plataforma publicada no bucket
    # (`prompts/base_plataforma.py`). Em 23/09/2026 o `/docs` da api de dev não era público.
    plataforma_openapi_url: str = Field(default_factory=lambda: os.getenv("PLATAFORMA_OPENAPI_URL", ""))
    plataforma_openapi_usuario: str = Field(default_factory=lambda: os.getenv("PLATAFORMA_OPENAPI_USUARIO", ""))
    plataforma_openapi_senha: str = Field(default_factory=lambda: os.getenv("PLATAFORMA_OPENAPI_SENHA", ""))
    kpis_check_estrito: bool = Field(
        default_factory=lambda: _env_bool("KPIS_CHECK_ESTRITO", "true"),
        description="Coerência KPI ↔ evento ↔ tela trava a esteira. Nasceu desligado porque os 14 "
                    "PRDs medidos reprovavam todos — eram anteriores ao formato. Ligado em "
                    "23/09/2026, junto com o gate do sub-bloco 9f: a partir daí as perguntas são "
                    "decididas na spec e o PRD só as transporta, então reprovar aqui significa que "
                    "alguma se perdeu no caminho — que é exatamente o que o gate existe para dizer. "
                    "Desligar só para depurar uma execução, nunca como regime.",
    )
    tentativas_modelo: int = Field(
        default_factory=lambda: int(os.getenv("TENTATIVAS_MODELO", "4")),
        description="Tentativas por chamada ao modelo, com backoff exponencial e jitter. A esteira "
                    "faz 33 a 55 chamadas e a banca dispara 5 em paralelo: sem isto, um 429 no "
                    "meio derruba uma execução de 20 minutos.",
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
    # Os cortes da rubrica de profundidade (P1–P3 em 3) são convenção até serem calibrados contra as
    # revisões do time pedagógico. Desligar não mexe nas notas nem nas rodadas: o núcleo continua
    # sendo devolvido ao autor, e só o veredito final deixa de ser 🔴 — o de acordo volta a ser possível.
    profundidade_estrita: bool = Field(
        default_factory=lambda: _env_bool("PROFUNDIDADE_ESTRITA", "true"),
        description="Se true, profundidade pedagógica reprovada na última rodada do núcleo fica 🔴 e recusa o de acordo de produto; se false, fica 🟡 com a ressalva registrada",
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
        default_factory=lambda: int(os.getenv("AVALIACOES_MAX_RODADAS", "2")),
        description="Rodadas do loop avaliações ↔ revisor do one-pager movido pelo parecer de adequação. 2 (padrão) = o revisor aplica o ajuste exigido e as avaliações refazem; 1 = sem correção automática",
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
    # O sufixo `_raw` não é enfeite: um campo chamado `stitch_mcp_mode` seria populado
    # direto de STITCH_MCP_MODE pelo pydantic-settings, e o `default_factory` — que é
    # quem resolve o `auto` — nunca rodaria. O modo sairia a string "auto", que não é
    # nem `remote` nem `proxy`, e `is_stitch_enabled` daria False com a chave no lugar.
    stitch_mcp_mode_raw: str = Field(
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
    # A geração das telas saiu do modelo em 07/10/2026 (`tools/stitch_geracao.py`): cada (tela, estado) é uma
    # chamada que leva minutos, e 25 a 46 delas em série passariam de uma hora.
    stitch_paralelo: int = Field(
        default_factory=lambda: int(os.getenv("STITCH_PARALELO", "4")),
        description="Telas geradas ao mesmo tempo no Stitch. Mais rápido com mais; o limite é a cota do Stitch",
    )
    stitch_prazo_geracao_s: int = Field(
        default_factory=lambda: int(os.getenv("STITCH_PRAZO_GERACAO_S", "300")),
        description="Segundos de espera por tela gerada antes de conciliar pelo projeto (a ferramenta pede para não repetir em timeout)",
    )

    # -------------------------------------------------------------------- Miro
    # Espelha no Miro a jornada (D2) e o fluxo de telas (D3). O Mermaid continua sendo a
    # fonte; o board é publicado depois, por código, e devolve um link para o PRD.
    # `_raw` pelo mesmo motivo do Stitch: sem isso o pydantic-settings entrega "auto".
    miro_mode_raw: str = Field(
        default_factory=lambda: _detect_miro_mode(),
        description="off | remote (mcp.miro.com, OAuth com registro dinâmico conduzido pelo Streamlit)",
    )
    miro_mcp_url: str = Field(
        default_factory=lambda: os.getenv("MIRO_MCP_URL", "https://mcp.miro.com/"),
        description="Endpoint do MCP, que também é o authorization server e o `resource` do token",
    )
    miro_redirect_uri: str = Field(
        default_factory=lambda: os.getenv("MIRO_REDIRECT_URI", "http://localhost:8501"),
        description="Para onde o Miro devolve o código; precisa bater com o endereço do Streamlit",
    )
    miro_oauth_tokens_file: str = Field(
        default_factory=lambda: os.getenv("MIRO_OAUTH_TOKENS_FILE", ".miro_mcp_tokens.json"),
        description="Arquivo com o client registrado e os tokens em vigor (fora do versionamento)",
    )
    miro_team_id: str = Field(
        default_factory=lambda: os.getenv("MIRO_TEAM_ID", ""),
        description="Time onde os boards nascem; vazio = o time escolhido ao conectar",
    )
    miro_max_itens: int = Field(
        default_factory=lambda: int(os.getenv("MIRO_MAX_ITENS", "80")),
        description="Teto de itens por board, para não bater no rate limit do Miro",
    )
    # O MCP não usa estas duas: são do app do dev portal e autenticam a REST API v2,
    # o caminho alternativo caso a escrita via MCP não sirva.
    miro_client_id: str = Field(default_factory=lambda: os.getenv("MIRO_CLIENT_ID", ""))
    miro_client_secret: str = Field(default_factory=lambda: os.getenv("MIRO_CLIENT_SECRET", ""))

    # ------------------------------------------ Imagem da jornada e do fluxo no pedagógico
    # O `.docx` não roda mermaid.js e a imagem do Cloud Run não tem navegador: a figura dos
    # diagramas vem de um renderizador de fora. **Desligado por padrão** porque `url` envia o
    # texto do fluxo da missão a um serviço de terceiros, e `miro` lê o board com o token da
    # esteira — quem liga é o dono da decisão. Desligado, o documento aponta `design/09-diagramas.html`.
    # `_raw` pelo mesmo motivo do Stitch: o pydantic-settings entregaria o valor sem normalizar.
    diagrama_imagem_fonte_raw: str = Field(
        default_factory=lambda: os.getenv("DIAGRAMA_IMAGEM_FONTE", "off"),
        description="off (padrão) | url (MERMAID_RENDER_URL, estilo mermaid.ink ou Kroki) | miro (lê o board da sessão)",
    )
    mermaid_render_url: str = Field(
        default_factory=lambda: os.getenv("MERMAID_RENDER_URL", ""),
        description="Com DIAGRAMA_IMAGEM_FONTE=url: https://mermaid.ink/img (GET), https://kroki.io/mermaid/png "
                    "(POST) ou um modelo com {codigo} (GET, Mermaid em base64url). Vazio = nada sai daqui",
    )

    # ------------------------------------------------------------------ Login
    # Quatro contas fixas (produto, design, dev, admin), sem provedor de identidade. Os dois
    # valores saem de `scripts/gerar_credenciais.py` e vivem no Secret Manager; sem qualquer um
    # deles o app recusa subir (`tools/auth.py`, `configuracao_de_login`) — não existe modo aberto
    # por esquecimento, senão um deploy sem o segredo publicaria o app sem login.
    auth_credenciais: str = Field(
        default_factory=lambda: os.getenv("AUTH_CREDENCIAIS", ""),
        description="JSON {usuario: {hash, papel}} com os hashes scrypt das senhas",
    )
    auth_segredo_jwt: str = Field(
        default_factory=lambda: os.getenv("AUTH_SEGREDO_JWT", ""),
        description="Chave HS256 que assina o token de sessão. Girar derruba todas as sessões",
    )
    auth_horas_sessao: float = Field(
        default_factory=lambda: float(os.getenv("AUTH_HORAS_SESSAO", "4")),
        description="Validade absoluta da sessão, contada do login",
    )
    parecer_humano: bool = Field(
        default_factory=lambda: _env_bool("PARECER_HUMANO", "true"),
        description="Se true, a esteira para ao fim de cada etapa e espera o parecer do dono "
                    "(pipeline/passagem.py). Padrão da sessão; o admin muda na barra lateral",
    )


    # ----------------------------------------------------------- Derivados
    @property
    def pipeline_stages(self) -> List[str]:
        stages = [s.strip().lower() for s in self.pipeline_stages_raw.split(",") if s.strip()]
        return [s for s in stages if s in ("produto", "design", "dev")] or ["produto", "design", "dev"]

    @property
    def stitch_mcp_mode(self) -> str:
        return self.stitch_mcp_mode_raw

    @property
    def miro_mode(self) -> str:
        return self.miro_mode_raw

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
    def is_miro_enabled(self) -> bool:
        return self.miro_mode == "remote"

    @property
    def miro_status_label(self) -> str:
        """Rótulo só do modo. O estado da conexão exige disco e vive em `tools.miro_oauth`."""
        if self.miro_mode == "off":
            return "⚪ Desligado (MIRO_MODE=off)"
        if self.miro_mode == "remote":
            return "🟢 Remoto (mcp.miro.com)"
        return f"🔴 Modo desconhecido ({self.miro_mode})"


    @property
    def diagrama_imagem_fonte(self) -> str:
        """`off`, `url` ou `miro`; qualquer outra coisa — e `url` sem endereço — é `off`."""
        fonte = (self.diagrama_imagem_fonte_raw or "off").strip().lower()
        if fonte == "url" and not self.mermaid_render_url.strip():
            return "off"
        return fonte if fonte in ("off", "url", "miro") else "off"

    @property
    def output_path(self) -> Path:
        path = Path(self.output_dir)
        return path if path.is_absolute() else PROJECT_ROOT / path

    def is_gemini_configured(self) -> bool:
        return bool(self.google_api_key and not self.google_api_key.startswith("SUA_CHAVE"))




def get_settings() -> AppSettings:
    """Retorna uma instância atualizada das configurações (relê o ambiente).

    Deliberadamente sem cache: `OUTPUT_DIR` e as chaves de MCP são trocadas em tempo de
    execução (testes e o fluxo OAuth do Miro dependem da releitura). O custo é ~0,4 ms por
    chamada, irrelevante perto do I/O que a esteira faz.
    """
    return AppSettings()
