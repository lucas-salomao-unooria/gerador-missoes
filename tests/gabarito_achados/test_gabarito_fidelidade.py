"""Gabarito da fidelidade (`tools/fidelidade.py`, C2 do backlog de 24/10/2026): cada falso positivo (FP) classificado no
levantamento de produto e de design, com o trecho real, NÃO pode disparar; cada verdadeiro (V) TEM de disparar. Os ids
`P…` e `DS-…` são os do levantamento (`deficiencias/{produto,design}/achados.csv`); o trecho é o do item do checklist.

A conferência roda sobre o estado real com a resposta gravada do juiz e do intérprete (`gabarito_fidelidade.reavaliar`).
Os mutantes mudam uma coisa só no estado real — o documento, o texto do item ou a resposta do juiz — para provar que a
regra que tirou o FP não cega o V vizinho.
"""
from __future__ import annotations

import pytest

from gabarito_fidelidade import (codigos_do_item, documentos_do_design, estado, fora_do_recorte, item, juiz_alterado,
                                 prova_do_item, reavaliar)

E89 = "acervo:exp01em1b-e89e91b3"
S53 = "acervo:exp06ef1b-53e011b6"
C60 = "acervo:exp02em1b-60cfa7f4"
B2E = "acervo:exp03em1b-b2e7b4a3"
E39 = "acervo:exp01em1b-e3980485"
D31 = "acervo:exp03ef1b-317df247"
F4F = "acervo:exp02ef1b-4fd72a9a"
T27 = "exp03ef1b-274a2e75"


#: O juiz de hoje diz no campo `superado_por` quais itens do pedido mais novo do PO o documento segue (revisão da C2,
#: 25/10/2026); as respostas gravadas são de antes do campo e os apontavam na explicação. O gabarito põe no campo os ids
#: que a explicação gravada apontava — no fim de produto da e3980485, a do F28 e a do F31 só davam a data, e os ids são
#: os que o juiz do núcleo da mesma execução apontou para o mesmo item.
SUPERADO_NO_CAMPO = {
    (E39, "nucleo"): {
        "No v4.1, ele monta a configuração escolhendo critérios de um banco de": ["F1", "F2", "F5"],
        "Quem não quiser montar, segue com a configuração padrão (B-B-A). Mecan": ["F2", "F3", "F9"],
        "A narrativa é “antes de aplicar a sua, vamos testar a versão que está": ["F2", "F6"],
        "A construção do aluno fica guardada pra Etapa 5.": ["F1", "F2"],
    },
    (E39, "produto"): {
        "No v4.1, ele monta a configuração escolhendo critérios de um banco de": ["F1", "F2", "F3", "F4", "F5"],
        "Quem não quiser montar, segue com a configuração padrão (B-B-A). Mecan": ["F2", "F3", "F9"],
        "A narrativa é “antes de aplicar a sua, vamos testar a versão que está": ["F2", "F6"],
    },
    # «Remoção completa de Canal B» — o pedido de 21/10 09:44:36, item 1 (F1 e F2 do checklist)
    (E89, "produto"): {"Manter integralmente: o nome da missão, o slug, o ambiente (chatgpt)": ["F1", "F2"]},
}


def _juiz_de_hoje(st, execucao: str, gate: str):
    """A resposta gravada do juiz com o `superado_por` que o prompt de hoje pede; `None` se o caso não tem."""
    saida = None
    for trecho, ids in SUPERADO_NO_CAMPO.get((execucao, gate), {}).items():
        saida = juiz_alterado(st, gate, trecho, saida=saida, superado_por=ids)
    return saida


def _reavaliado(execucao: str, gate: str):
    st = estado(execucao)
    return reavaliar(st, gate, juiz=_juiz_de_hoje(st, execucao, gate))


def _leitura(st, gate: str, por_trecho):
    """A saída do intérprete com a leitura dos itens que têm os trechos, nos ids gravados (o b2e7b4a3 é de antes do
    intérprete, c8a36d2)."""
    import json

    from gabarito_fidelidade import GATES, _id_gravado, _linhas_do_relatorio

    linhas = _linhas_do_relatorio(str(st.get(GATES[gate][2]) or ""))
    itens = []
    for trecho, campos in por_trecho.items():
        antigo = _id_gravado(linhas, trecho)
        assert antigo, trecho
        itens.append({"id": antigo, **campos})
    return "```json\n" + json.dumps({"itens": itens}, ensure_ascii=False) + "\n```"


# ---------------------------------------------------------------------------------------------------------------------
# (1) Núcleo: o item que mora no one-pager ou na spec sai do escopo do A010 (41 de 41 `nao-tratado` eram FP)
# ---------------------------------------------------------------------------------------------------------------------

FP_NUCLEO = [
    ("P100", E89, "Redesenho do Canal A de EM13CO01 (secundária)."),
    ("P101", E89, "Ternário: Atingiu = explorou specs de 2+ módulos E reutilizou template"),
    ("P102", E89, "Em processo = reutilizou em apenas 1 módulo OU reutilizou 2+ sem explo"),
    ("P103", E89, "Não atingiu = tentou tudo do zero sem reutilizar nenhum template."),
    ("P104", E89, "Redesenho do Canal A de EM13CO03 (secundária)."),
    ("P105", E89, "A evidência vem do padrão de alocação na bancada."),
    ("P106", E89, "Ternário: Atingiu = montou a release com margem de segurança"),
    ("P107", E89, "Em processo = montou dentro do orçamento mas precisou desativar módulo"),
    ("P108", E89, "Não atingiu = tentou lançar com saldo negativo repetidamente"),
    ("P109", E89, "Redesenho do Canal A de EM13CO18 (secundária)."),
    ("P110", E89, "Declarar explicitamente que os modificadores “de forma colaborativa”"),
    ("P111", E89, "Focar o Canal A nos componentes capturáveis."),
    ("P112", E89, "Ternário: Atingiu = planejou e executou o lançamento na primeira sequê"),
    ("P113", E89, "Em processo = concluiu mas resetou a seleção 2+ vezes."),
    ("P114", E89, "Não atingiu = abandonou ou tentou forçar publicação ignorando travas."),
    ("P115", E89, "COMO AS HABILIDADES DEVEM SER EXERCITADAS (não como proxy, literalment"),
    ("P152", S53, "Sinalizador de ociosos no dashboard docente (Seção 9): Explicitar que"),
    ("P153", S53, "Validação pré-código (Seção 17): Adicionar: “Validação pré-código: wal"),
    ("P154", S53, "Trocar o marcador [PROPOSTA — validar com PO] de cada uma por [HOMOLOG"),
    ("P155", S53, "Todos os itens anteriormente homologados (tempo em tela de 29 min, tet"),
    ("P184", B2E, "EM13CO13 — substituir “cruza os dados” por observáveis:"),
    ("P185", B2E, "Atingiu: Abriu o anexo da nota metodológica antes de avançar para o De"),
    ("P186", B2E, "Observável: evento de abertura do anexo registrado antes do primeiro c"),
    ("P187", B2E, "Em processo: Abriu o anexo somente após o nudge do sistema."),
    ("P188", B2E, "Não atingiu: Não abriu o anexo em nenhum momento."),
    ("P189", B2E, "Remover “associando a desmontagem geométrica” e usar: marcou corretame"),
    ("P190", B2E, "EM13CO21 — substituir “compreendendo a relação” por observáveis:"),
    ("P191", B2E, "Atingiu: Seleciona parâmetros de escala onde a proporção visual se apr"),
    ("P192", B2E, "Em processo: Interage com os parâmetros de escala mas seleciona config"),
    ("P193", B2E, "EM13CO22 — substituir “articula perfeitamente” por observáveis:"),
    ("P194", B2E, "Atingiu: Campo de Nota de Intenção preenchido com 3-5 linhas + texto c"),
    ("P195", B2E, "Em processo: Campo preenchido com menos de 3 linhas ou texto genérico"),
    ("P196", B2E, "Não atingiu: Campo vazio ou imagem enviada sem texto."),
    ("P197", B2E, "Atingiu: O aluno assumiu autoria publicamente — publicou com Nota de I"),
    ("P198", B2E, "Em processo: Publicou errata, mas o texto não assume responsabilidade"),
    ("P199", B2E, "Não atingiu: Não publicou Nota de Intenção, não usou a errata, ou deix"),
    ("P200", B2E, "EM13CO26 — o “atingiu” não pode depender da errata:"),
    ("P232", E39, "Isso resolve P3 (a escolha do aluno tem consequência,"),
    ("P233", E39, "Manter o restante"),
    ("P234", E39, "No v4.1, ele monta a configuração escolhendo critérios de um banco de"),
    ("P235", E39, "Quem não quiser montar, segue com a configuração padrão (B-B-A). Mecan"),
    ("P236", E39, "A narrativa é “antes de aplicar a sua, vamos testar a versão que está"),
    ("P237", E39, "A construção do aluno fica guardada pra Etapa 5."),
    ("P251", D31, "Explicitar que o estudante não po"),
    ("P252", D31, "⚠️ Especificar o comportamento da ação destrutiva de zerar turma, deta"),
    ("P253", D31, "⚠️ Definir formalmente as regras para reaplicação da missão na mesma t"),
    ("P254", D31, "⚠️ Falta tabela classificando explicitamente cada elemento numérico vi"),
    ("P255", D31, "⚠️ A spec não explicita a visão do gestor escolar/regional, que deve c"),
    ("P256", D31, "⚠️ Ausência de diretriz sobre a perda de validade formativa na reaplic"),
    ("P257", D31, "⚠️ Falta documentar plano de playtest analógico prévio com estudantes"),
]


@pytest.mark.parametrize("caso", FP_NUCLEO, ids=lambda c: c[0])
def test_fp_nucleo_item_sem_prova_no_nucleo_nao_e_achado(caso):
    _, execucao, trecho = caso
    itens, r = _reavaliado(execucao, "nucleo")
    it = item(itens, trecho)
    assert codigos_do_item(r, it["id"]) == [], f"{it['id']}: «{it['texto'][:120]}»"
    assert fora_do_recorte(r, it["id"]) or prova_do_item(r, it["id"]), it["id"]


@pytest.mark.parametrize("execucao", [E89, S53, B2E, E39, D31])
def test_fp_nucleo_das_execucoes_de_outubro_sai_verde(execucao):
    """Nenhuma das cinco execuções tinha contradição no núcleo: o A010 sai 🟢, com os itens fora do recorte à vista."""
    from tools import fidelidade as fid

    itens, r = _reavaliado(execucao, "nucleo")
    assert r["status"] == "aprovado", r["achados"]
    relatorio = fid.relatorio(r, itens, "", "núcleo")
    assert "**Veredito: 🟢**" in relatorio
    assert (r["fora_do_recorte"] == []) or "Fora do recorte deste documento" in relatorio


def test_v_nucleo_contradicao_explicita_continua_bloqueando():
    """Mutante: o juiz diz que o núcleo contraria o pedido — no recorte parcial, a contradição explícita bloqueia."""
    st = estado(E89)
    juiz = juiz_alterado(st, "nucleo", "Redesenho do Canal A de EM13CO01", veredito="violado", citacao="",
                         explicacao="O núcleo mantém o Canal A antigo.")
    itens, r = reavaliar(st, "nucleo", juiz=juiz)
    it = item(itens, "Redesenho do Canal A de EM13CO01")
    assert codigos_do_item(r, it["id"]) == [("pedido-violado", "bloqueio")]
    assert r["status"] == "bloqueado"


def test_v_nucleo_o_mesmo_item_sem_prova_e_cobrado_no_fim_de_produto():
    """Fora do recorte do núcleo não é aprovado: o A060 lê os três documentos e cobra o item sem prova. Mutante: o juiz
    do fim de produto não acha o item."""
    st = estado(B2E)
    juiz = juiz_alterado(st, "produto", "Não atingiu: Não abriu o anexo em nenhum momento.", veredito="nao_tratado",
                         citacao="", citacoes=[], explicacao="")
    itens, r = reavaliar(st, "produto", juiz=juiz)
    it = item(itens, "Não atingiu: Não abriu o anexo em nenhum momento.")
    assert codigos_do_item(r, it["id"]) == [("nao-tratado", "bloqueio")]


# ---------------------------------------------------------------------------------------------------------------------
# (2) `conflito-pedido-regra`: o item que um pedido mais novo do PO contrariou não é decisão a pedir
# ---------------------------------------------------------------------------------------------------------------------

FP_SUPERADO = [
    ("P234", E39, "nucleo", "No v4.1, ele monta a configuração escolhendo critérios de um banco de"),
    ("P235", E39, "nucleo", "Quem não quiser montar, segue com a configuração padrão (B-B-A). Mecan"),
    ("P236", E39, "nucleo", "A narrativa é “antes de aplicar a sua, vamos testar a versão que está"),
    ("P237", E39, "nucleo", "A construção do aluno fica guardada pra Etapa 5."),
    ("P247", E39, "produto", "No v4.1, ele monta a configuração escolhendo critérios de um banco de"),
    ("P248", E39, "produto", "Quem não quiser montar, segue com a configuração padrão (B-B-A). Mecan"),
    ("P249", E39, "produto", "A narrativa é “antes de aplicar a sua, vamos testar a versão que está"),
]


@pytest.mark.parametrize("caso", FP_SUPERADO, ids=lambda c: f"{c[0]}-{c[2]}")
def test_fp_item_superado_por_pedido_mais_novo_do_po_nao_e_conflito(caso):
    _, execucao, gate, trecho = caso
    itens, r = _reavaliado(execucao, gate)
    it = item(itens, trecho)
    assert codigos_do_item(r, it["id"]) == []
    prova = prova_do_item(r, it["id"])
    assert prova and prova.startswith("superado pelo pedido mais novo do PO"), prova


def test_superado_em_parte_ordem_de_nao_mexer_fica_em_atencao():
    """P129 (AMBÍGUO no levantamento) — e89e91b3 F35: «Manter integralmente: o nome da missão, o slug, o ambiente…,
    Canal A e Canal B…» (01/10) e o pedido de 21/10 09:44:36 mandou tirar o Canal B. O pedido novo prevalece no Canal B;
    o resto da ordem não tem prova aqui. Nem 🔵 nem ✅: 🟡, para confirmar."""
    itens, r = _reavaliado(E89, "produto")
    it = item(itens, "Manter integralmente: o nome da missão, o slug, o ambiente (chatgpt)")
    assert codigos_do_item(r, it["id"]) == [("superado-em-parte", "atencao")]
    assert prova_do_item(r, it["id"]) is None
    assert "F1, F2" in next(a["resumo"] for a in r["achados"] if a["id"] == it["id"])


def test_v_resposta_gravada_sem_o_campo_continua_decisao_do_po():
    """A resposta gravada antes do campo `superado_por` apontava «F1-F5» só na explicação: continua 🔵."""
    itens, r = reavaliar(estado(E39), "produto")
    it = item(itens, "No v4.1, ele monta a configuração escolhendo critérios de um banco de")
    assert codigos_do_item(r, it["id"]) == [("conflito-pedido-regra", "decisao_humana")]


def test_v_id_citado_de_passagem_na_explicacao_nao_supera():
    """Mutante da revisão da C2: conflito real com regra da esteira, cuja explicação cita um item novo de passagem."""
    st = estado(E39)
    trecho = "No v4.1, ele monta a configuração escolhendo critérios de um banco de"
    juiz = juiz_alterado(st, "produto", trecho, explicacao=(
        "A regra 7 do núcleo impõe trava irreversível na escolha; o pedido F1 não trata disso."))
    itens, r = reavaliar(st, "produto", juiz=juiz)
    assert codigos_do_item(r, item(itens, trecho)["id"]) == [("conflito-pedido-regra", "decisao_humana")]


def test_v_superado_por_item_que_nao_e_de_pedido_mais_novo_continua_decisao_do_po():
    """Mutante: `superado_por` aponta um item do briefing (mais velho, e com prova) ou um id que não existe — o PO
    decide."""
    st = estado(E39)
    trecho = "No v4.1, ele monta a configuração escolhendo critérios de um banco de"
    itens, r = reavaliar(st, "produto")
    do_briefing = item(itens, "A pegada que eu deixo / O perfil que fala por mim")["id"]
    assert prova_do_item(r, do_briefing) and item(itens, "A pegada que eu deixo")["origem"] == "briefing"
    for ids in ([do_briefing], ["F1", "F999"], "F1 e F2"):
        juiz = juiz_alterado(st, "produto", trecho, superado_por=ids)
        itens, r = reavaliar(st, "produto", juiz=juiz)
        assert codigos_do_item(r, item(itens, trecho)["id"]) == [("conflito-pedido-regra", "decisao_humana")], ids


def test_v_conflito_sem_pedido_mais_novo_apontado_continua_decisao_do_po():
    """Mutante: a explicação do juiz não aponta item nem data de pedido mais novo — conflito com regra da esteira."""
    st = estado(E39)
    trecho = "No v4.1, ele monta a configuração escolhendo critérios de um banco de"
    juiz = juiz_alterado(st, "produto", trecho, explicacao="A regra 7 do núcleo impõe trava irreversível na escolha.")
    itens, r = reavaliar(st, "produto", juiz=juiz)
    assert codigos_do_item(r, item(itens, trecho)["id"]) == [("conflito-pedido-regra", "decisao_humana")]


def test_v_conflito_apontando_pedido_novo_sem_prova_continua_decisao_do_po():
    """Mutante: um dos itens do pedido novo que o juiz aponta em `superado_por` («F1, F2 e F5») não tem prova — o PO
    decide."""
    st = estado(E39)
    juiz = juiz_alterado(st, "nucleo", "Não há banco de critérios nesse momento.", saida=_juiz_de_hoje(st, E39, "nucleo"),
                         veredito="nao_tratado", citacao="", citacoes=[])
    itens, r = reavaliar(st, "nucleo", juiz=juiz)
    alvo = item(itens, "No v4.1, ele monta a configuração escolhendo critérios de um banco de")
    assert codigos_do_item(r, alvo["id"]) == [("conflito-pedido-regra", "decisao_humana")]


# ---------------------------------------------------------------------------------------------------------------------
# (3) Preservação: «Manter o restante» e a justificativa não são ordem de não mexer; a ordem explícita é cobrada
# ---------------------------------------------------------------------------------------------------------------------

FP_PRESERVACAO = [
    ("P245", E39, "Isso resolve P3 (a escolha do aluno tem consequência,"),
    ("P246", E39, "Manter o restante"),
]


@pytest.mark.parametrize("caso", FP_PRESERVACAO, ids=lambda c: c[0])
def test_fp_preservacao_generica_e_justificativa_nao_bloqueiam(caso):
    _, execucao, trecho = caso
    itens, r = _reavaliado(execucao, "produto")
    assert codigos_do_item(r, item(itens, trecho)["id"]) == []


def test_fp_fim_de_produto_da_exp01em1b_e3980485_sai_verde():
    """A execução que terminou 🔴 e fez a missão recomeçar em outra sessão (22/10/2026): sem achado nenhum."""
    _, r = _reavaliado(E39, "produto")
    assert r["status"] == "aprovado", r["achados"]


def test_v_ordem_explicita_de_nao_mexer_continua_cobrada():
    """Mutante: o mesmo item, mas nomeando o que não muda — a citação do juiz (changelog novo) não prova. Continua cobrada,
    como 🟡 desde a C7 (25/10/2026): sem prova de que mudou nem de que ficou, e lida como ordem de não mexer por regex."""
    st = estado(E39)
    itens, r = reavaliar(st, "produto", trocas_no_item={
        "Manter o restante": "Manter a mecânica do banco de critérios da Etapa 5"})
    it = item(itens, "Manter a mecânica do banco de critérios da Etapa 5")
    assert codigos_do_item(r, it["id"]) == [("preservacao-sem-prova", "atencao")]


def test_fp_criterio_ditado_com_nao_altera_nao_e_ordem_de_preservacao():
    """b2e7b4a3 F27: «Não atingiu: Não altera os parâmetros padrão de escala…» é o texto que o PO ditou para a régua."""
    itens, r = _reavaliado(B2E, "produto")
    it = item(itens, "Não atingiu: Não altera os parâmetros padrão de escala e não completa o checklist.")
    assert codigos_do_item(r, it["id"]) == []
    assert prova_do_item(r, it["id"]).startswith("texto ditado pelo PO no documento")


# ---------------------------------------------------------------------------------------------------------------------
# (4) Texto ditado pelo PO presente, letra por letra, no documento = aplicado
# ---------------------------------------------------------------------------------------------------------------------

F12_DITADO = "Remover “associando a desmontagem geométrica” e usar: marcou"
NOVO_F12 = "marcou corretamente no checklist os elementos de truncamento de eixo e recorte de escala como vetores de distorção"


def test_fp_texto_ditado_sem_aspas_sem_o_interprete_fica_em_atencao():
    """P210 — b2e7b4a3 F12 (🔴 `citou-o-pedido` no fim de produto, 21/10/2026). A execução é de antes do intérprete: o
    texto do PO é novo no corpo, mas a comparação literal não lê o verbo — 🟡 com a dúvida, não 🔴 nem ✅."""
    itens, r = _reavaliado(B2E, "produto")
    it = item(itens, F12_DITADO)
    assert codigos_do_item(r, it["id"]) == [("texto-ditado-a-conferir", "atencao")]
    assert prova_do_item(r, it["id"]) is None


def test_fp_texto_ditado_sem_aspas_com_o_interprete_prova_o_item():
    """O mesmo F12 com a leitura que o intérprete dá (c8a36d2): o texto a pôr no corpo, o texto a tirar fora."""
    st = estado(B2E)
    st["interpretacao_fidelidade_saida"] = _leitura(st, "produto", {F12_DITADO: {
        "inserir": [NOVO_F12], "remover": ["associando a desmontagem geométrica"], "outras_exigencias": False}})
    itens, r = reavaliar(st, "produto")
    it = item(itens, F12_DITADO)
    assert codigos_do_item(r, it["id"]) == []
    assert prova_do_item(r, it["id"]).startswith("texto ditado no documento")


def test_duvida_do_texto_ditado_e_do_superado_em_parte_sai_do_recorte_do_nucleo():
    """No núcleo (parcial), as duas atenções novas são falta de prova, não contradição: saem do recorte e o fim de
    produto as confere."""
    import json

    from tools import fidelidade as fid

    frase = "o aluno descobre sozinho qual é a resposta certa do desafio"
    itens = [
        {"id": "F1", "origem": "refazer Produto · produto · 22/10/2026 10:00:00", "tipo": "pedido",
         "texto": f"Na tela de abertura, não mostrar a frase {frase}."},
        {"id": "F2", "origem": "refazer Produto · produto · 22/10/2026 10:00:00", "tipo": "pedido",
         "texto": "Tirar o Canal B da Etapa 3."},
        {"id": "F3", "origem": "refazer Produto · produto · 01/10/2026 10:00:00", "tipo": "pedido",
         "texto": "Manter integralmente: o nome da missão, o slug e o Canal B da Etapa 3."},
    ]
    juiz = "```json\n" + json.dumps({"decisoes": [
        {"id": "F1", "veredito": "atendido", "citacao": frase},
        {"id": "F2", "veredito": "atendido", "citacao": "A Etapa 3 avalia só pelo Canal A, sem enquete."},
        {"id": "F3", "veredito": "conflito_com_regra", "superado_por": ["F2"], "explicacao": ""},
    ]}, ensure_ascii=False) + "\n```"
    docs = {"nucleo_narrativo": f"Na abertura, {frase}.\nA Etapa 3 avalia só pelo Canal A, sem enquete."}
    anteriores = {"nucleo_narrativo": "Na abertura, o aluno escolhe um caminho.\nA Etapa 3 tem enquete (Canal B)."}
    inteiro = fid.aplicar(itens, juiz, docs, anteriores=anteriores)
    assert {(a["id"], a["codigo"]) for a in inteiro["achados"]} == {
        ("F1", "texto-ditado-a-conferir"), ("F3", "superado-em-parte")}
    parcial = fid.aplicar(itens, juiz, docs, anteriores=anteriores, parcial=True)
    assert parcial["achados"] == [] and parcial["status"] == "aprovado"
    assert {f["id"] for f in parcial["fora_do_recorte"]} == {"F1", "F3"}


PROIBICOES_SEM_ASPAS = [
    "Na tela de abertura, não mostrar a frase",
    "Remover da tela de abertura",
    "Tirar o trecho",
]


@pytest.mark.parametrize("ordem", PROIBICOES_SEM_ASPAS)
def test_v_proibicao_sem_aspas_com_o_texto_novo_no_corpo_nao_prova(ordem):
    """Mutante da revisão da C2: o item manda tirar ou não mostrar o texto (sem aspas), o juiz diz «atendido» citando
    esse texto, e ele é novo no corpo. Sem o intérprete: 🟡, nunca ✅. Com a leitura dele: o texto em `remover` não
    prova, e a leitura sem o texto em `inserir` volta a `citou-o-pedido`."""
    st = estado(B2E)
    troca = {"Remover “associando a desmontagem geométrica” e usar:": ordem}
    itens, r = reavaliar(st, "produto", trocas_no_item=troca)
    it = item(itens, NOVO_F12)
    assert codigos_do_item(r, it["id"]) == [("texto-ditado-a-conferir", "atencao")]
    assert prova_do_item(r, it["id"]) is None

    st["interpretacao_fidelidade_saida"] = _leitura(st, "produto", {F12_DITADO: {
        "inserir": [], "remover": [NOVO_F12], "outras_exigencias": False}})
    itens, r = reavaliar(st, "produto", trocas_no_item=troca)
    it = item(itens, NOVO_F12)
    assert prova_do_item(r, it["id"]) is None and codigos_do_item(r, it["id"]), r["achados"]

    st["interpretacao_fidelidade_saida"] = _leitura(st, "produto", {F12_DITADO: {"inserir": [], "remover": []}})
    itens, r = reavaliar(st, "produto", trocas_no_item=troca)
    assert codigos_do_item(r, item(itens, NOVO_F12)["id"]) == [("citou-o-pedido", "bloqueio")]


def test_v_texto_ditado_com_o_texto_citado_ainda_no_documento_nao_prova():
    """Mutante: o texto entre aspas que o item cita continua no one-pager — a prova volta ao juiz (e ele citou o
    pedido)."""
    st = estado(B2E)
    ditado = "elementos de truncamento de eixo e recorte de escala como vetores de distorção"
    assert ditado in st["one_pager"]
    st["one_pager"] = st["one_pager"].replace(ditado, f"{ditado}, associando a desmontagem geométrica", 1)
    itens, r = reavaliar(st, "produto")
    it = item(itens, "Remover “associando a desmontagem geométrica” e usar: marcou")
    assert ("citou-o-pedido", "bloqueio") in codigos_do_item(r, it["id"])


def test_v_texto_ditado_ausente_do_documento_continua_sem_prova():
    """Mutante: o texto ditado saiu do one-pager e da spec — o juiz citou o pedido, e nada prova."""
    st = estado(B2E)
    ditado = "elementos de truncamento de eixo e recorte de escala como vetores de distorção"
    for k in ("one_pager", "spec_missao", "nucleo_narrativo"):
        st[k] = st[k].replace(ditado, "elementos do gráfico")
    itens, r = reavaliar(st, "produto")
    it = item(itens, "Remover “associando a desmontagem geométrica” e usar: marcou")
    assert ("citou-o-pedido", "bloqueio") in codigos_do_item(r, it["id"])


# Os FP que a fidelidade ainda dá: a prova depende de ler sentido (paráfrase do juiz, ou o pedido que não é texto
# ditado), e a regra não lê prosa. Na execução real, a linha de base os rebaixou a 🟡 — e o relatório passou a dizê-lo
# (caso 6). O de b2e7b4a3 F1 se resolve com o intérprete, que marca o cabeçalho (c8a36d2, depois da execução).
RESIDUAIS = [
    ("P128", E89, "produto", "Não atingiu = abandonou ou tentou forçar publicação ignorando travas.",
     "a segunda citação do juiz parafraseia «destinado exclusivamente ao professor no hub docente»"),
    ("P183", C60, "produto", "O encaminhamento é simulado — não envia mensagem real.",
     "o documento diz «mensagem de confirmação simulada»; o juiz copiou o pedido"),
    ("P209", B2E, "produto", "Corrigir os critérios ternários do Canal A das seguintes habilidades.",
     "cabeçalho: sem a leitura do intérprete, não tem prova própria"),
]


@pytest.mark.parametrize("caso", RESIDUAIS, ids=lambda c: c[0])
@pytest.mark.xfail(strict=True, reason="FP residual: depende de sentido — ver o comentário de RESIDUAIS")
def test_fp_residual_que_a_regra_literal_nao_resolve(caso):
    _, execucao, gate, trecho, _ = caso
    itens, r = _reavaliado(execucao, gate)
    assert codigos_do_item(r, item(itens, trecho)["id"]) == []


def test_fp_cabecalho_marcado_pelo_interprete_vale_pela_prova_dos_itens():
    """P209 com a leitura que o intérprete daria (c8a36d2): o cabeçalho vale pela prova dos itens que anuncia."""
    import json

    st = estado(B2E)
    trecho = "Corrigir os critérios ternários do Canal A das seguintes habilidades."
    from gabarito_fidelidade import _id_gravado, _linhas_do_relatorio

    antigo = _id_gravado(_linhas_do_relatorio(st["fidelidade_report"]), trecho)
    f12 = _id_gravado(_linhas_do_relatorio(st["fidelidade_report"]), F12_DITADO)
    st["interpretacao_fidelidade_saida"] = "```json\n" + json.dumps(
        {"itens": [{"id": antigo, "cabecalho": True, "inserir": [], "remover": []},
                   {"id": f12, "inserir": [NOVO_F12], "remover": ["associando a desmontagem geométrica"],
                    "outras_exigencias": False}]}, ensure_ascii=False) + "\n```"
    itens, r = reavaliar(st, "produto")
    it = item(itens, trecho)
    # o cabeçalho só cai se todos os itens do mesmo pedido têm prova; os outros achados da execução eram do F12 (que o
    # intérprete prova) e do F27 (a ordem de não mexer que é o texto ditado)
    assert codigos_do_item(r, it["id"]) == [], r["achados"]


# ---------------------------------------------------------------------------------------------------------------------
# (5) Falso negativo: a proibição do briefing vira item e é conferida em código
# ---------------------------------------------------------------------------------------------------------------------

def test_v_secao_travada_pelo_briefing_violada_bloqueia_sem_o_juiz():
    """274a2e75 (07/10/2026): «secao_ds: unoogaleria · É PROIBIDO usar qualquer outro design system», one-pager e
    spec em `unoochat`, fidelidade 🟢 com 0 itens. O juiz nem rodou; o código confere a seção declarada."""
    itens, r = reavaliar(estado(T27), "produto", juiz="")
    it = item(itens, "secao_ds: unoogaleria")
    assert it["tipo"] == "trava" and it["origem"] == "briefing"
    assert codigos_do_item(r, it["id"]) == [("briefing-violado", "bloqueio")]
    resumo = next(a["resumo"] for a in r["achados"] if a["id"] == it["id"])
    assert "`one_pager` declara `unoochat`" in resumo and "`spec_missao` declara `unoochat`" in resumo
    assert r["status"] == "bloqueado"


def test_fp_secao_travada_respeitada_e_provada_em_codigo():
    """O núcleo da mesma execução declara `unoogaleria`: a trava se prova sem o juiz."""
    itens, r = reavaliar(estado(T27), "nucleo", juiz="")
    it = item(itens, "secao_ds: unoogaleria")
    assert codigos_do_item(r, it["id"]) == []
    assert "`unoogaleria`" in prova_do_item(r, it["id"])


def test_v_secao_extra_proibida_pelo_briefing_bloqueia():
    """Mutante: o one-pager declara a seção do briefing, mas com uma extra — e o briefing proíbe outras seções."""
    st = estado(T27)
    for k in ("one_pager", "spec_missao"):
        st[k] = st[k].replace("unoochat", "unoogaleria")
    st["one_pager"] = st["one_pager"].replace("Seção do DS: `unoogaleria`",
                                              "Seção do DS: `unoogaleria` · Seções extras do DS: unoochat", 1)
    itens, r = reavaliar(st, "produto", juiz="")
    it = item(itens, "secao_ds: unoogaleria")
    assert codigos_do_item(r, it["id"]) == [("briefing-violado", "bloqueio")]
    assert "extras `unoochat`" in next(a["resumo"] for a in r["achados"] if a["id"] == it["id"])


def test_secao_que_o_pedido_do_po_nomeia_fica_em_atencao():
    """Mutante: um pedido do PO nomeia a seção que os documentos declaram — vale o mais novo, e quem confirma é o PO."""
    st = estado(T27)
    st["pedidos_do_po"] = [{"origem": "refazer Produto · produto · 08/10/2026 10:00:00", "etapa": "produto",
                            "texto": "Pode usar o unoochat: a conversa da turma pede o chat."}]
    itens, r = reavaliar(st, "produto", juiz="")
    it = item(itens, "secao_ds: unoogaleria")
    assert codigos_do_item(r, it["id"]) == [("briefing-violado", "atencao")]


# ---------------------------------------------------------------------------------------------------------------------
# (6) O relatório concorda com o status depois que a linha de base rebaixa
# ---------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("execucao", [E89, C60])
def test_relatorio_rebaixado_pela_linha_de_base_diz_o_veredito_final(execucao):
    """e89e91b3 e 60cfa7f4: `fidelidade_status` 🟡 e o relatório começando por «**Veredito: 🔴**»."""
    from agents.callbacks import extrair_envelope
    from tools import linha_de_base as lb

    st = estado(execucao)
    gravado = st["fidelidade_report"]
    assert st["fidelidade_status"] == "amarelo" and "**Veredito: 🔴**" in gravado  # o defeito, como gravado
    envelope = st["fidelidade_status_envelope"]
    ids = [a["id"] for a in envelope["achados"] if a.get("linha_de_base") in (lb.TEXTO_INALTERADO, lb.FORA_DA_CORRECAO)]
    assert ids
    novo = lb.relatorio_rebaixado(gravado, envelope, ids)
    assert "**Veredito: 🟡**" in novo and "**Veredito: 🔴**" not in novo
    assert not any(f"🔴 **{i}**" in novo for i in ids)
    assert extrair_envelope(novo)["status"] == "amarelo"


def test_linha_de_base_reescreve_o_cabecalho_ao_rebaixar():
    """O caminho inteiro: o estado da 60cfa7f4 antes da linha de base (o 🔴 do F21, citação em texto que a correção não
    tocou) — o relatório reescrito diz 🟡 no cabeçalho, na marca do achado e no envelope."""
    from agents.callbacks import extrair_envelope
    from tools import linha_de_base as lb

    st = estado(C60)
    gravado = st["fidelidade_status_envelope"]
    antes = []
    for a in gravado["achados"]:
        a = {k: v for k, v in a.items() if k not in ("linha_de_base", "severidade_original")}
        a["severidade"] = "bloqueio"
        a["resumo"] = a["resumo"].split("] ", 1)[-1]
        antes.append(a)
    relatorio = st["fidelidade_report"].split("\n\n---\n> 📏")[0]
    estado_antes = {"fidelidade_status": "bloqueado", "fidelidade_report": relatorio,
                    "fidelidade_status_envelope": {**gravado, "status": "bloqueado", "achados": antes}}
    edicoes = [{"documento": "one_pager", "de": "texto que não existe", "para": "outro texto que não existe"}]
    delta, _ = lb.aplicar(estado_antes, {}, edicoes, ["fidelidade_status"])
    assert delta["fidelidade_status"] == "amarelo"
    novo = delta["fidelidade_report"]
    # o cabeçalho é o da C5 (#83): «**Veredito: 🟡 amarelo (revisto — ver a nota no fim)**»
    assert novo.startswith(relatorio.split("**Veredito:")[0]) and "**Veredito: 🟡" in novo
    assert "**Veredito: 🔴" not in novo and "🔴 **F21**" not in novo and "🟡 **F21**" in novo
    assert extrair_envelope(novo)["status"] == "amarelo"


# ---------------------------------------------------------------------------------------------------------------------
# (7) Remoção × preservação no design: desde o PR 6 o A094 lê o anexo, não a spec
# ---------------------------------------------------------------------------------------------------------------------

def test_fp_remocao_do_texto_que_so_a_spec_tem_nao_e_cobrada_no_design():
    """DS-073..077 (4fd72a9a, 23/10/2026): «Publicar no Álbum» ficou só na spec, que a preservação restaurava e a
    fidelidade de design mandava tirar. Com os documentos do design de hoje (anexo no lugar da spec, PR 6), nenhum
    `remocao-*` sobre ele — o item de spec vai a produto pela triagem (PR 5) e é conferido no A060."""
    st = estado(F4F)
    assert "spec_missao" not in documentos_do_design()
    _, r = reavaliar(st, "design")
    assert not [a for a in r["achados"] if a["codigo"].startswith("remocao") and "Publicar no Álbum" in a["resumo"]]


def test_v_remocao_cobrada_quando_o_texto_esta_num_documento_do_design():
    """Mutante: a mesma leitura com a spec entre os documentos (como antes do PR 6) — a remoção volta a ser cobrada."""
    st = estado(F4F)
    _, r = reavaliar(st, "design", documentos=documentos_do_design() + ["spec_missao"])
    assert [a for a in r["achados"] if a["codigo"].startswith("remocao") and "Publicar no Álbum" in a["resumo"]]


# ---------------------------------------------------------------------------------------------------------------------
# Design: verbo dentro das aspas ou rótulo do pedido não é exigência
# ---------------------------------------------------------------------------------------------------------------------

def test_fp_verbo_dentro_das_aspas_nao_faz_exigencia():
    """DS-034 — 60cfa7f4 F25: «… a chance de clicar “fixar aviso” por acaso é 20%. É alta.» — o juiz a tratou como
    contexto, e o código a reclassificava como exigência pelo «fixar» do nome do botão."""
    itens, r = _reavaliado(C60, "design")
    it = item(itens, "Sobre o rusher: com 5 opções no menu, a chance de clicar")
    assert codigos_do_item(r, it["id"]) == []
    assert prova_do_item(r, it["id"]) == "(contexto do pedido, sem exigência)"


def test_v_verbo_fora_das_aspas_continua_exigencia():
    """Mutante: o juiz trata como contexto um item com verbo do PO fora das aspas — `exigencia-dispensada`, 🟡 desde a C7
    (25/10/2026), e o classificador de sentido também lê exigência: não é dispensado."""
    st = estado(C60)
    st["interpretacao_fidelidade_saida"] = ""  # sem a leitura do intérprete, que prova a troca pelo texto ditado
    trecho = "Trocar o botão “Ver Métricas da Publicação” por “Configuração da Publicação”."
    juiz = juiz_alterado(st, "produto", trecho, veredito="contexto", citacao="", citacoes=[])
    itens, r = reavaliar(st, "produto", juiz=juiz)
    assert codigos_do_item(r, item(itens, trecho)["id"]) == [("exigencia-dispensada", "atencao")]


def test_exige_acao_le_so_a_voz_do_po():
    from tools.fidelidade import exige_acao

    assert not exige_acao("Sobre o rusher: com 5 opções no menu, a chance de clicar “fixar aviso” por acaso é 20%. É alta.")
    assert not exige_acao("> “O que não pode faltar na foto?” Botão: “Publicar no Álbum” Ajuste solicitado: Para o exemplo:")
    assert exige_acao("Trocar o botão “Ver Métricas da Publicação” por “Configuração da Publicação”.")
    assert exige_acao("O aluno vê o aviso. Remover o banner “fixar aviso” da tela.")
