"""Gabarito do `coluna-da-spec-ausente` (A114 — `tools/consistencia.py`). Na exp02em1b, a linha da seção de design
system da spec «| `unooriaai` | Sem memória contínua …; sem navegação livre e irrestrita na internet real; … |»
declarava a coluna `unooriaai` do tipo REAL (o «real» da prosa), e o mesmo com `unoovista`: 4 FP em 2 execuções
(diagnóstico C1, 24/10/2026). O tipo tem de abrir a célula; a coluna da DDL e da tabela de modelo continua cobrada.
"""
from __future__ import annotations

import pytest

from gabarito_estados import achados_do_prd, estado, rotulo
from tools import consistencia


@pytest.mark.parametrize("execucao", ["R11", "R12"], ids=rotulo)
def test_fp_secao_do_design_system_nao_e_coluna(execucao):
    from tools.anexo_design import spec_consolidada

    assert "internet real" in spec_consolidada(estado(execucao))
    resumos = " ".join(a["resumo"] for a in achados_do_prd(execucao) if a["codigo"] == "coluna-da-spec-ausente")
    assert "`unooriaai`" not in resumos and "`unoovista`" not in resumos


@pytest.mark.parametrize("spec", [
    'CREATE TABLE "exp06ef1b_sessoes" (\n  turma_id UUID NOT NULL,\n  coluna_faltando INT NOT NULL\n);',
    "| Coluna | Tipo |\n|---|---|\n| `coluna_faltando` | `INTEGER NOT NULL` |\n",
    "| `coluna_faltando` | real |\n",
])
def test_v_coluna_da_spec_ausente_do_prd_dispara(spec):
    prd = 'CREATE TABLE "exp06ef1b_sessoes" (\n  "turma_id" UUID NOT NULL\n);'
    assert any(a["codigo"] == "coluna-da-spec-ausente" for a in consistencia.conferir_colunas(prd, spec)), spec
