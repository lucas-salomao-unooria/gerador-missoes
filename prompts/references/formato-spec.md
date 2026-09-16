---
name: formato-spec
description: Gabarito da especificação de missão emitida pelo Gate 0 — o contrato que a esteira constrói. Lido por qa-conformidade e por todos os agentes de construção.
sources: [chat]
---

# Especificação de missão → `spec/<missao>-spec.md`

Emitida pelo agente 1 junto com o veredito 🟢. É a **fonte da verdade da construção** — a esteira constrói contra ela, não contra o one-pager. Campo em aberto não existe: se está aberto, a missão não passou.

```markdown
# Spec — <missão> v<x>

**Ano/faixa · Ambiente · Rubrica vX.X · Gate 0 aprovado em <data>**

## 0. Identificação de plataforma
Slug `exp-NN-<nome>` · nome que o estudante vê · série(s) no formato da
plataforma (`["5EF"]`, `["2EM"]`, `[]` = transversal) · unidade da trilha ·
`publico: estudante` · software clonado · **seção do DS** (uma das cinco de
`references/ambientes.md`, ou seção nova com componentes, responsável e
prazo) · viewport (casca 375×812 ou desktop) e por quê.

Campo em branco aqui é ❌ em PROD-01 e TEC-01 do gate de dev, e sem série a
api não aplica regra por ano.

## 1. Descoberta central
<frase única> — e o beat exato em que ela é vivida.

## 2. Mecanismo por etapa
Por etapa (1–6): o que o sistema **apresenta**, **ordena**, **bloqueia** e
**garante**. Não o que se espera do aluno — o que o sistema faz.
Onde a descoberta depende de sequência, a regra de sequência está aqui.

**Contrato de estados — obrigatório.** Uma linha por transição: estado
inicial, gatilho, regra, estado seguinte, responsável. **Estados com nome
próprio**, porque viram enum no código. Fecha com a frase que declara o
conjunto completo: "não existem outros caminhos de conclusão, correção
antecipada, reabertura de escolha ou mudança de pacote". Inclui:
conclusão (quem fecha, o que congela, o que reporta, o que ainda é
permitido) · estados latch · reentrada (F5, voltar noutro dia) · segunda
aplicação (o que re-sorteia, o que preserva, o que "zerar turma" apaga) ·
modos de erro **na voz da ficção**, como estado próprio, nunca confundidos
com decisão do aluno.

## 3. Caminhos degenerados — tratamento
| Caminho | O que acontece | Etapa preservada? |
Não escolheu nada · escolheu tudo · não usou a ferramenta ·
exploração mínima · terminou antes.

## 4. Verbos e affordances
Verbo nativo confirmado por ação, com antes / verbo / depois.

## 5. Ausências declaradas
O que o ambiente simulado NÃO tem, e por que cada ausência existe.
Reaparecimento é violação, não melhoria.

## 6. Tetos aplicados
Decisões do mesmo tipo (com a conta) · duração por ato · etapas
cognitivas por decisão · onde há scaffolding e onde a dica desaparece.

## 7. Acessibilidade
Canais por instrução (áudio / pictograma / texto), teto de palavras,
gestos que exigem demonstração animada.

## 8. Professora, preparação e parametrização com IA
Contrato de customização: inputs aceitos do professor (tema, foco, contexto) · regras e schemas Zod de geração de conteúdo por IA (Vertex AI Gemini) · fluxo de curadoria docente (preview, edição de postagens e aprovação) · banco curado default (fallback imediato sem IA) · gatilhos de handoff · comportamento da plataforma em cada mediação e pausas · dados do dashboard · roteiro de perguntas.

## 9. Evidências e dados
Campo por campo: o que é coletado, quando, finalidade, retenção, acesso.
E a lista do que **não** é coletado nem calculado. Mais, obrigatoriamente:

**Graus de medida.** Por medida: `scored` (≥2 sinais independentes, tem
número) · `indicative` (1 sinal, texto, fora das médias) · `zero` (teve a
chance e não foi — entra na média) · `none` (a oportunidade não chegou —
sai da conta). Tratar "não teve chance" como "escolheu não" faz uma criança
parecer ter recusado o que nunca lhe foi oferecido, e o número será lido
por um adulto que decide sobre ela.

**Canal por dado.** Cada dado em um de dois canais que não se misturam:
**operacional** (alimenta a mecânica em tempo real, rota síncrona) ou
**analítico** (análise posterior, em lote, sem garantia de ordem). Tempo de
exploração e dwell nunca no analítico.

**Texto livre de menor.** Existe? Por quê é necessário? **Quem lê?** Se
existe, vai em **tabela própria, lida só pelo professor da escola** — nunca
na telemetria analítica. Campos de payload aceitam só número, booleano ou
string de vocabulário fechado. O registro da reflexão que o critério 1.6
exige é, por definição, texto livre de menor: é legítimo e **precisa deste
campo preenchido**. O 1.6 e a regra de dados só colidem quando o destino
não está escrito.

**Segredo de servidor.** Lista do que nunca vai ao bundle: gabarito,
parâmetros ocultos, calibragem, vieses, prompt de sistema, e qualquer conta
cujo resultado antecipe o desfecho.

**Gabarito.** Fonte da verdade pedagógica, com **autor e revisor nomeados**
(pessoas, não "time pedagógico"), e a declaração de que vive
exclusivamente no servidor.

**Servidor calcula, nunca aceita.** O que o cliente envia (medidas brutas)
e o que o servidor deriva.

## 10. Cenários de dispositivo
Os três, com o que muda e a garantia de que a descoberta chega.

## 11. Currículo
Habilidades e códigos **confirmados**, com o momento em tela de cada um.

## 12. Decisões fechadas neste gate
Decisão · quem decidiu · data · alternativas descartadas.
```

## Regra de alteração

A spec só muda por reabertura do Gate 0. Agente de construção não edita spec — se ela estiver errada ou incompleta, devolve, e isso é registrado como falha do gate.

**Blocos acrescentados pela esteira de design (não alteram os blocos 0–12).** Depois do Gate 0, dois agentes anexam blocos à spec sem tocar no texto original:

- **Bloco 13 — Decisões D0** (`fecha-lacunas`): decisões `[D0-n]` que preenchem ausências deriváveis da missão, com base declarada, e os pedidos de re-spec `[RS-n]` pendentes. Preenche ausência, nunca altera presença.
- **Bloco 14 — Ambiente simulado** (`ambiente-simulado`): a ficha do ambiente — nome, seção do DS, verbos do bloco 4 com rótulo literal, dispositivo nativo, estados e o que a plataforma real não tem. Emitido mesmo quando a spec já nomeia o ambiente (dormente).

Bloco 0–12 diferente do texto do Gate 0 continua sendo violação; bloco 13 ou 14 ausente numa spec que passou pela esteira de design é sinal de que D0 ou D9 não rodaram.
