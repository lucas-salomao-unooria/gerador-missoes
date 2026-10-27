"""Gera `prompts/references/pronto-prototipo.md` a partir de `pronto.md`.

Por que existe: o protótipo incluía `pronto.md` inteiro — as contas de jornada, fluxo, copy, CAA,
telas, completude e fecha-lacunas — e não tinha a seção dele. Contava o que não era seu e nada do
que é (pacote do designer de 26/10/2026). A seção `prototipo` mora em `pronto.md`, ao lado das
outras, para a regra de manutenção valer para todas; o protótipo recebe só o preâmbulo e ela,
gerados daqui, no mesmo padrão de `gerar_resumo_literatura.py`, para não divergir.

Uso:
  python scripts/gerar_pronto_prototipo.py           # regenera
  python scripts/gerar_pronto_prototipo.py --check   # falha (exit 1) se a fonte mudou e o gerado não
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTE = RAIZ / "prompts" / "references" / "pronto.md"
DESTINO = RAIZ / "prompts" / "references" / "pronto-prototipo.md"
SECAO = "prototipo"


def _sha(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _partes(fonte: str) -> tuple[str, str]:
    """(preâmbulo sem frontmatter nem título, seção `## prototipo` inteira com o título)."""
    corpo = re.sub(r"\A---\n.*?\n---\n", "", fonte, flags=re.S)
    primeira = re.search(r"^## ", corpo, re.M)
    if not primeira:
        raise SystemExit(f"Nenhuma seção '## ' em {FONTE.name}")
    preambulo = re.sub(r"^\s*# .*\n", "", corpo[: primeira.start()]).strip()
    m = re.search(rf"^## {SECAO}\s*$", corpo, re.M)
    if not m:
        raise SystemExit(f"Seção '## {SECAO}' não encontrada em {FONTE.name}")
    fim = re.search(r"^## ", corpo[m.end():], re.M)
    secao = corpo[m.start(): m.end() + fim.start()] if fim else corpo[m.start():]
    return preambulo, secao.strip()


def _assinatura(fonte: str) -> str:
    preambulo, secao = _partes(fonte)
    return _sha(f"{preambulo}\n\n{secao}")


def gerar() -> str:
    fonte = FONTE.read_text(encoding="utf-8")
    preambulo, secao = _partes(fonte)
    partes = [
        "---",
        "name: pronto-prototipo",
        "description: Definição de pronto do protótipo (D8) — o preâmbulo e a seção `prototipo` de pronto.md, só o que o agente de protótipo conta. Gerado; não edite à mão.",
        "sources: [pronto.md]",
        "---",
        "",
        "# Definição de pronto — protótipo",
        "",
        f"> **Gerado automaticamente** de `pronto.md` por `scripts/gerar_pronto_prototipo.py`. Não edite à mão: edite a seção `{SECAO}` de `pronto.md` e regenere. "
        f"SHA-256 da fonte (preâmbulo e seção): `{_assinatura(fonte)}`.",
        "",
        preambulo,
        "",
        secao,
        "",
    ]
    return "\n".join(partes)


def main(argv: list[str]) -> int:
    if "--check" in argv:
        if not DESTINO.exists():
            print(f"❌ {DESTINO.name} não existe — rode sem --check para gerar."); return 1
        atual = _assinatura(FONTE.read_text(encoding="utf-8"))
        m = re.search(r"SHA-256 da fonte \(preâmbulo e seção\): `([0-9a-f]{64})`", DESTINO.read_text(encoding="utf-8"))
        if not m or m.group(1) != atual:
            print(f"❌ {DESTINO.name} está defasado em relação a {FONTE.name} — regenere."); return 1
        print(f"✅ {DESTINO.name} confere com a fonte ({atual[:12]}…)."); return 0
    DESTINO.write_text(gerar(), encoding="utf-8")
    print(f"✅ gerado {DESTINO.relative_to(RAIZ)} ({DESTINO.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
