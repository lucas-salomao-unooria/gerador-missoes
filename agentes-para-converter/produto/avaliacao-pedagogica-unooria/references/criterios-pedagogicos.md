# Critérios da Avaliação Pedagógica — Rubrica v1.16 — verificação curricular e handoffs reforçados

## 2. IMERSÃO E SIMULAÇÃO (subset — 2.2 a 2.5)

|#|Critério|Tipo|Teste prático|
|-|-|-|-|
|2.2|**Vivência, não leitura** — O aluno experimenta o conceito, não lê sobre ele|Obrigatório|Tirando todo texto explicativo, o conceito ainda chega ao aluno pela experiência?|
|2.3|**Simulação diegética** — O ambiente simulado existe por uma razão dentro da narrativa|Desejável|A narrativa justifica por que aquele ambiente existe, ou ele aparece "do nada"?|
|2.4|**Descoberta central articulada** — Existe uma frase-chave que captura o "aha moment"|Obrigatório|Dá pra resumir em uma frase o que o aluno descobre? Se não dá, a descoberta não está clara.|
|2.5|**Diferenciação no catálogo** — Quando o ambiente ou eixo temático é compartilhado com missão de outro ano, a descoberta central e o tipo de decisão são suficientemente distintos|Desejável|Consultar catálogo de missões: existe outra no mesmo ambiente ou eixo? Se sim, teste de 2 frases: descrever o que o aluno faz em cada missão em uma frase — se intercambiáveis, não diferencia. Se catálogo incompleto, marcar "N/A — catálogo incompleto".|

---

## 4. PAPEL DO PROFESSOR (subset — 4.1 a 4.4)

|#|Critério|Tipo|Teste prático|
|-|-|-|-|
|4.1|**Antes, durante e depois definidos, com gatilhos e ritmos de handoff** — O professor sabe o que fazer e a plataforma define o comportamento da turma em ritmos diferentes.|Obrigatório|**Teste de handoff:** para cada mediação: (a) o que aciona a entrada do professor; (b) o que a plataforma faz enquanto ele media; (c) o que acontece com quem ainda não terminou; (d) o que acontece com quem terminou cedo sem poder avançar; (e) o que muda quando a próxima etapa é liberada. A espera de quem termina cedo deve ter função pedagógica e preservar a descoberta; espera passiva indefinida → ❌.|
|4.2|**Mediação pós-missão desenhada** — A roda de conversa tem roteiro de perguntas|Obrigatório|As perguntas estão escritas, ou o professor precisa inventar?|
|4.3|**Customização do professor** — O professor pode adaptar a missão ao seu contexto/disciplina|Obrigatório|Existe mecanismo pra trazer seu tema, ou a missão é 100% fixa?|
|4.4|**Dashboard / visibilidade** — O professor acompanha o progresso durante a missão|Obrigatório|Tem dados em tempo real pra mediar, ou fica no escuro?|

### Falso-positivo frequente em 4.1:
"Professor debate/media na etapa 4" sem dizer o que aciona a entrada dele nem o que a plataforma faz enquanto ele media — passa como "papel definido" mas não é operacionalizável.

---

## 5. HABILIDADES E CURRÍCULO

|#|Critério|Tipo|Teste prático|
|-|-|-|-|
|5.1|**BNCC Computação mapeada e verificada** — Habilidades explicitamente listadas e separadas entre adequação pedagógica e confirmação do código.|Obrigatório|Para cada EFxxCOxx: (1) a ação observável realmente exercita a habilidade? (2) o código foi conferido em fonte curricular autoritativa/material pedagógico? Se (1) sim e (2) não verificável → 🔵 pendência externa, não ✅. Não validar código por memória ou plausibilidade.|
|5.2|**Habilidades exercitadas ativamente** — O aluno pratica, não só "tem contato"|Obrigatório|Para cada habilidade listada: em que momento específico da missão o aluno a exerce? Sem momento apontável, é conexão fraca.|
|5.3|**Conexão com BNCC de disciplinas** — Conecta genuinamente com componentes curriculares do ano e diferencia adequação do mapeamento de confirmação do código.|Desejável|A ação observável sustenta a habilidade? Se houver código declarado, ele foi verificado em fonte autoritativa? Código plausível mas não conferido → 🔵, sem afirmar confirmação.|
|5.4|**Habilidades socioemocionais presentes** — Pelo menos uma competência geral da BNCC socioemocional|Obrigatório|O aluno exercita empatia, pensamento crítico, responsabilidade, colaboração ou autoconhecimento? **Se já faz isso na prática mas não nomeia**, indique a competência e o momento — nomear torna visível pro professor e pro argumento comercial. **Se nenhuma aparece**, sugira qual poderia ser incorporada e onde, em vez de só marcar ❌.|
|5.5|**Rastreabilidade semanal verificada na fonte curricular** — Cada elemento se conecta ao conteúdo real das semanas do bimestre.|Obrigatório|A tabela “elemento da missão ← semana de origem” foi confrontada com o arquivo Entre Redes/material curricular daquele ano e bimestre? Reconstruir semanas a partir do próprio one-pager NÃO conta como evidência. Sem acesso à fonte → 🔵 pendência externa e bloqueio de “pronta para design/dev”.|
|5.6|**Potencial SAEB identificado sem falsa confirmação de código**|**Obrigatório** em 5º EF, 9º EF, 3ª série EM. **Desejável** nos demais.|Há operação de leitura/matemática exercitada compatível com SAEB? Nos anos em que é obrigatório, código/descritor oficial só recebe ✅ se verificado em fonte autoritativa. Nos demais anos, é suficiente declarar potencial qualitativo sem inventar código. Se houver código não verificado → 🔵.|

---

## 8. GUARDRAILS E ÉTICA

|#|Critério|Tipo|Teste prático|
|-|-|-|-|
|8.1|**Limites da IA definidos** — O que a IA faz e o que NÃO faz|Obrigatório — N/A se não há IA generativa|Existe seção separada de "papel e restrições da IA"? Se lógica determinística sem IA generativa, marcar N/A.|
|8.2|**Sem conteúdo fora do banco curado** — A IA não gera conteúdo sem curadoria|Obrigatório — mesma ressalva do 8.1|Em algum cenário a IA cria texto/imagem/áudio sem curadoria, ou responde com dado não aprovado? **Se responde em tempo real via modelo de linguagem**, o guardrail comportamental explícito no one-pager (ex: "só responde com base no dataset autorizado; se não encontrar, diz que não sabe") já cumpre o critério — não exige lista fechada de datasets (isso é desejável, pertence ao 9.1).|
|8.3|**Privacidade e tratamento de dados definido** — Se coleta dados pessoais (nome, voz, imagem)|Obrigatório|Está claro quais dados, por quê, e como armazenados com segurança? Coleta sem documentar tratamento → ❌.|
|8.4|**Sem rotulação do aluno** — Sistema não categoriza por perfil, tipo ou ideologia|Obrigatório|O sistema atribui um "tipo" ao aluno em algum momento? Se sim → ❌.|
|8.5|**Tom acolhedor sem julgamento do aluno** — Pode mostrar resultado pior *dentro da simulação*, nunca julgar a pessoa|Obrigatório|Existe mensagem/cor/ícone/fala que julgue o ALUNO (não o resultado da escolha) como errado ou inferior? **Em missões individuais** com mediação que compara resultados nominalmente, há risco de exposição social mesmo cumprindo a letra do critério — prefira comparação em nível de grupo/anonimizada, ou documente como o professor conduz essa exposição com cuidado.|
|8.6|**Affordance nativa × guardrail ético** — O comportamento real da plataforma, quando o aluno usa um verbo nativo, não viola um guardrail ético da missão.|Obrigatório|Um verbo pode ser 100% nativo (passa no 2.6 do gate estrutural) e ainda assim o comportamento real da plataforma pode violar um guardrail. **Teste:** para cada ação nativa usada pelo aluno, o que a plataforma real faz com essa ação produz consequência que a missão tenta evitar? Exemplos: enquete nativa que expõe votantes nominalmente quando a missão pede anonimato; "apagar mensagem" que deixa rastro de "mensagem apagada" quando a missão precisa de comparação limpa; "compartilhar" que notifica o dono do conteúdo quando a missão simula observação anônima. Se a affordance nativa contradiz o guardrail ético → ❌. Se contradiz mas há mitigação documentada no one-pager → ⚠️.|

### Falso-negativo frequente em 8.6:
O critério 2.6 do gate estrutural valida se o verbo **existe** na plataforma. O 8.6 valida se a **consequência** do verbo é compatível com o guardrail. São testes ortogonais — um passa e o outro pode reprovar no mesmo verbo.

---

## RESUMO DE CONTAGEM — Avaliação Pedagógica

| Categoria | Obrigatórios | Desejáveis |
|-|:-:|:-:|
| 2. Imersão (subset) | 1 | 2 |
| 4. Professor (subset) | 4 | 0 |
| 5. Habilidades | 4 + 1 condicional | 1 |
| 8. Guardrails | 6 | 0 |
| **TOTAL** | **15 + 1 condicional** | **3** |


### Regra comum de verificação curricular

- Separar sempre **“a habilidade faz sentido aqui”** de **“o código oficial está confirmado”**.
- Fonte ausente ou não conferida em critério obrigatório → 🔵, nunca ✅ por plausibilidade.
- O veredito “pedagogicamente pronta” exige todos os obrigatórios em ✅ ou, quando o critério for explicitamente condicional e não se aplicar, N/A justificado por regra da rubrica — não por falta de informação.
