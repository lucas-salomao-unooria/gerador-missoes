"""O conteúdo que o PO aprovou no one-pager chega inteiro à spec, ao PRD e ao one-pager pedagógico.

Os documentos de teste reproduzem, em miniatura, o que a auditoria do bucket encontrou em 06/10/2026:
a spec da exp06ef1b tirou a EF06CO07 e foi de 29 para 24 minutos em tela seguindo um parecer que o
PO tinha recusado, e o PRD seguiu a spec — sem KPI por habilidade, sem requisito para o podcast e com
links para arquivos que a sessão não tem.
"""

import asyncio
from pathlib import Path

from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from agents.checkers import AnexoAprovadoAgent, RastroCheckAgent, SaidaDeLoopAgent
from tools import conteudo_aprovado as ca

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "exp09ef1b"

ROTEIRO = "**Bia:** Fala, jurados! " + "A mostra escondeu doze projetos de você. " * 8

ONE_PAGER = f"""# One-pager — O Júri Estadual de Projetos v1.5.2

## 2. Currículo
- Foco primário: `EF06CO10`. Esteio: `EF06CO01`, `EF06CO03`, `EF06CO07`.
- Socioemocional: tomada de decisão responsável (CG5).

## 9. Papel do professor e parametrização com IA
### 9a. Preparo — o fluxo do professor em cinco passos
1. Escolhe a disciplina.

## 10. Modularidade, tempos sugeridos e controle do professor
| Etapa | Em tela | Fora da tela |
|---|---|---|
| 1. Desafiar | 2 min | 3 min |
| **Total** | **29 min** | **21 min** |

**Tempo de aula: 50 min · Em tela: 29 min**

---

## 11. Podcast de recapitulação
- **Título do episódio:** *"A Mostra que Ninguém Viu Inteira"*
- **Aviso ao professor:** tocar só depois da Etapa 4.

{ROTEIRO}

---

## 12. Evidências e dados
- O que é capturado: curtidas e voto.

### 12a. Contrato de evidência por habilidade
| Habilidade | Canal | Regra |
|---|---|---|
| `EF06CO10` | A + B | Atingiu: busca ativa · Em processo: abre a galeria · Não atingiu: fecha |
| `EF06CO01` | A + B | Atingiu: agrupa · Em processo: conta · Não atingiu: acaso |
| `EF06CO03` | A + B | Atingiu: 4 blocos · Em processo: inverte · Não atingiu: desconexo |
| `EF06CO07` | A + B | Atingiu: pacote · Em processo: troca · Não atingiu: mágica |

## 13. Cenários de dispositivo
Um aparelho por estudante.

## 17. Hipóteses de validação
- **Hipótese 1:** 85% afunilam o feed.

## 18. Decisões de direção
Nenhuma.
"""


def _spec(codigos=("EF06CO10", "EF06CO01", "EF06CO03", "EF06CO07"), tempo="29 minutos", podcast=True):
    linhas = "\n".join(f"| `{c}` | `E4-ALU-01` | ação | nada | medida | A + B | Atingiu · Em processo · Não atingiu |"
                       for c in codigos)
    return f"""# Spec — O Júri Estadual de Projetos v1.5.2

## 6. Tetos aplicados
- **Tempo total em tela:** **{tempo}** (o teto de referência da rubrica é 25 min).
- **Duração por ato:** máximo de 6 minutos em tela na Etapa 5.

## 8. Professora, preparação e parametrização com IA
{"- Podcast de recapitulação «A Mostra que Ninguém Viu Inteira», depois da Etapa 4." if podcast else "- Preparo em cinco passos."}

## 11. Currículo
| Código | Momento em tela | Ação observável | O que não conta | Medida do bloco 9 | Canal de evidência | Regra ternária |
|---|---|---|---|---|---|---|
{linhas}

## 12. Decisões fechadas neste gate
Nenhuma.
"""


def _prd(codigos_14=("EF06CO10", "EF06CO01", "EF06CO03", "EF06CO07"), kpi_cobre=True, podcast_rf=True,
         tempo="29 minutos", link="produto/05-spec-missao.md"):
    matriz = "\n".join(f"| `{c}` | evidência | interação | `exp06ef1b_sessoes.nivel` | Atingiu · Em processo · Não atingiu |"
                       for c in codigos_14)
    kpi_evid = ("| KPI-02 | — | Quantos chegam a Atingiu em `EF06CO10`, `EF06CO01`, `EF06CO03` e `EF06CO07`? | "
                "< 50% → reforçar o Explicar | turma | — | `EVT-003` | distribuição de `exp06ef1b_sessoes.nivel` | "
                "sem baseline — primeira medição | ≥ 60% | piloto |") if kpi_cobre else ""
    rf_pod = ("| `RF-012` | Podcast de recapitulação | A professora toca o podcast depois da Etapa 4. | P1 | §11 | "
              "QUANDO … O SISTEMA DEVE … |") if podcast_rf else ""
    return f"""---
prd_id: PRD-exp06ef1b
links: {{spec: {link}, prototipo: design/08-prototipo.html}}
---

# 2. Objetivos e métricas

| KPI | PQ | Pergunta | Decisão | Corte | Tela | Evento(s) | Como calcula | Baseline | Alvo | Prazo |
|---|---|---|---|---|---|---|---|---|---|---|
| KPI-01 | T7 | De cada X turmas, quantas terminam? | < 50% → dividir | missao | — | `EVT-U01` | razão | sem baseline — primeira medição | ≥ 70% | 2 meses |
{kpi_evid}

# 5. Experiência

- Total em tela: {tempo}.

# 8. Requisitos funcionais

| RF | Título | Descrição | Prioridade | Rastreio | Aceite |
|---|---|---|---|---|---|
| `RF-001` | Feed | O estudante rola o feed. | P0 | E2 | QUANDO … |
{rf_pod}

# 14. Pedagogia e conformidade

| Habilidade | Evidência | Interação | Coluna | Régua |
|---|---|---|---|---|
{matriz}

# 17. Plano de implementação

```bash
# Iniciar frente de trabalho em worktree dedicada
pnpm worktree criar exp06ef1b
```

# 22. Apêndices e changelog
- 0.1.0 — gerado pelo pipeline.
"""


ARTEFATOS = ["produto/00-one-pager.md", "produto/05-spec-missao.md", "design/08-prototipo.html",
             "dev/01-handoff-dev.md", "one-pager-pedagogico.md"]


def _codigos(resultado):
    return sorted(a["codigo"] for a in resultado["achados"])


# --------------------------------------------------------------------------- seções e anexo
def test_secao_respeita_cerca_e_subnumeracao():
    prd = _prd()
    # o `# Iniciar…` dentro do bloco bash não é título: a seção 17 inteira vem
    assert "pnpm worktree criar" in ca.secao(prd, 17)
    # `### 12a.` é parte da 12, não a 12; e `### 13.1` não abre a 13
    assert "Contrato de evidência" in ca.secao(ONE_PAGER, 12)
    assert ca.secao("# 13. Eventos\n### 13.1 Tabela\nlinha\n# 14. Pedagogia\nx\n", 13).strip().endswith("linha")
    assert ca.secao(ONE_PAGER, 99) is None


def test_anexo_traz_as_secoes_literais_e_e_idempotente():
    anexo = ca.anexo(ONE_PAGER, ca.SECOES_PRD)
    assert anexo.count(f"# {ca.TITULO_ANEXO}") == 1
    assert "A Mostra que Ninguém Viu Inteira" in anexo and ROTEIRO.strip() in anexo  # o roteiro inteiro
    assert "`EF06CO07` | A + B" in anexo and "Em tela: 29 min" in anexo
    assert "One-pager — O Júri Estadual de Projetos v1.5.2" in anexo  # diz de que versão veio
    assert "## 13." not in anexo and "## 18." not in anexo

    uma = ca.com_anexo(_prd(), ONE_PAGER, ca.SECOES_PRD)
    duas = ca.com_anexo(uma, ONE_PAGER, ca.SECOES_PRD)
    assert uma == duas and duas.count(ca.TITULO_ANEXO) == 1
    assert ca.remover_anexo(uma).rstrip() == _prd().rstrip()
    # one-pager sem as seções: nada a anexar, documento intacto
    assert ca.com_anexo("# PRD\n", "# vazio\n", ca.SECOES_PRD) == "# PRD\n"


# --------------------------------------------------------------------------- spec
def test_spec_que_aplica_ressalva_recusada_volta_ao_autor():
    """exp06ef1b: o parecer A2 tirou a EF06CO07 e o A3 levou o tempo a 24 min; o PO tinha mantido os dois."""
    r = ca.validar_spec(_spec(codigos=("EF06CO10", "EF06CO01", "EF06CO03"), tempo="24 minutos"), ONE_PAGER)
    assert r["status"] == "bloqueado"
    assert _codigos(r) == ["habilidade-perdida", "tempo-alterado"]
    perdida = next(a for a in r["achados"] if a["codigo"] == "habilidade-perdida")
    assert "`EF06CO07`" in perdida["resumo"] and "ressalva não incorporada" in perdida["resumo"]
    assert all(a["etapa"] == "produto" for a in r["achados"])

    acrescentada = ca.validar_spec(_spec(codigos=("EF06CO10", "EF06CO01", "EF06CO03", "EF06CO07", "EF06CO09")),
                                   ONE_PAGER)
    assert _codigos(acrescentada) == ["habilidade-acrescentada"]


def test_spec_fiel_passa_e_tetos_nao_sao_contradicao():
    # o teto de referência acima do aprovado e o teto de uma etapa não contradizem os 29 min
    r = ca.validar_spec(_spec(), ONE_PAGER)
    assert r["status"] == "aprovado", r["achados"]
    assert r["codigos"] == ["EF06CO10", "EF06CO01", "EF06CO03", "EF06CO07"] and r["tempo"] == 29
    # «não pode exceder 25» com 29 aprovados manda o código cortar a missão: é contradição
    assert ca.tempos_divergentes("O tempo total em tela não pode exceder 25 minutos.", 29)
    assert not ca.tempos_divergentes("20 minutos de interação em tela, abaixo do teto de 25 minutos em tela.", 20)
    assert not ca.tempos_divergentes("Alternativa descartada: manter 24 min em tela.", 29)


def test_spec_sem_podcast_acusa():
    r = ca.validar_spec(_spec(podcast=False), ONE_PAGER)
    assert _codigos(r) == ["podcast-ausente"]


def test_spec_com_decisao_pendente_deixa_o_curriculo_para_o_gate_bncc():
    spec = _spec(codigos=("EF06CO10",)).replace(
        "| `EF06CO10` |", "| `EF06CO10` [DECISÃO PENDENTE — responsável de produto: x] |")
    assert "habilidade-perdida" not in _codigos(ca.validar_spec(spec, ONE_PAGER))


def test_fixtures_reais_da_exp09_passam():
    op = (FIXTURES / "one_pager.md").read_text(encoding="utf-8")
    spec = (FIXTURES / "spec.md").read_text(encoding="utf-8")
    r = ca.validar_spec(spec, op)
    assert r["status"] == "aprovado", r["achados"]
    assert r["codigos"] == ["EF09CO07", "EF09CO08"] and r["tempo"] == 31 and r["podcast"]
    assert [n for n in ca.TITULOS if ca.secao(op, n)] == list(ca.TITULOS)


# --------------------------------------------------------------------------- PRD
def test_prd_como_os_do_bucket_bloqueia_com_a_correcao_escrita():
    """O PRD da exp06ef1b: três habilidades, sem KPI de evidência, 24 min, podcast só em RNF, spec/ inexistente."""
    prd = _prd(codigos_14=("EF06CO10", "EF06CO01", "EF06CO03"), kpi_cobre=False, podcast_rf=False,
               tempo="24 minutos", link="spec/exp06ef1b-spec.md")
    r = ca.validar_prd(prd, _spec(), ONE_PAGER, ARTEFATOS)
    assert r["status"] == "bloqueado"
    assert _codigos(r) == ["artefato-inexistente", "habilidade-perdida", "habilidade-sem-kpi",
                           "podcast-sem-requisito", "tempo-alterado"]
    resumos = " ".join(a["resumo"] for a in r["achados"])
    assert "`spec/exp06ef1b-spec.md`" in resumos and "`produto/05-spec-missao.md`" in resumos
    assert "nunca `resultado.nivel`" in resumos


def test_prd_fiel_passa_e_o_anexo_nao_conta_como_corpo():
    prd = ca.com_anexo(_prd(), ONE_PAGER, ca.SECOES_PRD)
    assert ca.validar_prd(prd, _spec(), ONE_PAGER, ARTEFATOS)["status"] == "aprovado"
    # a matriz que perdeu a habilidade não se salva porque o anexo a cita
    sem = ca.com_anexo(_prd(codigos_14=("EF06CO10", "EF06CO01", "EF06CO03")), ONE_PAGER, ca.SECOES_PRD)
    assert "habilidade-perdida" in _codigos(ca.validar_prd(sem, _spec(), ONE_PAGER, ARTEFATOS))


# --------------------------------------------------------------------------- pedagógico
def test_pedagogico_sem_podcast_com_tempo_da_spec_e_link_errado():
    ped = """# O Júri Estadual de Projetos

| Instagram | 6º ano | sozinho | 50 minutos (24 minutos em tela) | ninguém | um voto |

## O que a missão ensina
Analisar o consumo de tecnologia (EF06CO10), agrupar dados (EF06CO01), descrever a regra (EF06CO03).

## As telas
Abra `design/08-prototipo-navegavel.html`.
"""
    r = ca.validar_pedagogico(ped, _spec(), ONE_PAGER, ARTEFATOS)
    assert _codigos(r) == ["artefato-inexistente", "habilidade-perdida", "podcast-ausente", "tempo-alterado"]


# --------------------------------------------------------------------------- na esteira
async def _rodar(raiz, estado):
    runner = InMemoryRunner(agent=raiz, app_name="teste")
    await runner.session_service.create_session(app_name="teste", user_id="u", session_id="s", state=estado)
    async for _ in runner.run_async(user_id="u", session_id="s",
                                    new_message=types.Content(role="user", parts=[types.Part(text="go")])):
        pass
    final = await runner.session_service.get_session(app_name="teste", user_id="u", session_id="s")
    return dict(final.state)


def test_gate_e_anexo_na_esteira():
    """O gate reprova o PRD do bucket dentro do loop; o anexo entra depois, uma vez só, e não em mensagem de pulo."""
    loop = LoopAgent(name="PrdLoop", max_iterations=1, sub_agents=[
        RastroCheckAgent(name="A48cConteudoAprovadoPrd", modo="aprovado_prd", rotulo="PRD × one-pager aprovado",
                         report_key="conteudo_aprovado_prd_report", status_key="conteudo_aprovado_prd_status",
                         agente="conteudo-aprovado", estrito=False),
        SaidaDeLoopAgent(name="A48PrdRodada", rotulo="PRD", status_keys=["conteudo_aprovado_prd_status"],
                         rodada_key="prd_rodada", max_rounds=1),
    ])
    raiz = SequentialAgent(name="Raiz", sub_agents=[
        loop, AnexoAprovadoAgent(name="A48dAnexoPrd", chave="prd_final", secoes=list(ca.SECOES_PRD))])
    prd_ruim = _prd(codigos_14=("EF06CO10",), kpi_cobre=False)
    estado = asyncio.run(_rodar(raiz, {"one_pager": ONE_PAGER, "spec_missao": _spec(), "prd_final": prd_ruim}))
    assert estado["conteudo_aprovado_prd_status"] == "bloqueado"
    assert "DIVERGE DO ONE-PAGER APROVADO" in estado["conteudo_aprovado_prd_report"]
    assert estado["prd_final"].count(ca.TITULO_ANEXO) == 1 and ROTEIRO.strip() in estado["prd_final"]

    # rodar de novo (refazer dev) troca o anexo em vez de somar outro
    de_novo = asyncio.run(_rodar(raiz, dict(estado)))
    assert de_novo["prd_final"].count(ca.TITULO_ANEXO) == 1

    pulo = "⏭️ `A47PrdWriter` não executado — pipeline bloqueado (x)."
    estado = asyncio.run(_rodar(
        SequentialAgent(name="R", sub_agents=[AnexoAprovadoAgent(name="A", chave="prd_final", secoes=[11])]),
        {"one_pager": ONE_PAGER, "prd_final": pulo}))
    assert estado["prd_final"] == pulo


def test_refazer_entrega_ao_redator_a_versao_sem_anexo():
    from pipeline.reexecucao import preparar_estado

    prd = ca.com_anexo(_prd(), ONE_PAGER, ca.SECOES_PRD)
    limpo, _ = preparar_estado({"one_pager": ONE_PAGER, "spec_missao": _spec(), "prd_final": prd,
                                "one_pager_pedagogico": ca.com_anexo("# Ped\n", ONE_PAGER, ca.SECOES_PEDAGOGICO)},
                               "dev")
    assert "prd_final" not in limpo
    assert ca.TITULO_ANEXO not in limpo["anterior_prd_final"]
    assert "# 14. Pedagogia e conformidade" in limpo["anterior_prd_final"]
    assert ca.TITULO_ANEXO not in limpo["anterior_one_pager_pedagogico"]


def test_etapas_montadas_com_os_gates_e_os_anexos():
    from agents.dev import build_dev_stage
    from agents.produto import build_produto_stage

    dev = build_dev_stage()
    nomes = [a.name for a in dev.sub_agents]
    # A51 (07/10/2026): o refazer de dev conferido nos documentos de dev
    assert nomes[-6:] == ["PrdLoop", "A48dAnexoPrd", "OnePagerPedagogicoLoop", "A49cAnexoPedagogico", "A50Rastreabilidade",
                          "A51FidelidadeDev"]
    prd_loop = next(a for a in dev.sub_agents if a.name == "PrdLoop")
    saida = next(a for a in prd_loop.sub_agents if a.name == "A48PrdRodada")
    assert "conteudo_aprovado_prd_status" in saida.status_keys
    ped_loop = next(a for a in dev.sub_agents if a.name == "OnePagerPedagogicoLoop")
    assert [a.name for a in ped_loop.sub_agents] == [
        "A49OnePagerPedagogico", "A49bConteudoAprovadoPedagogico", "A49PedagogicoRodada"]

    spec_loop = build_produto_stage(a_partir_de="spec").sub_agents[0]
    saida = next(a for a in spec_loop.sub_agents if a.name == "A16SpecCheck")
    assert "conteudo_aprovado_spec_status" in saida.status_keys


def test_prompts_dizem_de_onde_vem_cada_coisa():
    from prompts import load_prompt

    spec = load_prompt("produto/13_spec_missao.md")
    assert "os ajustes exigidos aqui\nentram na spec" not in spec  # a frase que fez a spec redecidir
    assert "Ressalvas dos pareceres não incorporadas" in spec and "{conteudo_aprovado_spec_report?}" in spec
    prd = load_prompt("dev/47_prd_writer.md")
    assert "{adequacao_report?}" not in prd and "{conteudo_aprovado_prd_report?}" in prd
    assert "spec: spec/<slug>-spec.md" not in prd and "produto/05-spec-missao.md" in prd
    ped = load_prompt("dev/49_one_pager_pedagogico.md")
    for secao in ("## Como a gente sabe que a criança aprendeu", "## Quanto tempo leva e como dividir em aulas",
                  "## O podcast do fechamento", "{conteudo_aprovado_pedagogico_report?}"):
        assert secao in ped, secao


def test_bloco_11_com_subsecao_numerada_nao_fica_vazio():
    """A spec da exp06ef1b regerada com o modelo real (06/10/2026) abriu o currículo com `### 11.1`: o
    `secao_bloco` cortava ali, o bloco 11 saía vazio, e o gate BNCC acusava "nenhum código" — o mesmo
    falso positivo que o PO contestou em 28/09 na mesma missão."""
    from tools import bncc

    spec = _spec().replace("## 11. Currículo\n", "## 11. Currículo\n\n### 11.1 Habilidades e momentos\n\n")
    spec = spec.replace("## 12. Decisões", "### 11.2 Matriz de evidência\nmatriz acima\n\n## 12. Decisões")
    bloco = bncc.secao_bloco(spec, 11)
    assert "`EF06CO07`" in bloco and "### 11.2" in bloco and "## 12." not in bloco
    assert "sem-codigo" not in {a.get("codigo") for a in bncc.validar_spec(spec)["achados"]}
    assert ca.validar_spec(spec, ONE_PAGER)["status"] == "aprovado"


# --------------------------------------------------------------------------- exp01ef1b, 07/10/2026
ONE_PAGER_LITERAIS = """# One-pager — O Detetive da Foto Misteriosa v5.2

## 9. Papel do professor e parametrização com IA
### 9a. Preparo
5. **Pôr no ar:** o professor clica em "Liberar para a Turma".

#### Roteiro de perguntas para o debate mediado
1. *"Quem achou que o menino estava assustado ou em perigo quando viu só o pedaço da foto?"*
2. *"Por que a gente achou isso antes de ver a foto inteira?"*

## 11. Podcast de recapitulação
- **Duração:** ~3 min 30 s.

* **Lucas:** Oi, turma! Hoje a gente virou detetive de foto e descobriu um segredo das imagens.
* **Mariana:** É verdade, Lucas! Um pedaço da foto pode contar uma história bem diferente da foto inteira.
* **Lucas:** Por isso o detetive sempre afasta a câmera antes de decidir o que aconteceu de verdade.

## 12. Evidências e dados
### 12a. Contrato de evidência por habilidade
| Habilidade | Canal | Canal B |
|---|---|---|
| `EF01CO01` | B | **Pergunta:** "O que faz duas fotos combinarem?"<br>- **Atingiu:** "Tem a mesma coisa nas duas, tipo a mesma cara ou o mesmo lugar."<br>- **Em processo:** "As duas são bonitas, por isso combinam."<br>- **Não atingiu:** "Estavam uma do lado da outra na tela." |
"""


def test_literais_aprovados_e_onde_eles_sao_cobrados():
    lit = ca.literais(ONE_PAGER_LITERAIS)
    assert lit["canal_b"][0] == "O que faz duas fotos combinarem?" and len(lit["canal_b"]) == 4
    assert lit["roteiro"][0].startswith("Quem achou que o menino estava assustado") and len(lit["roteiro"]) == 2
    assert len(lit["podcast"]) == 3  # «Duração» aparece uma vez: é metadado, não fala

    # desde 07/10/2026 a copy também traz o roteiro do podcast literal (a exp01ef1b o reescreveu)
    fiel = "\n".join(lit["canal_b"] + lit["roteiro"] + lit["podcast"])
    assert ca.validar_copy(fiel, ONE_PAGER_LITERAIS) == []
    # a spec da exp01ef1b trocou a pergunta 1 do debate por outra redação
    reescrita = fiel.replace(lit["roteiro"][0], "Quem achou que a foto mostrava algo de verdade? O que na imagem fez você pensar isso?")
    achados = ca.validar_copy(reescrita, ONE_PAGER_LITERAIS)
    assert [a["codigo"] for a in achados] == ["roteiro-reescrito"]
    assert achados[0]["agente_responsavel"] == "copy-ptbr-revisao" and achados[0]["etapa"] == "design"
    spec = "## 8. Professora\n" + reescrita + "\n## 11. Currículo\n`EF01CO01`\n"
    assert "roteiro-reescrito" in _codigos(ca.validar_spec(spec, ONE_PAGER_LITERAIS))

    # o banco de conteúdo da exp01ef1b escreveu outro roteiro de podcast, de antes da aula
    assert ca.validar_banco("\n".join(lit["podcast"]), ONE_PAGER_LITERAIS) == []
    outro = "Olá, professoras e professores de todo o Brasil! Desejamos uma excelente aula com a turma."
    assert [a["codigo"] for a in ca.validar_banco(outro, ONE_PAGER_LITERAIS)] == ["podcast-reescrito"]


def test_conferidor_da_plataforma_le_negacao_e_reconhece_a_missao_que_ja_existe():
    from tools.conferir_prd_plataforma import validar_contrato

    def cods(texto, slug=""):
        return sorted(a["codigo"] for a in validar_contrato(texto, slug))

    # as três negações do handoff da exp01ef1b que bloqueavam o PRD
    assert cods("- **NÃO** implementar agendamento: a atividade vai ao ar na hora.") == []
    assert cods("Removidas as colunas `score_*` e a `CONSTRAINT exp01ef1b_score_artefato_check`.") == []
    assert cods("Sem agendamento: o professor põe no ar.") == []
    # e as afirmações que elas pareciam, que continuam pegas
    assert cods("### E0-PROF-05 — Ativação e Agendamento") == ["agendamento-inexistente"]
    pega = validar_contrato("CONSTRAINT exp01ef1b_score_artefato_check CHECK (score_artefato IN ('a','b'))")
    assert [a["codigo"] for a in pega] == ["evidencia-tabela-propria"] and "`exp01ef1b_score_artefato`" in pega[0]["resumo"]

    # a porta da própria missão não está ocupada; a missão que já existe não nasce de `new:exp`
    assert cods("A experiência exp01ef1b roda na porta 5183.", "exp01ef1b") == []
    novo = cods("Porta 5186 em `experiencias-dev.ts`.\n`pnpm new:exp exp01ef1b`", "exp01ef1b")
    assert novo == ["experiencia-ja-existe", "experiencia-ja-existe"]
    # e a porta de OUTRA missão continua ocupada
    assert cods("A exp09ef1b roda na porta 5184.", "exp09ef1b") == ["porta-ocupada"]


def test_lint_do_one_pager_pega_agendamento_e_nao_le_exemplo_nem_etapa_curta():
    from tools.contrato_produto import validar_one_pager

    base = ("## 2. Currículo\n- `EF01CO03` — sequência de passos, exercitada na E2 e na E4.\n\n"
            "## 9. Papel do professor\n5. **Ativar ou agendar:** o professor clica em \"Liberar\" ou agenda a data/horário da aula.\n\n"
            "## 10. Modularidade\n- Gráfico da turma (ex.: 😟 85% vs. 😄 15%).\n")
    r = validar_one_pager(base)
    codigos = [a["codigo"] for a in r["achados"]]
    assert "agendamento" in codigos and r["status"] == "bloqueado"
    assert "numero-sem-origem" not in codigos and "codigo-fora-do-eixo" not in codigos
    assert "agendamento" not in [a["codigo"] for a in validar_one_pager(base.replace(
        "5. **Ativar ou agendar:** o professor clica em \"Liberar\" ou agenda a data/horário da aula.",
        "5. **Pôr no ar:** o professor clica em \"Liberar\"; a plataforma não agenda."))["achados"]]


def test_juiz_tira_o_bullet_retirado_e_refaz_o_veredito():
    from tools.juiz_achados import reescrever_relatorio

    relatorio = ("# Contrato\n\n**Veredito: 🔴 BLOQUEADO** · handoff.\n\n"
                 "- ⚠️ **websocket-mencao** (dono: dev) — WebSocket proposto.\n"
                 "- ⛔ **tabela-eventos** (dono: dev) — sem tabela.\n\n```json\n{}\n```\n")
    env = {"status": "bloqueado", "achados": [{"codigo": "tabela-eventos", "severidade": "bloqueio"}]}
    novo = reescrever_relatorio(relatorio, env, [{"codigo": "websocket-mencao", "citacao": "a plataforma proíbe WebSockets"}])
    corpo = novo.split("## Revisto pelo juiz")[0]
    assert "**websocket-mencao**" not in corpo and "**tabela-eventos**" in corpo
    assert "**Veredito: 🔴 BLOQUEADO (revisto pelo juiz de achados)**" in novo


def test_reprovacao_nova_do_mesmo_gate_substitui_a_anterior():
    from agents.checkers import registrar_degradacao

    estado, delta = {}, {}
    registrar_degradacao(estado, delta, "Contrato de telemetria", "Contrato de telemetria reprovado (4 lacuna(s))")
    estado.update(delta); delta = {}
    registrar_degradacao(estado, delta, "Contrato de telemetria", "Contrato de telemetria reprovado (2 lacuna(s))")
    estado.update(delta); delta = {}
    registrar_degradacao(estado, delta, "Pendências do PRD", "Pendências do PRD reprovado (1 lacuna(s))")
    estado.update(delta)
    assert [d["motivo"] for d in estado["degradacoes"]] == [
        "Contrato de telemetria reprovado (2 lacuna(s))", "Pendências do PRD reprovado (1 lacuna(s))"]
    assert estado["pipeline_bloqueio_motivo"] == "Contrato de telemetria reprovado (2 lacuna(s))"


def test_conteudo_aprovado_chega_aos_agentes_que_nao_leem_o_one_pager():
    from agents.checkers import ConteudoAprovadoAgent
    from agents.design import build_design_stage
    from prompts import load_prompt

    estado = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[
        ConteudoAprovadoAgent(name="C", secoes=list(ca.SECOES_PRD))]), {"one_pager": ONE_PAGER}))
    assert "## Podcast de recapitulação — one-pager §11" in estado["conteudo_aprovado"]
    assert ROTEIRO.strip() in estado["conteudo_aprovado"] and ca.TITULO_ANEXO not in estado["conteudo_aprovado"]

    assert build_design_stage().sub_agents[0].name == "A16dConteudoAprovadoDesign"
    for prompt in ("design/23_fluxo.md", "design/25_caa.md", "design/26_telas.md", "design/27_copy_revisao.md",
                   "design/30_qa_entregaveis.md", "dev/35b_banco_conteudo.md"):
        assert "{conteudo_aprovado?}" in load_prompt(prompt), prompt


def test_secao_do_ds_usa_a_colecao_que_existe_em_vez_de_inventar_uma():
    """A exp01ef1b declarou `nova:galeriadefotos` e inventou oito componentes que a `unoogaleria` do DS 0.2.18
    já tinha. E a ficha do manifesto só aceitava as seções do contrato da plataforma: quem seguisse
    `ambientes.md` e declarasse `unoogaleria` levava "fora da lista"."""
    from tools.rastro import validar_manifesto

    def secao(valor):
        r = validar_manifesto(f"## 0. Identificação\n- `secao_ds: {valor}`\n")
        return [(a["severidade"], a["etapa"]) for a in r["achados"] if a.get("campo") == "secao_ds"]

    assert secao("nova:galeriadefotos") == [("bloqueio", "produto")]
    assert "`unoogaleria`" in validar_manifesto("- `secao_ds: nova:galeriadefotos`")["achados"][-1]["resumo"]
    assert secao("unoogaleria") == [("atencao", "plataforma")]  # existe no DS, sem ponte: pré-requisito
    assert secao("unoovista") == []
    assert secao("instanooria") == [("bloqueio", "produto")]  # legada: missão nova usa a sucessora
    assert secao("minijogo:labirinto") == [("atencao", "plataforma")]


BRIEFING_EXP03 = """BRIEFING DE MISSÃO — 3º ano, 1º bimestre

CONSTRAINT DE INTERFACE — OBRIGATÓRIO
secao_ds: unoogaleria
É PROIBIDO usar qualquer outro design system ou seção. Se a operação cognitiva exigir uma interação que esses componentes não suportam, SINALIZAR — não migrar para outro DS.

HABILIDADES BNCC COMPUTAÇÃO
- EF03CO03 (âncora) — Decomposição: dividir problema em partes menores, resolvê-las e combinar
- EF03CO01 — Lógica computacional

CONTRATO DE EVIDÊNCIA PEDAGÓGICA
Gesto registrável que demonstre:
1. Identificou um componente dentro de um todo
3. Recombinou as partes para formar compreensão do todo

MECÂNICA — IMAGEM PRÉ-DECOMPOSTA
As peças chegam misturadas na Biblioteca da unoogaleria e a criança move cada uma para o álbum certo.

NARRATIVA
Nina / O Boato da Escola. Pergunta-motor: "Se a mesma coisa aconteceu, por que contam de jeitos diferentes?"
"""


def test_briefing_com_titulos_em_maiusculas_vira_checklist_de_fidelidade():
    """O briefing da exp03ef1b (07/10/2026) tem títulos em maiúsculas e sem dois-pontos. O parser só via
    "Direcionamento pedagógico:" e afins: o checklist saía vazio, e a fidelidade aprovou a geração que
    trocou a `unoogaleria` do briefing pelo `unoochat`."""
    from tools import fidelidade as fid

    itens = fid.itens_do_briefing(BRIEFING_EXP03)
    travas = [i["texto"] for i in itens if i["tipo"] == "trava"]
    textos = " | ".join(i["texto"] for i in itens)
    assert len(travas) == 1 and "secao_ds: unoogaleria" in travas[0] and "É PROIBIDO" in travas[0]
    assert "EF03CO01 — Lógica computacional" in textos, "habilidade curta entra pelo bloco"
    assert "CONTRATO DE EVIDÊNCIA PEDAGÓGICA — Gesto registrável que demonstre: 3. Recombinou as partes" in textos
    assert "MECÂNICA — IMAGEM PRÉ-DECOMPOSTA: As peças chegam misturadas" in textos
    assert "Pergunta-motor" in textos
    assert all(i["origem"] == "briefing" for i in itens)
    # a pergunta-motor entre aspas é conferida letra a letra (as três gerações a perderam)
    literais = [i["texto"] for i in itens if i["tipo"] == "literal"]
    assert literais == ["Se a mesma coisa aconteceu, por que contam de jeitos diferentes?"]
    r = fid.aplicar([{**i, "id": f"F{n}"} for n, i in enumerate(itens, 1) if i["tipo"] == "literal"], "", {"one_pager": "sem a frase"})
    assert [(a["severidade"], a["codigo"]) for a in r["achados"]] == [("atencao", "frase-do-briefing-ausente")]
    # a linha solta que fixa a interface também é trava
    assert fid.itens_do_briefing("Interface forçada: Galeria de Fotos\n")[0]["tipo"] == "trava"
    # o formato antigo continua como estava
    antigos = fid.itens_do_briefing((FIXTURES / "briefing.md").read_text(encoding="utf-8"))
    assert len([i for i in antigos if i["tipo"] == "briefing"]) == 13 and not any(i["tipo"] == "trava" for i in antigos)


def test_secao_fixada_pelo_briefing_e_trava_na_spec_e_no_one_pager():
    """As três gerações da exp03ef1b saíram em `unoochat`, `unoovista` e `whatsappmobile` com o briefing
    dizendo `secao_ds: unoogaleria`; a que foi para o `unoochat` foi aprovada."""
    from tools.contrato_produto import validar_one_pager
    from tools.rastro import secao_travada, validar_manifesto

    secoes = {"unoogaleria": None, "unoochat": "@edu/ui/ds-unoochat", "unoovista": "@edu/ui/ds-unoovista"}
    assert secao_travada(BRIEFING_EXP03, secoes)["secao"] == "unoogaleria"
    lida = secao_travada("Interface forçada: Galeria de Fotos", secoes)
    assert lida == {"secao": "unoogaleria", "explicita": False, "trecho": "Interface forçada: Galeria de Fotos"}
    assert secao_travada("Sem interface fixa.", secoes) is None

    def trava_na_spec(valor, briefing=BRIEFING_EXP03):
        r = validar_manifesto(f"## 0. Identificação\n- `secao_ds: {valor}`\n", briefing=briefing)
        return [a["severidade"] for a in r["achados"] if "O briefing fixou" in a["resumo"]]

    assert trava_na_spec("unoochat") == ["bloqueio"]
    assert trava_na_spec("unoogaleria") == []
    assert trava_na_spec("unoochat", "Interface forçada: Galeria de Fotos") == ["atencao"]  # lida pelo nome
    assert trava_na_spec("unoochat", "") == []

    def trava_no_one_pager(cabecalho):
        r = validar_one_pager(f"# One-pager\n\nSlug = `exp03ef1b` · {cabecalho} · Público: estudante\n", briefing=BRIEFING_EXP03)
        return [a["severidade"] for a in r["achados"] if a["codigo"] == "secao-travada-pelo-briefing"]

    assert trava_no_one_pager("Seção do DS: `unoochat`") == ["bloqueio"]
    assert trava_no_one_pager("Seção do DS = `unoogaleria`") == []
    assert trava_no_one_pager("Ambiente simulado: galeria") == []  # sem cabeçalho, quem confere é a spec


def test_produto_conhece_as_secoes_do_ds_e_o_gate_le_o_briefing():
    """A esteira de produto dizia "um de cinco ambientes suportados" com as seções legadas, o critério 2.1
    reprovava o que não estivesse entre os cinco, e o gate estrutural e o revisor não liam o briefing —
    nunca viram o "SINALIZAR — não migrar"."""
    from prompts import get_prompt_raw, load_prompt

    for prompt in ("produto/00d_ideacao_mecanismos.md", "produto/01_nucleo_narrativo.md", "produto/04_secoes_apoio.md",
                   "produto/13_spec_missao.md", "produto/05_gate_estrutural.md",
                   "references/criterios-gate-estrutural.md", "references/formato-spec.md"):
        texto = get_prompt_raw(prompt)
        assert "unoogaleria" in texto, prompt
        assert "cinco ambientes" not in texto and "5 ambientes" not in texto and "um dos 5" not in texto, prompt
    for prompt in ("references/criterios-experiencia.md", "references/formato-relatorios.md"):
        texto = get_prompt_raw(prompt)
        assert "o briefing fix" in texto and "5 ambientes" not in texto, prompt
    for prompt in ("produto/05_gate_estrutural.md", "produto/07_revisor_one_pager.md", "produto/11_gate_final.md"):
        assert "{briefing?}" in get_prompt_raw(prompt), prompt
    for prompt in ("produto/00d_ideacao_mecanismos.md", "produto/01_nucleo_narrativo.md"):
        assert "AlbumCard" in load_prompt(prompt), f"{prompt} precisa do inventário do DS"


def test_agente_nao_decide_no_lugar_do_po():
    """As três gerações da exp03ef1b escreveram "aprovado pelo PO", "Quem decidiu: PO (via one-pager)" e
    "homologadas em 24/09" sem nenhum parecer do PO. Decisão atribuída ao PO sem registro bloqueia; a
    proposta do agente não bloqueia, mas deixa a etapa 🟡."""
    from tools import decisoes as dec

    inventadas = [
        "Desenvolveu-se estritamente o Candidato A aprovado pelo PO na ideação.",
        "| Ratificação do ambiente `unoochat` | PO (via One-pager v2.2) | 2026-10-07 | Rejeitada seção nova |",
        "- **Decisão:** trava da aposta. Quem decidiu: PO no one-pager aprovado. Data: 2026-10-07.",
        "As propostas P0a e P0b foram homologadas pelo PO em 24/09.",
    ]
    legitimas = [
        "- **Decisão:** as 4 gavetas da notícia. Quem decidiu: PO no briefing. Data: 2026-10-07.",
        "[DIVERGÊNCIA: briefing fixou unoogaleria; pendente de homologação pelo PO]",
        "[PROPOSTA — validar com PO: foco primário EF03CO08 · por quê: Regra 12]",
        "O teto ainda não foi aprovado pelo PO.",
    ]
    assert [len(dec.atribuicoes_ao_po(l)) for l in inventadas] == [1, 1, 1, 1]
    assert [len(dec.atribuicoes_ao_po(l)) for l in legitimas] == [0, 0, 0, 0]
    # o anexo que a esteira escreve no PRD diz a verdade: o PO aprovou o one-pager antes do dev
    prd = f"# PRD\n\nRF-01.\n\n---\n\n# {ca.TITULO_ANEXO}\n\n> a versão que o PO aprovou.\n"
    assert dec.atribuicoes_ao_po(prd) == []

    sem_registro = dec.achados("\n".join(inventadas), "A spec", registro_do_po=False)
    assert [(a["severidade"], a["codigo"]) for a in sem_registro] == [("bloqueio", "decisao-atribuida-ao-po")]
    com_registro = dec.achados(inventadas[0], "A spec", registro_do_po=True)
    assert [a["severidade"] for a in com_registro] == ["atencao"]
    assert dec.ha_registro_do_po({"pedidos_do_po": [{"texto": "refaça"}]}) and not dec.ha_registro_do_po({})

    propostas = dec.achados(legitimas[2], "A spec", registro_do_po=False)
    assert [(a["severidade"], a["codigo"]) for a in propostas] == [("atencao", "propostas-a-revisar")]
    assert dec.com_achados({"status": "aprovado", "achados": []}, propostas)["status"] == "amarelo"

    # na esteira: a spec com decisão inventada não passa o gate do conteúdo aprovado
    check = RastroCheckAgent(name="A15g", modo="aprovado_spec", report_key="r", status_key="s")
    estado = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[check]),
                                {"one_pager": ONE_PAGER, "spec_missao": "## 12. Decisões\n" + inventadas[2]}))
    assert estado["s"] == "bloqueado" and "decisao-atribuida-ao-po" in estado["r"]

    # e a regra chega a todo agente que escreve documento
    from prompts import get_prompt_raw

    for prompt in ("produto/01_nucleo_narrativo.md", "produto/13_spec_missao.md", "design/26_telas.md",
                   "dev/47_prd_writer.md", "dev/49_one_pager_pedagogico.md"):
        assert "references/decisoes-do-agente.md" in get_prompt_raw(prompt), prompt


def test_lint_cobra_habilidade_ancora_e_teto_do_briefing():
    """Habilidade do briefing cortada sem registro bloqueia; âncora trocada pela Regra 12 fica 🟡 para o
    PO; teto de palavras sem fonte vira parâmetro — o gate final da exp03ef1b reprovou por um teto
    de 18 palavras que o próprio one-pager inventou."""
    from tools.contrato_produto import validar_one_pager

    one_pager = """# One-pager
Slug = `exp03ef1b` · Seção do DS: `unoogaleria`

**Foco primário BNCC (Regra 12):** `EF03CO08` — expressar em formatos digitais. Esteio: `EF03CO03`.

## 15. Tetos
- Teto de palavras por string: 18 palavras por balão.
- Leitura autônoma: 0 palavras no 1º ano.
- Legenda: [CONVENÇÃO: 45 palavras por parágrafo]
"""
    r = validar_one_pager(one_pager, briefing=BRIEFING_EXP03)
    por_codigo = {a["codigo"]: a for a in r["achados"]}
    assert por_codigo["habilidade-do-briefing-sumiu"]["severidade"] == "bloqueio"
    assert "`EF03CO01`" in por_codigo["habilidade-do-briefing-sumiu"]["resumo"]
    assert por_codigo["ancora-do-briefing-trocada"]["severidade"] == "atencao"
    numeros = por_codigo["numero-sem-origem"]["resumo"]
    assert "18 palavras" in numeros and "0 palavras" not in numeros and "45 palavras" not in numeros

    # com a âncora como foco e o corte registrado como proposta, nada disso aparece
    ok = one_pager.replace("`EF03CO08` — expressar", "`EF03CO03` — decompor").replace(
        "## 15.", "## 18. Decisões\n[PROPOSTA — validar com PO: tirar EF03CO01 e EF03CO02 · por quê: não descrevem a ação]\n\n## 15.")
    codigos = {a["codigo"] for a in validar_one_pager(ok, briefing=BRIEFING_EXP03)["achados"]}
    assert not codigos & {"habilidade-do-briefing-sumiu", "ancora-do-briefing-trocada"}


def test_ajuste_exigido_pelo_parecer_nao_encerra_o_loop():
    """"ADEQUADA COM AJUSTES" é `aprovado_com_ressalvas` com `ajustes_exigidos > 0`; o loop encerrava e o
    revisor nunca aplicava o ajuste (exp03ef1b, geração A). E o teto padrão era 1 rodada."""
    from agents.checkers import SaidaDeLoopAgent
    from config import get_settings

    def saida(ajustes):
        agente = SaidaDeLoopAgent(name="A10b", status_keys=["adequacao_status"], rodada_key="rod", max_rounds=2,
                                  aceitos=["aprovado", "aprovado_com_ressalvas"],
                                  envelope_exige={"adequacao_status": "ajustes_exigidos"})
        loop = LoopAgent(name="L", max_iterations=2, sub_agents=[agente])
        estado = asyncio.run(_rodar(loop, {"adequacao_status": "aprovado_com_ressalvas",
                                           "adequacao_status_envelope": {"ajustes_exigidos": ajustes}}))
        return estado["rod"]

    assert saida(0) == 1, "sem ajuste exigido o loop encerra na primeira rodada"
    assert saida(2) == 2, "com ajuste exigido o loop segue para o revisor e as avaliações refazem"
    from agents.produto import build_produto_stage

    a10b = next(a for a in build_produto_stage().sub_agents if a.name == "AvaliacoesLoop").sub_agents
    a10b = next(a for a in a10b if a.name == "A10bAdequacaoCheck")
    assert a10b.envelope_exige == {"adequacao_status": "ajustes_exigidos"} and a10b.max_rounds >= 2
    assert get_settings().avaliacoes_max_rodadas >= 2


def test_unitube_e_o_nome_antigo_do_unootube():
    """O app e a documentação diziam `unitube`; o DS chama a pasta de `unootube`. Ficha antiga e nova do
    mesmo ambiente continuam vizinhas."""
    from tools import catalogo as cat

    assert cat._ambiente("Missão no ambiente do YouTube (unitube).") == "unootube"
    assert cat._ambiente("Missão no YouTube (unootube).") == "unootube"
    antiga = {"ambiente": "unitube", "descoberta": "", "eixo": ""}
    nova = {"ambiente": "unootube", "descoberta": "", "eixo": ""}
    assert cat.semelhanca(antiga, nova) >= 0.25


JORNADA_TELAS = """# Jornada

## Seção 3 — Inventário de telas
| ID | Etapa | Ator | Ambiente | Propósito | Peso | Elementos na tela | Ação (verbo nativo) | Resultado da ação | Estados | Cenário de dispositivo | Habilidade (bloco 11) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E0-PROF-01 | 0 | PROF | Hub | escolher | serviço | — | tocar | abre | padrão | — | — |
| E0-PROF-02 | 0 | PROF | Hub | recorte | alta | — | digitar | salva | padrão, vazio | — | — |
| E0-PROF-03 | 0 | PROF | Hub | gerar | serviço | — | esperar | progresso | carregando | — | — |
| E0-PROF-04 | 0 | PROF | Hub | curadoria | alta | — | editar | aprova | padrão | — | — |
| E0-PROF-05 | 0 | PROF | Hub | pôr no ar | serviço | — | tocar | libera | padrão | — | — |
| E1-ALU-01 | 1 | ALU | galeria | abrir | pico | — | tocar | abre | primeira vez, padrão, degradado | — | `EF03CO03` |

## Seção 4 — Direção
"""


def test_cobertura_de_telas_confere_por_id_em_todo_derivado():
    """Auditoria de 07/10/2026: o Stitch tinha 27% a 68% das telas, o protótipo um quadro por tela e não
    por estado, e a exp04ef1b tinha `EREV-ALU-01/02` fora do padrão — tudo aprovado, porque se contava
    quantidade, não ID."""
    from tools import telas
    from tools.afirmacoes import cobertura_stitch

    inv = telas.inventario(JORNADA_TELAS)
    assert [t["id"] for t in inv["telas"]][-1] == "E1-ALU-01"
    assert inv["telas"][-1]["estados"] == ["primeira vez", "padrão", "degradado"]
    com_erev = JORNADA_TELAS.replace("| E1-ALU-01 | 1 |", "| EREV-ALU-01 | 5 | ALU | x | x | x | x | x | x | x | x | x |\n| E1-ALU-01 | 1 |")
    assert telas.inventario(com_erev)["fora_do_padrao"] == ["EREV-ALU-01"]
    assert telas.normalizar("E1_ALU_01") == telas.normalizar("e0-prof-03b".replace("e0-prof-03b", "E1-ALU-01")) == "E1-ALU-01"
    assert telas.normalizar("E0-PROF-03b") == "E0-PROF-03"

    todas = " ".join(t["id"] for t in inv["telas"])
    html_ok = "".join(f'<section data-screen-id="{t["id"]}" data-estado="{e}"></section>'
                      for t in inv["telas"] for e in (t["estados"] or ["padrão"]))
    estado = {"jornada_telas": JORNADA_TELAS, "fluxo_arestas": todas.replace("-", "_"),
              "copy_strings_revisada": todas, "wireframes_cobertura": todas, "prototipo_arquivo": html_ok}
    assert telas.cobertura(estado)["status"] == "aprovado"

    # a tela que só aparece em comentário ou no trilho não é quadro; estado faltando é atenção
    so_comentario = html_ok.replace('<section data-screen-id="E0-PROF-05" data-estado="padrão"></section>',
                                    "<!-- E0-PROF-05 -->")
    so_comentario = so_comentario.replace('<section data-screen-id="E1-ALU-01" data-estado="degradado"></section>', "")
    r = telas.cobertura({**estado, "prototipo_arquivo": so_comentario,
                         "copy_strings_revisada": todas.replace("E0-PROF-02", "")})
    por_codigo = {a["codigo"]: a for a in r["achados"]}
    assert por_codigo["telas-fora-do-prototipo"]["agente_responsavel"] == "prototipo"
    assert "E0-PROF-05" in por_codigo["telas-fora-do-prototipo"]["resumo"]
    assert por_codigo["telas-fora-de-copy_strings_revisada"]["agente_responsavel"] == "copy-ptbr-revisao"
    assert por_codigo["estados-fora-do-prototipo"]["severidade"] == "atencao"
    assert "E1-ALU-01 (2 de 3" in por_codigo["estados-fora-do-prototipo"]["resumo"]
    assert telas.cobertura({**estado, "prototipo_arquivo": "<html><body>E1-ALU-01</body></html>"})["achados"][0][
        "codigo"] == "prototipo-sem-quadros-marcados"

    # Stitch: cinco telas, três estados da mesma, não cobrem um inventário de seis — e a lista vai inteira
    folha = "| Tela | Link |\n|---|---|\n" + "".join(f"| E1-ALU-01 — estado {n} | x |\n" for n in range(3)) + \
            "| E0-PROF-01 | x |\n| E0-PROF-02 | x |\n"
    cob = cobertura_stitch(folha, JORNADA_TELAS)
    assert cob["status"] == "bloqueado" and cob["faltando"] == ["E0-PROF-03", "E0-PROF-04", "E0-PROF-05"]
    assert "E0-PROF-05" in cob["achados"][0]["resumo"]


def test_prompts_de_telas_nao_mandam_priorizar():
    """`26_telas.md` mandava "Priorize… Declare o que ficou fora" e o protótipo tinha "Se não couber… na ordem
    de prioridade": as duas frases eram a causa do Stitch com uma fração das telas."""
    from prompts import get_prompt_raw

    telas_prompt, prototipo = get_prompt_raw("design/26_telas.md"), get_prompt_raw("design/28_prototipo.md")
    assert "**Priorize**" not in telas_prompt and "é assincronia, não falha" not in telas_prompt
    assert "{stitch_links?}" in telas_prompt
    assert "## Se não couber" not in prototipo and "data-screen-id" in prototipo and "data-estado" in prototipo


def test_retrabalho_recebe_a_propria_versao_anterior():
    """O despacho só gravava o ticket: o autor reescrevia do zero e o retrabalho das telas da exp09ef1b abriu
    outro projeto no Stitch. Agora o autor lê `anterior_<chave>` e, depois dele, a chave volta a ficar vazia."""
    import json as _json

    from google.adk.agents.base_agent import BaseAgent
    from google.adk.events.event import Event
    from google.adk.events.event_actions import EventActions

    from agents.checkers import DespachoTicketsAgent

    class Autor(BaseAgent):
        output_key: str = "jornada_telas"

        async def _run_async_impl(self, ctx):
            visto = str(ctx.session.state.get("anterior_jornada_telas") or "")
            yield Event(invocation_id=ctx.invocation_id, author=self.name,
                        actions=EventActions(state_delta={"visto": visto, "jornada_telas": "v2"}))

    envelope = {"status": "bloqueado", "achados": [
        {"id": "T1", "severidade": "bloqueio", "codigo": "D2", "agente_responsavel": "jornada", "resumo": "falta tela",
         "onde": "Seção 3", "como": "acrescente E0-PROF-04"}]}
    despacho = DespachoTicketsAgent(name="D", rotulo="Retrabalho", report_key="qa",
                                    mapa={"jornada": ["Autor"]}, ordem=["jornada"], sub_agents=[Autor(name="Autor")])
    estado = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[despacho]),
                                {"qa": "```json\n" + _json.dumps(envelope) + "\n```", "jornada_telas": "v1 com 21 telas"}))
    assert "## Sua versão anterior deste documento" in estado["visto"] and "v1 com 21 telas" in estado["visto"]
    assert estado["jornada_telas"] == "v2" and not estado.get("anterior_jornada_telas")


def test_o_que_o_autor_anterior_escreveu_nao_some_na_reescrita():
    """O D0 da exp06ef1b apagou a pergunta 3 do debate ao consolidar a spec, e a revisão da copy descartou
    prompts, banco curado e podcast em 8 de 8 sessões — com o prompt mandando manter. Linha perdida na spec
    bloqueia com dono; seção perdida na copy volta pelo código, sem mudança."""
    from agents.checkers import CopyPreservadaAgent, SecaoSplitAgent
    from tools import preservacao as pr

    gate0 = ("## 9. Debate\n3. *\"O aplicativo adivinhou o gosto de vocês por mágica ou fomos nós que ensinamos o robô?\"*\n"
             "- [ABERTO — dono: produto: retenção] linha que o D0 reescreve de propósito\n")
    consolidada = "## 9. Debate\n- Retenção: 90 dias — Resolvido em [D0-2]\n"
    assert pr.linhas_perdidas(gate0, consolidada) == [gate0.splitlines()[1].strip()]
    assert pr.linhas_perdidas(gate0, gate0 + " — Resolvido em [D0-1]") == []

    corpo = "x " * 40
    split = SecaoSplitAgent(name="S", source_key="fonte", status_key="st", extracoes=[{
        "chave": "spec_missao", "inicio": r"^## 13\. Spec consolidada", "fim": None, "preservar": "fecha-lacunas"}])
    fonte = f"## 13. Spec consolidada\n{consolidada}\n{corpo}\n"
    estado = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[split]), {"fonte": fonte, "spec_missao": gate0}))
    perdidas = [a for a in estado["st_envelope"]["achados"] if a["codigo"] == "linhas-perdidas"]
    assert estado["st"] == "bloqueado" and perdidas and perdidas[0]["agente_responsavel"] == "fecha-lacunas"
    assert "fomos nós que ensinamos o robô" in perdidas[0]["resumo"]

    p1 = ("## Sheet de strings\n| e1.feed.titulo | Oi |\n\n## Prompts e schemas para conteúdo dinâmico\nprompt X\n"
          "### Schema Zod\nz.object\n\n## Roteiro do podcast\n**Bia:** fala 1\n")
    p2 = "## Sheet de strings revisado\n| e1.feed.titulo | Olá |\n"
    estado = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[CopyPreservadaAgent(name="C")]),
                                {"copy_strings": p1, "copy_strings_revisada": p2}))
    final = estado["copy_strings_revisada"]
    assert final.startswith(p2.rstrip()) and "## Prompts e schemas" in final and "### Schema Zod" in final
    assert "**Bia:** fala 1" in final and final.count("## Prompts e schemas") == 1
    assert pr.reanexar_secoes(p1, final)["reanexadas"] == [], "idempotente"


def test_textos_do_po_conferidos_na_copy_na_caa_e_no_prototipo():
    """O podcast da exp01ef1b chegou ao banco com 0 de 9 falas do PO (a copy o reescreveu); o protótipo da
    exp06ef1b tinha 1 de 4 textos do Canal B. O protótipo monta as telas dentro de um `<script>` — o texto
    de lá conta."""
    one_pager = ONE_PAGER
    falas = ca.literais(one_pager)["podcast"]
    assert falas, "o one-pager de teste tem podcast"
    sem_podcast = ca.validar_copy("## Sheet\nnada do roteiro", one_pager)
    assert any(a["codigo"] == "podcast-reescrito" and a["agente_responsavel"] == "copy-ptbr-revisao" for a in sem_podcast)
    com_podcast = ca.validar_copy("\n".join(falas), one_pager)
    assert not any(a["codigo"] == "podcast-reescrito" for a in com_podcast)

    canal_b = ca.literais(one_pager)["canal_b"]
    if canal_b:
        html_script = "<html><body><script>const telas = `" + " ".join(canal_b) + "`;</script></body></html>"
        assert ca.validar_literais_design("", html_script, one_pager) == []
        achados = ca.validar_literais_design("Prancha do Canal B: escolha uma.", "<html><body>outra</body></html>", one_pager)
        assert {a["agente_responsavel"] for a in achados} == {"caa", "prototipo"}
    assert ca.validar_literais_design("Aplicabilidade: não roda.", "", one_pager) == [], "CAA que não se aplica não é cobrada"


def test_meta_de_kpi_so_com_origem_no_one_pager_ou_no_9f():
    """Os 23 alvos do PRD da exp01ef1b não estavam em lugar nenhum: o exemplo do gabarito trazia `≥ 70%`."""
    from tools.kpis import validar_kpis

    prd = ("## 2. Objetivos\n| KPI | Pergunta | Decisão | Corte | Tela | Evento(s) | Como calcula | Baseline | Alvo | Prazo |\n"
           "|---|---|---|---|---|---|---|---|---|---|\n"
           "| KPI-01 | quantas chegam ao fim? | <50% encurta | turma | E3 | EVT-005 | count(EVT-005) | "
           "sem baseline — primeira medição | ALVO | — |\n")

    def inventado(alvo, one_pager=""):
        return any(a["codigo"] == "kpi-alvo-inventado"
                   for a in validar_kpis(prd.replace("ALVO", alvo), "", one_pager=one_pager)["achados"])

    assert inventado("≥ 75%")
    assert not inventado("≥ 75%", one_pager="## 17. Métricas\n- 75% das turmas chegam ao fim\n")
    assert not inventado("sem meta — primeira medição")
    assert not inventado("[PROPOSTA — validar com PO: ≥ 75%]")


def test_d0_nao_fecha_lacuna_de_mecanica_ou_curriculo():
    """O D0-7 da exp01ef1b saiu `curriculo · Verde` e marcou Resolvido um `[ABERTO — dono: editorial]`;
    a exp02em1b fechou uma de mecânica em verde. As duas classes são decisão humana."""
    from tools.decisoes import lacunas_fechadas_pelo_agente

    tabela = ("| ID | Célula (bloco.campo) | Classe | Cor | Fonte | Quem consumiria |\n|---|---|---|---|---|---|\n"
              "| L-06 | `10.protocolo` | `dispositivo` | Verde | padrão | D2 |\n"
              "| L-07 | `12.pendencia_editorial_codigos` | `curriculo` | Verde | one-pager §2 | D1 |\n"
              "| 3 | `3.nao-usou-ferramenta` | `mecanica` | 🟢 Verde | one-pager §4 | D2 |\n"
              "| 4 | `5.regra` | `mecanica` | 🔴 Vermelho | — | D2 |\n")
    fechadas = lacunas_fechadas_pelo_agente(tabela)
    assert len(fechadas) == 2 and "L-07" in fechadas[0] and "nao-usou-ferramenta" in fechadas[1]


def test_design_recebe_falhas_e_cenarios_e_retrabalho_respeita_dependencias():
    """§8 (falhas) e §13 (cenários de dispositivo) não chegavam a fluxo, CAA, telas e QA; e a revisão da
    copy rodava antes das telas que ela lê."""
    from agents.design import ORDEM_RETRABALHO, build_design_stage

    primeiro = build_design_stage().sub_agents[0]
    assert {8, 13} <= set(primeiro.secoes)
    estado = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[primeiro.model_copy(update={"parent_agent": None})]),
                                {"one_pager": ONE_PAGER}))
    assert estado["conteudo_aprovado"].startswith(ca.NOTA_CONTEUDO_APROVADO)
    assert ORDEM_RETRABALHO.index("caa") < ORDEM_RETRABALHO.index("telas") < ORDEM_RETRABALHO.index("copy-ptbr-revisao")


def _cadeia_completa():
    """Estado da exp09ef1b com o produto real (one-pager, spec, jornada) e os artefatos a jusante completos."""
    from tools import rastreabilidade as rb

    estado = {"one_pager": (FIXTURES / "one_pager.md").read_text(encoding="utf-8"),
              "spec_missao": (FIXTURES / "spec.md").read_text(encoding="utf-8"),
              "jornada_telas": (FIXTURES / "jornada.md").read_text(encoding="utf-8"),
              "briefing": "secao_ds: unoochat\n"}
    reqs = rb.requisitos(estado)

    def do_tipo(*categorias):
        return [r["texto"] for r in reqs if r["categoria"] in categorias]

    telas_ids = do_tipo("tela")
    literais = do_tipo("canal_b", "roteiro", "podcast")
    textos_de_tela = do_tipo("texto_tela")
    comum = "\n".join(do_tipo("habilidade") + [f"{t} min em tela" for t in do_tipo("tempo")] + ["unoochat"])
    estado.update({
        "spec_missao": estado["spec_missao"] + "\n" + "\n".join(literais) + "\n" + comum,
        "fluxo_arestas": "\n".join(i.replace("-", "_") for i in telas_ids) + "\n" + "\n".join(do_tipo("estado")),
        "copy_strings_revisada": "\n".join(telas_ids + literais + textos_de_tela),
        "wireframes_cobertura": "\n".join(telas_ids),
        "prototipo_arquivo": "<html><body>" + "".join(f'<section data-screen-id="{i}" data-estado="padrão"></section>'
                                                      for i in telas_ids) + "<script>const t=`"
                             + " ".join(do_tipo("canal_b") + textos_de_tela) + "`;</script></body></html>",
        "stitch_links": "| Tela | Link |\n|---|---|\n" + "".join(f"| {i} | x |\n" for i in telas_ids),
        "handoff_dev": "\n".join(telas_ids + [e.split(" · ")[1] for e in do_tipo("evento")]) + "\n" + comum,
        "banco_conteudo": "\n".join(do_tipo("podcast")),
        "prd_final": "\n".join(telas_ids + do_tipo("estado") + [e.split(" · ")[1] for e in do_tipo("evento")] + literais
                               + [f"| {p} | [PROPOSTA — validar com PO] |" for p in do_tipo("proposta")]) + "\n" + comum,
        "one_pager_pedagogico": "\n".join(do_tipo("canal_b", "roteiro")) + "\n" + comum,
    })
    return estado, reqs


def test_mutacao_a_matriz_pega_cada_perda_plantada():
    """Padrão ouro: cruzamento que acha defeito vira teste, e quantos defeitos plantados a esteira pega é
    medida. Cada mutação reproduz uma perda que a auditoria de 07/10/2026 achou numa sessão real; a matriz
    tem de pegar todas, e não pode acusar o que está certo (ID com `_` no fluxo, literal só no anexo)."""
    from tools import rastreabilidade as rb

    base, reqs = _cadeia_completa()
    assert rb.matriz(base)["status"] == "aprovado", rb.matriz(base)["achados"]
    texto = {c: [r["texto"] for r in reqs if r["categoria"] == c] for c in rb.CATEGORIAS}

    def tirar(chave, *alvos):
        valor = base[chave]
        for a in alvos:
            valor = valor.replace(a, "")
        return {**base, chave: valor}

    mutacoes = {
        # exp01: a copy e o banco reescreveram o podcast
        "perdido-podcast-copy": tirar("copy_strings_revisada", *texto["podcast"]),
        "perdido-podcast-banco": tirar("banco_conteudo", texto["podcast"][0], texto["podcast"][1], texto["podcast"][2]),
        # exp06: o D0 apagou uma pergunta do debate na consolidação da spec
        "perdido-roteiro-spec": {**base, "spec_missao": base["spec_missao"].replace(texto["roteiro"][-1], "")
                                                                         .replace(texto["roteiro"][-1][:40], "")},
        # exp01/exp09: as telas do professor fora do Stitch
        "perdido-tela-stitch": tirar("stitch_links", "| E0-PROF-01 |", "| E0-PROF-03 |"),
        # protótipo: tela citada só em comentário não é quadro
        "perdido-tela-prototipo": {**base, "prototipo_arquivo": base["prototipo_arquivo"].replace(
            f'<section data-screen-id="{texto["tela"][-1]}" data-estado="padrão"></section>', f"<!-- {texto['tela'][-1]} -->")},
        # exp06: a habilidade sumiu do handoff
        "perdido-habilidade-handoff": tirar("handoff_dev", texto["habilidade"][-1]),
        # exp06: o PRD perdeu o tempo em tela aprovado
        "perdido-tempo-prd": tirar("prd_final", f"{texto['tempo'][0]} min em tela"),
        # exp01: 0 de 17 estados da spec no PRD
        "perdido-estado-prd": tirar("prd_final", *texto["estado"]),
        # exp01: o PRD apagou o marcador da proposta
        "perdido-proposta-prd": {**base, "prd_final": base["prd_final"].replace(
            f"| {texto['proposta'][0]} | [PROPOSTA — validar com PO] |", f"| {texto['proposta'][0]} | decidido |")},
        # exp09: o pedagógico reescreveu a alternativa do Canal B
        "perdido-canal_b-pedagogico": tirar("one_pager_pedagogico", texto["canal_b"][1]),
        # exp03: a seção fixada pelo briefing trocada no PRD
        "perdido-secao_ds-prd": tirar("prd_final", "unoochat"),
        # um evento da 9.4 que o handoff não instrumenta
        "perdido-evento-handoff": tirar("handoff_dev", texto["evento"][0].split(" · ")[1]),
        # a copy reescreveu o texto que o §4 põe na tela (a passada 1 perdia mais da metade; reanálise de 07/10/2026)
        "perdido-texto_tela-copy": tirar("copy_strings_revisada", texto["texto_tela"][0]),
    }
    pegas = {nome: nome in {a["codigo"] for a in rb.matriz(estado)["achados"]} for nome, estado in mutacoes.items()}
    perdidas = [n for n, ok in pegas.items() if not ok]
    assert not perdidas, f"a matriz deixou passar {len(perdidas)} de {len(pegas)} perdas plantadas: {perdidas}"

    # e não acusa o que está certo
    falso = {**base, "prd_final": base["prd_final"].replace(texto["canal_b"][0], "")
             + "\n---\n\n# " + ca.TITULO_ANEXO + "\n\n" + texto["canal_b"][0]}
    assert "perdido-canal_b-prd" not in {a["codigo"] for a in rb.matriz(falso)["achados"]}, "literal no anexo conta"

    # no pedagógico o anexo não salva o corpo: o gate dele (A49b) cobra o Canal B no corpo, e o anexo que a esteira
    # cola traz o §12 inteiro — contado, a coluna saía sempre ✅
    so_no_anexo = ca.com_anexo(base["one_pager_pedagogico"].replace(texto["canal_b"][1], ""), base["one_pager"],
                               ca.SECOES_PEDAGOGICO)
    assert "perdido-canal_b-pedagogico" in {a["codigo"] for a in rb.matriz({**base, "one_pager_pedagogico": so_no_anexo})["achados"]}

    # estado sem o prefixo `E1_` (6 das 15 specs do bucket): a matriz o vê, como o gate do PRD
    spec_minusculas = ("## 2. Mecanismo\n\n### Contrato de estados\n\n"
                       "| Estado inicial | Gatilho | Regra | Estado seguinte |\n|---|---|---|---|\n"
                       "| `INICIAL_DESAFIO` | `iniciar` | abre | `APOSTA_PENDENTE` |\n"
                       "| `APOSTA_PENDENTE` | `apostar` | trava | `APOSTA_TRAVADA` |\n")
    assert rb.estados_da_spec(spec_minusculas) == ["INICIAL_DESAFIO", "APOSTA_PENDENTE", "APOSTA_TRAVADA"]
    assert rb.estados_da_spec("```markdown\n" + spec_minusculas + "```\n") == ["INICIAL_DESAFIO", "APOSTA_PENDENTE",
                                                                                "APOSTA_TRAVADA"]


def test_conserto_de_design_pedido_pela_banca_refaz_o_que_deriva_dele():
    """A banca de dev mandava refazer a jornada e nada refazia protótipo, conferências e handoff."""
    import json as _json

    from google.adk.agents.base_agent import BaseAgent
    from google.adk.events.event import Event
    from google.adk.events.event_actions import EventActions

    from agents.checkers import DespachoTicketsAgent
    from agents.dev import POSFIXO_BANCA, build_dev_stage

    class Marca(BaseAgent):
        async def _run_async_impl(self, ctx):
            feitos = list(ctx.session.state.get("feitos") or []) + [self.name]
            yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta={"feitos": feitos}))

    def rodar(dono):
        envelope = {"status": "bloqueado", "achados": [{"id": "B1", "severidade": "bloqueio", "codigo": "DES-02",
                                                         "agente_responsavel": dono, "resumo": "x"}]}
        despacho = DespachoTicketsAgent(
            name="D", rotulo="Banca", report_key="banca", mapa={"jornada": ["J"], "handoff-dev": ["H"]},
            ordem=["jornada", "handoff-dev"], posfixo_por_dono={"jornada": ["P", "H"]},
            sub_agents=[Marca(name="J"), Marca(name="H"), Marca(name="P")])
        estado = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[despacho]),
                                    {"banca": "```json\n" + _json.dumps(envelope) + "\n```"}))
        return estado.get("feitos")

    assert rodar("jornada") == ["J", "P", "H"]
    assert rodar("handoff-dev") == ["H"], "conserto de handoff não refaz o protótipo"
    assert "A28PrototipoRetrabalhoBanca" in POSFIXO_BANCA["telas"]
    banca = next(a for a in build_dev_stage().sub_agents if a.name == "BancaLoop")
    despacho = next(a for a in banca.sub_agents if a.name == "A46DespachoBanca")
    existentes = {s.name for s in despacho.sub_agents}
    assert all(n in existentes for nomes in POSFIXO_BANCA.values() for n in nomes)
