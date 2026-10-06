# Dimensão B — Design & Imersão

Referências do gabarito: `packages/AGENTS.md` (mecânica do DS),
`documentacao-latex/secoes/14-design-system.tex`, ADR-22 (linha da revelação),
`apps/experiencias/*/src/main.tsx` (folhas importadas). Verifique a seção do DS
citada pela spec contra as pontes existentes em `packages/ui`.

## DES-01 [BLOQUEANTE] — Seção do design system definida e existente
A spec nomeia a seção do clone — para missão nova, `unooriaai`, `unoovista` ou
`unoochat` (tradução do ambiente em `ambientes.md`; a lista do que existe está no
contrato da plataforma); `tiktooria` existe sem ponte; as legadas (`instanooria`,
`unitube`, `chatgpt`, `whatsappmobile`) só com decisão registrada do PO —, ou
declara que precisa de seção NOVA. Componente/seção que não existe nasce no
repo `storybook-unooria` e chega por versão publicada ANTES da codificação da
missão — a spec então lista os componentes faltantes como pré-requisito, com
responsável. "A gente cria o componente na experiência" = ❌ (viola a regra de
ouro do DS).

## DES-02 [BLOQUEANTE] — Mapa de "quem está falando", tela a tela
Toda tela/diálogo/toast classificado: fala o CLONE (seção do clone) ou fala a
PLATAFORMA (seção `unooria`)? O critério nunca é "vem depois no tempo", e sim
"quem está falando" (ADR-22): na exp-02 o diálogo de limite de 3 salvos fala de
dentro da ficção (Modal do clone), e o ranking fala pela escola. Missão sem
revelação no software é 100% seção do clone e NÃO importa `unooria.css` nenhum
(exp-03). Spec sem esse mapa = ❌.

## DES-03 — Fidelidade do clone
Referências visuais do software imitado e a lista do que deliberadamente
difere (e por quê). A imersão é o instrumento de medida: um detalhe fora do
idioma do clone é ruído no dado.

## DES-04 — Viewport decidido
Casca de aparelho (`viewport` 375×812 → `DispositivoFrame`) ou desktop tela
cheia — decidido e justificado pela mecânica. Consequência conhecida: na
exp-01 o feed nunca expande fora do aparelho porque o dwell é medido contra o
iframe (área maior inflaria o sinal do motor em silêncio).

## DES-05 — Permissões de iframe derivadas das interações
Enumerar o que o sandbox precisa: formulário com submit ⇒ `forms` (o Composer
do DS é um `<form>`; sem `allow-forms` o Enter falha em silêncio — bug que
passou por typecheck, lint e duas versões do smoke); mouse capturado ⇒
`pointer-lock`. Só o que a missão realmente usa.

## DES-06 — Tema claro/escuro
Quem controla e como: a seção do clone lê `data-*-theme` na raiz; a seção da
plataforma recebe `theme` por prop; quem troca escreve nos dois (gabarito:
`exp-02/src/lib/tema.ts`). Preferência persiste em `localStorage` (permitido
para preferência de tela; proibido para token).

## DES-07 — Estados de interface completos
Para cada tela: vazio, carregando, erro — e o estado de PONTO CEGO: ausência de
dado aparece como "não sabemos", nunca como zero ("0 pessoas em risco" onde
nenhuma fonte cobre o bairro era defeito real; `estimativa === null` é ausência
por tipo). Idem `cartoesServidos ≠ apareceram`: "as mensagens não chegaram
nesta partida", nunca "ela ignorou tudo".

## DES-08 — Copy real, adequada à série
Textos finais (não lorem/placeholder) com tom adequado à idade. Diálogo em vez
de toast quando há decisão a tomar (o toast da exp-02 sumia em 5,2s sem dar
saída; o diálogo põe a troca na tela e não repreende). Textos que SÃO o
instrumento (mensagens, cartões) são servidos pela api — a spec não pode
prever cópia deles no hub.

## DES-09 — Sem componente local; exceções declaradas
Nenhum componente de UI novo na experiência ou em `packages/ui`. Exceções
aceitas no gabarito são arte, não UI: o mapa SVG e ícones autorais da exp-03,
o canvas 3D da exp-70. Se a spec pede exceção, ela nomeia e justifica.

## DES-10 — Inventário de assets
Lista de imagens/áudio/vídeo com peso estimado. >2MB vai ao bucket de assets,
referenciado por variável de build — nunca no git, nunca no bundle. Fontes do
clone vêm do DS com a folha de fontes em linha separada e obrigatória.

## DES-11 — Acessibilidade e pré-requisitos físicos
Contraste, não depender só de cor, navegação por teclado onde a mecânica
permite; se há áudio essencial, o preparo do professor inclui fones (exp-02).
Requisitos de máquina/navegador se houver WebGL/pointer lock.

## DES-12 — Microinterações que alimentam medida estão sinalizadas
Toda interação que vira dado (dwell, duplo toque, expandir legenda, abrir
busca) está marcada na spec de design como "instrumentada": o Designer não pode
mudá-la depois sem avisar quem lê o dado. Na exp-01, `abriu_busca` e `buscou`
são os eventos mais valiosos da missão — um redesign da busca é mudança de
instrumento, não de tela.

## DES-13 — Nada da marca institucional dentro do disfarce
Nenhum token, fonte, cor ou componente da seção `unooria` dentro das telas do
clone (e vice-versa). Um `Button` da plataforma no feed quebra a ilusão que a
experiência está medindo.

## DES-14 [BLOQUEANTE] — Visão do professor completa e transversal
**Severidade decidida por esta esteira em 22/09/2026** (o critério nasceu aqui em 21/09, não no time da plataforma): sem as cinco telas do preparo a missão não é preparável pelo professor de outra disciplina, e o QA de design já bloqueia a mesma ausência (D6) — duas severidades para o mesmo fato eram um defeito.
A missão é preparada pelo professor de qualquer disciplina. As cinco telas do
preparo (`E0-PROF-01…05`: escolher a missão, recorte da aula com disciplina, tema
e assuntos, geração em andamento, curadoria do pacote, ativar) existem na
jornada (seção 1c), no fluxo (segundo grafo, "Fluxo do professor"), no Stitch
(folha de links, seção "Visão do professor") e no protótipo (trilho do
professor), sobre o kit do DS do hub — não sobre a seção do ambiente simulado.
A tela de recorte e a de curadoria mostram uma aula de disciplina diferente do
banco default, tirada da tabela "a mesma missão em três aulas" do bloco 8 da
spec. Tela do preparo ausente do Stitch é `[LACUNA — dono: telas]`; fluxo do
professor ausente é lacuna com dono `fluxo`; formulário que só aceita um tipo de
conteúdo sem `[LIMITE DE TRANSVERSALIDADE]` declarado é achado com dono
`gate-estrutural`.
