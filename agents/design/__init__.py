"""Área de DESIGN — da spec aprovada aos wireframes lo-fi auditados.

Ordem (SequentialAgent). O MCP do Figma foi removido — não há cliente oficial que o sirva
aqui, e board em ferramenta que ninguém abre não é entregável. A jornada e o fluxo saem em
Mermaid (remontados em `design/09-diagramas.html`), as telas saem no Stitch, e o protótipo
HTML é o que a revisão humana de fato abre.
  d0  A17FechaLacunas       → fechamento_lacunas   (varredura, decisões [D0-n], re-specs [RS-n])
  d0c A18FechaLacunasSplit       → spec_missao (consolidada, bloco 13) · spec_missao_gate0 (cópia
                                 da original) · relatorio_lacunas · lacunas_status
  d9  A19AmbienteSimulado    → ambiente_simulado   (condicional: decide o ambiente quando a
                                 spec cala; dormente emite só a ficha do bloco 14)
  d9c A20AmbienteSimuladoSplit   → spec_missao (com bloco 14) · ambiente_status
  d1  A21BriefOficio        → brief_oficio
  d2  A22Jornada      → jornada_telas   (mapa de jornada + inventário + direção)
  d3  A23Fluxo        → fluxo_arestas   (grafo de telas + 5 testes)
  d4  A24CopyPtBr           → copy_strings    (passada 1)
  d4b A25Caa                → camada_caa      (camada CAA; ele mesmo decide se roda)
  d5  A26Telas    → wireframes_cobertura
  d6  A27CopyRevisao        → copy_strings_revisada (passada 2)
  d8  A28Prototipo          → prototipo_html  (protótipo navegável)
  d8c A29ArtefatosDesign         → prototipo_arquivo (.html) · prototipo_relatorio · stitch_links
                                 · diagramas_html — determinístico, o HTML nunca entra em prompt
  d8e A29dConsistencia           → consistencia_status (determinístico: jornada, fluxo, copy e
                                 protótipo contra o glossário canônico da spec)
  d8f A29eCoberturaTelas         → cobertura_telas_status (determinístico: toda tela do inventário
                                 da jornada no fluxo, na copy, na cobertura e no protótipo, por ID)
  d7  A30QaEntregaveis      → qa_entregaveis_report (gate de design)
  d7b A30bQaAfirmacoes          → qa_afirmacoes_status (determinístico: contagens de telas e nomes de
                                 arquivo do QA contra o real; divergência reescreve o QA como bloqueado)
  d7c A31QaEntregaveisCheck      → design_status (🔴 impede dev e PRD quando ESTEIRA_ESTRITA)
  d7d A33RastroDesign            → rastro_design_status (determinístico: lacuna de design na spec e
                                 nos documentos de design, cobrada onde o designer ainda refaz)

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
from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.sequential_agent import SequentialAgent

from agents.base import create_llm_agent
from agents.callbacks import marcar_heranca
from agents.banca import get_banca
from agents.juiz import get_fidelidade_check
from agents.checkers import (
    ArtefatosDesignAgent,
    CoberturaTelasAgent,
    CopyPreservadaAgent,
    RastreabilidadeAgent,
    StitchGeracaoAgent,
    ConteudoAprovadoAgent,
    PrototipoLintAgent,
    DespachoTicketsAgent,
    QaAfirmacoesAgent,
    EnvelopeGateAgent,
    EspelhoMiroAgent,
    RastroCheckAgent,
    SecaoSplitAgent,
)
from config import get_settings
from prompts import load_prompt
from tools.conteudo_aprovado import SECOES_DESIGN
from tools.rastro import FONTES_DESIGN
from tools.stitch_mcp import STITCH_TOOLS_QA, stitch_tools_or_empty

# Headings que D0 e D9 usam na "Saída obrigatória" dos seus prompts. Os regex são tolerantes
# ao travessão/hífen e ao texto depois do número, mas dependem do número do passo.
_H = r"^#{2,3}\s*"
D0_SPEC_INICIO = _H + r"Passo 5\b.*$"        # "## Passo 5 — Spec consolidada (...)"  (5\b não casa "5b")
D0_SPEC_FIM = _H + r"Passo 5b\b.*$"          # "## Passo 5b — Relatório de preenchimento ..."
D0_RELATORIO_FIM = _H + r"Passo 6\b.*$"      # "## Passo 6 — Devolutiva ao produto"
D9_SPEC_INICIO = _H + r"Passo 4\b.*$"        # "## Passo 4 — Spec consolidada (blocos 1–13 ... + bloco 14)"
D9_SPEC_FIM = _H + r"Bloco 14\b.*$"          # "## Bloco 14 — Ficha do ambiente"
SPEC_MINIMO_CHARS = 1500


def _stitch_vars() -> dict:
    s = get_settings()
    return {
        "stitch_mcp_mode": s.stitch_mcp_mode,
        "stitch_project_url_base": s.stitch_project_url_base,
    }


def get_fecha_lacunas_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A17FechaLacunas",
        description="Fechamento de lacunas da spec antes do design: varredura célula a célula, decisões [D0-n] com base declarada, pedidos de re-spec [RS-n] e spec consolidada com bloco 13.",
        instruction=load_prompt("design/17_fechamento_lacunas.md"),
        output_key="fechamento_lacunas",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_fecha_lacunas_split() -> SecaoSplitAgent:
    return SecaoSplitAgent(
        name="A18FechaLacunasSplit",
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
                "minimo_fracao": 0.8,
                "backup": "spec_missao_gate0",
                # o que o Gate 0 escreveu não some na consolidação (exp06ef1b perdeu a pergunta 3 do debate)
                "preservar": "fecha-lacunas",
                # entre execuções de refazer, a consolidação não muda sem motivo (exp06ef1b traduziu o próprio texto)
                "estavel_contra": "fechamento_lacunas",
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
        name="A19AmbienteSimulado",
        description="Ambiente simulado (condicional): decide em que casca a missão acontece quando a spec cala — app clonado da lista fechada, app novo ou mini-jogo em anos iniciais — e emite a ficha do bloco 14 mesmo quando dormente.",
        instruction=load_prompt("design/19_ambiente_simulado.md"),
        output_key="ambiente_simulado",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_spec_consolidada_check(nome: str) -> RastroCheckAgent:
    """A spec que o D0 e o D9 reescreveram, conferida de novo contra o one-pager aprovado (o que eles pioraram).

    O conserto vai ao dono do D0 pelo QA (A30b). Até 07/10/2026 essa conferência só rodava em produto, e o
    `bncc_status` e o `conteudo_aprovado_spec_status` ficavam verdes sobre uma spec que o design tinha trocado."""
    return RastroCheckAgent(
        name=nome,
        description="Spec consolidada pelo D0 e pelo D9 × one-pager aprovado: habilidades, tempo em tela, podcast, Canal B, debate e parâmetros a definir — só o que piorou desde a spec do Gate 0.",
        modo="aprovado_spec_design",
        rotulo="Spec consolidada × one-pager aprovado",
        report_key="conteudo_aprovado_spec_design_report",
        status_key="conteudo_aprovado_spec_design_status",
        agente="conteudo-aprovado",
        estrito=get_settings().esteira_estrita,
        before_agent_callback=marcar_heranca,
    )


def get_ambiente_simulado_split() -> SecaoSplitAgent:
    return SecaoSplitAgent(
        name="A20AmbienteSimuladoSplit",
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
                "minimo_fracao": 0.8,
                "preservar": "ambiente-simulado",
                # blocos 0–13 copiados da spec aceita pelo código; do D9 só entra o bloco 14
                "bloco_proprio": r"^##\s*14\b.*$",
            },
        ],
    )


def get_brief_oficio_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A21BriefOficio",
        description="Briefing de ofício: aposta, forma do arco, pico, beat memorável, mapa de beats e não-negociáveis.",
        instruction=load_prompt("design/21_brief_oficio.md"),
        output_key="brief_oficio",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_jornada_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A22Jornada",
        description="Mapa de jornada em Mermaid (raias × 6 etapas), cenários de dispositivo, inventário de telas e direção por tela.",
        instruction=load_prompt("design/22_jornada.md"),
        output_key="jornada_telas",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_fluxo_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A23Fluxo",
        description="Grafo de fluxo de telas em Mermaid: transições com condição, gates, estados de erro e os 5 testes.",
        instruction=load_prompt("design/23_fluxo.md"),
        output_key="fluxo_arestas",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_copy_ptbr_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A24CopyPtBr",
        description="Copy PT-BR passada 1: sheet de strings por tela, calibrado à faixa etária.",
        instruction=load_prompt("design/24_copy_ptbr.md"),
        output_key="copy_strings",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_caa_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A25Caa",
        description="Camada CAA: símbolos, modos de resposta alternativos e pranchas para quem não lê ou não fala. Aplica o gate de aplicabilidade e devolve `nao_aplicavel` quando a missão não justifica.",
        instruction=load_prompt("design/25_caa.md"),
        output_key="camada_caa",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_wireframes_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A26Telas",
        description="Wireframes lo-fi em escala de cinza no Stitch, montados sobre a seção do DS do ambiente simulado.",
        instruction=load_prompt("design/26_telas.md", **_stitch_vars()),
        output_key="wireframes_cobertura",
        # Sem ferramentas do Stitch desde 07/10/2026: o agente especifica (a tabela «Geração no Stitch») e o
        # `StitchGeracaoAgent` gera todas as telas fora do modelo — sem priorizar, sem teto, sem id inventado.
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_copy_revisao_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A27CopyRevisao",
        description="Copy PT-BR passada 2: revisão de cada string dentro da tela construída.",
        instruction=load_prompt("design/27_copy_revisao.md"),
        output_key="copy_strings_revisada",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_prototipo_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A28Prototipo",
        description="Protótipo HTML lo-fi navegável: arquivo único, sem dependências, que a revisão humana abre no navegador e o agente de codificação lê como referência de layout.",
        instruction=load_prompt("design/28_prototipo.md"),
        output_key="prototipo_html",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_qa_entregaveis_agent(max_rodadas: Optional[int] = None, **kw) -> LlmAgent:
    # O teto vive no código; o prompt precisa saber dele para não prometer uma rodada de
    # retrabalho que o LoopAgent nunca vai executar (mesmo motivo do gate estrutural).
    rodadas = max_rodadas or get_settings().qa_design_max_rodadas
    return create_llm_agent(
        name="A30QaEntregaveis",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Gate final de design: fidelidade à spec, diff de strings, currículo, faixa etária, fluxo, professor, briefing, ambiente simulado e CAA.",
        instruction=load_prompt(
            "design/30_qa_entregaveis.md",
            qa_max_rodadas=rodadas,
            **_stitch_vars(),
        ),
        output_key="qa_entregaveis_report",
        tools=stitch_tools_or_empty(STITCH_TOOLS_QA),
        before_agent_callback=marcar_heranca,
        **kw,
    )


#: Ordem em que dois donos de ticket se resolvem. Está escrita no prompt do D7
#: ("ambiente antes de jornada · jornada antes de fluxo · fluxo antes de wireframe ·
#: CAA antes de wireframe · wireframe antes da revisão da copy") — aqui ela vira execução.
#: A revisão da copy (passada 2) lê as telas: rodando antes delas, a correção de uma tela não
#: chegava ao texto revisado (auditoria de 07/10/2026).
ORDEM_RETRABALHO = [
    "fecha-lacunas",
    "ambiente-simulado",
    "brief-oficio",  # a jornada deriva os tiers do mapa de beats: o brief conserta primeiro
    "jornada",
    "fluxo",
    "caa",
    "telas",
    "copy-ptbr-revisao",
    "prototipo",
]

#: Slug do envelope → cadeia de agentes que o conserto exige, em ordem.
#: D0 e D9 emitem dois documentos numa resposta só: sem o split logo atrás, a correção
#: fica presa no relatório e nunca chega à `spec_missao` que o resto da esteira lê.
MAPA_RETRABALHO = {
    "fecha-lacunas": ["A17FechaLacunasRetrabalho", "A18FechaLacunasSplitRetrabalho", "A20bSpecConsolidadaRetrabalho"],
    "ambiente-simulado": ["A19AmbienteSimuladoRetrabalho", "A20AmbienteSimuladoSplitRetrabalho",
                          "A20bSpecConsolidadaRetrabalho"],
    # A D7 do QA manda "não-negociável sem marca é ticket com dono `brief-oficio`", e até
    # 23/09/2026 esse dono não tinha rota: o ticket era descartado em silêncio.
    "brief-oficio": ["A21BriefOficioRetrabalho"],
    "jornada": ["A22JornadaRetrabalho"],
    "fluxo": ["A23FluxoRetrabalho"],
    "copy-ptbr-revisao": ["A27CopyRevisaoRetrabalho", "A27bCopyPreservadaRetrabalho"],
    "caa": ["A25CaaRetrabalho"],
    "telas": ["A26TelasRetrabalho", "A26bStitchGeracaoRetrabalho"],
    # o protótipo tinha dono no QA e nenhuma rota: o ticket ia para "sem rota" (auditoria 07/10/2026)
    "prototipo": ["A28PrototipoRetrabalho"],
}

#: Roda depois de qualquer retrabalho. O protótipo deriva de jornada, copy, CAA e telas —
#: deixá-lo de fora faria o QA auditar, na rodada seguinte, um protótipo da rodada anterior.
#: O lint vem DEPOIS de separar o HTML e ANTES do QA voltar a julgar. Sem ele no posfixo, o
#: protótipo era reconstruído e o QA da rodada 2 lia o lint da rodada 1 — sobre o HTML velho —
#: com a instrução de tratá-lo como fato. Visto na auditoria de 23/09/2026.
POSFIXO_RETRABALHO = ["A28PrototipoRetrabalho", "A29ArtefatosDesignRetrabalho",
                      "A29cPrototipoLintRetrabalho", "A29dConsistenciaRetrabalho",
                      "A29eCoberturaTelasRetrabalho", "A29bEspelhoMiroRetrabalho"]

#: Tickets endereçados a estes donos não são desta etapa: o QA está devolvendo ao produto.
RETRABALHO_EXTERNO = ["gate-estrutural"]


def _agentes_de_retrabalho(**kw) -> list:
    """Instâncias dedicadas ao retrabalho: mesmo prompt e mesmo `output_key`, nome próprio.

    Precisam ser instâncias novas porque um agente do ADK tem um único pai na árvore;
    o nome com sufixo mantém a árvore válida e deixa o retrabalho visível no log.
    """
    pares = [
        (get_fecha_lacunas_agent, "A17FechaLacunasRetrabalho"),
        (get_ambiente_simulado_agent, "A19AmbienteSimuladoRetrabalho"),
        (get_brief_oficio_agent, "A21BriefOficioRetrabalho"),
        (get_jornada_agent, "A22JornadaRetrabalho"),
        (get_fluxo_agent, "A23FluxoRetrabalho"),
        (get_copy_revisao_agent, "A27CopyRevisaoRetrabalho"),
        (get_caa_agent, "A25CaaRetrabalho"),
        (get_wireframes_agent, "A26TelasRetrabalho"),
        (get_prototipo_agent, "A28PrototipoRetrabalho"),
    ]
    agentes = []
    for getter, nome in pares:
        agente = getter(**kw)
        agente.name = nome
        agente.description = f"{agente.description} (rodada de retrabalho: só roda com ticket do QA)"
        agentes.append(agente)

    # Determinísticos: sem eles a correção do D0/D9 não vira `spec_missao` e o HTML do
    # protótipo não é separado do relatório que o acompanha.
    split_lacunas = get_fecha_lacunas_split()
    split_lacunas.name = "A18FechaLacunasSplitRetrabalho"
    split_ambiente = get_ambiente_simulado_split()
    split_ambiente.name = "A20AmbienteSimuladoSplitRetrabalho"
    agentes += [
        split_lacunas,
        split_ambiente,
        get_spec_consolidada_check("A20bSpecConsolidadaRetrabalho"),
        StitchGeracaoAgent(name="A26bStitchGeracaoRetrabalho",
                           description="Gera no mesmo projeto do Stitch só o que o retrabalho das telas mudou ou ainda falta."),
        CopyPreservadaAgent(name="A27bCopyPreservadaRetrabalho"),
        ArtefatosDesignAgent(
            name="A29ArtefatosDesignRetrabalho",
            description="Reextrai o HTML do protótipo, os links do Stitch e a folha de diagramas depois de uma rodada de retrabalho.",
        ),
        PrototipoLintAgent(name="A29cPrototipoLintRetrabalho"),
        get_consistencia_check("A29dConsistenciaRetrabalho"),
        CoberturaTelasAgent(name="A29eCoberturaTelasRetrabalho",
                            description="Reconfere, por ID, toda tela do inventário em todo derivado depois do retrabalho."),
        EspelhoMiroAgent(
            name="A29bEspelhoMiroRetrabalho",
            description="Reenvia ao mesmo board do Miro os diagramas corrigidos na rodada de retrabalho.",
        ),
    ]
    return agentes


def get_consistencia_check(nome: str = "A29dConsistencia") -> RastroCheckAgent:
    """Jornada, fluxo, copy revisada e protótipo contra o `## Glossário canônico` da spec.

    Na exp09ef1b o órgão teve quatro nomes, os beneficiários de 14 anos viraram coordenadores na copy
    e seis ações tinham dois rótulos de botão. Nenhum documento estava errado sozinho; ninguém lia os
    quatro juntos. Variante proibida em tela bloqueia; o resto é atenção para o QA ler como fato.
    """
    return RastroCheckAgent(
        name=nome,
        description="Coerência entre documentos: nomes de entidade, papel e idade de personagem, números com unidade, "
                    "rótulos de botão e nomes de arquivo da jornada, do fluxo, da copy e do protótipo contra o glossário "
                    "canônico da spec. Variante proibida bloqueia.",
        modo="consistencia",
        rotulo="Coerência entre documentos",
        report_key="consistencia_report",
        status_key="consistencia_status",
        agente="consistencia-check",
        estrito=get_settings().esteira_estrita,
        before_agent_callback=marcar_heranca,
    )


def build_qa_design_loop(**kw) -> LoopAgent:
    """QA de entregáveis ↔ retrabalho dos agentes endereçados, até aprovar ou esgotar.

    O prompt do D7 sempre presumiu este ciclo — numera "rodada 1", endereça cada
    ticket a um dono e declara a ordem entre donos. Sem o loop, o veredito 🔴
    RETRABALHO não tinha para onde ir: o gate bloqueava e a missão parava, mesmo
    quando o conserto era uma string ou uma aresta de fluxo.
    """
    rodadas = max(1, get_settings().qa_design_max_rodadas)
    return LoopAgent(
        name="QaDesignLoop",
        description="QA de entregáveis ↔ retrabalho seletivo dos agentes com ticket, até aprovar ou esgotar as rodadas.",
        max_iterations=rodadas,
        before_agent_callback=marcar_heranca,
        sub_agents=[
            # A banca no fim de design (o que de produto se realiza em tela, e design e imersão), antes do parecer:
            # o bloqueio dela vira ticket pelo A30b, e o dono refaz nesta etapa. Até 08/10/2026 ela só rodava no
            # dev, que reescrevia o design depois do parecer (decisão do usuário).
            *get_banca("design", "AB", "A29f", rotulo="Banca de design", titulo="Banca de validação — fim de design",
                       report_key="banca_design_report", status_key="banca_design_status", **kw),
            get_qa_entregaveis_agent(max_rodadas=rodadas, **kw),
            # Entre o QA e o veredito: contagem de telas e nome de arquivo que o QA escreveu são
            # conferidos em código; divergência reescreve o envelope como bloqueado (exp09ef1b).
            QaAfirmacoesAgent(
                name="A30bQaAfirmacoes",
                description="Confere as contagens de telas e os nomes de arquivo que o QA afirma contra o inventário da jornada, o projeto no Stitch, o protótipo e os arquivos que a esteira grava; divergência, ou Stitch com menos telas que o inventário, reprova a rodada do QA com ticket.",
                before_agent_callback=marcar_heranca,
            ),
            EnvelopeGateAgent(
                name="A31QaEntregaveisCheck",
                documentos=["spec_missao", "jornada_telas", "fluxo_arestas", "copy_strings_revisada", "camada_caa", "wireframes_cobertura", "prototipo_arquivo", "prototipo_relatorio", "stitch_links", "ambiente_simulado", "brief_oficio"],  # citação dos bloqueios conferida em código (`tools/citacoes.py`)
                description="Lê o veredito do QA de entregáveis: aprovado encerra o loop; 🔴 na última rodada impede o dev e o PRD (modo estrito).",
                rotulo="QA de entregáveis (design)",
                report_key="qa_entregaveis_report",
                status_key="design_status",
                round_key="qa_design_rodada",
                max_rounds=rodadas,
                escalate_on_approve=True,
                block_pipeline_on_fail=get_settings().esteira_estrita,
                before_agent_callback=marcar_heranca,
            ),
            DespachoTicketsAgent(
                name="A32DespachoDesign",
                description="Lê os tickets do QA e reexecuta apenas os agentes endereçados, na ordem de precedência do prompt.",
                rotulo="Retrabalho de design",
                report_key="qa_entregaveis_report",
                mapa=MAPA_RETRABALHO,
                ordem=ORDEM_RETRABALHO,
                externos=RETRABALHO_EXTERNO,
                posfixo=POSFIXO_RETRABALHO,
                before_agent_callback=marcar_heranca,
                sub_agents=_agentes_de_retrabalho(**kw),
            ),
        ],
    )


def build_design_stage(
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
) -> SequentialAgent:
    kw = {"thinking_budget": thinking_budget, "include_thoughts": include_thoughts}
    return SequentialAgent(
        name="DesignStage",
        description="Área de Design: fechamento de lacunas → ambiente simulado → briefing de ofício → jornada e fluxo → copy → camada CAA → wireframes (Stitch) → protótipo navegável → QA de entregáveis.",
        before_agent_callback=marcar_heranca,
        sub_agents=[
            ConteudoAprovadoAgent(
                name="A16dConteudoAprovadoDesign",
                description="Grava as seções do one-pager aprovado, literais — o núcleo (§1, §3, §4) inclusive —, para os agentes de design que não leem o one-pager (fluxo, CAA, telas, revisão da copy, QA).",
                secoes=list(SECOES_DESIGN),
                chave_base="conteudo_aprovado_base_design",
                before_agent_callback=marcar_heranca,
            ),
            get_fecha_lacunas_agent(**kw),
            get_fecha_lacunas_split(),
            get_ambiente_simulado_agent(**kw),
            get_ambiente_simulado_split(),
            get_spec_consolidada_check("A20bSpecConsolidada"),
            get_brief_oficio_agent(**kw),
            get_jornada_agent(**kw),
            get_fluxo_agent(**kw),
            get_copy_ptbr_agent(**kw),
            get_caa_agent(**kw),
            get_wireframes_agent(**kw),
            # Toda (tela, estado) no Stitch, gerada pelo código com o screenId que o Stitch devolve.
            StitchGeracaoAgent(
                name="A26bStitchGeracao",
                description="Gera no Stitch, fora do modelo, cada linha da tabela «Geração no Stitch» e cada (tela, estado) do inventário que ela esqueceu; registra o screenId real.",
                before_agent_callback=marcar_heranca,
            ),
            get_copy_revisao_agent(**kw),
            # A revisão descartava prompts, banco curado e podcast em 8 de 8 sessões, com o prompt mandando
            # manter: copiar sem mudança é trabalho do código (auditoria de 07/10/2026).
            CopyPreservadaAgent(name="A27bCopyPreservada", before_agent_callback=marcar_heranca),
            get_prototipo_agent(**kw),
            ArtefatosDesignAgent(
                name="A29ArtefatosDesign",
                description="Separa o HTML do protótipo do relatório que o acompanha, colhe os links das telas no Stitch e monta a folha de diagramas da jornada e do fluxo.",
                before_agent_callback=marcar_heranca,
            ),
            # O QA lia o RELATÓRIO de quem construiu o protótipo, nunca o arquivo: metade das
            # telas, um `TODO` na tela de pico ou um HTML que nem abre passavam se o relatório
            # dissesse que estava pronto. Este lint toca o arquivo e alimenta o QA.
            PrototipoLintAgent(name="A29cPrototipoLint"),
            # Os nomes, papéis, números e rótulos contra o glossário da spec. Antes do QA, que lê o
            # relatório como fato e endereça o conserto ao dono de cada documento.
            get_consistencia_check("A29dConsistencia"),
            # Toda tela do inventário em todo derivado, por ID: o Stitch tinha 27% a 68% das telas e o
            # protótipo um quadro por tela, e os gates aprovavam por contagem (auditoria 07/10/2026).
            CoberturaTelasAgent(
                name="A29eCoberturaTelas",
                description="Confere, por ID, toda tela do inventário da jornada no fluxo, na copy revisada, na cobertura dos wireframes e nos quadros do protótipo; falta vira ticket com o dono.",
                before_agent_callback=marcar_heranca,
            ),
            EspelhoMiroAgent(
                name="A29bEspelhoMiro",
                description="Espelha no Miro os diagramas Mermaid da jornada e do fluxo e devolve o link do board.",
                before_agent_callback=marcar_heranca,
            ),
            build_qa_design_loop(**kw),
            # A lacuna de design só era cobrada em dev, que não reescreve documento de design.
            # Cobrada aqui, ela aparece no parecer de design, onde o designer ainda pode refazer.
            RastroCheckAgent(
                name="A33RastroDesign",
                description="Marcadores de lacuna na spec consolidada e nos documentos de design: o de design bloqueia; o que o D0 fechou (`Resolvido em [D0-n]`) não conta; o de produto já aprovado e o de dev ficam 🟡.",
                modo="lacunas",
                rotulo="Rastro de lacunas do design",
                report_key="rastro_design_report",
                status_key="rastro_design_status",
                fontes=FONTES_DESIGN,
                etapa="design",
                agente="rastro-lacunas-design",
                estrito=get_settings().esteira_estrita,
                before_agent_callback=marcar_heranca,
            ),
            # O que o produto especificou, requisito por requisito, em cada artefato de design (auditoria 07/10/2026).
            RastreabilidadeAgent(
                name="A33bRastreabilidadeDesign",
                description="Matriz de rastreabilidade: cada requisito do one-pager e da spec (habilidades, textos literais, tempo, telas, estados, seção do DS) procurado em cada artefato de design.",
                before_agent_callback=marcar_heranca,
            ),
            # O refazer de design, conferido nos documentos de design: até 07/10/2026 só o de produto tinha
            # conferência. Sem pedido de refazer de design, o juiz não roda.
            get_fidelidade_check("A33cFidelidadeDesign", status_key="fidelidade_design_status",
                                 report_key="fidelidade_design_report", documentos=FIDELIDADE_DOCUMENTOS_DESIGN,
                                 onde="fim do design", etapas_pedido=["design"], com_briefing=False, etapa="design",
                                 incluir_corrente=False, **kw),
        ],
    )


#: Onde o pedido de refazer de design tem de aparecer: o que o design escreve, e a spec que o D0 e o D9 consolidam.
FIDELIDADE_DOCUMENTOS_DESIGN = ["spec_missao", "brief_oficio", "jornada_telas", "fluxo_arestas", "copy_strings_revisada",
                                "camada_caa", "wireframes_cobertura"]


DESIGN_METADATA = [
    {"id": "A16dConteudoAprovadoDesign", "name": "16d · Conteúdo aprovado (determinístico)", "icon": "📎", "output_key": "conteudo_aprovado", "prompt_file": None, "description": "As seções do one-pager aprovado — o núcleo (descoberta, narrativa e as 6 etapas com o texto de tela), currículo, falhas, professor, tempos e cenários, podcast, contrato de evidência, dispositivos, hipóteses —, literais, para os agentes de design que não leem o one-pager."},
    {"id": "A17FechaLacunas", "name": "17 · Fechamento de lacunas", "icon": "🧩", "output_key": "fechamento_lacunas", "prompt_file": "design/17_fechamento_lacunas.md", "description": "Varredura da spec célula a célula, decisões [D0-n] com base declarada, pedidos de re-spec [RS-n], spec consolidada (bloco 13) e relatório de preenchimento."},
    {"id": "A18FechaLacunasSplit", "name": "18 · Relatório de lacunas + spec consolidada (determinístico)", "icon": "✂️", "output_key": "relatorio_lacunas", "prompt_file": None, "description": "Copia a spec consolidada para `spec_missao` (original preservada em `spec_missao_gate0`), separa o relatório e registra `lacunas_status`."},
    {"id": "A19AmbienteSimulado", "name": "19 · Ambiente simulado", "icon": "🏝️", "output_key": "ambiente_simulado", "prompt_file": "design/19_ambiente_simulado.md", "description": "Condicional: decide o ambiente (app clonado existente, app novo ou mini-jogo) quando a spec cala; dormente emite só a ficha do bloco 14 que D1, D2, D4, D5 e o QA consomem."},
    {"id": "A20AmbienteSimuladoSplit", "name": "20 · Spec com bloco 14 (determinístico)", "icon": "✂️", "output_key": "ambiente_status", "prompt_file": None, "description": "Copia a spec com o bloco 14 para `spec_missao` e registra `ambiente_status`."},
    {"id": "A20bSpecConsolidada", "name": "20b · Spec consolidada × one-pager aprovado (determinístico)", "icon": "📎", "output_key": "conteudo_aprovado_spec_design_report", "prompt_file": None, "description": "A spec que o D0 e o D9 reescreveram, contra o one-pager aprovado: habilidades, tempo em tela, podcast, Canal B, debate e parâmetros a definir. Só o que piorou desde a spec do Gate 0; o conserto vai ao D0 pelo QA."},
    {"id": "A21BriefOficio", "name": "21 · Briefing de ofício", "icon": "🎯", "output_key": "brief_oficio", "prompt_file": "design/21_brief_oficio.md", "description": "Aposta, forma do arco, pico, beat memorável, mapa de beats, não-negociáveis."},
    {"id": "A22Jornada", "name": "22 · Jornada (Mermaid)", "icon": "🗺️", "output_key": "jornada_telas", "prompt_file": "design/22_jornada.md", "description": "Raias × 6 etapas, cenários de dispositivo, inventário de telas e direção por tela."},
    {"id": "A23Fluxo", "name": "23 · Fluxo de telas (Mermaid)", "icon": "🕸️", "output_key": "fluxo_arestas", "prompt_file": "design/23_fluxo.md", "description": "Grafo de telas com condições, gates e os 5 testes de fluxo."},
    {"id": "A24CopyPtBr", "name": "24 · Copy PT-BR (passada 1)", "icon": "✍️", "output_key": "copy_strings", "prompt_file": "design/24_copy_ptbr.md", "description": "Sheet de strings por tela, calibrado à faixa etária."},
    {"id": "A25Caa", "name": "25 · Camada CAA", "icon": "🔣", "output_key": "camada_caa", "prompt_file": "design/25_caa.md", "description": "Símbolos, modos de resposta alternativos e pranchas; só roda quando a faixa ou a spec pedem."},
    {"id": "A26Telas", "name": "26 · Wireframes lo-fi (Stitch)", "icon": "📐", "output_key": "wireframes_cobertura", "prompt_file": "design/26_telas.md", "description": "Telas em escala de cinza sobre a seção do DS do ambiente."},
    {"id": "A26bStitchGeracao", "name": "26b · Telas no Stitch (determinístico)", "icon": "🖼️", "output_key": "stitch_geracao", "prompt_file": None, "description": "Gera no Stitch, fora do modelo, toda (tela, estado) da tabela do agente de telas e do inventário da jornada, em paralelo; o screenId é o que o Stitch devolve."},
    {"id": "A27CopyRevisao", "name": "27 · Copy PT-BR (passada 2)", "icon": "🔍", "output_key": "copy_strings_revisada", "prompt_file": "design/27_copy_revisao.md", "description": "Revisão em contexto de tela."},
    {"id": "A27bCopyPreservada", "name": "27b · Copy preservada (determinístico)", "icon": "📌", "output_key": "copy_strings_revisada", "prompt_file": None, "description": "Reanexa à copy revisada, sem mudança, as seções da passada 1 que a revisão não trouxe (prompts e schemas, banco curado, roteiro do podcast)."},
    {"id": "A28Prototipo", "name": "28 · Protótipo navegável (HTML)", "icon": "🖥️", "output_key": "prototipo_html", "prompt_file": "design/28_prototipo.md", "description": "Arquivo HTML único e sem dependências com as telas navegáveis, o painel da etapa vindo do one-pager e as cadências do pico. Salvo como `design/08-prototipo.html`."},
    {"id": "A29ArtefatosDesign", "name": "29 · Artefatos e links (determinístico)", "icon": "🔗", "output_key": "stitch_links", "prompt_file": None, "description": "Separa o HTML do protótipo do relatório, colhe os links das telas no Stitch e monta a folha de diagramas. Stitch com menos telas que o inventário da jornada bloqueia (`stitch_status`, dono `telas`)."},
    {"id": "A29cPrototipoLint", "name": "29a · Lint do protótipo (determinístico)", "icon": "🧹", "output_key": "prototipo_lint_report", "prompt_file": None, "description": "Confere o arquivo do protótipo HTML: o que o QA de entregáveis não vê por ler só o texto. Reprovado devolve ao protótipo no retrabalho de design."},
    {"id": "A29dConsistencia", "name": "29d · Coerência entre documentos (determinístico)", "icon": "📖", "output_key": "consistencia_report", "prompt_file": None, "description": "Jornada, fluxo, copy revisada e protótipo contra o glossário canônico da spec: variante proibida de entidade bloqueia; papel ou idade de personagem, número com unidade, rótulo de botão e nome de arquivo divergentes ficam 🟡. Pegou os quatro nomes do órgão da exp09ef1b."},
    {"id": "A29bEspelhoMiro", "name": "29b · Espelho no Miro (determinístico)", "icon": "🪞", "output_key": "miro_links", "prompt_file": None, "description": "Publica no Miro, como board navegável, os mesmos diagramas Mermaid da jornada e do fluxo. O Mermaid continua sendo a fonte; Miro indisponível não interrompe a esteira."},
    {"id": "A29eCoberturaTelas", "name": "29e · Cobertura de telas (determinístico)", "icon": "🧮", "output_key": "cobertura_telas_report", "prompt_file": None, "description": "Toda tela do inventário da jornada no fluxo, na copy revisada, na cobertura dos wireframes e nos quadros do protótipo, conferida por ID; falta vira ticket com o dono (`cobertura_telas_status`)."},
    {"id": "A29fBancaProdutoNarrativa", "name": "29f · Banca no fim de design: produto realizado em tela", "icon": "🅰️", "output_key": "banca_design_narrativa", "prompt_file": None, "description": "Os critérios PROD que se realizam em tela — fluxo × contrato de estados, momento de conclusão, condução do debate, modos de erro —, antes do parecer de design."},
    {"id": "A29fBancaDesignImersao", "name": "29f · Banca no fim de design: design e imersão", "icon": "🅱️", "output_key": "banca_design_imersao", "prompt_file": None, "description": "Os critérios DES da banca sobre os documentos de design, antes do parecer de design."},
    {"id": "A29fBancaConsolidacao", "name": "29f · Banca de design (determinístico)", "icon": "⚖️", "output_key": "banca_design_report", "prompt_file": None, "description": "Veredito da banca no fim de design. O bloqueio vira ticket pelo A30b e o dono refaz nesta etapa; esgotadas as rodadas, recusa o de acordo."},
    {"id": "A30QaEntregaveis", "name": "30 · QA de entregáveis", "icon": "🧪", "output_key": "qa_entregaveis_report", "prompt_file": "design/30_qa_entregaveis.md", "description": "Fidelidade à spec, diff de strings, currículo, faixa, fluxo, professor, briefing, ambiente (D8) e CAA (D8b)."},
    {"id": "A30bQaAfirmacoes", "name": "30b · Afirmações do QA (determinístico)", "icon": "🔎", "output_key": "qa_afirmacoes_report", "prompt_file": None, "description": "Contagens de telas (\"todas as N telas\", \"N de M\") e nomes de arquivo que o QA escreveu, contra o inventário da jornada, o Stitch, o protótipo e `pipeline/artifacts.py`. Divergência reescreve o veredito do QA como bloqueado; Stitch com menos telas que o inventário vira ticket para `telas`. Pegou as \"16 telas\" de um Stitch com 6 na exp09ef1b."},
    {"id": "A31QaEntregaveisCheck", "name": "31 · Veredito de design (determinístico)", "icon": "🔀", "output_key": "design_status", "prompt_file": None, "description": "Lê o envelope do QA de entregáveis."},
    {"id": "A33RastroDesign", "name": "33 · Rastro de lacunas do design (determinístico)", "icon": "🧭", "output_key": "rastro_design_report", "prompt_file": None, "description": "Marcadores de lacuna na spec consolidada e nos documentos de design: o de design bloqueia a etapa; o que o fechamento de lacunas fechou (`Resolvido em [D0-n]`) não conta; o de produto já aprovado e o de dev ficam 🟡."},
    {"id": "A33bRastreabilidadeDesign", "name": "33b · Matriz de rastreabilidade (determinístico)", "icon": "🧷", "output_key": "rastreabilidade_report", "prompt_file": None, "description": "Cada requisito do produto (habilidades, textos literais, tempo, telas, estados, seção do DS) procurado em cada artefato de design; o que se perdeu sai com o dono."},
    {"id": "A33cFidelidadeDesign", "name": "33c · Fidelidade ao refazer de design", "icon": "📌", "output_key": "fidelidade_design_report", "prompt_file": None, "description": "Cada pedido de refazer feito ao design (TRAVAS, AJUSTES, VALIDAÇÃO, frases entre aspas) conferido na spec consolidada, no brief, na jornada, no fluxo, na copy, na CAA e nas telas: o juiz cita, o código confere. Sem pedido de design, não roda. 🔴 recusa o de acordo."},
    {"id": "A32DespachoDesign", "name": "32 · Retrabalho de design (determinístico)", "icon": "🔁", "output_key": "tickets_retrabalho", "prompt_file": None, "description": "Reexecuta só os agentes com ticket do QA, na ordem de precedência do prompt, e refaz o protótipo depois."},
]
