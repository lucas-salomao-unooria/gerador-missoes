"""A missão faz o que o PO pediu e o que o briefing fixou? O código extrai, o juiz cita, o código confere.

Na missão do 9º ano (30/09/2026) o PO pediu duas vezes para refazer o produto. O primeiro pedido
definia "Caminho A (maioria): não perguntou… Caminho B (investigativo): perguntou… contrafactual" e
a frase da descoberta inteira, "…que cada um tinha no sistema — e quase deixei de fora quem mais
precisava de ajuda". O segundo pedido apagou o primeiro, o núcleo foi reescrito com A e B trocados e
a frase cortada, e o gate final escreveu "a versão final atende integralmente ao pedido de correção".
Nada conferia: o próprio PO tinha escrito um checklist ("VALIDAÇÃO — depois de gerar, confira: …"),
e ninguém o lia.

Este módulo transforma o que o PO e o briefing disseram num checklist e confere:

- **Extração (código):** os blocos `TRAVAS`, cada `AJUSTE N`, as perguntas de `VALIDAÇÃO`, as frases
  entre aspas e, no briefing, o direcionamento, os passos da experiência e os elementos fixos.
- **Frase entre aspas dentro das TRAVAS (código):** igualdade literal, sem o juiz. Aspas com
  reticências no fim valem pelo começo. Fora das travas a frase entre aspas é contexto ("a consultora
  disse: …") ou exemplo ("algo como: …"): vai ao juiz dentro do AJUSTE em que aparece.
- **O resto (juiz + código):** o juiz diz, item a item, se o documento atende, viola, não trata ou se
  o pedido conflita com uma regra da esteira — e só vale "atende" com citação literal que exista
  no documento. Sem citação conferida, o item não está comprovado. Na dúvida, falha fechada.

Pedido do PO não comprovado é bloqueio: com o 🔴 o *de acordo* da etapa é recusado. Elemento do
briefing não tratado é ressalva. Conflito entre o pedido e uma regra da esteira (o briefing pedia
"o aluno confirma ou muda a escolha" e a regra 7 do núcleo impõe trava irreversível) é decisão
humana: quem decide é o PO, não o agente.
"""
from __future__ import annotations

import functools
import json
import re
import unicodedata
from typing import Any, Dict, List, Optional, Sequence, Tuple

#: Itens demais tornam o juiz raso. O que passa disto é cortado do fim (briefing primeiro).
MAX_ITENS = 60
MIN_PALAVRAS_ITEM = 6
MIN_PALAVRAS_LITERAL = 8
MIN_CITACAO = 15

#: O bloco TRAVAS vai até o próximo bloco — ou até uma lista que começa depois de linha em branco (formato misto).
_RE_TRAVAS = re.compile(r"\bTRAVAS?\b[^:\n]{0,80}:(.*?)(?=\bAJUSTE\s+\d|\bVALIDA[ÇC][ÃA]O\b|"
                        r"\n\s*\n\s*(?:\d{1,2}[.)]|[-*•])\s|$)", re.S)
_RE_AJUSTE = re.compile(r"\b(AJUSTE\s+\d+)\s*[—–-]\s*(.*?)(?=\bAJUSTE\s+\d|\bVALIDA[ÇC][ÃA]O\b|$)", re.S)
_RE_VALIDACAO = re.compile(r"\bVALIDA[ÇC][ÃA]O\b[^:\n]{0,80}:(.*)$", re.S)
_RE_FRASE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9\"“])")
_SECOES_BRIEFING = ("direcionamento pedagógico", "passo a passo", "elementos fixos", "caso de transferência")


def _norm(texto: str) -> str:
    sem = "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")
    sem = re.sub(r"[—–-]", " ", sem)
    # marcação some sem deixar espaço: `latch: locked` entre crases virava "( latch: locked )" e não
    # casava com a citação "(latch: locked)" que o juiz copiou (06/10/2026, primeira execução real)
    sem = re.sub(r"[`*_]+", "", sem)
    sem = re.sub(r"[\"“”'|«»]+", " ", sem)
    sem = re.sub(r"\s+", " ", sem)
    sem = re.sub(r"\s+([,.;:!?)\]])", r"\1", sem)
    sem = re.sub(r"([(\[])\s+", r"\1", sem)
    return sem.strip(" .")


def _palavras(texto: str) -> int:
    return len(re.findall(r"\w+", texto or ""))


def _frases(bloco: str) -> List[str]:
    """Frases do bloco; as curtas ("Não trocar.", "Idêntico.") colam na anterior, que lhes dá sentido."""
    saida: List[str] = []
    for f in _RE_FRASE.split(re.sub(r"\s+", " ", bloco or "").strip()):
        f = f.strip()
        if not f:
            continue
        if saida and _palavras(f) < MIN_PALAVRAS_ITEM:
            saida[-1] = f"{saida[-1]} {f}"
        else:
            saida.append(f)
    return [f for f in saida if _palavras(f) >= MIN_PALAVRAS_ITEM]


def _entre_aspas(texto: str) -> List[str]:
    """Trechos entre aspas, pareando na ordem em que aparecem.

    O PO mistura aspas retas e curvas, e uma regex que aceita qualquer uma das duas dos dois lados
    juntava o fim de uma citação com o começo da seguinte. Aqui “…” pareia com ”, e a reta abre e
    fecha alternadamente.
    """
    trechos, aberta, inicio = [], None, 0
    for i, c in enumerate(texto or ""):
        if aberta is None and c in "\"“":
            aberta, inicio = c, i + 1
        elif aberta is not None and ((aberta == "“" and c == "”") or (aberta == '"' and c == '"')):
            trechos.append(texto[inicio:i])
            aberta = None
    return trechos


def _literais(bloco: str, origem: str) -> List[Dict[str, str]]:
    return [{"origem": origem, "tipo": "literal", "texto": t.strip()} for t in _entre_aspas(bloco)
            if _palavras(t) >= MIN_PALAVRAS_LITERAL and "\n" not in t.strip()]


def itens_do_pedido(texto: str, origem: str) -> List[Dict[str, str]]:
    """Checklist de um pedido do PO (refazer, parecer com ajuste)."""
    itens: List[Dict[str, str]] = []
    trechos_em_bloco: List[tuple] = []
    m = _RE_TRAVAS.search(texto or "")
    if m:
        trechos_em_bloco.append(m.span())
        itens += _literais(m.group(1), origem)
        itens += [{"origem": origem, "tipo": "trava", "texto": f} for f in _frases(m.group(1))]
    for aj in _RE_AJUSTE.finditer(texto or ""):
        trechos_em_bloco.append(aj.span())
        corpo = re.sub(r"\s+", " ", aj.group(2)).strip()
        quero = re.search(r"O que quero:(.*)", corpo, re.I)
        foco = (quero.group(1) if quero else corpo).strip()
        titulo = " ".join(corpo.split(" ")[:10])
        itens.append({"origem": origem, "tipo": "ajuste", "texto": f"{aj.group(1)} — {titulo}…: {foco}"[:1200]})
    v = _RE_VALIDACAO.search(texto or "")
    if v:
        trechos_em_bloco.append(v.span())
        for q in v.group(1).split("?"):
            q = re.sub(r"\s+", " ", q).strip(" .")
            if _palavras(q) >= 4:
                itens.append({"origem": origem, "tipo": "validacao", "texto": q + "?"})
    if itens:
        # Formato misto (um bloco TRAVAS/AJUSTE/VALIDAÇÃO e, fora dele, uma lista ou parágrafos): o que fica fora dos
        # blocos também é pedido. Até 08/10/2026 só os blocos viravam item, e a lista solta não era conferida.
        fora = list(texto or "")
        for a, b in trechos_em_bloco:
            fora[a:b] = [" "] * (b - a)
        itens += unidades_do_pedido("".join(fora), origem)
    if not itens:
        # Pedido sem a estrutura AJUSTE/TRAVAS: unidades atômicas recortadas em código. Até 08/10/2026 virava UM item
        # com o texto inteiro — o parecer de 8 pontos da exp06ef1b não tinha um trecho do documento que provasse tudo, o
        # juiz citou o próprio pedido e a fidelidade saiu 🔴 com os 8 aplicados.
        itens += unidades_do_pedido(texto, origem)
    return itens


#: Verbo de ação ou obrigação: unidade com um deles é exigência e não pode ser dispensada como "contexto" pelo juiz.
_RE_ACAO = re.compile(
    # formas de ordem e de dever, não particípio: «a versão aprovada pelo PO» descreve, «aprovar o pacote» manda
    r"\b(?:remov(?:er|a|am|e)|retir(?:ar|e|em)|tir(?:ar|e|em)|exclu(?:ir|a|am)|descart(?:ar|e|em)|"
    r"adicion(?:ar|e|em)|acrescent(?:ar|e|em)|inclu(?:ir|a|am)|insir(?:a|am)|inserir|explicit(?:ar|e|em)|"
    r"troc(?:ar|a|ue|uem)|substitu(?:ir|a|am)|crav(?:ar|e|em)|mant(?:er|enha|enham|ém|êm)|preserv(?:ar|e|em)|"
    r"permanec(?:er|e|em|am)|n[ãa]o\s+(?:alter|mud|prescrev|mant|troc|mex)\w*|alter(?:ar|e|em)|mud(?:ar|e|em)|"
    r"corrig(?:ir|a|am)|ajust(?:ar|e|em)|escrev(?:er|a|am)|registr(?:ar|e|em)|defin(?:ir|a|am)|fix(?:ar|e|em)|"
    r"homolog(?:ar|ue|uem)|ratific(?:ar|que)|aprov(?:ar|e|em)|dev(?:e|em)|precis(?:a|am)|garant(?:ir|a|am)|"
    r"exib(?:ir|a|am)|mostr(?:ar|e|em)|declar(?:ar|e|em)|resolv(?:er|a|am))\b", re.IGNORECASE)
#: Frase que só remete aos itens do pedido ("Resolver cada ponto abaixo"): não há no documento o que a prove.
#: Ordem de NÃO fazer: «não alterar spec, telas, fluxo», «manter o roteiro», «não gerar de novo».
_RE_PRESERVACAO = re.compile(
    r"\bdev\w*\s+(?:ser\s+)?(?:mantid|preservad|permanec)\w*|"
    r"\bn[ãa]o\s+(?:dev\w*\s+)?(?:ser\s+)?(?:alter|mud|mex|ger|regener|refaz|reescrev|troc|toc)\w*(?:\s+de\s+novo)?|"
    r"\bmant(?:er|enha|enham|ém|êm)\b|\bpreserv(?:ar|e|em)\b|\bpermanec(?:er|e|em|am)\b", re.IGNORECASE)


def so_preservacao(texto: str) -> bool:
    """O item só manda não mexer: tirada a ordem de preservar, não sobra verbo de ação.

    Ausência de mudança não tem trecho que a prove — na exp06ef1b (10/10/2026) o juiz citou o próprio «Não alterar
    spec, telas, fluxo, copy nem protótipo» e o design saiu 🔴 com 14 de 15 itens provados. O que não pode mudar é
    conferido em código pelos gates de preservação (linhas perdidas, rastreabilidade, registro do Stitch).
    """
    texto = _RE_RELATIVA_DESCRITIVA.sub(" ", texto or "")
    return bool(_RE_PRESERVACAO.search(texto)) and not _RE_ACAO.search(_RE_PRESERVACAO.sub(" ", texto))


#: Oração relativa com verbo conjugado descreve, não manda: «o apressado que não mexe no banco» (exp01em1b, 23/10/2026).
#: A ordem tem infinitivo ou dever — «o que não mudar», «o que não deve mudar» — e continua sendo preservação.
_RE_RELATIVA_DESCRITIVA = re.compile(
    r"\bquem?\s+n[ãa]o\s+(?:alter|mud|mex|ger|regener|refaz|reescrev|troc|toc)(?:a|e|am|em)\b", re.IGNORECASE)

#: A ordem de não mexer que não nomeia o que preservar — só «o restante». Lista fechada, comparada com o item inteiro
#: normalizado (sem o rótulo «(item N)» e sem pontuação): não interpreta prosa, só reconhece a fórmula. É a regra de
#: toda reexecução (o que o pedido não cita fica como estava, `pipeline.reexecucao`), e não há trecho que a prove: na
#: exp01em1b (e3980485, 22/10/2026) «Manter o restante» saiu 🔴 `preservacao-sem-prova` no fim de produto e a missão
#: recomeçou em outra sessão (C2, 25/10/2026). Ordem que nomeia o objeto («não alterar a mecânica») continua cobrada.
_PRESERVACAO_GENERICA = frozenset({
    "manter o restante", "manter todo o restante", "manter o resto", "manter tudo o mais", "manter o demais",
    "manter o restante como esta", "manter o restante sem alteracao", "manter o restante igual",
    "manter todo o restante sem alteracao", "manter todo o restante como esta", "e manter o restante",
    "preservar o restante", "preservar todo o restante", "preservar o restante sem alteracao",
    "preservar todo o restante sem alteracao", "o restante permanece como esta", "o restante fica como esta",
    "o resto permanece como esta", "o resto fica como esta", "nao alterar mais nada", "nao alterar nada mais",
    "nao alterar o restante", "nao mudar mais nada", "nao mudar nada mais", "nao mudar o restante",
    "nao mexer no restante", "nao mexer em mais nada", "nao mexer no resto", "nenhuma outra alteracao",
    "nenhuma outra mudanca", "sem outras alteracoes", "sem outras mudancas",
})
#: O rótulo de lista que o recorte põe no item («(item 5) …»): não é parte da frase do PO.
_RE_ROTULO_DO_ITEM = re.compile(r"^\s*\(item\s+\d{1,2}\)\s*", re.IGNORECASE)


def preservacao_generica(texto: str) -> bool:
    """O item inteiro é uma das fórmulas de `_PRESERVACAO_GENERICA` («Manter o restante.»)."""
    alvo = re.sub(r"[^\w\s]", " ", _norm(_RE_ROTULO_DO_ITEM.sub("", texto or "")))
    return re.sub(r"\s+", " ", alvo).strip() in _PRESERVACAO_GENERICA


#: O que só cita ou rotula, e por isso não manda: o texto entre aspas («clicar “fixar aviso”» nomeia um botão) e os
#: rótulos do pedido organizado por tela («Texto atual:», «Ajuste solicitado:»). Delimitador e rótulo fixo — não
#: interpreta a frase.
_RE_SO_CITA = re.compile(r"“[^”]*”|\"[^\"\n]*\"|«[^»]*»|\b(?:texto\s+atual|ajustes?\s+(?:solicitad|necess[áa]ri|pedid)\w*)"
                         r"\s*:", re.IGNORECASE)


def exige_acao(texto: str) -> bool:
    """Há verbo de ação ou de dever no que o PO escreve com a voz dele — fora das aspas, dos rótulos e da oração
    relativa que descreve.

    É a régua do `contexto` do juiz: com verbo, a frase é exigência e o `contexto` vira `exigencia-dispensada`. Até
    25/10/2026 o verbo valia em qualquer lugar da frase, e duas frases do PO que não pedem nada saíram 🔴 na fidelidade
    de design: «Sobre o rusher: com 5 opções no menu, a chance de clicar “fixar aviso” por acaso é 20%. É alta.»
    (exp02em1b, 60cfa7f4 — o verbo é o nome do botão) e «> “O que não pode faltar na foto…” Botão: “Publicar no Álbum”
    Ajuste solicitado: …» (exp02ef1b, 4fd72a9a — o texto atual citado, e «Ajuste» é o rótulo)."""
    sem = _RE_RELATIVA_DESCRITIVA.sub(" ", _RE_SO_CITA.sub(" ", texto or ""))
    return bool(_RE_ACAO.search(sem))


_RE_REMETE_A_LISTA = re.compile(r"\b(?:cada\s+(?:ponto|item)|(?:pontos|itens)\s+(?:abaixo|a\s+seguir|seguintes)|"
                                r"abaixo\s*[:.]?\s*$)", re.IGNORECASE)
_RE_ITEM_DE_LISTA = re.compile(r"^\s*(?:(\d{1,2})[.)]|[-*•])\s+")


def _frases_sem_cortar_aspas(texto: str) -> List[str]:
    """Frases do texto, sem quebrar dentro de aspas: «Substituir por: “A. B.”» é uma frase só."""
    frases, atual, dentro = [], [], False
    for i, c in enumerate(texto):
        atual.append(c)
        fecha_frase_citada = False
        if c in "“«":
            dentro = True
        elif c in "”»":
            dentro = False
            fecha_frase_citada = i > 0 and texto[i - 1] in ".!?"
        elif c == '"':
            dentro = not dentro
            fecha_frase_citada = not dentro and i > 0 and texto[i - 1] in ".!?"
        # fim de frase fora de aspas, ou aspas que fecham uma frase citada («…configuração.” Remover as tags…»)
        if (not dentro and (c in ".!?;" or fecha_frase_citada)
                and (i + 1 == len(texto) or texto[i + 1].isspace())):
            frases.append("".join(atual).strip())
            atual = []
    if "".join(atual).strip():
        frases.append("".join(atual).strip())
    return [f for f in frases if f]


def unidades_do_pedido(texto: str, origem: str) -> List[Dict[str, str]]:
    """O pedido recortado em unidades atômicas e literais: cada item de lista e cada frase vira um item.

    Recorte em código, não pelo modelo: nada é agrupado (duas exigências nunca viram um item) e nada é inventado (o
    texto do item está no pedido, letra por letra). Fragmento curto («Ponto final.») cola na unidade anterior. O item
    de lista leva o rótulo dele («item 2») para o juiz saber de onde a frase veio; a frase que proíbe mudar vira trava.
    """
    # Parágrafos primeiro: linha que continua a anterior (texto com quebra manual) é a mesma frase — cortada por linha,
    # «(Canal B,\nroteiro do debate…)» virava dois itens sem sentido. Item de lista e linha em branco abrem parágrafo.
    paragrafos: List[tuple] = []
    rotulo, em_branco, atual = "", False, []
    for bruta in (texto or "").splitlines() + [""]:
        linha = bruta.strip()
        m = _RE_ITEM_DE_LISTA.match(linha) if linha else None
        if not linha or m:
            if atual:
                paragrafos.append((rotulo, " ".join(atual)))
                atual = []
            if not linha:
                em_branco = True
                continue
            rotulo = f"item {m.group(1)}" if m.group(1) else rotulo
            linha = linha[m.end():]
        elif em_branco and not atual:
            rotulo = ""  # parágrafo novo fora da lista: o rótulo do último item não vale para ele
        em_branco = False
        atual.append(linha)
    unidades: List[Dict[str, str]] = []
    for rotulo, paragrafo in paragrafos:
        for frase in _frases_sem_cortar_aspas(paragrafo):
            # trava curta ("Não alterar mais nada.") é item próprio — colada noutro, passava junto com ele
            if _RE_TRAVA_PROSA.search(frase):
                unidades.append({"origem": origem, "tipo": "trava",
                                 "texto": (f"({rotulo}) {frase}" if rotulo else frase)[:900]})
                continue
            if unidades and _palavras(frase) < MIN_PALAVRAS_ITEM:
                unidades[-1]["texto"] = f"{unidades[-1]['texto']} {frase}"[:900]
                continue
            if _palavras(frase) < MIN_PALAVRAS_ITEM:
                continue
            tipo = "trava" if _RE_TRAVA_PROSA.search(frase) else "pedido"
            unidades.append({"origem": origem, "tipo": tipo,
                             "texto": (f"({rotulo}) {frase}" if rotulo else frase)[:900]})
    return unidades


#: Briefing com títulos em MAIÚSCULAS e sem dois-pontos ("OPERAÇÃO COGNITIVA", "MECÂNICA — IMAGEM
#: PRÉ-DECOMPOSTA", "CONSTRAINT DE INTERFACE — OBRIGATÓRIO"). O parser só via títulos com dois-pontos:
#: o briefing da exp03ef1b (07/10/2026) deu zero itens, e a fidelidade aprovou a geração que trocou a
#: seção do DS que o briefing proibia trocar. Radicais sem acento, comparados com `_norm`.
_TITULOS_EM_MAIUSCULAS = (
    ("restricao", ("constraint", "restricao", "obrigatorio", "proibido", "trava")),
    ("habilidades", ("habilidades",)),
    ("direcionamento pedagógico", ("operacao cognitiva", "contrato de evidencia", "direcionamento")),
    ("elementos fixos", ("mecanica", "narrativa", "elementos fixos")),
    ("passo a passo", ("passo a passo", "jornada")),
)
#: Seções cujas linhas são curtas demais para virar item uma a uma ("EF03CO01 — Lógica computacional",
#: "secao_ds: unoogaleria") e valem como bloco: o tipo do item que o bloco inteiro vira.
_BLOCO_INTEIRO = {"restricao": "trava", "habilidades": "briefing"}
#: Linha solta que fixa a interface ("Interface forçada: Galeria de Fotos", "secao_ds: unoogaleria").
_RE_LINHA_DE_INTERFACE = re.compile(r"^(?:interface|`?secao_ds`?|se[çc][ãa]o do ds)\b[^:\n]{0,40}[:=]\s*\S", re.IGNORECASE)
_RE_SUBTITULO = re.compile(r"\s[—–-]\s")


def _titulo_em_maiusculas(linha: str) -> Optional[str]:
    """A seção de um título em maiúsculas (decide o que vem antes do travessão); "" se não reconhecida."""
    cabeca = _RE_SUBTITULO.split(linha, maxsplit=1)[0]
    letras = [c for c in cabeca if c.isalpha()]
    # uma palavra de verdade, não só código: "EF03CO03" sozinho na linha não é título
    palavra = any(len(w) >= 4 and w.isalpha() for w in re.findall(r"\w+", cabeca))
    if not palavra or not all(c.isupper() for c in letras) or _palavras(linha) > 12:
        return None
    baixa = _norm(linha)
    return next((secao for secao, radicais in _TITULOS_EM_MAIUSCULAS if any(r in baixa for r in radicais)), "")


def itens_do_briefing(briefing: str) -> List[Dict[str, str]]:
    """Direcionamento, passos da experiência e elementos fixos — um item por parágrafo.

    Restrição explícita (bloco de título CONSTRAINT/RESTRIÇÃO/OBRIGATÓRIO, ou a linha que fixa a
    interface) vira um item só, do tipo `trava`: linhas curtas como `secao_ds: unoogaleria` não
    chegam a `MIN_PALAVRAS_ITEM` e sumiam, e é justamente a regra que não pode sumir. No briefing de
    títulos em maiúsculas, o item leva o título ("CONTRATO DE EVIDÊNCIA PEDAGÓGICA — Gesto registrável
    que demonstre: 3. Recombinou as partes…"): sem ele, "3. Recombinou…" não diz de onde veio.
    """
    itens: List[Dict[str, str]] = []
    secao: Optional[str] = None
    titulo = ""  # só o do título em maiúsculas, com o subtítulo de dois-pontos que vier abaixo dele
    bloco: List[str] = []

    def fechar_bloco() -> None:
        if bloco:
            itens.append({"origem": "briefing", "tipo": _BLOCO_INTEIRO[secao], "texto": f"{titulo}: {' '.join(bloco)}"[:900]})
            bloco.clear()

    for linha in (briefing or "").splitlines():
        limpa = linha.strip()
        if not limpa:
            continue
        maiusculas = _titulo_em_maiusculas(limpa)
        if maiusculas is not None:
            fechar_bloco()
            secao, titulo = maiusculas or None, limpa
            continue
        if limpa.endswith(":") and _palavras(limpa) <= 12:
            if titulo and secao and secao not in _BLOCO_INTEIRO:
                # "Gesto registrável que demonstre:" abaixo de CONTRATO DE EVIDÊNCIA é subtítulo dele
                titulo = f"{titulo.split(' — ')[0]} — {limpa.rstrip(':')}"
                continue
            fechar_bloco()
            baixa = limpa.lower()
            nova = next((s for s in _SECOES_BRIEFING if s in baixa), None)
            # "Os três projetos:" é subtítulo dos elementos fixos, não fim deles
            secao, titulo = nova or (secao if secao == "elementos fixos" else None), ""
            continue
        if secao in _BLOCO_INTEIRO:
            bloco.append(limpa)
        elif _RE_LINHA_DE_INTERFACE.match(limpa):
            itens.append({"origem": "briefing", "tipo": "trava", "texto": limpa[:900]})
        elif secao and _palavras(limpa) >= MIN_PALAVRAS_ITEM:
            texto = f"{titulo}: {limpa}" if titulo else limpa
            itens.append({"origem": "briefing", "tipo": "briefing", "texto": texto[:900]})
    fechar_bloco()
    if not itens:
        itens += _itens_da_prosa(briefing)
    # A frase que o briefing pôs entre aspas é texto do PO ("Pergunta-motor: “Se a mesma coisa
    # aconteceu…”"): as três gerações da exp03ef1b a perderam. Confere-se letra a letra, como as TRAVAS.
    itens += _literais(briefing or "", "briefing")
    return itens


#: Frase de briefing que proíbe mudar algo: vira trava, como o bloco CONSTRAINT dos briefings com título.
_RE_TRAVA_PROSA = re.compile(r"n[ãa]o\s+(?:alter|mud|troc|mex|reescrev|refa[zç])|sem\s+alterar|manter\b|mantenha|"
                             r"preserv|proibid|n[ãa]o\s+pode", re.IGNORECASE)


def _itens_da_prosa(briefing: str) -> List[Dict[str, str]]:
    """Briefing sem título nenhum: uma frase por item, como o pedido (`unidades_do_pedido`) — nada agrupado.

    O parser só via seção com título (em maiúsculas ou com dois-pontos). O reprocessamento da exp06ef1b
    (08/10/2026) veio em prosa — "A narrativa, o mecanismo das 6 etapas e a estrutura da missão estão
    aprovados — não alterar nenhum deles" — e o checklist saiu com um item só, o texto oficial de uma
    habilidade entre aspas: o juiz nem rodou e a fidelidade aprovou a missão reescrita. Depois, o parágrafo
    inteiro virava um item, e três exigências do PO dividiam uma prova só.
    """
    return [{**u, "tipo": "briefing" if u["tipo"] == "pedido" else u["tipo"]}
            for u in unidades_do_pedido(briefing, "briefing")]


#: Ordem de prioridade e teto por tipo. Os pedidos repetem as travas com outras palavras (os dois
#: refazer da exp09ef1b trouxeram 42), e elas empurravam o briefing para fora do checklist.
PRIORIDADE: Tuple[Tuple[str, int], ...] = (
    # «pedido» era 6: um parecer de 8 pontos perdia dois sem aviso (exp06ef1b, 08/10/2026)
    ("ajuste", 12), ("pedido", 30), ("literal", 8), ("validacao", 12), ("trava", 18), ("briefing", 16))


#: Relato de gate colado num pedido: «❌ remocao-nao-aplicada · O pedido manda tirar «X»…». Ele aponta para um item de
#: pedido anterior, que segue em vigor; lido como ordem, a esteira obedecia à mensagem do gate. Na exp02ef1b
#: (23/10/2026) o PO colou os achados e o editor pontual trocou «Colocar no álbum» de volta para «Publicar no Álbum».
_RE_RELATO_DE_GATE = re.compile(
    r"^\s*(?:[❌⚠️🟡🔴⛔✅]️?\s*)?`?[a-z]+(?:-[a-z]+)+`?\s*·|"
    r"O pedido manda tirar «|O juiz (?:diz que atende|tratou como contexto)|Ordem de não mexer sobre|"
    r"Pedido do PO sem prova|citou o próprio pedido|Devolva cada uma, no mesmo lugar", re.IGNORECASE)


def sem_relatos_de_gate(texto: str) -> str:
    """O pedido sem as linhas que são relato de gate colado — o item que o relato cita já está no pedido de origem.
    O que o PO escreveu depois de uma seta («❌ sem-codigo · … -> as habilidades foram trabalhadas…») é dele, e fica."""
    saida = []
    for linha in (texto or "").splitlines():
        if not _RE_RELATO_DE_GATE.search(linha):
            saida.append(linha)
            continue
        resposta = re.search(r"\s(?:->|→|=>)\s*(\S.*)$", linha)
        if resposta:
            saida.append(resposta.group(1))
    return "\n".join(saida)


#: O texto que a esteira escreve em volta do pedido de refazer (`pipeline.reexecucao.PedidoCorrecao.como_markdown`): o
#: cabeçalho «Esta execução refaz a etapa…», o título «Pedido, na íntegra» com o «>» de cada linha do PO, a divisão da
#: triagem, os textos-chave citados, o material anexado e as três regras de «Como agir».
_RE_PREAMBULO_DA_ESTEIRA = re.compile(r"Esta execução refaz a etapa `[^`\n]*`.*?(?:não de uma folha em branco\.|\n\s*\n|\Z)",
                                      re.S)
#: O título e as linhas citadas logo abaixo dele, que são o pedido do PO: a primeira linha sem «>» já não é do bloco.
_RE_PEDIDO_NA_INTEGRA = re.compile(
    r"^#{2,4}[ \t]*Pedido, na íntegra[ \t]*\n((?:[ \t]*(?:>[^\n]*)?\n)*(?:[ \t]*>[^\n]*)?)", re.M)
_RE_TITULO = re.compile(r"^#{1,3}[ \t]+\S", re.M)
_RE_MATERIAL_ANEXADO = re.compile(r"^#{2,4}[ \t]*Material anexado ao pedido[ \t]*$", re.M)
_RE_TITULO_COMO_AGIR = re.compile(r"^#{2,4}[ \t]*Como agir[ \t]*$", re.M)


def _plana(linha: str) -> str:
    """A linha sem negrito e com espaço único: a regra copiada da tela perde os `**`."""
    return re.sub(r"[*\s]+", " ", linha or "").strip()


@functools.lru_cache(maxsize=1)
def _blocos_da_esteira() -> Tuple["re.Pattern[str]", frozenset]:
    """`(blocos com título que são da esteira, regras de «Como agir» planas)`, lidos do próprio `como_markdown`: se a
    esteira mudar o texto, a limpeza acompanha."""
    from pipeline.reexecucao import PedidoCorrecao
    from tools.textos_chave import TITULO_CITADOS

    titulos = "|".join(re.escape(t) for t in ("Divisão do pedido pela triagem", TITULO_CITADOS))
    blocos = re.compile(rf"^#{{2,4}}[ \t]*(?:{titulos})[ \t]*\n.*?(?=^#{{1,3}}[ \t]+\S|\Z)", re.S | re.M)
    modelo = PedidoCorrecao(texto="-").como_markdown("produto")
    regras = frozenset(_plana(l) for l in _RE_TITULO_COMO_AGIR.split(modelo, 1)[-1].splitlines() if l.strip())
    return blocos, regras


def sem_texto_da_esteira(texto: str) -> str:
    """O pedido sem o texto que a esteira escreve em volta dele no refazer.

    Na exp06ef1b (727a3c2d, 08/10/2026 11:08) o cabeçalho «Esta execução refaz a etapa `produto`… a pedido de uma
    pessoa» entrou no checklist como item do PO e saiu 🔴 duas vezes, no núcleo (`sem-prova`) e no fim de produto
    (`pedido-violado`). A fidelidade passou a ler só o «Pedido, na íntegra» do pedido corrente (`texto_do_pedido`, 84354c2,
    08/10 12:27); aqui o mesmo vale para qualquer pedido — inclusive o markdown do refazer que o PO cola num pedido novo.

    Saem só os blocos fixos da esteira; o que o PO escreve antes ou depois deles fica. Até a revisão do PR #80
    (24/10/2026) o corte ia do «Pedido, na íntegra» e do «Como agir» até o fim, e os itens novos que o PO escrevia depois
    do markdown colado sumiam do checklist."""
    blocos, regras = _blocos_da_esteira()
    t = _RE_PREAMBULO_DA_ESTEIRA.sub("", texto or "")
    t = _RE_PEDIDO_NA_INTEGRA.sub(
        lambda m: "\n".join(re.sub(r"^\s*>\s?", "", l) for l in m.group(1).splitlines()) + "\n", t)
    t = blocos.sub("", t)
    m = _RE_MATERIAL_ANEXADO.search(t)
    while m:
        # o anexo pode ter títulos próprios: o bloco vai até o «Como agir» que o segue e, sem ele, até o próximo título
        fim = _RE_TITULO_COMO_AGIR.search(t, m.end()) or _RE_TITULO.search(t, m.end())
        t = t[:m.start()] + (t[fim.start():] if fim else "")
        m = _RE_MATERIAL_ANEXADO.search(t, m.start())
    linhas = [l for l in t.splitlines() if not _RE_TITULO_COMO_AGIR.match(l) and _plana(l) not in regras]
    return "\n".join(linhas).strip()


def montar_checklist(pedidos: List[Tuple[str, str]], briefing: str) -> List[Dict[str, str]]:
    """`pedidos` = [(origem, texto)], do mais antigo ao mais novo. Ids F1…Fn, sem repetição.

    Por tipo, na ordem de `PRIORIDADE`; dentro do tipo, do pedido mais novo para o mais antigo —
    quando dois pedidos repetem uma trava, vale a redação mais recente.
    """
    brutos: List[Dict[str, str]] = []
    for origem, texto in reversed(pedidos):
        brutos += itens_do_pedido(sem_relatos_de_gate(sem_texto_da_esteira(texto)), origem)
    brutos += itens_do_briefing(briefing)
    vistos, unicos = set(), []
    for tipo, teto in PRIORIDADE:
        n = 0
        for it in brutos:
            if it["tipo"] != tipo or n >= teto:
                continue
            chave = (tipo, _norm(it["texto"])[:160])
            if chave in vistos:
                continue
            vistos.add(chave)
            unicos.append(it)
            n += 1
    unicos = unicos[:MAX_ITENS]
    for i, it in enumerate(unicos, 1):
        it["id"] = f"F{i}"
    return unicos


def para_o_juiz(itens: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """O que o juiz julga: tudo menos as frases literais, que o código confere sozinho."""
    return [{"id": i["id"], "origem": i["origem"], "tipo": i["tipo"], "texto": i["texto"]}
            for i in itens if i["tipo"] != "literal"]


def para_o_interprete(itens: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """O que o intérprete lê: só os itens do PO — o briefing não manda trocar texto."""
    return [{"id": i["id"], "origem": i["origem"], "texto": i["texto"]}
            for i in itens if i["tipo"] != "literal" and i["origem"] != "briefing"]


def interpretacao(saida: str, itens: List[Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
    """`{id: {inserir, remover, outras_exigencias, cabecalho}}` lido da resposta do intérprete, conferido em código.

    O PO dita texto de mil jeitos («usar: X», «passa a ser X», «Atingiu: X»), e a regra do texto ditado só via aspas:
    na exp03em1b (21/10/2026) o texto novo estava no documento letra por letra e a fidelidade saiu 🔴 por
    `citou-o-pedido`. O intérprete (LLM determinístico, sem ver os documentos) diz o que é texto a pôr e o que é texto
    a tirar; o código só aceita trecho que está, letra por letra, no item. O resto é descartado e o item segue como era.
    """
    textos = {i["id"]: _norm(i["texto"]) for i in para_o_interprete(itens)}
    dados: Dict[str, Any] = {}
    for bruto in reversed(re.findall(r"```json\s*(.*?)```", saida or "", re.S)):
        try:
            dados = json.loads(bruto)
        except json.JSONDecodeError:
            continue
        if isinstance(dados, dict) and isinstance(dados.get("itens"), list):
            break
        dados = {}
    lidos: Dict[str, Dict[str, Any]] = {}
    for d in dados.get("itens") or []:
        if not isinstance(d, dict) or str(d.get("id")) not in textos:
            continue
        alvo = textos[str(d.get("id"))]

        def do_item(chave: str, minimo: int) -> List[str]:
            return [str(t) for t in (d.get(chave) or []) if isinstance(t, str)
                    and len(_norm(t)) >= minimo and _norm(t) in alvo]

        inserir = do_item("inserir", MIN_CITACAO)
        # o lado velho de uma troca é curto («eixo zero»), mas uma palavra solta casaria em qualquer lugar
        remover = [t for t in do_item("remover", 8) if _palavras(t) >= 2
                   and not any(_norm(t) in _norm(s) or _norm(s) in _norm(t) for s in inserir)]
        lidos[str(d.get("id"))] = {
            "inserir": inserir, "remover": remover,
            # na dúvida o item pede mais do que os trechos: a prova em código não basta
            "outras_exigencias": d.get("outras_exigencias") is not False,
            "cabecalho": d.get("cabecalho") is True and not inserir and not remover,
        }
    return lidos


#: Objetos de uma ordem de não mexer que têm gate de preservação próprio em código (linhas perdidas, conteúdo
#: aprovado, rastreabilidade, registro do Stitch, consistência do Canal B e dos estados). Sem citação, a ordem sobre
#: um destes fica 🟡 — o gate dele confere; sobre qualquer outra coisa (mecânica, regra, narrativa), 🔴.
_RE_OBJETO_COM_GATE = re.compile(
    r"\b(?:spec|texto literal|textos literais|copy|telas?|wireframes?|stitch|podcast|canal b|estados?|fsm)\b")
#: Documento inteiro nomeado numa ordem de não mexer → chaves do estado que o guardam. A ordem sobre o documento
#: inteiro se prova em código contra `anterior_<chave>` (`pipeline/reexecucao.py`), sem juiz.
_DOCUMENTO_INTEIRO = (
    (re.compile(r"\bspec\b"), ("spec_missao",)),
    (re.compile(r"\bone[- ]pager\b(?! (?:pedag|resum))"), ("one_pager",)),
    (re.compile(r"\bprd\b"), ("prd_final",)),
    (re.compile(r"\bprototipo\b"), ("prototipo_html",)),
    (re.compile(r"\bcopy\b"), ("copy_strings_revisada", "copy_strings")),
    (re.compile(r"\btelas\b|\bjornada\b"), ("jornada_telas",)),
    (re.compile(r"\bfluxo\b"), ("fluxo_arestas",)),
    (re.compile(r"\bwireframes?\b"), ("wireframes_cobertura",)),
)


def _decisoes(saida_juiz: str) -> Dict[str, Dict[str, Any]]:
    for bruto in reversed(re.findall(r"```json\s*(.*?)```", saida_juiz or "", re.S)):
        try:
            dados = json.loads(bruto)
        except json.JSONDecodeError:
            continue
        if isinstance(dados, dict) and isinstance(dados.get("decisoes"), list):
            return {str(d.get("id")): d for d in dados["decisoes"] if isinstance(d, dict)}
    return {}


def _sem_anexo(texto: str) -> str:
    """Sem o que a esteira escreve por código depois do autor: o anexo literal e, no handoff e no PRD, as pendências de
    governança da liberação de produto (PR 9) — a correção pontual que as atualiza não muda o que o autor escreveu."""
    from tools.conteudo_aprovado import remover_anexo
    from tools.governanca import sem_bloco

    return sem_bloco(remover_anexo(texto or ""))


def _documentos_nomeados(texto: str, documentos: Dict[str, str], anteriores: Dict[str, str]) -> List[str]:
    """As chaves dos documentos inteiros que a ordem nomeia e que existem agora e na versão anterior."""
    alvo = _norm(texto)
    chaves: List[str] = []
    for padrao, candidatas in _DOCUMENTO_INTEIRO:
        if padrao.search(alvo):
            chave = next((c for c in candidatas if c in documentos and (anteriores.get(c) or "").strip()), None)
            if chave:
                chaves.append(chave)
    return chaves


def _diferenca(anterior: str, atual: str) -> Tuple[List[str], List[str]]:
    """`(saíram, entraram)`: linhas não vazias da versão anterior ausentes da atual, e o contrário."""
    antes = [l.strip() for l in _sem_anexo(anterior).splitlines() if l.strip()]
    agora = [l.strip() for l in _sem_anexo(atual).splitlines() if l.strip()]
    ja, ag = set(agora), set(antes)
    return [l for l in antes if l not in ja], [l for l in agora if l not in ag]


#: Fração da citação que precisa aparecer contínua no documento. O juiz copia com pequenas diferenças
#: (vírgula, aspas, uma palavra a mais); paráfrase e texto do próprio pedido não chegam perto disto.
FRACAO_CITACAO = 0.85


def _trecho_confere(trecho: str, documentos_norm: str) -> bool:
    alvo = _norm(trecho)
    if alvo in documentos_norm:
        return True
    import difflib
    m = difflib.SequenceMatcher(None, documentos_norm, alvo, autojunk=False).find_longest_match(
        0, len(documentos_norm), 0, len(alvo))
    return m.size >= FRACAO_CITACAO * len(alvo)


def _citacao_confere(citacao: str, documentos_norm: str) -> bool:
    """A citação existe no documento. Com reticências no meio ("Mesa Aberta: … Ponto de Apoio: …"),
    cada parte precisa existir — o juiz corta assim mesmo quando o prompt diz para não cortar."""
    partes = [p for p in re.split(r"\.\.\.|…", citacao or "") if len(_norm(p)) >= MIN_CITACAO]
    if not partes:
        return False
    return all(_trecho_confere(p, documentos_norm) for p in partes)


def _literal_presente(frase: str, documentos_norm: str) -> bool:
    alvo = _norm(re.sub(r"(\.\.\.|…)\s*$", "", frase))
    return bool(alvo) and alvo in documentos_norm


def _ditado_no_corpo(citacoes: Sequence[str], texto_item: str, corpo: str, corpo_anterior: str) -> bool:
    """As citações do juiz são o texto do próprio PO, e ele entrou no corpo do documento.

    Cada citação tem de estar, letra por letra, no item (com `MIN_PALAVRAS_LITERAL` palavras ou mais) e no corpo — e,
    havendo versão anterior, não estar nela: o texto que já estava no documento antes do pedido (o «texto atual» que o PO
    cita para trocar) não prova nada. E o texto entre aspas do item que continua no documento como estava
    (`_citado_ficou`) deixa a prova com o juiz: pode ser o texto que o PO mandou tirar. Comparação literal, sem ler o
    verbo — por isso só prova sozinha na ordem de não mexer, em que o único verbo é o de preservar; no item com outro
    verbo, sem a leitura do intérprete, é 🟡 (`texto-ditado-a-conferir`): «não mostrar X» e «usar: X» ficam iguais.

    Na exp03em1b (b2e7b4a3, 21/10/2026) o PO escreveu «Remover “associando a desmontagem geométrica” e usar: marcou
    corretamente no checklist os elementos de truncamento de eixo e recorte de escala como vetores de distorção.»; o texto
    novo estava no one-pager e na spec, e o F12 saiu 🔴 `citou-o-pedido` — a citação do juiz era o texto ditado. Com o
    intérprete (c8a36d2), o texto vai para `inserir` e prova; sem ele, o F12 fica 🟡 (C2, 25/10/2026)."""
    citacoes = [c for c in citacoes if (c or "").strip()]
    if not citacoes:
        return False
    item = _norm(texto_item)
    for c in citacoes:
        alvo = _norm(c)
        if (_palavras(c) < MIN_PALAVRAS_LITERAL or alvo not in item or alvo not in corpo
                or (corpo_anterior and alvo in corpo_anterior)):
            return False
    return not _citado_ficou(texto_item, [_norm(c) for c in citacoes], corpo, corpo_anterior)


def _citado_ficou(texto_item: str, citacoes_norm: Sequence[str], corpo: str, corpo_anterior: str) -> bool:
    """Um texto entre aspas do item, que não é a citação, continua no corpo como estava: com a versão anterior, o mesmo
    número de vezes; sem ela, presente. Delimitador e contagem, sem ler o verbo ao lado das aspas."""
    for q in _entre_aspas(texto_item) + re.findall(r"«([^»]*)»", texto_item or ""):
        alvo = _norm(q)
        if _palavras(q) < 2 or not alvo or any(alvo in c or c in alvo for c in citacoes_norm):
            continue
        if corpo_anterior and alvo in corpo_anterior and corpo.count(alvo) >= corpo_anterior.count(alvo):
            return True
        if not corpo_anterior and alvo in corpo:
            return True
    return False


#: Data e hora na origem de um pedido («refazer Produto · produto · 22/10/2026 17:59:11»), gravada pela esteira.
_RE_QUANDO = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})(?:\s+(\d{2}):(\d{2})(?::(\d{2}))?)?")
_ORIGEM_CORRENTE = "pedido de correção desta execução"


def _quando(origem: str) -> Optional[Tuple[int, ...]]:
    """A ordem de uma origem no tempo: o briefing antes de todo pedido, o pedido desta execução depois de todos."""
    if origem == "briefing":
        return (0,)
    if (origem or "").startswith(_ORIGEM_CORRENTE):
        return (9999,)
    m = _RE_QUANDO.search(origem or "")
    if not m:
        return None
    d, mes, a, h, mi, s = m.groups()
    return (int(a), int(mes), int(d), int(h or 0), int(mi or 0), int(s or 0))


def superado_por(item: Dict[str, str], decisao: Dict[str, Any], itens: List[Dict[str, str]],
                 provados: set) -> Optional[Tuple[str, List[str]]]:
    """`(origem, [ids])` do pedido mais novo do PO que prevaleceu sobre o item, ou `None`.

    O juiz rotula `conflito_com_regra` o item que um pedido mais novo do PO contrariou, e diz em `superado_por` (lista
    de ids do checklist) quais itens do pedido novo o documento segue. Só esse campo vale: a `explicacao` é prosa, e
    o id que ela cita de passagem («o pedido F1 não trata disso») não diz que o documento segue F1. Cada id apontado
    tem de ser de um pedido mais novo que o item e ter prova — senão o conflito segue para o PO. Entre dois pedidos vale
    o mais novo (`pipeline.passagem.notas_de_passagem`), e o briefing é mais velho que todos.

    Na exp01em1b (e3980485, 22/10/2026) o PO inverteu a ordem construção → descoberta, o documento seguiu o pedido, e
    quatro itens do briefing v4.1 saíram 🔵 `conflito-pedido-regra` no núcleo e no fim de produto, com o juiz explicando
    que o documento «segue o pedido de refazer mais recente do próprio PO (22/10/2026 17:59:11, F1-F5)». O PO já tinha
    decidido (C2, 25/10/2026). Até a revisão da C2 o código lia os ids e a data na prosa da explicação; a regra 7 do
    núcleo com «o pedido F1 não trata disso» virava superado e perdia o 🔵. A resposta gravada antes do campo continua
    🔵 — quem confirma é o PO."""
    meu = _quando(item.get("origem") or "")
    bruto = (decisao or {}).get("superado_por")
    # só a lista que o prompt pede: «F1 e F2» numa string já é prosa
    if meu is None or not isinstance(bruto, list):
        return None
    apontados = list(dict.fromkeys(str(i).strip() for i in bruto if str(i).strip()))
    novos = {i["id"]: i["origem"] for i in itens
             if i["id"] != item["id"] and i["origem"] != "briefing" and (_quando(i["origem"]) or (-1,)) > meu}
    if not apontados or not all(i in novos and i in provados for i in apontados):
        return None
    return novos[apontados[0]], apontados


#: O campo que fixa a seção do DS num item do briefing («secao_ds: unoogaleria») — dado estruturado, lido como o
#: `rastro.secao_travada` lê o briefing.
_RE_SECAO_NO_ITEM = re.compile(r"`?\bsecao_ds`?\s*[:=]\s*`?([a-z][\w:-]*)", re.IGNORECASE)


def _secao_declarada(chave: str, texto: str) -> str:
    """A seção principal que o documento declara: o `secao_ds` da ficha na spec e no anexo; a «Seção do DS» do
    cabeçalho nos outros (como o lint de contrato a lê, `tools.contrato_produto`). `""` se não declara."""
    from tools import rastro
    from tools.contrato_produto import _RE_SECAO_DO_CABECALHO

    texto = _sem_anexo(texto)
    if chave in ("spec_missao", "anexo_design_spec"):
        return re.sub(r"\s*:\s*", ":", (rastro._campo(texto, "secao_ds") or "").strip().strip("`").lower())
    m = _RE_SECAO_DO_CABECALHO.search(texto[:4000])
    return m.group(1).lower() if m else ""


def secao_travada_conferida(texto_item: str, documentos: Dict[str, str],
                            itens: Sequence[Dict[str, str]] = ()) -> Optional[Tuple[str, str, str]]:
    """`(severidade, codigo, texto)` da trava de seção do DS do item, conferida em código — `None` se o item não fixa
    seção ou nenhum documento declara uma. `severidade` é `"provado"` quando todos os documentos declaram a seção fixada.

    A exp03ef1b (274a2e75, 07/10/2026) tinha no briefing «secao_ds: unoogaleria · É PROIBIDO usar qualquer outro design
    system ou seção», o one-pager e a spec saíram em `unoochat`, e a fidelidade aprovou com 0 itens: o parser não lia o
    bloco, e a conferência, quando o lia, era do juiz. A seção é dado estruturado: a mesma régua do lint de contrato e do
    manifesto (`tools.rastro.achado_secao_travada`), documento a documento, e as extras quando o item proíbe outras
    seções (C2, 25/10/2026). A seção que um pedido do PO nomeia (`itens` de outra origem) fica em atenção: entre o
    briefing e o pedido, vale o mais novo, e quem confirma é o PO."""
    from tools import rastro
    from tools import secoes as sec

    m = _RE_SECAO_NO_ITEM.search(texto_item or "")
    briefing = f"secao_ds: {m.group(1)}" if m else (texto_item or "")
    trava = rastro.secao_travada(briefing)
    if not trava:
        return None
    declaradas = {c: s for c, d in documentos.items() if (s := _secao_declarada(c, d))}
    if not declaradas:
        return None
    problemas, severidades = [], []
    for chave, secao in declaradas.items():
        a = rastro.achado_secao_travada(secao, briefing, f"`{chave}`")
        if a:
            problemas.append(f"`{chave}` declara `{secao}`")
            severidades.append(a["severidade"])
    if sec._RE_PROIBE_OUTRAS.search(texto_item or ""):
        for chave, doc in documentos.items():
            a_mais = [e for e in sec.extras(_sem_anexo(doc)) if e not in (trava["secao"], sec.SECAO_DA_PLATAFORMA)]
            if a_mais:
                problemas.append(f"`{chave}` declara as extras {', '.join(f'`{e}`' for e in a_mais)}")
                severidades.append("bloqueio")
    if not problemas:
        return "provado", "", f"seção do DS declarada em {', '.join(f'`{c}`' for c in declaradas)}: `{trava['secao']}`"
    pedidas = {s for s in declaradas.values() if any(
        i.get("origem") != "briefing" and re.search(rf"\b{re.escape(s)}\b", _norm(i.get("texto") or ""))
        for i in itens)}
    severidade = "bloqueio" if "bloqueio" in severidades and not pedidas else "atencao"
    texto = (f"O briefing fixa a seção do DS (“{trava['trecho']}”), e {'; '.join(problemas)}. Seção fixada pelo briefing "
             f"é trava: a missão monta na `{trava['secao']}`, e a interação que ela não oferece é sinalizada — não troca "
             "de seção. Se a trava inviabiliza a mecânica, quem decide é o PO.")
    if pedidas:
        texto += (f" Um pedido do PO nomeia {', '.join(f'`{s}`' for s in sorted(pedidas))}: se ele mandou trocar, vale o "
                  "pedido mais novo — confirme com o PO.")
    elif not trava["explicita"]:
        texto += " (Seção lida pelo nome da interface; se o PO quis outra, o briefing diz `secao_ds: <seção>`.)"
    return severidade, "briefing-violado", texto


#: O que, no documento parcial (o núcleo), é falta de prova e não contradição: sai do escopo e fica para o fim de
#: produto, que confere núcleo, one-pager e spec juntos.
SEM_PROVA_NO_RECORTE = frozenset({"nao-tratado", "sem-prova", "citou-o-pedido", "exigencia-dispensada",
                                  "preservacao-sem-prova", "preservacao-sem-citacao", "texto-ditado-a-conferir",
                                  "superado-em-parte"})


def aplicar(itens: List[Dict[str, str]], saida_juiz: str, documentos: Dict[str, str],
            etapa: str = "produto", parcial: bool = False,
            anteriores: Optional[Dict[str, str]] = None,
            edicoes: Optional[List[Dict[str, Any]]] = None,
            origens_correntes: Optional[set] = None,
            interpretacao: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
    """`{status, achados, conferidos}` a partir dos itens, da saída do juiz e dos documentos.

    `etapa` é a de quem responde pelos documentos: o pedido de refazer do design é conferido nos documentos de
    design, e o achado é dele. `anteriores` (`{chave: texto}`, a versão de antes do refazer) prova as ordens de não
    mexer: documento inteiro por comparação em código; parte dele pela citação do juiz, idêntica nas duas versões.

    `edicoes` (correção pontual, `tools/edicao_pontual.py`): as trocas que a correção aplicou. Com elas, a ordem de não
    mexer se prova inteira em código — cada documento é a versão anterior mais as trocas dele, e nada além. Até
    19/10/2026 "preservar todo o restante sem alteração" era 🔴 sem prova possível (exp03em1b, 13/10/2026).

    `origens_correntes` (numa correção): as origens do pedido desta execução. A ordem de não mexer de outra rodada, ou
    do briefing, não trava o pedido novo — ele pode mudar exatamente aquilo, e entre dois pedidos vale o mais novo
    (`pipeline.passagem.notas_de_passagem`). O briefing "trocar APENAS o número" reprovava em 🔴 a migração de DS que
    o pedido seguinte mandou fazer (exp03em1b, 14/10/2026). Ela fica como atenção, à vista do PO.

    `interpretacao` (`interpretacao(saida_do_interprete, itens)`): o texto que cada item do PO manda pôr e tirar. Item
    sem outra exigência se prova em código — o texto ditado no corpo do documento, o texto a tirar fora dele —, com ou
    sem aspas e qualquer que seja o verbo. Texto a tirar que ficou é bloqueio. O cabeçalho que só anuncia os itens
    seguintes vale pela prova deles (exp03em1b, 21/10/2026)."""
    from tools import edicao_pontual

    anteriores = {k: v for k, v in (anteriores or {}).items() if (v or "").strip()}
    doc_anterior = _norm("\n".join(anteriores.values()))
    doc = _norm("\n".join(documentos.values()))
    # o corpo, sem changelog nem tabela de alterações: o texto que o PO ditou só prova quando está ali — no registro
    # do que mudou, o autor só repete o pedido (auditoria de insumos de 08/10/2026)
    from tools.one_pager_po import _sem_secoes_que_nao_contam

    corpo = _norm("\n".join(_sem_secoes_que_nao_contam(d) for d in documentos.values()))
    corpo_anterior = _norm("\n".join(_sem_secoes_que_nao_contam(d) for d in anteriores.values()))
    decisoes = _decisoes(saida_juiz)
    achados: List[Dict[str, str]] = []
    conferidos: List[Dict[str, str]] = []
    ordens_antigas: set = set()
    fora_do_recorte: List[Dict[str, str]] = []

    def achado(item: Dict[str, str], severidade: str, codigo: str, resumo: str) -> None:
        # `parcial`: o documento é só um pedaço do que o pedido cobre (o núcleo, seções 0/1/3/4). Falta de prova ali é
        # esperada para o item de outra seção — só a contradição explícita bloqueia; a prova completa é cobrada no fim
        # de produto. A exp06ef1b (08/10/2026) saía 🔴 no núcleo por «painel docente na Seção 9», com o fim 🟢 25/25.
        if parcial and codigo in SEM_PROVA_NO_RECORTE:
            # A falta de prova no núcleo nem é achado: o item que mora no one-pager ou na spec sai do escopo e é
            # conferido no fim de produto (A060), que lê os três documentos. Rebaixado a 🟡, ele pintava o núcleo de
            # amarelo e voltava ao autor: 41 de 41 `nao-tratado` do núcleo de outubro eram falsos positivos — o mesmo
            # item estava ✅ no fim de produto da mesma execução, e o juiz escrevia que ele «pertence ao one-pager/spec»
            # (e89e91b3, b2e7b4a3, 317df247, 53e011b6; C2, 25/10/2026). A contradição explícita continua aqui.
            fora_do_recorte.append({"id": item["id"], "texto": item["texto"][:240], "codigo": codigo})
            return
        if parcial and severidade == "bloqueio" and codigo not in ("pedido-violado", "frase-do-po-alterada"):
            severidade = "atencao"
        if item["id"] in ordens_antigas and severidade == "bloqueio":
            severidade = "atencao"
            resumo = f"[ordem de não mexer de outra rodada — o pedido desta correção prevalece] {resumo}"
        achados.append({"id": item["id"], "severidade": severidade, "codigo": codigo, "etapa": etapa,
                        "origem": item["origem"], "resumo": resumo})

    for it in itens:
        do_po = it["origem"] != "briefing"
        trecho = it["texto"][:240]
        if it["tipo"] == "literal":
            if _literal_presente(it["texto"], doc):
                conferidos.append({"id": it["id"], "texto": trecho, "prova": "frase literal presente"})
            elif do_po:
                achado(it, "bloqueio", "frase-do-po-alterada",
                       f"O PO escreveu a frase entre aspas e ela não está, letra por letra, em nenhum documento: «{trecho}».")
            else:
                achado(it, "atencao", "frase-do-briefing-ausente",
                       f"O briefing traz a frase entre aspas e ela não está, letra por letra, em nenhum documento: «{trecho}». "
                       "Se a missão a reescreveu de propósito, registre `[PROPOSTA — validar com PO: …]`.")
            continue
        if not do_po and it["tipo"] == "trava":
            secao = secao_travada_conferida(it["texto"], documentos, itens)
            if secao and secao[0] == "provado":
                conferidos.append({"id": it["id"], "texto": trecho, "prova": secao[2]})
                continue
            if secao:
                achado(it, secao[0], secao[1], secao[2])
                continue
        d = decisoes.get(it["id"])
        veredito = str((d or {}).get("veredito") or "").strip().lower()
        citacao = str((d or {}).get("citacao") or "")
        explicacao = str((d or {}).get("explicacao") or "").strip()
        # o pedido ditou o texto ("Adicionar: “…”"): a prova é esse texto no corpo do documento, idêntico ao ditado
        ditado = (veredito == "atendido" and len(_norm(citacao)) >= MIN_CITACAO and _citacao_confere(citacao, corpo)
                  and any(_norm(citacao) in _norm(q) or _norm(q) in _norm(citacao) for q in _entre_aspas(it["texto"])))
        # frase sem exigência (título, contexto) que o documento repete: nada a provar além de estar lá
        sem_exigencia = (veredito == "atendido" and not _RE_ACAO.search(it["texto"]) and _citacao_confere(citacao, doc))
        # item com vários elementos ("29 min, tetos 60/25/35, toast de 60 s"): uma citação por elemento, todas no
        # documento e nenhuma copiada do pedido — o juiz não prova o conjunto repetindo a frase do PO
        varias = [str(c) for c in ((d or {}).get("citacoes") or []) if str(c).strip()]
        todas_provam = (veredito == "atendido" and len(varias) >= 2
                        and all(_citacao_confere(c, doc) and not _norm(c) in _norm(it["texto"]) for c in varias))
        if so_preservacao(it["texto"]) and veredito != "conflito_com_regra":
            # Ordem de não mexer: a prova é a versão anterior, nunca a palavra do juiz (plano padrão ouro, 2.3)
            provados = [c for c in documentos if c in anteriores]
            if edicoes is not None and provados and all(
                    edicao_pontual.reaplicar(anteriores[c], documentos[c], c, edicoes) for c in provados):
                conferidos.append({"id": it["id"], "texto": trecho, "prova": (
                    f"correção pontual: {', '.join(provados)} = versão anterior + {len(edicoes)} troca(s) do pedido, "
                    "nada além")})
                continue
            if preservacao_generica(it["texto"]) and veredito != "violado":
                conferidos.append({"id": it["id"], "texto": trecho, "prova": (
                    "(ordem genérica de não mexer — a regra de toda reexecução: o que o pedido não cita fica como estava, "
                    "conferido pelos gates de preservação)")})
                continue
            if origens_correntes is not None and it["origem"] not in origens_correntes:
                ordens_antigas.add(it["id"])
            nomeados = _documentos_nomeados(it["texto"], documentos, anteriores)
            if nomeados:
                saidas = {c: _diferenca(anteriores[c], documentos[c]) for c in nomeados}
                if all(not sa and not en for sa, en in saidas.values()):
                    conferidos.append({"id": it["id"], "texto": trecho,
                                       "prova": f"idêntico à versão anterior: {', '.join(nomeados)}"})
                    continue
                perdidas = [(c, l) for c, (sa, _) in saidas.items() for l in sa]
                novas = sum(len(en) for _, en in saidas.values())
                if perdidas:
                    achado(it, "bloqueio", "pedido-violado" if do_po else "briefing-violado",
                           f"Ordem de não mexer: «{trecho}». {len(perdidas)} linha(s) da versão anterior saíram ou "
                           f"mudaram:\n" + "\n".join(f"    - `{c}`: «{l[:160]}»" for c, l in perdidas[:10]))
                else:
                    achado(it, "atencao", "preservacao-com-acrescimo",
                           f"Ordem de não mexer: «{trecho}». Nada da versão anterior saiu, mas {novas} linha(s) "
                           f"entraram em {', '.join(nomeados)} — confira se o pedido as autoriza.")
                continue
            citadas = [c for c in ([citacao] + varias) if len(_norm(c)) >= MIN_CITACAO]
            if citadas and doc_anterior:
                no_antes = [c for c in citadas if _citacao_confere(c, doc_anterior)]
                if no_antes and all(_citacao_confere(c, doc) for c in no_antes):
                    conferidos.append({"id": it["id"], "texto": trecho,
                                       "prova": "idêntico nas duas versões: " + " · ".join(c[:120] for c in no_antes)[:400]})
                    continue
                sumiu = [c for c in no_antes if not _citacao_confere(c, doc)]
                if sumiu:
                    achado(it, "bloqueio", "pedido-violado" if do_po else "briefing-violado",
                           f"Ordem de não mexer: «{trecho}». O trecho estava na versão anterior e não está na atual: "
                           f"«{sumiu[0][:200]}».")
                    continue
            elif citadas and veredito == "atendido" and all(_citacao_confere(c, doc) for c in citadas) \
                    and not any(_norm(c) in _norm(it["texto"]) for c in citadas):
                # primeira execução, sem versão anterior: o trecho no documento é a prova possível
                conferidos.append({"id": it["id"], "texto": trecho, "prova": citacao[:240] or varias[0][:240]})
                continue
            if veredito == "atendido" and _ditado_no_corpo(citadas, it["texto"], corpo, corpo_anterior):
                # o «não altera» era do texto que o PO ditou para a régua («Não atingiu: Não altera os parâmetros padrão
                # de escala…», exp03em1b, b2e7b4a3, 21/10/2026): o texto entrou no documento, e a ordem é essa
                conferidos.append({"id": it["id"], "texto": trecho, "prova": (
                    "texto ditado pelo PO no documento: " + " · ".join(c[:120] for c in citadas))[:400]})
                continue
            if veredito == "violado":
                achado(it, "bloqueio", "pedido-violado" if do_po else "briefing-violado",
                       f"O documento contraria {'o pedido do PO' if do_po else 'o briefing'}: «{trecho}». {explicacao}")
            elif _RE_OBJETO_COM_GATE.search(_norm(it["texto"])):
                achado(it, "atencao", "preservacao-sem-citacao",
                       f"Ordem de não mexer, sem trecho que a prove: «{trecho}». A conferência é dos gates de preservação "
                       "(linhas perdidas, rastreabilidade, Stitch) — confira o que eles dizem.")
            else:
                achado(it, "bloqueio", "preservacao-sem-prova",
                       f"Ordem de não mexer sobre o que nenhum gate preserva, sem trecho idêntico nas duas versões: "
                       f"«{trecho}». {explicacao}")
            continue
        lido = (interpretacao or {}).get(it["id"]) or {}
        inserir, remover = lido.get("inserir") or [], lido.get("remover") or []
        if remover and veredito != "conflito_com_regra":
            # O texto a tirar conta no corpo, fora do texto novo que o contém («eixo» dentro de «eixo zero»). Ele pode
            # existir em outro lugar da missão por direito («nota metodológica» sai do critério e fica na mecânica):
            # com a versão anterior, só fica se nenhuma ocorrência saiu; sem ela, é atenção, nunca bloqueio.
            def fora_do_novo(texto: str) -> str:
                for s in inserir:
                    texto = texto.replace(_norm(s), " ")
                return texto

            agora = fora_do_novo(corpo)
            presentes = [r for r in remover if _norm(r) in agora]
            if presentes and corpo_anterior:
                antes = fora_do_novo(corpo_anterior)
                # O que não existia antes não tinha como sair: o PO citou de memória («onde diz “abre a Central de
                # Apoio”» num critério que dizia «acessa a central de apoio») e a troca foi feita. Se o texto aparece
                # agora, é novo e em outro lugar — atenção, não bloqueio (exp02em1b, 23/10/2026).
                novos = [r for r in presentes if antes.count(_norm(r)) == 0]
                ficou = [r for r in presentes if r not in novos and agora.count(_norm(r)) >= antes.count(_norm(r))]
                if novos and not ficou:
                    achado(it, "atencao", "remocao-a-conferir",
                           f"O pedido manda tirar «{novos[0][:160]}», que não estava na versão anterior e agora aparece "
                           f"em outro lugar — confira se o pedido mirava esse trecho: «{trecho}».")
                    continue
                if ficou:
                    achado(it, "bloqueio" if do_po else "atencao", "remocao-nao-aplicada",
                           f"O pedido manda tirar «{ficou[0][:160]}», e nenhuma ocorrência saiu do documento: «{trecho}».")
                    continue
            elif presentes:
                achado(it, "atencao", "remocao-a-conferir",
                       f"O pedido manda tirar «{presentes[0][:160]}», e o trecho ainda aparece no documento — confira se "
                       f"é o mesmo lugar: «{trecho}».")
                continue
        # O item que é só o texto ditado («“Você é moderador…”») não tem outra exigência, diga o intérprete o que disser.
        # Pode sobrar um rótulo sem verbo: o título da seção seguinte do pedido («2. Central de Apoio — nova tela»)
        # gruda no item quando não tem ponto final (exp02em1b, 23/10/2026).
        resto = _norm(re.sub(r"[“”\"«»]", " ", it["texto"]))
        for s in inserir:
            resto = resto.replace(_norm(s), " ")
        so_o_texto = bool(inserir) and len(resto.split()) <= 8 and not _RE_ACAO.search(resto)
        texto_lido_prova = (bool(inserir or remover) and (so_o_texto or not lido.get("outras_exigencias", True))
                            and veredito not in ("violado", "conflito_com_regra")
                            and all(_trecho_confere(s, corpo) for s in inserir))
        if veredito == "atendido" and _citacao_confere(citacao, doc) and not _norm(citacao) in _norm(it["texto"]):
            conferidos.append({"id": it["id"], "texto": trecho, "prova": citacao[:240]})
        elif todas_provam:
            conferidos.append({"id": it["id"], "texto": trecho, "prova": " · ".join(c[:120] for c in varias)[:400]})
        elif ditado or sem_exigencia:
            conferidos.append({"id": it["id"], "texto": trecho, "prova": citacao[:240]})
        elif texto_lido_prova:
            # o texto que o PO ditou, com ou sem aspas, está no corpo; o que mandou tirar, não
            prova = (f"texto ditado no documento: {' · '.join(s[:120] for s in inserir)}" if inserir
                     else f"texto retirado do documento: {' · '.join(r[:120] for r in remover)}")
            conferidos.append({"id": it["id"], "texto": trecho, "prova": prova[:400]})
        elif veredito == "contexto" and (not exige_acao(it["texto"]) or _RE_REMETE_A_LISTA.search(it["texto"])):
            # título ou contexto do pedido, sem verbo de ação: não há o que provar
            conferidos.append({"id": it["id"], "texto": trecho, "prova": "(contexto do pedido, sem exigência)"})
        elif veredito == "contexto":
            achado(it, "bloqueio" if do_po else "atencao", "exigencia-dispensada",
                   f"O juiz tratou como contexto uma frase com verbo de ação — é exigência e precisa de prova: «{trecho}».")
        elif veredito == "conflito_com_regra":
            achado(it, "decisao_humana", "conflito-pedido-regra",
                   f"O pedido conflita com uma regra da esteira — decisão do PO, não do agente: «{trecho}». {explicacao}")
        elif veredito == "violado":
            achado(it, "bloqueio", "pedido-violado" if do_po else "briefing-violado",
                   f"O documento contraria {'o pedido do PO' if do_po else 'o briefing'}: «{trecho}». {explicacao}")
        # O juiz citou o pedido, e o texto é o que o PO escreveu, novo no corpo (`_ditado_no_corpo`), sem a leitura do
        # intérprete. A comparação é literal e não lê o verbo: «usar: X» e «não mostrar X» ficam iguais, e X novo no
        # corpo pode ser o pedido cumprido ou o contrário dele. Fica 🟡, com a dúvida dita; com a leitura, a prova é a
        # do `texto_lido_prova` (o texto em `inserir`). Na revisão da C2 (25/10/2026) «Na tela de abertura, não mostrar
        # a frase …», com a frase nova no one-pager, saía ✅ «texto ditado pelo PO»; na main era 🔴 `citou-o-pedido`.
        elif (veredito == "atendido" and not lido
              and _ditado_no_corpo(ditadas := [citacao] if citacao.strip() else varias, it["texto"], corpo,
                                   corpo_anterior)):
            achado(it, "atencao", "texto-ditado-a-conferir",
                   f"O juiz citou o próprio pedido, e o texto citado é o que o PO escreveu e entrou no documento (não "
                   f"estava na versão anterior): «{ditadas[0][:160]}». Sem a leitura do intérprete, o código não sabe se "
                   f"o pedido manda pôr ou tirar esse texto — confira: «{trecho}».")
        elif veredito == "atendido" and len(_norm(citacao)) >= MIN_CITACAO and _norm(citacao) in _norm(it["texto"]):
            achado(it, "bloqueio" if do_po else "atencao", "citou-o-pedido",
                   f"O juiz diz que atende, mas citou o próprio pedido em vez do documento: «{trecho}».")
        elif veredito == "atendido":
            achado(it, "bloqueio" if do_po else "atencao", "sem-prova",
                   f"O juiz diz que atende, mas a citação não está no documento: «{trecho}».")
        else:
            achado(it, "bloqueio" if do_po else "atencao", "nao-tratado" if veredito else "nao-julgado",
                   f"{'Pedido do PO' if do_po else 'Elemento do briefing'} sem prova de que foi aplicado: «{trecho}». {explicacao}")
    # O item que um pedido mais novo do PO contrariou não é conflito com regra da esteira: o PO já decidiu
    # (`superado_por`). Depois do laço, para saber quais itens do pedido novo têm prova.
    provados = {c["id"] for c in conferidos}
    for it in itens:
        meus = [a for a in achados if a["id"] == it["id"] and a["codigo"] == "conflito-pedido-regra"]
        if not meus:
            continue
        superado = superado_por(it, decisoes.get(it["id"]) or {}, itens, provados)
        if not superado:
            continue
        achados = [a for a in achados if a not in meus]
        if _RE_PRESERVACAO.search(it["texto"]):
            # A ordem de não mexer lista várias coisas, e o pedido novo contraria uma: o resto continua valendo e não
            # tem prova aqui. Na exp01em1b (e89e91b3, 21/10/2026) «Manter integralmente: o nome da missão, o slug, o
            # ambiente…, Canal A e Canal B…» foi superada no Canal B pelo pedido de 21/10 09:44:36 — AMBÍGUO no
            # levantamento (revisão da C2, 25/10/2026).
            achado(it, "atencao", "superado-em-parte", (
                f"Um pedido mais novo do PO ({superado[0][:80]}; {', '.join(superado[1])}, com prova) contraria esta "
                f"ordem de não mexer, e o documento o segue. O que o pedido novo não contrariou continua valendo e não "
                f"tem prova aqui — confira: «{it['texto'][:240]}». "
                f"{str((decisoes.get(it['id']) or {}).get('explicacao') or '').strip()}").strip())
            continue
        conferidos.append({"id": it["id"], "texto": it["texto"][:240], "prova": (
            f"superado pelo pedido mais novo do PO ({superado[0][:80]}), que o documento segue: "
            f"{', '.join(superado[1])} com prova")})
    # O cabeçalho que só anuncia os itens seguintes («Corrigir os critérios das seguintes habilidades.») não tem trecho
    # próprio no documento: vale pela prova dos itens do mesmo pedido, quando todos a têm.
    provados = {c["id"] for c in conferidos}
    sem_prova_propria = ("sem-prova", "citou-o-pedido", "nao-tratado", "nao-julgado", "exigencia-dispensada")
    cabecalhos = {i for i, lido in (interpretacao or {}).items() if lido.get("cabecalho")}
    for it in itens:
        if it["id"] not in cabecalhos:
            continue
        meus = [a for a in achados if a["id"] == it["id"]]
        # os outros cabeçalhos não contam: dois títulos sem prova própria não se travam um ao outro
        irmaos = [i["id"] for i in itens if i["origem"] == it["origem"] and i["id"] not in cabecalhos]
        if meus and irmaos and all(a["codigo"] in sem_prova_propria for a in meus) \
                and all(i in provados for i in irmaos):
            achados = [a for a in achados if a["id"] != it["id"]]
            conferidos.append({"id": it["id"], "texto": it["texto"][:240],
                               "prova": f"cabeçalho do pedido: os {len(irmaos)} item(ns) que ele anuncia têm prova"})
    if any(a["severidade"] == "bloqueio" for a in achados):
        status = "bloqueado"
    else:
        status = "amarelo" if achados else "aprovado"
    return {"status": status, "achados": achados, "conferidos": conferidos, "fora_do_recorte": fora_do_recorte}


def aplicados_a_montante(pedidos: Sequence[Tuple[str, ...]]) -> List[Dict[str, str]]:
    """Os itens de outro dono que a triagem tirou desta etapa, como conferidos: aplicados a montante.

    O pedido do PO feito em design ou dev é dividido pela triagem (`tools/triagem_pedido.py`, PR 5 do plano «Produto
    dono do contrato»): o item de produto vai ao one-pager e à spec do Gate 0 por correção pontual de produto, e a
    fidelidade de produto o confere lá. Aqui ele aparece, sem cobrança — o A094 da exp02ef1b (23/10/2026) mandava
    «aplique o pedido como o PO o escreveu» nos documentos de design, e o design mudava produto.

    Cada entrada é `(origem, texto)` ou `(origem, texto, dono)`: no dev, o item de design de um pedido de dev também
    vem a montante, e a prova diz de quem é e que fidelidade o confere (revisão do PR 5, 24/10: saía como de
    produto). Sem dono, é de produto."""
    saida = []
    for n, entrada in enumerate(pedidos, 1):
        origem, texto = entrada[0], entrada[1]
        dono = (entrada[2] if len(entrada) > 2 else "") or "produto"
        cabeca = next((l.strip(" #>*-•") for l in (texto or "").splitlines() if l.strip(" #>*-•")), "")
        if cabeca:
            saida.append({"id": f"M{n}", "texto": cabeca[:240],
                          "prova": f"aplicado a montante — item de {dono} pela triagem ({origem[:120]}), conferido "
                                   f"pela fidelidade de {dono}"})
    return saida


def relatorio(resultado: Dict[str, Any], itens: List[Dict[str, str]], missao: str = "", onde: str = "") -> str:
    icone = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}[resultado["status"]]
    titulo = "# Fidelidade ao pedido do PO e ao briefing" + (f" — {missao}" if missao else "") + (f" ({onde})" if onde else "")
    linhas = [titulo, "",
              f"**Veredito: {icone}** · {len(itens)} item(ns) · {len(resultado['conferidos'])} com prova · "
              f"{len(resultado['achados'])} achado(s)", ""]
    if not itens:
        linhas += ["Nada a conferir: não há pedido do PO nem briefing com direcionamento, passos ou elementos fixos.", ""]
    if resultado["achados"]:
        linhas += ["## O que não está comprovado", ""]
        for a in resultado["achados"]:
            marca = {"bloqueio": "🔴", "atencao": "🟡", "decisao_humana": "🔵"}.get(a["severidade"], "⚪")
            linhas.append(f"- {marca} **{a['id']}** ({a['origem']}) — {a['resumo']}")
        # só quando há item aplicado a montante: o do refazer que não aplicou nada não está no one-pager (24/10)
        a_montante = any(str(c.get("prova") or "").startswith("aplicado a montante") for c in resultado["conferidos"])
        linhas += ["", "Quem escreveu o documento: aplique o pedido como o PO o escreveu. Se ele conflita com uma regra "
                   "da esteira, não escolha — registre `[ABERTO — PO]` citando os dois."
                   + (" O item que a triagem mandou a outro dono não é cobrado aqui: ele foi aplicado a montante, no "
                      "one-pager e na spec do Gate 0." if a_montante else ""), ""]
    if resultado["conferidos"]:
        linhas += ["## Conferido", ""]
        linhas += [f"- ✅ **{c['id']}** — {c['texto'][:140]} → «{c['prova'][:160]}»" for c in resultado["conferidos"]]
        linhas.append("")
    if resultado.get("fora_do_recorte"):
        # o núcleo é só parte do que o pedido cobre: o que ele não prova é conferido no fim de produto (C2, 25/10/2026)
        linhas += ["## Fora do recorte deste documento — conferido no fim de produto", "",
                   "O núcleo é só parte do que o pedido cobre: o item sem prova aqui não é achado. O fim de produto "
                   "confere núcleo, one-pager e spec juntos.", ""]
        linhas += [f"- ⏭️ **{f['id']}** — {f['texto'][:140]}" for f in resultado["fora_do_recorte"]]
        linhas.append("")
    env = {"agente": "fidelidade-check", "missao": missao, "status": resultado["status"],
           "achados": resultado["achados"],
           "precisa_humano": any(a["severidade"] == "decisao_humana" for a in resultado["achados"])}
    linhas += ["```json", json.dumps(env, ensure_ascii=False, indent=1), "```", ""]
    return "\n".join(linhas)


def avaliar(parecer: str, saida_juiz: str, doc_atual: str = "", doc_anterior: str = "") -> List[Dict[str, Any]]:
    """Os achados do parecer do PO contra a saída do juiz, o documento atual e (opcional) a versão anterior."""
    itens = montar_checklist([("parecer", parecer)], "")
    if not itens:
        itens = [{"id": "F1", "origem": "parecer", "tipo": "ajuste", "texto": parecer.strip()}]
    docs = {"atual": doc_atual} if doc_atual else {}
    res = aplicar(itens, saida_juiz, docs, anteriores={"atual": doc_anterior} if doc_anterior else None)
    return res["achados"]

