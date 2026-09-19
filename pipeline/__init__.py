"""Pacote do pipeline orquestrador do Google ADK.

Os símbolos são resolvidos sob demanda (PEP 562). Importar `orchestrator` e `runner`
avidamente aqui fazia com que qualquer `from pipeline.artifacts import ...` puxasse
`google.adk`, `google.genai` e `mcp` junto — cerca de 0,9 s de import para quem só queria
ler o manifesto de artefatos.
"""

from typing import Any, List

__all__ = [
    "FINAL_OUTPUT_KEY",
    "STAGES",
    "PipelineExecutionResult",
    "create_mission_orchestrator",
    "get_pipeline_agents_metadata",
    "get_pipeline_stages",
    "iter_agent_tree",
    "run_orchestrator_pipeline_stream",
    "run_orchestrator_pipeline_sync",
]

_ORIGEM = {
    "FINAL_OUTPUT_KEY": "orchestrator",
    "STAGES": "orchestrator",
    "create_mission_orchestrator": "orchestrator",
    "get_pipeline_agents_metadata": "orchestrator",
    "get_pipeline_stages": "orchestrator",
    "iter_agent_tree": "orchestrator",
    "PipelineExecutionResult": "runner",
    "run_orchestrator_pipeline_stream": "runner",
    "run_orchestrator_pipeline_sync": "runner",
}


def __getattr__(name: str) -> Any:
    modulo = _ORIGEM.get(name)
    if modulo is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    return getattr(import_module(f"{__name__}.{modulo}"), name)


def __dir__() -> List[str]:
    return sorted(__all__)
