"""O PRD contra o design: tela, chave de copy, asset e estado chegam ao PRD por ID (`tools/cobertura_design.py`).

Os documentos daqui reproduzem, em miniatura, o que a auditoria de 07/10/2026 mediu nas sete sessões completas
do bucket. O PRD da exp01ef1b citava 0 das 90 chaves da copy revisada, 1 dos 28 assets V1 do brief e 0 dos 17
estados do contrato da spec; 12 dos 17 RF P0 não tinham critério EARS/Gherkin; `ParametrosDoPreparoExp01ef1bSchema`
era citado sem definição; os KPI-14..17, vindos de `PQ-02..05` marcadas `[PROPOSTA — validar com PO]` na spec,
perderam o marcador; e o resumo trazia «Status dos gates» escrito pelo redator. A exp09ef1b tinha 100 das 104
chaves e uma story por tela — o PRD bom nesses dois pontos, mas sem dizer onde nenhuma chave vive: desde a decisão
do PO de 07/10/2026, a chave vale pelo nome, na story da tela dela, com a coluna «Onde vive», e curinga não cobre.

Nenhum teste lê sessão real: os trechos estão aqui, reduzidos ao que cada conferência precisa.
"""

import json

from agents.callbacks import extrair_envelope
from tools import cobertura_design as cd
from tools.conteudo_aprovado import TITULO_ANEXO

# --------------------------------------------------------------------------- insumos de design e spec
JORNADA = """# Jornada — O Detetive da Foto Misteriosa

## Seção 3 — Inventário de telas

| ID | Etapa | Ator | Peso | Estados |
|---|---|---|---|---|
| `E0-PROF-01` | Preparo | Professor | serviço | padrão |
| `E0-PROF-02` | Preparo | Professor | alta | padrão |
| `E0-PROF-03` | Preparo | Professor | serviço | carregando, sem_saldo |
| `E0-PROF-04` | Preparo | Professor | alta | padrão |
| `E0-PROF-05` | Preparo | Professor | serviço | padrão |
| `E1-ALU-01` | E1 | Estudante | média | padrão |
| `E6-ALU-01` | E6 | Estudante | alta | padrão |
| `E6-ALU-02` | E6 | Estudante | média | padrão |
| `E6-ALU-03` | E6 | Estudante | alta | padrão |

## Seção 4 — Direção
"""

#: (tela da copy, chave) — `Global` é a chave da missão inteira, sem tela do inventário (exp07ef1b, exp09ef1b).
CHAVES_POR_TELA = [
    ("E0-PROF-01", "e0.rotulo.titulo_catalogo"), ("E0-PROF-01", "e0.rotulo.btn_continuar"),
    ("E0-PROF-02", "e0.texto_professor.titulo_preparo"), ("E0-PROF-02", "e0.rotulo.btn_pacote_padrao"),
    ("E0-PROF-02", "e0.texto_professor.ajuda_padrao"), ("E0-PROF-02", "e0.rotulo.btn_gerar_ia"),
    ("E0-PROF-03", "e0.feedback_sistema.gerando_titulo"), ("E0-PROF-04", "e0.rotulo.btn_aprovar"),
    ("E0-PROF-05", "e0.rotulo.btn_liberar_agora"),
    ("E1-ALU-01", "e1.acessibilidade.abrir_pasta"), ("E1-ALU-01", "e1.texto_professor.instrucao_caa"),
    ("E6-ALU-01", "e6.acessibilidade.metodo_fechado"), ("E6-ALU-01", "e6.acessibilidade.metodo_amplo"),
    ("E6-ALU-01", "e6.texto_professor.instrucao_caa"), ("E6-ALU-02", "e6.texto_professor.instrucao_caa_p1"),
    ("E6-ALU-02", "e6.texto_professor.instrucao_caa_p2"), ("E6-ALU-03", "e6.rotulo.btn_finalizar"),
    ("E6-ALU-03", "e6.rotulo.btn_zerar_turma"),
    ("Global", "sys.erro.sem_sinal_aluno"), ("Global", "sys.erro.cota_ia_prof"),
]
CHAVES = [c for _, c in CHAVES_POR_TELA]

COPY = "\n".join([
    "# Copy — O Detetive da Foto Misteriosa (`exp01ef1b`) — passada 2",
    "",
    "## 1. Sheet de strings completo revisado em contexto",
    "",
    "| ID tela | Chave | Tipo | Seção | PT-BR (final) | Palavras |",
    "|---|---|---|---|---|---|",
    *[f"| `{t}` | `{c}` | rótulo de UI | `clone` | Texto {n}. | 2 |" for n, (t, c) in enumerate(CHAVES_POR_TELA)],
    "",
    "## 8. Pronto — contagem por item",
    "",
    "| Item | Contagem |",
    "|---|---|",
    "| Chave fora da convenção `eN.tipo.nome` (ou `sys.tipo.nome` para erros) | 0 |",
])

BRIEF = """# Brief de assets — O Detetive da Foto Misteriosa (`exp01ef1b`)

### Tabela mestre de assets

| ID | Bloco | Tipo | Onde aparece (ID de tela) | V1/V2 | Peso estimado | Destino |
|---|---|---|---|---|---|---|
| `pic-exp01ef1b-01` | Banco Default | ilustração de cena | `E1-ALU-01` | V1 | ~180 KB | Bundle local |
| `pic-exp01ef1b-02` | Banco Default | ilustração de cena | `E6-ALU-01` | V1 | ~420 KB | Bundle local |
| `img-exp01ef1b-03` a `06` | Banco Default | imagem de post | `E6-ALU-02` | V1 | ~200 KB (total) | Bundle local |
| `aud-exp01ef1b-01` | Fixo UI | áudio de podcast | Hub docente | V1 | ~3,2 MB | Bucket `-assets` |
| `ia-exp01ef1b-01` | Sintético IA | texto/persona sintética | `E0-PROF-02` | V2 | ~12 KB | Backend |
"""
ASSETS_V1 = ["pic-exp01ef1b-01", "pic-exp01ef1b-02", "img-exp01ef1b-03", "img-exp01ef1b-04", "img-exp01ef1b-05",
             "img-exp01ef1b-06", "aud-exp01ef1b-01"]

SPEC = """# Spec — O Detetive da Foto Misteriosa v5.2

## 2. Mecanismo por etapa

### Contrato de estados

```
[ESTADO INICIAL]          → GATILHO             → REGRA                  → [ESTADO SEGUINTE]         → RESPONSÁVEL → REVERSÍVEL
E1_ALBUM_FECHADO          → tap:album           → album_id == 'feira'    → E2_RECORTE_INSPECAO       → estudante   → não
E2_RECORTE_INSPECAO       → tap:lupa_zoomout    → pontos >= 2            → E3_APOSTA_TRAVADA_LATCH   → estudante   → não
E3_APOSTA_TRAVADA_LATCH   → sdk:concluir        → confirmação síncrona   → MISSAO_CONCLUIDA_LATCH    → plataforma  → não
QUALQUER_ESTADO           → erro:offline        → perda de conexão       → ERRO_SEM_SINAL_DIEGETICO  → sistema     → sim
```

- **Estados Latch:** a aposta (`E3_APOSTA_TRAVADA_LATCH`) e a conclusão (`MISSAO_CONCLUIDA_LATCH`) nunca reabrem.

## 8. Professora, preparação e parametrização com IA

```typescript
export const ParametrosDoPreparoExp01ef1bSchema = z.object({
  disciplina: z.string(),
  tema: z.string().max(60),
});
```

### 9f. Perguntas de produto desta missão

| ID | Pergunta | Decisão com limiar | Corte | Etapa | Ação | Origem |
|---|---|---|---|---|---|---|
| **PQ-01** | Que proporção escolhe o susto na E3? | < 70% → revisar a arte | turma | E3 | `scored aposta:votar` | one-pager §17 |
| **PQ-02** | Que proporção inspeciona 2 molduras? | < 80% → reforçar o pulso | serie | E4 | `interacted moldura:inspecionar` | [PROPOSTA — validar com PO] |
| **PQ-03** | Que proporção escolhe a foto ampla na E6? | < 60% → reforçar o debate | escola | E6 | `scored metodo:transferencia` | [PROPOSTA — validar com PO] |
"""
ESTADOS = ["E1_ALBUM_FECHADO", "E2_RECORTE_INSPECAO", "E3_APOSTA_TRAVADA_LATCH", "MISSAO_CONCLUIDA_LATCH",
           "ERRO_SEM_SINAL_DIEGETICO"]

STATE = {"jornada_telas": JORNADA, "copy_strings_revisada": COPY, "brief_assets": BRIEF, "spec_missao": SPEC}

ANEXO = f"""
---

# {TITULO_ANEXO}

> Copiado pela esteira, sem reescrita, de «One-pager — O Detetive da Foto Misteriosa».

## Papel do professor e parametrização com IA — one-pager §9

O professor lê `e0.rotulo.btn_pacote_padrao` e ouve `aud-exp01ef1b-01`. Status dos gates: 🟢 aprovado no one-pager.
"""


# --------------------------------------------------------------------------- o PRD da exp01ef1b, em miniatura
PRD_EXP01 = """---
prd_id: PRD-exp01ef1b
status: aprovado-com-pendencias-de-plataforma
---

# 0. Resumo executivo

### Problema
Crianças de 6 anos acreditam que toda foto mostra a verdade inteira.

### Status dos gates
- Gate Estrutural: 🟡 Aprovado com ressalvas.
- BNCC: 🟢 Aprovado.
- Telemetria e Arquitetura: 🟢 Conforme.

# 2. Objetivos e métricas

| KPI | Origem | Pergunta | Decisão com limiar | Corte | Tela | Evento |
|---|---|---|---|---|---|---|
| KPI-13 | PQ-01 | Que proporção escolhe o susto na E3? | < 70% → revisar a arte | turma | `E3-ALU-02` | `EVT-002` |
| KPI-14 | PQ-02 | Que proporção inspeciona 2 molduras? | < 80% → reforçar o pulso | serie | `E4-ALU-02` | `EVT-004` |

# 6. Fluxo e máquina de estados

| Estado inicial | Gatilho | Estado seguinte |
|---|---|---|
| `E1_ALU_01` | `tap:pasta` | `E6_ALU_01` |
| `E6_ALU_01` | `tap:metodo` | `MISSAO_CONCLUIDA` |

# 7. User stories (INVEST)

- **US-01 — Preparo Rápido no Hub (`E0-PROF-01..05`):** Como professor, quero ativar a missão em 2 minutos.
- **US-02 — Investigação (`E1-ALU-01`):** Como estudante, quero abrir o álbum.
- **US-03 — Transferência (`E6-ALU-01`, `E6-ALU-02`):** Como estudante, quero ver a foto inteira.

# 8. Requisitos funcionais

| ID | Título | Descrição (Necessidade) | Prioridade | Rastreio |
|---|---|---|:---:|---|
| **RF-001** | Seleção de Turma | O sistema deve permitir ao professor selecionar a turma no catálogo. | P0 🔒 | US-01 |
| **RF-002** | Aposta Emocional | Ao confirmar o pictograma, o sistema deve trancar a escolha com cadeado. | P0 🔒 | US-02 |
| **RF-003** | Zoom-out Contínuo | O sistema deve executar a animação de 2,5 s sem cortes. | P0 🔒 | US-03 |
| **RF-004** | Podcast Docente | O sistema deve disponibilizar o podcast no Hub. | P1 | US-01 |

### Critérios de aceite em EARS

- **EARS-01 (Zoom-out - RF-003):**
  - *QUANDO* o estudante acionar a lupa, *O SISTEMA DEVE* afastar a imagem em 2.500 ms.

# 10. UX, telas e design

- Podcast: `aud-exp01ef1b-01`.

# 12. Contratos de API

#### `POST /foto-misteriosa/turmas/:turmaId/gerar-conteudo`
- **Body:** `ParametrosDoPreparoExp01ef1bSchema`
""" + ANEXO

# --------------------------------------------------------------------------- um PRD que cobre o design
PRD_BOM = """---
prd_id: PRD-exp01ef1b
slug_experiencia: exp01ef1b
serie: ["1EF"]
unidade: 1
status: aprovado-com-pendencias-de-plataforma
---

# 0. Resumo executivo

### Problema
Crianças de 6 anos acreditam que toda foto mostra a verdade inteira.

> Legenda das tabelas de pendência: 🟢 resolvida · 🟡 com dono · 🔴 sem dono.

# 2. Objetivos e métricas

| KPI | Origem | Pergunta | Decisão com limiar | Corte | Tela | Evento |
|---|---|---|---|---|---|---|
| KPI-13 | PQ-01 | Que proporção escolhe o susto na E3? | < 70% → revisar a arte | turma | `E1-ALU-01` | `EVT-002` |
| KPI-14 | PQ-02 | Que proporção inspeciona 2 molduras? [PROPOSTA — validar com PO] | < 80% → reforçar o pulso | serie | `E6-ALU-02` | `EVT-004` |
| KPI-15 | PQ-03 | Que proporção escolhe a foto ampla na E6? | < 60% → reforçar o debate | escola | `E6-ALU-01` | `EVT-006` |

# 6. Fluxo e máquina de estados

| Estado inicial | Gatilho | Regra | Estado seguinte | Tela |
|---|---|---|---|---|
| `E1_ALBUM_FECHADO` | `tap:album` | `album_id == 'feira'` | `E2_RECORTE_INSPECAO` | `E1-ALU-01` |
| `E2_RECORTE_INSPECAO` | `tap:lupa_zoomout` | pontos ≥ 2 | `E3_APOSTA_TRAVADA_LATCH` | `E6-ALU-01` |
| `E3_APOSTA_TRAVADA_LATCH` | `sdk:concluir` | síncrona | `MISSAO_CONCLUIDA_LATCH` | `E6-ALU-03` |
| `*` | `erro:offline` | perda de conexão | `ERRO_SEM_SINAL_DIEGETICO` | todas |

# 7. User stories (INVEST)

### US-01 — Preparo rápido (`E0-PROF-01..05`)
Como professor, quero ativar a missão em 2 minutos.

| Chave | Onde vive |
|---|---|
| `e0.rotulo.titulo_catalogo` | catálogo/guia do hub |
| `e0.rotulo.btn_continuar`, `e0.rotulo.btn_pacote_padrao` | bundle de textos |
| `e0.texto_professor.titulo_preparo` | bundle de textos |
| `e0.texto_professor.ajuda_padrao` | bundle de textos |
| `e0.rotulo.btn_gerar_ia` | bundle de textos |
| `e0.feedback_sistema.gerando_titulo` | bundle de textos |
| `e0.rotulo.btn_aprovar` | bundle de textos |
| `e0.rotulo.btn_liberar_agora` | bundle de textos |
| `sys.erro.cota_ia_prof` | bundle de textos |

### US-02 — Abrir o álbum (`E1-ALU-01`)
Como estudante, quero abrir o álbum.

| Chave | Onde vive |
|---|---|
| `e1.acessibilidade.abrir_pasta` | aria-label |
| `e1.texto_professor.instrucao_caa` | bundle de textos (`src/lib/textos.ts`) |

### US-03 — Ver a foto inteira (`E6-ALU-01` a `03`)
Como estudante, quero ver a foto inteira.

| Chave | Onde vive |
|---|---|
| `e6.acessibilidade.metodo_fechado` | aria-label |
| `e6.acessibilidade.metodo_amplo` | aria-label |
| `e6.texto_professor.instrucao_caa` | bundle de textos |
| `e6.texto_professor.instrucao_caa_p1` | ficha de evidência no servidor |
| `e6.texto_professor.instrucao_caa_p2` | ficha de evidência no servidor |
| `e6.rotulo.btn_finalizar` | bundle de textos |
| `e6.rotulo.btn_zerar_turma` | bundle de textos |
| `sys.erro.sem_sinal_aluno` | bundle de textos |

# 8. Requisitos funcionais

| ID | Título | Descrição | Prioridade | Rastreio | Critério de aceite (EARS / Gherkin) |
|---|---|---|:---:|---|---|
| `RF-001` | Seleção de Turma | O sistema deve permitir selecionar a turma. | P0 🔒 | US-01 | **QUANDO** o professor escolher a turma, **O SISTEMA DEVE** abrir o recorte da aula. |
| `RF-002` | Aposta Emocional | O sistema deve trancar a escolha. | P0 🔒 | US-02 | **DADO** que o estudante tocou um pictograma, **O SISTEMA DEVE** trancá-lo com cadeado. |
| `RF-003` | Zoom-out Contínuo | O sistema deve animar sem cortes. | P0 🔒 | US-03 | ver o cenário abaixo |
| `RF-004` | Modos de falha | O sistema deve operar sem rede. | P0 | US-03 | **SE** a rede cair, **ENTÃO** o sistema mostra `sys.erro.sem_sinal_aluno`. |

```gherkin
Funcionalidade: RF-003 Zoom-out contínuo
  Cenário: a lupa afasta a foto
    Dado que a aposta está trancada
    Quando o estudante toca a lupa
    Então a foto inteira aparece em 2.500 ms
```

# 10. UX, telas e design

| ID | Etapa | Ator | Assets |
|---|---|---|---|
| `E0-PROF-01` | Preparo | Professor | — |
| `E1-ALU-01` | E1 | Estudante | `pic-exp01ef1b-01` |
| `E6-ALU-01` | E6 | Estudante | `pic-exp01ef1b-02` |
| `E6-ALU-02` | E6 | Estudante | `img-exp01ef1b-03..06` |
| `E6-PROF-01` | E6 | Professor | `aud-exp01ef1b-01.mp3` (bucket `-assets`) |

# 12. Contratos de API

```typescript
export const ParametrosDoPreparoExp01ef1bSchema = z.object({ disciplina: z.string(), tema: z.string().max(60) });
import { DadosDeProgressoSchema } from "@unooria/contratos";
```

- **Resposta do painel:** `PainelDocenteDto { turma: string; niveis: Nivel[] }`.
- **Boot da sessão:** `SessaoDiscenteDto`

| Campo | Tipo | Observação |
|---|---|---|
| `etapa` | `string` | CHECK na migration |

## 17.1 Manifesto `public/experiencia.json`

```json
{
  "id": "exp01ef1b",
  "nome": "O Detetive da Foto Misteriosa",
  "versao": "1.1.0",
  "series": ["1EF"],
  "unidade": 1,
  "produto": "entre-redes",
  "capabilities": ["telemetria", "progresso", "avaliacao"],
  "viewport": {"largura": 1280, "altura": 800},
  "publico": "estudante",
  "permissoes": [],
  "verbos": {"interacted": "tocou numa pista", "scored": "trancou a aposta"}
}
```

# 19. Decisões (ADR) e questões abertas

### Questões abertas
- PQ-03 — o limiar de 60% vem do agente; aguarda o PO.
- [ABERTO — dono: PO: substituir a existente ou outro código] A `exp01ef1b` já está publicada (O Que a Foto Conta).
""" + ANEXO


def _codigos(resultado):
    return {a["codigo"]: a["severidade"] for a in resultado["achados"]}


def _achado(resultado, codigo):
    return next(a for a in resultado["achados"] if a["codigo"] == codigo)


# --------------------------------------------------------------------------- o caso inteiro
def test_prd_como_o_da_exp01_bloqueia_em_cada_conferencia():
    """exp01ef1b real: 0/90 chaves, 1/28 assets, 0/17 estados, 10 linhas de status de gate, 5/17 P0 com critério,
    1 schema sem definição, 4 propostas sem marcador. Aqui, em miniatura, as mesmas oito faltas — e as duas da
    plataforma que o PRD real também tinha: nenhum `experiencia.json`, e a missão já publicada tratada como nova."""
    r = cd.validar(PRD_EXP01, STATE)
    assert r["status"] == "bloqueado"
    assert _codigos(r) == {
        "tela-sem-story": "bloqueio",
        "chave-de-copy-ausente": "bloqueio",
        "asset-fora-do-inventario": "bloqueio",
        "estado-da-spec-sem-mapa": "bloqueio",
        "status-de-gate-no-corpo": "bloqueio",
        "rf-p0-sem-criterio": "bloqueio",
        "schema-indefinido": "bloqueio",
        "proposta-perdida": "atencao",
        "manifesto-ausente": "bloqueio",
        "existente-sem-decisao": "bloqueio",
    }
    c = r["contagens"]
    # a chave e o asset que só o anexo cita não contam: quem os colou foi a esteira
    assert (c["chaves_no_prd"], c["chaves_na_story"], c["chaves_copy"]) == (0, 0, 20)
    assert (c["assets_no_prd"], c["assets_v1"]) == (1, 7)
    assert (c["estados_no_prd"], c["estados_spec"]) == (0, 5)
    assert (c["rf_p0_com_criterio"], c["rf_p0"]) == (1, 3)
    assert c["linhas_status_gate"] == 3
    assert "`E6-ALU-03`" in _achado(r, "tela-sem-story")["resumo"]
    assert "`RF-001`, `RF-002`" in _achado(r, "rf-p0-sem-criterio")["resumo"]
    assert "A spec define `ParametrosDoPreparoExp01ef1bSchema`" in _achado(r, "schema-indefinido")["resumo"]
    assert "`PQ-02`" in _achado(r, "proposta-perdida")["resumo"]
    assert all(a["etapa"] == "dev" and a["agente_responsavel"] == "prd-writer" for a in r["achados"])


def test_prd_que_cobre_o_design_passa_e_o_relatorio_tem_envelope():
    r = cd.validar(PRD_BOM, STATE)
    assert r["achados"] == [] and r["status"] == "aprovado", r["achados"]
    c = r["contagens"]
    assert (c["telas_no_prd"], c["telas_inventario"]) == (9, 9)
    assert (c["chaves_na_story"], c["chaves_com_onde_vive"], c["chaves_por_curinga"]) == (20, 20, 0)
    assert (c["assets_no_prd"], c["estados_no_prd"], c["rf_p0_com_criterio"]) == (7, 5, 4)
    rel = cd.relatorio(r, "exp01ef1b")
    assert "🟢 PRD COBRE O DESIGN" in rel
    envelope = extrair_envelope(rel)
    assert envelope == {"agente": "cobertura-design", "missao": "exp01ef1b", "status": "aprovado", "achados": []}

    ruim = cd.relatorio(cd.validar(PRD_EXP01, STATE), "exp01ef1b")
    env = extrair_envelope(ruim)
    assert env["status"] == "bloqueado" and len(env["achados"]) == 10
    assert "| Chaves da copy na story da tela, pelo nome | 0 | 20 |" in ruim


def test_prd_vazio_bloqueia_e_insumo_ausente_pula_a_conferencia():
    assert cd.validar("", STATE)["achados"][0]["codigo"] == "prd-vazio"
    # sessão sem design (produto parou antes): só o que é do próprio PRD é conferido
    r = cd.validar(PRD_BOM, {})
    assert r["status"] == "aprovado" and r["contagens"]["telas_inventario"] == 0


# --------------------------------------------------------------------------- 1. telas
def test_telas_por_id_com_intervalo_e_na_secao_certa():
    """exp01ef1b: lidas só pelo ID literal, as stories cobriam 12 das 22 telas — as outras vinham por intervalo
    (`E6-ALU-01..05`). exp02em1b: um `### 10. Custos e Quotas de IA` dentro da §9 vinha antes do `# 10. UX`."""
    assert cd.ids_de_tela("`E0-PROF-01..05`") == {f"E0-PROF-0{n}" for n in range(1, 6)}
    assert cd.ids_de_tela("E0-PROF-01 a 03 e E3-ALU-01 a E3-ALU-02") == {
        "E0-PROF-01", "E0-PROF-02", "E0-PROF-03", "E3-ALU-01", "E3-ALU-02"}
    assert cd.ids_de_tela("`E6-ALU-01`–`03`") == {"E6-ALU-01", "E6-ALU-02", "E6-ALU-03"}
    assert cd.ids_de_tela("`E0-PROF-01/03/05`") == {"E0-PROF-01", "E0-PROF-03", "E0-PROF-05"}
    assert cd.ids_de_tela("estado `E1_ALU_01` no fluxo") == {"E1-ALU-01"}
    # número que não é ID não vira intervalo, e etapas diferentes não se misturam
    assert cd.ids_de_tela("E1-ALU-01 a 30 segundos") == {"E1-ALU-01", "E1-ALU-30"}
    assert cd.ids_de_tela("`E1-ALU-01`…`E6-ALU-02`") == {"E1-ALU-01", "E6-ALU-02"}

    prd = ("# 7. User stories\n- `E0-PROF-01..05`, `E1-ALU-01`, `E6-ALU-01..02`\n\n# 9. Requisitos não funcionais\n"
           "### 10. Custos e Quotas de IA\n- custo por chamada\n\n# 10. UX, telas e design\n| ID |\n|---|\n| `E6-ALU-03` |\n")
    assert cd.conferir_telas(prd, JORNADA)[0] == []
    sem_ux = prd.replace("| `E6-ALU-03` |", "| — |")
    achados, conta = cd.conferir_telas(sem_ux, JORNADA)
    assert achados[0]["codigo"] == "tela-sem-story" and conta == {"telas_inventario": 9, "telas_no_prd": 8}


# --------------------------------------------------------------------------- 2. chaves
def _story(titulo: str, chaves, onde: str = "bundle de textos") -> str:
    linhas = [f"### {titulo}", "", "| Chave | Onde vive |", "|---|---|"] + [f"| `{c}` | {onde} |" for c in chaves]
    return "\n".join(linhas) + "\n\n"


def _secao7(*stories: str) -> str:
    return "# 7. User stories\n\n" + "".join(stories) + "# 8. Requisitos funcionais\n"


def _chaves_de(*telas_):
    return [c for t, c in CHAVES_POR_TELA if t in telas_]


STORIES = _secao7(
    _story("US-01 — Preparo (`E0-PROF-01..05`)", _chaves_de(*[f"E0-PROF-0{n}" for n in range(1, 6)])),
    _story("US-02 — Álbum (`E1-ALU-01`)", _chaves_de("E1-ALU-01")),
    _story("US-03 — Foto inteira (`E6-ALU-01` a `03`)", _chaves_de("E6-ALU-01", "E6-ALU-02", "E6-ALU-03", "Global")),
)


def test_chave_pelo_nome_na_story_da_tela_e_a_lista_inteira_das_que_faltam():
    """Decisão do PO de 07/10/2026: toda chave pelo nome, na story da tela dela; sem teto e sem curinga. Antes a
    exp09ef1b (100 das 104, as quatro `sys.*` de fora) era ⚠️ e a exp06ef1b (11 pelo nome e 90 por `e2.rotulo.*`)
    passava; medidas de novo, as duas bloqueiam — a exp06ef1b com 92 chaves fora da story, 90 só por curinga."""
    assert cd.chaves_da_copy(COPY) == CHAVES  # a linha «Chave fora da convenção `eN.tipo.nome`» não é chave
    mapa = cd.chaves_por_tela(COPY)
    assert mapa["e0.rotulo.btn_aprovar"] == {"E0-PROF-04"} and mapa["sys.erro.cota_ia_prof"] == set()
    achados, conta = cd.conferir_chaves(STORIES, COPY)
    assert achados == [] and (conta["chaves_na_story"], conta["chaves_com_onde_vive"]) == (20, 20)

    # uma chave basta para bloquear; a chave sem tela (`Global`) vale em qualquer lugar do corpo
    sem_uma = STORIES.replace("| `sys.erro.cota_ia_prof` | bundle de textos |\n", "")
    achados, _ = cd.conferir_chaves(sem_uma, COPY)
    assert [(a["codigo"], a["severidade"]) for a in achados] == [("chave-de-copy-ausente", "bloqueio")]
    assert "sem tela: `sys.erro.cota_ia_prof`" in achados[0]["resumo"]

    # a lista vai inteira, agrupada pela tela: é dela que o redator precisa na rodada seguinte
    so_e1 = cd.conferir_chaves(_secao7(_story("US-02 — Álbum (`E1-ALU-01`)", _chaves_de("E1-ALU-01"))), COPY)
    resumo = so_e1[0][0]["resumo"]
    assert all(f"`{c}`" in resumo for c in CHAVES if not c.startswith("e1.")) and " e mais " not in resumo
    assert "`E0-PROF-02`: `e0.texto_professor.titulo_preparo`, `e0.rotulo.btn_pacote_padrao`" in resumo

    # a chave de uma tela na story de outra não conta
    na_outra = STORIES.replace("| `e0.rotulo.btn_aprovar` | bundle de textos |\n", "").replace(
        "| `e1.acessibilidade.abrir_pasta` | bundle de textos |\n",
        "| `e1.acessibilidade.abrir_pasta` | bundle de textos |\n| `e0.rotulo.btn_aprovar` | bundle de textos |\n")
    resumo = cd.conferir_chaves(na_outra, COPY)[0][0]["resumo"]
    assert "`E0-PROF-04`: `e0.rotulo.btn_aprovar`" in resumo and "1 aparece no PRD, mas fora da story" in resumo

    # `…instrucao_caa_p1` não cita `…instrucao_caa`: a chave mais curta é outra
    so_p1 = STORIES.replace("| `e6.texto_professor.instrucao_caa` | bundle de textos |\n", "")
    assert "`E6-ALU-01`: `e6.texto_professor.instrucao_caa`" in cd.conferir_chaves(so_p1, COPY)[0][0]["resumo"]

    # curinga não cobre — o relatório conta quantas o PRD só cobria assim
    por_grupo = STORIES.replace(_story("US-02 — Álbum (`E1-ALU-01`)", _chaves_de("E1-ALU-01")),
                                "### US-02 — Álbum (`E1-ALU-01`)\n\n*Chaves:* `e1.*`.\n\n")
    achados, conta = cd.conferir_chaves(por_grupo, COPY)
    assert achados[0]["codigo"] == "chave-de-copy-ausente" and conta["chaves_por_curinga"] == 2
    assert "2 delas o PRD só cobre por curinga" in achados[0]["resumo"]


def test_onde_vive_preenchido_e_no_vocabulario_do_gabarito():
    """Nenhuma das sete sessões dizia onde a chave vive — a exp09ef1b listava as chaves em prosa («*Chaves:* `a`,
    `b`»). «Onde vive» é bundle de textos, ficha de evidência no servidor, catálogo/guia do hub ou aria-label."""
    em_prosa = STORIES.replace("| Chave | Onde vive |", "| Chave | Observação |")
    achados, conta = cd.conferir_chaves(em_prosa, COPY)
    assert [(a["codigo"], a["severidade"]) for a in achados] == [("chave-sem-onde-vive", "bloqueio")]
    assert (conta["chaves_na_story"], conta["chaves_com_onde_vive"]) == (20, 0)

    vazia = STORIES.replace("| `e1.acessibilidade.abrir_pasta` | bundle de textos |", "| `e1.acessibilidade.abrir_pasta` | — |")
    fora = STORIES.replace("| `e1.acessibilidade.abrir_pasta` | bundle de textos |",
                           "| `e1.acessibilidade.abrir_pasta` | no código |")
    assert "`E1-ALU-01`: `e1.acessibilidade.abrir_pasta`" in cd.conferir_chaves(vazia, COPY)[0][0]["resumo"]
    assert "«no código»" in cd.conferir_chaves(fora, COPY)[0][0]["resumo"]
    for onde in ("aria-label", "ficha de evidência no servidor", "catálogo/guia do hub", "`src/lib/textos.ts`"):
        assert cd.conferir_chaves(STORIES.replace("| bundle de textos |", f"| {onde} |"), COPY)[0] == []


def test_a_story_no_formato_de_lista_e_agrupada_por_titulo():
    """A §7 da exp01ef1b é uma lista (`- **US-03 — … (`E1-ALU-01`, `E2-ALU-01`):**`); a de outras, títulos `###`
    dentro de grupos `## 7.1 Estudante`. A story é o item, ou o título do nível que traz tela ou `US-`."""
    lista = ("- **US-02 — Álbum (`E1-ALU-01`):** Como estudante, quero abrir o álbum.\n\n"
             "  | Chave | Onde vive |\n  |---|---|\n  | `e1.acessibilidade.abrir_pasta` | aria-label |\n"
             "  | `e1.texto_professor.instrucao_caa` | bundle de textos |\n"
             "- **US-03 — Foto (`E6-ALU-01`):** Como estudante, quero ver a foto.\n")
    blocos = cd.blocos_de_story(lista)  # o corpo da §7, sem o título dela
    assert [ids for ids, _ in blocos] == [{"E1-ALU-01"}, {"E6-ALU-01"}]
    conta = cd.conferir_chaves("# 7. User stories\n\n" + lista, COPY)[1]
    assert (conta["chaves_na_story"], conta["chaves_com_onde_vive"]) == (2, 2)

    agrupada = "## 7.1 Professor\n\nAs telas `E0-PROF-01` a `E0-PROF-05`.\n\n" + _story(
        "US-04 — Curadoria", []).replace("### US-04 — Curadoria\n", "### US-04 — Curadoria\n- *Tela:* `E0-PROF-04`\n")
    assert [ids for ids, _ in cd.blocos_de_story(agrupada)] == [
        {"E0-PROF-01", "E0-PROF-02", "E0-PROF-03", "E0-PROF-04", "E0-PROF-05"}, {"E0-PROF-04"}]


# --------------------------------------------------------------------------- 3. assets
def test_assets_v1_do_brief_por_id_com_intervalo_e_extensao():
    """exp01ef1b: 1 dos 28 V1 no PRD. exp06ef1b: a célula `img-exp06ef1b-17` a `48` são 32 fotos — com teto de
    intervalo de tela, só as pontas entravam (73 V1 no total)."""
    assert cd.assets_v1(BRIEF) == ASSETS_V1  # `ia-…` é V2 e fica de fora
    grande = BRIEF.replace("`img-exp01ef1b-03` a `06`", "`img-exp01ef1b-17` a `48`")
    assert len([a for a in cd.assets_v1(grande) if a.startswith("img-")]) == 32

    texto = "`pic-exp01ef1b-01`, `pic-exp01ef1b-02`, `img-exp01ef1b-03` a `06` e o arquivo `aud-exp01ef1b-01.mp3`"
    assert cd.conferir_assets(texto, BRIEF)[0] == []
    achados, conta = cd.conferir_assets(texto.replace("`img-exp01ef1b-03` a `06`", "`img-exp01ef1b-03`"), BRIEF)
    assert achados[0]["codigo"] == "asset-fora-do-inventario" and achados[0]["severidade"] == "bloqueio"
    assert conta == {"assets_v1": 7, "assets_no_prd": 4}


# --------------------------------------------------------------------------- 4. estados
def test_estados_da_spec_nos_tres_formatos_e_com_a_cerca_em_volta():
    """Os formatos das sete specs: cerca com `→` (exp01), tabela com `CONCLUIDO` sem sublinhado e «Estado anterior»
    em prosa (exp02em1b), lista em minúsculas com `·` (exp04). A spec da exp09ef1b chegou embrulhada em
    ```markdown — sem desembrulhar, o contrato era bloco de código e os 18 estados sumiam."""
    assert cd.estados_da_spec(SPEC) == ESTADOS  # QUALQUER_ESTADO e a prosa de baixo não entram; o gatilho também não

    tabela = """### Contrato de estados

| Estado inicial | Gatilho | Regra | Estado seguinte | Responsável |
|---|---|---|---|---|
| `NAO_INICIADO` | Aluno clica em "Iniciar" | Missão liberada | `BRIEFING_LIDO` | Estudante |
| `CASO_TRANSFERENCIA` | Submissão do texto | ≥ 150 caracteres | `CONCLUIDO` | Estudante |
| `*` (qualquer) | Queda de rede | Perda de conectividade | `ERRO_CONEXAO` | Sistema |
| `ERRO_CONEXAO` | Reconexão | Recupera o último estado | Estado anterior | Sistema |

* **Estados latch:** `NOTA_SUBMETIDA`, citado só na prosa (`ESTADO_3` para `ESTADO_4`).
"""
    assert cd.estados_da_spec(tabela) == ["NAO_INICIADO", "BRIEFING_LIDO", "CASO_TRANSFERENCIA", "CONCLUIDO",
                                          "ERRO_CONEXAO"]
    minusculas = """### Contrato de estados

```
ESTADO INICIAL: e1_desafio_aberto
- e1_desafio_aberto · toque em [Explorar Mesa] · slot_count == 3 · e2_mesa_livre · estudante · reversivel: nao
- e2_mesa_livre · alocar materia · slots_preenchidos == 3 · e3_prancheta_pronta · estudante · reversivel: sim
- * · reconexao/F5 detectado · snapshot restaurado · [estado_salvo] · sistema · reversivel: sim
```
"""
    assert cd.estados_da_spec(minusculas) == ["e1_desafio_aberto", "e2_mesa_livre", "e3_prancheta_pronta"]

    embrulhada = "```markdown\n" + SPEC + "\n```\n"
    r = cd.validar("# 6. Fluxo\n" + " ".join(ESTADOS), {"spec_missao": embrulhada})
    assert r["contagens"]["estados_spec"] == 5 and "estado-da-spec-sem-mapa" not in _codigos(r)


def test_estado_esquecido_e_ressalva_e_outra_maquina_bloqueia():
    """exp04ef1b 20/21 e exp07ef1b 10/11 → ⚠️ (um estado esquecido). exp01ef1b 0/17 e exp06ef1b 1/11 → ⛔: a §6
    trocou o contrato por IDs de tela e estados `ST_*` que a spec não tem. O nome vale sem caixa (enum do CHECK)."""
    quase = " ".join(e.lower() for e in ESTADOS[:-1])
    achados, conta = cd.conferir_estados(quase, SPEC)
    assert achados[0]["severidade"] == "atencao" and conta["estados_no_prd"] == 4
    outra = "`E1_ALU_01` → `ST_FEED_CARREGANDO` → `E2_RECORTE_INSPECAO`"
    assert cd.conferir_estados(outra, SPEC)[0][0]["severidade"] == "bloqueio"


# --------------------------------------------------------------------------- 5. status de gate
def test_status_de_gate_nas_tres_formas_e_sem_falso_positivo():
    """As três formas das sete sessões: seção «Status dos gates» (exp01, exp04, exp06, exp07), rótulo numa linha
    (exp09, exp02em1b) e bloco `gates:` no frontmatter (exp05, exp07, exp02em1b) — 63 linhas, todas status."""
    rotulo = "# 0. Resumo\n- **Status dos gates:** Estrutural 🟢, BNCC 🟢, Banca de Dev 🟡 (apto com ressalvas)\n"
    frontmatter = "---\nprd_id: x\ngates:\n  estrutural: 🟢\n  lacunas: 🔴\n---\n\n# 0. Resumo\n"
    assert len(cd.linhas_de_status_de_gate(rotulo)) == 1
    assert [n for n, _ in cd.linhas_de_status_de_gate(frontmatter)] == [4, 5]
    assert len(cd.linhas_de_status_de_gate(PRD_EXP01)) == 3

    limpo = "\n".join([
        "# 0. Resumo",
        "> Legenda: 🟢 conforme · 🟡 com ressalva · 🔴 bloqueado.",
        "### Status dos gates",
        "Publicado pela esteira em `diagnostico-execucao.md`; o PRD não repete.",
        "# 19. Questões abertas",
        "| ID | Dono | Situação |",
        "|---|---|---|",
        "| PEND-01 | design | 🟡 com dono e prazo |",
        "- Banca de dev pediu o DDL na §11 — feito 🟢",
    ]) + ANEXO
    assert cd.linhas_de_status_de_gate(limpo) == []
    assert cd.conferir_status_de_gate(limpo) == ([], {"linhas_status_gate": 0})


# --------------------------------------------------------------------------- 6. RF P0
def test_rf_p0_sem_criterio_e_os_lugares_onde_o_criterio_pode_estar():
    """exp01ef1b: 12 dos 17 P0 só com a descrição «O sistema deve…»; os 5 com critério estavam no bloco EARS abaixo
    da tabela. exp05ef1b: `DADO … O SISTEMA DEVE` é critério. exp07ef1b: a coluna se chama «Pri.»."""
    achados, conta = cd.conferir_rf_p0(cd.corpo_do_prd(PRD_BOM))
    assert achados == [] and conta == {"rf_p0": 4, "rf_p0_com_criterio": 4}  # tabela, DADO, Gherkin na cerca, SE…ENTÃO

    abreviada = """| ID | Título | Pri. | Critérios de Aceite (EARS / Gherkin) |
|---|---|---|---|
| `RF-001` | Homologação | P0 | o professor aprova e a turma recebe |
| `RF-002` | Feed | P1 | — |
"""
    achados, conta = cd.conferir_rf_p0(abreviada)
    assert achados[0]["codigo"] == "rf-p0-sem-criterio" and "`RF-001`" in achados[0]["resumo"]
    assert conta == {"rf_p0": 1, "rf_p0_com_criterio": 0}  # P1 não é cobrado


# --------------------------------------------------------------------------- 7. schemas
def test_schema_citado_sem_definicao():
    """exp01ef1b: `ParametrosDoPreparoExp01ef1bSchema` só como «Body» → ⛔ (a spec o define). exp09ef1b:
    `EstadoSessaoDto` só o nome → ⛔; `ParametrosPreparoExp09Schema` (disciplina, tema, …) → ⚠️. exp02em1b:
    «validado por `PacoteSimulacaoChatGPTSchema`: Perspectiva A, Perspectiva B…» → ⚠️."""
    achados, conta = cd.conferir_schemas(cd.corpo_do_prd(PRD_BOM), SPEC)
    assert achados == [] and conta == {"schemas_citados": 4, "schemas_definidos": 4}  # const, import, inline, tabela

    texto = """- **Resposta:** `EstadoSessaoDto`. Idempotente.
- **Entrada:** `ParametrosPreparoExp09Schema` (disciplina, tema, assuntos, contexto?, foco?).
- `pacote`: JSONB validado por `PacoteSimulacaoChatGPTSchema`: Perspectiva A, Perspectiva B e caso judicial.
- **Entrada:** `PacoteConteudoExp09Schema` (com edições manuais se houver).
"""
    achados, conta = cd.conferir_schemas(texto, SPEC)
    sev = {a["severidade"]: a["resumo"] for a in achados}
    assert "`EstadoSessaoDto`, `PacoteConteudoExp09Schema`" in sev["bloqueio"]
    assert "`ParametrosPreparoExp09Schema`, `PacoteSimulacaoChatGPTSchema`" in sev["atencao"]
    assert conta == {"schemas_citados": 4, "schemas_definidos": 0}


# --------------------------------------------------------------------------- 8. propostas
def test_proposta_da_spec_continua_marcada_no_prd():
    """exp01ef1b: `PQ-02..05` [PROPOSTA] na spec viraram KPI-14..17 sem o marcador. O mesmo nas exp04, exp06 e
    exp09 (3 cada). Vale o marcador na linha, a seção de questões abertas, ou o intervalo marcado."""
    assert cd.propostas_da_spec(SPEC) == ["PQ-02", "PQ-03"]
    assert cd.conferir_propostas(cd.corpo_do_prd(PRD_BOM), SPEC)[0] == []

    intervalo = "| KPI-14..15 | PQ-02..03 | [PROPOSTA — validar com PO] |"
    assert cd.conferir_propostas(intervalo, SPEC)[0] == []
    no_changelog = "# 22. Histórico de revisões\n- PQ-02 e PQ-03 entraram como KPI-14 e KPI-15.\n"
    achados, conta = cd.conferir_propostas(no_changelog, SPEC)
    assert achados[0]["codigo"] == "proposta-perdida" and achados[0]["severidade"] == "atencao"
    assert conta == {"propostas_spec": 2, "propostas_no_prd": 2, "propostas_marcadas": 0}
    # o que o PRD nem cita não é proposta perdida — é assunto de outra conferência
    assert cd.conferir_propostas("# 2. KPIs\n- KPI-13 | PQ-01", SPEC) == (
        [], {"propostas_spec": 2, "propostas_no_prd": 0, "propostas_marcadas": 0})


def test_achados_cabem_no_envelope_que_a_esteira_le():
    """O despacho de retrabalho lê `agente_responsavel`; o diagnóstico, `etapa` e `severidade`."""
    r = cd.validar(PRD_EXP01, STATE)
    for a in r["achados"]:
        assert set(a) == {"severidade", "codigo", "etapa", "agente_responsavel", "resumo"}
        assert a["severidade"] in ("bloqueio", "atencao")
    json.dumps(r, ensure_ascii=False)  # serializável para o estado da sessão
