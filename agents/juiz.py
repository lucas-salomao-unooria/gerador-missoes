"""Fábrica do juiz de achados: o par (agente que aplica + juiz de LLM), uma instância por ponto.

Um agente do ADK tem um único pai na árvore, então cada gate que recebe juiz ganha o seu.
"""
from __future__ import annotations

from typing import Optional

from agents.base import create_llm_agent
from agents.checkers import FidelidadeCheckAgent, JuizDeAchadosAgent, JuizDeContradicoesAgent
from config import get_settings
from prompts import load_prompt


def get_juiz_de_achados(nome: str, *, status_key: str, report_key: str, fonte_key: str,
                        gate_rotulo: str, **kw) -> JuizDeAchadosAgent:
    base = status_key.removesuffix("_status")
    juiz = create_llm_agent(
        name=f"{nome}Llm",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description=f"Lê as linhas que o gate `{gate_rotulo}` marcou e decide, com citação, se o texto afirma o uso do que a plataforma veda ou só cita para vedar.",
        instruction=load_prompt("transversal/juiz_de_achados.md"),
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


def get_fidelidade_check(nome: str, *, status_key: str, report_key: str, documentos: list,
                         onde: str, etapas_pedido: Optional[list] = None, com_briefing: bool = True,
                         etapa: str = "produto", incluir_corrente: bool = True, parcial: bool = False,
                         **kw) -> FidelidadeCheckAgent:
    """O par (verificador de fidelidade + juiz), uma instância por ponto da esteira.

    `etapas_pedido` restringe o checklist aos pedidos de refazer daquelas etapas (no fim do design, os do
    design); sem ele, entram todos. `incluir_corrente` soma o pedido desta execução; `com_briefing`, o briefing."""
    base = status_key.removesuffix("_status")
    juiz = create_llm_agent(
        name=f"{nome}Juiz",
        deterministico=True,  # emite veredito: mesmo artefato, mesma resposta
        description="Confere item a item, com citação literal, se os documentos fazem o que o PO pediu e o briefing fixou.",
        instruction=load_prompt("transversal/juiz_de_fidelidade.md"),
        output_key=f"juiz_{base}_saida",
        **kw,
    )
    kw_interprete = dict(kw)
    if kw_interprete.get("thinking_budget") is None:
        kw_interprete["thinking_budget"] = get_settings().thinking_budget_curto
    interprete = create_llm_agent(
        name=f"{nome}Interprete",
        deterministico=True,  # lê o pedido: mesmo pedido, mesma leitura
        description="Lê só o pedido do PO e separa, item a item, o texto que ele ditou do texto que mandou tirar — qualquer verbo, com ou sem aspas.",
        instruction=load_prompt("transversal/interprete_do_pedido.md"),
        output_key=f"interpretacao_{base}_saida",
        **kw_interprete,
    )
    return FidelidadeCheckAgent(
        parcial=parcial,
        name=nome,
        description=(f"Fidelidade ao pedido do PO e ao briefing ({onde}): TRAVAS, AJUSTES, VALIDAÇÃO e elementos "
                     "fixos conferidos com citação; pedido sem prova é 🔴."),
        status_key=status_key, report_key=report_key, documentos=list(documentos), onde=onde,
        etapas_pedido=list(etapas_pedido or []), com_briefing=com_briefing, etapa=etapa,
        incluir_corrente=incluir_corrente,
        sub_agents=[juiz, interprete],
    )


def get_juiz_de_contradicoes(nome: str, *, documento_key: str, referencia_key: str, report_key: str, status_key: str,
                             dono: str, rotulo: str, etapa: str = "dev", **kw) -> JuizDeContradicoesAgent:
    """O par (verificador + juiz de contradições), uma instância por ponto da esteira. `etapa` é a dona do documento
    (o pedagógico é do design desde o PR 10)."""
    base = status_key.removesuffix("_status")
    juiz = create_llm_agent(
        name=f"{nome}Juiz",
        deterministico=True,  # emite veredito: mesmo documento, mesma resposta
        description="Aponta, citando os dois lados, onde o documento afirma o contrário do conteúdo aprovado.",
        instruction=load_prompt("transversal/juiz_de_contradicoes.md"),
        output_key=f"juiz_{base}_saida",
        **kw,
    )
    return JuizDeContradicoesAgent(
        name=nome,
        description=f"{rotulo}: o juiz cita os dois lados de cada contradição, o código confere as citações; comprovada é bloqueio para `{dono}`.",
        documento_key=documento_key, referencia_key=referencia_key, report_key=report_key, status_key=status_key,
        dono=dono, rotulo=rotulo, etapa=etapa, sub_agents=[juiz],
    )
