---
name: ambiente-e-minijogo
description: Como produto decide a classe do ambiente (app clonado | mini-jogo), o ambiente e, no mini-jogo, as regras e as fases do jogo — o que o D9 decidia no design até 24/10/2026. Lido pelo núcleo narrativo (P0a), pelo especificador da spec (P5) e pelo passo de completude (P5b).
sources: [prompts/design/067_ambiente_simulado.md (até 24/10/2026), docs/planos/2026-10-23-produto-dono-do-contrato.md (PR 8, decisão D8), tools/ambiente.py]
---

# Classe, ambiente e mini-jogo — decisões de produto

Desde 24/10/2026 (PR 8 do plano «Produto dono do contrato», decisão D8) **a classe do ambiente, o ambiente e as regras e as fases do mini-jogo são decididos em produto**. Até ali o D9 (ambiente simulado, no design) decidia a classe quando a spec calava, criava ambiente novo e a casca do jogo, e a jornada escrevia as fases: produto criado no design, que o PO nunca via. O D9 agora só lê o que a spec decidiu e escreve a ficha de UI; se a spec cala, ele devolve a produto. Um código confere cada passo (`tools/ambiente.py`).

## O que fica no bloco 0 da spec

- `secao_ds` — o ambiente (a seção do DS). A lista e a tradução do briefing estão em `ambientes.md`; a seção que o briefing fixa é trava.
- `classe_ambiente: app-clonado | mini-jogo` — uma linha, logo depois da `secao_ds`. Mini-jogo é sempre `secao_ds: minijogo:<nome>`; toda outra seção é app clonado. Um gate confere que as duas concordam. Spec de antes de 24/10/2026, sem a linha, é lida pela `secao_ds`.

## Regra de ouro: ambiente existente antes de ambiente novo

Vale nas duas classes. Criar só quando a **Passada 1** mostra que nada existente cabe. Um ambiente novo é candidato permanente à lista — então precisa ser tão específico quanto os outros (um app reconhecível, não "uma rede social genérica"; um jogo com regra própria, não "um joguinho") e igualmente montável.

**Passada 1 — cabe numa seção da lista?** Para cada seção de `ambientes.md`, teste os verbos nativos da missão (§6 do one-pager, bloco 4 da spec) e a dinâmica da descoberta central:

| Ambiente | Verbos da missão que ele tem nativamente | Verbos que faltam | Dinâmica cabe? (sim · com escape · não) | Missão irmã no catálogo |

Critérios, nesta ordem: (1) todos os verbos existem no app real e no DS; (2) a descoberta central acontece **dentro** do ambiente, sem escape além dos dois permitidos (contexto antes, reflexão depois); (3) a faixa já usa esse ambiente em missão irmã (continuidade > novidade); (4) verossimilhança: o estudante da faixa reconhece o app. Um passa nos quatro → é ele. Mais de um → o da missão irmã mais próxima na trilha, com a alternativa descartada registrada. Nenhum passa em (1) ou (2) → Passada 1b. Falha só em (3) ou (4) não justifica criar.

## Passada 1b — é caso de mini-jogo? (só anos iniciais)

Antes de criar um app novo, pergunte se a missão pede app nenhum. Existem missões de 1º a 5º ano cuja descoberta não mora em plataforma alguma — e para elas clonar um app é enfiar a criança num ambiente que não tem nada a ver com o que ela vai descobrir.

**Gate de aplicabilidade — as quatro condições valem juntas, ou não é mini-jogo:**

| # | Condição | Fonte | Se falhar |
|---|---|---|---|
| 1 | Faixa **1º–5º ano** | bloco 0 (`series`) | 6º em diante nunca é mini-jogo — o código bloqueia. App clonado |
| 2 | Os verbos são **verbos genéricos de interação** (escolher, comparar, ordenar, juntar, separar, seguir) e **não** verbos de plataforma (publicar, curtir, compartilhar, comentar, seguir alguém, pesquisar) | §6 do one-pager, bloco 4 | Verbo de plataforma exige plataforma. App clonado |
| 3 | A descoberta central **não depende** de reconhecer, habitar ou desconfiar de um app real | §1, bloco 1 | Se a descoberta é sobre o app, o app é o ambiente. App clonado |
| 4 | O eixo de educação digital da missão se sustenta **sem** a casca de plataforma | §2, bloco 11 | App clonado, e a dúvida vai ao PO como `[ABERTO — dono: PO]` |

Registre a tabela preenchida de qualquer forma — no §18 do one-pager e no bloco 12 da spec —, mesmo quando a resposta é "não": quem vem depois precisa saber que foi considerado e por que se descartou.

**Mini-jogo não é recompensa nem intervalo.** Ele carrega a mesma mecânica, as mesmas decisões e a mesma descoberta que um app clonado carregaria. Se você está propondo um jogo porque "criança gosta", pare: isso é enfeite.

## Escolha do PO: ambiente novo e mini-jogo

Ambiente da lista (`ambientes.md`) produto escolhe pela tabela, e a seção que o briefing fixa é trava. **Ambiente novo (`nova:<nome>`) e mini-jogo (`minijogo:<nome>`) são escolha do PO**: se o briefing (ou o one-pager que o PO anexou) não os fixa, escreva a escolha como proposta, numa linha do bloco 0 da spec (e no §0 do one-pager), com a sugestão e a alternativa:

`[PROPOSTA — validar com PO: mini-jogo `minijogo:<nome>` no lugar de app clonado · por quê: <a condição da Passada 1b que nenhuma seção comporta> · alternativa: <a seção existente mais próxima>]`

A proposta vai à lista do *de acordo* de produto (`tools/fechar_contrato.py`), e o PO aceita ou recusa. Spec que fixa ambiente novo ou mini-jogo sem a proposta, sem decisão gravada do PO e sem o briefing é bloqueada pelo gate do manifesto; se mesmo assim chegar ao *de acordo*, o cartão abre o item sozinho. Recusada, a spec volta com um ambiente da lista.

## Mini-jogo: as regras e as fases são de produto

Quantas fases, em que ordem, a regra de cada uma, o que a vence e o que a perde, e como o progresso aparece são **conteúdo de produto**. Nascem no núcleo (§4 do one-pager, que o P0b copia) e a spec as copia no bloco 2, na subseção «Regras e fases do mini-jogo». A jornada (design) só as copia e diz quais telas cada fase ocupa; regra ou fase que a spec não tem, na jornada, vira proposta ao PO (um gate em código confere).

### A gramática — Super Mario Bros. 3, a gramática, nunca a marca

A referência é **como aquele jogo ensina**, não o que ele mostra. Nada de personagem, sprite, som, nome, moeda, cogumelo, cano ou qualquer coisa reconhecível de jogo comercial — isso é marca de terceiro. As sete regras valem em todo mini-jogo:

1. **Uma ideia nova por fase.** A fase apresenta a ideia num lugar onde errar não custa, repete com variação, e só então cobra. Fase que apresenta duas ideias novas é duas fases mal cortadas.
2. **Fase curta e inteira.** Começa e termina numa sessão. Nada numa fase depende de lembrar do que aconteceu na aula passada.
3. **Mapa de mundo visível.** O progresso é um mapa onde a criança vê onde está, o que já fez e o que vem. Não é barra de progresso, não é porcentagem, não é número.
4. **Aprende jogando, não lendo.** Toda regra nova entra por demonstração animada e primeiro toque guiado. Se a regra só existe escrita, a fase está quebrada para quem não lê — e em 1º–2º isso é todo mundo.
5. **Erro é generoso e reversível.** Perder devolve ao começo **da fase**, nunca ao começo do jogo. Sem vidas que expulsam a criança do jogo, sem "game over" que apaga o que ela fez.
6. **Poder temporário muda o que dá para fazer, não quem a criança é.** Nenhum poder é permanente, nenhum classifica, nenhum fica indisponível para quem errou antes.
7. **O objetivo fica visível o tempo todo.** Criança parada porque não sabe o que a fase quer é falha de desenho, não falta de atenção.

**E uma proibição, que é da plataforma:** nenhum placar entre estudantes, nenhum tempo como medida de mérito, nenhuma estrela ou nota que ordene crianças (8.5 e PED-07).

### Adequação por faixa — o que a BNCC decide e o que não decide

As habilidades são as do contrato de evidência (§12a, bloco 11). O que se adequa à faixa é a **forma do jogo** — o quanto ele exige de leitura, de coordenação e de memória.

| | 1º–2º ano | 3º–5º ano |
|---|---|---|
| Verbo por vez | Um. Um alvo, uma ação | Até dois combinados, se o segundo já foi aprendido sozinho |
| Leitura | **Nenhuma pressuposta.** Regra por demonstração + áudio do personagem-guia | Instrução curta escrita, sempre com ícone e áudio juntos |
| Duração da fase | até ~90 s | até ~180 s |
| Regra nova | Demonstrada **antes de cada** fase que a usa | Demonstrada uma vez; pode ser retomada por ícone |
| Precisão motora | Alvo grande, sem tempo de reação apertado, sem arrastar preciso | Arrastar aceito; ainda sem exigência de reflexo |
| Memória entre fases | Nenhuma | Uma regra pode voltar duas fases depois |

**Cada fase carrega o momento em tela de uma habilidade do §12a.** Fase que não carrega nenhuma é enfeite e sai.

### O formato (one-pager §4 e spec, bloco 2)

```
### Regras e fases do mini-jogo

**Tipo de jogo:** percurso · coleta · ordenação · comparação — e por que este tipo carrega a mecânica

**Regras do jogo** (valem em todas as fases, 3 a 6, como a criança entenderia):
- `R1` <uma frase, verbo no imperativo, sem subordinada>
- `R2` …

| Fase | Nome | Ideia nova | Regra da fase (na voz da criança) | Verbo do jogo | Como vence | Como perde (volta ao começo da fase) | Habilidade (§12a) |
|---|---|---|---|---|---|---|---|
| 1 | <nome> | <uma> | <uma frase> | <verbo> | <condição única e visível> | <condição> | `EF0nCOnn` |

**Como o progresso aparece:** <o mapa de mundo: o que mostra e o que nunca mostra>
**Progressão:** <por que esta ordem — apresenta → varia → cobra>
```

Regra que só vale numa fase não é regra: é a ideia nova daquela fase, e mora na tabela. Fase não é decisão nova por definição; se uma fase pede do estudante uma decisão de **tipo diferente**, ela conta no teto de decisões do §15/bloco 6. Em 1º–2º ano a coluna «Regra da fase» é o texto que o **áudio** fala.

## O que não é de produto (fica com o design)

A **ficha de UI** do ambiente que produto decidiu, no bloco 14 do anexo de design (D9): chrome, navegação, affordances, os verbos nativos com o rótulo literal na tela e o componente do DS que os materializa, o padrão de conteúdo, os estados que a seção já traz, o que a plataforma real não tem — e, para ambiente novo ou mini-jogo, a seção do DS **só com tokens existentes** (o mini-jogo veste a seção `unooria`). As telas de cada fase são da jornada; os frames, das telas.
