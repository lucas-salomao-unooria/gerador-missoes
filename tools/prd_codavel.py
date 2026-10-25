"""O PRD dá para codar sem perguntar? As cinco lacunas que a auditoria de 08/10/2026 achou, conferidas em código.

O gabarito (`references/prd-padrao-ouro.md`) já pedia contrato por rota em Zod, tabela de erros, ficha de evidência
com regra sobre colunas, DDL com o bloco manual e prompt de IA no servidor — e nada conferia. Lido como quem vai
codar, o PRD da exp09ef1b (o último aprovado) deixava em aberto exatamente isso: `payload: Record<string, unknown>`,
schemas citados sem definição, `DELETE` para zerar, só `erDiagram` no modelo de dados, nível gravado em
`score_ef09co07` na tabela da missão, régua sem predicado, o motor do chat sem árvore de intenções e a IA do preparo
sem prompt nem schema de saída.

Cada regra procura a estrutura pelo cabeçalho da tabela e pelo bloco de código, dentro da seção do gabarito
(11, 12, 14) — não pelo número da subseção, que o redator renumera. Dono: `prd-writer`, exceto a árvore de
intenções do chat, que é do banco de conteúdo.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple

AGENTE = "prd-codavel"
DONO = "prd-writer"

#: Rotas do molde (gabarito §12.1): o fragmento que identifica cada uma no texto da seção 12.
ROTAS_DO_MOLDE = (
    ("sessão do estudante", r"/sessao\b"),
    ("gate da turma", r"/gate\b"),
    ("turmas do professor", r"/turmas\b"),
    ("painel da turma", r"/painel\b"),
    ("zerar (rodada nova)", r"/zerar\b"),
    ("pacotes da turma", r"/pacotes\b"),
    ("pôr no ar", r"/em-andamento\b"),
    ("material do professor", r"/material\b"),
)
#: Tipos que dizem "qualquer coisa" num contrato: quem codifica decide sozinho o que trafega.
_RE_TIPO_FROUXO = re.compile(r"Record<\s*string\s*,\s*(?:unknown|any)\s*>|:\s*any\b|\bz\.(?:any|unknown)\(\)|"
                             r":\s*unknown\b|\bas\s+any\b")
_RE_BLOCO = re.compile(r"```([\w-]*)[^\n]*\n(.*?)```", re.S)
_RE_ZOD = re.compile(r"\bz\.object\s*\(")
_RE_LINHA_API = re.compile(r"^\s*\|\s*\**`?API-\w+", re.M)
#: Coluna de nível de habilidade em tabela da missão — o nível mora em `evidencias_marcas` (gabarito §11).
_RE_COLUNA_DE_NIVEL = re.compile(r"^\s*[`\"]?((?:score|nivel|nota)_\w+)[`\"]?\s+[A-Za-z]", re.M | re.I)
_TIPOS_FICHA = ("acao", "multipla_escolha")
_RE_CHAT_LIVRE = re.compile(r"ia\s+simulada|ia\s+que\s+(?:fala|responde|conversa)|respostas?\s+(?:da|do)\s+(?:ia|chat|bot|assistente)|"
                            r"campo\s+de\s+(?:texto|mensagem)\s+livre|(?:estudante|crian[çc]a|aluno)\s+digita", re.I)
_RE_IA_NO_PREPARO = re.compile(r"gerar-conteudo|generateJson|\bia-[a-z0-9]+|gera(?:r|ção)\s+(?:com|pela|por)\s+ia", re.I)


def _norm(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")


def _secao(texto: str, numero: int) -> str:
    from tools.conteudo_aprovado import secao

    return secao(texto or "", numero) or ""


def _tabelas(texto: str) -> List[List[List[str]]]:
    from tools.consistencia import _tabelas as tabelas

    return tabelas(texto)


def _tabela_com(texto: str, *colunas: str) -> Optional[List[List[str]]]:
    """A primeira tabela cujo cabeçalho tem todas as colunas (sem acento, por prefixo)."""
    for t in _tabelas(texto):
        cab = [_norm(c).strip("*` ") for c in t[0]]
        if all(any(c.startswith(col) for c in cab) for col in colunas):
            return t
    return None


def _coluna(tabela: List[List[str]], nome: str) -> Optional[int]:
    cab = [_norm(c).strip("*` ") for c in tabela[0]]
    return next((i for i, c in enumerate(cab) if c.startswith(nome)), None)


def _codigo(texto: str) -> str:
    """Só o que está dentro de blocos de código."""
    return "\n".join(m.group(2) for m in _RE_BLOCO.finditer(texto or ""))


def _achado(achados: List[Dict[str, str]], severidade: str, codigo: str, resumo: str, dono: str = DONO) -> None:
    achados.append({"severidade": severidade, "codigo": codigo, "etapa": "dev", "agente_responsavel": dono,
                    "resumo": resumo})


def codigos_do_bloco11(spec: str) -> List[str]:
    from tools.bncc import CODIGO_RE, secao_bloco

    return list(dict.fromkeys(CODIGO_RE.findall(secao_bloco(spec or "", 11) or "")))


# --------------------------------------------------------------------------- 12. contratos de API
def _rotas(prd: str, achados: List[Dict[str, str]]) -> None:
    s12 = _secao(prd, 12)
    if not s12.strip():
        _achado(achados, "bloqueio", "secao-12-ausente", "O PRD não tem a seção 12 (Contratos de API): quem codifica "
                "inventa as rotas, os corpos e os erros.")
        return
    faltam = [nome for nome, rx in ROTAS_DO_MOLDE if not re.search(rx, s12)]
    if faltam:
        _achado(achados, "bloqueio", "rota-do-molde-ausente",
                f"A seção 12 não declara as rotas do molde: {', '.join(faltam)}. São as que toda missão tem (gabarito "
                "§12.1, molde do Júri); sem a linha `API-`, quem codifica decide o caminho, o papel e o corpo.")
    if any("/zerar" in l and re.search(r"\bDELETE\b", l) and not re.search(r"\b(?:nunca|n[ãa]o|sem)\b", l, re.I)
           for l in s12.splitlines()):
        _achado(achados, "bloqueio", "zerar-com-delete",
                "Zerar é `POST …/zerar` (rodada nova; a linha da rodada anterior fica), nunca `DELETE`.")
    if not _RE_LINHA_API.search(s12):
        _achado(achados, "bloqueio", "rotas-sem-id", "A seção 12 não tem a tabela de rotas com uma linha `API-xxx` por "
                "rota: a cobertura, o teste e a tarefa não têm como apontar para a rota.")
    codigo = _codigo(s12)
    if not _RE_ZOD.search(codigo):
        _achado(achados, "bloqueio", "contrato-sem-zod",
                "A seção 12 não tem nenhum `z.object(…)` em bloco de código: corpo e resposta das rotas ficam em prosa, e "
                "quem codifica escolhe os campos. O gabarito pede o Zod inline, cada campo com tipo e limite.")
    frouxos = sorted({m.group(0).strip() for m in _RE_TIPO_FROUXO.finditer(codigo + "\n" + s12)})
    if frouxos:
        _achado(achados, "bloqueio", "contrato-frouxo",
                f"O contrato da seção 12 aceita qualquer coisa: {', '.join(f'`{f}`' for f in frouxos)}. Declare os "
                "campos (o PRD da exp09ef1b tinha `payload: Record<string, unknown>` no evento operacional).")
    if not (_tabela_com(s12, "codigo", "status") or _tabela_com(s12, "erro", "status")):
        _achado(achados, "bloqueio", "erros-sem-tabela",
                "A seção 12 não tem a tabela de erros `código → status` (o `CodigoErro` de `<modulo>/erros.ts`): "
                "quem codifica inventa os códigos, e a tela não sabe o que mostrar.")
    if not re.search(r"idempot|segundo\s+clique|\block\b|advisory", s12, re.I):
        _achado(achados, "atencao", "sem-idempotencia",
                "A seção 12 não diz o que o segundo clique devolve nem qual lock protege a jogada e o gate.")
    if not re.search(r"rate\s*-?\s*limit|rateLimit|\b429\b", s12, re.I):
        _achado(achados, "atencao", "sem-rate-limit", "A seção 12 não declara o `rateLimit` por usuário das rotas.")


# --------------------------------------------------------------------------- 12.2 IA no preparo
def _ia(prd: str, achados: List[Dict[str, str]]) -> None:
    s12 = _secao(prd, 12)
    if not (_RE_IA_NO_PREPARO.search(s12) or _RE_IA_NO_PREPARO.search(_secao(prd, 8))):
        return
    tabela = _tabela_com(s12, "chamada", "prompt") or _tabela_com(s12, "chamada", "saida")
    if tabela is None:
        _achado(achados, "bloqueio", "ia-sem-tabela",
                "O PRD gera conteúdo com IA, e a seção 12 não tem a tabela «Chamada · Rota · Entrada · Saída · Prompt · "
                "Modelo · Quota · Fallback · Moderação» (gabarito §12.2).")
        return
    # o prompt em bloco de texto, ou já como a constante do `prompts.ts` (`export const PROMPT_X = \`…\``) — o PRD da
    # exp09ef1b gerado em 08/10/2026 escreveu assim, e é a forma que vai para o arquivo
    prompts = [m.group(2) for m in _RE_BLOCO.finditer(s12)
               if m.group(1).lower() in ("", "text", "txt", "md", "markdown", "prompt") and len(m.group(2).split()) >= 40]
    prompts += [t for t in re.findall(r"const\s+\w*PROMPT\w*\s*(?::\s*string\s*)?=\s*`([^`]*)`", _codigo(s12), re.I)
                if len(t.split()) >= 40]
    linhas = len(tabela) - 1
    if len(prompts) < linhas:
        _achado(achados, "bloqueio", "ia-sem-prompt",
                f"A tabela de IA tem {linhas} chamada(s) e o PRD traz o texto de {len(prompts)} prompt(s). O prompt vai "
                "para `apps/api/src/<modulo>/prompts.ts`: escreva o texto de cada um num bloco de código (instrução, com "
                "o recorte do professor delimitado como dado) — sem ele, quem codifica escreve o prompt.")
    col = _coluna(tabela, "saida")
    if col is not None:
        definidos = set(re.findall(r"(?:const|export\s+const)\s+(\w+)\s*=\s*z\.", _codigo(prd)))
        for linha in tabela[1:]:
            for n in re.findall(r"\b(\w+Schema)\b", linha[col] if col < len(linha) else ""):
                if n not in definidos:
                    _achado(achados, "bloqueio", "ia-saida-sem-schema",
                            f"A saída da IA `{n}` não está definida em Zod no PRD: o `validar` do `generateJson` não tem o "
                            "que conferir, e a homologação aceita o que vier.")


# --------------------------------------------------------------------------- 11. modelo de dados
def _modelo(prd: str, achados: List[Dict[str, str]]) -> None:
    s11 = _secao(prd, 11)
    if not s11.strip():
        _achado(achados, "bloqueio", "secao-11-ausente", "O PRD não tem a seção 11 (Modelo de dados).")
        return
    codigo = "\n".join(m.group(2) for m in _RE_BLOCO.finditer(s11) if m.group(1).lower() in ("sql", "prisma", "", "postgresql"))
    if not re.search(r"CREATE\s+TABLE|^\s*model\s+\w+\s*\{", codigo, re.I | re.M):
        _achado(achados, "bloqueio", "modelo-sem-ddl",
                "A seção 11 não tem DDL (`CREATE TABLE` em bloco `sql`) nem `model` Prisma: prosa e `erDiagram` não dizem "
                "tipo, nulidade, FK nem CHECK, e a conferência das chaves da plataforma não tem o que ler.")
        return
    nivel = sorted({m.group(1) for m in _RE_COLUNA_DE_NIVEL.finditer(codigo)})
    if nivel:
        _achado(achados, "bloqueio", "nivel-em-tabela-da-missao",
                f"Coluna de nível na tabela da missão: {', '.join(f'`{c}`' for c in nivel)}. O nível mora em "
                "`evidencias_marcas` (a missão grava o que a criança fez e chama `EvidenciasService.marcar`).")
    if not re.search(r"FORCE\s+ROW\s+LEVEL\s+SECURITY", s11, re.I):
        _achado(achados, "atencao", "sem-force-rls",
                "A seção 11 não traz o bloco manual da migration com `ENABLE` + `FORCE ROW LEVEL SECURITY` e a policy de "
                "`escola_id`.")
    if not re.search(r"GRANT\b[^\n]*app_runtime", s11, re.I):
        _achado(achados, "atencao", "sem-grant", "A seção 11 não concede as tabelas novas à role `app_runtime`.")


def colunas_declaradas(prd: str) -> Set[str]:
    from tools.consistencia import _declaracoes

    return {c for cols in _declaracoes(_secao(prd, 11) or prd).values() for c in cols}


# --------------------------------------------------------------------------- 14.2 ficha de evidência
def _ficha(prd: str, spec: str, achados: List[Dict[str, str]]) -> None:
    s14 = _secao(prd, 14)
    tabela = _tabela_com(s14, "habilidade", "marcador", "tipo") if s14 else None
    if tabela is None:
        _achado(achados, "bloqueio", "ficha-ausente",
                "A seção 14 não tem a ficha de evidência «Habilidade · Marcador · Tipo · Pergunta · Regra · Nível · Grava "
                "na transação de · Critério» (gabarito §14.2): o servidor não sabe calcular o nível de ninguém.")
        return
    i_hab, i_tipo, i_regra = _coluna(tabela, "habilidade"), _coluna(tabela, "tipo"), _coluna(tabela, "regra")
    colunas = colunas_declaradas(prd)
    from tools.consistencia import _declaracoes

    s11 = _secao(prd, 11) or prd
    jsonb = {c for cols in _declaracoes(s11).values() for c, fams in cols.items() if "json" in fams}
    cobertas: Set[str] = set()
    for linha in tabela[1:]:
        def cel(i: Optional[int]) -> str:
            return linha[i] if i is not None and i < len(linha) else ""
        cobertas |= set(re.findall(r"E[FM]\d{2}[A-Z]{2}\d{2,3}", cel(i_hab)))
        tipo = _norm(cel(i_tipo)).strip("*` ")
        if tipo not in _TIPOS_FICHA:
            _achado(achados, "bloqueio", "ficha-tipo-invalido",
                    f"Ficha: tipo «{cel(i_tipo)}» na linha de {cel(i_hab)[:40]}. Só `acao` ou `multipla_escolha`.")
        regra = cel(i_regra)
        if tipo == "acao" and "[PROPOSTA" in regra:
            # regra em proposta: o servidor ainda não sabe calcular o nível — o PO decide, e o achado não some
            _achado(achados, "atencao", "regra-em-proposta",
                    f"Ficha de {cel(i_hab)[:40]}: a regra é `[PROPOSTA …]`. Sem a decisão do PO, o servidor não sabe "
                    "calcular o nível desta habilidade.")
        if tipo == "acao" and "[PROPOSTA" not in regra:
            # Item 4 da Etapa 2 (Plano Padrão Ouro): cada ramo da regra de ação (antes do →) precisa ler coluna
            # e expressar predicado formal (OP valor), e não apenas citar palavra solta
            operadores = r"(?:=|>=|<=|>|<|!=|<>|\bBETWEEN\b|\bIN\b|\bLIKE\b|\bILIKE\b|\bIS\b)"
            ramos = [r.strip() for r in regra.strip("`").split(";")]
            erro_encontrado = False
            for ramo in ramos:
                if not ramo or erro_encontrado:
                    continue
                partes = re.split(r"→|->", ramo, maxsplit=1)
                condicao = partes[0].strip()
                if re.search(r"\b(?:sem\s+a[cç][aã]o|fallback|default|demais|outro[s]?|null)\b", condicao, re.I):
                    continue
                citadas = {c.lower() for c in re.findall(r"\b([a-z][a-z0-9_]*)\b", condicao)}
                intersecao = citadas & colunas
                if not intersecao:
                    _achado(achados, "bloqueio", "regra-sem-coluna",
                            f"Ficha de {cel(i_hab)[:40]}: a condição «{condicao[:80]}» não lê nenhuma coluna declarada na seção 11. "
                            "A regra é um predicado sobre o que o servidor gravou (`cadeia_tentativas = 1 → atingiu`); o que "
                            "não vira predicado é `[PROPOSTA — validar com PO: …]`, e a coluna que falta entra na seção 11.")
                    erro_encontrado = True
                    break
                tem_predicado = False
                for c in intersecao:
                    padrao = rf"\b{re.escape(c)}\b(?:\s*[:.]\s*\w+|\s*->>\s*['\"\w]+)?\s*{operadores}"
                    padrao_json = rf"\b{re.escape(c)}\s*:\s*\w+\s*{operadores}"
                    if re.search(padrao, condicao, re.IGNORECASE) or re.search(padrao_json, condicao, re.IGNORECASE):
                        tem_predicado = True
                        break
                # coluna JSONB: a chave lida precisa estar no DEFAULT ou na descrição da seção 11 (plano 2.4)
                for c in intersecao & jsonb:
                    for chave in re.findall(rf"\b{re.escape(c)}\s*(?:[:.]\s*|->>?\s*['\"]?)(\w+)", condicao, re.I):
                        if not re.search(rf"\b{re.escape(chave)}\b", s11, re.I):
                            _achado(achados, "bloqueio", "regra-chave-jsonb-ausente",
                                    f"Ficha de {cel(i_hab)[:40]}: a condição lê `{c}` → `{chave}`, mas a seção 11 não "
                                    f"declara a chave `{chave}` na coluna JSONB `{c}` (nem no DEFAULT nem na descrição). "
                                    "O servidor grava o que o modelo de dados diz; chave fora dele nunca existe.")
                            erro_encontrado = True
                if erro_encontrado:
                    break
                if not tem_predicado:
                    _achado(achados, "bloqueio", "regra-sem-predicado",
                            f"Ficha de {cel(i_hab)[:40]}: a condição «{condicao[:80]}» cita coluna mas não expressa um predicado "
                            "formal (`coluna OP valor`, `coluna: chave OP valor`, `coluna->>'chave' OP valor`). "
                            "Palavras soltas sem operador de comparação não definem como o servidor afere a evidência.")
                    erro_encontrado = True
                    break
    faltam = sorted(set(codigos_do_bloco11(spec)) - cobertas)
    if faltam:
        _achado(achados, "bloqueio", "ficha-sem-habilidade",
                f"A ficha de evidência não tem linha para {', '.join(f'`{c}`' for c in faltam)} (bloco 11 da spec): o "
                "painel do professor fica sem o nível dessas habilidades.")


# --------------------------------------------------------------------------- motor do chat simulado
def precisa_de_intencoes(spec: str, prd: str = "") -> bool:
    """A criança escreve para um interlocutor simulado: a resposta dele tem de vir de uma árvore fechada.

    A seção do DS sozinha não basta — um WhatsApp simulado só com botões não tem o que interpretar —: vale a spec ou o
    PRD dizendo que há IA simulada, resposta do chat, ou texto que o estudante digita."""
    return bool(_RE_CHAT_LIVRE.search(spec or "") or _RE_CHAT_LIVRE.search(prd or ""))


def validar_intencoes(banco: str, spec: str, prd: str = "") -> List[Dict[str, str]]:
    """O banco de conteúdo traz a árvore de intenções do chat: gatilhos fechados e resposta por estado."""
    achados: List[Dict[str, str]] = []
    if not precisa_de_intencoes(spec, prd):
        return achados
    tabela = _tabela_com(banco or "", "intenc", "gatilho", "resposta")
    if tabela is None:
        _achado(achados, "bloqueio", "chat-sem-intencoes",
                "A missão tem conversa com um interlocutor simulado, e o banco de conteúdo não traz a tabela «Intenção · "
                "Gatilhos · Resposta (por estado) · Efeito». Sem ela, quem codifica inventa o que o chat responde — na "
                "exp09ef1b o PRD citava um `base_dados_conselho.json` que ninguém escreveu, e os gatilhos divergiam "
                "entre o PRD (4 palavras) e o brief (6).", dono="banco-conteudo")
        return achados
    i_gat = _coluna(tabela, "gatilho")
    # a linha «sem correspondência» é a resposta de quando nenhum gatilho casa: não tem gatilho, por definição
    vazias = [l[0] for l in tabela[1:] if not re.search(r"sem\s+correspond|fallback|nenhum", _norm(l[0]))
              and (i_gat is None or i_gat >= len(l) or not re.findall(r"\w+", l[i_gat]))]
    if vazias:
        _achado(achados, "bloqueio", "intencao-sem-gatilho",
                f"Intenção sem gatilho na árvore do chat: {', '.join(v[:40] for v in vazias[:6])}.", dono="banco-conteudo")
    if not re.search(r"sem\s+correspond|fallback|nao\s+reconhec|nenhum\s+gatilho|default", _norm(banco or "")):
        _achado(achados, "atencao", "intencao-sem-fallback",
                "A árvore do chat não diz o que ele responde quando nenhum gatilho casa.", dono="banco-conteudo")
    if prd and not re.search(r"inten[çc][ãa]o|inten[çc][õo]es", prd, re.I):
        _achado(achados, "bloqueio", "prd-sem-intencoes",
                "O PRD não remete à árvore de intenções do banco de conteúdo: diga onde ela vive (`conteudo.ts`, no "
                "servidor) e se a detecção roda no cliente ou no servidor.")
    return achados


# --------------------------------------------------------------------------- handoff → PRD
_RE_TABELA_DA_MISSAO = re.compile(r"\b(exp\d{2}e[fm]\d[ab]_[a-z0-9_]+)\b")
_RE_ROTA = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\s+`?(/[\w/:{}.-]+)")


#: `p1..p3` na tabela de-para da seção 19 do PRD vale por `p1`, `p2` e `p3` (exp06ef1b-53e011b6, 10/10/2026).
_RE_INTERVALO_NA_ROTA = re.compile(r"([A-Za-z_]*)(\d+)\.\.\1?(\d+)")


def _rotas_normalizadas(texto: str) -> Set[Tuple[str, Tuple[str, ...]]]:
    """`(MÉTODO, segmentos)` de cada rota do texto, com o parâmetro normalizado (`:id`, `:turmaId`, `{id}` → `{p}`) e o
    intervalo `p1..p3` expandido."""
    from tools.rotas_plataforma import _normalizar

    saida: Set[Tuple[str, Tuple[str, ...]]] = set()
    for metodo, caminho in _RE_ROTA.findall(texto or ""):
        m = _RE_INTERVALO_NA_ROTA.search(caminho)
        variantes = [caminho]
        if m and int(m.group(3)) - int(m.group(2)) < 20:
            variantes = [caminho[:m.start()] + f"{m.group(1)}{i}" + caminho[m.end():]
                         for i in range(int(m.group(2)), int(m.group(3)) + 1)]
        saida |= {(metodo.upper(), tuple(_normalizar(v))) for v in variantes}
    return saida


def _rota_no_prd(metodo: str, caminho: str, rotas_do_prd: Set[Tuple[str, Tuple[str, ...]]]) -> bool:
    """O PRD tem a rota com outro nome de parâmetro: `POST /efeito-amplificador/turmas/:id/gate` no handoff e
    `…/turmas/:turmaId/gate` no PRD da exp02em1b (22/10/2026) são a mesma rota. `rotas_do_prd` vem de
    `_rotas_normalizadas`."""
    from tools.rotas_plataforma import _normalizar

    return (metodo.upper(), tuple(_normalizar(caminho))) in rotas_do_prd


def _rota_literal_no_prd(metodo: str, caminho: str, prd: str) -> bool:
    """O PRD escreve a rota do handoff com o mesmo verbo: «POST /x», «POST `/x`», em tabela «| `POST` | `/x` |», e com o
    prefixo do módulo que o handoff abreviou — «`GET /painel`» no handoff da exp02ef1b-4fd72a9a é a
    «| GET | `/galeria/turmas/:turmaId/painel` |» do PRD. O caminho sozinho não basta: o PRD que troca o verbo, ou que só
    tem o caminho dentro de outra rota, perdeu a rota (revisão do PR #77, 24/10/2026)."""
    c = re.escape(caminho.rstrip("/"))
    return bool(re.search(rf"\b{metodo}`?\s*(?:\|\s*)?`?(?:/[\w:{{}}.-]+)*?{c}(?![\w:{{}}-])", prd or ""))


def _rota_da_plataforma(metodo: str, caminho: str) -> bool:
    """A rota é da plataforma (índice `openapi-rotas.json` da base): `POST /telemetry/batch`, `POST
    /observabilidade/vitals`, `PUT /salas/turma/:turmaId/missoes/:expId`. O PRD codifica o módulo da missão; não precisa
    repetir a casca que o handoff cita (exp02em1b, 22/10/2026). Verbo errado não é da plataforma e continua cobrado."""
    from tools.rotas_plataforma import _casa, _normalizar, carregar

    rotas, _ = carregar()
    citada = _normalizar(caminho)
    return any(m == metodo.upper() and _casa(citada, r) for m, r in rotas)


def handoff_no_prd(prd: str, handoff: str) -> List[Dict[str, str]]:
    """O que o handoff entregou ao PRD não some no caminho: tabela da missão, evento, rota.

    Nada comparava os dois (auditoria do padrão ouro, 08/10/2026): o PRD da exp09ef1b reduziu a DDL do handoff a
    prosa e trocou `GET /sessoes/:id` por `GET /sessao` sem dizer. Tabela e evento que somem reprovam — a menos que a
    seção 19 do PRD os nomeie (divergência registrada). Rota diferente é ressalva: o PRD reorganiza para o molde.
    """
    achados: List[Dict[str, str]] = []
    if not (handoff or "").strip() or not (prd or "").strip():
        return achados
    s19 = _secao(prd, 19)
    # o nome só na seção 19 é divergência registrada, não presença: antes o corpo incluía a 19 e citar bastava
    corpo = prd.replace(s19, "") if s19 else prd

    def registrado(nome: str) -> bool:
        return nome in s19

    # tabela é o que o handoff declara como tabela — índice, policy e constraint têm o mesmo prefixo e não contam
    declaradas = set(re.findall(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"]?(exp\w+)", handoff, re.I))
    declaradas |= set(re.findall(r"@@map\(\"(exp\w+)\"\)", handoff))
    declaradas |= set(re.findall(r"tabela\s+\**`(exp\w+)`", handoff, re.I))
    if not declaradas:
        declaradas = {t for t in _RE_TABELA_DA_MISSAO.findall(handoff)
                      if not re.search(r"_(?:idx|pkey|fkey|key|check|por_escola|uk|unique)$", t)}
    # a seção 19 nomear a divergência é texto do modelo: não isenta, só tira do bloqueio — o PO vê (plano 2.8)
    so_registradas = sorted({t for t in declaradas if t not in corpo and registrado(t)})
    tabelas = sorted({t for t in declaradas if t not in corpo and not registrado(t)})
    if tabelas:
        _achado(achados, "bloqueio", "tabela-do-handoff-perdida",
                f"O handoff declara {', '.join(f'`{t}`' for t in tabelas)} e o PRD não as tem nem as registra como "
                "divergência na seção 19: quem codifica não sabe se a tabela existe.")
    objetos: Set[str] = set()
    for t in _tabelas(handoff):
        col = _coluna(t, "objeto")
        if col is None:
            continue
        for linha in t[1:]:
            objetos |= set(re.findall(r"\b[a-z_]+:[a-z0-9_:-]+\b", linha[col] if col < len(linha) else ""))
    so_registradas += sorted(o for o in objetos if o not in corpo and registrado(o))
    eventos = sorted(o for o in objetos if o not in corpo and not registrado(o))
    if eventos:
        _achado(achados, "bloqueio", "evento-do-handoff-perdido",
                f"Evento(s) do handoff que o PRD não traz nem registra na seção 19: {', '.join(f'`{o}`' for o in eventos[:12])}"
                f"{' …' if len(eventos) > 12 else ''}. O objeto é o que a conferência de telemetria procura literal.")
    if so_registradas:
        _achado(achados, "atencao", "divergencia-do-handoff-registrada",
                f"O PRD tira do handoff {', '.join(f'`{n}`' for n in so_registradas[:12])} e só registra a troca na seção 19. "
                "Confira se a divergência tem motivo antes do de acordo.")
    # rota normalizada (`:id` = `:turmaId`, `p1..p3` expandido) e a da plataforma de mesmo verbo não contam: 29 das 35
    # rotas acusadas nas 13 execuções de dev de 25/09 a 23/10/2026 eram isso (análise de 24/10/2026). O atalho literal
    # confere verbo e caminho: só o caminho deixava passar o PRD que troca o verbo da rota (`POST` → `PUT`) sem dizer
    # (revisão do PR #77, 24/10/2026)
    rotas_do_prd = _rotas_normalizadas(prd)
    rotas = sorted({f"{m} {p}" for m, p in _RE_ROTA.findall(handoff)
                    if not _rota_literal_no_prd(m, p, prd) and not _rota_no_prd(m, p, rotas_do_prd)
                    and not _rota_da_plataforma(m, p)})
    if rotas:
        _achado(achados, "atencao", "rota-do-handoff-mudou",
                f"Rota(s) do handoff que o PRD não repete: {', '.join(f'`{r}`' for r in rotas[:10])}. Se o PRD as trocou pelo "
                "molde, a seção 19 diz qual substitui qual.")
    return achados


# --------------------------------------------------------------------------- entrada
def validar(prd: str, spec: str = "", banco: str = "", handoff: str = "") -> Dict[str, Any]:
    from tools.conteudo_aprovado import remover_anexo

    corpo = remover_anexo(prd or "")
    achados: List[Dict[str, str]] = []
    if not corpo.strip():
        _achado(achados, "bloqueio", "prd-vazio", "O PRD está vazio.")
    else:
        _rotas(corpo, achados)
        _ia(corpo, achados)
        _modelo(corpo, achados)
        _ficha(corpo, spec, achados)
        achados += [a for a in validar_intencoes(banco, spec, corpo) if a["codigo"] == "prd-sem-intencoes"]
        achados += handoff_no_prd(corpo, handoff)
    status = "bloqueado" if any(a["severidade"] == "bloqueio" for a in achados) else ("amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados}


def relatorio(resultado: Dict[str, Any], missao: str = "") -> str:
    icone = {"aprovado": "🟢 DÁ PARA CODAR", "amarelo": "🟡 DÁ PARA CODAR, COM RESSALVAS",
             "bloqueado": "🔴 QUEM CODIFICA VAI TER DE DECIDIR"}[resultado["status"]]
    linhas = [f"# PRD codificável — {missao or 'missão'}", "", f"**Veredito: {icone}**", "",
              "Rotas do molde com Zod e erros, IA com prompt e schema, DDL com o bloco manual, ficha de evidência com "
              "regra sobre colunas e, em missão de chat, a árvore de intenções.", ""]
    if resultado["achados"]:
        linhas += ["## Achados", ""] + [f"- {'❌' if a['severidade'] == 'bloqueio' else '⚠️'} **{a['codigo']}** — "
                                        f"{a['resumo']}" for a in resultado["achados"]]
    linhas += ["", "```json", json.dumps({"agente": AGENTE, "missao": missao, "status": resultado["status"],
                                          "achados": resultado["achados"]}, ensure_ascii=False, indent=2), "```"]
    return "\n".join(linhas)
