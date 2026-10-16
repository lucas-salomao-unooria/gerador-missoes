"""Coerência pedagógica conferível: grau de medida, matriz habilidade→dado, gabarito no servidor.

Três perguntas de FATO, no molde de `tools/bncc.py` — que declara a fronteira certa: o que se
confere contra lista, formato ou outro trecho do documento é determinístico; julgar se a ação
exercita a habilidade continua com o LLM.

O que motivou cada uma, medido nas 14 primeiras execuções:

- `scored` exige ≥2 sinais independentes pela própria definição do bloco 9, e das 25 medidas
  declaradas `scored` em tabela apenas 10 nomeavam dois. Grau inflado vira número que um adulto
  usa para decidir sobre uma criança.
- O bloco 11 trazia 40 códigos de Computação e ~38 não tinham nenhum dado do bloco 9 ligado: a
  habilidade era declarada e nada a media.
- O gabarito "vive no servidor" aparecia em prosa em 6 das 14 specs, e é critério BLOQUEANTE
  (PED-04) que nenhuma verificação mecânica tocava.
- A matriz terminava numa coluna «Marcador» que dizia só «ternário»: a escala sem a regra que
  separa Atingiu, Em processo e Não atingiu, deixada para quem implementa. Desde a rubrica v1.21
  (revisão do PO, 24/09/2026) cada linha diz o canal da evidência — ação (A), pergunta (B) ou os
  dois — e a regra por extenso. Se as três alternativas ficam visíveis ao mesmo tempo no 1º–2º
  ano (critério 3.5) é pergunta de tela, e fica com os pareceres, não com este gate.

Como em `tools/rastro.py` aprendemos que prosa engana, aqui só se lê TABELA com cabeçalho
reconhecido e identificador entre crases. Texto corrido é ignorado, sem fallback.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional

from tools import bncc
from tools.rastro import _usado_afirmativamente

AGENTE = "evidencia-pedagogica"

_GRAUS = ("scored", "indicative", "zero", "none")
_RE_GRAU = re.compile(r"\b(scored|indicative|zero|none)\b", re.IGNORECASE)
_RE_IDENT = re.compile(r"`([^`]+)`")
_RE_MOMENTO = re.compile(r"\bE[0-6]-(?:ALU|PROF|SIS)-\d{2}\b|\b(desafiar|navegar|decidir|resultado|aha|explicar|refletir)\b", re.I)
_RE_GABARITO = re.compile(r"^\s*[-*]\s*[`*_]*gabarito_servidor[`*_]*\s*:\s*[`*_]*\s*(sim|n[ãa]o)\b", re.I | re.M)
_RE_GABARITO_CLIENTE = re.compile(r"gabarito[^\n]{0,90}\b(no cliente|bundle|front-?end|navegador|localstorage)", re.I)
_RE_LINHA_TABELA = re.compile(r"^\s*\|(.+)\|\s*$", re.M)
#: A, B ou os dois — tolera «Canal A», «A (ação)», «A + B». Letra maiúscula: «a ação» não é canal.
_RE_CANAL = re.compile(r"^[\W_]*(?:(?i:canal)\s+)?(A\s*\+\s*B|B\s*\+\s*A|A|B)(?!\w)")
#: Os três níveis, sobre o texto normalizado (sem acento, minúsculo). «Não atingiu» contém «atingiu».
_NIVEIS = (re.compile(r"(?<!nao )\batingiu\b"), re.compile(r"\bem processo\b"), re.compile(r"\bnao atingiu\b"))


#: Desde 15/10/2026 toda habilidade tem Canal A: a pergunta do Canal B só soma evidência (decisão do PO).
_RESUMO_SEM_CANAL_A = (
    "`{codigo}`: canal só `B`. Toda habilidade tem Canal A — uma ação nativa do ambiente com regra ternária —, e a "
    "pergunta de múltipla escolha só soma evidência a ela. Declare `A` ou `A + B`, com a ação e a regra; se nenhuma "
    "ação da missão exercita a habilidade, o defeito está na mecânica, e uma pergunta no fim não o conserta.")


def _so_canal_b(canal: str) -> bool:
    return re.sub(r"\s+", "", canal or "").upper() == "B"


def _norm(texto: str) -> str:
    sem = "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")
    return sem.strip(" `*_|")


def _tabelas(texto: str, obrigatorias: set) -> List[List[Dict[str, str]]]:
    """Tabelas markdown cujo cabeçalho contém todas as colunas pedidas (nome normalizado).

    Percorre o documento LINHA A LINHA, e não só as linhas de tabela: coletar apenas as
    linhas `|…|` apagava a fronteira entre duas tabelas, e o cabeçalho da seguinte virava
    dado da anterior — a tabela do bloco 11 era lida como medida do bloco 9 e o gate acusava
    "grau inválido" na linha que nomeia a coluna `Grau`.
    """
    achadas: List[List[Dict[str, str]]] = []
    cabecalho: Optional[List[str]] = None
    corpo: List[Dict[str, str]] = []

    def fechar() -> None:
        nonlocal cabecalho, corpo
        if cabecalho is not None and corpo:
            achadas.append(corpo)
        cabecalho, corpo = None, []

    for bruta in (texto or "").splitlines():
        linha = bruta.strip()
        if not (linha.startswith("|") and linha.endswith("|")):
            fechar()
            continue
        celulas = [c.strip() for c in linha.strip("|").split("|")]
        normal = [_norm(c) for c in celulas]
        if set("".join(celulas)) <= set("-: "):
            continue  # linha separadora
        if cabecalho is not None and normal == cabecalho:
            continue  # tabela sem separadora: o cabeçalho não é dado
        if cabecalho is None or not (obrigatorias <= set(normal)) and obrigatorias <= set(cabecalho):
            if obrigatorias <= set(normal):
                fechar()
                cabecalho = normal
                continue
            if cabecalho is None:
                continue
            corpo.append({cab: celulas[k] if k < len(celulas) else "" for k, cab in enumerate(cabecalho)})
        else:
            fechar()
            cabecalho = normal
    fechar()
    return achadas


def validar(spec: str) -> Dict[str, Any]:
    texto = spec or ""
    achados: List[Dict[str, str]] = []

    def falha(codigo: str, resumo: str, severidade: str = "bloqueio") -> None:
        achados.append({"severidade": severidade, "codigo": codigo, "etapa": "produto", "resumo": resumo})

    if not texto.strip():
        falha("spec-vazia", "A spec chegou vazia: não há evidência a conferir.")
        return {"status": "bloqueado", "achados": achados, "medidas": [], "codigos": []}

    # (a) grau de medida — `scored` exige ≥2 sinais nomeados, pela definição do próprio bloco 9
    medidas = [linha for tabela in _tabelas(texto, {"medida", "grau", "sinais"}) for linha in tabela]
    if not medidas:
        falha("tabela-medidas-ausente",
              "Bloco 9 sem a tabela de medidas. Cabeçalho exato a copiar: "
              "`| Medida | Grau | Sinais | Canal | Tabela.coluna | Habilidade |`. "
              "Sem ela não há como conferir se um grau `scored` tem os dois sinais que a própria "
              "definição exige — e grau inflado vira número que um adulto usa para decidir sobre uma criança.")
    for linha in medidas:
        nome = _norm(linha.get("medida", ""))
        grau = (_RE_GRAU.search(linha.get("grau", "")) or [None])
        grau_txt = grau.group(1).lower() if hasattr(grau, "group") else ""
        if not grau_txt:
            falha("grau-invalido", f"Medida `{linha.get('medida', '?')}` sem grau válido "
                                   f"(um de {', '.join(_GRAUS)}).")
            continue
        if grau_txt == "scored":
            sinais = [s for s in _RE_IDENT.findall(linha.get("sinais", "")) if _norm(s) != nome]
            if len(sinais) < 2:
                falha("scored-1-sinal",
                      f"Medida `{linha.get('medida', '?')}` é `scored` com {len(sinais)} sinal(is) nomeado(s). "
                      f"O grau `scored` exige ≥2 sinais independentes: rebaixe para `indicative` ou nomeie o segundo.")

    # (b) toda habilidade de Computação tem momento em tela E medida do bloco 9
    bloco11 = bncc.secao_bloco(texto, 11) if hasattr(bncc, "secao_bloco") else texto
    codigos = sorted(set(bncc.CODIGO_RE.findall(bloco11 or "")))
    matriz = [linha for tabela in _tabelas(texto, {"codigo", "momento em tela", "medida do bloco 9"}) for linha in tabela]
    por_codigo = {}
    for linha in matriz:
        for c in bncc.CODIGO_RE.findall(linha.get("codigo", "")):
            por_codigo[c] = linha
    nomes_medidas = {_norm(m.get("medida", "")) for m in medidas}
    for c in codigos:
        linha = por_codigo.get(c)
        if linha is None:
            falha("habilidade-sem-matriz",
                  f"`{c}` está no bloco 11 e não tem linha na matriz de evidência. Cabeçalho: "
                  f"`| Código | Momento em tela | Ação observável | O que não conta | Medida do bloco 9 | "
                  f"Canal de evidência | Regra ternária |`.")
            continue
        if not _RE_MOMENTO.search(linha.get("momento em tela", "")):
            falha("habilidade-sem-momento",
                  f"`{c}`: a coluna «Momento em tela» não aponta etapa nem tela (`E3-ALU-01`, «Decidir»…).")
        ligadas = [s for s in _RE_IDENT.findall(linha.get("medida do bloco 9", "")) if _norm(s) in nomes_medidas]
        if not ligadas:
            falha("habilidade-sem-medida",
                  f"`{c}`: nenhuma medida do bloco 9 ligada. Habilidade declarada que nada mede é "
                  f"currículo no papel — some no relatório do professor.")
        canal = _RE_CANAL.match(linha.get("canal de evidencia", "").strip())
        if not canal:
            falha("habilidade-sem-canal",
                  f"`{c}`: a coluna «Canal de evidência» não diz `A` (ação), `B` (pergunta) nem `A + B`. "
                  f"Sem canal, quem implementa não sabe de onde sai o nível — e inventa a classificação.")
        elif _so_canal_b(canal.group(1)):
            falha("habilidade-sem-canal-a", _RESUMO_SEM_CANAL_A.format(codigo=c))
        regra = _norm(linha.get("regra ternaria", ""))
        if not all(n.search(regra) for n in _NIVEIS):
            falha("regra-ternaria-ausente",
                  f"`{c}`: a coluna «Regra ternária» não diz o que separa Atingiu, Em processo e Não atingiu, "
                  f"por extenso. Sem a regra, a matriz declara a escala e deixa a classificação para quem implementa.")

    # (c) gabarito no servidor — PED-04 é bloqueante e nada o conferia
    ficha = _RE_GABARITO.search(texto)
    if not ficha:
        falha("gabarito-nao-declarado",
              "Bloco 9 sem a ficha `- `gabarito_servidor: sim``. É critério bloqueante (PED-04) e "
              "aparecia só em prosa: gabarito no bundle é gabarito entregue ao estudante.")
    elif ficha.group(1).lower().startswith("n"):
        falha("gabarito-no-cliente", "`gabarito_servidor: não` — o gabarito precisa viver no servidor (PED-04).")
    # A spec CORRETA fala do bundle justamente para dizer que o gabarito não está lá
    # ("Ausência total de pistas de gabarito no bundle do cliente"). Procurar o termo acusava
    # o texto por cumprir a regra — a mesma armadilha que o detector de WebSocket tinha.
    if _usado_afirmativamente(texto, _RE_GABARITO_CLIENTE.pattern):
        falha("gabarito-no-cliente", "O texto coloca o gabarito no cliente/bundle: ele vive no servidor (PED-04).")

    bloqueios = [a for a in achados if a["severidade"] == "bloqueio"]
    status = "bloqueado" if bloqueios else ("amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados, "medidas": medidas, "codigos": codigos}


def relatorio(resultado: Dict[str, Any], missao: str = "") -> str:
    import json
    icone = {"aprovado": "🟢 EVIDÊNCIA COERENTE", "amarelo": "🟡 COM RESSALVAS", "bloqueado": "🔴 BLOQUEADO"}[resultado["status"]]
    linhas = [f"# Matriz de evidência pedagógica — {missao or 'missão'}", "", f"**Veredito: {icone}**", "",
              f"Medidas declaradas: **{len(resultado['medidas'])}** · "
              f"habilidades de Computação no bloco 11: **{len(resultado['codigos'])}**", ""]
    if resultado["achados"]:
        linhas += ["## Achados", ""]
        for a in resultado["achados"]:
            marca = "❌" if a["severidade"] == "bloqueio" else "⚠️"
            linhas.append(f"- {marca} **{a['codigo']}** — {a['resumo']}")
    else:
        linhas.append("Nenhum achado: todo grau `scored` tem dois sinais, toda habilidade tem momento, medida, canal e regra ternária, e o gabarito está declarado no servidor.")
    linhas += ["", "```json", json.dumps(
        {"agente": AGENTE, "missao": missao, "status": resultado["status"], "achados": resultado["achados"]},
        ensure_ascii=False, indent=2), "```"]
    return "\n".join(linhas)


# --------------------------------------------------------------------------- §12a do one-pager
#: O contrato de evidência do one-pager, conferido onde ele nasce. Os comitês julgam o sentido de cada canal; aqui se
#: confere o que é forma — se a forma falha, o voto não chega a ser gasto (comitês de 15/10/2026).
AGENTE_ONE_PAGER = "evidencia-one-pager"
_RE_12A_TITULO = re.compile(r"^#{2,5}\s*[*_]*\s*12a\b", re.M | re.I)
CABECALHO_12A = ("| Habilidade (código) | Canal de evidência | Canal A: ação · etapa · regra ternária (Atingiu / Em "
                 "processo / Não atingiu) | Canal B: pergunta · 3 alternativas com o nível de cada uma, sem ordem fixa · "
                 "componente que renderiza |")


def _coluna_12a(nome: str) -> str:
    """Papel de uma coluna do §12a pelo nome normalizado. Dois formatos convivem no acervo: uma linha por habilidade
    com as colunas «Canal A: …» e «Canal B: …» (o do A014), e uma linha por habilidade e canal, com a coluna «Canal»
    dizendo qual (exp09ef1b)."""
    if nome.startswith("habilidade"):
        return "habilidade"
    if nome.startswith("canal de evidencia") or nome in ("canal", "canais"):
        return "canal"
    if re.match(r"canal a\b", nome):
        return "canal_a"
    if re.match(r"canal b\b", nome):
        return "canal_b"
    return ""


def _contrato_12a(trecho: str) -> Optional[Dict[str, Dict[str, Any]]]:
    """Por código: os canais declarados e o texto de cada um. `None` sem tabela reconhecível no §12a."""
    papeis: Optional[List[str]] = None
    contrato: Dict[str, Dict[str, Any]] = {}
    linhas = 0
    for bruta in trecho.splitlines()[1:]:
        linha = bruta.strip()
        if not (linha.startswith("|") and linha.endswith("|")):
            if papeis is not None and linhas:
                break
            continue
        celulas = [c.strip() for c in linha.strip("|").split("|")]
        if set("".join(celulas)) <= set("-: "):
            continue
        if papeis is None:
            candidatos = [_coluna_12a(_norm(c)) for c in celulas]
            if {"habilidade", "canal"} <= set(candidatos):
                papeis = candidatos
            continue
        linhas += 1
        por_papel: Dict[str, str] = {}
        resto: List[str] = []
        for i, celula in enumerate(celulas):
            papel = papeis[i] if i < len(papeis) else ""
            if papel:
                por_papel[papel] = por_papel.get(papel, "") + " " + celula
            else:
                resto.append(celula)
        canal = _RE_CANAL.match(por_papel.get("canal", "").strip())
        canais = set(re.sub(r"[^AB]", "", canal.group(1).upper())) if canal else set()
        largo = "canal_a" in papeis or "canal_b" in papeis
        for c in bncc.extrair_codigos(por_papel.get("habilidade", "")):
            item = contrato.setdefault(c, {"canais": set(), "texto_a": "", "texto_b": ""})
            item["canais"] |= canais
            if largo:
                item["texto_a"] += " " + por_papel.get("canal_a", "")
                item["texto_b"] += " " + por_papel.get("canal_b", "")
            else:  # uma linha por canal: o resto da linha é o contrato daquele canal
                chave = "texto_b" if canais == {"B"} else "texto_a"
                item[chave] += " " + " ".join(resto)
    return contrato if papeis is not None else None


def _vazia(celula: str) -> bool:
    return not re.sub(r"[\s`*_—–\-.]", "", celula or "")


def conferir_one_pager(one_pager: str) -> Dict[str, Any]:
    """O §12a do one-pager: toda habilidade de Computação da §2 tem contrato, com Canal A e regra ternária; o Canal B,
    quando existe, mapeia as alternativas aos três níveis. O sentido de cada canal é dos comitês, não deste gate."""
    from tools.conteudo_aprovado import secao

    texto = one_pager or ""
    achados: List[Dict[str, str]] = []

    def falha(codigo: str, resumo: str) -> None:
        achados.append({"severidade": "bloqueio", "codigo": codigo, "etapa": "produto",
                        "agente_responsavel": "one-pager", "resumo": resumo})

    s12 = secao(texto, 12) or ""
    m = _RE_12A_TITULO.search(s12)
    if not m:
        falha("12a-ausente", "O one-pager não tem o §12a «Contrato de evidência por habilidade»: sem ele, nenhuma "
                             "habilidade diz de onde sai o nível do estudante.")
        return {"status": "bloqueado", "achados": achados, "codigos": []}
    contrato = _contrato_12a(s12[m.start():])
    if contrato is None:
        falha("12a-sem-tabela", f"O §12a não tem a tabela do contrato. Cabeçalho a copiar: `{CABECALHO_12A}`")
        return {"status": "bloqueado", "achados": achados, "codigos": []}

    for c in bncc.extrair_codigos(secao(texto, 2) or ""):
        if c not in contrato:
            falha("habilidade-sem-contrato", f"`{c}` está na seção 2 e não tem linha no §12a: habilidade sem contrato "
                                             f"de evidência é habilidade que nada mede.")
    for c, item in contrato.items():
        if not item["canais"]:
            falha("habilidade-sem-canal", f"`{c}`: a coluna do canal não diz `A` nem `A + B`.")
            continue
        if "A" not in item["canais"]:
            falha("habilidade-sem-canal-a", _RESUMO_SEM_CANAL_A.format(codigo=c))
            continue
        if not all(n.search(_norm(item["texto_a"])) for n in _NIVEIS):
            falha("regra-ternaria-ausente",
                  f"`{c}`: o Canal A não diz, por extenso, o que separa Atingiu, Em processo e Não atingiu na ação "
                  f"observada. Sem a regra, quem implementa inventa a classificação.")
        if "B" in item["canais"]:
            if _vazia(item["texto_b"]):
                falha("canal-b-vazio", f"`{c}`: canal `A + B`, mas o Canal B está vazio: declare a pergunta e as três "
                                       f"alternativas, ou mude o canal para `A`.")
            elif not all(n.search(_norm(item["texto_b"])) for n in _NIVEIS):
                falha("canal-b-sem-niveis", f"`{c}`: as alternativas do Canal B não dizem a qual nível cada uma leva "
                                            f"(Atingiu · Em processo · Não atingiu).")
    status = "bloqueado" if achados else "aprovado"
    return {"status": status, "achados": achados, "codigos": list(contrato)}


def relatorio_one_pager(resultado: Dict[str, Any], missao: str = "") -> str:
    import json

    icone = {"aprovado": "🟢 CONTRATO COMPLETO", "bloqueado": "🔴 BLOQUEADO"}[resultado["status"]]
    linhas = [f"# Contrato de evidência do one-pager (§12a) — {missao or 'missão'}", "", f"**Veredito: {icone}**", "",
              f"Habilidades com linha no §12a: **{len(resultado['codigos'])}**", ""]
    if resultado["achados"]:
        linhas += ["## Achados", ""] + [f"- ❌ **{a['codigo']}** — {a['resumo']}" for a in resultado["achados"]]
    else:
        linhas.append("Nenhum achado: toda habilidade da seção 2 tem linha no §12a, com Canal A e regra ternária, e "
                      "todo Canal B declara o nível de cada alternativa.")
    linhas += ["", "```json", json.dumps(
        {"agente": AGENTE_ONE_PAGER, "missao": missao, "status": resultado["status"], "achados": resultado["achados"]},
        ensure_ascii=False, indent=2), "```"]
    return "\n".join(linhas)


def habilidades_com_canal_b(one_pager: str) -> Optional[List[str]]:
    """Códigos com Canal B no §12a; `None` quando o §12a não se lê — aí ninguém pula o painel B por engano."""
    from tools.conteudo_aprovado import secao

    s12 = secao(one_pager or "", 12) or ""
    m = _RE_12A_TITULO.search(s12)
    contrato = _contrato_12a(s12[m.start():]) if m else None
    if contrato is None:
        return None
    return [c for c, item in contrato.items() if "B" in item["canais"]]
