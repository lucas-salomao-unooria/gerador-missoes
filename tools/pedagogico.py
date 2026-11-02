"""O one-pager pedagógico fecha o design, montado sobre o contrato, e o de acordo de design é dado sobre ele.
Determinístico, sem LLM.

PR 10 do plano «Produto dono do contrato» (docs/planos/2026-10-23-produto-dono-do-contrato.md), combinado com o usuário
depois do plano de 23/10/2026. O time validava a missão pelos protótipos de design confrontados com o one-pager de
produto, que não descreve a missão inteira, e voltava para refazer porque não ficava claro o que a missão ia ser. O
pedagógico (A120) é o documento que descreve a missão inteira em linguagem de sala de aula, e era o último passo do dev:
o time o lia depois do PRD, com o design já aprovado. Agora ele fecha o design, e o de acordo de design é dado sobre ele.

Quatro peças:

- **Montagem sobre o contrato** (`montar`, A120b): o que o PO aprovou entra por código, num subtítulo «Do one-pager
  aprovado — …» no fim de cinco seções — as habilidades com o texto oficial (§12a), a régua do Canal A de cada habilidade
  (§12a), a tabela de tempos (§10), o podcast (§11) e o roteiro da conversa (textos-chave do §9) —, e
  a citação quase igual de um texto-chave volta ao texto aprovado (`tools/textos_chave.py`, PR 7). O LLM escreve só a
  narrativa de sala de aula e remete aos subtítulos. Idempotente: a montagem de uma rodada anterior é trocada.
- **Gate de montagem** (`validar`, A121b), no molde do gate do PRD (`tools/montagem.py`, PR 4): na narrativa, número de
  regra sem origem no contrato, hipótese do §17 ou teto do §15 com outro número, texto-chave reescrito, origem de produto
  falsa, tempo de etapa que não é o do §10, e subtítulo da esteira mexido. No changelog, só o número de antes de cada
  mudança fica fora da conferência; na pendência, só a linha marcada como proposta cujo número produto já registrou
  (`registro_conferido`). Habilidade, tempo total e podcast ficam com o A121 (`conteudo_aprovado.validar_pedagogico`),
  como o A116 ao lado do A116b no PRD.
- **O dev só acrescenta** (`no_dev`, A119b): as pendências da banca de dev e do rastro de lacunas do dev vão numa seção
  própria, guardada à parte (`pedagogico_pendencias_dev`) e juntada no fim do documento na exportação (`completo`). O
  texto aprovado no de acordo de design é conferido contra o retrato que o design gravou (`pedagogico_do_design`, A124)
  e volta a ele se mudou — e isso bloqueia: mudar o pedagógico em dev é pedido pela triagem ou Devolver, não edição.
- **O documento a aprovar** (`para_o_de_acordo`): o que o cartão do de acordo de design mostra, com os links do
  protótipo.

A sessão anterior ao PR 10 traz o pedagógico gerado em dev, sem os subtítulos da esteira: a leitura é tolerante (o gate
não cobra subtítulo de quem não tem nenhum), o refazer de design gera o novo, e o refazer só de dev não o apaga nem o
regenera — o pedagógico que existe passa a ser o retrato (`pipeline.reexecucao.preparar_estado`). A sessão desenhada
antes do PR 10 sem pedagógico o ganha no próximo design: no Iniciar, no refazer e também na correção pontual de design,
em que o redator escreve o documento que falta (`gerado_nesta_correcao`).
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

AGENTE = "montagem-pedagogico"
#: Quem corrige o documento: o redator (A120).
DONO = "one-pager-pedagogico"
#: O documento no estado, o retrato que o design deixa para o dev conferir e a seção que o dev acrescenta.
KEY = "one_pager_pedagogico"
KEY_RETRATO = "pedagogico_do_design"
KEY_SECAO_DEV = "pedagogico_pendencias_dev"
#: Onde o documento é gravado na sessão (o `.md`, o `.docx` e o `.html`). Até o PR 10 ficava na raiz.
ARQUIVO_BASE = "design/14-one-pager-pedagogico"
ARQUIVO_LEGADO = "one-pager-pedagogico"
#: O título de todo subtítulo que a esteira escreve no pedagógico. É também o marcador: sem comentário HTML, que
#: apareceria cru no `.docx` (o mesmo motivo do título do anexo, `tools/conteudo_aprovado.TITULO_ANEXO`).
PREFIXO_BLOCO = "Do one-pager aprovado —"
TITULO_SECAO_DEV = "Pendências do dev — acrescentadas pela esteira"
#: O motivo das trocas que a montagem registra na correção pontual (`edicoes_pontuais`).
MOTIVO_TROCA = "contrato do one-pager aprovado copiado por código no pedagógico (A120b, PR 10)"
#: Os gates do pedagógico no design: o A121, o A121b e o juiz A122.
GATES = ("conteudo_aprovado_pedagogico_status", "montagem_pedagogico_status", "coerencia_pedagogico_status")

#: Cada bloco da esteira, a seção do gabarito (`prompts/dev/120_one_pager_pedagogico.md`) em que ele entra — pelo começo
#: do título, sem acento nem caixa — e o título da seção quando o redator não a escreveu.
ALVOS: Tuple[Tuple[str, str, str, str], ...] = (
    ("habilidades", "o que a missao ensina", "O que a missão ensina", "as habilidades"),
    ("regua", "como a gente sabe", "Como a gente sabe que a criança aprendeu", "a régua de cada habilidade"),
    ("tempos", "quanto tempo leva", "Quanto tempo leva e como dividir em aulas", "os tempos"),
    ("podcast", "o podcast", "O podcast do fechamento", "o podcast"),
    ("roteiro", "o que voce faz", "O que você faz, professora", "o roteiro da conversa"),
)


# --------------------------------------------------------------------------- utilidades
def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")


def _titulo_norm(titulo: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", _sem_acento(titulo.strip("*_ ")))).strip()


_PREFIXO_NORM = _titulo_norm(PREFIXO_BLOCO)


def e_bloco(titulo: str) -> bool:
    """O título é de um subtítulo da esteira («Do one-pager aprovado — …»)."""
    return _titulo_norm(titulo).startswith(_PREFIXO_NORM)


def _pulo(texto: Any) -> bool:
    from pipeline.artifacts import e_mensagem_de_pulo

    return e_mensagem_de_pulo(texto)


def travado_nesta_correcao(state: Dict[str, Any]) -> bool:
    """O pedagógico é documento travado da correção pontual corrente: o editor de design o recebeu, e o documento é a
    versão anterior mais as trocas.

    Olha os documentos travados, e não só o modo: o `modo_correcao` da última correção ficava gravado no estado
    (60cfa7f4, b2e7b4a3, 4fd72a9a e e89e91b3 têm «pontual»), e o refazer de design e o Iniciar depois de uma correção
    pontual de produto pareciam correção pontual de design (revisão do PR #79, 24/10/2026)."""
    from agents.callbacks import KEY_DOCUMENTOS_TRAVADOS, KEY_MODO_CORRECAO

    return state.get(KEY_MODO_CORRECAO) == "pontual" and KEY in (state.get(KEY_DOCUMENTOS_TRAVADOS) or [])


def gerado_nesta_correcao(state: Dict[str, Any]) -> bool:
    """Correção pontual em que o redator gerou o pedagógico: ele não estava travado e existe agora.

    É a missão desenhada antes do PR 10, sem pedagógico (exp02em1b, exp01em1b e exp03em1b): o documento falta, e o
    redator o escreve mesmo na correção pontual de design — os demais documentos seguem travados. Os gates dele o julgam
    como na geração, com as rodadas de correção da geração (`SaidaDeLoopAgent.rodadas_com_autor_livre`): o texto é todo
    desta execução, e a linha de base não o rebaixa como «trecho que a correção não tocou»
    (`tools.linha_de_base.DOCUMENTO_NOVO`)."""
    from agents.callbacks import KEY_MODO_CORRECAO

    documento = state.get(KEY)
    return (state.get(KEY_MODO_CORRECAO) == "pontual" and not travado_nesta_correcao(state)
            and isinstance(documento, str) and bool(documento.strip()) and not _pulo(documento))


_RE_ENVELOPE = re.compile(r"^\s*```json\s*\{.*\}\s*```\s*$", re.S)


def partes(documento: str) -> Tuple[str, str, str]:
    """`(corpo, envelope, anexo)`: o texto do redator, o envelope JSON que ele fecha com (e a divisória antes dele) e o
    anexo literal que a esteira cola no fim. Juntos, em ordem, são o documento."""
    from tools.conteudo_aprovado import TITULO_ANEXO, remover_anexo

    texto = documento or ""
    anexo = ""
    if TITULO_ANEXO in texto:
        corpo = remover_anexo(texto).rstrip("\n")
        if texto.startswith(corpo):
            anexo, texto = texto[len(corpo):], corpo
    envelope = ""
    i = texto.rfind("```json")
    if i >= 0 and _RE_ENVELOPE.match(texto[i:]) and '"agente"' in texto[i:]:
        inicio = i
        antes = texto[:i].rstrip()
        if antes.endswith("---"):
            inicio = len(antes) - 3
        envelope, texto = texto[inicio:], texto[:inicio]
    return texto, envelope, anexo


def _titulos(texto: str) -> List[Tuple[int, int, int, str]]:
    from tools.conteudo_aprovado import _titulos as titulos

    return titulos(texto)


#: Divisória de seção (`---`): o redator costuma fechar cada seção com uma, e `_inserir` põe o bloco antes dela.
_RE_DIVISORIA = re.compile(r"^-{3,}[ \t]*$", re.M)


def _fim_do_bloco(texto: str, titulos: List[Tuple[int, int, int, str]], k: int) -> int:
    """Onde o subtítulo da esteira `titulos[k]` acaba: no próximo título de nível igual ou mais alto, ou antes, na
    divisória que fecha a seção. A divisória é do redator: contada no bloco, a primeira montagem já saía com o bloco
    «alterado» no A121b, e a segunda a apagava — no modo travado, trocas espúrias (revisão do PR #79, 24/10/2026)."""
    _, fim_titulo, nivel, _ = titulos[k]
    fim = next((i for i, _, n, _ in titulos[k + 1:] if n <= nivel), len(texto))
    divisoria = _RE_DIVISORIA.search(texto, fim_titulo, fim)
    return divisoria.start() if divisoria else fim


def sem_blocos(texto: str) -> str:
    """O texto sem os subtítulos da esteira (do título ao próximo título de nível igual ou mais alto, ou à divisória que
    fecha a seção)."""
    saida = texto or ""
    while True:
        titulos = _titulos(saida)
        k = next((k for k, t in enumerate(titulos) if e_bloco(t[3])), None)
        if k is None:
            return saida
        ini = titulos[k][0]
        fim = _fim_do_bloco(saida, titulos, k)
        saida = saida[:ini].rstrip("\n") + ("\n\n" + saida[fim:].lstrip("\n") if fim < len(saida) else "\n")


def narrativa(documento: str) -> str:
    """O que o redator escreveu: o corpo sem o anexo, sem o envelope e sem os subtítulos da esteira."""
    corpo, _, _ = partes(documento)
    return sem_blocos(corpo)


def blocos_presentes(documento: str) -> Dict[str, str]:
    """`{título normalizado: corpo}` de cada subtítulo da esteira que o documento traz."""
    corpo, _, _ = partes(documento)
    titulos = _titulos(corpo)
    saida: Dict[str, str] = {}
    for k, (_, fim_titulo, _, titulo) in enumerate(titulos):
        if not e_bloco(titulo):
            continue
        saida[_titulo_norm(titulo)] = corpo[fim_titulo:_fim_do_bloco(corpo, titulos, k)].strip()
    return saida


# --------------------------------------------------------------------------- os blocos do contrato
def _tabela_de_tempos(secao10: str) -> List[str]:
    """A primeira tabela do §10 que nomeia uma das seis etapas, linha por linha, como está."""
    from tools.conteudo_aprovado import _ETAPAS

    blocos: List[List[str]] = []
    atual: List[str] = []
    for linha in (secao10 or "").splitlines():
        if linha.strip().startswith("|"):
            atual.append(linha.rstrip())
        elif atual:
            blocos.append(atual)
            atual = []
    if atual:
        blocos.append(atual)
    for tabela in blocos:
        if any(re.search(rf"\b{e}\b", l, re.I) for l in tabela for e in _ETAPAS):
            return tabela
    return []


#: Rótulo de metadado do episódio no começo do §11 («**Duração total:**», «**Aviso ao professor:**»): a primeira palavra.
_METADADO_PODCAST = frozenset({"titulo", "formato", "duracao", "aviso", "apresentadores", "apresentador", "vozes",
                               "voz", "participantes", "momento", "publico", "tom", "objetivo", "nota", "quando",
                               "episodio"})
_RE_ROTULO = re.compile(r"^\s*(?:[-*]\s+)?[*_]*\(?\s*[*_]*([^:*_\n]{2,40}?)\s*:")


def _metadados_do_podcast(secao11: str) -> List[str]:
    """As linhas de abertura do §11 que descrevem o episódio — título, duração, quem fala, quando tocar, o aviso —, até
    a primeira fala, divisória, título ou bloco do roteiro. No máximo oito."""
    saida: List[str] = []
    for linha in (secao11 or "").splitlines():
        s = linha.strip()
        if not s:
            continue
        if s.startswith(("#", "---", "|")) or re.match(r"^[-*\s]*\**\s*\[?\s*bloco\b", _sem_acento(s)):
            break
        m = _RE_ROTULO.match(s)
        rotulo = _sem_acento(m.group(1)).split() if m else []
        if not rotulo or rotulo[0] not in _METADADO_PODCAST:
            if saida:
                break
            continue
        saida.append(s if re.match(r"^[-*]\s", s) else f"- {s}")
        if len(saida) >= 8:
            break
    return saida


def blocos_do_contrato(state: Dict[str, Any]) -> List[Tuple[str, str, str, str]]:
    """`[(nome, alvo, título do bloco, corpo)]`: o que a esteira põe no pedagógico, do one-pager aprovado e da spec de
    produto mais o anexo de design. Bloco sem conteúdo no contrato fica de fora (sem régua, sem roteiro); o podcast
    entra sempre, dizendo se há ou não."""
    from tools import bncc
    from tools import conteudo_aprovado as ca
    from tools import textos_chave as tk
    from tools.anexo_design import spec_consolidada

    one_pager = str(state.get("one_pager") or "")
    if not one_pager.strip():
        return []
    tcs = tk.da_sessao(state)
    corpos: Dict[str, List[str]] = {}

    codigos, origem = ca.habilidades_de_referencia(spec_consolidada(state), one_pager)
    if codigos:
        oficiais = bncc.habilidades()
        corpos["habilidades"] = [
            f"Copiadas pela esteira, com o texto oficial da BNCC uma vez só. Fonte: {origem}.", ""] + [
            (f"- **{c}** — «{oficiais[c]['habilidade']}»" if (oficiais.get(c) or {}).get("habilidade") else f"- **{c}**")
            for c in codigos]

    # a régua do Canal A de cada habilidade (§12a), no lugar da pergunta do fim: o Canal B saiu em 29/10/2026
    from tools import evidencia

    s12 = ca.secao(one_pager, 12) or ""
    m = evidencia._RE_12A_TITULO.search(s12)
    contrato = evidencia._contrato_12a(s12[m.start():]) if m else None
    reguas = [(c, " ".join(item["texto_a"].split())) for c, item in (contrato or {}).items() if item["texto_a"].strip()]
    if reguas:
        linhas = ["Copiada pela esteira do contrato de evidência (§12a), palavra por palavra: a ação que o estudante faz "
                  "na tela e o que separa Atingiu, Em processo e Não atingiu."]
        for c, regua in reguas:
            linhas += ["", f"- **{c}** — {regua}"]
        corpos["regua"] = linhas

    tabela = _tabela_de_tempos(ca.secao(one_pager, 10) or "")
    total = ca.tempo_aprovado(one_pager)
    if tabela or total is not None:
        linhas = ["Copiados pela esteira do one-pager aprovado (§10), sem mudar um número."]
        if tabela:
            linhas += [""] + tabela
        if total is not None:
            linhas += ["", f"**Total em tela:** {total} min."]
        corpos["tempos"] = linhas

    if ca.tem_podcast(one_pager):
        meta = _metadados_do_podcast(ca.secao(one_pager, 11) or "")
        corpos["podcast"] = (["Copiado pela esteira do one-pager aprovado (§11). O roteiro inteiro, palavra por palavra, "
                              "está no anexo."] + ([""] + meta if meta else []))
    else:
        corpos["podcast"] = ["O one-pager aprovado não tem podcast de recapitulação (§11)."]

    roteiro = [t for t in tcs if t.tipo == tk.ROTEIRO]
    if roteiro:
        # «como o PO aprovou» era lido pelo A121 (`tools.decisoes.achados`) como decisão atribuída ao PO: 🟡, e ⛔ sem
        # parecer humano (exp02em1b e exp01em1b; 3ª revisão do PR #79, 24/10/2026)
        corpos["roteiro"] = (["As perguntas da conversa, como o one-pager aprovado as traz (§9), para ler em voz alta no "
                              "momento em que o one-pager as põe:", ""]
                             + [f"{n}. «{t.texto}» ({t.id})" for n, t in enumerate(roteiro, 1)])

    return [(nome, alvo, f"{PREFIXO_BLOCO} {sufixo}", "\n".join(corpos[nome]).strip())
            for nome, alvo, _, sufixo in ALVOS if nome in corpos]


def _secao_do_alvo(texto: str, alvo: str) -> Optional[Tuple[int, int]]:
    """`(início, fim)` da seção `## ` cujo título começa com `alvo` (sem acento nem caixa); None sem ela."""
    titulos = _titulos(texto)
    for k, (ini, _, nivel, titulo) in enumerate(titulos):
        if nivel == 2 and _titulo_norm(titulo).startswith(alvo):
            fim = next((i for i, _, n, _ in titulos[k + 1:] if n <= 2), len(texto))
            return ini, fim
    return None


def _inserir(texto: str, alvo: str, titulo_secao: str, titulo_bloco: str, corpo: str) -> str:
    """O bloco no fim da seção-alvo — antes da divisória que a fecha, se houver; sem a seção, ela é criada no fim."""
    bloco = f"### {titulo_bloco}\n\n{corpo.strip()}\n"
    lugar = _secao_do_alvo(texto, alvo)
    if lugar is None:
        return texto.rstrip("\n") + f"\n\n## {titulo_secao}\n\n{bloco}"
    _, fim = lugar
    antes, depois = texto[:fim].rstrip(), texto[fim:]
    divisoria = ""
    if antes.endswith("\n---"):
        antes, divisoria = antes[:-4].rstrip(), "---\n\n"
    return antes + "\n\n" + bloco + ("\n" + divisoria + depois.lstrip("\n") if depois.strip() else "")


def montar(documento: str, state: Dict[str, Any]) -> str:
    """O pedagógico com o contrato no lugar: os subtítulos da esteira trocados pelos de agora, e a citação quase igual de
    um texto-chave de volta ao texto aprovado. O envelope e o anexo ficam onde estavam. Documento vazio ou mensagem de
    pulo volta como veio."""
    from tools import textos_chave as tk

    if not str(documento or "").strip() or _pulo(documento):
        return documento
    corpo, envelope, anexo = partes(documento)
    tcs = tk.da_sessao(state)
    if tcs:
        copia = str(state.get("copy_strings_revisada") or state.get("copy_strings") or "")
        propostas = tk.aplicar_na_copy(copia, tcs)["propostas"] if copia.strip() else []
        corpo, _ = tk.aplicar_em_documento(corpo, tcs, propostas)
    corpo = sem_blocos(corpo).rstrip("\n")
    titulos_secao = {nome: titulo for nome, _, titulo, _ in ALVOS}
    for nome, alvo, titulo, texto in blocos_do_contrato(state):
        corpo = _inserir(corpo, alvo, titulos_secao[nome], titulo, texto)
    novo = corpo.rstrip("\n") + "\n"
    if envelope:
        novo += "\n" + envelope.lstrip("\n")
    if anexo:
        novo = novo.rstrip("\n") + anexo
    return novo


# --------------------------------------------------------------------------- o gate de montagem
#: Hipótese citada pelo número na narrativa: «Hipótese 1», «H1».
_RE_HIPOTESE_CITADA = re.compile(r"\bH0*(\d{1,2})\b|hip[óo]tese\s+0*(\d{1,2})\b", re.I)


def _achado(codigo: str, resumo: str, severidade: str = "bloqueio") -> Dict[str, str]:
    return {"severidade": severidade, "codigo": codigo, "etapa": "design", "agente_responsavel": DONO, "resumo": resumo}


def contrato_firme(state: Dict[str, Any]) -> Tuple[Dict[str, str], str]:
    """`(documentos do contrato, texto de origem)`: o contrato do gate do PRD (`montagem.contrato`) — one-pager, núcleo,
    briefing, spec de produto, a lista branca do bloco 13 do anexo de design e as decisões do PO — sem o que é proposta.
    O pedagógico é o que o time aprova como a missão: número que só existe numa linha `[PROPOSTA]` ou `[PARÂMETRO]` ainda
    não é decisão (a PQ-01 «>25%» da exp02ef1b, D11), e no PRD ele ainda valia como origem do alvo que o KPI copia."""
    from tools import montagem

    docs = montagem.contrato(state)
    return docs, montagem.texto_do_contrato({k: montagem.sem_linhas_abertas(v) for k, v in docs.items()})


def _sem_secoes(texto: str, cabe) -> str:
    """O texto sem cada seção cujo `(nível, título normalizado)` `cabe`, do título ao próximo de nível igual ou mais
    alto."""
    saida = texto or ""
    while True:
        titulos = _titulos(saida)
        k = next((k for k, t in enumerate(titulos) if cabe(t[2], _titulo_norm(t[3]))), None)
        if k is None:
            return saida
        ini, _, nivel, _ = titulos[k]
        fim = next((i for i, _, n, _ in titulos[k + 1:] if n <= nivel), len(saida))
        saida = saida[:ini] + saida[fim:]


def sem_preparo(texto: str) -> str:
    """A narrativa sem os subtítulos «Antes da aula» (o preparo do professor, `E0-PROF`): o preparo é padrão da
    plataforma, igual em toda missão (D7), e o número dele não é regra desta missão — «a página da missão com duas
    opções simples», no pedagógico da exp02ef1b, é a tela de recorte da aula, não uma escolha da criança."""
    return _sem_secoes(texto, lambda nivel, titulo: nivel >= 3 and titulo.startswith("antes da aula"))


#: As seções do gabarito (`prompts/dev/120_one_pager_pedagogico.md`) que registram: a de pendências, onde o prompt manda
#: pôr a proposta ainda aberta («como proposta»), e o changelog, que traz o número de antes da mudança. Correspondem à
#: §19 e à §22 do PRD, mas não ficam fora da conferência inteiras, como lá (`montagem._linhas_do_corpo`): o changelog
#: afirma o estado novo da missão, e a pendência pode trazer número que não existe nem como proposta
#: (`registro_conferido`). «O que precisamos que você aprove» fica na conferência inteira: são perguntas ao time
#: pedagógico, e o prompt não manda proposta para lá.
SECOES_DE_REGISTRO = ("o que ainda esta em aberto", "o que mudou nesta versao")
CHANGELOG = SECOES_DE_REGISTRO[1]

_NUM = r"(?:\d+(?:[.,]\d+)?|(?:um|uma|dois|duas|tr[êe]s|quatro|cinco|seis|sete|oito|nove|dez)\b)"
_QUALIFICADOR = r"(?:(?:at[ée]|mais\s+de|menos\s+de|cerca\s+de|acima\s+de|abaixo\s+de|no\s+m[áa]ximo|no\s+m[íi]nimo)\s+)?"
_UNIDADE = (r"(?:\s?%|\s?(?:segundos?|seg|s|minutos?|min|palavras|caracteres|op[çc](?:[ãa]o|[õo]es)|alternativas?|"
            r"tentativas?|rodadas?)\b)?")
_VALOR = rf"{_QUALIFICADOR}[<>≤≥~]?\s*{_NUM}{_UNIDADE}"
#: O número de antes de uma mudança, no changelog: «de 30% para 25%», «de até 12 para até 10 palavras», «de 25% das
#: duplas para 30%» (o «de X» com «para» e outro número depois), «era 25%», «(antes: 25%)» e «30% → 25%». O «de X a Y»
#: fica de fora: é também faixa («de 8 a 10 palavras»), e a faixa é o estado novo.
_RE_NUMERO_DE_ANTES = (
    re.compile(rf"\bde\s+{_VALOR}(?:\s+[^\s\d]+){{0,3}}?(?=\s+para\s+{_QUALIFICADOR}[<>≤≥~]?\s*{_NUM})", re.I),
    re.compile(rf"\b(?:era|eram|antes)\b\s*[:,]?\s*{_VALOR}", re.I),
    re.compile(rf"{_VALOR}\s*(?:→|->|⟶|⇒|=>)", re.I),
)
#: Marca de proposta numa linha de pendência: `[PROPOSTA …]`, a palavra «proposta» ou o ID de uma pergunta de produto
#: (PQ-NN, do 9f da spec).
_RE_MARCA_DE_PROPOSTA = re.compile(r"\[PROPOSTA|\bpropostas?\b|\bPQ-?\d+\b", re.I)


def sem_numero_de_antes(linha: str) -> str:
    """A linha do changelog sem o número de antes de cada mudança (`_RE_NUMERO_DE_ANTES`): o resto é o estado novo."""
    for r in _RE_NUMERO_DE_ANTES:
        linha = r.sub(" ", linha)
    return linha


def _fora_do_registro(linha: str, contrato_inteiro: str, contagens: set) -> List[Dict[str, str]]:
    """Os números de regra e as contagens da linha que o contrato não tem nem como proposta."""
    from tools import montagem
    from tools.propagacao import _fmt, tem_numero

    resumo = re.sub(r"\s+", " ", linha).strip()[:180]
    saida = [{"numero": _fmt(t), "linha": resumo}
             for t in montagem.numeros_de_regra(linha) if not tem_numero(contrato_inteiro, t)]
    if not montagem.de_plataforma(linha):
        saida += [{"numero": f"{n} {u}", "linha": resumo}
                  for n, u in montagem._contagens(montagem._RE_CITACAO.sub(" ", linha)) if (n, u) not in contagens]
    return saida


def registro_conferido(texto: str, contrato_inteiro: str) -> Tuple[str, List[Dict[str, str]]]:
    """`(o que a narrativa afirma, números de proposta sem registro)`: a narrativa como o A121b a confere.

    - No changelog («O que mudou nesta versão») sai só o número de antes de cada mudança (`sem_numero_de_antes`); o de
      destino («para Y», o que vem depois da seta) é o estado novo da missão e é conferido como na narrativa.
    - Na pendência («O que ainda está em aberto»), a linha sem marca de proposta é conferida como na narrativa. A linha
      marcada (`_RE_MARCA_DE_PROPOSTA`) sai da conferência de número, hipótese e teto quando cada número dela está no
      contrato inteiro, com as propostas (`contrato_inteiro`: one-pager, spec, decisões, marcadores abertos inclusive);
      o número que não está nem como proposta volta na segunda lista, e bloqueia.

    Até a 2ª revisão do PR #79 (24/10/2026) o A121b conferia a narrativa inteira e bloqueava o que a esteira manda
    escrever: a proposta em «O que ainda está em aberto» (os 40% da PQ-01 da exp02em1b, os 25% da PQ-01 da exp02ef1b), a
    recondução da H1 de 25% para 30% no changelog da exp02ef1b (D11). A isenção que veio dela tirava as duas seções
    inteiras e virou porta (3ª revisão, 24/10/2026): «A hipótese 1 passou de 30% para 25%», «a meta passou para 47%»
    citando o §15, «Hipótese 1: 25% das crianças» sem marca e «7 alternativas» inventadas passavam 🟢 nas 4 missões a
    refazer."""
    from tools import montagem

    texto = texto or ""
    contagens = set(montagem._contagens(contrato_inteiro))
    titulos = _titulos(texto)
    pedacos: List[str] = []
    sem_registro: List[Dict[str, str]] = []
    pos = 0
    for k, (ini, fim_titulo, nivel, titulo) in enumerate(titulos):
        norm = _titulo_norm(titulo)
        if nivel != 2 or ini < pos or not norm.startswith(SECOES_DE_REGISTRO):
            continue
        fim = next((i for i, _, n, _ in titulos[k + 1:] if n <= 2), len(texto))
        linhas: List[str] = []
        for linha in texto[fim_titulo:fim].splitlines(keepends=True):
            if norm.startswith(CHANGELOG):
                linhas.append(sem_numero_de_antes(linha))
            elif _RE_MARCA_DE_PROPOSTA.search(linha):
                sem_registro += _fora_do_registro(linha, contrato_inteiro, contagens)
            else:
                linhas.append(linha)
        pedacos.append(texto[pos:fim_titulo] + "".join(linhas))
        pos = fim
    pedacos.append(texto[pos:])
    return "".join(pedacos), sem_registro


def hipoteses_citadas(texto: str, one_pager: str) -> List[Dict[str, str]]:
    """Linha da narrativa que cita a hipótese pelo número com outro número da mesma unidade que a hipótese do §17 tem
    (H1 com 25% no lugar dos 30% aprovados — a cadeia da exp02ef1b)."""
    from tools.conteudo_aprovado import secao
    from tools.montagem import _itens_de_hipotese, _numeros_de_hipotese
    from tools.propagacao import _fmt, tem_numero

    do_17 = _itens_de_hipotese(secao(one_pager or "", 17) or "")
    saida: List[Dict[str, str]] = []
    for linha in (texto or "").splitlines():
        for m in _RE_HIPOTESE_CITADA.finditer(linha):
            n = int(m.group(1) or m.group(2))
            if n not in do_17:
                continue
            aprovados = _numeros_de_hipotese(do_17[n])
            unidades = {u for _, u in aprovados}
            fora = [t for t in _numeros_de_hipotese(linha) if t[1] in unidades and not tem_numero(do_17[n], t)]
            if fora:
                saida.append({"hipotese": f"H{n}", "contrato": ", ".join(_fmt(t) for t in aprovados if t[1] in
                                                                       {u for _, u in fora}),
                              "corpo": ", ".join(_fmt(t) for t in fora), "linha": linha.strip()[:200]})
                break
    return saida


#: Semelhança mínima (`textos_chave.semelhanca`) para a citação ser outra redação do texto-chave; abaixo de 30
#: caracteres, só o quase idêntico. Com 0,6, a descoberta em primeira pessoa que abre o pedagógico da exp01ef1b («Achei
#: que o menino estava assustado com um acidente…», 0,62) contava como reescrita da pergunta do debate («Quem achou que o
#: menino estava assustado ou em perigo…»). Acima de 0,85 o A120b já troca pelo texto aprovado.
SEMELHANCA_REESCRITA = 0.7
SEMELHANCA_REESCRITA_CURTA = 0.8


def textos_chave_reescritos(texto: str, state: Dict[str, Any]) -> List[Tuple[str, str]]:
    """`(aprovado, como a narrativa escreveu)`: citação entre aspas da narrativa que é outra redação de um texto-chave
    (`tools/textos_chave.py`) ou de um texto literal do one-pager (Canal B, debate, texto de tela do §4).

    No PRD, a citação reescrita só conta quando o texto aprovado não está em lugar nenhum do corpo (`literais_
    parafraseados`). No pedagógico o texto aprovado está sempre no corpo — no subtítulo da esteira —, e a narrativa que o
    reescreve ao lado mostra ao time duas versões do mesmo texto: cada citação reescrita conta."""
    from tools import montagem
    from tools import textos_chave as tk

    saida: List[Tuple[str, str]] = []
    tcs = [t for t in tk.da_sessao(state) if t.tipo in tk.TIPOS_DE_TEXTO and tk.palavras(t.texto) >= 3]
    for m in re.finditer(r"[\"“«]([^\"”»\n]{12,400})[\"”»]", texto or ""):
        citado = m.group(1).strip().strip("*").strip()
        if not tcs or any(tk.mesmo_texto(t.texto, citado) for t in tcs):
            continue
        melhor, valor = None, 0.0
        for t in tcs:
            if tk.mesmos_numeros(t, citado):
                v = tk.semelhanca(t.texto, citado)
                if v > valor:
                    melhor, valor = t, v
        corte = SEMELHANCA_REESCRITA if len(melhor.texto if melhor else "") >= 30 else SEMELHANCA_REESCRITA_CURTA
        if melhor is not None and valor >= corte and (melhor.texto, citado) not in saida:
            saida.append((melhor.texto, citado))
    for par in montagem.textos_chave_reescritos(texto, str(state.get("one_pager") or "")):
        if par not in saida and not any(tk.mesmo_texto(a, par[0]) and c == par[1] for a, c in saida):
            saida.append(par)
    return saida


def validar(state: Dict[str, Any]) -> Dict[str, Any]:
    """A narrativa do pedagógico contra o contrato, e os subtítulos da esteira contra o que o contrato diz agora."""
    from tools import conteudo_aprovado as ca
    from tools import montagem
    from tools.propagacao import contrato_no_corpo

    documento = str(state.get(KEY) or "")
    if not documento.strip() or _pulo(documento):
        return {"status": "aprovado", "achados": [], "contagem": {"documento": 0}}
    one_pager = str(state.get("one_pager") or "")
    texto = narrativa(documento)
    # número, hipótese, teto e origem citada, no que a narrativa afirma: sem o número de antes do changelog e sem a
    # proposta registrada da pendência (`registro_conferido`, revisões do PR #79). Texto-chave e tempo de etapa valem no
    # texto todo
    docs, origem = contrato_firme(state)
    afirmado, sem_registro = registro_conferido(texto, "\n".join(docs.values()))
    achados: List[Dict[str, str]] = []

    # 🟡, como no PRD e no handoff (C7, 25/10/2026): o que é «número de regra» é leitura de sentido (`tools/severidade.py`)
    from tools.severidade import BLOQUEIO, INTERPRETACAO, por_prova

    sem_origem = montagem.numeros_sem_origem(sem_preparo(afirmado), origem)
    if sem_origem:
        achados.append(_achado(
            "numero-sem-origem",
            f"{len(sem_origem)} número(s) de regra na narrativa do pedagógico não estão no contrato (one-pager, spec de "
            "produto, decisões da lista branca do anexo de design, decisões do PO no de acordo) — ou só estão numa "
            "proposta ainda aberta: " + montagem._exemplos(f"{i['numero']} em «{i['linha'][:110]}»" for i in sem_origem)
            + ". O pedagógico monta, não decide: copie o número do one-pager, ou remeta ao subtítulo «Do one-pager "
            "aprovado» que o traz. Proposta em aberto entra em «O que ainda está em aberto», marcada como proposta "
            "(«[PROPOSTA…]», «proposta» ou o ID da PQ) e com o número que produto registrou. No changelog, só o número de "
            "antes («de X para…», «era X») fica fora da conferência: o de agora é o da missão. Não bloqueia: o código "
            "não sabe com certeza se cada número é de regra — confira.", por_prova(BLOQUEIO, INTERPRETACAO)))
    if sem_registro:
        achados.append(_achado(
            "numero-sem-origem",
            f"{len(sem_registro)} número(s) numa linha de proposta de «O que ainda está em aberto» não estão no contrato "
            "nem como proposta registrada (one-pager, spec, decisões do PO): "
            + montagem._exemplos(f"{i['numero']} em «{i['linha'][:110]}»" for i in sem_registro)
            + ". A pendência registra a proposta que produto já fez, com o número dela; número novo é decisão do PO, "
            "pedida no Refazer, que a triagem leva a Produto. Não bloqueia: o código não sabe com certeza se cada "
            "número é de regra — confira.", por_prova(BLOQUEIO, INTERPRETACAO)))

    hipoteses = hipoteses_citadas(afirmado, one_pager)
    vistos = {(h["hipotese"], h["corpo"]) for h in hipoteses}
    for c in contrato_no_corpo(one_pager, afirmado, secoes=(15, 17)):
        if c["situacao"] != "trocado":
            continue
        if c["secao"] == "§17" and any(set(c["corpo"].split(", ")) <= set(h["corpo"].split(", ")) for h in hipoteses):
            continue
        chave = (c["secao"], c["corpo"])
        if chave in vistos:
            continue
        vistos.add(chave)
        codigo = "hipotese-diverge" if c["secao"] == "§17" else "teto-diverge"
        achados.append(_achado(codigo, (
            f"O {c['secao']} do one-pager diz {c['contrato']} («{c['linha'][:120]}»), e a narrativa do pedagógico escreve "
            f"{c['corpo']}: «{c['linha_corpo'][:140]}». O pedagógico diz o que o one-pager diz, com os números dele; "
            "outro número, como proposta, entra em «O que ainda está em aberto».")))
    for h in hipoteses:
        achados.append(_achado("hipotese-diverge", (
            f"A {h['hipotese']} do §17 do one-pager diz {h['contrato']}, e a narrativa do pedagógico escreve {h['corpo']}: "
            f"«{h['linha'][:140]}». A hipótese é a do one-pager aprovado; outro número é decisão do PO e, como proposta, "
            "entra em «O que ainda está em aberto».")))

    reescritos = textos_chave_reescritos(texto, state)
    if reescritos:
        achados.append(_achado(
            "texto-chave-reescrito",
            f"{len(reescritos)} texto(s) que o PO aprovou palavra por palavra aparecem na narrativa do pedagógico com "
            "outra redação: " + montagem._exemplos(f"aprovado «{a[:80]}» → «{c[:80]}»" for a, c in reescritos)
            + ". A narrativa cita o texto aprovado ou remete ao subtítulo «Do one-pager aprovado» que o traz — nunca uma "
            "terceira versão; mudança é pedido do PO no Refazer, que a triagem leva a Produto."))

    falsas = montagem.origens_falsas(afirmado, docs)
    if falsas:
        achados.append(_achado(
            "origem-de-produto-falsa",
            f"{len(falsas)} citação(ões) dão origem de produto ao que produto não decidiu: "
            + montagem._exemplos((f"{f['numero']} citado como «{f['fonte']}», que não o tem: «{f['linha'][:100]}»"
                                  if f["tipo"] == "numero" else
                                  f"{f['ids']} apresentado como produto: «{f['linha'][:100]}»") for f in falsas)
            + ". Decisão do design é do design; número cita a fonte que o tem."))

    etapas = ca.tempos_de_etapa_divergentes(texto, one_pager)
    if etapas:
        achados.append(_achado(
            "tempo-de-etapa-divergente",
            "A narrativa do pedagógico dá a uma etapa outro tempo em tela que a tabela do §10 aprovada: "
            + montagem._exemplos(f"{e}: aprovado {a} min → «{l[:110]}»" for e, a, l in etapas)
            + ". A tabela aprovada já está no subtítulo «Do one-pager aprovado — os tempos»: não a reescreva."))

    presentes = blocos_presentes(documento)
    esperados = blocos_do_contrato(state)
    mexidos: List[str] = []
    faltando: List[str] = []
    if presentes:
        for _, _, titulo, corpo in esperados:
            atual = presentes.get(_titulo_norm(titulo))
            if atual is None:
                faltando.append(titulo)
            elif _linhas(atual) != _linhas(corpo):
                mexidos.append(titulo)
    _re_cb = re.compile(r"\bcanal\s*b\b|\bmultipla_escolha\b", re.I)
    if _re_cb.search(texto) and not _re_cb.search(origem):
        achados.append(_achado("canal-b-removido", (
            "A narrativa do one-pager pedagógico cita Canal B ou pergunta de múltipla escolha. O Canal B foi "
            "removido da esteira: toda evidência pedagógica é exclusivamente do Canal A (ação observada).")))
    _re_e6 = re.compile(r"\betapa\s*6\b|\bE6[-_](?:ALU|PROF|SIS)\b|\bmomento\s+6\.\d", re.I)
    if _re_e6.search(texto) and not _re_e6.search(origem):
        achados.append(_achado("etapa-6-removida", (
            "A narrativa do one-pager pedagógico cita a Etapa 6 (`E6-*` / `Momento 6.x`): a missão termina na "
            "Etapa 5 (Explicar) e não tem Etapa 6 de transferência.")))
    if faltando:
        achados.append(_achado("bloco-do-contrato-ausente", (
            f"O pedagógico não traz {len(faltando)} subtítulo(s) da esteira que o contrato tem: "
            + "; ".join(f"«{t}»" for t in faltando) + ". Eles são montados por código (A120b): não os apague.")))
    if mexidos:
        achados.append(_achado("bloco-do-contrato-alterado", (
            f"{len(mexidos)} subtítulo(s) da esteira diferem do contrato de agora: "
            + "; ".join(f"«{t}»" for t in mexidos) + ". O texto deles é copiado por código do one-pager aprovado; mudança "
            "nele é pedido do PO, que a triagem leva a Produto.")))

    status = "bloqueado" if any(a["severidade"] == "bloqueio" for a in achados) else ("amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados,
            "contagem": {"documento": 1, "numeros_sem_origem": len(sem_origem) + len(sem_registro),
                         "hipoteses": len([a for a in achados if a["codigo"] == "hipotese-diverge"]),
                         "textos_chave_reescritos": len(reescritos), "origens_falsas": len(falsas),
                         "tempos_de_etapa": len(etapas), "blocos": len(presentes), "blocos_esperados": len(esperados),
                         "legado": not presentes}}


def _linhas(texto: str) -> List[str]:
    return [re.sub(r"\s+", " ", l).strip() for l in (texto or "").splitlines() if l.strip()]


def relatorio(resultado: Dict[str, Any], missao: str = "") -> str:
    icone = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}[resultado["status"]]
    L = [f"# Pedagógico monta, não decide — {missao or 'missão'}", "",
         f"**Veredito: {icone}** · a narrativa contra o contrato (one-pager, spec de produto, lista branca do anexo de "
         "design, decisões do PO): números de regra, hipóteses e tetos e origem citada (no changelog, sem o número de antes "
         "de cada mudança; na pendência, sem a linha marcada como proposta cujo número produto já registrou), "
         "textos-chave e tempos por etapa; e os subtítulos «Do one-pager aprovado», que a esteira monta por código.", ""]
    if resultado.get("contagem", {}).get("legado") and resultado.get("contagem", {}).get("documento"):
        L += ["> Pedagógico sem os subtítulos da esteira: gerado antes de 24/10/2026, no dev. A narrativa é conferida do "
              "mesmo jeito; o refazer de design o monta sobre o contrato.", ""]
    if not resultado["achados"]:
        L.append("- O que a narrativa afirma de produto está no contrato, com os mesmos números e os mesmos textos.")
    for a in resultado["achados"]:
        L.append(f"- {'⛔' if a['severidade'] == 'bloqueio' else '⚠️'} `{a['codigo']}` — {a['resumo']}")
    envelope = {"agente": AGENTE, "missao": missao or "", "status": resultado["status"],
                "achados": [{"severidade": a["severidade"], "classe": "montagem", "codigo": a["codigo"],
                             "etapa": a["etapa"], "agente_responsavel": a["agente_responsavel"], "resumo": a["resumo"]}
                            for a in resultado["achados"]],
                "precisa_humano": False}
    return "\n".join(L) + "\n\n```json\n" + json.dumps(envelope, ensure_ascii=False) + "\n```\n"


# --------------------------------------------------------------------------- o dev só acrescenta
_ICONE = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}


def _icone(status: Any) -> str:
    v = str(status or "").strip().lower()
    return _ICONE.get(v, "🟡" if v in ("apto_com_ressalvas", "ressalvas") else "⚪")


def secao_do_dev(state: Dict[str, Any]) -> str:
    """A seção que o dev acrescenta no fim do pedagógico: as pendências da banca de dev e do rastro de lacunas do dev,
    com o dono de cada uma. Vazia quando o dev não chegou a nenhum dos dois."""
    fontes = (("Banca de dev", "dev_status"), ("Rastro de lacunas do dev", "rastro_lacunas_status"))
    partes_dev: List[str] = []
    for rotulo, chave in fontes:
        envelope = state.get(f"{chave}_envelope")
        status = state.get(chave)
        if not status and not isinstance(envelope, dict):
            continue
        achados = [a for a in ((envelope or {}).get("achados") if isinstance(envelope, dict) else None) or []
                   if isinstance(a, dict)]
        partes_dev += [f"## {rotulo} — {_icone(status)} {len(achados)} pendência(s)", ""]
        if not achados:
            partes_dev.append("Nenhuma pendência.")
        for a in achados:
            ident = str(a.get("id") or a.get("codigo") or "achado")
            dono = str(a.get("agente_responsavel") or a.get("etapa") or "—")
            resumo = re.sub(r"\s+", " ", str(a.get("resumo") or "")).strip(" -")
            marca = "⛔" if str(a.get("severidade") or "") == "bloqueio" else "⚠️"
            partes_dev.append(f"- {marca} `{ident}` · dono `{dono}` — {resumo[:400]}")
        partes_dev.append("")
    if not partes_dev:
        return ""
    return "\n".join([
        "---", "", f"# {TITULO_SECAO_DEV}", "",
        "> Acrescentada por código no fim do dev, depois do de acordo de design: o texto acima é o que o time aprovou, e o "
        "dev não o muda. Aqui ficam só as pendências que a banca de dev e o rastro de lacunas do dev deixaram, com o dono "
        "de cada uma. Mudar o que está acima é pedido no parecer — o Refazer passa pela triagem e leva a Produto o que é "
        "de produto e ao Design o que é do pedagógico —, ou Devolver ao Design; não edição deste documento.", "",
    ] + partes_dev).rstrip() + "\n"


def completo(state: Dict[str, Any]) -> str:
    """O pedagógico como sai para gente ler: o aprovado no de acordo de design e, no fim, a seção do dev."""
    documento = str(state.get(KEY) or "")
    secao = str(state.get(KEY_SECAO_DEV) or "")
    if not documento.strip() or _pulo(documento) or not secao.strip():
        return documento
    return documento.rstrip("\n") + "\n\n" + secao.lstrip("\n")


def assinatura(texto: str) -> str:
    return hashlib.sha256((texto or "").encode("utf-8")).hexdigest()[:16]


def no_dev(state: Dict[str, Any]) -> Dict[str, Any]:
    """O que o dev faz com o pedagógico: confere que o texto é o do retrato do design (e o devolve a ele se mudou) e
    monta a seção das pendências do dev. `{status, achados, restaurar, secao}`."""
    atual = str(state.get(KEY) or "")
    retrato = str(state.get(KEY_RETRATO) or "")
    achados: List[Dict[str, str]] = []
    restaurar: Optional[str] = None
    if not atual.strip() or _pulo(atual):
        if retrato.strip():
            restaurar = retrato
            achados.append({"severidade": "bloqueio", "codigo": "pedagogico-apagado-no-dev", "etapa": "dev",
                            "agente_responsavel": "dev",
                            "resumo": "O pedagógico aprovado no de acordo de design sumiu durante o dev e voltou ao "
                                      "retrato do design. O dev não escreve nem apaga o pedagógico."})
        else:
            achados.append({"severidade": "atencao", "codigo": "pedagogico-ausente", "etapa": "design",
                            "agente_responsavel": DONO,
                            "resumo": "A missão não tem o one-pager pedagógico: desde 24/10/2026 (PR 10) ele fecha o "
                                      "design, e esta sessão passou pelo design antes disso. O dev não o gera — refaça o "
                                      "design (ou Devolva ao Design) para tê-lo."})
    elif retrato.strip() and atual != retrato:
        restaurar = retrato
        achados.append({"severidade": "bloqueio", "codigo": "pedagogico-reescrito-no-dev", "etapa": "dev",
                        "agente_responsavel": "dev",
                        "resumo": (f"O pedagógico mudou durante o dev (retrato do design {assinatura(retrato)}, agora "
                                   f"{assinatura(atual)}) e voltou ao texto aprovado no de acordo de design. O dev só "
                                   "acrescenta as pendências dele numa seção própria; mudar o pedagógico é pedido no "
                                   "parecer, pela triagem, ou Devolver ao Design.")})
    status = "bloqueado" if any(a["severidade"] == "bloqueio" for a in achados) else ("amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados, "restaurar": restaurar, "secao": secao_do_dev(state)}


def relatorio_no_dev(resultado: Dict[str, Any], missao: str = "") -> str:
    icone = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴"}[resultado["status"]]
    L = [f"# Pedagógico no dev — {missao or 'missão'}", "",
         f"**Veredito: {icone}** · o pedagógico aprovado no de acordo de design, conferido contra o retrato do design, "
         "e as pendências do dev acrescentadas numa seção própria no fim.", ""]
    if not resultado["achados"]:
        L.append("- O pedagógico é o aprovado no de acordo de design, palavra por palavra.")
    for a in resultado["achados"]:
        L.append(f"- {'⛔' if a['severidade'] == 'bloqueio' else '⚠️'} `{a['codigo']}` — {a['resumo']}")
    if resultado.get("secao"):
        L += ["", "## A seção acrescentada", "", resultado["secao"].replace("\n# ", "\n### ").replace("\n## ", "\n#### ")]
    envelope = {"agente": "pedagogico-no-dev", "missao": missao or "", "status": resultado["status"],
                "achados": resultado["achados"], "precisa_humano": False}
    return "\n".join(L) + "\n\n```json\n" + json.dumps(envelope, ensure_ascii=False) + "\n```\n"


# --------------------------------------------------------------------------- o documento a aprovar
_RE_STITCH = re.compile(r"https://stitch\.withgoogle\.com/projects/\d+")
_RE_MIRO = re.compile(r"https://miro\.com/app/board/[^\s)\]>|]+")


def links_do_prototipo(state: Dict[str, Any]) -> List[Dict[str, str]]:
    """Os links que o cartão do de acordo de design mostra ao lado do pedagógico: o protótipo navegável, os diagramas,
    o projeto no Stitch e o board no Miro — só os que a sessão tem."""
    links: List[Dict[str, str]] = []
    if str(state.get("prototipo_arquivo") or state.get("prototipo_html") or "").strip():
        links.append({"rotulo": "Protótipo navegável", "alvo": "design/08-prototipo.html"})
    if str(state.get("diagramas_html") or "").strip():
        links.append({"rotulo": "Jornada e fluxo desenhados", "alvo": "design/09-diagramas.html"})
    stitch = _RE_STITCH.search(str(state.get("stitch_links") or ""))
    if stitch:
        links.append({"rotulo": "Telas no Stitch", "alvo": stitch.group(0)})
    miro = _RE_MIRO.search(str(state.get("miro_links") or ""))
    if miro:
        links.append({"rotulo": "Board no Miro", "alvo": miro.group(0).rstrip(".,;")})
    return links


def para_o_de_acordo(state: Dict[str, Any]) -> Dict[str, Any]:
    """O que o cartão do de acordo de design mostra: o pedagógico (o documento a aprovar), onde ele está e os links do
    protótipo. Sem o pedagógico (sessão desenhada antes de 24/10/2026), `existe` é falso e `aviso` diz o que fazer."""
    documento = str(state.get(KEY) or "")
    existe = bool(documento.strip()) and not _pulo(documento)
    return {
        "chave": KEY, "titulo": "One-pager pedagógico", "existe": existe,
        "texto": documento if existe else "",
        "markdown": f"{ARQUIVO_BASE}.md", "docx": f"{ARQUIVO_BASE}.docx", "html": f"{ARQUIVO_BASE}.html",
        "links": links_do_prototipo(state),
        # O Refazer de design o gera também na correção pontual, que é o caminho padrão do Refazer com comentário: o
        # redator escreve o documento que falta, e os outros documentos de design seguem travados (revisão do PR #79)
        "aviso": "" if existe else (
            "Esta sessão não tem o one-pager pedagógico: o design dela rodou antes de 24/10/2026, quando ele saía no fim "
            "do dev. O de acordo de design é dado sobre ele — use Refazer, com o que mais quiser mudar no design: o "
            "design o gera, e na correção pontual os outros documentos de design ficam como estão."),
    }
