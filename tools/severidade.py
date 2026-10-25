"""Política de severidade: só o que o código prova bloqueia (C7, aprovado em 25/10/2026).

Um 🔴 recusa o de acordo e manda o autor reescrever. Ele só vale quando o código **prova** o defeito: comparação literal
sobre dado estruturado ou texto (igualdade, presença, ausência, diff de linhas, ID, marcador, coluna) — o número do §17
que não está no corpo, a linha da versão anterior que saiu, o código BNCC que não existe. Quando decidir **se** há
defeito depende de ler sentido em texto livre — a porcentagem é meta ou mecânica? o número é «de regra»? a frase do
pedido é exigência ou contexto? a guarda do fluxo exige acerto? —, é interpretação, de regex heurística ou de LLM, e
vai ao PO como 🟡 «a conferir», com a dúvida explicada no achado.

Por quê, com os dados: os gates determinísticos de produto tinham 59% de falso positivo (levantamento de 24/10/2026), a
maior parte de regex de sentido; e cada revisão da C1 e da C3 achou um furo novo nessas regras (fase A da C7: a 1ª
versão da leitura meta × mecânica tinha revocação 0,12 nas paráfrases que a revisão seguinte escreveu). O LLM erra
menos, mas também erra (as 2 falas de personagem lidas como fala no held-out de texto de tela): nenhum dos dois
bloqueia sozinho. As duas leituras juntas — o código e o classificador lendo o mesmo — bastam para o 🔴 só onde a fase A
mediu o classificador (`leitura_dupla`); a discordância é 🟡 com as duas leituras à vista.

O que vira 🟡 por esta política, regra a regra, está no PR da C7 e no README («Política de severidade»).
"""
from __future__ import annotations

from typing import Any

BLOQUEIO = "bloqueio"
ATENCAO = "atencao"
DECISAO_HUMANA = "decisao_humana"

#: Como o achado se sustenta: `PROVA` (comparação literal em código) ou `INTERPRETACAO` (leitura de sentido).
PROVA = "prova"
INTERPRETACAO = "interpretacao"

#: O que `leitura_dupla` devolve.
CONCORDAM_SIM = "concordam_sim"
CONCORDAM_NAO = "concordam_nao"
DUVIDA = "duvida"


def por_prova(severidade: str, sustentacao: str, rebaixada: str = ATENCAO) -> str:
    """A severidade que o achado pode ter: o bloqueio sustentado só por interpretação cai para `rebaixada` (🟡, ou a
    decisão de uma pessoa); o resto fica como veio."""
    if severidade == BLOQUEIO and sustentacao != PROVA:
        return rebaixada
    return severidade


def leitura_dupla(codigo_le: bool, leitura: Any, positivo: str) -> str:
    """O código e o classificador leem a mesma coisa? `CONCORDAM_SIM` quando os dois leem `positivo`, `CONCORDAM_NAO`
    quando nenhum lê, `DUVIDA` quando discordam ou o classificador não respondeu («nao_sei», erro, sem chave, fora do
    cache): sem as duas leituras, ninguém decide sozinho."""
    rotulo = getattr(leitura, "rotulo", "nao_sei")
    if rotulo == "nao_sei":
        return DUVIDA
    if codigo_le and rotulo == positivo:
        return CONCORDAM_SIM
    if not codigo_le and rotulo != positivo:
        return CONCORDAM_NAO
    return DUVIDA
