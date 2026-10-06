"""A conta da virada fecha? O núcleo declara o ranking antes e depois; o código refaz a conta.

Na missão do 9º ano (06/10/2026) a IA simulada recomendava um projeto pelo "menor custo por vaga" e,
com os cadernos de campo, a recomendação se invertia "mantendo os mesmos critérios". Com R$ 12.000 para
24, 18 ou 20 vagas, o projeto que deveria perder (Mesa Aberta, R$ 500 por vaga) já vencia por custo
ANTES de qualquer caderno aparecer: a virada não fechava. O juiz de profundidade deu nota 4 à virada
citando justamente "pelo custo operacional relativo" — ninguém fez a conta.

Agora o núcleo escreve a tabela **1.3 · Conta da virada**:

    | Opção | Critério | Melhor quando | Peso | Antes | Depois |
    |---|---|---|---|---|---|
    | Mesa Aberta | custo por vaga (R$) | menor | 1 | 500 | 500 |
    | Mesa Aberta | atendimentos comprovados | maior | 2 | 0 | 360 |
    ...
    **Vencedor antes:** Conexão para Continuar · **Vencedor depois:** Mesa Aberta

ou, quando a missão não tem ranking, `**Não se aplica:** <por quê>`. O código normaliza cada critério
entre as opções (0 a 1, no sentido do "melhor quando"), soma com os pesos e cobra:

1. o vencedor calculado é o declarado, antes e depois;
2. antes e depois têm vencedores diferentes (senão não há virada);
3. critérios e pesos são os mesmos nas duas colunas: só os valores mudam (é a mesma linha).
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

_RE_SECAO = re.compile(r"^#{2,4}\s*1\.3\b[^\n]*$(.*?)(?=^#{1,4}\s|\Z)", re.M | re.S)
_RE_NAO_SE_APLICA = re.compile(r"\*\*\s*N[ãa]o se aplica\s*:?\s*\*\*\s*:?\s*(.+)", re.I)
_RE_VENCEDOR = re.compile(r"\*\*\s*Vencedor\s+(antes|depois)\s*:?\s*\*\*\s*:?\s*([^·*\n|]+)", re.I)
_RE_NUMERO = re.compile(r"-?\d[\d.]*(?:,\d+)?")


def _norm(texto: str) -> str:
    sem = "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[`*_]", "", sem)).strip(" .")


def _numero(celula: str) -> Optional[float]:
    m = _RE_NUMERO.search((celula or "").replace(" ", ""))
    if not m:
        return None
    bruto = m.group(0)
    # 12.000 é milhar; 12,5 é decimal
    if "," in bruto:
        bruto = bruto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", bruto):
        bruto = bruto.replace(".", "")
    try:
        return float(bruto)
    except ValueError:
        return None


def _linhas_da_tabela(bloco: str) -> List[List[str]]:
    linhas = []
    for linha in bloco.splitlines():
        linha = linha.strip()
        if not linha.startswith("|") or re.fullmatch(r"\|[\s:|-]+\|?", linha):
            continue
        linhas.append([c.strip() for c in linha.strip("|").split("|")])
    return linhas


def extrair(nucleo: str) -> Dict[str, Any]:
    """`{presente, nao_se_aplica, linhas, vencedores}` da seção 1.3 do núcleo."""
    m = _RE_SECAO.search(nucleo or "")
    if not m:
        return {"presente": False}
    bloco = m.group(1)
    na = _RE_NAO_SE_APLICA.search(bloco)
    tabela = _linhas_da_tabela(bloco)
    linhas = []
    if tabela:
        cab = [_norm(c) for c in tabela[0]]
        idx = {nome: next((i for i, c in enumerate(cab) if c.startswith(nome)), None)
               for nome in ("opcao", "criterio", "melhor", "peso", "antes", "depois")}
        if all(v is not None for v in idx.values()):
            for row in tabela[1:]:
                if len(row) < len(cab):
                    continue
                linhas.append({"opcao": row[idx["opcao"]], "criterio": row[idx["criterio"]],
                               "melhor": _norm(row[idx["melhor"]]), "peso": _numero(row[idx["peso"]]),
                               "antes": _numero(row[idx["antes"]]), "depois": _numero(row[idx["depois"]])})
    vencedores = {fase.lower(): nome.strip() for fase, nome in _RE_VENCEDOR.findall(bloco)}
    return {"presente": True, "nao_se_aplica": (na.group(1).strip() if na else ""), "linhas": linhas,
            "tem_tabela": bool(tabela), "vencedores": vencedores}


def ranking(linhas: List[Dict[str, Any]], fase: str) -> List[Tuple[str, float]]:
    """Pontuação de cada opção na fase (`antes` | `depois`), da maior para a menor."""
    por_criterio: Dict[str, List[Dict[str, Any]]] = {}
    for l in linhas:
        por_criterio.setdefault(_norm(l["criterio"]), []).append(l)
    pontos: Dict[str, float] = {}
    for grupo in por_criterio.values():
        valores = [l[fase] for l in grupo if l[fase] is not None]
        for l in grupo:
            pontos.setdefault(l["opcao"], 0.0)
        if not valores or max(valores) == min(valores):
            continue
        menor, maior = min(valores), max(valores)
        for l in grupo:
            if l[fase] is None:
                continue
            frac = (l[fase] - menor) / (maior - menor)
            if l["melhor"].startswith("menor"):
                frac = 1 - frac
            pontos[l["opcao"]] += frac * (l["peso"] if l["peso"] is not None else 1.0)
    return sorted(pontos.items(), key=lambda kv: -kv[1])


def validar(nucleo: str) -> Dict[str, Any]:
    dados = extrair(nucleo)
    achados: List[Dict[str, str]] = []

    def falha(codigo: str, resumo: str, severidade: str = "bloqueio") -> None:
        achados.append({"severidade": severidade, "codigo": codigo, "etapa": "produto", "resumo": resumo})

    calculo: Dict[str, Any] = {}
    if not dados["presente"]:
        falha("conta-ausente", "O núcleo não tem a seção **1.3 · Conta da virada**. Escreva a tabela do ranking antes e "
                               "depois (ou `**Não se aplica:** <por quê>`, se a missão não tem ranking).")
    elif dados["nao_se_aplica"] and not dados["linhas"]:
        if len(dados["nao_se_aplica"].split()) < 6:
            falha("nao-se-aplica-sem-motivo", "A 1.3 diz que não se aplica sem dizer por quê.", "atencao")
    elif not dados["linhas"]:
        falha("tabela-ilegivel", "A 1.3 existe, mas a tabela não tem as colunas `Opção | Critério | Melhor quando | Peso | "
                                 "Antes | Depois` com números — o código não consegue refazer a conta.")
    else:
        linhas = dados["linhas"]
        semnum = [l for l in linhas if l["antes"] is None or l["depois"] is None]
        if semnum:
            falha("valor-sem-numero", f"{len(semnum)} linha(s) da 1.3 sem número em Antes ou Depois "
                                      f"(ex.: {semnum[0]['opcao']} · {semnum[0]['criterio']}).")
        sentidos = {_norm(l["criterio"]): l["melhor"] for l in linhas}
        for crit, sentido in sentidos.items():
            if not (sentido.startswith("maior") or sentido.startswith("menor")):
                falha("sentido-indefinido", f"O critério «{crit}» não diz se ganha o maior ou o menor valor.")
        antes, depois = ranking(linhas, "antes"), ranking(linhas, "depois")
        calculo = {"antes": antes, "depois": depois}
        venc = dados["vencedores"]
        for fase, rk in (("antes", antes), ("depois", depois)):
            declarado = venc.get(fase, "")
            if not rk:
                continue
            if not declarado:
                falha("vencedor-nao-declarado", f"A 1.3 não declara o **Vencedor {fase}**.")
                continue
            calculado = rk[0][0]
            if len(rk) > 1 and abs(rk[0][1] - rk[1][1]) < 1e-9:
                falha("empate", f"{fase.capitalize()} da virada há empate entre {rk[0][0]} e {rk[1][0]}: a IA da missão "
                                f"não teria o que recomendar.")
            elif _norm(calculado) not in _norm(declarado):
                falha("conta-nao-fecha",
                      f"Com os critérios e pesos da própria 1.3, o vencedor **{fase}** é **{calculado}**, não {declarado}. "
                      f"Pontuação: " + ", ".join(f"{o} {p:.2f}" for o, p in rk) + ". A virada só acontece se a conta mostrar.")
        if antes and depois and antes[0][0] == depois[0][0]:
            falha("sem-virada", f"Antes e depois o vencedor calculado é o mesmo ({antes[0][0]}): o dado que faltava não "
                                f"muda a recomendação, então não há virada.")
    status = "bloqueado" if any(a["severidade"] == "bloqueio" for a in achados) else ("amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados, "calculo": calculo, "dados": dados}


def relatorio(resultado: Dict[str, Any], missao: str = "") -> str:
    icone = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}[resultado["status"]]
    linhas = [f"# Conta da virada{f' — {missao}' if missao else ''}", "", f"**Veredito: {icone}**", ""]
    calc = resultado.get("calculo") or {}
    if calc:
        linhas += ["| Fase | Ranking calculado pelo código |", "|---|---|"]
        for fase in ("antes", "depois"):
            linhas.append(f"| {fase} | " + " > ".join(f"{o} ({p:.2f})" for o, p in calc.get(fase, [])) + " |")
        linhas.append("")
    if resultado["achados"]:
        linhas += ["## Achados", ""]
        linhas += [f"- {'🔴' if a['severidade'] == 'bloqueio' else '🟡'} `{a['codigo']}` — {a['resumo']}" for a in resultado["achados"]]
        linhas += ["", "Corrija o mecanismo, não só a tabela: se a conta não fecha, a virada que o estudante vai ver também "
                   "não fecha. Mudar critério, peso ou o dado que falta é decisão de desenho — registre na 18-parcial.", ""]
    env = {"agente": "mecanica-check", "missao": missao, "status": resultado["status"], "achados": resultado["achados"],
           "precisa_humano": False}
    linhas += ["```json", json.dumps(env, ensure_ascii=False, indent=1), "```", ""]
    return "\n".join(linhas)
