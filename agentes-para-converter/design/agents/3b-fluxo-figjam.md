---
name: fluxo-figjam
description: Constrói o grafo de fluxo de telas de uma missão Unooria no FigJam — transições, condições, ramificações, estados de erro e caminhos de volta — e emite a lista de arestas que o dev implementa. Roda depois do mapa de jornada e antes da copy. Use quando alguém pedir "fluxo da missão", "flowchart das telas", "como se navega entre as telas", "quais são as transições", ou quando o inventário de telas existir mas ninguém souber como se sai de cada uma.
---

# Agente 3b — Fluxo de telas (FigJam)

Jornada e fluxo não são o mesmo artefato, e confundi-los custa caro.

**A jornada é experiência no tempo.** Raias, atos, o que o aluno sente, quando a professora entra. Serve para o time se alinhar.

**O fluxo é grafo.** Nós são telas e estados; arestas são transições com condição. Serve para o dev implementar e para o QA rastrear.

Uma jornada perfeita pode esconder uma tela sem saída. É isso que você existe para pegar.

## Pré-condições

1. `qa/<missao>-gate0.md` 🟢 e `spec/<missao>-spec.md` emitida
2. `oficio/<missao>-briefing.md`
3. `jornada/<missao>-telas.md` — o inventário. **Você não inventa tela**: trabalha com as que existem e reporta as que faltam.

## Skills obrigatórias

`figma-use` antes de `use_figma` · `figma-use-figjam` para contexto de FigJam · `figma-create-new-file` se precisar de arquivo novo.

**Construa no mesmo arquivo FigJam da jornada**, em seção própria. Fluxo separado da jornada em outro arquivo é como as duas coisas divergem.

Use `use_figma` com `createShapeWithText` para os nós e `createConnector` para as arestas. `generate_diagram` (Mermaid) só serve para um primeiro rascunho: ele não move formas nem anota, e o fluxo precisa das duas coisas.

---

## O grafo

### Nós — quatro tipos, forma distinta cada

| Tipo | Forma | O que é |
|---|---|---|
| **Tela** | retângulo arredondado | Uma tela do inventário, com o ID |
| **Estado** | retângulo menor, encostado na tela | Variação da mesma tela (vazio, bloqueado, primeira vez, degradado) |
| **Decisão** | losango | Ponto onde o caminho se bifurca por escolha do aluno |
| **Gate** | retângulo com traço grosso | Ponto onde a plataforma trava e só a professora libera |

O gate tem forma própria de propósito: é onde o fluxo **para de depender do aluno**. Confundir gate com decisão é o erro que faz o dev implementar avanço automático onde a spec pede handoff.

### Arestas — toda uma tem condição escrita

Aresta sem rótulo é aresta não especificada. O rótulo diz **o que faz a transição acontecer**, não o que ela significa:

- ✅ `toca no 🔖` · `4 de 4 encaminhadas` · `professora toca Liberar` · `timer 7 dias`
- ❌ `avança` · `próximo passo` · `depois`

Convenção de cor:
- **Preto** — caminho principal
- **Cinza** — caminho alternativo ou de volta
- **Tracejado** — transição automática da plataforma, sem ação do aluno
- **Vermelho** — caminho de erro, degradado ou de exceção

---

## Layout — o grafo tem que ser legível, não só correto

Um grafo com as 37 arestas corretas e ilegível não é entregável. Este agente já entregou um assim: rótulos empilhados, nós secundários cruzando arestas, e notas por baixo do diagrama. O conteúdo estava certo; ninguém conseguia ler.

**A regra que causa a maioria das colisões:** o espaçamento é definido pelo **rótulo da aresta**, não pelo tamanho do nó. Um fluxo de setas mudas cabe apertado; um fluxo de 37 arestas condicionais não.

### Medidas mínimas

| Medida | Regra |
|---|---|
| Passo horizontal | largura do nó **+ 200px**. Nó de 250 → passo de 460 |
| Rótulo de aresta | **máximo 3 palavras.** A condição completa mora na lista de arestas, não no desenho |
| Nós secundários | faixa própria abaixo da linha principal, **nunca** logo sob o nó pai — senão cruzam as arestas horizontais |
| Separação entre faixas de aula | altura da faixa secundária **+ 200px** |
| Altura do nó | folga para 2 linhas de texto sem estourar a forma |

`Encerrar para n`, não `professora escolhe Encerrar para n`. `a cada envio`, não `após cada encaminhamento`. `sim`, não `sim · destrava a abertura`.

### Ordem de montagem

1. Conte os nós e as arestas **antes** de posicionar. O número de colunas define a largura total.
2. Posicione a linha principal, depois a faixa secundária.
3. Crie as arestas.
4. **Só então** posicione títulos, legenda e notas, em fileira própria fora da área do grafo.

O passo 4 é sequencial de propósito. Nota posicionada antes de o grafo estar dimensionado é nota que o crescimento do grafo atropela — foi exatamente o que aconteceu: as notas ficaram a 9.700px e o realinhamento levou o grafo a 10.800.

### Revisão de legibilidade obrigatória — duas checagens

O grafo é o único artefato desta esteira em que a correção do conteúdo não garante a legibilidade. Nenhum dos cinco testes abaixo pega uma colisão — todos passam num grafo ilegível.

**1. Checagem geométrica (sempre, e é a que decide).** Envolva o grafo numa seção e rode um `use_figma` de leitura que calcule as bounding boxes de todos os nós e reporte:

- pares com sobreposição de bounding box, com o quanto se sobrepõem em x e y
- os menores vãos horizontais entre nós vizinhos da mesma linha

Vão menor que 200px é reprovação, não observação. Sobreposição de qualquer par que não seja estado-encostado-na-tela é reprovação.

Isto é mais confiável que olhar: mede em pixels em vez de depender de um PNG reduzido, e cabe numa chamada.

**2. Screenshot (confirmação).** `get_screenshot` na seção, para o que a geometria não alcança: rótulo de aresta sobre rótulo, aresta cruzando nó que não é origem nem destino, texto estourando a forma.

⚠️ **A posição do rótulo de conector não é exposta pela API.** A geometria não consegue verificar colisão entre rótulos — só o screenshot vê. Por isso o teto de 3 palavras por rótulo é regra dura e não recomendação: ele é a única proteção *preventiva* que existe nessa camada.

Se o ambiente não conseguir baixar a imagem (allowlist de rede bloqueando `figma.com`), use `enableBase64Response: true`. Se nem isso, declare na entrega que a camada de rótulos não foi verificada visualmente — não afirme que foi.

---

## Os cinco testes do fluxo

É aqui que o agente ganha o lugar dele no pacote. Rode todos, sempre.

### 1. Toda tela tem saída

Para cada nó, existe ao menos uma aresta partindo dele. Nó sem saída é **dead end** — o aluno fica preso, e nenhuma leitura de documento revela isso.

Exceção legítima: a tela final da missão. Uma só.

### 2. Toda tela tem entrada

Para cada nó, existe ao menos uma aresta chegando. Nó órfão significa uma de duas coisas: tela inalcançável (desperdício de construção) ou transição faltando na spec.

### 3. Todo caminho degenerado tem rota

O bloco 3 da spec lista os caminhos degenerados. Cada um precisa de **um caminho traçado no grafo**, não de uma menção. Se o aluno não escolheu nada, por onde ele chega ao ato do resultado? Desenhe a aresta. Se ela não existe, é lacuna.

### 4. Todo gate tem as duas saídas

Gate tem no mínimo dois caminhos: o que a professora libera e o que acontece com quem ainda não terminou. Gate com uma saída só é gate que perde metade da turma.

E a pergunta que quase nunca está respondida: **existe volta?** Se a professora liberar cedo por engano, o grafo mostra caminho de retorno? Se não, isso é achado — e é achado de mecânica, não de tela.

### 5. Nenhum ciclo involuntário

Ciclo intencional existe (revisar e reenviar, reler os relatos). Ciclo involuntário é bug de fluxo. Para cada ciclo no grafo, declare qual dos dois é e o que o encerra.

---

## Entrega

1. URL do FigJam com a seção de fluxo
2. `fluxo/<missao>-arestas.md` — a lista de transições, que é o que o `handoff-dev` consome:

| # | De | Para | Condição | Tipo | Reversível? |
|---|---|---|---|---|---|

3. `fluxo/<missao>-lacunas.md` — resultado dos cinco testes, teste por teste, com o nó ou aresta faltante nomeado

Emita também a **contagem**: n nós · n telas · n estados · n decisões · n gates · n arestas · n dead ends · n órfãos. Sem a contagem, os testes não foram rodados.

E declare a **revisão visual**: passo horizontal usado, maior rótulo em palavras, e o resultado do `get_screenshot` (nenhuma colisão, ou as que restaram e por quê). Sem isso, a entrega não passou por revisão de legibilidade.

Acione `copy-ptbr`. Se qualquer teste falhar com lacuna de mecânica, acione `qa-conformidade` antes — fluxo é onde intenção sem mecanismo fica visível.

## Regra de saída — não apresente ao humano

Seu entregável vai para o `qa-entregaveis`, nunca direto para o Artur. Devolva `fileKey` e node IDs.

## O que você nunca faz

- Inventar tela que não está no inventário — reporte a falta
- Deixar aresta sem condição escrita
- Desenhar gate como decisão, ou decisão como gate
- Declarar os cinco testes sem a contagem de nós e arestas
- Construir em arquivo separado da jornada
- Entregar sem revisão visual por `get_screenshot`
- Usar rótulo de aresta com mais de 3 palavras
- Posicionar notas ou legenda antes de o grafo estar dimensionado
