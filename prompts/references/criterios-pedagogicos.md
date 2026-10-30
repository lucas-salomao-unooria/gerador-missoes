# Critérios da Avaliação Pedagógica — Rubrica v1.21 — verificação curricular e handoffs reforçados

## 2. IMERSÃO E SIMULAÇÃO (subset — 2.2 a 2.5 e 2.8)

|#|Critério|Tipo|Teste prático|
|-|-|-|-|
|2.2|**Vivência, não leitura** — O aluno experimenta o conceito, não lê sobre ele|Obrigatório|Tirando todo texto explicativo, o conceito ainda chega ao aluno pela experiência?|
|2.3|**Simulação diegética** — O estudante entra no ambiente por uma razão que é dele, por uma ação que é do ambiente, e o ambiente não é trocável|Obrigatório|Três testes, todos precisam passar. **(a) Teste da porta:** o *job-to-be-done* do Desafiar (Regra 9 do P0a) diz por que o estudante abre **este** app **agora**, e é algo que um estudante da faixa faria fora da missão (`literatura-cognitiva.md` §10)? "A Unooria te leva ao feed" não é porta; "o Léo mandou o link no grupo" é. **(b) Teste da troca:** substitua mentalmente o ambiente (cada seção, quando a missão usa mais de uma) por outro da lista; se o Desafiar e o Decidir continuam válidos sem reescrita, o ambiente é cenário, não diegese. **(c) Teste da chegada:** a primeira entrada no ambiente — e cada troca entre seções do DS, quando a missão usa mais de uma — é uma ação nativa (abrir o app, abrir um grupo, tocar um link, receber uma notificação), não uma transição da plataforma? Falha em (a) ou (c) → ❌; falha só em (b) com justificativa na seção 18 → ⚠️.|
|2.4|**Descoberta central articulada e com anatomia** — Existe uma frase-chave que captura o "aha moment", e a seção 1.2 do one-pager desenha os seis passos que levam a ela|Obrigatório|Dá pra resumir em uma frase o que o aluno descobre? E a tabela 1.2 (anatomia do aha) nomeia a crença de entrada que a virada desmente, a aposta que o estudante trava antes e a consequência que muda conforme a escolha dele? Frase sem anatomia → ⚠️; virada que não desmente a crença da 1.2 → ❌. A profundidade em si é pontuada pelo juiz de profundidade no loop do núcleo (`criterios-profundidade.md`); aqui se confere que as correções das avaliações não a desmontaram.|
|2.5|**Diferenciação no catálogo** — Quando o ambiente ou eixo temático é compartilhado com missão de outro ano, a descoberta central e o tipo de decisão são suficientemente distintos|Desejável|Consultar catálogo de missões: existe outra no mesmo ambiente ou eixo? Se sim, teste de 2 frases: descrever o que o aluno faz em cada missão em uma frase — se intercambiáveis, não diferencia. Se catálogo incompleto, marcar "N/A — catálogo incompleto".|
|2.8|**Progressão na trilha** — Quando o catálogo tem missão anterior do mesmo ano, ou do ano anterior no mesmo eixo, esta missão sobe pelo menos um degrau em uma de três escadas|Desejável enquanto o catálogo não cobrir o ano da missão; **Obrigatório** depois|**Escadas:** (1) porta de abstração — descrever → explicar → criticar com apoio → criticar (`literatura-cognitiva.md` §4); (2) piso de repertório (6.6); (3) ambiente, de mais familiar para menos familiar (§10). **Teste:** cite a linha do catálogo comparada e a escada em que a missão nova sobe. Mesmo degrau nas três → ⚠️; degrau **abaixo** da missão anterior → ❌. Fundamento: intervenções de letramento midiático em múltiplas sessões superam as de sessão única (Huang, Jia & Yu, 2024) — a unidade de dose é a trilha, não a missão.|

---

## 4. PAPEL DO PROFESSOR (subset — 4.1 a 4.4)

|#|Critério|Tipo|Teste prático|
|-|-|-|-|
|4.1|**Antes, durante e depois definidos, com gatilhos e ritmos de handoff** — O professor sabe o que fazer e a plataforma define o comportamento da turma em ritmos diferentes.|Obrigatório|**Teste de handoff:** para cada mediação: (a) o que aciona a entrada do professor; (b) o que a plataforma faz enquanto ele media; (c) o que acontece com quem ainda não terminou; (d) o que acontece com quem terminou cedo sem poder avançar; (e) o que muda quando a próxima etapa é liberada. A espera de quem termina cedo deve ter função pedagógica e preservar a descoberta; espera passiva indefinida → ❌.|
|4.2|**Mediação pós-missão desenhada** — A roda de conversa tem roteiro de perguntas|Obrigatório|As perguntas estão escritas, ou o professor precisa inventar?|
|4.3|**Customização e geração assistida por IA na preparação docente** — O professor tem autonomia para parametrizar tema, contexto e conteúdos da missão. A spec define a interface e o fluxo de preparação com IA (inputs do professor → geração de rascunhos por IA via Vertex AI Gemini → revisão e aprovação pelo professor), além de banco curado padrão (default/fallback imediato).|Obrigatório|Existe mecanismo para o professor parametrizar tema/conteúdo na preparação da missão? Os prompts e schemas de geração por IA estão definidos? Há fluxo de curadoria docente antes de liberar para a turma? Existe banco curado default caso o professor não queira customizar? Missão 100% estática sem parametrização → ❌. **Teste das três disciplinas (transversalidade):** o recorte da aula aceita disciplina, tema **e assuntos**; a tabela "a mesma missão em três aulas" (Português, Ciências/Biologia, História) existe e cada linha mantém mecânica, cardinalidades e descoberta central? Slot que só aceita um tipo de conteúdo sem marcador → ⚠️ com ajuste exigido; slot que quebra a mecânica em alguma disciplina → ❌; `[LIMITE DE TRANSVERSALIDADE — dono: produto]` declarado é decisão registrada, não achado. **Teste do caminho curto:** a missão roda por completo com o professor tocando apenas "usar banco padrão" em `E0-PROF-02`, sem passar por geração nem curadoria (`E0-PROF-03` e `04` puladas)? Se não → ❌: o banco curado é *fallback* de nome, não de fato. **Teste de posição, anos iniciais:** em missão de 1º–5º ano, o botão do banco padrão é a primeira ação visível de `E0-PROF-02` e o recorte da aula vem depois (43% de formação continuada na rede municipal — TIC Educação 2024); nos anos finais e Médio a ordem é livre. Ordem invertida nos anos iniciais → ⚠️. **Contagem de preparo:** a seção 9a declara quantas telas e quantos toques o caminho curto e o caminho com IA exigem; sem a contagem → ⚠️.|
|4.4|**Dashboard / visibilidade** — O professor acompanha o progresso durante a missão|Obrigatório|Tem dados em tempo real pra mediar, ou fica no escuro?|

### Falso-positivo frequente em 4.1:
"Professor debate/media na etapa 4" sem dizer o que aciona a entrada dele nem o que a plataforma faz enquanto ele media — passa como "papel definido" mas não é operacionalizável.

---

## 5. HABILIDADES E CURRÍCULO

> [!IMPORTANT]
> **Regra fundamental de bloqueio da BNCC:**
> As **ÚNICAS regras da BNCC que bloqueiam de fato a missão são as de LETRAMENTO DIGITAL** (habilidades de Cultura Digital / Letramento Digital da BNCC Computação — uso crítico, ético, seguro e consciente de tecnologias e ambientes digitais). Sem vivência ativa e correta de letramento digital, a missão recebe ❌ bloqueante.
> As **demais regras da BNCC** (habilidades de disciplinas tradicionais, competências gerais socioemocionais, códigos disciplinares complementares) **não são conferidas pela esteira e não geram item no relatório**. Não existe motor de BNCC no servidor da plataforma e código de disciplina tradicional não muda uma linha da implementação: conferi-lo aqui produzia alerta que ninguém fechava — 43 dos 283 achados das 14 primeiras execuções vinham daí. O que **continua valendo** é a proibição de inventar: código declarado sem ação observável que o sustente é **ajuste exigido de remoção**, porque código errado no material do professor é pior do que código ausente. A leitura curricular dessas áreas vive no one-pager pedagógico, que é onde a professora lê.

|#|Critério|Tipo|Teste prático|
|-|-|-|-|
|5.1|**BNCC Computação — Letramento Digital mapeado e verificado** — Habilidades de letramento digital/cultura digital explicitamente listadas e exercitadas.|**Obrigatório [BLOQUEANTE]**|Para cada habilidade de letramento digital (EFxxCOxx de Cultura Digital / uso crítico e seguro da rede): (1) a ação observável realmente exercita a habilidade de letramento digital? (2) o código/descritor está coerente com a prática — **o texto oficial descreve a ação, sem reinterpretação** ("conduta e linguagem ao se comunicar" não descreve escolher uma conta e ver o feed afunilar)? **Este é o único critério da BNCC que bloqueia de fato a missão.** Se a missão falhar no letramento digital, ou se nenhuma habilidade de Cultura Digital do ano descreve a ação (one-pager com `[DECISÃO PENDENTE — responsável de produto: …]`) → ❌ bloqueio com 🔵 para o time decidir ano ou âncora.|
|5.2|**Habilidades exercitadas ativamente** — O aluno pratica letramento digital na experiência, não só "tem contato"|**Obrigatório [BLOQUEANTE para letramento digital]**|Para cada habilidade de letramento digital: em que momento específico da missão o aluno a exerce? Sem momento prático de letramento digital → ❌ bloqueio. Para código secundário de Computação (Pensamento Computacional, Mundo Digital) sem momento em tela que exercite o **texto oficial** → ajuste exigido de remoção do código (não bloqueia, mas não fica). Para habilidades de outras áreas sem momento claro → ⚠️ ressalva / item de alerta (não bloqueia). **Toda habilidade tem Canal A** (seção 12a, desde 15/10/2026): a evidência é a ação em tela, e o Canal B (pergunta de múltipla escolha) foi removido por decisão do PO de 29/10/2026 — qualquer `B` volta ao autor.|
|5.3|**Conexão com BNCC de disciplinas** — Conecta com componentes curriculares do ano (Português, História, Ciências, etc.).|Desejável (**não se registra**)|A ação observável sustenta a habilidade da disciplina? **Código não conferido não vira item de relatório** — a esteira não confere currículo de disciplina tradicional. Conexão **sem** ação observável, ou cuja habilidade descreve outra coisa, continua sendo ajuste exigido de remoção — ausência é melhor do que conexão forçada.|
|5.4|**Habilidades socioemocionais presentes** — Pelo menos uma competência geral da BNCC socioemocional|Recomendado (**não se registra**)|O aluno exercita empatia, pensamento crítico, responsabilidade, colaboração ou autoconhecimento? Se já faz na prática mas não nomeia, indique a competência e o momento **no texto da seção**. Ausência **não vira item de relatório**.|
|5.6|**Potencial SAEB identificado sem falsa confirmação de código**|Condicional (Alerta se pendente)|Há operação compatível com SAEB? **Anos aplicáveis: 2º, 5º e 9º do Fundamental e 3ª série do Médio** — fora deles a resposta é "N/A — ano não avaliado pelo SAEB", e descritor emprestado de outro ano é ajuste exigido de remoção. Nos anos aplicáveis, declarar potencial qualitativo. **Código não verificado não vira item de relatório** — só o descritor de ano errado, que é conferível e sai.|

---

## 8. GUARDRAILS E ÉTICA

|#|Critério|Tipo|Teste prático|
|-|-|-|-|
|8.1|**Limites da IA definidos** — O que a IA faz e o que NÃO faz|Obrigatório — N/A se não há IA generativa|Existe seção separada de "papel e restrições da IA"? Se lógica determinística sem IA generativa, marcar N/A.|
|8.2|**Curadoria docente ativa (Human-in-the-Loop) e guardrails de IA** — A IA gera conteúdos na preparação da aula para validação do professor; os estudantes nunca recebem conteúdo aberto de IA em tempo real sem curadoria prévia.|Obrigatório — mesma ressalva do 8.1|Em algum cenário o estudante é exposto a conteúdo gerado por IA em tempo real sem curadoria prévia do professor ou da plataforma? **Arquitetura Human-in-the-Loop:** a IA atua como assistente na preparação docente; o professor revisa, edita e aprova o pacote de postagens/mídias antes de publicar para a turma. O que chega ao estudante é sempre um banco 100% curado (pelo professor ou padrão de fábrica). Se há IA conversacional síncrona com o estudante (ex: chatbot de personagem), o guardrail comportamental explícito no one-pager (ex: "só responde sobre X com base no dataset autorizado") é obrigatório.|
|8.3|**Privacidade e tratamento de dados definido** — Se coleta dados pessoais (nome, voz, imagem)|Obrigatório|Está claro quais dados, por quê, e como armazenados com segurança? Coleta sem documentar tratamento → ❌.|
|8.4|**Sem rotulação do aluno** — Sistema não categoriza por perfil, tipo ou ideologia|Obrigatório|O sistema atribui um "tipo" ao aluno em algum momento? Se sim → ❌.|
|8.5|**Tom acolhedor sem julgamento do aluno** — Pode mostrar resultado pior *dentro da simulação*, nunca julgar a pessoa|Obrigatório|Existe mensagem/cor/ícone/fala que julgue o ALUNO (não o resultado da escolha) como errado ou inferior? **Em missões individuais** com mediação que compara resultados nominalmente, há risco de exposição social mesmo cumprindo a letra do critério — prefira comparação em nível de grupo/anonimizada, ou documente como o professor conduz essa exposição com cuidado.|
|8.6|**Affordance nativa × guardrail ético** — O comportamento real da plataforma, quando o aluno usa um verbo nativo, não viola um guardrail ético da missão.|Obrigatório|Um verbo pode ser 100% nativo (passa no 2.6 do gate estrutural) e ainda assim o comportamento real da plataforma pode violar um guardrail. **Teste:** para cada ação nativa usada pelo aluno, o que a plataforma real faz com essa ação produz consequência que a missão tenta evitar? Exemplos: enquete nativa que expõe votantes nominalmente quando a missão pede anonimato; "apagar mensagem" que deixa rastro de "mensagem apagada" quando a missão precisa de comparação limpa; "compartilhar" que notifica o dono do conteúdo quando a missão simula observação anônima. Se a affordance nativa contradiz o guardrail ético → ❌. Se contradiz mas há mitigação documentada no one-pager → ⚠️.|

### Falso-negativo frequente em 8.6:
O critério 2.6 do gate estrutural valida se o verbo **existe** na plataforma. O 8.6 valida se a **consequência** do verbo é compatível com o guardrail. São testes ortogonais — um passa e o outro pode reprovar no mesmo verbo.

---

## RESUMO DE CONTAGEM — Avaliação Pedagógica

| Categoria | Obrigatórios (Bloqueantes) | Ressalvas / Alertas / Desejáveis |
|-|:-:|:-:|
| 2. Imersão (subset) | 3 | 2 |
| 4. Professor (subset) | 4 | 0 |
| 5. Habilidades (Letramento Digital vs. Outras) | 2 (Letramento Digital) | 3 + 1 condicional (Outras BNCC / Alertas) |
| 8. Guardrails | 6 | 0 |
| **TOTAL** | **15** | **5 + 1 condicional** |


### Regra comum de verificação curricular e veredito

- **As únicas regras da BNCC que bloqueiam de fato são as de letramento digital** (5.1 e 5.2 no que tange ao letramento digital). Se a missão não exercitar letramento digital ou deturpar o conceito, ela é 🔴 BLOQUEADA.
- **As demais regras da BNCC não bloqueiam e não se registram**: disciplinas tradicionais (5.3), socioemocionais (5.4) e SAEB (5.6) não produzem item no relatório. Rastreabilidade semanal saiu da rubrica: em que semana do ano a aula acontece é combinado com a rede na implantação, não é insumo de construção.
- Separar sempre **“a habilidade faz sentido aqui”** de **“o código oficial está confirmado”** — e, quando o segundo não for conferível aqui, **não declarar o código**.
- Fonte ausente em código de disciplina tradicional → **não declare o código**; não há alerta a emitir.
- O veredito “pedagogicamente pronta” exige os itens bloqueantes em ✅. Se houver pendências em outras áreas da BNCC, emite-se “pronta com ressalvas” (com status `"aprovado"` no envelope).
