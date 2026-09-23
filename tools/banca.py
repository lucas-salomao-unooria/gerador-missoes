"""Consolidação determinística da banca de dev — o veredito vira contagem, não redação.

O consolidador era um `LlmAgent` cuja própria descrição prometia "veredito determinístico
🟢/🟡/🔴". Em 14 execuções ele leu 122 achados e aprovou 14 vezes — e a lista de bloqueantes
que ele carregava no prompt omitia `DES-14` (visão do professor), que os arquivos de critério
declaram bloqueante desde 22/09/2026. Ou seja: a visão do professor podia faltar inteira e a
banca liberava, porque o juiz não sabia que aquele critério travava.

Aqui a lista de bloqueantes é lida dos **próprios arquivos de critérios**, que são a fonte da
verdade. Não há segunda cópia para divergir.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from prompts import REFERENCES_DIR

AGENTE = "banca-consolidada"

#: `## DAD-07 [BLOQUEANTE] — Título` · o `[BLOQUEANTE para X]` do PED-01 também conta.
_RE_BLOQUEANTE = re.compile(r"^##\s+([A-Z]{3,4}-\d{2})\s*\[BLOQUEANTE", re.MULTILINE)
_RE_CRITERIO = re.compile(r"^##\s+([A-Z]{3,4}-\d{2})\b", re.MULTILINE)

#: Achados que a esteira não pode fechar porque pedem ato no monorepo da plataforma. Continuam
#: no relatório como pendência declarada, mas não rebaixam o veredito: o PRD que os nomeia é o
#: entregável, e cobrar deles a execução é cobrar de quem não tem o repositório.
FORA_DA_ESTEIRA = frozenset({"TEC-07", "TEC-08", "TEC-09", "TEC-10", "TEC-11", "DES-06"})

_ORDEM = {"bloqueado": 0, "amarelo": 1, "aprovado": 2}


def bloqueantes() -> Dict[str, List[str]]:
    """IDs bloqueantes por arquivo de dimensão, lidos da fonte."""
    fora: Dict[str, List[str]] = {}
    for caminho in sorted((REFERENCES_DIR / "criterios-dev").glob("*.md")):
        fora[caminho.stem] = _RE_BLOQUEANTE.findall(caminho.read_text(encoding="utf-8"))
    return fora


def todos_bloqueantes() -> frozenset:
    return frozenset(i for ids in bloqueantes().values() for i in ids)


def _status_da_dimensao(envelope: Optional[Dict[str, Any]], travam: frozenset) -> tuple:
    """(status, achados relevantes) de uma dimensão. Sem envelope legível = bloqueado."""
    if not envelope:
        return "bloqueado", [{
            "severidade": "bloqueio", "codigo": "dimensao-ausente",
            "resumo": "A dimensão não devolveu envelope legível: uma resposta que não chegou não é aprovação.",
        }]
    achados = [a for a in (envelope.get("achados") or []) if isinstance(a, dict)]
    contagem = envelope.get("contagem") or {}

    def _id(a: Dict[str, Any]) -> str:
        bruto = str(a.get("codigo") or a.get("id") or a.get("criterio") or "")
        m = re.search(r"[A-Z]{3,4}-\d{2}", bruto.upper())
        return m.group(0) if m else ""

    nok = [a for a in achados if str(a.get("severidade", "")).lower() in ("bloqueio", "nok", "❌")]
    nok_travam = [a for a in nok if _id(a) in travam]
    nok_fora = [a for a in nok if _id(a) in FORA_DA_ESTEIRA]

    if nok_travam or int(contagem.get("nok_bloqueantes", 0) or 0) > 0:
        return "bloqueado", achados
    if [a for a in nok if a not in nok_fora] or int(contagem.get("nok", 0) or 0) > len(nok_fora):
        return "amarelo", achados
    if any(str(a.get("severidade", "")).lower() in ("atencao", "atenção", "ressalva") for a in achados):
        return "amarelo", achados
    return "aprovado", achados


def consolidar(envelopes: Dict[str, Optional[Dict[str, Any]]]) -> Dict[str, Any]:
    """Veredito global = o pior das cinco dimensões. Dimensão ausente bloqueia."""
    travam = todos_bloqueantes()
    por_dimensao: Dict[str, Dict[str, Any]] = {}
    todos: List[Dict[str, Any]] = []

    for chave, envelope in envelopes.items():
        status, achados = _status_da_dimensao(envelope, travam)
        por_dimensao[chave] = {"status": status, "achados": achados}
        for a in achados:
            bruto = str(a.get("codigo") or a.get("id") or "").upper()
            m = re.search(r"[A-Z]{3,4}-\d{2}", bruto)
            ident = m.group(0) if m else ""
            copia = dict(a)
            copia["dimensao"] = chave
            if ident in FORA_DA_ESTEIRA:
                copia["severidade"] = "atencao"
                copia["classe"] = "pendencia-plataforma"
            todos.append(copia)

    global_ = min((d["status"] for d in por_dimensao.values()), key=lambda s: _ORDEM[s]) if por_dimensao else "bloqueado"
    return {
        "status": global_,
        "por_dimensao": por_dimensao,
        "achados": todos,
        "bloqueantes_conhecidos": sorted(travam),
    }


def relatorio(resultado: Dict[str, Any], missao: str = "") -> str:
    icone = {"aprovado": "🟢 APTO PARA CODIFICAR", "amarelo": "🟡 APTO COM RESSALVAS",
             "bloqueado": "🔴 NÃO APTO PARA CODIFICAR"}[resultado["status"]]
    linhas = [f"# Validação de insumos — {missao or 'missão'}", "",
              f"**Veredito: {icone}**", "",
              "| Dimensão | Veredito | Achados |", "|---|---|---|"]
    rotulos = {
        "validacao_produto_narrativa": "A — Produto e narrativa",
        "validacao_design_imersao": "B — Design e imersão",
        "validacao_pedagogia_bncc": "C — Pedagogia e BNCC",
        "validacao_dados_lgpd": "D — Dados, telemetria e LGPD",
        "validacao_tecnica_arquitetura": "E — Técnica e arquitetura",
    }
    marca = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}
    for chave, dados in resultado["por_dimensao"].items():
        linhas.append(f"| {rotulos.get(chave, chave)} | {marca[dados['status']]} | {len(dados['achados'])} |")

    impedem = [a for a in resultado["achados"] if str(a.get("severidade", "")).lower() in ("bloqueio", "nok", "❌")]
    plataforma = [a for a in resultado["achados"] if a.get("classe") == "pendencia-plataforma"]
    if impedem:
        linhas += ["", "## O que impede a codificação", ""]
        for a in impedem:
            linhas.append(f"- **{a.get('codigo') or a.get('id') or '—'}** ({a.get('dimensao', '—')}): {a.get('resumo', '')}")
    if plataforma:
        linhas += ["", "## Pendências de plataforma (declaradas, não impedem)", "",
                   "Pedem ato no monorepo — porta de dev, versão em três lugares, suíte E2E, "
                   "invariantes, publicação no Storybook, tema. O PRD que as nomeia é o entregável.", ""]
        for a in plataforma:
            linhas.append(f"- {a.get('codigo') or '—'}: {a.get('resumo', '')}")

    linhas += ["", "```json", _envelope_json(resultado, missao), "```"]
    return "\n".join(linhas)


def _envelope_json(resultado: Dict[str, Any], missao: str) -> str:
    import json
    return json.dumps({
        "agente": AGENTE, "missao": missao, "status": resultado["status"],
        "veredito": {"aprovado": "verde", "amarelo": "amarelo", "bloqueado": "vermelho"}[resultado["status"]],
        "por_dimensao": {k: v["status"] for k, v in resultado["por_dimensao"].items()},
        "achados": [
            {k: a.get(k) for k in ("codigo", "severidade", "dimensao", "classe", "resumo") if a.get(k)}
            for a in resultado["achados"]
        ],
        "precisa_humano": any(a.get("classe") == "pendencia-plataforma" for a in resultado["achados"]),
    }, ensure_ascii=False, indent=2)
