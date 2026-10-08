"""Fábrica padronizada de LlmAgent para o pipeline (Google ADK)."""

from __future__ import annotations

import time
from typing import Any, List, Optional

from google.adk.agents.llm_agent import LlmAgent
from google.genai import types

from config import get_settings


def create_llm_agent(
    name: str,
    instruction: str,
    description: str,
    output_key: Optional[str] = None,
    tools: Optional[List[Any]] = None,
    model: Optional[str] = None,
    thinking_budget: Optional[int] = None,
    include_thoughts: Optional[bool] = None,
    include_contents: str = "none",
    deterministico: bool = False,
    before_agent_callback: Any = None,
    after_agent_callback: Any = None,
    before_tool_callback: Any = None,
    after_tool_callback: Any = None,
) -> LlmAgent:
    """Cria um LlmAgent com ThinkingConfig e callbacks padronizados.

    Args:
        name: identificador único do agente (usado como `author` dos eventos).
        instruction: prompt de sistema; `{chave}` é interpolada do session.state pelo ADK.
        description: propósito do agente (observabilidade).
        output_key: chave do session.state onde a resposta final é gravada.
        tools: ferramentas/toolsets (ex.: McpToolset do Stitch).
        model: modelo Gemini (padrão: AppSettings.gemini_model).
        thinking_budget / include_thoughts: controle de raciocínio.
        include_contents: 'none' (padrão — o agente trabalha só com a instrução interpolada
            e o turno corrente) ou 'default' (recebe o histórico completo da conversa).
        deterministico: para quem emite VEREDITO. Fixa temperatura baixa e seed, de modo que
            dois gates sobre o mesmo artefato deem a mesma resposta — sem isso não há como
            medir se uma mudança de critério funcionou, e a matriz antes × depois de uma
            sessão vira ruído. Agentes que INVENTAM (núcleo, copy, telas) ficam de fora:
            achatar a amostragem deles aproxima as missões umas das outras, o que colide
            com o gate de semelhança do catálogo.
        before_agent_callback / after_agent_callback: callbacks do ADK.
        before_tool_callback / after_tool_callback: idem para ferramentas. Quando há
            `tools` e nada é passado, entram os limitadores de contexto de
            `agents.callbacks` — resposta de ferramenta MCP é a maior fonte de estouro
            do teto do modelo, e o histórico de chamada não é descartado por
            `include_contents="none"`.
    """
    # import tardio: `pipeline.reexecucao` importa `agents.callbacks`, que importa este módulo
    from pipeline.reexecucao import CHAVES_AUTORAIS, PREFIXO_ANTERIOR
    from tools.conteudo_aprovado import KEY_MUDANCAS

    settings = get_settings()
    selected_model = model or settings.gemini_model

    t_budget = thinking_budget if thinking_budget is not None else settings.thinking_budget
    inc_thoughts = include_thoughts if include_thoughts is not None else settings.include_thoughts

    kwargs: dict[str, Any] = {
        "name": name,
        "model": selected_model,
        # O bloco de herança entra em TODOS os agentes de uma vez, em vez de ser repetido em
        # ~30 prompts. Fica vazio na execução saudável; quando um gate reprova, é por ele que
        # o agente a jusante descobre que constrói sobre base reprovada — e é o que permite a
        # esteira seguir até o fim sem fingir que está tudo certo.
        # O pedido de correção segue o mesmo caminho: no modo correção (`pipeline/reexecucao.py`)
        # o app grava `pedido_correcao` no estado e todo agente o lê — autores aplicam no que é
        # seu, QA e banca conferem se foi atendido, o aprendizado registra. Vazio na execução normal.
        "instruction": (
            instruction.strip()
            + "\n\n---\n## Herança desta execução\n\n{heranca_degradada?}\n"
            + "\n---\n## Pedido de correção desta execução\n\n{pedido_correcao?}\n"
            # A versão que este autor escreveu antes, quando a etapa é refeita
            # (`pipeline/reexecucao.py`, CHAVES_AUTORAIS). Vazio na primeira execução; gate não tem.
            # E o que mudou no one-pager aprovado desde aquela versão (`tools.conteudo_aprovado.mudancas_no_aprovado`):
            # sem isso, depois de um refazer de produto, o autor mantinha «palavra por palavra» o número velho.
            + (f"\n{{{PREFIXO_ANTERIOR}{output_key}?}}\n\n{{{KEY_MUDANCAS}?}}\n" if output_key in CHAVES_AUTORAIS else "")
            # A versão que este autor escreveu na rodada anterior do loop, quando o gate reprovou
            # (`agents.checkers.SaidaDeLoopAgent.autor_keys`). Vazio na primeira rodada e fora dos loops.
            + (f"\n{{rodada_anterior_{output_key}?}}\n" if output_key in CHAVES_AUTORAIS else "")
            # Pareceres de quem responde por cada etapa já liberada (`pipeline/passagem.py`).
            # Vazio sem parecer humano ou na primeira etapa.
            + "\n---\n## Notas de passagem desta missão\n\n{notas_de_passagem?}\n"
            # O motivo de a tentativa anterior deste agente ter saído vazia — filtro de recitação, limite de tamanho
            # (`agents.callbacks.registrar_corte_do_modelo`). Vazio quase sempre.
            + f"\n{{bloqueio_modelo_{name}?}}\n"
            + f"\n---\nData de hoje: {time.strftime('%Y-%m-%d')}. Use esta data em cabeçalhos, changelogs e frontmatter."
        ),
        "description": description.strip(),
        "include_contents": include_contents,
    }

    thinking_params: dict[str, Any] = {}
    if t_budget is not None:
        thinking_params["thinking_budget"] = t_budget
    if inc_thoughts is not None:
        thinking_params["include_thoughts"] = inc_thoughts

    # O config é montado SEMPRE. Antes ele só existia quando havia `thinking_params`, e
    # qualquer outro parâmetro de geração passado por fora era descartado em silêncio —
    # incluindo temperatura e seed, que é o que torna o veredito de um gate reproduzível.
    config_params: dict[str, Any] = {}
    if thinking_params:
        config_params["thinking_config"] = types.ThinkingConfig(**thinking_params)

    # Retry com backoff exponencial e jitter, para todo agente. A esteira faz de 33 a 55
    # chamadas por execução e a banca dispara cinco validadores em paralelo: sem isto, um
    # 429 no meio derruba vinte minutos de trabalho e o estado parcial não é reaproveitável.
    if settings.tentativas_modelo > 1:
        config_params["http_options"] = types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                attempts=settings.tentativas_modelo,
                initial_delay=1.0,
                max_delay=60.0,
                exp_base=2.0,
                jitter=1.0,
                http_status_codes=[408, 429, 500, 502, 503, 504],
            )
        )

    if deterministico:
        config_params["temperature"] = settings.temperatura_juiz
        config_params["seed"] = settings.seed_juiz

    kwargs["generate_content_config"] = types.GenerateContentConfig(**config_params)

    if output_key:
        kwargs["output_key"] = output_key
    if tools:
        kwargs["tools"] = tools
        # Contenção padrão: sem ela, um agente que constrói artefato por MCP acumula
        # dezenas de respostas de ferramenta, dumps e imagens no mesmo turno, e o
        # modelo recusa a requisição com 400.
        from agents.callbacks import barrar_ferramenta_sem_orcamento, limitar_resposta_de_ferramenta

        kwargs["before_tool_callback"] = before_tool_callback or barrar_ferramenta_sem_orcamento
        kwargs["after_tool_callback"] = after_tool_callback or limitar_resposta_de_ferramenta
    else:
        if before_tool_callback is not None:
            kwargs["before_tool_callback"] = before_tool_callback
        if after_tool_callback is not None:
            kwargs["after_tool_callback"] = after_tool_callback
    from agents.callbacks import registrar_corte_do_modelo

    kwargs["after_model_callback"] = registrar_corte_do_modelo
    if before_agent_callback is not None:
        kwargs["before_agent_callback"] = before_agent_callback
    if after_agent_callback is not None:
        kwargs["after_agent_callback"] = after_agent_callback

    return LlmAgent(**kwargs)
