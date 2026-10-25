"""Gabarito do `linhas-perdidas` do design (A066/A068, preservação da spec — `agents/checkers.SecaoSplitAgent`): os 14 achados
do levantamento de deficiências de design de 24/10/2026 (8 FP, 4 da esteira, 2 V), conferidos com o estado real.

Desde o PR 6 (#73) a spec de produto não muda no design: o D0 e o D9 gravam só o anexo (blocos 13 e 14), a preservação
compara o anexo, e a mudança no texto do Gate 0 é descartada e vai ao PO (`[ABERTO — dono: PO]`, ou a rota do Refazer
quando é troca pedida por ele). Refeito o split do D0 e do D9 sobre as respostas gravadas, com o código da main, nenhuma
das sessões acusa `linhas-perdidas`, e a spec sai igual à do Gate 0 — a contradição «a fidelidade manda tirar, a
preservação restaura» (V73/V74) não tem mais onde acontecer. Só gabarito: a C4 não muda esta regra.

- FP: as linhas do próprio bloco 13 do D0 cobradas na rodada 2 (exp02em1b, 1ª execução, DS-036/043); a telemetria e o
  glossário com «Publicar no Álbum» trocados a pedido do PO (exp02ef1b, DS-059/069). NÃO podem disparar.
- Da esteira: a tabela de estados que o PO mandou trocar e o refazer de produto não trocou (exp02em1b, DS-012/021/113).
  Não é perda: é mudança no Gate 0, que aparece ao PO e não entra na spec.
- V: o D9 que reescreve a decisão do D0 (exp06ef1b, rodada 6, DS-110/111 — «chave de renovação» de volta ao inglês). A
  causa estrutural saiu (o D9 não recopia mais a spec), e o caso equivalente que sobrou no acervo — o D9 da exp03em1b
  reescrevendo a decisão de reentrada do D0 no bloco 13 — dispara como `alterou-fora-do-proprio-bloco`, com o texto do
  D0 mantido no anexo.
"""
from __future__ import annotations

import pytest

from gabarito_estados import achados_do_split, estado, remontar, rotulo

SEM_PERDA = [
    ("D01", "DS-036/043"),
    ("acervo:exp02ef1b-4fd72a9a", "DS-059/069"),
    ("acervo:exp02em1b-60cfa7f4", "DS-012/021/113"),
]


@pytest.mark.parametrize("caso", SEM_PERDA, ids=lambda c: f"{c[1]} {rotulo(c[0])}")
def test_fp_split_refeito_nao_acusa_linhas_perdidas_e_a_spec_fica_a_do_gate0(caso):
    execucao, _ = caso
    assert "linhas-perdidas" not in {a["codigo"] for a in achados_do_split(execucao)}
    assert remontar(execucao)["spec_missao"] == estado(execucao)["spec_missao_gate0"]


def test_esteira_a_troca_que_o_po_pediu_na_tabela_de_estados_aparece_ao_po_e_nao_entra_na_spec():
    """exp02em1b (V78): «Ação no menu 3 pontos … moderação» → «Configuração da Publicação, Central de Apoio…»."""
    execucao = "acervo:exp02em1b-60cfa7f4"
    aberto = [a for a in achados_do_split(execucao)
              if a["codigo"] == "alterou-fora-do-proprio-bloco" and a.get("aberto_dono_po") and a.get("bloco") == "2"]
    assert aberto and "Ação no menu 3 pontos" in aberto[0]["resumo"]
    assert "Ação no menu 3 pontos" in remontar(execucao)["spec_missao"]


def test_publicar_no_album_trocado_a_pedido_nao_volta_a_ser_cobrado():
    """exp02ef1b (V73/V74): o editor restaurou «Publicar no Álbum» na spec «para resolver o bloqueio de linhas-perdidas»."""
    achados = achados_do_split("acervo:exp02ef1b-4fd72a9a")
    assert not [a for a in achados if a["codigo"] == "linhas-perdidas"]
    assert [a for a in achados if a["codigo"] == "alterou-fora-do-proprio-bloco" and "Refazer" in a["resumo"]
            and "Publicar no Álbum" in a["resumo"]]


def test_v_d9_que_reescreve_a_decisao_do_d0_dispara_e_o_anexo_fica_com_o_texto_do_d0():
    execucao = "acervo:exp03em1b-b2e7b4a3"
    fora = [a for a in achados_do_split(execucao)
            if a["codigo"] == "alterou-fora-do-proprio-bloco" and "o bloco 13" in a["resumo"]]
    assert fora and "atualização de página" in fora[0]["resumo"]
    anexo = remontar(execucao)["anexo_design_spec"]
    assert "(por atualização de página, fechamento acidental ou retomada noutro dia)" in anexo
