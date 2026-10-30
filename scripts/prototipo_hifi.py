"""Gera o protótipo em alta fidelidade de uma sessão salva, com o Antigravity SDK — teste fora da esteira.

    .venv/bin/python scripts/prototipo_hifi.py --sessao output/<pasta> --destino <workspace> \
        --ds /Volumes/Documentos/Unooria/storybook-unooria [--paralelo 3] [--so-final]

1. Monta o workspace (`tools.prototipo_hifi.montar_workspace`).
2. Roda o lote de fundação (molduras em `_comum.tsx` + uma tela âncora por ator).
3. Roda os lotes por etapa em paralelo, cada um num subprocesso do motor na `.venv-antigravity`.
4. Fecha com build final, auditoria, captura de todos os quadros, rastreio do texto, lint do protótipo da
   esteira (`tools.prototipo.validar`) e um `RELATORIO.md` com tempo, tokens e o que ficou pendente.

A chave vem de `GEMINI_API_KEY` ou `GOOGLE_API_KEY` (o `.env` da esteira).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from dotenv import load_dotenv  # noqa: E402

from tools import prototipo as lint_prototipo  # noqa: E402
from tools.prototipo_hifi import ferramentas, lotes, montar_workspace  # noqa: E402

PYTHON_MOTOR = RAIZ / ".venv-antigravity" / "bin" / "python"
MOTOR = RAIZ / "tools" / "prototipo_hifi" / "motor_antigravity.py"


def _motor(ws: Path, lote: dict, modelo: str | None) -> dict:
    cmd = [str(PYTHON_MOTOR), "-I", str(MOTOR), "--ws", str(ws), "--lote", lote["nome"], "--ids", ",".join(lote["ids"])]
    if lote["fundacao"]:
        cmd.append("--fundacao")
    if modelo:
        cmd += ["--modelo", modelo]
    (ws / "logs").mkdir(exist_ok=True)
    t0 = time.time()
    with open(ws / "logs" / f"{lote['nome']}.log", "w", encoding="utf-8") as log:
        proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=os.environ.copy())
    rel = ws / "relatorios" / f"{lote['nome']}.json"
    dados = json.loads(rel.read_text(encoding="utf-8")) if rel.exists() else {}
    print(f"  {lote['nome']}: saída {proc.returncode}, {round(time.time() - t0)} s, aprovado={dados.get('aprovado')}", flush=True)
    return dados or {"lote": lote["nome"], "aprovado": False, "erro": f"motor saiu com {proc.returncode}, ver logs/{lote['nome']}.log"}


def fechar(ws: Path, sessao: Path, relatorios: list[dict], segundos: float) -> dict:
    """Build final, auditoria, capturas de todos os quadros, rastreio de texto e o relatório."""
    final = ferramentas.construir(ws, saida=ws / "prototipo.html")
    audit = ferramentas.auditar(ws, final["html"]) if final["ok"] else {"quadros": [], "faltando": [], "com_erro": []}
    missao = json.loads((ws / "dados" / "missao.json").read_text(encoding="utf-8"))
    capturas = []
    if final["ok"]:
        def cap(q: dict) -> dict:
            return ferramentas.capturar(ws, q["id"], q["estado"], final["html"])
        with ThreadPoolExecutor(max_workers=4) as pool:
            capturas = list(pool.map(cap, missao["quadros"]))
    corpus = "\n".join((ws / "insumos" / n).read_text(encoding="utf-8") for n in os.listdir(ws / "insumos"))
    texto = ferramentas.rastrear_texto(audit.get("quadros", []), corpus)
    lint_estatico = ferramentas.lint(ws)
    # o lint do protótipo da esteira lê o HTML: aqui os quadros nascem no navegador, então ele lê o DOM da auditoria
    dom = "".join(f'<div data-screen-id="{q["id"]}" data-estado="{q["estado"]}">{" ".join(q["texto"])}</div>'
                  for q in audit.get("quadros", []) if not q["faltando"] and not q["erro"])
    lint_esteira = lint_prototipo.validar("<html><body>" + dom + "</body></html>",
                                          sorted({q["id"] for q in missao["quadros"]}))
    uso = {k: sum(r.get("uso", {}).get(k, 0) for r in relatorios) for k in ("prompt", "cache", "saida", "pensamento", "total")}
    resumo = {"missao": missao["missao"], "quadros": len(missao["quadros"]), "telas": len({q["id"] for q in missao["quadros"]}),
              "build_final": final["ok"], "kb": final["kb"], "faltando": audit.get("faltando", []),
              "com_erro": audit.get("com_erro", []), "lint_estatico": lint_estatico["achados"],
              "lint_esteira": {"status": lint_esteira.get("status"), "achados": lint_esteira.get("achados", [])},
              "texto_rastreavel_pct": texto["percentual"], "linhas_de_texto": texto["linhas"],
              "segundos": round(segundos), "uso": uso,
              "lotes": [{k: r.get(k) for k in ("lote", "aprovado", "rodadas", "segundos", "uso", "gates", "erro")} for r in relatorios],
              "capturas": sum(1 for c in capturas if c.get("ok"))}
    (ws / "relatorios").mkdir(exist_ok=True)
    (ws / "relatorios" / "final.json").write_text(json.dumps({**resumo, "texto": texto}, ensure_ascii=False, indent=1), encoding="utf-8")
    _galeria(ws, missao)
    _relatorio_md(ws, sessao, resumo, texto)
    return resumo


def _galeria(ws: Path, missao: dict) -> None:
    """`capturas/index.html`: todas as capturas numa página, na ordem do trilho, para comparar com o código."""
    blocos = [f'<figure><img src="{q["id"]}--{ferramentas.slug(q["estado"])}.png" loading="lazy">'
              f'<figcaption><b>{q["id"]}</b> · {q["estado"]}</figcaption></figure>' for q in missao["quadros"]]
    (ws / "capturas" / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>Capturas</title><style>body{font:14px system-ui;margin:24px;background:#eee}'
        'main{display:grid;grid-template-columns:repeat(auto-fill,minmax(480px,1fr));gap:20px}figure{margin:0;background:#fff;padding:8px;border-radius:8px}'
        'img{width:100%;border:1px solid #ccc}</style><h1>' + missao["titulo"] + "</h1><main>" + "".join(blocos) + "</main>",
        encoding="utf-8")


def _relatorio_md(ws: Path, sessao: Path, r: dict, texto: dict) -> None:
    linhas = [f"# Protótipo hi-fi — {r['missao']} (Antigravity SDK)", "",
              f"- Sessão: `{sessao}`",
              f"- Quadros: {r['quadros']} ({r['telas']} telas) · capturados: {r['capturas']}",
              f"- Build final: {'ok' if r['build_final'] else 'FALHOU'} · {r['kb']} KB",
              f"- Faltando: {len(r['faltando'])} · com erro de montagem: {len(r['com_erro'])} · achados de lint: {len(r['lint_estatico'])}",
              f"- Lint do protótipo da esteira: {r['lint_esteira']['status']}",
              f"- Texto visível rastreável aos documentos: {r['texto_rastreavel_pct']}% de {r['linhas_de_texto']} linhas",
              f"- Tempo total: {r['segundos'] // 60} min · tokens: {r['uso']['total']:,} (saída {r['uso']['saida']:,}, pensamento {r['uso']['pensamento']:,}, cache {r['uso']['cache']:,})",
              "", "## Lotes", "", "| Lote | Aprovado | Rodadas | Tempo | Tokens |", "|---|---|---|---|---|"]
    for l in r["lotes"]:
        linhas.append(f"| {l.get('lote')} | {'sim' if l.get('aprovado') else 'não'} | {l.get('rodadas')} | "
                      f"{(l.get('segundos') or 0) // 60} min | {(l.get('uso') or {}).get('total', 0):,} |")
    for titulo, itens in (("Faltando", r["faltando"]), ("Erro de montagem", r["com_erro"]),
                          ("Lint", [f"{a['arquivo']}: {a['codigo']} `{a['trecho']}`" for a in r["lint_estatico"]])):
        if itens:
            linhas += ["", f"## {titulo}", ""] + [f"- {i}" for i in itens]
    fora = [q for q in texto["por_quadro"] if q["fora"]]
    if fora:
        linhas += ["", "## Texto que não aparece nos documentos (informativo)", ""]
        for q in fora:
            linhas.append(f"- **{q['id']} · {q['estado']}**: " + " · ".join(f"«{t[:80]}»" for t in q["fora"][:6]))
    (ws / "RELATORIO.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sessao", required=True)
    ap.add_argument("--destino", required=True)
    ap.add_argument("--ds", required=True, help="raiz do pacote @unooria/design-system (storybook-unooria)")
    ap.add_argument("--paralelo", type=int, default=3)
    ap.add_argument("--modelo", default=None)
    ap.add_argument("--pular-fundacao", action="store_true", help="a fundação já rodou neste workspace")
    ap.add_argument("--so-final", action="store_true", help="só o fechamento (build, auditoria, capturas, relatório)")
    a = ap.parse_args()
    load_dotenv(RAIZ / ".env")
    sessao, ws = Path(a.sessao).resolve(), Path(a.destino).resolve()
    t0 = time.time()
    if not (ws / "dados" / "missao.json").exists():
        montar_workspace(sessao, ws, a.ds)
    missao = json.loads((ws / "dados" / "missao.json").read_text(encoding="utf-8"))
    plano = lotes(missao)
    relatorios: list[dict] = []
    if not a.so_final:
        if not a.pular_fundacao:
            print("fundação…", flush=True)
            relatorios.append(_motor(ws, plano[0], a.modelo))
        print(f"{len(plano) - 1} lotes em paralelo ({a.paralelo} por vez)…", flush=True)
        with ThreadPoolExecutor(max_workers=a.paralelo) as pool:
            relatorios += list(pool.map(lambda l: _motor(ws, l, a.modelo), plano[1:]))
    for l in plano:  # relatórios de lotes de execuções anteriores entram na conta
        rel = ws / "relatorios" / f"{l['nome']}.json"
        if rel.exists() and not any(r.get("lote") == l["nome"] for r in relatorios):
            relatorios.append(json.loads(rel.read_text(encoding="utf-8")))
    resumo = fechar(ws, sessao, relatorios, time.time() - t0)
    print(json.dumps({k: resumo[k] for k in ("build_final", "kb", "capturas", "texto_rastreavel_pct")} |
                     {"faltando": len(resumo["faltando"]), "com_erro": len(resumo["com_erro"]),
                      "lint": len(resumo["lint_estatico"]), "tokens": resumo["uso"]["total"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
