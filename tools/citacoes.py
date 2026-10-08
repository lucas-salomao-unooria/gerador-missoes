"""O LLM só bloqueia com citação que existe — padrão ouro aplicado aos gates de veredito livre.

Até 08/10/2026 o micro-gate, o gate estrutural, os três pareceres, o gate final, o juiz das perguntas, o QA de design
e a banca nas quatro posições decidiam portas reais (o 🔴 deles devolve o documento ou recusa o de acordo) sem que
nada conferisse em que trecho o problema estava. Os juízes de fidelidade, de achados e de contradições já
funcionavam assim: o modelo aponta citando, o código confere.

Aqui vale o mesmo para os achados bloqueantes desses gates: cada um traz `citacao` — o trecho literal do documento
avaliado. Citação que não existe no documento rebaixa o achado a atenção ("citação não confere"): o bloqueio era do
juiz, não do documento. Achado bloqueante **sem** citação continua bloqueando, por cautela — os prompts pedem a
citação, e rebaixar a ausência enfraqueceria os gates enquanto o modelo não a traz sempre.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List

#: Severidades que bloqueiam nos envelopes dos gates (cada prompt usa um vocabulário).
BLOQUEANTES = ("bloqueio", "bloqueante", "nok", "❌", "critico", "crítico", "obrigatorio", "obrigatório")
CAMPOS_DE_CITACAO = ("citacao", "citação", "trecho", "evidencia_literal")
#: Citação curta demais casa em qualquer lugar ("o estudante"): não prova nada.
MIN_PALAVRAS = 4


def bloqueante(achado: Dict[str, Any]) -> bool:
    return str(achado.get("severidade", "")).strip().lower() in BLOQUEANTES


def citacao(achado: Dict[str, Any]) -> str:
    return next((str(achado[c]) for c in CAMPOS_DE_CITACAO if str(achado.get(c) or "").strip()), "")


def conferir(achados: Iterable[Dict[str, Any]], documentos: str) -> List[Dict[str, Any]]:
    """Rebaixa, no lugar, cada achado bloqueante cuja citação não existe nos documentos. Devolve os rebaixados."""
    from tools.fidelidade import _citacao_confere, _norm

    docs = _norm(documentos or "")
    rebaixados: List[Dict[str, Any]] = []
    if not docs:
        return rebaixados
    for a in achados:
        if not isinstance(a, dict) or not bloqueante(a):
            continue
        cit = citacao(a)
        if not cit or len(cit.split()) < MIN_PALAVRAS:
            continue
        if not _citacao_confere(cit, docs):
            a["severidade_original"] = a.get("severidade")
            a["severidade"] = "atencao"
            a["citacao_nao_confere"] = True
            a["resumo"] = f"[citação não confere — rebaixado de bloqueio] {a.get('resumo') or ''}".strip()
            rebaixados.append(a)
    return rebaixados


def texto_dos_documentos(state: Dict[str, Any], chaves: Iterable[str]) -> str:
    return "\n\n".join(str(state.get(k, "") or "") for k in chaves)
