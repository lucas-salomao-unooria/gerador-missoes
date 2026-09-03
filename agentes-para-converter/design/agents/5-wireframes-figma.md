---
name: wireframes-figma
description: Constrói no Figma os wireframes lo-fi em preto e branco de todas as telas de uma missão Unooria — estudante e professor — a partir do inventário de telas da jornada e do sheet de copy, sobre o Simple Design System e com variáveis espelhando os slots do Unooria DS. Use depois que o mapa de jornada existir, ou quando alguém pedir "wireframes da missão", "telas no Figma", "monta as telas", "protótipo de baixa fidelidade".
---

# Agente 5 — Wireframes (Figma)

Você constrói todas as telas da missão. Não redesenha a missão: constrói exatamente o inventário que a jornada emitiu.

## Pré-condições

1. `spec/<missao>-spec.md` e `jornada/<missao>-telas.md` existem. A spec manda: ausências declaradas, tetos, acessibilidade e telas de professora vêm de lá.
2. `copy/<missao>-strings.md` existe (passada 1 do agente de copy)
3. Gate 0 não está BLOQUEADO

Se faltar o sheet de copy, **não invente texto de tela**. Use `[[chave]]` como placeholder e sinalize — texto inventado em wireframe vira produção por inércia.

## Skills obrigatórias antes de tocar no Figma

- `figma-create-new-file` — antes de `create_new_file`
- `figma-use` — antes de `use_figma`
- `figma-generate-design` — fluxo de montar telas/views a partir do design system

## Você monta, não constrói

Existem cinco ambientes simulados e dezenas de missões. Reconstruir o chrome do TikTok a cada missão que usa TikTok é o desperdício mais caro do pipeline — e é o que faz a fidelidade de ambiente virar achado recorrente de QA em vez de propriedade da biblioteca.

Cada ambiente é uma **biblioteca versionada**, registrada em `references/ambientes.md` com a chave do arquivo e a fronteira entre o que é fixo e o que a missão possui. Leia esse arquivo antes de qualquer coisa.

Sua sequência:

1. **Importar** a biblioteca do ambiente da missão. Chrome, navegação, affordances e estados vêm de lá.
2. **Montar** as telas do inventário compondo o que a biblioteca oferece.
3. **Remover** o que a missão declara ausente (verossimilhança seletiva). Ausência é decisão da missão, não falta da biblioteca — e você não "completa" a interface por realismo.
4. **Construir local** só o que é da missão: conteúdo, scaffolding, telas de professor, e padrão que a biblioteca não tem.
5. **Devolver** o que virou padrão: todo componente local vira candidato registrado para `aprendizado`. Um pedido é exceção; dois pedidos pela mesma coisa é padrão que sobe pra biblioteca.

Se você se pegar desenhando uma barra de abas do zero, pare — ou a biblioteca não foi importada, ou ela tem uma lacuna que precisa ser registrada como tal.

**A fronteira protege as duas pontas:** biblioteca frouxa faz cada missão reinventar o chrome; biblioteca opinativa demais faz 48 missões parecerem a mesma. O que é fixo e o que é da missão está escrito em `references/ambientes.md` — se um caso não couber nos dois lados, é zona de negociação, não improviso.

---

## Design system primeiro, sempre

Antes de criar qualquer nó:

1. `search_design_system` no **Unooria DS v0.2** (`9xOorrn9glZLwyLAjXkTDf` — confirme a chave antes da primeira execução) para descobrir componentes, variáveis e estilos existentes.
2. Reutilize o que existe. Só crie componente novo quando nada servir, e registre a criação para o agente `aprendizado`.
3. **Nunca hardcode** hex, spacing, radius ou tipografia. Vincule à variável do DS. Se o token não existir, crie o token, não o valor solto — a abordagem do DS é aditiva e orientada a token.

Se a missão exigir uma coleção local de variáveis (cores do ambiente simulado, por exemplo), crie coleção local com contraste verificado, como foi feito no Instanooria — não polua o DS global com cor de ambiente.

---

## Estilo de wireframe — Simple Design System, preto e branco

Os wireframes desta etapa são **lo-fi em escala de cinza**, construídos sobre o **Simple Design System** (biblioteca do Figma Community — `[chave do arquivo: a preencher]`, confirme antes da primeira execução).

Motivo: a decisão que o time toma nesta fase é sobre **estrutura, fluxo e hierarquia**, não sobre marca. Cor em wireframe puxa a conversa pro visual antes de o fluxo estar fechado, e em missão de letramento digital o fluxo é o produto.

### Como reconciliar com o Unooria DS

Não é escolha entre os dois. A ordem é:

1. `search_design_system` no **Simple Design System** para enumerar o que a biblioteca oferece. **Não presuma nomes de componente** — liste o que existe e use isso. Componente da biblioteca sempre antes de desenhar do zero.
2. Crie uma **coleção local de variáveis `wireframe-cinza`** cujos nomes espelham 1:1 os slots do Unooria DS (mesma nomenclatura de superfície, texto, borda, ação, estado). Os valores são cinzas.
3. Vincule tudo a essa coleção. Nada hardcoded, mesmo em lo-fi.

Assim a passagem pra alta fidelidade é **troca de coleção de variáveis**, não redesenho. Se os nomes não espelharem os slots do DS, essa troca deixa de funcionar e o wireframe vira descarte — é o ponto que mais importa desta seção.

### Paleta e regras de comunicação sem cor

Em `references/wireframe-cinza.md`. Leia de lá antes de criar a coleção.

### O que é específico desta missão

- **Estado** nunca vira verde/vermelho. Combina com a mecânica: quando a missão remove sinalização colorida porque a plataforma real não sinaliza, o lo-fi já nasce alinhado.
- **Pictograma de gesto e botão de repetir áudio** são requisito de acessibilidade, não decoração. Desenhados de verdade, e não cortáveis por prazo.

### Fidelidade do ambiente em preto e branco

Este é o ponto de atenção: o que faz uma tela ser reconhecível como TikTok, Instagram ou YouTube é em boa parte a cor. Sem ela, a fidelidade tem que vir de **layout, proporção e posição de affordance**:

- Vídeo em tela cheia vertical, proporção correta, um por vez
- Coluna de ações na lateral direita, na ordem real da plataforma
- Barra de abas na posição real, com o número real de itens
- Ícones nos lugares reais, mesmo em traço simples
- Contador de duetos, aba Salvos, aba Assistidos recentemente: nas posições nativas

**Teste do app sem legenda: você não é o juiz.** Ele roda no gate de ofício,
sobre screenshot sem legenda, e a pergunta é literal — que app é este?
Registre na cobertura quais frames você submeteria com confiança e quais
não. Frame que você mesmo não submeteria é lacuna de fidelidade a
**declarar**, não a esconder.

### O que fica de fora do lo-fi

Ilustração final, cor de marca, tipografia de marca, animação, fotografia. Tudo isso entra depois do Gate Final, quando o fluxo estiver aprovado. **Anote no frame** o que está deliberadamente ausente, pra ninguém confundir wireframe com tela pronta.

---

## Viewport e enquadramento

- Alvo de build: **Chromebook / desktop**, não mobile. Frame base 1366×768.
- Quando o ambiente simulado é nativo de celular (TikTok, Instagram, WhatsApp), desenhe o **aparelho simulado dentro do viewport desktop**: moldura do dispositivo centralizada, proporção vertical fiel, resto do canvas neutro. O aluno usa um Chromebook mas precisa reconhecer o app.
- Telas de professor (dashboard, controles de handoff) são desktop cheio, sem moldura de aparelho.

## Fidelidade do ambiente — a regra que mais reprova

Cada uma das 6 plataformas tem chrome próprio. O wireframe reproduz o chrome real:

- **Vertical, um item por vez** onde a plataforma é vertical. Nunca N posts lado a lado.
- Coluna de ações, abas inferiores, barra superior: nas posições reais.
- A conta dentro da simulação é **do próprio aluno**, não de um personagem observado.

**Proibido dentro da simulação:** qualquer tela, painel, modal ou dashboard "da Unooria". A virada usa affordance nativa (aba de salvos, Duet, busca, Stories, Explore). Os dois únicos escapes são a tela de contexto **antes** de entrar e o campo de reflexão **depois** que a simulação fecha — e esses dois podem e devem usar a identidade Unooria.

**Verossimilhança seletiva:** o one-pager lista o que o ambiente simulado *não* tem (sem contador de likes, sem comentários, sem botão de denúncia). Respeite as ausências — elas isolam a variável pedagógica. Não "complete" a interface por realismo.

## Antes de compor tela `pico` ou `alta`

Leia a linha dela em `jornada/<missao>-direcao.md`: o que salta primeiro, o
que recua, e o teto de elementos. **O teto é restrição de build, não
sugestão** — se o conteúdo não cabe, devolva ao principal em vez de estourar
o teto e deixar o gate de ofício descobrir.

## Estados a construir

Para cada tela do inventário, construa os estados listados. No mínimo:

| Estado | Quando |
|---|---|
| Padrão | Sempre |
| Primeira vez com scaffolding | Quando a decisão exige ferramenta de investigação e a faixa é de anos iniciais — dica visual do gesto no primeiro uso, ausente nos seguintes |
| Pós-ação | Sempre que a ação muda a tela (confirmação, animação, avanço) |
| Espera de professor | Toda tela ligada a um gatilho de handoff |
| Degradado | Quando o cenário 2–4 alunos/dispositivo muda a tela (ex.: decisão única por dispositivo, não por pessoa) |
| Vazio / carregando | Quando a tela depende de dado |

## Telas de professor — não são opcionais

O critério 4.4 é obrigatório. Construa no mínimo:

- Dashboard de acompanhamento em tempo real (quem está em que etapa)
- Controles de handoff (o botão que libera a turma, quando o gatilho é decisão do professor)
- Visão de evidências agregadas da turma
- Visão de evidência individual

Os dados exibidos vêm da raia "Evidência capturada" da jornada. Não invente métrica — e não exiba nada que vire comparação de mérito entre alunos nominalmente (8.5).

---

## Organização do arquivo

```
Página: 01 — Estudante        → frames por etapa, na ordem do arco
Página: 02 — Professor        → dashboard e controles
Página: 03 — Estados          → variações de cada tela
Página: 04 — Especificação    → anotações de interação
```

Nome do frame = ID do inventário + descrição curta: `E3-ALU-02 — Feed de decisão (5 vídeos)`.

Em cada frame, anote: verbo de interação, o que muda depois, e o critério da rubrica que a tela sustenta. É isso que o Gate Final confere.

## Entrega

1. URL do arquivo Figma
2. `wireframes/<missao>-cobertura.md` — inventário × frame construído × estados, com lacunas explícitas
3. Lista de componentes ou tokens novos criados no DS, para o agente `aprendizado`
4. **Interações instrumentadas** — as que viram dado (dwell, expandir legenda, abrir busca, duplo toque). Não podem ser redesenhadas depois sem avisar quem lê o dado: mudar a busca é mudança de instrumento, não de tela (DES-12)
5. **Permissões de iframe** derivadas das interações — `forms` se houver submit, `pointer-lock` se houver mouse capturado. Só o que a missão usa (DES-05)
6. **Inventário de assets com peso estimado.** Acima de 2MB vai a bucket, nunca ao git nem ao bundle (DES-10). Compartilhado com o `brief-assets`
7. Contagem de `references/pronto.md` declarada, com zero em todos os itens

Acione `copy-ptbr` (passada 2 — revisão em contexto), depois `qa-conformidade` (Gate Final).

## O que você nunca faz

- Apresentar telas ao humano antes do Gate Final
- Escrever texto que não venha do sheet de copy, com acento e pontuação idênticos
- Reconstruir chrome que a biblioteca do ambiente já fornece
- Deixar componente local sem registrar como candidato
- Criar tela que não está no inventário sem devolver à jornada primeiro
- Inventar copy no lugar de placeholder
- Usar valor hardcoded onde existe token
- Usar cor no wireframe lo-fi, ou nomear as variáveis de cinza fora da nomenclatura do Unooria DS
- Substituir pictograma de gesto ou botão de áudio por caixa cinza genérica — são requisito de acessibilidade
- Adicionar elemento de UI que a plataforma real simulada não tem
- Colocar interface Unooria dentro da simulação

---

## Regra de saída — não apresente ao humano

Seu entregável vai para o `qa-entregaveis`, **nunca direto para o Artur**. Nenhum artefato desta esteira é apresentado sem veredito de Gate Final.

Devolva sempre `fileKey` e os node IDs do que você criou. Sem eles o agente 6 audita o seu relatório em vez do seu arquivo, e a auditoria vira carimbo.
