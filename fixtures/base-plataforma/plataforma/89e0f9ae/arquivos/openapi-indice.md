<!-- CÓPIA de plataforma-unooria@89e0f9ae (2026-10-06) · origem: docs/openapi.json · não edite -->

# `docs/openapi.json` — índice de rotas (método · caminho · resumo · tags)

315 caminhos. O contrato completo (Zod → OpenAPI) está no repositório; aqui só o mapa.

| Método | Caminho | Resumo | Tags |
|---|---|---|---|
| POST | `/a-selecao/concluir` | "Missão concluída!" — idempotente. | a-selecao |
| POST | `/a-selecao/decisao` | "Confirmar publicação" — os 3 posts e a legenda nos Stories (latch). | a-selecao |
| GET | `/a-selecao/gate` | Em que etapa a turma está (polling de ~5 s). | a-selecao |
| GET | `/a-selecao/mural` | O Mural da Turma: a própria tríade ao lado da do par. | a-selecao |
| POST | `/a-selecao/passo` | Registra o passo que a própria criança deu: feed, salvos ou reflexão. | a-selecao |
| GET | `/a-selecao/professor/material` | O banco curado com o gabarito, o roteiro da Etapa 4 e os colegas virtuais. | a-selecao |
| POST | `/a-selecao/reflexao` | A reflexão individual da Etapa 6 (latch) — leva às enquetes. | a-selecao |
| GET | `/a-selecao/sessao` | O estado da missão e os 12 posts do feed, sem o gabarito. | a-selecao |
| GET | `/a-selecao/turmas` | Turmas para o seletor do painel. | a-selecao |
| GET | `/a-selecao/turmas/{turmaId}/coberturas` | As atividades da turma: a em andamento, COM o gabarito, e a lista de todas. | a-selecao |
| GET | `/a-selecao/turmas/{turmaId}/coberturas/{coberturaId}` | UMA atividade, inteira e COM o gabarito — em andamento ou pronta. | a-selecao |
| POST | `/a-selecao/turmas/{turmaId}/coberturas/{coberturaId}/aprovar-imagens` | A segunda fase da aprovação: o professor viu as imagens dos posts e as aprova (ADR-146). | a-selecao |
| POST | `/a-selecao/turmas/{turmaId}/coberturas/{coberturaId}/em-andamento` | "Usar esta atividade agora" — a professora escolhe o que a turma faz (ADR-130). | a-selecao |
| POST | `/a-selecao/turmas/{turmaId}/coberturas/{coberturaId}/imagens/{postId}/regerar` | "Gerar outra imagem": uma imagem nova para UM post, enquanto as imagens estão em validação (ADR-146). | a-selecao |
| POST | `/a-selecao/turmas/{turmaId}/gate` | O botão único da aula: "Liberar Mural", "Revelar fichas", "Liberar conclusão". | a-selecao |
| POST | `/a-selecao/turmas/{turmaId}/gerar-conteudo` | Gera um RASCUNHO dos 12 posts com IA, sobre o tema da professora (pré-aula). | a-selecao |
| POST | `/a-selecao/turmas/{turmaId}/gerar-midia` | Gera as próximas imagens dos posts de uma atividade — incremental. | a-selecao |
| POST | `/a-selecao/turmas/{turmaId}/gerar-podcast` | Sintetiza o próximo trecho do podcast e, com os cinco prontos, emenda o episódio — incremental. | a-selecao |
| POST | `/a-selecao/turmas/{turmaId}/homologar` | "Criar atividade" — a curadoria humana (ADR-66/67). | a-selecao |
| GET | `/a-selecao/turmas/{turmaId}/painel` | O painel da aula: o botão da próxima etapa e quem publicou, POR COMPUTADOR. | a-selecao |
| GET | `/a-selecao/turmas/{turmaId}/podcast` | O podcast de recapitulação de uma atividade: o roteiro e o estado do áudio. | a-selecao |
| POST | `/a-selecao/turmas/{turmaId}/zerar` | "Zerar a turma" — abre a próxima rodada, sem apagar nada. | a-selecao |
| GET | `/agente-professor/conversas` | As conversas do professor na escola ativa, a mais recente primeiro. | agente-professor |
| POST | `/agente-professor/conversas` | Abre uma conversa nova com o agente de IA do professor. | agente-professor |
| GET | `/agente-professor/conversas/{id}` | Uma conversa: título e mensagens, montados da sessão no agente. | agente-professor |
| DELETE | `/agente-professor/conversas/{id}` | Apaga a conversa: a sessão no agente e a linha da posse. | agente-professor |
| POST | `/agente-professor/conversas/{id}/mensagens` | Envia uma mensagem e recebe a resposta do agente em SSE. | agente-professor |
| POST | `/ai/gerar` | Conversa com o tutor de IA da experiência. | ai |
| POST | `/ajuda/llm/chat/completions` | Um turno do atendente da Ajuda, no formato `chat/completions` do OpenAI. | ajuda |
| GET | `/ajuda/llm/models` | Lista o modelo da Ajuda, no formato OpenAI (o vendor consulta ao abrir a sessão). | ajuda |
| POST | `/ajuda/sessoes` | Abre a Ajuda: reserva os minutos e pede a sala de vídeo do atendente. | ajuda |
| POST | `/ajuda/sessoes/{id}/encerrar` | Encerra a sessão de vídeo da Ajuda. | ajuda |
| GET | `/analise/atividades/{id}` | O detalhe de uma atividade, com a eficácia da escrita por perfil. | analise |
| GET | `/analise/csv` | Export do nível de produto — por run ou por evento. | analise |
| GET | `/analise/resumo` | Uma linha por atividade — o nível de produto. | analise |
| GET | `/atividades` | As atividades DESTE professor. | atividades |
| POST | `/atividades` | Cria a atividade em rascunho, com os defaults do motor. | atividades |
| GET | `/atividades/{id}` | O detalhe de uma atividade. | atividades |
| DELETE | `/atividades/{id}` | Exclui a atividade. | atividades |
| GET | `/atividades/{id}/analise` | A análise pedagógica da turma — identificada. | atividades |
| GET | `/atividades/{id}/analise/csv` | A mesma análise da turma, em planilha. | atividades |
| PATCH | `/atividades/{id}/antagonismo` | O professor aprova (ou reescreve) os dois lados e os neutros. | atividades |
| POST | `/atividades/{id}/ativar` | Ativa a atividade para os estudantes entrarem. | atividades |
| POST | `/atividades/{id}/destilar` | Destila a pergunta-chave e os dois lados a partir do recorte. | atividades |
| GET | `/atividades/{id}/distribuicao` | Onde cada estudante vai cair — antes de começar. | atividades |
| GET | `/atividades/{id}/estudantes/{runId}` | Tudo o que UM estudante fez, durante a atividade. | atividades |
| POST | `/atividades/{id}/etapa` | O RELÓGIO DA AULA: move a turma inteira de momento. | atividades |
| GET | `/atividades/{id}/etapa` | Etapa atual e quantos estudantes em cada tela. | atividades |
| GET | `/atividades/{id}/geracao/progresso` | O progresso da geração — o alvo do polling da tela. | atividades |
| POST | `/atividades/{id}/gerar` | Enfileira a geração dos posts. | atividades |
| PATCH | `/atividades/{id}/ia` | Liga ou desliga a IA ao vivo durante a aula. | atividades |
| POST | `/atividades/{id}/limpar` | Apaga as sessões dos estudantes, mantendo a atividade e os posts. | atividades |
| GET | `/atividades/{id}/monitor` | O painel da turma ao vivo. | atividades |
| POST | `/atividades/{id}/perfis` | Importa perfis à mão — o fallback do professor. | atividades |
| GET | `/atividades/{id}/perfis` | O estado do perfil de cada estudante, para conferência. | atividades |
| POST | `/atividades/{id}/perfis/da-vila` | Traz os perfis da Vila do Lume para a largada do Instanooria. | atividades |
| GET | `/atividades/{id}/posts` | A grade de revisão do professor, paginada e filtrável. | atividades |
| POST | `/atividades/{id}/redistribuir` | Rebalanceia a turma quando ela cai quase toda num lado. | atividades |
| POST | `/auth/login` | Autentica uma credencial da rede. | auth |
| POST | `/auth/trocar-senha` | Troca a senha: a provisória do primeiro acesso, ou a de quem quer trocar. | auth |
| POST | `/bemestar/checkins/{id}/respostas` | Responde as três frases do dia. | bemestar |
| DELETE | `/bemestar/dados` | Apaga TUDO do bem-estar do professor logado. | bemestar |
| GET | `/bemestar/historico` | Os ciclos concluídos e as anotações — só do próprio professor. | bemestar |
| GET | `/bemestar/hoje` | O check-in de hoje — o já respondido, o pendente, ou um novo. | bemestar |
| GET | `/bemestar/resumo` | Estado leve do check-in, para o card do hub. | bemestar |
| GET | `/equipes/minha` | A equipe do estudante nesta missão: o nome dela e o primeiro nome dos colegas. | equipes |
| GET | `/equipes/turma/{turmaId}/missao/{expId}/atividade/{atividadeId}` | As equipes de uma atividade nesta turma: a montagem, as equipes e quem está sem equipe. | equipes |
| PUT | `/equipes/turma/{turmaId}/missao/{expId}/atividade/{atividadeId}` | Grava a montagem inteira das equipes desta atividade, com concorrência otimista. | equipes |
| DELETE | `/equipes/turma/{turmaId}/missao/{expId}/atividade/{atividadeId}` | Desfaz as equipes desta atividade na turma. | equipes |
| POST | `/equipes/turma/{turmaId}/missao/{expId}/atividade/{atividadeId}/sugestao` | Uma proposta de equipes (sorteio ou N equipes vazias) — nunca grava. O `individual` não tem proposta. | equipes |
| GET | `/equipes/turma/{turmaId}/missao/{expId}/atividade/{atividadeId}/ultima` | As equipes da atividade anterior desta turma, reprojetadas sobre a turma de hoje. | equipes |
| GET | `/escolas` | Todas as escolas do contrato, com contagem. | escolas |
| POST | `/escolas` | Cria uma escola. | escolas |
| POST | `/escolas/lotacoes-em-lote` | Lota uma pessoa em MUITAS escolas de uma vez. | escolas |
| GET | `/escolas/minhas` | As escolas de QUEM ESTÁ PEDINDO. | escolas |
| GET | `/escolas/minhas/relatorio` | Relatório da diretoria: consolidado e por escola. | escolas |
| GET | `/escolas/minhas/resumo` | O panorama de quem tem muitas escolas. | escolas |
| GET | `/escolas/profissionais` | Busca professor e coordenação na REDE inteira. | escolas |
| PATCH | `/escolas/{id}` | Edita os dados da escola. | escolas |
| DELETE | `/escolas/{id}` | Exclui uma regional. | escolas |
| POST | `/escolas/{id}/lotacoes` | Lota alguém nesta escola. | escolas |
| GET | `/escolas/{id}/pessoas` | Quem está lotado nesta escola. | escolas |
| GET | `/estudantes/{id}/historico` | O histórico do estudante ATRAVESSANDO escolas. | estudantes |
| GET | `/estudantes/{id}/perfil-portatil` | Monta o documento SEM assinatura, para o hub assinar. | estudantes |
| GET | `/estudantes/{id}/perfis-recebidos` | Os documentos que esta escola já recebeu sobre esta criança. | estudantes |
| POST | `/estudantes/{id}/transferir` | Transfere o estudante entre escolas da rede. | estudantes |
| GET | `/evidencias/escola/consolidado` | O painel de habilidades da escola: as turmas do ano letivo vigente, por série. | evidencias |
| GET | `/evidencias/estudante/{estudanteId}` | O perfil de evidência de um estudante: cada missão, cada atividade, o nível de cada habilidade. | evidencias |
| GET | `/evidencias/rede/consolidado` | O painel de habilidades da rede: cada escola, cada série, a soma das turmas. | evidencias |
| GET | `/evidencias/turma/{turmaId}/consolidado` | O painel de habilidades da turma: cada missão, cada habilidade da BNCC, quantas crianças em cada nível. | evidencias |
| GET | `/evidencias/turma/{turmaId}/missao/{expId}/atividade/{atividadeId}` | O painel da evidência de uma atividade: cada estudante, cada rodada, cada habilidade da BNCC. | evidencias |
| PATCH | `/evidencias/turma/{turmaId}/missao/{expId}/atividade/{atividadeId}/rodadas/{rodada}/ajustes` | Ajusta a evidência de um ou vários estudantes numa rodada. | evidencias |
| POST | `/evidencias/turma/{turmaId}/missao/{expId}/atividade/{atividadeId}/rodadas/{rodada}/confirmar` | Confirma para a turma as cópias da projeção desta rodada. | evidencias |
| GET | `/evidencias/{expId}/perguntas/{perguntaId}` | Uma pergunta de múltipla escolha da ficha da missão — sem o gabarito. | evidencias |
| POST | `/evidencias/{expId}/perguntas/{perguntaId}/resposta` | A resposta do estudante a uma pergunta — a api corrige, e só devolve o recibo. | evidencias |
| GET | `/experiencias` | O catálogo de experiências do contrato. | experiencias |
| GET | `/experiencias/{expId}` | Uma linha do manifesto. | experiencias |
| PUT | `/experiencias/{expId}` | Publica ou faz rollback de uma versão. | experiencias |
| POST | `/foto-conta/feed` | Etapa 2: registra a exploração do feed e abre a decisão. | foto-conta |
| GET | `/foto-conta/galeria` | O mural da turma (pós-publicação): as fotos dos colegas, chegando. | foto-conta |
| GET | `/foto-conta/latch` | O polling do latch (3s): a turma já foi liberada? (ADR-94) | foto-conta |
| POST | `/foto-conta/marca` | Etapa 1: grava a marca escolhida e abre o mural. | foto-conta |
| POST | `/foto-conta/publicar` | Etapa 3 (o PICO): publica o par foto+legenda e devolve o eco dos colegas. | foto-conta |
| POST | `/foto-conta/reflexao` | Etapa 6: a síntese metacognitiva — o servidor decide, sem nota. | foto-conta |
| POST | `/foto-conta/roda` | Etapa 4 → 5: o eco terminou; a run entra no latch da Roda de Conversa. | foto-conta |
| GET | `/foto-conta/sessao` | O boot da missão: estado da run + o pacote da aula, sem a matriz do Aha. | foto-conta |
| GET | `/foto-conta/turmas` | As turmas de quem pergunta, para o seletor do painel. | foto-conta |
| GET | `/foto-conta/turmas/{turmaId}` | O dashboard ao vivo: distribuição A/B, latch e a lista de hesitação. | foto-conta |
| POST | `/foto-conta/turmas/{turmaId}/aprovar-pacote` | Aprova o pacote conferido no preview — o `cfg_turma_ready` da spec. | foto-conta |
| POST | `/foto-conta/turmas/{turmaId}/configurar` | Grava tema e nível de leitura da turma (o passo anterior à geração). | foto-conta |
| POST | `/foto-conta/turmas/{turmaId}/destravar-latch` | LIBERAR REFLEXÃO FINAL: destrava os tablets da turma inteira. | foto-conta |
| POST | `/foto-conta/turmas/{turmaId}/gerar-conteudo` | Gera o pacote da aula com IA (Vertex), para o preview do professor. | foto-conta |
| GET | `/foto-conta/turmas/{turmaId}/projecao` | A projeção da lousa (E5): o par lado a lado, os rótulos e as 3 perguntas. | foto-conta |
| POST | `/foto-conta/turmas/{turmaId}/reset` | Zerar e Reiniciar Turma: arquiva a tentativa e rearma o latch. | foto-conta |
| GET | `/healthz` | O processo está vivo. | healthz |
| POST | `/jornal-escola/chave` | Uma tentativa da Chave do Editor: três blocos, em qualquer ordem. | jornal-escola |
| GET | `/jornal-escola/comparativo` | O antes e o depois: as duas edições, com o que cada uma causou. | jornal-escola |
| POST | `/jornal-escola/concluir` | "Concluir Missão" — idempotente. | jornal-escola |
| POST | `/jornal-escola/diagramar` | Diagrama a primeira página com as 3 vagas de agora — a IA só escolhe o layout. | jornal-escola |
| GET | `/jornal-escola/gate` | Em que etapa a turma está (polling de ~5 s). | jornal-escola |
| POST | `/jornal-escola/motivo` | Como a escolha foi feita — a pergunta de depois do latch, uma vez só. | jornal-escola |
| POST | `/jornal-escola/passo` | Registra o passo que a própria criança deu: a mesa, ou o Desafio Final. | jornal-escola |
| POST | `/jornal-escola/pista` | Abre uma pista (fonte, data ou autoria) de uma notícia — o texto vem do servidor. | jornal-escola |
| GET | `/jornal-escola/professor/material` | O banco padrão com o gabarito, os blocos da Chave e o roteiro da mediação. | jornal-escola |
| POST | `/jornal-escola/publicar` | "Distribuir Jornal Agora" — a 1ª edição (latch). | jornal-escola |
| POST | `/jornal-escola/republicar` | "Publicar 2ª Edição Revisada" — a 2ª edição (latch). | jornal-escola |
| GET | `/jornal-escola/resultado` | O que a 1ª edição causou: as verificadas e a reação de um leitor por vaga. | jornal-escola |
| GET | `/jornal-escola/revisao` | A mesa de revisão: o marcador que a Chave pôs em cada vaga da 1ª edição. | jornal-escola |
| GET | `/jornal-escola/sessao` | O estado da missão e as 8 notícias da mesa, sem o gabarito. | jornal-escola |
| GET | `/jornal-escola/turmas` | Turmas para o seletor do painel. | jornal-escola |
| POST | `/jornal-escola/turmas/{turmaId}/gate` | O botão único da aula: "Liberar resultado", depois "Liberar revisão". | jornal-escola |
| POST | `/jornal-escola/turmas/{turmaId}/gerar-conteudo` | Gera um RASCUNHO das 8 notícias com IA, sobre o tema do professor (pré-aula). | jornal-escola |
| POST | `/jornal-escola/turmas/{turmaId}/gerar-midia` | Gera as próximas imagens das notícias de uma atividade — incremental. | jornal-escola |
| POST | `/jornal-escola/turmas/{turmaId}/homologar` | "Criar atividade" — a curadoria humana (ADR-66/67). | jornal-escola |
| GET | `/jornal-escola/turmas/{turmaId}/pacotes` | As atividades da turma: o pacote em andamento, COM o gabarito, e a lista de todos. | jornal-escola |
| GET | `/jornal-escola/turmas/{turmaId}/pacotes/{pacoteId}` | UMA atividade, inteira e COM o gabarito — em andamento ou pronta. | jornal-escola |
| POST | `/jornal-escola/turmas/{turmaId}/pacotes/{pacoteId}/aprovar-imagens` | "Aprovar imagens" — o professor viu as imagens das notícias e dá o OK (ADR-147). | jornal-escola |
| POST | `/jornal-escola/turmas/{turmaId}/pacotes/{pacoteId}/em-andamento` | "Usar esta atividade agora" — o professor escolhe o que a turma faz (ADR-130). | jornal-escola |
| POST | `/jornal-escola/turmas/{turmaId}/pacotes/{pacoteId}/imagens/{noticiaId}/regerar` | "Gerar outra" — uma imagem nova para UMA notícia (ADR-147). | jornal-escola |
| GET | `/jornal-escola/turmas/{turmaId}/painel` | O painel da aula: o botão da próxima etapa e o progresso, POR COMPUTADOR. | jornal-escola |
| POST | `/jornal-escola/turmas/{turmaId}/regenerar-noticia` | Regenera UMA notícia do rascunho, mantendo o id, o meio e o papel no gabarito. | jornal-escola |
| POST | `/jornal-escola/turmas/{turmaId}/zerar` | "Zerar a turma" — abre a próxima rodada, sem apagar nada. | jornal-escola |
| POST | `/juri-estadual/cadeia` | Uma tentativa de montar a cadeia: Interações → Dados → Algoritmo → Bolha. | juri-estadual |
| POST | `/juri-estadual/cartoes` | O caso Mariana: um cartão de mecanismo e um de atitude. | juri-estadual |
| POST | `/juri-estadual/concluir` | O crachá homologado — conclui a missão, idempotente. | juri-estadual |
| POST | `/juri-estadual/feed/eventos` | O que a tela mediu (curtidas e permanências) e, se pedido, o próximo post. | juri-estadual |
| GET | `/juri-estadual/galeria` | A Galeria Oculta: os 16 estandes, os que não chegaram ao feed primeiro, e a taxa REAL. | juri-estadual |
| POST | `/juri-estadual/galeria/acoes` | Registra o que a criança fez na galeria: abriu um estande ou buscou. | juri-estadual |
| GET | `/juri-estadual/gate` | Em que etapa a turma está (polling de ~3 s, na espera da plenária). | juri-estadual |
| POST | `/juri-estadual/pacotes` | Uma tentativa de remontar a curtida: os quatro pacotes na ordem dos números. | juri-estadual |
| POST | `/juri-estadual/passo` | "Acessar o feed da mostra" — da credencial para o feed, com a abertura. | juri-estadual |
| GET | `/juri-estadual/professor/material` | O esqueleto da missão com o gabarito, a plenária e a regra do feed. | juri-estadual |
| POST | `/juri-estadual/revisao` | Manter ou trocar o voto, depois da galeria (latch). | juri-estadual |
| GET | `/juri-estadual/sessao` | O estado da missão: o passo, o feed servido até aqui, o voto e os blocos do fim. | juri-estadual |
| GET | `/juri-estadual/turmas` | Turmas para o seletor do painel. | juri-estadual |
| POST | `/juri-estadual/turmas/{turmaId}/gate` | "Liberar a Galeria Oculta" — o botão único da aula. | juri-estadual |
| POST | `/juri-estadual/turmas/{turmaId}/gerar-conteudo` | Gera um RASCUNHO da mostra com IA: 4 áreas e 16 projetos sobre o tema do professor. | juri-estadual |
| POST | `/juri-estadual/turmas/{turmaId}/gerar-midia` | Gera as próximas imagens dos estandes de uma atividade — incremental. | juri-estadual |
| POST | `/juri-estadual/turmas/{turmaId}/homologar` | "Criar atividade" — a curadoria humana (ADR-66/67). | juri-estadual |
| GET | `/juri-estadual/turmas/{turmaId}/pacotes` | As atividades da turma: a mostra em andamento, inteira, e a lista de todas. | juri-estadual |
| GET | `/juri-estadual/turmas/{turmaId}/pacotes/{pacoteId}` | UMA atividade, inteira — em andamento ou pronta. | juri-estadual |
| POST | `/juri-estadual/turmas/{turmaId}/pacotes/{pacoteId}/em-andamento` | "Usar esta atividade agora" — o professor escolhe o que a turma faz (ADR-130). | juri-estadual |
| GET | `/juri-estadual/turmas/{turmaId}/painel` | O painel da aula: o botão da galeria, o progresso POR COMPUTADOR e a lousa do pico. | juri-estadual |
| POST | `/juri-estadual/turmas/{turmaId}/regenerar-projeto` | Regenera UM projeto do rascunho, mantendo o id e a área. | juri-estadual |
| POST | `/juri-estadual/turmas/{turmaId}/zerar` | "Zerar a turma" — abre a próxima rodada, sem apagar nada. | juri-estadual |
| POST | `/juri-estadual/voto` | A cédula lacrada — o voto e a convicção (latch). | juri-estadual |
| DELETE | `/lotacoes/{id}` | Encerra o vínculo da pessoa com a escola. | lotacoes |
| POST | `/manifesto-ia/abrir-conversa` | Sai do briefing de Amara e abre o chat do EduPredict IA. | manifesto-ia |
| POST | `/manifesto-ia/clausula` | Fixa a salvaguarda prioritária — irrevogável (latch). | manifesto-ia |
| POST | `/manifesto-ia/concluir` | Finaliza o percurso e concede o selo — latch definitivo. | manifesto-ia |
| POST | `/manifesto-ia/disparar` | Envia um questionamento e recebe a defesa da máquina. | manifesto-ia |
| GET | `/manifesto-ia/gate` | Em que etapa a turma está — o polling de 5s do Checkpoint A. | manifesto-ia |
| POST | `/manifesto-ia/percurso` | O "Meu Percurso" — 2 palavras-chave e o parágrafo autoral (latch). | manifesto-ia |
| GET | `/manifesto-ia/sessao` | O estado da missão, o pacote da turma e a conversa reconstituída. | manifesto-ia |
| GET | `/manifesto-ia/turmas` | Turmas para o seletor do painel. | manifesto-ia |
| DELETE | `/manifesto-ia/turmas/{turmaId}` | Zerar a turma — a segunda aplicação. | manifesto-ia |
| GET | `/manifesto-ia/turmas/{turmaId}/conteudo` | O pacote da turma, com o material de mediação. | manifesto-ia |
| POST | `/manifesto-ia/turmas/{turmaId}/gate` | O botão mestre: Pausar para Debate / Retomar Missão. | manifesto-ia |
| POST | `/manifesto-ia/turmas/{turmaId}/gerar-conteudo` | Gera um RASCUNHO do pacote da turma com IA (pré-aula). | manifesto-ia |
| POST | `/manifesto-ia/turmas/{turmaId}/homologar` | O clique em "Aprovar Conteúdo da Turma" — o portão da exigência 8.2. | manifesto-ia |
| GET | `/manifesto-ia/turmas/{turmaId}/painel` | O painel de mediação ao vivo (Checkpoint A). | manifesto-ia |
| PATCH | `/matriculas/{id}` | Move de turma, ou torna esta a turma de referência. | matriculas |
| DELETE | `/matriculas/{id}` | Encerra a matrícula. | matriculas |
| POST | `/observabilidade/erros-cliente` | Registra um erro não capturado do navegador (experiência ou hub). | observabilidade |
| POST | `/observabilidade/publico/erros-cliente` | Registra um erro de navegador ocorrido ANTES do login (landing, tela de login, troca de senha). | observabilidade |
| POST | `/observabilidade/publico/vitals` | Recebe um Web Vital medido antes do login. | observabilidade |
| POST | `/observabilidade/v1/traces` | Ingestão OTLP/JSON dos spans que a SDK exporta do navegador. | observabilidade |
| POST | `/observabilidade/vitals` | Recebe um Web Vital (LCP, INP, CLS, TTFB) do hub ou de uma experiência. | observabilidade |
| POST | `/perfis-recebidos` | Recebe um documento de outra rede. | perfis-recebidos |
| GET | `/perfis-recebidos/{id}` | O documento recebido inteiro, como veio. | perfis-recebidos |
| DELETE | `/perfis-recebidos/{id}` | Apaga um perfil recebido. | perfis-recebidos |
| POST | `/perfis/importar` | Ponte externa do Ato 1 — compatibilidade. | perfis |
| GET | `/periodos-letivos` | O calendário do contrato, com quantas turmas cada período tem. | periodos-letivos |
| POST | `/periodos-letivos` | Cria um período letivo — a primeira etapa da virada do ano. | periodos-letivos |
| GET | `/planejamento/configuracoes` | As regências configuradas por ESTE professor. | planejamento |
| POST | `/planejamento/configuracoes` | Cria ou atualiza a regência de um componente × ano. | planejamento |
| DELETE | `/planejamento/configuracoes/{id}` | Apaga o planejamento inteiro daquele componente × ano. | planejamento |
| GET | `/planejamento/configuracoes/{id}/calendario` | Os períodos de avaliação e as semanas de planejamento do ano. | planejamento |
| POST | `/planejamento/configuracoes/{id}/plano-anual` | Cria o plano anual de uma regência. | planejamento |
| GET | `/planejamento/curriculo/componentes` | Os componentes curriculares que a rede oferta naquele ano. | planejamento |
| GET | `/planejamento/curriculo/habilidades` | As habilidades da BNCC daquele componente naquele ano, agrupadas. | planejamento |
| GET | `/planejamento/periodos/{id}` | O plano de uma semana, aula a aula. | planejamento |
| PUT | `/planejamento/periodos/{id}/aulas` | Salva as aulas editadas — e o registro do que foi cumprido. | planejamento |
| GET | `/planejamento/planos-anuais` | Os planos anuais DESTE professor. | planejamento |
| GET | `/planejamento/planos-anuais/{id}` | O plano anual com o conteúdo. | planejamento |
| DELETE | `/planejamento/planos-anuais/{id}` | Apaga o plano anual e os planos de período dele. | planejamento |
| PUT | `/planejamento/planos-anuais/{id}/conteudo` | Salva o plano anual editado pelo professor. | planejamento |
| PUT | `/planejamento/planos-anuais/{id}/distribuicao` | Salva a distribuição de habilidades pelos períodos. | planejamento |
| POST | `/planejamento/planos-anuais/{id}/gerar` | Dispara a geração do plano anual. | planejamento |
| GET | `/planejamento/planos-anuais/{id}/periodos` | As semanas JÁ PLANEJADAS, com as aulas — para exportar várias juntas. | planejamento |
| POST | `/planejamento/planos-anuais/{id}/periodos/{ordem}/gerar` | Gera o plano aula a aula de uma semana. | planejamento |
| GET | `/planos` | Os planos DESTE professor. | planos |
| POST | `/planos` | Pede a geração de um plano de aula. | planos |
| GET | `/planos/referencias` | O inventário das referências curriculares do contrato. | planos |
| POST | `/planos/referencias` | Importa (ou sobrescreve) uma referência curricular. | planos |
| GET | `/planos/referencias/disponiveis` | Disciplinas e séries que têm material curricular importado. | planos |
| DELETE | `/planos/referencias/{id}` | Remove uma referência do catálogo. | planos |
| GET | `/planos/{id}` | Um plano, com o conteúdo quando estiver pronto. | planos |
| PATCH | `/planos/{id}` | Renomeia o plano. | planos |
| DELETE | `/planos/{id}` | Exclui o plano. | planos |
| PUT | `/planos/{id}/conteudo` | Salva o conteúdo editado pelo professor. | planos |
| POST | `/planos/{id}/restaurar` | Descarta a edição e volta ao plano gerado. | planos |
| PATCH | `/posts/{id}` | Edita o post: legenda, hashtags, comentários e aprovação. | posts |
| DELETE | `/posts/{id}` | Exclui um post da grade. | posts |
| GET | `/posts/{id}/comentarios` | Os comentários de um post do feed. | posts |
| POST | `/posts/{id}/regenerar` | Regenera o texto ou a imagem de um post. | posts |
| GET | `/progresso/{expId}` | O progresso do estudante autenticado nesta experiência. | progresso |
| POST | `/progresso/{expId}` | Salva o progresso da experiência. | progresso |
| POST | `/progresso/{expId}/concluir` | Registra a conclusão da experiência. | progresso |
| GET | `/prospeccao/cadastros` | Os cadastros de interesse recebidos pelo site público. | prospeccao |
| GET | `/prospeccao/cadastros/exportacao` | Os mesmos cadastros, em CSV. | prospeccao |
| DELETE | `/prospeccao/cadastros/{id}` | Elimina um cadastro a pedido do titular (LGPD art. 18, VI). | prospeccao |
| POST | `/prospeccao/publico/cadastros` | Registra um cadastro de interesse feito no site público. | prospeccao |
| POST | `/quem-mandou-isso/concluir` | Encerra a missão, depois das perguntas de evidência. | quem-mandou-isso |
| POST | `/quem-mandou-isso/enquete` | O voto na enquete de motivo — o latch 2. | quem-mandou-isso |
| POST | `/quem-mandou-isso/entrar` | Toca "Entrar no grupo": abre a sessão desta rodada. | quem-mandou-isso |
| GET | `/quem-mandou-isso/gate` | A fase da turma e o passo do estudante (polling de 3 s). | quem-mandou-isso |
| POST | `/quem-mandou-isso/mural` | "Confirmar envio" no Mural da Turma — o latch 1 (exatamente 3). | quem-mandou-isso |
| GET | `/quem-mandou-isso/professor/material` | O guia da aula: o banco curado com gabarito, o roteiro e as perguntas de evidência. | quem-mandou-isso |
| PUT | `/quem-mandou-isso/selecao` | Guarda a triagem em andamento: de 0 a 3 mensagens para o Mural. | quem-mandou-isso |
| GET | `/quem-mandou-isso/sessao` | O estado da missão e as 8 mensagens do grupo, sem o gabarito. | quem-mandou-isso |
| POST | `/quem-mandou-isso/turmas/{turmaId}/aprovar` | "Criar atividade" — aprova o pacote como uma atividade PRONTA da turma. | quem-mandou-isso |
| POST | `/quem-mandou-isso/turmas/{turmaId}/gate` | Os três botões do console: revelação, síntese e reflexão. | quem-mandou-isso |
| POST | `/quem-mandou-isso/turmas/{turmaId}/gerar` | Gera com IA o RASCUNHO das 8 mensagens (pré-aula). | quem-mandou-isso |
| POST | `/quem-mandou-isso/turmas/{turmaId}/nova-rodada` | "Zerar Turma para Nova Aplicação" — abre a rodada seguinte, guardando o histórico. | quem-mandou-isso |
| GET | `/quem-mandou-isso/turmas/{turmaId}/pacote` | O pacote da turma: o ativo, o rascunho e o banco curado — COM o gabarito. | quem-mandou-isso |
| GET | `/quem-mandou-isso/turmas/{turmaId}/pacotes` | As atividades da turma: os pacotes aprovados, com o em andamento marcado. | quem-mandou-isso |
| GET | `/quem-mandou-isso/turmas/{turmaId}/pacotes/{pacoteId}` | UMA atividade, inteira e COM o gabarito — em andamento ou pronta. | quem-mandou-isso |
| POST | `/quem-mandou-isso/turmas/{turmaId}/pacotes/{pacoteId}/em-andamento` | "Usar esta atividade agora" — o professor escolhe o que a turma joga (ADR-130). | quem-mandou-isso |
| GET | `/quem-mandou-isso/turmas/{turmaId}/painel` | O painel ao vivo: o progresso, o Termômetro da Turma e a folha nominal. | quem-mandou-isso |
| POST | `/rastro-boato/auditoria` | Registra a abertura da janela "Dados da mensagem". | rastro-boato |
| POST | `/rastro-boato/decisao` | A intervenção no grupo — irrevogável (latch). | rastro-boato |
| POST | `/rastro-boato/entrar` | Sai da tela de contexto e abre a lista de conversas. | rastro-boato |
| GET | `/rastro-boato/gate` | Em que etapa a turma está (polling de ~5s). | rastro-boato |
| POST | `/rastro-boato/modelagem` | O modelo do ciclo da desinformação — 4 blocos, sem nota. | rastro-boato |
| GET | `/rastro-boato/professor/material` | As três intervenções com o gabarito e o ciclo ordenado, para o guia da aula. | rastro-boato |
| POST | `/rastro-boato/reflexao` | O "Meu percurso" — encerra a missão (latch). | rastro-boato |
| GET | `/rastro-boato/sessao` | O estado da missão, as 4 conversas e os metadados de cada mensagem. | rastro-boato |
| GET | `/rastro-boato/turmas` | Turmas para o seletor do painel. | rastro-boato |
| DELETE | `/rastro-boato/turmas/{turmaId}` | Zerar a turma — a segunda aplicação. | rastro-boato |
| POST | `/rastro-boato/turmas/{turmaId}/gate` | Abre a Aula 2, ou pausa a simulação de volta na Aula 1. | rastro-boato |
| GET | `/rastro-boato/turmas/{turmaId}/painel` | O que a turma está fazendo na missão, ao vivo. | rastro-boato |
| GET | `/readyz` | As dependências estão prontas (banco). | readyz |
| GET | `/recursos/arquivadas` | As experiências arquivadas: tiradas do produto sem serem apagadas (ADR-116). | recursos |
| GET | `/recursos/auditoria` | Quem ligou ou desligou o quê, e quando. | recursos |
| GET | `/recursos/efetivos` | O que está disponível para a escola do token. | recursos |
| POST | `/recursos/experiencias/{expId}/ativar` | Ativa uma versão para o CONTRATO (o rollback). | recursos |
| PUT | `/recursos/experiencias/{expId}/versao` | Fixa (ou solta) a versão de uma experiência num escopo. | recursos |
| GET | `/recursos/experiencias/{expId}/versoes` | As versões publicadas de uma experiência. | recursos |
| GET | `/recursos/limites-da-ajuda` | Os limites de minutos da Ajuda com avatar. | recursos |
| PUT | `/recursos/limites-da-ajuda/{chave}` | Define um limite de minutos da Ajuda. | recursos |
| GET | `/recursos/painel` | O painel: produtos, experiências e o que vale em cada escopo. | recursos |
| GET | `/recursos/quotas-de-ia` | O teto diário de IA de cada perfil. | recursos |
| PUT | `/recursos/quotas-de-ia/{perfil}` | Define o teto diário de IA de um perfil. | recursos |
| PUT | `/recursos/{recursoId}` | Liga ou desliga um recurso num escopo. | recursos |
| DELETE | `/recursos/{recursoId}` | Remove a exceção de um escopo (volta a herdar). | recursos |
| GET | `/rostering/contas-de-assento` | As contas sem matrícula da rede — as que podem ser de assento. | rostering |
| POST | `/rostering/importar` | Importa a planilha de pessoas. | rostering |
| GET | `/rostering/modelos/exemplo.csv` | O mesmo modelo, preenchido com um exemplo. | rostering |
| GET | `/rostering/modelos/oneroster/{arquivo}` | O modelo em branco de um arquivo do OneRoster 1.2. | rostering |
| GET | `/rostering/modelos/oneroster/{arquivo}/exemplo` | O mesmo arquivo do OneRoster, preenchido com um exemplo. | rostering |
| GET | `/rostering/modelos/usuarios.csv` | O modelo em branco da planilha de pessoas. | rostering |
| POST | `/rostering/oneroster/{arquivo}` | Binding CSV do OneRoster 1.2 — UM arquivo por chamada. | rostering |
| POST | `/runs` | Cria a run do estudante na atividade ativa. | runs |
| GET | `/runs/boot` | O bootstrap do aparelho — o que a tela de entrada precisa saber. | runs |
| GET | `/runs/{id}/busca` | Busca no acervo da atividade. | runs |
| POST | `/runs/{id}/conclusao` | A escolha de um lado no fim da missão. | runs |
| GET | `/runs/{id}/dossie` | O dossiê da sessão — o relatório da revelação. | runs |
| POST | `/runs/{id}/entrar` | O estudante entra no aparelho e vai ao feed. | runs |
| POST | `/runs/{id}/eventos` | Lote de eventos do cliente — o canal OPERACIONAL. | runs |
| GET | `/runs/{id}/fase` | A tela que o estudante deve estar vendo agora. | runs |
| GET | `/runs/{id}/feed` | O próximo bloco do feed. | runs |
| POST | `/runs/{id}/finish` | Congela a run e computa o dossiê. | runs |
| GET | `/runs/{id}/perdidos` | O que o estudante PERDEU — posts do lado oposto que nunca foram servidos. | runs |
| POST | `/runs/{id}/reacoes` | Reações das personas ao que o estudante escreveu. | runs |
| POST | `/runs/{id}/reflexao` | O fechamento escrito da atividade. | runs |
| GET | `/runs/{id}/reflexao` | O texto da reflexão que o estudante já escreveu. | runs |
| POST | `/runs/{id}/reset` | Reabre a run de um estudante, sorteando a largada de novo. | runs |
| GET | `/runs/{id}/salvos` | A coleção do estudante — o que ele salvou. | runs |
| POST | `/runs/{id}/student-post` | O estudante publica no app, e as personas reagem. | runs |
| GET | `/salas/minhas` | As salas do estudante: as turmas dele e a grade de cada uma. | salas |
| GET | `/salas/turma/{turmaId}` | A sala: a turma, a grade de missões e quem liberou cada uma. | salas |
| PUT | `/salas/turma/{turmaId}/missoes/{expId}` | Libera ou encerra uma missão nesta turma. | salas |
| POST | `/telemetry/batch` | Recebe um lote do canal ANALÍTICO da SDK. | telemetry |
| POST | `/telemetry/beacon` | Último lote de uma sessão que está fechando. | telemetry |
| POST | `/telemetry/ingest` | Consome a push subscription do Pub/Sub e grava os eventos. | telemetry |
| GET | `/turmas` | As turmas da escola. | turmas |
| POST | `/turmas` | Cria uma turma. | turmas |
| GET | `/turmas/minhas` | As turmas DO PROFESSOR — as que ele tem matrícula, e só elas. | turmas |
| PATCH | `/turmas/{id}` | Edita nome, série ou turno da turma. | turmas |
| GET | `/turmas/{id}` | Os matriculados da turma — a lista nominal. | turmas |
| POST | `/turmas/{id}/matriculas` | Matricula uma pessoa na turma. | turmas |
| GET | `/unoogpt/agregado/escola` | O agregado da escola — uma linha por turma. | unoogpt |
| POST | `/unoogpt/alocacao` | Manda uma equipe para um bairro. | unoogpt |
| PUT | `/unoogpt/conjuntos` | Carrega fontes no modelo pelo painel. | unoogpt |
| POST | `/unoogpt/contrafactual` | "E se eu tivesse mandado para…" — calculado e descartado. | unoogpt |
| POST | `/unoogpt/passo` | Move a sessão para outro passo da missão. | unoogpt |
| POST | `/unoogpt/pergunta` | O turno do Cientista — a rota que fala com o modelo. | unoogpt |
| GET | `/unoogpt/professor/estudantes/{estudanteId}` | A linha de UMA criança: leitura em graus e a Transcrição. | unoogpt |
| GET | `/unoogpt/professor/fontes` | As 8 fontes do cenário com o viés de cada uma, para o guia da aula. | unoogpt |
| GET | `/unoogpt/professor/turmas` | Turmas para o seletor de resultados do unooGPT. | unoogpt |
| GET | `/unoogpt/professor/turmas/{turmaId}` | A folha da turma: relógio, retrato de conduta e uma linha por estudante. | unoogpt |
| DELETE | `/unoogpt/professor/turmas/{turmaId}` | Zera a turma: apaga as partidas E o relógio. | unoogpt |
| POST | `/unoogpt/professor/turmas/{turmaId}/relogio` | Dá a largada, soma tempo, encerra, troca o modo ou redefine. | unoogpt |
| POST | `/unoogpt/reiniciar` | Recomeça — abre uma tentativa NOVA. | unoogpt |
| GET | `/unoogpt/relogio` | O relógio da turma — polling de ~5s. | unoogpt |
| GET | `/unoogpt/resultado` | O resultado da tentativa, com a faixa e o que ele nunca consultou. | unoogpt |
| GET | `/unoogpt/sessao` | O bootstrap da Missão Tempestade. Cria a sessão na primeira visita. | unoogpt |
| POST | `/unoogpt/simular` | Enfrenta a tempestade e fecha a tentativa. | unoogpt |
| GET | `/usuarios` | As pessoas da escola, paginadas. | usuarios |
| POST | `/usuarios` | Cadastra UMA pessoa da escola (estudante, professor ou gestor). | usuarios |
| POST | `/usuarios/importar-csv` | Compatibilidade: delega para `POST /rostering/importar`. | usuarios |
| POST | `/usuarios/sem-escola` | Cadastra um papel SEM escola (`gestor_contrato` ou `gestor_regional`). | usuarios |
| PATCH | `/usuarios/{id}` | Edita nome, CPF, e-mail, papel ou situação da pessoa. | usuarios |
| POST | `/usuarios/{id}/reset-senha` | Gera uma senha temporária e a devolve UMA vez. | usuarios |
| GET | `/vila/agregado/turmas` | Turmas para o seletor da Vila. | vila |
| GET | `/vila/agregado/turmas/{turmaId}` | O agregado da turma — contagens, nunca por criança. | vila |
| GET | `/vila/professor/cartoes` | TODOS os cartões, das três bolhas, COM o gabarito. | vila |
| GET | `/vila/professor/estudantes/{estudanteId}` | O relatório da última partida concluída de um estudante. | vila |
| GET | `/vila/professor/turmas/{turmaId}` | Uma linha por estudante da turma. | vila |
| DELETE | `/vila/professor/turmas/{turmaId}/dados` | Zera os dados da Vila desta turma. | vila |
| POST | `/vila/sessoes` | Abre a partida e entrega os cartões DESTA criança. | vila |
| POST | `/vila/sessoes/{id}/concluir` | Fecha a partida e grava o payload bruto. | vila |
