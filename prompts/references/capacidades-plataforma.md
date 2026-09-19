---
name: capacidades-plataforma
description: O que uma missão pode pedir ao aparelho do estudante, o que a plataforma concede hoje e o que exige extensão declarada. Lido pelo gate estrutural, pela spec, pelo handoff e pelo redator do PRD; o gate `ManifestoCheck` aplica a mesma tabela.
sources: [apps/hub/components/ExpFrame.tsx, apps/api/src/experiencias/contrato-de-rotas.ts, references/plataforma/versao-lida.json]
---

# Capacidades do aparelho — o que a missão pode pedir

A experiência roda dentro de um `iframe` com `sandbox`, no hub. Duas coisas diferentes controlam o que ela consegue fazer:

- **Tokens de sandbox** (`allow-scripts`, `allow-forms`…), ligados por experiência pelo campo `permissoes` do manifesto;
- **Permissions Policy** (o atributo `allow` do iframe), hoje uma lista **fixa** concedida a todas: `autoplay`, `fullscreen`, `clipboard-write`.

**A missão não precisa se limitar ao que existe hoje.** Quando a mecânica exige uma capacidade que a plataforma ainda não concede, ela é declarada assim mesmo, marcada como **pré-requisito de plataforma**, e o PRD sai 🟡 (`aprovado-com-pendencias-de-plataforma`) com o caminho de implementação escrito. Quem constrói a missão implementa a extensão junto. O que não se faz é inventar a capacidade em silêncio, nem desenhar a missão como se ela já existisse.

## 1. Nativo — já funciona, não declare nada

| A missão quer | Como funciona hoje |
|---|---|
| **Tocar áudio** (narração, podcast, efeito), inclusive começando sozinho | `<audio>` comum. `autoplay` já é delegado ao iframe; sem essa delegação um `play()` cross-origin falharia em silêncio |
| **Tocar vídeo** (story, clipe, depoimento) | `<video>` comum, mesma delegação |
| **Tela cheia** | `fullscreen` já delegado |
| **Copiar texto para a área de transferência** | `clipboard-write` já delegado |
| **Rolar, arrastar, tocar, digitar, escolher** | HTML comum |
| **Áudio e vídeo pesados** (≥ 2 MB) | Vão ao bucket `-assets` com `midia-externa.json`, nunca ao bundle (ADR-63) |

**Não declare `autoplay`, `fullscreen` nem `clipboard-write` em `permissoes`.** O vocabulário do manifesto é fechado e validado por Zod mais CHECK: um valor fora dele derruba o `PUT /experiencias/:expId` do job de deploy com 400, **depois** de os bundles já terem subido, com a `versaoAtiva` ainda na versão velha.

## 2. Concedido por declaração — três valores, hoje

`permissoes` no manifesto aceita exatamente estes:

| Valor | Para quê | Sem ele |
|---|---|---|
| `forms` | qualquer `<form>`, incluindo o `Composer` do design system | o navegador bloqueia o submit **em silêncio**; a criança aperta enviar e nada acontece |
| `downloads` | entregar arquivo ao computador (ferramentas do professor) | download bloqueado mudo, e o `a.click()` volta como se tivesse funcionado |
| `pointer-lock` | prender o ponteiro (jogo em primeira pessoa) | `requestPointerLock()` é ignorado |

## 3. Extensão declarada — a missão pede, a plataforma cresce

Capacidade real do navegador que a plataforma **ainda não concede**. Declare no manifesto assim mesmo: o gate marca como pendência de **plataforma** (🟡), e o PRD leva o pré-requisito com o caminho técnico.

| A missão quer | Valor a declarar | Natureza |
|---|---|---|
| **Gravar a voz do estudante** (justificativa falada, recado, mensagem de voz) | `microphone` | Permissions Policy |
| **Usar a câmera** (foto, selfie, leitura de QR) | `camera` | Permissions Policy |
| **Gravar vídeo** (depoimento, vlog, story) | `camera` e `microphone` | Permissions Policy |
| **Gravar a tela** | `display-capture` | Permissions Policy |
| **Localização** | `geolocation` | Permissions Policy |
| **Sensores de movimento** (jogo por inclinação) | `accelerometer`, `gyroscope`, `magnetometer` | Permissions Policy |
| **Manter a tela acesa** | `screen-wake-lock` | Permissions Policy |
| **Compartilhar pelo aparelho** | `web-share` | Permissions Policy |
| **Vídeo em janela flutuante** | `picture-in-picture` | Permissions Policy |
| **Instrumento MIDI** | `midi` | Permissions Policy |
| **Realidade aumentada ou virtual** | `xr-spatial-tracking` | Permissions Policy |

### O caminho de implementação (é o que vai ao PRD)

Toda extensão desta lista custa os mesmos cinco pontos, mais o que a captura de mídia exige à parte:

1. `apps/api/src/experiencias/contrato-de-rotas.ts` — o valor entra em `PERMISSOES_DE_IFRAME`.
2. **Migration nova** que troca o CHECK da coluna `experiencias.permissoes` (padrão: a migration que acrescentou `forms`). O CHECK e o Zod precisam concordar, e a divergência só aparece como 500 no CI.
3. `apps/hub/components/ExpFrame.tsx` — **aqui está a mudança de desenho**: hoje o `sandbox` é derivado do manifesto, mas o `allow` é uma string fixa (`autoplay; fullscreen; clipboard-write`). Microfone, câmera e afins são Permissions Policy, então o `allow` precisa passar a ser derivado do manifesto também. É a primeira vez que isso acontece; a ADR registra a decisão.
4. `apps/api/tests/permissoes-de-iframe.spec.ts` — cobra Zod e CHECK juntos.
5. As rotas do hub que renderizam o `ExpFrame` direto precisam **repassar** `permissoes` (as três rotas de professor não repassavam, e a permissão declarada não tinha efeito nenhum — ADR-76).

**Captura de mídia do estudante cobra mais três coisas, e elas não são técnicas:**

6. **Componente de gravação no design system.** Não existe hoje em nenhuma seção. Nasce no `storybook-unooria` e chega por versão; enquanto não chega, compensação local marcada.
7. **Contrato de dados, no bloco 9 da spec.** Voz e imagem de criança são dado pessoal, e a regra da casa é que nome, voz e imagem **não** são coletados por padrão. Se a missão os coleta, a spec declara: onde a mídia é gravada (tabela própria com `escola_id` e RLS, arquivo no bucket com caminho não adivinhável), quanto tempo fica, **quem lê** (só o professor da escola, nunca rota de gestor, nunca telemetria, nunca Clarity), e o que acontece quando a família não autoriza. Sem isso a missão não passa pela banca de dados.
8. **Degradação sem a capacidade.** Toda missão que captura mídia precisa funcionar sem ela: Chromebook sem microfone, criança que não autoriza, escola que bloqueia. O caminho alternativo é parte da mecânica, não um aviso de erro.

## 4. Decisão contrária registrada — não é lacuna, é desenho errado

Aqui a plataforma **já decidiu** não fazer assim, e existe alternativa. Escrever isso no handoff ou no PRD é erro de desenho, não pedido de extensão; o gate bloqueia e a correção é trocar pela alternativa.

| Se aparecer | A alternativa |
|---|---|
| WebSocket, `socket.io`, "tempo real", `hub:pause` como canal de sala | Tabela `expNNefNb_gates_turma` lida por polling HTTP curto (ADR-93/94). Cloud Run não sustenta WebSocket de aplicação |
| Componente de interface local (botão, campo, diálogo, aba, etiqueta) | Pedido no `storybook-unooria` mais compensação local marcada |
| Chamada a provedor de IA fora de `apps/api/src/ai` | O módulo de IA, com quota |
| IA aberta em tempo real na tela do estudante | Preparação docente com curadoria antes da aula, e banco curado como fallback |
| Redis, fila nova, biblioteca de estado global | Postgres e o Pub/Sub que já existe |
| `localStorage` para token, `targetOrigin: "*"` | O SDK |

## 5. Como declarar na spec

No bloco 0, `permissoes` leva **tudo** que a missão precisa, inclusive o que ainda não existe:

```
- `permissoes: [forms, microphone]`
```

E o bloco 9 declara o destino da mídia capturada. O gate lê os dois: `forms` passa, `microphone` vira pendência de plataforma com este documento anexado ao PRD, e a missão segue.

## Regra de manutenção

A tabela da seção 2 espelha `PERMISSOES_DE_IFRAME` no contrato da api, e a da seção 1 espelha o atributo `allow` do `ExpFrame`. Quando a plataforma conceder uma capacidade nova, ela sai da seção 3 e entra na 2 — e as listas em `tools/rastro.py` mudam junto. Reconferir a cada sincronização de `references/plataforma/`.
