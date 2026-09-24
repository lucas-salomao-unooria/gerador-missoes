"""Sincroniza o inventário de componentes do design system (`storybook-unooria`) para a esteira.

Os agentes de telas e de ambiente escreviam nomes de componente sem ter como conferir — o prompt dizia
isso a eles — e 32% dos componentes que as telas das 14 primeiras sessões chamavam "do DS" não
existiam na seção (66 de 206). Este script lê a API pública de cada marca (`src/<marca>/index.ts` →
`components/index.ts` → cada componente) e grava:

- ``prompts/references/ds-componentes.json`` — o que o lint confere (`tools/componentes_ds.py`);
- ``prompts/references/ds-componentes.md`` — o que os prompts de telas e ambiente incluem.

    python scripts/sincronizar_design_system.py            # usa ../storybook-unooria
    STORYBOOK_UNOORIA_DIR=/caminho python scripts/sincronizar_design_system.py

O ideal é ler de uma URL publicada (``DS_COMPONENTES_URL``, mesmo formato do JSON); em 23/09/2026 o
storybook de dev servia só a página padrão do Cloud Run, então esta cópia é a fonte.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORYBOOK = Path(os.getenv("STORYBOOK_UNOORIA_DIR", ROOT.parent / "storybook-unooria"))
DESTINO = ROOT / "prompts" / "references"
MARCAS = ("unooria", "instanooria", "chatgpt", "whatsappmobile", "tiktooria", "unootube")
#: Nome da seção na esteira (`secao_ds` do manifesto) → pasta da marca no DS.
SECAO_PARA_MARCA = {"unitube": "unootube"}

_RE_REEXPORTA = re.compile(r"export\s+\*\s+from\s+['\"](\.[^'\"]+)['\"]")
_RE_NOMEADO = re.compile(r"export\s+\{([^}]+)\}\s+from")
_RE_DECLARA = re.compile(r"export\s+(?:const|function|class|default\s+function)\s+([A-Z][A-Za-z0-9]+)")


def _arquivo(base: Path) -> "Path | None":
    for candidato in (base.with_suffix(".ts"), base.with_suffix(".tsx"), base / "index.ts", base / "index.tsx"):
        if candidato.exists():
            return candidato
    return None


def _exportados(arquivo: Path, vistos: set) -> set:
    if arquivo in vistos:
        return set()
    vistos.add(arquivo)
    texto = arquivo.read_text(encoding="utf-8", errors="ignore")
    nomes = set(_RE_DECLARA.findall(texto))
    for grupo in _RE_NOMEADO.findall(texto):
        for item in grupo.split(","):
            nome = item.split(" as ")[-1].strip()
            if re.fullmatch(r"[A-Z][A-Za-z0-9]+", nome) and not item.strip().startswith("type "):
                nomes.add(nome)
    for rel in _RE_REEXPORTA.findall(texto):
        alvo = _arquivo((arquivo.parent / rel).resolve())
        if alvo:
            nomes |= _exportados(alvo, vistos)
    return nomes


def main(argv: "list[str] | None" = None) -> int:
    argparse.ArgumentParser(prog="sincronizar_design_system.py", description=__doc__,
                            formatter_class=argparse.RawDescriptionHelpFormatter).parse_args(argv)
    if not (STORYBOOK / "src").exists():
        print(f"storybook-unooria não encontrado em {STORYBOOK} (defina STORYBOOK_UNOORIA_DIR)", file=sys.stderr)
        return 1
    git = lambda *a: subprocess.run(["git", "-C", str(STORYBOOK), *a], capture_output=True, text=True).stdout.strip()
    pacote = json.loads((STORYBOOK / "package.json").read_text(encoding="utf-8"))
    marcas = {}
    for marca in MARCAS:
        entrada = _arquivo(STORYBOOK / "src" / marca)
        if entrada:
            marcas[marca] = sorted(n for n in _exportados(entrada, set()) if not n.endswith(("Props", "Context")))
    dados = {"commit": git("rev-parse", "--short", "HEAD"), "data_commit": git("log", "-1", "--format=%cs"),
             "pacote": pacote.get("name"), "versao": pacote.get("version"),
             "sincronizado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "secao_para_marca": SECAO_PARA_MARCA, "marcas": marcas}
    (DESTINO / "ds-componentes.json").write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    linhas = [f"<!-- GERADO de storybook-unooria@{dados['commit']} ({dados['data_commit']}, {dados['pacote']} "
              f"{dados['versao']}) por scripts/sincronizar_design_system.py · não edite -->", "",
              "## Componentes que existem no design system, por seção", "",
              "Só estes nomes vão na coluna **Componentes do DS**. O que não está aqui é **componente local** "
              "(coluna própria, registrado como candidato), nunca \"do DS\". A seção `unitube` da esteira é a "
              "marca `unootube` no pacote. Todo componente da marca `unooria` vale em qualquer seção.", ""]
    for marca, nomes in marcas.items():
        linhas.append(f"**`{marca}`** ({len(nomes)}): " + " · ".join(f"`{n}`" for n in nomes))
        linhas.append("")
    (DESTINO / "ds-componentes.md").write_text("\n".join(linhas), encoding="utf-8")
    print(f"ok → {sum(len(v) for v in marcas.values())} componentes em {len(marcas)} marcas, "
          f"storybook-unooria@{dados['commit']} ({dados['versao']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
