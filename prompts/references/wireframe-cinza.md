---
name: wireframe-cinza
description: Paleta e regras da coleção de variáveis em escala de cinza usada nos wireframes lo-fi. Lido por telas.
sources: [chat]
---

# Coleção `wireframe-cinza`

Coleção local de variáveis para wireframes lo-fi. **Os nomes espelham 1:1 os slots do Unooria DS** — é isso que faz a subida pra alta fidelidade ser troca de coleção, não redesenho. Nome fora da nomenclatura do DS quebra a troca e transforma o wireframe em descarte.

| Slot | Valor | Uso |
|---|---|---|
| `superficie/base` | Branco | Fundo de tela |
| `superficie/elevada` | Cinza muito claro | Cards, painéis, barras |
| `superficie/midia` | Cinza médio | Placeholder de vídeo e imagem, com cruz diagonal |
| `borda/padrao` | Cinza claro | Divisórias, contorno de container |
| `borda/foco` | Preto | Estado ativo, seleção, foco de teclado |
| `texto/primario` | Preto | — |
| `texto/secundario` | Cinza escuro | — |
| `acao/primaria` | Preto, texto branco | — |
| `acao/secundaria` | Contorno preto, fundo transparente | — |

**Sem cor, em nenhuma hipótese** — nem para "só destacar uma coisinha". Uma exceção abre todas as outras.

## Como comunicar sem cor

- **Estado** → contorno, peso de traço, preenchimento de cinza. Nunca verde/vermelho.
- **Hierarquia** → tamanho e peso tipográfico. Uma família, dois ou três pesos.
- **Mídia** → placeholder com cruz diagonal na proporção correta. Nunca frame de vídeo real nem stock.
- **Ícone** → traço preto uniforme.
- **Pictograma de gesto e botão de áudio** → desenhados de verdade, nunca caixa cinza. São requisito de acessibilidade.
