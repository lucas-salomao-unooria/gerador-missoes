## O one-pager da missão, por trocas — o one-pager do PO é grande demais para ser reescrito

O PO anexou o one-pager da missão, com cerca de {tamanho_do_po} tokens: mais do que o modelo consegue devolver numa
resposta. Reescrito inteiro, ele sai cortado no meio e perde centenas de trechos do PO (teste de 25/10/2026). Por isso
este documento **não é reescrito**: o documento `one_pager` que você recebe já é o one-pager do PO — com as seções 0,
1, 3 e 4 copiadas por código do núcleo narrativo e as decisões do núcleo (18-parcial) no fim da seção 18 —, e você
devolve **só as trocas** que o seu trabalho pede. O código as aplica; tudo o que você não trocar fica como está.

Regras que valem para toda troca neste documento:

1. **O one-pager do PO é a missão aprovada.** Mude só o que o pedido do PO manda mudar, ou o que o voto de um comitê
   pedagógico mandou corrigir. Cada mudança no texto do PO entra também na tabela «Alterações sobre o one-pager do PO»
   (`| Trecho do PO | Como ficou | Pedido do PO ou voto do comitê |`), com o trecho do pedido ou do voto **entre aspas,
   copiado literalmente** — um código confere a citação. A troca que apaga texto do PO sem isso é recusada.
2. **O que um gate ou parecer pede e o PO não pediu vira proposta, não edição**: mantenha o texto do PO e acrescente ao
   lado `[PROPOSTA — validar com PO: <o que mudar> — <por quê>]`.
3. **Não decida no lugar do PO**: número, regra ou texto que só ele pode fixar vira `[PARÂMETRO — a definir por
   produto: …]` ou `[ABERTO — dono: PO: …]`.
4. **Acrescentar é troca**: use como `de` o trecho depois do qual o texto entra e repita-o no começo de `para`. Seção
   canônica que falta entra no lugar dela, depois do fim da seção anterior.
5. A resposta `estrutural` não existe aqui: o documento não pode ser reescrito. O que não couber numa troca vai para
   `pendencias`, e a esteira o mostra ao PO.
6. Nada a trocar é uma resposta válida: `"modo": "pontual"` com `edicoes` vazia.

### O seu trabalho nesta rodada

{tarefa_do_papel}

### Insumos

{insumos_do_papel}
