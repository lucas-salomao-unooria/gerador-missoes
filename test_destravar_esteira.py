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

    produto = get_banca("produto", "AC", "A15h", rotulo="Banca de produto", titulo="t", report_key="r", status_key="s")
    assert produto[0].name == "A15hConteudoAprovado" and produto[1].name == "A15hEscopoBanca"
    design = get_banca("design", "AB", "A29f", rotulo="Banca de design", titulo="t", report_key="r", status_key="s")
    assert design[0].name == "A29fEscopoBanca", "no design o conteúdo aprovado já existe, com o retrato da etapa"


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
    """O A04 terminou sem texto duas vezes; sem anexo do PO a conferência dizia «não se aplica» e o loop saía."""
    from tools import one_pager_po as op

    r = op.conferir("", "")
    assert r["status"] == "bloqueado" and r["achados"][0]["codigo"] == "one-pager-vazio"
    assert "ONE-PAGER VAZIO" in op.relatorio(r) and '"status": "bloqueado"' in op.relatorio(r)
    assert op.conferir("", "# One-pager")["status"] == "aprovado"


def test_documento_obrigatorio_para_a_etapa_com_mensagem_legivel():
    import pytest

    from agents.checkers import DocumentoAusente, DocumentoObrigatorioAgent

    guarda = DocumentoObrigatorioAgent(name="G", chave="one_pager", autor="A04SecoesApoio")
    with pytest.raises(DocumentoAusente, match="A04SecoesApoio terminou sem texto"):
        asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[guarda]), {"one_pager": ""}))
    guarda = DocumentoObrigatorioAgent(name="G", chave="one_pager", autor="A04SecoesApoio")
    assert asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[guarda]), {"one_pager": "# OP"}))["one_pager"] == "# OP"

    from agents.produto import build_produto_stage

    nomes = [a.name for a in build_produto_stage().sub_agents]
    assert nomes.index("SecoesApoioLoop") < nomes.index("A04fOnePagerExiste") < nomes.index("GateEstruturalLoop")


def test_erro_de_variavel_ausente_vira_mensagem_que_o_po_le():
    from pipeline.runner import mensagem_de_erro

    msg = mensagem_de_erro(KeyError("Context variable not found: `one_pager` in agent 'A05GateEstrutural'."))
    assert "`one_pager`" in msg and "A05GateEstrutural" in msg and "terminou sem texto" in msg
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
    """exp03ef1b (08/10/2026): o A04 terminou com FinishReason.RECITATION e nenhum texto, duas vezes, com a mesma
    instrução. Reproduzido localmente sobre o estado salvo. Agora o motivo vai ao estado e à instrução seguinte."""
    from google.adk.models.llm_response import LlmResponse
    from google.genai import types

    from agents.base import create_llm_agent
    from agents.callbacks import registrar_corte_do_modelo

    class _Ctx:
        agent_name = "A04SecoesApoio"

        def __init__(self):
            self.state = {}

    ctx = _Ctx()
    cortada = LlmResponse(content=types.Content(role="model", parts=[]), finish_reason=types.FinishReason.RECITATION)
    registrar_corte_do_modelo(ctx, cortada)
    assert "filtro de recitação" in ctx.state["bloqueio_modelo_A04SecoesApoio"]
    ok = LlmResponse(content=types.Content(role="model", parts=[types.Part(text="# One-pager")]),
                     finish_reason=types.FinishReason.STOP)
    registrar_corte_do_modelo(ctx, ok)
    assert ctx.state["bloqueio_modelo_A04SecoesApoio"] == ""

    agente = create_llm_agent(name="A04SecoesApoio", instruction="x", description="d", output_key="one_pager")
    assert "{bloqueio_modelo_A04SecoesApoio?}" in agente.instruction
    assert agente.after_model_callback is registrar_corte_do_modelo
