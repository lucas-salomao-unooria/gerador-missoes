"""Rodada única de correção depois do teste de ponta a ponta de 25/10/2026 (1/4): contexto que estoura o modelo, one-pager
do PO grande cortado em silêncio, telemetria na queda e manifesto.

A 3ef2b (one-pager do PO com 360 mil caracteres, ≈107 mil tokens) caiu no A004 com `400 INVALID_ARGUMENT — input token
count exceeds 1048576`, depois de 90 min e US$ 8,50; a 2ª tentativa caiu no mesmo 400 (US$ 10,34). O A004 recebia o
histórico inteiro da sessão (G01); o A014 e o A037 reescreviam o one-pager do PO inteiro e eram cortados perto de 218 mil
caracteres, sem aviso (G02); na queda nada era salvo (G19); juízes recebiam o one-pager do PO duas vezes (G20); e o
diagnóstico das três missões normais listava «Ausentes (6)» que eram dispensados (G26).

O one-pager real da 3ef2b está em `fixtures/e2e-2026-10-25/one-pager-po-3ef2b.md`, extraído pelo conversor do app
(`tools.doc_parser.process_document`) do `3EF-B2-onepager-v7.docx`.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any, AsyncGenerator, Dict, List
from unittest import mock

import pytest
from google.adk.agents import SequentialAgent
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import InMemoryRunner
from google.genai import types
from typing_extensions import override

from tools import contexto
from tools import edicao_pontual as ed
from tools import one_pager_grande as og

RAIZ = Path(__file__).resolve().parent
ACERVO = RAIZ / "tests" / "acervo"
PO_3EF2B = (RAIZ / "fixtures" / "e2e-2026-10-25" / "one-pager-po-3ef2b.md").read_text(encoding="utf-8")
DOCX_3EF2B = Path("/Volumes/Documentos/Unooria/analises-esteira/2026-10-25/e2e/entrada/3EF-B2-onepager-v7.docx")
MATERIAL_3EF2B = "### 📄 Documento de apoio (DOCX): 3EF-B2-onepager-v7.docx\n\n" + PO_3EF2B


def _missoes() -> List[str]:
    return sorted(p.name for p in ACERVO.iterdir() if (p / "estado.json").exists())


def _estado(missao: str) -> Dict[str, Any]:
    return json.loads((ACERVO / missao / "estado.json").read_text(encoding="utf-8"))


class _Ctx:
    """O que os callbacks leem de um `CallbackContext`."""

    def __init__(self, state: Dict[str, Any], agente: str = "A014SecoesApoio", user_content: Any = None,
                 output_key: str = ""):
        self.state = state
        self.agent_name = agente
        self.user_content = user_content
        self._invocation_context = SimpleNamespace(agent=SimpleNamespace(output_key=output_key))


async def _rodar(root, estado, eventos: List[Event] = None):
    runner = InMemoryRunner(agent=root, app_name="teste")
    await runner.session_service.create_session(app_name="teste", user_id="u", session_id="s", state=estado)
    async for ev in runner.run_async(user_id="u", session_id="s",
                                     new_message=types.Content(role="user", parts=[types.Part(text="go")])):
        if eventos is not None:
            eventos.append(ev)
    final = await runner.session_service.get_session(app_name="teste", user_id="u", session_id="s")
    return dict(final.state)


def _linha_unica(texto: str, ini: int, fim: int, minimo: int = 60) -> str:
    """Uma linha de prosa do trecho que aparece uma vez só no documento."""
    for linha in texto[ini:fim].splitlines():
        if len(linha) >= minimo and not linha.startswith(("|", "#")) and texto.count(linha) == 1:
            return linha
    raise AssertionError("nenhuma linha única no trecho")


# --------------------------------------------------------------------------- o one-pager real da 3ef2b
def test_fixture_e_o_que_o_conversor_do_app_extrai_do_docx():
    """O one-pager da fixture é o que o app extrai do docx do PO (sem o docx, na CI, confere só o tamanho)."""
    assert len(PO_3EF2B) > 360_000 and contexto.estimar_tokens(PO_3EF2B) > 100_000
    if not DOCX_3EF2B.exists():
        pytest.skip("docx do e2e fora desta máquina")
    from tools.doc_parser import DocumentBatch, process_document
    from pipeline.runner import material_dos_anexos
    from tools.one_pager_po import extrair

    lote = DocumentBatch()
    lote.documents.append(process_document(DOCX_3EF2B.name, DOCX_3EF2B.read_bytes()))
    assert extrair(material_dos_anexos(lote)) + "\n" == PO_3EF2B or extrair(material_dos_anexos(lote)) == PO_3EF2B


def test_um_pager_da_3ef2b_e_montado_por_trocas_e_os_do_acervo_nao():
    assert og.por_trocas({"one_pager_po": PO_3EF2B})
    # os 15 do acervo (e as 3 missões normais do e2e, de 58 a 71 mil caracteres) ficam como estavam
    assert not any(og.por_trocas(_estado(m)) for m in _missoes())
    assert not og.por_trocas({"one_pager_po": "x" * 131_000}) and og.por_trocas({"one_pager_po": "x" * 133_000})


def test_secoes_numeradas_do_po_real_incluem_as_subsecoes_e_param_no_brief():
    b = og.blocos(PO_3EF2B)
    assert [k for k in b] == [str(n) for n in range(19)]
    assert "## 0.2 Como a missão funciona passo a passo" in PO_3EF2B[b["0"][0]:b["0"][1]], "0.1 e 0.2 são da seção 0"
    assert PO_3EF2B[b["18"][1]:].lstrip().startswith("# MISSÃO DIGITAL UNOORIA · BRIEFING DE ESCOPO")
    # os títulos numerados do brief («### 1. O QUE É ESTA MISSÃO») não viram seção
    assert "### 1. O QUE É ESTA MISSÃO" in PO_3EF2B[b["18"][1]:]


def _nucleo_da_3ef2b() -> str:
    """O núcleo como o A004 o devolve: as seções 0, 1, 3 e 4 do one-pager do PO, uma proposta nova no §4 e a 18-parcial."""
    b = og.blocos(PO_3EF2B)
    secao = {n: PO_3EF2B[slice(*b[str(n)])] for n in (0, 1, 3, 4)}
    secao[4] = secao[4].rstrip() + "\n\n[PROPOSTA — validar com PO: núcleo de teste — o voto A·2 pediu a régua por extenso]\n"
    return ("# Núcleo narrativo — De onde veio a terça?\n\n" + "".join(secao[n] for n in (0, 1, 3, 4))
            + "\n## 18-parcial. Decisões de direção e propostas P0a\n\n### Decisões de direção desta versão\n\n"
              "- O núcleo partiu do one-pager do PO v7, sem mudar o mecanismo.\n\n"
              "### Alterações sobre o one-pager do PO\n\n| Trecho do PO | Como ficou | Pedido do PO ou voto do comitê |\n"
              "|---|---|---|\n")


def test_base_das_secoes_de_apoio_copia_o_nucleo_por_codigo():
    base = og.base_do_papel({"one_pager_po": PO_3EF2B, "nucleo_narrativo": _nucleo_da_3ef2b()}, "secoes_apoio")
    b = og.blocos(base)
    assert "núcleo de teste" in base[slice(*b["4"])], "a seção 4 é a do núcleo"
    assert f"### {og.TITULO_NUCLEO_18}" in base[slice(*b["18"])], "a 18-parcial entra no fim da 18"
    assert "#### Alterações sobre o one-pager do PO" in base, "um nível abaixo, e ainda lida como tabela de alterações"
    from tools.one_pager_po import conferir

    assert conferir(PO_3EF2B, base)["perdidas"] == [], "nada do PO se perde na montagem"
    # de novo, sobre a base: a 18-parcial é trocada, não repetida
    de_novo = og.sincronizar_com_nucleo(base, _nucleo_da_3ef2b())
    assert de_novo.count(og.TITULO_NUCLEO_18) == 1 and de_novo.count("núcleo de teste") == 1


class _EditorFalso:
    """O editor de trocas: devolve trocas fixas e guarda o pedido e o documento que recebeu."""

    def __init__(self, edicoes, pendencias=(), modo=ed.MODO_PONTUAL, motivo=""):
        self.edicoes, self.pendencias, self.modo, self.motivo = list(edicoes), list(pendencias), modo, motivo
        self.chamadas: List[Dict[str, Any]] = []

    async def __call__(self, pedido, etapa, documentos, *, erros="", achados=""):
        self.chamadas.append({"pedido": pedido, "etapa": etapa, "documentos": dict(documentos)})
        return ed.Proposta(modo=self.modo, motivo=self.motivo, edicoes=list(self.edicoes),
                           pendencias=list(self.pendencias))


def test_a014_com_o_one_pager_real_da_3ef2b_nao_reescreve_e_nao_corta():
    """O A014 não roda (o modelo dele não existe): o one-pager sai do código, com as trocas do editor que se aplicam, e
    as que não se aplicam viram pendência do PO. A conferência do one-pager do PO (A015) passa."""
    import agents.callbacks as cb
    from agents.produto import get_one_pager_po_check, get_secoes_apoio_agent

    b = og.blocos(PO_3EF2B)
    alvo = _linha_unica(PO_3EF2B, *b["9"])
    apagar = _linha_unica(PO_3EF2B, *b["10"])
    editor = _EditorFalso([
        ed.Edicao("one_pager", alvo, alvo + "\n\n[PROPOSTA — validar com PO: teste de troca — o voto B·3 pediu]", "voto B·3"),
        ed.Edicao("one_pager", "trecho que não existe no documento", "x", "voto A·1"),
        ed.Edicao("one_pager", apagar, "", "o gate pediu para tirar"),
    ], pendencias=["o voto F·2 pede outro tempo para a etapa 5, que o PO fixou"])
    autor = get_secoes_apoio_agent(model="modelo-que-nao-existe")
    raiz = SequentialAgent(name="R", sub_agents=[autor, get_one_pager_po_check("A015OnePagerPoCheck", estrito=False)])
    estado = {"one_pager_po": PO_3EF2B, "material_anexado": MATERIAL_3EF2B, "nucleo_narrativo": _nucleo_da_3ef2b(),
              "briefing": "Gere a missão a partir do one-pager anexado.",
              "comite_canal_a_report": "## Voto A·1\nRELATÓRIO DO PAINEL A DE TESTE"}
    with mock.patch.object(cb, "PROPONENTE_DO_ONE_PAGER_GRANDE", editor):
        final = asyncio.run(_rodar(raiz, estado))
    doc = final["one_pager"]
    assert len(editor.chamadas) == 1, "um editor por rodada, nenhum autor"
    assert "RELATÓRIO DO PAINEL A DE TESTE" in editor.chamadas[0]["pedido"]
    assert "autor das seções de apoio" in editor.chamadas[0]["pedido"]
    assert "núcleo de teste" in editor.chamadas[0]["documentos"]["one_pager"], "o editor recebe a base com o núcleo"
    assert len(doc) > len(PO_3EF2B), "o documento inteiro, sem corte"
    assert "teste de troca" in doc, "a troca que se aplica entra"
    assert apagar in doc, "a troca que apaga texto do PO é recusada"
    pendencias = [l for l in doc.splitlines() if l.startswith("- [ABERTO — dono: PO:")]
    assert len(pendencias) == 3 and og.TITULO_PENDENCIAS in doc
    assert "trecho que não existe" in pendencias[0] and "o voto F·2" in pendencias[2]
    assert [n["papel"] for n in final[og.KEY_TROCAS_NAO_APLICADAS]] == ["secoes_apoio", "secoes_apoio"]
    assert final["one_pager_po_status"] == "aprovado", "o A015 confere: nenhum trecho do PO perdido"
    assert final["one_pager_gate0"] == doc


def test_com_o_one_pager_do_po_que_cabe_o_autor_escreve_como_sempre():
    """Mutante do modo por trocas: com o one-pager do PO do acervo (exp06ef1b, 65 mil caracteres) o callback não age."""
    from agents.callbacks import montar_one_pager_por_trocas

    estado = _estado("exp06ef1b")
    assert estado["one_pager_po"] and asyncio.run(montar_one_pager_por_trocas("secoes_apoio")(_Ctx(estado))) is None
    assert asyncio.run(montar_one_pager_por_trocas("restaurador")(_Ctx({}))) is None


def test_restaurador_com_o_po_grande_recebe_os_trechos_por_extenso_e_os_devolve_por_troca():
    import agents.callbacks as cb
    from agents.callbacks import montar_one_pager_por_trocas

    from tools.one_pager_po import conferir

    b = og.blocos(PO_3EF2B)
    # uma linha da seção 7 que a conferência acusa quando some (a régua aceita 85% dos trigramas em outro lugar)
    for perdida in (l for l in PO_3EF2B[slice(*b["7"])].splitlines() if len(l) >= 60 and PO_3EF2B.count(l) == 1):
        atual = PO_3EF2B.replace(perdida + "\n", "", 1)
        if conferir(PO_3EF2B, atual)["perdidas"]:
            break
    vizinha = _linha_unica(atual, b["7"][0], b["7"][1] - len(perdida))
    assert perdida not in atual
    editor = _EditorFalso([ed.Edicao("one_pager", vizinha, vizinha + "\n" + perdida, "restaurar")])
    ctx = _Ctx({"one_pager_po": PO_3EF2B, "one_pager": atual, "one_pager_po_report": "1 trecho perdido"},
               agente="A037RestaurarOnePagerPo")
    with mock.patch.object(cb, "PROPONENTE_DO_ONE_PAGER_GRANDE", editor):
        conteudo = asyncio.run(montar_one_pager_por_trocas("restaurador")(ctx))
    assert perdida in editor.chamadas[0]["pedido"], "o trecho perdido vai inteiro, copiado do PO"
    assert "restaurador do one-pager do PO" in editor.chamadas[0]["pedido"]
    assert perdida in conteudo.parts[0].text and og.TITULO_PENDENCIAS not in conteudo.parts[0].text


def test_editor_sem_trocas_deixa_o_po_intacto_e_avisa():
    import agents.callbacks as cb
    from agents.callbacks import montar_one_pager_por_trocas

    editor = _EditorFalso([], modo=ed.MODO_ESTRUTURAL, motivo="o editor foi cortado pelo limite de saída do modelo")
    ctx = _Ctx({"one_pager_po": PO_3EF2B, "nucleo_narrativo": _nucleo_da_3ef2b(), "retrabalho_one_pager": "corrija X"})
    with mock.patch.object(cb, "PROPONENTE_DO_ONE_PAGER_GRANDE", editor):
        conteudo = asyncio.run(montar_one_pager_por_trocas("secoes_apoio")(ctx))
    assert "corrija X" in editor.chamadas[0]["pedido"] and ctx.state["retrabalho_one_pager"] == ""
    assert conteudo.parts[0].text == og.base_do_papel({"one_pager_po": PO_3EF2B,
                                                       "nucleo_narrativo": _nucleo_da_3ef2b()}, "secoes_apoio")
    assert ctx.state[og.KEY_TROCAS_NAO_APLICADAS][0]["falha"].startswith("o editor foi cortado")


def test_retrabalho_do_one_pager_grande_vai_ao_editor_uma_vez_so():
    """O retrabalho por trocas não roda antes: os motivos ficam para o one-pager por trocas, que os leva ao editor."""
    from agents.callbacks import retrabalhar_por_trocas

    ctx = _Ctx({"one_pager_po": PO_3EF2B, "one_pager": PO_3EF2B, "retrabalho_one_pager": "o gate reprovou"})
    with mock.patch.dict(os.environ, {"RETRABALHO_POR_TROCAS": "true"}):
        assert asyncio.run(retrabalhar_por_trocas("one_pager")(ctx)) is None
    assert ctx.state["retrabalho_one_pager"] == "o gate reprovou"


def test_aplicar_parcial_fica_com_as_boas_e_diz_por_que_cada_ruim_falhou():
    docs = {"d": "um dois três\nquatro cinco seis\n"}
    r = ed.aplicar_parcial(docs, [ed.Edicao("d", "um dois", "1 2"), ed.Edicao("d", "não existe", "x"),
                                  ed.Edicao("d", "quatro", "4")],
                           validador=lambda novos: ["apagou o quatro"] if "quatro" not in novos["d"] else [])
    assert r.documentos["d"] == "1 2 três\nquatro cinco seis\n"
    assert [e.de for e in r.aplicadas] == ["um dois"]
    assert r.falhas[0].startswith("edição 2") and r.falhas[1].startswith("edição 3") and "recusada" in r.falhas[1]
    # tudo bom: é o `aplicar` de sempre
    assert ed.aplicar_parcial(docs, [ed.Edicao("d", "um", "1")]).ok


def test_editor_tem_uma_tentativa_com_documento_grande():
    from pipeline import reexecucao as rx

    assert rx.tentativas_do_editor({"one_pager": "x" * 70_000}) == 1, "o one-pager de 71 mil caracteres da 1em1b"
    assert rx.tentativas_do_editor({"one_pager": "x" * 60_000}) == rx.TENTATIVAS_DO_EDITOR
    chamadas = []

    async def editor(pedido, etapa, documentos, *, erros="", achados=""):
        chamadas.append(1)
        return ed.Proposta(modo=ed.MODO_PONTUAL, edicoes=[ed.Edicao("one_pager", "não existe", "x")])

    resultado, proposta = asyncio.run(rx.editar("p", "retrabalho", {"one_pager": "y" * 70_000}, proponente=editor))
    assert resultado is None and len(chamadas) == 1 and "em 1 tentativa —" in proposta.motivo
    chamadas.clear()
    asyncio.run(rx.editar("p", "retrabalho", {"one_pager": "y" * 6_000}, proponente=editor))
    assert len(chamadas) == rx.TENTATIVAS_DO_EDITOR


def test_motivo_do_corte_do_editor_vai_para_a_proposta():
    from pipeline.reexecucao import com_corte_do_editor

    p = com_corte_do_editor(ed.ler_proposta("```json\n{\"modo\": \"pon"),
                            {"cortes_do_modelo": {"A000EditorPontual": {"caracteres": 65000}}})
    assert p.motivo.startswith("o editor foi cortado pelo limite de saída do modelo em 65000 caracteres")
    assert "não devolveu uma proposta legível" in p.motivo


# --------------------------------------------------------------------------- corte com texto (G02)
def _resposta(texto: str, motivo: str) -> LlmResponse:
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=texto)]),
                       finish_reason=getattr(types.FinishReason, motivo))


def test_resposta_cortada_com_texto_e_registrada_e_some_quando_o_agente_termina_inteiro():
    from agents.callbacks import KEY_CORTES_DO_MODELO, PREFIXO_BLOQUEIO_MODELO, registrar_corte_do_modelo

    ctx = _Ctx({}, output_key="one_pager")
    registrar_corte_do_modelo(ctx, _resposta("# One-pager\n" + "x" * 218_000, "MAX_TOKENS"))
    corte = ctx.state[KEY_CORTES_DO_MODELO]["A014SecoesApoio"]
    assert corte["chave"] == "one_pager" and corte["caracteres"] > 218_000 and corte["vezes"] == 1
    assert "cortada em" in ctx.state[f"{PREFIXO_BLOQUEIO_MODELO}A014SecoesApoio"]
    registrar_corte_do_modelo(ctx, _resposta("de novo", "MAX_TOKENS"))
    assert ctx.state[KEY_CORTES_DO_MODELO]["A014SecoesApoio"]["vezes"] == 2
    registrar_corte_do_modelo(ctx, _resposta("# One-pager inteiro", "STOP"))
    assert ctx.state[KEY_CORTES_DO_MODELO] == {} and ctx.state[f"{PREFIXO_BLOQUEIO_MODELO}A014SecoesApoio"] == ""
    # o caso antigo continua: sem texto, o motivo vai à próxima instrução, e não há documento cortado
    registrar_corte_do_modelo(ctx, LlmResponse(content=types.Content(role="model", parts=[]),
                                               finish_reason=types.FinishReason.RECITATION))
    assert "recitação" in ctx.state[f"{PREFIXO_BLOQUEIO_MODELO}A014SecoesApoio"]
    assert ctx.state[KEY_CORTES_DO_MODELO] == {}


class _Semente(BaseAgent):
    delta: Dict[str, Any] = {}

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta=dict(self.delta)))


def _saida(rodadas: int = 3):
    from agents.checkers import SaidaDeLoopAgent

    return SaidaDeLoopAgent(name="Saida", status_keys=["gate_status"], rodada_key="r", max_rounds=rodadas,
                            autor_keys=["one_pager"])


def test_saida_do_loop_nao_aprova_documento_cortado_e_para_no_segundo_corte():
    corte = {"agente": "A014SecoesApoio", "chave": "one_pager", "caracteres": 218_000, "motivo": "MAX_TOKENS"}
    base = {"gate_status": "aprovado", "one_pager": "# One-pager cortado no §12a", "retrabalho_one_pager": "x"}
    eventos: List[Event] = []
    final = asyncio.run(_rodar(_saida(), {**base, "cortes_do_modelo": {"A014SecoesApoio": {**corte, "vezes": 1}}},
                               eventos))
    saida = [e for e in eventos if e.author == "Saida"][-1]
    assert not saida.actions.escalate, "gates verdes, documento cortado: o autor escreve de novo"
    assert "cortado pelo limite de saída" in saida.content.parts[0].text
    assert final["retrabalho_one_pager"] == "" and final["rodada_anterior_one_pager"] == ""
    assert not final.get("degradacoes")

    eventos.clear()
    final = asyncio.run(_rodar(_saida(), {**base, "cortes_do_modelo": {"A014SecoesApoio": {**corte, "vezes": 2}}},
                               eventos))
    saida = [e for e in eventos if e.author == "Saida"][-1]
    assert saida.actions.escalate, "cortado de novo: outra rodada igual daria o mesmo corte"
    assert final["degradacoes"][0]["gate"] == "corte_do_modelo_one_pager"
    assert "A014SecoesApoio" in final["degradacoes"][0]["motivo"] and final["pipeline_bloqueado"] is True
    # o núcleo, cujo loop não tem `autor_keys`, também não sai aprovado cortado — e não ganha versão da rodada
    from agents.checkers import SaidaDeLoopAgent

    eventos.clear()
    nucleo = SaidaDeLoopAgent(name="Saida", status_keys=["gate_status"], rodada_key="r", max_rounds=2,
                              cortes_de=["nucleo_narrativo"])
    final = asyncio.run(_rodar(nucleo, {"gate_status": "aprovado", "cortes_do_modelo": {"A004NucleoNarrativo": {
        **corte, "agente": "A004NucleoNarrativo", "chave": "nucleo_narrativo", "vezes": 1}}}, eventos))
    assert not [e for e in eventos if e.author == "Saida"][-1].actions.escalate
    assert "rodada_anterior_nucleo_narrativo" not in final
    # mutante: sem corte, os gates verdes encerram o loop como antes
    eventos.clear()
    asyncio.run(_rodar(_saida(), dict(base), eventos))
    assert [e for e in eventos if e.author == "Saida"][-1].actions.escalate


# --------------------------------------------------------------------------- A004 só com a mensagem do PO (G01)
def test_a004_recebe_so_a_mensagem_do_po_sem_o_one_pager_repetido():
    from agents.callbacks import PONTEIRO_PO_NA_MENSAGEM, so_a_mensagem_do_po

    mensagem = types.Content(role="user", parts=[types.Part(text="Gere a missão.\n\n---\n" + MATERIAL_3EF2B)])
    historico = [types.Content(role="model" if i % 2 else "user", parts=[types.Part(text=f"evento {i} " + "y" * 60_000)])
                 for i in range(10)]
    pedido = LlmRequest(contents=list(historico))
    so_a_mensagem_do_po(_Ctx({"one_pager_po": PO_3EF2B}, agente="A004NucleoNarrativo", user_content=mensagem), pedido)
    assert len(pedido.contents) == 1 and pedido.contents[0].role == "user"
    texto = pedido.contents[0].parts[0].text
    assert texto.startswith("Gere a missão.") and PONTEIRO_PO_NA_MENSAGEM in texto and PO_3EF2B not in texto
    assert "Documento de apoio (DOCX)" in texto, "o resto da mensagem e o cabeçalho do anexo ficam"
    assert mensagem.parts[0].text.endswith(PO_3EF2B), "a mensagem original da sessão não é alterada"
    # sem one-pager do PO, a mensagem vai inteira
    pedido = LlmRequest(contents=list(historico))
    so_a_mensagem_do_po(_Ctx({}, user_content=mensagem), pedido)
    assert pedido.contents[0].parts[0].text == mensagem.parts[0].text


def test_a004_tem_o_callback_e_todo_agente_tem_o_orcamento_por_ultimo():
    from agents.callbacks import so_a_mensagem_do_po
    from agents.produto import get_micro_gate_agent, get_nucleo_narrativo_agent

    a004 = get_nucleo_narrativo_agent()
    assert a004.include_contents == "default" and a004.before_model_callback[0] is so_a_mensagem_do_po
    assert a004.before_model_callback[-1].__name__ == "orcamento_de_contexto"
    assert get_micro_gate_agent().before_model_callback[-1].__name__ == "orcamento_de_contexto_juiz"


def _pedido_ao_modelo(instrucao: str, historico: str = "") -> LlmRequest:
    return LlmRequest(config=types.GenerateContentConfig(system_instruction=instrucao),
                      contents=[types.Content(role="user", parts=[types.Part(text=historico or "go")])])


def test_prevoo_nao_manda_a_requisicao_acima_do_teto_e_diz_qual_agente_e_quanto():
    from agents.callbacks import orcamento_de_contexto

    estado = {"one_pager": "o" * 2_000_000, "nucleo_narrativo": "n" * 900_000, "briefing": "b"}
    with pytest.raises(contexto.ContextoGrandeDemais) as erro:
        orcamento_de_contexto(False)(_Ctx(estado, agente="A004NucleoNarrativo"),
                                     _pedido_ao_modelo("i" * 1_000_000, "h" * 2_000_000))
    texto = str(erro.value)
    assert "A004NucleoNarrativo" in texto and "1.048.576" in texto and "`one_pager`" in texto
    assert contexto.erro_deterministico(erro.value)
    # abaixo do teto: segue, e nada muda numa instrução sem one-pager do PO
    pedido = _pedido_ao_modelo("instrução curta")
    assert orcamento_de_contexto(True)(_Ctx(estado), pedido) is None
    assert pedido.config.system_instruction == "instrução curta"


def test_400_de_tamanho_vira_mensagem_legivel_e_erro_deterministico():
    from google.genai.errors import ClientError, ServerError

    from pipeline.runner import mensagem_de_erro

    erro = ClientError(400, {"error": {"code": 400, "status": "INVALID_ARGUMENT", "message":
                                       "The input token count exceeds the maximum number of tokens allowed 1048576."}})
    msg = mensagem_de_erro(erro, "A004NucleoNarrativo")
    assert "A004NucleoNarrativo" in msg and "1.048.576" in msg and "tentar de novo dá o mesmo erro" in msg
    assert contexto.erro_deterministico(erro)
    # outro 400 do modelo também se repete igual: quem tenta de novo não deve tentar sem mudar a entrada
    assert contexto.erro_deterministico(ClientError(400, {"error": {"code": 400, "status": "INVALID_ARGUMENT",
                                                                    "message": "Request contains an invalid argument."}}))
    assert not contexto.erro_deterministico(ServerError(503, {"error": {"code": 503, "message": "overloaded"}}))
    assert not contexto.erro_deterministico(ClientError(429, {"error": {"code": 429, "message": "quota"}}))


def test_nucleo_nao_roda_so_porque_o_12a_do_a014_falhou():
    """T23: na 3ef2b, com os dois painéis aprovados, o núcleo era reescrito a cada volta pelo §12a truncado do A014."""
    from agents.callbacks import manter_nucleo_sem_achado_do_a004 as manter

    nucleo = "# Núcleo\n\nFoco primário: `EF03CO05`."
    env = lambda codigo: {"status": "bloqueado", "achados": [  # noqa: E731
        {"severidade": "bloqueio", "codigo": "regra-ternaria-ausente", "resumo": f"`{codigo}`: o Canal A não diz…"}]}
    base = {"nucleo_narrativo": nucleo, "evidencia_one_pager_status": "bloqueado"}
    assert manter(_Ctx({**base, "evidencia_one_pager_status_envelope": env("EF03CO09")})) is not None
    assert manter(_Ctx({**base, "evidencia_one_pager_status_envelope": env("EF03CO05")})) is None, "foco primário"
    assert manter(_Ctx({**base, "evidencia_one_pager_status_envelope": {"status": "bloqueado", "achados": [
        {"codigo": "12a-ausente", "resumo": "O one-pager não tem o §12a"}]}})) is not None, "o §12a é montado pelo A014"
    assert manter(_Ctx(base)) is None, "sem envelope legível: na dúvida, o núcleo roda"


# --------------------------------------------------------------------------- orçamento e cache (G20)
def test_juiz_nao_recebe_o_one_pager_do_po_grande_ao_lado_do_one_pager_que_o_preserva():
    one_pager = PO_3EF2B + "\n\n### Alterações sobre o one-pager do PO\n\n| a | b | c |\n"
    estado = {"one_pager_po": PO_3EF2B, "one_pager": one_pager, "material_anexado": MATERIAL_3EF2B,
              "one_pager_po_status": "aprovado"}
    instrucao = f"Julgue.\n\n{one_pager}\n\nMaterial:\n{MATERIAL_3EF2B}\n\nPO:\n{PO_3EF2B}\n\nFim."
    nova, cortes = contexto.cortar_para_o_orcamento(instrucao, estado)
    assert nova.count(PO_3EF2B) == 1 and one_pager in nova, "fica só a cópia dentro do one-pager da missão"
    assert nova.count(contexto.PONTEIRO_PO_PRESERVADO) == 2 and "2 cópias" in cortes[0]
    assert contexto.estimar_tokens(nova) < contexto.estimar_tokens(instrucao) / 2
    # sem a conferência aprovada, ou com o one-pager do PO que cabe, nada sai
    assert contexto.cortar_para_o_orcamento(instrucao, {**estado, "one_pager_po_status": "bloqueado"}) == (instrucao, [])
    pequeno = _estado("exp06ef1b")
    instr = f"{pequeno['one_pager']}\n\n{pequeno['one_pager_po']}"
    assert contexto.cortar_para_o_orcamento(instr, {**pequeno, "one_pager_po_status": "aprovado"}) == (instr, [])


def test_acima_do_orcamento_sai_o_que_nao_e_contrato_e_as_secoes_0_a_17_ficam():
    estado = {"one_pager": PO_3EF2B}
    nova, cortes = contexto.cortar_para_o_orcamento("Julgue:\n" + PO_3EF2B, estado, orcamento=60_000)
    assert [c.split(" de `")[0] for c in cortes] == ["histórico de versões", "brief de escopo repetido",
                                                     "corpo da seção 18"]
    b = og.blocos(PO_3EF2B)
    for n in range(18):  # as seções 0 a 17, inteiras: textos-chave, números e IDs
        assert PO_3EF2B[slice(*b[str(n)])] in nova
    assert "BRIEFING DE ESCOPO" not in nova and "18.3 Inconsistências" in nova, "da 18 ficam os títulos"
    assert contexto.estimar_tokens(nova) < contexto.estimar_tokens(PO_3EF2B)
    # abaixo do orçamento, nada muda
    assert contexto.cortar_para_o_orcamento("Julgue:\n" + PO_3EF2B, estado) == ("Julgue:\n" + PO_3EF2B, [])


def test_po_grande_vai_para_o_comeco_da_instrucao_e_o_pequeno_fica_onde_esta():
    instrucao = f"Você é o gate.\n\n**One-pager do PO (anexo):**\n\n{PO_3EF2B}\n\nRegras."
    nova = contexto.po_primeiro(instrucao, {"one_pager_po": PO_3EF2B})
    assert nova.startswith(contexto.TITULO_PO_PRIMEIRO + "\n\n" + PO_3EF2B[:200])
    assert nova.count(PO_3EF2B) == 1 and contexto.PONTEIRO_PO_PRIMEIRO in nova and nova.endswith("Regras.")
    assert contexto.po_primeiro(nova, {"one_pager_po": PO_3EF2B}) == nova
    # dentro do material anexado (o one-pager do PO foi extraído dele), mover cortaria o material
    com_material = f"Material:\n{MATERIAL_3EF2B}"
    assert contexto.po_primeiro(com_material, {"one_pager_po": PO_3EF2B, "material_anexado": MATERIAL_3EF2B}) == com_material
    pequeno = _estado("exp06ef1b")["one_pager_po"]
    assert contexto.po_primeiro(f"x {pequeno} y", {"one_pager_po": pequeno}) == f"x {pequeno} y"


def test_no_acervo_nenhuma_instrucao_muda():
    """As 15 missões do acervo: com o one-pager do PO que cabe e abaixo do orçamento, o orçamento de contexto não muda
    a instrução de nenhum agente (é a conta de `scripts/medir_contexto.py`)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("medir_contexto", RAIZ / "scripts" / "medir_contexto.py")
    medir_contexto = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(medir_contexto)
    agentes = medir_contexto.agentes(["produto", "design", "dev"])
    assert len(agentes) > 50
    mudaram = []
    for missao in _missoes():
        linhas = medir_contexto.medir(_estado(missao), lista=agentes)
        mudaram += [(missao, l["agente"]) for l in linhas if l["antes"] != l["depois"]]
        assert max(l["antes"] for l in linhas) < contexto.ORCAMENTO_JUIZ
    assert mudaram == []
    # o mesmo estado com o one-pager da 3ef2b no lugar: os juízes que liam o one-pager do PO duas vezes caem
    estado = {**_estado("exp06ef1b"), "one_pager_po": PO_3EF2B, "material_anexado": MATERIAL_3EF2B,
              "one_pager": og.sincronizar_com_nucleo(PO_3EF2B, _nucleo_da_3ef2b()), "one_pager_po_status": "aprovado"}
    linhas = {l["agente"]: l for l in medir_contexto.medir(estado, lista=agentes)}
    assert linhas["A029aAvaliacaoPedagogica"]["depois"] < linhas["A029aAvaliacaoPedagogica"]["antes"] / 2
    assert linhas["A004NucleoNarrativo"]["po_primeiro"]


# --------------------------------------------------------------------------- na queda, o estado parcial (G19)
class _EscreveECai(BaseAgent):
    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(
            state_delta={"nucleo_narrativo": "# Núcleo da rodada 4", "one_pager": "# One-pager parcial"}))
        from google.genai.errors import ClientError

        raise ClientError(400, {"error": {"code": 400, "status": "INVALID_ARGUMENT", "message":
                                          "The input token count exceeds the maximum number of tokens allowed 1048576."}})


def _rodar_runner(runner_mod, **kw) -> List[Dict[str, Any]]:
    eventos = []

    async def _ir():
        async for evento in runner_mod.run_orchestrator_pipeline_stream(prompt="p", stages=["produto"],
                                                                        registrar_conversa=False, com_transversal=False,
                                                                        **kw):
            eventos.append(evento)

    asyncio.run(_ir())
    return eventos


def test_na_queda_o_estado_parcial_e_a_telemetria_ficam_na_pasta_da_sessao(tmp_path, monkeypatch):
    import pipeline.runner as runner_mod

    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "saida"))
    monkeypatch.setattr(runner_mod, "create_mission_orchestrator", lambda **kw: _EscreveECai(name="A004Falso"))
    sessao = tmp_path / "sessao"
    sessao.mkdir()
    (sessao / "conversa.json").write_text("{}", encoding="utf-8")  # a 3ef2b só tinha isto
    erro = [e for e in _rodar_runner(runner_mod, run_dir=sessao) if e["type"] == "pipeline_error"][0]
    assert erro["deterministico"] and erro["agente"] == "A004Falso"
    assert "A004Falso" in erro["error"] and "1.048.576" in erro["error"]
    estado = json.loads((sessao / "estado.json").read_text(encoding="utf-8"))
    assert estado["execucao"]["status"] == "erro" and estado["execucao"]["agente"] == "A004Falso"
    assert estado["nucleo_narrativo"] == "# Núcleo da rodada 4", "o que a execução já tinha escrito"
    assert (sessao / "produto" / "00a-nucleo-narrativo.md").exists(), "os artefatos parciais"
    linha = estado["custo_missao"]["execucoes"][-1]
    assert linha["falhou"] and "tokens_por_agente" in linha and erro["estado_parcial"] == str(sessao)


def test_na_queda_de_uma_reexecucao_a_sessao_fica_como_estava_e_o_parcial_vai_para_falhas(tmp_path, monkeypatch):
    import pipeline.runner as runner_mod

    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "saida"))
    monkeypatch.setattr(runner_mod, "create_mission_orchestrator", lambda **kw: _EscreveECai(name="A004Falso"))
    sessao = tmp_path / "sessao"
    sessao.mkdir()
    (sessao / "estado.json").write_text(json.dumps({"one_pager": "# o de antes"}), encoding="utf-8")
    erro = [e for e in _rodar_runner(runner_mod, run_dir=sessao) if e["type"] == "pipeline_error"][0]
    assert json.loads((sessao / "estado.json").read_text(encoding="utf-8")) == {"one_pager": "# o de antes"}
    parcial = Path(erro["estado_parcial"])
    assert parcial.parent.name == ".falhas" and parcial.parent.parent == sessao
    assert json.loads((parcial / "estado.json").read_text(encoding="utf-8"))["one_pager"] == "# One-pager parcial"


def test_prevoo_no_runner_para_antes_de_chamar_o_modelo(tmp_path, monkeypatch):
    """Um agente de verdade, com o modelo que não existe: o pré-voo barra a requisição antes de o modelo ser chamado."""
    import pipeline.runner as runner_mod
    from agents.base import create_llm_agent

    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "saida"))
    # o nome do modelo é resolvido antes do callback; a chave da API não: se o pré-voo falhasse, a chamada cairia
    agente = create_llm_agent(name="A004Gigante", instruction="Leia: {documento_enorme}", description="teste",
                              output_key="nucleo_narrativo")
    monkeypatch.setattr(runner_mod, "create_mission_orchestrator", lambda **kw: agente)
    eventos = _rodar_runner(runner_mod, run_dir=tmp_path / "sessao",
                            initial_state={"documento_enorme": "palavra " * 400_000})
    erro = [e for e in eventos if e["type"] == "pipeline_error"][0]
    assert "A004Gigante" in erro["error"] and "A chamada não foi feita" in erro["error"] and erro["deterministico"]
    assert "`documento_enorme`" in erro["error"]


def test_custo_de_cada_execucao_leva_os_tokens_por_agente():
    from tools import custo

    t = {"entrada": 1000, "saida": 10, "pensamento": 0, "cache": 0, "chamadas": 1, "maior_entrada": 1000}
    linha = custo.custo_da_execucao({"A004NucleoNarrativo": t}, "gemini-3.8-flash", {})
    assert linha["tokens_por_agente"]["A004NucleoNarrativo"]["maior_entrada"] == 1000
    acumulado = custo.acumular(custo.acumular(None, linha, ["produto"]), linha, ["design"])
    assert all("tokens_por_agente" in l for l in acumulado["execucoes"])
    assert acumulado["total"]["tokens"]["entrada"] == 2000


# --------------------------------------------------------------------------- manifesto e diagnóstico (G26)
def test_manifesto_nao_lista_como_ausente_o_que_a_execucao_nao_precisava_produzir():
    from pipeline.artifacts import ARTIFACT_FILES
    from tools.diagnostico import artefatos_esperados

    estado = {k: "texto" for k, _ in ARTIFACT_FILES}
    for k in ("spec_missao_gate0", "validacao_produto_narrativa", "validacao_design_imersao",
              "validacao_pedagogia_bncc", "stitch_links", "linha_de_base_report"):
        estado.pop(k)
    assert artefatos_esperados(estado, ARTIFACT_FILES)["ausentes"] == []
    # com o Stitch ligado, as telas fazem falta; na correção pontual, a linha de base também
    ausentes = artefatos_esperados({**estado, "stitch_ligado": True, "modo_correcao": "pontual"}, ARTIFACT_FILES)
    assert ausentes["ausentes"] == ["design/10-stitch-telas.md", "linha-de-base-da-correcao.md"]
    # o dispensado que existe continua entregue
    assert "produto/05a-spec-missao-gate0.md" in artefatos_esperados(
        {**estado, "spec_missao_gate0": "# spec"}, ARTIFACT_FILES)["entregues"]


def test_diagnostico_mostra_o_corte_e_as_trocas_nao_aplicadas_com_explicacao_para_o_po():
    from tools import diagnostico
    from tools import explicacoes as ex

    estado = {"cortes_do_modelo": {"A045SpecMissao": {"agente": "A045SpecMissao", "chave": "spec_missao",
                                                      "caracteres": 230_000, "motivo": "MAX_TOKENS", "vezes": 2}},
              og.KEY_TROCAS_NAO_APLICADAS: [
                  {"papel": "secoes_apoio", "motivo": "voto", "de": "texto", "para": "outro", "falha": "não existe"},
                  {"papel": "revisor", "motivo": "", "de": "", "para": "", "falha": "o editor foi cortado"}]}
    achados = {a["codigo"]: a for a in diagnostico.coletar(estado)["achados"]}
    assert achados["documento-cortado-pelo-modelo"]["severidade"] == "bloqueio"
    assert "spec_missao" in achados["documento-cortado-pelo-modelo"]["resumo"]
    assert achados["troca-nao-aplicada"]["severidade"] == "decisao_humana"
    assert achados["editor-sem-trocas"]["severidade"] == "atencao"
    for codigo, quem in (("documento-cortado-pelo-modelo", ex.ESTEIRA), ("troca-nao-aplicada", ex.PO),
                         ("editor-sem-trocas", ex.ESTEIRA)):
        explicacao = ex.explicar({"codigo": codigo, "resumo": "x"})
        assert not explicacao.generica and explicacao.quem == quem


def test_refazer_a_etapa_limpa_o_corte_dos_documentos_dela():
    from pipeline.reexecucao import preparar_estado

    estado = {"one_pager": "x", "spec_missao": "s", "handoff_dev": "h",
              "cortes_do_modelo": {"A014SecoesApoio": {"chave": "one_pager"}, "A100aHandoffDev": {"chave": "handoff_dev"}}}
    limpo, _ = preparar_estado(estado, "dev")
    assert list(limpo["cortes_do_modelo"]) == ["A014SecoesApoio"], "refazer o dev não desfaz o corte de produto"
    assert preparar_estado(estado, "produto")[0]["cortes_do_modelo"] == {}, "produto refeito refaz tudo depois dele"
