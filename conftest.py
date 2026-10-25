"""Os testes leem uma base da plataforma congelada em `fixtures/base-plataforma`.

Em produção a base vem do bucket (`prompts/base_plataforma.py`), regravada pelo CI da plataforma e do
storybook. Nos testes ela é uma fotografia: gerada com `node scripts/base-do-gerador/extrair.mjs --saida`
na plataforma e `node scripts/inventario-para-o-gerador.mjs --saida` no storybook, e copiada para cá.
Para testar contra outra base, exporte `BASE_PLATAFORMA_DIR`.
"""

import os
from pathlib import Path

os.environ.setdefault("BASE_PLATAFORMA_DIR", str(Path(__file__).resolve().parent / "fixtures" / "base-plataforma"))
# A correção pontual chama o editor (um modelo) antes da esteira. Teste não chama modelo: os que exercitam a correção
# pontual a ligam e injetam um editor falso (`executar_correcao_stream(..., proponente=...)`).
os.environ.setdefault("CORRECAO_PONTUAL", "false")
os.environ.setdefault("RETRABALHO_POR_TROCAS", "false")
# O classificador de sentido (`tools/classificador.py`, C7) também não chama modelo nos testes: lê o cache versionado
# (`fixtures/classificador-cache.json`), e o que não está nele é «nao_sei». Regravar com rede e chave:
# `python scripts/gravar_cache_classificador.py`.
os.environ.setdefault("CLASSIFICADOR_SENTIDO", "so_cache")
os.environ.setdefault("CLASSIFICADOR_CACHE_FIXO",
                      str(Path(__file__).resolve().parent / "fixtures" / "classificador-cache.json"))
