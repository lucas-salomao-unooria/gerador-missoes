"""Agentes TRANSVERSAIS — diagnóstico da execução e aprendizado do processo.

Dois passos, sempre os últimos, e nenhum deles depende de a esteira ter dado certo:

  A127Diagnostico (determinístico) → diagnostico_execucao
      O dossiê: como cada portão se saiu, o que trava, de quem é cada conserto, o que saiu
      provisório e qual documento não foi produzido. Lê os envelopes que os gates já
      gravaram no estado; não usa modelo de linguagem, então não falha junto com a esteira.

  A128Aprendizado (LLM) → aprendizado_registro
  A129RegistroCatalogo (determinístico) → ficha_catalogo (memória entre execuções)
      A leitura em prosa do dossiê, mais a memória do processo: catálogo, padrões,
      lacunas por classe, candidatos a critério. Nunca edita prompt de agente.
"""

from __future__ import annotations

from typing import Optional

from google.adk.agents.llm_agent import LlmAgent

from agents.base import create_llm_agent
from agents.checkers import DiagnosticoAgent, RegistroCatalogoAgent
from config import get_settings
from prompts import load_prompt


def get_diagnostico_agent() -> DiagnosticoAgent:
    return DiagnosticoAgent(
        name="A127Diagnostico",
        description="Dossiê determinístico da execução: portões, impedimentos por dono, decisões humanas, o que saiu provisório e documentos ausentes.",
    )


def get_registro_catalogo_agent() -> RegistroCatalogoAgent:
    return RegistroCatalogoAgent(
        name="A129RegistroCatalogo",
        description="Registra a missão na memória do gerador: ficha desta execução, missões mais próximas no índice e colisão de slug. Roda depois do aprendizado, que é quem escreve os campos de julgamento.",
    )


def get_aprendizado_agent(
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
) -> LlmAgent:
    settings = get_settings()
    orcamento = settings.thinking_budget_curto if thinking_budget is None else thinking_budget
    return create_llm_agent(
        name="A128Aprendizado",
        description="Registra o que a execução ensinou: catálogo, padrões, lacunas por classe e candidatos a critério.",
        instruction=load_prompt("transversal/128_aprendizado.md"),
        output_key="aprendizado_registro",
        model=settings.gemini_model_parecer,
        thinking_budget=orcamento,
        include_thoughts=include_thoughts,
        after_agent_callback=conferir_aprendizado,
    )


def conferir_aprendizado(callback_context) -> None:
    """after_agent_callback do A128: o status da linha de catálogo e os fatos em código (`tools/aprendizado.py`). Na
    exp06ef1b (53e011b6, R10 do levantamento de 24/10/2026) o registro dizia «Mecânicas ausentes encontradas
    tardiamente: Nenhuma» num PRD que trocou a H3, e propunha a missão «em produção»."""
    from pipeline.artifacts import e_mensagem_de_pulo
    from tools.aprendizado import conferir

    state = callback_context.state
    texto = state.get("aprendizado_registro")
    if not isinstance(texto, str) or not texto.strip() or e_mensagem_de_pulo(texto):
        return None
    novo = conferir(texto, state.to_dict() if hasattr(state, "to_dict") else dict(state))
    if novo != texto:
        state["aprendizado_registro"] = novo
    return None


def get_triagem_correcao_agent(thinking_budget: Optional[int] = 1024) -> LlmAgent:
    """Decide de qual etapa uma correção recomeça (`spec | design | dev | nenhuma`).

    Roda FORA da esteira, antes de montar o orquestrador (`pipeline/reexecucao.triar_pedido`).
    É o único agente além do A004 com `include_contents="default"`: precisa ver a mensagem da
    pessoa e os anexos, inclusive PDF como arquivo. Não entra em `TRANSVERSAL_METADATA`.
    """
    return create_llm_agent(
        name="A000TriagemCorrecao",
        description="Triagem de um pedido de correção numa missão já gerada: de qual etapa a esteira recomeça, e o resumo do pedido para quem executa.",
        instruction=load_prompt("transversal/triagem_correcao.md"),
        output_key="triagem_correcao",
        model=get_settings().gemini_model_classificador,
        include_contents="default",
        thinking_budget=thinking_budget,
        include_thoughts=False,
    )


def get_editor_pontual_agent(thinking_budget: Optional[int] = 4096) -> LlmAgent:
    """Transforma o pedido de correção em trocas trecho a trecho (`tools/edicao_pontual.py`), ou diz que é estrutural.

    Roda FORA da esteira, como a triagem (`pipeline/reexecucao.propor_edicao`), e não entra em `TRANSVERSAL_METADATA`.
    Não é autor: o `output_key` não é documento, então não recebe `anterior_` nem é travado na correção pontual. É
    determinístico para que o mesmo pedido sobre os mesmos documentos dê as mesmas trocas.
    """
    return create_llm_agent(
        name="A000EditorPontual",
        description="Correção pontual: aplica o pedido do PO como trocas literais nos documentos da etapa, sem reescrevê-los.",
        instruction=load_prompt("transversal/editor_pontual.md"),
        output_key="edicao_pontual",
        thinking_budget=thinking_budget,
        include_thoughts=False,
        deterministico=True,
    )


def get_conversa_etapa_agent(thinking_budget: Optional[int] = 2048) -> LlmAgent:
    """Responde perguntas sobre uma etapa da missão, sem alterar nada (`pipeline/conversa_etapas.py`).

    Roda FORA da esteira, como a triagem, e também não entra em `TRANSVERSAL_METADATA`. Vê a
    pergunta como mensagem (`include_contents="default"`); os documentos da etapa e a conversa
    anterior chegam pelo estado, já recortados.
    """
    return create_llm_agent(
        name="A000ConversaEtapa",
        description="Conversa sobre uma etapa da missão: responde com os documentos dela, sem mudar nada, e rascunha o comentário do parecer.",
        instruction=load_prompt("transversal/conversa_etapa.md"),
        output_key="resposta_conversa",
        include_contents="default",
        thinking_budget=thinking_budget,
        include_thoughts=False,
    )


TRANSVERSAL_METADATA = [
    {"id": "A127Diagnostico", "name": "127 · Diagnóstico da execução (determinístico)", "icon": "🩺", "output_key": "diagnostico_execucao", "prompt_file": None, "description": "Como cada portão se saiu, o que trava e de quem é cada conserto, o que saiu provisório e que documento faltou. Sem LLM — roda mesmo quando tudo o mais falhou."},
    {"id": "A128Aprendizado", "name": "128 · Aprendizado", "icon": "🧠", "output_key": "aprendizado_registro", "prompt_file": "transversal/128_aprendizado.md", "description": "A leitura em prosa do diagnóstico, mais catálogo, padrões aprendidos, lacunas com dono/classe e candidatos a critério."},
    {"id": "A129RegistroCatalogo", "name": "129 · Registro no catálogo (determinístico)", "icon": "🗂️", "output_key": "ficha_catalogo", "prompt_file": None, "description": "A memória entre execuções: registra esta missão no índice, mostra as mais próximas e acusa slug repetido. Sem LLM — status derivado dos gates, promover é ato humano."},
]
