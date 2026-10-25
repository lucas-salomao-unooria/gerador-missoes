"""Gabarito do `rotulo-divergente` no design (A082 — `tools/consistencia.py`): os 16 achados de 4 sessões de 22–23/10/2026
classificados no levantamento de deficiências de design de 24/10/2026 (11 FP, 2 V e 3 ambíguos), todos reproduzidos na
main 5df5d12. A C1 tratou o caso do dev (identificador minúsculo entre crases); aqui, o do design.

- FP: o verbo entre crases na coluna de gesto da jornada («`Acessar` / `Digitar`», «`Fixar` aviso de cuidado»); o rótulo
  de aresta do Mermaid, que o prompt do fluxo limita a três palavras (072), citado na linha que fala do desenho
  («Publicar Unoovista», «Toca modulo teste»); o nome da missão no card do professor («O Porta-Voz dos Dados»); o miolo
  entre duas citações («) | Disparar simulação (»). NÃO podem disparar.
- V: o botão com dois nomes da exp03em1b — «Avançar para Laudo Técnico» no fluxo e na copy, «Avançar para Perícia Final»
  no glossário da spec. TEM de disparar.
- Ambíguos, fora do gabarito (a medição do PR os mostra): «Publicar» na coluna de gesto (DS-024) e «toca Abrir Album»,
  rótulo de aresta citado no fluxo (DS-070), deixam de disparar; «Confirmar e Disparar Teste», botão entre aspas duplas na
  raia do estudante que pode ser outro botão (DS-086), continua.
"""
from __future__ import annotations

import pytest

from gabarito_estados import linhas_com, rotulo, rotulos_divergentes

#: O rótulo do documento no achado → a chave do estado.
CHAVE = {"jornada": "jornada_telas", "fluxo": "fluxo_arestas", "copy revisada": "copy_strings_revisada"}

FP = [
    # (execução, documento, como o achado o citava, trecho da linha, id do levantamento, por que não é rótulo)
    ("acervo:exp02em1b-60cfa7f4", "jornada", "Acessar", "| `Acessar` / `Digitar` |", "DS-023",
     "verbo nativo na coluna «Ação (verbo nativo)» do inventário"),
    ("acervo:exp02em1b-60cfa7f4", "jornada", "Fixar", "`Fixar` aviso de cuidado", "DS-025",
     "verbo nativo; o rótulo canônico está inteiro na célula"),
    ("acervo:exp02em1b-60cfa7f4", "jornada", "Encaminhar", "| `Encaminhar` relato |", "DS-026", "idem"),
    ("acervo:exp02em1b-60cfa7f4", "fluxo", "Publicar Unoovista", "**Maior rótulo no Mermaid:**", "DS-027",
     "rótulo de aresta Mermaid (≤ 3 palavras, 072)"),
    ("D01", "jornada", "Acessar", "| `Acessar` / `Digitar` |", "DS-045", "verbo nativo, na 1ª execução"),
    ("acervo:exp03em1b-b2e7b4a3", "jornada", "O Porta-Voz dos Dados", 'Card da missão "O Porta-Voz dos Dados"', "DS-051",
     "nome da missão no card do professor (E0-PROF-01)"),
    ("acervo:exp03em1b-b2e7b4a3", "fluxo", "O Porta-Voz dos Dados", 'card da missão "O Porta-Voz dos Dados"', "DS-053",
     "idem, na aresta P02"),
    ("acervo:exp01em1b-76d9af6e", "jornada", ") | Disparar simulação (", '`"Confirmar e Disparar Teste"`) | Disparar simulação',
     "DS-087", "o miolo entre o fecho de uma citação e a abertura da seguinte"),
    ("acervo:exp01em1b-76d9af6e", "jornada", "), Publicar transparência (", "(`SelectionBox`), Publicar transparência (",
     "DS-088", "idem"),
    ("acervo:exp01em1b-76d9af6e", "fluxo", "Toca modulo teste", "**Maior rótulo no desenho Mermaid:**", "DS-089",
     "rótulo de aresta Mermaid"),
    ("acervo:exp01em1b-76d9af6e", "fluxo", "Disparar simulacao latch", "**Maior rótulo no desenho Mermaid:**", "DS-090",
     "rótulo de aresta Mermaid"),
]

V = [
    # (execução, documento, como o achado o cita, trecho da linha, id do levantamento)
    ("acervo:exp03em1b-b2e7b4a3", "fluxo", "Avançar para Laudo Técnico", 'botão "Avançar para Laudo Técnico" é acionado',
     "DS-052"),
    ("acervo:exp03em1b-b2e7b4a3", "copy revisada", "Avançar para Laudo Técnico", "| Avançar para Laudo Técnico | 4 |",
     "DS-054"),
]


def _id(caso) -> str:
    return f"{caso[4]} {rotulo(caso[0])}/{caso[1]}/{caso[2]}"


@pytest.mark.parametrize("caso", FP, ids=_id)
def test_fp_nao_dispara(caso):
    execucao, documento, citado, trecho, _, _ = caso
    assert linhas_com(execucao, CHAVE[documento], trecho)
    assert not [r for r in rotulos_divergentes(execucao)
                if r.startswith(f"{documento}:") and f"aparece como «{citado}»" in r]


@pytest.mark.parametrize("caso", V, ids=_id)
def test_v_dispara(caso):
    execucao, documento, citado, trecho, _ = caso
    assert linhas_com(execucao, CHAVE[documento], trecho)
    assert [r for r in rotulos_divergentes(execucao)
            if r.startswith(f"{documento}:") and f"aparece como «{citado}»" in r
            and "o rótulo canônico é «Avançar para Perícia Final»" in r]
