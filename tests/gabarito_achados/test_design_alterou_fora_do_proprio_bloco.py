"""Gabarito do `alterou-fora-do-proprio-bloco` do D9 (A068 — `agents/checkers.montar_sobre_aceita`, refeito sobre a resposta
gravada por `tools/ambiente.reavaliar_d9`), dos 16 achados do levantamento de deficiências de design de 24/10/2026: 12 V,
1 FP e 3 da esteira.

- FP: a única diferença do bloco 13 era a régua `***` da moldura (exp02em1b, 1ª execução, DS-037: «-*** -»). A main já
  não a conta (`_linhas_normalizadas` tira a régua desde a791270, 23/10/2026): o que sobra no bloco 13 dessa execução é a
  recópia de verdade das decisões [D0-7]–[D0-9]. NÃO pode disparar pela régua.
- V: o D9 que reescreve texto que não é dele — a decisão do D0 no bloco 13 («atualização de página» → «… F5», exp03em1b,
  DS-050; exp01em1b-76d9af6e, DS-082), o bloco 12 com as [PROPOSTA] reescritas e o bloco 3 da exp02em1b (DS-016, DS-014),
  e os estados, a regra, a demonstração e os dispositivos que ele pôs nos blocos 2, 3, 7 e 10 da exp01em1b-76d9af6e
  (DS-078–081) — esses, desde o PR 8 (decisão D8), como `decisao-de-produto-pelo-agente`. TÊM de disparar.
- Documentado: a recópia que só acrescenta a marca «Resolvido em [D0-n]» (exp02em1b bloco 6, DS-015; exp02ef1b blocos 3,
  6 e 12, DS-061/062/064) não dispara desde o PR 2 (#69): a marca vira o mapa célula → D0 do bloco 13, e o bloco fica
  igual ao aceito. O caso confere que a diferença era só a marca.
- Da esteira (fora do gabarito): a troca pedida pelo PO que o D9 trouxe para a spec (DS-013, DS-060, DS-063) é descartada
  e avisada com a rota do Refazer (cascata a produto, PR 5).
"""
from __future__ import annotations

import pytest

from agents.checkers import (_linhas_normalizadas, _recolher_marcas_resolvido, _secoes, documento_sem_moldura,
                             montar_sobre_aceita)
from gabarito_estados import estado, rotulo
from tools import ambiente
from tools.anexo_design import KEY_ANEXO, _bloco, blocos_do_anexo
from tools.propagacao import spec_de_produto

FORA = ("alterou-fora-do-proprio-bloco", "decisao-de-produto-pelo-agente")


def _do_d9(execucao: str):
    return [a for a in ambiente.reavaliar_d9(estado(execucao))["achados"] if a["codigo"] in FORA]


def _aceita_e_nova(execucao: str):
    """A spec que o A068 aceita (a de produto mais o bloco 13) e a resposta do D9, como em `reavaliar_d9`."""
    st = estado(execucao)
    spec = str(st.get("spec_missao") or "")
    produto = str(st.get("spec_missao_gate0") or "") or spec_de_produto(spec)
    anexo = blocos_do_anexo(str(st.get(KEY_ANEXO) or "")) or _bloco(spec, "13")
    return produto.rstrip() + "\n\n" + anexo, documento_sem_moldura(ambiente._passo4(str(st["ambiente_simulado"])))


# --------------------------------------------------------------------------- FP
def _so_regua(resumo: str) -> bool:
    """O diff do achado só tem régua (`***`, `---`) e linha vazia."""
    diff = [l.strip()[1:] for l in resumo.splitlines()[1:] if l.strip()[:1] in "+-"]
    return not [l for l in diff if l.strip(" *-_")]


def test_fp_regua_do_bloco_13_na_1a_execucao_da_exp02em1b_nao_dispara():
    """DS-037: o envelope gravado em 22/10/2026 acusava o bloco 13 só pela régua; refeito com o código de agora sobre a
    mesma resposta, o que sobra no bloco 13 é a recópia de verdade das decisões do D0."""
    gravado = [a for a in (estado("D01").get("ambiente_status_envelope") or {}).get("achados") or []
               if a.get("codigo") == "alterou-fora-do-proprio-bloco" and "o bloco 13" in str(a.get("resumo"))]
    assert gravado and _so_regua(gravado[0]["resumo"])
    agora = [a for a in _do_d9("D01") if "o bloco 13" in a["resumo"]]
    assert agora and not [a for a in agora if _so_regua(a["resumo"])]


@pytest.mark.parametrize("regua", ["***", "---", "___"])
def test_fp_regua_a_mais_ou_a_menos_antes_do_bloco_13_nao_e_mudanca(regua):
    """A régua que o modelo põe ou tira antes do bloco 13, sobre a spec que o D9 da 1ª execução da exp02em1b aceitou."""
    aceita, nova = _aceita_e_nova("D01")
    treze, catorze = _bloco(aceita, "13"), _bloco(nova, "14")
    assert treze.strip() and catorze.strip()
    com_regua = aceita.replace(treze, f"{regua}\n\n{treze}", 1)
    for de, para in ((aceita, com_regua), (com_regua, aceita)):
        avisos = []
        montar_sobre_aceita(de, para.rstrip() + "\n\n" + catorze, r"^##\s*14\b.*$", avisos=avisos, estado=estado("D01"))
        assert avisos == []


# --------------------------------------------------------------------------- V
V = [
    # (execução, bloco, trecho do diff, id do levantamento)
    ("acervo:exp03em1b-b2e7b4a3", "13", "atualização de página", "DS-050"),
    ("acervo:exp01em1b-76d9af6e", "13", "2 a 4 por aparelho", "DS-082"),
    ("acervo:exp01em1b-76d9af6e", "2", "", "DS-078"),
    ("acervo:exp01em1b-76d9af6e", "3", "", "DS-079"),
    ("acervo:exp01em1b-76d9af6e", "7", "", "DS-080"),
    ("acervo:exp01em1b-76d9af6e", "10", "", "DS-081"),
    ("acervo:exp02em1b-60cfa7f4", "12", "", "DS-016"),
    ("acervo:exp02em1b-60cfa7f4", "3", "", "DS-014"),
]


@pytest.mark.parametrize("caso", V, ids=lambda c: f"{c[3]} {rotulo(c[0])}/bloco {c[1]}")
def test_v_d9_que_reescreve_texto_alheio_dispara(caso):
    execucao, bloco, trecho, _ = caso
    achados = [a for a in _do_d9(execucao) if f"bloco {bloco} " in a["resumo"] + " " or a.get("bloco") == bloco]
    assert achados and (not trecho or any(trecho in a["resumo"] for a in achados))


# --------------------------------------------------------------------------- documentado
MARCA = [
    ("acervo:exp02em1b-60cfa7f4", "6", "DS-015"),
    ("acervo:exp02ef1b-4fd72a9a", "3", "DS-061"),
    ("acervo:exp02ef1b-4fd72a9a", "6", "DS-062"),
    ("acervo:exp02ef1b-4fd72a9a", "12", "DS-064"),
]


@pytest.mark.parametrize("caso", MARCA, ids=lambda c: f"{c[2]} {rotulo(c[0])}/bloco {c[1]}")
def test_recopia_so_com_a_marca_resolvido_e_o_bloco_aceito(caso):
    execucao, bloco, _ = caso
    aceita, nova = _aceita_e_nova(execucao)
    crua = _secoes(nova)[bloco]
    sem_marca = _secoes(_recolher_marcas_resolvido(aceita, nova)[0])[bloco]
    assert _linhas_normalizadas(crua) != _linhas_normalizadas(_secoes(aceita)[bloco])
    assert _linhas_normalizadas(sem_marca) == _linhas_normalizadas(_secoes(aceita)[bloco])
    assert not [a for a in _do_d9(execucao) if f"o bloco {bloco} " in a["resumo"]]
