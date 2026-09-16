<!-- CÓPIA SINCRONIZADA de plataforma-unooria@4578555 (2026-09-16) · origem: docs/openapi.json · não edite: rode scripts/sincronizar_plataforma.py · placeholders entre chaves aparecem como «nome» por limitação de interpolação do ADK; no código real use chaves -->

# `docs/openapi.json` — índice de rotas (método · caminho · resumo · tags)

223 caminhos. O contrato completo (Zod → OpenAPI) está no repositório; aqui só o mapa.

| Método | Caminho | Resumo | Tags |
|---|---|---|---|
| POST | `/ai/gerar` | Conversa com o tutor de IA da experiência. | ai |
| GET | `/analise/atividades/«id»` | O detalhe de uma atividade, com a eficácia da escrita por perfil. | analise |
| GET | `/analise/csv` | Export do nível de produto — por run ou por evento. | analise |
| GET | `/analise/resumo` | Uma linha por atividade — o nível de produto. | analise |
| GET | `/atividades` | As atividades DESTE professor. | atividades |
| POST | `/atividades` | Cria a atividade em rascunho, com os defaults do motor. | atividades |
| GET | `/atividades/«id»` | O detalhe de uma atividade. | atividades |
| DELETE | `/atividades/«id»` | Exclui a atividade. | atividades |
| GET | `/atividades/«id»/analise` | A análise pedagógica da turma — identificada. | atividades |
| GET | `/atividades/«id»/analise/csv` | A mesma análise da turma, em planilha. | atividades |
| PATCH | `/atividades/«id»/antagonismo` | O professor aprova (ou reescreve) os dois lados e os neutros. | atividades |
| POST | `/atividades/«id»/ativar` | Ativa a atividade para os estudantes entrarem. | atividades |
| POST | `/atividades/«id»/destilar` | Destila a pergunta-chave e os dois lados a partir do recorte. | atividades |
| GET | `/atividades/«id»/distribuicao` | Onde cada estudante vai cair — antes de começar. | atividades |
| GET | `/atividades/«id»/estudantes/«runId»` | Tudo o que UM estudante fez, durante a atividade. | atividades |
| POST | `/atividades/«id»/etapa` | O RELÓGIO DA AULA: move a turma inteira de momento. | atividades |
| GET | `/atividades/«id»/etapa` | Etapa atual e quantos estudantes em cada tela. | atividades |
| GET | `/atividades/«id»/geracao/progresso` | O progresso da geração — o alvo do polling da tela. | atividades |
| POST | `/atividades/«id»/gerar` | Enfileira a geração dos posts. | atividades |
| PATCH | `/atividades/«id»/ia` | Liga ou desliga a IA ao vivo durante a aula. | atividades |
| POST | `/atividades/«id»/limpar` | Apaga as sessões dos estudantes, mantendo a atividade e os posts. | atividades |
| GET | `/atividades/«id»/monitor` | O painel da turma ao vivo. | atividades |
| POST | `/atividades/«id»/perfis` | Importa perfis à mão — o fallback do professor. | atividades |
| GET | `/atividades/«id»/perfis` | O estado do perfil de cada estudante, para conferência. | atividades |
| POST | `/atividades/«id»/perfis/da-vila` | Traz os perfis da Vila do Lume para a largada do Instanooria. | atividades |
| GET | `/atividades/«id»/posts` | A grade de revisão do professor, paginada e filtrável. | atividades |
| POST | `/atividades/«id»/redistribuir` | Rebalanceia a turma quando ela cai quase toda num lado. | atividades |
| POST | `/auth/login` | Autentica uma credencial da rede. | auth |
| POST | `/auth/trocar-senha` | Primeiro acesso: troca a senha provisória. | auth |
| POST | `/bemestar/checkins/«id»/respostas` | Responde as três frases do dia. | bemestar |
| DELETE | `/bemestar/dados` | Apaga TUDO do bem-estar do professor logado. | bemestar |
| GET | `/bemestar/historico` | Os ciclos concluídos e as anotações — só do próprio professor. | bemestar |
| GET | `/bemestar/hoje` | O check-in de hoje — o já respondido, o pendente, ou um novo. | bemestar |
| GET | `/bemestar/resumo` | Estado leve do check-in, para o card do hub. | bemestar |
| GET | `/escolas` | Todas as escolas do contrato, com contagem. | escolas |
| POST | `/escolas` | Cria uma escola. | escolas |
| POST | `/escolas/lotacoes-em-lote` | Lota uma pessoa em MUITAS escolas de uma vez. | escolas |
| GET | `/escolas/minhas` | As escolas de QUEM ESTÁ PEDINDO. | escolas |
| GET | `/escolas/minhas/relatorio` | Relatório da diretoria: consolidado e por escola. | escolas |
| GET | `/escolas/minhas/resumo` | O panorama de quem tem muitas escolas. | escolas |
| GET | `/escolas/profissionais` | Busca professor e coordenação na REDE inteira. | escolas |
| PATCH | `/escolas/«id»` | Edita os dados da escola. | escolas |
| DELETE | `/escolas/«id»` | Exclui uma regional. | escolas |
| POST | `/escolas/«id»/lotacoes` | Lota alguém nesta escola. | escolas |
| GET | `/escolas/«id»/pessoas` | Quem está lotado nesta escola. | escolas |
| GET | `/estudantes/«id»/historico` | O histórico do estudante ATRAVESSANDO escolas. | estudantes |
| GET | `/estudantes/«id»/perfil-portatil` | Monta o documento SEM assinatura, para o hub assinar. | estudantes |
| GET | `/estudantes/«id»/perfis-recebidos` | Os documentos que esta escola já recebeu sobre esta criança. | estudantes |
| POST | `/estudantes/«id»/transferir` | Transfere o estudante entre escolas da rede. | estudantes |
| GET | `/experiencias` | O catálogo de experiências do contrato. | experiencias |
| GET | `/experiencias/«expId»` | Uma linha do manifesto. | experiencias |
| PUT | `/experiencias/«expId»` | Publica ou faz rollback de uma versão. | experiencias |
| POST | `/foto-conta/feed` | Etapa 2: registra a exploração do feed e abre a decisão. | foto-conta |
| GET | `/foto-conta/galeria` | O mural da turma (pós-publicação): as fotos dos colegas, chegando. | foto-conta |
| GET | `/foto-conta/latch` | O polling do latch (3s): a turma já foi liberada? (ADR-94) | foto-conta |
| POST | `/foto-conta/marca` | Etapa 1: grava a marca escolhida e abre o mural. | foto-conta |
| POST | `/foto-conta/publicar` | Etapa 3 (o PICO): publica o par foto+legenda e devolve o eco dos colegas. | foto-conta |
| POST | `/foto-conta/reflexao` | Etapa 6: a síntese metacognitiva — o servidor decide, sem nota. | foto-conta |
| POST | `/foto-conta/roda` | Etapa 4 → 5: o eco terminou; a run entra no latch da Roda de Conversa. | foto-conta |
| GET | `/foto-conta/sessao` | O boot da missão: estado da run + o pacote da aula, sem a matriz do Aha. | foto-conta |
| GET | `/foto-conta/turmas` | As turmas de quem pergunta, para o seletor do painel. | foto-conta |
| GET | `/foto-conta/turmas/«turmaId»` | O dashboard ao vivo: distribuição A/B, latch e a lista de hesitação. | foto-conta |
| POST | `/foto-conta/turmas/«turmaId»/aprovar-pacote` | Aprova o pacote conferido no preview — o `cfg_turma_ready` da spec. | foto-conta |
| POST | `/foto-conta/turmas/«turmaId»/configurar` | Grava tema e nível de leitura da turma (o passo anterior à geração). | foto-conta |
| POST | `/foto-conta/turmas/«turmaId»/destravar-latch` | LIBERAR REFLEXÃO FINAL: destrava os tablets da turma inteira. | foto-conta |
| POST | `/foto-conta/turmas/«turmaId»/gerar-conteudo` | Gera o pacote da aula com IA (Vertex), para o preview do professor. | foto-conta |
| GET | `/foto-conta/turmas/«turmaId»/projecao` | A projeção da lousa (E5): o par lado a lado, os rótulos e as 3 perguntas. | foto-conta |
| POST | `/foto-conta/turmas/«turmaId»/reset` | Zerar e Reiniciar Turma: arquiva a tentativa e rearma o latch. | foto-conta |
| GET | `/healthz` | O processo está vivo. | healthz |
| DELETE | `/lotacoes/«id»` | Encerra o vínculo da pessoa com a escola. | lotacoes |
| POST | `/manifesto-ia/abrir-conversa` | Sai do briefing de Amara e abre o chat do EduPredict IA. | manifesto-ia |
| POST | `/manifesto-ia/clausula` | Fixa a salvaguarda prioritária — irrevogável (latch). | manifesto-ia |
| POST | `/manifesto-ia/concluir` | Finaliza o percurso e concede o selo — latch definitivo. | manifesto-ia |
| POST | `/manifesto-ia/disparar` | Envia um questionamento e recebe a defesa da máquina. | manifesto-ia |
| GET | `/manifesto-ia/gate` | Em que etapa a turma está — o polling de 5s do Checkpoint A. | manifesto-ia |
| POST | `/manifesto-ia/percurso` | O "Meu Percurso" — 2 palavras-chave e o parágrafo autoral (latch). | manifesto-ia |
| GET | `/manifesto-ia/sessao` | O estado da missão, o pacote da turma e a conversa reconstituída. | manifesto-ia |
| GET | `/manifesto-ia/turmas` | Turmas para o seletor do painel. | manifesto-ia |
| DELETE | `/manifesto-ia/turmas/«turmaId»` | Zerar a turma — a segunda aplicação. | manifesto-ia |
| GET | `/manifesto-ia/turmas/«turmaId»/conteudo` | O pacote da turma, com o material de mediação. | manifesto-ia |
| POST | `/manifesto-ia/turmas/«turmaId»/gate` | O botão mestre: Pausar para Debate / Retomar Missão. | manifesto-ia |
| POST | `/manifesto-ia/turmas/«turmaId»/gerar-conteudo` | Gera um RASCUNHO do pacote da turma com IA (pré-aula). | manifesto-ia |
| POST | `/manifesto-ia/turmas/«turmaId»/homologar` | O clique em "Aprovar Conteúdo da Turma" — o portão da exigência 8.2. | manifesto-ia |
| GET | `/manifesto-ia/turmas/«turmaId»/painel` | O painel de mediação ao vivo (Checkpoint A). | manifesto-ia |
| PATCH | `/matriculas/«id»` | Move de turma, ou torna esta a turma de referência. | matriculas |
| DELETE | `/matriculas/«id»` | Encerra a matrícula. | matriculas |
| POST | `/o-eco-no-grupo/acao` | Registra uma marca da investigação. | o-eco-no-grupo |
| POST | `/o-eco-no-grupo/amara` | Uma fala para Amara, no chat privado. | o-eco-no-grupo |
| POST | `/o-eco-no-grupo/desfazer` | "Apagar para todos e tentar outra resposta". | o-eco-no-grupo |
| GET | `/o-eco-no-grupo/gate` | Em que etapa a turma está (polling de ~5s). | o-eco-no-grupo |
| POST | `/o-eco-no-grupo/intervencao` | Envia a resposta citando o print — o pico da missão. | o-eco-no-grupo |
| GET | `/o-eco-no-grupo/midia` | As URLs das vozes e das fotos da missão. | o-eco-no-grupo |
| GET | `/o-eco-no-grupo/professor/material` | As três respostas com o gabarito e as reações do bairro, para o guia da aula. | o-eco-no-grupo |
| POST | `/o-eco-no-grupo/reflexao` | Entrega o "Meu percurso" e fecha a missão (latch). | o-eco-no-grupo |
| GET | `/o-eco-no-grupo/sessao` | O estado da missão, o conteúdo do grupo e a matéria completa. | o-eco-no-grupo |
| POST | `/o-eco-no-grupo/sintese` | Sai do mensageiro e abre os quadros de sistematização. | o-eco-no-grupo |
| GET | `/o-eco-no-grupo/turmas` | Turmas para o seletor do painel. | o-eco-no-grupo |
| DELETE | `/o-eco-no-grupo/turmas/«turmaId»` | Zerar a turma para uma segunda aplicação. | o-eco-no-grupo |
| POST | `/o-eco-no-grupo/turmas/«turmaId»/gate` | Abre a Aula 2, congela o debate ou libera a reflexão. | o-eco-no-grupo |
| GET | `/o-eco-no-grupo/turmas/«turmaId»/painel` | O que a turma está fazendo na missão, ao vivo. | o-eco-no-grupo |
| POST | `/o-eco-no-grupo/turmas/«turmaId»/preparar-midia` | Gera as vozes e as fotos da missão (preparo da aula). | o-eco-no-grupo |
| POST | `/observabilidade/erros-cliente` | Registra um erro não capturado do navegador (experiência ou hub). | observabilidade |
| POST | `/observabilidade/publico/erros-cliente` | Registra um erro de navegador ocorrido ANTES do login (landing, tela de login, troca de senha). | observabilidade |
| POST | `/observabilidade/publico/vitals` | Recebe um Web Vital medido antes do login. | observabilidade |
| POST | `/observabilidade/v1/traces` | Ingestão OTLP/JSON dos spans que a SDK exporta do navegador. | observabilidade |
| POST | `/observabilidade/vitals` | Recebe um Web Vital (LCP, INP, CLS, TTFB) do hub ou de uma experiência. | observabilidade |
| POST | `/perfis-recebidos` | Recebe um documento de outra rede. | perfis-recebidos |
| GET | `/perfis-recebidos/«id»` | O documento recebido inteiro, como veio. | perfis-recebidos |
| DELETE | `/perfis-recebidos/«id»` | Apaga um perfil recebido. | perfis-recebidos |
| POST | `/perfis/importar` | Ponte externa do Ato 1 — compatibilidade. | perfis |
| GET | `/periodos-letivos` | O calendário do contrato, com quantas turmas cada período tem. | periodos-letivos |
| POST | `/periodos-letivos` | Cria um período letivo — a primeira etapa da virada do ano. | periodos-letivos |
| GET | `/planejamento/configuracoes` | As regências configuradas por ESTE professor. | planejamento |
| POST | `/planejamento/configuracoes` | Cria ou atualiza a regência de um componente × ano. | planejamento |
| DELETE | `/planejamento/configuracoes/«id»` | Apaga o planejamento inteiro daquele componente × ano. | planejamento |
| GET | `/planejamento/configuracoes/«id»/calendario` | Os períodos de avaliação e as semanas de planejamento do ano. | planejamento |
| POST | `/planejamento/configuracoes/«id»/plano-anual` | Cria o plano anual de uma regência. | planejamento |
| GET | `/planejamento/curriculo/componentes` | Os componentes curriculares que a rede oferta naquele ano. | planejamento |
| GET | `/planejamento/curriculo/habilidades` | As habilidades da BNCC daquele componente naquele ano, agrupadas. | planejamento |
| GET | `/planejamento/periodos/«id»` | O plano de uma semana, aula a aula. | planejamento |
| PUT | `/planejamento/periodos/«id»/aulas` | Salva as aulas editadas — e o registro do que foi cumprido. | planejamento |
| GET | `/planejamento/planos-anuais` | Os planos anuais DESTE professor. | planejamento |
| GET | `/planejamento/planos-anuais/«id»` | O plano anual com o conteúdo. | planejamento |
| DELETE | `/planejamento/planos-anuais/«id»` | Apaga o plano anual e os planos de período dele. | planejamento |
| PUT | `/planejamento/planos-anuais/«id»/conteudo` | Salva o plano anual editado pelo professor. | planejamento |
| PUT | `/planejamento/planos-anuais/«id»/distribuicao` | Salva a distribuição de habilidades pelos períodos. | planejamento |
| POST | `/planejamento/planos-anuais/«id»/gerar` | Dispara a geração do plano anual. | planejamento |
| GET | `/planejamento/planos-anuais/«id»/periodos` | As semanas JÁ PLANEJADAS, com as aulas — para exportar várias juntas. | planejamento |
| POST | `/planejamento/planos-anuais/«id»/periodos/«ordem»/gerar` | Gera o plano aula a aula de uma semana. | planejamento |
| GET | `/planos` | Os planos DESTE professor. | planos |
| POST | `/planos` | Pede a geração de um plano de aula. | planos |
| GET | `/planos/referencias` | O inventário das referências curriculares do contrato. | planos |
| POST | `/planos/referencias` | Importa (ou sobrescreve) uma referência curricular. | planos |
| GET | `/planos/referencias/disponiveis` | Disciplinas e séries que têm material curricular importado. | planos |
| DELETE | `/planos/referencias/«id»` | Remove uma referência do catálogo. | planos |
| GET | `/planos/«id»` | Um plano, com o conteúdo quando estiver pronto. | planos |
| PATCH | `/planos/«id»` | Renomeia o plano. | planos |
| DELETE | `/planos/«id»` | Exclui o plano. | planos |
| PUT | `/planos/«id»/conteudo` | Salva o conteúdo editado pelo professor. | planos |
| POST | `/planos/«id»/restaurar` | Descarta a edição e volta ao plano gerado. | planos |
| PATCH | `/posts/«id»` | Edita o post: legenda, hashtags, comentários e aprovação. | posts |
| DELETE | `/posts/«id»` | Exclui um post da grade. | posts |
| GET | `/posts/«id»/comentarios` | Os comentários de um post do feed. | posts |
| POST | `/posts/«id»/regenerar` | Regenera o texto ou a imagem de um post. | posts |
| GET | `/progresso/«expId»` | O progresso do estudante autenticado nesta experiência. | progresso |
| POST | `/progresso/«expId»` | Salva o progresso da experiência. | progresso |
| POST | `/progresso/«expId»/concluir` | Registra a conclusão da experiência. | progresso |
| POST | `/rastro-boato/auditoria` | Registra a abertura da janela "Dados da mensagem". | rastro-boato |
| POST | `/rastro-boato/decisao` | A intervenção no grupo — irrevogável (latch). | rastro-boato |
| POST | `/rastro-boato/entrar` | Sai da tela de contexto e abre a lista de conversas. | rastro-boato |
| GET | `/rastro-boato/gate` | Em que etapa a turma está (polling de ~5s). | rastro-boato |
| POST | `/rastro-boato/modelagem` | O modelo do ciclo da desinformação — 4 blocos, sem nota. | rastro-boato |
| GET | `/rastro-boato/professor/material` | As três intervenções com o gabarito e o ciclo ordenado, para o guia da aula. | rastro-boato |
| POST | `/rastro-boato/reflexao` | O "Meu percurso" — encerra a missão (latch). | rastro-boato |
| GET | `/rastro-boato/sessao` | O estado da missão, as 4 conversas e os metadados de cada mensagem. | rastro-boato |
| GET | `/rastro-boato/turmas` | Turmas para o seletor do painel. | rastro-boato |
| DELETE | `/rastro-boato/turmas/«turmaId»` | Zerar a turma — a segunda aplicação. | rastro-boato |
| POST | `/rastro-boato/turmas/«turmaId»/gate` | Abre a Aula 2, ou pausa a simulação de volta na Aula 1. | rastro-boato |
| GET | `/rastro-boato/turmas/«turmaId»/painel` | O que a turma está fazendo na missão, ao vivo. | rastro-boato |
| GET | `/readyz` | As dependências estão prontas (banco). | readyz |
| GET | `/recursos/auditoria` | Quem ligou ou desligou o quê, e quando. | recursos |
| GET | `/recursos/efetivos` | O que está disponível para a escola do token. | recursos |
| POST | `/recursos/experiencias/«expId»/ativar` | Ativa uma versão para o CONTRATO (o rollback). | recursos |
| PUT | `/recursos/experiencias/«expId»/versao` | Fixa (ou solta) a versão de uma experiência num escopo. | recursos |
| GET | `/recursos/experiencias/«expId»/versoes` | As versões publicadas de uma experiência. | recursos |
| GET | `/recursos/painel` | O painel: produtos, experiências e o que vale em cada escopo. | recursos |
| GET | `/recursos/quotas-de-ia` | O teto diário de IA de cada perfil. | recursos |
| PUT | `/recursos/quotas-de-ia/«perfil»` | Define o teto diário de IA de um perfil. | recursos |
| PUT | `/recursos/«recursoId»` | Liga ou desliga um recurso num escopo. | recursos |
| DELETE | `/recursos/«recursoId»` | Remove a exceção de um escopo (volta a herdar). | recursos |
| GET | `/rostering/contas-de-assento` | As contas sem matrícula da rede — as que podem ser de assento. | rostering |
| POST | `/rostering/importar` | Importa a planilha de pessoas. | rostering |
| GET | `/rostering/modelos/exemplo.csv` | O mesmo modelo, preenchido com um exemplo. | rostering |
| GET | `/rostering/modelos/oneroster/«arquivo»` | O modelo em branco de um arquivo do OneRoster 1.2. | rostering |
| GET | `/rostering/modelos/oneroster/«arquivo»/exemplo` | O mesmo arquivo do OneRoster, preenchido com um exemplo. | rostering |
| GET | `/rostering/modelos/usuarios.csv` | O modelo em branco da planilha de pessoas. | rostering |
| POST | `/rostering/oneroster/«arquivo»` | Binding CSV do OneRoster 1.2 — UM arquivo por chamada. | rostering |
| POST | `/runs` | Cria a run do estudante na atividade ativa. | runs |
| GET | `/runs/boot` | O bootstrap do aparelho — o que a tela de entrada precisa saber. | runs |
| GET | `/runs/«id»/busca` | Busca no acervo da atividade. | runs |
| POST | `/runs/«id»/conclusao` | A escolha de um lado no fim da missão. | runs |
| GET | `/runs/«id»/dossie` | O dossiê da sessão — o relatório da revelação. | runs |
| POST | `/runs/«id»/entrar` | O estudante entra no aparelho e vai ao feed. | runs |
| POST | `/runs/«id»/eventos` | Lote de eventos do cliente — o canal OPERACIONAL. | runs |
| GET | `/runs/«id»/fase` | A tela que o estudante deve estar vendo agora. | runs |
| GET | `/runs/«id»/feed` | O próximo bloco do feed. | runs |
| POST | `/runs/«id»/finish` | Congela a run e computa o dossiê. | runs |
| GET | `/runs/«id»/perdidos` | O que o estudante PERDEU — posts do lado oposto que nunca foram servidos. | runs |
| POST | `/runs/«id»/reacoes` | Reações das personas ao que o estudante escreveu. | runs |
| POST | `/runs/«id»/reflexao` | O fechamento escrito da atividade. | runs |
| GET | `/runs/«id»/reflexao` | O texto da reflexão que o estudante já escreveu. | runs |
| POST | `/runs/«id»/reset` | Reabre a run de um estudante, sorteando a largada de novo. | runs |
| GET | `/runs/«id»/salvos` | A coleção do estudante — o que ele salvou. | runs |
| POST | `/runs/«id»/student-post` | O estudante publica no app, e as personas reagem. | runs |
| GET | `/salas/minhas` | As salas do estudante: as turmas dele e a grade de cada uma. | salas |
| GET | `/salas/turma/«turmaId»` | A sala: a turma, a grade de missões e quem liberou cada uma. | salas |
| PUT | `/salas/turma/«turmaId»/missoes/«expId»` | Libera ou encerra uma missão nesta turma. | salas |
| POST | `/telemetry/batch` | Recebe um lote do canal ANALÍTICO da SDK. | telemetry |
| POST | `/telemetry/beacon` | Último lote de uma sessão que está fechando. | telemetry |
| POST | `/telemetry/ingest` | Consome a push subscription do Pub/Sub e grava os eventos. | telemetry |
| GET | `/turmas` | As turmas da escola. | turmas |
| POST | `/turmas` | Cria uma turma. | turmas |
| GET | `/turmas/minhas` | As turmas DO PROFESSOR — as que ele tem matrícula, e só elas. | turmas |
| PATCH | `/turmas/«id»` | Edita nome, série ou turno da turma. | turmas |
| GET | `/turmas/«id»` | Os matriculados da turma — a lista nominal. | turmas |
| POST | `/turmas/«id»/matriculas` | Matricula uma pessoa na turma. | turmas |
| GET | `/unoogpt/agregado/escola` | O agregado da escola — uma linha por turma. | unoogpt |
| POST | `/unoogpt/alocacao` | Manda uma equipe para um bairro. | unoogpt |
| PUT | `/unoogpt/conjuntos` | Carrega fontes no modelo pelo painel. | unoogpt |
| POST | `/unoogpt/contrafactual` | "E se eu tivesse mandado para…" — calculado e descartado. | unoogpt |
| POST | `/unoogpt/passo` | Move a sessão para outro passo da missão. | unoogpt |
| POST | `/unoogpt/pergunta` | O turno do Cientista — a rota que fala com o modelo. | unoogpt |
| GET | `/unoogpt/professor/estudantes/«estudanteId»` | A linha de UMA criança: leitura em graus e a Transcrição. | unoogpt |
| GET | `/unoogpt/professor/fontes` | As 8 fontes do cenário com o viés de cada uma, para o guia da aula. | unoogpt |
| GET | `/unoogpt/professor/turmas` | Turmas para o seletor de resultados do unooGPT. | unoogpt |
| GET | `/unoogpt/professor/turmas/«turmaId»` | A folha da turma: relógio, retrato de conduta e uma linha por estudante. | unoogpt |
| DELETE | `/unoogpt/professor/turmas/«turmaId»` | Zera a turma: apaga as partidas E o relógio. | unoogpt |
| POST | `/unoogpt/professor/turmas/«turmaId»/relogio` | Dá a largada, soma tempo, encerra, troca o modo ou redefine. | unoogpt |
| POST | `/unoogpt/reiniciar` | Recomeça — abre uma tentativa NOVA. | unoogpt |
| GET | `/unoogpt/relogio` | O relógio da turma — polling de ~5s. | unoogpt |
| GET | `/unoogpt/resultado` | O resultado da tentativa, com a faixa e o que ele nunca consultou. | unoogpt |
| GET | `/unoogpt/sessao` | O bootstrap da Missão Tempestade. Cria a sessão na primeira visita. | unoogpt |
| POST | `/unoogpt/simular` | Enfrenta a tempestade e fecha a tentativa. | unoogpt |
| POST | `/unootube/credibilidade` | Fecha a missão trocando inscritos por credibilidade. | unootube |
| POST | `/unootube/curtidos/«videoId»` | Curte (ou descurte) um vídeo. | unootube |
| GET | `/unootube/professor/videos` | Os 21 vídeos do UnooTube com o gabarito, para o guia da aula. | unootube |
| GET | `/unootube/ranking` | O ranking — a virada da missão. | unootube |
| POST | `/unootube/reiniciar` | Começa a missão do zero. | unootube |
| POST | `/unootube/salvos` | Salva um vídeo na playlist. | unootube |
| POST | `/unootube/salvos/«videoId»/remover` | Tira um vídeo da playlist. | unootube |
| GET | `/unootube/sessao` | O estado da missão e o catálogo de vídeos. | unootube |
| GET | `/unootube/turmas` | Turmas para o seletor de resultados. | unootube |
| GET | `/unootube/turmas/«turmaId»/resultados` | O que a turma fez na missão do UnooTube. | unootube |
| GET | `/usuarios` | As pessoas da escola, paginadas. | usuarios |
| POST | `/usuarios` | Cadastra UMA pessoa da escola (estudante, professor ou gestor). | usuarios |
| POST | `/usuarios/importar-csv` | Compatibilidade: delega para `POST /rostering/importar`. | usuarios |
| POST | `/usuarios/sem-escola` | Cadastra um papel SEM escola (`gestor_contrato` ou `gestor_regional`). | usuarios |
| PATCH | `/usuarios/«id»` | Edita nome, CPF, e-mail, papel ou situação da pessoa. | usuarios |
| POST | `/usuarios/«id»/reset-senha` | Gera uma senha temporária e a devolve UMA vez. | usuarios |
| GET | `/vila/agregado/turmas` | Turmas para o seletor da Vila. | vila |
| GET | `/vila/agregado/turmas/«turmaId»` | O agregado da turma — contagens, nunca por criança. | vila |
| GET | `/vila/professor/cartoes` | TODOS os cartões, das três bolhas, COM o gabarito. | vila |
| GET | `/vila/professor/estudantes/«estudanteId»` | O relatório da última partida concluída de um estudante. | vila |
| GET | `/vila/professor/turmas/«turmaId»` | Uma linha por estudante da turma. | vila |
| DELETE | `/vila/professor/turmas/«turmaId»/dados` | Zera os dados da Vila desta turma. | vila |
| POST | `/vila/sessoes` | Abre a partida e entrega os cartões DESTA criança. | vila |
| POST | `/vila/sessoes/«id»/concluir` | Fecha a partida e grava o payload bruto. | vila |
