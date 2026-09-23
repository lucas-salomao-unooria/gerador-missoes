"""Coerência KPI ↔ evento ↔ tela no PRD — o número passa a apontar para algo que o mede.

Nada disso era conferido. Nas 14 primeiras execuções, entre 49 KPIs: 20 com baseline `0%`
(que não é medida, é espaço em branco vestido de número), KPIs alimentados por evento de OUTRA
tela ("Retenção na Mesa de Limpeza" → evento que dispara em "Salvar no Mural"), KPIs apontando
para uma tabela ou uma rota em vez de um evento, e payload que não computa o que o KPI afirma
medir (`{"total": 3}` para "exposição ao viés falso neutro"). O `telemetria-check` deu verde em
cinco dessas sessões: ele confere o FORMATO do evento, não se o KPI fecha com ele.

Todas as regras aqui são cross-ref — "o ID citado em A existe em B, e o que B diz bate com o
que A afirma" — e por isso cabem em código. A §2 dos PRDs saiu em formatos muito diferentes,
então as colunas são reconhecidas pelo NOME normalizado, nunca por posição.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Dict, List, Optional

AGENTE = "kpis-check"

_RE_KPI = re.compile(r"\bKPI-?\d{1,3}\b", re.IGNORECASE)
_RE_EVT = re.compile(r"\bEVT-U?\d{1,3}\b", re.IGNORECASE)
_RE_TELA = re.compile(r"\bE[0-6]-(?:ALU|PROF|SIS)-\d{2}\b")
_RE_ETAPA = re.compile(r"\bE[0-6]\b")
_RE_BASELINE_ZERO = re.compile(r"^\s*\**\s*\$?\s*0\s*\\?%", re.I)
_RE_SEM_BASELINE = re.compile(r"sem baseline", re.I)
_RE_ORIGEM = re.compile(r"\(([^)]{4,})\)")
_RE_TABELA_OU_ROTA = re.compile(r"\bENT-\d|\bexp_?\d{2}_?e[fm]\d?b?_|GET\s+/|POST\s+/|\bRota\b", re.I)
_CORTES = {"rede", "escola", "missao", "serie", "turma", "professor"}


def _norm(t: str) -> str:
    sem = "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")
    return sem.strip(" `*_|")


def _tabelas(texto: str, obrigatorias: set) -> List[List[Dict[str, str]]]:
    """Tabelas cujo cabeçalho contém todas as colunas pedidas, lendo o documento linha a linha."""
    achadas: List[List[Dict[str, str]]] = []
    cab: Optional[List[str]] = None
    corpo: List[Dict[str, str]] = []

    def fechar() -> None:
        nonlocal cab, corpo
        if cab is not None and corpo:
            achadas.append(corpo)
        cab, corpo = None, []

    for bruta in (texto or "").splitlines():
        linha = bruta.strip()
        if not (linha.startswith("|") and linha.endswith("|")):
            fechar()
            continue
        celulas = [c.strip() for c in linha.strip("|").split("|")]
        normal = [_norm(c) for c in celulas]
        if set("".join(celulas)) <= set("-: "):
            continue
        if obrigatorias <= set(normal):
            fechar()
            cab = normal
            continue
        if cab is not None:
            if normal == cab:
                continue
            corpo.append({c: celulas[k] if k < len(celulas) else "" for k, c in enumerate(cab)})
    fechar()
    return achadas


def _col(linha: Dict[str, str], *nomes: str) -> str:
    for n in nomes:
        for chave, valor in linha.items():
            if n in chave:
                return valor
    return ""


def validar_kpis(prd: str, spec: str = "") -> Dict[str, Any]:
    texto = prd or ""
    achados: List[Dict[str, str]] = []

    def falha(codigo: str, resumo: str, severidade: str = "bloqueio") -> None:
        achados.append({"severidade": severidade, "codigo": codigo, "etapa": "dev", "resumo": resumo})

    if not texto.strip():
        falha("prd-vazio", "PRD vazio: não há KPI a conferir.")
        return {"status": "bloqueado", "achados": achados, "kpis": 0, "eventos": 0}

    tab_kpi = [l for t in _tabelas(texto, {"kpi"}) for l in t if _RE_KPI.search(str(l))]
    tab_evt = [l for t in _tabelas(texto, {"quando dispara"}) for l in t]
    if not tab_kpi:
        falha("tabela-kpi-ausente",
              "Sem tabela de KPIs legível na seção de objetivos. Cabeçalho: "
              "`| KPI | Pergunta | Decisão | Corte | Tela | Evento(s) | Como calcula | Baseline | Alvo | Prazo |`.")
    if not tab_evt:
        falha("tabela-evt-ausente", "Sem tabela de eventos legível (coluna «Quando dispara»).",
              severidade="atencao")

    # telas de cada evento, para o casamento KPI ↔ evento ↔ tela
    tela_do_evento: Dict[str, set] = {}
    payload_do_evento: Dict[str, str] = {}
    for linha in tab_evt:
        ids = _RE_EVT.findall(" ".join(linha.values()))
        if not ids:
            continue
        # A etapa é FALLBACK, não soma: `\bE[0-6]\b` casa "E3" dentro de "E3-ALU-02" (o hífen é
        # fronteira de palavra), e aí "E3" == "E3" fazia qualquer par de telas casar — o gate
        # aprovava justamente o caso que existe para pegar.
        telas = set(_RE_TELA.findall(" ".join(linha.values())))
        if not telas:
            telas = set(_RE_ETAPA.findall(_col(linha, "quando dispara")))
        for i in ids:
            tela_do_evento.setdefault(i.upper(), set()).update(telas)
            payload_do_evento[i.upper()] = _col(linha, "resultado") + " " + _col(linha, "contexto")

    for linha in tab_kpi:
        kpi = (_RE_KPI.search(" ".join(linha.values())) or [None])
        nome = kpi.group(0).upper() if hasattr(kpi, "group") else "KPI-?"
        celula_evento = _col(linha, "evento", "evt", "alimenta")
        eventos = [e.upper() for e in _RE_EVT.findall(celula_evento)]

        if not _col(linha, "pergunta"):
            falha("kpi-sem-pergunta", f"{nome} sem a pergunta que responde: um número sem pergunta não muda decisão.")
        if not _col(linha, "decis"):
            falha("kpi-sem-decisao", f"{nome} sem a decisão que dispara: se nada muda conforme o valor, é métrica de vaidade.")
        corte = {_norm(c) for c in re.split(r"[·,/]", _col(linha, "corte")) if c.strip()}
        if corte and not (corte & _CORTES):
            falha("corte-invalido", f"{nome} com corte fora do vocabulário ({', '.join(sorted(corte))}): "
                                    f"use {', '.join(sorted(_CORTES))}.", severidade="atencao")

        if not eventos:
            if _RE_TABELA_OU_ROTA.search(celula_evento):
                falha("kpi-aponta-tabela-ou-rota",
                      f"{nome} é alimentado por uma tabela ou rota (`{celula_evento.strip()[:60]}`), não por um evento. "
                      f"Tabela guarda; evento é o que se conta.")
            else:
                falha("kpi-sem-evento", f"{nome} sem `EVT-` que o alimente: ninguém sabe de onde o número sai.")
            continue

        for e in eventos:
            if tab_evt and e not in tela_do_evento:
                falha("kpi-evento-inexistente", f"{nome} cita `{e}`, que não existe na tabela de eventos.")
                continue
            telas_kpi = set(_RE_TELA.findall(" ".join(linha.values())))
            if not telas_kpi:
                telas_kpi = set(_RE_ETAPA.findall(_col(linha, "tela")))
            telas_evt = tela_do_evento.get(e, set())
            if telas_kpi and telas_evt:
                casa = any(tk == te or tk.startswith(te) or te.startswith(tk) for tk in telas_kpi for te in telas_evt)
                if not casa:
                    falha("kpi-tela-divergente",
                          f"{nome} mede {sorted(telas_kpi)} e é alimentado por `{e}`, que dispara em "
                          f"{sorted(telas_evt)}. O número vai sair e não vai medir o que o KPI diz.")
            calculo = _col(linha, "como calcula", "calculo")
            campos = re.findall(r"(?:resultado|contexto)\.(\w+)", calculo)
            if campos:
                disponiveis = set(re.findall(r'"(\w+)"\s*:', payload_do_evento.get(e, "")))
                faltando = [c for c in campos if c not in disponiveis]
                if faltando:
                    falha("payload-nao-computa",
                          f"{nome} calcula com `{', '.join(faltando)}`, que `{e}` não carrega "
                          f"(payload: {payload_do_evento.get(e, '—')[:60]}).")

        baseline = _col(linha, "baseline", "linha de base")
        if _RE_BASELINE_ZERO.match(baseline) and not _RE_SEM_BASELINE.search(baseline):
            falha("baseline-zero",
                  f"{nome} com baseline `0%`: ninguém mediu zero, ninguém mediu. Escreva o número com a "
                  f"origem entre parênteses ou o literal `sem baseline — primeira medição`.")
        elif baseline.strip() in ("—", "-", "N/A", "n/a", ""):
            falha("baseline-ausente", f"{nome} sem baseline nem a declaração de que não há.")
        elif re.search(r"\d", baseline) and not _RE_ORIGEM.search(baseline) and not _RE_SEM_BASELINE.search(baseline):
            falha("baseline-sem-origem",
                  f"{nome} tem baseline `{baseline.strip()[:30]}` sem dizer de onde veio.", severidade="atencao")

    # a leitura precisa ter leitor: a fila analítica não é lugar onde alguém lê
    for linha in tab_evt:
        onde = _col(linha, "onde e lido", "tabela leitora", "leitor")
        if onde and re.search(r"/telemetry/(batch|beacon)|telemetria_eventos|pub/?sub", onde, re.I) \
                and not re.search(r"exp_?\d{2}_?e[fm]\d?b?_|posthog", onde, re.I):
            ids = _RE_EVT.findall(" ".join(linha.values()))
            falha("leitura-sem-leitor",
                  f"`{ids[0] if ids else 'evento'}` declara leitura em `{onde.strip()[:40]}` — é a fila de "
                  f"entrada, não um leitor. Ninguém lê `telemetria_eventos` para relatório de missão.")

    # A spec deixou de ser parâmetro morto. As perguntas decididas no 9f precisam CHEGAR ao PRD:
    # sem este cruzamento o redator podia largar três das cinco pelo caminho, e o gate aprovava as
    # duas que sobraram — ele conferia o PRD contra si mesmo.
    pq_spec = _pq_da_spec(spec)
    if pq_spec:
        citadas = {_pq_id(p) for p in _RE_PQ.findall(texto)}
        for pq in sorted(pq_spec):
            if pq not in citadas:
                falha("pq-sem-kpi",
                      f"{pq} («{pq_spec[pq][:60]}») foi decidida na spec e não tem KPI no PRD: "
                      f"a pergunta morreu entre produto e dev.")
        for pq in sorted(citadas - set(pq_spec)):
            falha("kpi-pq-inexistente",
                  f"O PRD cita {pq}, que não existe no sub-bloco 9f da spec. KPI não inventa pergunta: "
                  f"quem decide o que se quer saber é produto, com o PO.")

    bloqueios = [a for a in achados if a["severidade"] == "bloqueio"]
    status = "bloqueado" if bloqueios else ("amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados, "kpis": len(tab_kpi), "eventos": len(tela_do_evento)}


def relatorio(resultado: Dict[str, Any], missao: str = "") -> str:
    icone = {"aprovado": "🟢 KPI COERENTE", "amarelo": "🟡 COM RESSALVAS", "bloqueado": "🔴 BLOQUEADO"}[resultado["status"]]
    linhas = [f"# Coerência KPI ↔ evento ↔ tela — {missao or 'missão'}", "", f"**Veredito: {icone}**", "",
              f"KPIs: **{resultado['kpis']}** · eventos na tabela: **{resultado['eventos']}**", ""]
    if resultado["achados"]:
        linhas += ["## Achados", ""]
        for a in resultado["achados"]:
            linhas.append(f"- {'❌' if a['severidade'] == 'bloqueio' else '⚠️'} **{a['codigo']}** — {a['resumo']}")
    else:
        linhas.append("Nenhum achado: todo KPI tem pergunta, decisão, corte, evento que o alimenta na tela certa e baseline honesto.")
    linhas += ["", "```json", json.dumps(
        {"agente": AGENTE, "missao": missao, "status": resultado["status"], "achados": resultado["achados"]},
        ensure_ascii=False, indent=2), "```"]
    return "\n".join(linhas)


def extrair_perguntas_do_briefing(briefing: str) -> str:
    """O bloco `## Perguntas de produto` do briefing, normalizado para a tabela do 9f.

    O PO não precisa aprender formato de evento: ele escreve pergunta, decisão e corte em
    português, e a esteira transforma. Sem o bloco, devolve "" — e o agente propõe, marcando
    `[PROPOSTA — validar com PO]`.
    """
    texto = briefing or ""
    m = re.search(r"^##+\s*Perguntas de produto\s*$(.*?)(?=^##\s|\Z)", texto, re.M | re.S | re.I)
    if not m:
        return ""
    bloco = m.group(1)
    aulas = re.search(r"^\s*Aulas?\s*:\s*(\d)", bloco, re.M | re.I)
    herdar = re.search(r"^\s*Herdar\s*:\s*(.+)$", bloco, re.M | re.I)
    linhas: List[str] = []
    if aulas:
        linhas.append(f"- `declared_lessons: {aulas.group(1)}`")
    if herdar:
        ids = ", ".join(sorted(set(re.findall(r"\bT[1-8]\b", herdar.group(1)))))
        linhas.append(f"- `perguntas_herdadas: {ids}`")
    perguntas = []
    for item in re.findall(r"^\s*[-*]\s*(.+)$", bloco, re.M):
        partes = re.split(r"→|->", item)
        if len(partes) >= 2:
            pergunta = partes[0].strip()
            decisao = re.sub(r"^decis[ãa]o\s*:\s*", "", partes[1].strip(), flags=re.I)
            corte = re.sub(r"^corte\s*:\s*", "", partes[2].strip(), flags=re.I) if len(partes) > 2 else "missao"
            perguntas.append((pergunta, decisao, corte))
    if perguntas:
        linhas += ["", "| PQ | Pergunta | Decisão que dispara | Corte | Origem |", "|---|---|---|---|---|"]
        for i, (p_, d, c) in enumerate(perguntas, 1):
            linhas.append(f"| PQ-{i:02d} | {p_} | {d} | {c} | PO |")
    return "\n".join(linhas)


# ─── Sub-bloco 9f da spec: as 5 perguntas de produto ────────────────────────────────────
#
# O 9f é onde a pergunta NASCE. Até aqui nada o conferia: `validar_kpis` lia o PRD e a spec
# chegava como parâmetro morto. Uma spec podia sair com uma pergunta, com cinco frases vazias
# ou com cinco perguntas apontando para um evento que a própria spec não declara — e o PRD, duas
# etapas depois, herdava o buraco já convertido em KPI. Conferir aqui é mais barato: a correção
# custa uma reescrita da spec, não o retrabalho do PRD inteiro.
#
# Todas as regras são cross-ref dentro do MESMO documento: a ação que a pergunta usa existe na
# tabela de eventos do bloco 9? esse evento carrega algum campo? o corte está no vocabulário?
# Se a pergunta é boa — se responder a ela muda mesmo uma decisão nossa — é julgamento, e fica
# com o juiz LLM logo atrás (`prompts/produto/15_juiz_perguntas.md`).

PQ_POR_MISSAO = 5

_RE_PQ = re.compile(r"\bPQ-?\d{1,2}\b", re.IGNORECASE)
_RE_ACAO = re.compile(r"([a-z_][a-z_0-9]{2,})\s+([a-z_][a-z_0-9]*:[a-z_0-9.\-]+)", re.I)
_RE_LIMIAR = re.compile(r"\d|[<>≤≥]|abaixo de|acima de|menos de|mais de|nenhum[ao]?\b|todos?\b", re.I)
_RE_FICHA = re.compile(r"^\s*[-*]?\s*[`*_]*(declared_lessons|core_action|perguntas_herdadas)[`*_]*\s*:\s*(.+?)\s*$", re.M | re.I)
_VAZIOS = {"", "—", "-", "–", "n/a", "na", "nenhum", "nenhuma", "vazio", "todo", "?"}


def _limpo(celula: str) -> str:
    return (celula or "").strip(" `*_").strip()


def _mede(celula: str) -> bool:
    """A célula nomeia algum campo? Payload vazio não responde pergunta nenhuma."""
    texto = _limpo(celula)
    if _norm(texto) in _VAZIOS:
        return False
    return bool(re.search(r"[a-zA-Z_]{3,}", texto))


def _acao(celula: str) -> Optional[tuple]:
    m = _RE_ACAO.search(_limpo(celula))
    return (m.group(1).lower(), m.group(2).lower()) if m else None


def _eventos_da_spec(spec: str) -> Dict[tuple, str]:
    """`(verbo, objeto)` → payload declarado, lido da tabela de eventos do bloco 9."""
    mapa: Dict[tuple, str] = {}
    for tabela in _tabelas(spec, {"verbo", "objeto"}):
        for linha in tabela:
            verbo = _limpo(_col(linha, "verbo")).lower()
            objeto = _limpo(_col(linha, "objeto")).lower()
            if verbo and objeto:
                mapa[(verbo, objeto)] = _col(linha, "resultado") + " " + _col(linha, "contexto")
    return mapa


def validar_9f(spec: str) -> Dict[str, Any]:
    """As cinco perguntas de produto da spec: existem, são perguntas, e algo as responde."""
    texto = spec or ""
    achados: List[Dict[str, str]] = []

    def falha(codigo: str, resumo: str, severidade: str = "bloqueio") -> None:
        achados.append({"severidade": severidade, "codigo": codigo, "etapa": "produto", "resumo": resumo})

    if not texto.strip():
        falha("spec-vazia", "Spec vazia: não há sub-bloco 9f a conferir.")
        return {"status": "bloqueado", "achados": achados, "perguntas": 0}

    fichas = {m.group(1).lower(): _limpo(m.group(2)) for m in _RE_FICHA.finditer(texto)}
    eventos = _eventos_da_spec(texto)

    if not eventos:
        falha("spec-sem-tabela-eventos",
              "Sem tabela de eventos legível no bloco 9 (colunas `verbo` e `objeto`): nenhuma pergunta "
              "de produto pode ser cruzada com o que a missão de fato emite.")

    if "declared_lessons" not in fichas or not re.match(r"^\d", fichas.get("declared_lessons", "")):
        falha("declared-lessons-ausente",
              "Ficha `declared_lessons` ausente ou sem número. Sem ela a missão de duas aulas aparece "
              "com metade de conclusão por desenho, e as melhores são lidas como as piores.")
    if "core_action" not in fichas:
        falha("core-action-ausente",
              "Ficha `core_action` ausente: sem ela não se separa «o aluno passou pela decisão central» "
              "de «o aluno abriu a missão».")
    elif eventos:
        par = _acao(fichas["core_action"])
        if not par:
            falha("core-action-formato",
                  f"`core_action: {fichas['core_action']}` fora do formato `verbo objeto:slug`.")
        elif par not in eventos:
            falha("core-action-sem-evento",
                  f"`core_action: {par[0]} {par[1]}` não existe na tabela de eventos do bloco 9. "
                  f"A decisão central da missão não é emitida por nada.")
    if "perguntas_herdadas" not in fichas:
        falha("perguntas-herdadas-ausente",
              "Ficha `perguntas_herdadas` ausente: declare quais transversais (T1–T8) esta missão herda.",
              severidade="atencao")

    linhas = [l for t in _tabelas(texto, {"pq", "pergunta"}) for l in t if _RE_PQ.search(str(l))]
    if not linhas:
        falha("pq-tabela-ausente",
              "Sem tabela de perguntas de produto (sub-bloco 9f). Cabeçalho: "
              "`| PQ | Pergunta | Decisão que dispara | Corte | Etapa | Ação (verbo:objeto) | Origem |`.")
        return {"status": "bloqueado", "achados": achados, "perguntas": 0}

    if len(linhas) < PQ_POR_MISSAO:
        falha("pq-faltando",
              f"{len(linhas)} pergunta(s) de produto declarada(s); a missão fecha com {PQ_POR_MISSAO}. "
              f"Proposta não bloqueia e é marcada `[PROPOSTA — validar com PO]`: falta é lacuna, "
              f"proposta a mais é só uma linha para o PO riscar.")
    elif len(linhas) > PQ_POR_MISSAO:
        falha("pq-excedente",
              f"{len(linhas)} perguntas de produto para um teto de {PQ_POR_MISSAO}: escolha as que "
              f"mudam decisão e deixe as outras fora.", severidade="atencao")

    vistas: Dict[str, str] = {}
    acoes: set = set()
    for linha in linhas:
        m = _RE_PQ.search(" ".join(linha.values()))
        nome = m.group(0).upper() if m else "PQ-?"
        pergunta = _limpo(_col(linha, "pergunta"))
        decisao = _limpo(_col(linha, "decis"))
        corte = _limpo(_col(linha, "corte"))
        celula_acao = _col(linha, "acao", "verbo", "evento")
        origem = _limpo(_col(linha, "origem"))

        if _norm(pergunta) in _VAZIOS:
            falha("pq-sem-pergunta", f"{nome} sem pergunta.")
            continue
        if "?" not in pergunta:
            falha("pq-nao-e-pergunta",
                  f"{nome} não é uma pergunta: «{pergunta[:70]}». Se não termina em interrogação, "
                  f"não há resposta que mude decisão.")
        chave = _norm(pergunta)
        if chave in vistas:
            falha("pq-duplicada", f"{nome} repete a pergunta de {vistas[chave]}: «{pergunta[:60]}».")
        vistas[chave] = nome

        if _norm(decisao) in _VAZIOS:
            falha("pq-sem-decisao",
                  f"{nome} sem a decisão que dispara: pergunta que não muda nada é curiosidade.")
        elif not _RE_LIMIAR.search(decisao):
            falha("pq-decisao-sem-limiar",
                  f"{nome} decide «{decisao[:60]}» sem dizer a partir de quanto. Sem limiar ninguém "
                  f"sabe quando agir, e o número vira enfeite de dashboard.")

        cortes = {_norm(c) for c in re.split(r"[·,/]", corte) if c.strip()}
        if not cortes:
            falha("pq-sem-corte", f"{nome} sem corte: por quem a resposta é lida.", severidade="atencao")
        elif not (cortes & _CORTES):
            falha("pq-corte-invalido",
                  f"{nome} com corte fora do vocabulário ({', '.join(sorted(cortes))}): "
                  f"use {', '.join(sorted(_CORTES))}.", severidade="atencao")

        par = _acao(celula_acao)
        if not par:
            falha("pq-sem-acao",
                  f"{nome} não nomeia a ação que a responde no formato `verbo objeto:slug` "
                  f"(célula: «{_limpo(celula_acao)[:40] or 'vazia'}»).")
        elif eventos:
            acoes.add(par)
            if par not in eventos:
                falha("pq-acao-sem-evento",
                      f"{nome} é respondida por `{par[0]} {par[1]}`, que não existe na tabela de eventos "
                      f"do bloco 9. A pergunta não tem como ser respondida: ninguém emite esse evento.")
            elif not _mede(eventos[par]):
                falha("pq-evento-nao-mede",
                      f"{nome} aponta para `{par[0]} {par[1]}`, um evento sem `resultado` nem `contexto`: "
                      f"ele diz que aconteceu, não quanto. A pergunta pede um número que ninguém emite.")

        if origem and not re.search(r"\bPO\b|PROPOSTA", origem, re.I):
            falha("pq-origem-invalida",
                  f"{nome} com origem «{origem[:40]}»: use `PO` ou `[PROPOSTA — validar com PO]`.",
                  severidade="atencao")

    if len(linhas) >= PQ_POR_MISSAO and len(acoes) < 3 and eventos:
        falha("pq-acoes-pouco-distintas",
              f"As {len(linhas)} perguntas se apoiam em {len(acoes)} ação(ões) distinta(s): cinco leituras "
              f"do mesmo evento são uma pergunta escrita cinco vezes.", severidade="atencao")

    bloqueios = [a for a in achados if a["severidade"] == "bloqueio"]
    status = "bloqueado" if bloqueios else ("amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados, "perguntas": len(linhas)}


def relatorio_9f(resultado: Dict[str, Any], missao: str = "") -> str:
    icone = {"aprovado": "🟢 PERGUNTAS DE PRODUTO CONFORMES",
             "amarelo": "🟡 COM RESSALVAS",
             "bloqueado": "🔴 BLOQUEADO"}[resultado["status"]]
    linhas = [f"# Perguntas de produto (sub-bloco 9f) — {missao or 'missão'}", "", f"**Veredito: {icone}**", "",
              f"Perguntas declaradas: **{resultado['perguntas']}** de {PQ_POR_MISSAO}", ""]
    if resultado["achados"]:
        linhas += ["## Achados", ""]
        for a in resultado["achados"]:
            linhas.append(f"- {'❌' if a['severidade'] == 'bloqueio' else '⚠️'} **{a['codigo']}** — {a['resumo']}")
    else:
        linhas.append(f"As {PQ_POR_MISSAO} perguntas têm decisão com limiar, corte válido e uma ação "
                      f"declarada no bloco 9 que as responde com número.")
    linhas += ["", "```json", json.dumps(
        {"agente": "perguntas-check", "missao": missao, "status": resultado["status"],
         "achados": resultado["achados"]}, ensure_ascii=False, indent=2), "```"]
    return "\n".join(linhas)


def _pq_id(bruto: str) -> str:
    """`PQ01`, `pq-1`, `PQ-01` → `PQ-01`: o id é o mesmo, a grafia varia entre spec e PRD."""
    n = re.sub(r"[^0-9]", "", bruto or "")
    return f"PQ-{int(n):02d}" if n else "PQ-?"


def _pq_da_spec(spec: str) -> Dict[str, str]:
    """`PQ-nn` → pergunta, lidas do sub-bloco 9f. Vazio quando a spec não traz o bloco."""
    mapa: Dict[str, str] = {}
    for tabela in _tabelas(spec or "", {"pq", "pergunta"}):
        for linha in tabela:
            m = _RE_PQ.search(" ".join(linha.values()))
            if m:
                mapa[_pq_id(m.group(0))] = _limpo(_col(linha, "pergunta"))
    return mapa
