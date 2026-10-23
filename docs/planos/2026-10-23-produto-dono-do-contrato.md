# Produto dono do contrato — diagnóstico e plano de correção

23/10/2026. Cinco análises independentes (prompts, código, dados das sessões, histórico e consumidor do PRD) chegaram, cada uma sozinha, a «parcialmente procedente». A posição consolidada abaixo foi aprovada pelas cinco por unanimidade na primeira votação. Os fatos centrais foram reconferidos depois da votação. Acervo usado: 7 sessões com estado (53e011b6, 52455cbc, 60cfa7f4, b2e7b4a3, 4fd72a9a, e3980485, 76d9af6e); 5 delas chegaram ao design e 2 têm PRD.

## Hipótese testada

> Agentes de design preenchem lacunas e mudam a mecânica, mudando o produto sem revisar a especificação de produto, e por isso o PRD sai inconsistente. Design só deveria materializar UI/UX do que produto entregou. Isso aconteceu porque o PO não fazia o trabalho, e o design passou a cumprir esse papel.

**Veredito: parcialmente procedente.** O fato procede. A causa apontada é só metade, e o remédio «tudo que cria ou modifica produto vai para produto» vale para uma parte do design, não para o design inteiro.

## O que os dados mostram

| Fato | Medida |
|---|---|
| Decisões [D0-n] do fechamento de lacunas | 34 em 5 sessões (5/7/9/8/5): 28 verdes, 6 amarelas, 0 pedidos de re-spec ao Gate 0 |
| [D0-n] que criam regra ou fecham pendência do PO sem decisão dele | 9 (ex.: teto de 15 palavras, moldura de 10% e 45 s na exp02ef1b; retenção LGPD, 6 métricas do painel e revezamento de 4 na exp03em1b) |
| [D0-n] que contrariam produto | 1 (exp02em1b D0-7 confirma o StoryPoll que o PO mandou não implementar em 21/10). Um segundo caso (exp03em1b D0-9, 48 px) contraria o padrão da plataforma, não o one-pager |
| [D0-n] que aplicam decisão do PO nunca gravada | 2 (exp02em1b D0-5 e D0-6: 90 s e 45 palavras do de acordo de 21/10). O D0-4 da exp02ef1b torna PQ-01..05 «contratuais» a partir de um «Tudo de acordo» genérico: fecha PROPOSTA sem decisão |
| [D0-n] citados no one-pager | 0 nas 5 sessões |
| `[CONFLITO — pedido do PO × one-pager]` registrados | 0 nas 7 sessões (a instrução está nas notas de passagem de 6) |
| Bloco 13 (decisões do D0) presente na spec final | 3 de 5. Perdido em 60cfa7f4 e 4fd72a9a (linhas-perdidas), mas o PRD da 4fd72a9a cita D0-1 e D0-6 |
| Marcadores abertos entregues ao design | [PARÂMETRO] no one-pager: 3, 4 e 3 (60cfa7f4, 4fd72a9a, 76d9af6e). Na spec do Gate 0: 4–6 [PARÂMETRO] e 5–13 [PROPOSTA] |
| Copy | 98 a 173 linhas por missão; 43%–70% sem origem literal em produto (teto: a comparação é literal, e a maioria é microcopy). Textos do §4 do one-pager: 73/85 na copy e 69/85 no protótipo |
| Fluxo | 55 estados que a spec não nomeia, quase todos decomposição. Guardas mudadas: exp02ef1b A13 e A20; exp02em1b monta o StoryPoll |
| Pedido do PO em design (exp02ef1b, 23/10 13:24) | Textos novos: 0 ocorrências em núcleo, one-pager e spec; de 1 a 13 em design, handoff e PRD. Dos ~10 «textos atuais», 9 tinham sido escritos pelo design |
| Cadeia 30% → 25% (H1 do §17) | Nasce em produto (PQ-01 >25% [PROPOSTA] na spec do Gate 0) → D0-4 → handoff → corpo do PRD com 25%, anexo com 30%. O juiz A117 deu 🟢 |
| Liberação de produto | Conta produto 1 de 5; conta design «como Produto» 2; exceção do admin 2. As exceções do admin não são omissão do PO |

## Onde a hipótese não se sustenta

- **O produto sai aberto por regra de prompt.** Desde fa39727 (21/09), o `014_secoes_apoio.md:49` manda escrever `[PARÂMETRO — a definir por produto]` em vez de inventar. Nenhum passo exige que o PO feche esses marcadores antes do design. Alguém precisa fechar, e hoje isso acontece no D0. Os 15 palavras, 10% e 45 s da exp02ef1b eram as sugestões que o próprio produto escreveu: o design ratificou, não inventou.
- **O PO decidiu e a esteira perdeu a decisão.** Na exp02em1b, 90 s, 45 palavras e «StoryPoll — não implementar» foram ditos no de acordo de 21/10. O one-pager continua com [PARÂMETRO] e com o StoryPoll 12 vezes. Nada grava a decisão do de acordo.
- **A maior parte do design é UI/UX legítimo**, em ordem de grandeza perto de 60%: cerca de 20 das 34 decisões D0, as 16–23 telas por missão, a decomposição em estados, a CAA, os wireframes, o protótipo e a microcopy. Pôr tudo em produto multiplicaria o one-pager e as rodadas de comitê.
- **Parte das incoerências do PRD nasce fora do design.** O 25% nasceu em produto. As 35 palavras da exp06ef1b se perderam no consumo (jornada e copy) e o dev não recuperou. O PRD inventa estados sozinho.
- **O D0 nasceu de arquitetura, não de omissão.** 4dcdb18 (16/09) trouxe o D0 «para a esteira não parar seis vezes», uma semana antes de existir parecer humano. O pacote de origem previa volta ao Gate 0, e ela nunca foi implementada.
- **A rota «Devolver a produto» funciona quando usada**: 2 vezes em 23/10, e na exp02em1b a mudança chegou a todos os documentos.

## Causas raiz

1. **Contrato de produto aberto por desenho.** [PARÂMETRO] e [PROPOSTA] saem de produto. O de acordo não obriga a fechá-los, e o que o PO decide nele não é gravado no one-pager nem na spec.
2. **A volta de design para produto nunca foi implementada.** Re-spec existe só no prompt (065:91); `aguarda_gate` é informativo; ticket com dono gate-estrutural é RETRABALHO_EXTERNO. Resultado: 0 re-specs em 34 decisões.
3. **Mandato e controle frouxos do D0.** A tabela de autoridade (065:46-57) deixa em verde ou amarelo duração, dados e texto do professor. O controle depende do rótulo que o próprio agente escolhe: `tools/decisoes.py:176` só barra `mecanica` e `curriculo` por igualdade exata, e `mecanica_param` passou.
4. **A spec tem dois autores sob um nome só.** `spec_missao` é reescrita pelo A066 e pelo A068 e publicada como `produto/05-spec-missao.md`. Volta ao Gate 0 em todo refazer de design (`reexecucao.py:524-526`) e perde o bloco 13 quando há linhas-perdidas.
5. **Pedido do PO feito em design ou dev não tem rota em código para produto.** `edicao_pontual.py:22-28` fecha o design nos documentos de design; o Refazer não passa pela triagem; [CONFLITO] é só instrução, e o A094 cobra o contrário.
6. **Os consumidores de dev são autores sem gate de origem.** Nenhum gate determinístico confere números e textos do corpo do PRD contra o anexo ou o contrato.
7. **Governança diluída.** A conta design assina produto desde 58c3ed1 (24/09), e a conferência de leitura do de acordo foi desligada em 05feeaf (25/09).

Linha do tempo: 16/09 D0/D9 sem volta (4dcdb18) · 21/09 marcador PARÂMETRO (fa39727) · 24/09 design assina produto (58c3ed1) · 25/09 conferência desligada (05feeaf) · 07/10 [CONFLITO] só como orientação (85e2f1c) · 19/10 editor pontual por etapa sem cascata (3e43585) · 22/10 D0 aplica o parecer (ea5b248) · 22–23/10 PRs #56–#65 apagando conflitos entre gates.

## Agente por agente

| Agente | Classe | Destino |
|---|---|---|
| A065 D0 (fechamento de lacunas) | misto | Classes de produto (parâmetro, duração, teto, dados e retenção, painel, PQ e KPI, texto do professor, regra por inferência, revezamento, mecânica e currículo) vão para produto. Fica um D0-UX (gesto, scaffolding, acessibilidade de componente, dispositivo) |
| A066 / A068 (splits) | mecanismo que modifica produto | A spec de produto fica imutável depois do de acordo; o que é do design vai para chave própria |
| A067 D9 (ambiente) | detalha; cria produto só de forma latente | A ficha fica no design. A escolha de ambiente novo e de mini-jogo vai para produto |
| A070 brief de ofício | UI/UX | Fica |
| A071 jornada | misto | Telas ficam. Regras e fases do mini-jogo vão para produto |
| A072 fluxo | misto | Fica, com gate de arestas contra o bloco 2 |
| A073 / A077 / A078 copy | misto | Microcopy fica. Textos-chave (§4, Canal B, nº de opções, podcast) são travados por código |
| A074 CAA, A076 Stitch, A079–A084 | UI/UX | Ficam |
| A075 telas | misto | Fica, com gate de regras «habilitado apenas com» |
| A085–A091 banca e QA | julgam | Ticket de produto vira devolução real |
| A094 fidelidade de design | coage o design a mudar produto | Confere só os itens de design |
| A045 spec (produto) | segundo autor dentro de produto | Fica, lendo `celulas-consumidas.md`; marcadores abertos entram no de acordo |
| A100a / A104 / A113 (dev) | modificam produto | Montam, não decidem: gate de origem |

## Plano — 9 PRs, do mais barato ao mais estrutural

Os PRs 1 a 4 não mudam papéis. O PR 6 é o maior e depende dos PRs 2 e 3.

**PR 1 — medir antes de mudar (só leitura).** Versionar a matriz de propagação como `tools/propagacao.py`, com quatro relatórios por sessão:
- pedido do PO × documentos;
- classe real de cada [D0-n];
- números e textos do corpo do PRD e do handoff sem origem no contrato;
- [D0-n] citados a jusante e ausentes da spec.

Começa sem bloquear. A linha de base é o quadro acima.

**PR 2 — consertar as perdas silenciosas.**
- O D0 emite só o bloco 13, e a spec passa a ser montada em código (Gate 0 + 13 + 14), como o 7fdcb19 fez com o D9. Isso elimina o linhas-perdidas que derruba o bloco 13. A marca «Resolvido em [D0-n]» das células passa a viver num mapa célula → D0.
- `tools/decisoes.py` valida a classe por lista branca e prefixo (`mecanica*`, `curriculo*`, `parametro*`). Todo [D0-n] que fecha [PARÂMETRO] ou promove [PROPOSTA] sem parecer datado é tratado como produto, inclusive nas classes duração, dados e acessibilidade.
- Gate: [D0-n] citado a jusante precisa existir na spec apontada.
- Até o PR 5, a mudança em linha do Gate 0 vira `[ABERTO — dono: PO]` visível no cartão do parecer de design, sem bloquear fora de ESTEIRA_ESTRITA, para não sumir em silêncio.

**PR 3 — o de acordo de produto fecha o contrato e grava.**
- O parecer lista cada [PARÂMETRO], [PROPOSTA] e [ABERTO — dono: PO] com a sugestão do agente e as opções aceitar, outro valor, recusar ou deixar para o design.
- As respostas viram correção pontual determinística de produto no one-pager e na spec do Gate 0 («valor — PO, parecer de <data>»).
- Um «Tudo de acordo» genérico não aprova PROPOSTA.
- A decisão sobrevive ao refazer, com linha de base.
- Reverte o 065:67 (ea5b248).

**PR 4 — PRD e handoff montam, não decidem.** Gate determinístico com quatro conferências:
- todo número de regra e texto-chave do corpo existe no contrato;
- hipóteses e metas são iguais às do anexo §17 e do 9f;
- os tetos do §15 estão presentes;
- os estados da §6 são iguais aos do contrato.

Divergência vira item obrigatório da §19, com dono produto. Até o PR 6, a citação de bloco 13 em `produto/05-spec-missao.md` é legítima. Pode ser adiantado: é independente dos outros.

**PR 5 — pedido do PO em design ou dev passa por triagem, item a item, com rota de código para produto.** Uma regra determinística conservadora decide o que vai para produto: item cujo texto-alvo existe em núcleo, one-pager ou spec, ou que muda número, regra, gatilho, estado, opções, habilidade, Canal B ou podcast. O PO vê a divisão antes de confirmar. O A094 confere só os itens de design e aceita «aplicado a montante». O destino dos itens de produto é a decisão D4 abaixo.

**PR 6 — dividir o D0 por dono e tornar a spec de produto imutável.**
- As classes de produto do D0 viram um passo novo ao fim do SpecLoop (`prompts/produto/046_completude_spec.md`), antes da banca e do parecer.
- O que exigir decisão do PO cai na lista do PR 3.
- No design fica o D0-UX, gravado num anexo de design.
- `spec_missao` fica igual à aprovada, e o reset de `reexecucao.py:524-526` vira no-op.
- O PRD aponta para a spec de produto mais o anexo de design.
- Custo: uma chamada grande a mais em cada refazer de produto.

**PR 7 — textos-chave travados; fluxo e telas sem mudar contrato.**
- Tabela de textos-chave com ID no one-pager (aspas do §4, Canal B do §12a, nº de opções, podcast), copiada por código para a copy.
- Mudança nesses textos sai como [PROPOSTA] pela rota do PR 5.
- O lint de produto acusa texto aprovado acima do teto da faixa antes do de acordo.
- Gate de arestas do fluxo e de regras de habilitação das telas contra o bloco 2.

**PR 8 — D9 e jornada sem poder de produto.** Ambiente novo, classe mini-jogo e regras e fases do jogo passam a núcleo e spec. O D9 emite só o bloco 14.

**PR 9 — governança (condicional à D9).** Rever quem assina produto, a exceção do admin com 🔴 e a conferência de leitura quando há pendência aberta.

Como medir cada PR: regressão nas 5 sessões e nos 2 PRDs do acervo (`scripts/regressao_gates.py`), mais os mutantes «apagar bloco 13», «classe mecanica_x», «H1 25×30», «35 palavras omitidas» e «opção Lugar removida». Antes do PR 6, rodar as 3 missões do plano de 10/10 de ponta a ponta, com tempo e custo por etapa (`custo_missao`).

Custos medidos hoje:

| Execução | Tempo | Custo |
|---|---|---|
| Refazer de produto | 853–2.032 s | US$ 2,0–3,1 |
| Produto pontual | 614–1.418 s | — |
| Refazer de design | 1.124–2.548 s | — |
| Design pontual | 278–1.448 s | — |

Na exp02ef1b foram 6 refazeres de design em 23/10, quatro deles por causa de um pedido de texto.

## Decisões do usuário

- **D1 — Fronteira do texto de produto.** Todo texto que a criança ou o professor lê, ou só os textos-chave com ID, deixando a microcopy no design? Recomendação unânime: só os textos-chave.
- **D2 — D0.** Dividir (PR 6) ou manter no design com lista branca e itens para produto? E aceitar uma chamada a mais por refazer de produto?
- **D3 — De acordo.** Pode sair com PARÂMETRO ou PROPOSTA abertos? «Aceitar todas as sugestões» com um clique conta como decisão datada do PO?
- **D4 — Pedido do PO em design ou dev que toca produto.**
  - A) Cascata automática: produto pontual, depois design e dev pontuais (cerca de 15 a 50 min a mais por pedido).
  - B) Bloquear e exigir Devolver.
  - C) Só [CONFLITO] gravado em código e confirmado no de acordo.
- **D5 — Padrões da plataforma.** `defaults-missao.md` é rascunho v0 e é a base de 16 das 34 decisões D0. Aplicar automaticamente em produto ou exigir aceite por item?
- **D6 — Retenção de dados, métricas do painel, cortes de PQ e KPI e revezamento.** Decididos por missão em produto, como padrão de plataforma ou em dev?
- **D7 — Estados do fluxo e fluxo do professor E0-PROF.** Contrato de produto, ou detalhe de design com PROPOSTA só quando muda o que o aluno faz ou vê?
- **D8 — Ambiente novo e mini-jogo.** Passam formalmente para produto?
- **D9 — Governança.** A conta design continua assinando produto? E a exceção do admin com 🔴?
- **D10 — Fonte da verdade para codar.** O PRD é mandatório, ou a spec de produto vence?
- **D11 — Casos concretos da exp02ef1b.** H1 com 30% ou 25%; 5A com 3 opções («Lugar») ou 2; E5-ALU-02 trava em «Criança lendo» ou deixa errar (dimensão D3); teto de 15 palavras e reescrita do Canal B.
- **D12 — Caso concreto da exp02em1b.** O StoryPoll recusado em 21/10 continua no one-pager, na spec, na jornada e no fluxo.
- **D13 — Missões já geradas** (exp02ef1b; exp06ef1b em codificação). Reconciliar one-pager e spec, regenerar depois dos PRs ou registrar na §19?
- **D14 — Escopo.** Teto de tempo e custo por missão, autorização da ordem dos PRs e uso das 5 sessões como acervo de regressão.

## Recomendação para cada decisão

Cada recomendação parte dos dados acima. Aprovadas em bloco, tornam o plano executável sem novas perguntas; qualquer uma pode ser trocada sem mexer nas outras.

| # | Recomendação | Por quê |
|---|---|---|
| D1 | Só os textos-chave com ID (§4, Canal B, nº de opções, podcast, roteiro do professor). A microcopy fica no design | Unanimidade dos cinco. O one-pager tem de 14 a 36 textos entre aspas, contra 98 a 173 linhas de copy, e a maioria é microcopy |
| D2 | Dividir o D0 (PR 6), mas só depois dos PRs 2 e 3. Até lá, a lista branca do PR 2 barra as classes de produto no design | Isso tira do design as 9 decisões que criam produto e as 2 que aplicam decisão não gravada, sem levar a produto as cerca de 20 que são UI/UX. O custo de uma chamada a mais por refazer de produto é medido antes de abrir o PR |
| D3 | Com ESTEIRA_ESTRITA, o de acordo não sai com [PARÂMETRO] ou [PROPOSTA] sem resposta. «Aceitar as sugestões» vale como decisão datada quando a lista aparece no cartão e o clique é sobre ela. «Tudo de acordo» em texto livre não aprova proposta | Cadeia do 30%→25%: uma proposta virou contrato por um «Tudo de acordo» genérico (D0-4 da exp02ef1b) |
| D4 | (A) Cascata: os itens de produto vão para correção pontual de produto e depois para design e dev pontuais. Se a triagem não souber o dono, aplica-se (B) | É a única opção que mantém one-pager e spec como fonte da verdade. A rota «Devolver» funcionou nas 2 vezes em que foi usada. Hoje um pedido de texto custou 4 refazeres de design na exp02ef1b (cerca de 2 h); a cascata custa de 15 a 50 min |
| D5 | Validar `defaults-missao.md` uma vez com o usuário (é rascunho v0). Depois disso, aplicar automaticamente em produto, listado no de acordo como «padrão aplicado», sem aceite por item | É a base de 16 das 34 decisões D0. Aceite por item multiplicaria o trabalho do PO sem informação nova |
| D6 | Retenção e LGPD e protocolo de revezamento viram padrão de plataforma (`references/`). Métricas do painel docente e cortes de PQ e KPI ficam por missão, em produto | Retenção e revezamento se repetem entre missões; na exp06ef1b o PO recusou revezamento e o D0 o prescreveu em outras duas. Painel e PQ dependem do que a missão mede |
| D7 | Estados do fluxo são detalhe de design, com [PROPOSTA] só quando mudam o que o aluno faz ou vê (gate do PR 7). O fluxo E0-PROF sai do prompt de design e vira padrão de plataforma em `references/` | 55 estados novos são quase todos decomposição; as mudanças reais de guarda foram 3 e o gate as pega. E0-PROF já é fixo para toda missão |
| D8 | Sim: ambiente novo e mini-jogo passam para produto | O D9 ficou dormente em 5 de 5 sessões: custo baixo, e fecha uma porta de criação de produto |
| D9 | A conta design pode continuar liberando produto, mas o cartão e o dossiê marcam «liberado sem a conta produto» em 🟡. A exceção do admin com 🔴 em produto exige justificativa escrita | Atende à falta de disponibilidade do PO sem esconder quem liberou: hoje 1 de 5 liberações vem da conta produto |
| D10 | A fonte da verdade é a spec de produto mais o anexo de design. O PRD deriva delas, e divergência é defeito (gate do PR 4) | É o que o PR 4 torna verificável. O PRD da exp02ef1b se contradiz (25% no corpo, 30% no anexo) |
| D11 | Na exp02ef1b, reconduzir por produto pontual quando o PR 5 existir: textos e 2 opções na 5A como o PO pediu em 23/10 (decisão explícita mais recente); H1 e PQ-01 com 30% (o aprovado no §17; os 25% eram proposta); E5-ALU-02 deixa escolher o atributo errado, como manda a spec, para a dimensão D3 discriminar; Canal B volta ao texto aprovado | Segue a regra «vale o pedido mais novo do PO, mas no documento de produto». Travar em «Criança lendo» zera o poder de medida da D3 |
| D12 | Remover o StoryPoll da exp02em1b por produto pontual, citando a decisão do PO de 21/10 15:43 | Decisão explícita do PO que a esteira perdeu |
| D13 | exp02ef1b: reconciliar como no D11. exp06ef1b (em codificação): registrar as 35 palavras na §19 e avisar quem codifica; não regenerar | Regenerar uma missão em codificação custa mais que o defeito, que é um teto de texto |
| D14 | Ordem 1→9. Acervo de regressão com as 5 sessões e os 2 PRDs. Teto: produto até +1 chamada por refazer, medido no PR 6 antes do merge | Os PRs 1 a 4 não mudam papéis e já fecham as perdas silenciosas e a incoerência do PRD |
