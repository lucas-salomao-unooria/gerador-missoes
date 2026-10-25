"""Governança da liberação de produto: quem liberou, a exceção do admin com 🔴 e o que chega ao handoff e ao PRD.

PR 9 do plano «Produto dono do contrato» (docs/planos/2026-10-23-produto-dono-do-contrato.md), decisão D9: a conta
design continua liberando produto (58c3ed1, 24/09/2026), mas a liberação que não vem da conta produto fica à vista em
🟡 — no cartão da missão, no catálogo e no dossiê —, e a exceção do admin com 🔴 em produto exige justificativa escrita.
No acervo de 23/10/2026, 1 de 5 liberações de produto veio da conta produto; as em vigor da exp02em1b (23/10 16:03) e
da exp02ef1b (22/10 15:27) são da conta design («Tudo de acordo e podemos seguir design»).

A fonte da verdade são os pareceres do fluxo (`conversa.json`): `de_produto` deriva deles, sem I/O, o que vale para a
liberação em vigor. O resultado vai para o estado da sessão (`governanca_produto`) no começo de cada etapa e a cada
decisão gravada — é por ele que o handoff e o PRD recebem, por código, a pendência de governança na seção de
pendências (`com_pendencias`). Refazer de design ou de dev, correção pontual e a cascata do PR 5 não invalidam o de
acordo de produto, e a marca segue; o refazer de produto o invalida, e a marca passa a ser a da próxima liberação.

O bloco que entra nos documentos não leva texto livre de ninguém (nem a justificativa, que fica no parecer, no estado
e no dossiê) nem marcador de lacuna: os gates do handoff e do PRD — montagem, status de gate no corpo, rastro — não
o leem como número de regra, status nem pendência de outra etapa, e o redator não tem como «consertá-lo».

O bloco é da esteira, como o anexo literal do PRD: sai da base que o autor recebe (`anterior_<chave>`,
`rodada_anterior_<chave>`, os documentos do editor de trocas) e volta, como está agora, em todo caminho que escreve o
documento — o callback do redator, o documento travado na correção pontual, o retrabalho por trocas e o A119.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

#: A conta que responde por produto. O design também libera produto (24/09/2026) e o admin libera qualquer etapa.
CONTA_PRODUTO = "produto"
#: Como cartão, catálogo, dossiê e documentos chamam a liberação de produto dada por outra conta.
SEM_CONTA_PRODUTO = "liberado sem a conta produto"
#: Onde a governança vive no estado da sessão. Fica fora de toda lista de `pipeline/reexecucao.py`: é recalculada dos
#: pareceres a cada etapa, e nenhuma reexecução a apaga.
KEY_GOVERNANCA = "governanca_produto"

LIBERADO_SEM_CONTA = "liberado-sem-conta-produto"
EXCECAO_COM_VERMELHO = "excecao-com-vermelho"

_LIBERA = ("de_acordo", "excecao")


# ------------------------------------------------------------------ regras (puras)
def papel_do_parecer(parecer: Dict[str, Any]) -> str:
    """O papel da conta que registrou o parecer: `autor`, ou — no registro sem ele — a primeira palavra de `como`."""
    autor = str(parecer.get("autor") or "").strip()
    if autor:
        return autor
    como = str(parecer.get("como") or "").strip()
    return como.split(" ", 1)[0] if como else ""


def libera_produto(parecer: Any) -> bool:
    return isinstance(parecer, dict) and parecer.get("etapa") == "produto" and parecer.get("acao") in _LIBERA


def liberou_sem_conta_produto(parecer: Dict[str, Any]) -> bool:
    """O parecer libera produto e não veio da conta produto (design «como Produto», ou o admin).

    Registro sem `autor` nem `como` não diz quem liberou: não é marcado, para não acusar sem prova."""
    papel = papel_do_parecer(parecer)
    return libera_produto(parecer) and bool(papel) and papel != CONTA_PRODUTO


def justificativa_valida(texto: Any) -> bool:
    """Não vazia e não trivial: ao menos uma letra ou um dígito. Só espaços e pontuação («...», «-», «!!!») não
    justificam nada; além disso não há mínimo — o texto é de quem decide, e o registro mostra o que ele escreveu."""
    return bool(re.sub(r"[\W_]", "", str(texto or "")))


def gates_vermelhos(parecer: Dict[str, Any]) -> List[str]:
    return sorted(k for k, v in (parecer.get("gates") or {}).items() if v == "🔴")


def _liberacao(parecer: Dict[str, Any]) -> Dict[str, Any]:
    papel = papel_do_parecer(parecer)
    vermelhos = gates_vermelhos(parecer)
    saida = {"acao": parecer.get("acao"), "papel": papel, "como": str(parecer.get("como") or papel),
             "quando": str(parecer.get("quando") or ""), "valido": bool(parecer.get("valido", True)),
             "conta_produto": papel == CONTA_PRODUTO, "gates_vermelhos": vermelhos}
    j = parecer.get("justificativa_excecao")
    if isinstance(j, dict) and justificativa_valida(j.get("texto")):
        saida["justificativa"] = {"texto": str(j["texto"]).strip(), "autor": str(j.get("autor") or papel),
                                  "como": str(j.get("como") or saida["como"]), "quando": str(j.get("quando") or "")}
    return saida


def de_produto(pareceres: Optional[Iterable[Any]]) -> Dict[str, Any]:
    """A governança da liberação de produto lida dos pareceres, do mais antigo ao mais novo. Pura.

    `liberacao` é a liberação de produto em vigor (o último de acordo ou exceção de produto ainda válido), ou `None`;
    `pendencias`, as de governança dela (🟡, não impedem); `historico`, todas as liberações de produto, inclusive as que
    um refazer de produto invalidou — o registro de quem liberou não some."""
    liberacoes = [p for p in (pareceres or []) if libera_produto(p)]
    em_vigor = next((p for p in reversed(liberacoes) if p.get("valido", True)), None)
    saida: Dict[str, Any] = {"liberacao": None, "pendencias": [], "historico": [_liberacao(p) for p in liberacoes]}
    if em_vigor is None:
        return saida
    lib = _liberacao(em_vigor)
    saida["liberacao"] = lib
    if liberou_sem_conta_produto(em_vigor):
        saida["pendencias"].append({
            "codigo": LIBERADO_SEM_CONTA, "papel": lib["papel"], "como": lib["como"], "quando": lib["quando"],
            "resumo": f"{SEM_CONTA_PRODUTO} — o de acordo de produto em vigor é de {lib['como']}, em {lib['quando']}"})
    if lib["acao"] == "excecao" and lib["gates_vermelhos"]:
        j = lib.get("justificativa")
        saida["pendencias"].append({
            "codigo": EXCECAO_COM_VERMELHO, "como": lib["como"], "quando": lib["quando"],
            "gates": lib["gates_vermelhos"], "justificativa": j,
            "resumo": (f"exceção do admin com 🔴 em produto — {lib['como']} liberou em {lib['quando']} com "
                       f"{', '.join(lib['gates_vermelhos'])} em 🔴; "
                       + (f"justificativa de {j['como']} em {j['quando']}" if j else
                          "sem justificativa registrada (exceção anterior à regra de 24/10/2026)"))})
    return saida


def da_sessao(estado: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """A governança do estado (`governanca_produto`), ou — na sessão que só tem os pareceres copiados pela rodada final
    (`pareceres_humanos`) — derivada deles. Sessão sem parecer humano: sem liberação e sem pendência."""
    estado = estado or {}
    gravada = estado.get(KEY_GOVERNANCA)
    if isinstance(gravada, dict) and "pendencias" in gravada:
        return gravada
    return de_produto(estado.get("pareceres_humanos") or [])


def marca(gov: Optional[Dict[str, Any]]) -> str:
    """A marca curta do cartão e do catálogo: «🟡 liberado sem a conta produto — design (como Produto), <data>»."""
    lib = (gov or {}).get("liberacao") or {}
    if not any(p.get("codigo") == LIBERADO_SEM_CONTA for p in (gov or {}).get("pendencias") or []):
        return ""
    return f"🟡 {SEM_CONTA_PRODUTO} — {lib.get('como', '')}, {lib.get('quando', '')}".rstrip(", ")


# ------------------------------------------------------------------ handoff e PRD
#: O título é também o marcador: comentário HTML apareceria cru no `.docx` (como no anexo do conteúdo aprovado).
TITULO_BLOCO = "Pendências de governança da liberação de produto (registradas pela esteira)"
_RE_TITULO_BLOCO = re.compile(r"^#{1,6}\s*\**\s*Pend[êe]ncias de governan[çc]a da libera[çc][ãa]o de produto\b", re.I)
#: A frase de abertura, fixa, entre o título e os itens.
ABERTURA_BLOCO = ("Registradas por código a partir dos pareceres da missão (plano «Produto dono do contrato», D9). Não "
                  "impedem a codificação e não são decisão deste documento.")
#: O fecho do item «liberado sem a conta produto»: diz o que o item é, sem pedir ação de ninguém antes de codificar.
REGISTRO_SEM_CONDICAO = "Registro de governança: não condiciona a codificação."
#: As linhas que a esteira escreve no bloco, além do título: a abertura e os dois itens de `linhas_do_bloco`. Só elas saem
#: com o bloco — o item que o autor escreveu logo depois, na mesma seção, fica (revisão do PR #75, 24/10/2026: uma troca
#: do retrabalho do PrdLoop ancorada na última linha do bloco punha «- [PENDÊNCIA] H1 do corpo (25%) diverge do §17
#: (30%)» depois dela, e o A119 a apagava junto com o bloco).
_RE_LINHA_DO_BLOCO = re.compile(r"^\s*(?:Registradas por c[óo]digo a partir dos pareceres da miss[ãa]o\b"
                                r"|[-*]\s*🟡\s*\*\*\s*(?:Liberado sem a conta produto|Exce[çc][ãa]o do admin em produto))")
_RE_TITULO = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_RE_CERCA = re.compile(r"^\s*(```|~~~)")

#: Onde cada documento lista as pendências: o PRD na seção 19, o handoff na seção 7 («Lacunas e pendências»).
#: «Dependências» (a §15 do PRD) não é «pendências»: a palavra começa no limite.
SECAO_DE_PENDENCIAS: Dict[str, Tuple[int, str]] = {"prd_final": (19, r"\bpend[êe]ncias|\bquest[õo]es\s+abertas"),
                                                   "handoff_dev": (7, r"\blacunas\s+e\s+pend")}


def linhas_do_bloco(gov: Optional[Dict[str, Any]]) -> List[str]:
    """Os itens da lista, sem texto livre e sem marcador de lacuna. Vazio sem pendência de governança.

    Redação conferida contra os gates do PRD e do handoff: sem número com unidade (montagem), sem «gate: 🔴» nem
    «status do gate» (status de gate no corpo), sem `[ABERTO — dono: PO …]` — que o conferidor da plataforma leria como a
    decisão do PO sobre a experiência existente — e sem 🔵 (o rastro o contaria como pendência a validar).

    É registro, não pré-requisito: o D9 pede a marca, não uma confirmação do PO antes de codificar. A banca de dev (LLM,
    «Ausência é NOK») lê o handoff, e o agente de codificação lê o PRD. Até a revisão do PR #75 (24/10/2026), o item dizia
    que o PO «confirma o one-pager e a spec de produto antes de a missão ser codificada» — contradizia a abertura e, nas
    reexecuções liberadas pela conta design, punha uma condição de codificação na frente dos dois."""
    saida: List[str] = []
    for p in (gov or {}).get("pendencias") or []:
        if p.get("codigo") == LIBERADO_SEM_CONTA:
            saida.append(f"- 🟡 **Liberado sem a conta produto** — o de acordo de produto em vigor foi dado por "
                         f"`{p.get('como', '')}` em {p.get('quando', '')}, e não pela conta `produto`. "
                         f"{REGISTRO_SEM_CONDICAO}")
        elif p.get("codigo") == EXCECAO_COM_VERMELHO:
            j = p.get("justificativa") or {}
            nomes = ", ".join(f"`{g}`" for g in p.get("gates") or [])
            saida.append(f"- 🟡 **Exceção do admin em produto, com reprovação vermelha** — `{p.get('como', '')}` liberou "
                         f"produto em {p.get('quando', '')} sem resolver {nomes}. "
                         + (f"A justificativa escrita por `{j.get('como', '')}` em {j.get('quando', '')} está no "
                            "parecer e no dossiê da missão." if j else
                            "A exceção é anterior à justificativa obrigatória e não tem uma registrada."))
    return saida


def bloco(gov: Optional[Dict[str, Any]], nivel: int = 3) -> str:
    linhas = linhas_do_bloco(gov)
    if not linhas:
        return ""
    return "\n".join([f"{'#' * nivel} {TITULO_BLOCO}", "", ABERTURA_BLOCO, ""] + linhas) + "\n"


def _titulos(texto: str) -> List[Tuple[int, int, int, str]]:
    """(início da linha, fim da linha, nível, título) de cada título fora de bloco de código."""
    saida: List[Tuple[int, int, int, str]] = []
    pos, cerca = 0, False
    for linha in (texto or "").splitlines(keepends=True):
        if _RE_CERCA.match(linha):
            cerca = not cerca
        elif not cerca:
            m = _RE_TITULO.match(linha.rstrip("\n"))
            if m:
                saida.append((pos, pos + len(linha), len(m.group(1)), m.group(2).strip("*_ ")))
        pos += len(linha)
    return saida


def _regua(linha: str) -> bool:
    return bool(re.match(r"^\s*(?:(?:-\s*){3,}|(?:\*\s*){3,}|(?:_\s*){3,})$", linha))


def sem_bloco(texto: str) -> str:
    """O documento sem o bloco de governança: o título, a abertura e os itens que a esteira escreve, com as linhas em
    branco entre eles. O que vem depois — título, régua ou texto do autor na mesma seção — fica, separado do que vinha
    antes por uma linha em branco. Idempotente; sem o bloco, devolve o texto como veio."""
    linhas = (texto or "").splitlines(keepends=True)
    saida: List[str] = []
    dentro, cerca, achou = False, False, False
    for linha in linhas:
        if _RE_CERCA.match(linha):
            cerca = not cerca
        if not cerca and _RE_TITULO_BLOCO.match(linha):
            dentro = achou = True
            while saida and not saida[-1].strip():
                saida.pop()
            continue
        if dentro:
            if not cerca and (not linha.strip() or _RE_LINHA_DO_BLOCO.match(linha)):
                continue
            dentro = False
            if saida and saida[-1].strip():
                saida.append("\n")
        saida.append(linha)
    if not achou:
        return texto or ""
    junto = "".join(saida)
    return junto if junto.endswith("\n") or not junto else junto + "\n"


def _secao(texto: str, numero: int, titulo: str) -> Optional[Tuple[int, int, int]]:
    """(início do conteúdo, fim, nível) da seção de pendências, fora do bloco: a que tem o número e o título; senão a
    que tem o título; senão a que tem o número — em cada caso, a mais alta na hierarquia. O handoff tem «### 7. Design»
    dentro do modelo de insumo antes de «## 7. Lacunas e pendências» (as sete sessões do acervo), e o PRD da exp05ef1b
    chama a 19 de «Riscos e mitigações» e põe as pendências em «Questões abertas e pendências humanas»."""
    titulos = [t for t in _titulos(texto) if not _RE_TITULO_BLOCO.match("# " + t[3])]
    por_numero = re.compile(rf"^{numero}\s*(?:\.(?![\dA-Za-z])|[—–-])")
    por_titulo = re.compile(titulo, re.I)

    def achar(cabe: Any) -> Optional[Tuple[int, int, int]]:
        candidatos = [(i, t) for i, t in enumerate(titulos) if cabe(t[3])]
        if not candidatos:
            return None
        i, (_, fim, nivel, _) = min(candidatos, key=lambda c: c[1][2])
        fim_secao = next((ini for ini, _, n, _ in titulos[i + 1:] if n <= nivel), len(texto))
        return fim, fim_secao, nivel

    return (achar(lambda nome: por_numero.match(nome) and por_titulo.search(nome))
            or achar(lambda nome: por_titulo.search(nome)) or achar(lambda nome: por_numero.match(nome)))


def com_pendencias(documento: str, gov: Optional[Dict[str, Any]], chave: str) -> str:
    """O documento com o bloco de governança no fim da seção de pendências, trocando o de uma rodada anterior.

    Sem pendência de governança, o documento sai sem bloco. O anexo literal do PRD (`tools/conteudo_aprovado.py`) fica
    onde está, depois. Sem a seção de pendências, o bloco entra no fim do corpo, como seção própria."""
    from tools.conteudo_aprovado import TITULO_ANEXO

    texto = sem_bloco(documento or "")
    if not texto.strip():
        return documento or ""
    # o corpo vai até o anexo literal, quando já há um (o PRD reescrito pela banca pode trazê-lo da versão anterior)
    anexo = next((ini for ini, _, nivel, nome in _titulos(texto) if nivel == 1 and nome.startswith(TITULO_ANEXO)), None)
    corpo, resto = (texto[:anexo], texto[anexo:]) if anexo is not None else (texto, "")
    if anexo is not None:
        # a régua que precede o título do anexo é dele
        m = re.search(r"\n\s*---\s*\n\s*$", corpo)
        if m:
            corpo, resto = corpo[:m.start() + 1], corpo[m.start() + 1:] + resto
    numero, titulo = SECAO_DE_PENDENCIAS.get(chave, SECAO_DE_PENDENCIAS["prd_final"])
    secao = _secao(corpo, numero, titulo)
    novo_bloco = bloco(gov, nivel=(secao[2] + 1) if secao else 2)
    if not novo_bloco:
        return texto
    if secao is None:
        ponto = len(corpo.rstrip())
    else:
        # no fim do conteúdo da seção, antes das linhas em branco e da régua que a separam da seguinte
        linhas = corpo[secao[0]:secao[1]].splitlines(keepends=True)
        while linhas and (not linhas[-1].strip() or _regua(linhas[-1])):
            linhas.pop()
        ponto = secao[0] + sum(len(l) for l in linhas)
    antes, depois = corpo[:ponto].rstrip(), corpo[ponto:]
    novo = f"{antes}\n\n{novo_bloco.rstrip()}\n"
    if depois.strip():
        novo += "\n" + depois.lstrip("\n")
    if resto:
        novo = novo.rstrip("\n") + "\n\n" + resto.lstrip("\n")
    return novo
