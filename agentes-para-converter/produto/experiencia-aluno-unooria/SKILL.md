---
name: experiencia-aluno-unooria
description: "Avalia se a experiência de uma missão Unooria funciona de verdade para um aluno daquela idade específica: carga de decisões, linguagem, duração dos atos, complexidade cognitiva, repertório de ações. Simula a perspectiva do aluno em vez de checar formato. Fundamentada na mesma literatura cognitiva que a rubrica original já citava (Piaget, Pascual-Leone, Cowan, Gathercole, Iyengar/Schwartz) — ver references/literatura-cognitiva.md para o que cada fonte sustenta e onde os números da rubrica são extrapolação, não dado direto. Use depois que a missão passou no gate estrutural. Roda sempre que Vini pedir para avaliar se a missão está adequada pra idade, se a carga cognitiva faz sentido, ou mencionar 'faixa etária', 'carga cognitiva', 'complexidade pra idade'."
---

# Experiência do Aluno por Faixa Etária — Missões Unooria

Esta skill responde: **um aluno real dessa idade consegue viver essa experiência do jeito que ela foi desenhada, sem sobrecarga e sem ficar aquém do que ele é capaz?**

Pressupõe que a missão já passou pelo `gate-estrutural-unooria` — avaliar carga cognitiva num documento com seções faltando ou ambiente errado é calibrar em cima de algo que ainda vai mudar.

Esta é a skill que existe porque a rubrica original errava sistematicamente aqui: os critérios de faixa etária competiam por atenção com outros ~30 critérios de natureza totalmente diferente (formato, professor, BNCC). Aqui eles têm o espaço todo.

A tabela de critérios está em `references/criterios-experiencia.md`. A fundamentação cognitiva por trás de cada cap numérico está em `references/literatura-cognitiva.md` — **leia os dois antes de avaliar**, principalmente se for a primeira vez usando esta skill ou se o critério gerar dúvida sobre o "porquê" do número.

## Escopo: 11 critérios (10 obrigatórios + variações por faixa)

| Categoria | Critérios nesta skill | O que avalia |
|---|---|---|
| 3. Agência do aluno | 3.1–3.6 | Carga decisória, volume sequencial, significado da ação |
| 6. Adequação etária | 6.1–6.5 | Linguagem, duração, complexidade, ambiente plausível, repertório |

## Como avaliar — protocolo de simulação, não checklist

A diferença desta skill para as demais: não basta marcar ✅/❌ contra um teste prático. Antes de julgar cada critério, **simule ativamente o aluno daquela idade específica usando a missão**, apoiado no perfil cognitivo de `literatura-cognitiva.md`. Pergunte:

- Nessa idade, o aluno consegue manter na cabeça as opções que essa decisão pede, ao mesmo tempo? (ver M-capacity/Pascual-Leone e Cowan/Gathercole na literatura)
- Se ele já fez essa mesma decisão N vezes antes nesta missão, a N-ésima ainda tem a mesma qualidade de atenção que a primeira?
- O tipo de raciocínio que a decisão pede (concreto vs. abstrato) é compatível com o estágio cognitivo dessa idade? (ver Piaget na literatura)
- Ele tem repertório de leitura pra decifrar esse texto sem ajuda?
- Se ele terminar antes dos colegas e depender de um handoff coletivo, existe algo útil e compreensível para fazer sem acessar antecipadamente a virada?

Só depois de passar por essas perguntas, aplique o teste prático formal do critério.

### Passos

1. **Identifique o ano/série** e localize a faixa correspondente: anos iniciais (1º-5º EF), anos finais (6º-9º EF), Ensino Médio. Dentro de anos iniciais, distinga 1º-2º EF de 3º-5º EF quando o critério exigir (3.5 e 6.1 têm sub-faixas — ver `criterios-experiencia.md`).

2. **Leia `references/literatura-cognitiva.md`** e monte mentalmente o perfil cognitivo da faixa antes de olhar a missão — isso evita ancorar no que a missão "parece pedir" e julgar de trás pra frente.

3. **Percorra os critérios em ordem**, marcando ✅ / ❌ / ⚠️ / "N/A — falta informação", sempre citando o teste prático da rubrica, nunca uma opinião solta.

4. **Preste atenção aos falso-negativos e falso-positivos históricos documentados em `criterios-experiencia.md`** — a maioria das falhas reais da rubrica antiga aconteceu exatamente nesses padrões (volume sequencial disfarçado de decisão individual, 3 etapas cognitivas sem scaffolding, ambiente tecnicamente válido mas implausível pra idade).

5. **Teste o ritmo de espera nos handoffs coletivos.** Se parte da turma pode terminar antes, simule esse intervalo: espera passiva longa ou sem tarefa é risco de engajamento e gestão; revisão, exploração adicional ou outra ação coerente pode funcionar desde que não aumente carga desnecessária nem revele o resultado antes da hora.

6. **Quando o número da rubrica for extrapolação da literatura (não dado direto)** — marcado como tal em `literatura-cognitiva.md` — trate o cap como heurística de trabalho, não verdade absoluta. Se a missão está no limite (ex: 5/6 decisões pro cap de anos iniciais) e o resto do desenho é sólido, isso é ⚠️ com nota de risco, não ❌ automático. Se está claramente acima (8+ pra anos iniciais), é ❌ sem ambiguidade.

## Formato da saída

1. **Veredito no topo**: experiência adequada pra faixa / bloqueada por N critérios / adequada com ressalvas.
2. **Simulação do aluno primeiro, em prosa curta** (3-5 linhas): como um aluno dessa idade viveria a missão, ponto a ponto — isso é o que torna a avaliação legível pro Vini, não só uma tabela de símbolos.
3. **Tabela só dos critérios não-✅**: número, nome, status, motivo citando o teste prático + a fonte cognitiva quando relevante.
4. **Lista dos ❌ obrigatórios** isolada, com correção pronta — se o volume de decisões estoura o cap, corte itens específicos do banco preservando a proporção de tipos; se falta scaffolding, escreva a instrução visual do primeiro uso.
5. Critérios ✅ não precisam de explicação longa.

## Relação com as demais skills

```
gate-estrutural-unooria (já rodou) → Missão estruturalmente correta
    ↓
avaliacao-pedagogica-unooria (pode rodar em paralelo) → BNCC, professor, guardrails
    ↓
>>> ESTA SKILL (experiencia-aluno-unooria) <<<
    ↓
gate-final-unooria → coerência final e liberação para design/dev
```

Se o Vini pedir “roda tudo”, esta skill roda depois do gate estrutural e pode rodar em paralelo com a pedagógica; depois das duas, `gate-final-unooria` é obrigatório para liberar design/dev.
