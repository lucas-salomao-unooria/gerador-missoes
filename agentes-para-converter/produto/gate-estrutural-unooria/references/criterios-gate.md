# Critérios do Gate Estrutural — Rubrica v1.16 — fechamento de spec incorporado

## 1. ESTRUTURA — Alinhamento com o Framework de 6 Etapas

|#|Critério|Tipo|Teste prático|
|-|-|-|-|
|1.1|**Desafiar** — Existe uma narrativa de abertura que contextualiza a missão do estudante|Obrigatório|O aluno entende o que ele vai viver e por quê antes de começar?|
|1.2|**Navegar** — O aluno vivencia uma experiência simulada (não lê/assiste passivamente), **e** o one-pager descreve a interação em nível de tela: o que o aluno vê, o que ele faz (clica, arrasta, seleciona, escreve), e o que muda na tela depois da ação|Obrigatório|**Filtro de passividade:** o aluno interage ativamente com o ambiente ou só consome conteúdo? **Filtro de detalhamento:** para cada ação do aluno, o one-pager descreve (a) o que ele vê na tela antes de agir, (b) o verbo da interação (clicar, arrastar, selecionar, digitar), e (c) o que muda na tela depois? Dizer "aluno escolhe X" sem descrever como é insuficiente — o dev e o designer precisam construir a partir do one-pager sem adivinhar a mecânica. Se o filtro de passividade passa mas o de detalhamento não, marcar ⚠️ (não ❌).|
|1.3|**Decidir** — Existe um ponto de decisão claro com agência real do aluno|Obrigatório|Se tirar a decisão, a missão continua funcionando igual? (se sim, ❌)|
|1.4|**Resultado / Aha moment** — A decisão gera consequência visível dentro da missão|Obrigatório|O aluno vê o impacto da sua escolha? Caminhos diferentes geram resultados diferentes?|
|1.5|**Explicar** — Existe revelação do racional (por que aconteceu o que aconteceu)|Obrigatório|Após a consequência, o aluno entende o mecanismo por trás?|
|1.6|**Refletir / Produto final** — O aluno registra conclusão ou reflexão do aprendizado por meio de uma provocação concreta|Obrigatório|Existe um momento de registro que evidencia o que o aluno construiu/entendeu? A reflexão deve ser uma provocação concreta — uma situação nova onde o aluno precisa aplicar o que vivenciou (ex: "O Léo quer baixar um app que pede acesso à câmera e aos contatos. O que você diria pra ele?"). Campo aberto genérico ("o que você aprendeu?") → ⚠️. Quiz de múltipla escolha → ⚠️.|
|1.7|**Papel de cada agente definido** — Cada etapa indica quem faz (Professor, Unooria, ou ambos)|Obrigatório|Está claro quem conduz cada momento? O professor sabe o que fazer e quando?|

---

## 2. AMBIENTE E VERBOS (subset — 2.1 e 2.6 apenas)

|#|Critério|Tipo|Teste prático|
|-|-|-|-|
|2.1|**Ambiente é um dos 6 suportados, com conta própria e comportamento fiel** — Lista fechada: Instagram, YouTube, Roblox, ChatGPT, TikTok, WhatsApp. Nenhum outro ambiente passa.|Obrigatório|**Teste de lista fechada (aplicar PRIMEIRO):** o ambiente é literalmente um dos 6? Se não → ❌ direto, sem aplicar os demais testes. **Teste de plataforma real:** o aluno diria "eu uso isso"? **Teste de posse:** a conta é do aluno ou de um personagem? Se personagem → ❌. **Teste de fidelidade comportamental:** a mecânica se comporta como a plataforma real (feed rola um post por vez, não vários lado a lado)? **Teste de permanência ponta a ponta:** a experiência inteira (6 etapas) acontece dentro do ambiente? Telas/painéis "da Unooria" no meio → ❌. Escapes aceitáveis: tela de contexto antes da simulação e campo de reflexão final depois.|
|2.6|**Verbos nativos da plataforma** — As ações do aluno usam verbos/gestos que existem de fato na plataforma real (curtir, salvar, compartilhar, comentar, seguir, assistir, publicar)|Obrigatório|A ação existe na plataforma real, ou foi inventada pra servir à avaliação (ex: "marcar como suspeito", "taggear fonte")? Mecânica pedagógica inventada disfarçada de interação de plataforma → ❌.|

### Falso-positivos frequentes em 2.1:

- **Plataforma real fora da lista:** LinkedIn, Canva, Google Notícias, apps de órgão público → ❌ mesmo passando nos demais testes.
- **Escape nas etapas finais:** missão respeita o ambiente nas etapas iniciais e cria "Painel da Unooria" na virada → ❌ (teste de permanência).
- **Personagem em vez de conta do aluno:** aluno navega o perfil de um personagem da narrativa → ❌ (teste de posse).
- **Mecânica divergente:** feed mostra vários posts lado a lado que a rede real não faz → ❌ (teste de fidelidade).

---

## 4. LOGÍSTICA DE AULA (subset — 4.5, 4.6, 4.7 apenas)

|#|Critério|Tipo|Teste prático|
|-|-|-|-|
|4.5|**Cronograma de aula (30-35 min) com 7 blocos** — Tabela com: preparação do professor (pré-aula), ambiente da sala, laboratório, explicação, debate, mediação, reflexão. Preparação é fora dos 30-35 min. Sobreposições declaradas.|Obrigatório|O professor consegue olhar a tabela e saber como distribuir o tempo? Os 7 blocos estão presentes e somam ≤ 30-35 min (excluindo preparação)? Sobreposições declaradas?|
|4.6|**Formato de 2 aulas com breakpoint e fallback** — Aula 1 (imersão: Desafiar → Navegar → Decidir → Resultado) e Aula 2 (debate: recapitulação + Explicar + Debate + Reflexão). Breakpoint explícito, estado salvo, modo aula única com trade-offs.|Obrigatório|**Teste de breakpoint:** momento exato + tela de encerramento narrativamente coerente? **Teste de independência:** Aula 2 funciona com intervalo de até 7 dias? Podcast previsto como ponte? **Teste de estado:** o que a plataforma preserva entre aulas? **Teste de fallback:** modo aula única com trade-offs explícitos?|
|4.7|**Podcast de recapitulação** — Roteiro completo 3-5 min (máx 6 min), estilo NotebookLM (2 apresentadores), 5 blocos: abertura (~30s), recapitulação da dinâmica (~1-1.5 min), aha moment/revelação (~1-1.5 min), provocação de ponte (~30s-1 min), encerramento (~15s)|Obrigatório|**Teste de completude:** 5 blocos com falas escritas (não descrição)? **Teste de formato:** diálogo entre 2 apresentadores com falas alternadas? **Teste de conteúdo:** revelação explica o mecanismo oculto de forma acessível à faixa? Provocação aquece pro debate sem entregar conclusão? **Teste de tom:** usa "estudante" (nunca "aluno")? Sem lição de moral? Referencia ambiente pelo nome? ≥ 1 momento de surpresa genuína? **Teste de duração:** cabe em 3-5 min lido em voz alta? > 6 min → ❌. **Teste de cenário degradado:** funciona só com áudio?|

### Falso-positivos frequentes em 4.5-4.7:

- **Intenção sem conteúdo:** "podcast de recapitulação" listado como recurso sem roteiro escrito → ⚠️. Seção inteira ausente → ❌.
- **Cronograma sem sobreposição declarada:** mediação durante laboratório contada como sequencial → soma ultrapassa 30-35 min.
- **Breakpoint abrupto:** Aula 1 termina sem tela de encerramento provisório.

---

## 7. EVIDÊNCIA E REGISTRO

|#|Critério|Tipo|Teste prático|
|-|-|-|-|
|7.1|**Registro automático de percurso** — A plataforma captura as ações do aluno sem trabalho extra do professor|Obrigatório|O professor precisa anotar algo manualmente?|
|7.2|**Métricas internas sem virar avaliação formal** — Rankings/pontuações dentro da simulação OK, desde que nunca virem nota escolar ou conceito formal|Obrigatório|Alguma métrica da simulação vaza para avaliação formal (boletim, conceito)?|
|7.3|**Evidências listadas** — O one-pager descreve o que será capturado|Obrigatório|Está claro quais dados o professor terá acesso ao final?|
|7.4|**Contribuição ao perfil comportamental** — Sinais comportamentais (não temáticos) identificados|Obrigatório — aplicado como sugestão|Liste 1-2 sinais comportamentais candidatos que a mecânica da missão já gera, mesmo que o perfil unificado ainda não exista na plataforma.|

---

## 9. VIABILIDADE E PROTOTIPAÇÃO

|#|Critério|Tipo|Teste prático|
|-|-|-|-|
|9.1|**Spec implementável sem decisão de produto aberta** — Requisitos técnicos, regras de transição e ownership estão fechados o suficiente para designer/dev construírem sem inventar comportamento que altere a experiência.|Obrigatório|**Teste de implementação cega:** percorra cada ato e verifique obrigatoriamente: (a) cardinalidades, mínimos/máximos e bloqueios; (b) regra de geração/seleção de outputs; (c) estados incompletos e caminhos degenerados; (d) o que faz quem termina antes de um handoff coletivo; (e) qual conta/ator publica, envia ou altera cada elemento visível; (f) permissões antes/durante/depois de handoffs; (g) fallback quando pré-condições não são atendidas. Se designer/dev precisarem escolher uma regra que mude a experiência, → ❌. Uma lista de features sem essas regras não cumpre.|
|9.2|**Estágio IA sinalizado** — V1 vs V2|Desejável|Se o dev perguntar "o que entra primeiro?", a resposta está no documento?|
|9.3|**Hipóteses de validação listadas**|Desejável|O time sabe o que observar no teste?|
|9.4|**Estados de falha mapeados** — Para cada pré-condição do fluxo, o documento descreve o que acontece quando ela não é atendida: plataforma fora do ar, conteúdo que não carrega, professor que não libera a tempo, aluno que perde conexão no meio de uma etapa.|Obrigatório|**Teste de falha:** para cada ato que depende de dado, conexão, conteúdo gerado ou ação de outro ator, existe tratamento explícito do caso em que a dependência falha? Se não há nenhum estado de falha em toda a missão → ❌. Se há pelo menos um mapeado mas outros evidentes foram omitidos → ⚠️.|

### Falso-positivo frequente em 9.4:
"A plataforma exibe mensagem de erro" sem dizer *qual* mensagem, *o que o aluno faz* depois, e *se o progresso se perde* — isso não é tratamento de falha, é declaração de intenção de tratar.

---

## 10. CONTEXTO DE INFRAESTRUTURA ESCOLAR

|#|Critério|Tipo|Teste prático|
|-|-|-|-|
|10.1|**Cenários de dispositivo mapeados** — ≥ 3 cenários: (a) 1:1, (b) 2-4 por dispositivo, (c) projeção única|Obrigatório|Para cada cenário, está claro o que muda na dinâmica?|
|10.2|**Experiência degradada ≠ quebrada** — No compartilhamento, missão ainda entrega a descoberta central|Obrigatório|3 alunos dividem 1 computador — a missão ainda funciona pedagogicamente?|
|10.3|**Modalidade coerente com infraestrutura** — Individual/dupla/grupo considera realidade de dispositivos|Desejável|A missão exige individual mas escola tem 1 computador pra 4 alunos?|

---

### Falso-positivo crítico em 9.1

“Os requisitos técnicos estão listados” não significa “a spec está fechada”. Exemplos que devem bloquear: não dizer se o output do próprio estudante entra numa comparação; pedir exatamente N itens sem definir bloqueio/progresso para N incompleto; handoff coletivo sem estado útil para quem termina cedo; conteúdo publicado sem definir qual conta o publica. Esses pontos não podem ser delegados ao wireframe.

## RESUMO DE CONTAGEM — Gate Estrutural

| Categoria | Obrigatórios | Desejáveis |
|-|:-:|:-:|
| 1. Estrutura | 7 | 0 |
| 2. Ambiente e verbos | 2 | 0 |
| 4. Logística de aula | 3 | 0 |
| 7. Evidência e registro | 3 + 1 condicional | 0 |
| 9. Viabilidade | 2 | 2 |
| 10. Infraestrutura | 2 | 1 |
| **TOTAL** | **19 + 1 condicional** | **3** |
