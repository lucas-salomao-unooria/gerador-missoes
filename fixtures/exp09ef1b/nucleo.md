# Núcleo narrativo — O Dossiê Invisível v2.0

## O que mudou nesta versão
1. **Adequação do Canal A de evidências:** Substituição estrita de campos dissertativos em texto livre por ação discreta em tela seguida de múltipla escolha com 3 alternativas mapeadas 1:1 para a régua ternária (*Atingiu*, *Em processo*, *Não atingiu*) via componente nativo `ChatPollEmbed` (na Etapa 3 para `EF09CO08` e na Etapa 6 para `EF09CO07`).
2. **Correção de cobertura conceitual (Tabela 1.2 — Nomeação):** Remoção de delimitadores pontiagudos de texto (`<...>`) no passo Nomeação da anatomia do aha para sanar falso positivo de marcador de preenchimento, articulando a nomeação conceitual diretamente com os dados nominais da decisão do estudante e da turma.
3. **Reforço de profundidade (P2 e P4):** Interpolação textual e nominal explícita da aposta homologada pelo estudante na Etapa 3 ("Você homologou o repasse para o projeto [Nome do Projeto Votado]...") na virada da IA (Etapa 4) e no card explicativo de Amara comparado à proporção de votos da turma (Etapa 5).

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

## 18-parcial. Decisões de direção e propostas P0a

### Decisões de direção desta versão
1. **Ajuste integral do Canal A para ação discreta + múltipla escolha:** Em conformidade estrita com o pedido de correção, foi erradicada toda dependência de leitura e avaliação de texto livre pelo professor. O Canal A de `EF09CO07` é capturado pelo cruzamento interativo de tabelas na Etapa 6 seguido de pergunta estruturada com 3 alternativas mapeadas 1:1 para *Atingiu*, *Em processo* e *Não atingiu* via `ChatPollEmbed`. O Canal A de `EF09CO08` na Etapa 3 segue idêntica estrutura.
   * *Alternativa descartada:* Manter campos abertos de parecer dissertativo avaliados por rubrica subjetiva.
   * *O que essa escolha testa ou arrisca:* Elimina a sobrecarga docente de correção manual de textos longos na aula de 50 minutos e padroniza a telemetria do dashboard institucional B2G.
2. **Desenvolvimento do Candidato A da Ideação (O Dossiê Invisível):** Desenvolveu-se o Candidato A, conforme determinado pelo briefing pedagógico, que obteve nota máxima (4 em todas as dimensões).
   * *Alternativas descartadas:* Candidato B (triagem de bolsas escolares) e Candidato C (auditoria de RH corporativo).
   * *O que essa escolha testa ou arrisca:* Garante alta identificação emocional com o drama comunitário dos três adolescentes (João, Ana e Luana) e cumpre perfeitamente o dilema orçamentário dos R$ 12.000.
3. **Preservação da Bifurcação Investigativa (Caminho A / Caminho B):** Mantida a porta investigativa na Etapa 2 (`E2_CADERNOS_OFERECIDOS` e `E2_CADERNOS_DESBLOQUEADOS`) com registro da flag `caminho_tomado`.
   * *Alternativa descartada:* Forçar todos os alunos pelo mesmo trilho rígido.
   * *O que essa escolha testa ou arrisca:* Premia a investigação crítica ativa do estudante apressado versus o investigador diligente, alimentando a rica comparação contrafactual no debate em sala.
4. **Presença minimalista de Amara (Regra 6):** Amara atua pontualmente na abertura (Desafiar) e na sistematização (Explicar), conectando à tese do livro do 9º ano.
   * *Alternativa descartada:* Colocar Amara opinando ou mediando a cada prompt do chat.
   * *O que essa escolha testa ou arrisca:* Evita infantilizar o estudante do 9º ano e garante a imersão na relação profissional e autônoma com o assistente simulado de IA.
5. **Diferenciação do catálogo (Regra 16):**
   * *Contra qual missão se diferenciou:* `exp09ef1b` anterior (que utilizava parecer em texto livre) e missões de simulação neutra de IA.
   * *Em quê:* Implementação de avaliação puramente discreta de evidência com preservação do duplo canal, latch vinculante formal, interpolação nominal na virada e simulação contrafactual.

### O que o estudante apressado perde (Piso da Faixa — Regra 14)
* O estudante **apressado** (que clica na primeira sugestão da IA e aceita o ranqueamento por volume de PDFs) toma o Caminho B e homologa o Conexão para Continuar achando que fez uma escolha puramente técnica. Na Etapa 4, ele toma o choque de ver que o Mesa Aberta atendia mais jovens com urgência alimentar e que sua decisão foi induzida por uma assimetria documental.
* O estudante que **investiga** (Caminho A) questiona onde estão os dados de João, descobre os cadernos físicos antes de decidir, submete as evidências ao assistente e vivencia a inversão contrafactual com soberania analítica. Ambos convergem no mesmo conceito limiar, mas o contraste entre as posturas é exposto no gráfico da turma mediado pelo professor.

### Decisões abertas e propostas P0a
* Nenhuma pendência em aberto. Todas as travas pedagógicas, restrições estruturais de plataforma e o ajuste pontual do Canal A foram rigorosamente aplicados.