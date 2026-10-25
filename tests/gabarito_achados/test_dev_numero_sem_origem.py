"""Gabarito do `numero-sem-origem` (A101b handoff, A116b PRD — `tools/montagem.py`), das 7 execuções de dev que o PO
viu (diagnóstico C1, 24/10/2026): 55 números acusados na main c9af72b, 27 verdadeiros, 9 ambíguos e 19 falsos
positivos.

- FP: medida de string sem teto que a reja, estatística externa, «(ex.: …)», nota de Lighthouse, barra de progresso,
  limites do recorte da aula, teto da faixa e payload `segundos_sem_acao` da spec. NÃO podem disparar.
- V: os 27, mais 2 que a deduplicação da main escondia atrás de um FP e o «$\\ge 80\\%$» em LaTeX do handoff da
  exp02ef1b, que `numeros()` não lia. TÊM de disparar.
- Régua: os 9 ambíguos são detalhe de design (duração de animação, persona, «2 opções», microaproximação, debate). Se
  número de detalhe de design precisa de origem de produto é decisão de régua (D7), não correção de falso positivo:
  continuam disparando até o PO decidir.
- Documentado: o teto de 10 palavras que o PO ratificou em prosa no refazer de dev da exp04ef1b (25/09/2026). Desde a
  terceira revisão do PR #77, o pedido em prosa livre não é origem de número: a origem é o contrato, as decisões do de
  acordo e as trocas da correção pontual. A sessão é anterior ao PR 5 (#72), que leva o pedido de número a produto, e
  dispara — efeito conhecido, não FP a esconder.

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
    # terceira revisão do PR #77: `numeros()` não lia porcentagem em LaTeX
    ("R13", "handoff", "80%", "$\\ge 80\\%$ das duplas manipulando", "meta em LaTeX que o contrato não tem"),
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


DOCUMENTADO = [  # pedido em prosa da sessão anterior ao PR 5: não é origem, e dispara
    ("R03", "handoff", "10 palavras", "Ratificação do teto textual",
     "o PO ratificou em prosa no refazer de dev de 25/09/2026: «pode ser ate 10 palavras»"),
    ("R03", "prd", "10 palavras", "manchetes de até 10 palavras", "idem"),
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


@pytest.mark.parametrize("caso", DOCUMENTADO, ids=_id)
def test_pedido_em_prosa_da_sessao_anterior_ao_pr5_dispara(caso):
    execucao, documento, numero, trecho, motivo = caso
    assert _dispara(execucao, documento, numero, trecho), f"{rotulo(execucao)} {documento}: {numero} ({motivo})"


def test_sete_execucoes_tem_os_41_numeros_e_so_eles():
    """Os 41 números que ficam nas 7 execuções vistas pelo PO são os 30 V, os 9 da régua e os 2 documentados: nenhum
    outro."""
    esperados = {(e, d, n) for e, d, n, _, _ in V + REGUA + DOCUMENTADO}
    achados = {(e, d, n) for e in ("R03", "R04", "R06", "R08", "R10", "R12", "R13") for d in ("handoff", "prd")
               for n, _ in _sem_origem(e, d)}
    assert achados == esperados, (sorted(achados - esperados), sorted(esperados - achados))


def test_pedido_em_prosa_nao_muda_a_origem():
    """O pedido de refazer em prosa não entra no contrato (terceira revisão do PR #77): os números sem origem das
    execuções com pedido gravado são os mesmos sem ele."""
    for execucao in ("R12", "R13"):
        st = estado(execucao)
        assert st.get("pedidos_do_po")
        sem = dict(st, pedidos_do_po=[])
        for documento in ("handoff", "prd"):
            com_pedido = montagem.numeros_sem_origem(corpo(execucao, documento),
                                                     montagem.texto_do_contrato(montagem.contrato(st)))
            sem_pedido = montagem.numeros_sem_origem(corpo(execucao, documento),
                                                     montagem.texto_do_contrato(montagem.contrato(sem)))
            assert com_pedido == sem_pedido, (execucao, documento)


#: Pedidos naturais contra o 80% inventado do KPI-08 da exp02ef1b: na segunda revisão, «deve ser removido», «decidi
#: remover», «Ajuste solicitado: o PRD inventou» faziam dele origem; na terceira, 18 de 22 redações da recusa («Não
#: aceito», «não pode ter», «Não homologo»…) ainda faziam.
PEDIDOS_CONTRA_O_80 = (
    "No KPI-08 deve ser removido o limiar de 80%, que não está no 9f.",
    "Decidi remover o limiar de 80% do KPI-08.",
    "Ajuste solicitado: o PRD inventou o limiar de 80% do KPI-08.",
    "Ajuste solicitado: o limiar de 80% do KPI-08 deve ser removido.",
    "O KPI-08 não pode ter limiar de 80%: o 9f não tem esse número.",
    "O limiar do KPI-08 não deve ser 80%.",
    "O limiar do KPI-08 não pode ser 80%, o 9f não define limiar para ele.",
    "Não aceito o limiar de 80% no KPI-08.",
    "Não aprovo o limiar de 80% do KPI-08.",
    "Não homologo os 80% do KPI-08.",
    "Não confirmo o limiar de 80% do KPI-08.",
    "Não ratifico o limiar de 80% do KPI-08.",
    "O KPI-08 não pode ficar com 80% sem origem no contrato.",
    "O KPI-08 não tem que ter 80%.",
    "Em hipótese nenhuma o KPI-08 deve ter 80%.",
    "Ajuste solicitado: o limiar de 80% do KPI-08 não tem origem no 9f.",
    "Ajuste solicitado: limiar de 80% no KPI-08 sem origem.",
    "Solicitado: o KPI-08 sem o limiar de 80%.",
    "Confirmo: o 80% do KPI-08 não tem origem.",
    "Decidi: KPI-08 com 80% não.",
    "O KPI-08 pode ter 80%? Não está no 9f.",
    "Decidi: H1 com 30%; KPI-08 com 80% não tem origem.",
)


@pytest.mark.parametrize("pedido", PEDIDOS_CONTRA_O_80)
def test_v_continua_quando_o_po_pede_para_tirar_o_numero(pedido):
    st = estado("R13")
    st["pedidos_do_po"] = [{"etapa": "dev", "texto": pedido, "origem": "refazer Dev · completo · 24/10/2026 10:00"}]
    inicios = set(inicios_das_linhas_com("R13", "prd", "KPI-08"))
    contrato = montagem.texto_do_contrato(montagem.contrato(st))
    assert any(i["numero"] == "80%" and i["linha"] in inicios
               for i in montagem.numeros_sem_origem(corpo("R13", "prd"), contrato))
    assert "numero-sem-origem" in {a["codigo"] for a in montagem.validar_prd(st)["achados"]}


#: O teto inventado de 40 palavras do handoff da exp06ef1b-53e011b6 (R10), reescrito com outras redações de teto: tem
#: de continuar sem origem. A segunda revisão perdia 9 delas (8 que a main acusava, mais o LaTeX) — terceira revisão.
ORIGINAL_40 = ("- [ ] Modal de edição inline bloqueia submissão se a legenda ultrapassar 60 palavras ou o bastidor "
               "ultrapassar 40 palavras.")
REDACOES_DO_40 = (
    "- Teto de palavras do texto de bastidor de cada projeto: 40 palavras.",
    "- Teto de palavras por texto de bastidor do projeto: 40 palavras.",
    "- Texto de bastidor (teto): 40 palavras.",
    "- Texto de bastidor (máx.): 40 palavras.",
    "- O texto de bastidor tem 40 palavras, que é o teto.",
    "- 40 palavras é o teto do texto de bastidor.",
    "- O bastidor pode ter até 40 palavras.",
    "- O bastidor não pode ter mais de 40 palavras.",
    "- O bastidor tem limite de 40 palavras.",
    "- Bastidor: no máximo 40 palavras.",
    "- Bastidor: 40 palavras no máximo.",
    "- Bastidor: 40 palavras ou menos.",
    "- Bastidor limitado a 40 palavras.",
    "- O bastidor deve ter no máximo, 40 palavras.",
    "| Bastidor | Teto | 40 palavras |",
    "| Bastidor (teto) | 40 palavras |",
    "| Texto de bastidor | máx. 40 palavras |",
    "- Bastidor com 40 palavras (teto do D0-09).",
    "- O bastidor precisa caber em 40 palavras.",
    "- O bastidor não deve exceder 40 palavras.",
    "- Bastidor de, no máximo, 40 palavras.",
    "- Teto de leitura de 60 palavras por legenda de estande e 40 palavras por texto de bastidor.",
    "- Tetos de leitura: legenda com até 60 palavras e bastidor com 40 palavras.",
    "- Teto estrito de $\\le 40$ palavras por texto de bastidor.",
)


@pytest.mark.parametrize("redacao", REDACOES_DO_40)
def test_v_teto_inventado_com_qualquer_redacao(redacao):
    from tools.cobertura_design import corpo_do_prd

    st = estado("R10")
    assert ORIGINAL_40 in st["handoff_dev"]
    contrato = montagem.texto_do_contrato(montagem.contrato(st))
    handoff = corpo_do_prd(st["handoff_dev"].replace(ORIGINAL_40, redacao))
    assert any(i["numero"] == "40 palavras" for i in montagem.numeros_sem_origem(handoff, contrato)), redacao


@pytest.mark.parametrize("redacao", ("Teto estrito de $\\le 12$ palavras por string da casca do estudante",
                                     "Strings da casca do estudante com no máximo $12$ palavras",
                                     "Strings da casca do estudante: $\\le 12$ palavras"))
def test_v_teto_em_latex_no_prd(redacao):
    """O RNF-USA-001 do PRD da exp02ef1b escreve o teto em LaTeX («$\\le 15$ palavras»): com 12 palavras inventadas, o
    teto tem de pedir origem (a segunda revisão não o regia: procurava «12 palavras» e achava «12$ palavras»)."""
    from tools.cobertura_design import corpo_do_prd

    st = estado("R13")
    original = "Teto estrito de $\\le 15$ palavras por string da casca do estudante"
    assert original in st["prd_final"]
    contrato = montagem.texto_do_contrato(montagem.contrato(st))
    prd = corpo_do_prd(st["prd_final"].replace(original, redacao))
    assert any(i["numero"] == "12 palavras" for i in montagem.numeros_sem_origem(prd, contrato)), redacao


@pytest.mark.parametrize("linha, numero", (
    ("- [ ] Pausa 1: o cliente envia os Stories e aguarda; o painel do professor plota a barra de progresso em tempo "
     "real e, ao atingir ≥ 60% de submissões, habilita [Liberar Mural da Turma].", "60%"),
    ("- [ ] Barra de progresso da rodada: a IA avalia a resposta, e o estudante tem 25 segundos para responder.",
     "25 s"),
    ("- [ ] Skeleton da galeria; a dica aparece após 25 segundos sem toque.", "25 s"),
))
def test_v_regra_na_linha_da_espera_de_carregamento(linha, numero):
    """A Pausa 1 da exp07ef1b (acervo) tem a barra de progresso e o limiar de ≥ 80% de submissões na mesma linha: com
    outro limiar no handoff, a regra trocada tem de pedir origem. Spinner, skeleton e barra de progresso tiravam a
    linha inteira na segunda revisão; agora sai só a duração da espera."""
    from tools.cobertura_design import corpo_do_prd

    st = estado("acervo:exp07ef1b")
    contrato = montagem.texto_do_contrato(montagem.contrato(st))
    handoff = corpo_do_prd(st["handoff_dev"] + "\n\n## 9. Extra\n\n" + linha + "\n")
    assert any(i["numero"] == numero and i["linha"].startswith(linha[:60])
               for i in montagem.numeros_sem_origem(handoff, contrato)), linha
