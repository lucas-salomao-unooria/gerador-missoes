# Manual do Gerador de Missões — fonte LaTeX

Manual único da esteira, com a identidade visual da Unooria aplicada. Unifica e substitui
os dois documentos anteriores (`documentacao-latex/guia-do-gerador-de-missoes.tex`, voltado à
operação, e `manual-gerador-missoes/manual_gerador_missoes.tex`, voltado à fundamentação).

**2.ª edição — 25/09/2026.** A 1.ª (19/09) descrevia 55 passos e uma esteira que rodava sozinha
do briefing ao PRD. Entraram desde então: o parecer humano entre etapas com login por papel, a
camada de profundidade pedagógica, a memória entre execuções, as perguntas de produto e o recorte
da aula por disciplina. São 114 commits de diferença.

## Compilar

```bash
tectonic -X compile manual-gerador-missoes.tex
```

Gera `manual-gerador-missoes.pdf` (68 páginas, 2.ª edição). Não depende de BibTeX — a bibliografia é
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
código (`agents/*/__init__.py`, `config.py`, `prompts/`), não contra os manuais anteriores.
Ao mudar a esteira, o catálogo da Parte VI é o primeiro trecho a revisar — ele espelha o
dicionário de agentes de `agents/<etapa>/__init__.py`.

Três armadilhas conhecidas da composição, que já custaram tempo:

- **Emoji some do PDF sem erro.** Nenhuma fonte de texto traz 🟢🟡🔴; o XeTeX descarta o glifo com
  um aviso fácil de perder, e a frase perde o sentido ("o PRD sai 🔴" vira "o PRD sai"). Use os
  comandos `\statusVerde`, `\statusAmbar`, `\statusVermelho` e `\statusPendente`, que desenham
  as bolinhas. Conferir com `tectonic ... 2>&1 | grep -i "missing character"`.
- **`\multicolumn` na coluna `X` de um `tabularx`** desativa o cálculo elástico e estoura a caixa.
- **Título órfão no pé da página:** use `\Needspace*{N\baselineskip}` antes da seção.

## Prévias no README principal

O README da raiz embute seis páginas como PNG, porque o GitHub não renderiza PDF inline.
São elas: capa, o que a esteira faz, o parecer humano, o mapa dos 72 passos, a anatomia do *ahá*
e o catálogo de agentes.
Elas envelhecem junto com o manual — depois de mexer no `.tex`, rode:

```bash
./gerar-previews.sh
```

O script recompila o PDF e regenera `previews/`. As páginas escolhidas estão no dicionário
`PAGINAS` dentro dele; **confira se ainda correspondem**, porque a paginação muda quando o
texto muda.
