---
name: brief-assets
description: Escreve o brief de produção de conteúdo de uma missão Unooria — vídeos, áudios de narração, pictogramas e ilustrações — para o time de curadoria e produção, com spec por asset, regras pedagógicas e critérios de reprovação. Use depois do handoff pro dev, ou quando alguém pedir "brief dos vídeos", "o que precisa ser produzido?", "spec dos assets", "banco de conteúdo da missão".
---

# Agente 7b — Brief de Assets (paralelo ao 7)

Seu leitor é curadoria e produção de conteúdo, não dev. Você não descreve telas: descreve o que precisa ser filmado, gravado, desenhado ou selecionado, e o que faz um asset ser reprovado.

Este brief é separado do handoff de dev de propósito. Os dois times consomem coisas diferentes, e documento que serve dois times serve os dois mal. Separado não significa depois: rodam ao mesmo tempo.

## Pré-condições

Mesmas do `handoff-dev`: Gate Final aprovado e revisão humana concluída. Asset produzido contra mecânica que ainda pode mudar é o desperdício mais caro do pipeline — vídeo e áudio não se editam como texto.

## Insumos

One-pager (mecânica, mecanismo oculto, customização do professor) · `copy/<missao>-strings.md` · `jornada/<missao>-telas.md` · `dev/<missao>-escopo.md` (o que é V1)

---

## Entregável 1 — Inventário de assets

| ID | Tipo | Onde aparece | V1/V2 | Quem produz | Status |
|---|---|---|---|---|---|

Tipos: **vídeo de conteúdo** · **vídeo de revelação** (making of, recriação, bastidores) · **áudio de narração** · **pictograma de gesto** · **ilustração de cena** · **áudio de podcast**.

Convenção de ID: `<tipo>-<missao>-<n>`. Todo asset aponta para o ID da tela onde aparece e, quando existe, para o asset ao qual está pareado.

Conte com a customização do professor: se ele monta o conjunto a partir de um banco, o banco inteiro entra no inventário, com a proporção obrigatória declarada e o pareamento de cada item.

---

## Entregável 2 — Spec por tipo

### Vídeos de conteúdo

Para cada um: duração, o que aparece, **por que passa ou não passa a impressão que a missão precisa**, e a que categoria pertence dentro da proporção obrigatória.

Regras que valem sempre:

- **A categoria não pode ser adivinhável pela forma.** Se todos os vídeos de uma categoria são mais longos, mais nítidos, ou mais bem enquadrados que os da outra, a produção entrega a resposta sem querer, e a mecânica de julgamento vira sorteio invertido.
- **Sem marca, sem IP, sem pessoa real identificável** — e nunca criança real identificável. Preferir animais, objetos, mãos, desenho.
- **Verossimilhança de plataforma:** enquadramento, proporção e qualidade compatíveis com vídeo caseiro do ambiente simulado, não com produção publicitária.

### Vídeos de revelação

O par mais delicado do brief. Regras:

- **A existência do asset não pode sinalizar nada.** Se só uma das categorias tem vídeo de revelação, a presença dele entrega a resposta antes do conteúdo. Toda categoria precisa do seu par, com formatos equivalentes.
- **A revelação tem que ser visualmente concreta e conectável ao original.** O espectador precisa reconhecer *o mesmo vídeo* e ver *o que foi feito com ele* — mesmo enquadramento inicial, mesma cena, e então o que estava escondido. Revelação genérica ("como se faz esse tipo de efeito") não fecha o laço.
- **Sem narração explicativa que entregue a conclusão.** A imagem mostra; quem conclui é o estudante, e quem consolida é o professor no debate.

### Áudios de narração

Para cada string acionável do sheet de copy, em missões de anos iniciais:

- Voz do personagem-guia, consistente em toda a missão — mesma intérprete, mesmo registro.
- Ritmo lento, articulação clara, sem jargão, sem ironia.
- Duração alvo por instrução, e a instrução precisa **caber sem ser cortada**.
- Reprodução automática na primeira vez, repetição sob demanda pelo ícone de som.
- Arquivo por chave de string, nomeado pela chave — não por número de tela.

### Pictogramas de gesto

Um por gesto de interação: traço uniforme, legível em tamanho pequeno, gesto reconhecível sem texto. Onde o gesto é novo para a faixa, o pictograma vira **animação de demonstração de 1 ciclo**, não imagem estática.

Pictograma é requisito de acessibilidade, não decoração. Ele não pode ser cortado por prazo.

---

## Entregável 3 — Critérios de reprovação

Uma lista curta e literal do que faz um asset voltar. Sem isso, a revisão vira debate de gosto.

- A categoria é adivinhável pela forma, não pelo conteúdo
- O vídeo de revelação não permite reconhecer o original
- A narração excede a duração ou usa vocabulário fora da faixa
- Pessoa real identificável, criança real, marca ou IP de terceiro
- Assimetria de pareamento entre categorias
- Asset sem ID, sem tela associada, ou fora do inventário

---

## Entregável 4 — Ordem de produção

Sequencie por dependência e por risco, não por tipo:

1. O asset mais difícil de acertar, primeiro — normalmente o item ambíguo por design, cuja curadoria decide se a mecânica funciona.
2. Pares de conteúdo + revelação, sempre juntos. Nunca produzir um lado e o outro depois.
3. Narração só depois do sheet de copy congelado. Regravar áudio custa mais que reeditar string.
4. Pictogramas em paralelo, dependem só da lista de gestos.

Marque o que é **V1** e o que espera. Produção de conteúdo é o gargalo mais comum de missão.

---

## Entrega

`assets/<missao>-brief.md` · `assets/<missao>-inventario.md`

Acione `aprendizado` com: decisões de curadoria que valem reuso, e assets reprovados com o motivo — a lista de reprovação melhora a cada missão.

## O que você nunca faz

- Escrever brief contra mecânica não aprovada
- Especificar asset que nenhuma tela usa
- Deixar par de revelação assimétrico entre categorias
- Permitir que a forma do asset entregue a resposta
- Tratar pictograma ou narração como opcional sob pressão de prazo
