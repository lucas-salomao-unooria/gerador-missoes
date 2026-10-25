#!/usr/bin/env python3
"""scripts/gravar_cache_classificador.py

Regrava o cache versionado do classificador de sentido (`fixtures/classificador-cache.json`, `tools/classificador.py`),
para o CI e a regressão rodarem sem chamar o modelo. Chama o modelo só para a leitura que falta no cache: rodar de novo
sem nada novo custa zero. Precisa de rede e da chave do Gemini.

Uso:
    python scripts/gravar_cache_classificador.py --gabarito            # os casos de tests/gabarito_achados/classificador
    python scripts/gravar_cache_classificador.py --regressao           # os gates das 15 missões do acervo
    python scripts/gravar_cache_classificador.py --testes [-- args]    # a suíte (o que os testes leem)
    python scripts/gravar_cache_classificador.py --env /caminho/.env --gabarito --regressao --testes

Do `.env` só a chave é lida (`GOOGLE_API_KEY` ou `GEMINI_API_KEY`): o resto dele — modelo, ESTEIRA_ESTRITA, modo da
correção — mudaria o que os testes perguntam e o hash do cache. O modelo é o padrão do app, o mesmo do CI. A chave nunca
é impressa.

Quando subir a versão de uma pergunta (o texto do prompt mudou), rode com `--gabarito` e confira as métricas
(`tests/gabarito_achados/test_classificador_gabarito.py`) antes de `--regressao` e `--testes`.
"""
from __future__ import annotations

import argparse
import json
import lzma
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
GABARITO = RAIZ / "tests" / "gabarito_achados" / "classificador"


def _carregar_chave(env: Path) -> bool:
    if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        return True
    if not env.exists():
        return False
    from dotenv import dotenv_values

    valores = dotenv_values(env)
    for nome in ("GOOGLE_API_KEY", "GEMINI_API_KEY"):
        if valores.get(nome):
            os.environ[nome] = str(valores[nome])
            return True
    return False


def casos_do_gabarito():
    """`(Pergunta, caso)` de cada caso do gabarito do classificador."""
    from tools import classificador

    for arquivo in sorted(GABARITO.glob("*.jsonl.xz")):
        pergunta = classificador.PERGUNTAS[arquivo.name.split(".")[0]]
        for linha in lzma.decompress(arquivo.read_bytes()).decode("utf-8").splitlines():
            if linha.strip():
                yield pergunta, json.loads(linha)


def main() -> int:
    parser = argparse.ArgumentParser(description="Regrava o cache versionado do classificador de sentido.")
    parser.add_argument("--env", type=Path, default=RAIZ / ".env", help="de onde ler só a chave do Gemini")
    parser.add_argument("--gabarito", action="store_true")
    parser.add_argument("--regressao", action="store_true")
    parser.add_argument("--testes", action="store_true")
    parser.add_argument("resto", nargs=argparse.REMAINDER, help="argumentos do pytest, depois de --")
    args = parser.parse_args()
    if not (args.gabarito or args.regressao or args.testes):
        parser.error("escolha --gabarito, --regressao e/ou --testes")
    if not _carregar_chave(args.env):
        print("❌ Sem GOOGLE_API_KEY/GEMINI_API_KEY no ambiente nem no .env indicado.", file=sys.stderr)
        return 1
    os.environ.pop("GEMINI_MODEL", None)
    os.environ["CLASSIFICADOR_SENTIDO"] = "ligado"
    os.environ["CLASSIFICADOR_GRAVAR_CACHE_FIXO"] = "1"
    os.environ["CLASSIFICADOR_CACHE_FIXO"] = str(RAIZ / "fixtures" / "classificador-cache.json")

    from tools import classificador

    antes = len(classificador._cache_fixo())
    if args.gabarito:
        por_pergunta = {}
        for pergunta, caso in casos_do_gabarito():
            por_pergunta.setdefault(pergunta.id, (pergunta, []))[1].append(caso["entrada"])
        for pergunta, entradas in por_pergunta.values():
            lidas = classificador.ler(pergunta, entradas)
            print(f"📚 {pergunta.id} {pergunta.versao}: {len(lidas)} casos, "
                  f"{sum(1 for l in lidas if l.nao_sei)} «nao_sei»")
    if args.regressao:
        from scripts.regressao_gates import avaliar_acervo

        avaliar_acervo(RAIZ / "tests" / "acervo")
        print("📂 regressão avaliada")
    codigo = 0
    if args.testes:
        import pytest

        codigo = int(pytest.main(["-q", "-p", "no:cacheprovider", "--ignore=tests/mutantes",
                                  *[a for a in args.resto if a != "--"]]))
    depois = len(classificador._cache_fixo())
    print(f"💾 cache de teste: {antes} → {depois} leituras ({depois - antes} novas)")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
