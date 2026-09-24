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
                  f"`| Código | Momento em tela | Ação observável | O que não conta | Medida do bloco 9 | Marcador |`.")
            continue
        if not _RE_MOMENTO.search(linha.get("momento em tela", "")):
            falha("habilidade-sem-momento",
                  f"`{c}`: a coluna «Momento em tela» não aponta etapa nem tela (`E3-ALU-01`, «Decidir»…).")
        ligadas = [s for s in _RE_IDENT.findall(linha.get("medida do bloco 9", "")) if _norm(s) in nomes_medidas]
        if not ligadas:
            falha("habilidade-sem-medida",
                  f"`{c}`: nenhuma medida do bloco 9 ligada. Habilidade declarada que nada mede é "
                  f"currículo no papel — some no relatório do professor.")

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
        linhas.append("Nenhum achado: todo grau `scored` tem dois sinais, toda habilidade tem momento e medida, e o gabarito está declarado no servidor.")
    linhas += ["", "```json", json.dumps(
        {"agente": AGENTE, "missao": missao, "status": resultado["status"], "achados": resultado["achados"]},
        ensure_ascii=False, indent=2), "```"]
    return "\n".join(linhas)
