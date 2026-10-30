# Protótipo em alta fidelidade — contrato do agente de código

Você constrói o **front da missão quase como o código de produção**, com três diferenças: os dados são mockados, o servidor não existe e as imagens são geradas. Use os **componentes reais do Design System** (`@unooria/design-system`), as **interações da mecânica** e imagens fiéis à história. Quem joga o protótipo tem de viver a missão: clicar, digitar, arrastar, esperar o carregamento, ver a resposta e seguir para a próxima tela.

Quem decidiu cada tela, cada estado, cada texto e cada regra foram os agentes de produto e de design: você **não decide nada sobre a missão**, você constrói o que os documentos de `insumos/` já fixaram. Onde faltar informação, não invente: escreva `[[LACUNA: <o que falta>]]` dentro da tela e cite no resumo final.

**Nada de conteúdo inventado para «parecer real».** Nome de pessoa, de professor, de escola ou de turma; outra missão no catálogo; código BNCC; número; data: tudo sai dos `insumos/` com a grafia de lá. Na primeira execução, o catálogo do Hub ganhou duas missões irmãs com nomes e códigos BNCC que não existem, e o professor ganhou um nome que não estava em documento nenhum. Item de contexto que os documentos não trazem, como os outros cards de um catálogo, vira card neutro com `[[LACUNA: …]]`.

**Economia de contexto.** Cada mensagem reenvia a conversa inteira. Para achar o trecho de uma tela, use `search_directory` pelo ID (`E2-ALU-01`) nos `insumos/`, em vez de abrir um documento de 60 KB inteiro com `view_file`. Os `.types.ts` do DS são curtos: esses pode abrir. Capture cada estado no máximo 3 vezes.

## O que existe neste workspace

| Caminho | O que é | Pode editar? |
|---|---|---|
| `dados/missao.json` | Quadros: `{id, estado, etapa, ator, ambiente, proposito, acao, resultado, largura, altura}` | Não |
| `casca.tsx`, `casca-api.tsx` | A casca de revisão e a API que as telas usam (`useMissao`) | Não |
| `insumos/` | Documentos da missão: jornada, fluxo, wireframes, copy revisada, ambiente simulado, anexo da spec, spec, one-pager | Não |
| `dados/mock.ts` | Os dados mockados da missão inteira | **Só no lote de fundação** |
| `telas/_comum.tsx` | Molduras e blocos compartilhados | **Só no lote de fundação** |
| `assets/*.webp` | Imagens geradas por `gerar_imagem` | Só por `gerar_imagem` |
| `telas/<ID>.tsx` | Uma tela por arquivo | **Sim — é o seu trabalho** |
| `node_modules/@unooria/design-system/` | O DS real (`src/` e exemplos em `stories/`) | Não |

## Contrato de cada arquivo de tela

```tsx
import React, { useEffect, useState } from "react";
import { Button, ChatBubble, Composer } from "@unooria/design-system/unooriaai";
import { PuzzleBlock, PuzzleTrack, ProgressBar } from "@unooria/design-system/unooria";
import { useMissao } from "../casca-api";
import { PROJETOS, AMARA } from "../dados/mock";
import { JanelaUnooriaAI } from "./_comum";
import caderno from "../assets/caderno-de-frequencia.webp";

type Inicial = { selecionado?: string; pronto?: boolean };

function Tela({ inicial }: { inicial: Inicial }) {
  const { ir, sessao, definir } = useMissao();
  const [selecionado, setSelecionado] = useState(inicial.selecionado);
  // … a interação de verdade: seleção, arrastar, digitar, temporizadores da spec …
  const registrar = () => { definir("escolha_etapa3", selecionado); ir("E3-SIS-01"); };
  return <JanelaUnooriaAI>…</JanelaUnooriaAI>;
}

export const estados: Record<string, React.FC> = {
  "vazio sem seleção": () => <Tela inicial={{}} />,
  "projeto marcado": () => <Tela inicial={{ selecionado: "mesa-aberta" }} />,
  "pronto para registro": () => <Tela inicial={{ selecionado: "mesa-aberta", pronto: true }} />,
};
```

- O arquivo se chama exatamente `<ID>.tsx`.
- `estados` tem **uma chave por estado do quadro**, com o nome **idêntico** ao de `dados/missao.json`. Cada estado é um **ponto de partida** do mesmo componente interativo: a tela abre naquele estado e, a partir dali, responde ao estudante.
- **Interações da mecânica:** siga, para cada momento, a ficha de interação da seção 4 do one-pager (`#### Momento E.k`: gesto, resposta na hora, se não fizer, se errar, o que libera) e o fluxo de `03-fluxo-arestas.md`. Seleção, arrastar e soltar, digitação no composer, botão habilitado só quando a regra deixa, barra de progresso com o tempo exato da spec, mensagem da assistente que chega depois do «digitando», modal que abre e fecha: tudo funcionando. A correção e o gabarito são do servidor: **nunca** mostre ao estudante se ele acertou, a não ser que a ficha mande.
- **Navegação:** a ação que leva a outra tela chama `ir("<ID>")` ou `ir("<ID>", "<estado>")`, com ID e estado do inventário. O que uma tela posterior precisa saber (a escolha feita, o ranking, o caminho tomado) vai para a sessão com `definir(chave, valor)` e é lido com `sessao[chave]`, sempre com um valor padrão do mock para quem abre a tela direto pelo trilho.
- **Dados mockados:** tudo que é dado (projetos, pessoas, números, documentos, mensagens, linhas de tabela) vem de `dados/mock.ts`. A tela não repete literal de dado que está no mock. Texto de interface (rótulo, instrução, botão) sai de `06-copy-strings-revisada.md`, caractere a caractere.
- O quadro tem `largura × altura` do inventário. A raiz da tela ocupa `width: 100%; height: 100%`.

## Imagens

Use `gerar_imagem(nome, descricao, largura)` onde a missão mostra **foto, documento, cena ou ilustração**: o caderno de papel, a foto do projeto, o documento anexado, o avatar da personagem-guia. A ferramenta grava `assets/<nome>.webp`, e você importa com `import x from "../assets/<nome>.webp"`. Descreva como a imagem deve ser, sem pedir texto dentro dela: texto legível é sempre HTML por cima. Reaproveite as imagens que já existem em `assets/` antes de gerar outra. O teto é de 8 imagens novas por lote.

## Regras do Design System (o lint confere e reprova)

1. **Só importe** de `react`, `@unooria/design-system/unooriaai`, `@unooria/design-system/unooria`, `./_comum`, `../casca-api`, `../dados/mock` e `../assets/<nome>.webp` (arquivo que existe).
2. **Nenhuma cor escrita à mão:** nada de `#hex`, `rgb()` ou `hsl()`. Cor só por componente do DS ou por token: `var(--uai-…)` no UnooriaAI e `var(--unooria-…)` na plataforma, que estão em `node_modules/@unooria/design-system/src/<seção>/tokens/*.css`.
3. **Nenhuma fonte própria** (`fontFamily`, `@font-face`). Sem `<style>`, `localStorage`, `fetch` nem URL externa.
4. Estilo inline só para **layout** (`display`, `flex`, `grid`, `gap`, `padding`, `margin`, `width`, `height`, `overflow`, `position`, `object-fit`), de preferência com tokens de espaçamento.
5. Tela cuja ação no inventário não é «Aguardar…» tem de responder a alguma coisa (handler, temporizador ou `ir`). Todo `ir()` aponta para tela e estado do inventário.

## Qual seção do DS usar

- **ALU e SIS no ambiente `unooriaai`:** o cliente de IA UnooriaAI. Chrome, conversa, balões, composer, sugestões e modal vêm de `@unooria/design-system/unooriaai`. As peças da **mecânica** (tabela comparativa, blocos arrastáveis `PuzzleBlock`/`PuzzleTrack`, `ProgressBar`, cartões, `AlertBox`) vêm de `@unooria/design-system/unooria`: é o DS híbrido que o código de produção da plataforma usa.
- **PROF (Unooria Hub):** desktop cheio, só `@unooria/design-system/unooria`.

Antes de usar um componente, abra `node_modules/@unooria/design-system/src/<seção>/components/<Componente>/<Componente>.types.ts`, porque prop inventada quebra o build ou some calada. A composição de referência do UnooriaAI está em `node_modules/@unooria/design-system/stories/unooriaai/telas/Telas.stories.tsx`.

## Como trabalhar (repita até tudo passar)

1. Escreva ou edite `telas/<ID>.tsx`.
2. `construir_lote()` e corrija os erros de build.
3. `conferir_lint()` e zere os achados.
4. `auditar_lote()`: nenhum estado faltando, nenhum erro de montagem.
5. `interagir_tela(tela_id, estado, acoes)` joga a tela como um estudante, com a sequência da ficha de interação: clica, arrasta, digita, espera o tempo da spec. Confira se cada passo funcionou e se a tela foi para onde o fluxo manda (`depois`). Corrija o que não respondeu.
6. `capturar_tela(tela_id, estado)` e **abra o PNG com `view_file`**. Confira texto cortado, sobreposição, vazio sobrando, imagem distorcida, o que o wireframe pede e não aparece, e consistência com `_comum.tsx` e com as outras telas.
7. Quando todos os estados passarem nos passos 2 a 6, chame `finish` com o resumo por tela: o que foi feito, as interações que funcionam, as lacunas `[[LACUNA]]` e o que ficou pendente.

Não pare no primeiro build verde. A tela só está pronta depois que você a **jogou** e **viu**.
