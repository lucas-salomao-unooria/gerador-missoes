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

_RE_TRAVAS = re.compile(r"\bTRAVAS?\b[^:\n]{0,80}:(.*?)(?=\bAJUSTE\s+\d|\bVALIDA[ÇC][ÃA]O\b|$)", re.S)
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
    m = _RE_TRAVAS.search(texto or "")
    if m:
        itens += _literais(m.group(1), origem)
        itens += [{"origem": origem, "tipo": "trava", "texto": f} for f in _frases(m.group(1))]
    for aj in _RE_AJUSTE.finditer(texto or ""):
        corpo = re.sub(r"\s+", " ", aj.group(2)).strip()
        quero = re.search(r"O que quero:(.*)", corpo, re.I)
        foco = (quero.group(1) if quero else corpo).strip()
        titulo = " ".join(corpo.split(" ")[:10])
        itens.append({"origem": origem, "tipo": "ajuste", "texto": f"{aj.group(1)} — {titulo}…: {foco}"[:1200]})
    v = _RE_VALIDACAO.search(texto or "")
    if v:
        for q in v.group(1).split("?"):
            q = re.sub(r"\s+", " ", q).strip(" .")
            if _palavras(q) >= 4:
                itens.append({"origem": origem, "tipo": "validacao", "texto": q + "?"})
    if not itens and _palavras(texto) >= MIN_PALAVRAS_ITEM:
        # pedido sem estrutura: vale inteiro, como um item só
        itens.append({"origem": origem, "tipo": "pedido", "texto": re.sub(r"\s+", " ", texto).strip()[:1200]})
    return itens


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
    # A frase que o briefing pôs entre aspas é texto do PO ("Pergunta-motor: “Se a mesma coisa
    # aconteceu…”"): as três gerações da exp03ef1b a perderam. Confere-se letra a letra, como as TRAVAS.
    itens += _literais(briefing or "", "briefing")
    return itens


#: Ordem de prioridade e teto por tipo. Os pedidos repetem as travas com outras palavras (os dois
#: refazer da exp09ef1b trouxeram 42), e elas empurravam o briefing para fora do checklist.
PRIORIDADE: Tuple[Tuple[str, int], ...] = (
    ("ajuste", 12), ("pedido", 6), ("literal", 8), ("validacao", 12), ("trava", 18), ("briefing", 16))


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


def _decisoes(saida_juiz: str) -> Dict[str, Dict[str, Any]]:
    for bruto in reversed(re.findall(r"```json\s*(.*?)```", saida_juiz or "", re.S)):
        try:
            dados = json.loads(bruto)
        except json.JSONDecodeError:
            continue
        if isinstance(dados, dict) and isinstance(dados.get("decisoes"), list):
            return {str(d.get("id")): d for d in dados["decisoes"] if isinstance(d, dict)}
    return {}


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
            etapa: str = "produto") -> Dict[str, Any]:
    """`{status, achados, conferidos}` a partir dos itens, da saída do juiz e dos documentos.

    `etapa` é a de quem responde pelos documentos: o pedido de refazer do design é conferido nos documentos de
    design, e o achado é dele."""
    doc = _norm("\n".join(documentos.values()))
    decisoes = _decisoes(saida_juiz)
    achados: List[Dict[str, str]] = []
    conferidos: List[Dict[str, str]] = []

    def achado(item: Dict[str, str], severidade: str, codigo: str, resumo: str) -> None:
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
        if veredito == "atendido" and _citacao_confere(citacao, doc) and not _norm(citacao) in _norm(it["texto"]):
            conferidos.append({"id": it["id"], "texto": trecho, "prova": citacao[:240]})
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
