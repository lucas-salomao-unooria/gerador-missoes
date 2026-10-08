#!/usr/bin/env bash
# Recompila o manual e regenera as prévias que o README principal embute.
# As prévias envelhecem junto com o PDF — rode isto depois de mexer no .tex.
set -euo pipefail
cd "$(dirname "$0")"

tectonic -X compile manual-gerador-missoes.tex

python3 - <<'PY'
import subprocess, pathlib
from PIL import Image

# página do PDF -> nome do arquivo de prévia
PAGINAS = {
    1:  "capa",
    8:  "o-que-a-esteira-faz",
    18: "parecer-humano",
    30: "mapa-dos-agentes",
    47: "anatomia-do-aha",
    60: "catalogo-de-agentes",
}

dest = pathlib.Path("previews")
dest.mkdir(exist_ok=True)
for pagina, nome in PAGINAS.items():
    subprocess.run(["pdftoppm", "-f", str(pagina), "-l", str(pagina), "-r", "110", "-png",
                    "manual-gerador-missoes.pdf", f"/tmp/pv_{nome}"], check=True)
    src = next(pathlib.Path("/tmp").glob(f"pv_{nome}*.png"))
    im = Image.open(src).convert("RGB")
    im.thumbnail((1000, 1420), Image.LANCZOS)
    im.save(dest / f"{nome}.png", optimize=True)
    src.unlink()
    print(f"previews/{nome}.png  (página {pagina})")
PY

echo
echo "Confira se as páginas ainda correspondem: a paginação muda quando o texto muda."
