---
name: wireframe-cinza
description: Paleta e regras da coleção de variáveis em escala de cinza usada nos wireframes lo-fi. Lido por telas.
sources: [chat]
---

# Coleção `wireframe-cinza`

Coleção local de variáveis para wireframes lo-fi. **Os nomes espelham 1:1 os slots do Unooria DS** — é isso que faz a subida pra alta fidelidade ser troca de coleção, não redesenho. Nome fora da nomenclatura do DS quebra a troca e transforma o wireframe em descarte.

| Slot | Valor | Uso |
|---|---|---|
| `superficie/base` | Branco (`#FFFFFF`) | Fundo de tela |
| `superficie/elevada` | Cinza muito claro (`#FAFAFA`) | Cards, painéis, barras |
| `superficie/midia` | Cinza médio (`#E0E0E0`) | Placeholder de vídeo e imagem, com cruz diagonal |
| `borda/padrao` | Cinza claro (`#C7C7C7`) | Divisórias, contorno de container |
| `borda/foco` | Preto (`#1A1A1A`) | Estado ativo, seleção, foco de teclado |
| `texto/primario` | Preto (`#1A1A1A`) | — |
| `texto/secundario` | Cinza escuro (`#6B6B6B`) | — |
| `acao/primaria` | Preto (`#1A1A1A`), texto branco | — |
| `acao/secundaria` | Contorno preto (`#1A1A1A`), fundo transparente | — |

**Sem cor, em nenhuma hipótese** — nem para "só destacar uma coisinha". Uma exceção abre todas as outras.

## Como comunicar sem cor

- **Estado** → contorno, peso de traço, preenchimento de cinza. Nunca verde/vermelho.
- **Hierarquia** → tamanho e peso tipográfico. Uma família, dois ou três pesos.
- **Mídia** → placeholder com cruz diagonal na proporção correta. Nunca frame de vídeo real nem stock.
- **Ícone** → traço preto uniforme.
- **Pictograma de gesto e botão de áudio** → desenhados de verdade, nunca caixa cinza. São requisito de acessibilidade.
