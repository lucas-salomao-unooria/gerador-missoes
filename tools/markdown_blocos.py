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
_CERCA = re.compile(r"^\s*```\s*([\w-]*)\s*$")
_ENVELOPE = re.compile(r"```json.*?```", re.DOTALL)
_FRONT_MATTER = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.DOTALL)

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
    ``citacao`` · ``tabela`` (linhas) · ``codigo`` (texto, idioma) · ``divisoria``
    """

    tipo: str
    trechos: List[Trecho] = field(default_factory=list)
    nivel: int = 0
    ordenada: bool = False
    linhas: List[List[str]] = field(default_factory=list)
    texto: str = ""
    idioma: str = ""


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
    """Tira o envelope JSON do agente e o front matter — nenhum dos dois é do leitor."""
    texto = _ENVELOPE.sub("", markdown or "")
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


def analisar(markdown: str) -> List[Bloco]:
    """Markdown → blocos, na ordem em que aparecem."""
    linhas = limpar(markdown).splitlines()
    blocos: List[Bloco] = []
    paragrafo: List[str] = []

    def fechar_paragrafo() -> None:
        if paragrafo:
            blocos.append(Bloco("paragrafo", formatar(" ".join(paragrafo).strip())))
            paragrafo.clear()

    i = 0
    while i < len(linhas):
        linha = linhas[i]

        m = _CERCA.match(linha)
        if m:
            fechar_paragrafo()
            idioma = m.group(1)
            corpo: List[str] = []
            i += 1
            while i < len(linhas) and not _CERCA.match(linhas[i]):
                corpo.append(linhas[i])
                i += 1
            i += 1  # a cerca de fechamento
            blocos.append(Bloco("codigo", texto="\n".join(corpo), idioma=idioma))
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
