"""Dossiê determinístico da execução — o que passou, o que passou com ressalva, o que travou.

Por que existe: a esteira deixou de abortar no primeiro gate reprovado (ver
`agents/callbacks.py::marcar_heranca`). Ir até o fim só ajuda se, no fim, houver um
documento que explique o que aconteceu — senão o operador precisa abrir doze artefatos e
o `estado.json` para descobrir onde atuar.

Este módulo não usa modelo de linguagem. Ele lê o que os gates **já gravaram** no estado:
cada `EnvelopeGateAgent`, `BnccCheckAgent` e `RastroCheckAgent` persiste o envelope JSON
inteiro em `state["<status_key>_envelope"]`, com `achados[]`, severidade, dono e
`precisa_humano`. Essa informação estava disponível e ninguém a lia.

`GATES` é a fonte única da lista de gates da esteira — antes duplicada em
`pipeline/runner.py`, `pipeline/session_store.py` (duas vezes) e `app.py`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

#: Ordem de execução. `rodada` só existe nos gates que vivem dentro de um LoopAgent.
#: Fora desta lista de propósito: `catalogo_status` é gravado pelo registro no índice, que roda
#: DEPOIS deste diagnóstico (a missão só entra no catálogo com o status que o dossiê derivou), e
#: `diagnostico_status` é o próprio dossiê. Um cruzamento ingênuo status×dossiê acusa os dois.
GATES: List[Dict[str, Optional[str]]] = [
    {"status": "catalogo_indice_status", "rotulo": "Base de comparação do V5 (índice de missões)", "etapa": "produto", "rodada": None},
    {"status": "micro_gate_status", "rotulo": "Micro-gate do núcleo", "etapa": "produto", "rodada": "micro_gate_rodada"},
    {"status": "brief_escopo_status", "rotulo": "Brief de escopo separado do one-pager", "etapa": "produto", "rodada": None},
    {"status": "gate_estrutural_status", "rotulo": "Gate estrutural", "etapa": "produto", "rodada": "gate_estrutural_rodada"},
    {"status": "avaliacao_status", "rotulo": "Avaliação pedagógica", "etapa": "produto", "rodada": "avaliacoes_rodada"},
    {"status": "experiencia_status", "rotulo": "Experiência do estudante", "etapa": "produto", "rodada": "avaliacoes_rodada"},
    {"status": "adequacao_status", "rotulo": "Adequação pedagógica", "etapa": "produto", "rodada": "avaliacoes_rodada"},
    {"status": "gate_final_status", "rotulo": "Gate final de produto", "etapa": "produto", "rodada": None},
    {"status": "bncc_status", "rotulo": "Conformidade BNCC", "etapa": "produto", "rodada": "spec_rodada"},
    {"status": "lacunas_status", "rotulo": "Fechamento de lacunas (D0)", "etapa": "design", "rodada": None},
    {"status": "ambiente_status", "rotulo": "Ambiente simulado (D9)", "etapa": "design", "rodada": None},
    {"status": "prototipo_lint_status", "rotulo": "Lint do protótipo (arquivo)", "etapa": "design", "rodada": "qa_design_rodada"},
    {"status": "design_status", "rotulo": "QA de entregáveis", "etapa": "design", "rodada": "qa_design_rodada"},
    {"status": "manifesto_status", "rotulo": "Ficha do manifesto", "etapa": "produto", "rodada": "spec_rodada"},
    {"status": "evidencia_status", "rotulo": "Matriz de evidência pedagógica", "etapa": "produto", "rodada": "spec_rodada"},
    {"status": "perguntas_status", "rotulo": "Perguntas de produto (9f)", "etapa": "produto", "rodada": "spec_rodada"},
    {"status": "juiz_perguntas_status", "rotulo": "Juiz das perguntas de produto", "etapa": "produto", "rodada": "juiz_perguntas_rodada"},
    {"status": "telemetria_status", "rotulo": "Contrato de telemetria", "etapa": "dev", "rodada": "handoff_rodada"},
    {"status": "rastro_lacunas_status", "rotulo": "Rastro de lacunas", "etapa": "dev", "rodada": None},
    {"status": "dev_status", "rotulo": "Banca de dev", "etapa": "dev", "rodada": "banca_rodada"},
    {"status": "prd_status", "rotulo": "Pendências do PRD", "etapa": "dev", "rodada": None},
    {"status": "kpis_status", "rotulo": "Coerência KPI ↔ evento ↔ tela", "etapa": "dev", "rodada": "prd_rodada"},
]

#: Relatórios que não têm portão próprio: o parecer entra no dossiê como ressalva, nunca como
#: impedimento. É o caso da adequação pedagógica — avalia, aponta ajustes, e quem decide bloquear
#: continua sendo o gate estrutural e a avaliação pedagógica.
CONSULTIVOS = [
    # O lint de contrato de plataforma roda em modo não estrito por desenho (devolve ao autor
    # do one-pager em vez de travar), mas não aparecia em lugar nenhum do dossiê: os achados
    # dele — WebSocket na seção 8, número sem origem, SAEB fora do ano — eram invisíveis para
    # quem lia o relatório da execução.
    {"chave": "contrato_produto_report", "rotulo": "Contrato de plataforma e origem dos números", "etapa": "produto"},
]

_ICONE = {"aprovado": "🟢", "amarelo": "🟡", "bloqueado": "🔴", "devolvido": "🔴"}

#: Artefatos dos dois agentes transversais, que rodam depois deste diagnóstico.
_ESCRITOS_DEPOIS = ("diagnostico_execucao", "aprendizado_registro")

#: Severidades que impedem a missão de ser construída como está.
_BLOQUEIA = ("bloqueio",)
#: Severidades que pedem uma pessoa, não outra rodada de agente.
_HUMANO = ("decisao_humana",)


def _icone(status: str) -> str:
    return _ICONE.get(str(status or "").strip().lower(), "⚪")


def _dono(achado: Dict[str, Any], etapa_do_gate: str) -> str:
    """Quem conserta. Os gates não concordam sobre onde guardam isso — aqui é normalizado.

    `EnvelopeGateAgent` usa `agente_responsavel` com o slug do agente; `tools/rastro.py`
    usa `etapa` (input/produto/design/dev/plataforma/externo) e põe o texto livre do
    marcador em `agente_responsavel`. Sem esta normalização o dossiê mistura as duas.
    """
    for campo in ("agente_responsavel", "dono", "etapa"):
        valor = achado.get(campo)
        if valor and str(valor).lower() not in ("null", "none", ""):
            return str(valor)
    return etapa_do_gate


def coletar(state: Dict[str, Any]) -> Dict[str, Any]:
    """Lê o estado da execução e devolve o dossiê estruturado."""
    gates: List[Dict[str, Any]] = []
    achados: List[Dict[str, Any]] = []
    precisa_humano = False

    for gate in GATES:
        chave = gate["status"]
        if chave not in state:
            continue
        status = str(state.get(chave) or "")
        envelope = state.get(f"{chave}_envelope") or {}
        rodada = state.get(gate["rodada"]) if gate["rodada"] else None
        if isinstance(envelope, dict) and envelope.get("precisa_humano"):
            precisa_humano = True

        deste_gate = []
        if isinstance(envelope, dict):
            for achado in envelope.get("achados") or []:
                if not isinstance(achado, dict):
                    continue
                severidade = str(achado.get("severidade") or "").strip().lower()
                # O veredito do gate manda. A banca aprova (`nok_bloqueantes: 0`), dá ❌ num
                # critério não bloqueante e rotula o item `bloqueio`; contar isso como impedimento
                # deixava a execução 🔴 com o gate 🟢 (2026-09-21, exp06ef1b, DES-14). Só gate
                # reprovado tem impedimento; nos demais o item vira ressalva registrada.
                if severidade in _BLOQUEIA and status.strip().lower() not in ("bloqueado", "devolvido"):
                    severidade = "atencao"
                normalizado = {
                    "gate": gate["rotulo"],
                    "etapa": gate["etapa"],
                    "id": achado.get("id") or achado.get("codigo") or "—",
                    "codigo": achado.get("codigo") or "—",
                    "classe": achado.get("classe") or "",
                    "severidade": severidade,
                    "dono": _dono(achado, gate["etapa"]),
                    "resumo": (achado.get("resumo") or achado.get("trecho") or "").strip(),
                }
                deste_gate.append(normalizado)
                achados.append(normalizado)

        gates.append({
            "rotulo": gate["rotulo"],
            "etapa": gate["etapa"],
            "status": status,
            "icone": _icone(status),
            "rodadas": rodada,
            "achados": len(deste_gate),
            "bloqueios": sum(1 for a in deste_gate if a["severidade"] in _BLOQUEIA),
        })

    # pareceres consultivos: envelope lido do próprio texto, e todo achado rebaixado a ressalva
    from agents.callbacks import extrair_envelope

    for consultivo in CONSULTIVOS:
        texto = str(state.get(consultivo["chave"]) or "")
        if not texto.strip():
            continue
        envelope = extrair_envelope(texto) or {}
        status = str(envelope.get("status") or "")
        deste = []
        for achado in envelope.get("achados") or []:
            if not isinstance(achado, dict):
                continue
            severidade = str(achado.get("severidade") or "").strip().lower()
            deste.append({
                "gate": consultivo["rotulo"],
                "etapa": consultivo["etapa"],
                "id": achado.get("id") or "—",
                "codigo": achado.get("codigo") or "—",
                "classe": "parecer",
                # bloqueio de parecer consultivo vira ressalva: ele aconselha, não impede
                "severidade": "decisao_humana" if severidade in _HUMANO else "atencao",
                "dono": _dono(achado, consultivo["etapa"]),
                "resumo": (achado.get("resumo") or "").strip(),
            })
        achados.extend(deste)
        if envelope.get("precisa_humano"):
            precisa_humano = True
        gates.append({
            "rotulo": consultivo["rotulo"] + " (parecer)",
            "etapa": consultivo["etapa"],
            "status": status or "emitido",
            "icone": _icone(status),
            "rodadas": None,
            "achados": len(deste),
            "bloqueios": 0,
        })

    # Ticket que um gate emitiu e nenhum agente pôde executar: o 🔴 do gate já aparece acima,
    # mas sem isto ninguém ficava sabendo que o conserto nunca foi tentado, nem por quê.
    for ticket in state.get("tickets_sem_rota") or []:
        if not isinstance(ticket, dict):
            continue
        achados.append({
            "gate": f"{ticket.get('gate') or 'Retrabalho'} — sem quem execute",
            "etapa": "humano",
            "id": ticket.get("id") or "—",
            "codigo": "ticket-sem-rota",
            "classe": "roteamento",
            "severidade": "decisao_humana",
            "dono": ticket.get("dono") or "—",
            "resumo": f"{ticket.get('motivo', '')}: {ticket.get('resumo', '')}".strip(": "),
        })

    degradacoes = list(state.get("degradacoes") or [])
    agentes_degradados = list(state.get("agentes_degradados") or [])

    bloqueios = [a for a in achados if a["severidade"] in _BLOQUEIA]
    humanos = [a for a in achados if a["severidade"] in _HUMANO]
    ressalvas = [a for a in achados if a["severidade"] not in _BLOQUEIA and a["severidade"] not in _HUMANO]

    if degradacoes or bloqueios:
        veredito = "bloqueado"
    elif ressalvas or humanos or agentes_degradados:
        veredito = "amarelo"
    else:
        veredito = "aprovado"

    return {
        "veredito": veredito,
        "gates": gates,
        "achados": achados,
        "bloqueios": bloqueios,
        "ressalvas": ressalvas,
        "humanos": humanos,
        "degradacoes": degradacoes,
        "agentes_degradados": agentes_degradados,
        "precisa_humano": precisa_humano or bool(humanos) or bool(degradacoes),
        "reexecucoes": int(state.get("reexecucoes", 0) or 0),
    }


def _por_dono(achados: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    agrupado: Dict[str, List[Dict[str, Any]]] = {}
    for achado in achados:
        agrupado.setdefault(achado["dono"], []).append(achado)
    return dict(sorted(agrupado.items(), key=lambda kv: -len(kv[1])))


def artefatos_esperados(state: Dict[str, Any], mapa: Any) -> Dict[str, List[str]]:
    """Cruza o que a esteira deveria ter produzido com o que sobrou no estado.

    Documento ausente é sintoma: ou o agente não rodou, ou devolveu vazio. Nos dois casos
    é a primeira coisa que o operador precisa saber.
    """
    entregues, ausentes = [], []
    pares = mapa.items() if hasattr(mapa, "items") else mapa
    for chave, arquivo in pares:
        # Os dois transversais são escritos depois desta contagem — listá-los como ausentes
        # faria o dossiê acusar a própria falta.
        if chave in _ESCRITOS_DEPOIS:
            continue
        valor = state.get(chave)
        (entregues if (isinstance(valor, str) and valor.strip()) else ausentes).append(arquivo)
    return {"entregues": sorted(entregues), "ausentes": sorted(ausentes)}


def relatorio_markdown(d: Dict[str, Any], missao: str = "", artefatos: Optional[Dict[str, List[str]]] = None,
                       state: Optional[Dict[str, Any]] = None) -> str:
    """Dossiê legível. Sem chave de estado, sem nome de classe, sem log cru."""
    icone = _ICONE.get(d["veredito"], "⚪")
    linhas = [
        f"# Diagnóstico da execução — {missao or 'missão'}",
        "",
        f"**Veredito: {icone} "
        + {"aprovado": "tudo passou", "amarelo": "passou com ressalvas", "bloqueado": "há impedimentos"}[d["veredito"]]
        + f"** · {len(d['bloqueios'])} impedimento(s) · {len(d['ressalvas'])} ressalva(s) · "
        + f"{len(d['humanos'])} decisão(ões) para uma pessoa",
        "",
        "A esteira roda até o fim mesmo com gate reprovado: todos os documentos abaixo existem, e o que",
        "derivou de uma etapa reprovada está marcado `[PROVISÓRIO]` no próprio documento.",
        "",
        "## Como cada portão se saiu",
        "",
        "| Etapa | Portão | Resultado | Rodadas | Achados |",
        "|---|---|---|:-:|:-:|",
    ]
    for g in d["gates"]:
        rodadas = str(g["rodadas"]) if g["rodadas"] else "—"
        linhas.append(f"| {g['etapa']} | {g['rotulo']} | {g['icone']} {g['status'] or '—'} | {rodadas} | {g['achados']} |")

    if d["degradacoes"]:
        linhas += ["", "## O que reprovou, na ordem em que aconteceu", ""]
        for i, deg in enumerate(d["degradacoes"], 1):
            linhas.append(f"{i}. **{deg.get('gate', '?')}** — {deg.get('motivo', '')}")

    if d["bloqueios"]:
        linhas += ["", "## O que precisa ser consertado, por dono", ""]
        for dono, itens in _por_dono(d["bloqueios"]).items():
            linhas.append(f"**{dono}** — {len(itens)} item(ns)")
            for a in itens:
                classe = f" · {a['classe']}" if a["classe"] else ""
                linhas.append(f"- `{a['id']}` ({a['gate']}{classe}) — {a['resumo']}")
            linhas.append("")

    if d["humanos"]:
        linhas += ["", "## O que só uma pessoa decide", ""]
        for a in d["humanos"]:
            linhas.append(f"- `{a['id']}` ({a['gate']}) — {a['resumo']}")

    if d["ressalvas"]:
        linhas += ["", "## Ressalvas aceitas (não impedem, mas ficam registradas)", ""]
        for a in d["ressalvas"]:
            linhas.append(f"- `{a['id']}` ({a['gate']}) — {a['resumo']}")

    if d["agentes_degradados"]:
        linhas += [
            "",
            "## O que saiu provisório",
            "",
            "Estes agentes construíram depois de uma reprovação, sobre a base reprovada. O conteúdo",
            "existe e é utilizável como rascunho, mas precisa ser refeito quando o impedimento cair:",
            "",
        ]
        linhas += [f"- {nome}" for nome in d["agentes_degradados"]]

    if d.get("reexecucoes"):
        linhas += [
            "",
            "## Correções automáticas desta execução",
            "",
            f"A esteira reexecutou **{d['reexecucoes']} agente(s)** para consertar o que os portões apontaram.",
            "Isso é trabalho que ninguém precisou fazer à mão — e também o custo extra desta execução.",
        ]

    if artefatos:
        linhas += ["", "## Documentos desta execução", ""]
        linhas.append(f"- Entregues: {len(artefatos['entregues'])}")
        if artefatos["ausentes"]:
            linhas.append(f"- **Ausentes ({len(artefatos['ausentes'])})**: " + ", ".join(f"`{a}`" for a in artefatos["ausentes"]))
            linhas.append("  Documento ausente significa que o agente não produziu nada — verifique o log daquele passo.")

    linhas += ["", "## Por onde começar", ""]
    if d["bloqueios"]:
        dono, itens = next(iter(_por_dono(d["bloqueios"]).items()))
        linhas.append(f"1. **{dono}** concentra {len(itens)} dos {len(d['bloqueios'])} impedimentos — resolver ali destrava mais coisa de uma vez.")
        linhas.append(f"2. Comece por `{itens[0]['id']}`: {itens[0]['resumo']}")
    elif d["humanos"]:
        linhas.append("1. Não há impedimento técnico: o que falta são decisões listadas acima.")
    else:
        linhas.append("1. Nada travando. As ressalvas acima são opcionais e estão registradas para a próxima versão.")

    bloco = bloco_de_execucao(state or {})
    if bloco:
        linhas += ["", bloco]

    return "\n".join(linhas) + "\n"


def bloco_de_execucao(state: Dict[str, Any]) -> str:
    """Custo, modelo e reprodutibilidade — o que permite comparar duas execuções.

    O `usage_metadata` de cada evento era descartado: ninguém sabia quanto custa gerar uma
    missão, qual agente pesa, nem se a esteira está melhorando. E sem registrar modelo e seed,
    duas execuções da mesma missão não eram comparáveis.
    """
    exec_ = state.get("execucao") or {}
    if not exec_:
        return ""
    t = exec_.get("tokens") or {}
    total = t.get("entrada", 0) + t.get("saida", 0)

    def _n(valor: int) -> str:
        """Milhar com ponto, como se escreve em português."""
        return f"{valor:,}".replace(",", ".")
    linhas = ["## Execução", "",
              f"- **Modelo:** `{exec_.get('modelo', '—')}`"
              + (f" · PRD: `{exec_['modelo_prd']}`" if exec_.get("modelo_prd") and exec_["modelo_prd"] != exec_.get("modelo") else ""),
              f"- **Reprodutibilidade:** seed `{exec_.get('seed_juiz', '—')}` · temperatura dos juízes `{exec_.get('temperatura_juiz', '—')}`",
              f"- **Duração:** {exec_.get('duracao_s', 0)} s · **{t.get('chamadas', 0)} chamadas** ao modelo",
              f"- **Tokens:** {_n(total)} ({_n(t.get('entrada', 0))} de entrada, {_n(t.get('saida', 0))} de saída"
              + (f", {_n(t.get('pensamento', 0))} de raciocínio" if t.get("pensamento") else "") + ")",
              ""]
    por_agente = exec_.get("tokens_por_agente") or {}
    if por_agente:
        linhas += ["Os cinco agentes mais caros desta execução:", "",
                   "| Agente | Entrada | Saída | Chamadas |", "|---|---:|---:|---:|"]
        for nome, v in list(por_agente.items())[:5]:
            linhas.append(f"| {nome} | {_n(v['entrada'])} | {_n(v['saida'])} | {v['chamadas']} |")
        linhas.append("")
    return "\n".join(linhas)


def envelope(d: Dict[str, Any], missao: str = "") -> Dict[str, Any]:
    return {
        "agente": "diagnostico-execucao",
        "missao": missao or "",
        "status": {"aprovado": "aprovado", "amarelo": "aprovado_com_ressalvas", "bloqueado": "bloqueado"}[d["veredito"]],
        "impedimentos": len(d["bloqueios"]),
        "ressalvas": len(d["ressalvas"]),
        "decisoes_humanas": len(d["humanos"]),
        "agentes_provisorios": len(d["agentes_degradados"]),
        "achados": [
            {
                "id": a["id"],
                "severidade": a["severidade"],
                "codigo": a["codigo"],
                "classe": a["classe"],
                "agente_responsavel": a["dono"],
                "resumo": a["resumo"],
            }
            for a in d["bloqueios"] + d["humanos"]
        ],
        "precisa_humano": d["precisa_humano"],
    }
