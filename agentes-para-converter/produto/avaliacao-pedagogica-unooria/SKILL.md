---
name: avaliacao-pedagogica-unooria
description: "Avalia se o conteúdo pedagógico de uma missão Unooria é sólido: descoberta central, papel do professor e handoffs, BNCC realmente exercitada e verificada, rastreabilidade curricular e guardrails éticos. Julgamento de qualidade de conteúdo — não checklist de formato (isso é gate-estrutural-unooria) nem calibração de faixa etária (isso é experiencia-aluno-unooria). Use depois que a missão passou no gate estrutural. Roda sempre que Vini pedir avaliação pedagógica, checar BNCC, ou avaliar se o professor consegue conduzir a missão."
---

# Avaliação Pedagógica e Papel do Professor — Missões Unooria

Esta skill responde: **o conteúdo pedagógico é sólido, e o professor consegue conduzir a missão com o que está escrito?**

Pressupõe que a missão já passou pelo `gate-estrutural-unooria` — não avalia se as seções existem (isso já foi checado), avalia se o que está escrito nelas tem qualidade pedagógica real.

A tabela completa de critérios está em `references/criterios-pedagogicos.md` — leia antes de avaliar. O catálogo de missões existentes, usado no critério 2.5 (diferenciação), está em `references/catalogo-missoes.md` — é o registro vivo das missões aprovadas; atualize-o quando uma missão nova passar em todos os obrigatórios.

## Escopo: 15 critérios (14 obrigatórios + 1 condicional aplicado como sugestão)

| Categoria | Critérios nesta skill | O que avalia |
|---|---|---|
| 2. Imersão (subset) | 2.2, 2.3, 2.4, 2.5 | Vivência real, descoberta articulada, diferenciação |
| 4. Papel do professor (subset) | 4.1, 4.2, 4.3, 4.4 | Handoffs, mediação, customização, dashboard |
| 5. Habilidades e currículo | 5.1–5.6 | BNCC exercitada de verdade, não só citada |
| 8. Guardrails e ética | 8.1–8.6 | Limites de IA, privacidade, sem julgamento, affordance × guardrail |

## Como avaliar

1. **Leia `references/criterios-pedagogicos.md`** — texto exato de cada critério e teste prático.

2. **Use o material do Entre Redes do bimestre/ano como fonte de verdade quando disponível** — os critérios 5.1, 5.2 e 5.5 exigem checar se as habilidades BNCC citadas na missão são as mesmas do material curricular daquele ano/bimestre, e se cada uma tem um momento concreto de exercício na missão (não é conexão fraca — "toca no tema" não é "exercita a habilidade").

3. **Percorra os critérios em ordem**, marcando cada um como ✅ / ❌ / ⚠️ / 🔵 pendência externa / "N/A — falta informação". Use 🔵 quando o desenho parece adequado mas depende de validação documental/autoritativa que não está disponível.

4. **Separe adequação pedagógica de verificação documental.** Um código BNCC/SAEB pode estar pedagogicamente bem mapeado e ainda não estar oficialmente confirmado. Nunca transforme plausibilidade em ✅ de código. Não reconstrua rastreabilidade semanal a partir do próprio one-pager: a fonte deve ser o material curricular.

5. **Regra de veredito:** nunca emitir “pedagogicamente pronta” se qualquer critério obrigatório estiver ❌, N/A ou 🔵. ⚠️ só pode coexistir com “pronta com ressalvas” quando o risco está explicitamente aceito e não deixa regra, fonte ou requisito obrigatório em aberto.

6. **Trate os condicionais como oportunidade, não reprovação seca:**
   - 5.4 (socioemocional): se a missão já faz isso na prática mas não nomeia, aponte a competência e o momento.
   - 5.6 (SAEB): se não há descritor indicado, sugira ao menos um candidato em linguagem descritiva.
   - 7.4 não está nesta skill (está no gate), mas se aparecer contexto relevante de sinal comportamental durante a leitura, pode observar.
   - 8.2 (guardrail de IA): se a IA responde via modelo de linguagem em tempo real, o guardrail comportamental explícito no one-pager já cumpre o critério.

7. **Preste atenção aos falso-positivos históricos:**
   - 3.3/7.2 não estão nesta skill, mas 8.5 tem risco correlato — em missões individuais com mediação nominal, sinalize risco de exposição social mesmo cumprindo a letra do critério.
   - 4.1 — “professor debate/media na etapa N” sem gatilho descrito é falso-positivo frequente. Além disso, em handoff coletivo, verifique o estado de quem ainda não terminou, de quem já terminou e o que muda quando o professor libera a etapa.
   - 2.5 — consultar `references/catalogo-missoes.md` (nesta skill); se ausente ou vazio, marcar "N/A — catálogo incompleto".

## Formato da saída

1. **Veredito no topo**: pedagogicamente pronta / bloqueada por N critérios obrigatórios ou pendências obrigatórias / pronta com ressalvas. 🔵 obrigatório bloqueia “pronta”.
2. **Tabela só dos critérios não-✅**: número, nome, status, motivo em 1-2 frases citando o teste prático.
3. **Lista dos ❌ obrigatórios** isolada, com correção pronta para cada um (roteiro de perguntas escrito, seção de guardrail escrita — nunca "adicione uma seção sobre X").
4. Critérios ✅ não precisam de explicação longa.

## Relação com as demais skills

```
gate-estrutural-unooria (já rodou) → Missão estruturalmente correta
    ↓
>>> ESTA SKILL (avaliacao-pedagogica-unooria) <<<
    ↓
experiencia-aluno-unooria → Carga cognitiva, faixa etária, agência
    ↓
gate-final-unooria → valida coerência da missão final e dos três vereditos
```

Pode rodar em paralelo com `experiencia-aluno-unooria` — ambas avaliam a mesma missão pós-gate, mas em dimensões independentes (conteúdo pedagógico vs. experiência do aluno).
