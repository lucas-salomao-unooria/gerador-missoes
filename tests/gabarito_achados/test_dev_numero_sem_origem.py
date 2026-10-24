"""Gabarito do `numero-sem-origem` (A101b handoff, A116b PRD — `tools/montagem.py`), das 7 execuções de dev que o PO
viu (diagnóstico C1, 24/10/2026): 55 números acusados na main c9af72b, 27 verdadeiros, 9 ambíguos e 19 falsos
positivos.

- FP: medida de string sem teto que a reja, estatística externa, «(ex.: …)», nota de Lighthouse, barra de progresso,
  limites do recorte da aula, teto da faixa, payload `segundos_sem_acao` da spec e o teto que o PO ratificou ao
  refazer dev. NÃO podem disparar.
- V: os 27, mais 2 que a deduplicação da main escondia atrás de um FP. TÊM de disparar.
- Régua: os 9 ambíguos são detalhe de design (duração de animação, persona, «2 opções», microaproximação, debate). Se
  número de detalhe de design precisa de origem de produto é decisão de régua (D7), não correção de falso positivo:
  continuam disparando até o PO decidir.

O achado guarda só 180 caracteres da linha: o caso compara pelo começo da linha do documento que contém o trecho.
"""
from __future__ import annotations

import pytest

from gabarito_estados import corpo, estado, inicios_das_linhas_com, rotulo
from tools import montagem


def _sem_origem(execucao: str, documento: str):
    st = estado(execucao)
    contrato = montagem.texto_do_contrato(montagem.contrato(st))
    return [(i["numero"], i["linha"]) for i in montagem.numeros_sem_origem(corpo(execucao, documento), contrato)]


def _dispara(execucao: str, documento: str, numero: str, trecho: str) -> bool:
    inicios = set(inicios_das_linhas_com(execucao, documento, trecho))
    return any(n == numero and l in inicios for n, l in _sem_origem(execucao, documento))


def _id(caso) -> str:
    return f"{rotulo(caso[0])}/{caso[1]}/{caso[2]}"


FP = [
    # (execução, documento, número, trecho da linha, por que não é regra sem origem)
    ("R03", "handoff", "10 palavras", "Ratificação do teto textual",
     "o PO ratificou no refazer de dev de 25/09/2026: «pode ser ate 10 palavras»"),
    ("R03", "prd", "10 palavras", "manchetes de até 10 palavras", "idem"),
    ("R03", "handoff", "21 palavras", "fala de Bento com 21 palavras",
     "medida de string; o «teto» da linha rege outros números"),
    ("R03", "handoff", "60 caracteres", "tema central (máx. 60 caracteres)", "recorte da aula do E0-PROF (plataforma)"),
    ("R03", "handoff", "600 caracteres", "tópicos prioritários", "recorte da aula do E0-PROF (plataforma)"),
    ("R03", "handoff", "90 s", "Ao atingir 90s sem ação", "a spec tem o EVT-U04 com `{\"segundos_sem_acao\": 90}`"),
    ("R03", "prd", "90 s", "Ao atingir 90s sem ação", "idem"),
    ("R03", "prd", "98%", "Lighthouse Accessibility Score", "nota de acessibilidade medida por ferramenta: casca"),
    ("R04", "handoff", "73%", "(ex.: 73%)", "exemplo"),
    ("R04", "handoff", "17 palavras", "frases com até 17 palavras (teto da faixa",
     "medida: o teto vem depois, entre parênteses"),
    ("R04", "handoff", "46 palavras", "legendas com 39 a 46 palavras", "medida de string"),
    ("R04", "handoff", "20 palavras", "teto da faixa: 20 palavras", "teto da faixa 6–9 (teto-palavras-por-faixa.md)"),
    ("R04", "handoff", "20 s", "barra de progresso", "espera da geração por IA: casca"),
    ("R04", "prd", "15%", "CETIC.br", "estatística externa citada"),
    ("R04", "prd", "20 palavras", "comandos ≤ 20 palavras", "teto da faixa 6–9"),
    ("R06", "handoff", "2 palavras", "caixa alta de 1 a 2 palavras", "descrição da copy, não teto"),
    ("R08", "handoff", "20 palavras", "≤ 20 palavras por oração", "teto da faixa 6–9 (9º ano)"),
    ("R12", "handoff", "49 palavras", "`e6.pergunta.em13co26` (49 palavras)", "medida de string"),
    ("R12", "prd", "49 palavras", "`e6.pergunta.em13co26` (49 palavras)", "medida de string"),
]

V = [
    ("R04", "prd", "30 s", "KPI-05", "limiar de KPI inventado, sem [PROPOSTA]"),
    ("R04", "prd", "15 min", "KPI-05", "limiar de KPI inventado"),
    ("R04", "prd", "120 s", "KPI-05", "limiar de KPI inventado"),
    ("R04", "prd", "30%", "KPI-08", "limiar de KPI inventado"),
    ("R04", "prd", "25%", "KPI-16", "alvo de KPI inventado"),
    ("R06", "prd", "75%", "KPI-01", "alvo de KPI inventado (a T7 diz 50%)"),
    ("R06", "prd", "10%", "KPI-02", "limiar inventado"),
    ("R06", "prd", "30%", "KPI-08", "limiar inventado"),
    ("R06", "prd", "20%", "KPI-16", "alvo trocado (o 9f diz 25%)"),
    ("R08", "handoff", "35%", "Hipótese de Descoberta Crítica", "meta de hipótese inventada"),
    ("R08", "handoff", "70%", "Hipótese de Transferência", "meta de hipótese inventada"),
    ("R08", "handoff", "60%", "janela de 7 minutos", "meta de hipótese inventada"),
    ("R08", "handoff", "30%", "Campo Opcional de Anotações", "meta de hipótese inventada"),
    ("R08", "handoff", "10%", "Menos de 10% de uso", "meta de hipótese inventada"),
    ("R08", "prd", "70%", "Métrica-alvo", "meta inventada (o §17 tem 65%)"),
    ("R08", "prd", "10%", "KPI-02", "limiar inventado"),
    ("R08", "prd", "85%", "KPI-03", "limiar inventado"),
    ("R08", "prd", "34 min", "KPI-05", "limiar inventado"),
    ("R08", "prd", "30%", "KPI-08", "limiar inventado"),
    ("R08", "prd", "60%", "KPI-10", "limiar inventado"),
    ("R08", "prd", "25%", "KPI-17", "limiar inventado"),
    ("R10", "prd", "5%", "Taxa de abandono na Etapa 2", "guardrail inventado"),
    ("R10", "handoff", "40 palavras", "bastidor ultrapassar 40 palavras", "teto que nenhum documento da sessão tem"),
    ("R12", "handoff", "85%", "concluem o percurso", "meta inventada"),
    ("R12", "handoff", "70%", "identificam ao menos uma ferramenta", "meta inventada"),
    ("R12", "prd", "5%", "Abandono por frustração", "guardrail inventado"),
    ("R13", "prd", "80%", "KPI-08", "limiar inventado"),
    # a main deduplicava por número, e o FP da linha anterior escondia estes dois
    ("R04", "handoff", "17 palavras", "Crachá central exibe nome do aluno",
     "a maior frase medida na copy virou teto «em até 17 palavras»"),
    ("R04", "prd", "15%", "KPI-06", "limiar de KPI inventado"),
]

REGUA = [  # ambíguos: detalhe de design sem origem de produto — continuam disparando (decisão de régua, D7)
    ("R03", "handoff", "2 opções", "marcar uma das duas opções", "mecânica binária; o contrato não diz «duas opções»"),
    ("R06", "handoff", "10%", "microaproximação nos hotspots", "protocolo de negociação de escopo"),
    ("R06", "handoff", "20%", "microaproximação nos hotspots", "idem"),
    ("R06", "prd", "5 min", "**Perfil:**", "persona"),
    ("R06", "prd", "3 s", "a foto afasta mostrando a comemoração", "«após 3s dispara `concluir()`», da jornada"),
    ("R08", "handoff", "43 palavras", "100% revisada em contexto", "a medida da copy virou teto («≤ 43 palavras»)"),
    ("R08", "handoff", "15 min", "Debate socrático da Etapa 4", "duração do debate"),
    ("R12", "handoff", "1.8 s", "Duração da animação calibrada", "duração de animação, do protótipo"),
    ("R12", "prd", "1.8 s", "E4_AVANCO_TEMPORAL_ANIMADO", "idem"),
]


@pytest.mark.parametrize("caso", FP, ids=_id)
def test_fp_nao_dispara(caso):
    execucao, documento, numero, trecho, motivo = caso
    assert not _dispara(execucao, documento, numero, trecho), (
        f"{rotulo(execucao)} {documento}: {numero} é FP ({motivo})")


@pytest.mark.parametrize("caso", V, ids=_id)
def test_v_dispara(caso):
    execucao, documento, numero, trecho, motivo = caso
    assert _dispara(execucao, documento, numero, trecho), f"{rotulo(execucao)} {documento}: {numero} é V ({motivo})"


@pytest.mark.parametrize("caso", REGUA, ids=_id)
def test_regua_detalhe_de_design_continua_disparando(caso):
    execucao, documento, numero, trecho, motivo = caso
    assert _dispara(execucao, documento, numero, trecho), f"{rotulo(execucao)} {documento}: {numero} ({motivo})"


def test_sete_execucoes_tem_os_38_numeros_e_so_eles():
    """Os 38 números que ficam nas 7 execuções vistas pelo PO são os 29 V e os 9 da régua: nenhum outro."""
    esperados = {(e, d, n) for e, d, n, _, _ in V + REGUA}
    achados = {(e, d, n) for e in ("R03", "R04", "R06", "R08", "R10", "R12", "R13") for d in ("handoff", "prd")
               for n, _ in _sem_origem(e, d)}
    assert achados == esperados, (sorted(achados - esperados), sorted(esperados - achados))


def test_pedido_do_po_ao_refazer_dev_vira_origem_so_no_que_ele_afirma():
    """Os dois pedidos de refazer dev da exp04ef1b (25/09/2026): «pode ser ate 10 palavras» e «o teto … está ratificado
    …: resumo de notícia com 25 a 35 palavras; manchete com até 10 palavras». O pedido de produto (o material do
    bimestre) não entra."""
    pedidos = montagem.contrato(estado("R03"))["pedidos_do_po"]
    assert {l.split(" — ")[0] for l in pedidos.splitlines()} == {"10 palavras", "35 palavras"}, pedidos


def test_pedido_do_po_que_cita_o_texto_atual_nao_vira_origem():
    """exp02ef1b (23/10/2026): o pedido de design cita entre aspas o texto atual («pelo menos 10% da foto») e cola
    relatos de gate; exp02em1b (22/10/2026): o pedido de dev cita as rubricas «… por 4 segundos …» para trocá-las.
    Nenhum desses números é decisão do PO."""
    assert montagem.contrato(estado("R13"))["pedidos_do_po"] == ""
    assert montagem.contrato(estado("R12"))["pedidos_do_po"] == ""
