# Catálogo de Missões Unooria

> **A fonte viva deste catálogo não é este arquivo.** Desde 22/09/2026 as missões geradas são
> registradas automaticamente num índice (`output/_catalogo.json`), que a esteira lê a cada execução
> e entrega aos prompts pela variável `{catalogo_missoes?}`. Este arquivo define **as colunas, o
> vocabulário e como comparar** — a regra, versionada aqui; o dado vive no índice, que persiste
> entre execuções e entre revisões do serviço. A tabela ao fim é o **registro legado, congelado**:
> ela alimentou a carga inicial do índice e não é mais mantida à mão.

**Objetivo:** Registro vivo das missões criadas/aprovadas. A rubrica consulta este arquivo no critério 2.5 (diferenciação no catálogo) e no 2.8 (progressão na trilha) para detectar sobreposição de ambiente, eixo temático ou descoberta central entre missões, e para verificar se uma missão sobe um degrau em relação à anterior do mesmo ano ou eixo.

**Como se mantém agora:** o agente 52 registra a missão ao fim de cada execução, com status derivado dos gates (`em criação` ou `bloqueada`) — registrar é fato. Promover para `validada`, `aprovada` ou `em produção` é ato humano: `python scripts/catalogo.py promover --sessao <pasta> --status aprovada`. O agente 51 continua redigindo os campos de julgamento (descoberta, eixo, tipo de decisão), que o 52 copia. Campo desconhecido entra como `[preencher do manifesto]`, nunca em branco — e linha com campo por preencher **não sustenta reprovação** na verificação V5 do micro-gate.

**Campos:**
- **Slug** — o id da plataforma, `expNNefNb` (ano em dois dígitos + `ef`/`em` + bimestre + `b`); `exp-NN-<nome>` só para missão transversal sem série
- **Ano/série** — ex: 4º EF, 8º EF, 2º EM
- **Bimestre** — 1º, 2º, 3º ou 4º
- **Nome da missão** — título de trabalho
- **Ambiente simulado** — a seção de `ambientes.md`: `unooriaai`, `unoovista`, `unoochat`, `tiktooria`, `unoogaleria`, `unoojornal`, `unooblog` (ou `mini-jogo`, só 1º–5º); missões antigas aparecem com a legada (`instanooria`, `unootube`, `chatgpt`, `whatsappmobile`)
- **Eixo temático** — categoria do tema (narrativas/poder, algoritmos/viés, privacidade/dados, desinformação, etc.)
- **Descoberta central (aha)** — frase-chave que captura o que o estudante descobre
- **Tipo de decisão** — o que o estudante faz ativamente (comparar coberturas, montar dataset, curar fontes, selecionar candidatos, etc.)
- **Porta de abstração** — o que a decisão pede do estudante, na escala de `literatura-cognitiva.md` §4: `descrever` · `explicar` · `criticar com apoio` · `criticar`
- **Habilidade primária** — o código BNCC de letramento digital do foco primário (Regra 12 do P0a)
- **Status** — em criação / validada / aprovada / em produção / descartada

\---

## Registro legado (congelado em 22/09/2026)

As linhas abaixo vieram do catálogo escrito à mão e já foram importadas para o índice
(`scripts/catalogo.py importar-markdown`). Não acrescente linhas aqui: a esteira registra sozinha.

|Slug|Ano|Bim|Nome|Ambiente|Eixo temático|Descoberta central (aha)|Tipo de decisão|Porta de abstração|Habilidade primária|Status|
|-|-|-|-|-|-|-|-|-|-|-|-|
|exp04ef1b|4º EF|1º|Mais curtido ou mais confiável?|`unootube`|Desinformação / credibilidade|Popularidade não é o mesmo que confiabilidade — um vídeo ter mais views não significa que a informação é melhor.|Escolher 3 de 10 vídeos pra playlist do canal, avaliando credibilidade vs. popularidade|descrever|[preencher do manifesto]|validada|não|
|[preencher do manifesto]|8º EF|—|O conteúdo que não chegou|`instanooria`|Algoritmos / curadoria de feed|O que você não vê no feed foi decidido por alguém — o algoritmo mostra o que gera engajamento, não o que é importante.|Navegar feed curado e descobrir o que ficou de fora|explicar|[preencher do manifesto]|aprovada|não|
|[preencher do manifesto]|4º EF|—|O Vulcão dos Dois Lados|`whatsappmobile` + editor de vídeo (escape a revisar: editor não é seção do DS)|Narrativas / perspectiva|A mesma história contada de dois lados diferentes não é mentira de nenhum dos dois — é ponto de vista.|Receber duas versões do mesmo evento por WhatsApp e produzir um vídeo com sua versão|descrever|[preencher do manifesto]|aprovada|não|
|exp01ef1b|1º EF|1º|O Que a Foto Conta (exp-04 na plataforma)|[preencher do manifesto]|[preencher do manifesto]|[preencher do manifesto]|[preencher do manifesto]|descrever|[preencher do manifesto]|em produção|não|
|exp06ef2b|6º EF|2º (unidade 2)|Rastro do Boato (exp-06)|`whatsappmobile`|[preencher do manifesto]|[preencher do manifesto]|[preencher do manifesto]|[preencher do manifesto]|[preencher do manifesto]|em produção|não|
|[preencher do manifesto]|[preencher do manifesto]|—|O Eco no Grupo (exp-07)|`whatsappmobile`|[preencher do manifesto]|[preencher do manifesto]|[preencher do manifesto]|[preencher do manifesto]|[preencher do manifesto]|em produção|não|
|[preencher do manifesto]|[preencher do manifesto]|—|Manifesto IA (exp-08)|[preencher do manifesto]|[preencher do manifesto]|[preencher do manifesto]|[preencher do manifesto]|[preencher do manifesto]|[preencher do manifesto]|em produção|não|
|exp01ef1b|1º EF|—|Magia ou Truque|`tiktooria`|[preencher do one-pager]|[preencher do one-pager]|[preencher do one-pager]|descrever|[preencher do one-pager]|validada|não|
|exp05ef1b|5º EF|—|A foto é real|[preencher do one-pager]|Desinformação / credibilidade|[preencher do one-pager]|Classificar e encaminhar (ou não) fotos recebidas|descrever|[preencher do one-pager]|validada|não|
|exp07ef1b|7º EF|—|Quem ficou fora|`whatsappmobile`|Narrativas / perspectiva|[preencher do one-pager]|Comparar três versões e fixar mensagens|explicar|[preencher do one-pager]|validada|não|

\---

## Como usar na avaliação (critérios 2.5 e 2.8)

Ao avaliar uma missão nova:

1. Identificar o **ambiente simulado** e o **eixo temático** da missão sendo avaliada.
2. Filtrar a tabela acima por essas colunas — existe outra missão com o mesmo ambiente OU mesmo eixo?
3. **2.5 (diferenciação):** se sim, aplicar o **teste de 2 frases**: descrever o que o estudante faz em cada missão em uma frase. Se as frases são intercambiáveis ou uma contém a outra, a diferenciação é insuficiente.
4. **2.8 (progressão):** se existe missão anterior do mesmo ano, ou do ano anterior no mesmo eixo, comparar as colunas **Porta de abstração**, **Tipo de decisão** (repertório) e **Ambiente**: a missão nova sobe pelo menos um degrau em uma das três? Mesmo degrau nas três → ⚠️; degrau abaixo → ❌.
5. Se o catálogo não tem a missão comparada (ou está vazio), marcar "N/A — catálogo incompleto" e registrar como lacuna com dono produto.

## Quando atualizar

- Missão passou pela rubrica com todos os obrigatórios ✅ → adicionar ao catálogo.
- Missão mudou de conceito (trocou ambiente, aha, ou tipo de decisão) → atualizar a linha existente.
- Missão foi descartada → marcar status como "descartada".
