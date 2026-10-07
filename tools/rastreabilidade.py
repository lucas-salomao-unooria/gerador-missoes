"""Matriz de rastreabilidade: cada requisito do produto, em cada artefato que precisa carregá-lo.

O PO aprova o one-pager e a spec; design e dev reescrevem, resumem e traduzem esse conteúdo dez vezes
até o PRD. Cada passagem tinha a sua conferência — ou não tinha — e ninguém respondia a pergunta que
importa: **o que o produto especificou chegou inteiro ao fim?** A auditoria de 07/10/2026 achou o
roteiro do podcast reescrito na copy e no banco, a pergunta 3 do debate apagada na consolidação da
spec, telas do professor fora do Stitch, 0 de 17 estados da spec no PRD — cada perda num documento
diferente, nenhuma num lugar que o PO lê.

Aqui os requisitos saem do one-pager aprovado e da spec, por código (habilidades, textos literais do
PO, tempo em tela, seção do DS fixada, estados, eventos, decisões a revisar) e do inventário de telas
da jornada; e cada um é procurado, por fato, em cada artefato a jusante que tem de carregá-lo. A matriz
diz onde cada requisito chegou e onde se perdeu, com o dono do conserto. Artefato que ainda não existe
(a etapa não rodou) fica `—`, não ❌.

Fronteira (a mesma de `tools/bncc.py`): só se confere presença verificável — código, texto literal,
identificador. Se a tela *exercita* a habilidade é julgamento, e fica com os pareceres.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

AGENTE = "rastreabilidade"

#: Coluna → (chave do estado, rótulo, dono do conserto).
ARTEFATOS: Tuple[Tuple[str, str, str, str], ...] = (
    ("spec", "spec_missao", "Spec", "spec-missao"),
    ("jornada", "jornada_telas", "Jornada", "jornada"),
    ("fluxo", "fluxo_arestas", "Fluxo", "fluxo"),
    ("copy", "copy_strings_revisada", "Copy", "copy-ptbr-revisao"),
    ("telas", "wireframes_cobertura", "Telas", "telas"),
    ("prototipo", "prototipo_arquivo", "Protótipo", "prototipo"),
    ("stitch", "stitch_links", "Stitch", "telas"),
    ("handoff", "handoff_dev", "Handoff", "handoff-dev"),
    ("banco", "banco_conteudo", "Banco", "banco-conteudo"),
    ("prd", "prd_final", "PRD", "prd-writer"),
    ("pedagogico", "one_pager_pedagogico", "Pedagógico", "one-pager-pedagogico"),
)
_COLUNA = {c: (chave, rotulo, dono) for c, chave, rotulo, dono in ARTEFATOS}

#: Categoria → (rótulo, colunas onde o requisito TEM de estar, severidade da falta).
CATEGORIAS: Dict[str, Tuple[str, Tuple[str, ...], str]] = {
    "habilidade": ("Habilidade BNCC (one-pager §2)", ("spec", "jornada", "handoff", "prd", "pedagogico"), "bloqueio"),
    "canal_b": ("Canal B literal (one-pager §12a)", ("spec", "copy", "prototipo", "prd", "pedagogico"), "bloqueio"),
    "roteiro": ("Pergunta do debate literal (one-pager §9)", ("spec", "copy", "prd", "pedagogico"), "bloqueio"),
    "podcast": ("Fala do podcast literal (one-pager §11)", ("copy", "banco", "prd"), "bloqueio"),
    "tempo": ("Tempo em tela (one-pager §10)", ("spec", "prd", "pedagogico"), "bloqueio"),
    "secao_ds": ("Seção do DS fixada pelo briefing", ("spec", "handoff", "prd"), "bloqueio"),
    "tela": ("Tela do inventário (jornada)", ("fluxo", "copy", "telas", "prototipo", "stitch", "handoff", "prd"), "bloqueio"),
    "estado": ("Estado do contrato (spec bloco 2)", ("fluxo", "prd"), "atencao"),
    "evento": ("Evento de telemetria (spec 9.4)", ("handoff", "prd"), "atencao"),
    "proposta": ("Decisão do agente a revisar ([PROPOSTA])", ("prd",), "atencao"),
}

_RE_ESTADO = re.compile(r"\b[EF]\d_[A-Z0-9_]{3,}\b")


def _secao_md(texto: str, rx: str) -> str:
    """Do título que casa `rx` até o próximo título de nível igual ou maior."""
    m = re.search(rf"^(#{{1,6}})[^\n]*{rx}[^\n]*$", texto or "", re.I | re.M)
    if not m:
        return ""
    nivel = len(m.group(1))
    fim = re.search(rf"^#{{1,{nivel}}}\s", texto[m.end():], re.M)
    return texto[m.end(): m.end() + fim.start()] if fim else texto[m.end():]


def estados_da_spec(spec: str) -> List[str]:
    """Os estados nomeados no «Contrato de estados» da spec (`E2_PRONTO_APOSTA`)."""
    vistos: List[str] = []
    for e in _RE_ESTADO.findall(_secao_md(spec, r"contrato de estados")):
        if e not in vistos:
            vistos.append(e)
    return vistos


def eventos_da_spec(spec: str) -> List[str]:
    """`verbo · objeto` da tabela de eventos (9.4) da spec, lida pelo nome das colunas."""
    bloco = _secao_md(spec, r"tabela de eventos") or _secao_md(spec, r"9\.4")
    cabecalho: List[str] = []
    eventos: List[str] = []
    for linha in bloco.splitlines():
        s = linha.strip()
        if not s.startswith("|") or re.fullmatch(r"\|[\s:|-]+\|?", s):
            continue
        celulas = [c.strip().strip("`* ") for c in s.strip("|").split("|")]
        if not cabecalho:
            cabecalho = [c.lower() for c in celulas]
            continue
        d = dict(zip(cabecalho, celulas))
        verbo, objeto = d.get("verbo", ""), d.get("objeto", "")
        if objeto and f"{verbo} · {objeto}" not in eventos:
            eventos.append(f"{verbo} · {objeto}")
    return eventos


_RE_ID_DECISAO = re.compile(r"\b(?:PQ-\d+|D0-\d+|KPI-\d+|P0[ab]|RF-\d+|T\d{1,2})\b")


def propostas_da_spec(spec: str) -> List[str]:
    """Cada `[PROPOSTA …]` da spec pelo identificador da linha (`PQ-03`), ou pelo texto da linha sem o marcador."""
    from tools.decisoes import RE_PROPOSTA

    saida: List[str] = []
    for linha in (spec or "").splitlines():
        if not RE_PROPOSTA.search(linha):
            continue
        ids = _RE_ID_DECISAO.findall(linha)
        alvo = ids[0] if ids else re.sub(r"\s+", " ", RE_PROPOSTA.sub("", linha)).strip(" |*-")[:80]
        if alvo and alvo not in saida:
            saida.append(alvo)
    return saida


def requisitos(state: Dict[str, Any]) -> List[Dict[str, str]]:
    """Os requisitos do produto, cada um com id estável, categoria e o texto a procurar."""
    from tools import conteudo_aprovado as ca
    from tools import telas
    from tools.rastro import secao_travada

    one_pager = str(state.get("one_pager") or "")
    spec = str(state.get("spec_missao") or "")
    reqs: List[Dict[str, str]] = []

    def req(categoria: str, texto: str) -> None:
        n = sum(1 for r in reqs if r["categoria"] == categoria) + 1
        reqs.append({"id": f"{categoria.upper()}-{n:02d}", "categoria": categoria, "texto": texto})

    for c in ca.codigos_aprovados(one_pager):
        req("habilidade", c)
    lit = ca.literais(one_pager)
    for qual in ("canal_b", "roteiro", "podcast"):
        for t in lit.get(qual) or []:
            req(qual, t)
    tempo = ca.tempo_aprovado(one_pager)
    if tempo:
        req("tempo", str(tempo))
    trava = secao_travada(str(state.get("briefing") or ""))
    if trava:
        req("secao_ds", trava["secao"])
    for t in telas.inventario(str(state.get("jornada_telas") or ""))["telas"]:
        req("tela", t["id"])
    for e in estados_da_spec(spec):
        req("estado", e)
    for e in eventos_da_spec(spec):
        req("evento", e)
    for p in propostas_da_spec(spec):
        req("proposta", p)
    return reqs


def _presente(categoria: str, alvo: str, coluna: str, texto: str) -> bool:
    from tools import conteudo_aprovado as ca
    from tools import telas

    if categoria in ("canal_b", "roteiro", "podcast"):
        fonte = ca._texto_visivel(texto) if coluna == "prototipo" else texto
        return not ca.literais_ausentes(fonte, [alvo])
    corpo = ca.remover_anexo(texto) if coluna in ("prd", "pedagogico") else texto
    if categoria == "tempo":
        return bool(re.search(rf"(?<!\d){re.escape(alvo)}\s*(?:min|minutos)\b", corpo, re.I))
    if categoria == "secao_ds":
        return alvo in corpo.lower()
    if categoria == "tela":
        if coluna == "prototipo":
            quadros = telas.quadros_do_prototipo(corpo)
            return alvo in quadros if quadros else alvo in telas.ids(corpo)
        return alvo in telas.ids(corpo)
    if categoria == "evento":
        return alvo.split(" · ", 1)[-1] in corpo
    if categoria == "proposta":
        # a proposta continua marcada no PRD (o marcador na mesma linha do identificador) ou está na seção de
        # decisões a revisar; o PRD da exp01ef1b trouxe os KPI de PQ-02..05 sem o marcador da spec
        secao_revisar = _secao_md(corpo, r"decis[õo]es do agente|a revisar")
        if alvo in secao_revisar:
            return True
        return any(alvo in l and "PROPOSTA" in l.upper() for l in corpo.splitlines())
    return alvo in corpo  # habilidade, estado


def matriz(state: Dict[str, Any]) -> Dict[str, Any]:
    """`{status, requisitos, celulas, cobertura, achados}` — célula é True, False ou None (artefato ausente)."""
    reqs = requisitos(state)
    textos = {c: str(state.get(chave) or "") for c, chave, _, _ in ARTEFATOS}
    celulas: Dict[str, Dict[str, Optional[bool]]] = {}
    for r in reqs:
        celulas[r["id"]] = {c: (_presente(r["categoria"], r["texto"], c, textos[c]) if textos[c].strip() else None)
                            for c in CATEGORIAS[r["categoria"]][1]}
    achados: List[Dict[str, str]] = []
    cobertura: Dict[str, Dict[str, Any]] = {}
    for categoria, (rotulo, colunas, severidade) in CATEGORIAS.items():
        do_tipo = [r for r in reqs if r["categoria"] == categoria]
        if not do_tipo:
            continue
        cobertura[categoria] = {}
        for c in colunas:
            valores = [celulas[r["id"]][c] for r in do_tipo]
            cobertura[categoria][c] = None if all(v is None for v in valores) else (sum(1 for v in valores if v), len(do_tipo))
            faltando = [r for r in do_tipo if celulas[r["id"]][c] is False]
            if not faltando:
                continue
            _, rotulo_col, dono = _COLUNA[c]
            exemplos = "; ".join(f"`{r['id']}` «{r['texto'][:70]}»" for r in faltando[:6])
            achados.append({
                "severidade": severidade, "codigo": f"perdido-{categoria}-{c}",
                "etapa": "dev" if c in ("handoff", "banco", "prd", "pedagogico") else ("produto" if c == "spec" else "design"),
                "agente_responsavel": dono,
                "resumo": (f"{len(faltando)} de {len(do_tipo)} — {rotulo} — não chegaram a «{rotulo_col}»: {exemplos}"
                           + ("…" if len(faltando) > 6 else "") + "."),
            })
    status = ("bloqueado" if any(a["severidade"] == "bloqueio" for a in achados)
              else ("amarelo" if achados else "aprovado"))
    return {"status": status, "requisitos": reqs, "celulas": celulas, "cobertura": cobertura, "achados": achados}


def relatorio(resultado: Dict[str, Any], missao: str = "") -> str:
    icone = {"aprovado": "🟢 TUDO O QUE O PRODUTO ESPECIFICOU CHEGOU", "amarelo": "🟡 CHEGOU, COM RESSALVAS",
             "bloqueado": "🔴 HÁ REQUISITO PERDIDO NO CAMINHO"}[resultado["status"]]
    colunas = [c for c, _, _, _ in ARTEFATOS if any(c in l for l in resultado["cobertura"].values())]
    rotulos = {c: r for c, _, r, _ in ARTEFATOS}
    linhas = [f"# Matriz de rastreabilidade — {missao or 'missão'}", "", f"**Veredito: {icone}**", "",
              f"{len(resultado['requisitos'])} requisito(s) do one-pager aprovado, da spec e do inventário de telas, "
              "procurados por fato em cada artefato que tem de carregá-los. `—` = artefato ainda não produzido; "
              "célula vazia = o requisito não vai para esse artefato.", "",
              "| Requisito | " + " | ".join(rotulos[c] for c in colunas) + " |",
              "|---|" + "---|" * len(colunas)]
    for categoria, linha in resultado["cobertura"].items():
        celulas = []
        for c in colunas:
            if c not in linha:
                celulas.append("")
            elif linha[c] is None:
                celulas.append("—")
            else:
                feitos, total = linha[c]
                celulas.append(f"{'✅' if feitos == total else '❌'} {feitos}/{total}")
        linhas.append(f"| {CATEGORIAS[categoria][0]} | " + " | ".join(celulas) + " |")
    linhas.append("")
    if resultado["achados"]:
        linhas += ["## Onde se perdeu, e quem conserta", ""]
        for a in resultado["achados"]:
            marca = "⛔" if a["severidade"] == "bloqueio" else "⚠️"
            linhas.append(f"- {marca} (dono: `{a['agente_responsavel']}`) {a['resumo']}")
        linhas.append("")
    linhas += ["## Requisitos", "", "| ID | Requisito |", "|---|---|"]
    linhas += [f"| `{r['id']}` | {r['texto'][:140].replace('|', '/')} |" for r in resultado["requisitos"]]
    linhas += ["", "```json", json.dumps({"agente": AGENTE, "missao": missao, "status": resultado["status"],
                                          "achados": resultado["achados"], "precisa_humano": False},
                                         ensure_ascii=False, indent=2), "```"]
    return "\n".join(linhas)
