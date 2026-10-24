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
#: «Classe:» no começo da linha ou depois de «·» na mesma linha — a linha que o 067 prescreve é «- **Seção do DS:** `…` ·
#: **Classe:** mini-jogo» (revisão do PR #76, 24/10/2026: só o começo da linha era lido, e a troca de classe passava).
_RE_CLASSE_NO_BLOCO = re.compile(
    r"(?:^[\s>*-]*|[·|]\s*)(?:\*\*)?classe(?:\s+do\s+ambiente)?(?:\*\*)?\s*:\s*(?:\*\*)?\s*([^\n·|]+)", re.I | re.M)
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
#: Os marcadores que podem perguntar a escolha da classe ou do ambiente (o [PARÂMETRO] pergunta um valor, nunca ela).
_RE_PROPOSTA_ABERTA = re.compile(r"\[PROPOSTA\b([^\]\n]*)\]|\[ABERTO\s*[—–-]\s*dono:\s*(?:o\s+)?PO\b([^\]\n]*)\]")
#: O que o de acordo de produto grava no lugar da proposta (`tools/fechar_contrato._texto_gravado`) e na linha da
#: `secao_ds` (`escolhas_de_ambiente`): «aprovada — PO, parecer de <data>[: <a proposta>]» ou «recusada — …».
_RE_DECISAO_GRAVADA = re.compile(r"\b(aprovad[oa]s?|recusad[oa]s?)\s*[—–-]\s*PO,\s*parecer\s+de\s+[\d/]+(?:\s*:\s*(.*))?",
                                 re.I)
#: «Outro valor» numa proposta: «<valor> — PO, parecer de <data> (no lugar da proposta: <a proposta>)».
_RE_OUTRO_GRAVADO = re.compile(r"(\S[^—–\n]*?)\s*[—–-]\s*PO,\s*parecer\s+de\s+[\d/]+\s*\(no\s+lugar\s+da\s+proposta:\s*"
                               r"([^)\n]*)\)", re.I)
_RE_MINIJOGO = re.compile(r"\bmini-?\s?jogos?\b|\bminijogos?\b", re.I)
_RE_AMBIENTE_NOVO = re.compile(r"\bambiente\s+novo\b|\bapp\s+novo\b|\bse[çc][ãa]o\s+nova\b|\bnova\s*:", re.I)
#: Onde a proposta da escolha começa: a classe, o ambiente novo ou a seção — «mini-jogo `minijogo:<nome>` no lugar de app
#: clonado» (o formato de `ambiente-e-minijogo.md`), «ambiente novo `nova:<nome>`» (o do manifesto). «Duração da fase do
#: `minijogo:<nome>`» nomeia a seção e não é a escolha: é um parâmetro do jogo.
_RE_INICIO_DA_ESCOLHA = re.compile(
    r"^(?:(?:usar|adotar|criar|montar|manter|aprovar|propor|trocar\s+para)\s+)?(?:(?:o|a|um|uma|como)\s+)*"
    r"(?:mini-?\s?jogos?\b|minijogos?\b|ambientes?\s+nov[oa]s?\b|apps?\s+nov[oa]s?\b|se[çc][ãa]o\s+nova\b|classe\b|"
    r"ambiente\b|se[çc][ãa]o\s+do\s+ds\b|secao_ds\b|(?:nova|minijogo):)", re.I)
#: Palavras que negam o mini-jogo pedido no briefing: «não é mini-jogo», «nada de mini-jogo», «em vez de mini-jogo».
_NEGACOES = frozenset({"nao", "nem", "sem", "nunca", "jamais", "nada", "evitar", "vez", "lugar"})
#: Linha de regra ou fase de jogo dentro do bloco 14: o que é conteúdo de produto desde este PR. Procurado só no rótulo da
#: linha (`_RE_LINHA_COM_ROTULO`): «Demonstração na tela: … o áudio lê a regra da fase» é UI que cita o termo.
_RE_DEFINE_JOGO = re.compile(
    r"(?:como\s+(?:se\s+)?(?:vence|perde)|o\s+que\s+(?:é|e)\s+uma\s+fase|quantas\s+fases|fases_sugeridas|"
    r"intervalo\s+de\s+fases|regra\s+da\s+fase|como\s+o\s+progresso\s+aparece|vence\s+a\s+fase|perde\s+a\s+fase)", re.I)
#: A linha «rótulo: valor» da ficha — o rótulo é o que vem antes dos primeiros dois-pontos, sem a marca de lista ou de
#: título. A linha de tabela fica de fora: as fases em tabela são lidas por `_ler_regras_e_fases`.
_RE_LINHA_COM_ROTULO = re.compile(r"^\s*(?:#{1,6}\s+)?(?:[-*+]\s+|\d{1,2}[.)]\s+)?([^:\n|]{1,80}):(.*)$")
#: Palavras que fazem da seção citada depois delas, na linha «Seção do DS:», contexto e não seção da ficha: «`unoochat`
#: (… não o legado `whatsappmobile`)», «sucessora de `whatsappmobile`», «em vez de `instanooria`».
_RE_SECAO_DE_CONTEXTO = re.compile(
    r"\b(?:nao|nem|legad[oa]s?|antig[oa]s?|sucessor[a]?\s+d[eoa]s?|em\s+vez\s+d[eoa]s?|no\s+lugar\s+d[eoa]s?|"
    r"substitu\w*)\b")


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
    from tools.cobertura_design import _secao_por_titulo

    corpo = _secao_por_titulo(texto or "", _RE_TITULO_REGRAS) or ""
    return {"secao": bool(corpo.strip()), **_ler_regras_e_fases(corpo)}


#: Coluna que só uma tabela de fases de jogo tem: com ela, a coluna «#» é o número da fase, fora da seção «Regras e
#: fases». Sem ela, «| # | Componente | Tokens |» da ficha não é fase.
_RE_COLUNA_DE_JOGO = re.compile(r"^(?:regra|como\s+vence|vence|como\s+perde|perde|ideia\s+nova|verbo\s+do\s+jogo)")


def _ler_regras_e_fases(corpo: str, fora_da_secao: bool = False) -> Dict[str, Any]:
    """`{regras, fases}` do corpo. `fora_da_secao`: o corpo não é a seção «Regras e fases» (o bloco 14 inteiro), e a
    tabela só é de fases com a coluna «Fase», ou com «#» e uma coluna de jogo (regra, vence, perde, ideia nova)."""
    from tools.cobertura_design import tabelas

    regras: Dict[int, str] = {}
    for m in _RE_REGRA.finditer(corpo or ""):
        if m.group(0).lstrip().startswith("|"):
            continue
        regras.setdefault(int(m.group(1)), m.group(2).strip(" `*"))
    fases: Dict[int, Dict[str, str]] = {}
    for cab, linhas in tabelas(corpo or ""):
        numero = [c for c in cab if c in ("#", "n", "no", "nº", "n.º", "numero", "número") or c.startswith("fase")]
        if fora_da_secao and not any(_RE_COLUNA_DE_JOGO.match(c) for c in cab):
            numero = [c for c in numero if c.startswith("fase")]
        col_n = numero[0] if numero else None
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
                                               "linha": " | ".join(v for v in linha.values())[:240],
                                               "inteira": " ".join(linha.values())})
    return {"regras": regras, "fases": fases}


def _cabeca_da_proposta(texto: str) -> str:
    """A proposta sem o «por quê» e a alternativa, sem marcação e em minúsculas: «mini-jogo minijogo:varal no lugar de app
    clonado»."""
    cabeca = re.split(r"\s+·\s+|\s*\bpor\s+qu[eê]\s*:", texto or "", maxsplit=1, flags=re.I)[0]
    cabeca = re.sub(r"[`*]+", " ", cabeca).lower()
    cabeca = re.sub(r"\b(nova|minijogo)\s*:\s*", r"\1:", cabeca)
    return " ".join(cabeca.split()).strip(" .;:—–-")


def sobre_a_escolha(texto: str, secao: str = "") -> bool:
    """A proposta (ou o assunto dela) pergunta a escolha da classe ou do ambiente — e não um parâmetro do jogo.

    Ela nomeia a escolha (a seção `nova:`/`minijogo:` — a do bloco 0, quando `secao` vem —, «mini-jogo» ou «ambiente
    novo») e começa por ela («mini-jogo `minijogo:<nome>` no lugar de app clonado», o formato de
    `ambiente-e-minijogo.md`), ou troca a classe ou a seção por ela («trocar a `unoogaleria` pelo `minijogo:<nome>`»). Na
    revisão do PR #76 (24/10/2026) bastava a linha citar a seção: «Duração da fase do `minijogo:varal-do-dia`: 90 s — PO,
    parecer de …» contava como o PO ter aprovado o mini-jogo. Na dúvida, não é a escolha — e o de acordo a pergunta."""
    cabeca = _cabeca_da_proposta(texto)
    if not cabeca or not _nomeia_a_escolha(cabeca, secao):
        return False
    comeca = bool(_RE_INICIO_DA_ESCOLHA.match(cabeca) or (secao and cabeca.startswith(secao)))
    contra = re.search(r"\b(?:no\s+lugar|em\s+vez)\s+d[eoa]s?\s+", cabeca)
    if contra:
        antes, depois = cabeca[:contra.start()], cabeca[contra.end():]
        # a escolha é o que entra, não o que sai: «usar a unoochat no lugar do `minijogo:x`» recusa o mini-jogo
        if not _nomeia_a_escolha(antes, secao) or (secao and secao in depois):
            return False
        alvo = (r"(?:(?:o|a|um|uma)\s+)?(?:apps?\b|ambientes?\b|se[çc][ãa]o\b|classe\b|"
                + "|".join(re.escape(v) for v in sorted(_vocabulario(), key=len, reverse=True)) + ")")
        return comeca or bool(re.match(alvo, depois))
    if comeca:
        return True
    troca = re.search(r"\btroc\w*\b.{0,60}?\b(?:pel[oa]s?|por|para)\s+(.*)$", cabeca)
    return bool(troca and _nomeia_a_escolha(troca.group(1), secao))


def _nomeia_a_escolha(texto: str, secao: str = "") -> bool:
    """O texto nomeia o ambiente novo ou o mini-jogo — a seção do bloco 0, quando vem, e não outra `nova:`/`minijogo:`."""
    tokens = re.findall(r"\b(?:nova|minijogo):[a-z0-9][a-z0-9-]*", texto)
    if secao and tokens and secao not in tokens:
        return False  # a proposta de outro ambiente novo não responde por este
    return bool(tokens or (secao and secao in texto) or _RE_MINIJOGO.search(texto) or _RE_AMBIENTE_NOVO.search(texto))


def escolha_a_conferir(secao: str, briefing: str = "", secoes: Optional[Dict[str, Optional[str]]] = None) -> bool:
    """A escolha do PO sobre o ambiente novo ou o mini-jogo do bloco 0 é conferida — a mesma regra do manifesto
    (`tools.rastro.validar_manifesto`), em todo lugar que a confere ou a pergunta: não quando a seção nova repete uma
    coleção que o DS já tem (`colecao_que_ja_cobre`: `nova:galeriadefotos` → `unoogaleria`) nem quando o briefing fixa
    outra seção (`achado_secao_travada`). Nos dois casos o manifesto bloqueia por outro motivo, mais preciso, e a seção não
    vale nem com o PO aprovando. Na revisão do PR #76 (24/10/2026), o de acordo da exp01ef1b pedia ao PO a aprovação do
    `nova:galeriadefotos`, que o gate ignorava, e o D9 a cobrava como `escolha-de-ambiente-sem-o-po`."""
    from tools import rastro

    secao = (secao or "").strip().strip("`").lower()
    if not secao:
        return False
    if secoes is None:
        secoes = rastro.secoes_ds()
    if re.match(r"^nova\s*:", secao) and rastro.colecao_que_ja_cobre(secao.split(":", 1)[1], secoes):
        return False
    return not rastro.achado_secao_travada(secao, briefing or "", "a spec", secoes)


def secoes_para_o_de_acordo() -> List[str]:
    """As seções que o PO pode escrever no de acordo para a spec calada: a lista de missão nova de `ambientes.md` (as do
    DS, menos as legadas e a da plataforma). Ambiente novo e mini-jogo pedem a spec refeita — os componentes da seção
    nova, as regras e as fases do jogo no bloco 2 —, e a legada só vale fixada no briefing ou no one-pager do PO."""
    from tools import rastro

    try:
        todas = set(rastro.secoes_ds())
    except Exception:  # pragma: no cover - base da plataforma indisponível
        todas = set()
    return sorted(todas - set(rastro.SECOES_LEGADAS) - {SECAO_DA_PLATAFORMA})


#: O marcador que pergunta a classe e o ambiente da spec calada — o que o 046 escreve no bloco 15: «[ABERTO — dono: PO:
#: classe e ambiente da missão — `unoogaleria`, `unoochat` ou `unoovista`]».
_RE_PERGUNTA_DA_SECAO = re.compile(
    r"\bclasse\s+e\s+(?:o\s+)?ambiente\b|\bambiente\s+da\s+miss[ãa]o\b|\bse[çc][ãa]o\s+do\s+(?:ds|design\s+system)\b|"
    r"\bsecao_ds\b", re.I)


def pergunta_a_secao(texto: str) -> bool:
    """O marcador pergunta a classe e o ambiente da missão (a `secao_ds` que o bloco 0 não tem)."""
    return bool(_RE_PERGUNTA_DA_SECAO.search(texto or ""))


def _linha_da_secao(linha: str, secao: str) -> bool:
    """A linha que fixa a seção: o campo `secao_ds` da spec ou a «Seção do DS:» do one-pager, com a seção do bloco 0."""
    if re.search(r"secao_ds\W{0,6}" + re.escape(secao).replace(":", r"\s*:\s*"), linha, re.I):
        return True
    rotulo = _RE_ROTULO_SECAO.search(linha)
    return bool(rotulo and secao in re.sub(r"\s*:\s*", ":", rotulo.group(1).lower()))


def _minijogo_no_briefing(briefing: str) -> bool:
    """O briefing pede mini-jogo: a palavra sem negação nas três antes — «não é mini-jogo», «nada de mini-jogo», «app
    clonado em vez de mini-jogo» não pedem (revisão do PR #76: só a palavra contava)."""
    for m in _RE_MINIJOGO.finditer(briefing or ""):
        antes = re.sub(r"[^a-z0-9]+", " ", _sem_acento(briefing[max(0, m.start() - 60): m.start()]).lower()).split()
        if not set(antes[-3:]) & _NEGACOES:
            return True
    return False


def _escolha(spec: str, one_pager: str = "", briefing: str = "", decisoes_do_po: Optional[Iterable[Any]] = None,
             decidido: Optional[Dict[str, Any]] = None, one_pager_po: str = "") -> Dict[str, str]:
    """`{status, valor}` de `escolha_do_po`; `valor` é o que o PO escreveu no lugar da proposta («outro valor»)."""
    from tools.rastro import secao_travada

    d = decidido or classe_e_ambiente(spec)
    if not d["nova"]:
        return {"status": "nao_se_aplica", "valor": ""}
    secao = d["secao"]
    aprovada = recusada = pendente = False
    valor = ""
    for texto in (spec, one_pager):
        for linha in (texto or "").splitlines():
            da_secao = _linha_da_secao(linha, secao)
            # a resposta gravada: na linha da seção (o item que o de acordo abre sozinho grava ali, sem a proposta) ou
            # com a proposta da escolha depois dos dois-pontos. «90 s — PO, parecer de» é um [PARÂMETRO]: não conta
            for m in _RE_DECISAO_GRAVADA.finditer(linha):
                proposta = (m.group(2) or "").strip()
                if (da_secao and not proposta) or (proposta and sobre_a_escolha(proposta, secao)):
                    if m.group(1).lower().startswith("recusad"):
                        recusada = True
                    else:
                        aprovada = True
            for m in _RE_OUTRO_GRAVADO.finditer(linha):
                # «outro valor» na proposta da escolha é recusa da seção proposta: a que o PO escreveu vai a produto
                # pelo Refazer, nunca vale como aprovação (revisão do PR #76: «unoojornal — PO, parecer de … (no lugar da
                # proposta: mini-jogo …)» aprovava o mini-jogo)
                if sobre_a_escolha(m.group(2), secao):
                    recusada, valor = True, m.group(1).strip(" -*`")
            for m in _RE_PROPOSTA_ABERTA.finditer(linha):
                if m.group(1) is not None:
                    partes = re.split(r"\bPO\s*:", m.group(1), maxsplit=1)
                    descricao = partes[1] if len(partes) > 1 else ""
                else:
                    descricao = m.group(2).lstrip(" :—–-")
                if (da_secao and not descricao.strip()) or sobre_a_escolha(descricao, secao):
                    pendente = True
    ultima: Optional[Dict[str, Any]] = None
    for registro in decisoes_do_po or []:
        if not isinstance(registro, dict):
            continue
        assunto = str(registro.get("assunto") or "")
        tipo = str(registro.get("tipo") or "")
        if tipo == "escolha_ambiente":
            # o item que o de acordo abre sozinho é de uma seção: a recusa de `nova:x` não responde por `minijogo:y`
            if re.search(r"`\s*" + re.escape(secao).replace(":", r"\s*:\s*") + r"\s*`", assunto.lower()):
                ultima = registro
        elif tipo in ("proposta", "aberto_po", "") and sobre_a_escolha(assunto, secao):
            ultima = registro
    if ultima is not None:
        resposta = str(ultima.get("resposta") or "")
        if resposta == "aceitar":
            aprovada, recusada = True, False
        elif resposta in ("recusar", "outro"):
            aprovada, recusada = False, True
            valor = str(ultima.get("valor") or "") if resposta == "outro" else ""
    if recusada:
        return {"status": "recusada", "valor": valor}
    if aprovada:
        return {"status": "aprovada", "valor": ""}
    trava = secao_travada(briefing or "", {})
    if trava and trava.get("explicita"):
        if trava["secao"] == secao:
            return {"status": "briefing", "valor": ""}
        # o briefing fixou outra seção: a palavra «mini-jogo» nele não decide esta (a trava é conferida no manifesto)
    elif d["classe"] == MINI_JOGO and _minijogo_no_briefing(briefing):
        return {"status": "briefing", "valor": ""}
    # o one-pager que o PO anexou é documento dele: a «Seção do DS» do cabeçalho vale como o briefing (como a legada em
    # `rastro._legada_fixada_pelo_po`)
    cabecalho = re.search(r"Se[çc][ãa]o do DS\**\s*[:=]\s*\**\s*`?([a-z][\w:-]*)", (one_pager_po or "")[:6000], re.I)
    if cabecalho and re.sub(r"\s*:\s*", ":", cabecalho.group(1).lower()) == secao:
        return {"status": "briefing", "valor": ""}
    return {"status": "pendente" if pendente else "silencio", "valor": ""}


def escolha_do_po(spec: str, one_pager: str = "", briefing: str = "", decisoes_do_po: Optional[Iterable[Any]] = None,
                  decidido: Optional[Dict[str, Any]] = None, one_pager_po: str = "") -> str:
    """Quem decidiu o ambiente novo ou o mini-jogo do bloco 0: `briefing` (o briefing ou o one-pager que o PO anexou o
    fixam) · `aprovada` · `recusada` (o PO respondeu no de acordo, «— PO, parecer de <data>»; «outro valor» na proposta
    da escolha é recusa) · `pendente` (o marcador espera o de acordo) · `silencio` (ninguém perguntou) · `nao_se_aplica`
    (ambiente existente da lista: produto escolhe pela tabela de `ambientes.md`).

    Só a linha da escolha conta: a da `secao_ds` (ou a «Seção do DS:» do one-pager), a proposta da escolha
    (`sobre_a_escolha`) e o registro `escolha_ambiente` da mesma seção. Linha que só cita a seção — o [PARÂMETRO] da
    duração da fase do mini-jogo — não responde a escolha."""
    return _escolha(spec, one_pager, briefing, decisoes_do_po, decidido, one_pager_po)["status"]


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
    if conferir_escolha and d["nova"] and escolha_a_conferir(d["secao"], briefing):
        resposta = _escolha(spec, one_pager, briefing, decisoes_do_po, d, one_pager_po=one_pager_po)
        escolha = resposta["status"]
        rotulo = "o mini-jogo" if d["classe"] == MINI_JOGO else "o ambiente novo"
        if escolha == "recusada":
            achados.append({"severidade": "bloqueio", "campo": "secao_ds", "etapa": "produto",
                            "codigo": "escolha-de-ambiente-recusada", "resumo": (
                                f"O PO recusou {rotulo} (`{d['secao']}`) no de acordo, e o bloco 0 ainda o fixa. "
                                + (f"Ele escreveu «{resposta['valor']}» no lugar: a troca vai a produto pelo **Refazer**, "
                                   "e a spec volta com ela. " if resposta["valor"] else "")
                                + "Refaça a spec com um ambiente existente da lista de `ambientes.md` (ambiente "
                                "existente antes de ambiente novo).")})
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


def secoes_do_bloco_14(bloco: str, envelope: Optional[Dict[str, Any]] = None, decidida: str = "") -> List[str]:
    """As seções do DS que a ficha nomeia: a primeira de cada linha «Seção do DS:» (o valor, conhecido ou não — é o que
    pega a seção inventada sem prefixo), as outras dela que sejam seção conhecida, `secao_ds:` e o envelope.

    `decidida`: a `secao_ds` do bloco 0. Com ela `nova:<nome>` ou `minijogo:<nome>`, a ficha que escreve só `<nome>` nomeia
    a mesma seção — e `minijogo-<nome>`, o nome da seção do DS do mini-jogo no prompt 067, é `minijogo:<nome>` (revisão do
    PR #76, 24/10/2026: as duas formas bloqueavam o mini-jogo e o ambiente novo que o PO aprovou)."""
    vocab = _vocabulario()
    por_tamanho = sorted(vocab, key=len, reverse=True)
    saida: List[str] = []
    nome_decidido = decidida.split(":", 1)[1] if decidida.startswith(("nova:", "minijogo:")) else ""

    def pôr(token: str, primeiro: bool) -> None:
        t = re.sub(r"\s*:\s*", ":", token.strip().strip("`*_ ,.;").lower())
        # a ponte ou o nome do pacote da seção (`@edu/ui/ds-unoochat`, `ds-unoochat`) nomeiam a mesma seção
        t = re.sub(r"^ds-", "", re.sub(r"^@?edu/ui/", "", t))
        t = re.sub(r"^minijogo-(?=[a-z0-9])", "minijogo:", t)
        if nome_decidido and t == nome_decidido:
            t = decidida
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
        crases = list(re.finditer(r"`([^`\n]+)`", valor))
        if crases:
            fim = 0
            for i, crase in enumerate(crases):
                entre = _sem_acento(valor[fim:crase.start()]).lower()
                fim = crase.end()
                if i and _RE_SECAO_DE_CONTEXTO.search(entre):
                    # «`unoochat` (tema claro, ADR-134 — não o legado `whatsappmobile`)»: a legada é contexto, não seção
                    # da ficha. A tabela de `ambientes.md` traz «`unoochat` (e o legado `whatsappmobile`)», e o D9 já
                    # escreveu contexto nesta linha (8ce9c32d, 25/09/2026); no refazer da exp03em1b a ficha era descartada
                    # e bloqueava como decisão de produto (revisão do PR #76, 24/10/2026)
                    continue
                pôr(crase.group(1), i == 0)
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
    fases, «como se vence/perde uma fase», «quantas fases». Citar a regra da spec palavra por palavra não é decidir.

    A regra e a tabela são procuradas no bloco inteiro, não só sob um título «Regras e fases»: «### Regras do jogo» com
    `R1`, ou uma tabela «| Fase | Nome |» solta na ficha, passavam (revisão do PR #76, 24/10/2026). Fora da seção, a
    tabela com a coluna «#» só é de fases com uma coluna de jogo (regra, vence, perde) — «| # | Componente |» é da ficha.

    A linha em prosa conta só quando o termo está no rótulo, antes dos dois-pontos («**Como se vence uma fase:** …»), e o
    valor não é o texto do bloco 2 da spec. Na revisão do PR #76 (24/10/2026) bastava a linha citar o termo: as linhas que
    o próprio template do 067 pede — «Demonstração na tela: … o áudio do guia lê a regra da fase», «Estados de tela do jogo:
    … quando a criança vence a fase, confete», «Mapa de mundo como tela: …; como o progresso aparece: …» — bloqueavam a
    ficha do mini-jogo aprovado."""
    from tools.bncc import secao_bloco

    da_spec = {_norm(l) for l in (spec or "").splitlines() if l.strip()}
    bloco2 = f" {_norm(secao_bloco(spec or '', 2) or spec or '')} "
    secao = regras_e_fases(bloco)
    solto = _ler_regras_e_fases(bloco, fora_da_secao=True)
    regras = {**solto["regras"], **secao["regras"]}
    fases = {**solto["fases"], **secao["fases"]}
    saida = [f"R{n} {t}" for n, t in sorted(regras.items())]
    # a linha da tabela de fases igual à da spec é cópia: compara as células, sem a barra
    saida += [f"fase {n}: {f['linha']}" for n, f in sorted(fases.items()) if _norm(f["inteira"]) not in da_spec]
    for linha in (bloco or "").splitlines():
        m = _RE_LINHA_COM_ROTULO.match(linha)
        if not m or not _RE_DEFINE_JOGO.search(m.group(1)) or not m.group(2).strip(" *_`"):
            continue
        valor = _norm(m.group(2))
        # «Regra da fase 1: Ponha a foto do café antes da escola.» repete o bloco 2: cópia, não decisão (com três palavras
        # ou mais — «Quantas fases: 3» não se confere por trecho)
        if _norm(linha) in da_spec or (len(valor.split()) >= 3 and f" {valor} " in bloco2):
            continue
        saida.append(linha.strip()[:200])
    return [s for s in dict.fromkeys(saida) if _norm(s) not in da_spec]


def _placeholder(proposta: str) -> bool:
    """A proposta é só o formato: «…», «<a troca> · por quê: <…> · alternativa: <…>» — nada além de marcação."""
    resto = re.sub(r"<[^>]*>|…|\.\.\.|\b(?:por\s+qu[eê]|alternativa)\s*:", " ", proposta or "", flags=re.I)
    return not re.search(r"\w", resto)


def devolucoes_do_d9(texto: str, envelope: Optional[Dict[str, Any]] = None) -> List[str]:
    """O que o D9 devolve a produto: o campo `devolucao` do envelope (objeto ou lista, com `proposta`), os
    `[PROPOSTA …]` do Passo 3 e, na resposta de antes deste PR, o pedido de re-spec `[RS-AMB]`."""
    env = envelope if isinstance(envelope, dict) else {}
    saida: List[str] = []
    bruto = env.get("devolucao")
    for d in (bruto if isinstance(bruto, list) else [bruto] if bruto else []):
        if isinstance(d, dict):
            partes = [str(d.get(k) or "").strip() for k in ("proposta", "por_que", "alternativa")]
            if partes[0] and not _placeholder(partes[0]):
                saida.append(partes[0] + (f" · por quê: {partes[1]}" if partes[1] else "")
                             + (f" · alternativa: {partes[2]}" if partes[2] else ""))
        elif isinstance(d, str) and d.strip() and not _placeholder(d):
            saida.append(d.strip())
    m = re.search(D9_DEVOLUCAO_INICIO, texto or "", re.M)
    if m:
        fim = re.search(r"^#{2,3}\s", texto[m.end():], re.M)
        trecho = texto[m.end(): m.end() + fim.start()] if fim else texto[m.end():]
        for marcador in re.finditer(r"\[PROPOSTA\b[^\]\n]*?:\s*([^\]\n]+)\]", trecho):
            proposta = marcador.group(1).strip()
            if _placeholder(proposta):
                # «Nenhuma. Nenhum verbo pede `[PROPOSTA — validar com PO: …]`»: o formato citado, não uma devolução — com
                # ESTEIRA_ESTRITA virava bloqueio (revisão do PR #76, 24/10/2026)
                continue
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
    nomeadas = secoes_do_bloco_14(bloco, envelope, decidida=decidido["secao"])
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
        # a escolha do PO pela mesma regra do manifesto: a seção nova que repete uma coleção do DS, ou que o briefing não
        # fixou porque fixou outra, é bloqueada lá — cobrá-la aqui pedia ao PO o que o gate ignora (exp01ef1b,
        # `nova:galeriadefotos`; revisão do PR #76, 24/10/2026)
        if decidido["nova"] and escolha_a_conferir(decidido["secao"], str(estado.get("briefing") or "")):
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
