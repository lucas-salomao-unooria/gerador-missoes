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

### 1.2 Anatomia do aha
Crença de entrada: o gráfico mostra os números como eles são.

## 4. As etapas — mecanismo, não intenção

### Etapa 1 — Desafiar

#### Momento 1.1 — O estudante recebe a tarefa do assistente
- **Quem age:** Estudante
- **Na tela:** o chat do assistente com 1 mensagem e o contador de 3 publicações.
- **Gesto:** ler · 1 mensagem — ler a tarefa no chat
- **Resposta na hora:** o botão "Ver os dados" aparece embaixo da mensagem.
- **Se não fizer:** o botão fica parado na tela até ele tocar.
- **Se errar:** Não há erro aqui: é só leitura.
- **Libera:** tocar em "Ver os dados" → Momento 2.1
- **Fica registrado:** nada
- **Texto de tela:** "Seja bem-vindo, Porta-Voz. Você tem exatamente 3 publicações oficiais disponíveis" · "Ver os dados"

### Etapa 2 — Navegar

#### Momento 2.1 — O estudante compara as duas formas de mostrar
- **Quem age:** Estudante
- **Na tela:** a tabela com 95%, 94%, 92% e 88% e 2 botões de eixo.
- **Gesto:** tocar · 2 botões — alternar entre o eixo em 0% e o eixo em 80%
- **Resposta na hora:** a barra encolhe cerca de 47% no eixo em 80%, e os números não mudam.
- **Se não fizer:** o botão "Escolher" fica apagado até ele ver os dois eixos.
- **Se errar:** Não há erro aqui: ver os dois é o objetivo.
- **Libera:** depois de ver os dois eixos, tocar em "Escolher" → Momento 3.1
- **Fica registrado:** quantas vezes ele alternou os eixos.
- **Texto de tela:** "Escolher"

### Etapa 3 — Decidir

#### Momento 3.1 — O estudante escolhe o gráfico e publica
- **Quem age:** Estudante
- **Na tela:** os 2 gráficos lado a lado e o botão "Publicar".
- **Opções (2):** "Eixo em 0%" · "Eixo em 80%"
- **Gesto:** escolher · 1 de 2 gráficos — publicar no grupo da cidade
- **Resposta na hora:** o gráfico vai para o grupo, sem volta, e o contador cai para 2.
- **Se não fizer:** o assistente lembra da tarefa depois de 60 segundos.
- **Se errar:** Não há erro aqui: as duas escolhas valem.
- **Libera:** tocar em "Publicar" → Momento 4.1
- **Fica registrado:** o eixo escolhido (Canal A).
- **Texto de tela:** "Publicar"

### Etapa 4 — Resultado/Aha

#### Momento 4.1 — O estudante vê a reação da cidade
- **Quem age:** Estudante
- **Na tela:** o grupo da cidade com os comentários dos moradores.
- **Gesto:** ler · 3 comentários — rolar o grupo
- **Resposta na hora:** os moradores reagem ao gráfico.
  - Se "Eixo em 0%": os moradores comentam que a água segue boa.
  - Se "Eixo em 80%": os moradores pedem para fechar as escolas.
- **Se não fizer:** a tela fica no grupo até o professor pausar a turma.
- **Se errar:** Não há erro aqui: é a consequência da escolha.
- **Libera:** a tela congela sozinha → Momento 4.2
- **Fica registrado:** nada
- **Texto de tela:** nenhum texto novo

#### Momento 4.2 — O professor conduz a conversa com a turma
- **Quem age:** Professor
- **Na tela:** a tela do estudante congela e o painel do professor mostra os dois gráficos.
- **Gesto:** falar · — conduzir a conversa com a turma
- **Resposta na hora:** a turma compara os gráficos e ninguém avança sozinho.
- **Se não fizer:** a tela segue congelada.
- **Se errar:** Não há erro aqui.
- **Libera:** o professor toca em "Liberar Retomada" → Momento 5.1
- **Fica registrado:** nada
- **Texto de tela:** "Liberar Retomada"

### Etapa 5 — Explicar

#### Momento 5.1 — O estudante conserta o gráfico
- **Quem age:** Estudante
- **Na tela:** o gráfico publicado e uma régua que começa em 80%.
- **Gesto:** arrastar · 1 régua — levar o começo do eixo para 0%
- **Resposta na hora:** as barras mudam de tamanho e os números não mudam.
- **Se não fizer:** o botão "Concluir" fica apagado.
- **Se errar:** Não há erro aqui: a régua mostra o efeito em qualquer ponto.
- **Libera:** tocar em "Concluir" → fim da missão
- **Fica registrado:** o ponto em que ele deixou o eixo (Canal A).
- **Texto de tela:** "Concluir"

## 9. Papel do professor e parametrização com IA
O professor escolhe a missão e usa o banco padrão sobre a qualidade da água.
"""


def _passo(titulo, linha, campos):
    return f"### {{n}}. {titulo}\n" + (f"*{linha}*\n" if linha else "") + "\n".join(
        f"**{rotulo}:** {texto}" for rotulo, texto in campos)


PASSOS_LISTA = [
    ("O professor prepara e libera a atividade", "Preparo do professor",
     [("O professor", "escolhe a missão e usa o banco padrão.")]),
    ("O estudante recebe a tarefa", "Desafiar · momento 1.1",
     [("Na tela", "o chat do assistente e o contador de publicações."), ("O estudante", "lê 1 mensagem."),
      ("Acontece", "aparece o botão \"Ver os dados\"."), ("Se não fizer", "o botão fica parado na tela."),
      ("Libera", "o toque no botão abre a tabela.")]),
    ("O estudante compara os dois eixos", "Navegar · momento 2.1",
     [("Na tela", "a tabela com 95%, 94%, 92% e 88%."), ("O estudante", "toca nos 2 botões de eixo."),
      ("Acontece", "a barra encolhe cerca de 47% no eixo em 80%."),
      ("Se não fizer", "o botão de escolher fica apagado."), ("Libera", "ver os dois eixos libera a escolha.")]),
    ("O estudante escolhe e publica", "Decidir · momento 3.1",
     [("Na tela", "os 2 gráficos lado a lado."), ("O estudante", "escolhe 1 de 2 gráficos e toca em \"Publicar\"."),
      ("Acontece", "o gráfico vai para o grupo da cidade, sem volta."),
      ("Se não fizer", "o assistente lembra da tarefa."), ("Libera", "a publicação abre o grupo da cidade.")]),
    ("O estudante vê a reação", "Resultado · momento 4.1",
     [("Na tela", "o grupo da cidade."), ("O estudante", "lê 3 comentários."),
      ("Acontece", "Os moradores reagem ao gráfico."), ("Se não fizer", "a tela espera o professor."),
      ("Libera", "a tela congela sozinha.")]),
    ("O professor conduz a conversa", "Resultado · momento 4.2",
     [("Na tela", "o painel do professor com os dois gráficos."),
      ("O professor", "pergunta o que mudou, já que os números são os mesmos."),
      ("Acontece", "a turma compara os gráficos."), ("Libera", "o professor toca em \"Liberar Retomada\".")]),
    ("O estudante conserta o gráfico", "Explicar · momento 5.1",
     [("Na tela", "o gráfico publicado e uma régua."), ("O estudante", "arrasta 1 régua até 0%."),
      ("Acontece", "as barras mudam e os números ficam iguais."),
      ("Se não fizer", "o botão de concluir fica apagado."), ("Libera", "o toque em concluir fecha a missão.")]),
    ("A turma encerra a missão", "Fechamento",
     [("O professor", "retoma a descoberta com a turma.")]),
]

PASSOS = "\n\n".join(_passo(t, l, c).replace("{n}", str(n)) for n, (t, l, c) in enumerate(PASSOS_LISTA, start=1))

IDEIA = """**Em uma frase.** O estudante é porta-voz da escola e escolhe como mostrar a qualidade da água. No caminho, descobre que o mesmo número conta histórias diferentes.

**A situação.** No Unoochat, o assistente pede o gráfico oficial da escola. A tabela traz 95%, 94%, 92% e 88%. O gráfico vai para o grupo da cidade. A escolha não é óbvia: um eixo acalma, o outro assusta.

**O que o estudante faz.** O estudante lê a tarefa no chat. Depois compara o eixo em 0% e o eixo em 80%. Ele escolhe um dos dois e publica, sem volta. Em seguida, lê os comentários dos moradores. A tela congela até o professor liberar.

**A virada.** Quase todo mundo acha que o gráfico mostra os números como eles são. No eixo em 80%, a barra encolhe cerca de 47%. Os números continuam iguais. O que mudou foi a régua.

**O que o estudante aprende.** O jeito de desenhar muda o que as pessoas entendem. O material chama isso de truncamento de eixo — começar a régua acima do zero. Isso vale para qualquer gráfico de notícia.

**O papel do professor.** O professor escolhe a missão e libera a turma. Quando a tela congela, ele pergunta o que mudou. Só ele libera a volta."""

LEITURA = f"""{oc.TITULO_IDEIA}

{IDEIA}

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
    com_lista = LEITURA.replace("**A virada.**", "- **A virada.**")
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
