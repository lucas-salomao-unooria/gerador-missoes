```markdown
# Spec — O Dossiê Invisível v2.0

**9º ano EF · chatgpt · Rubrica v1.21 · Gate final: 🟡 em 2026-09-30**

## O que mudou nesta versão
Em conformidade estrita com o pedido de correção:
1. **Canal A de evidências integralmente discreto e ternário:** Substituição de qualquer campo dissertativo obrigatório de texto livre para fins de scoring pedagógico por ação discreta combinada a questão estruturada de múltipla escolha com 3 alternativas mapeadas 1:1 para a régua ternária (*Atingiu*, *Em processo*, *Não atingiu*) renderizadas via componente nativo `ChatPollEmbed` (na Etapa 3 para `EF09CO08` e na Etapa 6 para `EF09CO07`).
2. **Textos livres subordinados à condição facultativa:** O campo de parecer ou justificativa textual tornou-se estritamente opcional para organização de ideias do estudante e leitura qualitativa docente, gravado em tabela isolada e sem qualquer impacto na telemetria ou pontuação avaliativa.
3. **Preservação de todos os demais parâmetros:** Mantidos intactos o ambiente `chatgpt`, o dilema orçamentário dos três projetos (Mesa Aberta, Ponto de Apoio, Conexão para Continuar), a verba de R$ 12.000 indivisível, a bifurcação investigativa da Etapa 2 (Caminho A / Caminho B) com a flag `caminho_tomado`, a trava decisória irreversível (`latch: locked`), o caso de transferência Lia/Davi e a presença de Amara apenas no Desafiar e no Explicar.

---

## 0. Identificação de plataforma
O estudante vivencia a missão na interface corporativa clonada do assistente conversacional **ChatGPT** (`chatgpt`), atuando formalmente como Conselheiro Relator da Comissão Municipal de Recursos Comunitários. O viewport adotado é desktop, condizente com a interface de trabalho do chat em computadores ou chromebooks de laboratório escolar (1:1 ou bancadas). A seção do Design System fornece o layout de thread conversacional, balões de diálogo intercalados, stream de mensagens simulado, renderização de blocos Markdown (tabelas e metadados de arquivos anexos) e componentes de inserção inline.

- `id: exp09ef1b`
- `produto: entre-redes`
- `series: ["9EF"]`
- `unidade: 1`
- `publico: estudante`
- `viewport: desktop`
- `permissoes: [forms]`
- `capabilities: [telemetria, progresso, avaliacao]`
- `secao_ds: chatgpt`
- `versao: 0.1.0`
- `verbos: {attempted: "Iniciou a missão, carregou etapa ou acionou consulta no chat", interacted: "Interagiu com pílulas de prompt, anexos ou avisos de interface", progressed: "Avançou de etapa na esteira de investigação", scored: "Registrou resposta avaliativa no card de deliberação ou no cruzamento de dados", completed: "Concluiu a missão formalmente no encerramento da Etapa 6"}`
- `liberacao: por-turma`

---

## 1. Descoberta central
"Eu achei que estava avaliando qual projeto fazia o melhor trabalho, mas na verdade estava julgando apenas pela quantidade de documentos digitais que a inteligência artificial tinha para ler." — vivida no beat da **Etapa 4 (Resultado / Aha)**.

### Anatomia do aha
* **Crença de entrada:** "A IA é neutra e justa porque calcula dados objetivos sem sentimentos nem preconceitos" e "O projeto com mais relatórios em PDF com certeza funciona melhor do que aquele que anota no papel."
* **Aposta comprometida:** O estudante consulta o assistente simulado, avalia a recomendação induzida e trava irreversivelmente seu voto vinculante destinando os R$ 12.000 indivisíveis a um dos três projetos (ou confirma sua opção preliminar caso tenha antecipado os cadernos no Caminho A).
* **Consequência sentida:** O assistente emite parecer ranqueando os projetos a partir do volume e padronização dos arquivos digitais, rebaixando o Mesa Aberta a "alto risco orçamentário por déficit de comprovação documental".
* **Virada:** Ao incorporar os cadernos de campo manuscritos com registros diários de frequência e refeições mantendo os mesmos critérios de custo e atendimento, a recomendação da IA inverte radicalmente para o Mesa Aberta. O estudante constata que o algoritmo mediu a presença de arquivos digitalizados, não o trabalho social realizado.
* **Nomeação:** O Explicar nomeia formalmente viés algorítmico, dados do passado, identificação de padrões e decisões automatizadas, referenciando diretamente o projeto homologado pelo estudante e cruzando com os gráficos de votação da turma.
* **Transferência:** O Refletir apresenta o caso de corte automatizado de passe escolar de Lia e Davi (ambos com 4 faltas). O estudante cruza as tabelas de faltas e cancelamentos da Linha 302, identifica a correlação de Lia e argumenta pela suspensão de qualquer penalidade a Davi até a apuração de dados ausentes.

### Conceito limiar
* **C1 — A IA não é neutra: ela decide com base nos dados e critérios que recebeu, reproduzindo suas desigualdades.** Vivido concretamente nas etapas **Decidir (E3)** e **Resultado / Aha (E4)**.

---

## 2. Mecanismo por etapa

### Etapa 1 — Desafiar
* **Apresenta:** Interface do workspace "Conselho Municipal de Apoio Social" no ChatGPT. Mensagem de acolhimento institucional e provocação de Amara: *"Você tem R$ 12.000 para repassar a um único projeto. A máquina pode ler tudo rápido, mas lembre-se: se os dados contam uma história desigual, o que a máquina vai concluir?"*. Exibe 3 cartões de contexto resumindo os projetos: Mesa Aberta (24 vagas de almoço/permanência, João), Ponto de Apoio (18 vagas contra bullying, Ana) e Conexão para Continuar (20 vagas de inclusão digital, Luana). Três pílulas de prompt efêmeras sobre a barra de digitação:
  * `[Pílula 1: "Qual projeto atende mais pessoas pelo menor custo por vaga?"]`
  * `[Pílula 2: "Compare a regularidade e os relatórios enviados pelos três projetos."]`
  * `[Pílula 3: "Quais são as evidências de impacto de cada iniciativa?"]`
* **Ordena:** Leitura dos parâmetros orçamentários seguida da emissão do primeiro prompt no assistente.
* **Bloqueia:** Input de chat aceita no máximo 280 caracteres por prompt. O avanço de etapa fica bloqueado até o primeiro envio de mensagem.
* **Garante:** Se o estudante clicar em qualquer pílula ou digitar um prompt autoral e enviar, todas as pílulas de prompt desaparecem permanentemente da interface (`ChatSuggestionsEmbed` destruído).

### Etapa 2 — Navegar
* **Apresenta:** Thread de mensagens simuladas com respostas em streaming rápido. O assistente consulta `base_dados_conselho.json`.
  * Conexão para Continuar: 12 relatórios mensais em PDF na nuvem, gráficos de frequência e métricas analíticas.
  * Ponto de Apoio: Atas semestrais e relatórios intermediários.
  * Mesa Aberta: Ficha cadastral básica com anotação *"Déficit de relatórios na nuvem. Histórico institucional insuficiente para validação algorítmica."*
* **Ordena:** Interação investigativa livre por meio de prompts.
* **Bloqueia:** O botão "Emitir Parecer Vinculante" permanece oculto ou desabilitado até a troca de pelo menos 3 mensagens na thread (ou acionamento da bifurcação investigativa).
* **Garante (Bifurcação Investigativa Caminho A / Caminho B):**
  * **Caminho A (Investigação Ativa de Lacunas):** Se o prompt do estudante contiver termos de busca ou desconfiança sobre os dados ausentes do Mesa Aberta (ex.: *"caderno"*, *"papel"*, *"alimentação"*, *"onde estão os registros"*, *"físico"*), a IA transiciona para `E2_CADERNOS_OFERECIDOS` e responde: *"Constam nos arquivos físicos do conselho 3 cadernos de campo com registros diários de refeições e assinaturas dos responsáveis. Deseja anexar e processar esses dados agora?"*. Ao confirmar via clique no anexo, o sistema vai para `E2_CADERNOS_DESBLOQUEADOS`, define `caminho_tomado = "A"` e recalcula o parecer preliminar.
  * **Caminho B (Fluxo Convencional do Briefing):** Se o estudante não questionar a falta de documentos de João e comparar apenas os relatórios existentes, o sistema define `caminho_tomado = "B"`, mantém os cadernos ocultos e a IA emite parecer recomendando Conexão para Continuar como a opção de "maior governança técnica e menor risco documental".
  * Após 3 mensagens (ou desbloqueio dos cadernos), libera o botão "Emitir Parecer Vinculante".

### Etapa 3 — Decidir
* **Apresenta:** Card institucional `ChatDecisionLatchEmbed` no corpo da thread: "Homologação de Destinação Orçamentária — R$ 12.000". Lista os 3 projetos com botões de seleção de opção única (radio button). Abaixo, renderiza o componente `ChatPollEmbed` com a questão estruturada de posicionamento ético (Canal A de `EF09CO08`) e um campo opcional de anotação pessoal (não avaliado).
* **Ordena:** (1) Selecionar 1 projeto; (2) Responder à enquete de múltipla escolha no `ChatPollEmbed`; (3) Clicar em "Homologar Voto Irreversível".
* **Bloqueia:** O botão "Homologar Voto Irreversível" permanece desabilitado com cadeado cinza enquanto um projeto não for marcado E uma alternativa do `ChatPollEmbed` não for selecionada. Não é permitido marcar mais de um projeto nem fracionar a verba.
* **Garante:** Ao clicar em "Homologar Voto Irreversível", o estado transiciona para `E3_LATCH_LOCKED`. A interface congela permanentemente os inputs de seleção, exibe o ícone de cadeado fechado, grava `voto_etapa3` no servidor e trava a tela com o aviso: *"Parecer registrado. Aguardando autorização da presidência da mesa para abrir o próximo ponto de pauta."* (Gate do Professor via polling HTTP em `exp09ef1b_gates_turma`).

### Etapa 4 — Resultado / Aha
* **Apresenta:** Resposta do assistente de IA com badge "Auditoria de Integridade Convocada":
  * **Se Caminho B:** O assistente interpola nominalmente o projeto votado pelo estudante: *"Você homologou o repasse para o projeto [Nome do Projeto Votado]. Contudo, a equipe de campo localizou e digitalizou em caráter de urgência os Cadernos Físicos de Campo do projeto Mesa Aberta (180 dias de assinaturas, controle calórico e 24 jovens atendidos diariamente)."* O assistente roda o reprocessamento com os mesmos critérios de custo e atendimento: a recomendação inverte imediatamente para o Mesa Aberta.
  * **Se Caminho A:** A IA renderiza a simulação contrafactual personalizada: *"Você homologou seu voto em [Nome do Projeto Votado] após auditar os cadernos físicos. Se você não tivesse investigado as lacunas na Etapa 2, o sistema teria induzido seu voto para o Conexão para Continuar por causa dos 12 PDFs arquivados."*
  * Tabela comparativa em tela contrapondo: *Critério da IA (volume de PDFs)* versus *Realidade de campo (atendimento e urgência nutricional)*.
* **Ordena:** Leitura da inversão algorítmica e pausa obrigatória em tela para debate mediado pelo professor.
* **Bloqueia:** Botão de avanço para a Etapa 5 permanece travado até que o professor libere o gate da turma no dashboard docente.
* **Garante:** O professor visualiza no painel a proporção de alunos em Caminho A vs. Caminho B e o gráfico de votos homologados, projetando os dados para conduzir a mediação socrática.

### Etapa 5 — Explicar
* **Apresenta:** Card formativo assinado por Amara sistematizando os conceitos estruturais do capítulo: **viés algorítmico**, **dados do passado**, **identificação de padrões** e **decisões automatizadas**, interpolando o projeto homologado pelo estudante (*"Você homologou o repasse para o projeto [Nome do Projeto Votado]..."*). Interface apresenta ferramenta de ancoragem (*message highlight*).
* **Ordena:** O estudante clica para selecionar no histórico do chat duas mensagens-chave: (1) O parecer inicial que penalizou o Mesa Aberta por falta de relatórios digitais; (2) A tabela de reprocessamento pós-cadernos.
* **Bloqueia:** Botão "Avançar para Aplicação Prática" desabilitado até a marcação das 2 evidências textuais corretas.
* **Garante:** Feedback imediato no cliente confirmando a identificação dos momentos em que o viés operou na thread.

### Etapa 6 — Refletir
* **Apresenta:** Caso de transferência direta — O Transporte Escolar Municipal. Notificação da comissão disciplinar indicando suspensão do passe escolar de dois alunos, **Lia e Davi**, ambos com 4 faltas acumuladas em 20 dias letivos.
  * Duas tabelas interativas lado a lado:
    * *Tabela A (Frequência Escolar):* Faltas de Lia (03/mar, 10/mar, 17/mar, 24/mar) e faltas de Davi (04/mar, 11/mar, 18/mar, 25/mar).
    * *Tabela B (Relatório Operacional de Ônibus):* Cancelamentos da Linha 302 (bairro de Lia) em 03/mar, 10/mar, 17/mar e 24/mar. Bairro de Davi sem registros operacionais no consórcio (dados ausentes/não apurados).
  * Componente nativo `ChatPollEmbed` com a questão decisória do parecer de transporte (Canal A de `EF09CO07`).
  * Questões finais do Canal B das habilidades `EF09CO07` e `EF09CO08` via `ChatPollEmbed`.
  * Campo dissertativo de anotação pessoal opcional (sem scoring).
* **Ordena:** (1) Clicar nas 4 datas coincidentes de Lia entre a Tabela A e a Tabela B; (2) Responder ao `ChatPollEmbed` deliberativo do transporte; (3) Responder às perguntas conceituais do Canal B; (4) Clicar em "Concluir Missão".
* **Bloqueia:** Submissão do parecer de transporte bloqueada até a correspondência das 4 datas de Lia na tabela interativa.
* **Garante:** Ao clicar em "Concluir Missão", o SDK chama `concluir()`, emite `EVT-U03`, congela a sessão em estado final e exibe a mensagem de encerramento da comissão orçamentária.

---

### Contrato de estados
1. `E1_INICIAL` · Gatilho: Carregamento do workspace no client · Regra: Exibe mensagem de boas-vindas, cards dos 3 projetos e 3 pílulas efêmeras · Estado seguinte: `E1_AGUARDANDO_PROMPT` · Responsável: Unooria · Reversível: Não.
2. `E1_AGUARDANDO_PROMPT` · Gatilho: Estudante clica em pílula de sugestão ou digita texto e envia · Regra: Destrói `ChatSuggestionsEmbed` permanentemente, renderiza prompt na thread · Estado seguinte: `E2_INVESTIGANDO_CHAT` · Responsável: Estudante · Reversível: Não.
3. `E2_INVESTIGANDO_CHAT` · Gatilho: Prompt do estudante contém termos de dados de campo/físicos do Mesa Aberta · Regra: Detecta intenção investigativa de dados ausentes · Estado seguinte: `E2_CADERNOS_OFERECIDOS` · Responsável: Unooria · Reversível: Não.
4. `E2_CADERNOS_OFERECIDOS` · Gatilho: Estudante clica em "Anexar e Processar Cadernos Físicos" · Regra: Registra `caminho_tomado = "A"`, anexa dados de campo na base · Estado seguinte: `E2_CADERNOS_DESBLOQUEADOS` · Responsável: Estudante · Reversível: Não.
5. `E2_INVESTIGANDO_CHAT` · Gatilho: Troca de ≥ 3 mensagens sem questionar dados do Mesa Aberta · Regra: Registra `caminho_tomado = "B"`, emite parecer recomendando Conexão para Continuar · Estado seguinte: `E2_PRONTO_PARA_DECIDIR` · Responsável: Unooria · Reversível: Não.
6. `E2_CADERNOS_DESBLOQUEADOS` · Gatilho: Mensagem da IA recalculando com os cadernos · Regra: Libera botão de homologação com dados de campo integrados · Estado seguinte: `E2_PRONTO_PARA_DECIDIR` · Responsável: Unooria · Reversível: Não.
7. `E2_PRONTO_PARA_DECIDIR` · Gatilho: Estudante clica em "Emitir Parecer Vinculante" · Regra: Renderiza card de decisão orçamentária e enquete `ChatPollEmbed` · Estado seguinte: `E3_CARD_DELIBERACAO` · Responsável: Estudante · Reversível: Não.
8. `E3_CARD_DELIBERACAO` · Gatilho: Seleciona 1 projeto E responde à enquete do `ChatPollEmbed` · Regra: Habilita botão "Homologar Voto Irreversível" · Estado seguinte: `E3_APROVACAO_HABILITADA` · Responsável: Estudante · Reversível: Sim (pode trocar a seleção antes de travar).
9. `E3_APROVACAO_HABILITADA` · Gatilho: Estudante clica em "Homologar Voto Irreversível" · Regra: Grava `voto_etapa3`, congela seleções com ícone de cadeado, bloqueia edições · Estado seguinte: `E3_LATCH_LOCKED` · Responsável: Estudante · Reversível: Não (estado latch permanente).
10. `E3_LATCH_LOCKED` · Gatilho: Polling HTTP em `exp09ef1b_gates_turma` detecta gate E4 aberto pelo professor · Regra: Destrava tela do estudante para a virada algorítmica · Estado seguinte: `E4_AUDITORIA_REVELADA` · Responsável: Professor · Reversível: Não.
11. `E4_AUDITORIA_REVELADA` · Gatilho: Renderização da resposta do assistente (inversão pós-cadernos se Caminho B; contrafactual se Caminho A) · Regra: Apresenta tabela comparativa de critérios e bloqueia tela para debate · Estado seguinte: `E4_AGUARDANDO_DEBATE` · Responsável: Unooria · Reversível: Não.
12. `E4_AGUARDANDO_DEBATE` · Gatilho: Professor libera gate E5 no dashboard docente · Regra: Libera navegação para o Explicar · Estado seguinte: `E5_EXPLICAR_AMARA` · Responsável: Professor · Reversível: Não.
13. `E5_EXPLICAR_AMARA` · Gatilho: Seleção correta das 2 âncoras textuais no histórico de mensagens · Regra: Habilita botão de avanço para a transferência · Estado seguinte: `E6_REFLETIR_TRANSPORTE` · Responsável: Estudante · Reversível: Não.
14. `E6_REFLETIR_TRANSPORTE` · Gatilho: Cruzamento correto das 4 datas coincidentes de Lia nas tabelas · Regra: Ilumina correspondência em verde e destrava `ChatPollEmbed` de transferência · Estado seguinte: `E6_POLL_TRANSPORTE_LIBERADO` · Responsável: Estudante · Reversível: Não.
15. `E6_POLL_TRANSPORTE_LIBERADO` · Gatilho: Resposta ao `ChatPollEmbed` de transporte E às enquetes conceituais de Canal B · Regra: Habilita botão "Concluir Missão" · Estado seguinte: `E6_PRONTO_CONCLUSAO` · Responsável: Estudante · Reversível: Não.
16. `E6_PRONTO_CONCLUSAO` · Gatilho: Estudante clica em "Concluir Missão" · Regra: Invoca SDK `concluir()`, grava timestamp final e congela interface · Estado seguinte: `E6_CONCLUIDO` · Responsável: Estudante · Reversível: Não.
17. `MODO_ERRO_REDE` · Gatilho: Queda de conexão HTTP durante requisições operacionais · Regra: Exibe banner institucional: *"Conexão com o servidor da comissão interrompida. Reconectando aos registros..."*. Bloqueia ações em tela até reconectar · Estado seguinte: Retorna ao estado de origem após handshake · Responsável: Unooria · Reversível: Sim.
18. `MODO_ERRO_SESSAO` · Gatilho: Resposta 401/403 do servidor por expiração de credencial · Regra: Exibe modal diegético: *"Sua sessão como conselheiro relator expirou por segurança. Clique abaixo para reautenticar seu crachá digital."* · Estado seguinte: Recarrega no último checkpoint persistido após clique · Responsável: Estudante · Reversível: Não.

*Não existem outros caminhos de conclusão, correção antecipada, reabertura de escolha ou mudança de pacote.*

---

## 3. Caminhos degenerados — tratamento

| Caminho | O que acontece | Etapa preservada? |
|---|---|---|
| **Não escolheu nada (Inação na Etapa 3)** | O botão "Homologar Voto Irreversível" permanece travado e desabilitado com o ícone de cadeado cinza até que o estudante selecione 1 projeto e responda obrigatoriamente à enquete no `ChatPollEmbed`. | Sim. A interface não avança para o Resultado sem o voto formal registrado. |
| **Escolheu tudo / Tentativa de dividir a verba** | O sistema não oferece checkboxes nem campos fracionários de valor. Os botões operam em modo rádio estrito: selecionar um projeto desmarca automaticamente os demais e exibe a tag *"Fila de espera (sem abertura de vagas)"*. | Sim. Preserva a dor ética e a escassez material do recurso único de R$ 12.000. |
| **Não usou a ferramenta (Avançou rápido sem investigar)** | Se o estudante não fizer perguntas sobre os dados de João, cai compulsoriamente no **Caminho B**. A IA emite a recomendação induzida pelos 12 PDFs do Conexão para Continuar. | Sim. A experiência pedagógica é resguardada: o estudante sofre o impacto da virada na Etapa 4 ao descobrir que confiou em dados enviesados. |
| **Exploração mínima (1 pergunta curta e avanço)** | A IA responde com resumo genérico e o botão de deliberação só é habilitado após o teto mínimo de 3 mensagens ou abertura voluntária dos anexos. | Sim. Garante contato prévio com os relatórios antes da tomada de decisão vinculante. |
| **Terminou antes da turma** | Ao concluir a Etapa 6, a tela congela com o status *"Parecer arquivado. Aguardando deliberação da plenária."*. Uma aba lateral diegética libera a leitura do "Dossiê Histórico da Cidade" (texto complementar de apoio). | Sim. Evita spoilers e mantém o estudante ocupado com repertório relevante sem avançar etapas extras. |

---

## 4. Verbos e affordances

* **Digitar prompt:**
  * *Antes:* Campo de texto vazio na barra inferior com placeholder *"Consulte dados ou solicite relatórios da comissão..."*;
  * *Verbo:* Digitar string de busca/consulta e pressionar Enter ou clicar no botão de envio (ícone de seta);
  * *Depois:* Prompt renderizado no balão do usuário à direita; assistente inicia streaming simulado de resposta à esquerda.
* **Clicar em pílula de sugestão:**
  * *Antes:* Três pílulas de prompt flutuando sobre a barra de digitação (`ChatSuggestionsEmbed`);
  * *Verbo:* Clicar em uma das pílulas de sugestão;
  * *Depois:* O texto é disparado imediatamente para a thread; todas as pílulas desaparecem permanentemente da interface.
* **Clicar em anexo/arquivo:**
  * *Antes:* Card de anexo listado no chat com metadados (*"Cadernos_Fisicos_Campo.pdf — 3 volumes digitalizados"*);
  * *Verbo:* Clicar sobre o card de anexo;
  * *Depois:* Abre gaveta lateral com extrato textual dos registros de frequência e fotos dos manuscritos.
* **Selecionar alternativa em enquete (`ChatPollEmbed`):**
  * *Antes:* Três opções de múltipla escolha renderizadas nativamente na thread com caixas de seleção desmarcadas;
  * *Verbo:* Clicar no botão da opção desejada;
  * *Depois:* A opção selecionada ganha destaque visual ativo; identificador opaco da opção é enviado via rota operacional.
* **Travar deliberação (`ChatDecisionLatchEmbed`):**
  * *Antes:* Projeto selecionado no rádio; botão "Homologar Voto Irreversível" habilitado com cadeado aberto;
  * *Verbo:* Clicar no botão de homologação irreversível;
  * *Depois:* O botão congela no estado desabilitado com cadeado fechado (`latch: locked`); inputs de rádio são desativados permanentemente.
* **Cruzar linhas de tabelas:**
  * *Antes:* Linha da data 03/mar na Tabela A de faltas e 03/mar na Tabela B de cancelamentos em estado neutro;
  * *Verbo:* Clicar na data da Tabela A e em seguida na data correspondente da Tabela B;
  * *Depois:* Uma linha conectora surge e ambas as células passam ao preenchimento verde com ícone de correspondência causal confirmada.

---

## 5. Ausências declaradas

* **Sem edição de mensagens anteriores:** O estudante não pode alterar prompts já enviados no chat. *Motivo:* Preservar a rastreabilidade do raciocínio investigativo e a integridade da bifurcação Caminho A / Caminho B.
* **Sem botão "Regenerate response":** O assistente não reescreve suas saídas a pedido do usuário. *Motivo:* Garantir consistência determinística rigorosa com a base de conhecimento institucional configurada pelo professor.
* **Sem criação de conversas paralelas (botão "New Chat" desabilitado):** Não é permitido abrir novas abas de conversa. *Motivo:* Evitar dispersão de foco e perda do estado orçamentário deliberado.
* **Sem upload de arquivos arbitrários do computador:** O estudante não envia arquivos externos para a IA. *Motivo:* Evitar injeção de conteúdos descontrolados e resguardar os limites da simulação.
* **Sem navegação aberta na internet:** A IA não realiza buscas na web em tempo real. *Motivo:* O universo documental pertence estritamente ao território fictício homologado no preparo.
* **Sem modal intrusivo externo de pontuação:** A missão não exibe popups com confetes, estrelas ou notas numéricas de desempenho. *Motivo:* Preservar a imersão diegética do ambiente institucional de trabalho do conselho.

---

## 6. Tetos aplicados

* **Decisões do mesmo tipo por ato:** Rigorosamente 2 grandes decisões vinculantes na missão inteira (destinação da verba de R$ 12.000 na Etapa 3 e parecer de suspensão de passe no transporte escolar na Etapa 6) — dentro do cap de variedade de tarefa.
* **Opções por decisão:** Rigorosamente 3 projetos sociais no card da Etapa 3 e exatamente 3 alternativas por enquete no `ChatPollEmbed` — rigorosamente dentro do cap de 3 a 4 opções para o 9º ano EF (`literatura-cognitiva.md` §1).
* **Duração por ato em tela:** O maior ato contínuo em tela é a Etapa 2 (8 minutos); o maior ato mediado fora de tela é a Etapa 4 (12 minutos) — em conformidade com o teto de 10 a 12 minutos por ato para os anos finais (`literatura-cognitiva.md` §3).
* **Duração total em tela (tempo-aluno):** 31 minutos em tela (Etapa 1: 4m + Etapa 2: 8m + Etapa 3: 4m + Etapa 4: 3m + Etapa 5: 5m + Etapa 6: 7m) vs. 19 minutos de debate mediado fora da tela (Total: 50 minutos). Risco de duração mitigado expressamente pela arquitetura modular de fracionamento em 2 tempos de 25 minutos (Tempo 1: Etapas 1–3; Tempo 2: Etapas 4–6).
* **Etapas cognitivas por decisão:** Até 3 passos encadeados (Auditar relatórios → Selecionar alternativa discreta → Travar deliberação irreversível no latch).
* **Teto de palavras por string de interface:** Textos informativos de resposta do assistente limitados a ≤ 120 palavras por bloco, respeitando os parâmetros de escaneabilidade visual e a defasagem leitora do 9º ano EF (`literatura-cognitiva.md` §5 e §6).
* **Scaffolding e efemeridade:** As 3 pílulas de sugestão orientam a abertura, mas desaparecem permanentemente após a primeira interação do estudante para exigir formulação autônoma nas etapas seguintes.

---

## 7. Acessibilidade

* **Canais múltiplos por instrução:** Todo elemento visual crítico possui alternativa textual limpa. Se os gráficos ou fotos dos cadernos não carregarem, a interface injeta o extrato textual tabulado equivalente.
* **Teto informativo e densidade textual:** Máximo de 120 palavras por bloco no chat; tipografia com contraste mínimo 4.5:1 em conformidade com WCAG AA.
* **Navegação acessível por teclado:** Todos os inputs de rádio, enquetes `ChatPollEmbed`, links de anexo e botões de trava decisória possuem ordem de foco lógica via tecla Tab e acionamento por barra de espaço e tecla Enter.
* **Leitores de tela:** Componentes `ChatPollEmbed` e `ChatDecisionLatchEmbed` possuem atributos ARIA declarados (`role="radiogroup"`, `aria-checked`, `aria-disabled`), e atualizações de mensagens do chat utilizam `aria-live="polite"` para não interromper a leitura corrente.
* **Demonstração de gestos interativos:** O cruzamento de linhas entre as tabelas na Etapa 6 apresenta animação preliminar curta (micro-loop de 3 segundos) demonstrando o clique na Tabela A e na Tabela B antes do primeiro toque do estudante.

---

## 8. Professora, preparação e parametrização com IA

### Contrato de customização — Recorte da aula
A missão é transversal e pode ser preparada pelo professor de qualquer componente curricular. O contrato do recorte da aula consome:
* `disciplina`: Lista fechada dos componentes curriculares (`lingua-portuguesa`, `ciencias`, `historia`, `geografia`, `projeto-interdisciplinar`).
* `tema`: String descritiva (≤ 60 caracteres).
* `assuntos`: Lista de 3 a 6 itens (≤ 600 caracteres no total) representando os objetos de conhecimento da aula.
* `contexto`: String opcional (turma, escola, território local, ≤ 120 caracteres).
* `foco`: String opcional de ênfase pedagógica (≤ 120 caracteres).

### Schemas Zod de geração por IA (Vertex AI Gemini via `apps/api/src/ai`)
```typescript
import { z } from 'zod';

export const ParametrosPreparoExp09Schema = z.object({
  disciplina: z.enum(['lingua-portuguesa', 'ciencias', 'historia', 'geografia', 'projeto-interdisciplinar']),
  tema: z.string().max(60),
  assuntos: z.array(z.string()).min(3).max(6),
  contexto: z.string().max(120).optional(),
  foco: z.string().max(120).optional(),
});

export const ProjetoComunitarioSchema = z.object({
  id: z.enum(['projeto_a', 'projeto_b', 'projeto_c']),
  nome: z.string().max(60),
  responsavel: z.string().max(40),
  impacto_descricao: z.string().max(180),
  vagas: z.number().int().positive(),
  natureza_dados: z.enum(['cadernos_fisicos', 'relatorios_parciais', 'nuvem_completa_pdf']),
  resumo_arquivos: z.string().max(200),
  conteudo_anexo: z.string().max(500),
});

export const PacoteConteudoExp09Schema = z.object({
  turma_id: z.string().uuid(),
  titulo_workspace: z.string().max(80),
  mensagem_boas_vindas: z.string().max(280),
  projetos: z.array(ProjetoComunitarioSchema).length(3),
  respostas_chat: z.record(z.string().max(100), z.string().max(400)),
  dados_auditoria_revelacao: z.string().max(350),
});
```

### Rotas de preparo no módulo da missão
* `POST /exp09ef1b/turmas/:turmaId/gerar-conteudo`: Dispara a geração assíncrona do pacote temático via Vertex Gemini a partir dos parâmetros de recorte.
* `GET /exp09ef1b/turmas/:turmaId/conteudo`: Retorna o pacote gerado para visualização na interface do professor.
* `POST /exp09ef1b/turmas/:turmaId/homologar`: Salva as edições manuais feitas pelo professor nos textos do pacote e homologa a versão para aplicação.
* `POST /exp09ef1b/turmas/:turmaId/gate`: Libera a missão para a turma ou altera o estado dos gates síncronos de etapa (`E4` ou `E5`).
* `GET /exp09ef1b/turmas/:turmaId/painel`: Retorna os dados analíticos e de telemetria da turma para o dashboard docente.

### Fluxo de curadoria e fallback
* **Caminho curto (Banco padrão):** 2 telas, 2 cliques (`Selecionar Missão` → `Usar banco padrão e liberar`). O banco padrão carrega os projetos canônicos: Mesa Aberta (alimentação/cadernos), Ponto de Apoio (acolhimento) e Conexão para Continuar (informática/PDFs).
* **Fallback sem quota:** Se a cota de tokens na Vertex AI estiver zerada, a API responde HTTP 429 institucional e ativa compulsoriamente o banco padrão com aviso em tela: *"Limite de inteligência artificial atingido para este ciclo. A missão foi configurada automaticamente com o banco oficial curado."*
* **A mesma missão em três aulas:**

| Disciplina | Recorte do professor | O que a IA gera | O que não muda |
|---|---|---|---|
| **Língua Portuguesa** | *Acesso à literatura e combate à desinformação periférica.* | Projeto A: Saraus e biblioteca comunitária em cadernos de empréstimo; Projeto B: Oficina de combate a fake news com cartilhas mistas; Projeto C: Podcast e blog digital com relatórios analíticos de engajamento online. | Verba de R$ 12.000 para 1 projeto; IA ranqueia C pelo volume digital de métricas; cadernos de A revelam alcance físico omitido; voto vinculante. |
| **Ciências / Biologia** | *Saneamento ambiental, horta agroecológica e saúde comunitária.* | Projeto A: Horta comunitária contra insegurança alimentar com cadernos manuais de colheita; Projeto B: Coleta seletiva de resíduos; Projeto C: Monitoramento por sensores de qualidade do ar com dashboards e relatórios digitais em nuvem. | Verba de R$ 12.000 indivisível; IA recomenda C por relatórios automatizados; cadernos físicos de A mostram 100 famílias alimentadas; voto vinculante. |
| **História / Geografia** | *Preservação de memória quilombola/indígena e vulnerabilidade urbana.* | Projeto A: Preservação de história oral com cadernos manuscritos de anciãos; Projeto B: Cartografia social de riscos de encosta; Projeto C: Digitalização de acervo histórico com catálogo digital em PDF e planilhas online. | Verba de R$ 12.000 indivisível; IA privilegia C por estrutura de dados catalogada; registros orais em caderno mudam o parecer; caso Lia/Davi. |

### Controle de mediação e dados do painel docente
* A sincronização entre professor e estudantes é feita via polling HTTP curto (a cada 3 segundos) consultando a tabela `exp09ef1b_gates_turma` (sem WebSockets).
* O painel exibe:
  1. Gráfico de dispersão de investigação: Porcentagem de alunos no Caminho A (cadernos antecipados) vs. Caminho B (fluxo induzido pela IA);
  2. Gráfico de barras da homologação orçamentária: Destinação dos votos na Etapa 3 por projeto;
  3. Relatório formativo consolidado com níveis das habilidades `EF09CO07` e `EF09CO08`.
* **Roteiro de perguntas do debate mediado:**
  1. *"A qualidade real do trabalho do projeto Mesa Aberta aumentou quando descobrimos os cadernos de campo, ou o trabalho já existia e era a máquina que não conseguia enxergar?"*
  2. *"Por que um projeto comunitário que lida diretamente com urgência de alimentação tem muito mais dificuldade de gerar planilhas e relatórios em PDF do que uma oficina de informática?"*
  3. *"Se a prefeitura cortar uma verba ou suspender o passe de um estudante com base exclusiva na nota que a IA calculou, a culpa da injustiça é do algoritmo ou de quem aceitou a recomendação sem auditar os dados?"*

---

## 9. Evidências e dados

### Graus de medida
* `scored`: Medida derivada da combinação de ≥ 2 sinais operacionais independentes validados no servidor (ação discreta em tela + resposta ao `ChatPollEmbed`).
* `indicative`: Medida proveniente de um sinal único isolado (resposta a uma pergunta de Canal B antes do cruzamento com o Canal A).
* `zero`: O estudante teve a oportunidade técnica e visual de interagir no card ou na enquete, mas omitiu a ação voluntariamente antes de encerrar o tempo.
* `none`: A oportunidade de resposta não foi apresentada por interrupção de conectividade, queda de sessão ou travamento no gate docente (falha de plataforma nunca é decisão do estudante).

### Tabela de medidas

| Medida | Grau | Sinais | Canal | Tabela.coluna | Habilidade |
|---|---|---|---|---|---|
| `avaliacao_implicacoes_tecnologia` | `scored` | `cruzar_datas:tabela_transporte` + `responder:poll_transporte_canal_a` | operacional | `exp09ef1b_sessoes.score_ef09co07` | `EF09CO07` |
| `compreensao_disparidade_infraestrutura` | `scored` | `selecionar:projeto_orcamento` + `responder:poll_decidir_canal_a` | operacional | `exp09ef1b_sessoes.score_ef09co08` | `EF09CO08` |
| `conceito_auditoria_treinamento` | `indicative` | `responder:poll_canal_b_ef09co07` | operacional | `exp09ef1b_respostas_poll.nivel_opcao` | `EF09CO07` |
| `conceito_exclusao_digital_dados` | `indicative` | `responder:poll_canal_b_ef09co08` | operacional | `exp09ef1b_respostas_poll.nivel_opcao` | `EF09CO08` |
| `caminho_investigativo_trilhado` | `indicative` | `acionar:anexo_cadernos` | operacional | `exp09ef1b_sessoes.caminho_tomado` | `EF09CO08` |

### Canais por dado
* **Canal Operacional:** Rota síncrona `POST /exp09ef1b/sessoes/:id/evento` persistindo em `exp09ef1b_sessoes` e `exp09ef1b_respostas_poll`. Alimenta o dashboard em tempo real e os gates da turma.
* **Canal Analítico:** Disparos via SDK `track(verbo, objeto, resultado, contexto)` encaminhados assincronamente ao pipeline de telemetria analítica (`telemetria_eventos`).

### Texto livre de menor
Existe como campo facultativo de anotação na Etapa 3 (justificativa de bancada) e na Etapa 6 (parecer pessoal). **Finalidade:** Apoiar a fala oral do estudante no debate em sala. **Quem lê:** Exclusivamente o professor da turma no painel local (`GET /exp09ef1b/turmas/:turmaId/painel`). É gravado em tabela própria (`exp09ef1b_textos_reflexao`) isolada da telemetria e das rotas de gestor. Possui `chars_count`, sanitização estrita contra XSS e não interfere em nenhum cálculo de scoring da plataforma.

### Segredo de servidor
Nunca são expostos ao bundle do cliente:
* O mapeamento que associa os identificadores opacos de alternativas (`poll_option_id`) aos níveis da régua ternária (*Atingiu*, *Em processo*, *Não atingiu*);
* As flags e regras que determinam a transição oculta entre Caminho A e Caminho B na análise de intenção de busca;
* Os pesos e a matriz contrafactual do algoritmo simulado que recalcula o ranking dos projetos após os cadernos de campo.

- `gabarito_servidor: sim`

### Gabarito e regras de cálculo no servidor
O cliente transmite exclusivamente identificadores opacos (`option_id: "opt_ef09_07a_2"`). O backend da API realiza a validação contra a tabela interna e deriva o nível de competência no banco:

#### Canal A — `EF09CO07` (Etapa 6 — Refletir)
* **Ação discreta prévia obrigatória:** Cruzamento das 4 datas de cancelamento da Linha 302 com as 4 faltas de Lia (03/mar, 10/mar, 17/mar e 24/mar).
* **Pergunta:** "Com base no cruzamento das tabelas de transporte e frequência escolar, qual parecer a comissão deve emitir sobre Lia e Davi?"
  * `[Atingiu]`: Isentar as faltas de Lia pela correspondência exata com as falhas da Linha 302 e suspender qualquer punição a Davi até que os dados operacionais de sua linha de ônibus sejam apurados.
  * `[Em processo]`: Isentar Lia devido à comprovação de cancelamento da Linha 302, mas confirmar a suspensão do passe de Davi por falta de registros de falha no sistema.
  * `[Não atingiu]`: Manter a suspensão de ambos os estudantes para cumprir a regra de limite de 4 faltas registradas pelo sistema sem intervenção manual.

#### Canal A — `EF09CO08` (Etapa 3 — Decidir)
* **Ação discreta prévia obrigatória:** Seleção de 1 projeto no card de homologação dos R$ 12.000.
* **Pergunta:** "Ao analisar os documentos dos projetos sociais, como a comissão deve avaliar a diferença de relatórios digitais entre as iniciativas?"
  * `[Atingiu]`: Reconhecer que a falta de computadores e equipe de digitalização prejudica o registro de iniciativas comunitárias essenciais, exigindo validação de dados de campo antes do repasse.
  * `[Em processo]`: Considerar a existência de relatórios digitais padronizados como um diferencial técnico importante, independentemente das condições materiais da entidade.
  * `[Não atingiu]`: Desclassificar projetos que não possuam relatórios e planilhas na nuvem por considerá-los desorganizados ou despreparados para receber verba pública.

#### Canal B — `EF09CO07` (Fechamento)
* **Pergunta:** "Ao analisar a recomendação de uma IA que seleciona pessoas com base em históricos prévios, qual postura ética o avaliador deve adotar?"
  * `[Atingiu]`: Auditar os dados de treinamento para identificar lacunas históricas e assumir a responsabilidade humana pela decisão final.
  * `[Em processo]`: Aceitar a sugestão da máquina caso os critérios matemáticos pré-definidos tenham sido rigorosamente seguidos.
  * `[Não atingiu]`: Descartar o uso de computadores e decidir exclusivamente pela intuição pessoal.
  * *Componente:* `ChatPollEmbed`. Ordem das alternativas sorteada pelo servidor. Confirmação visual neutra no envio.

#### Canal B — `EF09CO08` (Fechamento)
* **Pergunta:** "Por que uma organização social que mantém dados apenas em papel corre maior risco de ser excluída por políticas públicas automatizadas?"
  * `[Atingiu]`: Porque a escassez de infraestrutura digital impede que seu trabalho real seja capturado por sistemas de triagem algorítmica.
  * `[Em processo]`: Porque sistemas computacionais são mais rápidos e exigem relatórios legíveis para arquivamento.
  * `[Não atingiu]`: Porque cadernos em papel têm menor validade legal do que planilhas digitais.
  * *Componente:* `ChatPollEmbed`. Ordem das alternativas sorteada pelo servidor.

### Mídia capturada do estudante
A missão declara expressamente que **NÃO** realiza captura de áudio (`microphone`), imagem/câmera (`camera`) ou gravação de tela (`display-capture`). Nenhuma permissão de mídia é solicitada ao navegador.

### Tabela de eventos da plataforma

| Verbo | Objeto | Quando dispara | `resultado` | `contexto` | Caminho | Onde é lido |
|---|---|---|---|---|---|---|
| `attempted` | `missao:iniciar` | Ao renderizar a primeira tela do estudante (E1) — também na reentrada (`EVT-U01`) | `{"retomada": false}` | `{"etapa": "E1"}` | analítico | `painel de produto (PostHog)` |
| `progressed` | `etapa:entrar` | Ao transicionar para cada etapa E1…E6 (`EVT-U02`) | `{"etapa": "E2"}` | `{"pedagogical_role": "core_action"}` | analítico | `painel de produto (PostHog)` |
| `completed` | `exp09ef1b` | Ao chamar `concluir()` da SDK no fechamento da Etapa 6 (`EVT-U03`) | `{"status": "finalizado"}` | `{"etapa": "E6"}` | analítico | `painel de produto (PostHog)` |
| `interacted` | `aviso:inatividade` | Ao disparar o aviso de inatividade de 90s (`EVT-U04`) | `{"segundos_sem_acao": 90}` | `{"etapa": "E2"}` | analítico | `painel de produto (PostHog)` |
| `attempted` | `erro:exibir` | Ao exibir estado de erro diegético (`EVT-U05`) | `{"codigo": "sem-sinal"}` | `{"etapa": "E2"}` | analítico | `painel de produto (PostHog)` |
| `interacted` | `chat:pilula_sugestao` | Ao clicar em uma das pílulas de prompt efêmeras na E1 | `{"pilula_id": 1}` | `{"etapa": "E1"}` | analítico | `painel de produto (PostHog)` |
| `interacted` | `chat:desbloquear_cadernos` | Ao clicar no anexo dos cadernos físicos na E2 (Caminho A) | `{"desbloqueou": true}` | `{"etapa": "E2"}` | analítico | `painel de produto (PostHog)` |
| `scored` | `decisao:homologar` | Ao clicar no botão com trava irreversível no latch na E3 | `{"projeto_id": "mesa_aberta", "latch_locked": true}` | `{"etapa": "E3"}` | operacional | `exp09ef1b_sessoes.projeto_homologado` |
| `scored` | `poll:submeter_canal_a_e3` | Ao registrar a resposta da enquete de Canal A na E3 | `{"option_id": "opt_ef09_08a_1"}` | `{"etapa": "E3", "habilidade": "EF09CO08"}` | operacional | `exp09ef1b_respostas_poll.nivel_opcao` |
| `interacted` | `tabela:cruzar_datas` | Ao concluir a correspondência das 4 datas na E6 | `{"pares_completos": 4}` | `{"etapa": "E6"}` | operacional | `exp09ef1b_sessoes.datas_cruzadas` |
| `scored` | `poll:submeter_canal_a_e6` | Ao registrar a resposta da enquete de Canal A na E6 | `{"option_id": "opt_ef09_07a_1"}` | `{"etapa": "E6", "habilidade": "EF09CO07"}` | operacional | `exp09ef1b_respostas_poll.nivel_opcao` |
| `scored` | `poll:submeter_canal_b` | Ao registrar respostas de Canal B no encerramento | `{"option_id": "opt_ef09_07b_1"}` | `{"etapa": "E6"}` | operacional | `exp09ef1b_respostas_poll.nivel_opcao` |

### DDL do banco de dados e políticas RLS

```sql
-- Tabela de sessões do estudante
CREATE TABLE exp09ef1b_sessoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    escola_id UUID NOT NULL,
    turma_id UUID NOT NULL,
    estudante_id UUID NOT NULL,
    caminho_tomado VARCHAR(2) NOT NULL DEFAULT 'B' CHECK (caminho_tomado IN ('A', 'B')),
    voto_etapa3 VARCHAR(30) CHECK (voto_etapa3 IN ('mesa_aberta', 'ponto_apoio', 'conexao_continuar')),
    latch_locked BOOLEAN NOT NULL DEFAULT FALSE,
    datas_cruzadas BOOLEAN NOT NULL DEFAULT FALSE,
    score_ef09co07 VARCHAR(20) CHECK (score_ef09co07 IN ('atingiu', 'em_processo', 'nao_atingiu')),
    score_ef09co08 VARCHAR(20) CHECK (score_ef09co08 IN ('atingiu', 'em_processo', 'nao_atingiu')),
    etapa_atual VARCHAR(20) NOT NULL DEFAULT 'E1_INICIAL',
    versao_instrumento VARCHAR(10) NOT NULL DEFAULT '0.1.0',
    criado_em TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE exp09ef1b_sessoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE exp09ef1b_sessoes FORCE ROW LEVEL SECURITY;
CREATE POLICY exp09ef1b_sessoes_escola_isolation ON exp09ef1b_sessoes
    FOR ALL USING (escola_id = current_setting('app.escola_id', true)::uuid);

-- Tabela de conteúdo parametrizado da turma (EVT-P01, EVT-P02, EVT-P03, EVT-P04)
CREATE TABLE exp09ef1b_conteudo_turma (
    turma_id UUID PRIMARY KEY,
    escola_id UUID NOT NULL,
    preparo_iniciado_em TIMESTAMPTZ, -- EVT-P01
    geracoes INT NOT NULL DEFAULT 0, -- EVT-P02
    tokens_usados INT NOT NULL DEFAULT 0, -- EVT-P02
    aprovado_em TIMESTAMPTZ, -- EVT-P03
    aprovado_por UUID, -- EVT-P03
    painel_visto_em TIMESTAMPTZ, -- EVT-P04
    painel_vistas INT NOT NULL DEFAULT 0, -- EVT-P04
    pacote_json JSONB NOT NULL,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE exp09ef1b_conteudo_turma ENABLE ROW LEVEL SECURITY;
ALTER TABLE exp09ef1b_conteudo_turma FORCE ROW LEVEL SECURITY;
CREATE POLICY exp09ef1b_conteudo_turma_escola_isolation ON exp09ef1b_conteudo_turma
    FOR ALL USING (escola_id = current_setting('app.escola_id', true)::uuid);

-- Tabela de sincronização de gates de turma
CREATE TABLE exp09ef1b_gates_turma (
    turma_id UUID PRIMARY KEY,
    escola_id UUID NOT NULL,
    etapa_liberada VARCHAR(20) NOT NULL DEFAULT 'E1',
    liberada_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE exp09ef1b_gates_turma ENABLE ROW LEVEL SECURITY;
ALTER TABLE exp09ef1b_gates_turma FORCE ROW LEVEL SECURITY;
CREATE POLICY exp09ef1b_gates_turma_escola_isolation ON exp09ef1b_gates_turma
    FOR ALL USING (escola_id = current_setting('app.escola_id', true)::uuid);

-- Tabela de histórico de abertura de gates (EVT-P05)
CREATE TABLE exp09ef1b_gates_historico (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    turma_id UUID NOT NULL,
    escola_id UUID NOT NULL,
    etapa VARCHAR(20) NOT NULL,
    liberada_em TIMESTAMPTZ NOT NULL DEFAULT NOW() -- EVT-P05
);

ALTER TABLE exp09ef1b_gates_historico ENABLE ROW LEVEL SECURITY;
ALTER TABLE exp09ef1b_gates_historico FORCE ROW LEVEL SECURITY;
CREATE POLICY exp09ef1b_gates_historico_escola_isolation ON exp09ef1b_gates_historico
    FOR ALL USING (escola_id = current_setting('app.escola_id', true)::uuid);

-- Tabela de respostas estruturadas de enquetes (ChatPollEmbed)
CREATE TABLE exp09ef1b_respostas_poll (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sessao_id UUID NOT NULL REFERENCES exp09ef1b_sessoes(id),
    escola_id UUID NOT NULL,
    poll_id VARCHAR(40) NOT NULL,
    option_id VARCHAR(40) NOT NULL,
    nivel_opcao VARCHAR(20) NOT NULL CHECK (nivel_opcao IN ('atingiu', 'em_processo', 'nao_atingiu')),
    respondido_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE exp09ef1b_respostas_poll ENABLE ROW LEVEL SECURITY;
ALTER TABLE exp09ef1b_respostas_poll FORCE ROW LEVEL SECURITY;
CREATE POLICY exp09ef1b_respostas_poll_escola_isolation ON exp09ef1b_respostas_poll
    FOR ALL USING (escola_id = current_setting('app.escola_id', true)::uuid);

-- Tabela isolada para texto livre opcional (lida apenas pelo professor da turma)
CREATE TABLE exp09ef1b_textos_reflexao (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sessao_id UUID NOT NULL REFERENCES exp09ef1b_sessoes(id),
    escola_id UUID NOT NULL,
    etapa VARCHAR(20) NOT NULL,
    texto TEXT NOT NULL,
    chars_count INT NOT NULL,
    registrado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE exp09ef1b_textos_reflexao ENABLE ROW LEVEL SECURITY;
ALTER TABLE exp09ef1b_textos_reflexao FORCE ROW LEVEL SECURITY;
CREATE POLICY exp09ef1b_textos_reflexao_escola_isolation ON exp09ef1b_textos_reflexao
    FOR ALL USING (escola_id = current_setting('app.escola_id', true)::uuid);
```

### 9f. Perguntas de produto desta missão

- `declared_lessons: 1`
- `core_action: scored decisao:homologar`
- `perguntas_herdadas: T7, T8, T9, T10, T11, T12, T14, T15, T16, T17, T19, T20`

| PQ | Pergunta | Decisão que dispara | Corte | Etapa | Ação (verbo:objeto) | Origem |
|---|---|---|---|---|---|---|
| PQ-01 | Que proporção de turmas mantém ≥ 65% dos votos no Conexão para Continuar na Etapa 3 quando segue o Caminho B? | <65% → O viés de volume digital está fraco: reforçar o tom técnico dos 12 PDFs no parecer da IA | turma | E3 | `scored decisao:homologar` | Origem: PO |
| PQ-02 | Quantos estudantes descobrem a porta de investigação dos cadernos na Etapa 2 (Caminho A) sem intervenção prévia do professor? | >40% → A porta investigativa está óbvia demais: calibrar os termos de busca para exigir reflexão crítica | missao | E2 | `interacted chat:desbloquear_cadernos` | Origem: PO |
| PQ-03 | Qual a porcentagem de estudantes que concluem o cruzamento tabular na Etapa 6 dentro da janela de 7 minutos? | <75% → A usabilidade do pareamento de datas está complexa: simplificar o clique entre Tabela A e B | serie | E6 | `interacted tabela:cruzar_datas` | [PROPOSTA — validar com PO] |
| PQ-04 | Que proporção de estudantes que votaram no Conexão para Continuar na E3 atingem o nível "Atingiu" no Canal A de `EF09CO07` na E6? | <50% → O Aha não gerou transferência cognitiva: ajustar o diálogo de Amara na Etapa 5 | turma | E6 | `scored poll:submeter_canal_a_e6` | [PROPOSTA — validar com PO] |
| PQ-05 | Quantos estudantes utilizam o campo de anotação dissertativa opcional mesmo sem obrigatoriedade de scoring? | <15% → O campo não agrega valor para a aula: remover o bloco de notas para reduzir carga cognitiva | escola | E3 | `scored decisao:homologar` | [PROPOSTA — validar com PO] |

---

## 10. Cenários de dispositivo

* **Cenário 1:1 (Um estudante por computador ou chromebook — Cenário de Referência):**
  * O estudante manuseia diretamente o teclado e o mouse, explora os nós de consulta no chat, experimenta pessoalmente o peso institucional de travar o latch irreversível e vivencia o impacto do contrafactual na Etapa 4 de forma direta.
* **Cenário de Bancada (2 a 4 estudantes por dispositivo):**
  * O grupo atua como "Conselho Deliberativo Colegiado". Um estudante atua como escrivão ao teclado enquanto os demais debatem quais perguntas formular ao assistente e deliberam conjuntamente qual projeto homologar.
  * A experiência pedagógica da descoberta e da virada é integralmente preservada, sendo potencializada pela argumentação entre os membros da bancada antes do acionamento da trava irreversível.
* **Cenário de Projeção Única (Lousa digital / TV conectada — Contingência de infraestrutura):**
  * O professor projeta a interface do ChatGPT na lousa e atua como relator-chefe da comissão.
  * Os estudantes analisam os dados dos projetos projetados, sugerem prompts oralmente e votam na destinação dos R$ 12.000 por contagem de braços erguidos em plenária. O professor insere a escolha majoritária da sala. A revelação e o debate na Etapa 4 ocorrem coletivamente com apoio do material físico do estudante.

---

## 11. Currículo

### Habilidades confirmadas
* **BNCC Computação — Eixo Cultura Digital (Foco Primário):**
  * `EF09CO07` — *Avaliar aplicações e implicações políticas, socioambientais e culturais das tecnologias digitais para propor alternativas aos desafios do mundo contemporâneo, incluindo aqueles relativos ao mundo do trabalho.* (Marcada como **letramento digital**).
  * *Momento em tela:* Na Etapa 6 (Refletir), o estudante audita a decisão disciplinar automatizada por IA, realiza o cruzamento causal entre a tabela de faltas escolares e o relatório de cancelamento de ônibus (Linha 302) e emite parecer via `ChatPollEmbed` propondo alternativa ética vinculante para proteger os direitos de Lia e Davi.
* **BNCC Computação — Eixo Cultura Digital (Habilidade Secundária):**
  * `EF09CO08` — *Discutir como a distribuição desigual de recursos de computação em uma economia global levanta questões de equidade, acesso e poder.* (Marcada como **letramento digital**).
  * *Momento em tela:* Na Etapa 3 (Decidir), o estudante confronta o card deliberativo em que um projeto comunitário carece de infraestrutura de digitalização e, via enquete estruturada `ChatPollEmbed`, reconhece formalmente como a assimetria material de recursos computacionais restringe o acesso ao poder orçamentário.
* **Conexões Interdisciplinares de Apoio (plausíveis, a confirmar em fonte oficial da BNCC):**
  * Língua Portuguesa (`EF89LP23`): Análise de estrutura argumentativa e operadores lógicos em relatórios técnicos institucionais.
  * Matemática (`EF09MA22`): Leitura e cruzamento de tabelas de dupla entrada e matrizes de ocorrências para identificar correlação e causalidade.
* **Competência Geral da BNCC:** Competência Geral 5 (Cultura Digital).
* **Competência Socioemocional Nomeada:** Tomada de decisão responsável.

### Matriz de evidência

| Código | Momento em tela | Ação observável | O que não conta | Medida do bloco 9 | Canal de evidência | Regra ternária |
|---|---|---|---|---|---|---|
| `EF09CO07` | `E6-ALU-01` (Refletir) | Cruza as 4 datas de faltas com cancelamentos e responde à enquete de transporte no `ChatPollEmbed` | Clicar em datas aleatórias sem pareamento causal ou chutar alternativas sem análise | `avaliacao_implicacoes_tecnologia` | `A + B` | **Atingiu:** Isenta Lia demonstrando a correlação das 4 datas com a Linha 302 E exige apuração de dados ausentes de Davi antes de qualquer sanção.<br>**Em processo:** Isenta Lia com base no cruzamento, mas acata a suspensão imediata de Davi sob pretexto de falta de dados no sistema.<br>**Não atingiu:** Acata a suspensão automática de ambos por excesso de faltas registradas pela IA ou desconsidera os dados de transporte. |
| `EF09CO08` | `E3-ALU-01` (Decidir) | Seleciona 1 projeto no card de homologação e responde à enquete de infraestrutura no `ChatPollEmbed` | Selecionar projeto aleatório e marcar opção de enquete sem fundamentação sobre recursos | `compreensao_disparidade_infraestrutura` | `A + B` | **Atingiu:** Problematiza a disparidade estrutural de infraestrutura digital entre projetos e reconhece que a assimetria tecnológica distorce o poder orçamentário.<br>**Em processo:** Aponta a vantagem dos arquivos digitais do projeto escolhido, mas sem relacionar com a desigualdade material de acesso aos computadores.<br>**Não atingiu:** Considera iniciativas sem registros digitalizados como inferiores, desorganizadas ou desqualificadas para receber verba pública. |

---

## 12. Decisões fechadas neste gate

* **Substituição definitiva de texto livre por ação discreta + múltipla escolha ternária no Canal A:** Decidido pelo time de Produto e Engenharia em 2026-09-30, acolhendo integralmente o Parecer de Adequação Pedagógica e a Avaliação Pedagógica. *Alternativas descartadas:* Correção manual de redações dissertativas pelos professores (inviável em escala na rede pública) e classificação semântica por LLM em tempo real no cliente (alto risco de alucinação e custo proibitivo de tokens).
* **Manutenção dos componentes `ChatPollEmbed` e `ChatDecisionLatchEmbed` nativos na thread:** Decidido pelo Design e Produto em 2026-09-30 para assegurar a imersão diegética no clone corporativo do ChatGPT. *Alternativa descartada:* Modais pop-up externos (quebrariam a imersão de ambiente de trabalho).
* **Preservação estrita dos tempos sugeridos (31 min tela + 19 min debate):** Ratificado pelo PO em 2026-09-30, aceitando o risco formal 6.2 mitigado pela opção de fracionamento em 2 tempos de 25 minutos. *Alternativa descartada:* Corte abrupto da etapa de debate na Etapa 4 (desidrataria o impacto pedagógico do Aha).

### Lista de pendências `[ABERTO — dono]`
*Nenhuma pendência em aberto. A especificação técnica e de produto está integralmente fechada e apta para desenvolvimento.*

---

## 13. Decisões D0 (Fechamento de Lacunas)

* **[D0-1] Bloco 2 (`2.reentrada`):** Caso o estudante atualize a página (F5), feche a aba ou acesse em outro instante, o cliente consulta `GET /exp09ef1b/sessoes/:id`, reidrata integralmente a thread de mensagens no estado exato em que foi interrompida, mantém desabilitadas as pílulas efêmeras já consumidas e restabelece a trava irreversível (latch) caso a sessão já tenha transitado por `E3_LATCH_LOCKED`. Nenhuma ação validada é descartada.
* **[D0-2] Bloco 2 (`2.segunda_aplicacao`):** A redefinição de progresso ("zerar turma") é uma ação privativa do professor no painel docente via `POST /exp09ef1b/turmas/:turmaId/zerar`. Essa ação arquiva as sessões correntes com status `arquivada` para fins de histórico e recria os registros com estado `E1_INICIAL`. Sem o comando explícito do professor, o estudante que já concluiu a missão e tenta reentrar é redirecionado compulsoriamente para o estado final de visualização de ata (`E6_CONCLUIDO`).
* **[D0-3] Bloco 2 (`2.modos_erro`):** Adiciona o estado `MODO_ERRO_MIDIA` ao contrato de estados:
  * *Gatilho:* Falha na renderização de tabelas interativas ou arquivos fac-símile dos cadernos;
  * *Regra:* Exibe card diegético no chat: *"Visualização gráfica indisponível. Carregando extrato textual transcrito dos arquivos."* Mantém o fluxo investigativo e a integridade da medição como `scored` ou `indicative`, sem classificar falha técnica como recusa ou erro do estudante (grau `none` para falhas de interface);
  * *Estado seguinte:* Retorna ao nó de origem da thread;
  * *Responsável:* Unooria;
  * *Reversível:* Sim.
* **[D0-4] Bloco 2 (`2.conclusao`):** Ao transicionar para `E6_CONCLUIDO`, a interface congela todos os botões de ação e campos de seleção, emite `EVT-U03` e bloqueia qualquer edição retrospectiva. O estudante permanece na interface do ChatGPT em modo de leitura irrestrito, podendo rolar o histórico completo da thread investigativa, rever a auditoria e acessar a aba diegética "Dossiê Histórico da Cidade" enquanto aguarda a turma.
* **[D0-5] Bloco 2 (`2.estado_espera_mediacao`):** Durante o estado `E4_AGUARDANDO_DEBATE`, enquanto a plataforma aguarda a liberação do gate E5 pelo professor, o rodapé da thread exibe o balão institucional: *"Sessão plenária em andamento. A presidência da mesa conduz a conferência dos dados em plenária antes da liberação do próximo parecer."* O campo de digitação de prompt permanece desabilitado com indicador visual de espera coletiva.
* **[D0-6] Bloco 8 (`8.gatilhos_handoff`):** Especifica as diretrizes operacionais de mediação no painel da professora para os dois gates síncronos:
  1. *No Checkpoint E3 (Liberação da Auditoria/Aha):* O painel exibe o alerta *"Todos os conselheiros homologaram o voto orçamentário. Projete o gráfico de distribuição de votos e clique em 'Liberar Auditoria dos Cadernos'"*. A professora clica no botão, o polling atualiza `exp09ef1b_gates_turma` para `E4` e ela pergunta: *"Por que tantos votos foram para o projeto com mais arquivos digitais?"*.
  2. *No Checkpoint E4 (Abertura da Sistematização):* Após o debate coletivo (12 min), o painel exibe *"Debate concluído. Clique em 'Liberar Etapa de Sistematização (Explicar)'"*. A professora orienta a turma a retornar às telas individuais e clica para liberar `E5`.
* **[D0-7] Bloco 9 (`9.retencao_dados`):** Os registros das tabelas operacionais (`exp09ef1b_sessoes`, `exp09ef1b_respostas_poll`, `exp09ef1b_textos_reflexao`) são retidos no banco durante o ano letivo corrente para fins pedagógicos e relatórios formativos da escola. Após 180 dias do encerramento do ano letivo, os textos facultativos de menor são expurgados permanentemente e as métricas de habilidades (`score_ef09co07`, `score_ef09co08`) são desvinculadas de qualquer identificador de estudante, permanecendo apenas como estatísticas agregadas anonimizadas da rede municipal/estadual.

---

## 14. Ambiente simulado (D9)

* **Nome do ambiente:** ChatGPT (`chatgpt`)
* **Seção do DS:** `chatgpt` (via ponte `@edu/ui/ds-chatgpt`, estilos `chatgpt.css` e tokens `--gpt-*`)
* **Dispositivo nativo:** Desktop cheio (viewport desktop em monitores e chromebooks de laboratório escolar, proporção fluida 16:9 / 16:10)
* **Chrome:**
  * Barra lateral recolhível à esquerda (`WebSidebar` / `Sidebar` com título do workspace fictício *"Conselho Municipal de Apoio Social"*, identificação do relator e histórico fixo da sessão);
  * Área principal de diálogo centralizada com rolagem vertical automática e balões intercalados (`ChatBubble`);
  * Barra inferior de entrada de comandos (`Composer` com campo `ChatInput`, botão de envio `IconButton` com glifo de seta e contêiner flutuante para pílulas de sugestão).
* **Mapeamento de verbos do Bloco 4:**

| Verbo da spec (bloco 4) | Rótulo literal na tela | Componente do DS existente | Componente local / composição |
|---|---|---|---|
| **Digitar prompt** | *"Consulte dados ou solicite relatórios da comissão..."* (placeholder) / Enter ou clique no ícone de envio | `Composer`, `ChatInput`, `IconButton` | — (DS existente) |
| **Clicar em pílula de sugestão** | 1. *"Qual projeto atende mais pessoas pelo menor custo por vaga?"*<br>2. *"Compare a regularidade e os relatórios enviados pelos três projetos."*<br>3. *"Quais são as evidências de impacto de cada iniciativa?"* | `PromptSuggestion` | `ChatSuggestionsEmbed` (composição local com gatilho de destruição permanente após 1º uso) |
| **Clicar em anexo/arquivo** | *"Cadernos_Fisicos_Campo.pdf — 3 volumes digitalizados"* (link de metadado inline) | `Button` (variante link/ghost), `Icon` | `AttachmentDrawer` (composição local com `Modal` / gaveta lateral de extrato fac-símile) |
| **Selecionar alternativa em enquete (`ChatPollEmbed`)** | Rótulos literais das 3 alternativas por enquete (conforme Etapa 3 e Etapa 6) com botões de rádio | `RadioButton`, `RadioGroup` (marca `unooria`) | `ChatPollEmbed` (candidato a componente do DS `chatgpt`: cartão inline estilizado com `--gpt-*`) |
| **Travar deliberação (`ChatDecisionLatchEmbed`)** | *"Homologar Voto Irreversível"* (botão com cadeado cinza/fechado pós-clique) | `Button`, `Icon` (Material Symbols `lock` / `lock_open`) | `ChatDecisionLatchEmbed` (candidato a componente do DS `chatgpt`: card inline com travamento irreversível) |
| **Cruzar linhas de tabelas** | Células com datas de faltas e datas de cancelamento (ex.: *"03/mar"*, *"10/mar"*, *"17/mar"*, *"24/mar"*) | `Table`, `TableCell`, `TableRow` (marca `unooria` com visual limpo Markdown) | `DataMatchTable` (composição local com realce verde e linha conectora de pareamento causal) |

* **Padrão de conteúdo e schema mínimo:**
  * Mensagens da thread: `ThreadMessage { id: string; remetente: 'usuario' | 'assistente' | 'sistema'; texto: string; blocos?: ('texto' | 'tabela_markdown' | 'anexo' | 'embed_poll' | 'embed_latch')[]; timestamp: string; }`
  * Cartão de projeto: `ProjetoCard { id: string; nome: string; vagas: number; arquivos_tipo: 'caderno' | 'pdf_nuvem' | 'atas'; status_auditoria: string; }`
* **Estados que a seção já traz:**
  * Vazio (`EmptyState` na abertura do chat antes do primeiro envio);
  * Carregando / Streaming (cursor piscante simulado na emissão de texto da IA);
  * Aguardando deliberação de plenária (campo de entrada desabilitado com mensagem institucional);
  * Modo de erro de rede (`MODO_ERRO_REDE` com banner diegético no topo da thread);
  * Modo de erro de sessão (`MODO_ERRO_SESSAO` com modal institucional de reautenticação);
  * Modo de erro de mídia (`MODO_ERRO_MIDIA` com extrato transcrito em texto puro).
* **Ausências por ambiente (o que a plataforma real NÃO tem):**
  * *Ausências estruturais da seção `chatgpt` (para alimentar a tabela de `ambientes.md`):* Memória de longo prazo entre conversas independentes; upload de imagens/arquivos arbitrários do computador; navegação e busca aberta na web pública em tempo real; biblioteca externa de plugins e GPTs de terceiros; modo de conversação por voz; histórico lateral de conversas fora do escopo da missão; respostas não curadas geradas em tempo real sem base homologada.
  * *Ausências declaradas da missão (Bloco 5 da spec):* Sem edição ou regravação de mensagens anteriores já enviadas; sem botão de reescrita ("Regenerate response"); sem criação de conversas paralelas (botão "New Chat" desabilitado); sem modais externos de pontuação gamificada ou confetes.
```

---