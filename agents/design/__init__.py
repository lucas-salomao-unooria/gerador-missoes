"""Área de DESIGN — da spec aprovada aos wireframes lo-fi auditados.

Ordem (SequentialAgent). O MCP do Figma foi removido — não há cliente oficial que o sirva
aqui, e board em ferramenta que ninguém abre não é entregável. A jornada e o fluxo saem em
Mermaid (remontados em `design/09-diagramas.html`), as telas saem no Stitch, e o protótipo
HTML é o que a revisão humana de fato abre.
  d0  A16FechaLacunas       → fechamento_lacunas   (varredura, decisões [D0-n], re-specs [RS-n])
  d0c A17FechaLacunasSplit       → spec_missao (consolidada, bloco 13) · spec_missao_gate0 (cópia
                                 da original) · relatorio_lacunas · lacunas_status
  d9  A18AmbienteSimulado    → ambiente_simulado   (condicional: decide o ambiente quando a
                                 spec cala; dormente emite só a ficha do bloco 14)
  d9c A19AmbienteSimuladoSplit   → spec_missao (com bloco 14) · ambiente_status
  d1  A20BriefOficio        → brief_oficio
  d2  A21Jornada      → jornada_telas   (mapa de jornada + inventário + direção)
  d3  A22Fluxo        → fluxo_arestas   (grafo de telas + 5 testes)
  d4  A23CopyPtBr           → copy_strings    (passada 1)
  d4b A24Caa                → camada_caa      (camada CAA; ele mesmo decide se roda)
  d5  A25Telas    → wireframes_cobertura
  d6  A26CopyRevisao        → copy_strings_revisada (passada 2)
  d8  A27Prototipo          → prototipo_html  (protótipo navegável)
  d8c A28ArtefatosDesign         → prototipo_arquivo (.html) · prototipo_relatorio · stitch_links
                                 · diagramas_html — determinístico, o HTML nunca entra em prompt
  d7  A29QaEntregaveis      → qa_entregaveis_report (gate de design)
  d7c A30QaEntregaveisCheck      → design_status (🔴 impede dev e PRD quando ESTEIRA_ESTRITA)

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
from agents.checkers import (
    ArtefatosDesignAgent,
    DespachoTicketsAgent,
    EnvelopeGateAgent,
    SecaoSplitAgent,
)
from config import get_settings
from prompts import load_prompt
from tools.stitch_mcp import STITCH_TOOLS_QA, STITCH_TOOLS_WIREFRAMES, stitch_tools_or_empty

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


def _gdrive_vars() -> dict:
    s = get_settings()
    return {
        "gdrive_folder_url": s.gdrive_folder_url
        or "(não configurada — as ferramentas do Google Drive não estão disponíveis nesta esteira; registre `GDOCS: indisponível` e entregue só o Markdown)",
    }


def get_fecha_lacunas_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A16FechaLacunas",
        description="Fechamento de lacunas da spec antes do design: varredura célula a célula, decisões [D0-n] com base declarada, pedidos de re-spec [RS-n] e spec consolidada com bloco 13.",
        instruction=load_prompt("design/16_fechamento_lacunas.md", **_gdrive_vars()),
        output_key="fechamento_lacunas",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_fecha_lacunas_split() -> SecaoSplitAgent:
    return SecaoSplitAgent(
        name="A17FechaLacunasSplit",
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
        name="A18AmbienteSimulado",
        description="Ambiente simulado (condicional): decide em que casca a missão acontece quando a spec cala — app clonado da lista fechada, app novo ou mini-jogo em anos iniciais — e emite a ficha do bloco 14 mesmo quando dormente.",
        instruction=load_prompt("design/18_ambiente_simulado.md"),
        output_key="ambiente_simulado",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_ambiente_simulado_split() -> SecaoSplitAgent:
    return SecaoSplitAgent(
        name="A19AmbienteSimuladoSplit",
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
            },
        ],
    )


def get_brief_oficio_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A20BriefOficio",
        description="Briefing de ofício: aposta, forma do arco, pico, beat memorável, mapa de beats e não-negociáveis.",
        instruction=load_prompt("design/20_brief_oficio.md"),
        output_key="brief_oficio",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_jornada_figjam_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A21Jornada",
        description="Mapa de jornada no FigJam (raias × 6 etapas), cenários de dispositivo, inventário de telas e direção por tela.",
        instruction=load_prompt("design/21_jornada.md"),
        output_key="jornada_telas",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_fluxo_figjam_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A22Fluxo",
        description="Grafo de fluxo de telas no FigJam: transições com condição, gates, estados de erro e os 5 testes.",
        instruction=load_prompt("design/22_fluxo.md"),
        output_key="fluxo_arestas",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_copy_ptbr_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A23CopyPtBr",
        description="Copy PT-BR passada 1: sheet de strings por tela, calibrado à faixa etária.",
        instruction=load_prompt("design/23_copy_ptbr.md"),
        output_key="copy_strings",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_caa_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A24Caa",
        description="Camada CAA: símbolos, modos de resposta alternativos e pranchas para quem não lê ou não fala. Aplica o gate de aplicabilidade e devolve `nao_aplicavel` quando a missão não justifica.",
        instruction=load_prompt("design/24_caa.md"),
        output_key="camada_caa",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_wireframes_figma_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A25Telas",
        description="Wireframes lo-fi em escala de cinza no Figma, montados sobre a seção do DS do ambiente simulado.",
        instruction=load_prompt("design/25_telas.md", **_stitch_vars()),
        output_key="wireframes_cobertura",
        # Stitch primeiro: é ele que gera as telas hoje. O Figma continua aceito para
        # quem tiver assento Full e OAuth, e os dois podem coexistir.
        tools=stitch_tools_or_empty(STITCH_TOOLS_WIREFRAMES),
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_copy_revisao_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A26CopyRevisao",
        description="Copy PT-BR passada 2: revisão de cada string dentro da tela construída.",
        instruction=load_prompt("design/26_copy_revisao.md"),
        output_key="copy_strings_revisada",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_prototipo_agent(**kw) -> LlmAgent:
    return create_llm_agent(
        name="A27Prototipo",
        description="Protótipo HTML lo-fi navegável: arquivo único, sem dependências, que a revisão humana abre no navegador e o agente de codificação lê como referência de layout.",
        instruction=load_prompt("design/27_prototipo.md"),
        output_key="prototipo_html",
        before_agent_callback=marcar_heranca,
        **kw,
    )


def get_qa_entregaveis_agent(max_rodadas: Optional[int] = None, **kw) -> LlmAgent:
    # O teto vive no código; o prompt precisa saber dele para não prometer uma rodada de
    # retrabalho que o LoopAgent nunca vai executar (mesmo motivo do gate estrutural).
    rodadas = max_rodadas or get_settings().qa_design_max_rodadas
    return create_llm_agent(
        name="A29QaEntregaveis",
        description="Gate final de design: fidelidade à spec, diff de strings, currículo, faixa etária, fluxo, professor, briefing, ambiente simulado e CAA.",
        instruction=load_prompt(
            "design/29_qa_entregaveis.md",
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
#: copy antes de wireframe · CAA antes de wireframe") — aqui ela vira execução.
ORDEM_RETRABALHO = [
    "fecha-lacunas",
    "ambiente-simulado",
    "jornada",
    "fluxo",
    "copy-ptbr-revisao",
    "caa",
    "telas",
]

#: Slug do envelope → cadeia de agentes que o conserto exige, em ordem.
#: D0 e D9 emitem dois documentos numa resposta só: sem o split logo atrás, a correção
#: fica presa no relatório e nunca chega à `spec_missao` que o resto da esteira lê.
MAPA_RETRABALHO = {
    "fecha-lacunas": ["A16FechaLacunasRetrabalho", "A17FechaLacunasSplitRetrabalho"],
    "ambiente-simulado": ["A18AmbienteSimuladoRetrabalho", "A19AmbienteSimuladoSplitRetrabalho"],
    "jornada": ["A21JornadaRetrabalho"],
    "fluxo": ["A22FluxoRetrabalho"],
    "copy-ptbr-revisao": ["A26CopyRevisaoRetrabalho"],
    "caa": ["A24CaaRetrabalho"],
    "telas": ["A25TelasRetrabalho"],
}

#: Roda depois de qualquer retrabalho. O protótipo deriva de jornada, copy, CAA e telas —
#: deixá-lo de fora faria o QA auditar, na rodada seguinte, um protótipo da rodada anterior.
POSFIXO_RETRABALHO = ["A27PrototipoRetrabalho", "A28ArtefatosDesignRetrabalho"]

#: Tickets endereçados a estes donos não são desta etapa: o QA está devolvendo ao produto.
RETRABALHO_EXTERNO = ["gate-estrutural"]


def _agentes_de_retrabalho(**kw) -> list:
    """Instâncias dedicadas ao retrabalho: mesmo prompt e mesmo `output_key`, nome próprio.

    Precisam ser instâncias novas porque um agente do ADK tem um único pai na árvore;
    o nome com sufixo mantém a árvore válida e deixa o retrabalho visível no log.
    """
    pares = [
        (get_fecha_lacunas_agent, "A16FechaLacunasRetrabalho"),
        (get_ambiente_simulado_agent, "A18AmbienteSimuladoRetrabalho"),
        (get_jornada_figjam_agent, "A21JornadaRetrabalho"),
        (get_fluxo_figjam_agent, "A22FluxoRetrabalho"),
        (get_copy_revisao_agent, "A26CopyRevisaoRetrabalho"),
        (get_caa_agent, "A24CaaRetrabalho"),
        (get_wireframes_figma_agent, "A25TelasRetrabalho"),
        (get_prototipo_agent, "A27PrototipoRetrabalho"),
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
    split_lacunas.name = "A17FechaLacunasSplitRetrabalho"
    split_ambiente = get_ambiente_simulado_split()
    split_ambiente.name = "A19AmbienteSimuladoSplitRetrabalho"
    agentes += [
        split_lacunas,
        split_ambiente,
        ArtefatosDesignAgent(
            name="A28ArtefatosDesignRetrabalho",
            description="Reextrai o HTML do protótipo, os links do Stitch e a folha de diagramas depois de uma rodada de retrabalho.",
        ),
    ]
    return agentes


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
            get_qa_entregaveis_agent(max_rodadas=rodadas, **kw),
            EnvelopeGateAgent(
                name="A30QaEntregaveisCheck",
                description="Lê o veredito do QA de entregáveis: aprovado encerra o loop; 🔴 na última rodada impede o dev e o PRD (modo estrito).",
                rotulo="QA de entregáveis (design)",
                report_key="qa_entregaveis_report",
                status_key="design_status",
                round_key="qa_design_rodada",
                max_rounds=rodadas,
                escalate_on_approve=True,
                block_pipeline_on_fail=get_settings().esteira_estrita,
                treat_indefinido_as_blocked=False,
                # Com o pipeline já bloqueado ele leria a mensagem de pulo do QA
                # e sobrescreveria o motivo do bloqueio original.
                before_agent_callback=marcar_heranca,
            ),
            DespachoTicketsAgent(
                name="A31DespachoDesign",
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
            get_prototipo_agent(**kw),
            ArtefatosDesignAgent(
                name="A28ArtefatosDesign",
                description="Separa o HTML do protótipo do relatório que o acompanha, colhe os links das telas no Stitch e monta a folha de diagramas da jornada e do fluxo.",
                before_agent_callback=marcar_heranca,
            ),
            build_qa_design_loop(**kw),
        ],
    )


DESIGN_METADATA = [
    {"id": "A16FechaLacunas", "name": "16 · Fechamento de lacunas", "icon": "🧩", "output_key": "fechamento_lacunas", "prompt_file": "design/16_fechamento_lacunas.md", "description": "Varredura da spec célula a célula, decisões [D0-n] com base declarada, pedidos de re-spec [RS-n], spec consolidada (bloco 13) e relatório de preenchimento."},
    {"id": "A17FechaLacunasSplit", "name": "17 · Relatório de lacunas + spec consolidada (determinístico)", "icon": "✂️", "output_key": "relatorio_lacunas", "prompt_file": None, "description": "Copia a spec consolidada para `spec_missao` (original preservada em `spec_missao_gate0`), separa o relatório e registra `lacunas_status`."},
    {"id": "A18AmbienteSimulado", "name": "18 · Ambiente simulado", "icon": "🏝️", "output_key": "ambiente_simulado", "prompt_file": "design/18_ambiente_simulado.md", "description": "Condicional: decide o ambiente (app clonado existente, app novo ou mini-jogo) quando a spec cala; dormente emite só a ficha do bloco 14 que D1, D2, D4, D5 e o QA consomem."},
    {"id": "A19AmbienteSimuladoSplit", "name": "19 · Spec com bloco 14 (determinístico)", "icon": "✂️", "output_key": "ambiente_status", "prompt_file": None, "description": "Copia a spec com o bloco 14 para `spec_missao` e registra `ambiente_status`."},
    {"id": "A20BriefOficio", "name": "20 · Briefing de ofício", "icon": "🎯", "output_key": "brief_oficio", "prompt_file": "design/20_brief_oficio.md", "description": "Aposta, forma do arco, pico, beat memorável, mapa de beats, não-negociáveis."},
    {"id": "A21Jornada", "name": "21 · Jornada (Mermaid)", "icon": "🗺️", "output_key": "jornada_telas", "prompt_file": "design/21_jornada.md", "description": "Raias × 6 etapas, cenários de dispositivo, inventário de telas e direção por tela."},
    {"id": "A22Fluxo", "name": "22 · Fluxo de telas (Mermaid)", "icon": "🕸️", "output_key": "fluxo_arestas", "prompt_file": "design/22_fluxo.md", "description": "Grafo de telas com condições, gates e os 5 testes de fluxo."},
    {"id": "A23CopyPtBr", "name": "23 · Copy PT-BR (passada 1)", "icon": "✍️", "output_key": "copy_strings", "prompt_file": "design/23_copy_ptbr.md", "description": "Sheet de strings por tela, calibrado à faixa etária."},
    {"id": "A24Caa", "name": "24 · Camada CAA", "icon": "🔣", "output_key": "camada_caa", "prompt_file": "design/24_caa.md", "description": "Símbolos, modos de resposta alternativos e pranchas; só roda quando a faixa ou a spec pedem."},
    {"id": "A25Telas", "name": "25 · Wireframes lo-fi (Stitch)", "icon": "📐", "output_key": "wireframes_cobertura", "prompt_file": "design/25_telas.md", "description": "Telas em escala de cinza sobre a seção do DS do ambiente."},
    {"id": "A26CopyRevisao", "name": "26 · Copy PT-BR (passada 2)", "icon": "🔍", "output_key": "copy_strings_revisada", "prompt_file": "design/26_copy_revisao.md", "description": "Revisão em contexto de tela."},
    {"id": "A27Prototipo", "name": "27 · Protótipo navegável (HTML)", "icon": "🖥️", "output_key": "prototipo_html", "prompt_file": "design/27_prototipo.md", "description": "Arquivo HTML único e sem dependências com as telas navegáveis, o painel da etapa vindo do one-pager e as cadências do pico. Salvo como `design/08-prototipo.html`."},
    {"id": "A28ArtefatosDesign", "name": "28 · Artefatos e links (determinístico)", "icon": "🔗", "output_key": "stitch_links", "prompt_file": None, "description": "Separa o HTML do protótipo do relatório, colhe os links das telas no Stitch e monta a folha de diagramas."},
    {"id": "A29QaEntregaveis", "name": "29 · QA de entregáveis", "icon": "🧪", "output_key": "qa_entregaveis_report", "prompt_file": "design/29_qa_entregaveis.md", "description": "Fidelidade à spec, diff de strings, currículo, faixa, fluxo, professor, briefing, ambiente (D8) e CAA (D8b)."},
    {"id": "A30QaEntregaveisCheck", "name": "30 · Veredito de design (determinístico)", "icon": "🔀", "output_key": "design_status", "prompt_file": None, "description": "Lê o envelope do QA de entregáveis."},
    {"id": "A31DespachoDesign", "name": "31 · Retrabalho de design (determinístico)", "icon": "🔁", "output_key": "tickets_retrabalho", "prompt_file": None, "description": "Reexecuta só os agentes com ticket do QA, na ordem de precedência do prompt, e refaz o protótipo depois."},
]
