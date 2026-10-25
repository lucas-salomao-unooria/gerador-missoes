"""Gabarito do `teto-ausente` (A116b — `tools/montagem.py`): o teto do §15 do one-pager que o PRD não traz. Os casos
reais das 7 execuções de dev que o PO viu (diagnóstico C1, 24/10/2026) são todos verdadeiros — as 35 palavras da
exp06ef1b e os 8 e 15 min de tela — e TÊM de continuar bloqueando depois da calibragem do `numero-sem-origem`. O
`25 minutos` do PRD da exp04ef1b não é o «15 minutos» do §15.
"""
from __future__ import annotations

import pytest

from gabarito_estados import achados_da_montagem, rotulo

V = [
    ("R03", "15 min", "o PRD diz «25 minutos»; o §15 diz 15 min de tela sem pausa mediada"),
    ("R04", "8 min", "duração por ato em tela"),
    ("R04", "35 palavras", "balões de notificação da comissão"),
    ("R08", "8 min", "duração por ato em tela"),
    ("R10", "35 palavras", "balões de notificação da comissão (exp06ef1b-53e011b6)"),
    ("R12", "15 min", "tempo contínuo em tela"),
]


@pytest.mark.parametrize("caso", V, ids=lambda c: f"{rotulo(c[0])}/{c[1]}")
def test_v_teto_do_15_ausente_bloqueia(caso):
    execucao, teto, motivo = caso
    assert any(a["codigo"] == "teto-ausente" and a["severidade"] == "bloqueio" and f"({teto})" in a["resumo"]
               for a in achados_da_montagem(execucao, "prd")), f"{rotulo(execucao)}: {teto} ({motivo})"
