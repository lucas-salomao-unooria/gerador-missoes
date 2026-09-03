"""Área de DEV — do handoff ao PRD completo, validado pela banca de dev.

Ordem (SequentialAgent):
  ┌─ ParallelAgent ───────────────────────────────────────────────┐
  │ v1  HandoffDevAgent      → handoff_dev  (insumo + stories +   │
  │                             eventos + escopo V1/V2)            │
  │ v1b BriefAssetsAgent     → brief_assets                        │
  └────────────────────────────────────────────────────────────────┘
  ┌─ ParallelAgent (banca /validar-missao, 5 dimensões) ──────────┐
  │ v2a ValidacaoProdutoNarrativa   → validacao_produto_narrativa │
  │ v2b ValidacaoDesignImersao      → validacao_design_imersao    │
  │ v2c ValidacaoPedagogiaBncc      → validacao_pedagogia_bncc    │
  │ v2d ValidacaoDadosLgpd          → validacao_dados_lgpd        │
  │ v2e ValidacaoTecnicaArquitetura → validacao_tecnica_arquitetura│
  └────────────────────────────────────────────────────────────────┘
  v3  ConsolidacaoBancaAgent → validacao_dev_report (veredito 🟢/🟡/🔴)
  v3c ValidacaoDevCheck      → dev_status
  v4  PrdWriterAgent         → prd_final   ← entregável do pipeline
"""

from __future__ import annotations

from typing import Optional

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent

from agents.base import create_llm_agent
from agents.callbacks import skip_if_blocked
from agents.checkers import EnvelopeGateAgent
from config import get_settings
from prompts import load_prompt


def get_handoff_dev_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="HandoffDevAgent",
        description="Handoff para dev: modelo de insumo preenchido, user stories com 🔒, spec de eventos, escopo V1/V2 e hipóteses.",
        instruction=load_prompt("dev/v1_handoff_dev.md"),
        output_key="handoff_dev",
        before_agent_callback=skip_if_blocked,
        **kw,
    )


def get_brief_assets_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="BriefAssetsAgent",
        description="Brief de produção de conteúdo: inventário de assets, spec por tipo, critérios de reprovação e ordem de produção.",
        instruction=load_prompt("dev/v1b_brief_assets.md"),
        output_key="brief_assets",
        before_agent_callback=skip_if_blocked,
        **kw,
    )


_VALIDADORES = [
    ("ValidacaoProdutoNarrativaAgent", "validacao_produto_narrativa", "dev/v2a_validacao_produto_narrativa.md",
     "Dimensão A — PO sênior de EdTech: produto e narrativa (PROD-01…16)."),
    ("ValidacaoDesignImersaoAgent", "validacao_design_imersao", "dev/v2b_validacao_design_imersao.md",
     "Dimensão B — Design lead: design e imersão (DES-01…13)."),
    ("ValidacaoPedagogiaBnccAgent", "validacao_pedagogia_bncc", "dev/v2c_validacao_pedagogia_bncc.md",
     "Dimensão C — Avaliação educacional e BNCC (PED-01…15)."),
    ("ValidacaoDadosLgpdAgent", "validacao_dados_lgpd", "dev/v2d_validacao_dados_lgpd.md",
     "Dimensão D — Engenharia de dados + DPO: telemetria e LGPD (DAD-01…15)."),
    ("ValidacaoTecnicaArquiteturaAgent", "validacao_tecnica_arquitetura", "dev/v2e_validacao_tecnica_arquitetura.md",
     "Dimensão E — Tech lead do monorepo: técnica e arquitetura (TEC-01…13)."),
]


def get_validador_agents(**kw) -> list[LlmAgent]:
    return [
        create_llm_agent(
            name=name,
            description=desc,
            instruction=load_prompt(prompt),
            output_key=key,
            before_agent_callback=skip_if_blocked,
            **kw,
        )
        for name, key, prompt, desc in _VALIDADORES
    ]


def get_consolidacao_banca_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="ConsolidacaoBancaAgent",
        description="Consolida as 5 dimensões da banca em um relatório único com veredito determinístico 🟢/🟡/🔴.",
        instruction=load_prompt("dev/v3_consolidacao_banca.md"),
        output_key="validacao_dev_report",
        before_agent_callback=skip_if_blocked,
        **kw,
    )


def get_prd_writer_agent(**kw) -> LlmAgent:
    settings = get_settings()
    return create_llm_agent(
        name="PrdWriterAgent",
        description="Redige o PRD padrão ouro da missão, com o contexto arquitetural da plataforma, para alimentar um agente de codificação.",
        instruction=load_prompt("dev/v4_prd_writer.md"),
        output_key="prd_final",
        model=settings.gemini_model_prd,
        before_agent_callback=skip_if_blocked,
        **kw,
    )


def build_dev_stage(
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
) -> SequentialAgent:
    kw = {"thinking_budget": thinking_budget, "include_thoughts": include_thoughts}
    return SequentialAgent(
        name="DevStage",
        description="Área de Dev: handoff + brief de assets → banca de validação (5 dimensões em paralelo) → consolidação → PRD.",
        before_agent_callback=skip_if_blocked,
        sub_agents=[
            ParallelAgent(
                name="HandoffParalelo",
                description="Handoff para dev e brief de assets rodam em paralelo (mesmas pré-condições).",
                sub_agents=[get_handoff_dev_agent(**kw), get_brief_assets_agent(**kw)],
                before_agent_callback=skip_if_blocked,
            ),
            ParallelAgent(
                name="BancaValidacaoDev",
                description="Banca /validar-missao: cinco dimensões avaliadas em paralelo.",
                sub_agents=get_validador_agents(**kw),
                before_agent_callback=skip_if_blocked,
            ),
            get_consolidacao_banca_agent(**kw),
            EnvelopeGateAgent(
                name="ValidacaoDevCheck",
                description="Lê o veredito da banca de dev; não bloqueia o PRD — o status entra no frontmatter.",
                rotulo="Banca de dev",
                report_key="validacao_dev_report",
                status_key="dev_status",
                block_pipeline_on_fail=False,
                treat_indefinido_as_blocked=False,
            ),
            get_prd_writer_agent(**kw),
        ],
    )


DEV_METADATA = [
    {"id": "HandoffDevAgent", "name": "V1 · Handoff para dev", "icon": "🤝", "output_key": "handoff_dev", "prompt_file": "dev/v1_handoff_dev.md", "description": "Modelo de insumo preenchido, stories com 🔒, eventos, escopo V1/V2, hipóteses (paralelo com V1b)."},
    {"id": "BriefAssetsAgent", "name": "V1b · Brief de assets", "icon": "🎬", "output_key": "brief_assets", "prompt_file": "dev/v1b_brief_assets.md", "description": "Inventário de assets, spec por tipo, critérios de reprovação, ordem de produção."},
    {"id": "ValidacaoProdutoNarrativaAgent", "name": "V2a · Banca: Produto & Narrativa", "icon": "🅰️", "output_key": "validacao_produto_narrativa", "prompt_file": "dev/v2a_validacao_produto_narrativa.md", "description": "PROD-01…16."},
    {"id": "ValidacaoDesignImersaoAgent", "name": "V2b · Banca: Design & Imersão", "icon": "🅱️", "output_key": "validacao_design_imersao", "prompt_file": "dev/v2b_validacao_design_imersao.md", "description": "DES-01…13."},
    {"id": "ValidacaoPedagogiaBnccAgent", "name": "V2c · Banca: Pedagogia & BNCC", "icon": "🅲", "output_key": "validacao_pedagogia_bncc", "prompt_file": "dev/v2c_validacao_pedagogia_bncc.md", "description": "PED-01…15."},
    {"id": "ValidacaoDadosLgpdAgent", "name": "V2d · Banca: Dados, Telemetria & LGPD", "icon": "🅳", "output_key": "validacao_dados_lgpd", "prompt_file": "dev/v2d_validacao_dados_lgpd.md", "description": "DAD-01…15."},
    {"id": "ValidacaoTecnicaArquiteturaAgent", "name": "V2e · Banca: Técnica & Arquitetura", "icon": "🅴", "output_key": "validacao_tecnica_arquitetura", "prompt_file": "dev/v2e_validacao_tecnica_arquitetura.md", "description": "TEC-01…13."},
    {"id": "ConsolidacaoBancaAgent", "name": "V3 · Consolidação da banca", "icon": "⚖️", "output_key": "validacao_dev_report", "prompt_file": "dev/v3_consolidacao_banca.md", "description": "Veredito determinístico 🟢/🟡/🔴 e bloqueios."},
    {"id": "ValidacaoDevCheck", "name": "V3c · Veredito de dev (determinístico)", "icon": "🔀", "output_key": "dev_status", "prompt_file": None, "description": "Lê o envelope da banca."},
    {"id": "PrdWriterAgent", "name": "V4 · PRD padrão ouro", "icon": "📘", "output_key": "prd_final", "prompt_file": "dev/v4_prd_writer.md", "description": "PRD completo com contexto arquitetural da plataforma — entregável do pipeline."},
]
