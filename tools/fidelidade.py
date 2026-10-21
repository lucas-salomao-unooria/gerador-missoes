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

import json
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

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
    return bool(_RE_PRESERVACAO.search(texto or "")) and not _RE_ACAO.search(_RE_PRESERVACAO.sub(" ", texto or ""))


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


def montar_checklist(pedidos: List[Tuple[str, str]], briefing: str) -> List[Dict[str, str]]:
    """`pedidos` = [(origem, texto)], do mais antigo ao mais novo. Ids F1…Fn, sem repetição.

    Por tipo, na ordem de `PRIORIDADE`; dentro do tipo, do pedido mais novo para o mais antigo —
    quando dois pedidos repetem uma trava, vale a redação mais recente.
    """
    brutos: List[Dict[str, str]] = []
    for origem, texto in reversed(pedidos):
        brutos += itens_do_pedido(texto, origem)
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
    from tools.conteudo_aprovado import remover_anexo

    return remover_anexo(texto or "")


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

    def achado(item: Dict[str, str], severidade: str, codigo: str, resumo: str) -> None:
        # `parcial`: o documento é só um pedaço do que o pedido cobre (o núcleo, seções 0/1/3/4). Falta de prova ali é
        # esperada para o item de outra seção — só a contradição explícita bloqueia; a prova completa é cobrada no fim
        # de produto. A exp06ef1b (08/10/2026) saía 🔴 no núcleo por «painel docente na Seção 9», com o fim 🟢 25/25.
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
                ficou = [r for r in presentes if agora.count(_norm(r)) >= antes.count(_norm(r))]
                if ficou:
                    achado(it, "bloqueio" if do_po else "atencao", "remocao-nao-aplicada",
                           f"O pedido manda tirar «{ficou[0][:160]}», e nenhuma ocorrência saiu do documento: «{trecho}».")
                    continue
            elif presentes:
                achado(it, "atencao", "remocao-a-conferir",
                       f"O pedido manda tirar «{presentes[0][:160]}», e o trecho ainda aparece no documento — confira se "
                       f"é o mesmo lugar: «{trecho}».")
                continue
        texto_lido_prova = (bool(inserir or remover) and not lido.get("outras_exigencias", True)
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
        elif veredito == "contexto" and (not _RE_ACAO.search(it["texto"]) or _RE_REMETE_A_LISTA.search(it["texto"])):
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
        elif veredito == "atendido" and len(_norm(citacao)) >= MIN_CITACAO and _norm(citacao) in _norm(it["texto"]):
            achado(it, "bloqueio" if do_po else "atencao", "citou-o-pedido",
                   f"O juiz diz que atende, mas citou o próprio pedido em vez do documento: «{trecho}».")
        elif veredito == "atendido":
            achado(it, "bloqueio" if do_po else "atencao", "sem-prova",
                   f"O juiz diz que atende, mas a citação não está no documento: «{trecho}».")
        else:
            achado(it, "bloqueio" if do_po else "atencao", "nao-tratado" if veredito else "nao-julgado",
                   f"{'Pedido do PO' if do_po else 'Elemento do briefing'} sem prova de que foi aplicado: «{trecho}». {explicacao}")
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
    return {"status": status, "achados": achados, "conferidos": conferidos}


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
        linhas += ["", "Quem escreveu o documento: aplique o pedido como o PO o escreveu. Se ele conflita com uma regra "
                   "da esteira, não escolha — registre `[ABERTO — PO]` citando os dois.", ""]
    if resultado["conferidos"]:
        linhas += ["## Conferido", ""]
        linhas += [f"- ✅ **{c['id']}** — {c['texto'][:140]} → «{c['prova'][:160]}»" for c in resultado["conferidos"]]
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

