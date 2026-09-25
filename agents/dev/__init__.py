"""Área de DEV — do handoff ao PRD completo, validado pela banca de dev.

Ordem (SequentialAgent):
  v0  A33ManifestoCheck        → manifesto_status  (ficha do manifesto no bloco 0 da spec × listas
                               fechadas da plataforma; não conforme impede o PRD)
  ┌─ ParallelAgent ───────────────────────────────────────────────┐
  │ v1  A34HandoffDev      → handoff_dev  (insumo + stories +   │
  │                             eventos + escopo V1/V2)            │
  │ v1b A35BriefAssets     → brief_assets                        │
  └────────────────────────────────────────────────────────────────┘
  v1c A36TelemetriaCheck       → telemetria_status (contrato real de evento, tabela de leitura,
                               sem WebSocket, papéis e quota atuais)
  v1d A38LacunaCheck           → rastro_lacunas_status (marcadores de lacuna em spec, design,
                               handoff e assets, por dono: input · produto · design · dev ·
                               plataforma — só plataforma não bloqueia, e deixa o PRD 🟡)
  ┌─ ParallelAgent (banca /validar-missao, 5 dimensões) ──────────┐
  │ v2a ValidacaoProdutoNarrativa   → validacao_produto_narrativa │
  │ v2b ValidacaoDesignImersao      → validacao_design_imersao    │
  │ v2c ValidacaoPedagogiaBncc      → validacao_pedagogia_bncc    │
  │ v2d ValidacaoDadosLgpd          → validacao_dados_lgpd        │
  │ v2e ValidacaoTecnicaArquitetura → validacao_tecnica_arquitetura│
  └────────────────────────────────────────────────────────────────┘
  v3  A44ConsolidacaoBanca → validacao_dev_report (veredito 🟢/🟡/🔴)
  v3c A45ValidacaoDevCheck      → dev_status   (🔴 impede o PRD quando ESTEIRA_ESTRITA)
  ┌── PrdLoop (até PRD_MAX_RODADAS) ───────────────────────────────┐
  │ v4  A47PrdWriter         → prd_final ← entregável para o agente │
  │                            de codificação                       │
  │ v4c A48PrdCheck          → prd_status (marcadores que o redator │
  │                            deixou no PRD + consistência interna)│
  │ v4r A48PrdRodada         → prd_rodada (reprovado devolve ao     │
  │                            redator com o relatório do gate)     │
  └────────────────────────────────────────────────────────────────┘
  v5  A49OnePagerPedagogico → one_pager_pedagogico ← entregável para GENTE: o documento
                               que o time pedagógico lê para aprovar a missão antes de
                               alguém codificar. Sem jargão, com os links do protótipo,
                               exportado também em `.docx`.
"""

from __future__ import annotations

from typing import Optional

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent

from agents.juiz import get_juiz_de_achados
from agents.base import create_llm_agent
from agents.callbacks import marcar_heranca
from agents.checkers import (
    ConsolidacaoBancaAgent,
    DespachoTicketsAgent,
    EnvelopeGateAgent,
    RastroCheckAgent,
    SaidaDeLoopAgent,
)
from config import get_settings
from prompts import load_prompt
from tools.rastro import FONTES_DEV


def get_handoff_dev_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A34HandoffDev",
        description="Handoff para dev: modelo de insumo preenchido, user stories com 🔒, spec de eventos, escopo V1/V2 e hipóteses.",
        instruction=load_prompt("dev/34_handoff_dev.md"),
        output_key="handoff_dev",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_brief_assets_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A35BriefAssets",
        description="Brief de produção de conteúdo: inventário de assets, spec por tipo, critérios de reprovação e ordem de produção.",
        instruction=load_prompt("dev/35_brief_assets.md"),
        output_key="brief_assets",
        before_agent_callback=marcar_heranca,
        **kw,
    )


_VALIDADORES = [
    ("A39BancaProdutoNarrativa", "validacao_produto_narrativa", "dev/39_validacao_produto_narrativa.md",
     "Dimensão A — PO sênior de EdTech: produto e narrativa (PROD-01…16)."),
    ("A40BancaDesignImersao", "validacao_design_imersao", "dev/40_validacao_design_imersao.md",
     "Dimensão B — Design lead: design e imersão (DES-01…14)."),
    ("A41BancaPedagogiaBncc", "validacao_pedagogia_bncc", "dev/41_validacao_pedagogia_bncc.md",
     "Dimensão C — Avaliação educacional e BNCC (PED-01…15)."),
    ("A42BancaDadosLgpd", "validacao_dados_lgpd", "dev/42_validacao_dados_lgpd.md",
     "Dimensão D — Engenharia de dados + DPO: telemetria e LGPD (DAD-01…15)."),
    ("A43BancaTecnicaArquitetura", "validacao_tecnica_arquitetura", "dev/43_validacao_tecnica_arquitetura.md",
     "Dimensão E — Tech lead do monorepo: técnica e arquitetura (TEC-01…13)."),
]


def get_validador_agents(**kw) -> list[LlmAgent]:
    return [
        create_llm_agent(
            name=name,
            description=desc,
            instruction=load_prompt(prompt),
            output_key=key,
            before_agent_callback=marcar_heranca,
            deterministico=True,  # as cinco dimensões emitem veredito
            **kw,
        )
        for name, key, prompt, desc in _VALIDADORES
    ]


def get_consolidacao_banca_agent(**kw) -> ConsolidacaoBancaAgent:
    """Determinístico desde 23/09/2026 — ver `tools/banca.py` para o porquê."""
    return ConsolidacaoBancaAgent(
        name="A44ConsolidacaoBanca",
        description="Consolida as 5 dimensões da banca: veredito = o pior delas, com a lista de "
                    "bloqueantes lida dos próprios arquivos de critério.",
        fontes=[key for _, key, _, _ in _VALIDADORES],
    )


def get_prd_writer_agent(**kw) -> LlmAgent:
    settings = get_settings()
    return create_llm_agent(
        name="A47PrdWriter",
        description="Redige o PRD padrão ouro da missão, com o contexto arquitetural da plataforma, para alimentar um agente de codificação.",
        instruction=load_prompt("dev/47_prd_writer.md"),
        output_key="prd_final",
        model=settings.gemini_model_prd,
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_one_pager_pedagogico_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A49OnePagerPedagogico",
        description="O documento de validação humana: a missão inteira em linguagem de sala de aula, com o papel do professor, os links do protótipo e as perguntas que só o time pedagógico responde.",
        instruction=load_prompt("dev/49_one_pager_pedagogico.md"),
        output_key="one_pager_pedagogico",
        before_agent_callback=marcar_heranca,
        **kw,
    )


#: Slug do envelope da banca → cadeia de agentes que conserta. A dimensão B (design e
#: imersão) aponta para agentes de DESIGN: um erro de jornada ou de tela só é fatalmente
#: detectado aqui, uma etapa depois de quem o cometeu, e mandar ticket para quem não roda
#: mais é o mesmo que não mandar.
MAPA_BANCA = {
    "handoff-dev": ["A34HandoffDevRetrabalhoBanca"],
    "brief-assets": ["A35BriefAssetsRetrabalhoBanca"],
    "jornada": ["A22JornadaRetrabalhoBanca"],
    "fluxo": ["A23FluxoRetrabalhoBanca"],
    "copy-ptbr-revisao": ["A27CopyRevisaoRetrabalhoBanca"],
    "telas": ["A26TelasRetrabalhoBanca"],
}

#: Ordem entre donos: design antes de dev, porque o handoff deriva do design.
ORDEM_BANCA = [
    "jornada",
    "fluxo",
    "copy-ptbr-revisao",
    "telas",
    "handoff-dev",
    "brief-assets",
]

#: Achado de produto não se conserta aqui — a spec é de outra etapa e reabri-la invalida
#: tudo que foi construído sobre ela. Vira pendência nomeada no diagnóstico.
BANCA_EXTERNO = ["gate-estrutural", "spec-missao", "produto", "avaliacao-pedagogica", "experiencia-aluno"]


def _agentes_de_retrabalho_banca(**kw) -> list:
    """Instâncias que a banca aciona: quatro de design e duas de dev, com nome próprio."""
    from agents.design import (
        get_copy_revisao_agent,
        get_fluxo_agent,
        get_jornada_agent,
        get_wireframes_agent,
    )

    pares = [
        (get_jornada_agent, "A22JornadaRetrabalhoBanca"),
        (get_fluxo_agent, "A23FluxoRetrabalhoBanca"),
        (get_copy_revisao_agent, "A27CopyRevisaoRetrabalhoBanca"),
        (get_wireframes_agent, "A26TelasRetrabalhoBanca"),
        (get_handoff_dev_agent, "A34HandoffDevRetrabalhoBanca"),
        (get_brief_assets_agent, "A35BriefAssetsRetrabalhoBanca"),
    ]
    agentes = []
    for getter, nome in pares:
        agente = getter(**kw)
        agente.name = nome
        agente.description = f"{agente.description} (acionado pela banca de dev quando o achado é dele)"
        agentes.append(agente)
    return agentes


def build_dev_stage(
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
) -> SequentialAgent:
    kw = {"thinking_budget": thinking_budget, "include_thoughts": include_thoughts}
    estrito = get_settings().esteira_estrita
    rodadas_handoff = max(1, get_settings().handoff_max_rodadas)
    rodadas_banca = max(1, get_settings().banca_max_rodadas)
    rodadas_prd = max(1, get_settings().prd_max_rodadas)
    return SequentialAgent(
        name="DevStage",
        description="Área de Dev: ficha do manifesto → handoff + brief de assets → telemetria e rastro de lacunas → banca de validação (5 dimensões em paralelo) → consolidação → PRD → pendências do PRD → one-pager pedagógico para validação humana.",
        before_agent_callback=marcar_heranca,
        sub_agents=[
            RastroCheckAgent(
                name="A33ManifestoCheck",
                description="Ficha do manifesto no bloco 0 da spec × listas fechadas da plataforma (produto, séries, unidade, público, viewport, permissões, capabilities, seção do DS, liberação por turma).",
                modo="manifesto",
                rotulo="Ficha do manifesto",
                report_key="manifesto_report",
                status_key="manifesto_status",
                estrito=estrito,
                before_agent_callback=marcar_heranca,
            ),
            # O handoff é o loop mais barato da esteira: os dez achados do contrato de
            # telemetria são violações mecânicas (campo `dados` que a api descarta em
            # silêncio, papel antigo, WebSocket onde a plataforma exige polling), todas
            # dentro da autoria do V1, e cada mensagem do gate já traz a correção escrita.
            LoopAgent(
                name="HandoffLoop",
                description="Handoff e brief de assets ↔ contrato de telemetria, até o contrato bater ou esgotar as rodadas.",
                max_iterations=rodadas_handoff,
                before_agent_callback=marcar_heranca,
                sub_agents=[
                    ParallelAgent(
                        name="HandoffParalelo",
                        description="Handoff para dev e brief de assets rodam em paralelo (mesmas pré-condições).",
                        sub_agents=[get_handoff_dev_agent(**kw), get_brief_assets_agent(**kw)],
                        before_agent_callback=marcar_heranca,
                    ),
                    RastroCheckAgent(
                        name="A36TelemetriaCheck",
                        description="Contrato real de evento no handoff (verbo · objeto · resultado · contexto, sem `dados`), tabela de leitura das medidas, sem WebSocket, papéis e quota atuais.",
                        modo="telemetria",
                        rotulo="Contrato de telemetria e arquitetura",
                        report_key="telemetria_report",
                        status_key="telemetria_status",
                        estrito=estrito,
                        before_agent_callback=marcar_heranca,
                    ),
                    get_juiz_de_achados("A36bJuizTelemetria", status_key="telemetria_status",
                                        report_key="telemetria_report", fonte_key="handoff_dev",
                                        gate_rotulo="Contrato de telemetria e arquitetura", **kw),
                    SaidaDeLoopAgent(
                        name="A37HandoffCheck",
                        description="Contrato conforme encerra o loop; reprovado devolve o handoff ao V1 com o relatório do gate.",
                        rotulo="Handoff de dev",
                        status_keys=["telemetria_status"],
                        rodada_key="handoff_rodada",
                        max_rounds=rodadas_handoff,
                    ),
                ],
            ),
            RastroCheckAgent(
                name="A38LacunaCheck",
                description="Conta os marcadores de lacuna em spec, design, handoff e assets e diz o que faltou de input, produto, design ou dev. Só pendência de plataforma não bloqueia (PRD 🟡).",
                modo="lacunas",
                rotulo="Rastro de lacunas antes do PRD",
                report_key="rastro_lacunas_report",
                status_key="rastro_lacunas_status",
                fontes=FONTES_DEV,
                etapa="dev",
                agente="rastro-lacunas",
                estrito=estrito,
                before_agent_callback=marcar_heranca,
            ),
            LoopAgent(
                name="BancaLoop",
                description="Banca de cinco dimensões ↔ retrabalho do dono de cada achado, até a banca liberar ou esgotar as rodadas.",
                max_iterations=rodadas_banca,
                before_agent_callback=marcar_heranca,
                sub_agents=[
                    ParallelAgent(
                        name="BancaValidacaoDev",
                        description="Banca /validar-missao: cinco dimensões avaliadas em paralelo.",
                        sub_agents=get_validador_agents(**kw),
                        before_agent_callback=marcar_heranca,
                    ),
                    get_consolidacao_banca_agent(**kw),
                    EnvelopeGateAgent(
                        name="A45ValidacaoDevCheck",
                        description="Lê o veredito da banca: aprovado encerra o loop; reprovado despacha o retrabalho ao dono de cada achado.",
                        rotulo="Banca de dev",
                        report_key="validacao_dev_report",
                        status_key="dev_status",
                        round_key="banca_rodada",
                        max_rounds=rodadas_banca,
                        escalate_on_approve=True,
                        block_pipeline_on_fail=estrito,
                        before_agent_callback=marcar_heranca,
                    ),
                    DespachoTicketsAgent(
                        name="A46DespachoBanca",
                        description="Lê os achados da banca e reexecuta só o dono de cada um — inclusive quando o dono está na etapa de design.",
                        rotulo="Retrabalho da banca",
                        report_key="validacao_dev_report",
                        mapa=MAPA_BANCA,
                        ordem=ORDEM_BANCA,
                        externos=BANCA_EXTERNO,
                        before_agent_callback=marcar_heranca,
                        sub_agents=_agentes_de_retrabalho_banca(**kw),
                    ),
                ],
            ),
            LoopAgent(
                name="PrdLoop",
                description="Redator do PRD ↔ gate de consistência, até o PRD fechar ou esgotar as rodadas.",
                max_iterations=rodadas_prd,
                before_agent_callback=marcar_heranca,
                sub_agents=[
                    get_prd_writer_agent(**kw),
                    RastroCheckAgent(
                        name="A48PrdCheck",
                        description="Marcadores que o redator deixou no PRD ([NEEDS CLARIFICATION], [verificar no repositório], 🔵) e consistência interna (caminho, prefixo de tabela, P0 sem rastro, evento sem leitor): lacuna de produto/design/dev marca o PRD como não pronto; só plataforma deixa 🟡.",
                        modo="prd",
                        rotulo="Pendências e consistência do PRD",
                        report_key="prd_check_report",
                        status_key="prd_status",
                        fontes=[{"chave": "prd_final", "rotulo": "PRD", "etapa_padrao": "dev"}],
                        agente="prd-check",
                        estrito=estrito,
                        before_agent_callback=marcar_heranca,
                    ),
                    RastroCheckAgent(
                        name="A48bKpisCheck",
                        description="Coerência KPI ↔ evento ↔ tela: todo KPI com pergunta, decisão, corte, evento que dispara na tela que o KPI nomeia, e baseline honesto.",
                        modo="kpis",
                        rotulo="Coerência KPI ↔ evento ↔ tela",
                        report_key="kpis_report",
                        status_key="kpis_status",
                        agente="kpis-check",
                        estrito=get_settings().kpis_check_estrito,
                        before_agent_callback=marcar_heranca,
                    ),
                    SaidaDeLoopAgent(
                        name="A48PrdRodada",
                        description="PRD consistente encerra o loop; reprovado devolve ao redator com o relatório do gate.",
                        rotulo="Consistência do PRD",
                        status_keys=["prd_status", "kpis_status"],
                        rodada_key="prd_rodada",
                        max_rounds=rodadas_prd,
                    ),
                ],
            ),
            get_one_pager_pedagogico_agent(**kw),
        ],
    )


DEV_METADATA = [
    {"id": "A33ManifestoCheck", "name": "33 · Ficha do manifesto (determinístico)", "icon": "🪪", "output_key": "manifesto_report", "prompt_file": None, "description": "Bloco 0 da spec × listas fechadas da plataforma: produto, séries, unidade, público, viewport, permissões, capabilities, seção do DS, liberação por turma. Não conforme impede o PRD."},
    {"id": "A34HandoffDev", "name": "34 · Handoff para dev", "icon": "🤝", "output_key": "handoff_dev", "prompt_file": "dev/34_handoff_dev.md", "description": "Modelo de insumo preenchido, stories com 🔒, eventos, escopo V1/V2, hipóteses (paralelo com V1b)."},
    {"id": "A35BriefAssets", "name": "35 · Brief de assets", "icon": "🎬", "output_key": "brief_assets", "prompt_file": "dev/35_brief_assets.md", "description": "Inventário de assets, spec por tipo, critérios de reprovação, ordem de produção."},
    {"id": "A36TelemetriaCheck", "name": "36 · Contrato de telemetria e arquitetura (determinístico)", "icon": "📡", "output_key": "telemetria_report", "prompt_file": None, "description": "Evento = verbo · objeto · resultado · contexto (sem `dados`), medida com tabela de leitura, sem WebSocket, seis papéis, quota em `ia_quotas`."},
    {"id": "A37HandoffCheck", "name": "37 · Veredito do handoff (determinístico)", "icon": "🔀", "output_key": "handoff_rodada", "prompt_file": None, "description": "Contrato de telemetria conforme encerra o loop; reprovado devolve o handoff ao V1 com o relatório."},
    {"id": "A38LacunaCheck", "name": "38 · Rastro de lacunas (determinístico)", "icon": "🧭", "output_key": "rastro_lacunas_report", "prompt_file": None, "description": "Marcadores de lacuna em spec, design, handoff e assets, por dono: o que faltou de input, produto, design ou dev impede o PRD; plataforma vira pendência humana (🟡)."},
    {"id": "A39BancaProdutoNarrativa", "name": "39 · Banca: Produto & Narrativa", "icon": "🅰️", "output_key": "validacao_produto_narrativa", "prompt_file": "dev/39_validacao_produto_narrativa.md", "description": "PROD-01…16."},
    {"id": "A40BancaDesignImersao", "name": "40 · Banca: Design & Imersão", "icon": "🅱️", "output_key": "validacao_design_imersao", "prompt_file": "dev/40_validacao_design_imersao.md", "description": "DES-01…14."},
    {"id": "A41BancaPedagogiaBncc", "name": "41 · Banca: Pedagogia & BNCC", "icon": "🅲", "output_key": "validacao_pedagogia_bncc", "prompt_file": "dev/41_validacao_pedagogia_bncc.md", "description": "PED-01…15."},
    {"id": "A42BancaDadosLgpd", "name": "42 · Banca: Dados, Telemetria & LGPD", "icon": "🅳", "output_key": "validacao_dados_lgpd", "prompt_file": "dev/42_validacao_dados_lgpd.md", "description": "DAD-01…15."},
    {"id": "A43BancaTecnicaArquitetura", "name": "43 · Banca: Técnica & Arquitetura", "icon": "🅴", "output_key": "validacao_tecnica_arquitetura", "prompt_file": "dev/43_validacao_tecnica_arquitetura.md", "description": "TEC-01…13."},
    {"id": "A44ConsolidacaoBanca", "name": "44 · Consolidação da banca", "icon": "⚖️", "output_key": "validacao_dev_report", "prompt_file": None, "description": "Determinístico: veredito = a pior das 5 dimensões; bloqueantes lidos de `references/criterios-dev/`."},
    {"id": "A45ValidacaoDevCheck", "name": "45 · Veredito de dev (determinístico)", "icon": "🔀", "output_key": "dev_status", "prompt_file": None, "description": "Lê o envelope da banca."},
    {"id": "A46DespachoBanca", "name": "46 · Retrabalho da banca (determinístico)", "icon": "🔁", "output_key": "reexecucoes", "prompt_file": None, "description": "Reexecuta o dono de cada achado da banca — inclusive quando o dono está na etapa de design. Achado de produto vira pendência nomeada."},
    {"id": "A47PrdWriter", "name": "47 · PRD padrão ouro", "icon": "📘", "output_key": "prd_final", "prompt_file": "dev/47_prd_writer.md", "description": "PRD completo com contexto arquitetural da plataforma — entregável do pipeline."},
    {"id": "A48PrdCheck", "name": "48 · Pendências do PRD (determinístico)", "icon": "🧭", "output_key": "prd_check_report", "prompt_file": None, "description": "Marcadores que o redator deixou no PRD, mais a consistência interna do documento (prefixo de tabela único, requisito P0 com teste e tarefa, evento com tabela leitora, caminho único). lacuna de produto/design/dev marca o PRD como não pronto, plataforma deixa 🟡."},
    # sem esta linha o gate rodava, podia bloquear, e a tela não tinha onde mostrar o relatório (24/09/2026)
    {"id": "A48bKpisCheck", "name": "48a · Coerência KPI ↔ evento ↔ tela (determinístico)", "icon": "📈", "output_key": "kpis_report", "prompt_file": None, "description": "Todo KPI com pergunta, decisão, corte e evento que dispara na tela que ele nomeia; os sinais universais das transversais de dono missão na tabela de eventos, com a IA ao estudante decidida pela spec."},
    {"id": "A48PrdRodada", "name": "48b · Veredito do PRD (determinístico)", "icon": "🔁", "output_key": "prd_rodada", "prompt_file": None, "description": "PRD consistente encerra o loop; reprovado devolve ao redator com o relatório do gate, até o teto de rodadas."},
    {"id": "A49OnePagerPedagogico", "name": "49 · One-pager pedagógico (validação humana)", "icon": "🧑‍🏫", "output_key": "one_pager_pedagogico", "prompt_file": "dev/49_one_pager_pedagogico.md", "description": "A missão inteira em linguagem de sala de aula, com o papel do professor, os links do protótipo e as perguntas de aprovação. Salvo em Markdown e `.docx`."},
]
