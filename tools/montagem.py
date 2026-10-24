"""PRD e handoff montam, não decidem. Determinístico, sem LLM.

PR 4 do plano «Produto dono do contrato» (docs/planos/2026-10-23-produto-dono-do-contrato.md), decisão D10: a fonte
da verdade para codar é a spec de produto mais o anexo de design, e o PRD deriva delas; divergência é defeito. Até
aqui, nenhum gate comparava os números e os textos do corpo do PRD com o contrato: o juiz de coerência (A117) deu 🟢 ao
PRD da exp02ef1b-4fd72a9a com a Hipótese 1 a 25% no corpo e a 30% no anexo (§17), e o PRD da exp06ef1b-53e011b6 saiu
sem o teto de 35 palavras do §15, que estava no one-pager, na spec, no D0 e no D9 (análise de 23/10/2026). O handoff
fazia o mesmo antes do PRD: reescrevia as hipóteses do §17 e propagava o número trocado.

Quatro conferências, no corpo (sem o anexo literal que a esteira cola no fim):

a) **número de regra e texto-chave com origem no contrato.** Todo número de regra (%, s, min, palavras com teto,
   contagens de opção) existe no contrato: one-pager, núcleo, briefing, spec de produto (a spec sem os blocos 13 e
   14), as linhas do bloco 13 cuja decisão passa pela lista branca do PR 2 (`tools/decisoes.py`) e as decisões do PO
   gravadas no de acordo (`estado.decisoes_do_po`, PR 3). Ficam de fora os de dono plataforma (polling, TTL, p95,
   uptime, lote da SDK, `px`), a medida de layout (`75% da tela`), a contagem de palavras de uma string e o que vem
   marcado `[PROPOSTA — validar com PO: …]`, que é proposta e não decisão. No handoff, o texto-chave do PO (Canal B,
   debate, texto de tela do §4) citado com outra redação também volta; no PRD isso já é o `literal-parafraseado` do
   A116.
b) **hipóteses, metas e tetos iguais aos do contrato.** O número de cada hipótese do §17 está na linha
   correspondente do corpo (H1 25×30 da exp02ef1b); o alvo e o limiar de decisão de cada KPI que cita uma `PQ-nn` são
   os da linha dela no 9f da spec; no PRD, cada teto do §15 está no corpo (as 35 palavras da exp06ef1b).
c) **estados da §6 iguais aos do contrato.** Todo estado do «Contrato de estados» da spec está nas colunas de estado
   e no diagrama da §6, e nenhum estado ali é inventado (o PRD da exp02ef1b trocou os 15 nomes do contrato por
   `desafiar`, `explicar_padroes`…, e largou `PROCESSANDO_RESPOSTA_VISITA`). Estado de decomposição que o fluxo do
   design nomeia não é invenção (D7: estado do fluxo é detalhe de design).
d) **decisão de design não vira origem de produto.** Número com origem citada em produto («(§17 do one-pager)»,
   «(spec, bloco 9f)») tem de estar lá; `[D0-n]` citado como «contratual», «do PO» ou com origem no one-pager é
   decisão do design vestida de produto. Até o PR 6, `produto/05-spec-missao.md › Bloco 13` (e o 14, que mora no mesmo
   arquivo) é citação legítima.

Divergência que o próprio contrato tem — o número do corpo também está no contrato, em outro lugar — não se resolve
no PRD: o corpo segue o one-pager, e o PRD só sai com ela registrada na seção 19 (no handoff, na seção 7) como
`[ABERTO — dono: produto: …]` com os dois valores. O rastro conta esse marcador como pendência de produto, e o PRD
continua não pronto até o PO decidir: a divergência vira item obrigatório da §19, com dono produto.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from tools.propagacao import (
    _fmt,
    bloco_13,
    contrato_no_corpo,
    numeros,
    spec_de_produto,
    tem_numero,
)

AGENTE = "montagem-dev"
#: Quem corrige cada documento.
DONO = {"prd": "prd-writer", "handoff": "handoff-dev"}

# --------------------------------------------------------------------------- o contrato
#: Documentos de produto, na ordem: o que o PO aprova e o que ele mesmo escreveu.
FONTES_DO_CONTRATO = ("one_pager", "nucleo_narrativo", "briefing", "one_pager_po", "spec_missao_gate0")


def _linhas_do_bloco_13(spec: str) -> Dict[str, str]:
    """`D0-n` → o texto da linha do bloco 13 (tabela ou parágrafo) que define a decisão."""
    saida: Dict[str, str] = {}
    atual: Optional[str] = None
    for linha in bloco_13(spec).splitlines():
        m = re.search(r"\[\s*D0-0*(\d+)\s*\]", linha)
        if m and (linha.lstrip().startswith(("|", "-", "*", "#", "[", "`")) or linha.count("|") >= 2):
            atual = f"D0-{int(m.group(1))}"
            saida[atual] = saida.get(atual, "") + linha + "\n"
        elif atual and linha.strip() and not linha.lstrip().startswith("#"):
            saida[atual] += linha + "\n"
        elif linha.lstrip().startswith("#"):
            atual = None
    return saida


def bloco_13_da_lista_branca(state: Dict[str, Any]) -> Tuple[str, List[str]]:
    """`(texto, ids_de_produto)`: as linhas do bloco 13 cujas decisões passam pela lista branca do PR 2, e os ids que
    não passam — classe de produto por prefixo ou fora da lista, ou [D0-n] que fecha [PARÂMETRO]/promove [PROPOSTA] da
    spec do Gate 0 sem parecer datado. O número que só uma decisão dessas tem não é contrato: é o design decidindo no
    lugar do PO (os 15 palavras, 10% e 45 s da exp02ef1b)."""
    from tools import decisoes as dec
    from tools.propagacao import _pareceres_texto, decisoes_d0

    linhas = _linhas_do_bloco_13(str(state.get("spec_missao") or ""))
    if not linhas:
        return "", []
    de_produto: Set[str] = set()
    for d in decisoes_d0(state):
        if d["classe"] not in ("", "?") and dec.classe_de_produto(d["classe"]):
            de_produto.add(d["id"])
    sem_parecer, _ = dec.decisoes_d0_de_produto(
        str(state.get("fechamento_lacunas") or ""), state.get("lacunas_status_envelope") or {},
        str(state.get("spec_missao_gate0") or ""), _pareceres_texto(state, None))
    for linha in sem_parecer:
        m = re.match(r"\[(D0-\d+)\]", linha)
        if m:
            de_produto.add(m.group(1))
    texto = "".join(t for i, t in linhas.items() if i not in de_produto)
    return texto, sorted(de_produto, key=lambda x: int(x.split("-")[1]))


def _texto_das_decisoes_do_po(decisoes_do_po: Optional[Sequence[Dict[str, Any]]]) -> str:
    """O valor que o PO aceitou ou escreveu no de acordo de produto — a mesma régua do lint de produto
    (`tools/contrato_produto._numeros_decididos`): o recusado não é contrato."""
    textos = []
    for d in decisoes_do_po or []:
        if not isinstance(d, dict):
            continue
        if d.get("resposta") == "outro":
            textos.append(str(d.get("valor") or ""))
        elif d.get("resposta") == "aceitar":
            textos.append(str(d.get("gravado") or ""))
    return "\n".join(textos)


def contrato(state: Dict[str, Any]) -> Dict[str, str]:
    """Os textos do contrato, por fonte: `spec_produto` é a `spec_missao` sem os blocos 13 e 14; `bloco_13` só as
    decisões da lista branca; `decisoes_do_po` o que o PO fixou no de acordo."""
    docs = {k: str(state.get(k) or "") for k in FONTES_DO_CONTRATO}
    docs["spec_produto"] = spec_de_produto(str(state.get("spec_missao") or ""))
    docs["bloco_13"], _ = bloco_13_da_lista_branca(state)
    docs["decisoes_do_po"] = _texto_das_decisoes_do_po(state.get("decisoes_do_po"))
    docs["perguntas_transversais"] = perguntas_transversais()
    return docs


#: Marcador aberto não é decisão: a sugestão dentro de `[PARÂMETRO — …, sugestão: 10%]` é do agente de produto, e o
#: número só vira contrato quando o PO a aceita no de acordo (PR 3). Os 10% da moldura, os 45 s e as 15 palavras da
#: exp02ef1b estavam só na sugestão — e o D0 os fechou no lugar do PO.
_RE_MARCADOR_ABERTO = re.compile(r"\[(?:PAR[ÂA]METRO|PROPOSTA)\b[^\]\n]*\]", re.I)


def texto_do_contrato(docs: Dict[str, str]) -> str:
    """O contrato num texto só, sem o conteúdo dos marcadores abertos."""
    return _RE_MARCADOR_ABERTO.sub(" ", "\n".join(docs.values()))


def perguntas_transversais() -> str:
    """As linhas `T*` do catálogo de perguntas de produto (`references/perguntas-de-produto.md`): a decisão de cada
    pergunta transversal é padrão da plataforma, e o KPI que a herda copia o corte dela («abaixo de 50%», T7)."""
    from pathlib import Path

    caminho = Path(__file__).resolve().parent.parent / "prompts" / "references" / "perguntas-de-produto.md"
    try:
        texto = caminho.read_text(encoding="utf-8")
    except OSError:
        return ""
    return "\n".join(l for l in texto.splitlines() if l.lstrip().startswith("| `T"))


def _spec_produto(state: Dict[str, Any]) -> str:
    """A spec de produto: a `spec_missao` sem os blocos 13 e 14 (a do Gate 0 quando a sessão não tem a consolidada)."""
    return spec_de_produto(str(state.get("spec_missao") or "")) or str(state.get("spec_missao_gate0") or "")


# --------------------------------------------------------------------------- texto do corpo
_RE_CERCA = re.compile(r"^\s*(```|~~~)")
#: Seções do PRD que não são corpo de requisito: a 19 (pendências, onde a divergência se registra) e a 22 (changelog).
_RE_TITULO_FORA = re.compile(r"^#{1,3}\s*\**\s*(?:19|22)\s*[.—–-]", re.I)
_RE_TITULO = re.compile(r"^#{1,6}\s")
#: Texto entre aspas e código em linha: copy citada e identificador não são número de regra (a copy da exp06ef1b
#: «75% dos projetos da feira ficaram fora do seu feed» é texto de tela, conferido como texto).
_RE_CITACAO = re.compile(r"«[^»\n]*»|“[^”\n]*”|\"[^\"\n]*\"|`[^`\n]*`")


def _linhas_do_corpo(texto: str, pular_secoes: bool = True) -> List[str]:
    """As linhas do corpo fora de bloco de código, sem a seção 19 nem a 22."""
    saida: List[str] = []
    cerca = False
    fora = False
    nivel_fora = 0
    for linha in (texto or "").splitlines():
        if _RE_CERCA.match(linha):
            cerca = not cerca
            continue
        if cerca:
            continue
        if _RE_TITULO.match(linha):
            nivel = len(linha) - len(linha.lstrip("#"))
            if pular_secoes and _RE_TITULO_FORA.match(linha):
                fora, nivel_fora = True, nivel
                continue
            if fora and nivel <= nivel_fora:
                fora = False
        if not fora:
            saida.append(linha)
    return saida


# --------------------------------------------------------------------------- a) número de regra com origem
#: Contexto de dono plataforma: o número é da infraestrutura, não da missão (ADR-93/94 para o polling; TTL do JWT do
#: hub; lote de 50 eventos / 10 s da SDK; Web Vitals; disponibilidade e latência). No acervo de 23/10/2026 eram 3 s de
#: polling em 5 dos 6 PRDs, TTL 15 min, LCP 2 s, uptime 99,5%.
_RE_PLATAFORMA = re.compile(
    r"polling|sondagem|\bTTL\b|\bJWT\b|token|\bLCP\b|\bINP\b|\bCLS\b|\bp9[59]\b|percentil|uptime|disponibilidade|"
    r"lat[êe]ncia|\b5xx\b|\b(?:HTTP|erro|status|c[óo]digo)\s*\d{3}\b|\b429\b|taxa de erro|erro t[ée]cnico|falha de (?:carregamento|renderiza)|web ?vitals|"
    r"amostragem|\blote\b|batch|timeout|tempo limite|retry|backoff|\bcache\b|RNF-(?:PERF|DISP|SEG)|"
    r"F5\b|recarreg|reconex|Cloud ?Run|\bCDN\b|bundle|\bKB\b|\bMB\b|throttl|debounce|quota|cota de IA|"
    # consulta periódica a uma rota é polling com outro nome («consultando `GET /juri-estadual/gate` a cada 3
    # segundos», PRD da exp06ef1b)
    r"\bGET\s+/|a cada \d+(?:[.,]\d+)?\s*(?:s\b|seg)|"
    # a origem declarada é a plataforma: «(contrato da plataforma)», «(ADR-105)»
    r"\bADR-\d|contrato da plataforma|\(plataforma\)", re.I)
#: Porcentagem de layout: o que a tela ocupa é desenho (a folha de 75% e o overlay de 70% da exp02ef1b). A área mínima
#: da moldura não entra aqui: os 10% da exp02ef1b são regra da mecânica, que o D0 decidiu no lugar do PO.
_RE_LAYOUT = re.compile(r"viewport|altura|largura|overlay|opacidade|cobr[ie]|ocupa|\bfolha\b|modal|drawer|"
                        r"sheet", re.I)
#: Palavras e caracteres só são regra quando a linha diz teto ou piso; «(13 palavras)» ao lado de uma string é medida.
_RE_TETO_OU_PISO = re.compile(r"m[áa]x|teto|limite|\bat[ée]\b|≤|<=|n[ãa]o (?:pode|deve)|exced|ultrapass|passa de|m[íi]nim|piso|≥|"
                              r">=|pelo menos|no m[íi]nimo", re.I)
#: Contagem de opções que é texto-chave (D1: nº de opções): «3 alternativas», «duas opções».
_NUMERO_POR_EXTENSO = {"um": "1", "uma": "1", "dois": "2", "duas": "2", "tres": "3", "três": "3", "quatro": "4",
                       "cinco": "5", "seis": "6", "sete": "7", "oito": "8", "nove": "9", "dez": "10"}
_RE_CONTAGEM = re.compile(r"(?<![\w.,])(\d{1,2}|um|uma|dois|duas|tr[êe]s|quatro|cinco|seis|sete|oito|nove|dez)\s+"
                          r"(op[çc](?:[ãa]o|[õo]es)|alternativas?|tentativas?|rodadas?)\b", re.I)
_RE_PROPOSTA = re.compile(r"\[PROPOSTA", re.I)


def _contagens(texto: str) -> List[Tuple[str, str]]:
    saida: List[Tuple[str, str]] = []
    for m in _RE_CONTAGEM.finditer(texto or ""):
        n = _NUMERO_POR_EXTENSO.get(m.group(1).lower(), m.group(1))
        if int(n) < 2:
            continue  # «uma alternativa», «selecionar uma opção»: artigo, não contagem
        nome = {"op": "opções", "al": "alternativas", "te": "tentativas", "ro": "rodadas"}[m.group(2).lower()[:2]]
        if (n, nome) not in saida:
            saida.append((n, nome))
    return saida


#: O formulário do preparo (disciplina, componente curricular) é o fluxo E0-PROF, fixo para toda missão: as «7 opções»
#: do dropdown de disciplinas não são o nº de opções da mecânica (handoff da exp06ef1b).
_RE_FORMULARIO_DO_PREPARO = re.compile(r"dropdown|lista suspensa|\bselect\b|disciplina|componente curricular", re.I)


def numeros_de_regra(linha: str) -> List[Tuple[str, str]]:
    """Os números de regra da linha, fora de citação e de código em linha: %, s, min e palavras ou caracteres com teto
    ou piso — sem os de plataforma, de layout e o 100%, que é «todos». Contagens de opção vêm à parte."""
    if _RE_PLATAFORMA.search(linha):
        return []
    limpa = _RE_CITACAO.sub(" ", linha)
    saida = []
    for n, u in numeros(limpa):
        if u == "px" or float(n) == 0 or (u == "%" and float(n) == 100):
            continue
        if u == "%" and _RE_LAYOUT.search(limpa):
            continue
        if u in ("palavras", "caracteres") and not _RE_TETO_OU_PISO.search(limpa):
            continue
        saida.append((n, u))
    return saida


def numeros_sem_origem(corpo: str, contrato_texto: str) -> List[Dict[str, str]]:
    """Cada número de regra do corpo que o contrato não tem, com a linha. A linha marcada `[PROPOSTA — validar com
    PO: …]` não decide: propõe, e a proposta chega ao PO pela seção 19.3."""
    saida: List[Dict[str, str]] = []
    vistos: Set[Tuple[str, ...]] = set()
    contagens_do_contrato = set(_contagens(contrato_texto))
    for linha in _linhas_do_corpo(corpo):
        if not linha.strip() or _RE_PROPOSTA.search(linha):
            continue
        for tok in numeros_de_regra(linha):
            if tok in vistos or tem_numero(contrato_texto, tok):
                continue
            vistos.add(tok)
            saida.append({"numero": _fmt(tok), "linha": re.sub(r"\s+", " ", linha).strip()[:180]})
        if _RE_PLATAFORMA.search(linha) or _RE_FORMULARIO_DO_PREPARO.search(linha):
            continue
        for tok in _contagens(_RE_CITACAO.sub(" ", linha)):
            if ("#",) + tok in vistos or tok in contagens_do_contrato:
                continue
            vistos.add(("#",) + tok)
            saida.append({"numero": f"{tok[0]} {tok[1]}", "linha": re.sub(r"\s+", " ", linha).strip()[:180]})
    return saida


# --------------------------------------------------------------------------- b) hipóteses, metas e tetos
#: O registro que o PRD faz da divergência que o contrato tem: o marcador que o rastro conta como pendência de produto.
_RE_REGISTRO_PRODUTO = re.compile(r"\[(?:ABERTO|LACUNA)\s*[—–-]\s*dono:\s*produto\b", re.I)


def _registro(secao_de_pendencias: str, *toks: Tuple[str, str]) -> Optional[str]:
    """A linha da seção de pendências com `[ABERTO — dono: produto …]` que traz todos os números dados."""
    for linha in (secao_de_pendencias or "").splitlines():
        if _RE_REGISTRO_PRODUTO.search(linha) and all(tem_numero(linha, t) for t in toks):
            return linha.strip()
    return None


def _tok(fmt: str) -> Tuple[str, str]:
    """`30%` / `35 palavras` → o token de `numeros`."""
    return numeros(fmt)[0] if numeros(fmt) else (fmt, "")


def hipoteses_e_tetos(one_pager: str, corpo: str, contrato_texto: str, pendencias: str,
                      exigir_tetos: bool = True) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """`(divergentes, registradas)`: números do §17 trocados no corpo e, com `exigir_tetos`, os do §15 ausentes ou
    trocados (régua do PR 1, `propagacao.contrato_no_corpo`). Trocado por um número que o contrato também tem é
    divergência do próprio contrato: passa se a seção de pendências a registra com dono produto e os dois valores.

    O handoff não repete os tetos nem as hipóteses (remete ao §17): nele só conta o trocado. A hipótese é comparada
    também item a item (`hipoteses_reescritas`): o handoff da exp02ef1b parafraseou a H1 inteira com 25%, e a linha
    não casava por palavras com a do §17."""
    corpo = "\n".join(_linhas_do_corpo(corpo))
    candidatos = [c for c in contrato_no_corpo(one_pager, corpo, secoes=(15, 17))
                  # a hipótese ausente do corpo não é número trocado: o PRD remete ao anexo, e o handoff ao §17
                  if not (c["situacao"] == "ausente" and (c["secao"] == "§17" or not exigir_tetos))]
    vistos = {(c["secao"], c["contrato"], c["corpo"]) for c in candidatos}
    for h in hipoteses_reescritas(one_pager, corpo):
        if not any(c["secao"] == "§17" and set(h["corpo"].split(", ")) <= set(c["corpo"].split(", "))
                   for c in candidatos) and (h["secao"], h["contrato"], h["corpo"]) not in vistos:
            candidatos.append(h)
    divergentes, registradas = [], []
    for c in candidatos:
        item = {**c}
        if c["situacao"] in ("trocado", "acrescentado"):
            corpo_toks = [_tok(x.strip()) for x in c["corpo"].split(",")]
            if c["situacao"] == "trocado" and all(tem_numero(contrato_texto, t) for t in corpo_toks):
                linha = _registro(pendencias, *[_tok(x.strip()) for x in c["contrato"].split(",")], *corpo_toks)
                if linha:
                    registradas.append({**item, "registro": linha[:180]})
                    continue
                item["no_contrato"] = "sim"
        divergentes.append(item)
    return divergentes, registradas


_RE_TITULO_HIPOTESE = re.compile(r"^(#{1,6})\s+.*hip[óo]tese", re.I)


def _itens_de_hipotese(texto: str) -> Dict[int, str]:
    """Número da hipótese → o texto dela (a linha que a abre e as que vêm abaixo, mais recuadas). O número sai de
    «Hipótese 1», «(H1)» ou do «1.» da lista (o §17 da exp07ef1b)."""
    saida: Dict[int, str] = {}
    atual: Optional[int] = None
    recuo_atual = 0
    for linha in (texto or "").splitlines():
        if not linha.strip():
            continue
        recuo = len(linha) - len(linha.lstrip())
        cabeca = linha.strip()[:90]
        # «Hipótese de Usabilidade Motora (H1): Duplas de 7 a 8 anos» (handoff da exp02ef1b): o número é o do H1, não o
        # primeiro que aparece
        m_h = re.search(r"hip[óo]tese\s+(\d+)\b", cabeca, re.I) or re.search(r"\bH(\d+)\b", cabeca)
        m_n = re.match(r"^(\d+)[.)]\s", linha.strip())
        novo = None
        if (m_h or m_n) and (atual is None or recuo <= recuo_atual):
            novo = int(m_h.group(1) if m_h else m_n.group(1))
        if novo is not None:
            atual, recuo_atual = novo, recuo
            saida[atual] = saida.get(atual, "") + linha + "\n"
        elif atual is not None and recuo > recuo_atual:
            saida[atual] += linha + "\n"
        elif atual is not None and recuo <= recuo_atual:
            atual = None
    return saida


def _secoes_de_hipotese(corpo: str) -> str:
    """O texto das seções do corpo cujo título fala em hipótese (a 6 do handoff; a subseção da 2 do PRD)."""
    linhas = (corpo or "").splitlines()
    saida: List[str] = []
    nivel: Optional[int] = None
    for linha in linhas:
        m_t = _RE_TITULO.match(linha)
        if m_t:
            n = len(linha) - len(linha.lstrip("#"))
            if nivel is not None and n <= nivel:
                nivel = None
            if nivel is None and _RE_TITULO_HIPOTESE.match(linha):
                nivel = n
                continue
        if nivel is not None:
            saida.append(linha)
    return "\n".join(saida)


def _numeros_de_hipotese(texto: str) -> List[Tuple[str, str]]:
    return [t for t in numeros(_RE_CITACAO.sub(" ", texto)) if t[1] in ("%", "s", "min") and float(t[0]) not in (0, 100)]


def hipoteses_reescritas(one_pager: str, corpo: str) -> List[Dict[str, str]]:
    """Hipótese do corpo com número que a hipótese de mesmo número do §17 não tem: `trocado` quando a do §17 tem
    outro número da mesma unidade (H1: 30% no §17, 25% no handoff da exp02ef1b), `acrescentado` quando ela não
    quantifica e o corpo inventou a meta (H2 do mesmo handoff: «menos de 70%»)."""
    from tools.conteudo_aprovado import secao

    do_17 = _itens_de_hipotese(secao(one_pager or "", 17) or "")
    do_corpo = _itens_de_hipotese(_secoes_de_hipotese(corpo))
    saida = []
    for n, texto in do_corpo.items():
        if n not in do_17:
            continue
        aprovados = _numeros_de_hipotese(do_17[n])
        fora = [t for t in _numeros_de_hipotese(texto) if not tem_numero(do_17[n], t)]
        if not fora:
            continue
        mesma_unidade = [t for t in aprovados if t[1] in {u for _, u in fora}]
        linha_corpo = next((l for l in texto.splitlines() if any(tem_numero(l, t) for t in fora)), texto)
        saida.append({"secao": "§17", "situacao": "trocado" if mesma_unidade else "acrescentado",
                      "contrato": ", ".join(_fmt(t) for t in mesma_unidade) or "nenhum número",
                      "corpo": ", ".join(_fmt(t) for t in fora), "hipotese": f"H{n}",
                      "linha": do_17[n].strip().splitlines()[0][:200], "linha_corpo": linha_corpo.strip()[:200]})
    return saida


def _linhas_9f(spec: str) -> Dict[str, str]:
    """`PQ-nn` → a linha inteira dela no sub-bloco 9f da spec."""
    from tools.kpis import _RE_PQ, _pq_id, _tabelas

    saida: Dict[str, str] = {}
    for tabela in _tabelas(spec or "", {"pq", "pergunta"}):
        for linha in tabela:
            texto = " | ".join(linha.values())
            m = _RE_PQ.search(texto)
            if m:
                saida.setdefault(_pq_id(m.group(0)), texto)
    return saida


def _pct(texto: str) -> Set[str]:
    return {n for n, u in numeros((texto or "").replace("\\%", "%")) if u == "%"}


def metas_contra_9f(corpo: str, spec: str) -> List[Dict[str, str]]:
    """KPI que cita uma `PQ-nn` com alvo ou limiar de decisão (%) que não é o da linha dela no 9f. O `kpi-alvo-inventado`
    do A115 aceita qualquer número do §17 ou do 9f; aqui o número é o da própria pergunta."""
    from tools.kpis import _RE_PQ, _col, _pq_id, _tabelas

    nove_f = _linhas_9f(spec)
    if not nove_f:
        return []
    saida = []
    for tabela in _tabelas(corpo or "", {"kpi"}):
        for linha in tabela:
            pq = _RE_PQ.search(_col(linha, "pq") or "")
            if not pq or _pq_id(pq.group(0)) not in nove_f:
                continue
            pid = _pq_id(pq.group(0))
            da_spec = _pct(nove_f[pid])
            for coluna in ("alvo", "decis"):
                celula = _col(linha, coluna)
                if not celula or _RE_PROPOSTA.search(celula) or re.search(r"sem meta", celula, re.I):
                    continue
                fora = sorted(_pct(celula) - da_spec, key=float)
                if fora:
                    saida.append({"kpi": (_col(linha, "kpi") or "").strip("` "), "pq": pid, "coluna": coluna,
                                  "corpo": ", ".join(f"{n}%" for n in fora),
                                  "spec": ", ".join(f"{n}%" for n in sorted(da_spec, key=float)) or "nenhum",
                                  "celula": celula.strip()[:120]})
    return saida


# --------------------------------------------------------------------------- c) estados da §6
_RE_ID_ESTADO = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)*$")
_RE_MERMAID_ARESTA = re.compile(r"^\s*([\w\[\]*]+)\s*-->\s*([\w\[\]*]+)", re.M)
_RE_MERMAID_ESPECIAL = re.compile(r"^\s*state\s+(\w+)\s*(?:<<\w+>>|\{)", re.M)


def _estado_da_celula(celula: str) -> Optional[str]:
    """O estado de uma célula: o primeiro identificador entre crases, ou a célula inteira se ela é um identificador."""
    em_codigo = re.findall(r"`([^`\n]+)`", celula or "")
    alvo = (em_codigo[0] if em_codigo else (celula or "").strip("*_ ")).strip("*_ `")
    alvo = alvo.split()[0] if alvo.split() else ""
    return alvo if _RE_ID_ESTADO.match(alvo) and (("_" in alvo) or alvo.isupper() or em_codigo) else None


def estados_usados(texto: str, so_tabelas: bool = False) -> List[str]:
    """Os estados que o texto declara como estado: as colunas «Estado …» e «destino» das tabelas (menos a do nome do
    design no de-para) e os nós do `stateDiagram`, sem `[*]` nem nó de escolha ou composto."""
    from tools.cobertura_design import tabelas

    nomes: List[str] = []
    for cab, linhas in tabelas(texto or ""):
        colunas = [c for c in cab if (c.startswith("estado") or c.startswith("destino")) and "design" not in c]
        for linha in linhas:
            for col in colunas:
                e = _estado_da_celula(linha.get(col, ""))
                if e:
                    nomes.append(e)
    if not so_tabelas:
        especiais = set(_RE_MERMAID_ESPECIAL.findall(texto or ""))
        for a, b in _RE_MERMAID_ARESTA.findall(texto or ""):
            for e in (a, b):
                if e != "[*]" and e not in especiais and _RE_ID_ESTADO.match(e):
                    nomes.append(e)
    vistos: Set[str] = set()
    saida = []
    for n in nomes:
        if n.lower() not in vistos:
            vistos.add(n.lower())
            saida.append(n)
    return saida


def estados_contra_o_contrato(secao6: str, spec: str, design: str, exigir_todos: bool = True,
                              so_identificadores: bool = False) -> Tuple[List[str], List[str]]:
    """`(ausentes, inventados)`: os estados do contrato que a §6 não usa como estado e os que ela usa sem que o
    contrato nem o design os nomeiem. Estado de decomposição do fluxo do design não é inventado (D7)."""
    from tools.cobertura_design import _RE_NAO_ESTADO, estados_da_spec

    contrato = estados_da_spec(spec)
    if not contrato:
        return [], []
    usados = estados_usados(secao6)
    usados_min = {u.lower() for u in usados}
    ausentes = [e for e in contrato if e.lower() not in usados_min] if exigir_todos else []
    do_contrato = {e.lower() for e in contrato}
    do_design = identificadores_do_design(design)
    inventados = [u for u in usados if u.lower() not in do_contrato and not _RE_NAO_ESTADO.match(u)
                  and u.lower() not in do_design and ("_" in u or not so_identificadores)]
    return ausentes, inventados


def identificadores_do_design(design: str) -> Set[str]:
    """Os nomes que o design escreve como identificador: entre crases, ou com sublinhado. A palavra solta não conta —
    «desafiar» e «resultado» estão na prosa de qualquer jornada, e o PRD da exp02ef1b os fez estados."""
    nomes = {t.strip().lower() for t in re.findall(r"`([A-Za-z][A-Za-z0-9_]*)`", design or "")}
    nomes |= {t.lower() for t in re.findall(r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b", design or "")}
    return nomes


# --------------------------------------------------------------------------- d) design citado como produto
#: Origem de produto citada entre parênteses ao lado do número: «(§17 do one-pager)», «(spec, bloco 9f)».
_RE_ORIGEM_CITADA = re.compile(r"\(([^()\n]{0,80}?(?:one[- ]?pager|spec|bloco|§)[^()\n]{0,60})\)", re.I)
_RE_D0_CITADO = re.compile(r"\bD0-0*(\d+)\b")
#: Atribuição de produto ao lado de um [D0-n]: o D0 é decisão do design (até o PR 6, do bloco 13 da spec).
_RE_ATRIBUI_PRODUTO = re.compile(
    r"contratua(?:l|is)|decis[ãa]o\s+(?:do|de)\s+(?:PO|produto)|(?:aprovad|ratificad|homologad|decidid)[oa]s?\s+pel[oa]\s+PO|"
    r"produto/00|one[- ]?pager|n[úu]cleo", re.I)
#: Até o PR 6 o bloco 13 (e o 14, no mesmo arquivo) mora em `produto/05-spec-missao.md`: citá-lo é legítimo.
_RE_BLOCO_DO_DESIGN = re.compile(r"bloco\s*1[34]\b|›\s*bloco\s*1[34]", re.I)


def _fonte_citada(origem: str, docs: Dict[str, str]) -> Optional[Tuple[str, str]]:
    """`(rótulo, texto)` da fonte de produto que a citação nomeia; None se ela não nomeia produto."""
    from tools import bncc
    from tools.conteudo_aprovado import secao

    o = origem.lower()
    if _RE_BLOCO_DO_DESIGN.search(o):
        return None
    # «(One-Pager §6 e §10)»: vale qualquer uma das seções citadas (handoff da exp06ef1b)
    secoes = [int(x) for x in re.findall(r"§\s*(\d{1,2})", o)]

    def do_one_pager() -> Tuple[str, str]:
        if not secoes:
            return "one-pager", docs.get("one_pager", "")
        rotulo = " e ".join(f"§{n}" for n in secoes) + " do one-pager"
        return rotulo, "\n".join(secao(docs.get("one_pager", ""), n) or "" for n in secoes)

    if "one" in o and "pager" in o.replace("-", "").replace(" ", ""):
        return do_one_pager()
    if "spec" in o or "bloco" in o:
        blocos = [int(x) for x in re.findall(r"bloco\s*(\d{1,2})", o)]
        spec = docs.get("spec_produto", "") or docs.get("spec_missao_gate0", "")
        if blocos:
            return (" e ".join(f"bloco {b}" for b in blocos) + " da spec",
                    "\n".join(bncc.secao_bloco(spec, b) or "" for b in blocos))
        return "spec", spec
    if secoes and not re.search(r"se[çc][ãa]o|prd|gabarito", o):
        return do_one_pager()
    return None


def origens_falsas(corpo: str, docs: Dict[str, str]) -> List[Dict[str, str]]:
    """Número de regra com origem de produto citada que não está lá — e `[D0-n]` apresentado como produto."""
    saida: List[Dict[str, str]] = []
    vistos: Set[str] = set()
    for linha in _linhas_do_corpo(corpo):
        if _RE_PROPOSTA.search(linha):
            continue
        for celula in re.split(r"(?<!\\)\||;", linha):
            for m in _RE_ORIGEM_CITADA.finditer(celula):
                fonte = _fonte_citada(m.group(1), docs)
                if not fonte or not fonte[1].strip():
                    continue
                antes = _RE_CITACAO.sub(" ", celula[: m.start()])
                for tok in numeros_de_regra(antes[-120:]):
                    if tem_numero(fonte[1], tok):
                        continue
                    chave = f"{_fmt(tok)}@{fonte[0]}"
                    if chave not in vistos:
                        vistos.add(chave)
                        saida.append({"tipo": "numero", "numero": _fmt(tok), "fonte": fonte[0],
                                      "linha": re.sub(r"\s+", " ", celula).strip()[:160]})
            if _RE_D0_CITADO.search(celula) and _RE_ATRIBUI_PRODUTO.search(celula) \
                    and not _RE_BLOCO_DO_DESIGN.search(celula):
                ids = ", ".join(f"D0-{int(x)}" for x in sorted(set(_RE_D0_CITADO.findall(celula)), key=int))
                if ids not in vistos:
                    vistos.add(ids)
                    saida.append({"tipo": "d0", "ids": ids, "linha": re.sub(r"\s+", " ", celula).strip()[:160]})
    return saida


# --------------------------------------------------------------------------- textos-chave (handoff)
def textos_chave_reescritos(documento: str, one_pager: str) -> List[Tuple[str, str]]:
    """O texto que o PO aprovou palavra por palavra (Canal B, debate, texto de tela do §4) citado com outra redação."""
    from tools.conteudo_aprovado import literais_parafraseados

    return literais_parafraseados(documento, one_pager)


# --------------------------------------------------------------------------- os gates
def _achado(codigo: str, resumo: str, documento: str, severidade: str = "bloqueio", etapa: str = "dev") -> Dict[str, str]:
    return {"severidade": severidade, "codigo": codigo, "etapa": etapa, "agente_responsavel": DONO[documento],
            "resumo": resumo}


def _status(achados: Sequence[Dict[str, str]]) -> str:
    if any(a["severidade"] == "bloqueio" for a in achados):
        return "bloqueado"
    return "amarelo" if achados else "aprovado"


def _exemplos(itens: Iterable[str], limite: int = 6) -> str:
    itens = list(itens)
    return "; ".join(itens[:limite]) + (f"; … e mais {len(itens) - limite}" if len(itens) > limite else "")


def _design(state: Dict[str, Any]) -> str:
    """Os documentos do design onde um estado de decomposição pode ter nascido."""
    return "\n".join(str(state.get(k) or "") for k in ("fluxo_arestas", "jornada_telas", "wireframes_cobertura"))


def _validar(documento: str, texto: str, state: Dict[str, Any]) -> Dict[str, Any]:
    from tools.cobertura_design import corpo_do_prd, secao_numerada

    rotulo = "PRD" if documento == "prd" else "handoff"
    pendencias_rotulo = "seção 19" if documento == "prd" else "seção 7 (Lacunas e pendências)"
    corpo = corpo_do_prd(texto)
    achados: List[Dict[str, str]] = []
    if not corpo.strip():
        return {"status": "aprovado", "achados": [], "registradas": [], "contagem": {}}
    docs = contrato(state)
    contrato_texto = texto_do_contrato(docs)
    one_pager = docs["one_pager"]
    spec = _spec_produto(state)
    pendencias = (secao_numerada(corpo, 19, "pend[êe]ncias") if documento == "prd"
                  else secao_numerada(corpo, 7, "lacunas e pend")) or ""

    # a) números de regra sem origem no contrato
    sem_origem = numeros_sem_origem(corpo, contrato_texto)
    if sem_origem:
        achados.append(_achado(
            "numero-sem-origem",
            f"{len(sem_origem)} número(s) de regra do corpo do {rotulo} não estão no contrato (one-pager, spec de "
            f"produto, decisões da lista branca do bloco 13, decisões do PO no de acordo): "
            + _exemplos(f"{i['numero']} em «{i['linha'][:110]}»" for i in sem_origem)
            + f". O {rotulo} monta, não decide: copie o número do contrato, tire-o, ou marque a linha "
            "`[PROPOSTA — validar com PO: <o número> · por quê]` (ela vai para a seção 19.3). Polling, TTL, p95 e o que "
            "mais for da plataforma não precisam de origem no contrato.", documento))

    # b) hipóteses, tetos e metas
    divergentes, registradas = hipoteses_e_tetos(one_pager, corpo, contrato_texto, pendencias,
                                                 exigir_tetos=(documento == "prd"))
    for c in divergentes:
        if c["secao"] == "§17":
            codigo, o_que = "hipotese-diverge", "hipótese"
        else:
            codigo, o_que = ("teto-ausente", "teto") if c["situacao"] == "ausente" else ("teto-diverge", "teto")
        if c["situacao"] == "acrescentado":
            resumo = (f"A {c.get('hipotese', 'hipótese')} do §17 do one-pager não tem número, e o {rotulo} lhe dá "
                      f"{c['corpo']}: «{c['linha_corpo'][:140]}». Meta de hipótese é decisão do PO: "
                      + ("remeta ao §17 sem reescrevê-lo." if documento == "handoff" else
                         "copie a hipótese do §17 com as palavras dela, ou marque `[PROPOSTA — validar com PO: …]`."))
        elif c["situacao"] == "trocado":
            resumo = (f"{o_que.capitalize()} do {c['secao']} do one-pager com {c['contrato']}, e o {rotulo} escreve "
                      f"{c['corpo']}: «{c['linha_corpo'][:140]}». O corpo diz o que o {c['secao']} diz, com as "
                      "palavras e os números dele" + (" — ou remete ao §17 sem reescrevê-lo." if documento == "handoff"
                                                       else "."))
            if c.get("no_contrato"):
                resumo += (f" O {c['corpo']} também está no contrato, em outro lugar: a divergência é do próprio "
                           f"contrato, e não se decide aqui — o corpo segue o one-pager, e a {pendencias_rotulo} "
                           f"registra `[ABERTO — dono: produto: {c['secao']} diz {c['contrato']} e <onde> diz "
                           f"{c['corpo']}]`.")
        else:
            resumo = (f"O {rotulo} não traz o teto do {c['secao']} do one-pager ({c['contrato']}): «{c['linha'][:140]}». "
                      "Teto da faixa é requisito de quem codifica: leve-o ao RNF e à story das telas que ele limita.")
        achados.append(_achado(codigo, resumo, documento))
    for r in registradas:
        achados.append(_achado(
            "divergencia-registrada",
            f"{r['secao']} do one-pager diz {r['contrato']}, o corpo diz {r['corpo']}, e o contrato tem os dois: está "
            f"registrado na {pendencias_rotulo} com dono produto («{r['registro'][:120]}»). É pendência do PO, e o "
            "rastro a conta.", documento, severidade="atencao", etapa="produto"))
    metas = metas_contra_9f(corpo, spec)
    if metas:
        achados.append(_achado(
            "meta-diverge-9f",
            "KPI com alvo ou limiar que não é o da pergunta dele no 9f da spec: "
            + _exemplos(f"{m['kpi']} ({m['pq']}, {m['coluna']}): {m['corpo']} — no 9f, {m['spec']}" for m in metas)
            + ". Meta e limiar de uma `PQ-nn` são os da linha dela no 9f, copiados; outro número é decisão do PO "
            "(`[PROPOSTA — validar com PO: …]`).", documento))

    # c) estados
    if documento == "prd":
        s6 = secao_numerada(corpo, 6, "estados") or ""
        ausentes, inventados = estados_contra_o_contrato(s6, spec, _design(state))
    else:
        # no handoff, a tabela «estado» de cada tela mistura estado da máquina com estado visual da tela («gerando»,
        # «compacto», handoff da exp06ef1b): só conta o identificador com sublinhado, a forma do contrato
        ausentes, inventados = estados_contra_o_contrato(corpo, spec, _design(state), exigir_todos=False,
                                                         so_identificadores=True)
    if ausentes:
        achados.append(_achado(
            "estado-do-contrato-ausente",
            f"{len(ausentes)} estado(s) do «Contrato de estados» da spec não estão nas colunas de estado nem no diagrama "
            f"da §6 do PRD: {_exemplos(f'`{e}`' for e in ausentes)}. A máquina de estados do PRD é a do contrato, com "
            "os mesmos nomes (eles viram o enum e o CHECK) — estado de falha e de espera inclusive; o nome do design só "
            "aparece no de-para.", documento))
    if inventados:
        onde = "na §6 do PRD" if documento == "prd" else "nas tabelas e no diagrama do handoff"
        achados.append(_achado(
            "estado-fora-do-contrato",
            f"{len(inventados)} estado(s) {onde} não existem no contrato de estados da spec nem no fluxo do design: "
            f"{_exemplos(f'`{e}`' for e in inventados)}. O {rotulo} não cria vocabulário de estado: use o nome do "
            "contrato.", documento))

    # d) decisão de design citada como produto
    falsas = origens_falsas(corpo, docs)
    if falsas:
        achados.append(_achado(
            "origem-de-produto-falsa",
            f"{len(falsas)} citação(ões) dão origem de produto ao que produto não decidiu: "
            + _exemplos((f"{f['numero']} citado como «{f['fonte']}», que não o tem: «{f['linha'][:100]}»"
                         if f["tipo"] == "numero" else
                         f"{f['ids']} apresentado como produto: «{f['linha'][:100]}»") for f in falsas)
            + ". Decisão do D0 é do design: cite-a como `produto/05-spec-missao.md › Bloco 13`; número cita a fonte que o "
            "tem.", documento))

    # texto-chave (handoff: no PRD é o `literal-parafraseado` do A116)
    if documento == "handoff":
        reescritos = textos_chave_reescritos(corpo, one_pager)
        if reescritos:
            achados.append(_achado(
                "texto-chave-reescrito",
                f"{len(reescritos)} texto(s) que o PO aprovou palavra por palavra aparecem no handoff com outra redação: "
                + _exemplos(f"aprovado «{a[:80]}» → «{c[:80]}»" for a, c in reescritos)
                + ". O handoff referencia a chave da copy ou cita o texto aprovado — nunca uma terceira versão.",
                documento))

    return {"status": _status(achados), "achados": achados, "registradas": registradas,
            "contagem": {"numeros_sem_origem": len(sem_origem), "divergentes": len(divergentes),
                         "metas_9f": len(metas), "estados_ausentes": len(ausentes),
                         "estados_inventados": len(inventados), "origens_falsas": len(falsas)}}


def validar_prd(state: Dict[str, Any]) -> Dict[str, Any]:
    """O corpo do PRD (`prd_final`, sem o anexo) contra o contrato: as quatro conferências."""
    return _validar("prd", str(state.get("prd_final") or ""), state)


def validar_handoff(state: Dict[str, Any]) -> Dict[str, Any]:
    """O handoff (`handoff_dev`) contra o contrato: números de regra, hipóteses trocadas, metas do 9f, estados
    inventados, origem de produto falsa e texto-chave reescrito. Teto do §15 e hipótese que o handoff não repete não
    contam: ele remete ao §17 e ao anexo."""
    return _validar("handoff", str(state.get("handoff_dev") or ""), state)


def relatorio(resultado: Dict[str, Any], documento: str, missao: str = "") -> str:
    import json

    rotulo = "PRD" if documento == "prd" else "Handoff"
    icone = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}[resultado["status"]]
    L = [f"# {rotulo} monta, não decide — {missao or 'missão'}", "",
         f"**Veredito: {icone}** · o corpo contra o contrato (one-pager, spec de produto, lista branca do bloco 13, "
         "decisões do PO): números de regra, hipóteses e metas, tetos, estados e origem citada.", ""]
    if not resultado["achados"]:
        L.append("- Tudo o que o corpo afirma de produto está no contrato, com os mesmos números e estados.")
    for a in resultado["achados"]:
        L.append(f"- {'⛔' if a['severidade'] == 'bloqueio' else '⚠️'} `{a['codigo']}` — {a['resumo']}")
    envelope = {"agente": AGENTE, "missao": missao or "", "status": resultado["status"],
                "achados": [{"severidade": a["severidade"], "classe": "montagem", "codigo": a["codigo"],
                             "agente_responsavel": a["agente_responsavel"], "resumo": a["resumo"]}
                            for a in resultado["achados"]],
                "precisa_humano": False}
    return "\n".join(L) + "\n\n```json\n" + json.dumps(envelope, ensure_ascii=False) + "\n```\n"
