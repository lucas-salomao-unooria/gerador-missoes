# Esteira de missões Unooria — pacote para o time de dev

Nove agentes que levam uma missão de one-pager a entrega, com dois portões de qualidade e dois pontos de decisão humana.

## Por onde começar

1. `agents/00-PIPELINE.md` — a ordem dos agentes e a divisão de escopo. Leia primeiro.
2. `ORQUESTRACAO-N8N.md` — a especificação da esteira em n8n. É o documento de implementação.
3. `references/contrato-saida.md` — o envelope JSON que os nós usam para rotear.

## O que tem aqui

```
agents/          9 agentes + o mapa do pipeline. Prompts, um por arquivo.
references/      Conhecimento compartilhado entre missões e entre agentes.
exemplo/         Uma missão real, parcialmente rodada, para conferência.
```

## Duas coisas que importam mais que o resto

**O agente 1 é portão e autoridade de especificação.** Veredito binário: 🟢 ou 🔴. Se passou, ele emitiu `spec/<missao>-spec.md`, e é contra a spec que todo mundo constrói — não contra o one-pager. Aprovação sem spec é erro de execução, e a esteira deve falhar alto.

**O agente 6 valida a nossa esteira, não a de upstream.** Ele pergunta "a esteira produziu certo?". Se ele encontrar problema de missão, isso é falha do agente 1 e conta como devolução. Devoluções por missão é a métrica de saúde do portão, meta zero.

## O que está incompleto, de propósito

- **Sem workflow JSON pronto.** Motivo em `ORQUESTRACAO-N8N.md`.
- **`references/ambientes.md` tem as chaves de arquivo em branco** e a fronteira fixo/da-missão a preencher. Decisão de produto, não de implementação.
- **`references/exemplares.md` está vazio.** Enche quando as primeiras missões fecharem.
- **Não existe agente de enquadramento** antes do portão. A esteira começa num one-pager pronto e valida pra baixo — nada pergunta se a missão deveria existir.

## Estado da missão de exemplo

`exemplo/` traz a Magia ou Truque? (1º EF, TikTok simulado) com o one-pager v1.1, dois relatórios de Gate 0, o briefing de ofício e a jornada.

Ela está **🔴 BLOQUEADA** e sem spec — duas lacunas de mecânica e uma decisão de ambiente em aberto. Serve como caso de teste: rodada pelo agente 1, a esteira tem que devolver 🔴.
