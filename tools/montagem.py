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
   14), as linhas do bloco 13 cuja decisão passa pela lista branca do PR 2 (`tools/decisoes.py`), as decisões do PO
   gravadas no de acordo (`estado.decisoes_do_po`, PR 3), o valor que o PO afirmou ao refazer design ou dev e o teto
   de palavras da faixa da missão. Ficam de fora os de dono plataforma (polling, TTL, p95, uptime, lote da SDK, `px`,
   espera de carregamento), a medida de layout (`75% da tela`), a medida de uma string que nenhum teto rege, o
   exemplo «(ex.: …)», a estatística de fonte externa, a nota de acessibilidade, os limites do recorte da aula e o que
   vem marcado `[PROPOSTA — validar com PO: …]`, que é proposta e não decisão. No handoff, o texto-chave do PO (Canal B,
   debate, texto de tela do §4) citado com outra redação também volta; no PRD isso já é o `literal-parafraseado` do
   A116.
b) **hipóteses, metas e tetos iguais aos do contrato.** O número de cada hipótese do §17 está na linha
   correspondente do corpo (H1 25×30 da exp02ef1b); o alvo e o limiar de decisão de cada KPI que cita uma `PQ-nn` são
   os da linha dela no 9f da spec; no PRD, cada teto do §15 está no corpo (as 35 palavras da exp06ef1b). O que não é
   divergência certa — o limiar da `PQ-nn` citada no lugar da meta do §17, o complemento dela — sai como dúvida
   (`hipotese-a-conferir`, atenção), separada do bloqueio no relatório.
c) **estados da §6 iguais aos do contrato.** Todo estado do «Contrato de estados» da spec está nas colunas de estado
   e no diagrama da §6, e nenhum estado ali é inventado (o PRD da exp02ef1b trocou os 15 nomes do contrato por
   `desafiar`, `explicar_padroes`…, e largou `PROCESSANDO_RESPOSTA_VISITA`). Estado de decomposição que o fluxo do
   design nomeia não é invenção (D7: estado do fluxo é detalhe de design).
d) **decisão de design não vira origem de produto.** Número com origem citada em produto («(§17 do one-pager)»,
   «(spec, bloco 9f)») tem de estar lá; `[D0-n]` citado como «contratual», «do PO» ou com origem no one-pager é
   decisão do design vestida de produto. Citar o bloco 13 ou o 14 é legítimo: desde o PR 6 eles moram no anexo de design
   (`design/00-anexo-design-spec.md`), e na missão desenhada antes dele, em `produto/05-spec-missao.md`.

Divergência que o próprio contrato tem — na origem certa: a linha correspondente da spec, ou a linha do 9f que cita a
hipótese, com outro número que o §15 ou o §17; o que vem marcado `[PROPOSTA]`/`[PARÂMETRO]` não conta — não se
resolve no PRD: o corpo segue o one-pager *e* o PRD registra a divergência na seção 19 (no handoff, na seção 7) como
`[ABERTO — dono: produto: …]` com os dois valores. O registro é exigência a mais, nunca saída para o corpo trocado. O
rastro conta esse marcador como pendência de produto, e o PRD continua não pronto até o PO decidir.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from tools.propagacao import (
    _RE_NUMERO,
    _UNIDADE,
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

    from tools.anexo_design import KEY_ANEXO, spec_consolidada

    # o bloco 13 mora no anexo de design desde o PR 6; na sessão anterior, dentro da `spec_missao`
    linhas = _linhas_do_bloco_13(spec_consolidada(state))
    if not linhas:
        return "", []
    # a missão desenhada antes do PR 6 é lida com a lista do D0 de então: o PRD dela cita decisões de duração e de dados
    # que eram do design, e reler com a régua do D0-UX mudaria o veredito do que já foi aprovado
    legado = not str(state.get(KEY_ANEXO) or "").strip()
    de_produto: Set[str] = set()
    for d in decisoes_d0(state):
        if d["classe"] not in ("", "?") and dec.classe_de_produto(d["classe"], legado=legado):
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


#: O valor que o PO afirma como novo no pedido: «pode ser até 10 palavras» (exp04ef1b, 25/09/2026), «deve ser 30%»,
#: «volta para 30%», «passa a ser 45 s», «ratifico», «fica em», «o correto é 60 s». Número de pedido sem um desses que o
#: reja (`_rege`) não vira origem: o pedido em prosa livre cita também o número errado («o PRD está com 25%, deve ser
#: 30%»). «Troca para» e «muda para» só no imperativo e no infinitivo: «o PRD troca para 25%» descreve o documento.
_RE_VALOR_AFIRMADO = re.compile(
    r"\b(?:pode|podem|deve|devem)\s+(?:ser|ficar|ter)\b|\bseja\b|\bpassa(?:r|m)?\s+(?:a\s+ser|a\s+ter|para)\b|"
    r"\bvolta(?:r|m)?\s+(?:a\s+ser|para)\b|"
    r"\b(?:mud(?:e|em|ar)|troqu(?:e|em)|trocar|alter(?:e|em|ar)|ajust(?:e|em|ar)|corrij(?:a|am)|corrigir)\s+para\b|"
    r"\bfi(?:ca|car|que|quem)\s+(?:com|em)\b|\bratific\w*|\bhomolog\w*|\bdecid[oi]\b|\bdefin[oi]\b|\baprovo\b|"
    r"\bconfirmo\b|\baceito\b|\bsolicitad[oa]\b|\bt[êe]m\s+(?:de|que)\s+(?:ser|ter|ficar)\b|"
    r"\b(?:o\s+)?(?:valor\s+)?(?:correto|certo)\s+(?:é|seria|ser[áa])(?!\w)", re.I)
#: O marcador rege só o número que vem logo depois dele: no meio, só artigo, preposição, quantificador e o nome do
#: valor — «pode ser até 10 palavras», «fica em 60 s», «tem que ter no máximo 35 palavras», «ratifico o teto de 35
#: palavras» — e os números de antes com o separador («30% ou 40%», «de 8 a 10 palavras»). Revisão do PR #77
#: (24/10/2026): bastava o marcador antes do número, e «No KPI-08 deve ser removido o limiar de 80%», «Decidi remover o
#: limiar de 80%», «Tem que ser tirada a meta de 70%» faziam origem do número que o PO manda tirar — o 80% inventado do
#: KPI-08 da exp02ef1b-4fd72a9a deixava de ser cobrado. Verbo no meio, seja qual for, tira o número do alcance.
_CONECTORES_DE_VALOR = frozenset(
    "a à ao aos o os as um uma de do da dos das em no na nos nas para pra com até ate entre cerca aproximadamente "
    "apenas só somente exatamente máximo maximo mínimo minimo máx max mín min pelo menos igual "
    "teto limiar meta alvo limite valor tempo timer prazo duração duracao piso".split())
_SEPARADORES_DE_VALOR = frozenset({",", "e", "ou", "a", "até", "ate", "-", "–"})
_LIMITE_DE_CONECTORES = 5
_RE_TOKEN = re.compile(r"\d+(?:[.,]\d+)?|[^\W\d_]+\.?|%|[~≤≥<>=]+|[,–-]|\S")
#: O que o PO cita como errado ou antigo, no rótulo do item da lista: «o PRD está com 25%», «hoje», «em vez de 25%»,
#: «não 25%», «o PRD usou 25%», «o §17 diz 30%», «o timer tem 45 s».
_RE_VALOR_CITADO = re.compile(
    r"\best[áa]\s+(?:com|em|escrit[oa]|como)\b|\bestava(?:m)?\b|\bhoje\b|\batual(?:mente)?\b|\bem\s+vez\s+de\b|"
    r"\bno\s+lugar\s+de\b|\bao\s+inv[ée]s\s+de\b|\berrad[oa]s?\b|\bincorret[oa]s?\b|\bera(?:m)?\b|\bn[ãa]o\b|"
    r"\bus(?:ou|a|ava|aram|am)\b|\bescrev(?:e|eu|ia|eram|em)\b|\bdi(?:z|zia|sse|zem)\b|"
    r"\bt(?:em|inha|êm)\b(?!\s+(?:de|que)\b)|\btr(?:ouxe|az|aziam?)\b|\bp(?:[ôo]s|[õo]e|useram)\b|"
    r"\bcoloc(?:ou|a|aram)\b|\baparec(?:e|eu|em)\b|\bmostr(?:a|ou|ava)\b|\bcit(?:a|ou)\b", re.I)
#: Verbo de remoção ou de autoria do redator: o número que vem depois é o que o PO manda tirar ou o que o documento
#: escreveu — «remover», «tirada», «o PRD inventou», «o handoff baixou o timer para 45 s», «reduziu», «subiu».
_RE_VERBO_DE_REMOCAO_OU_AUTORIA = re.compile(
    r"\b(?:remov|retir|tir(?:a|am|ar|ad[oa]s?|e|em|ou)\b|elimin|apag|exclu|descart|suprim|invent|"
    r"cri(?:ou|ad[oa]s?|ar|aram)\b|baix|reduz|diminu|aument|sub(?:iu|ir|iram)\b|troc|mud|encolh|"
    r"cort(?:ar|ad[oa]s?|ou)\b|alter(?:ar|ad[oa]s?|ou)\b|perd(?:er|eu|id[oa]s?)\b)", re.I)
#: O rótulo do item de lista que o marcador abre com dois-pontos nomeia o valor: «O teto de texto está ratificado …:
#: resumo de notícia com 25 a 35 palavras; manchete com até 10 palavras» (exp04ef1b, 25/09/2026). Não fala do
#: documento, não tem número solto nem verbo — passado, infinitivo, gerúndio ou cópula («Ajuste solicitado: o PRD
#: inventou o limiar de 80%»).
_RE_ROTULO_QUE_CITA = re.compile(
    r"\b(?:PRD|handoff|prot[óo]tipo|redator|agente|Stitch|spec|design|banca|gate|wireframe|verificador|documento|"
    r"one-pager)\b|§|(?<![\w-])\d", re.I)
_RE_FORMA_VERBAL = re.compile(r"\w{2,}(?:ou|eu|iu|ar|er|ir|ndo)|é|são|era|eram|foi|foram|est[áa]|est[ãa]o|ficou|"
                              r"vai|v[ãa]o|h[áa]|deve|devem|pode|podem|precisa", re.I)
#: Logo depois do número, até o próximo: «de 25% para 30%», «25% → 30%» (o de antes da seta sai); «o 25% está
#: errado»; «o limiar de 80% do KPI-08 deve ser removido», «80% inventado».
_RE_CITADO_DEPOIS = re.compile(
    r"^\s*(?:para\b|→|->|=>)|^[^;:]{0,50}?\b(?:errad[oa]s?|incorret[oa]s?|inventad[oa]s?|"
    r"(?:remov|retir|tir|elimin|apag|cort|descart|suprim)(?:ad[oa]s?|id[oa]s?|ar|er|ir)|exclu(?:[íi]d[oa]s?|ir)|"
    r"sai|sair)\b", re.I)
#: Frase: o ponto seguido de maiúscula ou a quebra de linha — «máx. 10 palavras» não corta a frase.
_RE_FIM_DE_FRASE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ])|\n")
#: Fronteira de oração dentro da frase. A adversativa encerra o alcance do marcador: «Decidi: o timer tem 45 s no
#: handoff, mas deve ser 60 s». Os dois-pontos depois do marcador abrem o que ele afirma, e o ponto e vírgula separa os
#: itens dessa lista — «O teto … está ratificado …: resumo de notícia com 25 a 35 palavras; manchete com até 10
#: palavras» (exp04ef1b, 25/09/2026); sem os dois-pontos, o ponto e vírgula também encerra o alcance.
_RE_FRONTEIRA_DE_ORACAO = re.compile(r"[;:]|\b(?:mas|por[ée]m|contudo|entretanto|todavia)\b", re.I)


def _so_valor(trecho: str) -> bool:
    """Entre o marcador e o número só há o que rege um valor: até `_LIMITE_DE_CONECTORES` conectores de valor,
    símbolo de comparação e os números de antes, com a unidade e o separador."""
    conectores, depois_de_numero = 0, False
    for tok in _RE_TOKEN.findall(trecho or ""):
        t = tok.lower().rstrip(".") if tok != "." else tok
        if re.fullmatch(r"\d+(?:[.,]\d+)?", t):
            depois_de_numero = True
        elif depois_de_numero and (t == "%" or t in _UNIDADE):
            pass
        elif depois_de_numero and t in _SEPARADORES_DE_VALOR:
            depois_de_numero = False
        elif re.fullmatch(r"[~≤≥<>=]+", t):
            depois_de_numero = False
        elif t in _CONECTORES_DE_VALOR:
            depois_de_numero, conectores = False, conectores + 1
            if conectores > _LIMITE_DE_CONECTORES:
                return False
        else:
            return False
    return True


def _rotulo_de_valor(rotulo: str) -> bool:
    """O começo do item de lista, antes dos conectores, só nomeia o valor (`_RE_ROTULO_QUE_CITA`): sem documento, sem
    número solto, sem verbo citado, de remoção ou de autoria, e sem forma verbal fora dos nomes de valor."""
    if _RE_ROTULO_QUE_CITA.search(rotulo) or _RE_VALOR_CITADO.search(rotulo) or (
            _RE_VERBO_DE_REMOCAO_OU_AUTORIA.search(rotulo)):
        return False
    return not any(_RE_FORMA_VERBAL.fullmatch(p) for p in re.findall(r"[^\W\d_]+", rotulo)
                   if p.lower() not in _CONECTORES_DE_VALOR)


def _item_de_valor(item: str) -> bool:
    """O item da lista é «rótulo + conectores + número»: o rótulo mais curto cujo resto só rege o valor."""
    cortes = [0] + [m.end() for m in re.finditer(r"\s+", item)] + [len(item)]
    corte = next(c for c in cortes if _so_valor(item[c:]))
    return _rotulo_de_valor(item[:corte])


def _rege(frase: str, inicio: int) -> bool:
    """Um marcador afirmado rege o número que começa em `inicio`: o da própria oração, só com conectores de valor no
    meio (`_so_valor`); sem marcador na oração, o que abre com dois-pontos a lista de que ela é item — sem número
    regido antes dos dois-pontos, com ponto e vírgula entre os itens e o item no formato rótulo do valor + conectores
    (`_item_de_valor`). Nunca por cima de adversativa."""
    fronteiras = list(_RE_FRONTEIRA_DE_ORACAO.finditer(frase, 0, inicio))
    oracao = fronteiras[-1].end() if fronteiras else 0
    proprios = list(_RE_VALOR_AFIRMADO.finditer(frase, oracao, inicio))
    if proprios:
        return _so_valor(frase[proprios[-1].end():inicio])
    k = len(fronteiras)
    # sobe pelos itens separados por ponto e vírgula até os dois-pontos que os abrem
    while k and fronteiras[k - 1].group(0) == ";":
        k -= 1
    if not k or fronteiras[k - 1].group(0) != ":":
        return False
    dois_pontos = fronteiras[k - 1].start()
    abre = list(_RE_VALOR_AFIRMADO.finditer(frase, fronteiras[k - 2].end() if k > 1 else 0, dois_pontos))
    if not abre or _RE_NUMERO.search(frase[abre[-1].end():dois_pontos]):
        # sem marcador, ou ele já regeu o seu número: os dois-pontos explicam, não abrem lista («Deve ser 30%: o PRD
        # usou 25%»)
        return False
    return _item_de_valor(frase[oracao:inicio])


def _valores_afirmados(texto: str) -> List[Tuple[str, str]]:
    """Os números (com unidade) que o pedido afirma como valor novo, regidos por um `_RE_VALOR_AFIRMADO` (`_rege`) —
    sem o relato de gate colado, sem o que vem entre aspas (o texto que o PO cita para trocar) e sem o que ele cita
    como errado, manda tirar ou atribui ao documento logo depois do número (`_RE_CITADO_DEPOIS`).

    Revisão do PR #77 (24/10/2026), duas vezes: bastava o marcador em qualquer lugar antes do número, na mesma frase,
    e «Deve ser 30%; o PRD usou 25%» faziam origem do número citado; depois, com o alcance na própria oração e uma lista
    fechada de verbos de citação, ainda passavam «deve ser removido o limiar de 80%», «Ajuste solicitado: o PRD
    inventou o limiar de 80%». O ônus inverteu: o marcador só rege o número logo depois dele."""
    from tools.fidelidade import sem_relatos_de_gate

    saida: List[Tuple[str, str]] = []
    for frase in _RE_FIM_DE_FRASE.split(_RE_CITACAO.sub(" ", sem_relatos_de_gate(texto or ""))):
        ms = list(_RE_NUMERO.finditer(frase))
        for i, m in enumerate(ms):
            depois = frase[m.end():ms[i + 1].start() if i + 1 < len(ms) else len(frase)]
            if not _rege(frase, m.start()) or _RE_CITADO_DEPOIS.search(depois):
                continue
            tok = (m.group(1).replace(",", "."), _UNIDADE[m.group(2).lower()])
            if tok not in saida:
                saida.append(tok)
    return saida


def _texto_dos_pedidos_do_po(state: Dict[str, Any]) -> str:
    """O que o PO decidiu ao refazer design ou dev — depois do de acordo de produto, quando a spec já não muda. Na
    exp04ef1b-8ce9c32d (25/09/2026) o PO pediu no refazer de dev «pode ser até 10 palavras», o PRD e o handoff as
    escreveram, e o A101b/A116b as cobravam como número sem origem (análise de 24/10/2026). Vale `pedidos_do_po` (sem
    o item de produto, que a cascata leva ao one-pager, e sem o que ficou pendente de Devolver); na sessão anterior a
    ele, os pareceres `refazer` dessas etapas. Só o número que o PO afirma como valor novo vira origem
    (`_valores_afirmados`): o que ele cita para trocar — entre aspas, «texto atual», «está com», relato de gate —
    não."""
    pedidos = [p for p in state.get("pedidos_do_po") or [] if isinstance(p, dict)]
    # o pedido dividido pela triagem que voltou ao PO para Devolver: o item de outro dono ficou `pendente_em`, e o
    # contexto do pedido (o «Resumo geral»), que vai junto no texto da etapa, repete o número dele — nem o contexto nem
    # o número do item pendente viram origem (revisão do PR #77, 24/10/2026)
    pendentes = {_refazer_de(p) for p in pedidos if p.get("pendente_em")}
    numeros_pendentes = {t for p in pedidos if p.get("pendente_em") for t in numeros(str(p.get("texto") or ""))}
    textos: List[Tuple[str, bool]] = []
    for p in pedidos:
        if str(p.get("etapa") or "") not in ("design", "dev") or p.get("pendente_em"):
            continue
        texto, com_pendente = str(p.get("texto") or ""), _refazer_de(p) in pendentes
        if com_pendente and str(p.get("contexto") or "").strip():
            texto = texto.replace(str(p["contexto"]).strip(), " ")
        textos.append((texto, com_pendente))
    if not pedidos:
        textos = [(str(p.get("comentario") or ""), False) for p in state.get("pareceres_humanos") or []
                  if isinstance(p, dict) and p.get("acao") == "refazer" and p.get("etapa") in ("design", "dev")]
    valores: List[Tuple[str, str]] = []
    for t, com_pendente in textos:
        valores += [v for v in _valores_afirmados(t)
                    if v not in valores and not (com_pendente and v in numeros_pendentes)]
    return "\n".join(f"{_fmt(v)} — pedido do PO ao refazer" for v in valores)


def _refazer_de(pedido: Dict[str, Any]) -> str:
    """O refazer de onde o pedido veio: a origem sem o sufixo que a divisão por dono acrescenta
    (`pipeline/passagem.py::_pedido_por_dono`)."""
    return str(pedido.get("origem") or "").split(" · itens de ")[0]


def _teto_da_faixa(state: Dict[str, Any]) -> str:
    """O teto de palavras por frase da faixa da missão (`references/teto-palavras-por-faixa.md`), que o handoff da
    exp06ef1b-727a3c2d citou como «teto da faixa: 20 palavras» (6º ano): é padrão da plataforma, não decisão do
    redator. Só o da faixa da missão — o 20 do 6º–9º não vira origem numa missão do 1º ano."""
    from tools.textos_chave import faixa, tetos_por_faixa

    f = faixa(*(str(state.get(k) or "") for k in ("slug", "one_pager", "briefing", "spec_missao")))
    teto = tetos_por_faixa()[0].get(f) if f else None
    return f"teto da faixa {f}: {teto} palavras por frase" if teto else ""


def contrato(state: Dict[str, Any]) -> Dict[str, str]:
    """Os textos do contrato, por fonte: `spec_produto` é a `spec_missao` sem os blocos 13 e 14 (desde o PR 6 ela não os
    tem: o bloco 15, de completude, é de produto e conta); `bloco_13` só as decisões da lista branca, lidas do anexo de
    design; `decisoes_do_po` o que o PO fixou no de acordo; `pedidos_do_po` o que ele decidiu ao refazer design ou dev;
    `teto_da_faixa` o padrão de palavras por frase da faixa."""
    docs = {k: str(state.get(k) or "") for k in FONTES_DO_CONTRATO}
    docs["spec_produto"] = spec_de_produto(str(state.get("spec_missao") or ""))
    docs["bloco_13"], _ = bloco_13_da_lista_branca(state)
    docs["decisoes_do_po"] = _texto_das_decisoes_do_po(state.get("decisoes_do_po"))
    docs["pedidos_do_po"] = _texto_dos_pedidos_do_po(state)
    docs["teto_da_faixa"] = _teto_da_faixa(state)
    docs["perguntas_transversais"] = perguntas_transversais()
    return docs


#: Marcador aberto não é decisão: a sugestão dentro de `[PARÂMETRO — …, sugestão: 10%]` é do agente de produto, e o
#: número só vira contrato quando o PO a aceita no de acordo (PR 3). Os 10% da moldura, os 45 s e as 15 palavras da
#: exp02ef1b estavam só na sugestão — e o D0 os fechou no lugar do PO.
_RE_MARCADOR_ABERTO = re.compile(r"\[(?:PAR[ÂA]METRO|PROPOSTA)\b[^\]\n]*\]", re.I)


def texto_do_contrato(docs: Dict[str, str]) -> str:
    """O contrato num texto só, sem o conteúdo dos marcadores abertos. Serve só de origem para o número de regra: a
    linha do 9f marcada `[PROPOSTA]` continua valendo como origem do alvo que o KPI copia dela (regra 8 do redator),
    mas não decide divergência do contrato (`divergencias_do_contrato` tira a linha inteira)."""
    texto = _RE_MARCADOR_ABERTO.sub(" ", "\n".join(docs.values()))
    # o payload do evento diz a unidade no nome da chave: `{"segundos_sem_acao": 90}` na tabela de eventos da spec é a
    # origem dos «90s sem ação» do handoff e do PRD da exp04ef1b (24/10/2026)
    return re.sub(r"(\w*(segundos|minutos)\w*)[\"']?\s*:\s*(\d+(?:\.\d+)?)",
                  lambda m: f"{m.group(1)} {m.group(3)} {'s' if m.group(2) == 'segundos' else 'min'}", texto)


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
    r"polling|sondagem|\bTTL\b|\bJWT\b|\bLCP\b|\bINP\b|\bCLS\b|\bp9[59]\b|percentil|uptime|"
    r"lat[êe]ncia|\b5xx\b|\b(?:HTTP|erro|status|c[óo]digo)\s*\d{3}\b|\b429\b|taxa de erro|falha de (?:carregamento|renderiza)|web ?vitals|"
    r"amostragem|batch|retry|backoff|RNF-(?:PERF|DISP|SEG)|"
    r"F5\b|recarreg|reconex|Cloud ?Run|\bCDN\b|bundle|\bKB\b|\bMB\b|throttl|debounce|quota|cota de IA|"
    # consulta periódica a uma rota é polling com outro nome («consultando `GET /juri-estadual/gate` a cada 3
    # segundos», PRD da exp06ef1b)
    r"\bGET\s+/|"
    # a origem declarada é a plataforma: «(contrato da plataforma)», «(ADR-105)»
    r"\bADR-\d|contrato da plataforma|\(plataforma\)|"
    # a espera do carregamento é da casca (handoff da exp06ef1b-727a3c2d, 24/10/2026); a barra de progresso, que também
    # mostra o tempo de uma rodada, está em `_PLATAFORMA_COM_CONTEXTO`
    r"spinner|skeleton", re.I)
#: Termos que também nomeiam regra da mecânica: só são de plataforma com o contexto técnico na mesma linha. «Tempo
#: limite de 45 s para responder» é decisão de produto (os 45 s da exp02ef1b foram o D0 decidindo no lugar do PO);
#: «timeout > 10 s» de rede (exp06ef1b), «Timeout» da API de IA (exp05ef1b), o «lote de 50 eventos / 10 s da SDK»
#: (exp07ef1b), «tokens de IA» e o «erro técnico → bug de infra» do KPI T10 são plataforma (acervo, revisão de
#: 23/10/2026).
_CONTEXTO_DE_REDE = (r"HTTP|requisi[çc]|\bAPI\b|sess[ãa]o|\bJWT\b|servidor|endpoint|\brede\b|conex[ãa]o|offline|"
                     r"\b(?:GET|POST|PUT|PATCH|DELETE)\s+/|\bCDN\b|navegador|service ?worker|\bSDK\b")
_PLATAFORMA_COM_CONTEXTO = (
    (re.compile(r"timeout|tempo limite|\bcache\b|a cada \d+(?:[.,]\d+)?\s*(?:s\b|seg)", re.I),
     re.compile(_CONTEXTO_DE_REDE, re.I)),
    (re.compile(r"\btokens?\b", re.I),
     re.compile(r"tokens?\s+(?:de\s+)?(?:IA|acesso|sess[ãa]o|autentica)|(?:access|refresh|id)[ _-]?token|\bJWT\b", re.I)),
    (re.compile(r"\blote\b", re.I), re.compile(r"eventos?|\bSDK\b|telemetria", re.I)),
    (re.compile(r"disponibilidade|erro t[ée]cnico", re.I),
     re.compile(r"infra|\bbug\b|servidor|\bAPI\b|\bSLA\b|\bSLO\b|" + _CONTEXTO_DE_REDE, re.I)),
    # a «barra de progresso contínua com estimativa tranquilizadora de 10 a 20 segundos» da geração por IA (handoff da
    # exp06ef1b-727a3c2d, 24/10/2026) é espera da casca; a «barra de progresso do tempo da rodada: 45 s» é a mecânica,
    # decisão de produto (revisão do PR #77)
    (re.compile(r"barra de progresso|indicador de progresso", re.I),
     re.compile(r"carreg|gera[çc][ãa]o|gerando|\bIA\b|\bespera\b|aguard|estimativ", re.I)),
)


def de_plataforma(linha: str) -> bool:
    """A linha fala de infraestrutura: termo inequívoco, ou termo ambíguo com o contexto técnico ao lado."""
    if _RE_PLATAFORMA.search(linha or ""):
        return True
    return any(termo.search(linha or "") and contexto.search(linha or "") for termo, contexto in _PLATAFORMA_COM_CONTEXTO)
#: Porcentagem de layout: o que a tela ocupa é desenho (a folha de 75% e o overlay de 70% da exp02ef1b). A área mínima
#: da moldura não entra aqui: os 10% da exp02ef1b são regra da mecânica, que o D0 decidiu no lugar do PO.
_RE_LAYOUT = re.compile(r"viewport|altura|largura|overlay|opacidade|cobr[ie]|ocupa|\bfolha\b|modal|drawer|"
                        r"sheet", re.I)
#: Palavras e caracteres só são regra quando a linha diz teto ou piso; «(13 palavras)» ao lado de uma string é medida.
_RE_TETO_OU_PISO = re.compile(r"m[áa]x|teto|limite|\bat[ée]\b|≤|<=|n[ãa]o (?:pode|deve)|exced|ultrapass|passa de|m[íi]nim|piso|≥|"
                              r">=|pelo menos|no m[íi]nimo", re.I)
#: E o teto ou o piso tem de reger aquele número: vir logo antes dele, na mesma oração (sem `,;|()` no meio). Bastava a
#: linha dizer «teto» em qualquer lugar, e a medida da string ao lado virava regra: «fala de Bento com 21 palavras»
#: (exp04ef1b), «legendas com 39 a 46 palavras (teto: 60)» (exp06ef1b), «`e6.pergunta.em13co26` (49 palavras)»
#: (exp02em1b) — análise de 24/10/2026.
_RE_TETO_ANTES = re.compile(_RE_TETO_OU_PISO.pattern + r"|\bcap\b|limitad[oa]s?\b", re.I)
#: «frases com até 17 palavras (teto da faixa: 20 palavras)», «legendas com 39 a 46 palavras (teto: 60)»: o número
#: seguido do teto com outro número — solto ou da mesma unidade — é a medida, e o teto é o outro. «(teto do D0-09)»,
#: «(teto do §15)» e «(máx. 2 linhas)» não trazem outro número de palavras: são o teto deste (o «§15» é a seção onde
#: moram os tetos, não um teto de 15 — revisão do PR #77, 24/10/2026).
_TETO_DEPOIS = (r"^\s*[(,—–]?\s*(?:teto|m[áa]x|limite)[^)\n;|]*?(?<![\w.,§-])(?<!§\s)\d+(?:[.,]\d+)?"
                r"\s*(?:{unidade}\b|[)\n;,|]|$)")
#: O teto ou o piso logo depois do número: «35 palavras no máximo», «35 palavras (teto)», «(teto do D0-09)», «8 a 10
#: palavras, sem exceder o teto», «35 palavras ou menos». Revisão do PR #77 (24/10/2026): só o marcador de antes
#: contava, e o teto novo sem origem escrito assim deixava de ser cobrado.
_RE_TETO_POSPOSTO = re.compile(
    r"^\s*(?:,\s*)?(?:\(\s*(?:teto|m[áa]x|limite|piso|m[íi]n)|no\s+m[áa]ximo|no\s+m[íi]nimo|ou\s+(?:menos|mais)\b|"
    r"(?:de\s+|como\s+)?(?:teto|limite|piso)\b|(?:sem|n[ãa]o\s+(?:pode|deve)(?:m)?)\s+(?:exceder|ultrapassar|passar))",
    re.I)
#: O marcador que vem logo antes da vírgula que o separa do número: «balões com, no máximo, 35 palavras».
_RE_MARCADOR_E_VIRGULA = re.compile(r"(m[áa]x(?:imo)?|m[íi]n(?:imo)?|teto|limite|piso)\.?\s*,\s*$", re.I)


def _teto_rege(linha: str, tok: Tuple[str, str]) -> bool:
    """Algum teto ou piso rege este número de palavras ou caracteres na linha (em alguma das ocorrências dele): logo
    antes dele, na mesma oração; logo depois (`_RE_TETO_POSPOSTO`); ou, em linha de tabela, na célula anterior
    («| Balão | Teto | 35 palavras |»). A medida seguida do teto com outro número (`_TETO_DEPOIS`) não é regida."""
    num = re.escape(tok[0]).replace(r"\.", "[.,]")
    tabela = linha.count("|") >= 2
    for m in re.finditer(rf"(?<![\w.,]){num}\s?{tok[1]}", linha, re.I):
        depois = linha[m.end():]
        if re.match(_TETO_DEPOIS.format(unidade=tok[1]), depois, re.I):
            continue
        trecho = _RE_MARCADOR_E_VIRGULA.sub(r"\1 ", linha[max(0, m.start() - 40):m.start()])
        if _RE_TETO_ANTES.search(re.split(r"[,;|()]", trecho)[-1]) or _RE_TETO_POSPOSTO.match(depois):
            return True
        if tabela:
            celulas = linha[:m.start()].split("|")
            # o número abre a célula, e a anterior é só o marcador — sem número dela
            if (len(celulas) >= 3 and not re.search(r"\w", re.sub(r"[*_`~≈]", "", celulas[-1]))
                    and _RE_TETO_ANTES.search(celulas[-2]) and not re.search(r"\d", celulas[-2])):
                return True
    return False


#: Exemplo não é regra: «índice médio de invisibilidade da sala (ex.: 73%)» no painel do handoff da exp06ef1b.
_RE_EXEMPLO = re.compile(r"\(\s*(?:ex\.|exemplo|e\.g\.|por exemplo)[^)\n]*\)", re.I)
#: Estatística de fonte externa citada como contexto: «Pesquisas do CETIC.br (TIC Kids Online Brasil 2024) apontam que
#: … menos de 15% compreendem…» no §1 do PRD da exp06ef1b-727a3c2d (24/10/2026) é dado do mundo, não regra da missão.
#: Só a porcentagem: a duração ou o teto na mesma linha continuam pedindo origem.
_RE_FONTE_EXTERNA = re.compile(r"\b(?:CETIC|TIC Kids|IBGE|PNAD|INEP|SAEB|PISA|OCDE|OECD|UNICEF|UNESCO|Datafolha)\b")
#: A nota de acessibilidade medida por ferramenta é da casca: «Lighthouse Accessibility Score ≥ 98%» no RNF do PRD da
#: exp04ef1b-8ce9c32d (24/10/2026). Também só a porcentagem: o tempo de uma mecânica que cita a WCAG («ajustável, WCAG
#: 2.2.1») continua sendo decisão de produto.
_RE_FERRAMENTA_DE_ACESSIBILIDADE = re.compile(r"Lighthouse|\bWCAG\b|axe-core", re.I)
#: O recorte da aula do E0-PROF é o contrato de customização da plataforma, o mesmo em toda missão
#: (`references/formato-spec.md`: `tema` ≤ 60, `assuntos` ≤ 600, `contexto` e `foco` ≤ 120 caracteres): os «máx. 60 /
#: 600 caracteres» do handoff da exp04ef1b-8ce9c32d (24/10/2026). Só esses números, na linha que fala do recorte: outro
#: teto de caracteres para o mesmo campo continua pedindo origem.
_RE_RECORTE_DA_AULA = re.compile(r"disciplina|\btema\b|assuntos|t[óo]picos|contexto|recorte da aula|E0-PROF", re.I)
_LIMITES_DO_RECORTE = frozenset({"60", "600", "120"})
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
    """Os números de regra da linha, fora de citação, de código em linha e de exemplo «(ex.: …)»: %, s, min e palavras
    ou caracteres que um teto ou piso rege — sem os de plataforma, de layout, a estatística externa, a nota de
    acessibilidade, os limites do recorte da aula e o 100%, que é «todos». Contagens de opção vêm à parte."""
    if de_plataforma(linha):
        return []
    limpa = _RE_EXEMPLO.sub(" ", _RE_CITACAO.sub(" ", linha))
    saida = []
    for n, u in numeros(limpa):
        if u == "px" or float(n) == 0 or (u == "%" and float(n) == 100):
            continue
        if u == "%" and (_RE_LAYOUT.search(limpa) or _RE_FONTE_EXTERNA.search(linha)
                         or _RE_FERRAMENTA_DE_ACESSIBILIDADE.search(linha)):
            continue
        if u in ("palavras", "caracteres") and not _teto_rege(limpa, (n, u)):
            continue
        if u == "caracteres" and n in _LIMITES_DO_RECORTE and _RE_RECORTE_DA_AULA.search(linha):
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
        if de_plataforma(linha) or _RE_FORMULARIO_DO_PREPARO.search(linha):
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


def hipoteses_e_tetos(one_pager: str, corpo: str, exigir_tetos: bool = True, spec: str = "",
                      contrato_texto: Optional[str] = None) -> List[Dict[str, str]]:
    """Números do §17 trocados no corpo e, com `exigir_tetos`, os do §15 ausentes ou trocados (régua do PR 1,
    `propagacao.contrato_no_corpo`). Todo item bloqueia: o corpo diz o que o one-pager diz, mesmo quando o próprio
    contrato diverge — aí a seção de pendências registra a divergência *além* do corpo certo
    (`divergencias_do_contrato`), nunca no lugar dele. Até a revisão de 23/10/2026, o registro na §19 tirava o item
    daqui, e a H1 com 25% no corpo da exp02ef1b passava como 🟡 com uma linha só.

    O handoff não repete os tetos nem as hipóteses (remete ao §17): nele só conta o trocado. A hipótese é comparada
    também item a item (`hipoteses_reescritas`): o handoff da exp02ef1b parafraseou a H1 inteira com 25%, e a linha
    não casava por palavras com a do §17.

    Com `spec`, o item que não é divergência certa sai como dúvida (`situacao` `limiar-do-9f` ou `complemento`, ver
    `hipoteses_reescritas`): o gate o mostra como atenção, não bloqueia."""
    corpo = "\n".join(_linhas_do_corpo(corpo))
    candidatos = [c for c in contrato_no_corpo(one_pager, corpo, secoes=(15, 17))
                  # a hipótese ausente do corpo não é número trocado: o PRD remete ao anexo, e o handoff ao §17
                  if not (c["situacao"] == "ausente" and (c["secao"] == "§17" or not exigir_tetos))]
    vistos = {(c["secao"], c["contrato"], c["corpo"]) for c in candidatos}
    for h in hipoteses_reescritas(one_pager, corpo, spec, contrato_texto):
        if h["situacao"] in SITUACOES_DE_DUVIDA:
            # a mesma troca que a régua de linha acusou (o corpo copiou a frase do §17 com o limiar da PQ): quem decide
            # é a leitura por hipótese, que sabe da pergunta citada — senão a dúvida sumia atrás de um bloqueio
            mesma = [c for c in candidatos if c["secao"] == "§17" and c["situacao"] == "trocado" and "hipotese" not in c
                     and c["contrato"] in h["contrato"].split(", ") and c["corpo"] == h["corpo"]]
            candidatos = [c for c in candidatos if c not in mesma]
            vistos -= {(c["secao"], c["contrato"], c["corpo"]) for c in mesma}
        if not any(c["secao"] == "§17" and set(h["corpo"].split(", ")) <= set(c["corpo"].split(", "))
                   for c in candidatos) and (h["secao"], h["contrato"], h["corpo"]) not in vistos:
            candidatos.append(h)
    return candidatos


#: Linha de tabela com marcador aberto: o número de qualquer célula dela é proposta, não contrato. A PQ-01 da exp02ef1b
#: trazia «>25% → …» numa célula e `[PROPOSTA — validar com PO]` na última — os 25% eram proposta (D11), e a limpeza
#: só de dentro dos colchetes os deixava contar como origem da H1 com 25%.
_RE_MARCADOR_ABERTO_NA_LINHA = re.compile(r"\[(?:PAR[ÂA]METRO|PROPOSTA)\b", re.I)


#: Fora de tabela, `[PROPOSTA …]` marca o item inteiro como proposta («- *Indica falha:* Mais de 25% das duplas …
#: `[PROPOSTA — validar com PO]`»); `[PARÂMETRO …]` marca só o valor dentro dos colchetes («Mais de [PARÂMETRO — a
#: definir: limiar, sugestão: 25%] das duplas»). Revisão do PR #71 (23/10/2026): só a linha de tabela saía, e o item
#: de lista com a proposta virava divergência do contrato — o formato está em 17 itens de lista do acervo, como a
#: «[PROPOSTA P0b — validar com PO: … máx. 45 palavras…]» da exp01em1b-e3980485.
_RE_PROPOSTA_NA_LINHA = re.compile(r"\[PROPOSTA\b", re.I)


def sem_linhas_abertas(texto: str) -> str:
    """O texto sem o que é proposta: a linha de tabela com `[PROPOSTA …]` ou `[PARÂMETRO …]` aberto, a linha fora de
    tabela com `[PROPOSTA …]`, e o conteúdo de `[PARÂMETRO …]` nas demais."""
    saida = []
    for l in (texto or "").splitlines():
        if not _RE_MARCADOR_ABERTO_NA_LINHA.search(l):
            saida.append(l)
        elif l.count("|") < 2 and not _RE_PROPOSTA_NA_LINHA.search(l):
            saida.append(_RE_MARCADOR_ABERTO.sub(" ", l))
    return "\n".join(saida)


def _faixa_do_contrato(linha_contrato: str, tok: Tuple[str, str]) -> bool:
    """O número da spec aparece solto na linha do one-pager — «máximo de 8 a 10 palavras» no §15 da exp03ef1b, e a
    spec escolheu 8: é detalhe dentro da faixa, não divergência."""
    n = tok[0].replace(".", "[.,]")
    return bool(re.search(rf"(?<![\d.,]){n}(?![\d.,]|\d)", linha_contrato or ""))


def divergencias_do_contrato(one_pager: str, spec: str) -> List[Dict[str, str]]:
    """Onde o próprio contrato diverge, na origem certa: a linha correspondente da spec de produto (régua de linha do
    PR 1) com outro número para o §15 ou o §17, e a linha do 9f que cita a hipótese (`H1`, «Hipótese 1») com
    porcentagem que a hipótese de mesmo número do §17 não tem. O que é proposta não conta (`sem_linhas_abertas`).
    Independe do corpo — com o corpo já certo, a divergência continua do PO, e a seção de pendências a registra com os
    dois valores."""
    from tools.conteudo_aprovado import secao

    spec_firme = sem_linhas_abertas(spec)
    saida: List[Dict[str, str]] = []
    for c in contrato_no_corpo(one_pager, spec_firme, secoes=(15, 17)):
        if c["situacao"] != "trocado":
            continue
        outros = [_tok(x.strip()) for x in c["corpo"].split(",")]
        if all(_faixa_do_contrato(c["linha"], t) for t in outros):
            continue
        saida.append({"secao": c["secao"], "contrato": c["contrato"], "outro": c["corpo"], "onde": "a spec",
                      "linha": c["linha"], "linha_outra": c["linha_corpo"]})
    do_17 = _itens_de_hipotese(secao(one_pager or "", 17) or "")
    for pq, linha in _linhas_9f(spec_firme).items():
        for n, texto in do_17.items():
            if not re.search(rf"\bH0*{n}\b|hip[óo]tese\s+0*{n}\b", linha, re.I):
                continue
            da_h = [t for t in _numeros_de_hipotese(texto) if t[1] == "%"]
            outros = [t for t in _numeros_de_hipotese(linha) if t[1] == "%" and not tem_numero(texto, t)]
            if da_h and outros:
                saida.append({"secao": "§17", "contrato": ", ".join(_fmt(t) for t in da_h),
                              "outro": ", ".join(_fmt(t) for t in outros), "onde": f"o 9f da spec ({pq})",
                              "linha": texto.strip().splitlines()[0][:200], "linha_outra": linha[:200]})
    return saida


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


#: O comparativo da meta, logo antes da porcentagem: «mais de 25%», «superar 25%», «maior que 25%», «a partir de 25%»…
#: (`_RE_MAIS`), «menos de 60%», «abaixo de 60%», «no máximo 60%»… (`_RE_MENOS`). Logo depois: «25% ou mais».
_RE_MAIS = (r"(?:\b(?:mais\s+(?:de|que|do\s+que)|acima\s+de|superior(?:es)?\s+a|maior(?:es)?\s+(?:do\s+)?que|"
            r"igual\s+ou\s+(?:superior|maior)\s+(?:a|que)|a\s+partir\s+de|pelo\s+menos|ao\s+menos|no\s+m[íi]nimo|"
            r"super(?:ar|arem|a|am|e|em)|ultrapass(?:ar|arem|a|am|e|em)|exced(?:er|erem|e|em|a|am)|"
            r"pass(?:ar|arem|a|am|e|em)\s+de)\b|>=?|≥)")
_RE_MENOS = (r"(?:\b(?:menos\s+(?:de|que|do\s+que)|abaixo\s+de|inferior(?:es)?\s+a|menor(?:es)?\s+(?:do\s+)?que|"
             r"igual\s+ou\s+(?:inferior|menor)\s+(?:a|que)|no\s+m[áa]ximo|at[ée])(?!\w)|<=?|≤)")
_RE_COMPARATIVO_ANTES = re.compile(rf"(?:{_RE_MAIS}|{_RE_MENOS}|entre)\s*~?\s*$", re.I)
_RE_COMPARATIVO_DEPOIS = re.compile(r"^\s*ou\s+(mais|menos)\b", re.I)
_RE_POPULACAO_DEPOIS = re.compile(r"^\s*(?:ou\s+(?:mais|menos)\s+)?d[aeo]s?\s+(?:estudantes|alun[oa]s|turmas?|duplas|"
                                  r"crian[çc]as|jurados|conselheiros|professor(?:es|as)|participantes|grupos|equipes|"
                                  r"jovens|respondentes|usu[áa]rios|sala)\b", re.I)
#: A porcentagem da mecânica vem marcada como tal, sem comparativo: «taxa real de ~75% de invisibilidade» do PRD e «a
#: taxa de 75% da Galeria Oculta» do handoff da exp06ef1b eram os 12 de 16 projetos ocultos, não meta da H2 (análise de
#: 24/10/2026). «taxa de desistência de 25%» não é esse caso: a taxa ali é a medida da hipótese. O «~» solto não marca
#: nada (revisão do PR #77, 24/10/2026: «Se a desistência chegar a ~25%» tirava a H1 30×25 da exp02ef1b do gate).
_RE_MECANICA_ANTES = re.compile(r"\btaxa\s+(?:real\s+)?de\s*~?\s*$", re.I)


def _contrato_da_mecanica(contrato_texto: str) -> str:
    """O contrato sem o §17 (as metas) e sem as linhas de tabela com `PQ-nn` (os limiares do 9f): onde a porcentagem
    marcada como mecânica tem de estar para não ser meta. Os 75% da exp06ef1b estão na conta da invisibilidade do
    one-pager e da spec; os 25% da exp02ef1b, só no limiar da PQ-01 — «a taxa de 25% de desistência» é a meta."""
    from tools.kpis import _RE_PQ

    saida: List[str] = []
    nivel: Optional[int] = None
    for linha in (contrato_texto or "").splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)$", linha)
        if m:
            if nivel is not None and len(m.group(1)) <= nivel:
                nivel = None
            if nivel is None and re.match(r"^(?:§\s*)?17\s*(?:\.(?![\dA-Za-z])|[—–-])", m.group(2).strip("*_ ")):
                nivel = len(m.group(1))
                continue
        if nivel is None and not ("|" in linha and _RE_PQ.search(linha)):
            saida.append(linha)
    return "\n".join(saida)


def _metas_do_corpo(texto: str, mecanica: str = "") -> List[Tuple[str, str]]:
    """Os números de hipótese do corpo que podem ser meta: a duração (s, min) e toda porcentagem, menos a que vem
    marcada como mecânica (`_RE_MECANICA_ANTES`) sem comparativo nem população e que o contrato tem fora do §17 e do
    9f (`mecanica`, de `_contrato_da_mecanica`). Sem o contrato, a marca não basta: a porcentagem é meta.

    Revisão do PR #77 (24/10/2026): a leitura pedia o comparativo de uma lista curta ou a população, e fora disso a
    porcentagem sumia em silêncio — «Se a desistência das duplas superar 25%», «25% ou mais das duplas», «maior que
    25%» tiravam do gate a H1 30×25 da exp02ef1b (D11). O lado conservador é o contrário: só sai a marcada. Na segunda
    revisão, a marca sozinha ainda tirava «Se a taxa de 25% de desistência for atingida»: a mecânica é a do contrato."""
    limpo = _RE_CITACAO.sub(" ", texto or "").replace("$", "").replace("\\%", "%").replace("\\ge", "≥").replace(
        "\\le", "≤")
    saida = []
    for t in _numeros_de_hipotese(limpo):
        if t[1] == "%" and tem_numero(mecanica, t):
            num = re.escape(t[0]).replace(r"\.", "[.,]")
            ocorrencias = list(re.finditer(rf"(?<![\w.,]){num}\s?%", limpo))
            if ocorrencias and all(
                    _RE_MECANICA_ANTES.search(limpo[max(0, m.start() - 25):m.start()])
                    and not _RE_COMPARATIVO_ANTES.search(limpo[max(0, m.start() - 25):m.start()])
                    and not _RE_COMPARATIVO_DEPOIS.match(limpo[m.end():m.end() + 20])
                    and not _RE_POPULACAO_DEPOIS.match(limpo[m.end():m.end() + 40])
                    for m in ocorrencias):
                continue
        saida.append(t)
    return saida


#: Palavras de qualquer hipótese: não dizem se duas hipóteses falam da mesma coisa.
_GENERICAS_DE_HIPOTESE = frozenset("""estudante estudantes aluno alunos alunas turma turmas crianca criancas dupla
duplas jurado jurados conselheiro conselheiros hipotese eficacia falha indica observar etapa assume proporcao
percentual quantos quantas antes depois durante menos""".split())


def _radicais(texto: str) -> Set[str]:
    from tools.propagacao import _palavras

    texto = re.sub(r"\bPQ-?\d+\b|\bH\d+\b", " ", _RE_CITACAO.sub(" ", texto or ""))
    return {p[:5] for p in _palavras(texto) if len(p) >= 5 and p not in _GENERICAS_DE_HIPOTESE}


def _mesma_hipotese(a: str, b: str) -> bool:
    """As duas falam da mesma coisa: 3 radicais de conteúdo em comum. A H1 do handoff da exp06ef1b-727a3c2d e a do §17
    têm 7 («afuni», «curte», «posts»…); a H3, trocada por «Adoção da Busca Ativa», tem 1 («bolha»)."""
    return len(_radicais(a) & _radicais(b)) >= 3


def _direcao(texto: str, tok: Tuple[str, str]) -> str:
    """`mais` ou `menos`: o comparativo logo antes da porcentagem («superar 25%», «menos de 60%») ou logo depois
    («25% ou mais»); vazio sem comparativo."""
    num = re.escape(tok[0]).replace(r"\.", "[.,]")
    m = re.search(rf"({_RE_MAIS}|{_RE_MENOS})\s*~?\s*{num}\s?%", texto or "", re.I)
    if m:
        return "mais" if re.fullmatch(_RE_MAIS, m.group(1), re.I) else "menos"
    m = re.search(rf"(?<![\w.,]){num}\s?%\s*ou\s+(mais|menos)\b", texto or "", re.I)
    return m.group(1).lower() if m else ""


#: Situações de `hipoteses_reescritas` que são dúvida, não divergência certa: saem como `hipotese-a-conferir`, atenção.
SITUACOES_DE_DUVIDA = ("limiar-do-9f", "complemento")


def hipoteses_reescritas(one_pager: str, corpo: str, spec: str = "",
                         contrato_texto: Optional[str] = None) -> List[Dict[str, str]]:
    """Hipótese do corpo com número que a hipótese de mesmo número do §17 não tem: `trocado` quando a do §17 tem
    outro número da mesma unidade (H1: 30% no §17, 25% no handoff da exp02ef1b), `acrescentado` quando ela não
    quantifica e o corpo inventou a meta (H2 do mesmo handoff: «menos de 70%»).

    Análise de 24/10/2026 (7 execuções de dev vistas pelo PO), o que deixou de ser divergência certa:
    - porcentagem marcada como mecânica («taxa real de ~75%») não é meta (`_metas_do_corpo`) — qualquer outra é, com
      qualquer redação do comparativo; duração que o §17 não quantifica e que o contrato tem é
      parâmetro da mecânica citado («retenção >5s», «zoom-out de 2,5s», PRDs da exp06ef1b e da exp01ef1b) — a que o
      contrato não tem continua meta inventada («`tempo_feed_segundos` < 180s» na H1 do PRD da exp05ef1b);
    - `limiar-do-9f` (dúvida): o número é o limiar da `PQ-nn` que a própria hipótese cita, numa linha firme do 9f (sem
      `[PROPOSTA]`), e a hipótese fala da mesma coisa que a do §17 — meta do §17 (85%) × limiar da PQ-01 (80%) no
      handoff da exp06ef1b-727a3c2d. A H3 do mesmo handoff, que trocou a hipótese inteira, continua `trocado`;
    - `complemento` (dúvida): 100 − x com o comparativo invertido — «mais de 40% parearem pela cor» no §17 e «menos de
      60% … com a justificativa correta» no handoff da exp02ef1b. Só é a mesma regra se ninguém ficar fora dos dois."""
    from tools.conteudo_aprovado import secao
    from tools.kpis import _RE_PQ, _pq_id

    do_17 = _itens_de_hipotese(secao(one_pager or "", 17) or "")
    do_corpo = _itens_de_hipotese(_secoes_de_hipotese(corpo))
    nove_f = _linhas_9f(sem_linhas_abertas(spec)) if spec else {}
    mecanica = _contrato_da_mecanica(contrato_texto or "")
    saida = []
    for n, texto in do_corpo.items():
        if n not in do_17:
            continue
        aprovados = _numeros_de_hipotese(do_17[n])
        unidades = {u for _, u in aprovados}
        fora = [t for t in _metas_do_corpo(texto, mecanica) if not tem_numero(do_17[n], t)
                and (t[1] == "%" or t[1] in unidades or contrato_texto is None or not tem_numero(contrato_texto, t))]
        if not fora:
            continue
        mesma_unidade = [t for t in aprovados if t[1] in {u for _, u in fora}]
        situacao, pq = ("trocado" if mesma_unidade else "acrescentado"), ""
        citadas = [_pq_id(x) for x in _RE_PQ.findall(texto) if _pq_id(x) in nove_f]
        do_9f = {p: _pct(nove_f[p]) for p in citadas}
        # só quando o §17 quantifica a hipótese: sem meta no §17, o número do corpo continua `acrescentado`
        if mesma_unidade and all(t[1] == "%" for t in fora) and _mesma_hipotese(do_17[n], texto):
            pq = next((p for p in citadas if all(t[0] in do_9f[p] for t in fora)), "")
            if pq:
                situacao = "limiar-do-9f"
            elif all(any(abs(float(t[0]) + float(a[0]) - 100) < 1e-9 and a[1] == "%"
                         and {_direcao(texto, t), _direcao(do_17[n], a)} == {"mais", "menos"} for a in aprovados)
                     for t in fora):
                situacao = "complemento"
        linha_corpo = next((l for l in texto.splitlines() if any(tem_numero(l, t) for t in fora)), texto)
        saida.append({"secao": "§17", "situacao": situacao, "pq": pq,
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
#: Atribuição de produto ao lado de um [D0-n]: o D0 é decisão do design (do anexo de design; até o PR 6, do bloco 13
#: dentro da spec).
_RE_ATRIBUI_PRODUTO = re.compile(
    r"contratua(?:l|is)|decis[ãa]o\s+(?:do|de)\s+(?:PO|produto)|(?:aprovad|ratificad|homologad|decidid)[oa]s?\s+pel[oa]\s+PO|"
    r"produto/00|one[- ]?pager|n[úu]cleo", re.I)
#: O bloco 13 e o 14 são do design — no anexo (`design/00-anexo-design-spec.md`) desde o PR 6, e em
#: `produto/05-spec-missao.md` na missão anterior: citá-los é legítimo.
_RE_BLOCO_DO_DESIGN = re.compile(r"bloco\s*1[34]\b|›\s*bloco\s*1[34]|anexo\s+de\s+design|00-anexo-design-spec", re.I)


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
            f"produto, decisões da lista branca do bloco 13, decisões do PO no de acordo e nos pedidos de refazer): "
            + _exemplos(f"{i['numero']} em «{i['linha'][:110]}»" for i in sem_origem)
            + f". O {rotulo} monta, não decide: copie o número do contrato, tire-o, ou marque a linha "
            "`[PROPOSTA — validar com PO: <o número> · por quê]` (ela vai para a seção 19.3). Polling, TTL, p95 e o que "
            "mais for da plataforma não precisam de origem no contrato.", documento))

    # b) hipóteses, tetos e metas — o corpo trocado bloqueia sempre; a divergência do próprio contrato, na origem
    # certa, pede o registro na seção de pendências além do corpo certo
    divergentes = hipoteses_e_tetos(one_pager, corpo, exigir_tetos=(documento == "prd"), spec=spec,
                                    contrato_texto=contrato_texto)
    do_contrato = divergencias_do_contrato(one_pager, spec)
    for c in divergentes:
        if c["secao"] == "§17":
            codigo, o_que = "hipotese-diverge", "hipótese"
        else:
            codigo, o_que = ("teto-ausente", "teto") if c["situacao"] == "ausente" else ("teto-diverge", "teto")
        # dúvida, não divergência certa: atenção, separada do bloqueio pelo código (análise de 24/10/2026)
        if c["situacao"] in SITUACOES_DE_DUVIDA:
            if c["situacao"] == "limiar-do-9f":
                por_que = (f"que é o limiar da {c['pq']} no 9f da spec — a pergunta que a própria hipótese cita, "
                           "numa linha firme do contrato. Meta da hipótese e limiar de decisão da pergunta não são a "
                           "mesma grandeza")
            else:
                por_que = ("o complemento do número do §17 com o comparativo invertido. Só é a mesma regra se ninguém "
                           "ficar fora dos dois lados (quem não conclui conta como falha num e não no outro)")
            achados.append(_achado(
                "hipotese-a-conferir",
                f"Dúvida, não divergência certa: a {c['hipotese']} do §17 do one-pager tem {c['contrato']}, e o "
                f"{rotulo} escreve {c['corpo']}, {por_que}: «{c['linha_corpo'][:140]}». Confira com o PO antes do de "
                "acordo; o seguro é copiar o §17" + (" (ou remeter a ele)" if documento == "handoff" else "")
                + (f" e citar o limiar da {c['pq']} à parte." if c["pq"] else "."), documento, severidade="atencao"))
            continue
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
            origem = next((d for d in do_contrato if d["secao"] == c["secao"] and d["contrato"] == c["contrato"]
                           and set(c["corpo"].split(", ")) <= set(d["outro"].split(", "))), None)
            if origem:
                resumo += (f" O {c['corpo']} é o que {origem['onde']} diz: a divergência é do próprio contrato e não "
                           f"se decide aqui — o corpo segue o one-pager ({c['contrato']}) e, além disso, a "
                           f"{pendencias_rotulo} a registra com dono produto.")
        else:
            resumo = (f"O {rotulo} não traz o teto do {c['secao']} do one-pager ({c['contrato']}): «{c['linha'][:140]}». "
                      "Teto da faixa é requisito de quem codifica: leve-o ao RNF e à story das telas que ele limita.")
        achados.append(_achado(codigo, resumo, documento))
    registradas: List[Dict[str, str]] = []
    for d in do_contrato:
        toks = [_tok(x.strip()) for x in d["contrato"].split(",")] + [_tok(x.strip()) for x in d["outro"].split(",")]
        linha = _registro(pendencias, *toks)
        if linha:
            registradas.append({**d, "registro": linha[:180]})
            achados.append(_achado(
                "divergencia-registrada",
                f"O {d['secao']} do one-pager diz {d['contrato']} e {d['onde']} diz {d['outro']}: está registrado na "
                f"{pendencias_rotulo} com dono produto («{linha[:120]}»). É pendência do PO, e o rastro a conta.",
                documento, severidade="atencao", etapa="produto"))
        else:
            achados.append(_achado(
                "divergencia-do-contrato-sem-registro",
                f"O próprio contrato diverge: o {d['secao']} do one-pager diz {d['contrato']} («{d['linha'][:110]}») e "
                f"{d['onde']} diz {d['outro']} («{d['linha_outra'][:110]}»). Não se decide no {rotulo}: o corpo segue "
                f"o one-pager e a {pendencias_rotulo} registra `[ABERTO — dono: produto: o {d['secao']} diz "
                f"{d['contrato']} e {d['onde']} diz {d['outro']}]`, com os dois valores.", documento))
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
                         "divergencias_do_contrato": len(do_contrato),
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
    # divergência certa e dúvida em blocos separados, para o PO e para o retrabalho: das 7 execuções de dev vistas pelo
    # PO até 23/10/2026, todas saíram 🔴 com acerto e ruído na mesma lista (análise de 24/10/2026)
    certas = [a for a in resultado["achados"] if a["severidade"] == "bloqueio"]
    duvidas = [a for a in resultado["achados"] if a["severidade"] != "bloqueio"]
    if certas and duvidas:
        L.append("**Divergência certa — bloqueia; o redator corrige:**")
    L += [f"- ⛔ `{a['codigo']}` — {a['resumo']}" for a in certas]
    if certas and duvidas:
        L += ["", "**Dúvida ou registro — não bloqueia; o PO confere antes do de acordo:**"]
    L += [f"- ⚠️ `{a['codigo']}` — {a['resumo']}" for a in duvidas]
    envelope = {"agente": AGENTE, "missao": missao or "", "status": resultado["status"],
                "achados": [{"severidade": a["severidade"], "classe": "montagem", "codigo": a["codigo"],
                             "agente_responsavel": a["agente_responsavel"], "resumo": a["resumo"]}
                            for a in resultado["achados"]],
                "precisa_humano": False}
    return "\n".join(L) + "\n\n```json\n" + json.dumps(envelope, ensure_ascii=False) + "\n```\n"
