# One-pager — O Dossiê Invisível v2.0

## O que mudou nesta versão
1. **Adequação integral do Canal A de evidências:** Substituição de qualquer campo dissertativo obrigatório de texto livre para fins de scoring pedagógico por ação discreta em tela (seleção/cruzamento) combinada a questão estruturada de múltipla escolha com 3 alternativas mapeadas 1:1 para a régua ternária (*Atingiu*, *Em processo*, *Não atingiu*) renderizadas via componente nativo `ChatPollEmbed` (na Etapa 3 para `EF09CO08` e na Etapa 6 para `EF09CO07`). Textos livres reflexivos tornam-se estritamente opcionais para leitura qualitativa docente, sem impacto na telemetria avaliativa.
2. **Preservação e derivação fiel das seções de apoio (2 e 5–18):** Formalização do contrato de evidências 12a, especificação dos caminhos degenerados com respeito à bifurcação investigativa (Caminho A / Caminho B), roteiro de podcast e parametrização docente em conformidade com o núcleo narrativo aprovado.

---

## 0. Identificação
* **Slug:** `exp09ef1b`
* **Nome que o estudante vê:** O Dossiê Invisível
* **Ano/série:** `["9EF"]`
* **Bimestre:** 1º Bimestre
* **Unidade da trilha:** Unidade 1 — Síntese crítica: o que aprendi sobre mídias, dados e poder?
* **Ambiente simulado:** `chatgpt`
* **Seção do DS:** `chatgpt`
* **Modalidade:** Individual com debate coletivo mediado pelo professor
* **Tempo sugerido de execução:** 50 minutos (aula única de 50 min ou 2 tempos fracionados de 25 min)
* **Arranjo pedagógico sugerido:** Laboratório de informática ou sala com chromebooks/computadores individuais (1:1); mediação socrática do professor no ápice da Etapa 4 e no fechamento da Etapa 6.
* **Público:** estudante

---

## 1. Descoberta central
"Eu achei que estava avaliando qual projeto fazia o melhor trabalho, mas na verdade estava julgando apenas pela quantidade de documentos digitais que a inteligência artificial tinha para ler."

* **Eixo temático:** Sistemas de Informação, Algoritmos e Relações de Poder no Mundo do Trabalho / Cultura Digital.
* **Eixo de Pensamento Computacional:** Abstração e Reconhecimento de Padrões.
* **Tipo de decisão:** Auditar dados ausentes na IA e homologar destinação orçamentária vinculante de projeto social.
* **Porta de abstração:** `criticar com apoio` (o estudante confronta o parecer técnico do algoritmo a partir de novas evidências materiais, detecta a ausência de dados de campo e assume a responsabilidade ética vinculante pela decisão).
* **Foco primário BNCC (Regra 12):** `EF09CO07` — *Avaliar aplicações e implicações políticas, socioambientais e culturais das tecnologias digitais para propor alternativas aos desafios do mundo contemporâneo, incluindo aqueles relativos ao mundo do trabalho.*
  * **Como esta missão o exercita de forma distinta:** O estudante atua ativamente como conselheiro comunitário auditando um sistema de IA de triagem orçamentária. Em vez de consumir a resposta passivamente ou apenas discutir conceitos abstratos em texto, ele experimenta diretamente como a assimetria na digitalização de documentos induz a IA a reproduzir exclusões sistêmicas contra projetos comunitários reais. Ele intervém no sistema fornecendo dados de cadernos físicos e formula uma alternativa crítica e vinculante que subverte a recomendação automatizada enviesada.

### 1.1 Conceitos do material vividos em tela

| Conceito | Etapa | O que o estudante faz em tela | Como o professor aprofunda |
|---|---|---|---|
| C1 — A IA não é neutra: ela decide com base nos dados e critérios que recebeu, reproduzindo suas desigualdades. (limiar) | Decidir · Resultado/Aha | Compara a recomendação do assistente antes e depois de fornecer dados que estavam ausentes da base digital (cadernos de campo) e verifica a inversão da ordem sugerida mantendo idênticos os critérios. | Questiona a turma: "A qualidade do projeto social mudou em cinco minutos ou mudou apenas o que a IA conseguia enxergar sobre ele?" |
| C2 — Ter mais documentos digitais não significa ter mais impacto social ou merecimento; dados ausentes distorcem o julgamento algorítmico. (núcleo) | Navegar · Decidir | Identifica que o projeto Mesa Aberta parecia documentalmente inconsistente para a IA unicamente porque seus registros de frequência e refeições estavam anotados à mão em cadernos físicos de campo. | Provoca: "Por que uma organização que gasta todo o seu tempo alimentando pessoas reais pode parecer 'invisível' ou 'desorganizada' para um algoritmo treinado apenas com PDFs digitais?" |
| C3 — A máquina gera recomendações a partir de critérios configurados, mas a responsabilidade ética e política da escolha é sempre humana. (núcleo) | Decidir · Resultado/Aha | Assume a decisão final e vinculante (com trava irreversível) da destinação dos R$ 12.000, ciente de que o assistente gera pareceres técnicos, mas não assina o termo de responsabilidade institucional. | Intervém no debate: "Se uma família ficar sem alimentação ou acolhimento por causa dessa escolha, quem responde perante a comunidade: vocês ou o ChatGPT?" |
| C4 — Argumentar criticamente exige articular tese, evidências verificadas e síntese, questionando correlações superficiais antes de emitir parecer. (apoio) | Refletir | Cruza a matriz de faltas de Lia e Davi com a planilha oficial de cancelamentos da Linha 302 para evidenciar a falha algorítmica e demonstrar a necessidade de apuração de causas. | Conduz o fechamento: "Como o caso do cancelamento de ônibus se conecta diretamente com os cadernos de campo de João?" |

### 1.2 Anatomia do aha

| Passo | Nesta missão |
|---|---|
| Crença de entrada | B1 — "A IA é neutra e justa porque calcula dados objetivos sem sentimentos nem preconceitos" e B2 — "O projeto com mais relatórios em PDF com certeza funciona melhor do que aquele que anota no papel." |
| Aposta comprometida | O estudante formula critérios de análise no chat, avalia a recomendação automatizada da IA e trava seu voto vinculante formal no sistema destinando os R$ 12.000 para 1 dos 3 projetos antes da revelação dos dados ausentes (ou confirmando sua aposta prévia caso tenha investigado ativamente no Caminho A). |
| Consequência sentida | O chat emite um relatório formal ranqueando os projetos a partir do volume e padronização dos arquivos digitais; o projeto Mesa Aberta (com cadernos manuais) recebe parecer de "alto risco orçamentário por déficit de comprovação documental". |
| Virada | Ao incorporar os dados verificáveis dos cadernos físicos de campo mantendo rigorosamente as mesmas instruções e pesos, a recomendação da IA se inverte radicalmente. O estudante constata que o robô não mediu a eficácia comunitária, mas apenas a presença de rastros digitalizados. Descarte previsto desmontado ("o projeto inventou os números"): os cadernos contêm assinaturas físicas e datas cruzáveis. |
| Nomeação | O Explicar nomeia formalmente os conceitos de viés algorítmico, dados do passado, identificação de padrões e decisões automatizadas, retomando nominalmente a escolha homologada pelo estudante ("Você homologou o repasse para o projeto X...") e comparando com a distribuição percentual dos votos da turma no painel, conectando à pergunta central de Amara sobre ensinar máquinas usando apenas histórias desiguais. |
| Transferência | O Refletir apresenta o caso de transporte escolar de Lia e Davi (ambos com 4 faltas). O estudante cruza as tabelas de faltas e cancelamentos da Linha 302, comprova a correlação de Lia e argumenta por que o corte de benefício de Davi exige investigar dados ausentes. |

---

## 2. Currículo

* **BNCC Computação — Eixo Cultura Digital (Foco Primário):**
  * `EF09CO07` — *Avaliar aplicações e implicações políticas, socioambientais e culturais das tecnologias digitais para propor alternativas aos desafios do mundo contemporâneo, incluindo aqueles relativos ao mundo do trabalho.*
* **BNCC Computação — Eixo Cultura Digital (Habilidade Secundária):**
  * `EF09CO08` — *Discutir como a distribuição desigual de recursos de computação em uma economia global levanta questões de equidade, acesso e poder.*
  * *Momento em tela que exercita `EF09CO08`:* Na Etapa 3 (Decidir), o estudante confronta o card deliberativo em que um projeto comunitário de base carece de infraestrutura de digitalização e, via enquete estruturada, reconhece formalmente como a assimetria material de tecnologia restringe a legitimidade institucional e a distribuição de poder orçamentário.
* **Conexões com Disciplinas Tradicionais (plausíveis, a confirmar em fonte oficial da BNCC):**
  * *Língua Portuguesa (EF89LP23):* Analisar a estrutura argumentativa e os operadores lógicos em pareceres técnicos, contrapondo dados e teses em tomada de decisão comunitária (plausível, a confirmar em fonte oficial da BNCC).
  * *Matemática (EF09MA22):* Analisar e cruzar tabelas de dupla entrada e matrizes de ocorrências para identificar correlação e causalidade estatística no caso de frequência escolar (plausível, a confirmar em fonte oficial da BNCC).
* **Competência Geral da Educação Básica (BNCC):**
  * *Competência Geral 5 (Cultura Digital):* Compreender, utilizar e criar tecnologias digitais de informação e comunicação de forma crítica, significativa, reflexiva e ética nas diversas práticas sociais.
* **Competência Socioemocional Nomeada:** Tomada de decisão responsável (avaliação ética das consequências de decisões automatizadas sobre pessoas e grupos vulnerabilizados).
* **Descritor SAEB (9º ano do Ensino Fundamental — Língua Portuguesa):**
  * *D14:* Distinguir um fato da opinião relativa a esse fato (aplicado à identificação de dados materiais verificados versus pareceres enviesados do assistente).
* **Rastreabilidade Bimestral:** 9º ano EF, 1º Bimestre — Unidade 1: *Síntese crítica: o que aprendi sobre mídias, dados e poder?*

---

## 3. Narrativa e personagem-guia

### Abertura (Desafiar) com job-to-be-done concreto
O estudante recebe a notificação institucional no ChatGPT: ele foi nomeado Conselheiro Relator da Comissão de Recursos Comunitários. Sua tarefa de trabalho concreta (*job-to-be-done*) é: **analisar 3 projetos sociais locais em disputa, consultar o assistente de IA para examinar seus históricos e assinar a homologação vinculante de destinação de uma verba única e indivisível de R$ 12.000 para apenas 1 deles, ciente de que os outros dois permanecerão na fila sem conseguir abrir novas vagas.**

Os três projetos:
1. **Mesa Aberta:** Coordenado por João. Oferece 24 novas vagas de refeição e permanência escolar no contraturno escolar em 2 dias por semana. João (14 anos) nem sempre tem refeição garantida fora da escola. Sem o recurso, as vagas não abrem. Seus registros estão em cadernos físicos de campo assinados.
2. **Ponto de Apoio:** Coordenado por Ana. Oferece 18 novas vagas de acolhimento psicológico e convivência em grupo com educadores para enfrentar situações de bullying. Ana (14 anos) se afastou das aulas após humilhações recorrentes. Possui relatórios intermediários.
3. **Conexão para Continuar:** Coordenado por Luana. Oferece 20 novas vagas de acesso a computadores, laboratório conectado e orientação pedagógica. Luana (14 anos) depende de aparelhos emprestados para estudar. Possui relatórios mensais padronizados em PDF, gráficos e métricas estruturadas na nuvem.

### Decisão deliberada sobre o personagem-guia
* **Personagem:** Amara (9º ano).
* **Padrão de presença:** Apenas no Desafiar e no Explicar.
* **Justificativa pedagógica:** O 9º ano exige postura crítica autônoma e protagonismo decisório (`criticar com apoio`). Amara surge na abertura lançando a inquietação do livro ("Se os dados contam uma história desigual, o que acontece quando ensinamos uma máquina usando apenas essa história?") e reaparece na Etapa 5 (Explicar) para ajudar a sistematizar a tese do ensaio do bimestre. Durante o Navegar, Decidir e Resultado/Aha, Amara não intervém: a tensão ética e institucional pertence estritamente ao estudante e ao assistente de IA.

### Superfície de parametrização docente (Regra 11)
* **O que o professor de qualquer disciplina customiza:** O recorte temático da aula (a natureza dos 3 projetos sociais e o foco comunitário do território).
* **O que a IA da plataforma gera:** O texto descritivo dos 3 projetos, as respostas do chat simulado sobre as atividades de cada grupo, os trechos dos relatórios e o conteúdo dos cadernos de campo.
* **Camada estrutural fixa:** O mecanismo das 6 etapas, o valor de R$ 12.000 indivisível, o formato da árvore de arquivos (1 projeto com acervo digital completo, 1 mediano e 1 com cadernos físicos), a bifurcação investigativa (Caminho A / Caminho B), o latch de voto vinculante irreversível e o caso de transferência Lia/Davi.

#### Teste das três disciplinas

| Disciplina | Recorte do professor (exemplo) | O que a IA gera | O que não muda |
|---|---|---|---|
| **Língua Portuguesa** | *Acesso à literatura e combate à desinformação periférica.* | Projeto A: Saraus e biblioteca comunitária em cadernos de empréstimo; Projeto B: Oficina de combate a fake news com cartilhas mistas; Projeto C: Podcast e blog digital com relatórios analíticos de engajamento online. | Verba de R$ 12.000 para 1 projeto; IA ranqueia C pelo volume digital de métricas; cadernos de A revelam alcance físico omitido; voto vinculante. |
| **Ciências / Biologia** | *Saneamento ambiental, horta agroecológica e saúde comunitária.* | Projeto A: Horta comunitária contra insegurança alimentar com cadernos manuais de colheita; Projeto B: Coleta seletiva de resíduos; Projeto C: Monitoramento por sensores de qualidade do ar com dashboards e relatórios digitais em nuvem. | Verba de R$ 12.000 indivisível; IA recomenda C por relatórios automatizados; cadernos físicos de A mostram 100 famílias alimentadas; voto vinculante. |
| **História / Geografia** | *Preservação de memória quilombola/indígena e vulnerabilidade urbana.* | Projeto A: Preservação de história oral com cadernos manuscritos de anciãos; Projeto B: Cartografia social de riscos de encosta; Projeto C: Digitalização de acervo histórico com catálogo digital em PDF e planilhas online. | Verba de R$ 12.000 indivisível; IA privilegia C por estrutura de dados catalogada; registros orais em caderno mudam o parecer; caso Lia/Davi. |

---

## 4. As 6 etapas — mecanismo, não intenção

### Etapa 1 — Desafiar
* **O que o estudante vê:** Interface do ChatGPT carregando o workspace "Conselho Municipal de Apoio Social". Na tela de boas-vindas do chat, uma mensagem formal da presidência do conselho e um balão reflexivo de Amara: *"Você tem R$ 12.000 para repassar a um único projeto. A máquina pode ler tudo rápido, mas lembre-se: se os dados contam uma história desigual, o que a máquina vai concluir?"*. Abaixo, 3 cartões de contexto resumem a demanda: Mesa Aberta (24 vagas de almoço/permanência, João), Ponto de Apoio (18 vagas contra bullying, Ana) e Conexão para Continuar (20 vagas de inclusão digital, Luana).
* **Verbo nativo:** Ler notificação e digitar/enviar primeira mensagem no chat.
* **O que muda na tela:** O estudante clica em "Iniciar Auditoria no Assistente" e o campo de input de texto do ChatGPT é focado.
* **Quem conduz:** Unooria (contextualização inicial) → Estudante.
* **Regra do sistema:** Apresenta três pílulas de prompt efêmeras e opcionais sugeridas sobre a barra de digitação:
  * `[Pílula 1: "Qual projeto atende mais pessoas pelo menor custo por vaga?"]`
  * `[Pílula 2: "Compare a regularidade e os relatórios enviados pelos três projetos."]`
  * `[Pílula 3: "Quais são as evidências de impacto de cada iniciativa?"]`
  * *Regra de efemeridade:* Se o estudante clica em uma pílula ou digita texto livre autoral, as pílulas desaparecem permanentemente da interface durante toda a missão.

### Etapa 2 — Navegar
* **O que o estudante vê:** Thread interativa no ChatGPT. O assistente responde às perguntas do estudante consultando uma base institucional pré-carregada (`base_dados_conselho.json`).
* **Verbo nativo:** Digitar prompts, consultar dados, solicitar comparações e clicar em abas de anexos.
* **O que muda na tela:** Conforme o estudante dialoga, a IA apresenta respostas estruturadas.
  * O projeto **Conexão para Continuar** aparece com 12 relatórios mensais em PDF, gráficos de presença digital e métricas analíticas detalhadas.
  * O projeto **Ponto de Apoio** tem atas semestrais digitais e relatórios parciais.
  * O projeto **Mesa Aberta** aparece no sistema apenas com a ficha cadastral básica e a anotação: *"Déficit de relatórios na nuvem. Histórico institucional insuficiente para validação algorítmica."*
* **Quem conduz:** Estudante interagindo com IA simulada.
* **Regra do sistema (Bifurcação Investigativa Caminho A / Caminho B):**
  * **Caminho A (Investigação Ativa de Lacunas):** Se o estudante faz perguntas que desconfiam da ausência de dados de João (ex.: *"Por que o Mesa Aberta não tem relatórios?"*, *"Onde estão os registros de alimentação do Mesa Aberta?"*, *"Existem documentos físicos arquivados?"*), a IA aciona o estado `E2_CADERNOS_OFERECIDOS` e responde: *"Constam nos arquivos do conselho 3 cadernos físicos de campo com anotações diárias de frequência e assinaturas dos responsáveis, que não foram digitalizados. Deseja anexar e processar esses cadernos agora?"*. Se o estudante aceita, transiciona para `E2_CADERNOS_DESBLOQUEADOS`, a flag `caminho_tomado = "A"` é gravada e a IA já processa os dados de campo antes do voto.
  * **Caminho B (Fluxo Convencional do Briefing):** Se o estudante não questiona os dados faltantes e foca apenas em comparar métricas pré-existentes, o sistema mantém os cadernos ocultos, define `caminho_tomado = "B"` e a IA emite parecer formal recomendando **Conexão para Continuar** como a opção de "menor risco documental e maior governança técnica".
  * Após 3 mensagens trocadas no chat (ou ao clicar em "Avançar para Homologação"), o sistema libera o botão nativo "Emitir Parecer Vinculante".

### Etapa 3 — Decidir
* **O que o estudante vê:** Card formal de deliberação vinculante integrado ao fluxo do chat: "Homologação de Destinação Orçamentária — R$ 12.000".
* **Verbo nativo:** Clicar para selecionar 1 de 3 projetos comunitários, responder à questão estruturada de posicionamento ético e clicar no botão com trava formal.
* **O que muda na tela:** Ao marcar um projeto, os outros dois ficam destacados com a tag cinza *"Fila de espera (sem abertura de vagas)"*. Em seguida, o chat renderiza o componente `ChatPollEmbed` com a pergunta de justificativa de critérios. Ao responder, o botão *"Homologar Voto Irreversível"* é habilitado com ícone de cadeado. Ao clicar, a interface trava permanentemente (`latch: locked`), impedindo qualquer retorno ou alteração.
* **Quem conduz:** Estudante.
* **Regra do sistema:** O voto vinculante é registrado no estado da sessão (`voto_etapa3`). Exige a seleção discreta do projeto e a resposta obrigatória ao `ChatPollEmbed` (Canal A de evidência da habilidade `EF09CO08`), garantindo scoring automatizado sem dependência de leitura de texto livre pelo professor.

### Etapa 4 — Resultado / Aha
* **O que o estudante vê e vive:**
  * **Se Caminho B:** O chat emite a mensagem de auditoria pós-voto interpolando explicitamente o voto do próprio estudante: *"Auditoria de Integridade Convocada: Você homologou o repasse para o projeto [Nome do Projeto Votado]. Contudo, a equipe de campo localizou e digitalizou em caráter de urgência os Cadernos Físicos de Campo do projeto Mesa Aberta (180 dias de assinaturas, controle calórico e 24 jovens atendidos diariamente)."* O assistente roda automaticamente o reprocessamento com os mesmos critérios de custo e atendimento: a recomendação inverte-se imediatamente para o Mesa Aberta, rebaixando a Conexão para Continuar pelo custo operacional relativo.
  * **Se Caminho A:** O estudante já havia antecipado os cadernos e homologado sua decisão. A IA projeta na tela uma **Simulação Contrafactual** personalizada: *"Você homologou seu voto em [Nome do Projeto Votado] após auditar os cadernos físicos. Se você não tivesse investigado as lacunas na Etapa 2, o sistema teria induzido seu voto para o Conexão para Continuar por causa dos 12 PDFs arquivados."*
  * **Consequência sentida na interface:** O estudante confronta na tela a tabela comparativa:
    * *Critério da IA:* Volume de documentação na nuvem (favoreceu Conexão para Continuar).
    * *Realidade de campo:* Urgência nutricional e atendimento diário efetivo (Mesa Aberta).
* **Mediação do professor (Regra 10):** O professor paralisa a turma e projeta no quadro as métricas da sala enviadas pelo dashboard da plataforma:
  * Gráfico 1: Quantos estudantes votaram em cada projeto na Etapa 3 (Caminho B votou massivamente no Conexão para Continuar pela influência da IA; Caminho A distribuiu os votos).
  * Debate mediado: *"Quem aqui achou que o Mesa Aberta era desorganizado só porque não tinha PDF? O trabalho do João era ruim ou ele estava ocupado demais servindo refeições para preencher planilhas?"*.
  * Os estudantes percebem que o robô não errou na matemática, mas operou sobre uma lacuna estrutural de dados.
* **Quem conduz:** Professor conduzindo a análise com dados da turma + Unooria exibindo a virada contrafactual.
* **Regra do sistema:** A plataforma garante a revelação nativa no chat; proíbe cards externos de celebração genérica; disponibiliza no painel docente a separação entre alunos que fizeram Caminho A vs. Caminho B.

### Etapa 5 — Explicar
* **O que o estudante vê:** Card conceitual no chat assinado por Amara, dialogando diretamente com a tese do ensaio do 1º bimestre e referenciando nominalmente a decisão do estudante (*"Você homologou o repasse para o projeto [Nome do Projeto Votado], enquanto parte significativa da turma foi induzida pelos relatórios da nuvem a votar em outro"*). O texto nomeia e sistematiza formalmente com o vocabulário oficial do material:
  * **viés algorítmico:** distorção sistemática decorrente de assimetrias nos dados de entrada.
  * **dados do passado:** registros históricos que refletem desigualdades de infraestrutura.
  * **identificação de padrões:** a IA calcula correlações nos dados presentes, ignorando o que não foi registrado.
  * **decisões automatizadas:** riscos de delegar julgamentos humanos a métricas frias de sistemas computacionais.
* **Verbo nativo:** Clicar e selecionar na interface as evidências do próprio histórico de chat que comprovam onde ocorreu a distorção algorítmica.
* **O que muda na tela:** O estudante marca no histórico: (1) O momento em que a IA apontou "falta de consistência" no Mesa Aberta; (2) A tabela invertida pós-cadernos.
* **Quem conduz:** Estudante sob mediação de Amara e do professor.
* **Regra do sistema:** Valida que o estudante selecione as âncoras corretas antes de liberar o botão para o Refletir.

### Etapa 6 — Refletir
* **O que o estudante vê:** Cenário novo de transferência direta (`literatura-cognitiva.md` §12) — O caso do Transporte Escolar Municipal:
  * Uma comissão disciplinar automatizada por IA recomendou a suspensão do passe escolar de dois estudantes, **Lia e Davi**, por excesso de faltas injustificadas (ambos acumulam rigorosamente 4 faltas em 20 dias letivos).
  * Na tela, duas tabelas de dados públicos:
    1. *Tabela A (Frequência Escolar):* Datas exatas das faltas de Lia (03/mar, 10/mar, 17/mar, 24/mar) e de Davi (04/mar, 11/mar, 18/mar, 25/mar).
    2. *Tabela B (Relatório Operacional de Ônibus):* Registra cancelamentos da **Linha 302** (que atende o bairro periférico de Lia) exatamente nos dias 03/mar, 10/mar, 17/mar e 24/mar. Para o bairro de Davi, os registros de ocorrência da linha de transporte não constam na planilha do consórcio (dados ausentes/não apurados).
* **Verbo nativo:** Clicar para cruzar interativamente as linhas das tabelas (marcação de correspondência de datas) e responder à questão de posicionamento institucional em múltipla escolha.
* **O que muda na tela:** Ao clicar nas datas coincidentes de Lia, o sistema destaca em verde a justificativa verificada de força maior. Em seguida, o chat abre o componente `ChatPollEmbed` com a pergunta estruturada sobre a deliberação dos dois casos.
* **Quem conduz:** Estudante individualmente.
* **Regra do sistema (Pergunta-ponte docente e avaliação discreta):** O professor lança a pergunta-ponte: *"Onde mais no seu dia a dia você é avaliado apenas pelo que o sistema registrou, sem ninguém saber o que aconteceu no caminho?"*.

---

### Evidência do foco primário (Regra 17)

| Habilidade (código) | Canal de evidência | Canal A: ação · etapa · regra ternária (Atingiu / Em processo / Não atingiu) | Canal B: pergunta · 3 alternativas com o nível de cada uma, sem ordem fixa · componente que renderiza |
|---|---|---|---|
| `EF09CO07` *(Foco primário)* | `A + B` | **Ação:** Cruzamento tabular interativo na Etapa 6 (seleção das 4 datas coincidentes da Linha 302) seguido de resposta no `ChatPollEmbed`.<br>**Régua ternária do Canal A:**<br>• *Atingiu:* Alternativa que demonstra correlação causal exata das datas de Lia com os cancelamentos da Linha 302 E exige investigação prévia de dados ausentes de Davi antes de qualquer sanção.<br>• *Em processo:* Alternativa que isenta Lia com base no cruzamento, mas acata a suspensão imediata de Davi sob a justificativa de "ausência de registro no sistema".<br>• *Não atingiu:* Alternativa genérica que aceita a punição automática de ambos ou rejeita a análise de dados como irrelevante. | **Pergunta:** "Ao analisar a recomendação de uma IA que seleciona pessoas com base em históricos prévios, qual postura ética o avaliador deve adotar?"<br>• *[Atingiu]:* Auditar os dados de treinamento para identificar lacunas históricas e assumir a responsabilidade humana pela decisão final.<br>• *[Em processo]:* Aceitar a sugestão da máquina caso os critérios matemáticos pré-definidos tenham sido rigorosamente seguidos.<br>• *[Não atingiu]:* Descartar o uso de computadores e decidir exclusivamente pela intuição pessoal.<br>*Componente:* `ChatPollEmbed` pós-Refletir. |
| `EF09CO08` *(Secundária)* | `A + B` | **Ação:** Seleção de 1 projeto no card de homologação da Etapa 3 seguida de resposta no `ChatPollEmbed`.<br>**Régua ternária do Canal A:**<br>• *Atingiu:* Alternativa que problematiza a disparidade estrutural de infraestrutura digital entre projetos e demonstra compreensão de como a distribuição desigual de recursos afeta o poder de decisão.<br>• *Em processo:* Alternativa que menciona a vantagem dos arquivos digitais do projeto escolhido, mas sem problematizar a desigualdade de acesso e de recursos que gerou essa diferença.<br>• *Não atingiu:* Alternativa que trata projetos sem documentação digitalizada como inferiores, desorganizados ou desqualificados para receber verba pública. | **Pergunta:** "Por que uma organização social que mantém dados apenas em papel corre maior risco de ser excluída por políticas públicas automatizadas?"<br>• *[Atingiu]:* Porque a escassez de infraestrutura digital impede que seu trabalho real seja capturado por sistemas de triagem algorítmica.<br>• *[Em processo]:* Porque sistemas computacionais são mais rápidos e exigem relatórios legíveis para arquivamento.<br>• *[Não atingiu]:* Porque cadernos em papel têm menor validade legal do que planilhas digitais.<br>*Componente:* `ChatPollEmbed` integrado ao fechamento. |

---

## 5. Verificação de ambiente

| Etapa | Dentro do ambiente? | Escape permitido? | Affordance nativa usada |
|---|---|---|---|
| **1. Desafiar** | Sim (`chatgpt`) | Não | Banner de workspace colaborativo, pílulas de prompt sugerido (`ChatSuggestionsEmbed`), caixa de entrada com botão de envio. |
| **2. Navegar** | Sim (`chatgpt`) | Não | Fluxo contínuo de mensagens intercaladas (usuário/assistente), renderização de tabelas Markdown e citações de arquivos anexos. |
| **3. Decidir** | Sim (`chatgpt`) | Não | Card de decisão incorporado no stream do chat (`ChatDecisionLatchEmbed`) e componente de votação interativo (`ChatPollEmbed`). |
| **4. Resultado/Aha** | Sim (`chatgpt`) | Não | Resposta do assistente simulando reprocessamento com badge de auditoria e tabela comparativa nativa. |
| **5. Explicar** | Sim (`chatgpt`) | Não | Mensagem do sistema assinada por Amara com seleção interativa de trechos anteriores da conversa (*message highlight*). |
| **6. Refletir** | Sim (`chatgpt`) | Não | Visualizador de dados tabulares em split-view dentro da thread de chat e componente `ChatPollEmbed`. |

---

## 6. Verbos e affordances

### Verbos nativos usados
* **Digitar prompt:** O estudante clica no input de texto do ChatGPT → digita sua pergunta investigativa → envia para o assistente simulado;
* **Clicar em pílula de sugestão:** O estudante visualiza as pílulas efêmeras sobre a barra de digitação → clica em uma das pílulas → o texto é copiado para o input e disparado, sumindo com as pílulas;
* **Clicar em anexo/arquivo:** O estudante visualiza menções a relatórios e cadernos na thread → clica para inspecionar os metadados do documento;
* **Selecionar opção em enquete (`ChatPollEmbed`):** O estudante lê a pergunta e as 3 opções no corpo do chat → clica na alternativa desejada → a opção é registrada com feedback visual nativo;
* **Travar deliberação (`ChatDecisionLatchEmbed`):** O estudante marca o projeto escolhido → revisa o impacto nos outros dois → clica em "Homologar Voto Irreversível" → a interface congela em estado de cadeado travado;
* **Cruzar linhas de tabelas:** O estudante clica em uma data na Tabela A de faltas → clica na data correspondente na Tabela B de cancelamentos → a linha se ilumina com status de correspondência causal confirmada.

### Ausências deliberadas do ambiente simulado
* **Sem botão de edição de mensagens passadas:** O estudante não pode reescrever prompts já enviados para garantir a rastreabilidade investigativa e a integridade da bifurcação A/B.
* **Sem botão "Regenerate response":** O assistente mantém consistência determinística com a base de conhecimento institucional configurada pelo professor.
* **Sem criação de novas conversas paralelas (botão New Chat desabilitado):** O estudante permanece focado na thread oficial da comissão orçamentária sem dispersão.

---

## 7. Caminhos degenerados

| Caminho degenerado | O que acontece no sistema | Experiência pedagógica resultante |
|---|---|---|
| **Não escolheu nada (Inação na Etapa 3)** | O botão "Homologar Voto Irreversível" permanece desabilitado com o ícone de cadeado cinza até que o estudante selecione 1 projeto e responda obrigatoriamente à enquete no `ChatPollEmbed`. | O estudante é forçado a assumir a responsabilidade institucional pelo repasse antes de avançar para a revelação. |
| **Escolheu tudo / Tentativa de dividir a verba** | A interface não permite múltipla seleção. A verba de R$ 12.000 é indivisível no sistema: ao marcar um projeto, os outros dois são marcados automaticamente como *"Fila de espera"*. | O estudante experimenta a escassez material e a dor ética da escolha orçamentária no mundo real. |
| **Não usou a ferramenta (Ignorou perguntas e só clicou pílulas ou avançou rápido)** | O sistema cai compulsoriamente no **Caminho B**. A IA recomenda o projeto Conexão para Continuar pelo excesso de PDFs. | O estudante sofre o aha na Etapa 4 ao descobrir que confiou cegamente em uma recomendação enviesada por ausência de dados. |
| **Exploração mínima (Fez 1 pergunta monossilábica e avançou)** | A IA responde com parecer preliminar padrão destacando a ausência de dados do Mesa Aberta. O botão de avançar só é liberado após o limite mínimo de interação da Etapa 2. | O estudante vivencia as consequências de uma triagem rasa ao ver seu voto confrontado na Etapa 4. |
| **Terminou antes do tempo da turma** | O sistema trava na tela de encerramento do Refletir com o status "Aguardando deliberação da plenária". Uma aba lateral diegética libera a leitura do "Dossiê Histórico da Cidade" (material complementar sem avanço de etapa). | O estudante aprofunda o contexto histórico do território sem vazar o desfecho para os colegas que continuam decidindo. |

---

## 8. Estados de falha

* **Conexão cai durante a missão:**
  * *O que o estudante vê:* Banner discreto na interface do ChatGPT: *"Conexão com o servidor da comissão interrompida. Reconectando aos registros..."*.
  * *O que o estudante faz:* O estudante aguarda a reconexão automática ou clica em "Tentar novamente".
  * *O que se preserva:* O estado da sessão (mensagens trocadas no chat, projeto homologado na trava irreversível e dados já cruzados) é persistido no servidor a cada interação; nenhuma ação validada é perdida.
* **Sessão expira por inatividade:**
  * *O que o estudante vê:* Modal diegético institucional: *"Sua sessão como conselheiro relator expirou por segurança. Clique abaixo para reautenticar seu crachá digital."*.
  * *O que o estudante faz:* Clica em "Reautenticar" e a tela recarrega exatamente no último checkpoint concluído no servidor.
* **Mídia ou arquivo não carrega:**
  * *O que o estudante vê:* Card de substituição com a mensagem: *"Visualização gráfica indisponível. Carregando extrato textual transcrito dos arquivos."*.
  * *O que o estudante faz:* O estudante consegue ler todos os dados em formato de texto limpo, sem que a falta de renderização gráfica bloqueie a deliberação.
* **Professor não libera a próxima etapa (trava do gate):**
  * *O que o estudante vê:* O chat exibe no rodapé o status formal: *"Parecer registrado. Aguardando autorização da presidência da mesa para abrir o próximo ponto de pauta."*.
  * *O que o estudante faz:* Aguarda a mediação do professor e o desbloqueio coletivo via dashboard.

---

## 9. Papel do professor e parametrização com IA

### 9a. Preparo — o fluxo do professor em cinco passos
1. **Escolher a missão no catálogo:** O professor seleciona `exp09ef1b` ("O Dossiê Invisível") no catálogo do 9º ano EF, Unidade 1.
2. **Recorte da aula:**
   * O professor define o componente curricular (Língua Portuguesa, Ciências, História, Geografia ou Projeto/Interdisciplinar).
   * Insere o tema da aula (ex.: *"Políticas públicas e combate à desigualdade urbana"*).
   * Seleciona/edita os 3 a 6 assuntos da aula (ex.: orçamentos comunitários, vulnerabilidade social, triagem algorítmica).
   * *Caminho curto obrigatório:* Para rodar a aula sem edição, o professor simplesmente clica no botão visível **"Usar banco padrão"**, mantendo os 3 projetos canônicos (Mesa Aberta, Ponto de Apoio e Conexão para Continuar).
3. **Geração do pacote pela IA (assíncrona):**
   * Caso customize o tema, a IA da plataforma (Vertex Gemini) gera o pacote de textos (descrição dos 3 projetos, respostas da IA no chat e detalhes dos cadernos).
   * Enquanto gera, o professor visualiza uma barra de progresso com status das entidades geradas.
   * Se a escola estiver sem saldo de IA, a plataforma bloqueia a geração personalizada e ativa compulsoriamente o banco curado padrão com feedback explicativo.
4. **Curadoria docente:** O professor pré-visualiza os cards dos projetos, edita trechos textuais se desejar, clica em "Regenerar item" em campos pontuais e clica em **"Aprovar Pacote"**.
5. **Ativar ou agendar:** O professor clica em **"Liberar para a Turma"** ou agenda a data/horário da aula.

*Contagem de preparo `[CONVENÇÃO]`:*
* *Caminho curto (banco padrão):* 2 telas, 2 toques (Selecionar Missão → Usar banco padrão e ativar).
* *Caminho customizado com IA:* 4 telas, 7 toques (Selecionar Missão → Definir Recorte → Gerar com IA → Aprovar Curadoria → Liberar para a Turma).

#### Mediação em sala de aula
* **Antes da aula:** O professor projeta a tela inicial de acolhimento e orienta a turma a entrar com seus crachás de conselheiros.
* **Durante a aula:**
  * Observa no dashboard a bifurcação de caminhos (quantos estudantes estão explorando no Caminho A e quantos no Caminho B).
  * No ápice da Etapa 4, o professor aciona o congelamento de telas via dashboard e projeta o gráfico de votos da sala.
  * Conduz o debate socrático sem entregar a virada com antecedência.
* **Depois da aula:** O professor acessa a leitura de evidências consolidada das habilidades `EF09CO07` e `EF09CO08` para subsidiar a avaliação formativa.

#### Roteiro de perguntas do debate mediado (≥ 3 perguntas)
1. *"A qualidade real do trabalho do projeto Mesa Aberta aumentou quando descobrimos os cadernos de campo, ou o trabalho já existia e era a máquina que não conseguia enxergar?"*
2. *"Por que um projeto comunitário que lida diretamente com urgência de alimentação tem muito mais dificuldade de gerar planilhas e relatórios em PDF do que uma oficina de informática?"*
3. *"Se a prefeitura cortar uma verba ou suspender o passe de um estudante com base exclusiva na nota que a IA calculou, a culpa da injustiça é do algoritmo ou de quem aceitou a recomendação sem auditar os dados?"*

### 9b. A mesma missão em três aulas

| Disciplina | Recorte do professor | O que a IA gera (posts, mensagens, perfis…) | O que não muda |
|---|---|---|---|
| **Língua Portuguesa** | *Acesso à literatura e combate à desinformação periférica.* | Projeto A: Saraus e biblioteca comunitária em cadernos de empréstimo; Projeto B: Oficina de combate a fake news com cartilhas mistas; Projeto C: Podcast e blog digital com relatórios analíticos de engajamento online. | Verba de R$ 12.000 para 1 projeto; IA ranqueia C pelo volume digital de métricas; cadernos de A revelam alcance físico omitido; voto vinculante. |
| **Ciências / Biologia** | *Saneamento ambiental, horta agroecológica e saúde comunitária.* | Projeto A: Horta comunitária contra insegurança alimentar com cadernos manuais de colheita; Projeto B: Coleta seletiva de resíduos; Projeto C: Monitoramento por sensores de qualidade do ar com dashboards e relatórios digitais em nuvem. | Verba de R$ 12.000 indivisível; IA recomenda C por relatórios automatizados; cadernos físicos de A mostram 100 famílias alimentadas; voto vinculante. |
| **História / Geografia** | *Preservação de memória quilombola/indígena e vulnerabilidade urbana.* | Projeto A: Preservação de história oral com cadernos manuscritos de anciãos; Projeto B: Cartografia social de riscos de encosta; Projeto C: Digitalização de acervo histórico com catálogo digital em PDF e planilhas online. | Verba de R$ 12.000 indivisível; IA privilegia C por estrutura de dados catalogada; registros orais em caderno mudam o parecer; caso Lia/Davi. |

---

## 10. Modularidade, tempos sugeridos e controle do professor

| Etapa | Em tela (estudante) | Fora da tela (mediação/debate) |
|---|---|---|
| **1. Desafiar** | 4 min | 2 min (Contextualização inicial do professor) |
| **2. Navegar** | 8 min | 0 min |
| **3. Decidir** | 4 min | 0 min |
| **4. Resultado/Aha** | 3 min | 12 min (Debate coletivo e análise do gráfico da turma) |
| **5. Explicar** | 5 min | 2 min (Sistematização com Amara e fechamento da tese) |
| **6. Refletir + Canal B** | 7 min | 3 min (Pergunta-ponte docente e encerramento) |
| **Total** | **31 min** | **19 min** |

*Tempo de aula: 50 min · Em tela: 31 min*

### Checkpoints e controle docente
* **Checkpoint 1 (Fim da Etapa 3):** Trava automática de homologação. O estudante não avança para o Resultado/Aha até que o professor libere a projeção no dashboard.
* **Checkpoint 2 (Fim da Etapa 4):** Liberação do Explicar após a conclusão do debate mediado.
* **Cenários de aplicação:**
  * *Aula única de 50 minutos:* Segue o fluxo integrado da tabela acima.
  * *Dois tempos fracionados de 25 minutos:* Tempo 1 finaliza no Checkpoint 1 (Etapas 1 a 3, registrando o voto); Tempo 2 inicia no debate da Etapa 4 e conclui as Etapas 5 e 6.

---

## 11. Podcast de recapitulação

* **Duração aproximada:** 3 minutos e 30 segundos.
* **Apresentadores:** Lucas e Bianca.
* **Nota de proteção de gap:** O podcast deve ser reproduzido *apenas após* a conclusão da Etapa 6, pois discute abertamente a virada algorítmica e a revelação dos cadernos físicos.

---

**[Bloco 1 — Abertura: ~30s]**
* **Lucas:** Fala, pessoal! Bem-vindos ao Recapitulação Unooria. Hoje a gente acompanhou a turma do 9º ano encarando uma responsabilidade pesada: gerenciar uma verba de doze mil reais para projetos sociais locais usando um assistente de inteligência artificial.
* **Bianca:** É isso, Lucas! Na tela, parecia uma tarefa simples: perguntar para a IA, olhar quem tinha mais dados e assinar o repasse. Mas o que parecia uma decisão técnica virou um baita dilema ético!

**[Bloco 2 — Recapitulação: ~1 min]**
* **Lucas:** Exatamente. De um lado, a gente tinha o projeto Conexão para Continuar, da Luana, cheio de relatórios mensais em PDF, gráficos lindos e métricas em nuvem. Do outro lado, o Mesa Aberta, do João, que oferece refeição diária para dezenas de estudantes no contraturno, mas não tinha quase nada no sistema.
* **Bianca:** E aí a IA fez o que foi programada para fazer com os dados que tinha: carimbou o Mesa Aberta como de alto risco e recomendou repassar todo o recurso para a oficina de informática. E muita gente na sala seguiu a recomendação da máquina e homologou o voto!

**[Bloco 3 — Revelação: ~1 min]**
* **Lucas:** Mas aí veio a grande virada da nossa investigação. Quando a equipe foi a campo, descobriu que o João tinha tudo registrado, sim! Só que em cadernos de papel, com assinaturas diárias, controle calórico e presenças reais de famílias atendidas.
* **Bianca:** E quando esses cadernos foram digitalizados e alimentados na IA, mantendo as mesmas regras de custo e atendimento... adivinha? A recomendação inverteu na hora! O Mesa Aberta passou para o primeiro lugar. A inteligência artificial não estava avaliando o impacto humano; ela estava medindo apenas quem tinha equipamento para gerar PDF!

**[Bloco 4 — Provocação: ~45s]**
* **Lucas:** E isso ficou claríssimo no caso do transporte de Lia e Davi. A máquina queria suspender o passe dos dois por quatro faltas. Mas quem cruzou as tabelas viu que as quatro faltas de Lia batiam com os dias em que a linha de ônibus quebrou! E no caso de Davi, os registros nem existiam.
* **Bianca:** Pois é! Não dá para punir ou premiar ninguém confiando cegamente no que a máquina mostra sem antes perguntar: quem teve condições de colocar dados no sistema?

**[Bloco 5 — Encerramento: ~15s]**
* **Lucas:** A IA calcula padrões nos dados do passado, mas a responsabilidade pela justiça da decisão é 100% humana.
* **Bianca:** Até a próxima missão, conselheiros!

---

## 12. Evidências e dados

* **O que é capturado:**
  * Eventos discretos de navegação (cliques nas pílulas, tempo por etapa, nós da árvore de dados consultados);
  * Caminho investigativo percorrido na Etapa 2 (`caminho_tomado`: "A" ou "B");
  * Voto formal e projeto homologado na Etapa 3;
  * Seleção de alternativas nos componentes `ChatPollEmbed` (Canal A e Canal B de cada habilidade);
  * Cruzamento de pares ordenados (datas de faltas x cancelamentos de linha) na Etapa 6.
* **O que NÃO é coletado:** Nome civil completo, áudio de microfone, captura de câmera, biometria facial, histórico de navegação externo ou texto livre de menores com identificação pessoal.
* **Finalidade e retenção:** Avaliação pedagógica formativa do professor no semestre letivo corrente; dados anonimizados agregados para auditoria da rede pública municipal/estadual.
* **Texto livre:** Campos de texto eventualmente digitados pelo estudante no chat funcionam apenas como prompt local e reflexão qualitativa facultativa, sendo excluídos de qualquer algoritmo de scoring automatizado da plataforma.
* **Gabarito e segurança de servidor:** A rota de telemetria envia apenas identificadores opacos de alternativas (`option_id`); a associação entre alternativa e nível ternário reside exclusivamente na lógica de backend da API.

---

### 12a. Contrato de evidência por habilidade

| Habilidade | Canal | Evento registrado | Identificador / Campo avaliado | Regra ternária de cálculo no servidor |
|---|---|---|---|---|
| `EF09CO07` *(Primária)* | **Canal A** | `submit_refletir_decision` | `poll_option_id` (após cruzamento tabular de 4 datas) | O servidor recebe o ID da opção selecionada no `ChatPollEmbed` da Etapa 6:<br>• **Atingiu:** Selecionou a opção que demonstra correlação causal exata das datas de Lia com os cancelamentos da Linha 302 E exige investigação prévia de dados ausentes de Davi antes de qualquer sanção.<br>• **Em processo:** Selecionou a opção que isenta Lia com base no cruzamento, mas acata a suspensão imediata de Davi sob a justificativa de "ausência de registro no sistema".<br>• **Não atingiu:** Selecionou a opção genérica que aceita a punição automática de ambos ou rejeita a análise de dados como irrelevante. |
| `EF09CO07` *(Primária)* | **Canal B** | `submit_poll_canal_b` | `poll_option_id` | Pergunta: *"Ao analisar a recomendação de uma IA que seleciona pessoas com base em históricos prévios, qual postura ética o avaliador deve adotar?"*<br>• **Atingiu:** *"Auditar os dados de treinamento para identificar lacunas históricas e assumir a responsabilidade humana pela decisão final."*<br>• **Em processo:** *"Aceitar a sugestão da máquina caso os critérios matemáticos pré-definidos tenham sido rigorosamente seguidos."*<br>• **Não atingiu:** *"Descartar o uso de computadores e decidir exclusivamente pela intuição pessoal."*<br>*Componente:* `ChatPollEmbed`. O estudante vê apenas confirmação de envio diegético. O servidor sorteia a ordem das alternativas. |
| `EF09CO08` *(Secundária)* | **Canal A** | `submit_decidir_decision` | `poll_option_id` (após seleção do projeto de R$ 12.000) | O servidor recebe o ID da opção selecionada no `ChatPollEmbed` da Etapa 3:<br>• **Atingiu:** Selecionou a opção que problematiza a disparidade estrutural de infraestrutura digital entre projetos e demonstra compreensão de como a distribuição desigual de recursos afeta o poder de decisão.<br>• **Em processo:** Selecionou a opção que menciona a vantagem dos arquivos digitais do projeto escolhido, mas sem problematizar a desigualdade de acesso e de recursos que gerou essa diferença.<br>• **Não atingiu:** Selecionou a opção que trata projetos sem documentação digitalizada como inferiores, desorganizados ou desqualificados para receber verba pública. |
| `EF09CO08` *(Secundária)* | **Canal B** | `submit_poll_canal_b` | `poll_option_id` | Pergunta: *"Por que uma organização social que mantém dados apenas em papel corre maior risco de ser excluída por políticas públicas automatizadas?"*<br>• **Atingiu:** *"Porque a escassez de infraestrutura digital impede que seu trabalho real seja capturado por sistemas de triagem algorítmica."*<br>• **Em processo:** *"Porque sistemas computacionais são mais rápidos e exigem relatórios legíveis para arquivamento."*<br>• **Não atingiu:** *"Porque cadernos em papel têm menor validade legal do que planilhas digitais."*<br>*Componente:* `ChatPollEmbed`. Exibição pós-Refletir sem sinal de acerto/erro. |

*Grau de medida:* Uma resposta de Canal B isolada gera sinal `indicative`. Ela é consolidada como `scored` no dashboard quando combinada com a ação correspondente do Canal A da mesma habilidade.

---

## 13. Cenários de dispositivo

* **Cenário 1:1 (Um estudante por dispositivo — Ideal):**
  * O estudante opera com autonomia completa no chat, escolhe ativamente suas perguntas investigativas, experimenta o dilema da trava vinculante e toma o susto contrafactual na Etapa 4 de forma direta.
* **Cenário 2 a 4 estudantes por dispositivo (Grupo de bancada):**
  * Os estudantes atuam como uma "banca colegiada de conselheiros". Um estudante digita enquanto os demais debatem quais perguntas fazer e qual projeto homologar.
  * A descoberta central chega com o mesmo impacto pedagógico, enriquecida pela negociação prévia do grupo antes da trava irreversível.
* **Cenário de Projeção Única (Sem computadores individuais — Contingência total):**
  * O professor projeta a missão na lousa digital ou telão. Ele assume o papel de escrivão da comissão.
  * Os estudantes sugerem em voz alta os prompts e votam por aclamação ou contagem de braços erguidos para cada decisão em tela. O professor insere a escolha majoritária da sala. A revelação e o debate na Etapa 4 ocorrem coletivamente com apoio do material físico do estudante.

---

## 14. Guardrails e IA

* **IA na preparação docente:** A geração de novos recortes temáticos via Vertex Gemini ocorre exclusivamente no ambiente seguro do professor (`apps/api/src/ai`), com controle de cota e obrigatoriedade de aprovação curatorial humana antes de qualquer distribuição para as turmas.
* **IA na experiência do estudante:** O assistente ChatGPT vivenciado pelo estudante é um ambiente determinístico simulado que roda sobre uma base estruturada fechada (`base_dados_conselho.json`). Isso elimina riscos de alucinações ofensivas, vazamento de dados ou respostas imprevisíveis.
* **Proteção contra rotulação do estudante:** Em nenhuma hipótese o sistema emite diagnósticos morais, notas punitivas ou rótulos psicológicos sobre o estudante (ex.: "aluno ingênuo" ou "aluno preconceituoso"). Os relatórios analíticos registram estritamente os níveis de evidência de aprendizagem (*Atingiu*, *Em processo*, *Não atingiu*).
* **Affordance x Guardrail:** O input de texto no chat possui filtro sanitizador estrito no cliente que impede a colagem de scripts ou termos discriminatórios graves, respondendo com mensagem institucional formal: *"O sistema do conselho aceita apenas consultas pertinentes às diretrizes orçamentárias."*.

---

## 15. Tetos aplicados à faixa (9º ano do Ensino Fundamental)

* **Decisões do mesmo tipo por ato:** No máximo 1 grande decisão vinculante por etapa de ação (a escolha do projeto na Etapa 3 e o parecer no caso de transporte na Etapa 6).
* **Opções por decisão:** Rigorosamente 3 opções simultâneas (Mesa Aberta, Ponto de Apoio e Conexão para Continuar na Etapa 3; e exatamente 3 alternativas por enquete no `ChatPollEmbed`).
* **Duração por ato em tela:** Entre 3 e 8 minutos contínuos, garantindo foco cognitivo sem sobrecarga atencional.
* **Etapas cognitivas por decisão:** Até 3 passos encadeados (Auditar dados → Selecionar alternativa discreta → Travar voto irreversível).
* **Teto de palavras por string de interface:** Textos informativos de chat com no máximo 120 palavras por bloco de resposta, permitindo leitura dinâmica e escaneabilidade em tela.

---

## 16. Requisitos técnicos e escopo

* **V1 Mínimo Jogável:**
  * Motor de simulação do ChatGPT (`chatgpt`) com renderização de mensagens, sugestões efêmeras (`ChatSuggestionsEmbed`) e streaming textual simulado;
  * Componente nativo de trava decisória (`ChatDecisionLatchEmbed`);
  * Componente de enquete estruturada nativa (`ChatPollEmbed`);
  * Mecanismo de persistência no servidor de sessão via API institucional;
  * Sincronização de etapas mediadas por polling HTTP curto no hub (`expNNefNb_gates_turma`);
  * Banco de dados curado default (Mesa Aberta, Ponto de Apoio e Conexão para Continuar).
* **V2 (Evoluções futuras):**
  * Geração dinâmica assistida de novos cenários orçamentários por professores via Vertex Gemini com curadoria em interface WYSIWYG;
  * Exportação de síntese em PDF do Dossiê do Conselheiro para compor o portfólio físico escolar.
* **Permissões de manifesto:** `permissoes: [forms]` (necessário para a submissão dos componentes nativos de seleção e enquetes do design system).

---

## 17. Hipóteses de validação

1. **Hipótese de Indução Algorítmica (Caminho B):** Assume-se que pelo menos 65% dos estudantes sem mediação prévia escolherão o projeto com mais PDFs digitais (Conexão para Continuar), validando a crença de que "mais dados digitais equivalem a maior legitimidade".
   * *O que observar:* Porcentagem de cliques no projeto Conexão para Continuar antes da revelação.
   * *O que indica falha:* Se mais de 80% da turma desconfiar imediatamente da falta de relatórios do Mesa Aberta sem instrução, o briefing pode estar excessivamente óbvio.
2. **Hipótese de Virada Cognitiva (Aha):** Assume-se que a revelação contrafactual dos cadernos físicos de campo gerará desestabilização suficiente para que o estudante compreenda a diferença entre ausência de dados e ausência de trabalho social real.
   * *O que observar:* Participação ativa e mudança de perspectiva expressa no debate socrático da Etapa 4.
   * *O que indica falha:* Estudantes insistirem que a decisão correta era a primeira porque "o papel não tem validade técnica".
3. **Hipótese de Usabilidade de Avaliação Discreta:** Assume-se que a substituição de campos de texto livre por cruzamento de tabelas e `ChatPollEmbed` mantém o engajamento reflexivo sem gerar atrito de digitação no tempo de 50 minutos.
   * *O que observar:* Taxa de conclusão da Etapa 6 dentro da janela de 7 minutos.

---

## 18. Decisões de direção, trade-offs e propostas

### Decisões de direção herdadas do núcleo
1. **Ajuste integral do Canal A para ação discreta + múltipla escolha:** Em conformidade estrita com o pedido de correção, foi erradicada toda dependência de leitura e avaliação de texto livre pelo professor. O Canal A de `EF09CO07` é capturado pelo cruzamento interativo de tabelas na Etapa 6 seguido de pergunta estruturada com 3 alternativas mapeadas 1:1 para *Atingiu*, *Em processo* e *Não atingiu* via `ChatPollEmbed`. O Canal A de `EF09CO08` na Etapa 3 segue idêntica estrutura.
2. **Desenvolvimento do Candidato A da Ideação (O Dossiê Invisível):** Foco no dilema dos R$ 12.000 indivisíveis entre alimentação, acolhimento ao bullying e laboratório digital.
3. **Preservação da Bifurcação Investigativa (Caminho A / Caminho B):** Mantida a porta investigativa na Etapa 2 (`E2_CADERNOS_OFERECIDOS` e `E2_CADERNOS_DESBLOQUEADOS`) com registro da flag `caminho_tomado`.
4. **Presença minimalista de Amara (Regra 6):** Amara atua pontualmente na abertura (Desafiar) e na sistematização (Explicar), garantindo autonomia e tom maduro para o 9º ano.
5. **Diferenciação do catálogo (Regra 16):** Foco em auditoria algorítmica de triagem orçamentária no ChatGPT com avaliação automatizada por componentes nativos de design system.

### Decisões adicionadas pelo P0b
6. **Mapeamento de affordances nativas no ChatGPT simulado:** A interface utiliza o componente nativo `ChatPollEmbed` para renderizar as questões de avaliação pedagógica diretamente na thread, evitando diálogos modais intrusivos e preservando a ilusão de um assistente institucional corporativo.
7. **Tratamento de contingência para projeção única:** Inclusão de fluxo de debate por bancada e votação coletiva mediada pelo professor caso a escola enfrente queda total do laboratório de informática, garantindo a viabilidade de execução do programa pedagógico em qualquer rede pública de ensino.
8. **Subordinação do texto livre à condição de reflexão qualitativa facultativa:** Qualquer campo de anotação de parecer textual mantido na tela serve estritamente para o estudante organizar suas ideias para o debate oral, sem jamais bloquear a transição de telas ou gerar pendência de correção manual no dashboard docente.

---

**MISSÃO DIGITAL UNOORIA · BRIEFING DE ESCOPO (LEITURA RÁPIDA)**

**"Eu achei que estava avaliando qual projeto fazia o melhor trabalho, mas na verdade estava julgando apenas pela quantidade de documentos digitais que a inteligência artificial tinha para ler."**

*Nome de trabalho: "O Dossiê Invisível" · Cenário: Uma comissão comunitária usa um assistente de inteligência artificial para auditar projetos sociais e destinar R$ 12.000, descobrindo que a máquina privilegia arquivos digitais em detrimento do trabalho social de campo.*

9º ano EF · Missão digital individual com debate coletivo mediado · 50 min em sala · Spec em aprovação de engenharia · Protótipo V1 funcional em simulador chatgpt

# 1. O QUE É ESTA MISSÃO
Uma experiência imersiva de tomada de decisão orçamentária e letramento digital crítico. No papel de Conselheiro Relator da Comissão Municipal de Recursos Comunitários, o estudante do 9º ano precisa destinar uma verba única e indivisível de R$ 12.000 para um entre três projetos sociais locais urgentes: o **Mesa Aberta** (alimentação escolar no contraturno, 24 vagas, registros em cadernos de papel), o **Ponto de Apoio** (enfrentamento do bullying e acolhimento emocional, 18 vagas) e o **Conexão para Continuar** (laboratório de computadores e inclusão digital, 20 vagas, dezenas de relatórios padronizados em PDF). Ao consultar o assistente de IA, o estudante se depara com uma recomendação que penaliza o projeto de alimentação por "falta de consistência documental". A missão força o estudante a decidir, auditar lacunas de dados e confrontar a falácia de que decisões automatizadas são neutras.

# 2. O AMBIENTE — chatgpt
A missão transcorre integralmente dentro de uma réplica do ambiente corporativo do **ChatGPT**. O estudante interage via prompts de texto, utiliza pílulas opcionais de sugestão rápida e lida com respostas em formato Markdown, tabelas comparativas e cards de decisão integrados. Não há fuga de ambiente nem popups externos de celebração genérica: toda a tensão institucional e ética é mediada na thread de mensagens.

# 3. CAMADA DO PROFESSOR — CONTROLE DE LIBERAÇÃO
* **Preparo docente simples:** O professor pode ativar a missão em apenas dois cliques utilizando o banco curado padrão ou customizar o tema para sua disciplina (Língua Portuguesa, Ciências, História, Geografia ou Projeto de Vida) com geração assistida por IA.
* **Trava de sincronização:** A plataforma utiliza gates sincronizados por polling HTTP curto no hub. Ao término da Etapa 3 (após todos homologarem o voto irreversível), o sistema trava e aguarda o professor liberar a Etapa 4 no dashboard.
* **Debate projetado:** Na Etapa 4, o professor projeta na lousa o gráfico da turma gerado pelo painel, mostrando como a sala foi dividida pela recomendação da IA e conduzindo o debate socrático da virada.

# 4. O PAPEL DO PERSONAGEM-GUIA OU AGENTE DE IA
* **Amara (9º ano):** Personagem com presença deliberadamente contida. Surge na abertura (Desafiar) lançando o questionamento orientador e retorna apenas na Etapa 5 (Explicar) para sistematizar os conceitos de viés algorítmico e dados do passado junto à tese do livro didático.
* **O Assistente de IA simulado:** Atua como o interlocutor central durante a investigação. Ele não emite juízos morais; apenas calcula friamente sobre a base de documentos indexados, expondo a falha estrutural de desconsiderar dados que não estão em formato digital.

# 5. BEATS DA MISSÃO
1. **Desafiar:** Notificação oficial do conselho com a missão de destinar R$ 12.000 para 1 dos 3 projetos.
2. **Navegar:** O estudante investiga os projetos no chat. Se questiona a ausência de dados do Mesa Aberta, antecipa os cadernos físicos (Caminho A); se aceita as métricas prontas, a IA recomenda a Conexão para Continuar (Caminho B).
3. **Decidir:** Card de homologação vinculado a um cadeado irreversível (`latch: locked`) e enquete estruturada (`ChatPollEmbed`) sobre os critérios de escolha.
4. **Resultado / Aha:** O chat processa a auditoria dos cadernos físicos manuscritos. A recomendação inverte imediatamente para o Mesa Aberta. O estudante percebe que julgou volume de PDFs, não impacto social.
5. **Explicar:** Amara sistematiza formalmente com a turma os conceitos de viés algorítmico, dados do passado e decisões automatizadas.
6. **Refletir:** Caso do Transporte Escolar. O estudante cruza as tabelas de faltas de Lia e Davi com os cancelamentos da Linha 302 e comprova a falha do corte automatizado de benefícios.

# 6. O QUE ESTAMOS VALIDANDO
* A eficácia da simulação em desmistificar a suposta "neutralidade matemática" de sistemas algorítmicos para estudantes de 14–15 anos.
* A retenção do conceito de que a responsabilidade ética pelas escolhas sociais e políticas é indelegável e permanece humana.
* A robustez da telemetria de avaliação formativa baseada exclusivamente em ações discretas e enquetes estruturadas (`ChatPollEmbed`), eliminando a sobrecarga de correção manual de texto livre pelo professor.

# 7. HABILIDADES BNCC E CRITÉRIOS CURRICULARES
* **Foco Primário:** `EF09CO07` — *Avaliar aplicações e implicações políticas, socioambientais e culturais das tecnologias digitais para propor alternativas aos desafios do mundo contemporâneo, incluindo aqueles relativos ao mundo do trabalho.*
* **Habilidade Secundária:** `EF09CO08` — *Discutir como a distribuição desigual de recursos de computação em uma economia global levanta questões de equidade, acesso e poder.*
* **Contrato de Evidências Discretas:** Ambas as habilidades são avaliadas pelo cruzamento de evidências discretas em tela (ações do estudante) somadas a enquetes de múltipla escolha com 3 alternativas mapeadas para a régua ternária (*Atingiu*, *Em processo*, *Não atingiu*), com gabarito seguro no servidor.

# 8. STATUS ATUAL E PRÓXIMOS PASSOS
* **Status:** Núcleo narrativo v2.0 aprovado por micro-gate; seções de apoio e contrato de evidências 12a totalmente adequados à diretriz de scoring discreto sem dependência de texto livre.
* **Próximos passos:** Geração e auditoria do Manifesto técnico (`exp09ef1b`), validação determinística de BNCC e envio para desenvolvimento dos componentes visuais do chat no Storybook Unooria.