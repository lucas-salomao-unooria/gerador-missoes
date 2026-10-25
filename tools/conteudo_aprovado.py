"""O que o PO aprovou no one-pager chega inteiro à spec, ao PRD e ao one-pager pedagógico.

Auditoria das 11 missões do bucket em 06/10/2026: nenhuma spec trazia o podcast de recapitulação,
nenhuma trazia a tabela de tempos por etapa com os cenários de aula, e a spec aplicava as ressalvas
🟡 dos pareceres que o PO não tinha incorporado — a exp06ef1b perdeu a EF06CO07 (o PO aprovou "o
contrato de evidência com 4 habilidades") e passou de 29 para 24 minutos em tela; a exp04ef1b, de
29 para 25. Tudo a jusante segue a spec, e o PRD ainda trocava o contrato de evidência por chaves
de string: das quatro perguntas do Canal B da exp06ef1b, nenhuma chegou ao PRD. O dev devolveu a
missão por "inconsistência entre PRD e documentação de produto", e nenhum gate tinha acusado nada,
porque nenhum conferia um documento contra o one-pager aprovado.

Duas peças, as duas sem LLM:

- **Anexo literal.** As seções do one-pager que os gabaritos a jusante não tinham onde pôr —
  currículo, papel do professor, tempos e cenários de aula, podcast, contrato de evidência,
  hipóteses — são copiadas pela esteira para o fim do PRD e do one-pager pedagógico. O redator
  remete a elas e não as reescreve. O texto das réguas e das perguntas não é interpretado: o §12a
  muda de forma de missão para missão (tabela de quatro colunas, de cinco, subseções por
  habilidade), e um parser dele erraria em silêncio. Inteiro, ele não tem como perder nada.
- **Conferência.** Só o que tem estrutura firme: os códigos BNCC (§12a do one-pager → bloco 11 da
  spec → §14 do PRD e o pedagógico), o tempo total em tela (§10), o podcast (§11), um KPI por
  habilidade no PRD e os caminhos de artefato que o documento cita. Calibrado nos documentos das 11
  missões: as divergências que ele acusa são as que a auditoria encontrou lendo.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from tools import bncc

AGENTE = "conteudo-aprovado"

#: Seções do one-pager (`prompts/produto/014_secoes_apoio.md`); a numeração é a mesma nas 11 missões.
TITULOS = {
    0: "Identificação",
    1: "Descoberta central e anatomia do aha",
    2: "Currículo",
    3: "Narrativa e personagem-guia",
    4: "As 6 etapas — mecanismo e o que a tela mostra",
    5: "Verificação de ambiente",
    6: "Verbos e affordances",
    7: "Caminhos degenerados",
    8: "Estados de falha",
    9: "Papel do professor e parametrização com IA",
    10: "Modularidade, tempos sugeridos e controle do professor",
    11: "Podcast de recapitulação",
    12: "Evidências e dados, com o contrato de evidência por habilidade",
    13: "Cenários de dispositivo",
    14: "Guardrails e IA",
    15: "Tetos aplicados à faixa",
    16: "Requisitos técnicos e escopo",
    17: "Hipóteses de validação",
    18: "Decisões de direção, trade-offs e propostas",
}
SECOES_PRD: Tuple[int, ...] = (2, 9, 10, 11, 12, 17)
#: §9 entrou em 07/10/2026: o roteiro do debate mora nele, e o pedagógico da exp01ef1b copiou a pergunta 1
#: na redação que a spec reescreveu — o anexo, que deveria ser a referência, não a trazia.
SECOES_PEDAGOGICO: Tuple[int, ...] = (9, 10, 11, 12)
#: O design recebe também §8 (falhas — a de mídia não chegava a tela nenhuma) e §13 (cenários de
#: dispositivo — projeção e 2 a 4 por aparelho), que fluxo, CAA, telas e QA não liam (auditoria de 07/10/2026).
#: E o núcleo aprovado — §1, §3 e §4 — desde a reanálise da noite de 07/10/2026: o §4 traz o texto que a tela
#: mostra (a pergunta da aposta e as alternativas, as falas da personagem, o caso de transferência), e a spec
#: levava 81 de 153 desses textos nas dez sessões de outubro. Fluxo, CAA, telas e a revisão da copy só o viam
#: pela spec; nas sessões que chegaram ao fim, de 18% a 45% chegavam ao protótipo.
#: E §6, §7, §14 e §15 (verbos, caminhos degenerados, guardrails, tetos da faixa): 6 a 9 mil caracteres por missão,
#: que fluxo, revisão da copy e banca só viam pela spec — §7 chegava à spec com 26 de 41 textos, §14 com 2 de 11.
SECOES_NUCLEO: Tuple[int, ...] = (1, 3, 4)
#: E §0, §5, §16 e §18 (identificação, verificação de ambiente, escopo V1/V2, decisões e propostas), que a
#: auditoria do PR #32 achou faltando: com elas, design e dev recebem o one-pager inteiro, seção por seção.
SECOES_DESIGN: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18)
#: O dev recebe o mesmo que o design. Até 07/10/2026 o `A095ConteudoAprovadoDev` regravava a chave com as
#: seções do PRD, e a banca — e os agentes de design que ela reaciona — perdiam §8, §13 e o núcleo; o banco de
#: conteúdo lia o núcleo de antes da revisão do one-pager (`nucleo_narrativo`).
SECOES_DEV: Tuple[int, ...] = SECOES_DESIGN
#: Abre o `conteudo_aprovado` que os agentes leem: sem ela, a seção que pede o que a plataforma não tem
#: ("ativar ou agendar" no §9 da exp01ef1b) valia tanto quanto a spec que a corrigiu.
NOTA_CONTEUDO_APROVADO = (
    "> Copiado pela esteira, sem reescrita, do one-pager que o PO aprovou. Para o que a missão ensina e mede, os "
    "textos literais (Canal B, debate, podcast e o que o §4 põe na tela entre aspas — a pergunta da aposta, as "
    "alternativas, as falas da personagem), os tempos e o papel do professor, se a spec divergir, vale este "
    "texto. Onde a spec detalha o mecanismo (estados, regras, IDs de tela), vale a spec; onde ela contradiz o §4 "
    "num número ou num texto de tela, siga este texto e registre a divergência. Restrição da plataforma não se "
    "decide aqui: se ele pedir o que a plataforma não tem (agendamento, por exemplo), vale a spec, e a divergência "
    "é pendência de produto."
)

#: O título do anexo é também o marcador: comentário HTML apareceria cru no `.docx` do pedagógico.
TITULO_ANEXO = "Anexo — conteúdo aprovado pelo PO"
NOTA_ANEXO = (
    "> Copiado pela esteira, sem reescrita, de «{origem}», a versão que o PO aprovou. É a fonte do que "
    "a missão ensina e mede, do podcast, dos tempos e do papel do professor: para isso, se o corpo deste "
    "documento divergir do anexo, vale o anexo. Restrição da plataforma não se decide aqui: se o anexo pedir o "
    "que a plataforma não tem (agendamento, por exemplo), vale o corpo, e a divergência é pendência de produto."
)

_RE_TITULO = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_RE_CERCA = re.compile(r"^\s*(```|~~~)")
_RE_12A = re.compile(r"^#{2,5}\s*12a\b", re.M | re.I)


# --------------------------------------------------------------------------- seções
def _titulos(texto: str) -> List[Tuple[int, int, int, str]]:
    """(início da linha, fim da linha, nível, título) de cada título fora de bloco de código.

    O PRD tem `# Iniciar frente de trabalho…` dentro do bloco bash da seção 17: lido como título,
    cortava a seção 17 no meio.
    """
    saida: List[Tuple[int, int, int, str]] = []
    pos, cerca = 0, False
    for linha in (texto or "").splitlines(keepends=True):
        if _RE_CERCA.match(linha):
            cerca = not cerca
        elif not cerca:
            m = _RE_TITULO.match(linha.rstrip("\n"))
            if m:
                saida.append((pos, pos + len(linha), len(m.group(1)), m.group(2)))
        pos += len(linha)
    return saida


def secao(texto: str, numero: int) -> Optional[str]:
    """Corpo da seção `numero` (`## 11. Podcast…`, `# 14. Pedagogia…`), sem o título.

    Vai até o próximo título de nível igual ou mais alto. `12a.` não é a seção 12 e `14.1` não é a
    14 — o `bncc.secao_bloco` cortava a 13 do PRD da exp09ef1b no `### 13.1`, e a seção saía vazia.
    """
    titulos = _titulos(texto)
    padrao = re.compile(rf"^{numero}\s*(?:\.(?![\dA-Za-z])|[—–-])")
    for i, (_, fim, nivel, titulo) in enumerate(titulos):
        if padrao.match(titulo.strip("*_ ")):
            fim_secao = next((ini for ini, _, n, _ in titulos[i + 1:] if n <= nivel), len(texto))
            return texto[fim:fim_secao]
    return None


def _origem(one_pager: str) -> str:
    for _, _, nivel, titulo in _titulos(one_pager):
        if nivel == 1:
            return titulo.strip("*_ ")
    return "one-pager de produto"


# --------------------------------------------------------------------------- anexo
def remover_anexo(texto: str) -> str:
    """O documento sem o anexo (e sem a divisória que o precede). Idempotente."""
    if not texto:
        return texto or ""
    for ini, _, nivel, titulo in _titulos(texto):
        if nivel == 1 and titulo.strip("*_ ").startswith(TITULO_ANEXO):
            corpo = texto[:ini].rstrip()
            if corpo.endswith("---"):
                corpo = corpo[:-3].rstrip()
            return corpo + "\n"
    return texto


def secoes_literais(one_pager: str, secoes: Sequence[int]) -> str:
    """As seções aprovadas, literais, cada uma sob o próprio título. Vazio se o one-pager não tem nenhuma."""
    partes = []
    for numero in secoes:
        corpo = (secao(one_pager or "", numero) or "").strip()
        # a divisória que fecha cada seção do one-pager vira ruído entre as seções do anexo
        corpo = re.sub(r"\n-{3,}\s*$", "", corpo).strip()
        if corpo:
            partes.append(f"## {TITULOS.get(numero, f'Seção {numero}')} — one-pager §{numero}\n\n{corpo}\n")
    return "\n".join(partes)


#: O que mudou nas seções aprovadas desde a última vez que a etapa rodou (`agents/base.py` o põe junto da versão
#: anterior de cada autor). Vazio na primeira execução e quando o one-pager não mudou.
KEY_MUDANCAS = "mudancas_no_aprovado"
LIMITE_MUDANCAS = 120


def mudancas_no_aprovado(anterior: str, atual: str, limite: int = LIMITE_MUDANCAS) -> str:
    """As linhas das seções aprovadas que mudaram entre o retrato da última execução da etapa e o one-pager atual.

    Depois de um refazer de produto, design e dev recomeçam da versão anterior dos próprios documentos
    (`anterior_<chave>`), com a instrução de mantê-la «palavra por palavra quando nada obriga a mudar» — e nada
    dizia o que tinha mudado no one-pager. O número que foi de 24 para 20 vagas seguia 24 na jornada, na copy e no
    PRD (auditoria da noite de 07/10/2026).
    """
    import difflib

    if not (anterior or "").strip() or anterior == atual:
        return ""
    linhas: List[str] = []
    for l in difflib.unified_diff(anterior.splitlines(), (atual or "").splitlines(), lineterm="", n=0):
        if l.startswith(("---", "+++", "@@")):
            continue
        conteudo = l[1:].strip()
        if not conteudo or set(conteudo) <= set("-|:> "):
            continue  # divisória, separador de tabela, citação vazia
        linhas.append(("antes: " if l[0] == "-" else "agora: ") + conteudo[:300])
    if not linhas:
        return ""
    corpo = [f"- {x}" for x in linhas[:limite]]
    if len(linhas) > limite:
        corpo.append(f"- … e mais {len(linhas) - limite} linha(s). Com tanta mudança, trate a sua versão anterior como "
                     "rascunho: confira cada número, nome, habilidade e texto de tela contra o conteúdo aprovado.")
    return "\n".join([
        "## O one-pager aprovado mudou desde a sua versão anterior", "",
        "A versão anterior dos seus documentos (o bloco «Sua versão anterior», quando você o recebeu) foi escrita sobre "
        "um one-pager que mudou depois — o PO refez produto. Abaixo, as linhas que mudaram nas seções aprovadas. O que "
        "você reaproveitar da versão anterior tem de bater com o «agora»: número, nome, habilidade ou texto de tela que "
        "o contradiga, reescreva. O que não aparece aqui não mudou.", "",
    ] + corpo)


def anexo(one_pager: str, secoes: Sequence[int], textos_chave: str = "") -> str:
    """As seções aprovadas, literais, sob um título único — e, quando vem, a tabela dos textos-chave com ID
    (`tools/textos_chave.py`, PR 7), que o corpo cita pelo ID. Vazio se o one-pager não tem nenhuma seção."""
    partes = secoes_literais(one_pager, secoes)
    if not partes:
        return ""
    return "\n".join(["---", "", f"# {TITULO_ANEXO}", "", NOTA_ANEXO.format(origem=_origem(one_pager)), "", partes]
                     + ([textos_chave.strip(), ""] if (textos_chave or "").strip() else []))


def com_anexo(documento: str, one_pager: str, secoes: Sequence[int], textos_chave: str = "") -> str:
    """O documento com o anexo atual no fim, trocando o de uma rodada anterior."""
    corpo = remover_anexo(documento or "").rstrip()
    extra = anexo(one_pager, secoes, textos_chave)
    return f"{corpo}\n\n{extra}" if extra else corpo + "\n"


# --------------------------------------------------------------------------- o que se confere
def codigos_aprovados(one_pager: str) -> List[str]:
    """Códigos de Computação do contrato de evidência (§12a); sem §12a, os do currículo (§2)."""
    s12 = secao(one_pager or "", 12) or ""
    m = _RE_12A.search(s12)
    if m:
        codigos = bncc.extrair_codigos(s12[m.start():])
        if codigos:
            return codigos
    return bncc.extrair_codigos(secao(one_pager or "", 2) or "")


#: Texto entre aspas logo depois do rótulo: `**Pergunta:** "…"`, `Pergunta: *"…"*`, `- **Atingiu:** "…"`.
#: A régua do Canal A vem sem aspas e fica de fora — ela é conferida pelo anexo, não aqui.
_RE_CANAL_B = re.compile(
    r"(?:Pergunta|Atingiu|Em processo|N[ãa]o atingiu)\s*\**\s*:?\s*\**\s*:?\s*\*?\s*[\"“]([^\"”\n]{12,}?)[\"”]", re.I)
_RE_TITULO_ROTEIRO = re.compile(r"^#{2,6}[^\n]*\b(?:roteiro|perguntas)\b[^\n]*$", re.I | re.M)
_RE_PERGUNTA = re.compile(r"[\"“]([^\"”\n]{12,}\?)[\"”]")
_RE_FALA = re.compile(r"^\s*(?:[-*]\s+)?\*\*([^*\n]{2,30}?):\*\*\s*(.{20,})$", re.M)
#: Rótulo de uma palavra que é metadado do episódio, não voz: `**Duração:**`, `**Apresentadores:**`.
_ROTULOS_DE_METADADO = frozenset({"duração", "duracao", "formato", "participantes", "apresentadores", "vozes", "aviso",
                                  "público", "publico", "tom", "objetivo", "título", "titulo", "episódio", "nota",
                                  "trilha", "quando", "roteiro", "resumo", "voz", "público-alvo",
                                  "publico-alvo"})
#: Primeira palavra de rubrica de produção sonora (`**Trilha sonora:**`, `**Efeito sonoro:**`, `**Áudio de vinheta:**`):
#: indica o que tocar, não o que alguém diz — nunca é voz, nem repetida. Na exp02em1b (22/10/2026) «Trilha sonora»
#: aparecia duas vezes, contava como personagem, e o banco foi reprovado no dev por reescrever a rubrica.
_RE_RUBRICA_SONORA = re.compile(
    r"^(?:trilha|efeitos?|sfx|vinheta|[áa]udio|m[úu]sica|som|sons|sonoplastia|ru[íi]do|ambi[êe]ncia|fundo|bgm|jingle)\b",
    re.I)


#: O título de cada etapa do §4 (`### Etapa 3: Decidir`, `### 3. Decidir`, `#### Etapa 5b: Revisar`) e o bloco
#: de evidência que fecha a seção — esse é o §12a resumido, e o Canal B já é conferido por ele.
_RE_TITULO_ETAPA = re.compile(r"^#{2,6}\s*(?:Etapa\s*)?\d\s*[a-z]?\s*[:.—–-]", re.I)
_RE_TITULO_EVIDENCIA = re.compile(r"^#{2,6}\s*(?:Bloco\s+de\s+)?Evid[êe]ncia", re.I)
#: Qualquer par de aspas, do tamanho que for: o tamanho mínimo é filtrado depois. Com `{12,}` no padrão, um rótulo
#: curto («"Ontem"») não fechava par, e a aspa que o fechava abria outro — «(que ficou guardada) e a lista de» virava
#: texto de tela (auditoria do PR #32, sessão 0b99718a).
_RE_ENTRE_ASPAS = re.compile(r"[\"“]([^\"”\n]*)[\"”]")
#: Linha que é fala do professor em sala, não texto de tela: «Quem conduz», «o professor pergunta: "…"»,
#: a pergunta-ponte, a mediação. Também a crença que a missão desmonta («O descarte previsto ("…")»).
_RE_LINHA_ORAL = re.compile(
    r"quem conduz|professor\w*\b[^\"“\n]{0,60}?\b(?:pergunta|diz|orienta|refor[çc]a|conduz|lan[çc]a|fecha|chama|"
    r"paralisa|projeta|encerra|provoca|comenta|retoma|media)|pergunta[- ]ponte|pergunta mediada|debate mediado|"
    r"media[çc][ãa]o|\boral(?:mente)?\b|roda de conversa|descarte previsto|"
    # a pergunta com que o professor abre a conversa: «3. Pergunta disparadora: "Vocês acham que a rede…?"», na
    # condução do aha da exp02em1b, era cobrada na copy e no protótipo como texto de tela (levantamento de 24/10/2026)
    r"pergunta disparadora", re.I)
#: Aspas depois disto, na mesma linha, são exemplo do que o estudante faria ou diria, não texto aprovado. Também a fala
#: hipotética: «se alguém disser "aconteceu isso porque eu errei na IA"» (exp02em1b, 24/10/2026).
_RE_ANTES_DE_EXEMPLO = re.compile(
    r"\bex\.?\s*:|\bexemplo|algo como|\brespond(?:em|e)\b|estudantes? (?:diz|dizem|fala|falam|escreve)|"
    r"\b(?:algu[ée]m|estudantes?|alunos?|alunas?|crian[çc]as?|turma)\s+(?:disser|disserem|falar|falarem|"
    r"argumentar|argumentarem|alegar|alegarem|reclamar|reclamarem)\b", re.I)
#: Fala dirigida à turma, sem rótulo na linha: «Turma, olhem…», «Quem marcou monstro, levante a mão!».
_RE_FALA_A_TURMA = re.compile(r"^(?:turma|pessoal|gente|crian[çc]as|detetives)\b|levant\w*\s+a\s+m[ãa]o|\b(?:olhem|vejam|observem)\b",
                              re.I)


def textos_de_tela(one_pager: str) -> List[str]:
    """O que o §4 aprovado põe na tela entre aspas: a pergunta da aposta e as alternativas, botões, títulos,
    mensagens do sistema e falas da personagem, o caso de transferência.

    Fica de fora o que não é texto de tela: fala do professor em sala, exemplo do que o estudante diria («ex.:
    "…"»), aspas quebradas por crase, rótulo de até duas palavras, e o bloco de evidência que fecha o §4 (o Canal B
    tem conferência própria). Calibrado nas 15 sessões do bucket de 25/09 a 07/10/2026: de 7 a 28 textos por missão.
    """
    return [t for _, t in textos_de_tela_por_etapa(one_pager)]


#: O número da etapa no título do §4: «### Etapa 3: Decidir», «### 3. Decidir», «#### Etapa 5b: Revisar».
_RE_NUMERO_DA_ETAPA = re.compile(r"^#{2,6}\s*(?:Etapa\s*)?(\d\s*[a-z]?)", re.I)


def linhas_das_etapas(one_pager: str) -> Iterable[Tuple[str, Optional[str]]]:
    """`(etapa, linha)` de cada linha do §4 que está dentro de uma etapa, sem o bloco de evidência que fecha a seção;
    o título de cada etapa sai como `(etapa, None)`. `etapa` é o número do título («3», «5b»). A mesma leitura do
    `textos_de_tela`; os textos-chave (PR 7) a usam para saber de que etapa é cada texto e cada escolha."""
    etapa = ""
    for linha in (secao(one_pager or "", 4) or "").splitlines():
        s = linha.strip()
        if _RE_TITULO_EVIDENCIA.match(s):
            etapa = ""
            continue
        if _RE_TITULO_ETAPA.match(s):
            m = _RE_NUMERO_DA_ETAPA.match(s)
            etapa = re.sub(r"\s+", "", m.group(1)) if m else "?"
            yield etapa, None
            continue
        if etapa:
            yield etapa, linha


def textos_de_tela_por_etapa(one_pager: str) -> List[Tuple[str, str]]:
    """`(etapa, texto)` do que o §4 põe na tela entre aspas, na ordem — o `textos_de_tela` com a etapa de cada texto."""
    saida: List[Tuple[str, str]] = []
    vistos: Set[str] = set()
    #: recuo da linha oral que abre uma lista: os itens mais recuados abaixo dela são falas dela
    #: («- **Mediação do professor:**» seguido de «  * "Quem aqui escolheu a capa?"»)
    recuo_oral: Optional[int] = None
    for etapa, linha in linhas_das_etapas(one_pager):
        if linha is None:
            recuo_oral = None  # título de etapa: a lista oral da etapa anterior acabou
            continue
        s = linha.strip()
        if not s:
            continue
        recuo = len(linha) - len(linha.lstrip())
        if recuo_oral is not None and recuo > recuo_oral:
            continue
        recuo_oral = None
        if _RE_LINHA_ORAL.search(linha):
            recuo_oral = recuo
            continue
        for m in _RE_ENTRE_ASPAS.finditer(linha):
            if _RE_ANTES_DE_EXEMPLO.search(linha[:m.start()]):
                continue
            t = m.group(1).strip().strip("*").strip()
            if len(t) < 12 or t[0] in ",;:.)]" or "`" in t or _RE_FALA_A_TURMA.search(t):
                continue
            if len(t.split()) >= 3 and t not in vistos:
                vistos.add(t)
                saida.append((etapa, t))
    return saida


def literais(one_pager: str) -> Dict[str, List[str]]:
    """O texto que o PO aprovou palavra por palavra e que a criança ou o professor ouvem.

    - `canal_b`: perguntas e alternativas entre aspas do §12a;
    - `roteiro`: as perguntas do debate (bloco «Roteiro…»/«Perguntas…» do §9);
    - `podcast`: as falas do §11 (`**Nome:** fala`): o nome que se repete, ou o nome próprio de uma palavra
      que não é rótulo de metadado (`**Duração:**`, `**Apresentadores:**`);
    - `texto_tela`: o que o §4 põe na tela entre aspas (`textos_de_tela`).

    Na exp01ef1b (07/10/2026) a spec reescreveu a primeira pergunta do debate, a camada CAA parafraseou
    as alternativas, a copy reescreveu o podcast e o banco de conteúdo escreveu outro roteiro.
    """
    texto = one_pager or ""
    s12 = secao(texto, 12) or ""
    m = _RE_12A.search(s12)
    canal_b = list(dict.fromkeys(t.strip() for t in _RE_CANAL_B.findall(s12[m.start():] if m else "")))
    s9 = secao(texto, 9) or ""
    roteiro: List[str] = []
    for t in _RE_TITULO_ROTEIRO.finditer(s9):
        resto = s9[t.end():]
        fim = re.search(r"^#{2,6} ", resto, re.M)
        roteiro += [q.strip() for q in _RE_PERGUNTA.findall(resto[: fim.start()] if fim else resto)]
    falas = _RE_FALA.findall(secao(texto, 11) or "")
    vezes: Dict[str, int] = {}
    for nome, _ in falas:
        vezes[nome.strip()] = vezes.get(nome.strip(), 0) + 1
    def e_voz(nome: str) -> bool:
        nome = nome.strip()
        if _RE_RUBRICA_SONORA.match(nome):
            return False
        return vezes[nome] >= 2 or (" " not in nome and nome[:1].isupper() and nome.lower() not in _ROTULOS_DE_METADADO)

    podcast = [fala.strip().strip('"“”*').strip() for nome, fala in falas if e_voz(nome)]
    return {"canal_b": canal_b, "roteiro": list(dict.fromkeys(roteiro)), "podcast": podcast,
            "texto_tela": textos_de_tela(texto)}


_RE_NEGACAO = re.compile(r"\b(?:nao|nunca|jamais|nenhum|nenhuma|sem)\b")


def _negacoes(texto: str) -> int:
    """Negações do trecho, sem os rótulos de nível — «Não atingiu:», «Ainda não:» (o pedagógico, em linguagem de sala) —,
    que antecedem a alternativa no Canal B e não a negam. Rótulo é a negação seguida de dois-pontos ou de «atingiu»."""
    return len(_RE_NEGACAO.findall(re.sub(r"\bnao\s+atingiu\b|\b(?:nao|nunca|sem)\s*:", " ", texto)))


def _ocorrencias(texto: str, alvo: str) -> List[int]:
    saida, i = [], texto.find(alvo)
    while i >= 0:
        saida.append(i)
        i = texto.find(alvo, i + 1)
    return saida


#: A lacuna que a plataforma ou o professor preenche: «[recorte da aula: parâmetro do professor]», «{motivo}». A mesma
#: leitura dos textos-chave (`tools/textos_chave._RE_LACUNA`), sem o `X%` e as reticências, que lá são do texto-chave.
_RE_LACUNA = re.compile(r"\s*(?:\[[^\]\n]{1,120}\]|\{[^}\n]{1,60}\})\s*")
#: A ligação que sai junto com a lacuna quando a copy a omite: «na Trilha Avançada do [recorte da aula] para estudar» →
#: «na trilha avançada para estudar».
_LIGACAO_DA_LACUNA = frozenset("a o as os ao aos à às de do da dos das no na nos nas em para pelo pela com".split())


def _pedacos_sem_lacuna(trecho: str) -> Optional[List[str]]:
    """Os pedaços do texto aprovado entre as lacunas (de duas palavras ou mais), ou None quando ele não tem lacuna."""
    partes = _RE_LACUNA.split(trecho or "")
    if len(partes) < 2:
        return None
    pedacos = []
    for i, parte in enumerate(partes):
        palavras = parte.split()
        if i < len(partes) - 1:
            while palavras and palavras[-1].lower() in _LIGACAO_DA_LACUNA:
                palavras.pop()
        pedaco = " ".join(palavras).strip(" ,;:.—–-")
        if len(pedaco.split()) >= 2:
            pedacos.append(pedaco)
    return pedacos


def _literal_confere(trecho: str, documento_norm: str) -> bool:
    """O texto aprovado está no documento: 85% contínuos, e o começo, o fim e as negações dele intactos.

    Os 85% são a conferência de citação da fidelidade, tolerante de propósito (o juiz copia com uma vírgula a mais).
    Para texto aprovado palavra por palavra ela deixava passar a troca das últimas palavras e o "não" inserido perto
    do começo — mutações que a matriz não pegava (auditoria do padrão ouro, 08/10/2026). Aqui, na região que casou,
    as três primeiras e as três últimas palavras do trecho têm de estar, e o número de negações tem de ser o mesmo.

    A lacuna do texto aprovado é curinga: cada pedaço entre lacunas confere sozinho, com as mesmas regras. A copy que a
    preenche («…para o recorte da aula. A coordenação…») ou a omite («Comitê Municipal de Políticas Públicas», sem o
    «[recorte da aula: parâmetro do professor]») traz o texto aprovado — a matriz cobrava a lacuna literal na
    exp01em1b-e89e91b3 e na exp03em1b (levantamento de deficiências de design, 24/10/2026). O texto que é só lacuna, ou
    cujos pedaços fora dela têm uma palavra só («Olá, [nome]!», «[Opção]»), confere inteiro, como sem lacuna: sem pedaço
    para conferir, o curinga o daria sempre como presente — no Canal B, no roteiro, no banco e na paráfrase também
    (revisão do PR #81, 25/10/2026).
    """
    import difflib

    from tools.fidelidade import _norm

    pedacos = _pedacos_sem_lacuna(trecho)
    if pedacos:
        return all(_literal_confere(p, documento_norm) for p in pedacos)
    alvo = _norm(trecho)
    if not alvo:
        return True
    if alvo in documento_norm:
        # inteiro, mas negado pela palavra imediatamente anterior ("Não apenas para a família…"): o texto está lá e
        # diz o contrário. Só a palavra anterior — a frase de antes pode ter um "sem" que não é com ele.
        anteriores = [(documento_norm[max(0, i - 30):i].split() or [""])[-1] for i in _ocorrencias(documento_norm, alvo)]
        # «Ainda não:» antes da alternativa é rótulo de nível, não negação (o dois-pontos o separa do texto)
        return any(p.endswith(":") or not _RE_NEGACAO.fullmatch(p.strip(".,;!?()[]")) for p in anteriores)
    m = difflib.SequenceMatcher(None, documento_norm, alvo, autojunk=False).find_longest_match(
        0, len(documento_norm), 0, len(alvo))
    if m.size < 0.85 * len(alvo):
        return False
    inicio = max(0, m.a - m.b)
    regiao = documento_norm[inicio: inicio + len(alvo) + max(12, len(alvo) // 10)]
    palavras = alvo.split()
    cabeca, cauda = " ".join(palavras[:3]), " ".join(palavras[-3:])
    if cabeca not in regiao or cauda not in regiao:
        return False
    fim_da_cauda = regiao.find(cauda) + len(cauda)
    return _negacoes(regiao[:fim_da_cauda]) == _negacoes(alvo)


def literais_ausentes(documento: str, trechos: Sequence[str]) -> List[str]:
    """Os trechos aprovados que não estão no documento (`_literal_confere`)."""
    from tools.fidelidade import _norm

    alvo = _norm(documento or "")
    return [t for t in trechos if not _literal_confere(t, alvo)]


def _decisao_pendente(*textos: str) -> bool:
    return any(bncc._DECISAO_RE.search(t or "") for t in textos)


_RE_EM_TELA_APROVADO = re.compile(r"em\s+tela\W{0,6}(\d{1,3})\s*min", re.I)
_RE_TEMPO_DECLARADO = (
    re.compile(r"\b(\d{1,3})\s*min(?:utos)?\b\s+(?:de\s+\w+\s+)?em\s+tela", re.I),  # "24 minutos em tela"
    re.compile(r"\btotal\s+(?:em|de|na)\s+tela\b[^0-9\n]{0,60}?(\d{1,3})\s*min", re.I),  # "tempo total em tela: 24 min"
    re.compile(r"\bem\s+tela\W{1,6}(\d{1,3})\s*min", re.I),  # "Em tela: 24 min"
)
#: Linha de decisão descartada: "Alternativa descartada: manter 29 min em tela" não é contradição.
_RE_LINHA_DESCARTADA = re.compile(r"descart|alternativa|anterior|\bantes\b", re.I)
#: Número logo depois disto discute o teto ou a ressalva, não declara o total. Vale para o número, não
#: para a linha: «Tempo total em tela: 24 minutos (o teto de referência da rubrica é 25)» declara 24.
_RE_NUMERO_DISCUTIDO = re.compile(r"rubrica|ressalva|teto de refer", re.I)


def tempo_aprovado(one_pager: str) -> Optional[int]:
    """O total em tela do §10 (`Em tela: 29 min`). Dois totais diferentes no §10: não há um aprovado."""
    valores = {int(n) for n in _RE_EM_TELA_APROVADO.findall(secao(one_pager or "", 10) or "")}
    return valores.pop() if len(valores) == 1 else None


def _linhas_fora_de_codigo(texto: str) -> Iterable[str]:
    cerca = False
    for linha in (texto or "").splitlines():
        if _RE_CERCA.match(linha):
            cerca = not cerca
        elif not cerca:
            yield linha


_RE_TETO = re.compile(r"teto|≤|<=|limite|m[áa]xim|exceder|\bat[ée]\s*$", re.I)


def tempos_divergentes(texto: str, alvo: int) -> List[Tuple[int, str]]:
    """Linhas que declaram outro total em tela.

    Número abaixo de 60% do aprovado é de uma etapa, não do total. Teto («não pode exceder 25 min»,
    «≤ 25 min») só contradiz quando fica abaixo do aprovado: «20 min em tela, abaixo do teto de 25»
    está certo; «29 aprovados» com «não pode exceder 25» manda o código cortar a missão.
    """
    achados: List[Tuple[int, str]] = []
    for linha in _linhas_fora_de_codigo(texto):
        if _RE_LINHA_DESCARTADA.search(linha):
            continue
        numeros: List[Tuple[int, bool]] = []
        for rx in _RE_TEMPO_DECLARADO:
            for m in rx.finditer(linha):
                antes = linha[max(0, m.start(1) - 40):m.start(1)]
                if _RE_NUMERO_DISCUTIDO.search(antes):
                    continue
                numeros.append((int(m.group(1)), bool(_RE_TETO.search(antes[-30:]))))
        if not numeros or any(n == alvo for n, _ in numeros):
            continue
        for n, teto in numeros:
            # o piso vale para os dois: «máximo de 6 minutos em tela na Etapa 5» é teto de uma etapa
            if n >= alvo * 0.6 and (n < alvo if teto else True):
                achados.append((n, linha.strip()))
                break
    return achados


_RE_SEM_PODCAST = re.compile(r"n[ãa]o se aplica|sem podcast|n[ãa]o h[áa] podcast|n[ãa]o tem podcast", re.I)
_RE_PODCAST = re.compile(r"podcast", re.I)


def tem_podcast(one_pager: str) -> bool:
    s11 = (secao(one_pager or "", 11) or "").strip()
    return len(s11) >= 200 and not _RE_SEM_PODCAST.search(s11[:400])


#: O número que o one-pager deixou para o PO decidir: `[PARÂMETRO — a definir por produto: 45 segundos]`.
_RE_PARAMETRO_PENDENTE = re.compile(r"\[(?:PAR[ÂA]METRO|DECIS[ÃA]O PENDENTE)[^\]\n]{0,300}\]", re.I)
_RE_VALOR_COM_UNIDADE = re.compile(
    r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*(?:a\s*\d+(?:[.,]\d+)?\s*)?"
    r"(%|s\b|seg\w*|min\w*|palavras?|ms\b|milissegundos?|toques?|mensage\w+|tentativas?|rodadas?|caracteres?|itens?)",
    re.I)
#: Família da unidade → como ela aparece escrita (`45 s`, `45 segundos`; `3 min`, `3 minutos`).
_UNIDADE_ESCRITA = {"seg": r"(?:s\b|seg\w*)", "min": r"min\w*", "%": r"%", "pal": r"palavras?", "mil": r"(?:ms\b|milissegundos?)",
                    "toq": r"toques?", "men": r"mensage\w+", "ten": r"tentativas?", "rod": r"rodadas?",
                    "car": r"caracteres?", "ite": r"itens?"}
#: Linha que ainda trata o número como pendente, ou que diz quem o decidiu (o D0 ratificou, o PO homologou).
_RE_AINDA_PENDENTE = re.compile(r"PAR[ÂA]METRO|PROPOSTA|ABERTO|DECIS[ÃA]O PENDENTE|a definir|validar com (?:o )?PO|"
                                r"NEEDS CLARIFICATION", re.I)
#: Só a decisão do PO com data isenta (princípio 1 do plano padrão ouro). A ratificação pelo D0 (`[D0-n]`,
#: «ratificado») é de um agente: não isenta, e o número decidido assim fica 🟡 para o PO ver (`_RE_RATIFICADO_PELO_D0`).
_RE_DECISAO_REGISTRADA = re.compile(r"(?:homologad|parecer d[oe]|decidido (?:pelo|em|no)|PO —|pedido d[oe] PO)"
                                    r"[^\n]*\b\d{2}/\d{2}/\d{4}\b", re.I)
_RE_RATIFICADO_PELO_D0 = re.compile(r"ratificad|\[D0-\d", re.I)


def _familia_da_unidade(unidade: str) -> str:
    u = unidade.lower()
    if u == "s" or u.startswith("seg"):
        return "seg"
    if u == "ms" or u.startswith("mil"):
        return "mil"
    return "%" if u == "%" else u[:3]


def parametros_decididos(documento: str, one_pager: str) -> List[Tuple[str, str]]:
    """`(marcador do one-pager, linha do documento)` de cada número que o one-pager deixou a definir por produto e
    que o documento afirma como decidido — sem marcador e sem dizer quem decidiu.

    Nas dez sessões de outubro, 4 de 16 parâmetros viraram fato na spec («Após 45 segundos sem interação…»,
    «quando ≥ 80% da turma concluir…», «no máximo 25 palavras por string»): a spec decidia no lugar do PO, e
    design e PRD herdavam o número como decidido. O parâmetro que some do documento não entra aqui.

    Varre todas as linhas, inclusive as de bloco de código: o comentário de um schema também afirma o número, e a
    spec da exp04ef1b (25/09) abria uma cerca ```markdown na linha 2 que invertia a paridade das outras.
    """
    linhas = (documento or "").splitlines()
    saida: List[Tuple[str, str]] = []
    for m in _RE_PARAMETRO_PENDENTE.finditer(one_pager or ""):
        valor = _RE_VALOR_COM_UNIDADE.search(m.group(0))
        if not valor:
            continue
        familia = _familia_da_unidade(valor.group(2))
        unidade = _UNIDADE_ESCRITA.get(familia, re.escape(familia))
        alvo = re.compile(rf"(?<![\d.,]){re.escape(valor.group(1))}\s*(?:a\s*\d+(?:[.,]\d+)?\s*)?{unidade}", re.I)
        com_o_numero = [l for l in linhas if alvo.search(l)]
        if not com_o_numero or any(_RE_AINDA_PENDENTE.search(l) or _RE_DECISAO_REGISTRADA.search(l)
                                   for l in com_o_numero):
            continue
        if m.group(0) not in [s for s, _ in saida]:
            saida.append((m.group(0), com_o_numero[0].strip()))
    return saida


#: Palavras que não dizem de que assunto é o número: as do próprio marcador e as unidades.
_PALAVRAS_SEM_ASSUNTO = frozenset({"definir", "produto", "parametro", "decisao", "pendente", "segundo", "segundos",
                                   "minuto", "minutos", "palavra", "palavras", "milissegundos", "toques", "mensagens",
                                   "tentativas", "rodadas", "caracteres", "itens", "entre", "maximo", "minimo",
                                   "padrao", "cerca", "apenas", "quando", "depois", "antes"})


def _palavras_de_assunto(texto: str) -> Set[str]:
    import unicodedata

    sem_acento = "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")
    return {p for p in re.findall(r"[a-z]{5,}", sem_acento) if p not in _PALAVRAS_SEM_ASSUNTO}


def parametro_no_mesmo_assunto(marcador: str, linha_da_spec: str, one_pager: str) -> bool:
    """A linha da spec fala do mesmo assunto que o parâmetro? Alguma palavra de conteúdo em comum com o marcador ou
    com a linha do one-pager onde ele está. O número igual num assunto diferente («inatividade de 45 segundos» no
    one-pager, «o áudio dura 45 segundos» na spec) não é o parâmetro decidido (auditoria do PR #32)."""
    linha_op = next((l for l in (one_pager or "").splitlines() if marcador in l), marcador)
    return bool(_palavras_de_assunto(linha_op) & _palavras_de_assunto(linha_da_spec))


_RE_ARTEFATO = re.compile(r"(?<![\w/.-])((?:produto|design|dev|spec)/[\w./-]+?\.(?:md|html|docx|json|pdf))\b")


def artefatos_inexistentes(texto: str, validos: Iterable[str]) -> List[str]:
    """Caminhos de artefato da sessão (`produto/…`, `design/…`, `dev/…`) que a sessão não tem.

    Os PRDs das 11 missões apontavam `spec/<slug>-spec.md`, `design/04-copy-ptbr.md`,
    `design/08-prototipo-navegavel.html` — o primeiro vinha do próprio gabarito do PRD.
    """
    conhecidos = set(validos)
    vistos: List[str] = []
    for caminho in _RE_ARTEFATO.findall(texto or ""):
        if caminho not in conhecidos and caminho not in vistos:
            vistos.append(caminho)
    return vistos


# --------------------------------------------------------------------------- validação
def _achado(codigo: str, resumo: str, etapa: str, severidade: str = "bloqueio") -> Dict[str, str]:
    return {"severidade": severidade, "codigo": codigo, "etapa": etapa, "resumo": resumo}


def _status(achados: List[Dict[str, str]]) -> str:
    if any(a["severidade"] == "bloqueio" for a in achados):
        return "bloqueado"
    return "amarelo" if achados else "aprovado"


def _lista(codigos: Iterable[str]) -> str:
    return ", ".join(f"`{c}`" for c in codigos)


def _comparar_codigos(aprovados: Sequence[str], declarados: Sequence[str], onde: str, origem: str,
                      etapa: str, correcao_falta: str, correcao_sobra: str) -> List[Dict[str, str]]:
    achados = []
    faltam = [c for c in aprovados if c not in declarados]
    sobram = [c for c in declarados if c not in aprovados]
    if faltam:
        achados.append(_achado(
            "habilidade-perdida",
            f"{_lista(faltam)} {'está' if len(faltam) == 1 else 'estão'} em {origem} e "
            f"{'saiu' if len(faltam) == 1 else 'saíram'} de {onde}. {correcao_falta}", etapa))
    if sobram:
        achados.append(_achado(
            "habilidade-acrescentada",
            f"{_lista(sobram)} {'aparece' if len(sobram) == 1 else 'aparecem'} em {onde} e não "
            f"{'está' if len(sobram) == 1 else 'estão'} em {origem}. {correcao_sobra}", etapa))
    return achados


def _tempo(texto: str, one_pager: str, onde: str, etapa: str) -> List[Dict[str, str]]:
    alvo = tempo_aprovado(one_pager)
    if alvo is None:
        return []
    divergentes = tempos_divergentes(texto, alvo)
    if not divergentes:
        return []
    exemplos = "; ".join(f"«{linha[:140]}»" for _, linha in divergentes[:3])
    return [_achado(
        "tempo-alterado",
        f"O one-pager aprovado dá {alvo} min em tela (§10), e {onde} declara outro total: {exemplos}. "
        f"Use {alvo} min e a tabela por etapa do §10. Se um parecer pediu menos tempo, a recomendação "
        f"é do PO decidir no one-pager — aqui ela entra só como ressalva não incorporada.", etapa)]


def validar_spec(spec: str, one_pager: str) -> Dict[str, Any]:
    """A spec traduz o one-pager aprovado: mesmas habilidades, mesmo tempo, o podcast declarado."""
    achados: List[Dict[str, str]] = []
    bloco11 = bncc.secao_bloco(spec or "", 11) or ""
    aprovados = codigos_aprovados(one_pager)
    if aprovados and not _decisao_pendente(bloco11, secao(one_pager or "", 2) or ""):
        achados += _comparar_codigos(
            aprovados, bncc.extrair_codigos(bloco11), "o bloco 11 da spec",
            "o contrato de evidência do one-pager aprovado (§12a)", "produto",
            "A spec traduz o one-pager, não o revisa: recoloque cada uma no bloco 11, com a linha da matriz "
            "copiada do §12a (canal, ação, régua ternária). Se um parecer recomendou tirá-la, a recomendação "
            "vai para o bloco 12 como ressalva não incorporada — quem tira habilidade é o PO, no one-pager.",
            "A spec não acrescenta habilidade: tire-a do bloco 11, ou, se a lista oficial obriga a trocá-la, "
            "marque `[ABERTO — dono: produto: …]` dizendo por quê.")
    achados += _tempo(spec, one_pager, "a spec", "produto")
    achados += _literais(spec, one_pager, ("canal_b", "roteiro"), "na spec", "produto",
                         "A spec copia do one-pager, palavra por palavra: a pergunta e as alternativas do Canal B no "
                         "bloco 9, as perguntas do debate no bloco 8. Melhorar a redação é decisão do PO, no one-pager.")
    if tem_podcast(one_pager) and not _RE_PODCAST.search(spec or ""):
        achados.append(_achado(
            "podcast-ausente",
            "O one-pager aprovado tem podcast de recapitulação (§11) e a spec não o menciona. Declare-o no "
            "bloco 8: título, vozes, duração, quando toca e quem toca, copiados do §11 — o roteiro fica no "
            "one-pager. Sem isso, design e dev reescrevem ou esquecem o áudio (aconteceu nas 11 missões).",
            "produto"))
    decididos = parametros_decididos(spec, one_pager)
    # no mesmo assunto bloqueia; número igual em outro assunto (a duração de um áudio) só fica 🟡 para o PO ver
    # ratificado pelo D0 é decisão de agente com registro: não bloqueia, mas não some (o PO decide)
    def bloqueia(d: Tuple[str, str]) -> bool:
        return parametro_no_mesmo_assunto(d[0], d[1], one_pager) and not _RE_RATIFICADO_PELO_D0.search(d[1])

    for severidade, grupo in (("bloqueio", [d for d in decididos if bloqueia(d)]),
                              ("atencao", [d for d in decididos if not bloqueia(d)])):
        if not grupo:
            continue
        exemplos = "; ".join(f"{marcador[:110]} → «{linha[:120]}»" for marcador, linha in grupo[:4])
        achados.append(_achado(
            "parametro-decidido",
            f"{len(grupo)} número(s) que o one-pager aprovado deixou a definir por produto aparece(m) na spec como "
            f"decidido(s), sem marcador: {exemplos}. A spec não decide no lugar do PO: mantenha o número com o "
            "marcador na mesma linha (`[PARÂMETRO — a definir por produto: …]`, ou `[ABERTO — dono: PO: …]`), ou diga "
            "quem o decidiu e quando."
            + ("" if severidade == "bloqueio" else " A linha não fala do mesmo assunto do parâmetro: confira se é ele."),
            "produto", severidade))
    return {"status": _status(achados), "achados": achados, "codigos": aprovados,
            "tempo": tempo_aprovado(one_pager), "podcast": tem_podcast(one_pager)}


def validar_spec_consolidada(spec: str, spec_gate0: str, one_pager: str) -> Dict[str, Any]:
    """A spec que o D0 e o D9 reescreveram no design, contra o one-pager aprovado: só o que eles pioraram.

    Até 07/10/2026 a conferência da spec contra o one-pager só rodava em produto. O D0 e o D9 reescrevem a spec
    inteira, e o split só detecta linha removida (trocar o código numa linha longa do bloco 11, ou acrescentar
    «Tempo total em tela: 25 minutos», passava). O que já divergia na spec do Gate 0 foi decidido em produto — com
    exceção do admin, se foi o caso — e não volta aqui; o que é novo vai ao dono do D0.
    """
    antes = {a["resumo"] for a in validar_spec(spec_gate0, one_pager)["achados"]} if (spec_gate0 or "").strip() else set()
    resultado = validar_spec(spec, one_pager)
    achados = []
    for a in resultado["achados"]:
        if a["resumo"] in antes:
            continue
        achados.append({**a, "etapa": "design", "agente_responsavel": "fecha-lacunas",
                        "resumo": "Depois do fechamento de lacunas (D0) e do ambiente (D9): " + a["resumo"]})
    return {**resultado, "status": _status(achados), "achados": achados}


_ROTULO_LITERAL = {"canal_b": "do Canal B (pergunta ou alternativa)", "roteiro": "do debate",
                   "podcast": "do podcast"}


def _literais(documento: str, one_pager: str, quais: Sequence[str], onde: str, etapa: str,
              correcao: str) -> List[Dict[str, str]]:
    achados: List[Dict[str, str]] = []
    todos = literais(one_pager)
    for qual in quais:
        faltam = literais_ausentes(documento, todos.get(qual) or [])
        if faltam:
            exemplos = "; ".join(f"«{t[:120]}»" for t in faltam[:3])
            achados.append(_achado(
                f"{qual.replace('_', '-')}-reescrito",
                f"{len(faltam)} texto(s) {_ROTULO_LITERAL[qual]} aprovado(s) no one-pager não está(ão) {onde}, nem "
                f"com 85% da redação: {exemplos}. {correcao}", etapa))
    return achados


def validar_copy(copy_revisada: str, one_pager: str) -> List[Dict[str, str]]:
    """A copy revisada traz a pergunta e as alternativas do Canal B e as perguntas do debate como o PO aprovou."""
    if not (copy_revisada or "").strip():
        # vazia com texto aprovado a conferir é o autor mudo, não "nada a cobrar" (auditoria de 08/10/2026)
        lits = literais(one_pager)
        if any(lits.get(q) for q in ("canal_b", "roteiro", "podcast")):
            return [_achado("copy-vazia", "A copy revisada chegou vazia, e o one-pager tem textos aprovados que ela "
                            "precisa trazer (Canal B, debate, podcast). Dono: `copy-ptbr-revisao`.", "design")]
        return []
    achados = _literais(copy_revisada, one_pager, ("canal_b", "roteiro"), "na copy revisada", "design",
                        "Dono: `copy-ptbr-revisao`. A criança ouve e o professor lê exatamente o texto aprovado: copie "
                        "do conteúdo aprovado, sem parafrasear.")
    # o roteiro do podcast também: a passada 1 o reescrevia ("se não vier pronto, escreva") e a revisão o
    # descartava — a exp01ef1b chegou ao banco com 0 de 9 falas do PO (auditoria de 07/10/2026)
    falas = literais(one_pager)["podcast"]
    faltam = literais_ausentes(copy_revisada, falas) if falas else []
    if falas and len(faltam) > 0.2 * len(falas):
        achados.append(_achado(
            "podcast-reescrito",
            f"{len(faltam)} de {len(falas)} falas do podcast aprovado no one-pager (§11) não estão na copy revisada — "
            f"ex.: «{faltam[0][:120]}». Dono: `copy-ptbr-revisao`. O roteiro é o do PO: copie as falas do conteúdo "
            "aprovado, com as mesmas vozes; revise só a marcação de voz.", "design"))
    # e o que o §4 põe na tela: a aposta e as alternativas, as falas da personagem, o caso de transferência. Nas
    # sessões que chegaram ao fim, a copy trazia de 25% a 85% desses textos. 🟡 e não ⛔ enquanto o extrator não é
    # calibrado contra as revisões do time: o PO vê a lista e decide.
    tela = literais(one_pager)["texto_tela"]
    faltam = literais_ausentes(copy_revisada, tela) if tela else []
    if tela and len(faltam) > LIMIAR_TEXTO_DE_TELA * len(tela):
        exemplos = "; ".join(f"«{t[:100]}»" for t in faltam[:4])
        achados.append(_achado(
            "texto-de-tela-reescrito",
            f"{len(faltam)} de {len(tela)} textos que o §4 do one-pager aprovado põe na tela entre aspas não estão na "
            f"copy revisada, nem com 85% da redação: {exemplos}. Dono: `copy-ptbr-revisao`. Copie do conteúdo aprovado "
            "(§4); se o teto de palavras da faixa obrigar a mudar, registre em «Strings que precisam de decisão» "
            "`[PROPOSTA — validar com PO: TC-nn «texto aprovado» → «texto novo» · por quê]`, com o ID do texto-chave "
            "(é o formato que `tools/textos_chave.py` lê para levar a proposta ao PO).", "design", severidade="atencao"))
    for a in achados:
        a["agente_responsavel"] = "copy-ptbr-revisao"
    return achados


#: Fração dos textos de tela do §4 que pode faltar na copy antes de virar achado: a mesma folga do podcast, para o
#: ruído do extrator (uma aspa de exemplo que escapou) não acusar a copy fiel.
LIMIAR_TEXTO_DE_TELA = 0.2


def _texto_visivel(html: str) -> str:
    """O texto das telas: sem `<style>`, comentários e tags. O `<script>` fica — o protótipo da exp01ef1b
    monta todas as telas em templates dentro de um único script, e tirá-lo deixava 436 caracteres."""
    sem = re.sub(r"<style\b.*?</style>|<!--.*?-->", " ", html or "", flags=re.S | re.I)
    sem = re.sub(r"<[^>]+>", " ", sem)
    return re.sub(r"\s+", " ", sem)


def validar_literais_design(camada_caa: str, prototipo_html: str, one_pager: str) -> List[Dict[str, str]]:
    """O Canal B que o PO aprovou chega literal à prancha CAA e às telas do protótipo.

    A camada CAA parafraseou o Canal B na exp09, na exp06 e na exp04 (0 de 8, 0 de 4, 0 de 3 textos), e o
    protótipo da exp06 trazia 1 de 4 (auditoria de 07/10/2026). Só a copy revisada era conferida. A CAA só é
    cobrada quando trata do Canal B — a camada que não se aplica à missão não tem por que trazê-lo.
    """
    achados: List[Dict[str, str]] = []
    if (camada_caa or "").strip() and re.search(r"canal\s*b", camada_caa, re.I):
        for a in _literais(camada_caa, one_pager, ("canal_b",), "na camada CAA", "design",
                           "Dono: `caa`. A prancha mostra a pergunta e as alternativas do Canal B com o texto aprovado — "
                           "o símbolo acompanha o texto, não o substitui."):
            a["agente_responsavel"] = "caa"
            achados.append(a)
    if (prototipo_html or "").strip():
        for a in _literais(_texto_visivel(prototipo_html), one_pager, ("canal_b",), "nas telas do protótipo", "design",
                           "Dono: `prototipo`. O texto das telas sai do sheet de copy, que traz o Canal B literal."):
            a["agente_responsavel"] = "prototipo"
            achados.append(a)
    return achados


def validar_banco(banco: str, one_pager: str) -> List[Dict[str, str]]:
    """O banco de conteúdo grava o roteiro do podcast que o PO aprovou — não escreve outro."""
    falas = literais(one_pager)["podcast"]
    if not falas:
        return []
    if not (banco or "").strip():
        return [_achado("banco-vazio", f"O banco de conteúdo chegou vazio, e o podcast aprovado tem {len(falas)} falas "
                        "que ele grava para a síntese. Dono: `banco-conteudo`.", "dev")]
    faltam = literais_ausentes(banco, falas)
    if len(faltam) <= 0.2 * len(falas):
        return []
    return [_achado(
        "podcast-reescrito",
        f"{len(faltam)} de {len(falas)} falas do podcast aprovado no one-pager (§11) não estão no banco de conteúdo — "
        f"ex.: «{faltam[0][:120]}». O roteiro que vai para a gravação é o do PO, com as mesmas vozes e falas: copie-o "
        f"do conteúdo aprovado. Na exp01ef1b o banco escreveu outro, de antes da aula.", "dev")]


def habilidades_de_referencia(spec: str, one_pager: str) -> Tuple[List[str], str]:
    """`(códigos, de onde vêm)` contra os quais o PRD, o pedagógico e o resumido conferem as habilidades.

    O one-pager aprovado (§12a; sem ele, o §2), como manda a precedência do redator do PRD — «onde as duas
    divergem numa habilidade, siga o one-pager». Até 07/10/2026 a referência era o bloco 11 da spec: com a spec
    sem a EF09CO08 (o loop da spec esgotado, a exceção do admin, o D0 mexendo no bloco 11), o PRD fiel ao
    one-pager recebia «tire-a da matriz». O bloco 11 vale quando o one-pager não tem código, ou quando o currículo
    é decisão pendente no one-pager ou na spec — o código do one-pager que a lista oficial não aceita vira
    `[ABERTO — dono: produto: …]` no bloco 11, e o PRD não pode ser cobrado por ele.
    """
    bloco11 = bncc.secao_bloco(spec or "", 11) or ""
    aprovados = codigos_aprovados(one_pager)
    # código que a lista oficial não tem é do gate BNCC decidir, não do PRD reinserir (auditoria do PR #32)
    oficiais = bncc.habilidades()
    if aprovados and all(c in oficiais for c in aprovados) and not _decisao_pendente(secao(one_pager or "", 2) or "", bloco11):
        s12 = secao(one_pager or "", 12) or ""
        m = _RE_12A.search(s12)
        do_12a = bool(m and bncc.extrair_codigos(s12[m.start():]))
        return aprovados, ("o contrato de evidência do one-pager aprovado (§12a)" if do_12a
                           else "o currículo do one-pager aprovado (§2)")
    return bncc.extrair_codigos(bloco11), "o bloco 11 da spec"


#: Semelhança mínima para o texto entre aspas no documento ser uma redação do aprovado, e não outro texto.
SEMELHANCA_PARAFRASE = 0.6


def literais_parafraseados(documento: str, one_pager: str) -> List[Tuple[str, str]]:
    """`(aprovado, como o documento escreveu)`: texto entre aspas no documento parecido com um texto aprovado (Canal B,
    debate, texto de tela do §4) sem ser ele.

    O corpo do PRD pode remeter ao anexo sem citar; o que ele não pode é citar outra redação — o dev codifica o corpo
    e o anexo diz outra coisa (decisão do usuário, 08/10/2026: o corpo do PRD conferido contra o anexo).
    """
    import difflib

    from tools.fidelidade import _norm

    lit = literais(one_pager)
    alvos = [t for qual in ("canal_b", "roteiro", "texto_tela") for t in lit.get(qual) or []]
    # e os textos-chave do PR 7 (`tools/textos_chave.py`): o Canal B sem os rótulos «Pergunta:»/«Atingiu:» — na exp02ef1b
    # as alternativas vêm em «*Alt 1:* "…" `[Atingiu]`», e a leitura antiga não achava nenhuma — e as opções de cada escolha
    from tools import textos_chave as tk

    chave = tk.extrair(one_pager)
    alvos += [t.texto for t in chave if t.tipo in (tk.TELA, tk.CANAL_B, tk.ROTEIRO) and t.texto not in alvos]
    alvos += [o for t in chave if t.tipo == tk.OPCOES for o in t.opcoes if o not in alvos]
    citados = list(dict.fromkeys(m.group(1).strip() for m in _RE_ENTRE_ASPAS.finditer(documento or "")
                                 if len(m.group(1).strip()) >= 12))
    if not alvos or not citados:
        return []
    saida: List[Tuple[str, str]] = []
    for alvo in alvos:
        if not literais_ausentes(documento, [alvo]):
            continue  # está literal
        a = _norm(alvo)
        melhor = max(citados, key=lambda c: difflib.SequenceMatcher(None, a, _norm(c), autojunk=False).ratio())
        # rótulo curto parece com outro rótulo curto por acaso («Galeria Oculta da Mostra» × «Acessar Feed da
        # Mostra», PRD da exp06ef1b): abaixo de 30 caracteres, só conta o quase idêntico
        corte = SEMELHANCA_PARAFRASE if len(a) >= 30 else 0.8
        if difflib.SequenceMatcher(None, a, _norm(melhor), autojunk=False).ratio() >= corte:
            saida.append((alvo, melhor))
    return saida


_ETAPAS = ("Desafiar", "Navegar", "Decidir", "Resultado", "Explicar", "Refletir")


def tempos_por_etapa(one_pager: str) -> Dict[str, int]:
    """Etapa → minutos em tela, da tabela do §10 (a primeira coluna com minutos depois do nome da etapa)."""
    saida: Dict[str, int] = {}
    for linha in (secao(one_pager or "", 10) or "").splitlines():
        if not linha.strip().startswith("|"):
            continue
        celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
        etapa = next((e for e in _ETAPAS if e.lower() in celulas[0].lower()), None) if celulas else None
        if not etapa or etapa in saida:
            continue
        for celula in celulas[1:]:
            m = re.search(r"(\d{1,2})\s*min", celula)
            if m:
                saida[etapa] = int(m.group(1))
                break
    return saida


def tempos_de_etapa_divergentes(documento: str, one_pager: str) -> List[Tuple[str, int, str]]:
    """`(etapa, aprovado, linha)`: linha de tabela do documento que nomeia uma só etapa e dá a ela minutos que não são os
    do §10. Só tabela: em prosa, o número junto da etapa costuma ser outra coisa (o tempo fora da tela, um teto)."""
    aprovados = tempos_por_etapa(one_pager)
    saida: List[Tuple[str, int, str]] = []
    for linha in _linhas_fora_de_codigo(documento):
        if not linha.strip().startswith("|"):
            continue
        nomeadas = [e for e in aprovados if re.search(rf"\b{e}\b", linha, re.I)]
        if len(nomeadas) != 1:
            continue
        etapa = nomeadas[0]
        numeros = [int(n) for n in re.findall(r"(\d{1,2})\s*min", linha)]
        if numeros and aprovados[etapa] not in numeros and etapa not in [s[0] for s in saida]:
            saida.append((etapa, aprovados[etapa], linha.strip()))
    return saida


def _linhas_de_kpi(prd: str) -> List[str]:
    return [l for l in _linhas_fora_de_codigo(prd) if l.lstrip().startswith("|") and re.search(r"\bKPI-?\d", l)]


def validar_prd(prd: str, spec: str, one_pager: str, artefatos: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """O corpo do PRD (sem o anexo) contra a spec e o one-pager aprovado."""
    achados: List[Dict[str, str]] = []
    corpo = remover_anexo(prd or "")
    da_spec, origem = habilidades_de_referencia(spec, one_pager)
    s14 = secao(corpo, 14)
    if da_spec:
        if s14 is None:
            achados.append(_achado("secao-14-ausente", "O PRD não tem a seção `# 14. Pedagogia e conformidade`, "
                                   "onde fica a matriz das habilidades.", "dev"))
        else:
            achados += _comparar_codigos(
                da_spec, bncc.extrair_codigos(s14), "a matriz da seção 14 do PRD", origem, "dev",
                "Toda habilidade aprovada tem linha na matriz, com a régua inteira — Atingiu, Em processo e "
                "Não atingiu — e a pergunta do Canal B remetendo ao anexo (§12a). O PRD não reabre currículo: se a "
                "spec a tirou, a divergência é defeito a montante — mantenha a linha e registre-a na seção 19 com "
                "dono `produto`.",
                "O PRD não acrescenta habilidade que o one-pager aprovado não tem: tire-a da matriz. Se foi a spec "
                "que a acrescentou, registre a divergência na seção 19 com dono `produto`.")
        linhas_kpi = _linhas_de_kpi(corpo)
        sem_kpi = [c for c in da_spec if not any(c in l for l in linhas_kpi)]
        if sem_kpi:
            achados.append(_achado(
                "habilidade-sem-kpi",
                f"Nenhum KPI da seção 2 mede quantos estudantes atingem {_lista(sem_kpi)}. A evidência pedagógica "
                f"é o número que a missão existe para mover: acrescente o KPI (uma linha pode cobrir várias "
                f"habilidades) com a pergunta «Quantos estudantes chegam a Atingiu em <código>?», a decisão com "
                f"limiar, os `EVT-` das ações que o servidor classifica e o cálculo sobre a coluna que a seção 14 "
                f"diz que guarda o nível dela — nunca `resultado.nivel`, o nível não vai no `track`. Alvo só se o "
                f"one-pager (§17) ou o 9f o fixam; sem eles, `sem meta — primeira medição`.", "dev"))
    achados += _tempo(corpo, one_pager, "o PRD", "dev")
    if tem_podcast(one_pager):
        tem_rf = any(re.search(r"\bRF-\d", l) and _RE_PODCAST.search(l) for l in _linhas_fora_de_codigo(corpo))
        if not tem_rf:
            achados.append(_achado(
                "podcast-sem-requisito",
                "O one-pager aprovado tem podcast de recapitulação (§11, no anexo) e nenhum requisito funcional "
                "do PRD o cita. Acrescente o RF (quem toca, em que tela, em que momento — o aviso do §11 diz "
                "quando), a linha do asset no inventário de conteúdo e a tarefa que o liga.", "dev"))
    if artefatos is not None:
        achados += _artefatos(corpo, artefatos, "o PRD")
    # o corpo que cita o texto aprovado com outra redação: o dev codifica o do corpo, e o anexo diz outra coisa
    parafraseados = literais_parafraseados(corpo, one_pager)
    if parafraseados:
        exemplos = "; ".join(f"aprovado «{a[:90]}» → no corpo «{c[:90]}»" for a, c in parafraseados[:4])
        achados.append(_achado(
            "literal-parafraseado",
            f"{len(parafraseados)} texto(s) que o PO aprovou palavra por palavra aparece(m) no corpo do PRD com outra "
            f"redação: {exemplos}. O corpo copia o texto aprovado, ou remete ao anexo sem citá-lo — nunca uma terceira "
            "versão.", "dev"))
    divergentes = tempos_de_etapa_divergentes(corpo, one_pager)
    if divergentes:
        exemplos = "; ".join(f"{etapa}: aprovado {aprovado} min → «{linha[:110]}»" for etapa, aprovado, linha in divergentes[:4])
        achados.append(_achado(
            "tempo-de-etapa-divergente",
            f"O tempo em tela por etapa do corpo não bate com a tabela do §10 aprovada: {exemplos}. Confira — o anexo "
            "traz a tabela; se a divergência é proposital, registre-a na seção 19.", "dev", severidade="atencao"))
    return {"status": _status(achados), "achados": achados, "codigos": da_spec,
            "tempo": tempo_aprovado(one_pager), "podcast": tem_podcast(one_pager)}


def _artefatos(texto: str, artefatos: Iterable[str], onde: str) -> List[Dict[str, str]]:
    validos = sorted(set(artefatos))
    faltam = artefatos_inexistentes(texto, validos)
    if not faltam:
        return []
    mais_citados = [p for p in validos if p.startswith(("produto/05", "produto/00-", "design/0", "dev/01"))][:12]
    return [_achado(
        "artefato-inexistente",
        f"{onde.capitalize()} cita {_lista(faltam)}, que não {'existe' if len(faltam) == 1 else 'existem'} na sessão. "
        f"Os caminhos reais: {_lista(mais_citados)}.", "dev")]


def validar_pedagogico(pedagogico: str, spec: str, one_pager: str,
                       artefatos: Optional[Iterable[str]] = None, etapa: str = "design") -> Dict[str, Any]:
    """O corpo do one-pager pedagógico (sem o anexo) contra a spec e o one-pager aprovado. Os achados são do design: o
    pedagógico fecha o design desde o PR 10 do plano «Produto dono do contrato» (24/10/2026)."""
    achados: List[Dict[str, str]] = []
    corpo = remover_anexo(pedagogico or "")
    da_spec, origem = habilidades_de_referencia(spec, one_pager)
    if da_spec:
        achados += _comparar_codigos(
            da_spec, bncc.extrair_codigos(corpo), "o one-pager pedagógico", origem, "dev",
            "Cada habilidade entra em «O que a missão ensina» e em «Como a gente sabe que a criança aprendeu», "
            "com o código entre parênteses.",
            "O pedagógico não acrescenta habilidade: tire-a.")
    achados += _tempo(corpo, one_pager, "o one-pager pedagógico", "dev")
    if tem_podcast(one_pager) and not _RE_PODCAST.search(corpo):
        achados.append(_achado(
            "podcast-ausente",
            "O one-pager aprovado tem podcast de recapitulação (§11) e o pedagógico não o menciona. A seção "
            "«O podcast do fechamento» diz o título, quem fala, quanto dura, quando tocar e quem toca; o "
            "roteiro vai no anexo, para o time pedagógico aprovar o texto.", "dev"))
    # a pergunta do Canal B e as perguntas do debate que o professor lê em sala, como o PO aprovou
    achados += _literais(corpo, one_pager, ("canal_b", "roteiro"), "no corpo do one-pager pedagógico", "dev",
                         "O professor lê em sala exatamente o texto aprovado: copie do conteúdo aprovado, sem parafrasear.")
    if artefatos is not None:
        achados += _artefatos(corpo, artefatos, "o one-pager pedagógico")
    for a in achados:
        a["etapa"] = etapa
    return {"status": _status(achados), "achados": achados, "codigos": da_spec,
            "tempo": tempo_aprovado(one_pager), "podcast": tem_podcast(one_pager)}


#: Linha do resumido que cita a habilidade sem afirmá-la: a proposta de tirá-la, «a confirmar», a divergência.
_RE_HABILIDADE_SO_CITADA = re.compile(r"PROPOSTA|a confirmar|DIVERG[ÊE]NCIA|ABERTO|DECIS[ÃA]O PENDENTE|plaus[íi]vel", re.I)


def validar_resumido(resumido: str, spec: str, one_pager: str) -> Dict[str, Any]:
    """O one-pager resumido contra o canônico aprovado e a spec.

    O resumido é o que o time de produto lê para aprovar a missão pedagogicamente (A061); o canônico é o que
    segue para design e dev. Até 07/10/2026 nada os comparava, e o prompt mandava a spec vencer quando os dois
    divergiam. Confere as habilidades do bloco 11 (já conferidas contra o §12a), o tempo em tela do §10 e o Canal
    B com o texto aprovado — o contrato de evidência do resumido usa as alternativas como tabela de marcadores, e
    nas sessões de outubro só uma em cada três o trazia. Habilidade citada numa proposta de tirá-la ou «a
    confirmar» não conta como acrescentada.
    """
    achados: List[Dict[str, str]] = []
    corpo = resumido or ""
    da_spec, origem = habilidades_de_referencia(spec, one_pager)
    if da_spec and not _decisao_pendente(bncc.secao_bloco(spec or "", 11) or ""):
        citadas = bncc.extrair_codigos(corpo)
        afirmadas = bncc.extrair_codigos("\n".join(l for l in _linhas_fora_de_codigo(corpo)
                                                   if not _RE_HABILIDADE_SO_CITADA.search(l)))
        correcao_falta = ("Cada habilidade aprovada entra no componente curricular e no contrato de evidência, com "
                          "o código entre crases.")
        correcao_sobra = ("O resumido não acrescenta habilidade: tire-a, ou cite-a como `[PROPOSTA — validar com PO: …]` "
                          "ou «a confirmar».")
        achados += [a for a in _comparar_codigos(da_spec, citadas, "o one-pager resumido", origem,
                                                 "produto", correcao_falta, correcao_sobra)
                    if a["codigo"] == "habilidade-perdida"]
        achados += [a for a in _comparar_codigos(da_spec, afirmadas, "o one-pager resumido", origem,
                                                 "produto", correcao_falta, correcao_sobra)
                    if a["codigo"] == "habilidade-acrescentada"]
    achados += _tempo(corpo, one_pager, "o one-pager resumido", "produto")
    # 🟡, não ⛔: nas 15 sessões do bucket o resumido não trazia o Canal B literal em 7 — geradas antes de o prompt
    # pedir — e travar o de acordo de produto por isso recusaria quase metade das missões (auditoria do PR #32).
    achados += [{**a, "severidade": "atencao"} for a in _literais(
        corpo, one_pager, ("canal_b",), "no one-pager resumido", "produto",
        "O time pedagógico aprova a pergunta e as alternativas que a criança vai ler: no contrato de evidência, a "
        "tabela de marcadores do Canal B traz o texto do §12a do canônico, palavra por palavra, e só depois a "
        "explicação de cada nível.")]
    for a in achados:
        a["agente_responsavel"] = "one-pager-resumido"
    return {"status": _status(achados), "achados": achados, "codigos": da_spec,
            "tempo": tempo_aprovado(one_pager), "podcast": tem_podcast(one_pager)}


# --------------------------------------------------------------------------- relatório
def relatorio(resultado: Dict[str, Any], documento: str, missao: str = "") -> str:
    icone = {"aprovado": "🟢 FIEL AO ONE-PAGER APROVADO", "amarelo": "🟡 COM RESSALVAS",
             "bloqueado": "🔴 DIVERGE DO ONE-PAGER APROVADO"}[resultado["status"]]
    tempo = f"{resultado['tempo']} min em tela" if resultado.get("tempo") else "sem total em tela no §10"
    linhas = [f"# Conteúdo aprovado × {documento} — {missao or 'missão'}", "", f"**Veredito: {icone}**", "",
              f"Habilidades conferidas: {_lista(resultado.get('codigos') or []) or 'nenhuma'} · {tempo} · "
              f"podcast no one-pager: {'sim' if resultado.get('podcast') else 'não'}", ""]
    if resultado["achados"]:
        linhas += ["## Achados", ""]
        for a in resultado["achados"]:
            marca = "❌" if a["severidade"] == "bloqueio" else "⚠️"
            linhas.append(f"- {marca} **{a['codigo']}** — {a['resumo']}")
    else:
        linhas.append("Nenhum achado: habilidades, tempo em tela e podcast batem com o one-pager aprovado.")
    linhas += ["", "```json", json.dumps(
        {"agente": AGENTE, "missao": missao, "documento": documento, "status": resultado["status"],
         "achados": resultado["achados"]}, ensure_ascii=False, indent=2), "```"]
    return "\n".join(linhas)
