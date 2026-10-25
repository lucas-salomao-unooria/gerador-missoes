"""Rodada única E2E (4/4): design — o teste de ponta a ponta de 25/10/2026 (exp01em1b, exp02ef1b, exp02em1b, exp03ef2b).

- G07: quando o fechamento de lacunas (D0) tira uma decisão do bloco 13, os documentos de design que a citam entram na
  mesma rodada do retrabalho; e o órfão que já existe vira ticket do A089 com o dono do documento. Na exp02em1b
  (session_f6ef44de) jornada, copy e ambiente seguiram citando «([D0-9])», e o rastro de design deu 🔴 depois do loop.
- G09: o fluxo carrega o nome do estado do contrato (prompt 072, de-para), o handoff recebe o nome a usar na mensagem, o
  curinga `EST_04_*` e o `[*]` do `stateDiagram` não são acusados.
- G13: `rotulo-divergente` tira o emoji e os colchetes da notação de botão antes de comparar.
- 2EM-06: o marcador do professor num texto-chave sobrevive na string da copy revisada.

Os trechos abaixo são copiados, literais, das sessões em `analises-esteira/2026-10-25/e2e/saidas/` (fora do repositório).
"""
from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator, List

import pytest
from google.adk.agents import BaseAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.runners import InMemoryRunner
from google.genai import types
from typing_extensions import override

# --------------------------------------------------------------------------- trechos reais da exp02em1b (G07)
#: `design/00-anexo-design-spec.md` depois do retrabalho do D0: o bloco 13 vai de [D0-1] a [D0-8]
ANEXO_SEM_D0_9 = "# Anexo de design\n\n## 13. Decisões D0\n\n" + "\n".join(
    f"### [D0-{n}] decisão {n}\nTexto da decisão {n}.\n" for n in range(1, 9)) + "\n## 14. Ambiente simulado (D9)\n\nFicha.\n"
ANEXO_COM_D0_9 = ANEXO_SEM_D0_9.replace("## 14.", "### [D0-9] Adaptação para uso em lousa digital\nTexto.\n\n## 14.")
#: `design/02-jornada-telas.md:119`
JORNADA_119 = ("| **O que muda na tela** | Smartphone simulado centralizado em viewport 375×812 (ou tela cheia móvel). | "
               "Smartphone simulado exibindo no topo a barra de contexto `\"Comitê Editorial (Sessão Compartilhada)\"` "
               "([D0-9]). | Renderização desktop (1366×768) com botões e alvos aumentados para no mínimo 88×88px e "
               "tipografia aumentada em 125% ([D0-9]). |")
#: `design/06-copy-strings-revisada.md:164-166`
COPY_166 = ("2. `e1.rotulo.barra_comite_compartilhado` (Tela `E1-ALU-01`, estado `degradado`):\n"
            "   - *Texto:* `\"Comitê Editorial (Sessão Compartilhada)\"`\n"
            "   - *Contexto:* Tarja fixa superior de cabeçalho nos cenários de 2–4 estudantes por aparelho ([D0-9]).")
#: `design/00b-ambiente-simulado.md:84-86`, no bloco 14
AMBIENTE_86 = ("## 14. Ambiente simulado (D9)\n\n- **Estados que a seção já traz:**\n"
               "  - *Carregando / Digitando:* Balão cinza com 3 pontos animados ([D0-3]).\n"
               "  - *Degradado (compartilhado 2–4 por aparelho):* Barra de contexto informando *\"Comitê Editorial "
               "(Sessão Compartilhada)\"* com alternância voluntária entre chat e edição ([D0-9]).\n")


def _estado_g07(anexo: str = ANEXO_SEM_D0_9) -> dict:
    return {"spec_missao": "# Spec\n\n## 2. Mecânica\n\nTexto.\n", "anexo_design_spec": anexo,
            "jornada_telas": JORNADA_119, "copy_strings_revisada": COPY_166, "ambiente_simulado": AMBIENTE_86,
            "fluxo_arestas": "Fluxo sem citação de decisão."}


def test_tickets_d0_orfaos_exp02em1b():
    from tools.rastro import tickets_d0_orfaos

    tickets = tickets_d0_orfaos(_estado_g07())
    assert {t["agente_responsavel"]: t["trecho"] for t in tickets} == {
        "jornada": "D0-9", "copy-ptbr-revisao": "D0-9", "ambiente-simulado": "D0-9"}
    assert all(t["severidade"] == "bloqueio" and t["codigo"] == "d0-orfao" and t["etapa"] == "design" for t in tickets)
    assert all("[ABERTO — dono: PO" in t["como"] for t in tickets)
    # mutante: com o D0-9 no bloco 13, nada é órfão; o D0-3 do ambiente está no bloco e nunca foi órfão
    assert tickets_d0_orfaos(_estado_g07(ANEXO_COM_D0_9)) == []


def test_tickets_d0_orfaos_sem_bloco_13_fica_com_o_rastro():
    """Sem o bloco 13 o conserto é do D0 (o rastro o cobra com dono `fecha-lacunas`): o ticket ao documento que cita
    mandaria tirar uma citação de decisão que pode existir."""
    from tools.rastro import tickets_d0_orfaos

    assert tickets_d0_orfaos(_estado_g07("# Anexo sem o bloco\n\n## 14. Ambiente\n\nFicha.\n")) == []


def test_donos_dos_documentos_tem_rota_no_retrabalho_de_design():
    from agents.design import MAPA_RETRABALHO, ORDEM_RETRABALHO, build_qa_design_loop
    from agents.checkers import DespachoTicketsAgent
    from tools.rastro import DONO_DO_DOCUMENTO_DESIGN, FONTES_DESIGN

    assert set(DONO_DO_DOCUMENTO_DESIGN.values()) <= set(MAPA_RETRABALHO)
    rotulos = {f["rotulo"] for f in FONTES_DESIGN} - {"spec da missão", "anexo de design da spec"}
    assert rotulos == set(DONO_DO_DOCUMENTO_DESIGN)
    assert ORDEM_RETRABALHO[0] == "fecha-lacunas"
    despacho = next(s for s in build_qa_design_loop().sub_agents if isinstance(s, DespachoTicketsAgent))
    assert despacho.cascata_d0_apos == "fecha-lacunas"
    assert "fecha-lacunas" not in DONO_DO_DOCUMENTO_DESIGN.values(), "a cascata não pode reabrir o D0"


# --------------------------------------------------------------------------- o despacho com a cascata (G07)
class Autor(BaseAgent):
    """Agente falso que grava o texto, conta a execução, anota a ordem e guarda os tickets que recebeu."""

    key: str
    text: str = ""
    tickets_de: str = ""

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        st = ctx.session.state
        delta = {"ordem": list(st.get("ordem") or []) + [self.name]}
        if self.key:
            delta[self.key] = self.text
        if self.tickets_de:
            delta[self.tickets_de] = str(st.get("tickets_retrabalho") or "")
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    actions=EventActions(state_delta=delta))


class Semente(BaseAgent):
    estado: dict

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    actions=EventActions(state_delta=dict(self.estado)))


def _qa(*achados) -> str:
    env = {"agente": "qa-entregaveis", "status": "bloqueado", "achados": list(achados)}
    return "QA\n```json\n" + json.dumps(env, ensure_ascii=False) + "\n```"


TICKET_D0 = {"id": "QA-A4", "severidade": "bloqueio", "codigo": "decisao-de-produto-pelo-agente",
             "agente_responsavel": "fecha-lacunas", "resumo": "[D0-9] toca revezamento"}


def _despacho(anexo_do_d0: str, cascata: str = "fecha-lacunas", **kw):
    from agents.checkers import DespachoTicketsAgent

    return DespachoTicketsAgent(
        name="Despacho", rotulo="Retrabalho de design", report_key="qa_entregaveis_report",
        mapa={"fecha-lacunas": ["D0", "D0Split", "SpecCons"], "ambiente-simulado": ["D9", "D9Split", "SpecCons"],
              "jornada": ["Jornada"], "fluxo": ["Fluxo"], "copy-ptbr-revisao": ["Copy", "CopyPreservada"]},
        ordem=["fecha-lacunas", "ambiente-simulado", "jornada", "fluxo", "copy-ptbr-revisao"],
        posfixo=["Prototipo"], cascata_d0_apos=cascata,
        sub_agents=[
            Autor(name="D0", key="fechamento_lacunas", text="D0 refeito"),
            Autor(name="D0Split", key="anexo_design_spec", text=anexo_do_d0),
            Autor(name="SpecCons", key="spec_cons", text="ok"),
            Autor(name="D9", key="ambiente_simulado", text=AMBIENTE_86.replace(" ([D0-9])", ""), tickets_de="t_d9"),
            Autor(name="D9Split", key="ambiente_status", text="ok"),
            Autor(name="Jornada", key="jornada_telas", text=JORNADA_119.replace(" ([D0-9])", ""), tickets_de="t_jornada"),
            Autor(name="Fluxo", key="fluxo_arestas", text="fluxo", tickets_de="t_fluxo"),
            Autor(name="Copy", key="copy_strings_revisada", text=COPY_166.replace(" ([D0-9])", ""), tickets_de="t_copy"),
            Autor(name="CopyPreservada", key="", text=""),
            Autor(name="Prototipo", key="prototipo_html", text="<html>"),
        ], **kw)


async def _rodar(agentes: List[BaseAgent]):
    runner = InMemoryRunner(agent=SequentialAgent(name="R", sub_agents=agentes), app_name="t")
    sessao = await runner.session_service.create_session(app_name="t", user_id="u", session_id="s")
    eventos = []
    async for ev in runner.run_async(user_id="u", session_id=sessao.id,
                                     new_message=types.Content(role="user", parts=[types.Part(text="go")])):
        eventos.append(ev)
    final = await runner.session_service.get_session(app_name="t", user_id="u", session_id="s")
    return eventos, dict(final.state)


def _texto(eventos) -> str:
    return "\n".join(p.text for e in eventos if e.content for p in (e.content.parts or []) if getattr(p, "text", None))


def test_despacho_refaz_na_mesma_rodada_quem_cita_a_decisao_que_o_d0_apagou():
    """O retrabalho da exp02em1b: o QA manda o D0 tirar o D0-9; o D0 o tira; jornada, copy e ambiente o citam."""
    semente = Semente(name="Semente", estado={**_estado_g07(ANEXO_COM_D0_9), "qa_entregaveis_report": _qa(TICKET_D0)})
    eventos, st = asyncio.run(_rodar([semente, _despacho(ANEXO_SEM_D0_9)]))
    # D0 e o split antes; depois os que citam, na ordem de precedência (ambiente antes de jornada antes da copy); o
    # posfixo por último. O fluxo não cita o D0-9 e não roda; a spec consolidada roda de novo depois do D9 novo
    assert st["ordem"] == ["D0", "D0Split", "SpecCons", "D9", "D9Split", "SpecCons", "Jornada", "Copy",
                           "CopyPreservada", "Prototipo"]
    for chave in ("t_d9", "t_jornada", "t_copy"):
        assert "D0-9" in st[chave] and "saiu do bloco 13" in st[chave] and "[ABERTO — dono: PO" in st[chave]
    assert "t_fluxo" not in st
    assert "ambiente-simulado, copy-ptbr-revisao, jornada" in _texto(eventos)
    # a conta do orçamento leva os três autores novos: D0 + D9, jornada e copy
    from agents.checkers import KEY_REEXECUCOES

    assert st[KEY_REEXECUCOES] == 4


def test_mutante_sem_cascata_quem_cita_nao_roda():
    semente = Semente(name="Semente", estado={**_estado_g07(ANEXO_COM_D0_9), "qa_entregaveis_report": _qa(TICKET_D0)})
    _, st = asyncio.run(_rodar([semente, _despacho(ANEXO_SEM_D0_9, cascata="")]))
    assert st["ordem"] == ["D0", "D0Split", "SpecCons", "Prototipo"]


def test_mutante_d0_que_mantem_a_decisao_nao_dispara_cascata():
    semente = Semente(name="Semente", estado={**_estado_g07(ANEXO_COM_D0_9), "qa_entregaveis_report": _qa(TICKET_D0)})
    _, st = asyncio.run(_rodar([semente, _despacho(ANEXO_COM_D0_9)]))
    assert st["ordem"] == ["D0", "D0Split", "SpecCons", "Prototipo"]


def test_cascata_junta_o_ticket_ao_dono_que_ja_tinha_ticket():
    """A jornada já tinha ticket do QA nesta rodada: ela roda uma vez, com os dois tickets."""
    jornada = {"id": "QA-1", "severidade": "bloqueio", "codigo": "D1", "agente_responsavel": "jornada",
               "resumo": "rótulo abreviado"}
    semente = Semente(name="Semente", estado={**_estado_g07(ANEXO_COM_D0_9),
                                              "qa_entregaveis_report": _qa(TICKET_D0, jornada)})
    _, st = asyncio.run(_rodar([semente, _despacho(ANEXO_SEM_D0_9)]))
    assert st["ordem"].count("Jornada") == 1
    assert "rótulo abreviado" in st["t_jornada"] and "D0-9" in st["t_jornada"]


def test_cascata_sem_orcamento_vai_ao_dossie(monkeypatch):
    from agents import checkers

    semente = Semente(name="Semente", estado={**_estado_g07(ANEXO_COM_D0_9), "qa_entregaveis_report": _qa(TICKET_D0)})
    chamadas = []

    def orcamento(state, quantos):
        chamadas.append(quantos)
        return len(chamadas) == 1  # cabe o conserto do D0, não a cascata

    monkeypatch.setattr(checkers, "orcamento_disponivel", orcamento)
    eventos, st = asyncio.run(_rodar([semente, _despacho(ANEXO_SEM_D0_9)]))
    assert st["ordem"] == ["D0", "D0Split", "SpecCons", "Prototipo"]
    sem_rota = st[checkers.KEY_TICKETS_SEM_ROTA]
    assert {r["dono"] for r in sem_rota} == {"jornada", "copy-ptbr-revisao", "ambiente-simulado"}
    assert all("orçamento" in r["motivo"] for r in sem_rota)
    assert "Vai ao dossiê como pendência" in _texto(eventos)


def test_qa_afirmacoes_transforma_o_orfao_em_ticket_do_dono_do_documento():
    """O órfão que já existe na rodada (o D0 o tirou numa rodada anterior) tem dono: o A089 o põe no envelope do QA."""
    from agents.checkers import QaAfirmacoesAgent
    from agents.callbacks import extrair_envelope

    qa = "QA\n```json\n" + json.dumps({"agente": "qa-entregaveis", "status": "aprovado", "achados": []}) + "\n```"
    semente = Semente(name="Semente", estado={**_estado_g07(), "qa_entregaveis_report": qa})
    _, st = asyncio.run(_rodar([semente, QaAfirmacoesAgent(name="A089")]))
    env = extrair_envelope(st["qa_entregaveis_report"])
    assert env["status"] == "bloqueado"
    donos = {a["agente_responsavel"] for a in env["achados"] if a.get("codigo") == "d0-orfao"}
    assert donos == {"jornada", "copy-ptbr-revisao", "ambiente-simulado"}
    # mutante: com o D0-9 no bloco, o QA aprovado fica aprovado
    semente = Semente(name="Semente", estado={**_estado_g07(ANEXO_COM_D0_9), "qa_entregaveis_report": qa})
    _, st = asyncio.run(_rodar([semente, QaAfirmacoesAgent(name="A089")]))
    assert extrair_envelope(st["qa_entregaveis_report"])["status"] == "aprovado"


# --------------------------------------------------------------------------- G09: estados
#: `produto/05-spec-missao.md:104-110` da exp02em1b (o contrato de estados, primeiras linhas)
CONTRATO_2EM = (
    "## 2. Mecânica\n\n### Contrato de estados\n\n"
    "| Estado inicial | Gatilho | Regra do sistema | Estado seguinte | Responsável | Reversível |\n"
    "|---|---|---|---|---|:---:|\n"
    "| `EST_01_DESAFIAR` | Estudante clica em \"Abrir UnooriaAI\" | Valida token | `EST_02_NAVEGAR_CHAT` | Estudante | Não |\n"
    "| `EST_02_NAVEGAR_CHAT` | Estudante envia prompt ou edita prévia | Atualiza chat | `EST_02_NAVEGAR_CHAT` | Estudante | Sim |\n"
    "| `EST_02_NAVEGAR_CHAT` | Estudante clica em \"Exportar para o Unoovista\" | Prévia ok | `EST_03_DECIDIR_MODAL` | Estudante | Sim |\n"
    "| `EST_03_DECIDIR_MODAL` | Estudante seleciona manchete | Grava latch | `EST_04_FEED_NOTURNO` | Estudante | Não |\n"
    "| `EST_04_FEED_NOTURNO` | Estudante interage com moderação/proteção | Persiste | `EST_04_FEED_NOTURNO` | Estudante | Sim |\n"
    "| `QUALQUER_ESTADO` | Professor aciona trava \"Pausar Telas\" | Congela | `EST_PAUSA_DOCENTE` | Professor | Sim |\n"
)
#: `dev/01-handoff-dev.md:451-470` da exp02em1b
HANDOFF_2EM = (
    "| Estado | Tela | Gatilho | Destino | O que persiste no servidor |\n|---|---|---|---|---|\n"
    "| `EST_02_NAVEGAR_CHAT` | `E2-ALU-01` | Clicar na aba \"Prévia da Campanha\" | `EST_02_NAVEGAR_PREVIA` | — |\n"
    "| `EST_02_NAVEGAR_PREVIA` | `E2-ALU-02` | Editar campos de autoria/privacidade | `EST_02_NAVEGAR_PREVIA` | Rascunho |\n"
    "| `EST_04_FEED_NOTURNO` | `E4-ALU-01` | Clicar \"Configuração da Publicação\"| `EST_04_MODERACAO` | — |\n"
    "| `EST_04_*` | `E4-ALU-*` | Professor aciona \"Pausar Telas\" | `EST_PAUSA_DOCENTE` | Trava em `exp02em1b_gates_turma.pausado` |\n"
)
#: a seção que o prompt 072 passa a exigir, no molde da §6.1 do PRD da exp02em1b
DE_PARA = ("## De-para nó → estado do contrato (bloco 2)\n"
           "| Nó do fluxo | Tela (ID do inventário) | Estado do contrato (bloco 2, nome literal) |\n|---|---|---|\n"
           "| E2_ALU_01 | `E2-ALU-01` | `EST_02_NAVEGAR_CHAT` |\n| E2_ALU_02 | `E2-ALU-02` | `EST_02_NAVEGAR_CHAT` |\n"
           "| E4_ALU_01 | `E4-ALU-01` | `EST_04_FEED_NOTURNO` |\n\n## Lista de arestas\n")


def test_curinga_nao_e_estado():
    from tools import montagem as mt

    assert mt._estado_da_celula("`EST_04_*`") is None
    assert mt._estado_da_celula("EST_04_*") is None
    usados = mt.estados_usados(HANDOFF_2EM)
    assert "EST_04" not in usados and "EST_PAUSA_DOCENTE" in usados
    # mutante: a ênfase em volta do nome não é curinga
    assert mt._estado_da_celula("**EST_04_FEED_NOTURNO**") == "EST_04_FEED_NOTURNO"
    assert mt._estado_da_celula("`EST_04_FEED_NOTURNO`") == "EST_04_FEED_NOTURNO"


def test_mensagem_do_estado_inventado_diz_o_nome_do_contrato():
    from tools import montagem as mt

    estado = {"spec_missao": CONTRATO_2EM, "fluxo_arestas": DE_PARA, "handoff_dev": HANDOFF_2EM}
    achado = next(a for a in mt.validar_handoff(estado)["achados"] if a["codigo"] == "estado-fora-do-contrato")
    assert "`EST_02_NAVEGAR_PREVIA` → na linha da tela `E2-ALU-01`, que o de-para do fluxo põe em `EST_02_NAVEGAR_CHAT`" \
        in achado["resumo"]
    assert "`EST_04_MODERACAO` → na linha da tela `E4-ALU-01`, que o de-para do fluxo põe em `EST_04_FEED_NOTURNO`" \
        in achado["resumo"]
    assert "`EST_04`;" not in achado["resumo"] and "`EST_04`." not in achado["resumo"]
    # sem de-para (o fluxo das sessões de 25/10/2026), o contrato com o mesmo prefixo
    sem = next(a for a in mt.validar_handoff({**estado, "fluxo_arestas": "só IDs de tela"})["achados"]
               if a["codigo"] == "estado-fora-do-contrato")
    assert "`EST_02_NAVEGAR_PREVIA` → do contrato, com o mesmo prefixo: `EST_02_NAVEGAR_CHAT`" in sem["resumo"]
    assert "Os estados do contrato: `EST_01_DESAFIAR`" in sem["resumo"]


def test_de_para_do_fluxo_le_so_a_secao_e_o_nome_literal():
    from tools import montagem as mt

    contrato = ["EST_01_DESAFIAR", "EST_02_NAVEGAR_CHAT", "EST_04_FEED_NOTURNO"]
    assert mt.de_para_do_fluxo(DE_PARA, contrato) == {
        "E2-ALU-01": ["EST_02_NAVEGAR_CHAT"], "E2-ALU-02": ["EST_02_NAVEGAR_CHAT"], "E4-ALU-01": ["EST_04_FEED_NOTURNO"]}
    # a tabela de arestas não é de-para, e o nome fora do contrato não entra
    arestas = "## Lista de arestas\n| # | De | Para |\n|---|---|---|\n| A1 | `E2-ALU-01` | `EST_02_NAVEGAR_CHAT` |\n"
    assert mt.de_para_do_fluxo(arestas, contrato) == {}
    assert mt.de_para_do_fluxo(DE_PARA.replace("EST_04_FEED_NOTURNO", "EST_04_MODERACAO"), contrato).get("E4-ALU-01") \
        is None


#: `produto/05-spec-missao.md:105` e `design/03-fluxo-arestas.md:5-9` da exp01em1b
SPEC_1EM = ("## 2. Mecânica\n\n### Contrato de estados\n\n"
            "| Estado inicial | Gatilho | Regra do sistema | Estado seguinte | Responsável | Reversível |\n"
            "|---|---|---|---|---|---|\n"
            "| `NAO_INICIADO` | Aluno clica em \"Abrir Módulo de Teste\" | Inicializa sessão | `AUDITORIA_DESAFIAR` | Cliente/API | Não |\n"
            "| `AUDITORIA_DESAFIAR` | Aluno avança | Abre bancada | `EXPLORACAO_FUNCOES` | Cliente | Não |\n")
FLUXO_1EM = ("```mermaid\nstateDiagram-v2\n  [*] --> E1_ALU_01: Iniciar sessao\n\n"
             "  state \"E1-ALU-01 · Boas-vindas Zara\\n[AUDITORIA_DESAFIAR]\" as E1_ALU_01\n"
             "  state \"E2-ALU-01 · Bancada Funcoes\\n[EXPLORACAO_FUNCOES]\" as E2_ALU_01\n```\n")


def _estados_perdidos(state, coluna):
    from tools import rastreabilidade as rb

    r = rb.matriz(state)
    return [f["texto"] for a in r["achados"] if a["codigo"] == f"perdido-estado-{coluna}" for f in a["faltando"]]


def test_estado_inicial_e_o_colchete_estrela_do_fluxo():
    assert _estados_perdidos({"spec_missao": SPEC_1EM, "fluxo_arestas": FLUXO_1EM}, "fluxo") == []
    # mutante: sem o `[*] -->`, o NAO_INICIADO continua perdido
    sem = FLUXO_1EM.replace("[*] --> E1_ALU_01: Iniciar sessao", "E1_ALU_01 --> E2_ALU_01: ok")
    assert _estados_perdidos({"spec_missao": SPEC_1EM, "fluxo_arestas": sem}, "fluxo") == ["NAO_INICIADO"]
    # mutante: só o primeiro estado do contrato; o segundo ausente continua perdido
    sem2 = FLUXO_1EM.replace("[AUDITORIA_DESAFIAR]", "[BOAS_VINDAS]")
    assert _estados_perdidos({"spec_missao": SPEC_1EM, "fluxo_arestas": sem2}, "fluxo") == ["AUDITORIA_DESAFIAR"]
    # mutante: no PRD o nome continua exigido
    prd = "## 6. Estados\n\nAUDITORIA_DESAFIAR, EXPLORACAO_FUNCOES\n" + FLUXO_1EM
    assert _estados_perdidos({"spec_missao": SPEC_1EM, "prd_final": prd}, "prd") == ["NAO_INICIADO"]


def test_prompt_do_fluxo_exige_o_de_para_e_nao_se_contradiz():
    from prompts.loader import get_prompt_raw

    p = get_prompt_raw("design/072_fluxo.md")
    assert "identificado pelo código da tela" not in p
    assert "## De-para nó → estado do contrato (bloco 2)" in p
    assert p.rindex("## De-para nó → estado do contrato (bloco 2)") > p.index("## Saída obrigatória")
    assert "Decompor é livre" in p and "nome **literal**" in p
    handoff = get_prompt_raw("dev/100a_handoff_dev.md")
    assert "De-para nó → estado do contrato" in handoff


# --------------------------------------------------------------------------- G13: rótulo com emoji e colchetes
#: o glossário e o fluxo da exp02ef1b (session_935e39e4): «🌿 SÓ UM PEDAÇO» × «SÓ UM PEDAÇO» × «[🌿 SÓ UM PEDAÇO]»
GLOSSARIO_2EF = ("# Spec\n\n## Glossário canônico\n\n| Ação | Rótulo canônico |\n|---|---|\n"
                 "| Escolher transferência de enquadramento parcial na E6 | 🌿 SÓ UM PEDAÇO |\n"
                 "| Escolher transferência de enquadramento total na E6 | 💥 MOSTRA TUDO |\n")
FLUXO_2EF = ("| A47 | 'E6_ALU_01' | 'DEC_E6_T' | Estudante visualiza close da lagarta e toca em \"SÓ UM PEDAÇO\" ou "
             "\"MOSTRA TUDO\" | principal |\n")
PRD_2EF = ("| 'E6-ALU-01' | 'e6.pergunta.horta_acabou' | Botão '[🌿 SÓ UM PEDAÇO]' | 'assertive' (ao confirmar) |\n")


def _rotulos(documento: str, texto: str):
    from tools import consistencia

    return [a["resumo"] for a in consistencia.validar(GLOSSARIO_2EF, {documento: texto})["achados"]
            if a["codigo"] == "rotulo-divergente"]


def test_rotulo_com_emoji_ou_colchetes_e_o_mesmo_rotulo():
    assert _rotulos("fluxo", FLUXO_2EF) == []
    assert _rotulos("PRD", PRD_2EF) == []


def test_mutante_rotulo_com_outra_palavra_continua_acusado():
    outro = "SÓ UM PEDAÇO DA HORTA"
    assert any(f"«{outro}»" in r for r in _rotulos("fluxo", FLUXO_2EF.replace("SÓ UM PEDAÇO", outro)))
    assert any(f"«[🌿 {outro}]»" in r for r in _rotulos("PRD", PRD_2EF.replace("SÓ UM PEDAÇO", outro)))


def test_norm_tira_emoji_e_colchetes_das_bordas():
    from tools.consistencia import _norm

    assert _norm("[🌿 SÓ UM PEDAÇO]") == _norm("🌿 SÓ UM PEDAÇO") == _norm("SÓ UM PEDAÇO") == "so um pedaco"
    assert _norm("👍🏽 Curtir") == "curtir"  # o modificador de tom de pele (Sk) e o seletor de variação saem
    assert _norm("❤️ Curtir") == "curtir"
    # os colchetes de dentro ficam: «[A] e [B]» não é um rótulo entre colchetes
    assert _norm("[A] e [B]") == "[a] e [b]"


# --------------------------------------------------------------------------- 2EM-06: o marcador do professor
#: `produto/00n-textos-chave.md` (TC-11) e `design/06-copy-strings-revisada.md:13,98` da exp02em1b
TC_11 = ("Você é moderador do perfil do grêmio estudantil no Unoovista. O post sobre [recorte da aula: parâmetro do "
         "professor] viralizou e saiu da bolha da escola. Pessoas de fora estão chegando, perfis desconhecidos estão "
         "aparecendo nos comentários e alguns colegas estão compartilhando relatos sobre como foram afetados. O perfil é "
         "responsabilidade de vocês: decida o que precisa ser feito com a publicação, com quem está interagindo e com a "
         "situação como um todo. O grêmio não tem preparo pra resolver isso sozinho, busque soluções de apoio dentro do "
         "Unoovista")
CABECALHO_COPY = ("| ID tela | Chave | Tipo | Seção | PT-BR (final) | Palavras | Redundância | Voz | "
                  "Revisão (o que mudou e por quê) |\n|---|---|---|---|---|---|---|---|---|\n")


def _linha_98(texto: str) -> str:
    return (f"| `E4-ALU-01` | `e4.narrativa.overlay_cta_gremio` | narrativa | `unoovista` | {texto} | 88 | `texto` | "
            "`unooria` | `TC-11` — Faixa de contexto do grêmio. Texto literal do one-pager (§4). |\n")


def _tc(ident: str, texto: str):
    from tools.textos_chave import TELA, TextoChave

    return TextoChave(id=ident, tipo=TELA, origem="§4 · Etapa 4", texto=texto)


def test_slot_do_professor_fixado_na_copy_exp02em1b():
    from tools import textos_chave as tk

    fixo = TC_11.replace("[recorte da aula: parâmetro do professor]", "convivência escolar")
    copy = "# Copy\n\n" + CABECALHO_COPY + _linha_98(fixo)
    # o literal com o marcador numa seção de propostas da copy (como na sessão) não salva a string
    copy += "\n## 3. Strings que não couberam\n\n1. *Texto aprovado:* «" + TC_11 + "»\n"
    assert tk.slots_do_professor_fixados(copy, [_tc("TC-11", TC_11)]) == [{
        "id": "TC-11", "chave": "e4.narrativa.overlay_cta_gremio", "valor": "convivência escolar",
        "marcador": "[recorte da aula: parâmetro do professor]"}]
    r = tk.conferir_copy(copy, [_tc("TC-11", TC_11)])
    achado = next(a for a in r["achados"] if a["codigo"] == "slot-do-professor-fixado")
    assert r["status"] == "bloqueado" and achado["severidade"] == "bloqueio"
    assert achado["agente_responsavel"] == "copy-ptbr-revisao"
    assert "«convivência escolar» no lugar de «[recorte da aula: parâmetro do professor]»" in achado["resumo"]


@pytest.mark.parametrize("na_copy", [
    TC_11,                                                                              # o marcador inteiro
    TC_11.replace("[recorte da aula: parâmetro do professor]", "[recorte da aula]"),    # a grafia curta
    TC_11.replace("[recorte da aula: parâmetro do professor]", "{recorte_da_aula}"),    # variável de template
])
def test_slot_preservado_nao_e_acusado(na_copy):
    from tools import textos_chave as tk

    assert tk.slots_do_professor_fixados(CABECALHO_COPY + _linha_98(na_copy), [_tc("TC-11", TC_11)]) == []


def test_slot_sem_colchetes_e_valor_fixo():
    """exp01em1b-e89e91b3 (acervo): «…da Escola para o recorte da aula. A coordenação…» — os colchetes saíram, e o
    professor não tem mais onde preencher."""
    from tools import textos_chave as tk

    tc = ("Você foi encarregado de colocar no ar o Assistente de Estudos da Escola para o [recorte da aula: parâmetro do "
          "professor]. A coordenação liberou 100 créditos computacionais.")
    copy = CABECALHO_COPY + _linha_98(tc.replace("[recorte da aula: parâmetro do professor]", "recorte da aula"))
    assert [f["valor"] for f in tk.slots_do_professor_fixados(copy, [_tc("TC-01", tc)])] == ["recorte da aula"]


def test_mutante_lacuna_que_nao_e_do_professor_pode_ser_preenchida():
    """`{motivo}`, `X%` e `[nome do colega]` são lacunas que a copy preenche (exp05ef1b, exp01em1b): não são do
    professor, e a regra não as toca."""
    from tools import textos_chave as tk

    tc = "O seu colega [nome do colega] enviou {motivo} com X% de certeza."
    copy = CABECALHO_COPY + _linha_98("O seu colega Rafa enviou o relato com 68% de certeza.")
    assert tk.slots_do_professor_fixados(copy, [_tc("TC-02", tc)]) == []


def test_mutante_marcador_na_ponta_nao_tem_onde_parar():
    """O marcador na ponta do texto-chave não vira grupo: sem texto fixo depois dele, a comparação não sabe onde o valor
    termina. A string que só traz a frase sem o fim não é acusada — fica com o gate do texto-chave."""
    from tools import textos_chave as tk

    tc = "Recebe a pauta da semana: produzir um post informativo sobre [recorte da aula: parâmetro do professor]"
    copy = CABECALHO_COPY + _linha_98("Recebe a pauta da semana: produzir um post informativo sobre alimentação")
    assert tk.slots_do_professor_fixados(copy, [_tc("TC-03", tc)]) == []
    # com o ponto final depois do marcador, há onde parar
    copy = CABECALHO_COPY + _linha_98("Recebe a pauta da semana: produzir um post informativo sobre alimentação.")
    assert [f["valor"] for f in tk.slots_do_professor_fixados(copy, [_tc("TC-03", tc + ".")])] == ["alimentação"]


def test_mutante_amostra_preenchida_nas_notas_nao_e_acusada():
    from tools import textos_chave as tk

    fixo = TC_11.replace("[recorte da aula: parâmetro do professor]", "convivência escolar")
    linha = _linha_98(TC_11).replace("Faixa de contexto do grêmio.", f"Amostra: {fixo}")
    assert tk.slots_do_professor_fixados(CABECALHO_COPY + linha, [_tc("TC-11", TC_11)]) == []


# --------------------------------------------------------------------------- explicações para o PO
def test_codigos_novos_tem_explicacao_para_o_po():
    from tools import explicacoes as ex

    for codigo in ("slot-do-professor-fixado", "d0-orfao"):
        assert codigo in ex.CATALOGO
    slot = ex.CATALOGO["slot-do-professor-fixado"]
    assert slot.quem == ex.DESIGN and "professor" in slot.o_que_aconteceu
    assert "tirada ou renumerada" in ex.CATALOGO["d0-orfao"].o_que_aconteceu
