---
name: gate-estrutural-unooria
description: "Gate de completude estrutural e fechamento de spec de missões Unooria — checa se o documento está completo, o ambiente é válido, os verbos são nativos, modularidade/tempos sugeridos/checkpoints/dispositivos estão mapeados e, principalmente, se designer e dev conseguem implementar sem inventar regra de produto. Use sempre que Vini pedir para validar uma missão, rodar a rubrica ou checar se está pronta. Roda PRIMEIRO, antes de avaliacao-pedagogica-unooria e experiencia-aluno-unooria; missão com obrigatório aberto não segue na esteira."
---

# Gate Estrutural — Missões Unooria

Esta skill é o primeiro filtro de validação. Ela responde duas perguntas: **o documento da missão está completo?** e **a spec está fechada o suficiente para designer/dev implementarem sem tomar decisões que mudem a experiência?**

Não avalia qualidade pedagógica (isso é a `avaliacao-pedagogica-unooria`). Não avalia se a experiência funciona pra faixa etária (isso é a `experiencia-aluno-unooria`). Avalia completude, conformidade e fechamento operacional da spec.

A tabela completa de critérios está em `references/criterios-gate.md` — leia antes de avaliar.

## Escopo: 23 critérios (19 obrigatórios + 1 condicional + 3 desejáveis)

| Categoria | Critérios nesta skill | Natureza |
|---|---|---|
| 1. Estrutura (6 etapas) | 1.1–1.7 | Obrigatório |
| 2. Ambiente e verbos | 2.1, 2.6 | Obrigatório |
| 4. Logística de aula e modularidade | 4.5, 4.6, 4.7 | Obrigatório |
| 7. Evidência e registro | 7.1–7.4 | Obrigatório (7.4 como sugestão) |
| 9. Viabilidade e fechamento de spec | 9.1 obrigatório; 9.2–9.4 (9.4 obrigatório, 9.2–9.3 desejáveis) | Implementabilidade sem decisão aberta |
| 10. Infraestrutura | 10.1–10.3 | Obrigatório (10.3 desejável) |

## Como avaliar

1. **Leia `references/criterios-gate.md`** — contém o texto exato de cada critério e teste prático.

2. **Identifique o ano/série** — muda o que é aplicável em 2.1 (qual dos 6 ambientes é plausível pra idade).

3. **Confira PRIMEIRO o critério 2.1** (ambiente na lista fechada). Se o ambiente não é um dos 6 (Instagram, YouTube, Roblox, ChatGPT, TikTok, WhatsApp), a missão reprova direto. Nesse caso:
   - Escolha qual dos 6 é mais plausível pro ano/atividade da missão.
   - Reescreva as partes que dependem do ambiente antigo: etapa Navegar, verbos de interação, qualquer texto que nomeie a plataforma errada.
   - Entregue como "proposta de migração de ambiente" no veredito.

4. **Percorra os demais critérios em ordem**, marcando cada um como:
   - ✅ cumpre
   - ❌ não cumpre
   - ⚠️ cumpre parcialmente (justificar em 1 frase)
   - "N/A — falta informação" quando o material não permite julgar

5. **Mecanismo definido, ou só intenção declarada? (Passo 4.3)**

   Para **cada etapa**, pergunte: o documento diz *como* aquilo acontece, ou apenas *o que se espera que aconteça*?

   Intenção declarada tem a forma de resultado desejado — *"o estudante abre os duetos e descobre"*, *"a turma percebe a diferença"*, *"o aluno compara os dois"*. Mecanismo tem a forma de regra do sistema: o que a plataforma ordena, bloqueia, apresenta primeiro, ou garante.

   **Quando a intenção depende de uma sequência, a sequência é mecanismo e precisa estar escrita.** Se a descoberta só funciona caso o aluno investigue o item A antes do item B, o documento tem que dizer como o sistema garante isso — ordenação, bloqueio, ou apresentação. "O aluno provavelmente vai fazer" não é mecanismo; é aposta na sorte.

   Intenção sem mecanismo em etapa que carrega a descoberta central → **❌**. Em etapa secundária → **⚠️**.

6. **Caminhos degenerados (Passo 4.4)**

   Rode a missão mentalmente com o aluno que faz o mínimo. Para cada caminho abaixo, alguma etapa deixa de acontecer?

   - **Não escolheu nada** — passou todos os itens, não salvou nenhum, não marcou nenhum
   - **Escolheu tudo** — salvou todos, sem discriminar
   - **Não usou a ferramenta** de investigação em nenhum momento
   - **Fez o mínimo de exploração** — viu o número mínimo de itens e avançou
   - **Terminou muito antes** do resto da turma

   Etapa que só funciona para o aluno que se comportou como esperado é etapa que não funciona. Se a tela de resultado depende de o aluno ter feito alguma escolha e ele não fez nenhuma, ele fica sem a virada — e é ❌, não estado vazio de wireframe.

   Este teste é barato e pega o que a leitura linear do documento nunca pega, porque o one-pager narra o aluno ideal.

7. **A mecânica sustenta a descoberta central? (Passo 4.5)**

   Teste de 30 segundos: leia a frase da descoberta central. Leia o que a **plataforma faz** na etapa Resultado. Uma nega a outra?

   Uma missão pode passar em 2.1, 2.2 e 2.4 individualmente e ainda entregar a lição invertida — se a frase diz "a plataforma não te avisa" e a mecânica faz a plataforma avisar, o aluno sai tendo vivido o contrário do que a missão afirma ensinar.

   **Estenda a checagem aos artefatos secundários.** Roteiro de podcast, falas do personagem-guia, textos do professor, roteiro de perguntas: todos descrevem a mecânica, e todos podem contradizê-la. Leia esses trechos contra a mecânica, não isolados.

8. **Execute o teste de implementação cega após os critérios (9.1).** Percorra cada ato como máquina de estados e registre: pré-condição → ação → regra → mudança de estado → caminho incompleto → próximo estado → ator responsável. Pergunte: "Se eu entregar somente este documento para designer e dev, eles precisam inventar alguma regra que altere a experiência pedagógica ou o comportamento do produto?" Se sim, 9.1 = ❌.

9. **Para cada ❌ obrigatório, escreva usando o formato de remediação:**

   **ONDE** (etapa/seção exata) · **POR QUÊ** (o teste que falhou e o que o documento diz ou não diz) · **IMPACTO** (o que quebra pro aluno) · **COMO** (2 a 3 alternativas, cada uma com: affordance nativa usada, custo de implementação, critério que resolve e risco que abre) · **Recomendação**.

   Restrições que toda alternativa proposta precisa respeitar:
   - Fica dentro dos 6 ambientes suportados (2.1)
   - Usa verbo nativo da plataforma real (2.6)
   - Não ultrapassa os tetos da faixa etária (3.5)
   - Preserva a descoberta central (Passo 4.5)

   Se **nenhuma** alternativa dentro dos 6 ambientes resolver, diga isso explicitamente: a missão precisa mudar de mecanismo, não forçar encaixe.

   Não pare no diagnóstico. Não pare em "falta roteiro do podcast" — escreva o roteiro. Não pare em "falta modularidade/tempos sugeridos" — escreva a tabela de etapas e cenários de aula. A correção mantém o tom, o ambiente e o mecanismo da missão.

## Veredito — binário

| Veredito | Condição |
|---|---|
| 🟢 **APROVADO** | A spec está completa. Todo obrigatório ✅, toda decisão fechada, todo mecanismo escrito, todo caminho tratado. A esteira pode construir do início ao fim sem perguntar nada. |
| 🔴 **BLOQUEADO** | Qualquer outra coisa. |

**"Aprovado com ressalvas" não existe.** Era o depósito do que ninguém queria decidir, e o custo aparecia dois agentes depois.

Uma ⚠️ só sobrevive ao gate se você **nomear os agentes a jusante e demonstrar que nenhum deles precisa daquilo**. Requisito técnico ausente não é ressalva: designer/dev precisam dele. Ambiente em aberto não é ressalva: a experiência depende dele. Código BNCC não confirmado não é ressalva: ele sustenta o argumento curricular.

O teste é único: **a esteira consegue ir do começo ao fim sem voltar aqui?** Se não, é 🔴.

## Formato da saída

### Saída 1 — Relatório completo

1. **Veredito no topo**: 🟢 / 🔴 e contagem de ❌ obrigatórios.
2. **Tabela só dos critérios não-✅**: número, nome, status, motivo em 1-2 frases.
3. **Lista dos ❌ obrigatórios** isolada.
4. **Remediação estruturada para cada ❌** (formato ONDE/POR QUÊ/IMPACTO/COMO/Recomendação).
5. **Bloco "Decisões de implementação ainda abertas"**: listar qualquer regra, cardinalidade, estado ou ownership que designer/dev ainda precisariam decidir. Vazio quando 9.1 = ✅.
6. **Bloco "Complemento — pronto pra colar"**: todas as correções num texto único, na ordem das seções do one-pager, pra colar direto no documento.

Critérios ✅ não precisam de explicação longa — só liste que cumprem.

### Saída 2 — Relatório executivo (obrigatório, sempre)

O relatório completo é para quem vai corrigir. O executivo é para quem vai **decidir**. Gerar sempre, mesmo quando o veredito é 🟢.

Regras:
- Um bullet por achado, no máximo duas linhas. Não couber = mal formulado, ou são dois achados.
- Todo bullet começa com o código do critério. Sem código, é opinião.
- Todo bullet de 🔴 termina com a correção e o custo.
- O resumo nunca cria achado que não esteja no relatório completo.
- 🔵 é só para o que o gate não deve decidir sozinho — nunca escape para achado com resposta técnica clara.
- Ordene os 🔴 por impacto na experiência do aluno, não por número.

### Saída 3 — Alerta ao Artur (obrigatório em 🔴 e em qualquer 🔵)

Se a missão não passa, ou se há decisão que não é do gate, **avise imediatamente**.

Dispara em: veredito 🔴, ou qualquer 🔵 decisão de produto. Formato: o que trava, o que precisa de decisão dele, menor caminho pro verde, e os links dos relatórios. Curto — o detalhe fica no relatório.

Em 🟢 sem 🔵, não alerte.

### Saída 4 — Sinais de ofício para o briefing (🎨)

Sinais que a leitura levantou sobre forma, ritmo e ênfase: abertura longa, tensão no lugar errado, missão fazendo três coisas mornas, ausência de beat memorável, nada removido do ambiente.

🎨 **nunca bloqueia.** É insumo pro briefing de design. Se você não consegue apontar o beat e sugerir a alternativa, não escreva o sinal.

---

## Ao auditar uma revisão (segunda rodada em diante)

Não basta reverificar o que estava ❌. Toda correção troca uma coisa por outra, e a coisa nova é a que ninguém olhou.

- **Reverifique o que foi corrigido** e diga por que agora cumpre.
- **Audite o que a correção introduziu.** Mecânica que substituiu outra costuma carregar um pressuposto novo — e pressuposto novo sobre a faixa etária vai pro 9.3 como hipótese de validação, com o que observar no teste.
- **Verifique se a correção de um critério derrubou outro** que já passava.
- Registre a mudança de veredito por critério, não só o veredito final.

Segunda rodada que só confirma o que foi pedido é carimbo, não auditoria.

---

## Devoluções de agentes a jusante

**Devolução de agente a jusante é falha do gate, não fluxo normal.** Se a jornada, a copy ou os wireframes encontram lacuna na spec — mecanismo faltando, caminho sem tratamento, decisão em aberto — o gate deixou passar algo que não podia passar.

Quando acontecer:
- Reaudite os critérios afetados
- Corrija a spec
- Regenere os relatórios
- Alerte o Artur
- **Registre a devolução como falha**, com a classe da lacuna

Duas devoluções da mesma classe = passo faltando no gate, não desatenção. A meta é zero devoluções.

---

## Relação com as demais skills de avaliação

```
Gerador → Missão crua
    ↓
>>> ESTA SKILL (gate-estrutural-unooria) <<<
    ↓
avaliacao-pedagogica-unooria → BNCC, professor, guardrails
    ↓
experiencia-aluno-unooria → Carga cognitiva, faixa etária, agência
    ↓
gate-final-unooria → Coerência da saída + liberação para design/dev
```

Missão que não passa no gate NÃO deve seguir para as demais skills — as correções estruturais vão mudar o conteúdo, invalidando a avaliação pedagógica e de experiência. Corrija primeiro, depois avalie.

Se o Vini pedir "roda tudo de uma vez" ou "valida a missão completa", rode a esteira completa: gate estrutural → pedagógica → experiência → gate final. Um ❌ obrigatório neste gate bloqueia as avaliações seguintes até a missão ser corrigida.
