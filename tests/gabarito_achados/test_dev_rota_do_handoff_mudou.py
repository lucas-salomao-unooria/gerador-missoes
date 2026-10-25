"""Gabarito do `rota-do-handoff-mudou` (A114 — `tools/prd_codavel.py`): rota do handoff que o PRD não repete. Nas 13
execuções de dev de 25/09 a 23/10/2026 eram 35 rotas em 9 achados, 29 delas falsas (diagnóstico C1, 24/10/2026): o
mesmo caminho com outro nome de parâmetro (`:id` × `:turmaId`), o intervalo `p1..p3` do de-para da seção 19 e rota da
plataforma (índice `openapi-rotas.json` da base), que o PRD não precisa repetir. Ficam as 6 verdadeiras — inclusive o
`POST` numa rota que a plataforma tem como `PUT` —, mais a que o atalho literal escondia: ele conferia só o caminho, e
`GET /exp09ef1b/sessoes/:id` passava por estar dentro de `POST /exp09ef1b/sessoes/:id/evento` (terceira revisão do PR
#77; é a troca por `GET /exp09ef1b/sessao` que a auditoria do padrão ouro de 08/10/2026 já apontava).
"""
from __future__ import annotations

import pytest

from gabarito_estados import achados_do_prd, rotulo

FP = {
    "R01": ["POST /telemetry/batch", "POST /observabilidade/vitals"],
    "R05": ["PUT /salas/turma/:turmaId/missoes/exp01ef1b"],
    "R07": ["GET /turmas/minhas", "GET /evidencias/exp01ef1b/perguntas/:id"],
    "R08": ["POST /observabilidade/erros-cliente"],
    "R09": ["POST /evidencias/:exp/perguntas/p2", "POST /evidencias/:exp/perguntas/p3"],
    "R11": ["POST /efeito-amplificador/turmas/:id/gate", "POST /telemetry/batch", "PUT /salas/"],
    "R12": ["POST /efeito-amplificador/turmas/:id/homologar", "POST /observabilidade/vitals"],
}
V = {
    "R04": ["GET /exp06ef1b/turmas/:turmaId/conteudo", "POST /exp06ef1b/sessoes/:sessaoId/etapa"],
    "R06": ["POST /foto-misteriosa/gerar-conteudo", "POST /foto-misteriosa/homologar",
            "POST /salas/turma/:turmaId/missoes/exp01ef1b"],
    "R08": ["GET /exp09ef1b/sessoes/:id", "POST /exp09ef1b/turmas/:turmaId/zerar"],
}


def _rotas(execucao: str) -> str:
    return " ".join(a["resumo"] for a in achados_do_prd(execucao) if a["codigo"] == "rota-do-handoff-mudou")


@pytest.mark.parametrize("execucao", sorted(FP), ids=rotulo)
def test_fp_rota_normalizada_ou_da_plataforma_nao_dispara(execucao):
    texto = _rotas(execucao)
    assert not [r for r in FP[execucao] if r in texto], texto


@pytest.mark.parametrize("execucao", sorted(V), ids=rotulo)
def test_v_rota_mudada_dispara(execucao):
    texto = _rotas(execucao)
    assert all(f"`{r}`" in texto for r in V[execucao]), texto
    # e só elas: as 7 verdadeiras, nenhuma rota a mais
    assert texto.count("`") // 2 == len(V[execucao]), texto


@pytest.mark.parametrize("execucao, caminho", (
    ("R04", "/exp06ef1b/turmas/:turmaId/gerar-conteudo"),
    ("R08", "/exp09ef1b/turmas/:turmaId/homologar"),
    ("R10", "/evidencias/:exp/perguntas/p1"),
), ids=lambda x: x)
def test_v_prd_que_troca_so_o_verbo_da_rota_dispara(execucao, caminho):
    """O atalho literal olhava só o caminho: com o caminho igual e o verbo trocado no PRD (`POST` → `PUT`), a rota nunca
    chegava à comparação por método (terceira revisão do PR #77)."""
    from gabarito_estados import estado
    from tools import prd_codavel

    st = estado(execucao)
    prd, handoff = st["prd_final"], st["handoff_dev"]
    assert f"POST {caminho}" in handoff and (f"POST {caminho}" in prd or f"POST `{caminho}" in prd)
    trocado = prd.replace(f"POST {caminho}", f"PUT {caminho}").replace(f"POST `{caminho}", f"PUT `{caminho}")
    rotas = " ".join(a["resumo"] for a in prd_codavel.handoff_no_prd(trocado, handoff)
                     if a["codigo"] == "rota-do-handoff-mudou")
    assert f"`POST {caminho}`" in rotas, rotas
