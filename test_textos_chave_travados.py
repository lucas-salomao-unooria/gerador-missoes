"""PR 7 do plano «Produto dono do contrato» (docs/planos/2026-10-23-produto-dono-do-contrato.md, D1 e D7): textos-chave
com ID travados do one-pager à copy; fluxo e telas sem mudar o contrato.

- a tabela de textos-chave sai do one-pager por código (aspas do §4, opções de cada escolha, roteiro do §9, podcast
  do §11; o Canal B do §12a saiu por decisão do PO de 29/10/2026), com ID estável — o texto trocado no mesmo lugar
  guarda o ID, o que sai se aposenta; a sessão anterior ao PR 7 é lida das mesmas seções, sem gravar nada;
- o texto-chave é copiado por código para a copy (e para a citação quase igual no handoff, no PRD e no pedagógico), a
  redação do design vira [PROPOSTA] ao PO, e o gate bloqueia a divergência que sobra — os mutantes «Pronto», «Criança
  lendo» e «opção Lugar removida»;
- o lint de produto acusa o texto-chave acima do teto de palavras, e ele vira item do de acordo (PR 3);
- o gate de arestas do fluxo e de regras de habilitação contra o bloco 2 pega a A13 e a A20 da exp02ef1b e nada nas
  outras 14 missões do acervo;
- o preparo do professor (E0-PROF-01…05) virou padrão da plataforma em references/, sem mudar o que os prompts pedem.

Tudo sem modelo, sobre os estados do acervo (`tests/acervo`).
"""
from __future__ import annotations

import asyncio
import copy
import json
import re
import warnings
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict

import pytest

from tools import arestas as ar
from tools import fechar_contrato as fc
from tools import textos_chave as tk

warnings.filterwarnings("ignore", category=DeprecationWarning)

ACERVO = Path(__file__).resolve().parent / "tests" / "acervo"


def _estado(missao: str = "exp02ef1b-4fd72a9a") -> Dict[str, Any]:
    return json.loads((ACERVO / missao / "estado.json").read_text(encoding="utf-8"))


def _por_texto(tcs, trecho: str):
    return next(t for t in tcs if trecho in t.texto)


# --------------------------------------------------------------------------- a tabela, do one-pager
FALA = "Oi, turma do segundo ano! Aqui é a Clara!"  # `TC-02` da exp02ef1b, a primeira fala do podcast (§11)


def test_exp02ef1b_tem_a_escolha_da_5a_com_tres_opcoes_e_nenhum_canal_b():
    tcs = tk.da_sessao(_estado())
    escolha = next(t for t in tcs if t.tipo == tk.OPCOES and "Lugar" in t.texto)
    assert escolha.n == 3 and escolha.origem == "§4 · Etapa 5"
    opcoes = [t for t in tcs if t.grupo == escolha.id]
    assert [o.texto for o in opcoes] == ["Atividade", "Cor da roupa", "Lugar"]
    assert [o.id for o in opcoes] == [f"{escolha.id}.1", f"{escolha.id}.2", f"{escolha.id}.3"]
    # o Canal B do §12a saiu da esteira (decisão do PO de 29/10/2026): a pergunta e as alternativas não viram texto-chave
    assert not [t for t in tcs if t.tipo == tk.CANAL_B or t.origem.startswith("§12a")]
    assert not any(t.texto.startswith(("Para mostrar em uma foto", "A parede bonita")) for t in tcs)
    assert tk.por_id(tcs)["TC-02"].texto == FALA
    # o podcast entra fala a fala; as opções não entram de novo como texto de tela
    assert sum(1 for t in tcs if t.tipo == tk.PODCAST) == 18
    assert not any(t.tipo == tk.TELA and t.texto == "Cor da roupa" for t in tcs)


@pytest.mark.parametrize("missao", ["exp02em1b-60cfa7f4", "exp06ef1b-53e011b6", "exp03em1b-b2e7b4a3", "exp09ef1b"])
def test_extrair_nao_gera_mais_canal_b_nos_formatos_do_acervo(missao):
    """Decisão do PO de 29/10/2026: o Canal B saiu do one-pager. As quatro missões que traziam o §12a em formatos
    diferentes (com e sem aspas, «Alternativa 1:», «[Atingiu]» na frente) continuam com o Canal B gravado, e `extrair`
    não gera texto-chave dele — o tipo `CANAL_B` fica só para ler o registro das sessões antigas."""
    tcs = tk.extrair(_estado(missao)["one_pager"])
    assert tcs and not [t for t in tcs if t.tipo == tk.CANAL_B or t.origem.startswith("§12a")]
    assert not hasattr(tk, "canal_b")
    assert tk.CANAL_B in tk.ROTULO_TIPO


def test_escolhas_do_s4_sao_so_as_listas_de_opcoes():
    """Calibrado no acervo: a lista depois de um verbo de escolha, a enumerada e a canônica — não os comentários que «os
    comentários dizem» (exp03ef1b), nem os horários do post (exp02em1b)."""
    assert tk.escolhas_do_s4(_estado("exp03ef1b")["one_pager"]) == []
    em = tk.escolhas_do_s4(_estado("exp02em1b-60cfa7f4")["one_pager"])
    assert [len(o) for _, o in em] == [2, 3] and not any("16h00" in x for _, o in em for x in o)
    canonica = "## 4. As 6 etapas\n### Etapa 3: Decidir\n- **Opções (3):** \"Brincar\" · \"Estudar\" · \"Comer\"\n"
    assert tk.escolhas_do_s4(canonica) == [("3", ["Brincar", "Estudar", "Comer"])]


def test_sessao_anterior_ao_pr7_e_lida_sem_gravar_e_sempre_igual():
    estado = _estado()
    antes = copy.deepcopy(estado)
    a, b = tk.da_sessao(estado), tk.da_sessao(estado)
    assert estado == antes and tk.KEY_REGISTRO not in estado
    assert [t.como_dict() for t in a] == [t.como_dict() for t in b]
    assert a[0].id == "TC-01"


def test_id_estavel_quando_o_po_troca_o_texto_no_mesmo_lugar():
    """Cascata do PR 5: o editor de produto troca o texto no one-pager; o ID fica, o texto novo desce por código. O texto
    que sai do one-pager se aposenta, e o número dele não volta."""
    estado = _estado()
    tcs, registro = tk.atualizar(estado)
    fala = _por_texto(tcs, "Valeu, turma! Até a próxima aventura")
    lugar = next(t for t in tcs if t.tipo == tk.OPCAO and t.texto == "Lugar")
    # o PO pede, em design, 2 opções na 5A e outra redação para a última fala do podcast; produto pontual aplica
    one_pager = (estado["one_pager"]
                 .replace('a "Atividade", descartando "Cor da roupa" e "Lugar"', 'a "A atividade", descartando "A cor da roupa"')
                 .replace("Valeu, turma! Até a próxima aventura fotográfica!", "Valeu, turma! Até a próxima aventura!"))
    novo_estado = {**estado, "one_pager": one_pager, tk.KEY_REGISTRO: registro}
    novos, registro2 = tk.atualizar(novo_estado)
    assert _por_texto(novos, "Valeu, turma! Até a próxima aventura!").id == fala.id
    assert not [t for t in novos if t.tipo == tk.CANAL_B]
    escolha = next(t for t in novos if t.tipo == tk.OPCOES and t.origem == "§4 · Etapa 5")
    assert escolha.n == 2 and escolha.id == lugar.grupo
    assert [t.texto for t in novos if t.grupo == escolha.id] == ["A atividade", "A cor da roupa"]
    assert lugar.id in {d["id"] for d in registro2["aposentados"]}
    # um texto novo ganha número novo, e o aposentado não volta
    acrescido = one_pager.replace("### Etapa 5: Explicar", "### Etapa 5: Explicar\n- Bento diz: \"Que história essa foto conta para você?\"")
    terceiros, registro3 = tk.atualizar({**novo_estado, "one_pager": acrescido, tk.KEY_REGISTRO: registro2})
    novo_tc = _por_texto(terceiros, "Que história essa foto conta")
    maior = max(tk.partes_do_id(t.id)[0] for t in novos)
    assert tk.partes_do_id(novo_tc.id)[0] == maior + 1
    assert lugar.id not in {t.id for t in terceiros}


def test_tabela_do_po_no_one_pager_dele_da_os_ids():
    estado = _estado()
    estado["one_pager_po"] = ("## Textos-chave\n\n| ID | Tipo | Origem | Texto aprovado |\n|---|---|---|---|\n"
                              f"| TC-40 | podcast | §11 | «{FALA}» |\n")
    tcs = tk.da_sessao(estado)
    assert _por_texto(tcs, FALA).id == "TC-40"
    # quem não estava na tabela do PO continua numerado, depois do maior dele
    assert all(tk.partes_do_id(t.id)[0] > 40 for t in tcs if t.texto != FALA)


def test_tabela_em_markdown_tem_id_tipo_origem_e_palavras():
    estado = _estado()
    tcs, registro = tk.atualizar(estado)
    md = tk.tabela(tcs, tk.teto_de_palavras(estado["one_pager"], estado.get("briefing", "")))
    assert md.startswith(f"## {tk.TITULO_TABELA}")
    assert "| `TC-01` | escolha · 3 opções | §4 · Etapa 5 | «Atividade» · «Cor da roupa» · «Lugar» | — |" in md
    assert f"| `TC-02` | podcast | §11 | «{FALA}» | 9 |" in md
    assert "Canal B" not in md
    # a própria tabela é lida de volta (é o que vale quando o PO já a traz no one-pager dele)
    lidos = {d["id"]: d for d in tk.ler_tabela(md)}
    assert lidos["TC-01"]["tipo"] == tk.OPCOES and lidos["TC-01"]["n"] == 3 and lidos["TC-01.3"]["texto"] == "Lugar"
    # o texto acima do teto leva o ⚠️ na coluna das palavras (exp06ef1b: o TC-10 do §4, 81 palavras, teto 60 por texto)
    e06 = _estado("exp06ef1b-53e011b6")
    md06 = tk.tabela(tk.da_sessao(e06), tk.teto_de_palavras(e06["one_pager"], e06.get("briefing", "")))
    assert re.search(r"\| `TC-10` \| texto de tela \| §4 · Etapa 6 \| «Na eleição para o Grêmio .*» \| 81 ⚠️ teto 60 \|", md06)


# --------------------------------------------------------------------------- copy: copiado por código, gate, mutantes
def _copy_de_teste(linhas_extra: str = "") -> str:
    return ("# Copy — exp02ef1b — passada 2\n\n"
            "| ID tela | Chave | Tipo | Seção | PT-BR (final) | Palavras | Redundância | Voz | Revisão (o que mudou e por quê) |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            "| `E5-ALU-01` | `e5.opt.atividade` | rótulo de UI | unoogaleria | Atividade | 1 | texto+ícone | plataforma | `TC-01.1` |\n"
            "| `E5-ALU-01` | `e5.opt.roupa` | rótulo de UI | unoogaleria | Cor da roupa | 3 | texto+ícone | plataforma | `TC-01.2` |\n"
            "| `E5-ALU-01` | `e5.opt.lugar` | rótulo de UI | unoogaleria | Lugar | 1 | texto+ícone | plataforma | `TC-01.3` |\n"
            f"| `E6-PROF-01` | `podcast.clara.abertura` | fala do podcast | unooria | {FALA} | 9 | áudio | Clara | `TC-02` |\n"
            "| `E4-ALU-02` | `e4.btn.pronto` | rótulo de UI | unoogaleria | Pronto | 1 | texto+ícone | plataforma | microcopy |\n"
            + linhas_extra)


def test_copy_fiel_passa_e_o_codigo_nao_muda_nada():
    tcs = tk.da_sessao(_estado())
    copia = _copy_de_teste()
    aplicado = tk.aplicar_na_copy(copia, tcs)
    assert aplicado["copiados"] == 0 and not aplicado["propostas"]
    r = tk.conferir_copy(aplicado["texto"], tcs)
    assert not [a for a in r["achados"] if a["severidade"] == "bloqueio"]


def test_mutante_pronto_texto_chave_trocado_por_microcopy():
    """«Pronto» no lugar da primeira fala do podcast, na linha que cita `TC-02`: o gate bloqueia a copy como veio; o
    código copia o texto aprovado de volta, e «Pronto» vira proposta ao PO."""
    tcs = tk.da_sessao(_estado())
    pergunta = _por_texto(tcs, FALA)
    mutante = _copy_de_teste().replace(FALA + " | 9 |", "Pronto | 1 |")
    r = tk.conferir_copy(mutante, tcs)
    assert r["status"] == "bloqueado"
    assert [a["codigo"] for a in r["achados"] if a["severidade"] == "bloqueio"] == ["texto-chave-divergente"]
    aplicado = tk.aplicar_na_copy(mutante, tcs)
    assert f"| {pergunta.texto} | 9 |" in aplicado["texto"]
    assert f"[PROPOSTA — validar com PO: {pergunta.id} «{pergunta.texto}» → «Pronto»" in aplicado["texto"]
    depois = tk.conferir_copy(aplicado["texto"], tcs)
    assert depois["status"] == "amarelo"  # a copy de teste não tem o podcast: o resto é 🟡 «sem linha»
    proposta = next(a for a in depois["achados"] if a["codigo"] == "texto-chave-proposta")
    assert proposta["severidade"] == "decisao_humana" and proposta["agente_responsavel"] == "PO"
    assert not [a for a in depois["achados"] if a["severidade"] == "bloqueio"]
    # idempotente: a segunda passada não muda nada e a proposta continua uma só
    de_novo = tk.aplicar_na_copy(aplicado["texto"], tcs)
    assert de_novo["texto"] == aplicado["texto"] and aplicado["texto"].count("[PROPOSTA — validar com PO:") == 1


def test_mutante_crianca_lendo_opcao_renomeada():
    """A opção «Atividade» renomeada para «Criança lendo»: com o ID na linha, o código restaura e registra a proposta; sem
    o ID, a opção some — escolha com opção a menos bloqueia."""
    tcs = tk.da_sessao(_estado())
    com_id = _copy_de_teste().replace("| Atividade | 1 |", "| Criança lendo | 2 |")
    aplicado = tk.aplicar_na_copy(com_id, tcs)
    assert "| Atividade | 1 |" in aplicado["texto"] and "«Atividade» → «Criança lendo»" in aplicado["texto"]
    assert tk.conferir_copy(com_id, tcs)["status"] == "bloqueado"
    sem_id = com_id.replace("| `TC-01.1` |", "| — |")
    r = tk.conferir_copy(sem_id, tcs)
    assert "opcoes-divergentes" in [a["codigo"] for a in r["achados"] if a["severidade"] == "bloqueio"]
    assert "«Atividade»" in next(a["resumo"] for a in r["achados"] if a["codigo"] == "opcoes-divergentes")
    # o código não inventa a linha da opção: a divergência sobra depois da cópia
    assert tk.conferir_copy(tk.aplicar_na_copy(sem_id, tcs)["texto"], tcs)["status"] == "bloqueado"


def test_mutante_opcao_lugar_removida():
    """O nº de opções é texto-chave (D1): a 5A com 2 linhas, sem «Lugar», bloqueia e volta ao dono da copy."""
    tcs = tk.da_sessao(_estado())
    mutante = "\n".join(l for l in _copy_de_teste().splitlines() if "e5.opt.lugar" not in l) + "\n"
    r = tk.conferir_copy(tk.aplicar_na_copy(mutante, tcs)["texto"], tcs)
    assert r["status"] == "bloqueado"
    achado = next(a for a in r["achados"] if a["codigo"] == "opcoes-divergentes")
    assert "3 opções" in achado["resumo"] and "«Lugar»" in achado["resumo"]
    assert achado["agente_responsavel"] == "copy-ptbr-revisao"
    # e a opção a mais também
    a_mais = _copy_de_teste("| `E5-ALU-01` | `e5.opt.cena` | rótulo de UI | unoogaleria | Cenário | 1 | texto | p | `TC-01.4` |\n")
    r = tk.conferir_copy(a_mais, tcs)
    assert any(a["codigo"] == "opcoes-divergentes" and "TC-01.4" in a["resumo"] for a in r["achados"])


def test_copy_real_da_exp02ef1b_mostra_o_pedido_do_po_que_ficou_so_em_design():
    """A copy revisada da exp02ef1b (23/10) trazia as opções que o PO pediu em design e que nunca chegaram ao one-pager: o
    código devolve o texto aprovado à linha, e o pedido vira proposta — o PO o leva a produto pelo Refazer. «Lugar» saiu
    da 5A, e o código não o inventa: bloqueia. A redação do Canal B que a copy também trazia não é mais texto-chave
    (decisão do PO de 29/10/2026) e não vira proposta."""
    estado = _estado()
    tcs = tk.da_sessao(estado)
    copia = estado["copy_strings_revisada"]
    aplicado = tk.aplicar_na_copy(copia, tcs)
    propostas = {i: p for i, _, p in aplicado["propostas_novas"]}
    assert propostas == {"TC-01.1": "A atividade", "TC-01.2": "A cor da roupa"}
    assert "| `e5.opt.atividade` | rótulo de UI | `unoogaleria` | Atividade | 1 |" in aplicado["texto"]
    r = tk.conferir_copy(aplicado["texto"], tcs)
    assert [a["codigo"] for a in r["achados"] if a["severidade"] == "bloqueio"] == ["opcoes-divergentes"]


def test_moldura_em_volta_do_texto_chave_fica_e_so_a_reescrita_muda():
    """exp01em1b-e89e91b3: «Chamado #101 — Beatriz (23h45): "…"» na linha; a reescrita está entre as aspas. O código troca
    só o trecho; e a linha que já traz o texto-chave com moldura não muda."""
    estado = _estado("exp01em1b-e89e91b3")
    tcs = tk.da_sessao(estado)
    aplicado = tk.aplicar_na_copy(estado["copy_strings_revisada"], tcs)
    linha = next(l for l in aplicado["texto"].splitlines() if "e4.narrativa.ticket_beatriz" in l)
    assert "Chamado #101 — Beatriz (23h45):" in linha and "Trilha Avançada do [recorte da aula]" in linha
    assert tk.aplicar_na_copy(aplicado["texto"], tcs)["texto"] == aplicado["texto"]


def test_lacuna_preenchida_nao_e_reescrita():
    """`[Opção votada pelo estudante]` no one-pager, `{motivo}` na copy (exp05ef1b): o mesmo texto-chave."""
    assert tk.mesmo_texto("Seu motivo declarado: [Opção votada pelo estudante]", "Seu motivo declarado: {motivo}")
    assert tk.mesmo_texto("Reforço Básico", "Reforço Básico.")
    assert not tk.mesmo_texto("Atividade", "A atividade")


def test_proposta_da_passada_1_sobrevive_a_revisao():
    """A passada 1 registrou a proposta; a revisão reemite a copy com o texto aprovado: a proposta continua na seção da
    esteira até o PO decidir."""
    tcs = tk.da_sessao(_estado())
    pergunta = _por_texto(tcs, FALA)
    passada1 = tk.aplicar_na_copy(_copy_de_teste().replace(FALA + " | 9 |", "Pronto | 1 |"), tcs)["texto"]
    revisada = tk.remover_secao(passada1) + "\n## Seções carregadas da passada 1\n\n" + passada1.split("## " + tk.TITULO_SECAO_COPY)[1]
    revisada = revisada.replace("## Seções carregadas da passada 1\n\n", "## Seções carregadas da passada 1\n\n### " + tk.TITULO_SECAO_COPY, 1)
    final = tk.aplicar_na_copy(revisada, tcs)
    assert final["texto"].count(tk.TITULO_SECAO_COPY) == 1
    assert any(i == pergunta.id and p == "Pronto" for i, _, p in final["propostas"])


@pytest.mark.parametrize("missao", ["exp02em1b-60cfa7f4", "exp03em1b-b2e7b4a3", "exp09ef1b", "exp06ef1b-53e011b6"])
def test_copia_por_codigo_e_idempotente_no_acervo(missao):
    estado = _estado(missao)
    tcs = tk.da_sessao(estado)
    uma = tk.aplicar_na_copy(estado["copy_strings_revisada"], tcs)
    duas = tk.aplicar_na_copy(uma["texto"], tcs)
    assert duas["texto"] == uma["texto"] and duas["copiados"] == 0
    assert not [a for a in tk.conferir_copy(uma["texto"], tcs)["achados"] if a["codigo"] == "texto-chave-divergente"]


# --------------------------------------------------------------------------- agentes e callbacks
async def _rodar(agente, estado):
    from google.adk.agents.sequential_agent import SequentialAgent
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    runner = InMemoryRunner(agent=SequentialAgent(name="R", sub_agents=[agente]), app_name="teste")
    await runner.session_service.create_session(app_name="teste", user_id="u", session_id="s", state=estado)
    async for _ in runner.run_async(user_id="u", session_id="s",
                                    new_message=types.Content(role="user", parts=[types.Part(text="go")])):
        pass
    final = await runner.session_service.get_session(app_name="teste", user_id="u", session_id="s")
    return dict(final.state)


def test_agente_da_copy_copia_confere_e_grava_o_registro():
    from agents.checkers import TextosChaveCopyAgent

    estado = _estado()
    base = {k: estado[k] for k in ("one_pager", "briefing", "spec_missao")}
    tcs = tk.da_sessao(estado)
    pergunta = _por_texto(tcs, FALA)
    base["copy_strings_revisada"] = _copy_de_teste().replace(FALA + " | 9 |", "Pronto | 1 |")
    final = asyncio.run(_rodar(TextosChaveCopyAgent(name="A078bTextosChave"), base))
    assert f"| {pergunta.texto} | 9 |" in final["copy_strings_revisada"]
    assert final["textos_chave_status"] == "amarelo"
    assert final["textos_chave_status_envelope"]["achados"][0]["codigo"] == "texto-chave-proposta"
    assert final[tk.KEY_REGISTRO]["itens"][0]["id"] == "TC-01"


def test_agente_de_produto_grava_registro_e_tabela_e_a_correcao_pontual_mantem_o_id():
    from agents.checkers import TextosChaveAgent

    estado = _estado()
    base = {k: estado[k] for k in ("one_pager", "briefing")}
    final = asyncio.run(_rodar(TextosChaveAgent(name="A044bTextosChave"), base))
    registro = final[tk.KEY_REGISTRO]
    assert final[tk.KEY_TABELA].startswith(f"## {tk.TITULO_TABELA}")
    alt = next(d for d in registro["itens"] if d["texto"].startswith("Valeu, turma! Até a próxima aventura"))
    editado = {**final, "one_pager": final["one_pager"].replace("Valeu, turma! Até a próxima aventura fotográfica!",
                                                                "Valeu, turma! Até a próxima aventura!")}
    final2 = asyncio.run(_rodar(TextosChaveAgent(name="A044bTextosChave"), editado))
    assert next(d for d in final2[tk.KEY_REGISTRO]["itens"] if d["texto"] == "Valeu, turma! Até a próxima aventura!")["id"] == alt["id"]
    assert not [d for d in final2[tk.KEY_REGISTRO]["itens"] if d["tipo"] == tk.CANAL_B]


def test_callback_copia_na_passada_1_e_na_citacao_do_prd():
    from agents.callbacks import copiar_textos_chave
    from tools.conteudo_aprovado import TITULO_ANEXO

    estado = _estado()
    tcs = tk.da_sessao(estado)
    pergunta = _por_texto(tcs, FALA)
    estado["copy_strings"] = _copy_de_teste().replace(FALA + " | 9 |", "Pronto | 1 |")
    copiar_textos_chave("copy_strings")(SimpleNamespace(state=estado))
    assert f"| {pergunta.texto} | 9 |" in estado["copy_strings"]
    quase = pergunta.texto.replace("Aqui é a Clara", "Aqui quem fala é a Clara")
    assert tk.semelhanca(pergunta.texto, quase) >= tk.CORTE_DOCUMENTO
    # a redação distante que ninguém registrou fica para o gate (a registrada como proposta volta ao aprovado sem a
    # régua — teste da segunda revisão, abaixo)
    longe = "Olá, crianças! Quem está falando com vocês é a Clara."
    estado["prd_final"] = (f"# PRD\n\nA pergunta: \"{quase}\"\n\nNo corpo antigo: \"{longe}\"\n\n---\n\n# {TITULO_ANEXO}\n\n"
                           f"Anexo com \"{quase}\" literal do jeito que veio.\n")
    copiar_textos_chave("prd_final")(SimpleNamespace(state=estado))
    corpo, anexo = estado["prd_final"].split(f"# {TITULO_ANEXO}")
    assert f"\"{pergunta.texto}\"" in corpo and longe in corpo  # a quase igual volta; a distante fica para o gate
    assert quase in anexo  # o anexo literal é da esteira: não é tocado


def test_conteudo_aprovado_e_anexo_levam_a_tabela():
    from agents.checkers import AnexoAprovadoAgent, ConteudoAprovadoAgent
    from tools.conteudo_aprovado import SECOES_DESIGN, SECOES_PRD

    estado = _estado()
    base = {k: estado[k] for k in ("one_pager", "briefing")}
    final = asyncio.run(_rodar(ConteudoAprovadoAgent(name="A064", secoes=list(SECOES_DESIGN)), base))
    assert tk.TITULO_TABELA in final["conteudo_aprovado"] and final[tk.KEY_TABELA]
    base["prd_final"] = "# PRD\n\nCorpo.\n"
    final = asyncio.run(_rodar(AnexoAprovadoAgent(name="A119", chave="prd_final", secoes=list(SECOES_PRD)), base))
    assert final["prd_final"].index(tk.TITULO_TABELA) > final["prd_final"].index("Anexo — conteúdo aprovado")


# --------------------------------------------------------------------------- teto de palavras: lint e de acordo
def test_teto_do_15_vale_o_maior_e_sem_ele_vale_a_faixa_rascunho():
    assert tk.teto_de_palavras(_estado("exp06ef1b-53e011b6")["one_pager"])["valor"] == 60  # legendas 60, cartões 25, balões 35
    sem = tk.teto_de_palavras(_estado()["one_pager"])  # o §15 da exp02ef1b é [PARÂMETRO … sugestão: 15]
    assert (sem["valor"], sem["por"], sem["faixa"]) == (10, "frase", "1-2") and "rascunho" in sem["origem"]
    assert tk.teto_de_palavras(_estado("exp01ef1b")["one_pager"])["por"] == "frase"  # «0 palavras de leitura autônoma»
    tetos, status = tk.tetos_por_faixa()
    assert tetos == {"1-2": 10, "3-5": 15, "6-9": 20, "EM": 20} and status.startswith("rascunho")
    # o teto da faixa (calibragem da copy) é por frase; o do §15, pelo texto inteiro
    duas = "Uma frase curta de seis palavras. Outra frase curta de seis palavras."
    assert tk.contar_para_o_teto(duas, {"por": "frase"}) == 6 and tk.contar_para_o_teto(duas, {"por": "texto"}) == 12
    assert not tk.acima_do_teto([tk.TextoChave(id="TC-01", tipo=tk.TELA, origem="§4", texto=duas)],
                                {"valor": 10, "por": "frase"})


def test_lint_acusa_texto_chave_acima_do_teto_sem_bloquear():
    from tools.contrato_produto import validar_one_pager

    estado = _estado("exp06ef1b-53e011b6")
    r = validar_one_pager(estado["one_pager"], nucleo=estado.get("nucleo_narrativo", ""), briefing=estado.get("briefing", ""))
    achado = next(a for a in r["achados"] if a["codigo"] == "texto-chave-acima-do-teto")
    assert achado["severidade"] == "atencao" and "Na eleição para o Grêmio" in achado["resumo"] and "(81)" in achado["resumo"]


def test_texto_acima_do_teto_vira_item_do_de_acordo_e_a_decisao_grava():
    estado = _estado("exp06ef1b-53e011b6")
    item = next(i for i in fc.itens_em_aberto(estado) if i.tipo == fc.TEXTO_TETO)
    assert item.opcoes() == [fc.ACEITAR, fc.OUTRO] and item.sugestao == "manter o texto aprovado"
    assert item.assunto.startswith("TC-") and "81 palavras, teto de 60 por texto" in item.assunto
    # outro texto: entra no one-pager no lugar do texto-chave, e o lint e o cartão não o acusam de novo
    novo = "Mariana só viu vídeos da Chapa A no feed. Como você explicaria o que aconteceu?"
    d = fc.decidir([item], {item.id: {"resposta": fc.OUTRO, "valor": novo}}, "24/10/2026 10:00:00", "produto")
    novos, falhas = fc.aplicar_edicoes(estado, d.edicoes)
    assert not falhas and novo in novos["one_pager"] and item.texto_chave not in novos["one_pager"]
    assert d.decisoes[0]["texto"] == novo and d.decisoes[0]["gravado"] == novo
    gravado = {**estado, **novos, fc.KEY_DECISOES: d.decisoes}
    assert not [i for i in fc.itens_em_aberto(gravado) if i.tipo == fc.TEXTO_TETO]
    # manter: nada muda no texto, e a decisão tira o item do cartão
    d2 = fc.decidir([item], {item.id: {"resposta": fc.ACEITAR}}, "24/10/2026 10:00:00", "produto")
    assert not d2.edicoes and d2.decisoes[0]["texto"] == item.texto_chave
    mantido = {**estado, fc.KEY_DECISOES: d2.decisoes}
    assert not [i for i in fc.itens_em_aberto(mantido) if i.tipo == fc.TEXTO_TETO]
    assert not fc.decisoes_perdidas(mantido, fc.itens_em_aberto(mantido))


def test_de_acordo_escrito_a_mao_nao_responde_texto_chave_pelo_assunto():
    """«teto de palavras por parágrafo → 45 palavras» (exp02em1b, 21/10) não é resposta a um texto-chave acima do teto:
    sem isto, o Canal B virava «45 palavras»."""
    estado = _estado("exp02em1b-60cfa7f4")
    itens = fc.itens_em_aberto(estado)
    fluxo = {"pareceres": [{"etapa": "produto", "acao": "de_acordo", "quando": "21/10/2026 15:43:51",
                            "comentario": "[PARÂMETRO: a definir por produto: teto de palavras por parágrafo, "
                                          "sugestão: 45 palavras] → 45 palavras"}]}
    anteriores = fc.respostas_anteriores(estado, fluxo, itens)
    assert not [i for i in itens if i.tipo == fc.TEXTO_TETO and i.id in anteriores]
    # e a decisão sobre um texto-chave não responde o [PARÂMETRO] do teto de palavras, que tem assunto parecido
    teto = next(i for i in itens if i.tipo == fc.TEXTO_TETO)
    gravado = {**estado, fc.KEY_DECISOES: [{"id": teto.id, "tipo": fc.TEXTO_TETO, "resposta": fc.OUTRO,
                                            "valor": "45 palavras", "assunto": "teto de palavras por parágrafo",
                                            "texto": "45 palavras", "quando": "24/10/2026 10:00:00"}]}
    marcadores = [i for i in fc.itens_em_aberto(gravado) if i.tipo != fc.TEXTO_TETO]
    respondidos = fc.respostas_anteriores(gravado, {}, marcadores)
    assert not [i for i in marcadores if "teto de palavras" in i.assunto and i.id in respondidos]


# --------------------------------------------------------------------------- triagem: o ID leva o item a produto
def test_item_que_cita_o_id_do_texto_chave_vai_a_produto():
    from tools.triagem_pedido import regra_de_produto

    motivos = regra_de_produto("Aceito a proposta TC-03.1 do design para a alternativa.", {})
    assert any("TC-03.1" in m for m in motivos)


# --------------------------------------------------------------------------- arestas do fluxo × bloco 2
def test_arestas_da_exp02ef1b_que_mudam_o_que_o_aluno_faz_vao_ao_po():
    estado = _estado()
    r = ar.validar(estado)
    assert r["status"] == "amarelo"
    por_aresta = {a.get("aresta"): a for a in r["achados"]}
    assert por_aresta["A13"]["codigo"] == "guarda-afrouxada"
    assert por_aresta["A20"]["codigo"] == "guarda-exige-acerto" and "«Criança lendo»" in por_aresta["A20"]["resumo"]
    assert por_aresta["A22"]["codigo"] == "guarda-exige-acerto"
    assert all(a["severidade"] == "decisao_humana" and a["agente_responsavel"] == "PO"
               and a["resumo"].startswith("[PROPOSTA — validar com PO:") for a in r["achados"])
    # o comentário entre parênteses não é guarda: «(cobre pareamento correto e exploração mínima)» da A17
    assert "A17" not in por_aresta
    # C7 (25/10/2026): a guarda lida por regex é interpretação — com ESTEIRA_ESTRITA continua decisão do PO, não 🔴
    estrito = ar.validar(estado, estrito=True)
    assert estrito["status"] == "amarelo" and all(a["severidade"] == "decisao_humana" for a in estrito["achados"])


@pytest.mark.parametrize("missao", sorted(p.name for p in ACERVO.iterdir() if (p / "estado.json").exists()
                                          and p.name != "exp02ef1b-4fd72a9a"))
def test_arestas_sem_falso_positivo_no_resto_do_acervo(missao):
    """Calibração: decompor estado é livre (D7) — as outras 14 missões não têm guarda mudada."""
    assert ar.validar(_estado(missao))["achados"] == []


def test_decomposicao_nao_e_achado_e_guarda_que_trava_na_resposta_certa_e():
    estado = _estado()
    fluxo = estado["fluxo_arestas"]
    sem_a20 = fluxo.replace('com atributo essencial selecionado ("Criança lendo") e moldura ajustada',
                            "com atributo essencial selecionado e moldura ajustada")
    decomposto = sem_a20.replace(
        "| A21 |", "| A20b | `E5-ALU-02` | `E5-ALU-02b` | Toque em `Colocar no álbum` abre a confirmação do recorte | "
                   "principal | Não | estudante |\n| A21 |")
    r = ar.validar({**estado, "fluxo_arestas": decomposto})
    assert "A20" not in {a.get("aresta") for a in r["achados"]} and "A20b" not in {a.get("aresta") for a in r["achados"]}
    # a regra de habilitação da tela que trava na resposta certa também vai ao PO
    telas = estado["wireframes_cobertura"] + ("\n### `E5-ALU-02` — Segunda foto\n- *Rodapé:* botão `Colocar no álbum` "
                                              "habilitado apenas após selecionar o atributo correto.\n")
    r = ar.validar({**estado, "fluxo_arestas": sem_a20, "wireframes_cobertura": telas})
    assert any(a["codigo"] == "guarda-exige-acerto" and "cobertura das telas" in a["resumo"] for a in r["achados"])


# --------------------------------------------------------------------------- E0-PROF como padrão da plataforma
PREPARO = "references/padrao-plataforma-preparo-professor.md"
#: O bloco de cada agente e um trecho que só ele traz: o prompt inclui a definição comum e só o próprio bloco (revisão de
#: 24/10/2026 — com a referência inteira, a jornada recebia a ordem de desenhar o grafo do professor e as regras do QA).
BLOCOS_DO_PREPARO = {
    "jornada": "Tabela própria, **colunas** = os passos do preparo no hub mais a aula",
    "fluxo": "sob o título fixo `## Fluxo do professor (Mermaid — obrigatório)`",
    "telas": "**Estados a gerar** (Stitch): padrão · gerando · sem saldo · pacote pronto.",
    "prototipo": "`E0-PROF-01…05` navegáveis (escolher a missão → recorte da aula → geração em andamento",
    "qa": "tela do professor ausente do Stitch é ⛔ com dono `telas`",
}


@pytest.mark.parametrize("prompt, bloco, exigencias", [
    ("design/071_jornada.md", "jornada", ["`E0-PROF-01` **Escolher a missão no catálogo.**", "Unooria Hub (kit configuração)",
                                          "Escolher a missão → Recorte da aula (disciplina · tema · assuntos · contexto)",
                                          "As telas de condução", "a mesma missão em três aulas"]),
    ("design/072_fluxo.md", "fluxo", ["## Fluxo do professor (Mermaid — obrigatório)",
                                      "`E0-PROF-02 -->|usar banco padrão| E0-PROF-05`", "`atividade ativada → E1-ALU-01`",
                                      "O módulo `/atividades` é o motor do Instanooria e não se reusa"]),
    ("design/075_telas.md", "telas", ["**construída nos dois estados**", "padrão · gerando · sem saldo · pacote pronto",
                                      "uma disciplina diferente do banco default"]),
    ("design/079_prototipo.md", "prototipo", ["**O trilho do professor é obrigatório e começa antes da aula:**",
                                              "a transição «atividade ativada» levando à primeira tela do estudante"]),
    ("design/088_qa_entregaveis.md", "qa", ["tela do professor ausente do Stitch é ⛔ com dono `telas`",
                                            "caminho curto** `E0-PROF-01 → 02 → 05`", "Teste das três disciplinas",
                                            "Simulação de preparo em minutos"]),
])
def test_preparo_do_professor_saiu_do_prompt_e_o_prompt_ainda_pede_o_mesmo(prompt, bloco, exigencias):
    """D7: o fluxo fixo E0-PROF-01…05 vira padrão da plataforma em references/, e cada prompt de design o cita — o
    texto expandido traz as mesmas exigências que o prompt trazia, e só elas: a definição das cinco telas e o bloco do
    próprio agente, nenhum dos outros quatro (o 071 não pede o grafo do professor; o 072 não pede a conferência do QA)."""
    from prompts import get_prompt_raw, load_prompt

    bruto = get_prompt_raw(prompt)
    proprio = PREPARO.replace(".md", f"-{bloco}.md")
    assert f"<!-- include: {PREPARO} -->" in bruto and f"<!-- include: {proprio} -->" in bruto
    assert "`E0-PROF-03` Geração em andamento (progresso por polling" not in bruto  # a descrição mora na referência
    expandido = load_prompt(prompt, stitch_mcp_mode="x", stitch_project_url_base="x", qa_max_rodadas=2)
    for e in exigencias:
        assert e in expandido, (prompt, e)
    assert BLOCOS_DO_PREPARO[bloco] in expandido
    for outro, trecho in BLOCOS_DO_PREPARO.items():
        if outro != bloco:
            assert trecho not in expandido, (prompt, outro)
            assert f"preparo-professor-{outro}.md -->" not in bruto


def test_nenhum_prompt_inclui_bloco_do_preparo_de_outro_agente():
    """A definição comum não traz instrução de agente nenhum, e cada bloco é incluído só pelo prompt dele."""
    from prompts import get_prompt_raw
    from prompts.loader import PROMPTS_DIR

    comum = get_prompt_raw(PREPARO)
    for trecho in BLOCOS_DO_PREPARO.values():
        assert trecho not in comum
    donos = {"jornada": "071_jornada.md", "fluxo": "072_fluxo.md", "telas": "075_telas.md",
             "prototipo": "079_prototipo.md", "qa": "088_qa_entregaveis.md"}
    for md in PROMPTS_DIR.rglob("*.md"):
        texto = md.read_text(encoding="utf-8")
        for bloco, dono in donos.items():
            if f"include: references/padrao-plataforma-preparo-professor-{bloco}.md" in texto:
                assert md.name == dono, (md.name, bloco)


# --------------------------------------------------------------------------- a esteira
def test_agentes_novos_estao_no_lugar():
    from agents.design import MAPA_RETRABALHO, POSFIXO_RETRABALHO, build_design_stage
    from agents.produto import build_produto_stage

    nomes = [a.name for a in build_produto_stage().sub_agents]
    assert nomes.index("A044bTextosChave") == nomes.index("A044GateFinalProdutoCheck") + 1
    assert nomes.index("SpecLoop") > nomes.index("A044bTextosChave")
    design = [a.name for a in build_design_stage().sub_agents]
    assert design.index("A078bTextosChave") == design.index("A078CopyPreservada") + 1
    assert design.index("A079Prototipo") > design.index("A078bTextosChave")
    assert design.index("A083bArestasContrato") == design.index("A083CoberturaTelas") + 1
    assert MAPA_RETRABALHO["copy-ptbr-revisao"][-1] == "A078bTextosChaveRetrabalho"
    assert "A083bArestasContratoRetrabalho" in POSFIXO_RETRABALHO


def test_registro_sobrevive_ao_refazer_e_a_tabela_e_refeita():
    from pipeline.reexecucao import CHAVES_DESIGN, CHAVES_PRODUTO, preparar_estado

    assert tk.KEY_REGISTRO not in CHAVES_PRODUTO and tk.KEY_TABELA in CHAVES_PRODUTO
    assert {"textos_chave_status", "arestas_status"} <= CHAVES_DESIGN
    estado = _estado()
    _, registro = tk.atualizar(estado)
    limpo, _ = preparar_estado({**estado, tk.KEY_REGISTRO: registro, tk.KEY_TABELA: "x"}, "produto", "pedido")
    assert limpo[tk.KEY_REGISTRO] == registro and tk.KEY_TABELA not in limpo


def test_gate_do_handoff_ve_o_texto_de_tela_reescrito_pelo_design():
    """exp06ef1b-53e011b6: o handoff cita duas vezes o texto de tela do §4 «Jurado, a plenária aguarda seu voto para
    prosseguir.» (`TC-06`). Com outra redação no lugar, o gate de montagem a vê pelos textos-chave e bloqueia. (Antes de
    29/10/2026 o exemplo era a pergunta do Canal B da exp02ef1b, que saiu da esteira.)"""
    from tools import montagem

    estado = _estado("exp06ef1b-53e011b6")
    aprovado = tk.por_id(tk.da_sessao(estado))["TC-06"].texto
    assert aprovado == "Jurado, a plenária aguarda seu voto para prosseguir." and estado["handoff_dev"].count(aprovado) == 2
    assert not [a for a in montagem.validar_handoff(estado)["achados"] if a["codigo"] == "texto-chave-reescrito"]
    reescrito = estado["handoff_dev"].replace(aprovado, "Jurado, a plenária espera o seu voto para seguir.")
    r = montagem.validar_handoff({**estado, "handoff_dev": reescrito})
    achado = next(a for a in r["achados"] if a["codigo"] == "texto-chave-reescrito")
    assert "Jurado, a plenária espera o seu voto" in achado["resumo"] and achado["severidade"] == "bloqueio"


def test_cartao_de_produto_mostra_a_tabela_dos_textos_chave():
    pytest.importorskip("streamlit.testing.v1")
    from streamlit.testing.v1 import AppTest

    def roteiro():
        import json
        from pathlib import Path

        import app
        estado = json.loads(Path("tests/acervo/exp02ef1b-4fd72a9a/estado.json").read_text(encoding="utf-8"))
        app._render_textos_chave(estado)

    at = AppTest.from_function(roteiro, default_timeout=60)
    at.run()
    assert not at.exception
    # 19 com ID desde 29/10/2026: a escolha da 5A e as 18 falas do podcast (a pergunta e as alternativas do Canal B saíram)
    assert at.expander[0].label.startswith("🔑 Textos-chave aprovados — 19 com ID")
    assert any("TC-01" in m.value for m in at.markdown)


def test_outro_texto_do_po_entra_tambem_na_spec_que_copia_o_texto_chave():
    """O texto da Etapa 4 da exp02em1b (`TC-10`, acima do teto) está no one-pager e na spec do Gate 0: o texto que o PO
    escreve no de acordo entra nos dois — trocado só no one-pager, a spec ficava com o texto velho. (O exemplo era o
    Canal B da exp02ef1b, que saiu da esteira em 29/10/2026.)"""
    estado = _estado("exp02em1b-60cfa7f4")
    item = next(i for i in fc.itens_em_aberto(estado) if i.tipo == fc.TEXTO_TETO and i.assunto.startswith("TC-10 "))
    assert {o.documento for o in item.ocorrencias} == {fc.DOC_ONE_PAGER, fc.DOC_SPEC}
    novo = "Você modera o perfil do grêmio. O post viralizou: o que fazer?"
    d = fc.decidir([item], {item.id: {"resposta": fc.OUTRO, "valor": novo}}, "24/10/2026 10:00:00", "produto")
    novos, falhas = fc.aplicar_edicoes(estado, d.edicoes)
    assert not falhas and set(novos) == {"one_pager", "spec_missao_gate0", "spec_missao"}
    assert all(novo in texto and item.texto_chave not in texto for texto in novos.values())


def test_proposta_decidida_pelo_po_sai_da_secao_da_esteira():
    """Cascata do PR 5: o PO aceita no Refazer a redação que o design propôs (ou escreve outra), o editor de produto a põe
    no one-pager e o texto-chave muda — a proposta antiga sai da seção da esteira em vez de ficar no cartão para sempre."""
    estado = _estado()
    tcs = tk.da_sessao(estado)
    pergunta = _por_texto(tcs, FALA)
    com_proposta = tk.aplicar_na_copy(_copy_de_teste().replace(FALA + " | 9 |", "Pronto | 1 |"), tcs)["texto"]
    novo = "Olá, turma do segundo ano! Quem fala é a Clara!"
    _, registro = tk.atualizar(estado)
    trocado = {**estado, "one_pager": estado["one_pager"].replace(pergunta.texto, novo), tk.KEY_REGISTRO: registro}
    tcs2 = tk.da_sessao(trocado)
    assert _por_texto(tcs2, novo).id == pergunta.id
    depois = tk.aplicar_na_copy(com_proposta, tcs2)
    assert f"| {novo} |" in depois["texto"]  # o texto novo desce por código para a linha que cita o ID
    assert not any(p == "Pronto" for _, _, p in depois["propostas"])
    # e a redação aprovada antes, que estava na linha, não vira proposta do design: ela só desce
    assert not [p for p in depois["propostas"] if p[2] == FALA]


def test_cascata_em_sessao_sem_registro_leva_o_texto_novo_a_linha_da_copy():
    """As quatro missões refeitas depois do PR 7 não têm registro: na correção pontual de produto, os IDs saem do
    one-pager de antes do pedido (`versao_anterior_one_pager`). O texto que o PO trocou guarda o ID e a redação velha, e
    a linha da copy que ainda a traz — sem citar o ID — recebe a nova por código, sem proposta."""
    estado = _estado()
    pergunta = _por_texto(tk.da_sessao(estado), FALA)
    novo = "Olá, crianças da turma do segundo ano! Quem está falando com vocês é a Clara!"
    corrigido = {**estado, "versao_anterior_one_pager": estado["one_pager"],
                 "one_pager": estado["one_pager"].replace(pergunta.texto, novo)}
    tcs, registro = tk.atualizar(corrigido)
    nova = _por_texto(tcs, novo)
    assert nova.id == pergunta.id and nova.texto == novo and nova.antes == [pergunta.texto]
    assert registro["itens"][[d["id"] for d in registro["itens"]].index(nova.id)]["antes"] == [pergunta.texto]
    copia = _copy_de_teste().replace("| `TC-02` |", "| — |")
    aplicado = tk.aplicar_na_copy(copia, tcs)
    assert f"| {novo} |" in aplicado["texto"] and f"`{nova.id}`" in aplicado["texto"]
    assert not aplicado["propostas"]


# --------------------------------------------------------------------------- revisão do PR #74 (24/10/2026)
def test_outro_numero_e_outro_texto_na_copy_real_da_exp03em1b():
    """A cota «Publicações Oficiais Disponíveis: 1/3» da E4-ALU-04 está certa (a jornada diz «cota 1/3»): para a
    semelhança ela era reescrita do TC-09 «Publicações Disponíveis: 2/3» (o contador depois da 1ª publicação, outra
    tela), virava 2/3 e gerava proposta falsa ao PO. Com outro número, é outro texto: a linha fica e o TC-09 fica sem
    linha. A mesma sequência de números dos dois lados («Origem 0» × «Origem 0%») continua reescrita."""
    estado = _estado("exp03em1b-b2e7b4a3")
    tcs = tk.da_sessao(estado)
    tc09 = tk.por_id(tcs)["TC-09"]
    assert tc09.texto == "Publicações Disponíveis: 2/3"
    original = next(l for l in estado["copy_strings_revisada"].splitlines() if "e4.feed.cota_atualizada" in l)
    aplicado = tk.aplicar_na_copy(estado["copy_strings_revisada"], tcs)
    assert next(l for l in aplicado["texto"].splitlines() if "e4.feed.cota_atualizada" in l) == original
    assert "Publicações Oficiais Disponíveis: 1/3" in original
    assert not [p for p in aplicado["propostas"] if p[0] == "TC-09"]
    assert "TC-09" in {t.id for t in aplicado["sem_linha"]}
    assert ("TC-06.1", "Escala Absoluta (Origem 0)", "Escala Absoluta (Origem 0%)") in aplicado["propostas_novas"]
    # o texto-chave com lacuna aceita o número que a copy põe nela (`X%` → `68%`, exp01em1b-76d9af6e)
    lacuna = tk.TextoChave(id="TC-11", tipo=tk.TELA, origem="§4", texto="Na sua turma: X% apostou no cumprimento")
    assert tk.mesmos_numeros(lacuna, "Na sua turma: 68% apostou no cumprimento")
    assert tk.mesmos_numeros(tk.TextoChave(id="TC-02", tipo=tk.TELA, origem="§4", texto="Você tem R$ 12.000."),
                             "Você tem R$ 12000 agora.")
    assert not tk.mesmos_numeros(tc09, "Publicações Oficiais Disponíveis: 1/3")


def test_citacao_com_outro_numero_no_prd_nao_vira_o_texto_chave():
    """No PRD, «o contador mostra “Publicações Oficiais Disponíveis: 1/3” depois da errata» casava com o TC-03 «…: 3/3»
    (semelhança ≥ 0,85) e saía «3/3»."""
    tcs = tk.da_sessao(_estado("exp03em1b-b2e7b4a3"))
    prd = "# PRD\n\nNa E4, o contador mostra “Publicações Oficiais Disponíveis: 1/3” depois da errata.\n"
    assert tk.aplicar_em_documento(prd, tcs) == (prd, [])
    # e a citação quase igual, com os mesmos números, continua voltando ao texto aprovado
    quase = "# PRD\n\nO topo mostra “Publicacoes Oficiais Disponiveis: 3/3” na abertura.\n"
    novo, trocas = tk.aplicar_em_documento(quase, tcs)
    assert trocas and trocas[0][0] == "TC-03" and "“Publicações Oficiais Disponíveis: 3/3”" in novo


def test_linha_da_19_3_com_as_propostas_do_design_fica_como_esta():
    """O item 13 do prompt 113 manda listar na 19.3 o texto literal de cada [PROPOSTA] aberta. O callback trocava o lado
    proposto pelo aprovado (≥ 0,85) e a linha ficava «aprovado» → «aprovado»: a redação do design sumia do documento
    que o dev e o PO leem (exp02ef1b TC-01.1 e TC-01.2; até 29/10/2026 também as alternativas do Canal B)."""
    from agents.callbacks import copiar_textos_chave

    estado = _estado()
    tcs = tk.da_sessao(estado)
    propostas = [l[2:] for l in tk.aplicar_na_copy(estado["copy_strings_revisada"], tcs)["texto"].splitlines()
                 if l.startswith("- [PROPOSTA")]
    assert len(propostas) == 2 and all("Cor da roupa" in p or "Atividade" in p for p in propostas)
    tabela = ("## 19.3 Decisões do agente a revisar\n\n| Marcador | Origem |\n|---|---|\n"
              + "".join(f"| {p} | copy revisada |\n" for p in propostas))
    prd = f"# PRD\n\n{tabela}\nNo fim o podcast diz «Valeu, turma! Até a próxima aventura fotográfica, pessoal!» e acaba.\n"
    novo, trocas = tk.aplicar_em_documento(prd, tcs)
    assert novo.startswith(f"# PRD\n\n{tabela}")  # a 19.3 intacta
    # a citação solta depois dela é que volta ao texto aprovado — na posição dela, não na da proposta acima
    assert [t[0] for t in trocas] == ["TC-19"]
    assert "No fim o podcast diz «Valeu, turma! Até a próxima aventura fotográfica!» e acaba." in novo
    # a linha que compara o aprovado com outra redação, sem o marcador, também é comparação, não citação a corrigir
    comparacao = "# PRD\n\n| TC-01.2 | «Cor da roupa» | «A cor da roupa» |\n"
    assert tk.aplicar_em_documento(comparacao, tcs) == (comparacao, [])
    # e a proposta que não repete o texto aprovado continua sendo proposta
    so_proposta = "# PRD\n\n- [PROPOSTA — validar com PO: TC-01.2 · trocar por «A cor da roupa» · artigo para a leitura em voz]\n"
    assert tk.aplicar_em_documento(so_proposta, tcs) == (so_proposta, [])
    estado["prd_final"] = prd
    copiar_textos_chave("prd_final")(SimpleNamespace(state=estado))
    assert tabela in estado["prd_final"]


def _estado_pontual(missao: str) -> Dict[str, Any]:
    estado = _estado(missao)
    base = {k: estado[k] for k in ("one_pager", "briefing", "spec_missao")}
    base.update({"copy_strings_revisada": estado["copy_strings_revisada"], "modo_correcao": "pontual",
                 "versao_anterior_copy_strings_revisada": estado["copy_strings_revisada"],
                 "edicoes_pontuais": [{"documento": "one_pager", "de": "x", "para": "y", "motivo": "pedido"}]})
    return base


@pytest.mark.parametrize("missao", ["exp03em1b-b2e7b4a3", "exp02em1b-60cfa7f4", "exp02ef1b-4fd72a9a"])
def test_correcao_pontual_nao_anota_linha_sem_troca_e_registra_o_que_copiou(missao):
    """Na correção pontual a copy é a versão anterior mais as trocas, e é isso que prova as ordens de não mexer. O A078b
    anotava `TC-nn` em toda linha que já trazia o texto (de 14 a 64 por missão) e a prova caía: agora só a linha cujo
    texto mudou ganha o ID, e o que o código copiou entra em `edicoes_pontuais` — `reaplicar` volta a provar."""
    from agents.checkers import TextosChaveCopyAgent
    from tools import edicao_pontual

    base = _estado_pontual(missao)
    anterior = base["copy_strings_revisada"]
    final = asyncio.run(_rodar(TextosChaveCopyAgent(name="A078bTextosChave"), base))
    copia = final["copy_strings_revisada"]
    mudadas = [(a, b) for a, b in zip(anterior.splitlines(), copia.splitlines()) if a != b]
    # toda linha mudada trocou texto (não só ganhou o ID na nota)
    assert all(re.sub(r"\s*`TC-\d+(?:\.\d+)?`", "", b) != a for a, b in mudadas)
    fora = tk.aplicar_na_copy(anterior, tk.da_sessao(base))["texto"]
    n_fora = sum(1 for a, b in zip(anterior.splitlines(), fora.splitlines()) if a != b)
    if missao == "exp02ef1b-4fd72a9a":
        # sem o Canal B (29/10/2026), os textos-chave da exp02ef1b na copy são só as opções da 5A, e as duas linhas que o
        # código toca trocam texto: fora da pontual nenhuma linha ganha só a nota, e as contagens empatam
        assert len(mudadas) == n_fora == 2
    else:
        assert len(mudadas) < n_fora
    trocas = final["edicoes_pontuais"][1:]
    assert final["edicoes_pontuais"][0]["motivo"] == "pedido"
    assert trocas and all(e["motivo"] == tk.MOTIVO_TROCA_DA_COPY for e in trocas)
    assert edicao_pontual.reaplicar(anterior, copia, "copy_strings_revisada", final["edicoes_pontuais"])
    # fora da correção pontual, nada vai para `edicoes_pontuais`
    geral = {k: v for k, v in base.items() if k not in ("modo_correcao", "edicoes_pontuais")}
    final2 = asyncio.run(_rodar(TextosChaveCopyAgent(name="A078bTextosChave"), geral))
    assert "edicoes_pontuais" not in final2


def test_trocas_por_linhas_reproduzem_o_documento():
    from tools import edicao_pontual as ep

    assert ep.trocas_por_linhas("d", "a\nb", "a\nb") == []
    # a linha que se repete leva contexto até ser única
    trocas = ep.trocas_por_linhas("d", "a\nb\na\nb\n", "a\nb\na\nc\n", "m")
    assert ep.aplicar({"d": "a\nb\na\nb\n"}, trocas).documentos["d"] == "a\nb\na\nc\n"
    assert all(e.motivo == "m" for e in trocas)
    # acréscimo no fim (a seção da esteira)
    assert ep.aplicar({"d": "x\ny"}, ep.trocas_por_linhas("d", "x\ny", "x\ny\n\n## Seção\n")).documentos["d"] == "x\ny\n\n## Seção\n"


def test_proposta_do_design_nos_dois_formatos_chega_ao_gate():
    """Os prompts 073 e 077 pediam `[PROPOSTA — validar com PO: «aprovado» → «novo» · TC-07 · por quê]`, e o leitor só
    casava `PO: TC-07 «…» → «…»`: a proposta que o design escrevia em «Strings que precisam de decisão» não chegava ao
    🧑 do gate. Os dois formatos são lidos, a linha da proposta não é tratada como string de tela, e o formato que os
    prompts pedem agora (o ID primeiro) é o da esteira."""
    from prompts import get_prompt_raw

    tcs = tk.da_sessao(_estado())
    pergunta = _por_texto(tcs, FALA)
    atividade = next(t for t in tcs if t.tipo == tk.OPCAO and t.texto == "Atividade")
    decisao = ("\n## Strings que precisam de decisão\n\n"
               f"- [PROPOSTA — validar com PO: «{pergunta.texto}» → «Olá, turma! Aqui é a Clara!» · {pergunta.id} · "
               "a fala fica mais curta]\n"
               f"- [PROPOSTA — validar com PO: {atividade.id} «Atividade» → «A atividade» · artigo para a leitura em voz]\n")
    copia = _copy_de_teste() + decisao
    assert tk.propostas_registradas(copia) == [
        (pergunta.id, pergunta.texto, "Olá, turma! Aqui é a Clara!"), (atividade.id, "Atividade", "A atividade")]
    aplicado = tk.aplicar_na_copy(copia, tcs)
    assert decisao.strip() in aplicado["texto"]  # a seção do design não é tocada
    r = tk.conferir_copy(aplicado["texto"], tcs)
    achado = next(a for a in r["achados"] if a["codigo"] == "texto-chave-proposta")
    assert "Olá, turma! Aqui é a Clara!" in achado["resumo"] and "A atividade" in achado["resumo"]
    assert not [a for a in r["achados"] if a["severidade"] == "bloqueio"]
    # idempotente: a proposta copiada para a seção da esteira não se duplica
    de_novo = tk.aplicar_na_copy(aplicado["texto"], tcs)
    assert de_novo["texto"] == aplicado["texto"] and len(de_novo["propostas"]) == 2
    # a proposta com aspas duplas, para um texto-chave sem linha, também não é string a corrigir
    fala = next(t for t in tcs if t.tipo == tk.PODCAST and "aventura fotográfica" in t.texto)
    reescrita = fala.texto.replace("aventura fotográfica", "aventura de fotos")
    so_proposta = _copy_de_teste() + f"\n- [PROPOSTA — validar com PO: {fala.id} → \"{reescrita}\" · ritmo da fala]\n"
    aplicado = tk.aplicar_na_copy(so_proposta, tcs)
    assert f"\"{reescrita}\"" in aplicado["texto"] and fala.id in {t.id for t in aplicado["sem_linha"]}
    # o exemplo de cada prompt de copy é lido pelo código
    for prompt in ("design/073_copy_ptbr.md", "design/077_copy_revisao.md"):
        exemplo = re.search(r"`(\[PROPOSTA — validar com PO: TC-07[^`]*\])`", get_prompt_raw(prompt)).group(1)
        assert tk.propostas_registradas(exemplo) == [("TC-07", "texto aprovado", "texto novo")], prompt


def test_teto_na_faixa_e_o_limite_de_cima():
    """«máximo de 8 a 10 palavras» (exp03ef1b) é teto 10, e «40 a 50 palavras» (exp07ef1b) é 50 — o limite de baixo
    acusava texto demais no de acordo."""
    def s15(linha: str) -> str:
        return f"## 15. Restrições\n\n{linha}\n"

    assert tk.teto_do_one_pager(s15("* Manchetes: frases curtas (máximo de 8 a 10 palavras)."))[0] == 10
    assert tk.teto_do_one_pager(s15("* Legendas: Máximo de 40 a 50 palavras por publicação."))[0] == 50
    assert tk.teto_do_one_pager(s15("* Balões: até 18 palavras."))[0] == 18
    # no acervo, o maior teto de cada missão vem de outra linha: nada muda
    assert tk.teto_do_one_pager(_estado("exp03ef1b")["one_pager"])[0] == 18
    assert tk.teto_do_one_pager(_estado("exp07ef1b")["one_pager"])[0] == 65


@pytest.mark.parametrize("prompt", ["produto/026_gate_estrutural.md", "produto/revisor_one_pager.md"])
def test_gate_e_revisor_nao_encurtam_o_texto_chave_acima_do_teto(prompt):
    """O 026 manda pôr cada ⚠️ do lint no complemento, e o revisor aplica o que faltar: o texto-chave acima do teto é a
    exceção — vai ao de acordo, e o PO mantém ou troca."""
    from prompts import get_prompt_raw

    bruto = get_prompt_raw(prompt)
    trecho = bruto[bruto.index("`texto-chave-acima-do-teto`"):][:260]
    assert "não entra no complemento nem é reescrito" in trecho and "de acordo" in trecho and "PO mantém ou troca" in trecho


# --------------------------------------------------------------------------- segunda revisão do PR #74 (24/10/2026)
#: A redação do design para a opção `TC-01.2` («Cor da roupa») da 5A, registrada na copy revisada da exp02ef1b. Até
#: 29/10/2026 o exemplo era a proposta para a pergunta do Canal B (`TC-02` de então), que saiu da esteira.
PROPOSTA_TC01_2 = "A cor da roupa"


def _estado_com_a_esteira(missao: str = "exp02ef1b-4fd72a9a") -> Dict[str, Any]:
    """O estado com a copy como o A078b a deixa: o texto aprovado na linha e a redação do design na seção da esteira."""
    estado = _estado(missao)
    estado["copy_strings_revisada"] = tk.aplicar_na_copy(estado["copy_strings_revisada"], tk.da_sessao(estado))["texto"]
    return estado


def test_pedido_que_cita_so_o_id_chega_expandido_ao_editor_aos_juizes_e_a_triagem():
    """«Aceito a proposta TC-01.2»: o ID não está no núcleo, no one-pager, no resumido nem na spec. A esteira expande por
    código o texto aprovado e a proposta registrada na copy — no pedido do editor, no do estado (que os juízes leem) e no
    mapa da triagem —, fora do «Pedido, na íntegra» que a fidelidade confere."""
    from pipeline.reexecucao import PedidoCorrecao, montar_mapa_da_missao, texto_do_pedido, texto_para_o_editor

    estado = _estado_com_a_esteira()
    aprovado = tk.por_id(tk.da_sessao(estado))["TC-01.2"].texto
    citados = tk.citados_no_pedido("Aceito a proposta TC-01.2.", estado)
    assert f"texto aprovado: «{aprovado}»" in citados
    assert f"(`TC-01.2`): «{aprovado}» → «{PROPOSTA_TC01_2}»" in citados
    assert tk.citados_no_pedido("Trocar o botão Publicar.", estado) == ""
    assert "não está na tabela" in tk.citados_no_pedido("E a TC-77?", estado)
    # a escolha traz as opções com os IDs, e as propostas das opções
    escolha = tk.citados_no_pedido("TC-01", estado)
    assert "`TC-01.3` «Lugar»" in escolha and "«Cor da roupa» → «A cor da roupa»" in escolha
    pedido = PedidoCorrecao(texto="Aceito a proposta TC-01.2.", textos_chave_citados=citados)
    assert citados in texto_para_o_editor(pedido)
    md = pedido.como_markdown("produto")
    assert citados in md and texto_do_pedido(md) == "Aceito a proposta TC-01.2."
    assert f"«{aprovado}» → «{PROPOSTA_TC01_2}»" in montar_mapa_da_missao(estado, "Aceito a proposta TC-01.2.")
    assert tk.TITULO_CITADOS not in montar_mapa_da_missao(estado)


def test_aceito_tc_01_2_na_exp02ef1b_desce_pela_cascata_ate_o_one_pager():
    """A rota do PR 5 com o pedido só pelo ID: a triagem leva o item a produto, o editor de produto recebe o texto
    aprovado e a proposta (sem isso não trocava nada, e a cascata acabava em Devolver) e troca no one-pager; o design
    recebe o texto novo como aprovado e a redação velha como aprovada antes."""
    import os
    import tempfile
    from unittest import mock

    import pipeline.runner as runner_mod
    from pipeline.reexecucao import PedidoCorrecao, executar_cascata_stream
    from tools.edicao_pontual import Proposta, trocas_por_linhas
    from tools.triagem_pedido import PRODUTO, dividir

    estado = _estado_com_a_esteira()
    pedido = "Aceito a proposta TC-01.2 do design para a opção da 5A."
    divisao = dividir(pedido, "design", estado, [])
    assert [i.dono for i in divisao.itens] == [PRODUTO]
    run_dir = Path(tempfile.mkdtemp()) / "20261024-000000-session_tc01_2"
    run_dir.mkdir(parents=True)
    (run_dir / "estado.json").write_text(json.dumps(estado), encoding="utf-8")
    (run_dir / "conversa.json").write_text(json.dumps({"session_id": "s", "user_id": "u", "prompt": "briefing",
                                                       "created_at": "24/10/2026 10:00:00", "messages": []}), "utf-8")
    editor, runs = [], []

    async def proponente(texto, etapa, documentos, *, erros="", achados=""):
        editor.append({"etapa": etapa, "pedido": texto})
        if etapa != "produto":
            return Proposta(modo="pontual", motivo="o design acompanha", edicoes=[])
        # o editor só sabe o texto pelo que a esteira expandiu
        m = re.search(r"\(`TC-01\.2`\): «(.+?)» → «(.+?)»", texto)
        if not m:
            return Proposta(modo="pontual", motivo="não sei a que texto o TC-01.2 se refere", edicoes=[],
                            pendencias=["TC-01.2 sem texto"])
        de, para = m.groups()
        # em todo lugar onde o texto aprovado está (o one-pager e as duas specs: a troca leva contexto)
        trocas = [e for chave, doc in documentos.items() if de in doc
                  for e in trocas_por_linhas(chave, doc, doc.replace(de, para), "TC-01.2")]
        return Proposta(modo="pontual", motivo="aceita a proposta TC-01.2", edicoes=trocas)

    async def falso(**kwargs):
        from pipeline.runner import PipelineExecutionResult

        runs.append(kwargs)
        novo = dict(kwargs["initial_state"], linha_de_base_linhas=[])
        (Path(kwargs["run_dir"]) / "estado.json").write_text(json.dumps(novo), encoding="utf-8")
        yield {"type": "pipeline_completed", "result": PipelineExecutionResult(
            session_id=kwargs["session_id"], user_id=kwargs["user_id"], prompt=kwargs["prompt"], final_output="ok",
            state=novo, status="success", output_dir=str(kwargs["run_dir"]))}

    async def coletar():
        return [e async for e in executar_cascata_stream(run_dir, "design", PedidoCorrecao(texto=pedido),
                                                         divisao.como_dict(), None, proponente=proponente)]

    with mock.patch.dict(os.environ, {"CORRECAO_PONTUAL": "true", "CORRECAO_PONTUAL_PASSADAS": "1"}), \
            mock.patch.object(runner_mod, "run_orchestrator_pipeline_stream", falso):
        eventos = asyncio.run(coletar())
    assert not [e for e in eventos if e["type"] == "correcao_error"], eventos
    aprovado = tk.por_id(tk.da_sessao(estado))["TC-01.2"].texto
    assert [e["etapa"] for e in editor] == ["produto", "design"]
    assert f"«{aprovado}» → «{PROPOSTA_TC01_2}»" in editor[0]["pedido"]
    produto = runs[0]["initial_state"]
    assert PROPOSTA_TC01_2 in produto["one_pager"] and aprovado not in produto["one_pager"]
    assert PROPOSTA_TC01_2 in (produto.get("spec_missao_gate0") or produto["spec_missao"])
    assert tk.TITULO_CITADOS in produto["pedido_correcao"]
    # no passo de design o texto novo já é o aprovado, com o velho no histórico — o A078b o leva à linha da copy
    assert f"texto aprovado: «{PROPOSTA_TC01_2}»" in editor[1]["pedido"]
    assert f"redações aprovadas antes: «{aprovado}»" in editor[1]["pedido"]
    assert "(já é o texto aprovado)" in editor[1]["pedido"]


def test_citacao_que_e_a_proposta_registrada_volta_ao_aprovado_no_handoff_da_exp02ef1b():
    """O handoff cita um texto-chave na redação do design, distante do aprovado (semelhança abaixo da régua de 0,85 dos
    documentos de dev): é a proposta que a copy registra, e volta ao aprovado por código. No PRD, a linha da proposta na
    19.3 fica; a especificação da tela volta. Até 29/10/2026 o exemplo era a pergunta do Canal B que o handoff gravado da
    exp02ef1b citava; sem o Canal B, a proposta é plantada para a última fala do podcast (`TC-19`), sobre os documentos
    gravados da mesma sessão."""
    from agents.callbacks import copiar_textos_chave

    def com_a_proposta(estado: Dict[str, Any]) -> Dict[str, Any]:
        estado["copy_strings_revisada"] += (f"\n\n- [PROPOSTA — validar com PO: TC-19 «{aprovado}» → «{reescrita}» · "
                                            "a despedida mais solta]\n")
        estado["handoff_dev"] += f"\n- O podcast fecha com a fala do Léo: \"{reescrita}\"\n"
        return estado

    aprovado = tk.por_id(tk.da_sessao(_estado()))["TC-19"].texto
    reescrita = "Tchau, pessoal! Na próxima missão tem mais foto!"
    assert tk.semelhanca(aprovado, reescrita) < tk.CORTE_DOCUMENTO
    estado = com_a_proposta(_estado())
    estado["copy_strings_revisada"] = tk.aplicar_na_copy(estado["copy_strings_revisada"], tk.da_sessao(estado))["texto"]
    assert (estado["handoff_dev"].count(aprovado), estado["handoff_dev"].count(reescrita)) == (0, 1)
    assert tk.aplicar_em_documento(estado["handoff_dev"], tk.da_sessao(estado))[1] == []  # sem as propostas, nada
    copiar_textos_chave("handoff_dev")(SimpleNamespace(state=estado))
    assert estado["handoff_dev"].count(reescrita) == 0 and estado["handoff_dev"].count(aprovado) == 1
    # no corpo, antes do anexo literal (que o callback não toca): a especificação da tela e a proposta na 19.3
    corpo, anexo = estado["prd_final"].split("\n---\n", 1)
    estado["prd_final"] = (f"{corpo}\n\nEspecificação da tela final: o áudio termina em \"{reescrita}\".\n\n"
                           "## 19.3 Decisões do agente a revisar\n\n"
                           f"- [PROPOSTA — validar com PO: TC-19 «{aprovado}» → «{reescrita}» · a despedida mais solta]\n"
                           f"\n---\n{anexo}")
    prd = estado["prd_final"]
    copiar_textos_chave("prd_final")(SimpleNamespace(state=estado))
    linhas = [l for l in estado["prd_final"].splitlines() if reescrita in l]
    assert linhas and all("[PROPOSTA" in l for l in linhas)
    assert estado["prd_final"].count(aprovado) == prd.count(aprovado) + 1
    # sem a seção da esteira (sessão anterior ao PR 7 refeita só no dev), o callback acha a mesma proposta
    antiga = com_a_proposta(_estado())
    copiar_textos_chave("handoff_dev")(SimpleNamespace(state=antiga))
    assert antiga["handoff_dev"].count(aprovado) == 1


def test_redacao_aprovada_antes_desce_sem_a_regua_e_a_ambigua_fica():
    """A redação que o PO trocou (`antes`) é mapeamento exato para o texto novo: a citação dela desce ao handoff e ao
    PRD mesmo distante da nova. A mesma redação registrada para dois textos-chave não se troca, e a citação distante sem
    registro continua com os gates."""
    velho = "Para mostrar em uma foto que duas crianças estão estudando juntas, o que é mais importante aparecer?"
    novo = "O que precisa aparecer na foto para mostrar duas crianças estudando juntas?"
    tc = tk.TextoChave(id="TC-02", tipo=tk.TELA, origem="§4 · Etapa 5", texto=novo, antes=[velho])
    assert tk.semelhanca(velho, novo) < tk.CORTE_DOCUMENTO
    doc = f"# Handoff\n\nA folha mostra *\"{velho}\"* e três cartões.\n"
    saida, trocas = tk.aplicar_em_documento(doc, [tc])
    assert trocas == [("TC-02", novo, velho)] and f"*\"{novo}\"*" in saida
    outro = tk.TextoChave(id="TC-09", tipo=tk.TELA, origem="§4", texto="Outro texto da tela, bem diferente deste.",
                          antes=[velho])
    assert tk.aplicar_em_documento(doc, [tc, outro]) == (doc, [])
    distante = "# Handoff\n\nA folha mostra \"O que a foto precisa ter para provar que estudam juntas?\".\n"
    assert tk.aplicar_em_documento(distante, [tc]) == (distante, [])
    # a proposta já decidida (o aprovado dela não é mais o texto-chave) não manda nada
    decidida = [("TC-02", velho, "O que a foto precisa ter para provar que estudam juntas?")]
    assert tk.aplicar_em_documento(distante, [tc], decidida) == (distante, [])
    aberta = [("TC-02", novo, "O que a foto precisa ter para provar que estudam juntas?")]
    assert tk.aplicar_em_documento(distante, [tc], aberta)[1][0][0] == "TC-02"


@pytest.mark.parametrize("missao", ["exp06ef1b", "exp06ef1b-53e011b6", "exp03ef1b-317df247"])
def test_copy_sem_quebra_no_fim_volta_igual_e_a_pontual_nao_registra_troca(missao):
    """As copies do acervo terminam na cerca do envelope, sem «\\n». A cópia por código devolvia o texto com a quebra a
    mais, e na correção pontual o A078b gravava a copy e registrava em `edicoes_pontuais` a troca «}\\n```» →
    «}\\n```\\n», com o motivo «copiados por código» e nada copiado."""
    from agents.checkers import TextosChaveCopyAgent

    base = _estado_pontual(missao)
    copia = base["copy_strings_revisada"]
    assert not copia.endswith("\n")
    aplicado = tk.aplicar_na_copy(copia, tk.da_sessao(base), anotar_sem_troca=False)
    assert aplicado["copiados"] == 0 and aplicado["texto"] == copia
    final = asyncio.run(_rodar(TextosChaveCopyAgent(name="A078bTextosChave"), base))
    assert final["copy_strings_revisada"] == copia
    assert final["edicoes_pontuais"] == base["edicoes_pontuais"]
    # o fim que veio é o fim que fica, com ou sem a seção da esteira
    assert tk.aplicar_na_copy(copia + "\n", tk.da_sessao(base))["texto"].endswith("```\n")
    com_secao = tk.aplicar_na_copy(_estado("exp02ef1b-4fd72a9a")["copy_strings_revisada"],
                                   tk.da_sessao(_estado("exp02ef1b-4fd72a9a")))["texto"]
    assert not com_secao.endswith("\n") and tk.TITULO_SECAO_COPY in com_secao
