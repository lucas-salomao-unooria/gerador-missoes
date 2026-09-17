<!-- CÓPIA SINCRONIZADA de plataforma-unooria@29afc8f (2026-09-16) · origem: apps/api/prisma/schema.prisma · não edite: rode scripts/sincronizar_plataforma.py · placeholders entre chaves aparecem como «nome» por limitação de interpolação do ADK; no código real use chaves -->

# `apps/api/prisma/schema.prisma` — só os modelos das missões-molde (exp-04, exp-06, exp-07, exp-08)

16 modelos. Padrões a imitar: `@@map("exp_NN_…")`, `escola_id` em toda tabela sob RLS, PK composta da sessão, `turma_id` denormalizado, `versao_instrumento`, `tentativa`, estado como string (CHECK na migration, nunca enum), texto livre de menor em tabela própria com `chars_count`.

```prisma
/// Estado server-side da exp-07-o-eco-no-grupo (uma linha por estudante).
///
/// `passo` é o que o SERVIDOR precisa saber para reidratar a missão depois de um
/// F5 — não o estado de tela. Modal aberto, cutucão de ociosidade e os 7s da
/// cascata são do cliente: gravá-los aqui faria o servidor herdar o vocabulário
/// da interface e mudar de schema a cada ajuste de layout.
///
/// O gabarito (qual das 3 opções é a checada) NÃO está aqui nem em coluna
/// nenhuma: mora em `src/o-eco-no-grupo/catalogo.ts` e é aplicado por
/// `regras/` (regra inviolável nº 3). CHECKs e RLS vivem na migration.
model EcoSessao {
  escolaId    String  @map("escola_id")
  estudanteId String  @map("estudante_id") @db.Uuid
  /// Denormalizado da identidade, como na exp-03: o painel do professor e o
  /// gate da turma consultam por turma o tempo todo.
  turmaId     String? @map("turma_id") @db.Uuid

  /// chat_amara | grupo | breakpoint | podcast | intervencao | desfecho |
  /// sintese | reflexao | fim (CHECK na migration; ordem em `regras/passos.ts`).
  passo String @default("chat_amara")

  /// A evidência que a missão MEDE (BNCC EF07CO01): o estudante abriu a matéria
  /// íntegra antes de responder? É `indicative`, não nota — mas é a condição de
  /// enviar a intervenção, e por isso é coluna e não derivado.
  inspecionouMateria Boolean @default(false) @map("inspecionou_materia")
  /// O áudio da moradora chegou a 100%. Também `indicative`.
  ouviuAudio         Boolean @default(false) @map("ouviu_audio")
  /// O podcast de recapitulação chegou a 100% — é o que destrava a decisão.
  ouviuPodcast       Boolean @default(false) @map("ouviu_podcast")
  /// Quantos dos 3 cards de sistematização já foram lidos.
  cardsLidos         Int     @default(0) @map("cards_lidos") @db.SmallInt

  /// A | B | C (CHECK na migration). Null = ainda não respondeu.
  opcao         String?
  /// Segundos entre abrir o menu de intervenção e enviar. Distingue impulso de
  /// reflexão, e é do estudante, não do modelo: o cliente cronometra o próprio
  /// tempo de decisão porque a latência da api não é o dado.
  latenciaSeg   Int?    @map("latencia_seg")
  /// Quantas vezes usou "Apagar para todos". Recuperação formativa não é
  /// punição — o contador existe para o professor ver quem se corrigiu.
  desfazerUsado Int     @default(0) @map("desfazer_usado") @db.SmallInt
  /// 100 se inspecionou e acertou de primeira, 70 após recuperação, 0 sem
  /// intervenção correta. Calculado em `regras/pontuacao.ts`, nunca aceito do
  /// cliente. Null = a missão ainda não fechou.
  score         Int?

  /// As 3 reações que o grupo deu à intervenção, como saíram do modelo. Ficam
  /// gravadas para o F5 devolver a MESMA cena: regerar mostraria o bairro
  /// reagindo de outro jeito à mesma mensagem, e a cascata perderia a causa.
  /// Null = caiu no roteiro do catálogo (a IA falhou ou está desligada).
  reacoes Json?

  /// Quantas vezes o estudante já falou com Amara no privado. Ela é amiga, não
  /// assistente: uma conversa infinita viraria o centro da missão, e o centro é
  /// o que aconteceu no grupo.
  turnosAmara Int @default(0) @map("turnos_amara") @db.SmallInt

  /// Teto de custo por sessão, no espírito da exp-03: soma o que foi PAGO
  /// (reações, conversa com Amara, devolutiva), não o aproveitado.
  tokensGastos Int @default(0) @map("tokens_gastos")
  chamadasIa   Int @default(0) @map("chamadas_ia")

  criadoEm     DateTime  @default(now()) @map("criado_em") @db.Timestamptz(6)
  atualizadoEm DateTime  @default(now()) @updatedAt @map("atualizado_em") @db.Timestamptz(6)
  concluidoEm  DateTime? @map("concluido_em") @db.Timestamptz(6)

  estudante User          @relation("EcoEstudante", fields: [estudanteId], references: [id], onDelete: Cascade)
  mensagens EcoMensagem[]
  reflexoes EcoReflexao[]

  @@id([escolaId, estudanteId])
  @@index([escolaId])
  @@index([escolaId, turmaId])
  @@map("exp_07_sessoes")
}

/// A conversa com Amara, DEPOIS da decisão no grupo.
///
/// `texto` é caixa livre escrita por menor de idade — o dado mais sensível desta
/// experiência, e a razão da ADR que reabriu essa porta. Ele nunca vai a log,
/// nunca à telemetria e nenhuma rota de gestor o alcança. O silêncio de Amara na
/// investigação é não-negociável: nada aqui existe antes do `passo` `desfecho`.
model EcoMensagem {
  id          BigInt   @id @default(autoincrement())
  escolaId    String   @map("escola_id")
  estudanteId String   @map("estudante_id") @db.Uuid
  /// estudante | amara (CHECK na migration).
  papel       String
  texto       String
  criadoEm    DateTime @default(now()) @map("criado_em") @db.Timestamptz(6)

  sessao EcoSessao @relation(fields: [escolaId, estudanteId], references: [escolaId, estudanteId], onDelete: Cascade)

  /// Paginação por id é estável; por timestamp não.
  @@index([escolaId, estudanteId, id])
  @@map("exp_07_mensagens")
}

/// O "Meu percurso" — 2 estratégias de checagem e 1 justificativa, todas de
/// lista fechada. Zero texto livre aqui de propósito: este é o instrumento que
/// vira portfólio, e ele não precisa de redação para medir critério de checagem.
///
/// `devolutiva` é o comentário formativo escrito pelo modelo sobre as escolhas.
/// Não é nota e não entra no `score`: quem pontua são as regras puras.
model EcoReflexao {
  escolaId      String   @map("escola_id")
  estudanteId   String   @map("estudante_id") @db.Uuid
  /// Exatamente 2 ids de `catalogo.ts` (CHECK de cardinalidade na migration).
  estrategias   String[] @default([])
  justificativa String
  devolutiva    String?
  criadoEm      DateTime @default(now()) @map("criado_em") @db.Timestamptz(6)

  sessao EcoSessao @relation(fields: [escolaId, estudanteId], references: [escolaId, estudanteId], onDelete: Cascade)

  @@id([escolaId, estudanteId])
  @@index([escolaId])
  @@map("exp_07_reflexoes")
}

/// O GATE DA AULA — por TURMA, e é o que deixa a professora conduzir 30 telas.
///
/// Mesmo espírito do relógio da exp-03, mas a escassez aqui não é tempo: é
/// ETAPA. A Aula 1 fecha num breakpoint que só ela abre, o debate CONGELA a
/// turma na mesma tela (a conversa é entre pares) e a reflexão é liberada depois.
/// A reconciliação entre esta etapa e o passo de cada estudante é função pura
/// (`regras/passos.ts`), porque a api e o cliente precisam chegar à mesma
/// resposta — duas implementações divergentes seriam a tela discordando do
/// servidor.
model EcoGateTurma {
  escolaId String @map("escola_id")
  turmaId  String @map("turma_id") @db.Uuid

  /// investigacao | aula2 | debate | reflexao (CHECK na migration).
  etapa String @default("investigacao")

  atualizadoEm DateTime @default(now()) @updatedAt @map("atualizado_em") @db.Timestamptz(6)

  turma Turma @relation(fields: [turmaId], references: [id], onDelete: Cascade)

  @@id([escolaId, turmaId])
  @@index([escolaId])
  @@map("exp_07_gates_turma")
}

/// A sessão do estudante na missão. Uma por estudante e por escola.
model RastroSessao {
  escolaId    String  @map("escola_id")
  estudanteId String  @map("estudante_id") @db.Uuid
  /// Denormalizado da identidade, como na exp-07: o painel e o gate da turma
  /// consultam por turma o tempo todo.
  turmaId     String? @map("turma_id") @db.Uuid

  /// contexto | chats | decisao | breakpoint | resultado | ciclo | percurso |
  /// fim (CHECK na migration; a ordem é `regras/passos.ts`).
  passo String @default("contexto")

  /// A | B | C (CHECK na migration). Null = ainda não decidiu.
  opcao          String?
  /// Segundos entre a crise chegar e o envio. Distingue impulso de reflexão, e
  /// é cronometrado pelo CLIENTE: a latência da api não é o dado.
  latenciaSeg    Int?    @map("latencia_seg")
  /// O alerta de inação de 90s chegou a aparecer? É `indicative` e alimenta a
  /// hipótese H3 do playtest — nunca entra no nível.
  houveInacao90s Boolean @default(false) @map("houve_inacao_90s")

  /// A sequência dos 4 blocos como o estudante a montou. Vazio = ainda não
  /// confirmou. Guardar a ordem BRUTA, e não só o booleano, é o que deixa
  /// reprocessar a leitura pedagógica numa versão futura do instrumento.
  ordemBlocos String[] @default([]) @map("ordem_blocos")
  /// A sequência descreve o ciclo? Calculado em `regras/ciclo.ts`, nunca aceito
  /// do cliente. Null = ainda não confirmou.
  coerente    Boolean? @map("coerente")

  /// 0 / 70 / 100, de `regras/pontuacao.ts`. NÃO é nota e não aparece em tela
  /// nenhuma: existe porque o `exp:concluir` da bridge tem o campo e o
  /// progresso da plataforma o lê. Null = a missão ainda não fechou.
  score Int?

  /// A versão do instrumento, gravada na linha para permitir reprocessamento
  /// histórico quando o catálogo mudar (DAD-06).
  versaoInstrumento String @default("1.0.0") @map("versao_instrumento")

  criadoEm     DateTime  @default(now()) @map("criado_em") @db.Timestamptz(6)
  atualizadoEm DateTime  @default(now()) @updatedAt @map("atualizado_em") @db.Timestamptz(6)
  concluidoEm  DateTime? @map("concluido_em") @db.Timestamptz(6)

  estudante  User              @relation("RastroEstudante", fields: [estudanteId], references: [id], onDelete: Cascade)
  auditorias RastroAuditoria[]
  reflexoes  RastroReflexao[]

  @@id([escolaId, estudanteId])
  @@index([escolaId])
  @@index([escolaId, turmaId])
  @@map("exp_06_sessoes")
}

/// Cada abertura do modal "Dados da mensagem".
///
/// É a evidência que a missão MEDE (EF06CO01), e é 1:N de propósito: a cota de
/// 3 é sobre mensagens DISTINTAS, e guardar só um contador perderia QUAIS o
/// estudante escolheu auditar — que é o dado pedagógico. A dedupe é do
/// servidor (`regras/auditoria.ts`), reforçada pelo UNIQUE abaixo.
model RastroAuditoria {
  id            BigInt   @id @default(autoincrement())
  escolaId      String   @map("escola_id")
  estudanteId   String   @map("estudante_id") @db.Uuid
  /// Id do catálogo (`msg-boato-01`…). Validado contra ele antes de gravar.
  mensagemId    String   @map("mensagem_id")
  chatId        String   @map("chat_id")
  /// Segundos com o modal aberto. Calibragem de fluxo, não medida de mérito.
  tempoLeituraS Int      @default(0) @map("tempo_leitura_s")
  criadoEm      DateTime @default(now()) @map("criado_em") @db.Timestamptz(6)

  sessao RastroSessao @relation(fields: [escolaId, estudanteId], references: [escolaId, estudanteId], onDelete: Cascade)

  /// Reabrir o mesmo balão é releitura, não auditoria nova: o UNIQUE faz a
  /// dedupe valer mesmo se um caminho novo esquecer de checar antes.
  @@unique([escolaId, estudanteId, mensagemId])
  @@index([escolaId, estudanteId])
  @@map("exp_06_auditorias")
}

/// O "Meu percurso" — a reflexão metacognitiva de até 280 caracteres.
///
/// **Texto livre escrito por menor de idade**, e o dado mais sensível daqui.
/// Nunca vai a log, nunca à telemetria analítica (o Pub/Sub leva números e
/// enums), e nenhuma rota de gestor o alcança: quem lê é o professor da turma
/// dela. LGPD art. 14 + `invariantes.ts`.
model RastroReflexao {
  escolaId    String   @map("escola_id")
  estudanteId String   @map("estudante_id") @db.Uuid
  texto       String   @db.VarChar(280)
  charsCount  Int      @map("chars_count")
  criadoEm    DateTime @default(now()) @map("criado_em") @db.Timestamptz(6)

  sessao RastroSessao @relation(fields: [escolaId, estudanteId], references: [escolaId, estudanteId], onDelete: Cascade)

  @@id([escolaId, estudanteId])
  @@index([escolaId])
  @@map("exp_06_reflexoes")
}

/// O GATE DA AULA — por TURMA. É o que deixa a professora conduzir 30 telas.
///
/// Duas etapas só (`regras/passos.ts`): a Aula 1 fecha num breakpoint que só
/// ela abre, e "Pausar simulação" volta. A reconciliação entre esta etapa e o
/// passo de cada estudante é função pura, porque a api e o cliente precisam
/// chegar à mesma resposta.
model RastroGateTurma {
  escolaId String @map("escola_id")
  turmaId  String @map("turma_id") @db.Uuid

  /// aula1 | aula2 (CHECK na migration).
  etapa String @default("aula1")

  atualizadoEm DateTime @default(now()) @updatedAt @map("atualizado_em") @db.Timestamptz(6)

  turma Turma @relation(fields: [turmaId], references: [id], onDelete: Cascade)

  @@id([escolaId, turmaId])
  @@index([escolaId])
  @@map("exp_06_gates_turma")
}

/// O PACOTE CURADO DA TURMA — o que a professora homologa antes da aula.
///
/// Uma linha por turma. `aprovado_por_professor` é o portão da exigência 8.2:
/// sem ele `true`, a missão do estudante lê o banco curado default da Unooria
/// (`src/manifesto-ia/catalogo.ts`) e a aula corre igual. **Nunca** o conteúdo
/// gerado por IA em rascunho — é essa a diferença entre curadoria e
/// publicação automática.
///
/// Sobrevive ao "Zerar turma": o preparo custou tempo da professora, e apagá-lo
/// junto com as respostas obrigaria a refazer a curadoria para reaplicar a
/// missão numa segunda turma no mesmo dia.
model Exp08ConteudoTurma {
  escolaId String @map("escola_id")
  turmaId  String @map("turma_id") @db.Uuid

  /// O caso da escola, como a professora o descreveu no formulário.
  casoContextual  String @map("caso_contextual")
  focoPrioritario String @map("foco_prioritario")

  /// Os 3 prompts de auditoria COM as réplicas da máquina, e as 4 cláusulas COM
  /// as justificativas de mediação. `Json` e não tabelas-filhas porque o pacote
  /// é lido e escrito SEMPRE inteiro — a professora aprova o conjunto, não um
  /// prompt de cada vez —, e normalizá-lo produziria sete linhas com uma FK
  /// cada para nada. O Zod de `contrato-de-rotas.ts` é o schema real (o Prisma
  /// não valida forma de Json), e o CHECK da migration cobra a cardinalidade.
  contexto      Json @map("contexto")
  promptsJson   Json @map("prompts_json")
  clausulasJson Json @map("clausulas_json")

  /// O clique formal em "Aprovar Conteúdo da Turma". Falso = rascunho.
  aprovadoPorProfessor Boolean @default(false) @map("aprovado_por_professor")
  /// A professora manteve o pacote da Unooria em vez de gerar com IA? É o dado
  /// que diz se a curadoria assistida está sendo usada — e a resposta "não"
  /// não é problema: o banco default é homologado, não é fallback de erro.
  usouBancoDefault     Boolean @default(false) @map("usou_banco_default")

  criadoEm     DateTime @default(now()) @map("criado_em") @db.Timestamptz(6)
  atualizadoEm DateTime @default(now()) @updatedAt @map("atualizado_em") @db.Timestamptz(6)

  turma Turma @relation(fields: [turmaId], references: [id], onDelete: Cascade)

  @@id([escolaId, turmaId])
  @@index([escolaId])
  @@map("exp_08_conteudo_turma")
}

/// A sessão do estudante na missão. Uma por estudante e por escola.
model Exp08Sessao {
  escolaId    String  @map("escola_id")
  estudanteId String  @map("estudante_id") @db.Uuid
  /// Denormalizado da identidade, como na exp-06: o painel e o gate da turma
  /// consultam por turma o tempo todo.
  turmaId     String? @map("turma_id") @db.Uuid

  /// briefing | chat | decisao | manifesto | percurso | podcast | fim
  /// (CHECK na migration; a ordem é `regras/passos.ts`).
  passo String @default("briefing")

  /// A cláusula fixada na Etapa 3 — LATCH. Null = ainda não decidiu.
  clausulaId          String? @map("clausula_id")
  /// Segundos entre a concessão da máquina e a submissão. Distingue impulso de
  /// deliberação, e é cronometrado pelo CLIENTE: a latência da api não é o dado.
  latenciaClausulaSeg Int?    @map("latencia_clausula_seg")
  /// A criança clicou em menos de 5s e passou pela réplica provocativa do bot?
  /// É `indicative` e alimenta a hipótese de exploração mínima do playtest —
  /// nunca entra em avaliação de ninguém.
  confirmouProvocacao Boolean @default(false) @map("confirmou_provocacao")

  /// O documento promulgado, compilado no SERVIDOR (`regras/manifesto.ts`).
  /// Gravado porque é a EVIDÊNCIA do percurso: o que a professora lê no painel
  /// e o que o estudante copiou têm de ser o mesmo texto, e uma recompilação
  /// futura com a copy revisada mudaria o documento que já foi assinado.
  manifestoMarkdown String? @map("manifesto_markdown")

  /// A versão do instrumento, na linha, para permitir reprocessamento histórico
  /// quando o catálogo mudar (DAD-06).
  versaoInstrumento String @default("1.0.0") @map("versao_instrumento")

  criadoEm     DateTime  @default(now()) @map("criado_em") @db.Timestamptz(6)
  atualizadoEm DateTime  @default(now()) @updatedAt @map("atualizado_em") @db.Timestamptz(6)
  concluidoEm  DateTime? @map("concluido_em") @db.Timestamptz(6)

  estudante  User             @relation("Exp08Estudante", fields: [estudanteId], references: [id], onDelete: Cascade)
  auditorias Exp08Auditoria[]
  percursos  Exp08Percurso[]

  @@id([escolaId, estudanteId])
  @@index([escolaId])
  @@index([escolaId, turmaId])
  @@map("exp_08_sessoes")
}

/// Cada questionamento disparado contra a máquina na Etapa 2.
///
/// 1:N de propósito: a cota de 2 é sobre prompts DISTINTOS, e guardar só o
/// contador perderia QUAIS a criança escolheu — que é o dado da hipótese
/// pedagógica (a contradição só aparece no prompt do preconceito histórico).
model Exp08Auditoria {
  id          BigInt @id @default(autoincrement())
  escolaId    String @map("escola_id")
  estudanteId String @map("estudante_id") @db.Uuid
  /// Id do catálogo (`prompt_origem_dados`…), validado contra o pacote da
  /// turma antes de gravar.
  promptId    String @map("prompt_id")
  /// Ordem do disparo na conversa: 1 e 2 são os obrigatórios, 3 é o extra de
  /// quem quis ouvir a terceira defesa.
  iteracao    Int
  /// Segundos entre o seletor abrir e o envio. Calibragem de fluxo, não mérito.
  latenciaSeg Int    @default(0) @map("latencia_seg")

  criadoEm DateTime @default(now()) @map("criado_em") @db.Timestamptz(6)

  sessao Exp08Sessao @relation(fields: [escolaId, estudanteId], references: [escolaId, estudanteId], onDelete: Cascade)

  /// Reenviar o mesmo questionamento não é auditoria nova: o UNIQUE faz a
  /// dedupe valer mesmo se um caminho novo esquecer de checar antes.
  @@unique([escolaId, estudanteId, promptId])
  @@index([escolaId, estudanteId])
  @@map("exp_08_auditorias")
}

/// O "MEU PERCURSO" — as 2 palavras-chave e o parágrafo autoral da Etapa 5.
///
/// **Texto livre escrito por menor de idade**, e o dado mais sensível daqui.
/// Nunca vai a log (`justificativaTexto` está em `CHAVES_REDIGIDAS`), nunca à
/// telemetria analítica (o Pub/Sub leva números e enums), e nenhuma rota de
/// gestor o alcança: quem lê é o professor da turma dela. LGPD art. 14 +
/// `invariantes.ts`.
///
/// RETENÇÃO: vinculada à vigência contratual escolar, **sem rotina ativa de
/// expurgo programado** (DAD-10). A frase é literal e a escolha é deliberada:
/// não existe scheduler de expurgo na plataforma, e declarar "um ano letivo"
/// aqui seria escrever um prazo que ninguém cumpre — a armadilha do
/// `expires_at` que o `AGENTS.md` da raiz cita.
model Exp08Percurso {
  escolaId    String @map("escola_id")
  estudanteId String @map("estudante_id") @db.Uuid

  /// Exatamente 2, distintas (CHECK na migration). São ids minúsculos sem
  /// acento — identificador, não texto de tela (ADR-91).
  tags String[] @map("palavras_chave_tags")

  /// O parágrafo. Passou pelo filtro de dado pessoal ANTES de chegar aqui: o
  /// que casa o regex é RECUSADO com 422 e não gravado, então esta coluna não
  /// tem flag de moderação — não há registro moderado a marcar.
  justificativaTexto String @map("justificativa_texto") @db.Text
  charsCount         Int    @map("chars_count")

  versaoInstrumento String @default("1.0.0") @map("versao_instrumento")

  criadoEm DateTime @default(now()) @map("criado_em") @db.Timestamptz(6)

  sessao Exp08Sessao @relation(fields: [escolaId, estudanteId], references: [escolaId, estudanteId], onDelete: Cascade)

  @@id([escolaId, estudanteId])
  @@index([escolaId])
  @@map("exp_08_respostas_percurso")
}

/// O CHECKPOINT A — por TURMA. É o que congela 30 telas para o debate oral.
///
/// **Tabela, e não WebSocket** (ADR-93). A infraestrutura Cloud Run da
/// plataforma não tem WebSocket de aplicação: o handoff original previa um
/// broadcast `hub:pause`, e ele não existe. O congelamento é uma LINHA aqui que
/// a tela do estudante lê por polling HTTP de 5s (`GET /manifesto-ia/gate`).
///
/// Duas etapas só (`regras/passos.ts`): `missao` e `debate`. E, diferente da
/// exp-06, o gate é OPCIONAL — a missão corre inteira sem ninguém apertar nada,
/// porque a spec admite a sessão assíncrona individual. Por isso `debate` mexe
/// só no TETO do passo, nunca no piso: subir o piso empurraria para a frente
/// quem ainda estava auditando a máquina, e são justamente essas crianças que o
/// debate tenta alcançar.
model Exp08GateTurma {
  escolaId String @map("escola_id")
  turmaId  String @map("turma_id") @db.Uuid

  /// missao | debate (CHECK na migration).
  etapa String @default("missao")

  atualizadoEm DateTime @default(now()) @updatedAt @map("atualizado_em") @db.Timestamptz(6)

  turma Turma @relation(fields: [turmaId], references: [id], onDelete: Cascade)

  @@id([escolaId, turmaId])
  @@index([escolaId])
  @@map("exp_08_gates_turma")
}

/// A configuração da aula, POR TURMA: o pacote de fotos/legendas (gerado por IA
/// e aprovado pelo professor, ou o banco curado padrão quando `pacote` é null)
/// e o interruptor do latch da Roda de Conversa.
///
/// `tentativa` é a rotação de sessão do "Zerar e Reiniciar Turma": o reset
/// incrementa o número em vez de apagar runs — as antigas ficam arquivadas na
/// tentativa anterior (DAD-06: dado legado imutável), e a run ativa é sempre a
/// da tentativa corrente.
model FotoContaTurmaConfig {
  escolaId String @map("escola_id")
  turmaId  String @map("turma_id") @db.Uuid

  /// recreio | nossa_horta | sala_de_aula | parquinho (CHECK na migration).
  tema String @default("recreio")
  /// nivel_1 (palavras curtas) | nivel_2 (frases simples) (CHECK na migration).
  complexidade String @default("nivel_1")
  /// pendente | pronto (CHECK). `pronto` = o professor aprovou (o
  /// `cfg_turma_ready` da spec); sem aprovação até a aula, o banco padrão vale.
  statusPacote String @default("pendente") @map("status_pacote")
  /// O pacote APROVADO (validado por `PacoteDaTurmaSchema`). Null = banco
  /// curado padrão do `catalogo.ts` — o fallback que nunca deixa a aula sem
  /// material.
  pacote Json?
  /// Se o pacote aprovado veio da IA (auditoria do painel; o professor pode
  /// ter editado os textos antes de aprovar).
  pacoteDaIa Boolean @default(false) @map("pacote_da_ia")

  /// O latch da Etapa 5 (Roda de Conversa). `false` congela os tablets da
  /// turma; o professor libera UMA vez por aula (o reset o rearma).
  latchLiberado Boolean @default(false) @map("latch_liberado")

  tentativa Int @default(1) @db.SmallInt

  criadoEm     DateTime @default(now()) @map("criado_em") @db.Timestamptz(6)
  atualizadoEm DateTime @default(now()) @updatedAt @map("atualizado_em") @db.Timestamptz(6)

  turma Turma @relation(fields: [turmaId], references: [id], onDelete: Cascade)

  @@id([escolaId, turmaId])
  @@index([escolaId])
  @@map("exp_04_turma_config")
}

/// A execução de UM estudante em UMA tentativa da turma.
///
/// Payloads de tempo real e telemetria carregam SÓ `estudante_id` (regra 6 /
/// DAD-07): o nome entra na resposta do painel do professor, hidratado na rota
/// autenticada pela matrícula da turma — nunca gravado aqui.
model FotoContaRun {
  id          String @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  escolaId    String @map("escola_id")
  turmaId     String @map("turma_id") @db.Uuid
  estudanteId String @map("estudante_id") @db.Uuid
  tentativa   Int    @default(1) @db.SmallInt

  /// desafiar | feed | decidir | aha | roda | refletir | concluida (CHECK).
  /// `roda` é o latch: a run só sai dele quando o professor libera a turma.
  etapa String @default("desafiar")

  /// coruja | estrela | sol (CHECK) — a "marca" da Etapa 1 (cosmético).
  marcaId String? @map("marca_id")
  /// Id da foto escolhida no pacote (ex.: `par_a`, `par_b`).
  fotoEscolhidaId String? @map("foto_escolhida_id") @db.VarChar(30)
  /// Id da legenda escolhida no pacote (`legenda_1`, `legenda_2`).
  legendaEscolhidaId String? @map("legenda_escolhida_id") @db.VarChar(30)
  /// Milissegundos entre entrar na tela de decisão e publicar. Teto de 2h no
  /// CHECK: acima disso é aba esquecida, não tempo de decisão.
  latenciaDecisaoMs Int? @map("latencia_decisao_ms")

  /// Exploração do feed (grau `none`: cosmético/motor, sem peso avaliativo).
  curtidasFeed     Int @default(0) @map("curtidas_feed") @db.SmallInt
  permanenciaFeedMs Int @default(0) @map("permanencia_feed_ms")

  /// `lupa` (CHECK) — só a resposta que CONCLUI é gravada; o Globo é retry
  /// formativo e vive em `tentativas_reflexao`, nunca como resposta final.
  reflexaoFinal      String? @map("reflexao_final")
  tentativasReflexao Int     @default(0) @map("tentativas_reflexao") @db.SmallInt

  versaoInstrumento String @default("1.0.0") @map("versao_instrumento")

  criadoEm     DateTime  @default(now()) @map("criado_em") @db.Timestamptz(6)
  atualizadoEm DateTime  @default(now()) @updatedAt @map("atualizado_em") @db.Timestamptz(6)
  concluidoEm  DateTime? @map("concluido_em") @db.Timestamptz(6)

  estudante User               @relation("FotoContaEstudante", fields: [estudanteId], references: [id], onDelete: Cascade)
  post      FotoContaPostTurma?

  @@unique([escolaId, turmaId, estudanteId, tentativa], map: "exp_04_run_unica_por_tentativa")
  @@index([escolaId, turmaId, tentativa])
  @@map("exp_04_runs")
}

/// A publicação no mural coletivo — o que a Galeria da Turma mostra.
///
/// Carrega o CONTEÚDO renderizável (ids do pacote + texto da legenda) e nunca
/// o nome da criança: quem assina o post na tela é a MARCA (coruja/estrela/
/// sol), que é a identidade da ficção.
model FotoContaPostTurma {
  id       String @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  runId    String @unique @map("run_id") @db.Uuid
  escolaId String @map("escola_id")
  turmaId  String @map("turma_id") @db.Uuid
  tentativa Int   @default(1) @db.SmallInt

  marcaId        String @map("marca_id")
  fotoId         String @map("foto_id") @db.VarChar(30)
  legendaTexto   String @map("legenda_texto") @db.VarChar(100)
  curtidasSimuladas Int @default(0) @map("curtidas_simuladas")

  criadoEm DateTime @default(now()) @map("criado_em") @db.Timestamptz(6)

  run FotoContaRun @relation(fields: [runId], references: [id], onDelete: Cascade)

  @@index([escolaId, turmaId, tentativa])
  @@map("exp_04_posts_turma")
}
```
