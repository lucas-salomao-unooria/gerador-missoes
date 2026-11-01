"""As imagens do one-pager pedagógico: a tela de cada passo e o desenho da jornada e do fluxo.

Quem aprova a missão lê o pedagógico e não abre o Stitch por fora. O documento conta a missão
passo a passo, e cada passo termina numa linha «Telas deste passo: `E2-ALU-01` · …» com os IDs do
inventário da jornada (`prompts/dev/120_one_pager_pedagogico.md`). Na exportação, essa linha vira a
imagem de cada tela, com a legenda `ID — título`, logo abaixo do passo.

De onde vêm as imagens: a folha `stitch_links` (`design/10-stitch-telas.md`), que o
`tools.stitch_cliente.montar_folha_de_links` monta com o endereço público da imagem de cada tela
(o título da tela começa pelo ID). Só as telas citadas num passo são baixadas; cada uma vai para um
cache na pasta da sessão (`.cache-imagens/`), porque o endereço do Stitch vence em poucos dias e a
exportação roda de novo a cada etapa. Download com tempo curto; falha não derruba a exportação —
vira a legenda "imagem indisponível" com o link. Três falhas de rede seguidas e o resto nem é tentado.

Sem desenho no Stitch — ele está desligado por padrão desde 22/10/2026 —, a tela vem do protótipo
navegável (`quadros_do_prototipo`): o quadro `data-screen-id` do estado padrão, com os estilos do
protótipo e sem os scripts. No `.html` ele entra como a própria tela, num `iframe` isolado; no
`.docx`, que não desenha HTML, vira a legenda com o caminho do protótipo.

Os diagramas vêm de `tools.diagrama_imagem`, desligado por padrão; desligado, o documento aponta
o `design/09-diagramas.html`.
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from tools.markdown_blocos import Bloco, analisar, ids_de_tela, texto_puro

logger = logging.getLogger("ilustracoes")

PASTA_CACHE = ".cache-imagens"
#: Largura da imagem embutida. 1200 px numa coluna de 13 cm dá ~230 dpi: o texto da tela se lê.
LARGURA_TELA_PX = 1200
LARGURA_DIAGRAMA_PX = 1800
TIMEOUT_S = 8.0
FALHAS_ATE_DESISTIR = 3
TAMANHO_MAXIMO = 15 * 1024 * 1024

INDISPONIVEL = "imagem indisponível"
#: O protótipo navegável (`design/08-prototipo.html`, `pipeline.artifacts.ARTIFACT_FILES`), de onde vêm as telas sem
#: Stitch — a partir de `design/`, onde o pedagógico fica.
CAMINHO_PROTOTIPO = "08-prototipo.html"
SEM_IMAGEM_NO_STITCH = "tela sem imagem no Stitch"

_ID_NO_INICIO = re.compile(r"^\s*E\d[-_](?:ALU|PROF|SIS)[-_]\d{2}[A-Za-z]?\s*(?:[—–:|-]+\s*)?", re.IGNORECASE)
_LINK = re.compile(r"\]\((https://[^)\s]+)\)")
_BOARD_MIRO = re.compile(r"https://miro\.com/app/board/[^\s)>\]]+")


@dataclass
class Figura:
    """Uma imagem pronta para embutir, ou o aviso de por que ela não veio."""

    rotulo: str
    imagem: Optional[bytes] = None  # PNG ou JPEG, que o Word e o navegador abrem
    mime: str = "image/png"
    svg: Optional[str] = None  # só o `.html` usa (diagrama do Miro sem conversor)
    html: Optional[str] = None  # só o `.html` usa: o quadro do protótipo, documento HTML inteiro e sem script
    link: Optional[str] = None
    aviso: str = ""
    largura: int = 0
    altura: int = 0


@dataclass
class TelaStitch:
    id: str
    titulo: str
    url_imagem: Optional[str]


@dataclass
class Ilustracoes:
    """O que a exportação do pedagógico precisa para pôr as imagens no lugar."""

    telas: Dict[str, List[Figura]] = field(default_factory=dict)
    propositos: Dict[str, str] = field(default_factory=dict)
    tem_stitch: bool = False
    #: Telas que vieram do protótipo porque o Stitch não as desenhou (ou está desligado).
    do_prototipo: bool = False
    diagramas: List[Figura] = field(default_factory=list)
    #: A frase que entra quando não há figura dos diagramas (ou falta alguma); "" = sessão sem diagrama.
    aviso_diagramas: str = ""

    def do_passo(self, ids: Sequence[str]) -> Tuple[List[Figura], List[str]]:
        """As figuras dos IDs, na ordem da linha; e os IDs que o Stitch não desenhou."""
        figuras: List[Figura] = []
        sem_desenho: List[str] = []
        for i in ids:
            achadas = self.telas.get(i) or []
            if achadas:
                # uma imagem por tela: o Stitch tem um desenho por estado desde que a esteira gera todos
                # (07/10/2026), e quem lê a missão precisa ver a tela, não cada variação dela — o estado
                # padrão, ou o primeiro; o texto do passo conta os outros
                figuras.append(next((f for f in achadas if "padr" in _norm(f.rotulo)), achadas[0]))
            else:
                sem_desenho.append(i)
        return figuras, sem_desenho

    def nomes(self, ids: Sequence[str]) -> str:
        """`E1-ALU-01 — Abertura do álbum` · …, com o propósito do inventário da jornada."""
        return " · ".join(f"{i} — {self.propositos[i]}" if self.propositos.get(i) else i for i in ids)

    @property
    def tem_telas(self) -> bool:
        """Há imagem de tela para pôr debaixo dos passos — do Stitch ou do protótipo."""
        return self.tem_stitch or self.do_prototipo

    @property
    def tem_diagramas(self) -> bool:
        return bool(self.diagramas or self.aviso_diagramas)


# ------------------------------------------------------------------------------------ leitura
def _norm(texto: str) -> str:
    sem = "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", sem).strip()


def _celulas(linha: str) -> List[str]:
    return [c.strip() for c in linha.strip().strip("|").split("|")]


def telas_da_folha(folha: Optional[str]) -> List[TelaStitch]:
    """As telas da folha do Stitch: o ID do começo do título, o resto do título e o link da imagem.

    Lê qualquer linha de tabela cuja primeira célula começa pelo ID — a folha repete as telas do
    professor numa segunda tabela, e a repetição sai pelo endereço da imagem.
    """
    telas: List[TelaStitch] = []
    vistas = set()
    for linha in (folha or "").splitlines():
        if not linha.lstrip().startswith("|"):
            continue
        primeira = _celulas(linha)[0].replace("`", "").replace("*", "").strip()
        ids = ids_de_tela(primeira)
        if not ids or not _ID_NO_INICIO.match(primeira):
            continue
        m = _LINK.search(linha)
        url = m.group(1) if m else None
        chave = (ids[0], url or primeira)
        if chave in vistas:
            continue
        vistas.add(chave)
        telas.append(TelaStitch(ids[0], _ID_NO_INICIO.sub("", primeira).strip(), url))
    return telas


def propositos_da_jornada(jornada: Optional[str]) -> Dict[str, str]:
    """ID → propósito, da tabela do inventário de telas da jornada (lida pelo nome da coluna)."""
    texto = jornada or ""
    m = re.search(r"^#{1,4}[^\n]*invent[áa]rio de telas[^\n]*$", texto, re.IGNORECASE | re.MULTILINE)
    if m:
        texto = texto[m.end():]
    saida: Dict[str, str] = {}
    cabecalho: Optional[List[str]] = None
    for linha in texto.splitlines():
        if not linha.lstrip().startswith("|"):
            if saida:
                break
            cabecalho = None
            continue
        celulas = _celulas(linha)
        if cabecalho is None:
            cabecalho = [_norm(c) for c in celulas]
            continue
        if not linha.replace("|", "").replace("-", "").replace(":", "").strip():
            continue
        if "proposito" not in cabecalho:
            continue
        ids = ids_de_tela(celulas[0])
        col = cabecalho.index("proposito")
        if ids and col < len(celulas):
            saida.setdefault(ids[0], celulas[col].replace("`", "").strip())
    return saida


_RE_QUADRO = re.compile(r"<(\w+)\b[^>]*\bdata-screen-id\s*=\s*[\"']([^\"']+)[\"'][^>]*>", re.IGNORECASE)
_RE_ESTADO = re.compile(r"\bdata-estado\s*=\s*[\"']([^\"']*)[\"']", re.IGNORECASE)
_RE_ESTILO = re.compile(r"<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
_RE_SCRIPT = re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_RE_EVENTO = re.compile(r"\s+on[a-z]+\s*=\s*(?:\"[^\"]*\"|'[^']*')", re.IGNORECASE)
#: O que os protótipos fazem para mostrar um quadro por vez e prender a página na altura da tela: desfeito no quadro
#: avulso, que tem de aparecer sozinho e inteiro.
_CSS_QUADRO_AVULSO = """
html, body { height: auto !important; overflow: visible !important; display: block !important;
             background: #FFFFFF !important; margin: 0 !important; }
body .moldura-mobile, body .moldura-desktop { width: 100% !important; max-width: 100% !important; margin: 0 !important; }
body .moldura-mobile [data-screen-id].tela-ativa,
body .moldura-desktop [data-screen-id].tela-ativa,
body [data-screen-id].tela-ativa { display: flex !important; flex-direction: column; min-height: 600px; }
.screen-meta-badge { display: none !important; }
"""
_RE_CLASSE = re.compile(r"\bclass\s*=\s*([\"'])(.*?)\1", re.IGNORECASE | re.DOTALL)


def _ativo(abertura: str) -> str:
    """A tag de abertura do quadro com a classe `tela-ativa`: os protótipos escondem todo quadro que não a tem."""
    m = _RE_CLASSE.search(abertura)
    if m:
        return abertura[:m.start(2)] + m.group(2) + " tela-ativa" + abertura[m.end(2):]
    return abertura[:-1].rstrip("/ ") + ' class="tela-ativa">'



def _fim_do_elemento(texto: str, inicio: int, tag: str) -> int:
    """O fim do elemento que abre em `inicio` (logo depois do `</tag>` que fecha o `<tag>` de abertura)."""
    abre = re.compile(rf"<{tag}\b", re.IGNORECASE)
    fecha = re.compile(rf"</{tag}\s*>", re.IGNORECASE)
    nivel, pos = 0, inicio
    while True:
        a = abre.search(texto, pos)
        f = fecha.search(texto, pos)
        if not f:
            return len(texto)
        if a and a.start() < f.start():
            nivel += 1
            pos = a.end()
            continue
        nivel -= 1
        pos = f.end()
        if nivel <= 0:
            return pos


def quadros_do_prototipo(prototipo: Optional[str]) -> Dict[str, str]:
    """ID da tela → o quadro do protótipo como documento HTML avulso (estilos do protótipo, nenhum script).

    O quadro é o do estado padrão (`padrão`, `normal`), ou o primeiro do ID: quem lê a missão precisa ver a tela, não
    cada variação dela. O protótipo que não marca os quadros com `data-screen-id` (os de antes de 07/10/2026) não dá
    quadro nenhum.
    """
    texto = re.sub(r"^```(?:html)?\s*\n|\n```\s*$", "", (prototipo or "").strip())
    if "data-screen-id" not in texto:
        return {}
    estilos = "\n".join(_RE_ESTILO.findall(texto.split("<body", 1)[0]) or _RE_ESTILO.findall(texto))
    escolhidos: Dict[str, Tuple[bool, str]] = {}
    for m in _RE_QUADRO.finditer(texto):
        tela = m.group(2).strip()
        estado = _norm((_RE_ESTADO.search(m.group(0)) or [None, ""])[1])
        padrao = not estado or "padr" in estado or "normal" in estado
        if tela in escolhidos and (escolhidos[tela][0] or not padrao):
            continue
        quadro = _ativo(m.group(0)) + texto[m.end():_fim_do_elemento(texto, m.start(), m.group(1))]
        quadro = _RE_EVENTO.sub("", _RE_SCRIPT.sub("", quadro))
        escolhidos[tela] = (padrao, quadro)
    return {
        tela: ("<!DOCTYPE html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
               f"{estilos}<style>{_CSS_QUADRO_AVULSO}</style></head><body>"
               f"<div class=\"{'moldura-desktop' if '-PROF-' in tela else 'moldura-mobile'}\">{quadro}</div></body></html>")
        for tela, (_, quadro) in escolhidos.items()
    }


def ids_citados(blocos: Sequence[Bloco]) -> List[str]:
    vistos: List[str] = []
    for b in blocos:
        for i in b.ids if b.tipo == "telas" else ():
            if i not in vistos:
                vistos.append(i)
    return vistos


def posicao_dos_diagramas(blocos: Sequence[Bloco]) -> Optional[int]:
    """Onde o desenho da jornada e do fluxo entra: no fim da seção do passo a passo.

    `None` quando o documento não tem a seção (nem a antiga «Como a missão acontece, do começo ao
    fim», nem «As telas»): aí o desenho vai antes do anexo, ou no fim.
    """
    criterios = (
        lambda t: "passo a passo" in t or t.startswith("como a missao acontece"),
        lambda t: t.startswith("as telas"),
    )
    for criterio in criterios:
        for n, b in enumerate(blocos):
            if b.tipo != "titulo" or b.nivel > 2 or not criterio(_norm(texto_puro(b.trechos))):
                continue
            for k in range(n + 1, len(blocos)):
                if blocos[k].tipo == "titulo" and blocos[k].nivel <= b.nivel:
                    return k
            return len(blocos)
    return None


def nivel_da_secao_dos_diagramas(blocos: Sequence[Bloco], posicao: Optional[int]) -> int:
    """O subtítulo dos diagramas fica um nível abaixo da seção em que eles entram."""
    if posicao is None:
        return 2
    for b in reversed(blocos[:posicao]):
        if b.tipo == "titulo" and b.nivel <= 2:
            return min(b.nivel + 1, 4)
    return 2


def indice_do_anexo(blocos: Sequence[Bloco]) -> int:
    for n, b in enumerate(blocos):
        if b.tipo == "titulo" and b.nivel == 1 and _norm(texto_puro(b.trechos)).startswith("anexo"):
            return n
    return len(blocos)


# ------------------------------------------------------------------------------------ imagens
class _Cache:
    """Imagens já preparadas (PNG ou JPEG), por chave, na pasta da sessão. Sem pasta, não guarda nada."""

    def __init__(self, pasta: Optional[Path]) -> None:
        self.pasta = Path(pasta) if pasta else None

    def _caminho(self, chave: str, ext: str) -> Optional[Path]:
        # Nome com ponto na frente: o registro no FileArtifactService do ADK (`_save_adk_artifacts`)
        # pula arquivo oculto, e o cache não é artefato. A pasta oculta já o tira do manifesto e do ZIP.
        if not self.pasta:
            return None
        return self.pasta / f".{hashlib.sha256(chave.encode('utf-8')).hexdigest()[:32]}.{ext}"

    def ler(self, chave: str, ext: str = "img") -> Optional[bytes]:
        caminho = self._caminho(chave, ext)
        try:
            return caminho.read_bytes() if caminho and caminho.is_file() else None
        except OSError:
            return None

    def gravar(self, chave: str, dados: bytes, ext: str = "img") -> None:
        caminho = self._caminho(chave, ext)
        if not caminho:
            return
        try:
            caminho.parent.mkdir(parents=True, exist_ok=True)
            caminho.write_bytes(dados)
        except OSError as exc:  # cache é conveniência
            logger.debug("Não gravei o cache %s: %s", caminho, exc)


def preparar_imagem(dados: bytes, largura_maxima: int = LARGURA_TELA_PX) -> Tuple[bytes, int, int, str]:
    """Qualquer imagem → `(bytes, largura, altura, mime)` que o Word aceita, no máximo `largura_maxima`.

    PNG ou JPEG que já cabe e não tem transparência passa como veio — reencodar a tela do Stitch
    quadruplicava o tamanho. WebP, GIF, transparência ou largura demais viram PNG.
    """
    from PIL import Image

    with Image.open(io.BytesIO(dados)) as im:
        im.load()
        transparente = im.mode in ("RGBA", "LA") or "transparency" in im.info
        if im.format in ("PNG", "JPEG") and im.width <= largura_maxima and not transparente \
                and im.mode in ("RGB", "L", "P"):
            return dados, im.width, im.height, "image/png" if im.format == "PNG" else "image/jpeg"
        if im.width > largura_maxima:
            im = im.resize((largura_maxima, max(1, round(im.height * largura_maxima / im.width))), Image.LANCZOS)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            fundo = Image.new("RGB", im.size, (255, 255, 255))
            fundo.paste(im, mask=im.split()[-1])
            im = fundo
        elif im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        saida = io.BytesIO()
        im.save(saida, "PNG", optimize=True)
        return saida.getvalue(), im.width, im.height, "image/png"


def _inspecionar(dados: bytes) -> Tuple[int, int, str]:
    """Largura, altura e tipo de uma imagem do cache."""
    try:
        from PIL import Image

        with Image.open(io.BytesIO(dados)) as im:
            return im.width, im.height, "image/jpeg" if im.format == "JPEG" else "image/png"
    except Exception:
        return 0, 0, "image/png"


def baixar_http(url: str, timeout: float = TIMEOUT_S) -> bytes:
    """GET de uma imagem pública: só `https`, só `image/*`, até 15 MB."""
    import httpx

    if not url.startswith("https://"):
        raise ValueError("só endereço https")
    resp = httpx.get(url, timeout=timeout, follow_redirects=True,
                     headers={"Accept": "image/png,image/jpeg,image/*;q=0.8"})
    resp.raise_for_status()
    tipo = (resp.headers.get("content-type") or "").lower()
    if not tipo.startswith("image/"):
        raise ValueError(f"não é imagem: {tipo or 'sem content-type'}")
    if len(resp.content) > TAMANHO_MAXIMO:
        raise ValueError("imagem grande demais")
    return resp.content


def _resposta_de_erro(exc: BaseException) -> bool:
    """O servidor respondeu (4xx/5xx, ou algo que não é imagem) — não é a rede que caiu."""
    try:
        import httpx

        if isinstance(exc, httpx.HTTPStatusError):
            return True
    except ImportError:  # pragma: no cover
        pass
    return isinstance(exc, ValueError)


def _url_na_largura(url: str) -> str:
    """A imagem do Stitch (googleusercontent) vem com 512 px; `=w1200` pede a largura certa."""
    if "googleusercontent.com/" in url and "=" not in url.rsplit("/", 1)[-1]:
        return f"{url}=w{LARGURA_TELA_PX}"
    return url


class _Baixador:
    def __init__(self, baixar: Callable[[str], bytes], cache: _Cache) -> None:
        self.baixar = baixar
        self.cache = cache
        self.falhas_seguidas = 0

    def figura(self, tela: TelaStitch) -> Figura:
        rotulo = f"{tela.id} — {tela.titulo}" if tela.titulo else tela.id
        if not tela.url_imagem:
            return Figura(rotulo, aviso=SEM_IMAGEM_NO_STITCH)
        guardada = self.cache.ler(tela.url_imagem)
        if guardada:
            largura, altura, mime = _inspecionar(guardada)
            return Figura(rotulo, imagem=guardada, mime=mime, link=tela.url_imagem, largura=largura, altura=altura)
        if self.falhas_seguidas >= FALHAS_ATE_DESISTIR:
            return Figura(rotulo, link=tela.url_imagem, aviso=INDISPONIVEL)
        try:
            candidatas = list(dict.fromkeys([_url_na_largura(tela.url_imagem), tela.url_imagem]))
            bruto, erro = None, None
            for url in candidatas:
                try:
                    bruto = self.baixar(url)
                    break
                except Exception as exc:
                    erro = exc
                    # A versão grande pode não existir (resposta HTTP de erro) e a original, sim. Rede
                    # fora do ar ou tempo esgotado não se resolve com outro endereço: não dobra a espera.
                    if not _resposta_de_erro(exc):
                        break
            if bruto is None:
                raise erro or RuntimeError("sem resposta")
            imagem, largura, altura, mime = preparar_imagem(bruto)
        except Exception as exc:
            self.falhas_seguidas += 1
            logger.warning("Imagem da tela %s indisponível: %s", tela.id, exc)
            return Figura(rotulo, link=tela.url_imagem, aviso=INDISPONIVEL)
        self.falhas_seguidas = 0
        self.cache.gravar(tela.url_imagem, imagem)
        return Figura(rotulo, imagem=imagem, mime=mime, link=tela.url_imagem, largura=largura, altura=altura)


# ---------------------------------------------------------------------------------- diagramas
def _url_do_board(state: Dict[str, Any]) -> str:
    board = state.get("miro_board")
    if isinstance(board, dict) and board.get("url_board"):
        return str(board["url_board"])
    m = _BOARD_MIRO.search(str(state.get("miro_links") or ""))
    return m.group(0) if m else ""


def frase_dos_diagramas(state: Dict[str, Any]) -> str:
    """A frase que substitui a figura: onde o desenho está, para quem quiser abrir."""
    if state.get("diagramas_html"):
        frase = ("O desenho da jornada (as etapas em ordem e quem conduz cada uma) e o do fluxo (o caminho "
                 "de tela em tela, inclusive os desvios) estão em `design/09-diagramas.html`, que abre no navegador.")
    else:
        frase = ("O desenho da jornada e o do fluxo estão nos documentos `design/02-jornada-telas.md` e "
                 "`design/03-fluxo-arestas.md`.")
    board = _url_do_board(state)
    if board:
        frase += f" Os dois também estão no board do Miro: [{board}]({board})."
    return frase


def _figuras_dos_diagramas(state: Dict[str, Any], cache: _Cache, renderizador: Any) -> Tuple[List[Figura], bool]:
    """(figuras, faltou alguma). Sem renderizador, nenhuma figura e nada sai daqui."""
    from tools.diagrama_imagem import diagramas_da_sessao

    diagramas = diagramas_da_sessao(state.get("jornada_telas"), state.get("fluxo_arestas"))
    if not diagramas:
        return [], False
    if renderizador is None:
        return [], True
    figuras: List[Figura] = []
    faltou = False
    origem = getattr(renderizador, "url", None) or getattr(renderizador, "url_board", None) or type(renderizador).__name__
    for d in diagramas:
        chave = f"diagrama|{origem}|{d.id}|{d.mermaid}"
        png = cache.ler(chave)
        svg_guardado = cache.ler(chave, "svg")
        if png or svg_guardado:
            faltou = faltou or not png  # SVG sem conversor: o `.docx` fica sem esta figura
            largura, altura, mime = _inspecionar(png) if png else (0, 0, "image/png")
            figuras.append(Figura(d.titulo, imagem=png, mime=mime, largura=largura, altura=altura,
                                  svg=svg_guardado.decode("utf-8") if svg_guardado else None))
            continue
        try:
            desenho = renderizador(d)
        except Exception as exc:  # renderizador fora do ar não derruba a exportação
            logger.warning("Diagrama %s sem figura: %s", d.id, exc)
            desenho = None
        if desenho is None or not (desenho.png or desenho.svg):
            faltou = True
            continue
        largura = altura = 0
        png, mime = None, "image/png"
        if desenho.png:
            try:
                png, largura, altura, mime = preparar_imagem(desenho.png, LARGURA_DIAGRAMA_PX)
                cache.gravar(chave, png)
            except Exception as exc:
                logger.warning("Figura do diagrama %s ilegível: %s", d.id, exc)
        if desenho.svg:
            cache.gravar(chave, desenho.svg.encode("utf-8"), "svg")
        if not png and not desenho.svg:
            faltou = True
            continue
        if not png:
            faltou = True  # SVG sem conversor: o `.docx` fica sem esta figura
        figuras.append(Figura(d.titulo, imagem=png, mime=mime, svg=desenho.svg, largura=largura, altura=altura))
    return figuras, faltou


# ------------------------------------------------------------------------------------- montagem
def montar_ilustracoes(
    state: Dict[str, Any],
    documento: str,
    pasta_cache: Optional[Path] = None,
    *,
    baixar: Optional[Callable[[str], bytes]] = None,
    renderizador: Any = "configurado",
) -> Ilustracoes:
    """Junta as imagens das telas citadas nos passos e as dos diagramas da sessão.

    `baixar` (url → bytes) e `renderizador` (`tools.diagrama_imagem`) entram por parâmetro para os
    testes; por padrão, o download é HTTP e o renderizador é o da configuração — desligado.
    """
    cache = _Cache(pasta_cache)
    blocos = analisar(documento or "")
    citados = ids_citados(blocos)
    telas = telas_da_folha(str(state.get("stitch_links") or ""))
    ilustracoes = Ilustracoes(propositos=propositos_da_jornada(str(state.get("jornada_telas") or "")),
                              tem_stitch=bool(telas))

    baixador = _Baixador(baixar or baixar_http, cache)
    for tela in telas:
        if tela.id in citados:
            ilustracoes.telas.setdefault(tela.id, []).append(baixador.figura(tela))
    # a tela que o Stitch não desenhou — ou todas, com o Stitch desligado — vem do protótipo navegável
    quadros = quadros_do_prototipo(str(state.get("prototipo_html") or ""))
    for tela_id in citados:
        desenhadas = [f for f in ilustracoes.telas.get(tela_id, []) if f.imagem]
        if desenhadas or tela_id not in quadros:
            continue
        rotulo = f"{tela_id} — {ilustracoes.propositos[tela_id]}" if ilustracoes.propositos.get(tela_id) else tela_id
        ilustracoes.telas[tela_id] = [Figura(rotulo, html=quadros[tela_id], link=CAMINHO_PROTOTIPO,
                                             aviso="tela do protótipo navegável")]
        ilustracoes.do_prototipo = True

    if isinstance(renderizador, str) and renderizador == "configurado":
        from tools.diagrama_imagem import renderizador_configurado

        renderizador = renderizador_configurado(state)
    figuras, faltou = _figuras_dos_diagramas(state, cache, renderizador)
    ilustracoes.diagramas = figuras
    if faltou or (not figuras and (state.get("diagramas_html") or state.get("jornada_telas") or state.get("fluxo_arestas"))):
        ilustracoes.aviso_diagramas = frase_dos_diagramas(state)
    return ilustracoes
