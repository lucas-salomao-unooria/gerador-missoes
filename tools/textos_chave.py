"""Textos-chave com ID: o texto que o PO aprova palavra por palavra, travado do one-pager à copy. Determinístico.

PR 7 do plano «Produto dono do contrato» (docs/planos/2026-10-23-produto-dono-do-contrato.md), decisão D1: só os
textos-chave carregam ID — as aspas do §4, o Canal B do §12a (a pergunta e as alternativas), o nº de opções de cada
escolha, o podcast (§11) e o roteiro do professor (§9). A microcopy (rótulo de botão, aviso, estado de tela) fica no
design. Na exp02ef1b (23/10/2026) o PO pediu em design textos novos para cinco telas: eles chegaram à copy, ao
protótipo, ao handoff e ao PRD, e a nenhum documento de produto; das ~10 frases «atuais» que ele citou, 9 tinham sido
escritas pelo design. O one-pager tem de 14 a 36 textos entre aspas, contra 98 a 173 linhas de copy, e a maioria da
copy é microcopy (análise de 23/10).

Aqui:

- `extrair` lê os textos-chave das seções citadas, sem ID. A leitura do §4 é a do `conteudo_aprovado.textos_de_tela`
  (calibrada nas sessões do bucket), mais as escolhas com as opções entre aspas; a do §12a lê a pergunta e as
  alternativas do Canal B nos formatos do acervo — com aspas ou sem, «Alt 1», «Alternativa 1», «• Atingiu:».
- `numerar` dá o ID estável (`TC-07`; a opção de uma escolha, `TC-12.2`): o mesmo texto guarda o ID; o texto que o PO
  trocou no mesmo lugar (mesmo tipo, mesma origem, mesma posição) também; o novo ganha o próximo número, e o que saiu
  se aposenta — o número não volta.
- `da_sessao` lê qualquer sessão: a nova traz o registro (`textos_chave`, que o A044b grava no fim de produto), a
  anterior ao PR 7 é lida das mesmas seções, sem gravar nada — o acervo continua o mesmo.
- `aplicar_na_copy` copia por código cada texto-chave para a linha da copy que o cita, pelo ID ou pelo próprio texto,
  e a redação que o design tinha escrito vira `[PROPOSTA — validar com PO: …]` (a rota é a do PR 5: o PO pede no
  Refazer, e a triagem leva o item a produto). `conferir_copy` é o gate: a divergência que sobrou bloqueia.
- `aplicar_em_documento` faz o mesmo nas citações entre aspas do handoff, do PRD e do pedagógico.
- `teto_de_palavras` e `acima_do_teto` alimentam o lint de produto (A024) e a lista do de acordo (PR 3).

A tabela não entra no texto do one-pager: ela vive ao lado dele (`textos_chave_tabela`, `produto/00n-textos-chave.md`),
no cartão do de acordo e no conteúdo aprovado que design e dev leem. Dentro do one-pager, cada texto ficaria duas vezes —
e a troca do editor pontual exige trecho único, e a fidelidade compara o one-pager linha a linha com a versão anterior.
Uma tabela que o PO já tenha escrito no one-pager dele (título «Textos-chave») é lida: os IDs dele valem.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

AGENTE = "textos-chave"
#: Onde o registro fica no estado. Fora de toda lista de `pipeline/reexecucao.py`: o ID sobrevive ao refazer.
KEY_REGISTRO = "textos_chave"
KEY_TABELA = "textos_chave_tabela"

TELA = "tela"
CANAL_B = "canal_b"
OPCOES = "opcoes"
OPCAO = "opcao"
ROTEIRO = "roteiro"
PODCAST = "podcast"
ROTULO_TIPO = {TELA: "texto de tela", CANAL_B: "Canal B — pergunta", OPCOES: "escolha", OPCAO: "opção",
               ROTEIRO: "roteiro do professor", PODCAST: "podcast"}
_TIPO_DO_ROTULO = {v.lower(): k for k, v in ROTULO_TIPO.items()}
#: O que a criança lê na tela: é isto que o teto de palavras da faixa limita. Podcast é ouvido; o roteiro, o professor lê.
TIPOS_LIDOS_PELA_CRIANCA = (TELA, CANAL_B, OPCAO)
#: Texto inteiro que a copy carrega numa linha só (a escolha é conferida pelas opções dela).
TIPOS_DE_TEXTO = (TELA, CANAL_B, OPCAO, ROTEIRO, PODCAST)

TITULO_TABELA = "Textos-chave aprovados (TC)"
#: A seção que a esteira escreve na copy: as propostas do design e os textos-chave sem linha no sheet.
TITULO_SECAO_COPY = "Textos-chave aprovados — conferência da esteira"
#: O motivo das trocas que a cópia por código registra na correção pontual (`edicoes_pontuais`).
MOTIVO_TROCA_DA_COPY = "textos-chave do one-pager aprovado copiados por código para a copy (A078b, PR 7)"

_RE_ID = re.compile(r"\bTC-(\d{1,3})(?:\.(\d{1,2}))?\b")


def formatar_id(numero: int, sub: int = 0) -> str:
    return f"TC-{numero:02d}" + (f".{sub}" if sub else "")


def partes_do_id(ident: str) -> Tuple[int, int]:
    m = _RE_ID.fullmatch(ident or "")
    return (int(m.group(1)), int(m.group(2) or 0)) if m else (0, 0)


def ids_citados(texto: str) -> List[str]:
    """Os IDs de texto-chave que o texto cita, normalizados (`TC-7` → `TC-07`)."""
    return [formatar_id(int(n), int(s or 0)) for n, s in _RE_ID.findall(texto or "")]


@dataclass
class TextoChave:
    """Um texto-chave. Na escolha (`opcoes`), `opcoes` são as opções e `n` quantas são; cada opção é também um
    texto-chave próprio (`opcao`, ID `TC-nn.k`), com `grupo` apontando para a escolha."""

    id: str
    tipo: str
    origem: str
    texto: str
    grupo: str = ""
    n: int = 0
    opcoes: List[str] = field(default_factory=list)
    #: As redações aprovadas antes desta, com o mesmo ID (o PO trocou o texto no one-pager). A linha da copy que ainda
    #: traz uma delas recebe o texto novo por código, sem virar proposta do design.
    antes: List[str] = field(default_factory=list)

    def como_dict(self) -> Dict[str, Any]:
        return asdict(self)


def de_dict(d: Dict[str, Any]) -> TextoChave:
    return TextoChave(id=str(d.get("id") or ""), tipo=str(d.get("tipo") or ""), origem=str(d.get("origem") or ""),
                      texto=str(d.get("texto") or ""), grupo=str(d.get("grupo") or ""), n=int(d.get("n") or 0),
                      opcoes=[str(o) for o in d.get("opcoes") or []], antes=[str(a) for a in d.get("antes") or []])


def _herdar(novo: "TextoChave", antigo: "TextoChave") -> None:
    """O ID e as redações anteriores do texto-chave pareado; a redação de antes entra no histórico se mudou."""
    novo.id = antigo.id
    trocou = literal(antigo.texto) != literal(novo.texto)
    novo.antes = (list(antigo.antes) + ([antigo.texto] if trocou else []))[-5:]


# --------------------------------------------------------------------------- normalização
_ASPAS = "\"“”«»‘’'`"


#: Toda aspa vira a reta: a citação dentro do texto-chave vem com aspa simples no one-pager e dupla na copy («disse:
#: *'Eu só vi…'*» × «disse: "Eu só vi…"», Canal B da exp06ef1b) — é o mesmo texto.
_RE_ASPA = re.compile(r"[“”«»‘’']")


def literal(texto: str) -> str:
    """O texto para a comparação literal: espaços e aspas normalizados, a ênfase (`*`) e as aspas em volta tiradas — e
    só. Caixa, acento e pontuação contam: «Pronto» não é «pronto.»."""
    t = re.sub(r"<br\s*/?>", " ", (texto or "").replace("\u00a0", " ")).replace("*", "")
    t = re.sub(r"\s+", " ", t).strip()
    for _ in range(3):
        t = t.strip("_ ").strip(_ASPAS + " ")
    return _RE_ASPA.sub('"', t).strip()


def _documento_literal(texto: str) -> str:
    """O documento normalizado como `literal`, para procurar um texto-chave dentro dele. A ênfase só sai colada na aspa
    (`*"…"*`): a de uma palavra solta (`**Lugar**`) é o que separa o texto curto da frase em volta."""
    t = re.sub(r"<br\s*/?>", " ", (texto or "").replace("\u00a0", " "))
    t = _RE_ASPA.sub('"', t)
    t = re.sub(r"\*+(?=\")|(?<=\")\*+", "", t)
    return re.sub(r"\s+", " ", t)


#: O que no texto-chave é lacuna a preencher, e não texto: `[recorte da aula]`, `{motivo}`, `X%`, `___`, «estava…».
#: A copy que preenche a lacuna («para o passeio ao museu», «{motivo}», «68%») traz o texto-chave (exp05ef1b, exp01em1b).
_RE_LACUNA = re.compile(r"\[[^\]\n]{1,100}\]|\{[^}\n]{1,60}\}|\b[XYZN]\s?%|_{3,}|\.{3}|…")


def _padrao(texto: str) -> Optional["re.Pattern[str]"]:
    """O texto-chave com lacunas como expressão regular (cada lacuna aceita até 160 caracteres), ou None sem lacuna."""
    alvo = literal(texto)
    if not _RE_LACUNA.search(alvo):
        return None
    partes = _RE_LACUNA.split(alvo)
    return re.compile(r".{0,160}?".join(re.escape(p) for p in partes))


def mesmo_texto(aprovado: str, outro: str) -> bool:
    """O outro texto é o texto-chave, literal — ou o texto-chave com as lacunas dele preenchidas. O ponto final a mais ou
    a menos não conta: na string de tela ele é tipografia, e a proposta «Reforço Básico» → «Reforço Básico.» só faria
    ruído no cartão do PO (exp01em1b-76d9af6e)."""
    a, b = literal(aprovado), literal(outro)
    if a == b or a.rstrip(". ") == b.rstrip(". "):
        return True
    padrao = _padrao(aprovado)
    return bool(padrao and padrao.fullmatch(b))


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")


def _chave(texto: str) -> str:
    """Para a semelhança: sem caixa, sem acento, só palavras."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", _sem_acento(texto)).split())


def palavras(texto: str) -> int:
    return len(re.findall(r"[0-9A-Za-zÀ-ÿ]+(?:[-'][0-9A-Za-zÀ-ÿ]+)*", texto or ""))


def semelhanca(a: str, b: str) -> float:
    ka, kb = _chave(a), _chave(b)
    if not ka or not kb:
        return 0.0
    return difflib.SequenceMatcher(None, ka, kb, autojunk=False).ratio()


def corte(texto: str) -> float:
    """Semelhança mínima para outra redação ser uma reescrita do texto-chave, e não outro texto. A régua do
    `conteudo_aprovado.literais_parafraseados` (calibrada no PRD da exp06ef1b): abaixo de 30 caracteres, só o quase
    igual — «Galeria Oculta da Mostra» se parece com «Acessar Feed da Mostra» por acaso."""
    return 0.6 if len(_chave(texto)) >= 30 else 0.8


def _numeros(texto: str) -> List[str]:
    """Os números do texto, na ordem; o ponto de milhar não conta («R$ 12.000» é «R$ 12000»)."""
    return re.findall(r"\d+(?:,\d+)?", re.sub(r"(?<=\d)\.(?=\d{3}(?!\d))", "", texto or ""))


def mesmos_numeros(tc: "TextoChave", outro: str) -> bool:
    """O outro texto traz os números do texto-chave, na mesma ordem — ou o texto-chave tem lacuna (`X%`, `[…]`), que a
    copy preenche com o número dela. Para a semelhança, «1/3» e «2/3» são o mesmo texto; não são: na exp03em1b
    (24/10/2026) a cota «Publicações Oficiais Disponíveis: 1/3» da E4-ALU-04 virava «2/3» (o contador depois da 1ª
    publicação, outra tela), com proposta falsa ao PO, e a citação «…: 1/3» do PRD virava «3/3»."""
    return _padrao(tc.texto) is not None or _numeros(literal(tc.texto)) == _numeros(literal(outro))


def presente(tc: "TextoChave", documento_literal: str) -> bool:
    """O texto-chave está no documento (já normalizado por `_documento_literal`), literal. Texto de até três palavras
    («Lugar», «Cor da roupa») só conta entre aspas, crases, ênfase ou célula de tabela: a palavra solta aparece em
    qualquer frase."""
    alvo = literal(tc.texto)
    if not alvo:
        return True
    padrao = _padrao(tc.texto)
    if padrao is not None:
        return bool(padrao.search(documento_literal))
    if palavras(alvo) > 3:
        return alvo in documento_literal
    delim = r"[\"`*|]"
    return bool(re.search(rf"{delim}\s*{re.escape(alvo)}\s*[.!?]?\s*{delim}", documento_literal))


# --------------------------------------------------------------------------- extração
_Q = r"[\"“]([^\"”\n]{1,600})[\"”]"
_RE_Q = re.compile(_Q)
#: As opções de uma escolha escritas em lista: `a "Atividade", descartando "Cor da roupa" e "Lugar"`.
_RE_LISTA_DE_OPCOES = re.compile(
    rf"\*?{_Q}\*?(?:(?:\s*(?:,|;|·|/|\be\b|\bou\b|\bdescartando\b|\brejeitando\b|\bem\s+vez\s+de\b|\bcontra\b)\s*)+"
    rf"(?:(?:a|o|as|os)\s+)?\*?{_Q}\*?)+", re.I)
#: O que diz que o que vem depois são as opções de uma escolha do estudante.
_RE_VERBO_DE_ESCOLHA = re.compile(
    r"(?:\bselecion\w*|\bescolh\w*|\bop[çc](?:[ãa]o|[õo]es)\b|\balternativas?\b|\betiquetas?\b|\bentre\b|\bmarca\w*|"
    r"\btoca\w*\s+(?:em|n[oa]s?)\b|\bvota\w*|\bmotivo\b|\bpictogramas?\b|\bcart[õo]es\b|\bcards?\b|\bbot[õo]es\b)"
    r"[^\"“\n]{0,70}$", re.I)
#: Entre o verbo e a lista, isto diz que as aspas são fala, exemplo ou o que a tela não mostra, não opções: «os
#: comentários dizem: "…"» (exp03ef1b), «sem spoilers ou rótulos de "correto" ou "problemático"» (exp01em1b-76d9af6e).
_RE_FALA_NO_MEIO = re.compile(r"\bdiz(?:em)?\b|\bfala\w*|\bcomenta\w*|\bresponde\w*|\bmostra\w*|\bexibe\w*|\baparece\w*|"
                              r"\bex\.?\s*:|\bexemplo|\bsem\b|\bnunca\b|\bn[ãa]o\b", re.I)
#: Opções enumeradas: `(a) "…" … (b) "…"` (o motivo do aviso de cuidado da exp02em1b).
_RE_ENUMERADA = re.compile(rf"(?:^|[\s(])\(?([a-e]|[1-6])\)\s*\*?{_Q}", re.I)
#: A forma canônica que o núcleo escreve desde o PR 7: `**Opções (3):** "A" · "B" · "C"`.
_RE_OPCOES_CANONICAS = re.compile(r"\*{0,2}Op[çc][õo]es\s*(?:\(\s*\d+\s*\))?\s*\*{0,2}\s*:\s*\*{0,2}\s*(.+)$", re.I)


def _opcoes_da_linha(linha: str) -> List[str]:
    """As opções de uma escolha na linha do §4, ou nada. Calibrado nas 15 missões do acervo (`tests/acervo`): das listas
    entre aspas do §4, só as que vêm depois de um verbo de escolha sem fala no meio, as enumeradas e a forma canônica —
    de 0 a 2 escolhas por missão, e nenhuma lista de comentários («os comentários dizem: "…"», exp03ef1b) ou de horários
    (exp02em1b)."""
    m = _RE_OPCOES_CANONICAS.search(linha)
    if m and len(_RE_Q.findall(m.group(1))) >= 2:
        return [q.strip().strip("*").strip() for q in _RE_Q.findall(m.group(1))]
    enumeradas = _RE_ENUMERADA.findall(linha)
    if len(enumeradas) >= 2:
        return [q.strip().strip("*").strip() for _, q in enumeradas]
    for lista in _RE_LISTA_DE_OPCOES.finditer(linha):
        antes = linha[:lista.start()]
        verbo = _RE_VERBO_DE_ESCOLHA.search(antes)
        if not verbo or _RE_FALA_NO_MEIO.search(antes[verbo.start():]):
            continue
        itens = [q.strip().strip("*").strip() for q in _RE_Q.findall(lista.group(0))]
        if len(itens) >= 2 and all(palavras(i) <= 8 for i in itens):
            return itens
    return []


def escolhas_do_s4(one_pager: str) -> List[Tuple[str, List[str]]]:
    """`(etapa, opções)` das escolhas do §4 com as opções entre aspas."""
    from tools import conteudo_aprovado as ca

    saida: List[Tuple[str, List[str]]] = []
    for etapa, linha in ca.linhas_das_etapas(one_pager):
        if not linha or not linha.strip() or ca._RE_LINHA_ORAL.search(linha):
            continue
        opcoes = [o for o in _opcoes_da_linha(linha) if o]
        if len(opcoes) >= 2 and opcoes not in [o for _, o in saida]:
            saida.append((etapa, opcoes))
    return saida


_RE_NIVEL = re.compile(r"\b(?:Atingiu|Em\s+processo|N[ãa]o\s+atingiu)\b", re.I)
#: «Alt 1:», «Alternativa 1 [Atingiu]:» (exp03em1b), «A)», «(a)».
_RE_ROTULO_ALTERNATIVA = re.compile(
    r"^[\s\-—–•*]*\**\s*(?:Alt(?:ernativa)?\.?\s*\d+|[A-C]\)|\(?[a-c]\))\s*(?:\[[^\]\n]{1,20}\])?\s*\**\s*[:.\-—]?\s*\**",
    re.I)
_RE_ROTULO_NIVEL = re.compile(r"^[\s\-—–•*]*\**\s*(?:Atingiu|Em\s+processo|N[ãa]o\s+atingiu)\s*\**\s*:\s*\**", re.I)
_RE_PERGUNTA_ROTULO = re.compile(r"\bPergunta\b[^:\n]{0,80}:\**", re.I)
_RE_COMPONENTE = re.compile(r"^\W*\**\s*Componente", re.I)


def _texto_sem_rotulo(parte: str) -> str:
    """A alternativa ou a pergunta sem rótulo, sem o nível («`[Atingiu]`», «→ **Atingiu**») e sem a ênfase."""
    t = _RE_ROTULO_ALTERNATIVA.sub("", parte)
    t = _RE_ROTULO_NIVEL.sub("", t)
    t = re.sub(r"`?\[\s*(?:Atingiu|Em\s+processo|N[ãa]o\s+atingiu)\s*\]`?", " ", t, flags=re.I)
    t = re.sub(r"(?:→|->)\s*\**\s*(?:Atingiu|Em\s+processo|N[ãa]o\s+atingiu)\s*\**", " ", t, flags=re.I)
    # «- [Atingiu] Revela um engano: …» (exp06ef1b): o marcador da lista fica depois de tirar o nível
    return literal(re.sub(r"^[\s\-—–•*:]+", "", t))


def _ler_canal_b(texto: str) -> Tuple[str, List[str]]:
    """`(pergunta, alternativas)` do texto do Canal B de uma habilidade."""
    pergunta, alternativas, esperando = "", [], False
    for parte in [p for p in re.split(r"<br\s*/?>|\n", texto or "") if p.strip()]:
        s = parte.strip()
        if _RE_COMPONENTE.match(s):
            break
        citacoes = [q.strip().strip("*").strip() for q in _RE_Q.findall(s)]
        if not pergunta:
            com_interrogacao = [q for q in citacoes if q.rstrip().endswith("?")]
            rotulo = _RE_PERGUNTA_ROTULO.search(s)
            if com_interrogacao:
                pergunta = com_interrogacao[0]
            elif rotulo:
                resto = literal(s[rotulo.end():])
                if resto:
                    pergunta = citacoes[0] if citacoes else resto
                else:
                    esperando = True
            elif esperando:
                pergunta = citacoes[0] if citacoes else literal(s)
            continue
        if re.match(r"^\W*\**\s*Alternativas\s*:?\s*\**\s*$", s, re.I):
            continue
        if _RE_NIVEL.search(s) or _RE_ROTULO_ALTERNATIVA.match(s):
            texto_alt = citacoes[0] if citacoes else _texto_sem_rotulo(s)
            if texto_alt and texto_alt not in alternativas:
                alternativas.append(texto_alt)
    return pergunta, alternativas


def canal_b(one_pager: str) -> List[Tuple[str, str, List[str]]]:
    """`(habilidade, pergunta, alternativas)` de cada Canal B do §12a: a tabela de quatro colunas (a última é o Canal B)
    ou, sem tabela, cada trecho «Canal B» até o próximo título."""
    from tools import bncc
    from tools import conteudo_aprovado as ca

    s12 = ca.secao(one_pager or "", 12) or ""
    m = ca._RE_12A.search(s12)
    if not m:
        return []
    linhas = s12[m.start():].splitlines()
    saida: List[Tuple[str, str, List[str]]] = []
    for linha in linhas:
        s = linha.strip()
        if not s.startswith("|") or re.fullmatch(r"\|[\s:|-]+\|?", s):
            continue
        celulas = [c.strip() for c in re.split(r"(?<!\\)\|", s.strip("|"))]
        ultima = celulas[-1] if len(celulas) >= 2 else ""
        if not (re.search(r"Pergunta|\?", ultima) and (_RE_NIVEL.search(ultima) or _RE_ROTULO_ALTERNATIVA.search(ultima))):
            continue
        pergunta, alternativas = _ler_canal_b(ultima)
        if pergunta:
            codigos = bncc.extrair_codigos(celulas[0])
            saida.append((codigos[0] if codigos else "", pergunta, alternativas))
    if saida:
        return saida
    atual, bloco, habilidade = False, [], ""
    for linha in linhas + ["# fim"]:
        if re.match(r"^#{1,6}\s", linha):
            if atual and bloco:
                pergunta, alternativas = _ler_canal_b("\n".join(bloco))
                if pergunta:
                    saida.append((habilidade, pergunta, alternativas))
            atual, bloco = False, []
            codigos = bncc.extrair_codigos(linha)
            habilidade = codigos[0] if codigos else habilidade
            continue
        if re.search(r"Canal\s*B", linha):
            atual = True
        if atual:
            bloco.append(linha)
    return saida


def extrair(one_pager: str) -> List[TextoChave]:
    """Os textos-chave do one-pager, sem ID, na ordem: §4 (textos de tela e escolhas, por etapa), §12a (pergunta e
    alternativas do Canal B), §9 (roteiro do professor) e §11 (podcast). O mesmo texto em duas fontes entra uma vez, na
    primeira; a opção de uma escolha não entra de novo como texto de tela."""
    from tools import conteudo_aprovado as ca

    escolhas = escolhas_do_s4(one_pager)
    canais = canal_b(one_pager)
    das_escolhas = {literal(o) for _, ops in escolhas for o in ops} | {literal(a) for _, _, alts in canais for a in alts}
    saida: List[TextoChave] = []
    vistos: Set[str] = set()

    def novo(tipo: str, origem: str, texto: str) -> None:
        chave = literal(texto)
        if chave and chave not in vistos:
            vistos.add(chave)
            saida.append(TextoChave(id="", tipo=tipo, origem=origem, texto=texto.strip()))

    def escolha(origem: str, opcoes: Sequence[str]) -> None:
        opcoes = [o.strip() for o in opcoes if literal(o)]
        if len(opcoes) >= 2:
            saida.append(TextoChave(id="", tipo=OPCOES, origem=origem, texto=" · ".join(f"«{o}»" for o in opcoes),
                                    n=len(opcoes), opcoes=list(opcoes)))
            vistos.update(literal(o) for o in opcoes)

    por_etapa: Dict[str, List[Tuple[str, Any]]] = {}
    for etapa, texto in ca.textos_de_tela_por_etapa(one_pager):
        if literal(texto) not in das_escolhas:
            por_etapa.setdefault(etapa, []).append((TELA, texto))
    for etapa, ops in escolhas:
        por_etapa.setdefault(etapa, []).append((OPCOES, ops))
    for etapa, itens in por_etapa.items():
        for tipo, valor in itens:
            if tipo == TELA:
                novo(TELA, f"§4 · Etapa {etapa}", valor)
            else:
                escolha(f"§4 · Etapa {etapa}", valor)
    for habilidade, pergunta, alternativas in canais:
        origem = "§12a" + (f" · {habilidade}" if habilidade else "")
        novo(CANAL_B, origem, pergunta)
        escolha(origem, alternativas)
    lit = ca.literais(one_pager)
    for t in lit.get("roteiro") or []:
        novo(ROTEIRO, "§9", t)
    for t in lit.get("podcast") or []:
        novo(PODCAST, "§11", t)
    return saida


# --------------------------------------------------------------------------- IDs
def _numeros_usados(itens: Iterable[Dict[str, Any]]) -> int:
    return max([partes_do_id(str(d.get("id") or ""))[0] for d in itens] or [0])


def _parear(novos: List[TextoChave], antigos: List[TextoChave]) -> Dict[int, TextoChave]:
    """`{índice do novo: antigo}`. Primeiro o texto igual (no mesmo tipo); depois, por tipo e origem, o que sobrou na
    mesma posição — é o texto que o PO trocou (exp02ef1b: a resposta da Visita na E4 foi reescrita inteira em 23/10); com
    contagens diferentes na origem, só o parecido."""
    def chave(tc: TextoChave) -> str:
        return " | ".join(literal(o) for o in tc.opcoes) if tc.tipo == OPCOES else literal(tc.texto)

    pares: Dict[int, TextoChave] = {}
    livres = list(antigos)
    for i, tc in enumerate(novos):
        igual = next((a for a in livres if a.tipo == tc.tipo and chave(a) == chave(tc)), None)
        if igual is not None:
            pares[i] = igual
            livres.remove(igual)
    baldes: Dict[Tuple[str, str], List[int]] = {}
    for i, tc in enumerate(novos):
        if i not in pares:
            baldes.setdefault((tc.tipo, tc.origem), []).append(i)
    for (tipo, origem), indices in baldes.items():
        sobra = [a for a in livres if a.tipo == tipo and a.origem == origem]
        if not sobra:
            continue
        if len(sobra) == len(indices):
            for i, a in zip(indices, sobra):
                pares[i] = a
                livres.remove(a)
            continue
        for i in indices:
            melhor = max(sobra, key=lambda a: semelhanca(chave(a), chave(novos[i])), default=None)
            if melhor is not None and semelhanca(chave(melhor), chave(novos[i])) >= 0.5:
                pares[i] = melhor
                livres.remove(melhor)
                sobra.remove(melhor)
    return pares


def numerar(extraidos: Sequence[TextoChave], anteriores: Optional[Dict[str, Any]] = None
            ) -> Tuple[List[TextoChave], List[Dict[str, Any]]]:
    """`(textos-chave com ID, aposentados)`. `anteriores` é o registro (`{"itens": […], "aposentados": […]}`): quem tinha
    ID o guarda; o novo ganha o próximo número; o que saiu entra nos aposentados, e o número não volta."""
    registro = anteriores or {}
    itens_ant = [de_dict(d) for d in registro.get("itens") or [] if isinstance(d, dict)]
    aposentados = [dict(d) for d in registro.get("aposentados") or [] if isinstance(d, dict)]
    topo_ant = [t for t in itens_ant if t.tipo != OPCAO]
    proximo = max(_numeros_usados(t.como_dict() for t in itens_ant), _numeros_usados(aposentados)) + 1
    novos = [TextoChave(**{**t.como_dict(), "opcoes": list(t.opcoes)}) for t in extraidos if t.tipo != OPCAO]
    pares = _parear(novos, topo_ant)
    saida: List[TextoChave] = []
    for i, tc in enumerate(novos):
        antigo = pares.get(i)
        if antigo is not None:
            _herdar(tc, antigo)
        else:
            tc.id = formatar_id(proximo)
            proximo += 1
        saida.append(tc)
        if tc.tipo == OPCOES:
            saida += _opcoes_numeradas(tc, [t for t in itens_ant if t.tipo == OPCAO and t.grupo == tc.id],
                                       aposentados)
    usados = {t.id for t in saida}
    for a in itens_ant:
        if a.id not in usados and not any(d.get("id") == a.id for d in aposentados):
            aposentados.append({"id": a.id, "tipo": a.tipo, "origem": a.origem, "texto": a.texto})
    return saida, aposentados


def _opcoes_numeradas(grupo: TextoChave, antigas: List[TextoChave], aposentados: List[Dict[str, Any]]
                      ) -> List[TextoChave]:
    novas = [TextoChave(id="", tipo=OPCAO, origem=grupo.origem, texto=o, grupo=grupo.id) for o in grupo.opcoes]
    pares = _parear(novas, antigas)
    usados_sub = [partes_do_id(a.id)[1] for a in antigas] + [
        partes_do_id(str(d.get("id") or ""))[1] for d in aposentados if str(d.get("id") or "").startswith(grupo.id + ".")]
    proximo = max(usados_sub or [0]) + 1
    numero = partes_do_id(grupo.id)[0]
    for i, op in enumerate(novas):
        if i in pares:
            _herdar(op, pares[i])
        else:
            op.id = formatar_id(numero, proximo)
            proximo += 1
    return novas


# --------------------------------------------------------------------------- registro e tabela
def _celulas(linha: str) -> List[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", linha.strip().strip("|"))]


def ler_tabela(texto: str) -> List[Dict[str, Any]]:
    """Os textos-chave de uma tabela «Textos-chave» escrita no texto (a do PO, no one-pager dele): `[{id, tipo, origem,
    texto}]`. A escolha é refeita pelas opções (`TC-nn.k`). Sem a seção, vazio."""
    m = re.search(r"^(#{1,6})\s*[^\n]*textos?-chave[^\n]*$", texto or "", re.I | re.M)
    if not m:
        return []
    nivel = len(m.group(1))
    fim = re.search(rf"^#{{1,{nivel}}}\s", texto[m.end():], re.M)
    trecho = texto[m.end(): m.end() + fim.start()] if fim else texto[m.end():]
    itens: List[Dict[str, Any]] = []
    cabecalho: List[str] = []
    for linha in trecho.splitlines():
        if not linha.strip().startswith("|") or _e_separador(linha.strip()):
            continue
        celulas = _celulas(linha)
        ids = ids_citados(celulas[0]) if celulas else []
        if not ids:
            cabecalho = [c.lower().strip("*_ `") for c in celulas]
            continue
        if len(celulas) < 2:
            continue
        ident = ids[0]
        tipo_txt = next((c for c in celulas[1:] if c.lower().strip("*_ ") in _TIPO_DO_ROTULO
                         or c.lower().startswith("escolha")), "")
        tipo = _TIPO_DO_ROTULO.get(tipo_txt.lower().strip("*_ "), OPCOES if tipo_txt.lower().startswith("escolha") else "")
        origem = next((c for c in celulas[1:] if c.startswith("§")), "")
        itexto = next((k for k, c in enumerate(cabecalho) if c.startswith("texto")), None)
        if itexto is not None and itexto < len(celulas):
            texto_cel = celulas[itexto]
        else:
            texto_cel = next((c for c in celulas[1:] if "«" in c), "") or max(
                (c for c in celulas[1:] if c not in (origem, tipo_txt)), key=len, default="")
        num, sub = partes_do_id(ident)
        if sub:
            tipo = OPCAO
        itens.append({"id": ident, "tipo": tipo or TELA, "origem": origem, "texto": literal(texto_cel),
                      "grupo": formatar_id(num) if sub else ""})
    grupos: Dict[str, List[str]] = {}
    for d in itens:
        if d["tipo"] == OPCAO:
            grupos.setdefault(d["grupo"], []).append(d["texto"])
    for d in itens:
        if d["id"] in grupos:
            d.update({"tipo": OPCOES, "opcoes": grupos[d["id"]], "n": len(grupos[d["id"]])})
    return itens


def registro(estado: Dict[str, Any]) -> Dict[str, Any]:
    """O registro de IDs da sessão: o que a esteira gravou (`textos_chave`), ou a tabela que o PO escreveu no one-pager
    (dele ou o gerado), ou nada — a sessão anterior ao PR 7."""
    gravado = estado.get(KEY_REGISTRO)
    if isinstance(gravado, dict) and gravado.get("itens"):
        return gravado
    for chave in ("one_pager", "one_pager_po"):
        itens = ler_tabela(str(estado.get(chave) or ""))
        if itens:
            return {"itens": itens, "aposentados": [], "origem": chave}
    # a sessão anterior ao PR 7 numa correção ou num refazer de produto: os IDs saem do one-pager de antes do pedido
    # (`versao_anterior_one_pager`), e o texto que o PO trocou guarda o ID e a redação velha — sem isto, a linha da copy
    # com a redação velha não tinha como receber a nova (a cascata das quatro missões refeitas depois do PR 7)
    anterior = str(estado.get("versao_anterior_one_pager") or "")
    if anterior.strip():
        itens, _ = numerar(extrair(anterior))
        if itens:
            return {"itens": [t.como_dict() for t in itens], "aposentados": [], "origem": "versao_anterior_one_pager"}
    return {"itens": [], "aposentados": []}


def da_sessao(estado: Dict[str, Any]) -> List[TextoChave]:
    """Os textos-chave da sessão, do one-pager de agora, com os IDs do registro. Só leitura: na sessão anterior ao PR 7
    os IDs saem na ordem das seções, e nada é gravado."""
    return numerar(extrair(str(estado.get("one_pager") or "")), registro(estado))[0]


def atualizar(estado: Dict[str, Any]) -> Tuple[List[TextoChave], Dict[str, Any]]:
    """`(textos-chave, registro novo)` — o que o A044b grava no fim de produto e a cópia da copy grava se a sessão não
    tinha registro."""
    anterior = registro(estado)
    tcs, aposentados = numerar(extrair(str(estado.get("one_pager") or "")), anterior)
    return tcs, {"versao": 1, "itens": [t.como_dict() for t in tcs], "aposentados": aposentados}


def por_id(tcs: Iterable[TextoChave]) -> Dict[str, TextoChave]:
    return {t.id: t for t in tcs}


def _celula(texto: str) -> str:
    return (texto or "").replace("|", "\\|").replace("\n", " ")


def tabela(tcs: Sequence[TextoChave], teto: Optional[Dict[str, Any]] = None, aposentados: Sequence[Dict[str, Any]] = ()
           ) -> str:
    """A tabela dos textos-chave em Markdown, para o cartão do de acordo, o artefato e o conteúdo aprovado."""
    if not tcs:
        return ""
    linhas = [f"## {TITULO_TABELA}", "",
              "> Montada pela esteira, por código, do one-pager aprovado (§4, §12a, §9, §11). O ID é estável: o texto "
              "trocado no mesmo lugar guarda o ID, e o que sai do one-pager não volta a usá-lo. Cada texto é copiado "
              "palavra por palavra, por código, para a copy e para onde o handoff, o PRD e o pedagógico o citam; o "
              "design não o reescreve — mudança é `[PROPOSTA — validar com PO]`, e o PO a pede no Refazer (a triagem leva "
              "o item a Produto). Microcopy (rótulos, avisos, estados de tela) é do design e não está aqui.", ""]
    limite = (teto or {}).get("valor")
    linhas += ["| ID | Tipo | Origem | Texto aprovado | Palavras |", "|---|---|---|---|---|"]
    for t in tcs:
        if t.tipo == OPCOES:
            linhas.append(f"| `{t.id}` | escolha · {t.n} opções | {t.origem} | {_celula(t.texto)} | — |")
            continue
        n = palavras(t.texto)
        marca = ""
        if limite and t.tipo in TIPOS_LIDOS_PELA_CRIANCA and contar_para_o_teto(t.texto, teto) > limite:
            marca = f" ⚠️ teto {limite}"
        linhas.append(f"| `{t.id}` | {ROTULO_TIPO.get(t.tipo, t.tipo)} | {t.origem} | «{_celula(t.texto)}» | {n}{marca} |")
    if aposentados:
        linhas += ["", "Saíram do one-pager (o ID não volta): " + "; ".join(
            f"`{d.get('id')}` «{str(d.get('texto') or '')[:60]}»" for d in aposentados[-12:])]
    return "\n".join(linhas) + "\n"


# --------------------------------------------------------------------------- teto de palavras (lint de produto)
#: Onde a tabela de tetos por faixa mora: rascunho para o usuário validar (o repo não tinha teto por faixa — só a
#: calibragem por frase da copy, `073_copy_ptbr.md`, e a cláusula de defasagem do critério 6.1).
REFERENCIA_TETOS = "teto-palavras-por-faixa.md"
_RE_SLUG = re.compile(r"\bexp(\d{2})(ef|em)\d+b\b", re.I)


def faixa(*textos: str) -> str:
    """`1-2`, `3-5`, `6-9` ou `EM`, do slug da missão (`exp02ef1b` → 2º ano) ou da série declarada."""
    from tools.bncc import extrair_serie

    for texto in textos:
        m = _RE_SLUG.search(texto or "")
        if m:
            numero, etapa = int(m.group(1)), m.group(2).lower()
            if etapa == "em":
                return "EM"
            return "1-2" if numero <= 2 else "3-5" if numero <= 5 else "6-9"
    for texto in textos:
        serie = extrair_serie(texto or "")
        if serie.get("anos"):
            ano = min(serie["anos"])
            return "1-2" if ano <= 2 else "3-5" if ano <= 5 else "6-9"
        if serie.get("em"):
            return "EM"
    return ""


def tetos_por_faixa(raiz: Optional[Path] = None) -> Tuple[Dict[str, int], str]:
    """`({faixa: teto}, status)` da referência `prompts/references/teto-palavras-por-faixa.md`."""
    caminho = (raiz or Path(__file__).resolve().parent.parent) / "prompts" / "references" / REFERENCIA_TETOS
    try:
        texto = caminho.read_text(encoding="utf-8")
    except OSError:
        return {}, ""
    status = (re.search(r"^status:\s*(.+)$", texto, re.M) or [None, ""])[1].strip()
    tetos = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\|\s*`([0-9EM-]+)`\s*\|[^|\n]*\|\s*(\d+)\s*\|", texto, re.M)}
    return tetos, status


#: Número que a linha do §15 declara como teto de palavras: «35 palavras por balão», «no máximo 45 palavras». Na faixa
#: («8 a 10 palavras», exp03ef1b; «40 a 50 palavras», exp07ef1b), o teto é o limite de cima (grupo 2).
_RE_TETO_PALAVRAS = re.compile(r"(?<![\d.,])(\d{1,3})\s*(?:(?:a|até|-|–)\s*(\d{1,3})\s*)?palavras?\b", re.I)
_RE_MARCADOR_ABERTO = re.compile(r"\[(?:PAR[ÂA]METRO|PROPOSTA|ABERTO|DECIS[ÃA]O PENDENTE)[^\]]*\]", re.I)


def teto_do_one_pager(one_pager: str) -> Optional[Tuple[int, str]]:
    """`(teto, linha)` de palavras que o §15 aprovado declara para os textos da tela. Com vários («legendas 60, cartões
    25, balões 35», exp06ef1b), o maior — o lint não sabe a que tipo de texto cada texto-chave pertence, e o maior não
    acusa texto que outro teto permitiria. O número dentro de `[PARÂMETRO]`/`[PROPOSTA]` não é teto aprovado, e zero
    («0 palavras de leitura autônoma», exp01ef1b) é ausência de leitura, não teto."""
    from tools.conteudo_aprovado import secao

    candidatos: List[Tuple[int, str]] = []
    for linha in (secao(one_pager or "", 15) or "").splitlines():
        if not re.search(r"palavra", linha, re.I) or re.search(r"caracter", linha, re.I):
            continue
        limpa = _RE_MARCADOR_ABERTO.sub(" ", linha)
        for m in _RE_TETO_PALAVRAS.finditer(limpa):
            n = int(m.group(2) or m.group(1))
            if n > 0:
                candidatos.append((n, linha.strip()))
    return max(candidatos, key=lambda c: c[0]) if candidatos else None


def teto_de_palavras(one_pager: str, *outros: str, raiz: Optional[Path] = None) -> Dict[str, Any]:
    """O teto de palavras que vale para os textos-chave lidos pela criança: o do §15 do one-pager aprovado, por texto
    (é o que o PO aprovou para a missão); sem ele, o da faixa, por frase (`teto-palavras-por-faixa.md`, rascunho).
    `{}` quando nenhum dos dois existe."""
    do_one_pager = teto_do_one_pager(one_pager)
    if do_one_pager:
        return {"valor": do_one_pager[0], "por": "texto", "origem": "§15 do one-pager aprovado",
                "linha": do_one_pager[1]}
    f = faixa(one_pager, *outros)
    tetos, status = tetos_por_faixa(raiz)
    if f and f in tetos:
        return {"valor": tetos[f], "por": "frase", "faixa": f,
                "origem": f"`references/{REFERENCIA_TETOS}`, faixa {f}" + (f" ({status})" if status else "")}
    return {}


def contar_para_o_teto(texto: str, teto: Optional[Dict[str, Any]]) -> int:
    """As palavras que o teto conta: o texto inteiro (teto do §15, por texto) ou a frase mais longa (teto da faixa)."""
    if (teto or {}).get("por") == "frase":
        frases = [f for f in re.split(r"(?<=[.!?…])\s+", texto or "") if f.strip()]
        return max((palavras(f) for f in frases), default=0)
    return palavras(texto)


#: O tipo do item do de acordo (PR 3) que o texto-chave acima do teto vira.
TIPO_DECISAO_TETO = "texto_teto"


def decididos_acima_do_teto(decisoes_do_po: Optional[Sequence[Dict[str, Any]]]) -> Set[str]:
    """Os textos que o PO decidiu no de acordo — o que ele manteve acima do teto e o que ele mesmo escreveu no lugar —,
    pelo texto normalizado: não voltam ao cartão nem ao lint."""
    saida: Set[str] = set()
    for d in decisoes_do_po or []:
        if isinstance(d, dict) and d.get("tipo") == TIPO_DECISAO_TETO and d.get("resposta") in ("aceitar", "outro"):
            saida.add(literal(str(d.get("texto") or "")))
    return saida


def acima_do_teto(tcs: Sequence[TextoChave], teto: Optional[Dict[str, Any]],
                  decisoes_do_po: Optional[Sequence[Dict[str, Any]]] = None) -> List[Tuple[TextoChave, int]]:
    """`(texto-chave, palavras)` dos textos lidos pela criança acima do teto, menos os que o PO já manteve."""
    limite = (teto or {}).get("valor")
    if not limite:
        return []
    mantidos = decididos_acima_do_teto(decisoes_do_po)
    saida = []
    for t in tcs:
        if t.tipo not in TIPOS_LIDOS_PELA_CRIANCA or literal(t.texto) in mantidos:
            continue
        n = contar_para_o_teto(t.texto, teto)
        if n > limite:
            saida.append((t, n))
    return saida


# --------------------------------------------------------------------------- copy (design)
_RE_SEPARADOR = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")


def _e_separador(linha: str) -> bool:
    return bool(_RE_SEPARADOR.match(linha or "")) and "-" in (linha or "")


def _linhas_de_tabela(linhas: Sequence[str]) -> Iterable[Tuple[int, List[str], List[str]]]:
    """`(índice, células, cabeçalho)` de cada linha de dados das tabelas do texto."""
    cabecalho: Optional[List[str]] = None
    for i, linha in enumerate(linhas):
        s = linha.strip()
        if not s.startswith("|"):
            cabecalho = None
            continue
        if _e_separador(s):
            continue
        if i + 1 < len(linhas) and _e_separador(linhas[i + 1].strip()):
            cabecalho = [c.lower() for c in _celulas(s)]
            continue
        if cabecalho is not None:
            yield i, _celulas(s), cabecalho


def _coluna(cabecalho: Sequence[str], *prefixos: str) -> Optional[int]:
    for i, c in enumerate(cabecalho):
        if any(c.strip("*_ `").startswith(p) for p in prefixos):
            return i
    return None


def remover_secao(texto: str, titulo: str = TITULO_SECAO_COPY) -> str:
    """O texto sem a seção da esteira (em qualquer nível de título), até o próximo título de nível igual ou maior."""
    m = re.search(rf"^(#{{1,6}})\s*{re.escape(titulo)}\s*$", texto or "", re.M)
    if not m:
        return texto or ""
    nivel = len(m.group(1))
    fim = re.search(rf"^#{{1,{nivel}}}\s", texto[m.end():], re.M)
    corpo = texto[: m.start()].rstrip()
    resto = texto[m.end() + fim.start():] if fim else ""
    return (corpo + ("\n\n" + resto.lstrip() if resto.strip() else "")).rstrip() + "\n"


_RE_MARCADOR_PROPOSTA = re.compile(r"\[PROPOSTA\s*[—–-]\s*validar com PO\s*:", re.I)
#: O par «aprovado» → «proposto» dentro da proposta: com aspas angulares (o formato da esteira e dos prompts) ou, sem
#: elas, com aspas duplas.
_RE_PAR_ANGULAR = re.compile(r"«([^»\n]+)»\s*(?:→|->)\s*«([^»\n]+)»")
_RE_PAR_DUPLAS = re.compile(r"[\"“]([^\"”\n]+)[\"”]\s*(?:→|->)\s*[\"“]([^\"”\n]+)[\"”]")


def propostas_registradas(texto: str) -> List[Tuple[str, str, str]]:
    """`(ID, aprovado, proposto)` de cada `[PROPOSTA — validar com PO: …]` da copy que nomeia um texto-chave: as da
    seção da esteira (`TC-07 «aprovado» → «proposto»`) e as que o design escreve em «Strings que precisam de decisão»,
    com o ID antes ou depois do par (`«aprovado» → «proposto» · TC-07 · por quê`, o formato que os prompts 073 e 077
    pediam até 24/10/2026 — sem esta leitura, a proposta do design não chegava ao 🧑 do gate)."""
    saida: List[Tuple[str, str, str]] = []
    for linha in (texto or "").splitlines():
        marcas = list(_RE_MARCADOR_PROPOSTA.finditer(linha))
        for k, m in enumerate(marcas):
            trecho = linha[m.end(): marcas[k + 1].start() if k + 1 < len(marcas) else len(linha)]
            par = _RE_PAR_ANGULAR.search(trecho) or _RE_PAR_DUPLAS.search(trecho)
            if not par:
                continue
            ids = ids_citados(trecho[: par.start()] + " " + trecho[par.end():])
            item = (ids[0], par.group(1).strip(), par.group(2).strip()) if ids else None
            if item and (item[0], literal(item[2])) not in {(i, literal(p)) for i, _, p in saida}:
                saida.append(item)
    return saida


#: Onde a copy com as propostas do design está: a revisada; a da execução anterior, quando o passo de produto da cascata
#: já a apagou do estado (`pipeline/reexecucao.py`, `versao_anterior_<chave>`); a da passada 1.
_CHAVES_DA_COPY = ("copy_strings_revisada", "versao_anterior_copy_strings_revisada", "copy_strings")
TITULO_CITADOS = "Textos-chave citados no pedido"


def citados_no_pedido(pedido: str, estado: Dict[str, Any]) -> str:
    """Os textos-chave que o pedido cita pelo ID, expandidos por código: a linha da tabela (ID, tipo, origem, texto
    aprovado, as redações aprovadas antes) e as propostas do design registradas na copy para o ID. Vazio quando o pedido
    não cita ID.

    O ID não está em nenhum documento de produto (a tabela vive ao lado do one-pager): o PO que escreve no Refazer só
    «aceito a proposta TC-02» manda a produto um item que o editor pontual não sabia a que texto se referia — não trocava
    nada, e a cascata acabava em Devolver (revisão do PR 7, 24/10/2026, exp02ef1b)."""
    citados = list(dict.fromkeys(ids_citados(pedido)))
    if not citados:
        return ""
    tcs = da_sessao(estado)
    tabela_ = por_id(tcs)
    aposentados = {str(d.get("id") or ""): d for d in registro(estado).get("aposentados") or [] if isinstance(d, dict)}
    copy = next((str(estado.get(k)) for k in _CHAVES_DA_COPY if str(estado.get(k) or "").strip()), "")
    propostas = propostas_registradas(copy)
    linhas = [f"### {TITULO_CITADOS}", "",
              "O pedido cita textos-chave pelo ID. O ID não aparece no núcleo, no one-pager, no resumido nem na spec: "
              "procure pelo **texto aprovado**. Aceitar uma proposta é trocar o texto aprovado pelo texto proposto, letra "
              "por letra, em todo lugar onde ele está. Expandidos pela esteira, da tabela do one-pager aprovado e das "
              "propostas do design registradas na copy:", ""]
    for ident in citados:
        tc = tabela_.get(ident)
        if tc is None:
            velho = aposentados.get(ident)
            linhas.append(f"- `{ident}` — não está na tabela do one-pager aprovado"
                          + (f" (saiu do one-pager; o último texto era «{velho.get('texto')}»)" if velho else
                             " (ID desconhecido)") + ": não há texto aprovado com este ID.")
            continue
        if tc.tipo == OPCOES:
            linhas.append(f"- `{tc.id}` — escolha com {tc.n} opções ({tc.origem}): "
                          + " · ".join(f"`{o.id}` «{o.texto}»" for o in tcs if o.tipo == OPCAO and o.grupo == tc.id))
        else:
            grupo = tabela_.get(tc.grupo) if tc.grupo else None
            linhas.append(f"- `{tc.id}` — {ROTULO_TIPO.get(tc.tipo, tc.tipo)} ({tc.origem}"
                          + (f", opção da escolha `{grupo.id}`: {grupo.texto}" if grupo else "")
                          + f") — texto aprovado: «{tc.texto}»")
        if tc.antes:
            linhas.append("  - redações aprovadas antes: " + " · ".join(f"«{a}»" for a in tc.antes))
        doid = [(i, a, p) for i, a, p in propostas if i == tc.id or (tc.tipo == OPCOES and i.startswith(tc.id + "."))]
        for i, aprovado, proposto in doid:
            ja = " (já é o texto aprovado)" if mesmo_texto(tabela_[i].texto if i in tabela_ else "", proposto) else ""
            linhas.append(f"  - proposta do design registrada na copy (`{i}`): «{aprovado}» → «{proposto}»{ja}")
        if not doid:
            linhas.append("  - nenhuma proposta do design registrada na copy para este ID")
    return "\n".join(linhas)


def _candidatos(linhas: Sequence[str], ocupadas: Set[int]) -> List[Tuple[int, str]]:
    """`(linha, trecho)` onde uma reescrita de texto-chave pode estar: célula de tabela, texto entre aspas e a fala depois
    de um rótulo (`**Clara:** …`)."""
    saida: List[Tuple[int, str]] = []
    cerca = False
    for i, linha in enumerate(linhas):
        if re.match(r"^\s*(```|~~~)", linha):
            cerca = not cerca
            continue
        if cerca or i in ocupadas or _RE_MARCADOR_PROPOSTA.search(linha):
            continue  # a proposta ao PO cita a outra redação de propósito: não é string de tela a corrigir
        s = linha.strip()
        if s.startswith("|") and not _e_separador(s):
            saida += [(i, c) for c in _celulas(s) if palavras(c) >= 2]
        saida += [(i, q) for q in _RE_Q.findall(linha) if palavras(q) >= 2]
        m = re.match(r"^\s*(?:[-*]\s+)?\*\*[^*\n]{2,30}?:\*\*\s*(.{8,})$", linha)
        if m:
            saida.append((i, m.group(1).strip()))
    return saida


#: A célula já traz o texto-chave (com moldura em volta, ou as lacunas preenchidas): nada a trocar.
_JA_ESTA = "\x00já está"


def _trecho_do_texto_chave(tc: "TextoChave", celula: str) -> Optional[str]:
    """Na linha que cita o ID, o trecho da célula PT-BR que é o texto-chave: a célula que traz o texto-chave inteiro com
    moldura em volta já o traz (devolve ele mesmo, e nada muda); senão, a reescrita mais parecida dentro dela, se passa
    da régua; senão, a célula inteira — o ID diz que a linha é dele («Pronto» no lugar do texto aprovado)."""
    if presente(tc, _documento_literal(celula)):
        return _JA_ESTA
    trechos = [t for t in _trechos_da_celula(celula) if t != celula]
    achado = _melhor(tc, [(0, t) for t in trechos])
    return achado[1] if achado else None


def _trechos_da_celula(celula: str) -> List[str]:
    """Onde a reescrita pode estar numa célula PT-BR: a célula inteira, o texto entre aspas dela e, com a aspa que abre e
    não fecha, o resto depois dela («Nico investigou no livro didático: "O objetivo…», exp02em1b)."""
    trechos = [celula]
    trechos += [q for q in _RE_Q.findall(celula) if palavras(q) >= 2]
    abre = re.search(r"[:—–-]\s*[\"“]", celula)
    if abre and celula.count('"') + celula.count("“") + celula.count("”") == 1:
        resto = celula[abre.end():].strip()
        if palavras(resto) >= 2:
            trechos.append(resto)
    return list(dict.fromkeys(trechos))


_PALAVRAS_DE_LIGACAO = frozenset("a o as os um uma uns umas de da do das dos pela pelo e".split())


def _cita_inteiro(ka: str, kb: str) -> bool:
    """O trecho traz o texto-chave inteiro e mais palavra de conteúdo: é outro texto que o cita («Detetive da Foto
    Oficial»). Só artigo a mais («A atividade» × «Atividade», o pedido do PO de 23/10 na exp02ef1b) é reescrita."""
    if ka == kb or f" {ka} " not in f" {kb} ":
        return False
    resto = f" {kb} ".replace(f" {ka} ", " ", 1).split()
    return any(p not in _PALAVRAS_DE_LIGACAO for p in resto)


def _melhor(tc: TextoChave, candidatos: Sequence[Tuple[int, str]]) -> Optional[Tuple[int, str, float]]:
    """A reescrita mais parecida com o texto-chave, se passa da régua. Texto de até seis palavras precisa, além da
    semelhança, de metade das palavras em comum: «Iniciar Auditoria no Assistente» não é reescrita de «Liberar
    Auditoria dos Cadernos (Gate E4)» (exp09ef1b). O trecho que contém o texto-chave inteiro («Detetive da Foto
    Oficial», exp01ef1b) é outro texto que o cita, não reescrita."""
    alvo = literal(tc.texto)
    melhor: Optional[Tuple[int, str, float]] = None
    ka = _chave(alvo)
    palavras_a = set(ka.split())
    curto = len(palavras_a) <= 6
    for i, trecho in candidatos:
        kb = _chave(trecho)
        if not kb or not (0.5 <= len(kb) / max(1, len(ka)) <= 2.0) or _cita_inteiro(ka, kb):
            continue
        if not mesmos_numeros(tc, trecho):
            continue  # outro número é outro texto («…: 1/3» × «…: 2/3», exp03em1b)
        if curto:
            palavras_b = set(kb.split())
            if len(palavras_a & palavras_b) * 2 < len(palavras_a | palavras_b):
                continue
        r = difflib.SequenceMatcher(None, ka, kb, autojunk=False)
        if r.quick_ratio() < corte(alvo):
            continue
        valor = r.ratio()
        if valor >= corte(alvo) and (melhor is None or valor > melhor[2]):
            melhor = (i, trecho, valor)
    return melhor


def _trocar_trecho(linha: str, trecho: str, novo: str) -> str:
    """Troca o trecho pelo texto aprovado, na linha. Célula inteira de tabela: a célula; senão, a primeira ocorrência."""
    if linha.strip().startswith("|"):
        celulas = _celulas(linha)
        for k, c in enumerate(celulas):
            if c == trecho:
                fecha = {"“": "”", "«": "»", '"': '"'}.get(c[:1], "")
                celulas[k] = f"{c[:1]}{novo}{fecha}" if fecha else novo
                return "| " + " | ".join(celulas) + " |"
    return linha.replace(trecho, novo, 1)


def aplicar_na_copy(copy: str, tcs: Sequence[TextoChave], anotar_sem_troca: bool = True) -> Dict[str, Any]:
    """Copia por código os textos-chave para a copy. Pura.

    - A linha da tabela de strings que cita o ID (`TC-07`, em qualquer coluna) ou que traz o próprio texto recebe o texto
      aprovado na coluna PT-BR, e a contagem de palavras. A redação que estava lá, se era outra, vira proposta. O ID vai
      para a coluna de notas da linha ligada pelo texto — menos, com `anotar_sem_troca=False` (a correção pontual), na
      linha que já trazia o texto aprovado: ali a copy é a versão anterior mais as trocas, e a nota mudava de 14 a 64
      linhas por missão sem trocar texto nenhum (exp03em1b, exp02em1b, exp01em1b-76d9af6e, exp02ef1b; 24/10/2026).
    - O texto-chave que nenhuma linha cita e que não está literal na copy, mas tem uma reescrita (célula, texto entre
      aspas, fala do podcast) com a semelhança da régua da paráfrase, tem a reescrita trocada pelo aprovado — e a
      reescrita vira proposta. Sem reescrita, ele vai à lista dos sem linha, na seção da esteira.
    - A seção da esteira (`TITULO_SECAO_COPY`) é refeita no fim, com as propostas — as de uma execução anterior ficam,
      enquanto o texto-chave existir e a proposta for diferente dele — e os sem linha.

    Devolve `{texto, propostas_novas, propostas, sem_linha, opcoes_divergentes, ids_desconhecidos, copiados}`.
    """
    tcs = list(tcs)
    if not (copy or "").strip() or not tcs:
        return {"texto": copy or "", "propostas_novas": [], "propostas": [], "sem_linha": [], "opcoes_divergentes": [],
                "ids_desconhecidos": [], "copiados": 0}
    ids = por_id(tcs)
    # a proposta de uma execução anterior continua enquanto o texto-chave é o mesmo de quando ela foi feita: se o PO o
    # trocou no one-pager (aceitando a proposta ou escrevendo outro texto), ela já foi decidida e sai
    anteriores = [(i, a, p) for i, a, p in propostas_registradas(copy)
                  if i in ids and mesmo_texto(ids[i].texto, a) and not mesmo_texto(ids[i].texto, p)]
    texto = remover_secao(copy)
    linhas = texto.split("\n")
    do_texto = {literal(t.texto): t for t in tcs if t.tipo in TIPOS_DE_TEXTO}
    com_lacuna = [t for t in tcs if t.tipo in TIPOS_DE_TEXTO and _padrao(t.texto) is not None]
    ligados: Dict[str, List[int]] = {}
    novas: List[Tuple[str, str, str]] = []
    desconhecidos: List[str] = []
    copiados = 0
    #: as linhas das tabelas de strings: `{linha: (células, cabeçalho, coluna PT-BR)}`
    strings: Dict[int, Tuple[List[str], List[str], int]] = {}
    for i, celulas, cabecalho in list(_linhas_de_tabela(linhas)):
        ipt = _coluna(cabecalho, "pt-br", "pt br", "texto aprovado", "string")
        if ipt is not None and ipt < len(celulas):
            strings[i] = (celulas, cabecalho, ipt)

    def ligar(i: int, alvo: TextoChave, anotar: bool, trecho: Optional[str] = None) -> None:
        """A linha `i` passa a trazer o texto-chave: a célula PT-BR inteira, ou só o `trecho` dela que é a reescrita (a
        moldura em volta — «Chamado #101 — Beatriz (23h45): "…"», exp01em1b-e89e91b3 — é microcopy e fica)."""
        nonlocal copiados
        celulas, cabecalho, ipt = strings[i]
        ligados.setdefault(alvo.id, []).append(i)
        mudou = False

        def proposta(escrito: str) -> None:
            # a redação aprovada antes (o PO trocou o texto) só desce: não é proposta do design
            if not any(mesmo_texto(a, escrito) for a in alvo.antes):
                novas.append((alvo.id, alvo.texto, literal(escrito)))

        if trecho == _JA_ESTA:
            pass
        elif trecho is not None and trecho != celulas[ipt] and trecho in celulas[ipt]:
            if not mesmo_texto(alvo.texto, trecho) and not presente(alvo, _documento_literal(trecho)):
                proposta(trecho)
                celulas[ipt] = celulas[ipt].replace(trecho, alvo.texto, 1)
                ipal = _coluna(cabecalho, "palavras")
                if ipal is not None and ipal < len(celulas):
                    celulas[ipal] = str(palavras(celulas[ipt]))
                mudou = True
                copiados += 1
        elif not mesmo_texto(alvo.texto, celulas[ipt]):
            proposta(celulas[ipt])
            celulas[ipt] = alvo.texto
            ipal = _coluna(cabecalho, "palavras")
            if ipal is not None and ipal < len(celulas):
                celulas[ipal] = str(palavras(alvo.texto))
            mudou = True
            copiados += 1
        if anotar and (mudou or anotar_sem_troca):
            inota = _coluna(cabecalho, "nota", "revis")
            if inota is not None and inota < len(celulas) and alvo.id not in ids_citados(celulas[inota]):
                celulas[inota] = (celulas[inota] + f" `{alvo.id}`").strip()
                mudou = True
        if mudou:
            linhas[i] = "| " + " | ".join(celulas) + " |"

    # 1. a linha que cita o ID, ou que traz o próprio texto (com as lacunas preenchidas, se o texto-chave as tem)
    for i, (celulas, _, ipt) in strings.items():
        citados = [c for k, cel in enumerate(celulas) if k != ipt for c in ids_citados(cel)]
        desconhecidos += [c for c in citados if c not in ids]
        alvo = next((ids[c] for c in citados if c in ids and ids[c].tipo in TIPOS_DE_TEXTO), None)
        if alvo is not None:
            ligar(i, alvo, anotar=False, trecho=_trecho_do_texto_chave(alvo, celulas[ipt]))
            continue
        alvo = do_texto.get(literal(celulas[ipt])) or next(
            (t for t in com_lacuna if mesmo_texto(t.texto, celulas[ipt])), None) or next(
            (t for t in tcs if t.tipo in TIPOS_DE_TEXTO and any(mesmo_texto(a, celulas[ipt]) for a in t.antes)), None)
        if alvo is not None:
            ligar(i, alvo, anotar=True)

    def ja_e_texto_chave(trecho: str) -> bool:
        return (literal(trecho) in do_texto
                or any(mesmo_texto(t.texto, trecho) for t in com_lacuna)
                or any(presente(t, _documento_literal(trecho)) for t in tcs if t.tipo in TIPOS_DE_TEXTO))

    # G03 + Decisão 2: variantes quase iguais na mesma etapa do one-pager (ex.: TC-09 e TC-10 da exp02em1b) são ambas
    # aprovadas até o PO escolher uma no de acordo. Quando uma variante irmã já está na copy, a outra não substitui a
    # irmã nem acusa `texto-chave-divergente`.
    irmas_por_id: Dict[str, List[TextoChave]] = {}
    for a, b, _ in variantes_de_texto_chave(tcs):
        irmas_por_id.setdefault(a.id, []).append(b)
        irmas_por_id.setdefault(b.id, []).append(a)

    # 2. o texto-chave sem linha e sem o literal: a reescrita dele — primeiro na coluna PT-BR das tabelas de strings,
    # depois no resto (texto entre aspas, fala do podcast). A reescrita citada na prosa da copy (a nota «o que mudou») não
    # é a string da tela: só é trocada quando não há linha de string parecida.
    sem_linha: List[TextoChave] = []
    doc = _documento_literal("\n".join(linhas))
    for tc in tcs:
        if tc.tipo not in TIPOS_DE_TEXTO or tc.id in ligados:
            continue
        # o texto de tela, o Canal B e a opção moram numa linha de string: o literal citado só na prosa da copy (a nota
        # «Ajuste adotado», a proposta) não é a string da tela — a exp02ef1b citava a pergunta do Canal B aprovada numa
        # nota e trazia outra redação na linha `e6.canalb.pergunta`. O podcast e o roteiro valem onde estiverem.
        if tc.tipo in (PODCAST, ROTEIRO) and presente(tc, doc):
            continue
        celulas_pt = [strings[i][0][strings[i][2]] for i in strings]
        if any(presente(tc, _documento_literal(c)) for c in celulas_pt):
            continue  # numa linha de string, com moldura em volta («Nico investigou no livro: "…"», exp02em1b)
        if any(ir.id in ligados or any(presente(ir, _documento_literal(c)) for c in celulas_pt)
               for ir in irmas_por_id.get(tc.id, [])):
            continue  # variante irmã da mesma etapa já presente na copy (G03 + Decisão 2)
        livres = [(i, t) for i in strings if i not in {j for v in ligados.values() for j in v}
                  for t in _trechos_da_celula(strings[i][0][strings[i][2]])]
        achado = _melhor(tc, [c for c in livres if not ja_e_texto_chave(c[1])])
        if achado is not None:
            ligar(achado[0], tc, anotar=True, trecho=achado[1])
            continue
        if presente(tc, doc):
            continue
        ocupadas = set(strings) | {j for v in ligados.values() for j in v}
        achado = _melhor(tc, [c for c in _candidatos(linhas, ocupadas) if not ja_e_texto_chave(c[1])])
        if achado is not None:
            i, trecho, _ = achado
            linhas[i] = _trocar_trecho(linhas[i], trecho, tc.texto)
            novas.append((tc.id, tc.texto, literal(trecho)))
            ligados.setdefault(tc.id, []).append(i)
            copiados += 1
            continue
        if tc.tipo != OPCAO:
            sem_linha.append(tc)
    doc = _documento_literal("\n".join(linhas))
    divergentes: List[Dict[str, Any]] = []
    for g in [t for t in tcs if t.tipo == OPCOES]:
        opcoes = [t for t in tcs if t.tipo == OPCAO and t.grupo == g.id]
        presentes = [o for o in opcoes if o.id in ligados or presente(o, doc)]
        if presentes and len(presentes) < len(opcoes):
            divergentes.append({"grupo": g, "faltam": [o for o in opcoes if o not in presentes]})
        elif not presentes and g.tipo == OPCOES:
            # nenhuma opção na copy, nem reescrita: a escolha inteira está sem linha (🟡), não com opção a menos
            sem_linha.append(g)
    estranhos = sorted({c for c in desconhecidos if any(c.startswith(g.id + ".") for g in tcs if g.tipo == OPCOES)})
    for c in estranhos:
        g = ids.get(c.rsplit(".", 1)[0])
        if g is not None and not any(d["grupo"].id == g.id for d in divergentes):
            divergentes.append({"grupo": g, "faltam": [], "a_mais": [c]})
    vistas = {(i, literal(p)) for i, _, p in novas}
    propostas = novas + [(i, a, p) for i, a, p in anteriores if (i, literal(p)) not in vistas]
    texto = "\n".join(linhas)
    secao = _secao_da_copy(propostas, sem_linha)
    if secao:
        texto = texto.rstrip() + "\n\n" + secao
    # o fim do texto como veio: as 12 copies do acervo terminam na cerca do envelope, sem «\n», e a quebra a mais virava,
    # na correção pontual, uma troca falsa em `edicoes_pontuais` sem nada copiado (revisão do PR 7, 24/10/2026)
    texto = texto.rstrip() + (copy or "")[len((copy or "").rstrip()):]
    return {"texto": texto, "propostas_novas": novas, "propostas": propostas, "sem_linha": sem_linha,
            "opcoes_divergentes": divergentes, "ids_desconhecidos": sorted(set(desconhecidos)), "copiados": copiados}


def _secao_da_copy(propostas: Sequence[Tuple[str, str, str]], sem_linha: Sequence[TextoChave]) -> str:
    if not propostas and not sem_linha:
        return ""
    linhas = [f"## {TITULO_SECAO_COPY}", "",
              "> Escrita pela esteira (`tools/textos_chave.py`); não edite. O texto-chave do one-pager aprovado é copiado "
              "por código para a linha que o traz: vale o aprovado. A redação que o design tinha escrito está abaixo como "
              "proposta ao PO — para valer, o PO a pede no **Refazer**, e a triagem leva o item a Produto (o one-pager muda "
              "lá, e o texto desce por código).", ""]
    if propostas:
        linhas += ["### Redação que o design propôs e não entrou", ""]
        for ident, aprovado, proposto in propostas:
            linhas.append(f"- [PROPOSTA — validar com PO: {ident} «{aprovado}» → «{proposto}» · a copy trazia esta "
                          "redação; vale o texto aprovado até o PO decidir]")
        linhas.append("")
    if sem_linha:
        linhas += ["### Textos-chave sem linha no sheet", "",
                   "Nenhuma linha da tabela de strings os traz: estão aqui, literais, para quem codifica. A linha da tela "
                   "que os mostra precisa citar o ID.", "", "| ID | Origem | Texto aprovado |", "|---|---|---|"]
        linhas += [f"| `{t.id}` | {t.origem} | {_celula(t.texto)} |" for t in sem_linha]
        linhas.append("")
    return "\n".join(linhas)


def _achado(codigo: str, resumo: str, severidade: str, dono: str = "copy-ptbr-revisao") -> Dict[str, Any]:
    return {"severidade": severidade, "codigo": codigo, "etapa": "design", "agente_responsavel": dono, "resumo": resumo}


#: O marcador do que o professor preenche na preparação, nas grafias do acervo e das sessões de 25/10/2026:
#: `[recorte da aula: parâmetro do professor]`, `[recorte da aula]`, `[tema: parâmetro do professor]`, `[tema do professor]`.
_RE_SLOT_DO_PROFESSOR = re.compile(
    r"\[\s*(?:recorte\s+da\s+aula\b[^\]\n]{0,100}|[^\[\]\n]{0,60}\bpar[âa]metro\s+do\s+professor\s*|tema\s+do\s+professor\s*)\]",
    re.I)
#: A variável de template (`{recorte_da_aula}`) também guarda o lugar do professor.
_RE_VARIAVEL = re.compile(r"\{[^{}\n]{1,60}\}")


def _padrao_dos_slots(texto: str) -> Optional["re.Pattern[str]"]:
    """O texto-chave como expressão regular em que cada marcador do professor é um grupo (o que a copy pôs no lugar dele)
    e as outras lacunas aceitam qualquer coisa, como em `_padrao`; None sem marcador do professor. O marcador na ponta do
    texto não é grupo: sem texto fixo depois (ou antes) dele, a comparação não tem onde parar."""
    alvo = literal(texto)
    lacunas = [m.group(0) for m in _RE_LACUNA.finditer(alvo)]
    partes = _RE_LACUNA.split(alvo)
    if not any(_RE_SLOT_DO_PROFESSOR.fullmatch(l) for l in lacunas):
        return None
    pedacos, grupos = [re.escape(partes[0])], 0
    for k, lacuna in enumerate(lacunas):
        na_ponta = (k == 0 and not partes[0].strip()) or (k == len(lacunas) - 1 and not partes[-1].strip())
        if _RE_SLOT_DO_PROFESSOR.fullmatch(lacuna) and not na_ponta:
            pedacos.append(r"(.{0,160}?)")
            grupos += 1
        else:
            pedacos.append(r"(?:.{0,160}?)")
        pedacos.append(re.escape(partes[k + 1]))
    return re.compile("".join(pedacos)) if grupos else None


def slots_do_professor_fixados(copy: str, tcs: Sequence[TextoChave]) -> List[Dict[str, str]]:
    """As strings da copy que trazem um texto-chave com o marcador do professor trocado por um valor fixo: `{id, chave,
    valor, marcador}`. Comparação de marcador, literal: o resto do texto-chave está na string, e no lugar do marcador há
    outra coisa que não é marcador nem variável.

    Na exp02em1b (session_f6ef44de, 25/10/2026) a string canônica do TC-11 (`e4.narrativa.overlay_cta_gremio`) dizia «O
    post sobre convivência escolar viralizou…», e o one-pager, «O post sobre [recorte da aula: parâmetro do professor]
    viralizou…»: o texto que o professor de qualquer disciplina parametriza saiu fixo. Nenhum gate pegou, porque a lacuna
    preenchida conta como o texto-chave (`mesmo_texto`, certo para `{motivo}` e `X%`) e o literal estava inteiro na seção
    de propostas da copy (2EM-06). Só a coluna PT-BR das tabelas de strings: a amostra preenchida fica nas notas."""
    alvos = [(t, p) for t in tcs if t.tipo in TIPOS_DE_TEXTO for p in (_padrao_dos_slots(t.texto),) if p is not None]
    if not alvos or not (copy or "").strip():
        return []
    saida: List[Dict[str, str]] = []
    for _, celulas, cabecalho in _linhas_de_tabela(remover_secao(copy).split("\n")):
        ipt = _coluna(cabecalho, "pt-br", "pt br", "texto aprovado", "string")
        if ipt is None or ipt >= len(celulas):
            continue
        ichave = _coluna(cabecalho, "chave", "key")
        chave = celulas[ichave].strip("` ") if ichave is not None and ichave < len(celulas) else ""
        celula = _documento_literal(celulas[ipt])
        for tc, padrao in alvos:
            marcadores = [m.group(0) for m in _RE_SLOT_DO_PROFESSOR.finditer(literal(tc.texto))]
            for m in padrao.finditer(celula):
                for valor in m.groups():
                    valor = (valor or "").strip()
                    if _RE_SLOT_DO_PROFESSOR.search(valor) or _RE_VARIAVEL.search(valor):
                        continue
                    item = {"id": tc.id, "chave": chave, "valor": valor, "marcador": marcadores[0] if marcadores else ""}
                    if item not in saida:
                        saida.append(item)
    return saida


def conferir_copy(copy: str, tcs: Sequence[TextoChave]) -> Dict[str, Any]:
    """O gate dos textos-chave na copy: `{status, achados, contagem}`.

    - `texto-chave-divergente` ⛔: linha da copy que cita o texto-chave com outra redação, ou reescrita dele sem o literal
      em lugar nenhum. Depois da cópia por código (`aplicar_na_copy`) não sobra nenhuma; na copy de uma sessão anterior ao
      PR 7, é a medida de quanto o design reescreveu.
    - `opcoes-divergentes` ⛔: escolha com opção a menos (removida ou renomeada) ou a mais — o nº de opções é texto-chave
      (D1). O código não inventa a linha que falta: volta ao dono da copy.
    - `slot-do-professor-fixado` ⛔: string que traz o texto-chave com o marcador do professor trocado por um valor fixo
      (`slots_do_professor_fixados`, 2EM-06). Volta ao dono da copy.
    - `texto-chave-proposta` 🧑: a redação que o design propôs e o código não aplicou, para o PO decidir.
    - `texto-chave-sem-linha` 🟡: texto-chave que nenhuma linha do sheet traz (está só na seção da esteira).
    """
    tcs = list(tcs)
    if not tcs:
        return {"status": "aprovado", "achados": [], "contagem": {"textos_chave": 0}}
    if not (copy or "").strip():
        return {"status": "bloqueado", "contagem": {"textos_chave": len(tcs)},
                "achados": [_achado("copy-vazia", f"A copy chegou vazia, e o one-pager tem {len(tcs)} texto(s)-chave "
                                    "que ela precisa trazer.", "bloqueio")]}
    r = aplicar_na_copy(copy, tcs)
    achados: List[Dict[str, Any]] = []
    if r["propostas_novas"]:
        exemplos = "; ".join(f"`{i}` aprovado «{a[:70]}» → na copy «{p[:70]}»" for i, a, p in r["propostas_novas"][:6])
        achados.append(_achado(
            "texto-chave-divergente",
            f"{len(r['propostas_novas'])} texto(s)-chave do one-pager aprovado estão na copy com outra redação: {exemplos}"
            + ("…" if len(r["propostas_novas"]) > 6 else "") + ". O texto-chave é copiado palavra por palavra (D1): a linha "
            "cita o ID e traz o texto aprovado. Mudança é `[PROPOSTA — validar com PO]`, e o PO a pede no Refazer.",
            "bloqueio"))
    for d in r["opcoes_divergentes"]:
        g = d["grupo"]
        if d.get("faltam"):
            falta = ", ".join(f"`{o.id}` «{o.texto}»" for o in d["faltam"])
            resumo = (f"A escolha `{g.id}` ({g.origem}) tem {g.n} opções no one-pager aprovado — {g.texto} — e a copy "
                      f"não traz {falta}: a opção foi tirada ou renomeada. O nº de opções e o texto delas são do PO (D1): "
                      "restaure a linha com o ID e o texto aprovado. Se o design quer outra escolha, é "
                      f"`[PROPOSTA — validar com PO: {g.id} {g.n} opções → …]`, pela rota do Refazer.")
        else:
            resumo = (f"A copy cita {', '.join(d.get('a_mais') or [])}, opção que a escolha `{g.id}` ({g.origem}) não "
                      f"tem: o one-pager aprovado dá {g.n} opções — {g.texto}. Opção a mais é decisão do PO (D1).")
        achados.append(_achado("opcoes-divergentes", resumo, "bloqueio"))
    fixados = slots_do_professor_fixados(r["texto"], tcs)
    if fixados:
        from tools.severidade import BLOQUEIO, PROVA, por_prova

        # prova em código — o marcador some da string, comparação literal —, então o 🔴 vale (`tools/severidade.py`)
        exemplos = "; ".join(
            f"`{f['id']}`" + (f" (`{f['chave']}`)" if f["chave"] else "")
            + f" traz «{f['valor'][:60]}» no lugar de «{f['marcador']}»" for f in fixados[:6])
        achados.append(_achado(
            "slot-do-professor-fixado",
            f"{len(fixados)} string(s) da copy trazem um texto-chave com o lugar do professor preenchido por um valor fixo: "
            + exemplos + ("…" if len(fixados) > 6 else "") + ". O marcador é o que o professor de qualquer disciplina preenche na preparação "
            "da aula: a string mantém o marcador do one-pager, literal (ou uma variável `{…}`); a amostra preenchida vai "
            "na coluna de notas.", por_prova(BLOQUEIO, PROVA)))
    ja_relatadas = {(i, literal(p)) for i, _, p in r["propostas_novas"]}
    pendentes = [p for p in r["propostas"] if (p[0], literal(p[2])) not in ja_relatadas]
    if pendentes:
        achados.append(_achado(
            "texto-chave-proposta",
            f"{len(pendentes)} redação(ões) que o design propôs para texto-chave não entraram (vale o aprovado): "
            + "; ".join(f"`{i}` «{a[:60]}» → «{p[:60]}»" for i, a, p in pendentes[:6])
            + ". Para valer, o PO pede no **Refazer**: a triagem leva o item a Produto, o one-pager muda e o texto desce "
            "por código.", "decisao_humana", dono="PO"))
    if r["sem_linha"]:
        achados.append(_achado(
            "texto-chave-sem-linha",
            f"{len(r['sem_linha'])} texto(s)-chave sem linha na tabela de strings — estão literais só na seção da esteira: "
            + "; ".join(f"`{t.id}` «{t.texto[:60]}»" for t in r["sem_linha"][:6])
            + ("…" if len(r["sem_linha"]) > 6 else "") + ". A linha da tela que os mostra cita o ID.", "atencao"))
    if r["ids_desconhecidos"]:
        achados.append(_achado(
            "texto-chave-id-desconhecido",
            f"A copy cita ID(s) de texto-chave que o one-pager não tem (mais): {', '.join(r['ids_desconhecidos'][:8])}. "
            "O texto pode ter saído do one-pager num refazer de produto: confira a linha.", "atencao"))
    status = ("bloqueado" if any(a["severidade"] == "bloqueio" for a in achados)
              else "amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados,
            "contagem": {"textos_chave": len([t for t in tcs if t.tipo != OPCAO]), "copiados": r["copiados"],
                         "propostas": len(r["propostas"]), "sem_linha": len(r["sem_linha"]),
                         "opcoes_divergentes": len(r["opcoes_divergentes"])}}


def relatorio(resultado: Dict[str, Any], missao: str = "") -> str:
    import json

    icone = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}[resultado["status"]]
    c = resultado.get("contagem") or {}
    L = [f"# Textos-chave na copy — {missao or 'missão'}", "",
         f"**Veredito: {icone}** · {c.get('textos_chave', 0)} texto(s)-chave do one-pager aprovado (§4, §12a, §9, §11) · "
         f"{c.get('copiados', 0)} copiado(s) por código nesta conferência · {c.get('propostas', 0)} proposta(s) do "
         "design para o PO.", ""]
    if not resultado["achados"]:
        L.append("- Todo texto-chave está na copy, palavra por palavra, e toda escolha com as opções do one-pager.")
    for a in resultado["achados"]:
        marca = {"bloqueio": "⛔", "decisao_humana": "🧑"}.get(a["severidade"], "⚠️")
        L.append(f"- {marca} `{a['codigo']}` — {a['resumo']}")
    envelope = {"agente": AGENTE, "missao": missao or "", "status": resultado["status"],
                "achados": resultado["achados"], "precisa_humano": any(
                    a["severidade"] == "decisao_humana" for a in resultado["achados"])}
    return "\n".join(L) + "\n\n```json\n" + json.dumps(envelope, ensure_ascii=False) + "\n```\n"


# --------------------------------------------------------------------------- handoff, PRD e pedagógico
#: Nos documentos de dev, só a reescrita quase igual é trocada por código: o corpo cita pouco texto de tela, e uma troca
#: errada mudaria o que o dev codifica. A reescrita mais distante fica com os gates (montagem, A116, A121).
CORTE_DOCUMENTO = 0.85


def variantes_de_texto_chave(tcs: Sequence[TextoChave]) -> List[Tuple[TextoChave, TextoChave, float]]:
    """`(tc_a, tc_b, semelhanca)`: pares de textos-chave da mesma origem/etapa que são variantes quase iguais um do outro
    (G03 + Decisão 2). Não decide sozinho: o de acordo pergunta ao PO qual vale, e os gates não tratam uma variante
    aprovada como reescrita da outra."""
    itens = [t for t in tcs if t.tipo in TIPOS_DE_TEXTO and palavras(t.texto) >= 4]
    pares: List[Tuple[TextoChave, TextoChave, float]] = []
    for idx, a in enumerate(itens):
        for b in itens[idx + 1:]:
            if a.tipo != b.tipo or a.origem != b.origem or mesmo_texto(a.texto, b.texto):
                continue
            if not mesmos_numeros(a, b.texto):
                continue
            sim = semelhanca(a.texto, b.texto)
            if sim >= max(0.75, min(corte(a.texto), corte(b.texto))):
                pares.append((a, b, sim))
    return pares


def _exato(texto: str) -> str:
    """Para casar uma redação registrada com a citação: `literal`, sem o ponto final — e sem lacuna preenchida."""
    return literal(texto).rstrip(". ")


def _redacoes_registradas(tcs: Sequence[TextoChave], propostas: Sequence[Tuple[str, str, str]]
                          ) -> Dict[str, List[TextoChave]]:
    """`{redação: [textos-chave]}` das redações que são, por registro, outra versão de um texto-chave: as aprovadas antes
    (`antes`, o PO trocou o texto) e o lado proposto das propostas do design ainda abertas para o mesmo ID."""
    ids = por_id(tcs)
    saida: Dict[str, List[TextoChave]] = {}
    for t in tcs:
        if t.tipo in TIPOS_DE_TEXTO:
            for a in t.antes:
                if not mesmo_texto(t.texto, a):
                    saida.setdefault(_exato(a), []).append(t)
    for i, aprovado, proposto in propostas:
        t = ids.get(i)
        if t is not None and t.tipo in TIPOS_DE_TEXTO and mesmo_texto(t.texto, aprovado) \
                and not mesmo_texto(t.texto, proposto):
            saida.setdefault(_exato(proposto), []).append(t)
    return {k: list({t.id: t for t in v}.values()) for k, v in saida.items() if k}


def aplicar_em_documento(texto: str, tcs: Sequence[TextoChave], propostas: Sequence[Tuple[str, str, str]] = ()
                         ) -> Tuple[str, List[Tuple[str, str, str]]]:
    """`(texto, trocas)`: no corpo (sem o anexo literal), cada citação entre aspas que é reescrita de um texto-chave passa
    a ser o texto aprovado. `trocas` = `(ID, aprovado, como estava)`.

    Reescrita é a citação quase igual (semelhança ≥ `CORTE_DOCUMENTO`) ou, sem régua, a que é letra por letra uma redação
    registrada do mesmo texto-chave: uma aprovada antes (`antes`) ou o lado proposto de uma das `propostas` do design
    (`(ID, aprovado, proposto)`, as da copy). Na exp02ef1b, a pergunta do Canal B que o design reescreveu («Para mostrar
    que duas crianças estudam juntas…», semelhança 0,71) é a proposta TC-02 que o A078b grava na copy, e seguia no
    handoff e no PRD (revisão do PR 7, 24/10/2026)."""
    from tools.conteudo_aprovado import TITULO_ANEXO, remover_anexo

    if not (texto or "").strip() or not tcs:
        return texto or "", []
    corpo = remover_anexo(texto)
    anexo = texto[len(corpo.rstrip("\n")):] if TITULO_ANEXO in texto and texto.startswith(corpo.rstrip("\n")) else ""
    alvos = [t for t in tcs if t.tipo in TIPOS_DE_TEXTO and palavras(t.texto) >= 3]
    textos = [t for t in tcs if t.tipo in TIPOS_DE_TEXTO]
    registradas = _redacoes_registradas(tcs, propostas)
    trocas: List[Tuple[str, str, str]] = []
    #: `(início, fim, texto aprovado)` de cada citação trocada: a troca é feita na posição dela — trocar a primeira
    #: ocorrência do texto pegaria a mesma redação dentro de uma proposta, mais acima no documento
    pedacos: List[Tuple[int, int, str]] = []
    for m in list(re.finditer(r"[\"“«]([^\"”»\n]{12,400})[\"”»]", corpo)):
        citado = m.group(1).strip().strip("*").strip()
        if any(mesmo_texto(t.texto, citado) or presente(t, _documento_literal(citado)) for t in textos):
            continue  # o texto-chave, com o ponto final, sem ele ou com lacuna preenchida (PRD da exp01ef1b / G03)
        inicio = corpo.rfind("\n", 0, m.start()) + 1
        fim = corpo.find("\n", m.end())
        linha = corpo[inicio: fim if fim >= 0 else len(corpo)]
        if _RE_MARCADOR_PROPOSTA.search(linha):
            # a redação que o design propôs, registrada para o PO (a 19.3 do PRD lista o texto literal de cada
            # [PROPOSTA] aberta): trocá-la pelo aprovado deixava «aprovado» → «aprovado», e a proposta sumia
            continue
        donos = registradas.get(_exato(citado), [])
        if len(donos) > 1:
            continue  # a mesma redação registrada para dois textos-chave: não há como saber qual
        melhor, valor = (donos[0], 1.0) if donos else (None, 0.0)
        for t in ([] if donos else alvos):
            if not mesmos_numeros(t, citado):
                continue  # «…: 1/3» não é reescrita de «…: 3/3» (exp03em1b)
            v = semelhanca(t.texto, citado)
            if v > valor:
                melhor, valor = t, v
        if melhor is None or valor < max(CORTE_DOCUMENTO, corte(melhor.texto)):
            continue
        resto = linha[: m.start() - inicio] + " " + linha[m.end() - inicio:]
        if presente(melhor, _documento_literal(resto)):
            continue  # a linha compara o aprovado com outra redação: não é citação a corrigir
        pedacos.append((m.start(1), m.end(1), melhor.texto))
        trocas.append((melhor.id, melhor.texto, citado))
    if not trocas:
        return texto, []
    novo = corpo
    for ini, fim_, aprovado in reversed(pedacos):
        novo = novo[:ini] + aprovado + novo[fim_:]
    return (novo.rstrip("\n") + anexo) if anexo else novo, trocas
