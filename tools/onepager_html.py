"""Os one-pagers como página única com a identidade da Unooria, pronta para virar PDF.

O `.docx` é para quem edita; esta página é para quem apresenta. Ela abre no navegador
sem instalar nada e sai em PDF pelo "Imprimir → Salvar como PDF", com capa, cores e
tipografia da marca — sem depender de LaTeX nem de conversor no servidor.

O arquivo é autossuficiente: o logotipo e o grafismo vão embutidos em base64 e o CSS é
inline, então ele continua inteiro depois de baixado, anexado num e-mail ou aberto sem
rede. As fontes vêm do Google Fonts quando há rede; sem ela, cai no fallback do sistema
e só o desenho da letra muda.
"""

from __future__ import annotations

import html
from typing import List, Optional

from tools import marca
from tools.markdown_blocos import Bloco, Trecho, analisar, formatar, titulo_do_documento


def _trechos_html(trechos: List[Trecho]) -> str:
    saida = []
    for trecho in trechos:
        texto = html.escape(trecho.texto)
        if trecho.href:
            saida.append(f'<a href="{html.escape(trecho.href, quote=True)}">{texto}</a>')
            continue
        if trecho.mono:
            texto = f"<code>{texto}</code>"
        if trecho.negrito:
            texto = f"<strong>{texto}</strong>"
        if trecho.italico:
            texto = f"<em>{texto}</em>"
        saida.append(texto)
    return "".join(saida)


def _corpo(blocos: List[Bloco]) -> str:
    """Blocos → HTML, agrupando itens consecutivos numa lista só."""
    partes: List[str] = []
    lista_aberta: Optional[str] = None

    def fechar_lista() -> None:
        nonlocal lista_aberta
        if lista_aberta:
            partes.append(f"</{lista_aberta}>")
            lista_aberta = None

    for bloco in blocos:
        if bloco.tipo == "item":
            etiqueta = "ol" if bloco.ordenada else "ul"
            if lista_aberta != etiqueta:
                fechar_lista()
                partes.append(f"<{etiqueta}>")
                lista_aberta = etiqueta
            recuo = ' class="recuo"' if bloco.nivel else ""
            partes.append(f"<li{recuo}>{_trechos_html(bloco.trechos)}</li>")
            continue

        fechar_lista()
        if bloco.tipo == "titulo":
            nivel = min(bloco.nivel, 4)
            partes.append(f"<h{nivel}>{_trechos_html(bloco.trechos)}</h{nivel}>")
        elif bloco.tipo == "citacao":
            partes.append(f"<blockquote>{_trechos_html(bloco.trechos)}</blockquote>")
        elif bloco.tipo == "codigo":
            partes.append(f"<pre>{html.escape(bloco.texto)}</pre>")
        elif bloco.tipo == "divisoria":
            partes.append("<hr />")
        elif bloco.tipo == "tabela" and bloco.linhas:
            cabecalho, *resto = bloco.linhas
            colunas = max(len(linha) for linha in bloco.linhas)

            def celulas(valores: List[str], tag: str, _colunas: int = colunas) -> str:
                preenchidas = list(valores) + [""] * (_colunas - len(valores))
                return "".join(f"<{tag}>{_trechos_html(formatar(v))}</{tag}>" for v in preenchidas)

            corpo = "".join(f"<tr>{celulas(linha, 'td')}</tr>" for linha in resto)
            partes.append(
                '<div class="tabela"><table><thead><tr>'
                f"{celulas(cabecalho, 'th')}</tr></thead><tbody>{corpo}</tbody></table></div>"
            )
        elif bloco.trechos:
            partes.append(f"<p>{_trechos_html(bloco.trechos)}</p>")

    fechar_lista()
    return "\n".join(partes)


_PAGINA = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{titulo} — {etiqueta}</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link rel="stylesheet" href="{fontes}" />
<style>
  :root {{
    color-scheme: light;
    --navy: #{navy}; --lavanda: #{lavanda}; --azul: #{azul};
    --papel: #{papel}; --linha: #{linha}; --texto: #{texto};
    --titulo: {pilha_titulo};
    --corpo: {pilha_corpo};
    --mono: {pilha_mono};
  }}
  * {{ box-sizing: border-box; min-width: 0; }}
  body {{
    margin: 0; background: var(--papel); color: var(--texto);
    font: 16px/1.6 var(--corpo); -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }}
  .folha {{ max-width: 860px; margin: 0 auto; background: #fff; box-shadow: 0 1px 3px rgba(14,16,57,.08); }}
  /* -------------------------------------------------------------- capa --- */
  .capa {{
    position: relative; overflow: hidden; background: var(--navy); color: #fff;
    padding: 48px 56px 44px;
  }}
  .capa .grafismo {{
    position: absolute; right: -60px; bottom: -70px; width: 320px; opacity: .16;
    pointer-events: none;
  }}
  .capa img.logotipo {{ width: 190px; display: block; margin-bottom: 30px; position: relative; }}
  .capa .marca-texto {{
    font: 700 20px/1 var(--titulo); letter-spacing: .14em; display: block; margin-bottom: 30px;
  }}
  .capa .etiqueta {{
    font: 700 12px/1 var(--titulo); letter-spacing: .16em; text-transform: uppercase;
    color: var(--azul); position: relative;
  }}
  /* A cor vem depois das regras de título do conteúdo, senão o nome da missão sai
     navy sobre navy — invisível — e ainda herda a régua lavanda de `h1`. */
  .capa h1.nome {{
    font: 700 38px/1.15 var(--titulo); margin: 12px 0 0; position: relative;
    color: #fff; border: 0; padding: 0;
  }}
  .capa .subtitulo {{ margin: 14px 0 0; color: var(--lavanda); font-size: 15px; position: relative; }}
  /* ------------------------------------------------------------ conteúdo --- */
  .conteudo {{ padding: 40px 56px 56px; }}
  .conteudo h1, .conteudo h2, .conteudo h3, .conteudo h4 {{
    font-family: var(--titulo); color: var(--navy); line-height: 1.25;
  }}
  .conteudo h1 {{ font-size: 26px; margin: 34px 0 12px; padding-bottom: 8px; border-bottom: 2px solid var(--lavanda); }}
  .conteudo h2 {{ font-size: 20px; margin: 32px 0 10px; padding-bottom: 6px; border-bottom: 1px solid var(--linha); }}
  .conteudo h3 {{ font-size: 16px; margin: 24px 0 8px; }}
  .conteudo h4 {{ font-size: 14px; margin: 20px 0 6px; color: var(--lavanda); text-transform: uppercase; letter-spacing: .06em; }}
  .conteudo > :first-child {{ margin-top: 0; }}
  p {{ margin: 0 0 12px; }}
  ul, ol {{ margin: 0 0 14px; padding-left: 22px; }}
  li {{ margin: 0 0 6px; }}
  li.recuo {{ margin-left: 18px; }}
  a {{ color: var(--navy); text-decoration: underline; text-underline-offset: 2px; }}
  a:hover {{ color: var(--lavanda); }}
  strong {{ color: var(--navy); }}
  code {{ font: 13.5px/1.4 var(--mono); background: var(--papel); border: 1px solid var(--linha);
          border-radius: 3px; padding: 1px 4px; }}
  pre {{ font: 13px/1.5 var(--mono); background: var(--papel); border-left: 3px solid var(--lavanda);
         padding: 14px 16px; overflow-x: auto; white-space: pre-wrap; word-break: break-word; }}
  blockquote {{
    margin: 16px 0; padding: 14px 18px; background: var(--papel);
    border-left: 4px solid var(--lavanda); border-radius: 0 6px 6px 0;
  }}
  blockquote p {{ margin: 0; }}
  hr {{ border: 0; border-top: 1px solid var(--linha); margin: 26px 0; }}
  .tabela {{ overflow-x: auto; margin: 0 0 18px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 14.5px; }}
  th {{
    background: var(--navy); color: #fff; font-family: var(--titulo); font-size: 13px;
    text-align: left; padding: 9px 12px; border: 1px solid var(--navy);
  }}
  td {{ padding: 9px 12px; border: 1px solid var(--linha); vertical-align: top; }}
  tbody tr:nth-child(even) {{ background: var(--papel); }}
  th code, td code {{ font-size: 12.5px; }}
  /* ------------------------------------------------------------- rodapé --- */
  .rodape {{
    padding: 18px 56px 28px; color: var(--lavanda); font-size: 12.5px;
    border-top: 1px solid var(--linha); display: flex; justify-content: space-between; gap: 16px;
  }}
  /* ----------------------------------------------------------- impressão --- */
  @page {{ size: A4; margin: 14mm; }}
  @media print {{
    body {{ background: #fff; }}
    .folha {{ max-width: none; box-shadow: none; }}
    .capa {{ padding: 38px 30px; }}
    .conteudo {{ padding: 26px 30px 0; }}
    .rodape {{ padding: 16px 30px 0; }}
    h1, h2, h3, h4 {{ break-after: avoid; }}
    table, blockquote, pre, li {{ break-inside: avoid; }}
  }}
  @media (max-width: 640px) {{
    .capa {{ padding: 32px 20px; }}
    .capa h1.nome {{ font-size: 28px; }}
    .conteudo {{ padding: 26px 20px 36px; }}
    .rodape {{ padding: 16px 20px 24px; flex-direction: column; }}
  }}
</style>
</head>
<body>
<article class="folha">
  <header class="capa">
    {grafismo}
    {logotipo}
    <span class="etiqueta">{etiqueta}</span>
    <h1 class="nome">{titulo}</h1>
    {subtitulo}
  </header>
  <main class="conteudo">
{corpo}
  </main>
  <footer class="rodape">
    <span>Unooria · uso interno</span>
    <span>Gerado pelo Gerador de Missões</span>
  </footer>
</article>
</body>
</html>
"""


def markdown_para_html(
    markdown: str,
    titulo_fallback: str = "Missão",
    etiqueta: str = "One-pager",
    subtitulo: Optional[str] = None,
) -> str:
    """Devolve a página completa, pronta para gravar em disco."""
    blocos = analisar(markdown or "")
    titulo = titulo_do_documento(blocos) or titulo_fallback
    if blocos and blocos[0].tipo == "titulo" and blocos[0].nivel == 1:
        blocos = blocos[1:]  # o nome da missão já está na capa

    logotipo_uri = marca.marca_em_base64(marca.LOGOTIPO_CLARO)
    grafismo_uri = marca.marca_em_base64(marca.SIMBOLO_GRAFISMO)

    return _PAGINA.format(
        titulo=html.escape(titulo),
        etiqueta=html.escape(etiqueta),
        subtitulo=f'<p class="subtitulo">{html.escape(subtitulo)}</p>' if subtitulo else "",
        logotipo=(
            f'<img class="logotipo" alt="Unooria" src="{logotipo_uri}" />'
            if logotipo_uri
            else '<span class="marca-texto">UNOORIA</span>'
        ),
        grafismo=f'<img class="grafismo" alt="" src="{grafismo_uri}" />' if grafismo_uri else "",
        corpo=_corpo(blocos),
        fontes=marca.GOOGLE_FONTS,
        navy=marca.NAVY,
        lavanda=marca.LAVANDA,
        azul=marca.AZUL,
        papel=marca.PAPEL,
        linha=marca.LINHA,
        texto=marca.TEXTO,
        pilha_titulo=marca.PILHA_TITULO,
        pilha_corpo=marca.PILHA_CORPO,
        pilha_mono=marca.PILHA_MONO,
    )
