"""Rotas que a plataforma de fato tem — para conferir o que o PRD e o handoff dizem que ela tem.

Medido nas 14 primeiras sessões: das 33 rotas citadas em módulos que já existem na plataforma, duas
não existiam (`PUT /atividades/:id/revisar`, `DELETE /turmas/:id` — esta apagaria uma turma inteira
a partir de uma missão), uma tinha o verbo errado, e nove rotas de missão estavam penduradas no módulo
`experiencias` da plataforma, contra o padrão de módulo próprio (TEC-02). Nenhum gate conferia.

**Fonte, na ordem:**
1. `PLATAFORMA_OPENAPI_URL` — o documento servido pela api (`/docs-json`, com `SWAGGER_USUARIO` e
   `SWAGGER_SENHA` quando o `/docs` é protegido). É o ideal: sempre atualizado. Em 23/09/2026 a api
   de dev não expunha o documento publicamente, então o padrão é vazio.
2. `references/plataforma/openapi-rotas.json` — gerado do roteador de verdade
   (`apps/api/scripts/gerar-openapi.ts`) por `scripts/sincronizar_plataforma.py --openapi`.

Rota em módulo que a plataforma ainda não tem é proposta da missão, e não é conferida aqui.
"""
from __future__ import annotations

import base64
import json
import re
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from prompts import REFERENCES_DIR

ARQUIVO = REFERENCES_DIR / "plataforma" / "openapi-rotas.json"
_RE_ROTA = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+`?(/[A-Za-z0-9_\-/{}:«».]+)", re.IGNORECASE)
#: Marcação de que a rota ainda não existe e é pedida à plataforma — aí ela não é afirmação falsa.
_RE_PROPOSTA = re.compile(r"\[\s*nova|nova rota|rota nova|a criar|proposta|pend[êe]ncia de plataforma|verificar no reposit", re.IGNORECASE)
#: Linha que cita a rota para PROIBI-LA: "**NÃO** utilizar rotas inexistentes como `PUT /salas`",
#: "Eliminada qualquer menção incorreta a `GET /turmas/:id/painel`". O redator escreve isso quando o
#: pedido de correção aponta a rota errada, e o gate a lia como rota em uso (24/09/2026).
_RE_PROIBICAO = re.compile(
    r"\bn[ãa]o\s+(?:utiliz|us[ae]|cham|consum|cri[ae])|\bnunca\b|\binexistente|\beliminad|\bincorret|"
    r"\bproibid|\bvedad|\bveda-se|\bexpurg", re.IGNORECASE)
_RE_PARAM = re.compile(r"«[^»]+»|:\w+|\{[^}]+\}")
_cache: Dict[str, Any] = {}


def _normalizar(caminho: str) -> List[str]:
    return [("{p}" if _RE_PARAM.fullmatch(s) else s) for s in _RE_PARAM.sub("{p}", caminho.strip("`").rstrip("/.")).split("/") if s]


def _do_openapi(doc: Dict[str, Any]) -> List[Tuple[str, List[str]]]:
    return [(m.upper(), _normalizar(c)) for c, ops in (doc.get("paths") or {}).items()
            for m in ops if m.lower() in ("get", "post", "put", "patch", "delete")]


def carregar() -> Tuple[List[Tuple[str, List[str]]], str]:
    """`(rotas, origem)`. A URL vence; sem ela, ou se ela falhar, a lista sincronizada."""
    if "rotas" in _cache:
        return _cache["rotas"], _cache["origem"]
    from config import get_settings
    s = get_settings()
    rotas: List[Tuple[str, List[str]]] = []
    origem = ""
    if s.plataforma_openapi_url:
        try:
            req = urllib.request.Request(s.plataforma_openapi_url)
            if s.plataforma_openapi_usuario:
                cred = f"{s.plataforma_openapi_usuario}:{s.plataforma_openapi_senha}".encode()
                req.add_header("Authorization", "Basic " + base64.b64encode(cred).decode())
            with urllib.request.urlopen(req, timeout=8) as resp:
                rotas = _do_openapi(json.loads(resp.read().decode("utf-8")))
            origem = s.plataforma_openapi_url
        except Exception:  # sem rede ou sem permissão: a cópia sincronizada serve
            rotas = []
    if not rotas and ARQUIVO.exists():
        dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
        rotas = [(r["metodo"], _normalizar(r["caminho"])) for r in dados.get("rotas", [])]
        origem = f"cópia sincronizada ({dados.get('commit', '?')}, {dados.get('data_commit', '?')})"
    _cache.update(rotas=rotas, origem=origem)
    return rotas, origem


def _casa(citado: List[str], real: List[str]) -> bool:
    if len(citado) != len(real):
        return False
    # parâmetro do índice casa qualquer segmento — inclusive o slug da missão escrito por extenso
    return all(r == "{p}" or c == r for c, r in zip(citado, real))


def validar_rotas(texto: str) -> List[Dict[str, str]]:
    """Achados sobre rotas citadas em módulos que a plataforma JÁ tem."""
    rotas, origem = carregar()
    if not rotas:
        return []
    modulos = {r[0] for _, r in rotas if r}
    # O módulo que o próprio documento declara para a missão é proposta dela, não afirmação sobre a
    # plataforma — mesmo que um módulo de mesmo nome já exista lá (a exp05ef1b propôs `quem-mandou-isso`
    # antes de ele ser construído com outras rotas).
    proprios = set(re.findall(r"apps/api/src/([a-z0-9\-]+)/", texto or ""))
    achados: List[Dict[str, str]] = []
    vistos = set()
    for linha in (texto or "").splitlines():
        # antes do `vistos`: a mesma rota usada de verdade noutra linha continua sendo conferida
        if _RE_PROIBICAO.search(linha):
            continue
        for m in _RE_ROTA.finditer(linha):
            metodo, citado = m.group(1).upper(), _normalizar(m.group(2))
            if not citado or citado[0] not in modulos or citado[0] in proprios or (metodo, tuple(citado)) in vistos:
                continue
            vistos.add((metodo, tuple(citado)))
            rota = f"{metodo} /{'/'.join(citado)}"
            if citado[0] == "experiencias" and len(citado) > 1 and re.fullmatch(r"exp\d{2}(?:ef|em)\d+b", citado[1], re.I):
                achados.append({"severidade": "atencao", "codigo": "rota-fora-do-modulo", "etapa": "dev",
                                "resumo": f"`{rota}` pendura a missão no módulo `experiencias` da plataforma. Missão tem "
                                          f"módulo próprio (`apps/api/src/<slug-curto>/`, critério TEC-02)."})
                continue
            if any(mm == metodo and _casa(citado, r) for mm, r in rotas):
                continue
            if _RE_PROPOSTA.search(linha):
                continue
            outros = sorted({mm for mm, r in rotas if _casa(citado, r)})
            if outros:
                achados.append({"severidade": "bloqueio", "codigo": "rota-verbo-errado", "etapa": "dev",
                                "resumo": f"`{rota}` existe na plataforma com outro verbo: {', '.join(outros)}. Fonte: {origem}."})
            else:
                achados.append({"severidade": "bloqueio", "codigo": "rota-inexistente", "etapa": "dev",
                                "resumo": f"`{rota}` não existe na plataforma, e o módulo `{citado[0]}` é dela. Se é rota "
                                          f"nova pedida à plataforma, marque como pendência de plataforma; se não, use "
                                          f"a rota real do índice. Fonte: {origem}."})
    return achados
