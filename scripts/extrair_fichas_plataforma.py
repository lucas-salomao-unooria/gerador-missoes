"""Extração de fichas técnicas da plataforma Unooria (Etapa 4 do Plano Padrão Ouro).

Lê o repositório `plataforma-unooria` e consolida em `references/plataforma/fichas-tecnicas.json`:
- Versão e portas das experiências (`apps/experiencias/*/package.json`);
- Fichas de evidências registradas (`apps/api/src/evidencias/fichas/*.ts`);
- Módulos da API e rotas declaradas;
- Tabelas e migrations conhecidas.

Uso:
  python scripts/extrair_fichas_plataforma.py [--repo ../plataforma-unooria] [--ref origin/dev-local]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

RAIZ = Path(__file__).resolve().parent.parent
SAIDA_PADRAO = RAIZ / "references" / "plataforma" / "fichas-tecnicas.json"


def git_show(repo: Path, ref: str, caminho: str) -> str:
    res = subprocess.run(["git", "show", f"{ref}:{caminho}"], cwd=repo, capture_output=True, text=True)
    return res.stdout if res.returncode == 0 else ""


def git_ls(repo: Path, ref: str, pasta: str) -> List[str]:
    res = subprocess.run(["git", "ls-tree", "--name-only", ref, pasta], cwd=repo, capture_output=True, text=True)
    if res.returncode != 0:
        return []
    return [l.strip() for l in res.stdout.splitlines() if l.strip()]


def extrair_fichas(repo: Path, ref: str) -> Dict[str, Any]:
    fichas: Dict[str, Any] = {}

    # 1. Varre apps/experiencias/
    itens_exp = git_ls(repo, ref, "apps/experiencias/")
    for item in itens_exp:
        nome_pasta = Path(item).name
        if not re.match(r"^exp\d{2}(?:ef|em)\d(?:b)?$", nome_pasta, re.IGNORECASE):
            continue
        slug = nome_pasta.lower()
        pkg_json_raw = git_show(repo, ref, f"apps/experiencias/{nome_pasta}/package.json")
        versao = ""
        porta = 0
        if pkg_json_raw:
            try:
                pkg = json.loads(pkg_json_raw)
                versao = pkg.get("version", "")
                scripts = pkg.get("scripts", {})
                dev_script = scripts.get("dev", "")
                m_port = re.search(r"--port\s+(\d+)", dev_script)
                if m_port:
                    porta = int(m_port.group(1))
            except Exception:
                pass

        fichas[slug] = {
            "slug": slug,
            "pasta": f"apps/experiencias/{nome_pasta}",
            "versao": versao,
            "porta": porta,
            "modulo_api": "",
            "rotas": [],
            "ficha_evidencia_arquivo": "",
            "tabelas": [],
        }

    # 2. Mapeia fichas de evidências em apps/api/src/evidencias/fichas/
    itens_fichas = git_ls(repo, ref, "apps/api/src/evidencias/fichas/")
    for item in itens_fichas:
        nome_arq = Path(item).name
        m_slug = re.match(r"^(exp\d{2}(?:ef|em)\d(?:b)?)\.ts$", nome_arq, re.IGNORECASE)
        if m_slug:
            slug = m_slug.group(1).lower()
            if slug not in fichas:
                fichas[slug] = {
                    "slug": slug,
                    "pasta": f"apps/experiencias/{slug}",
                    "versao": "",
                    "porta": 0,
                    "modulo_api": "",
                    "rotas": [],
                    "ficha_evidencia_arquivo": item,
                    "tabelas": [],
                }
            else:
                fichas[slug]["ficha_evidencia_arquivo"] = item

    # 3. Mapeia módulos da api conhecidos
    itens_api = git_ls(repo, ref, "apps/api/src/")
    modulo_para_slug = {
        "juri-estadual": "exp06ef1b",
        "a-selecao": "exp07ef1b",
        "foto-conta": "exp01ef1b",
        "unootube": "exp04ef1b",
        "dossie": "exp08ef1b",
    }
    for mod, slug in modulo_para_slug.items():
        if slug in fichas:
            fichas[slug]["modulo_api"] = f"apps/api/src/{mod}"

    return fichas


def extrair_esquema(repo: Path, ref: str) -> Dict[str, Any]:
    """Tabelas, colunas, tipos e chaves estrangeiras depois de todas as migrations (`tools/esquema_plataforma`)."""
    import sys

    sys.path.insert(0, str(RAIZ))
    from tools.esquema_plataforma import ler_migrations

    pastas = sorted(git_ls(repo, ref, "apps/api/prisma/migrations/"))
    sql = "\n".join(git_show(repo, ref, f"{p}/migration.sql") for p in pastas)
    tabelas, fks = ler_migrations(sql)
    return {"tabelas_plataforma": tabelas,
            "chaves_estrangeiras": {t: {c: list(a) for c, a in r.items()} for t, r in fks.items()}}


def tabelas_da_missao(slug: str, tabelas: Dict[str, Dict[str, str]]) -> List[str]:
    """`exp05ef1b_*` e o prefixo legado `exp_05_*` (missões publicadas antes do id inteiro no nome)."""
    m = re.match(r"exp(\d{2})", slug)
    legado = f"exp_{m.group(1)}_" if m and slug.endswith("ef1b") else None
    return sorted(t for t in tabelas if t.startswith(f"{slug}_") or (legado and t.startswith(legado)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(RAIZ.parent / "plataforma-unooria"), help="Caminho do monorepo da plataforma")
    parser.add_argument("--ref", default="origin/dev-local", help="Referência git da plataforma")
    parser.add_argument("--saida", default=str(SAIDA_PADRAO), help="Caminho de saída do JSON consolidado")
    args = parser.parse_args()

    repo = Path(args.repo)
    if not repo.exists():
        print(f"❌ Repositório não encontrado em {repo}")
        raise SystemExit(1)

    print(f"🔍 Extraindo fichas da plataforma em {repo} @ {args.ref}...")
    fichas = extrair_fichas(repo, args.ref)
    esquema = extrair_esquema(repo, args.ref)
    for slug, ficha in fichas.items():
        ficha["tabelas"] = tabelas_da_missao(slug, esquema["tabelas_plataforma"])

    saida = Path(args.saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps({"fichas": fichas, **esquema}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✅ {len(fichas)} fichas técnicas consolidadas salvas em {saida}")


if __name__ == "__main__":
    main()
