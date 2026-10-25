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

import re
from typing import Any, Dict, List, Optional

#: Ordem de execução. `rodada` só existe nos gates que vivem dentro de um LoopAgent.
#: Fora desta lista de propósito: `catalogo_status` é gravado pelo registro no índice, que roda
#: DEPOIS deste diagnóstico (a missão só entra no catálogo com o status que o dossiê derivou), e
#: `diagnostico_status` é o próprio dossiê. Um cruzamento ingênuo status×dossiê acusa os dois.
GATES: List[Dict[str, Optional[str]]] = [
    {"status": "catalogo_indice_status", "rotulo": "Base de comparação do V5 (índice de missões)", "etapa": "produto", "rodada": None},
    {"status": "micro_gate_status", "rotulo": "Micro-gate do núcleo", "etapa": "produto", "rodada": "micro_gate_rodada"},
    {"status": "profundidade_status", "rotulo": "Profundidade pedagógica", "etapa": "produto", "rodada": "profundidade_rodada"},
    {"status": "mecanica_status", "rotulo": "Conta da virada", "etapa": "produto", "rodada": "nucleo_rodada"},
    {"status": "fidelidade_nucleo_status", "rotulo": "Fidelidade ao pedido do PO (núcleo)", "etapa": "produto", "rodada": "nucleo_rodada"},
    {"status": "evidencia_one_pager_status", "rotulo": "Contrato de evidência do one-pager (§12a)", "etapa": "produto", "rodada": "comite_canais_rodada"},
    {"status": "comite_canal_a_status", "rotulo": "Comitê dos canais — painel A (mecânica e Canal A)", "etapa": "produto", "rodada": "comite_canal_a_rodada"},
    {"status": "comite_canal_b_status", "rotulo": "Comitê dos canais — painel B (Canal B)", "etapa": "produto", "rodada": "comite_canal_b_rodada"},
    {"status": "brief_escopo_status", "rotulo": "Brief de escopo separado do one-pager", "etapa": "produto", "rodada": None},
    {"status": "gate_estrutural_status", "rotulo": "Gate estrutural", "etapa": "produto", "rodada": "gate_estrutural_rodada"},
    {"status": "avaliacao_status", "rotulo": "Avaliação pedagógica", "etapa": "produto", "rodada": "avaliacoes_rodada"},
    {"status": "experiencia_status", "rotulo": "Experiência do estudante", "etapa": "produto", "rodada": "avaliacoes_rodada"},
    {"status": "adequacao_status", "rotulo": "Adequação pedagógica", "etapa": "produto", "rodada": "avaliacoes_rodada"},
    {"status": "mecanica_one_pager_status", "rotulo": "Conta da virada no one-pager", "etapa": "produto", "rodada": "comite_final_rodada"},
    {"status": "comite_final_status", "rotulo": "Comitê final — pedagogia, qualidade e imersão", "etapa": "produto", "rodada": "comite_final_rodada"},
    {"status": "gate_final_status", "rotulo": "Gate final de produto", "etapa": "produto", "rodada": None},
    {"status": "bncc_status", "rotulo": "Conformidade BNCC", "etapa": "produto", "rodada": "spec_rodada"},
    {"status": "fidelidade_status", "rotulo": "Fidelidade ao pedido do PO e ao briefing", "etapa": "produto", "rodada": None},
    {"status": "completude_status", "rotulo": "Completude da spec (produto)", "etapa": "produto", "rodada": "spec_rodada"},
    {"status": "lacunas_status", "rotulo": "Fechamento de lacunas (D0)", "etapa": "design", "rodada": None},
    {"status": "ambiente_status", "rotulo": "Ambiente simulado (D9)", "etapa": "design", "rodada": None},
    {"status": "conteudo_aprovado_spec_design_status", "rotulo": "Spec consolidada × one-pager aprovado", "etapa": "design", "rodada": "qa_design_rodada"},
    {"status": "prototipo_lint_status", "rotulo": "Lint do protótipo (arquivo)", "etapa": "design", "rodada": "qa_design_rodada"},
    {"status": "consistencia_status", "rotulo": "Coerência entre documentos", "etapa": "design", "rodada": None},
    {"status": "stitch_status", "rotulo": "Telas no Stitch × inventário", "etapa": "design", "rodada": "qa_design_rodada"},
    {"status": "cobertura_telas_status", "rotulo": "Cobertura de telas por ID", "etapa": "design", "rodada": "qa_design_rodada"},
    {"status": "textos_chave_status", "rotulo": "Textos-chave na copy", "etapa": "design", "rodada": "qa_design_rodada"},
    {"status": "arestas_status", "rotulo": "Fluxo e telas × bloco 2 da spec", "etapa": "design", "rodada": "qa_design_rodada"},
    {"status": "qa_afirmacoes_status", "rotulo": "Afirmações do QA conferidas", "etapa": "design", "rodada": "qa_design_rodada"},
    # o board ausente não fica em silêncio (V13, exp06ef1b): 🟡 sem bloquear, ⚪ com o Miro desligado (C4, 24/10/2026)
    {"status": "miro_status", "rotulo": "Espelho dos diagramas no Miro", "etapa": "design", "rodada": None},
    {"status": "design_status", "rotulo": "QA de entregáveis", "etapa": "design", "rodada": "qa_design_rodada"},
    {"status": "rastro_design_status", "rotulo": "Rastro de lacunas do design", "etapa": "design", "rodada": None},
    {"status": "manifesto_status", "rotulo": "Ficha do manifesto", "etapa": "produto", "rodada": "spec_rodada"},
    {"status": "evidencia_status", "rotulo": "Matriz de evidência pedagógica", "etapa": "produto", "rodada": "spec_rodada"},
    {"status": "perguntas_status", "rotulo": "Perguntas de produto (9f)", "etapa": "produto", "rodada": "spec_rodada"},
    {"status": "juiz_perguntas_status", "rotulo": "Juiz das perguntas de produto", "etapa": "produto", "rodada": "juiz_perguntas_rodada"},
    {"status": "rastro_spec_status", "rotulo": "Rastro de lacunas da spec", "etapa": "produto", "rodada": "spec_rodada"},
    {"status": "conteudo_aprovado_spec_status", "rotulo": "Spec × one-pager aprovado", "etapa": "produto", "rodada": "spec_rodada"},
    {"status": "banca_produto_status", "rotulo": "Banca de produto (fim de produto)", "etapa": "produto", "rodada": "spec_rodada"},
    {"status": "banca_design_status", "rotulo": "Banca de design (fim de design)", "etapa": "design", "rodada": "qa_design_rodada"},
    {"status": "banca_entrada_status", "rotulo": "Banca de entrada do dev (segunda verificação)", "etapa": "dev", "rodada": None},
    {"status": "conteudo_aprovado_resumido_status", "rotulo": "Resumido × one-pager aprovado", "etapa": "produto", "rodada": "resumido_rodada"},
    {"status": "one_pager_po_status", "rotulo": "One-pager do PO preservado", "etapa": "produto", "rodada": "one_pager_po_rodada"},
    {"status": "fidelidade_design_status", "rotulo": "Fidelidade ao refazer de design", "etapa": "design", "rodada": None},
    {"status": "fidelidade_dev_status", "rotulo": "Fidelidade ao refazer de dev", "etapa": "dev", "rodada": None},
    {"status": "conteudo_status", "rotulo": "Banco de conteúdo", "etapa": "dev", "rodada": "banco_rodada"},
    {"status": "telemetria_status", "rotulo": "Contrato de telemetria", "etapa": "dev", "rodada": "handoff_rodada"},
    {"status": "montagem_handoff_status", "rotulo": "Handoff monta, não decide", "etapa": "dev", "rodada": "handoff_rodada"},
    {"status": "rastro_lacunas_status", "rotulo": "Rastro de lacunas", "etapa": "dev", "rodada": None},
    {"status": "dev_status", "rotulo": "Banca de dev", "etapa": "dev", "rodada": "banca_rodada"},
    {"status": "prd_status", "rotulo": "Pendências do PRD", "etapa": "dev", "rodada": None},
    {"status": "kpis_status", "rotulo": "Coerência KPI ↔ evento ↔ tela", "etapa": "dev", "rodada": "prd_rodada"},
    {"status": "conteudo_aprovado_prd_status", "rotulo": "PRD × one-pager aprovado", "etapa": "dev", "rodada": "prd_rodada"},
    {"status": "montagem_prd_status", "rotulo": "PRD monta, não decide", "etapa": "dev", "rodada": "prd_rodada"},
    {"status": "coerencia_prd_status", "rotulo": "Coerência do PRD com o one-pager aprovado", "etapa": "dev", "rodada": "prd_rodada"},
    # o pedagógico fecha o design desde o PR 10 (24/10/2026); o dev só acrescenta as pendências dele
    {"status": "coerencia_pedagogico_status", "rotulo": "Coerência do pedagógico com o one-pager aprovado", "etapa": "design", "rodada": "pedagogico_rodada"},
    {"status": "conteudo_aprovado_pedagogico_status", "rotulo": "Pedagógico × one-pager aprovado", "etapa": "design", "rodada": "pedagogico_rodada"},
    {"status": "montagem_pedagogico_status", "rotulo": "Pedagógico monta, não decide", "etapa": "design", "rodada": "pedagogico_rodada"},
    {"status": "pedagogico_dev_status", "rotulo": "Pedagógico aprovado, no dev", "etapa": "dev", "rodada": None},
    {"status": "rastreabilidade_status", "rotulo": "Matriz de rastreabilidade (produto → design)", "etapa": "design", "rodada": None},
    {"status": "rastreabilidade_dev_status", "rotulo": "Matriz de rastreabilidade (produto → design → dev)", "etapa": "dev", "rodada": None},
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
#: A ficha do catálogo é gravada pelo A129, que roda depois do dossiê: as gerações de 23/09 a
#: listavam como "ausente" com o arquivo presente na pasta.
_ESCRITOS_DEPOIS = ("diagnostico_execucao", "aprendizado_registro", "ficha_catalogo")

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
    from tools import liberacao
    from tools.envelope_relatorio import envelope_do_gate

    gates: List[Dict[str, Any]] = []
    achados: List[Dict[str, Any]] = []
    precisa_humano = False
    # O parecer humano em vigor (`pareceres_humanos`, copiados pela rodada final): o 🔴 que uma pessoa viu e liberou não é
    # impedimento. O dossiê da exp02em1b (60cfa7f4, 22/10/2026) dizia «4 impedimento(s)» com a exceção do admin no design
    # e o de acordo de dev dados (`tools/liberacao.py`).
    pareceres = [p for p in (state.get("pareceres_humanos") or []) if isinstance(p, dict)]

    for gate in GATES:
        chave = gate["status"]
        if chave not in state:
            continue
        status = str(state.get(chave) or "")
        # o envelope que concorda com o status gravado (`tools/envelope_relatorio.py`, 8ce9c32d de 25/09/2026)
        envelope = envelope_do_gate(state, chave)
        liberado = liberacao.gate_liberado(state, chave, pareceres) if pareceres else None
        rodada = state.get(gate["rodada"]) if gate["rodada"] else None
        pede_pessoa = isinstance(envelope, dict) and bool(envelope.get("precisa_humano"))
        if pede_pessoa:
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
                resumo = (achado.get("resumo") or achado.get("trecho") or "").strip()
                if chave == "dev_status":
                    prd_final = str(state.get("prd_final") or "")
                    ids_citados = re.findall(r"`([A-Za-z0-9_./:-]{3,})`", resumo)
                    if prd_final and ids_citados and all(i in prd_final for i in ids_citados):
                        resumo = f"{resumo} [tratado no PRD — conferir]".strip()
                if severidade in _BLOQUEIA and liberado:
                    # liberado por uma pessoa que viu o gate em 🔴: fica registrado, não impede
                    severidade = "atencao"
                    resumo = f"[liberado por pessoa — {liberacao.descricao(liberado)}] {resumo}".strip()
                normalizado = {
                    "gate": gate["rotulo"],
                    "etapa": gate["etapa"],
                    "id": achado.get("id") or achado.get("codigo") or "—",
                    "codigo": achado.get("codigo") or "—",
                    "classe": achado.get("classe") or "",
                    "severidade": severidade,
                    "dono": _dono(achado, gate["etapa"]),
                    "resumo": resumo,
                }
                deste_gate.append(normalizado)
                achados.append(normalizado)

        # O gate pediu uma pessoa e nenhum achado dele diz qual decisão: as ressalvas dele SÃO a
        # decisão. Sem isto, a banca da missão do 9º ano gravou `precisa_humano: true` e o texto do
        # mesmo dossiê disse "Nada travando. As ressalvas são opcionais" (06/10/2026).
        if pede_pessoa and not any(a["severidade"] in _HUMANO for a in deste_gate):
            for a in deste_gate:
                if a["severidade"] not in _BLOQUEIA:
                    a["severidade"] = "decisao_humana"
            if not deste_gate:
                item = {"gate": gate["rotulo"], "etapa": gate["etapa"], "id": "—", "codigo": "precisa-humano",
                        "classe": "", "severidade": "decisao_humana", "dono": gate["etapa"],
                        "resumo": "O gate pediu uma decisão de pessoa e não disse qual: leia o relatório dele."}
                deste_gate.append(item)
                achados.append(item)

        gates.append({
            "rotulo": gate["rotulo"],
            "etapa": gate["etapa"],
            "status": status,
            "icone": _icone(status),
            "rodadas": rodada,
            "achados": len(deste_gate),
            "bloqueios": sum(1 for a in deste_gate if a["severidade"] in _BLOQUEIA),
            "liberado": liberacao.descricao(liberado),
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

    # Resposta cortada pelo limite de saída do modelo que ninguém refez (`agents.callbacks.registrar_corte_do_modelo`): o
    # documento está incompleto. Na 3ef2b (e2e de 25/10/2026) o one-pager cortado em 218 mil caracteres passava calado.
    cortes = state.get("cortes_do_modelo")
    for corte in cortes.values() if isinstance(cortes, dict) else []:
        if not isinstance(corte, dict):
            continue
        achados.append({
            "gate": "Resposta cortada pelo modelo", "etapa": "esteira", "id": corte.get("agente") or "—",
            "codigo": "documento-cortado-pelo-modelo", "classe": "esteira", "severidade": "bloqueio", "dono": "esteira",
            "resumo": (f"O {corte.get('agente')} passou do limite de saída do modelo e foi cortado em "
                       f"{corte.get('caracteres')} caracteres: o documento `{corte.get('chave')}` está incompleto."),
        })
    # A troca que a esteira quis fazer no one-pager do PO grande e não se aplicou (`tools/one_pager_grande.py`): o texto
    # ficou como estava, e a mudança é decisão do PO.
    trocas_vistas: set = set()
    for item in state.get("trocas_nao_aplicadas") or []:
        if not isinstance(item, dict):
            continue
        chave_troca = (str(item.get("papel") or ""), str(item.get("de") or "")[:160], str(item.get("para") or "")[:160], str(item.get("falha") or "")[:120])
        if chave_troca in trocas_vistas:
            continue
        trocas_vistas.add(chave_troca)
        sem_troca = not str(item.get("de") or "").strip()
        achados.append({
            "gate": "One-pager montado por trocas", "etapa": "produto", "id": item.get("papel") or "—",
            "codigo": "editor-sem-trocas" if sem_troca else "troca-nao-aplicada", "classe": "one-pager-grande",
            "severidade": "atencao" if sem_troca else "decisao_humana", "dono": "esteira" if sem_troca else "PO",
            "resumo": (f"{item.get('papel')}: {item.get('falha')}" if sem_troca else
                       f"{item.get('papel')} quis trocar «{str(item.get('de'))[:160]}» por «{str(item.get('para'))[:160]}»"
                       f" e a troca não se aplicou ({str(item.get('falha'))[:200]})."),
        })

    # Colisão de slug: o registro no catálogo roda DEPOIS deste dossiê, então a checagem é feita aqui.
    try:
        from tools.catalogo import colisao_de_slug, ficha_da_execucao

        for a in colisao_de_slug(ficha_da_execucao(state)):
            achados.append({"gate": "Registro no catálogo de missões", "etapa": "produto", "id": a["codigo"],
                            "codigo": a["codigo"], "classe": "catalogo", "severidade": a["severidade"],
                            "dono": "produto", "resumo": a["resumo"]})
    except Exception:  # pragma: no cover - índice ilegível não derruba o dossiê
        pass

    # Desduplica achados idênticos propagados entre gates cumulativos (ex.: rastro de spec → design → dev → prd
    # ou rastreabilidade design → dev): preserva a primeira ocorrência no gate de origem e anota os demais em `tambem_em`.
    achados_unicos: List[Dict[str, Any]] = []
    indice_por_chave: Dict[tuple, Dict[str, Any]] = {}
    for a in achados:
        resumo_norm = re.sub(r"\s+", " ", (a.get("resumo") or "")).strip().lower()
        if a["severidade"] not in _BLOQUEIA and resumo_norm:
            chave_dedup = (a["severidade"], str(a.get("codigo") or ""), resumo_norm)
            if chave_dedup in indice_por_chave:
                prim = indice_por_chave[chave_dedup]
                outros = prim.setdefault("tambem_em", [])
                if a["gate"] != prim["gate"] and a["gate"] not in outros:
                    outros.append(a["gate"])
                continue
            indice_por_chave[chave_dedup] = a
        achados_unicos.append(a)
    achados = achados_unicos

    # a reprovação registrada que uma pessoa liberou sai das que impedem e vai para a seção própria, com quem e quando
    degradacoes, liberadas = liberacao.separar_degradacoes(state, pareceres)
    liberadas = [l for l in state.get(liberacao.KEY_LIBERADAS) or [] if isinstance(l, dict)] + liberadas
    agentes_degradados = list(state.get("agentes_degradados") or [])

    bloqueios = [a for a in achados if a["severidade"] in _BLOQUEIA]
    humanos = [a for a in achados if a["severidade"] in _HUMANO]
    ressalvas = [a for a in achados if a["severidade"] not in _BLOQUEIA and a["severidade"] not in _HUMANO]

    if degradacoes or bloqueios:
        veredito = "bloqueado"
    elif ressalvas or humanos or agentes_degradados or liberadas:
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
        "liberadas": liberadas,
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
    from pipeline.artifacts import documentos_dispensados

    pares = mapa.items() if hasattr(mapa, "items") else mapa
    dispensados = documentos_dispensados(state)
    # Por arquivo: a matriz de rastreabilidade nasce de duas chaves (a do design e a final do dev), e o arquivo
    # está entregue se qualquer uma delas tem conteúdo.
    por_arquivo: Dict[str, bool] = {}
    for chave, arquivo in pares:
        # Os dois transversais são escritos depois desta contagem — listá-los como ausentes
        # faria o dossiê acusar a própria falta.
        if chave in _ESCRITOS_DEPOIS:
            continue
        valor = state.get(chave)
        # o que a execução não precisava produzir só conta quando existe (G26: «Ausentes (6)» nas três missões do e2e)
        if chave in dispensados and not (isinstance(valor, str) and valor.strip()):
            continue
        por_arquivo[arquivo] = por_arquivo.get(arquivo, False) or bool(isinstance(valor, str) and valor.strip())
    return {"entregues": sorted(a for a, ok in por_arquivo.items() if ok),
            "ausentes": sorted(a for a, ok in por_arquivo.items() if not ok)}


def _linha_da_base(state: Dict[str, Any]) -> str:
    """Qual retrato da plataforma e do DS a execução leu. A missão do 9º ano (06/10/2026) foi escrita
    contra uma cópia de 16/09 e nada no dossiê dizia isso."""
    commit = state.get("base_plataforma_commit")
    if not commit:
        return "**Base da plataforma:** não registrada nesta execução."
    return (f"**Base da plataforma:** `plataforma-unooria@{commit}` ({state.get('base_plataforma_branch', '?')}, "
            f"{state.get('base_plataforma_data', '?')}) · design system {state.get('ds_versao', '?')}")


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
        _linha_da_base(state or {}),
        "",
        "## Como cada portão se saiu",
        "",
        "| Etapa | Portão | Resultado | Rodadas | Achados |",
        "|---|---|---|:-:|:-:|",
    ]
    for g in d["gates"]:
        rodadas = str(g["rodadas"]) if g["rodadas"] else "—"
        liberado = f" · liberado: {g['liberado']}" if g.get("liberado") else ""
        linhas.append(f"| {g['etapa']} | {g['rotulo']} | {g['icone']} {g['status'] or '—'}{liberado} | {rodadas} | "
                      f"{g['achados']} |")

    if d["degradacoes"]:
        linhas += ["", "## O que reprovou, na ordem em que aconteceu", ""]
        for i, deg in enumerate(d["degradacoes"], 1):
            linhas.append(f"{i}. **{deg.get('gate', '?')}** — {deg.get('motivo', '')}")

    if d.get("liberadas"):
        linhas += ["", "## Reprovações que uma pessoa liberou no parecer", "",
                   "O gate reprovou, quem responde pela etapa viu o 🔴 e liberou. Não impedem; ficam registradas:", ""]
        for lib in d["liberadas"]:
            acao = {"de_acordo": "de acordo", "excecao": "exceção"}.get(str(lib.get("acao") or ""), lib.get("acao") or "")
            linhas.append(f"- **{lib.get('gate', '?')}** — {lib.get('motivo', '')} · {acao} de {lib.get('como') or '?'} "
                          f"em {lib.get('quando') or '?'}")

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
    elif d["humanos"] or d.get("precisa_humano"):
        linhas.append("1. Não há impedimento técnico: o que falta são decisões listadas acima.")
    else:
        linhas.append("1. Nada travando. As ressalvas acima são opcionais e estão registradas para a próxima versão.")

    passagens = bloco_de_passagens(state or {})
    if passagens:
        linhas += ["", passagens]

    bloco = bloco_de_execucao(state or {})
    if bloco:
        linhas += ["", bloco]

    return "\n".join(linhas) + "\n"


def bloco_de_passagens(state: Dict[str, Any]) -> str:
    """Quem deu parecer em cada etapa, com que texto, e quantas voltas cada uma levou.

    Vem de `pareceres_humanos`, que a rodada final da esteira com parecer humano copia do `fluxo`
    do `conversa.json` (`pipeline/reexecucao.py`, `iniciar_etapa_stream`). Sem parecer humano, vazio.
    """
    from tools import governanca

    pareceres = [p for p in (state.get("pareceres_humanos") or []) if isinstance(p, dict)]
    if not pareceres:
        return ""
    nomes = {"de_acordo": "de acordo", "refazer": "pediu para refazer", "devolver": "devolveu",
             "excecao": "**liberou com exceção** (havia gate 🔴)"}
    linhas = ["## Passagens", "",
              "Cada etapa só seguiu depois do parecer de quem responde por ela. Pareceres de uma versão que",
              "depois foi refeita aparecem riscados.", ""]
    # A governança da liberação de produto em vigor, antes da trilha (PR 9 do plano «Produto dono do contrato», D9): em
    # 23/10/2026, 1 de 5 liberações de produto do acervo veio da conta produto
    gov = governanca.de_produto(pareceres)
    for pendencia in gov["pendencias"]:
        linhas.append(f"- 🟡 **{pendencia['resumo'][0].upper()}{pendencia['resumo'][1:]}**.")
    if gov["pendencias"]:
        linhas.append("")
    for etapa in ("produto", "design", "dev"):
        da_etapa = [p for p in pareceres if p.get("etapa") == etapa]
        if not da_etapa:
            continue
        voltas = sum(1 for p in da_etapa if p.get("acao") in ("refazer", "devolver"))
        linhas.append(f"### {etapa.capitalize()} — {voltas} volta(s)")
        linhas.append("")
        for p in da_etapa:
            texto = " ".join(str(p.get("comentario") or "").split())
            marca = f" 🟡 *{governanca.SEM_CONTA_PRODUTO}*" if governanca.liberou_sem_conta_produto(p) else ""
            acao = nomes.get(p.get("acao"), p.get("acao"))
            linha = f"- {p.get('quando', '?')} · {p.get('como', '?')}{marca} {acao}: {texto}"
            linhas.append(linha if p.get("valido", True) else f"- ~~{linha[2:]}~~")
            j = p.get("justificativa_excecao")
            if isinstance(j, dict) and governanca.justificativa_valida(j.get("texto")):
                linhas.append(f"  - Justificativa da exceção, escrita por {j.get('como') or j.get('autor') or '?'} em "
                              f"{j.get('quando') or p.get('quando', '?')}: «{' '.join(str(j['texto']).split())}»")
            elif etapa == "produto" and p.get("acao") == "excecao" and governanca.gates_vermelhos(p):
                linhas.append("  - 🟡 Sem justificativa registrada: a exceção é anterior à justificativa obrigatória "
                              "(24/10/2026).")
            conferencia = [c for c in p.get("conferencia_de_leitura") or [] if isinstance(c, dict)]
            if conferencia:
                decididos = sum(1 for c in conferencia if c.get("como") == "decidido")
                linhas.append(f"  - Conferência de leitura: {len(conferencia)} marcador(es) aberto(s) — {decididos} "
                              f"decidido(s) na lista do contrato, {len(conferencia) - decididos} lido(s).")
        linhas.append("")
    return "\n".join(linhas).rstrip()


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
        "liberadas_por_pessoa": len(d.get("liberadas") or []),
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
