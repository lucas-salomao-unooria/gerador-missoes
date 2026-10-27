---
name: pronto-prototipo
description: Definição de pronto do protótipo (D8) — o preâmbulo e a seção `prototipo` de pronto.md, só o que o agente de protótipo conta. Gerado; não edite à mão.
sources: [pronto.md]
---

# Definição de pronto — protótipo

> **Gerado automaticamente** de `pronto.md` por `scripts/gerar_pronto_prototipo.py`. Não edite à mão: edite a seção `prototipo` de `pronto.md` e regenere. SHA-256 da fonte (preâmbulo e seção): `4911c826b3c00682d6820a38911508da5af70886bcdfc01fb85c6c00779ace7f`.

Higiene técnica, não ofício. Todo item fecha em **zero**. Item acima de zero **retém a entrega** — o agente corrige antes de acionar o próximo, não depois de tomar ticket.

Isto não é uma dimensão de auditoria. É a lista que impede o gate de ofício de gastar rodada com achado que uma contagem pega.

**Declare a contagem no envelope** (`pronto` em `references/contrato-saida.md`). Contagem ausente equivale a contagem falhada: sem ela ninguém sabe se o zero foi verificado ou presumido.

## prototipo

Conta-se no arquivo HTML, não no relatório sobre ele. O lint e a esteira tocam o arquivo.

| Conta | Zero significa |
|---|---|
| Quadro sem `data-screen-id` ou sem `data-estado` | A esteira conta quadro por atributo: ID só em comentário, trilho ou rodapé não é tela |
| (ID, estado) da cobertura sem quadro e fora da lista «o que ficou fora» | Cobertura incompleta (teste 2): nunca "completo" com quadro faltando |
| Texto visível fora do sheet de copy, ou marcador `[[…]]` que não seja `[[LACUNA — dono]]` declarado no relatório | Invenção ou placeholder não resolvido (teste 1) |
| Hexadecimal fora dos nove tokens dentro de um quadro | Uma exceção abre todas (teste 3) |
| Escolha da missão com alternativa ou distrator faltando, ou com marca de gabarito (`[Correto]`, `[Distrator …]`, nível do Canal B) | O protótipo entregaria a resposta |
| Botão, aba ou affordance que a spec declara ausente | O que o ambiente não tem não aparece, nem "por realismo" |
| Tela `pico` com mais elementos que uma vizinha | Teste 4: a hierarquia invertida bloqueia (O1) |
| Tela de congelamento com affordance além da saída declarada da demo | Teste 5: a saída é concessão da demo, não a trava |
| Etapa sem texto no painel, ou sem a fonte declarada | Teste 6 |
| Coluna de grid ou item de flex sem `min-width: 0`, ou coluna de texto sem quebra de palavra | Rolagem horizontal (teste 7) |
| Momento scriptado com tempo diferente do da spec | Teste 8 |
| Alvo acionável abaixo de 64×64 px (88×88 na projeção) ou vão menor que 16 px | Mesma régua da D4a do QA, com ou sem camada CAA |
| Animação sem regra `prefers-reduced-motion` | Gatilho vestibular que a criança não desliga |
| Mais de um quadro visível ao mesmo tempo | A navegação parece quebrada (exp03em1b: 61 telas empilhadas) |
| `localStorage`, `sessionStorage` ou recurso externo (CDN, fonte remota, import) | O arquivo abre offline, com duplo clique, sem guardar estado |
| Tela `E0-PROF-01…05` ausente do trilho do professor | O preparo é obrigatório e navegável |
| Instrução fixa dentro do quadro (e não em elemento irmão), ou com estado diferente da Seção 3b | A exceção à DES-13 vale só para a camada do hub |
| Instrução fixa sem recolher por botão e por `Esc`, ou com alvo abaixo de 64×64 px | O estudante não consegue liberar a tela |
