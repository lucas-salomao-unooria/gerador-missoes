"""O índice de missões conhece a grade publicada da plataforma, e o V5 não compara uma missão com versões dela mesma.

08/10/2026: o índice tinha 7 missões, todas geradas pela esteira; as 9 publicadas no hub — 4 delas nascidas fora do
gerador — não entravam na verificação de semelhança. E o V5 comparava a missão com outras versões do mesmo slug
(a exp03ef1b tem 7 tentativas no bucket), o que reprovaria a regeração de uma missão por "repetir a si mesma".
"""
from tools import catalogo as cat

CATALOGO_TS = '''
export const MISSAO_JURI_ESTADUAL: Missao = {
  anoSlug: "6-ano",
  unidadeSlug: "unidade-1",
  unidade: 1,
  expId: "exp06ef1b",
  titulo: "O Júri Estadual de Projetos",
  resumo:
    "O estudante é jurado de uma mostra " +
    "e descobre que o feed escondeu projetos.",
  status: "disponivel",
  estudante: {
    titulo: "O Júri Estadual",
    chamada: "Entre na mostra.",
  },
  ficha: {
    competencia: "Letramento digital — perceber que o feed se ajusta.",
    formato: "Uma missão",
  },
};

export const MISSAO_ARQUIVADA: Missao = {
  anoSlug: "4-ano",
  unidade: 1,
  expId: "backup-exp04ef1b",
  titulo: "UnooTube",
  resumo: "Arquivada.",
  status: "disponivel",
};

export const MISSAO_UNOOGPT: Missao = {
  anoSlug: "2-serie",
  unidade: 1,
  expId: "exp02em1b",
  titulo: "UnooriaAI",
  resumo: "Decidir com dados.",
  status: "disponivel",
  estudante: { titulo: "UnooriaAI", chamada: "x" },
  ficha: { competencia: "Letramento de dados." },
};

const MISSOES_PUBLICADAS: Record<string, Missao[]> = {
  "6-ano": [MISSAO_JURI_ESTADUAL],
  "2-serie": [MISSAO_UNOOGPT],
};
'''


def test_fichas_da_grade_publicada():
    fichas = {f["slug"]: f for f in cat.fichas_da_plataforma(CATALOGO_TS)}
    assert set(fichas) == {"exp06ef1b", "exp02em1b"}, "só as de MISSOES_PUBLICADAS; a arquivada fica de fora"
    juri = fichas["exp06ef1b"]
    assert juri["ano"] == "6º EF" and juri["bimestre"] == "1º bimestre" and juri["status"] == "em produção"
    assert juri["descoberta"] == "O estudante é jurado de uma mostra e descobre que o feed escondeu projetos."
    assert juri["eixo"].startswith("Letramento digital") and juri["origem"] == cat.ORIGEM_PLATAFORMA
    assert juri["ambiente"] == "", "título que não é seção do DS não vira ambiente"
    assert fichas["exp02em1b"]["ambiente"] == "unooriaai" and fichas["exp02em1b"]["ano"] == "2ª EM"


def test_ambiente_sai_do_codigo_da_experiencia():
    assert cat.ambiente_da_fonte("@edu/ui/ds\n@unooria/design-system/fonts\nds-unoovista\n@edu/ui/ds") == "unoovista"
    assert cat.ambiente_da_fonte("ds-insta\nds-insta\nds-reflexao") == "instanooria"
    assert cat.ambiente_da_fonte("@unooria/design-system/unooria\n@unooria/design-system/whatsappmobile") == "whatsappmobile"
    assert cat.ambiente_da_fonte("nada aqui") == ""


def test_v5_nao_compara_a_missao_com_versoes_dela_mesma():
    publicada = {"sessao": "plataforma:exp06ef1b", "slug": "exp06ef1b", "ano": "6º EF", "ambiente": "unoovista",
                 "eixo": "Letramento digital", "descoberta": "o feed escondeu projetos", "status": "em produção"}
    outra = {**publicada, "sessao": "plataforma:exp06ef2b", "slug": "exp06ef2b", "descoberta": "o boato voa"}
    indice = {"missoes": [publicada, outra]}
    nova_versao = {"sessao": "s1", "slug": "exp06ef1b", "ano": "6º EF", "ambiente": "unoovista",
                   "eixo": "Letramento digital", "descoberta": "o feed esconde o resto da mostra"}
    assert [m["slug"] for m in cat.vizinhas(nova_versao, indice)] == ["exp06ef2b"]


def test_ficha_da_plataforma_tem_o_que_o_v5_compara():
    """Sem tipo de decisão a ficha «não sustenta reprovação» no V5: a chamada do estudante diz o que ele faz."""
    juri = next(f for f in cat.fichas_da_plataforma(CATALOGO_TS) if f["slug"] == "exp06ef1b")
    assert juri["tipo_decisao"] == "Entre na mostra."
    assert not cat.tem_lacuna({**juri, "ambiente": "unoovista"})


def test_ambiente_da_spec_aceita_colecao_conhecida_que_a_base_ainda_nao_publica():
    assert cat._ambiente_da_spec("- `secao_ds: unoogaleria`") == "unoogaleria"
    assert cat._ambiente_da_spec("- `secao_ds: inventada`") == ""
