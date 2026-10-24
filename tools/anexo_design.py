"""A spec de produto e o anexo de design: dois documentos, dois donos. Determinístico, sem LLM.

PR 6 do plano «Produto dono do contrato» (docs/planos/2026-10-23-produto-dono-do-contrato.md), decisões D2 e D10. Até
aqui a `spec_missao` tinha dois autores sob um nome só: o A045 escrevia a spec em produto, e o D0 e o D9 (A066/A068)
a reescreviam no design com os blocos 13 e 14 e publicavam tudo como `produto/05-spec-missao.md`. O refazer de design
voltava a spec à do Gate 0 (`pipeline/reexecucao.py`), e o bloco 13 sumiu em 60cfa7f4 e 4fd72a9a.

Agora:

- `spec_missao` é a spec de produto: os blocos 0–12, o glossário e o bloco 15 (completude de produto, passo 045b),
  igual à que o PO aprova no de acordo. O design não a escreve;
- `anexo_design_spec` é o anexo de design: o bloco 13 (decisões D0-UX) e o bloco 14 (ficha do ambiente, D9), montados
  em código pelos splits do D0 e do D9 e gravados em `design/00-anexo-design-spec.md`;
- quem lê a missão inteira (design, dev, PRD, montagem, rastro) lê a spec de produto mais o anexo — `spec_consolidada`.

A sessão anterior ao PR 6 traz os blocos 13 e 14 dentro da `spec_missao`, sem anexo: `spec_consolidada` a devolve como
está (compatibilidade de leitura), e `spec_de_produto_legada` a devolve à de produto quando o design é refeito.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

#: Chave do anexo de design no estado e o arquivo dele na sessão.
KEY_ANEXO = "anexo_design_spec"
ARQUIVO_ANEXO = "design/00-anexo-design-spec.md"
#: Os blocos do anexo, na ordem: 13 é do D0 (UI/UX), 14 é do D9 (ambiente).
BLOCOS_DO_ANEXO = ("13", "14")
#: O bloco da spec de produto que o passo de completude (prompt 046) escreve.
BLOCO_DA_COMPLETUDE = "15"
TITULO_ANEXO = "# Anexo de design da spec"

_RE_TITULO_BLOCO = re.compile(r"^##\s*\**\s*(\d{1,2})\b.*$", re.MULTILINE)


def _bloco(texto: str, numero: str) -> str:
    """O bloco `## <numero>` do texto — do título ao próximo `## ` ou ao fim; "" sem ele."""
    for m in _RE_TITULO_BLOCO.finditer(texto or ""):
        if m.group(1) == numero:
            fim = re.search(r"^## ", texto[m.end():], re.MULTILINE)
            return texto[m.start(): m.end() + fim.start() if fim else len(texto)].rstrip() + "\n"
    return ""


def blocos_do_anexo(texto: str) -> str:
    """Os blocos 13 e 14 do texto, nessa ordem, sem o que houver em volta (o cabeçalho do anexo, a spec de produto)."""
    return "\n".join(b for b in (_bloco(texto, n) for n in BLOCOS_DO_ANEXO) if b.strip())


def tem_blocos_do_design(spec: str) -> bool:
    """A spec traz o bloco 13 ou o 14 dentro dela: é a consolidada de uma sessão anterior ao PR 6."""
    return any(m.group(1) in BLOCOS_DO_ANEXO for m in _RE_TITULO_BLOCO.finditer(spec or ""))


def montar_anexo(blocos: str, missao: str = "") -> str:
    """O documento do anexo: o cabeçalho, a frase que diz o que ele é, e os blocos 13 e 14."""
    cabecalho = TITULO_ANEXO + (f" — {missao}" if missao else "")
    return (cabecalho + "\n\n> Decisões de UI/UX do design (bloco 13, D0) e ficha do ambiente simulado (bloco 14, D9). "
            "Não altera a spec de produto (`produto/05-spec-missao.md`): a fonte da verdade para codar é a spec de "
            "produto mais este anexo.\n\n" + blocos.strip() + "\n")


def spec_consolidada(state: Dict[str, Any]) -> str:
    """A spec de produto mais os blocos do anexo de design: o que design e dev leem como a missão inteira.

    Sem anexo — a sessão parada em produto, ou a anterior ao PR 6, que traz os blocos 13 e 14 dentro da `spec_missao` —,
    é a `spec_missao` como está."""
    spec = str(state.get("spec_missao") or "")
    blocos = blocos_do_anexo(str(state.get(KEY_ANEXO) or ""))
    if not blocos.strip() or tem_blocos_do_design(spec):
        return spec
    return spec.rstrip() + "\n\n" + blocos


def spec_de_produto_legada(state: Dict[str, Any]) -> Optional[str]:
    """A spec de produto de uma sessão anterior ao PR 6, cuja `spec_missao` traz os blocos 13 e 14 do design: a do
    Gate 0 (`spec_missao_gate0`) ou, sem ela, a `spec_missao` sem os dois blocos. `None` quando não há o que migrar —
    é o caso de toda sessão nova, em que a spec de produto nunca recebe bloco do design."""
    spec = str(state.get("spec_missao") or "")
    if not tem_blocos_do_design(spec):
        return None
    gate0 = str(state.get("spec_missao_gate0") or "")
    if gate0.strip() and not tem_blocos_do_design(gate0):
        return gate0
    from tools.propagacao import spec_de_produto

    return spec_de_produto(spec)
