"""O fluxograma da esteira (`scripts/gerar_fluxograma.py`) cobre todos os passos, na ordem, e o .tex publicado está em dia.

O fluxograma é gerado do código: se um agente entra ou sai da esteira e ninguém roda o script, o PDF ao lado do manual
passa a descrever outra esteira. Este teste falha nesse caso, com o comando que conserta.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "scripts"))

import gerar_fluxograma as fx  # noqa: E402

from pipeline.orchestrator import get_pipeline_agents_metadata  # noqa: E402


def test_cada_passo_da_esteira_vira_um_bloco_na_ordem():
    passos = fx.coletar()
    metadados = get_pipeline_agents_metadata(active_only=False)
    assert [p.agente for p in passos] == [m["id"] for m in metadados]
    assert len({p.numero.rstrip("abcdefghij") for p in passos}) == 129
    assert all(p.faz for p in passos) and all(p.grava or p.tipo == "codigo" for p in passos)
    # os ciclos vêm da árvore real: o núcleo roda dentro dos dois comitês
    nucleo = next(p for p in passos if p.agente == "A004NucleoNarrativo")
    assert [n for n, _ in nucleo.loops] == ["ComiteFinalLoop", "ComiteCanaisLoop", "NucleoNarrativoLoop"]
    # o verificador de vários modos mostra o que o modo dele lê, não os campos padrão de todos
    po = next(p for p in passos if p.agente == "A015OnePagerPoCheck")
    assert "one_pager_po" in po.le and "one_pager" in po.le and "handoff_dev" not in po.le


def test_tex_publicado_esta_em_dia():
    publicado = fx.SAIDA.read_text(encoding="utf-8")
    sem_data = lambda t: "\n".join(l for l in t.splitlines() if "Gerado do código em" not in l)  # noqa: E731
    assert sem_data(publicado) == sem_data(fx.gerar()), (
        "O fluxograma está desatualizado: rode `python scripts/gerar_fluxograma.py` e recompile "
        "`manual-unooria/fluxograma-dos-agentes.tex`.")
