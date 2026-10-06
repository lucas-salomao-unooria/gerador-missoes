<!-- CÓPIA de plataforma-unooria@89e0f9ae (2026-10-06) · origem: apps/api/prisma/schema.prisma · não edite -->

# `apps/api/prisma/schema.prisma` — só os modelos das missões-molde e das tabelas de plataforma que elas usam

13 modelos: `exp06ef1b_*` (O Júri Estadual), `exp07ef1b_*` (A Seleção), `evidencias*` e `equipes*`.

Padrões a imitar numa missão nova:

- **Prefixo é o CÓDIGO da experiência** (`@@map("exp06ef1b_…")`, ADR-110); tabela que serve a todas (`evidencias`, `equipes`, `liberacoes`) fica sem prefixo.
- **`escola_id` em toda tabela, sob RLS** (`ENABLE` + `FORCE ROW LEVEL SECURITY` e a policy `escola_id = current_setting('app.escola_id', true)`), escrita no bloco MANUAL da migration — o Prisma não gera CHECK, índice parcial, RLS nem GRANT. `turma_id` vai denormalizado.
- **A atividade é do professor, por turma** (ADR-130): o pacote (`exp06ef1b_pacotes`) ou a cobertura (`exp07ef1b_coberturas`) que ele homologa, com `ativo`, `criado_por` sem FK e o conteúdo em `Json` validado pelo Zod do `contrato-de-rotas.ts` (o CHECK cobra só a forma).
- **O gate da turma** (`<código>_gates_turma`, PK `turma_id`) diz qual atividade e qual RODADA estão em andamento. "Zerar a turma" soma 1 na rodada — nunca apaga sessão.
- **Sessão por (atividade, rodada, estudante)**, com `@@unique` nomeado à mão (`map:`; o nome gerado passa de 63 caracteres e o Postgres o corta em silêncio). A rodada anterior fica imutável: é ela que o painel de habilidades lê (vale a melhor rodada).
- **Estado como `String` com CHECK na migration, nunca `enum`**: passo, etapa e vocabulários; cada latch (carimbo + valores) é amarrado por CHECK ao passo gravado.
- Contadores de `tentativas`, `versao_instrumento` para reprocessamento, e **texto livre de menor em tabela própria** (`exp07ef1b_reflexoes`, com `chars` = `char_length(texto)` no CHECK), lida só por quem leciona.
- A missão não grava nível em tabela própria: chama `EvidenciasService.marcar` com a ficha registrada (`evidencias_marcas`), e a equipe é da atividade (`equipes_*`).

```prisma
/// Um PACOTE — a mostra da aula: as quatro áreas e os dezesseis projetos,
/// gerados por IA e homologados pelo professor. É a atividade.
///
/// Um ATIVO (= EM ANDAMENTO) por turma: índice único parcial na migration.
/// Nasce PRONTO (`ativo = false`, ADR-130): quem põe no ar é o professor.
model Exp06ef1bPacote {
  id         String  @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  escolaId   String  @map("escola_id")
  turmaId    String  @map("turma_id") @db.Uuid
  /// ia (CHECK). A missão não tem acervo padrão.
  origem     String
  /// O slug de `juri-estadual/vocabulario.ts#DISCIPLINAS` (CHECK).
  disciplina String
  /// O tema da mostra como o estudante o lê (o `conteudo.tema`).
  tema       String
  /// Os assuntos que o professor deu ao gerador (de 10 a 600 caracteres).
  assuntos   String
  /// O contexto opcional da turma (até 120 caracteres).
  contexto   String?

  /// As quatro categorias e os dezesseis projetos. `Json` porque o pacote é
  /// lido e escrito sempre inteiro; o schema real é o Zod de
  /// `juri-estadual/contrato-de-rotas.ts#ConteudoDoPacoteSchema`, e o CHECK
  /// cobra a forma (4 categorias, 16 projetos).
  conteudo Json

  /// As URLs das imagens geradas, por id de projeto (`{ "proj-a1": url }`).
  midia Json @default("{}")

  ativo Boolean @default(false)

  /// Quem homologou. Carimbo sem FK, como `exp07ef1b_coberturas.aprovada_por`:
  /// a saída de um professor da rede não pode travar a atividade da turma.
  criadoPor String @map("criado_por") @db.Uuid

  criadoEm     DateTime @default(now()) @map("criado_em") @db.Timestamptz(6)
  atualizadoEm DateTime @default(now()) @updatedAt @map("atualizado_em") @db.Timestamptz(6)

  /// As gerações de rascunho feitas com este pacote em sala (o rascunho não
  /// persiste, e a turma é o que se mede) e o que custaram.
  iaGeracoes Int @default(0) @map("ia_geracoes")
  iaTokens   Int @default(0) @map("ia_tokens")

  turma   Turma                @relation(fields: [turmaId], references: [id], onDelete: Cascade)
  gates   Exp06ef1bGateTurma[]
  sessoes Exp06ef1bSessao[]

  @@index([escolaId, turmaId], map: "exp06ef1b_pacotes_escola_turma_idx")
  @@map("exp06ef1b_pacotes")
}

/// O RELÓGIO DA TURMA — o botão único do painel ("Liberar a Galeria Oculta"),
/// lido por polling de 3 s.
///
/// Diz QUAL atividade e QUAL rodada estão em andamento: a sessão do estudante é
/// a de (pacote, rodada) deste gate, e o resolvedor da evidência só aceita
/// resposta das enquetes dessa sessão.
model Exp06ef1bGateTurma {
  turmaId  String @id @map("turma_id") @db.Uuid
  escolaId String @map("escola_id")
  pacoteId String @map("pacote_id") @db.Uuid
  /// ≥ 1 (CHECK). "Zerar turma" soma um; pacote novo abre a seguinte à última.
  rodada   Int    @default(1)
  /// exploracao | galeria (CHECK; a ordem é `regras/passos.ts`).
  etapa    String @default("exploracao")

  /// Quando a galeria abriu NESTA rodada. Volta a nulo ao zerar (CHECK).
  galeriaLiberadaEm DateTime? @map("galeria_liberada_em") @db.Timestamptz(6)

  atualizadoEm DateTime @default(now()) @updatedAt @map("atualizado_em") @db.Timestamptz(6)

  turma  Turma           @relation(fields: [turmaId], references: [id], onDelete: Cascade)
  pacote Exp06ef1bPacote @relation(fields: [pacoteId], references: [id], onDelete: Cascade)

  @@index([escolaId], map: "exp06ef1b_gates_turma_escola_idx")
  @@index([pacoteId], map: "exp06ef1b_gates_turma_pacote_idx")
  @@map("exp06ef1b_gates_turma")
}

/// A sessão de UM estudante em UMA rodada de UM pacote.
///
/// Zerar abre outra rodada e, com ela, outra linha: a anterior fica, imutável,
/// e é ela que o painel de habilidades lê como a rodada passada.
model Exp06ef1bSessao {
  id          String @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  escolaId    String @map("escola_id")
  turmaId     String @map("turma_id") @db.Uuid
  pacoteId    String @map("pacote_id") @db.Uuid
  rodada      Int
  estudanteId String @map("estudante_id") @db.Uuid

  /// credencial | feed | lacrada | pacotes | cadeia | mariana | enquetes | fim
  /// (CHECK; a ordem é `regras/passos.ts`). `galeria` NUNCA é gravado: a etapa
  /// da turma o impõe a quem está em `lacrada`.
  passo   String @default("credencial")
  /// O texto estável que sorteia esta sessão: a abertura e o feed, os ids
  /// opacos e a ordem de chegada dos pacotes e dos blocos. Nasce no servidor,
  /// aleatório, e não muda — o F5 rende o mesmo feed.
  semente String

  /// Os ids de post que o feed serviu, na ordem da tela (até dez).
  postsServidos Json @default("[]") @map("posts_servidos")
  /// Os posts curtidos AGORA (descurtir tira daqui).
  curtidos      Json @default("[]")
  /// Os posts em que o estudante ficou mais de 5 s (uma vez por post).
  permanencias  Json @default("[]")

  /// O LATCH 1: o projeto da cédula, a convicção e o carimbo, juntos (CHECK).
  votoProjeto String?   @map("voto_projeto")
  /// examinei_bem | vi_tudo (CHECK).
  conviccao   String?
  votadoEm    DateTime? @map("votado_em") @db.Timestamptz(6)

  /// O que a criança fez na Galeria Oculta: `{ abertos: [ids], buscas: [{ tipo,
  /// area }] }`. O TEXTO da busca nunca entra (texto livre de menor).
  auditoria Json @default("{\"abertos\": [], \"buscas\": []}")

  /// O LATCH 2: manter | trocar (CHECK), o voto FINAL (o mesmo do inicial
  /// quando manteve) e o carimbo, juntos.
  revisaoAcao  String?   @map("revisao_acao")
  votoRevisado String?   @map("voto_revisado")
  revisadoEm   DateTime? @map("revisado_em") @db.Timestamptz(6)

  /// Cada envio da remontagem é uma tentativa (EF06CO07).
  pacotesTentativas   Int       @default(0) @map("pacotes_tentativas")
  pacotesRemontadosEm DateTime? @map("pacotes_remontados_em") @db.Timestamptz(6)
  /// Cada envio da cadeia é uma tentativa (EF06CO03).
  cadeiaTentativas    Int       @default(0) @map("cadeia_tentativas")
  cadeiaMontadaEm     DateTime? @map("cadeia_montada_em") @db.Timestamptz(6)

  /// O caso Mariana: a escolha de um cartão de mecanismo e um de atitude. Não
  /// vira nota: a evidência da missão está nas três habilidades.
  mecanismo String?
  atitude   String?
  cartoesEm DateTime? @map("cartoes_em") @db.Timestamptz(6)

  concluidaEm DateTime? @map("concluida_em") @db.Timestamptz(6)

  /// A versão do instrumento, para reprocessamento histórico.
  versaoInstrumento String @default("1.0.0") @map("versao_instrumento")

  criadoEm     DateTime @default(now()) @map("criado_em") @db.Timestamptz(6)
  atualizadoEm DateTime @default(now()) @updatedAt @map("atualizado_em") @db.Timestamptz(6)

  turma     Turma           @relation(fields: [turmaId], references: [id], onDelete: Cascade)
  estudante User            @relation("Exp06ef1bEstudante", fields: [estudanteId], references: [id], onDelete: Cascade)
  pacote    Exp06ef1bPacote @relation(fields: [pacoteId], references: [id], onDelete: Cascade)

  @@unique([pacoteId, rodada, estudanteId], map: "exp06ef1b_sessao_unica_por_rodada")
  @@index([escolaId, turmaId, pacoteId, rodada], map: "exp06ef1b_sessoes_rodada_idx")
  @@index([escolaId, estudanteId], map: "exp06ef1b_sessoes_estudante_idx")
  @@map("exp06ef1b_sessoes")
}

/// Uma COBERTURA — os 12 posts que a turma lê, COM o gabarito. É a atividade.
///
/// Uma ATIVA por turma (índice único parcial na migration). Sem homologação, a
/// turma roda o banco curado da Praça Central: a cobertura `padrao` nasce na
/// primeira entrada, e a missão NÃO nasce vazia — ao contrário da exp05ef1b, o
/// banco curado é uma cobertura completa, e não um tema alheio.
///
/// Homologar um tema novo DESATIVA a anterior (a linha fica, com as sessões
/// dela) e abre a rodada 1 da nova.
model Exp07ef1bCobertura {
  id       String  @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  escolaId String  @map("escola_id")
  turmaId  String  @map("turma_id") @db.Uuid
  tema     String
  /// O foco regional que a professora deu ao gerador ("Bairro Jardim das Flores").
  foco     String?
  /// padrao | ia (CHECK). `padrao` é o banco curado, não fallback de erro.
  origem   String

  /// Os 12 posts COM `enquadramento`, `tagFonte` e `tagAngulo`. `Json` porque o
  /// lote é lido e escrito sempre inteiro; o schema real é o Zod de
  /// `contrato-de-rotas.ts`, e o CHECK cobra array com 12.
  posts Json

  /// As URLs das imagens geradas, por id de post. Aqui, e não no bucket, para o
  /// `GET sessao` de 30 crianças não perguntar ao bucket se cada imagem existe.
  midia Json @default("{}")

  /// As três falas do Bloco 2 do podcast (`a-selecao/podcast.ts`), sobre o que
  /// cada veículo mostrou NESTE tema. Nulo = as do sheet (a Praça Central); um
  /// tema da IA as traz do preparo, revisadas junto com os posts (CHECK: objeto).
  podcast Json?

  /// Quem homologou. Carimbo sem FK, como `equipes_montagens.atualizado_por`:
  /// a saída de um professor da rede não pode travar a atividade da turma.
  /// Nulo só na `padrao` que nasceu sozinha (CHECK).
  aprovadaPor String? @map("aprovada_por") @db.Uuid

  /// A segunda fase da aprovação (ADR-146): o professor viu as imagens no card
  /// de cada post e as aprovou. Nulo = não vai ao ar (409 `imagens-nao-aprovadas`).
  imagensAprovadasEm DateTime? @map("imagens_aprovadas_em") @db.Timestamptz(6)

  ativa        Boolean  @default(true)
  criadaEm     DateTime @default(now()) @map("criada_em") @db.Timestamptz(6)
  atualizadaEm DateTime @default(now()) @updatedAt @map("atualizada_em") @db.Timestamptz(6)

  turma   Turma                @relation(fields: [turmaId], references: [id], onDelete: Cascade)
  gates   Exp07ef1bGateTurma[]
  sessoes Exp07ef1bSessao[]

  @@index([escolaId, turmaId], map: "exp07ef1b_coberturas_escola_turma_idx")
  @@map("exp07ef1b_coberturas")
}

/// O RELÓGIO DA TURMA — o botão único do painel (ADR-93: tabela lida por
/// polling de 5 s, nunca WebSocket).
///
/// Diz QUAL atividade e QUAL rodada estão em andamento: a sessão do estudante é
/// a de (cobertura, rodada) deste gate, e o resolvedor da evidência só aceita
/// resposta de enquete dessa sessão.
model Exp07ef1bGateTurma {
  escolaId    String @map("escola_id")
  turmaId     String @map("turma_id") @db.Uuid
  coberturaId String @map("cobertura_id") @db.Uuid
  /// ≥ 1 (CHECK). "Zerar turma" soma um; tema novo volta a 1.
  rodada      Int    @default(1)
  /// exploracao | mural | fichas | explicacao (CHECK; a ordem é `regras/passos.ts`).
  etapa       String @default("exploracao")

  atualizadoEm DateTime @default(now()) @updatedAt @map("atualizado_em") @db.Timestamptz(6)

  turma     Turma              @relation(fields: [turmaId], references: [id], onDelete: Cascade)
  cobertura Exp07ef1bCobertura @relation(fields: [coberturaId], references: [id], onDelete: Cascade)

  @@id([escolaId, turmaId])
  @@index([coberturaId], map: "exp07ef1b_gates_turma_cobertura_idx")
  @@map("exp07ef1b_gates_turma")
}

/// A sessão de UM estudante em UMA rodada de UMA cobertura.
///
/// Zerar abre outra rodada e, com ela, outra linha: a anterior fica, imutável,
/// e é ela que o painel de habilidades lê como a rodada passada.
model Exp07ef1bSessao {
  id          String @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  escolaId    String @map("escola_id")
  turmaId     String @map("turma_id") @db.Uuid
  estudanteId String @map("estudante_id") @db.Uuid
  coberturaId String @map("cobertura_id") @db.Uuid
  rodada      Int

  /// desafio | feed | salvos | publicado | mural | fichas | explicacao |
  /// reflexao | enquetes | fim (CHECK; a ordem é `regras/passos.ts`).
  passo String @default("desafio")

  /// Os 3 ids publicados. Nulo antes do latch; com ele, os três juntos com a
  /// legenda, a matriz e o carimbo (CHECK de coerência).
  selecao String[] @default([])
  /// 10 a 140 CODE POINTS (`varchar` conta caracteres, como o `[...s].length`
  /// do Zod). Texto livre de menor que OUTRA criança lê no Mural: passa pelo
  /// sanitizador antes de chegar aqui, e só o professor da turma o vê no painel.
  legenda String?  @db.VarChar(140)
  /// A contagem por lente, calculada NO SERVIDOR a partir da cobertura.
  matriz  Json?

  publicadaEm DateTime? @map("publicada_em") @db.Timestamptz(6)
  concluidaEm DateTime? @map("concluida_em") @db.Timestamptz(6)
  /// O tempo de feed que a tela mediu. INDICATIVO, nunca mérito.
  tempoFeedS  Int?      @map("tempo_feed_s")

  /// O par do Mural, congelado no pareamento. `par_sessao_id` sem FK: a sessão
  /// do par pode sair com a criança (cascata de `users`), e o Mural desta não
  /// pode travar a exclusão da outra.
  parSessaoId String? @map("par_sessao_id") @db.Uuid
  /// tomas | malu (CHECK) — o colega virtual, quando não há par na sala.
  parVirtual  String? @map("par_virtual")
  /// O que a tela escreve sobre o par ("Bia", "Equipe 3", "Tomás"). Congelado:
  /// renomear a equipe depois do Mural não muda o que a sala já viu.
  parRotulo   String? @map("par_rotulo")

  /// A versão do instrumento, para reprocessamento histórico (DAD-06).
  versaoInstrumento String @default("1.0.0") @map("versao_instrumento")

  criadaEm     DateTime @default(now()) @map("criada_em") @db.Timestamptz(6)
  atualizadaEm DateTime @default(now()) @updatedAt @map("atualizada_em") @db.Timestamptz(6)

  turma     Turma              @relation(fields: [turmaId], references: [id], onDelete: Cascade)
  estudante User               @relation("Exp07ef1bEstudante", fields: [estudanteId], references: [id], onDelete: Cascade)
  cobertura Exp07ef1bCobertura @relation(fields: [coberturaId], references: [id], onDelete: Cascade)
  reflexao  Exp07ef1bReflexao?

  @@unique([escolaId, turmaId, estudanteId, coberturaId, rodada], map: "exp07ef1b_sessao_unica_por_rodada")
  @@index([escolaId, turmaId, coberturaId, rodada], map: "exp07ef1b_sessoes_rodada_idx")
  @@index([escolaId, estudanteId], map: "exp07ef1b_sessoes_estudante_idx")
  @@map("exp07ef1b_sessoes")
}

/// A reflexão da Etapa 6 — uma por sessão, e só o professor da turma a lê.
///
/// **Texto livre de menor de idade.** Não vai a log nem à telemetria; no painel
/// só sai para quem leciona (o recorte da ADR-108). Sem criptografia de
/// aplicação, pela mesma decisão da exp05ef1b: o Cloud SQL já cifra em repouso.
///
/// RETENÇÃO: vinculada à vigência contratual, sem rotina de expurgo (DAD-10).
model Exp07ef1bReflexao {
  sessaoId String @id @map("sessao_id") @db.Uuid
  escolaId String @map("escola_id")
  /// 100 a 500 code points — `char_length` no CHECK, `[...s].length` no Zod.
  texto    String
  /// O mesmo número, gravado; o CHECK cobra `chars = char_length(texto)`.
  chars    Int

  criadaEm DateTime @default(now()) @map("criada_em") @db.Timestamptz(6)

  sessao Exp07ef1bSessao @relation(fields: [sessaoId], references: [id], onDelete: Cascade)

  @@index([escolaId], map: "exp07ef1b_reflexoes_escola_idx")
  @@map("exp07ef1b_reflexoes")
}

/// UMA MARCA da ficha pedagógica (E14): o que a missão viu o estudante fazer
/// numa atividade, numa rodada — uma AÇÃO ("tirou o post do ar") ou a
/// resposta de uma PERGUNTA de múltipla escolha.
///
/// É o DADO BRUTO da evidência, e a única tabela que a missão escreve (pela
/// porta `EvidenciasService.marcar`). A evidência que o professor lê
/// (`evidencias`) é DERIVADA daqui: a melhor marca de cada habilidade.
///
/// A chave NÃO leva `turma_id`: a marca é da criança naquela atividade e
/// rodada, e a turma é só o contexto em que ela foi registrada.
///
/// **Sem FK de `exp_id` para `experiencias`** (catálogo vazio em dev), como
/// `liberacoes` e `equipes_montagens`. O `estudante_id` TEM FK (a trava da
/// identidade única), com cascata: a marca é dado da criança.
model EvidenciaMarca {
  escolaId    String @map("escola_id")
  turmaId     String @map("turma_id") @db.Uuid
  expId       String @map("exp_id")
  /// O id da ATIVIDADE, dado pela missão — texto opaco para a plataforma
  /// (`[A-Za-z0-9_.:-]`, 1 a 100; CHECK na migration e `ATIVIDADE_ID_RE`).
  atividadeId String @map("atividade_id")
  /// Reiniciar uma atividade abre uma rodada NOVA (≥ 1); a anterior fica.
  rodada      Int
  estudanteId String @map("estudante_id") @db.Uuid
  /// O código BNCC que este marcador mede, copiado da ficha no registro.
  habilidade  String
  /// O id do marcador na ficha.
  marcador    String
  /// atingiu | em_processo | nao_atingiu — CHECK na migration.
  status      String
  /// acao | multipla_escolha — CHECK na migration. Na ação vale a MELHOR
  /// marca; na pergunta, a PRIMEIRA resposta.
  tipo        String
  /// A versão da ficha em vigor quando a marca foi registrada.
  versaoFicha Int    @map("versao_ficha")

  /// É por ela que se acha a RODADA EM ANDAMENTO da turma × missão: a da marca
  /// mais recente. Só ela é recalculada quando as equipes mudam.
  registradaEm DateTime @default(now()) @map("registrada_em") @db.Timestamptz(6)

  turma     Turma @relation(fields: [turmaId], references: [id], onDelete: Cascade)
  estudante User  @relation("EvidenciaMarcaEstudante", fields: [estudanteId], references: [id], onDelete: Cascade)

  @@id([escolaId, expId, atividadeId, rodada, estudanteId, marcador])
  @@index([escolaId, turmaId, expId, registradaEm])
  @@map("evidencias_marcas")
}

/// A EVIDÊNCIA de uma habilidade: o nível de UM estudante numa habilidade da
/// BNCC, numa atividade, numa rodada (E14). É o que o painel do professor lê.
///
/// **N/A ("Não avaliado") é a AUSÊNCIA de linha.** `nao_participou` é outra
/// coisa: um N/A EXPLÍCITO, posto pelo professor, que existe para BARRAR a
/// cópia da equipe ("ela faltou; não herda o que o colega fez").
///
/// A precedência entre as origens é regra de `evidencias/regras.ts`:
/// professor > própria > cópia da equipe. A cópia da PROJEÇÃO (a turma
/// inteira diante de um computador só) nasce `a_revisar` e não conta até o
/// professor confirmar.
///
/// `equipe_id` sem FK, de propósito: as equipes são TROCADAS INTEIRAS a cada
/// `PUT` (ADR-111), e uma FK apagaria (ou travaria) a evidência junto. O
/// `estudante_id` tem FK com cascata (a trava da identidade única).
model Evidencia {
  id          String @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  escolaId    String @map("escola_id")
  turmaId     String @map("turma_id") @db.Uuid
  expId       String @map("exp_id")
  atividadeId String @map("atividade_id")
  rodada      Int
  estudanteId String @map("estudante_id") @db.Uuid
  habilidade  String

  /// atingiu | em_processo | nao_atingiu | nao_participou — CHECK na migration.
  status   String
  /// propria | equipe | projecao | professor — CHECK na migration.
  origem   String
  /// valida | a_revisar — CHECK na migration. `a_revisar` só na projeção.
  situacao String

  /// De quem a cópia veio (origem `equipe` ou `projecao`), e só nelas.
  fonteEstudanteId String? @map("fonte_estudante_id") @db.Uuid
  /// A equipe da cópia no momento em que ela foi feita. Carimbo, sem FK.
  equipeId         String? @map("equipe_id") @db.Uuid
  /// Quem ajustou (origem `professor`), e só nela. Carimbo, sem FK.
  editadoPor       String? @map("editado_por") @db.Uuid

  atualizadoEm DateTime @default(now()) @updatedAt @map("atualizado_em") @db.Timestamptz(6)

  turma     Turma @relation(fields: [turmaId], references: [id], onDelete: Cascade)
  estudante User  @relation("EvidenciaEstudante", fields: [estudanteId], references: [id], onDelete: Cascade)

  @@unique([escolaId, expId, atividadeId, rodada, estudanteId, habilidade])
  @@index([escolaId, turmaId, expId, atividadeId, rodada])
  @@index([escolaId, estudanteId])
  @@map("evidencias")
}

/// O HISTÓRICO da evidência (E14): toda mudança, com de/para, quem e quando.
///
/// **APPEND-ONLY no banco**: um trigger recusa `UPDATE` para qualquer role, e
/// a role de runtime só recebe `SELECT, INSERT`. É o que responde "quem mudou
/// a nota da Ana, e de quê para quê?" meses depois — reescrever uma linha é o
/// único jeito de ele mentir.
///
/// `estudante_id` e `habilidade` são nulos no evento da TURMA (a
/// confirmação da projeção vale para todos de uma vez).
model EvidenciaEvento {
  id          String  @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  escolaId    String  @map("escola_id")
  turmaId     String  @map("turma_id") @db.Uuid
  expId       String  @map("exp_id")
  atividadeId String  @map("atividade_id")
  rodada      Int
  estudanteId String? @map("estudante_id") @db.Uuid
  habilidade  String?

  /// marca | copia | recalculo | confirmacao | ajuste — CHECK na migration.
  tipo String
  /// O estado ANTES (`null` = não havia linha) e DEPOIS (`null` = a linha saiu).
  de   Json?
  para Json?

  /// Quem causou: o estudante na marca, o professor no ajuste e na
  /// confirmação, `null` no que a plataforma recalculou sozinha.
  autorId  String?  @map("autor_id") @db.Uuid
  criadoEm DateTime @default(now()) @map("criado_em") @db.Timestamptz(6)

  turma     Turma @relation(fields: [turmaId], references: [id], onDelete: Cascade)
  /// Cascata, e não `SET NULL`: anular a coluna seria um `UPDATE`, que o
  /// trigger do append-only recusa — e a saída da criança travaria.
  estudante User? @relation("EvidenciaEventoEstudante", fields: [estudanteId], references: [id], onDelete: Cascade)

  @@index([escolaId, turmaId, expId, atividadeId, rodada])
  @@index([escolaId, estudanteId])
  @@map("evidencias_eventos")
}

/// A MONTAGEM DAS EQUIPES de uma missão numa turma (E13, ADR-111): quantos
/// computadores a sala tem hoje, como as equipes nasceram e quem faltou.
///
/// **Equipe é quem DIVIDE UM COMPUTADOR**, e não agrupamento pedagógico. A
/// escola pública tem menos máquinas que crianças, e sem isto a plataforma
/// contava a sala como se cada estudante tivesse a própria tela — o painel
/// dizia "12 não começaram" quando os 12 estavam sentados ao lado de quem
/// começou.
///
/// Uma linha por (turma × missão × ATIVIDADE) — ADR-130: a equipe é da
/// atividade, e não da missão. É ela que carrega a `versao` da
/// concorrência otimista: duas telas do mesmo professor (o computador da sala e
/// o celular) salvando ao mesmo tempo não podem se sobrescrever em silêncio.
///
/// **Sem FK de `exp_id` para `experiencias`**, pelo mesmo motivo de
/// `liberacoes.exp_id`: aquele catálogo é escrito pelo CI ao publicar, e em dev
/// está vazio. Quem restringe as missões que aceitam equipe é
/// `equipes/regras.ts#EXPERIENCIAS_COM_EQUIPE`, no código.
model EquipesMontagem {
  escolaId    String @map("escola_id")
  turmaId     String @map("turma_id") @db.Uuid
  expId       String @map("exp_id")
  /// O id da ATIVIDADE, dado pela missão — texto opaco, o alfabeto de
  /// `evidencias_marcas.atividade_id` (CHECK na migration). A missão sem
  /// atividade usa o fixo `turma` (`regras.ts#ATIVIDADE_DA_TURMA`).
  atividadeId String @map("atividade_id")

  /// sorteio | manual | individual — CHECK na migration. `manual` nasce com N
  /// equipes VAZIAS: quem distribui é o professor, que conhece quem senta com
  /// quem. `individual` é "um aluno por computador": grava a montagem e
  /// nenhuma equipe.
  modo String

  /// Quantos computadores a sala tem nesta aula. É o número de equipes do
  /// sorteio, e muda de aula para aula (o laboratório divide horário). NULO
  /// só no `individual` (CHECK na migration): lá são tantos quantas crianças.
  computadores Int?

  /// Quem faltou na hora de montar. Fica fora do sorteio, e não é matrícula:
  /// amanhã a criança volta e entra no próximo.
  ausentes String[] @default([]) @db.Uuid

  /// A concorrência otimista: o `PUT` diz em qual versão se baseou, e versão
  /// velha é 409. Começa em 1 — `0` é o que o cliente manda quando não havia
  /// montagem nenhuma.
  versao Int @default(1)

  /// Quem salvou por último. Sem FK, de propósito: é carimbo de auditoria, e
  /// uma FK para `users` faria a saída de um professor da rede apagar (ou
  /// travar) a montagem da turma inteira.
  atualizadoPor String   @map("atualizado_por") @db.Uuid
  atualizadoEm  DateTime @default(now()) @updatedAt @map("atualizado_em") @db.Timestamptz(6)

  turma   Turma    @relation(fields: [turmaId], references: [id], onDelete: Cascade)
  equipes Equipe[]

  @@id([escolaId, turmaId, expId, atividadeId])
  @@index([escolaId, turmaId])
  @@map("equipes_montagens")
}

/// Uma EQUIPE: um computador, um nome e quem senta diante dele.
///
/// O nome é o que a criança lê na tela ("Equipe 3") e o professor pode trocar;
/// o UNIQUE por missão existe porque duas "Equipe 3" no mesmo painel são a
/// dúvida que ninguém consegue resolver no meio da aula.
model Equipe {
  id          String @id @default(dbgenerated("gen_random_uuid()")) @db.Uuid
  escolaId    String @map("escola_id")
  turmaId     String @map("turma_id") @db.Uuid
  expId       String @map("exp_id")
  atividadeId String @map("atividade_id")

  /// 1 a 30 caracteres depois do `trim` — CHECK na migration e `NOME_MAX` no
  /// código. O teto é o que cabe no card do painel sem quebrar a linha.
  nome String

  /// A ordem em que o professor montou. É a ordem da tela, e não o nome:
  /// "Equipe 10" viria antes de "Equipe 2" na ordem alfabética.
  ordem Int

  montagem EquipesMontagem @relation(fields: [escolaId, turmaId, expId, atividadeId], references: [escolaId, turmaId, expId, atividadeId], onDelete: Cascade)
  membros  EquipeMembro[]

  @@unique([escolaId, turmaId, expId, atividadeId, nome])
  @@index([escolaId, turmaId, expId, atividadeId])
  @@map("equipes")
}

/// Quem está em qual equipe.
///
/// `turma_id`, `exp_id` e `atividade_id` REPETIDOS da equipe, e é isso que
/// torna possível o UNIQUE que importa: **uma criança, uma equipe por
/// atividade**. Sem as colunas
/// aqui, a regra só existiria no código, e dois `PUT` em paralelo poriam a
/// mesma criança em dois computadores.
model EquipeMembro {
  escolaId    String @map("escola_id")
  equipeId    String @map("equipe_id") @db.Uuid
  turmaId     String @map("turma_id") @db.Uuid
  expId       String @map("exp_id")
  atividadeId String @map("atividade_id")
  estudanteId String @map("estudante_id") @db.Uuid

  equipe    Equipe @relation(fields: [equipeId], references: [id], onDelete: Cascade)
  estudante User   @relation("EquipeMembroEstudante", fields: [estudanteId], references: [id], onDelete: Cascade)

  @@id([equipeId, estudanteId])
  @@unique([escolaId, turmaId, expId, atividadeId, estudanteId])
  @@index([escolaId, estudanteId])
  @@map("equipes_membros")
}
```
