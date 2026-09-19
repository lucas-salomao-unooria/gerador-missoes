"""A identidade visual da Unooria em um lugar só.

Os documentos que saem da esteira para gente — o one-pager de produto e o one-pager
pedagógico — não são rascunhos: o time pedagógico aprova a missão neles e a PM os
encaminha. Por isso eles saem com a marca, e a marca mora aqui: paleta, tipografia e
logotipos, lidos por quem escreve o `.docx` e por quem escreve o `.html`.

A fonte da verdade é o brandbook (abril/2026), o mesmo que o manual em LaTeX usa:
``#0e1039`` azul profundo (estrutura) · ``#8b85ac`` lavanda (inteligência) ·
``#7fa5e2`` azul claro (interface). Os neutros são tintas dessa paleta, não cores
novas; e as três cores de sinal existem só para reproduzir 🟢 🟡 🔴 dos relatórios.

A fonte institucional é a Garet. Nos documentos gerados usamos Montserrat (geométrica,
mesma família de desenho) nos títulos e Source Sans 3 no corpo, porque são as que o
Google Docs — onde o time abre o `.docx` — tem nativamente. Sem elas, o leitor cai no
fallback declarado e o documento continua legível.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional, Tuple

# ------------------------------------------------------------------ PALETA ---
NAVY = "0E1039"      # azul profundo — estrutura
LAVANDA = "8B85AC"   # lavanda — inteligência
AZUL = "7FA5E2"      # azul claro — interface
BRANCO = "FFFFFF"
# neutros derivados
PAPEL = "F5F5FA"
LINHA = "D9D7E4"
TEXTO = "2B2D45"
# sinalização (🟢 🟡 🔴) — funcionais, não são cores de marca
SINAL_VERDE = "2E6F5E"
SINAL_AMBAR = "B07A22"
SINAL_VERMELHO = "A33B33"

# -------------------------------------------------------------- TIPOGRAFIA ---
FONTE_TITULO = "Montserrat"
FONTE_CORPO = "Source Sans 3"
FONTE_MONO = "Source Code Pro"
# Pilha de fallback para o HTML: sem rede, o navegador usa a fonte do sistema.
PILHA_TITULO = f"'{FONTE_TITULO}', 'Avenir Next', Avenir, system-ui, -apple-system, 'Segoe UI', sans-serif"
PILHA_CORPO = f"'{FONTE_CORPO}', 'Source Sans Pro', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
PILHA_MONO = f"'{FONTE_MONO}', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
GOOGLE_FONTS = (
    "https://fonts.googleapis.com/css2"
    "?family=Montserrat:wght@400;600;700&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&display=swap"
)

# ------------------------------------------------------------------ MARCA ----
# `images/marca/` é a cópia que vai no contêiner; `manual-unooria/marca/` é a pasta do
# manual, que pode não estar presente numa cópia enxuta do repositório.
_RAIZ = Path(__file__).resolve().parent.parent
_PASTAS = (_RAIZ / "images" / "marca", _RAIZ / "manual-unooria" / "marca")

LOGOTIPO_NAVY = "logotipo-navy.png"        # sobre fundo claro
LOGOTIPO_CLARO = "logotipo-claro.png"      # sobre fundo navy
LOGOTIPO_LAVANDA = "logotipo-lavanda.png"
SIMBOLO_GRAFISMO = "simbolo-grafismo.png"  # o símbolo como grafismo de fundo
SIMBOLO_LAVANDA = "simbolo-lavanda.png"


def arquivo_de_marca(nome: str) -> Optional[Path]:
    """Caminho do asset da marca, ou ``None`` quando ele não veio nesta cópia do repo.

    Nenhum documento depende de ter a imagem: sem ela o cabeçalho escreve "Unooria" em
    texto, que é a falha certa — perde-se o logotipo, não o documento.
    """
    for pasta in _PASTAS:
        caminho = pasta / nome
        if caminho.is_file():
            return caminho
    return None


def marca_em_base64(nome: str) -> Optional[str]:
    """O asset como ``data:`` URI, para o HTML abrir sozinho depois de baixado."""
    caminho = arquivo_de_marca(nome)
    if not caminho:
        return None
    try:
        dados = base64.b64encode(caminho.read_bytes()).decode("ascii")
    except OSError:
        return None
    return f"data:image/png;base64,{dados}"


def rgb(hexa: str) -> Tuple[int, int, int]:
    """``"0E1039"`` → ``(14, 16, 57)``, que é o que o python-docx pede."""
    return tuple(int(hexa[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
