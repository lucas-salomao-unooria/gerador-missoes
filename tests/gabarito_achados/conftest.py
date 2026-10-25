"""O gabarito roda também chamado de fora do repositório (`pytest /caminho/tests/gabarito_achados`): sem a raiz no
`sys.path`, `tools` não importa, e sem o conftest da raiz a base da plataforma não é a congelada dos testes. Revisão do
PR #77 (24/10/2026): de /tmp a coleta dava «No module named 'tools'»."""
import runpy
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
# as mesmas variáveis do conftest da raiz (base da plataforma congelada, correção pontual desligada)
runpy.run_path(str(RAIZ / "conftest.py"))
