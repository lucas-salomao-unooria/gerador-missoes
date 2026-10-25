"""Comitês pedagógicos — três juízes votam, o código conta.

Até 15/10/2026 o sentido pedagógico da mecânica e dos canais de evidência era julgado por um parecer avulso (o 5f do
024a e o Eixo 5 do 024c), corrigido por um revisor que não escreveu a missão e, com one-pager do PO anexado, nem podia
exigir mudança. Agora cada comitê tem três juízes com lentes diferentes, e a missão só passa com os três aprovando.

O comitê não escreve: o relatório volta a quem escreve a missão — o A004 (núcleo: mecânica e canais do foco primário)
e o A014 (seções de apoio: §12a das demais habilidades e seções 5–18) —, e a reescrita passa de novo pelos gates do
núcleo. Por isso cada achado diz de quem é a correção.

Como na banca e no juiz de profundidade, o voto é contado em código a partir dos achados, não do que o juiz escreveu:
- reprova = ao menos um achado bloqueante que sobreviveu à conferência de citação (`tools/citacoes.py`);
- "reprova" sem achado verificável conta como aprova, com a ressalva no relatório: reprovar sem apontar o trecho
  devolveria a missão ao autor sem nada para ele corrigir;
- envelope ausente ou ilegível conta como reprova: juiz que não respondeu não aprovou.

Unanimidade aprova. Sem ela, a missão volta ao autor; na última rodada, segue com 🟡 e os votos vencidos ficam no
relatório (decisão do PO de 15/10/2026: o teto esgotado não bloqueia o de acordo).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

AGENTE = "comite-pedagogico"

#: Quem corrige cada achado. O juiz escreve `autor`; aceitamos também o nome do agente.
AUTORES = {"A004": "o núcleo narrativo (A004)", "A014": "as seções de apoio (A014)"}
_RE_AUTOR_NUCLEO = re.compile(r"\b(a0?04|n[uú]cleo)\b", re.I)
_RE_AUTOR_APOIO = re.compile(r"\b(a0?14|se[cç][oõ]es\s+de\s+apoio|apoio)\b", re.I)

_VOTO_REPROVA = ("reprova", "reprovado", "reprovada", "bloqueado", "bloqueada", "nao_aprova", "não aprova", "🔴")

#: Relatórios consolidados dos comitês, que os autores leem e que autorizam alterar o texto do PO.
CHAVES_RELATORIO = ["comite_canal_a_report", "comite_canal_b_report", "comite_final_report"]


def autor_do_achado(achado: Dict[str, Any]) -> str:
    """`A004` | `A014` | `""` — a quem cabe a correção."""
    bruto = str(achado.get("autor") or achado.get("agente_responsavel") or "")
    if _RE_AUTOR_NUCLEO.search(bruto):
        return "A004"
    if _RE_AUTOR_APOIO.search(bruto):
        return "A014"
    return ""


def _voto_declarado(envelope: Dict[str, Any]) -> str:
    bruto = str(envelope.get("voto") or envelope.get("status") or "").strip().lower()
    return "reprova" if bruto in _VOTO_REPROVA else "aprova"


def voto(relatorio: str, documentos: str = "") -> Dict[str, Any]:
    """O voto de um juiz, contado dos achados que ele trouxe."""
    from agents.callbacks import extrair_envelope
    from tools import citacoes

    envelope = extrair_envelope(relatorio or "")
    if not envelope:
        return {"voto": "reprova", "dispensado": False, "achados": [{
            "severidade": "bloqueio", "codigo": "juiz-sem-voto", "autor": "",
            "resumo": "O juiz não devolveu envelope legível: resposta vazia, truncada ou sem o bloco JSON. "
                      "Não respondeu não é aprovou."}]}
    if envelope.get("dispensado"):
        return {"voto": "aprova", "dispensado": True, "motivo": str(envelope.get("motivo") or ""), "achados": []}

    achados = [dict(a) for a in envelope.get("achados") or [] if isinstance(a, dict)]
    if documentos:
        citacoes.conferir(achados, documentos)
    bloqueios = [a for a in achados if citacoes.bloqueante(a)]
    declarado = _voto_declarado(envelope)
    if declarado == "reprova" and not bloqueios:
        achados.append({"severidade": "atencao", "codigo": "voto-sem-achado-verificavel", "autor": "",
                        "resumo": "O juiz votou pela reprovação sem nenhum achado bloqueante com trecho que exista no "
                                  "documento. Conta como aprovação: não há o que o autor corrigir."})
    return {"voto": "reprova" if bloqueios else "aprova", "dispensado": False, "achados": achados,
            "declarado": declarado}


def consolidar(relatorios: Dict[str, str], documentos: str = "", rodada: int = 1,
               max_rodadas: int = 5) -> Dict[str, Any]:
    """Veredito do comitê: unanimidade aprova; sem ela, bloqueia — e na última rodada, 🟡."""
    from tools import citacoes

    votos = {chave: voto(texto, documentos) for chave, texto in relatorios.items()}
    unanime = bool(votos) and all(v["voto"] == "aprova" for v in votos.values())
    if unanime:
        status = "aprovado"
    elif rodada >= max_rodadas:
        status = "amarelo"
    else:
        status = "bloqueado"

    achados: List[Dict[str, Any]] = []
    por_autor: Dict[str, List[Dict[str, Any]]] = {}
    for chave, v in votos.items():
        for a in v["achados"]:
            item = {**a, "juiz": chave, "autor": autor_do_achado(a)}
            if citacoes.bloqueante(item):
                por_autor.setdefault(item["autor"], []).append(item)
            if status == "amarelo" and citacoes.bloqueante(item):
                # No teto de rodadas (veredito 🟡), achados de juízes vencidos seguem como ressalva («segue com
                # ressalva») no envelope, sem contar como bloqueio residual na saúde da missão (G08).
                item = {**item, "severidade": "atencao", "rebaixado_no_teto": True}
            achados.append(item)
    return {"status": status, "unanime": unanime, "rodada": rodada, "max_rodadas": max_rodadas,
            "votos": votos, "achados": achados, "por_autor": por_autor,
            "contra": sum(1 for v in votos.values() if v["voto"] == "reprova")}


def _linha_de_achado(a: Dict[str, Any], rotulos: Dict[str, str]) -> str:
    from tools import citacoes

    partes = [f"**{a.get('id') or a.get('codigo') or '—'}**"]
    if a.get("habilidade"):
        partes.append(f"`{a['habilidade']}`")
    partes.append(f"({rotulos.get(a.get('juiz', ''), a.get('juiz', ''))})")
    texto = " ".join(partes) + f": {a.get('resumo', '')}"
    if a.get("o_que_corrigir"):
        texto += f" **Corrigir:** {a['o_que_corrigir']}"
    cit = citacoes.citacao(a)
    if cit:
        texto += f"\n  > «{cit}»"
    return f"- {texto}"


def relatorio(resultado: Dict[str, Any], titulo: str, rotulos: Dict[str, str], missao: str = "") -> str:
    """O relatório que o autor lê na rodada seguinte: o que corrigir vem antes das ressalvas."""
    from tools import citacoes

    n = len(resultado["votos"])
    icone = {
        "aprovado": f"🟢 APROVADO POR UNANIMIDADE ({n} de {n})",
        "bloqueado": f"🔴 REPROVADO — {resultado['contra']} de {n} contra; volta ao autor",
        "amarelo": f"🟡 SEM UNANIMIDADE NO TETO — {resultado['contra']} de {n} contra; segue com ressalva",
    }[resultado["status"]]
    linhas = [f"# {titulo} — {missao or 'missão'}", "",
              f"**Veredito: {icone}** · rodada {resultado['rodada']} de {resultado['max_rodadas']}", "",
              "| Juiz | Voto | Achados que bloqueiam |", "|---|---|---|"]
    for chave, v in resultado["votos"].items():
        if v.get("dispensado"):
            marca = "dispensado (nada a julgar)"
        else:
            marca = "✅ aprova" if v["voto"] == "aprova" else "❌ reprova"
        n_bloq = sum(1 for a in v["achados"] if citacoes.bloqueante(a))
        linhas.append(f"| {rotulos.get(chave, chave)} | {marca} | {n_bloq} |")

    if resultado["por_autor"]:
        linhas += ["", "## O que corrigir", "",
                   "Cada achado diz quem reescreve. Corrija exatamente o que está atribuído a você e mantenha o resto "
                   "palavra por palavra — o comitê vota de novo sobre a versão inteira."]
        for autor in ("A004", "A014", ""):
            itens = resultado["por_autor"].get(autor)
            if not itens:
                continue
            titulo_autor = (f"### Para {AUTORES[autor]}" if autor
                            else "### Sem autor indicado — os dois autores leem, e o dono do trecho corrige")
            linhas += ["", titulo_autor, ""] + [_linha_de_achado(a, rotulos) for a in itens]

    ressalvas = [a for a in resultado["achados"] if not citacoes.bloqueante(a)]
    if ressalvas:
        linhas += ["", "## Ressalvas (não bloqueiam)", ""] + [_linha_de_achado(a, rotulos) for a in ressalvas]
    if resultado["status"] == "amarelo":
        linhas += ["", "## Votos vencidos no teto", "",
                   f"O comitê chegou à rodada {resultado['rodada']} sem unanimidade. A missão segue para o parecer do PO "
                   "com os achados acima à vista: leia-os antes do de acordo."]

    linhas += ["", "```json", json.dumps(envelope(resultado), ensure_ascii=False), "```"]
    return "\n".join(linhas)


def envelope(resultado: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "agente": AGENTE,
        "status": resultado["status"],
        "rodada": resultado["rodada"],
        "unanime": resultado["unanime"],
        "votos": {k: ("dispensado" if v.get("dispensado") else v["voto"]) for k, v in resultado["votos"].items()},
        "achados": [{"severidade": a.get("severidade"), "codigo": a.get("id") or a.get("codigo") or "comite",
                     "juiz": a.get("juiz"), "autor": a.get("autor"), "habilidade": a.get("habilidade") or "",
                     "resumo": str(a.get("resumo") or "")[:400]}
                    for a in resultado["achados"]],
    }


def envelope_dispensado(motivo: str) -> str:
    """O que o juiz pulado devolve: um voto que aprova sem custo (painel B sem Canal B na missão)."""
    return "```json\n" + json.dumps({"agente": AGENTE, "status": "aprovado", "voto": "aprova", "dispensado": True,
                                      "motivo": motivo, "achados": []}, ensure_ascii=False) + "\n```"


def texto_votos(state: Dict[str, Any], chaves: Optional[List[str]] = None) -> str:
    """Os relatórios dos comitês, juntos — onde o pedido de uma alteração no texto do PO é conferido."""
    return "\n\n".join(str(state.get(k, "") or "") for k in (chaves or CHAVES_RELATORIO))
