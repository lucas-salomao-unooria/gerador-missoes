"""Componentes que as telas dizem ser do design system existem nele?

32% dos componentes que as telas das 14 primeiras sessões chamavam "do DS" não existiam na seção (66
de 206) — `LikeButton`, `FeedContainer`, `StoryComposer` numa missão InstaNooria, `MessageBubble` (do
WhatsApp) numa de ChatGPT. O prompt de telas dizia ao agente "você não tem como conferir o catálogo".
Agora ele recebe o inventário, e este módulo confere a coluna `Componentes do DS` contra ele.

**Fonte, na ordem:** `DS_COMPONENTES_URL` (JSON no formato de `ds-componentes.json`, quando o
inventário for publicado) e, sem ela, `references/ds-componentes.json`, gerado do `storybook-unooria`
por `scripts/sincronizar_design_system.py`. Componente local vai na coluna própria e não é conferido.
"""
from __future__ import annotations

import difflib
import json
import re
import unicodedata
import urllib.request
from typing import Any, Dict, List, Optional, Set, Tuple

from prompts import REFERENCES_DIR

ARQUIVO = REFERENCES_DIR / "ds-componentes.json"
_RE_NOME = re.compile(r"\b([A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+)(?:\.[A-Z][A-Za-z]+)?\b")
_RE_SECAO = re.compile(r"secao_ds[`*_]*\s*:\s*[`*_]*\s*([a-z0-9:_\-]+)", re.IGNORECASE)
#: Não são componente: esquema Zod, tipo, contexto, token.
_NAO_COMPONENTE = re.compile(r"(Schema|Props|Context|Token|Type|Enum)$")
#: Famílias que a referência do DS nomeia como grupo (`plataforma-unooria-design-system.md` §3).
_FAMILIAS = {"DataViz"}
_cache: Dict[str, Any] = {}


def carregar() -> Tuple[Dict[str, Set[str]], Dict[str, str], str]:
    """`(marca → nomes, seção → marca, origem)`."""
    if "marcas" in _cache:
        return _cache["marcas"], _cache["mapa"], _cache["origem"]
    from config import get_settings
    dados: Optional[Dict[str, Any]] = None
    origem = ""
    url = get_settings().ds_componentes_url
    if url:
        try:
            with urllib.request.urlopen(url, timeout=8) as resp:
                dados = json.loads(resp.read().decode("utf-8"))
            origem = url
        except Exception:
            dados = None
    if dados is None and ARQUIVO.exists():
        dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
        origem = f"storybook-unooria@{dados.get('commit', '?')} ({dados.get('versao', '?')})"
    marcas = {m: set(v) for m, v in ((dados or {}).get("marcas") or {}).items()}
    mapa = dict((dados or {}).get("secao_para_marca") or {})
    _cache.update(marcas=marcas, mapa=mapa, origem=origem)
    return marcas, mapa, origem


def _norm(celula: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", celula.lower()) if unicodedata.category(c) != "Mn").strip(" `*_")


def validar(wireframes: str, spec: str = "") -> List[Dict[str, str]]:
    marcas, mapa, origem = carregar()
    if not marcas:
        return []
    m = _RE_SECAO.search(spec or "")
    secao = (m.group(1).lower().strip("`") if m else "")
    marca = mapa.get(secao, secao)
    if marca in marcas:
        validos, onde = marcas[marca] | marcas.get("unooria", set()), f"marca `{marca}` (ou `unooria`)"
        severidade = "bloqueio"
    else:  # seção nova: componente local é legítimo, só está na coluna errada — erro de rótulo
        validos, onde = set().union(*marcas.values()), "nenhuma marca do DS"
        severidade = "atencao"
    validos = validos | _FAMILIAS
    achados: List[Dict[str, str]] = []
    vistos: Set[str] = set()
    coluna: Optional[int] = None
    for linha in (wireframes or "").splitlines():
        l = linha.strip()
        if not (l.startswith("|") and l.endswith("|")):
            coluna = None
            continue
        celulas = [c.strip() for c in l.strip("|").split("|")]
        if set("".join(celulas)) <= set("-: "):
            continue
        normal = [_norm(c) for c in celulas]
        alvo = next((k for k, c in enumerate(normal) if "componentes do ds" in c), None)
        if alvo is not None:
            coluna = alvo
            continue
        if coluna is None or coluna >= len(celulas):
            continue
        for nome in _RE_NOME.findall(celulas[coluna]):
            if nome in vistos or nome in validos or _NAO_COMPONENTE.search(nome):
                continue
            vistos.add(nome)
            parecidos = difflib.get_close_matches(nome, sorted(validos), n=2, cutoff=0.6)
            dica = f" Parecido: {', '.join(f'`{p}`' for p in parecidos)}." if parecidos else ""
            achados.append({"severidade": severidade, "codigo": "componente-inexistente", "etapa": "design",
                            "resumo": f"`{nome}` está como componente do DS e não existe em {onde} ({origem}).{dica} "
                                      f"Use um componente do inventário, ou mova-o para Componentes locais (candidatos)."})
    return achados
