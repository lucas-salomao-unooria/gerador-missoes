"""Gabarito do `agendamento-inexistente` e do `evidencia-tabela-propria` (A101 handoff e A114 PRD —
`tools/conferir_prd_plataforma.py`). O levantamento de 24/10/2026 classificou como falso positivo três linhas
negativas da exp01ef1b — «Removidas do DDL de `exp01ef1b_sessoes` as colunas `score_artefato`…», «Eliminação de menções
a agendamento (ADR-146)» e «**NÃO** implementar agendamento» —, que a main já não acusa desde antes de ecc61e2 (a
negação está em `_RE_PROIBICAO`). Nenhuma correção: o gabarito trava as duas pontas, a linha negativa que não dispara
e a afirmativa que dispara.
"""
from __future__ import annotations

from gabarito_estados import achados_do_prd, estado
from tools import conferir_prd_plataforma as plataforma
from tools import rastro
from tools.conteudo_aprovado import remover_anexo

CODIGOS = ("agendamento-inexistente", "evidencia-tabela-propria")


def _linhas_que_disparam(execucao: str, chave: str):
    texto = str(estado(execucao).get(chave) or "")
    texto = remover_anexo(texto) if chave == "prd_final" else texto
    return [l for l in plataforma._linhas_afirmativas(texto)
            if plataforma._RE_AGENDA.search(l) or plataforma._RE_TABELA_PROPRIA.search(l)]


def test_fp_negacao_da_exp01ef1b_nao_dispara():
    handoff = str(estado("R07").get("handoff_dev") or "")
    assert "Eliminação de menções a agendamento" in handoff and "score_artefato" in handoff
    assert not _linhas_que_disparam("R07", "handoff_dev") and not _linhas_que_disparam("R07", "prd_final")
    assert not [a for a in rastro.validar_telemetria(handoff)["achados"] if a["codigo"] in CODIGOS]
    assert not [a for a in achados_do_prd("R07") if a["codigo"] in CODIGOS]


def test_v_agendamento_e_tabela_de_enquete_afirmativos_disparam():
    assert any("Agendar para Data Futura" in l for l in _linhas_que_disparam("R04", "handoff_dev"))
    assert any("seletor de agendamento" in l for l in _linhas_que_disparam("R08", "handoff_dev"))
    assert any("CREATE TABLE exp09ef1b_respostas_poll" in l for l in _linhas_que_disparam("R08", "handoff_dev"))
    codigos = {a["codigo"] for a in rastro.validar_telemetria(str(estado("R08").get("handoff_dev") or ""))["achados"]}
    assert set(CODIGOS) <= codigos
