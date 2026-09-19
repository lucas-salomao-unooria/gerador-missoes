---
name: contrato-saida
description: Envelope JSON que todo agente devolve quando roda dentro de uma orquestração automatizada. Anexado ao prompt pelo nó, não escrito dentro dos agentes.
sources: [chat]
---

# Contrato de saída

Os prompts dos agentes são escritos para leitura humana e produzem markdown. Uma esteira automatizada precisa decidir o próximo passo por programa, e prosa não é decidível.

**Solução: o nó anexa este bloco ao prompt do agente.** Nenhum arquivo de agente é alterado, e eles seguem funcionando em Cowork sem envelope.

## Bloco a anexar

```
Além do documento em markdown, devolva no fim da resposta um bloco
```json ... ``` com exatamente este formato, sem comentários:

{
  "agente": "<name do frontmatter>",
  "missao": "<slug>",
  "rodada": <int>,
  "status": "aprovado" | "bloqueado" | "concluido" | "devolvido",
  "artefatos": [{"caminho": "spec/x-spec.md", "titulo": "..."}],
  "achados": [
    {"severidade": "bloqueio" | "atencao" | "decisao_humana" | "oficio",
     "classe": "<classe da lacuna>" | null,
     "codigo": "<critério ou dimensão>",
     "agente_responsavel": "<name> | null",
     "resumo": "<uma linha>"}
  ],
  "precisa_humano": true | false,
  "devolucao": {"para": "<name>", "classe": "<classe da lacuna>"} | null
}
```

## Como a esteira lê

| Campo | Uso na orquestração |
|---|---|
| `status` | Roteia o próximo nó. `bloqueado` e `devolvido` param o fluxo |
| `precisa_humano` | Dispara a notificação e o nó de espera |
| `achados[].severidade` | `bloqueio` impede avanço · `decisao_humana` sempre notifica · `oficio` nunca bloqueia |
| `achados[].agente_responsavel` | Endereço do ticket no loop de feedback |
| `devolucao` | Volta ao agente 1 e incrementa o contador de devoluções |
| `artefatos` | O que gravar no armazenamento da missão |

## Regras

- O markdown continua sendo o entregável real. O JSON é roteamento, não substitui o documento.
- `status: "aprovado"` do agente 1 exige `artefatos` contendo a spec. Aprovação sem spec é erro de execução — a esteira deve falhar alto, não seguir.
- Contador de rodadas e contador de devoluções vivem no **estado da esteira**, nunca no prompt. O agente lê `rodada`, não a incrementa.
- `severidade: "oficio"` (🎨) nunca influencia roteamento.

## Adições v2

```json
"achados": [
  {"severidade": "bloqueio" | "atencao" | "decisao_humana" | "oficio",
   "id": "L1",
   "codigo": "<critério ou dimensão>",
   "classe": "<classe da lacuna>" | null,
   "agente_responsavel": "<name> | null",
   "resumo": "<uma linha>"}
],
"pronto": {"verificado": true, "itens_abertos": 0,
           "detalhe": [{"item": "<da lista>", "n": 0}]} | null
```

| Campo | Uso na orquestração |
|---|---|
| `pronto.itens_abertos` | `> 0` retém a entrega. O gate de ofício não roda sem os três em zero |
| `achados[].classe` | Contagem por classe, insumo do `candidatos-a-criterio` |
| `achados[].id` | Rastreia o achado do markdown ao envelope |

- `pronto: null` de um agente de construção é erro de execução, não "não verificado". A esteira deve falhar alto.
- `severidade: "oficio"` roteia sempre para `jornada`, nunca para o staff.
