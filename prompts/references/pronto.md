---
name: pronto
description: Definição de pronto por agente — só o que se conta. Verificada pelo próprio agente antes de entregar, e declarada no envelope. Lido por jornada-figjam, fluxo-figjam, copy-ptbr, caa, wireframes-figma e pelo gate de ofício.
sources: [chat]
---

# Definição de pronto

Higiene técnica, não ofício. Todo item fecha em **zero**. Item acima de zero **retém a entrega** — o agente corrige antes de acionar o próximo, não depois de tomar ticket.

Isto não é uma dimensão de auditoria. É a lista que impede o gate de ofício de gastar rodada com achado que uma contagem pega.

**Declare a contagem no envelope** (`pronto` em `references/contrato-saida.md`). Contagem ausente equivale a contagem falhada: sem ela ninguém sabe se o zero foi verificado ou presumido.

## jornada-figjam

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

## fluxo-figjam

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

## wireframes-figma

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

## Regra de manutenção

Item novo entra aqui só se **se conta**. Se a verificação admite "acho que sim", ela pertence a `rubrica-oficio.md`, não a este arquivo — e confundir os dois é o que faz higiene virar debate de gosto.

Item que nunca sai de zero em cinco missões seguidas sai da lista. Checagem que nunca pega nada é cerimônia, e cerimônia treina o agente a declarar sem verificar.
