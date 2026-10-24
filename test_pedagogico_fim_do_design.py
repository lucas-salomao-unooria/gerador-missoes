"""O one-pager pedagógico fecha o design, montado sobre o contrato, e o de acordo de design é dado sobre ele (PR 10).

Combinado com o usuário depois do plano «Produto dono do contrato» (docs/planos/2026-10-23-produto-dono-do-contrato.md).
O time validava a missão pelos protótipos de design contra o one-pager de produto, que não descreve a missão inteira, e
voltava para refazer porque não ficava claro o que a missão ia ser. O pedagógico (A120) era o último passo do dev:

- agora é o fim do design (depois da banca, do QA e do rastro de design; antes do parecer), e o de acordo de design é
  dado sobre ele (`pipeline.passagem.documento_a_aprovar`, o cartão do app);
- o contrato — habilidades, Canal B, tempos, podcast, roteiro — entra por código (`tools.pedagogico.montar`, A120b), e o
  gate de montagem (A121b) confere a narrativa no molde do gate do PRD (PR 4);
- o dev só acrescenta as pendências dele numa seção própria; o texto aprovado que mudar no dev volta e bloqueia (A119b).

Os mutantes pedidos: «pedagógico com H1 25% em vez de 30%», «texto-chave reescrito no pedagógico» e «dev reescreve o
pedagógico aprovado» (tem de ser barrado). Dados reais: o acervo (`tests/acervo/`), com a exp02ef1b-4fd72a9a — a da
cadeia 30% → 25% da H1 (D11) — e as outras seis missões que chegaram ao pedagógico.
"""

import asyncio
import json
import re
from pathlib import Path
from typing import AsyncGenerator

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.events import Event, EventActions
from google.adk.runners import InMemoryRunner
from google.genai import types
from typing_extensions import override

from tools import conteudo_aprovado as ca
from tools import pedagogico as pg

ACERVO = Path(__file__).resolve().parent / "tests" / "acervo"


def _estado(nome: str = "exp02ef1b-4fd72a9a") -> dict:
    return json.loads((ACERVO / nome / "estado.json").read_text(encoding="utf-8"))


def _montado(nome: str = "exp02ef1b-4fd72a9a") -> dict:
    """A sessão do acervo com o pedagógico como a esteira de agora o deixa no fim do design: montado e com o anexo."""
    estado = _estado(nome)
    corpo = pg.montar(ca.remover_anexo(estado["one_pager_pedagogico"]), estado)
    estado["one_pager_pedagogico"] = ca.com_anexo(corpo, estado["one_pager"], ca.SECOES_PEDAGOGICO)
    return estado


def _na_secao(documento: str, titulo: str, linha: str) -> str:
    """O documento com `linha` acrescentada no começo da seção `## titulo` (na narrativa, antes de qualquer bloco)."""
    m = re.search(rf"^## {re.escape(titulo)}[^\n]*\n", documento, re.M)
    assert m, titulo
    return documento[:m.end()] + "\n" + linha + "\n" + documento[m.end():]


class _Escreve(BaseAgent):
    """Agente falso: grava um texto numa chave — o papel de um autor (ou de um mutante)."""

    chave: str
    texto: str

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    actions=EventActions(state_delta={self.chave: self.texto}))


async def _rodar(raiz, estado):
    runner = InMemoryRunner(agent=raiz, app_name="teste")
    await runner.session_service.create_session(app_name="teste", user_id="u", session_id="s", state=estado)
    async for _ in runner.run_async(user_id="u", session_id="s",
                                    new_message=types.Content(role="user", parts=[types.Part(text="go")])):
        pass
    final = await runner.session_service.get_session(app_name="teste", user_id="u", session_id="s")
    return dict(final.state)


def _rodar_sync(agentes, estado):
    return asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=list(agentes)), estado))


# --------------------------------------------------------------------------- 1. a esteira
def test_pedagogico_fecha_o_design_e_sai_do_dev():
    from google.adk.agents.llm_agent import LlmAgent

    from agents.design import DESIGN_METADATA, build_design_stage
    from agents.dev import DEV_METADATA, agentes_em_ordem, build_dev_stage
    from pipeline.orchestrator import iter_agent_tree

    design = [a.name for a in build_design_stage().sub_agents]
    # depois da banca, do QA e do rastro de design (o que ele lê); antes da matriz e da fidelidade (que o leem)
    assert design.index("QaDesignLoop") < design.index("A092RastroDesign") < design.index("OnePagerPedagogicoLoop") \
        < design.index("A124AnexoPedagogico") < design.index("A093RastreabilidadeDesign") < design.index("A094FidelidadeDesign")
    dev = build_dev_stage()
    nomes_dev = [a.name for _, a in iter_agent_tree(dev)]
    assert not {"OnePagerPedagogicoLoop", "A120OnePagerPedagogico", "A122CoerenciaPedagogico", "A124AnexoPedagogico"} \
        & set(nomes_dev)
    assert [a.name for a in agentes_em_ordem(dev)][-4:] == ["A119AnexoPrd", "A119bPedagogicoNoDev", "A125Rastreabilidade",
                                                            "A126FidelidadeDev"]
    # nenhum agente de modelo do dev escreve o pedagógico
    assert not [a.name for _, a in iter_agent_tree(dev) if isinstance(a, LlmAgent)
                and a.output_key == "one_pager_pedagogico"]
    # o catálogo acompanha: os passos 120–124 estão no design, na ordem em que rodam, e o 119b no dev
    ids_design = [m["id"] for m in DESIGN_METADATA]
    assert ids_design[ids_design.index("A092RastroDesign") + 1: ids_design.index("A093RastreabilidadeDesign")] == [
        "A120OnePagerPedagogico", "A120bContratoNoPedagogico", "A121ConteudoAprovadoPedagogico",
        "A121bMontagemPedagogico", "A122CoerenciaPedagogico", "A123PedagogicoRodada", "A124AnexoPedagogico"]
    assert not {m["id"] for m in DEV_METADATA} & {"A120OnePagerPedagogico", "A124AnexoPedagogico"}
    assert "A119bPedagogicoNoDev" in {m["id"] for m in DEV_METADATA}


def test_custo_neutro_as_chamadas_de_modelo_mudam_de_etapa():
    """Saem do dev e entram no design as mesmas chamadas: o redator (A120) e o juiz de coerência (A122), por rodada. Os
    passos novos — a montagem do contrato (A120b), o gate dela (A121b) e o guarda do dev (A119b) — são código."""
    from google.adk.agents.llm_agent import LlmAgent

    from agents.design import build_design_stage
    from agents.dev import build_dev_stage
    from pipeline.orchestrator import iter_agent_tree

    loop = next(a for a in build_design_stage().sub_agents if a.name == "OnePagerPedagogicoLoop")
    llm = sorted(a.name for _, a in iter_agent_tree(loop) if isinstance(a, LlmAgent))
    assert llm == ["A120OnePagerPedagogico", "A122CoerenciaPedagogicoJuiz"]
    no_dev = [a.name for _, a in iter_agent_tree(build_dev_stage()) if isinstance(a, LlmAgent) and "Pedagogico" in a.name]
    assert no_dev == []


def test_prompt_le_as_pendencias_do_design_e_nao_as_do_dev():
    from prompts import load_prompt

    ped = load_prompt("dev/120_one_pager_pedagogico.md")
    for chave in ("{rastro_design_report?}", "{banca_design_report?}", "{qa_entregaveis_report?}",
                  "{montagem_pedagogico_report?}", "{jornada_telas?}", "{fluxo_arestas?}", "{copy_strings_revisada?}",
                  "{anexo_design_spec?}", "{stitch_links?}", "{prototipo_relatorio?}", "design/08-prototipo.html"):
        assert chave in ped, chave
    for chave in ("{rastro_lacunas_report?}", "{validacao_dev_report?}", "{prd_final?}", "{handoff_dev?}"):
        assert chave not in ped, chave
    assert "Do one-pager aprovado" in ped and "de acordo" in ped


# --------------------------------------------------------------------------- 2. montado sobre o contrato
def test_montagem_poe_o_contrato_no_fim_de_cada_secao():
    estado = _estado()
    doc = pg.montar(estado["one_pager_pedagogico"], estado)
    blocos = pg.blocos_presentes(doc)
    assert set(blocos) == {pg._titulo_norm(f"{pg.PREFIXO_BLOCO} {s}") for s in
                           ("as habilidades", "a pergunta do fim (Canal B)", "os tempos", "o podcast")}
    # cada bloco no fim da seção dele, antes da seção seguinte
    for secao, bloco, seguinte in (("O que a missão ensina", "as habilidades", "Como a gente sabe"),
                                   ("Como a gente sabe que a criança aprendeu", "a pergunta do fim", "Quanto tempo leva"),
                                   ("Quanto tempo leva e como dividir em aulas", "os tempos", "O podcast do fechamento"),
                                   ("O podcast do fechamento", "o podcast", "O que a missão NÃO faz")):
        i, j, k = (doc.index(f"## {secao}"), doc.index(f"### {pg.PREFIXO_BLOCO} {bloco}"), doc.index(f"## {seguinte}"))
        assert i < j < k, secao
    # o texto é o do contrato, por código: o texto oficial da BNCC, a pergunta e as alternativas do Canal B, a tabela
    # do §10 linha por linha e o que o §11 diz do episódio
    assert "**EF02CO01** — «Criar e comparar modelos (representações) de objetos" in doc
    assert "> Para mostrar em uma foto que duas crianças estão estudando juntas, o que é mais importante aparecer no " \
           "enquadramento?" in doc
    assert "1. «A ação das crianças lendo ou escrevendo juntas com o material.»" in doc
    assert "| **TOTAL GERAL DA MISSÃO** | **24 min** | **55 min** |" in doc and "**Total em tela:** 24 min." in doc
    assert "- **Duração total:** 3 minutos e 30 segundos." in doc
    # o roteiro da conversa entra quando o one-pager o tem (a exp02ef1b não tem textos-chave do §9; a exp06ef1b tem)
    outro = _estado("exp06ef1b-53e011b6")
    montado = pg.montar(outro["one_pager_pedagogico"], outro)
    assert f"### {pg.PREFIXO_BLOCO} o roteiro da conversa" in montado
    assert "«Quando vocês abriram o aplicativo, vocês sentiram que estavam vendo a feira inteira" in montado


def test_montagem_e_idempotente_e_guarda_o_envelope_e_o_anexo():
    estado = _estado()
    corpo = pg.montar(ca.remover_anexo(estado["one_pager_pedagogico"]), estado)
    assert pg.montar(corpo, estado) == corpo
    com_anexo = ca.com_anexo(corpo, estado["one_pager"], ca.SECOES_PEDAGOGICO)
    remontado = pg.montar(com_anexo, estado)
    assert remontado == com_anexo, "o anexo fica no fim, e nada muda"
    # o envelope do redator fica depois dos blocos, e o anexo depois dele
    assert remontado.index("### Do one-pager aprovado — o podcast") < remontado.index('"agente": "one-pager-pedagogico"') \
        < remontado.index(f"# {ca.TITULO_ANEXO}")
    # a narrativa é o que o redator escreveu: sem os blocos, sem o envelope, sem o anexo
    narrativa = pg.narrativa(remontado)
    assert pg.PREFIXO_BLOCO not in narrativa and ca.TITULO_ANEXO not in narrativa and '"agente"' not in narrativa
    assert "## O que a missão ensina" in narrativa


def test_secao_que_o_redator_nao_escreveu_e_criada_com_o_bloco():
    estado = _estado()
    sem = re.sub(r"## O podcast do fechamento.*?(?=\n## )", "", estado["one_pager_pedagogico"], flags=re.S)
    assert "## O podcast do fechamento" not in sem
    doc = pg.montar(sem, estado)
    assert "## O podcast do fechamento\n\n### Do one-pager aprovado — o podcast" in doc
    assert doc.index("## O podcast do fechamento") < doc.index('"agente": "one-pager-pedagogico"')
    assert pg.montar(doc, estado) == doc


def test_contrato_no_pedagogico_na_correcao_pontual_entra_como_troca():
    """Na correção pontual o redator não roda; o A120b sim, e o que ele muda (a sessão anterior ao PR 10 ganha os
    subtítulos) entra em `edicoes_pontuais`: o documento continua a versão anterior mais as trocas (A094)."""
    from agents.pedagogico import ContratoNoPedagogicoAgent
    from tools import edicao_pontual

    estado = _estado()
    antes = ca.remover_anexo(estado["one_pager_pedagogico"])
    final = _rodar_sync([ContratoNoPedagogicoAgent(name="A120b")],
                        {**estado, "one_pager_pedagogico": antes, "modo_correcao": "pontual", "edicoes_pontuais": []})
    depois = final["one_pager_pedagogico"]
    assert depois != antes and pg.blocos_presentes(depois)
    trocas = final["edicoes_pontuais"]
    assert trocas and all(t["motivo"] == pg.MOTIVO_TROCA for t in trocas)
    assert edicao_pontual.reaplicar(antes, depois, "one_pager_pedagogico", trocas)
    # fora da correção pontual, nenhuma troca é registrada
    # (a sessão do acervo guardou o modo da última correção dela, que foi pontual)
    final = _rodar_sync([ContratoNoPedagogicoAgent(name="A120b")],
                        {**estado, "one_pager_pedagogico": antes, "modo_correcao": ""})
    assert final.get("edicoes_pontuais") == estado.get("edicoes_pontuais")


def test_fechamento_do_design_monta_confere_anexa_e_grava_o_retrato():
    """O loop do pedagógico com um redator falso no lugar do A120 (e sem o juiz, que é modelo): a narrativa sai montada
    sobre o contrato, os gates aprovam, e o A124 cola o anexo e grava o retrato que o dev confere."""
    from agents.pedagogico import build_fechamento_pedagogico

    estado = _estado()
    narrativa = pg.narrativa(estado["one_pager_pedagogico"])
    loop, anexo = build_fechamento_pedagogico()
    loop.max_iterations = 1
    loop.sub_agents = [_Escreve(name="RedatorFalso", chave="one_pager_pedagogico", texto=narrativa)] + [
        a for a in loop.sub_agents[1:] if a.name in ("A120bContratoNoPedagogico", "A121ConteudoAprovadoPedagogico",
                                                     "A121bMontagemPedagogico")]
    for a in loop.sub_agents:
        a.parent_agent = None
    anexo.parent_agent = None
    # a geração (a sessão do acervo guardou o modo da última correção dela, pontual — em que o loop não roda sem documento)
    inicial = {**{k: v for k, v in estado.items() if k != "one_pager_pedagogico"}, "modo_correcao": ""}
    final = _rodar_sync([loop, anexo], inicial)
    doc = final["one_pager_pedagogico"]
    assert pg.blocos_presentes(doc) and ca.TITULO_ANEXO in doc
    assert final[pg.KEY_RETRATO] == doc
    assert final["montagem_pedagogico_status"] == "aprovado", final["montagem_pedagogico_report"]
    assert final["conteudo_aprovado_pedagogico_status"] == "aprovado", final["conteudo_aprovado_pedagogico_report"]


def test_correcao_pontual_sem_pedagogico_nao_roda_o_loop():
    from agents.pedagogico import PEDAGOGICO_PULADO_NA_CORRECAO, pular_pedagogico_sem_documento_na_correcao_pontual

    class _Ctx:
        def __init__(self, state):
            self.state = state

    pular = pular_pedagogico_sem_documento_na_correcao_pontual
    assert pular(_Ctx({"modo_correcao": "pontual"})).parts[0].text == PEDAGOGICO_PULADO_NA_CORRECAO
    assert pular(_Ctx({"modo_correcao": "pontual", "one_pager_pedagogico": "# Ped\n\ntexto"})) is None
    # o refazer de design gera o pedagógico das sessões anteriores ao PR 10 (exp02em1b, exp01em1b, exp03em1b)
    assert pular(_Ctx({})) is None
    from pipeline.artifacts import e_mensagem_de_pulo

    assert e_mensagem_de_pulo(PEDAGOGICO_PULADO_NA_CORRECAO)


# --------------------------------------------------------------------------- 3. o gate de montagem
def test_gate_aprova_o_montado_e_le_o_legado_com_tolerancia():
    for nome in ("exp02ef1b-4fd72a9a", "exp05ef1b", "exp06ef1b-53e011b6", "exp01ef1b"):
        r = pg.validar(_montado(nome))
        assert r["status"] == "aprovado", (nome, r["achados"])
    # o pedagógico gerado no dev, sem os subtítulos: o gate não cobra subtítulo de quem não tem nenhum
    legado = pg.validar(_estado("exp05ef1b"))
    assert legado["contagem"]["legado"] and not [a for a in legado["achados"] if a["codigo"].startswith("bloco-")]
    assert pg.validar({})["status"] == "aprovado"


def test_mutante_pedagogico_com_h1_25_em_vez_de_30():
    """A cadeia da exp02ef1b (D11): a H1 do §17 diz 30%, e os 25% eram proposta (PQ-01 `[PROPOSTA]`). No pedagógico, a
    H1 com 25% bloqueia — citada pelo número ou parafraseada."""
    estado = _montado()
    certo = "- A hipótese 1 (usabilidade motora) será observada: mais de 30% das duplas desistirem de ajustar a moldura."
    errado = certo.replace("30%", "25%")
    ok = pg.validar({**estado, "one_pager_pedagogico": _na_secao(estado["one_pager_pedagogico"],
                                                                 "O que ainda está em aberto", certo)})
    assert ok["status"] == "aprovado", ok["achados"]
    r = pg.validar({**estado, "one_pager_pedagogico": _na_secao(estado["one_pager_pedagogico"],
                                                                "O que ainda está em aberto", errado)})
    assert r["status"] == "bloqueado"
    assert {"hipotese-diverge", "numero-sem-origem"} <= {a["codigo"] for a in r["achados"]}
    assert all(a["etapa"] == "design" and a["agente_responsavel"] == pg.DONO for a in r["achados"])
    # parafraseada, sem dizer «hipótese 1»: os 25% só existem numa linha de proposta, e proposta não é origem
    parafrase = "Se mais de 25% das duplas desistirem de ajustar a moldura, a professora retoma o gesto com a turma."
    r = pg.validar({**estado, "one_pager_pedagogico": _na_secao(estado["one_pager_pedagogico"],
                                                                "Por que isso importa nesta idade", parafrase)})
    assert r["status"] == "bloqueado" and "numero-sem-origem" in {a["codigo"] for a in r["achados"]}

    # na esteira: o A121b reprova, e o loop devolve ao redator
    from agents.checkers import RastroCheckAgent

    gate = RastroCheckAgent(name="A121b", modo="montagem_pedagogico", rotulo="Pedagógico monta, não decide",
                            report_key="montagem_pedagogico_report", status_key="montagem_pedagogico_status",
                            estrito=False)
    final = _rodar_sync([gate], {**estado, "one_pager_pedagogico": _na_secao(
        estado["one_pager_pedagogico"], "O que ainda está em aberto", errado)})
    assert final["montagem_pedagogico_status"] == "bloqueado"
    assert "hipotese-diverge" in final["montagem_pedagogico_report"]


def test_mutante_texto_chave_reescrito_no_pedagogico():
    """A pergunta do Canal B (TC-02) reescrita na narrativa: quase igual, o código a devolve ao texto aprovado (A120b);
    mais distante, o gate bloqueia e devolve ao redator."""
    estado = _montado()
    perto = "Para mostrar em uma foto que duas crianças estão estudando juntas, o que é mais importante aparecer na foto?"
    longe = "Numa foto de duas crianças estudando juntas, o que mais importa aparecer no quadro?"
    aprovado = ("Para mostrar em uma foto que duas crianças estão estudando juntas, o que é mais importante aparecer no "
                "enquadramento?")
    doc = _na_secao(estado["one_pager_pedagogico"], "Como a gente sabe que a criança aprendeu",
                    f"No fim, a criança responde: «{perto}»")
    montado = pg.montar(doc, estado)
    assert f"«{perto}»" not in montado and f"responde: «{aprovado}»" in montado
    assert pg.validar({**estado, "one_pager_pedagogico": montado})["status"] == "aprovado"

    doc = _na_secao(estado["one_pager_pedagogico"], "Como a gente sabe que a criança aprendeu",
                    f"No fim, a criança responde: «{longe}»")
    montado = pg.montar(doc, estado)
    assert f"«{longe}»" in montado, "a reescrita distante não é trocada em silêncio"
    r = pg.validar({**estado, "one_pager_pedagogico": montado})
    assert r["status"] == "bloqueado" and "texto-chave-reescrito" in {a["codigo"] for a in r["achados"]}
    # o A121 sozinho não a via: o subtítulo da esteira traz o texto aprovado no mesmo corpo
    assert ca.validar_pedagogico(montado, estado["spec_missao"], estado["one_pager"])["status"] == "aprovado"


def test_mutante_subtitulo_da_esteira_mexido_ou_apagado():
    estado = _montado()
    doc = estado["one_pager_pedagogico"]
    mexido = doc.replace("**Total em tela:** 24 min.", "**Total em tela:** 20 min.")
    r = pg.validar({**estado, "one_pager_pedagogico": mexido})
    assert r["status"] == "bloqueado" and "bloco-do-contrato-alterado" in {a["codigo"] for a in r["achados"]}
    apagado = re.sub(r"### Do one-pager aprovado — o podcast.*?(?=\n## )", "", doc, flags=re.S)
    r = pg.validar({**estado, "one_pager_pedagogico": apagado})
    assert r["status"] == "bloqueado" and "bloco-do-contrato-ausente" in {a["codigo"] for a in r["achados"]}


def test_numero_do_preparo_nao_e_regra_da_missao():
    """«A página da missão com duas opções simples» é a tela de recorte da aula (E0-PROF, padrão da plataforma, D7)."""
    estado = _montado()
    assert "duas opções simples" in pg.narrativa(estado["one_pager_pedagogico"])
    assert pg.validar(estado)["status"] == "aprovado"
    # a mesma frase fora do preparo é contagem de opções da missão, sem origem
    doc = _na_secao(estado["one_pager_pedagogico"], "Em uma frase", "A criança escolhe entre duas opções simples.")
    r = pg.validar({**estado, "one_pager_pedagogico": doc})
    assert "numero-sem-origem" in {a["codigo"] for a in r["achados"]}


# --------------------------------------------------------------------------- 4. o dev só acrescenta
def _ate_o_fim_do_design(estado):
    """O A124 do design: o anexo e o retrato."""
    from agents.checkers import AnexoAprovadoAgent

    corpo = pg.montar(ca.remover_anexo(estado["one_pager_pedagogico"]), estado)
    return _rodar_sync([AnexoAprovadoAgent(name="A124", chave="one_pager_pedagogico", secoes=list(ca.SECOES_PEDAGOGICO),
                                           retrato_key=pg.KEY_RETRATO)], {**estado, "one_pager_pedagogico": corpo})


def test_dev_acrescenta_as_pendencias_numa_secao_propria():
    from agents.pedagogico import PedagogicoNoDevAgent
    from pipeline.passagem import assinatura_da_etapa

    estado = _ate_o_fim_do_design(_estado())
    assert estado[pg.KEY_RETRATO] == estado["one_pager_pedagogico"] and ca.TITULO_ANEXO in estado[pg.KEY_RETRATO]
    aprovado = estado["one_pager_pedagogico"]
    design_antes = assinatura_da_etapa(estado, "design")
    final = _rodar_sync([PedagogicoNoDevAgent(name="A119b")], estado)
    assert final["pedagogico_dev_status"] == "aprovado"
    assert final["one_pager_pedagogico"] == aprovado, "o texto aprovado no de acordo de design não muda"
    assert assinatura_da_etapa(final, "design") == design_antes, "nem a assinatura do design"
    secao = final[pg.KEY_SECAO_DEV]
    assert f"# {pg.TITULO_SECAO_DEV}" in secao and "`DAD-10` · dono `handoff-dev`" in secao
    assert "## Rastro de lacunas do dev — 🟡 1 pendência(s)" in secao and "`externo` · dono `externo`" in secao
    completo = pg.completo(final)
    assert completo.startswith(aprovado.rstrip("\n")) and completo.rstrip().endswith(secao.rstrip())
    assert completo.index(ca.TITULO_ANEXO) < completo.index(pg.TITULO_SECAO_DEV)


def test_mutante_dev_reescreve_o_pedagogico_aprovado_e_barrado():
    """Mutante «o dev reescreve o pedagógico aprovado»: um agente do dev grava o documento. O A119b o devolve ao retrato
    do design e fica 🔴, com a degradação registrada (ESTEIRA_ESTRITA)."""
    from agents.pedagogico import ROTULO_NO_DEV, PedagogicoNoDevAgent

    estado = _ate_o_fim_do_design(_estado())
    aprovado = estado["one_pager_pedagogico"]
    reescrito = aprovado.replace("Toda imagem tem um autor", "Toda imagem tem um dono")
    final = _rodar_sync([_Escreve(name="MutanteDoDev", chave="one_pager_pedagogico", texto=reescrito),
                         PedagogicoNoDevAgent(name="A119b", estrito=True)], estado)
    assert final["one_pager_pedagogico"] == aprovado
    assert final["pedagogico_dev_status"] == "bloqueado"
    assert "pedagogico-reescrito-no-dev" in final["pedagogico_dev_report"]
    assert final.get("pipeline_bloqueado") and any(d["gate"] == ROTULO_NO_DEV for d in final["degradacoes"])
    # apagado também volta
    final = _rodar_sync([_Escreve(name="MutanteDoDev", chave="one_pager_pedagogico", texto=""),
                         PedagogicoNoDevAgent(name="A119b", estrito=True)], estado)
    assert final["one_pager_pedagogico"] == aprovado and final["pedagogico_dev_status"] == "bloqueado"


def test_mutante_editor_do_dev_que_volta_a_editar_o_pedagogico_e_barrado(monkeypatch):
    """Mutante: o pedagógico de volta à lista de documentos do editor de dev (como era até o PR 10). A troca dele entra no
    estado da correção pontual de dev, e o A119b a barra; sem o mutante, ela nem entra."""
    from agents.pedagogico import PedagogicoNoDevAgent
    from pipeline.reexecucao import preparar_estado_pontual
    from tools import edicao_pontual

    assert "one_pager_pedagogico" not in edicao_pontual.DOCUMENTOS_POR_ETAPA["dev"]
    assert "one_pager_pedagogico" in edicao_pontual.DOCUMENTOS_POR_ETAPA["design"]
    estado = _ate_o_fim_do_design(_estado())
    aprovado = estado["one_pager_pedagogico"]
    editado = {"one_pager_pedagogico": "# Outro pedagógico\n", "prd_final": estado["prd_final"]}
    limpo, _ = preparar_estado_pontual(estado, "dev", "pedido", editado, [])
    assert limpo["one_pager_pedagogico"] == aprovado

    monkeypatch.setitem(edicao_pontual.DOCUMENTOS_POR_ETAPA, "dev",
                        edicao_pontual.DOCUMENTOS_POR_ETAPA["dev"] + ("one_pager_pedagogico",))
    limpo, _ = preparar_estado_pontual(estado, "dev", "pedido", editado, [])
    assert limpo["one_pager_pedagogico"] == "# Outro pedagógico\n"
    final = _rodar_sync([PedagogicoNoDevAgent(name="A119b", estrito=True)], limpo)
    assert final["one_pager_pedagogico"] == aprovado and final["pedagogico_dev_status"] == "bloqueado"


def test_refazer_so_dev_nao_apaga_nem_regera_o_pedagogico():
    from pipeline.reexecucao import CHAVES_DESIGN, CHAVES_DEV, CHAVES_PRODUTO, preparar_estado

    for chave in ("one_pager_pedagogico", pg.KEY_RETRATO, "montagem_pedagogico_status", "coerencia_pedagogico_status",
                  "conteudo_aprovado_pedagogico_status"):
        assert chave in CHAVES_DESIGN and chave not in CHAVES_DEV, chave
    assert pg.KEY_SECAO_DEV in CHAVES_DEV and "pedagogico_dev_status" in CHAVES_DEV
    estado = _ate_o_fim_do_design(_estado())
    limpo, removidas = preparar_estado({**estado, pg.KEY_SECAO_DEV: "x"}, "dev")
    assert limpo["one_pager_pedagogico"] == estado["one_pager_pedagogico"]
    assert limpo[pg.KEY_RETRATO] == estado[pg.KEY_RETRATO] and "anterior_one_pager_pedagogico" not in limpo
    assert pg.KEY_SECAO_DEV in removidas
    # a sessão anterior ao PR 10 (pedagógico gerado no dev, sem retrato): o pedagógico que ela tem passa a ser o retrato
    legado = _estado()
    assert pg.KEY_RETRATO not in legado
    limpo, _ = preparar_estado(legado, "dev")
    assert limpo[pg.KEY_RETRATO] == legado["one_pager_pedagogico"] == limpo["one_pager_pedagogico"]
    # refazer design (e produto) o regera, sobre a versão anterior sem o anexo da esteira
    for etapa in ("design", "produto"):
        limpo, _ = preparar_estado(estado, etapa)
        assert "one_pager_pedagogico" not in limpo and pg.KEY_RETRATO not in limpo
        assert ca.TITULO_ANEXO not in limpo["anterior_one_pager_pedagogico"]
    assert "one_pager_pedagogico" in CHAVES_PRODUTO


def test_sessao_sem_pedagogico_no_dev_fica_amarela():
    """A missão desenhada antes do PR 10 que vai ao dev sem refazer o design: o dev não gera o pedagógico."""
    r = pg.no_dev({"dev_status": "amarelo", "dev_status_envelope": {"achados": []}})
    assert r["status"] == "amarelo" and r["achados"][0]["codigo"] == "pedagogico-ausente" and r["restaurar"] is None


# --------------------------------------------------------------------------- 5. arquivos, cartão e conversa
def test_pedagogico_na_pasta_de_design_com_a_secao_do_dev_e_sem_o_da_raiz(tmp_path):
    from pipeline.artifacts import ONE_PAGERS_COM_MARCA, save_run_artifacts
    from pipeline.reexecucao import arquivos_das_chaves

    estado = _ate_o_fim_do_design(_estado())
    estado[pg.KEY_SECAO_DEV] = pg.secao_do_dev(estado)
    (tmp_path / "one-pager-pedagogico.md").write_text("antigo", encoding="utf-8")
    (tmp_path / "one-pager-pedagogico.docx").write_bytes(b"antigo")
    save_run_artifacts(estado, "s", run_dir=tmp_path)
    md = (tmp_path / "design" / "14-one-pager-pedagogico.md").read_text(encoding="utf-8")
    assert md.rstrip().endswith(estado[pg.KEY_SECAO_DEV].rstrip())
    assert (tmp_path / "design" / "14-one-pager-pedagogico.docx").exists()
    assert not (tmp_path / "one-pager-pedagogico.md").exists() and not (tmp_path / "one-pager-pedagogico.docx").exists()
    assert (tmp_path / "design" / "14b-montagem-pedagogico.md").exists() is False  # sem relatório no estado, sem arquivo
    assert ("one_pager_pedagogico", "design/14-one-pager-pedagogico", "One-pager pedagógico",
            "Para leitura e aprovação do time pedagógico") in ONE_PAGERS_COM_MARCA
    # o backup de uma reexecução leva junto o arquivo de antes da mudança de pasta
    caminhos = arquivos_das_chaves(["one_pager_pedagogico"])
    assert "design/14-one-pager-pedagogico.md" in caminhos and "one-pager-pedagogico.md" in caminhos


def test_de_acordo_de_design_e_dado_sobre_o_pedagogico():
    from pipeline import passagem

    estado = _ate_o_fim_do_design(_estado())
    doc = passagem.documento_a_aprovar(estado, "design")
    assert doc["existe"] and doc["texto"] == estado["one_pager_pedagogico"]
    assert doc["docx"] == "design/14-one-pager-pedagogico.docx"
    rotulos = {l["rotulo"]: l["alvo"] for l in doc["links"]}
    assert rotulos["Protótipo navegável"] == "design/08-prototipo.html"
    assert rotulos["Board no Miro"].startswith("https://miro.com/app/board/uXjVEW48Kqo=")
    assert passagem.documento_a_aprovar(estado, "produto") is None
    assert passagem.documento_a_aprovar(estado, "dev") is None
    # a missão desenhada antes do PR 10: o cartão avisa e o de acordo segue valendo sobre os documentos de design
    sem = passagem.documento_a_aprovar(_estado("exp02em1b-60cfa7f4"), "design")
    assert not sem["existe"] and "Refazer" in sem["aviso"]
    # os gates do pedagógico estão no semáforo de design, e o guarda do dev no de dev
    assert {"montagem_pedagogico_status", "coerencia_pedagogico_status", "conteudo_aprovado_pedagogico_status"} \
        <= passagem.chaves_da_etapa("design")
    assert "pedagogico_dev_status" in passagem.chaves_da_etapa("dev")


def test_conversa_e_dossie_tratam_o_pedagogico_como_de_design():
    from pipeline import conversa_etapas
    from pipeline.reexecucao import ROTULOS_GATE_POR_ETAPA
    from tools import diagnostico, rastreabilidade

    assert conversa_etapas.PRIORIDADE["design"][0] == "one_pager_pedagogico"
    assert "one_pager_pedagogico" not in conversa_etapas.PRIORIDADE["dev"]
    assert pg.KEY_RETRATO in conversa_etapas.FORA_DO_CONTEXTO
    estado = _ate_o_fim_do_design(_estado())
    assert "one_pager_pedagogico" in conversa_etapas.documentos_da_etapa(estado, "design")
    assert pg.KEY_RETRATO not in conversa_etapas.documentos_da_etapa(estado, "design")
    etapas = {g["status"]: g["etapa"] for g in diagnostico.GATES}
    assert etapas["montagem_pedagogico_status"] == etapas["coerencia_pedagogico_status"] == "design"
    assert etapas["pedagogico_dev_status"] == "dev"
    for rotulo in ("Pedagógico monta, não decide", "Pedagógico × one-pager aprovado",
                   "Coerência do pedagógico com o one-pager aprovado"):
        assert ROTULOS_GATE_POR_ETAPA[rotulo] == "design", rotulo
    assert ROTULOS_GATE_POR_ETAPA["Pedagógico aprovado, no dev"] == "dev"
    sem_canal_b = {**estado, "one_pager_pedagogico": "# Ped\n\nnada\n"}
    achados = [a for a in rastreabilidade.matriz(sem_canal_b)["achados"] if a["codigo"].endswith("-pedagogico")]
    assert achados and all(a["etapa"] == "design" for a in achados)
    assert all(a["etapa"] == "design" for a in ca.validar_pedagogico("# Ped\n", estado["spec_missao"],
                                                                      estado["one_pager"])["achados"])


def test_fidelidade_do_design_confere_o_pedagogico_e_a_do_dev_nao():
    from agents.design import FIDELIDADE_DOCUMENTOS_DESIGN
    from agents.dev import FIDELIDADE_DOCUMENTOS_DEV

    assert "one_pager_pedagogico" in FIDELIDADE_DOCUMENTOS_DESIGN
    assert "one_pager_pedagogico" not in FIDELIDADE_DOCUMENTOS_DEV


# --------------------------------------------------------------------------- 6. o pedido do PO sobre o pedagógico
def test_pedido_sobre_o_pedagogico_feito_no_dev_vai_ao_design_e_o_de_produto_a_produto():
    from tools.triagem_pedido import DESIGN, DEV, PRODUTO, dividir

    estado = _estado()
    pedido = ("1. No pedagógico, a seção «Por que isso importa nesta idade» deve falar mais da roda de conversa.\n"
              "2. No PRD, o nome da tabela de sessões tem de seguir o prefixo da missão.\n"
              "3. No pedagógico, tire a habilidade EF02CO05 do que a missão ensina.\n")
    d = dividir(pedido, "dev", estado, [{"n": 1, "dono": "dev"}, {"n": 2, "dono": "dev"}, {"n": 3, "dono": "dev"}])
    assert [i.dono for i in d.itens] == [DESIGN, DEV, PRODUTO]
    assert "pedagógico" in d.itens[0].motivo_triagem
    # «o time pedagógico» não é o documento
    d = dividir("O time pedagógico pediu que o PRD cite a tabela certa.", "dev", estado, [{"n": 1, "dono": "dev"}])
    assert d.itens[0].dono == DEV
    # pedido feito ao design: o item do pedagógico é do design — e o texto-alvo que está em produto vai a produto
    d = dividir("No pedagógico, a parte da sala precisa dizer que a turma usa tablets.", "design", estado,
                [{"n": 1, "dono": "design"}])
    assert d.itens[0].dono == DESIGN
    d = dividir("No pedagógico, a seção «Em uma frase» fica curta demais.", "design", estado, [{"n": 1, "dono": "design"}])
    assert d.itens[0].dono == PRODUTO and "one-pager resumido" in d.itens[0].regra[0]
