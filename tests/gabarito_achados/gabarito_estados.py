"""Gabarito de achados: o estado real de cada execução classificada e os atalhos que os testes usam.

Semente da C6 do backlog de correções de 24/10/2026: cada falso positivo (FP) classificado com evidência vira caso que
NÃO pode disparar, e cada verdadeiro (V), caso que TEM de disparar — com a execução (missão e sessão), o documento e o
trecho real. Um arquivo por etapa e regra (`test_<etapa>_<regra>.py`). O trecho tem de existir no documento: caso cujo
trecho sumiu falha, nunca passa por vacuidade.

Os estados vêm de `estados/<missão>-<sessão>.json.xz` (`extrair_estados.py`), e os do acervo de regressão
(`tests/acervo/<nome>/estado.json`) pelo id `acervo:<nome>`.
"""
from __future__ import annotations

import functools
import json
import lzma
import re
from pathlib import Path
from typing import Any, Dict, List

from extrair_estados import EXECUCOES, arquivo_da_sessao

ACERVO = Path(__file__).resolve().parent.parent / "acervo"
DOCUMENTO = {"prd": "prd_final", "handoff": "handoff_dev"}


@functools.lru_cache(maxsize=None)
def _sessao(missao: str, sessao: str) -> Dict[str, Any]:
    return json.loads(lzma.decompress(arquivo_da_sessao(missao, sessao).read_bytes()).decode("utf-8"))


def estado(execucao: str) -> Dict[str, Any]:
    """O estado da execução (`R01`…`R13`, ou `acervo:<nome>`), numa cópia rasa: o gate não grava nele."""
    if execucao.startswith("acervo:"):
        return json.loads((ACERVO / execucao.split(":", 1)[1] / "estado.json").read_text(encoding="utf-8"))
    missao, sessao, _, _ = EXECUCOES[execucao]
    return dict(_sessao(missao, sessao)["execucoes"][execucao]["estado"])


def rotulo(execucao: str) -> str:
    """`R03 exp04ef1b-8ce9c32d` — o id do levantamento e a missão-sessão."""
    if execucao.startswith("acervo:"):
        return execucao
    missao, sessao, _, _ = EXECUCOES[execucao]
    return f"{execucao} {missao}-{sessao}"


def corpo(execucao: str, documento: str) -> str:
    """O corpo do PRD ou do handoff, sem o anexo literal que a esteira cola no fim."""
    from tools.cobertura_design import corpo_do_prd

    return corpo_do_prd(str(estado(execucao).get(DOCUMENTO[documento]) or ""))


def inicios_das_linhas_com(execucao: str, documento: str, trecho: str) -> List[str]:
    """Os começos (180 caracteres, como o achado guarda) das linhas do documento que contêm o trecho. Trecho que o
    documento não tem é erro do gabarito."""
    inicios = [re.sub(r"\s+", " ", l).strip()[:180] for l in corpo(execucao, documento).splitlines() if trecho in l]
    assert inicios, f"o gabarito cita «{trecho}», que o {documento} de {rotulo(execucao)} não tem"
    return inicios


@functools.lru_cache(maxsize=None)
def achados_da_montagem(execucao: str, documento: str) -> List[Dict[str, str]]:
    from tools import montagem

    st = estado(execucao)
    return (montagem.validar_prd(st) if documento == "prd" else montagem.validar_handoff(st))["achados"]


@functools.lru_cache(maxsize=None)
def achados_do_prd(execucao: str) -> List[Dict[str, str]]:
    """Os achados do A114 sobre o PRD: o rastro (`tools/rastro.py`) e o PRD codável (`tools/prd_codavel.py`)."""
    from tools import prd_codavel, rastro
    from tools.anexo_design import spec_consolidada

    st = estado(execucao)
    spec = spec_consolidada(st)
    prd, banco = str(st.get("prd_final") or ""), str(st.get("banco_conteudo") or "")
    return (rastro.validar_prd(prd, spec=spec, banco=banco, aprovado=str(st.get("one_pager") or ""))["achados"]
            + prd_codavel.validar(prd, spec, banco, handoff=str(st.get("handoff_dev") or ""))["achados"])
