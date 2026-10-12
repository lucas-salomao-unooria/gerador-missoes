"""Correções da auditoria do padrão ouro de 08/10/2026, medidas na primeira execução real do código novo.

A exp01ef1b terminou o design 🔴 com «Coerência entre documentos reprovado (21 lacunas)»: 20 eram falsos positivos ou
conflito do glossário com o one-pager aprovado, e o orçamento de retrabalho, mal contado, não deixou nenhum autor
consertar a única real. Outros defeitos foram confirmados em código na mesma auditoria. Cada teste aqui fixa um deles.
"""
import asyncio

from google.adk.agents.sequential_agent import SequentialAgent

from test_conteudo_aprovado import _rodar
from test_pipeline import _fixture_exp09

GLOSSARIO = """# Spec — exp01ef1b

## Glossário canônico

### Entidades
| Nome canônico | Variantes proibidas |
|---|---|
| Unoovista | "Instagram da Tia"; "Insta"; "App Escola" |
| Atividade | "Visualizadores"; "Quem viu"; "Olhinho" |
| Seu story | "Story público"; "Para todos" |
| Unooria | "App Escola"; "Sistema Unooria" |
"""
ONE_PAGER = "# One-pager — O MUNDO DAS IMAGENS: Quem viu o bolo da Iara\n\nTata: apertou no olhinho da atividade.\n"


def _codigos(r):
    return [a["codigo"] for a in r["achados"] if a["severidade"] == "bloqueio"]


# --------------------------------------------------------------------------- glossário
def test_tabela_do_glossario_republicada_nao_e_uso_da_variante():
    from tools.consistencia import validar

    copy = ("| Unoovista | Nome da rede social. | \"Instagram da Tia\", \"Insta\", \"App Escola\" | \"Vamos postar no Unoovista?\" |\n"
            "| Seu story | Botão de publicação aberta. | \"Story público\", \"Para todos\" | \"Seu story\" |\n")
    assert _codigos(validar(GLOSSARIO, {"copy revisada": copy})) == []
    # a mesma variante fora da tabela é uso, e continua bloqueando
    assert _codigos(validar(GLOSSARIO, {"copy revisada": "Abra o Instagram da Tia e poste a foto."})) == ["variante-proibida"]


def test_variante_curta_so_conta_como_rotulo():
    from tools.consistencia import validar

    frase = "A liberação ativa a missão para todos os dispositivos pareados da sala."
    assert _codigos(validar(GLOSSARIO, {"jornada": frase})) == []
    assert _codigos(validar(GLOSSARIO, {"jornada": 'Toque em "Para todos" para publicar.'})) == ["variante-proibida"]
    assert _codigos(validar(GLOSSARIO, {"jornada": "| E4-ALU-02 | **Para todos** |"})) == ["variante-proibida"]


def test_variante_que_o_po_aprovou_nao_e_proibida_e_volta_ao_autor_da_spec():
    from tools.consistencia import glossario_contra_o_aprovado, validar

    prototipo = 'Protótipo — O MUNDO DAS IMAGENS. Toque em "Quem viu" e depois no **Olhinho**.'
    assert _codigos(validar(GLOSSARIO, {"protótipo": prototipo})) == ["variante-proibida"] * 2
    assert _codigos(validar(GLOSSARIO, {"protótipo": prototipo}, aprovado=ONE_PAGER)) == []
    conflitos = glossario_contra_o_aprovado(GLOSSARIO, ONE_PAGER)
    assert {a["codigo"] for a in conflitos} == {"glossario-proibe-o-aprovado"}
    assert {a["agente_responsavel"] for a in conflitos} == {"spec-missao"}
    assert sorted(a["resumo"].split("«")[1].split("»")[0] for a in conflitos) == ["Olhinho", "Quem viu"]


# --------------------------------------------------------------------------- Stitch
def test_tela_com_id_fora_do_padrao_bloqueia_a_cobertura_do_stitch():
    from tools import afirmacoes as af

    folha, jornada = _fixture_exp09("stitch_telas.md"), _fixture_exp09("jornada.md")
    linha = next(l for l in jornada.splitlines() if l.startswith("| `E3-ALU-01` | E3"))
    com_sessao_b = jornada.replace(linha, linha + "\n" + linha.replace("`E3-ALU-01` | E3", "`E5B-ALU-01` | E5"), 1)
    cob = af.cobertura_stitch(folha, com_sessao_b)
    sem_id = [a for a in cob["achados"] if a["codigo"] == "stitch-tela-sem-id"]
    assert sem_id and sem_id[0]["agente_responsavel"] == "jornada" and "E5B-ALU-01" in sem_id[0]["resumo"]
    assert "E5-ALU-04" in sem_id[0]["resumo"], "a convenção sugerida tem de ser um ID que o normalizador aceita"
    from tools.telas import normalizar

    assert normalizar("E5-ALU-04") == "E5-ALU-04" and normalizar("E5B-ALU-01") is None


# --------------------------------------------------------------------------- leitura de veredito
def test_nao_aprovado_e_envelope_contraditorio_reprovam():
    from agents.callbacks import inferir_status, status_registrado

    assert inferir_status("# Gate\n\n**Veredito: NÃO APROVADO**") == "bloqueado"
    assert inferir_status("x", {"status": "aprovado", "veredito": "vermelho"}) == "bloqueado"
    assert status_registrado("x", {"status": "aprovado", "veredito": "vermelho"}) == "bloqueado"
    assert inferir_status("**Veredito: 🟢 APROVADO**") == "aprovado"
    assert inferir_status("x", {"status": "aguarda_gate"}) == "aprovado"


# --------------------------------------------------------------------------- quem decidiu
def test_po_no_one_pager_e_atribuicao_ao_po():
    from tools.decisoes import atribuicoes_ao_po, ha_registro_do_po

    linha = "| Mecânica de construção de programa em blocos na E5 | **PO no one-pager v1.8.0** | 2026-10-08 |"
    assert atribuicoes_ao_po(linha)
    assert not atribuicoes_ao_po("| Desvinculação de EF06CO07 | Briefing do PO (reprocessamento) | 2026-10-08 |")
    assert not ha_registro_do_po({}) and ha_registro_do_po({"one_pager_po": "# One-pager do PO"})


# --------------------------------------------------------------------------- PRD embrulhado
def test_prd_embrulhado_e_desembrulhado_ao_ser_gravado_e_antes_do_anexo():
    from agents.callbacks import desembrulhar_documento

    class _Ctx:
        def __init__(self, state):
            self.state = state

    ctx = _Ctx({"prd_final": "```markdown\n# PRD\n\n## 14. KPIs\nKPI-01\n```"})
    desembrulhar_documento("prd_final")(ctx)
    assert ctx.state["prd_final"] == "# PRD\n\n## 14. KPIs\nKPI-01"

    from agents.checkers import AnexoAprovadoAgent

    estado = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[
        AnexoAprovadoAgent(name="A", chave="prd_final", secoes=[10])]),
        {"prd_final": "```markdown\n# PRD\n\ncorpo\n```", "one_pager": "# OP\n\n## 10. Tempos\n29 min em tela\n"}))
    assert not estado["prd_final"].lstrip().startswith("```")
    assert estado["prd_final"].startswith("# PRD")


def test_writers_do_dev_desembrulham_a_saida():
    from agents.dev import get_one_pager_pedagogico_agent, get_prd_writer_agent

    for agente in (get_prd_writer_agent(), get_one_pager_pedagogico_agent()):
        assert agente.after_agent_callback is not None, agente.name


# --------------------------------------------------------------------------- banca de produto
def test_banca_de_produto_recebe_o_one_pager_antes_de_julgar():
    from agents.banca import get_banca

    produto = get_banca("produto", "AC", 45, rotulo="Banca de produto", titulo="t", report_key="r", status_key="s")
    assert produto[0].name == "A045ConteudoAprovado" and produto[1].name == "A046EscopoBanca"
    design = get_banca("design", "AB", 75, rotulo="Banca de design", titulo="t", report_key="r", status_key="s")
    assert design[0].name == "A075EscopoBanca", "no design o conteúdo aprovado já existe, com o retrato da etapa"


def test_pedido_do_po_que_retira_habilidade_vence_o_briefing_original():
    """exp06ef1b (08/10/2026): o briefing de 28/09 listava EF06CO07 como obrigatória; o PO pediu três vezes para tirá-la
    e ratificou («Descarte curricular de EF06CO07 — RATIFICADO … Remover a habilidade EF06CO07 de todos os documentos,
    incluindo a própria tag [PROPOSTA — validar com PO: tirar EF06CO07]»). O lint, lendo só o briefing, bloqueava o
    one-pager sem ela e mandava recolocar a tag — e ela voltava a cada refazer."""
    from tools.contrato_produto import validar_one_pager

    briefing = ("Gere uma missão para o 6 ano. As habilidades que devem ser trabalhadas, obrigatoriamente, são essas:\n"
                "EF06CO01\nEF06CO03\nEF06CO07\n")
    one_pager = ("# One-pager — exp06ef1b\n\n## 1. Descoberta central\nFoco primário: `EF06CO10`, com `EF06CO01` e "
                 "`EF06CO03`.\n\n## 2. Currículo\n- EF06CO01 — tipos de dados\n- EF06CO03 — regra condicional\n")
    pedido = ("Descarte curricular de EF06CO07 — RATIFICADO. Remover a habilidade EF06CO07 de todos os documentos de "
              "produto — incluindo a própria tag [PROPOSTA — validar com PO: tirar EF06CO07...] da Seção 18.")
    codigos = lambda r: {a["codigo"] for a in r["achados"]}  # noqa: E731
    assert "habilidade-do-briefing-sumiu" in codigos(validar_one_pager(one_pager, briefing=briefing))
    assert "habilidade-do-briefing-sumiu" not in codigos(validar_one_pager(one_pager, briefing=briefing, pedidos=pedido))
    # habilidade que nenhum pedido retirou continua cobrada
    sem_co01 = one_pager.replace("`EF06CO01` e ", "").replace("- EF06CO01 — tipos de dados\n", "")
    r = validar_one_pager(sem_co01, briefing=briefing, pedidos=pedido)
    assert any(a["codigo"] == "habilidade-do-briefing-sumiu" and "EF06CO01" in a["resumo"] for a in r["achados"])


# --------------------------------------------------------------------------- autor mudo (exp03ef1b, 08/10/2026)
def test_one_pager_vazio_reprova_a_conferencia_mesmo_sem_anexo_do_po():
    """O A014 terminou sem texto duas vezes; sem anexo do PO a conferência dizia «não se aplica» e o loop saía."""
    from tools import one_pager_po as op

    r = op.conferir("", "")
    assert r["status"] == "bloqueado" and r["achados"][0]["codigo"] == "one-pager-vazio"
    assert "ONE-PAGER VAZIO" in op.relatorio(r) and '"status": "bloqueado"' in op.relatorio(r)
    assert op.conferir("", "# One-pager")["status"] == "aprovado"


def test_documento_obrigatorio_para_a_etapa_com_mensagem_legivel():
    import pytest

    from agents.checkers import DocumentoAusente, DocumentoObrigatorioAgent

    guarda = DocumentoObrigatorioAgent(name="G", chave="one_pager", autor="A014SecoesApoio")
    with pytest.raises(DocumentoAusente, match="A014SecoesApoio terminou sem texto"):
        asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[guarda]), {"one_pager": ""}))
    guarda = DocumentoObrigatorioAgent(name="G", chave="one_pager", autor="A014SecoesApoio")
    assert asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[guarda]), {"one_pager": "# OP"}))["one_pager"] == "# OP"

    from agents.produto import build_produto_stage

    nomes = [a.name for a in build_produto_stage().sub_agents]
    assert nomes.index("SecoesApoioLoop") < nomes.index("A017OnePagerExiste") < nomes.index("GateEstruturalLoop")


def test_erro_de_variavel_ausente_vira_mensagem_que_o_po_le():
    from pipeline.runner import mensagem_de_erro

    msg = mensagem_de_erro(KeyError("Context variable not found: `one_pager` in agent 'A021GateEstrutural'."))
    assert "`one_pager`" in msg and "A021GateEstrutural" in msg and "terminou sem texto" in msg
    assert mensagem_de_erro(RuntimeError("outra coisa")) == "outra coisa"


def test_fidelidade_le_so_o_texto_do_pedido_e_nao_o_cabecalho_da_esteira():
    """exp06ef1b: o item F1 citava «Esta execução refaz a etapa produto…» como pedido do PO, e o mesmo pedido entrava
    duas vezes no checklist (o embrulho não casava com o texto registrado no parecer)."""
    from agents.checkers import _pedidos_de_produto
    from pipeline.reexecucao import PedidoCorrecao, texto_do_pedido

    texto = "Descarte curricular de EF06CO07 — RATIFICADO.\n\nRemover a habilidade EF06CO07 de todos os documentos."
    md = PedidoCorrecao(texto=texto).como_markdown("produto")
    assert texto_do_pedido(md) == texto and "Esta execução refaz" not in texto_do_pedido(md)
    assert texto_do_pedido("pedido solto") == "pedido solto"
    assert "Esta execução refaz" not in _pedidos_de_produto({"pedido_correcao": md})


def test_resposta_cortada_pelo_modelo_vai_a_proxima_tentativa_do_mesmo_agente():
    """exp03ef1b (08/10/2026): o A014 terminou com FinishReason.RECITATION e nenhum texto, duas vezes, com a mesma
    instrução. Reproduzido localmente sobre o estado salvo. Agora o motivo vai ao estado e à instrução seguinte."""
    from google.adk.models.llm_response import LlmResponse
    from google.genai import types

    from agents.base import create_llm_agent
    from agents.callbacks import registrar_corte_do_modelo

    class _Ctx:
        agent_name = "A014SecoesApoio"

        def __init__(self):
            self.state = {}

    ctx = _Ctx()
    cortada = LlmResponse(content=types.Content(role="model", parts=[]), finish_reason=types.FinishReason.RECITATION)
    registrar_corte_do_modelo(ctx, cortada)
    assert "filtro de recitação" in ctx.state["bloqueio_modelo_A014SecoesApoio"]
    ok = LlmResponse(content=types.Content(role="model", parts=[types.Part(text="# One-pager")]),
                     finish_reason=types.FinishReason.STOP)
    registrar_corte_do_modelo(ctx, ok)
    assert ctx.state["bloqueio_modelo_A014SecoesApoio"] == ""

    agente = create_llm_agent(name="A014SecoesApoio", instruction="x", description="d", output_key="one_pager")
    assert "{bloqueio_modelo_A014SecoesApoio?}" in agente.instruction
    assert agente.after_model_callback is registrar_corte_do_modelo


# --------------------------------------------------------------------------- mutação além da remoção
def test_mutacao_pega_troca_negacao_e_renomeacao_nao_so_remocao():
    """As 13 perdas do teste de mutação eram todas remoção. A auditoria de 08/10/2026 plantou as que passavam: palavra
    trocada no fim de um texto aprovado, "não" inserido, evento renomeado com sufixo, estado renomeado, fala do podcast
    com uma palavra trocada. Agora a matriz pega cada uma."""
    from test_conteudo_aprovado import _cadeia_completa
    from tools import rastreabilidade as rb

    base, reqs = _cadeia_completa()
    assert rb.matriz(base)["status"] == "aprovado", rb.matriz(base)["achados"]
    texto = {c: [r["texto"] for r in reqs if r["categoria"] == c] for c in rb.CATEGORIAS}

    def trocar(chave, de, para):
        assert de in base[chave], (chave, de[:60])
        return {**base, chave: base[chave].replace(de, para)}

    alt = texto["canal_b"][1]
    ultima = alt.rstrip(" .?!").split()[-1]
    fala = texto["podcast"][0]
    meio = fala.split()[len(fala.split()) // 2]
    pergunta = texto["roteiro"][-1]
    objeto = texto["evento"][0].split(" · ")[1]
    estado = texto["estado"][0]
    mutacoes = {
        "perdido-canal_b-copy": trocar("copy_strings_revisada", alt, alt.replace(ultima, "diferente", 1)),
        "perdido-roteiro-copy": trocar("copy_strings_revisada", pergunta,
                                       pergunta.replace(" ", " não ", 1)),
        "perdido-evento-handoff": trocar("handoff_dev", objeto, objeto + "_v2"),
        "perdido-estado-prd": {**base, "prd_final": base["prd_final"].replace(estado, estado + "_novo")},
        "perdido-podcast-copy": trocar("copy_strings_revisada", fala, fala.replace(meio, "qualquer", 1)),
    }
    perdidas = [n for n, e in mutacoes.items() if n not in {a["codigo"] for a in rb.matriz(e)["achados"]}]
    assert not perdidas, f"a matriz deixou passar: {perdidas}"


def test_literal_tolera_formatacao_mas_nao_troca_de_sentido():
    from tools import conteudo_aprovado as ca

    aprovado = "Apenas para a família e amigos próximos que você conhece de verdade."
    assert ca.literais_ausentes("**Apenas** para a família e amigos próximos que você conhece de verdade!", [aprovado]) == []
    assert ca.literais_ausentes("Apenas para a família e amigos próximos que você conhece de mentira.", [aprovado]) == [aprovado]
    assert ca.literais_ausentes("Não apenas para a família e amigos próximos que você conhece de verdade.", [aprovado]) == [aprovado]


# --------------------------------------------------------------------------- gates que aprovavam vazio
def test_gates_que_aprovavam_vazio_agora_reprovam():
    from tools import conteudo_aprovado as ca
    from tools import telas

    assert telas.cobertura({"jornada_telas": ""})["status"] == "bloqueado"
    jornada = _fixture_exp09("jornada.md")
    r = telas.cobertura({"jornada_telas": jornada, "fluxo_arestas": "", "copy_strings_revisada": "x",
                         "wireframes_cobertura": "x"})
    assert any(a["codigo"] == "derivado-vazio" and a["agente_responsavel"] == "fluxo" for a in r["achados"])
    one_pager = _fixture_exp09("one_pager.md")
    if any(ca.literais(one_pager).get(q) for q in ("canal_b", "roteiro", "podcast")):
        assert [a["codigo"] for a in ca.validar_copy("", one_pager)] == ["copy-vazia"]
    if ca.literais(one_pager)["podcast"]:
        assert [a["codigo"] for a in ca.validar_banco("", one_pager)] == ["banco-vazio"]


# --------------------------------------------------------------------------- handoff → PRD e PRD → pedagógico
def test_handoff_no_prd_tabela_e_evento_nao_somem_sem_registro():
    from tools.prd_codavel import handoff_no_prd

    handoff = ("CREATE TABLE exp06ef1b_sessoes (id UUID);\nCREATE TABLE exp06ef1b_reflexoes (id UUID);\n"
               "| Verbo | Objeto |\n|---|---|\n| interacted | `voto:cravar` |\n| completed | `missao:concluir` |\n"
               "POST /exp06ef1b/turmas/:turmaId/zerar\n")
    prd = "exp06ef1b_sessoes · `voto:cravar` · POST /exp06ef1b/turmas/:turmaId/zerar"
    codigos = {a["codigo"] for a in handoff_no_prd(prd, handoff)}
    assert codigos == {"tabela-do-handoff-perdida", "evento-do-handoff-perdido"}
    registrado = prd + "\n\n# 19. Decisões\n`exp06ef1b_reflexoes` e `missao:concluir` saem: divergência com o handoff, dono produto.\n"
    # registrar na seção 19 é texto do modelo: tira do bloqueio, mas fica 🟡 para o PO (plano padrão ouro, 2.8)
    assert [(a["codigo"], a["severidade"]) for a in handoff_no_prd(registrado, handoff)] == [
        ("divergencia-do-handoff-registrada", "atencao")]
    rota = handoff_no_prd(prd.replace("POST /exp06ef1b/turmas/:turmaId/zerar", "DELETE /exp06ef1b/turmas/:turmaId")
                          + "\n# 19. Decisões\nexp06ef1b_reflexoes missao:concluir\n", handoff)
    assert sorted(a["codigo"] for a in rota) == ["divergencia-do-handoff-registrada", "rota-do-handoff-mudou"]
    assert all(a["severidade"] == "atencao" for a in rota)


def test_pedagogico_tem_juiz_de_contradicoes():
    from agents.dev import agentes_em_ordem, build_dev_stage

    loop = next(a for a in agentes_em_ordem(build_dev_stage()) if a.name == "OnePagerPedagogicoLoop")
    nomes = [a.name for a in loop.sub_agents]
    assert nomes.index("A112CoerenciaPedagogico") < nomes.index("A113PedagogicoRodada")
    assert "coerencia_pedagogico_status" in loop.sub_agents[-1].status_keys


# --------------------------------------------------------------------------- citação conferida nos gates de LLM
def _relatorio(achados, status="bloqueado"):
    import json

    return "# Gate\n\n**Veredito: 🔴**\n\n```json\n" + json.dumps({"status": status, "achados": achados}, ensure_ascii=False) + "\n```"


def test_gate_de_llm_so_bloqueia_com_citacao_que_existe():
    from agents.checkers import EnvelopeGateAgent

    one_pager = "## 4. Etapas\nO estudante escolhe o projeto campeão e o voto fica travado depois de confirmar."

    def rodar(achados):
        gate = EnvelopeGateAgent(name="G", rotulo="Gate", report_key="r", status_key="s", block_pipeline_on_fail=False,
                                 documentos=["one_pager"])
        return asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[gate]), {"r": _relatorio(achados), "one_pager": one_pager}))

    inventada = [{"severidade": "bloqueio", "codigo": "X", "resumo": "voto destravável",
                  "citacao": "o estudante pode trocar o voto a qualquer momento antes do resultado"}]
    final = rodar(inventada)
    assert final["s"] == "amarelo" and final["s_envelope"]["achados"][0]["citacao_nao_confere"]
    assert "Citação conferida em código" in final["r"]

    verdadeira = [{"severidade": "bloqueio", "codigo": "X", "resumo": "sem retorno",
                   "citacao": "o voto fica travado depois de confirmar"}]
    assert rodar(verdadeira)["s"] == "bloqueado"
    sem_citacao = [{"severidade": "bloqueio", "codigo": "X", "resumo": "falta a tela de erro"}]
    assert rodar(sem_citacao)["s"] == "bloqueado", "ausência de citação não rebaixa (cautela)"
    misto = inventada + verdadeira
    assert rodar(misto)["s"] == "bloqueado", "sobrou um bloqueio comprovado"


def test_banca_rebaixa_nok_com_citacao_inventada():
    from tools import banca as bnc

    bloqueante = sorted(bnc.todos_bloqueantes())[0]
    env = {"status": "bloqueado", "contagem": {"nok_bloqueantes": 1},
           "achados": [{"codigo": bloqueante, "severidade": "nok", "resumo": "x",
                        "citacao": "uma frase que não está em lugar nenhum do documento avaliado"}]}
    import copy

    assert bnc.consolidar({"d": copy.deepcopy(env)})["status"] == "bloqueado"
    assert bnc.consolidar({"d": copy.deepcopy(env)}, "## Spec\nO estudante vota uma vez.")["status"] == "amarelo"


def test_gates_de_llm_pedem_citacao_e_sabem_o_que_avaliam():
    from agents.design import build_design_stage
    from agents.produto import build_produto_stage
    from pipeline.orchestrator import iter_agent_tree  # noqa: F401  (só garante que o módulo carrega)
    from prompts import load_prompt

    for p in ("produto/007_micro_gate.md", "produto/021_gate_estrutural.md", "produto/033_gate_final.md",
              "design/078_qa_entregaveis.md", "dev/validacao_produto_narrativa.md"):
        assert "o código confere" in load_prompt(p).lower(), p

    def todos(a):
        yield a
        for s in getattr(a, "sub_agents", []) or []:
            yield from todos(s)

    gates = {a.name: a for raiz in (build_produto_stage(), build_design_stage()) for a in todos(raiz)
             if type(a).__name__ == "EnvelopeGateAgent"}
    for nome in ("A012MicroGateCheck", "A022GateEstruturalCheck", "A025AvaliacaoCheck", "A027AdequacaoCheck",
                 "A034GateFinalProdutoCheck", "A042JuizPerguntasCheck", "A080QaEntregaveisCheck"):
        assert gates[nome].documentos, nome


def test_falsos_positivos_achados_no_prd_gerado_ao_vivo():
    """Dev da exp09ef1b reexecutado localmente com o código novo (08/10/2026): o PRD saiu passando em tudo menos em dois
    achados que eram do gate — o prompt escrito como a constante do `prompts.ts` e o rótulo «Ainda não:» do pedagógico."""
    from test_prd_codavel import PRD, PROMPT, SPEC
    from tools import conteudo_aprovado as ca
    from tools import prd_codavel as pc

    em_ts = PRD.replace(f"```text\n{PROMPT}\n```", f"```typescript\n// prompts.ts\nexport const PROMPT_PREPARO = `\n{PROMPT}\n`;\n```")
    assert "ia-sem-prompt" not in {a["codigo"] for a in pc.validar(em_ts, SPEC)["achados"]}
    alt = "Descartar o uso de computadores e decidir exclusivamente pela intuição pessoal."
    assert ca.literais_ausentes(f"Ainda não: {alt} Para a compreensão…", [alt]) == []
    assert ca.literais_ausentes(f"Não atingiu: {alt}", [alt]) == []
    assert ca.literais_ausentes(f"Não {alt.lower()}", [alt]) == [alt]


def test_secao_legada_escolhida_pelo_po_nao_bloqueia():
    """Seção legada é bloqueio — salvo quando o PO a fixou no one-pager que anexou ou no briefing: a decisão é dele."""
    from tools.rastro import validar_manifesto

    spec = ("## 0. Ficha\n- id: exp06ef1b\n- secao_ds: instanooria\n- produto: entre-redes\n")
    def sev(r):
        return [a["severidade"] for a in r["achados"] if a.get("campo") == "secao_ds"]
    assert sev(validar_manifesto(spec)) == ["bloqueio"]
    assert sev(validar_manifesto(spec, one_pager_po="# One-pager\n- **Seção do DS:** `instanooria`\n")) == ["atencao"]
    assert sev(validar_manifesto(spec, briefing="secao_ds: instanooria")) == ["atencao"]
    assert sev(validar_manifesto(spec, one_pager_po="- **Seção do DS:** `unoovista`")) == ["bloqueio"]


# --------------------------------------------------------------------------- fidelidade em unidades atômicas
PARECER_NUMERADO = """Fechamento de todas as pendências abertas — exp06ef1b

Resolver cada ponto abaixo no corpo dos documentos. Não alterar narrativa, mecanismo das 6 etapas nem estrutura de telas.

1. Cenário de dispositivos (Seção 13): Não prescrever protocolo de revezamento de papéis. Substituir qualquer menção a rodízio por: “O arranjo é definido pela escola. A mecânica funciona igual.” Remover as tags [PROPOSTA] relacionadas a revezamento em todos os documentos.
2. Habilidade complementar EF67LP08: Remover a habilidade EF67LP08 de todos os documentos de produto. A conferência em fonte oficial não foi realizada e a missão não depende dela.
3. Perguntas de Produto: Trocar o marcador [PROPOSTA — validar com PO] de cada uma por [HOMOLOGADO pelo PO].

Não alterar mais nada. Todos os itens anteriormente homologados (tempo em tela de 29 min) permanecem como estão.
"""


def test_parecer_numerado_vira_unidades_atomicas_e_literais():
    """O parecer de 8 pontos da exp06ef1b (08/10/2026) virava um item só e a fidelidade saía 🔴 com tudo aplicado."""
    from tools import fidelidade as fid

    itens = fid.itens_do_pedido(PARECER_NUMERADO, "pedido")
    textos = [i["texto"] for i in itens]
    # nada inventado: cada unidade (sem o rótulo) está no pedido, letra por letra
    for t in textos:
        assert t.split(") ", 1)[-1] in PARECER_NUMERADO.replace("\n", " "), t
    # nada agrupado: as três exigências do item 1 são três itens, e a frase depois das aspas não gruda nelas
    do_item_1 = [t for t in textos if t.startswith("(item 1)")]
    assert len(do_item_1) == 3 and any(t.endswith("Remover as tags [PROPOSTA] relacionadas a revezamento em todos os documentos.")
                                       for t in do_item_1)
    # trava curta é item próprio, e o parágrafo depois da lista não herda o rótulo do último item
    assert {"tipo": "trava", "texto": "Não alterar mais nada."}.items() <= next(i for i in itens if "mais nada" in i["texto"]).items()
    assert not any(t.startswith("(item 3) Todos os itens") for t in textos)
    # o teto de itens de pedido não corta um parecer longo
    assert len(fid.montar_checklist([("pedido", PARECER_NUMERADO)], "")) == len(itens)


def test_juiz_so_dispensa_como_contexto_o_que_nao_e_exigencia():
    import json

    from tools import fidelidade as fid

    itens = [{"id": "F1", "origem": "pedido", "tipo": "pedido", "texto": "Fechamento de todas as pendências abertas — exp06ef1b"},
             {"id": "F2", "origem": "pedido", "tipo": "pedido", "texto": "Resolver cada ponto abaixo no corpo dos documentos."},
             {"id": "F3", "origem": "pedido", "tipo": "pedido", "texto": "Remover a habilidade EF67LP08 de todos os documentos."}]
    saida = "```json\n" + json.dumps({"decisoes": [{"id": i, "veredito": "contexto"} for i in ("F1", "F2", "F3")]}) + "\n```"
    r = fid.aplicar(itens, saida, {"one_pager": "# One-pager\nNada aqui."})
    assert [a["codigo"] for a in r["achados"]] == ["exigencia-dispensada"] and "EF67LP08" in r["achados"][0]["resumo"]


def test_formato_misto_bloco_e_lista_solta_sao_conferidos_inteiros():
    """Com um bloco TRAVAS e uma lista numerada fora dele, só o bloco virava item — e o TRAVAS engolia a lista."""
    from tools import fidelidade as fid

    texto = ("TRAVAS: a frase da descoberta fica como está, sem nenhuma mudança.\n\n"
             "1. Remover a habilidade EF67LP08 de todos os documentos.\n"
             "2. Adicionar a nota pedagógica ao guia do professor.\n")
    itens = [(i["tipo"], i["texto"]) for i in fid.itens_do_pedido(texto, "pedido")]
    assert ("trava", "a frase da descoberta fica como está, sem nenhuma mudança.") in itens
    assert ("pedido", "(item 1) Remover a habilidade EF67LP08 de todos os documentos.") in itens
    assert ("pedido", "(item 2) Adicionar a nota pedagógica ao guia do professor.") in itens


def test_fidelidade_do_nucleo_e_parcial_so_violacao_bloqueia():
    """exp06ef1b (08/10/2026): o fim de produto saía 🟢 25/25, e o núcleo 🔴 por itens das seções 9 e 17, que ele não tem."""
    from agents.produto import build_produto_stage
    from tools import fidelidade as fid

    itens = [{"id": "F1", "origem": "pedido", "tipo": "pedido", "texto": "Explicitar o painel docente na Seção 9."}]
    saida = '```json\n{"decisoes":[{"id":"F1","veredito":"nao_tratado"}]}\n```'
    assert fid.aplicar(itens, saida, {"n": "núcleo"}, parcial=True)["status"] != "bloqueado"
    assert fid.aplicar(itens, saida, {"n": "núcleo"})["status"] == "bloqueado"
    violado = '```json\n{"decisoes":[{"id":"F1","veredito":"violado","citacao":"x"}]}\n```'
    assert fid.aplicar(itens, violado, {"n": "núcleo"}, parcial=True)["status"] == "bloqueado"

    def todos(a):
        yield a
        for s in getattr(a, "sub_agents", []) or []:
            yield from todos(s)
    nucleo = next(a for a in todos(build_produto_stage()) if a.name == "A010FidelidadeNucleo")
    fim = next(a for a in todos(build_produto_stage()) if a.name == "A050FidelidadeProduto")
    assert nucleo.parcial and not fim.parcial


def test_split_tira_a_moldura_do_agente_e_a_preservacao_nao_faz_ping_pong():
    """exp06ef1b (09/10/2026): a frase de abertura do D0 entrava na spec e o D9 era cobrado por não repeti-la."""
    from agents.checkers import documento_sem_moldura
    from tools.preservacao import linhas_perdidas

    corpo = "# Spec — Missão\n\n## 0. Identificação\nO estudante atua como jurado da mostra estadual.\n\n```json\n{\"a\": 1}\n```\n"
    d0 = ("Abaixo segue a especificação técnica consolidada, preservando integralmente os Blocos 0 a 12:\n\n"
          f"```markdown\n{corpo}```\n\n---")
    d9 = f"Segue a spec consolidada com a adição do Bloco 14, sem mudar os blocos anteriores:\n\n```markdown\n{corpo}```"
    assert documento_sem_moldura(d0).startswith("# Spec") and documento_sem_moldura(d0).endswith("```")
    assert "Abaixo segue" not in documento_sem_moldura(d0)
    assert linhas_perdidas(documento_sem_moldura(d0), documento_sem_moldura(d9)) == []
    # sem moldura, ou com título antes da cerca, o texto fica como está
    assert documento_sem_moldura(corpo) == corpo
    com_titulo = "## Passo 4\n\n```markdown\n# Spec\n```"
    assert documento_sem_moldura(com_titulo) == com_titulo


def test_prototipo_pede_cada_pergunta_do_canal_b_em_quadro_e_sem_gabarito():
    from prompts import load_prompt

    p = load_prompt("design/069_prototipo.md")
    assert "um quadro\npor item" in p or "um quadro por item" in p.replace("\n", " ")
    assert "sem o rótulo de nível" in p


def test_estados_da_spec_nao_contam_o_gatilho_em_snake_case():
    """exp06ef1b (09/10/2026): `estado · gatilho · regra · estado seguinte` — o gatilho `confirmar_voto` virava estado."""
    from tools import cobertura_design as cd

    spec = ("## 2. Mecânica\n\n### Contrato de estados — obrigatório\n\n```\n"
            "E3_DECIDINDO · confirmar_voto · selecionou projeto · E3_LATCH_ESPERA · estudante · não\n"
            "QUALQUER_ESTADO · midia_falhou · erro 404 · PLACEHOLDER_DIEGETICO · sistema · não\n"
            "e1_desafio_aberto · toque · slot_count == 3 · e2_mesa_livre · estudante · não\n```\n")
    estados = cd.estados_da_spec(spec)
    assert "confirmar_voto" not in estados and "midia_falhou" not in estados and "toque" not in estados
    assert {"E3_DECIDINDO", "E3_LATCH_ESPERA", "PLACEHOLDER_DIEGETICO", "e1_desafio_aberto", "e2_mesa_livre"} <= set(estados)


def test_prototipo_mostra_distratores_de_toda_escolha():
    from prompts import load_prompt

    assert "distratores" in load_prompt("design/069_prototipo.md")


def test_listagem_do_stitch_segue_paginas_e_busca_por_id_o_que_faltou(monkeypatch):
    """exp06ef1b (09/10/2026): o `list_screens` voltou parcial e o Stitch saiu 🔴 com telas que existiam."""
    from tools import stitch_cliente as sc

    def tela(i, titulo):
        return {"name": f"projects/p/screens/{i}", "title": titulo}

    chamadas = []

    def falso(ferramenta, args, timeout=180):
        chamadas.append((ferramenta, args))
        if ferramenta == "list_screens":
            if not args.get("pageToken"):
                return {"screens": [tela("a" * 32, "A"), tela("d" * 32, "DESIGN.md")], "nextPageToken": "t2"}
            return {"screens": [tela("b" * 32, "B")]}
        if ferramenta == "get_screen":
            i = args["name"].rsplit("/", 1)[-1]
            return tela(i, "C") if i == "c" * 32 else {}
        raise AssertionError(ferramenta)

    monkeypatch.setattr(sc, "chamar", falso)
    telas = sc.listar_telas("p", ["a" * 32, "C" * 32, "e" * 32])
    assert [t["id"] for t in telas] == ["a" * 32, "b" * 32, "c" * 32]
    # só o que a listagem não trouxe vai ao get_screen
    assert [a["name"].rsplit("/", 1)[-1] for f, a in chamadas if f == "get_screen"] == ["c" * 32, "e" * 32]


def test_afirmacao_do_qa_conta_telas_e_nao_estados_nem_grupo_nomeado():
    """exp06ef1b (09/10/2026): «22 de 22 telas (38 estados)» contra 30 linhas, e «as 5 telas do preparo» contra o projeto."""
    from tools import afirmacoes as af

    ids = ["E0-PROF-01", "E0-PROF-02", "E1-ALU-01"]
    jornada = "## Seção 3\n\n| ID | Tela | Estados |\n|---|---|---|\n" + "\n".join(f"| {i} | t | padrão |" for i in ids)
    folha = "| Tela | Dispositivo |\n|---|---|\n" + "\n".join(
        f"| {i} — {e} | DESKTOP |" for i in ids for e in ("normal", "erro"))
    qa = ("- A contagem no Stitch fecha com **3 de 3 telas** do inventário (6 estados).\n"
          "| D6 | ✅ | Todas as 2 telas do preparo `E0-PROF-01` a `02` construídas no Stitch. |\n")
    r = af.conferir_qa(qa, folha, jornada, "")
    assert not [a for a in r["achados"] if a["codigo"].startswith("afirmacao-stitch")], r["achados"]


def test_ordem_de_nao_mexer_sem_citacao_e_atencao_e_violacao_bloqueia():
    """exp06ef1b (10/10/2026): «Não alterar spec, telas, fluxo, copy nem protótipo» não tem trecho que prove ausência de mudança."""
    from tools import fidelidade as fid

    assert fid.so_preservacao("Não alterar spec, telas, fluxo, copy nem protótipo;")
    assert fid.so_preservacao("O one-pager, a spec e o resumido devem permanecer exatamente como estão.")
    assert fid.so_preservacao("as telas do Stitch já existem e não devem ser geradas de novo.")
    assert not fid.so_preservacao("Manter a narrativa e trocar o título da Etapa 2.")
    assert not fid.so_preservacao("Remover a habilidade EF67LP08 de todos os documentos.")

    itens = [{"id": "F1", "origem": "pedido", "tipo": "pedido", "texto": "Não alterar spec, telas, fluxo, copy nem protótipo;"}]
    citou = '```json\n{"decisoes":[{"id":"F1","veredito":"atendido","citacao":"Não alterar spec, telas, fluxo, copy nem protótipo;"}]}\n```'
    r = fid.aplicar(itens, citou, {"d": "documento sem a frase"}, etapa="design")
    assert r["status"] == "amarelo" and r["achados"][0]["codigo"] == "preservacao-sem-citacao"
    violou = '```json\n{"decisoes":[{"id":"F1","veredito":"violado","citacao":"x"}]}\n```'
    assert fid.aplicar(itens, violou, {"d": "documento"}, etapa="design")["status"] == "bloqueado"


def test_prd_que_segue_a_plataforma_e_registra_nao_bloqueia_por_tipo_da_spec():
    """Plano Padrão Ouro (item 1 e 2 da Etapa 2):
    - A spec não dita DDL SQL: tipos da spec não bloqueiam o PRD.
    - Coluna de plataforma (`turma_id UUID`) é validada diretamente contra a plataforma (sem válvula de escape textual).
    - Coluna da spec não declarada no PRD gera atenção `coluna-da-spec-ausente`.
    """
    from tools.consistencia import conferir_colunas

    spec = 'CREATE TABLE "exp06ef1b_sessoes" (\n  turma_id VARCHAR(64) NOT NULL,\n  assuntos JSONB NOT NULL\n);'
    prd = 'CREATE TABLE "exp06ef1b_sessoes" (\n  "turma_id" UUID NOT NULL,\n  "assuntos" TEXT NOT NULL\n);'
    achados = conferir_colunas(prd, spec)
    # turma_id UUID segue a plataforma (UUID), assuntos TEXT não é da plataforma e a spec não impõe tipo DDL
    assert not [a for a in achados if a["severidade"] == "bloqueio"]
    # Se a spec tiver coluna que o PRD não tem, acusa atenção coluna-da-spec-ausente
    spec_com_extra = 'CREATE TABLE "exp06ef1b_sessoes" (\n  turma_id VARCHAR(64) NOT NULL,\n  assuntos JSONB NOT NULL,\n  coluna_faltando INT NOT NULL\n);'
    achados_extra = conferir_colunas(prd, spec_com_extra)
    assert any(a["codigo"] == "coluna-da-spec-ausente" for a in achados_extra)


def test_regra_da_ficha_le_coluna_jsonb_de_uma_palavra():
    """`auditoria: abertos >= 2` lê a coluna `auditoria` (JSONB); o check só via nomes com sublinhado."""
    from tools import prd_codavel as pc

    prd = ("## 11. Dados\n```sql\nCREATE TABLE \"exp06ef1b_sessoes\" (\n  \"auditoria\" JSONB NOT NULL\n);\n```\n\n"
           "## 14. Evidência\n| Habilidade | Marcador | Tipo | Pergunta | Regra |\n|---|---|---|---|---|\n"
           "| EF06CO10 | m1 | acao | — | `auditoria: abertos >= 2 AND buscas >= 1 → atingiu` |\n")
    achados = []
    pc._ficha(prd, "", achados)
    assert not [a for a in achados if a["codigo"] == "regra-sem-coluna"], achados
