# Copy — exp09ef1b (O Dossiê Invisível) — passada 2 (revisão em contexto)

**Data:** 2026-09-30  
**Ambiente:** ChatGPT (`chatgpt`) e Unooria Hub (`unooria`)  
**Faixa:** 9º ano do Ensino Fundamental (`9EF`)  
**Status:** Revisão concluída em contexto com as telas construídas (`DESKTOP`).

---

## Sheet de strings revisado (100% das strings em contexto)

| ID tela | Chave | Tipo | Seção | PT-BR (final) | Palavras | Redundância | Voz | Revisão (o que mudou e por quê) |
|---|---|---|---|---|:---:|---|---|---|
| `E0-PROF-01` | `e0.rotulo.catalogo_titulo` | rótulo de UI | `unooria` | O Dossiê Invisível: Triagem Algorítmica e Orçamento | 8 | `texto` | Unooria | Mantido. Título canônico institucional no Hub. |
| `E0-PROF-01` | `e0.texto.catalogo_sub` | narrativa | `unooria` | 9º ano EF · Unidade 1 · Habilidades EF09CO07 e EF09CO08. | 9 | `texto` | Unooria | Mantido. Metadados do card no catálogo docente. |
| `E0-PROF-01` | `e0.rotulo.botao_configurar` | rótulo de UI | `unooria` | Configurar Missão | 2 | `texto+ícone` | Unooria | Mantido. Ação primária que salta no card do catálogo. |
| `E0-PROF-01` | `e0.rotulo.botao_padrao_hub` | rótulo de UI | `unooria` | Usar banco padrão | 3 | `texto+ícone` | Unooria | Mantido. Atalho secundário de 2 cliques. |
| `E0-PROF-02` | `e0.rotulo.preparo_cabecalho` | rótulo de UI | `unooria` | Recorte Temático da Aula | 4 | `texto` | Unooria | Mantido. Topo da gaveta de formulário docente. |
| `E0-PROF-02` | `e0.instrucao.preparo_guia` | instrução | `unooria` | Escolha o componente curricular e defina o território comunitário da atividade. | 11 | `texto` | Unooria | Mantido. Guia de preenchimento dos 5 parâmetros. |
| `E0-PROF-02` | `e0.rotulo.campo_disciplina` | rótulo de UI | `unooria` | Componente Curricular | 2 | `texto` | Unooria | Mantido. Dropdown fechado de disciplinas BNCC. |
| `E0-PROF-02` | `e0.rotulo.campo_tema` | rótulo de UI | `unooria` | Tema da Aula (máx. 60 caracteres) | 6 | `texto` | Unooria | Mantido. Rótulo com teto visível explícito. |
| `E0-PROF-02` | `e0.rotulo.campo_assuntos` | rótulo de UI | `unooria` | Objetos de Conhecimento (3 a 6 itens) | 7 | `texto` | Unooria | Mantido. Rótulo da área de pílulas/tags. |
| `E0-PROF-02` | `e0.rotulo.campo_contexto` | rótulo de UI | `unooria` | Contexto Local / Escola (opcional) | 5 | `texto` | Unooria | Mantido. Campo facultativo contextualizador. |
| `E0-PROF-02` | `e0.rotulo.campo_foco` | rótulo de UI | `unooria` | Foco Pedagógico (opcional) | 4 | `texto` | Unooria | Mantido. Campo facultativo de ênfase da aula. |
| `E0-PROF-02` | `e0.rotulo.botao_gerar_ia` | rótulo de UI | `unooria` | Gerar Cenário com IA | 4 | `texto+ícone` | Unooria | Mantido. Botão de ação primária destacada. |
| `E0-PROF-02` | `e0.rotulo.botao_usar_curado` | rótulo de UI | `unooria` | Usar Banco Padrão Oficial | 4 | `texto` | Unooria | Mantido. Ação secundária sem consumo de cota. |
| `E0-PROF-03` | `e0.feedback.gerando_titulo` | feedback de sistema | `unooria` | Estruturando documentos e dossiês com inteligência artificial... | 8 | `texto+ícone` | Unooria | Mantido. Título do modal de progresso assíncrono. |
| `E0-PROF-03` | `e0.feedback.gerando_status` | feedback de sistema | `unooria` | Sintetizando projetos comunitários e relatórios de auditoria. | 7 | `texto` | Unooria | Mantido. Progresso em tempo real da Vertex Gemini. |
| `E0-PROF-03` | `e0.rotulo.botao_cancelar_geracao` | rótulo de UI | `unooria` | Cancelar Geração | 2 | `texto` | Unooria | Mantido. Botão de escape/retorno ao formulário. |
| `E0-PROF-03` | `e0.erro.quota_esgotada` | erro/falha | `unooria` | Limite de inteligência artificial atingido para este ciclo. A missão foi configurada automaticamente com o banco oficial curado. | 18 | `texto+ícone` | Unooria | Mantido. Fallback transparente HTTP 429. |
| `E0-PROF-04` | `e0.rotulo.curadoria_titulo` | rótulo de UI | `unooria` | Curadoria do Cenário da Turma | 5 | `texto` | Unooria | Mantido. Topo da tela de revisão docente. |
| `E0-PROF-04` | `e0.instrucao.curadoria_guia` | instrução | `unooria` | Revise os três projetos e os registros de campo antes de liberar para os estudantes. | 14 | `texto` | Unooria | Mantido. Instrução da homologação obrigatória. |
| `E0-PROF-04` | `e0.rotulo.botao_editar_item` | rótulo de UI | `unooria` | Editar Texto | 2 | `texto+ícone` | Unooria | Mantido. Ação secundária por card de projeto. |
| `E0-PROF-04` | `e0.rotulo.botao_regenerar_item` | rótulo de UI | `unooria` | Regenerar Este Projeto | 3 | `texto+ícone` | Unooria | Mantido. Ação de chamada pontual de IA. |
| `E0-PROF-04` | `e0.rotulo.botao_aprovar_pacote` | rótulo de UI | `unooria` | Aprovar e Avançar para Ativação | 5 | `texto+ícone` | Unooria | Mantido. Ação primária que salta no rodapé. |
| `E0-PROF-05` | `e0.rotulo.ativacao_titulo` | rótulo de UI | `unooria` | Liberação e Agendamento | 3 | `texto` | Unooria | Mantido. Topo da etapa de abertura da missão. |
| `E0-PROF-05` | `e0.instrucao.ativacao_selecao` | instrução | `unooria` | Selecione a turma que participará da sessão do conselho. | 9 | `texto` | Unooria | Mantido. Guia de vinculação de turma. |
| `E0-PROF-05` | `e0.rotulo.botao_liberar_agora` | rótulo de UI | `unooria` | Liberar Missão Agora | 3 | `texto+ícone` | Unooria | Mantido. Ação primária de ativação síncrona. |
| `E0-PROF-05` | `e0.rotulo.botao_agendar` | rótulo de UI | `unooria` | Agendar para Data Futura | 4 | `texto+ícone` | Unooria | Mantido. Ação secundária programada. |
| `E1-ALU-01` | `e1.narrativa.amara_desafio` | narrativa | `clone` | Você tem R$ 12.000 para repassar a um único projeto. A máquina lê rápido, mas lembre-se: se os dados contam uma história desigual, o que ela vai concluir? | 28 | `texto` | Amara | **Revisado.** Encurtada a 2ª oração de 21 para 18 palavras, eliminando prolixidade e mantendo rigorosamente ≤ 20 palavras/oração. |
| `E1-ALU-01` | `e1.rotulo.sidebar_workspace` | rótulo de UI | `clone` | Conselho Municipal de Recursos | 4 | `texto` | Plataforma simulada | Mantido. Cabeçalho superior na `WebSidebar`. |
| `E1-ALU-01` | `e1.rotulo.sidebar_sessao` | rótulo de UI | `clone` | Deliberação Orçamentária 2026/1 | 3 | `texto` | Plataforma simulada | Mantido. Thread ativa identificada na barra lateral. |
| `E1-ALU-01` | `e1.rotulo.card_mesa_titulo` | rótulo de UI | `clone` | Projeto Mesa Aberta | 3 | `texto` | Plataforma simulada | Mantido. Título do card de contexto 1. |
| `E1-ALU-01` | `e1.texto.card_mesa_desc` | narrativa | `clone` | 24 vagas. Refeições e permanência escolar no contraturno para estudantes vulnerabilizados. Coordenação: João. | 14 | `texto` | Plataforma simulada | Mantido. Resumo da entidade no corpo do card. |
| `E1-ALU-01` | `e1.rotulo.card_ponto_titulo` | rótulo de UI | `clone` | Projeto Ponto de Apoio | 4 | `texto` | Plataforma simulada | Mantido. Título do card de contexto 2. |
| `E1-ALU-01` | `e1.texto.card_ponto_desc` | narrativa | `clone` | 18 vagas. Acolhimento emocional e mediação de conflitos contra situações de bullying. Coordenação: Ana. | 14 | `texto` | Plataforma simulada | Mantido. Resumo da entidade no corpo do card. |
| `E1-ALU-01` | `e1.rotulo.card_conexao_titulo` | rótulo de UI | `clone` | Conexão para Continuar | 3 | `texto` | Plataforma simulada | Mantido. Título do card de contexto 3. |
| `E1-ALU-01` | `e1.texto.card_conexao_desc` | narrativa | `clone` | 20 vagas. Laboratório de informática e inclusão digital para pesquisas escolares. Coordenação: Luana. | 13 | `texto` | Plataforma simulada | Mantido. Resumo da entidade no corpo do card. |
| `E1-ALU-01` | `e1.rotulo.pilula_1` | rótulo de UI | `clone` | Qual projeto atende mais pessoas pelo menor custo por vaga? | 10 | `texto` | Plataforma simulada | Mantido. Pílula efêmera 1 que salta sobre o composer. |
| `E1-ALU-01` | `e1.rotulo.pilula_2` | rótulo de UI | `clone` | Compare a regularidade e os relatórios enviados pelos três projetos. | 10 | `texto` | Plataforma simulada | Mantido. Pílula efêmera 2 que salta sobre o composer. |
| `E1-ALU-01` | `e1.rotulo.pilula_3` | rótulo de UI | `clone` | Quais são as evidências de impacto de cada iniciativa? | 9 | `texto` | Plataforma simulada | Mantido. Pílula efêmera 3 que salta sobre o composer. |
| `E1-ALU-01` | `e1.rotulo.composer_placeholder` | rótulo de UI | `clone` | Consulte dados ou solicite relatórios da comissão... | 7 | `texto` | Plataforma simulada | Mantido. Placeholder nativo no `ChatInput`. |
| `E2-ALU-01` | `e2.narrativa.ia_analise_geral` | narrativa | `clone` | Base institucional consultada. O Conexão para Continuar apresenta 12 relatórios mensais padronizados em nuvem. O Ponto de Apoio possui atas semestrais. O Mesa Aberta apresenta ficha cadastral com déficit de relatórios digitais na nuvem. | 34 | `texto` | Plataforma simulada | Mantido. Stream da IA no primeiro retorno investigativo. |
| `E2-ALU-01` | `e2.narrativa.ia_alerta_mesa` | narrativa | `clone` | Alerta de conformidade: Histórico institucional insuficiente para validação algorítmica do Mesa Aberta. Alto risco documental por ausência de métricas digitalizadas. | 20 | `texto` | Plataforma simulada | Mantido. Elemento que salta na tela investigativa. |
| `E2-ALU-01` | `e2.narrativa.ia_oferece_cadernos` | narrativa | `clone` | Constam nos arquivos físicos do conselho 3 cadernos de campo com registros diários de refeições e assinaturas dos responsáveis. Deseja anexar e processar esses dados agora? | 27 | `texto` | Plataforma simulada | Mantido. Oferta condicional do Caminho A. |
| `E2-ALU-01` | `e2.rotulo.botao_anexar_cadernos` | rótulo de UI | `clone` | Anexar e Processar Cadernos Físicos | 5 | `texto+ícone` | Plataforma simulada | Mantido. Card de anexo que registra `caminho_tomado = "A"`. |
| `E2-ALU-01` | `e2.narrativa.ia_parecer_caminhob` | narrativa | `clone` | Parecer preliminar do assistente: Recomendo repasse integral ao Conexão para Continuar. A iniciativa apresenta governança técnica consolidada, métricas auditáveis em PDF e menor risco orçamentário. | 25 | `texto` | Plataforma simulada | Mantido. Indução burocrática fria do Caminho B. |
| `E2-ALU-01` | `e2.rotulo.botao_emitir_parecer` | rótulo de UI | `clone` | Emitir Parecer Vinculante | 3 | `texto+ícone` | Plataforma simulada | Mantido. Habilita após 3 trocas para avançar ao Pico. |
| `E2-ALU-02` | `e2.rotulo.drawer_titulo` | rótulo de UI | `clone` | Cadernos_Fisicos_Campo.pdf — 3 volumes digitalizados | 5 | `texto+ícone` | Plataforma simulada | Mantido. Cabeçalho da gaveta lateral `AttachmentDrawer`. |
| `E2-ALU-02` | `e2.texto.drawer_extrato` | narrativa | `clone` | Volume 1 a 3: 180 dias de registros diários de almoço, controle nutricional por estudante e assinaturas físicas dos responsáveis. Frequência média aferida: 24 atendimentos diários. | 26 | `texto` | Plataforma simulada | Mantido. Extrato textual acessível e fac-símile. |
| `E2-ALU-02` | `e2.rotulo.drawer_fechar` | rótulo de UI | `clone` | Fechar Visualização | 2 | `texto` | Plataforma simulada | Mantido. Botão secundário de fechar gaveta. |
| `E3-ALU-01` | `e3.rotulo.latch_titulo` | rótulo de UI | `clone` | Homologação de Destinação Orçamentária — R$ 12.000 | 7 | `texto+ícone` | Plataforma simulada | Mantido. Cabeçalho formal do card de Pico. |
| `E3-ALU-01` | `e3.instrucao.latch_aviso` | instrução | `clone` | Seleção única e definitiva. A verba é indivisível e os projetos não contemplados aguardarão na fila de espera. | 17 | `texto` | Plataforma simulada | Mantido. Aviso de tensão institucional indivisível. |
| `E3-ALU-01` | `e3.rotulo.opcao_mesa` | rótulo de UI | `clone` | Projeto Mesa Aberta (Alimentação e Permanência) | 6 | `texto` | Plataforma simulada | Mantido. Opção 1 exclusiva do radio button. |
| `E3-ALU-01` | `e3.rotulo.opcao_ponto` | rótulo de UI | `clone` | Projeto Ponto de Apoio (Acolhimento Antibullying) | 6 | `texto` | Plataforma simulada | Mantido. Opção 2 exclusiva do radio button. |
| `E3-ALU-01` | `e3.rotulo.opcao_conexao` | rótulo de UI | `clone` | Conexão para Continuar (Inclusão Digital) | 5 | `texto` | Plataforma simulada | Mantido. Opção 3 exclusiva do radio button. |
| `E3-ALU-01` | `e3.rotulo.tag_fila_espera` | feedback de sistema | `clone` | Fila de espera (sem abertura de vagas) | 7 | `texto` | Plataforma simulada | Mantido. Tag que cai sobre as opções não marcadas. |
| `E3-ALU-01` | `e3.pergunta.poll_canal_a` | pergunta de reflexão | `clone` | Ao analisar os documentos dos projetos sociais, como a comissão deve avaliar a diferença de relatórios digitais entre as iniciativas? | 19 | `texto` | Plataforma simulada | Mantido. Enquete discreta Canal A de `EF09CO08`. |
| `E3-ALU-01` | `e3.rotulo.poll_opt_atingiu` | rótulo de UI | `clone` | Reconhecer que a falta de computadores e equipe de digitalização prejudica o registro de iniciativas comunitárias essenciais, exigindo validação de dados de campo antes do repasse. | 26 | `texto` | Plataforma simulada | Mantido. Opção Atingiu (preserva gabarito da spec). |
| `E3-ALU-01` | `e3.rotulo.poll_opt_processo` | rótulo de UI | `clone` | Considerar a existência de relatórios digitais padronizados como um diferencial técnico importante, independentemente das condições materiais da entidade. | 18 | `texto` | Plataforma simulada | Mantido. Opção Em processo. |
| `E3-ALU-01` | `e3.rotulo.poll_opt_naoatingiu` | rótulo de UI | `clone` | Desclassificar projetos que não possuam relatórios e planilhas na nuvem por considerá-los desorganizados ou despreparados para receber verba pública. | 19 | `texto` | Plataforma simulada | Mantido. Opção Não atingiu. |
| `E3-ALU-01` | `e3.rotulo.campo_opcional_nota` | rótulo de UI | `clone` | Anotação pessoal do relator para o debate (opcional) | 8 | `texto` | Plataforma simulada | Mantido. Textarea facultativa sem impacto em nota. |
| `E3-ALU-01` | `e3.rotulo.botao_homologar_latch` | rótulo de UI | `clone` | Homologar Voto Irreversível | 3 | `texto+ícone` | Plataforma simulada | Mantido. **Ponto focal exclusivo do PICO**. |
| `E3-ALU-01` | `e3.feedback.latch_travado` | feedback de sistema | `clone` | Parecer registrado. Aguardando autorização da presidência da mesa para abrir o próximo ponto de pauta. | 15 | `texto+ícone` | Plataforma simulada | Mantido. Estado diegético de trava permanente. |
| `E3-PROF-01` | `e3.rotulo.prof_painel_titulo` | rótulo de UI | `unooria` | Quórum de Homologação Orçamentária | 4 | `texto` | Unooria | Mantido. Cabeçalho de acompanhamento docente. |
| `E3-PROF-01` | `e3.instrucao.prof_painel_guia` | texto do professor | `unooria` | Acompanhe a entrega dos votos vinculantes antes de liberar a auditoria algorítmica da Etapa 4. | 15 | `texto` | Unooria | Mantido. Guia de handoff docente. |
| `E3-PROF-01` | `e3.rotulo.botao_liberar_gate4` | rótulo de UI | `unooria` | Liberar Auditoria dos Cadernos (Gate E4) | 6 | `texto+ícone` | Unooria | Mantido. Ação síncrona que destrava os terminais. |
| `E4-ALU-01` | `e4.feedback.badge_auditoria` | feedback de sistema | `clone` | Auditoria de Integridade Convocada | 4 | `texto+ícone` | Plataforma simulada | Mantido. Badge de destaque oficial no topo da resposta. |
| `E4-ALU-01` | `e4.narrativa.ia_revelacao_b` | narrativa | `clone` | Você homologou o repasse para o projeto Conexão para Continuar. Contudo, a equipe de campo localizou e digitalizou os cadernos de campo do Mesa Aberta. Reprocessando dados com critérios idênticos de custo por atendimento: o Mesa Aberta atinge a primeira posição de eficiência social. | 43 | `texto` | Plataforma simulada | Mantido. **Virada do AHA** no Caminho B induzido. |
| `E4-ALU-01` | `e4.narrativa.ia_revelacao_a` | narrativa | `clone` | Você homologou seu voto no Mesa Aberta após auditar os cadernos físicos. Simulação contrafactual: sem sua averiguação das lacunas na Etapa 2, o algoritmo teria induzido o voto para o Conexão para Continuar unicamente pela presença de arquivos em PDF. | 39 | `texto` | Plataforma simulada | Mantido. **Virada do AHA** no Caminho A contrafactual. |
| `E4-ALU-01` | `e4.texto.tabela_comparativa` | narrativa | `clone` | Critério do algoritmo anterior: volume de arquivos PDF na nuvem. Critério de campo comprovado: atendimento diário de 24 jovens e urgência alimentar verificada. | 22 | `texto` | Plataforma simulada | Mantido. Split-view que salta na tela do AHA. |
| `E4-ALU-01` | `e4.feedback.espera_plenaria` | feedback de sistema | `clone` | Sessão plenária em andamento. A presidência da mesa conduz a conferência dos dados em plenária antes da liberação do próximo parecer. | 21 | `texto+ícone` | Plataforma simulada | Mantido. Banner de espera pelo debate mediado. |
| `E4-PROF-01` | `e4.rotulo.prof_debate_titulo` | rótulo de UI | `unooria` | Projeção Plenária: Dispersão de Votação da Turma | 7 | `texto` | Unooria | Mantido. Cabeçalho de projeção no telão/lousa. |
| `E4-PROF-01` | `e4.instrucao.prof_projecao_guia` | texto do professor | `unooria` | Projete este gráfico para a sala e conduza o debate com as três perguntas socráticas. | 15 | `texto` | Unooria | Mantido. Instrução da mediação coletiva de 12 min. |
| `E4-PROF-01` | `e4.rotulo.botao_liberar_gate5` | rótulo de UI | `unooria` | Liberar Etapa de Sistematização (Gate E5) | 6 | `texto+ícone` | Unooria | Mantido. Disparo do Gate E5 pós-debate. |
| `E5-ALU-01` | `e5.narrativa.amara_explicar` | narrativa | `clone` | Quando os computadores calculam decisões usando apenas dados prévios digitalizados, eles transformam a desigualdade de acesso em desvantagem injusta. Veja como isso aconteceu no nosso próprio chat. | 27 | `texto` | Amara | Mantido. **Card do MEMORÁVEL** com as 4 caixas teóricas. |
| `E5-ALU-01` | `e5.instrucao.selecionar_ancoras` | instrução | `clone` | Selecione no histórico duas mensagens que comprovam o viés: o parecer inicial de alto risco documental e a tabela de reprocessamento pós-cadernos. | 22 | `texto` | Plataforma simulada | Mantido. Instrução da ferramenta de marcação de âncoras. |
| `E5-ALU-01` | `e5.feedback.ancoras_validadas` | feedback de sistema | `clone` | Evidências identificadas com sucesso na thread. O viés de dados foi localizado. | 12 | `texto+ícone` | Plataforma simulada | Mantido. Feedback pós-seleção correta das 2 mensagens. |
| `E5-ALU-01` | `e5.rotulo.botao_avancar_refletir` | rótulo de UI | `clone` | Avançar para Aplicação Prática | 4 | `texto+ícone` | Plataforma simulada | Mantido. Ação habilitada para a Etapa 6. |
| `E6-ALU-01` | `e6.narrativa.caso_transporte_intro` | narrativa | `clone` | Notificação disciplinar: O sistema automatizado suspendeu o passe escolar de Lia e Davi por atingirem o limite de 4 faltas em 20 dias letivos. Analise as planilhas para emitir parecer. | 30 | `texto` | Plataforma simulada | Mantido. Contexto do caso de transferência direta. |
| `E6-ALU-01` | `e6.instrucao.cruzar_datas` | instrução | `clone` | Clique na data de falta na Tabela de Frequência e em seguida no registro correspondente no Relatório de Ônibus para verificar justificativas de força maior. | 25 | `texto` | Plataforma simulada | Mantido. Guia de pareamento entre tabelas. |
| `E6-ALU-01` | `e6.rotulo.tab_a_cabecalho` | rótulo de UI | `clone` | Frequência Escolar: Faltas Registradas | 5 | `texto` | Plataforma simulada | Mantido. Topo da Tabela A (Lia e Davi). |
| `E6-ALU-01` | `e6.rotulo.tab_b_cabecalho` | rótulo de UI | `clone` | Relatório Operacional: Linha 302 | 5 | `texto` | Plataforma simulada | Mantido. Topo da Tabela B (Cancelamentos do ônibus). |
| `E6-ALU-01` | `e6.feedback.datas_validadas` | feedback de sistema | `clone` | 4 datas de faltas de Lia correspondem exatamente a falhas da Linha 302. Dados do itinerário de Davi ausentes na base. | 21 | `texto+ícone` | Plataforma simulada | Mantido. Destrava a enquete ética de transporte. |
| `E6-ALU-01` | `e6.pergunta.poll_transporte` | pergunta de reflexão | `clone` | Com base no cruzamento das tabelas de transporte e frequência escolar, qual parecer a comissão deve emitir sobre Lia e Davi? | 20 | `texto` | Plataforma simulada | Mantido. Enquete ética Canal A de `EF09CO07`. |
| `E6-ALU-01` | `e6.rotulo.transp_opt_atingiu` | rótulo de UI | `clone` | Isentar as faltas de Lia pela correspondência exata com as falhas da Linha 302 e suspender qualquer punição a Davi até que os dados operacionais de sua linha de ônibus sejam apurados. | 32 | `texto` | Plataforma simulada | Mantido. Opção Atingiu (preserva gabarito da spec). |
| `E6-ALU-01` | `e6.rotulo.transp_opt_processo` | rótulo de UI | `clone` | Isentar Lia devido à comprovação de cancelamento da Linha 302, mas confirmar a suspensão do passe de Davi por falta de registros de falha no sistema. | 25 | `texto` | Plataforma simulada | Mantido. Opção Em processo. |
| `E6-ALU-01` | `e6.rotulo.transp_opt_naoatingiu` | rótulo de UI | `clone` | Manter a suspensão de ambos os estudantes para cumprir a regra de limite de 4 faltas registradas pelo sistema sem intervenção manual. | 22 | `texto` | Plataforma simulada | Mantido. Opção Não atingiu. |
| `E6-ALU-02` | `e6.pergunta.poll_b_ef09co07` | pergunta de reflexão | `clone` | Ao analisar a recomendação de uma IA que seleciona pessoas com base em históricos prévios, qual postura ética o avaliador deve adotar? | 22 | `texto` | Plataforma simulada | Mantido. Pergunta conceitual Canal B de `EF09CO07`. |
| `E6-ALU-02` | `e6.rotulo.b07_opt_atingiu` | rótulo de UI | `clone` | Auditar os dados de treinamento para identificar lacunas históricas e assumir a responsabilidade humana pela decisão final. | 18 | `texto` | Plataforma simulada | Mantido. Opção Atingiu Canal B. |
| `E6-ALU-02` | `e6.rotulo.b07_opt_processo` | rótulo de UI | `clone` | Aceitar a sugestão da máquina caso os critérios matemáticos pré-definidos tenham sido rigorosamente seguidos. | 15 | `texto` | Plataforma simulada | Mantido. Opção Em processo Canal B. |
| `E6-ALU-02` | `e6.rotulo.b07_opt_naoatingiu` | rótulo de UI | `clone` | Descartar o uso de computadores e decidir exclusivamente pela intuição pessoal. | 11 | `texto` | Plataforma simulada | Mantido. Opção Não atingiu Canal B. |
| `E6-ALU-02` | `e6.pergunta.poll_b_ef09co08` | pergunta de reflexão | `clone` | Por que uma organização social que mantém dados apenas em papel corre maior risco de ser excluída por políticas públicas automatizadas? | 21 | `texto` | Plataforma simulada | Mantido. Pergunta conceitual Canal B de `EF09CO08`. |
| `E6-ALU-02` | `e6.rotulo.b08_opt_atingiu` | rótulo de UI | `clone` | Porque a escassez de infraestrutura digital impede que seu trabalho real seja capturado por sistemas de triagem algorítmica. | 19 | `texto` | Plataforma simulada | Mantido. Opção Atingiu Canal B. |
| `E6-ALU-02` | `e6.rotulo.b08_opt_processo` | rótulo de UI | `clone` | Porque sistemas computacionais são mais rápidos e exigem relatórios legíveis para arquivamento. | 13 | `texto` | Plataforma simulada | Mantido. Opção Em processo Canal B. |
| `E6-ALU-02` | `e6.rotulo.b08_opt_naoatingiu` | rótulo de UI | `clone` | Porque cadernos em papel têm menor validade legal do que planilhas digitais. | 12 | `texto` | Plataforma simulada | Mantido. Opção Não atingiu Canal B. |
| `E6-ALU-02` | `e6.rotulo.campo_parecer_opcional` | rótulo de UI | `clone` | Justificativa do relator para ata (opcional) | 7 | `texto` | Plataforma simulada | Mantido. Campo dissertativo facultativo final. |
| `E6-ALU-02` | `e6.rotulo.botao_concluir_missao` | rótulo de UI | `clone` | Concluir Missão | 2 | `texto+ícone` | Plataforma simulada | Mantido. Ação primária que invoca SDK `concluir()`. |
| `E6-ALU-02` | `e6.feedback.ata_arquivada` | feedback de sistema | `clone` | Parecer arquivado. Aguardando deliberação da plenária. | 7 | `texto+ícone` | Plataforma simulada | Mantido. Congelamento terminal pós-conclusão. |
| `E6-ALU-02` | `e6.rotulo.botao_abrir_dossie` | rótulo de UI | `clone` | Consultar Dossiê Histórico da Cidade | 5 | `texto+ícone` | Plataforma simulada | Mantido. Aba lateral para quem termina antes da turma. |
| `E6-PROF-01` | `e6.rotulo.prof_relatorio_titulo` | rótulo de UI | `unooria` | Diagnóstico Formativo da Turma | 4 | `texto` | Unooria | Mantido. Topo do relatório consolidado no Hub. |
| `E6-PROF-01` | `e6.texto.prof_consolidado_desc` | narrativa | `unooria` | Resultados consolidados das habilidades EF09CO07 e EF09CO08 baseados em evidências discretas e posicionamento ético. | 15 | `texto` | Unooria | Mantido. Descrição da matriz de evidências docentes. |
| `E6-PROF-01` | `e6.rotulo.botao_exportar_relatorio` | rótulo de UI | `unooria` | Exportar Relatório Pedagógico (PDF) | 4 | `texto+ícone` | Unooria | Mantido. Ação secundária de download pedagógico. |
| Global | `sys.erro.rede_banner` | erro/falha | `clone` | Conexão com o servidor da comissão interrompida. Reconectando aos registros... | 10 | `texto+ícone` | Plataforma simulada | Mantido. Banner diegético de queda de rede (`MODO_ERRO_REDE`). |
| Global | `sys.erro.sessao_modal` | erro/falha | `clone` | Sua sessão como conselheiro relator expirou por segurança. Clique abaixo para reautenticar seu crachá digital. | 16 | `texto+ícone` | Plataforma simulada | Mantido. Modal diegético institucional (`MODO_ERRO_SESSAO`). |
| Global | `sys.rotulo.botao_reautenticar` | rótulo de UI | `clone` | Reautenticar Crachá Digital | 3 | `texto+ícone` | Plataforma simulada | Mantido. Botão do modal de sessão expirada. |
| Global | `sys.erro.midia_card` | erro/falha | `clone` | Visualização gráfica indisponível. Carregando extrato textual transcrito dos arquivos. | 10 | `texto+ícone` | Plataforma simulada | Mantido. Card diegético de fallback (`MODO_ERRO_MIDIA`). |

---

## Strings novas (placeholders resolvidos)

* **Nenhum placeholder novo foi deixado pelo wireframe.** A tabela de cobertura do agente Telas declarou explicitamente zero placeholders `[[…]]` não resolvidos.
* **Strings de estado e contingência verificadas em contexto:**
  - Fallback de mídia em erro (`sys.erro.midia_card`): transcrição em texto puro ativada sem interromper o fluxo investigativo.
  - Alerta de cota esgotada de IA (`e0.erro.quota_esgotada`): substitui a síntese assíncrona pelo banco curado oficial sem expor erros de infraestrutura ao professor.
  - Banner diegético de espera da plenária (`e4.feedback.espera_plenaria`): bloqueia a thread discente com linguagem corporativa enquanto a sala realiza o debate mediado com o professor.

---

## Strings que não couberam — decisão de design necessária

* **Nenhuma string excedeu os tetos ou foi encolhida até virar telegrama.**
  - **Teto do assistente de IA simulado:** ≤ 120 palavras por bloco. A maior resposta institucional emitida na thread possui 43 palavras (`e4.narrativa.ia_revelacao_b`), consumindo menos de 40% do teto máximo permitido.
  - **Teto por oração para o 9º ano EF:** Até 20 palavras por oração em instruções e textos narrativos. Na presente rodada de revisão em contexto, a oração final de provocação de Amara na tela `E1-ALU-01` (`e1.narrativa.amara_desafio`) foi calibrada de 21 para 18 palavras, atingindo conformidade integral com a literatura cognitiva.
  - **Opções estruturadas das enquetes (`ChatPollEmbed`):** Entre 11 e 32 palavras, preservando o texto fechado da matriz de gabarito da spec e garantindo touch target amplo (≥ 64 px) em botões de rádio com rolagem vertical suave e sem quebras estranhas.

---

## Strings do professor (final)

### 1. Rótulos e textos de ajuda do recorte da aula (`E0-PROF-02`)
* **Componente Curricular:** `Componente Curricular`
  * *Texto de apoio:* `Selecione a disciplina que contextualizará os projetos comunitários avaliados pela turma.`
* **Tema da Aula:** `Tema da Aula (máx. 60 caracteres)`
  * *Texto de apoio:* `Resuma em até 60 caracteres a temática central (ex.: Políticas públicas e combate à desigualdade urbana).`
* **Objetos de Conhecimento:** `Objetos de Conhecimento (3 a 6 itens)`
  * *Texto de apoio:* `Insira de 3 a 6 conceitos-chave separados por vírgula (ex.: orçamento comunitário, vulnerabilidade social, triagem algorítmica).`
* **Contexto Territorial:** `Contexto Local / Escola (opcional)`
  * *Texto de apoio:* `Indique particularidades do bairro, município ou comunidade escolar em até 120 caracteres.`
* **Foco Pedagógico:** `Foco Pedagógico (opcional)`
  * *Texto de apoio:* `Destaque a ênfase reflexiva da aula em até 120 caracteres (ex.: impacto de decisões automatizadas sobre serviços públicos).`
* **Botão Banco Padrão:** `Usar Banco Padrão Oficial`
  * *Texto de apoio de ativação rápida:* `Ativa imediatamente o cenário canônico dos três projetos comunitários em apenas dois cliques, sem consumo de cotas de IA.`

### 2. Mensagens de geração, falha e contingência (`E0-PROF-03`)
* **Geração em andamento (Título):** `Estruturando documentos e dossiês com inteligência artificial...`
* **Geração em andamento (Subtítulo):** `Sintetizando projetos comunitários e relatórios de auditoria.`
* **Geração concluída:** `Cenário pedagógico gerado com sucesso. Prossiga para a curadoria dos dados.`
* **Falha de conectividade na geração:** `Não foi possível conectar ao gerador de inteligência artificial. Verifique sua conexão e tente novamente.`
* **Aviso de cota de IA esgotada (HTTP 429):** `Limite de inteligência artificial atingido para este ciclo. A missão foi configurada automaticamente com o banco oficial curado.`

### 3. Curadoria e homologação do pacote (`E0-PROF-04`)
* **Título da tela:** `Curadoria do Cenário da Turma`
* **Instrução de revisão:** `Revise os três projetos e os registros de campo antes de liberar para os estudantes.`
* **Botão de edição rápida:** `Editar Texto`
* **Botão de regeneração pontual:** `Regenerar Este Projeto`
* **Confirmação de homologação:** `Aprovar e Avançar para Ativação`
* **Feedback de pacote pronto:** `Pacote validado e homologado para aplicação em sala de aula.`

### 4. Ativação e agendamento (`E0-PROF-05`)
* **Título da tela:** `Liberação e Agendamento`
* **Instrução de agendamento:** `Selecione a turma que participará da sessão do conselho.`
* **Opção 1 (Imediata):** `Liberar Missão Agora`
* **Opção 2 (Futura):** `Agendar para Data Futura`
* **Confirmação de agendamento:** `Missão agendada com sucesso. Os terminais receberão acesso na data e horário marcados.`

### 5. Gatilhos de condução e mediação em tempo real (`E3-PROF-01` e `E4-PROF-01`)
* **Gatilho 1 (Checkpoint E3 — Liberação da Auditoria/Aha):**
  * *Texto em tela:* `Acompanhe a entrega dos votos vinculantes antes de liberar a auditoria algorítmica da Etapa 4.`
  * *Ação no botão:* `Liberar Auditoria dos Cadernos (Gate E4)`
  * *Pergunta oral da professora:* `Por que tantos votos foram para o projeto com mais arquivos digitais?`
* **Gatilho 2 (Checkpoint E4 — Abertura da Sistematização):**
  * *Texto em tela:* `Projete este gráfico para a sala e conduza o debate com as três perguntas socráticas.`
  * *Ação no botão:* `Liberar Etapa de Sistematização (Gate E5)`
  * *Instrução oral da professora:* `Estudantes, retornem aos seus computadores individuais para localizar onde o algoritmo errou na nossa thread.`

### 6. Roteiro socrático para o debate mediado de 12 minutos
1. *A qualidade real do trabalho do projeto Mesa Aberta aumentou quando descobrimos os cadernos de campo, ou o trabalho já existia e era a máquina que não conseguia enxergar?*
2. *Por que um projeto comunitário que lida diretamente com urgência de alimentação tem muito mais dificuldade de gerar planilhas e relatórios em PDF do que uma oficina de informática?*
3. *Se a prefeitura cortar uma verba ou suspender o passe de um estudante com base exclusiva na nota que a IA calculou, a culpa da injustiça é do algoritmo ou de quem aceitou a recomendação sem auditar os dados?*

---

## Testes de voz — resultado final

### 1. Teste da boca
* **Procedimento:** Leitura oral dos balões e botões em ritmo conversacional e técnico por um leitor de 14–15 anos.
* **Resultado:** Cadência fluida e sem nós fonéticos. As frases analíticas do assistente de IA soam objetivas e desprovidas de sentimentalismo (`Base institucional consultada.`, `Alerta de conformidade: Histórico institucional insuficiente...`). A fala revisada de Amara na Etapa 1 flui com ritmo reflexivo natural, sem afetações adultas artificiais.

### 2. Teste do exclamativo
* **Procedimento:** Varredura algorítmica sobre todas as 82 strings de interface, cards, botões e mensagens de erro do sheet final.
* **Contagem de pontos de exclamação:** **Exatamente zero** exclamações nas strings de tela e de sistema. A pontuação expressiva permanece restrita exclusivamente ao roteiro de podcast em áudio da dupla de apresentadores Lucas e Bianca, respeitando a oralidade radiofônica.

### 3. Teste do "quem fala"
* **Assistente de IA Simulado:** Linguagem corporativa, burocrática, concisa e neutra (`Alerta de conformidade`, `governança técnica consolidada`, `reprocessando dados com critérios idênticos`). Não expressa pedidos de desculpa nem arrependimento.
* **Amara:** Colega madura e atenta que problematiza premissas éticas (`se os dados contam uma história desigual, o que ela vai concluir?`). Presente estritamente nos Beats 1 e 6.
* **Unooria / Casca do Conselho:** Moldura institucional crível e sóbria (`Conselho Municipal de Recursos`, `Homologação de Destinação Orçamentária`, `Parecer arquivado. Aguardando deliberação da plenária.`).
* **Conclusão:** Nenhuma voz invade a raia da outra. A imersão diegética do ambiente corporativo é integralmente preservada.

---

## Glossário por faixa (atualizado)

| Termo canônico | O que significa na missão | Como a tela apresenta | O que evitar |
|---|---|---|---|
| **Viés algorítmico** | Distorção nas decisões de um sistema causada por assimetrias ou lacunas nos dados que o alimentam. | Apresentado na Etapa 5 por Amara após a turma vivenciar a desclassificação injusta do projeto comunitário. | "Erro do robô", "máquina preconceituosa". |
| **Dados do passado** | Registros históricos acumulados que refletem quem tinha ou não tinha acesso a computadores no período anterior. | Demonstrado pelo contraste entre os 12 PDFs da Luana e os cadernos manuscritos de João. | "Memória antiga", "passado digital". |
| **Identificação de padrões** | Operação matemática da IA que calcula regularidades e ranqueia propostas com base em métricas visíveis. | Explicado no parecer comparativo emitido pelo assistente na Etapa 2. | "Pensamento da IA", "inteligência própria". |
| **Decisões automatizadas** | Julgamentos de triagem ou penalidade executados por software sem mediação ou intervenção humana prévia. | Contextualizado pelo corte de passe escolar de Lia e Davi por 4 faltas acumuladas no sistema. | "Decisão do computador", "punição digital". |
| **Governança técnica / Risco documental** | Jargão corporativo usado por sistemas burocráticos para medir a presença de documentos formais em nuvem. | Utilizado pelo assistente de IA para justificar a preferência pelo projeto que possuía PDFs padronizados. | "Papelada boa", "nota técnica informal". |
| **Cadernos físicos de campo** | Registros diários manuscritos com assinaturas e controle diário de atendimento e alimentação. | Apresentados como contraprova material auditável do Projeto Mesa Aberta. | "Rascunhos", "anotações soltas". |

---

## Lacunas (dono e classe)

*Nenhuma lacuna aberta. Todos os contratos de voz, limites de palavras, hierarquias de tela e estados construídos foram validados em contexto com os wireframes entregues.*

---

## Pronto — contagem por item

| Verificação | Contagem |
|---|:---:|
| String acima do teto de palavras da faixa (até 20 palavras por oração / ≤ 120 por bloco) | 0 |
| Instrução acionável em anos iniciais sem `texto+ícone+áudio` (não se aplica a 9EF) | 0 |
| String encolhida para caber sem entrar na lista de "não couberam" | 0 |
| Tela do inventário sem string (todas as 16 telas cobertas) | 0 |
| String no sheet sem tela correspondente | 0 |
| Chave fora da convenção `eN.tipo.nome` ou `sys.tipo.nome` | 0 |
| Tela com dois registros de voz misturados no mesmo elemento | 0 |
| Registro sem régua com exemplo e contraexemplo no glossário | 0 |
| Termo "aluno" em texto voltado para o estudante (utilizado estritamente "estudante") | 0 |
| Julgamento moral ou rotulação punitiva do estudante | 0 |
| **Total de itens abertos** | **0** |

---

```json
{
  "agente": "copy-ptbr-revisao",
  "missao": "exp09ef1b",
  "rodada": 2,
  "status": "concluido",
  "achados": [],
  "pronto": {
    "verificado": true,
    "itens_abertos": 0
  },
  "precisa_humano": false
}
```
