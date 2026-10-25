"""Gabarito de achados de produto: o estado real de cada execução classificada e os atalhos que os testes usam.

Correção C3 do backlog de 24/10/2026 (juízes e lints de produto), no molde do gabarito de dev da C1: cada falso positivo
(FP) classificado com evidência no levantamento de produto vira caso que NÃO pode disparar, e cada verdadeiro (V), caso
que TEM de disparar — com a execução, o documento e o trecho real. O trecho tem de existir no documento: caso cujo trecho
sumiu falha, nunca passa por vacuidade.

Os estados vêm de `estados_produto/<missão>-<sessão>.json.xz` (`extrair_estados_produto.py`), pelo id
`<sessão>:<momento>`, e os do acervo de regressão (`tests/acervo/<nome>/estado.json`) pelo id `acervo:<nome>`. Nomes
próprios, para não cruzar com o `gabarito_estados.py` da C1; o que for comum aos dois se unifica depois.
"""
from __future__ import annotations

import copy
import functools
import json
import lzma
from pathlib import Path
from typing import Any, Dict

from extrair_estados_produto import EXECUCOES, arquivo_da_sessao

ACERVO = Path(__file__).resolve().parent.parent / "acervo"


@functools.lru_cache(maxsize=None)
def _sessao(missao: str, sessao: str) -> Dict[str, Any]:
    return json.loads(lzma.decompress(arquivo_da_sessao(missao, sessao).read_bytes()).decode("utf-8"))


@functools.lru_cache(maxsize=None)
def _acervo(nome: str) -> Dict[str, Any]:
    return json.loads((ACERVO / nome / "estado.json").read_text(encoding="utf-8"))


def estado(execucao: str) -> Dict[str, Any]:
    """O estado da execução (`8ce9c32d:final`… ou `acervo:<nome>`), numa cópia: o teste pode mexer nele."""
    if execucao.startswith("acervo:"):
        return copy.deepcopy(_acervo(execucao.split(":", 1)[1]))
    missao, sessao, _, _ = EXECUCOES[execucao]
    return copy.deepcopy(_sessao(missao, sessao)["execucoes"][execucao]["estado"])


def rotulo(execucao: str) -> str:
    """`727a3c2d:final exp06ef1b` — a sessão, o momento e a missão."""
    if execucao.startswith("acervo:"):
        return execucao
    return f"{execucao} {EXECUCOES[execucao][0]}"


def exige(texto: str, trecho: str, onde: str) -> None:
    """O trecho do gabarito está no texto da execução — senão o caso passaria por vacuidade."""
    assert trecho in (texto or ""), f"o gabarito cita «{trecho}», que {onde} não tem"
