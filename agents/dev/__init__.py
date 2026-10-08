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
  v1e A35bBancoConteudo        → banco_conteudo  (o texto integral de cada item de conteúdo do brief
                               e as falas da IA simulada por estado — `dev/01e-banco-conteudo.md`)
  v1f A35cConteudoCheck        → conteudo_status (determinístico: todo ID de texto do brief tem bloco;
                               Status do brief só `a produzir | rascunho | escrito`; falas por estado)
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
  │ v4a A48cConteudoAprovadoPrd → conteudo_aprovado_prd_status      │
  │                            (habilidades, KPI por habilidade,    │
  │                            tempo, podcast e caminhos × one-pager)│
  │ v4r A48PrdRodada         → prd_rodada (reprovado devolve ao     │
  │                            redator com o relatório do gate)     │
  └────────────────────────────────────────────────────────────────┘
  v4d A48dAnexoPrd             → prd_final + anexo literal do one-pager aprovado (§2, 9, 10,
                               11, 12, 17): o que nenhum gabarito tinha onde pôr
  ┌── OnePagerPedagogicoLoop (até PRD_MAX_RODADAS) ─────────────────┐
  │ v5  A49OnePagerPedagogico → one_pager_pedagogico ← entregável   │
  │       para GENTE: o documento que o time pedagógico lê para      │
  │       aprovar a missão antes de alguém codificar. Sem jargão,    │
  │       com os links do protótipo, exportado também em `.docx`.    │
  │ v5b A49bConteudoAprovadoPedagogico → habilidades, tempo,        │
  │       podcast e caminhos × one-pager aprovado                   │
  └────────────────────────────────────────────────────────────────┘
  v5c A49cAnexoPedagogico      → one_pager_pedagogico + anexo literal (§10, 11, 12)
"""

from __future__ import annotations

from typing import Optional

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent

from agents.juiz import get_fidelidade_check, get_juiz_de_achados
from agents.base import create_llm_agent
from agents.callbacks import marcar_heranca
from agents.checkers import (
    AnexoAprovadoAgent,
    ConsolidacaoBancaAgent,
    ConteudoAprovadoAgent,
    DespachoTicketsAgent,
    EnvelopeGateAgent,
    RastroCheckAgent,
    SaidaDeLoopAgent,
    RastreabilidadeAgent,
)
from config import get_settings
from prompts import load_prompt
from tools.conteudo_aprovado import SECOES_DEV, SECOES_PEDAGOGICO, SECOES_PRD
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


def get_banco_conteudo_agent(**kw) -> LlmAgent:
    """O texto que o brief de assets só descreve. Na exp09ef1b o banco padrão inteiro (12 PDFs, atas,
    cadernos, a tabela da Linha 302) e quase toda a fala da IA simulada ficaram por escrever, com o
    brief dizendo "Homologado" — e o PRD mandou codificar sobre conteúdo nenhum."""
    return create_llm_agent(
        name="A35bBancoConteudo",
        description="Banco de conteúdo: o texto integral de cada documento, tabela, transcrição e roteiro do brief de assets, e a árvore de falas da IA simulada por estado da spec (boas-vindas, fora do tema, aviso de limite).",
        instruction=load_prompt("dev/35b_banco_conteudo.md"),
        output_key="banco_conteudo",
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
    # a revisão descarta o que a passada 1 escreveu (prompts, banco curado, podcast): o código reanexa logo depois,
    # antes de brief e banco consertados na mesma rodada lerem a copy (auditoria da noite de 07/10/2026)
    "copy-ptbr-revisao": ["A27CopyRevisaoRetrabalhoBanca", "A27bCopyPreservadaRetrabalhoBanca"],
    "telas": ["A26TelasRetrabalhoBanca", "A26bStitchGeracaoRetrabalhoBanca"],
    # PROD-16 confere o banco contra o brief, e o dono não tinha rota: o ticket virava pendência humana
    "banco-conteudo": ["A35bBancoConteudoRetrabalhoBanca"],
}

#: Depois de um conserto de design pedido pela banca, o que deriva dele: o protótipo e as conferências
#: (copy preservada, artefatos, consistência, telas por ID) e o handoff, que a banca vai reler.
_DERIVADOS_DO_DESIGN = ["A27bCopyPreservadaRetrabalhoBanca", "A28PrototipoRetrabalhoBanca",
                        "A29ArtefatosDesignRetrabalhoBanca", "A29dConsistenciaRetrabalhoBanca",
                        "A29eCoberturaTelasRetrabalhoBanca", "A34HandoffDevRetrabalhoBanca",
                        "A36TelemetriaCheckRetrabalhoBanca"]
POSFIXO_BANCA = {dono: _DERIVADOS_DO_DESIGN for dono in ("jornada", "fluxo", "copy-ptbr-revisao", "telas")}
# O banco e o handoff reescritos pela banca passavam sem a conferência que tiveram na primeira passada: o podcast
# do §11 (só o A35c o confere) e o contrato de telemetria (A36). O veredito velho seguia no semáforo de dev.
POSFIXO_BANCA["banco-conteudo"] = ["A35cConteudoCheckRetrabalhoBanca"]
POSFIXO_BANCA["handoff-dev"] = ["A36TelemetriaCheckRetrabalhoBanca"]

#: Ordem entre donos: design antes de dev, porque o handoff deriva do design. Telas antes da copy, como no
#: retrabalho do design (`ORDEM_RETRABALHO`): a revisão da copy lê as telas.
ORDEM_BANCA = [
    "jornada",
    "fluxo",
    "telas",
    "copy-ptbr-revisao",
    "handoff-dev",
    "brief-assets",
    "banco-conteudo",  # o banco lê o brief: conserta depois dele
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
        get_prototipo_agent,
        get_wireframes_agent,
    )

    pares = [
        (get_jornada_agent, "A22JornadaRetrabalhoBanca"),
        (get_fluxo_agent, "A23FluxoRetrabalhoBanca"),
        (get_copy_revisao_agent, "A27CopyRevisaoRetrabalhoBanca"),
        (get_wireframes_agent, "A26TelasRetrabalhoBanca"),
        (get_handoff_dev_agent, "A34HandoffDevRetrabalhoBanca"),
        (get_brief_assets_agent, "A35BriefAssetsRetrabalhoBanca"),
        (get_banco_conteudo_agent, "A35bBancoConteudoRetrabalhoBanca"),
        (get_prototipo_agent, "A28PrototipoRetrabalhoBanca"),
    ]
    agentes = []
    for getter, nome in pares:
        agente = getter(**kw)
        agente.name = nome
        agente.description = f"{agente.description} (acionado pela banca de dev quando o achado é dele)"
        agentes.append(agente)
    # determinísticos que seguem um conserto de design pedido pela banca (`POSFIXO_BANCA`)
    from agents.checkers import ArtefatosDesignAgent, CoberturaTelasAgent, CopyPreservadaAgent, StitchGeracaoAgent
    from agents.design import get_consistencia_check

    estrito = get_settings().esteira_estrita
    agentes += [
        CopyPreservadaAgent(name="A27bCopyPreservadaRetrabalhoBanca"),
        StitchGeracaoAgent(name="A26bStitchGeracaoRetrabalhoBanca"),
        ArtefatosDesignAgent(name="A29ArtefatosDesignRetrabalhoBanca",
                             description="Reextrai o HTML do protótipo e os links do Stitch depois de um conserto pedido pela banca."),
        get_consistencia_check("A29dConsistenciaRetrabalhoBanca"),
        CoberturaTelasAgent(name="A29eCoberturaTelasRetrabalhoBanca"),
        # as conferências de dev que a primeira passada teve, de novo sobre o que a banca reescreveu
        RastroCheckAgent(
            name="A35cConteudoCheckRetrabalhoBanca",
            description="O banco reescrito pela banca, conferido de novo: IDs do brief com bloco, Status do brief, falas por estado e o roteiro do podcast do one-pager.",
            modo="conteudo", rotulo="Banco de conteúdo", report_key="conteudo_report", status_key="conteudo_status",
            agente="conteudo-check", estrito=estrito,
        ),
        RastroCheckAgent(
            name="A36TelemetriaCheckRetrabalhoBanca",
            description="O handoff reescrito pela banca, conferido de novo contra o contrato real de evento e as proibições de arquitetura.",
            modo="telemetria", rotulo="Contrato de telemetria e arquitetura", report_key="telemetria_report",
            status_key="telemetria_status", estrito=estrito,
        ),
    ]
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
        description="Área de Dev: ficha do manifesto → handoff + brief de assets → banco de conteúdo → telemetria e rastro de lacunas → banca de validação (5 dimensões em paralelo) → consolidação → PRD → pendências do PRD → one-pager pedagógico para validação humana.",
        before_agent_callback=marcar_heranca,
        sub_agents=[
            # As mesmas seções do design: até 07/10/2026 esta chave era regravada só com as do PRD, e a banca —
            # e os agentes de design que ela reaciona — perdiam §8, §13 e o núcleo aprovado (§1, §3, §4).
            ConteudoAprovadoAgent(
                name="A33aConteudoAprovadoDev",
                description="Grava as seções do one-pager aprovado, literais — as mesmas do design —, para o banco de conteúdo, a banca e os agentes de design que ela reaciona, que não leem o one-pager.",
                secoes=list(SECOES_DEV),
                chave_base="conteudo_aprovado_base_dev",
                before_agent_callback=marcar_heranca,
            ),
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
            # O brief descreve; o banco escreve. Depois do loop do handoff, porque lê o brief final.
            # Em loop desde 07/10/2026: o bloqueio do verificador (podcast reescrito, ID sem bloco) não
            # voltava a ninguém — o banco rodava uma vez e o achado ia direto ao dossiê.
            LoopAgent(
                name="BancoLoop",
                description="Banco de conteúdo ↔ verificador do banco, até o banco fechar ou esgotar as rodadas.",
                max_iterations=2,
                before_agent_callback=marcar_heranca,
                sub_agents=[
                    get_banco_conteudo_agent(**kw),
                    RastroCheckAgent(
                        name="A35cConteudoCheck",
                        description="Todo ID de texto, documento, tabela e roteiro do brief tem bloco escrito no banco; o Status do brief é `a produzir | rascunho | escrito` (homologar é ato humano); cada estado de fala da IA na spec tem fala; o roteiro do podcast é o do one-pager.",
                        modo="conteudo",
                        rotulo="Banco de conteúdo",
                        report_key="conteudo_report",
                        status_key="conteudo_status",
                        agente="conteudo-check",
                        estrito=estrito,
                        before_agent_callback=marcar_heranca,
                    ),
                    SaidaDeLoopAgent(
                        name="A35dBancoRodada",
                        description="Banco conferido encerra o loop; com bloqueio, o banco reescreve com o relatório.",
                        rotulo="Banco de conteúdo",
                        status_keys=["conteudo_status"],
                        rodada_key="banco_rodada",
                        max_rounds=2,
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
                        posfixo_por_dono=POSFIXO_BANCA,
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
                    RastroCheckAgent(
                        name="A48cConteudoAprovadoPrd",
                        description="PRD × one-pager aprovado e spec: as habilidades do bloco 11 na matriz da seção 14, um KPI por habilidade, o tempo em tela do §10, o podcast do §11 com requisito, e só caminhos de artefato que a sessão tem.",
                        modo="aprovado_prd",
                        rotulo="PRD × one-pager aprovado",
                        report_key="conteudo_aprovado_prd_report",
                        status_key="conteudo_aprovado_prd_status",
                        agente="conteudo-aprovado",
                        estrito=estrito,
                        before_agent_callback=marcar_heranca,
                    ),
                    SaidaDeLoopAgent(
                        name="A48PrdRodada",
                        description="PRD consistente encerra o loop; reprovado devolve ao redator com o relatório do gate.",
                        rotulo="Consistência do PRD",
                        status_keys=["prd_status", "kpis_status", "conteudo_aprovado_prd_status"],
                        rodada_key="prd_rodada",
                        max_rounds=rodadas_prd,
                    ),
                ],
            ),
            # Depois do loop, para os gates lerem só o que o redator escreveu. O PRD das 11 missões do
            # bucket não tinha onde pôr o podcast, os tempos e o contrato de evidência, e os resumia.
            AnexoAprovadoAgent(
                name="A48dAnexoPrd",
                description="Cola no fim do PRD as seções do one-pager aprovado — currículo, professor, tempos e cenários, podcast, contrato de evidência, hipóteses —, literais.",
                chave="prd_final",
                secoes=list(SECOES_PRD),
                rotulo="Anexo do PRD",
                before_agent_callback=marcar_heranca,
            ),
            LoopAgent(
                name="OnePagerPedagogicoLoop",
                description="One-pager pedagógico ↔ conferência contra o one-pager aprovado, até bater ou esgotar as rodadas.",
                max_iterations=rodadas_prd,
                before_agent_callback=marcar_heranca,
                sub_agents=[
                    get_one_pager_pedagogico_agent(**kw),
                    RastroCheckAgent(
                        name="A49bConteudoAprovadoPedagogico",
                        description="One-pager pedagógico × one-pager aprovado e spec: as habilidades do bloco 11, o tempo em tela do §10, o podcast do §11 e só caminhos de artefato que a sessão tem.",
                        modo="aprovado_pedagogico",
                        rotulo="Pedagógico × one-pager aprovado",
                        report_key="conteudo_aprovado_pedagogico_report",
                        status_key="conteudo_aprovado_pedagogico_status",
                        agente="conteudo-aprovado",
                        estrito=estrito,
                        before_agent_callback=marcar_heranca,
                    ),
                    SaidaDeLoopAgent(
                        name="A49PedagogicoRodada",
                        description="Pedagógico fiel encerra o loop; divergente volta ao redator com o relatório.",
                        rotulo="One-pager pedagógico",
                        status_keys=["conteudo_aprovado_pedagogico_status"],
                        rodada_key="pedagogico_rodada",
                        max_rounds=rodadas_prd,
                    ),
                ],
            ),
            AnexoAprovadoAgent(
                name="A49cAnexoPedagogico",
                description="Cola no fim do pedagógico os tempos e cenários de aula, o podcast com o roteiro e o contrato de evidência do one-pager aprovado, literais — o texto que o time pedagógico aprova.",
                chave="one_pager_pedagogico",
                secoes=list(SECOES_PEDAGOGICO),
                rotulo="Anexo do pedagógico",
                before_agent_callback=marcar_heranca,
            ),
            # A pergunta do PO, respondida num lugar só: o que o produto especificou chegou ao PRD?
            # Chaves próprias: a do design (A33b) é do semáforo de design, e a matriz final regravava a mesma chave —
            # o 🔴 do PRD e do pedagógico não entrava no semáforo de dev, e o de design mudava depois do de acordo.
            RastreabilidadeAgent(
                name="A50Rastreabilidade",
                description="Matriz de rastreabilidade final: cada requisito do produto em cada artefato de design e de dev, até o PRD e o pedagógico.",
                report_key="rastreabilidade_dev_report",
                status_key="rastreabilidade_dev_status",
                before_agent_callback=marcar_heranca,
            ),
            # O refazer de dev, conferido nos documentos de dev: até 07/10/2026 só o de produto tinha conferência.
            # Sem pedido de refazer de dev, o juiz não roda.
            get_fidelidade_check("A51FidelidadeDev", status_key="fidelidade_dev_status", report_key="fidelidade_dev_report",
                                 documentos=FIDELIDADE_DOCUMENTOS_DEV, onde="fim do dev", etapas_pedido=["dev"],
                                 com_briefing=False, etapa="dev", incluir_corrente=False, **kw),
        ],
    )


#: Onde o pedido de refazer de dev tem de aparecer: o que o dev escreve.
FIDELIDADE_DOCUMENTOS_DEV = ["handoff_dev", "brief_assets", "banco_conteudo", "prd_final", "one_pager_pedagogico"]


DEV_METADATA = [
    {"id": "A33aConteudoAprovadoDev", "name": "33a · Conteúdo aprovado (determinístico)", "icon": "📎", "output_key": "conteudo_aprovado", "prompt_file": None, "description": "As seções do one-pager aprovado, literais — as mesmas do design: núcleo (§1, §3, §4), currículo, falhas, professor, tempos, podcast, evidência, dispositivos e hipóteses —, para o banco de conteúdo, a banca e os agentes de design que ela reaciona."},
    {"id": "A33ManifestoCheck", "name": "33 · Ficha do manifesto (determinístico)", "icon": "🪪", "output_key": "manifesto_report", "prompt_file": None, "description": "Bloco 0 da spec × listas fechadas da plataforma: produto, séries, unidade, público, viewport, permissões, capabilities, seção do DS, liberação por turma. Não conforme impede o PRD."},
    {"id": "A34HandoffDev", "name": "34 · Handoff para dev", "icon": "🤝", "output_key": "handoff_dev", "prompt_file": "dev/34_handoff_dev.md", "description": "Modelo de insumo preenchido, stories com 🔒, eventos, escopo V1/V2, hipóteses (paralelo com V1b)."},
    {"id": "A35BriefAssets", "name": "35 · Brief de assets", "icon": "🎬", "output_key": "brief_assets", "prompt_file": "dev/35_brief_assets.md", "description": "Inventário de assets, spec por tipo, critérios de reprovação, ordem de produção."},
    {"id": "A35bBancoConteudo", "name": "35b · Banco de conteúdo", "icon": "📚", "output_key": "banco_conteudo", "prompt_file": "dev/35b_banco_conteudo.md", "description": "O texto integral de cada item de conteúdo do brief (documentos fictícios, atas, tabelas cujas linhas não entregam a resposta, transcrições, roteiros) e a árvore de falas da IA simulada por estado. Status `escrito` — homologar é da curadoria. Salvo em `dev/01e-banco-conteudo.md`."},
    {"id": "A35cConteudoCheck", "name": "35c · Banco de conteúdo conferido (determinístico)", "icon": "🗂️", "output_key": "conteudo_report", "prompt_file": None, "description": "ID de texto/documento/tabela/roteiro do brief sem bloco no banco bloqueia; Status do brief fora de `a produzir | rascunho | escrito` (\"Homologado\", \"Pronto para corte\") bloqueia; estado de fala da IA sem fala fica 🟡."},
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
    {"id": "A48cConteudoAprovadoPrd", "name": "48c · PRD × one-pager aprovado (determinístico)", "icon": "📎", "output_key": "conteudo_aprovado_prd_report", "prompt_file": None, "description": "As habilidades do bloco 11 na matriz da seção 14, um KPI por habilidade, o tempo em tela do one-pager, o podcast com requisito funcional e só caminhos de artefato que existem na sessão. Divergência volta ao redator."},
    {"id": "A48PrdRodada", "name": "48b · Veredito do PRD (determinístico)", "icon": "🔁", "output_key": "prd_rodada", "prompt_file": None, "description": "PRD consistente encerra o loop; reprovado devolve ao redator com o relatório do gate, até o teto de rodadas."},
    {"id": "A48dAnexoPrd", "name": "48d · Anexo do conteúdo aprovado no PRD (determinístico)", "icon": "📎", "output_key": "prd_final", "prompt_file": None, "description": "Cola no fim do PRD, literais, as seções do one-pager aprovado que o gabarito não tinha onde pôr: currículo, papel do professor, tempos e cenários de aula, podcast com roteiro, contrato de evidência e hipóteses."},
    {"id": "A49OnePagerPedagogico", "name": "49 · One-pager pedagógico (validação humana)", "icon": "🧑‍🏫", "output_key": "one_pager_pedagogico", "prompt_file": "dev/49_one_pager_pedagogico.md", "description": "A missão inteira em linguagem de sala de aula, com o papel do professor, os links do protótipo e as perguntas de aprovação. Salvo em Markdown e `.docx`."},
    {"id": "A49bConteudoAprovadoPedagogico", "name": "49b · Pedagógico × one-pager aprovado (determinístico)", "icon": "📎", "output_key": "conteudo_aprovado_pedagogico_report", "prompt_file": None, "description": "As habilidades do bloco 11, o tempo em tela, o podcast e os caminhos de artefato do pedagógico contra o one-pager aprovado. Divergência volta ao redator."},
    {"id": "A49PedagogicoRodada", "name": "49r · Veredito do pedagógico (determinístico)", "icon": "🔁", "output_key": "pedagogico_rodada", "prompt_file": None, "description": "Pedagógico fiel encerra o loop; divergente volta ao redator com o relatório, até o teto de rodadas."},
    {"id": "A50Rastreabilidade", "name": "50 · Matriz de rastreabilidade (determinístico)", "icon": "🧷", "output_key": "rastreabilidade_dev_report", "prompt_file": None, "description": "Cada requisito do produto procurado em cada artefato de design e de dev, até o PRD e o pedagógico; o que se perdeu sai com o dono."},
    {"id": "A51FidelidadeDev", "name": "51 · Fidelidade ao refazer de dev", "icon": "📌", "output_key": "fidelidade_dev_report", "prompt_file": None, "description": "Cada pedido de refazer feito ao dev (TRAVAS, AJUSTES, VALIDAÇÃO, frases entre aspas) conferido no handoff, no brief, no banco, no PRD e no pedagógico: o juiz cita, o código confere. Sem pedido de dev, não roda. 🔴 recusa o de acordo."},
    {"id": "A49cAnexoPedagogico", "name": "49c · Anexo do conteúdo aprovado no pedagógico (determinístico)", "icon": "📎", "output_key": "one_pager_pedagogico", "prompt_file": None, "description": "Cola no fim do pedagógico, literais, os tempos e cenários de aula, o podcast com o roteiro e o contrato de evidência do one-pager aprovado — o texto que o time pedagógico aprova."},
]
