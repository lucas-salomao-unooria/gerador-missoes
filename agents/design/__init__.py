"""Área de DESIGN — da spec aprovada aos wireframes lo-fi auditados.

Ordem (SequentialAgent), com o MCP do Figma nos agentes marcados 🎨:
  d0  FechaLacunasAgent       → fechamento_lacunas   (varredura, decisões [D0-n], re-specs [RS-n])
  d0c FechaLacunasSplit       → spec_missao (consolidada, bloco 13) · spec_missao_gate0 (cópia
                                 da original) · relatorio_lacunas · lacunas_status
  d9  AmbienteSimuladoAgent 🎨 → ambiente_simulado   (condicional: decide o ambiente quando a
                                 spec cala; dormente emite só a ficha do bloco 14)
  d9c AmbienteSimuladoSplit   → spec_missao (com bloco 14) · ambiente_status
  d1  BriefOficioAgent        → brief_oficio
  d2  JornadaFigJamAgent   🎨 → jornada_telas   (mapa de jornada + inventário + direção)
  d3  FluxoFigJamAgent     🎨 → fluxo_arestas   (grafo de telas + 5 testes)
  d4  CopyPtBrAgent           → copy_strings    (passada 1)
  d4b CaaAgent                → camada_caa      (camada CAA; ele mesmo decide se roda)
  d5  WireframesFigmaAgent 🎨 → wireframes_cobertura
  d6  CopyRevisaoAgent        → copy_strings_revisada (passada 2)
  d7  QaEntregaveisAgent   🎨 → qa_entregaveis_report (gate de design)
  d7c QaEntregaveisCheck      → design_status (🔴 impede dev e PRD quando ESTEIRA_ESTRITA)

D0 e D9 emitem dois documentos numa única resposta (a spec consolidada e o próprio
relatório). Um `LlmAgent` grava uma só chave, então cada um é seguido por um
`SecaoSplitAgent` determinístico que copia a seção da spec para `spec_missao` — é assim
que D1–D7 leem a spec consolidada sem saber que D0/D9 existiram. O status de D0 e D9 é
informativo: não há loop de re-spec com o Gate 0 na esteira, então `aguarda_gate`
aparece como 🔴 na UI e o pipeline segue com os `RS-n` carimbados como pendentes.
"""

from __future__ import annotations

from typing import Optional

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent

from agents.base import create_llm_agent
from agents.callbacks import skip_if_blocked
from agents.checkers import EnvelopeGateAgent, SecaoSplitAgent
from config import get_settings
from prompts import load_prompt
from tools.figma_mcp import (
    FIGMA_TOOLS_AMBIENTE,
    FIGMA_TOOLS_FLUXO,
    FIGMA_TOOLS_JORNADA,
    FIGMA_TOOLS_QA,
    FIGMA_TOOLS_WIREFRAMES,
    figma_tools_or_empty,
)

# Headings que D0 e D9 usam na "Saída obrigatória" dos seus prompts. Os regex são tolerantes
# ao travessão/hífen e ao texto depois do número, mas dependem do número do passo.
_H = r"^#{2,3}\s*"
D0_SPEC_INICIO = _H + r"Passo 5\b.*$"        # "## Passo 5 — Spec consolidada (...)"  (5\b não casa "5b")
D0_SPEC_FIM = _H + r"Passo 5b\b.*$"          # "## Passo 5b — Relatório de preenchimento ..."
D0_RELATORIO_FIM = _H + r"Passo 6\b.*$"      # "## Passo 6 — Devolutiva ao produto"
D9_SPEC_INICIO = _H + r"Passo 4\b.*$"        # "## Passo 4 — Spec consolidada (blocos 1–13 ... + bloco 14)"
D9_SPEC_FIM = _H + r"Bloco 14\b.*$"          # "## Bloco 14 — Ficha do ambiente"
SPEC_MINIMO_CHARS = 1500


def _figma_vars() -> dict:
    s = get_settings()
    return {
        "figma_mcp_mode": s.figma_mcp_mode,
        "figma_folder_url": s.figma_default_folder_url or "(não configurada — crie o arquivo no espaço padrão do usuário)",
        "figma_ds_file_key": s.figma_ds_file_key,
        "figma_ds_v02_file_key": s.figma_ds_v02_file_key,
    }


def _gdrive_vars() -> dict:
    s = get_settings()
    return {
        "gdrive_folder_url": s.gdrive_folder_url
        or "(não configurada — as ferramentas do Google Drive não estão disponíveis nesta esteira; registre `GDOCS: indisponível` e entregue só o Markdown)",
    }


def get_fecha_lacunas_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="FechaLacunasAgent",
        description="Fechamento de lacunas da spec antes do design: varredura célula a célula, decisões [D0-n] com base declarada, pedidos de re-spec [RS-n] e spec consolidada com bloco 13.",
        instruction=load_prompt("design/d0_fechamento_lacunas.md", **_gdrive_vars()),
        output_key="fechamento_lacunas",
        before_agent_callback=skip_if_blocked,
        **kw,
    )


def get_fecha_lacunas_split() -> SecaoSplitAgent:
    return SecaoSplitAgent(
        name="FechaLacunasSplit",
        description="Copia a spec consolidada (bloco 13) do D0 para `spec_missao`, preserva a original em `spec_missao_gate0`, separa o relatório de preenchimento em `relatorio_lacunas` e registra `lacunas_status`.",
        rotulo="Fechamento de lacunas (D0)",
        source_key="fechamento_lacunas",
        status_key="lacunas_status",
        extracoes=[
            {
                "chave": "spec_missao",
                "inicio": D0_SPEC_INICIO,
                "fim": D0_SPEC_FIM,
                "exigir": r"13",
                "minimo_chars": SPEC_MINIMO_CHARS,
                "backup": "spec_missao_gate0",
            },
            {
                "chave": "relatorio_lacunas",
                "inicio": D0_SPEC_FIM,
                "fim": D0_RELATORIO_FIM,
                "minimo_chars": 80,
            },
        ],
    )


def get_ambiente_simulado_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="AmbienteSimuladoAgent",
        description="Ambiente simulado (condicional): decide em que casca a missão acontece quando a spec cala — app clonado da lista fechada, app novo ou mini-jogo em anos iniciais — e emite a ficha do bloco 14 mesmo quando dormente.",
        instruction=load_prompt("design/d9_ambiente_simulado.md", **_figma_vars()),
        output_key="ambiente_simulado",
        tools=figma_tools_or_empty(FIGMA_TOOLS_AMBIENTE),
        before_agent_callback=skip_if_blocked,
        **kw,
    )


def get_ambiente_simulado_split() -> SecaoSplitAgent:
    return SecaoSplitAgent(
        name="AmbienteSimuladoSplit",
        description="Copia a spec consolidada com o bloco 14 do D9 para `spec_missao` e registra `ambiente_status` (dormente | existente | novo | aguarda_gate).",
        rotulo="Ambiente simulado (D9)",
        source_key="ambiente_simulado",
        status_key="ambiente_status",
        extracoes=[
            {
                "chave": "spec_missao",
                "inicio": D9_SPEC_INICIO,
                "fim": D9_SPEC_FIM,
                "exigir": r"14",
                "minimo_chars": SPEC_MINIMO_CHARS,
            },
        ],
    )


def get_brief_oficio_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="BriefOficioAgent",
        description="Briefing de ofício: aposta, forma do arco, pico, beat memorável, mapa de beats e não-negociáveis.",
        instruction=load_prompt("design/d1_brief_oficio.md"),
        output_key="brief_oficio",
        before_agent_callback=skip_if_blocked,
        **kw,
    )


def get_jornada_figjam_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="JornadaFigJamAgent",
        description="Mapa de jornada no FigJam (raias × 6 etapas), cenários de dispositivo, inventário de telas e direção por tela.",
        instruction=load_prompt("design/d2_jornada_figjam.md", **_figma_vars()),
        output_key="jornada_telas",
        tools=figma_tools_or_empty(FIGMA_TOOLS_JORNADA),
        before_agent_callback=skip_if_blocked,
        **kw,
    )


def get_fluxo_figjam_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="FluxoFigJamAgent",
        description="Grafo de fluxo de telas no FigJam: transições com condição, gates, estados de erro e os 5 testes.",
        instruction=load_prompt("design/d3_fluxo_figjam.md", **_figma_vars()),
        output_key="fluxo_arestas",
        tools=figma_tools_or_empty(FIGMA_TOOLS_FLUXO),
        before_agent_callback=skip_if_blocked,
        **kw,
    )


def get_copy_ptbr_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="CopyPtBrAgent",
        description="Copy PT-BR passada 1: sheet de strings por tela, calibrado à faixa etária.",
        instruction=load_prompt("design/d4_copy_ptbr.md"),
        output_key="copy_strings",
        before_agent_callback=skip_if_blocked,
        **kw,
    )


def get_caa_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="CaaAgent",
        description="Camada CAA: símbolos, modos de resposta alternativos e pranchas para quem não lê ou não fala. Aplica o gate de aplicabilidade e devolve `nao_aplicavel` quando a missão não justifica.",
        instruction=load_prompt("design/d4b_caa.md"),
        output_key="camada_caa",
        before_agent_callback=skip_if_blocked,
        **kw,
    )


def get_wireframes_figma_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="WireframesFigmaAgent",
        description="Wireframes lo-fi em escala de cinza no Figma, montados sobre a seção do DS do ambiente simulado.",
        instruction=load_prompt("design/d5_wireframes_figma.md", **_figma_vars()),
        output_key="wireframes_cobertura",
        tools=figma_tools_or_empty(FIGMA_TOOLS_WIREFRAMES),
        before_agent_callback=skip_if_blocked,
        **kw,
    )


def get_copy_revisao_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="CopyRevisaoAgent",
        description="Copy PT-BR passada 2: revisão de cada string dentro da tela construída.",
        instruction=load_prompt("design/d6_copy_revisao.md"),
        output_key="copy_strings_revisada",
        before_agent_callback=skip_if_blocked,
        **kw,
    )


def get_qa_entregaveis_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="QaEntregaveisAgent",
        description="Gate final de design: fidelidade à spec, diff de strings, currículo, faixa etária, fluxo, professor, briefing, ambiente simulado e CAA.",
        instruction=load_prompt("design/d7_qa_entregaveis.md", **_figma_vars()),
        output_key="qa_entregaveis_report",
        tools=figma_tools_or_empty(FIGMA_TOOLS_QA),
        before_agent_callback=skip_if_blocked,
        **kw,
    )


def build_design_stage(
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
) -> SequentialAgent:
    kw = {"thinking_budget": thinking_budget, "include_thoughts": include_thoughts}
    return SequentialAgent(
        name="DesignStage",
        description="Área de Design: fechamento de lacunas → ambiente simulado → briefing de ofício → jornada e fluxo (FigJam) → copy → camada CAA → wireframes (Figma) → QA de entregáveis.",
        before_agent_callback=skip_if_blocked,
        sub_agents=[
            get_fecha_lacunas_agent(**kw),
            get_fecha_lacunas_split(),
            get_ambiente_simulado_agent(**kw),
            get_ambiente_simulado_split(),
            get_brief_oficio_agent(**kw),
            get_jornada_figjam_agent(**kw),
            get_fluxo_figjam_agent(**kw),
            get_copy_ptbr_agent(**kw),
            get_caa_agent(**kw),
            get_wireframes_figma_agent(**kw),
            get_copy_revisao_agent(**kw),
            get_qa_entregaveis_agent(**kw),
            EnvelopeGateAgent(
                name="QaEntregaveisCheck",
                description="Lê o veredito do QA de entregáveis: 🔴 impede o dev e o PRD (modo estrito); ressalvas entram no PRD.",
                rotulo="QA de entregáveis (design)",
                report_key="qa_entregaveis_report",
                status_key="design_status",
                block_pipeline_on_fail=get_settings().esteira_estrita,
                treat_indefinido_as_blocked=False,
            ),
        ],
    )


DESIGN_METADATA = [
    {"id": "FechaLacunasAgent", "name": "D0 · Fechamento de lacunas", "icon": "🧩", "output_key": "fechamento_lacunas", "prompt_file": "design/d0_fechamento_lacunas.md", "description": "Varredura da spec célula a célula, decisões [D0-n] com base declarada, pedidos de re-spec [RS-n], spec consolidada (bloco 13) e relatório de preenchimento."},
    {"id": "FechaLacunasSplit", "name": "D0c · Relatório de lacunas + spec consolidada (determinístico)", "icon": "✂️", "output_key": "relatorio_lacunas", "prompt_file": None, "description": "Copia a spec consolidada para `spec_missao` (original preservada em `spec_missao_gate0`), separa o relatório e registra `lacunas_status`."},
    {"id": "AmbienteSimuladoAgent", "name": "D9 · Ambiente simulado 🎨", "icon": "🏝️", "output_key": "ambiente_simulado", "prompt_file": "design/d9_ambiente_simulado.md", "description": "Condicional: decide o ambiente (app clonado existente, app novo ou mini-jogo) quando a spec cala; dormente emite só a ficha do bloco 14 que D1, D2, D4, D5 e o QA consomem."},
    {"id": "AmbienteSimuladoSplit", "name": "D9c · Spec com bloco 14 (determinístico)", "icon": "✂️", "output_key": "ambiente_status", "prompt_file": None, "description": "Copia a spec com o bloco 14 para `spec_missao` e registra `ambiente_status`."},
    {"id": "BriefOficioAgent", "name": "D1 · Briefing de ofício", "icon": "🎯", "output_key": "brief_oficio", "prompt_file": "design/d1_brief_oficio.md", "description": "Aposta, forma do arco, pico, beat memorável, mapa de beats, não-negociáveis."},
    {"id": "JornadaFigJamAgent", "name": "D2 · Jornada (FigJam) 🎨", "icon": "🗺️", "output_key": "jornada_telas", "prompt_file": "design/d2_jornada_figjam.md", "description": "Raias × 6 etapas, cenários de dispositivo, inventário de telas e direção por tela."},
    {"id": "FluxoFigJamAgent", "name": "D3 · Fluxo de telas (FigJam) 🎨", "icon": "🕸️", "output_key": "fluxo_arestas", "prompt_file": "design/d3_fluxo_figjam.md", "description": "Grafo de telas com condições, gates e os 5 testes de fluxo."},
    {"id": "CopyPtBrAgent", "name": "D4 · Copy PT-BR (passada 1)", "icon": "✍️", "output_key": "copy_strings", "prompt_file": "design/d4_copy_ptbr.md", "description": "Sheet de strings por tela, calibrado à faixa etária."},
    {"id": "CaaAgent", "name": "D4b · Camada CAA", "icon": "🔣", "output_key": "camada_caa", "prompt_file": "design/d4b_caa.md", "description": "Símbolos, modos de resposta alternativos e pranchas; só roda quando a faixa ou a spec pedem."},
    {"id": "WireframesFigmaAgent", "name": "D5 · Wireframes lo-fi (Figma) 🎨", "icon": "📐", "output_key": "wireframes_cobertura", "prompt_file": "design/d5_wireframes_figma.md", "description": "Telas em escala de cinza sobre a seção do DS do ambiente."},
    {"id": "CopyRevisaoAgent", "name": "D6 · Copy PT-BR (passada 2)", "icon": "🔍", "output_key": "copy_strings_revisada", "prompt_file": "design/d6_copy_revisao.md", "description": "Revisão em contexto de tela."},
    {"id": "QaEntregaveisAgent", "name": "D7 · QA de entregáveis 🎨", "icon": "🧪", "output_key": "qa_entregaveis_report", "prompt_file": "design/d7_qa_entregaveis.md", "description": "Fidelidade à spec, diff de strings, currículo, faixa, fluxo, professor, briefing, ambiente (D8) e CAA (D8b)."},
    {"id": "QaEntregaveisCheck", "name": "D7c · Veredito de design (determinístico)", "icon": "🔀", "output_key": "design_status", "prompt_file": None, "description": "Lê o envelope do QA de entregáveis."},
]
