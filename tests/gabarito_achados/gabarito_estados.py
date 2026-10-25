"""Gabarito de achados: o estado real de cada execução classificada e os atalhos que os testes usam.

Semente da C6 do backlog de correções de 24/10/2026: cada falso positivo (FP) classificado com evidência vira caso que
NÃO pode disparar, e cada verdadeiro (V), caso que TEM de disparar — com a execução (missão e sessão), o documento e o
trecho real. Um arquivo por etapa e regra (`test_<etapa>_<regra>.py`). O trecho tem de existir no documento: caso cujo
trecho sumiu falha, nunca passa por vacuidade.

Os estados vêm de `estados/<missão>-<sessão>.json.xz` (`extrair_estados.py`), e os do acervo de regressão
(`tests/acervo/<nome>/estado.json`) pelo id `acervo:<nome>`. As execuções de dev são `R01`…`R13`; as de design que não
estão no acervo, `D01`… (C4, 24/10/2026).
"""
from __future__ import annotations

import functools
import json
import lzma
import re
from pathlib import Path
from typing import Any, Dict, List

from extrair_estados import EXECUCOES, EXECUCOES_DESIGN, arquivo_da_sessao

ACERVO = Path(__file__).resolve().parent.parent / "acervo"
DOCUMENTO = {"prd": "prd_final", "handoff": "handoff_dev"}


@functools.lru_cache(maxsize=None)
def _sessao(missao: str, sessao: str) -> Dict[str, Any]:
    return json.loads(lzma.decompress(arquivo_da_sessao(missao, sessao).read_bytes()).decode("utf-8"))


def _execucao(execucao: str):
    return EXECUCOES.get(execucao) or EXECUCOES_DESIGN[execucao]


def estado(execucao: str) -> Dict[str, Any]:
    """O estado da execução (`R01`…`R13`, `D01`…, ou `acervo:<nome>`), numa cópia rasa: o gate não grava nele."""
    if execucao.startswith("acervo:"):
        return json.loads((ACERVO / execucao.split(":", 1)[1] / "estado.json").read_text(encoding="utf-8"))
    missao, sessao, _, _ = _execucao(execucao)
    return dict(_sessao(missao, sessao)["execucoes"][execucao]["estado"])


def rotulo(execucao: str) -> str:
    """`R03 exp04ef1b-8ce9c32d` — o id do levantamento e a missão-sessão."""
    if execucao.startswith("acervo:"):
        return execucao
    missao, sessao, _, _ = _execucao(execucao)
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


# --------------------------------------------------------------------------- design (C4, 24/10/2026)
def linhas_com(execucao: str, chave: str, trecho: str) -> List[str]:
    """As linhas do documento `chave` do estado que contêm o trecho. Trecho que o documento não tem é erro do gabarito."""
    linhas = [l for l in str(estado(execucao).get(chave) or "").splitlines() if trecho in l]
    assert linhas, f"o gabarito cita «{trecho}», que `{chave}` de {rotulo(execucao)} não tem"
    return linhas


@functools.lru_cache(maxsize=None)
def achados_de_consistencia(execucao: str) -> List[Dict[str, str]]:
    """Os achados do A082 (coerência entre documentos): o glossário canônico, a copy e o Canal B — o que o gate grava em
    `consistencia_status`."""
    from tools import consistencia, conteudo_aprovado

    st = estado(execucao)
    one_pager = str(st.get("one_pager") or "")
    return (consistencia.validar_estado(st)["achados"]
            + conteudo_aprovado.validar_copy(str(st.get("copy_strings_revisada") or ""), one_pager)
            + conteudo_aprovado.validar_literais_design(str(st.get("camada_caa") or ""),
                                                         str(st.get("prototipo_arquivo") or ""), one_pager))


def rotulos_divergentes(execucao: str) -> List[str]:
    """Os resumos dos `rotulo-divergente` da execução."""
    return [a["resumo"] for a in achados_de_consistencia(execucao) if a["codigo"] == "rotulo-divergente"]


@functools.lru_cache(maxsize=None)
def textos_de_tela_perdidos(execucao: str) -> Dict[str, List[str]]:
    """`{coluna: [texto]}` dos textos de tela do §4 que a matriz de rastreabilidade (A093) dá como perdidos na copy e no
    protótipo."""
    from tools import rastreabilidade

    r = rastreabilidade.matriz(estado(execucao))
    perdidos: Dict[str, List[str]] = {"copy": [], "prototipo": []}
    for req in r["requisitos"]:
        if req["categoria"] != "texto_tela":
            continue
        for coluna in perdidos:
            if r["celulas"][req["id"]].get(coluna) is False:
                perdidos[coluna].append(req["texto"])
    return perdidos


def textos_de_tela_exigidos(execucao: str) -> List[str]:
    """Os textos de tela do §4 que a matriz exige (`conteudo_aprovado.textos_de_tela`)."""
    from tools import conteudo_aprovado

    return conteudo_aprovado.textos_de_tela(str(estado(execucao).get("one_pager") or ""))


def rodar(inicial: Dict[str, Any], *agentes: Any) -> Dict[str, Any]:
    """Os agentes determinísticos em sequência sobre o estado `inicial`, sem modelo; devolve o estado final."""
    import asyncio

    from google.adk.agents.base_agent import BaseAgent
    from google.adk.agents.sequential_agent import SequentialAgent
    from google.adk.events import Event, EventActions
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    class Semente(BaseAgent):
        async def _run_async_impl(self, ctx):
            yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta=inicial))

    async def executar() -> Dict[str, Any]:
        runner = InMemoryRunner(agent=SequentialAgent(name="R", sub_agents=[Semente(name="S"), *agentes]), app_name="g")
        sessao = await runner.session_service.create_session(app_name="g", user_id="u", session_id="s")
        async for _ in runner.run_async(user_id="u", session_id=sessao.id,
                                        new_message=types.Content(role="user", parts=[types.Part(text="go")])):
            pass
        return dict((await runner.session_service.get_session(app_name="g", user_id="u", session_id="s")).state)

    return asyncio.run(executar())


@functools.lru_cache(maxsize=None)
def remontar(execucao: str) -> Dict[str, Any]:
    """O split do D0 e do D9 de novo sobre as respostas gravadas, com o código de agora: a spec do Gate 0, a resposta do D0
    (`fechamento_lacunas`) e a do D9 (`ambiente_simulado`) — como o `test_perdas_silenciosas._remontar`."""
    from agents.design import get_ambiente_simulado_split, get_fecha_lacunas_split

    st = estado(execucao)
    inicial = {k: v for k, v in st.items()
               if not k.startswith(("lacunas_status", "ambiente_status", "base_preservada", "spec_missao_gate0"))}
    inicial["spec_missao"] = st["spec_missao_gate0"]
    d0, d9 = get_fecha_lacunas_split(), get_ambiente_simulado_split()
    d0.estrito = d9.estrito = False
    return rodar(inicial, d0, d9)


def achados_do_split(execucao: str) -> List[Dict[str, Any]]:
    """Os achados do split do D0 (`lacunas_status`) e do D9 (`ambiente_status`) refeito (`remontar`)."""
    st = remontar(execucao)
    return [a for chave in ("lacunas_status_envelope", "ambiente_status_envelope")
            for a in (st.get(chave) or {}).get("achados") or []]
