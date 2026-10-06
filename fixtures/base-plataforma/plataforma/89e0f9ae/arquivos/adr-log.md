<!-- CÓPIA de plataforma-unooria@89e0f9ae (2026-10-06) · origem: documentacao-latex/secoes/18-adr.tex · não edite -->

# `documentacao-latex/secoes/18-adr.tex` — o registro das ADRs (número, título, data, estado)

149 ADRs; a última é a ADR-149. O texto completo de cada uma (contexto, alternativas, consequências) está no `.tex`; aqui só o índice.

| ADR | Decisão | Data | Estado |
|---|---|---|---|
| ADR-01 | Experiências como bundles estáticos, não serviços | 2026-08 | Aceita |
| ADR-02 | Monorepo único (pnpm + Turborepo) | 2026-08 | Aceita |
| ADR-03 | Autenticação por OIDC genérico | 2026-08 | Aceita |
| ADR-04 | Uma stack por contrato; escolas por RLS | 2026-08 | Aceita |
| ADR-05 | Cloud SQL HA, não AlloyDB | 2026-08 | Aceita |
| ADR-06 | Pub/Sub para telemetria desde o início | 2026-08 | Aceita |
| ADR-07 | IA atrás de um gateway na própria API | 2026-08 | Aceita; revista para o agente do professor (ADR-126) |
| ADR-08 | RLS forçada e uma porta única de banco | 2026-08-24 | Aceita |
| ADR-09 | Domínio por experiência na API; gabarito server-side | 2026-08-24 | Aceita |
| ADR-10 | Bem-estar: DASS-21 fixo, IA só no entorno, sem visão de gestor | 2026-08-25 | Aceita |
| ADR-11 | Telemetria sem PII e vocabulário fechado no payload | 2026-08-26 | Aceita |
| ADR-12 | `grau` como invariante de API, não regra de tela | 2026-08-26 | Aceita |
| ADR-13 | Retenção sem prazo declarado, em troca de reprocessamento | 2026-08-26 | Aceita |
| ADR-14 | Telemetria no PostgreSQL particionado; sem BigQuery, sem Redis | 2026-08-27 | Aceita |
| ADR-15 | O hub assina os tokens enquanto o IdP central não entra | 2026-08 | Aceita, transitória |
| ADR-16 | Credencial por ADC; modelo `3.6-flash` em `global` | 2026-08 | Aceita, com custo |
| ADR-17 | Claim atômico em vez de fila externa | 2026-08 | Aceita |
| ADR-18 | Exceções registradas: jogo em JS clássico, app-70 fora do DS | 2026-08-26 | Aceita |
| ADR-19 | Design system externo como fonte única de interface | 2026-08 | Aceita |
| ADR-20 | Um banco, um schema; prefixo `exp_NN_` | 2026-08-27 | Aceita; prefixo revisto na ADR-110 |
| ADR-21 | Push subscription para a própria API, sem worker | 2026-08 | Aceita |
| ADR-22 | exp04ef1b 1.1.0: briefing na voz da escola, conclusão por botão | 2026-08-27 | Aceita, com custo |
| ADR-23 | Function calling entra no `AiProvider`, não na experiência | 2026-08-27 | Aceita |
| ADR-24 | Teto de custo de IA por SESSÃO; a quota diária é fusível | 2026-08-27 | Aceita, com número a medir |
| ADR-25 | O Relógio da Aula é tabela da experiência, não coluna em `turmas` | 2026-08-27 | Aceita |
| ADR-26 | Sem prazo de retenção na exp02em1b; exclusão por zerar a turma | 2026-08-27 | Aceita |
| ADR-27 | Transcrição do estudante é dado do instrumento: professor lê, gestor não | 2026-08-27 | Aceita |
| ADR-28 | O feed do professor consome a API do estudante | 2026-08-27 | Aceita |
| ADR-29 | A app-70 não emite nota, emite perfil | 2026-08-27 | Aceita |
| ADR-30 | Vínculo pessoa × escola datado (`lotacoes`) | 2026-08-28 | Aceita |
| ADR-31 | CPF como identificador civil, sem senha no CSV | 2026-08-28 | Aceita |
| ADR-32 | Sessão por cookie HttpOnly com rotação | 2026-08-28 | Aceita |
| ADR-33 | Rotação de chave a frio por variável de ambiente dupla | 2026-08-28 | Aceita |
| ADR-34 | Uma escola ativa por sessão; sem agregação de rede | 2026-08-28 | Aceita |
| ADR-35 | Portabilidade de dados por JWS assinado | 2026-08-28 | Aceita |
| ADR-36 | Perfil portátil é chave/valor com esquema fechado | 2026-08-28 | Aceita |
| ADR-37 | Validação de entrada exclusivamente via Zod | 2026-08-29 | Aceita |
| ADR-38 | Documentação viva em LaTeX compilada no CI | 2026-08-29 | Aceita |
| ADR-39 | Dependências sob varredura de vulnerabilidade (Snyk) | 2026-08-29 | Aceita |
| ADR-40 | Landing institucional: estática, sem sessão, 1440 px | 2026-08-30 | Aceita |
| ADR-41 | Dispositivo expansível na pós-revelação da exp08ef1b | 2026-08-30 | Aceita |
| ADR-42 | Exposição no dossiê mede o feed, não o domínio | 2026-08-30 | Aceita |
| ADR-43 | Conclusão do estudante: guarda primeira e última inclinação | 2026-08-30 | Aceita |
| ADR-44 | Janela de envolvimento fecha no último post visto | 2026-08-30 | Aceita |
| ADR-45 | Geração de planos com streaming SSE e retenção de 30 dias | 2026-08-31 | Aceita |
| ADR-46 | Embed via iframe restrito: sandbox, allow e canal postMessage | 2026-08-31 | Aceita |
| ADR-47 | Rate limit por IP em rotas públicas, por usuário em autenticadas | 2026-08-31 | Aceita |
| ADR-48 | Importação de CSV síncrona com limite de 30 MB | 2026-08-31 | Aceita |
| ADR-49 | Atividade vinculada à turma; clone para cada turma nova | 2026-09-01 | Aceita |
| ADR-50 | Perfil da Vila importado na exp08ef1b sem FK rígida | 2026-09-01 | Aceita |
| ADR-51 | Testes E2E com Playwright contra ambiente real | 2026-09-01 | Aceita |
| ADR-52 | Mock de IA determinístico para testes e homologação | 2026-09-01 | Aceita |
| ADR-53 | GitHub Actions com três ambientes (`dev`, `hml`, `main`) | 2026-09-02 | Aceita |
| ADR-54 | Balcão de atendimento: cadastro individual delega ao importador | 2026-09-02 | Aceita |
| ADR-55 | Reset de senha pelo professor gera credencial temporária | 2026-09-02 | Aceita |
| ADR-56 | Soft delete com `desativado_em` em usuários | 2026-09-02 | Aceita |
| ADR-57 | Observabilidade: traces OpenTelemetry com proporção configurável | 2026-09-02 | Aceita |
| ADR-58 | Sourcemaps enviados a bucket privado, nunca na CDN | 2026-09-02 | Aceita |
| ADR-59 | Quem escreve usuário é o importador; balcão gera linha CSV | 2026-09-03 | Aceita |
| ADR-60 | Microsoft Clarity via `@edu/sdk`, desligado se sem ID | 2026-09-03 | Aceita |
| ADR-61 | Frentes paralelas com git worktree sobre `origin/dev` | 2026-09-03 | Aceita |
| ADR-62 | DLQ no Pub/Sub para telemetria rejeitada | 2026-09-04 | Aceita |
| ADR-63 | Ingestão de telemetria desacoplada do processamento analítico | 2026-09-04 | Aceita |
| ADR-64 | Relógio da Tempestade: tempo no marco, não em background | 2026-09-05 | Aceita |
| ADR-65 | Guia da aula é gerado do catálogo, sem tela dedicada | 2026-09-06 | Aceita |
| ADR-66 | exp07ef1b: IA no runtime para conversas, gabarito server-side | 2026-09-06 | Superada (missão retirada, ADR-113) |
| ADR-67 | Mídias da exp07ef1b: imagens e áudios pré-gerados no bucket | 2026-09-06 | Aceita como molde; o Eco saiu (ADR-113) |
| ADR-68 | exp07ef1b e exp06ef2b: clone de mensageria só no tema escuro | 2026-09-06 | Aceita (vale para a exp06ef2b; o Eco saiu, ADR-113) |
| ADR-69 | Missão só abre na turma se o professor liberou (`liberacoes`) | 2026-09-06 | Aceita |
| ADR-70 | Página de transparência algorítmica aberta ao público | 2026-09-06 | Aceita |
| ADR-71 | Fatias verticais por módulo em frentes paralelas | 2026-09-06 | Aceita |
| ADR-72 | Fronteira do disfarce da exp06ef2b: mapa da rede fala pela escola | 2026-09-06 | Aceita |
| ADR-73 | Planejamento curricular dirigido pela BNCC (app-92) | 2026-09-06 | Aceita; recortada para o agente do professor (ADR-127) |
| ADR-74 | Contabilidade de tokens de IA com callback `aoUsarTokens` | 2026-09-06 | Aceita |
| ADR-75 | Rolagem unificada via `ScrollBar` do Design System | 2026-09-07 | Aceita |
| ADR-76 | Planejamento semanal estruturado com suporte a downloads | 2026-09-07 | Aceita |
| ADR-77 | Trilha de navegação (breadcrumb) no layout, não na página | 2026-09-07 | Aceita |
| ADR-78 | Logoff no menu da conta com limpeza completa de cookies | 2026-09-07 | Aceita |
| ADR-79 | Vínculo obrigatório escola × regional na governança da rede | 2026-09-07 | Aceita |
| ADR-80 | Modelo de seis papéis e cadeia de atribuição transitiva | 2026-09-08 | Aceita |
| ADR-81 | Panorama da diretoria de ensino consolidado por regional | 2026-09-08 | Aceita |
| ADR-82 | Relatório pedagógico da regional com varredura em lote | 2026-09-08 | Aceita |
| ADR-83 | Header institucional ancorado na janela (full-bleed) | 2026-09-08 | Aceita |
| ADR-84 | Observabilidade de cliente sem sessão com sanitização | 2026-09-08 | Aceita |
| ADR-85 | Trocar de escola remonta o miolo da área (`<EscopoDaEscola>`) | 2026-09-09 | Aceita |
| ADR-86 | O guia da aula mostra o conteúdo da missão, não o descreve | 2026-09-09 | Aceita |
| ADR-87 | Disponibilidade: terceiro eixo, e o produto como teto | 2026-09-09 | Aceita |
| ADR-88 | O painel da Unooria é só do `admin` | 2026-09-09 | Aceita |
| ADR-89 | Histórico do painel é tabela append-only, e a rede lê o dela | 2026-09-10 | Aceita |
| ADR-90 | A suíte da API roda em UM worker | 2026-09-10 | Aceita |
| ADR-91 | O idioma da interface tem três zonas, e o clone não se traduz | 2026-09-10 | Aceita |
| ADR-92 | Voltar um momento reabre a sessão; a trava é a revelação | 2026-09-10 | Aceita |
| ADR-93 | Sincronização de sala por polling HTTP, não WebSocket | 2026-09-10 | Aceita |
| ADR-94 | O latch de turma anda por polling curto, nunca por canal persistente | 2026-09-10 | Aceita |
| ADR-95 | A sessão do hub dura 2h de inatividade, igual para todo papel | 2026-09-10 | Aceita |
| ADR-96 | Ficar na missão conta como uso, e a sessão que morre tem tela | 2026-09-10 | Aceita |
| ADR-97 | A tela diz POR QUE não entrou, e a suíte espera o desfecho | 2026-09-10 | Aceita |
| ADR-98 | A plataforma assume UM fuso, numa constante só | 2026-09-11 | Aceita |
| ADR-99 | O fuso vem de uma variável de ambiente, em três superfícies | 2026-09-11 | Aceita |
| ADR-100 | Da sala para a missão há UM caminho, e ele leva à ficha | 2026-09-15 | Aceita |
| ADR-101 | Quatro ambientes, e a frente nasce e volta em `dev-local` | 2026-09-15 | Aceita |
| ADR-102 | A doutrina é uma fonte só, lida por quatro agentes | 2026-09-15 | Aceita |
| ADR-103 | A frente mergeada se enterra sozinha | 2026-09-15 | Aceita |
| ADR-104 | A base se realinha sozinha depois da promoção | 2026-09-15 | Aceita |
| ADR-105 | A quota de IA é dado, editável pela Unooria, e não variável de ambiente | 2026-09-15 | Aceita |
| ADR-106 | O `_template` nasce com a fiação inteira e sem componente de interface | 2026-09-16 | Aceita |
| ADR-107 | O site público entra no hub como porte, e o cadastro de interesse passa pela api | 2026-09-16 | Aceita |
| ADR-108 | A missão de sala nasce vazia, e a revelação é do relógio da turma | 2026-09-17 | Aceita; a v1 saiu (ADR-114) e a v2.2 a retoma (ADR-118) |
| ADR-109 | O rótulo da tabela da BNCC de Computação é CENTRADO, e a atribuição é uma partição | 2026-09-17 | Aceita |
| ADR-110 | O código da experiência diz onde ela mora na trilha | 2026-09-23 | Aceita |
| ADR-111 | Equipe é quem divide um computador, e o painel conta por computador | 2026-09-25 | Aceita |
| ADR-112 | A evidência é por atividade e rodada, e a melhor rodada vale por habilidade | 2026-09-25 | Aceita |
| ADR-113 | A Seleção substitui o Eco no Grupo, e a limpeza vem antes | 2026-09-25 | Aceita |
| ADR-114 | Quem mandou isso? v1 é retirada; a v2.2 entra com o mesmo código | 2026-09-25 | Aceita |
| ADR-115 | A Seleção: o par do Mural é do computador, e a IA gradua a legenda | 2026-09-25 | Aceita; a leitura da legenda ficou sem teto de saída (ADR-148) |
| ADR-116 | A experiência que perde o código é arquivada, não apagada | 2026-09-25 | Aceita |
| ADR-117 | Jornal da Escola: a redação é da Unooria, o professor abre o resultado e a revisão, e a IA só escolhe o layout | 2026-09-27 | Aceita; as imagens passam pelo OK do professor, uma a uma (ADR-147); a diagramação ficou sem teto de saída (ADR-148) |
| ADR-118 | Quem mandou isso? v2.2: atividade é o pacote, rodada é a reaplicação, e a régua mede pela seleção e pelas perguntas do PO | 2026-09-25 | Aceita; a régua foi substituída pela ADR-120 |
| ADR-119 | O podcast da A Seleção é do professor, e a IA reescreve só as três falas que dependem do tema | 2026-09-26 | Aceita |
| ADR-120 | A régua v2 de Quem mandou isso?: cada habilidade pelo verbo dela, e refazer o mesmo pacote não mede memória | 2026-09-26 | Aceita; as perguntas voltaram às do PO (ADR-131); a medição única e a rubrica do Se/Então saíram (ADR-145) |
| ADR-121 | O CI verifica só os PRs para `dev`, `hml` e `main` | 2026-09-26 | Aceita |
| ADR-122 | A modelagem UML entra no Capítulo 5, com os catorze tipos da UML 2.5.1 e par Mermaid mesmo onde o Mermaid não tem o tipo | 2026-09-27 | Aceita |
| ADR-123 | O plano anual tem uma estrutura só, definida pelo prompt, e o template é exemplo de formato | 2026-09-30 | Aceita |
| ADR-124 | O `CLAUDE.md` admite o bloco que uma ferramenta escreve, e só ele | 2026-09-30 | Aceita; emenda a ADR-55 e a ADR-102 |
| ADR-125 | O grafo do código nasce copiado em cada worktree e se atualiza sozinho no pull, e fica fora do git | 2026-09-30 | Aceita; completa a ADR-124 |
| ADR-126 | O agente de IA do professor roda no Vertex AI Agent Engine, atrás da api | 2026-09-30 | Aceita; revisa a ADR-07 |
| ADR-127 | Só data store, inclusive para as habilidades da BNCC | 2026-09-30 | Aceita, em avaliação; recorta a ADR-73 |
| ADR-128 | SSE só no chat do agente | 2026-09-30 | Aceita; a segunda rota com stream é a da ADR-132 |
| ADR-129 | O markdown do agente vira HTML no navegador | 2026-09-30 | Aceita |
| ADR-130 | A atividade é do professor, e a equipe é da atividade | 2026-10-01 | Aceita |
| ADR-131 | As perguntas de evidência de Quem mandou isso? são as do PO, literais | 2026-10-01 | Aceita |
| ADR-132 | A Ajuda com avatar: o vídeo é do vendor, o LLM é nosso, e o limite é em minutos | 2026-10-02 | Aceita; exceção à regra 5 e à ADR-105 |
| ADR-133 | A missão do 8º ano troca o Instanooria pelo Unoovista | 2026-10-02 | Aceita |
| ADR-134 | Quem mandou isso? troca o clone do WhatsApp pelo Unoochat | 2026-10-02 | Aceita |
| ADR-135 | A Seleção troca o Instanooria pelo Unoovista | 2026-10-02 | Aceita |
| ADR-136 | As peças da gaveta do Jornal da Escola passam para o Unoovista e o Unoochat | 2026-10-02 | Aceita |
| ADR-137 | O Júri Estadual de Projetos nasce no Unoovista e mede o que o briefing pediu | 2026-10-02 | Aceita |
| ADR-138 | A missão da 2ª série do EM troca o clone do ChatGPT pelo UnooriaAI | 2026-10-02 | Aceita |
| ADR-139 | O design system tem uma versão só, e todas as experiências sobem juntas | 2026-10-02 | Aceita |
| ADR-140 | A eliminação a pedido do titular apaga o cadastro de verdade, e o comprovante não guarda a pessoa | 2026-10-03 | Aceita |
| ADR-141 | A idade de uma versão fixada sai do histórico, não de uma coluna nova | 2026-10-03 | Aceita |
| ADR-142 | Na subida do DS, o `dist/` se compara sem os sourcemaps | 2026-10-03 | Aceita |
| ADR-143 | O lado do feed entra no sorteio de equipes por registro da missão, e redistribuir não convive com equipe | 2026-10-03 | Aceita |
| ADR-144 | O painel de habilidades lê por unidade, a missão vale o melhor entre as atividades, e a regional desce até a escola sem lotação | 2026-10-03 | Aceita |
| ADR-145 | Toda rodada mede todas as habilidades, o critério de cada nível aparece no painel, e Quem mandou isso? perde a regra dissertativa | 2026-10-05 | Aceita; revê a ADR-120 |
| ADR-146 | Pôr a atividade no ar libera a missão na sala, e A Seleção aprova textos e imagens em duas fases | 2026-10-05 | Aceita; complementa a ADR-130 |
| ADR-147 | O Jornal da Escola: o professor aprova cada imagem antes da turma, e a mesa leva a criança à página | 2026-10-05 | Aceita; complementa a ADR-117 |
| ADR-148 | As duas chamadas curtas de IA em sala não têm teto de saída, e as missões revisadas se testam com a IA real | 2026-10-05 | Aceita; revê o teto da ADR-115 e da ADR-117 |
| ADR-149 | A plataforma publica a base que o gerador de missões lê | 2026-10-06 | Aceita |
