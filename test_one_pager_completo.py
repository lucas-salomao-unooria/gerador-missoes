"""O one-pager de produto é um documento só: o canônico aberto pela missão em linguagem do time (28/10/2026).

O time de negócio e de produto não entendia o que a missão faz lendo o one-pager nem o resumido. O modelo aprovado
(`Unooria_One_Page_Completo_Porta_Voz_dos_Dados.docx`) junta tudo: §0, §0.1 A ideia, §0.2 Como a missão funciona
passo a passo, §1–§18 e o brief de escopo no fim. Estes testes fixam o encaixe das duas seções, a conferência em
código (forma, jargão, números e falas) e a exportação — e que o resumido saiu da esteira.
"""
import asyncio
from types import SimpleNamespace

from google.adk.agents.loop_agent import LoopAgent

from agents.callbacks import (KEY_MODO_CORRECAO, encaixar_leitura_no_one_pager,
                              manter_leitura_na_correcao_pontual)
from agents.checkers import RastroCheckAgent, SaidaDeLoopAgent
from test_conteudo_aprovado import _rodar
from tools import one_pager_completo as oc

ONE_PAGER = """# One-pager — O Porta-Voz dos Dados v1.1

## 0. Identificação
Slug = exp03em1b · Nome que o estudante vê: O Porta-Voz dos Dados · Ambiente simulado: Unoochat

## 1. Descoberta central
"Mesmo quando dois gráficos usam os mesmos números, a escolha do eixo muda o que as pessoas entendem."

## 4. As 6 etapas — mecanismo, não intenção
O bot abre com "Seja bem-vindo, Porta-Voz. Você tem exatamente 3 publicações oficiais disponíveis". A tabela traz
95%, 94%, 92% e 88%. No eixo em 80% a barra encolhe cerca de 47%. O professor toca em "Liberar Retomada".

## 9. Papel do professor e parametrização com IA
O professor escolhe a missão e usa o banco padrão sobre a qualidade da água.
"""

PASSOS = "\n\n".join(
    f"### {n}. {titulo}\n\n{texto}" for n, (titulo, texto) in enumerate([
        ("O professor prepara e libera a atividade", "O professor escolhe a missão e usa o banco padrão."),
        ("O estudante assume o papel de porta-voz", "Ele abre o chat do assistente e vê as 3 publicações."),
        ("Lê a tabela", "O assistente mostra 95%, 94%, 92% e 88%."),
        ("Compara duas formas de mostrar", "Ele alterna entre o eixo em 0% e o eixo em 80%."),
        ("Escolhe e publica", "Ele publica no grupo da cidade, sem volta."),
        ("Vê a reação", "Os moradores reagem ao gráfico."),
        ("Conversa com a turma", "A tela congela e o professor toca em \"Liberar Retomada\"."),
        ("Encerra a missão", "O professor retoma a descoberta com a turma."),
    ], start=1))

LEITURA = f"""{oc.TITULO_IDEIA}

O professor libera a atividade e o estudante entra no Unoochat como porta-voz da escola.

Ele recebe a tabela com 95%, 94%, 92% e 88% e escolhe onde começa o eixo do gráfico.

No eixo em 80% a barra encolhe cerca de 47%, e a turma discute por que os mesmos números contam histórias diferentes.

{oc.TITULO_PASSO_A_PASSO}

{PASSOS}
"""


def test_encaixa_entre_a_identificacao_e_a_secao_1_e_substitui_a_versao_anterior():
    completo = oc.encaixar(ONE_PAGER, LEITURA)
    assert completo.index("## 0. Identificação") < completo.index(oc.TITULO_IDEIA) \
        < completo.index(oc.TITULO_PASSO_A_PASSO) < completo.index("## 1. Descoberta central")
    de_novo = oc.encaixar(completo, LEITURA.replace("cerca de 47%", "quase metade"))
    assert de_novo.count(oc.TITULO_IDEIA) == 1 and "quase metade" in de_novo
    assert oc.sem_leitura(de_novo).strip() == ONE_PAGER.strip()


def test_leitura_fiel_e_sem_jargao_passa():
    resultado = oc.validar(oc.encaixar(ONE_PAGER, LEITURA))
    assert resultado["status"] == "aprovado", resultado["achados"]
    assert resultado["passos"] == 8


def test_jargao_numero_sem_origem_e_fala_reescrita_voltam_ao_redator():
    ruim = LEITURA.replace("Os moradores reagem ao gráfico.",
                           "O bot determinístico consome 1 slot e o gate trava; 63% reagem com \"A água está "
                           "contaminada, fechem as escolas\".")
    resultado = oc.validar(oc.encaixar(ONE_PAGER, ruim))
    codigos = [a["codigo"] for a in resultado["achados"]]
    assert resultado["status"] == "bloqueado"
    assert codigos.count("jargao") == 3  # determinístico, slot, gate
    assert "numero-sem-origem" in codigos and "fala-reescrita" in codigos
    # a fala copiada do one-pager e a contagem do dia a dia passam
    assert not any("Liberar Retomada" in a["resumo"] or " 3 " in a["resumo"] for a in resultado["achados"])


def test_forma_do_modelo_prosa_e_passos_numerados_do_professor_ao_fechamento():
    so_ideia = oc.encaixar(ONE_PAGER, LEITURA.split(oc.TITULO_PASSO_A_PASSO)[0])
    assert "passo-a-passo-ausente" in [a["codigo"] for a in oc.validar(so_ideia)["achados"]]
    com_lista = LEITURA.replace("Ele recebe a tabela", "- Ele recebe a tabela")
    assert "ideia-com-lista" in [a["codigo"] for a in oc.validar(oc.encaixar(ONE_PAGER, com_lista))["achados"]]
    poucos = LEITURA.split("### 4.")[0]
    assert "passos-fora-da-faixa" in [a["codigo"] for a in oc.validar(oc.encaixar(ONE_PAGER, poucos))["achados"]]
    assert "ideia-ausente" in [a["codigo"] for a in oc.validar(ONE_PAGER)["achados"]]


def test_callback_encaixa_a_saida_do_redator_sem_preambulo_nem_envelope():
    saida = ("Aqui estão as seções:\n\n" + LEITURA
             + '\n---\n```json\n{"agente": "one-pager-completo", "status": "concluido"}\n```\n')
    estado = {"one_pager": ONE_PAGER, "one_pager_leitura": saida}
    encaixar_leitura_no_one_pager(SimpleNamespace(state=estado))
    assert estado["one_pager_leitura"].startswith(oc.TITULO_IDEIA) and '"agente"' not in estado["one_pager_leitura"]
    assert oc.secoes(estado["one_pager"])[1].startswith("### 1.")
    assert "Aqui estão" not in estado["one_pager"]


def test_correcao_pontual_mantem_o_que_o_editor_deixou_e_missao_antiga_ganha_as_secoes():
    completo = oc.encaixar(ONE_PAGER, LEITURA)
    pontual = {KEY_MODO_CORRECAO: "pontual", "one_pager": completo}
    conteudo = manter_leitura_na_correcao_pontual(SimpleNamespace(state=pontual))
    assert conteudo is not None and oc.secoes(conteudo.parts[0].text) == oc.secoes(completo)
    assert manter_leitura_na_correcao_pontual(SimpleNamespace(state={**pontual, "one_pager": ONE_PAGER})) is None
    assert manter_leitura_na_correcao_pontual(SimpleNamespace(state={"one_pager": completo})) is None


def test_gate_na_esteira_grava_relatorio_e_status():
    loop = LoopAgent(name="OnePagerCompletoLoop", max_iterations=1, sub_agents=[
        RastroCheckAgent(name="A062LeituraOnePagerCheck", modo="one_pager_completo", rotulo="Leitura clara do one-pager",
                         report_key="one_pager_completo_report", status_key="one_pager_completo_status",
                         agente="one-pager-completo", estrito=False),
        SaidaDeLoopAgent(name="A063OnePagerCompletoRodada", rotulo="Leitura clara do one-pager",
                         status_keys=["one_pager_completo_status"], rodada_key="one_pager_completo_rodada",
                         max_rounds=1),
    ])
    estado = asyncio.run(_rodar(loop, {"one_pager": oc.encaixar(ONE_PAGER, LEITURA)}))
    assert estado["one_pager_completo_status"] == "aprovado"
    assert "PRONTO PARA LEITURA" in estado["one_pager_completo_report"]


def test_exportacao_traz_o_brief_de_escopo_no_fim_uma_vez_so():
    from pipeline.artifacts import ONE_PAGERS_COM_MARCA, documento_para_gravar

    brief = "**MISSÃO DIGITAL UNOORIA · BRIEFING DE ESCOPO (LEITURA RÁPIDA)**\n\n# 1. O QUE É ESTA MISSÃO\nUma vivência."
    estado = {"one_pager": oc.encaixar(ONE_PAGER, LEITURA), "brief_escopo": brief}
    gravado = documento_para_gravar(estado, "one_pager")
    assert gravado.index(oc.TITULO_PASSO_A_PASSO) < gravado.index("## 9.") < gravado.index("BRIEFING DE ESCOPO")
    assert documento_para_gravar({**estado, "one_pager": gravado}, "one_pager").count("BRIEFING DE ESCOPO") == 1
    assert [c for c, *_ in ONE_PAGERS_COM_MARCA] == ["one_pager", "one_pager_pedagogico"]


def test_o_resumido_saiu_da_esteira():
    from agents.produto import PRODUTO_METADATA, SPEC_AGENT_IDS, build_produto_stage
    from pipeline.artifacts import ARTIFACT_FILES

    nomes = [a.name for a in build_produto_stage().sub_agents]
    assert nomes[-1] == "OnePagerCompletoLoop"
    assert [a.name for a in build_produto_stage(a_partir_de="spec").sub_agents][-1] == "OnePagerCompletoLoop"
    assert "one_pager_resumido" not in dict(ARTIFACT_FILES)
    assert not any("Resumido" in m["id"] for m in PRODUTO_METADATA)
    assert SPEC_AGENT_IDS[-3:] == ["A061OnePagerCompleto", "A062LeituraOnePagerCheck", "A063OnePagerCompletoRodada"]
