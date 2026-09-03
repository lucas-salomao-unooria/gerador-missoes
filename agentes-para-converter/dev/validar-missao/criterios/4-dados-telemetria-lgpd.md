# Dimensão D — Dados, Telemetria & LGPD

Referências do gabarito: `documentacao-latex/secoes/10-telemetria.tex` (dois
canais), `secoes/08-modelo-de-dados.tex`, `packages/sdk/src/types.ts`
(`TelemetryEvent`), `apps/api/src/telemetry/`, regras 1, 3 e 6 do AGENTS.md.

## DAD-01 [BLOQUEANTE] — Vocabulário de telemetria documentado
Verbos do contrato xAPI simplificado (`attempted`, `interacted`, `progressed`,
`completed`, `scored`) + objetos + campos de `dados`, com o significado de cada
um (na exp-01: `attempted` = entrou no aparelho, `completed` = dossiê visto).
Esse vocabulário vai no `experiencia.json` (`verbos`) e no README da
experiência. Spec sem vocabulário = ❌.

## DAD-02 [BLOQUEANTE] — Canal certo para cada dado
Dois canais que não se misturam: dado que ALIMENTA a mecânica em tempo real
(curadoria, adaptação) vai por rota operacional própria, síncrona e
transacional (como `POST /runs/:id/eventos`); dado de análise posterior vai
pelo SDK (`track` → batch 50/10s → Pub/Sub, sem garantia de ordem). Dwell nunca
passa pelo Pub/Sub. A spec classifica cada dado num dos dois canais; adaptação
em tempo real desenhada sobre o canal analítico = ❌.

## DAD-03 [BLOQUEANTE] — Tabelas com prefixo, tenancy e RLS
Tabelas novas com prefixo `exp_NN_`, `escola_id NOT NULL` + RLS; tabela que é
contrato entre duas experiências carrega os DOIS números
(`exp_01_exp_70_perfis_importados`). A spec lista as entidades a persistir com
seus campos principais — o dev não deve descobrir o modelo de dados durante a
codificação.

## DAD-04 [BLOQUEANTE] — Lista do que nunca vai ao bundle
Enumerar o que é segredo de servidor: gabarito, parâmetros ocultos do mundo,
calibragem, vieses, prompt de sistema (na exp-03 essa lista é verificada por
`grep` no `dist/` como parte da entrega). Contas cujo resultado anteciparia o
desfecho também sobem para a api (minuto da cidade, projeção de rotas). A spec
produz essa lista explicitamente.

## DAD-05 [BLOQUEANTE] — Servidor calcula, nunca aceita
Toda pontuação/perfil/correção é recalculada server-side a partir de medidas
brutas; o payload do cliente que trouxer o resultado pronto é RECUSADO (como
`CHAVES_DE_PERFIL` na exp-70). O `score` do `exp.concluir` é progresso, não
nota. A spec diz o que o cliente envia (medidas brutas) e o que o servidor
deriva.

## DAD-06 — Payload bruto e versão do instrumento
O dado bruto que permite reprocessar é guardado (na exp-70, `payload` da
sessão é a única fonte para recomputar o retrato quando `VERSAO_MAPEAMENTO`
subir), e toda medida derivada carrega a versão do instrumento/relatório.
A spec define o que acontece com dados antigos quando a versão sobe (aviso no
painel? reprocessamento?).

## DAD-07 [BLOQUEANTE] — PII de menor
`estudante_id` opaco (UUID) em todo dado; identidade sempre derivada do token
(o que o cliente mandar nesses campos é descartado); nome NUNCA em payload,
log ou JSONB de longa duração — no máximo primeiro nome, vivo só na camada de
ficção, nunca gravado (ADR-0002 da exp-70). Nenhuma PII em log em texto claro.

## DAD-08 [BLOQUEANTE] — Texto livre de menor
Texto livre digitado por menor NUNCA vai à telemetria analítica. Se precisa
existir (transcrição da exp-03), vai em tabela própria, lida só pelo professor
da escola, e a spec justifica a necessidade. Campos `dados` de payloads de
longa duração aceitam só número, booleano ou string de vocabulário FECHADO
(trava estrutural, não lista de proibidos).

## DAD-09 — Dado sensível (LGPD art. 11)
Se a missão toca saúde, sofrimento, família: sem agregado de gestor sem decisão
formal (o gabarito da exp-91: só o professor lê, nenhuma rota de gestor;
agregado anonimizado exige DPA e k-anonimato — "não sai de um GROUP BY").
Sinal de risco tem resposta FIXA definida (a IA não é chamada).

## DAD-10 — Retenção declarada ou lacuna assumida
Prazo de retenção por tabela nova, com a rotina que o cumpre — ou a lacuna
assumida por escrito (a plataforma já removeu um `expires_at` que nenhuma
rotina cumpria; prazo só existe junto com a rotina). Não inventar prazo
decorativo.

## DAD-11 — Concorrência especificada
Cliques duplos, duas abas, a sala inteira clicando junto: onde precisa de
`FOR UPDATE`, advisory lock por run/turma (o lock por turma na exp-70 evita os
25 caírem todos na bolha A; o débito de pergunta da exp-03 é transacional para
duas abas não gastarem a mesma pergunta). A spec aponta cada mutação de estado
e o que a serializa.

## DAD-12 — Estado sobrevive a F5
Persistência de estado da missão é server-side; recarregar nunca perde fase
nem repete medida. `localStorage` só para preferência de tela. A asserção
honesta de teste é "a conversa sobrevive a um F5" — porque aí ela veio do
banco.

## DAD-13 — O que o professor lê vem do canal síncrono
Relatórios/fichas do professor leem tabelas de domínio gravadas
transacionalmente (marcos, sessões, eventos do motor), nunca
`telemetria_eventos` (que hoje ninguém lê e não tem garantia de ordem).
A spec nomeia as tabelas/rotas que alimentam cada tela do professor.

## DAD-14 — Evento sem identidade é recusado
Nenhum dado de missão é gravado com `estudante_id` vazio/ausente (lição do
`ingest`, que aceita `""` — não repetir). Identidade vem do token em toda
rota de estudante.

## DAD-15 — Volume estimado
Ordem de grandeza de eventos por estudante por sessão e tamanho de payload —
para caber no lote de 50/10s do SDK e no INSERT multi-linha, na escala de 2-4k
simultâneos. Missão que emite evento por frame/scroll contínuo precisa de
agregação no cliente (como o dwell agrega antes de enviar).
