"""Gabarito do `hipotese-diverge` e do `hipotese-a-conferir` (A101b handoff, A116b PRD — `tools/montagem.py`), das 7
execuções de dev que o PO viu (diagnóstico C1, 24/10/2026): 24 itens 🔴 na main c9af72b, 16 verdadeiros, 3 ambíguos e
5 falsos positivos.

- V: hipótese trocada (a H3 «Adoção/Eficácia da Busca Ativa» no lugar da H3 do §17), número do §17 trocado (H1 30%→25%
  da exp02ef1b) e meta inventada onde o §17 não quantifica. TÊM de bloquear.
- FP: número da mecânica lido como meta («~75% de invisibilidade», «retenção >5s», «zoom-out de 2,5s»). NÃO podem
  bloquear nem virar dúvida.
- Dúvida: o corpo escreve o limiar da `PQ-nn` que a própria hipótese cita (linha firme do 9f) no lugar da meta do
  §17, ou o complemento dela com o comparativo invertido. Não é divergência certa: sai como `hipotese-a-conferir`,
  atenção, e a mensagem começa por «Dúvida, não divergência certa».
"""
from __future__ import annotations

import pytest

from gabarito_estados import DOCUMENTO, achados_da_montagem, corpo, estado, rotulo
from tools import montagem

BLOQUEIA = ("trocado", "acrescentado")


def _situacoes(execucao: str, documento: str, hipotese: str):
    st = estado(execucao)
    contrato = montagem.texto_do_contrato(montagem.contrato(st))
    itens = montagem.hipoteses_e_tetos(str(st.get("one_pager") or ""), corpo(execucao, documento),
                                       exigir_tetos=(documento == "prd"), spec=montagem._spec_produto(st),
                                       contrato_texto=contrato)
    return [i["situacao"] for i in itens if i.get("hipotese") == hipotese]


def _id(caso) -> str:
    return f"{rotulo(caso[0])}/{caso[1]}/{caso[2]}"


V = [
    ("R04", "handoff", "H3", "Adoção da Busca Ativa: hipótese trocada (70% → 50%)"),
    ("R04", "prd", "H3", "Agência por Busca Ativa: hipótese trocada (70% → 60%)"),
    ("R06", "handoff", "H1", "o §17 não quantifica; o handoff dá > 25%"),
    ("R06", "handoff", "H4", "§17 mais de 50% → handoff < 60%"),
    ("R06", "prd", "H1", "o §17 não quantifica; o PRD dá ≥ 70%"),
    ("R08", "handoff", "H1", "§17 65%/80% → handoff < 40%"),
    ("R08", "handoff", "H2", "o §17 não quantifica; o handoff dá 15–35%, 60%, 5%"),
    ("R08", "handoff", "H3", "o §17 não quantifica; o handoff dá 70%, 40%"),
    ("R08", "prd", "H2", "o §17 não quantifica; o PRD dá ≥ 70%"),
    ("R10", "handoff", "H3", "Eficácia da Busca Ativa: hipótese trocada, mesmo citando a PQ-03 firme a 50%"),
    ("R12", "handoff", "H1", "o §17 não quantifica; < 65%"),
    ("R12", "handoff", "H2", "o §17 não quantifica; < 60%"),
    ("R12", "handoff", "H3", "o §17 não quantifica; 60%, 40%"),
    ("R13", "handoff", "H1", "30% → 25% (o PO acusou em 23/10/2026)"),
    ("R13", "handoff", "H2", "o §17 não quantifica; < 70% (a PQ-02 está em [PROPOSTA])"),
]

FP = [
    ("R04", "prd", "H1", "«retenção >5s» é peso da mecânica (o one-pager tem «tempo > 5s = +1 ponto»)"),
    ("R04", "prd", "H2", "«taxa real de ~75% de invisibilidade» é a mecânica (12 de 16 projetos ocultos)"),
    ("R06", "prd", "H2", "«zoom-out vetorial de 2,5s» é a duração da animação (está na spec)"),
]

DUVIDA = [
    # (execução, documento, hipótese, número do §17, número do corpo, por quê)
    ("R04", "handoff", "H1", "85%", "80%", "meta do §17 × limiar da PQ-01 (linha firme do 9f, origem PO)"),
    ("R04", "handoff", "H2", "80%", "75%", "meta do §17 × limiar da PQ-02"),
    ("R10", "handoff", "H1", "85%", "70%", "meta do §17 × limiar da PQ-02 (HOMOLOGADO pelo PO)"),
    ("R10", "handoff", "H2", "80%", "15%", "o 75% era a mecânica; sobra o «< 15%», limiar da PQ-01"),
    ("R13", "handoff", "H3", "40%", "60%",
     "«mais de 40% parearem pela cor» × «menos de 60% … com a justificativa correta»: complemento, mas quem não "
     "conclui conta como falha num lado e não no outro"),
]


@pytest.mark.parametrize("caso", V, ids=_id)
def test_v_bloqueia(caso):
    execucao, documento, hipotese, motivo = caso
    assert set(_situacoes(execucao, documento, hipotese)) & set(BLOQUEIA), f"{rotulo(execucao)} {hipotese}: {motivo}"


def test_v_h1_30_contra_25_no_corpo_do_prd_da_exp02ef1b():
    """No PRD a H1 com 25% sai da régua de linha (o corpo repete a frase do §17): continua bloqueando."""
    assert any("30%" in a["resumo"] and "25%" in a["resumo"] and a["severidade"] == "bloqueio"
               for a in achados_da_montagem("R13", "prd") if a["codigo"] == "hipotese-diverge")


#: Mutantes da H1 30×25 da exp02ef1b sobre o estado real (revisão do PR #77, 24/10/2026): a mesma troca com outra
#: redação do comparativo. Na leitura que pedia comparativo de lista curta ou população, todos passavam sem achado.
H1_HANDOFF = "Se mais de 25% das duplas"
H1_PRD = ("Mais de 25% das duplas desistirem de ajustar a moldura e clicarem em confirmar na posição default sem "
          "interagir (alimenta PQ-01).")
MUTANTES_H1 = [
    ("handoff", H1_HANDOFF, "Se 25% ou mais das duplas"),
    ("handoff", H1_HANDOFF, "Se a desistência das duplas superar 25%"),
    ("handoff", H1_HANDOFF, "Se a taxa de desistência for maior que 25%"),
    ("handoff", H1_HANDOFF, "Se a desistência passar de 25%"),
    ("handoff", H1_HANDOFF, "Se a desistência ultrapassar 25%"),
    ("handoff", H1_HANDOFF, "Se a desistência exceder 25%"),
    ("handoff", H1_HANDOFF, "Se mais que 25% das duplas"),
    ("handoff", H1_HANDOFF, "Se a taxa de desistência de 25% for atingida, ou"),
    ("prd", H1_PRD, "Se a desistência das duplas na moldura superar 25% (alimenta PQ-01)."),
    ("prd", H1_PRD, "25% ou mais das duplas desistem da moldura (alimenta PQ-01)."),
    ("prd", H1_PRD, "A desistência for maior do que 25% das duplas (alimenta PQ-01)."),
    ("prd", H1_PRD, "Se a taxa de desistência ultrapassar 25% (alimenta PQ-01)."),
    # segunda revisão (24/10/2026): o «~» solto e a «taxa de 25%» marcavam a porcentagem como mecânica, e o 25% só
    # existe no contrato no limiar da PQ-01
    ("handoff", H1_HANDOFF, "Se a desistência chegar a ~25%, ou"),
    ("handoff", H1_HANDOFF, "Se ~25% desistirem, ou"),
    ("handoff", H1_HANDOFF, "Se a taxa de 25% de desistência for atingida pelas duplas, ou"),
    ("prd", H1_PRD, "A taxa de 25% de desistência na moldura for atingida (alimenta PQ-01)."),
    ("prd", H1_PRD, "Desistência na moldura em ~25% (alimenta PQ-01)."),
]


@pytest.mark.parametrize("caso", MUTANTES_H1, ids=lambda c: f"{c[0]}/{c[2]}")
def test_v_h1_30_contra_25_com_qualquer_comparativo(caso):
    documento, original, mutante = caso
    st = estado("R13")
    chave = DOCUMENTO[documento]
    assert original in st[chave], f"o {documento} de {rotulo('R13')} não tem «{original}»"
    st[chave] = st[chave].replace(original, mutante)
    r = montagem.validar_prd(st) if documento == "prd" else montagem.validar_handoff(st)
    assert any(a["codigo"] == "hipotese-diverge" and a["severidade"] == "bloqueio" and "30%" in a["resumo"]
               and "escreve 25%" in a["resumo"] for a in r["achados"]), mutante


def test_v_duracao_que_o_contrato_nao_tem_continua_meta():
    """exp05ef1b (acervo): «verificado por `tempo_feed_segundos` < 180s» na H1 do PRD — o §17 não quantifica e nenhum
    documento do contrato tem 180 s: meta inventada, não parâmetro da mecânica."""
    assert any("180 s" in a["resumo"] for a in achados_da_montagem("acervo:exp05ef1b", "prd")
               if a["codigo"] == "hipotese-diverge")


@pytest.mark.parametrize("caso", FP, ids=_id)
def test_fp_nao_bloqueia_nem_vira_duvida(caso):
    execucao, documento, hipotese, motivo = caso
    assert not _situacoes(execucao, documento, hipotese), f"{rotulo(execucao)} {hipotese}: {motivo}"


@pytest.mark.parametrize("caso", DUVIDA, ids=_id)
def test_duvida_sai_como_atencao_separada_do_bloqueio(caso):
    execucao, documento, hipotese, do_17, do_corpo, motivo = caso
    situacoes = _situacoes(execucao, documento, hipotese)
    assert situacoes and not set(situacoes) & set(BLOQUEIA), f"{rotulo(execucao)} {hipotese} ainda bloqueia: {motivo}"
    achados = achados_da_montagem(execucao, documento)
    duvidas = [a for a in achados if a["codigo"] == "hipotese-a-conferir" and f"a {hipotese} do §17" in a["resumo"]]
    assert duvidas and duvidas[0]["severidade"] == "atencao"
    assert duvidas[0]["resumo"].startswith("Dúvida, não divergência certa")
    # e nenhum bloqueio acusa a mesma troca por outro caminho (a régua de linha do §17)
    assert not [a for a in achados if a["severidade"] == "bloqueio" and a["codigo"] == "hipotese-diverge"
                and f"com {do_17}, e o" in a["resumo"] and f"escreve {do_corpo}" in a["resumo"]]


def test_relatorio_separa_divergencia_certa_de_duvida():
    """O relatório do handoff da exp06ef1b-727a3c2d tem a H3 trocada (bloqueia) e as H1/H2 em dúvida: em blocos
    separados, para o PO e para o retrabalho do redator."""
    st = estado("R04")
    texto = montagem.relatorio(montagem.validar_handoff(st), "handoff", "exp06ef1b")
    certa = texto.index("**Divergência certa — bloqueia; o redator corrige:**")
    duvida = texto.index("**Dúvida ou registro — não bloqueia; o PO confere antes do de acordo:**")
    assert certa < texto.index("⛔ `hipotese-diverge`") < duvida < texto.index("⚠️ `hipotese-a-conferir`")
