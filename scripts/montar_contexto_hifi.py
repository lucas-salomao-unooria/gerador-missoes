"""Monta o contexto de build da imagem do Job do protótipo hi-fi (`Dockerfile.prototipo-hifi`).

    .venv/bin/python scripts/montar_contexto_hifi.py \
        --ds /Volumes/Documentos/Unooria/storybook-unooria \
        --plataforma /Volumes/Documentos/Unooria/plataforma-unooria

Grava em `build/hifi-contexto/` o contexto completo da imagem (o Dockerfile, o `cloudbuild.yaml`, o código do
kit e o requirements da venv do SDK) e um RETRATO do que o agente lê:
- `ds/`: o pacote do Design System (`package.json`, `dist/`, `src/`, `stories/`); sem `node_modules`, que a
  imagem instala para Linux;
- `plataforma/`: a ponte `@edu/ui`, as regras de DS, as telas do hub do professor e o código das experiências
  `exp*`, com as mesmas listas de `tools/prototipo_hifi`.

O repositório da plataforma é privado e o Job não o clona: o retrato entra na imagem. Reconstruir a imagem
atualiza o retrato. O passo seguinte é o CI da plataforma gravar isto no bucket da base, como já faz com a base.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from tools.prototipo_hifi import REFERENCIAS_HUB, REFERENCIAS_REGRAS  # noqa: E402

IGNORAR = shutil.ignore_patterns("node_modules", ".turbo", "dist", "*.map", "*.test.*", ".DS_Store")


def _copiar(origem: Path, destino: Path, ignorar=IGNORAR) -> None:
    if origem.is_dir():
        shutil.copytree(origem, destino, dirs_exist_ok=True, ignore=ignorar)
    elif origem.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origem, destino)


def montar(ds: Path, plataforma: Path, destino: Path) -> None:
    shutil.rmtree(destino, ignore_errors=True)
    # o DS: o `dist/` é o que o build usa; `src/` (os .types.ts) e `stories/` (as telas de exemplo), o que o agente lê
    _copiar(ds / "package.json", destino / "ds" / "package.json")
    _copiar(ds / "dist", destino / "ds" / "dist", shutil.ignore_patterns("*.map", ".DS_Store"))
    for parte in ("src", "stories"):
        _copiar(ds / parte, destino / "ds" / parte)
    p = destino / "plataforma"
    for parte in ("package.json", "src", "styles", "AGENTS.md"):
        _copiar(plataforma / "packages" / "ui" / parte, p / "packages" / "ui" / parte)
    for rel in REFERENCIAS_REGRAS:
        _copiar(plataforma / rel, p / rel)
    for rel in REFERENCIAS_HUB:
        _copiar(plataforma / "apps" / "hub" / rel, p / "apps" / "hub" / rel)
    for exp in sorted((plataforma / "apps" / "experiencias").iterdir()):
        if exp.is_dir() and exp.name.startswith("exp") and (exp / "src").exists():
            _copiar(exp / "src", p / "apps" / "experiencias" / exp.name / "src")
            _copiar(exp / "AGENTS.md", p / "apps" / "experiencias" / exp.name / "AGENTS.md")


CLOUDBUILD = """# Gerado por scripts/montar_contexto_hifi.py. Constrói a imagem do Job do protótipo hi-fi em amd64 e publica.
steps:
  - name: gcr.io/cloud-builders/docker
    args: ["build", "-f", "Dockerfile.prototipo-hifi", "-t", "{imagem}:{tag}", "-t", "{imagem}:latest", "."]
images: ["{imagem}:{tag}", "{imagem}:latest"]
timeout: 2400s
options:
  machineType: E2_HIGHCPU_8
"""
IMAGEM = "us-east1-docker.pkg.dev/entre-redes-dev/plataforma-unooria-dev/gerador-missoes-hifi"


def codigo_do_kit(destino: Path, tag: str) -> None:
    """O Dockerfile, o código do kit e o requirements entram no contexto: o Cloud Build só vê esta pasta."""
    shutil.copy2(RAIZ / "Dockerfile.prototipo-hifi", destino / "Dockerfile.prototipo-hifi")
    shutil.copy2(RAIZ / "requirements-antigravity.txt", destino / "requirements-antigravity.txt")
    for parte in ("tools", "scripts"):
        _copiar(RAIZ / parte, destino / parte, shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"))
    (destino / "cloudbuild.yaml").write_text(CLOUDBUILD.format(imagem=IMAGEM, tag=tag), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ds", required=True, help="raiz do repositório storybook-unooria")
    ap.add_argument("--plataforma", required=True, help="raiz do monorepo plataforma-unooria")
    ap.add_argument("--destino", default=str(RAIZ / "build" / "hifi-contexto"))
    ap.add_argument("--tag", default=None, help="tag da imagem (padrão: o commit atual do gerador)")
    a = ap.parse_args()
    import subprocess
    tag = a.tag or subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=RAIZ, capture_output=True,
                                  text=True).stdout.strip() or "manual"
    montar(Path(a.ds), Path(a.plataforma), Path(a.destino))
    codigo_do_kit(Path(a.destino), tag)
    print(f"contexto em {a.destino}")


if __name__ == "__main__":
    main()
