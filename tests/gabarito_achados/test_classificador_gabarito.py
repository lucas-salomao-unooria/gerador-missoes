"""Gabarito do classificador de sentido (C7): os casos da fase A, por pergunta, com o rótulo e a origem, lidos pelo cache
versionado (`fixtures/classificador-cache.json`) — o CI mede sem chamar o modelo.

Os casos (`classificador/<pergunta>.jsonl.xz`) vêm de `analises-esteira/2026-10-25/c7/casos`, sem nenhum inventado:
- `real`: o achado do levantamento de 24/10/2026, com o trecho da execução e o rótulo dele (V/FP);
- `mutante`: o que os gabaritos e as revisões da C1 e da C3 escreveram sobre estado real, antes e sem conhecer o prompt
  (as 17 paráfrases da H1 30×25, as recusas em prosa do StoryPoll, as denúncias sem número);
- `holdout`: candidatos reais que a regra recorta no acervo, fora do gabarito, sorteados com semente fixa e rotulados às
  cegas antes de rodar o classificador;
- `ambiguo`: o rótulo admite leitura contrária; fica fora das métricas.

Precisão e revocação da classe que faz a regra agir — «nao_sei» conta como disparo, como na fase A (vai a 🟡). Os mínimos
são os da fase A com folga: um caso a mais errado em cada pergunta ainda passa; dois, não.
"""
from __future__ import annotations

import json
import lzma
from collections import Counter
from pathlib import Path

import pytest

from tools import classificador

PASTA = Path(__file__).resolve().parent / "classificador"

#: pergunta → (classe que faz a regra agir, precisão mínima, revocação mínima). Fase A: hipótese 1,00/1,00 (60 casos);
#: botão 1,00/1,00 (55 + 3 ambíguos); item do pedido v2 1,00/0,93 (53); decisão do PO 1,00/1,00 (53); ressalva 0,97/1,00
#: (37).
MINIMOS = {
    "numero_da_hipotese": ("meta", 0.95, 0.95),
    "rotulo_de_botao": ("rotulo_de_botao", 0.90, 0.90),
    "item_do_pedido_classe": ("exigencia", 0.95, 0.88),
    "decisao_do_po_confirmada": ("nao_confirmada", 0.95, 0.95),
    "ressalva_repete_decisao_do_po": ("aponta_problema", 0.92, 0.95),
}


def _casos(pergunta: str):
    texto = lzma.decompress((PASTA / f"{pergunta}.jsonl.xz").read_bytes()).decode("utf-8")
    return [json.loads(l) for l in texto.splitlines() if l.strip()]


@pytest.fixture(autouse=True)
def _so_o_cache_de_teste(monkeypatch):
    monkeypatch.setenv(classificador.ENV_MODO, "so_cache")
    monkeypatch.delenv(classificador.ENV_GRAVAR_CACHE_FIXO, raising=False)


def test_todo_caso_tem_rotulo_origem_e_a_pergunta_dele():
    assert sorted(p.name.split(".")[0] for p in PASTA.glob("*.jsonl.xz")) == sorted(classificador.PERGUNTAS)
    for pergunta, (positivo, _, _) in MINIMOS.items():
        p = classificador.PERGUNTAS[pergunta]
        casos = _casos(pergunta)
        assert casos and len({c["id"] for c in casos}) == len(casos)
        for c in casos:
            assert c["pergunta"] == pergunta and c["versao"] == p.versao, c["id"]
            assert c["rotulo"] in p.rotulos and c["tipo"] in ("real", "mutante", "holdout", "ambiguo"), c["id"]
            assert c["origem"] or c["tipo"] == "holdout", c["id"]
        assert {c["rotulo"] for c in casos if c["tipo"] != "ambiguo"} >= {positivo}


@pytest.mark.parametrize("pergunta", sorted(MINIMOS))
def test_precisao_e_revocacao_minimas_pelo_cache(pergunta):
    positivo, p_min, r_min = MINIMOS[pergunta]
    p = classificador.PERGUNTAS[pergunta]
    casos = [c for c in _casos(pergunta) if c["tipo"] != "ambiguo"]
    lidas = classificador.ler(p, [c["entrada"] for c in casos])
    fora = [c["id"] for c, l in zip(casos, lidas) if l.motivo == "fora do cache"]
    assert not fora, f"casos sem leitura no cache de teste (rode scripts/gravar_cache_classificador.py --gabarito): {fora}"
    n = Counter()
    for c, l in zip(casos, lidas):
        dispara = l.rotulo in (positivo, classificador.NAO_SEI)
        certo = c["rotulo"] == positivo
        n["tp"] += dispara and certo
        n["fp"] += dispara and not certo
        n["fn"] += (not dispara) and certo
    precisao = n["tp"] / (n["tp"] + n["fp"])
    revocacao = n["tp"] / (n["tp"] + n["fn"])
    assert precisao >= p_min and revocacao >= r_min, (pergunta, dict(n), round(precisao, 2), round(revocacao, 2))


def test_os_erros_da_fase_a_continuam_os_mesmos():
    """Os erros que a fase A listou, um a um (`c7/saidas/medicao.md`): se mudarem, a medição mudou e alguém tem de ler."""
    erros = {}
    for pergunta, (positivo, _, _) in MINIMOS.items():
        p = classificador.PERGUNTAS[pergunta]
        casos = [c for c in _casos(pergunta) if c["tipo"] != "ambiguo"]
        for c, l in zip(casos, classificador.ler(p, [c["entrada"] for c in casos])):
            if l.rotulo != c["rotulo"]:
                erros[c["id"]] = l.rotulo
    # três títulos «Redesenho do Canal A de … (secundária)» lidos como contexto; P096, discutível (o levantamento diz
    # repetição, a C3 diz resíduo)
    assert erros == {"FID2-P100": "contexto", "FID2-P104": "contexto", "FID2-P109": "contexto",
                     "RESS-P096": "aponta_problema"}
