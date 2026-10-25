"""Gabarito do texto de tela do §4 — `perdido-texto_tela-copy` e `perdido-texto_tela-prototipo` (A093, matriz de
rastreabilidade) e `texto-de-tela-reescrito` (A082) —, dos achados do levantamento de deficiências de design de 24/10/2026.
Os três leem os textos de `conteudo_aprovado.textos_de_tela` e os conferem com `literais_ausentes`.

- FP: a lacuna «[recorte da aula: …]» cobrada literal — a copy a preenche («…para o recorte da aula. A coordenação…») ou a
  omite com a preposição dela («Comitê Municipal de Políticas Públicas»; «na trilha avançada para estudar»), na
  exp01em1b-e89e91b3 (DS-008/009) e na exp03em1b (DS-055/056); a «Pergunta disparadora» do professor e a fala hipotética
  do aluno («se alguém disser "aconteceu isso porque eu errei na IA"») cobradas como texto de tela, na exp02em1b
  (DS-028/032/033 e, na 1ª execução, DS-046/048/049). NÃO podem disparar.
- V: o que falta de fato — «Prévia do Post», «Divulgar para a turma com foco informativo» e o «… de o aluno continuar
  navegando» encurtado (exp02em1b); «Escala Absoluta (Origem 0)» → «(Origem 0%)» (exp03em1b); «Engajamento insuficiente
  para nível avançado» fora do protótipo (exp01em1b-e89e91b3); os cinco da exp01em1b-76d9af6e (DS-092/093). TÊM de
  disparar, e o `texto-de-tela-reescrito` da exp02em1b continua.
- Ambíguos, fora do gabarito: «Reescreva removendo os nomes pessoais…» (exemplo de prompt na linha do verbo nativo) e
  «Publicações Disponíveis: 2/3» (o próprio one-pager diz «Publicações Oficiais Disponíveis»): continuam cobrados.

Os textos-chave do PR 7 (`tools/textos_chave.py`) leem o §4 pela mesma `textos_de_tela`: a pergunta do professor e a fala
hipotética deixam de ser texto-chave de tela, e não são mais copiadas por código para a copy.
"""
from __future__ import annotations

import pytest

from gabarito_estados import achados_de_consistencia, rotulo, textos_de_tela_exigidos, textos_de_tela_perdidos
from tools import textos_chave

E89 = "acervo:exp01em1b-e89e91b3"
B2E = "acervo:exp03em1b-b2e7b4a3"
F60 = "acervo:exp02em1b-60cfa7f4"
D76 = "acervo:exp01em1b-76d9af6e"

FP_LACUNA = [
    # (execução, começo do texto aprovado, colunas, id do levantamento)
    (E89, "Você foi encarregado de colocar no ar o Assistente de Estudos da Escola para o [recorte da aula",
     ("copy", "prototipo"), "DS-008/009"),
    (E89, "Tentei entrar na Trilha Avançada do [recorte da aula] para estudar", ("copy", "prototipo"), "DS-008/009"),
    (B2E, "Comitê Municipal de Políticas Públicas [recorte da aula", ("copy", "prototipo"), "DS-055/056"),
]

FP_FALA = [
    # (execução, começo da fala, id do levantamento)
    (F60, "Vocês acham que a rede entregou essa postagem às duas da manhã", "DS-028/032/033 (pergunta disparadora)"),
    (F60, "aconteceu isso porque eu errei na IA", "DS-028/032/033 (fala hipotética: «se alguém disser»)"),
    ("D01", "Vocês acham que a rede entregou essa postagem às duas da manhã", "DS-046/048/049"),
    ("D01", "aconteceu isso porque eu errei na IA", "DS-046/048/049"),
]

V = [
    # (execução, começo do texto aprovado, coluna, id do levantamento)
    (F60, "Prévia do Post", "copy", "DS-032"),
    (F60, "Divulgar para a turma com foco informativo", "copy", "DS-032"),
    (F60, "O objetivo não é a qualidade da informação, mas o engajamento", "copy", "DS-032"),
    (F60, "Relato encaminhado à equipe do Unoovista", "prototipo", "DS-033"),
    ("D01", "Prévia do Post", "copy", "DS-048"),
    ("D01", "Divulgar para a turma com foco informativo", "copy", "DS-048"),
    (B2E, "Escala Absoluta (Origem 0)", "copy", "DS-055"),
    (B2E, "Escala Absoluta (Origem 0)", "prototipo", "DS-056"),
    (E89, "Engajamento insuficiente para nível avançado", "prototipo", "DS-009"),
    (D76, "Na sua turma: X% apostou que o cadastro seria cumprido integralmente", "copy", "DS-092"),
    (D76, "Garantia de direito à explicação e canal de contestação", "copy", "DS-092"),
    (D76, "Limite de interações atingido para a sua sessão", "prototipo", "DS-093"),
    (D76, "Você previu: 'Apenas alguns receberão Avançado", "prototipo", "DS-093"),
    (D76, "Você previu: 'Todos receberão nível Básico", "prototipo", "DS-093"),
]


def _exigido(execucao: str, comeco: str) -> str:
    textos = [t for t in textos_de_tela_exigidos(execucao) if t.startswith(comeco)]
    assert textos, f"o gabarito cita «{comeco}», que o §4 de {rotulo(execucao)} não põe na tela"
    return textos[0]


@pytest.mark.parametrize("caso", FP_LACUNA, ids=lambda c: f"{c[3]} {rotulo(c[0])} «{c[1][:30]}»")
def test_fp_lacuna_preenchida_ou_omitida_nao_dispara(caso):
    execucao, comeco, colunas, _ = caso
    texto = _exigido(execucao, comeco)
    perdidos = textos_de_tela_perdidos(execucao)
    assert [c for c in colunas if texto in perdidos[c]] == []


@pytest.mark.parametrize("caso", FP_FALA, ids=lambda c: f"{c[2]} {rotulo(c[0])} «{c[1][:30]}»")
def test_fp_fala_do_professor_ou_hipotetica_nao_e_texto_de_tela(caso):
    execucao, comeco, _ = caso
    from gabarito_estados import estado

    assert comeco in str(estado(execucao).get("one_pager") or "")
    assert not [t for t in textos_de_tela_exigidos(execucao) if t.startswith(comeco)]
    assert not [t for t in textos_de_tela_perdidos(execucao)["copy"] if t.startswith(comeco)]
    # e não vira texto-chave de tela (PR 7): a cópia por código não a põe na copy
    assert not [tc for tc in textos_chave.extrair(str(estado(execucao).get("one_pager") or ""))
                if tc.tipo == textos_chave.TELA and tc.texto.startswith(comeco)]


@pytest.mark.parametrize("caso", V, ids=lambda c: f"{c[3]} {rotulo(c[0])}/{c[2]} «{c[1][:30]}»")
def test_v_dispara(caso):
    execucao, comeco, coluna, _ = caso
    texto = _exigido(execucao, comeco)
    assert texto in textos_de_tela_perdidos(execucao)[coluna]


@pytest.mark.parametrize("execucao", [F60, "D01"], ids=rotulo)
def test_v_texto_de_tela_reescrito_continua_na_copy(execucao):
    reescrito = [a["resumo"] for a in achados_de_consistencia(execucao) if a["codigo"] == "texto-de-tela-reescrito"]
    assert reescrito and "«Prévia do Post»" in reescrito[0]
    assert "Vocês acham" not in reescrito[0] and "errei na IA" not in reescrito[0]
