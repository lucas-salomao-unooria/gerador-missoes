"""Custo de uma missão em tokens, dólares e reais, somando todas as execuções dela.

O runner já contava os tokens por agente (`state["execucao"]`), mas cada execução sobrescrevia a anterior: depois de
um refazer, ninguém sabia quanto a missão tinha custado no total. `state["custo_missao"]` guarda uma linha por
execução (nova, iniciar etapa, refazer) e o total, e não sai do estado numa reexecução.

Preço: tabela Standard da API do Gemini (https://ai.google.dev/gemini-api/docs/pricing, consultada em 12/10/2026),
em dólares por 1 milhão de tokens. A saída inclui os tokens de pensamento. A entrada que veio do cache implícito
custa a tarifa de cache, não a cheia.

O real usa a cotação do momento da execução, nesta ordem: `COTACAO_USD_BRL` no ambiente (para fixar um valor); a PTAX
de venda mais recente do Banco Central (API pública Olinda, sem chave); o padrão, se a API não responder. A linha da
execução guarda a cotação e a fonte dela.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

KEY_CUSTO = "custo_missao"

#: `modelo → [(vale até, entrada, saída, entrada em cache)]`, em US$ por 1M de tokens. `None` = sem data final.
PRECOS: Dict[str, List[Tuple[Optional[date], float, float, float]]] = {
    "gemini-3.8-flash": [(date(2026, 12, 31), 0.75, 3.75, 0.075), (None, 1.50, 7.50, 0.15)],
    "gemini-3.6-flash": [(date(2026, 12, 31), 0.75, 3.75, 0.075), (None, 1.50, 7.50, 0.15)],
    "gemini-3-flash-preview": [(None, 0.50, 3.00, 0.05)],
}

logger = logging.getLogger(__name__)

#: Cotação de último recurso: sem `COTACAO_USD_BRL` e sem resposta da PTAX.
COTACAO_PADRAO = 5.50

_PTAX = ("https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo("
         "dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@dataInicial='{ini}'&@dataFinalCotacao='{fim}'"
         "&$top=100&$format=json&$select=cotacaoVenda,dataHoraCotacao")
#: `{dia: (cotação, fonte)}`: uma consulta por dia e por processo.
_CACHE_PTAX: Dict[date, Tuple[float, str]] = {}


def ptax_venda(hoje: Optional[date] = None, timeout: float = 5.0) -> Optional[Tuple[float, str]]:
    """`(cotação, "PTAX dd/mm/aaaa")` do último dia útil dos 10 anteriores; `None` se a API falhar."""
    hoje = hoje or date.today()
    if hoje in _CACHE_PTAX:
        return _CACHE_PTAX[hoje]
    url = _PTAX.format(ini=(hoje - timedelta(days=10)).strftime("%m-%d-%Y"), fim=hoje.strftime("%m-%d-%Y"))
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            valores = json.loads(resp.read().decode("utf-8")).get("value") or []
        ultimo = valores[-1]
        dia = ultimo["dataHoraCotacao"][:10].split("-")
        resultado = (float(ultimo["cotacaoVenda"]), f"PTAX {dia[2]}/{dia[1]}/{dia[0]}")
    except Exception as exc:  # sem rede ou API fora: o custo não pode derrubar a execução
        logger.warning("PTAX indisponível (%s); a cotação cai no padrão", exc)
        return None
    _CACHE_PTAX[hoje] = resultado
    return resultado


def cotacao_usd_brl() -> Tuple[float, str]:
    """`(cotação, fonte)`: o `.env` vence, depois a PTAX, depois o padrão."""
    fixa = os.getenv("COTACAO_USD_BRL", "").strip()
    if fixa:
        try:
            return float(fixa.replace(",", ".")), "COTACAO_USD_BRL"
        except ValueError:
            logger.warning("COTACAO_USD_BRL inválida: %r", fixa)
    return ptax_venda() or (COTACAO_PADRAO, "padrão (PTAX indisponível)")


def preco(modelo: str, dia: Optional[date] = None) -> Optional[Tuple[float, float, float]]:
    """`(entrada, saída, cache)` em US$/1M do modelo no dia; `None` se o modelo não está na tabela."""
    faixas = PRECOS.get((modelo or "").strip().lower())
    if not faixas:
        return None
    dia = dia or date.today()
    for ate, entrada, saida, cache in faixas:
        if ate is None or dia <= ate:
            return entrada, saida, cache
    return faixas[-1][1:]


def custo_usd(tokens: Dict[str, int], modelo: str, dia: Optional[date] = None) -> Optional[float]:
    """Dólares de um bloco `{entrada, saida, pensamento, cache}`. `entrada` já inclui a parte em cache."""
    p = preco(modelo, dia)
    if p is None:
        return None
    entrada, saida, cache = p
    em_cache = min(int(tokens.get("cache", 0) or 0), int(tokens.get("entrada", 0) or 0))
    cheia = int(tokens.get("entrada", 0) or 0) - em_cache
    gerada = int(tokens.get("saida", 0) or 0) + int(tokens.get("pensamento", 0) or 0)
    return (cheia * entrada + em_cache * cache + gerada * saida) / 1_000_000


def _soma(blocos: List[Dict[str, int]]) -> Dict[str, int]:
    chaves = ("entrada", "saida", "pensamento", "cache", "chamadas")
    return {k: sum(int(b.get(k, 0) or 0) for b in blocos) for k in chaves}


def custo_da_execucao(tokens_por_agente: Dict[str, Dict[str, int]], modelo: str, modelo_por_agente: Dict[str, str],
                      dia: Optional[date] = None) -> Dict[str, Any]:
    """Tokens e custo de uma execução, cada agente pelo modelo dele (o redator do PRD pode usar outro)."""
    usd, sem_preco = 0.0, set()
    for agente, tokens in tokens_por_agente.items():
        m = modelo_por_agente.get(agente, modelo)
        c = custo_usd(tokens, m, dia)
        if c is None:
            sem_preco.add(m)
        else:
            usd += c
    cotacao, fonte = cotacao_usd_brl()
    # Os tokens por agente vão junto, em cada linha de `custo_missao.execucoes`: o `execucao` do estado é só o da última
    # execução, e nas missões do e2e de 25/10/2026 só sobrava o A128Aprendizado (G19)
    return {"tokens": _soma(list(tokens_por_agente.values())), "usd": round(usd, 4), "cotacao": cotacao,
            "fonte_cotacao": fonte,
            "brl": round(usd * cotacao, 2), "modelos_sem_preco": sorted(sem_preco),
            "tokens_por_agente": {a: dict(t) for a, t in tokens_por_agente.items()}}


def acumular(anterior: Optional[Dict[str, Any]], execucao: Dict[str, Any], etapas: List[str],
             quando: Optional[float] = None) -> Dict[str, Any]:
    """`custo_missao` com a execução nova somada às anteriores."""
    linhas = list((anterior or {}).get("execucoes") or [])
    linhas.append({"quando": time.strftime("%d/%m/%Y %H:%M", time.localtime(quando or time.time())),
                   "etapas": list(etapas), **execucao})
    return {"execucoes": linhas,
            "total": {"tokens": _soma([l.get("tokens") or {} for l in linhas]),
                      "usd": round(sum(float(l.get("usd") or 0) for l in linhas), 4),
                      "brl": round(sum(float(l.get("brl") or 0) for l in linhas), 2)}}


def brl(valor: float) -> str:
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def milhares(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def texto_ao_vivo(execucao: Optional[Dict[str, Any]], missao_antes: Optional[Dict[str, Any]]) -> str:
    """`💰 R$ 3,42 nesta execução · R$ 18,90 na missão · 1.234.567 de entrada · 85.432 de saída`."""
    if not execucao:
        return ""
    t = execucao.get("tokens") or {}
    agora = float(execucao.get("brl") or 0)
    total = agora + float((missao_antes or {}).get("brl") or 0)
    saida = int(t.get("saida") or 0) + int(t.get("pensamento") or 0)
    return (f"💰 {brl(agora)} nesta execução · {brl(total)} na missão · {milhares(int(t.get('entrada') or 0))} de "
            f"entrada · {milhares(saida)} de saída")
