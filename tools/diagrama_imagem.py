"""A figura da jornada e do fluxo para o one-pager pedagógico — desligada por padrão.

Os diagramas são Mermaid (`jornada_telas` e `fluxo_arestas`), e quem os desenha é o mermaid.js,
no navegador: é assim que nasce o `design/09-diagramas.html`. O `.docx` não roda JavaScript, e a
imagem do Cloud Run não tem navegador (só o Node do proxy do MCP). Então a figura vem de fora,
por um de dois caminhos, escolhidos em `DIAGRAMA_IMAGEM_FONTE`:

- ``url`` — um renderizador HTTP de Mermaid (`MERMAID_RENDER_URL`), no formato do mermaid.ink
  (GET com o Mermaid em base64url) ou do Kroki (POST com o Mermaid no corpo). **Envia o texto do
  fluxo da missão a esse serviço**: se for um serviço público, é um terceiro lendo a missão.
- ``miro`` — lê o board que o espelho (`tools.miro_cliente`) já publicou, com `canvas_read_as_svg`,
  e recorta o widget `jornada`/`fluxo`. Se o Miro devolver o widget desenhado (formas SVG), ele
  vira PNG aqui mesmo (`cairosvg`, se instalado; sem ele, a figura só vai para o `.html`). Se
  devolver só o Mermaid dentro do `foreignObject` — que é como a esteira o publica —, não há o
  que desenhar e a exportação cai na frase que aponta o `09-diagramas.html`. **O formato que o
  `canvas_read_as_svg` devolve não foi conferido ao vivo**: o token local é antigo e o Miro
  rotaciona o refresh token a cada renovação, e renovar fora da esteira derruba a sessão dela.
- ``off`` (padrão) — nada sai daqui; o documento aponta o `design/09-diagramas.html`.

Os renderizadores recebem o cliente HTTP e a sessão do Miro por parâmetro: os testes passam
falsos e nada vai para a rede.
"""

from __future__ import annotations

import base64
import copy
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from tools.artefatos_html import e_diagrama_do_professor, extrair_mermaid_com_titulos

logger = logging.getLogger("diagrama_imagem")

#: Um diagrama grande leva alguns segundos no mermaid.ink; mais que isso é serviço fora do ar.
TIMEOUT_S = 20.0
#: Largura do PNG quando o SVG do Miro é convertido aqui.
LARGURA_PNG = 1600
#: O tamanho que o renderizador devolve é limitado: imagem de diagrama não passa disso.
TAMANHO_MAXIMO = 15 * 1024 * 1024

_SVG_NS = "http://www.w3.org/2000/svg"
_XLINK_NS = "http://www.w3.org/1999/xlink"
#: O que conta como "desenhado": forma de verdade, não o `foreignObject` com o texto do Mermaid.
_FORMAS = {"path", "rect", "polygon", "polyline", "line", "circle", "ellipse", "image", "use"}


@dataclass
class Diagrama:
    """Um bloco Mermaid da sessão. `id` é o do widget no Miro (`jornada`, `fluxo-professor`…)."""

    id: str
    titulo: str
    mermaid: str


@dataclass
class Desenho:
    """O que um renderizador devolve: PNG (vai ao `.docx` e ao `.html`) ou só SVG (só ao `.html`)."""

    png: Optional[bytes] = None
    svg: Optional[str] = None


Renderizador = Callable[[Diagrama], Optional[Desenho]]


def diagramas_da_sessao(jornada: Optional[str], fluxo: Optional[str]) -> List[Diagrama]:
    """Os mesmos blocos, com os mesmos ids, que `miro_cliente.publicar_diagramas` espelha no board."""
    saida: List[Diagrama] = []
    for chave, titulo, documento in (("jornada", "Jornada do estudante", jornada), ("fluxo", "Fluxo de telas", fluxo)):
        blocos = extrair_mermaid_com_titulos(documento)
        if not blocos:
            continue
        saida.append(Diagrama(chave, titulo, blocos[0][1]))
        professor = next((b for t, b in blocos[1:] if e_diagrama_do_professor(t)), None)
        if professor:
            saida.append(Diagrama(f"{chave}-professor", f"{titulo.split(' ')[0]} do professor", professor))
    return saida


# --------------------------------------------------------------------------- url (mermaid.ink, Kroki)
def _base64url(texto: str) -> str:
    return base64.urlsafe_b64encode(texto.encode("utf-8")).decode("ascii")


class RenderizadorUrl:
    """Mermaid → PNG por um serviço HTTP. Três formas de endereço:

    - com ``{codigo}`` — GET, com o Mermaid em base64url no lugar da marca;
    - terminado em ``/png`` (Kroki: ``https://kroki.io/mermaid/png``) — POST com o Mermaid no corpo;
    - qualquer outro (mermaid.ink: ``https://mermaid.ink/img``) — GET em ``<url>/<base64url>?type=png``.
    """

    def __init__(self, url: str, cliente: Any = None, timeout: float = TIMEOUT_S) -> None:
        self.url = url.strip()
        self.timeout = timeout
        if cliente is None:
            import httpx

            cliente = httpx
        self.cliente = cliente

    def __call__(self, diagrama: Diagrama) -> Optional[Desenho]:
        if "{codigo}" in self.url:
            resp = self.cliente.get(self.url.replace("{codigo}", _base64url(diagrama.mermaid)),
                                    timeout=self.timeout, follow_redirects=True)
        elif self.url.rstrip("/").endswith("/png"):
            resp = self.cliente.post(self.url, content=diagrama.mermaid.encode("utf-8"),
                                     headers={"Content-Type": "text/plain; charset=utf-8"},
                                     timeout=self.timeout, follow_redirects=True)
        else:
            resp = self.cliente.get(f"{self.url.rstrip('/')}/{_base64url(diagrama.mermaid)}", params={"type": "png"},
                                    timeout=self.timeout, follow_redirects=True)
        resp.raise_for_status()
        tipo = (resp.headers.get("content-type") or "").lower()
        if not tipo.startswith("image/") or len(resp.content) > TAMANHO_MAXIMO:
            raise ValueError(f"o renderizador não devolveu imagem ({tipo or 'sem content-type'}, {len(resp.content)} bytes)")
        if "svg" in tipo:
            svg = resp.content.decode("utf-8", "replace")
            return Desenho(png=svg_para_png(svg), svg=svg)
        return Desenho(png=resp.content)


# ------------------------------------------------------------------------------------------- miro
def _local(tag: Any) -> str:
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _achar_svg(valor: Any) -> Optional[str]:
    """O documento SVG na resposta da ferramenta, qualquer que seja o nome do campo."""
    if isinstance(valor, str):
        return valor if "<svg" in valor else None
    if isinstance(valor, dict):
        for chave in ("svg", "result_svg", "texto", "content", "data"):
            achado = _achar_svg(valor.get(chave))
            if achado:
                return achado
        for item in valor.values():
            achado = _achar_svg(item)
            if achado:
                return achado
    if isinstance(valor, list):
        for item in valor:
            achado = _achar_svg(item)
            if achado:
                return achado
    return None


def desenhado(elemento: ET.Element) -> bool:
    """O widget veio com formas SVG? Só o `foreignObject` com o texto do Mermaid não conta."""
    return any(_local(e.tag) in _FORMAS for e in elemento.iter())


def elemento_do_widget(raiz: ET.Element, diagrama: Diagrama, miro_id: Optional[str] = None) -> Optional[ET.Element]:
    """O elemento do widget: pelo `data-miro-id` da publicação, pelo id local ou pelo título."""
    candidatos = list(raiz.iter())
    for criterio in (
        lambda e: bool(miro_id) and e.get("data-miro-id") == miro_id,
        lambda e: e.get("id") == diagrama.id,
        lambda e: (e.get("data-title") or "").strip() == diagrama.titulo,
    ):
        achado = next((e for e in candidatos if e is not raiz and criterio(e)), None)
        if achado is not None:
            return achado
    return None


def _sem_namespace(elemento: ET.Element) -> ET.Element:
    """Cópia com as tags sem namespace, para serializar como SVG simples (sem `ns0:`)."""
    copia = copy.deepcopy(elemento)
    for e in copia.iter():
        e.tag = _local(e.tag)
        for chave in list(e.attrib):
            if chave.startswith("{"):
                valor = e.attrib.pop(chave)
                ns, nome = chave[1:].split("}", 1)
                e.set(f"xlink:{nome}" if ns == _XLINK_NS else nome, valor)
    return copia


def svg_isolado(elemento: ET.Element, raiz: ET.Element) -> str:
    """O widget como documento SVG próprio, com a caixa dele (ou a do board, sem ela)."""
    caixa = [elemento.get(a) for a in ("x", "y", "width", "height")]
    if all(caixa[2:]):
        x, y = caixa[0] or "0", caixa[1] or "0"
        dimensoes = f'viewBox="{x} {y} {caixa[2]} {caixa[3]}" width="{caixa[2]}" height="{caixa[3]}"'
    else:
        dimensoes = " ".join(f'{a}="{raiz.get(a)}"' for a in ("viewBox", "width", "height") if raiz.get(a))
    corpo = ET.tostring(_sem_namespace(elemento), encoding="unicode")
    return f'<svg xmlns="{_SVG_NS}" xmlns:xlink="{_XLINK_NS}" {dimensoes}>{corpo}</svg>'


def svg_para_png(svg: str) -> Optional[bytes]:
    """SVG → PNG com `cairosvg`, se estiver instalado. Sem ele, `None`: a figura fica só no `.html`."""
    try:
        import cairosvg  # type: ignore[import-not-found]
    except Exception:
        return None
    try:
        return cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=LARGURA_PNG)
    except Exception as exc:  # SVG que o cairo não entende não derruba a exportação
        logger.warning("cairosvg não converteu o diagrama: %s", exc)
        return None


class RenderizadorMiro:
    """Recorta o widget do diagrama do SVG que o `canvas_read_as_svg` devolve para o board da sessão.

    O board é lido uma vez só, na primeira figura pedida. Widget ausente ou só com o texto do
    Mermaid → `None`, e a exportação usa a frase que aponta o `09-diagramas.html`.
    """

    def __init__(self, url_board: str, widgets: Optional[Dict[str, str]] = None, sessao: Any = None) -> None:
        self.url_board = url_board
        self.widgets = dict(widgets or {})
        if sessao is None:
            from tools.miro_cliente import SessaoMiro

            sessao = SessaoMiro
        self._abrir_sessao = sessao
        self._raiz: Optional[ET.Element] = None
        self._lido = False

    def _board(self) -> Optional[ET.Element]:
        if not self._lido:
            self._lido = True
            with self._abrir_sessao() as sessao:
                resposta = sessao.chamar("canvas_read_as_svg", {"miro_url": self.url_board})
            svg = _achar_svg(resposta)
            if not svg:
                logger.warning("canvas_read_as_svg não devolveu SVG: %s", str(resposta)[:200])
                return None
            try:
                self._raiz = ET.fromstring(svg[svg.index("<svg"):])
            except (ET.ParseError, ValueError) as exc:
                logger.warning("SVG do board ilegível: %s", exc)
        return self._raiz

    def __call__(self, diagrama: Diagrama) -> Optional[Desenho]:
        raiz = self._board()
        if raiz is None:
            return None
        elemento = elemento_do_widget(raiz, diagrama, self.widgets.get(diagrama.id))
        if elemento is None or not desenhado(elemento):
            return None
        svg = svg_isolado(elemento, raiz)
        return Desenho(png=svg_para_png(svg), svg=svg)


def renderizador_configurado(
    state: Dict[str, Any], *, fonte: Optional[str] = None, cliente_http: Any = None, sessao_miro: Any = None
) -> Optional[Renderizador]:
    """O renderizador que a configuração escolheu, ou `None` quando nada deve sair daqui."""
    from config import get_settings

    s = get_settings()
    fonte = (fonte or s.diagrama_imagem_fonte or "off").strip().lower()
    if fonte == "url" and s.mermaid_render_url.strip():
        return RenderizadorUrl(s.mermaid_render_url, cliente_http)
    if fonte == "miro":
        board = state.get("miro_board") if isinstance(state.get("miro_board"), dict) else {}
        url_board = (board or {}).get("url_board") or ""
        if url_board:
            return RenderizadorMiro(url_board, (board or {}).get("widgets"), sessao_miro)
    return None
