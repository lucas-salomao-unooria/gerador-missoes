"""Agentes TRANSVERSAIS — diagnóstico da execução e aprendizado do processo.

Dois passos, sempre os últimos, e nenhum deles depende de a esteira ter dado certo:

  A50Diagnostico (determinístico) → diagnostico_execucao
      O dossiê: como cada portão se saiu, o que trava, de quem é cada conserto, o que saiu
      provisório e qual documento não foi produzido. Lê os envelopes que os gates já
      gravaram no estado; não usa modelo de linguagem, então não falha junto com a esteira.

  A51Aprendizado (LLM) → aprendizado_registro
  A52RegistroCatalogo (determinístico) → ficha_catalogo (memória entre execuções)
      A leitura em prosa do dossiê, mais a memória do processo: catálogo, padrões,
      lacunas por classe, candidatos a critério. Nunca edita prompt de agente.
"""

from __future__ import annotations

from typing import Optional

from google.adk.agents.llm_agent import LlmAgent

from agents.base import create_llm_agent
from agents.checkers import DiagnosticoAgent, RegistroCatalogoAgent
from prompts import load_prompt


def get_diagnostico_agent() -> DiagnosticoAgent:
    return DiagnosticoAgent(
        name="A50Diagnostico",
        description="Dossiê determinístico da execução: portões, impedimentos por dono, decisões humanas, o que saiu provisório e documentos ausentes.",
    )


def get_registro_catalogo_agent() -> RegistroCatalogoAgent:
    return RegistroCatalogoAgent(
        name="A52RegistroCatalogo",
        description="Registra a missão na memória do gerador: ficha desta execução, missões mais próximas no índice e colisão de slug. Roda depois do aprendizado, que é quem escreve os campos de julgamento.",
    )


def get_aprendizado_agent(
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
) -> LlmAgent:
    return create_llm_agent(
        name="A51Aprendizado",
        description="Registra o que a execução ensinou: catálogo, padrões, lacunas por classe e candidatos a critério.",
        instruction=load_prompt("transversal/51_aprendizado.md"),
        output_key="aprendizado_registro",
        thinking_budget=thinking_budget,
        include_thoughts=include_thoughts,
    )


def get_triagem_correcao_agent(thinking_budget: Optional[int] = 1024) -> LlmAgent:
    """Decide de qual etapa uma correção recomeça (`spec | design | dev | nenhuma`).

    Roda FORA da esteira, antes de montar o orquestrador (`pipeline/reexecucao.triar_pedido`).
    É o único agente além do A01 com `include_contents="default"`: precisa ver a mensagem da
    pessoa e os anexos, inclusive PDF como arquivo. Não entra em `TRANSVERSAL_METADATA`.
    """
    return create_llm_agent(
        name="A00TriagemCorrecao",
        description="Triagem de um pedido de correção numa missão já gerada: de qual etapa a esteira recomeça, e o resumo do pedido para quem executa.",
        instruction=load_prompt("transversal/00_triagem_correcao.md"),
        output_key="triagem_correcao",
        include_contents="default",
        thinking_budget=thinking_budget,
        include_thoughts=False,
    )


TRANSVERSAL_METADATA = [
    {"id": "A50Diagnostico", "name": "50 · Diagnóstico da execução (determinístico)", "icon": "🩺", "output_key": "diagnostico_execucao", "prompt_file": None, "description": "Como cada portão se saiu, o que trava e de quem é cada conserto, o que saiu provisório e que documento faltou. Sem LLM — roda mesmo quando tudo o mais falhou."},
    {"id": "A51Aprendizado", "name": "51 · Aprendizado", "icon": "🧠", "output_key": "aprendizado_registro", "prompt_file": "transversal/51_aprendizado.md", "description": "A leitura em prosa do diagnóstico, mais catálogo, padrões aprendidos, lacunas com dono/classe e candidatos a critério."},
    {"id": "A52RegistroCatalogo", "name": "52 · Registro no catálogo (determinístico)", "icon": "🗂️", "output_key": "ficha_catalogo", "prompt_file": None, "description": "A memória entre execuções: registra esta missão no índice, mostra as mais próximas e acusa slug repetido. Sem LLM — status derivado dos gates, promover é ato humano."},
]
