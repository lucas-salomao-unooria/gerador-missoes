# Manual do Gerador de Missões — fonte LaTeX

Manual único da esteira, com a identidade visual da Unooria aplicada. Unifica e substitui
os dois documentos anteriores (`documentacao-latex/guia-do-gerador-de-missoes.tex`, voltado à
operação, e `manual-gerador-missoes/manual_gerador_missoes.tex`, voltado à fundamentação).

**4.ª edição — 08/10/2026.** A 3.ª (06/10) descrevia 81 passos; esta descreve 114. Entraram: o
one-pager anexado pelo PO como base preservada, conferido trecho a trecho e com restaurador; o
conteúdo aprovado entregue literal a design e dev, conferido até o PRD e colado no fim dele e do
pedagógico; a banca de validação em quatro posições (fim de produto, fim de design, entrada do dev,
dentro do dev); as telas do Stitch geradas fora do modelo, versionadas «· vN»; o PRD codificável
conferido em código; os gates de modelo que só bloqueiam com citação que existe; a matriz de
rastreabilidade com teste de mutação; a resposta cortada pelo modelo registrada; a base da plataforma
num bucket só dela, só leitura; e o catálogo com a grade publicada da plataforma. A Parte VII ganhou
três casos: a exp06ef1b (254 de 304 trechos do one-pager do PO reescritos; 304 de 304 preservados
depois da correção), a exp03ef1b (corte por `RECITATION`) e a primeira volta do padrão ouro
(exp01ef1b, 21 lacunas de coerência, 1 real). Corrigido onde a 3.ª divergia do código:
o apêndice do PRD (23 seções, 0 a 22, e não 25), a pasta da sessão (`<data-hora>-session_<id>`),
o Stitch decidido pelo modelo, o ciclo das avaliações desligado e a banca do dev reescrevendo design.

**3.ª edição — 06/10/2026.** A 2.ª (25/09) descrevia 72 passos; esta descreve 81. Entraram: a base
da plataforma lida do bucket (no lugar da cópia no git, parada em 16/09), os pedidos do PO que se
acumulam e são conferidos item a item (fidelidade), a conta da virada refeita em código, a coerência
entre documentos pelo glossário canônico, as afirmações do QA conferidas, o banco de conteúdo escrito
e conferido, e o rastro de lacunas por etapa. A Parte VII ganhou o caso da exp09ef1b, a missão que
saiu verde e estava errada.

**2.ª edição — 25/09/2026.** A 1.ª (19/09) descrevia 55 passos e uma esteira que rodava sozinha
do briefing ao PRD. Entraram: o parecer humano entre etapas com login por papel, a camada de
profundidade pedagógica, a memória entre execuções, as perguntas de produto e o recorte da aula por
disciplina.

## Compilar

```bash
tectonic -X compile manual-gerador-missoes.tex
```

Gera `manual-gerador-missoes.pdf` (92 páginas, 4.ª edição). Não depende de BibTeX — a bibliografia é
`thebibliography` embutida. A primeira compilação baixa as fontes e os pacotes do bundle.

## Identidade visual

Paleta e tipografia vêm do brandbook (`~/Documents/Unooria/Manual de Marca`):

| Cor | Hex | Papel no brandbook |
|---|---|---|
| Azul profundo | `#0e1039` | estrutura |
| Lavanda | `#8b85ac` | inteligência |
| Azul claro | `#7fa5e2` | interface |

A fonte institucional é a **Garet**, que não está disponível como pacote TeX. A composição usa
**Montserrat** para títulos (geométrica, mesma família de desenho) e **Source Sans Pro** para
corpo de texto. Trocar por Garet é uma edição no preâmbulo, se as fontes forem instaladas:

```latex
\setsansfont{Garet-Bold.otf}[...]        % títulos
```

Verde, âmbar e vermelho aparecem apenas como **cores funcionais de sinalização**, para reproduzir
os três estados dos relatórios da esteira (🟢 🟡 🔴). Não são cores de marca e nunca se aplicam
ao logotipo.

## Assets

`marca/` traz os arquivos do brandbook já recortados no alfa e redimensionados:

- `logotipo-navy.png` — sobre fundo claro (cabeçalho, fechamento)
- `logotipo-lavanda.png`, `logotipo-claro.png` — sobre fundo navy (capa, aberturas de parte)
- `simbolo-lavanda.png`, `simbolo-navy.png`, `simbolo-claro.png`, `simbolo-azul.png`
- `simbolo-grafismo.png` — o símbolo na cor navy clareada em 18% com lavanda, usado como
  grafismo de fundo. É pré-composto porque `opacity` do TikZ não funciona na camada de
  background do `eso-pic`.

## Manutenção

As descrições de agentes, portões, variáveis de ambiente e artefatos foram conferidas contra o
código (`agents/*/__init__.py`, `config.py`, `prompts/`, `tools/`), não contra os manuais anteriores.
Ao mudar a esteira, o catálogo da Parte VI é o primeiro trecho a revisar — ele espelha o
dicionário de agentes de `agents/<etapa>/__init__.py`.

As contagens do manual vêm do código. Os **passos numerados** (114 na 4.ª edição: 48 em Produto,
31 em Design, 32 em Dev e 3 transversais) são a lista que a tela de progresso mostra:

```bash
python -c "from pipeline.orchestrator import STAGES; print(sum(len(s['agents']) for s in STAGES))"
```

Quantos usam modelo (43) e quantos são código (71) **não** sai mais do `prompt_file` dos metadados:
as quatro dimensões da banca no fim de produto e no fim de design (`A15h…`, `A29f…`) são `LlmAgent`
sem `prompt_file` declarado, e a conta por `prompt_file` dá 39/75. Conte pela árvore montada — um
passo numerado é de modelo quando o nó com o `id` dele é `LlmAgent`. Seis passos em código (03a,
16c, 33c, 51, 48e e 49e) chamam por dentro um juiz de modelo e contam como código, como na 3.ª edição.

A **árvore** (160 agentes na 4.ª edição: os 114 passos, 24 cópias de retrabalho e 22 auxiliares — 9
juízes de modelo e 13 passos de código) sai de
`pipeline.orchestrator.create_mission_orchestrator(stages=["produto","design","dev"])` percorrida com
`iter_agent_tree`, contando os nós que **não** são `SequentialAgent`, `ParallelAgent` nem `LoopAgent`
(o método que deu 114 na 3.ª edição; «só as folhas» deixava de fora os passos que têm um juiz como
filho). Cópia é o nó cujo nome tem `Retrabalho`; auxiliar é o resto que não está nos metadados.
Montar a árvore exige a base da plataforma: rode com `BASE_PLATAFORMA_DIR=fixtures/base-plataforma`
e chame `prompts.base_plataforma.fixar(ler_atual())` antes.

Três armadilhas conhecidas da composição, que já custaram tempo:

- **Emoji some do PDF sem erro.** Nenhuma fonte de texto traz 🟢🟡🔴; o XeTeX descarta o glifo com
  um aviso fácil de perder, e a frase perde o sentido ("o PRD sai 🔴" vira "o PRD sai"). Use os
  comandos `\statusVerde`, `\statusAmbar`, `\statusVermelho` e `\statusPendente`, que desenham
  as bolinhas. Conferir com `tectonic ... 2>&1 | grep -i "missing character"`.
- **`\multicolumn` na coluna `X` de um `tabularx`** desativa o cálculo elástico e estoura a caixa.
- **Título órfão no pé da página:** use `\Needspace*{N\baselineskip}` antes da seção.

## Prévias no README principal

O README da raiz embute seis páginas como PNG, porque o GitHub não renderiza PDF inline.
São elas: capa, o que a esteira faz, o parecer humano, o mapa dos 114 passos, a anatomia do *ahá*
e o catálogo de agentes.
Elas envelhecem junto com o manual — depois de mexer no `.tex`, rode:

```bash
./gerar-previews.sh
```

O script recompila o PDF e regenera `previews/`. As páginas escolhidas estão no dicionário
`PAGINAS` dentro dele; **confira se ainda correspondem**, porque a paginação muda quando o
texto muda.
