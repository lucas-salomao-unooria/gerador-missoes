"""Testes unitários da leva consolidada de correções E2E (Pacotes E2E-2 e E2E-3 + Decisões 1 a 4)."""
from __future__ import annotations

from tools import (
    afirmacoes,
    comite,
    conferir_prd_plataforma,
    consistencia,
    conteudo_aprovado,
    decisoes,
    diagnostico,
    explicacoes,
    fechar_contrato,
    kpis,
    montagem,
    prd_codavel,
    rastreabilidade,
    rastro,
    textos_chave,
)


def test_g03_variantes_quase_iguais_no_one_pager():
    """G03 + Decisão 2: variantes quase iguais na mesma etapa não acusam divergência e entram no de acordo."""
    one_pager = """
## 4. Mecânica e fluxo
### Etapa 2 — Navegar
A tela mostra: "Post 4 — Você viu o escândalo na escola? Clique aqui urgente antes que apaguem!"
Logo abaixo: "Post 4 — Você viu o escândalo na escola? Clique aqui urgente antes que apaguem tudo!"
"""
    tcs = textos_chave.numerar(textos_chave.extrair(one_pager))[0]
    pares = textos_chave.variantes_de_texto_chave(tcs)
    assert len(pares) == 1
    copy = (
        "| ID da string | PT-BR | Palavras | Notas |\n"
        "|---|---|---|---|\n"
        '| `e2.post4` | Post 4 — Você viu o escândalo na escola? Clique aqui urgente antes que apaguem! | 14 | |\n'
    )
    res = textos_chave.conferir_copy(copy, tcs)
    assert not [a for a in res["achados"] if a["codigo"] == "texto-chave-divergente"]
    itens = fechar_contrato.variantes_do_one_pager({"one_pager": one_pager, "spec_missao": ""})
    assert len(itens) == 1
    assert "qual vale?" in itens[0].assunto


def test_g04_hipotese_sem_classificador_fica_atencao():
    """G04: quando o classificador não pôde rodar (modo determinístico), hipótese sem número fica 🟡."""
    one_pager = "## 17. Hipóteses\n- **H1:** A turma prefere explorar com calma antes de responder.\n"
    prd = "## 17. Hipóteses\n- **H1:** A turma prefere explorar por 45s antes de responder.\n"
    res = montagem.validar_prd({"one_pager": one_pager, "prd_final": prd})
    achados_h1 = [a for a in res["achados"] if a["codigo"] == "hipotese-a-conferir"]
    assert achados_h1 and all(a["severidade"] == "atencao" for a in achados_h1)


def test_g05_g23_explicacoes_traduz_codigos_novos():
    """G05 e G23: códigos novos têm tradução amigável em `tools/explicacoes.py`."""
    for cod in (
        "rota-gestor-com-dado-nominal",
        "regra-sem-ramo-residual",
        "evento-operacional-sem-coluna",
        "arquivo-inexistente-no-glossario",
    ):
        assert cod in explicacoes.CATALOGO


def test_g06_consistencia_arquivo_inexistente_no_glossario_da_spec():
    """G06: caminho de artefato inexistente na esteira declarado no glossário da spec acusa a spec e não os documentos a jusante."""
    spec = (
        "## Glossário canônico\n"
        "| Artefato | Arquivo |\n|---|---|\n"
        "| Protótipo | `design/08-prototipo-inexistente.html` |\n"
    )
    res_spec = consistencia.validar(spec, {"spec": spec})
    assert any(a["codigo"] == "arquivo-inexistente-no-glossario" for a in res_spec["achados"])
    res_jusante = consistencia.validar(spec, {"PRD": "O arquivo `design/08-prototipo.html` é gerado."})
    assert not [a for a in res_jusante["achados"] if a["codigo"] == "arquivo-divergente"]


def test_g08_comite_no_teto_rebaixa_achados_para_atencao():
    """G08: quando o comitê atinge o teto de rodadas (status amarelo), achados bloqueantes viram ressalva (atencao)."""
    doc = "Texto literal que existe no documento da missão para validar a citação do juiz."
    rel = (
        "**Veredito: 🔴 REPROVADO**\n"
        '```json\n'
        '{"voto": "reprova", "achados": [{"id": "J1", "severidade": "bloqueio", '
        '"trecho_citado": "Texto literal que existe no documento da missão", '
        '"resumo": "Ressalva pedagógica"}]}\n'
        '```\n'
    )
    res = comite.consolidar({"juiz_1": rel}, documentos=doc, rodada=5, max_rodadas=5)
    assert res["status"] == "amarelo"
    assert all(a["severidade"] == "atencao" for a in res["achados"])


def test_g10_rastreabilidade_reconhece_intervalo_pq_e_colunas_veredito():
    """G10: intervalo `PQ-01 a PQ-04` na §19.2 é reconhecido e `colunas_veredito` filtra achados de etapas anteriores."""
    spec = "Hipótese: `[PROPOSTA — validar com PO: PQ-02 · meta de 80% na conclusão]`.\n"
    prd = (
        "## 19. Decisões abertas, parâmetros e pendências\n"
        "### 19.2 Propostas de produto\n"
        "- `PQ-01 a PQ-04`: metas mantidas em `PROPOSTA — validar com PO` (`PEND-02`).\n"
    )
    res = rastreabilidade.matriz(
        {"spec_missao": spec, "handoff_dev": "PQ-02", "schema_sql": "PQ-02", "prd_final": prd},
        colunas_veredito=("handoff", "banco", "prd"),
    )
    assert res["status"] == "aprovado"
    assert not [a for a in res["achados"] if a["codigo"] == "proposta-sumiu-no-prd"]


def test_g11_montagem_orienta_marcador_proposta_em_meta_diverge_9f():
    """G11: `meta-diverge-9f` orienta manter `[PROPOSTA — validar com PO: meta <valor> · por quê]` na célula."""
    spec = "### 9f. Perguntas de produto\n| PQ | Pergunta | Corte |\n|---|---|---|\n| PQ-01 | Conclusão? | ≥ 80% |\n"
    prd = "## 2. Objetivos e KPIs\n| KPI | PQ | Alvo |\n|---|---|---|\n| KPI-01 | PQ-01 | ≥ 90% |\n"
    res = montagem.validar_prd({"spec_missao": spec, "prd_final": prd})
    div = [a for a in res["achados"] if a["codigo"] == "meta-diverge-9f"]
    assert div and "[PROPOSTA — validar com PO:" in div[0]["resumo"]


def test_g12_prd_codavel_chaves_jsonb_e_regra_sem_ramo_residual():
    """G12: `_ficha` confere chaves JSONB nas §§11/12 e alerta (`atencao`) quando regra tem 2+ ramos sem ramo residual."""
    prd = """
## 11. Modelo de dados
```sql
CREATE TABLE exp01_sessoes (
    id UUID PRIMARY KEY,
    respostas JSONB NOT NULL -- {"escolha_final": "A"}
);
```
## 12. Contratos de API
POST `/api/missoes/exp01/salvar` recebe `escolha_final`.
## 14. Avaliação e evidências
| Habilidade | Marcador | Tipo | Pergunta | Regra |
|---|---|---|---|---|
| EF05CO01 | `escolha_final` | `acao` | — | `(respostas->>'escolha_final') = 'A' → atingiu; (respostas->>'escolha_final') = 'B' → em_processo` |
"""
    achados: list = []
    prd_codavel._ficha(prd, "", achados)
    assert any(a["codigo"] == "regra-sem-ramo-residual" and a["severidade"] == "atencao" for a in achados)
    assert not [a for a in achados if a["codigo"] == "regra-chave-jsonb-ausente"]


def test_g14_conteudo_aprovado_limpa_prefixos_de_alternativa_e_regua():
    """G14: `_literal_confere` ignora prefixos `*Alt 1:*`/`1.` e sufixos `[Atingiu]` extraídos junto do literal."""
    assert conteudo_aprovado._literal_confere("*Alt 1:* A sombra torta na parede [Atingiu]", "a sombra torta na parede")
    assert conteudo_aprovado._literal_confere("1. A cor bonita do quadro [Não atingiu]", "a cor bonita do quadro")


def test_g15_decisoes_1_3_4_metas_tecnicas_e_numeros_no_prd():
    """G15 + Decisões 1, 3 e 4: metas técnicas (60 FPS) viram plataforma; número técnico no PRD vira 🟡; PEND na §19 não acusa."""
    assert montagem.de_plataforma("Manter 60 FPS estável durante a transição")
    assert montagem.de_plataforma("Taxa de falhas técnicas <= 1% das sessões")
    spec = "Tempo de aviso: `[PARÂMETRO — a definir por produto: tempo de aviso · sugestão: 45 segundos]`.\n"
    prd_com_pend = (
        "Usar constante configurável de 45 segundos (`PEND-01`).\n"
        "## 19. Pendências\n"
        "| ID | Tipo | Descrição |\n|---|---|---|\n"
        "| PEND-01 | `[PARÂMETRO — a definir por produto: tempo de aviso · sugestão: 45 segundos]` | 45 segundos |\n"
    )
    estado = {"spec_missao": spec, "prd_final": prd_com_pend}
    assert "45 segundos" in montagem._sugestoes_de_parametros_abertos_com_pend(estado)
    res = montagem.validar_prd(estado)
    assert not [a for a in res["achados"] if a["codigo"] == "numero-sem-origem"]


def test_g16_decisoes_d0_preservando_marcador_nao_bloqueia():
    """G16: quando a decisão do D0 mantém o marcador `[PARÂMETRO]`/`[PROPOSTA]`/`[ABERTO — dono: PO]`, não acusa fechamento."""
    spec_g0 = "Tempo: `[PARÂMETRO — a definir por produto: tempo limite · sugestão: 45 s]`.\n"
    fechamento = (
        "[D0-1] 2.tempo\n"
        "Decisão: Manter `[PARÂMETRO — a definir por produto: tempo limite · sugestão: 45 s]` aberto para o PO.\n"
        "Base: spec\nReversível: sim\n"
    )
    sem_par, _ = decisoes.decisoes_d0_de_produto(fechamento, {"decisoes": [{"id": "D0-1", "campo": "2.tempo", "classe": "estado", "cor": "amarelo"}]}, spec_g0)
    assert sem_par == []


def test_g17_fechar_contrato_pergunta_secao_ds_sem_trava_no_briefing():
    """G17: quando o briefing não trava `secao_ds` e a spec escolhe seção padrão sem o PO ter fixado, pergunta no de acordo."""
    estado = {
        "briefing": "Missão para o 6º ano sobre checagem de boatos.",
        "one_pager": "## 1. Visão\nChecagem de boatos.\n",
        "spec_missao": "## 0. Identidade\n- `secao_ds`: `unoochat`\n- `classe_ambiente`: `padrao`\n",
    }
    itens = fechar_contrato.escolhas_de_ambiente(estado)
    assert len(itens) == 1
    assert "unoochat" in itens[0].assunto


def test_g21_conferir_prd_plataforma_ignora_offline_de_ia():
    """G21: «processamento offline de IA» não acusa `capacidade-inexistente` de operação offline."""
    prd = "## 8. Requisitos\n- RF-01: O lote usa processamento offline de IA no servidor antes da aula."
    achados = conferir_prd_plataforma.conferir_capacidades(prd)
    assert not [a for a in achados if a["codigo"] == "capacidade-inexistente"]


def test_g24_diagnostico_anota_tratado_no_prd_quando_identificadores_presentes():
    """G24: quando `dev_status` traz achado cujos identificadores entre crases já estão em `prd_final`, anota `[tratado no PRD — conferir]`."""
    estado = {
        "prd_final": "A tabela `exp01_sessoes` possui a coluna `escolha_final`.",
        "dev_status": "bloqueado",
        "dev_status_envelope": {
            "status": "bloqueado",
            "achados": [
                {
                    "codigo": "coluna-ausente",
                    "severidade": "bloqueio",
                    "etapa": "dev",
                    "resumo": "Falta declarar `exp01_sessoes` e `escolha_final`.",
                }
            ],
        },
    }
    res = diagnostico.coletar(estado)
    achados_dev = [a for a in res["achados"] if a.get("codigo") == "coluna-ausente"]
    assert achados_dev and "[tratado no PRD — conferir]" in achados_dev[0]["resumo"]


def test_g25_afirmacoes_parcial_do_prototipo_nao_acusa_inventario():
    """G25: «8 de 9 telas renderizam no protótipo» confere o protótipo e não acusa `afirmacao-inventario`."""
    jornada = "| ID |\n|---|\n" + "\n".join(f"| `E1-ALU-0{i}` |" for i in range(1, 10))
    proto = "\n".join(f'<section data-screen-id="E1-ALU-0{i}"></section>' for i in range(1, 9))
    qa = "No teste visual, 8 de 9 telas renderizam sem corte no protótipo."
    res = afirmacoes.conferir_qa(qa, jornada=jornada, prototipo_html=proto)
    assert not [a for a in res["achados"] if a["codigo"] == "afirmacao-inventario"]


def test_decisao2_literais_parafraseados_respeita_variantes_aprovadas():
    """Decisão 2: duas variantes quase iguais da mesma etapa no one-pager não se acusam como paráfrase em `literais_parafraseados` nem `textos_chave_reescritos`."""
    one_pager = (
        "## 4. Jornada\n"
        "- **Etapa 2 — Navegar:** O aluno recebe a instrução \"Marque no pátio o que ficou fora da sua foto.\"\n"
        "- Na variante da biblioteca, lê \"Marque na biblioteca o que ficou fora da sua foto.\"\n"
    )
    prd = "Na tela E2-ALU-01 exibimos o enunciado \"Marque na biblioteca o que ficou fora da sua foto.\"."
    assert conteudo_aprovado.literais_parafraseados(prd, one_pager) == []
    assert montagem.textos_chave_reescritos(prd, one_pager) == []


def test_mecanica_arquetipos_e_anti_frankenstein_nos_prompts():
    """Prompts de ideação, núcleo, juízes e seções de apoio carregam os arquétipos interativos, a regra do Core Loop único e a cláusula residual enxuta."""
    from prompts import load_prompt

    p002 = load_prompt("produto/002_mapa_conceitual.md")
    p003 = load_prompt("produto/003_ideacao_mecanismos.md")
    p004 = load_prompt("produto/004_nucleo_narrativo.md")
    p007 = load_prompt("produto/007_micro_gate.md")
    p008 = load_prompt("produto/008_juiz_profundidade.md")
    p014 = load_prompt("produto/014_secoes_apoio.md")
    p029b = load_prompt("produto/029b_experiencia_estudante.md")
    p_canal_a = load_prompt("produto/comite_canal_a_medida.md")

    assert "Ancoragem vivencial da idade" in p002
    assert "6 Arquétipos Criativos Nativos do Design System" in p003
    assert "Brinquedo Epistêmico" in p003
    assert "1 Core Loop = 1 Objeto Interativo Central em 3 Voltas" in p004
    assert "Proibido Efeito Frankenstein" in p007
    assert "Efeito Frankenstein" in p008
    assert "complementar lógico de Atingiu e Em processo" in p014
    assert "anti-Frankenstein" in p029b
    assert "complementar lógico de Atingiu e Em processo" in p_canal_a


def test_3ef2b_falsos_positivos_deterministicos():
    """Garante que os 5 falsos positivos revelados na execução E2E de 3ef2b não ocorrem."""
    # 1. [ABERTO — dono: humano: ...] é reconhecido como decisão humana (🟡), não produto (🔴)
    rastro._REGRAS_DONOS_CACHE = None
    assert rastro._etapa_por_tokens("humano: pedagógico") == "humano"

    # 2. Habilidades explicitamente marcadas como fora da missão ou não reivindicadas não entram em codigos_aprovados
    op = (
        "## 12. Evidência\n### 12a. Contrato de evidência\n"
        "| Habilidade | Canal |\n|---|---|\n"
        "| EF03CO07 | **A + B** |\n"
        "| EF03CO03 (fora da missão) | **A** (não exercido em tela) |\n"
        "| EF03CO01 (não reivindicada) | — |\n"
    )
    assert conteudo_aprovado.codigos_aprovados(op) == ["EF03CO07"]

    # 3. Tempo aproximado no one-pager (≈ 47 min) aceita decimal que arredonda para 47 na spec (46,9 min ou | 46,9 | minutos)
    assert rastreabilidade._presente("tempo", "47", "spec", "| **Total Acumulado** | **46,9 min** |")
    assert rastreabilidade._presente("tempo", "47", "spec", "| Duração total em tela | 46,9 | minutos |")

    # 4. Tabela de tickets resolvidos do QA citando 'arquivo-inexistente' — citação de 'design/00-relatorio-d0.md'
    qa_rel = "| **QA-A1** ('arquivo-inexistente' — citação de 'design/00-relatorio-d0.md') | **Resolvido** |"
    res_qa = afirmacoes.conferir_qa(qa_rel)
    assert res_qa["achados"] == []

    # 5. Nota de histórico de correção («corrigida referência de D0-7 para D0-5») não acusa D0-7 como órfão
    st_d0 = {
        "spec_missao": "## 13. Decisões D0\n### [D0-5] Ajuste\nTexto.\n",
        "copy_strings_revisada": "| `e1.msg` | Olá [D0-5] | 2 | (corrigida referência de D0-7 para D0-5 conforme ticket) |",
    }
    assert rastro.d0_orfaos(rastro.FONTES_DESIGN, st_d0) == []


def test_usuario_produto_pode_aprovar_com_ressalva_e_sugestao_sem_dois_pontos():
    """O papel 'produto' pode liberar com exceção/ressalva em produto (com gate vermelho ou item lido sem resposta),
    e [PARÂMETRO ... sugestão 45 segundos] sem dois-pontos extrai a sugestão e oferece 'Aceitar a sugestão'."""
    from pipeline import passagem
    from tools.auth import Sessao

    estado_sem_vermelho = {
        "one_pager": "- Tempo de inatividade: `[PARÂMETRO — a definir por produto: sugestão 45 segundos]`\n",
        "spec_missao_gate0": "- Timeout de IA: `[PARÂMETRO — a definir por produto: sugestão 3 minutos]`\n",
        "gate_final_status": "🟡",
    }
    itens = fechar_contrato.itens_em_aberto(estado_sem_vermelho)
    assert len(itens) == 2
    for it in itens:
        assert fechar_contrato.ACEITAR in it.opcoes()
    assert itens[0].sugestao == "45 segundos"
    assert itens[1].sugestao == "3 minutos"

    fluxo = {"etapa": "produto", "situacao": passagem.AGUARDANDO, "versao": 1, "pareceres": []}
    acoes_po = passagem.acoes_possiveis(fluxo, "produto", estado_sem_vermelho, estrito=True)
    assert passagem.DE_ACORDO in acoes_po
    assert passagem.EXCECAO in acoes_po

    # Com item marcado como lido sem resposta, o próprio PO ('produto') consegue aprovar via EXCECAO no modo estrito
    sessao_po = Sessao(usuario="po", papel="produto", emitida_em=1.0, expira_em=9999999999.0, jti="j1")
    decisoes_lidas = {it.id: {"resposta": "", "valor": "", "lido": True} for it in itens}
    novo_fluxo, _ = passagem.aplicar(
        fluxo, passagem.EXCECAO, sessao_po,
        "Aprovado com ressalva deixando os dois parâmetros abertos para calibragem.",
        estado_sem_vermelho, decisoes=decisoes_lidas, estrito=True,
    )
    assert novo_fluxo["etapa"] == "design"
    assert novo_fluxo["situacao"] == passagem.LIBERADA

    # Com gate em 🔴, o PO ('produto') também recebe EXCECAO (com justificativa obrigatória) e vê o contrato
    estado_vermelho = dict(estado_sem_vermelho, one_pager_po_status="🔴")
    acoes_po_vermelho = passagem.acoes_possiveis(fluxo, "produto", estado_vermelho, estrito=True)
    assert passagem.EXCECAO in acoes_po_vermelho
    novo_fluxo_v, _ = passagem.aplicar(
        fluxo, passagem.EXCECAO, sessao_po,
        "Estou de acordo com o conteúdo do one-pager desta versão.",
        estado_vermelho,
        decisoes={it.id: {"resposta": fechar_contrato.ACEITAR, "valor": ""} for it in itens},
        estrito=True,
        justificativa="Aceito as duas reformulações textuais apontadas no one_pager_po_status.",
    )
    assert novo_fluxo_v["etapa"] == "design"


def test_bloco_de_governanca_nao_passa_pelo_glossario_do_prd():
    """exp01em1b (sessão a38e5b2f): o glossário lista «Admin» como variante do «Módulo de Homologação», e o bloco que a
    esteira escreve no PRD cita a conta `admin (como Produto)` — o PRD saía 🔴 por um texto que o autor não escreveu."""
    from tools import governanca

    spec = ("## Glossário canônico\n\n| Nome canônico | Variantes proibidas |\n|---|---|\n"
            "| Módulo de Homologação | \"Bancada de Testes\", \"Admin\" |\n")
    gov = {"pendencias": [{"codigo": governanca.LIBERADO_SEM_CONTA, "como": "admin (como Produto)",
                           "quando": "26/10/2026 01:18:39"}]}
    prd = "# 19. Pendências\n\n" + governanca.bloco(gov) + "\n# 20. Testes\n\nO Módulo de Homologação abre a bancada.\n"
    codigos = [a.get("codigo") for a in rastro.validar_prd(prd, spec=spec)["achados"]]
    assert "variante-proibida" not in codigos
    # o texto do autor continua conferido
    codigos = [a.get("codigo") for a in rastro.validar_prd(prd + "\nAbra o **Admin**.\n", spec=spec)["achados"]]
    assert "variante-proibida" in codigos


def test_frente_a_versionamento_e_pedidos_acumulados():
    """Frente A: pedidos acumulados do PO autorizam mudança sobre one_pager_po, spec_missao_gate0 acompanha spec_missao
    na edição pontual e brief_escopo não é sobrescrito na correção pontual."""
    from pipeline.reexecucao import CHAVES_AUTORAIS, CHAVES_PRODUTO, preparar_estado_pontual
    from tools import edicao_pontual, one_pager_po, triagem_pedido

    # 1. brief_escopo é chave autoral e travada na correção pontual de produto, e base_preservada_one_pager limpa no refazer
    assert "brief_escopo" in CHAVES_AUTORAIS
    assert "brief_escopo" in edicao_pontual.TRAVADOS_SEM_EDICAO["produto"]
    assert "base_preservada_one_pager" in CHAVES_PRODUTO

    # 2. one_pager_po aceita mudança pedida em pedidos acumulados do PO (mesmo sem estar na tabela Alterações)
    po = "# One-Pager\n\n## 4. Mecânica\n\nO estudante analisa 5 cartões de postagem na tela inicial.\n"
    gerado = "# One-Pager\n\n## 4. Mecânica\n\nO estudante analisa 3 cartões de postagem na tela inicial.\n"
    sem_pedido = one_pager_po.conferir(po, gerado)
    assert sem_pedido["status"] == "bloqueado"
    com_pedido_acumulado = one_pager_po.conferir(
        po, gerado, pedidos="Reduzir de 5 cartões de postagem para 3 cartões de postagem na tela inicial."
    )
    assert com_pedido_acumulado["status"] == "aprovado"

    # 3. preparar_estado_pontual sincroniza spec_missao_gate0 quando spec_missao é editada
    estado = {
        "spec_missao": "# Spec\n\nTempo: 15 min\n",
        "spec_missao_gate0": "# Spec\n\nTempo: 15 min\n",
    }
    ed = edicao_pontual.Edicao(documento="spec_missao", de="Tempo: 15 min", para="Tempo: 20 min", motivo="pedido PO")
    novo_estado, _ = preparar_estado_pontual(
        estado, "produto", "Mudar tempo para 20 min", {"spec_missao": "# Spec\n\nTempo: 20 min\n"},
        edicao_pontual.como_dicts([ed]),
    )
    assert "Tempo: 20 min" in novo_estado["spec_missao_gate0"]

    # 4. triagem_pedido respeita dono_llm para artefato exclusivo de design (sem achar frase literal no produto)
    divisao = triagem_pedido.dividir(
        "Ajustar o espaçamento visual dos cartões no 08-prototipo para ficar na Etapa 2.",
        etapa="design",
        estado={"one_pager": "# One-Pager\n\n## 4. Mecânica\n\nTexto da missão.\n"},
        triagem_itens=[{"n": 1, "dono": "design", "motivo": "ajuste visual no protótipo"}],
    )
    assert divisao.itens[0].dono == "design"


def test_frente_b_secao_zero_completa_e_prototipo_hifi_com_fichas():
    """Frente B: secao(one_pager, 0) inclui 0.1 e 0.2, sincronizar_com_nucleo preserva 0.1/0.2 e quadros PROF usam desktop."""
    from tools import conteudo_aprovado, ilustracoes, one_pager_completo, one_pager_grande

    op = (
        "# Missão\n\n"
        "## 0. Visão Geral\nTexto 0.\n\n"
        "## 0.1 A ideia\nMecânica de arrastar cartões.\n\n"
        "## 0.2 A missão passo a passo\nPasso 1.\n\n"
        "## 1. Narrativa\nHistória.\n"
    )
    s0 = conteudo_aprovado.secao(op, 0) or ""
    assert "0.1 A ideia" in s0
    assert "0.2 A missão passo a passo" in s0
    assert "História." not in s0

    nucleo = "## 0. Visão Geral\nTexto 0 atualizado.\n\n## 1. Narrativa\nHistória nova.\n"
    sincronizado = one_pager_grande.sincronizar_com_nucleo(op, nucleo)
    assert "Texto 0 atualizado." in sincronizado
    assert "## 0.1 A ideia" in sincronizado
    assert "## 0.2 A missão passo a passo" in sincronizado

    # Termos de interação funcional não são mais bloqueados como PALAVRAS_DIFICEIS
    padroes = [p for p, _ in one_pager_completo.PALAVRAS_DIFICEIS]
    assert not any("ranking" in p or "arrast" in p or "interface" in p for p in padroes)

    # Quadros de professor usam moldura-desktop e quadros de aluno usam moldura-mobile
    html = (
        '<style>.x{}</style><body>'
        '<div class="quadro-tela" data-screen-id="E0-PROF-01" data-estado="padrão">Prof</div>'
        '<div class="quadro-tela" data-screen-id="E1-ALU-01" data-estado="padrão">Alu</div>'
        '</body>'
    )
    quadros = ilustracoes.quadros_do_prototipo(html)
    assert 'class="moldura-desktop"' in quadros["E0-PROF-01"]
    assert 'class="moldura-mobile"' in quadros["E1-ALU-01"]


def test_frente_c_falsos_positivos_classificador_e_duracao_ui():
    """Frente C: durações curtas de transição/animação/feedback visual não viram numero-sem-origem."""
    from tools import montagem

    numeros_ui = montagem.numeros_de_regra("Transição suave de fade-in de 0,3 s e toast de confirmação por 2 s.")
    assert numeros_ui == []
    numeros_regra = montagem.numeros_de_regra("O estudante tem 45 s para responder cada rodada.")
    assert ("45", "s") in numeros_regra

