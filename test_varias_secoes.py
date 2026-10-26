"""Missão em mais de uma seção do DS: principal + extras, mapa, transições e teto por ano (decisão do PO, 15/10/2026)."""
from tools import secoes as sec

VOCAB = {"unoochat": "ds-unoochat", "unoovista": "ds-unoovista", "unoojornal": None, "unooriaai": "ds-unooriaai",
         "instanooria": "ds-instanooria", "unooria": "ds-unooria"}

MAPA = ("| Etapa | Tela/momento | Seção do DS | O que esta seção permite medir ou mostrar |\n|---|---|---|---|\n"
        "| Desafiar | E1-ALU-01 | `unoovista` | o feed |\n| Decidir | E3-ALU-01 | `unoochat` | encaminhar ao grupo |\n")
TRANSICOES = ("| De | Para | Gatilho na história (notificação, link, compartilhar) | Etapa |\n|---|---|---|---|\n"
              "| `unoovista` | `unoochat` | o estudante toca em compartilhar no post | Decidir |\n")


def _spec(extras="[unoochat]", serie="7EF", mapa=MAPA, transicoes=TRANSICOES):
    return (f"## 0. Ficha\n- `id: exp0{serie[0]}ef1b`\n- `series: [\"{serie}\"]`\n- `secao_ds: unoovista`\n"
            f"- `secoes_ds_extras: {extras}`\n## 14. Ambiente\n{mapa}\n{transicoes}")


def _codigos(texto, **kw):
    return sorted(a["codigo"] for a in sec.validar(texto, "unoovista", "a spec", vocabulario=VOCAB, **kw))


def test_sem_extras_nada_a_conferir():
    assert sec.extras("- `secoes_ds_extras: []`") == [] and sec.extras("- `secoes_ds_extras: nenhuma`") == []
    assert _codigos(_spec(extras="[]")) == []


def test_extras_completas_dentro_do_teto_passam():
    assert sec.extras(_spec()) == ["unoochat"]
    assert _codigos(_spec()) == []


def test_teto_por_ano():
    assert (sec.teto("2EF"), sec.teto("3EF"), sec.teto("4EF"), sec.teto("5EF"), sec.teto("6EF"), sec.teto("2EM")) == (1, 1, 2, 2, 3, 3)
    assert _codigos(_spec(serie="2EF")) == ["secoes-acima-do-teto"]
    assert _codigos(_spec(serie="4EF")) == []
    tres = _spec(extras="[unoochat, unoojornal]", serie="4EF",
                 mapa=MAPA + "| Explicar | E5-ALU-01 | `unoojornal` | a notícia |\n",
                 transicoes=TRANSICOES + "| `unoochat` | `unoojornal` | o link no grupo | Explicar |\n")
    assert _codigos(tres) == ["secoes-acima-do-teto"]
    assert _codigos(tres.replace("4EF", "7EF").replace("exp04", "exp07")) == []


def test_a_plataforma_nao_conta_no_teto():
    assert _codigos(_spec(extras="[unooria]", serie="2EF")) == []


def test_extra_sem_mapa_sem_transicao_ou_sem_gatilho():
    assert _codigos(_spec(mapa="")) == ["secao-extra-sem-mapa"]
    assert _codigos(_spec(transicoes="")) == ["secao-extra-sem-transicao"]
    sem_gatilho = TRANSICOES.replace("o estudante toca em compartilhar no post", "—")
    assert _codigos(_spec(transicoes=sem_gatilho)) == ["transicao-sem-gatilho"]


def test_extra_fora_do_vocabulario_ou_legada():
    assert "secao-extra-desconhecida" in _codigos(_spec(extras="[whatsapp2]"))
    assert "secao-extra-legada" in _codigos(_spec(extras="[instanooria]"))


def test_briefing_que_proibe_outras_secoes_vence():
    briefing = "secao_ds: unoovista. É PROIBIDO usar qualquer outro design system."
    assert "briefing-proibe-outras-secoes" in _codigos(_spec(), briefing=briefing)


def test_spec_e_one_pager_conferem_as_extras_nos_gates():
    from tools.contrato_produto import validar_one_pager
    from tools.rastro import validar_manifesto

    r = validar_manifesto(_spec(serie="2EF"))
    assert any(a["campo"] == "secoes_ds_extras" and "teto" in a["resumo"] for a in r["achados"])
    assert r["campos"]["secoes_ds_extras"] == ["unoochat"]
    op = ("# One-pager — exp02ef1b\n**Seção do DS:** `unoovista` · **Seções extras do DS:** `unoochat`\n"
          "## 5. Ambiente\n" + MAPA + "\n" + TRANSICOES)
    codigos = {a["codigo"] for a in validar_one_pager(op)["achados"]}
    assert "secoes-acima-do-teto" in codigos


def test_componente_e_conferido_contra_a_secao_da_tela(monkeypatch):
    from tools import componentes_ds

    marcas = {"unoovista": {"PostCard", "TabBar"}, "unoochat": {"MessageBubble", "TabBar"}, "unooria": {"Button"}}
    monkeypatch.setattr(componentes_ds, "carregar", lambda: (marcas, {}, "teste"))
    spec = "- `secao_ds: unoovista`\n- `secoes_ds_extras: [unoochat]`\n"
    por_tela = ("| ID tela | Seção do DS | Frame (screenId) | Componentes do DS |\n|---|---|---|---|\n"
                "| E1-ALU-01 | `unoovista` | f1 | PostCard, TabBar |\n"
                "| E3-ALU-01 | `unoochat` | f2 | MessageBubble |\n"
                "| E4-ALU-01 | `unoovista` | f3 | MessageBubble |\n")
    achados = componentes_ds.validar(por_tela, spec)
    assert len(achados) == 1 and "MessageBubble" in achados[0]["resumo"] and "unoovista" in achados[0]["resumo"]
    # sem a coluna de seção, vale a união da principal com as extras
    sem_coluna = "| ID tela | Componentes do DS |\n|---|---|\n| E3-ALU-01 | MessageBubble, PostCard |\n"
    assert componentes_ds.validar(sem_coluna, spec) == []
    assert componentes_ds.validar(sem_coluna, "- `secao_ds: unoovista`\n")[0]["severidade"] == "bloqueio"


def test_catalogo_compara_conjuntos_de_secoes():
    from tools import catalogo as cat

    a = {"ambiente": "unoovista", "ambientes_extras": ["unoochat"]}
    assert cat.mesmo_ambiente(a, {"ambiente": "unoochat"}) and cat.mesmo_ambiente({"ambiente": "unoochat"}, a)
    assert not cat.mesmo_ambiente(a, {"ambiente": "unooriaai"})
    assert not cat.mesmo_ambiente({"ambiente": ""}, {"ambiente": ""})


def test_rastreabilidade_cobra_a_secao_extra_ate_o_prd():
    from tools import rastreabilidade as rb

    reqs = rb.requisitos({"one_pager": "**Seção do DS:** `unoovista` · **Seções extras do DS:** `unoochat`\n",
                          "spec_missao": "", "jornada_telas": ""})
    assert ("secao_extra", "unoochat") in {(r["categoria"], r["texto"]) for r in reqs}
    assert rb._presente("secao_extra", "unoochat", "prd", "secoes_ds_extras: [unoochat]")


# o app de cada etapa, como o §5 do one-pager aprovou (exp02em1b, sessão 19a39981, 25/10/2026)
ONE_PAGER_SECOES = (
    "## 5. Verificação de ambiente\n\n### Verificação por etapa\n\n"
    "| Etapa | Seção do DS | Dentro do ambiente? | Escape permitido? | Affordance nativa usada |\n|---|---|---|---|---|\n"
    "| 1. Desafiar | unooriaai | Sim | Não | PromptSuggestion |\n"
    "| 3. Decidir | unooriaai → unoovista | Sim (modal de exportação) | Não | Publicar no Unoovista |\n"
    "| 4. Resultado/Aha | unoovista | Sim | Não | FeedScroll |\n"
    "| 5. Explicar | unoovista | Sim (painel analítico de bastidores/insights da postagem) | Não | Indicadores |\n"
    "| 6. Refletir | unoovista | Sim | Não | Campo de texto |\n\n"
    "### Transições\n\n| De | Para | Gatilho na história (notificação, link, compartilhar) | Etapa |\n|---|---|---|---|\n"
    "| unooriaai | unoovista | Publicar no Unoovista | Decidir → Resultado/Aha |\n")


def _spec_secoes(explicar="unooriaai", refletir="unooriaai", volta=True):
    return (
        "### Mapa de seções\n| Etapa | Tela/momento | Seção do DS | Papel na experiência |\n|---|---|---|---|\n"
        "| 1. Desafiar | Briefing | unooriaai | Chat |\n| 3. Decidir | Modal | unooriaai | Envio |\n"
        "| 4. Resultado / Aha | Feed noturno | unoovista | Feed |\n"
        f"| 5. Explicar | Painel analítico de bastidores | {explicar} | Dados |\n"
        f"| 6. Refletir | Diário de bordo | {refletir} | Reflexão |\n\n"
        "### Transições\n| De | Para | Gatilho na história | Etapa |\n|---|---|---|---|\n"
        "| unooriaai | unoovista | Link nativo ao clicar em \"Publicar no Unoovista\" | 3 |\n"
        + ("| unoovista | unooriaai | Notificação nativa do grêmio para análise | 4 |\n" if volta else ""))


def test_spec_que_troca_o_app_de_uma_etapa_bloqueia_em_produto():
    from tools import conteudo_aprovado as ca

    achados = {a["codigo"]: a for a in ca.validar_spec(_spec_secoes(), ONE_PAGER_SECOES)["achados"]}
    trocada = achados["secao-trocada"]
    assert trocada["severidade"] == "bloqueio" and trocada["etapa"] == "produto"
    assert "Explicar" in trocada["resumo"] and "Refletir" in trocada["resumo"]
    assert achados["transicao-acrescentada"]["severidade"] == "atencao"
    assert "`unoovista` → `unooriaai`" in achados["transicao-acrescentada"]["resumo"]


def test_spec_fiel_ao_mapa_do_one_pager_passa():
    from tools import conteudo_aprovado as ca

    fiel = _spec_secoes(explicar="unoovista", refletir="unoovista", volta=False)
    assert ca._secoes(fiel, ONE_PAGER_SECOES) == []
    # tela da plataforma numa etapa não troca o app aprovado; célula deixada ao PO é pendência, não troca
    assert ca._secoes(_spec_secoes(explicar="unoovista + unooria", refletir="`unoovista` (extra)", volta=False),
                      ONE_PAGER_SECOES) == []
    assert ca._secoes(_spec_secoes(explicar="unooriaai [ABERTO — dono: produto: insights no app?]",
                                   refletir="unoovista", volta=False), ONE_PAGER_SECOES) == []
    # one-pager sem mapa: nada a comparar
    assert ca._secoes(_spec_secoes(), "## 5. Ambiente\nUma seção só.") == []


def test_passagens_aprovadas_pelo_mapa_e_pelas_transicoes():
    assert sec.secoes_da_celula("unooriaai → unoovista") == ["unooriaai", "unoovista"]
    assert sec.secoes_da_celula("`unoovista` (painel analítico de bastidores/insights)") == ["unoovista"]
    assert sec.secoes_da_celula("a definir com o PO") == []
    assert sec.passagens_aprovadas(ONE_PAGER_SECOES) == {("unooriaai", "unoovista")}
