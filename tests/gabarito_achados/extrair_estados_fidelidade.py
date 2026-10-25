"""Monta os estados do gabarito da fidelidade que o acervo de regressão não tem (só leitura sobre as sessões do bucket).

O gabarito da fidelidade (`test_gabarito_fidelidade.py`) reavalia as fidelidades A010, A060 e A094 sobre o estado real
de cada execução classificada no levantamento de deficiências de 24/10/2026, com a resposta que o juiz e o intérprete
gravaram. Quase todas as execuções estão no acervo (`tests/acervo/<missão>-<sessão>/estado.json`); as que não estão
são gravadas aqui, só com as chaves que a fidelidade lê (`CHAVES`), em `estados_fidelidade/<missão>-<sessão>.json.xz`.

Uso (a pasta é a cópia das sessões do bucket, `<pasta>/estado.json`):

    python tests/gabarito_achados/extrair_estados_fidelidade.py /caminho/para/raw
"""
from __future__ import annotations

import json
import lzma
import sys
from pathlib import Path

ESTADOS = Path(__file__).resolve().parent / "estados_fidelidade"

#: O que a fidelidade lê do estado (`agents.checkers.FidelidadeCheckAgent`): pedidos, briefing, documentos de produto,
#: versões anteriores, as respostas do juiz e do intérprete e o relatório gravado (o recorte e os ids do checklist).
CHAVES = ("briefing", "pedidos_do_po", "pedido_correcao", "etapa_da_correcao", "modo_correcao", "edicoes_pontuais",
          "nucleo_narrativo", "one_pager", "spec_missao", "fidelidade_status", "fidelidade_report",
          "fidelidade_nucleo_status", "fidelidade_nucleo_report", "juiz_fidelidade_saida",
          "juiz_fidelidade_nucleo_saida", "interpretacao_fidelidade_saida", "interpretacao_fidelidade_nucleo_saida",
          "versao_anterior_nucleo_narrativo", "versao_anterior_one_pager", "versao_anterior_spec_missao")

#: Execuções fora do acervo: id → (missão, sessão, pasta da cópia, o que mostram).
EXECUCOES = {
    "exp03ef1b-274a2e75": ("exp03ef1b", "274a2e75", "20261007-111405-session_274a2e75",
                           "briefing com «secao_ds: unoogaleria · É PROIBIDO usar qualquer outro design system», "
                           "one-pager e spec em unoochat, fidelidade 🟢 com 0 itens (07/10/2026)"),
}


def arquivo(execucao: str) -> Path:
    return ESTADOS / f"{execucao}.json.xz"


def main(raw: Path) -> None:
    ESTADOS.mkdir(exist_ok=True)
    for execucao, (_, _, pasta, _) in EXECUCOES.items():
        estado = json.loads((raw / pasta / "estado.json").read_text(encoding="utf-8"))
        recorte = {k: estado[k] for k in CHAVES if k in estado}
        arquivo(execucao).write_bytes(lzma.compress(json.dumps(recorte, ensure_ascii=False, sort_keys=True).encode()))
        print(f"{execucao}: {len(recorte)} chaves")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
