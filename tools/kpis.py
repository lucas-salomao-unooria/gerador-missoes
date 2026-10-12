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
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

AGENTE = "kpis-check"

_RE_KPI = re.compile(r"\bKPI-?\d{1,3}\b", re.IGNORECASE)
_RE_EVT = re.compile(r"\bEVT-[UP]?\d{1,3}\b", re.IGNORECASE)
_RE_T = re.compile(r"\bT(\d{1,2})\b")
_CANON = Path(__file__).resolve().parent.parent / "prompts" / "references" / "perguntas-de-produto.md"
_RE_TELA = re.compile(r"\bE[0-6]-(?:ALU|PROF|SIS)-\d{2}\b")
_RE_ETAPA = re.compile(r"\bE[0-6]\b")
#: `E1..E6`, `E1…E6`, `E1–E6`, `E1 a E6`, `E1 até E6`. O hífen só vale seguido de `E`: `E3-ALU-02` é tela.
_RE_INTERVALO_ETAPA = re.compile(r"\bE([0-6])\s*(?:\.\.\.?|…|–|—|-(?=\s*E)|\ba\b|\bat[ée]\b)\s*E([0-6])\b", re.I)


def _etapas(texto: str) -> set:
    """Etapas citadas, com o intervalo expandido.

    «Ao entrar em cada etapa E1..E6» era lido como E1 e E6, e o `EVT-U02` — que dispara em
    todas — deixava sem evento os KPIs de E2 e E4 (exp04ef1b, 25/09/2026: dois falsos 🔴).
    """
    t = texto or ""
    etapas = set(_RE_ETAPA.findall(_RE_TELA.sub(" ", t)))
    for m in _RE_INTERVALO_ETAPA.finditer(t):
        a, b = sorted((int(m.group(1)), int(m.group(2))))
        etapas.update(f"E{n}" for n in range(a, b + 1))
    return etapas
_RE_BASELINE_ZERO = re.compile(r"^\s*\**\s*\$?\s*0\s*\\?%", re.I)
_RE_SEM_BASELINE = re.compile(r"sem baseline", re.I)
_RE_ORIGEM = re.compile(r"\(([^)]{4,})\)")
_RE_TABELA_OU_ROTA = re.compile(r"\bENT-\d|\bexp_?\d{2}_?e[fm]\d?b?_|GET\s+/|POST\s+/|\bRota\b", re.I)
_CORTES = {"rede", "escola", "missao", "serie", "turma", "professor", "etapa", "aluno", "disciplina"}
#: Os dois leitores possíveis de um evento — o mesmo nos dois gates (`kpis-check` e `prd-check`).
LEITOR_VALIDO = r"exp_?\d{2}_?e[fm]\d?b?_\w+|posthog|painel\s+de\s+produto"
MENSAGEM_LEITOR = ("Pub/Sub, `/telemetry/batch` e `telemetria_eventos` são transporte, não leitor. Se o evento "
                   "alimenta a tela da professora, o leitor é a tabela `expNNefNb_*` do módulo; se só alimenta "
                   "uma pergunta de produto do 9f, é o `painel de produto (PostHog)`.")


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


# ─── O catálogo das transversais e dos sinais universais ────────────────────────────────
#
# Na geração de 23/09 o PRD reescreveu T1 ("professores que abriram → liberaram") como "turmas
# que iniciam", e o alimentou com o evento da lupa — o primeiro da tabela. O prompt mandava usar
# "eventos `EVT-U*`", mas nenhuma referência dizia quais: o redator inventava três a cada
# execução, e para as perguntas do lado do professor não havia nenhum. A fonte única é a cerca
# JSON de `perguntas-de-produto.md`, como a BNCC é o JSON de `tools/bncc.py`.

@lru_cache(maxsize=1)
def catalogo() -> Dict[str, Any]:
    texto = _CANON.read_text(encoding="utf-8")
    m = re.search(r"```json\s*(\{.*?\})\s*```", texto, re.S)
    dados = json.loads(m.group(1))
    perguntas: Dict[str, str] = {}
    for tabela in _tabelas(texto, {"id", "dono", "sinais"}):
        for linha in tabela:
            t = _RE_T.search(_col(linha, "id"))
            if t:
                perguntas[f"T{t.group(1)}"] = _col(linha, "pergunta").strip()
    dados["perguntas"] = perguntas
    return dados


def _ids_t(celula: str) -> List[str]:
    return [f"T{n}" for n in _RE_T.findall(celula or "")]


def ia_responde_estudante(spec: str = "", prd: str = "") -> bool:
    """A condição de `T21`: a spec herda T21, ou o PRD já emite o sinal de IA ao estudante."""
    herdadas = re.search(r"perguntas_herdadas[`*_]*\s*:\s*([^\n]+)", spec or "", re.I)
    if herdadas and "T21" in _ids_t(herdadas.group(1)):
        return True
    return bool(re.search(r"\bEVT-U06\b|\bEVT-P06\b", prd or ""))


#: As transversais do grupo "customização de tema (IA)" na revisão do PO de 24/09/2026. Antes dela,
#: T15, T16 e T20 eram cobradas de toda missão, e a missão sem customização levava bloqueio por não
#: gravar `geracoes` de um `gerar-conteudo` que ela não tem.
_CUSTOMIZACAO_TS = ("T15", "T16", "T20")
_RE_CUSTOMIZACAO = re.compile(r"gerar-conteudo|customiza", re.I)
#: nome antigo da condição da IA conversacional, aceito para não quebrar catálogo anterior
_ALIAS_CONDICAO = {"ia_responde_estudante": "ia_conversacional"}


def _herdadas(spec: str) -> Optional[List[str]]:
    m = re.search(r"perguntas_herdadas[`*_]*\s*:\s*([^\n]+)", spec or "", re.I)
    return _ids_t(m.group(1)) if m else None


def condicoes_da_missao(spec: str = "", prd: str = "") -> set:
    """Os grupos de missão a que ela pertence, além do universal.

    A ficha `perguntas_herdadas` é quem diz: T21 → IA conversacional; T15, T16 ou T20 → customização
    de tema. Sem a ficha, a customização se reconhece pelo preparo (`gerar-conteudo`, customização).
    """
    ativas = set()
    if ia_responde_estudante(spec, prd):
        ativas.add("ia_conversacional")
    herdadas = _herdadas(spec)
    if herdadas is not None:
        if any(t in herdadas for t in _CUSTOMIZACAO_TS):
            ativas.add("customizacao_tema")
    elif _RE_CUSTOMIZACAO.search(spec or "") or re.search(r"\bEVT-P0[23]\b", prd or ""):
        ativas.add("customizacao_tema")
    return ativas


def sinais_exigidos(ia: bool = False, customizacao: bool = True) -> Dict[str, List[str]]:
    """Sinal → transversais que ele responde, para toda T de dono `missao` do grupo da missão."""
    ativas = {c for c, ligada in (("ia_conversacional", ia), ("customizacao_tema", customizacao)) if ligada}

    def vale(condicao: Optional[str]) -> bool:
        return not condicao or _ALIAS_CONDICAO.get(condicao, condicao) in ativas

    exigidos: Dict[str, List[str]] = {}
    for t, info in catalogo()["transversais"].items():
        if info["dono"] != "missao" or not vale(info.get("so_se")):
            continue
        for s in info["sinais"]:
            if not vale(catalogo()["sinais"][s].get("so_se")):
                continue
            exigidos.setdefault(s, []).append(t)
    return exigidos


def _palavras(texto: str) -> set:
    return {p for p in re.findall(r"[a-z]{4,}", _norm(texto))}


def _numeros(texto: str) -> set:
    return {n.replace(",", ".").rstrip("0").rstrip(".") or "0" for n in re.findall(r"\d+(?:[.,]\d+)?", texto or "")}


def _numeros_de_meta(spec: str, one_pager: str) -> set:
    """Os números que podem ser meta: os do §17 do one-pager e os do bloco 9 da spec (onde mora o 9f)."""
    from tools import bncc
    from tools.conteudo_aprovado import secao

    return _numeros(secao(one_pager or "", 17) or "") | _numeros(bncc.secao_bloco(spec or "", 9) or "")


def validar_kpis(prd: str, spec: str = "", one_pager: str = "") -> Dict[str, Any]:
    texto = prd or ""
    origem_das_metas = _numeros_de_meta(spec, one_pager)
    achados: List[Dict[str, str]] = []

    def falha(codigo: str, resumo: str, severidade: str = "bloqueio") -> None:
        achados.append({"severidade": severidade, "codigo": codigo, "etapa": "dev", "resumo": resumo})

    if not texto.strip():
        falha("prd-vazio", "PRD vazio: não há KPI a conferir.")
        return {"status": "bloqueado", "achados": achados, "kpis": 0, "eventos": 0}

    # A tabela de eventos com uma coluna «KPI» de volta (qual KPI o evento alimenta) é rastro, não
    # declaração de KPI. Lida como tabela de KPIs, cada evento virava um KPI sem pergunta, decisão
    # nem baseline: 27 bloqueios num PRD cujos 11 KPIs estavam completos (24/09/2026).
    tab_kpi = [l for t in _tabelas(texto, {"kpi"}) if not {"quando dispara", "quando grava"} & set(t[0])
               for l in t if _RE_KPI.search(str(l))]
    # Os `EVT-P*` são colunas do módulo, não eventos de telemetria, e o catálogo os ensina numa tabela
    # própria (`| Sinal | Objeto | Quando grava | Onde fica | Responde |`). O gate só lia a de «Quando
    # dispara»: o PRD que copiou o catálogo à risca levou 13 achados de sinal «inexistente» (24/09/2026).
    tab_evt = [l for t in _tabelas(texto, {"quando dispara"}) + _tabelas(texto, {"quando grava"}) for l in t]
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
    onde_do_sinal: Dict[str, str] = {}
    verbo_objeto: Dict[str, tuple] = {}
    # O caminho de cada evento (coluna «Caminho» da tabela de eventos). Evento OPERACIONAL não passa por `track`: é
    # a rota do módulo gravando uma coluna, e o que ele «carrega» em `resultado`/`contexto` na tabela é o corpo da
    # rota, não telemetria — não há evento em lugar nenhum para o KPI contar (exp01ef1b, 07/10/2026).
    caminho_do_evento: Dict[str, str] = {}
    for linha in tab_evt:
        caminho = _norm(_col(linha, "caminho"))
        for i in _RE_EVT.findall(" ".join(linha.values())):
            if caminho:
                caminho_do_evento.setdefault(i.upper(), caminho)
    for linha in tab_evt:
        for i in _RE_EVT.findall(" ".join(linha.values())):
            verbo_objeto.setdefault(i.upper(), (_norm(_col(linha, "verbo")), _norm(_col(linha, "objeto"))))
    # Os `EVT-P*` também valem declarados em lista, com o id e o objeto do catálogo — o redator alternou
    # entre tabela de eventos, tabela do catálogo e lista em três rodadas da mesma missão (24/09/2026), e
    # os três trazem o que importa. O formato é estrito de propósito: citação solta na prosa não conta.
    for m in re.finditer(r"^\s*[-*]\s*`?(EVT-P\d{2})`?\s*\(\s*`?([a-z_]+:[a-z_]+)`?\s*\)", texto, re.M | re.I):
        verbo_objeto.setdefault(m.group(1).upper(), ("", _norm(m.group(2))))
        tela_do_evento.setdefault(m.group(1).upper(), set())
    for linha in tab_evt:
        ids = _RE_EVT.findall(" ".join(linha.values()))
        if not ids:
            continue
        # A etapa é FALLBACK, não soma: `\bE[0-6]\b` casa "E3" dentro de "E3-ALU-02" (o hífen é
        # fronteira de palavra), e aí "E3" == "E3" fazia qualquer par de telas casar — o gate
        # aprovava justamente o caso que existe para pegar.
        telas = set(_RE_TELA.findall(" ".join(linha.values())))
        if not telas:
            telas = _etapas(_col(linha, "quando dispara"))
        # O payload vem só de tabela com coluna `resultado`/`contexto`, e SOMA entre tabelas. Antes a
        # última tabela ganhava: a «Sinais do professor» (`| Sinal | Objeto | Quando grava | Onde fica |`)
        # zerava o payload dos mesmos ids, e o gate dizia «carrega nenhum campo» (29/09/2026).
        tem_payload = any("resultado" in k or "contexto" in k for k in linha)
        for i in ids:
            iu = i.upper()
            tela_do_evento.setdefault(iu, set()).update(telas)
            if iu.startswith("EVT-P"):
                # `EVT-P*` não passa por `track`: é a escrita de uma coluna do módulo, sem payload —
                # o que o redator escrever em `resultado` para ele é ficção. Guarda-se onde ele grava.
                onde = _col(linha, "onde fica") or _col(linha, "onde e lido")
                if onde and ("onde fica" in " ".join(linha) or iu not in onde_do_sinal):
                    onde_do_sinal[iu] = onde.strip()
            elif tem_payload:
                payload_do_evento[iu] = (payload_do_evento.get(iu, "") + " " + _col(linha, "resultado")
                                         + " " + _col(linha, "contexto"))

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

        # KPI que herda uma transversal usa a pergunta dela e só os sinais que o catálogo lista
        for t in _ids_t(_col(linha, "pq")):
            info = catalogo()["transversais"].get(t)
            if not info:
                falha("kpi-herdada-inexistente",
                      f"{nome} herda `{t}`, que não existe: as transversais são T1–T21 de "
                      f"`references/perguntas-de-produto.md`.")
                continue
            if info["dono"] == "plataforma":
                falha("kpi-herdada-plataforma",
                      f"{nome} herda `{t}`, que só a plataforma responde (hub ou api): a missão não tem "
                      f"o dado. Tire o KPI e cite `{t}` como pendência de plataforma.", severidade="atencao")
                continue
            fora = [e for e in eventos if e not in info["sinais"]]
            if fora:
                falha("kpi-herdada-evento",
                      f"{nome} herda `{t}` e é alimentado por {', '.join(f'`{e}`' for e in fora)}, que não "
                      f"responde a ela. `{t}` se responde com {', '.join(f'`{s}`' for s in info['sinais'])} "
                      f"do catálogo — o mesmo em toda missão, para que as missões se comparem.")
            canonica = catalogo()["perguntas"].get(t, "")
            escrita = _col(linha, "pergunta")
            if canonica and escrita:
                a, b = _palavras(canonica), _palavras(escrita)
                if a and len(a & b) / len(a) < 0.4:
                    falha("kpi-herdada-reescrita",
                          f"{nome} herda `{t}` mas pergunta outra coisa: «{escrita.strip()[:70]}». A "
                          f"transversal não se reinventa: «{canonica[:90]}».", severidade="atencao")

        for e in eventos:
            if tab_evt and e not in tela_do_evento:
                falha("kpi-evento-inexistente", f"{nome} cita `{e}`, que não existe na tabela de eventos.")
                continue
            telas_kpi = set(_RE_TELA.findall(" ".join(linha.values())))
            if not telas_kpi:
                telas_kpi = _etapas(_col(linha, "tela"))
            telas_evt = tela_do_evento.get(e, set())
            if telas_kpi and telas_evt:
                casa = any(tk == te or tk.startswith(te) or te.startswith(tk) for tk in telas_kpi for te in telas_evt)
                if not casa:
                    # a mensagem traz a saída: sem ela o redator consertou 25 de 27 achados na
                    # rodada 2 de 23/09 e deixou estes, que só diziam o que estava errado
                    na_tela = sorted(ev for ev, ts in tela_do_evento.items()
                                     if any(tk == te or tk.startswith(te) or te.startswith(tk)
                                            for tk in telas_kpi for te in ts))
                    saida = (f"Na tela do KPI disparam {', '.join(f'`{x}`' for x in na_tela)}."
                             if na_tela else "Nenhum evento da tabela dispara nessa tela: acrescente o "
                             "evento que a mede, ou corrija a coluna Tela.")
                    # o KPI-20 da exp01ef1b mede uma sequência E2→E4; a dica antiga só mandava trocar o
                    # evento, e trocá-lo derrubaria a medida (07/10/2026)
                    saida += (f" Se o KPI mede uma sequência de etapas, a correção é ampliar a coluna Tela para "
                              f"{sorted(telas_kpi | telas_evt)}, não trocar o evento.")
                    falha("kpi-tela-divergente",
                          f"{nome} mede {sorted(telas_kpi)} e é alimentado por `{e}`, que dispara em "
                          f"{sorted(telas_evt)}. O número vai sair e não vai medir o que o KPI diz. {saida}")

        # O campo do cálculo tem de estar em ALGUM evento que o cálculo usa — não em todos os da célula.
        # Cobrar cada campo de cada evento acusava `count(EVT-U05 com resultado.codigo) vs count(EVT-U04
        # com resultado.segundos_sem_acao)` duas vezes, e um evento listado na célula mas fora da conta
        # (KPI-06 da exp01ef1b, 29/09/2026) pagava por um campo que ninguém pediu a ele.
        calculo = _col(linha, "como calcula", "calculo")
        campos = list(dict.fromkeys(re.findall(r"(?:resultado|contexto)\.(\w+)", calculo)))
        usados = list(dict.fromkeys(x.upper() for x in _RE_EVT.findall(calculo))) or eventos
        usados = [x for x in usados if not tab_evt or x in tela_do_evento]
        # KPI que conta `resultado.*`/`contexto.*` de evento operacional: medido nas sete sessões, a exp01ef1b
        # (KPI-13/15/17: `resultado.voto`, `.metodo`, `.alt_id` de `EVT-002/006/008`, operacionais), a exp06ef1b
        # (KPI-16/17) e a exp04ef1b (KPI-02/03/05/06). O voto está em `exp01ef1b_sessoes.voto_emocional`, e é essa
        # coluna que o cálculo lê. ⚠️: o número sai, mas de uma telemetria que ninguém emite.
        operacionais = [x for x in usados if caminho_do_evento.get(x, "").startswith("operac")]
        if campos and operacionais:
            falha("kpi-operacional-com-resultado",
                  f"{nome} calcula com `{', '.join(campos)}` de {', '.join(f'`{x}`' for x in operacionais)}, de caminho "
                  f"operacional: evento operacional não passa por `track` — é a rota do módulo gravando uma coluna, e "
                  f"não existe `resultado` nem `contexto` para contar. Calcule com a coluna que a rota grava (a da "
                  f"seção 11, como em `count(<id>_sessoes.<coluna> = '<valor>')`), ou, se o número é de produto e "
                  f"não da professora, emita o evento também pelo caminho analítico.", severidade="atencao")
        if campos and usados:
            sinais_p = [x for x in usados if x.startswith("EVT-P")]
            carregam = {x: set(re.findall(r'"(\w+)"\s*:', payload_do_evento.get(x, "")))
                        for x in usados if x not in sinais_p}
            disponiveis = set().union(*carregam.values())
            faltando = [c for c in campos if c not in disponiveis]
            if faltando:
                partes = []
                if carregam:
                    partes.append("; ".join(
                        f"`{x}` carrega {', '.join(f'`{c}`' for c in sorted(cs)) or 'nenhum campo'}"
                        for x, cs in carregam.items())
                        + ": reescreva o cálculo com eles, ou acrescente o campo ao evento que o mede.")
                if sinais_p:
                    onde = "; ".join(f"`{x}` → {onde_do_sinal[x]}" for x in sinais_p if x in onde_do_sinal)
                    partes.append(
                        f"{', '.join(f'`{x}`' for x in sinais_p)} "
                        f"{'é sinal' if len(sinais_p) == 1 else 'são sinais'} do professor: o hub não tem `track`, "
                        f"o sinal é a escrita de uma coluna do módulo e não tem `resultado` nem `contexto`. "
                        f"Calcule com a coluna onde ele grava" + (f" ({onde})" if onde else "")
                        + ", e não invente campo de payload para ele.")
                falha("payload-nao-computa",
                      f"{nome} calcula com `{', '.join(faltando)}`, que nenhum evento do cálculo carrega. "
                      + " ".join(partes) + " Coluna de tabela do módulo não é campo do evento.")

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

        # Meta é decisão do PO: só vale o número que o §17 do one-pager ou o 9f da spec fixam. Os 23 alvos do
        # PRD da exp01ef1b (≥75%, ≥85%, ≤1,4…) não estavam em lugar nenhum — o exemplo do gabarito trazia
        # `≥ 70%` e o redator o imitou (auditoria de 07/10/2026).
        alvo = _col(linha, "alvo", "meta")
        if alvo and "[PROPOSTA" not in alvo.upper() and not re.search(r"sem meta", alvo, re.I):
            inventados = sorted(_numeros(alvo) - origem_das_metas)
            if inventados:
                falha("kpi-alvo-inventado",
                      f"{nome} tem alvo `{alvo.strip()[:40]}` e o número não está no §17 do one-pager nem no 9f da spec. "
                      "Meta é decisão do PO: escreva `sem meta — primeira medição`, ou marque "
                      "`[PROPOSTA — validar com PO: <meta> · por quê]`.")

    # a leitura precisa ter leitor: a fila analítica não é lugar onde alguém lê
    for linha in tab_evt:
        onde = _col(linha, "onde e lido", "tabela leitora", "leitor")
        if onde and re.search(r"/telemetry/(batch|beacon)|telemetria_eventos|pub/?sub", onde, re.I) \
                and not re.search(LEITOR_VALIDO, onde, re.I):
            ids = _RE_EVT.findall(" ".join(linha.values()))
            falha("leitura-sem-leitor",
                  f"`{ids[0] if ids else 'evento'}` declara leitura em `{onde.strip()[:40]}`. {MENSAGEM_LEITOR}")

    # Os sinais universais das transversais de dono `missao` estão na tabela, com o id, o verbo e
    # o objeto do catálogo. É o que a missão deve às perguntas do PO — mesmo sem KPI próprio para
    # elas, que se leem comparando missões no painel de produto.
    if tab_evt:
        # Com spec, é ela quem diz se a IA responde ao estudante (T21 herdada). O PRD não pode decidir
        # isso por si: em 24/09/2026 o redator pôs `EVT-U06` no KPI de espera (T12) de uma missão cuja IA
        # só atua no preparo docente, o gate leu "o PRD emite sinal de IA" e passou a exigir o `EVT-P06`
        # de custo — mandou acrescentar um evento de algo que não existe, quando o certo era tirar o outro.
        # «Emite» é estar na tabela de eventos ou na coluna de evento de um KPI — não ser citado na
        # prosa: o PRD refeito dizia "expurgo definitivo de `EVT-U06`" no changelog e o gate lia a
        # própria remoção como emissão (24/09/2026).
        emitido_em = " ".join(" ".join(l.values()) for l in tab_evt) + " " + \
                     " ".join(_col(l, "evento", "evt", "alimenta") for l in tab_kpi)
        emitidos = [s for s in ("EVT-U06", "EVT-P06") if re.search(rf"\b{s}\b", emitido_em)]
        ia_prd = bool(emitidos)
        ia = ia_responde_estudante(spec, "") if (spec or "").strip() else ia_prd
        if ia_prd and not ia:
            falha("sinal-ia-sem-ia-ao-estudante",
                  f"O PRD emite {', '.join(f'`{s}`' for s in emitidos)}, sinal de IA que responde ao estudante, "
                  f"mas a spec não herda `T21`: nesta missão a IA não fala com o aluno. Tire "
                  f"{'o evento' if len(emitidos) == 1 else 'os eventos'} da tabela e dos KPIs (em `T12`, a "
                  f"espera vem só de não entender o que fazer) — ou, se a IA responde mesmo ao estudante, "
                  f"a spec precisa herdar `T21`.")
        # o grupo "customização de tema" vem da spec (T15/T16/T20 herdadas); sem spec, do próprio PRD
        custom = ("customizacao_tema" in condicoes_da_missao(spec)) if (spec or "").strip() \
            else bool(re.search(r"\bEVT-P0[123]\b", emitido_em))
        for s, ts in sorted(sinais_exigidos(ia, custom).items()):
            canon = catalogo()["sinais"][s]
            if s not in verbo_objeto:
                forma = f"`{canon['verbo']} {canon['objeto']}`" if canon.get("verbo") else f"objeto `{canon['objeto']}`"
                falha("sinal-universal-ausente",
                      f"`{s}` ({forma}) não está na tabela de eventos: é o sinal que responde a "
                      f"{', '.join(ts)}. Copie a linha do catálogo de `references/perguntas-de-produto.md`.")
                continue
            verbo, objeto = verbo_objeto[s]
            errado = (canon.get("verbo") and verbo and canon["verbo"] not in verbo) or \
                     ("<" not in canon["objeto"] and objeto and canon["objeto"] not in objeto)
            if errado:
                falha("sinal-universal-divergente",
                      f"`{s}` está como `{verbo} {objeto}`; no catálogo é "
                      f"`{canon.get('verbo', '')} {canon['objeto']}`. O id universal é o mesmo em toda "
                      f"missão — reaproveitá-lo para outro evento quebra a comparação entre missões.")

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
        ids = ", ".join(sorted(set(_ids_t(herdar.group(1))), key=lambda t: int(t[1:])))
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
# com o juiz LLM logo atrás (`prompts/produto/041_juiz_perguntas.md`).

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
    # As universais sempre; as de customização de tema quando a spec tem o preparo com IA (o grupo se
    # reconhece pelo texto, porque a ficha é justamente o que se está conferindo); T21 nunca é cobrada
    # — só a spec sabe se a IA fala com o aluno, e declarar é o que a põe no grupo.
    customiza = bool(_RE_CUSTOMIZACAO.search(re.sub(r"perguntas_herdadas[^\n]*", "", texto)))
    missao_ts = [t for t, i in catalogo()["transversais"].items() if i["dono"] == "missao"
                 and (not i.get("so_se") or (customiza and i.get("so_se") == "customizacao_tema"))]
    if "perguntas_herdadas" not in fichas:
        falha("perguntas-herdadas-ausente",
              f"Ficha `perguntas_herdadas` ausente: a missão herda as transversais de dono `missao` do "
              f"seu grupo ({', '.join(missao_ts)}; T15, T16 e T20 só com customização de tema por IA; "
              f"T21 só com IA conversacional em tempo real).", severidade="atencao")
    else:
        declaradas = _ids_t(fichas["perguntas_herdadas"])
        for t in declaradas:
            info = catalogo()["transversais"].get(t)
            if not info:
                falha("herdada-inexistente", f"`perguntas_herdadas` cita `{t}`, que não existe (T1–T21).")
            elif info["dono"] == "plataforma":
                falha("herdada-plataforma",
                      f"`{t}` é de dono `plataforma`: só o hub ou a api respondem, e a missão não tem o dado. "
                      f"Tire da ficha.", severidade="atencao")
        faltam = [t for t in missao_ts if t not in declaradas]
        if faltam:
            falha("herdada-faltando",
                  f"`perguntas_herdadas` deixa de fora {', '.join(faltam)}, de dono `missao` e do grupo desta "
                  f"missão: ela as herda, e emite os sinais delas.", severidade="atencao")

    # Os eventos universais do estudante nascem no bloco 9: é dele que o handoff e o PRD copiam.
    # (`EVT-U03` é o `completed` que a própria SDK emite no `concluir()`; os `EVT-P*` são colunas
    # do módulo e são conferidos no PRD.)
    if eventos:
        ativas = condicoes_da_missao(texto)
        for s, ts in sorted(sinais_exigidos("ia_conversacional" in ativas, "customizacao_tema" in ativas).items()):
            canon = catalogo()["sinais"][s]
            if not s.startswith("EVT-U") or "<" in canon["objeto"]:
                continue
            if (canon["verbo"], canon["objeto"]) not in eventos:
                falha("sinal-universal-ausente",
                      f"A tabela de eventos do bloco 9 não tem `{canon['verbo']} {canon['objeto']}` "
                      f"(`{s}`), o sinal universal que responde a {', '.join(ts)}. Copie a linha do "
                      f"catálogo de `references/perguntas-de-produto.md`.")

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
