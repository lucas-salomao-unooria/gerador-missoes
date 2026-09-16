# Unooria Design System — referência para design e código

> **Atenção à versão.** O inventário de tokens e componentes abaixo foi lido do repo `storybook-unooria` na tag **0.1.18**; a plataforma consome **`@unooria/design-system@^0.2.2`** (compilado contra React 19) desde 11/09/2026. Onde houver divergência, vale o Storybook publicado (`https://storybook.unooria.com/`) e as regras da plataforma copiadas ao final deste arquivo (`regras-design-system.md`, `agents-ui.md`). Reconferir o inventário na próxima sincronização do storybook.
>
> **Pontes existentes em `@edu/ui`:** `ds` (unooria), `ds-insta` (instanooria), `ds-unootube` (unitube, CSS `--uni-*`), `ds-chatgpt`, `ds-whatsapp` (whatsappmobile, **só tema escuro**, ADR-68; usada por exp-06 e exp-07). **`tiktooria` não tem ponte** — criar a ponte é pré-requisito de qualquer missão TikTok. Componente de UI local continua proibido; compensação local marcada nunca vira componente (ADR-68/72).

## 1. Pacote

| Item | Valor |
|---|---|
| Nome npm | `@unooria/design-system` |
| Versão | `0.1.18` (inventário lido) · **`^0.2.2` em uso na plataforma** |
| Peer deps | `react >=18`, `react-dom >=18` |
| Publicação | GitHub Actions por tag `v*`; Storybook em Cloud Run |

**Multimarca**: seis design systems irmãos, cada um com subpath export próprio: `./unooria` (a plataforma), `./instanooria`, `./chatgpt`, `./whatsappmobile`, `./tiktooria`, `./unootube`. Cada marca tem CSS próprio (`@unooria/design-system/unooria.css`) e folha de fontes opt-in (`@unooria/design-system/fonts/unooria.css`).

Consumo exige ponte `components/ds.ts` com `'use client'` reexportando o que se usa; **nunca importar o barril raiz numa tela**.

## 2. Tokens (`src/unooria/tokens/`, CSS `--unooria-*`)

### 2.1 Paleta (base = 600, salvo indicação)

| Escala | 50 | 300 | 600 (base) | 900 |
|---|---|---|---|---|
| **brandNavy** (primária) | `#F5F8FC` | `#BDD0EF` | **`#7FA5E2`** | `#2F4F7F` (950 `#0E1039`) |
| **brandPurple** (secundária) | `#F7F6FA` | `#CCC9DE` | **`#716C98`** | `#0E1039` |
| **neutral** (light) | `#FFFFFF` | `#A7B5B9` | `#536167` | `#383E41` (950 `#22272A`; 150 `#E4E8E9` bordas) |
| **danger** | `#FFF1F1` | `#FFA1A1` | **`#E31A1A`** | `#841818` |
| **success** | `#EBFEF4` | `#63F2B5` | **`#01B574`** (500) | `#00543C` |
| **warning** | `#FFF8EB` | `#FFB74A` | **`#F97607`** (500) | `#7A230D` |
| **info** | `#E9FAFF` | `#26D4FF` | **`#0086FF`** (500) | `#002752` |

Papéis semânticos (convenção, não há camada `--unooria-color-surface-*`):

| Papel | Light | Dark |
|---|---|---|
| Fundo página / card | `neutral-50 #FFFFFF` / `neutral-100 #F5F5F5` | `neutraldark-50 #22272A` |
| Texto principal | `neutral-950 #22272A` | `#F5F5F5` |
| Texto secundário | `neutral-700 #475157` | `#CBD4D6` |
| Borda / divisor | `neutral-150 #E4E8E9` | `#3D4448` |
| Ação / destaque | `brandnavy-600 #7FA5E2`; ativo `#6487C2` | idem |

### 2.2 Tipografia — **Open Sans** única (embutida, sem Google Fonts). Pesos 400/500/600/700.

| Token | Desktop | Mobile |
|---|---|---|
| `heading-xxl` | 34/48 | 24/34 |
| `title-xl` | 24/34 | 20/30 |
| `title-l` | 20/30 | 18/28 |
| `body-m` | 18/28 | 16/24 |
| `body-s` | 16/24 | 14/20 |
| `body-xs` | 14/20 | 14/18 |
| `body-xxs` | 12/18 | 10/14 |

### 2.3 Espaçamento (T-shirt): `4XS 2` · `XXXS 4` · `XXS 8` · `XS 12` · `S 16` · `M 24` · `L 32` · `XL 48` · `XXL 64` · `XXXL 80` · `4XL 96` px.

### 2.4 Raios — **não há tokens em `:root`**, só fallbacks inline. Valores de fato: 8px padrão, 12px cards grandes, 4px pequeno, 16px, pílula 1000px. (Lacuna a declarar em PRD.)

### 2.5 Sombras = **glows** sem offset (`brand-primary 0 0 10px rgba(127,165,226,.3)`), nunca sombra dura deslocada. Blur glassmorphism 8–64px.

### 2.6 Breakpoints/grid

| Breakpoint | min-width | Canvas Figma | Colunas | Gutter | Margem |
|---|---|---|---|---|---|
| mobile | 0 | 375 | 4 | 12 | 12 |
| tablet | 768 | 1280 | 8 | 24 | 24 |
| notebook | 1280 | 1440 | 12 | 24 | 48 |
| desktop | 1920 | 1920 | 12 | 24 | 48 |

### 2.7 Tema — prop `theme="light"|"dark"` nos componentes + seletor `[data-theme="dark"]`. Clones usam atributo na raiz (`data-uni-theme`, `data-gpt-theme`).

## 3. Componentes — marca `unooria` (39)

`Button` (primary·secondary·outline·ghost·danger; sm/md/lg) · `Card` (default·elevated·outlined·interactive; compound `Card.Header/Media/Content/Footer/Progress`) · `Badge` · `TextField`/`PasswordInput`/`SearchInput`/`TextArea` · `Modal` (dialog·alertdialog; sm 400/md 617/lg 800/full; focus trap) · `ProgressBar` (brand·primary·success·warning·danger; xs–lg) · `Avatar`/`AvatarGroup` · `Stepper` · `Tag` · `Tabs` · `AlertBox` · `FeedbackAlert`/`Snackbar` · `EmptyState` · `Checkbox`/`RadioButton`/`Toggle`/`Selection` · `Table` · `DataViz` (`BarChart`, `LineChart`, `AreaChart`, `PieChart`, `DonutChart`, `RadarChart`, `MetricCard`, `StackedProgressBar`, `CircularProgressBar`, `RankingCard`) · `SideBar`, `BottomBar`, `Breadcrumb`, `Pagination`, `Outline`, `SectionHeader` · `Calendar`, `DatePicker`, `TimePicker`, `Cropper`, `RichTextEditor`, `UploadFileModal`, `Collapse`, `Tooltip` · `Logo`, `Icon`.

**Clones (ambientes simulados)**: `instanooria` 21 comp. (`PostCard`, `StoriesTray`, `StoryViewer`, `ProfileHeader`, `PhoneFrame`…), `chatgpt` 25 (`ChatBubble`, `Composer`, `WebSidebar`…), `whatsappmobile` 29 (`MessageBubble`, `ChatListItem`…), `tiktooria` 35 (`ActionRail`, `VideoMeta`, `RecordButton`…), `unootube` ~44 (`VideoCard`, `ShortsPlayer`, `Playlist`, `DesktopFrame`…).

## 4. Padrões transversais

- Compound components com dot-notation + atalhos declarativos, espelhando os component sets do Figma. Prop `as` polimórfica.
- **Acessibilidade**: ARIA completa, focus trap e `initialFocusRef` no `Modal`, teclado; addon a11y em modo `todo` (não bloqueia CI).
- **Animação**: `transition .15s/.2s ease`; `prefers-reduced-motion` quase ausente (lacuna).
- **Ícones**: **Material Symbols Rounded**, weight 300, fill 0, tamanhos 12–48; ícones customizados só por export literal do Figma.
- **Tom visual**: azul-lavanda sóbrio; o lúdico vem das marcas-simulacro, não do DS da plataforma.

## 5. Vínculo com Figma

| fileKey | Nome | Uso |
|---|---|---|
| `mPw4Hhx9ptkgcHtySaSilO` | **Design System Unooria** | tokens e maioria dos componentes |
| `i0HRQSBtQQ9ZXDYiJPRnGv` | **Unooria_DS_v0.2** | `Selection` (`13244-44733`), `Avatar` (`17423-1574`) |

Arquivos community dos clones: ChatGPT `FlQnC8T6Sg5HdVodu0f7bL`, YouTube `HcbrbLtDZ1rMEvSjoXpA5c` + Shorts `FlqnnoY0Mqdjic53twLAC1`, WhatsApp `MSEV2CgXr84WwOyMauIBy2`, Instagram `RA6xg5xo3Ty2iXpjlqVnXq`, TikTok `UIYCB87CQkpFwf1aWTBl1a`.

Nós principais (Dev Mode): `ProgressBar` 18644-1049 · `Badge` 17265-3692 · `AlertBox` 17025-277 · `Card` 7740-1778 · `Modal` 8909-60 · `Stepper` 12694-10079 · `Tab` 12694-10183 · `TextField` 6107-729 · `Toggle` 6034-914 · `Tooltip` 6034-1092 · `Tag` 6029-1817 · `Snackbar` 6029-1314 · `Checkbox`/`RadioButton` 25405-5873 · `SideBar`/`BottomBar` 3340-11320 · `DataViz` 5847-2154 · **Ícones 6024-2923**; espaçamento `6189:512`, elevação `6188:6091`, blur `6217:97`.

**Code Connect: não existe.** O vínculo é documental.

## 6. Storybook

Storybook 10, porta 6007. Títulos `Plataforma Unooria/Componentes/[Nome]`; pastas `stories/<marca>/{fundamentos,componentes,telas}`. 1ª story sempre `📄 Documentação Completa` (Visão Geral, Figma & Specs com node ID, Anatomia, Matriz de Variantes, DO/DON'T, Temas, Props). Testes: `vitest --project=storybook` (cada story vira teste de render). Chromatic instalado sem workflow.

## 7. Protótipos — lições de padrão de missão

| Pasta | Lição |
|---|---|
| `prototipos/Plataforma Unooria` | Modelo canônico: Ano → 4 Unidades → cada unidade **é uma missão**. Missão = catálogo; **Atividade** = instância configurada. Ações destrutivas separadas (excluir atividade × limpar dados dos alunos). |
| `prototipos/UnooTube-projeto-completo` | Missão como feed + playlists + ranking de colegas fictícios. |
| `prototipos/gpturia` | Orçamentos procedurais (relógio da turma + perguntas debitadas), falha do provedor não custa ao aluno, termina no **Espelho** (o aluno vê só o que fez; a moral é do professor no debate). Duas marcas que não se misturam, com teste de invariante. |
| `prototipos/vila-do-lume` | Dois instrumentos que não podem se tocar (perfil de valores × julgamento de mensagens). Identidade vem do link, nunca da criança. |
| `prototipos/planodeaula` | `TEMPLATE.md` v2 — contrato de arquitetura replicável, §7 “DS: linguagem visual por superfície”. |

## 8. Implicações para wireframes e código

**Design (Figma)**: grid 12 col / 24 gutter / 48 margem em 1440; 4 col / 12 / 12 em 375. Título de tela `title-xl 24/34`, corpo `body-s 16/24`, legenda `body-xxs 12/18`. Cor de ação `#7FA5E2`, texto `#22272A`, borda `#E4E8E9`, fundo card `#F5F5F5`. Raio 8px padrão. Ícones Material Symbols Rounded 300, 24px.

**Kit por tipo de tela**: catálogo → `Card interactive` + `Badge` + `SectionHeader` + `EmptyState`; missão aberta → `Breadcrumb` + `Stepper` + `ProgressBar brand sm` + `Collapse`; configuração → `TextField`/`Selection` + `Modal md`; monitor da turma → `Table` + `AvatarGroup` + `Tag` + `Snackbar`; dossiê → `DataViz` (`MetricCard`, `RadarChart`, `StackedProgressBar`, `DonutChart`); destrutivas → `Modal role="alertdialog"` + `AlertBox error`; **dentro da simulação → subpath da marca-simulacro** com `PhoneFrame`/`DesktopFrame` só no Storybook (no hub o aparelho é o `DispositivoFrame`).

**Código**:
```ts
// components/ds.ts  (SEMPRE com 'use client' no topo)
'use client';
export { Button, Card, Badge, Modal, TextField, Table, Stepper, ProgressBar,
         Avatar, Tag, Tabs, AlertBox, Snackbar, EmptyState, Breadcrumb, Icon,
         BarChart, DonutChart, RadarChart, MetricCard, RankingCard, tokens }
  from '@unooria/design-system/unooria';
```
CSS: `@unooria/design-system/unooria.css` + `@unooria/design-system/fonts/unooria.css`. Para clone, segunda ponte com o subpath dele. No monorepo, usar as pontes `@edu/ui/ds*`.

**Riscos a declarar em PRD**: (1) sem tokens de radius; (2) sem camada semântica de cor; (3) sem Code Connect; (4) `prefers-reduced-motion` ausente; (5) a11y não bloqueia CI; (6) README do DS desatualizado — `AGENTS.md` é a fonte.

## Regras da plataforma sobre o DS (cópias sincronizadas)

<!-- include: references/plataforma/regras-design-system.md -->

<!-- include: references/plataforma/agents-ui.md -->
