"""Gabarito do `tarefa-nao-atomica` (A114 — `tools/rastro.py`). Nas 13 execuções de dev de 25/09 a 23/10/2026 a regra
só acusou suíte de testes de ponta a ponta, que cobre todos os RFs por definição (diagnóstico C1, 24/10/2026): 5 FP.
A tarefa de implementação que fecha tudo continua cobrada — inclusive quando a coluna de teste dela cita e2e.
"""
from __future__ import annotations

import pytest

from gabarito_estados import achados_do_prd, inicios_das_linhas_com, rotulo
from tools import rastro

FP = [
    ("R01", "T-010", "Escrever suíte de testes ponta a ponta (E2E) com Playwright"),
    ("R03", "T-013", "Suíte E2E automatizada de estudante e professor"),
    ("R11", "T-013", "Implementar suíte de testes de ponta a ponta (e2e Playwright)"),
    ("R12", "T-013", "Implementar suíte de testes de ponta a ponta (e2e Playwright)"),
    ("R13", "T-016", "Construir suíte de testes de ponta a ponta (e2e) estudante/professor"),
]


@pytest.mark.parametrize("caso", FP, ids=lambda c: f"{rotulo(c[0])}/{c[1]}")
def test_fp_suite_e2e_nao_dispara(caso):
    execucao, tarefa, trecho = caso
    assert inicios_das_linhas_com(execucao, "prd", trecho)
    assert not [a for a in achados_do_prd(execucao) if a["codigo"] == "tarefa-nao-atomica"]


@pytest.mark.parametrize("linha", [
    "| `T-005` | Implementar serviço | RF-001..RF-014 | src/api.ts |",
    "| T-005 | Implementar o módulo da missão | RF-001..RF-014 | src/x.ts | `scripts/e2e/estudante/03.mjs` |",
    "| T-009 | Implementar todas as telas | Todos os RFs | apps/experiencias/x |",
])
def test_v_tarefa_de_implementacao_que_fecha_tudo_dispara(linha):
    assert [a for a in rastro.validar_prd(linha)["achados"] if a["codigo"] == "tarefa-nao-atomica"], linha
