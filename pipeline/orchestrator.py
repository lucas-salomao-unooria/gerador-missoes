"""Orquestrador do Gerador de Missões Unooria (Google ADK).

Árvore de agentes:

    MissionPipelineOrchestrator (SequentialAgent)
    ├── ProdutoStage   (SequentialAgent)  one-pager → gate estrutural (loop) → avaliações (paralelo) → gate final → spec
    ├── DesignStage    (SequentialAgent)  briefing → jornada 🎨 → fluxo 🎨 → copy → wireframes 🎨 → copy 2 → QA
    ├── DevStage       (SequentialAgent)  handoff ∥ assets → banca (5 ∥) → consolidação → PRD
    └── A128Aprendizado (transversal)

Controle de fluxo determinístico: os `EnvelopeGateAgent` leem o envelope JSON dos
relatórios e gravam o status no `session.state`; os agentes a jusante carregam o
`before_agent_callback` `marcar_heranca`, que os pula quando um gate de produto
bloqueou a missão em modo estrito.

Nota: `SequentialAgent`/`ParallelAgent`/`LoopAgent` estão marcados como deprecated no
ADK 2.x em favor de `Workflow`; continuam funcionais e são a base desta estrutura.
A migração para `Workflow` (rotas condicionais nativas) é o próximo passo natural.
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional

from google.adk.agents.sequential_agent import SequentialAgent

from agents.checkers import LinhaDeBaseAgent
from agents.design import DESIGN_METADATA, build_design_stage
from agents.dev import DEV_METADATA, build_dev_stage
from agents.produto import PRODUTO_METADATA, PRODUTO_METADATA_SPEC, build_produto_stage
from agents.transversal import (
    TRANSVERSAL_METADATA,
    get_aprendizado_agent,
    get_diagnostico_agent,
    get_registro_catalogo_agent,
)
from config import get_settings

warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.adk")

STAGES: List[Dict[str, Any]] = [
    {"key": "produto", "name": "Produto", "icon": "🧭", "container": "ProdutoStage", "agents": PRODUTO_METADATA},
    {"key": "design", "name": "Design", "icon": "🎨", "container": "DesignStage", "agents": DESIGN_METADATA},
    {"key": "dev", "name": "Dev", "icon": "🛠️", "container": "DevStage", "agents": DEV_METADATA},
    {"key": "transversal", "name": "Transversal", "icon": "🧠", "container": None, "agents": TRANSVERSAL_METADATA},
]

#: Etapa parcial do modo correção (`pipeline/reexecucao.py`): só spec ↔ gates → one-pager resumido.
#: Fica fora de `STAGES` de propósito — não é uma etapa que a configuração liga, e listá-la
#: duplicaria os agentes A045–A061 nos metadados da UI.
STAGE_SPEC: Dict[str, Any] = {"key": "spec", "name": "Produto (spec)", "icon": "🧭", "container": "ProdutoStage", "agents": PRODUTO_METADATA_SPEC}

FINAL_OUTPUT_KEY = "prd_final"


def get_pipeline_stages(active_only: bool = True) -> List[Dict[str, Any]]:
    """Etapas do pipeline com seus agentes (para UI e testes)."""
    settings = get_settings()
    active = set(settings.pipeline_stages) | {"transversal"}
    stages = []
    for stage in STAGES:
        if active_only and stage["key"] not in active:
            continue
        stages.append(stage)
    return stages


def get_pipeline_agents_metadata(active_only: bool = True) -> List[Dict[str, Any]]:
    """Lista plana de agentes (com `stage` e `step`) para exibição e monitoramento."""
    flat: List[Dict[str, Any]] = []
    step = 0
    for stage in get_pipeline_stages(active_only):
        for meta in stage["agents"]:
            step += 1
            item = dict(meta)
            item.update({"step": step, "stage": stage["key"], "stage_name": stage["name"], "stage_icon": stage["icon"]})
            flat.append(item)
    return flat


def stages_para_ui(keys: List[str]) -> List[Dict[str, Any]]:
    """Entradas de etapa (com agentes) para as chaves pedidas, mais a transversal, na ordem da esteira.

    É o que a tela de progresso usa numa correção: só as etapas que vão rodar. `spec` resolve
    para o estágio parcial de produto.
    """
    pedidas = set(keys or []) | {"transversal"}
    resultado: List[Dict[str, Any]] = []
    for stage in STAGES:
        if stage["key"] == "produto" and "produto" not in pedidas and "spec" in pedidas:
            resultado.append(STAGE_SPEC)
        elif stage["key"] in pedidas:
            resultado.append(stage)
    return resultado


def create_mission_orchestrator(
    name: str = "MissionPipelineOrchestrator",
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
    modo_estrito: Optional[bool] = None,
    stages: Optional[List[str]] = None,
    com_transversal: bool = True,
    modo_pontual: bool = False,
) -> SequentialAgent:
    """Cria o orquestrador raiz com as etapas Produto → Design → Dev → Aprendizado.

    `com_transversal=False` monta só as etapas pedidas, sem diagnóstico, aprendizado e registro
    no catálogo: é como a esteira roda com parecer humano (`pipeline/passagem.py`), uma etapa por
    vez. Os três ficam para o parecer final do Dev — rodar a cada etapa registraria no catálogo
    uma missão pela metade, e o gate de repetição (V5) passaria a acusá-la contra si mesma.
    """
    settings = get_settings()
    t_budget = thinking_budget if thinking_budget is not None else settings.thinking_budget
    inc_thoughts = include_thoughts if include_thoughts is not None else settings.include_thoughts
    active = stages or settings.pipeline_stages

    sub_agents = []
    if "produto" in active:
        sub_agents.append(build_produto_stage(t_budget, inc_thoughts, modo_estrito=modo_estrito))
    elif "spec" in active:
        # correção a partir da spec: núcleo, one-pager e gates vêm do estado salvo
        sub_agents.append(build_produto_stage(t_budget, inc_thoughts, modo_estrito=modo_estrito, a_partir_de="spec"))
    if "design" in active:
        sub_agents.append(build_design_stage(t_budget, inc_thoughts))
    if "dev" in active:
        sub_agents.append(build_dev_stage(t_budget, inc_thoughts))
    if modo_pontual:
        # Correção pontual (`pipeline/reexecucao.py`): os documentos já vêm editados e os autores não rodam
        # (`agents.callbacks.travar_documento_na_correcao_pontual`). Os gates julgam uma vez — repetir a rodada só os
        # faria julgar o mesmo texto —, e o que a correção causou volta ao editor fora da esteira. No fim, a linha de
        # base separa o bloqueio da correção do que ela não tocou.
        for etapa in sub_agents:
            limitar_a_uma_rodada(etapa)
        sub_agents.append(LinhaDeBaseAgent(name="A000LinhaDeBase",
                                           description="Correção pontual: bloqueios dos gates × veredito de antes."))
    # O diagnóstico vem antes do aprendizado: é ele quem monta o dossiê que o aprendizado
    # lê para escrever a leitura em prosa. Ambos rodam sempre — a esteira não aborta mais,
    # e mesmo que abortasse, estes dois são o que explica o que houve.
    if com_transversal:
        sub_agents.append(get_diagnostico_agent())
        sub_agents.append(get_aprendizado_agent(t_budget, inc_thoughts))
        # Por último, de propósito: a ficha de catálogo copia do aprendizado os campos de julgamento
        # (descoberta, eixo, tipo de decisão) que só ele redige.
        sub_agents.append(get_registro_catalogo_agent())

    return SequentialAgent(
        name=name,
        description=(
            "Orquestrador do Gerador de Missões Unooria: valida e especifica a missão (Produto), "
            "constrói jornada e fluxo em Mermaid, copy, telas no Stitch e protótipo navegável (Design), e entrega um PRD "
            "padrão ouro validado pela banca de dev (Dev), com o contexto arquitetural da plataforma."
        ),
        sub_agents=sub_agents,
    )


#: Prompts que nenhum agente dos metadados declara: os juízes genéricos (um por tipo de verificador) e os dois
#: agentes fora da esteira. `passos_dos_prompts_compartilhados` diz quem os usa, a partir da árvore real.
ROTULO_PROMPT_COMPARTILHADO = {
    "transversal/juiz_de_fidelidade.md": "Juiz de fidelidade (compartilhado)",
    "transversal/juiz_de_achados.md": "Juiz de achados (compartilhado)",
    "transversal/juiz_de_contradicoes.md": "Juiz de contradições (compartilhado)",
    "transversal/triagem_correcao.md": "000 · Triagem do pedido de correção (fora da esteira)",
    "transversal/conversa_etapa.md": "000 · Conversa sobre a missão (fora da esteira)",
}


def passos_dos_prompts_compartilhados() -> Dict[str, List[str]]:
    """`{prompt: [agentes]}` dos juízes genéricos, pela classe do verificador que os contém, e dos dois de fora."""
    from agents.checkers import FidelidadeCheckAgent, JuizDeAchadosAgent, JuizDeContradicoesAgent
    from agents.design import build_design_stage
    from agents.dev import build_dev_stage
    from agents.produto import build_produto_stage

    por_classe = {FidelidadeCheckAgent: "transversal/juiz_de_fidelidade.md",
                  JuizDeAchadosAgent: "transversal/juiz_de_achados.md",
                  JuizDeContradicoesAgent: "transversal/juiz_de_contradicoes.md"}
    usos: Dict[str, List[str]] = {"transversal/triagem_correcao.md": ["A000TriagemCorrecao"],
                                  "transversal/conversa_etapa.md": ["A000ConversaEtapa"]}
    for raiz in (build_produto_stage(), build_design_stage(), build_dev_stage()):
        for _, agente in iter_agent_tree(raiz):
            prompt = next((p for c, p in por_classe.items() if isinstance(agente, c)), None)
            if prompt and agente.name not in usos.setdefault(prompt, []):
                usos[prompt].append(agente.name)
    return usos


def limitar_a_uma_rodada(raiz) -> None:
    """Todo loop da árvore roda uma volta, e cada gate decide na primeira rodada (registra a reprovação, não a adia).

    O comitê fica de fora: na última rodada ele vira 🟡 por desenho, e na correção pontual o voto vencido tem de
    chegar como 🔴 à linha de base e ao editor.
    """
    from google.adk.agents.loop_agent import LoopAgent

    from agents.checkers import ComiteVotosAgent

    for _, agente in iter_agent_tree(raiz):
        if isinstance(agente, LoopAgent):
            agente.max_iterations = 1
        elif not isinstance(agente, ComiteVotosAgent) and isinstance(getattr(agente, "max_rounds", None), int):
            agente.max_rounds = 1


def iter_agent_tree(agent, depth: int = 0):
    """Percorre a árvore de agentes (para testes e depuração)."""
    yield depth, agent
    for sub in getattr(agent, "sub_agents", []) or []:
        yield from iter_agent_tree(sub, depth + 1)
