"""O que o autor anterior escreveu continua no documento que o próximo agente reescreve?

Quatro agentes de design recebem um documento e devolvem a versão inteira dele: o D0 e o D9 reemitem a
spec com o que acrescentam, e a revisão da copy (passada 2) reemite a passada 1. Nada conferia o que
saiu contra o que entrou — só o tamanho (≥ 80%). A auditoria de 07/10/2026 achou: o D0 da exp04ef1b
apagou sete linhas da spec do Gate 0 (o rótulo do caminho curto, um parâmetro homologado, a retenção,
um `[ABERTO]`); o da exp06ef1b apagou a pergunta 3 do debate; a passada 2 da copy descartou as seções
de prompts e do banco curado nas quatro sessões auditadas.

Aqui a conferência é de fato: cada linha com conteúdo do documento anterior está no novo — igual, ou
com pelo menos 85% dos seus trigramas de palavra (o D0 acrescenta "— Resolvido em [D0-n]" ao fim da
linha que fecha). Linha com marcador de lacuna fica de fora: o D0 existe para reescrevê-la.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Set

MIN_PALAVRAS = 6
FRACAO = 0.85
#: Linha que o próximo agente tem o dever de reescrever: a lacuna que ele fecha.
_RE_MARCADOR = re.compile(r"\[(?:ABERTO|LACUNA|NEEDS|PAR[ÂA]METRO|PROPOSTA|DECIS[ÃA]O PENDENTE|PENDÊNCIA|PENDENCIA)|🔵|\[\[",
                          re.IGNORECASE)
#: Linha que descreve Canal B, Etapa 6 / Refletir ou podcast para o estudante: removê-la é cumprir o contrato atual.
_RE_REMOVIDO_PELO_CONTRATO = re.compile(
    r"\bcanal\s*b\b|\bmultipla_escolha\b|\betapa\s*6\b|\brefletir\b|\bE6[-_]\w+|\bmomento\s+6\.\d",
    re.IGNORECASE,
)
_RE_SEPARADOR = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")
_RE_TITULO = re.compile(r"^(#{2,4})\s+(.+?)\s*$", re.M)


def _norm(texto: str) -> str:
    sem = "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")
    sem = re.sub(r"[`*_|>#]+", " ", sem)
    return re.sub(r"\s+", " ", sem).strip()


def _trigramas(texto: str) -> Set[tuple]:
    p = re.findall(r"\w+", texto)
    return {tuple(p[i:i + 3]) for i in range(len(p) - 2)}


def linhas_perdidas(antes: str, depois: str) -> List[str]:
    """Linhas do documento anterior que não estão no novo (nem quase iguais)."""
    novo = _norm(depois)
    tri_novo = _trigramas(novo)
    perdidas: List[str] = []
    for linha in (antes or "").splitlines():
        if _RE_SEPARADOR.match(linha) or _RE_MARCADOR.search(linha) or _RE_REMOVIDO_PELO_CONTRATO.search(linha):
            continue
        n = _norm(linha)
        if len(n.split()) < MIN_PALAVRAS or n in novo:
            continue
        tri = _trigramas(n)
        if tri and len(tri & tri_novo) / len(tri) >= FRACAO:
            continue
        perdidas.append(linha.strip())
    return perdidas


#: Seções da copy que a revisão (passada 2) deve reemitir sem mudança, e que descartou em 8 de 8
#: sessões do bucket: o PRD lê só a revisada, e o que ela não traz deixa de existir para a esteira.
TEMAS_DA_COPY = (
    ("prompts e schemas", re.compile(r"prompt|schema")),
    ("banco curado", re.compile(r"\bbanco\b")),
    ("roteiro do podcast", re.compile(r"podcast")),
)


def _secoes(texto: str) -> List[Dict[str, object]]:
    """Títulos `##`–`####` com nível, posição e o corpo até o próximo título de nível igual ou maior."""
    titulos = [(m.start(), len(m.group(1)), m.group(2)) for m in _RE_TITULO.finditer(texto or "")]
    saida = []
    for i, (ini, nivel, titulo) in enumerate(titulos):
        fim = next((p for p, n, _ in titulos[i + 1:] if n <= nivel), len(texto))
        saida.append({"inicio": ini, "fim": fim, "nivel": nivel, "titulo": titulo, "texto": texto[ini:fim].rstrip()})
    return saida


def reanexar_secoes(antes: str, depois: str) -> Dict[str, object]:
    """A copy revisada com as seções temáticas da passada 1 que ela não trouxe, copiadas sem mudança.

    Devolve `{texto, reanexadas: [tema]}`. Tema que a revisão trouxe (com qualquer título) não é tocado.
    """
    titulos_depois = [_norm(s["titulo"]) for s in _secoes(depois)]
    blocos: List[str] = []
    reanexadas: List[str] = []
    for tema, rx in TEMAS_DA_COPY:
        if any(rx.search(t) for t in titulos_depois):
            continue
        capturadas = []
        for s in _secoes(antes):
            if rx.search(_norm(str(s["titulo"]))) and not any(c["inicio"] <= s["inicio"] < c["fim"] for c in capturadas):
                capturadas.append(s)
        if capturadas:
            reanexadas.append(tema)
            blocos += [str(c["texto"]) for c in capturadas]
    if not blocos:
        return {"texto": depois, "reanexadas": []}
    nota = ("\n\n---\n\n## Da passada 1, sem mudança (reanexado pela esteira)\n\n"
            "> A revisão não reemitiu estas seções; a esteira as copiou da passada 1, palavra por palavra, para que "
            "o banco de conteúdo, o brief e o PRD as recebam.\n\n")
    return {"texto": (depois or "").rstrip() + nota + "\n\n".join(blocos) + "\n", "reanexadas": reanexadas}
