"""test_propagacao.py

A régua do PR 1 do plano «Produto dono do contrato» (`tools/propagacao.py`): só leitura, quatro relatórios por sessão.
Os testes usam estados sintéticos para cada regra e o acervo dourado (`tests/acervo/`) para a linha de base, com os
mutantes que o plano lista para medir os PRs seguintes: «apagar bloco 13», «classe mecanica_x», «H1 25×30»,
«35 palavras omitidas» e «opção Lugar removida».
"""
import copy
import json
import sys

import pytest

from scripts.regressao_gates import RAIZ
from tools import propagacao as pg

ACERVO = RAIZ / "tests" / "acervo"


def _estado(missao):
    return json.loads((ACERVO / missao / "estado.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def exp06ef1b():
    return _estado("exp06ef1b")


@pytest.fixture(scope="module")
def exp02ef1b():
    return _estado("exp02ef1b-4fd72a9a")


@pytest.fixture(scope="module")
def exp03em1b():
    return _estado("exp03em1b-b2e7b4a3")


def _d0(campo, classe, decisao, base="padrao", titulo="", base_texto=""):
    return {"id": "D0-1", "campo": campo, "classe": classe, "cor": "verde", "base": base, "titulo": titulo,
            "decisao": decisao, "base_texto": base_texto}


# --------------------------------------------------------------------------- 1. pedido do PO × documentos
def test_frases_do_pedido_separam_texto_atual_do_novo():
    texto = ("### E3-ALU-01\n\nTexto atual:\n\n> “A moldura precisa ter pelo menos 10% da foto!”\n\n"
             "Ajuste solicitado:\n\n> “Aumente a moldura.”\n\nNo botão, trocar \"Concluir Análise\" por \"Pronto agora\".")
    papeis = {f["texto"]: f["papel"] for f in pg.frases_do_pedido(texto)}
    assert papeis == {"A moldura precisa ter pelo menos 10% da foto!": "atual", "Aumente a moldura.": "novo",
                      "Concluir Análise": "atual", "Pronto agora": "novo"}


def test_relato_de_gate_colado_vale_pelas_citacoes_de_dentro():
    # 14:37 da exp02ef1b: «…» envolvendo “…” — o relato inteiro não é uma frase do PO
    texto = "❌ remocao-nao-aplicada · tirar «Botão: “Publicar no Álbum” Ajuste solicitado: Para o exemplo»."
    assert [f["texto"] for f in pg.frases_do_pedido(texto)] == ["Publicar no Álbum"]


def test_pedido_aplicado_so_a_jusante():
    state = {
        "one_pager": "## 4. Jornada\n\nA Visita diz “Que legal, na sua escola as crianças só comem!”.\n",
        "spec_missao": "# Spec\n\n## 2. Mecanismo\n\nnada\n\n## 14. Ambiente (D9)\n\nBotão `Colocar no álbum`.\n",
        "copy_strings_revisada": "| E5 | Colocar no álbum |\n| E4 | Que legal, na sua escola as crianças só comem! |",
        "prd_final": "Botão «Colocar no álbum».",
        "pedidos_do_po": [{"origem": "refazer Design", "etapa": "design", "texto":
                           'Trocar "Publicar no Álbum" por "Colocar no álbum". Manter “Que legal, na sua escola as crianças só comem!”.'}],
    }
    frases = {f["texto"]: f for f in pg.pedido_x_documentos(state)[0]["frases"]}
    # o bloco 14 da spec é do D9: não conta como produto
    assert frases["Colocar no álbum"]["situacao"] == "so-a-jusante"
    assert frases["Colocar no álbum"]["contagens"]["spec_produto"] == 0
    assert frases["Colocar no álbum"]["contagens"]["prd_final"] == 1
    assert frases["Que legal, na sua escola as crianças só comem!"]["situacao"] == "em-produto"
    assert frases["Publicar no Álbum"]["situacao"] == "ausente"


def test_pedido_repetido_na_conversa_nao_conta_duas_vezes():
    state = {"pedidos_do_po": [{"origem": "refazer Produto", "etapa": "produto", "texto": 'Trocar "a b c" por "d e f".'}]}
    conversa = {"historico_correcoes": [{"quando": "x", "etapa": "produto", "pedido": 'Trocar  "a b c" por "d e f". '},
                                        {"quando": "y", "etapa": "design", "pedido": 'Outro "g h i".'}]}
    assert [p["etapa"] for p in pg.pedidos_do_po(state, conversa)] == ["produto", "design"]


def test_exp02ef1b_pedido_de_23_10_textos_novos_so_a_jusante(exp02ef1b):
    """Linha de base do quadro: os textos novos do pedido de 23/10 13:24 têm 0 ocorrências no contrato e chegam a
    design, handoff e PRD; dos 10 «textos atuais», só «Publicar no Álbum» e «Pela cor da roupa» (esta no one-pager
    resumido) existem em produto."""
    pedido = next(p for p in pg.pedido_x_documentos(exp02ef1b) if "13:24" in p["origem"])
    novos = {f["texto"]: f for f in pedido["frases"] if f["papel"] == "novo"}
    for texto in ("Aumente a moldura.", "Na foto, vi crianças comendo!", "Marque no pátio o que ficou fora da sua foto.",
                  "O que é parecido?", "Foto de leitura: o que precisa aparecer?", "Criança lendo", "Colocar no álbum"):
        assert novos[texto]["situacao"] == "so-a-jusante", texto
        assert novos[texto]["em_contrato"] == 0
    atuais = [f for f in pedido["frases"] if f["papel"] == "atual"]
    assert len(atuais) == 10
    assert sorted(f["texto"] for f in atuais if f["situacao"] == "em-produto") == ["Pela cor da roupa", "Publicar no Álbum"]


# --------------------------------------------------------------------------- 2. classe real de cada [D0-n]
@pytest.mark.parametrize("classe, esperado", [("mecanica_x", "produto"), ("mecanica_param", "produto"),
                                              ("curriculo-extra", "produto"), ("parametro", "produto"),
                                              ("estado", "ux")])
def test_mutante_classe_mecanica_x_e_produto_por_prefixo(classe, esperado):
    d = pg.classificar_d0(_d0("2.mecanismo_etapa", classe, "Fixar o comportamento do botão."), {})
    assert d["classe_real"] == esperado


def test_d0_que_fecha_parametro_aberto_e_produto():
    docs = {"one_pager": "Inatividade: [PARÂMETRO — a definir por produto: tempo de inatividade no chat, sugestão: 90 segundos]"}
    d = pg.classificar_d0(_d0("3.inatividade_chat", "duracao", "Fixar em 90 segundos o aviso."), docs)
    assert d["classe_real"] == "produto"
    assert any("fecha [PARÂMETRO" in m for m in d["motivos"])


def test_d0_que_aplica_parecer_datado_e_a_decisao_nao_foi_gravada():
    # exp02em1b D0-5: o PO decidiu 90 s no de acordo de 21/10, o one-pager ficou com o [PARÂMETRO] e a sugestão
    docs = {"one_pager": "[PARÂMETRO — a definir por produto: tempo de inatividade no chat, sugestão: 90 segundos]"}
    d = pg.classificar_d0(_d0("3.inatividade_chat", "duracao", "Fixar em 90 segundos.",
                              base_texto="Parecer formal do responsável de produto emitido em 21/10/2026 às 15:43:51"),
                          docs, pareceres="de_acordo · produto · 21/10/2026 15:43:51\n→ 90s")
    assert d["classe_real"] == "aplica-parecer"
    assert d["nao_gravada"] == ["90 s"]
    assert not any("não conferida" in m for m in d["motivos"])


def test_parecer_generico_nao_aprova_proposta():
    # exp02ef1b D0-4: «Tudo de acordo e podemos seguir design» tornou PQ-01..05 contratuais (decisão D3)
    docs = {"spec_missao_gate0": "[PROPOSTA — validar com PO: Metas e limiares das 5 perguntas de produto PQ-01 a PQ-05]"}
    d = pg.classificar_d0(_d0("9f.perguntas_produto", "dados", "Consolidar como contratuais os cortes.",
                              titulo="validação dos limiares de PQ-01 a PQ-05",
                              base_texto='Parecer de Produto de 22/10/2026 ("Tudo de acordo e podemos seguir design")'), docs)
    assert d["classe_real"] == "produto"
    assert any("genérico" in m for m in d["motivos"])


def test_d0_que_mantem_o_que_o_po_recusou_contraria_produto():
    pareceres = ("[PROPOSTA P0b: validar com PO: Utilização do componente StoryPoll nativo do Unoovista] "
                 "→ ignorar / não implementar")
    d0 = _d0("9.componente_canal_b", "evidencia", "Manutenção do componente nativo `StoryPoll` no Canal B.")
    recusas = pg.recusas_do_po(pareceres)
    assert recusas[0]["termos"] == ["StoryPoll"]
    assert pg.classificar_d0(d0, {}, pareceres, recusas)["classe_real"] == "contraria-produto"
    assert pg.classificar_d0(d0, {}, "", [])["classe_real"] != "contraria-produto"


def test_alvo_de_toque_abaixo_do_padrao_marca_sem_virar_produto():
    d = pg.classificar_d0(_d0("7.acessibilidade_slider", "acessibilidade", "Área de toque de 48x48 px."), {})
    assert d["classe_real"] == "ux"
    assert "48 px" in d["contraria_padrao"]
    assert pg.alvo_de_toque_minimo() == 64


def test_tempo_de_animacao_novo_so_informa():
    d = pg.classificar_d0(_d0("6.scaffolding", "duracao", "Pulso de 2 segundos no botão; some após 5 segundos."), {})
    assert d["classe_real"] == "ux"
    assert d["numeros_novos"] == ["2 s", "5 s"]


def test_acervo_exp03em1b_classe_real(exp03em1b):
    reais = {d["id"]: d for d in pg.classe_real_d0(exp03em1b)}
    assert len(reais) == 9
    assert {i for i, d in reais.items() if d["classe_real"] == "produto"} == {"D0-6", "D0-7", "D0-8"}
    assert "contraria_padrao" in reais["D0-9"]


def test_acervo_exp02ef1b_classe_real(exp02ef1b):
    reais = {d["id"]: d for d in pg.classe_real_d0(exp02ef1b)}
    assert [d["cor"] for d in reais.values()] == ["verde"] * 8
    assert {i for i, d in reais.items() if d["classe_real"] == "produto"} == {"D0-1", "D0-2", "D0-3", "D0-4", "D0-7", "D0-8"}
    assert any("mecanica_param" in m for m in reais["D0-2"]["motivos"])


# --------------------------------------------------------------------------- 3. números e textos sem origem
_ONE_PAGER_H1 = ("## 17. Hipóteses de validação\n\n- **Hipótese 1 (Usabilidade motora):** manipular as alças.\n"
                 "  - *Indica falha:* Mais de 30% das duplas desistirem de ajustar a moldura e clicarem em confirmar.\n")


def _prd(corpo):
    return f"# PRD\n\n## Hipóteses\n\n{corpo}\n\n---\n\n# Anexo — conteúdo aprovado pelo PO\n\n{_ONE_PAGER_H1}"


def test_mutante_h1_25_x_30():
    trocado = pg.contrato_no_corpo(_ONE_PAGER_H1, pg_corpo := _prd(
        "- *Indica falha:* Mais de 25% das duplas desistirem de ajustar a moldura e clicarem em confirmar.").split("# Anexo")[0])
    assert [(c["situacao"], c["contrato"], c["corpo"]) for c in trocado] == [("trocado", "30%", "25%")]
    assert "25%" in pg_corpo
    fiel = pg.sem_origem({"one_pager": _ONE_PAGER_H1, "prd_final": _prd(
        "- *Indica falha:* Mais de 30% das duplas desistirem de ajustar a moldura e clicarem em confirmar.")})
    assert fiel["prd"]["contrato_no_corpo"] == []


def test_mutante_h1_no_anexo_nao_esconde_a_troca_no_corpo():
    res = pg.sem_origem({"one_pager": _ONE_PAGER_H1, "prd_final": _prd(
        "- *Indica falha:* Mais de 25% das duplas desistirem de ajustar a moldura e clicarem em confirmar.")})
    assert [c["situacao"] for c in res["prd"]["contrato_no_corpo"]] == ["trocado"]


def test_linha_parecida_de_outra_sessao_nao_e_troca():
    # «Subtotal Sessão 2» do one-pager não é a linha «Subtotal Sessão 1» do PRD (exp02ef1b)
    one_pager = "## 10. Tempo\n\n| *Subtotal Sessão 2* | *12 min* | *30 min* |\n"
    corpo = "| **Subtotal Sessão 1** | **12 min** | **25 min** |\n| **Subtotal Sessão 2** | 30 min |"
    assert pg.contrato_no_corpo(one_pager, corpo) == []


def test_mutante_35_palavras_omitidas(exp06ef1b):
    """exp06ef1b: o §15 tem «35 palavras» e o corpo do PRD não; devolvido ao corpo, o achado some."""
    real = pg.sem_origem(exp06ef1b)["prd"]["contrato_no_corpo"]
    assert [(c["secao"], c["contrato"], c["situacao"]) for c in real] == [("§15", "35 palavras", "ausente")]
    mutante = copy.deepcopy(exp06ef1b)
    prd = mutante["prd_final"]
    fim_do_primeiro_titulo = prd.find("\n", prd.find("\n# ") + 1)
    mutante["prd_final"] = (prd[:fim_do_primeiro_titulo] + "\n\n- Balões de notificação da comissão: até 35 palavras "
                            "por balão.\n" + prd[fim_do_primeiro_titulo:])
    assert pg.sem_origem(mutante)["prd"]["contrato_no_corpo"] == []


def test_procedencia_dos_numeros_do_corpo():
    state = {"one_pager": "Duração de 12 minutos.", "copy_strings_revisada": "Teto de 13 palavras.",
             "handoff_dev": "Polling de 3 segundos.", "prd_final": "12 min; 13 palavras; 3 s; 80%."}
    nums = {proc: [i["numero"] for i in itens] for proc, itens in pg.sem_origem(state)["prd"]["numeros"].items()}
    assert nums == {"produto": ["12 min"], "design": ["13 palavras"], "dev": ["3 s"], "so-no-documento": ["80%"]}


def test_mutante_opcao_lugar_removida():
    one_pager = ('## 4. Jornada\n\n- Tocar no pictograma: a "Atividade", descartando "Cor da roupa" e "Lugar".\n'
                 "## 5. Outra\n")
    copy_ok = '| E5-ALU-01 | opções | "Atividade" · "Cor da roupa" · "Lugar" |'
    # «lugar» como palavra solta, em outra frase, não conta como a opção
    copy_sem = '| E5-ALU-01 | opções | "Atividade" · "Cor da roupa" |\n| E4 | Duas fotos do mesmo lugar. |'
    ok = pg.sem_origem({"one_pager": one_pager, "copy_strings_revisada": copy_ok})["s4_a_jusante"]["copy_strings_revisada"]
    sem = pg.sem_origem({"one_pager": one_pager, "copy_strings_revisada": copy_sem})["s4_a_jusante"]["copy_strings_revisada"]
    assert (ok["chegaram"], ok["total"]) == (3, 3)
    assert (sem["chegaram"], sem["faltam"]) == (2, ["Lugar"])


# --------------------------------------------------------------------------- 4. [D0-n] a jusante × spec
def test_mutante_apagar_bloco_13(exp06ef1b):
    real = pg.d0_a_jusante(exp06ef1b)
    assert real["bloco_13"] and real["na_spec"] == [1, 2, 3, 4, 5] and real["orfas"] == {}
    mutante = copy.deepcopy(exp06ef1b)
    b13 = pg.bloco_13(mutante["spec_missao"])
    assert b13
    mutante["spec_missao"] = mutante["spec_missao"].replace(b13, "")
    sem = pg.d0_a_jusante(mutante)
    assert not sem["bloco_13"]
    assert sem["orfas"]["prd_final"] == [1, 2, 3, 4, 5]
    assert sem["orfas"]["handoff_dev"] == [1, 2, 3, 4, 5]


def test_mutante_apagar_bloco_13_com_marcas_fora_do_bloco():
    """exp01ef1b: a spec cita D0-1 e D0-7 fora do bloco 13 («Resolvido em [D0-7]» nas células). Essas marcas ficam
    quando o bloco se perde e não podem contar como definição, senão D0-1 e D0-7 somem dos órfãos."""
    state = _estado("exp01ef1b")
    real = pg.d0_a_jusante(state)
    assert real["na_spec"] == [1, 2, 3, 4, 5, 6, 7] and real["fora_do_bloco_13"] == [1, 7] and real["orfas"] == {}
    mutante = copy.deepcopy(state)
    mutante["spec_missao"] = mutante["spec_missao"].replace(pg.bloco_13(mutante["spec_missao"]), "")
    sem = pg.d0_a_jusante(mutante)
    assert sem["na_spec"] == [] and sem["fora_do_bloco_13"] == [1, 7]
    assert sem["orfas"]["brief_oficio"] == [1]
    assert sem["orfas"]["handoff_dev"] == [1, 2, 3, 5]
    assert sem["orfas"]["prototipo_html"] == [1, 2, 3, 6]


def test_acervo_exp02ef1b_d0_citados_fora_da_spec(exp02ef1b):
    """O bloco 13 se perdeu (linhas-perdidas) e o design cita [D0-n] que a spec não tem."""
    j = pg.d0_a_jusante(exp02ef1b)
    assert j["decisoes"] == 8 and not j["bloco_13"] and j["na_spec"] == []
    assert j["orfas"]["copy_strings_revisada"] == [1, 3, 6]
    assert "one_pager" not in j["citacoes"]


def test_d0_no_anexo_do_prd_nao_conta_como_citacao():
    state = {"spec_missao": "## 13. Decisões D0\n\n[D0-1] x\n",
             "prd_final": "# PRD\n\nVer [D0-1].\n\n---\n\n# Anexo — conteúdo aprovado pelo PO\n\nCópia com [D0-9].\n"}
    j = pg.d0_a_jusante(state)
    assert j["citacoes"]["prd_final"] == {"mencoes": 1, "ids": [1]} and j["orfas"] == {}


def test_spec_de_produto_tira_os_blocos_13_e_14():
    spec = "# Spec\n\n## 12. Decisões\n\nA\n\n## 13. Decisões D0\n\nB [D0-1]\n\n## 14. Ambiente\n\nC\n\n## Glossário\n\nD\n"
    assert pg.spec_de_produto(spec) == "# Spec\n\n## 12. Decisões\n\nA\n\n## Glossário\n\nD\n"
    assert pg.bloco_13(spec).startswith("## 13.")


# --------------------------------------------------------------------------- spec do Gate 0 ausente
_SPEC_SEM_GATE0 = ("# Spec\n\n## 6. Regras\n\nTeto de 35 palavras. [PARÂMETRO — produto: duração do podcast]\n\n"
                   "## 13. Decisões D0\n\n[D0-1] Animação de 400 ms; balão de 90 s.\n\n## Glossário\n\nX\n")


def test_sem_spec_gate0_a_spec_de_produto_faz_as_vezes():
    """Sessão antiga ou parada em produto: sem `spec_missao_gate0`, a régua contava 0 [PARÂMETRO] no Gate 0 e dava ao
    design o que estava na spec de produto (exp03ef1b e exp01em1b-76d9af6e no acervo de 23/10/2026)."""
    state = {"spec_missao": _SPEC_SEM_GATE0, "prd_final": "35 palavras; 90 s."}
    assert pg.spec_gate0_inferida(state)
    mk = pg.marcadores(state)
    assert mk["spec_gate0_inferida"] and mk["spec_gate0"] == {"parametro": 1, "proposta": 0}
    nums = pg.sem_origem(state)["prd"]["numeros"]
    assert nums["produto"] == [{"numero": "35 palavras", "onde": ["spec_missao_gate0"]}]
    assert nums["design"] == [{"numero": "90 s", "onde": ["spec_missao (fora da spec do Gate 0)"]}]
    assert "spec do Gate 0 1 e 0 (sem `spec_missao_gate0`" in pg.relatorio(pg.avaliar(state), "x")


def test_com_spec_gate0_a_edicao_em_linha_do_design_nao_vira_produto():
    """Com a cópia do Gate 0, o que só está na `spec_missao` (bloco 13 ou edição em linha do A066/A068) é design."""
    gate0 = "# Spec\n\n## 6. Regras\n\nTeto de 30 palavras.\n"
    state = {"spec_missao_gate0": gate0, "spec_missao": _SPEC_SEM_GATE0, "prd_final": "30 palavras; 35 palavras."}
    assert not pg.spec_gate0_inferida(state) and not pg.marcadores(state)["spec_gate0_inferida"]
    nums = pg.sem_origem(state)["prd"]["numeros"]
    assert [i["numero"] for i in nums["produto"]] == ["30 palavras"]
    assert nums["design"] == [{"numero": "35 palavras", "onde": ["spec_missao (fora da spec do Gate 0)"]}]


def test_acervo_spec_gate0_inferida():
    estados = [(m, ACERVO / m / "estado.json") for m in ("exp03ef1b", "exp01em1b-76d9af6e", "exp06ef1b")]
    q = pg.quadro(pg.avaliar_arquivos(estados))
    # a 76d9af6e do acervo chegou ao design (23/10/2026): a spec do Gate 0 é a cópia, não a inferida
    assert q["spec_gate0_inferida"] == ["exp03ef1b"]
    assert q["spec_gate0"]["exp03ef1b"] == {"parametro": 0, "proposta": 3}
    assert q["spec_gate0"]["exp01em1b-76d9af6e"] == {"parametro": 4, "proposta": 5}


# --------------------------------------------------------------------------- quadro e integração
def test_quadro_do_acervo_sem_conflito_nem_d0_no_one_pager():
    estados = [(m, ACERVO / m / "estado.json") for m in ("exp06ef1b", "exp02ef1b-4fd72a9a", "exp03em1b-b2e7b4a3")]
    q = pg.quadro(pg.avaliar_arquivos(estados))
    assert q["d0_total"] == 22 and q["d0_respec"] == 0
    assert q["d0_cores"] == {"verde": 19, "amarelo": 3}
    assert q["bloco_13_na_spec"] == "2 de 3"
    assert q["conflito_documentos"] == 0 and q["d0_no_one_pager"] == 0
    assert q["parametro_one_pager"] == {"exp02ef1b-4fd72a9a": 4}
    # os dois casos reais do plano: o teto homologado que sumiu e a H1 do §17 reescrita no corpo do PRD
    assert q["contrato_trocado_ou_ausente_no_prd"] == {"exp06ef1b": ["§15 35 palavras ausente"],
                                                       "exp02ef1b-4fd72a9a": ["§17 30% trocado (25%)"]}


def test_regressao_gates_propagacao_nao_reprova(monkeypatch, capsys):
    from scripts import regressao_gates

    # main() grava BASE_PLATAFORMA_DIR quando falta, e o valor ficava no processo para os testes seguintes. Com o
    # setenv, o monkeypatch devolve o estado original no fim (o delenv de variável ausente não registra o que desfazer)
    monkeypatch.setenv("BASE_PLATAFORMA_DIR", str(RAIZ / "fixtures" / "base-plataforma"))
    monkeypatch.setattr(sys, "argv", ["regressao_gates.py", "--propagacao", "exp07ef1b"])
    assert regressao_gates.main() == 0
    saida = capsys.readouterr().out
    assert "# Propagação — exp07ef1b" in saida and "# Quadro da propagação" in saida


def test_numeros_em_latex():
    """O redator escreve número em LaTeX («$\\ge 80\\%$ das duplas», «$\\le 15$ palavras», PRD e handoff da exp02ef1b):
    `numeros()` tirava só `$` e `\\le`, e a porcentagem com `\\%` não era número (revisão do PR #77, 24/10/2026)."""
    assert pg.numeros("$\\ge 80\\%$ das duplas") == [("80", "%")]
    assert pg.numeros("Teto estrito de $\\leq 15$ palavras") == [("15", "palavras")]
    assert pg.numeros("entre $10\\%$ e $20\\%$ da foto") == [("10", "%"), ("20", "%")]
    assert pg.tem_numero("o limiar é $\\ge 80\\%$", ("80", "%"))
    assert pg.sem_latex("$\\left( x \\right)$ e $\\ge 5$") == "\\left( x \\right) e ≥ 5"
