---
name: ambientes
description: Registro dos ambientes simulados — seção do design system, versão publicada, e a fronteira entre o que é fixo na biblioteca e o que cada missão possui. Lido por wireframes-figma e jornada-figjam.
sources: [chat]
---

# Ambientes simulados

Cinco ambientes, dezenas de missões. **A biblioteca não é nossa** — cada ambiente é uma **seção do design system**, publicada no `storybook-unooria`. Missão **monta**; a seção **fornece**.

Isto substitui a ideia de "biblioteca de ambiente por missão": não existe biblioteca a construir, existe seção a consumir na versão publicada.

## As seções

| Ambiente | Seção do DS | Versão publicada | Componentes | Missões que usam |
|---|---|---|---|---|
| Instagram | `instanooria` | `[storybook]` | `[storybook]` | exp-01 Instanooria |
| YouTube | `unitube` (ponte `@edu/ui/ds-unootube`, CSS `--uni-*`) | `[storybook]` | `[storybook]` | exp-02 UnooTube |
| ChatGPT | `chatgpt` | `[storybook]` | `[storybook]` | exp-03 unooGPT |
| WhatsApp | `whatsappmobile` (ponte `@edu/ui/ds-whatsapp`, **só tema escuro** — ADR-68) | `[storybook]` | `[storybook]` | exp-06 Rastro do Boato · exp-07 O Eco no Grupo |
| TikTok | `tiktooria` | `[storybook]` | `[storybook]` | — *(existe no DS, **sem ponte em `@edu/ui`**; criar a ponte é pré-requisito declarado)* |

`[storybook]` = preencher a partir de `https://storybook.unooria.com/`. Nome da seção é fato do repositório e está confirmado por DES-01 do gate de dev; versão e inventário de componentes só o storybook dá.

**`tiktooria` é o nome canônico.** TikNooria, UnooTok e NooriaTok em missões anteriores são desvios a corrigir — inclusive em roteiro de podcast já escrito, que é o mais caro.

**Roblox saiu.** Não tem seção de DS e não está em uso. Missão em Roblox reprova em DES-01. Se voltar, volta como seção nova, com componentes a criar no `storybook-unooria`, responsável e prazo declarados **antes** da codificação — nunca como componente criado dentro da experiência.

## Seção que não existe

Missão que precisa de seção ou componente novo **não o cria na experiência** — é a regra de ouro do DS, e violá-la é ❌ em DES-01 e DES-09.

O caminho é: a missão lista os componentes faltantes como **pré-requisito**, com responsável e prazo, e eles chegam por versão publicada antes de a codificação começar. O `wireframes-figma` monta contra a seção; o que não existir nela é pré-requisito declarado, não improviso local.

## A fronteira — um teste, não uma lista

**Isso muda se a missão mudar?**

- Não muda → **seção do DS**. Chrome, posição e ordem das affordances, ícones nativos, proporções, barra de abas, estados de interação padrão, tokens.
- Muda → **da missão**. Conteúdo, ritmo, quais affordances entram em cena e em que etapa, o que é deliberadamente removido, scaffolding, telas de professor.

Caso que não couber nos dois lados é zona de negociação, não improviso: a missão constrói local, marca como candidato, e `aprendizado` decide se sobe quando uma segunda missão pedir o mesmo. Um pedido é exceção; dois é padrão.

## Ausências por ambiente — o que a plataforma real NÃO tem

É markdown, não Figma, e é o que mais reduz achado de fidelidade. Uma tabela por seção, para ninguém "completar" a interface por realismo. **A preencher — é o item mais barato e mais valioso deste arquivo.**

| Seção | Não tem |
|---|---|
| `instanooria` | |
| `unitube` | |
| `chatgpt` | |
| `whatsappmobile` | |
| `tiktooria` | |

## Nomenclatura de slot

Componente da seção vem com os slots de variável do DS. **Não recrie o valor** — a coleção `wireframe-cinza` espelha os mesmos slots (ver `references/wireframe-cinza.md`), e é isso que faz a subida pra alta fidelidade ser troca de coleção.

Se a seção trouxer valor em vez de slot, isso é lacuna a registrar no storybook, não a resolver localmente: wireframe montado sobre valores fixos quebra na troca e vira descarte pela metade.

## Nada da marca dentro do disfarce

Nenhum token, fonte, cor ou componente da seção `unooria` dentro das telas do clone — e vice-versa (DES-13). Os dois escapes conhecidos continuam: tela de contexto antes de entrar e reflexão depois que a simulação fecha, e esses **podem** usar a seção `unooria`.

O mapa de qual seção fala em cada tela é entrega do `copy-ptbr` (coluna `seção` no sheet), porque quem decide quem está falando é quem escreve a fala.
