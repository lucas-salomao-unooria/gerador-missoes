"""C3 do backlog de 24/10/2026: falsos positivos dos juízes e lints de produto.

O levantamento de produto (287 achados, 38% falsos; 59% nos determinísticos) apontou sete defeitos de régua. Os casos
reais estão no gabarito (`tests/gabarito_achados/test_gabarito_produto.py`); aqui ficam as regras, uma a uma, com o
texto mínimo que as exercita.
"""
import asyncio
import json

from google.adk.agents.sequential_agent import SequentialAgent

from test_conteudo_aprovado import _rodar


# --------------------------------------------------------------------------- 1. cobertura: aspas e material do PO
MAPA = ("| ID | Conceito | Papel | Trecho do material | O que o estudante faz |\n|---|---|---|---|---|\n"
        "| C1 | Engajamento | limiar | \"o algoritmo prioriza o 'engajamento' e não a verdade dos fatos\" | x |\n")


def test_citacao_com_aspas_trocadas_esta_no_material():
    from tools.profundidade import validar_cobertura

    material = 'Texto: o algoritmo prioriza o "engajamento" e não a verdade dos fatos, diz a apostila.'
    achados = validar_cobertura("núcleo", MAPA, material)["achados"]
    assert "trecho-inexistente" not in [a["codigo"] for a in achados]
    reescrito = validar_cobertura("núcleo", MAPA.replace("verdade", "qualidade"), material)["achados"]
    assert "trecho-inexistente" in [a["codigo"] for a in reescrito]


def test_material_do_po_vem_dos_pedidos_pareceres_e_anexos_sem_o_cabecalho_da_esteira():
    from pipeline.reexecucao import PedidoCorrecao
    from tools.profundidade import material_do_po

    pedido = PedidoCorrecao(texto="Segue a apostila.", anexos=[("apostila.docx", "Capítulo 2: fonte, data e autoria.")])
    estado = {
        "pedidos_do_po": [{"texto": "Material colado: Bento publica sem verificar.", "etapa": "produto"}],
        "pareceres_humanos": [{"comentario": "No parecer: a verificabilidade importa."}],
        "notas_de_passagem": "## Pedidos\n\n> Nas notas: critérios verificáveis.\nTexto da esteira, não do PO.",
        "pedido_correcao": pedido.como_markdown("produto"),
    }
    texto = material_do_po(estado)
    for trecho in ("Bento publica sem verificar", "a verificabilidade importa", "critérios verificáveis",
                   "Segue a apostila", "fonte, data e autoria"):
        assert trecho in texto
    assert "Esta execução refaz" not in texto and "Texto da esteira" not in texto and "Como agir" not in texto


# --------------------------------------------------------------------------- 2. decisão atribuída ao PO
def test_registro_do_po_e_verdadeiro_nos_mesmos_casos_do_booleano():
    from tools.decisoes import ha_registro_do_po

    assert not ha_registro_do_po({}) and not ha_registro_do_po({"briefing": "secao_ds: unoovista"})
    for estado in ({"pedidos_do_po": [{"texto": "x"}]}, {"notas_de_passagem": "x"}, {"pedido_correcao": "x"},
                   {"one_pager_po": "x"}):
        assert ha_registro_do_po(estado)


def test_so_o_registro_estruturado_confirma_a_atribuicao():
    """3ª revisão do PR #80 (25/10/2026): o texto livre dos pedidos e pareceres não confirma mais nada — nem o trecho
    literal, nem o «Pedido N», nem a marca `[HOMOLOGADO pelo PO]` que o PO mandou escrever. Confirmam só a linha idêntica
    no one-pager que o PO anexou e a decisão gravada no cartão do de acordo."""
    from tools.decisoes import achados, ha_registro_do_po

    pedidos = {"pedidos_do_po": [
        {"texto": "Refaça a etapa 3."},
        {"texto": "1. Tetos: HOMOLOGADOS. Cravar 60 palavras por legenda de projeto no feed.\n\n"
                  "2. PQ-01 a PQ-03: trocar o marcador por [HOMOLOGADO pelo PO]."}]}
    reg = ha_registro_do_po(pedidos)
    for linha in ("Teto (homologado pelo PO): 60 palavras por legenda de projeto no feed.",
                  "Teto cravado em 60 palavras (aprovado pelo PO no Pedido 2).",
                  "| PQ-02 | pergunta | [HOMOLOGADO pelo PO] |"):
        assert not reg.confirma(linha), linha
    # a pista diz de onde a decisão parece vir, e o PO confere
    achado = [a for a in achados("- Teto cravado em 60 palavras (aprovado pelo PO no Pedido 2).", "O one-pager", reg)
              if a["codigo"] == "decisao-atribuida-ao-po"]
    assert [a["severidade"] for a in achado] == ["atencao"]
    assert "o Pedido 2: «1. Tetos: HOMOLOGADOS" in achado[0]["resumo"] and "registro estruturado" in achado[0]["resumo"]

    # a linha idêntica (a menos de espaços) no one-pager que o PO anexou confirma; a parecida não
    anexo = {**pedidos, "one_pager_po": "## 15. Tetos\n5. **Tetos (homologados pelo PO):**  60 palavras por legenda.\n"}
    reg = ha_registro_do_po(anexo)
    assert reg.confirma("5. **Tetos (homologados pelo PO):** 60 palavras por legenda.")
    assert not reg.confirma("5. **Tetos (homologados pelo PO):** 60 palavras por legenda. E 90 por cartão.")
    assert not reg.confirma("**Tetos (homologados pelo PO):** 60 palavras")
    texto = "5. **Tetos (homologados pelo PO):** 60 palavras por legenda.\n- Corte (aprovado pelo PO): 3 etapas."
    restam = [a for a in achados(texto, "O one-pager", reg) if a["codigo"] == "decisao-atribuida-ao-po"]
    assert len(restam) == 1 and "3 etapas" in restam[0]["resumo"] and "1 outra(s)" in restam[0]["resumo"]
    # com o booleano de antes, nada muda
    assert len([a for a in achados(texto, "O one-pager", True) if a["codigo"] == "decisao-atribuida-ao-po"]) == 1
    assert [a["severidade"] for a in achados(texto, "O one-pager", False)
            if a["codigo"] == "decisao-atribuida-ao-po"] == ["bloqueio"]


def test_recusa_em_prosa_nunca_confirma():
    """M1 da 3ª revisão do PR #80 (p1_recusas, 25/10/2026): sobre o parecer real da exp02em1b (21/10/2026 15:43:51), 12
    de 27 maneiras de recusar o StoryPoll em prosa («→ não, manter o quiz atual», «→ sem aprovação», «→ aprovado? não»)
    confirmavam «aprovado pelo PO» pelo trecho literal. Sem a leitura do texto livre, nenhuma confirma — e a ressalva do
    juiz continua contando."""
    from tools.decisoes import ha_registro_do_po
    from tools.juizes_produto import recontar

    storypoll = "- Utilização do componente StoryPoll nativo como suporte ao Canal B (aprovado pelo PO)."
    env = {"status": "aprovado_com_ressalvas", "achados": [{"severidade": "atencao", "codigo": "6.2", "resumo": (
        "Utilização do componente StoryPoll nativo como suporte ao Canal B, aprovado pelo PO, adiciona carga.")}]}
    for resposta in ("ignorar / não implementar", "não, manter o quiz atual", "sem aprovação", "aprovado? não",
                     "fechado: sem StoryPoll", "aprovado só o Canal A; StoryPoll fica de fora", "aprovado"):
        estado = {"pareceres_humanos": [{"etapa": "produto", "comentario": (
            "[PROPOSTA P0b: validar com PO: Utilização do componente StoryPoll nativo como suporte ao Canal B] → "
            + resposta)}]}
        assert not ha_registro_do_po(estado).confirma(storypoll), resposta
        novo, nota = recontar(env, estado)
        assert novo["status"] == "aprovado_com_ressalvas" and novo["achados"][0]["a_conferir"], resposta
        assert "a conferir" in nota


def test_recusa_no_de_acordo_nunca_confirma_e_a_atribuicao_contraria_fica_para_conferir():
    """Revisão do PR #80 (24/10/2026): a decisão recusada no de acordo confirmava «aprovado pelo PO» pelo valor da
    sugestão. Na 3ª revisão (25/10/2026) a linha que parece falar do recusado deixa de ser ⛔: a semelhança com o assunto
    é comparação de palavras, e interpretação não bloqueia sozinha — fica ⚠️ com a recusa na mensagem."""
    from tools import fechar_contrato as fc
    from tools.decisoes import achados, ha_registro_do_po
    from tools.juizes_produto import recontar

    one_pager = ("- `[PROPOSTA — validar com PO: Utilização do componente StoryPoll nativo como suporte ao Canal B]`\n"
                 "- Inatividade: `[PARÂMETRO — a definir por produto: tempo de inatividade no chat, sugestão: 90 "
                 "segundos]`\n")
    itens = fc.itens_em_aberto({"one_pager": one_pager})
    assert len(itens) == 2

    def com(resposta):
        return {"pedidos_do_po": [{"texto": "refaça"}], "decisoes_do_po": fc.decidir(
            itens, {i.id: {"resposta": resposta} for i in itens}, "21/10/2026 15:43:00", "produto").decisoes}

    estado = com("recusar")
    reg = ha_registro_do_po(estado)
    storypoll = "- Utilização do componente StoryPoll nativo como suporte ao Canal B (aprovado pelo PO)."
    assert not reg.decisao_gravada(storypoll) and not reg.confirma(storypoll) and reg.decisao_recusada(storypoll)
    achado = [a for a in achados(storypoll, "O one-pager", reg) if a["codigo"] == "decisao-atribuida-ao-po"]
    assert [a["severidade"] for a in achado] == ["atencao"] and "recusado pelo PO no de acordo" in achado[0]["resumo"]
    assert [a["severidade"] for a in achados("Tempo de inatividade no chat: 90 s (homologado pelo PO).", "X", reg)] == [
        "atencao"]
    # duas palavras em comum com o assunto recusado não bastam para dizer que fala dele
    assert not reg.decisao_recusada("Seções do DS como suporte ao Canal B (aprovado pelo PO).")
    env = {"status": "aprovado_com_ressalvas", "achados": [{"severidade": "atencao", "codigo": "6.2", "resumo": (
        "Utilização do componente StoryPoll nativo como suporte ao Canal B, aprovado pelo PO, adiciona carga.")}]}
    novo, _ = recontar(env, estado)
    assert novo["status"] == "aprovado_com_ressalvas" and "recusado pelo PO" in novo["achados"][0]["a_conferir"]
    # aceitar a mesma sugestão confirma
    aceito = ha_registro_do_po(com("aceitar"))
    assert aceito.confirma(storypoll) and aceito.confirma("Tempo de inatividade no chat: 90 s (homologado pelo PO).")
    # registros que se contradizem — o one-pager anexado traz a linha, o cartão a recusou — não confirmam
    contraditorio = {**estado, "one_pager_po": storypoll}
    assert ha_registro_do_po(contraditorio).linha_do_anexo(storypoll)
    assert not ha_registro_do_po(contraditorio).confirma(storypoll)


def test_pareceres_da_esteira_invalidados_ou_de_outra_etapa_nao_sao_fonte_do_po():
    """M2 da 3ª revisão do PR #80 (25/10/2026): a devolução automática da esteira (`autor: "esteira"`), o parecer
    invalidado por um refazer e o de design não são palavra do PO sobre produto — nem na pista."""
    from tools.decisoes import ha_registro_do_po

    def parecer(**kw):
        return {"etapa": "produto", "autor": "po@unooria.com", "quando": "21/10/2026 15:43:51", "valido": True,
                "comentario": "4. Tempo em tela de 29 min: RESSALVA ACEITA.", **kw}

    achado = "Tempo em tela de 29 min homologado pelo PO."
    assert "parecer de produto de 21/10/2026" in ha_registro_do_po({"pareceres_humanos": [parecer()]}).decisao_repetida(
        achado)
    for outro in (parecer(autor="esteira"), parecer(valido=False), parecer(etapa="design")):
        assert ha_registro_do_po({"pareceres_humanos": [outro]}).decisao_repetida(achado) == "", outro


def test_numeros_com_unidade_normalizados():
    from tools.decisoes import numeros_com_unidade

    assert numeros_com_unidade("após 60 segundos, 29 min em tela e 25 palavras") == ["60 s", "29 min", "25 palavras"]
    assert numeros_com_unidade("toast aos 60s; 2,5 s de espera") == ["60 s", "2.5 s"]


# --------------------------------------------------------------------------- 3 e 4. juízes recontados
def _relatorio(status, achados):
    return "# Juiz\n\n```json\n" + json.dumps({"status": status, "achados": achados, "precisa_humano": True},
                                                  ensure_ascii=False) + "\n```"


_PEDIDO = {"pedidos_do_po": [{"texto": "4. Tempo em tela de 29 min: RESSALVA ACEITA. O tempo de 29 min em tela para "
                                       "aula de 50 min é uma ressalva aceita pelo PO."}]}
_REPETE = {"severidade": "atencao", "codigo": "6.2",
           "resumo": "Tempo em tela de 29 min acima do teto de 25 min, mantido como ressalva homologada pelo PO."}
_PROPOSTAS = {"severidade": "decisao_humana", "codigo": "F7",
              "resumo": "Propostas e parâmetros do one-pager aguardando homologação do PO."}


def test_ressalva_que_repete_decisao_do_po_conta_a_conferir():
    """3ª revisão do PR #80 (25/10/2026): o achado que diz que o PO decidiu não sai mais da contagem — fica 🟡 com a marca
    «a conferir» e a pista de onde a decisão parece estar. Separar a repetição da denúncia é interpretar o sentido."""
    from tools.juizes_produto import recontar, status_recontado

    novo, nota = recontar({"status": "aprovado_com_ressalvas", "achados": [_REPETE]}, _PEDIDO)
    assert novo["status"] == "aprovado_com_ressalvas" and "veredito_original" not in novo
    assert novo["achados"][0]["codigo"] == "6.2"
    assert novo["achados"][0]["a_conferir"].startswith("a conferir: parece repetir a decisão do PO — o Pedido 1:")
    assert "a conferir" in nota and "continuam contando" in nota
    assert status_recontado(_relatorio("aprovado_com_ressalvas", [_REPETE]), _PEDIDO)["status"] == "amarelo"
    # sem registro do PO, a marca diz que a sessão não tem
    novo, _ = recontar({"status": "aprovado_com_ressalvas", "achados": [_REPETE]}, {})
    assert "a sessão não tem" in novo["achados"][0]["a_conferir"]
    # com outro número, a pista diz o valor divergente
    outro = {**_REPETE, "resumo": _REPETE["resumo"].replace("29 min", "35 min")}
    assert status_recontado(_relatorio("aprovado_com_ressalvas", [outro]), _PEDIDO)["status"] == "amarelo"
    # ressalva que não diz que o PO decidiu não ganha marca
    sem_po = {**_REPETE, "resumo": "Tempo em tela de 29 min acima do teto de 25 min."}
    assert recontar({"status": "aprovado_com_ressalvas", "achados": [sem_po]}, _PEDIDO)[1] == ""


def test_bloqueio_do_juiz_nao_e_recontado():
    from tools.juizes_produto import recontar

    bloqueio = {"severidade": "bloqueio", "codigo": "F2", "resumo": "habilidade cortada"}
    env = {"status": "bloqueado", "achados": [_REPETE, bloqueio]}
    assert recontar(env, _PEDIDO) == (env, "")
    env = {"status": "aprovado_com_ressalvas", "achados": [_REPETE, bloqueio]}
    assert recontar(env, _PEDIDO) == (env, "")


def test_proposta_aberta_vai_ao_de_acordo_so_no_gate_final_e_com_itens():
    from tools.juizes_produto import recontar

    one_pager = "## 15. Tetos\n- Teto: `[PARÂMETRO — a definir por produto: palavras por balão · sugestão: 35 palavras]`\n"
    env = {"status": "aprovado_com_ressalvas", "achados": [_PROPOSTAS], "precisa_humano": True}
    assert recontar(env, {"one_pager": one_pager})[1] == ""  # sem a flag do gate final
    novo, nota = recontar(env, {"one_pager": one_pager}, contrato_no_de_acordo=True)
    assert novo["status"] == "aprovado" and novo["precisa_humano"] is False
    assert novo["na_lista_do_de_acordo"][0]["itens_no_de_acordo"] == 1 and "lista do de acordo" in nota
    # sem marcador aberto, o 🔵 fica
    assert recontar(env, {"one_pager": "## 15. Tetos\n- Teto: 35 palavras."}, contrato_no_de_acordo=True)[1] == ""


def test_achado_misto_do_gate_final_fica_na_contagem():
    """Revisão do PR #80: o achado que fala de proposta e de outra coisa não sai inteiro para o de acordo — o que ele diz
    tem de estar nos itens da lista."""
    from tools.juizes_produto import recontar

    one_pager = ("## 18. Propostas\n- `[PROPOSTA P0b — validar com PO: botão de zoom na tabela de metadados]`\n"
                 "- `[PROPOSTA — validar com PO: abertura da 3ª aba da conversa com a escola rival]`\n")

    def status(resumo):
        env = {"status": "aprovado_com_ressalvas", "precisa_humano": True,
               "achados": [{"severidade": "decisao_humana", "codigo": "F7", "resumo": resumo}]}
        return recontar(env, {"one_pager": one_pager}, contrato_no_de_acordo=True)[0]["status"]

    assert status("Propostas abertas na Seção 18 aguardando validação do PO (3ª aba da escola rival e botão de zoom "
                  "na tabela).") == "aprovado"
    assert status("Propostas e parâmetros do one-pager aguardando homologação do PO.") == "aprovado"
    assert status("Propostas P0b e a divergência entre o briefing e o critério 6.2 aguardam homologação do "
                  "PO") == "aprovado_com_ressalvas"
    assert status("Propostas abertas (botão de zoom na tabela) e o conflito com o briefing aguardam o parecer do "
                  "PO.") == "aprovado_com_ressalvas"


def test_gate_de_envelope_reconta_e_grava_a_nota():
    from agents.checkers import EnvelopeGateAgent

    def gate():
        return EnvelopeGateAgent(name="G", rotulo="Gate final", report_key="r", status_key="s",
                                 block_pipeline_on_fail=False, recontar_decisoes_do_po=True, contrato_no_de_acordo=True)

    one_pager = "- `[PROPOSTA — validar com PO: botão de zoom na tabela]`\n"
    # o 🔵 do contrato vai ao de acordo; a ressalva que diz que o PO decidiu fica, a conferir (3ª revisão, 25/10/2026)
    final = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[gate()]), {
        **_PEDIDO, "one_pager": one_pager, "r": _relatorio("aprovado_com_ressalvas", [_REPETE, _PROPOSTAS])}))
    assert final["s"] == "amarelo" and final["s_envelope"]["achados"][0]["a_conferir"]
    assert "Recontado em código" in final["r"] and "a conferir" in final["r"] and "lista do de acordo" in final["r"]
    final = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[gate()]), {
        **_PEDIDO, "one_pager": one_pager, "r": _relatorio("aprovado_com_ressalvas", [_PROPOSTAS])}))
    assert final["s"] == "aprovado" and final["s_envelope"]["veredito_original"] == "aprovado_com_ressalvas"
    # sem a flag, o gate de sempre
    comum = EnvelopeGateAgent(name="G", rotulo="Gate final", report_key="r", status_key="s",
                              block_pipeline_on_fail=False)
    final = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[comum]), {
        **_PEDIDO, "one_pager": one_pager, "r": _relatorio("aprovado_com_ressalvas", [_REPETE, _PROPOSTAS])}))
    assert final["s"] == "amarelo" and "Recontado" not in final["r"]


def test_juizes_de_produto_ligados_na_esteira():
    from agents.produto import build_produto_stage
    from agents.checkers import EnvelopeGateAgent
    from pipeline.orchestrator import iter_agent_tree

    gates = {a.name: a for _, a in iter_agent_tree(build_produto_stage()) if isinstance(a, EnvelopeGateAgent)}
    assert gates["A044GateFinalProdutoCheck"].recontar_decisoes_do_po and gates["A044GateFinalProdutoCheck"].contrato_no_de_acordo
    for nome in ("A030AvaliacaoCheck", "A031ExperienciaCheck"):
        assert gates[nome].recontar_decisoes_do_po and not gates[nome].contrato_no_de_acordo
    assert not gates["A027GateEstruturalCheck"].recontar_decisoes_do_po


def test_prompts_dos_juizes_dizem_que_decisao_do_po_nao_e_ressalva():
    from prompts import load_prompt

    for arquivo in ("produto/029a_avaliacao_pedagogica.md", "produto/029b_experiencia_estudante.md",
                    "produto/043_gate_final.md"):
        assert "Decisão do PO registrada não é ressalva" in load_prompt(arquivo)
    gate_final = load_prompt("produto/043_gate_final.md")
    assert "lista do de acordo de produto" in gate_final and "Não a repita em" in gate_final


# --------------------------------------------------------------------------- 5. seções extras do DS
def test_valor_do_campo_e_so_a_lista_de_secoes():
    from tools.secoes import extras

    assert extras("**Seções extras do DS:** nenhuma · **Modalidade:** duplas por aparelho · **Público:** estudante") == []
    assert extras("**Seções extras do DS:** `unoochat` (compartilhar) · **Modalidade:** x") == ["unoochat"]
    assert extras("Seções extras do DS: nenhuma — a missão é de seção única") == []
    assert extras("- `secoes_ds_extras: [unoochat, unoovista]`") == ["unoochat", "unoovista"]
    assert extras("Seções extras do DS: unoochat e unoovista.") == ["unoochat", "unoovista"]
    assert extras("- `secoes_ds_extras: nova:galeria`") == ["nova:galeria"]
    # o campo seguinte da mesma linha não é valor dele, nem quando nomeia uma seção
    assert extras("**Seções extras do DS:** nenhuma · **Seção do DS:** `unoovista` · **Série:** 7EF") == []


def test_secao_0_vale_sobre_o_changelog():
    from tools.secoes import extras

    texto = ("# One-pager\n\n## Changelog\n- Seções extras do DS: `unoochat` (versão anterior)\n\n"
             "## 0. Identificação\n- Seções extras do DS: nenhuma\n")
    assert extras(texto) == []
    assert extras(texto.replace("Seções extras do DS: nenhuma", "Seções extras do DS: `unoojornal`")) == ["unoojornal"]


def test_prosa_no_campo_so_conta_pelas_secoes_que_nomeia(monkeypatch):
    from tools import rastro
    from tools.secoes import extras

    monkeypatch.setattr(rastro, "secoes_ds", lambda: {"unoochat": "ds-unoochat", "unoovista": "ds-unoovista"})
    assert extras("Seções extras do DS: o compartilhamento abre o unoochat no fim") == ["unoochat"]
    assert extras("## Changelog\nSeções extras do DS: removida a menção ao unoochat") == []


# --------------------------------------------------------------------------- 6. texto da esteira fora do checklist
def test_checklist_sem_o_cabecalho_e_sem_como_agir():
    from pipeline.reexecucao import PedidoCorrecao
    from tools.fidelidade import montar_checklist, sem_texto_da_esteira

    md = PedidoCorrecao(texto="Trocar o título da Etapa 2 para «A Caça ao Boato».").como_markdown("produto")
    limpo = sem_texto_da_esteira("Antes do pedido colado.\n\n" + md)
    assert "Esta execução refaz" not in limpo and "Como agir" not in limpo and "Aplique o pedido" not in limpo
    assert "Antes do pedido colado." in limpo and "A Caça ao Boato" in limpo
    itens = montar_checklist([("pedido", md)], "")
    assert itens and not [i for i in itens if "Esta execução" in i["texto"] or "no que é seu" in i["texto"]]
    assert sem_texto_da_esteira("Pedido simples, sem cabeçalho.") == "Pedido simples, sem cabeçalho."


def test_checklist_tira_so_os_blocos_da_esteira_e_o_que_o_po_escreve_depois_fica():
    """Revisão do PR #80 (24/10/2026): o corte ia do «Como agir» até o fim, e o pedido novo escrito depois do markdown
    colado sumia. Saem o cabeçalho, a triagem, os textos-chave citados, o material anexado (mesmo com títulos próprios) e
    as três regras — também copiadas da tela, sem o negrito."""
    from pipeline.reexecucao import PedidoCorrecao
    from tools.fidelidade import montar_checklist, sem_texto_da_esteira
    from tools.textos_chave import TITULO_CITADOS

    md = PedidoCorrecao(
        texto="Trocar o título da Etapa 2 para «A Caça ao Boato».", anexos=[("roteiro.md", "### Parte 1\n\nTexto do anexo.")],
        nota_da_esteira="Estes são os itens de produto de um pedido feito pelo PO em design, triados item a item.",
        textos_chave_citados=f"### {TITULO_CITADOS}\n\n- `TC-07` — texto aprovado: «Vamos lá»").como_markdown("produto")
    depois = "\n\nAlém disso:\n\n1. Trocar o título da Etapa 3 para «A plenária decide».\n2. Aumentar o botão Votar para 48 px."
    for colado in (md, md.replace("**", "")):
        limpo = sem_texto_da_esteira("Antes do pedido colado.\n\n" + colado + depois)
        for da_esteira in ("Esta execução refaz", "Pedido, na íntegra", "triados item a item", TITULO_CITADOS, "TC-07",
                           "Material anexado", "Texto do anexo", "Parte 1", "Como agir", "no que é seu",
                           "Não invente o resto", "O que mudou nesta versão"):
            assert da_esteira not in limpo, da_esteira
        for do_po in ("Antes do pedido colado.", "A Caça ao Boato", "A plenária decide", "48 px"):
            assert do_po in limpo, do_po
    itens = [i["texto"] for i in montar_checklist([("pedido", md + depois)], "")]
    assert any("A plenária decide" in t for t in itens) and any("48 px" in t for t in itens)
    # sem o «Como agir» depois, o anexo vai só até o próximo título
    assert sem_texto_da_esteira("### Material anexado ao pedido\n\nNenhum.\n\n## Pedido novo\n\nTrocar X.") == \
        "## Pedido novo\n\nTrocar X."


# --------------------------------------------------------------------------- 7. banca no fim de produto
def test_banca_de_produto_nao_conta_ped_03_12_15_e_as_outras_posicoes_contam():
    from tools import banca as bnc

    env = {"status": "aprovado_com_ressalvas", "achados": [
        {"id": "PED-12", "severidade": "atencao", "resumo": "gestor só agregado"},
        {"id": "PED-15", "severidade": "nok", "resumo": "playtest"},
        {"id": "PED-03", "severidade": "atencao", "resumo": "medida × cosmético"}], "contagem": {"nok": 1}}
    r = bnc.consolidar({"banca_produto_pedagogia": json.loads(json.dumps(env))})
    assert r["status"] == "aprovado" and r["achados"] == [] and len(r["outra_posicao"]) == 3
    assert bnc.consolidar({"banca_entrada_pedagogia": json.loads(json.dumps(env))})["status"] == "amarelo"
    assert bnc.consolidar({"validacao_pedagogia_bncc": json.loads(json.dumps(env))})["status"] == "amarelo"
    com_outro = json.loads(json.dumps(env))
    com_outro["achados"].append({"id": "PED-02", "severidade": "atencao", "resumo": "matriz"})
    assert bnc.consolidar({"banca_produto_pedagogia": com_outro})["status"] == "amarelo"
    # o escopo da posição diz ao juiz o mesmo que o código conta
    assert all(c in bnc.ESCOPOS["produto"] for c in ("PED-03", "PED-12", "PED-15"))
    assert not any(c in bnc.ESCOPOS["entrada"] for c in ("PED-03", "PED-12", "PED-15"))


def test_divergencia_da_entrada_nao_diz_que_passou_onde_nao_e_avaliado():
    """Revisão do PR #80: o PED-12 que reprova na entrada do dev saía «passou no fim de produto», onde não é avaliado."""
    from tools import banca as bnc

    entrada = {"achados": [{"id": "PED-12", "severidade": "nok"}, {"id": "PROD-07", "severidade": "bloqueio"}]}
    assert bnc.divergencias_com_etapas(entrada, {"produto": {"achados": []}, "design": {"achados": []}}) == [
        "`PED-12` passou no fim de design e reprova aqui. No fim de produto ele não é avaliado.",
        "`PROD-07` passou no fim de produto e de design e reprova aqui."]
    # só produto rodou: o PED-12 não tem com que comparar
    assert bnc.divergencias_com_etapas(entrada, {"produto": {"achados": []}, "design": None}) == [
        "`PROD-07` passou no fim de produto e reprova aqui."]
