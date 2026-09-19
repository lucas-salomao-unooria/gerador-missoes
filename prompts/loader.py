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
import time
from functools import lru_cache
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


@lru_cache(maxsize=512)
def _ler_arquivo(path: Path, _mtime: float) -> str:
    """Leitura memoizada. O `_mtime` entra na chave para o cache cair sozinho na edição."""
    return path.read_text(encoding="utf-8")


def get_prompt_raw(filename: str) -> str:
    """Conteúdo bruto do arquivo (sem resolver includes nem interpolar).

    Memoizado por (caminho, mtime): o editor de prompts e a construção dos ~40 agentes
    reliam o mesmo arquivo — e cada include dele, recursivamente — a cada chamada.
    """
    path = _resolve(filename)
    return _ler_arquivo(path, path.stat().st_mtime)


def limpar_cache_prompts() -> None:
    """Descarta as leituras e expansões memoizadas de prompts."""
    _ler_arquivo.cache_clear()
    _expandir_includes.cache_clear()


def save_prompt(filename: str, content: str) -> bool:
    """Salva o conteúdo atualizado no arquivo de prompt correspondente."""
    if not filename.endswith(".md"):
        filename = f"{filename}.md"
    path = (PROMPTS_DIR / filename).resolve()
    if PROMPTS_DIR not in path.parents:
        raise ValueError(f"Caminho de prompt fora da pasta prompts/: {filename}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    # O mtime já invalidaria a leitura deste arquivo, mas não a expansão dos prompts que o
    # incluem — por isso o cache inteiro cai aqui.
    limpar_cache_prompts()
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


@lru_cache(maxsize=256)
def _expandir_includes(filename: str, _assinatura: str) -> str:
    """Expansão memoizada dos includes de um prompt.

    A expansão de um prompt grande chega a 380 KB e era refeita a cada chamada — no editor
    de prompts, a cada rerun do Streamlit.
    """
    return resolve_includes(get_prompt_raw(filename))


_ASSINATURA_TTL = 2.0
_assinatura_cache: tuple[float, str] = (0.0, "")


def _assinatura_prompts() -> str:
    """Maior mtime da árvore de prompts — invalida as expansões memoizadas.

    Cobre tanto a edição pelo editor da UI quanto a edição direta do `.md` no disco, que é
    como os prompts são trabalhados no dia a dia. O TTL evita repetir o walk de ~109 stats
    nas ~40 chamadas seguidas que a construção dos agentes faz.
    """
    global _assinatura_cache
    agora = time.monotonic()
    if agora - _assinatura_cache[0] < _ASSINATURA_TTL:
        return _assinatura_cache[1]
    try:
        marca = str(max(p.stat().st_mtime_ns for p in PROMPTS_DIR.rglob("*.md")))
    except ValueError:
        marca = "0"
    _assinatura_cache = (agora, marca)
    return marca


def load_prompt(filename: str, **kwargs: Any) -> str:
    """Carrega um prompt: resolve includes e substitui variáveis estáticas de configuração.

    As variáveis dinâmicas de estado do ADK (`{one_pager}`, `{spec_missao?}`…) são
    preservadas para interpolação em tempo de execução.
    """
    content = _expandir_includes(filename, _assinatura_prompts())
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
