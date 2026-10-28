"""O PRD dá para codar sem perguntar (auditoria de 08/10/2026).

Lido como quem vai codar, o PRD da exp09ef1b deixava aberto: rotas do molde ausentes, corpo sem Zod,
`payload: Record<string, unknown>`, sem tabela de erros, `DELETE` para zerar, IA sem prompt nem schema, só `erDiagram`,
`score_*` na tabela da missão, régua sem predicado e o chat sem árvore de intenções. O gate (`tools/prd_codavel.py`)
reprova cada um; o PRD completo passa.
"""
from tools import prd_codavel as pc

SPEC = "## 11. Currículo\n\n| Código | Habilidade |\n|---|---|\n| EF06CO10 | consumo |\n| EF06CO03 | regra |\n"

ROTAS = """| ID | Método | Caminho | Papel |
|---|---|---|---|
| API-001 | GET | /exp06ef1b/sessao | estudante |
| API-002 | GET | /exp06ef1b/gate | estudante |
| API-003 | GET | /exp06ef1b/turmas | professor |
| API-004 | GET | /exp06ef1b/turmas/:turmaId/painel | professor |
| API-005 | POST | /exp06ef1b/turmas/:turmaId/zerar | professor |
| API-006 | GET | /exp06ef1b/turmas/:turmaId/pacotes | professor |
| API-007 | POST | /exp06ef1b/turmas/:turmaId/pacotes/:pacoteId/em-andamento | professor |
| API-008 | GET | /exp06ef1b/professor/material | professor |
| API-009 | POST | /exp06ef1b/turmas/:turmaId/gerar-conteudo | professor |
"""
PROMPT = " ".join(["Você gera os dezesseis posts da mostra a partir do recorte do professor."] * 8)
PRD = f"""# PRD

## 8. Requisitos funcionais
RF-01 — o professor gera o rascunho com IA.

## 11. Modelo de dados
```sql
CREATE TABLE exp06ef1b_sessoes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  escola_id TEXT NOT NULL,
  cadeia_tentativas INTEGER NOT NULL DEFAULT 0,
  voto_em TIMESTAMPTZ
);
ALTER TABLE exp06ef1b_sessoes FORCE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE, DELETE ON exp06ef1b_sessoes TO app_runtime;
```

## 12. Contratos de API
### 12.1 Rotas
{ROTAS}
```ts
export const VotoSchema = z.object({{ projetoId: z.string().uuid() }});
export const RascunhoSchema = z.object({{ posts: z.array(z.string().max(280)).length(16) }});
```

| Código | Status |
|---|---|
| missao-nao-liberada | 403 |

Idempotência: o segundo clique devolve a mesma sessão; lock por estudante. Rate limit: `rateLimit` por usuário, 429.

### 12.2 IA no preparo
| Chamada | Rota | Entrada | Saída | Prompt | Modelo | Quota | Fallback | Moderação |
|---|---|---|---|---|---|---|---|---|
| gerar posts | API-009 | recorte | RascunhoSchema | abaixo | padrao | professor | 429 sem-saldo | invariantes.ts |

```text
{PROMPT}
```

## 14. Pedagogia e conformidade
### 14.2 Ficha de evidência
| Habilidade | Marcador | Tipo | Pergunta | Regra | Nível | Grava na transação de | Critério |
|---|---|---|---|---|---|---|---|
| EF06CO03 | cadeia | acao | — | `cadeia_tentativas = 1 → atingiu` | 3 | API-001 | ... |
| EF06CO10 | canal B | multipla_escolha | PQ-1 | gabarito | 3 | Canal B | ... |
"""


def _codigos(r):
    return sorted({a["codigo"] for a in r["achados"] if a["severidade"] == "bloqueio"})


def test_prd_completo_da_para_codar():
    r = pc.validar(PRD, SPEC)
    assert r["status"] == "aprovado", r["achados"]


def test_cada_lacuna_da_exp09ef1b_reprova():
    casos = {
        "rota-do-molde-ausente": PRD.replace("| API-008 | GET | /exp06ef1b/professor/material | professor |\n", ""),
        "zerar-com-delete": PRD.replace("| API-005 | POST | /exp06ef1b/turmas/:turmaId/zerar", "| API-005 | DELETE | /exp06ef1b/turmas/:turmaId/zerar"),
        "contrato-sem-zod": PRD.replace("z.object(", "zobject("),
        "contrato-frouxo": PRD.replace("projetoId: z.string().uuid()", "payload: Record<string, unknown>"),
        "erros-sem-tabela": PRD.replace("| Código | Status |\n|---|---|\n| missao-nao-liberada | 403 |\n", ""),
        "ia-sem-prompt": PRD.replace(f"```text\n{PROMPT}\n```", ""),
        "ia-saida-sem-schema": PRD.replace("| RascunhoSchema |", "| PacoteSchema |"),
        "modelo-sem-ddl": PRD.replace("```sql", "```mermaid").replace("CREATE TABLE", "erDiagram"),
        "nivel-em-tabela-da-missao": PRD.replace("voto_em TIMESTAMPTZ", "score_ef06co03 INTEGER"),
        "regra-sem-coluna": PRD.replace("`cadeia_tentativas = 1 → atingiu`", "cumpre ordenadamente a rotina"),
        "ficha-tipo-invalido": PRD.replace("| cadeia | acao |", "| cadeia | observacao |"),
        "ficha-sem-habilidade": PRD.replace("| EF06CO10 | canal B | multipla_escolha | PQ-1 | gabarito | 3 | Canal B | ... |\n", ""),
    }
    for codigo, prd in casos.items():
        assert codigo in _codigos(pc.validar(prd, SPEC)), (codigo, _codigos(pc.validar(prd, SPEC)))
    assert "ficha-ausente" in _codigos(pc.validar(PRD.split("## 14.")[0], SPEC))
    assert _codigos(pc.validar("", SPEC)) == ["prd-vazio"]
    # régua que não vira predicado, marcada para o PO, não reprova
    proposta = PRD.replace("`cadeia_tentativas = 1 → atingiu`", "[PROPOSTA — validar com PO: tentativas]")
    assert "regra-sem-coluna" not in _codigos(pc.validar(proposta, SPEC))


def test_chat_com_texto_livre_exige_arvore_de_intencoes_no_banco_e_remissao_no_prd():
    spec_chat = SPEC + "\nO estudante digita a pergunta para a IA simulada do Conselho.\n"
    sem_arvore = pc.validar_intencoes("## Itens do brief\n", spec_chat)
    assert [a["codigo"] for a in sem_arvore] == ["chat-sem-intencoes"] and sem_arvore[0]["agente_responsavel"] == "banco-conteudo"
    banco = ("## Árvore de intenções\n\n| Intenção | Gatilhos | Resposta | Efeito |\n|---|---|---|---|\n"
             "| pedir orçamento | orçamento; quanto custa | `E2` → fala | nenhum |\n"
             "| sem correspondência | — | fala de fallback | nenhum |\n")
    assert pc.validar_intencoes(banco, spec_chat) == []
    assert "prd-sem-intencoes" in _codigos(pc.validar(PRD, spec_chat, banco))
    assert "prd-sem-intencoes" not in _codigos(pc.validar(PRD + "\nA árvore de intenções vive em conteudo.ts.\n", spec_chat, banco))
    # WhatsApp só com botões não precisa de árvore
    assert not pc.precisa_de_intencoes("secao_ds: whatsappmobile · a criança toca nos botões de resposta")


def test_gate_ligado_a_conferencia_do_prd_e_ao_banco():
    import inspect

    from agents import checkers

    fonte = inspect.getsource(checkers.RastroCheckAgent._run_async_impl)
    assert "prd_codavel" in fonte and "validar_intencoes" in fonte


def test_regra_com_cast_depois_do_parentese_e_predicado():
    """`(pericia_resultado->>'sinalizou_B')::boolean = true` saía `regra-sem-predicado` (exp03em1b-db50c2a9, 28/10/2026),
    e a própria mensagem do gate ensina `(coluna->>'chave')::int OP valor`."""
    com_cast = PRD.replace("`cadeia_tentativas = 1 → atingiu`", "`(cadeia_tentativas)::int = 1 → atingiu`")
    assert "regra-sem-predicado" not in _codigos(pc.validar(com_cast, SPEC))
    # mutante: o cast sem operador continua sem predicado
    sem_operador = PRD.replace("`cadeia_tentativas = 1 → atingiu`", "`(cadeia_tentativas)::int → atingiu`")
    assert "regra-sem-predicado" in _codigos(pc.validar(sem_operador, SPEC))
