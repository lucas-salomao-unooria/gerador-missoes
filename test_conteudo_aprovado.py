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
    assert nomes[-4:] == ["PrdLoop", "A48dAnexoPrd", "OnePagerPedagogicoLoop", "A49cAnexoPedagogico"]
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
