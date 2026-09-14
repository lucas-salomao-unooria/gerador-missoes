"""Área de DESIGN — da spec aprovada aos wireframes lo-fi auditados.

Ordem (SequentialAgent), com o MCP do Figma nos agentes marcados 🎨:
  d1  BriefOficioAgent        → brief_oficio
  d2  JornadaFigJamAgent   🎨 → jornada_telas   (mapa de jornada + inventário + direção)
  d3  FluxoFigJamAgent     🎨 → fluxo_arestas   (grafo de telas + 5 testes)
  d4  CopyPtBrAgent           → copy_strings    (passada 1)
  d4b CaaAgent                → camada_caa      (camada CAA; ele mesmo decide se roda)
  d5  WireframesFigmaAgent 🎨 → wireframes_cobertura
  d6  CopyRevisaoAgent        → copy_strings_revisada (passada 2)
  d7  QaEntregaveisAgent   🎨 → qa_entregaveis_report (gate de design)
  d7c QaEntregaveisCheck      → design_status
"""

from __future__ import annotations

from typing import Optional

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent

from agents.base import create_llm_agent
from agents.callbacks import skip_if_blocked
from agents.checkers import EnvelopeGateAgent
from config import get_settings
from prompts import load_prompt
from tools.figma_mcp import (
    FIGMA_TOOLS_FLUXO,
    FIGMA_TOOLS_JORNADA,
    FIGMA_TOOLS_QA,
    FIGMA_TOOLS_WIREFRAMES,
    figma_tools_or_empty,
)


def _figma_vars() -> dict:
    s = get_settings()
    return {
        "figma_mcp_mode": s.figma_mcp_mode,
        "figma_folder_url": s.figma_default_folder_url or "(não configurada — crie o arquivo no espaço padrão do usuário)",
        "figma_ds_file_key": s.figma_ds_file_key,
        "figma_ds_v02_file_key": s.figma_ds_v02_file_key,
    }


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
        description="Gate final de design: fidelidade à spec, diff de strings, currículo, faixa etária, fluxo, professor e briefing.",
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
        description="Área de Design: briefing de ofício → jornada e fluxo (FigJam) → copy → camada CAA → wireframes (Figma) → QA de entregáveis.",
        before_agent_callback=skip_if_blocked,
        sub_agents=[
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
                description="Lê o veredito do QA de entregáveis; não bloqueia o dev — o PRD registra as pendências.",
                rotulo="QA de entregáveis (design)",
                report_key="qa_entregaveis_report",
                status_key="design_status",
                block_pipeline_on_fail=False,
                treat_indefinido_as_blocked=False,
            ),
        ],
    )


DESIGN_METADATA = [
    {"id": "BriefOficioAgent", "name": "D1 · Briefing de ofício", "icon": "🎯", "output_key": "brief_oficio", "prompt_file": "design/d1_brief_oficio.md", "description": "Aposta, forma do arco, pico, beat memorável, mapa de beats, não-negociáveis."},
    {"id": "JornadaFigJamAgent", "name": "D2 · Jornada (FigJam) 🎨", "icon": "🗺️", "output_key": "jornada_telas", "prompt_file": "design/d2_jornada_figjam.md", "description": "Raias × 6 etapas, cenários de dispositivo, inventário de telas e direção por tela."},
    {"id": "FluxoFigJamAgent", "name": "D3 · Fluxo de telas (FigJam) 🎨", "icon": "🕸️", "output_key": "fluxo_arestas", "prompt_file": "design/d3_fluxo_figjam.md", "description": "Grafo de telas com condições, gates e os 5 testes de fluxo."},
    {"id": "CopyPtBrAgent", "name": "D4 · Copy PT-BR (passada 1)", "icon": "✍️", "output_key": "copy_strings", "prompt_file": "design/d4_copy_ptbr.md", "description": "Sheet de strings por tela, calibrado à faixa etária."},
    {"id": "CaaAgent", "name": "D4b · Camada CAA", "icon": "🔣", "output_key": "camada_caa", "prompt_file": "design/d4b_caa.md", "description": "Símbolos, modos de resposta alternativos e pranchas; só roda quando a faixa ou a spec pedem."},
    {"id": "WireframesFigmaAgent", "name": "D5 · Wireframes lo-fi (Figma) 🎨", "icon": "📐", "output_key": "wireframes_cobertura", "prompt_file": "design/d5_wireframes_figma.md", "description": "Telas em escala de cinza sobre a seção do DS do ambiente."},
    {"id": "CopyRevisaoAgent", "name": "D6 · Copy PT-BR (passada 2)", "icon": "🔍", "output_key": "copy_strings_revisada", "prompt_file": "design/d6_copy_revisao.md", "description": "Revisão em contexto de tela."},
    {"id": "QaEntregaveisAgent", "name": "D7 · QA de entregáveis 🎨", "icon": "🧪", "output_key": "qa_entregaveis_report", "prompt_file": "design/d7_qa_entregaveis.md", "description": "Fidelidade à spec, diff de strings, currículo, faixa, fluxo, professor, briefing."},
    {"id": "QaEntregaveisCheck", "name": "D7c · Veredito de design (determinístico)", "icon": "🔀", "output_key": "design_status", "prompt_file": None, "description": "Lê o envelope do QA de entregáveis."},
]
