"""Agentes TRANSVERSAIS — diagnóstico da execução e aprendizado do processo.

Dois passos, sempre os últimos, e nenhum deles depende de a esteira ter dado certo:

  A49Diagnostico (determinístico) → diagnostico_execucao
      O dossiê: como cada portão se saiu, o que trava, de quem é cada conserto, o que saiu
      provisório e qual documento não foi produzido. Lê os envelopes que os gates já
      gravaram no estado; não usa modelo de linguagem, então não falha junto com a esteira.

  A50Aprendizado (LLM) → aprendizado_registro
      A leitura em prosa do dossiê, mais a memória do processo: catálogo, padrões,
      lacunas por classe, candidatos a critério. Nunca edita prompt de agente.
"""

from __future__ import annotations

from typing import Optional

from google.adk.agents.llm_agent import LlmAgent

from agents.base import create_llm_agent
from agents.checkers import DiagnosticoAgent
from prompts import load_prompt


def get_diagnostico_agent() -> DiagnosticoAgent:
    return DiagnosticoAgent(
        name="A49Diagnostico",
        description="Dossiê determinístico da execução: portões, impedimentos por dono, decisões humanas, o que saiu provisório e documentos ausentes.",
    )


def get_aprendizado_agent(
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
) -> LlmAgent:
    return create_llm_agent(
        name="A50Aprendizado",
        description="Registra o que a execução ensinou: catálogo, padrões, lacunas por classe e candidatos a critério.",
        instruction=load_prompt("transversal/50_aprendizado.md"),
        output_key="aprendizado_registro",
        thinking_budget=thinking_budget,
        include_thoughts=include_thoughts,
    )


TRANSVERSAL_METADATA = [
    {"id": "A49Diagnostico", "name": "49 · Diagnóstico da execução (determinístico)", "icon": "🩺", "output_key": "diagnostico_execucao", "prompt_file": None, "description": "Como cada portão se saiu, o que trava e de quem é cada conserto, o que saiu provisório e que documento faltou. Sem LLM — roda mesmo quando tudo o mais falhou."},
    {"id": "A50Aprendizado", "name": "50 · Aprendizado", "icon": "🧠", "output_key": "aprendizado_registro", "prompt_file": "transversal/50_aprendizado.md", "description": "A leitura em prosa do diagnóstico, mais catálogo, padrões aprendidos, lacunas com dono/classe e candidatos a critério."},
]
