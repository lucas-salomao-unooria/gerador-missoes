## Missão em mais de uma seção do DS

Desde 15/10/2026 (decisão do PO) uma missão pode combinar seções do DS — fazer algo no `unoovista`, compartilhar e
continuar a conversa no `unoochat`, ler a notícia no `unoojornal` —, como se a plataforma já suportasse: na
codificação entram quantas pontes `@edu/ui/ds-*` forem necessárias. Não é pré-requisito de plataforma.

**Quando usar.** Só quando a seção extra **torna observável uma habilidade** (a ação do Canal A acontece nela) ou
**carrega a virada** (o que o estudante publicou num app chega ao outro). Trocar de app como cenário, sem que nenhuma
decisão dependa disso, é detalhe sedutor (`premissa-imersao.md`) e custa carga.

**Teto por ano** `[EXTRAPOLAÇÃO — validar com PO]`, contando a principal e as extras (a seção `unooria`, da
plataforma, não conta): **1º–3º EF: 1 seção · 4º–5º EF: até 2 · 6º EF ao 3º EM: até 3.** Cada app novo é uma
interface nova a aprender e entra no teto de gestos novos por ato (`literatura-cognitiva.md` §5).

**Como declarar.**
- `secao_ds` continua sendo **uma** seção — a principal, onde a missão começa e passa mais tempo. A trava do briefing
  vale para ela; "É PROIBIDO usar outro design system" no briefing proíbe as extras.
- `secoes_ds_extras: [<seção>, …]` (vazio = nenhuma) no bloco 0 da spec; «Seções extras do DS:» no cabeçalho do
  one-pager, logo depois da «Seção do DS».
- **Mapa de seções** — onde cada seção fala:
  `| Etapa | Tela/momento | Seção do DS | O que esta seção permite medir ou mostrar |`
- **Transições** — como o estudante passa de um app ao outro, sempre por uma ação nativa da história (notificação,
  link, compartilhar, abrir o app pelo ícone), nunca por um salto da plataforma (critério 2.3c):
  `| De | Para | Gatilho na história (notificação, link, compartilhar) | Etapa |`
- Um viewport por missão (campo do manifesto): todas as seções renderizam nele.
- Os componentes de cada tela vêm da seção daquela tela — `MessageBubble`, `TabBar` e `PhoneFrame` existem em mais
  de uma coleção, e a coluna de seção por tela é o que diz qual.

Um código confere tudo isto na spec e no one-pager: extra fora do vocabulário, acima do teto do ano, sem linha no
Mapa de seções ou sem transição que leve até ela.
