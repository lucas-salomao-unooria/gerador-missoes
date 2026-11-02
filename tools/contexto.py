"""Orçamento de contexto de cada chamada ao modelo: estimar, cortar o que é longo e não é contrato, e parar antes do 400.

Teste de ponta a ponta de 25/10/2026: a 3ef2b (one-pager do PO com 360 mil caracteres, ≈107 mil tokens) caiu no
`A004NucleoNarrativo` com `400 INVALID_ARGUMENT — The input token count exceeds the maximum number of tokens allowed
1048576`, depois de 90 minutos e US$ 8,50, e a segunda tentativa do roteiro bateu no mesmo 400 (US$ 10,34). Ninguém
media o tamanho da requisição antes de mandá-la, e o erro chegava ao PO como o JSON do Gemini.

Aqui, sem chamar a API:

- `estimar_tokens`: caracteres ÷ 3,3. É a razão medida no one-pager da 3ef2b (360.619 caracteres ≈ 107,7 mil tokens):
  tabela markdown, negrito e marcador custam mais que prosa, e a estimativa de 4 caracteres por token subestimava;
- `ContextoGrandeDemais`: a requisição que passa de `TETO_PREVOO` não sai — o erro nomeia o agente, o tamanho e as três
  maiores chaves do estado, em vez do 400 depois de uma hora e meia. É erro da esteira, não pede ação do PO;
- `erro_deterministico`: o 400 `INVALID_ARGUMENT` repete igual em toda tentativa — quem tenta de novo (o roteiro do
  e2e, o «rodar de novo» do app) não deve tentar sem mudar a entrada;
- `cortar_para_o_orcamento`: o juiz (agente `deterministico`) não recebe o one-pager do PO grande ao lado do one-pager
  da missão que o preserva (conferido em código): é o mesmo texto duas vezes. E, se a instrução ainda passa de
  `ORCAMENTO_JUIZ`, perde, nesta ordem e só até caber, o que é longo e não é contrato — o histórico de versões, o brief
  de escopo copiado dentro do documento e o corpo da seção 18. As seções 0 a 17, o §12a, os textos-chave, os números e
  os IDs nunca saem. Com o one-pager do PO que cabe e abaixo do orçamento, nada muda: as missões normais do e2e
  (one-pagers de 58 a 71 mil caracteres) ficam como estavam;
- `po_primeiro`: com o one-pager do PO grande, ele vai para o começo da instrução de quem o lê. O cache implícito do
  Gemini só reaproveita um prefixo idêntico; no meio da instrução, depois de texto que muda por agente, nunca havia
  prefixo comum — a 3ef2b teve 16 mil tokens em cache em 17,27 milhões de entrada.

Puro: recebe textos e o estado, devolve textos — exceto `anotar_chamada`, que guarda quem chamou o modelo por último
para a mensagem de erro do runner. Os callbacks que o usam estão em `agents/callbacks.py`.
"""
from __future__ import annotations

import re
from contextvars import ContextVar
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

#: Caracteres por token medidos no one-pager da 3ef2b (360.619 caracteres ≈ 107,7 mil tokens).
CARACTERES_POR_TOKEN = 3.3
#: O teto de entrada do modelo (a mensagem do 400 da 3ef2b).
TETO_DO_MODELO = 1_048_576
#: Acima disto a requisição não sai: folga para a estimativa, que não é a contagem do modelo.
TETO_PREVOO = 900_000
#: Quanto um autor devolve, com segurança, numa resposta só. O corte do A014 caiu sempre perto de 218 mil caracteres
#: (≈65 mil tokens, o limite de saída do modelo); com o raciocínio e o que o autor acrescenta, 40 mil tokens de
#: documento do PO é o que ainda cabe. Os one-pagers do PO das 15 missões do acervo e das 3 normais do e2e têm de 12 a 71
#: mil caracteres (até ≈22 mil tokens): todos abaixo.
SAIDA_SEGURA = 40_000
#: Orçamento de entrada de um juiz, em tokens estimados. Acima dele, o que é longo e não é contrato sai da instrução. A
#: maior chamada de juiz das três missões normais do e2e é a banca técnica do dev (A109b, 293 a 297 mil tokens): o
#: orçamento fica bem acima dela, para que nenhuma missão que já cabia mude.
ORCAMENTO_JUIZ = 400_000
#: Documento com menos que isto não é candidato a corte nem a ir para o começo da instrução: o ganho não paga a mudança.
LIMIAR_BLOCO = 30_000
#: Juízes que não entram no orçamento: o editor de trocas copia `de` letra por letra do documento inteiro.
SEM_ORCAMENTO = frozenset({"A000EditorPontual"})
#: Chaves do estado que são documentos longos e que um juiz lê inteiros.
DOCUMENTOS_LONGOS = ("one_pager", "one_pager_po", "material_anexado", "nucleo_narrativo", "spec_missao")

TITULO_PO_PRIMEIRO = "## One-pager do PO (anexo) — texto integral"
PONTEIRO_PO_PRIMEIRO = ("(o texto integral do one-pager do PO está no começo desta instrução, no bloco «One-pager do PO "
                        "(anexo) — texto integral»)")
TITULO_PLATAFORMA_PRIMEIRO = "## Referência da plataforma Unooria (prefixo compartilhado)"
PONTEIRO_PLATAFORMA_PRIMEIRO = (
    "(a referência da plataforma Unooria está no começo desta instrução, no bloco «Referência da plataforma Unooria "
    "(prefixo compartilhado)»)")
_RE_BLOCO_PLATAFORMA = re.compile(
    r"<!-- início de (references/plataforma-unooria-(?!software\.md)[a-z0-9_-]+\.md) -->.*?"
    r"<!-- fim de \1 -->",
    re.DOTALL,
)
PONTEIRO_PO_PRESERVADO = (
    "(o one-pager do PO não é repetido aqui, para caber no contexto: ele está inteiro, palavra por palavra, dentro do "
    "one-pager da missão que você recebeu acima — um código conferiu cada trecho dele nesta execução. O que a esteira "
    "mudou no texto do PO está na tabela «Alterações sobre o one-pager do PO»; o que ela acrescentou vem marcado "
    "[PROPOSTA], [PARÂMETRO] ou [ABERTO], ou é seção que o PO não tinha.)")


def estimar_tokens(texto: Optional[str]) -> int:
    """Tokens estimados de um texto, sem chamar a API."""
    n = len(texto or "")
    return int(n / CARACTERES_POR_TOKEN) + (1 if n else 0)


def grande(texto: Optional[str]) -> bool:
    """O documento passa do que um autor devolve com segurança numa resposta (`SAIDA_SEGURA`)."""
    return estimar_tokens(texto) > SAIDA_SEGURA


# ------------------------------------------------------------------ a requisição
def _texto_de(conteudo: Any) -> str:
    partes = getattr(conteudo, "parts", None) or []
    return "".join(str(getattr(p, "text", "") or "") for p in partes)


def instrucao_da_requisicao(llm_request: Any) -> str:
    config = getattr(llm_request, "config", None)
    si = getattr(config, "system_instruction", None) if config is not None else None
    if isinstance(si, str):
        return si
    if si is None:
        return ""
    return _texto_de(si) if hasattr(si, "parts") else str(si)


def tokens_da_requisicao(llm_request: Any) -> Tuple[int, int]:
    """`(instrução, histórico)` em tokens estimados. Arquivo binário (PDF anexado) não entra: o modelo o conta por página."""
    historico = "".join(_texto_de(c) for c in getattr(llm_request, "contents", None) or [])
    return estimar_tokens(instrucao_da_requisicao(llm_request)), estimar_tokens(historico)


def maiores_chaves(state: Mapping[str, Any], n: int = 3) -> List[Tuple[str, int]]:
    """As `n` chaves do estado com mais texto, em tokens estimados — é o que se lê primeiro quando a conta estoura."""
    tamanhos = [(str(k), estimar_tokens(v if isinstance(v, str) else str(v)))
                for k, v in state.items() if not str(k).startswith("temp:") and v]
    return sorted(tamanhos, key=lambda kv: -kv[1])[:n]


class ContextoGrandeDemais(RuntimeError):
    """A requisição de um agente passa do que o modelo aceita. Determinística: tentar de novo dá o mesmo erro."""

    def __init__(self, agente: str, tokens: int, historico: int = 0, maiores: Iterable[Tuple[str, int]] = ()):
        self.agente, self.tokens, self.historico, self.maiores = agente, tokens, historico, list(maiores)
        chaves = ", ".join(f"`{k}` ({_milhares(t)})" for k, t in self.maiores) or "—"
        super().__init__(
            f"o agente {agente} montou uma entrada de ≈{_milhares(tokens)} tokens para o modelo, acima do teto de "
            f"{_milhares(TETO_DO_MODELO)} (o histórico da conversa responde por ≈{_milhares(historico)}). A chamada não foi "
            f"feita. As maiores partes do estado: {chaves}. É falha da esteira, não da missão: tentar de novo dá o mesmo "
            "erro — avise o time técnico.")


def _milhares(n: int) -> str:
    return f"{int(n):,}".replace(",", ".")


_RE_TAMANHO = re.compile(r"input token count[^.]*exceeds the maximum number of tokens allowed\s*(\d+)?", re.I)


def e_erro_de_tamanho(exc: BaseException) -> bool:
    """O 400 de entrada grande demais do Gemini, ou o pré-voo que o evitou."""
    return isinstance(exc, ContextoGrandeDemais) or bool(_RE_TAMANHO.search(str(exc)))


def erro_deterministico(exc: BaseException) -> bool:
    """Erro que se repete igual em toda tentativa: entrada grande demais, ou outro `400 INVALID_ARGUMENT` do modelo.

    É o que o roteiro do e2e e o «rodar de novo» precisam saber para não pagar a mesma queda duas vezes (US$ 10,34 na
    segunda tentativa da 3ef2b). 429, 500 e 503 são passageiros e continuam com retentativa (`agents/base.py`)."""
    if e_erro_de_tamanho(exc):
        return True
    codigo = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    texto = str(exc)
    return codigo == 400 or texto.startswith("400 ") or "INVALID_ARGUMENT" in texto


def mensagem_de_tamanho(exc: BaseException, agente: str = "") -> str:
    """O 400 de tamanho como o PO consegue ler: qual agente e quanto."""
    if isinstance(exc, ContextoGrandeDemais):
        return str(exc)
    m = _RE_TAMANHO.search(str(exc))
    teto = _milhares(int(m.group(1))) if m and m.group(1) else _milhares(TETO_DO_MODELO)
    quem = f"o agente {agente}" if agente else "um agente"
    return (f"{quem} mandou ao modelo uma entrada maior que o teto de {teto} tokens, e o modelo a recusou (400 "
            "INVALID_ARGUMENT). É falha da esteira, não da missão: tentar de novo dá o mesmo erro — avise o time técnico.")


# ------------------------------------------------------------------ quem chamou o modelo por último
#: O agente da última chamada ao modelo nesta execução, anotado pelo orçamento de contexto logo antes de cada chamada. É
#: um dicionário mutável na contextvar: as tarefas que o ADK cria copiam o contexto, mas o dicionário é o mesmo, e duas
#: execuções em paralelo (duas sessões no app) têm cada uma o seu.
_ULTIMA_CHAMADA: ContextVar[Optional[Dict[str, str]]] = ContextVar("ultima_chamada_ao_modelo", default=None)


def acompanhar_chamadas() -> Dict[str, str]:
    """Começa o registro desta execução (`pipeline.runner`) e o devolve: `{"agente": <nome>}` depois da 1ª chamada."""
    registro: Dict[str, str] = {}
    _ULTIMA_CHAMADA.set(registro)
    return registro


def anotar_chamada(agente: str) -> None:
    """Quem vai chamar o modelo agora. O autor do último evento não serve: na 3ef2b o A004 não emite evento antes da
    chamada, e o «🔁 nova volta» do `…Isolado` vinha logo antes — o 400 citaria o agente errado (revisão do PR #87)."""
    registro = _ULTIMA_CHAMADA.get()
    if registro is not None and agente:
        registro["agente"] = agente


# ------------------------------------------------------------------ o que sai da instrução de um juiz
_RE_TITULO = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.M)
_RE_HISTORICO = re.compile(r"hist[óo]rico de vers|changelog", re.I)
_RE_BRIEF = re.compile(r"^(?:#{1,6}\s*|\*\*)\s*MISS[ÃA]O DIGITAL UNOORIA\s*·\s*BRIEFING DE ESCOPO[^\n]*", re.M)
_RE_SECAO_18 = re.compile(r"^18\s*(?:\.(?![\dA-Za-z])|[—–-]\s)")
_RE_MARCADOR = re.compile(r"\[(?:PROPOSTA|PAR[ÂA]METRO|ABERTO|DECIS[ÃA]O PENDENTE|CONFLITO|LACUNA)", re.I)
_RE_ALTERACOES = re.compile(r"altera[çc][õo]es sobre o one-pager", re.I)


def _titulos(texto: str) -> List[Tuple[int, int, int, str]]:
    """`(início, fim da linha, nível, título)` de cada título markdown."""
    return [(m.start(), m.end(), len(m.group(1)), m.group(2).strip("*_ ")) for m in _RE_TITULO.finditer(texto or "")]


def _fim_do_bloco(titulos: List[Tuple[int, int, int, str]], i: int, total: int) -> int:
    nivel = titulos[i][2]
    return next((ini for ini, _, n, _ in titulos[i + 1:] if n <= nivel), total)


def sem_historico(texto: str) -> Tuple[str, int]:
    """O documento sem «Histórico de versões» e «Changelog». `(texto, caracteres tirados)`."""
    titulos = _titulos(texto)
    cortes = [(ini, _fim_do_bloco(titulos, i, len(texto))) for i, (ini, _, _, t) in enumerate(titulos)
              if _RE_HISTORICO.search(t)]
    return _tirar(texto, cortes, "*(histórico de versões fora do contexto deste juiz: {n} caracteres)*")


def sem_brief(texto: str) -> Tuple[str, int]:
    """O documento sem o brief de escopo copiado dentro dele (do título do brief ao próximo histórico ou ao fim).

    O brief tem chave própria (`brief_escopo`), e o juiz que precisa dele o recebe por ela."""
    m = _RE_BRIEF.search(texto or "")
    if not m:
        return texto, 0
    fim = next((ini for ini, _, _, t in _titulos(texto) if ini > m.start() and _RE_HISTORICO.search(t)), len(texto))
    return _tirar(texto, [(m.start(), fim)], "*(brief de escopo fora do contexto deste juiz: {n} caracteres; ele "
                                               "é lido à parte)*")


def secao_18_resumida(texto: str) -> Tuple[str, int]:
    """A seção 18 só com os títulos, as linhas com marcador aberto e a tabela «Alterações sobre o one-pager do PO».

    São as decisões de direção, os trade-offs e as notas de autoria: o que a missão decidiu está nas seções 0 a 17, e o
    que ficou em aberto, nos marcadores — que ficam."""
    titulos = _titulos(texto)
    for i, (ini, fim_titulo, _, t) in enumerate(titulos):
        if not _RE_SECAO_18.match(t):
            continue
        fim = _fim_do_bloco(titulos, i, len(texto))
        corpo = texto[fim_titulo:fim]
        mantidas, em_alteracoes = [], False
        for linha in corpo.splitlines():
            mt = _RE_TITULO.match(linha)
            if mt:
                em_alteracoes = bool(_RE_ALTERACOES.search(mt.group(2)))
                mantidas.append(linha)
            elif _RE_MARCADOR.search(linha) or (em_alteracoes and linha.strip().startswith("|")):
                mantidas.append(linha)
        novo = "\n".join(mantidas).strip()
        tirados = len(corpo.strip()) - len(novo)
        if tirados <= 0:
            return texto, 0
        nota = (f"\n\n*(seção 18 resumida para este juiz: {tirados} caracteres de decisões de direção e notas de autoria "
                "fora do contexto; ficaram os títulos, os marcadores abertos e a tabela de alterações)*\n\n")
        return texto[:fim_titulo] + nota + novo + "\n\n" + texto[fim:], tirados
    return texto, 0


def _tirar(texto: str, cortes: List[Tuple[int, int]], nota: str) -> Tuple[str, int]:
    if not cortes:
        return texto, 0
    partes, ultimo, tirados = [], 0, 0
    for ini, fim in sorted(cortes):
        if ini < ultimo:
            continue
        partes.append(texto[ultimo:ini])
        partes.append(nota.format(n=fim - ini) + "\n\n")
        tirados += fim - ini
        ultimo = fim
    partes.append(texto[ultimo:])
    return "".join(partes), tirados


#: Os cortes, na ordem em que entram: do que não perde nada ao que resume.
_CORTES = (("histórico de versões", sem_historico), ("brief de escopo repetido", sem_brief),
           ("corpo da seção 18", secao_18_resumida))


def _solto(instrucao: str, chave: str, state: Mapping[str, Any]) -> bool:
    """O documento da chave aparece uma vez na instrução, e não como pedaço de outro documento dela (o one-pager do PO
    está dentro do `material_anexado`, de onde foi extraído): trocá-lo ali cortaria o outro documento."""
    texto = str(state.get(chave) or "")
    if not texto or instrucao.count(texto) != 1:
        return False
    return not any(texto in outro and outro in instrucao
                   for outro in (str(state.get(k) or "") for k in DOCUMENTOS_LONGOS if k != chave) if outro != texto)


def cortar_para_o_orcamento(instrucao: str, state: Mapping[str, Any],
                            orcamento: int = ORCAMENTO_JUIZ) -> Tuple[str, List[str]]:
    """A instrução de um juiz sem o que é repetido e, acima do orçamento, sem o que é longo e não é contrato.
    `(instrução, cortes)`.

    Cada documento longo do estado (`DOCUMENTOS_LONGOS`) que aparece uma vez, inteiro, na instrução é trocado pela versão
    cortada; nada é cortado no meio de uma frase.
    """
    cortes: List[str] = []
    atuais = {k: str(state.get(k) or "") for k in DOCUMENTOS_LONGOS}
    po, op = atuais["one_pager_po"], atuais["one_pager"]
    # 1. O one-pager do PO grande ao lado do one-pager da missão, quando um código conferiu que este preserva aquele: é
    # o mesmo texto duas, às vezes três vezes — na 3ef2b o material anexado é o próprio one-pager do PO (≈107 mil tokens
    # a mais por cópia, por juiz). Sai toda cópia fora do one-pager da missão; o que cabe fica como estava.
    if (grande(po) and op and op != po and op in instrucao
            and str(state.get("one_pager_po_status") or "") == "aprovado"):
        pedacos = instrucao.split(op)
        copias = sum(p.count(po) for p in pedacos)
        if copias:
            instrucao = op.join(p.replace(po, PONTEIRO_PO_PRESERVADO) for p in pedacos)
            atuais = {k: (v if k == "one_pager" else v.replace(po, PONTEIRO_PO_PRESERVADO)) for k, v in atuais.items()}
            cortes.append(f"one-pager do PO repetido ({copias} cópia{'s' if copias > 1 else ''} de "
                          f"{_milhares(len(po))} caracteres)")
    for rotulo, cortar in _CORTES:
        if estimar_tokens(instrucao) <= orcamento:
            break
        for chave in DOCUMENTOS_LONGOS:
            texto = atuais[chave]
            if len(texto) < LIMIAR_BLOCO or not _solto(instrucao, chave, atuais):
                continue
            novo, tirados = cortar(texto)
            if tirados > 0:
                instrucao = instrucao.replace(texto, novo, 1)
                atuais[chave] = novo
                cortes.append(f"{rotulo} de `{chave}` ({_milhares(tirados)} caracteres)")
    return instrucao, cortes


def po_primeiro(instrucao: str, state: Mapping[str, Any]) -> str:
    """O one-pager do PO grande no começo da instrução, com um ponteiro no lugar onde ele estava. Igual sem PO grande,
    sem o texto dele inteiro na instrução, se ele já está no começo ou se ele é pedaço de outro documento da instrução
    (mover o pedaço cortaria o outro documento)."""
    po = str(state.get("one_pager_po") or "")
    if not grande(po) or instrucao.startswith(TITULO_PO_PRIMEIRO) or not _solto(instrucao, "one_pager_po", state):
        return instrucao
    return f"{TITULO_PO_PRIMEIRO}\n\n{po}\n\n---\n\n" + instrucao.replace(po, PONTEIRO_PO_PRIMEIRO, 1)


def prefixo_cache_implicito(instrucao: str, state: Optional[Mapping[str, Any]] = None) -> str:
    """Posiciona blocos estáticos da plataforma (`references/plataforma-unooria-*.md`) e o documento-base
    compartilhado da etapa (`spec_missao` ou `one_pager` com pelo menos `LIMIAR_BLOCO` caracteres) no início da
    instrução para maximizar o hit rate do cache implícito do Gemini entre agentes consecutivos."""
    if not instrucao or instrucao.startswith(TITULO_PLATAFORMA_PRIMEIRO):
        return instrucao
    blocos: List[str] = []

    def _extrair(m: re.Match[str]) -> str:
        blocos.append(m.group(0))
        return PONTEIRO_PLATAFORMA_PRIMEIRO

    corpo = _RE_BLOCO_PLATAFORMA.sub(_extrair, instrucao)
    prefixos: List[str] = []
    if blocos:
        prefixos.append(f"{TITULO_PLATAFORMA_PRIMEIRO}\n\n" + "\n\n".join(blocos))
    if state and not corpo.startswith(TITULO_PO_PRIMEIRO):
        for chave in ("spec_missao", "one_pager"):
            doc = str(state.get(chave) or "")
            if len(doc) < LIMIAR_BLOCO or not _solto(corpo, chave, state):
                continue
            pos = corpo.find(doc)
            if pos >= 500:
                ponteiro = (f"(o texto integral de `{chave}` está no começo desta instrução, no bloco "
                            f"«Documento-base compartilhado (`{chave}`)»)")
                corpo = corpo.replace(doc, ponteiro, 1)
                prefixos.append(f"## Documento-base compartilhado (`{chave}`)\n\n{doc}")
                break
    if not prefixos:
        return instrucao
    return "\n\n---\n\n".join(prefixos) + "\n\n---\n\n" + corpo

