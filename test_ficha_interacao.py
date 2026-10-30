"""A mecânica contada para o time e para o design: ficha de interação na seção 4 e 0.2 que a reconta (29/10/2026).

O time achava o one-pager difícil e confuso — «não fica claro o que o estudante tem que fazer» — e o design desenhava
telas sem saber quantos itens, que gesto, o que acontece se o estudante não age nem o que abre o momento seguinte. Na
exp09ef1b o 0.2 contou «Digitalizar cadernos» em dois passos sem dizer que eram caminhos diferentes, e o 0.1 tinha
frases de 72 palavras com quatro conceitos enfileirados. Estes testes fixam a ficha (`tools/ficha_interacao.py`), o 0.2
amarrado a ela e as regras de linguagem cobradas em código (`tools/one_pager_completo.py`).
"""
import asyncio

from agents.checkers import MecanicaCheckAgent
from agents.callbacks import extrair_envelope
from test_conteudo_aprovado import _rodar
from test_one_pager_completo import IDEIA, LEITURA, ONE_PAGER
from tools import ficha_interacao as fi
from tools import one_pager_completo as oc


def _codigos(resultado):
    return [a["codigo"] for a in resultado["achados"]]


# --- a ficha na seção 4 -------------------------------------------------------------------------------------------

def test_ficha_completa_passa_e_le_cada_momento():
    momentos = fi.extrair(ONE_PAGER)
    assert [m.id for m in momentos] == ["1.1", "2.1", "3.1", "4.1", "4.2", "5.1"]
    assert momentos[2].campos["Opções (n)"] == "2" and momentos[4].campos["Quem age"] == "Professor"
    resultado = fi.validar(ONE_PAGER)
    assert resultado["status"] == "aprovado", resultado["achados"]


def test_secao_4_sem_fichas_so_avisa():
    antigo = ONE_PAGER.split("### Etapa 1")[0] + "### Etapa 1 — Desafiar\nO estudante lê a tarefa.\n\n## 9. Papel\n"
    resultado = fi.validar(antigo)
    assert resultado["status"] == "amarelo" and _codigos(resultado) == ["secao-4-sem-fichas"]


def test_campo_que_falta_gesto_fora_da_lista_e_sem_quantidade_bloqueiam():
    sem_campo = ONE_PAGER.replace("- **Se não fizer:** o botão fica parado na tela até ele tocar.\n", "")
    assert "campo-ausente" in _codigos(fi.validar(sem_campo))
    gesto_vago = ONE_PAGER.replace("- **Gesto:** tocar · 2 botões", "- **Gesto:** interagir · 2 botões")
    assert "gesto-fora-da-lista" in _codigos(fi.validar(gesto_vago))
    sem_quantidade = ONE_PAGER.replace("- **Gesto:** tocar · 2 botões —", "- **Gesto:** tocar · os botões —")
    assert "gesto-sem-quantidade" in _codigos(fi.validar(sem_quantidade))
    # o que o PO ainda decide conta como preenchido: a ficha não bloqueia por decisão que não é do núcleo
    aberto = ONE_PAGER.replace("o assistente lembra da tarefa depois de 60 segundos.",
                               "[ABERTO — dono: PO: há lembrete? depois de quanto tempo?]")
    assert fi.validar(aberto)["status"] == "aprovado" and fi.validar(aberto)["abertos"] == 1


def test_escolha_sem_opcoes_e_consequencia_sem_relato_por_opcao():
    sem_opcoes = ONE_PAGER.replace('- **Opções (2):** "Eixo em 0%" · "Eixo em 80%"\n', "")
    assert "escolha-sem-opcoes" in _codigos(fi.validar(sem_opcoes))
    um_relato = ONE_PAGER.replace('  - Se "Eixo em 80%": os moradores pedem para fechar as escolas.\n', "")
    achados = fi.validar(um_relato)["achados"]
    assert any(a["codigo"] == "consequencia-sem-opcao" and "Eixo em 80%" in a["resumo"] for a in achados)


def test_caminho_dos_libera_ramo_sem_condicao_e_texto_de_tela():
    destino_errado = ONE_PAGER.replace("→ Momento 5.1", "→ Momento 5.3")
    codigos = _codigos(fi.validar(destino_errado))
    assert "libera-sem-destino" in codigos and "momento-inalcancavel" in codigos
    sem_fim = ONE_PAGER.replace("→ fim da missão", "→ Momento 1.1")
    assert "sem-fim" in _codigos(fi.validar(sem_fim))
    ramo = ONE_PAGER.replace("#### Momento 4.2 —", "#### Momento 4.2a —").replace("→ Momento 4.2", "→ Momento 4.2a")
    assert "ramo-sem-condicao" in _codigos(fi.validar(ramo))
    tela_sem_aspas = ONE_PAGER.replace('- **Texto de tela:** "Concluir"', "- **Texto de tela:** o botão de concluir")
    assert "texto-de-tela-ausente" in _codigos(fi.validar(tela_sem_aspas))


def test_mecanica_check_junta_a_ficha_ao_relatorio_e_ao_status():
    agente = MecanicaCheckAgent(name="A039ContaDaViradaOnePager", chave="one_pager",
                                report_key="mecanica_one_pager_report", status_key="mecanica_one_pager_status")
    quebrado = ONE_PAGER.replace("- **Gesto:** tocar · 2 botões", "- **Gesto:** interagir · 2 botões")
    estado = asyncio.run(_rodar(agente, {"one_pager": quebrado}))
    assert "# Ficha de interação" in estado["mecanica_one_pager_report"]
    envelope = extrair_envelope(estado["mecanica_one_pager_report"])
    assert envelope["status"] == estado["mecanica_one_pager_status"] == "bloqueado"
    assert any(a["codigo"] == "gesto-fora-da-lista" for a in envelope["achados"])


# --- o 0.2 amarrado à ficha ---------------------------------------------------------------------------------------

def _passos_trocados(antigo, novo):
    assert antigo in LEITURA, antigo
    return oc.encaixar(ONE_PAGER, LEITURA.replace(antigo, novo))


def test_cada_momento_contado_uma_vez_na_ordem():
    sem_momento = _passos_trocados("*Explicar · momento 5.1*", "*Explicar*")
    codigos = _codigos(oc.validar(sem_momento))
    assert "passo-sem-momento" in codigos and "momento-nao-contado" in codigos
    duas_vezes = _passos_trocados("*Explicar · momento 5.1*", "*Explicar · momento 4.2*")
    assert "momento-contado-duas-vezes" in _codigos(oc.validar(duas_vezes))
    fora_de_ordem = LEITURA.replace("*Desafiar · momento 1.1*", "*Desafiar · momento 2.1*") \
        .replace("*Navegar · momento 2.1*", "*Navegar · momento 1.1*")
    assert "passos-fora-da-ordem-da-missao" in _codigos(oc.validar(oc.encaixar(ONE_PAGER, fora_de_ordem)))
    inexistente = _passos_trocados("*Explicar · momento 5.1*", "*Explicar · momento 5.1 e 5.2*")
    assert "momento-inexistente" in _codigos(oc.validar(inexistente))


def test_passo_sem_campos_e_acao_repetida_sem_caminho():
    sem_campos = _passos_trocados("**Acontece:** a turma compara os gráficos.\n", "")
    assert "passo-sem-campos" in _codigos(oc.validar(sem_campos))
    sem_se_nao_fizer = _passos_trocados("**Se não fizer:** o botão fica parado na tela.\n", "")
    assert "passo-sem-se-nao-fizer" in _codigos(oc.validar(sem_se_nao_fizer))
    # o mesmo botão na ação de dois passos — o «Digitalizar cadernos» dos passos 4 e 6 da exp09ef1b
    repetido = _passos_trocados("**O estudante:** arrasta 1 régua até 0%.",
                                "**O estudante:** escolhe 1 de 2 gráficos e toca em \"Publicar\".")
    assert "acao-repetida" in _codigos(oc.validar(repetido))


# --- a linguagem cobrada em código --------------------------------------------------------------------------------

#: O 0.1 da exp09ef1b de 28/10/2026, encurtado: o que o time achou difícil.
IDEIA_DIFICIL = """O estudante consulta o assistente sobre as opções: o Mesa Aberta oferece 24 vagas de almoço no contraturno, \
mas só tem 1 documento cadastrado no sistema, enquanto a máquina recomenda destinar todo o dinheiro para o projeto com \
mais relatórios, e na hora de votar o estudante organiza três critérios num ranking arrastável.

Na explicação, Amara sistematiza os conceitos: viés algorítmico — distorções quando faltam dados —, dados do passado — \
registros antigos que carregam desigualdades — e decisões automatizadas — escolhas feitas por robôs.

A inteligência artificial deverá gerar um relatório formativo completo no painel do professor."""


def test_ideia_dificil_volta_ao_redator_pelos_motivos_certos():
    leitura = LEITURA.replace(IDEIA, IDEIA_DIFICIL)
    codigos = _codigos(oc.validar(oc.encaixar(ONE_PAGER, leitura)))
    for codigo in ("frase-longa", "frases-longas-em-media", "conceitos-numa-frase", "palavra-dificil",
                   "um-nome-por-coisa", "futuro-ou-condicional", "ideia-sem-bloco"):
        assert codigo in codigos, codigo


def test_virada_sem_crenca_bloco_longo_e_jargao_pedagogico():
    sem_crenca = IDEIA.replace("Quase todo mundo acha que o gráfico mostra os números como eles são. ", "")
    assert "virada-sem-crenca" in _codigos(oc.validar(oc.encaixar(ONE_PAGER, LEITURA.replace(IDEIA, sem_crenca))))
    longo = IDEIA.replace("**Em uma frase.** ", "**Em uma frase.** " + "O estudante decide. " * 20)
    assert "bloco-longo" in _codigos(oc.validar(oc.encaixar(ONE_PAGER, LEITURA.replace(IDEIA, longo))))
    pedagogico = IDEIA.replace("O professor escolhe a missão", "A mediação docente propicia o protagonismo do aluno")
    achados = oc.validar(oc.encaixar(ONE_PAGER, LEITURA.replace(IDEIA, pedagogico)))["achados"]
    assert sum(a["codigo"] == "jargao" for a in achados) >= 3


def test_fala_que_termina_em_ponto_fecha_a_frase():
    """Ao vivo (exp09ef1b, 30/10/2026): «… a mensagem de Amara: “… conselheiro.” Três cartões resumem…» — o ponto dentro
    das aspas fecha a frase; sem ele, as duas viravam uma frase de 33 palavras."""
    texto = ("**Na tela:** a tela do ChatGPT com a mensagem de Amara: “Doze mil reais. Um projeto fica, dois ficam sem nada. "
             "A decisão é sua, conselheiro.” Três cartões resumem os projetos: Mesa Aberta com 24 vagas, Ponto de Apoio "
             "com 18 vagas e Conexão para Continuar com 20 vagas.")
    assert max(len(f.split()) for f in oc._frases(texto)) <= oc.MAX_PALAVRAS_FRASE
