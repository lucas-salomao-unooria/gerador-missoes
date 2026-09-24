"""Índice de missões geradas — reconstruir, importar o catálogo legado, promover status e listar.

As sessões em `output/` são a memória; o índice (`output/_catalogo.json`) é cache. Perder o índice
não perde nada: `reconstruir` o refaz varrendo os `estado.json`.

Uso:
  python scripts/catalogo.py listar
  python scripts/catalogo.py reconstruir [--seco]
  python scripts/catalogo.py importar-markdown [--seco]
  python scripts/catalogo.py promover --sessao 20260922-132758-exp06ef1b --status aprovada
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from config import get_settings  # noqa: E402
from prompts import REFERENCES_DIR  # noqa: E402
from tools import catalogo as cat  # noqa: E402

MARKDOWN_LEGADO = REFERENCES_DIR / "catalogo-missoes.md"
#: Colunas do catálogo em markdown, na ordem da tabela.
COLUNAS_LEGADO = ["slug", "ano", "bimestre", "nome", "ambiente", "eixo", "descoberta",
                  "tipo_decisao", "porta_abstracao", "habilidade_primaria", "status"]


def _sessoes() -> list[Path]:
    base = get_settings().output_path
    if not base.exists():
        return []
    return sorted((d for d in base.iterdir() if d.is_dir() and not d.name.startswith(".") and (d / "estado.json").exists()),
                  key=lambda d: d.name)


def reconstruir(seco: bool) -> int:
    """Refaz o índice do zero a partir das sessões salvas. Preserva status humano já atribuído."""
    anterior = {m.get("sessao"): m for m in cat.carregar().get("missoes", [])}
    indice = cat.indice_vazio()
    lidas = 0
    for pasta in _sessoes():
        try:
            state = json.loads((pasta / "estado.json").read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"  ⚠️  {pasta.name}: estado ilegível ({exc})")
            continue
        ficha = cat.ficha_da_execucao(state, sessao=pasta.name)
        velha = anterior.get(pasta.name, {})
        if str(velha.get("status", "")) in cat.STATUS_HUMANOS:
            ficha["status"] = velha["status"]
        r = cat.registrar(ficha, indice, gravar_arquivo=False)
        lidas += 1
        marca = "·" if r["status"] == "aprovado" else "⚠️"
        print(f"  {marca} {pasta.name} → {ficha.get('slug') or '(sem slug)'} · {ficha.get('ano') or '?'} · {ficha.get('ambiente') or '?'} · {ficha['status']}")
        for a in r["achados"]:
            print(f"      ⚠️ {a['codigo']}: {a['resumo'][:120]}")
    # As entradas legadas (sem sessão em disco) sobrevivem à reconstrução.
    for sessao, m in anterior.items():
        if m.get("origem") == "markdown-legado" and not any(x.get("sessao") == sessao for x in indice["missoes"]):
            indice["missoes"].append(m)
    if seco:
        print(f"\n[seco] {lidas} sessão(ões) lida(s); {len(indice['missoes'])} missão(ões) no índice. Nada gravado.")
        return 0
    caminho = cat.gravar(indice)
    print(f"\n✅ {lidas} sessão(ões) lida(s) · {len(indice['missoes'])} missão(ões) → {caminho}")
    return 0


def importar_markdown(seco: bool) -> int:
    """Traz as linhas do catálogo legado em markdown, marcadas como tal."""
    if not MARKDOWN_LEGADO.exists():
        print(f"❌ {MARKDOWN_LEGADO} não existe."); return 1
    indice = cat.carregar()
    novas = 0
    for n, linha in enumerate(MARKDOWN_LEGADO.read_text(encoding="utf-8").splitlines(), 1):
        if not re.match(r"^\|(?!\s*[-:]+\s*\|).+\|\s*$", linha.strip()):
            continue
        celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
        if len(celulas) < 11 or celulas[0].lower() in ("slug", "ano"):
            continue
        ficha = {COLUNAS_LEGADO[i]: celulas[i] for i in range(min(len(celulas), len(COLUNAS_LEGADO)))}
        ficha.update({
            "sessao": f"legado-{n:03d}",
            "origem": "markdown-legado",
            "gates": {},
            "gerada_em": "",
            "ambiente": cat._ambiente(ficha.get("ambiente", "")) or (ficha.get("ambiente") or "").lower().strip("`"),
            "slug": (ficha.get("slug") or "").lower(),
        })
        r = cat.registrar(ficha, indice, gravar_arquivo=False)
        novas += 1
        print(f"  · {ficha['sessao']} → {ficha.get('slug')} · {ficha.get('nome', '')[:40]}")
        for a in r["achados"]:
            print(f"      ⚠️ {a['codigo']}: {a['resumo'][:130]}")
    if seco:
        print(f"\n[seco] {novas} linha(s) legada(s); {len(indice['missoes'])} no total. Nada gravado.")
        return 0
    caminho = cat.gravar(indice)
    print(f"\n✅ {novas} linha(s) importada(s) · {len(indice['missoes'])} missão(ões) → {caminho}")
    return 0


def promover(sessao: str, status: str) -> int:
    if status not in cat.STATUS_HUMANOS:
        print(f"❌ status inválido: {status!r}. Escolha um de {', '.join(cat.STATUS_HUMANOS)} — `em criação` e `bloqueada` são derivados pela esteira.")
        return 1
    indice = cat.carregar()
    alvo = next((m for m in indice.get("missoes", []) if m.get("sessao") == sessao or m.get("slug") == sessao), None)
    if not alvo:
        print(f"❌ não achei `{sessao}` no índice. Use `listar` para ver as sessões."); return 1
    antigo = alvo.get("status")
    alvo["status"] = status
    cat.gravar(indice)
    print(f"✅ {alvo.get('sessao')} ({alvo.get('slug')}): {antigo} → {status}")
    return 0


def listar() -> int:
    indice = cat.carregar()
    missoes = indice.get("missoes", [])
    if not missoes:
        print("Índice vazio. Rode `reconstruir` e `importar-markdown`."); return 0
    print(f"{len(missoes)} missão(ões) · índice gerado em {indice.get('gerado_em') or '—'}\n")
    print(cat.tabela_markdown(missoes))
    lacunas = [m for m in missoes if cat.tem_lacuna(m)]
    if lacunas:
        print(f"\n⚠️ {len(lacunas)} missão(ões) com campo de comparação vazio — não sustentam reprovação em V5:")
        for m in lacunas:
            print(f"   - {m.get('sessao')} ({m.get('slug') or '?'})")
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for nome in ("reconstruir", "importar-markdown"):
        s = sub.add_parser(nome)
        s.add_argument("--seco", action="store_true", help="mostra o que faria, sem gravar")
    sub.add_parser("listar")
    sp = sub.add_parser("promover")
    sp.add_argument("--sessao", required=True, help="nome da pasta da sessão ou slug")
    sp.add_argument("--status", required=True, help=" · ".join(cat.STATUS_HUMANOS))
    a = p.parse_args(argv)
    if a.cmd == "reconstruir":
        return reconstruir(a.seco)
    if a.cmd == "importar-markdown":
        return importar_markdown(a.seco)
    if a.cmd == "promover":
        return promover(a.sessao, a.status)
    return listar()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
