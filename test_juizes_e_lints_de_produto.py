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


def test_atribuicao_conferida_por_trecho_numero_pedido_e_marca():
    from tools.decisoes import achados, ha_registro_do_po

    estado = {"pedidos_do_po": [
        {"texto": "Refaça a etapa 3."},
        {"texto": "1. Tetos: HOMOLOGADOS. Cravar 60 palavras por legenda de projeto no feed.\n\n"
                  "2. PQ-01 a PQ-03: trocar o marcador por [HOMOLOGADO pelo PO].\n\n"
                  "3. Não aceito os 40 min de tela por cartão de leitura."}]}
    reg = ha_registro_do_po(estado)
    # trecho literal com o mesmo número
    assert reg.confirma("Teto (homologado pelo PO): 60 palavras por legenda de projeto no feed.")
    assert not reg.confirma("Teto (homologado pelo PO): 90 palavras por legenda de projeto no feed.")
    # o «Pedido 2» decide e traz o número
    assert reg.confirma("Teto cravado em 60 palavras (aprovado pelo PO no Pedido 2).")
    assert not reg.confirma("Teto cravado em 60 palavras (aprovado pelo PO no Pedido 1).")
    # a marca que o PO mandou escrever, só nos itens da ordem
    assert reg.confirma("| PQ-02 | pergunta | [HOMOLOGADO pelo PO] |")
    assert not reg.confirma("| PQ-04 | pergunta | [HOMOLOGADO pelo PO] |")
    # o parágrafo que nega não confirma
    assert not reg.confirma("Tempo de 40 min de tela por cartão de leitura (aprovado pelo PO).")
    texto = "- Teto (homologado pelo PO): 60 palavras por legenda de projeto no feed.\n- Corte (aprovado pelo PO): 3 etapas."
    restam = [a for a in achados(texto, "O one-pager", reg) if a["codigo"] == "decisao-atribuida-ao-po"]
    assert len(restam) == 1 and "3 etapas" in restam[0]["resumo"] and "1 outra(s)" in restam[0]["resumo"]
    # com o booleano de antes, nada muda
    assert len([a for a in achados(texto, "O one-pager", True) if a["codigo"] == "decisao-atribuida-ao-po"]) == 1
    assert [a["severidade"] for a in achados(texto, "O one-pager", False)
            if a["codigo"] == "decisao-atribuida-ao-po"] == ["bloqueio"]


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


def test_ressalva_que_repete_decisao_do_po_nao_conta():
    from tools.juizes_produto import recontar, status_recontado

    novo, nota = recontar({"status": "aprovado_com_ressalvas", "achados": [_REPETE]}, _PEDIDO)
    assert novo["status"] == "aprovado" and novo["veredito_original"] == "aprovado_com_ressalvas"
    assert novo["achados"] == [] and novo["decisoes_do_po_registradas"][0]["codigo"] == "6.2"
    assert "decisão do PO já registrada" in nota
    # sem a decisão do PO, ou com outro número, a ressalva fica
    assert recontar({"status": "aprovado_com_ressalvas", "achados": [_REPETE]}, {})[1] == ""
    outro = {**_REPETE, "resumo": _REPETE["resumo"].replace("29 min", "35 min")}
    assert status_recontado(_relatorio("aprovado_com_ressalvas", [outro]), _PEDIDO)["status"] == "amarelo"
    # ressalva que não diz que o PO decidiu também fica
    sem_po = {**_REPETE, "resumo": "Tempo em tela de 29 min acima do teto de 25 min."}
    assert status_recontado(_relatorio("aprovado_com_ressalvas", [sem_po]), _PEDIDO)["status"] == "amarelo"


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


def test_gate_de_envelope_reconta_e_grava_a_nota():
    from agents.checkers import EnvelopeGateAgent

    gate = EnvelopeGateAgent(name="G", rotulo="Gate final", report_key="r", status_key="s",
                             block_pipeline_on_fail=False, recontar_decisoes_do_po=True, contrato_no_de_acordo=True)
    one_pager = "- `[PROPOSTA — validar com PO: botão de zoom na tabela]`\n"
    final = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[gate]), {
        **_PEDIDO, "one_pager": one_pager, "r": _relatorio("aprovado_com_ressalvas", [_REPETE, _PROPOSTAS])}))
    assert final["s"] == "aprovado" and final["s_envelope"]["veredito_original"] == "aprovado_com_ressalvas"
    assert "Recontado em código" in final["r"]
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
