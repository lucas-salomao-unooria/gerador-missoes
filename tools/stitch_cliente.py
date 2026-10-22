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


#: O Stitch responde a recusa como texto numa resposta de sucesso: «Resource has been exhausted (e.g. check quota).»
#: Na exp03em1b (22/10/2026) a cota acabou e a esteira registrou «sem resposta do Stitch» em todas as telas.
_RE_RECUSA = re.compile(r"resource has been exhausted|check quota|quota exceeded|rate limit|caller does not have "
                        r"permission|permission denied|unauthenticated|api key not valid", re.I)


def recusa(resposta: Any) -> str:
    """O texto da recusa do Stitch numa resposta de `chamar`, ou "" quando a resposta não é uma recusa."""
    texto = resposta.get("texto") if isinstance(resposta, dict) else None
    return texto.strip() if isinstance(texto, str) and _RE_RECUSA.search(texto) else ""


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


#: Teto de páginas do `list_screens`: o laço não pode girar para sempre se o token se repetir.
_MAX_PAGINAS = 20


def listar_telas(project_id: str, ids_de_reserva: Any = ()) -> List[Dict[str, Any]]:
    """Telas do projeto, sem o DESIGN.md, com o link de download do HTML.

    O caminho normal é `list_screens`, seguindo `nextPageToken` quando vem. Depois, cada identificador de
    `ids_de_reserva` que a listagem não trouxe é buscado com `get_screen`, um a um. O Stitch já devolveu `{}`
    para projeto com telas (17/09/2026) e, na exp06ef1b (09/10/2026), uma lista **parcial**: 37 telas num
    projeto de mais de 49, sem `E0-PROF-02` e `E4-PROF-01`, que não tinham mudado e estavam na folha da
    execução anterior — o Stitch saiu 🔴 com 19 de 22 telas que existiam. Ver `extrair_screen_ids`.
    """
    brutas: List[Dict[str, Any]] = []
    token = ""
    for _ in range(_MAX_PAGINAS):
        dados = chamar("list_screens", {"projectId": project_id, **({"pageToken": token} if token else {})})
        brutas += list(dados.get("screens") or [])
        novo = str(dados.get("nextPageToken") or "")
        if not novo or novo == token:
            break
        token = novo
    telas = [_tela(t) for t in brutas if not (t.get("title") or "").upper().startswith("DESIGN.MD")]
    vistos = {t["id"] for t in telas}
    faltando = [i for i in dict.fromkeys(str(i).lower() for i in (ids_de_reserva or ())) if i and i not in vistos]
    if not faltando:
        return telas

    logger.warning("list_screens não trouxe %d de %d tela(s) esperada(s) em %s; buscando por id",
                   len(faltando), len(vistos) + len(faltando), project_id)
    for i in faltando:
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
    # A visão do professor é entregável: quem abre a folha precisa achar o que ele customiza
    # e como, sem varrer a tabela inteira. Sem tela `PROF`, a ausência fica escrita — o rastro
    # de lacunas e o QA (D6) leem esta linha.
    professor = [t for t in dados["telas"] if "PROF" in (t.get("titulo") or "").upper()]
    linhas.append("")
    linhas.append("## Visão do professor")
    linhas.append("")
    if professor:
        linhas.append("| Tela | Dispositivo | Prévia |")
        linhas.append("|---|---|---|")
        for t in professor:
            previa = f"[abrir imagem]({t['url_imagem']})" if t.get("url_imagem") else "—"
            linhas.append(f"| {t['titulo']} | {t.get('dispositivo') or '—'} | {previa} |")
        if not any("E0-PROF" in (t.get("titulo") or "").upper() for t in professor):
            linhas.append("")
            linhas.append("[LACUNA — dono: telas] Há tela de condução do professor, mas nenhuma do preparo (`E0-PROF-01…05`: recorte da aula, geração, curadoria, ativação). O que o professor customiza e como não foi construído.")
    else:
        linhas.append("[LACUNA — dono: telas] Nenhuma tela de professor no projeto do Stitch — nem preparo (`E0-PROF-01…05`) nem condução. A visão do professor não foi construída.")
    return "\n".join(linhas) + "\n"
