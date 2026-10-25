"""Gabarito da fidelidade (C2 do backlog de 24/10/2026): a fidelidade reavaliada sobre o estado real da execução.

A conferência (`tools.fidelidade.aplicar`) é determinística sobre a resposta que o juiz e o intérprete gravaram. Aqui
ela roda como o `FidelidadeCheckAgent` a roda — checklist dos pedidos da etapa e do briefing, núcleo em modo parcial,
versões anteriores, correção pontual —, com uma diferença: o checklist é montado pelo código de hoje, e os ids que o
juiz respondeu (os do checklist da época) são casados pelo texto do item no relatório gravado. Item que não casa fica
sem resposta (`nao-julgado`), e o teste que dependa dele falha: o caso tem de achar o item pelo trecho real.

Estados: `acervo:<missão>-<sessão>` (`tests/acervo`) ou `<missão>-<sessão>` de `estados_fidelidade/`
(`extrair_estados_fidelidade.py`).
"""
from __future__ import annotations

import copy
import functools
import json
import lzma
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from extrair_estados_fidelidade import arquivo

ACERVO = Path(__file__).resolve().parent.parent / "acervo"

#: gate → (juiz, intérprete, relatório, documentos, etapas do pedido, parcial, com briefing, etapa)
GATES = {
    "nucleo": ("juiz_fidelidade_nucleo_saida", "interpretacao_fidelidade_nucleo_saida", "fidelidade_nucleo_report",
               ("nucleo_narrativo",), ("produto", ""), True, True, "produto"),
    "produto": ("juiz_fidelidade_saida", "interpretacao_fidelidade_saida", "fidelidade_report",
                ("nucleo_narrativo", "one_pager", "spec_missao"), ("produto", ""), False, True, "produto"),
    "design": ("juiz_fidelidade_design_saida", "interpretacao_fidelidade_design_saida", "fidelidade_design_report",
               None, ("design",), False, False, "design"),
}


@functools.lru_cache(maxsize=None)
def _estado(execucao: str) -> Dict[str, Any]:
    if execucao.startswith("acervo:"):
        return json.loads((ACERVO / execucao.split(":", 1)[1] / "estado.json").read_text(encoding="utf-8"))
    return json.loads(lzma.decompress(arquivo(execucao).read_bytes()).decode("utf-8"))


def estado(execucao: str) -> Dict[str, Any]:
    """Cópia funda: o caso que muda um documento (mutante) não contamina os outros."""
    return copy.deepcopy(_estado(execucao))


def documentos_do_design() -> List[str]:
    from agents.design import FIDELIDADE_DOCUMENTOS_DESIGN

    return list(FIDELIDADE_DOCUMENTOS_DESIGN)


def _simples(texto: str) -> str:
    from tools.fidelidade import _norm

    return re.sub(r"[«»]", "", _norm(texto))


def _linhas_do_relatorio(relatorio: str) -> Dict[str, List[str]]:
    """`{id: [textos do item]}` do relatório gravado: no conferido, o texto entre o travessão e a seta; no achado, cada
    trecho entre «» (o primeiro pode ser o texto a tirar, não o item)."""
    textos: Dict[str, List[str]] = {}
    for linha in (relatorio or "").splitlines():
        m = re.match(r"^- ✅ \*\*(F\d+)\*\* — (.*?) → «", linha.strip())
        if m:
            textos.setdefault(m.group(1), []).append(_simples(m.group(2)))
            continue
        m = re.match(r"^- \S+ \*\*(F\d+)\*\* \(.*?\) — (.*)$", linha.strip())
        if m:
            textos.setdefault(m.group(1), []).extend(_simples(s) for s in re.findall(r"«(.*?)»(?=[.\s]|$)", m.group(2)))
    return textos


def _id_gravado(textos: Dict[str, List[str]], trecho: str, usados: Sequence[str] = ()) -> Optional[str]:
    """O id gravado do item cujo texto começa como o trecho (ou o contém, para trecho do meio do item)."""
    alvo = _simples(trecho)[:50]
    if not alvo:
        return None
    for criterio in (lambda s: s.startswith(alvo) or alvo.startswith(s[:50]), lambda s: alvo in s):
        for i, segmentos in textos.items():
            if i not in usados and any(s and criterio(s) for s in segmentos):
                return i
    return None


def _remapear(saida: str, chave: str, mapa: Dict[str, str]) -> str:
    """A resposta do juiz (`decisoes`) ou do intérprete (`itens`) com os ids do checklist de hoje."""
    for bruto in reversed(re.findall(r"```json\s*(.*?)```", saida or "", re.S)):
        try:
            dados = json.loads(bruto)
        except json.JSONDecodeError:
            continue
        if not isinstance(dados, dict) or not isinstance(dados.get(chave), list):
            continue
        por_id = {str(d.get("id")): d for d in dados[chave] if isinstance(d, dict)}
        novos = [{**por_id[antigo], "id": novo} for novo, antigo in mapa.items() if antigo in por_id]
        return "```json\n" + json.dumps({chave: novos}, ensure_ascii=False) + "\n```"
    return saida or ""


def reavaliar(st: Dict[str, Any], gate: str, documentos: Optional[Sequence[str]] = None,
              juiz: Optional[str] = None, trocas_no_item: Optional[Dict[str, str]] = None,
              ) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """`(itens, resultado)` da fidelidade `gate` sobre o estado `st`, com a resposta gravada do juiz (ou `juiz`).

    `trocas_no_item` (mutante): `{trecho: novo}` troca o texto do item que tem o trecho depois de casado com o id
    gravado — o juiz responde pelo item como respondeu ao original."""
    from pipeline.reexecucao import PREFIXO_VERSAO_ANTERIOR, texto_do_pedido
    from tools import fidelidade as fid

    k_juiz, k_int, k_rel, docs_padrao, etapas, parcial, com_briefing, etapa = GATES[gate]
    documentos = list(documentos or docs_padrao or documentos_do_design())
    pedidos = [(str(p.get("origem") or "pedido"), str(p.get("texto") or "")) for p in st.get("pedidos_do_po") or []
               if isinstance(p, dict) and str(p.get("etapa") or "") in etapas]
    # o pedido corrente do estado final é o da última correção: conta só se ela foi desta etapa
    corrente = texto_do_pedido(str(st.get("pedido_correcao") or ""))
    simples = lambda t: re.sub(r"\s+", " ", (t or "").lower()).strip()  # noqa: E731 — o mesmo do agente
    if (str(st.get("etapa_da_correcao") or "") in etapas and corrente.strip()
            and not any(simples(t)[:200] in simples(corrente) for _, t in pedidos)):
        pedidos.append(("pedido de correção desta execução", corrente))
    itens = fid.montar_checklist(pedidos, str(st.get("briefing") or "") if com_briefing else "")
    gravadas = _linhas_do_relatorio(str(st.get(k_rel) or ""))
    mapa: Dict[str, str] = {}
    for it in itens:
        antigo = _id_gravado(gravadas, it["texto"], list(mapa.values()))
        if antigo:
            mapa[it["id"]] = antigo
    for trecho, novo in (trocas_no_item or {}).items():
        it = item(itens, trecho)
        it["texto"] = it["texto"].replace(trecho, novo)
    docs = {k: str(st.get(k) or "") for k in documentos if str(st.get(k) or "").strip()}
    anteriores = {k: str(st.get(f"{PREFIXO_VERSAO_ANTERIOR}{k}") or "") for k in docs}
    correntes = ({o for o, t in pedidos if simples(t)[:200] in simples(corrente)} | {"pedido de correção desta execução"}
                 if corrente.strip() else None)
    edicoes = list(st.get("edicoes_pontuais") or []) if st.get("modo_correcao") == "pontual" else None
    resultado = fid.aplicar(itens, _remapear(juiz if juiz is not None else str(st.get(k_juiz) or ""), "decisoes", mapa),
                            docs, etapa=etapa, parcial=parcial, anteriores=anteriores, edicoes=edicoes,
                            origens_correntes=correntes,
                            interpretacao=fid.interpretacao(_remapear(str(st.get(k_int) or ""), "itens", mapa), itens))
    return itens, resultado


def item(itens: List[Dict[str, str]], trecho: str) -> Dict[str, str]:
    """O item do checklist que contém o trecho. Trecho que nenhum item tem é erro do gabarito."""
    alvo = _simples(trecho)
    achados = [i for i in itens if alvo in _simples(i["texto"])]
    assert achados, f"nenhum item do checklist tem «{trecho}»"
    return achados[0]


def codigos_do_item(resultado: Dict[str, Any], id_: str) -> List[Tuple[str, str]]:
    """`[(codigo, severidade)]` dos achados do item."""
    return [(a["codigo"], a["severidade"]) for a in resultado["achados"] if a["id"] == id_]


def prova_do_item(resultado: Dict[str, Any], id_: str) -> Optional[str]:
    return next((c["prova"] for c in resultado["conferidos"] if c["id"] == id_), None)


def fora_do_recorte(resultado: Dict[str, Any], id_: str) -> bool:
    return any(f["id"] == id_ for f in resultado.get("fora_do_recorte") or [])


def juiz_alterado(st: Dict[str, Any], gate: str, trecho: str, **campos: Any) -> str:
    """A resposta gravada do juiz com a decisão do item que tem o trecho alterada (mutante). O id é o gravado, achado
    pela linha do relatório."""
    k_juiz, _, k_rel = GATES[gate][:3]
    antigo = _id_gravado(_linhas_do_relatorio(str(st.get(k_rel) or "")), trecho)
    assert antigo, f"o relatório gravado não tem «{trecho}»"
    saida = str(st.get(k_juiz) or "")
    for bruto in reversed(re.findall(r"```json\s*(.*?)```", saida, re.S)):
        try:
            dados = json.loads(bruto)
        except json.JSONDecodeError:
            continue
        if isinstance(dados, dict) and isinstance(dados.get("decisoes"), list):
            for d in dados["decisoes"]:
                if isinstance(d, dict) and str(d.get("id")) == antigo:
                    d.update(campos)
            return "```json\n" + json.dumps(dados, ensure_ascii=False) + "\n```"
    raise AssertionError("resposta do juiz sem decisões")
