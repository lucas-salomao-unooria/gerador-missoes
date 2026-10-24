"""Classe e ambiente decididos em produto; o D9 e a jornada sem poder de produto. Determinístico, sem LLM.

PR 8 do plano «Produto dono do contrato» (docs/planos/2026-10-23-produto-dono-do-contrato.md), decisão D8: ambiente novo
e mini-jogo passam formalmente para produto. Até aqui o D9 (A067) decidia a classe do ambiente (app clonado ou
mini-jogo) e criava ambiente novo quando a spec calava, e a jornada (A071, Seção 5) escrevia as regras e as fases do
jogo: produto criado no design, que o PO nunca via. O D9 ficou dormente em 5 de 5 sessões de 23/10/2026 — o custo é
baixo, e fecha uma porta de criação de produto. Na exp01em1b-76d9af6e (23/10) ele ainda escreveu no texto do Gate 0:
um estado `ERRO_MIDIA_FALHOU` no bloco 2, uma regra no bloco 3, uma «Demonstração de primeiro uso» no bloco 7 e outra
divisão de papéis no bloco 10.

Três conferências:

- `conferir_spec` (produto, no gate do manifesto, A047 e A099): o bloco 0 fixa a classe (`classe_ambiente`, ou inferida
  da `secao_ds` — leitura tolerante para a spec anterior a este PR) e o ambiente; mini-jogo só no 1º–5º ano (condição 1
  do gate de aplicabilidade), com as regras e as fases na spec; ambiente novo ou mini-jogo que o briefing não fixou é
  escolha do PO — `[PROPOSTA — validar com PO]` na lista do de acordo (`tools/fechar_contrato.py`), nunca decidido em
  silêncio.
- `conferir_d9` (design, no split do D9, A068): o bloco 14 é só o detalhe de UI do ambiente que a spec decidiu. Bloco 14
  com ambiente ou classe diferente do bloco 0, ou com regra ou fase de jogo, é decisão de produto: bloqueia, como a
  decisão de produto do D0 no A066 (PR 6). Spec calada, ou o D9 pedindo outro ambiente: devolução a produto,
  `[PROPOSTA — validar com PO]` no cartão — a rota do PR 5 (Refazer → triagem → produto). O texto do D9 fora do bloco 14
  é conferido na montagem (`agents.checkers.montar_sobre_aceita`).
- `conferir_jornada` (design, no gate das arestas, A083b): a Seção 5 da jornada copia as regras e as fases da spec e só
  mapeia as telas; regra ou fase que a spec não tem vira `[PROPOSTA — validar com PO]`, como a guarda do fluxo que muda
  o que o aluno faz (`tools/arestas.py`, PR 7).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional

APP_CLONADO = "app-clonado"
MINI_JOGO = "mini-jogo"
AGENTE_D9 = "ambiente-simulado"
#: A plataforma em si (tela de contexto e reflexão, e a casca do mini-jogo): pode aparecer em qualquer missão.
SECAO_DA_PLATAFORMA = "unooria"
#: Condição 1 do gate de aplicabilidade do mini-jogo: 1º ao 5º ano do Fundamental.
SERIES_DO_MINIJOGO = frozenset({"1EF", "2EF", "3EF", "4EF", "5EF"})

#: Os títulos da resposta do D9 (prompt 067): o bloco 14 vem no Passo 4, e a resposta segue com os testes. A resposta de
#: antes deste PR trazia, depois do Passo 4, um «## Bloco 14 — Ficha do ambiente»; as duas formas são lidas.
D9_PASSO4_INICIO = r"^#{2,3}\s*Passo 4\b.*$"
D9_PASSO4_FIM = r"^(?:#{2,3}\s*Bloco 14\b|##\s*Testes\b).*$"
D9_DEVOLUCAO_INICIO = r"^#{2,3}\s*Passo 3\b.*$"

_RE_CLASSE_LINHA = re.compile(r"(?:classe_ambiente|classe\s+do\s+ambiente)[`*_]*\s*[:=]\s*[`*_]*\s*([^\n`|]+)", re.I)
_RE_CLASSE_VALOR = re.compile(r"\b(mini-?\s?jogo|minijogo|app[\s-]+clonado)\b", re.I)
_RE_CLASSE_NO_BLOCO = re.compile(r"^[\s>*-]*(?:\*\*)?classe(?:\s+do\s+ambiente)?(?:\*\*)?\s*:\s*(?:\*\*)?\s*([^\n]+)$",
                                 re.I | re.M)
_RE_FICHA_DE_MINIJOGO = re.compile(r"^#{1,4}\s*mini-?jogo\s*[—–-]", re.I | re.M)
_RE_ROTULO_SECAO = re.compile(r"se[çc][ãa]o\s+(?:principal\s+)?(?:do\s+)?(?:ds|design\s+system)\b[^:\n]{0,40}:\s*(.+)$",
                              re.I | re.M)
_RE_SECAO_DS_CAMPO = re.compile(r"secao_ds[`*_]*\s*:\s*[`*_]*\s*([a-z0-9:_\-]+)", re.I)
_RE_TOKEN_SECAO = re.compile(r"^(?:(?:nova|minijogo)\s*:\s*)?[a-z][a-z0-9-]*$")
#: Valores que aparecem na linha «Seção do DS:» da ficha e não são seção: a coleção do lo-fi, a negação.
_NAO_SAO_SECAO = frozenset({"wireframe-cinza", "nenhuma", "nenhum", "nao", "não"})
_RE_TITULO_REGRAS = re.compile(r"\bregras\b.*\bfases\b", re.I)
_RE_REGRA = re.compile(r"^\s*(?:[-*]\s+)?[`*]{0,2}R(\d{1,2})[`*]{0,2}(?=[\s:—–.)-])\s*[:—–.)-]?\s*(.+?)\s*$", re.M)
#: Marcador do contrato aberto: a escolha que espera o PO.
_RE_MARCADOR_DO_PO = re.compile(r"\[(?:PROPOSTA|PAR[ÂA]METRO)\b[^\]\n]*\]|\[ABERTO\s*[—–-]\s*dono:\s*(?:o\s+)?PO\b[^\]\n]*\]")
#: O que o de acordo de produto grava no lugar do marcador: «<valor> — PO, parecer de <data>» (`tools/fechar_contrato`).
_RE_PARECER_DO_PO = re.compile(r"\bPO,\s*parecer\s+de\b", re.I)
_RE_RECUSA = re.compile(r"\brecusad[oa]s?\b", re.I)
_RE_MINIJOGO = re.compile(r"\bmini-?\s?jogos?\b|\bminijogos?\b", re.I)
_RE_AMBIENTE_NOVO = re.compile(r"\bambiente\s+novo\b|\bapp\s+novo\b|\bse[çc][ãa]o\s+nova\b|\bnova\s*:", re.I)
#: A linha que fala da escolha da classe, não de um parâmetro do jogo.
_RE_FALA_DA_CLASSE = re.compile(r"\bclasse\b|\bambiente\b|app\s+clonado|no\s+lugar|em\s+vez|secao_ds|se[çc][ãa]o\s+do\s+DS",
                                re.I)
#: Linha de regra ou fase de jogo dentro do bloco 14: o que é conteúdo de produto desde este PR.
_RE_DEFINE_JOGO = re.compile(
    r"(?:como\s+se\s+(?:vence|perde)|o\s+que\s+(?:é|e)\s+uma\s+fase|quantas\s+fases|fases_sugeridas|"
    r"intervalo\s+de\s+fases|regra\s+da\s+fase|como\s+o\s+progresso\s+aparece|vence\s+a\s+fase|perde\s+a\s+fase)", re.I)


# ------------------------------------------------------------------ normalização
def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn")


def _norm(texto: str) -> str:
    """Para comparar cópia: sem caixa, acento, marcação nem pontuação (a regra copiada com outro ponto final é a mesma)."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", _sem_acento(texto).lower()).split())


def _classe(valor: str) -> Optional[str]:
    m = _RE_CLASSE_VALOR.search(valor or "")
    if not m:
        return None
    return MINI_JOGO if "jogo" in m.group(1).lower() else APP_CLONADO


def _bloco0(spec: str) -> str:
    from tools.bncc import secao_bloco

    return secao_bloco(spec or "", 0) or (spec or "")[:4000]


def _vocabulario() -> set:
    from tools import rastro

    try:
        return set(rastro.secoes_ds()) | set(rastro.SECOES_LEGADAS) | {SECAO_DA_PLATAFORMA}
    except Exception:  # pragma: no cover - base da plataforma indisponível
        return set(rastro.SECOES_LEGADAS) | {SECAO_DA_PLATAFORMA}


# ------------------------------------------------------------------ o que a spec decidiu
def classe_e_ambiente(spec: str) -> Dict[str, Any]:
    """`{secao, extras, classe, declarada, inferida, nova}` do bloco 0 da spec.

    A classe vem da linha `classe_ambiente: app-clonado | mini-jogo` (desde 24/10/2026, PR 8) ou, sem ela, da `secao_ds`:
    `minijogo:<nome>` é mini-jogo, qualquer outra é app clonado. É a leitura tolerante da spec de antes deste PR — as 15
    missões do acervo e as quatro que vão ser refeitas (exp02ef1b, exp02em1b, exp01em1b e exp03em1b) são app clonado numa
    seção que existe, e nenhuma declara a classe."""
    from tools import secoes as sec
    from tools.rastro import _campo

    bloco = _bloco0(spec)
    secao = (_campo(bloco, "secao_ds") or "").strip().strip("`*_ ").lower()
    secao = re.sub(r"\s*:\s*", ":", secao)
    m = _RE_CLASSE_LINHA.search(bloco)
    declarada = _classe(m.group(1)) if m else None
    inferida = (MINI_JOGO if secao.startswith("minijogo:") else APP_CLONADO) if secao else None
    return {"secao": secao, "extras": sec.extras(bloco), "classe": declarada or inferida, "declarada": declarada,
            "inferida": inferida, "nova": secao.startswith(("nova:", "minijogo:"))}


def regras_e_fases(texto: str) -> Dict[str, Any]:
    """As regras (`R1`…) e as fases (tabela com a coluna «Fase» ou «#») da seção «Regras e fases» do texto — o bloco 2
    da spec de um mini-jogo, ou a Seção 5 da jornada. `{secao, regras: {n: texto}, fases: {n: {nome, regra, linha}}}`;
    sem a seção, tudo vazio. «n/a — ambiente é app clonado» não tem regra nem fase (as 12 jornadas do acervo)."""
    from tools.cobertura_design import _secao_por_titulo, tabelas

    corpo = _secao_por_titulo(texto or "", _RE_TITULO_REGRAS) or ""
    regras: Dict[int, str] = {}
    for m in _RE_REGRA.finditer(corpo):
        if m.group(0).lstrip().startswith("|"):
            continue
        regras.setdefault(int(m.group(1)), m.group(2).strip(" `*"))
    fases: Dict[int, Dict[str, str]] = {}
    for cab, linhas in tabelas(corpo):
        col_n = next((c for c in cab if c in ("#", "n", "no", "nº", "n.º", "numero", "número")
                      or c.startswith("fase")), None)
        if not col_n:
            continue
        col_nome = next((c for c in cab if c.startswith("nome")), None)
        col_regra = next((c for c in cab if c.startswith("regra")), None)
        for linha in linhas:
            m = re.search(r"\d{1,2}", linha.get(col_n, ""))
            if not m:
                continue
            nome = linha.get(col_nome, "") if col_nome else re.sub(r"^\D*\d{1,2}\s*[—–:.-]?\s*", "", linha.get(col_n, ""))
            fases.setdefault(int(m.group(0)), {"nome": nome.strip(" `*"), "regra": (linha.get(col_regra, "") if col_regra
                                                                                    else "").strip(" `*"),
                                               "linha": " | ".join(v for v in linha.values())[:240]})
    return {"secao": bool(corpo.strip()), "regras": regras, "fases": fases}


def escolha_do_po(spec: str, one_pager: str = "", briefing: str = "", decisoes_do_po: Optional[Iterable[Any]] = None,
                  decidido: Optional[Dict[str, Any]] = None, one_pager_po: str = "") -> str:
    """Quem decidiu o ambiente novo ou o mini-jogo do bloco 0: `briefing` (o briefing ou o one-pager que o PO anexou o
    fixam) · `aprovada` · `recusada` (o PO respondeu no de acordo, «— PO, parecer de <data>») · `pendente` (o marcador
    espera o de acordo) · `silencio` (ninguém perguntou) · `nao_se_aplica` (ambiente existente da lista: produto escolhe
    pela tabela de `ambientes.md`)."""
    from tools.rastro import secao_travada

    d = decidido or classe_e_ambiente(spec)
    if not d["nova"]:
        return "nao_se_aplica"
    secao = d["secao"]
    minijogo = d["classe"] == MINI_JOGO

    def fala_da_escolha(linha: str) -> bool:
        # a seção nomeada, ou a classe com a palavra da escolha: «mini-jogo no lugar de app clonado». Só «mini-jogo» não
        # basta — o [PARÂMETRO] da duração da fase do mini-jogo é outra decisão do PO, não a da classe
        if secao and secao in linha.lower():
            return True
        if minijogo:
            return bool(_RE_MINIJOGO.search(linha) and _RE_FALA_DA_CLASSE.search(linha))
        return bool(_RE_AMBIENTE_NOVO.search(linha))

    aprovada = recusada = pendente = False
    for texto in (spec, one_pager):
        for linha in (texto or "").splitlines():
            if not fala_da_escolha(linha):
                continue
            if _RE_PARECER_DO_PO.search(linha):
                if _RE_RECUSA.search(linha):
                    recusada = True
                else:
                    aprovada = True
            elif _RE_MARCADOR_DO_PO.search(linha):
                pendente = True
    ultima = None
    for registro in decisoes_do_po or []:
        if not isinstance(registro, dict):
            continue
        assunto = str(registro.get("assunto") or "")
        if registro.get("tipo") == "escolha_ambiente" or fala_da_escolha(assunto):
            ultima = str(registro.get("resposta") or "")
    if ultima == "recusar":
        recusada, aprovada = True, False
    elif ultima in ("aceitar", "outro"):
        aprovada, recusada = True, False
    if recusada:
        return "recusada"
    if aprovada:
        return "aprovada"
    trava = secao_travada(briefing or "", {})
    if trava and trava.get("explicita") and trava["secao"] == secao:
        return "briefing"
    if minijogo and _RE_MINIJOGO.search(briefing or ""):
        return "briefing"
    # o one-pager que o PO anexou é documento dele: a «Seção do DS» do cabeçalho vale como o briefing (como a legada em
    # `rastro._legada_fixada_pelo_po`)
    cabecalho = re.search(r"Se[çc][ãa]o do DS\**\s*[:=]\s*\**\s*`?([a-z][\w:-]*)", (one_pager_po or "")[:6000], re.I)
    if cabecalho and re.sub(r"\s*:\s*", ":", cabecalho.group(1).lower()) == secao:
        return "briefing"
    return "pendente" if pendente else "silencio"


def conferir_spec(spec: str, serie: Optional[str] = None, briefing: str = "", one_pager: str = "",
                  decisoes_do_po: Optional[Iterable[Any]] = None, conferir_escolha: bool = True,
                  one_pager_po: str = "") -> List[Dict[str, Any]]:
    """Os achados de produto sobre a classe e o ambiente do bloco 0, no formato do manifesto (`campo`, `etapa`)."""
    d = classe_e_ambiente(spec)
    achados: List[Dict[str, Any]] = []
    if not d["secao"]:
        return achados  # o manifesto já acusa a `secao_ds` ausente
    divergente = bool(d["declarada"] and d["declarada"] != d["inferida"])
    if divergente:
        achados.append({"severidade": "bloqueio", "campo": "classe_ambiente", "etapa": "produto",
                        "codigo": "classe-ambiente-divergente", "resumo": (
                            f"`classe_ambiente: {d['declarada']}` com `secao_ds: {d['secao']}`: mini-jogo é "
                            "`minijogo:<nome>`, e toda outra seção é app clonado. Corrija um dos dois no bloco 0 — a classe "
                            "e o ambiente são decididos em produto, e o D9 lê os dois daqui.")})
    # com as duas linhas em desacordo, o resto se confere pela seção — a divergência já bloqueia
    if (d["inferida"] if divergente else d["classe"]) == MINI_JOGO:
        if serie and serie.upper() not in SERIES_DO_MINIJOGO:
            achados.append({"severidade": "bloqueio", "campo": "classe_ambiente", "etapa": "produto",
                            "codigo": "minijogo-fora-da-faixa", "resumo": (
                                f"Mini-jogo (`{d['secao']}`) numa missão de {serie}: o gate de aplicabilidade do mini-jogo "
                                "vale só no 1º–5º ano (condição 1 de `ambiente-e-minijogo.md`). Do 6º em diante a classe é "
                                "app clonado, numa seção da lista de `ambientes.md`.")})
        rf = regras_e_fases(spec)
        if not rf["fases"]:
            com_o_po = any(_RE_MARCADOR_DO_PO.search(l) and re.search(r"\bfases?\b|\bregras?\b", l, re.I)
                           for l in (spec or "").splitlines())
            achados.append({
                "severidade": "atencao" if com_o_po else "bloqueio", "campo": "classe_ambiente", "etapa": "produto",
                "codigo": "minijogo-regras-e-fases-com-o-po" if com_o_po else "minijogo-sem-regras-e-fases",
                "resumo": ("Mini-jogo com as regras e as fases do jogo pendentes de decisão do PO no de acordo de produto."
                           if com_o_po else
                           "Mini-jogo sem as regras e as fases do jogo na spec: quantas fases, em que ordem, a regra de cada "
                           "uma, o que vence e o que perde, e como o progresso aparece são conteúdo de produto desde o PR 8 — "
                           "a subseção «Regras e fases do mini-jogo» do bloco 2 (`formato-spec.md`), copiada do §4 do "
                           "one-pager. A jornada só mapeia as telas para elas; se a decisão é do PO, escreva "
                           "`[ABERTO — dono: PO: regras e fases do mini-jogo …]` com a sugestão.")})
    if conferir_escolha and d["nova"]:
        escolha = escolha_do_po(spec, one_pager, briefing, decisoes_do_po, d, one_pager_po=one_pager_po)
        rotulo = "o mini-jogo" if d["classe"] == MINI_JOGO else "o ambiente novo"
        if escolha == "recusada":
            achados.append({"severidade": "bloqueio", "campo": "secao_ds", "etapa": "produto",
                            "codigo": "escolha-de-ambiente-recusada", "resumo": (
                                f"O PO recusou {rotulo} (`{d['secao']}`) no de acordo, e o bloco 0 ainda o fixa. Refaça a "
                                "spec com um ambiente existente da lista de `ambientes.md` (ambiente existente antes de "
                                "ambiente novo).")})
        elif escolha == "pendente":
            achados.append({"severidade": "atencao", "campo": "secao_ds", "etapa": "produto",
                            "codigo": "escolha-de-ambiente-com-o-po", "resumo": (
                                f"{rotulo[0].upper() + rotulo[1:]} (`{d['secao']}`) é escolha do PO: o marcador vai à lista do "
                                "de acordo de produto, que o PO responde item a item.")})
        elif escolha == "silencio":
            achados.append({"severidade": "bloqueio", "campo": "secao_ds", "etapa": "produto",
                            "codigo": "escolha-de-ambiente-sem-o-po", "resumo": (
                                f"O bloco 0 fixa {rotulo} (`{d['secao']}`) sem decisão do PO e sem o briefing fixá-lo. "
                                "Ambiente novo e mini-jogo são escolha do PO (decisão D8): escreva, numa linha do bloco 0, "
                                f"`[PROPOSTA — validar com PO: {rotulo[2:]} `{d['secao']}` · por quê: <o que nenhuma seção da "
                                "lista comporta> · alternativa: <a seção existente mais próxima>]` — a lista do de acordo a "
                                "mostra, e o PO aceita ou recusa.")})
    return achados


# ------------------------------------------------------------------ o D9: só o bloco 14
def bloco_14(texto: str) -> str:
    """O bloco `## 14.` da resposta do D9 — do título ao próximo `## `; "" sem ele."""
    m = re.search(r"^##\s*\**\s*14\b.*$", texto or "", re.M)
    if not m:
        return ""
    fim = re.search(r"^## ", texto[m.end():], re.M)
    return texto[m.start(): m.end() + fim.start()] if fim else texto[m.start():]


def secoes_do_bloco_14(bloco: str, envelope: Optional[Dict[str, Any]] = None) -> List[str]:
    """As seções do DS que a ficha nomeia: a primeira de cada linha «Seção do DS:» (o valor, conhecido ou não — é o que
    pega a seção inventada sem prefixo), as outras dela que sejam seção conhecida, `secao_ds:` e o envelope."""
    vocab = _vocabulario()
    por_tamanho = sorted(vocab, key=len, reverse=True)
    saida: List[str] = []

    def pôr(token: str, primeiro: bool) -> None:
        t = re.sub(r"\s*:\s*", ":", token.strip().strip("`*_ ,.;").lower())
        # a ponte ou o nome do pacote da seção (`@edu/ui/ds-unoochat`, `ds-unoochat`) nomeiam a mesma seção
        t = re.sub(r"^ds-", "", re.sub(r"^@?edu/ui/", "", t))
        if not t or not _RE_TOKEN_SECAO.match(t) or t in _NAO_SAO_SECAO:
            return
        if t not in vocab and not t.startswith(("nova:", "minijogo:")):
            conhecida = next((v for v in por_tamanho if v in t), None)
            if conhecida:
                t = conhecida
            elif not primeiro:
                return
        if t not in saida:
            saida.append(t)

    for m in _RE_ROTULO_SECAO.finditer(bloco or ""):
        valor = m.group(1)
        tokens = re.findall(r"`([^`\n]+)`", valor)
        if tokens:
            for i, token in enumerate(tokens):
                pôr(token, i == 0)
            continue
        # sem crase, só a palavra que é seção conhecida conta: «nenhuma seção nova», «Galeria de fotos» não são valor
        primeira = re.match(r"[\s*_]*([a-z][\w:-]*)", valor, re.I)
        if primeira:
            pôr(primeira.group(1), False)
    for m in _RE_SECAO_DS_CAMPO.finditer(bloco or ""):
        pôr(m.group(1), True)
    amb = (envelope or {}).get("ambiente") if isinstance(envelope, dict) else None
    if isinstance(amb, dict) and amb.get("secao_ds"):
        pôr(str(amb["secao_ds"]), True)
    return saida


def classes_do_bloco_14(bloco: str, envelope: Optional[Dict[str, Any]] = None) -> List[str]:
    """As classes que a ficha declara: a linha «Classe:», o título «# Mini-jogo — …» e o envelope."""
    saida: List[str] = []
    for m in _RE_CLASSE_NO_BLOCO.finditer(bloco or ""):
        c = _classe(m.group(1))
        if c and c not in saida:
            saida.append(c)
    if _RE_FICHA_DE_MINIJOGO.search(bloco or "") and MINI_JOGO not in saida:
        saida.append(MINI_JOGO)
    amb = (envelope or {}).get("ambiente") if isinstance(envelope, dict) else None
    if isinstance(amb, dict):
        c = _classe(str(amb.get("classe") or ""))
        if c and c not in saida:
            saida.append(c)
    return saida


def jogo_no_bloco_14(bloco: str, spec: str) -> List[str]:
    """As linhas do bloco 14 que definem regra ou fase de jogo e que a spec não traz, iguais: regra `R<n>`, tabela de
    fases, «como se vence/perde uma fase», «quantas fases». Citar a regra da spec palavra por palavra não é decidir."""
    da_spec = {_norm(l) for l in (spec or "").splitlines() if l.strip()}
    rf = regras_e_fases(bloco)
    saida = [f"R{n} {t}" for n, t in sorted(rf["regras"].items())]
    saida += [f"fase {n}: {f['linha']}" for n, f in sorted(rf["fases"].items())]
    for linha in (bloco or "").splitlines():
        if _RE_DEFINE_JOGO.search(linha) and re.search(r":\s*\S", linha) and _norm(linha) not in da_spec:
            saida.append(linha.strip()[:200])
    return [s for s in dict.fromkeys(saida) if _norm(s) not in da_spec]


def devolucoes_do_d9(texto: str, envelope: Optional[Dict[str, Any]] = None) -> List[str]:
    """O que o D9 devolve a produto: o campo `devolucao` do envelope (objeto ou lista, com `proposta`), os
    `[PROPOSTA …]` do Passo 3 e, na resposta de antes deste PR, o pedido de re-spec `[RS-AMB]`."""
    env = envelope if isinstance(envelope, dict) else {}
    saida: List[str] = []
    bruto = env.get("devolucao")
    for d in (bruto if isinstance(bruto, list) else [bruto] if bruto else []):
        if isinstance(d, dict):
            partes = [str(d.get(k) or "").strip() for k in ("proposta", "por_que", "alternativa")]
            if partes[0]:
                saida.append(partes[0] + (f" · por quê: {partes[1]}" if partes[1] else "")
                             + (f" · alternativa: {partes[2]}" if partes[2] else ""))
        elif isinstance(d, str) and d.strip():
            saida.append(d.strip())
    m = re.search(D9_DEVOLUCAO_INICIO, texto or "", re.M)
    if m:
        fim = re.search(r"^#{2,3}\s", texto[m.end():], re.M)
        trecho = texto[m.end(): m.end() + fim.start()] if fim else texto[m.end():]
        for marcador in re.finditer(r"\[PROPOSTA\b[^\]\n]*?:\s*([^\]\n]+)\]", trecho):
            proposta = marcador.group(1).strip()
            if not any(_norm(proposta)[:60] in _norm(s) or _norm(s)[:60] in _norm(proposta) for s in saida):
                saida.append(proposta)
    respec = env.get("respec") if isinstance(env.get("respec"), dict) else {}
    if not saida and (str(respec.get("id") or "").upper() == "RS-AMB" or str(env.get("status") or "") == "aguarda_gate"):
        saida.append("o D9 pediu a troca do ambiente ao Gate 0 (`[RS-AMB]`) — o pedido está no relatório dele")
    return saida


def _achado_devolucao(proposta: str, estrito: bool) -> Dict[str, Any]:
    return {"severidade": "bloqueio" if estrito else "decisao_humana", "codigo": "devolucao-a-produto",
            "etapa": "design", "agente_responsavel": "PO",
            "resumo": (f"[PROPOSTA — validar com PO: {proposta.rstrip('.')}]. O D9 não decide ambiente nem classe (PR 8, "
                       "decisão D8): se a troca deve valer, o PO a pede no **Refazer** (a triagem leva o item a Produto) "
                       "ou devolve a Produto com a decisão; senão, o design segue com o ambiente da spec.")}


def conferir_d9(texto: str, envelope: Optional[Dict[str, Any]], estado: Dict[str, Any],
                estrito: bool = False) -> Dict[str, Any]:
    """`{achados, descartar}` da resposta do D9 contra o bloco 0 da spec de produto. `descartar`: o bloco 14 decide o
    ambiente ou a classe no lugar de produto, e o anexo de design fica como estava."""
    spec = str(estado.get("spec_missao") or "")
    decidido = classe_e_ambiente(spec)
    bloco = bloco_14(_passo4(texto) or "")
    nomeadas = secoes_do_bloco_14(bloco, envelope)
    classes = classes_do_bloco_14(bloco, envelope)
    devolucoes = devolucoes_do_d9(texto, envelope)
    achados: List[Dict[str, Any]] = []
    descartar = False
    if not decidido["secao"]:
        # a devolução a produto, como a proposta do fluxo (PR 7): decisão humana no cartão; com ESTEIRA_ESTRITA, bloqueia
        achados.append({
            "severidade": "bloqueio" if estrito else "decisao_humana", "codigo": "ambiente-ausente-na-spec",
            "etapa": "produto", "agente_responsavel": "PO",
            "resumo": ("[ABERTO — dono: PO: a spec de produto não fixa a classe nem o ambiente (bloco 0, `secao_ds`)]. "
                       "Desde o PR 8 (decisão D8) quem decide é produto: o D9 não cria ambiente e o design não tem casca "
                       "para montar. Devolva a Produto — o passo de completude da spec pergunta, e o PO decide no de "
                       "acordo.")})
        if nomeadas or classes:
            descartar = True
            sugerido = ", ".join(f"`{s}`" for s in nomeadas) or "um ambiente"
            devolucoes.insert(0, f"o D9 sugeriu {sugerido}" + (f" ({', '.join(classes)})" if classes else "")
                              + " com a spec calada — a criação foi descartada pelo código, e vale como sugestão")
    else:
        permitidas = {decidido["secao"], *decidido["extras"], SECAO_DA_PLATAFORMA}
        fora = [s for s in nomeadas if s not in permitidas]
        outra_classe = [c for c in classes if decidido["classe"] and c != decidido["classe"]]
        if fora or outra_classe:
            descartar = True
            o_que = "; ".join(filter(None, [
                ("seção " + ", ".join(f"`{s}`" for s in fora)) if fora else "",
                ("classe " + ", ".join(outra_classe)) if outra_classe else ""]))
            achados.append({
                "severidade": "bloqueio", "codigo": "decisao-de-produto-pelo-agente", "etapa": "design",
                "agente_responsavel": AGENTE_D9,
                "resumo": (f"O bloco 14 nomeia {o_que}, e o bloco 0 da spec de produto decidiu `{decidido['secao']}` "
                           f"({decidido['classe']}"
                           + (f"; extras: {', '.join(decidido['extras'])}" if decidido["extras"] else "") + "). "
                           "Ambiente e classe são decisão de produto (PR 8): o bloco 14 não entrou no anexo de design. "
                           "Reemita a ficha do ambiente que a spec decidiu; se ele não comporta os verbos do bloco 4, "
                           "devolva a troca a produto no Passo 3 e no envelope (`devolucao`), sem criar.")})
            devolucoes.append("o D9 quis " + o_que + f" no lugar de `{decidido['secao']}` ({decidido['classe']})")
        jogo = jogo_no_bloco_14(bloco, spec)
        if jogo:
            achados.append({
                "severidade": "bloqueio", "codigo": "decisao-de-produto-pelo-agente", "etapa": "design",
                "agente_responsavel": AGENTE_D9,
                "resumo": ("O bloco 14 traz regra ou fase de jogo que a spec não tem — quantas fases, a regra de cada uma, o "
                           "que vence e o que perde e como o progresso aparece são conteúdo de produto desde o PR 8, na "
                           "subseção «Regras e fases do mini-jogo» do bloco 2. A ficha é só UI (chrome, navegação, "
                           "affordances, verbos com rótulo e componente, a seção do DS): tire estas linhas e, se o jogo "
                           "precisa de outra regra, devolva-a a produto:\n"
                           + "\n".join(f"    - «{l[:180]}»" for l in jogo[:10]))})
        if decidido["nova"]:
            escolha = escolha_do_po(spec, str(estado.get("one_pager") or ""), str(estado.get("briefing") or ""),
                                    estado.get("decisoes_do_po") or [], decidido,
                                    one_pager_po=str(estado.get("one_pager_po") or ""))
            rotulo = "o mini-jogo" if decidido["classe"] == MINI_JOGO else "o ambiente novo"
            if escolha == "recusada":
                achados.append({"severidade": "bloqueio", "codigo": "escolha-de-ambiente-recusada", "etapa": "produto",
                                "agente_responsavel": "PO", "resumo": (
                                    f"O PO recusou {rotulo} (`{decidido['secao']}`) no de acordo de produto, e a spec ainda o "
                                    "fixa: o design montaria o que o PO recusou. Devolva a Produto.")})
            elif escolha in ("pendente", "silencio"):
                achados.append({"severidade": "bloqueio" if estrito else "decisao_humana",
                                "codigo": "escolha-de-ambiente-sem-o-po", "etapa": "produto", "agente_responsavel": "PO",
                                "resumo": (f"[PROPOSTA — validar com PO: {rotulo[2:]} `{decidido['secao']}`, que a spec "
                                           "fixa sem decisão do PO]. Ambiente novo e mini-jogo são escolha do PO (D8): ele "
                                           "a responde no de acordo de produto (Devolver a Produto).")})
    for proposta in dict.fromkeys(devolucoes):
        achados.append(_achado_devolucao(proposta, estrito))
    return {"achados": achados, "descartar": descartar, "decidido": decidido, "nomeadas": nomeadas,
            "classes": classes}


def _passo4(texto: str) -> Optional[str]:
    m = re.search(D9_PASSO4_INICIO, texto or "", re.M)
    if not m:
        return None
    fim = re.search(D9_PASSO4_FIM, texto[m.end():], re.M)
    return texto[m.end(): m.end() + fim.start()] if fim else texto[m.end():]


def reavaliar_d9(estado: Dict[str, Any], estrito: bool = False) -> Dict[str, Any]:
    """`{status, achados}` do split do D9 refeito sobre a resposta gravada (`ambiente_simulado`): as conferências deste
    módulo mais o texto do D9 fora do bloco 14 (`agents.checkers.montar_sobre_aceita`). A spec aceita é a de produto (a do
    Gate 0, na sessão anterior ao PR 6) mais o bloco 13 — é o que o A068 monta. Para a regressão do acervo."""
    from agents.callbacks import extrair_envelope
    from agents.checkers import documento_sem_moldura, montar_sobre_aceita
    from tools.anexo_design import KEY_ANEXO, _bloco, blocos_do_anexo
    from tools.propagacao import spec_de_produto

    texto = str(estado.get("ambiente_simulado") or "")
    if not texto.strip():
        return {"status": "aprovado", "achados": []}
    envelope = extrair_envelope(texto) or {}
    spec = str(estado.get("spec_missao") or "")
    produto = str(estado.get("spec_missao_gate0") or "") or spec_de_produto(spec)
    # o anexo de design; na sessão anterior ao PR 6, o bloco 13 que o D0 deixou dentro da spec
    anexo = blocos_do_anexo(str(estado.get(KEY_ANEXO) or "")) or _bloco(spec, "13")
    aceita = produto.rstrip() + ("\n\n" + anexo if anexo.strip() else "")
    resultado = conferir_d9(texto, envelope, {**estado, "spec_missao": produto}, estrito=estrito)
    achados = list(resultado["achados"])
    secao = _passo4(texto)
    if secao and re.search(r"^##\s*\**\s*14\b", secao, re.M):
        avisos: List[Dict[str, Any]] = []
        montar_sobre_aceita(aceita, documento_sem_moldura(secao), r"^##\s*14\b.*$", avisos=avisos, autor="D9",
                            agente=AGENTE_D9, estrito=estrito, estado=estado)
        achados += avisos
    status = ("bloqueado" if any(a.get("severidade") == "bloqueio" for a in achados)
              else "amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados}


# ------------------------------------------------------------------ a jornada: só mapeia as telas
def conferir_jornada(spec: str, jornada: str, estrito: bool = False) -> Dict[str, Any]:
    """`{achados, contagem}` da Seção 5 da jornada contra as regras e as fases da spec.

    A jornada copia as regras e as fases da spec e só mapeia as telas para elas. Regra ou fase que a spec não tem, ou com
    outro texto, é `[PROPOSTA — validar com PO]` (a rota do PR 5); jogo numa missão que a spec decide app clonado também.
    Fase da spec sem tela na jornada é atenção para a jornada. Nas 12 jornadas do acervo, a Seção 5 diz «n/a — ambiente é
    app clonado»: nenhuma acusa."""
    decidido = classe_e_ambiente(spec)
    da_spec = regras_e_fases(spec)
    da_jornada = regras_e_fases(jornada)
    achados: List[Dict[str, Any]] = []

    def proposta(codigo: str, texto: str) -> None:
        achados.append({"severidade": "bloqueio" if estrito else "decisao_humana", "codigo": codigo, "etapa": "design",
                        "agente_responsavel": "PO",
                        "resumo": (f"[PROPOSTA — validar com PO: {texto}]. Regras e fases do mini-jogo são conteúdo de "
                                   "produto desde o PR 8 (decisão D8): a jornada as copia da spec e só mapeia as telas. "
                                   "Se a mudança deve valer, o PO a pede no **Refazer** (a triagem leva o item a "
                                   "Produto); senão, a Seção 5 volta a copiar a spec.")})

    if decidido["classe"] != MINI_JOGO:
        if da_jornada["fases"] or da_jornada["regras"]:
            proposta("jogo-fora-da-spec", (
                f"a Seção 5 da jornada traz {len(da_jornada['fases'])} fase(s) e {len(da_jornada['regras'])} regra(s) de "
                f"jogo, e a spec decide {decidido['classe'] or 'a classe'} (`{decidido['secao'] or '—'}`): mini-jogo "
                "é escolha do PO"))
    else:
        for n, fase in sorted(da_jornada["fases"].items()):
            if n not in da_spec["fases"]:
                proposta("fase-fora-da-spec", (
                    f"a jornada acrescenta a fase {n}" + (f" «{fase['nome']}»" if fase["nome"] else "")
                    + f", que a spec não tem (a spec tem {len(da_spec['fases'])} fase(s))"))
            elif fase["regra"] and da_spec["fases"][n]["regra"] and _norm(fase["regra"]) != _norm(da_spec["fases"][n]["regra"]):
                proposta("regra-de-fase-mudada", (
                    f"a jornada muda a regra da fase {n}: «{fase['regra'][:120]}» no lugar de "
                    f"«{da_spec['fases'][n]['regra'][:120]}»"))
        for n, regra in sorted(da_jornada["regras"].items()):
            if n not in da_spec["regras"]:
                proposta("regra-fora-da-spec", f"a jornada acrescenta a regra R{n} «{regra[:120]}», que a spec não tem")
            elif _norm(regra) != _norm(da_spec["regras"][n]):
                proposta("regra-de-jogo-mudada", (f"a jornada muda a regra R{n}: «{regra[:120]}» no lugar de "
                                                  f"«{da_spec['regras'][n][:120]}»"))
        sem_tela = [n for n in sorted(da_spec["fases"]) if n not in da_jornada["fases"]]
        if da_spec["fases"] and sem_tela:
            achados.append({"severidade": "atencao", "codigo": "fase-sem-tela", "etapa": "design",
                            "agente_responsavel": "jornada", "resumo": (
                                "Fase(s) da spec sem linha na Seção 5 da jornada, e portanto sem tela: "
                                + ", ".join(f"{n} «{da_spec['fases'][n]['nome']}»" for n in sem_tela)
                                + ". A Seção 5 copia todas as fases da spec e diz quais telas cada uma ocupa.")})
    return {"achados": achados, "contagem": {"fases_da_spec": len(da_spec["fases"]),
                                             "fases_da_jornada": len(da_jornada["fases"]),
                                             "regras_da_spec": len(da_spec["regras"]),
                                             "regras_da_jornada": len(da_jornada["regras"])}}
