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
   gravadas no de acordo (`estado.decisoes_do_po`, PR 3), o lado «para» das trocas da correção pontual de design ou
   dev (`edicoes_pontuais`) e o teto de palavras da faixa da missão — o pedido do PO em prosa livre não é origem. Ficam
   de fora os de dono plataforma (polling, TTL, p95, uptime, lote da SDK, `px`), a duração da espera de carregamento,
   a medida de layout (`75% da tela`), a medida de uma string que nenhum teto rege, o
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

from tools.severidade import BLOQUEIO, CONCORDAM_NAO, CONCORDAM_SIM, DUVIDA, INTERPRETACAO, leitura_dupla, por_prova
from tools.propagacao import (
    _ALIAS,
    _fmt,
    bloco_13,
    contrato_no_corpo,
    numeros,
    sem_latex,
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


#: Documentos de produto: a troca de uma correção pontual de produto já está no one-pager e na spec, que são o
#: contrato; e a de uma correção de produto antiga, que outra desfez, não pode continuar valendo como origem.
_DOCUMENTOS_DE_PRODUTO = frozenset({"nucleo_narrativo", "one_pager", "spec_missao", "one_pager_resumido"})


def _texto_das_trocas_da_correcao(state: Dict[str, Any]) -> str:
    """Os números que a correção pontual de design ou de dev trocou a pedido do PO (`edicoes_pontuais`,
    `tools/edicao_pontual.py`): o lado «para» de cada troca, só o número que o «de» não tinha — o que a troca trouxe,
    não o que ela só repete. Vale na correção pontual em curso (`modo_correcao`), como lêem as trocas os outros gates.

    O pedido do PO em prosa livre deixou de ser origem de número (terceira revisão do PR #77, 24/10/2026): ler intenção
    em linguagem natural por regex errava a cada ajuste — «Não aceito o limiar de 80%», «O KPI-08 não pode ter 80%»
    faziam origem do 80% inventado do KPI-08 da exp02ef1b, e «Trocar 80% por 70%», «Mudar de 80% para 70%» não davam o
    70%. Desde o PR 5 (#72), o pedido feito em design ou dev que muda número passa pela triagem
    (`tools/triagem_pedido.py`) e vai a produto, que o grava no one-pager e na spec; o de acordo grava as decisões em
    `decisoes_do_po` (PR 3, #70). Origem é o que está escrito em estrutura: o contrato, as decisões e as trocas."""
    from tools.edicao_pontual import MODO_PONTUAL

    # `agents.callbacks.KEY_MODO_CORRECAO`, lido pela chave para o gate não importar o ADK
    if state.get("modo_correcao") != MODO_PONTUAL:
        return ""
    valores: List[Tuple[str, str]] = []
    for e in state.get("edicoes_pontuais") or []:
        if not isinstance(e, dict) or str(e.get("documento") or "") in _DOCUMENTOS_DE_PRODUTO:
            continue
        antes = numeros(str(e.get("de") or ""))
        valores += [t for t in numeros(str(e.get("para") or "")) if t not in antes and t not in valores]
    return "\n".join(f"{_fmt(v)} — troca da correção pontual" for v in valores)


#: Fontes do contrato que são decisão do PO sobre o documento, não o texto do contrato: valem como origem de número,
#: nunca como a mecânica da hipótese (`_contrato_da_mecanica`) — a decisão não diz que um número é parâmetro da
#: mecânica e não meta (revisão do PR #77, 24/10/2026: o pedido «A H1 não pode ter 25%» tirava do gate a H1 30×25 da
#: exp02ef1b, porque o 25% do pedido entrava na mecânica).
_FONTES_DE_DECISAO = ("decisoes_do_po", "trocas_da_correcao")


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
    design; `decisoes_do_po` o que o PO fixou no de acordo; `trocas_da_correcao` o que a correção pontual de design ou
    de dev trocou a pedido dele; `teto_da_faixa` o padrão de palavras por frase da faixa. O pedido em prosa livre não
    entra (`_texto_das_trocas_da_correcao`)."""
    docs = {k: str(state.get(k) or "") for k in FONTES_DO_CONTRATO}
    docs["spec_produto"] = spec_de_produto(str(state.get("spec_missao") or ""))
    docs["bloco_13"], _ = bloco_13_da_lista_branca(state)
    docs["decisoes_do_po"] = _texto_das_decisoes_do_po(state.get("decisoes_do_po"))
    docs["trocas_da_correcao"] = _texto_das_trocas_da_correcao(state)
    docs["teto_da_faixa"] = _teto_da_faixa(state)
    docs["perguntas_transversais"] = perguntas_transversais()
    docs["copy_aprovada"] = _texto_da_copy_revisada(str(state.get("copy_strings_revisada") or ""))
    docs["parametros_configuraveis"] = _sugestoes_de_parametros_abertos_com_pend(state)
    return docs


def _texto_da_copy_revisada(copy_md: str) -> str:
    """Os textos de interface da `copy_strings_revisada` (sem a coluna de contagem de palavras): quando o PRD ou o
    handoff citam sem aspas uma frase literal da copy («Restam 30 segundos para concluir»), o número vem da copy."""
    linhas = []
    for l in (copy_md or "").splitlines():
        if l.strip().startswith("|"):
            celulas = [c.strip() for c in l.strip().strip("|").split("|")]
            # pula a última coluna quando é só o inteiro da contagem de palavras
            if len(celulas) >= 3 and re.fullmatch(r"\d+", celulas[-1]):
                celulas = celulas[:-1]
            linhas.append(" | ".join(celulas))
    return "\n".join(linhas)


def _sugestoes_de_parametros_abertos_com_pend(state: Dict[str, Any]) -> str:
    """Decisão 4 (25/10/2026): quando não houve de acordo humano para fechar um `[PARÂMETRO — … sugestão: X]` da spec,
    o PRD pode adotar a sugestão `X` como constante configurável desde que registre a pendência (`PEND` / `[PARÂMETRO` /
    `[ABERTO`) na seção 19 (ou seção 7 do handoff)."""
    spec_raw = str(state.get("spec_missao") or "")
    prd_ou_handoff = str(state.get("prd_final") or "") + "\n" + str(state.get("handoff_dev") or "")
    if not re.search(r"\bPEND-\d+\b|\[(?:PAR[ÂA]METRO|ABERTO)\b|constante\s+configur[áa]vel", prd_ou_handoff, re.I):
        return ""
    sugestoes = re.findall(r"\[PAR[ÂA]METRO\b[^\]\n]*?sugest[ãa]o\s*:\s*([^\]\n]+)\]", spec_raw, re.I)
    return "\n".join(sugestoes)


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
    r"\b\d+\s*FPS\b|taxa de quadros|queda de frame|falhas?\s+t[ée]cnicas?|"
    r"amostragem|batch|retry|backoff|RNF-(?:PERF|DISP|SEG)|"
    r"F5\b|recarreg|reconex|Cloud ?Run|\bCDN\b|bundle|\bKB\b|\bMB\b|throttl|debounce|quota|cota de IA|"
    # consulta periódica a uma rota é polling com outro nome («consultando `GET /juri-estadual/gate` a cada 3
    # segundos», PRD da exp06ef1b)
    r"\bGET\s+/|"
    # a origem declarada é a plataforma: «(contrato da plataforma)», «(ADR-105)»
    r"\bADR-\d|contrato da plataforma|\(plataforma\)", re.I)
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
)


def de_plataforma(linha: str) -> bool:
    """A linha fala de infraestrutura: termo inequívoco, ou termo ambíguo com o contexto técnico ao lado."""
    if _RE_PLATAFORMA.search(linha or ""):
        return True
    return any(termo.search(linha or "") and contexto.search(linha or "") for termo, contexto in _PLATAFORMA_COM_CONTEXTO)


#: A espera do carregamento é da casca: a duração dela não é regra da missão — a «barra de progresso contínua com
#: estimativa tranquilizadora de 10 a 20 segundos» da geração por IA (handoff da exp06ef1b-727a3c2d, 24/10/2026). Sai só
#: a duração, na mesma oração. Revisão do PR #77 (24/10/2026): spinner, skeleton e a barra de progresso tiravam a linha
#: inteira, e «ao atingir ≥ 60% de submissões» na linha da barra (a Pausa 1 da exp07ef1b), «a dica aparece após 25
#: segundos» depois de «Skeleton da galeria;» deixavam de pedir origem. A barra ou o indicador de progresso só é espera
#: com carregamento, geração, IA, espera ou estimativa na oração: a barra do tempo da rodada é a mecânica.
_RE_ESPERA = re.compile(r"spinner|skeleton", re.I)
_RE_PROGRESSO = re.compile(r"barra de progresso|indicador de progresso", re.I)
_RE_CONTEXTO_DE_ESPERA = re.compile(r"carreg|gera[çc][ãa]o|gerando|\bIA\b|\bespera\b|aguard|estimativ", re.I)
#: A oração da duração: entre ponto e vírgula, vírgula, célula de tabela e fim de frase.
_RE_FRONTEIRA_DA_ESPERA = re.compile(r"[;,|]|(?<=[.!?])\s")


def _duracao_de_espera(linha: str, tok: Tuple[str, str]) -> bool:
    """Alguma ocorrência da duração está numa oração de espera de carregamento: spinner, skeleton, ou barra/indicador
    de progresso com o contexto da espera."""
    num = re.escape(tok[0]).replace(r"\.", "[.,]")
    unidade = "|".join(re.escape(a) for a in _ALIAS[tok[1]])
    for m in re.finditer(rf"(?<![\w.,]){num}\s?(?:{unidade})\b", linha or "", re.I):
        antes = list(_RE_FRONTEIRA_DA_ESPERA.finditer(linha, 0, m.start()))
        depois = _RE_FRONTEIRA_DA_ESPERA.search(linha, m.end())
        oracao = linha[antes[-1].end() if antes else 0:depois.start() if depois else len(linha)]
        if _RE_ESPERA.search(oracao) or (_RE_PROGRESSO.search(oracao) and _RE_CONTEXTO_DE_ESPERA.search(oracao)):
            return True
    return False


#: Porcentagem de layout: o que a tela ocupa é desenho (a folha de 75% e o overlay de 70% da exp02ef1b). A área mínima
#: da moldura não entra aqui: os 10% da exp02ef1b são regra da mecânica, que o D0 decidiu no lugar do PO.
_RE_LAYOUT = re.compile(r"viewport|altura|largura|overlay|opacidade|cobr[ie]|ocupa|\bfolha\b|modal|drawer|"
                        r"sheet", re.I)
#: Palavras e caracteres só são regra quando a linha diz teto ou piso; «(13 palavras)» ao lado de uma string é medida.
_RE_TETO_OU_PISO = re.compile(r"m[áa]x|teto|limite|\bat[ée]\b|≤|<=|n[ãa]o (?:pode|deve)|exced|ultrapass|passa de|m[íi]nim|piso|≥|"
                              r">=|pelo menos|no m[íi]nimo", re.I)
#: E o teto ou o piso tem de reger aquele número: vir antes dele, na mesma oração. Bastava a linha dizer «teto» em
#: qualquer lugar, e a medida da string ao lado virava regra: «fala de Bento com 21 palavras» (exp04ef1b), «legendas com
#: 39 a 46 palavras (teto: 60)» (exp06ef1b), «`e6.pergunta.em13co26` (49 palavras)» (exp02em1b) — análise de 24/10/2026.
#: Na revisão do PR #77 (24/10/2026) o marcador valia só nos 40 caracteres antes do número, cortados em `,;|()`, e o
#: teto inventado escrito de outro jeito sumia («Teto de palavras do texto de bastidor de cada projeto: 40 palavras»,
#: «Texto de bastidor (teto): 40 palavras», «Teto de leitura de 60 palavras por legenda e 40 palavras por bastidor»):
#: agora vale a oração inteira, e só sai a medida que o diagnóstico classificou (`_e_medida`).
_RE_TETO_ANTES = re.compile(_RE_TETO_OU_PISO.pattern + r"|\bcap\b|limitad[oa]s?\b|\bcab(?:er|e|em)\s+em\b", re.I)
#: Onde a oração do teto acaba: ponto e vírgula, célula de tabela e fim de frase. A vírgula e os dois-pontos não cortam
#: («Teto de palavras do bastidor de cada projeto: 40 palavras»). O parêntese aberto que diz alguma coisa antes do
#: número é a sua oração, e o item de lista dentro dele também («respeitando os tetos da faixa (resumo de 25 a 35
#: palavras, …, fala de Bento com 21 palavras)» — o 21 é a medida da fala); o que abre pelo número é o valor do que vem
#: antes («Teto do bastidor (40 palavras)»). O parêntese fechado corta só com número solto dentro («(teto)», «(máx.)»,
#: «(D0-09)» e «(§15)» não cortam).
_RE_FIM_DA_ORACAO_DO_TETO = re.compile(r"[;|]|(?<=[.!?])\s+(?=[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ])")
_RE_NUMERO_SOLTO = re.compile(r"(?<![\w.,§-])(?<!§\s)\d")
#: «frases com até 17 palavras (teto da faixa: 20 palavras)», «legendas com 39 a 46 palavras (teto: 60)», «fala com
#: exatamente 21 palavras (cumprindo teto ≤ 25)»: o número seguido do teto com outro número — solto ou da mesma unidade
#: — é a medida, e o teto é o outro. «(teto do D0-09)», «(teto do §15)» e «(máx. 2 linhas)» não trazem outro número de
#: palavras: são o teto deste (o «§15» é a seção onde moram os tetos, não um teto de 15 — revisão do PR #77).
_TETO_DEPOIS = (r"^\s*(?:\(\s*(?:[^\W\d]+\s+){{0,2}}?|[,—–]\s*)?(?:teto|m[áa]x|limite)[^)\n;|]*?(?<![\w.,§-])"
                r"(?<!§\s)\d+(?:[.,]\d+)?\s*(?:{unidade}\b|[)\n;,|]|$)")
#: A medida da string logo depois do identificador ou da copy citada: «`e6.pergunta.em13co26` (49 palavras)»
#: (exp02em1b). `_CITADO` marca, na linha limpa, onde estava o texto entre aspas ou crases.
_CITADO = "\ue000"
_RE_IDENTIFICADOR_E_PARENTESE = re.compile(r"(?:\ue000|\b[\w-]+(?:[._][\w-]+)+)\s*\(\s*$")
#: «fala de Bento com exatamente 21 palavras» (exp04ef1b): a contagem da copy, não um teto.
_RE_EXATAMENTE = re.compile(r"\b(?:com|em)\s+exatamente\s+$", re.I)
#: O teto ou o piso logo depois do número: «35 palavras no máximo», «35 palavras (teto)», «(teto do D0-09)», «8 a 10
#: palavras, sem exceder o teto», «35 palavras ou menos», «40 palavras, que é o teto», «40 palavras é o teto».
_RE_TETO_POSPOSTO = re.compile(
    r"^\s*(?:,\s*)?(?:\(\s*(?:teto|m[áa]x|limite|piso|m[íi]n)|no\s+m[áa]ximo|no\s+m[íi]nimo|ou\s+(?:menos|mais)\b|"
    r"(?:de\s+|como\s+)?(?:teto|limite|piso)\b|(?:sem|n[ãa]o\s+(?:pode|deve)(?:m)?)\s+(?:exceder|ultrapassar|passar)|"
    r"(?:que\s+)?(?:é|s[ãa]o|ser[áa]|seria)\s+o\s+(?:teto|limite|m[áa]ximo|piso|m[íi]nimo)\b)",
    re.I)


def _oracao_do_teto(antes: str) -> str:
    """O trecho da oração antes do número onde um teto o rege (`_RE_FIM_DA_ORACAO_DO_TETO`, parêntese)."""
    fronteiras = list(_RE_FIM_DA_ORACAO_DO_TETO.finditer(antes))
    trecho = antes[fronteiras[-1].end():] if fronteiras else antes
    abertos: List[int] = []
    corte = 0
    for i, c in enumerate(trecho):
        if c == "(":
            abertos.append(i)
        elif c == ")" and abertos:
            j = abertos.pop()
            if _RE_NUMERO_SOLTO.search(trecho[j + 1:i]):
                corte = i + 1
    if abertos and re.search(r"[^\W\d_]", trecho[abertos[-1] + 1:]):
        itens = list(re.finditer(r"[,;]", trecho[abertos[-1]:]))
        corte = max(corte, abertos[-1] + (itens[-1].end() if itens else 1))
    return trecho[corte:]


def _e_medida(antes: str, depois: str, unidade: str) -> bool:
    """A ocorrência é a medida de uma string, não um teto (os FP do diagnóstico de 24/10/2026): seguida do teto com
    outro número (`_TETO_DEPOIS`), entre parênteses logo depois de identificador ou copy citada, ou «com/em exatamente
    N palavras»."""
    return bool(re.match(_TETO_DEPOIS.format(unidade=unidade), depois, re.I)
                or (_RE_IDENTIFICADOR_E_PARENTESE.search(antes) and re.match(r"\s*\)", depois))
                or _RE_EXATAMENTE.search(antes))


def _teto_rege(linha: str, tok: Tuple[str, str]) -> bool:
    """Algum teto ou piso rege este número de palavras ou caracteres na linha (em alguma das ocorrências dele): antes
    dele, em qualquer ponto da mesma oração (`_oracao_do_teto`); logo depois (`_RE_TETO_POSPOSTO`); ou, em linha de
    tabela, na célula anterior («| Balão | Teto | 35 palavras |»). A medida (`_e_medida`) não é regida."""
    num = re.escape(tok[0]).replace(r"\.", "[.,]")
    tabela = linha.count("|") >= 2
    for m in re.finditer(rf"(?<![\w.,]){num}\s?{tok[1]}", linha, re.I):
        antes, depois = linha[:m.start()], linha[m.end():]
        if _e_medida(antes, depois, tok[1]):
            continue
        if _RE_TETO_ANTES.search(_oracao_do_teto(antes)) or _RE_TETO_POSPOSTO.match(depois):
            return True
        if tabela:
            celulas = antes.split("|")
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
    """Os números de regra da linha (também em LaTeX), fora de citação, de código em linha e de exemplo «(ex.: …)»: %,
    s, min e palavras ou caracteres que um teto ou piso rege — sem os de plataforma, de layout, a duração da espera de
    carregamento, a estatística externa, a nota de acessibilidade, os limites do recorte da aula e o 100%, que é
    «todos». Contagens de opção vêm à parte."""
    if de_plataforma(linha):
        return []
    linha = sem_latex(linha)
    limpa = _RE_EXEMPLO.sub(" ", _RE_CITACAO.sub(f" {_CITADO} ", linha))
    saida = []
    for n, u in numeros(limpa):
        if u == "px" or float(n) == 0 or (u == "%" and float(n) == 100):
            continue
        if u == "%" and (_RE_LAYOUT.search(limpa) or _RE_FONTE_EXTERNA.search(linha)
                         or _RE_FERRAMENTA_DE_ACESSIBILIDADE.search(linha)):
            continue
        if u in ("s", "min") and _duracao_de_espera(limpa, (n, u)):
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
    `hipoteses_reescritas`): o gate o mostra como atenção, não bloqueia. A leitura por hipótese não dá dúvida quando o
    corpo reproduz a frase do §17 com o número trocado (`_reproduz_a_frase`)."""
    corpo = "\n".join(_linhas_do_corpo(corpo))
    candidatos = [c for c in contrato_no_corpo(one_pager, corpo, secoes=(15, 17))
                  # a hipótese ausente do corpo não é número trocado: o PRD remete ao anexo, e o handoff ao §17
                  if not (c["situacao"] == "ausente" and (c["secao"] == "§17" or not exigir_tetos))]
    vistos = {(c["secao"], c["contrato"], c["corpo"]) for c in candidatos}
    for h in hipoteses_reescritas(one_pager, corpo, spec, contrato_texto):
        if h["situacao"] in SITUACOES_DE_DUVIDA:
            # a mesma troca que a régua de linha acusou (a linha do corpo tem as palavras da do §17): quem decide é a
            # leitura por hipótese, que sabe da pergunta citada, do comparativo e do predicado — e que já não dá dúvida
            # quando o corpo reproduz a frase do §17 com o número trocado (`_reproduz_a_frase`)
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


def _limpo_de_hipotese(texto: str) -> str:
    """A hipótese sem as citações e sem a marcação LaTeX da porcentagem e do comparativo."""
    return _RE_CITACAO.sub(" ", texto or "").replace("$", "").replace("\\%", "%").replace("\\ge", "≥").replace(
        "\\le", "≤")


def _metas_do_corpo(texto: str, mecanica: str = "") -> List[Tuple[str, str]]:
    """Os números de hipótese do corpo que podem ser meta: a duração (s, min) e toda porcentagem, menos a que vem
    marcada como mecânica (`_RE_MECANICA_ANTES`) sem comparativo nem população e que o contrato tem fora do §17 e do
    9f (`mecanica`, de `_contrato_da_mecanica`). Sem o contrato, a marca não basta: a porcentagem é meta.

    Revisão do PR #77 (24/10/2026): a leitura pedia o comparativo de uma lista curta ou a população, e fora disso a
    porcentagem sumia em silêncio — «Se a desistência das duplas superar 25%», «25% ou mais das duplas», «maior que
    25%» tiravam do gate a H1 30×25 da exp02ef1b (D11). O lado conservador é o contrário: só sai a marcada. Na segunda
    revisão, a marca sozinha ainda tirava «Se a taxa de 25% de desistência for atingida»: a mecânica é a do contrato."""
    limpo = _limpo_de_hipotese(texto)
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
#: `leitura-a-conferir` (C7, 25/10/2026): o código e o classificador não leem igual se o número é a meta da hipótese.
SITUACOES_DE_DUVIDA = ("limiar-do-9f", "complemento", "leitura-a-conferir")
#: Onde acaba o predicado da porcentagem — o que a hipótese diz da população que o número conta: «Mais de 30% das
#: duplas desistirem de ajustar a moldura e clicarem em confirmar na posição default sem interagir.»
_RE_FIM_DO_PREDICADO = re.compile(r"[;:|(\n]|\.(?!\d)")
#: Negação explícita do predicado, logo depois da população: «dos estudantes não conseguirem», «das duplas que não
#: concluírem». A de uma oração subordinada mais adiante («projetos que nunca viram») não nega a meta.
_RE_PREDICADO_NEGADO = re.compile(r"^\s*(?:d[aeo]s?\s+[^\W\d]+\s+)?(?:que\s+)?(?:n[ãa]o|nunca|jamais)\b", re.I)


def _predicado(texto: str, tok: Tuple[str, str]) -> str:
    """O que vem depois da porcentagem até o fim da oração (`_RE_FIM_DO_PREDICADO`); vazio se ela não está no texto."""
    limpo = sem_latex(_RE_CITACAO.sub(" ", texto or ""))
    num = re.escape(tok[0]).replace(r"\.", "[.,]")
    m = re.search(rf"(?<![\w.,]){num}\s?%", limpo)
    if not m:
        return ""
    fim = _RE_FIM_DO_PREDICADO.search(limpo, m.end())
    return limpo[m.end():fim.start() if fim else len(limpo)]


def _mesmo_predicado(a: str, b: str) -> bool:
    """Os dois predicados falam da mesma coisa: 2 radicais de conteúdo em comum. «das duplas desistirem de ajustar as
    alças e confirmarem na posição central default» e «das duplas desistirem de ajustar a moldura e clicarem em
    confirmar na posição default» têm 5; «concluírem o agrupamento com a justificativa correta» e «parearem cartas
    justificando pela cor do uniforme» (H3 da exp02ef1b), 1."""
    return len(_radicais(a) & _radicais(b)) >= 2


def _reproduz_a_frase(texto: str, fora: Sequence[Tuple[str, str]], do_17: str,
                      aprovados: Sequence[Tuple[str, str]]) -> bool:
    """O corpo reproduz a frase da meta do §17 com o número trocado: cada número dele tem, no §17, uma meta da mesma
    unidade com o mesmo comparativo e o mesmo predicado. É a H1 da exp02ef1b — «Se mais de 25% das duplas desistirem
    de ajustar as alças e confirmarem na posição central default» contra «Mais de 30% das duplas desistirem de ajustar
    a moldura …» —, que o PO acusou em 23/10/2026: divergência certa, mesmo com uma PQ firme no outro número."""
    return all(any(a[1] == t[1] and _direcao(texto, t) == _direcao(do_17, a)
                   and _mesmo_predicado(_predicado(texto, t), _predicado(do_17, a)) for a in aprovados)
               for t in fora)


def _complemento_pelo_predicado(texto: str, tok: Tuple[str, str], do_17: str, aprovado: Tuple[str, str]) -> bool:
    """100 − x com o comparativo invertido só é o complemento quando o predicado também muda: outro predicado («mais
    de 40% parearem pela cor» × «menos de 60% concluírem com a justificativa correta», exp02ef1b) ou o mesmo negado
    («mais de 30% desistirem» × «menos de 70% não desistirem»). O mesmo predicado com o critério invertido — «menos de
    70% das duplas desistirem» contra «mais de 30% das duplas desistirem» — é divergência certa (revisão do PR #77)."""
    p_corpo, p_17 = _predicado(texto, tok), _predicado(do_17, aprovado)
    return (not _mesmo_predicado(p_corpo, p_17)
            or bool(_RE_PREDICADO_NEGADO.match(p_corpo)) != bool(_RE_PREDICADO_NEGADO.match(p_17)))


def _meta_do_17_com_outro_numero(texto: str, tok: Tuple[str, str], do_17: str,
                                 aprovados: Sequence[Tuple[str, str]]) -> bool:
    """A porcentagem do corpo está no lugar da meta do §17: o §17 tem uma porcentagem com o mesmo predicado, sem a
    negação que faria dela o complemento — com o mesmo comparativo (`_reproduz_a_frase`, a H1 30×25 da exp02ef1b) ou
    com o critério invertido («menos de 70% das duplas desistirem» × «mais de 30% …», revisão do PR #77). É comparação
    com o texto do §17, não leitura de sentido: vale como prova quando o classificador não responde (revisão do PR #85,
    25/10/2026)."""
    if tok[1] != "%":
        return False
    p_corpo = _predicado(texto, tok)
    return any(a[1] == "%" and _mesmo_predicado(p_corpo, _predicado(do_17, a))
               and bool(_RE_PREDICADO_NEGADO.match(p_corpo)) == bool(_RE_PREDICADO_NEGADO.match(_predicado(do_17, a)))
               for a in aprovados)


def _leitura_sem_classificador(codigo_le_meta: bool, texto: str, tok: Tuple[str, str], do_17: str,
                               aprovados: Sequence[Tuple[str, str]]) -> str:
    """O que vale quando o classificador não respondeu (erro, 429, timeout, limite do gate, sem chave, desligado): sem
    a segunda leitura, só a prova em código decide. A porcentagem no lugar da meta do §17 (`_meta_do_17_com_outro_numero`)
    continua divergência certa, como na C1; o número que o código lê como mecânica fica calado, como antes da C7 — a
    dúvida sem segunda leitura seria ruído em todo número da mecânica; e a meta que só o código lê vira dúvida 🟡,
    porque é interpretação. Revisão do PR #85 (25/10/2026): com `CLASSIFICADOR_SENTIDO=desligado`, a H1 30×25 da
    exp02ef1b saía 🟡 e cada número da mecânica, 🟡 «a conferir»."""
    if not codigo_le_meta:
        return CONCORDAM_NAO
    return CONCORDAM_SIM if _meta_do_17_com_outro_numero(texto, tok, do_17, aprovados) else DUVIDA


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
      handoff da exp06ef1b-727a3c2d. A H3 do mesmo handoff, que trocou a hipótese inteira, continua `trocado`; e a
      frase do §17 reproduzida com o número trocado também (`_reproduz_a_frase`, a H1 30×25 da exp02ef1b);
    - `complemento` (dúvida): 100 − x com o comparativo invertido e outro predicado, ou o mesmo negado — «mais de 40%
      parearem pela cor» no §17 e «menos de 60% … com a justificativa correta» no handoff da exp02ef1b. Só é a mesma
      regra se ninguém ficar fora dos dois. O mesmo predicado com o critério invertido é `trocado`
      (`_complemento_pelo_predicado`)."""
    from tools.conteudo_aprovado import secao
    from tools.kpis import _RE_PQ, _pq_id

    do_17 = _itens_de_hipotese(secao(one_pager or "", 17) or "")
    do_corpo = _itens_de_hipotese(_secoes_de_hipotese(corpo))
    nove_f = _linhas_9f(sem_linhas_abertas(spec)) if spec else {}
    mecanica = _contrato_da_mecanica(contrato_texto or "")
    # Cada número da hipótese que o §17 não tem é lido duas vezes (C7, 25/10/2026): pelo código — a meta é toda
    # porcentagem menos a marcada como mecânica que o contrato tem, e a duração que o contrato não tem — e pelo
    # classificador (`tools/classificador.numero_da_hipotese`). Só a divergência que os dois leem como meta bloqueia; a
    # discordância é dúvida (`leitura-a-conferir`), com as duas leituras. Na fase A, o código perdia 4 de 13 metas do
    # held-out (a isenção «duração que o contrato tem») e a 1ª versão da C1 perdia 15 de 17 paráfrases da H1 30×25; o
    # classificador acertou os 60 casos — mas interpretação não bloqueia sozinha (`tools/severidade.py`). Quando o
    # classificador não responde, só a prova em código decide (`_leitura_sem_classificador`).
    lidos: Dict[Tuple[int, Tuple[str, str]], Any] = {}
    pedidos = [(n, t) for n, texto in do_corpo.items() if n in do_17
               for t in _numeros_de_hipotese(_limpo_de_hipotese(texto)) if not tem_numero(do_17[n], t)]
    if pedidos:
        from tools import classificador

        leituras = classificador.ler(classificador.NUMERO_DA_HIPOTESE, [
            {"hipotese_no_documento": do_corpo[n], "hipotese_aprovada_no_17": do_17[n], "numero": _numero_lido(t)}
            for n, t in pedidos])
        lidos = dict(zip(pedidos, leituras))
    saida = []
    for n, texto in do_corpo.items():
        if n not in do_17:
            continue
        aprovados = _numeros_de_hipotese(do_17[n])
        unidades = {u for _, u in aprovados}
        pelo_codigo = [t for t in _metas_do_corpo(texto, mecanica) if not tem_numero(do_17[n], t)
                       and (t[1] == "%" or t[1] in unidades or contrato_texto is None
                            or not tem_numero(contrato_texto, t))]
        candidatos = [t for (m, t) in lidos if m == n]
        leitura = {t: _leitura_sem_classificador(t in pelo_codigo, texto, t, do_17[n], aprovados)
                   if getattr(lidos[(n, t)], "nao_sei", True) else leitura_dupla(t in pelo_codigo, lidos[(n, t)], "meta")
                   for t in candidatos}
        fora = [t for t in candidatos if leitura[t] == CONCORDAM_SIM]
        duvidas = [t for t in candidatos if leitura[t] == DUVIDA]
        if duvidas:
            linha_duvida = next((l for l in texto.splitlines() if any(tem_numero(l, t) for t in duvidas)), texto)
            saida.append({"secao": "§17", "situacao": "leitura-a-conferir", "pq": "",
                          "contrato": ", ".join(_fmt(a) for a in aprovados if a[1] in {u for _, u in duvidas})
                          or "nenhum número", "quantifica": "sim" if aprovados else "",
                          "sem_classificador": "sim" if all(getattr(lidos[(n, t)], "nao_sei", True)
                                                            for t in duvidas) else "",
                          "corpo": ", ".join(_fmt(t) for t in duvidas), "hipotese": f"H{n}",
                          "linha": do_17[n].strip().splitlines()[0][:200], "linha_corpo": linha_duvida.strip()[:200],
                          "leituras": "; ".join(
                              f"{_fmt(t)}: o código lê {'meta' if t in pelo_codigo else 'parâmetro da mecânica'}, e "
                              + lidos[(n, t)].explicada({"meta": "meta", "mecanica": "parâmetro da mecânica"})
                              for t in duvidas)})
        if not fora:
            continue
        mesma_unidade = [t for t in aprovados if t[1] in {u for _, u in fora}]
        situacao, pq = ("trocado" if mesma_unidade else "acrescentado"), ""
        citadas = [_pq_id(x) for x in _RE_PQ.findall(texto) if _pq_id(x) in nove_f]
        do_9f = {p: _pct(nove_f[p]) for p in citadas}
        # só quando o §17 quantifica a hipótese: sem meta no §17, o número do corpo continua `acrescentado`
        if mesma_unidade and all(t[1] == "%" for t in fora) and _mesma_hipotese(do_17[n], texto):
            pq = next((p for p in citadas if all(t[0] in do_9f[p] for t in fora)), "")
            if pq and _reproduz_a_frase(texto, fora, do_17[n], aprovados):
                pq = ""
            elif pq:
                situacao = "limiar-do-9f"
            elif all(any(abs(float(t[0]) + float(a[0]) - 100) < 1e-9 and a[1] == "%"
                         and {_direcao(texto, t), _direcao(do_17[n], a)} == {"mais", "menos"}
                         and _complemento_pelo_predicado(texto, t, do_17[n], a) for a in aprovados)
                     for t in fora):
                situacao = "complemento"
        linha_corpo = next((l for l in texto.splitlines() if any(tem_numero(l, t) for t in fora)), texto)
        saida.append({"secao": "§17", "situacao": situacao, "pq": pq,
                      "contrato": ", ".join(_fmt(t) for t in mesma_unidade) or "nenhum número",
                      "corpo": ", ".join(_fmt(t) for t in fora), "hipotese": f"H{n}",
                      "linha": do_17[n].strip().splitlines()[0][:200], "linha_corpo": linha_corpo.strip()[:200]})
    return saida


def _tem_numero_do_17(c: Dict[str, str]) -> str:
    """«tem 30%», ou «não tem número» quando o §17 não quantifica a hipótese (nessa unidade): «tem nenhum número» saía
    na mensagem do handoff da exp01ef1b (revisão do PR #85, 25/10/2026)."""
    if c.get("contrato") != "nenhum número":
        return f"tem {c['contrato']}"
    return "não tem número nessa unidade" if c.get("quantifica") else "não tem número"


def _numero_lido(tok: Tuple[str, str]) -> str:
    """O número como o classificador o lê: `25%`, `2,5 s`."""
    return f"{tok[0].replace('.', ',')}{'%' if tok[1] == '%' else ' ' + tok[1]}"


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
    # o curinga não é estado: `EST_04_*` (as telas da etapa 4, handoff da exp02em1b de 25/10/2026) virava `EST_04` com o
    # `*` tirado como ênfase, e o gate o dava como estado inventado
    if (em_codigo and "*" in em_codigo[0]) or (not em_codigo and re.search(r"[A-Za-z0-9]_\*", celula or "")):
        return None
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


#: O ID de tela do inventário, com hífen ou sublinhado (o nó do Mermaid não aceita hífen): `E2-ALU-01`, `E2_ALU_01`.
_RE_ID_TELA = re.compile(r"\b(E\d{1,2})[-_]([A-Z]{2,5})[-_](\d{2})\b")


def _ids_de_tela(texto: str) -> List[str]:
    saida: List[str] = []
    for m in _RE_ID_TELA.finditer(texto or ""):
        t = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        if t not in saida:
            saida.append(t)
    return saida


def de_para_do_fluxo(fluxo: str, contrato: Sequence[str]) -> Dict[str, List[str]]:
    """`{tela: [estados do contrato]}` da seção «De-para nó → estado do contrato» do fluxo do design (prompt 072, G09): o
    estado é o nome do contrato escrito na linha da tela, literal (sem caixa). Sem a seção, vazio."""
    from tools.cobertura_design import tabelas

    # fronteira de palavra: sem ela, «## Unidade para cada estado» passava por seção de-para (revisão do PR #86)
    m = re.search(r"^#{1,6}[^\n]*\bde[- ]?para\b[^\n]*\bestados?\b[^\n]*$", fluxo or "", re.I | re.M)
    if not m:
        return {}
    fim = re.search(r"^#{1,6}\s", fluxo[m.end():], re.M)
    secao = fluxo[m.end(): m.end() + fim.start() if fim else len(fluxo)]
    por_nome = {e.lower(): e for e in contrato}
    saida: Dict[str, List[str]] = {}
    for _, linhas in tabelas(secao):
        for linha in linhas:
            texto = " | ".join(linha.values())
            estados = [por_nome[t.lower()] for t in re.findall(r"[A-Za-z][A-Za-z0-9_]*", texto) if t.lower() in por_nome]
            for tela in _ids_de_tela(texto):
                for e in estados:
                    if e not in saida.setdefault(tela, []):
                        saida[tela].append(e)
    return saida


def _sugestoes_de_estado(inventados: Sequence[str], texto: str, contrato: Sequence[str],
                         de_para: Dict[str, List[str]]) -> List[str]:
    """Para cada estado inventado, o nome do contrato que o autor pode usar — dado copiado, sem leitura de sentido: o que o
    de-para do fluxo dá às telas da linha onde o nome inventado está; sem de-para, os estados do contrato com o mesmo
    prefixo de etapa (`EST_02_…`). O handoff da exp02em1b (25/10/2026) ficou 🔴 nas duas rodadas porque a mensagem não
    dizia qual nome usar (G09)."""
    saida: List[str] = []
    linhas = [l for l in (texto or "").splitlines() if l.strip().startswith("|")]
    for inv in inventados:
        rx = re.compile(rf"(?<![\w]){re.escape(inv)}(?![\w])", re.I)
        telas = [t for l in linhas if rx.search(l) for t in _ids_de_tela(l)]
        telas = list(dict.fromkeys(telas))
        pares = [(t, e) for t in telas for e in de_para.get(t, [])]
        if pares:
            saida.append(f"`{inv}` → na linha da tela " + ", ".join(
                f"`{t}`, que o de-para do fluxo põe em `{e}`" for t, e in pares[:3]))
            continue
        prefixo = re.match(r"[A-Za-z]*_?0*\d+", inv)
        mesmos = [e for e in contrato if prefixo and re.match(rf"{re.escape(prefixo.group(0))}(?:_|$)", e, re.I)]
        if mesmos:
            saida.append(f"`{inv}` → do contrato, com o mesmo prefixo: " + ", ".join(f"`{e}`" for e in mesmos[:4]))
    return saida


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
    contrato_escrito = texto_do_contrato({k: v for k, v in docs.items() if k not in _FONTES_DE_DECISAO})
    one_pager = docs["one_pager"]
    spec = _spec_produto(state)
    pendencias = (secao_numerada(corpo, 19, "pend[êe]ncias") if documento == "prd"
                  else secao_numerada(corpo, 7, "lacunas e pend")) or ""

    # a) números de regra sem origem no contrato. 🟡, não 🔴 (C7, 25/10/2026): a ausência no contrato é literal, mas quem
    # decide que o número é «de regra» — e não de plataforma, de layout, de espera, de exemplo ou de fonte externa — é
    # uma heurística de sentido. No levantamento de 24/10/2026 foram 3 verdadeiros, 7 falsos positivos e 9 ambíguos
    # (`tools/severidade.py`)
    sem_origem = numeros_sem_origem(corpo, contrato_texto)
    if sem_origem:
        achados.append(_achado(
            "numero-sem-origem",
            f"{len(sem_origem)} número(s) de regra do corpo do {rotulo} não estão no contrato (one-pager, spec de "
            f"produto, decisões da lista branca do bloco 13, decisões do PO no de acordo e trocas da correção pontual): "
            + _exemplos(f"{i['numero']} em «{i['linha'][:110]}»" for i in sem_origem)
            + f". O {rotulo} monta, não decide: copie o número do contrato, tire-o, ou marque a linha "
            "`[PROPOSTA — validar com PO: <o número> · por quê]` (ela vai para a seção 19.3). Polling, TTL, p95 e o que "
            "mais for da plataforma não precisam de origem no contrato. Não bloqueia: o código não sabe com certeza se "
            "cada número é de regra — confira.", documento,
            severidade=por_prova(BLOQUEIO, INTERPRETACAO)))

    # b) hipóteses, tetos e metas — o corpo trocado bloqueia sempre; a divergência do próprio contrato, na origem
    # certa, pede o registro na seção de pendências além do corpo certo
    divergentes = hipoteses_e_tetos(one_pager, corpo, exigir_tetos=(documento == "prd"), spec=spec,
                                    contrato_texto=contrato_escrito)
    do_contrato = divergencias_do_contrato(one_pager, spec)
    for c in divergentes:
        if c["secao"] == "§17":
            codigo, o_que = "hipotese-diverge", "hipótese"
        else:
            codigo, o_que = ("teto-ausente", "teto") if c["situacao"] == "ausente" else ("teto-diverge", "teto")
        # dúvida, não divergência certa: atenção, separada do bloqueio pelo código (análise de 24/10/2026)
        if c["situacao"] == "leitura-a-conferir":
            achados.append(_achado(
                "hipotese-a-conferir",
                f"Dúvida, não divergência certa: a {c['hipotese']} do §17 do one-pager {_tem_numero_do_17(c)}, e o "
                f"{rotulo} escreve {c['corpo']}: «{c['linha_corpo'][:140]}». "
                + ("O classificador de sentido não respondeu, e só o código lê o número como a meta da hipótese, não "
                   "como um parâmetro da mecânica que ela cita — " if c.get("sem_classificador") else
                   "O código e o classificador de sentido não leem igual se o número é a meta da hipótese ou um "
                   "parâmetro da mecânica que ela cita — ")
                + f"{c['leituras'][:400]}. Se for a meta, o corpo diz o que o §17 diz"
                + (" (ou remete a ele)" if documento == "handoff" else "") + "; se for da mecânica, nada a corrigir. "
                "Confira com o PO antes do de acordo.", documento, severidade="atencao"))
            continue
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
                f"Dúvida, não divergência certa: a {c['hipotese']} do §17 do one-pager {_tem_numero_do_17(c)}, e o "
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
            + ". Meta e limiar de uma `PQ-nn` são os da linha dela no 9f, copiados; se a linha do 9f está marcada "
            "`[PROPOSTA …]`, mantenha o marcador `[PROPOSTA — validar com PO: meta <valor> · por quê]` também na célula "
            "do KPI no PRD (ou escreva `sem meta — primeira medição`), pois retirar o marcador transforma proposta em "
            "meta decidida e aciona `kpi-alvo-inventado`.", documento))

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
        from tools.cobertura_design import estados_da_spec

        # o nome a usar, copiado do de-para do fluxo ou do contrato (G09): sem ele, o autor da rodada 2 trocava um nome
        # inventado por outro
        contrato_estados = estados_da_spec(spec)
        sugestoes = _sugestoes_de_estado(inventados, corpo, contrato_estados,
                                         de_para_do_fluxo(str(state.get("fluxo_arestas") or ""), contrato_estados))
        achados.append(_achado(
            "estado-fora-do-contrato",
            f"{len(inventados)} estado(s) {onde} não existem no contrato de estados da spec nem no fluxo do design: "
            f"{_exemplos(f'`{e}`' for e in inventados)}. O {rotulo} não cria vocabulário de estado: use o nome do "
            "contrato — a tela que a spec põe dentro de um estado usa o nome dele."
            + (f" Onde usar: {_exemplos(sugestoes)}." if sugestoes else "")
            + f" Os estados do contrato: {_exemplos((f'`{e}`' for e in contrato_estados), limite=20)}.", documento))

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
