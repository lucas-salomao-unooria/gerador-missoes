"""Área de DEV — do handoff ao PRD completo, validado pela banca de dev.

Ordem (SequentialAgent):
  v0  A099ManifestoCheck        → manifesto_status  (ficha do manifesto no bloco 0 da spec × listas
                               fechadas da plataforma; não conforme impede o PRD)
  ┌─ ParallelAgent ───────────────────────────────────────────────┐
  │ v1  A100aHandoffDev      → handoff_dev  (insumo + stories +   │
  │                             eventos + escopo V1/V2)            │
  │ v1b A100bBriefAssets     → brief_assets                        │
  └────────────────────────────────────────────────────────────────┘
  v1c A101TelemetriaCheck       → telemetria_status (contrato real de evento, tabela de leitura,
                               sem WebSocket, papéis e quota atuais)
  v1g A101bMontagemHandoff      → montagem_handoff_status (o handoff monta, não decide: número de
                               regra com origem no contrato, hipótese igual à do §17, meta igual à
                               do 9f, estado do contrato — PR 4 do plano «Produto dono do contrato»)
  v1e A104BancoConteudo        → banco_conteudo  (o texto integral de cada item de conteúdo do brief
                               e as falas da IA simulada por estado — `dev/01e-banco-conteudo.md`)
  v1f A105ConteudoCheck        → conteudo_status (determinístico: todo ID de texto do brief tem bloco;
                               Status do brief só `a produzir | rascunho | escrito`; falas por estado)
  v1d A107LacunaCheck           → rastro_lacunas_status (marcadores de lacuna em spec, design,
                               handoff e assets, por dono: input · produto · design · dev ·
                               plataforma — só plataforma não bloqueia, e deixa o PRD 🟡)
  ┌─ ParallelAgent (banca /validar-missao, 5 dimensões) ──────────┐
  │ v2a ValidacaoProdutoNarrativa   → validacao_produto_narrativa │
  │ v2b ValidacaoDesignImersao      → validacao_design_imersao    │
  │ v2c ValidacaoPedagogiaBncc      → validacao_pedagogia_bncc    │
  │ v2d ValidacaoDadosLgpd          → validacao_dados_lgpd        │
  │ v2e ValidacaoTecnicaArquitetura → validacao_tecnica_arquitetura│
  └────────────────────────────────────────────────────────────────┘
  v3  A110ConsolidacaoBanca → validacao_dev_report (veredito 🟢/🟡/🔴)
  v3c A111ValidacaoDevCheck      → dev_status   (🔴 impede o PRD quando ESTEIRA_ESTRITA)
  ┌── PrdLoop (até PRD_MAX_RODADAS) ───────────────────────────────┐
  │ v4  A113PrdWriter         → prd_final ← entregável para o agente │
  │                            de codificação                       │
  │ v4c A114PrdCheck          → prd_status (marcadores que o redator │
  │                            deixou no PRD + consistência interna)│
  │ v4a A116ConteudoAprovadoPrd → conteudo_aprovado_prd_status      │
  │                            (habilidades, KPI por habilidade,    │
  │                            tempo, podcast e caminhos × one-pager)│
  │ v4b A116bMontagemPrd      → montagem_prd_status (o PRD monta,    │
  │                            não decide: números, hipóteses, metas,│
  │                            tetos e estados × contrato)          │
  │ v4r A118PrdRodada         → prd_rodada (reprovado devolve ao     │
  │                            redator com o relatório do gate)     │
  └────────────────────────────────────────────────────────────────┘
  v4d A119AnexoPrd             → prd_final + anexo literal do one-pager aprovado (§2, 9, 10,
                               11, 12, 17): o que nenhum gabarito tinha onde pôr; e, na §19, as
                               pendências de governança da liberação de produto (PR 9, D9)
  v4e A119bPedagogicoNoDev      → pedagogico_pendencias_dev · pedagogico_dev_status (determinístico, PR 10: o
                               one-pager pedagógico fecha o design e é aprovado no de acordo de design; o dev só
                               acrescenta, numa seção própria no fim, as pendências da banca e do rastro de dev, e o
                               texto aprovado que mudou no dev volta ao retrato do design e bloqueia)
"""

from __future__ import annotations

from typing import Optional

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent

from agents.banca import get_banca, pular_se_banca_de_entrada_bloqueou
from agents.juiz import get_fidelidade_check, get_juiz_de_achados, get_juiz_de_contradicoes
from agents.base import create_llm_agent
from agents.callbacks import copiar_textos_chave, desembrulhar_documento, marcar_heranca, registrar_governanca
from agents.pedagogico import PedagogicoNoDevAgent
from agents.checkers import (
    AnexoAprovadoAgent,
    ConsolidacaoBancaAgent,
    ConteudoAprovadoAgent,
    DespachoTicketsAgent,
    EscopoBancaAgent,
    EnvelopeGateAgent,
    RastroCheckAgent,
    SaidaDeLoopAgent,
    RastreabilidadeAgent,
)
from config import get_settings
from prompts import load_prompt
from tools.conteudo_aprovado import SECOES_DEV, SECOES_PRD
from tools.rastro import FONTES_DEV


def get_handoff_dev_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A100aHandoffDev",
        description="Handoff para dev: modelo de insumo preenchido, user stories com 🔒, spec de eventos, escopo V1/V2 e hipóteses.",
        instruction=load_prompt("dev/100a_handoff_dev.md"),
        output_key="handoff_dev",
        before_agent_callback=marcar_heranca,
        # a citação de texto-chave reescrita quase igual volta ao texto aprovado por código (PR 7, D1), e a liberação de
        # produto sem a conta produto entra na seção 7 como pendência de governança (PR 9, D9)
        after_agent_callback=[copiar_textos_chave("handoff_dev"), registrar_governanca("handoff_dev")],
        **kw,
    )


def get_brief_assets_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A100bBriefAssets",
        description="Brief de produção de conteúdo: inventário de assets, spec por tipo, critérios de reprovação e ordem de produção.",
        instruction=load_prompt("dev/100b_brief_assets.md"),
        output_key="brief_assets",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_banco_conteudo_agent(**kw) -> LlmAgent:
    """O texto que o brief de assets só descreve. Na exp09ef1b o banco padrão inteiro (12 PDFs, atas,
    cadernos, a tabela da Linha 302) e quase toda a fala da IA simulada ficaram por escrever, com o
    brief dizendo "Homologado" — e o PRD mandou codificar sobre conteúdo nenhum."""
    return create_llm_agent(
        name="A104BancoConteudo",
        description="Banco de conteúdo: o texto integral de cada documento, tabela, transcrição e roteiro do brief de assets, e a árvore de falas da IA simulada por estado da spec (boas-vindas, fora do tema, aviso de limite).",
        instruction=load_prompt("dev/104_banco_conteudo.md"),
        output_key="banco_conteudo",
        before_agent_callback=marcar_heranca,
        **kw,
    )


#: As dimensões de dev (D e E): produto (A), design (B) e pedagogia (C) rodam no fim das etapas delas e na entrada
#: do dev (`agents/banca.py`).
_VALIDADORES_DEV = [
    ("A109aBancaDadosLgpd", "validacao_dados_lgpd", "dev/109a_validacao_dados_lgpd.md",
     "Dimensão D — Engenharia de dados + DPO: telemetria e LGPD (DAD-01…15)."),
    ("A109bBancaTecnicaArquitetura", "validacao_tecnica_arquitetura", "dev/109b_validacao_tecnica_arquitetura.md",
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
        for name, key, prompt, desc in _VALIDADORES_DEV
    ]


def get_consolidacao_banca_agent(**kw) -> ConsolidacaoBancaAgent:
    """Determinístico desde 23/09/2026 — ver `tools/banca.py` para o porquê."""
    return ConsolidacaoBancaAgent(
        name="A110ConsolidacaoBanca",
        description="Consolida as dimensões de dev da banca (dados e técnica): veredito = o pior delas, com a lista "
                    "de bloqueantes lida dos próprios arquivos de critério.",
        fontes=[key for _, key, _, _ in _VALIDADORES_DEV],
    )


def get_prd_writer_agent(**kw) -> LlmAgent:
    settings = get_settings()
    return create_llm_agent(
        name="A113PrdWriter",
        description="Redige o PRD padrão ouro da missão, com o contexto arquitetural da plataforma, para alimentar um agente de codificação.",
        instruction=load_prompt("dev/113_prd_writer.md"),
        output_key="prd_final",
        model=settings.gemini_model_prd,
        before_agent_callback=marcar_heranca,
        after_agent_callback=[desembrulhar_documento("prd_final"), copiar_textos_chave("prd_final"),
                              registrar_governanca("prd_final")],
        **kw,
    )


#: Slug do envelope da banca → cadeia de agentes que conserta. Desde 08/10/2026 só documento de dev (decisão do
#: usuário): a banca de dev reescrevia jornada, fluxo, telas e copy depois do parecer de design. O design agora é
#: validado no fim da etapa dele, antes do parecer, e de novo na entrada do dev — que bloqueia sem reescrever.
MAPA_BANCA = {
    "handoff-dev": ["A100aHandoffDevRetrabalhoBanca"],
    "brief-assets": ["A100bBriefAssetsRetrabalhoBanca"],
    # PROD-16 confere o banco contra o brief, e o dono não tinha rota: o ticket virava pendência humana
    "banco-conteudo": ["A104BancoConteudoRetrabalhoBanca"],
}

# O banco e o handoff reescritos pela banca passavam sem a conferência que tiveram na primeira passada: o podcast
# do §11 (só o A105 o confere) e o contrato de telemetria (A101). O veredito velho seguia no semáforo de dev.
POSFIXO_BANCA = {
    "banco-conteudo": ["A105ConteudoCheckRetrabalhoBanca"],
    "handoff-dev": ["A101TelemetriaCheckRetrabalhoBanca", "A101bMontagemHandoffRetrabalhoBanca"],
}

#: Ordem entre donos: o banco lê o brief, então conserta depois dele.
ORDEM_BANCA = ["handoff-dev", "brief-assets", "banco-conteudo"]

#: Achado de produto ou de design não se conserta aqui: a etapa dona já deu parecer, e reabri-la invalida o que foi
#: construído sobre ela. Vira pendência nomeada no diagnóstico, para a devolução.
BANCA_EXTERNO = ["gate-estrutural", "spec-missao", "produto", "avaliacao-pedagogica", "experiencia-aluno",
                 "jornada", "fluxo", "copy-ptbr-revisao", "telas", "caa", "prototipo", "brief-oficio",
                 "fecha-lacunas", "ambiente-simulado"]


def _agentes_de_retrabalho_banca(**kw) -> list:
    """Instâncias que a banca de dev aciona: os três autores de dev e as conferências que os seguem."""
    pares = [
        (get_handoff_dev_agent, "A100aHandoffDevRetrabalhoBanca"),
        (get_brief_assets_agent, "A100bBriefAssetsRetrabalhoBanca"),
        (get_banco_conteudo_agent, "A104BancoConteudoRetrabalhoBanca"),
    ]
    agentes = []
    for getter, nome in pares:
        agente = getter(**kw)
        agente.name = nome
        agente.description = f"{agente.description} (acionado pela banca de dev quando o achado é dele)"
        agentes.append(agente)
    estrito = get_settings().esteira_estrita
    agentes += [
        # as conferências de dev que a primeira passada teve, de novo sobre o que a banca reescreveu
        RastroCheckAgent(
            name="A105ConteudoCheckRetrabalhoBanca",
            description="O banco reescrito pela banca, conferido de novo: IDs do brief com bloco, Status do brief, falas por estado e o roteiro do podcast do one-pager.",
            modo="conteudo", rotulo="Banco de conteúdo", report_key="conteudo_report", status_key="conteudo_status",
            agente="conteudo-check", estrito=estrito,
        ),
        RastroCheckAgent(
            name="A101TelemetriaCheckRetrabalhoBanca",
            description="O handoff reescrito pela banca, conferido de novo contra o contrato real de evento e as proibições de arquitetura.",
            modo="telemetria", rotulo="Contrato de telemetria e arquitetura", report_key="telemetria_report",
            status_key="telemetria_status", estrito=estrito,
        ),
        # e contra o contrato de produto: a banca reescreve o handoff, e a hipótese trocada voltava sem conferência
        _montagem_handoff("A101bMontagemHandoffRetrabalhoBanca", estrito,
                          "O handoff reescrito pela banca, conferido de novo contra o contrato de produto: números de "
                          "regra, hipóteses do §17, metas do 9f e estados."),
    ]
    return agentes


#: Rótulos dos gates do PR 4 («PRD e handoff montam, não decidem», `tools/montagem.py`).
ROTULO_MONTAGEM_HANDOFF = "Handoff monta, não decide"
ROTULO_MONTAGEM_PRD = "PRD monta, não decide"


def _montagem_handoff(nome: str, estrito: bool, descricao: str, **kw) -> RastroCheckAgent:
    return RastroCheckAgent(
        name=nome, description=descricao, modo="montagem_handoff", rotulo=ROTULO_MONTAGEM_HANDOFF,
        report_key="montagem_handoff_report", status_key="montagem_handoff_status", agente="montagem-dev",
        estrito=estrito, **kw,
    )


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
        description="Área de Dev: ficha do manifesto → handoff + brief de assets → banco de conteúdo → telemetria e rastro de lacunas → banca de validação (5 dimensões em paralelo) → consolidação → PRD → pendências do PRD → as pendências do dev acrescentadas ao pedagógico aprovado no design.",
        before_agent_callback=marcar_heranca,
        sub_agents=[
            # As mesmas seções do design: até 07/10/2026 esta chave era regravada só com as do PRD, e a banca —
            # e os agentes de design que ela reaciona — perdiam §8, §13 e o núcleo aprovado (§1, §3, §4).
            ConteudoAprovadoAgent(
                name="A095ConteudoAprovadoDev",
                description="Grava as seções do one-pager aprovado, literais — as mesmas do design —, para o banco de conteúdo, a banca e os agentes de design que ela reaciona, que não leem o one-pager.",
                secoes=list(SECOES_DEV),
                chave_base="conteudo_aprovado_base_dev",
                before_agent_callback=marcar_heranca,
            ),
            # Segunda verificação de produto e design, antes de qualquer agente de dev, com a visão cruzada que nenhuma
            # etapa tem sozinha. Não reescreve nada: se bloqueia, o dev não roda (decisão do usuário, 08/10/2026).
            *get_banca("entrada", "ABC", 96, rotulo="Banca de entrada do dev",
                       titulo="Segunda verificação de produto e design (entrada do dev)",
                       report_key="banca_entrada_report", status_key="banca_entrada_status",
                       comparar_com={"produto": "banca_produto_status_envelope", "design": "banca_design_status_envelope"},
                       **kw),
            SequentialAgent(
                name="DevConstrucao",
                description="O dev propriamente dito — handoff, banco, banca de dev e PRD, e as pendências dele no pedagógico —, que só roda quando a banca de entrada libera produto e design.",
                before_agent_callback=pular_se_banca_de_entrada_bloqueou,
                sub_agents=[
                RastroCheckAgent(
                    name="A099ManifestoCheck",
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
                            name="A101TelemetriaCheck",
                            description="Contrato real de evento no handoff (verbo · objeto · resultado · contexto, sem `dados`), tabela de leitura das medidas, sem WebSocket, papéis e quota atuais.",
                            modo="telemetria",
                            rotulo="Contrato de telemetria e arquitetura",
                            report_key="telemetria_report",
                            status_key="telemetria_status",
                            estrito=estrito,
                            before_agent_callback=marcar_heranca,
                        ),
                        get_juiz_de_achados("A102JuizTelemetria", status_key="telemetria_status",
                                            report_key="telemetria_report", fonte_key="handoff_dev",
                                            gate_rotulo="Contrato de telemetria e arquitetura", **kw),
                        # O handoff monta, não decide (PR 4, D10): o da exp02ef1b reescreveu as três hipóteses do §17
                        # (H1 com 25% no lugar de 30%) e o PRD herdou o número trocado.
                        _montagem_handoff(
                            "A101bMontagemHandoff", estrito,
                            "O handoff contra o contrato de produto: número de regra com origem no contrato, hipótese "
                            "igual à do §17, meta igual à do 9f, estado do contrato, texto-chave literal e nenhuma "
                            "decisão de design citada como produto.",
                            before_agent_callback=marcar_heranca),
                        SaidaDeLoopAgent(
                            name="A103HandoffCheck",
                            description="Contrato de telemetria e montagem conformes encerram o loop; reprovado devolve o handoff ao V1 com os relatórios dos gates.",
                            rotulo="Handoff de dev",
                            status_keys=["telemetria_status", "montagem_handoff_status"],
                            rodada_key="handoff_rodada",
                            max_rounds=rodadas_handoff,
                            autor_keys=["handoff_dev", "brief_assets"],
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
                            name="A105ConteudoCheck",
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
                            name="A106BancoRodada",
                            description="Banco conferido encerra o loop; com bloqueio, o banco reescreve com o relatório.",
                            rotulo="Banco de conteúdo",
                            status_keys=["conteudo_status"],
                            rodada_key="banco_rodada",
                            max_rounds=2,
                        ),
                    ],
                ),
                RastroCheckAgent(
                    name="A107LacunaCheck",
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
                        EscopoBancaAgent(name="A108EscopoBancaDev", posicao="dev",
                                         description="Grava o escopo da banca dentro do dev: dados e técnica, conserto só de documento de dev."),
                        ParallelAgent(
                            name="BancaValidacaoDev",
                            description="Banca /validar-missao: cinco dimensões avaliadas em paralelo.",
                            sub_agents=get_validador_agents(**kw),
                            before_agent_callback=marcar_heranca,
                        ),
                        get_consolidacao_banca_agent(**kw),
                        EnvelopeGateAgent(
                            name="A111ValidacaoDevCheck",
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
                            name="A112DespachoBanca",
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
                            name="A114PrdCheck",
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
                            name="A115KpisCheck",
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
                            name="A116ConteudoAprovadoPrd",
                            description="PRD × one-pager aprovado e spec: as habilidades do bloco 11 na matriz da seção 14, um KPI por habilidade, o tempo em tela do §10, o podcast do §11 com requisito, e só caminhos de artefato que a sessão tem.",
                            modo="aprovado_prd",
                            rotulo="PRD × one-pager aprovado",
                            report_key="conteudo_aprovado_prd_report",
                            status_key="conteudo_aprovado_prd_status",
                            agente="conteudo-aprovado",
                            estrito=estrito,
                            before_agent_callback=marcar_heranca,
                        ),
                        # O PRD monta, não decide (PR 4, D10): o juiz abaixo deu 🟢 ao PRD da exp02ef1b com 25% no corpo e
                        # 30% no anexo; o código confere número, hipótese, meta, teto e estado contra o contrato.
                        RastroCheckAgent(
                            name="A116bMontagemPrd",
                            description="O corpo do PRD contra o contrato de produto: número de regra com origem no contrato, hipóteses do §17 e metas do 9f com os números deles, tetos do §15 presentes, estados da §6 iguais aos do contrato e nenhuma decisão de design citada como produto. Divergência do próprio contrato só passa registrada na seção 19 com dono produto.",
                            modo="montagem_prd",
                            rotulo=ROTULO_MONTAGEM_PRD,
                            report_key="montagem_prd_report",
                            status_key="montagem_prd_status",
                            agente="montagem-dev",
                            estrito=estrito,
                            before_agent_callback=marcar_heranca,
                        ),
                        # O corpo do PRD contra o conteúdo aprovado, na mecânica que o código não confere (decisão de 08/10/2026):
                        # o juiz cita os dois lados, o código confere; contradição comprovada volta ao redator.
                        get_juiz_de_contradicoes("A117CoerenciaPrd", documento_key="prd_final", referencia_key="conteudo_aprovado",
                                                 report_key="coerencia_prd_report", status_key="coerencia_prd_status",
                                                 dono="prd-writer", rotulo="Coerência do PRD com o one-pager aprovado", **kw),
                        SaidaDeLoopAgent(
                            name="A118PrdRodada",
                            description="PRD consistente encerra o loop; reprovado devolve ao redator com o relatório do gate.",
                            rotulo="Consistência do PRD",
                            status_keys=["prd_status", "kpis_status", "conteudo_aprovado_prd_status", "montagem_prd_status",
                                         "coerencia_prd_status"],
                            rodada_key="prd_rodada",
                            max_rounds=rodadas_prd,
                            autor_keys=["prd_final"],
                        ),
                    ],
                ),
                # Depois do loop, para os gates lerem só o que o redator escreveu. O PRD das 11 missões do
                # bucket não tinha onde pôr o podcast, os tempos e o contrato de evidência, e os resumia.
                AnexoAprovadoAgent(
                    name="A119AnexoPrd",
                    description="Cola no fim do PRD as seções do one-pager aprovado — currículo, professor, tempos e cenários, podcast, contrato de evidência, hipóteses —, literais.",
                    chave="prd_final",
                    secoes=list(SECOES_PRD),
                    rotulo="Anexo do PRD",
                    before_agent_callback=marcar_heranca,
                ),
                # O pedagógico fecha o design desde o PR 10 (24/10/2026): o dev não o escreve. Só acrescenta as pendências
                # dele numa seção própria no fim, guardada à parte, e confere que o texto aprovado no de acordo de design
                # está como estava — o que mudou volta ao retrato do design e bloqueia.
                PedagogicoNoDevAgent(
                    name="A119bPedagogicoNoDev",
                    description="O pedagógico aprovado no de acordo de design, conferido contra o retrato do design (o que mudou no dev volta a ele e bloqueia), e as pendências da banca de dev e do rastro de lacunas do dev numa seção própria no fim.",
                    estrito=estrito,
                    before_agent_callback=marcar_heranca,
                ),
                # A pergunta do PO, respondida num lugar só: o que o produto especificou chegou ao PRD?
                # Chaves próprias: a do design (A33b) é do semáforo de design, e a matriz final regravava a mesma chave —
                # o 🔴 do PRD e do pedagógico não entrava no semáforo de dev, e o de design mudava depois do de acordo.
                RastreabilidadeAgent(
                    name="A125Rastreabilidade",
                    description="Matriz de rastreabilidade final: cada requisito do produto em cada artefato de design e de dev, até o PRD e o pedagógico.",
                    report_key="rastreabilidade_dev_report",
                    status_key="rastreabilidade_dev_status",
                    colunas_veredito=("handoff", "banco", "prd"),
                    before_agent_callback=marcar_heranca,
                ),
                # O refazer de dev, conferido nos documentos de dev: até 07/10/2026 só o de produto tinha conferência.
                # Sem pedido de refazer de dev, o juiz não roda.
                get_fidelidade_check("A126FidelidadeDev", status_key="fidelidade_dev_status", report_key="fidelidade_dev_report",
                                     documentos=FIDELIDADE_DOCUMENTOS_DEV, onde="fim do dev", etapas_pedido=["dev"],
                                     com_briefing=False, etapa="dev", incluir_corrente=False, **kw),
                ],
            ),
        ],
    )


def agentes_em_ordem(etapa: SequentialAgent) -> list:
    """Os agentes do dev na ordem em que rodam, com o `DevConstrucao` aberto: conteúdo aprovado, banca de entrada e o
    resto do dev, que só roda quando a banca de entrada libera."""
    saida: list = []
    for a in etapa.sub_agents:
        saida += list(a.sub_agents) if a.name == "DevConstrucao" else [a]
    return saida


#: Onde o pedido de refazer de dev tem de aparecer: o que o dev escreve.
#: O pedagógico saiu daqui no PR 10: é documento de design, e o pedido do PO sobre ele vai ao design pela triagem.
FIDELIDADE_DOCUMENTOS_DEV = ["handoff_dev", "brief_assets", "banco_conteudo", "prd_final"]


DEV_METADATA = [
    {"id": "A095ConteudoAprovadoDev", "name": "095 · Conteúdo aprovado (determinístico)", "icon": "📎", "output_key": "conteudo_aprovado", "prompt_file": None, "description": "As seções do one-pager aprovado, literais — as mesmas do design: núcleo (§1, §3, §4), currículo, falhas, professor, tempos, podcast, evidência, dispositivos e hipóteses —, para o banco de conteúdo, a banca e os agentes de design que ela reaciona."},
    {"id": "A096EscopoBanca", "name": "096 · Escopo da banca de entrada do dev (determinístico)", "icon": "🔀", "output_key": None, "prompt_file": None, "description": "Grava o escopo da banca na posição «entrada»."},
    {"id": "A097aBancaProdutoNarrativa", "name": "097a · Banca de entrada: produto e narrativa", "icon": "🅰️", "output_key": "banca_entrada_narrativa", "prompt_file": "dev/validacao_produto_narrativa.md", "description": "Segunda verificação de produto, antes de qualquer agente de dev, com a visão cruzada de produto e design. Não reescreve nada."},
    {"id": "A097bBancaDesignImersao", "name": "097b · Banca de entrada: design e imersão", "icon": "🅱️", "output_key": "banca_entrada_imersao", "prompt_file": "dev/validacao_design_imersao.md", "description": "Segunda verificação de design, com a visão cruzada: cada estado da spec com tela, a conclusão em tela, o professor com as telas dele, os textos aprovados na copy."},
    {"id": "A097cBancaPedagogiaBncc", "name": "097c · Banca de entrada: pedagogia e BNCC", "icon": "🅲", "output_key": "banca_entrada_pedagogia", "prompt_file": "dev/validacao_pedagogia_bncc.md", "description": "Segunda verificação dos critérios PED sobre a spec e o design aprovados."},
    {"id": "A098BancaConsolidacao", "name": "098 · Banca de entrada do dev (determinístico)", "icon": "🚦", "output_key": "banca_entrada_report", "prompt_file": None, "description": "O pior das três dimensões. 🔴 para o dev antes de qualquer agente de dev (BANCA_ENTRADA_ESTRITA) e lista os bloqueios por dono; o que passou na etapa e reprova aqui sai numa seção própria."},
    {"id": "A099ManifestoCheck", "name": "099 · Ficha do manifesto (determinístico)", "icon": "🪪", "output_key": "manifesto_report", "prompt_file": None, "description": "Bloco 0 da spec × listas fechadas da plataforma: produto, séries, unidade, público, viewport, permissões, capabilities, seção do DS, liberação por turma. Não conforme impede o PRD."},
    {"id": "A100aHandoffDev", "name": "100a · Handoff para dev", "icon": "🤝", "output_key": "handoff_dev", "prompt_file": "dev/100a_handoff_dev.md", "description": "Modelo de insumo preenchido, stories com 🔒, eventos, escopo V1/V2, hipóteses (paralelo com V1b)."},
    {"id": "A100bBriefAssets", "name": "100b · Brief de assets", "icon": "🎬", "output_key": "brief_assets", "prompt_file": "dev/100b_brief_assets.md", "description": "Inventário de assets, spec por tipo, critérios de reprovação, ordem de produção."},
    {"id": "A101TelemetriaCheck", "name": "101 · Contrato de telemetria e arquitetura (determinístico)", "icon": "📡", "output_key": "telemetria_report", "prompt_file": None, "description": "Evento = verbo · objeto · resultado · contexto (sem `dados`), medida com tabela de leitura, sem WebSocket, seis papéis, quota em `ia_quotas`."},
    {"id": "A102JuizTelemetria", "name": "102 · Juiz da telemetria", "icon": "⚖️", "output_key": "telemetria_status", "prompt_file": None, "description": "Juiz de achados sobre `Contrato de telemetria e arquitetura`: retira o achado de uso vedado quando o texto só cita para vedar — com citação literal conferida."},
    {"id": "A101bMontagemHandoff", "name": "101b · Handoff monta, não decide (determinístico)", "icon": "🧩", "output_key": "montagem_handoff_report", "prompt_file": None, "description": "O handoff contra o contrato de produto (one-pager, spec de produto, lista branca do bloco 13, decisões do PO): número de regra sem origem, hipótese reescrita do §17, meta fora do 9f, estado inventado, texto-chave reescrito e decisão de design citada como produto voltam ao V1."},
    {"id": "A103HandoffCheck", "name": "103 · Veredito do handoff (determinístico)", "icon": "🔀", "output_key": "handoff_rodada", "prompt_file": None, "description": "Contrato de telemetria e montagem conformes encerram o loop; reprovado devolve o handoff ao V1 com os relatórios."},
    {"id": "A104BancoConteudo", "name": "104 · Banco de conteúdo", "icon": "📚", "output_key": "banco_conteudo", "prompt_file": "dev/104_banco_conteudo.md", "description": "O texto integral de cada item de conteúdo do brief (documentos fictícios, atas, tabelas cujas linhas não entregam a resposta, transcrições, roteiros) e a árvore de falas da IA simulada por estado. Status `escrito` — homologar é da curadoria. Salvo em `dev/01e-banco-conteudo.md`."},
    {"id": "A105ConteudoCheck", "name": "105 · Banco de conteúdo conferido (determinístico)", "icon": "🗂️", "output_key": "conteudo_report", "prompt_file": None, "description": "ID de texto/documento/tabela/roteiro do brief sem bloco no banco bloqueia; Status do brief fora de `a produzir | rascunho | escrito` (\"Homologado\", \"Pronto para corte\") bloqueia; estado de fala da IA sem fala fica 🟡."},
    {"id": "A106BancoRodada", "name": "106 · Saída do loop do banco de conteúdo (determinístico)", "icon": "🔀", "output_key": None, "prompt_file": None, "description": "Banco conferido encerra o loop; com bloqueio, o banco reescreve com o relatório."},
    {"id": "A107LacunaCheck", "name": "107 · Rastro de lacunas (determinístico)", "icon": "🧭", "output_key": "rastro_lacunas_report", "prompt_file": None, "description": "Marcadores de lacuna em spec, design, handoff e assets, por dono: o que faltou de input, produto, design ou dev impede o PRD; plataforma vira pendência humana (🟡)."},
    {"id": "A108EscopoBancaDev", "name": "108 · Escopo da banca de dev (determinístico)", "icon": "🔀", "output_key": None, "prompt_file": None, "description": "Grava o escopo da banca dentro do dev: dados e técnica, conserto só de documento de dev."},
    {"id": "A109aBancaDadosLgpd", "name": "109a · Banca: Dados, Telemetria & LGPD", "icon": "🅳", "output_key": "validacao_dados_lgpd", "prompt_file": "dev/109a_validacao_dados_lgpd.md", "description": "DAD-01…15."},
    {"id": "A109bBancaTecnicaArquitetura", "name": "109b · Banca: Técnica & Arquitetura", "icon": "🅴", "output_key": "validacao_tecnica_arquitetura", "prompt_file": "dev/109b_validacao_tecnica_arquitetura.md", "description": "TEC-01…13."},
    {"id": "A110ConsolidacaoBanca", "name": "110 · Consolidação da banca", "icon": "⚖️", "output_key": "validacao_dev_report", "prompt_file": None, "description": "Determinístico: veredito = a pior das 5 dimensões; bloqueantes lidos de `references/criterios-dev/`."},
    {"id": "A111ValidacaoDevCheck", "name": "111 · Veredito de dev (determinístico)", "icon": "🔀", "output_key": "dev_status", "prompt_file": None, "description": "Lê o envelope da banca."},
    {"id": "A112DespachoBanca", "name": "112 · Retrabalho da banca (determinístico)", "icon": "🔁", "output_key": "reexecucoes", "prompt_file": None, "description": "Reexecuta o dono de cada achado da banca — inclusive quando o dono está na etapa de design. Achado de produto vira pendência nomeada."},
    {"id": "A113PrdWriter", "name": "113 · PRD padrão ouro", "icon": "📘", "output_key": "prd_final", "prompt_file": "dev/113_prd_writer.md", "description": "PRD completo com contexto arquitetural da plataforma — entregável do pipeline."},
    {"id": "A114PrdCheck", "name": "114 · Pendências do PRD (determinístico)", "icon": "🧭", "output_key": "prd_check_report", "prompt_file": None, "description": "Marcadores que o redator deixou no PRD, mais a consistência interna do documento (prefixo de tabela único, requisito P0 com teste e tarefa, evento com tabela leitora, caminho único). lacuna de produto/design/dev marca o PRD como não pronto, plataforma deixa 🟡."},
    # sem esta linha o gate rodava, podia bloquear, e a tela não tinha onde mostrar o relatório (24/09/2026)
    {"id": "A115KpisCheck", "name": "115 · Coerência KPI ↔ evento ↔ tela (determinístico)", "icon": "📈", "output_key": "kpis_report", "prompt_file": None, "description": "Todo KPI com pergunta, decisão, corte e evento que dispara na tela que ele nomeia; os sinais universais das transversais de dono missão na tabela de eventos, com a IA ao estudante decidida pela spec."},
    {"id": "A116ConteudoAprovadoPrd", "name": "116 · PRD × one-pager aprovado (determinístico)", "icon": "📎", "output_key": "conteudo_aprovado_prd_report", "prompt_file": None, "description": "As habilidades do bloco 11 na matriz da seção 14, um KPI por habilidade, o tempo em tela do one-pager, o podcast com requisito funcional e só caminhos de artefato que existem na sessão. Divergência volta ao redator."},
    {"id": "A116bMontagemPrd", "name": "116b · PRD monta, não decide (determinístico)", "icon": "🧩", "output_key": "montagem_prd_report", "prompt_file": None, "description": "O corpo do PRD contra o contrato de produto: número de regra com origem no contrato, hipóteses do §17 e metas do 9f com os números deles, tetos do §15 presentes, estados da §6 iguais aos do contrato, nenhuma decisão de design citada como produto. Divergência do próprio contrato só passa registrada na seção 19 com dono produto."},
    {"id": "A117CoerenciaPrd", "name": "117 · Coerência do PRD com o one-pager aprovado", "icon": "⚖️", "output_key": "coerencia_prd_report", "prompt_file": None, "description": "Um juiz aponta onde o corpo do PRD afirma o contrário do conteúdo aprovado — mecânica, número, regra, texto —, citando os dois lados; o código confere as citações. Contradição comprovada volta ao redator."},
    {"id": "A118PrdRodada", "name": "118 · Veredito do PRD (determinístico)", "icon": "🔁", "output_key": "prd_rodada", "prompt_file": None, "description": "PRD consistente encerra o loop; reprovado devolve ao redator com o relatório do gate, até o teto de rodadas."},
    {"id": "A119AnexoPrd", "name": "119 · Anexo do conteúdo aprovado no PRD (determinístico)", "icon": "📎", "output_key": "prd_final", "prompt_file": None, "description": "Cola no fim do PRD, literais, as seções do one-pager aprovado que o gabarito não tinha onde pôr: currículo, papel do professor, tempos e cenários de aula, podcast com roteiro, contrato de evidência e hipóteses. E põe na seção 19, por código, as pendências de governança da liberação de produto — liberado sem a conta produto, exceção do admin com gate vermelho — como estão agora, também na correção pontual."},
    {"id": "A119bPedagogicoNoDev", "name": "119b · Pedagógico aprovado, no dev (determinístico)", "icon": "🔏", "output_key": "pedagogico_dev_report", "prompt_file": None, "description": "O one-pager pedagógico fecha o design desde o PR 10 e é aprovado no de acordo de design: o dev não o escreve. Confere o texto contra o retrato do design (o que mudou no dev volta a ele e bloqueia) e acrescenta, numa seção própria no fim, as pendências da banca de dev e do rastro de lacunas do dev, com o dono de cada uma."},
    {"id": "A125Rastreabilidade", "name": "125 · Matriz de rastreabilidade (determinístico)", "icon": "🧷", "output_key": "rastreabilidade_dev_report", "prompt_file": None, "description": "Cada requisito do produto procurado em cada artefato de design e de dev, até o PRD e o pedagógico; o que se perdeu sai com o dono."},
    {"id": "A126FidelidadeDev", "name": "126 · Fidelidade ao refazer de dev", "icon": "📌", "output_key": "fidelidade_dev_report", "prompt_file": None, "description": "Cada pedido de refazer feito ao dev (TRAVAS, AJUSTES, VALIDAÇÃO, frases entre aspas) conferido no handoff, no brief, no banco e no PRD (o pedagógico é do design desde o PR 10): o juiz cita, o código confere. Sem pedido de dev, não roda. 🔴 recusa o de acordo."},
]
