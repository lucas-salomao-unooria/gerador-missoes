"""O que o PRD e o handoff afirmam sobre a plataforma existe nela?

A missão do 9º ano (06/10/2026) saiu da esteira com o PRD citando uma "ADR-108 (Proposta)" quando a
última ADR era a 148, o DS "v0.2.2" quando era o 0.2.18, a ponte `@edu/ui/ds-chatgpt` para uma missão
nova, tabelas próprias de enquete e de nota quando a evidência já é genérica, "zerar" que arquiva
sessões quando a plataforma abre rodada, e agendamento que a plataforma não tem. Nenhum gate conferia:
o contrato da plataforma não existia como lista.

Agora existe: o `contrato-plataforma.json` da base fixada na execução (`prompts/base_plataforma.py`),
extraído do código pela própria plataforma. Este módulo confere o texto contra ele, no molde de
`tools/rotas_plataforma.py`. Linha marcada `[PENDÊNCIA PLATAFORMA]` (ou "pendência de plataforma",
"a criar") é pedido à plataforma, não afirmação — não é conferida. Linha que cita a coisa para
proibi-la também não.

`validar_contrato` vale para o handoff e para o PRD. `validar_prd` (no fim do arquivo) é só do PRD: o
que o agente de codificação tira dele e que a plataforma cobra em teste — modelo de dados, manifesto,
ADR, capacidade, modelo de IA e os registros do hub. É chamado por `tools/cobertura_design.validar`.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from prompts import base_plataforma

_RE_PEDIDO = re.compile(r"pend[êe]ncia\s+(de\s+)?plataforma|\[\s*pend|a criar|rota nova|nova rota", re.IGNORECASE)
_RE_PROIBICAO = re.compile(
    r"\bn[ãa]o\s+(?:utiliz|us[ae]|cham|consum|cri[ae]|invent|import|crav|cit|possu|tem\b|implement|agend)|"
    r"\bnunca\b|\binexistente|\bpro[ií]b|\bvedad|\bn[ãa]o existe|"
    # o handoff da exp01ef1b (07/10/2026) dizia "Removidas as colunas `score_*`…", "Eliminação de menções a
    # agendamento" e "sem agendamento": três negações lidas como afirmação, e o PRD bloqueou por elas
    r"\bremovid|\bremov[ea]\b|\belimin|\bsem\s+agendament", re.IGNORECASE)
#: Ênfase markdown some antes da busca: "**NÃO** implementar agendamento" não casava `n[ãa]o\s+`.
_RE_ENFASE = re.compile(r"[*_`]+")
_RE_ADR = re.compile(r"\bADR-(\d{1,4})\b")
_RE_ADR_PROPOSTA = re.compile(r"\bADR-(\d{1,4})\b[^\n]{0,30}\b(propost|nova|a criar)", re.IGNORECASE)
_RE_PONTE = re.compile(r"@edu/ui/(ds(?:-[a-z]+)?)\b")
_RE_VERSAO_DS = re.compile(
    r"(?:design[- ]system|\bDS\b|@unooria/design-system)[^\n]{0,40}?\bv?\^?(0\.\d+\.\d+)\b", re.IGNORECASE)
_RE_PORTA = re.compile(r"\bporta[^\n]{0,40}?\b(5[12]\d\d)\b|\b(5[12]\d\d)\b[^\n]{0,20}\bporta\b", re.IGNORECASE)
_RE_TABELA_PROPRIA = re.compile(
    r"\b(exp\d{2}(?:ef|em)\d+b_[a-z_]*(?:poll|enquete|respostas|score|pontuac|nota)[a-z_]*)\b", re.IGNORECASE)
_RE_ARQUIVADA = re.compile(r"status\s*=\s*['\"]?arquivad|\bmarca[^\n]{0,40}\barquivad", re.IGNORECASE)
_RE_AGENDA = re.compile(r"\bagend(ar|ad[oa]|amento)\b", re.IGNORECASE)
_RE_JSON = re.compile(r"```json\s*\n(.*?)```", re.DOTALL)
_RE_SUFIXO_DE_INDICE = re.compile(r"_(idx|pkey|fkey|key|por_escola|unique|uniq|check|ck)$", re.IGNORECASE)
_RE_SLUG = re.compile(r"\b(exp\d{2}(?:ef|em)\d+b)\b", re.IGNORECASE)
_RE_NEW_EXP = re.compile(r"pnpm\s+new:exp\s+([a-z0-9-]+)", re.IGNORECASE)
#: Pontes das seções legadas (ADR-133 a 138): existem para as missões antigas, não para missão nova.
PONTES_LEGADAS = {"ds-chatgpt": "ds-unooriaai", "ds-insta": "ds-unoovista", "ds-whatsapp": "ds-unoochat",
                  "ds-unootube": None}


def _linhas_afirmativas(texto: str) -> Iterable[str]:
    for linha in (texto or "").splitlines():
        limpa = _RE_ENFASE.sub("", linha)
        if _RE_PEDIDO.search(limpa) or _RE_PROIBICAO.search(limpa):
            continue
        yield linha


def _slug_do_texto(texto: str) -> str:
    """O id da missão que o documento descreve: o `expNNefNb` mais citado nele."""
    contagem: Dict[str, int] = {}
    for m in _RE_SLUG.findall(texto or ""):
        contagem[m.lower()] = contagem.get(m.lower(), 0) + 1
    return max(contagem, key=contagem.get) if contagem else ""


def _ja_existe(exp: Dict[str, Any]) -> str:
    return (f"A `{exp.get('id')}` já existe na plataforma («{exp.get('nome')}», v{exp.get('versao')}, porta "
            f"{exp.get('porta')}, `{exp.get('pasta')}`). Trate a missão como atualização dela: a mesma porta e a mesma "
            f"pasta, sem `pnpm new:exp`, versão acima de {exp.get('versao')}; e registre na seção 19 a decisão do PO — "
            f"substituir a existente ou dar um id novo a esta.")


def _achado(codigo: str, resumo: str, severidade: str = "bloqueio", etapa: str = "dev") -> Dict[str, str]:
    return {"severidade": severidade, "codigo": codigo, "etapa": etapa, "resumo": resumo}


def _manifestos(texto: str) -> List[Dict[str, Any]]:
    """Blocos JSON do documento que têm cara de `experiencia.json`."""
    encontrados = []
    for bloco in _RE_JSON.findall(texto or ""):
        try:
            dados = json.loads(bloco)
        except json.JSONDecodeError:
            continue
        if isinstance(dados, dict) and "capabilities" in dados and ("series" in dados or "publico" in dados):
            encontrados.append(dados)
    return encontrados


def validar_contrato(texto: str, slug: str = "") -> List[Dict[str, str]]:
    """Achados sobre o que o documento afirma da plataforma e o contrato da base desmente.

    `slug` é a missão descrita (sem ele, a mais citada no texto): a porta dela não está "ocupada" por ela
    mesma, e uma missão que a plataforma já tem não nasce de `pnpm new:exp` (exp01ef1b, 07/10/2026).
    """
    try:
        c = base_plataforma.contrato()
    except base_plataforma.BaseIndisponivel:
        return []
    adr = c.get("adr") or {}
    ultima, proxima = int(adr.get("ultima") or 0), int(adr.get("proxima") or 0)
    ds = c.get("design_system") or {}
    pontes = {str(p.get("ponte") or "").split("/")[-1] for p in ds.get("pontes") or []}
    versao_ds = re.sub(r"[^\d.]", "", str(ds.get("dependencia") or ""))
    portas = {str(v): k for k, v in ((c.get("portas") or {}).get("ocupadas") or {}).items()}
    man = c.get("manifesto") or {}
    slug = (slug or _slug_do_texto(texto)).lower()
    existente = next((e for e in c.get("experiencias") or [] if str(e.get("id") or "").lower() == slug), None)
    achados: List[Dict[str, str]] = []
    vistos: set = set()

    def uma_vez(chave: str, achado: Dict[str, str]) -> None:
        if chave not in vistos:
            vistos.add(chave)
            achados.append(achado)

    for linha in _linhas_afirmativas(texto):
        for m in _RE_ADR_PROPOSTA.finditer(linha):
            n = int(m.group(1))
            if proxima and n != proxima:
                uma_vez(f"adr-proposta-{n}", _achado(
                    "adr-numero-errado",
                    f"`ADR-{n}` aparece como decisão nova, mas a última ADR da plataforma é a {ultima} e a próxima é a "
                    f"**ADR-{proxima}** (contrato da plataforma). A ADR-{n} já existe com outro assunto."))
        for m in _RE_ADR.finditer(linha):
            n = int(m.group(1))
            if ultima and n > proxima:
                uma_vez(f"adr-inexistente-{n}", _achado(
                    "adr-inexistente", f"`ADR-{n}` não existe: a última ADR da plataforma é a {ultima}."))
        for m in _RE_PONTE.finditer(linha):
            ponte = m.group(1)
            if pontes and ponte not in pontes:
                uma_vez(f"ponte-{ponte}", _achado(
                    "ponte-inexistente",
                    f"`@edu/ui/{ponte}` não existe. As pontes da plataforma são: "
                    + ", ".join(f"`@edu/ui/{p}`" for p in sorted(pontes)) + "."))
            elif ponte in PONTES_LEGADAS:
                sucessora = PONTES_LEGADAS[ponte]
                uma_vez(f"ponte-legada-{ponte}", _achado(
                    "ponte-legada",
                    f"`@edu/ui/{ponte}` é a ponte de uma seção legada: missão nova não reproduz a identidade de app de "
                    f"terceiro (ADR-133 a 138)" + (f" e usa `@edu/ui/{sucessora}`" if sucessora else "")
                    + " — veja `ambientes.md`. A legada só por decisão registrada do PO.", etapa="produto"))
        for m in _RE_VERSAO_DS.finditer(linha):
            if versao_ds and m.group(1) != versao_ds:
                uma_vez(f"ds-{m.group(1)}", _achado(
                    "ds-versao-cravada",
                    f"O documento crava o DS em `{m.group(1)}`; a plataforma está em `^{versao_ds}` e segue sempre a "
                    f"última versão publicada (versão única, ADR-139). Não crave número.", severidade="atencao"))
        for m in _RE_PORTA.finditer(linha):
            porta = m.group(1) or m.group(2)
            if existente and porta != str(existente.get("porta")):
                uma_vez(f"porta-{porta}", _achado(
                    "experiencia-ja-existe",
                    _ja_existe(existente) + f" O documento põe a missão na porta {porta}."))
            elif porta in portas and portas[porta] != slug:
                uma_vez(f"porta-{porta}", _achado(
                    "porta-ocupada",
                    f"A porta {porta} já é da `{portas[porta]}`. A próxima livre é a "
                    f"{(c.get('portas') or {}).get('proxima_livre', '?')} (contrato da plataforma)."))
        for m in _RE_TABELA_PROPRIA.finditer(linha):
            tabela = _RE_SUFIXO_DE_INDICE.sub("", _RE_SUFIXO_DE_INDICE.sub("", m.group(1).lower()))
            uma_vez(f"tabela-{tabela}", _achado(
                "evidencia-tabela-propria",
                f"`{tabela}` guarda enquete ou nota por missão. A evidência pedagógica é genérica (módulo "
                f"`evidencias/`, E14): ficha em `apps/api/src/evidencias/fichas/<expId>.ts`, Canal B pelas rotas "
                f"`/evidencias/:expId/perguntas/:id`. Não crie tabela própria."))
        if _RE_ARQUIVADA.search(linha) and re.search(r"zer|reaplic|reinici|sess", linha, re.IGNORECASE):
            uma_vez("zerar-arquivada", _achado(
                "zerar-arquiva",
                "\"Zerar\" que arquiva sessões não é o modelo da plataforma: zerar abre uma **rodada** nova sem apagar "
                "nada (molde da A Seleção e do Júri, no contrato e nos exemplares)."))
        for m in _RE_NEW_EXP.finditer(linha):
            if existente and m.group(1).lower() == slug:
                uma_vez("new-exp", _achado(
                    "experiencia-ja-existe", _ja_existe(existente) + " O documento manda criá-la com `pnpm new:exp`."))
        if _RE_AGENDA.search(linha):
            uma_vez("agendamento", _achado(
                "agendamento-inexistente",
                "A plataforma não tem agendamento: pôr a atividade no ar libera a missão na sala na hora (ADR-146). "
                "Se a missão precisa de agendamento, é `[PENDÊNCIA PLATAFORMA]` com dono."))

    for dados in _manifestos(texto):
        fora = sorted(set(dados) - set(man.get("chaves") or dados))
        if fora:
            uma_vez("manifesto-chaves", _achado(
                "manifesto-chave-inexistente",
                f"O manifesto traz {fora}, que não são chaves de `experiencia.json`. As aceitas são "
                f"{man.get('chaves')} (contrato da plataforma)."))
        for cap in dados.get("capabilities") or []:
            if man.get("capabilities") and cap not in man["capabilities"]:
                uma_vez(f"cap-{cap}", _achado(
                    "manifesto-capability", f"`{cap}` não é capability da plataforma ({man['capabilities']}).",
                    severidade="atencao", etapa="plataforma"))
        for perm in dados.get("permissoes") or []:
            if man.get("permissoes_iframe") and perm not in man["permissoes_iframe"]:
                uma_vez(f"perm-{perm}", _achado(
                    "manifesto-permissao", f"`{perm}` não é permissão de iframe concedida ({man['permissoes_iframe']}).",
                    severidade="atencao", etapa="plataforma"))
    return achados


# =========================================================================== só o PRD
#
# `validar_contrato` confere o que o documento AFIRMA. Daqui para baixo é o que o PRD tem de TRAZER para o
# agente de codificação não decidir sozinho — e o que, faltando ou errado, quebra um teste da plataforma. A
# auditoria de 07/10/2026 leu os PRDs da exp01ef1b e da exp09ef1b contra o código: ids `TEXT` com «NÃO usar
# `UUID`», `escola_id UUID`, `tentativa` no lugar da rodada, nenhum `experiencia.json`, a ADR-108 com outro
# assunto, um RF P0 de offline que o SDK não tem e nenhum dos registros do hub que os testes cobram. As
# severidades foram medidas nas sete sessões completas do bucket (exp01ef1b, exp02em1b, exp04ef1b, exp05ef1b,
# exp06ef1b, exp07ef1b e exp09ef1b), contra a base fixada nos testes (89e0f9ae) e a base viva de 07/10/2026
# (6587824e): cada conferência diz no comentário o que mediu.

_RE_CERCA_CODIGO = re.compile(r"```([\w+-]*)[^\n]*\n(.*?)```", re.S)
_RE_CERCA_LINHA = re.compile(r"^\s*(```|~~~)")
#: O título da seção do PRD (`# 11. Modelo de dados`, `## 3 — Não-objetivos`): só os níveis 1 e 2 — o
#: `### 10. Custos e Quotas de IA` dentro da §9 da exp02em1b não abre a §10.
_RE_TITULO_SECAO = re.compile(r"^#{1,2}\s+\**\s*(\d{1,2})\s*(?:[.)—–-]|\s)")


def _linhas_com_secao(texto: str) -> Iterable[Tuple[Optional[int], str, bool]]:
    """(número da seção do PRD, linha, está dentro de bloco de código)."""
    secao: Optional[int] = None
    cerca = False
    for linha in (texto or "").splitlines():
        if _RE_CERCA_LINHA.match(linha):
            cerca = not cerca
            yield secao, linha, True
            continue
        if not cerca:
            m = _RE_TITULO_SECAO.match(linha)
            if m:
                secao = int(m.group(1))
        yield secao, linha, cerca


#: Negação na linha, antes do termo: «NÃO escrever Service Worker na missão», «a missão não opera offline».
#: `_RE_PROIBICAO` só conhece os verbos de `validar_contrato` («não usar», «não criar»…).
_RE_NEGACAO = re.compile(r"\b(?:n[ãa]o|nunca|jamais|nem)\b|\bproib|\bvedad", re.I)


def _afirmativa(linha: str) -> bool:
    limpa = _RE_ENFASE.sub("", linha)
    return not (_RE_PEDIDO.search(limpa) or _RE_PROIBICAO.search(limpa))


def _norm_simples(texto: str) -> str:
    sem = "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", sem).strip(" `*_|:")


_PARADAS = frozenset("""
a o e de da do das dos em no na nos nas um uma uns umas para pra por com sem que se ao aos as os nao ou mais
muito como pelo pela pelos pelas este esta isto esse essa isso aquele aquela ser sao tem ter foi era sobre entre
quando onde qual quais cada todo toda todos todas outro outra outros outras mesmo mesma ja so seu sua seus suas
zero total ausencia ausente ausentes deliberada nenhum nenhuma qualquer adr
""".split())
#: Palavras que todo título de ADR e toda glosa de missão dividem: casar por elas não diz que é a mesma decisão.
_GENERICAS = frozenset({"missa", "plata", "exper", "decis", "siste"})


def radicais(texto: str) -> Set[str]:
    """Os cinco primeiros caracteres de cada palavra de conteúdo, sem acento: `Sincronização` e `sincronizar`
    caem no mesmo radical. É o casamento mais burro que ainda distingue assunto — e é determinístico."""
    sem = _norm_simples(texto)
    return {p[:5] for p in re.findall(r"[a-z0-9]+", sem) if len(p) >= 4 and p not in _PARADAS}


# --------------------------------------------------------------------------- frontmatter e id da missão
_RE_FRONTMATTER = re.compile(r"\A\s*---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.S)
_RE_ID_MISSAO = re.compile(r"^exp\d{2}e[fm]\db$")


def frontmatter(texto: str) -> Dict[str, str]:
    """As chaves de primeiro nível do frontmatter YAML, como texto (`serie: ["1EF"]` → `'["1EF"]'`)."""
    m = _RE_FRONTMATTER.match(texto or "")
    saida: Dict[str, str] = {}
    for linha in (m.group(1).splitlines() if m else []):
        mm = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", linha)
        if mm:
            saida[mm.group(1).lower()] = re.sub(r"\s+#\s.*$", "", mm.group(2)).strip().strip("'\"")
    return saida


def codigo_da_missao(serie: str, unidade: Any) -> str:
    """`codigoDaMissao` da plataforma (`apps/api/src/comum/codigo-da-experiencia.ts`, ADR-110): `8EF` + 1 →
    `exp08ef1b`. Fora da grade (série que não existe, unidade fora de 1–4) devolve vazio."""
    m = re.fullmatch(r"([1-9])(EF|EM)", str(serie or "").strip().upper())
    try:
        u = int(unidade)
    except (TypeError, ValueError):
        return ""
    if not m or (m.group(2) == "EM" and int(m.group(1)) > 3) or not 1 <= u <= 4:
        return ""
    return f"exp0{m.group(1)}{m.group(2).lower()}{u}b"


def _series(valor: Any) -> List[str]:
    if isinstance(valor, list):
        return [str(v).strip().upper() for v in valor]
    return re.findall(r"\b([1-9]E[FM])\b", str(valor or "").upper())


def slug_do_prd(texto: str) -> str:
    """O id da missão do PRD: o `slug_experiencia` do frontmatter, o `id` do manifesto, ou o mais citado."""
    fm = frontmatter(texto).get("slug_experiencia", "").lower()
    if _RE_ID_MISSAO.match(fm):
        return fm
    for _, dados, _ in blocos_de_manifesto(texto):
        if dados and _RE_ID_MISSAO.match(str(dados.get("id") or "").lower()):
            return str(dados["id"]).lower()
    return _slug_do_texto(texto)


# --------------------------------------------------------------------------- 1. modelo de dados
#: O tipo que a plataforma grava em toda tabela de missão (`exemplo-schema-exp.md` e
#: `exemplo-migration-exp06ef1b.md` da base). O tenant é texto — `escolas.id` é `escola-demo`, e a RLS o
#: compara com `current_setting('app.escola_id', true)`, que é texto; turma e estudante são as chaves UUID de
#: `turmas` e `users`, e a FK entre `TEXT` e `UUID` o Postgres recusa.
TIPO_DA_PLATAFORMA = {"escola_id": "TEXT", "turma_id": "UUID", "estudante_id": "UUID"}
_FAMILIA_DA_PLATAFORMA = {"escola_id": "texto", "turma_id": "uuid", "estudante_id": "uuid"}
#: De qual atividade é a sessão: o pacote (Júri, Jornal, Quem mandou isso?) ou a cobertura (A Seleção).
#: A evidência é por atividade e rodada (ADR-112), e a atividade é do professor (ADR-130).
COLUNAS_DE_ATIVIDADE = ("pacote_id", "atividade_id", "cobertura_id", "edicao_id")
_TESTE_IDENTIDADE = "`apps/api/tests/identidade-unica.spec.ts › toda coluna de pessoa aponta para users`"

_RE_CREATE = re.compile(r"\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:\w+\.)?[\"`]?(\w+)[\"`]?\s*\(", re.I)
_TIPOS_SQL = (r"UUID|CITEXT|TEXT|VARCHAR|CHARACTER\s+VARYING|CHAR|SMALLINT|INTEGER|INT[248]?|BIGINT|SMALLSERIAL|"
              r"BIGSERIAL|SERIAL|BOOLEAN|BOOL|JSONB|JSON|TIMESTAMPTZ|TIMESTAMP|DATE|NUMERIC|DECIMAL|REAL|"
              r"DOUBLE\s+PRECISION")
_RE_COLUNA_SQL = re.compile(r"^\s*[\"`]?([A-Za-z_]\w*)[\"`]?\s+(" + _TIPOS_SQL + r")\b(.*)$", re.I)
_RE_FK_SQL = re.compile(r"FOREIGN\s+KEY\s*\(([^)]*)\)\s*REFERENCES\b", re.I)
_RE_FK_ALTER = re.compile(r"ALTER\s+TABLE\s+(?:ONLY\s+)?(?:\w+\.)?[\"`]?(\w+)[\"`]?\s+ADD\s+(?:CONSTRAINT\s+\S+\s+)?"
                          r"FOREIGN\s+KEY\s*\(([^)]*)\)\s*REFERENCES\b", re.I)
_NAO_COLUNA_SQL = {"constraint", "primary", "unique", "foreign", "check", "exclude", "like"}
_RE_MODELO_PRISMA = re.compile(r"^[ \t]*model\s+(\w+)\s*\{(.*?)^[ \t]*\}", re.S | re.M)
_RE_CAMPO_PRISMA = re.compile(r"^\s*(\w+)\s+(String|Int|BigInt|Boolean|Json|DateTime|Decimal|Float|Bytes)(\?|\[\])?([^\n]*)$",
                              re.M)
_RE_RELACAO_PRISMA = re.compile(r"@relation\([^\n]*?fields:\s*\[([^\]]*)\]")
_RE_ENTIDADE_ER = re.compile(r"^\s*\"?([\w-]+)\"?\s*\{\s*$")
_RE_ATRIBUTO_ER = re.compile(r"^\s*([A-Za-z][\w()]*)\s+([A-Za-z_]\w*)\b")
_RE_TABELA_EXP = re.compile(r"`(exp\d{2}e[fm]\d+b_[a-z0-9_]+)`", re.I)
_RE_COLUNA_PROSA = re.compile(r"`([a-z_][a-z0-9_]*)\s+(UUID|TEXT|VARCHAR(?:\s*\(\d+\))?|SMALLINT|INTEGER|INT|BIGINT|BOOLEAN|"
                              r"JSONB|TIMESTAMPTZ)\b[^`]*`", re.I)
#: Linha que registra o que OUTRO documento diz (a tabela «Divergências spec × plataforma» da §19, «a spec
#: declarava `escola_id UUID`») não é declaração do PRD.
_RE_PROSA_DE_REGISTRO = re.compile(r"\bspec\b|one-pager|diverg", re.I)


_RE_NAO_USE_UUID = re.compile(r"\b(?:n[ãa]o|nunca)\s+(?:usar|use|utilizar|declarar)\s+UUID\b", re.I)


def _familia(tipo: str) -> str:
    t = re.sub(r"\s*\(.*$", "", (tipo or "").strip().lower())
    if t == "uuid":
        return "uuid"
    if t in ("text", "citext", "string", "varchar", "character varying", "char", "character"):
        return "texto"
    if t in ("int", "integer", "int2", "int4", "int8", "smallint", "bigint", "serial", "bigserial", "smallserial"):
        return "inteiro"
    return "outro"


def _snake(nome: str) -> str:
    return re.sub(r"(?<=[a-z0-9])([A-Z])", r"_\1", nome).lower()


def _nomes(lista: str) -> List[str]:
    return [n.strip().strip("\"`").lower() for n in (lista or "").split(",") if n.strip()]


def _fecha_parenteses(texto: str, inicio: int) -> str:
    nivel, i = 1, inicio
    while i < len(texto) and nivel:
        nivel += {"(": 1, ")": -1}.get(texto[i], 0)
        i += 1
    return texto[inicio:i - 1]


def colunas_declaradas(texto: str) -> List[Dict[str, Any]]:
    """Toda coluna que o PRD declara com tipo: DDL SQL, schema Prisma, `erDiagram` e prosa com `` `col TIPO` ``.

    Cada uma: `tabela`, `coluna`, `tipo` (como escrito), `familia` (`uuid`, `texto`, `inteiro`, `outro`),
    `fonte` e `fk` — `True`/`False` onde a fonte expressa chave estrangeira (SQL e Prisma), `None` onde não
    expressa (o `FK` do `erDiagram` e a prosa não são migration). Os PRDs das sete sessões declaram o modelo
    nas quatro formas, às vezes em duas ao mesmo tempo (a exp07ef1b tem `erDiagram` e DDL).
    """
    texto = texto or ""
    saida: List[Dict[str, Any]] = []

    def anota(tabela: str, coluna: str, tipo: str, fonte: str, fk: Optional[bool]) -> None:
        saida.append({"tabela": tabela.lower(), "coluna": coluna.lower(), "tipo": re.sub(r"\s+", " ", tipo).strip(),
                      "familia": _familia(tipo), "fonte": fonte, "fk": fk})

    # SQL: CREATE TABLE, a FK na coluna, na tabela ou num ALTER TABLE depois
    fks_alter: Dict[str, Set[str]] = {}
    for m in _RE_FK_ALTER.finditer(texto):
        fks_alter.setdefault(m.group(1).lower(), set()).update(_nomes(m.group(2)))
    for m in _RE_CREATE.finditer(texto):
        tabela = m.group(1).lower()
        corpo = _fecha_parenteses(texto, m.end())
        fks = set(fks_alter.get(tabela, set()))
        for f in _RE_FK_SQL.finditer(corpo):
            fks.update(_nomes(f.group(1)))
        for linha in corpo.splitlines():
            c = _RE_COLUNA_SQL.match(linha)
            if c and c.group(1).lower() not in _NAO_COLUNA_SQL:
                inline = bool(re.search(r"\bREFERENCES\b", c.group(3), re.I))
                anota(tabela, c.group(1), c.group(2), "DDL SQL", inline or c.group(1).lower() in fks)

    # Prisma: `@db.Uuid` faz o `String` virar UUID; a FK é o `@relation(fields: [...])`
    for m in _RE_MODELO_PRISMA.finditer(texto):
        corpo = m.group(2)
        mapa = re.search(r"@@map\(\s*\"(\w+)\"", corpo)
        tabela = mapa.group(1) if mapa else m.group(1)
        com_fk: Set[str] = set()
        for r in _RE_RELACAO_PRISMA.finditer(corpo):
            com_fk.update(n.strip() for n in r.group(1).split(",") if n.strip())
        for c in _RE_CAMPO_PRISMA.finditer(corpo):
            campo, tipo, resto = c.group(1), c.group(2), c.group(4)
            coluna = (re.search(r"@map\(\s*\"(\w+)\"", resto) or [None, _snake(campo)])[1]
            if tipo == "String":
                db = re.search(r"@db\.(\w+)", resto)
                tipo = {"uuid": "UUID", "varchar": "VARCHAR", "char": "CHAR"}.get((db.group(1) if db else "").lower(),
                                                                                 "TEXT")
            anota(tabela, coluna, tipo, "schema Prisma", campo in com_fk)

    # erDiagram (Mermaid): `uuid turma_id FK`
    for lingua, bloco in _RE_CERCA_CODIGO.findall(texto):
        if "erDiagram" not in bloco:
            continue
        entidade = ""
        for linha in bloco.splitlines():
            e = _RE_ENTIDADE_ER.match(linha)
            if e:
                entidade = e.group(1)
                continue
            if linha.strip() == "}":
                entidade = ""
                continue
            a = _RE_ATRIBUTO_ER.match(linha)
            if entidade and a:
                anota(entidade, a.group(2), a.group(1), "erDiagram", None)

    # prosa: «`exp09ef1b_conteudo_turma`: … PK: `turma_id UUID`. Campos: `escola_id TEXT`, …» (exp09ef1b)
    for secao, linha, cerca in _linhas_com_secao(texto):
        if (cerca or secao in (3, 19) or _RE_PROSA_DE_REGISTRO.search(linha) or not _afirmativa(linha)
                or _RE_NEGACAO.search(_RE_ENFASE.sub("", linha))):
            continue
        tabela = _RE_TABELA_EXP.search(linha)
        for c in _RE_COLUNA_PROSA.finditer(linha):
            anota(tabela.group(1) if tabela else "(prosa)", c.group(1), c.group(2), "prosa", None)
    return saida


def _da_missao(tabela: str) -> bool:
    return bool(re.match(r"^exp\d{2}", tabela, re.I))


def conferir_modelo_de_dados(texto: str) -> List[Dict[str, str]]:
    """Tipos e chaves do PRD contra os da plataforma, e a sessão contra o molde da rodada.

    Medido nas sete sessões: a exp01ef1b declarou `turma_id` e `estudante_id` `String` sem `@db.Uuid` e sem
    FK, e escreveu «NÃO usar `UUID`» na §17.4; a exp06ef1b, `escola_id UUID` nas quatro tabelas (com o
    `::uuid` na policy para fechar a conta); a exp02em1b, `escola_id UUID NOT NULL` num RNF e no
    `erDiagram`. A exp04, a exp05, a exp07 e a exp09 acertaram os tipos — e a exp05 e a exp07 deixaram o
    `estudante_id` de `_reflexoes` sem FK, que o teste de identidade única da plataforma reprova. Todas as
    sete gravam `tentativa` (ou nada) no lugar de `rodada`, e nenhuma põe o pacote na sessão.
    """
    colunas = colunas_declaradas(texto)
    achados: List[Dict[str, str]] = []

    divergentes: List[str] = []
    vistos: Set[Tuple[str, str, str, str]] = set()
    for c in colunas:
        esperada = _FAMILIA_DA_PLATAFORMA.get(c["coluna"])
        chave = (c["tabela"], c["coluna"], c["tipo"].upper(), c["fonte"])
        if esperada and c["familia"] != esperada and chave not in vistos:
            vistos.add(chave)
            onde = "" if c["tabela"] == "(prosa)" else f"{c['tabela']}."
            divergentes.append(f"`{onde}{c['coluna']}` {c['tipo']} ({c['fonte']}) — a plataforma grava "
                               f"`{TIPO_DA_PLATAFORMA[c['coluna']]}`")
    # a instrução contrária, sem DDL: «**NÃO** usar `UUID` para `estudante_id`, `sessao_id` ou `turma_id`» (§17.4 da
    # exp01ef1b, 07/10/2026) — quem codifica obedece, e a FK para `users(id)` deixa de existir
    for secao, linha, cerca in _linhas_com_secao(texto):
        limpa = re.sub(r"[*`]+", "", linha)  # sem tirar o `_`: `estudante_id` continua inteiro
        if cerca or secao == 19 or not _RE_NAO_USE_UUID.search(limpa):
            continue
        for col in dict.fromkeys(re.findall(r"\b(turma_id|estudante_id)\b", limpa)):
            item = f"`{col}` «não usar `UUID`» (prosa) — a plataforma grava `UUID`"
            if item not in divergentes:
                divergentes.append(item)
    if divergentes:
        achados.append(_achado(
            "tipo-divergente-da-plataforma",
            f"{len(divergentes)} coluna(s) com o tipo diferente do da plataforma: " + "; ".join(divergentes) + ". "
            "Na plataforma `escola_id` é `TEXT NOT NULL` (o tenant é `escola-demo`, e a RLS o compara com "
            "`current_setting('app.escola_id', true)`, que é texto); `turma_id` é `UUID NOT NULL` com FK para "
            "`turmas(id)` e `estudante_id` é `UUID NOT NULL` com FK para `users(id)`, os dois `ON DELETE CASCADE` "
            "(moldes `exemplo-schema-exp.md` e `exemplo-migration-exp06ef1b.md`). O corpo segue a plataforma mesmo "
            "quando a spec diz outra coisa; a divergência vai para a tabela «Divergências spec × plataforma» da §19."))

    sem_fk_estudante = sorted({c["tabela"] for c in colunas
                               if c["coluna"] == "estudante_id" and c["fk"] is False and _da_missao(c["tabela"])})
    sem_fk_turma = sorted({c["tabela"] for c in colunas
                           if c["coluna"] == "turma_id" and c["fk"] is False and _da_missao(c["tabela"])})
    if sem_fk_estudante:
        achados.append(_achado(
            "tipo-divergente-da-plataforma",
            f"`estudante_id` sem chave estrangeira em {', '.join(f'`{t}`' for t in sem_fk_estudante)}: o "
            f"{_TESTE_IDENTIDADE} reprova toda coluna `estudante_id` sem FK, e sem ela a eliminação a pedido do "
            "titular (ADR-140) deixa o dado da criança para trás. Declare `FOREIGN KEY (\"estudante_id\") "
            "REFERENCES \"users\"(\"id\") ON DELETE CASCADE` em cada uma — inclusive na tabela de reflexões, que "
            "já tem a FK para a sessão."))
    if sem_fk_turma:
        achados.append(_achado(
            "tipo-divergente-da-plataforma",
            f"`turma_id` sem chave estrangeira em {', '.join(f'`{t}`' for t in sem_fk_turma)}. No molde, toda "
            "tabela da missão tem `turma_id` denormalizado com FK para `turmas(id)` `ON DELETE CASCADE`: sem ela, "
            "a turma que sai leva o resto e deixa estas linhas.", severidade="atencao"))

    # A sessão: rodada, não tentativa; e de qual atividade ela é. DDL SQL e schema Prisma são a lista de
    # colunas; sem eles (`erDiagram` e prosa, como na exp09ef1b), vale também a coluna citada sem tipo na
    # linha da tabela — «UK: `[pacote_id, rodada, estudante_id]`» —, e só como coluna: a `rodada` de um KPI
    # numa linha que cita `exp04ef1b_sessoes` escondia a sessão sem rodada do schema Prisma da exp04ef1b.
    por_tabela: Dict[str, Dict[str, Set[str]]] = {}
    for c in colunas:
        if _da_missao(c["tabela"]) and "sess" in c["tabela"]:
            fonte = "ddl" if c["fonte"] in ("DDL SQL", "schema Prisma") else "outra"
            por_tabela.setdefault(c["tabela"], {}).setdefault(fonte, set()).add(c["coluna"])
    problemas: List[str] = []
    for tabela, fontes in sorted(por_tabela.items()):
        cols = fontes.get("ddl") or fontes.get("outra") or set()
        if "ddl" not in fontes:
            for linha in texto.splitlines():
                if re.search(rf"\b{re.escape(tabela)}\b", linha, re.I):
                    cols = cols | {n.lower() for n in re.findall(
                        r"(?:`|\[|,\s*|\(\s*)(rodada|tentativa|" + "|".join(COLUNAS_DE_ATIVIDADE) + r")(?=`|\]|\s*,|\s*\))",
                        linha, re.I)}
        faltas = []
        if "tentativa" in cols:
            faltas.append("`tentativa` no lugar de `rodada`")
        elif "rodada" not in cols:
            faltas.append("sem `rodada`")
        if not any(a in cols for a in COLUNAS_DE_ATIVIDADE):
            faltas.append("sem a atividade (`pacote_id`)")
        if faltas:
            problemas.append(f"`{tabela}`: " + ", ".join(faltas))
    if problemas:
        achados.append(_achado(
            "sessao-sem-rodada",
            "A sessão não está no molde da plataforma — " + "; ".join(problemas) + ". A sessão é de um estudante "
            "numa rodada de uma atividade: `pacote_id UUID` (FK para `<id>_pacotes`), `rodada INTEGER NOT NULL` "
            "(CHECK ≥ 1) e `UNIQUE (pacote_id, rodada, estudante_id)` com nome dado à mão. Zerar soma 1 à rodada no "
            "gate da turma e abre outra linha; a anterior fica, imutável, e é ela que o painel de habilidades lê — "
            "a evidência é por atividade e rodada (ADR-112/145), e `EvidenciasService.marcar` precisa das duas. "
            "Não existe coluna `tentativa` de reaplicação: o que se conta por ação é `<acao>_tentativas`."))
    return achados


# --------------------------------------------------------------------------- 2. manifesto
#: As séries da plataforma (`apps/api/src/comum/series.ts`), o enum do `UpsertSchema` do manifesto.
SERIES = tuple(f"{n}EF" for n in range(1, 10)) + tuple(f"{n}EM" for n in range(1, 4))
_TESTE_PUT = "`apps/api/tests/manifestos-passam-no-put.spec.ts › o corpo do PUT passa no UpsertSchema da rota`"
_TESTE_CODIGO = "`apps/api/tests/codigo-da-experiencia.spec.ts`"
_RE_ABERTO_PO = re.compile(r"\[\s*ABERTO\s*[—–-]+\s*dono\s*:\s*PO\b", re.I)
_RE_DECISAO_PO_REGISTRADA = re.compile(
    r"(?:\[\s*ABERTO\s*[—–-]+\s*dono\s*:\s*PO\b|"
    r"(?:decis[ãa]o|parecer|pedido)\s+(?:do\s+)?PO\b[^\n]{0,200}(?:substitu|manter|c[óo]digo|vers[ãa]o|\b\d{2}/\d{2}(?:/\d{4})?\b|\b\d{4}-\d{2}-\d{2}\b))",
    re.IGNORECASE
)


def blocos_de_manifesto(texto: str) -> List[Tuple[str, Optional[Dict[str, Any]], str]]:
    """(bloco, dados, erro) de cada bloco de código com cara de `experiencia.json` — o `id` ou as `series`, e uma
    das chaves que só o manifesto tem. Comentário `//` e vírgula sobrando não reprovam a leitura (o redator
    anota o manifesto); bloco que nem assim é JSON volta com o erro."""
    saida: List[Tuple[str, Optional[Dict[str, Any]], str]] = []
    for lingua, bloco in _RE_CERCA_CODIGO.findall(texto or ""):
        if lingua.lower() not in ("", "json", "jsonc", "json5"):
            continue
        if not (re.search(r"\"(?:capabilities|verbos|permissoes|viewport)\"\s*:", bloco)
                and re.search(r"\"(?:id|series)\"\s*:", bloco)):
            continue
        erro = "o bloco não é um objeto JSON"
        for tentativa in (bloco, re.sub(r",(\s*[}\]])", r"\1", re.sub(r"(?m)^\s*//.*$|\s+//[^\"\n]*$", "", bloco))):
            try:
                dados = json.loads(tentativa)
            except json.JSONDecodeError as e:
                erro = str(e)
                continue
            if isinstance(dados, dict):
                saida.append((bloco, dados, ""))
                break
        else:
            saida.append((bloco, None, erro))
    return saida


def _semver(v: Any) -> Optional[Tuple[int, int, int]]:
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", str(v or "").strip())
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def datas_do_po(state: Dict[str, Any]) -> Set[str]:
    """`DD/MM/AAAA` de cada parecer humano e pedido do PO da sessão: a fonte que prova uma decisão registrada."""
    datas: Set[str] = set()
    for p in list(state.get("pareceres_humanos") or []) + list(state.get("pedidos_do_po") or []):
        if isinstance(p, dict):
            datas.update(re.findall(r"\b\d{2}/\d{2}/\d{4}\b", f"{p.get('quando') or ''} {p.get('origem') or ''}"))
    return datas


def _decisao_do_po_provada(texto: str, datas_po: Optional[Set[str]]) -> bool:
    """O marcador `[ABERTO — dono: PO …]`, ou uma decisão do PO cuja data é a de um parecer ou pedido da sessão.

    Sem `datas_po` (chamador sem estado) a decisão escrita não prova nada: só o marcador vale (princípio 1 do
    plano padrão ouro — nenhuma isenção pela palavra do próprio modelo)."""
    if _RE_ABERTO_PO.search(texto):
        return True
    if not datas_po:
        return False
    for m in _RE_DECISAO_PO_REGISTRADA.finditer(texto):
        linha = texto[texto.rfind("\n", 0, m.start()) + 1:texto.find("\n", m.end()) if "\n" in texto[m.end():] else len(texto)]
        if any(d in linha for d in datas_po):
            return True
    return False


def conferir_manifesto(texto: str, slug: str, c: Dict[str, Any],
                       datas_po: Optional[Set[str]] = None) -> List[Dict[str, str]]:
    """O `experiencia.json` completo no PRD, que passe nos testes da plataforma, com o id derivado.

    Medido nas sete sessões: só a exp02em1b trazia o manifesto num bloco json, sem o `viewport` — e é o
    `viewport` que diz a casca de aparelho. As outras seis o descreviam em prosa ou numa linha da árvore de
    arquivos («Manifesto v0.1.0 completo», exp01ef1b): quem codifica decide capabilities, permissões,
    viewport e verbos. Os sete frontmatters têm `slug_experiencia` igual a `codigoDaMissao(serie, unidade)`.
    """
    man = c.get("manifesto") or {}
    chaves = list(man.get("chaves") or [])
    publicos = list(man.get("publico") or ["estudante", "professor"])
    achados: List[Dict[str, str]] = []
    blocos = blocos_de_manifesto(texto)
    validos = [d for _, d, _ in blocos if d is not None]
    if not validos:
        erro = next((e for _, d, e in blocos if d is None), "")
        achados.append(_achado(
            "manifesto-ausente",
            ("O bloco do manifesto não é JSON válido (" + erro + ")" if erro else
             "O PRD não traz o `public/experiencia.json` num bloco ```json") + ". A §17.1 leva o manifesto completo, "
            f"com as chaves do contrato da plataforma ({', '.join(f'`{k}`' for k in chaves)}), no molde de "
            "`exemplo-manifesto-exp06ef1b.md`: sem ele, quem codifica escolhe capabilities, permissões, viewport e "
            "verbos — e é o manifesto que os testes da plataforma leem."))
    for dados in validos[:1]:
        faltam = [k for k in chaves if k not in dados]
        if faltam:
            achados.append(_achado(
                "manifesto-ausente",
                f"O `experiencia.json` do PRD não tem {', '.join(f'`{k}`' for k in faltam)}. Ele vai completo, com "
                f"as {len(chaves)} chaves do contrato da plataforma ({', '.join(f'`{k}`' for k in chaves)}): o "
                "`viewport` diz a casca de aparelho (`{ \"largura\": …, \"altura\": … }`), e os `verbos`, o que cada "
                "verbo significa nesta missão."))
        invalidos = []
        vp = dados.get("viewport")
        if vp is not None and not (isinstance(vp, dict) and all(isinstance(vp.get(k), int) and vp.get(k) > 0
                                                                 for k in ("largura", "altura"))):
            invalidos.append(f"`viewport` é `{json.dumps(vp, ensure_ascii=False)}`, e o schema pede "
                             "`{ \"largura\": <inteiro>, \"altura\": <inteiro> }` (o `\"mobile\"` da exp01ef1b derrubou "
                             "o deploy de 11/09/2026)")
        if "versao" in dados and not _semver(dados.get("versao")):
            invalidos.append(f"`versao` `{dados.get('versao')}` não é `x.y.z`")
        if "unidade" in dados and dados["unidade"] is not None and dados["unidade"] not in (1, 2, 3, 4):
            invalidos.append(f"`unidade` `{dados['unidade']}` fora de 1–4")
        fora = [s for s in _series(dados.get("series")) if s not in SERIES]
        if fora or ("series" in dados and not isinstance(dados["series"], list)):
            invalidos.append(f"`series` {json.dumps(dados.get('series'), ensure_ascii=False)} fora de {list(SERIES)}")
        if "publico" in dados and dados["publico"] not in publicos:
            invalidos.append(f"`publico` `{dados['publico']}` fora de {publicos}")
        if "nome" in dados and not (isinstance(dados["nome"], str) and 0 < len(dados["nome"]) <= 120):
            invalidos.append("`nome` vazio ou com mais de 120 caracteres")
        if invalidos:
            achados.append(_achado(
                "manifesto-invalido",
                "O manifesto não passa no schema do `PUT` do deploy: " + "; ".join(invalidos) + f". Reprova o "
                f"{_TESTE_PUT}."))

    # o id deriva de série + unidade, no manifesto e no frontmatter, e os dois dizem o mesmo
    fm = frontmatter(texto)
    pares = []
    # só onde o documento diz série e unidade: sem elas o manifesto já é `manifesto-ausente`, e o frontmatter antigo
    # sem `serie` não tem de onde derivar
    for dados in validos[:1]:
        if "series" in dados and "unidade" in dados:
            pares.append(("o manifesto", str(dados.get("id") or ""), (_series(dados.get("series")) or [""])[0],
                          dados.get("unidade")))
    if fm.get("slug_experiencia") and fm.get("serie") and fm.get("unidade"):
        pares.append(("o frontmatter", fm["slug_experiencia"], (_series(fm.get("serie")) or [""])[0], fm.get("unidade")))
    divergencias = []
    for onde, id_, serie, unidade in pares:
        if not id_.lower().startswith("exp"):
            continue
        esperado = codigo_da_missao(serie, unidade)
        if id_.lower() != esperado:
            divergencias.append(f"{onde} diz `{id_}` com série `{serie or '—'}` e unidade `{unidade}`"
                                + (f" — o código é `{esperado}`" if esperado else " — série e unidade fora da grade"))
    ids = {p[1].lower() for p in pares if p[1]}
    if len(ids) > 1:
        divergencias.append(f"o manifesto e o frontmatter dão ids diferentes ({', '.join(sorted(ids))})")
    if divergencias:
        achados.append(_achado(
            "id-nao-derivado",
            "O id da missão não é o que a plataforma deriva: " + "; ".join(divergencias) + ". O código sai de "
            "`series[0]` + `unidade` e não se escolhe (ADR-110: `6EF` + 1 = `exp06ef1b`), e a pasta tem o nome do "
            f"id: o {_TESTE_CODIGO} reprova o manifesto cujo `id` não é `codigoDaMissao(series[0], unidade)`."))

    # o id já existe: atualização da existente, com a decisão do PO registrada
    existente = next((e for e in c.get("experiencias") or [] if str(e.get("id") or "").lower() == slug), None)
    if existente:
        faltas = []
        if not _decisao_do_po_provada(texto, datas_po):
            faltas.append("a seção 19 não registra `[ABERTO — dono: PO: substituir a existente ou outro código]` nem "
                          "a decisão do PO com a data de um parecer ou pedido desta sessão")
        atual = _semver(existente.get("versao"))
        for dados in validos[:1]:
            nova = _semver(dados.get("versao"))
            if atual and nova and nova <= atual:
                proxima = f"{atual[0]}.{atual[1] + 1}.0"
                faltas.append(f"o manifesto diz `versao` `{dados.get('versao')}`, que não sobe da publicada "
                              f"`{existente.get('versao')}` — use `{proxima}` no manifesto, no frontmatter e no "
                              "`package.json` (versão em três lugares)")
        if faltas:
            achados.append(_achado(
                "existente-sem-decisao",
                f"A `{slug}` já existe na plataforma («{existente.get('nome')}», v{existente.get('versao')}, porta "
                f"{existente.get('porta')}, `{existente.get('pasta')}`), e " + "; ".join(faltas) + ". A missão é "
                "atualização da existente — a mesma pasta, o mesmo módulo da api, a mesma porta, versão acima, nunca "
                "`pnpm new:exp` — até o PO decidir se ela substitui a publicada ou ganha outro código; sem o "
                "marcador, ele aprova o PRD sem saber que a missão da sala vai ser trocada."))
    return achados


# --------------------------------------------------------------------------- 3. ADR
#: «ADR-150 (proposta)», «ADR nova», «a criar». O `nova:` da seção de DS (`nova:galeriadefotos`) não é marca.
_RE_ADR_MARCADA = re.compile(r"propost|\bnova\b(?!:)|a criar|\[\s*PROPOSTA", re.I)
_RE_ADR_DECLARADA = re.compile(r"^\s*(?:#{1,6}\s+|(?:[-*+]|\d+[.)])\s+\*\*)\s*\**\s*ADR-(\d{1,4})\b(.*)$")


def _citacoes_de_adr(texto: str) -> List[Tuple[int, str, str]]:
    """(número, o que o PRD diz da ADR, onde — a linha, ou a célula) — só onde o PRD a DECLARA: num título (`#### ADR-108: …`), num
    item que abre com ela em negrito (`- **ADR-105:** …`) ou numa célula de coluna «ADR» («ADR necessária»).
    Citada de passagem («os nomes da ADR-80»), a glosa é exemplo, não título, e fica de fora. Duas ADRs juntas
    (`ADR-87 / ADR-88`, `ADR-112/145`) dividem a glosa e também ficam."""
    saida: List[Tuple[int, str, str]] = []
    cab: Optional[List[str]] = None
    cerca = False
    for linha in (texto or "").splitlines():
        if _RE_CERCA_LINHA.match(linha):
            cerca, cab = not cerca, None
            continue
        s = linha.strip()
        if cerca or not s:
            cab = None if not s else cab
            continue
        if s.startswith("|"):
            celulas = [x.strip() for x in re.split(r"(?<!\\)\|", s.strip("|"))]
            if set("".join(celulas)) <= set("-: "):
                continue
            if cab is None:
                cab = [_norm_simples(x) for x in celulas]
                continue
            for k, cel in enumerate(celulas):
                if k < len(cab) and re.search(r"\badr\b", cab[k]):
                    for m in _RE_ADR.finditer(cel):
                        saida.append((int(m.group(1)), cel[m.end():], cel))
            continue
        cab = None
        m = _RE_ADR_DECLARADA.match(linha)
        if m:
            saida.append((int(m.group(1)), m.group(2), linha))
    return saida


def conferir_adr(texto: str, c: Dict[str, Any]) -> List[Dict[str, str]]:
    """A ADR citada existe com aquele assunto, e a que ainda não existe está marcada como proposta.

    `validar_contrato` já pega a ADR acima da próxima (`adr-inexistente`) e a proposta com número que não é o da
    próxima (`adr-numero-errado`). Faltava: (a) a PRÓXIMA citada como se existisse — «**ADR-150:** Recurso de
    podcast…» na exp01ef1b, contra a base de 06/10 (última 149); (b) a ADR existente declarada com outro
    assunto. Medido nas sete sessões, contra as duas bases: cinco declarações com zero radical em comum com o
    título do contrato, todas decisões novas sob número tomado — ADR-108 «Seção de Galeria de Fotos no DS»
    (exp01ef1b, coluna «ADR necessária»), ADR-108/109 «Sincronização… por Polling» e «Fallback Determinístico»
    (exp06ef1b, títulos `####`) e ADR-108/109 «Sincronização… de Redação» e «Validação Permutacional»
    (exp04ef1b, itens em negrito); e nenhuma declaração certa reprovada — as outras 13 (14 na base viva, onde a
    ADR-150 já existe) dividem pelo menos um radical com o título: «Quota diária de IA como dado» × «A quota de
    IA é dado…». A citação de passagem e a glosa de duas ADRs juntas ficam de fora (`_citacoes_de_adr`)."""
    adr = c.get("adr") or {}
    ultima, proxima = int(adr.get("ultima") or 0), int(adr.get("proxima") or 0)
    titulos = {int(re.sub(r"\D", "", k) or 0): v for k, v in (adr.get("titulos") or {}).items()}
    achados: List[Dict[str, str]] = []
    if not ultima:
        return achados
    sem_marca: List[int] = []
    for linha in texto.splitlines():
        if not _afirmativa(linha) or _RE_ADR_MARCADA.search(linha):
            continue
        for m in _RE_ADR.finditer(linha):
            n = int(m.group(1))
            if ultima < n <= proxima and n not in sem_marca:
                sem_marca.append(n)
    if sem_marca:
        achados.append(_achado(
            "adr-sem-proposta",
            f"{', '.join(f'`ADR-{n}`' for n in sem_marca)} ainda não existe: a última ADR da plataforma é a {ultima} "
            f"(contrato da plataforma). Se é decisão nova desta missão, escreva `ADR-{proxima} (proposta)` e registre-a "
            "na seção 19 com dono `plataforma`; se o texto atribui à plataforma uma decisão que ela não tomou, tire o "
            "número — quem codifica vai procurar a ADR no LaTeX e não vai achar."))
    divergentes: List[str] = []
    for n, glosa, linha in _citacoes_de_adr(texto):
        if n > ultima or n not in titulos or _RE_ADR_MARCADA.search(linha):
            continue
        if re.search(r"ADR-\d", glosa) or re.match(r"\s*(?:/|,|\be\b)\s*(?:ADR-)?\d", glosa):
            continue
        dito = radicais(glosa) - _GENERICAS
        if dito and not dito & (radicais(titulos[n]) - _GENERICAS):
            item = f"`ADR-{n}` «{re.sub(r'[*`]+', '', glosa).strip(' :—–-()')[:80]}» — no contrato, «{titulos[n]}»"
            if item not in divergentes:
                divergentes.append(item)
    if divergentes:
        achados.append(_achado(
            "adr-titulo-divergente",
            "ADR existente declarada com outro assunto: " + "; ".join(divergentes) + ". O número é da ADR do "
            f"contrato: se o PRD fala dela, use o título dela; se é decisão nova desta missão, é a `ADR-{proxima} "
            "(proposta)` — duas decisões com o mesmo número viram duas seções no LaTeX e uma referência errada em "
            "todo arquivo que cita a ADR."))
    return achados


# --------------------------------------------------------------------------- 4. capacidade que a plataforma não tem
_RE_OFFLINE = re.compile(
    r"service[\s-]?worker|\bPWA\b|workbox|offline[\s-]first|"
    r"\b(?:oper[ae]r?|funcion[ae]r?|funcione|rod[ae]r?|jog[ae]r?|continu[ae]r?|carreg[ae]r?)\b[^\n.;|]{0,40}\boffline\b|"
    r"\boffline\b[^\n.;|]{0,30}\b(?:com|via|em)\s+cache\b|"
    r"\bcache\s+local\b|\bIndexedDB\b|\bbuffer\s+local\b", re.I)
_RE_REQUISITO = re.compile(r"\b(?:RF|RNF(?:-[A-Z]+)?|US)-\d{1,3}\b")


def conferir_capacidades(texto: str) -> List[Dict[str, str]]:
    """Offline, Service Worker e cache local pedidos como se a plataforma os tivesse.

    O SDK não tem Service Worker nem cache persistente: a fila de telemetria offline é em memória e some com
    a aba («IndexedDB é o próximo passo», `agents-sdk.md` da base), e toda jogada é rota do servidor — o
    gabarito mora lá. Medido nas sete sessões: a exp01ef1b pedia «funcione offline» (US-09), «operar offline com
    cache local» (RF-019, P0) e «operar offline… buffer local» (RNF-003) — três requisitos, ⛔; a exp07ef1b
    mitigava a queda de rede com «IndexedDB… com ressincronização» numa tabela de riscos — ⚠️. Os estados de
    erro (`ST_OFFLINE`, `MODO_OFFLINE_FICTICIO`, «Estados: offline») são a degradação certa e não casam."""
    requisitos: List[str] = []
    outros: List[str] = []
    for secao, linha, cerca in _linhas_com_secao(texto):
        if cerca or secao == 3 or not _afirmativa(linha):
            continue
        m = _RE_OFFLINE.search(linha)
        if not m or _RE_NEGACAO.search(_RE_ENFASE.sub("", linha[:m.start()])):
            continue
        ids = _RE_REQUISITO.findall(linha)
        trecho = (", ".join(dict.fromkeys(ids)) + ": " if ids else "") + f"«{m.group(0).strip()}»"
        (requisitos if ids or secao in (8, 9) else outros).append(trecho)
    achados: List[Dict[str, str]] = []
    explica = ("O SDK não tem Service Worker nem cache persistente: a fila de telemetria offline é em memória e some "
               "com a aba (`packages/sdk/AGENTS.md`), e toda jogada é rota do servidor, onde mora o gabarito. A "
               "degradação certa é o estado de erro na voz da ficção e a reentrada pelo servidor (seção 6); se a "
               "mecânica precisa mesmo de offline, é `[PENDÊNCIA PLATAFORMA]` com dono `plataforma` na seção 15.1 e "
               "na 19 — nunca um Service Worker escrito dentro da missão.")
    if requisitos:
        achados.append(_achado(
            "capacidade-inexistente",
            f"O PRD exige o que a plataforma não tem — {'; '.join(dict.fromkeys(requisitos))}. " + explica))
    if outros:
        achados.append(_achado(
            "capacidade-inexistente",
            f"O PRD conta com o que a plataforma não tem — {'; '.join(dict.fromkeys(outros))}. " + explica,
            severidade="atencao"))
    return achados


# --------------------------------------------------------------------------- 5. modelo de IA
_RE_MODELO_IA = re.compile(
    r"\b(gemini|imagen)[\s_-]*(\d+(?:\.\d+)?)((?:[\s_-]+(?:pro|flash|ultra|nano|lite|image|preview|exp|tts))*)\b", re.I)


def conferir_modelo_de_ia(texto: str, c: Dict[str, Any]) -> List[Dict[str, str]]:
    """O modelo de IA que o PRD nomeia é o do contrato (`ia.modelo_padrao`, `ia.modelo_imagem_padrao`).

    Medido nas sete sessões: «Vertex Gemini 1.5 Flash» (exp07ef1b, RNF de custo e provedor), «Gemini 1.5 Pro»
    (exp06ef1b, teto de tokens e C4), «Gemini 3.6 Flash» (exp01ef1b e exp09ef1b, certo). ⚠️ e não ⛔: o
    `AiRequest.modelo` escolhe a família (`padrao`/`longo`), não o nome, e o número errado erra o custo e o
    teto, não o código. Fica de fora a §3 (o que não se faz: «Imagen 3» na V2 da exp09ef1b) e o modelo de voz
    (`…-tts`), que é do módulo de podcast."""
    ia = c.get("ia") or {}
    aceitos = {str(v).lower() for v in ia.values() if v}
    if not aceitos:
        return []
    errados: Dict[str, str] = {}
    for secao, linha, cerca in _linhas_com_secao(texto):
        if secao == 3 or not _afirmativa(linha):
            continue
        for m in _RE_MODELO_IA.finditer(linha):
            nome = "-".join([m.group(1).lower(), m.group(2)] + re.findall(r"[a-z]+", m.group(3).lower()))
            if "tts" in nome or nome in aceitos:
                continue
            errados.setdefault(nome, m.group(0).strip())
    if not errados:
        return []
    return [_achado(
        "modelo-ia-divergente",
        f"O PRD nomeia {', '.join(f'«{v}»' for v in errados.values())}, e a plataforma usa `{ia.get('modelo_padrao')}` "
        f"para texto e `{ia.get('modelo_imagem_padrao')}` para imagem (contrato da plataforma, `ia`). A missão escolhe "
        "a família (`AiRequest.modelo`: `padrao` ou `longo`), nunca o nome; teto de tokens e custo por chamada saem do "
        "modelo do contrato.", severidade="atencao")]


# --------------------------------------------------------------------------- 6. registros do hub e da api
#: (o que é, o que o PRD escreve quando o traz, o teste da plataforma que quebra sem ele — vazio: nenhum quebra).
#: Lido no código da plataforma em 07/10/2026 (6587824e). Os três primeiros reprovam a missão publicada no
#: catálogo sem o registro; os outros só aparecem em produção ou no e2e — ⚠️.
REGISTROS = (
    ("o guia da aula (`apps/hub/lib/entre-redes/guias/<expId>.ts` e a linha em `guias/index.ts`)",
     r"guias/(?:{slug}|<\s*expId\s*>|«\s*expId\s*»|\$\{{\s*expId\s*\}})\.ts",
     "`apps/hub/lib/entre-redes/guias/index.test.ts › toda missão disponível com experiência tem guia`"),
    ("o ramo da missão no despachante da ficha (`…/professor/entre-redes/[ano]/[unidade]/page.tsx` + "
     "`missao-<slug>.tsx`)",
     r"\[unidade\]/page\.tsx|\bmissao-[a-z0-9-]+\.tsx|despachante[- ]da[- ]ficha",
     "`apps/hub/lib/entre-redes/despachante-da-ficha.test.ts › toda missão publicada com experiência tem ramo próprio`"),
    ("o ramo da missão no despachante dos resultados (`…/[unidade]/resultados/page.tsx` + `resultados-<slug>.tsx`)",
     r"resultados/page\.tsx|\bresultados-[a-z0-9-]+\.tsx",
     "`apps/hub/lib/rotas-da-missao.test.ts › todo corpo que linka /resultados tem ramo no despachante`"),
    ("a entrada no catálogo da trilha (`apps/hub/lib/entre-redes/catalogo.ts`, `MISSAO_<NOME>` em "
     "`MISSOES_PUBLICADAS`)", r"entre-redes/catalogo\.ts|MISSOES_PUBLICADAS|\bMISSAO_[A-Z0-9_]+\b", ""),
    ("o prefixo do módulo em `PREFIXOS_PERMITIDOS` do BFF (`apps/hub/app/api/plataforma/[...path]/route.ts`) — ou "
     "por que a tela do professor é server-side", r"PREFIXOS_PERMITIDOS", ""),
    ("a liberação de demo em `LIBERACOES_DE_DEMO` (`apps/api/prisma/catalogo-e-liberacoes.ts`)",
     r"LIBERACOES_DE_DEMO|catalogo-e-liberacoes", ""),
    ("a porta em `apps/hub/lib/experiencias-dev.ts`", r"experiencias-dev\.ts", ""),
    ("a origem da porta em `CORS_ORIGINS` (`.env.example` e `docker-compose.dev.yml`)", r"CORS_ORIGINS", ""),
)
_TESTE_EQUIPES = "`apps/api/tests/equipes-regras.spec.ts`"


def conferir_registros(texto: str, slug: str, c: Dict[str, Any]) -> List[Dict[str, str]]:
    """Missão nova: os registros do hub e da api que a §17 tem de nomear.

    Só missão NOVA: a que já está na tabela de experiências do contrato já tem guia, ficha e resultados. Medido
    nas sete sessões: nenhum PRD nomeava o guia, o despachante da ficha nem o dos resultados — e a exp09ef1b,
    a única nova delas, quebraria os três testes ao ser publicada no catálogo. E as listas
    `EXPERIENCIAS_COM_EQUIPE`/`_COM_ATIVIDADE` estão escritas à mão em `equipes-regras.spec.ts`: missão que
    entra numa delas sem o teste mudar junto reprova a suíte da api (nenhum dos sete PRDs as citava)."""
    if not _RE_ID_MISSAO.match(slug or ""):
        return []
    achados: List[Dict[str, str]] = []
    nova = not any(str(e.get("id") or "").lower() == slug for e in c.get("experiencias") or [])
    if nova:
        quebra, avisa = [], []
        for o_que, padrao, teste in REGISTROS:
            if re.search(padrao.format(slug=re.escape(slug)), texto, re.I):
                continue
            (quebra if teste else avisa).append(f"{o_que} — sem ele reprova o {teste}" if teste else o_que)
        if quebra:
            achados.append(_achado(
                "registro-da-plataforma-ausente",
                f"A `{slug}` é missão nova, e a §17.3 não nomeia: " + "; ".join(quebra) + ". Cada um é arquivo a "
                "criar ou a tocar com o caminho completo, como na tabela «Hub do professor» do gabarito."))
        if avisa:
            achados.append(_achado(
                "registro-da-plataforma-ausente",
                f"A `{slug}` é missão nova, e o plano não nomeia: " + "; ".join(avisa) + ". Nenhum teste quebra, "
                "mas sem eles a missão some do catálogo, a tela do professor recebe 404 `bff-prefixo-recusado`, a "
                "turma de demonstração não a recebe ou a api recusa a origem da porta de dev.", severidade="atencao"))
    equipes = c.get("equipes") or {}
    for lista, chave in (("EXPERIENCIAS_COM_EQUIPE", "com_equipe"), ("EXPERIENCIAS_COM_ATIVIDADE", "com_atividade")):
        if (re.search(rf"\b{lista}\b", texto) and slug not in (equipes.get(chave) or [])
                and not re.search(r"equipes-regras\.spec", texto)):
            achados.append(_achado(
                "registro-da-plataforma-ausente",
                f"O PRD põe a `{slug}` em `{lista}` e não manda atualizar o {_TESTE_EQUIPES}, que lista as missões à "
                f"mão ({', '.join(equipes.get(chave) or [])}): a suíte da api reprova."))
    return achados


# --------------------------------------------------------------------------- tudo
def validar_prd(texto: str, slug: str = "", datas_po: Optional[Set[str]] = None) -> List[Dict[str, str]]:
    """O que só o PRD traz para a plataforma, conferido contra o contrato da base e os moldes.

    Sem base, nada: a conferência é contra o contrato, e sem ele não há o que conferir (como `validar_contrato`).
    O modelo de dados não depende do contrato e é conferido sempre.
    """
    achados = conferir_modelo_de_dados(texto or "") + conferir_capacidades(texto or "")
    try:
        c = base_plataforma.contrato()
    except base_plataforma.BaseIndisponivel:
        return achados
    slug = (slug or slug_do_prd(texto or "")).lower()
    return (achados + conferir_manifesto(texto or "", slug, c, datas_po) + conferir_adr(texto or "", c)
            + conferir_modelo_de_ia(texto or "", c) + conferir_registros(texto or "", slug, c))
