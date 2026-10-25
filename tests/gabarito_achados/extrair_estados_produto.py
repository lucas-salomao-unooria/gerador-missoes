"""Monta os estados do gabarito de achados de PRODUTO a partir das sessões do bucket (só leitura sobre elas).

O gabarito de produto (`tests/gabarito_achados/test_gabarito_produto.py`, correção C3 do backlog de 24/10/2026) roda os
juízes e lints de produto sobre o estado real de cada execução em que o achado foi classificado — verdadeiro (V) ou falso
positivo (FP) — no levantamento de deficiências de produto (`deficiencias/produto/achados.csv`). As execuções que estão no
acervo de regressão (`tests/acervo/<nome>/estado.json`) são lidas de lá; este script grava as que não estão, uma por
sessão, em `estados_produto/<missão>-<sessão>.json.xz`: só as chaves que esses gates leem (`CHAVES`), e dos pareceres
humanos só etapa, ação, comentário e data — sem conta nem assinatura.

Arquivos e nomes próprios, para não cruzar com o gabarito de dev da C1 (`estados/`, `extrair_estados.py`,
`gabarito_estados.py`); um helper comum aos dois se unifica depois que os dois PRs estiverem na main.

Uso (a pasta é a cópia das sessões do bucket, `<sessão>/estado.json` e `<sessão>/.correcoes/<quando>-<etapa>/`):

    python tests/gabarito_achados/extrair_estados_produto.py /caminho/para/raw
"""
from __future__ import annotations

import json
import lzma
import sys
from pathlib import Path
from typing import Any, Dict

ESTADOS = Path(__file__).resolve().parent / "estados_produto"

#: O que os gates do gabarito de produto leem do estado (cobertura conceitual, decisão atribuída ao PO, juízes
#: recontados, fidelidade e banca do fim de produto), medido em 24/10/2026. A banca confere a citação dos achados em
#: `tools.banca.DOCUMENTOS_DA_BANCA`.
CHAVES = ("anexo_design_spec", "avaliacao_pedagogica_report", "avaliacao_status", "banca_produto_narrativa",
          "banca_produto_pedagogia", "banca_produto_status", "brief_assets", "brief_oficio", "briefing", "camada_caa",
          "conteudo_aprovado", "copy_strings_revisada", "decisoes_do_po", "experiencia_aluno_report",
          "experiencia_status", "fidelidade_nucleo_status_envelope", "fidelidade_status_envelope", "fluxo_arestas",
          "gate_final_report", "gate_final_status", "jornada_telas", "mapa_conceitual", "material_anexado",
          "notas_de_passagem", "nucleo_narrativo", "one_pager", "one_pager_po", "one_pager_resumido",
          "pareceres_humanos", "pedido_correcao", "pedidos_do_po", "prototipo_relatorio", "slug", "spec_missao",
          "spec_missao_gate0", "stitch_links", "wireframes_cobertura")

#: As execuções de produto fora do acervo (`deficiencias/produto/achados.csv`, colunas `sessao` e `momento`):
#: id → (missão, sessão, pasta da cópia, momento).
EXECUCOES = {
    "8ce9c32d:final": ("exp04ef1b", "8ce9c32d", "20260925-110608-session_8ce9c32d", "estado final da sessão"),
    "727a3c2d:final": ("exp06ef1b", "727a3c2d", "20260928-084426-session_727a3c2d",
                       "estado final, depois da ratificação do PO de 08/10/2026 11:08 (Pedido 13)"),
    "727a3c2d:02-10": ("exp06ef1b", "727a3c2d",
                       "20260928-084426-session_727a3c2d/.correcoes/20261002-145539-passagem-transversal",
                       "antes da ratificação: passagem de 02/10/2026"),
    "274a2e75:final": ("exp03ef1b", "274a2e75", "20261007-111405-session_274a2e75", "estado final da sessão"),
    "60cfa7f4:22-10": ("exp02em1b", "60cfa7f4", "20261021-110215-session_60cfa7f4/.correcoes/20261022-120224-dev",
                       "o PO pede refazer de dev (22/10/2026 12:02)"),
}


def arquivo_da_sessao(missao: str, sessao: str) -> Path:
    return ESTADOS / f"{missao}-{sessao}.json.xz"


def _enxuto(estado: Dict[str, Any]) -> Dict[str, Any]:
    saida = {k: estado[k] for k in CHAVES if k in estado}
    if "pareceres_humanos" in saida:
        saida["pareceres_humanos"] = [{k: p.get(k) for k in ("etapa", "acao", "comentario", "quando")}
                                      for p in saida["pareceres_humanos"] or [] if isinstance(p, dict)]
    return saida


def main(raw: Path) -> None:
    por_sessao: Dict[str, Dict[str, Any]] = {}
    for eid, (missao, sessao, pasta, momento) in EXECUCOES.items():
        estado = json.loads((raw / pasta / "estado.json").read_text(encoding="utf-8"))
        s = por_sessao.setdefault(f"{missao}-{sessao}", {"missao": missao, "sessao": sessao, "execucoes": {}})
        s["execucoes"][eid] = {"momento": momento, "estado": _enxuto(estado)}
    ESTADOS.mkdir(exist_ok=True)
    for s in por_sessao.values():
        dados = json.dumps(s, ensure_ascii=False, indent=0, sort_keys=True).encode("utf-8")
        arquivo_da_sessao(s["missao"], s["sessao"]).write_bytes(lzma.compress(dados, preset=9 | lzma.PRESET_EXTREME))
        print(arquivo_da_sessao(s["missao"], s["sessao"]).name, ", ".join(s["execucoes"]))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
