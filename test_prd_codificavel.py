"""O PRD como insumo para codificação: o que ele leva à plataforma confere com ela (`tools/conferir_prd_plataforma.py`),
e o que a spec decidiu de eventos e ausências chega a ele (`tools/cobertura_design.py`).

A auditoria de 07/10/2026 leu os PRDs da exp01ef1b e da exp09ef1b contra o código da plataforma: ids `TEXT` com «NÃO
usar `UUID`», `escola_id UUID`, `tentativa` no lugar da rodada, nenhum `experiencia.json`, ADR-108 com outro assunto,
um RF P0 de offline que o SDK não tem e nenhum dos registros do hub que os testes da plataforma cobram. Cada teste
reproduz, em miniatura, o que foi medido nas sete sessões completas do bucket (exp01ef1b, exp02em1b, exp04ef1b,
exp05ef1b, exp06ef1b, exp07ef1b e exp09ef1b) e diz o número no docstring.

A base é a fotografia de `fixtures/base-plataforma` (89e0f9ae, 06/10/2026: última ADR 149, a exp01ef1b publicada na
porta 5183 em v1.0.6, a exp09ef1b ainda não). Nenhum teste lê sessão real.
"""

import pytest

from agents.callbacks import extrair_envelope
from tools import cobertura_design as cd
from tools import conferir_prd_plataforma as cp

# --------------------------------------------------------------------------- um PRD novo no padrão ouro, em miniatura
DDL_BOM = '''```sql
CREATE TABLE "exp09ef1b_pacotes" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "escola_id" TEXT NOT NULL,
    "turma_id" UUID NOT NULL,
    "conteudo" JSONB NOT NULL,
    "ativo" BOOLEAN NOT NULL DEFAULT false,
    "criado_por" UUID NOT NULL,
    CONSTRAINT "exp09ef1b_pacotes_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "exp09ef1b_sessoes" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "escola_id" TEXT NOT NULL,
    "turma_id" UUID NOT NULL,
    "pacote_id" UUID NOT NULL,
    "rodada" INTEGER NOT NULL,
    "estudante_id" UUID NOT NULL,
    "voto_tentativas" INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT "exp09ef1b_sessoes_pkey" PRIMARY KEY ("id")
);

ALTER TABLE "exp09ef1b_pacotes" ADD CONSTRAINT "exp09ef1b_pacotes_turma_id_fkey" FOREIGN KEY ("turma_id") REFERENCES "turmas"("id") ON DELETE CASCADE;
ALTER TABLE "exp09ef1b_sessoes" ADD CONSTRAINT "exp09ef1b_sessoes_turma_id_fkey" FOREIGN KEY ("turma_id") REFERENCES "turmas"("id") ON DELETE CASCADE;
ALTER TABLE "exp09ef1b_sessoes" ADD CONSTRAINT "exp09ef1b_sessoes_estudante_id_fkey" FOREIGN KEY ("estudante_id") REFERENCES "users"("id") ON DELETE CASCADE;
ALTER TABLE "exp09ef1b_sessoes" ADD CONSTRAINT "exp09ef1b_sessoes_pacote_id_fkey" FOREIGN KEY ("pacote_id") REFERENCES "exp09ef1b_pacotes"("id") ON DELETE CASCADE;
```
'''

MANIFESTO_BOM = '''```json
{
  "id": "exp09ef1b",
  "nome": "O Conselho da Verba",
  "versao": "0.1.0",
  "series": ["9EF"],
  "unidade": 1,
  "produto": "entre-redes",
  "capabilities": ["telemetria", "progresso", "ia", "avaliacao"],
  "viewport": {"largura": 1280, "altura": 800},
  "publico": "estudante",
  "permissoes": [],
  "verbos": {"scored": "homologou a verba", "interacted": "abriu um documento"}
}
```
'''

PRD_NOVA = f"""---
prd_id: PRD-exp09ef1b
slug_experiencia: exp09ef1b
serie: ["9EF"]
unidade: 1
---

# 3. Não-objetivos

- Imagens sintéticas por território via Imagen 3 ficam para a V2.

# 6. Fluxo e máquina de estados

| Estado inicial | Gatilho | Estado seguinte |
|---|---|---|
| `E2_THREAD` | queda de rede | `ST_OFFLINE` |

- **SE** a conexão cair, **ENTÃO O SISTEMA DEVE** mostrar a faixa na voz da ficção e reentrar pelo servidor.

# 11. Modelo de dados

{DDL_BOM}
# 12. Contratos de API

## 12.2 IA no preparo

| Chamada | Modelo |
|---|---|
| gerar-conteudo | família `padrao` (`gemini-3.6-flash`, contrato da plataforma) |

# 16. Arquitetura da solução

#### ADR-146 — Pôr a atividade no ar libera a missão na sala

- **ADR-105:** Quota de IA como dado em `ia_quotas`, editável pela Unooria.
- **ADR-87 / ADR-88 (Eixo da Disponibilidade)**: o painel `/unooria` desliga a missão.
- Decisão nova: `ADR-150 (proposta)` — o resolvedor da evidência do Conselho.

# 17. Plano de implementação

## 17.1 Manifesto `public/experiencia.json`

{MANIFESTO_BOM}
## 17.2 Porta

A porta 5186 em `apps/hub/lib/experiencias-dev.ts`, com `--strictPort`, e a origem em `CORS_ORIGINS`. A liberação de
demo é a turma "9A" em `LIBERACOES_DE_DEMO`.

## 17.3 Hub do professor

| O quê | Arquivo |
|---|---|
| Catálogo | `apps/hub/lib/entre-redes/catalogo.ts` (`MISSAO_CONSELHO` em `MISSOES_PUBLICADAS`) |
| Guia | `apps/hub/lib/entre-redes/guias/exp09ef1b.ts` + `guias/index.ts` |
| Ficha | `apps/hub/app/(plataforma)/professor/entre-redes/[ano]/[unidade]/page.tsx` + `missao-conselho.tsx` |
| Resultados | `…/[unidade]/resultados/page.tsx` + `resultados-conselho.tsx` |
| BFF | o slug `conselho` em `PREFIXOS_PERMITIDOS` |

# 19. Decisões e pendências

| O que a spec ou o one-pager dizem | O que a plataforma tem (fonte) | O que o PRD seguiu | Dono |
|---|---|---|---|
| `escola_id UUID` (spec, bloco 9) | `escola_id TEXT` (`exemplo-schema-exp.md`) | `TEXT` | produto |
"""


def _codigos(achados):
    return {a["codigo"]: a["severidade"] for a in achados}


def _achados(texto, codigo):
    return [a for a in cp.validar_prd(texto) if a["codigo"] == codigo]


def test_o_prd_novo_no_padrao_ouro_passa_em_tudo():
    """O gabarito de 07/10/2026 inteiro: tipos da plataforma com FK, sessão por (pacote, rodada, estudante), o
    manifesto completo com o id derivado, ADR nova marcada, o modelo do contrato e os registros do hub. E o que
    não é defeito fica de fora: o estado `ST_OFFLINE`, a «Imagen 3» da V2 na §3 e a `escola_id UUID` da spec
    registrada na tabela de divergências da §19."""
    assert cp.slug_do_prd(PRD_NOVA) == "exp09ef1b"
    assert cp.validar_prd(PRD_NOVA) == []
    r = cd.validar(PRD_NOVA, {})
    assert r["status"] == "aprovado", r["achados"]
    rel = cd.relatorio(r, "exp09ef1b")
    assert "modelo de dados, manifesto, ADR" in rel and extrair_envelope(rel)["status"] == "aprovado"


# --------------------------------------------------------------------------- 1. modelo de dados
PRISMA_EXP01 = '''```prisma
model Exp01ef1bSessao {
  sessaoId    String @default(dbgenerated("gen_random_uuid()")) @map("sessao_id")
  escolaId    String @map("escola_id")
  turmaId     String @map("turma_id")
  estudanteId String @map("estudante_id")
  tentativa   Int    @default(1) @db.SmallInt

  @@id([escolaId, sessaoId])
  @@map("exp01ef1b_sessoes")
}
```

- **NÃO** usar `UUID` para `estudante_id`, `sessao_id` ou `turma_id` nas tabelas da missão.
'''


def test_tipos_e_chaves_do_modelo_de_dados_sao_os_da_plataforma():
    """exp01ef1b: `turma_id`/`estudante_id` `String` sem `@db.Uuid` nem `@relation` (e «NÃO usar `UUID`» na §17.4);
    exp06ef1b: `escola_id UUID` nas quatro tabelas do DDL; exp02em1b: `escola_id UUID NOT NULL` num RNF e no
    `erDiagram`. As quatro outras acertaram os tipos."""
    achados = cp.conferir_modelo_de_dados(PRISMA_EXP01)
    tipos = next(a for a in achados if a["codigo"] == "tipo-divergente-da-plataforma" and "tipo diferente" in a["resumo"])
    assert tipos["severidade"] == "bloqueio"
    assert "`exp01ef1b_sessoes.turma_id` TEXT (schema Prisma) — a plataforma grava `UUID`" in tipos["resumo"]
    assert "`exp01ef1b_sessoes.estudante_id` TEXT" in tipos["resumo"]
    assert "escola_id" not in tipos["resumo"].split("Na plataforma")[0]  # `escolaId String` é TEXT: certo
    assert "`turma_id` «não usar `UUID`» (prosa)" in tipos["resumo"]  # a §17.4 da exp01ef1b

    sql = DDL_BOM.replace('"escola_id" TEXT NOT NULL,\n    "turma_id" UUID NOT NULL,\n    "conteudo"',
                          '"escola_id" UUID NOT NULL,\n    "turma_id" UUID NOT NULL,\n    "conteudo"')
    assert "`exp09ef1b_pacotes.escola_id` UUID (DDL SQL)" in _achados(sql, "tipo-divergente-da-plataforma")[0]["resumo"]
    rnf = "# 9. Requisitos não funcionais\n- **RNF-SEC-001**: toda tabela tem a coluna `escola_id UUID NOT NULL` com RLS.\n"
    assert "`escola_id` UUID (prosa)" in cp.conferir_modelo_de_dados(rnf)[0]["resumo"]
    er = "```mermaid\nerDiagram\n  exp02em1b_sessoes {\n    uuid escola_id\n    uuid turma_id FK\n  }\n```\n"
    assert "`exp02em1b_sessoes.escola_id` uuid (erDiagram)" in cp.conferir_modelo_de_dados(er)[0]["resumo"]
    # registrar o que a spec diz não é declarar: a tabela de divergências da §19 e a frase que cita a spec
    registro = "# 19. Pendências\n| Spec | Plataforma |\n|---|---|\n| `escola_id UUID` | `escola_id TEXT` |\n"
    citacao = "# 11. Modelo\nA spec declarava `escola_id UUID`, e a plataforma grava `escola_id TEXT`.\n"
    proibicao = "# 17.4 O que NÃO fazer\n- NÃO declarar `escola_id UUID`: o tenant é `escola_id TEXT`.\n"
    assert cp.conferir_modelo_de_dados(registro) == [] and cp.conferir_modelo_de_dados(citacao) == []
    assert cp.conferir_modelo_de_dados(proibicao) == []


def test_estudante_sem_fk_reprova_o_teste_de_identidade_unica():
    """exp05ef1b e exp07ef1b: `_reflexoes` com `estudante_id UUID` e FK só para a sessão — o
    `identidade-unica.spec.ts` da plataforma reprova toda coluna `estudante_id` sem FK. Sem FK de `turma_id` nenhum
    teste quebra: ⚠️."""
    reflexoes = '''```sql
CREATE TABLE "exp07ef1b_reflexoes" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "escola_id" TEXT NOT NULL,
    "turma_id" UUID NOT NULL,
    "estudante_id" UUID NOT NULL,
    "sessao_id" UUID NOT NULL,
    "texto" TEXT NOT NULL,
    CONSTRAINT "fk_reflexoes_sessao" FOREIGN KEY ("sessao_id") REFERENCES "exp07ef1b_sessoes"("id") ON DELETE CASCADE
);
```
'''
    achados = cp.conferir_modelo_de_dados(reflexoes)
    estudante = [a for a in achados if "identidade-unica.spec.ts" in a["resumo"]]
    turma = [a for a in achados if "`turma_id` sem chave estrangeira" in a["resumo"]]
    assert [a["severidade"] for a in estudante] == ["bloqueio"] and "`exp07ef1b_reflexoes`" in estudante[0]["resumo"]
    assert [a["severidade"] for a in turma] == ["atencao"]
    # a FK inline também vale, e a do Prisma é o `@relation(fields: [...])`
    inline = reflexoes.replace('"estudante_id" UUID NOT NULL,', '"estudante_id" UUID NOT NULL REFERENCES "users"("id"),')
    inline = inline.replace('"turma_id" UUID NOT NULL,', '"turma_id" UUID NOT NULL REFERENCES "turmas"("id"),')
    assert cp.conferir_modelo_de_dados(inline) == []
    prisma = PRISMA_EXP01.replace('estudanteId String @map("estudante_id")',
                                  'estudanteId String @map("estudante_id") @db.Uuid\n'
                                  '  estudante User @relation(fields: [estudanteId], references: [id], onDelete: Cascade)')
    assert not any("identidade-unica" in a["resumo"] for a in cp.conferir_modelo_de_dados(prisma))


def test_sessao_por_rodada_e_atividade():
    """Todas as sete gravam `tentativa` (ou nada) no lugar de `rodada`, e nenhuma põe o pacote na sessão: a
    evidência é por atividade e rodada (ADR-112) e `EvidenciasService.marcar` precisa das duas. `<acao>_tentativas`
    é contador, não a rodada. A exp09ef1b declara a sessão só em prosa e `erDiagram`."""
    sessao = _achados(PRISMA_EXP01, "sessao-sem-rodada")
    assert sessao[0]["severidade"] == "bloqueio"
    assert "`exp01ef1b_sessoes`: `tentativa` no lugar de `rodada`, sem a atividade (`pacote_id`)" in sessao[0]["resumo"]
    prosa = ("# 11. Modelo de dados\n- **`exp09ef1b_sessoes`**: PK `id UUID`, UK `[escola_id, turma_id, estudante_id]`. "
             "Campos: `escola_id TEXT`, `turma_id UUID`, `estudante_id UUID`, `etapa_atual VARCHAR(30)`.\n")
    assert "sem `rodada`, sem a atividade" in _achados(prosa, "sessao-sem-rodada")[0]["resumo"]
    certa = prosa.replace("UK `[escola_id, turma_id, estudante_id]`", "UK `[pacote_id, rodada, estudante_id]`")
    assert _achados(certa, "sessao-sem-rodada") == []
    # a `rodada` de um KPI na linha que cita a tabela não é coluna dela (exp04ef1b, schema Prisma sem rodada)
    kpi = PRISMA_EXP01.replace("  tentativa   Int    @default(1) @db.SmallInt\n", "") + (
        "\n| KPI-02 | `exp01ef1b_sessoes` com `resultado.rodada` == 1 |\n")
    assert "sem `rodada`" in _achados(kpi, "sessao-sem-rodada")[0]["resumo"]


# --------------------------------------------------------------------------- 2. manifesto
def test_manifesto_completo_valido_e_com_o_id_derivado():
    """Só a exp02em1b trazia o manifesto num bloco json — sem o `viewport`; as outras seis, em prosa («Manifesto v0.1.0
    completo», exp01ef1b). O `viewport: "mobile"` da exp01ef1b derrubou o deploy de 11/09/2026, e o
    `codigo-da-experiencia.spec.ts` reprova id que não é `codigoDaMissao(series[0], unidade)`."""
    sem = PRD_NOVA.replace(MANIFESTO_BOM, "O manifesto v0.1.0, completo.\n")
    assert _codigos(cp.validar_prd(sem)) == {"manifesto-ausente": "bloqueio"}
    quebrado = PRD_NOVA.replace('"publico": "estudante",', '"publico": "estudante"')
    assert "não é JSON válido" in _achados(quebrado, "manifesto-ausente")[0]["resumo"]
    comentado = PRD_NOVA.replace('"permissoes": [],', '"permissoes": [],  // nenhuma')
    assert _achados(comentado, "manifesto-ausente") == []  # comentário não esconde o manifesto
    sem_viewport = PRD_NOVA.replace('  "viewport": {"largura": 1280, "altura": 800},\n', "")
    assert "não tem `viewport`" in _achados(sem_viewport, "manifesto-ausente")[0]["resumo"]

    invalido = PRD_NOVA.replace('{"largura": 1280, "altura": 800}', '"mobile"').replace('"0.1.0"', '"0.1"')
    resumo = _achados(invalido, "manifesto-invalido")[0]["resumo"]
    assert "`viewport` é `\"mobile\"`" in resumo and "`versao` `0.1` não é `x.y.z`" in resumo
    assert "manifestos-passam-no-put.spec.ts" in resumo

    serie_errada = PRD_NOVA.replace('"series": ["9EF"]', '"series": ["8EF"]')
    resumo = _achados(serie_errada, "id-nao-derivado")[0]["resumo"]
    assert "o manifesto diz `exp09ef1b` com série `8EF` e unidade `1` — o código é `exp08ef1b`" in resumo
    assert "codigo-da-experiencia.spec.ts" in resumo
    frontmatter = PRD_NOVA.replace("unidade: 1\n---", "unidade: 2\n---", 1)
    assert "o frontmatter diz `exp09ef1b`" in _achados(frontmatter, "id-nao-derivado")[0]["resumo"]
    assert cp.codigo_da_missao("2EM", 1) == "exp02em1b" and cp.codigo_da_missao("4EM", 1) == ""


def test_missao_que_ja_existe_e_atualizacao_com_a_decisao_do_po():
    """exp01ef1b (07/10/2026): o PRD mandava `pnpm new:exp exp01ef1b` na porta 5186, e a plataforma já tem a exp01ef1b
    (O Que a Foto Conta, v1.0.6, porta 5183). `validar_contrato` acusa o `new:exp` e a porta; aqui, o que falta para
    ser atualização: a decisão do PO registrada e a versão acima da publicada. As seis sessões cujo id a plataforma
    publicou depois (exp01, exp02em1b, exp04, exp05, exp06, exp07) caem aqui; a exp09ef1b, nova, não."""
    existente = PRD_NOVA.replace("exp09ef1b", "exp01ef1b").replace('["9EF"]', '["1EF"]')
    resumo = _achados(existente, "existente-sem-decisao")[0]["resumo"]
    assert "«O Que a Foto Conta», v1.0.6, porta 5183" in resumo
    assert "não registra `[ABERTO — dono: PO" in resumo and "`versao` `0.1.0`, que não sobe da publicada `1.0.6`" in resumo
    decidida = existente.replace('"versao": "0.1.0"', '"versao": "1.1.0"') + (
        "\n- [ABERTO — dono: PO: substituir a existente ou outro código] A exp01ef1b já está publicada.\n")
    assert _achados(decidida, "existente-sem-decisao") == []
    assert _achados(PRD_NOVA, "existente-sem-decisao") == []


# --------------------------------------------------------------------------- 3. ADR
def test_adr_proxima_sem_proposta_e_adr_existente_com_outro_assunto():
    """exp01ef1b: «**ADR-150:** Recurso de podcast…» com a última ADR em 149. exp06ef1b (`#### ADR-108: Sincronização
    Síncrona Coletiva por Polling…`), exp04ef1b (item em negrito) e exp01ef1b (coluna «ADR necessária»: «ADR-108
    (Seção de Galeria de Fotos no DS)») — cinco declarações, nenhum radical em comum com o título do contrato, todas
    decisões novas sob número tomado. As 13 declarações certas das sete sessões passam."""
    proxima = "# 19. ADR\n- **ADR-150:** Recurso de podcast de recapitulação como padrão da plataforma.\n"
    a = _achados(proxima, "adr-sem-proposta")[0]
    assert a["severidade"] == "bloqueio" and "`ADR-150` ainda não existe" in a["resumo"]
    assert _achados(proxima.replace("**ADR-150:**", "**ADR-150 (proposta):**"), "adr-sem-proposta") == []

    titulo = "#### ADR-108: Sincronização Síncrona Coletiva por Polling HTTP Curto na Mostra Escolar\n"
    a = _achados(titulo, "adr-titulo-divergente")[0]
    assert a["severidade"] == "bloqueio"
    assert "no contrato, «A missão de sala nasce vazia, e a revelação é do relógio da turma»" in a["resumo"]
    tabela = ("| Capacidade | ADR necessária |\n|---|---|\n"
              "| Seção de DS `nova:galeriadefotos` | ADR-108 (Seção de Galeria de Fotos no DS) |\n")
    assert "`ADR-108` «Seção de Galeria de Fotos no DS»" in _achados(tabela, "adr-titulo-divergente")[0]["resumo"]
    # o que não é declaração com outro assunto
    certas = ("- **ADR-105:** Quota diária de IA como dado em `ia_quotas`, editável só pelo `admin`.\n"
              "- **ADR-87 / ADR-88 (Eixo da Disponibilidade)**: interruptor do painel.\n"
              "- **ADR-112/145:** Módulo genérico de evidências.\n"
              "- NÃO usar `@Roles(\"gestor\")` (usar os nomes da ADR-80: `gestor_escola`, `gestor_contrato`).\n"
              "| Capacidade | ADR necessária |\n|---|---|\n| Gravar voz | ADR nova (a próxima, ADR-150 proposta) |\n")
    assert cp.conferir_adr(certas, cp.base_plataforma.contrato()) == []


# --------------------------------------------------------------------------- 4. capacidade
def test_offline_e_cache_local_que_o_sdk_nao_tem():
    """exp01ef1b: US-09 «funcione offline», RF-019 (P0) «operar offline com cache local», RNF-003 «operar offline…
    buffer local» → ⛔. exp07ef1b: «IndexedDB… com ressincronização» numa tabela de riscos → ⚠️. O estado de erro
    (`ST_OFFLINE`, «Estados: offline») é a degradação certa e não casa; pedido à plataforma também não."""
    rf = ("# 8. Requisitos funcionais\n| ID | Descrição | Pri. |\n|---|---|---|\n"
          "| **RF-019** | O sistema deve operar offline com cache local para o pacote padrão. | P0 |\n")
    a = _achados(rf, "capacidade-inexistente")[0]
    assert a["severidade"] == "bloqueio" and "RF-019: «operar offline»" in a["resumo"]
    risco = "# 21. Riscos\n| Risco | Mitigação |\n|---|---|\n| Queda de conexão | Rascunho em IndexedDB no navegador |\n"
    assert _achados(risco, "capacidade-inexistente")[0]["severidade"] == "atencao"
    limpo = ("# 6. Fluxo\n| `*` | `net:desconexao` | `ST_OFFLINE` |\n- **Estados:** normal, gaveta expandida, offline.\n"
             "# 15. Pré-requisitos\n- [PENDÊNCIA PLATAFORMA] Service Worker para operar offline — dono: plataforma.\n"
             "# 17.4 O que NÃO fazer\n- NÃO escrever Service Worker na missão.\n"
             "- A missão não opera offline: cada jogada é rota do servidor.\n")
    assert cp.conferir_capacidades(limpo) == []


# --------------------------------------------------------------------------- 5. modelo de IA
def test_modelo_de_ia_e_o_do_contrato():
    """exp06ef1b «Gemini 1.5 Pro» e exp07ef1b «Gemini 1.5 Flash» → ⚠️; exp01ef1b e exp09ef1b «Gemini 3.6 Flash», certo.
    A voz (`…-tts`) é do módulo de podcast e a §3 é o que não se faz (a «Imagen 3» da V2 da exp09ef1b)."""
    c = cp.base_plataforma.contrato()
    a = cp.conferir_modelo_de_ia("- Teto de 10.000 tokens por turma (Vertex Gemini 1.5 Pro).\n", c)
    assert _codigos(a) == {"modelo-ia-divergente": "atencao"} and "«Gemini 1.5 Pro»" in a[0]["resumo"]
    certo = ("- Vertex AI Gemini 3.6 Flash no preparo; a arte com `gemini-3.1-flash-image`.\n"
             "- O podcast sintetiza com `gemini-2.5-flash-tts` (módulo da plataforma).\n"
             "# 3. Não-objetivos\n- Imagens por território via Imagen 3, na V2.\n")
    assert cp.conferir_modelo_de_ia(certo, c) == []


# --------------------------------------------------------------------------- 6. registros do hub e da api
def test_missao_nova_nomeia_os_registros_que_os_testes_da_plataforma_cobram():
    """A exp09ef1b, a única nova das sete, não nomeava guia, despachante da ficha nem dos resultados — três testes da
    plataforma reprovariam a missão publicada. O resto (catálogo, BFF, demo, porta, CORS) não quebra teste: ⚠️.
    Missão que já existe já tem os registros e não é cobrada."""
    sem_guia = PRD_NOVA.replace("| Guia | `apps/hub/lib/entre-redes/guias/exp09ef1b.ts` + `guias/index.ts` |\n", "")
    a = _achados(sem_guia, "registro-da-plataforma-ausente")
    assert [x["severidade"] for x in a] == ["bloqueio"]
    assert "guias/index.test.ts › toda missão disponível com experiência tem guia" in a[0]["resumo"]
    sem_bff = PRD_NOVA.replace("| BFF | o slug `conselho` em `PREFIXOS_PERMITIDOS` |\n", "")
    a = _achados(sem_bff, "registro-da-plataforma-ausente")
    assert [x["severidade"] for x in a] == ["atencao"] and "`PREFIXOS_PERMITIDOS`" in a[0]["resumo"]

    nada = "---\nslug_experiencia: exp09ef1b\nserie: [\"9EF\"]\nunidade: 1\n---\n# 17. Plano\n"
    quebra = next(x for x in _achados(nada, "registro-da-plataforma-ausente") if x["severidade"] == "bloqueio")
    for teste in ("guias/index.test.ts", "despachante-da-ficha.test.ts", "rotas-da-missao.test.ts"):
        assert teste in quebra["resumo"]
    existente = nada.replace("exp09ef1b", "exp01ef1b").replace("9EF", "1EF")
    assert _achados(existente, "registro-da-plataforma-ausente") == []


def test_lista_de_equipes_escrita_a_mao_no_teste_da_api():
    """`equipes-regras.spec.ts` lista as missões de `EXPERIENCIAS_COM_EQUIPE` e `_COM_ATIVIDADE` à mão: a missão que
    entra numa delas sem o teste mudar junto reprova a suíte da api. Nenhum dos sete PRDs as citava."""
    com_equipe = PRD_NOVA + "\n- A missão entra em `EXPERIENCIAS_COM_EQUIPE` (`apps/api/src/equipes/regras.ts`).\n"
    a = _achados(com_equipe, "registro-da-plataforma-ausente")
    assert [x["severidade"] for x in a] == ["bloqueio"] and "tests/equipes-regras.spec.ts`" in a[0]["resumo"]
    assert _achados(com_equipe + "- e em `apps/api/tests/equipes-regras.spec.ts`.\n",
                    "registro-da-plataforma-ausente") == []
    # a exp06ef1b já está na lista: citá-la não muda o teste
    ja = com_equipe.replace("exp09ef1b", "exp06ef1b").replace("9EF", "6EF")
    assert not any("equipes-regras" in x["resumo"] for x in cp.validar_prd(ja))


# --------------------------------------------------------------------------- 9. eventos e 10. ausências da spec
SPEC_EVENTOS = """# Spec

## 5. Ausências declaradas

| Recurso Ausente | Por que a ausência existe no simulador |
|---|---|
| **Barra de pesquisa textual / busca** | Impede filtrar termos pré-concebidos. |
| **Botão de editar/desfazer postagem após envio** | Protege a irreversibilidade. |

### 9.4 Tabela de eventos

| Verbo | Objeto | Quando dispara | Caminho |
|---|---|---|---|
| `visualizar` | `dm:amara_inicio` | Abertura do modal | Operacional |
| `salvar` | `post:feed` | Marcador | Operacional |
| `<verbo>` | `<namespace:slug>` | molde | — |
"""


def test_evento_da_spec_chega_a_secao_13_com_o_mesmo_verbo_e_objeto():
    """exp01 13/13, exp09 12/12, exp06 12/12, exp04 9/9; a exp07ef1b renomeou os sete objetos
    (`dm:amara_inicio` → `exp07ef1b:dm_amara_inicio`), a exp05ef1b trocou os seis verbos, a exp02em1b os cinco. ⚠️."""
    assert cd.eventos_da_spec(SPEC_EVENTOS) == [("visualizar", "dm:amara_inicio"), ("salvar", "post:feed")]
    renomeado = ("# 13. Eventos\n| EVT | Verbo | Objeto |\n|---|---|---|\n"
                 "| `EVT-001` | `visualizar` | `exp07ef1b:dm_amara_inicio` |\n| `EVT-002` | `scored` | `post:feed` |\n")
    achados, conta = cd.conferir_eventos(renomeado, SPEC_EVENTOS)
    assert _codigos(achados) == {"evento-perdido": "atencao"} and conta == {"eventos_spec": 2, "eventos_no_prd": 0}
    assert "`visualizar dm:amara_inicio`; `salvar post:feed` (o objeto está lá, com outro verbo)" in achados[0]["resumo"]
    certo = renomeado.replace("`exp07ef1b:dm_amara_inicio`", "`dm:amara_inicio`").replace("`scored`", "`salvar`")
    assert cd.conferir_eventos(certo, SPEC_EVENTOS) == ([], {"eventos_spec": 2, "eventos_no_prd": 2})
    # fora de tabela também vale, com verbo e objeto na mesma linha da §13
    assert cd.conferir_eventos("# 13. Eventos\n- `visualizar dm:amara_inicio` e `salvar post:feed`.\n",
                               SPEC_EVENTOS)[0] == []


def test_ausencia_declarada_da_spec_chega_ao_prd():
    """Das 37 ausências das sete specs, 19 estão no PRD (60% dos radicais numa linha) e 18 não — 12 faltam mesmo, 6
    estão com outras palavras. ⚠️, e o resumo pede a ausência com as palavras da spec. A exp09ef1b declara em lista
    («* **Sem edição de mensagens anteriores:** …»)."""
    assert cd.ausencias_da_spec(SPEC_EVENTOS) == ["Barra de pesquisa textual / busca",
                                                  "Botão de editar/desfazer postagem após envio"]
    prd = "# 3. Não-objetivos\n- **Sem barra de pesquisa textual nem busca:** o feed é orgânico.\n"
    achados, conta = cd.conferir_ausencias(prd, SPEC_EVENTOS)
    assert _codigos(achados) == {"ausencia-perdida": "atencao"} and conta["ausencias_no_prd"] == 1
    assert "«Botão de editar/desfazer postagem após envio»" in achados[0]["resumo"]
    lista = "## 5. Ausências declaradas\n\n* **Sem edição de mensagens anteriores:** preserva a trilha.\n"
    assert cd.ausencias_da_spec(lista) == ["Sem edição de mensagens anteriores"]
    # a chave de copy não é frase: `e0.rotulo.botao_editar_postagem` não cobre a ausência do botão de editar
    so_chave = prd + "- *Chaves:* `e0.rotulo.botao_editar_postagem`, `e0.rotulo.desfazer_envio`.\n"
    assert cd.conferir_ausencias(so_chave, SPEC_EVENTOS)[1]["ausencias_no_prd"] == 1


def test_os_achados_novos_cabem_no_envelope_e_voltam_ao_redator():
    """O relatório do modo `prd` do `RastroCheckAgent` volta ao redator no loop do PRD: todo achado tem dono
    `prd-writer`, e a lista das chaves faltantes vai inteira."""
    ruim = PRD_NOVA.replace(MANIFESTO_BOM, "") + "\n| **RF-019** | Operar offline com cache local. | P0 |\n"
    r = cd.validar(ruim, {"spec_missao": SPEC_EVENTOS})
    assert {"manifesto-ausente", "capacidade-inexistente", "evento-perdido", "ausencia-perdida"} <= set(_codigos(r["achados"]))
    for a in r["achados"]:
        assert set(a) == {"severidade", "codigo", "etapa", "agente_responsavel", "resumo"}
        assert a["agente_responsavel"] == "prd-writer" and a["etapa"] == "dev"
    rel = cd.relatorio(r, "exp09ef1b")
    assert "| Eventos da spec com o mesmo verbo e objeto na §13 | 0 | 2 |" in rel
    assert extrair_envelope(rel)["status"] == "bloqueado"


@pytest.mark.parametrize("vazio", ["", "   "])
def test_texto_vazio_nao_quebra(vazio):
    """O PRD vazio é `prd-vazio` em `cobertura_design.validar`; aqui só não pode estourar."""
    assert {a["codigo"] for a in cp.validar_prd(vazio)} <= {"manifesto-ausente"}
