"""Correção pontual: o pedido vira trocas, os autores não reescrevem, os gates julgam e a linha de base separa o 🔴.

Os casos vêm do acervo do bucket (19/10/2026): a troca de um número na exp03em1b devolveu a spec com 49% das linhas
iguais e dois 🔴 novos — BNCC, pela reescrita do bloco 11, e fidelidade, por «preservar todo o restante» sem prova
possível; na correção seguinte, a ordem «trocar APENAS o número» do briefing reprovou a migração de DS que o PO pediu.
"""
import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest import mock

from google.adk.agents import LoopAgent, SequentialAgent
from google.adk.runners import InMemoryRunner
from google.genai import types

from tools import edicao_pontual as ed
from tools import fidelidade as fid
from tools import linha_de_base as lb

ONE_PAGER = ("# One-pager — O Porta-Voz dos Dados\n\n## 4. As 6 etapas\n\n"
             "**Etapa 5 — Explicar:** o eixo em 80% faz a queda parecer de mais de 70%.\n\n"
             "## 9. Conceitos\n\n| C2 | Truncamento | a perda visual aparente é mais de 70% |\n")
SPEC = ("# Spec — O Porta-Voz dos Dados v1\n\n### Etapa 5: Explicar\n\nO estudante vê que a queda parece de mais de 70%.\n"
        "\n## 11. BNCC\n\n| EM13CO26 | Aplicar os conceitos do direito digital |\n")
NUCLEO = "# Núcleo\n\nDescoberta: gráfico é escolha editorial.\n"


def _troca(doc, de, para):
    return ed.Edicao(documento=doc, de=de, para=para)


# ------------------------------------------------------------------ aplicar e provar as trocas
def test_aplica_trocas_e_deixa_o_resto_identico():
    docs = {"one_pager": ONE_PAGER, "spec_missao": SPEC}
    r = ed.aplicar(docs, [
        _troca("one_pager", "parecer de mais de 70%.", "parecer de cerca de 47% (alturas 15 → 8)."),
        _troca("one_pager", "| a perda visual aparente é mais de 70% |", "| a perda visual aparente é de ≈47% |"),
        _troca("spec_missao", "parece de mais de 70%.", "parece de cerca de 47%."),
    ])
    assert r.ok and len(r.aplicadas) == 3
    assert "70%" not in r.documentos["one_pager"] + r.documentos["spec_missao"]
    # tudo o que nenhuma troca tocou continua igual, letra por letra
    assert r.documentos["one_pager"].replace("parecer de cerca de 47% (alturas 15 → 8).", "parecer de mais de 70%.") \
        .replace("| a perda visual aparente é de ≈47% |", "| a perda visual aparente é mais de 70% |") == ONE_PAGER


def test_troca_que_nao_existe_ou_se_repete_falha_e_nada_e_aplicado():
    docs = {"one_pager": ONE_PAGER}
    inventada = ed.aplicar(docs, [_troca("one_pager", "Etapa 5", "Etapa cinco"),
                                  _troca("one_pager", "mais de setenta por cento", "47%")])
    assert not inventada.ok and inventada.documentos == docs and inventada.aplicadas == []
    assert any("não existe, letra por letra" in f for f in inventada.falhas)
    repetida = ed.aplicar(docs, [_troca("one_pager", "mais de 70%", "47%")])
    assert any("aparece 2 vezes" in f for f in repetida.falhas)
    outro_doc = ed.aplicar(docs, [_troca("prd_final", "x", "y")])
    assert "não existe nesta etapa" in outro_doc.falhas[0]


def test_acrescentar_e_remover():
    r = ed.aplicar({"one_pager": ONE_PAGER}, [
        _troca("one_pager", "## 9. Conceitos\n", "## 9. Conceitos\n\nNota: alturas visuais de 15 e 8 unidades.\n"),
        _troca("one_pager", "| C2 | Truncamento | a perda visual aparente é mais de 70% |\n", ""),
    ])
    assert r.ok and "alturas visuais de 15 e 8" in r.documentos["one_pager"] and "| C2 |" not in r.documentos["one_pager"]


def test_reaplicar_prova_que_so_as_trocas_mudaram():
    trocas = [{"documento": "spec_missao", "de": "parece de mais de 70%.", "para": "parece de cerca de 47%."}]
    corrigida = SPEC.replace("parece de mais de 70%.", "parece de cerca de 47%.")
    assert ed.reaplicar(SPEC, corrigida, "spec_missao", trocas)
    # a reescrita do bloco 11 que a exp03em1b sofreu não passa
    assert not ed.reaplicar(SPEC, corrigida.replace("| EM13CO26 |", "| Cultura Digital | EM13CO26 |"), "spec_missao", trocas)


def test_documentos_da_etapa_usam_a_spec_do_gate0_e_o_prd_sem_anexo():
    from tools.conteudo_aprovado import TITULO_ANEXO

    estado = {"spec_missao": "consolidada pelo D0", "spec_missao_gate0": SPEC, "one_pager": ONE_PAGER,
              "prd_final": f"# PRD\n\ncorpo\n\n---\n\n# {TITULO_ANEXO}\n\nanexo da esteira", "nucleo_narrativo": ""}
    produto = ed.documentos_da_etapa(estado, "produto")
    assert produto["spec_missao"] == SPEC and "nucleo_narrativo" not in produto
    assert "anexo da esteira" not in ed.documentos_da_etapa(estado, "dev")["prd_final"]


def test_proposta_ilegivel_e_estrutural():
    texto = ('Vou trocar o número.\n```json\n{"agente": "editor-pontual", "modo": "pontual", "motivo": "número", '
             '"edicoes": [{"documento": "one_pager", "de": "a", "para": "b"}], "pendencias": []}\n```')
    p = ed.ler_proposta(texto)
    assert p.pontual and p.edicoes[0].documento == "one_pager"
    assert ed.ler_proposta("não sei").modo == ed.MODO_ESTRUTURAL
    assert not ed.ler_proposta('```json\n{"modo": "talvez"}\n```').pontual


# ------------------------------------------------------------------ linha de base
def _bloqueio(codigo, resumo, citacao=""):
    return {"severidade": "bloqueio", "codigo": codigo, "resumo": resumo, **({"citacao": citacao} if citacao else {})}


def test_cada_bloqueio_e_classificado_contra_o_veredito_de_antes():
    base = {"bncc_status": {"status": "bloqueado", "achados": [_bloqueio("eixo-divergente", "EM13CO26 com eixo")]}}
    alterado = lb._norm("O estudante vê que a queda parece de mais de 70%.\nO estudante vê que a queda parece de cerca de 47%.")
    lugares = {("etapa", "5")}
    assert lb.classificar(_bloqueio("x", "r", "a queda parece de cerca de 47%"), {}, alterado) == lb.DA_EDICAO
    assert lb.classificar(_bloqueio("eixo-divergente", "EM13CO26 com eixo"), base["bncc_status"], alterado) == lb.PRE_EXISTENTE
    assert lb.classificar(_bloqueio("y", "r", "Descoberta: gráfico é escolha editorial"), {}, alterado) == lb.TEXTO_INALTERADO
    # sem citação: é da correção se põe entre aspas o que as trocas tocaram, ou aponta o lugar que elas editaram
    assert lb.classificar(_bloqueio("d", "a spec diz «a queda parece de mais de 70%» e o one-pager não"), {},
                          alterado) == lb.DA_EDICAO
    assert lb.classificar(_bloqueio("t", "A Etapa 5 não fecha o tempo"), {}, alterado, lugares) == lb.DA_EDICAO
    assert lb.classificar(_bloqueio("z", "A Seção 1 não contém a subseção 1.3"), {}, alterado, lugares) == lb.FORA_DA_CORRECAO
    assert lb.classificar(_bloqueio("dimensao-ausente", "o juiz não respondeu"), {}, alterado) == lb.FALHA_DE_EXECUCAO


def test_lugares_editados_saem_do_titulo_sob_a_troca():
    anteriores = {"spec_missao": SPEC, "one_pager": ONE_PAGER}
    lugares = lb.lugares_editados(anteriores, [
        {"documento": "spec_missao", "de": "parece de mais de 70%.", "para": "x"},
        {"documento": "one_pager", "de": "| C2 | Truncamento |", "para": "y"}])
    assert ("etapa", "5") in lugares and ("secao", "9") in lugares and ("secao", "11") not in lugares


def test_regras_novas_da_reexecucao_real_nao_travam_a_troca_do_numero():
    # os 10 🔴 da exp03em1b reexecutada em 19/10/2026: gates sem veredito antes, nenhum ligado às 4 trocas
    achados = {
        "comite_canal_b_status": _bloqueio("B1-1", "A pergunta mede memória do enredo em vez da habilidade."),
        "comite_final_status": _bloqueio("F2-2", "A Seção 1 não contém a subseção 1.3 (Conta da virada)."),
        "evidencia_one_pager_status": _bloqueio("12a-sem-tabela", "O §12a não tem a tabela do contrato."),
        "manifesto_status": _bloqueio("secao_ds", "`whatsappmobile` é seção legada: missão nova usa `unoochat`."),
        "banca_produto_status": _bloqueio("dimensao-ausente", "A dimensão não devolveu envelope legível."),
    }
    estado = {k: "bloqueado" for k in achados}
    estado.update({f"{k}_envelope": {"status": "bloqueado", "achados": [a]} for k, a in achados.items()})
    trocas = [{"documento": "spec_missao", "de": "parece de mais de 70%.", "para": "parece de cerca de 47%."}]
    delta, linhas = lb.aplicar(estado, {"manifesto_status": {"status": "aprovado", "achados": []}}, trocas,
                               list(achados), anteriores={"spec_missao": SPEC})
    assert {k for k in achados if delta.get(k) == "amarelo"} == set(achados) - {"banca_produto_status"}
    assert lb.bloqueios_novos(linhas) == []


def test_bloqueio_em_trecho_que_a_correcao_nao_tocou_vira_amarelo_e_o_antigo_continua_vermelho():
    estado = {
        "gate_final_status": "bloqueado",
        "gate_final_status_envelope": {"status": "bloqueado", "achados": [
            _bloqueio("F4", "ruído do juiz", "Descoberta: gráfico é escolha editorial.")]},
        "gate_final_report": "# Gate final\n",
        "bncc_status": "bloqueado",
        "bncc_status_envelope": {"status": "bloqueado", "achados": [_bloqueio("eixo-divergente", "EM13CO26 com eixo")]},
        "degradacoes": [{"gate": "Gate final de produto", "motivo": "reprovado"}], "pipeline_bloqueado": True,
    }
    base = {"gate_final_status": {"status": "amarelo", "achados": []},
            "bncc_status": {"status": "bloqueado", "achados": [_bloqueio("eixo-divergente", "EM13CO26 com eixo")]}}
    trocas = [{"documento": "spec_missao", "de": "parece de mais de 70%.", "para": "parece de cerca de 47%."}]
    delta, linhas = lb.aplicar(estado, base, trocas, ["bncc_status", "gate_final_status"])
    assert delta["gate_final_status"] == "amarelo"
    assert delta["gate_final_status_envelope"]["veredito_original"] == "bloqueado"
    assert "Linha de base da correção pontual" in delta["gate_final_report"]
    assert "bncc_status" not in delta  # o 🔴 que já existia não cai: a correção não o resolveu
    assert {l["gate"]: l["origem"] for l in linhas} == {"bncc_status": lb.PRE_EXISTENTE,
                                                         "gate_final_status": lb.TEXTO_INALTERADO}
    assert lb.bloqueios_novos(linhas) == []
    assert "degradacoes" not in delta  # ainda há gate vermelho vivo


def test_sem_gate_vermelho_vivo_a_degradacao_da_etapa_cai():
    estado = {"gate_final_status": "bloqueado", "degradacoes": [{"gate": "Gate final de produto", "motivo": "r"}],
              "pipeline_bloqueado": True, "gate_final_status_envelope": {"status": "bloqueado", "achados": [
                  _bloqueio("F4", "ruído", "Descoberta: gráfico é escolha editorial.")]}}
    delta, _ = lb.aplicar(estado, {}, [{"documento": "one_pager", "de": "a", "para": "outra coisa qualquer aqui"}],
                          ["gate_final_status"])
    assert delta["pipeline_bloqueado"] is False and delta["degradacoes"] == []


# ------------------------------------------------------------------ fidelidade
_PEDIDO = ("Reprocessamento pontual: correção de consistência numérica. Corrigir o número em todos os pontos. "
           "Preservar os dados do exemplo (95% → 88%, eixo em 80%), a dinâmica da missão e todo o restante dos "
           "documentos sem alteração.")


def _preservacao(itens):
    return next(i for i in itens if "todo o restante" in i["texto"])


def test_preservar_todo_o_restante_se_prova_pelas_trocas():
    itens = fid.montar_checklist([("refazer Produto · PO · 13/10", _PEDIDO)], "")
    trocas = [{"documento": "spec_missao", "de": "parece de mais de 70%.", "para": "parece de cerca de 47%."}]
    atual = {"spec_missao": SPEC.replace("parece de mais de 70%.", "parece de cerca de 47%.")}
    anteriores = {"spec_missao": SPEC}
    sem_prova = fid.aplicar(itens, "", atual, anteriores=anteriores)
    item = _preservacao(itens)
    # sem as trocas, nada prova que mudou nem que ficou: 🟡 a conferir desde a C7 (25/10/2026)
    assert any(a["id"] == item["id"] and a["severidade"] == "atencao" for a in sem_prova["achados"])
    pontual = fid.aplicar(itens, "", atual, anteriores=anteriores, edicoes=trocas)
    assert any(c["id"] == item["id"] and "correção pontual" in c["prova"] for c in pontual["conferidos"])
    # e uma mudança fora das trocas é prova em código de que a ordem não foi cumprida: continua 🔴
    reescrita = {"spec_missao": atual["spec_missao"].replace("Aplicar os conceitos", "Aplicar conceitos")}
    fora = fid.aplicar(itens, "", reescrita, anteriores=anteriores, edicoes=trocas)
    assert any(a["id"] == item["id"] and a["severidade"] == "bloqueio" and "além das trocas" in a["resumo"]
               for a in fora["achados"])


def test_ordem_de_nao_mexer_de_outra_rodada_nao_trava_o_pedido_novo():
    antigo = "Correção cirúrgica. Não alterar nenhuma outra frase, seção, componente ou estrutura dos documentos."
    novo = "Migrar a seção do design system de whatsappmobile para unoochat em todos os documentos da missão."
    itens = fid.montar_checklist([("refazer Produto · PO · 13/10", antigo), ("refazer Produto · PO · 14/10", novo)], "")
    ordem = next(i for i in itens if "Não alterar nenhuma outra frase" in i["texto"])
    juiz = "```json\n" + json.dumps({"decisoes": [
        {"id": ordem["id"], "veredito": "violado", "citacao": "", "explicacao": "o DS mudou"}]}) + "\n```"
    docs = {"spec_missao": "secao_ds: unoochat"}
    sem_rodada = fid.aplicar(itens, juiz, docs)
    assert next(a for a in sem_rodada["achados"] if a["id"] == ordem["id"])["severidade"] == "bloqueio"
    corrente = fid.aplicar(itens, juiz, docs, origens_correntes={"refazer Produto · PO · 14/10"})
    achado = next(a for a in corrente["achados"] if a["id"] == ordem["id"])
    assert achado["severidade"] == "atencao" and "o pedido desta correção prevalece" in achado["resumo"]


# ------------------------------------------------------------------ autores travados e esteira de uma rodada
async def _rodar(root, estado):
    runner = InMemoryRunner(agent=root, app_name="teste")
    await runner.session_service.create_session(app_name="teste", user_id="u", session_id="s", state=estado)
    async for _ in runner.run_async(user_id="u", session_id="s",
                                    new_message=types.Content(role="user", parts=[types.Part(text="go")])):
        pass
    final = await runner.session_service.get_session(app_name="teste", user_id="u", session_id="s")
    return dict(final.state)


def test_autor_nao_reescreve_documento_travado_na_correcao_pontual():
    from agents.base import create_llm_agent

    # modelo inexistente: se o autor rodasse, a chamada falharia — travado, ele nem chega a chamar
    autor = create_llm_agent(name="A014SecoesApoio", instruction="escreva", description="autor", output_key="one_pager",
                             model="modelo-que-nao-existe")
    final = asyncio.run(_rodar(autor, {"one_pager": ONE_PAGER, "modo_correcao": "pontual",
                                       "documentos_travados": ["one_pager"]}))
    assert final["one_pager"] == ONE_PAGER


def test_orquestrador_pontual_roda_cada_loop_uma_vez_e_fecha_com_a_linha_de_base():
    from agents.checkers import ComiteVotosAgent, EnvelopeGateAgent, LinhaDeBaseAgent
    from pipeline.orchestrator import create_mission_orchestrator, iter_agent_tree

    pontual = create_mission_orchestrator(stages=["produto"], com_transversal=False, modo_pontual=True)
    arvore = [a for _, a in iter_agent_tree(pontual)]
    assert isinstance(pontual.sub_agents[-1], LinhaDeBaseAgent)
    assert {a.max_iterations for a in arvore if isinstance(a, LoopAgent)} == {1}
    assert {a.max_rounds for a in arvore if isinstance(a, EnvelopeGateAgent)} == {1}
    assert all(a.max_rounds > 1 for a in arvore if isinstance(a, ComiteVotosAgent))
    # a geração não muda: a montagem pontual não vaza para a normal
    normal = create_mission_orchestrator(stages=["produto"], com_transversal=False)
    assert not any(isinstance(a, LinhaDeBaseAgent) for _, a in iter_agent_tree(normal))
    assert max(a.max_iterations for _, a in iter_agent_tree(normal) if isinstance(a, LoopAgent)) > 1


def test_linha_de_base_agent_so_age_na_correcao_pontual():
    from agents.checkers import LinhaDeBaseAgent

    estado = {"etapa_da_correcao": "produto", "gate_final_status": "bloqueado",
              "gate_final_status_envelope": {"status": "bloqueado", "achados": [
                  _bloqueio("F4", "ruído", "Descoberta: gráfico é escolha editorial.")]},
              "edicoes_pontuais": [{"documento": "one_pager", "de": "70%", "para": "cerca de 47%"}],
              "linha_de_base": {"gate_final_status": {"status": "aprovado", "achados": []}}}
    agente = SequentialAgent(name="R", sub_agents=[LinhaDeBaseAgent(name="LB")])
    assert asyncio.run(_rodar(agente, dict(estado)))["gate_final_status"] == "bloqueado"
    final = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[LinhaDeBaseAgent(name="LB")]),
                               {**estado, "modo_correcao": "pontual"}))
    assert final["gate_final_status"] == "amarelo"
    assert "cerca de 47%" in final["linha_de_base_report"] and "trecho inalterado" in final["linha_de_base_report"]


# ------------------------------------------------------------------ o fluxo inteiro, com runner e editor falsos
class _Fluxo:
    def __init__(self):
        self.temp = Path(tempfile.mkdtemp())
        self.run_dir = self.temp / "20261013-000000-session_teste"
        self.run_dir.mkdir(parents=True)
        estado = {"briefing": "briefing", "material_anexado": "material", "nucleo_narrativo": NUCLEO,
                  "one_pager": ONE_PAGER, "spec_missao": SPEC,
                  "mapa_conceitual": "mapa", "ideacao_mecanismos": "ideação",
                  "gate_final_status": "amarelo", "bncc_status": "aprovado", "jornada_telas": "telas de design"}
        (self.run_dir / "estado.json").write_text(json.dumps(estado), encoding="utf-8")
        (self.run_dir / "conversa.json").write_text(json.dumps({
            "session_id": "session_teste", "user_id": "u", "created_at": "13/10/2026 10:00:00", "prompt": "briefing",
            "messages": []}), encoding="utf-8")
        self.runs = []
        self.editor = []

    def runner(self, linhas_por_passada):
        fluxo = self

        async def falso(**kwargs):
            from pipeline.runner import PipelineExecutionResult

            fluxo.runs.append(kwargs)
            estado = dict(kwargs["initial_state"],
                          linha_de_base_linhas=linhas_por_passada[min(len(fluxo.runs), len(linhas_por_passada)) - 1])
            (Path(kwargs["run_dir"]) / "estado.json").write_text(json.dumps(estado), encoding="utf-8")
            yield {"type": "pipeline_completed", "result": PipelineExecutionResult(
                session_id=kwargs["session_id"], user_id=kwargs["user_id"], prompt=kwargs["prompt"], final_output="ok",
                state=estado, status="success", output_dir=str(kwargs["run_dir"]))}

        return falso

    def proponente(self, respostas):
        fluxo = self

        async def falso(pedido, etapa, documentos, *, erros="", achados=""):
            fluxo.editor.append({"documentos": dict(documentos), "erros": erros, "achados": achados})
            return respostas[min(len(fluxo.editor), len(respostas)) - 1]

        return falso

    def rodar(self, pedido, respostas, linhas_por_passada=([],)):
        import pipeline.runner as runner_mod
        from pipeline.reexecucao import PedidoCorrecao, executar_correcao_stream

        async def coletar():
            return [e async for e in executar_correcao_stream(
                self.run_dir, "produto", PedidoCorrecao(texto=pedido), None, so_esta_etapa=True,
                proponente=self.proponente(respostas))]

        with mock.patch.dict(os.environ, {"CORRECAO_PONTUAL": "true", "CORRECAO_PONTUAL_PASSADAS": "2"}), \
                mock.patch.object(runner_mod, "run_orchestrator_pipeline_stream", self.runner(list(linhas_por_passada))):
            return asyncio.run(coletar())

    def fechar(self):
        shutil.rmtree(self.temp, ignore_errors=True)


def _proposta(*trocas, pendencias=()):
    return ed.Proposta(modo=ed.MODO_PONTUAL, edicoes=[ed.Edicao(*t) for t in trocas], pendencias=list(pendencias))


_NUMERO = ("one_pager", "parecer de mais de 70%.", "parecer de cerca de 47%.")
_NUMERO_SPEC = ("spec_missao", "parece de mais de 70%.", "parece de cerca de 47%.")


def test_correcao_pontual_roda_os_gates_sobre_os_documentos_editados():
    f = _Fluxo()
    try:
        eventos = f.rodar("Corrigir 70% para 47%.", [_proposta(_NUMERO, _NUMERO_SPEC, pendencias=["validar com o PO"])])
        assert len(f.runs) == 1 and f.runs[0]["modo_pontual"] is True and f.runs[0]["stages"] == ["produto"]
        inicial = f.runs[0]["initial_state"]
        assert "cerca de 47%" in inicial["one_pager"] and "cerca de 47%" in inicial["spec_missao"]
        assert inicial["nucleo_narrativo"] == NUCLEO and inicial["mapa_conceitual"] == "mapa"
        assert inicial["modo_correcao"] == "pontual" and "one_pager" in inicial["documentos_travados"]
        assert inicial["versao_anterior_one_pager"] == ONE_PAGER.strip()  # a prova da fidelidade
        assert inicial["one_pager_gate0"] == inicial["one_pager"]
        assert "gate_final_status" not in inicial and "jornada_telas" not in inicial  # gates e design caem
        assert inicial["linha_de_base"]["gate_final_status"]["status"] == "amarelo"
        assert "edição pontual" in inicial["pedido_correcao"]
        registro = next(e for e in eventos if e["type"] == "correcao_completed")["registro"]
        assert registro["modo"] == "pontual" and len(registro["edicoes"]) == 2 and registro["passadas"] == 1
        assert registro["pendencias"] == ["validar com o PO"]
        conversa = json.loads((f.run_dir / "conversa.json").read_text(encoding="utf-8"))
        assert "Correção pontual aplicada" in conversa["messages"][-1]["content"]
    finally:
        f.fechar()


def test_bloqueio_causado_pela_correcao_volta_ao_editor_e_os_gates_julgam_de_novo():
    f = _Fluxo()
    try:
        novo = {"gate": "conteudo_aprovado_spec_status", "origem": lb.DA_EDICAO, "codigo": "divergente",
                "resumo": "a tabela de conceitos ainda diz 70%", "antes": "aprovado"}
        conserto = _proposta(("one_pager", "aparente é mais de 70%", "aparente é cerca de 47%"))
        eventos = f.rodar("Corrigir 70% para 47%.", [_proposta(_NUMERO, _NUMERO_SPEC), conserto],
                          linhas_por_passada=([novo], []))
        assert len(f.runs) == 2 and len(f.editor) == 2
        assert "a tabela de conceitos ainda diz 70%" in f.editor[1]["achados"]
        assert "cerca de 47%" in f.editor[1]["documentos"]["one_pager"]  # o conserto parte do já editado
        segunda = f.runs[1]["initial_state"]
        assert "aparente é cerca de 47%" in segunda["one_pager"] and len(segunda["edicoes_pontuais"]) == 3
        registro = next(e for e in eventos if e["type"] == "correcao_completed")["registro"]
        assert registro["passadas"] == 2 and len(registro["edicoes"]) == 3
    finally:
        f.fechar()


def test_troca_que_nao_se_aplica_volta_ao_editor_com_o_motivo():
    f = _Fluxo()
    try:
        errada = _proposta(("one_pager", "texto que não está lá", "x"))
        f.rodar("Corrigir 70% para 47%.", [errada, _proposta(_NUMERO)])
        assert len(f.editor) == 2 and "não existe, letra por letra" in f.editor[1]["erros"]
        assert f.runs[0]["modo_pontual"] is True
    finally:
        f.fechar()


def test_pedido_estrutural_refaz_a_etapa_pelos_autores():
    f = _Fluxo()
    try:
        estrutural = ed.Proposta(modo=ed.MODO_ESTRUTURAL, motivo="o PO descartou a direção da missão")
        eventos = f.rodar("Descartar esta direção e criar outra narrativa.", [estrutural])
        assert f.runs[0]["modo_pontual"] is False
        inicial = f.runs[0]["initial_state"]
        assert "one_pager" not in inicial and "anterior_one_pager" in inicial and "modo_correcao" not in inicial
        registro = next(e for e in eventos if e["type"] == "correcao_completed")["registro"]
        assert registro["modo"] == "refazer" and registro["motivo_modo"] == "o PO descartou a direção da missão"
    finally:
        f.fechar()


def test_sem_o_material_original_so_a_correcao_pontual_cabe():
    f = _Fluxo()
    try:
        estado = json.loads((f.run_dir / "estado.json").read_text(encoding="utf-8"))
        estado.pop("material_anexado")
        (f.run_dir / "estado.json").write_text(json.dumps(estado), encoding="utf-8")
        conversa = json.loads((f.run_dir / "conversa.json").read_text(encoding="utf-8"))
        (f.run_dir / "conversa.json").write_text(json.dumps({**conversa, "attached_files": ["manual.docx"]}),
                                                 encoding="utf-8")
        recusada = f.rodar("Outra narrativa.", [ed.Proposta(modo=ed.MODO_ESTRUTURAL, motivo="direção nova")])
        assert recusada[-1]["type"] == "correcao_error" and "manual.docx" in recusada[-1]["error"] and not f.runs
        aceita = f.rodar("Corrigir 70% para 47%.", [_proposta(_NUMERO)])
        assert aceita[-1]["type"] == "correcao_completed" and f.runs[0]["modo_pontual"] is True
    finally:
        f.fechar()


def test_juiz_que_nao_respondeu_e_julgado_de_novo_sem_editar():
    f = _Fluxo()
    try:
        falha = {"gate": "banca_produto_status", "origem": lb.FALHA_DE_EXECUCAO, "codigo": "dimensao-ausente",
                 "resumo": "o juiz não respondeu", "antes": "—"}
        eventos = f.rodar("Corrigir 70% para 47%.", [_proposta(_NUMERO)], linhas_por_passada=([falha], []))
        assert len(f.runs) == 2 and len(f.editor) == 1
        registro = next(e for e in eventos if e["type"] == "correcao_completed")["registro"]
        assert registro["passadas"] == 2 and len(registro["edicoes"]) == 1
    finally:
        f.fechar()


# ------------------------------------------------------------------ retrabalho por trocas nos loops (geração e correção)
from google.adk.agents.base_agent import BaseAgent  # noqa: E402
from google.adk.events import Event, EventActions  # noqa: E402


class _GateQueReprovaUmaVez(BaseAgent):
    """Reprova enquanto a Etapa 5 disser «parecer de mais de 70%»; aprova depois."""

    async def _run_async_impl(self, ctx):
        reprovado = "parecer de mais de 70%" in str(ctx.session.state.get("one_pager") or "")
        envelope = {"status": "bloqueado" if reprovado else "aprovado", "achados": [
            {"severidade": "bloqueio", "codigo": "conta", "resumo": "a conta está errada",
             "citacao": "faz a queda parecer de mais de 70%"}] if reprovado else []}
        yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(state_delta={
            "gate_status": envelope["status"], "gate_status_envelope": envelope,
            "gate_report": "A Etapa 5 erra a conta: 15 → 8 é ≈47%." if reprovado else ""}))


def _loop_de_retrabalho():
    from agents.base import create_llm_agent
    from agents.checkers import SaidaDeLoopAgent

    autor = create_llm_agent(name="A014SecoesApoio", instruction="escreva", description="autor",
                             output_key="one_pager", model="modelo-que-nao-existe")
    return LoopAgent(name="L", max_iterations=3, sub_agents=[
        _GateQueReprovaUmaVez(name="Gate"),
        SaidaDeLoopAgent(name="Saida", status_keys=["gate_status"], rodada_key="r", max_rounds=3, autor_keys=["one_pager"]),
        autor,
    ])


def test_retrabalho_do_loop_corrige_por_trocas_sem_o_autor_reescrever():
    import agents.callbacks as cb

    pedidos = []

    async def editor(pedido, etapa, documentos, *, erros="", achados=""):
        pedidos.append(pedido)
        return _proposta(_NUMERO)

    with mock.patch.dict(os.environ, {"RETRABALHO_POR_TROCAS": "true"}), \
            mock.patch.object(cb, "PROPONENTE_DE_RETRABALHO", editor):
        final = asyncio.run(_rodar(_loop_de_retrabalho(), {"one_pager": ONE_PAGER}))
    # o modelo do autor não existe: se ele tivesse rodado, a execução teria quebrado
    assert final["one_pager"] == ONE_PAGER.replace("parecer de mais de 70%.", "parecer de cerca de 47%.")
    assert final["gate_status"] == "aprovado" and final["r"] == 2
    assert "a conta está errada" in pedidos[0] and "15 → 8" in pedidos[0]
    assert final["trocas_de_retrabalho"][0]["chave"] == "one_pager" and final["retrabalho_one_pager"] == ""


def test_retrabalho_estrutural_volta_ao_autor():
    import agents.callbacks as cb
    from agents.callbacks import retrabalhar_por_trocas

    async def editor(pedido, etapa, documentos, *, erros="", achados=""):
        return ed.Proposta(modo=ed.MODO_ESTRUTURAL, motivo="a seção inteira tem de ser outra")

    contexto = mock.Mock()
    contexto.state = {"one_pager": ONE_PAGER, "retrabalho_one_pager": "reescreva a seção 4 inteira"}
    with mock.patch.dict(os.environ, {"RETRABALHO_POR_TROCAS": "true"}), \
            mock.patch.object(cb, "PROPONENTE_DE_RETRABALHO", editor):
        assert asyncio.run(retrabalhar_por_trocas("one_pager")(contexto)) is None
    assert contexto.state["retrabalho_one_pager"] == "" and contexto.state["one_pager"] == ONE_PAGER
    # sem rodada de retrabalho (primeira rodada, geração normal), nada acontece
    contexto.state = {"one_pager": ONE_PAGER}
    with mock.patch.dict(os.environ, {"RETRABALHO_POR_TROCAS": "true"}):
        assert asyncio.run(retrabalhar_por_trocas("one_pager")(contexto)) is None


def test_design_inteiro_vai_ao_editor_inclusive_o_prototipo():
    prototipo = "<html><body>" + ("<div class='tela'>texto</div>\n" * 9000) + "<p>Etapa 5: mais de 70%</p></body></html>"
    estado = {"jornada_telas": "# Jornada\n\nE5: mais de 70%\n", "copy_strings_revisada": "E5-ALU-01: mais de 70%\n",
              "prototipo_html": prototipo, "wireframes_cobertura": "# Wireframes\n"}
    docs = ed.documentos_da_etapa(estado, "design")
    assert set(docs) == set(estado) and len(prototipo) > 250_000
    assert "grande demais" not in ed.renderizar(docs) and "<p>Etapa 5: mais de 70%</p>" in ed.renderizar(docs)
    r = ed.aplicar(docs, [ed.Edicao("prototipo_html", "<p>Etapa 5: mais de 70%</p>", "<p>Etapa 5: cerca de 47%</p>"),
                          ed.Edicao("copy_strings_revisada", "E5-ALU-01: mais de 70%", "E5-ALU-01: cerca de 47%")])
    assert r.ok and "cerca de 47%" in r.documentos["prototipo_html"]
    assert set(ed.travados("design")) >= set(estado)


# ------------------------------------------------------------------ o one-pager do PO não perde texto por troca
PO = ("# One-pager do PO\n\n## 12a. Contrato de evidência\n\n"
      "**Pergunta:** \"O que significa a palavra DECOMPOSIÇÃO que você usou na missão?\"\n\n"
      "## 9. Conceitos\n\nO estudante compara as duas notícias e decide qual publicar no mural da turma.\n")


def test_troca_que_apaga_texto_do_po_e_detectada():
    from tools.one_pager_po import perdidos_pela_edicao

    reescrita = PO.replace("O que significa a palavra DECOMPOSIÇÃO que você usou na missão?",
                           "Como você dividiu a notícia em partes?")
    assert perdidos_pela_edicao(PO, PO, reescrita) and "DECOMPOSIÇÃO" in perdidos_pela_edicao(PO, PO, reescrita)[0]
    com_proposta = PO.replace("missão?\"\n", "missão?\" [PROPOSTA — validar com PO: «Como você dividiu a notícia?»]\n")
    assert perdidos_pela_edicao(PO, PO, com_proposta) == []


def test_retrabalho_que_apagaria_o_texto_do_po_volta_ao_editor():
    import agents.callbacks as cb
    from agents.callbacks import retrabalhar_por_trocas

    pergunta = "**Pergunta:** \"O que significa a palavra DECOMPOSIÇÃO que você usou na missão?\""
    respostas = [
        _proposta(("one_pager", pergunta, "**Pergunta:** \"Como você dividiu a notícia em partes?\"")),
        _proposta(("one_pager", pergunta,
                   pergunta + " [PROPOSTA — validar com PO: «Como você dividiu a notícia em partes?»]")),
    ]
    erros = []

    async def editor(pedido, etapa, documentos, *, erros_="", achados="", **kw):
        erros.append(kw.get("erros", ""))
        return respostas[len(erros) - 1]

    async def editor_compat(pedido, etapa, documentos, *, erros="", achados=""):
        return await editor(pedido, etapa, documentos, erros=erros, achados=achados)

    contexto = mock.Mock()
    contexto.state = {"one_pager": PO, "one_pager_po": PO, "retrabalho_one_pager": "B1-1: a pergunta mede memória"}
    with mock.patch.dict(os.environ, {"RETRABALHO_POR_TROCAS": "true"}), \
            mock.patch.object(cb, "PROPONENTE_DE_RETRABALHO", editor_compat):
        conteudo = asyncio.run(retrabalhar_por_trocas("one_pager")(contexto))
    texto = conteudo.parts[0].text
    assert "DECOMPOSIÇÃO" in texto and "[PROPOSTA — validar com PO" in texto
    assert len(erros) == 2 and "foram recusadas" in erros[1] and "DECOMPOSIÇÃO" in erros[1]
