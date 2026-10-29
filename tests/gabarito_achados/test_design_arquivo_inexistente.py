"""Gabarito do `arquivo-inexistente` (A089 — `tools/afirmacoes.conferir_qa`), dos 5 achados do levantamento de
deficiências de design de 24/10/2026 (2 V, 2 FP e o da V82, que trava a exp03em1b).

- FP: na rodada 2, o QA RELATA o ticket da rodada 1, com a negação colada no caminho que a rodada 1 já acusou — «Citação
  no relatório de QA ao caminho inexistente `design/04-copy-passada2.md`» (exp01em1b-e89e91b3, DS-005/007; a main já não
  acusava) e «… citou a chave de caminho 'design/06-copy-revisada.md', arquivo não gravado na esteira» (V82, DS-123, o
  texto que o PO colou no refazer de 23/10/2026 02:09; a main acusava mesmo com o caminho já apontado). NÃO podem
  disparar.
- V: o QA que cita como real um nome que a esteira não grava — «**ONDE:** `design/04-copy-ptbr.md`» (exp02em1b, DS-020/022)
  e o nome que o relatório do protótipo inventou e o QA repetiu na rodada 1 da V82 (`design/06-copy-revisada.md`, na
  frase que a correção pontual tirou do protótipo). TÊM de disparar, com o caminho já apontado ou não.
"""
from __future__ import annotations

import pytest

from gabarito_estados import estado, linhas_com, rotulo
from tools import afirmacoes


def _acusa(texto: str, apontados) -> bool:
    return any(a["codigo"] == "arquivo-inexistente" for a in afirmacoes.conferir_qa(texto, ja_apontados=apontados)["achados"])


def _relato_da_v82() -> str:
    """O trecho do QA que o PO colou no pedido de refazer da V82 (exp03em1b, 23/10/2026 02:09)."""
    pedido = next(str(p.get("texto")) for p in estado("acervo:exp03em1b-b2e7b4a3")["pedidos_do_po"]
                  if "arquivo-inexistente" in str(p.get("texto")))
    return pedido.split("Trecho do QA: ", 1)[1]


def _citacao_da_rodada_1() -> str:
    """A frase do relatório do protótipo que trazia o nome inventado — a correção pontual da V82 a tirou do protótipo."""
    troca = next(e for e in estado("acervo:exp03em1b-b2e7b4a3")["edicoes_pontuais"]
                 if "design/06-copy-revisada.md" in str(e.get("de")))
    return str(troca["de"])


def test_fp_v82_relato_do_ticket_com_o_caminho_ja_apontado_nao_dispara():
    relato = _relato_da_v82()
    assert "'design/06-copy-revisada.md', arquivo não gravado na esteira" in relato
    assert not _acusa(relato, ["design/06-copy-revisada.md"])


@pytest.mark.parametrize("execucao", ["acervo:exp01em1b-e89e91b3"], ids=rotulo)
def test_fp_relato_da_rodada_2_com_o_caminho_ja_apontado_nao_dispara(execucao):
    linha, = [l for l in linhas_com(execucao, "qa_entregaveis_report", "ao caminho inexistente `design/04-copy-passada2.md`")
              if l.lstrip().startswith("- *Apontamento:*")]
    assert not _acusa(linha, ["design/04-copy-passada2.md"])


@pytest.mark.parametrize("apontados", [[], ["design/06-copy-revisada.md"]], ids=["sem-apontado", "ja-apontado"])
def test_v_v82_rodada_1_nome_inventado_citado_como_real_dispara(apontados):
    citacao = _citacao_da_rodada_1()
    assert "sheet de copy revisado (`design/06-copy-revisada.md`)" in citacao
    assert _acusa(citacao, apontados)


@pytest.mark.parametrize("apontados", [[], ["design/04-copy-ptbr.md"]], ids=["sem-apontado", "ja-apontado"])
def test_v_onde_cita_arquivo_que_a_esteira_nao_grava_dispara(apontados):
    linha = linhas_com("acervo:exp02em1b-60cfa7f4", "qa_entregaveis_report", "**ONDE:** `design/04-copy-ptbr.md`")[0]
    assert _acusa(linha, apontados)


def test_v82_sem_o_caminho_apontado_continua_acusando():
    """O relato só é dispensado para o caminho que a rodada anterior acusou (816b026): sem ele, o QA que escreve um nome
    que a esteira não grava continua reprovado, mesmo com a negação colada."""
    assert _acusa(_relato_da_v82(), [])


#: A rodada 2 da exp01em1b-d203ac83 (29/10/2026) relatou o ticket com «que não consta na lista», sem a negação colada que
#: as regex conhecem, e a missão travou no design. A seção da auditoria basta, seja qual for a redação.
_AUDITORIA_D203 = (
    "# QA de Entregáveis — exp01em1b — rodada 2 de 2\n\n"
    "## Auditoria da rodada anterior (o que mudou)\n\n"
    "* **`QA-A1` (severidade `bloqueio`, código `arquivo-inexistente`):** **RESOLVIDO.** Na rodada 1, o relatório citou "
    "a rota `design/06-copy-revisada.md`, que não consta na lista de artefatos persistidos pela esteira "
    "(`pipeline/artifacts.py`).\n\n"
    "## Pré-check de lacunas\n\n* Nada aberto.\n"
)


def test_fp_d203_relato_na_secao_da_auditoria_nao_dispara():
    assert not _acusa(_AUDITORIA_D203, ["design/06-copy-revisada.md"])


def test_v_d203_fora_da_auditoria_ou_sem_o_caminho_apontado_dispara():
    """Fora da seção, o mesmo caminho volta a ser citação; dentro dela, só o caminho que a rodada anterior acusou é relato."""
    fora = _AUDITORIA_D203 + "\n## Tickets\n\n* A copy está em `design/06-copy-revisada.md`.\n"
    assert _acusa(fora, ["design/06-copy-revisada.md"])
    assert _acusa(_AUDITORIA_D203, [])
    assert _acusa(_AUDITORIA_D203.replace("06-copy-revisada", "04-copy-final"), ["design/06-copy-revisada.md"])


def test_prompt_do_qa_lista_os_caminhos_de_design_que_a_esteira_grava():
    """O QA copia o caminho da lista do prompt em vez de deduzi-lo; a lista tem de ser a de `pipeline/artifacts.py`."""
    import re

    from pipeline.artifacts import ARTIFACT_FILES
    from prompts.loader import get_prompt_raw

    bloco = get_prompt_raw("design/088_qa_entregaveis.md").split("caminhos-de-design: início")[1].split("caminhos-de-design: fim")[0]
    assert set(re.findall(r"`(design/[^`]+)`", bloco)) == {n for _, n in ARTIFACT_FILES if n.startswith("design/")}
