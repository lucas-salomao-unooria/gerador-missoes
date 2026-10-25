"""Gabarito dos juízes e lints de produto (correção C3 do backlog de 24/10/2026).

Cada caso parte de um achado do levantamento de produto (`deficiencias/produto/achados.csv`, id `P…`), com a execução
real e o trecho que o prova: FP não pode disparar, V tem de disparar. Onde o levantamento não tem V para a regra, o V é
um mutante sobre o mesmo documento real (o número trocado, o item fora da ordem do PO, a citação reescrita), para
provar que a correção não cegou o gate. Os resíduos — FP que o código continua sem poder provar — estão marcados como
tal, com o que sobra.
"""
from __future__ import annotations

import re

import pytest

from gabarito_produto import estado, exige, rotulo
from tools import banca as bnc
from tools import decisoes, juizes_produto, profundidade
from tools import fidelidade as fid
from tools import secoes
from tools.contrato_produto import validar_one_pager


# ------------------------------------------------------------------ 1. cobertura conceitual: trecho-inexistente
def _trechos_inexistentes(st, material):
    r = profundidade.validar_cobertura(st["nucleo_narrativo"], st["mapa_conceitual"], material)
    return [a for a in r["achados"] if a["codigo"] == "trecho-inexistente"]


def test_fp_p002_p011_material_colado_no_parecer_do_po_e_material():
    """8ce9c32d (exp04ef1b): o PO colou o material do bimestre no parecer de refazer de 25/09 11:21:25; os cinco trechos
    do mapa estão lá, e só lá (P002–P006 na cobertura, P007–P011 na profundidade, que funde a cobertura)."""
    st = estado("8ce9c32d:final")
    parecer = next(p["comentario"] for p in st["pareceres_humanos"] if p["quando"] == "25/09/2026 11:21:25")
    exige(parecer, "Segue o material trabalhado no bimestre", "o parecer de 25/09")
    exige(parecer, "Bento publica sem verificar e precisa lidar com as consequências.", "o parecer de 25/09")
    assert len(_trechos_inexistentes(st, st["material_anexado"])) == 5  # o que a cobertura via antes
    assert _trechos_inexistentes(st, profundidade.material_da_sessao(st)) == []


def test_fp_p161_p166_aspas_trocadas_pelo_mapa():
    """60cfa7f4 (exp02em1b): o material diz «mas o "engajamento".» e o mapa cita «mas o 'engajamento'.» — e tira as aspas
    de «"metadados", que são…». C1, C2 e C4 (P161–P163 e P164–P166)."""
    st = estado("acervo:exp02em1b-60cfa7f4")
    exige(st["material_anexado"], 'mas o "engajamento". O algoritmo prioriza', "o material")
    exige(st["mapa_conceitual"], "mas o 'engajamento'. O algoritmo prioriza", "o mapa")
    assert _trechos_inexistentes(st, st["material_anexado"]) == []


def test_v_mutante_citacao_reescrita_continua_inexistente():
    """O mapa que reescreve a citação (troca «engajamento» por «entretenimento») ainda é acusado."""
    st = estado("acervo:exp02em1b-60cfa7f4")
    st["mapa_conceitual"] = st["mapa_conceitual"].replace("mas o 'engajamento'", "mas o 'entretenimento'")
    achados = _trechos_inexistentes(st, profundidade.material_da_sessao(st))
    assert [a["resumo"][:4] for a in achados] == ["`C1`"]


def test_v_cabecalho_da_esteira_nao_e_material():
    """O cabeçalho que a esteira põe no pedido de refazer não é material do PO: o mapa que o cita é acusado."""
    st = estado("acervo:exp02em1b-60cfa7f4")
    pedido = estado("727a3c2d:final")["pedido_correcao"]
    exige(pedido, "Os documentos das etapas anteriores foram preservados e são seus insumos", "o pedido de refazer")
    st["pedido_correcao"] = pedido
    st["mapa_conceitual"] = st["mapa_conceitual"].replace(
        "\"não é a qualidade da informação, mas o 'engajamento'. O algoritmo prioriza o que prende a atenção, "
        "calculando a probabilidade de o aluno continuar navegando.\"",
        "\"Os documentos das etapas anteriores foram preservados e são seus insumos.\"")
    assert [a["resumo"][:4] for a in _trechos_inexistentes(st, profundidade.material_da_sessao(st))] == ["`C1`"]


# ------------------------------------------------------------------ 2. decisão atribuída ao PO
def _atribuidas(st, chave, documento="O documento"):
    achados = decisoes.achados(st[chave], documento, decisoes.ha_registro_do_po(st))
    return [a for a in achados if a["codigo"] == "decisao-atribuida-ao-po"]


@pytest.mark.parametrize("execucao, chave, trecho", [
    # P049: «homologados pelo PO» — o Pedido 13 crava 60/25/35 palavras e aceita os 29 min
    ("727a3c2d:final", "one_pager", "60 palavras por legenda de projeto, 25 por cartão argumentativo"),
    # P063: as duas linhas do resumido citam o Pedido 13 e repetem o que ele decide
    ("727a3c2d:final", "one_pager_resumido", "O PO ratificou e homologou no Pedido 13 esse tempo de tela de 29 min"),
    # P156: o one-pager que o PO anexou traz as mesmas linhas
    ("acervo:exp06ef1b-53e011b6", "one_pager", "Tetos de palavras cravados (homologados pelo PO)"),
    # P159: o PO mandou trocar o marcador das PQ-01 a PQ-05 por [HOMOLOGADO pelo PO] (parecer de 08/10 15:11, item 8)
    ("acervo:exp06ef1b-53e011b6", "spec_missao", "[HOMOLOGADO pelo PO]"),
])
def test_fp_atribuicao_que_o_registro_do_po_confirma(execucao, chave, trecho):
    st = estado(execucao)
    exige(st[chave], trecho, f"o {chave} de {rotulo(execucao)}")
    assert _atribuidas(st, chave) == []


def test_fp_p159_a_ordem_do_po_esta_no_parecer():
    st = estado("acervo:exp06ef1b-53e011b6")
    ordem = next(p["texto"] for p in st["pedidos_do_po"] if "HOMOLOGADO pelo PO" in p["texto"])
    exige(ordem, "Trocar o marcador [PROPOSTA — validar com PO] de cada uma por [HOMOLOGADO pelo PO]", "o pedido")
    exige(ordem, "PQ-01 a PQ-05", "o pedido")


def test_residuo_p056_so_a_generalizacao_fica_para_conferir():
    """P056 (727a3c2d, spec): das três atribuições, duas o Pedido 13 confirma (os 29 min); a terceira generaliza — «Todas as
    pendências e parâmetros foram homologados e ratificados pelo PO no Pedido 13» — e o código não prova «todas». O achado
    continua ⚠️ só com ela."""
    st = estado("727a3c2d:final")
    achado = _atribuidas(st, "spec_missao", "A spec")
    assert len(achado) == 1 and achado[0]["severidade"] == "atencao"
    assert "Todas as pendências e parâmetros foram homologados" in achado[0]["resumo"]
    assert "Tempo em tela de 29 min" not in achado[0]["resumo"] and "2 outra(s)" in achado[0]["resumo"]


def test_v_mutante_numero_trocado_na_atribuicao():
    """O one-pager que diz «homologados pelo PO» com 90 palavras, quando o PO cravou 60, é acusado — o trecho comum de
    seis palavras não basta, o número tem de ser o dele."""
    st = estado("727a3c2d:final")
    st["one_pager"] = st["one_pager"].replace("cravados (homologados pelo PO):** 60 palavras",
                                              "cravados (homologados pelo PO):** 90 palavras")
    achado = _atribuidas(st, "one_pager")
    assert len(achado) == 1 and "90 palavras" in achado[0]["resumo"]


def test_v_mutante_marca_homologado_fora_da_ordem_do_po():
    """[HOMOLOGADO pelo PO] numa PQ que a ordem do PO (PQ-01 a PQ-05) não cobre é acusado."""
    st = estado("acervo:exp06ef1b-53e011b6")
    linha = next(l for l in st["spec_missao"].splitlines() if l.startswith("| PQ-05 "))
    st["spec_missao"] += "\n" + linha.replace("| PQ-05 ", "| PQ-06 ") + "\n"
    achado = _atribuidas(st, "spec_missao", "A spec")
    assert len(achado) == 1 and "PQ-06" in achado[0]["resumo"] and "PQ-05" not in achado[0]["resumo"]


def test_v_sem_registro_do_po_continua_bloqueando():
    """274a2e75 (exp03ef1b): «PO (via One-pager v2.2)» sem nenhum parecer, pedido ou correção do PO na sessão é ⛔."""
    st = estado("274a2e75:final")
    assert not decisoes.ha_registro_do_po(st)
    exige(st["spec_missao"], "PO (via One-pager v2.2)", "a spec")
    assert [a["severidade"] for a in _atribuidas(st, "spec_missao")] == ["bloqueio"]


def test_decisao_gravada_no_de_acordo_confirma_e_valor_diferente_nao():
    """A decisão do de acordo de produto (`decisoes_do_po`, PR 3) confirma a atribuição do mesmo assunto e valor."""
    from tools import fechar_contrato as fc

    st = estado("acervo:exp02em1b-60cfa7f4")
    item = next(i for i in fc.itens_em_aberto(st) if decisoes.numeros_com_unidade(i.sugestao))
    decisao = fc.decidir([item], {item.id: {"resposta": "aceitar"}}, "23/10/2026 10:00:00", "produto")
    st["decisoes_do_po"] = decisao.decisoes
    valor = decisoes.numeros_com_unidade(item.sugestao)[0]
    linha = f"- **{item.assunto[:80]}:** {valor} (homologado pelo PO)."
    registro = decisoes.ha_registro_do_po(st)
    assert registro.decisao_gravada(linha)
    numero, unidade = valor.split(" ", 1)
    assert not registro.decisao_gravada(linha.replace(valor, f"{int(float(numero)) + 7} {unidade}"))


# ------------------------------------------------------------------ 3 e 4. juízes de produto recontados
def _recontado(execucao, relatorio, contrato=False):
    st = estado(execucao)
    return juizes_produto.status_recontado(st[relatorio], st, contrato)["status"], st


@pytest.mark.parametrize("execucao, relatorio, contrato, trecho", [
    # P054 e P055: gate final repete os 29 min e os 60/25/35 «homologados no Pedido 13»
    ("727a3c2d:final", "gate_final_report", True, "homologada pelo PO no Pedido 13"),
    # P053: experiência 6.2
    ("727a3c2d:final", "experiencia_aluno_report", False, "mantido sob ressalva operacional homologada pelo PO"),
    # P052: avaliação 4.1 (decisao_humana)
    ("727a3c2d:final", "avaliacao_pedagogica_report", False, "homologada formalmente pelo PO no Pedido 13"),
    # P158 e P157: 53e011b6 — «Todos os itens anteriormente homologados (tempo em tela de 29 min…) permanecem»
    ("acervo:exp06ef1b-53e011b6", "gate_final_report", True, "registrado como ressalva operacional aceita e homologada"),
    ("acervo:exp06ef1b-53e011b6", "experiencia_aluno_report", False, "mantido como ressalva operacional homologada"),
])
def test_fp_ressalva_que_so_repete_decisao_do_po(execucao, relatorio, contrato, trecho):
    st = estado(execucao)
    exige(st[relatorio], trecho, f"o {relatorio} de {rotulo(execucao)}")
    status, _ = _recontado(execucao, relatorio, contrato)
    assert status == "aprovado"
    _, envelope = juizes_produto.recontar_relatorio(st[relatorio], st, contrato)
    assert envelope["decisoes_do_po_registradas"]
    assert envelope.get("veredito_original") in ("aprovado_com_ressalvas", None)


@pytest.mark.parametrize("execucao, relatorio, trecho", [
    # P018: 8ce9c32d, experiência 6.2 sem homologação nenhuma
    ("8ce9c32d:final", "experiencia_aluno_report", "excede em 4 min o teto recomendado de 25 min"),
    # P021: o mesmo no gate final
    ("8ce9c32d:final", "gate_final_report", "excede em 4 min a recomendação para aulas de 50 min"),
    # P036 e P041: 727a3c2d em 02/10, antes do Pedido 13 — o mesmo tempo, sem decisão do PO ainda
    ("727a3c2d:02-10", "experiencia_aluno_report", "recomendável recalibrar para 24 min"),
    ("727a3c2d:02-10", "gate_final_report", "exigem calibração fina no build para assegurar 25 min em tela"),
])
def test_v_ressalva_sem_decisao_do_po_continua(execucao, relatorio, trecho):
    st = estado(execucao)
    exige(st[relatorio], trecho, f"o {relatorio} de {rotulo(execucao)}")
    status, _ = _recontado(execucao, relatorio, relatorio == "gate_final_report")
    assert status == "amarelo"


def test_v_mutante_ressalva_que_cita_o_po_com_outro_numero():
    """A experiência que diz «homologada pelo PO» sobre 35 min, quando o PO aceitou 29, continua ressalva."""
    st = estado("727a3c2d:final")
    st["experiencia_aluno_report"] = st["experiencia_aluno_report"].replace("(29 min)", "(35 min)")
    exige(st["experiencia_aluno_report"], "(35 min) excede o teto", "o relatório mutado")
    assert juizes_produto.status_recontado(st["experiencia_aluno_report"], st)["status"] == "amarelo"


def test_residuo_p096_travado_pelo_briefing_sem_o_numero_no_registro():
    """P096 (c19d3cb0, exp09ef1b): «31 min … travado pelo briefing do PO». O PO pediu «tempos sugeridos: tudo idêntico»,
    mas nenhum texto dele traz os 31 min: o código não prova a decisão, e a ressalva fica."""
    st = estado("acervo:exp09ef1b")
    exige(st["experiencia_aluno_report"], "travado pelo briefing do PO", "a experiência")
    assert juizes_produto.status_recontado(st["experiencia_aluno_report"], st)["status"] == "amarelo"


@pytest.mark.parametrize("execucao, trecho", [
    ("acervo:exp02em1b-60cfa7f4", "Propostas estruturais e parâmetros de interface registrados no one-pager"),  # P168
    ("acervo:exp03em1b-b2e7b4a3", "Propostas abertas na Seção 18 aguardando validação do PO"),  # P201
    ("acervo:exp01em1b-e3980485", "Propostas ergonômicas de P0b"),  # P239
])
def test_gate_final_proposta_aberta_vai_ao_de_acordo_e_nao_rebaixa(execucao, trecho):
    """O 🔵 que só repete as propostas e parâmetros abertos sai da contagem — e os itens estão na lista do de acordo."""
    from tools import fechar_contrato as fc

    st = estado(execucao)
    exige(st["gate_final_report"], trecho, "o gate final")
    assert [i for i in fc.itens_em_aberto(st) if i.tipo in (fc.PARAMETRO, fc.PROPOSTA)], \
        "a pendência tem de estar na lista do de acordo"
    texto, envelope = juizes_produto.recontar_relatorio(st["gate_final_report"], st, True)
    assert juizes_produto.status_recontado(st["gate_final_report"], st, True)["status"] == "aprovado"
    assert [a["resumo"][:len(trecho)] for a in envelope["na_lista_do_de_acordo"]] == [trecho]
    assert "na lista do de acordo de produto" in texto and envelope["precisa_humano"] is False


def test_v_mutante_sem_itens_no_de_acordo_o_azul_fica():
    """Sem marcador aberto no one-pager nem na spec, a lista do de acordo está vazia: o 🔵 do gate final fica."""
    st = estado("acervo:exp02em1b-60cfa7f4")
    for chave in ("one_pager", "spec_missao", "spec_missao_gate0"):
        st[chave] = re.sub(r"\[(?:PAR[ÂA]METRO|PROPOSTA|ABERTO)[^\]\n]*\]", "", str(st.get(chave) or ""))
    assert juizes_produto.status_recontado(st["gate_final_report"], st, True)["status"] == "amarelo"


def test_v_p147_p148_conflito_com_o_briefing_continua_decisao_humana():
    """274a2e75: unoochat no lugar da unoogaleria que o briefing travou, e ícones sem texto × áudio — decisão do PO de
    verdade, que nenhum marcador do contrato registra."""
    st = estado("274a2e75:final")
    exige(st["gate_final_report"], "homologação formal do ambiente unoochat", "o gate final")
    _, envelope = juizes_produto.recontar_relatorio(st["gate_final_report"], st, True)
    humanos = [a for a in envelope["achados"] if a.get("severidade") == "decisao_humana"]
    assert len(humanos) == 2
    assert juizes_produto.status_recontado(st["gate_final_report"], st, True)["status"] == "amarelo"


def test_gate_final_com_ressalva_real_fica_amarelo_mesmo_movendo_o_contrato():
    """76d9af6e: P269 e P270 vão ao de acordo; a ressalva E2-A1 (P268) fica, e o gate continua 🟡."""
    st = estado("acervo:exp01em1b-76d9af6e")
    _, envelope = juizes_produto.recontar_relatorio(st["gate_final_report"], st, True)
    assert len(envelope["na_lista_do_de_acordo"]) == 2
    assert [a["codigo"] for a in envelope["achados"]] == ["F7"]
    assert juizes_produto.status_recontado(st["gate_final_report"], st, True)["status"] == "amarelo"


# ------------------------------------------------------------------ 5. critério 2.1: contagem de seções do DS
def _secao0_numa_linha(one_pager):
    linhas = one_pager.splitlines()
    ini = next(i for i, l in enumerate(linhas) if l.startswith("## 0."))
    fim = next(i for i in range(ini + 1, len(linhas)) if linhas[i].startswith("## "))
    uma = " · ".join(l.lstrip("- ").strip() for l in linhas[ini + 1:fim] if l.strip())
    return "\n".join(linhas[:ini + 1] + [uma] + linhas[fim:])


def _codigos_de_secao(one_pager, briefing=""):
    return [a["codigo"] for a in validar_one_pager(one_pager, briefing=briefing)["achados"]
            if a["codigo"].startswith(("secao-extra", "secoes-"))]


def test_fp_p285_secao_0_numa_linha_nao_vira_26_secoes():
    """4fd72a9a (exp02ef1b), rodada 1: a seção 0 numa linha só («… **Seções extras do DS:** nenhuma · **Modalidade:**
    duplas…»). O relatório da rodada 2 fala em «falso-positivo léxico de 26 seções espúrias». Reconstruída a partir do
    one-pager final, que pôs cada campo numa linha."""
    st = estado("acervo:exp02ef1b-4fd72a9a")
    exige(st["one_pager"], "falso-positivo léxico de 26 seções espúrias", "o changelog do one-pager")
    rodada1 = _secao0_numa_linha(st["one_pager"])
    exige(rodada1, "**Seções extras do DS:** nenhuma · **Modalidade:**", "a seção 0 reconstruída")
    assert secoes.extras(rodada1) == []
    assert _codigos_de_secao(rodada1, st.get("briefing", "")) == []


def test_fp_p286_changelog_que_cita_o_campo_nao_e_a_declaracao():
    """e3980485 (exp01em1b), rodadas 1–2: o changelog reproduzia «a chave literal de busca de metadados de seções extras»
    antes da seção 0 (o one-pager final diz que a sanitizou). Reconstruído com a chave no item 1 do «O que mudou»."""
    st = estado("acervo:exp01em1b-e3980485")
    exige(st["one_pager"], "sem reproduzir a chave literal de busca de metadados de seções extras", "o changelog")
    antes = st["one_pager"].replace(
        "e especificação de ausência de ambientes adicionais, eliminando",
        "e `Seções extras do DS: nenhuma` passa a ter linha própria, eliminando")
    assert antes != st["one_pager"]
    assert secoes.extras(antes) == []
    assert _codigos_de_secao(antes, st.get("briefing", "")) == []


def test_v_mutante_extra_de_verdade_no_2o_ano_continua_acima_do_teto():
    st = estado("acervo:exp02ef1b-4fd72a9a")
    com_extra = _secao0_numa_linha(st["one_pager"]).replace(
        "**Seções extras do DS:** nenhuma ·", "**Seções extras do DS:** `unoochat` ·")
    assert secoes.extras(com_extra) == ["unoochat"]
    assert "secoes-acima-do-teto" in _codigos_de_secao(com_extra)


def test_v_mutante_extra_fora_da_lista_continua_desconhecida():
    st = estado("acervo:exp02ef1b-4fd72a9a")
    com_extra = st["one_pager"].replace("- **Seções extras do DS:** nenhuma", "- **Seções extras do DS:** whatsapp2")
    assert secoes.extras(com_extra) == ["whatsapp2"]
    assert "secao-extra-desconhecida" in _codigos_de_secao(com_extra)


# ------------------------------------------------------------------ 6. o cabeçalho da esteira não é pedido do PO
def _checklist_como_a_esteira(st):
    """O checklist da fidelidade de produto como o `DocumentoObrigatorioAgent` o monta: os pedidos de refazer de produto e
    o «Pedido, na íntegra» do pedido corrente."""
    from pipeline.reexecucao import texto_do_pedido

    pedidos = [(p["origem"], p["texto"]) for p in st["pedidos_do_po"] if p.get("etapa") in ("produto", "")]
    pedidos.append(("pedido de correção desta execução", texto_do_pedido(st["pedido_correcao"])))
    return fid.montar_checklist(pedidos, st.get("briefing", ""))


def test_fp_p047_p060_preambulo_nao_entra_no_checklist():
    """727a3c2d (exp06ef1b), 08/10 11:08: o «pedido do PO» citado no 🔴 era o cabeçalho da esteira. A main lê só o
    «Pedido, na íntegra» desde 84354c2 (08/10 12:27); o pedido colado com o cabeçalho também não o traz mais."""
    st = estado("727a3c2d:final")
    exige(str(st["fidelidade_nucleo_status_envelope"]), "Esta execução refaz a etapa `produto`", "o 🔴 gravado")
    assert not [i for i in _checklist_como_a_esteira(st) if "Esta execução refaz" in i["texto"]]
    colado = fid.montar_checklist([("pedido colado", "Segue de novo o pedido:\n\n" + st["pedido_correcao"])], "")
    assert not [i for i in colado if "Esta execução refaz" in i["texto"] or "Aplique o pedido" in i["texto"]]
    # o que o PO escreveu continua item
    assert any("EF06CO07" in i["texto"] for i in colado)


def test_v_p061_p062_a_ordem_de_tirar_ef06co07_continua_no_checklist():
    st = estado("727a3c2d:final")
    itens = [i["texto"] for i in _checklist_como_a_esteira(st)]
    assert any("Remover a habilidade EF06CO07 de todos os documentos de produto" in t for t in itens)
    assert any("remover menções residuais de EF06CO07" in t for t in itens)


# ------------------------------------------------------------------ 7. banca de produto alinhada aos modelos
def _banca(st, posicao="produto"):
    from agents.callbacks import extrair_envelope
    from tools.citacoes import texto_dos_documentos

    envs = {f"banca_{posicao}_{d}": extrair_envelope(str(st.get(f"banca_produto_{d}") or ""))
            for d in ("narrativa", "pedagogia")}
    return bnc.consolidar(envs, texto_dos_documentos(st, bnc.DOCUMENTOS_DA_BANCA))


def _ids(achados):
    return sorted({str(a.get("id") or a.get("codigo")) for a in achados})


@pytest.mark.parametrize("execucao, fora, status", [
    ("727a3c2d:final", ["PED-12", "PED-15"], "aprovado"),  # P058, P059
    ("60cfa7f4:22-10", ["PED-03", "PED-12", "PED-15"], "aprovado"),  # P176, P177, P178
    ("acervo:exp03em1b-b2e7b4a3", ["PED-03"], "amarelo"),  # P208; o PED-01 (P207) fica
])
def test_banca_de_produto_nao_cobra_o_que_os_modelos_nao_pedem(execucao, fora, status):
    st = estado(execucao)
    r = _banca(st)
    assert _ids(r["outra_posicao"]) == fora and not set(fora) & set(_ids(r["achados"]))
    assert r["status"] == status
    assert "Avaliados em outra posição" in bnc.relatorio(r, "missao")


def test_v_p276_ped06_bloqueante_continua_bloqueando():
    """76d9af6e: o PED-06 (zero × none) é bloqueante e da spec; PED-03/12/15 saem, o 🔴 fica."""
    r = _banca(estado("acervo:exp01em1b-76d9af6e"))
    assert r["status"] == "bloqueado" and "PED-06" in _ids(r["achados"])
    assert _ids(r["outra_posicao"]) == ["PED-03", "PED-12", "PED-15"]


def test_v_os_outros_achados_da_banca_continuam():
    """4fd72a9a: PED-12 e PED-15 saem; PROD-16, PROD-14, PROD-10, PROD-05 e PED-13 ficam 🟡."""
    r = _banca(estado("acervo:exp02ef1b-4fd72a9a"))
    assert r["status"] == "amarelo"
    assert {"PROD-16", "PROD-14", "PED-13"} <= set(_ids(r["achados"]))


def test_v_p126_rotulado_ped12_mas_sobre_o_ddl_continua():
    """e89e91b3 (exp01em1b): o juiz rotulou de PED-12 um achado sobre o DDL (colunas `score_coXX` fora do módulo de
    evidências). Não é a leitura do gestor: continua contando no fim de produto."""
    st = estado("acervo:exp01em1b-e89e91b3")
    exige(st["banca_produto_pedagogia"], "DDL da missão define colunas próprias score_coXX", "a banca")
    r = _banca(st)
    assert "PED-12" in _ids(r["achados"]) and r["outra_posicao"] == [] and r["status"] == "amarelo"


def test_v_na_entrada_do_dev_ped_12_15_03_continuam_cobrados():
    """Os mesmos envelopes na posição da entrada do dev: a rubrica não afrouxou fora do fim de produto."""
    r = _banca(estado("727a3c2d:final"), posicao="entrada")
    assert r["status"] == "amarelo" and {"PED-12", "PED-15"} <= set(_ids(r["achados"])) and not r["outra_posicao"]
