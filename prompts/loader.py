"""Carregamento, edição e persistência dos prompts (.md) dos agentes.

Estrutura da pasta:
    prompts/
      produto/      prompts da área de Produto
      design/       prompts da área de Design
      dev/          prompts da área de Dev
      transversal/  prompts transversais (aprendizado)
      references/   conhecimento compartilhado, incluído nos prompts via diretiva

Diretiva de inclusão (resolvida em tempo de carga, antes da interpolação do ADK):
    <!-- include: references/criterios-gate-estrutural.md -->

Variáveis:
    {chave}   -> interpolada pelo Google ADK a partir do session.state em tempo de execução.
    {chave?}  -> idem, opcional (vazio se ausente).
    Variáveis estáticas de configuração são substituídas aqui por `load_prompt(**kwargs)`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

PROMPTS_DIR = Path(__file__).resolve().parent
REFERENCES_DIR = PROMPTS_DIR / "references"

_INCLUDE_RE = re.compile(r"<!--\s*include:\s*([\w./-]+)\s*-->")
_STATE_VAR_RE = re.compile(r"(?<!\{)\{([A-Za-z_][A-Za-z0-9_]*)\??\}(?!\})")


def _resolve(filename: str) -> Path:
    """Resolve um nome relativo à pasta prompts/, aceitando com ou sem `.md`."""
    if not filename.endswith(".md"):
        filename = f"{filename}.md"
    path = (PROMPTS_DIR / filename).resolve()
    if PROMPTS_DIR not in path.parents:
        raise ValueError(f"Caminho de prompt fora da pasta prompts/: {filename}")
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de prompt não encontrado: {path}")
    return path


def get_prompt_raw(filename: str) -> str:
    """Conteúdo bruto do arquivo (sem resolver includes nem interpolar)."""
    return _resolve(filename).read_text(encoding="utf-8")


def save_prompt(filename: str, content: str) -> bool:
    """Salva o conteúdo atualizado no arquivo de prompt correspondente."""
    if not filename.endswith(".md"):
        filename = f"{filename}.md"
    path = (PROMPTS_DIR / filename).resolve()
    if PROMPTS_DIR not in path.parents:
        raise ValueError(f"Caminho de prompt fora da pasta prompts/: {filename}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    return True


def resolve_includes(content: str, _depth: int = 0) -> str:
    """Substitui diretivas `<!-- include: caminho -->` pelo conteúdo do arquivo referenciado."""
    if _depth > 5:
        raise RecursionError("Profundidade máxima de includes excedida (ciclo?)")

    def _repl(match: re.Match[str]) -> str:
        rel = match.group(1)
        included = get_prompt_raw(rel)
        included = resolve_includes(included, _depth + 1)
        return f"\n<!-- início de {rel} -->\n{included.strip()}\n<!-- fim de {rel} -->\n"

    return _INCLUDE_RE.sub(_repl, content)


def load_prompt(filename: str, **kwargs: Any) -> str:
    """Carrega um prompt: resolve includes e substitui variáveis estáticas de configuração.

    As variáveis dinâmicas de estado do ADK (`{one_pager}`, `{spec_missao?}`…) são
    preservadas para interpolação em tempo de execução.
    """
    content = resolve_includes(get_prompt_raw(filename))
    for key, val in kwargs.items():
        content = content.replace(f"{{{key}}}", str(val))
    return content.strip()


def list_state_variables(content: str) -> List[str]:
    """Lista as variáveis `{nome}` / `{nome?}` presentes num prompt (após includes)."""
    return sorted(set(_STATE_VAR_RE.findall(content)))


def list_prompt_files() -> Dict[str, List[str]]:
    """Mapeia área -> arquivos de prompt disponíveis (exclui references/)."""
    areas: Dict[str, List[str]] = {}
    for area_dir in sorted(PROMPTS_DIR.iterdir()):
        if not area_dir.is_dir() or area_dir.name in {"references", "__pycache__"}:
            continue
        # `_arquivo.md` é fragmento incluído por outro prompt, não agente: fora do dropdown.
        files = sorted(p.name for p in area_dir.glob("*.md") if not p.name.startswith("_"))
        if files:
            areas[area_dir.name] = files
    return areas
