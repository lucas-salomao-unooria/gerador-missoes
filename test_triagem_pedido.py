"""Pedido do PO feito em design ou dev: triagem item a item e rota de código para produto (plano «Produto dono do
contrato», PR 5, D4).

Os casos vêm do acervo (`tests/acervo/`): o pedido de 23/10/2026 13:24 da exp02ef1b-4fd72a9a (textos de tela por tela,
as opções da 5A e o botão «Publicar no Álbum», que está quatro vezes na spec do Gate 0) e o de 23/10/2026 17:08 da
exp02em1b-60cfa7f4 (Central de Apoio, overlay do CTA, botão de configuração e a régua da habilidade 24). A triagem do LLM
e o editor pontual são simulados; o resto é o código da esteira.
"""
import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.runners import InMemoryRunner
from google.genai import types

from pipeline import passagem
from tools import edicao_pontual as ed
from tools import linha_de_base as lb
from tools import triagem_pedido as tp
from tools.auth import Sessao

ACERVO = Path(__file__).parent / "tests" / "acervo"


def _estado(missao):
    return json.loads((ACERVO / missao / "estado.json").read_text(encoding="utf-8"))


def _pedido(estado, quando):
    return next(p["texto"] for p in estado["pedidos_do_po"] if quando in p["origem"])


def _triagem_simulada(divisao_por_n, motivo="o PO pediu no parecer de design"):
    """O envelope que o A000TriagemCorrecao devolve, com um dono por item."""
    itens = [{"n": n, "dono": dono, "motivo": motivo} for n, dono in divisao_por_n.items()]
    return SimpleNamespace(etapa="design", motivo="triagem simulada", itens=itens)


# ------------------------------------------------------------------ divisão do pedido (sem LLM)
def test_pedido_por_tela_da_exp02ef1b_manda_a_produto_o_que_esta_na_spec_e_deixa_a_microcopy_no_design():
    estado = _estado("exp02ef1b-4fd72a9a")
    pedido = _pedido(estado, "23/10/2026 13:24")
    contexto, itens = tp.itens_do_pedido(pedido)
    assert [t for t, _ in itens] == ["E3-ALU-01 — Moldura pequena", "E4-ALU-01 — Resposta da visitante",
                                     "E4-ALU-02 — Comparação", "E5-ALU-01 — Formar pares",
                                     "E5-ALU-01 — Motivo do par", "E5-ALU-02 — Segunda foto"]
    # o «Resumo geral» só repete os itens e pede para manter as interações: é contexto, não item
    assert "Resumo geral dos ajustes" in contexto and "Segue a transcrição" in contexto

    # a triagem do LLM diz «design» para tudo — foi pedido ao design —, e a regra conservadora corrige o que é produto
    triagem = _triagem_simulada({n: "design" for n in range(1, 7)})
    d = tp.dividir(pedido, "design", estado, triagem.itens)
    donos = {i.titulo: i.dono for i in d.itens}
    assert donos["E5-ALU-02 — Segunda foto"] == tp.PRODUTO  # «Publicar no Álbum» está na spec do Gate 0
    assert donos["E5-ALU-01 — Motivo do par"] == tp.PRODUTO  # as opções da 5A (o instrumento de 3 para 2 opções)
    regra_5b = next(i for i in d.itens if i.n == 6).regra
    assert any("Publicar no Álbum" in r and "spec do Gate 0 (4)" in r for r in regra_5b), regra_5b
    assert any("opções" in r for r in next(i for i in d.itens if i.n == 5).regra)
    # pura microcopy escrita pelo design: 0 ocorrência em núcleo, one-pager e spec — fica no design. A moldura cita
    # «10%» e diz que a porcentagem «é uma regra do sistema»: não muda número nem regra
    for titulo in ("E3-ALU-01 — Moldura pequena", "E4-ALU-01 — Resposta da visitante", "E4-ALU-02 — Comparação",
                   "E5-ALU-01 — Formar pares"):
        assert donos[titulo] == tp.DESIGN, (titulo, next(i.regra for i in d.itens if i.titulo == titulo))
    # o texto de produto leva só os itens de produto, sem o contexto (o «Resumo geral» deu 🔴 de preservação)
    texto_produto = d.texto_de(tp.PRODUTO)
    assert "Publicar no Álbum" in texto_produto and "Aumente a moldura" not in texto_produto
    assert "Resumo geral" not in texto_produto
    assert "Resumo geral" in d.texto_de(tp.DESIGN, com_contexto=True)


def test_tela_com_titulo_de_introducao_ou_resumo_e_item_e_nao_contexto():
    """Revisão do PR 5 (24/10): a palavra «introdução» ou «resumo» em qualquer lugar do título tirava a seção da divisão;
    a tela «E1-ALU-01 — Introdução» com «Publicar no Álbum» (4 vezes na spec do Gate 0) ia inteira só ao design."""
    estado = _estado("exp02ef1b-4fd72a9a")
    pedido = ("## E1-ALU-01 — Introdução\nTrocar “Publicar no Álbum” por “Colocar no álbum”.\n\n"
              "## E2-ALU-01 — Galeria\nTrocar o título por “Sua galeria”.\n\n"
              "## Resumo geral dos ajustes\nManter as interações.")
    d = tp.dividir(pedido, "design", estado, [{"n": 1, "dono": "design"}, {"n": 2, "dono": "design"}])
    assert [(i.titulo, i.dono) for i in d.itens] == [("E1-ALU-01 — Introdução", tp.PRODUTO),
                                                     ("E2-ALU-01 — Galeria", tp.DESIGN)]
    assert "Publicar no Álbum" in d.texto_de(tp.PRODUTO)
    assert d.contexto == "## Resumo geral dos ajustes\nManter as interações."


@pytest.mark.parametrize("titulo, contexto", [
    ("Resumo geral dos ajustes", True), ("Contexto", True), ("Contexto do pedido:", True), ("**Visão geral**", True),
    ("Observações gerais", True), ("Introdução", True),
    # título ambíguo é item: o lado conservador
    ("E1-ALU-01 — Introdução", False), ("E0-PROF-05 — Card de resumo", False), ("Contexto da cena", False),
    ("Resumo da etapa 3", False), ("Introdução da 5A", False),
])
def test_titulo_de_contexto(titulo, contexto):
    assert tp._titulo_de_contexto(titulo) is contexto


def test_sem_a_triagem_do_llm_o_que_a_regra_nao_pega_fica_sem_dono():
    estado = _estado("exp02ef1b-4fd72a9a")
    d = tp.dividir(_pedido(estado, "23/10/2026 13:24"), "design", estado, None)
    assert [i.n for i in d.de(tp.PRODUTO)] == [5, 6]
    assert [i.n for i in d.indefinidos] == [1, 2, 3, 4]


def test_pedido_em_lista_da_exp02em1b_vai_todo_a_produto():
    """17:08: o PO repetiu em design o que tinha pedido a produto às 11:01 — Central de Apoio, overlay do CTA, o botão de
    configuração e a régua ternária da habilidade 24 com o motivo ao fixar aviso. Os quatro estão no one-pager."""
    estado = _estado("exp02em1b-60cfa7f4")
    pedido = _pedido(estado, "23/10/2026 17:08")
    _, itens = tp.itens_do_pedido(pedido)
    # os «•» dentro da citação aberta com ” são a fala do aluno, e os que seguem «Encaminhar para» são as opções dela
    assert len(itens) == 4, [c for c, _ in itens]
    assert itens[0][0].startswith("central de apoio") and itens[3][0].startswith("habilidade 24")
    d = tp.dividir(pedido, "design", estado, _triagem_simulada({1: "design", 2: "design", 3: "design", 4: "produto"}).itens)
    assert [i.dono for i in d.itens] == [tp.PRODUTO] * 4
    regras = {i.n: " | ".join(i.regra) for i in d.itens}
    assert "Encaminhar relato" in regras[1]
    assert "moderador do perfil" in regras[2]
    assert "metricas publicacao" in regras[3]  # citado sem acento e sem «da»: as palavras na mesma linha do one-pager
    assert "fixar aviso" in regras[4] and "forma de avaliacao" in regras[4]


@pytest.mark.parametrize("pedido, de_produto", [
    # mutante «opção Lugar removida» (plano, «Como medir cada PR»)
    ("Na 5A, tirar a opção “Lugar” das justificativas.", True),
    ("Na 5A, deixar só 2 opções.", True),
    ("Aumentar o tempo da etapa 3 de 7 min para 9 min.", True),
    ("Mudar a pergunta do Canal B.", True),
    ("Trocar o podcast do professor.", True),
    ("Mudar a forma de avaliação da EF02CO01.", True),
    # formas de pedir sem verbo de troca (revisão do PR 5, 24/10), entre elas o corte do D11
    ("O tempo da etapa 3 deve ser 9 minutos.", True),
    ("Quero 2 opções na 5A em vez de 3.", True),
    ("A 5A deve ter só duas opções.", True),
    ("Usar 30% na H1.", True),
    ("Na H1, o corte é 30%, não 25%.", True),
    ("Teto de 20 palavras no Canal A.", True),
    ("Remover a fase 2 do mini-jogo.", True),
    ("O feedback deve aparecer só depois da segunda tentativa.", True),
    # «criança» e «alternativa» não são verbo de mudança; cartas na tela não são contrato
    ("Mostrar a criança as alternativas maiores.", False),
    ("A criança precisa ver 3 cartas na tela.", False),
    # «usar» conta para número e opções, não para «estado» (exp06ef1b, 09/10 12:11: pedido de dev)
    ("No fluxo, usar os nomes de estado da spec para os modos de falha.", False),
    ("Na etapa 3, trocar a cor do botão para verde.", False),
    # palavra solta citada casa com qualquer texto; botão maior é UI
    ("Trocar o texto do botão “Pronto” por “Seguir”.", False),
    ("Deixar o botão maior e com mais contraste.", False),
    # ordem de não mexer não muda nada (exp06ef1b, 09/10 12:11)
    ("Não alterar telas, mecânica nem os demais textos aprovados.", False),
    ("A moldura precisa de indicação visual nas alças. A porcentagem é uma regra do sistema.", False),
])
def test_regra_conservadora(pedido, de_produto):
    docs = tp.documentos_de_produto(_estado("exp02ef1b-4fd72a9a"))
    assert bool(tp.regra_de_produto(pedido, docs)) is de_produto, tp.regra_de_produto(pedido, docs)


def test_texto_alvo_e_procurado_numa_linha_so():
    """«Brincar 2» casava com «brincar» no fim de uma linha e «2.» no começo da seguinte."""
    docs = {"one_pager": "Crianças podem brincar\n2. Etapa seguinte", "nucleo_narrativo": "", "one_pager_resumido": "",
            "spec_missao_gate0": ""}
    assert tp.regra_de_produto("Nas cartas, sem rótulos como “Brincar 2”.", docs) == []
    docs["one_pager"] = "Rótulo da carta: Brincar 2"
    assert tp.regra_de_produto("Nas cartas, sem rótulos como “Brincar 2”.", docs)


def test_escolha_do_po_so_tira_de_produto_o_que_a_regra_nao_pos_la():
    estado = _estado("exp02ef1b-4fd72a9a")
    d = tp.dividir(_pedido(estado, "23/10/2026 13:24"), "design", estado,
                   _triagem_simulada({1: "produto", 2: "design", 3: "indefinido", 4: "design", 5: "design", 6: "design"}).itens)
    assert [i.dono for i in d.itens] == ["produto", "design", "indefinido", "design", "produto", "produto"]
    final = tp.com_escolhas_do_po(d, {1: False, 3: True, 6: False})
    assert [i.dono for i in final.itens] == ["design", "design", "produto", "design", "produto", "produto"]
    assert final.itens[0].pelo_po and final.itens[2].pelo_po and not final.itens[5].pelo_po
    # o indefinido deixado sem marcar continua sem dono: a esteira não escolhe por ele
    assert tp.com_escolhas_do_po(d, {3: False}).indefinidos
    ida_e_volta = tp.Divisao.de_dict(final.como_dict())
    assert [i.dono for i in ida_e_volta.itens] == [i.dono for i in final.itens] and ida_e_volta.contexto == d.contexto


def test_triagem_le_o_dono_de_cada_item():
    from pipeline.reexecucao import Triagem

    t = Triagem.de_texto('ok\n```json\n{"agente": "triagem-correcao", "etapa": "design", "motivo": "telas", '
                         '"itens": [{"n": 1, "dono": "produto", "motivo": "botão da spec"}, {"n": 2, "dono": "design"}]}\n```')
    assert t.etapa == "design" and [i["dono"] for i in t.itens] == ["produto", "design"]
    prompt = (Path(__file__).parent / "prompts" / "transversal" / "triagem_correcao.md").read_text(encoding="utf-8")
    assert "{itens_do_pedido?}" in prompt and '"itens"' in prompt and "indefinido" in prompt
    assert tp.numerados("Só um parágrafo.") == "### Item 1\n\nSó um parágrafo."


# ------------------------------------------------------------------ parecer: Refazer com a divisão
def _sessao(papel):
    return Sessao(usuario=papel, papel=papel, emitida_em=0, expira_em=1e12, jti="x")


PEDIDO = ("### E5-ALU-02 — Segunda foto\n\nBotão: “Publicar no Álbum” → “Colocar no álbum”.\n\n"
          "### E4-ALU-02 — Comparação\n\nTexto atual: “Toque no pátio inteiro!” Ajuste solicitado: “Marque no pátio.”\n")
ESTADO_ITENS = {"one_pager": "Etapa 5B: o aluno toca em **Publicar no Álbum**.",
                "spec_missao_gate0": "- Botão `Publicar no Álbum` confirma a segunda foto.",
                "nucleo_narrativo": "", "one_pager_resumido": "", "design_status": "aprovado"}


def _divisao(donos=None):
    return tp.dividir(PEDIDO, "design", ESTADO_ITENS, [{"n": 1, "dono": "design"},
                                                       {"n": 2, "dono": (donos or {}).get(2, "design")}])


def test_refazer_de_design_com_item_sem_dono_e_recusado_e_pede_devolver():
    fluxo = {**passagem.novo_fluxo(), "etapa": "design", "situacao": passagem.AGUARDANDO}
    d = _divisao({2: "indefinido"})
    with pytest.raises(passagem.DecisaoInvalida, match="Devolver"):
        passagem.aplicar(fluxo, passagem.REFAZER, _sessao("design"), PEDIDO, ESTADO_ITENS, divisao=d.como_dict())


def test_refazer_de_design_leva_a_divisao_e_o_pedido_de_produto_vale_em_produto():
    fluxo = {**passagem.novo_fluxo(), "etapa": "design", "situacao": passagem.AGUARDANDO}
    d = _divisao()
    assert [i.dono for i in d.itens] == [tp.PRODUTO, tp.DESIGN]
    novo, efeito = passagem.aplicar(fluxo, passagem.REFAZER, _sessao("design"), PEDIDO, ESTADO_ITENS,
                                    divisao=d.como_dict())
    assert efeito.tipo == "refazer" and efeito.divisao["itens"][0]["dono"] == tp.PRODUTO
    assert novo["pareceres"][-1]["divisao"] == d.como_dict()
    pedidos = passagem.pedidos_do_po(novo)
    assert [(p["etapa"], p.get("a_montante_de")) for p in pedidos] == [("produto", "design"), ("design", None)]
    assert "Publicar no Álbum" in pedidos[0]["texto"] and "Toque no pátio" not in pedidos[0]["texto"]
    assert "Toque no pátio" in pedidos[1]["texto"] and "Publicar no Álbum" not in pedidos[1]["texto"]
    notas = passagem.notas_de_passagem(novo)
    assert "itens de produto (triagem)" in notas and "já foi aplicado no one-pager" in notas
    # sem divisão (chamador antigo), o pedido segue inteiro, como antes
    _, sem = passagem.aplicar(fluxo, passagem.REFAZER, _sessao("design"), PEDIDO, ESTADO_ITENS)
    assert sem.divisao is None


def test_pedido_todo_da_etapa_continua_um_pedido_so():
    fluxo = {**passagem.novo_fluxo(), "etapa": "design", "situacao": passagem.AGUARDANDO}
    d = tp.dividir("Trocar a cor do botão de confirmar para verde e aumentar o ícone da lupa.", "design",
                   ESTADO_ITENS, [{"n": 1, "dono": "design"}])
    novo, efeito = passagem.aplicar(fluxo, passagem.REFAZER, _sessao("design"), "Trocar a cor do botão de confirmar "
                                    "para verde e aumentar o ícone da lupa.", ESTADO_ITENS, divisao=d.como_dict())
    assert [p["etapa"] for p in passagem.pedidos_do_po(novo)] == ["design"]
    from pipeline.reexecucao import precisa_de_cascata

    assert not precisa_de_cascata(efeito.divisao)
    assert precisa_de_cascata(_divisao().como_dict())


# ------------------------------------------------------------------ ticket de produto vira devolução real
def test_ticket_do_qa_para_gate_estrutural_devolve_a_missao_a_produto():
    fluxo = {**passagem.novo_fluxo(), "etapa": "design", "situacao": passagem.GERANDO,
             "pareceres": [{"etapa": "produto", "acao": passagem.DE_ACORDO, "valido": True, "comentario": "ok"}]}
    estado = {"devolucoes_a_produto": {"Retrabalho de design": [
        {"id": "QA-3", "codigo": "mecanica-sem-gatilho", "resumo": "A 5A não diz o que destrava a 5B."}]}}
    novo = passagem.concluir_execucao(fluxo, True, estado)
    assert (novo["etapa"], novo["situacao"]) == ("produto", passagem.DEVOLVIDA)
    devolucao = novo["pareceres"][-1]
    assert devolucao["acao"] == passagem.DEVOLVER and devolucao["automatica"] and devolucao["autor"] == "esteira"
    assert "QA-3" in devolucao["comentario"] and "gate-estrutural" in devolucao["comentario"]
    assert novo["pareceres"][0]["valido"] is False  # o de acordo de produto deixa de valer, como numa devolução
    assert passagem.ultima_devolutiva(novo, "produto") is devolucao
    # sem ticket, ou com a etapa falhando, a missão volta ao dono da etapa como antes
    assert passagem.concluir_execucao(fluxo, True, {})["situacao"] == passagem.AGUARDANDO
    assert passagem.concluir_execucao(fluxo, False, estado)["situacao"] == passagem.FALHOU


async def _rodar(root, estado):
    runner = InMemoryRunner(agent=root, app_name="teste")
    await runner.session_service.create_session(app_name="teste", user_id="u", session_id="s", state=estado)
    async for _ in runner.run_async(user_id="u", session_id="s",
                                    new_message=types.Content(role="user", parts=[types.Part(text="go")])):
        pass
    final = await runner.session_service.get_session(app_name="teste", user_id="u", session_id="s")
    return dict(final.state)


def test_despacho_grava_o_ticket_de_produto_e_a_aprovacao_o_derruba():
    from agents.checkers import KEY_DEVOLUCOES_A_PRODUTO, DespachoTicketsAgent

    envelope = {"status": "bloqueado", "achados": [
        {"id": "QA-1", "severidade": "bloqueio", "codigo": "regra-ausente", "agente_responsavel": "gate-estrutural",
         "resumo": "A spec não diz quantas fotos a 5A tem."}]}

    def despacho():
        return DespachoTicketsAgent(name="D", rotulo="Retrabalho de design", report_key="qa",
                                    externos=["gate-estrutural"], mapa={})

    final = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[despacho()]),
                               {"qa": "```json\n" + json.dumps(envelope) + "\n```"}))
    assert final[KEY_DEVOLUCOES_A_PRODUTO]["Retrabalho de design"][0]["id"] == "QA-1"
    aprovado = {"status": "aprovado", "achados": []}
    final = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[despacho()]),
                               {**final, "qa": "```json\n" + json.dumps(aprovado) + "\n```"}))
    assert final[KEY_DEVOLUCOES_A_PRODUTO] == {}


# ------------------------------------------------------------------ fidelidade: só os itens da etapa
def test_a094_confere_so_os_itens_de_design_e_aceita_aplicado_a_montante():
    from agents.checkers import FidelidadeCheckAgent

    d = _divisao()

    def agente():
        return FidelidadeCheckAgent(name="A094", status_key="fid_status", report_key="fid_report",
                                    documentos=["copy_strings_revisada"], etapas_pedido=["design"], com_briefing=False,
                                    etapa="design", incluir_corrente=False)
    from pipeline.reexecucao import PedidoCorrecao

    estado = {"copy_strings_revisada": "Marque no pátio.", "etapa_da_correcao": "design",
              "pedido_correcao": PedidoCorrecao(texto=PEDIDO).como_markdown("design"),
              "divisao_do_pedido": d.como_dict()}
    final = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[agente()]), estado))
    relatorio = final["fid_report"]
    assert "aplicado a montante" in relatorio and "E5-ALU-02" in relatorio
    # o item de produto não entra no checklist do design: «Colocar no álbum» não é cobrado na copy
    assert "Colocar no álbum" not in relatorio.split("## Conferido")[0]
    # o registrado no parecer (pedidos_do_po dividido) também: o de produto aparece uma vez, como aplicado a montante
    fluxo = {**passagem.novo_fluxo(), "etapa": "design", "situacao": passagem.AGUARDANDO}
    novo, _ = passagem.aplicar(fluxo, passagem.REFAZER, _sessao("design"), PEDIDO, ESTADO_ITENS, divisao=d.como_dict())
    final = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[agente()]),
                               {**estado, "pedidos_do_po": passagem.pedidos_do_po(novo)}))
    assert final["fid_report"].count("aplicado a montante — item de produto") == 1


# ------------------------------------------------------------------ montagem da spec no design
def test_d0_com_a_spec_de_antes_da_cascata_nao_vira_aberto_do_po():
    from agents.checkers import montar_sobre_aceita

    aceita = ("# Spec\n\n## 2. Mecânica\n- Botão `Colocar no álbum` confirma a segunda foto.\n- Outra linha.\n\n"
              "## 13. Decisões D0\n| `[D0-1]` | x |\n")
    velha = aceita.replace("`Colocar no álbum`", "`Publicar no Álbum`")
    montante = [{"documento": "spec_missao", "de": "Botão `Publicar no Álbum` confirma",
                 "para": "Botão `Colocar no álbum` confirma"}]
    avisos = []
    montada = montar_sobre_aceita(aceita, velha, r"^## 13", avisos=avisos, autor="D0",
                                  estado={"edicoes_a_montante": montante}, estrito=True)
    assert "`Colocar no álbum`" in montada
    assert [a["codigo"] for a in avisos] == ["gate0-aplicado-a-montante"]
    assert avisos[0]["severidade"] == "atencao" and not avisos[0].get("aberto_dono_po")
    # a mesma diferença sem a cascata é mudança do D0 no texto do Gate 0: continua `[ABERTO — dono: PO]`
    avisos = []
    montar_sobre_aceita(aceita, velha, r"^## 13", avisos=avisos, autor="D0", estado={}, estrito=True)
    assert avisos[0]["aberto_dono_po"] and avisos[0]["severidade"] == "bloqueio"


def test_troca_curta_a_montante_nao_explica_qualquer_linha_do_d0():
    """Revisão do PR 5 (24/10): com «a troca está na linha», a troca «3» → «2» explicava qualquer linha com «2», e a
    mudança espontânea do D0 no texto do Gate 0 virava atenção em vez de `[ABERTO — dono: PO]`."""
    from agents.checkers import montar_sobre_aceita

    aceita = ("# Spec\n\n## 2. Mecânica\n- A 5A tem 2 opções.\n- A 5B libera em 2 toques.\n\n"
              "## 13. Decisões D0\n| `[D0-1]` | x |\n")
    montante = [{"documento": "spec_missao", "de": "3", "para": "2"}]
    # o D0 trazia a linha de antes da troca: o par exato explica, mesmo com a troca curta
    avisos = []
    montar_sobre_aceita(aceita, aceita.replace("tem 2 opções", "tem 3 opções"), r"^## 13", avisos=avisos, autor="D0",
                        estado={"edicoes_a_montante": montante}, estrito=True)
    assert [a["codigo"] for a in avisos] == ["gate0-aplicado-a-montante"]
    # o D0 mudou outra linha, que só por acaso tem «2»: continua `[ABERTO — dono: PO]`
    avisos = []
    montar_sobre_aceita(aceita, aceita.replace("libera em 2 toques", "libera em 4 toques"), r"^## 13", avisos=avisos,
                        autor="D0", estado={"edicoes_a_montante": montante}, estrito=True)
    assert avisos[0]["aberto_dono_po"] and avisos[0]["codigo"] == "alterou-fora-do-proprio-bloco"
    # troca longa que cobre só um pedaço da linha também não explica a linha inteira
    longa = [{"documento": "spec_missao", "de": "em 9 toques", "para": "em 2 toques"}]
    avisos = []
    montar_sobre_aceita(aceita, aceita.replace("A 5B libera em 2 toques.", "A 5B libera em 9 toques, sem limite de "
                                                                           "tempo e com dica sonora."),
                        r"^## 13", avisos=avisos, autor="D0", estado={"edicoes_a_montante": longa}, estrito=True)
    assert avisos[0]["aberto_dono_po"]


# ------------------------------------------------------------------ linha de base com as trocas a montante
def test_linha_de_base_conta_as_trocas_de_produto_como_da_correcao():
    from agents.checkers import LinhaDeBaseAgent

    estado = {"modo_correcao": "pontual", "etapa_da_correcao": "design", "edicoes_pontuais": [],
              "edicoes_a_montante": [{"documento": "one_pager", "de": "Publicar no Álbum", "para": "Colocar no álbum"}],
              "design_status": "bloqueado",
              "design_status_envelope": {"achados": [{"severidade": "bloqueio", "codigo": "copy-diverge",
                                                      "resumo": "A copy não traz «Colocar no álbum» do one-pager.",
                                                      "citacao": "Colocar no álbum"}]},
              "linha_de_base": {"design_status": {"status": "aprovado", "achados": []}}}
    final = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[LinhaDeBaseAgent(name="L")]), estado))
    assert [l["origem"] for l in final["linha_de_base_linhas"]] == [lb.DA_EDICAO]
    assert final["design_status"] == "bloqueado"
    assert "Trocas a montante" in final["linha_de_base_report"]


# ------------------------------------------------------------------ a cascata, com runner e editor falsos
ONE_PAGER = ("# One-pager\n\n## 4. Etapas\n\n**Etapa 5B:** a criança toca em **Publicar no Álbum**.\n\n"
             "## 10. Tempos\n\nTempo da etapa 3: 90 s — PO, parecer de 21/10/2026\n")
SPEC = "# Spec v1\n\n## 2. Mecânica\n\n- Botão `Publicar no Álbum` confirma a segunda foto.\n"
COPY = "| E5-ALU-02 | botão | Publicar no Álbum |\n| E4-ALU-02 | instrução | Toque no pátio inteiro! |\n"


class _Cascata:
    def __init__(self, estado=None):
        self.temp = Path(tempfile.mkdtemp())
        self.run_dir = self.temp / "20261023-000000-session_cascata"
        self.run_dir.mkdir(parents=True)
        self.estado = estado or {
            "briefing": "briefing", "material_anexado": "material", "nucleo_narrativo": "# Núcleo\n",
            "mapa_conceitual": "mapa", "ideacao_mecanismos": "ideação", "one_pager": ONE_PAGER,
            "spec_missao_gate0": SPEC, "spec_missao": SPEC + "\n## 13. Decisões D0\n| `[D0-1]` | x |\n",
            "one_pager_resumido": "# Resumido\n", "copy_strings_revisada": COPY, "jornada_telas": "jornada",
            "gate_final_status": "aprovado", "design_status": "bloqueado",
            "design_status_envelope": {"achados": [{"severidade": "bloqueio", "codigo": "antigo",
                                                    "resumo": "bloqueio que já existia"}]},
            "decisoes_do_po": [{"id": "x1", "tipo": "parametro", "assunto": "tempo da etapa 3",
                                "gravado": "90 s — PO, parecer de 21/10/2026"}]}
        (self.run_dir / "estado.json").write_text(json.dumps(self.estado), encoding="utf-8")
        (self.run_dir / "conversa.json").write_text(json.dumps({
            "session_id": "session_cascata", "user_id": "u", "created_at": "23/10/2026 10:00:00", "prompt": "briefing",
            "messages": []}), encoding="utf-8")
        self.runs, self.editor = [], []

    def runner(self, linhas_por_run):
        cascata = self

        async def falso(**kwargs):
            from pipeline.runner import PipelineExecutionResult

            cascata.runs.append(kwargs)
            linhas = linhas_por_run.get(kwargs["stages"][0], [])
            estado = dict(kwargs["initial_state"], linha_de_base_linhas=linhas)
            (Path(kwargs["run_dir"]) / "estado.json").write_text(json.dumps(estado), encoding="utf-8")
            yield {"type": "pipeline_completed", "result": PipelineExecutionResult(
                session_id=kwargs["session_id"], user_id=kwargs["user_id"], prompt=kwargs["prompt"], final_output="ok",
                state=estado, status="success", output_dir=str(kwargs["run_dir"]))}

        return falso

    def proponente(self, por_etapa):
        cascata = self

        async def falso(pedido, etapa, documentos, *, erros="", achados=""):
            cascata.editor.append({"etapa": etapa, "pedido": pedido, "documentos": dict(documentos), "erros": erros})
            respostas = por_etapa[etapa]
            n = sum(1 for e in cascata.editor if e["etapa"] == etapa)
            return respostas[min(n, len(respostas)) - 1]

        return falso

    def rodar(self, divisao, por_etapa, linhas_por_run=None, etapa="design", pedido=PEDIDO, falha_em=(), **opcoes):
        import pipeline.runner as runner_mod
        from pipeline.reexecucao import PedidoCorrecao, executar_cascata_stream

        async def coletar():
            return [e async for e in executar_cascata_stream(
                self.run_dir, etapa, PedidoCorrecao(texto=pedido), divisao, None,
                proponente=self.proponente(por_etapa), **opcoes)]

        runner = self.runner(linhas_por_run or {})

        async def com_falha(**kwargs):
            if kwargs["stages"][0] in falha_em:
                self.runs.append(kwargs)
                yield {"type": "pipeline_error", "error": "o runner caiu"}
                return
            async for evento in runner(**kwargs):
                yield evento

        with mock.patch.dict(os.environ, {"CORRECAO_PONTUAL": "true", "CORRECAO_PONTUAL_PASSADAS": "2"}), \
                mock.patch.object(runner_mod, "run_orchestrator_pipeline_stream", com_falha):
            return asyncio.run(coletar())

    def estado_final(self):
        return json.loads((self.run_dir / "estado.json").read_text(encoding="utf-8"))

    def fechar(self):
        shutil.rmtree(self.temp, ignore_errors=True)


def _proposta(*trocas, pendencias=()):
    return ed.Proposta(modo=ed.MODO_PONTUAL, edicoes=[ed.Edicao(*t) for t in trocas], pendencias=list(pendencias))


_BOTAO_1P = ("one_pager", "toca em **Publicar no Álbum**", "toca em **Colocar no álbum**")
_BOTAO_SPEC = ("spec_missao", "Botão `Publicar no Álbum`", "Botão `Colocar no álbum`")
_BOTAO_COPY = ("copy_strings_revisada", "| botão | Publicar no Álbum |", "| botão | Colocar no álbum |")
_PATIO_COPY = ("copy_strings_revisada", "Toque no pátio inteiro!", "Marque no pátio.")


def test_cascata_aplica_produto_antes_e_o_design_acompanha():
    c = _Cascata()
    try:
        eventos = c.rodar(_divisao().como_dict(), {"produto": [_proposta(_BOTAO_1P, _BOTAO_SPEC)],
                                                   "design": [_proposta(_BOTAO_COPY, _PATIO_COPY)]})
        assert [r["stages"] for r in c.runs] == [["produto"], ["design"]]
        # o editor de produto recebe só o item de produto; o de design, o pedido inteiro e a divisão
        assert "Publicar no Álbum" in c.editor[0]["pedido"] and "Toque no pátio" not in c.editor[0]["pedido"]
        assert "Toque no pátio" in c.editor[1]["pedido"] and "aplicados a montante" in c.editor[1]["pedido"]
        # o design parte da versão de antes: o passo de produto tinha apagado os documentos de design do estado
        assert c.editor[1]["documentos"]["copy_strings_revisada"] == COPY.strip()
        produto, design = (r["initial_state"] for r in c.runs)
        assert "Colocar no álbum" in produto["one_pager"] and "Colocar no álbum" in produto["spec_missao"]
        assert "Toque no pátio" not in produto["pedido_correcao"].split("### Divisão")[0]
        assert design["one_pager"] == produto["one_pager"]
        assert "Marque no pátio." in design["copy_strings_revisada"] and "Colocar no álbum" in design["copy_strings_revisada"]
        # a linha de base do design é a de antes da cascata: o 🔴 antigo continua «já bloqueava antes»
        assert design["linha_de_base"]["design_status"]["status"] == "bloqueado"
        assert [e["documento"] for e in design["edicoes_a_montante"]] == ["one_pager", "spec_missao"]
        assert design["divisao_do_pedido"]["itens"][0]["dono"] == tp.PRODUTO
        registros = [e["registro"] for e in eventos if e["type"] == "correcao_completed"]
        assert [r["cascata"]["passo"] for r in registros] == ["1/2 (produto)", "2/2 (design)"]
        assert [r["etapa"] for r in registros] == ["produto", "design"]
        final = c.estado_final()
        assert final["decisoes_do_po"] == c.estado["decisoes_do_po"]
        assert "90 s — PO, parecer de 21/10/2026" in final["one_pager"]
        conversa = json.loads((c.run_dir / "conversa.json").read_text(encoding="utf-8"))
        assert len(conversa["historico_correcoes"]) == 2 and "cascata do pedido feito em" in conversa["messages"][-1]["content"]
    finally:
        c.fechar()


def test_so_o_ultimo_passo_da_cascata_fecha_a_missao():
    """Revisão do PR 5 (24/10): pela correção do chat, o passo de produto rodava diagnóstico, aprendizado e catálogo sobre
    a missão cujo design ele tinha acabado de apagar."""
    c = _Cascata()
    try:
        c.rodar(_divisao().como_dict(), {"produto": [_proposta(_BOTAO_1P, _BOTAO_SPEC)],
                                         "design": [_proposta(_PATIO_COPY)]}, com_transversal=True)
        assert [(r["stages"], r["com_transversal"]) for r in c.runs] == [(["produto"], False), (["design"], True)]
    finally:
        c.fechar()


def test_refazer_depois_do_design_que_falhou_corrige_o_design_pontualmente():
    """Revisão do PR 5 (24/10): produto aplicado, design falhou (o backup devolve o estado sem os documentos de design);
    no Refazer seguinte produto sai sem trocas, e o design tem de partir da versão anterior, pelo editor — não pelos
    autores."""
    c = _Cascata()
    try:
        eventos = c.rodar(_divisao().como_dict(), {"produto": [_proposta(_BOTAO_1P, _BOTAO_SPEC)],
                                                   "design": [_proposta(_BOTAO_COPY, _PATIO_COPY)]}, falha_em=("design",))
        assert eventos[-1]["type"] == "correcao_error"
        intermediario = c.estado_final()
        assert "Colocar no álbum" in intermediario["one_pager"] and not intermediario.get("copy_strings_revisada")
        c.runs, c.editor = [], []
        sem_trocas = ed.Proposta(modo=ed.MODO_PONTUAL, motivo="o one-pager já diz isso")
        eventos = c.rodar(_divisao().como_dict(), {"produto": [sem_trocas],
                                                   "design": [_proposta(_BOTAO_COPY, _PATIO_COPY)]})
        assert [r["stages"] for r in c.runs] == [["design"]]
        assert c.editor[-1]["etapa"] == "design" and c.editor[-1]["documentos"]["copy_strings_revisada"] == COPY.strip()
        design = c.runs[0]["initial_state"]
        assert design["modo_correcao"] == ed.MODO_PONTUAL
        assert "Marque no pátio." in design["copy_strings_revisada"] and "Colocar no álbum" in design["copy_strings_revisada"]
        assert eventos[-1]["type"] == "correcao_completed"
    finally:
        c.fechar()


def test_decisao_do_po_e_conferida_em_cada_documento_e_por_contagem():
    """Revisão do PR 5 (24/10): a decisão sumia do one-pager e a guarda não recusava porque a spec ainda a dizia."""
    from pipeline.reexecucao import validador_das_decisoes

    g = "90 s — PO, parecer de 21/10/2026"
    estado = {"one_pager": f"Tempo: {g}\nOutro tempo: {g}\n", "spec_missao_gate0": f"- Tempo: {g}\n",
              "spec_missao": f"- Tempo: {g}\n\n## 13. D0\n", "decisoes_do_po": [{"gravado": g}, {"gravado": g}]}
    validar = validador_das_decisoes(estado)
    assert validar({"one_pager": estado["one_pager"], "spec_missao": estado["spec_missao_gate0"]}) == []
    # só o one-pager perde a decisão; a spec ainda a diz
    erros = validar({"one_pager": "Tempo: 60 s\nOutro tempo: 60 s\n", "spec_missao": estado["spec_missao_gate0"]})
    assert len(erros) == 1 and "one-pager" in erros[0]
    # dois itens com o mesmo valor e a mesma data: apagar uma das ocorrências também é apagar
    assert validar({"one_pager": f"Tempo: {g}\nOutro tempo: 60 s\n", "spec_missao": estado["spec_missao_gate0"]})
    # só a spec perde
    erros = validar({"one_pager": estado["one_pager"], "spec_missao": "- Tempo: 60 s\n"})
    assert len(erros) == 1 and "spec" in erros[0]


def test_cascata_nao_apaga_a_decisao_do_po_gravada_no_de_acordo():
    c = _Cascata()
    try:
        apaga = _proposta(_BOTAO_1P, ("one_pager", "90 s — PO, parecer de 21/10/2026", "60 s"))
        c.rodar(_divisao().como_dict(), {"produto": [apaga, _proposta(_BOTAO_1P, _BOTAO_SPEC)],
                                         "design": [_proposta(_PATIO_COPY)]})
        assert "decisão do PO gravada no de acordo" in c.editor[1]["erros"]
        assert "90 s — PO, parecer de 21/10/2026" in c.runs[0]["initial_state"]["one_pager"]
    finally:
        c.fechar()


def test_item_de_produto_que_nao_cabe_em_edicao_nao_toca_em_nada_e_pede_devolver():
    c = _Cascata()
    try:
        estrutural = ed.Proposta(modo=ed.MODO_ESTRUTURAL, motivo="refaz a mecânica da 5A")
        eventos = c.rodar(_divisao().como_dict(), {"produto": [estrutural], "design": [_proposta(_PATIO_COPY)]})
        assert eventos[-1]["type"] == "correcao_error" and "Devolver" in eventos[-1]["error"]
        assert not c.runs and c.estado_final() == c.estado
        assert not (c.run_dir / ".correcoes").exists()
    finally:
        c.fechar()


def test_item_de_produto_ja_no_one_pager_pula_os_gates_de_produto():
    c = _Cascata()
    try:
        sem_trocas = ed.Proposta(modo=ed.MODO_PONTUAL, motivo="o one-pager já diz isso")
        eventos = c.rodar(_divisao().como_dict(), {"produto": [sem_trocas], "design": [_proposta(_PATIO_COPY)]})
        assert [r["stages"] for r in c.runs] == [["design"]]
        assert any(e["type"] == "cascata_produto_sem_trocas" for e in eventos)
        assert c.editor[1]["documentos"]["copy_strings_revisada"] == COPY  # do estado, que o produto não apagou
        assert eventos[-1]["type"] == "correcao_completed"
    finally:
        c.fechar()


def test_bloqueio_novo_em_produto_desfaz_a_cascata():
    c = _Cascata()
    try:
        novo = {"gate": "gate_final_status", "origem": lb.DA_EDICAO, "codigo": "x", "resumo": "quebrou", "antes": "aprovado"}
        eventos = c.rodar(_divisao().como_dict(), {"produto": [_proposta(_BOTAO_1P, _BOTAO_SPEC), ed.Proposta(
            modo=ed.MODO_PONTUAL, motivo="nada a consertar")], "design": [_proposta(_PATIO_COPY)]},
            linhas_por_run={"produto": [novo]})
        assert eventos[-1]["type"] == "correcao_error" and "Devolver" in eventos[-1]["error"]
        assert all(r["stages"] == ["produto"] for r in c.runs)  # o design não rodou
        final = c.estado_final()
        assert final["one_pager"] == ONE_PAGER and final["copy_strings_revisada"] == COPY
        conversa = json.loads((c.run_dir / "conversa.json").read_text(encoding="utf-8"))
        assert conversa["historico_correcoes"][-1]["status"] == "desfeita"
        assert "Pedido não aplicado" in conversa["messages"][-1]["content"]
    finally:
        c.fechar()


def test_cascata_recusa_divisao_com_item_sem_dono():
    c = _Cascata()
    try:
        eventos = c.rodar(_divisao({2: "indefinido"}).como_dict(), {"produto": [], "design": []})
        assert eventos[-1]["type"] == "correcao_error" and "Devolver" in eventos[-1]["error"] and not c.runs
    finally:
        c.fechar()


def test_refazer_de_dev_com_item_de_produto_passa_por_design():
    c = _Cascata({**_Cascata().estado, "handoff_dev": "handoff: botão Publicar no Álbum"})
    try:
        d = tp.dividir(PEDIDO, "dev", ESTADO_ITENS, [{"n": 1, "dono": "dev"}, {"n": 2, "dono": "dev"}])
        c.rodar(d.como_dict(), {"produto": [_proposta(_BOTAO_1P, _BOTAO_SPEC)], "design": [_proposta(_BOTAO_COPY)],
                                "dev": [_proposta(("handoff_dev", "botão Publicar no Álbum", "botão Colocar no álbum"))]},
                etapa="dev")
        assert [r["stages"] for r in c.runs] == [["produto"], ["design"], ["dev"]]
        dev = c.runs[2]["initial_state"]
        assert dev["handoff_dev"] == "handoff: botão Colocar no álbum"
        # o dev conta como da correção as trocas de produto e as de design
        assert [e["documento"] for e in dev["edicoes_a_montante"]] == ["one_pager", "spec_missao", "copy_strings_revisada"]
    finally:
        c.fechar()


def test_reaplicar_o_pedido_de_13_24_na_exp02ef1b_poe_o_texto_novo_em_produto():
    """Como medir do plano: hoje o texto novo de produto tem 0 ocorrência no one-pager e na spec; com a rota, o botão
    «Colocar no álbum» chega aos dois, e a microcopy escrita pelo design só aos documentos de design."""
    from tools.propagacao import _Corpus, documentos

    estado = _estado("exp02ef1b-4fd72a9a")
    pedido = _pedido(estado, "23/10/2026 13:24")
    d = tp.dividir(pedido, "design", estado, [{"n": n, "dono": "design"} for n in range(1, 7)])
    c = _Cascata(estado)
    try:
        def trocas(chave, texto):
            linhas = [l for l in dict.fromkeys(texto.splitlines()) if "Publicar no Álbum" in l and texto.count(l) == 1]
            return [(chave, l, l.replace("Publicar no Álbum", "Colocar no álbum")) for l in linhas]

        produto = trocas("one_pager", estado["one_pager"]) + trocas("spec_missao", estado["spec_missao_gate0"])
        c.rodar(d.como_dict(), {"produto": [_proposta(*produto)], "design": [ed.Proposta(modo=ed.MODO_PONTUAL)]},
                pedido=pedido)
        assert "E5-ALU-02 — Segunda foto" in c.editor[0]["pedido"] and "Moldura pequena" not in c.editor[0]["pedido"]
        corpus = _Corpus(documentos(c.estado_final()))
        assert corpus.conta("one_pager", "Colocar no álbum") >= 1
        assert corpus.conta("spec_missao_gate0", "Colocar no álbum") >= 1 or corpus.conta("spec_produto", "Colocar no álbum") >= 1
        assert corpus.conta("one_pager", "Aumente a moldura") == 0
    finally:
        c.fechar()


def test_documentos_da_etapa_da_versao_anterior_so_quando_pedido():
    estado = {"versao_anterior_copy_strings_revisada": "copy de antes", "jornada_telas": "jornada"}
    assert "copy_strings_revisada" not in ed.documentos_da_etapa(estado, "design")
    docs = ed.documentos_da_etapa(estado, "design", versao_anterior=True)
    assert docs["copy_strings_revisada"] == "copy de antes" and docs["jornada_telas"] == "jornada"


def test_nota_da_esteira_fica_fora_do_pedido_que_a_fidelidade_confere():
    from pipeline.reexecucao import PedidoCorrecao, texto_do_pedido

    md = PedidoCorrecao(texto="Trocar o botão.", nota_da_esteira="Itens de produto já aplicados.").como_markdown("design")
    assert "### Divisão do pedido pela triagem" in md and texto_do_pedido(md) == "Trocar o botão."


def test_dev_parte_da_versao_anterior_quando_so_o_design_rodou_antes():
    """Produto sem nada a trocar (o one-pager já diz), design rodou: o passo de design apagou o handoff do estado."""
    c = _Cascata({**_Cascata().estado, "handoff_dev": "handoff: botão Publicar no Álbum"})
    try:
        d = tp.dividir(PEDIDO, "dev", ESTADO_ITENS, [{"n": 1, "dono": "dev"}, {"n": 2, "dono": "dev"}])
        sem_trocas = ed.Proposta(modo=ed.MODO_PONTUAL, motivo="o one-pager já diz isso")
        c.rodar(d.como_dict(), {"produto": [sem_trocas], "design": [_proposta(_BOTAO_COPY)],
                                "dev": [_proposta(("handoff_dev", "botão Publicar no Álbum", "botão Colocar no álbum"))]},
                etapa="dev")
        assert [r["stages"] for r in c.runs] == [["design"], ["dev"]]
        assert c.editor[-1]["documentos"]["handoff_dev"] == "handoff: botão Publicar no Álbum"
        assert c.runs[1]["initial_state"]["handoff_dev"] == "handoff: botão Colocar no álbum"
    finally:
        c.fechar()


def test_refazer_triado_que_nao_aplicou_nada_volta_ao_parecer_para_devolver():
    fluxo = {**passagem.novo_fluxo(), "etapa": "design", "situacao": passagem.REFAZENDO}
    novo = passagem.concluir_execucao(fluxo, False, None, pede_devolver=True)
    assert novo["situacao"] == passagem.AGUARDANDO and not novo.get("falhou_refazendo")
    assert passagem.DEVOLVER in passagem.acoes_possiveis(novo, "design", {})
    # erro comum de execução continua «falhou»
    assert passagem.concluir_execucao(fluxo, False, None)["situacao"] == passagem.FALHOU


def test_execucao_em_segundo_plano_repassa_o_pedido_de_devolver():
    from pipeline import execucao_fundo

    temp = Path(tempfile.mkdtemp())
    try:
        run_dir = temp / "sessao"
        run_dir.mkdir()
        fluxo = {**passagem.novo_fluxo(), "etapa": "design", "situacao": passagem.REFAZENDO}
        (run_dir / "conversa.json").write_text(json.dumps({"fluxo": fluxo}), encoding="utf-8")

        async def stream():
            yield {"type": "correcao_error", "error": "itens de produto não cabem", "pede_devolver": True}

        with mock.patch.dict(os.environ, {"EXECUCAO_LOCAL_DIR": str(temp / "local")}):
            asyncio.run(execucao_fundo._consumir(run_dir, stream(), {"etapa": "design"}, False))
            assert execucao_fundo.ler_execucao(run_dir)["pede_devolver"] is True
        assert passagem.ler_fluxo(run_dir)["situacao"] == passagem.AGUARDANDO
    finally:
        shutil.rmtree(temp, ignore_errors=True)


# ------------------------------------------------------------------ revisão do PR 5 (24/10, 2ª rodada)
def test_editor_de_produto_sem_trocas_e_com_pendencia_nao_segue_ao_design():
    """O editor de produto não trocou nada e deixou o item para o PO (regra 6 do `editor_pontual.md`: o pedido contraria
    a decisão gravada no de acordo). Seguir ao design deixava o one-pager com «Publicar no Álbum», a copy com «Colocar
    no álbum» e o A094 dando o item por aplicado a montante."""
    c = _Cascata()
    try:
        recusa = ed.Proposta(modo=ed.MODO_PONTUAL, motivo="o pedido contraria a decisão do PO",
                             pendencias=["o item 1 contraria a decisão do PO de 21/10; fica para o PO"])
        eventos = c.rodar(_divisao().como_dict(), {"produto": [recusa], "design": [_proposta(_BOTAO_COPY, _PATIO_COPY)]})
        assert eventos[-1]["type"] == "correcao_error" and eventos[-1]["pede_devolver"] is True
        assert "contraria a decisão do PO de 21/10" in eventos[-1]["error"] and "Devolver" in eventos[-1]["error"]
        assert eventos[-1]["pendencias"] == ["o item 1 contraria a decisão do PO de 21/10; fica para o PO"]
        assert not any(e["type"] == "cascata_produto_sem_trocas" for e in eventos)
        assert not c.runs and [e["etapa"] for e in c.editor] == ["produto"]
        assert c.estado_final() == c.estado and not (c.run_dir / ".correcoes").exists()
    finally:
        c.fechar()


def test_sem_trocas_e_sem_pendencia_segue_e_mostra_o_motivo_do_editor():
    c = _Cascata()
    try:
        sem_trocas = ed.Proposta(modo=ed.MODO_PONTUAL, motivo="o one-pager já diz «Colocar no álbum» na 5B")
        eventos = c.rodar(_divisao().como_dict(), {"produto": [sem_trocas], "design": [_proposta(_PATIO_COPY)]})
        aviso = next(e for e in eventos if e["type"] == "cascata_produto_sem_trocas")
        assert aviso["motivo"] == "o one-pager já diz «Colocar no álbum» na 5B" and aviso["motivo"] in aviso["mensagem"]
        assert eventos[-1]["type"] == "correcao_completed"
    finally:
        c.fechar()


def test_pendencia_do_passo_de_produto_com_trocas_chega_ao_design_como_nao_aplicada():
    c = _Cascata()
    try:
        parcial = _proposta(_BOTAO_1P, _BOTAO_SPEC, pendencias=["o tempo da etapa 3 contraria a decisão do PO"])
        c.rodar(_divisao().como_dict(), {"produto": [parcial], "design": [_proposta(_BOTAO_COPY, _PATIO_COPY)]})
        assert [r["stages"] for r in c.runs] == [["produto"], ["design"]]
        nota = c.editor[-1]["pedido"]
        assert "**não aplicou**" in nota and "o tempo da etapa 3 contraria a decisão do PO" in nota
    finally:
        c.fechar()


def test_design_que_falha_depois_de_produto_diz_que_produto_ficou_aplicado():
    c = _Cascata()
    try:
        eventos = c.rodar(_divisao().como_dict(), {"produto": [_proposta(_BOTAO_1P, _BOTAO_SPEC)],
                                                   "design": [_proposta(_BOTAO_COPY, _PATIO_COPY)]}, falha_em=("design",))
        erro = eventos[-1]
        assert erro["type"] == "correcao_error" and erro["aplicados_antes"] == ["produto"]
        assert "ficaram aplicados" in erro["error"] and not erro.get("pede_devolver")
        assert erro["registro"]["cascata"]["aplicados_antes"] == ["produto"]
        conversa = json.loads((c.run_dir / "conversa.json").read_text(encoding="utf-8"))
        ultima = conversa["messages"][-1]["content"]
        assert "O passo de design da cascata falhou" in ultima and "voltou ao estado anterior" not in ultima
        # o erro do primeiro passo continua «nada foi aplicado», sem aplicados_antes
        c2 = _Cascata()
        try:
            eventos = c2.rodar(_divisao().como_dict(), {"produto": [_proposta(_BOTAO_1P, _BOTAO_SPEC)],
                                                        "design": []}, falha_em=("produto",))
            assert eventos[-1]["type"] == "correcao_error" and "aplicados_antes" not in eventos[-1]
            ultima = json.loads((c2.run_dir / "conversa.json").read_text(encoding="utf-8"))["messages"][-1]["content"]
            assert "voltou ao estado anterior" in ultima
        finally:
            c2.fechar()
    finally:
        c.fechar()


def test_refazer_que_nao_aplicou_nada_nao_da_os_itens_de_produto_por_aplicados():
    """Revisão do PR 5 (24/10): o refazer recusado (Devolver) seguia nas notas como «já aplicado no one-pager», e o A094
    das execuções seguintes o listava como aplicado a montante — inclusive depois de um De acordo no design."""
    from agents.checkers import FidelidadeCheckAgent

    fluxo = {**passagem.novo_fluxo(), "etapa": "design", "situacao": passagem.AGUARDANDO}
    novo, _ = passagem.aplicar(fluxo, passagem.REFAZER, _sessao("design"), PEDIDO, ESTADO_ITENS,
                               divisao=_divisao().como_dict())
    # erro comum de execução não marca: produto pode ter sido aplicado antes do design falhar
    assert not passagem.concluir_execucao(novo, False, None)["pareceres"][-1].get("nao_aplicado")
    novo = passagem.concluir_execucao(novo, False, None, pede_devolver=True)
    assert novo["pareceres"][-1]["nao_aplicado"] is True
    pedidos = passagem.pedidos_do_po(novo)
    assert [(p["etapa"], p.get("a_montante_de"), p.get("pendente_em")) for p in pedidos] == [
        ("produto", None, "produto"), ("design", None, None)]
    assert "NÃO APLICADOS" in pedidos[0]["origem"]
    assert "NÃO APLICADOS" in passagem.notas_de_passagem(novo)

    agente = FidelidadeCheckAgent(name="A094", status_key="fid_status", report_key="fid_report",
                                  documentos=["copy_strings_revisada"], etapas_pedido=["design"], com_briefing=False,
                                  etapa="design", incluir_corrente=False)
    final = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[agente]),
                               {"copy_strings_revisada": "Marque no pátio.", "pedidos_do_po": pedidos}))
    assert "aplicado a montante" not in final["fid_report"]
    assert "Publicar no Álbum" not in final["fid_report"].split("```json")[0]  # nem cobrado no design


def test_item_de_design_de_um_pedido_de_dev_sai_como_de_design_na_prova():
    from agents.checkers import FidelidadeCheckAgent
    from pipeline.reexecucao import PedidoCorrecao
    from tools.fidelidade import aplicados_a_montante

    assert "item de produto" in aplicados_a_montante([("o", "Botão")])[0]["prova"]
    prova = aplicados_a_montante([("o", "Botão", "design")])[0]["prova"]
    assert "item de design" in prova and "fidelidade de design" in prova and "produto" not in prova
    d = tp.dividir(PEDIDO, "dev", ESTADO_ITENS, [{"n": 1, "dono": "dev"}, {"n": 2, "dono": "design"}])
    assert [i.dono for i in d.itens] == [tp.PRODUTO, tp.DESIGN]
    agente = FidelidadeCheckAgent(name="A126", status_key="fid_status", report_key="fid_report",
                                  documentos=["handoff_dev"], etapas_pedido=["dev"], com_briefing=False,
                                  etapa="dev", incluir_corrente=False)
    estado = {"handoff_dev": "handoff", "etapa_da_correcao": "dev", "divisao_do_pedido": d.como_dict(),
              "pedido_correcao": PedidoCorrecao(texto=PEDIDO).como_markdown("dev")}
    relatorio = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[agente]), estado))["fid_report"]
    assert "item de produto pela triagem" in relatorio and "item de design pela triagem" in relatorio
    assert "conferido pela fidelidade de design" in relatorio
