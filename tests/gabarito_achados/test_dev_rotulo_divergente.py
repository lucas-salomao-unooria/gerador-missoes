"""Gabarito do `rotulo-divergente` no PRD (A114 — `tools/consistencia.py`). Na exp02em1b, o critério de aceite do botão
de publicar «… aciona o botão de publicação, O SISTEMA DEVE emitir `EVT-003` … e disparar a transição para
`unoovista`» acusava o nome de estado como rótulo do botão: 2 FP (diagnóstico C1, 24/10/2026). Uma palavra minúscula
entre crases é identificador; o rótulo entre aspas com outro texto continua acusado.
"""
from __future__ import annotations

import pytest

from gabarito_estados import achados_do_prd, inicios_das_linhas_com, rotulo
from tools import consistencia


@pytest.mark.parametrize("execucao", ["R11", "R12"], ids=rotulo)
def test_fp_nome_de_estado_entre_crases_nao_e_rotulo(execucao):
    assert inicios_das_linhas_com(execucao, "prd", "disparar a transição para `unoovista`")
    assert not [a for a in achados_do_prd(execucao) if a["codigo"] == "rotulo-divergente"]


_GLOSSARIO = ("### Glossário canônico\n\n| Ação | Rótulo canônico |\n|---|---|\n"
              "| Confirmar e publicar no feed da rede | Publicar no Unoovista |\n")
_CRITERIO = ('QUANDO o estudante aciona o botão "Publicar no feed da rede", O SISTEMA DEVE disparar a transição para '
             "`unoovista`.\n")


def _rotulos():
    achados = consistencia.validar(_GLOSSARIO, {"PRD": _CRITERIO}, exigir_glossario=False, etapa="dev")["achados"]
    return [a["resumo"] for a in achados if a["codigo"] == "rotulo-divergente"]


def test_v_rotulo_entre_aspas_com_outro_texto_dispara():
    assert any("«Publicar no feed da rede»" in r for r in _rotulos())


def test_fp_identificador_entre_crases_na_mesma_linha_nao_dispara():
    assert not any("«unoovista»" in r for r in _rotulos())
