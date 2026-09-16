"""Conformidade determinística com a BNCC Computação.

Fonte única: ``prompts/references/bncc-computacao.json`` (transcrito do anexo oficial do MEC;
o markdown incluído nos prompts é gerado dele por ``scripts/gerar_bncc_referencia.py``).

Três regras, todas mecânicas — o que exige julgamento (a ação em tela exercita a habilidade?)
fica com os agentes LLM:

1. todo código citado no bloco 11 da spec existe na lista oficial;
2. todo código é compatível com a série da missão (``EF0n`` = ano n · ``EF15`` = 1º–5º ·
   ``EF69`` = 6º–9º · ``EM13`` = Ensino Médio);
3. pelo menos um código é de **letramento digital** — Cultura Digital — no Ensino Fundamental.

No Ensino Médio não há separação por série nem eixo: qualquer ``EM13`` vale para 1ª–3ª série, a
missão precisa citar pelo menos uma, e a marca de letramento digital (lista proposta pela Unooria)
gera atenção, não bloqueio.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from prompts import REFERENCES_DIR

JSON_PATH: Path = REFERENCES_DIR / "bncc-computacao.json"

CODIGO_RE = re.compile(r"\bE[FM]\d{2}CO\d{2}\b")
_BLOCO_RE = r"^#{1,4}\s*%d\s*[.—-]"  # "## 11. Currículo", "## 11 — Currículo"

AGENTE = "bncc-check"


@lru_cache(maxsize=1)
def carregar() -> Dict[str, Any]:
    return json.loads(JSON_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def habilidades() -> Dict[str, Dict[str, Any]]:
    return {h["codigo"]: h for h in carregar()["habilidades"]}


def extrair_codigos(texto: str) -> List[str]:
    """Códigos `EFnnCOnn`/`EM13COnn` na ordem em que aparecem, sem repetição."""
    vistos: List[str] = []
    for c in CODIGO_RE.findall(texto or ""):
        c = c.upper()
        if c not in vistos:
            vistos.append(c)
    return vistos


def secao_bloco(texto: str, numero: int) -> Optional[str]:
    """Texto do bloco `## <numero>.` da spec até o próximo heading numerado (ou o fim)."""
    m = re.search((_BLOCO_RE % numero) + r".*$", texto or "", re.MULTILINE)
    if not m:
        return None
    resto = texto[m.end():]
    m2 = re.search(r"^#{1,4}\s*\d{1,2}\s*[.—-]", resto, re.MULTILINE)
    return resto[: m2.start()] if m2 else resto


# ------------------------------------------------------------------ série / ano
_ANOS_INICIAIS = {1, 2, 3, 4, 5}
_ANOS_FINAIS = {6, 7, 8, 9}


def extrair_serie(texto: str) -> Dict[str, Any]:
    """Anos do Fundamental e/ou Ensino Médio declarados no texto.

    Reconhece `5EF`, `["5EF"]`, `5º ano`, `5° ano do EF`, `1º–2º ano`, `1º ao 5º`, `anos iniciais`,
    `anos finais`, `2EM`, `2ª série do EM`, `Ensino Médio`.
    """
    t = texto or ""
    anos: Set[int] = set()
    em = False
    evid: List[str] = []

    for m in re.finditer(r"\b([1-9])\s*EF\b", t):
        anos.add(int(m.group(1))); evid.append(m.group(0))
    for m in re.finditer(r"\b([1-3])\s*EM\b", t):
        em = True; evid.append(m.group(0))
    # faixas "1º–2º", "1º ao 5º", "6º a 9º"
    for m in re.finditer(r"([1-9])\s*[ºo°]\s*(?:ano\s*)?(?:[–\-]|a|ao|até)\s*([1-9])\s*[ºo°]", t, re.IGNORECASE):
        a, b = int(m.group(1)), int(m.group(2))
        if a <= b:
            anos.update(range(a, b + 1)); evid.append(m.group(0))
    # "5º ano", "5° ano", "5º do EF"
    for m in re.finditer(r"\b([1-9])\s*[ºo°]\s*(?:ano|do\s+EF|EF|do\s+Ensino\s+Fundamental)\b", t, re.IGNORECASE):
        anos.add(int(m.group(1))); evid.append(m.group(0))
    # série do EM
    for m in re.finditer(r"\b([1-3])\s*[ªa]\s*s[ée]rie", t, re.IGNORECASE):
        em = True; evid.append(m.group(0))
    if re.search(r"\bensino\s+m[ée]dio\b", t, re.IGNORECASE):
        em = True; evid.append("Ensino Médio")
    if re.search(r"\banos\s+iniciais\b", t, re.IGNORECASE):
        anos.update(_ANOS_INICIAIS); evid.append("anos iniciais")
    if re.search(r"\banos\s+finais\b", t, re.IGNORECASE):
        anos.update(_ANOS_FINAIS); evid.append("anos finais")

    return {"anos": anos, "em": em, "evidencias": evid[:8]}


def _compativel(hab: Dict[str, Any], anos: Set[int], em: bool) -> bool:
    if hab["etapa"] == "EM":
        return em
    return bool(anos & set(hab["anos"]))


# ------------------------------------------------------------------ validação
def validar_spec(spec: str) -> Dict[str, Any]:
    """Aplica as três regras à spec. Devolve status, achados e o detalhe por código."""
    spec = spec or ""
    data = carregar()
    habs = habilidades()
    em_letramento = set(data["letramento_digital"]["em_proposta"])
    achados: List[Dict[str, str]] = []

    bloco11 = secao_bloco(spec, 11)
    if bloco11 is None:
        achados.append({"severidade": "atencao", "codigo": "bloco-11", "resumo": "Bloco 11 (Currículo) não encontrado pelo heading `## 11.`; os códigos foram lidos da spec inteira."})
        fonte_codigos = spec
    else:
        fonte_codigos = bloco11
    codigos = extrair_codigos(fonte_codigos)

    bloco0 = secao_bloco(spec, 0)
    serie = extrair_serie(bloco0 or "")
    if not serie["anos"] and not serie["em"]:
        serie = extrair_serie(spec[:2000])
    if not serie["anos"] and not serie["em"]:
        serie = extrair_serie(spec)
    anos, em = serie["anos"], serie["em"]

    if not codigos:
        achados.append({"severidade": "bloqueio", "codigo": "sem-codigo", "resumo": "Nenhum código de habilidade da BNCC Computação no bloco 11. A missão não declara currículo."})
    if not anos and not em:
        achados.append({"severidade": "bloqueio", "codigo": "serie", "resumo": "Série da missão não identificada no bloco 0 (esperado `[\"5EF\"]`, `5º ano`, `2EM`…). Sem série não há como conferir o ano das habilidades."})

    detalhes: List[Dict[str, Any]] = []
    tem_letramento = False
    for c in codigos:
        hab = habs.get(c)
        if not hab:
            detalhes.append({"codigo": c, "existe": False, "eixo": None, "letramento": False, "ano_ok": False, "habilidade": ""})
            achados.append({"severidade": "bloqueio", "codigo": c, "resumo": f"`{c}` não existe na BNCC Computação. Código inventado ou digitado errado."})
            continue
        ano_ok = _compativel(hab, anos, em) if (anos or em) else False
        letr = bool(hab["letramento_digital"])
        detalhes.append({"codigo": c, "existe": True, "eixo": hab["eixo"], "letramento": letr, "ano_ok": ano_ok, "habilidade": hab["habilidade"], "anos": hab["anos"], "etapa": hab["etapa"]})
        if (anos or em) and not ano_ok:
            alvo = "Ensino Médio" if hab["etapa"] == "EM" else "/".join(f"{a}º" for a in hab["anos"]) + " ano"
            declarado = ("EM" if em else "") + ("/".join(f"{a}º" for a in sorted(anos)) if anos else "")
            achados.append({"severidade": "bloqueio", "codigo": c, "resumo": f"`{c}` é do {alvo}; a missão é de {declarado}. Habilidade de outro ano."})
        if letr and ano_ok:
            tem_letramento = True
            if hab["etapa"] == "EM":
                achados.append({"severidade": "atencao", "codigo": c, "resumo": f"`{c}` conta como letramento digital pela leitura **proposta** do EM (sem eixo oficial) — validar com pedagogia."})

    if codigos and (anos or em) and not tem_letramento:
        if anos and not em:
            achados.append({"severidade": "bloqueio", "codigo": "letramento", "resumo": "Nenhuma habilidade de letramento digital (Cultura Digital) compatível com a série. É o único recorte da BNCC que bloqueia — e falta."})
        else:
            achados.append({"severidade": "atencao", "codigo": "letramento", "resumo": "Nenhuma habilidade da lista proposta de letramento digital do EM. O anexo não tem eixo no Médio, então isto não bloqueia — a avaliação pedagógica decide."})

    status = "bloqueado" if any(a["severidade"] == "bloqueio" for a in achados) else "aprovado"
    return {
        "status": status,
        "anos": sorted(anos),
        "em": em,
        "evidencias_serie": serie["evidencias"],
        "codigos": codigos,
        "detalhes": detalhes,
        "achados": achados,
        "tem_letramento": tem_letramento,
        "bloco11_encontrado": bloco11 is not None,
    }


def relatorio_markdown(resultado: Dict[str, Any], missao: str = "") -> str:
    """Relatório legível + envelope JSON no padrão da esteira."""
    r = resultado
    ok = r["status"] == "aprovado"
    linhas = [f"# Conformidade BNCC Computação — {missao or 'missão'}", ""]
    linhas.append(f"**Veredito: {'🟢 CONFORME' if ok else '🔴 BLOQUEADO'}** · verificação determinística contra `references/bncc-computacao.json` (anexo oficial do MEC).")
    serie = ("Ensino Médio " if r["em"] else "") + (", ".join(f"{a}º ano" for a in r["anos"]) if r["anos"] else "")
    linhas.append(f"**Série identificada:** {serie or '— não identificada'}" + (f" (evidências: {', '.join(r['evidencias_serie'])})" if r["evidencias_serie"] else ""))
    linhas.append(f"**Bloco 11 encontrado:** {'sim' if r['bloco11_encontrado'] else 'não — códigos lidos da spec inteira'}")
    linhas.append("")
    linhas.append("## Habilidades citadas")
    linhas.append("")
    if r["detalhes"]:
        linhas.append("| Código | Existe | Eixo | Ano compatível | Letramento digital | Habilidade |")
        linhas.append("|---|---|---|---|---|---|")
        eixos = {"PC": "Pensamento Computacional", "MD": "Mundo Digital", "CD": "Cultura Digital", None: "— (EM, por competência)"}
        for d in r["detalhes"]:
            linhas.append(
                f"| `{d['codigo']}` | {'✅' if d['existe'] else '❌'} | {eixos.get(d['eixo'], d['eixo']) if d['existe'] else '—'} | "
                f"{'✅' if d['ano_ok'] else '❌'} | {'✅' if d['letramento'] else '—'} | {d['habilidade']} |"
            )
    else:
        linhas.append("_Nenhum código encontrado._")
    linhas.append("")
    linhas.append("## Achados")
    linhas.append("")
    if r["achados"]:
        for a in r["achados"]:
            icone = "⛔" if a["severidade"] == "bloqueio" else "⚠️"
            linhas.append(f"- {icone} **{a['codigo']}** — {a['resumo']}")
    else:
        linhas.append("- Nenhum. As três regras (existência, ano, letramento digital) passaram.")
    linhas.append("")
    linhas.append("## O que este gate não julga")
    linhas.append("")
    linhas.append("Se a ação em tela exercita de fato a habilidade é julgamento da avaliação pedagógica (critérios 5.1 e 5.2) e do QA de entregáveis (D2). Este gate garante só que o currículo declarado existe, é do ano certo e, no Fundamental, inclui letramento digital. No Ensino Médio (tabela única, sem eixo) basta pelo menos uma habilidade EM13; a marca de letramento é orientação.")
    linhas.append("")
    envelope = {
        "agente": AGENTE,
        "missao": missao or "",
        "rodada": 1,
        "status": r["status"],
        "serie": {"anos": r["anos"], "em": r["em"]},
        "codigos": r["codigos"],
        "letramento_digital": r["tem_letramento"],
        "achados": [
            {"severidade": a["severidade"], "classe": "curriculo", "codigo": a["codigo"], "agente_responsavel": "gate-estrutural", "resumo": a["resumo"]}
            for a in r["achados"]
        ],
        "precisa_humano": not ok,
    }
    linhas.append("```json")
    linhas.append(json.dumps(envelope, ensure_ascii=False))
    linhas.append("```")
    return "\n".join(linhas)
