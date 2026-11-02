"""A mecânica contada para o time e para o design: ficha de interação na seção 4 e 0.2 que a reconta (29/10/2026).

O time achava o one-pager difícil e confuso — «não fica claro o que o estudante tem que fazer» — e o design desenhava
telas sem saber quantos itens, que gesto, o que acontece se o estudante não age nem o que abre o momento seguinte. Na
exp09ef1b o 0.2 contou «Digitalizar cadernos» em dois passos sem dizer que eram caminhos diferentes, e o 0.1 tinha
frases de 72 palavras com quatro conceitos enfileirados. Estes testes fixam a ficha (`tools/ficha_interacao.py`), o 0.2
amarrado a ela e as regras de linguagem cobradas em código (`tools/one_pager_completo.py`).
"""
import asyncio
import json

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


def test_numero_por_extenso_volta_ao_redator():
    """Ao vivo (exp09ef1b, 30/10/2026) o redator escreveu «vinte e quatro vagas» e «doze mil reais»: o número por extenso
    escapava da conferência dos números. Fala entre aspas e contagem até doze passam."""
    extenso = IDEIA.replace("A tabela traz 95%, 94%, 92% e 88%.", "A tabela traz noventa e cinco por cento.")
    assert "numero-por-extenso" in _codigos(oc.validar(oc.encaixar(ONE_PAGER, LEITURA.replace(IDEIA, extenso))))
    assert "numero-por-extenso" not in _codigos(oc.validar(oc.encaixar(ONE_PAGER, LEITURA)))


def test_sinonimos_de_gesto_e_detalhamento_mecanico():
    """Sinônimos frequentes (`clicar`, `selecionar`, `observar`) mapeiam aos 12 verbos canônicos sem falso positivo, e
    descrições curtas demais (< 4 palavras) em `Na tela` ou `Resposta na hora` geram aviso `mecanica-pouco-detalhada`."""
    sinonimo = ONE_PAGER.replace("- **Gesto:** tocar · 2 botões", "- **Gesto:** clicar · 2 botões")
    assert "gesto-fora-da-lista" not in _codigos(fi.validar(sinonimo))
    curto = ONE_PAGER.replace(
        "- **Na tela:** o chat do assistente com 1 mensagem e o contador de 3 publicações.",
        "- **Na tela:** tela inicial.",
    )
    achados = fi.validar(curto)["achados"]
    assert any(a["codigo"] == "mecanica-pouco-detalhada" and a["severidade"] == "atencao" for a in achados)


def test_kpis_intervalo_telas_ts_payload_e_9f_plural():
    """Valida que `tools/kpis.py` aceita intervalos `E3-ALU-01..03`, chaves TypeScript sem aspas no payload e plural/singular
    na ação do sub-bloco 9f."""
    from tools import kpis

    assert "E3-ALU-02" in kpis._telas_expandidas("Telas `E3-ALU-01..03`")
    campos = kpis._campos_payload("{ tentativa_n: number, mudou_voto: boolean }")
    assert {"tentativa_n", "mudou_voto"} <= campos
    evts = {("ordenar", "criterio:ranking"): {"resultado": "{ordem}", "contexto": "{pesos}"}}
    assert kpis._resolver_acao_em_eventos(("ordenar", "criterios:ranking"), evts) == ("ordenar", "criterio:ranking")


def test_fidelidade_pedido_so_remocao_cumprido():
    """Pedido do PO que exige apenas remover um trecho (`inserir` vazio) é aprovado deterministicamente quando o trecho já
    saiu do documento."""
    from tools import fidelidade

    itens = [{"id": "F1", "origem": "refazer Produto · PO · 30/10/2026 10:00:00", "tipo": "exigencia",
              "texto": "Remover a pergunta do Canal B do final da missão."}]
    saida_juiz = json.dumps({"itens": [{"id": "F1", "veredito": "atendido", "citacao": "", "explicacao": "Saiu."}]})
    res = fidelidade.aplicar(
        itens,
        saida_juiz,
        {"one_pager": "Texto limpo da missão sem a pergunta antiga."},
        interpretacao={"F1": {"inserir": [], "remover": ["pergunta do Canal B"], "so_remocao": True}},
    )
    assert res["status"] == "aprovado"
    assert res["achados"] == []


def test_edicao_pontual_aspas_curvas_e_gesto_numeral_extenso_e_base_preservada():
    """Valida as melhorias da 2ª investigação:
    - fallback de aspas tipográficas em `tools/edicao_pontual.py`;
    - numeral por extenso em `gesto-sem-quantidade` de `tools/ficha_interacao.py`;
    - limpeza de `base_preservada_<chave>` em `pipeline/reexecucao.py`;
    - cobertura de `.moldura-desktop` em `tools/ilustracoes.py`."""
    from pipeline.reexecucao import preparar_estado
    from tools import edicao_pontual as ep
    from tools import ilustracoes

    doc_curvo = 'O estudante toca no botão “Confirmar envio” para concluir.'
    res_ep = ep.aplicar({"one_pager": doc_curvo}, [ep.Edicao("one_pager", 'botão "Confirmar envio"', 'botão "Enviar agora"')])
    assert res_ep.ok
    assert 'botão "Enviar agora" para concluir.' in res_ep.documentos["one_pager"]

    num_extenso = ONE_PAGER.replace("- **Gesto:** tocar · 2 botões", "- **Gesto:** tocar · dois botões")
    assert "gesto-sem-quantidade" not in _codigos(fi.validar(num_extenso))

    estado_sujo = {
        "one_pager": "versão atual",
        "base_preservada_one_pager": "versão antiga reprovada",
        "anexo_design_spec": "anexo atual",
        "base_preservada_anexo_design_spec": "anexo antigo",
    }
    limpo, _ = preparar_estado(estado_sujo, "produto")
    assert "base_preservada_one_pager" not in limpo

    assert ".moldura-desktop" in ilustracoes._CSS_QUADRO_AVULSO


def test_sem_canal_b_podcast_so_professor_e_sem_etapa_6():
    """Garante os três contratos pedidos pelo PO:
    1. Canal B (`multipla_escolha`) é rejeitado também na ficha §14.2 do PRD;
    2. Podcast de recapitulação em momento/tela do estudante (`Estudante` / `ALU` / `SIS`) bloqueia;
    3. Etapa 6 de transferência (atividade nova para reaplicar habilidades) bloqueia no one-pager e no inventário de telas."""
    from tools import prd_codavel, telas

    # 1. Etapa 6 e podcast na visão do estudante no one-pager
    com_etapa_6 = ONE_PAGER.replace(
        "## 9. Papel",
        "### Etapa 6 — Transferir\n\n#### Momento 6.1 — Nova atividade\n- **Quem age:** Estudante\n- **Gesto:** tocar · 1 botão\n"
        "- **Na tela:** o estudante ouve o podcast de recapitulação e aplica em outro caso.\n"
        "- **Resposta na hora:** o player abre na tela.\n- **Estado gravado:** transferencia_feita\n\n## 9. Papel",
    )
    cods_fi = _codigos(fi.validar(com_etapa_6))
    assert "etapa-6-removida" in cods_fi
    assert "podcast-na-tela-do-estudante" in cods_fi

    # 2. Etapa 6 e podcast em tela do estudante no inventário da jornada
    jornada = (
        "## Seção 3 — Inventário de telas\n\n"
        "| ID | Etapa | Ator | Peso | Estados | Propósito |\n"
        "|---|---|---|---|---|---|\n"
        "| E0-PROF-01 | 0 | PROF | leve | padrão | Escolher missão |\n"
        "| E0-PROF-02 | 0 | PROF | leve | padrão | Recorte da aula |\n"
        "| E0-PROF-03 | 0 | PROF | leve | padrão | Geração |\n"
        "| E0-PROF-04 | 0 | PROF | leve | padrão | Curadoria |\n"
        "| E0-PROF-05 | 0 | PROF | leve | padrão | Pôr no ar |\n"
        "| E5-ALU-02 | 5 | ALU | médio | padrão | Ouvir o podcast de recapitulação da missão |\n"
        "| E6-ALU-01 | 6 | ALU | denso | padrão | Transferência para nova atividade |\n"
    )
    res_telas = telas.cobertura({"jornada_telas": jornada, "fluxo_arestas": jornada,
                                 "copy_strings_revisada": jornada, "wireframes_cobertura": jornada})
    cods_telas = {a["codigo"] for a in res_telas["achados"]}
    assert "etapa-6-removida" in cods_telas
    assert "podcast-em-tela-do-estudante" in cods_telas

    # 3. `multipla_escolha` (Canal B) bloqueado em `prd_codavel`
    assert "multipla_escolha" not in prd_codavel._TIPOS_FICHA


def test_regressao_terceira_rodada_invariantes_e_falsos_positivos():
    """3ª rodada de auditoria (01/11/2026):
    1. Invariantes inegociáveis nunca são rebaixados por `linha_de_base.classificar`.
    2. Menção negativa a podcast («sem podcast») na tela do estudante não gera falso positivo.
    3. `evidencia.conferir_one_pager` bloqueia `etapa-6-removida` e `Canal B` por extenso.
    4. `prototipo.validar` bloqueia `etapa-6-removida` e `podcast-na-tela-do-estudante`."""
    from tools import evidencia, linha_de_base, prototipo

    for cod in ("etapa-6-removida", "podcast-na-tela-do-estudante", "canal-b-removido", "ficha-tipo-invalido"):
        achado = {"codigo": cod, "severidade": "bloqueio", "resumo": "Violação de invariante."}
        assert linha_de_base.classificar(achado, {"status": "aprovado", "achados": []}, "") == linha_de_base.DA_EDICAO

    sem_podcast = ONE_PAGER.replace(
        "o chat do assistente com 1 mensagem e o contador de 3 publicações.",
        "o chat do assistente com 1 mensagem, sem podcast para o aluno, e o contador de 3 publicações.",
    )
    assert "podcast-na-tela-do-estudante" not in _codigos(fi.validar(sem_podcast))

    op_12a_e6 = (
        "## 2. Habilidades BNCC\n- `EF06CO01`\n- `EF06CO02`\n\n"
        "## 12. Evidência\n### 12a. Contrato de evidência por habilidade\n"
        "| Habilidade (código) | Canal de evidência | Canal A: ação · etapa · regra ternária (Atingiu / Em processo / Não atingiu) |\n"
        "|---|---|---|\n"
        "| `EF06CO01` | Canal B | Atingiu se acertar, Em processo se tentar, Não atingiu se errar. |\n"
        "| `EF06CO02` | A | Etapa 6 (E6-ALU-01): Atingiu se acertar, Em processo se tentar, Não atingiu se errar. |\n"
    )
    cods_ev = {a["codigo"] for a in evidencia.conferir_one_pager(op_12a_e6)["achados"]}
    assert "canal-b-removido" in cods_ev
    assert "etapa-6-removida" in cods_ev

    html_invalido = (
        '<!doctype html><html><body>'
        '<section data-screen-id="E5-ALU-01" data-ator="ALU">Ouça o podcast de recapitulação da missão</section>'
        '<section data-screen-id="E6-ALU-01" data-ator="ALU">Etapa 6</section>'
        '</body></html>'
    )
    cods_proto = {a["codigo"] for a in prototipo.validar(html_invalido)["achados"]}
    assert "etapa-6-removida" in cods_proto
    assert "podcast-na-tela-do-estudante" in cods_proto




