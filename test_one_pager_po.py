"""O one-pager que o PO anexou é a missão: a esteira completa e confere, não redesenha (08/10/2026).

O reprocessamento da exp06ef1b pediu três correções ("não alterar a narrativa, o mecanismo e a estrutura") e saiu
com 253 de 304 trechos do PO reescritos, todos os gates 🟢. Estes testes fixam o que mudou: o one-pager do PO é
extraído do anexo, a conferência trecho a trecho reprova a reescrita, aceita só o que o pedido manda — com a
citação conferida em código —, e a ideação não inventa mecanismo novo.
"""
import asyncio

from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.sequential_agent import SequentialAgent

from agents.checkers import RastroCheckAgent, SaidaDeLoopAgent
from test_conteudo_aprovado import _rodar
from tools import one_pager_po as op

ONE_PAGER_PO = """# One-pager — O Júri Estadual de Projetos v1.5.2

### O que mudou nesta versão (v1.5.2)
- Ajuste de redação em toda a seção 4 para deixar o texto mais claro ao professor.

## 0. Identificação
- **Slug:** `exp06ef1b` · **Seção do DS:** `instanooria` · 6º ano EF, 1º bimestre

## 1. Descoberta central
O estudante descobre que as próprias curtidas fizeram o aplicativo esconder doze projetos da feira inteira.
Foco primário em EF06CO10, sustentado por EF06CO01, EF06CO03 e EF06CO07 nas etapas de auditoria do feed.

## 2. Currículo
- EF06CO07 — Entender o processo de transmissão de dados em pacotes através de múltiplos equipamentos.
- EF06CO03 — Descrever a regra condicional que estruturou o afunilamento algorítmico do feed do jurado.

## 3. Narrativa e personagem-guia
O estudante recebe o crachá de Jurado Oficial da Mostra Estadual de Projetos Escolares no aplicativo.

## 4. As 6 etapas — mecanismo, não intenção
### Etapa 5: Explicar
* **O que muda na tela:** O estudante deve conectar quatro blocos ordenados com base na sua própria experiência.
* **Regra do sistema:** O sistema só valida o esquema se o estudante ordenar corretamente a cadeia conceitual.

## 5. Verificação de ambiente
| Etapa | Em tela | Componente |
|---|---|---|
| 5. Explicar | Parcial (modal pedagógico com blocos conectáveis) | Painel de auditoria do jurado com blocos de encadeamento lógico |

## 6. Verbos e affordances
* Arrastar blocos para os slots de um a quatro com feedback sonoro discreto ao encaixar.

## 7. Caminhos degenerados
* O estudante que não usou a busca recebe o registro de Em processo no Canal A da habilidade.

## 8. Estados de falha
* Tentando reconectar aos servidores da Mostra Estadual, suas notas ficam guardadas no servidor.

## 9. Papel do professor
* **Ativar ou agendar:** o professor clica em "Liberar Missão Agora" ou opta por agendar para o horário da aula.

## 10. Tempos
| Etapa | Em tela | Fora de tela |
|---|---|---|
| **Total** | **29 min de atividade em tela** | **21 min de mediação fora da tela** |

## 11. Podcast
* **Formato:** Diálogo dinâmico entre dois jovens apresentadores da Unooria (Bia e Rafa).

## 12. Evidências e dados
| EF06CO07 | Canal A + B | **Pergunta:** "Quando você tocava no coração para curtir, como essa informação chegava ao sistema?" |
| EF06CO03 | Canal A + B | **Pergunta:** "Qual regra lógica descreve com exatidão a instrução que o programa executou?" |

## 15. Tetos aplicados à faixa etária
* Legendas de postagens: máximo de 60 palavras por projeto escolar exibido no feed.

## 16. Requisitos
* Avaliação de transferência com seleção de cartões na Etapa 6 e Enquete de Canal B.

## 17. Hipóteses
* H1: 85% dos estudantes terminam a navegação com o feed totalmente afunilado em um único tema.

## 18. Decisões
* Confirmada a implementação de um pop-up de confirmação dupla para impedir cliques acidentais no voto.
"""

BRIEFING = (
    "Reprocessamento de produto — exp06ef1b. A narrativa, o mecanismo das 6 etapas e a estrutura da missão estão "
    "aprovados — não alterar nenhum deles. Habilidade EF06CO07 ainda aparece como ativa no one-pager. Remover EF06CO07 "
    "de todas as seções onde aparece como habilidade mobilizada. Trocar o nome do apresentador Rafa por Tiago no podcast."
)


def _sem(texto: str, *trechos: str) -> str:
    for t in trechos:
        assert t in texto, t
        texto = texto.replace(t, "")
    return texto


# --------------------------------------------------------------------------- extração do anexo
def test_extrai_o_one_pager_entre_os_anexos_e_ignora_a_apostila():
    apostila = "### 📄 Documento de apoio (DOCX): apostila.docx\n\n# Unidade 1\n## 1. Introdução\nTexto da apostila."
    material = f"{apostila}\n\n### 📄 Documento de apoio (DOCX): 00-one-pager.docx\n\n{ONE_PAGER_PO}"
    extraido = op.extrair(material)
    assert extraido.startswith("# One-pager — O Júri Estadual")
    assert "apostila" not in extraido and "📄" not in extraido
    assert op.extrair(apostila) == ""
    assert op.extrair("") == ""


# --------------------------------------------------------------------------- a conferência
def test_sem_one_pager_do_po_nao_se_aplica():
    r = op.conferir("", "# qualquer one-pager", BRIEFING)
    assert r["status"] == "aprovado" and not r["aplica"]
    assert "NÃO SE APLICA" in op.relatorio(r)


def test_one_pager_preservado_aprova_e_vazio_bloqueia():
    assert op.conferir(ONE_PAGER_PO, ONE_PAGER_PO, BRIEFING)["status"] == "aprovado"
    # trocar a versão e formatar diferente não é reescrever
    reformatado = ONE_PAGER_PO.replace("v1.5.2", "v1.8.0").replace("**", "")
    assert op.conferir(ONE_PAGER_PO, reformatado, BRIEFING)["status"] == "aprovado"
    vazio = op.conferir(ONE_PAGER_PO, "   ", BRIEFING)
    assert vazio["status"] == "bloqueado" and vazio["achados"][0]["codigo"] == "one-pager-vazio"


def test_reescrever_o_mecanismo_bloqueia_com_a_lista_do_que_restaurar():
    """A exp06ef1b: a Etapa 5 virou "construir programa SE…ENTÃO" e o podcast trocou de formato."""
    gerado = ONE_PAGER_PO.replace(
        "O estudante deve conectar quatro blocos ordenados com base na sua própria experiência.",
        "O estudante constrói o programa visual que implementa a regra condicional SE … ENTÃO do feed.")
    r = op.conferir(ONE_PAGER_PO, gerado, BRIEFING)
    assert r["status"] == "bloqueado"
    assert [a["codigo"] for a in r["achados"]] == ["trecho-do-po-perdido"]
    assert "Etapa 5: Explicar" in r["achados"][0]["resumo"]
    assert "conectar quatro blocos ordenados" in r["achados"][0]["resumo"]
    assert "🔴 REESCREVEU" in op.relatorio(r, "exp06ef1b")


def test_habilidade_que_o_pedido_manda_remover_pode_sair_com_as_linhas_que_a_citam():
    gerado = _sem(ONE_PAGER_PO,
                  "- EF06CO07 — Entender o processo de transmissão de dados em pacotes através de múltiplos equipamentos.\n",
                  '| EF06CO07 | Canal A + B | **Pergunta:** "Quando você tocava no coração para curtir, como essa '
                  'informação chegava ao sistema?" |\n')
    gerado = gerado.replace("EF06CO03 e EF06CO07 nas etapas", "EF06CO03 nas etapas")
    r = op.conferir(ONE_PAGER_PO, gerado, BRIEFING)
    assert r["status"] == "aprovado", r["achados"]
    assert r["codigos_removidos"] == ["EF06CO07"] and r["removidas"] >= 3
    # sem o pedido de remoção, a mesma retirada é perda
    assert op.conferir(ONE_PAGER_PO, gerado, "Revisar a missão.")["status"] == "bloqueado"


def test_alteracao_pedida_vale_so_com_o_trecho_do_pedido_conferido():
    trecho = "* **Formato:** Diálogo dinâmico entre dois jovens apresentadores da Unooria (Bia e Rafa)."
    novo = ONE_PAGER_PO.replace(trecho, "* **Formato:** Diálogo dinâmico entre dois jovens apresentadores da Unooria (Bia e Tiago).")
    tabela = ("\n### Alterações sobre o one-pager do PO\n| Trecho do PO | Como ficou | Pedido do PO |\n|---|---|---|\n"
              "| Diálogo dinâmico entre dois jovens apresentadores da Unooria (Bia e Rafa). | (Bia e Tiago) | {pedido} |\n")
    certo = novo + tabela.format(pedido="«Trocar o nome do apresentador Rafa por Tiago no podcast»")
    r = op.conferir(ONE_PAGER_PO, certo, BRIEFING)
    assert r["status"] == "aprovado" and r["declaradas"] == 1, r["achados"]
    # o agente declara, mas a citação não existe no pedido: não vale, e o trecho conta como perdido
    inventado = novo + tabela.format(pedido="«Ajuste exigido A2 da adequação pedagógica»")
    r = op.conferir(ONE_PAGER_PO, inventado, BRIEFING)
    assert r["status"] == "bloqueado"
    assert {a["codigo"] for a in r["achados"]} == {"trecho-do-po-perdido", "alteracao-sem-pedido"}


def test_alteracao_pedida_por_voto_de_comite_vale_com_o_trecho_do_voto():
    """Desde 15/10/2026 o comitê pedagógico pode mandar reescrever o texto do PO (decisão do PO); a alteração cita o voto."""
    trecho = "* **Formato:** Diálogo dinâmico entre dois jovens apresentadores da Unooria (Bia e Rafa)."
    novo = ONE_PAGER_PO.replace(trecho, "* **Formato:** Diálogo dinâmico entre dois jovens apresentadores da Unooria (Bia e Tiago).")
    tabela = ("\n### Alterações sobre o one-pager do PO\n| Trecho do PO | Como ficou | Pedido |\n|---|---|---|\n"
              "| Diálogo dinâmico entre dois jovens apresentadores da Unooria (Bia e Rafa). | (Bia e Tiago) | "
              "Voto do comitê: «o apresentador precisa ter nome diferente do personagem Rafa da etapa 2» |\n")
    voto = ("# Comitê final\n- **F2-1** (Qualidade): nomes repetidos confundem. **Corrigir:** o apresentador precisa ter "
            "nome diferente do personagem Rafa da etapa 2\n")
    r = op.conferir(ONE_PAGER_PO, novo + tabela, BRIEFING, votos=voto)
    assert r["status"] == "aprovado" and r["declaradas"] == 1, r["achados"]
    # sem o voto, a mesma alteração não tem pedido
    assert op.conferir(ONE_PAGER_PO, novo + tabela, BRIEFING)["status"] == "bloqueado"


def test_colar_o_trecho_no_changelog_nao_conta_como_preservar():
    trecho = "* Arrastar blocos para os slots de um a quatro com feedback sonoro discreto ao encaixar."
    gerado = ONE_PAGER_PO.replace(trecho, "* Construir o programa condicional em blocos.")
    gerado += f"\n\n## Changelog v1.8.0\n- Trocado: {trecho}\n"
    assert op.conferir(ONE_PAGER_PO, gerado, BRIEFING)["status"] == "bloqueado"


def test_lacuna_aberta_pelo_po_pode_ser_fechada():
    po = ONE_PAGER_PO + "\n* [PROPOSTA P0b — a validar pelo time: toast após 60 segundos de inatividade na cédula de voto]\n"
    assert op.conferir(po, ONE_PAGER_PO, BRIEFING)["status"] == "aprovado"


# --------------------------------------------------------------------------- na esteira
def test_gate_na_esteira_e_loop_que_devolve_ao_autor():
    gerado = ONE_PAGER_PO.replace("Bia e Rafa", "Nina e Tiago, cinco blocos de três minutos e meio")

    def loop():
        return SequentialAgent(name="R", sub_agents=[LoopAgent(name="L", max_iterations=2, sub_agents=[
            RastroCheckAgent(name="C", modo="one_pager_po", rotulo="One-pager do PO preservado",
                             report_key="one_pager_po_report", status_key="one_pager_po_status",
                             agente="one-pager-do-po", estrito=False),
            SaidaDeLoopAgent(name="S", rotulo="One-pager do PO", status_keys=["one_pager_po_status"],
                             rodada_key="one_pager_po_rodada", max_rounds=2, autor_keys=["one_pager"]),
        ])])

    estado = asyncio.run(_rodar(loop(), {"one_pager_po": ONE_PAGER_PO, "one_pager": gerado, "briefing": BRIEFING}))
    assert estado["one_pager_po_status"] == "bloqueado"
    assert "Bia e Rafa" in estado["one_pager_po_report"]
    sem_po = asyncio.run(_rodar(loop(), {"one_pager": gerado}))
    assert sem_po["one_pager_po_status"] == "aprovado" and sem_po["one_pager_po_rodada"] == 1


def test_pedido_de_refazer_conta_como_pedido():
    """No refazer, o pedido vem em `pedido_correcao`, não no briefing — a citação também vale de lá."""
    from agents.checkers import _pedidos_de_produto

    estado = {"pedido_correcao": "Trocar o nome do apresentador Rafa por Tiago no podcast.",
              "pedidos_do_po": [{"etapa": "produto", "texto": "Remover EF06CO07 do contrato."},
                                {"etapa": "design", "texto": "Mudar o botão."}]}
    texto = _pedidos_de_produto(estado)
    assert "EF06CO07" in texto and "Rafa por Tiago" in texto and "botão" not in texto


# --------------------------------------------------------------------------- quem escreve e quem avalia
def test_ideacao_dispensada_quando_o_po_trouxe_o_one_pager():
    from agents.callbacks import IDEACAO_DISPENSADA, dispensar_ideacao_com_one_pager_do_po

    class _Ctx:
        def __init__(self, state):
            self.state = state

    assert dispensar_ideacao_com_one_pager_do_po(_Ctx({"briefing": "x"})) is None
    conteudo = dispensar_ideacao_com_one_pager_do_po(_Ctx({"one_pager_po": ONE_PAGER_PO}))
    assert conteudo.parts[0].text == IDEACAO_DISPENSADA


def test_lint_aceita_numero_do_po_e_agendamento_com_proposta():
    from tools.contrato_produto import validar_one_pager

    linha = "* Legendas de postagens: máximo de 60 palavras por projeto escolar exibido no feed."
    one_pager = ONE_PAGER_PO.replace(
        '* **Ativar ou agendar:** o professor clica em "Liberar Missão Agora" ou opta por agendar para o horário da aula.',
        '* **Ativar ou agendar:** o professor clica em "Liberar Missão Agora" ou opta por agendar para o horário da aula. '
        "[PROPOSTA — validar com PO: a plataforma não agenda (ADR-146); trocar por «Pôr no ar agora»]")
    codigos = lambda r: {a["codigo"] for a in r["achados"]}  # noqa: E731
    assert "agendamento" not in codigos(validar_one_pager(one_pager, one_pager_po=ONE_PAGER_PO))
    assert "agendamento" in codigos(validar_one_pager(ONE_PAGER_PO))
    sem_origem = validar_one_pager(ONE_PAGER_PO)
    assert any(linha[:40] in a["resumo"] for a in sem_origem["achados"] if a["codigo"] == "numero-sem-origem")
    com_po = validar_one_pager(ONE_PAGER_PO, one_pager_po=ONE_PAGER_PO)
    assert not any(linha[:40] in a["resumo"] for a in com_po["achados"] if a["codigo"] == "numero-sem-origem")


def test_runner_guarda_o_one_pager_do_po_e_o_salvo_vence():
    from pipeline.runner import one_pager_do_po

    material = f"### 📄 Documento de apoio (DOCX): 00-one-pager.docx\n\n{ONE_PAGER_PO}"
    assert one_pager_do_po({"material_anexado": material}, None).startswith("# One-pager")
    assert one_pager_do_po({"material_anexado": material, "one_pager_po": "salvo"}, None) == "salvo"
    assert one_pager_do_po({}, None) == ""


def test_quem_escreve_e_quem_avalia_recebem_o_one_pager_do_po():
    from prompts import load_prompt

    for arquivo in ("004_nucleo_narrativo", "014_secoes_apoio", "026_gate_estrutural", "revisor_one_pager",
                    "029a_avaliacao_pedagogica", "029b_experiencia_estudante", "029c_adequacao_pedagogica", "043_gate_final",
                    "037_restaurar_one_pager_po"):
        texto = load_prompt(f"produto/{arquivo}.md")
        assert "{one_pager_po?}" in texto, arquivo
    # o parecer que exigiu trocar o mecanismo da exp06ef1b não via o briefing
    assert "{briefing?}" in load_prompt("produto/029c_adequacao_pedagogica.md")


def test_fidelidade_le_o_briefing_em_prosa_e_a_ordem_de_nao_mexer_vira_trava():
    """O briefing do reprocessamento da exp06ef1b não tem título: o checklist saía com um item só e o juiz não rodava."""
    from tools.fidelidade import montar_checklist

    itens = montar_checklist([], BRIEFING)
    travas = [i["texto"] for i in itens if i["tipo"] == "trava"]
    assert any("não alterar nenhum deles" in t for t in travas)
    assert any(i["tipo"] == "briefing" and "Remover EF06CO07" in i["texto"] for i in itens)
    # briefing com títulos continua no parser de seções: a prosa só entra quando nada foi reconhecido
    com_titulo = "CONSTRAINT DE INTERFACE — OBRIGATÓRIO\nsecao_ds: unoogaleria\nÉ PROIBIDO usar outra seção do DS."
    assert all(i["tipo"] != "briefing" for i in montar_checklist([], com_titulo))
