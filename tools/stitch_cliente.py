"""Cliente HTTP do Stitch usado FORA do modelo, para montar o protótipo compartilhável.

Por que existe, se já há o toolset MCP: o HTML de uma tela tem dezenas de KB, e vinte
telas não cabem no contexto de nenhum agente. O agente decide o que gerar e reporta os
identificadores; este cliente baixa os arquivos por conta própria e um passo
determinístico monta o protótipo. O modelo nunca vê o HTML.

Mesma autenticação do toolset: `X-Goog-Api-Key`.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from config import get_settings

logger = logging.getLogger("stitch_cliente")

_PROJECT_ID = re.compile(r"(?:projects?|projeto|projectid)\W{0,8}(\d{6,})", re.IGNORECASE)
_SCREEN_ID = re.compile(r"\b([0-9a-f]{32})\b", re.IGNORECASE)


def extrair_project_id(texto: Optional[str]) -> Optional[str]:
    """O `projectId` que o agente de wireframes reportou, em qualquer das formas usuais."""
    if not texto or not isinstance(texto, str):
        return None
    m = _PROJECT_ID.search(texto)
    return m.group(1) if m else None


def extrair_screen_ids(texto: Optional[str]) -> List[str]:
    """Os `screenId` que o agente de wireframes registrou, na ordem em que aparecem.

    Existe porque o `list_screens` do Stitch devolve `{}` mesmo para projeto com telas
    (verificado em 2026-09-17 no projeto 5513254360244222961: `list_screens` vazio,
    `get_screen` respondendo cada tela). Sem isso a folha de links sai vazia e o PRD
    perde a prévia de todas as telas.
    """
    if not texto or not isinstance(texto, str):
        return []
    vistos: List[str] = []
    for m in _SCREEN_ID.finditer(texto):
        i = m.group(1).lower()
        if i not in vistos:
            vistos.append(i)
    return vistos


def _headers() -> Dict[str, str]:
    s = get_settings()
    h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if s.stitch_api_key:
        h["X-Goog-Api-Key"] = s.stitch_api_key
    elif s.stitch_access_token:
        h["Authorization"] = f"Bearer {s.stitch_access_token}"
    return h


def chamar(ferramenta: str, argumentos: Dict[str, Any], timeout: int = 180) -> Dict[str, Any]:
    """Uma chamada `tools/call` ao endpoint MCP, devolvendo o JSON já desembrulhado."""
    s = get_settings()
    resp = httpx.post(
        s.stitch_mcp_remote_url,
        headers=_headers(),
        timeout=timeout,
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": ferramenta, "arguments": argumentos}},
    )
    resp.raise_for_status()
    corpo = resp.json()
    if "error" in corpo:
        raise RuntimeError(f"Stitch respondeu erro em {ferramenta}: {corpo['error']}")
    for parte in corpo.get("result", {}).get("content", []):
        if parte.get("type") == "text":
            try:
                return json.loads(parte["text"])
            except json.JSONDecodeError:
                return {"texto": parte["text"]}
    return corpo.get("result", {})


def _tela(t: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": (t.get("name") or "").rsplit("/", 1)[-1],
        "titulo": (t.get("title") or "").strip() or "(sem título)",
        "largura": int(t.get("width") or 0) or None,
        "altura": int(t.get("height") or 0) or None,
        "dispositivo": t.get("deviceType"),
        "url_html": (t.get("htmlCode") or {}).get("downloadUrl"),
        "url_imagem": (t.get("screenshot") or {}).get("downloadUrl"),
    }


def listar_telas(project_id: str, ids_de_reserva: Any = ()) -> List[Dict[str, Any]]:
    """Telas do projeto, sem o DESIGN.md, com o link de download do HTML.

    O caminho normal é `list_screens`. Quando ele devolve vazio — o que o Stitch faz
    hoje mesmo para projeto com telas —, cai para `get_screen` um a um, com os
    identificadores que o agente reportou. Ver `extrair_screen_ids`.
    """
    dados = chamar("list_screens", {"projectId": project_id})
    telas = [_tela(t) for t in (dados.get("screens") or []) if not (t.get("title") or "").upper().startswith("DESIGN.MD")]
    if telas or not ids_de_reserva:
        return telas

    logger.warning("list_screens devolveu vazio para %s; buscando %d tela(s) por id", project_id, len(list(ids_de_reserva)))
    for i in ids_de_reserva:
        try:
            t = chamar("get_screen", {"name": f"projects/{project_id}/screens/{i}"})
        except Exception as exc:  # uma tela inexistente não invalida as demais
            logger.warning("get_screen falhou para %s: %s", i, exc)
            continue
        if t.get("name") and not (t.get("title") or "").upper().startswith("DESIGN.MD"):
            telas.append(_tela(t))
    return telas


def coletar_links(project_id: str, limite: int = 60, ids_de_reserva: Any = ()) -> Dict[str, Any]:
    """Projeto e telas com os endereços que uma pessoa abre — sem baixar arquivo nenhum.

    O link do projeto é o que vai ao PRD. A imagem de cada tela tem endereço próprio e
    público, e serve de miniatura para quem só quer olhar sem entrar no Stitch.
    """
    s = get_settings()
    telas = listar_telas(project_id, ids_de_reserva)[:limite]
    return {
        "project_id": project_id,
        "url_projeto": f"{s.stitch_project_url_base.rstrip('/')}/{project_id}",
        "telas": telas,
    }


def montar_folha_de_links(dados: Dict[str, Any], titulo: str = "") -> str:
    """A seção em Markdown que entra no relatório, no artefato e no PRD."""
    linhas = [f"# Telas no Stitch — {titulo or 'missão'}", ""]
    linhas.append(f"**Projeto:** [{dados['url_projeto']}]({dados['url_projeto']}) · `{dados['project_id']}`")
    linhas.append("")
    linhas.append(
        "O projeto nasce **privado**: quem abrir o link precisa de acesso concedido na própria "
        "interface do Stitch, em Share. A imagem de cada tela, ao contrário, tem endereço público "
        "e abre para qualquer pessoa — é ela que serve de prévia enquanto o acesso não é concedido."
    )
    linhas.append("")
    if not dados["telas"]:
        linhas.append("_Nenhuma tela encontrada no projeto._")
        return "\n".join(linhas) + "\n"
    linhas.append("| Tela | Dispositivo | Medidas | Prévia |")
    linhas.append("|---|---|---|---|")
    for t in dados["telas"]:
        medidas = f"{t['largura']}×{t['altura']}" if t.get("largura") and t.get("altura") else "—"
        previa = f"[abrir imagem]({t['url_imagem']})" if t.get("url_imagem") else "—"
        linhas.append(f"| {t['titulo']} | {t.get('dispositivo') or '—'} | {medidas} | {previa} |")
    linhas.append("")
    linhas.append(f"{len(dados['telas'])} tela(s).")
    return "\n".join(linhas) + "\n"
