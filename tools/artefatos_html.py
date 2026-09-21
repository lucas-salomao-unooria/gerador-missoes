"""Artefatos HTML da esteira: o protótipo navegável e a folha de diagramas.

Dois arquivos que a revisão humana abre no navegador e que o agente de codificação lê
como referência — sem Figma, sem conta, sem rede:

- ``extrair_prototipo``: separa o HTML que o D8 escreveu do relatório que vem junto.
- ``montar_folha_de_diagramas``: monta, sem LLM, uma página com os diagramas Mermaid
  que a jornada e o fluxo já produziram. O Mermaid vem de CDN; sem rede, a página
  mostra o código-fonte do diagrama, que continua legível.
"""

from __future__ import annotations

import html
import re
from typing import List, Optional, Tuple

_BLOCO_HTML = re.compile(r"```html\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
_BLOCO_MERMAID = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
_DOCTYPE = re.compile(r"<!doctype html", re.IGNORECASE)


def extrair_prototipo(saida: str) -> Tuple[Optional[str], str]:
    """Devolve ``(html, relatorio)`` a partir da saída do D8.

    O agente entrega o HTML num bloco cercado e o relatório depois. Quando ele
    esquece a cerca mas escreve um documento inteiro, o `<!doctype html>` salva.
    """
    if not saida or not isinstance(saida, str):
        return None, saida or ""

    m = _BLOCO_HTML.search(saida)
    if m:
        documento = m.group(1).strip()
        relatorio = (saida[: m.start()] + saida[m.end() :]).strip()
        return (documento, relatorio) if _DOCTYPE.search(documento) or "<html" in documento.lower() else (None, saida)

    m = _DOCTYPE.search(saida)
    if m:
        fim = saida.lower().rfind("</html>")
        if fim > m.start():
            fim += len("</html>")
            return saida[m.start() : fim].strip(), (saida[: m.start()] + saida[fim:]).strip()
    return None, saida


def extrair_mermaid(texto: Optional[str]) -> List[str]:
    """Blocos Mermaid de um documento, na ordem em que aparecem."""
    if not texto or not isinstance(texto, str):
        return []
    return [b.strip() for b in _BLOCO_MERMAID.findall(texto) if b.strip()]


_TITULO_MD = re.compile(r"^#{1,4}\s+(.+?)\s*$", re.MULTILINE)


def extrair_mermaid_com_titulos(texto: Optional[str]) -> List[Tuple[str, str]]:
    """Blocos Mermaid com o título do heading mais próximo acima de cada um.

    O documento de fluxo passou a ter dois grafos — o do estudante e o do professor — e
    tanto a folha de diagramas quanto o espelho no Miro precisam nomeá-los pelo que são,
    não por "Fluxo · 2". O heading imediatamente acima do bloco é o nome; sem heading, vazio.
    """
    if not texto or not isinstance(texto, str):
        return []
    saida: List[Tuple[str, str]] = []
    for m in _BLOCO_MERMAID.finditer(texto):
        bloco = m.group(1).strip()
        if not bloco:
            continue
        titulos = _TITULO_MD.findall(texto[: m.start()])
        titulo = titulos[-1].strip() if titulos else ""
        saida.append((re.sub(r"\s*\(.*?\)\s*$", "", titulo).strip(), bloco))
    return saida


def e_diagrama_do_professor(titulo: str) -> bool:
    return bool(re.search(r"professor|docente", titulo or "", re.IGNORECASE))


_PAGINA = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{titulo} — diagramas</title>
<style>
  :root {{
    color-scheme: light;
    --fundo: #f6f7f9; --superficie: #fff; --borda: #d8dce1;
    --texto: #1a1d21; --secundario: #5b6570; --acento: #2f4f7f;
  }}
  * {{ box-sizing: border-box; min-width: 0; }}
  body {{
    margin: 0; padding: 32px 24px 64px; background: var(--fundo); color: var(--texto);
    font: 15px/1.55 system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    overflow-x: hidden;
  }}
  header {{ max-width: 1100px; margin: 0 auto 28px; }}
  h1 {{ font-size: 22px; margin: 0 0 6px; }}
  header p {{ margin: 0; color: var(--secundario); font-size: 13.5px; }}
  section {{
    max-width: 1100px; margin: 0 auto 24px; background: var(--superficie);
    border: 1px solid var(--borda); border-radius: 10px; overflow: hidden;
  }}
  h2 {{
    font-size: 14px; margin: 0; padding: 12px 18px; color: var(--acento);
    border-bottom: 1px solid var(--borda); background: #fbfcfd;
    letter-spacing: .02em; text-transform: uppercase;
  }}
  .palco {{ padding: 20px 18px; overflow-x: auto; }}
  .mermaid {{ font-size: 14px; }}
  .erro {{ margin: 0; color: #a3232b; font-size: 13.5px; }}
  details {{ border-top: 1px dashed var(--borda); }}
  summary {{ padding: 10px 18px; cursor: pointer; color: var(--secundario); font-size: 13px; }}
  pre {{
    margin: 0; padding: 0 18px 18px; white-space: pre-wrap; word-break: break-word;
    font: 12.5px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--secundario);
  }}
  footer {{ max-width: 1100px; margin: 32px auto 0; color: var(--secundario); font-size: 12.5px; }}
</style>
</head>
<body>
<header>
  <h1>{titulo}</h1>
  <p>Jornada e fluxo gerados pela esteira. Sem rede, o desenho não renderiza e o código do diagrama fica visível abaixo de cada bloco.</p>
</header>
{secoes}
<footer>Gerado pelo Gerador de Missões Unooria a partir dos documentos de design desta execução.</footer>
<script type="module">
  // Versão exata, não a tag flutuante `@11`: a página fica gravada em disco e busca a CDN a
  // cada abertura, então um major novo quebraria execuções antigas retroativamente.
  const abrir = (secao, motivo) => {{
    const det = secao.querySelector("details");
    if (det) det.open = true;
    const palco = secao.querySelector(".palco");
    if (palco) palco.innerHTML = '<p class="erro">Não foi possível desenhar este diagrama: '
      + String(motivo).replace(/[<&]/g, c => c === "<" ? "&lt;" : "&amp;")
      + "</p>";
  }};
  try {{
    const {{ default: mermaid }} = await import("https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs");
    mermaid.initialize({{ startOnLoad: false, theme: "neutral", securityLevel: "strict" }});
    // Um nó por vez: com `startOnLoad`, um diagrama de sintaxe inválida derrubava a renderização
    // de todos os outros, e a página inteira aparecia vazia sem dizer qual deles falhou.
    for (const no of document.querySelectorAll("pre.mermaid")) {{
      try {{
        await mermaid.run({{ nodes: [no] }});
      }} catch (e) {{
        abrir(no.closest("section"), e && e.message ? e.message : e);
      }}
    }}
  }} catch (e) {{
    // Sem rede: nenhum diagrama desenha, mas o código-fonte de cada um continua legível.
    for (const el of document.querySelectorAll("details")) el.open = true;
  }}
</script>
</body>
</html>
"""


def montar_folha_de_diagramas(titulo: str, jornada: Optional[str], fluxo: Optional[str]) -> Optional[str]:
    """Página única com os diagramas da jornada e do fluxo. ``None`` se não houver nenhum."""
    blocos: List[Tuple[str, str]] = []
    for rotulo, texto in (("Jornada", jornada), ("Fluxo de telas", fluxo)):
        diagramas = extrair_mermaid_com_titulos(texto)
        for i, (titulo_bloco, d) in enumerate(diagramas, 1):
            if len(diagramas) == 1:
                nome = rotulo
            elif e_diagrama_do_professor(titulo_bloco):
                nome = "Fluxo do professor" if rotulo.startswith("Fluxo") else "Jornada do professor"
            else:
                nome = titulo_bloco or f"{rotulo} · {i}"
            blocos.append((nome, d))
    if not blocos:
        return None

    secoes = []
    for nome, codigo in blocos:
        seguro = html.escape(codigo)
        secoes.append(
            f'<section>\n  <h2>{html.escape(nome)}</h2>\n'
            f'  <div class="palco"><pre class="mermaid">{seguro}</pre></div>\n'
            f'  <details><summary>Código do diagrama</summary><pre>{seguro}</pre></details>\n'
            f"</section>"
        )
    return _PAGINA.format(titulo=html.escape(titulo or "Missão"), secoes="\n".join(secoes))
