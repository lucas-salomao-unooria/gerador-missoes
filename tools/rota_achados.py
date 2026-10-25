"""O achado vai a quem pode consertá-lo: bloqueio sobre o conteúdo do one-pager não volta ao autor da spec.

76d9af6e (exp01em1b, 23/10/2026): a banca de produto deu 🔴 com o PED-06 — «No registro do Canal A, o indicador de
EM13CO03 é classificado como 'Não atingiu'…», texto do §7 do one-pager. O `SpecLoop` devolveu o achado ao autor da spec
(`autor_keys=["spec_missao"]`), que não pode contrariar o one-pager (A054): a rodada foi gasta, o loop chegou ao teto
(`spec_rodada` = 2) e a banca saiu 🔴 do mesmo jeito. O achado era verdadeiro; o defeito era a rota.

A regra é literal, sobre o dado estruturado do achado: a citação dele (`citacao`/`trecho`, a que `tools/citacoes.py`
confere) está no documento do dono — o one-pager — e não está no documento do autor do loop. Então o conteúdo citado é
do one-pager, e quem decide é o PO, no parecer de produto (Refazer com a mudança, que refaz o one-pager). O achado fica
bloqueante (o veredito do gate não muda, e o de acordo continua recusado com o 🔴); só deixa de mandar o autor que não é
dono reescrever. Achado sem citação, com citação curta ou que também está no documento do autor segue com o autor.

Achado misto — o resumo do PED-06 também dizia «além de faltar a definição explícita de zero e none na tabela 9b da
spec» — não é partido: separar a parte da spec seria interpretar a prosa do juiz. Quando o loop roda por outro bloqueio, o
achado do PO vai ao autor como contexto (`motivos_do_retrabalho`: «não altere o que o one-pager decide»), sem gastar
rodada por ele; quando ele é o único bloqueio, o loop não roda, e a parte da spec chega ao autor pelo Refazer de produto
do PO, que refaz o one-pager e a spec com o pedido.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

ROTA_PO = "po"
_PREFIXO = "[conteúdo do one-pager — quem decide é o PO, no parecer de produto (Refazer com a mudança); a spec não pode " \
           "contrariar o one-pager]"


def marcar(envelope: Optional[Dict[str, Any]], documento_do_dono: str, documento_do_autor: str) -> List[Dict[str, Any]]:
    """Marca, no lugar, cada achado bloqueante cuja citação está no documento do dono e não no do autor. Devolve os
    marcados (os já marcados antes não contam de novo)."""
    from tools import citacoes

    if not isinstance(envelope, dict) or not str(documento_do_dono or "").strip():
        return []
    dono, autor = citacoes.normalizar(documento_do_dono), citacoes.normalizar(documento_do_autor or "")
    marcados: List[Dict[str, Any]] = []
    for a in envelope.get("achados") or []:
        if not isinstance(a, dict) or not citacoes.bloqueante(a) or a.get("rota") == ROTA_PO:
            continue
        cit = citacoes.citacao(a)
        if not cit or len(cit.split()) < citacoes.MIN_PALAVRAS:
            continue
        if citacoes.existe(cit, dono) and not (autor and citacoes.existe(cit, autor)):
            a["rota"] = ROTA_PO
            a["resumo"] = f"{_PREFIXO} {a.get('resumo') or ''}".strip()
            marcados.append(a)
    return marcados


def bloqueios_do_autor(envelope: Any) -> List[Dict[str, Any]]:
    """Os achados bloqueantes que o autor do loop pode consertar — todos, menos os que vão ao PO."""
    from tools import citacoes

    if not isinstance(envelope, dict):
        return []
    return [a for a in envelope.get("achados") or []
            if isinstance(a, dict) and citacoes.bloqueante(a) and a.get("rota") != ROTA_PO]


def so_do_po(envelope: Any) -> bool:
    """O gate reprova só por achado que vai ao PO: repetir o loop não o conserta."""
    from tools import citacoes

    if not isinstance(envelope, dict):
        return False
    bloqueios = [a for a in envelope.get("achados") or [] if isinstance(a, dict) and citacoes.bloqueante(a)]
    return bool(bloqueios) and all(a.get("rota") == ROTA_PO for a in bloqueios)
