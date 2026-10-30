# Protótipo em alta fidelidade: Stitch, Paper ou agente de código com o DS real

**Data:** 30/10/2026 · **Status:** estudo, aguarda decisão · **Spike:** `/Volumes/Documentos/Unooria/analises-esteira/2026-10-30/spike-prototipo-hifi/`

## 1. Resumo

1. **Paper fica fora da esteira.** O MCP dele só funciona com o app desktop aberto e um arquivo aberto, segundo a [documentação](https://paper.design/docs/mcp). No Cloud Run não há como rodar isso, mas ele pode servir ao designer, fora da esteira.
2. **O Stitch não resolve a consistência voltando do jeito que era.** A inconsistência vinha da forma como nós o chamamos: cada (tela, estado) era gerada à parte, em paralelo e a partir de texto, sem tela-base. Mesmo bem usado, o Stitch não monta telas com os componentes reais do DS. Ele desenha uma imitação, que o dev reescreve depois. Fica como opcional, para explorar a direção visual.
3. **O caminho recomendado é um agente de código que escreve as telas com os componentes React reais do `@unooria/design-system`.** Um empacotador determinístico (esbuild) junta React, o DS, o CSS e as fontes num **único HTML offline**. O spike de hoje provou que isso funciona: uma tela com 7 componentes reais do Instanooria virou um HTML de 316 KB, montado em 113 ms.
4. **Sobre o ADK, a hipótese está certa pela metade.** O que não dá conta é o agente ADK *como usamos hoje*, que devolve o HTML inteiro numa resposta só (`output_key`). Isso esbarra no teto de saída, e o agente não compila nem olha o que fez. Um agente de código (ADK com ferramentas de arquivo, build e captura de tela, ou o SDK do Antigravity) dá conta. O SDK do Antigravity existe e roda em Python ([`google-antigravity` 0.1.23](https://pypi.org/project/google-antigravity/), Alpha, Apache-2.0). Ele traz pronto o ciclo editar → rodar comando → subagentes, mas **não traz navegador**: a captura de tela entra como ferramenta nossa ou por MCP.
5. **Recomendação:** isolar o motor atrás de uma interface (`MotorDeCodigo`) e testar o Antigravity SDK primeiro, com o ADK como plano B. O projeto de trabalho, o build, a casca de revisão, os lints e o juiz são nossos e valem para os dois motores.

## 2. Onde estamos

| Item | Hoje | Evidência |
|---|---|---|
| Protótipo | Lo-fi em cinza, 9 tokens (`wireframe-cinza`), HTML escrito à mão pelo LLM numa resposta só | `prompts/design/079_prototipo.md`, `A079Prototipo` com `output_key="prototipo_html"` |
| Tamanho | Cerca de 170 KB por missão, com 49 quadros na exp09ef1b. São uns 45 a 50 mil tokens de saída, perto do teto de uma resposta. | `output/20261028-154851-session_f4caa98a/design/08-prototipo.html` |
| Casca de revisão | Também escrita pelo LLM a cada rodada (trilho, painel, rodapé, navegação) | prompt 079, «Estrutura da casca» |
| Stitch | Desligado desde 22/10 (cota e inconsistência) | memória `stitch-desligado-por-padrao`, PR #61 |
| Causa da inconsistência | `generate_screen_from_text` por (tela, estado) em paralelo, com um `DESIGN.md` de 9 cinzas. Não havia tela-âncora, edição a partir dela nem DS real. | `tools/stitch_geracao.py:226-255` |
| DS real | `@unooria/design-system` 0.2.26, em React, 12 marcas com CSS por marca e fontes embutidas | `storybook-unooria/dist`; `GEMINI.md`/`AGENTS.md` com 1.302 linhas de regras; telas de exemplo em `stories/<marca>/telas/` |
| Contêiner | Já tem Node 20 (proxy do Stitch) | `Dockerfile` |

Capturas no spike: `atual.png` é o lo-fi de hoje e `tela.png` é a tela com o DS real.

## 3. As três opções

### 3.1 Stitch com consistência visual

**O que o SDK oferece hoje** ([README](https://github.com/google-labs-code/stitch-sdk/blob/main/README.md), `@google/stitch-sdk` 0.3.5):
- design system por projeto: `createDesignSystem`, `update` e `apply(telas)`;
- edição de tela existente: `screen.edit`;
- variações: `screen.variants`, com `creativeRange REFINE` e `aspects` controlados;
- `getHtml()`.

**Como ficaria consistente:**
1. Criar o design system do projeto com os tokens **reais** da seção, tirados dos CSS do `dist`, e não os cinzas.
2. Gerar **uma tela-âncora por seção e por ator** e esperar a aprovação.
3. Derivar as demais em sequência com `edit` ou `variants(REFINE)` a partir da âncora, nunca do zero em paralelo.
4. Rodar `apply` no fim, porque relatos de terceiros dizem que telas antigas não se atualizam sozinhas.

**Limites que continuam:**
- Quem desenha é o LLM, e terceiros relatam que trocar a fonte no design system não chega às telas ([MindStudio](https://www.mindstudio.ai/blog/what-is-design-md-google-stitch)).
- Não há componente real: o dev reconstrói tudo.
- A cota é de cerca de 400 créditos por dia, sem plano pago (dado de [terceiros](https://www.banani.co/blog/google-stitch-pricing-and-credits)), contra cerca de 50 telas por rodada mais os refazeres.
- O erro `CLARIFICATION_REQUIRED` pode parar a geração com uma pergunta.
- O adaptador ADK do SDK é só para TypeScript.

**Veredito:** só como exploração visual, opcional e com poucas telas-âncora. Não serve como fonte das telas.

### 3.2 Paper (paper.design)

- **A favor:** o canvas é HTML e CSS de verdade, e o MCP tem ferramentas como `write_html` e `get_screenshot` (lista vinda de [terceiros](https://abduzeedo.com/node/89066)).
- **Contra:** o MCP exige o app desktop aberto, em `127.0.0.1:29979`, e não há modo headless nem API pública ([docs](https://paper.design/docs/mcp)). Uma revisão de terceiros o chama de "open alpha". O Free tem 100 chamadas MCP por semana; o Pro custa US$ 16 a 20 por editor por mês ([preços](https://paper.design/pricing)).

**Veredito:** descartado para a esteira. Fica como ferramenta do designer para retocar o HTML gerado, se o time quiser.

### 3.3 Agente de código com o DS real (recomendado)

**A ideia:** o LLM não escreve o HTML final. Ele escreve **TSX por tela**, usando só componentes do DS, num projeto de trabalho que nós montamos. O build e a casca de revisão são código nosso e determinístico.

```
workspace/ (montado pela esteira)
  dados/missao.json         ← jornada, estados, copy, one-pager por etapa, ficha de interação (o código injeta)
  casca/                     ← trilho, painel, rodapé, navegação, moldura: CÓDIGO FIXO, não é o LLM que escreve
  telas/E2-ALU-01.padrao.tsx ← o agente escreve um arquivo por (tela, estado)
  ds/ → dist/ da versão do DS usada pela missão (base-plataforma)
  build.mjs                  ← esbuild → protótipo.html único (JS + CSS + fontes inline)
```

**Ciclo do agente, por lote de telas:**
1. Lê os dados da tela e a tela de exemplo do Storybook da seção (`stories/<marca>/telas/`), que serve de modelo.
2. Escreve o TSX.
3. `run_command`: `node build.mjs` mostra os erros de tipo e de import.
4. Tira uma captura de tela por (tela, estado) com Chrome headless.
5. Corrige pelo que viu e pelos lints, e repete.

**Gates determinísticos, fora do LLM:**
- Todo (tela, estado) da jornada tem um arquivo e um quadro `data-screen-id`/`data-estado`. É o mesmo contrato de hoje.
- O lint de import só aceita `@unooria/design-system/<marca>` e o React. Componente local, hex, `style` com cor e fonte remota reprovam, como manda a regra do DS: componente só do DS (ADR-68/72).
- Todo texto visível existe no sheet de copy. Reaproveita o teste do texto atual.
- O build passa e a página carrega sem erro no console.

**Juiz visual multimodal**, com as capturas: compara a tela com o exemplo do Storybook e com a ficha de interação. Ele aponta, mas não reprova sozinho.

**Por que a consistência vem pela construção:** um botão é o `Button` do DS em toda tela, e o espaçamento e a tipografia vêm dos tokens. O que pode variar é a composição, e o juiz e o exemplo do Storybook cuidam disso.

**Ganhos que valem por si:**
- **O TSX por tela é quase o código de produção.** As experiências são bundles Vite e React que só usam componentes do DS. O dev parte das telas prontas em vez de reescrevê-las, e o PRD passa a apontar para arquivos reais.
- **Cada tela é um arquivo**, então o refazer pontual troca um arquivo só. Isso casa com a «correção pontual» (PR #52) e com «refazer preserva a versão anterior».
- **A casca sai do LLM.** Isso acaba com a classe de defeito de 61 telas empilhadas da exp03em1b e libera contexto para as telas.

## 4. O motor: SDK do Antigravity ou ADK

| | Antigravity SDK (`google-antigravity`) | ADK com ferramentas nossas |
|---|---|---|
| Existe? | Sim. 0.1.23 de 28/10/2026, Alpha, Python, com wheels para Linux | Sim. Já é a nossa stack (`google-adk>=2.8`) |
| Ciclo de código pronto | `view_file`, `create_file`, `edit_file`, `run_command`, `start_subagent`, `finish` ([tools](https://antigravity.google/docs/sdk/tools)) | Precisamos escrever as ferramentas de arquivo, de comando e o loop |
| Navegador e captura | **Não vem no SDK.** O `/browser` é recurso da IDE. Entra como ferramenta Python nossa ou como Chrome DevTools MCP. | Ferramenta nossa (Playwright ou Chrome headless). O `ComputerUseToolset` está em preview e não é necessário. |
| Autenticação | `GEMINI_API_KEY`, Vertex ou ADC ([overview](https://antigravity.google/docs/sdk/overview)) | A de hoje |
| Riscos | API alfa muda rápido, sem guia de servidor, e o handler de aprovação de shell precisa de uma lista fechada de comandos | Mais código nosso e o mesmo risco de qualidade do modelo |
| Observabilidade na esteira | A investigar: precisa entrar na conversa com as etapas, no rastro e no fluxograma | Nativa (callbacks, `output_key`, LoopAgent) |

O Gemini CLI headless foi substituído pelo Antigravity CLI nos planos de consumidor em 18/06/2026 ([docs](https://geminicli.com/docs/cli/headless/)). O `agy -p` tem um bug de travar sem TTY e o uso em servidor com conta de consumidor está em dúvida, então fica fora. O Jules é assíncrono e amarrado a PR no GitHub, então também não serve.

**Recomendação:** criar a interface `MotorDeCodigo.gerar(workspace, tarefa) -> relatório`. A primeira implementação é o Antigravity SDK, e a segunda, de reserva, é um `LlmAgent` ADK com as mesmas ferramentas. Os gates e o build são os mesmos para as duas, e a escolha final sai do spike, com números.

## 5. Plano em fases

| Fase | Entrega | Critério de saída |
|---|---|---|
| **F0 · spike do motor** (1 a 2 dias) | Antigravity SDK no contêiner, 10 telas de uma missão real (exp09ef1b), com captura de tela e lints | Build verde, 10 de 10 quadros, 0 import fora do DS, tempo e custo medidos. Mesma tarefa no ADK como comparação. |
| **F1 · kit do protótipo** | `tools/prototipo_hifi/`: template do projeto, `build.mjs`, casca fixa, injeção de `missao.json`, captura por quadro | Casca e build cobertos por teste. O protótipo de hoje continua igual. |
| **F2 · gates** | Lint de import, lint de cobertura `data-screen-id`, teste do texto, console limpo, juiz visual | Os mutantes em `tests/mutantes/` pegam tela faltando, hex, componente local e texto inventado |
| **F3 · na esteira** | `A079PrototipoHifi`, atrás de um controle na barra lateral como o do Stitch, com o lo-fi de reserva | Uma missão de ponta a ponta no Cloud Run dev, com a revisão humana abrindo o HTML |
| **F4 · dev** | O PRD e o kit de codificação apontam para os TSX por tela | O dev parte das telas e não as reescreve |
| **F5 · Stitch (opcional)** | Âncoras por seção com o design system real, só para explorar a direção | Decisão depois da F3 |

## 6. Pontos de atenção levantados no spike

- **Fontes:** a `material-symbols-rounded` tem 5,1 MB. Embutida inteira, ela incha o HTML. É preciso fazer subset dos glifos usados (pyftsubset) ou não embutir os ícones que a seção não usa. Open Sans e Inter têm cerca de 84 KB por peso, o que é aceitável.
- **O agente precisa ver a tela.** No spike, `TopBar` dentro de `PhoneFrame` deixou um vão duplo da barra de status, porque faltava `withStatusBarInset={false}`. Lint de texto não pega isso; só a captura de tela pega.
- **Distribuição do DS no Cloud Run:** a esteira lê a versão do DS pela `base-plataforma`, mas o `dist/` não está no contêiner. Há duas saídas: publicar o `dist` da versão no bucket da base-plataforma, ou instalar o pacote no build com um token do registro.
- **Imagens:** fotos e capas entram por prop no DS, e o pacote não as embute. O protótipo precisa de placeholders ou do `tools/ilustracoes.py`.
- **Logo dos clones:** o `Logo` do Instanooria desenha a palavra «Instagram». Convém confirmar com o time de marca antes de levar isso a quem revisa.

## 7. Decisões que dependem de você

1. **O hi-fi substitui o lo-fi ou vem depois do «de acordo» do design?** A sugestão é vir depois: o lo-fi segue como gate rápido de estrutura, e o hi-fi gasta mais tokens e tempo.
2. **Pode autorizar o spike F0 com o Antigravity SDK** (alfa, chave Gemini do projeto dev)?
3. **Stitch:** aposentar de vez ou guardar para a F5?
4. **Distribuição do DS:** pelo bucket ou pelo registro npm?
