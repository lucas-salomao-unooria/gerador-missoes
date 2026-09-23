"""Fábrica do juiz de achados: o par (agente que aplica + juiz de LLM), uma instância por ponto.

Um agente do ADK tem um único pai na árvore, então cada gate que recebe juiz ganha o seu.
"""
from __future__ import annotations

from agents.base import create_llm_agent
from agents.checkers import JuizDeAchadosAgent
from prompts import load_prompt


def get_juiz_de_achados(nome: str, *, status_key: str, report_key: str, fonte_key: str,
                        gate_rotulo: str, **kw) -> JuizDeAchadosAgent:
    base = status_key.removesuffix("_status")
    juiz = create_llm_agent(
        name=f"{nome}Llm",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description=f"Lê as linhas que o gate `{gate_rotulo}` marcou e decide, com citação, se o texto afirma o uso do que a plataforma veda ou só cita para vedar.",
        instruction=load_prompt("transversal/60_juiz_de_achados.md"),
        output_key=f"juiz_{base}_saida",
        **kw,
    )
    return JuizDeAchadosAgent(
        name=nome,
        description=f"Juiz de achados sobre `{gate_rotulo}`: retira o achado de uso vedado quando o texto só cita para vedar — com citação literal conferida.",
        status_key=status_key, report_key=report_key, fonte_key=fonte_key, gate_rotulo=gate_rotulo,
        rotulo=f"Juiz de achados ({gate_rotulo})",
        sub_agents=[juiz],
    )
