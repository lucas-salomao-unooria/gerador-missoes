"""Missão em mais de uma seção do design system — o que se confere em código.

Decisão do PO de 15/10/2026: a ideação pode combinar seções do DS quando isso ajuda a medir uma habilidade (fazer
algo no chat, compartilhar, ver outra coisa na mensageria), como se a plataforma já suportasse — na codificação
entram quantas pontes `@edu/ui/ds-*` forem necessárias. O limite é a carga cognitiva da criança: cada app novo é
uma interface nova a aprender.

O formato não quebra quem lê uma seção só: `secao_ds` continua escalar e é a **principal** (a trava do briefing vale
para ela); as outras vão em `secoes_ds_extras`, e a missão declara onde cada seção fala («Mapa de seções») e como o
estudante passa de uma para outra («Transições» — sempre um gatilho da história: notificação, link, compartilhar).

Teto por ano `[EXTRAPOLAÇÃO — validar com PO]`, contando a principal e as extras; a seção `unooria` é a plataforma,
não um clone, e não conta: 1º–3º EF uma seção · 4º–5º EF até duas · 6º EF ao 3º EM até três.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional

#: Teto de seções clonadas por série (decisão do PO de 15/10/2026, [EXTRAPOLAÇÃO]).
TETO_POR_SERIE = {"1EF": 1, "2EF": 1, "3EF": 1, "4EF": 2, "5EF": 2}
TETO_PADRAO = 3
#: A plataforma em si: pode aparecer em qualquer missão e não conta no teto.
SECAO_DA_PLATAFORMA = "unooria"
#: Valor que diz "nenhuma extra".
_VAZIOS = {"", "nenhuma", "nenhum", "vazio", "n/a", "na", "—", "-", "[]"}

_RE_EXTRAS = re.compile(
    r"(?:secoes_ds_extras|se[çc][õo]es\s+extras(?:\s+do\s+ds)?)[`*_]*\s*[:=]\s*\**\s*([^\n|]*)", re.IGNORECASE)
_RE_SECAO = re.compile(r"[a-z][a-z0-9]*(?::[a-z0-9-]+)?", re.IGNORECASE)
_RE_SERIE_CAMPO = re.compile(r"series[`*_]*\s*:\s*[`*_]*\s*\[\s*[\"']?(\d{1,2}(?:EF|EM))", re.IGNORECASE)
_RE_ID = re.compile(r"\bexp(0[1-9])(ef|em)[1-4]b\b", re.IGNORECASE)
_RE_PROIBE_OUTRAS = re.compile(
    r"proibid[oa][^.\n]{0,80}\boutr[oa]s?\s+(?:design\s+system|se[çc][ãa]o|se[çc][õo]es|ds|interfaces?|apps?)",
    re.IGNORECASE)


def _norm(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower())
                   if unicodedata.category(c) != "Mn").strip(" `*_")


def teto(serie: Optional[str]) -> int:
    return TETO_POR_SERIE.get((serie or "").upper(), TETO_PADRAO)


def serie_do_texto(texto: str) -> Optional[str]:
    """A série pelo campo `series: ["7EF"]` ou pelo identificador `exp07ef1b`."""
    m = _RE_SERIE_CAMPO.search(texto or "")
    if m:
        return m.group(1).upper()
    m = _RE_ID.search(texto or "")
    return f"{int(m.group(1))}{m.group(2).upper()}" if m else None


#: Onde termina o valor do campo numa linha de metadados: «nenhuma · **Modalidade:** duplas…», «nenhuma — …», «;».
_RE_FIM_DO_CAMPO = re.compile(r"\s*[·•]\s*|\s+[—–]\s+|;|\*\*|\|")
#: O valor é uma lista de seções: cada item é um identificador (`unoochat`, `nova:galeria`), não uma frase.
_RE_ID_SECAO = re.compile(r"^[a-z][a-z0-9]*(?::[a-z0-9-]+)?$")
_RE_TITULO = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)
#: A seção 0 do one-pager («## 0. Identificação») e o bloco 0 da spec — onde o campo é declarado.
_RE_TITULO_DA_SECAO_0 = re.compile(r"^(?:bloco\s+)?0\s*[.)—–:-]|^identifica|^ficha", re.IGNORECASE)
#: Changelog e «O que mudou»: o campo citado ali é relato, não declaração.
_RE_TITULO_DE_RELATO = re.compile(r"changelog|o que mudou|hist[óo]rico|vers[õo]es anteriores", re.IGNORECASE)


def _valor_do_campo(bruto: str) -> str:
    valor = re.sub(r"\([^)]*\)", " ", bruto or "")  # comentário entre parênteses não é seção
    valor = _RE_FIM_DO_CAMPO.split(valor, maxsplit=1)[0]
    valor = re.split(r"\.(?:\s|$)", valor, maxsplit=1)[0]  # «nenhuma. A missão usa só a galeria.»
    return valor.strip(" \t`*_\"'«»“”")


def _declaracao(valor: str) -> Optional[List[str]]:
    """As seções da declaração; `[]` para «nenhuma»; `None` quando o valor é prosa, e não uma lista de seções."""
    corpo = valor.strip().strip("[]").strip()
    if _norm(corpo) in _VAZIOS:
        return []
    secoes: List[str] = []
    for parte in re.split(r",|\s+e\s+|\s*\+\s*", corpo):
        s = re.sub(r"\s*:\s*", ":", parte.strip(" \t`*_\"'«»“”[]")).lower()
        if not s or _norm(s) in _VAZIOS:
            continue
        if not _RE_ID_SECAO.match(s):
            return None
        if s not in secoes:
            secoes.append(s)
    return secoes


def _onde(texto: str, pos: int) -> str:
    """`secao0` | `relato` | `corpo`: o título mais próximo acima da posição diz onde o campo está."""
    titulo = ""
    for m in _RE_TITULO.finditer(texto):
        if m.start() > pos:
            break
        titulo = m.group(2).strip(" *_`")
    if _RE_TITULO_DE_RELATO.search(titulo):
        return "relato"
    return "secao0" if _RE_TITULO_DA_SECAO_0.search(titulo) else "corpo"


def extras(texto: str) -> List[str]:
    """As seções extras declaradas (`secoes_ds_extras: [unoochat, unoovista]` ou «Seções extras do DS: …»).

    Só o valor do campo conta, e só quando ele é uma lista de seções. Até 24/10/2026 o resto da linha entrava: na
    exp02ef1b (4fd72a9a, 22/10) a seção 0 numa linha só («**Seções extras do DS:** nenhuma · **Modalidade:** duplas
    por aparelho…») virou 26 «seções» (`modalidade`, `duplas`, `por`…), o lint acusou seções acima do teto do 2º ano
    e o gate estrutural reprovou o 2.1 — uma rodada gasta para reescrever a seção 0. Na exp01em1b (e3980485) o
    changelog que citava o campo antes da seção 0 era lido no lugar dela, e o gate foi ao teto de 3 rodadas. Vale a
    declaração da seção 0 (ou do bloco 0); a citada num changelog é relato. Sem declaração em forma de lista, a prosa
    só conta pelas seções do DS que ela nomeia — o campo mal escrito não esconde uma extra de verdade."""
    candidatos: List[tuple] = []
    prosas: List[str] = []
    for m in _RE_EXTRAS.finditer(texto or ""):
        valor = _valor_do_campo(m.group(1))
        lista = _declaracao(valor)
        onde = _onde(texto, m.start())
        if lista is None:
            if onde != "relato":
                prosas.append(valor)
            continue
        candidatos.append(({"secao0": 0, "corpo": 1, "relato": 2}[onde], len(candidatos), lista))
    if candidatos:
        return min(candidatos)[2]
    if not prosas:
        return []
    from tools.rastro import SECOES_LEGADAS, secoes_ds

    conhecidas = set(secoes_ds()) | set(SECOES_LEGADAS)
    vistos: List[str] = []
    for s in _RE_SECAO.findall(_norm(prosas[0])):
        if (s in conhecidas or re.match(r"^(nova|minijogo):", s)) and s not in vistos:
            vistos.append(s)
    return vistos


def _tabelas(texto: str, exigidas: List[str]) -> List[List[Dict[str, str]]]:
    """Tabelas cujo cabeçalho tem colunas que COMEÇAM com cada nome exigido (normalizado)."""
    achadas: List[List[Dict[str, str]]] = []
    cabecalho: Optional[List[str]] = None
    corpo: List[Dict[str, str]] = []
    for bruta in (texto or "").splitlines() + [""]:
        linha = bruta.strip()
        if not (linha.startswith("|") and linha.endswith("|")):
            if cabecalho is not None and corpo:
                achadas.append(corpo)
            cabecalho, corpo = None, []
            continue
        celulas = [c.strip() for c in linha.strip("|").split("|")]
        if set("".join(celulas)) <= set("-: "):
            continue
        normal = [_norm(c) for c in celulas]
        if cabecalho is None:
            if all(any(n.startswith(e) for n in normal) for e in exigidas):
                cabecalho = normal
            continue
        corpo.append({cabecalho[i]: celulas[i] for i in range(min(len(cabecalho), len(celulas)))})
    return achadas


def _coluna(linha: Dict[str, str], prefixo: str) -> str:
    return next((v for k, v in linha.items() if k.startswith(prefixo)), "")


def secoes_no_mapa(texto: str) -> List[str]:
    """As seções que o «Mapa de seções» (`| Etapa | Tela/momento | Seção do DS | … |`) põe em alguma tela."""
    vistas: List[str] = []
    for tabela in _tabelas(texto, ["etapa", "secao do ds"]):
        for linha in tabela:
            for s in _RE_SECAO.findall(_norm(_coluna(linha, "secao do ds"))):
                if s not in vistas:
                    vistas.append(s)
    return vistas


def transicoes(texto: str) -> List[Dict[str, str]]:
    """As linhas da tabela «Transições» (`| De | Para | Gatilho na história | Etapa |`)."""
    return [{"de": _coluna(l, "de"), "para": _coluna(l, "para"), "gatilho": _coluna(l, "gatilho")}
            for tabela in _tabelas(texto, ["de", "para", "gatilho"]) for l in tabela]


def _etapa(celula: str) -> str:
    """A etapa pela primeira palavra do nome: o número muda entre one-pager e spec («5. Explicar», «Explicar»), e a
    etapa 4 vem com ou sem o «Aha» («Resultado / Aha», «Resultado/Aha»)."""
    palavras = [p for p in re.findall(r"[a-z]+", _norm(celula)) if p != "etapa"]
    return palavras[0] if palavras else ""


def secoes_da_celula(celula: str) -> List[str]:
    """As seções de uma célula «Seção do DS» («unooriaai», «unooriaai → unoovista», «`unoovista` (extra)»). Lê pela
    forma, não pelo vocabulário do DS: sem a base da plataforma, `secoes_ds()` só conhece as legadas. Prosa não é seção."""
    secoes: List[str] = []
    for parte in re.split(r"→|->|,|/|\+|\s+e\s+", re.sub(r"\([^)]*\)", " ", celula or "")):
        s = re.sub(r"\s*:\s*", ":", parte.strip(" \t`*_\"'«»“”[]")).lower()
        if _RE_ID_SECAO.match(s) and s not in secoes:
            secoes.append(s)
    return secoes


def mapa_por_etapa(texto: str) -> List[Dict[str, Any]]:
    """`{etapa, secoes, celula}` de cada linha das tabelas com «Etapa» e «Seção do DS», na ordem: o «Mapa de seções»
    e, no one-pager, também a «Verificação por etapa» do §5."""
    return [{"etapa": _etapa(_coluna(l, "etapa")), "secoes": secoes_da_celula(_coluna(l, "secao do ds")),
             "celula": _coluna(l, "secao do ds")}
            for tabela in _tabelas(texto, ["etapa", "secao do ds"]) for l in tabela]


def passagens_aprovadas(texto: str) -> set:
    """Os pares `(de, para)` de app a app que o texto aprova: as linhas de «Transições», a troca de seção entre etapas
    seguidas de um mapa e a troca dentro de uma etapa, na ordem escrita («unooriaai → unoovista» no Decidir)."""
    pares = {(a, b) for t in transicoes(texto) for a in secoes_da_celula(t["de"])
             for b in secoes_da_celula(t["para"]) if a != b}
    for tabela in _tabelas(texto, ["etapa", "secao do ds"]):
        anteriores: List[str] = []
        for l in tabela:
            atuais = secoes_da_celula(_coluna(l, "secao do ds"))
            pares |= {(a, b) for a in anteriores for b in atuais if a != b}
            pares |= {(a, b) for i, a in enumerate(atuais) for b in atuais[i + 1:] if a != b}
            if atuais:
                anteriores = atuais
    return pares


def validar(texto: str, principal: str, onde: str, briefing: str = "", serie: Optional[str] = None,
            vocabulario: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
    """Achados sobre as seções extras de `texto` (spec ou one-pager). Sem extra declarada, não há o que conferir."""
    from tools.rastro import SECOES_LEGADAS, secoes_ds

    lista = extras(texto)
    if not lista:
        return []
    secoes = vocabulario if vocabulario is not None else secoes_ds()
    principal = (principal or "").strip().strip("`").lower()
    achados: List[Dict[str, str]] = []

    def achado(codigo: str, resumo: str, severidade: str = "bloqueio") -> None:
        achados.append({"severidade": severidade, "codigo": codigo, "campo": "secoes_ds_extras",
                        "etapa": "produto", "resumo": resumo})

    clones = [s for s in lista if s != SECAO_DA_PLATAFORMA]
    for s in clones:
        if s == principal:
            achado("secao-extra-repetida", f"`{s}` é a seção principal e está também nas extras.", "atencao")
        elif s in SECOES_LEGADAS:
            achado("secao-extra-legada", f"`{s}` é seção legada: missão nova não reproduz a identidade de app de "
                                         f"terceiro (ADR-133 a 138) — use a sucessora (`ambientes.md`).")
        elif not (s in secoes or re.match(r"^(nova|minijogo):", s)):
            achado("secao-extra-desconhecida", f"`{s}` em {onde} não é seção do DS (lista: {sorted(secoes)}).")
    todas = sorted({principal, *clones} - {"", SECAO_DA_PLATAFORMA})
    serie = serie or serie_do_texto(texto)
    if len(todas) > teto(serie):
        achado("secoes-acima-do-teto",
               f"{onde} usa {len(todas)} seções do DS ({', '.join(todas)}) e o teto "
               f"{'do ' + serie if serie else 'sem série declarada'} é {teto(serie)} "
               "[EXTRAPOLAÇÃO — 1º–3º EF: 1 · 4º–5º EF: 2 · 6º EF ao 3º EM: 3]. Cada app novo é uma interface nova a "
               "aprender: tire a seção que menos mede, ou justifique ao PO.")
    no_mapa = secoes_no_mapa(texto)
    passagens = transicoes(texto)
    for s in clones:
        if s == principal:
            continue
        if s not in no_mapa:
            achado("secao-extra-sem-mapa", f"`{s}` está nas extras e nenhuma linha do «Mapa de seções» "
                                           f"(`| Etapa | Tela/momento | Seção do DS | … |`) diz onde ela fala.")
        if not any(s in _norm(t["para"]) for t in passagens):
            achado("secao-extra-sem-transicao",
                   f"Nenhuma linha de «Transições» (`| De | Para | Gatilho na história | Etapa |`) leva o estudante a "
                   f"`{s}`. A troca de app é uma ação nativa (notificação, link, compartilhar), nunca um salto da "
                   "plataforma (critério 2.3c).")
    for t in passagens:
        if not _norm(t["gatilho"]).strip("—- "):
            achado("transicao-sem-gatilho", f"A transição de `{t['de']}` para `{t['para']}` não diz o gatilho na "
                                            f"história que leva o estudante de um app ao outro.")
    proibe = _RE_PROIBE_OUTRAS.search(briefing or "")
    if proibe and clones:
        achado("briefing-proibe-outras-secoes",
               f"O briefing proíbe outras seções (“{proibe.group(0)}”) e {onde} declara extras "
               f"({', '.join(clones)}). A restrição do briefing vale: tire as extras, ou o PO decide.")
    return achados
