"""Lint determinístico do protótipo HTML — o D8 deixa de se auto-aprovar.

O QA de design julgava o HTML que o próprio agente de design gerou, lendo o relatório dele
em vez do arquivo. Não havia nenhuma conferência mecânica: um protótipo com metade das telas,
com `TODO` na tela de pico ou que nem abre passava se o relatório dissesse que estava pronto.

As perguntas aqui são todas de FATO — o arquivo abre? as telas declaradas estão nele? sobrou
marcador de rascunho? — e por isso cabem em código. Julgar se a tela está BOA continua sendo
trabalho do QA.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

AGENTE = "prototipo-lint"

_RE_ID_TELA = re.compile(r"\bE\d-(?:ALU|PROF|SIS)-\d{2}\b")
_RE_RASCUNHO = re.compile(r"\b(TODO|FIXME|XXX|lorem ipsum|placeholder|\[preencher|a definir)\b", re.IGNORECASE)
_RE_TAG_ABERTA = re.compile(r"<(html|body)\b", re.IGNORECASE)


def validar(html: str, telas_declaradas: Optional[List[str]] = None) -> Dict[str, Any]:
    """Confere o protótipo contra o inventário de telas da jornada."""
    texto = html or ""
    achados: List[Dict[str, str]] = []

    def falha(codigo: str, resumo: str, severidade: str = "bloqueio") -> None:
        achados.append({"severidade": severidade, "codigo": codigo, "etapa": "design", "resumo": resumo})

    if not texto.strip():
        falha("prototipo-vazio", "O protótipo chegou vazio: não há arquivo para o QA inspecionar.")
        return {"status": "bloqueado", "achados": achados, "telas": [], "declaradas": telas_declaradas or []}

    if not _RE_TAG_ABERTA.search(texto):
        falha("prototipo-nao-abre", "Sem `<html>` nem `<body>`: o arquivo não é uma página que o navegador abre.")

    telas = sorted(set(_RE_ID_TELA.findall(texto)))
    declaradas = sorted(set(telas_declaradas or []))
    if declaradas:
        faltando = [t for t in declaradas if t not in telas]
        if faltando:
            falha("telas-ausentes",
                  f"{len(faltando)} tela(s) do inventário não aparecem no protótipo: {', '.join(faltando[:6])}"
                  + ("…" if len(faltando) > 6 else "")
                  + ". O QA inspeciona o que está na tela, não o que o relatório promete.")
        sobrando = [t for t in telas if t not in declaradas]
        if sobrando:
            falha("telas-nao-declaradas",
                  f"Tela no protótipo que o inventário não declara: {', '.join(sobrando[:6])}. "
                  f"Ou a jornada está desatualizada, ou o protótipo inventou tela.",
                  severidade="atencao")
    elif not telas:
        falha("sem-id-de-tela",
              "Nenhum identificador `E<etapa>-<ator>-<n>` no protótipo: sem isso não há como "
              "casar tela construída com tela declarada, e o QA vira leitura de relatório.")

    rascunhos = sorted(set(m.group(0).lower() for m in _RE_RASCUNHO.finditer(texto)))
    if rascunhos:
        falha("marcador-de-rascunho",
              f"Marcador de rascunho no protótipo ({', '.join(rascunhos[:4])}): o que vai ao QA "
              f"é o que a criança veria.")

    bloqueios = [a for a in achados if a["severidade"] == "bloqueio"]
    status = "bloqueado" if bloqueios else ("amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados, "telas": telas, "declaradas": declaradas}


def relatorio(resultado: Dict[str, Any], missao: str = "") -> str:
    import json
    icone = {"aprovado": "🟢 PROTÓTIPO ÍNTEGRO", "amarelo": "🟡 COM RESSALVAS", "bloqueado": "🔴 BLOQUEADO"}[resultado["status"]]
    linhas = [f"# Lint do protótipo — {missao or 'missão'}", "", f"**Veredito: {icone}**", "",
              f"Telas no arquivo: **{len(resultado['telas'])}**"
              + (f" · declaradas no inventário: **{len(resultado['declaradas'])}**" if resultado["declaradas"] else ""),
              ""]
    if resultado["achados"]:
        linhas += ["## Achados", ""]
        for a in resultado["achados"]:
            marca = "❌" if a["severidade"] == "bloqueio" else "⚠️"
            linhas.append(f"- {marca} **{a['codigo']}** — {a['resumo']}")
    else:
        linhas.append("Nenhum achado: o arquivo abre, tem os identificadores de tela e não traz marcador de rascunho.")
    linhas += ["", "```json", json.dumps(
        {"agente": AGENTE, "missao": missao, "status": resultado["status"], "achados": resultado["achados"]},
        ensure_ascii=False, indent=2), "```"]
    return "\n".join(linhas)
