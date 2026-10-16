"""Componentes que as telas dizem ser do design system existem nele?

32% dos componentes que as telas das 14 primeiras sessões chamavam "do DS" não existiam na seção (66
de 206) — `LikeButton`, `FeedContainer`, `StoryComposer` numa missão InstaNooria, `MessageBubble` (do
WhatsApp) numa de ChatGPT. O prompt de telas dizia ao agente "você não tem como conferir o catálogo".
Agora ele recebe o inventário, e este módulo confere a coluna `Componentes do DS` contra ele.

**Fonte:** o `ds-componentes.json` da base fixada na execução (`prompts/base_plataforma.py`), que o CI
do storybook publica a cada versão. Até 06/10/2026 era uma cópia no git com as marcas fixas no código, e
`unooriaai`, `unoovista` e `unoochat` nunca entraram. Componente local vai na coluna própria e não é
conferido.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple

from prompts import base_plataforma

_RE_NOME = re.compile(r"\b([A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+)(?:\.[A-Z][A-Za-z]+)?\b")
_RE_SECAO = re.compile(r"secao_ds[`*_]*\s*:\s*[`*_]*\s*([a-z0-9:_\-]+)", re.IGNORECASE)
#: Não são componente: esquema Zod, tipo, contexto, token.
_NAO_COMPONENTE = re.compile(r"(Schema|Props|Context|Token|Type|Enum)$")
#: Famílias que a referência do DS nomeia como grupo (`plataforma-unooria-design-system.md` §3).
_FAMILIAS = {"DataViz"}
_cache: Dict[str, Any] = {}


def carregar() -> Tuple[Dict[str, Set[str]], Dict[str, str], str]:
    """`(marca → nomes, seção → marca, origem)`, da base fixada na execução."""
    base = base_plataforma.ativa()
    if _cache.get("assinatura") == base.assinatura:
        return _cache["marcas"], _cache["mapa"], _cache["origem"]
    dados = base_plataforma.ds_componentes(base)
    origem = f"storybook-unooria@{dados.get('commit', '?')} ({dados.get('versao', '?')})"
    marcas = {m: set(v) for m, v in (dados.get("marcas") or {}).items()}
    mapa = dict(dados.get("secao_para_marca") or {})
    _cache.update(assinatura=base.assinatura, marcas=marcas, mapa=mapa, origem=origem)
    return marcas, mapa, origem


def _norm(celula: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", celula.lower()) if unicodedata.category(c) != "Mn").strip(" `*_")


def _validos(secao: str, marcas: Dict[str, Set[str]], mapa: Dict[str, str]) -> Optional[Set[str]]:
    """Os nomes da marca de uma seção, mais a `unooria`; `None` quando a seção não é marca do DS (seção nova)."""
    marca = mapa.get(secao, secao)
    return (marcas[marca] | marcas.get("unooria", set())) if marca in marcas else None


def validar(wireframes: str, spec: str = "") -> List[Dict[str, str]]:
    """A coluna `Componentes do DS` contra o inventário da seção.

    Com várias seções do DS (15/10/2026), cada tela é conferida contra a seção dela — a coluna `Seção do DS` da
    tabela de cobertura — e, sem a coluna, contra a união da principal com as extras: `MessageBubble` existe no
    `unoochat` e no `unoovista`, e só a seção da tela diz se o nome está no lugar certo.
    """
    from tools import secoes as sec

    marcas, mapa, origem = carregar()
    if not marcas:
        return []
    m = _RE_SECAO.search(spec or "")
    principal = (m.group(1).lower().strip("`") if m else "")
    da_missao = [principal, *sec.extras(spec or "")]
    conjuntos = [v for v in (_validos(s, marcas, mapa) for s in da_missao if s) if v is not None]
    if conjuntos and len(conjuntos) == len([s for s in da_missao if s]):
        validos_missao, onde_missao = set().union(*conjuntos), " ou ".join(f"`{s}`" for s in da_missao if s)
        severidade = "bloqueio"
    else:  # seção nova: componente local é legítimo, só está na coluna errada — erro de rótulo
        validos_missao, onde_missao = set().union(*marcas.values()), "nenhuma marca do DS"
        severidade = "atencao"
    achados: List[Dict[str, str]] = []
    vistos: Set[Tuple[str, str]] = set()
    coluna: Optional[int] = None
    coluna_secao: Optional[int] = None
    for linha in (wireframes or "").splitlines():
        l = linha.strip()
        if not (l.startswith("|") and l.endswith("|")):
            coluna = coluna_secao = None
            continue
        celulas = [c.strip() for c in l.strip("|").split("|")]
        if set("".join(celulas)) <= set("-: "):
            continue
        normal = [_norm(c) for c in celulas]
        alvo = next((k for k, c in enumerate(normal) if "componentes do ds" in c), None)
        if alvo is not None:
            coluna = alvo
            coluna_secao = next((k for k, c in enumerate(normal) if c.startswith("secao do ds")), None)
            continue
        if coluna is None or coluna >= len(celulas):
            continue
        validos, onde = validos_missao, f"{onde_missao} (ou `unooria`)" if severidade == "bloqueio" else onde_missao
        if coluna_secao is not None and coluna_secao < len(celulas):
            da_tela = _norm(celulas[coluna_secao]).strip("` ")
            proprios = _validos(da_tela, marcas, mapa) if da_tela else None
            if proprios is not None:
                validos, onde = proprios, f"`{da_tela}`, a seção desta tela (ou `unooria`)"
        validos = validos | _FAMILIAS
        for nome in _RE_NOME.findall(celulas[coluna]):
            if (nome, onde) in vistos or nome in validos or _NAO_COMPONENTE.search(nome):
                continue
            vistos.add((nome, onde))
            parecidos = difflib.get_close_matches(nome, sorted(validos), n=2, cutoff=0.6)
            dica = f" Parecido: {', '.join(f'`{p}`' for p in parecidos)}." if parecidos else ""
            achados.append({"severidade": severidade, "codigo": "componente-inexistente", "etapa": "design",
                            "resumo": f"`{nome}` está como componente do DS e não existe em {onde} ({origem}).{dica} "
                                      f"Use um componente do inventário, ou mova-o para Componentes locais (candidatos)."})
    return achados
