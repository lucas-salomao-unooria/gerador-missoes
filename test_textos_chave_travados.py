"""PR 7 do plano «Produto dono do contrato» (docs/planos/2026-10-23-produto-dono-do-contrato.md, D1 e D7): textos-chave
com ID travados do one-pager à copy; fluxo e telas sem mudar o contrato.

- a tabela de textos-chave sai do one-pager por código (aspas do §4, Canal B do §12a, opções de cada escolha, roteiro do
  §9, podcast do §11), com ID estável — o texto trocado no mesmo lugar guarda o ID, o que sai se aposenta; a sessão
  anterior ao PR 7 é lida das mesmas seções, sem gravar nada;
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
def test_exp02ef1b_tem_a_escolha_da_5a_com_tres_opcoes_e_o_canal_b_com_tres_alternativas():
    tcs = tk.da_sessao(_estado())
    escolha = next(t for t in tcs if t.tipo == tk.OPCOES and "Lugar" in t.texto)
    assert escolha.n == 3 and escolha.origem == "§4 · Etapa 5"
    opcoes = [t for t in tcs if t.grupo == escolha.id]
    assert [o.texto for o in opcoes] == ["Atividade", "Cor da roupa", "Lugar"]
    assert [o.id for o in opcoes] == [f"{escolha.id}.1", f"{escolha.id}.2", f"{escolha.id}.3"]
    pergunta = next(t for t in tcs if t.tipo == tk.CANAL_B)
    assert pergunta.texto.startswith("Para mostrar em uma foto que duas crianças") and pergunta.origem == "§12a · EF02CO01"
    alternativas = next(t for t in tcs if t.tipo == tk.OPCOES and t.origem.startswith("§12a"))
    assert alternativas.n == 3 and alternativas.opcoes[2] == "A parede bonita da sala onde elas estão sentadas."
    # o podcast entra fala a fala; o Canal B e as opções não entram de novo como texto de tela
    assert sum(1 for t in tcs if t.tipo == tk.PODCAST) == 18
    assert not any(t.tipo == tk.TELA and t.texto == "Cor da roupa" for t in tcs)


@pytest.mark.parametrize("missao, perguntas, uma_alternativa", [
    # sem aspas: «**Pergunta:** …» e «— **Alternativa 1:** … `[Atingiu]`»
    ("exp02em1b-60cfa7f4", 4, "Confiar na precisão dos dados, desde que a linguagem do texto esteja bem estruturada"),
    # «- [Atingiu] Revela um engano: …»
    ("exp06ef1b-53e011b6", 3, "Revela um engano: o jurado não percebeu"),
    # «• *Alternativa 1 [Atingiu]:* Manter a proporcionalidade…»
    ("exp03em1b-b2e7b4a3", 6, "Manter a proporcionalidade geométrica linear dos eixos"),
    # «Pergunta: *"…"*<br>• **Atingiu:** *"…"*»
    ("exp09ef1b", 2, "Auditar os dados de treinamento"),
])
def test_canal_b_nos_formatos_do_acervo(missao, perguntas, uma_alternativa):
    canais = tk.canal_b(_estado(missao)["one_pager"])
    assert len(canais) == perguntas and all(len(alts) == 3 for _, _, alts in canais)
    alternativas = [a for _, _, alts in canais for a in alts]
    assert any(a.startswith(uma_alternativa) for a in alternativas), alternativas
    assert not any(a.startswith(("-", ":", "*", "[")) for a in alternativas)


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
    alt = _por_texto(tcs, "As duas crianças usando a mesma camiseta")
    lugar = next(t for t in tcs if t.tipo == tk.OPCAO and t.texto == "Lugar")
    pergunta = next(t for t in tcs if t.tipo == tk.CANAL_B)
    # o PO pede, em design, 2 opções na 5A e outra redação para uma alternativa do Canal B; produto pontual aplica
    one_pager = (estado["one_pager"]
                 .replace('a "Atividade", descartando "Cor da roupa" e "Lugar"', 'a "A atividade", descartando "A cor da roupa"')
                 .replace("As duas crianças usando a mesma camiseta da escola.", "As duas crianças com a mesma camiseta."))
    novo_estado = {**estado, "one_pager": one_pager, tk.KEY_REGISTRO: registro}
    novos, registro2 = tk.atualizar(novo_estado)
    assert _por_texto(novos, "As duas crianças com a mesma camiseta").id == alt.id
    assert next(t for t in novos if t.tipo == tk.CANAL_B).id == pergunta.id
    escolha = next(t for t in novos if t.tipo == tk.OPCOES and t.origem == "§4 · Etapa 5")
    assert escolha.n == 2 and escolha.id == lugar.grupo
    assert [t.texto for t in novos if t.grupo == escolha.id] == ["A atividade", "A cor da roupa"]
    assert lugar.id in {d["id"] for d in registro2["aposentados"]}
    # um texto novo ganha número novo, e o aposentado não volta
    acrescido = one_pager.replace("### Etapa 6: Refletir", "### Etapa 6: Refletir\n- Bento diz: \"Que história essa foto conta para você?\"")
    terceiros, registro3 = tk.atualizar({**novo_estado, "one_pager": acrescido, tk.KEY_REGISTRO: registro2})
    novo_tc = _por_texto(terceiros, "Que história essa foto conta")
    maior = max(tk.partes_do_id(t.id)[0] for t in novos)
    assert tk.partes_do_id(novo_tc.id)[0] == maior + 1
    assert lugar.id not in {t.id for t in terceiros}


def test_tabela_do_po_no_one_pager_dele_da_os_ids():
    estado = _estado()
    estado["one_pager_po"] = ("## Textos-chave\n\n| ID | Tipo | Origem | Texto aprovado |\n|---|---|---|---|\n"
                              "| TC-40 | Canal B — pergunta | §12a | «Para mostrar em uma foto que duas crianças estão estudando "
                              "juntas, o que é mais importante aparecer no enquadramento?» |\n")
    tcs = tk.da_sessao(estado)
    assert next(t for t in tcs if t.tipo == tk.CANAL_B).id == "TC-40"
    # quem não estava na tabela do PO continua numerado, depois do maior dele
    assert all(tk.partes_do_id(t.id)[0] > 40 for t in tcs if t.tipo != tk.CANAL_B)


def test_tabela_em_markdown_tem_id_tipo_origem_e_palavras():
    estado = _estado()
    tcs, registro = tk.atualizar(estado)
    md = tk.tabela(tcs, tk.teto_de_palavras(estado["one_pager"], estado.get("briefing", "")))
    assert md.startswith(f"## {tk.TITULO_TABELA}")
    assert "| `TC-01` | escolha · 3 opções | §4 · Etapa 5 | «Atividade» · «Cor da roupa» · «Lugar» | — |" in md
    assert re.search(r"\| `TC-02` \| Canal B — pergunta \| §12a · EF02CO01 \| «Para mostrar .*» \| 19 ⚠️ teto 10 \|", md)
    # a própria tabela é lida de volta (é o que vale quando o PO já a traz no one-pager dele)
    lidos = {d["id"]: d for d in tk.ler_tabela(md)}
    assert lidos["TC-01"]["tipo"] == tk.OPCOES and lidos["TC-01"]["n"] == 3 and lidos["TC-01.3"]["texto"] == "Lugar"


# --------------------------------------------------------------------------- copy: copiado por código, gate, mutantes
def _copy_de_teste(linhas_extra: str = "") -> str:
    return ("# Copy — exp02ef1b — passada 2\n\n"
            "| ID tela | Chave | Tipo | Seção | PT-BR (final) | Palavras | Redundância | Voz | Revisão (o que mudou e por quê) |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            "| `E5-ALU-01` | `e5.opt.atividade` | rótulo de UI | unoogaleria | Atividade | 1 | texto+ícone | plataforma | `TC-01.1` |\n"
            "| `E5-ALU-01` | `e5.opt.roupa` | rótulo de UI | unoogaleria | Cor da roupa | 3 | texto+ícone | plataforma | `TC-01.2` |\n"
            "| `E5-ALU-01` | `e5.opt.lugar` | rótulo de UI | unoogaleria | Lugar | 1 | texto+ícone | plataforma | `TC-01.3` |\n"
            "| `E6-ALU-02` | `e6.canalb.pergunta` | pergunta | unoogaleria | Para mostrar em uma foto que duas crianças estão "
            "estudando juntas, o que é mais importante aparecer no enquadramento? | 19 | texto+ícone+áudio | guia | `TC-02` |\n"
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
    """«Pronto» no lugar da pergunta do Canal B, na linha que cita `TC-02`: o gate bloqueia a copy como veio; o código
    copia o texto aprovado de volta, e «Pronto» vira proposta ao PO."""
    tcs = tk.da_sessao(_estado())
    pergunta = next(t for t in tcs if t.tipo == tk.CANAL_B)
    mutante = _copy_de_teste().replace(pergunta.texto + " | 19 |", "Pronto | 1 |")
    r = tk.conferir_copy(mutante, tcs)
    assert r["status"] == "bloqueado"
    assert [a["codigo"] for a in r["achados"] if a["severidade"] == "bloqueio"] == ["texto-chave-divergente"]
    aplicado = tk.aplicar_na_copy(mutante, tcs)
    assert f"| {pergunta.texto} | 19 |" in aplicado["texto"]
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
    """A copy revisada da exp02ef1b (23/10) trazia as opções e o Canal B que o PO pediu em design e que nunca chegaram ao
    one-pager: o código devolve o texto aprovado à linha, e o pedido vira proposta — o PO o leva a produto pelo Refazer.
    «Lugar» saiu da 5A, e o código não o inventa: bloqueia."""
    estado = _estado()
    tcs = tk.da_sessao(estado)
    copia = estado["copy_strings_revisada"]
    aplicado = tk.aplicar_na_copy(copia, tcs)
    propostas = {i: p for i, _, p in aplicado["propostas_novas"]}
    assert propostas["TC-01.1"] == "A atividade" and propostas["TC-01.2"] == "A cor da roupa"
    assert propostas["TC-02"].startswith("Para mostrar que duas crianças estudam juntas")
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
    pergunta = next(t for t in tcs if t.tipo == tk.CANAL_B)
    passada1 = tk.aplicar_na_copy(_copy_de_teste().replace(pergunta.texto + " | 19 |", "Pronto | 1 |"), tcs)["texto"]
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
    pergunta = next(t for t in tcs if t.tipo == tk.CANAL_B)
    base["copy_strings_revisada"] = _copy_de_teste().replace(pergunta.texto + " | 19 |", "Pronto | 1 |")
    final = asyncio.run(_rodar(TextosChaveCopyAgent(name="A078bTextosChave"), base))
    assert f"| {pergunta.texto} | 19 |" in final["copy_strings_revisada"]
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
    alt = next(d for d in registro["itens"] if d["texto"].startswith("As duas crianças usando"))
    editado = {**final, "one_pager": final["one_pager"].replace("As duas crianças usando a mesma camiseta da escola.",
                                                                "As duas crianças com a mesma camiseta.")}
    final2 = asyncio.run(_rodar(TextosChaveAgent(name="A044bTextosChave"), editado))
    assert next(d for d in final2[tk.KEY_REGISTRO]["itens"] if d["texto"] == "As duas crianças com a mesma camiseta.")["id"] == alt["id"]


def test_callback_copia_na_passada_1_e_na_citacao_do_prd():
    from agents.callbacks import copiar_textos_chave
    from tools.conteudo_aprovado import TITULO_ANEXO

    estado = _estado()
    tcs = tk.da_sessao(estado)
    pergunta = next(t for t in tcs if t.tipo == tk.CANAL_B)
    estado["copy_strings"] = _copy_de_teste().replace(pergunta.texto + " | 19 |", "Pronto | 1 |")
    copiar_textos_chave("copy_strings")(SimpleNamespace(state=estado))
    assert f"| {pergunta.texto} | 19 |" in estado["copy_strings"]
    quase = pergunta.texto.replace("é mais importante aparecer", "é mais importante que apareça")
    longe = "Para mostrar que duas crianças estudam juntas, o que deve aparecer na foto?"
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
    assert ar.validar(estado, estrito=True)["status"] == "bloqueado"


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


@pytest.mark.parametrize("prompt, exigencias", [
    ("design/071_jornada.md", ["`E0-PROF-01` **Escolher a missão no catálogo.**", "Unooria Hub (kit configuração)",
                               "Escolher a missão → Recorte da aula (disciplina · tema · assuntos · contexto)",
                               "As telas de condução", "a mesma missão em três aulas"]),
    ("design/072_fluxo.md", ["## Fluxo do professor (Mermaid — obrigatório)",
                             "`E0-PROF-02 -->|usar banco padrão| E0-PROF-05`", "`atividade ativada → E1-ALU-01`",
                             "O módulo `/atividades` é o motor do Instanooria e não se reusa"]),
    ("design/075_telas.md", ["**Construída nos dois estados**", "padrão · gerando · sem saldo · pacote pronto",
                             "uma disciplina diferente do banco default"]),
    ("design/079_prototipo.md", ["**O trilho do professor é obrigatório e começa antes da aula:**",
                                 "a transição «atividade ativada» levando à primeira tela do estudante"]),
    ("design/088_qa_entregaveis.md", ["tela do professor ausente do Stitch é ⛔ com dono `telas`",
                                      "caminho curto** `E0-PROF-01 → 02 → 05`", "Teste das três disciplinas",
                                      "Simulação de preparo em minutos"]),
])
def test_preparo_do_professor_saiu_do_prompt_e_o_prompt_ainda_pede_o_mesmo(prompt, exigencias):
    """D7: o fluxo fixo E0-PROF-01…05 vira padrão da plataforma em references/, e cada prompt de design o cita — o
    texto expandido traz as mesmas exigências que o prompt trazia."""
    from prompts import get_prompt_raw, load_prompt

    bruto = get_prompt_raw(prompt)
    assert f"<!-- include: {PREPARO} -->" in bruto
    assert "`E0-PROF-03` Geração em andamento (progresso por polling" not in bruto  # a descrição mora na referência
    expandido = load_prompt(prompt, stitch_mcp_mode="x", stitch_project_url_base="x", qa_max_rodadas=2)
    for e in exigencias:
        assert e in expandido, (prompt, e)


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


def test_gate_do_handoff_ve_o_canal_b_reescrito_pelo_design():
    """exp02ef1b: o handoff cita a pergunta do Canal B na redação que o design escreveu em 23/10. A leitura antiga do
    §12a não achava o Canal B nesse formato («*Alt 1:* "…" `[Atingiu]`»); com os textos-chave, o gate de montagem o vê."""
    from tools import montagem

    r = montagem.validar_handoff(_estado())
    achado = next(a for a in r["achados"] if a["codigo"] == "texto-chave-reescrito")
    assert "Para mostrar que duas crianças estudam juntas" in achado["resumo"] and achado["severidade"] == "bloqueio"


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
    assert at.expander[0].label.startswith("🔑 Textos-chave aprovados — 21 com ID")
    assert any("TC-01" in m.value for m in at.markdown)


def test_outro_texto_do_po_entra_tambem_na_spec_que_copia_o_canal_b():
    """O Canal B da exp02ef1b está no one-pager e no bloco 9 da spec do Gate 0: o texto que o PO escreve no de acordo
    entra nos dois — trocado só no one-pager, a spec ficava com o texto velho."""
    estado = _estado()
    item = next(i for i in fc.itens_em_aberto(estado) if i.tipo == fc.TEXTO_TETO and "Para mostrar" in i.assunto)
    assert {o.documento for o in item.ocorrencias} == {fc.DOC_ONE_PAGER, fc.DOC_SPEC}
    novo = "O que precisa aparecer na foto?"
    d = fc.decidir([item], {item.id: {"resposta": fc.OUTRO, "valor": novo}}, "24/10/2026 10:00:00", "produto")
    novos, falhas = fc.aplicar_edicoes(estado, d.edicoes)
    assert not falhas and set(novos) == {"one_pager", "spec_missao_gate0", "spec_missao"}
    assert all(novo in texto and item.texto_chave not in texto for texto in novos.values())


def test_proposta_decidida_pelo_po_sai_da_secao_da_esteira():
    """Cascata do PR 5: o PO aceita no Refazer a redação que o design propôs (ou escreve outra), o editor de produto a põe
    no one-pager e o texto-chave muda — a proposta antiga sai da seção da esteira em vez de ficar no cartão para sempre."""
    estado = _estado()
    tcs = tk.da_sessao(estado)
    pergunta = next(t for t in tcs if t.tipo == tk.CANAL_B)
    com_proposta = tk.aplicar_na_copy(_copy_de_teste().replace(pergunta.texto + " | 19 |", "Pronto | 1 |"), tcs)["texto"]
    novo = "O que precisa aparecer na foto?"
    _, registro = tk.atualizar(estado)
    trocado = {**estado, "one_pager": estado["one_pager"].replace(pergunta.texto, novo), tk.KEY_REGISTRO: registro}
    tcs2 = tk.da_sessao(trocado)
    assert next(t for t in tcs2 if t.tipo == tk.CANAL_B).id == pergunta.id
    depois = tk.aplicar_na_copy(com_proposta, tcs2)
    assert f"| {novo} |" in depois["texto"]  # o texto novo desce por código para a linha que cita o ID
    assert not any(p == "Pronto" for _, _, p in depois["propostas"])
    # e a redação aprovada antes, que estava na linha, não vira proposta do design: ela só desce
    assert not [p for p in depois["propostas"] if p[2].startswith("Para mostrar em uma foto")]


def test_cascata_em_sessao_sem_registro_leva_o_texto_novo_a_linha_da_copy():
    """As quatro missões refeitas depois do PR 7 não têm registro: na correção pontual de produto, os IDs saem do
    one-pager de antes do pedido (`versao_anterior_one_pager`). O texto que o PO trocou guarda o ID e a redação velha, e
    a linha da copy que ainda a traz — sem citar o ID — recebe a nova por código, sem proposta."""
    estado = _estado()
    pergunta = next(t for t in tk.da_sessao(estado) if t.tipo == tk.CANAL_B)
    novo = "O que precisa aparecer na foto para mostrar duas crianças estudando juntas?"
    corrigido = {**estado, "versao_anterior_one_pager": estado["one_pager"],
                 "one_pager": estado["one_pager"].replace(pergunta.texto, novo)}
    tcs, registro = tk.atualizar(corrigido)
    nova = next(t for t in tcs if t.tipo == tk.CANAL_B)
    assert nova.id == pergunta.id and nova.texto == novo and nova.antes == [pergunta.texto]
    assert registro["itens"][[d["id"] for d in registro["itens"]].index(nova.id)]["antes"] == [pergunta.texto]
    copia = _copy_de_teste().replace("| `TC-02` |", "| — |")
    aplicado = tk.aplicar_na_copy(copia, tcs)
    assert f"| {novo} |" in aplicado["texto"] and f"`{nova.id}`" in aplicado["texto"]
    assert not aplicado["propostas"]
