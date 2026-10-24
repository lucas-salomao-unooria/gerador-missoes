"""Pedido do PO feito em design ou dev: item a item, o que é de produto vai a produto. Determinístico, sem LLM.

Até 23/10/2026 o pedido feito no parecer de design ou de dev ficava preso na etapa: o editor pontual de design não edita
o one-pager nem a spec (`tools/edicao_pontual.py`), o Refazer não passava pela triagem, e o A094 cobrava a aplicação nos
documentos de design. Na exp02ef1b (23/10 13:24) o PO trocou textos de tela, o nº de opções da 5A e o botão «Publicar no
Álbum», que está quatro vezes na spec do Gate 0: os textos novos chegaram a copy, protótipo, handoff e PRD e a 0
documento de produto, e o pedido custou quatro refazeres de design (plano «Produto dono do contrato», PR 5, D4).

Aqui:

- `itens_do_pedido` divide o pedido em itens (seções por título, ou a lista de primeiro nível) e separa o contexto
  (preâmbulo, «Resumo geral») — o que o PO vê no cartão e o que a triagem do LLM recebe numerado;
- `regra_de_produto` é a regra conservadora: vai para produto o item cujo texto-alvo existe em núcleo, one-pager ou spec
  do Gate 0, ou que muda número, regra, gatilho, estado, opções, habilidade, Canal B ou podcast;
- `dividir` junta a regra à resposta da triagem (`prompts/transversal/triagem_correcao.md`): a regra só manda para
  produto, nunca tira de lá; item sem dono — a triagem não respondeu e a regra não o pega — fica `indefinido`, e o
  Refazer não sai (D4, opção B: Devolver a Produto).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

PRODUTO = "produto"
DESIGN = "design"
DEV = "dev"
INDEFINIDO = "indefinido"
#: Donos possíveis de um item pedido em cada etapa. O pedido feito ao design não tem item de dev: o dev ainda não rodou
#: (ou será refeito depois do de acordo de design) e lê o pedido nas notas de passagem.
DONOS_POR_ETAPA: Dict[str, Tuple[str, ...]] = {DESIGN: (PRODUTO, DESIGN), DEV: (PRODUTO, DESIGN, DEV)}
ROTULO_DONO = {PRODUTO: "Produto", DESIGN: "Design", DEV: "Dev", INDEFINIDO: "sem dono"}

#: Onde o texto-alvo é procurado: o contrato que o PO aprova. A spec é a do Gate 0 (a consolidada traz os blocos 13 e 14
#: do design, que não são produto).
DOCUMENTOS_DE_PRODUTO = ("nucleo_narrativo", "one_pager", "one_pager_resumido", "spec_missao_gate0")
ROTULO_DOC = {"nucleo_narrativo": "núcleo", "one_pager": "one-pager", "one_pager_resumido": "one-pager resumido",
              "spec_missao_gate0": "spec do Gate 0"}
#: Frase solta do pedido que já está, igual, num documento de produto: o item mira o contrato.
MIN_PALAVRAS_FRASE = 8

_RE_TITULO = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_RE_MARCA_LISTA = re.compile(r"^(\s*)(?:[-*•]|\d{1,2}[.)])\s+\S")
#: Seção do pedido que não pede nada: o resumo e o contexto valem para todos os itens, não são item (exp02ef1b, 23/10
#: 13:24: o «Resumo geral dos ajustes» só repete os itens e pede para manter as interações). O título inteiro tem de ser
#: isso — a palavra e, no máximo, um qualificador do pedido —, sem ID de tela: buscada em qualquer lugar do título, a
#: palavra tirava da divisão a tela «E1-ALU-01 — Introdução» ou o «Card de resumo» da E0-PROF-05, e o texto dela não
#: chegava à regra, ao PO nem a produto (revisão do PR 5, 24/10). Título ambíguo é item: é o lado conservador.
_RE_TITULO_DE_CONTEXTO = re.compile(
    r"^(?:resumo|contexto|vis[ãa]o\s+geral|observa[çc][õo]es(?:\s+gerais)?|introdu[çc][ãa]o)"
    r"(?:\s+(?:geral|gerais|d[oa]s?\s+(?:pedidos?|ajustes?|altera[çc](?:[ãa]o|[õo]es)|mudan[çc]as?|corre[çc](?:[ãa]o|[õo]es))))*"
    r"\s*:?$", re.I)
_RE_ID_DE_TELA = re.compile(r"\bE\d+-(?:ALU|PROF)-\d+", re.I)
_ASPAS = (("“", "”"), ('"', '"'), ("«", "»"), ("‘", "’"))
#: Verbo que muda alguma coisa — a palavra-chave só conta na frase que tem um deles: «A porcentagem é uma regra do
#: sistema» (exp02ef1b, E3-ALU-01) não muda regra nenhuma. Fora da lista ficam os substantivos que o radical casava
#: («criança», «alternativa»: «A criança precisa ver 3 cartas» ia a produto; revisão do PR 5, 24/10).
_RE_VERBO_DE_MUDANCA = re.compile(
    r"\b(?:troc\w*|mud\w*|alter(?!nativ)\w*|substitu\w*|acrescent\w*|inclu\w*|cri(?!an[çc])\w*|tir\w*|retir\w*|"
    r"remov\w*|exclu\w*|passa\w*|atualiz\w*|aument\w*|reduz\w*|diminu\w*|nov[oa]s?|elimin\w*|adicion\w*|"
    r"reescrev\w*|corrig\w*|ajust\w*|tro[cq]u\w*|subir|baixar|dobr\w*|deix\w*)\b", re.I)
#: Forma de pedir sem verbo de troca («deve ser 9 minutos», «quero 2 opções», «usar 30%», «em vez de 3»): passava pela
#: regra (revisão do PR 5, 24/10). Conta só para número, opções e gatilho — com «estado» ou «regra», «usar os nomes de
#: estado da spec» (exp06ef1b, 09/10 12:11) é pedido de dev, não mudança de estado.
_RE_FORMA_DE_PEDIDO = re.compile(
    r"\b(?:us[ae]r?|usem|quer\w*|quero|em\s+vez\s+d[eao]s?|no\s+lugar\s+d[eao]s?|ser\s+de|"
    r"dev(?:e|em|eria|eriam)\s+(?:ser|ter|ficar|aparecer|mostrar|haver|valer|durar|come[çc]ar|terminar|liberar))\b",
    re.I)
#: «Na H1, o corte é 30%, não 25%» (o caso do D11): o número novo e, depois da vírgula, o que ele substitui.
_RE_N_NAO_M = re.compile(r"(\d+(?:[.,]\d+)?)\s*\S{0,12},?\s+n[ãa]o\s+(?:os?\s+|as?\s+)?(\d+(?:[.,]\d+)?)", re.I)
#: Número que mede o que o plano dá a produto (tempo, opções, palavras, %, rodadas e tentativas): fora de citação, conta
#: como mudança mesmo sem verbo («Teto de 20 palavras no Canal A.»). Cartas, fotos, pares e px ficam de fora: são
#: conteúdo e tela, e «ver 3 cartas na tela» não é contrato.
_RE_NUMERO_DE_PRODUTO = re.compile(r"(?<![\w.,/])\d+(?:[.,]\d+)?\s?(?:%|segundos?\b|seg\b|s\b|minutos?\b|min\b|"
                                   r"palavras\b|caracteres\b|op[çc][õo]es\b|alternativas\b|tentativas\b|rodadas\b)",
                                   re.I)
#: Tirar ou pôr uma fase, rodada ou etapa muda a mecânica: «Remover a fase 2 do mini-jogo.»
_RE_ESTRUTURA_DA_MECANICA = re.compile(
    r"\b(?:tir|retir|remov|exclu|elimin|acrescent|adicion|inclu|cri(?!an[çc])|junt|separ|divid)\w*\s+"
    r"(?:(?:a|o|as|os|uma?|mais|outra|nova|novo|toda|todo)\s+){0,2}(?:fases?|rodadas?|etapas?|tentativas?)\b", re.I)
#: Gatilho: o que destrava o quê, contado em tentativas, erros, acertos ou rodadas («O feedback deve aparecer só depois da
#: segunda tentativa.»).
_RE_GATILHO = re.compile(r"\b(?:depois|ap[óo]s|antes|at[ée])\s+d?[aeo]?s?\s*(?:\w+\s+){0,2}"
                         r"(?:tentativas?|erros?|acertos?|rodadas?)\b", re.I)
#: O que o item muda e o plano dá a produto (D1, D6, D7): regra, gatilho, estado, habilidade e a régua dela.
_RE_TEMA_DE_PRODUTO = re.compile(
    r"\b(?:regras?|gatilhos?|estados?|habilidades?|EF\d{2}CO\d{2}|EM13CO\d{2}|CO\d{2}|tern[áa]ri\w*|r[ée]gua|"
    r"forma\s+de\s+avalia\w*|crit[ée]rios?\s+de\s+avalia\w*|mec[âa]nica\w*)\b", re.I)
#: Sempre de produto, com ou sem verbo: Canal B e podcast são textos-chave do one-pager (D1). Desde o PR 7, também o item
#: que cita o ID de um texto-chave (`TC-07`, a opção `TC-12.2`): a proposta do design que o PO aceita no Refazer chega
#: com o ID dela (`tools/textos_chave.py`).
_RE_SEMPRE_PRODUTO = re.compile(r"\bcanal\s*b\b|\bpodcast\w*|\bTC-\d{1,3}(?:\.\d{1,2})?\b", re.I)
_RE_OPCOES = re.compile(r"\bop[çc](?:[ãa]o|[õo]es)\b|\balternativas?\b", re.I)
_RE_DE_PARA_NUMERO = re.compile(r"\bde\s+(\d+(?:[.,]\d+)?)\s*\S{0,12}\s+(?:para|por|→|->)\s+(\d+(?:[.,]\d+)?)", re.I)
_RE_NUMERO = re.compile(r"(?<![\w.,/])(\d+(?:[.,]\d+)?)\s?(%|segundos?\b|seg\b|s\b|minutos?\b|min\b|palavras\b|"
                        r"caracteres\b|op[çc][õo]es\b|alternativas\b|tentativas\b|rodadas\b|pares\b|cartas\b|fotos\b|"
                        r"px\b|vezes\b)", re.I)
#: «sem rótulos como “Brincar 1”», «tirar “Concluir Análise”»: a citação depois disto é texto a sair, não texto novo.
_RE_ANTES_DE_ALVO = re.compile(r"(?:\bsem\b|\btir\w*|\bretir\w*|\bremov\w*|\bexclu\w*|\bno\s+lugar\s+de|"
                               r"\bonde\s+diz|\btexto\s+atual|\btroc\w*|\bhoje\b|\batualmente\b)[^.\n“\"«‘]{0,40}$", re.I)
_RE_MARCA_NOVO = re.compile(r"\bajuste\s+solicitado\b|\baltera[çc][ãa]o\s+solicitada\b|\bnovo\s+texto\b|"
                            r"\btexto\s+novo\b|\bpassa\s+a\s+ser\b|\bdeve\s+ficar\b|\bpor\s*$", re.I)
_RE_MARCA_ATUAL = re.compile(r"\btexto\s+atual\b|\batualmente\b|\bhoje\s+(?:est[áa]|diz|aparece)|\bonde\s+diz\b", re.I)
_PALAVRAS_VAZIAS = frozenset("""a o as os de da do das dos e em no na nos nas um uma uns umas por para com sem que se
ao aos ou the""".split())


# ------------------------------------------------------------------ normalização
def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")


def _palavras(texto: str) -> List[str]:
    return re.sub(r"[^a-z0-9]+", " ", _sem_acento(texto)).split()


def _norm(texto: str) -> str:
    return " " + " ".join(_palavras(texto)) + " "


# ------------------------------------------------------------------ itens
@dataclass
class ItemDoPedido:
    """Um item do pedido: o trecho literal, o dono final e por quê."""

    n: int
    texto: str
    titulo: str = ""
    dono: str = INDEFINIDO
    #: O que a triagem do LLM disse, e o motivo dela.
    dono_triagem: str = ""
    motivo_triagem: str = ""
    #: Por que a regra determinística manda o item a produto (vazio = a regra não o pega).
    regra: List[str] = field(default_factory=list)
    #: O PO mudou o dono no cartão (só para produto: a regra conservadora não deixa tirar de lá).
    pelo_po: bool = False

    @property
    def forcado(self) -> bool:
        return bool(self.regra)

    def rotulo(self, limite: int = 90) -> str:
        cabeca = self.titulo or next((l.strip(" -*•#>") for l in self.texto.splitlines() if l.strip(" -*•#>")), "")
        cabeca = re.sub(r"\s+", " ", cabeca)
        return cabeca if len(cabeca) <= limite else cabeca[: limite - 1] + "…"


@dataclass
class Divisao:
    """O pedido dividido: cada item com o dono, e o contexto que vale para todos."""

    etapa: str
    itens: List[ItemDoPedido] = field(default_factory=list)
    contexto: str = ""

    def de(self, dono: str) -> List[ItemDoPedido]:
        return [i for i in self.itens if i.dono == dono]

    @property
    def indefinidos(self) -> List[ItemDoPedido]:
        return self.de(INDEFINIDO)

    @property
    def tem_produto(self) -> bool:
        return bool(self.de(PRODUTO))

    def texto_de(self, *donos: str, com_contexto: bool = False) -> str:
        """O texto literal dos itens destes donos, na ordem do pedido. O contexto entra só quando pedido: no texto de
        produto ele virava ordem de não mexer sem prova (o «Resumo geral» de 23/10 13:24 deu 🔴 de preservação)."""
        partes = [i.texto.strip() for i in self.itens if i.dono in donos]
        if com_contexto and self.contexto.strip():
            partes.append(self.contexto.strip())
        return "\n\n".join(p for p in partes if p)

    def como_dict(self) -> Dict[str, Any]:
        return {"etapa": self.etapa, "contexto": self.contexto, "itens": [asdict(i) for i in self.itens]}

    @classmethod
    def de_dict(cls, dados: Optional[Dict[str, Any]]) -> Optional["Divisao"]:
        if not isinstance(dados, dict) or not isinstance(dados.get("itens"), list):
            return None
        itens = []
        for d in dados["itens"]:
            if isinstance(d, dict):
                campos = {k: d[k] for k in ItemDoPedido.__dataclass_fields__ if k in d}
                itens.append(ItemDoPedido(**campos))
        return cls(etapa=str(dados.get("etapa") or ""), itens=itens, contexto=str(dados.get("contexto") or ""))


def _aspas_abertas(linha: str, abertas: bool) -> bool:
    """Se ao fim da linha uma citação de várias linhas segue aberta. As curvas contam como alternância: na exp02em1b
    (23/10 17:08) o PO abriu a citação com ” e as linhas com • dentro dela são a fala do aluno, não itens do pedido."""
    for c in linha:
        if c in "“”":
            abertas = not abertas
    return abertas


def _titulo_de_contexto(titulo: str) -> bool:
    limpo = re.sub(r"\s+", " ", titulo.strip(" #*_`\t")).strip()
    return bool(_RE_TITULO_DE_CONTEXTO.match(limpo)) and not _RE_ID_DE_TELA.search(limpo)


def _secoes_por_titulo(texto: str) -> Optional[Tuple[str, List[Tuple[str, str]]]]:
    """`(contexto, [(título, trecho)])` pelas seções de título mais fundas; None se o pedido não tem dois títulos."""
    linhas = texto.splitlines()
    titulos = [(i, len(m.group(1)), m.group(2)) for i, l in enumerate(linhas) if (m := _RE_TITULO.match(l))]
    if len(titulos) < 2:
        return None
    contexto: List[str] = ["\n".join(linhas[: titulos[0][0]]).strip()]
    secoes: List[Tuple[str, str]] = []
    for k, (i, nivel, titulo) in enumerate(titulos):
        fim = titulos[k + 1][0] if k + 1 < len(titulos) else len(linhas)
        corpo = "\n".join(linhas[i + 1: fim]).strip()
        if not corpo:
            continue  # título que só abre subtítulos («## Pedidos de ajustes»)
        trecho = "\n".join(linhas[i: fim]).strip()
        if _titulo_de_contexto(titulo):
            contexto.append(trecho)
        else:
            secoes.append((titulo.strip(" #*"), trecho))
    if not secoes:
        return None
    return "\n\n".join(c for c in contexto if c), secoes


def _rotulo_curto(linha: str) -> bool:
    """«Encaminhar para», «Opções:»: rótulo que abre uma lista de opções, não um item."""
    s = linha.strip()
    return bool(s) and not _RE_MARCA_LISTA.match(linha) and len(s.split()) <= 4 and not re.search(r"[.!?]$", s)


def _itens_por_lista(texto: str) -> Optional[Tuple[str, List[Tuple[str, str]]]]:
    """`(contexto, [(cabeça, trecho)])` pela lista do pedido; None se ele não tem dois marcadores de lista.

    Um marcador abre item novo, salvo dentro de citação aberta ou logo depois de um rótulo curto («Encaminhar para»:
    os marcadores que seguem são as opções dele)."""
    linhas = texto.splitlines()
    inicios: List[int] = []
    abertas = False
    anterior = ""
    indentacao_das_opcoes: Optional[int] = None
    for i, l in enumerate(linhas):
        m = _RE_MARCA_LISTA.match(l)
        if m and not abertas:
            recuo = len(m.group(1).replace("\t", "    "))
            if _rotulo_curto(anterior):
                indentacao_das_opcoes = recuo
            elif indentacao_das_opcoes is None or recuo != indentacao_das_opcoes:
                indentacao_das_opcoes = None
                inicios.append(i)
        elif l.strip():
            if not _rotulo_curto(l):
                indentacao_das_opcoes = None
        abertas = _aspas_abertas(l, abertas)
        if l.strip():
            anterior = l
    if len(inicios) < 2:
        return None
    contexto = "\n".join(linhas[: inicios[0]]).strip()
    itens = []
    for k, i in enumerate(inicios):
        fim = inicios[k + 1] if k + 1 < len(inicios) else len(linhas)
        trecho = "\n".join(linhas[i:fim]).strip()
        itens.append((re.sub(r"^\s*(?:[-*•]|\d{1,2}[.)])\s+", "", linhas[i]).strip(), trecho))
    return contexto, itens


def itens_do_pedido(texto: str) -> Tuple[str, List[Tuple[str, str]]]:
    """`(contexto, [(cabeça, trecho literal)])` — os itens do pedido, na ordem em que o PO os escreveu.

    Por título (o formato por tela da exp02ef1b, 23/10 13:24), senão pela lista (os • da exp02em1b, 23/10 17:08; os
    «1.» do refazer de produto de 23/10 11:01), senão por parágrafo. Pedido de um parágrafo só é um item."""
    texto = (texto or "").strip()
    if not texto:
        return "", []
    for divisor in (_secoes_por_titulo, _itens_por_lista):
        dividido = divisor(texto)
        if dividido:
            return dividido
    paragrafos = [p.strip() for p in re.split(r"\n\s*\n", texto) if p.strip()]
    return "", [("", p) for p in paragrafos] if len(paragrafos) > 1 else [("", texto)]


# ------------------------------------------------------------------ a regra conservadora
def _citacoes(texto: str) -> List[Tuple[int, str]]:
    """(posição, trecho) de cada citação do item, com “…”, "…", «…» e ‘…’ (o PO da exp02em1b citou o botão com ‘…’)."""
    saida, aberta, inicio = [], None, 0
    for i, c in enumerate(texto or ""):
        if aberta is None:
            for a, f in _ASPAS:
                if c == a:
                    aberta, inicio = f, i + 1
                    break
        elif c == aberta:
            saida.append((inicio, texto[inicio:i]))
            aberta = None
        elif c == "\n" and len(texto[inicio:i]) > 400:
            aberta = None
    return saida


def _papel(texto: str, pos: int) -> str:
    """`alvo` (texto que o item manda trocar ou tirar) ou `novo` (o que ele pede). Na dúvida, `alvo`: é o lado
    conservador — o texto citado que já está em produto leva o item a produto."""
    antes = texto[:max(0, pos - 1)]
    if _RE_ANTES_DE_ALVO.search(antes[-60:]):
        return "alvo"
    marcas = sorted([(m.start(), "alvo") for m in _RE_MARCA_ATUAL.finditer(antes)]
                    + [(m.start(), "novo") for m in _RE_MARCA_NOVO.finditer(antes)])
    return marcas[-1][1] if marcas else "alvo"


def _linhas_normalizadas(docs: Dict[str, str]) -> Dict[str, List[str]]:
    return {k: [_norm(l) for l in (docs.get(k) or "").splitlines() if l.strip()] for k in DOCUMENTOS_DE_PRODUTO}


def _onde_esta(frase: str, linhas: Dict[str, List[str]]) -> Dict[str, int]:
    """Em que documentos de produto a frase está, numa linha só (sem caixa nem acento). Juntar o documento inteiro
    casava «Brincar 2» com «brincar» no fim de uma linha e «2.» no começo da seguinte."""
    alvo = _norm(frase)
    if len(alvo.split()) < 1:
        return {}
    saida = {}
    for k, ls in linhas.items():
        n = sum(l.count(alvo) for l in ls)
        if n:
            saida[k] = n
    return saida


def _palavras_numa_linha(frase: str, linhas: Dict[str, List[str]]) -> Dict[str, int]:
    """Citação sem acento ou abreviada («‘metricas publicacao’», exp02em1b 17:08): as palavras dela, todas na mesma
    linha de um documento de produto. Só para citação de 2 a 6 palavras com pelo menos duas significativas."""
    palavras = [p for p in _palavras(frase) if p not in _PALAVRAS_VAZIAS and len(p) >= 4]
    if len(palavras) < 2 or len(_palavras(frase)) > 6:
        return {}
    saida = {}
    for k, ls in linhas.items():
        n = sum(1 for l in ls if all(f" {p}" in l for p in palavras))
        if n:
            saida[k] = n
    return saida


def _frases(texto: str) -> List[str]:
    return [f.strip() for f in re.split(r"(?<=[.!?:])\s+|\n+", texto or "") if f.strip()]


def _muda(frase: str, com_pedido: bool = False) -> bool:
    """A frase tem verbo de mudança que não está negado: «Não alterar telas, mecânica nem os demais textos aprovados»
    (exp06ef1b, 09/10 12:11) é ordem de não mexer, não mudança de mecânica. `com_pedido` aceita também a forma de pedir
    sem verbo de troca (`_RE_FORMA_DE_PEDIDO`)."""
    for regex in (_RE_VERBO_DE_MUDANCA, _RE_FORMA_DE_PEDIDO) if com_pedido else (_RE_VERBO_DE_MUDANCA,):
        for m in regex.finditer(frase or ""):
            antes = _palavras(frase[: m.start()])[-2:]
            if not any(p in ("nao", "nem", "sem", "nunca") for p in antes):
                return True
    return False


def _numeros(texto: str) -> set:
    return {(m.group(1).replace(",", "."), _sem_acento(m.group(2))[:3]) for m in _RE_NUMERO.finditer(texto or "")}


def _onde(contagem: Dict[str, int]) -> str:
    return ", ".join(f"{ROTULO_DOC.get(k, k)} ({n})" for k, n in contagem.items())


def regra_de_produto(texto: str, docs: Dict[str, str], linhas: Optional[Dict[str, List[str]]] = None) -> List[str]:
    """Por que o item é de produto, segundo a regra conservadora do plano (PR 5); vazio se ela não o pega.

    - o texto-alvo (o que o item cita para trocar ou tirar, ou uma frase dele com 8 palavras ou mais) está em núcleo,
      one-pager, one-pager resumido ou spec do Gate 0;
    - o item muda opções, número (um número novo, «de N para M», «N, não M», ou tempo, opções, palavras, %, rodadas e
      tentativas fora de citação), regra, gatilho, estado, habilidade ou fases e rodadas da mecânica (a palavra e um
      verbo ou forma de pedido na mesma frase), ou fala de Canal B ou podcast.
    Palavra solta citada («Pronto») não conta: casa com qualquer texto."""
    linhas = linhas if linhas is not None else _linhas_normalizadas(docs)
    motivos: List[str] = []
    citacoes = _citacoes(texto)
    novos_txt, atuais_txt = [], []
    for pos, trecho in citacoes:
        frase = re.sub(r"\s+", " ", trecho).strip()
        if not frase:
            continue
        papel = _papel(texto, pos)
        (atuais_txt if papel == "alvo" else novos_txt).append(frase)
        if papel != "alvo" or len(_palavras(frase)) < 2:
            continue
        onde = _onde_esta(frase, linhas) or _palavras_numa_linha(frase, linhas)
        if onde:
            motivos.append(f"o texto-alvo «{frase[:80]}» está em {_onde(onde)}")
    sem_citacoes = texto
    for _, trecho in citacoes:
        sem_citacoes = sem_citacoes.replace(trecho, " ")
    for frase in _frases(texto):
        if len(_palavras(frase)) >= MIN_PALAVRAS_FRASE and not any(frase[:60] in m for m in motivos):
            onde = _onde_esta(frase.strip("“”\"«»‘’ "), linhas)
            if onde:
                motivos.append(f"a frase «{frase[:80]}» está em {_onde(onde)}")
                break
    if _RE_SEMPRE_PRODUTO.search(texto):
        citado = _RE_SEMPRE_PRODUTO.search(texto).group(0)
        motivos.append(f"cita o texto-chave {citado.upper()} do one-pager" if citado.upper().startswith("TC-")
                       else f"fala de {citado}, texto-chave do one-pager")
    # opções: o item lista as novas («Opções: “A atividade” · “A cor da roupa”», 13:24), ou muda as que existem na
    # mesma frase («tirar a opção “Lugar”», «deixar só 2 opções»)
    if _RE_OPCOES.search(texto) and (novos_txt or any(_RE_OPCOES.search(f) and _muda(f, com_pedido=True)
                                                      for f in _frases(texto))):
        motivos.append("muda as opções que o aluno vê")
    de_para = _RE_DE_PARA_NUMERO.search(sem_citacoes) or _RE_N_NAO_M.search(sem_citacoes)
    if de_para:
        motivos.append(f"muda número ({de_para.group(0).strip()[:40]})")
    else:
        numeros_novos = _numeros(" ".join(novos_txt)) - _numeros(" ".join(atuais_txt))
        if numeros_novos:
            motivos.append("muda número (" + ", ".join(f"{n} {u}" for n, u in sorted(numeros_novos)) + ")")
        else:
            for frase in _frases(sem_citacoes):
                if (_RE_NUMERO.search(frase) and _muda(frase, com_pedido=True)) or _RE_NUMERO_DE_PRODUTO.search(frase):
                    motivos.append(f"muda número ({frase[:60]})")
                    break
    for frase in _frases(sem_citacoes):
        tema = _RE_TEMA_DE_PRODUTO.search(frase)
        if tema and _muda(frase) or not tema and _RE_GATILHO.search(frase) and _muda(frase, com_pedido=True):
            motivos.append(f"muda {tema.group(0).lower() if tema else 'gatilho'} («{frase[:70]}»)")
            break
    for frase in _frases(sem_citacoes):
        estrutura = _RE_ESTRUTURA_DA_MECANICA.search(frase)
        if estrutura and _muda(frase):
            motivos.append(f"muda a mecânica («{frase[:70]}»)")
            break
    return list(dict.fromkeys(motivos))


def documentos_de_produto(estado: Dict[str, Any]) -> Dict[str, str]:
    """Os documentos onde o texto-alvo é procurado. Sem a spec do Gate 0 (sessão antiga), a `spec_missao` sem os blocos
    13 e 14 do design (`tools.propagacao.spec_de_produto`)."""
    docs = {k: str(estado.get(k) or "") for k in DOCUMENTOS_DE_PRODUTO}
    if not docs["spec_missao_gate0"].strip():
        from tools.propagacao import spec_de_produto

        docs["spec_missao_gate0"] = spec_de_produto(str(estado.get("spec_missao") or ""))
    return docs


# ------------------------------------------------------------------ divisão
def _dono_da_triagem(valor: str, etapa: str) -> str:
    """O dono que a triagem do LLM deu, no vocabulário da etapa. `spec` é produto; `nenhuma` (pergunta, comentário)
    fica na etapa — não muda documento de produto; o que a etapa não tem vira a etapa."""
    v = (valor or "").strip().lower()
    if v in (PRODUTO, "spec"):
        return PRODUTO
    if v in (DESIGN, DEV, "nenhuma"):
        dono = etapa if v == "nenhuma" else v
        return dono if dono in DONOS_POR_ETAPA.get(etapa, ()) else etapa
    return INDEFINIDO


def dividir(pedido: str, etapa: str, estado: Dict[str, Any],
            triagem_itens: Optional[Sequence[Dict[str, Any]]] = None) -> Divisao:
    """O pedido dividido por dono. `triagem_itens` é o que a triagem do LLM devolveu (`[{n, dono, motivo}]`, os números
    de `itens_do_pedido`); sem ela, o item que a regra não pega fica `indefinido`."""
    contexto, brutos = itens_do_pedido(pedido)
    docs = documentos_de_produto(estado)
    linhas = _linhas_normalizadas(docs)
    respostas: Dict[int, Dict[str, Any]] = {}
    for r in triagem_itens or []:
        try:
            respostas[int(r.get("n"))] = r
        except (TypeError, ValueError, AttributeError):
            continue
    itens: List[ItemDoPedido] = []
    for n, (titulo, trecho) in enumerate(brutos, 1):
        resposta = respostas.get(n) or {}
        dono_llm = _dono_da_triagem(str(resposta.get("dono") or ""), etapa) if resposta else ""
        regra = regra_de_produto(trecho, docs, linhas)
        dono = PRODUTO if regra else (dono_llm or INDEFINIDO)
        itens.append(ItemDoPedido(n=n, texto=trecho, titulo=titulo, dono=dono, dono_triagem=dono_llm,
                                  motivo_triagem=str(resposta.get("motivo") or "").strip(), regra=regra))
    return Divisao(etapa=etapa, itens=itens, contexto=contexto)


def com_escolhas_do_po(divisao: Divisao, escolhas: Dict[int, bool]) -> Divisao:
    """A divisão com o que o PO marcou no cartão (`{n: vai a produto?}`). O item que a regra pôs em produto não sai de
    lá — é o caminho conservador do plano —, e o indefinido só sai do limbo indo a produto: deixá-lo na etapa seria a
    esteira escolhendo o dono (D4, opção B). O que a triagem do LLM deu a produto e a regra não pega, o PO pode deixar na
    etapa: a triagem erra o dono, e quem decide é ele."""
    itens = []
    for i in divisao.itens:
        quer = escolhas.get(i.n)
        if quer is not None and not i.forcado:
            if quer and i.dono != PRODUTO:
                i = ItemDoPedido(**{**asdict(i), "dono": PRODUTO, "pelo_po": True})
            elif not quer and i.dono == PRODUTO:
                i = ItemDoPedido(**{**asdict(i), "dono": divisao.etapa, "pelo_po": True})
        itens.append(i)
    return Divisao(etapa=divisao.etapa, itens=itens, contexto=divisao.contexto)


def numerados(pedido: str) -> str:
    """Os itens do pedido numerados, para a triagem do LLM responder um dono por número."""
    contexto, itens = itens_do_pedido(pedido)
    if not itens:
        return ""
    blocos = [f"### Item {n}\n\n{trecho.strip()}" for n, (_, trecho) in enumerate(itens, 1)]
    if contexto.strip():
        blocos.insert(0, f"### Contexto do pedido (não é item)\n\n{contexto.strip()}")
    return "\n\n".join(blocos)


def resumo(divisao: Divisao) -> str:
    """A divisão em markdown: o que o PO viu antes de confirmar, para o registro e para os agentes."""
    linhas = []
    for dono in (PRODUTO, DESIGN, DEV, INDEFINIDO):
        itens = divisao.de(dono)
        if not itens:
            continue
        linhas.append(f"**{ROTULO_DONO[dono]}** — {len(itens)} item(ns):")
        for i in itens:
            porque = ("; ".join(i.regra) if i.regra else
                      ("escolha do PO no cartão" if i.pelo_po else (i.motivo_triagem or "triagem")))
            linhas.append(f"- {i.n}. {i.rotulo()} — {porque}")
    return "\n".join(linhas)


def nota_para_a_etapa(divisao: Divisao) -> str:
    """O que o editor e os agentes da etapa leem junto com o pedido inteiro: os itens de produto já foram aplicados a
    montante, no one-pager e na spec do Gate 0; a etapa os acompanha onde o texto aparece nos documentos dela."""
    produto = divisao.de(PRODUTO)
    if not produto:
        return ""
    etapa = ROTULO_DONO.get(divisao.etapa, divisao.etapa)
    linhas = [f"A triagem dividiu este pedido por dono antes de aplicar. Os itens abaixo são de **produto** e já foram "
              "aplicados a montante — no one-pager e na spec do Gate 0, por correção pontual de produto. Nos documentos "
              f"de {etapa.lower()}, acompanhe-os onde o texto deles aparece (copy, telas, protótipo, handoff, PRD), "
              "sem decidir de novo; os demais itens são desta etapa.", ""]
    linhas += [f"- Item {i.n} (produto): {i.rotulo()}" for i in produto]
    outros = [i for i in divisao.itens if i.dono != PRODUTO]
    if outros:
        linhas += [""] + [f"- Item {i.n} ({ROTULO_DONO.get(i.dono, i.dono).lower()}): {i.rotulo()}" for i in outros]
    return "\n".join(linhas)
