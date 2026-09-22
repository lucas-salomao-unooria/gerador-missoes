# Critérios do Gate Estrutural — Rubrica v1.16 — fechamento de spec incorporado

## 1. ESTRUTURA — Alinhamento com o Framework de 6 Etapas

|#|Critério|Tipo|Teste prático|
|-|-|-|-|
|1.1|**Desafiar** — Existe uma narrativa de abertura que contextualiza a missão do estudante|Obrigatório|O aluno entende o que ele vai viver e por quê antes de começar?|
|1.2|**Navegar** — O aluno vivencia uma experiência simulada (não lê/assiste passivamente), **e** o one-pager descreve a interação em nível de tela: o que o aluno vê, o que ele faz (clica, arrasta, seleciona, escreve), e o que muda na tela depois da ação|Obrigatório|**Filtro de passividade:** o aluno interage ativamente com o ambiente ou só consome conteúdo? **Filtro de detalhamento:** para cada ação do aluno, o one-pager descreve (a) o que ele vê na tela antes de agir, (b) o verbo da interação (clicar, arrastar, selecionar, digitar), e (c) o que muda na tela depois? Dizer "aluno escolhe X" sem descrever como é insuficiente — o dev e o designer precisam construir a partir do one-pager sem adivinhar a mecânica. Se o filtro de passividade passa mas o de detalhamento não, marcar ⚠️ (não ❌).|
|1.3|**Decidir** — Existe um ponto de decisão claro com agência real do aluno|Obrigatório|Se tirar a decisão, a missão continua funcionando igual? (se sim, ❌)|
|1.4|**Resultado / Aha moment** — A decisão gera consequência visível dentro da missão|Obrigatório|O aluno vê o impacto da sua escolha? Caminhos diferentes geram resultados diferentes?|
|1.5|**Explicar** — Existe revelação do racional (por que aconteceu o que aconteceu)|Obrigatório|Após a consequência, o aluno entende o mecanismo por trás?|
|1.6|**Refletir / Produto final** — O estudante registra conclusão ou reflexão do aprendizado por meio de uma provocação concreta|Obrigatório|Existe um momento de registro que evidencia o que o estudante construiu/entendeu? A reflexão deve ser uma provocação concreta — uma situação nova onde o estudante precisa aplicar o que vivenciou (ex: "O Léo quer baixar um app que pede acesso à câmera e aos contatos. O que você diria pra ele?"). **3 armadilhas que passam como provocação mas não são:** Campo aberto genérico ("o que você aprendeu?") → ⚠️. Quiz de múltipla escolha → ⚠️. Provocação que contém a resposta na pergunta ("Fulana SÓ curte vídeos de gatinho, o que vai acontecer com o feed dela?") → ⚠️. **Teste:** um estudante que NÃO fez a missão consegue responder corretamente só pela pergunta? Se sim, a provocação não testa aplicação — testa leitura.|
|1.7|**Papel de cada agente definido** — Cada etapa indica quem faz (Professor, Unooria, ou ambos)|Obrigatório|Está claro quem conduz cada momento? O professor sabe o que fazer e quando?|

---

## 2. AMBIENTE E VERBOS (subset — 2.1 e 2.6 apenas)

|#|Critério|Tipo|Teste prático|
|-|-|-|-|
|2.1|**Ambiente é um dos 5 suportados, com conta própria e comportamento fiel** — Lista fechada, com a seção do design system entre parênteses: Instagram (`instanooria`), YouTube (`unitube`), ChatGPT (`chatgpt`), TikTok (`tiktooria`), WhatsApp (`whatsappmobile`). Nenhum outro ambiente passa. Roblox não tem seção e reprova aqui; se voltar, volta por `ambientes.md`, nunca por este critério. **TikTok:** a seção existe sem ponte em `@edu/ui` — a missão passa no 2.1 e declara a ponte como pré-requisito com responsável (DES-01).|Obrigatório|**Teste de lista fechada (aplicar PRIMEIRO):** o ambiente é literalmente um dos 5? Se não → ❌ direto, sem aplicar os demais testes. **Teste de plataforma real:** consulte `literatura-cognitiva.md` §10 (uso de plataforma por idade, TIC Kids Online Brasil 2024). O ambiente está entre os de maior uso para a faixa? Se está, ✅. Zona de transição (6º–7º ano) → ✅ com justificativa na seção 18. Fora da tabela (ex.: Instagram pessoal no 3º ano) → ⚠️; e ❌ se, além disso, a missão pressupõe conta própria numa faixa em que a maioria não tem perfil, sem tratar a primeira conta dentro da ficção. **Teste de posse:** a conta é do aluno ou de um personagem? Se personagem → ❌. **Teste de fidelidade comportamental:** a mecânica se comporta como a plataforma real (feed rola um post por vez, não vários lado a lado)? **Teste de permanência ponta a ponta:** a experiência inteira (6 etapas) acontece dentro do ambiente? Telas/painéis "da Unooria" no meio → ❌. Escapes aceitáveis: tela de contexto antes da simulação e campo de reflexão final depois.|
|2.6|**Verbos nativos da plataforma** — As ações do aluno usam verbos/gestos que existem de fato na plataforma real (curtir, salvar, compartilhar, comentar, seguir, assistir, publicar)|Obrigatório|A ação existe na plataforma real, ou foi inventada pra servir à avaliação (ex: "marcar como suspeito", "taggear fonte")? Mecânica pedagógica inventada disfarçada de interação de plataforma → ❌.|

### Falso-positivos frequentes em 2.1:

- **Plataforma real fora da lista:** LinkedIn, Canva, Google Notícias, apps de órgão público → ❌ mesmo passando nos demais testes.
- **Roblox:** fora da lista fechada desde a revisão de setembro de 2026 (`ambientes.md`, "Roblox saiu"); missão em Roblox reprova aqui, no 2.1, não duas etapas depois em DES-01.
- **Escape nas etapas finais:** missão respeita o ambiente nas etapas iniciais e cria "Painel da Unooria" na virada → ❌ (teste de permanência).
- **Personagem em vez de conta do aluno:** aluno navega o perfil de um personagem da narrativa → ❌ (teste de posse).
- **Mecânica divergente:** feed mostra vários posts lado a lado que a rede real não faz → ❌ (teste de fidelidade).

---

## 4. LOGÍSTICA DE AULA E MODULARIDADE (subset — 4.5, 4.6, 4.7 apenas)

|#|Critério|Tipo|Teste prático|
|-|-|-|-|
|4.5|**Modularidade por etapas e tempos sugeridos de execução** — Tabela com: preparação do professor (pré-atividade), ambientação, exploração/laboratório, revelação/explicação, mediação/debate, reflexão. Preparação é fora do tempo em tela dos estudantes. Tempos sugeridos de execução declarados por etapa. Sobreposições declaradas. Compatibilidade com aula escolar padrão (50 min).|Obrigatório|O professor consegue olhar a tabela e saber o tempo estimado de cada etapa? Os blocos pedagógicos trazem tempos sugeridos de execução realistas? Sobreposições (ex: mediação durante exploração) estão declaradas? O one-pager orienta como as etapas se distribuem na aula padrão de 50 min?|
|4.6|**Controle do professor, checkpoints modulares e flexibilidade de condução** — A missão é estruturada em etapas com checkpoints explícitos de parada e retomada (estado 100% salvo no servidor). O professor tem autonomia e controle sobre o ritmo (pausar/travar telas para mediação, avançar etapas). Cenários sugeridos de condução detalhados: (a) aula única de 50 min; (b) duas aulas de 50 min (com ponto de corte narrativo natural); (c) sessões fracionadas (20–40 min).|Obrigatório|**Teste de checkpoint:** as etapas têm pontos de pausa naturais com tela de fechamento/espera provisória coerente? **Teste de controle docente:** o professor tem controle sobre quando a turma avança ou pausa? **Teste de persistência:** o que a plataforma preserva ao pausar? O estado é 100% do servidor: seção 8 ou 16 que atribui progresso, curtidas ou cache a `localStorage`/`IndexedDB`/`sessionStorage` → ❌ (o one-pager diz o que se preserva, não onde no aparelho). **Teste de cenários:** o documento apresenta como o professor pode conduzir a missão em aula única (50 min), em 2 aulas (50 min cada) ou em blocos menores (20–40 min), adaptando-se à dinâmica da turma?|
|4.7|**Podcast de recapitulação** — Roteiro completo 3-5 min (máx 6 min), estilo NotebookLM (2 apresentadores), 5 blocos: abertura (~30s), recapitulação da dinâmica (~1-1.5 min), aha moment/revelação (~1-1.5 min), provocação de ponte (~30s-1 min), encerramento (~15s)|Obrigatório|**Teste de completude:** 5 blocos com falas escritas (não descrição)? **Teste de formato:** diálogo entre 2 apresentadores com falas alternadas? **Teste de conteúdo:** revelação explica o mecanismo oculto de forma acessível à faixa? Provocação aquece pro debate sem entregar conclusão? **Teste de tom:** usa "estudante" (nunca "aluno")? Sem lição de moral? Referencia ambiente pelo nome? ≥ 1 momento de surpresa genuína? **Teste de duração:** cabe em 3-5 min lido em voz alta? > 6 min → ❌. **Teste de flexibilidade:** utilizável como abertura de nova aula, transição entre blocos ou áudio de ponte? Funciona só com áudio?|

### Falso-positivos frequentes em 4.5-4.7:

- **Intenção sem conteúdo:** "podcast de recapitulação" listado como recurso sem roteiro escrito → ⚠️. Seção inteira ausente → ❌.
- **Cronograma rígido ou sem sobreposição:** tratar tempos sugeridos como tempo total de aula escolar rígido, ou contar mediação concorrente como sequencial estourando o tempo planejado.
- **Checkpoint abrupto ou sem controle docente:** etapa congela ou encerra sem tela provisória narrativamente coerente, ou sem permitir que o professor comande a retomada.

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
|9.1|**Spec implementável sem decisão de produto aberta** — Requisitos técnicos, regras de transição e ownership estão fechados o suficiente para designer/dev construírem sem inventar comportamento que altere a experiência.|Obrigatório|**Teste de implementação cega:** percorra cada ato e verifique obrigatoriamente: (a) cardinalidades, mínimos/máximos e bloqueios; (b) regra de geração/seleção de outputs (incluindo contrato de parametrização docente por IA, schemas de dados dos conteúdos dinâmicos e fallback para banco padrão curado); (c) estados incompletos e caminhos degenerados; (d) o que faz quem termina antes de um handoff coletivo; (e) qual conta/ator publica, envia ou altera cada elemento visível; (f) permissões antes/durante/depois de handoffs; (g) fallback quando pré-condições não são atendidas; (h) **contrato de plataforma:** sala sincronizada por polling HTTP em `expNNefNb_gates_turma` (nunca WebSocket, socket.io ou "tempo real" como canal), estado no servidor, seção 16 sem protocolo, formato de imagem ou CDN escolhidos pelo redator; (i) **origem dos parâmetros:** todo número que vira regra de sistema nas seções 7, 8, 9, 10, 15 e 16 (segundos, caracteres, KB, percentuais, intervalos) vem do núcleo ou do briefing, ou traz `[PARÂMETRO — a definir por produto: …]` / `[PROPOSTA P0b — …]`; número apresentado como fato sem origem é decisão de produto tomada pelo redator → ❌. Se designer/dev precisarem escolher uma regra que mude a experiência, → ❌. Uma lista de features sem essas regras não cumpre.|
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
