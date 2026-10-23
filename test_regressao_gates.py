"""test_regressao_gates.py

Validação contínua da suíte de regressão de gates determinísticos sobre o acervo dourado.
Garante que nenhuma PR altere os vereditos ou códigos de achados sem atualização explícita
da linha de base (tests/acervo/linha-de-base.json).
"""

from pathlib import Path
import json
import pytest

from scripts.regressao_gates import (
    RAIZ,
    avaliar_acervo,
    comparar_linhas_de_base,
)


def test_regressao_gates_linha_de_base():
    """Executa a regressão determinística e compara com a linha de base congelada."""
    acervo_dir = RAIZ / "tests" / "acervo"
    linha_de_base_file = acervo_dir / "linha-de-base.json"

    assert acervo_dir.exists(), f"Diretório de acervo não encontrado: {acervo_dir}"
    assert linha_de_base_file.exists(), f"Linha de base não encontrada: {linha_de_base_file}"

    base = json.loads(linha_de_base_file.read_text(encoding="utf-8"))
    atual = avaliar_acervo(acervo_dir)

    diffs = comparar_linhas_de_base(base, atual)
    assert not diffs, (
        f"Regressão detectada em relação à linha de base ({len(diffs)} divergência(s)):\n"
        + "\n".join(f"  - {d}" for d in diffs)
        + "\nSe as alterações foram intencionais, atualize a linha de base com:\n"
        + "  python scripts/regressao_gates.py --gravar-linha-de-base"
    )
