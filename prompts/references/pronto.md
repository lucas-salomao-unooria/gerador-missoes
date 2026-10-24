---
name: pronto
description: Definição de pronto por agente — só o que se conta. Verificada pelo próprio agente antes de entregar, e declarada no envelope. Lido por completude-spec, fecha-lacunas, ambiente-simulado, jornada, fluxo, copy-ptbr, caa, telas e pelo gate de ofício.
sources: [chat]
---

# Definição de pronto

Higiene técnica, não ofício. Todo item fecha em **zero**. Item acima de zero **retém a entrega** — o agente corrige antes de acionar o próximo, não depois de tomar ticket.

Isto não é uma dimensão de auditoria. É a lista que impede o gate de ofício de gastar rodada com achado que uma contagem pega.

**Declare a contagem no envelope** (`pronto` em `references/contrato-saida.md`). Contagem ausente equivale a contagem falhada: sem ela ninguém sabe se o zero foi verificado ou presumido.

## jornada

| Conta | Zero significa |
|---|---|
| Célula de raia vazia sem `⚠️ lacuna` | Vazio é omissão; lacuna é achado. Não confunda |
| Tela no inventário sem etapa ou sem ator | Tela órfã |
| Tela sem `Peso` atribuído | O staff receberia densidade uniforme |
| Tela `pico` além de uma | Tier precisa de topo único |
| Tela `pico` ou `alta` sem linha na Seção 4 | Direção prometida e não escrita |
| Beat marcado no mapa de beats sem tela que o carregue | Beat perdido antes do build |
| Verbo na jornada fora da lista de verbos do bloco 4 da spec | Verbo inventado |
| Cenário de dispositivo com "descoberta chega?" em branco | 10.2 sem resposta |

## fluxo

| Conta | Zero significa |
|---|---|
| Tela do inventário ausente do grafo | Cobertura incompleta |
| Nó sem saída, ou sem entrada | Teste 1 e 2 do fluxo |
| Aresta sem condição escrita na lista | Rótulo no desenho não é condição |
| Rótulo de aresta acima de 3 palavras | Legibilidade |
| Gate com menos de duas saídas | Teste 4 |
| Caminho degenerado da spec sem rota no grafo | Teste 3 |
| Ciclo sem marcação de intencional | Teste 5 |

## copy-ptbr

| Conta | Zero significa |
|---|---|
| String acima do teto de palavras da faixa | Teto em `rubrica-atual.md` |
| Instrução acionável em anos iniciais sem `texto+ícone+áudio` | Acessibilidade, não preciosismo |
| String encolhida para caber sem entrar na lista de "não couberam" | Encolher em silêncio produz telegrama |
| Tela do inventário sem string | O agente 5 vai inventar texto |
| String no sheet sem tela | Sobra de passada anterior |
| Chave fora da convenção `eN.tipo.nome` | O dev usa a chave |
| Tela com dois registros de voz | Guia, plataforma e Unooria não se misturam na mesma tela |
| Registro sem régua com exemplo e contraexemplo no glossário | Proibição não produz voz |

## caa

Só conta quando o gate de aplicabilidade deu "roda". Em `nao_aplicavel`, a contagem é a própria condição verificada.

| Conta | Zero significa |
|---|---|
| Decisão da raia "Estudante — faz" sem modo de resposta alternativo | A faixa não consegue responder |
| Conceito com mais de um símbolo na missão | Um conceito, um símbolo |
| Símbolo sem o texto junto | Símbolo sozinho é substituição, não redundância |
| Símbolo acionável sem chave de string indicada para o áudio | Rota não-leitora incompleta |
| Prancha CAA dentro do clone | DES-13: quebra a ficção do ambiente simulado |
| Símbolo abaixo de 64×64 px no aparelho, 88×88 na projeção, ou vão menor que 16 px | Restrição de build, não sugestão |
| Símbolos numa tela acima do teto de elementos da Seção 4 | O teto é da jornada |
| Tela coberta sem linha no mapa CAA | Cobertura incompleta |
| Célula do mapa sem resposta na spec e sem `⚠️ lacuna` | Vazio é invenção; lacuna é achado |
| Momento de mediação sem linha de instrução para a professora | Prancha sem quem a conduza |
| Marcador que distingue "respondeu por CAA" na evidência | Rotular estudante (8.4) |

## telas

| Conta | Zero significa |
|---|---|
| Valor hardcoded onde existe token | Hex, spacing, radius, tipografia |
| Variável de cinza fora da nomenclatura do Unooria DS | Quebra a troca de coleção e transforma o wireframe em descarte |
| Cor no lo-fi | Uma exceção abre todas |
| Frame sem anotação de verbo, do que muda depois, e do critério | É o que o Gate Final confere |
| Frame fora da convenção `ID — descrição` | |
| Frame que não está no inventário | Escopo cresceu no build |
| Tela do inventário sem frame | Cobertura incompleta |
| Estado obrigatório do inventário não construído | Espera, vazio, pós-ação, degradado, primeira vez |
| Componente local criado sem busca no DS registrada | Log da busca, não afirmação de que buscou |
| Componente local sem registro como candidato | `aprendizado` decide se sobe |
| Chrome desenhado do zero que a biblioteca do ambiente fornece | Ou não importou, ou a biblioteca tem lacuna a registrar |
| Pictograma de gesto ou botão de áudio como caixa cinza | Requisito de acessibilidade |
| `[[placeholder]]` não resolvido na entrega final | |
| Elemento contado acima do teto da tela na Seção 4 | Conta como em `rubrica-oficio.md` |

## completude-spec

O passo de completude da spec, em produto (prompt 046, desde 24/10/2026).

| Conta | Zero significa |
|---|---|
| Célula de produto do checklist (`celulas-consumidas.md`) sem ✅, `[CP-n]` ou marcador para o PO | Varredura completa — nenhuma ⚠️ solta |
| Decisão `[CP-n]` que reescreve texto já presente na spec | Preenche ausência, nunca altera presença |
| `[PARÂMETRO]` ou `[PROPOSTA]` da spec fechado sem parecer datado do PO | Quem decide é o PO, no de acordo |
| Decisão com base "inferência" sem frase ancorada na descoberta ou na faixa | Inferência sem âncora é invenção — vira marcador para o PO |
| Decisão que aumenta decisões do estudante, telas ou dados coletados | O cap é do produto, e só o PO o muda |
| Lacuna de classe `mecanica` ou `curriculo` decidida | As duas classes são sempre do PO |
| Prazo de retenção ou protocolo de revezamento escrito pela missão | É padrão da plataforma: cite-o |
| `[CP-n]` do bloco 15 sem entrada no relatório de completude, ou vice-versa | Os dois documentos dizem a mesma coisa |
| Linha fora do bloco 15 | A spec do A045 é montada em código |
| Termo em inglês no relatório de completude | Quem lê é o PO |

## fecha-lacunas

O D0-UX, no design (desde 24/10/2026 só UI/UX; o que é de produto fecha em produto, no passo de completude da spec).

| Conta | Zero significa |
|---|---|
| Célula de UI/UX do checklist (`celulas-consumidas.md`) sem ✅, `[D0-n]` ou `[ABERTO — dono: PO]` | Varredura completa — nenhuma ⚠️ solta |
| Decisão `[D0-n]` que reescreve texto já presente na spec | Preenche ausência, nunca altera presença |
| Decisão `[D0-n]` de classe fora de estado (de tela), gesto, scaffolding, acessibilidade, dispositivo | O resto é de produto — vira `[ABERTO — dono: PO]` |
| Decisão com base "inferência" sem frase ancorada na descoberta ou na faixa | Inferência sem âncora é invenção — vira vermelho |
| Decisão que aumenta decisões do estudante, telas ou dados coletados | O cap é do produto |
| `[RS-n]` sem "Bloqueia" preenchido | Sem bloqueio não é re-spec, é anotação |
| Linha da spec de produto (blocos 0–12, glossário, bloco 15) reescrita | A spec de produto é intocada no design |
| `[D0-n]` do bloco 13 sem entrada no relatório de preenchimento, ou vice-versa | Os dois documentos dizem a mesma coisa |
| Termo em inglês no relatório de preenchimento | Quem lê é a PM e a professora |
| Decisão em voz de opinião ("sugiro", "acho") | A spec é contrato |

## ambiente-simulado

Sem poder de produto desde 24/10/2026 (PR 8, decisão D8): a classe e o ambiente vêm do bloco 0 da spec, e as regras e as fases do mini-jogo, do bloco 2. As linhas marcadas **(código)** são conferidas pelo split do D9, que bloqueia.

| Conta | Zero significa |
|---|---|
| Verbo do bloco 4 sem rótulo literal e componente do DS na ficha | Ficha incompleta — D2 e D4 vão inventar |
| Texto escrito na spec de produto (blocos 0–12, glossário, bloco 15) **(código)** | O texto de produto é do PO |
| Texto escrito no bloco 13 do anexo (descartado com atenção 🟡 pelo código, sem bloquear) | O bloco 13 é do D0 |
| Ambiente ou classe no bloco 14 diferente do bloco 0 da spec **(código)** | Decidir o ambiente é de produto: o que não cabe volta como devolução |
| Regra ou fase de jogo no bloco 14, ou numa seção `## ` nova fora dele — quantas fases, a regra de cada uma, como vence, como perde, como o progresso aparece **(código)** | É conteúdo de produto, no bloco 2 |
| Spec calada sobre o ambiente, ou ambiente que não comporta os verbos, sem devolução no Passo 3 e no envelope | O D9 não cria: devolve a produto |
| Decisões, telas ou dados coletados diferentes de antes do bloco 14 | O cap é do produto |
| Token, cor ou fonte fora do DS na seção do ambiente | A marca é forma e chrome, não paleta |
| Componente local novo sem busca no DS registrada e sem marca de candidato | `aprendizado` decide se sobe |
| Nome do ambiente ou texto lido por pessoa em inglês | Identificadores de contrato ficam; o resto traduz |
| Mini-jogo: placar entre estudantes, tempo como nota, vida que expulsa, poder permanente na casca de UI | 🔴 por 8.5 e PED-07 |
| Mini-jogo: nome, personagem, som, ícone ou forma de jogo comercial | A referência é a gramática, nunca a marca |

## Regra de manutenção

Item novo entra aqui só se **se conta**. Se a verificação admite "acho que sim", ela pertence a `rubrica-oficio.md`, não a este arquivo — e confundir os dois é o que faz higiene virar debate de gosto.

Item que nunca sai de zero em cinco missões seguidas sai da lista. Checagem que nunca pega nada é cerimônia, e cerimônia treina o agente a declarar sem verificar.
