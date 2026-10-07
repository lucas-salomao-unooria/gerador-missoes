---
name: literatura-cognitiva-resumo
description: Resumo operacional da régua por idade — só as tabelas e as regras de aplicação da fonte única, para os agentes de design. Gerado; não edite à mão.
sources: [literatura-cognitiva.md]
---

# Régua por idade — resumo operacional

> **Gerado automaticamente** de `literatura-cognitiva.md` por `scripts/gerar_resumo_literatura.py`. Não edite à mão: edite a fonte e regenere. SHA-256 da fonte: `afe07c3a8b4052ea8c1f128fc2f14ea39b21395e73ca8f8f62945f90b0ed7dd5`.

Esta é a **fonte única dos números** que a esteira usa para julgar se uma missão cabe na idade, em uma página. Todo número é **[DADO DIRETO]** (medido), **[EXTRAPOLAÇÃO]** (derivado de princípio) ou **[CONVENÇÃO]** (escolha da equipe); extrapolação justifica ⚠️ com mais frequência que ❌. A fundamentação e as citações estão na fonte — aqui só o que se aplica ao construir tela, copy e jornada.

## Opções comparadas ao mesmo tempo numa decisão (fonte §1)

| Faixa | Teto | Marca |
|---|:-:|---|
| 1º–2º EF (6–7 anos) | **2** | [EXTRAPOLAÇÃO de base direta forte] |
| 3º–5º EF (8–10 anos) | **3** | [EXTRAPOLAÇÃO de base direta forte] |
| 6º–9º EF (11–14 anos) | **3–4** | [EXTRAPOLAÇÃO] |
| Ensino Médio (15–17 anos) | **4** | [EXTRAPOLAÇÃO, corrigida para baixo nesta revisão] |

**Opção visível não é opção lembrada.** Se todas as alternativas permanecem na tela enquanto o estudante decide, o gargalo deixa de ser memória de trabalho e passa a ser comparação atencional — nesse caso o teto sobe em **+1**. Se ele precisa lembrar de opções que saíram da tela, vale o teto da tabela, sem acréscimo. Esta distinção era a maior imprecisão da versão anterior.

## Duração (fonte §3)

| Faixa | Teto por ato | Marca |
|---|:-:|---|
| 1º–2º EF | **6–8 min** | [EXTRAPOLAÇÃO de base direta] |
| 3º–5º EF | **8–10 min** | [EXTRAPOLAÇÃO de base direta] |
| 6º–9º EF | **10–12 min** | [EXTRAPOLAÇÃO] |
| Ensino Médio | **12–15 min** | [EXTRAPOLAÇÃO] |

**Teto agregado da missão inteira: ≤ 25 minutos de tempo-aluno em aula de 50 min; ≤ 20 min em aula de 45 min.** Este teto é novo e é o mais importante: sem ele, três atos de 15 minutos somam 45 e não sobra aula. **[EXTRAPOLAÇÃO de base direta]**

## Abstração: as portas por idade (fonte §4)

| O que se pede | A partir de | Fonte |
|---|---|---|
| **Descrever** o comportamento ("o app me mostra mais vídeo de gato") | ~8 anos | Starks & Reich (2024) |
| **Explicar** o mecanismo (dados → inferência → recomendação) | 10–11 anos | Starks & Reich (2024) |
| **Criticar** a intenção e o viés, com apoio | 12–13 anos | estudo suíço (2024); Rozendaal et al. |
| **Criticar** de forma autônoma | 14+ anos | [EXTRAPOLAÇÃO] |

## Narração e redundância (fonte §5)

**Narrar ajuda quando:** (a) não há animação ou gráfico concorrente disputando o olhar; (b) o estudante ainda não decodifica com fluência — aí o texto **não** é segunda cópia da mesma informação, porque decodificar é em si uma tarefa cara; (c) os segmentos são curtos e há replay sob controle do estudante.

**Narrar atrapalha quando:** há visual concorrente e a narração é palavra por palavra do texto; o texto é longo e o ritmo é do sistema; o estudante já lê com fluência — aí o áudio vira ruído por *expertise reversal*.

**Consequência prática:** a exigência de narração vale para 1º–2º ano e **deve ser removida a partir do 3º**, ou quando houver sinal de fluência. Scaffolding que não é removido vira obstáculo.

## O cenário de piso da escola pública (fonte §6)

| Parâmetro | Piso realista | Observação |
|---|---|---|
| Alunos por turma, anos iniciais | **25** | a média oficial é 22,3 — afirmar "30 a 40" infla a dificuldade |
| Alunos por turma, anos finais e Médio | **32** | 26,6 no Censo; 32,5 na turma de referência do TALIS |
| Dispositivo | **nenhum fornecido pela escola** | só 47% das escolas disponibilizam computador ao aluno; o piso não é compartilhar, é não ter |
| Internet | **assumir queda ou sinal ausente em sala** | 96% das escolas têm internet, mas 39% das estaduais relatam que o sinal não chega à sala |
| Leitura, 5º ano | 39% abaixo do adequado | **60,7% estão adequados** — tratar anos iniciais como majoritariamente defasados contraria o Saeb 2025 |
| Leitura, 9º ano | **62% abaixo do adequado** | aqui a defasagem se confirma |
| Leitura, Ensino Médio | **65% abaixo do adequado** | 50% abaixo do Nível 2 do PISA aos 15 anos |
| Professor | sem formação recente em tecnologia | 46% não tiveram; só ~1/3 decide sobre uso de recurso digital; **43%** com formação continuada na rede municipal, que concentra os anos iniciais (TIC Educação 2024) |
| Preparo docente | cinco telas obrigatórias (`E0-PROF-01…05`) | **sem tempo medido**; a contagem de telas e toques exigida pelo 4.3 é [CONVENÇÃO] — acordo interno, não medida |
| Duração da aula | 50 min é **parâmetro de rede** | a LDB fixa carga anual (800h no EF, 1.000h no EM), não duração de aula |

## Que plataforma a criança usa, por idade (fonte §10)

| Indicador | 9–10 | 11–12 | 13–14 | 15–17 |
|---|:-:|:-:|:-:|:-:|
| Tem perfil em alguma rede social | 60% | 70% | 93% | 99% |
| Plataforma mais usada várias vezes ao dia | YouTube | transição | Instagram | Instagram |

- **(a) 3º–5º ano:** o ambiente de consumo mais plausível é YouTube (`unootube`, hoje arquivado — ADR-116); WhatsApp é plausível como *grupo da família ou da turma*, não como conta pessoal.
- **(b) 6º–7º ano:** zona de transição — qualquer um dos cinco é defensável, e a spec justifica na seção 18.
- **(c) 8º ano em diante:** Instagram, TikTok e WhatsApp são os de maior uso.
- **(d) 1º–2º ano:** sem dado. Presumir uso mediado por adulto e sem perfil próprio, o que faz da "primeira conta" um evento diegético legítimo (ver Regra 15 do P0a). **[EXTRAPOLAÇÃO]**
- **(e) Aos 9–10 anos, 40% não têm perfil algum.** Missão dessa faixa que pressupõe conta declara, na seção 18, o que faz com quem nunca teve uma.

## O que NÃO sustenta a régua (fonte §7)

Não use como fundamentação (refutado ou sem fonte primária):

- **Choice overload** como base de teto de opções
- **Decision fatigue / ego depletion** como base de teto de volume
- **"Idade da criança = minutos de atenção"**
- **Piaget para vetar abstração por idade**

## Como usar

- **Teto é sinal, não veredito:** nenhum número desta página foi medido com missões da Unooria (fonte §9). No limite, com desenho sólido, é ⚠️; claramente acima, ❌.
- **Layout muda o teto:** se todas as opções ficam na tela enquanto o estudante decide, o teto de opções sobe +1 (§1). É a distinção que mais importa para quem desenha tela.
- **Formato pesa mais que duração:** atividade individual ou em pequeno grupo sustenta atenção melhor que turma inteira (§3).
- **Chrome nativo não conta** como elemento novo: ícone de coração e botão de play já estão automatizados (§5).
