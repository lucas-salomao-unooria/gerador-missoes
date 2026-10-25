"""Monta os estados do gabarito de achados a partir das sessões do bucket (só leitura sobre elas).

O gabarito (`tests/gabarito_achados/test_*.py`) roda os gates determinísticos de dev sobre o estado real de cada
execução em que o achado foi classificado — verdadeiro (V) ou falso positivo (FP) — no levantamento de deficiências de
24/10/2026. Este script grava, por sessão, um `<missão>-<sessão>.json.xz` com as execuções dela: só as chaves que
esses gates leem (`CHAVES`), e dos pareceres humanos só o pedido de refazer de design e dev (etapa, ação, comentário,
data), sem conta nem assinatura. Os documentos repetem de uma execução para a outra; o xz guarda cada um uma vez.

Uso (a pasta é a cópia das sessões do bucket, `<sessão>/estado.json` e `<sessão>/.correcoes/<quando>-<etapa>/`):

    python tests/gabarito_achados/extrair_estados.py /caminho/para/raw
"""
from __future__ import annotations

import json
import lzma
import sys
from pathlib import Path
from typing import Any, Dict

ESTADOS = Path(__file__).resolve().parent / "estados"

#: O que os gates do gabarito leem do estado (montagem do PRD e do handoff, rastro do PRD, PRD codável e a
#: conferência com a plataforma), medido em 24/10/2026. `edicoes_pontuais` e `modo_correcao`: as trocas da correção
#: pontual, origem de número da montagem desde a terceira revisão do PR #77.
CHAVES = ("anexo_design_spec", "banco_conteudo", "briefing", "decisoes_do_po", "edicoes_pontuais", "fechamento_lacunas",
          "fluxo_arestas", "handoff_dev", "jornada_telas", "lacunas_status_envelope", "modo_correcao",
          "notas_de_passagem", "nucleo_narrativo", "one_pager", "one_pager_po", "pareceres_humanos", "pedidos_do_po",
          "prd_final", "slug", "spec_missao", "spec_missao_gate0", "wireframes_cobertura")

#: As 13 execuções de dev de 25/09 a 23/10/2026 (`deficiencias/dev/achados.csv`, coluna `run`): id → (missão, sessão,
#: pasta da cópia, momento). `.correcoes/<quando>-<etapa>` é o estado que o PO tinha diante de si ao pedir o refazer.
EXECUCOES = {
    "R01": ("exp04ef1b", "8ce9c32d", "20260925-110608-session_8ce9c32d/.correcoes/20260925-151458-dev",
            "o PO pede o 1º refazer de dev (25/09/2026 15:14)"),
    "R02": ("exp04ef1b", "8ce9c32d", "20260925-110608-session_8ce9c32d/.correcoes/20260925-154433-dev",
            "o PO pede o 2º refazer de dev (25/09/2026 15:44)"),
    "R03": ("exp04ef1b", "8ce9c32d", "20260925-110608-session_8ce9c32d", "estado final da sessão"),
    "R04": ("exp06ef1b", "727a3c2d", "20260928-084426-session_727a3c2d/.correcoes/20261008-094902-produto",
            "o PO devolve a produto (08/10/2026 09:49)"),
    "R05": ("exp01ef1b", "4e6cf385", "20260928-092207-session_4e6cf385/.correcoes/20260929-135911-dev",
            "o PO pede refazer de dev (29/09/2026 13:59)"),
    "R06": ("exp01ef1b", "4e6cf385", "20260928-092207-session_4e6cf385/.correcoes/20261006-094156-produto",
            "o PO devolve a produto (06/10/2026 09:41)"),
    "R07": ("exp01ef1b", "4e6cf385", "20260928-092207-session_4e6cf385", "estado final da sessão"),
    "R08": ("exp09ef1b", "c19d3cb0", "20260930-095201-session_c19d3cb0", "estado final da sessão"),
    "R09": ("exp06ef1b", "53e011b6", "20261008-140726-session_53e011b6/.correcoes/20261010-115540-dev",
            "o PO pede refazer de dev (10/10/2026 11:55)"),
    "R10": ("exp06ef1b", "53e011b6", "20261008-140726-session_53e011b6", "estado final da sessão"),
    "R11": ("exp02em1b", "60cfa7f4", "20261021-110215-session_60cfa7f4/.correcoes/20261022-120224-dev",
            "o PO pede refazer de dev (22/10/2026 12:02)"),
    "R12": ("exp02em1b", "60cfa7f4", "20261021-110215-session_60cfa7f4/.correcoes/20261023-110444-produto",
            "o PO devolve a produto (23/10/2026 11:04)"),
    "R13": ("exp02ef1b", "4fd72a9a", "20261022-145435-session_4fd72a9a", "estado final da sessão"),
}


def arquivo_da_sessao(missao: str, sessao: str) -> Path:
    return ESTADOS / f"{missao}-{sessao}.json.xz"


def _enxuto(estado: Dict[str, Any]) -> Dict[str, Any]:
    saida = {k: estado[k] for k in CHAVES if k in estado}
    if "pareceres_humanos" in saida:
        saida["pareceres_humanos"] = [
            {k: p.get(k) for k in ("etapa", "acao", "comentario", "quando")}
            for p in saida["pareceres_humanos"] or []
            if isinstance(p, dict) and p.get("acao") == "refazer" and p.get("etapa") in ("design", "dev")]
    return saida


def main(raw: Path) -> None:
    por_sessao: Dict[str, Dict[str, Any]] = {}
    for rid, (missao, sessao, pasta, momento) in EXECUCOES.items():
        estado = json.loads((raw / pasta / "estado.json").read_text(encoding="utf-8"))
        s = por_sessao.setdefault(f"{missao}-{sessao}", {"missao": missao, "sessao": sessao, "execucoes": {}})
        s["execucoes"][rid] = {"momento": momento, "estado": _enxuto(estado)}
    ESTADOS.mkdir(exist_ok=True)
    for s in por_sessao.values():
        dados = json.dumps(s, ensure_ascii=False, indent=0, sort_keys=True).encode("utf-8")
        arquivo_da_sessao(s["missao"], s["sessao"]).write_bytes(lzma.compress(dados, preset=9 | lzma.PRESET_EXTREME))
        print(arquivo_da_sessao(s["missao"], s["sessao"]).name, ", ".join(s["execucoes"]))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
