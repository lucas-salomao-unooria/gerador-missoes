"""Orquestrador do Gerador de Missões Unooria (Google ADK).

Árvore de agentes:

    MissionPipelineOrchestrator (SequentialAgent)
    ├── ProdutoStage   (SequentialAgent)  one-pager → gate estrutural (loop) → avaliações (paralelo) → gate final → spec
    ├── DesignStage    (SequentialAgent)  briefing → jornada 🎨 → fluxo 🎨 → copy → wireframes 🎨 → copy 2 → QA
    ├── DevStage       (SequentialAgent)  handoff ∥ assets → banca (5 ∥) → consolidação → PRD
    └── A51Aprendizado (transversal)

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

from agents.design import DESIGN_METADATA, build_design_stage
from agents.dev import DEV_METADATA, build_dev_stage
from agents.produto import PRODUTO_METADATA, build_produto_stage
from agents.transversal import TRANSVERSAL_METADATA, get_aprendizado_agent, get_diagnostico_agent
from config import get_settings

warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.adk")

STAGES: List[Dict[str, Any]] = [
    {"key": "produto", "name": "Produto", "icon": "🧭", "container": "ProdutoStage", "agents": PRODUTO_METADATA},
    {"key": "design", "name": "Design", "icon": "🎨", "container": "DesignStage", "agents": DESIGN_METADATA},
    {"key": "dev", "name": "Dev", "icon": "🛠️", "container": "DevStage", "agents": DEV_METADATA},
    {"key": "transversal", "name": "Transversal", "icon": "🧠", "container": None, "agents": TRANSVERSAL_METADATA},
]

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


def create_mission_orchestrator(
    name: str = "MissionPipelineOrchestrator",
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
    modo_estrito: Optional[bool] = None,
    stages: Optional[List[str]] = None,
) -> SequentialAgent:
    """Cria o orquestrador raiz com as etapas Produto → Design → Dev → Aprendizado."""
    settings = get_settings()
    t_budget = thinking_budget if thinking_budget is not None else settings.thinking_budget
    inc_thoughts = include_thoughts if include_thoughts is not None else settings.include_thoughts
    active = stages or settings.pipeline_stages

    sub_agents = []
    if "produto" in active:
        sub_agents.append(build_produto_stage(t_budget, inc_thoughts, modo_estrito=modo_estrito))
    if "design" in active:
        sub_agents.append(build_design_stage(t_budget, inc_thoughts))
    if "dev" in active:
        sub_agents.append(build_dev_stage(t_budget, inc_thoughts))
    # O diagnóstico vem antes do aprendizado: é ele quem monta o dossiê que o aprendizado
    # lê para escrever a leitura em prosa. Ambos rodam sempre — a esteira não aborta mais,
    # e mesmo que abortasse, estes dois são o que explica o que houve.
    sub_agents.append(get_diagnostico_agent())
    sub_agents.append(get_aprendizado_agent(t_budget, inc_thoughts))

    return SequentialAgent(
        name=name,
        description=(
            "Orquestrador do Gerador de Missões Unooria: valida e especifica a missão (Produto), "
            "constrói jornada e fluxo em Mermaid, copy, telas no Stitch e protótipo navegável (Design), e entrega um PRD "
            "padrão ouro validado pela banca de dev (Dev), com o contexto arquitetural da plataforma."
        ),
        sub_agents=sub_agents,
    )


def iter_agent_tree(agent, depth: int = 0):
    """Percorre a árvore de agentes (para testes e depuração)."""
    yield depth, agent
    for sub in getattr(agent, "sub_agents", []) or []:
        yield from iter_agent_tree(sub, depth + 1)
