"""Converte o one-pager pedagógico de Markdown para `.docx`.

Existe porque o time pedagógico não lê Markdown: lê um documento que abre no Word, no
Google Docs ou no LibreOffice, com título, lista e tabela no lugar. A conversão é
determinística e roda sem modelo nenhum.

Cobre o que o documento realmente usa: títulos de um a três níveis, parágrafos, listas
com marcador e numeradas, tabelas, linha divisória, e **negrito**, *itálico* e `código`
dentro do texto. O que não for reconhecido vira parágrafo comum, que é a falha certa:
o texto aparece, só não formatado.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple

_TITULO = re.compile(r"^(#{1,6})\s+(.*)$")
_MARCADOR = re.compile(r"^\s*[-*+]\s+(.*)$")
_NUMERADA = re.compile(r"^\s*\d+[.)]\s+(.*)$")
_LINHA_TABELA = re.compile(r"^\s*\|(.+)\|\s*$")
_SEPARADOR_TABELA = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
_DIVISORIA = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
_ENVELOPE = re.compile(r"```json.*?```", re.DOTALL)
# **negrito** · *itálico* · `código`
_TRECHOS = re.compile(r"(\*\*[^*]+\*\*|(?<!\*)\*[^*]+\*(?!\*)|`[^`]+`)")


def _celulas(linha: str) -> List[str]:
    return [c.strip() for c in linha.strip().strip("|").split("|")]


def _escrever_trechos(paragrafo, texto: str) -> None:
    """Quebra o texto em pedaços formatados e os acrescenta ao parágrafo."""
    for pedaco in _TRECHOS.split(texto):
        if not pedaco:
            continue
        if pedaco.startswith("**") and pedaco.endswith("**"):
            paragrafo.add_run(pedaco[2:-2]).bold = True
        elif pedaco.startswith("`") and pedaco.endswith("`"):
            run = paragrafo.add_run(pedaco[1:-1])
            run.font.name = "Consolas"
        elif pedaco.startswith("*") and pedaco.endswith("*") and len(pedaco) > 2:
            paragrafo.add_run(pedaco[1:-1]).italic = True
        else:
            paragrafo.add_run(pedaco)


def _bloco_de_tabela(linhas: List[str], inicio: int) -> Tuple[List[List[str]], int]:
    """Lê uma tabela a partir de `inicio` e devolve as linhas e onde ela termina."""
    corpo: List[List[str]] = []
    i = inicio
    while i < len(linhas) and _LINHA_TABELA.match(linhas[i]):
        if not _SEPARADOR_TABELA.match(linhas[i]):
            corpo.append(_celulas(linhas[i]))
        i += 1
    return corpo, i


def markdown_para_docx(markdown: str, destino: Path, titulo_fallback: str = "Documento") -> Optional[Path]:
    """Escreve o `.docx` e devolve o caminho. ``None`` se a biblioteca não estiver instalada."""
    try:
        from docx import Document
        from docx.shared import Pt
    except ImportError:  # pragma: no cover - dependência declarada em requirements
        return None

    texto = _ENVELOPE.sub("", markdown or "").strip()
    doc = Document()
    estilo = doc.styles["Normal"]
    estilo.font.name = "Calibri"
    estilo.font.size = Pt(11)

    linhas = texto.splitlines()
    i = 0
    escreveu_titulo = False
    while i < len(linhas):
        linha = linhas[i]

        if _LINHA_TABELA.match(linha):
            corpo, i = _bloco_de_tabela(linhas, i)
            if corpo:
                tabela = doc.add_table(rows=len(corpo), cols=max(len(l) for l in corpo))
                tabela.style = "Light Grid Accent 1"
                for r, celulas in enumerate(corpo):
                    for c, valor in enumerate(celulas):
                        celula = tabela.cell(r, c)
                        celula.text = ""
                        p = celula.paragraphs[0]
                        _escrever_trechos(p, valor)
                        if r == 0:
                            for run in p.runs:
                                run.bold = True
                doc.add_paragraph()
            continue

        m = _TITULO.match(linha)
        if m:
            nivel = len(m.group(1))
            doc.add_heading(re.sub(r"[*`]", "", m.group(2)).strip(), level=min(nivel, 4))
            escreveu_titulo = True
            i += 1
            continue

        if _DIVISORIA.match(linha):
            doc.add_paragraph()
            i += 1
            continue

        m = _MARCADOR.match(linha)
        if m:
            _escrever_trechos(doc.add_paragraph(style="List Bullet"), m.group(1))
            i += 1
            continue

        m = _NUMERADA.match(linha)
        if m:
            _escrever_trechos(doc.add_paragraph(style="List Number"), m.group(1))
            i += 1
            continue

        if linha.strip():
            _escrever_trechos(doc.add_paragraph(), linha.strip())
        i += 1

    if not escreveu_titulo:
        doc.paragraphs[0].insert_paragraph_before(titulo_fallback, style="Title")

    destino.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(destino))
    return destino
