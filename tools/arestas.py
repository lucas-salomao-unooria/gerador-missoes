"""Arestas do fluxo e regras de habilitação das telas × bloco 2 da spec de produto. Determinístico, sem LLM.

PR 7 do plano «Produto dono do contrato» (docs/planos/2026-10-23-produto-dono-do-contrato.md), decisão D7: estados do
fluxo são detalhe de design. Decompor um estado da spec em telas e estados intermediários é livre — os 55 estados que
as specs não nomeiam, nas sessões de 23/10/2026, eram quase todos decomposição. O que não é livre é a guarda que muda o
que o aluno faz, decide ou vê em relação ao bloco 2 (mecânica): as mudanças reais de guarda foram três, duas delas na
exp02ef1b — A13 (`Pronto` OU fim do tempo, contra «conclusão das marcações e fim do tempo S1») e A20 (só segue com o
atributo «Criança lendo» selecionado, contra «confirmação bloqueada até seleção do atributo essencial»: travar na
resposta certa zera a dimensão D3, D11). A terceira, o StoryPoll da exp02em1b, está na própria spec — a decisão do PO de
21/10 se perdeu em produto (D12) —, e é a correção pontual de produto que a tira; não há divergência entre fluxo e spec
para acusar.

Duas regras, calibradas nas 15 missões do acervo de regressão (608 arestas, `tests/acervo`): pegam A13 e A20 e mais uma
aresta da exp02ef1b (A22, «toque no pictograma correto» na transferência, que a etapa 6 da spec deixa responder sem
acerto), e nada nas outras 14 missões.

- `guarda-exige-acerto`: a aresta do aluno — ou a regra «habilitado só …» da tela, na jornada e na cobertura das telas —
  só deixa seguir com a resposta certa («correto», «acerta», «na ordem exata», a opção nomeada entre aspas depois de
  «selecionado»), e a etapa dela no bloco 2 da spec não pede acerto em lugar nenhum (Apresenta, Ordena, Bloqueia,
  Garante). O que vem entre parênteses é comentário, não guarda («cobre pareamento correto»).
- `guarda-afrouxada`: a aresta chega a um estado do contrato de estados por «A OU B», e todo gatilho da spec que leva a
  esse estado é «A e B», sem «ou».

Cada achado sai como `[PROPOSTA — validar com PO: …]`, com dono PO: se a mudança deve valer, o PO a pede no Refazer, e a
triagem do PR 5 leva o item a produto; senão, o design segue a spec. Com ESTEIRA_ESTRITA bloqueia, como a mudança do
design no texto do Gate 0 (PR 2); sem ela, é decisão humana 🟡 no cartão do parecer de design.

Desde o PR 8 (decisão D8) a mesma régua vale para a Seção 5 da jornada: as regras e as fases do mini-jogo são da spec
(bloco 2), e a jornada só mapeia as telas para elas — regra ou fase que a spec não tem vira proposta
(`tools/ambiente.conferir_jornada`). Nas 12 jornadas do acervo a Seção 5 é «n/a — ambiente é app clonado».
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

AGENTE = "arestas-contrato"

#: A guarda que só deixa seguir com a resposta certa.
_RE_ACERTO = re.compile(
    r"(?<![\w-])(?:corret[oa]s?|acert(?:a|am|ar|ou|aram|ando|e|em)|ordem\s+(?:causal\s+)?exata|exat[oa]s?\s+(?:ordem|sequ\w+)|"
    r"resposta\s+(?:certa|esperada)|gabarito)\b", re.I)
#: A opção nomeada depois de «selecionado»: `com atributo essencial selecionado ("Criança lendo")`.
_RE_OPCAO_NOMEADA = re.compile(r"(?:selecionad|escolhid|marcad|assinalad)[oa]s?\s*\(?\s*[\"“«]([^\"”»\n]{1,60})[\"”»]",
                               re.I)
#: A etapa da spec pede acerto em algum lugar: a guarda que o exige não é mudança.
_RE_ACERTO_NA_SPEC = re.compile(r"corret|acert|exat|incorret|errad|gabarito|v[áa]lid", re.I)
#: A regra de habilitação de tela: «habilitado apenas após …», «só habilita quando …».
_RE_HABILITACAO = re.compile(r"habilit\w*", re.I)
_RE_NEGADA = re.compile(r"\b(?:nenhum|nenhuma|sem|n[ãa]o)\b[^.;|]{0,30}$", re.I)


def _sem_parenteses(texto: str) -> str:
    """O texto sem o que está entre parênteses — comentário da aresta («cobre pareamento correto»), não guarda. O
    parêntese com a opção entre aspas fica: `selecionado ("Criança lendo")` é a guarda."""
    return re.sub(r"\((?![^()]*[\"“«])[^()]*\)", " ", texto or "")


def _etapa(*textos: str) -> Optional[str]:
    for t in textos:
        m = re.search(r"\bE(\d)[-_](?:ALU|SIS)\b", t or "", re.I)
        if m:
            return m.group(1)
    return None


def _do_professor(*textos: str) -> bool:
    return any(re.search(r"PROF", t or "") for t in textos)


def etapas_da_spec(spec: str) -> Dict[str, str]:
    """`{número: texto}` de cada «### Etapa N» do bloco 2 da spec."""
    from tools import bncc

    bloco = bncc.secao_bloco(spec or "", 2) or ""
    return {m.group(1): m.group(2) for m in re.finditer(r"^#{2,5}\s*Etapa\s*(\d)[^\n]*\n(.*?)(?=^#{2,5}\s|\Z)", bloco,
                                                         re.M | re.S)}


def contrato_de_estados(spec: str) -> List[Dict[str, str]]:
    """As linhas da tabela do contrato de estados (as que têm coluna «Gatilho»)."""
    from tools.cobertura_design import _desembrulhar, tabelas

    linhas: List[Dict[str, str]] = []
    for cab, corpo in tabelas(_desembrulhar(spec or "")):
        if any(c.startswith("gatilho") for c in cab):
            linhas += corpo
    return linhas


def _nome(celula: str) -> str:
    return re.sub(r"[`*\s]", "", celula or "").lower()


def _destino(linha: Dict[str, str]) -> str:
    return _nome(next((v for k, v in linha.items() if k.startswith("estado seguinte") or k.startswith("estado destino")
                       or k.startswith("destino") or k.startswith("próximo") or k.startswith("proximo")), ""))


def arestas(fluxo: str) -> List[Dict[str, str]]:
    """As arestas das tabelas do fluxo: `{id, de, para, condicao}`."""
    from tools.cobertura_design import tabelas

    saida: List[Dict[str, str]] = []
    for cab, corpo in tabelas(fluxo or ""):
        if "de" not in cab or "para" not in cab:
            continue
        col_cond = next((c for c in cab if c.startswith("condi") or c.startswith("gatilho")), None)
        if not col_cond:
            continue
        col_id = cab[0]
        for linha in corpo:
            saida.append({"id": re.sub(r"[`*]", "", linha.get(col_id, "")).strip(), "de": linha.get("de", ""),
                          "para": linha.get("para", ""), "condicao": linha.get(col_cond, "")})
    return saida


def _exige_acerto(texto: str) -> Optional[str]:
    """O trecho que exige a resposta certa, ou None."""
    m = _RE_OPCAO_NOMEADA.search(texto or "")
    if m:
        return f"selecionado «{m.group(1).strip()}»"
    m = _RE_ACERTO.search(_sem_parenteses(texto))
    return m.group(0) if m else None


def regras_de_habilitacao(texto: str) -> List[Tuple[Optional[str], str, str]]:
    """`(etapa, trecho que exige acerto, linha)` das regras de habilitação de tela do aluno que só liberam com a resposta
    certa: «habilitado estritamente após a seleção das 2 evidências corretas». A etapa vem do ID de tela da linha ou do
    último ID de tela visto antes dela."""
    saida: List[Tuple[Optional[str], str, str]] = []
    etapa: Optional[str] = None
    professor = False
    for linha in (texto or "").splitlines():
        ids = re.findall(r"\bE(\d)[-_](ALU|SIS|PROF)[-_]\d{2}", linha, re.I)
        if ids:
            etapa, professor = ids[0][0], ids[0][1].upper() == "PROF"
        if professor or not etapa:
            continue
        for m in _RE_HABILITACAO.finditer(linha):
            clausula = re.split(r"[.;|]", linha[m.end():], maxsplit=1)[0]
            if not re.match(r"\s*(?:\w+\s+){0,3}?(?:ap[óo]s|quando|ao|com|se|at[ée]|somente|apenas|s[óo]|"
                            r"exclusivamente|estritamente)\b", clausula, re.I):
                continue
            trecho = _exige_acerto(clausula)
            if trecho and not _RE_NEGADA.search(clausula[: clausula.find(trecho)] if trecho in clausula else ""):
                saida.append((etapa, trecho, linha.strip()))
                break
    return saida


def _achado(codigo: str, resumo: str, estrito: bool, **extra: Any) -> Dict[str, Any]:
    return {"severidade": "bloqueio" if estrito else "decisao_humana", "codigo": codigo, "etapa": "design",
            "agente_responsavel": "PO", "resumo": resumo, **extra}


def _spec_de_produto(state: Dict[str, Any]) -> str:
    return str(state.get("spec_missao_gate0") or state.get("spec_missao") or "")


def validar(state: Dict[str, Any], estrito: bool = False) -> Dict[str, Any]:
    """`{status, achados, contagem}`: as arestas do fluxo e as regras de habilitação das telas contra o bloco 2."""
    spec = _spec_de_produto(state)
    fluxo = str(state.get("fluxo_arestas") or "")
    jornada = str(state.get("jornada_telas") or "")
    if not spec.strip() or not (fluxo.strip() or jornada.strip()):
        return {"status": "aprovado", "achados": [], "contagem": {"arestas": 0}}
    etapas = etapas_da_spec(spec)
    contrato = contrato_de_estados(spec)
    estados = {_destino(l) for l in contrato} | {_nome(next(iter(l.values()), "")) for l in contrato}
    achados: List[Dict[str, Any]] = []
    todas = arestas(fluxo)
    for a in todas:
        if _do_professor(a["de"], a["para"]):
            continue
        etapa = _etapa(a["de"], a["para"])
        trecho = _exige_acerto(a["condicao"])
        if trecho and etapa and not _RE_ACERTO_NA_SPEC.search(etapas.get(etapa, "")):
            achados.append(_achado(
                "guarda-exige-acerto",
                f"[PROPOSTA — validar com PO: a aresta {a['id']} ({a['de']} → {a['para']}) só deixa o aluno seguir com a "
                f"resposta certa — «{trecho}» em «{a['condicao'][:160]}» —, e a etapa {etapa} do bloco 2 da spec não pede "
                "acerto]. O aluno passa a não poder errar: a escolha deixa de medir (D11, a dimensão D3 da exp02ef1b). Se "
                "a mudança deve valer, o PO a pede no **Refazer** (a triagem leva o item a Produto); senão, o fluxo segue a "
                "spec e deixa escolher.", estrito, aresta=a["id"]))
            continue
        destino = _nome(a["para"])
        if destino in estados and re.search(r"\bOU\b|\bou\b", a["condicao"]):
            gatilhos = [l.get("gatilho", "") for l in contrato if _destino(l) == destino]
            if gatilhos and all(re.search(r"\s(?:e|E)\s", g) and not re.search(r"\bou\b", g, re.I) for g in gatilhos):
                achados.append(_achado(
                    "guarda-afrouxada",
                    f"[PROPOSTA — validar com PO: a aresta {a['id']} ({a['de']} → {a['para']}) chega a `{a['para'].strip('`')}` "
                    f"por «{a['condicao'][:160]}», com OU, e o contrato de estados da spec leva a esse estado só com "
                    f"«{gatilhos[0][:120]}»]. O aluno passa a seguir com uma das condições, não com as duas. Se a mudança "
                    "deve valer, o PO a pede no **Refazer** (a triagem leva o item a Produto); senão, a aresta segue o "
                    "gatilho da spec.", estrito, aresta=a["id"]))
    habilitacoes = 0
    for chave, rotulo in (("jornada_telas", "jornada"), ("wireframes_cobertura", "cobertura das telas")):
        for etapa, trecho, linha in regras_de_habilitacao(str(state.get(chave) or "")):
            habilitacoes += 1
            if etapa and not _RE_ACERTO_NA_SPEC.search(etapas.get(etapa, "")):
                achados.append(_achado(
                    "guarda-exige-acerto",
                    f"[PROPOSTA — validar com PO: a regra de habilitação da {rotulo} só libera o aluno com a resposta certa "
                    f"— «{trecho}» em «{linha[:160]}» —, e a etapa {etapa} do bloco 2 da spec não pede acerto]. Se deve "
                    "valer, o PO a pede no **Refazer**; senão, a tela habilita como a spec manda.", estrito))
    # PR 8: as regras e as fases do mini-jogo na jornada × as da spec (a jornada só mapeia as telas)
    from tools.ambiente import conferir_jornada

    jogo = conferir_jornada(spec, jornada, estrito=estrito)
    achados += jogo["achados"]
    status = ("bloqueado" if any(a["severidade"] == "bloqueio" for a in achados) else "amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados,
            "contagem": {"arestas": len(todas), "estados_do_contrato": len(estados), "etapas_da_spec": len(etapas),
                         "regras_de_habilitacao": habilitacoes, **jogo["contagem"]}}


def propostas(resultado: Dict[str, Any]) -> List[str]:
    """As propostas ao PO, uma por achado, para a seção do fluxo e o cartão."""
    return [a["resumo"].split("]", 1)[0] + "]" for a in resultado.get("achados") or [] if a["resumo"].startswith("[PROPOSTA")]


def relatorio(resultado: Dict[str, Any], missao: str = "") -> str:
    icone = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}[resultado["status"]]
    c = resultado.get("contagem") or {}
    L = [f"# Fluxo e telas × bloco 2 da spec — {missao or 'missão'}", "",
         f"**Veredito: {icone}** · {c.get('arestas', 0)} aresta(s) do fluxo e {c.get('regras_de_habilitacao', 0)} regra(s) "
         "de habilitação das telas conferidas contra a mecânica da spec de produto. Decompor estado é livre (D7); a guarda "
         "que muda o que o aluno faz, decide ou vê vai ao PO como proposta."
         + (f" Mini-jogo: {c.get('fases_da_jornada', 0)} fase(s) e {c.get('regras_da_jornada', 0)} regra(s) na jornada "
            f"contra {c.get('fases_da_spec', 0)} e {c.get('regras_da_spec', 0)} da spec (PR 8)."
            if c.get("fases_da_spec") or c.get("fases_da_jornada") or c.get("regras_da_jornada") else ""), ""]
    if not resultado["achados"]:
        L.append("- Nenhuma guarda muda o que a spec manda o aluno fazer: o fluxo só decompõe.")
    for a in resultado["achados"]:
        marca = "⛔" if a["severidade"] == "bloqueio" else "🧑"
        L.append(f"- {marca} `{a['codigo']}` — {a['resumo']}")
    envelope = {"agente": AGENTE, "missao": missao or "", "status": resultado["status"], "achados": resultado["achados"],
                "precisa_humano": bool(resultado["achados"])}
    return "\n".join(L) + "\n\n```json\n" + json.dumps(envelope, ensure_ascii=False) + "\n```\n"
