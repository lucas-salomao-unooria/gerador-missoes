"""Publica no Miro, FORA do modelo, o espelho dos diagramas de jornada e fluxo.

Por que não é um agente com toolset: o Mermaid já existe — foi a jornada (D2) e o fluxo
(D3) que o escreveram, e ele é a fonte da verdade. Deixar um LLM reconstruir o board
item a item gastaria dezenas de chamadas de ferramenta dentro do orçamento do turno, que
é justamente o que derrubou o D2 quando os diagramas viviam no FigJam. Aqui o código
pega o bloco pronto e manda; o modelo não vê o board.

O espelho cabe num widget nativo: `canvas_create_from_svg` aceita Mermaid dentro de um
`<foreignObject data-type="diagram">`, então não há parser nem layout a manter. O board
fixa o widget em 1600x900 e ignora tentativa de redimensionar.

Idempotência: os widgets têm id estável (`jornada`, `fluxo`). No `canvas_update_from_svg`
o servidor casa pelo id e deixa em paz um diagrama cuja fonte não mudou — então uma
segunda rodada de QA atualiza o board existente em vez de criar outro.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape as escapar_xml

import httpx

from config import get_settings
from tools.artefatos_html import e_diagrama_do_professor, extrair_mermaid_com_titulos

logger = logging.getLogger("miro_cliente")

# O board fixa o widget neste tamanho; o vão vem da escala de espaçamento do Miro.
LARGURA_DIAGRAMA = 1600
ALTURA_DIAGRAMA = 900
VAO = 320

_ID_BOARD = re.compile(r"/app/board/([^/?#]+)")


class SessaoMiro:
    """Uma sessão MCP viva: `initialize` uma vez, várias `tools/call` depois.

    O servidor devolve um `Mcp-Session-Id` no handshake e espera vê-lo nas chamadas
    seguintes; abrir uma sessão por chamada desperdiça um round-trip em cada uma.
    """

    def __init__(self, timeout: int = 60) -> None:
        s = get_settings()
        self.url = s.miro_mcp_url
        self.timeout = timeout
        self._cliente: Optional[httpx.Client] = None
        self._headers: Dict[str, str] = {}

    def __enter__(self) -> "SessaoMiro":
        from tools.miro_oauth import token_store

        s = get_settings()
        self._headers = {
            "Authorization": f"Bearer {token_store().access_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        self._cliente = httpx.Client(timeout=self.timeout)
        corpo, cabecalhos = self._post(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": s.app_name, "version": s.app_version},
                },
            },
            devolver_headers=True,
        )
        sessao = cabecalhos.get("mcp-session-id")
        if sessao:
            self._headers["Mcp-Session-Id"] = sessao
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"}, notificacao=True)
        return self

    def __exit__(self, *_exc) -> None:
        if self._cliente:
            self._cliente.close()
            self._cliente = None

    # ------------------------------------------------------------------ interno
    def _post(self, corpo: Dict[str, Any], devolver_headers: bool = False, notificacao: bool = False):
        assert self._cliente is not None, "use a sessão dentro de um `with`"
        resp = self._cliente.post(self.url, headers=self._headers, json=corpo)
        resp.raise_for_status()
        if notificacao:
            return None
        dados = _desembrulhar_sse(resp)
        return (dados, resp.headers) if devolver_headers else dados

    # -------------------------------------------------------------------- uso
    def chamar(self, ferramenta: str, argumentos: Dict[str, Any]) -> Dict[str, Any]:
        """Uma `tools/call`, com o JSON de resultado já desembrulhado."""
        corpo = self._post(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                # O servidor pede estes dois campos em toda chamada.
                "params": {
                    "name": ferramenta,
                    "arguments": {"invocation_source": None, "is_repository": True, **argumentos},
                },
            }
        )
        if "error" in corpo:
            raise RuntimeError(f"Miro respondeu erro em {ferramenta}: {corpo['error']}")
        return _conteudo_de(corpo)


def _desembrulhar_sse(resp: httpx.Response) -> Dict[str, Any]:
    """O endpoint responde ora JSON, ora um evento SSE com o JSON na linha `data:`."""
    if "text/event-stream" in resp.headers.get("content-type", ""):
        for linha in resp.text.splitlines():
            if linha.startswith("data:"):
                return json.loads(linha[5:].strip())
        return {}
    return resp.json()


def _conteudo_de(corpo: Dict[str, Any]) -> Dict[str, Any]:
    """O payload útil de uma `tools/call`, que vem como texto JSON dentro de `content`."""
    for parte in corpo.get("result", {}).get("content", []):
        if parte.get("type") == "text":
            try:
                return json.loads(parte["text"])
            except json.JSONDecodeError:
                return {"texto": parte["text"]}
    return corpo.get("result", {})


# ------------------------------------------------------------------ composição
def montar_svg(diagramas: List[Dict[str, str]], widgets: Optional[Dict[str, str]] = None) -> str:
    """Empilha os diagramas num documento do Canvas Composer.

    Cada bloco vira um `<foreignObject data-type="diagram">` com um título acima. O
    corpo é Mermaid puro, escapado para XML — sem isso o `-->` de cada aresta seria
    lido como tag e o documento inteiro seria recusado.

    `widgets` mapeia id local → `data-miro-id` da publicação anterior. **É o que
    diferencia atualizar de duplicar**: o servidor casa os elementos por esse atributo,
    não pelo id local, então um update sem ele cria um segundo par de diagramas no
    mesmo board (verificado na marra: quatro widgets viraram oito).
    """
    widgets = widgets or {}
    partes: List[str] = []
    y = 0
    for d in diagramas:
        id_titulo = f"titulo-{d['id']}"
        atr_titulo = _atributo_miro_id(widgets.get(id_titulo))
        atr_diagrama = _atributo_miro_id(widgets.get(d["id"]))
        partes.append(
            f'<text id="{id_titulo}" x="0" y="{y - 40}" fill="#1a1a1a" '
            f'font-family="noto_sans" font-size="33" font-weight="bold"{atr_titulo}>'
            f'{escapar_xml(d["titulo"])}</text>'
        )
        partes.append(
            f'<foreignObject id="{d["id"]}" x="0" y="{y}" '
            f'width="{LARGURA_DIAGRAMA}" height="{ALTURA_DIAGRAMA}" '
            f'data-type="diagram" data-title="{escapar_xml(d["titulo"])}"{atr_diagrama}>\n'
            f'{escapar_xml(d["mermaid"])}\n'
            f"</foreignObject>"
        )
        y += ALTURA_DIAGRAMA + VAO
    return "<svg>\n" + "\n".join(partes) + "\n</svg>"


def _atributo_miro_id(valor: Optional[str]) -> str:
    return f' data-miro-id="{valor}"' if valor else ""


_ELEMENTO_COM_ID = re.compile(r'<(?:text|textArea|foreignObject)\s[^>]*\bid="([^"]+)"[^>]*\bdata-miro-id="([^"]+)"')


def ids_dos_widgets(result_svg: Optional[str]) -> Dict[str, str]:
    """Extrai `{id local: data-miro-id}` do SVG que a publicação devolve.

    Guardar esse mapa é o que permite à rodada seguinte atualizar em vez de duplicar.
    """
    if not result_svg:
        return {}
    return {local: miro for local, miro in _ELEMENTO_COM_ID.findall(result_svg)}


def _url_do_board(dados: Dict[str, Any]) -> str:
    """A URL do board na resposta, qualquer que seja o nome do campo."""
    for chave in ("url", "board_url", "viewLink", "view_link", "link", "miro_url"):
        valor = dados.get(chave)
        if isinstance(valor, str) and "miro.com" in valor:
            return valor
    # Alguns retornos aninham o board num objeto.
    for valor in dados.values():
        if isinstance(valor, dict):
            achado = _url_do_board(valor)
            if achado:
                return achado
    return ""


def id_do_board(url: str) -> str:
    m = _ID_BOARD.search(url or "")
    return m.group(1) if m else ""


# ------------------------------------------------------------------- publicação
def publicar_diagramas(
    titulo: str,
    jornada: Optional[str],
    fluxo: Optional[str],
    board: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Publica (ou atualiza) o board com os diagramas da jornada e do fluxo.

    `jornada` e `fluxo` são os documentos inteiros do D2 e do D3: daqui saem os blocos
    Mermaid pela mesma função que monta a folha HTML, e é isso que garante que o board
    seja espelho, e não uma segunda versão que envelhece sozinha.

    `board` é o retorno de uma publicação anterior (`url_board` + `widgets`). Passá-lo
    faz a rodada seguinte atualizar o mesmo board; omiti-lo cria um novo.
    """
    diagramas: List[Dict[str, str]] = []
    ressalvas: List[str] = []

    for chave, titulo_bloco, documento in (
        ("jornada", "Jornada do estudante", jornada),
        ("fluxo", "Fluxo de telas", fluxo),
    ):
        blocos = extrair_mermaid_com_titulos(documento)
        if not blocos:
            ressalvas.append(f"{titulo_bloco}: nenhum bloco Mermaid no documento — nada a espelhar")
            continue
        # O primeiro bloco é o do estudante. O documento de fluxo traz um segundo grafo, o do
        # professor (preparo e condução), sob heading próprio: ele vira widget separado, com
        # id estável, para o board mostrar a visão do professor ao lado da do estudante.
        diagramas.append({"id": chave, "titulo": titulo_bloco, "mermaid": blocos[0][1]})
        extras = blocos[1:]
        professor = next((b for t, b in extras if e_diagrama_do_professor(t)), None)
        if professor:
            diagramas.append({"id": f"{chave}-professor", "titulo": f"{titulo_bloco.split(' ')[0]} do professor", "mermaid": professor})
        sobrando = len(extras) - (1 if professor else 0)
        if sobrando > 0:
            ressalvas.append(f"{titulo_bloco}: {len(blocos)} blocos Mermaid; espelhados o do estudante{' e o do professor' if professor else ''}")

    if not diagramas:
        raise RuntimeError("nenhum diagrama Mermaid para publicar")

    board = board or {}
    board_url = board.get("url_board") or ""
    widgets = dict(board.get("widgets") or {})

    with SessaoMiro() as sessao:
        modo = "atualizado"
        if not board_url:
            criado = sessao.chamar("board_create", {"name": (titulo[:60] or "Missão"), "icon_emoji": "🎓"})
            board_url = _url_do_board(criado)
            if not board_url:
                raise RuntimeError(f"o Miro criou o board mas não devolveu a URL: {criado}")
            modo = "criado"
            widgets = {}

        ferramenta = "canvas_create_from_svg" if modo == "criado" else "canvas_update_from_svg"
        resposta = sessao.chamar(ferramenta, {"miro_url": board_url, "svg": montar_svg(diagramas, widgets)})

    # O mapa novo substitui o antigo: o servidor reemite o id de cada elemento que
    # continua no board, e some com o de quem saiu.
    widgets = ids_dos_widgets(resposta.get("result_svg")) or widgets
    recusados = list(resposta.get("failed_items") or [])
    for falha in recusados:
        ressalvas.append(f"o Miro recusou um item: {sem_segredo(str(falha))[:160]}")

    return {
        "board_id": id_do_board(board_url),
        "url_board": board_url,
        "modo": modo,
        "widgets": widgets,
        "diagramas": [{"id": d["id"], "titulo": d["titulo"]} for d in diagramas],
        "ressalvas": ressalvas,
        "recusados": len(recusados),
    }


# ----------------------------------------------------------------------- folhas
def montar_folha_de_links(dados: Dict[str, Any], titulo: str = "") -> str:
    """O `design/11-miro-boards.md`: o link do board e o que foi espelhado."""
    linhas = [f"# Board no Miro — {titulo}".rstrip(" —"), ""]
    linhas.append(f"**Board:** {dados['url_board']}")
    linhas.append("")
    linhas.append("| Diagrama | Espelhado de |")
    linhas.append("| --- | --- |")
    origem = {
        "jornada": "`design/02-jornada-telas.md`",
        "fluxo": "`design/03-fluxo-arestas.md`",
        "fluxo-professor": "`design/03-fluxo-arestas.md` (seção \"Fluxo do professor\")",
        "jornada-professor": "`design/02-jornada-telas.md` (seção 1c)",
    }
    for d in dados.get("diagramas", []):
        linhas.append(f"| {d['titulo']} | {origem.get(d['id'], '—')} |")
    linhas.append("")
    linhas.append(
        "O board é **espelho**: quem manda é o Mermaid dos documentos acima, remontado "
        "também em `design/09-diagramas.html`. Editar o board não altera a fonte."
    )
    if dados.get("ressalvas"):
        linhas.append("")
        linhas.append("**Ressalvas**")
        linhas.extend(f"- {r}" for r in dados["ressalvas"])
    linhas.append("")
    linhas.append(
        "> Board privado do time: quem não tiver acesso vê 404. Compartilhe pelo próprio "
        "Miro se a revisão for feita por alguém de fora."
    )
    return "\n".join(linhas) + "\n"


def folha_de_indisponibilidade(motivo: str, titulo: str = "") -> str:
    """Grava-se isto mesmo com o Miro fora: a folha não fica ausente, e a falta do board vai ao semáforo do design."""
    cabecalho = f"# Board no Miro — {titulo}".rstrip(" —")
    return (
        f"{cabecalho}\n\n"
        f"**MIRO: indisponível — {sem_segredo(motivo)}.** A fonte dos diagramas continua sendo o "
        "Mermaid em `design/09-diagramas.html`, com a jornada em "
        "`design/02-jornada-telas.md` e o fluxo em `design/03-fluxo-arestas.md`.\n\n"
        "Isto **não é um achado de QA**: o espelho no Miro é conveniência, e a esteira "
        "entrega a missão sem ele. A falta do board aparece no semáforo do design, no gate "
        f"«{ROTULO_GATE}», sem bloquear.\n"
    )


#: O que, numa mensagem de erro, pode ser credencial: o cabeçalho `Bearer …`, `access_token=…`, um JWT, um segredo longo.
_RE_SEGREDO = re.compile(
    r"(?i)\bbearer\s+[^\s'\",;]+|"
    r"\b(?:access_token|refresh_token|id_token|client_secret|client_id|code_verifier|authorization|token|code)"
    r"(\s*[=:]\s*[\"']?)(?:bearer\s+)?[^\s'\",;&}]+|"
    r"\b[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,}\b|\b[A-Za-z0-9_\-]{32,}\b")


def sem_segredo(texto: str) -> str:
    """A mensagem sem o que pode ser credencial do Miro: ela vai à folha, ao relatório do gate e ao cartão do parecer."""
    def troca(m: "re.Match[str]") -> str:
        if m.group(1) is not None:
            nome = m.group(0)[: m.start(1) - m.start(0)]
            return f"{nome}{m.group(1)}[oculto]"
        return "[oculto]"

    return _RE_SEGREDO.sub(troca, texto or "")


def motivo_de_indisponibilidade(exc: BaseException) -> str:
    """Traduz a falha para uma linha que o relatório pode mostrar a um humano, sem credencial."""
    if isinstance(exc, httpx.HTTPStatusError):
        codigo = exc.response.status_code
        if codigo == 401:
            return "a conexão com o Miro expirou — reconecte pelo botão na barra lateral"
        if codigo == 403:
            return "a conta conectada não tem permissão de escrita neste time"
        if codigo == 429:
            return "limite de uso do Miro atingido"
        return f"o Miro respondeu {codigo}"
    if isinstance(exc, httpx.TimeoutException):
        return "tempo esgotado ao falar com o Miro"
    if isinstance(exc, httpx.HTTPError):
        return "falha de rede ao falar com o Miro"
    texto = str(exc).strip() or exc.__class__.__name__
    return sem_segredo(texto)[:160]


# ----------------------------------------------------------------------- gate
#: O veredito do espelho, no semáforo do design. Na exp06ef1b (727a3c2d, 28/09/2026) o espelho falhou, os cinco gates de
#: design ficaram 🟢 e o PO só soube ao abrir a missão («Fluxos não foram gerados, algum problema na ponte mermaid-miro»):
#: o único conserto foi refazer o design inteiro, 1.698 s (V13 do levantamento de deficiências de design, 24/10/2026).
#: O board é espelho, nunca fonte: a falta dele é 🟡 — não impede o de acordo nem gera ticket a agente de design —, e o
#: Miro desligado por configuração (`MIRO_MODE=off`) é ⚪, nunca 🟢.
KEY_STATUS = "miro_status"
KEY_REPORT = "miro_report"
ROTULO_GATE = "Espelho dos diagramas no Miro"
AGENTE = "espelho-miro"
DESLIGADO = "desligado"


def conferir_espelho(ligado: bool, jornada: str = "", fluxo: str = "", dados: Optional[Dict[str, Any]] = None,
                     motivo: str = "", board_anterior: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """`{status, achados}` do espelho: `aprovado` com o board completo, `amarelo` com o board ausente ou incompleto e
    `desligado` com o Miro desligado por configuração. `dados` é o retorno de `publicar_diagramas`; `motivo`, o da falha
    (`motivo_de_indisponibilidade`)."""
    if not ligado:
        return {"status": DESLIGADO, "achados": []}
    achados: List[Dict[str, Any]] = []
    anterior = str((board_anterior or {}).get("url_board") or "")
    if dados is None:
        resumo = (f"O board do Miro não foi {'atualizado' if anterior else 'criado'}: {sem_segredo(motivo or 'sem motivo')}. "
                  + (f"O board da execução anterior ({anterior}) ficou como estava e pode não ter os diagramas desta. "
                     if anterior else "A etapa saiu sem board. ")
                  + "Os diagramas da jornada e do fluxo continuam em `design/09-diagramas.html`, que é a fonte. Para ter o "
                    "board, reconecte o Miro (barra lateral) se a conexão caiu e rode o design de novo.")
        achados.append({"severidade": "atencao", "codigo": "miro-indisponivel", "etapa": "design",
                        "agente_responsavel": None, "classe": "pendencia-externa", "resumo": resumo})
    else:
        espelhados = {d.get("id") for d in dados.get("diagramas") or []}
        faltam = [nome for nome, doc in (("jornada", jornada), ("fluxo", fluxo))
                  if str(doc or "").strip() and nome not in espelhados]
        recusados = int(dados.get("recusados") or 0)
        if faltam or recusados:
            partes = ([f"sem o diagrama de {' e de '.join(faltam)}"] if faltam else []) + (
                [f"{recusados} item(ns) recusado(s) pelo Miro"] if recusados else [])
            achados.append({
                "severidade": "atencao", "codigo": "miro-board-incompleto", "etapa": "design", "agente_responsavel": None,
                "classe": "pendencia-externa",
                "resumo": (f"O board do Miro ({dados.get('url_board') or '—'}) saiu incompleto: {'; '.join(partes)}. "
                           "Os diagramas continuam em `design/09-diagramas.html`; as ressalvas estão em "
                           "`design/11-miro-boards.md`.")})
    return {"status": "amarelo" if achados else "aprovado", "achados": achados}


def relatorio_espelho(resultado: Dict[str, Any], missao: str = "") -> str:
    """O relatório do gate, com o envelope JSON que o dossiê e o cartão do parecer leem."""
    icone = {"aprovado": "🟢", "amarelo": "🟡", DESLIGADO: "⚪"}.get(resultado["status"], "⚪")
    linhas = [f"# {ROTULO_GATE}{f' — {missao}' if missao else ''}", "",
              f"**Veredito: {icone}** · o board é espelho do Mermaid da jornada e do fluxo; a falta dele não bloqueia.",
              ""]
    if resultado["status"] == DESLIGADO:
        linhas.append("- O Miro está desligado nesta instalação (`MIRO_MODE=off`): não há board, e os diagramas ficam em "
                      "`design/09-diagramas.html`.")
    elif not resultado["achados"]:
        linhas.append("- Board publicado com os diagramas da jornada e do fluxo.")
    for a in resultado["achados"]:
        linhas.append(f"- ⚠️ `{a['codigo']}` — {a['resumo']}")
    env = {"agente": AGENTE, "missao": missao, "status": resultado["status"], "achados": resultado["achados"],
           "precisa_humano": False}
    return "\n".join(linhas) + "\n\n```json\n" + json.dumps(env, ensure_ascii=False, indent=1) + "\n```\n"
