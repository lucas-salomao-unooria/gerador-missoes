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
from typing import Any, Dict, List, Optional, Set

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
    prompts = [m.group(2) for m in _RE_BLOCO.finditer(s12)
               if m.group(1).lower() in ("", "text", "txt", "md", "markdown", "prompt") and len(m.group(2).split()) >= 40]
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
        if tipo == "acao" and "[PROPOSTA" not in regra:
            citadas = {c.lower() for c in re.findall(r"\b([a-z][a-z0-9]*_[a-z0-9_]+)\b", regra)}
            if not citadas & colunas:
                _achado(achados, "bloqueio", "regra-sem-coluna",
                        f"Ficha de {cel(i_hab)[:40]}: a regra «{regra[:120]}» não lê nenhuma coluna declarada na seção 11. "
                        "A regra é um predicado sobre o que o servidor gravou (`cadeia_tentativas = 1 → atingiu`); o que "
                        "não vira predicado é `[PROPOSTA — validar com PO: …]`, e a coluna que falta entra na seção 11.")
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


# --------------------------------------------------------------------------- entrada
def validar(prd: str, spec: str = "", banco: str = "") -> Dict[str, Any]:
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
