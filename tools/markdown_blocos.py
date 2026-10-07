"""Lê o Markdown que os agentes escrevem e devolve blocos, sem saber para onde vão.

Os one-pagers saem da esteira em dois formatos: `.docx`, para o time editar, e `.html`,
para imprimir em PDF. Os dois leem o mesmo documento, então o documento é interpretado
uma vez só, aqui, e cada renderizador cuida da aparência.

Cobre o que os prompts realmente produzem: títulos, parágrafos, listas com marcador e
numeradas (com um nível de recuo), tabelas, blocos de citação — o pedagógico abre com
um `>` dizendo o que se pede a quem lê —, divisórias e blocos de código. No texto:
**negrito**, *itálico*, `código` e [links](url), que no pedagógico são o item que deixa
a professora abrir o protótipo antes de aprovar.

O que não for reconhecido vira parágrafo, que é a falha certa: o texto aparece, só não
formatado.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

_TITULO = re.compile(r"^(#{1,6})\s+(.*)$")
_MARCADOR = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_NUMERADA = re.compile(r"^(\s*)\d+[.)]\s+(.*)$")
_LINHA_TABELA = re.compile(r"^\s*\|(.+)\|\s*$")
_SEPARADOR_TABELA = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
_DIVISORIA = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
_CITACAO = re.compile(r"^\s*>\s?(.*)$")
#: O envelope de contrato que o agente assina no fim do relatório. Ancorado no fim de propósito:
#: sem a âncora, `limpar()` apagava QUALQUER bloco ```json do documento — inclusive o exemplo de
#: payload que o one-pager cita — e o leitor recebia um buraco sem aviso.
_ENVELOPE = re.compile(r"(?:\n\s*(?:-{3,}|\*{3,})\s*)?\n?```json\s(?:(?!```)[\s\S])*```\s*\Z")
_FRONT_MATTER = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)
#: O anexo literal que a esteira cola no fim do pedagógico e do PRD (`tools.conteudo_aprovado`).
_ANEXO = re.compile(r"^#[ \t]+Anexo\b", re.MULTILINE)
#: «Telas deste passo: `E2-ALU-01` · `E2-ALU-02`» — a âncora das imagens no pedagógico. Aceita o
#: rótulo em negrito, como item de lista e com "desta etapa"/"deste momento".
_LINHA_TELAS = re.compile(
    r"^\s*(?:[-*+]\s+)?(?:\*\*|__)?\s*telas?\s+(?:deste|desta|do|da)\s+(?:passo|etapa|momento)\b", re.IGNORECASE
)
#: O ID de tela, como em `tools.telas.RE_ID`: `E<etapa>-<ator>-<nn>`, com `_` ou sufixo de estado.
_ID_TELA = re.compile(r"\bE(\d)[-_](ALU|PROF|SIS)[-_](\d{2})[A-Za-z]?(?![\w])")


def ids_de_tela(texto: str) -> List[str]:
    """IDs de tela citados na linha, normalizados (`E2-ALU-01`), sem repetição, na ordem."""
    vistos: List[str] = []
    for m in _ID_TELA.finditer((texto or "").upper()):
        i = f"E{m.group(1)}-{m.group(2)}-{m.group(3)}"
        if i not in vistos:
            vistos.append(i)
    return vistos

# **negrito** · *itálico* · `código` · [texto](url)
_TRECHOS = re.compile(
    r"(\*\*[^*]+\*\*|__[^_]+__|(?<!\*)\*[^*\n]+\*(?!\*)|`[^`]+`|\[[^\]\n]+\]\([^)\s]+\))"
)
_LINK = re.compile(r"^\[([^\]]+)\]\(([^)\s]+)\)$")


@dataclass
class Trecho:
    """Um pedaço de texto com a formatação que ele carrega."""

    texto: str
    negrito: bool = False
    italico: bool = False
    mono: bool = False
    href: Optional[str] = None


@dataclass
class Bloco:
    """Um bloco do documento. `tipo` diz o que é; os demais campos, o que ele carrega.

    tipos: ``titulo`` (nivel) · ``paragrafo`` · ``item`` (nivel, ordenada) ·
    ``citacao`` · ``tabela`` (linhas) · ``codigo`` (texto, idioma) · ``divisoria`` ·
    ``telas`` (ids) — a linha «Telas deste passo: `E2-ALU-01` · …» do one-pager pedagógico, que
    é a âncora onde a exportação põe a imagem de cada tela; sem imagens, sai como parágrafo.
    """

    tipo: str
    trechos: List[Trecho] = field(default_factory=list)
    nivel: int = 0
    ordenada: bool = False
    linhas: List[List[str]] = field(default_factory=list)
    texto: str = ""
    idioma: str = ""
    ids: List[str] = field(default_factory=list)


def formatar(texto: str) -> List[Trecho]:
    """Quebra uma linha de texto nos seus trechos formatados."""
    saida: List[Trecho] = []
    for pedaco in _TRECHOS.split(texto or ""):
        if not pedaco:
            continue
        m = _LINK.match(pedaco)
        if m:
            saida.append(Trecho(m.group(1), href=m.group(2)))
        elif (pedaco.startswith("**") and pedaco.endswith("**")) or (
            pedaco.startswith("__") and pedaco.endswith("__")
        ):
            saida.append(Trecho(pedaco[2:-2], negrito=True))
        elif pedaco.startswith("`") and pedaco.endswith("`"):
            saida.append(Trecho(pedaco[1:-1], mono=True))
        elif pedaco.startswith("*") and pedaco.endswith("*") and len(pedaco) > 2:
            saida.append(Trecho(pedaco[1:-1], italico=True))
        else:
            saida.append(Trecho(pedaco))
    return saida


def texto_puro(trechos: List[Trecho]) -> str:
    return "".join(t.texto for t in trechos)


def limpar(markdown: str) -> str:
    """Tira o envelope JSON do agente e o front matter — nenhum dos dois é do leitor.

    O envelope é o último bloco do que o agente escreveu, mas nem sempre o último do documento:
    no pedagógico a esteira cola o anexo literal (`# Anexo — conteúdo aprovado pelo PO`) DEPOIS
    dele, e o `.docx` da exp01ef1b (06/10/2026) saía com o JSON do contrato no meio do texto que
    a professora aprova. Antes de um `# Anexo` de nível 1 o envelope sai do mesmo jeito — só o que
    tem a assinatura `"agente"`, para um ```json citado no corpo continuar intacto.
    """
    texto = markdown or ""
    anexo = _ANEXO.search(texto)
    if anexo:
        corpo = texto[: anexo.start()].rstrip()
        sem_divisoria = re.sub(r"\n\s*(?:-{3,}|\*{3,})\s*\Z", "", corpo)
        m = _ENVELOPE.search(sem_divisoria)
        if m and '"agente"' in m.group(0):
            texto = sem_divisoria[: m.start()].rstrip() + "\n\n---\n\n" + texto[anexo.start() :]
    texto = _ENVELOPE.sub("", texto)
    texto = _FRONT_MATTER.sub("", texto)
    # A divisória que anunciava o envelope fica órfã no fim do documento.
    return re.sub(r"\n\s*(-{3,}|\*{3,})\s*\Z", "", texto.strip())


def titulo_do_documento(blocos: List[Bloco]) -> Optional[str]:
    """O `# ` de abertura, que vira o título da capa."""
    for bloco in blocos:
        if bloco.tipo == "divisoria":
            continue
        if bloco.tipo == "titulo" and bloco.nivel == 1:
            return texto_puro(bloco.trechos).strip()
        break
    return None


def _celulas(linha: str) -> List[str]:
    return [c.strip() for c in linha.strip().strip("|").split("|")]


def _blocos_de_codigo(linhas: List[str]) -> tuple:
    """`({linha de abertura: (linha de fechamento | None, idioma)}, {cercas órfãs})`.

    As cercas são pareadas como o renderizador as pareia (`_blocos`): qualquer uma abre, só a
    nua da mesma marca fecha — ```` ```typescript ```` dentro de um bloco é conteúdo, não fim.
    A leitura antiga alternava código e texto a cada linha de cerca, e um documento com cerca
    interna de linguagem saía com código e texto trocados até o fim. Cerca aberta no fim do
    texto segue a regra de `sanear_para_streamlit`: se o que vem depois é markdown (ou nada),
    ela é órfã e some; se é código, o bloco vai até o fim.
    """
    pares = _blocos(_cercas(linhas))
    orfas = set()
    if pares and pares[-1][1] is None:
        aberta = pares[-1][0]
        resto = linhas[aberta.linha + 1 :]
        so_divisoria = all(not l.strip() or _TRACO_SOB_TEXTO.match(l) for l in resto)
        if so_divisoria or any(_MARKDOWN_FORTE.search(l) for l in resto):
            orfas.add(aberta.linha)
            pares = pares[:-1]
    aberturas = {a.linha: (f.linha if f else None, a.idioma) for a, f in pares}
    return aberturas, orfas


def analisar(markdown: str) -> List[Bloco]:
    """Markdown → blocos, na ordem em que aparecem.

    O documento passa antes por `desembrulhar_documento`, o mesmo do saneamento da tela: o
    agente embrulha o documento em ```markdown e abre ```sql/```typescript dentro, e sem isto o
    `.docx` e o `.html` saíam com o documento inteiro num bloco de código.
    """
    linhas = limpar(desembrulhar_documento(markdown or "")).splitlines()
    codigo, orfas = _blocos_de_codigo(linhas)
    blocos: List[Bloco] = []
    paragrafo: List[str] = []

    def fechar_paragrafo() -> None:
        if paragrafo:
            blocos.append(Bloco("paragrafo", formatar(" ".join(paragrafo).strip())))
            paragrafo.clear()

    i = 0
    while i < len(linhas):
        linha = linhas[i]

        if i in orfas:
            fechar_paragrafo()
            i += 1
            continue

        if i in codigo:
            fechar_paragrafo()
            fim, idioma = codigo[i]
            fim = len(linhas) if fim is None else fim
            blocos.append(Bloco("codigo", texto="\n".join(linhas[i + 1 : fim]), idioma=idioma))
            i = fim + 1  # a cerca de fechamento
            continue

        if _LINHA_TELAS.match(linha) and ids_de_tela(linha):
            fechar_paragrafo()
            texto = re.sub(r"^\s*[-*+]\s+", "", linha).strip()
            blocos.append(Bloco("telas", formatar(texto), ids=ids_de_tela(linha)))
            i += 1
            continue

        if _LINHA_TABELA.match(linha):
            fechar_paragrafo()
            tabela: List[List[str]] = []
            while i < len(linhas) and _LINHA_TABELA.match(linhas[i]):
                if not _SEPARADOR_TABELA.match(linhas[i]):
                    tabela.append(_celulas(linhas[i]))
                i += 1
            if tabela:
                blocos.append(Bloco("tabela", linhas=tabela))
            continue

        if _CITACAO.match(linha):
            fechar_paragrafo()
            # Linhas de continuação recuadas pertencem à mesma frase da citação; uma
            # linha `>` vazia separa dois parágrafos dentro do mesmo bloco.
            partes: List[str] = []
            while i < len(linhas):
                m = _CITACAO.match(linhas[i])
                if not m:
                    break
                partes.append(m.group(1).strip())
                i += 1
            acumulado: List[str] = []
            for parte in partes:
                if parte:
                    acumulado.append(parte)
                elif acumulado:
                    blocos.append(Bloco("citacao", formatar(" ".join(acumulado))))
                    acumulado = []
            if acumulado:
                blocos.append(Bloco("citacao", formatar(" ".join(acumulado))))
            continue

        m = _TITULO.match(linha)
        if m:
            fechar_paragrafo()
            blocos.append(Bloco("titulo", formatar(m.group(2).strip()), nivel=len(m.group(1))))
            i += 1
            continue

        if _DIVISORIA.match(linha):
            fechar_paragrafo()
            blocos.append(Bloco("divisoria"))
            i += 1
            continue

        m = _MARCADOR.match(linha)
        if m:
            fechar_paragrafo()
            blocos.append(Bloco("item", formatar(m.group(2)), nivel=min(len(m.group(1)) // 2, 2)))
            i += 1
            continue

        m = _NUMERADA.match(linha)
        if m:
            fechar_paragrafo()
            blocos.append(
                Bloco("item", formatar(m.group(2)), nivel=min(len(m.group(1)) // 2, 2), ordenada=True)
            )
            i += 1
            continue

        if linha.strip():
            # Linha recuada logo depois de um item: é a continuação dele, não um
            # parágrafo novo. Os prompts quebram itens longos assim, e sem isto o fim
            # da frase — muitas vezes quem responde por uma pendência — descola do item.
            if not paragrafo and linha[:1].isspace() and blocos and blocos[-1].tipo == "item":
                blocos[-1].trechos.extend(formatar(" " + linha.strip()))
            else:
                paragrafo.append(linha.strip())
        else:
            fechar_paragrafo()
        i += 1

    fechar_paragrafo()
    return blocos


# ------------------------------------------------------------------ saneamento para o Streamlit
#: Uma linha de cerca: a marca (``` ou ~~~, três ou mais) e o resto, que é a linguagem quando ela abre.
_LINHA_CERCA = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
#: Código inline com qualquer número de crases (`x`, ``a`b``): não é prosa e não se mexe.
_INLINE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
#: O que só existe em markdown — título, linha de tabela, negrito. Medida de "markdown preso em código".
_MARKDOWN_FORTE = re.compile(r"^\s{0,3}#{1,6}\s|^\s*\|.*\|\s*$|\*\*\S")
#: As linguagens com que o agente embrulha um documento para entregá-lo.
_INVOLUCRO = ("markdown", "md")
#: Um invólucro que cobre ao menos esta fração do texto é o documento inteiro, não uma citação.
_COBRE_O_DOCUMENTO = 0.6
#: Um ```markdown que abre com título de nível 1 é um documento citado (a spec, a ficha do ambiente
#: e o relatório que o D0 e o D9 devolvem juntos); sem ele, é trecho citado e fica como código.
_TITULO_1 = re.compile(r"^\s{0,3}#\s")
#: Front matter YAML no topo; sem plugin, o Streamlit o mostra como <hr> + um <h2> com todas as chaves.
_FRONT_MATTER_TOPO = re.compile(r"\A---[ \t]*\n([\w-]+[ \t]*:.*\n(?:.*\n)*?)---[ \t]*(?:\n|\Z)")
#: `---` logo abaixo de uma linha de texto não é divisória: é o sublinhado que faz dela um <h2>.
_TRACO_SOB_TEXTO = re.compile(r"^ {0,3}-{2,}[ \t]*$")
#: `<br>` sem unsafe_allow_html aparece escrito na tela; nas tabelas ele separa itens da célula.
_BR = re.compile(r"[ \t]*<br\s*/?>[ \t]*(?:[-*•][ \t]+)?", re.IGNORECASE)
_LINHA_TABELA_S = re.compile(r"^\s*\|.*\|\s*$")
_SEPARADOR_TABELA_S = re.compile(r"^\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)+\|?\s*$")


@dataclass
class _Cerca:
    linha: int
    marca: str  # "`" ou "~"
    tamanho: int
    idioma: str  # "" quando a cerca é nua


def _cercas(linhas: List[str]) -> List[_Cerca]:
    achadas = []
    for i, linha in enumerate(linhas):
        m = _LINHA_CERCA.match(linha)
        if not m:
            continue
        marca, resto = m.group(1), m.group(2).strip()
        if marca[0] == "`" and "`" in resto:
            continue  # ```x``` numa linha só é código inline, não cerca
        achadas.append(_Cerca(i, marca[0], len(marca), resto.split()[0].lower() if resto else ""))
    return achadas


def _fecha(aberta: _Cerca, c: _Cerca) -> bool:
    """CommonMark: só fecha a cerca nua, da mesma marca e com pelo menos o mesmo tamanho."""
    return c.marca == aberta.marca and c.tamanho >= aberta.tamanho and not c.idioma


def _blocos(cercas: List[_Cerca]) -> List[tuple]:
    """Pareia as cercas como o renderizador pareia: qualquer uma abre, só `_fecha` fecha.

    `(abertura, None)` é bloco aberto até o fim do texto.
    """
    blocos, aberta = [], None
    for c in cercas:
        if aberta is None:
            aberta = c
        elif _fecha(aberta, c):
            blocos.append((aberta, c))
            aberta = None
    if aberta is not None:
        blocos.append((aberta, None))
    return blocos


def _markdown_preso(linhas: List[str], blocos: List[tuple]) -> int:
    """Quantas linhas de título, tabela ou negrito ficam dentro de bloco de código não-markdown."""
    total = 0
    for aberta, fechada in blocos:
        if aberta.idioma in _INVOLUCRO:
            continue  # citação declarada de markdown não conta: é intencional
        fim = fechada.linha if fechada else len(linhas)
        total += sum(1 for l in linhas[aberta.linha + 1 : fim] if _MARKDOWN_FORTE.search(l))
    return total


def desembrulhar_documento(texto: str) -> str:
    """Tira a cerca ```markdown que o agente põe em volta de um documento, inteiro ou citado.

    O renderizador fecha a cerca na PRIMEIRA cerca nua que encontra. O agente não escreve
    assim: embrulha a spec em ```markdown e, dentro dela, abre ```typescript … ```. O ``` que
    fecharia o typescript fecha o invólucro, e dali em diante código e texto trocam de lugar até
    o fim (PRD da exp06ef1b, 2026-09-28: front matter e seções 0–4 em bloco de código, a seção 5
    inteira também). Como fechamento do invólucro vale a cerca nua que deixa as cercas de dentro
    pareadas e prende menos markdown em bloco de código; no empate, a primeira — a leitura do
    renderizador. O invólucro sai quando o renderizador o fecharia em outro lugar, quando ele
    embrulha o documento quase inteiro (com ou sem uma frase de abertura antes) ou quando o que
    ele embrulha abre com `# Título` — é um documento citado, como a spec dentro do relatório do
    D0. Um ```markdown sem título, bem fechado, no meio de um relatório é trecho citado ("trecho
    proposto" do gate estrutural) e fica como código.
    Um ```markdown que nunca fecha perde a abertura: o que vem depois é o documento.
    """
    if not texto or not isinstance(texto, str) or ("```" not in texto and "~~~" not in texto):
        return texto
    linhas = texto.split("\n")
    nao_vazias = sum(1 for l in linhas if l.strip()) or 1
    remover: set = set()
    i = 0
    while True:
        cercas = [c for c in _cercas(linhas) if c.linha not in remover]
        if i >= len(cercas):
            break
        aberta = cercas[i]
        do_renderizador = next((j for j in range(i + 1, len(cercas)) if _fecha(aberta, cercas[j])), None)
        if aberta.idioma not in _INVOLUCRO:
            if do_renderizador is None:
                break
            i = do_renderizador + 1
            continue
        candidatas = [
            j for j in range(i + 1, len(cercas))
            if _fecha(aberta, cercas[j]) and all(f is not None for _, f in _blocos(cercas[i + 1 : j]))
        ]
        if not candidatas:
            if do_renderizador is None:  # invólucro que nunca fecha
                remover.add(aberta.linha)
                continue
            i = do_renderizador + 1
            continue

        def custo(j: int) -> int:
            return _markdown_preso(linhas, _blocos(cercas[i + 1 : j]) + _blocos(cercas[j + 1 :]))

        j = min(candidatas, key=lambda j: (custo(j), j))
        fechada = cercas[j]
        miolo = [l for l in linhas[aberta.linha + 1 : fechada.linha] if l.strip()]
        cobre = (len(miolo) + 2) / nao_vazias
        documento_citado = bool(miolo) and _TITULO_1.match(miolo[0]) is not None
        if j != do_renderizador or cobre >= _COBRE_O_DOCUMENTO or documento_citado:
            remover |= {aberta.linha, fechada.linha}
            continue  # as cercas de dentro viram as de fora: a varredura recomeça na mesma posição
        i = j + 1
    if not remover:
        return texto
    return "\n".join(l for n, l in enumerate(linhas) if n not in remover)


def _front_matter_em_bloco(texto: str) -> str:
    """O front matter vira um bloco ```yaml: continua à vista, sem virar um título gigante."""
    m = _FRONT_MATTER_TOPO.match(texto)
    if not m:
        return texto
    return "```yaml\n" + m.group(1) + "```\n" + texto[m.end() :]


def _contar_celulas(linha: str) -> int:
    corpo = linha.strip()
    corpo = corpo[1:] if corpo.startswith("|") else corpo
    corpo = corpo[:-1] if corpo.endswith("|") and not corpo.endswith("\\|") else corpo
    return len(re.split(r"(?<!\\)\|", corpo))


def _fora_do_codigo_inline(linha: str, trocar) -> str:
    """Aplica `trocar` só nos pedaços de prosa da linha; o que está entre crases fica igual."""
    pedacos: List[str] = []
    fim = 0
    for m in _INLINE.finditer(linha):
        pedacos.append(trocar(linha[fim : m.start()]))
        pedacos.append(m.group(0))
        fim = m.end()
    pedacos.append(trocar(linha[fim:]))
    return "".join(pedacos)


def _linha_de_prosa(linha: str) -> str:
    if "$" in linha:
        # `(?<!\\)`: o `\$` que o agente já escapou não vira `\\$`, que voltaria a abrir LaTeX
        linha = _fora_do_codigo_inline(linha, lambda p: re.sub(r"(?<!\\)\$", r"\\$", p))
    if "<br" in linha.lower():
        linha = _fora_do_codigo_inline(linha, lambda p: _BR.sub(" · ", p))
    if _LINHA_TABELA_S.match(linha) and "`" in linha:
        # na tabela, o `|` dentro de crase também separa célula: a linha ganha uma coluna e a
        # última é descartada em silêncio (fluxo de arestas da 4e6cf385, aresta A18)
        linha = _INLINE.sub(lambda m: re.sub(r"(?<!\\)\|", r"\\|", m.group(0)), linha)
    return linha


def sanear_para_streamlit(texto: str) -> str:
    """Prepara markdown de LLM para `st.markdown` sem que ele se desfaça na tela.

    Corrige o que o agente escreve por direito e o renderizador do Streamlit (react-markdown
    com GFM, math e diretivas, sem HTML) entende como outra coisa:

    - **Invólucro ```markdown.** Ver `desembrulhar_documento`: é o que punha a spec e o PRD
      crus na tela, com `#`, `|` e `**` à mostra.
    - **Cerca aberta e não fechada.** Se o que vem depois dela é markdown (ou nada), ela é
      órfã e sai; se é código, ganha o fechamento no fim.
    - **`$` vira LaTeX.** `$…$` é KaTeX inline e `$$…$$` é bloco; "custa R$ 10, no máximo
      R$ 30" some entre os dois cifrões, e um `DO $$ … END $$` de PL/pgSQL engole o corpo
      inteiro. O `$` da prosa é escapado; dentro de cerca ou de crase ele é código e fica.
      As cercas são pareadas como o renderizador as pareia — ```` ```typescript ```` não fecha
      bloco —, senão o `\\$` aparece escrito dentro do código.
    - **Front matter** vira bloco ```yaml (sem isso, `<hr>` + um `<h2>` com todas as chaves).
    - **`---` colado embaixo de um parágrafo** ganha uma linha em branco: é divisória, não o
      sublinhado que transforma o parágrafo inteiro num `<h2>`.
    - **Tabela:** `|` dentro de crase é escapado; a linha separadora ganha o número de colunas
      do cabeçalho (com uma a mais, a tabela inteira sai como texto com pipes); linhas de
      tabela sem cabeçalho ganham um cabeçalho vazio; `<br>` vira ` · `, porque sem HTML ele
      aparece escrito na célula.
    """
    if not texto or not isinstance(texto, str):
        return texto or ""

    texto = _front_matter_em_bloco(desembrulhar_documento(texto))
    linhas = texto.split("\n")
    blocos = _blocos(_cercas(linhas))

    # cerca órfã no fim
    fechar_no_fim = False
    if blocos and blocos[-1][1] is None:
        aberta = blocos[-1][0]
        resto = linhas[aberta.linha + 1 :]
        so_divisoria = all(not l.strip() or _TRACO_SOB_TEXTO.match(l) for l in resto)
        if so_divisoria or any(_MARKDOWN_FORTE.search(l) for l in resto):
            linhas[aberta.linha] = ""
            blocos = blocos[:-1]
        else:
            fechar_no_fim = True

    em_codigo = [False] * len(linhas)
    for aberta, fechada in blocos:
        for n in range(aberta.linha, (fechada.linha if fechada else len(linhas) - 1) + 1):
            em_codigo[n] = True

    saida: List[str] = []
    for n, linha in enumerate(linhas):
        if em_codigo[n]:
            saida.append(linha)
            continue
        anterior = saida[-1] if saida else ""
        anterior_e_prosa = n > 0 and not em_codigo[n - 1] and anterior.strip()
        if _TRACO_SOB_TEXTO.match(linha) and anterior_e_prosa and not _LINHA_TABELA_S.match(anterior):
            saida.append("")
        elif _SEPARADOR_TABELA_S.match(linha) and _LINHA_TABELA_S.match(anterior):
            colunas = _contar_celulas(anterior)
            if _contar_celulas(linha) != colunas:
                linha = "|" + "---|" * colunas
        elif (
            _LINHA_TABELA_S.match(linha)
            and not _LINHA_TABELA_S.match(anterior)
            and n + 1 < len(linhas)
            and _LINHA_TABELA_S.match(linhas[n + 1])
            and not _SEPARADOR_TABELA_S.match(linhas[n + 1])
        ):
            colunas = _contar_celulas(linha)
            if anterior.strip():
                saida.append("")
            saida.append("|" + " |" * colunas)
            saida.append("|" + "---|" * colunas)
        saida.append(_linha_de_prosa(linha))

    saneado = "\n".join(saida)
    if fechar_no_fim:
        saneado = saneado.rstrip("\n") + "\n```\n"
    return saneado
