---
name: defaults-missao
description: Respostas-padrão da plataforma por classe de lacuna. O passo de completude da spec (produto) aplica antes de decidir sozinho, e o D0-UX (design) só os de UI; missão irmã no catálogo vem depois; one-pager depois; inferência por último. Rascunho v0 — cada padrão marca de onde saiu e o que ainda precisa de confirmação do produto.
sources: [criterios-gate-estrutural, criterios-experiencia, criterios-pedagogicos, formato-spec, criterios-dev/4-dados-telemetria-lgpd, pronto, padroes-aprendidos, chat]
status: rascunho v0 — validar com produto (PM) e pedagogia antes de tratar como contrato
---

# Padrões da plataforma por classe de lacuna

**O que este arquivo é.** Quando a spec cala sobre algo que a esteira precisa e a resposta é a mesma para toda missão, a resposta está aqui. Desde 24/10/2026 (PR 6 do plano «Produto dono do contrato», decisão D5) quem aplica é **produto**: o passo de completude da spec cita o padrão pelo nome (`padrão: <nome>`) na base da decisão `[CP-n]` do bloco 15, e o de acordo de produto lista cada padrão citado como «padrão aplicado» — sem aceite item a item (enquanto este arquivo for rascunho, «padrão a confirmar»). O D0-UX, no design, só detalha a tela do que a spec de produto já decidiu (a tela de cada estado, o gesto, a adaptação de tela por cenário) e aplica os padrões de UI que ela ainda não trouxer (`gesto-com-demonstracao`, `nada-so-por-cor`). Retenção de dados e revezamento têm referência própria: `padrao-plataforma-retencao-lgpd.md` e `padrao-plataforma-revezamento.md` (D6).

**Nenhum número aqui é fonte.** Padrão de duração, de opções ou de etapas cita `literatura-cognitiva.md` pela seção; o valor pode aparecer como lembrete, mas quem vale é a fonte. Foi assim que este arquivo carregou por semanas tetos de duração revogados (12/15/20 min) sem que ninguém percebesse.

**O que este arquivo não é.** Padrão não substitui mecânica. Se aplicar um padrão exige inventar o que o estudante faz, quantas decisões toma ou que dado é coletado, a lacuna é vermelha e vai ao Gate 0 — não importa quão razoável o padrão pareça.

**Ordem de preferência (completude de produto e D0-UX):** padrão daqui → missão irmã no catálogo → one-pager → inferência. Padrão marcado 🟡 exige que a decisão saia **amarela** (reversível, com "Quem deve olhar" no relatório), porque a plataforma ainda não fechou a resposta.

Cada padrão diz de onde saiu. Padrão sem fonte não entra — vira candidato em `candidatos-a-criterio.md` até alguém confirmar.

---

## Classe `estado` — estados de falha e espera (bloco 2)

| Nome | Padrão | Fonte |
|---|---|---|
| `erro-na-voz-da-ficcao` | Todo modo de erro (conexão, sessão expirada, mídia que não carrega) é um **estado próprio, nomeado**, com texto na voz da plataforma simulada — nunca mensagem técnica, nunca confundido com decisão do estudante. Estados mínimos: `<AMB>_SEM_CONEXAO`, `<AMB>_SESSAO_EXPIRADA`, `<AMB>_MIDIA_FALHOU`. Cada um é registrado no bloco 9 como grau `none` para as medidas daquela tela — nunca como decisão do estudante (critério 9.4, teste de contaminação). | formato-spec bloco 2 · DES-13 |
| `estado-salvo-no-servidor` | Reentrada (F5, voltar noutro dia) devolve o estudante **exatamente onde parou**: estado 100% salvo no servidor a cada transição. Nada se perde por recarregar. | critério 4.6 (gate estrutural) |
| `espera-de-professor` | Toda tela ligada a um handoff tem o estado **"Espera de professor"**: a tela congela sem affordance de avanço e mostra, na voz da ficção, que a turma está junta agora. Nenhum botão de voltar, fechar ou áudio. | pronto.md (wireframes) · prompt-base (tela de congelamento) |
| `vazio-e-carregando` | Toda lista, mural ou feed tem estado **vazio** e **carregando** na voz da ficção (indicador de carregamento do próprio ambiente, não da Unooria). | pronto.md (wireframes) · DES-13 |
| `degradado-2-4` | Cenário 2–4 por aparelho tem estado **degradado** explícito por tela: o que muda quando a tela é compartilhada (quem toca, quem decide, como a evidência é registrada por grupo). | critério 10.1 · d5 (estados obrigatórios) |
| `conclusao-congela` 🟡 | Ao concluir, a plataforma **congela** as escolhas (nada reabre), **reporta** ao painel docente e **ainda permite** rever o que foi feito em modo leitura. Reabrir escolha depois de concluir não existe. | formato-spec bloco 2 · confirmar com produto se "modo leitura" é padrão |

## Classe `handoff` — gatilhos e comportamento durante a mediação (bloco 8)

| Nome | Padrão | Fonte |
|---|---|---|
| `gatilho-pelo-painel` | Quando o one-pager implica mediação mas não diz o que a aciona, o gatilho padrão é **decisão da professora pelo painel docente** (botão de pausar/liberar), não timer nem porcentagem da turma. Timer e "70% chegou" só quando a spec pede. | critério 4.1 (teste de handoff) |
| `plataforma-trava-na-mediacao` 🟡 | Durante a mediação, a plataforma **trava** (estado `espera-de-professor`), não continua em segundo plano. Liberação pelo painel. "Continua rodando" só quando a spec diz que a mediação é paralela à ação. | critério 4.1 · confirmar com produto |
| `liberacao-coletiva` | A liberação depois da mediação é **da turma inteira de uma vez**, pelo painel. Não existe liberação individual. | critério 4.6 · pronto.md |
| `quem-termina-antes-revisa` | Quem termina antes do handoff **revisa ou explora** o que já fez, com affordance nativa do ambiente (editar, reordenar, rever) — nunca tela de espera vazia, nunca liberação antecipada da virada. | critério 6.2 (espera) · padrões P2, P3 |

## Classe `evidencia` — o que é capturado quando a decisão já está definida (bloco 9)

| Nome | Padrão | Fonte |
|---|---|---|
| `evidencia-e-a-decisao` | A evidência de uma decisão é **a própria decisão registrada** (o que foi escolhido, entre quais opções, em que ordem, em que etapa) — não uma captura de tela, não um texto explicando. Se a spec define a decisão, a evidência é derivável. | formato-spec bloco 9 |
| `grau-de-medida-default` | Toda medida nasce `indicative` (1 sinal, texto, fora das médias). Só vira `scored` quando a spec nomeia ≥ 2 sinais independentes. `zero` e `none` são sempre distinguidos: quem não teve a chance não conta como recusa. | formato-spec bloco 9 (graus de medida) |
| `canal-operacional-so-para-mecanica` | Dado que alimenta a mecânica em tempo real vai no canal **operacional**; todo o resto é **analítico**, em lote. Tempo de exploração e dwell nunca no analítico. | formato-spec bloco 9 (canal por dado) |
| `reflexao-e-texto-livre-de-menor` | O campo de reflexão do critério 1.6 é texto livre de menor: vai em **tabela própria, lida só pela professora da escola**, nunca na telemetria. Payloads aceitam só número, booleano ou vocabulário fechado. | formato-spec bloco 9 |

## Classe `dispositivo` — cenários (bloco 10)

| Nome | Padrão | Fonte |
|---|---|---|
| `tres-cenarios` | Os três cenários existem sempre: **1:1**, **2–4 por aparelho**, **projeção única**. Para cada um a spec responde "o que muda" e "a descoberta chega?". | critério 10.1 |
| `1-1-e-o-cenario-base` | O cenário 1:1 é o de referência: o wireframe é desenhado para ele e os outros dois derivam. | d2, d5 |
| `2-4-decide-em-grupo-registra-por-grupo` 🟡 | Em 2–4 por aparelho, **a conta é do grupo**, com identidade escolhida pelo grupo por affordance nativa (nome de usuário, nome no grupo, foto entre as do banco); a decisão é do grupo e a evidência é **por grupo**, não por criança; a plataforma não tenta inferir quem tocou. A missão não prescreve revezamento: o protocolo é padrão da plataforma (`padrao-plataforma-revezamento.md`, D6). | critério 10.1 · bloco 9 (não rotular estudante, 8.4) · confirmar com dados |
| `projecao-e-conduzida-pela-professora` | Em projeção única, quem toca é a professora e a turma decide em voz alta; a tela usa o viewport docente/projeção 1366×768, alvos ≥ 88×88, e a descoberta precisa chegar **sem** a mecânica individual. Se não chega, a spec tem que dizer o que substitui. | critério 10.1 · d4b (88×88) · d5 |

## Classe `copy-fonte` — o que a professora diz e o que o guia fala (bloco 8)

| Nome | Padrão | Fonte |
|---|---|---|
| `roteiro-tres-perguntas` | A roda de conversa tem **≥ 3 perguntas escritas**, na ordem: (1) o que você viu / o que aconteceu, (2) por que você acha que aconteceu, (3) e fora da simulação, onde isso acontece? Sem lição de moral, sem "certo/errado". | critério 4.2 (pedagógico) · 4.7 (tom) |
| `instrucao-de-gatilho-para-professora` | Para cada handoff, uma linha de instrução para a professora: o que ela vê no painel, o que aperta, o que diz à turma. É copy-fonte que o D4 reescreve, não texto final. | critério 4.1 · d4b (linha de instrução) |
| `guia-fala-no-escape-nao-no-clone` 🟡 | O personagem-guia fala nas telas de contexto (antes) e de reflexão (depois). Dentro do clone ele **não aparece**, salvo quando a spec o coloca como conta dentro do ambiente. Onde o one-pager dá direção mas não texto, o D0 escreve o **propósito** da fala, não a fala — a fala é do D4. | DES-13 · d4 (registros de voz) · confirmar |
| `estudante-nunca-aluno` | Toda copy-fonte usa **estudante**, nunca aluno; mural, publicação, marca, curtida conforme o glossário da missão. | critério 4.7 (tom) · glossário |

## Classe `acessibilidade` (bloco 7)

| Nome | Padrão | Fonte |
|---|---|---|
| `audio-autoplay-1-2` | Em 1º–2º ano, todo texto voltado ao estudante é **narrado em áudio** (toca sozinho); texto na tela é reforço. Rótulos curtos com ícone não exigem narração. | critério 6.1 (v1.19) |
| `texto-icone-audio-anos-iniciais` | Toda instrução acionável em anos iniciais entra como `texto + ícone + áudio`. | pronto.md (copy-ptbr) |
| `alvo-64-88-vao-16` | Alvo de toque ≥ 64×64 px no aparelho, ≥ 88×88 na projeção, vão ≥ 16 px. | d4b · pronto.md (caa) |
| `gesto-com-demonstracao` | Gesto que não seja toque simples (arrastar, segurar, deslizar) exige demonstração animada no primeiro uso. | formato-spec bloco 7 · critério 6.3 (scaffolding) |
| `nada-so-por-cor` | Nenhuma regra, estado ou feedback comunicado só por cor. | d9 (restrições) · WCAG |

## Classe `dados` (bloco 9)

| Nome | Padrão | Fonte |
|---|---|---|
| `so-o-que-a-decisao-produz` | Quando o bloco 9 não lista os dados, a completude de produto lista **apenas** o que as decisões já definidas produzem (escolha, opções, ordem, etapa, cenário de dispositivo). Nome, voz, imagem, texto livre e tempo de tela **não entram** por padrão. | d0 (autoridade) · bloco 9 (lista do que não é coletado) |
| `retencao-declarada-ou-lacuna` 🟡 | Sem prazo de retenção na spec, a completude de produto cita o padrão `retencao-lacuna-assumida` (`padrao-plataforma-retencao-lgpd.md`): lacuna com dono **responsável de dados**, sem prazo inventado. | DAD-10 |
| `servidor-calcula` | O cliente envia medidas brutas; o servidor deriva tudo o que vira número. Gabarito, parâmetros e prompt de sistema nunca vão ao bundle. | formato-spec bloco 9 |
| `sem-placar-entre-estudantes` | Nada ordena, pontua ou cronometra crianças entre si. Consequência e hierarquia existem **dentro da simulação**, nunca como avaliação da criança. | critério 3.3 · 8.5 · PED-07 |

## Classe `duracao` (bloco 6)

| Nome | Padrão | Fonte |
|---|---|---|
| `teto-por-ato` | Ato dentro do teto da faixa em `literatura-cognitiva.md` §3 (1º–2º: 6–8 min · 3º–5º: 8–10 · 6º–9º: 10–12 · EM: 12–15), e missão inteira ≤ 25 min de tempo-aluno em aula de 50. Sem estimativa na spec, a completude de produto usa o teto da faixa como **máximo** e marca amarelo. Os valores antigos (12/15/20) foram revogados na revisão de setembro de 2026 da fonte. | critério 6.2 · `literatura-cognitiva.md` §3 |
| `piso-conta-consumo-e-negociacao` | A estimativa inclui consumo de conteúdo, navegação e negociação em grupo — não só a decisão. | critério 6.2 (piso) |
| `fase-de-minijogo` | Mini-jogo: fase ≤ ~90 s em 1º–2º, ≤ ~180 s em 3º–5º. | produto (adequação por faixa em `ambiente-e-minijogo.md`; era do d9 até o PR 8) |

## Tetos de referência (não são padrões — são a régua que a completude e o D0 não podem ultrapassar)

| Faixa | Opções por comparação | Decisões significativas | Etapas cognitivas sem apoio |
|---|---|---|---|
| Anos iniciais (1º–5º) | ≤ 2–3 | 1–2 | 2 (observar → decidir) |
| Anos finais (6º–9º) | ≤ 3–4 | 2–3 | 3 |
| Ensino Médio | ≤ 4 | 3–4 | 3+ |

Fonte: `literatura-cognitiva.md` §1 (opções) e §4 (etapas cognitivas), via critérios 3.5 e 6.3. **Nenhum número deste arquivo é fonte: quando a fonte única mudar, este arquivo muda junto** (`scripts/conferir_referencias.py` acusa a divergência). Decisão `[D0-n]` que aproxime a missão desses tetos é sinal de que a lacuna era de mecânica — vermelha.

## Regra de manutenção

Padrão entra aqui quando o D0 aplicou a **mesma inferência em três missões** (o próprio D0 reporta isso no Passo 6) e alguém do produto confirmou. Padrão 🟡 vira definitivo quando a confirmação chega; padrão que uma spec contradiz explicitamente perde para a spec — a spec é contrato, o padrão é ausência preenchida.
