# Donos e etapas — quem fecha cada pendência

Um marcador de lacuna (`[ABERTO — dono: …]`, `[LACUNA — dono: …]`, `[NEEDS CLARIFICATION: …]`,
`RS-n pendente`, 🔵) só vira impedimento quando **existe alguém capaz de fechá-lo dentro da
esteira**. Essa é a regra inteira, e ela decide se uma execução sai 🔴 ou 🟡.

Este arquivo é a **fonte única**: o classificador de `tools/rastro.py` lê a cerca JSON abaixo, e
os prompts que escrevem marcadores leem a prosa. Enquanto as duas metades viviam separadas, o
prompt mandava escrever um marcador que o gate reprovava — e a lista de tokens acumulou cinco
correções datadas, uma por sessão quebrada.

## As sete etapas, e o que cada uma significa

| Dono | Bloqueia? | Quem de fato fecha |
|---|---|---|
| `input` | **sim** | quem abriu o briefing |
| `produto` | **sim** | os agentes de produto (núcleo, seções, revisor, gate estrutural, spec) |
| `design` | **sim** | os agentes de design (jornada, fluxo, copy, CAA, telas, ambiente) |
| `dev` | **sim** | os agentes de dev (handoff, brief de assets, PRD) |
| `plataforma` | não (🟡) | o monorepo `plataforma-unooria`: ADR, componente de DS, ponte `@edu/ui` |
| `externo` | não (🟡) | gente de fora: coordenação, rede, especialista, jurídico, encarregado de dados |
| `humano` | não (🟡) | um ato que só pessoa pratica: homologar, ratificar, licenciar, nomear autoria, **decidir produto** |

**A pergunta que decide** não é "de que assunto isto trata?", é **"quem precisa agir para
fechar?"**. Um marcador sobre telemetria cujo dono é o encarregado de dados é `externo`, não
`dev` — nenhum agente da esteira resolve. Um marcador que diz "produto precisa decidir o teto" é
`humano`, não `produto`: `produto` são os *agentes* de produto, e nenhum deles decide por você.
Ratificar é o mesmo ato que homologar — o PO confirma um valor —, e até 25/09/2026 só o segundo
era reconhecido: `[ABERTO — dono: produto: Ratificação formal do teto de texto…]` barrou o PRD da
exp04ef1b enquanto três `Homologação…` na mesma lista passavam como decisão humana.

## Cada etapa cobra o que é dela

O rastro de lacunas roda em três pontos, e cada um só **bloqueia** pelas lacunas cujo dono é a
etapa que está rodando — onde ainda há quem as feche:

- **Produto**, no loop da spec: lacuna de `input` ou de `produto` na spec volta para quem a
  escreveu; decisão do PO (`humano`) aparece no semáforo do parecer de produto.
- **Design**, no fim da etapa: lacuna de `design` na spec e nos documentos de design.
- **Dev**, antes do PRD: lacuna de `dev` no handoff e no brief de assets.

Lacuna de uma etapa **seguinte** fica registrada (🟡, «fica para a etapa dela»). Lacuna de uma
etapa **anterior**, num documento dela, também (🟡, «de etapa anterior»): ela já passou pelo
rastro e pelo parecer da dona, e a etapa de agora não reescreve aquele documento. Uma lacuna de
etapa anterior escrita num documento **desta** etapa continua bloqueando: foi esta etapa que a
escreveu.

**Lacuna fechada pelo fechamento de lacunas (D0).** Quando uma decisão `[D0-n]` do bloco 13 fecha
um `[ABERTO — …]` da spec, o D0 registra o marcador, literal, no mapa célula → D0 do fim do bloco
13, e o rastro deixa de contá-lo — desde que o `[D0-n]` exista no bloco 13. Mapa (ou a marca
antiga ` — Resolvido em [D0-n]`) que aponta para um D0 inexistente continua aberto.

## Como escrever o marcador

Escreva `[ABERTO — dono: <um dos sete>: <o que falta>]`. Se o dono é uma pessoa ou um papel
(PO, coordenação, jurídico), a etapa é `humano` ou `externo` — e aí o marcador **não trava a
esteira**, aparece no dossiê com `precisa_humano: true` e segue.

Cinco marcadores têm dono fixo, porque o prompt que os cria já sabe quem fecha:

- `RS-n pendente` → **`humano`**. É pedido ao Gate 0 ou ao PO que o fechamento de lacunas
  registrou; não existe loop que devolva isso a um agente.
- `[PARÂMETRO — a definir por produto: …]` e `[PROPOSTA — validar com PO: …]` → **`humano`**. São o
  contrato que produto deixou para o PO decidir: o de acordo de produto lista cada um no cartão, e a
  resposta entra no one-pager e na spec do Gate 0 como «<valor> — PO, parecer de <data>». Até lá
  ficam 🟡, pendência do PO — nenhum agente os fecha, nem o D0.
- `[verificar no repositório]` → **`plataforma`**. Os agentes não têm o monorepo por desenho,
  só as cópias sincronizadas: o marcador é instrução para quem codifica. Oito ou mais no mesmo
  documento é outra história — aí o documento não conhece o gabarito, e isso é achado de `dev`.
- 🔵 → **`externo`**. Validação curricular ou de fonte que a esteira não tem como conferir.

## O contrato lido por código

```json
{
  "etapas": {
    "humano": {
      "bloqueia": false,
      "severidade": "decisao_humana",
      "quem_fecha": "Uma pessoa, num ato que nenhum agente pratica: homologar código curricular, nomear autoria, licenciar pictograma, decidir um parâmetro de produto. Inclui PO, PM e 'decisão de produto pendente'.",
      "tokens": [
        "homologa",
        "homologar",
        "ratifica",
        "ratificar",
        "editorial",
        "autoria",
        "autor e revisor",
        "nomear autor",
        "licen[çc]a",
        "direitos de uso",
        "validar com o time",
        "aprova[çc][ãa]o human",
        "po",
        "pm",
        "product owner",
        "decis[ãa]o de produto",
        "respons[áa]vel de produto",
        "time de produto"
      ]
    },
    "externo": {
      "bloqueia": false,
      "severidade": "atencao",
      "quem_fecha": "Alguém fora da esteira: coordenação da escola, rede parceira, especialista curricular, consultoria, jurídico, encarregado de dados (DPO).",
      "tokens": [
        "coordena(ção|cao|dor|dora|dores|doras)",
        "rede parceira",
        "escola parceira",
        "designer instrucional",
        "especialista",
        "assessor",
        "assessoria",
        "parecerista",
        "consultor",
        "time pedag[oó]g[a-z]*",
        "externo",
        "externa",
        "cliente",
        "secretaria",
        "jur[ií]dico",
        "dpo",
        "rede escolar",
        "rede de ensino",
        "semana letiva",
        "est[uú]dio",
        "calend[áa]rio letivo",
        "calend[áa]rio",
        "implanta[çc][ãa]o",
        "respons[áa]vel de dados",
        "dad",
        "encarregad[oa] de dados",
        "parceir[oa]s?",
        "entre redes",
        "\\bef\\d{2}(?!co)[a-z]{2}\\d{2}\\b",
        "\\bem13(?!co)[a-z]{2,3}\\d{2}\\b"
      ]
    },
    "plataforma": {
      "bloqueia": false,
      "severidade": "atencao",
      "quem_fecha": "O monorepo `plataforma-unooria`: ADR nova, componente de design system a publicar, ponte `@edu/ui`, porta de dev. A esteira não tem o repositório — só as cópias em `references/plataforma/`.",
      "tokens": [
        "plataforma",
        "adr",
        "design-system",
        "storybook",
        "infra",
        "ponte",
        "@edu/ui",
        "componente do ds",
        "componente de ds",
        "design system"
      ]
    },
    "dev": {
      "bloqueia": true,
      "severidade": "bloqueio",
      "quem_fecha": "Os agentes de dev desta esteira: handoff-dev, brief-assets, prd-writer.",
      "tokens": [
        "handoff-dev",
        "handoff",
        "brief-assets",
          "assets",
        "banca",
        "tech",
        "arquitetura",
        "dev"
      ]
    },
    "design": {
      "bloqueia": true,
      "severidade": "bloqueio",
      "quem_fecha": "Os agentes de design: jornada, fluxo, copy revisada, CAA, telas, ambiente simulado, fechamento de lacunas.",
      "tokens": [
        "jornada",
        "fluxo",
        "copy",
        "wireframe",
        "caa",
        "ambiente-simulado",
        "ambiente",
        "brief-oficio",
        "briefing de ofício",
        "qa-entregaveis",
          "telas",
        "mermaid",
        "stitch",
        "design"
      ]
    },
    "produto": {
      "bloqueia": true,
      "severidade": "bloqueio",
      "quem_fecha": "Os agentes de produto: núcleo, seções de apoio, revisor, gate estrutural, spec da missão.",
      "tokens": [
        "gate-estrutural",
        "gate estrutural",
        "gate 0",
        "gate0",
        "spec",
        "produto",
        "one-pager",
        "gate-final",
        "gate final",
        "pedag[oó]g[a-z]*",
        "experiencia-aluno",
        "fecha-lacunas"
      ]
    },
    "input": {
      "bloqueia": true,
      "severidade": "bloqueio",
      "quem_fecha": "Quem abriu o briefing — o solicitante da missão.",
      "tokens": [
        "input",
        "briefing",
        "insumo",
        "solicitante"
      ]
    }
  },
  "ordem_precedencia": [
    "humano",
    "externo",
    "plataforma",
    "dev",
    "design",
    "produto",
    "input"
  ],
  "marcadores": {
    "rs_pendente": "humano",
    "parametro": "humano",
    "proposta": "humano",
    "verificar_repositorio": "plataforma",
    "a_validar": "externo"
  },
  "slugs_roteaveis": {
    "ambiente": "ambiente-simulado",
    "ambiente-simulado": "ambiente-simulado",
    "assets": "brief-assets",
    "brief-assets": "brief-assets",
    "brief-oficio": "brief-oficio",
    "brief_oficio": "brief-oficio",
    "brief-de-oficio": "brief-oficio",
    "caa": "caa",
    "copy": "copy-ptbr-revisao",
    "copy-ptbr": "copy-ptbr-revisao",
    "copy-ptbr-revisao": "copy-ptbr-revisao",
    "fecha-lacunas": "fecha-lacunas",
    "fluxo": "fluxo",
    "gate-estrutural": "gate-estrutural",
    "handoff": "handoff-dev",
    "handoff-dev": "handoff-dev",
    "jornada": "jornada",
    "lacunas": "fecha-lacunas",
    "spec": "spec-missao",
    "spec-missao": "spec-missao",
    "telas": "telas",
    "wireframe": "telas",
    "wireframes": "telas"
  }
}
```
