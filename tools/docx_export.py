"""Converte os one-pagers de Markdown para `.docx` com a identidade da Unooria.

Existe porque o time pedagógico não lê Markdown: lê um documento que abre no Word, no
Google Docs ou no LibreOffice — e porque o documento em que a missão é aprovada tem a
cara da Unooria, não a cara do Word. A conversão é determinística e roda sem modelo.

O que ele monta: capa navy com o logotipo, cabeçalho e rodapé com a marca e o número da
página, títulos em azul profundo com régua lavanda, tabelas com cabeçalho navy e linhas
alternadas, citações com barra lavanda — o pedagógico abre com uma —, e links clicáveis,
que são o item que deixa a professora abrir o protótipo antes de aprovar.

A leitura do Markdown fica em `tools.markdown_blocos`; aqui só a aparência. Sem os
arquivos de marca no repositório, o cabeçalho escreve "Unooria" em texto e o documento
sai igual no resto.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from tools import marca
from tools.markdown_blocos import Bloco, Trecho, analisar, formatar, titulo_do_documento


def _elemento(tag: str, **atributos):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    el = OxmlElement(tag)
    for chave, valor in atributos.items():
        el.set(qn(f"w:{chave}"), valor)
    return el


def _sombrear(elemento, cor: str) -> None:
    """Pinta o fundo de um parágrafo ou de uma célula."""
    elemento.append(_elemento("w:shd", val="clear", color="auto", fill=cor))


def _bordas(
    paragrafo, *, esquerda: Optional[str] = None, baixo: Optional[str] = None, espessura: int = 6
) -> None:
    from docx.oxml.ns import qn

    pPr = paragrafo._p.get_or_add_pPr()
    pBdr = _elemento("w:pBdr")
    for lado, cor in (("left", esquerda), ("bottom", baixo)):
        if not cor:
            continue
        pBdr.append(_elemento(f"w:{lado}", val="single", sz=str(espessura), space="4", color=cor))
    if len(pBdr):
        # O `pBdr` tem lugar fixo na ordem do schema: logo depois do sombreamento.
        anterior = pPr.find(qn("w:shd"))
        if anterior is not None:
            anterior.addnext(pBdr)
        else:
            pPr.insert(0, pBdr)


def _campo_de_pagina(paragrafo) -> None:
    """O número da página, como campo — o Word o atualiza sozinho."""
    run = paragrafo.add_run()
    run._r.append(_elemento("w:fldChar", fldCharType="begin"))
    instrucao = _elemento("w:instrText", space="preserve")
    instrucao.text = "PAGE"
    run._r.append(instrucao)
    run._r.append(_elemento("w:fldChar", fldCharType="end"))


def _hyperlink(paragrafo, texto: str, url: str) -> None:
    """Link clicável de verdade: o python-docx não traz isso pronto."""
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor

    rid = paragrafo.part.relate_to(url, RT.HYPERLINK, is_external=True)
    link = _elemento("w:hyperlink")
    link.set(qn("r:id"), rid)
    run = paragrafo.add_run(texto)
    run.font.color.rgb = RGBColor(*marca.rgb(marca.NAVY))
    run.font.underline = True
    run.font.size = Pt(10.5)
    link.append(run._r)
    paragrafo._p.append(link)


def _escrever(paragrafo, trechos: List[Trecho], *, cor: Optional[str] = None, tamanho: float = 10.5) -> None:
    from docx.shared import Pt, RGBColor

    for trecho in trechos:
        if trecho.href:
            _hyperlink(paragrafo, trecho.texto, trecho.href)
            continue
        run = paragrafo.add_run(trecho.texto)
        run.bold = trecho.negrito
        run.italic = trecho.italico
        run.font.size = Pt(tamanho)
        if trecho.mono:
            run.font.name = marca.FONTE_MONO
            run.font.size = Pt(tamanho - 1)
            run.font.color.rgb = RGBColor(*marca.rgb(marca.TEXTO))
        elif cor:
            run.font.color.rgb = RGBColor(*marca.rgb(cor))


def _preparar_documento(doc) -> None:
    """A4, margens do manual, e as fontes da marca no estilo Normal."""
    from docx.shared import Cm, Pt, RGBColor

    for secao in doc.sections:
        secao.page_width, secao.page_height = Cm(21.0), Cm(29.7)
        secao.top_margin, secao.bottom_margin = Cm(2.4), Cm(2.2)
        secao.left_margin, secao.right_margin = Cm(2.4), Cm(2.4)
        secao.header_distance, secao.footer_distance = Cm(1.2), Cm(1.2)

    normal = doc.styles["Normal"]
    normal.font.name = marca.FONTE_CORPO
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor(*marca.rgb(marca.TEXTO))
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.18

    for nome in ("List Bullet", "List Number", "List Bullet 2", "List Number 2"):
        try:
            estilo = doc.styles[nome]
        except KeyError:
            continue
        estilo.font.name = marca.FONTE_CORPO
        estilo.font.size = Pt(10.5)
        estilo.font.color.rgb = RGBColor(*marca.rgb(marca.TEXTO))

    # Os títulos usam os estilos `Heading` do Word, e não formatação solta: é isso que dá
    # painel de navegação no Word e sumário no Google Docs para quem lê um documento de
    # vinte seções. A marca entra redefinindo o estilo, não trocando-o.
    escala = {1: (17, marca.NAVY), 2: (13.5, marca.NAVY), 3: (11.5, marca.NAVY), 4: (10.5, marca.LAVANDA)}
    for nivel, (tamanho, cor) in escala.items():
        estilo = doc.styles[f"Heading {nivel}"]
        estilo.font.name = marca.FONTE_TITULO
        estilo.font.size = Pt(tamanho)
        estilo.font.bold = True
        estilo.font.italic = False
        estilo.font.color.rgb = RGBColor(*marca.rgb(cor))
        estilo.paragraph_format.space_before = Pt(16 if nivel <= 2 else 11)
        estilo.paragraph_format.space_after = Pt(5)
        estilo.paragraph_format.keep_with_next = True


def _cabecalho_e_rodape(doc, etiqueta: str) -> None:
    from docx.enum.text import WD_TAB_ALIGNMENT
    from docx.shared import Cm, Pt, RGBColor

    secao = doc.sections[0]
    secao.different_first_page_header_footer = True  # a capa não leva cabeçalho

    topo = secao.header.paragraphs[0]
    topo.text = ""
    logotipo = marca.arquivo_de_marca(marca.LOGOTIPO_NAVY)
    if logotipo:
        topo.add_run().add_picture(str(logotipo), width=Cm(2.4))
    else:
        nome = topo.add_run("Unooria")
        nome.font.bold = True
        nome.font.color.rgb = RGBColor(*marca.rgb(marca.NAVY))
    legenda = topo.add_run("   ·   " + etiqueta)
    legenda.font.size = Pt(8)
    legenda.font.color.rgb = RGBColor(*marca.rgb(marca.LAVANDA))
    _bordas(topo, baixo=marca.LINHA, espessura=4)

    rodape = secao.footer.paragraphs[0]
    rodape.text = ""
    largura_util = secao.page_width - secao.left_margin - secao.right_margin
    rodape.paragraph_format.tab_stops.add_tab_stop(largura_util, WD_TAB_ALIGNMENT.RIGHT)
    assinatura = rodape.add_run("Unooria · uso interno\t")
    assinatura.font.size = Pt(8)
    assinatura.font.color.rgb = RGBColor(*marca.rgb(marca.LAVANDA))
    _campo_de_pagina(rodape)
    rodape.runs[-1].font.size = Pt(9)
    rodape.runs[-1].font.bold = True
    rodape.runs[-1].font.color.rgb = RGBColor(*marca.rgb(marca.NAVY))


def _capa(doc, titulo: str, etiqueta: str, subtitulo: Optional[str]) -> None:
    """Bloco navy com o logotipo claro, a etiqueta do documento e o nome da missão."""
    from docx.shared import Cm, Pt, RGBColor

    tabela = doc.add_table(rows=1, cols=1)
    celula = tabela.cell(0, 0)
    celula.width = Cm(16.2)
    tcPr = celula._tc.get_or_add_tcPr()
    _sombrear(tcPr, marca.NAVY)
    margens = _elemento("w:tcMar")
    for lado, valor in (("top", "340"), ("bottom", "340"), ("left", "360"), ("right", "360")):
        margens.append(_elemento(f"w:{lado}", w=valor, type="dxa"))
    tcPr.append(margens)

    primeiro = celula.paragraphs[0]
    primeiro.paragraph_format.space_after = Pt(10)
    logotipo = marca.arquivo_de_marca(marca.LOGOTIPO_CLARO)
    if logotipo:
        primeiro.add_run().add_picture(str(logotipo), width=Cm(4.2))
    else:
        run = primeiro.add_run("UNOORIA")
        run.font.bold = True
        run.font.size = Pt(16)
        run.font.color.rgb = RGBColor(*marca.rgb(marca.BRANCO))

    p_etiqueta = celula.add_paragraph()
    p_etiqueta.paragraph_format.space_after = Pt(4)
    run = p_etiqueta.add_run(etiqueta.upper())
    run.font.name = marca.FONTE_TITULO
    run.font.size = Pt(9)
    run.font.bold = True
    run.font.color.rgb = RGBColor(*marca.rgb(marca.AZUL))

    p_titulo = celula.add_paragraph()
    p_titulo.paragraph_format.space_after = Pt(0)
    run = p_titulo.add_run(titulo)
    run.font.name = marca.FONTE_TITULO
    run.font.size = Pt(23)
    run.font.bold = True
    run.font.color.rgb = RGBColor(*marca.rgb(marca.BRANCO))

    if subtitulo:
        p_sub = celula.add_paragraph()
        p_sub.paragraph_format.space_before = Pt(8)
        run = p_sub.add_run(subtitulo)
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(*marca.rgb(marca.LAVANDA))

    respiro = doc.add_paragraph()
    respiro.paragraph_format.space_after = Pt(2)


def _titulo(doc, bloco: Bloco) -> None:
    """Título com o estilo `Heading` do nível, mais a régua da marca embaixo."""
    nivel = min(bloco.nivel, 4)
    paragrafo = doc.add_paragraph(style=f"Heading {nivel}")
    # Sem cor nem tamanho no run: quem manda é o estilo, e é ele que o Word usa para
    # montar a navegação. O run só carrega o que veio do Markdown.
    for trecho in bloco.trechos:
        run = paragrafo.add_run(trecho.texto)
        run.italic = trecho.italico
        if trecho.mono:
            run.font.name = marca.FONTE_MONO
    if nivel == 1:
        _bordas(paragrafo, baixo=marca.LAVANDA, espessura=8)
    elif nivel == 2:
        _bordas(paragrafo, baixo=marca.LINHA, espessura=4)


def _citacao(doc, bloco: Bloco) -> None:
    """O que se pede a quem lê, destacado com a barra lavanda da marca."""
    from docx.shared import Cm, Pt

    paragrafo = doc.add_paragraph()
    paragrafo.paragraph_format.left_indent = Cm(0.5)
    paragrafo.paragraph_format.space_before = Pt(6)
    paragrafo.paragraph_format.space_after = Pt(6)
    _sombrear(paragrafo._p.get_or_add_pPr(), marca.PAPEL)
    _bordas(paragrafo, esquerda=marca.LAVANDA, espessura=18)
    _escrever(paragrafo, bloco.trechos)


def _tabela(doc, bloco: Bloco) -> None:
    from docx.shared import Pt, RGBColor

    colunas = max(len(linha) for linha in bloco.linhas)
    tabela = doc.add_table(rows=len(bloco.linhas), cols=colunas)
    bordas = _elemento("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        bordas.append(_elemento(f"w:{lado}", val="single", sz="4", space="0", color=marca.LINHA))
    tabela._tbl.tblPr.append(bordas)

    for r, celulas in enumerate(bloco.linhas):
        for c in range(colunas):
            celula = tabela.cell(r, c)
            celula.text = ""
            paragrafo = celula.paragraphs[0]
            paragrafo.paragraph_format.space_after = Pt(2)
            valor = celulas[c] if c < len(celulas) else ""
            if r == 0:
                _sombrear(celula._tc.get_or_add_tcPr(), marca.NAVY)
                _escrever(paragrafo, formatar(valor), tamanho=9.5)
                for run in paragrafo.runs:
                    run.bold = True
                    run.font.name = marca.FONTE_TITULO
                    run.font.color.rgb = RGBColor(*marca.rgb(marca.BRANCO))
            else:
                if r % 2 == 0:
                    _sombrear(celula._tc.get_or_add_tcPr(), marca.PAPEL)
                _escrever(paragrafo, formatar(valor), tamanho=9.5)
    doc.add_paragraph()


def _codigo(doc, bloco: Bloco) -> None:
    from docx.shared import Cm, Pt, RGBColor

    paragrafo = doc.add_paragraph()
    paragrafo.paragraph_format.left_indent = Cm(0.4)
    _sombrear(paragrafo._p.get_or_add_pPr(), marca.PAPEL)
    run = paragrafo.add_run(bloco.texto)
    run.font.name = marca.FONTE_MONO
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(*marca.rgb(marca.TEXTO))


def markdown_para_docx(
    markdown: str,
    destino: Path,
    titulo_fallback: str = "Documento",
    etiqueta: str = "One-pager",
    subtitulo: Optional[str] = None,
) -> Optional[Path]:
    """Escreve o `.docx` e devolve o caminho. ``None`` se a biblioteca não estiver instalada."""
    try:
        from docx import Document
        from docx.shared import Pt
    except ImportError:  # pragma: no cover - dependência declarada em requirements
        return None

    blocos = analisar(markdown or "")
    titulo = titulo_do_documento(blocos) or titulo_fallback
    if blocos and blocos[0].tipo == "titulo" and blocos[0].nivel == 1:
        blocos = blocos[1:]  # o título já é a capa; repeti-lo no corpo é ruído

    doc = Document()
    _preparar_documento(doc)
    _cabecalho_e_rodape(doc, etiqueta)
    _capa(doc, titulo, etiqueta, subtitulo)

    for bloco in blocos:
        if bloco.tipo == "titulo":
            _titulo(doc, bloco)
        elif bloco.tipo == "tabela":
            _tabela(doc, bloco)
        elif bloco.tipo == "citacao":
            _citacao(doc, bloco)
        elif bloco.tipo == "codigo":
            _codigo(doc, bloco)
        elif bloco.tipo == "item":
            base = "List Number" if bloco.ordenada else "List Bullet"
            estilo = base if bloco.nivel == 0 else f"{base} {min(bloco.nivel + 1, 3)}"
            try:
                paragrafo = doc.add_paragraph(style=estilo)
            except KeyError:
                paragrafo = doc.add_paragraph(style=base)
            paragrafo.paragraph_format.space_after = Pt(3)
            _escrever(paragrafo, bloco.trechos)
        elif bloco.tipo == "divisoria":
            regua = doc.add_paragraph()
            regua.paragraph_format.space_after = Pt(4)
            _bordas(regua, baixo=marca.LINHA, espessura=4)
        elif bloco.trechos:
            _escrever(doc.add_paragraph(), bloco.trechos)

    destino.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(destino))
    return destino
