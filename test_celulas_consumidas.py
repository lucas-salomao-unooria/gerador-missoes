"""A tabela de células consumidas (`prompts/references/celulas-consumidas.md`) contra o que ela descreve.

Só o D0 lê a tabela: percorre a spec com ela para achar lacunas e manda cada uma a quem consome a célula.
Uma tabela errada manda a lacuna ao agente errado, ou a nenhum. A auditoria de 07/10/2026 cruzou a tabela com
os prompts de design e achou: só os blocos 0–12, sem o conteúdo aprovado, o bloco 14 nem o glossário; o D2
como consumidor de `0.liberacao` e de `6.duração`, que a jornada não lê; e consumidores faltando em linha
atrás de linha (ausências sem D4, D6 e D8; schemas sem D6; curadoria sem D5; painel sem D5 e D7; roteiro
do debate sem D6 e D8; viewport, painel da etapa e congelamento sem D8). Cada cruzamento que achou defeito
virou um teste aqui:

- toda célula `N.campo` está num bloco que o formato da spec tem (lido pelos títulos de bloco de
  `formato-spec.md`), na seção com o título dele, e fala de algo que o bloco contém;
- todo agente citado como consumidor existe em `agents/design/__init__.py`;
- todo prompt de design que cita «bloco N» tem uma linha do bloco N que o aponta, e todo prompt que recebe
  o conteúdo aprovado tem uma linha do conteúdo aprovado;
- toda seção de `SECOES_DESIGN` tem a sua linha, e quem a consome recebe o conteúdo aprovado ou o one-pager.
"""

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PROMPTS = RAIZ / "prompts"
TABELA = PROMPTS / "references" / "celulas-consumidas.md"
FORMATO = PROMPTS / "references" / "formato-spec.md"
#: O gabarito do one-pager: os `§N` que a tabela cita são as seções `## N.` dele.
ONE_PAGER = PROMPTS / "produto" / "014_secoes_apoio.md"

#: Código de agente usado na tabela → nome do agente em `agents/design/__init__.py`.
AGENTES = {
    "D0": "A065FechaLacunas",
    "D9": "A067AmbienteSimulado",
    "D1": "A070BriefOficio",
    "D2": "A071Jornada",
    "D3": "A072Fluxo",
    "D4": "A073CopyPtBr",
    "D4b": "A074Caa",
    "D5": "A075Telas",
    "D6": "A077CopyRevisao",
    "D8": "A079Prototipo",
    "D7": "A088QaEntregaveis",
}

#: Prompts fora do cruzamento «bloco citado → linha que aponta o agente». O D0 percorre a tabela inteira:
#: os blocos que o prompt dele cita («estados de falha (bloco 2) sem descrição», «Bloco 9 sem lista») dizem o
#: que ele pode preencher, não o que lê como contrato.
FORA_DO_CRUZAMENTO = {"D0"}
#: Bloco que o próprio agente escreve: citá-lo diz o que ele emite, não o que consome.
BLOCO_EMITIDO = {"D9": {14}}

#: «bloco 4», «Bloco 9», «blocos 13»; nunca um intervalo («blocos 0–12», «bloco 1–13»), que é menção
#: incidental — «os blocos 1–13 intocados» não é consumo de bloco nenhum.
_RE_BLOCO = re.compile(r"\bblocos?\s+(\d{1,2})(?!\d)(?!\s*[–-]\s*\d)", re.IGNORECASE)
_RE_CODIGO = re.compile(r"\bD\d+b?\b")
_RE_SECAO_BLOCO = re.compile(r"^Bloco (\d+) — (.+)$")
SECAO_GLOSSARIO = "Glossário canônico"
PREFIXO_CONTEUDO_APROVADO = "Conteúdo aprovado"
#: Palavras curtas demais ou genéricas demais para dizer que a célula está no bloco certo.
_VAZIAS = frozenset({"para", "como", "cada", "pelo", "pela", "quem", "onde", "isso", "esta", "este", "todo",
                     "toda", "todos", "todas", "entre", "sobre", "dentro", "mesmo", "mesma", "ainda", "nunca",
                     "bloco", "blocos", "spec", "linha", "campo"})


# --------------------------------------------------------------------------- leitura
def _ler(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8")


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()


def _palavras(texto: str) -> set:
    return {p for p in re.findall(r"[a-z]{4,}", _sem_acento(texto)) if p not in _VAZIAS}


def _consumidores(coluna: str) -> set:
    """Os códigos de agente da coluna «Quem consome», fora dos parênteses.

    Dentro dos parênteses vai o detalhe, e `D7 (D8)` é a dimensão D8 do QA, não o protótipo.
    """
    anterior = None
    while anterior != coluna:
        anterior, coluna = coluna, re.sub(r"\([^()]*\)", "", coluna)
    return set(_RE_CODIGO.findall(coluna))


@lru_cache(maxsize=1)
def _secoes_da_tabela() -> dict:
    """Título de cada seção `## …` da tabela → as linhas dela: (célula, quem consome, sem ela)."""
    secoes, atual = {}, None
    for linha in _ler(TABELA).splitlines():
        if linha.startswith("## "):
            atual = linha[3:].strip()
            secoes[atual] = []
        elif atual and linha.startswith("|"):
            celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
            if celulas[0] == "Célula" or set(celulas[0]) <= set("-: "):
                continue
            assert len(celulas) == 3, f"linha fora das três colunas em «{atual}»: {linha}"
            secoes[atual].append(tuple(celulas))
    return secoes


def _secoes_de_bloco() -> dict:
    """Número do bloco → (título da seção na tabela, linhas)."""
    saida = {}
    for titulo, linhas in _secoes_da_tabela().items():
        m = _RE_SECAO_BLOCO.match(titulo)
        if m:
            assert int(m.group(1)) not in saida, f"bloco {m.group(1)} com duas seções na tabela"
            saida[int(m.group(1))] = (m.group(2).strip(), linhas)
    return saida


def _linhas_do_conteudo_aprovado() -> list:
    secoes = [t for t in _secoes_da_tabela() if t.startswith(PREFIXO_CONTEUDO_APROVADO)]
    assert len(secoes) == 1, f"esperada uma seção «{PREFIXO_CONTEUDO_APROVADO} …» na tabela, achadas: {secoes}"
    return _secoes_da_tabela()[secoes[0]]


@lru_cache(maxsize=1)
def _blocos_do_formato() -> dict:
    """Número do bloco → (título, texto), lidos de `formato-spec.md`.

    Blocos 0–12: os títulos `## N. …` do gabarito. Blocos 13 e 14: o que a regra de alteração descreve, e no
    14 também a ficha que o D9 emite (`## Bloco 14 — Ficha do ambiente` do prompt dele), que é onde os campos
    do bloco estão definidos.
    """
    texto = _ler(FORMATO)
    inicios = [m.start() for m in re.finditer(r"^## ", texto, re.M)]
    blocos = {}
    for m in re.finditer(r"^## (\d+)\. (.+)$", texto, re.M):
        fim = next((p for p in inicios if p > m.start()), len(texto))
        blocos[int(m.group(1))] = (m.group(2).strip(), texto[m.start():fim])
    for m in re.finditer(r"^- \*\*Bloco (\d+) — ([^*]+)\*\*.*$", texto, re.M):
        blocos[int(m.group(1))] = (m.group(2).strip(), m.group(0))
    d9 = _ler(PROMPTS / _prompts_de_design()["D9"])
    m = re.search(r"^## Bloco 14 — Ficha do ambiente.*?(?=^## |\Z)", d9, re.M | re.S)
    assert m, "o prompt do D9 não tem mais a seção «## Bloco 14 — Ficha do ambiente»"
    titulo, corpo = blocos[14]
    blocos[14] = (titulo, corpo + "\n" + m.group(0))
    return blocos


def _subsecoes_do_glossario() -> set:
    texto = _ler(FORMATO)
    ini = texto.index(f"## {SECAO_GLOSSARIO}")
    fim = texto.find("\n## ", ini + 1)
    return {m.group(1).strip() for m in re.finditer(r"^### (.+)$", texto[ini:fim if fim > 0 else None], re.M)}


@lru_cache(maxsize=1)
def _prompts_de_design() -> dict:
    """Código do agente → arquivo do prompt (relativo a `prompts/`), via `DESIGN_METADATA`."""
    from agents import design

    arquivos = {m["id"]: m["prompt_file"] for m in design.DESIGN_METADATA if m.get("prompt_file")}
    return {codigo: arquivos[nome] for codigo, nome in AGENTES.items() if nome in arquivos}


# --------------------------------------------------------------------------- 1. o formato da spec
def test_toda_celula_esta_num_bloco_do_formato_da_spec():
    blocos = _blocos_do_formato()
    secoes = _secoes_de_bloco()
    assert set(secoes) == set(blocos), (
        f"blocos da tabela {sorted(secoes)} ≠ blocos do formato da spec {sorted(blocos)}: bloco sem seção na "
        "tabela é bloco que o D0 não varre")
    erros = []
    for n, (titulo, linhas) in sorted(secoes.items()):
        titulo_formato, texto_formato = blocos[n]
        if not _sem_acento(titulo_formato).startswith(_sem_acento(titulo)):
            erros.append(f"seção «Bloco {n} — {titulo}» ≠ título do formato «{titulo_formato}»")
        assert linhas, f"seção do bloco {n} sem nenhuma linha"
        vocabulario = _palavras(texto_formato)
        for celula, _, _ in linhas:
            if not celula.startswith(f"{n}."):
                erros.append(f"«{celula}» está na seção do bloco {n}")
            elif not _palavras(celula[len(f'{n}.'):]) & vocabulario:
                erros.append(f"«{celula}» não tem palavra em comum com o bloco {n} do formato da spec — bloco errado?")
    assert not erros, "\n".join(erros)


def test_glossario_da_tabela_e_o_do_formato():
    subsecoes = _subsecoes_do_glossario()
    assert subsecoes, "formato-spec.md sem as subseções do glossário canônico"
    linhas = _secoes_da_tabela().get(SECAO_GLOSSARIO)
    assert linhas, f"a tabela não tem a seção «{SECAO_GLOSSARIO}»"
    citadas = set()
    for celula, _, _ in linhas:
        m = re.match(r"Glossário\.(.+?)(?: — |$)", celula)
        assert m, f"célula do glossário fora da notação `Glossário.<subseção>`: «{celula}»"
        assert m.group(1).strip() in subsecoes, f"«{m.group(1)}» não é subseção do glossário canônico: {subsecoes}"
        citadas.add(m.group(1).strip())
    assert citadas == subsecoes, f"subseções do glossário sem linha na tabela: {subsecoes - citadas}"


def test_bloco_e_secao_do_one_pager_citados_existem():
    texto = _ler(TABELA)
    blocos = _blocos_do_formato()
    citados = {int(n) for n in _RE_BLOCO.findall(texto)}
    assert citados <= set(blocos), f"a tabela cita bloco que o formato da spec não tem: {citados - set(blocos)}"
    secoes_one_pager = {int(n) for n in re.findall(r"^## (\d+)\. ", _ler(ONE_PAGER), re.M)}
    paragrafos = {int(n) for n in re.findall(r"§(\d+)", texto)}
    assert paragrafos <= secoes_one_pager, f"a tabela cita seção do one-pager que não existe: {paragrafos - secoes_one_pager}"


def test_tabela_nao_tem_chave_que_o_adk_interpolaria():
    # A tabela entra inteira no prompt do D0: `{conteudo_aprovado?}` escrito aqui seria trocado pelo valor.
    achado = re.search(r"\{[A-Za-z_][A-Za-z0-9_]*\??\}", _ler(TABELA))
    assert achado is None, f"`{achado.group()}` na tabela seria interpolado pelo ADK no prompt do D0"


# --------------------------------------------------------------------------- 2. os agentes
def test_todo_agente_citado_existe():
    from agents import design

    llm = {m["id"] for m in design.DESIGN_METADATA if (m.get("prompt_file") or "").startswith("design/")}
    assert set(AGENTES.values()) == llm, (
        f"agentes de design com prompt sem código na tabela: {llm - set(AGENTES.values())}; "
        f"códigos sem agente: {set(AGENTES.values()) - llm}")
    for codigo, nome in AGENTES.items():
        assert re.search(rf"^\s*{codigo.lower()}\s+{nome}\b", design.__doc__ or "", re.M), (
            f"o docstring de agents/design não diz mais que {codigo} é {nome}")
    citados = {(codigo, celula) for linhas in _secoes_da_tabela().values()
               for celula, consome, _ in linhas for codigo in _consumidores(consome)}
    desconhecidos = sorted(f"{c} em «{celula}»" for c, celula in citados if c not in AGENTES)
    assert not desconhecidos, "consumidor que não é agente de design:\n" + "\n".join(desconhecidos)


def test_o_d0_le_a_tabela():
    prompt = _ler(PROMPTS / _prompts_de_design()["D0"])
    assert "<!-- include: references/celulas-consumidas.md -->" in prompt, "nenhum agente lê a tabela"


# --------------------------------------------------------------------------- 3. os prompts contra a tabela
def test_prompt_que_cita_um_bloco_tem_linha_que_o_aponta():
    consumo = {n: set().union(*(_consumidores(c) for _, c, _ in linhas)) for n, (_, linhas) in _secoes_de_bloco().items()}
    faltas = []
    for codigo, arquivo in sorted(_prompts_de_design().items()):
        if codigo in FORA_DO_CRUZAMENTO:
            continue
        citados = {int(n) for n in _RE_BLOCO.findall(_ler(PROMPTS / arquivo))} - BLOCO_EMITIDO.get(codigo, set())
        faltas += [f"{codigo} ({arquivo}) cita o bloco {n}, e nenhuma linha do bloco {n} o aponta"
                   for n in sorted(citados) if codigo not in consumo.get(n, set())]
    assert not faltas, "\n".join(faltas)


def test_quem_recebe_o_conteudo_aprovado_tem_linha_nele():
    consumo = set().union(*(_consumidores(c) for _, c, _ in _linhas_do_conteudo_aprovado()))
    faltas, sem_fonte = [], []
    for codigo, arquivo in sorted(_prompts_de_design().items()):
        prompt = _ler(PROMPTS / arquivo)
        if "{conteudo_aprovado?}" in prompt and codigo not in consumo:
            faltas.append(f"{codigo} ({arquivo}) recebe o conteúdo aprovado e nenhuma linha dele o aponta")
        if codigo in consumo and "{conteudo_aprovado?}" not in prompt and "{one_pager?}" not in prompt:
            sem_fonte.append(f"{codigo} ({arquivo}) consta como leitor do conteúdo aprovado e não recebe nem ele "
                             "nem o one-pager")
    assert not faltas + sem_fonte, "\n".join(faltas + sem_fonte)


# --------------------------------------------------------------------------- 4. o conteúdo aprovado
def test_secoes_que_o_design_recebe_tem_linha():
    from tools.conteudo_aprovado import SECOES_DESIGN, TITULOS

    linhas = {}
    for celula, _, _ in _linhas_do_conteudo_aprovado():
        m = re.match(r"§(\d+) (.+)$", celula)
        assert m, f"linha do conteúdo aprovado fora da notação `§N <título>`: «{celula}»"
        linhas[int(m.group(1))] = m.group(2)
    faltando = [n for n in SECOES_DESIGN if n not in linhas]
    assert not faltando, f"seções que o design recebe e a tabela não cita: {faltando}"
    a_mais = sorted(set(linhas) - set(SECOES_DESIGN))
    assert not a_mais, f"a tabela cita como conteúdo aprovado seção que o design não recebe: {a_mais}"
    for n in SECOES_DESIGN:
        # o título é o que o agente vê: `## <título> — one-pager §N`
        assert linhas[n].startswith(TITULOS[n]), f"§{n}: «{linhas[n]}» não começa pelo título «{TITULOS[n]}»"


def test_espelho_do_conteudo_aprovado_e_celula_da_tabela():
    secoes = _secoes_de_bloco()
    erros = []
    for celula, _, _ in _linhas_do_conteudo_aprovado():
        _, _, espelho = celula.partition("espelho:")
        for n, palavra in re.findall(r"\b(\d{1,2})\.([^\W\d_]+)", espelho):
            rotulos = [c for c, _, _ in secoes.get(int(n), ("", []))[1]]
            if not any(r.startswith(f"{n}.{palavra}") for r in rotulos):
                erros.append(f"«{celula}» aponta o espelho `{n}.{palavra}…`, que não é célula do bloco {n}")
    assert not erros, "\n".join(erros)
