"""Área de DEV — do handoff ao PRD completo, validado pela banca de dev.

Ordem (SequentialAgent):
  v0  ManifestoCheck        → manifesto_status  (ficha do manifesto no bloco 0 da spec × listas
                               fechadas da plataforma; não conforme impede o PRD)
  ┌─ ParallelAgent ───────────────────────────────────────────────┐
  │ v1  HandoffDevAgent      → handoff_dev  (insumo + stories +   │
  │                             eventos + escopo V1/V2)            │
  │ v1b BriefAssetsAgent     → brief_assets                        │
  └────────────────────────────────────────────────────────────────┘
  v1c TelemetriaCheck       → telemetria_status (contrato real de evento, tabela de leitura,
                               sem WebSocket, papéis e quota atuais)
  v1d LacunaCheck           → rastro_lacunas_status (marcadores de lacuna em spec, design,
                               handoff e assets, por dono: input · produto · design · dev ·
                               plataforma — só plataforma não bloqueia, e deixa o PRD 🟡)
  ┌─ ParallelAgent (banca /validar-missao, 5 dimensões) ──────────┐
  │ v2a ValidacaoProdutoNarrativa   → validacao_produto_narrativa │
  │ v2b ValidacaoDesignImersao      → validacao_design_imersao    │
  │ v2c ValidacaoPedagogiaBncc      → validacao_pedagogia_bncc    │
  │ v2d ValidacaoDadosLgpd          → validacao_dados_lgpd        │
  │ v2e ValidacaoTecnicaArquitetura → validacao_tecnica_arquitetura│
  └────────────────────────────────────────────────────────────────┘
  v3  ConsolidacaoBancaAgent → validacao_dev_report (veredito 🟢/🟡/🔴)
  v3c ValidacaoDevCheck      → dev_status   (🔴 impede o PRD quando ESTEIRA_ESTRITA)
  v4  PrdWriterAgent         → prd_final   ← entregável do pipeline
  v4c PrdCheck               → prd_status  (marcadores que o redator deixou no PRD; lacuna de
                               produto/design/dev marca o PRD como não pronto)
"""

from __future__ import annotations

from typing import Optional

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent

from agents.base import create_llm_agent
from agents.callbacks import skip_if_blocked
from agents.checkers import EnvelopeGateAgent, RastroCheckAgent
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
    estrito = get_settings().esteira_estrita
    fontes_lacunas = [
        {"chave": "spec_missao", "rotulo": "spec da missão", "etapa_padrao": "produto"},
        {"chave": "jornada_telas", "rotulo": "jornada (D2)", "etapa_padrao": "design"},
        {"chave": "fluxo_arestas", "rotulo": "fluxo (D3)", "etapa_padrao": "design"},
        {"chave": "copy_strings_revisada", "rotulo": "copy revisada (D6)", "etapa_padrao": "design"},
        {"chave": "wireframes_cobertura", "rotulo": "wireframes (D5)", "etapa_padrao": "design"},
        {"chave": "camada_caa", "rotulo": "camada CAA (D4b)", "etapa_padrao": "design"},
        {"chave": "ambiente_simulado", "rotulo": "ambiente simulado (D9)", "etapa_padrao": "design"},
        {"chave": "handoff_dev", "rotulo": "handoff de dev (V1)", "etapa_padrao": "dev"},
        {"chave": "brief_assets", "rotulo": "brief de assets (V1b)", "etapa_padrao": "dev"},
    ]
    return SequentialAgent(
        name="DevStage",
        description="Área de Dev: ficha do manifesto → handoff + brief de assets → telemetria e rastro de lacunas → banca de validação (5 dimensões em paralelo) → consolidação → PRD → pendências do PRD.",
        before_agent_callback=skip_if_blocked,
        sub_agents=[
            RastroCheckAgent(
                name="ManifestoCheck",
                description="Ficha do manifesto no bloco 0 da spec × listas fechadas da plataforma (produto, séries, unidade, público, viewport, permissões, capabilities, seção do DS, liberação por turma).",
                modo="manifesto",
                rotulo="Ficha do manifesto",
                report_key="manifesto_report",
                status_key="manifesto_status",
                estrito=estrito,
                before_agent_callback=skip_if_blocked,
            ),
            ParallelAgent(
                name="HandoffParalelo",
                description="Handoff para dev e brief de assets rodam em paralelo (mesmas pré-condições).",
                sub_agents=[get_handoff_dev_agent(**kw), get_brief_assets_agent(**kw)],
                before_agent_callback=skip_if_blocked,
            ),
            RastroCheckAgent(
                name="TelemetriaCheck",
                description="Contrato real de evento no handoff (verbo · objeto · resultado · contexto, sem `dados`), tabela de leitura das medidas, sem WebSocket, papéis e quota atuais.",
                modo="telemetria",
                rotulo="Contrato de telemetria e arquitetura",
                report_key="telemetria_report",
                status_key="telemetria_status",
                estrito=estrito,
                before_agent_callback=skip_if_blocked,
            ),
            RastroCheckAgent(
                name="LacunaCheck",
                description="Conta os marcadores de lacuna em spec, design, handoff e assets e diz o que faltou de input, produto, design ou dev. Só pendência de plataforma não bloqueia (PRD 🟡).",
                modo="lacunas",
                rotulo="Rastro de lacunas antes do PRD",
                report_key="rastro_lacunas_report",
                status_key="rastro_lacunas_status",
                fontes=fontes_lacunas,
                agente="rastro-lacunas",
                estrito=estrito,
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
                description="Lê o veredito da banca de dev: 🔴 impede o PRD (modo estrito); 🟡 segue e entra no frontmatter.",
                rotulo="Banca de dev",
                report_key="validacao_dev_report",
                status_key="dev_status",
                block_pipeline_on_fail=estrito,
                treat_indefinido_as_blocked=False,
            ),
            get_prd_writer_agent(**kw),
            RastroCheckAgent(
                name="PrdCheck",
                description="Marcadores que o redator deixou no PRD ([NEEDS CLARIFICATION], [verificar no repositório], 🔵): lacuna de produto/design/dev marca o PRD como não pronto; só plataforma deixa 🟡.",
                modo="lacunas",
                rotulo="Pendências do PRD",
                report_key="prd_check_report",
                status_key="prd_status",
                fontes=[{"chave": "prd_final", "rotulo": "PRD", "etapa_padrao": "dev"}],
                agente="prd-check",
                estrito=estrito,
                before_agent_callback=skip_if_blocked,
            ),
        ],
    )


DEV_METADATA = [
    {"id": "ManifestoCheck", "name": "V0 · Ficha do manifesto (determinístico)", "icon": "🪪", "output_key": "manifesto_report", "prompt_file": None, "description": "Bloco 0 da spec × listas fechadas da plataforma: produto, séries, unidade, público, viewport, permissões, capabilities, seção do DS, liberação por turma. Não conforme impede o PRD."},
    {"id": "HandoffDevAgent", "name": "V1 · Handoff para dev", "icon": "🤝", "output_key": "handoff_dev", "prompt_file": "dev/v1_handoff_dev.md", "description": "Modelo de insumo preenchido, stories com 🔒, eventos, escopo V1/V2, hipóteses (paralelo com V1b)."},
    {"id": "BriefAssetsAgent", "name": "V1b · Brief de assets", "icon": "🎬", "output_key": "brief_assets", "prompt_file": "dev/v1b_brief_assets.md", "description": "Inventário de assets, spec por tipo, critérios de reprovação, ordem de produção."},
    {"id": "TelemetriaCheck", "name": "V1c · Contrato de telemetria e arquitetura (determinístico)", "icon": "📡", "output_key": "telemetria_report", "prompt_file": None, "description": "Evento = verbo · objeto · resultado · contexto (sem `dados`), medida com tabela de leitura, sem WebSocket, seis papéis, quota em `ia_quotas`."},
    {"id": "LacunaCheck", "name": "V1d · Rastro de lacunas (determinístico)", "icon": "🧭", "output_key": "rastro_lacunas_report", "prompt_file": None, "description": "Marcadores de lacuna em spec, design, handoff e assets, por dono: o que faltou de input, produto, design ou dev impede o PRD; plataforma vira pendência humana (🟡)."},
    {"id": "ValidacaoProdutoNarrativaAgent", "name": "V2a · Banca: Produto & Narrativa", "icon": "🅰️", "output_key": "validacao_produto_narrativa", "prompt_file": "dev/v2a_validacao_produto_narrativa.md", "description": "PROD-01…16."},
    {"id": "ValidacaoDesignImersaoAgent", "name": "V2b · Banca: Design & Imersão", "icon": "🅱️", "output_key": "validacao_design_imersao", "prompt_file": "dev/v2b_validacao_design_imersao.md", "description": "DES-01…13."},
    {"id": "ValidacaoPedagogiaBnccAgent", "name": "V2c · Banca: Pedagogia & BNCC", "icon": "🅲", "output_key": "validacao_pedagogia_bncc", "prompt_file": "dev/v2c_validacao_pedagogia_bncc.md", "description": "PED-01…15."},
    {"id": "ValidacaoDadosLgpdAgent", "name": "V2d · Banca: Dados, Telemetria & LGPD", "icon": "🅳", "output_key": "validacao_dados_lgpd", "prompt_file": "dev/v2d_validacao_dados_lgpd.md", "description": "DAD-01…15."},
    {"id": "ValidacaoTecnicaArquiteturaAgent", "name": "V2e · Banca: Técnica & Arquitetura", "icon": "🅴", "output_key": "validacao_tecnica_arquitetura", "prompt_file": "dev/v2e_validacao_tecnica_arquitetura.md", "description": "TEC-01…13."},
    {"id": "ConsolidacaoBancaAgent", "name": "V3 · Consolidação da banca", "icon": "⚖️", "output_key": "validacao_dev_report", "prompt_file": "dev/v3_consolidacao_banca.md", "description": "Veredito determinístico 🟢/🟡/🔴 e bloqueios."},
    {"id": "ValidacaoDevCheck", "name": "V3c · Veredito de dev (determinístico)", "icon": "🔀", "output_key": "dev_status", "prompt_file": None, "description": "Lê o envelope da banca."},
    {"id": "PrdWriterAgent", "name": "V4 · PRD padrão ouro", "icon": "📘", "output_key": "prd_final", "prompt_file": "dev/v4_prd_writer.md", "description": "PRD completo com contexto arquitetural da plataforma — entregável do pipeline."},
    {"id": "PrdCheck", "name": "V4c · Pendências do PRD (determinístico)", "icon": "🧭", "output_key": "prd_check_report", "prompt_file": None, "description": "Conta os marcadores que o redator deixou no PRD; lacuna de produto/design/dev marca o PRD como não pronto, plataforma deixa 🟡."},
]
