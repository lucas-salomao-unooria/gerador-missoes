"""O PRD contra o design: tela, chave de copy, asset e estado que o design fechou chegam ao PRD por ID.

O PRD era conferido contra a spec, o one-pager e a plataforma — e nunca contra o design, que é de onde
quem codifica tira as telas, os textos e os arquivos. A auditoria de 07/10/2026 leu o PRD da exp01ef1b
ao lado dos artefatos de design da mesma sessão: ele citava 0 das 90 chaves da copy revisada, 1 dos 28
assets V1 do brief, 0 dos 17 estados do «Contrato de estados» da spec (a máquina de estados da §6 tinha
virado uma tabela de telas); 12 dos 17 requisitos P0 não tinham critério EARS nem Gherkin;
`ParametrosDoPreparoExp01ef1bSchema` era o corpo de uma rota sem estar definido em lugar nenhum do PRD;
e os KPI-14..17 — que vinham de `PQ-02..05`, marcadas `[PROPOSTA — validar com PO]` na spec — chegaram
sem o marcador: o PO leria aquilo como decidido. Por cima, o resumo executivo trazia uma seção «Status
dos gates» escrita pelo redator, com «Telemetria e Arquitetura: 🟢» enquanto o gate estava 🔴. Nenhum
gate acusou nada. A exp09ef1b, ao contrário, tinha uma story por tela e 100 das 104 chaves da copy: o
redator consegue, quando alguém confere.

Dez conferências, todas por conjunto de IDs e nenhuma por contagem (`tools/telas.py` conta por quê:
cinco quadros com três estados da mesma tela aprovavam com três telas faltando):

1. `tela-sem-story` ⛔ — toda tela do inventário da jornada está nas stories (§7) ou no inventário (§10);
2. `chave-de-copy-ausente` ⛔ e `chave-sem-onde-vive` ⛔ — toda chave da copy revisada, pelo nome, na story
   da tela dela, numa tabela `| Chave | Onde vive |` preenchida; curinga (`e2.rotulo.*`) não cobre, e a
   lista inteira das faltantes vai no resumo (decisão do PO de 07/10/2026);
3. `asset-fora-do-inventario` ⛔ — todo asset V1 do brief está no PRD;
4. `estado-da-spec-sem-mapa` — todo estado do contrato da spec (bloco 2) está no PRD; até metade
   faltando é ⚠️, acima ⛔;
5. `status-de-gate-no-corpo` ⛔ — o redator não escreve status de gate: quem os publica é a esteira;
6. `rf-p0-sem-criterio` ⛔ — todo RF P0 tem critério EARS ou Gherkin, na linha ou num bloco que o cita;
7. `schema-indefinido` — todo `…Schema`/`…Dto` citado é definido no próprio PRD (⛔ só o nome; ⚠️ campos
   em prosa ou «existente» sem dizer de onde);
8. `proposta-perdida` ⚠️ — o que a spec marcou `[PROPOSTA …]` continua marcado no PRD;
9. `evento-perdido` ⚠️ — todo `verbo · objeto` da tabela de eventos da spec (bloco 9) está na §13;
10. `ausencia-perdida` ⚠️ — toda ausência declarada da spec (bloco 5) chega ao PRD.

E, pelo mesmo relatório, o que só o PRD leva à plataforma (`tools/conferir_prd_plataforma.validar_prd`):
tipos e chaves do modelo de dados, a sessão por rodada, o `experiencia.json` completo e com o id derivado,
a ADR, a capacidade que o SDK não tem, o modelo de IA e os registros do hub que os testes da plataforma
cobram.

As severidades foram fixadas lendo as sete sessões completas do bucket (exp01, exp02em1b, exp04, exp05,
exp06, exp07 e exp09); cada conferência diz no docstring o que mediu. Nenhum dos sete PRDs passa
inteiro: todos escrevem status de gate (o gabarito passou a proibir depois deles), nenhum nomeia todos
os assets V1 e nenhum diz onde a chave de copy vive — é o que a esteira vai cobrar a partir daqui. O anexo literal do PRD
(`tools.conteudo_aprovado.remover_anexo`) não conta como cobertura: é a esteira que o cola, não o
redator que o escreve. Todo achado tem dono `prd-writer`, e o resumo diz o que reescrever.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from tools import telas
from tools.conteudo_aprovado import remover_anexo
from tools.markdown_blocos import desembrulhar_documento

AGENTE = "cobertura-design"
DONO = "prd-writer"

#: Fração de estados do contrato da spec que pode faltar no PRD antes de bloquear: acima dela o PRD tem outra
#: máquina de estados (exp01ef1b 100% fora, exp06ef1b 91%); abaixo, é um estado esquecido (exp04ef1b, exp07ef1b).
TETO_ESTADOS_AUSENTES = 0.5
#: Intervalo maior que isto não é intervalo de IDs: «`E1-ALU-01` a 30 segundos» não vira 30 telas. Asset
#: tem intervalo grande de verdade — `img-exp06ef1b-17` a `48` são as 32 fotos do carrossel.
_TETO_TELAS = 20
_TETO_IDS = 200

_RE_CERCA = re.compile(r"^\s*(```|~~~)")
_RE_TITULO = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


# --------------------------------------------------------------------------- utilidades de texto
def _norm(texto: str) -> str:
    sem = "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", sem).strip(" `*_|:")


def _linhas(texto: str) -> List[Tuple[int, str, bool]]:
    """(número da linha, linha, está dentro de bloco de código) — o número começa em 1."""
    saida: List[Tuple[int, str, bool]] = []
    cerca = False
    for n, linha in enumerate((texto or "").splitlines(), 1):
        if _RE_CERCA.match(linha):
            saida.append((n, linha, True))
            cerca = not cerca
            continue
        saida.append((n, linha, cerca))
    return saida


def _desembrulhar(texto: str) -> str:
    """O documento sem a cerca ```markdown que o agente às vezes põe em volta dele inteiro.

    A spec da exp09ef1b chegou assim: lida com a cerca, o documento todo era bloco de código e o
    contrato de estados sumia.
    """
    return desembrulhar_documento(texto or "") or ""


def _secao_por_titulo(texto: str, padrao: "re.Pattern[str]") -> Optional[str]:
    """Corpo da seção cujo título casa `padrao`, até o próximo título de nível igual ou mais alto.

    Título dentro de bloco de código não conta. Com mais de um título que casa, vale o de nível mais
    alto: o PRD da exp02em1b tem um `### 10. Custos e Quotas de IA` dentro da §9, antes do
    `# 10. UX, telas e design` — o `secao()` do conteúdo aprovado pegava o primeiro e a §10 saía errada.
    """
    linhas = _linhas(texto)
    candidatos = []
    for i, (_, linha, cerca) in enumerate(linhas):
        m = _RE_TITULO.match(linha)
        if not cerca and m and padrao.search(m.group(2).strip("*_ ")):
            candidatos.append((len(m.group(1)), i))
    if not candidatos:
        return None
    nivel, i = min(candidatos)
    corpo: List[str] = []
    for _, outra, cerca2 in linhas[i + 1:]:
        m2 = _RE_TITULO.match(outra)
        if not cerca2 and m2 and len(m2.group(1)) <= nivel:
            break
        corpo.append(outra)
    return "\n".join(corpo)


def secao_numerada(texto: str, numero: int, *titulos: str) -> Optional[str]:
    """A seção `numero` (`# 7. User stories`), ou, sem o número, a que tem uma das palavras do título."""
    achada = _secao_por_titulo(texto, re.compile(rf"^{numero}\s*(?:\.(?![\dA-Za-z])|[—–-])"))
    if achada is None and titulos:
        achada = _secao_por_titulo(texto, re.compile("|".join(titulos), re.I))
    return achada


def _celulas(linha: str) -> List[str]:
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", linha.strip().strip("|"))]


def tabelas(texto: str) -> List[Tuple[List[str], List[Dict[str, str]]]]:
    """Toda tabela markdown fora de bloco de código: (cabeçalho normalizado, linhas por nome de coluna)."""
    achadas: List[Tuple[List[str], List[Dict[str, str]]]] = []
    cab: Optional[List[str]] = None
    corpo: List[Dict[str, str]] = []

    def fechar() -> None:
        nonlocal cab, corpo
        if cab is not None:
            achadas.append((cab, corpo))
        cab, corpo = None, []

    for _, linha, cerca in _linhas(texto):
        s = linha.strip()
        if cerca or not s.startswith("|"):
            fechar()
            continue
        celulas = _celulas(s)
        if set("".join(celulas)) <= set("-: "):
            continue
        if cab is None:
            cab = [_norm(c) for c in celulas]
            continue
        corpo.append({cab[k]: celulas[k] if k < len(celulas) else "" for k in range(len(cab))})
    fechar()
    return achadas


def _coluna(cabecalho: Sequence[str], *prefixos: str) -> Optional[str]:
    """O nome da primeira coluna que começa por um dos prefixos (já normalizados)."""
    for p in prefixos:
        for c in cabecalho:
            if c == p or c.startswith(p):
                return c
    return None


def _status(achados: List[Dict[str, str]]) -> str:
    if any(a["severidade"] == "bloqueio" for a in achados):
        return "bloqueado"
    return "amarelo" if achados else "aprovado"


def _lista(itens: Iterable[str], limite: int = 12) -> str:
    itens = list(itens)
    corpo = ", ".join(f"`{i}`" for i in itens[:limite])
    return corpo + (f" e mais {len(itens) - limite}" if len(itens) > limite else "")


def corpo_do_prd(prd: str) -> str:
    """O PRD sem a cerca em volta e sem o anexo literal que a esteira cola no fim."""
    return remover_anexo(_desembrulhar(prd))


# --------------------------------------------------------------------------- intervalos de IDs
#: Separadores de intervalo: `..`, `...`, `…`, `–`, `—`, hífen colado (`01-05`), e « a » / « até ».
_SEP = r"(?:\s*(?:\.\.\.?|…)\s*|\s*[–—]\s*|-|\s+(?:a|at[ée])\s+)"


def _faixa(ini: str, fim: str, teto: int = _TETO_IDS) -> List[str]:
    """`01`, `05` → `01 02 03 04 05`, com o zero à esquerda do início. Faixa absurda → só as pontas."""
    a, b = int(ini), int(fim)
    if not 0 < b - a <= teto:
        return [ini, fim] if b != a else [ini]
    return [str(n).zfill(len(ini)) for n in range(a, b + 1)]


_RE_TELA_FAIXA = re.compile(
    r"\bE(\d)[-_](ALU|PROF|SIS)[-_](\d{2})[A-Za-z]?[`*]*"
    r"(?:" + _SEP + r"[`*]*(?:E\1[-_]\2[-_])?(?P<fim>\d{2})(?![\w-])"
    r"|(?P<lista>(?:\s*/\s*[`*]*\d{2}(?![\w-]))+))"
)


def ids_de_tela(texto: str) -> Set[str]:
    """IDs de tela citados, normalizados por `tools.telas`, com intervalos e listas expandidos.

    `E0-PROF-01..05`, `E0-PROF-01 a 05`, `E0-PROF-01–05`, `E3-ALU-01 a E3-ALU-03` e `E0-PROF-01/03/05`. As
    stories da exp01ef1b cobrem as telas por intervalo (`US-07 — E6-ALU-01..05`): lidas só pelo ID
    literal, 10 das 22 telas sumiam da §7.
    """
    citados = set(telas.ids(texto))
    for m in _RE_TELA_FAIXA.finditer(texto or ""):
        base = f"E{m.group(1)}-{m.group(2)}-"
        if m.group("fim"):
            numeros = _faixa(m.group(3), m.group("fim"), _TETO_TELAS)
        else:
            numeros = [m.group(3)] + re.findall(r"\d{2}", m.group("lista"))
        citados.update(base + n for n in numeros)
    return citados


def _expandir_faixas(texto: str, prefixo: str) -> Set[str]:
    """`PQ-02..05`, `KPI-14 a KPI-17`, `pic-exp01ef1b-17` a `23` → cada ID do intervalo.

    `prefixo` é a expressão do que vem antes do número (com o hífen). O intervalo só vale com o mesmo
    prefixo dos dois lados, ou com o número sozinho do lado direito.
    """
    rx = re.compile(r"(?P<pre>" + prefixo + r")(?P<ini>\d{1,3})[`*]*" + _SEP + r"[`*]*(?:(?P=pre))?(?P<fim>\d{1,3})(?![\w-])")
    saida: Set[str] = set()
    for m in rx.finditer(texto or ""):
        saida.update(m.group("pre") + n for n in _faixa(m.group("ini"), m.group("fim")))
    return saida


def _presente(identificador: str, texto: str, ignorar_caixa: bool = False, arquivo: bool = False) -> bool:
    """O ID inteiro, sem ser pedaço de outro: `e6.x.instrucao_caa` não está em `e6.x.instrucao_caa_p1`.

    Com `arquivo`, o ID com extensão também vale (`aud-exp01ef1b-01.mp3`): para chave de copy o ponto
    depois do nome é outra chave, para asset é o arquivo dele.
    """
    flags = re.I if ignorar_caixa else 0
    depois = r"(?![\w]|-\w)" if arquivo else r"(?![\w]|[.-]\w)"
    return re.search(r"(?<![\w.-])" + re.escape(identificador) + depois, texto or "", flags) is not None


# --------------------------------------------------------------------------- 1. telas
def _texto_das_telas(corpo: str) -> Tuple[str, str]:
    """O texto onde a tela tem de estar — §7 (stories) e §10 (inventário) — e de onde ele veio."""
    partes = [s for s in (secao_numerada(corpo, 7, r"user stor", r"hist[óo]rias"),
                          secao_numerada(corpo, 10, r"\bUX\b", r"\btelas\b")) if s]
    if partes:
        return "\n".join(partes), "as stories (§7) e o inventário de telas (§10)"
    return corpo, "o PRD (sem §7 nem §10 numerados)"


def conferir_telas(corpo: str, jornada: str) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    inv = telas.inventario(jornada or "")
    esperadas = [t["id"] for t in inv["telas"]]
    if not esperadas:
        return [], {"telas_inventario": 0}
    alvo, onde = _texto_das_telas(corpo)
    citadas = ids_de_tela(alvo)
    faltam = [t for t in esperadas if t not in citadas]
    contagem = {"telas_inventario": len(esperadas), "telas_no_prd": len(esperadas) - len(faltam)}
    if not faltam:
        return [], contagem
    return [{
        "severidade": "bloqueio", "codigo": "tela-sem-story", "etapa": "dev", "agente_responsavel": DONO,
        "resumo": (f"{len(faltam)} de {len(esperadas)} tela(s) do inventário da jornada fora de {onde}: "
                   f"{_lista(faltam, 25)}. Toda tela tem story (§7) — uma por tela, ou um intervalo explícito como "
                   "`E0-PROF-01..05` — e linha no inventário consolidado (§10), com o mesmo ID da jornada."),
    }], contagem


# --------------------------------------------------------------------------- 2. chaves da copy
_RE_CHAVE = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z0-9_]+){2,}$")
#: A convenção escrita como exemplo (`eN.tipo.nome`, `sys.tipo.nome`) não é chave.
_RE_CHAVE_EXEMPLO = re.compile(r"\.tipo\.nome$|^en\.")
_RE_TOKEN_CODIGO = re.compile(r"`([^`\n]+)`")
_RE_CURINGA = re.compile(r"`?\b([a-z][a-z0-9]*(?:\.[a-z0-9_]+)*\.[a-z0-9_]*\*)`?")


def _limpa_chave(celula: str) -> str:
    return (celula or "").strip().strip("`*_ ").strip()


def chaves_da_copy(copy_revisada: str) -> List[str]:
    """As chaves da copy revisada, na ordem do sheet, lidas da coluna `Chave` de toda tabela.

    Só a coluna: nas sete sessões ela tinha todas as chaves que o arquivo cita, e uma chave citada fora
    dela pode ser a antiga de uma renomeação («renomeada de `e1.rotulo.x`»). Copy sem a coluna — nenhuma
    das sete, mas o formato pode mudar — cai nos tokens em código no formato da convenção
    (`eN.tipo.nome`, `sys.tipo.nome`, `global.tipo.nome`).
    """
    chaves: List[str] = []
    tem_coluna = False
    for cab, linhas in tabelas(copy_revisada):
        col = _coluna(cab, "chave")
        if not col:
            continue
        tem_coluna = True
        for linha in linhas:
            c = _limpa_chave(linha.get(col, ""))
            if _RE_CHAVE.match(c) and not _RE_CHAVE_EXEMPLO.search(c) and c not in chaves:
                chaves.append(c)
    if not tem_coluna:
        for token in _RE_TOKEN_CODIGO.findall(copy_revisada or ""):
            c = token.strip()
            if (_RE_CHAVE.match(c) and re.match(r"(?:e\d|sys|global)\.", c) and not _RE_CHAVE_EXEMPLO.search(c)
                    and c not in chaves):
                chaves.append(c)
    return chaves


def _curingas(texto: str) -> List["re.Pattern[str]"]:
    """`e0.rotulo.*`, `e5.rotulo.bloco_*` → expressões que casam as chaves do grupo."""
    saida = []
    for c in dict.fromkeys(_RE_CURINGA.findall(texto or "")):
        saida.append(re.compile("^" + re.escape(c).replace(r"\*", r"[a-z0-9_.]*") + "$"))
    return saida


def chaves_por_tela(copy_revisada: str) -> Dict[str, Set[str]]:
    """Chave → as telas do inventário que a copy revisada dá a ela (coluna `ID tela`, lida pelo nome).

    Chave sem tela de inventário — `Global` (exp07ef1b, exp09ef1b), `ST_OFFLINE` (exp06ef1b), `ERRO_SEM_SINAL`
    (exp01ef1b) — tem o conjunto vazio: é da missão inteira, não da story de uma tela.
    """
    mapa: Dict[str, Set[str]] = {}
    for cab, linhas in tabelas(copy_revisada):
        col = _coluna(cab, "chave")
        if not col:
            continue
        col_tela = _coluna(cab, "id tela", "tela")
        for linha in linhas:
            c = _limpa_chave(linha.get(col, ""))
            if _RE_CHAVE.match(c) and not _RE_CHAVE_EXEMPLO.search(c):
                ids = {i for i in ids_de_tela(linha.get(col_tela, "")) if telas.RE_ID.fullmatch(i)} if col_tela else set()
                mapa.setdefault(c, set()).update(ids)
    return mapa


_RE_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+")
#: A linha da story que diz a tela quando o título não diz: «- *Tela:* `E0-PROF-03`», «**Telas:** …».
_RE_LINHA_DE_TELA = re.compile(r"^\W*telas?\b", re.I)


def blocos_de_story(s7: str) -> List[Tuple[Set[str], str]]:
    """As stories da §7, cada uma com as telas que ela declara: (telas, texto da story).

    A story é o bloco que começa num título do nível em que os títulos trazem tela ou `US-` (`### US-001
    (Tela `E0-PROF-01` — …)`, exp09ef1b) — título mais raso também corta (o grupo «## 7.1 Estudante») e o
    mais fundo fica dentro («#### Copy»). Sem título, cada item de lista do nível mais raso é uma story
    (`- **US-03 — Investigação (`E1-ALU-01`, `E2-ALU-01`):**`, exp01ef1b). As telas são as do título ou do
    item, com intervalo expandido (`E0-PROF-01..05`); sem tela ali, as da linha «Tela:»; sem ela, as do bloco.
    """
    linhas = _linhas(s7 or "")
    titulos = [(i, len(m.group(1)), m.group(2)) for i, (_, l, cerca) in enumerate(linhas)
               if not cerca for m in [_RE_TITULO.match(l)] if m]
    if titulos:
        com_id: Dict[int, int] = {}
        for _, nivel, t in titulos:
            com_id[nivel] = com_id.get(nivel, 0) + bool(ids_de_tela(t) or re.search(r"\bUS-?\d", t))
        nivel_story = max(com_id, key=lambda n: (com_id[n], -n))
        inicios = [i for i, nivel, _ in titulos if nivel <= nivel_story]
    else:
        itens = [(i, len(m.group(1))) for i, (_, l, cerca) in enumerate(linhas) if not cerca
                 for m in [_RE_ITEM.match(l)] if m]
        raso = min((n for _, n in itens), default=0)
        inicios = [i for i, n in itens if n == raso]
    blocos: List[Tuple[Set[str], str]] = []
    for k, i in enumerate(inicios):
        fim = inicios[k + 1] if k + 1 < len(inicios) else len(linhas)
        texto = "\n".join(l for _, l, _ in linhas[i:fim])
        ids = ids_de_tela(linhas[i][1])
        if not ids:
            ids = set().union(*[ids_de_tela(l) for _, l, _ in linhas[i:fim] if _RE_LINHA_DE_TELA.match(l)] or [set()])
        blocos.append((ids or ids_de_tela(texto), texto))
    return blocos


#: Onde a chave vive, no vocabulário do gabarito (§7): o bundle de textos da experiência (`src/lib/textos.ts`), a
#: ficha de evidência no servidor (enunciado e alternativas do Canal B), o catálogo ou o guia do hub, o aria-label.
_RE_ONDE_VIVE = re.compile(r"bundle|textos(?:\.ts)?\b|ficha|servidor|cat[aá]logo|guia|\bhub\b|aria", re.I)


def _onde_vive(texto: str) -> Dict[str, str]:
    """Chave → célula «Onde vive» das tabelas que têm as colunas «Chave» e «Onde vive» (pelo nome).

    Uma célula pode trazer mais de uma chave; com a chave em duas linhas, vale a que diz onde ela vive.
    """
    saida: Dict[str, str] = {}
    for cab, linhas in tabelas(texto):
        col, onde = _coluna(cab, "chave"), _coluna(cab, "onde vive", "onde mora", "vive em")
        if not (col and onde):
            continue
        for linha in linhas:
            valor = linha.get(onde, "").strip()
            for token in _RE_TOKEN_CODIGO.findall(linha.get(col, "")) or [_limpa_chave(linha.get(col, ""))]:
                c = token.strip()
                if _RE_CHAVE.match(c) and (c not in saida or not _RE_ONDE_VIVE.search(saida[c])):
                    saida[c] = valor
    return saida


def _por_tela(chaves: Sequence[str], mapa: Dict[str, Set[str]]) -> str:
    """A lista inteira, agrupada pela tela da copy: «`E0-PROF-02`: `a`, `b`; sem tela: `sys.x`»."""
    grupos: Dict[str, List[str]] = {}
    for c in chaves:
        grupos.setdefault(min(mapa.get(c) or {"sem tela"}), []).append(c)
    ordem = sorted(grupos, key=lambda t: (t == "sem tela", t))
    return "; ".join(f"{'sem tela' if t == 'sem tela' else f'`{t}`'}: " + ", ".join(f"`{c}`" for c in grupos[t])
                     for t in ordem)


def conferir_chaves(corpo: str, copy_revisada: str) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """Toda chave da copy revisada, pelo nome, na story da tela dela (§7), com a coluna «Onde vive» preenchida.

    Decisão do PO de 07/10/2026 («o padrão ouro e o que for melhor para o PRD como insumo para codificação»):
    curinga não cobre e não há teto. Antes, `e2.rotulo.*` contava como citada e até 10% de chaves faltando era
    ressalva; medido nas sete sessões, a exp06ef1b citava pelo nome 11 das 103 chaves e 90 por curinga, a
    exp04ef1b 5 das 84 e 77 por curinga — e o curinga não diz a quem codifica qual chave vai em qual elemento
    da tela, nem em que arquivo ela entra. A exp09ef1b, a mais completa, tinha 100 das 104 na story da tela, e
    nenhuma das sete dizia onde a chave vive. A chave sem tela (`Global`, estado de erro) vale citada em
    qualquer lugar do corpo, e também com «Onde vive». A lista das faltantes vai inteira no resumo: é dela que o
    redator precisa para corrigir na rodada seguinte.
    """
    chaves = chaves_da_copy(copy_revisada)
    if not chaves:
        return [], {"chaves_copy": 0}
    mapa = chaves_por_tela(copy_revisada)
    s7 = secao_numerada(corpo, 7, r"user stor", r"hist[óo]rias")
    blocos = [(ids, texto, _onde_vive(texto)) for ids, texto in blocos_de_story(s7 or "")]
    onde_no_corpo = _onde_vive(corpo)
    curingas = _curingas(corpo)
    faltam: List[str] = []
    sem_onde: List[str] = []
    fora_do_vocabulario: List[str] = []
    for c in chaves:
        telas_da_chave = mapa.get(c, set())
        if telas_da_chave:
            da_tela = [b for b in blocos if b[0] & telas_da_chave]
            na_story = any(_presente(c, texto) for _, texto, _ in da_tela)
            onde = next((o[c] for _, _, o in da_tela if _RE_ONDE_VIVE.search(o.get(c, ""))), None) \
                or next((o[c] for _, _, o in da_tela if c in o), "")
        else:
            na_story, onde = _presente(c, corpo), onde_no_corpo.get(c, "")
        if not na_story:
            faltam.append(c)
        elif not _RE_ONDE_VIVE.search(onde):
            sem_onde.append(c)
            if onde.strip(" —–-?"):
                fora_do_vocabulario.append(f"`{c}` → «{onde[:40]}»")
    literais = [c for c in chaves if _presente(c, corpo)]
    por_curinga = [c for c in faltam if c not in literais and any(p.match(c) for p in curingas)]
    contagem = {"chaves_copy": len(chaves), "chaves_na_story": len(chaves) - len(faltam),
                "chaves_com_onde_vive": len(chaves) - len(faltam) - len(sem_onde), "chaves_no_prd": len(literais),
                "chaves_por_curinga": len(por_curinga)}
    achados: List[Dict[str, str]] = []
    if faltam:
        fora_da_story = [c for c in faltam if c in literais]
        achados.append({
            "severidade": "bloqueio", "codigo": "chave-de-copy-ausente", "etapa": "dev", "agente_responsavel": DONO,
            "resumo": (f"{len(faltam)} de {len(chaves)} chave(s) da copy revisada não estão, pelo nome, na story da tela "
                       f"delas (§7)" + ("" if s7 is not None else " — o PRD não tem a §7 (User stories)") + ": "
                       + _por_tela(faltam, mapa) + "."
                       + (f" {len(por_curinga)} delas o PRD só cobre por curinga (`eN.tipo.*`), que não vale: o curinga "
                          "não diz qual chave vai em qual elemento da tela." if por_curinga else "")
                       + (f" {len(fora_da_story)} {'aparece' if len(fora_da_story) == 1 else 'aparecem'} no PRD, "
                          "mas fora da story da tela." if fora_da_story else "")
                       + " Cada story traz a tabela `| Chave | Onde vive |` com todas as chaves que a copy dá para a "
                       "tela; a chave sem tela (`Global`, estado de erro) entra na story ou no RF de modos de falha, na "
                       "mesma tabela. Sem a chave, quem codifica reescreve o texto — e a copy revisada se perde."),
        })
    if sem_onde:
        achados.append({
            "severidade": "bloqueio", "codigo": "chave-sem-onde-vive", "etapa": "dev", "agente_responsavel": DONO,
            "resumo": (f"{len(sem_onde)} chave(s) estão na story sem dizer onde vivem: {_por_tela(sem_onde, mapa)}. A "
                       "story traz a tabela `| Chave | Onde vive |`, e «Onde vive» é `bundle de textos` "
                       "(`src/lib/textos.ts` da experiência), `ficha de evidência no servidor` (enunciado e alternativas "
                       "do Canal B), `catálogo/guia do hub` (`catalogo.ts`, `guias/<expId>.ts`) ou `aria-label` — é o que "
                       "diz a quem codifica em que arquivo a chave entra."
                       + (f" Fora desse vocabulário: {', '.join(fora_do_vocabulario[:12])}." if fora_do_vocabulario
                          else "")),
        })
    return achados, contagem


# --------------------------------------------------------------------------- 3. assets do brief
_RE_ID_ASSET = re.compile(r"^[a-z][a-z0-9]*(?:[-_][a-z0-9]+)+$")
_RE_ASSET_FAIXA = re.compile(r"^(?P<pre>[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*?[-_])(?P<ini>\d{2,3})$")


def _ids_da_celula(celula: str) -> List[str]:
    """`` `pic-exp01ef1b-01` `` → um ID; `` `img-exp06ef1b-01` a `16` `` → dezesseis."""
    tokens = [t.strip() for t in _RE_TOKEN_CODIGO.findall(celula or "")] or [_limpa_chave(celula)]
    ids = [t for t in tokens if _RE_ID_ASSET.match(t)]
    m = _RE_ASSET_FAIXA.match(ids[0]) if len(ids) == 1 else None
    if m:
        # o que vem depois do ID na célula: « a `16`», «..16», «–`img-exp06ef1b-16`»
        resto = (celula or "").split(ids[0], 1)[-1]
        f = re.match(r"[`*]*" + _SEP + r"[`*]*(?:" + re.escape(m.group("pre")) + r")?(\d{2,3})\b", resto)
        if f:
            return [m.group("pre") + n for n in _faixa(m.group("ini"), f.group(1))]
    return ids


def assets_v1(brief_assets: str) -> List[str]:
    """IDs V1 da tabela mestre do brief (colunas `ID` e `V1/V2`, lidas pelo nome).

    Sem coluna `V1/V2`, toda linha da tabela com `ID`, `Tipo` e `Destino` conta — o brief antigo não
    separava as versões. Intervalo na célula (`img-exp06ef1b-01` a `16`) é expandido.
    """
    saida: List[str] = []
    candidatas = []
    for cab, linhas in tabelas(brief_assets):
        col_id = "id" if "id" in cab else None
        if not col_id:
            continue
        col_v = _coluna(cab, "v1")
        if col_v:
            candidatas.append((col_id, col_v, linhas))
        elif _coluna(cab, "tipo") and (_coluna(cab, "destino") or _coluna(cab, "peso")):
            candidatas.append((col_id, None, linhas))
    if any(v for _, v, _ in candidatas):
        candidatas = [c for c in candidatas if c[1]]
    for col_id, col_v, linhas in candidatas:
        for linha in linhas:
            if col_v and not re.search(r"\bV1\b", linha.get(col_v, ""), re.I):
                continue
            for i in _ids_da_celula(linha.get(col_id, "")):
                if i not in saida:
                    saida.append(i)
    return saida


def _assets_no_texto(texto: str, ids: Sequence[str]) -> Set[str]:
    prefixos = {m.group("pre") for i in ids for m in [_RE_ASSET_FAIXA.match(i)] if m}
    expandidos: Set[str] = set()
    for p in prefixos:
        expandidos |= _expandir_faixas(texto, re.escape(p))
    return {i for i in ids if i in expandidos or _presente(i, texto, arquivo=True)}


def conferir_assets(corpo: str, brief_assets: str) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    ids = assets_v1(brief_assets)
    if not ids:
        return [], {"assets_v1": 0}
    presentes = _assets_no_texto(corpo, ids)
    faltam = [i for i in ids if i not in presentes]
    contagem = {"assets_v1": len(ids), "assets_no_prd": len(presentes)}
    if not faltam:
        return [], contagem
    return [{
        "severidade": "bloqueio", "codigo": "asset-fora-do-inventario", "etapa": "dev", "agente_responsavel": DONO,
        "resumo": (f"{len(faltam)} de {len(ids)} asset(s) V1 do brief não aparecem no PRD: {_lista(faltam)}. O "
                   "inventário de conteúdo do PRD (§10 ou §17) nomeia cada asset pelo ID do brief, com a tela, o peso e "
                   "o destino (bundle ou bucket `-assets`) — sem isso quem codifica inventa o caminho do arquivo."),
    }], contagem


# --------------------------------------------------------------------------- 4. estados da spec
_RE_TITULO_CONTRATO = re.compile(r"contrato\s+de\s+estados", re.I)
_RE_ESTADO = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b")
#: Um campo da linha de transição que é só um identificador snake_case: o estado inicial ou o seguinte.
_RE_ESTADO_CAMPO = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+$")
#: Na célula da coluna «Estado …» o nome pode não ter sublinhado: `CONCLUIDO` (exp02em1b).
_RE_ESTADO_CELULA = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)*$")
#: Os separadores de campo que as specs usam: `·` (exp04, exp09), `→` (exp01), `-- … -->` e `|` (exp06).
_RE_SEPARA_CAMPO = re.compile(r"\s*(?:·|→|⟶|-->|->|--|=>|\|)\s*")
#: Rótulo antes do estado: «Estado seguinte: `E1_AGUARDANDO_PROMPT`», «ESTADO INICIAL: e1_desafio_aberto». Só
#: rótulo de estado: `tap:lupa_zoomout` é gatilho, e o `tap:` não pode ser tirado como se fosse rótulo.
_RE_ROTULO_CAMPO = re.compile(r"^(?:(?:estado(?:\s+\w+)?|pr[óo]ximo\s+estado|destino|origem)\s*:\s*)", re.I)
#: Curingas do contrato, não estados: «QUALQUER_ESTADO → erro», «QUALQUER_ESTADO_FEED», «→ ESTADO_ANTERIOR»,
#: «[estado_salvo]», «`*` (qualquer)».
_RE_NAO_ESTADO = re.compile(r"^(?:qualquer_estado\w*|estado_(?:anterior|inicial|seguinte|origem|de_origem|atual|salvo)\w*)$",
                            re.I)


def _estados_dos_campos(linha: str) -> List[str]:
    """Estados de uma linha de transição: os em caixa alta onde estiverem, e os em caixa baixa quando ocupam
    um campo inteiro (`e1_desafio_aberto · toque · slot_count == 3 · e2_mesa_livre · …`, exp04ef1b).

    Variável de regra (`slot_count == 3`) e gatilho (`tap:album`) não são um identificador sozinho no campo.
    """
    saida = list(_RE_ESTADO.findall(linha))
    sem_marcador = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", linha)
    campos = _RE_SEPARA_CAMPO.split(sem_marcador)
    # Na linha `estado inicial · gatilho · regra · estado seguinte · …` do formato da spec, o estado em caixa baixa só
    # está no 1º e no 4º campo: o gatilho `confirmar_voto` também é snake_case e entrava como estado — a exp06ef1b
    # (09/10/2026) contou 29 «estados», 15 deles gatilhos, e o fluxo saía 🟡 com 17 «perdidos».
    if sem_marcador.count("·") >= 3 and len(campos) >= 4:
        campos = [campos[0], campos[3]]
    for campo in campos:
        c = _RE_ROTULO_CAMPO.sub("", campo.strip().strip(" `*[]")).strip(" `*[]_.")
        if _RE_ESTADO_CAMPO.match(c):
            saida.append(c)
    return saida


def _e_transicao(linha: str) -> bool:
    """Linha do contrato, não prosa: dois separadores de campo, ou o rótulo «Estado seguinte»."""
    return (len(re.findall(r"·|→|⟶|-->|->|=>", linha)) >= 2 or bool(re.search(r"estado\s+seguinte\s*:", linha, re.I))
            or (linha.count("|") >= 2 and bool(re.search(r"-->|->|→", linha))))


def estados_da_spec(spec: str) -> List[str]:
    """Os estados com nome próprio do «Contrato de estados» (bloco 2), na ordem em que aparecem.

    Com tabela (exp02em1b, exp05, exp07), lidos das colunas cujo nome começa por «Estado» — inicial e
    seguinte. Sem tabela, das linhas de transição (cerca com `→`, lista com `·`, `-- … -->`). A prosa de
    baixo do contrato fica de fora: «a confirmação (`ESTADO_3` para `ESTADO_4`)» abrevia estados, não os declara.
    """
    contrato = _secao_por_titulo(spec or "", _RE_TITULO_CONTRATO)
    if not contrato:
        return []
    nomes: List[str] = []
    com_tabela = False
    for cab, linhas in tabelas(contrato):
        colunas = [c for c in cab if c.startswith("estado")]
        if not colunas:
            continue
        com_tabela = True
        for linha in linhas:
            for col in colunas:
                celula = linha.get(col, "")
                em_codigo = [t.strip("*_ ") for t in _RE_TOKEN_CODIGO.findall(celula)][:1]
                # sem crase, só o que tem cara de identificador: `CONCLUIDO` sim, «Estado anterior» não
                solto = [t for t in celula.strip("*_ ").split()[:1] if "_" in t or re.fullmatch(r"[A-Z][A-Z0-9]+", t)]
                nomes += [t for t in (em_codigo or solto) if _RE_ESTADO_CELULA.match(t)]
    if not com_tabela:
        for linha in contrato.splitlines():
            if _e_transicao(linha):
                nomes += _estados_dos_campos(linha)
    saida: List[str] = []
    vistos: Set[str] = set()
    for nome in nomes:
        chave = nome.lower()
        if _RE_NAO_ESTADO.match(nome) or telas.RE_ID.fullmatch(nome.upper()) or chave in vistos:
            continue
        vistos.add(chave)
        saida.append(nome)
    return saida


def conferir_estados(corpo: str, spec: str) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """Medido nas sete sessões, o mapa existe ou não existe: exp09 18/18, exp05 12/12, exp02em1b 14/14, exp04
    20/21 e exp07 10/11 levaram o contrato para a §6; a exp01 (0/17) trocou os estados por IDs de tela e a
    exp06 (1/11) por IDs de tela e estados `ST_*` que a spec não tem. A falta pontual (um de 21) é ⚠️ — o humano vê e
    decide; mais da metade faltando é ⛔: a máquina de estados do PRD não é a da spec, e o enum que quem
    codifica escreve também não. O nome é conferido sem caixa (`e3_voto_lacrado` no CHECK vale)."""
    estados = estados_da_spec(spec)
    if not estados:
        return [], {"estados_spec": 0}
    faltam = [e for e in estados if not _presente(e, corpo, ignorar_caixa=True)]
    contagem = {"estados_spec": len(estados), "estados_no_prd": len(estados) - len(faltam)}
    if not faltam:
        return [], contagem
    fracao = len(faltam) / len(estados)
    severidade = "bloqueio" if fracao > TETO_ESTADOS_AUSENTES else "atencao"
    return [{
        "severidade": severidade, "codigo": "estado-da-spec-sem-mapa", "etapa": "dev", "agente_responsavel": DONO,
        "resumo": (f"{len(faltam)} de {len(estados)} estado(s) do «Contrato de estados» da spec (bloco 2) não aparecem "
                   f"no PRD: {_lista(faltam)}. A §6 do PRD tem os mesmos estados com o mesmo nome (eles viram o enum e o "
                   "CHECK da migration), cada um com a tela que o mostra; estado de falha e latch inclusive."
                   + (" Com mais da metade fora, a máquina de estados do PRD não é a da spec." if severidade == "bloqueio"
                      else "")),
    }], contagem


# --------------------------------------------------------------------------- 5. status de gate
_STATUS = "🟢🟡🔴"
_RE_ROTULO_STATUS = re.compile(r"status\s+d[eo]s?\s+gates?", re.I)
_RE_GATE_COM_STATUS = re.compile(
    r"\b(?:gates?|estrutural|final(?:\s+de\s+produto)?|bncc|lacunas(?:\s+d0)?|ambiente(?:\s+simulado)?|design|"
    r"manifesto|telemetria|rastro|banca|pedag[óo]gic\w*|experi[êe]ncia|qa|dev|entreg[áa]veis|adequa[çc][ãa]o|"
    r"consist[êe]ncia|kpis?|evid[êe]ncia)\b[^:\n|]{0,60}:\s*(?:\*\*|\*|_)?\s*[" + _STATUS + "]",
    re.I,
)
_RE_PALAVRA_STATUS = re.compile(r"[" + _STATUS + r"]|\b(?:aprovad|reprovad|bloquead|conforme|apto)\w*", re.I)


def linhas_de_status_de_gate(prd: str) -> List[Tuple[int, str]]:
    """(número, linha) de cada status de gate que o redator escreveu — frontmatter incluído, anexo não.

    Três formas, todas vistas nas sete sessões: a seção `### Status dos gates` com uma linha por gate
    (exp01, exp04, exp06, exp07), o rótulo `**Status dos gates:** Estrutural 🟢, BNCC 🟢…` (exp09, exp02em1b)
    e o bloco `gates:` no frontmatter (exp05, exp07, exp02em1b). Legenda (`🟢 = conforme`) e a cor de
    severidade numa tabela de pendências não são status de gate: a primeira é pulada pela palavra
    «legenda», a segunda não tem o nome do gate seguido de dois-pontos na mesma célula.
    """
    saida: List[Tuple[int, str]] = []
    secao_status = 0  # nível do título «Status dos gates» aberto; 0 = fora
    for n, linha, cerca in _linhas(corpo_do_prd(prd)):
        if cerca or re.search(r"legenda", linha, re.I):
            continue
        m = _RE_TITULO.match(linha)
        if m:
            nivel = len(m.group(1))
            if secao_status and nivel <= secao_status:
                secao_status = 0
            if _RE_ROTULO_STATUS.search(m.group(2)):
                secao_status = nivel
                continue
        tem_cor = any(c in linha for c in _STATUS)
        if ((tem_cor and (_RE_GATE_COM_STATUS.search(linha) or _RE_ROTULO_STATUS.search(linha)))
                or (secao_status and _RE_PALAVRA_STATUS.search(linha))
                or (_RE_ROTULO_STATUS.search(linha) and _RE_PALAVRA_STATUS.search(linha))):
            saida.append((n, re.sub(r"\s+", " ", linha).strip()))
    return saida


def conferir_status_de_gate(prd: str) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    linhas = linhas_de_status_de_gate(prd)
    contagem = {"linhas_status_gate": len(linhas)}
    if not linhas:
        return [], contagem
    exemplos = "; ".join(f"l. {n}: «{l[:110]}»" for n, l in linhas[:4])
    return [{
        "severidade": "bloqueio", "codigo": "status-de-gate-no-corpo", "etapa": "dev", "agente_responsavel": DONO,
        "resumo": (f"O PRD escreve status de gate em {len(linhas)} linha(s) — {exemplos}. Tire a seção e as linhas, "
                   "inclusive o bloco `gates:` do frontmatter: o status é da esteira, que o publica no dossiê da execução. "
                   "Na exp01ef1b o redator escreveu «Telemetria e Arquitetura: 🟢 Conforme» com o gate 🔴."),
    }], contagem


# --------------------------------------------------------------------------- 6. RF P0 com critério
_RE_RF = re.compile(r"\bRF-\d{2,3}\b")
#: EARS com o gatilho em caixa alta, como o gabarito escreve (`QUANDO … O SISTEMA DEVE …`, `SE … ENTÃO …`).
#: A descrição em prosa («O sistema deve permitir…», «Ao confirmar…, o sistema deve…») não é critério.
_RE_EARS = re.compile(
    r"\b(?:QUANDO|ENQUANTO|ONDE|SE|DADO|WHEN|WHILE|WHERE|IF|GIVEN)\b[^\n]*?\b(?:DEVE|DEVER[ÁA]|ENT[ÃA]O|SHALL|THEN)\b")
_RE_GHERKIN = re.compile(r"\b(?:Dado|DADO|Given)\b.*?\b(?:Quando|QUANDO|When)\b.*?\b(?:Então|ENTÃO|Then)\b", re.S)


def _tem_criterio(texto: str) -> bool:
    plano = re.sub(r"[*_`]", "", texto or "")
    return bool(_RE_EARS.search(plano) or _RE_GHERKIN.search(plano))


def _indentacao(linha: str) -> int:
    return len(linha) - len(linha.lstrip(" \t"))


def _blocos_que_citam(corpo: str) -> Dict[str, List[str]]:
    """RF → textos fora de tabela que o citam com o que vem pendurado embaixo (o bloco EARS da exp01ef1b:
    `- **EARS-01 (… RF-008):**` e as linhas recuadas com `QUANDO … O SISTEMA DEVE …`).

    O bloco vai até a próxima linha de recuo igual ou menor que comece outro item, até um título ou até
    uma linha em branco seguida de texto no mesmo recuo. Cerca de código é atravessada inteira (o Gherkin
    vem em ```gherkin logo abaixo do RF); RF citado dentro de uma cerca leva o resto dela. Linha de tabela
    não pendura nada: é ela só.
    """
    linhas = _linhas(corpo)
    blocos: Dict[str, List[str]] = {}
    for i, (_, linha, cerca) in enumerate(linhas):
        rfs = _RE_RF.findall(linha)
        if not rfs:
            continue
        trecho = [linha]
        if not linha.lstrip().startswith("|"):
            base = _indentacao(linha)
            dentro = cerca  # o RF está numa cerca: o bloco vai até ela fechar
            for _, seguinte, _ in linhas[i + 1:i + 30]:
                s = seguinte.strip()
                if _RE_CERCA.match(seguinte):
                    trecho.append(seguinte)
                    if dentro:
                        break
                    dentro = True
                    continue
                if dentro:
                    trecho.append(seguinte)
                    continue
                if _RE_TITULO.match(seguinte) or s.startswith("|"):
                    break
                if not s:
                    trecho.append(seguinte)
                    continue
                if _indentacao(seguinte) <= base and (re.match(r"([-*+]|\d+[.)])\s", s) or not trecho[-1].strip()):
                    break
                trecho.append(seguinte)
        for rf in rfs:
            blocos.setdefault(rf, []).append("\n".join(trecho))
    return blocos


def requisitos_p0(corpo: str) -> List[Tuple[str, str]]:
    """(RF, linha inteira da tabela) de cada requisito P0, das tabelas com coluna `Prioridade`."""
    saida: List[Tuple[str, str]] = []
    vistos: Set[str] = set()
    for cab, linhas in tabelas(corpo):
        col_p = _coluna(cab, "prioridade", "pri")  # a exp07ef1b abrevia: «Pri.»
        if not col_p:
            continue
        col_id = _coluna(cab, "id", "rf", "requisito", "codigo")
        for linha in linhas:
            if not re.search(r"\bP0\b", linha.get(col_p, "")):
                continue
            fonte = linha.get(col_id, "") if col_id else " ".join(linha.values())
            m = _RE_RF.search(fonte) or _RE_RF.search(" ".join(linha.values()))
            if m and m.group(0) not in vistos:
                vistos.add(m.group(0))
                saida.append((m.group(0), " | ".join(linha.values())))
    return saida


def conferir_rf_p0(corpo: str) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """Medido nas sete sessões: a exp06 e a exp09 têm a coluna «Critério de aceite (EARS / Gherkin)» e passam
    inteiras; a exp01 deixou 12 de 17 P0 só com a descrição em prosa. Bloqueio: o gabarito exige EARS em
    todo P0 («Todo RF P0 deve ter pelo menos um critério EARS»), e sem critério o teste não tem o que provar."""
    p0 = requisitos_p0(corpo)
    if not p0:
        return [], {"rf_p0": 0}
    blocos = _blocos_que_citam(corpo)
    sem = [rf for rf, linha in p0 if not _tem_criterio(linha) and not any(_tem_criterio(b) for b in blocos.get(rf, []))]
    contagem = {"rf_p0": len(p0), "rf_p0_com_criterio": len(p0) - len(sem)}
    if not sem:
        return [], contagem
    return [{
        "severidade": "bloqueio", "codigo": "rf-p0-sem-criterio", "etapa": "dev", "agente_responsavel": DONO,
        "resumo": (f"{len(sem)} de {len(p0)} requisito(s) P0 sem critério de aceite EARS nem Gherkin: {_lista(sem, 20)}. "
                   "Escreva o critério na coluna «Critério de aceite (EARS / Gherkin)» da tabela da §8 — `QUANDO <gatilho>, "
                   "O SISTEMA DEVE <resposta>`, `SE <falha>, ENTÃO …`, ou `Dado / Quando / Então`. A descrição «O sistema "
                   "deve permitir…» é a necessidade, não o critério: o teste não tem o que provar."),
    }], contagem


# --------------------------------------------------------------------------- 7. schemas definidos
_RE_SCHEMA = re.compile(r"\b[A-Z][A-Za-z0-9]*(?:Schema|Dto|DTO)\b")
_NAO_SCHEMA = frozenset({"JSONSchema", "JsonSchema", "ZodSchema", "OpenApiSchema", "OpenAPISchema"})
#: O PRD diz de onde o nome vem: pacote da plataforma ou import. Não é definição a cobrar.
_RE_IMPORTADO = re.compile(r"@unooria/|@edu/|\bimport\b|\bfrom\s+['\"]|\bpackages/", re.I)
#: O PRD o trata como existente, sem dizer de onde: na dúvida, ⚠️.
_RE_EXISTENTE = re.compile(r"\bexistente|\bj[áa]\s+existe|\bda\s+plataforma\b|\breus[ao]|\breutiliz|\breaproveit", re.I)
_RE_CAMPO_TABELA = re.compile(r"\b(?:campo|field|propriedade|atributo)\b", re.I)


def _definido(nome: str, corpo: str) -> bool:
    n = re.escape(nome)
    if re.search(rf"\b(?:const|let|var)\s+{n}\s*(?::[^=\n]+)?=|\b(?:type|interface|class|enum)\s+{n}\b"
                 rf"|\b{n}\s*:\s*z\.|\b{n}\s*=\s*z\.|\b{n}`?\s*(?:=\s*)?\{{\s*['\"]?\w+['\"]?\??\s*:", corpo):
        return True
    # tabela de campos logo depois do nome (título ou linha que o apresenta)
    linhas = corpo.splitlines()
    for i, linha in enumerate(linhas):
        if not re.search(rf"\b{n}\b", linha) or linha.lstrip().startswith("|"):
            continue
        for seguinte in [l for l in linhas[i + 1:i + 6] if l.strip()][:3]:
            if seguinte.lstrip().startswith("|"):
                cab = [_norm(c) for c in _celulas(seguinte)]
                if any(_RE_CAMPO_TABELA.search(c) for c in cab) and any(c.startswith(("tipo", "type")) for c in cab):
                    return True
                break
    return False


def _campos_em_prosa(nome: str, corpo: str) -> bool:
    """O nome seguido da lista do que ele carrega, sem tipo — entre parênteses ou depois de dois-pontos:

    - `ParametrosPreparoExp09Schema` (disciplina, tema, assuntos, contexto?, foco?) — exp09ef1b;
    - validado por `PacoteSimulacaoChatGPTSchema`: Perspectiva A, Perspectiva B, palavras de indução — exp02em1b;
    - `PacoteConteudoTurmaSchema` (16 estandes completos e 4 categorias) — exp06ef1b.

    Um comentário só não é lista: «`PacoteConteudoExp09Schema` (com edições manuais se houver)».
    """
    n = re.escape(nome)
    for m in re.finditer(rf"\b{n}\b`?\s*(?:\(([^)\n]{{3,200}})\)|:\s*(?!\s*z\.)([^\n]{{3,200}}))", corpo):
        lista = m.group(1) or m.group(2) or ""
        if len([p for p in re.split(r",|;|\s+e\s+", lista) if p.strip()]) >= 2:
            return True
    return False


def conferir_schemas(corpo: str, spec: str = "") -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """Medido nas sete sessões. Definido (`const X = z.object`, `type`, `interface`, `X { campo: tipo }` ou
    tabela de campos): nada. Importado de pacote: nada. Tratado como existente sem dizer de onde, ou com os
    campos listados em prosa sem tipo: ⚠️ — o dev sabe o que vai no contrato, mas não o tipo. Só o nome,
    sem definição em lugar nenhum do PRD: ⛔ — é o corpo de uma rota que ninguém escreveu (a exp01ef1b com
    `ParametrosDoPreparoExp01ef1bSchema`, a exp09ef1b com `EstadoSessaoDto`). Quando a spec o define, o
    resumo diz para copiar de lá."""
    citados = [n for n in dict.fromkeys(_RE_SCHEMA.findall(corpo or "")) if n not in _NAO_SCHEMA]
    contagem = {"schemas_citados": len(citados)}
    if not citados:
        return [], contagem
    sem_def: List[str] = []
    em_prosa: List[str] = []
    for nome in citados:
        if _definido(nome, corpo):
            continue
        linhas = [l for l in corpo.splitlines() if re.search(rf"\b{re.escape(nome)}\b", l)]
        if any(_RE_IMPORTADO.search(l) for l in linhas):
            continue
        if any(_RE_EXISTENTE.search(l) for l in linhas) or _campos_em_prosa(nome, corpo):
            em_prosa.append(nome)
        else:
            sem_def.append(nome)
    contagem["schemas_definidos"] = len(citados) - len(sem_def) - len(em_prosa)
    achados: List[Dict[str, str]] = []
    if sem_def:
        na_spec = [n for n in sem_def if _definido(n, spec or "")]
        achados.append({
            "severidade": "bloqueio", "codigo": "schema-indefinido", "etapa": "dev", "agente_responsavel": DONO,
            "resumo": (f"{_lista(sem_def)} {'é citado' if len(sem_def) == 1 else 'são citados'} no PRD sem definição: "
                       "nenhum `const … = z.object(…)`, `type`/`interface` nem tabela de campos com tipo. É o contrato de "
                       "entrada ou resposta de uma rota (`@Contrato`): escreva o Zod na §12, junto da rota."
                       + (f" A spec define {_lista(na_spec)} — copie de lá." if na_spec else "")),
        })
    if em_prosa:
        achados.append({
            "severidade": "atencao", "codigo": "schema-indefinido", "etapa": "dev", "agente_responsavel": DONO,
            "resumo": (f"{_lista(em_prosa)}: citado(s) com os campos em prosa, sem tipo, ou como já existente sem dizer "
                       "de onde se importa. Se é da plataforma, diga o pacote (`@unooria/…`); se é da missão, escreva o Zod."),
        })
    return achados, contagem


# --------------------------------------------------------------------------- 8. propostas da spec
_RE_PROPOSTA = re.compile(r"\[\s*PROPOSTA", re.I)
_PREFIXO_DECISAO = r"\b(?:PQ|KPI|D0)-"
_RE_ID_DECISAO = re.compile(_PREFIXO_DECISAO + r"\d{1,3}\b")
#: Seção onde o PO vai olhar o que falta decidir: «Questões abertas», «Pendências», «Decisões a revisar»,
#: «Propostas a validar». Não «Histórico de revisões» — o changelog não é lugar de decisão aberta.
_RE_SECAO_REVISAO = re.compile(
    r"a\s+revisar|para\s+revis[ãa]o|propostas?\s+(?:do\s+agente|a\s+validar|pendentes?)|quest[õo]es\s+abertas|"
    r"pend[êe]ncias|a\s+validar|em\s+aberto|a\s+decidir|validar\s+com\s+(?:o\s+)?PO", re.I)


def propostas_da_spec(spec: str) -> List[str]:
    """IDs (`PQ-nn`, `D0-n`, `KPI-nn`) das linhas da spec com `[PROPOSTA …]`; sem ID na linha, os do título
    da seção em que ela está (`### [D0-3] …` com a proposta no parágrafo de baixo)."""
    saida: List[str] = []
    titulo = ""
    for _, linha, cerca in _linhas(spec or ""):
        if not cerca and _RE_TITULO.match(linha):
            titulo = linha
        if not _RE_PROPOSTA.search(linha):
            continue
        ids = _RE_ID_DECISAO.findall(linha) or _RE_ID_DECISAO.findall(titulo)
        for i in ids:
            if i not in saida:
                saida.append(i)
    return saida


def conferir_propostas(corpo: str, spec: str) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    propostas = propostas_da_spec(spec)
    if not propostas:
        return [], {"propostas_spec": 0}
    ocorrencias: Dict[str, List[Tuple[str, str]]] = {p: [] for p in propostas}
    titulo = ""
    for _, linha, cerca in _linhas(corpo):
        m = _RE_TITULO.match(linha)
        if m and not cerca:
            titulo = m.group(2)
        citados = set(_RE_ID_DECISAO.findall(linha)) | _expandir_faixas(linha, _PREFIXO_DECISAO)
        for p in propostas:
            if p in citados:
                ocorrencias[p].append((linha, titulo))
    no_prd = [p for p in propostas if ocorrencias[p]]
    perdidas = [p for p in no_prd
                if not any(re.search(r"PROPOSTA", l, re.I) or _RE_SECAO_REVISAO.search(t) for l, t in ocorrencias[p])]
    contagem = {"propostas_spec": len(propostas), "propostas_no_prd": len(no_prd),
                "propostas_marcadas": len(no_prd) - len(perdidas)}
    if not perdidas:
        return [], contagem
    return [{
        "severidade": "atencao", "codigo": "proposta-perdida", "etapa": "dev", "agente_responsavel": DONO,
        "resumo": (f"{_lista(perdidas)} {'é proposta' if len(perdidas) == 1 else 'são propostas'} do agente na spec "
                   "(`[PROPOSTA — validar com PO]`) e chega(m) ao PRD sem o marcador — numa linha de KPI, de RF ou de "
                   "story, o PO lê como decidido. Mantenha `[PROPOSTA — validar com PO]` na linha que a usa, ou liste-a "
                   "nas questões abertas da §19."),
    }], contagem


# --------------------------------------------------------------------------- 9. eventos da spec
def _limpa_evento(celula: str) -> str:
    return re.sub(r"[`*]", "", celula or "").strip().lower()


def eventos_da_spec(spec: str) -> List[Tuple[str, str]]:
    """(verbo, objeto) de cada linha das tabelas de eventos da spec — colunas «Verbo» e «Objeto», pelo nome.

    O bloco 9 chama a tabela de jeitos diferentes («9.4 Tabela de eventos», «9.7 Eventos de telemetria»,
    «9e. Tabela de eventos da plataforma», «Contrato de eventos (`track`)»); as colunas são sempre as duas.
    Linha de molde (`<namespace:slug>`, `…`) não é evento.
    """
    pares: List[Tuple[str, str]] = []
    for cab, linhas in tabelas(spec or ""):
        col_v, col_o = _coluna(cab, "verbo"), _coluna(cab, "objeto")
        if not (col_v and col_o) or col_v == col_o:
            continue
        for linha in linhas:
            par = (_limpa_evento(linha.get(col_v, "")), _limpa_evento(linha.get(col_o, "")))
            if all(par) and not re.search(r"[<>…]|\.\.\.|^[—–-]$", "".join(par)) and par not in pares:
                pares.append(par)
    return pares


def _objeto_em(objeto: str, texto: str) -> bool:
    return re.search(r"(?<![\w:.-])" + re.escape(objeto) + r"(?![\w:-])", texto or "", re.I) is not None


def conferir_eventos(corpo: str, spec: str) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """Todo `verbo · objeto` da tabela de eventos da spec está na §13 do PRD, com o mesmo verbo e o mesmo objeto.

    Medido nas sete sessões: exp01 13/13, exp09 12/12, exp06 12/12 e exp04 9/9 levaram a tabela inteira; a
    exp07ef1b renomeou os sete objetos (`dm:amara_inicio` → `exp07ef1b:dm_amara_inicio`), a exp05ef1b trocou os
    seis verbos (`votar` → `scored`) e a exp02em1b fez as duas coisas nos cinco. ⚠️: o evento chega a quem
    codifica, mas com um nome que o painel de produto, os KPIs e a spec não conhecem.
    """
    pares = eventos_da_spec(spec)
    if not pares:
        return [], {"eventos_spec": 0}
    alvo = secao_numerada(corpo, 13, r"eventos", r"telemetria") or corpo
    no_prd: Set[Tuple[str, str]] = set()
    for cab, linhas in tabelas(alvo):
        col_v, col_o = _coluna(cab, "verbo"), _coluna(cab, "objeto")
        if col_v and col_o and col_v != col_o:
            no_prd.update((_limpa_evento(l.get(col_v, "")), _limpa_evento(l.get(col_o, ""))) for l in linhas)
    linhas_alvo = alvo.splitlines()

    def presente(verbo: str, objeto: str) -> bool:
        return (verbo, objeto) in no_prd or any(
            _objeto_em(objeto, l) and re.search(rf"\b{re.escape(verbo)}\b", l, re.I) for l in linhas_alvo)

    faltam = [p for p in pares if not presente(*p)]
    contagem = {"eventos_spec": len(pares), "eventos_no_prd": len(pares) - len(faltam)}
    if not faltam:
        return [], contagem
    outro_verbo = [p for p in faltam if _objeto_em(p[1], alvo)]
    descricao = "; ".join(f"`{v} {o}`" + (" (o objeto está lá, com outro verbo)" if (v, o) in outro_verbo else "")
                          for v, o in faltam)
    return [{
        "severidade": "atencao", "codigo": "evento-perdido", "etapa": "dev", "agente_responsavel": DONO,
        "resumo": (f"{len(faltam)} de {len(pares)} evento(s) da tabela de eventos da spec (bloco 9) não estão na §13 do "
                   f"PRD com o mesmo verbo e o mesmo objeto: {descricao}. Copie verbo e objeto da spec: o objeto é o id "
                   "estável que o painel de produto e os KPIs leem, e renomeá-lo (`dm:amara_inicio` → "
                   "`exp07ef1b:dm_amara_inicio`) ou trocar o verbo quebra a ligação com o que produto decidiu. Se a "
                   "troca é de propósito, a §13 traz o de-para e a §19 registra a divergência."),
    }], contagem


# --------------------------------------------------------------------------- 10. ausências da spec
_RE_TITULO_AUSENCIAS = re.compile(r"^(?:5\s*[.)—–-]?\s*)?aus[eê]ncias\s+declaradas", re.I)


def ausencias_da_spec(spec: str) -> List[str]:
    """As ausências declaradas do bloco 5 da spec: a coluna da ausência (pelo nome — «Ausência», «Ausência
    deliberada», «Recurso ausente», «Recurso do WhatsApp real»), ou o negrito de cada item da lista (exp09ef1b:
    «* **Sem edição de mensagens anteriores:** …»)."""
    secao = _secao_por_titulo(spec or "", _RE_TITULO_AUSENCIAS)
    if not secao:
        return []
    itens: List[str] = []
    for cab, linhas in tabelas(secao):
        col = _coluna(cab, "ausencia", "recurso")
        for linha in linhas if col else []:
            item = re.sub(r"[*_`]", "", linha.get(col, "")).strip()
            if item and item not in itens:
                itens.append(item)
    if not itens:
        for _, linha, cerca in _linhas(secao):
            m = None if cerca else re.match(r"^\s*(?:[-*+]|\d+[.)])\s+\*\*(.+?)\*\*", linha)
            if m and m.group(1).strip(" :") not in itens:
                itens.append(m.group(1).strip(" :"))
    return itens


def conferir_ausencias(corpo: str, spec: str) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
    """Toda ausência declarada da spec chega ao PRD — o que o ambiente real tem e a missão deliberadamente não.

    É o que impede quem codifica de construir a lixeira ou o «New Chat» que a mecânica proíbe. A ausência vale
    com outras palavras: está no PRD quando uma linha do corpo divide com ela pelo menos 60% dos radicais
    (`conferir_prd_plataforma.radicais`; dois, se ela tem até três). Medido nas sete sessões: das 37 ausências
    das specs, 19 estão no PRD por esse critério e 18 não; lidas uma a uma, 12 das 18 faltam mesmo (a exp09ef1b
    deixou o upload, a edição de mensagens, o «New Chat» e o modal de pontuação) e 6 estão com outras palavras
    («Upload de anexos e mídias» na exp02em1b, «barras de pesquisa» na exp07ef1b). Com 50% de radicais o
    critério ganhava uma e passava duas que não estavam; com 40%, mais. Por isso ⚠️, e o resumo pede a
    ausência com as palavras da spec — o que torna a correção literal, e a próxima conferência exata.
    """
    from tools.conferir_prd_plataforma import radicais

    itens = ausencias_da_spec(spec)
    if not itens:
        return [], {"ausencias_spec": 0}
    # identificador em código (`e0.rotulo.botao_regenerar`, `exp09ef1b_sessoes`) não é frase: o «botao» de uma chave
    # de copy cobria o «Sem botão "Regenerate response"» da exp09ef1b numa linha que só listava chaves
    linhas = [radicais(re.sub(r"`[^`\s]*[._:][^`\s]*`", " ", l)) for _, l, cerca in _linhas(corpo)
              if not cerca and l.strip()]
    faltam = []
    for item in itens:
        alvo = radicais(item)
        precisa = min(len(alvo), max(2, math.ceil(0.6 * len(alvo))))
        if alvo and not any(len(alvo & l) >= precisa for l in linhas):
            faltam.append(item)
    contagem = {"ausencias_spec": len(itens), "ausencias_no_prd": len(itens) - len(faltam)}
    if not faltam:
        return [], contagem
    return [{
        "severidade": "atencao", "codigo": "ausencia-perdida", "etapa": "dev", "agente_responsavel": DONO,
        "resumo": (f"{len(faltam)} de {len(itens)} ausência(s) declarada(s) da spec (bloco 5) não aparecem no PRD: "
                   + "; ".join(f"«{i[:90]}»" for i in faltam) + ". A §5 do PRD traz as ausências declaradas do "
                   "ambiente — o que o app real tem e a missão deliberadamente não —, com as palavras da spec e o "
                   "motivo: sem elas, quem codifica reproduz o recurso do app real que a mecânica proíbe."),
    }], contagem


# --------------------------------------------------------------------------- validação
def validar(prd: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """O corpo do PRD (sem o anexo) contra o design e a spec da sessão.

    Do estado: `jornada_telas`, `copy_strings_revisada`, `brief_assets` e `spec_missao`. Insumo vazio
    pula a conferência que depende dele (a sessão de produto sem design não tem o que cobrar aqui). E o corpo
    contra o contrato da plataforma (`tools/conferir_prd_plataforma.validar_prd`), que não depende de insumo.
    """
    texto = prd or ""
    if not texto.strip():
        achado = {"severidade": "bloqueio", "codigo": "prd-vazio", "etapa": "dev", "agente_responsavel": DONO,
                  "resumo": "O PRD chegou vazio: não há tela, chave nem asset do design a conferir nele."}
        return {"status": "bloqueado", "achados": [achado], "contagens": {}}
    corpo = corpo_do_prd(texto)

    def insumo(chave: str) -> str:
        return _desembrulhar(str(state.get(chave, "") or ""))

    spec = insumo("spec_missao")
    achados: List[Dict[str, str]] = []
    contagens: Dict[str, Any] = {}
    # Insumo de design vazio pula a conferência que depende dele — mas não em silêncio: o PRD que «passou» contra uma
    # jornada que não existe não foi conferido (auditoria do padrão ouro, 08/10/2026). 🟡, para o semáforo mostrar.
    for chave, rotulo in (("jornada_telas", "jornada (telas)"), ("copy_strings_revisada", "copy revisada"),
                          ("brief_assets", "brief de assets"), ("spec_missao", "spec")):
        if not insumo(chave).strip():
            achados.append({"severidade": "atencao", "codigo": "insumo-ausente", "etapa": "dev", "agente_responsavel": DONO,
                            "resumo": f"Sem {rotulo} na sessão: o PRD não foi conferido contra ela — não é aprovação."})
    for novos, conta in (
        conferir_telas(corpo, insumo("jornada_telas")),
        conferir_chaves(corpo, insumo("copy_strings_revisada")),
        conferir_assets(corpo, insumo("brief_assets")),
        conferir_estados(corpo, spec),
        conferir_status_de_gate(texto),
        conferir_rf_p0(corpo),
        conferir_schemas(corpo, spec),
        conferir_propostas(corpo, spec),
        conferir_eventos(corpo, spec),
        conferir_ausencias(corpo, spec),
    ):
        achados += novos
        contagens.update(conta)
    # o que só o PRD leva à plataforma: modelo de dados, manifesto, ADR, capacidade, modelo de IA e os registros
    # do hub e da api que os testes da plataforma cobram (`tools/conferir_prd_plataforma.validar_prd`)
    from tools import conferir_prd_plataforma as plataforma

    achados += [{**a, "agente_responsavel": DONO} for a in plataforma.validar_prd(corpo, plataforma.slug_do_prd(corpo),
                                                                                   plataforma.datas_do_po(state))]
    return {"status": _status(achados), "achados": achados, "contagens": contagens}


# --------------------------------------------------------------------------- relatório
_LINHAS_CONTAGEM = (
    ("Telas do inventário nas stories/§10", "telas_no_prd", "telas_inventario"),
    ("Chaves da copy na story da tela, pelo nome", "chaves_na_story", "chaves_copy"),
    ("Chaves com «Onde vive» na story", "chaves_com_onde_vive", "chaves_copy"),
    ("Assets V1 do brief", "assets_no_prd", "assets_v1"),
    ("Estados do contrato da spec", "estados_no_prd", "estados_spec"),
    ("RF P0 com critério EARS/Gherkin", "rf_p0_com_criterio", "rf_p0"),
    ("Schemas/DTOs definidos no PRD", "schemas_definidos", "schemas_citados"),
    ("Propostas da spec marcadas no PRD", "propostas_marcadas", "propostas_no_prd"),
    ("Eventos da spec com o mesmo verbo e objeto na §13", "eventos_no_prd", "eventos_spec"),
    ("Ausências declaradas da spec", "ausencias_no_prd", "ausencias_spec"),
)


def relatorio(resultado: Dict[str, Any], missao: str = "") -> str:
    icone = {"aprovado": "🟢 PRD COBRE O DESIGN", "amarelo": "🟡 COM RESSALVAS",
             "bloqueado": "🔴 PRD NÃO COBRE O DESIGN"}[resultado["status"]]
    c = resultado.get("contagens") or {}
    linhas = [f"# Cobertura do design no PRD — {missao or 'missão'}", "", f"**Veredito: {icone}**", "",
              "Conferência por ID contra a jornada, a copy revisada, o brief de assets e a spec, e do que só o PRD "
              "leva à plataforma — modelo de dados, manifesto, ADR, capacidade, modelo de IA e registros do hub — "
              "contra o contrato da base. O anexo do PRD não conta como cobertura.", ""]
    tabela = [(rotulo, c.get(a, 0), c[b]) for rotulo, a, b in _LINHAS_CONTAGEM if c.get(b)]
    if tabela:
        linhas += ["| Conferência | No PRD | Esperado |", "|---|---:|---:|"]
        linhas += [f"| {rotulo} | {feito} | {total} |" for rotulo, feito, total in tabela]
        if c.get("chaves_por_curinga"):
            linhas.append(f"| Chaves cobertas só por curinga (`eN.tipo.*`), que não contam | {c['chaves_por_curinga']} | 0 |")
        linhas += [f"| Linhas de status de gate escritas pelo redator | {c.get('linhas_status_gate', 0)} | 0 |", ""]
    if resultado["achados"]:
        linhas += ["## Achados", ""]
        for a in resultado["achados"]:
            marca = "⛔" if a["severidade"] == "bloqueio" else "⚠️"
            linhas.append(f"- {marca} **{a['codigo']}** (dono: `{a['agente_responsavel']}`) — {a['resumo']}")
        linhas.append("")
    else:
        linhas += ["Nenhum achado: tela, chave, asset e estado do design estão no PRD, por ID, e o que ele leva à "
                   "plataforma confere com o contrato.", ""]
    linhas += ["```json", json.dumps({"agente": AGENTE, "missao": missao, "status": resultado["status"],
                                      "achados": resultado["achados"]}, ensure_ascii=False, indent=2), "```"]
    return "\n".join(linhas)
