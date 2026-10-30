---
name: ambientes
description: Registro dos ambientes simulados — de "ChatGPT/Instagram/WhatsApp" do briefing para a seção atual do design system, e a fronteira entre o que é fixo na biblioteca e o que cada missão possui. Lido por telas e jornada.
sources: [chat]
---

# Ambientes simulados

**A biblioteca não é nossa** — cada ambiente é uma **seção do design system**, publicada no `storybook-unooria`. Missão **monta**; a seção **fornece**. Não existe biblioteca a construir, existe seção a consumir **na última versão publicada** (versão única, ADR-139: não crave número).

## Ambiente do briefing ≠ seção do DS

O briefing fala a língua do aluno: "ChatGPT", "Instagram", "WhatsApp". A spec e o PRD falam a língua do código: a **seção**. Desde as ADR-133 a 138 (out/2026), **missão nova não reproduz a identidade visual de aplicativo de terceiros**: ela usa a cópia estrutural do app **com a identidade da Unooria**. A tradução é esta, e vale para todo briefing:

| O briefing diz | Seção para missão NOVA | Ponte | App que o aluno vê | Seção legada (só missão antiga) |
|---|---|---|---|---|
| ChatGPT, assistente de IA, chat com IA | `unooriaai` (tokens `--uai-*`, `data-uai-theme`) | `@edu/ui/ds-unooriaai` | **UnooriaAI** | `chatgpt` (exp08ef4b) |
| Instagram, feed, rede social de fotos | `unoovista` (tokens `--unv-*`, `data-unv-theme`) | `@edu/ui/ds-unoovista` | **Unoovista** | `instanooria` (exp01ef1b) |
| WhatsApp, mensageiro, grupo de conversa | `unoochat` (tema CLARO) | `@edu/ui/ds-unoochat` | **Unoochat** | `whatsappmobile` (exp06ef2b, só tema escuro, ADR-68) |
| YouTube, vídeo | — (o `unootube` está arquivado, ADR-116) | — | — | `unootube` (arquivado) |
| Jornal, notícia, manchete | `unoojornal` (tokens `--ujn-*`, `data-ujn-theme`) | `@edu/ui/ds-unoojornal` (desde 28/10/2026, exp03ef1b, ADR-197) | **Unoojornal** | — |
| TikTok, vídeo curto | `tiktooria` (existe no DS, **sem ponte** em `@edu/ui` e sem consumidor) | criar a ponte é pré-requisito | — | — |
| Blog, galeria de fotos | `unooblog`, `unoogaleria` (existem no DS, **sem ponte**) | criar a ponte é pré-requisito | — | — |
| A escola, a plataforma, o professor | `unooria` | `@edu/ui/ds` | Unooria | — |

**O nome do app que o aluno vê é o da coluna "App que o aluno vê"**, nunca o da marca imitada: a missão do 9º ano (out/2026) saiu da esteira pedindo `chatgpt`, `@edu/ui/ds-chatgpt` e `data-gpt-theme` porque esta tabela não existia. A lista do que existe de fato (seções, pontes, componentes) está no **contrato da plataforma** e no inventário do DS, incluídos ao lado; esta tabela só diz **qual escolher**. A coluna «Ponte» é uma fotografia (30/10/2026, `@unooria/design-system` 0.2.26): onde o contrato da plataforma listar ponte que ela não lista, ou o contrário, **o contrato vence** — ponte que já existe não é pré-requisito. Briefing que pedir explicitamente a seção legada é decisão do PO: registre `[ABERTO — PO]`, não escolha sozinho.

**Uma peça de outro app dentro de uma tela da Unooria fala na voz de onde veio** (ADR-117): um post que chegou por rede social aparece como `PostCard` do `unoovista` dentro da redação `unooria`, uma mensagem encaminhada como `MessageBubble` do `unoochat`. A regra é por **peça**, nunca por tela: o cromo em volta continua da Unooria. O inverso — peça da plataforma dentro do clone — continua proibido.

## Seção que não existe

Missão que precisa de seção ou componente novo **não o cria na experiência** — é a regra de ouro do DS, e violá-la é ❌ em DES-01 e DES-09.

O caminho é: a missão lista os componentes faltantes como **pré-requisito**, com responsável e prazo, e eles chegam por versão publicada antes de a codificação começar. O `telas` monta contra a seção; o que não existir nela é pré-requisito declarado, não improviso local.

## A fronteira — um teste, não uma lista

**Isso muda se a missão mudar?**

- Não muda → **seção do DS**. Chrome, posição e ordem das affordances, ícones nativos, proporções, barra de abas, estados de interação padrão, tokens.
- Muda → **da missão**. Conteúdo, ritmo, quais affordances entram em cena e em que etapa, o que é deliberadamente removido, scaffolding, telas de professor.

Caso que não couber nos dois lados é zona de negociação, não improviso: a missão constrói local, marca como candidato, e `aprendizado` decide se sobe quando uma segunda missão pedir o mesmo. Um pedido é exceção; dois é padrão.

## Ausências por ambiente — o que a plataforma real NÃO tem

É markdown, e é o que mais reduz achado de fidelidade. Uma tabela por seção, para ninguém "completar" a interface por realismo. Preenchida em 22/09/2026 (emenda E-02) com linhas `[PROPOSTA]`, a conferir.

| Seção | Não tem (o que a plataforma real tem e a simulação deliberadamente não) |
|---|---|
| `unoovista` (e o legado `instanooria`) | [PROPOSTA] Mensagens diretas · Stories e Reels, salvo quando a mecânica os pede · anúncios e publicações patrocinadas · loja e compras · notificações fora da missão · busca aberta na internet · perfis fora do banco curado · contadores de seguidores ao vivo (todo número visível é gabarito ou cosmético declarado, PED-03) |
| `unootube` (arquivado) | [PROPOSTA] Anúncios · transmissão ao vivo e chat · monetização · autoplay infinito fora do banco · comentários de terceiros reais · download · histórico entre sessões fora do estado salvo |
| `unooriaai` (e o legado `chatgpt`) | [PROPOSTA] Memória entre conversas · upload de arquivo ou imagem · navegação na web · plugins e GPTs · modo de voz · histórico lateral fora da missão · resposta em tempo real sem curadoria (8.2) |
| `unoochat` (e o legado `whatsappmobile`) | [PROPOSTA] Chamadas de voz e vídeo · status · localização · pagamentos · contatos fora do grupo da missão · encaminhar para fora da simulação. Tema: `unoochat` é CLARO (ADR-134); `whatsappmobile`, só escuro (ADR-68) |
| `tiktooria` | [PROPOSTA] Transmissão ao vivo · loja · mensagens diretas · efeitos e filtros de criação · monetização · download · "Para você" infinito fora do banco |

Cada linha nasce marcada `[PROPOSTA]` até conferência contra o storybook e contra o bloco 5 das specs já aprovadas — uma lista imperfeita é conferível; uma lista vazia não é. Quem conferir tira a marca e registra a data.

**Regra de leitura.** Ausência desta tabela é ausência **da seção** e vale para toda missão naquele ambiente. Ausência do bloco 5 da spec é **da missão**. O3 da rubrica de ofício confere as duas; o D9 copia a linha da seção para o bloco 14 e acrescenta as ausências da missão.

## Nomenclatura de slot

Componente da seção vem com os slots de variável do DS. **Não recrie o valor** — a coleção `wireframe-cinza` espelha os mesmos slots (ver `references/wireframe-cinza.md`), e é isso que faz a subida pra alta fidelidade ser troca de coleção.

Se a seção trouxer valor em vez de slot, isso é lacuna a registrar no storybook, não a resolver localmente: wireframe montado sobre valores fixos quebra na troca e vira descarte pela metade.

## Nada da marca dentro do disfarce

Nenhum token, fonte, cor ou componente da seção `unooria` dentro das telas do clone — e vice-versa (DES-13). Os dois escapes conhecidos continuam: tela de contexto antes de entrar e tela de fechamento (sem pergunta nem campo de texto) depois que a simulação fecha, e esses **podem** usar a seção `unooria`. Há uma terceira exceção, restrita: a **instrução fixa** do estudante (`references/padrao-plataforma-instrucao-fixa.md`), só com `instrucao_fixa: sim` na spec, camada do hub fora do iframe e do DOM do clone, nas condições escritas ali.

**DS híbrido — exceção registrada, não padrão.** A plataforma aceitou, missão a missão, a mecânica da missão (carimbos, etiquetas, esteira de blocos, peças de montar) na seção `unooria` **ao lado** do ambiente: o jornal `unoojornal` com a mecânica `unooria` na exp03ef1b (ADR-197) e o clone `unooriaai` com o `PuzzleBlock`/`PuzzleTrack` da `unooria` na exp09ef1b (ADR-202). Cada peça continua inteira numa seção só, e o chrome do ambiente nunca recebe token da `unooria`. Missão nova que precisar disso registra `[ABERTO — PO: DS híbrido, a mecânica <qual> na seção unooria ao lado de <seção>]` e cita o precedente; não adota o híbrido sozinha.

O mapa de qual seção fala em cada tela é entrega do `copy-ptbr` (coluna `seção` no sheet), porque quem decide quem está falando é quem escreve a fala.

<!-- include: references/varias-secoes.md -->

