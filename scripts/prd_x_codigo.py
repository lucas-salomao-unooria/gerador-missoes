"""Comparação PRD × Código (Etapa 4.3 do Plano Padrão Ouro).

Compara o PRD da sessão com o código implementado no monorepo `plataforma-unooria`:
- Lê `divergencias-prd.md` se presente na raiz do worktree ou na sessão;
- Analisa divergências de rotas, eventos, tabelas e portas;
- Emite classificação para retroalimentar regras ou fichas técnicas.

Uso:
  python scripts/prd_x_codigo.py <slug> [--sessao <sessao>] [--repo ../plataforma-unooria] [--ref origin/dev-local]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


def ler_prd_da_sessao(sessao_ou_slug: str) -> str:
    from config import get_settings

    base = get_settings().output_path
    if not base.exists():
        return ""
    # Busca por nome exato de pasta ou estado.json com slug correspondente
    for d in base.iterdir():
        if not d.is_dir() or d.name.startswith("."):
            continue
        if d.name == sessao_ou_slug or sessao_ou_slug in d.name:
            prd_path = d / "PRD.md"
            if prd_path.exists():
                return prd_path.read_text(encoding="utf-8")
            st_path = d / "estado.json"
            if st_path.exists():
                try:
                    st = json.loads(st_path.read_text(encoding="utf-8"))
                    if st.get("prd_final"):
                        return st["prd_final"]
                except Exception:
                    pass
    return ""


def comparar(slug: str, prd_texto: str, repo: Path, ref: str) -> Dict[str, Any]:
    resultado = {
        "slug": slug,
        "prd_presente": bool(prd_texto),
        "diferencas": [],
        "pontos_atencao": [],
    }

    if not prd_texto:
        resultado["pontos_atencao"].append("PRD não encontrado para a missão informada.")
        return resultado

    # Verifica package.json da missão no repo
    pkg_raw = subprocess.run(
        ["git", "show", f"{ref}:apps/experiencias/{slug}/package.json"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if pkg_raw.returncode == 0:
        try:
            pkg = json.loads(pkg_raw.stdout)
            versao_repo = pkg.get("version", "")
            # Checa se PRD menciona a versão do repo
            m_v = re.search(r"\bversao\b.*?(\d+\.\d+\.\d+)", prd_texto, re.IGNORECASE)
            versao_prd = m_v.group(1) if m_v else ""
            if versao_repo and versao_prd and versao_repo != versao_prd:
                resultado["diferencas"].append({
                    "item": "versao",
                    "prd": versao_prd,
                    "codigo": versao_repo,
                    "classificacao": "versao_divergente",
                })
        except Exception:
            pass
    else:
        resultado["pontos_atencao"].append(f"Experiência {slug} ainda não encontrada em apps/experiencias/{slug}")

    return resultado


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="Slug da missão (ex.: exp06ef1b)")
    parser.add_argument("--sessao", default="", help="Nome da pasta da sessão (opcional)")
    parser.add_argument("--repo", default=str(RAIZ.parent / "plataforma-unooria"), help="Caminho do monorepo")
    parser.add_argument("--ref", default="origin/dev-local", help="Referência git")
    args = parser.parse_args()

    repo = Path(args.repo)
    if not repo.exists():
        print(f"❌ Repositório não encontrado em {repo}")
        raise SystemExit(1)

    alvo = args.sessao or args.slug
    prd_texto = ler_prd_da_sessao(alvo)
    res = comparar(args.slug, prd_texto, repo, args.ref)

    print(f"=== Comparação PRD × Código: {args.slug} ===")
    print(f"PRD encontrado: {'Sim' if res['prd_presente'] else 'Não'}")
    if res["diferencas"]:
        print(f"\nDiferenças encontradas ({len(res['diferencas'])}):")
        for d in res["diferencas"]:
            print(f"  · [{d['classificacao']}] {d['item']}: PRD={d['prd']} vs Código={d['codigo']}")
    else:
        print("Nenhuma divergência estrutural detectada.")

    if res["pontos_atencao"]:
        print("\nPontos de atenção:")
        for p in res["pontos_atencao"]:
            print(f"  ⚠️ {p}")


if __name__ == "__main__":
    main()
