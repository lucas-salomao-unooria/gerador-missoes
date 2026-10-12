"""Reanálise de 07/10/2026 (noite): o que do one-pager aprovado chega a cada agente, e as conferências novas.

Cada teste reproduz, em miniatura, uma lacuna achada nas 15 sessões do bucket ou na leitura do código: o §4 sem
proteção, o conteúdo aprovado do dev sem §8/§13/núcleo, o resumido sem conferência, o parâmetro do PO decidido pela
spec, o PRD ancorado na spec, a spec do D0 sem reconferência, a matriz cega a estados, a base velha depois de refazer
produto, a fidelidade só em produto, a devolutiva perdida no repasse e o orçamento da banca.
"""

import asyncio
import json

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions

from test_conteudo_aprovado import (
    ARTEFATOS, FIXTURES, ONE_PAGER, ONE_PAGER_LITERAIS, _codigos, _prd, _rodar, _spec,
)
from tools import conteudo_aprovado as ca

S4 = """## 4. As 6 etapas — mecanismo, não intenção

### Etapa 1: Desafiar
- **O que o estudante vê:** Nina pergunta: *"Antes de abrir as fotos, o que você acha que aconteceu no pátio?"*
- [A] "Um monstro assustador atacou e quebrou tudo na escola." (Crença do boato)
- [B] "Alguém inventou uma mentira de propósito para assustar todo mundo."
- **Quem conduz:** o professor pergunta: "Quem aqui já viu um boato assim na escola?"
- **Regra do sistema:** define `caminho = "B"` e segue.
- Se o estudante perguntar algo (ex.: "Por que a foto está borrada no canto?"), a IA responde.

### Etapa 4: Resultado / Aha
- Balão de Nina: "Uau! Não teve bagunça nenhuma quando a gente separou as pistas!"
- **Mediação:** "Turma, olhem para a fita que se formou na tela de vocês."
- Botão "OK".

### Evidência do foco primário (Regra 17)
| `EF03CO08` | B | **Pergunta:** "Qual frase é verdadeira sobre o que aconteceu no pátio?" |
"""
ONE_PAGER_S4 = "# One-pager — O Mistério do Pátio v1\n\n" + S4 + "\n## 5. Verificação de ambiente\nNada.\n"


# --------------------------------------------------------------------------- §4: o texto que a tela mostra
def test_textos_de_tela_do_4_e_o_que_fica_de_fora():
    """A pergunta da aposta, as alternativas e a fala da personagem entram; fala do professor em sala, exemplo do
    que o estudante diria, aspas de código e o bloco de evidência (o Canal B tem conferência própria) ficam fora."""
    assert ca.textos_de_tela(ONE_PAGER_S4) == [
        "Antes de abrir as fotos, o que você acha que aconteceu no pátio?",
        "Um monstro assustador atacou e quebrou tudo na escola.",
        "Alguém inventou uma mentira de propósito para assustar todo mundo.",
        "Uau! Não teve bagunça nenhuma quando a gente separou as pistas!",
    ]
    assert ca.literais(ONE_PAGER_S4)["texto_tela"] == ca.textos_de_tela(ONE_PAGER_S4)
    # a missão real do 9º ano: botões, títulos, mensagens da IA e o caso de transferência
    assert len(ca.textos_de_tela((FIXTURES / "one_pager.md").read_text(encoding="utf-8"))) == 17


def test_aspas_curtas_nao_emparelham_com_a_seguinte_e_sub_item_oral_fica_fora():
    """Auditoria do PR #32: «"Ontem" (que ficou guardada) e a lista de "Hoje"» virava texto de tela, e a fala do
    professor num sub-item da «Mediação do professor:» escapava do filtro de linha oral."""
    op = ("# OP\n\n## 4. Etapas\n\n### Etapa 1: Desafiar\n"
          '- **O que o estudante vê:** a lista de "Ontem" (que ficou guardada) e a lista de "Hoje".\n'
          "- **Mediação do professor:**\n"
          '  * "Quem aqui escolheu a capa com o susto?"\n'
          '- Balão de Nina: "Uau! Não teve bagunça nenhuma aqui hoje!"\n')
    assert ca.textos_de_tela(op) == ["Uau! Não teve bagunça nenhuma aqui hoje!"]


def test_correcoes_da_auditoria_do_pr_32():
    # o mesmo número em outro assunto não bloqueia: fica 🟡 para o PO conferir
    op = ONE_PAGER + "\n## 8. Estados de falha\n- Inatividade: dica após `[PARÂMETRO — a definir por produto: tempo de inatividade de 45 segundos]`.\n"
    audio = _spec() + "\n- O áudio de encerramento dura 45 segundos.\n"
    achado = next(a for a in ca.validar_spec(audio, op)["achados"] if a["codigo"] == "parametro-decidido")
    assert achado["severidade"] == "atencao"
    inatividade = _spec() + "\n- Inatividade: após 45 segundos sem interação, a dica aparece.\n"
    achado = next(a for a in ca.validar_spec(inatividade, op)["achados"] if a["codigo"] == "parametro-decidido")
    assert achado["severidade"] == "bloqueio"

    # o Canal B parafraseado no resumido é 🟡: não recusa o de acordo de produto
    r = ca.validar_resumido("## 2. Componente\n`EF01CO01`\nA criança escolhe por que as fotos combinam.",
                            "## 11. Currículo\n`EF01CO01`\n", ONE_PAGER_LITERAIS)
    assert r["status"] == "amarelo" and _codigos(r) == ["canal-b-reescrito"]

    # código do one-pager fora da lista oficial: manda o gate BNCC, a referência volta à spec
    invalido = ONE_PAGER.replace("`EF06CO07` | A + B", "`EF06CO99` | A + B")
    assert ca.habilidades_de_referencia(_spec(), invalido)[1] == "o bloco 11 da spec"
    # sem §12a, o rótulo diz §2
    so_curriculo = "# One-pager\n\n## 2. Currículo\n- Foco: `EF06CO10`.\n"
    assert ca.habilidades_de_referencia(_spec(), so_curriculo) == (["EF06CO10"], "o currículo do one-pager aprovado (§2)")

    # piora nova do D0 aparece mesmo com outra divergência do mesmo tipo já na spec do Gate 0
    op2 = op + "- Handoff: quando `[PARÂMETRO — a definir por produto: patamar de 80% da turma]` concluir.\n"
    gate0 = inatividade
    consolidada = gate0 + "\n- Handoff: o painel avisa quando 80% da turma concluir.\n"
    novos = ca.validar_spec_consolidada(consolidada, gate0, op2)["achados"]
    assert [a["codigo"] for a in novos] == ["parametro-decidido"] and "80%" in novos[0]["resumo"]


def test_pedido_corrente_so_conta_na_etapa_em_que_a_correcao_comecou():
    from agents.checkers import FidelidadeCheckAgent
    from pipeline.reexecucao import preparar_estado

    estado = {"pedidos_do_po": [], "briefing": "", "copy_strings_revisada": "a copy",
              "pedido_correcao": "AJUSTE 1 — o botão da tela E3-ALU-02 diz Enviar a minha resposta agora"}

    def origens(etapa_da_correcao):
        f = FidelidadeCheckAgent(name="F", status_key="f_status", report_key="f_report",
                                 documentos=["copy_strings_revisada"], etapas_pedido=["design"], com_briefing=False,
                                 incluir_corrente=False, etapa="design")
        final = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[f]),
                                   {**estado, "etapa_da_correcao": etapa_da_correcao}))
        return {a["origem"] for a in final["f_status_envelope"]["achados"]}

    assert origens("design") == {"pedido de correção desta execução"}, "a correção pela triagem é conferida no design"
    assert origens("produto") == set(), "a correção de produto não é cobrada do design"
    limpo, _ = preparar_estado({"one_pager": "x"}, "design", "corrija o botão")
    assert limpo["etapa_da_correcao"] == "design"
    assert "etapa_da_correcao" not in preparar_estado({**limpo}, "dev")[0]

    from agents.design import build_design_stage
    from agents.dev import agentes_em_ordem, build_dev_stage

    assert build_design_stage().sub_agents[-1].incluir_corrente is False
    assert agentes_em_ordem(build_dev_stage())[-1].incluir_corrente is False


def test_copy_sem_o_texto_de_tela_fica_amarela_e_a_proposta_conta():
    tela = ca.textos_de_tela(ONE_PAGER_S4)
    assert ca.validar_copy("\n".join(tela), ONE_PAGER_S4) == []
    so_um = ca.validar_copy(tela[0], ONE_PAGER_S4)
    assert [(a["codigo"], a["severidade"], a["agente_responsavel"]) for a in so_um] == [
        ("texto-de-tela-reescrito", "atencao", "copy-ptbr-revisao")]
    # a proposta que cita o texto aprovado entre aspas conta: o PO vê as duas redações e decide
    proposta = "\n".join(tela[1:]) + f"\n[PROPOSTA — validar com PO: «{tela[0]}» → «O que houve no pátio?» · teto de palavras]"
    assert ca.validar_copy(proposta, ONE_PAGER_S4) == []


def test_design_e_dev_recebem_o_nucleo_e_o_banco_nao_le_o_nucleo_antigo():
    from agents.design import build_design_stage
    from agents.dev import agentes_em_ordem, build_dev_stage
    from prompts import load_prompt

    assert {1, 3, 4, 8, 13} <= set(ca.SECOES_DESIGN)
    design, dev = build_design_stage().sub_agents[0], agentes_em_ordem(build_dev_stage())[0]
    assert design.secoes == list(ca.SECOES_DESIGN) and dev.name == "A33aConteudoAprovadoDev"
    # o dev regravava a chave só com as seções do PRD: banca e retrabalhos de design perdiam §8, §13 e o núcleo
    assert dev.secoes == list(ca.SECOES_DESIGN)
    banco = load_prompt("dev/35b_banco_conteudo.md")
    assert "{nucleo_narrativo" not in banco and "{conteudo_aprovado?}" in banco
    for prompt in ("design/24_copy_ptbr.md", "design/27_copy_revisao.md"):
        assert "§4" in load_prompt(prompt) and "PROPOSTA — validar com PO: «texto aprovado»" in load_prompt(prompt), prompt


# --------------------------------------------------------------------------- a spec não decide no lugar do PO
def test_spec_que_decide_parametro_do_po_volta_ao_autor():
    op = ONE_PAGER + "\n## 8. Estados de falha\n- Inatividade: dica após `[PARÂMETRO — a definir por produto: tempo de inatividade de 45 segundos]`.\n"
    decidida = _spec() + "\n- Inatividade: após 45 segundos sem interação, a dica aparece.\n"
    assert "parametro-decidido" in _codigos(ca.validar_spec(decidida, op))
    marcada = _spec() + "\n- Inatividade: após 45 segundos `[PARÂMETRO — a definir por produto: inatividade]`.\n"
    registrada = _spec() + "\n- Inatividade: 45 s, decidido pelo PO no parecer de 08/10/2026.\n"
    for spec in (marcada, registrada, _spec()):
        assert "parametro-decidido" not in _codigos(ca.validar_spec(spec, op))
    # o D0 ratificar é decisão de agente: não isenta nem bloqueia, fica 🟡 para o PO (plano padrão ouro, 2.8)
    pelo_d0 = ca.validar_spec(_spec() + "\n- Inatividade: 45 s sem interação, ratificado no [D0-3].\n", op)
    assert [a["severidade"] for a in pelo_d0["achados"] if a["codigo"] == "parametro-decidido"] == ["atencao"]
    sem_data = _spec() + "\n- Inatividade: após 45 segundos sem interação, decidido pelo PO.\n"
    assert "parametro-decidido" in _codigos(ca.validar_spec(sem_data, op))
    assert ca.parametros_decididos("- Inatividade: 45 s sem toque, a dica pisca.", op)


# --------------------------------------------------------------------------- o resumido que o time aprova
def test_resumido_conferido_contra_o_canonico():
    spec = "## 11. Currículo\n`EF01CO01`\n"
    lit = ca.literais(ONE_PAGER_LITERAIS)["canal_b"]
    fiel = "## 2. Componente curricular\n`EF01CO01`\n\n## 6. Contrato de evidência\n" + "\n".join(f'"{t}"' for t in lit)
    assert ca.validar_resumido(fiel, spec, ONE_PAGER_LITERAIS)["status"] == "aprovado"
    parafraseado = "## 2. Componente curricular\n`EF01CO01`\n\n## 6. Contrato\nA criança escolhe por que as fotos combinam."
    assert _codigos(ca.validar_resumido(parafraseado, spec, ONE_PAGER_LITERAIS)) == ["canal-b-reescrito"]
    # citar numa proposta de incluir não é acrescentar; afirmar é
    proposta = fiel + "\n`EF01CO03` [PROPOSTA — validar com PO: incluir a EF01CO03]"
    assert ca.validar_resumido(proposta, spec, ONE_PAGER_LITERAIS)["status"] == "aprovado"
    afirmada = fiel + "\nTambém exercita `EF01CO03`."
    r = ca.validar_resumido(afirmada, spec, ONE_PAGER_LITERAIS)
    assert _codigos(r) == ["habilidade-acrescentada"] and r["achados"][0]["agente_responsavel"] == "one-pager-resumido"
    # o tempo em tela do canônico (29 min), não o de um parecer
    outro_tempo = "`EF06CO10` `EF06CO01` `EF06CO03` `EF06CO07` — 24 minutos em tela."
    assert _codigos(ca.validar_resumido(outro_tempo, _spec(), ONE_PAGER)) == ["tempo-alterado"]


def test_resumido_em_loop_e_o_prompt_manda_o_canonico_vencer():
    from agents.produto import build_produto_stage
    from prompts import load_prompt

    loop = build_produto_stage().sub_agents[-1]
    assert loop.name == "OnePagerResumidoLoop"
    assert [a.name for a in loop.sub_agents] == ["A16bOnePagerResumido", "A16eConteudoAprovadoResumido", "A16fResumidoRodada"]
    prompt = load_prompt("produto/16b_one_pager_resumido.md")
    assert "a spec vence e você registra" not in prompt and "**vale o canônico**" in prompt
    assert "{conteudo_aprovado_resumido_report?}" in prompt


# --------------------------------------------------------------------------- PRD ancorado no one-pager
def test_prd_e_pedagogico_conferidos_contra_o_one_pager_mesmo_com_a_spec_divergente():
    """Com a spec sem a EF06CO07 (loop esgotado, exceção do admin), o PRD fiel ao one-pager recebia «tire-a»."""
    spec_sem = _spec(codigos=("EF06CO10", "EF06CO01", "EF06CO03"))
    fiel = ca.com_anexo(_prd(), ONE_PAGER, ca.SECOES_PRD)
    assert "habilidade-acrescentada" not in _codigos(ca.validar_prd(fiel, spec_sem, ONE_PAGER, ARTEFATOS))
    sem = ca.com_anexo(_prd(codigos_14=("EF06CO10", "EF06CO01", "EF06CO03")), ONE_PAGER, ca.SECOES_PRD)
    r = ca.validar_prd(sem, spec_sem, ONE_PAGER, ARTEFATOS)
    perdida = next(a for a in r["achados"] if a["codigo"] == "habilidade-perdida")
    assert "`EF06CO07`" in perdida["resumo"] and "one-pager aprovado" in perdida["resumo"]
    # sem código no one-pager, a referência volta a ser o bloco 11
    assert ca.habilidades_de_referencia(_spec(), "# One-pager\n## 2. Currículo\nA definir.\n")[1] == "o bloco 11 da spec"
    # e também quando a spec deixou o currículo pendente: o código do one-pager que a lista oficial recusou não é cobrado
    pendente = _spec().replace("## 11. Currículo", "## 11. Currículo\n[ABERTO — dono: produto: EF06CO07 fora da lista do ano]")
    assert ca.habilidades_de_referencia(pendente, ONE_PAGER)[1] == "o bloco 11 da spec"


def test_spec_consolidada_so_acusa_o_que_o_d0_piorou():
    gate0 = _spec(codigos=("EF06CO10", "EF06CO01", "EF06CO03"))  # já divergia em produto: decidido lá
    assert ca.validar_spec_consolidada(gate0, gate0, ONE_PAGER)["status"] == "aprovado"
    consolidada = gate0.replace("**29 minutos**", "**25 minutos**")  # o D0 trocou o tempo
    r = ca.validar_spec_consolidada(consolidada, gate0, ONE_PAGER)
    assert [a["codigo"] for a in r["achados"]] == ["tempo-alterado"]
    assert r["achados"][0]["agente_responsavel"] == "fecha-lacunas" and r["achados"][0]["etapa"] == "design"

    from agents.design import MAPA_RETRABALHO, build_design_stage

    nomes = [a.name for a in build_design_stage().sub_agents]
    assert nomes.index("A20AmbienteSimuladoSplit") + 1 == nomes.index("A20bSpecConsolidada")
    assert MAPA_RETRABALHO["fecha-lacunas"][-1] == "A20bSpecConsolidadaRetrabalho"


# --------------------------------------------------------------------------- refazer produto: o que mudou
class _Marca(BaseAgent):
    async def _run_async_impl(self, ctx):
        feitos = list(ctx.session.state.get("feitos") or []) + [self.name]
        yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta={"feitos": feitos}))


def test_o_que_mudou_no_one_pager_chega_aos_autores_com_a_versao_anterior():
    from agents.base import create_llm_agent
    from agents.checkers import ConteudoAprovadoAgent
    from pipeline.reexecucao import preparar_estado

    def rodar(estado):
        return asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[
            ConteudoAprovadoAgent(name="C", secoes=[10], chave_base="base_teste")]), estado))

    primeira = rodar({"one_pager": ONE_PAGER})
    assert primeira["mudancas_no_aprovado"] == "" and "Em tela: 29 min" in primeira["base_teste"]
    refeito = ONE_PAGER.replace("Em tela: 29 min", "Em tela: 25 min")
    segunda = rodar({**primeira, "one_pager": refeito})
    assert "antes: **Tempo de aula: 50 min · Em tela: 29 min**" in segunda["mudancas_no_aprovado"]
    assert "agora: **Tempo de aula: 50 min · Em tela: 25 min**" in segunda["mudancas_no_aprovado"]
    assert rodar(segunda)["mudancas_no_aprovado"] == "", "sem mudança nova, nada a dizer"

    autor = create_llm_agent(name="X", instruction="Escreva.", description="d", output_key="jornada_telas")
    assert "{anterior_jornada_telas?}" in autor.instruction and "{mudancas_no_aprovado?}" in autor.instruction
    gate = create_llm_agent(name="Y", instruction="Julgue.", description="d", output_key="qa_entregaveis_report")
    assert "{mudancas_no_aprovado?}" not in gate.instruction
    # o retrato sobrevive ao refazer de produto; a lista de mudanças, não
    limpo, _ = preparar_estado({"one_pager": "x", "conteudo_aprovado_base_design": "b", "mudancas_no_aprovado": "m"},
                               "produto")
    assert "mudancas_no_aprovado" not in limpo and limpo["conteudo_aprovado_base_design"] == "b"


# --------------------------------------------------------------------------- pedidos do PO, por etapa
def test_cada_etapa_confere_o_refazer_que_foi_pedido_a_ela():
    from agents.checkers import FidelidadeCheckAgent

    pedidos = [
        {"origem": "refazer Produto", "etapa": "produto",
         "texto": "AJUSTE 1 — a descoberta central passa a falar de bolha de filtro no feed"},
        {"origem": "refazer Design", "etapa": "design",
         "texto": "AJUSTE 1 — o botão da tela E3-ALU-02 diz Enviar a minha resposta agora"},
    ]
    estado = {"pedidos_do_po": pedidos, "pedido_correcao": "AJUSTE 9 — um pedido da execução corrente que é de produto",
              "briefing": "", "copy_strings_revisada": "a copy", "one_pager": "o one-pager"}

    def origens(**campos):
        f = FidelidadeCheckAgent(name="F", status_key="f_status", report_key="f_report", **campos)
        final = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[f]), dict(estado)))
        return final["f_status_envelope"]["achados"]

    design = origens(documentos=["copy_strings_revisada"], etapas_pedido=["design"], com_briefing=False,
                     incluir_corrente=False, etapa="design")
    assert {a["origem"] for a in design} == {"refazer Design"} and {a["etapa"] for a in design} == {"design"}
    produto = origens(documentos=["one_pager"], etapas_pedido=["produto", ""])
    assert {a["origem"] for a in produto} == {"refazer Produto", "pedido de correção desta execução"}

    from agents.design import build_design_stage
    from agents.dev import agentes_em_ordem, build_dev_stage

    assert build_design_stage().sub_agents[-1].name == "A33cFidelidadeDesign"
    assert agentes_em_ordem(build_dev_stage())[-1].name == "A51FidelidadeDev"


def test_devolutiva_que_achou_o_problema_chega_ao_refazer_e_o_conteudo_muda_em_produto():
    from pipeline import passagem
    from test_passagem import COMENTARIO, DESIGN, ESTADO_VERDE, PO

    pareceres = [
        {"etapa": "design", "acao": "devolver", "como": "dev", "quando": "07/10/2026 10:00:00",
         "comentario": "29 × 24 min em tela, e falta a EF06CO07 no PRD"},
        {"etapa": "produto", "acao": "devolver", "como": "design", "quando": "07/10/2026 11:00:00",
         "comentario": "A causa é a mecânica do one-pager, não o design"},
    ]
    fluxo = {**passagem.novo_fluxo(), "etapa": "produto", "situacao": passagem.DEVOLVIDA, "pareceres": pareceres}
    _, efeito = passagem.aplicar(fluxo, passagem.REFAZER, PO, "Refaça a mecânica e mantenha a EF06CO07 no contrato.",
                                 ESTADO_VERDE)
    assert "29 × 24 min em tela" in efeito.pedido and "A causa é a mecânica" in efeito.pedido

    # em design, mudança de conteúdo aprovado vai a produto, não ao refazer
    aguardando = {**passagem.novo_fluxo(), "etapa": "design", "situacao": passagem.AGUARDANDO}
    try:
        passagem.aplicar(aguardando, passagem.DE_ACORDO, DESIGN,
                         COMENTARIO + " Pergunta 1 passa a ser outra, bem diferente.", ESTADO_VERDE)
        assert False, "de acordo com mudança de conteúdo deveria ser recusado"
    except passagem.DecisaoInvalida as e:
        assert "Devolver" in str(e)

    notas = passagem.notas_de_passagem({"pareceres": [
        {"etapa": "produto", "acao": passagem.DE_ACORDO, "como": "produto", "quando": "1", "comentario": COMENTARIO},
        {"etapa": "design", "acao": passagem.REFAZER, "como": "design", "quando": "2", "comentario": COMENTARIO}]})
    assert "CONFLITO — parecer × one-pager aprovado" in notas and "CONFLITO — pedido do PO × one-pager aprovado" in notas


# --------------------------------------------------------------------------- banca de dev
def test_orcamento_conta_so_chamada_de_modelo_e_o_conserto_pulado_vai_ao_dossie():
    from agents.checkers import KEY_REEXECUCOES, KEY_TICKETS_SEM_ROTA, DespachoTicketsAgent
    from config import get_settings

    envelope = {"status": "bloqueado", "achados": [{"id": "B1", "severidade": "bloqueio", "codigo": "DES-02",
                                                     "agente_responsavel": "jornada", "resumo": "jornada sem a tela"}]}
    teto = get_settings().orcamento_reexecucoes

    def rodar(gastos):
        derivados = [f"P{i}" for i in range(6)]
        despacho = DespachoTicketsAgent(
            name="D", rotulo="Banca", report_key="banca", mapa={"jornada": ["J"]}, ordem=["jornada"],
            posfixo_por_dono={"jornada": derivados}, sub_agents=[_Marca(name="J")] + [_Marca(name=n) for n in derivados])
        return asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[despacho]),
                                  {"banca": "```json\n" + json.dumps(envelope) + "\n```", KEY_REEXECUCOES: gastos}))

    # resta 1 no orçamento: o ticket da jornada custa 1; os seis determinísticos que derivam dela não custam
    assert rodar(teto - 1)["feitos"] == ["J", "P0", "P1", "P2", "P3", "P4", "P5"]
    pulado = rodar(teto)
    assert not pulado.get("feitos")
    assert [(r["id"], r["dono"]) for r in pulado[KEY_TICKETS_SEM_ROTA]] == [("B1", "jornada")]


def test_banca_nas_quatro_posicoes_e_o_dev_so_conserta_dev():
    """Decisão de 08/10/2026: a banca roda no fim de produto e no fim de design (antes do parecer, com retrabalho da
    própria etapa), de novo na entrada do dev (segunda verificação, sem reescrever) e, dentro do dev, só com dados e
    técnica — consertando só documento de dev."""
    from agents.design import build_qa_design_loop
    from agents.dev import BANCA_EXTERNO, MAPA_BANCA, ORDEM_BANCA, POSFIXO_BANCA, agentes_em_ordem, build_dev_stage
    from agents.produto import _build_spec_loop
    from config import get_settings
    from tools import banca as bnc

    # dentro do dev: só documento de dev, e o que ele reescreve é reconferido
    assert set(MAPA_BANCA) == {"handoff-dev", "brief-assets", "banco-conteudo"} and ORDEM_BANCA[-1] == "banco-conteudo"
    assert {"jornada", "fluxo", "telas", "copy-ptbr-revisao", "spec-missao"} <= set(BANCA_EXTERNO)
    assert POSFIXO_BANCA == {"banco-conteudo": ["A35cConteudoCheckRetrabalhoBanca"],
                             "handoff-dev": ["A36TelemetriaCheckRetrabalhoBanca"]}
    banca_dev = next(a for a in agentes_em_ordem(build_dev_stage()) if a.name == "BancaLoop")
    juizes = next(a for a in banca_dev.sub_agents if a.name == "BancaValidacaoDev").sub_agents
    assert [j.output_key for j in juizes] == ["validacao_dados_lgpd", "validacao_tecnica_arquitetura"]
    assert banca_dev.sub_agents[0].posicao == "dev"

    # fim de produto: dentro do loop da spec, e o loop só termina com a banca liberada
    loop_spec = _build_spec_loop({}, get_settings(), 2)
    nomes = [a.name for a in loop_spec.sub_agents]
    assert nomes.index("A15hBancaConsolidacao") < nomes.index("A16SpecCheck")
    assert "banca_produto_status" in loop_spec.sub_agents[-1].status_keys

    # fim de design: antes do QA, e o bloqueio vira ticket pelo A30b
    qa = [a.name for a in build_qa_design_loop().sub_agents]
    assert qa.index("A29fBancaConsolidacao") < qa.index("A30QaEntregaveis")

    # entrada do dev: antes de qualquer agente de dev, comparando com as etapas
    dev = build_dev_stage()
    topo = [a.name for a in dev.sub_agents]
    assert topo == ["A33aConteudoAprovadoDev", "A33bEscopoBanca", "A33bBanca", "A33bBancaConsolidacao", "DevConstrucao"]
    entrada = dev.sub_agents[3]
    assert entrada.status_key == "banca_entrada_status" and entrada.gravar_status
    assert set(entrada.comparar_com) == {"produto", "design"}
    assert set(bnc.ESCOPOS) == {"produto", "design", "entrada", "dev"}


def test_banca_de_entrada_bloqueada_nao_deixa_o_dev_rodar_e_aponta_a_divergencia():
    from agents.banca import pular_se_banca_de_entrada_bloqueou
    from tools import banca as bnc

    def rodar(status):
        dev = SequentialAgent(name="DevConstrucao", before_agent_callback=pular_se_banca_de_entrada_bloqueou,
                              sub_agents=[_Marca(name="Handoff")])
        return asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[dev]), {"banca_entrada_status": status}))

    assert rodar("bloqueado").get("feitos") is None, "com a entrada 🔴 o dev não roda"
    assert rodar("aprovado")["feitos"] == ["Handoff"]

    entrada = {"achados": [{"id": "PROD-07", "severidade": "bloqueio"}, {"id": "DES-14", "severidade": "bloqueio"}]}
    design = {"achados": [{"id": "DES-14", "severidade": "bloqueio"}]}  # o design já sabia: liberado por exceção
    assert bnc.divergencias_com_etapas(entrada, {"produto": {"achados": []}, "design": design}) == [
        "`PROD-07` passou no fim de produto e de design e reprova aqui."]
    assert bnc.divergencias_com_etapas(entrada, {"produto": None, "design": None}) == []


def test_matriz_final_no_semaforo_de_dev_e_a_do_design_no_de_design():
    from agents.dev import agentes_em_ordem, build_dev_stage
    from pipeline import passagem
    from pipeline.artifacts import ARTIFACT_FILES

    a50 = next(a for a in agentes_em_ordem(build_dev_stage()) if a.name == "A50Rastreabilidade")
    assert (a50.report_key, a50.status_key) == ("rastreabilidade_dev_report", "rastreabilidade_dev_status")
    assert "rastreabilidade_dev_status" in passagem.chaves_da_etapa("dev")
    assert "rastreabilidade_status" in passagem.chaves_da_etapa("design")
    estado = {"rastreabilidade_status": "aprovado", "rastreabilidade_dev_status": "bloqueado"}
    assert passagem.semaforo_da_etapa(estado, "dev").get("rastreabilidade_dev_status") == "🔴"
    # o arquivo é o mesmo: a final, quando existe, substitui a do design
    assert [k for k, f in ARTIFACT_FILES if f == "matriz-de-rastreabilidade.md"] == [
        "rastreabilidade_report", "rastreabilidade_dev_report"]


def test_triagem_manda_a_produto_o_que_o_one_pager_fixa():
    texto = (FIXTURES.parent.parent / "prompts" / "transversal" / "00_triagem_correcao.md").read_text(encoding="utf-8")
    linha_spec = next(l for l in texto.splitlines() if l.startswith("| `spec`"))
    linha_produto = next(l for l in texto.splitlines() if l.startswith("| `produto`"))
    assert "códigos BNCC do bloco 11" not in linha_spec
    assert "§12a" in linha_produto and "Canal B" in linha_produto and "PARÂMETRO" in linha_produto


# --------------------------------------------------------------------------- PRD × conteúdo aprovado (08/10/2026)
class _JuizFalso(BaseAgent):
    output_key: str = "juiz_saida"
    resposta: str = ""

    async def _run_async_impl(self, ctx):
        yield Event(invocation_id=ctx.invocation_id, author=self.name,
                    actions=EventActions(state_delta={self.output_key: self.resposta}))


def test_corpo_do_prd_que_cita_o_aprovado_com_outra_redacao_ou_outro_tempo():
    aprovado = "Antes de abrir as fotos, o que você acha que aconteceu no pátio?"
    assert ca.literais_parafraseados(f'O estudante lê "{aprovado}"', ONE_PAGER_S4) == []
    reescrito = 'O estudante lê "Antes de abrir as fotos, o que você imagina que houve no pátio?"'
    assert ca.literais_parafraseados(reescrito, ONE_PAGER_S4) == [
        (aprovado, "Antes de abrir as fotos, o que você imagina que houve no pátio?")]
    # rótulo curto parecido com outro rótulo curto não é paráfrase
    assert not ca.literais_parafraseados('"Galeria Oculta da Mostra"', '# OP\n## 4. E\n### Etapa 1: Desafiar\n- Botão "Acessar Feed da Mostra"\n')

    assert ca.tempos_por_etapa(ONE_PAGER) == {"Desafiar": 2}
    assert ca.tempos_de_etapa_divergentes("| Desafiar | 4 min |", ONE_PAGER)[0][:2] == ("Desafiar", 2)
    assert ca.tempos_de_etapa_divergentes("| Desafiar | 2 min |", ONE_PAGER) == []
    prd = ca.com_anexo(_prd() + "\n| Desafiar | 4 min |\n", ONE_PAGER, ca.SECOES_PRD)
    achado = next(a for a in ca.validar_prd(prd, _spec(), ONE_PAGER, ARTEFATOS)["achados"]
                  if a["codigo"] == "tempo-de-etapa-divergente")
    assert achado["severidade"] == "atencao"


def test_juiz_de_contradicoes_so_vale_com_as_duas_citacoes_conferidas():
    from agents.checkers import JuizDeContradicoesAgent

    referencia = "O estudante não pode voltar à etapa anterior depois de travar a aposta."
    prd = "# PRD\n\nRF-004: o estudante pode voltar e trocar a aposta a qualquer momento antes do resultado.\n"
    resposta = "```json\n" + json.dumps({"contradicoes": [
        {"tipo": "mecanica", "citacao_documento": "o estudante pode voltar e trocar a aposta a qualquer momento",
         "citacao_referencia": "não pode voltar à etapa anterior depois de travar a aposta",
         "explicacao": "um diz que a aposta trava, o outro que pode trocar"},
        {"tipo": "numero", "citacao_documento": "são cinco rodadas de votação na turma",
         "citacao_referencia": "não pode voltar à etapa anterior depois de travar a aposta", "explicacao": "inventada"},
    ]}, ensure_ascii=False) + "\n```"

    def rodar(estado):
        agente = JuizDeContradicoesAgent(name="C", documento_key="prd_final", referencia_key="conteudo_aprovado",
                                         report_key="c_report", status_key="c_status", dono="prd-writer",
                                         sub_agents=[_JuizFalso(name="J", resposta=resposta)])
        return asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[agente]), estado))

    final = rodar({"prd_final": prd, "conteudo_aprovado": referencia})
    assert final["c_status"] == "bloqueado"
    achados = final["c_status_envelope"]["achados"]
    assert [a["codigo"] for a in achados] == ["contradicao-mecanica"] and achados[0]["agente_responsavel"] == "prd-writer"
    assert "Apontadas sem prova" in final["c_report"], "a contradição inventada é descartada"
    assert final["contradicoes_documento"] == "" and final["contradicoes_referencia"] == ""
    # o anexo colado pela esteira não é o corpo: a contradição que só ele teria não conta — e sem corpo nada foi
    # conferido, então é 🟡, não 🟢 (auditoria de 08/10/2026: o juiz que não conferia aprovava)
    assert rodar({"prd_final": "", "conteudo_aprovado": referencia})["c_status"] == "amarelo"
    mudo = JuizDeContradicoesAgent(name="C", documento_key="prd_final", referencia_key="conteudo_aprovado",
                                   report_key="c_report", status_key="c_status", dono="prd-writer",
                                   sub_agents=[_JuizFalso(name="J", resposta="Não consegui avaliar.")])
    final = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[mudo]), {"prd_final": prd, "conteudo_aprovado": referencia}))
    assert final["c_status"] == "amarelo" and "NÃO CONFERIDO" in final["c_report"]

    from agents.dev import agentes_em_ordem, build_dev_stage

    prd_loop = next(a for a in agentes_em_ordem(build_dev_stage()) if a.name == "PrdLoop")
    nomes = [a.name for a in prd_loop.sub_agents]
    assert nomes.index("A48eCoerenciaPrd") < nomes.index("A48PrdRodada")
    assert "coerencia_prd_status" in prd_loop.sub_agents[-1].status_keys


def test_loop_que_repete_entrega_ao_autor_a_versao_da_rodada():
    from agents.base import create_llm_agent
    from agents.checkers import SaidaDeLoopAgent

    def rodar(status):
        saida = SaidaDeLoopAgent(name="S", status_keys=["g_status"], rodada_key="r", max_rounds=3,
                                 autor_keys=["prd_final"])
        return asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[saida]),
                                  {"g_status": status, "prd_final": "# PRD v1\nRF-001 …"}))

    repete = rodar("bloqueado")
    assert "<versao_da_rodada chave=\"prd_final\">" in repete["rodada_anterior_prd_final"]
    assert "# PRD v1" in repete["rodada_anterior_prd_final"]
    assert rodar("aprovado")["rodada_anterior_prd_final"] == "", "ao sair do loop a versão da rodada some"
    autor = create_llm_agent(name="X", instruction="Escreva.", description="d", output_key="prd_final")
    assert "{rodada_anterior_prd_final?}" in autor.instruction


def test_folha_do_stitch_entrega_so_a_versao_atual(monkeypatch):
    from agents.checkers import ArtefatosDesignAgent
    from config import get_settings
    import tools.stitch_cliente as cliente

    telas = [{"id": "a" * 32, "titulo": "E1-ALU-01 — padrão"}, {"id": "b" * 32, "titulo": "E1-ALU-01 — padrão"},
             {"id": "c" * 32, "titulo": "E1-ALU-02 — padrão"}]
    monkeypatch.setattr(cliente, "coletar_links", lambda pid, limite=60, ids_de_reserva=(): {
        "project_id": pid, "url_projeto": f"https://stitch/{pid}", "telas": [dict(t) for t in telas]})
    monkeypatch.setattr(type(get_settings()), "is_stitch_enabled", property(lambda self: True))
    registro = {"E1-ALU-01|padrão": {"screen_id": "b" * 32, "hash": "h", "versao": 2},
                "E1-ALU-02|padrão": {"screen_id": "c" * 32, "hash": "h", "versao": 1}}
    estado = {"stitch_project_id": "123", "stitch_geracao": registro, "jornada_telas": "E1-ALU-01 E1-ALU-02",
              "prototipo_html": "<html></html>", "wireframes_cobertura": "x"}
    final = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[ArtefatosDesignAgent(name="A")]), estado))
    folha = final["stitch_links"]
    assert "E1-ALU-01 — padrão · v2" in folha and "E1-ALU-02 — padrão" in folha
    assert "2 tela(s)." in folha and "1 tela(s) do projeto são versões anteriores" in folha


def test_orcamento_conta_o_autor_e_nao_a_cadeia_inteira_de_cada_dono():
    """exp01ef1b (08/10/2026): sete donos de design, cada um com determinísticos na cadeia (D9 + split + spec
    consolidada; telas + Stitch). A conta deu 11 contra o orçamento de 8 com 7 chamadas de modelo, e nenhum conserto
    rodou nas duas rodadas do QA."""
    from agents.checkers import KEY_REEXECUCOES, DespachoTicketsAgent

    donos = [f"d{i}" for i in range(7)]
    envelope = {"status": "bloqueado", "achados": [
        {"id": f"T{i}", "severidade": "bloqueio", "codigo": "X", "agente_responsavel": d, "resumo": "conserto"}
        for i, d in enumerate(donos)]}
    mapa = {d: [f"A{i}", f"A{i}det"] if i < 4 else [f"A{i}"] for i, d in enumerate(donos)}
    nomes = [n for cadeia in mapa.values() for n in cadeia]
    despacho = DespachoTicketsAgent(name="D", rotulo="QA", report_key="qa", mapa=mapa, ordem=donos,
                                    sub_agents=[_Marca(name=n) for n in nomes])
    final = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[despacho]),
                               {"qa": "```json\n" + json.dumps(envelope) + "\n```", KEY_REEXECUCOES: 0}))
    assert final["feitos"] == [n for d in donos for n in mapa[d]]
    assert final[KEY_REEXECUCOES] == 7
