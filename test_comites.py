"""Comitês pedagógicos: três juízes votam, o código conta, e a correção volta a quem escreve a missão."""
import json

from tools import comite

DOC = ("O estudante curte os posts que acha confiáveis e salva os que vai mostrar à turma. "
       "No Decidir, ele escolhe três contas para seguir antes de ver o feed novo.")


def _rel(voto="aprova", achados=None, status=None):
    env = {"agente": "comite-canal-a-curriculo", "status": status or ("aprovado" if voto == "aprova" else "reprovado"),
           "voto": voto, "achados": achados or []}
    return f"# Juiz\n\n```json\n{json.dumps(env, ensure_ascii=False)}\n```"


BLOQ = {"id": "A1-1", "severidade": "bloqueio", "habilidade": "EF06CO01", "autor": "A004",
        "citacao": "O estudante curte os posts que acha confiáveis", "resumo": "curtir não é avaliar credibilidade",
        "o_que_corrigir": "a ação precisa separar fonte confiável de não confiável"}


def test_unanimidade_aprova():
    r = comite.consolidar({"j1": _rel(), "j2": _rel(), "j3": _rel()}, DOC, rodada=1, max_rodadas=5)
    assert r["status"] == "aprovado" and r["unanime"] and r["contra"] == 0


def test_um_voto_contra_reprova_e_volta_ao_autor():
    r = comite.consolidar({"j1": _rel(), "j2": _rel(), "j3": _rel("reprova", [BLOQ])}, DOC, rodada=1, max_rodadas=5)
    assert r["status"] == "bloqueado" and r["contra"] == 1
    assert [a["id"] for a in r["por_autor"]["A004"]] == ["A1-1"]


def test_envelope_ausente_conta_como_reprova():
    r = comite.consolidar({"j1": _rel(), "j2": _rel(), "j3": "o juiz respondeu sem envelope"}, DOC)
    assert r["status"] == "bloqueado"
    assert r["votos"]["j3"]["achados"][0]["codigo"] == "juiz-sem-voto"


def test_citacao_inexistente_rebaixa_e_o_voto_vira_aprovacao():
    inventada = {**BLOQ, "citacao": "o estudante vota numa enquete pública da turma"}
    r = comite.consolidar({"j1": _rel(), "j2": _rel(), "j3": _rel("reprova", [inventada])}, DOC)
    assert r["status"] == "aprovado"
    codigos = {a.get("codigo") for a in r["achados"]}
    assert "voto-sem-achado-verificavel" in codigos
    assert any(a.get("citacao_nao_confere") for a in r["achados"])


def test_juiz_que_aprova_com_bloqueio_citado_reprova():
    r = comite.consolidar({"j1": _rel("aprova", [BLOQ]), "j2": _rel(), "j3": _rel()}, DOC)
    assert r["status"] == "bloqueado"


def test_teto_sem_unanimidade_segue_com_amarelo():
    r = comite.consolidar({"j1": _rel(), "j2": _rel("reprova", [BLOQ]), "j3": _rel()}, DOC, rodada=5, max_rodadas=5)
    assert r["status"] == "amarelo"
    texto = comite.relatorio(r, "Comitê dos canais — painel A", {"j1": "Currículo", "j2": "Medida", "j3": "Vivência"})
    assert "🟡 SEM UNANIMIDADE NO TETO" in texto and "Votos vencidos no teto" in texto


def test_achados_agrupados_por_autor_no_relatorio():
    apoio = {**BLOQ, "id": "A2-1", "autor": "seções de apoio", "habilidade": "EF06CO03",
             "citacao": "salva os que vai mostrar à turma"}
    r = comite.consolidar({"j1": _rel("reprova", [BLOQ]), "j2": _rel("reprova", [apoio]), "j3": _rel()}, DOC)
    assert set(r["por_autor"]) == {"A004", "A014"}
    texto = comite.relatorio(r, "Comitê", {"j1": "Currículo", "j2": "Medida", "j3": "Vivência"}, "exp01ef6b")
    assert texto.index("### Para o núcleo narrativo (A004)") < texto.index("### Para as seções de apoio (A014)")
    env = comite.envelope(r)
    assert env["status"] == "bloqueado" and env["votos"] == {"j1": "reprova", "j2": "reprova", "j3": "aprova"}


def test_relatorio_tem_envelope_legivel_pelo_inferir_status():
    from agents.callbacks import extrair_envelope, inferir_status

    r = comite.consolidar({"j1": _rel("reprova", [BLOQ]), "j2": _rel(), "j3": _rel()}, DOC)
    texto = comite.relatorio(r, "Comitê", {})
    assert inferir_status(texto, extrair_envelope(texto)) == "bloqueado"


# --------------------------------------------------------------------------- loops no ADK
import asyncio
from typing import AsyncGenerator

from google.adk.agents import LoopAgent, ParallelAgent
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.runners import InMemoryRunner
from google.genai import types
from typing_extensions import override

from agents.checkers import ComiteVotosAgent, LoopIsolado, SaidaDeLoopAgent, chaves_de_rodada, isolar


class _Falso(BaseAgent):
    """Grava um texto no estado (como faria output_key) e conta quantas vezes rodou."""

    key: str
    text: str
    marker_key: str = ""

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        delta = {self.key: self.text}
        if self.marker_key:
            delta[self.marker_key] = int(ctx.session.state.get(self.marker_key, 0) or 0) + 1
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    content=types.Content(role="model", parts=[types.Part(text=self.text[:40])]),
                    actions=EventActions(state_delta=delta))


async def _rodar(root: BaseAgent):
    runner = InMemoryRunner(agent=root, app_name="teste")
    session = await runner.session_service.create_session(app_name="teste", user_id="u", session_id="s")
    async for _ in runner.run_async(user_id="u", session_id=session.id,
                                    new_message=types.Content(role="user", parts=[types.Part(text="go")])):
        pass
    final = await runner.session_service.get_session(app_name="teste", user_id="u", session_id="s")
    return dict(final.state)


def _loop_interno(gate: str) -> LoopAgent:
    return LoopAgent(name="Interno", max_iterations=2, sub_agents=[
        _Falso(name="Autor", key="doc", text=DOC, marker_key="escritas"),
        _Falso(name="GateInterno", key="gate_status", text=gate),
        SaidaDeLoopAgent(name="SaidaInterna", status_keys=["gate_status"], rodada_key="interno_rodada", max_rounds=2),
    ])


def _loop_externo(interno: BaseAgent) -> LoopAgent:
    return LoopAgent(name="Externo", max_iterations=3, sub_agents=[
        interno,
        _Falso(name="Juiz", key="juiz_status", text="bloqueado"),
        SaidaDeLoopAgent(name="SaidaExterna", status_keys=["juiz_status"], rodada_key="externo_rodada", max_rounds=3),
    ])


def test_sem_isolar_a_saida_do_loop_interno_encerra_o_externo():
    """O defeito que o `LoopIsolado` existe para evitar — se este teste falhar, o ADK mudou e o isolador sobra."""
    state = asyncio.run(_rodar(_loop_externo(_loop_interno("aprovado"))))
    assert state["escritas"] == 1 and "externo_rodada" not in state


def test_loop_isolado_deixa_o_externo_dar_todas_as_voltas():
    state = asyncio.run(_rodar(_loop_externo(isolar(_loop_interno("aprovado")))))
    assert state["externo_rodada"] == 3
    assert state["escritas"] == 3, "o autor do loop interno roda uma vez por volta do externo"


def test_loop_isolado_zera_os_contadores_do_interno_a_cada_volta():
    # gate interno sempre reprova: 2 rodadas internas por volta. Sem zerar, a 2ª volta entraria esgotada (1 rodada).
    state = asyncio.run(_rodar(_loop_externo(isolar(_loop_interno("bloqueado")))))
    assert state["escritas"] == 6
    assert state["interno_rodada"] == 2


def test_chaves_de_rodada_percorrem_a_arvore():
    assert chaves_de_rodada(_loop_externo(isolar(_loop_interno("aprovado")))) == ["interno_rodada", "externo_rodada"]


def _comite(j3: str, max_rodadas: int = 5) -> LoopAgent:
    return LoopAgent(name="ComiteLoop", max_iterations=max_rodadas, sub_agents=[
        _Falso(name="Autor", key="one_pager", text=DOC, marker_key="escritas"),
        ParallelAgent(name="Painel", sub_agents=[
            _Falso(name="J1", key="j1", text=_rel()), _Falso(name="J2", key="j2", text=_rel()),
            _Falso(name="J3", key="j3", text=j3)]),
        ComiteVotosAgent(name="Votos", fontes={"j1": "Currículo", "j2": "Medida", "j3": "Vivência"},
                         report_key="comite_canal_a_report", status_key="comite_canal_a_status",
                         round_key="comite_canal_a_rodada", max_rounds=max_rodadas),
        SaidaDeLoopAgent(name="Saida", status_keys=["comite_canal_a_status"], rodada_key="comite_canais_rodada",
                         max_rounds=max_rodadas, autor_keys=["one_pager"]),
    ])


def test_comite_unanime_sai_na_primeira_rodada():
    state = asyncio.run(_rodar(_comite(_rel())))
    assert state["comite_canal_a_status"] == "aprovado" and state["escritas"] == 1
    assert state["rodada_anterior_one_pager"] == ""


def test_comite_sem_unanimidade_devolve_ao_autor_ate_o_teto_e_segue_com_amarelo():
    state = asyncio.run(_rodar(_comite(_rel("reprova", [BLOQ]))))
    assert state["escritas"] == 5, "o autor reescreve a cada rodada reprovada, até o teto de 5"
    assert state["comite_canal_a_rodada"] == 5
    assert state["comite_canal_a_status"] == "amarelo"
    assert "Para o núcleo narrativo (A004)" in state["comite_canal_a_report"]


# --------------------------------------------------------------------------- Canal A em toda habilidade
from tools import evidencia

_SPEC = ("# Spec — `id: exp06ef1b`\n## 9. Evidências\n"
         "| Medida | Grau | Sinais | Canal | Tabela.coluna | Habilidade |\n|---|---|---|---|---|---|\n"
         "| `posts` | `scored` | `a:b` + `c:d` | operacional | `exp06ef1b_sessoes.p` | `EF06CO09` |\n"
         "- `gabarito_servidor: sim`\n## 11. Currículo\n"
         "| Código | Momento em tela | Ação observável | O que não conta | Medida do bloco 9 | Canal de evidência | Regra ternária |\n"
         "|---|---|---|---|---|---|---|\n| `EF06CO09` | `E3-ALU-02` | fixa | rola | `posts` | {canal} | "
         "Atingiu: fixa com fonte · Em processo: fixa sem fonte · Não atingiu: não fixa |\n")


def test_spec_com_canal_b_bloqueia():
    """O Canal B saiu da missão por decisão do PO (29/10/2026): só `A` passa; `B` e `A + B` bloqueiam."""
    assert evidencia.validar(_SPEC.format(canal="A"))["status"] == "aprovado"
    for canal in ("A + B", "B"):
        r = evidencia.validar(_SPEC.format(canal=canal))
        assert r["status"] == "bloqueado"
        assert [a["codigo"] for a in r["achados"]] == ["canal-b-removido"]


_REGRA = "**Regra:** • **Atingiu:** fixa com fonte • **Em processo:** fixa sem fonte • **Não atingiu:** não fixa"
_B = ('Pergunta: "Qual post você mostraria à turma?" • **Atingiu:** "o que cita a fonte" • **Em processo:** '
      '"o mais curtido" • **Não atingiu:** "o mais engraçado" · Componente: `PollCard`')


def _one_pager(linhas: str, s2: str = "`EF06CO09` e `EF06CO01`") -> str:
    return (f"# One-pager\n## 2. Currículo\n- {s2}\n## 12. Evidências e dados\n- capturado\n"
            f"### 12a. Contrato de evidência por habilidade\n\n{evidencia.CABECALHO_12A}\n|---|---|---|\n{linhas}\n"
            f"## 13. Professor\n- conduz\n")


def test_12a_completo_aprova():
    op = _one_pager(f"| `EF06CO09` (Foco Primário) | A | {_REGRA} |\n| `EF06CO01` | `A` | {_REGRA} |")
    r = evidencia.conferir_one_pager(op)
    assert r["status"] == "aprovado", r["achados"]


def test_12a_cobra_regra_ternaria_e_proibe_o_canal_b():
    op = _one_pager(f"| `EF06CO09` | A + B | ação sem regra |\n| `EF06CO01` | B | {_REGRA} |")
    codigos = sorted(a["codigo"] for a in evidencia.conferir_one_pager(op)["achados"])
    assert codigos == ["canal-b-removido", "canal-b-removido", "regra-ternaria-ausente"]
    # o one-pager antigo, com a coluna do Canal B preenchida, também bloqueia
    largo = (f"# One-pager\n## 2. Currículo\n- `EF06CO09`\n## 12. Evidências\n### 12a. Contrato\n\n"
             f"| Habilidade (código) | Canal de evidência | Canal A: ação | Canal B: pergunta |\n|---|---|---|---|\n"
             f"| `EF06CO09` | A | {_REGRA} | {_B} |\n## 13. Professor\n")
    assert [a["codigo"] for a in evidencia.conferir_one_pager(largo)["achados"]] == ["canal-b-removido"]


def test_12a_cobra_toda_habilidade_da_secao_2():
    op = _one_pager(f"| `EF06CO09` | A | {_REGRA} |")
    assert [a["codigo"] for a in evidencia.conferir_one_pager(op)["achados"]] == ["habilidade-sem-contrato"]


def test_12a_aceita_uma_linha_por_canal():
    """O formato da exp09ef1b: «| Habilidade | Canal | Evento | Campo | Regra |», uma linha por canal."""
    op = ("# One-pager\n## 2. Currículo\n- `EF09CO07`\n## 12. Evidências\n### 12a. Contrato de evidência por habilidade\n\n"
          "| Habilidade | Canal | Evento registrado | Campo | Regra ternária de cálculo no servidor |\n|---|---|---|---|---|\n"
          f"| `EF09CO07` | **Canal A** | `submit_decidir` | `opcao` | {_REGRA} |\n## 13. Professor\n")
    assert evidencia.conferir_one_pager(op)["status"] == "aprovado"
    com_b = op.replace("## 13. Professor", f"| `EF09CO07` | **Canal B** | `submit_poll` | `opcao` | {_B} |\n## 13. Professor")
    assert [a["codigo"] for a in evidencia.conferir_one_pager(com_b)["achados"]] == ["canal-b-removido"]


def test_12a_ausente_ou_sem_tabela_bloqueia():
    assert [a["codigo"] for a in evidencia.conferir_one_pager("## 2. X\n## 12. Y\n- nada")["achados"]] == ["12a-ausente"]
    sem_tabela = "## 2. X\n## 12. Y\n### 12a. Contrato\n- EF06CO09: canal A\n"
    assert [a["codigo"] for a in evidencia.conferir_one_pager(sem_tabela)["achados"]] == ["12a-sem-tabela"]


def test_rastro_check_no_modo_evidencia_one_pager_grava_status_e_relatorio():
    from agents.checkers import RastroCheckAgent
    from google.adk.agents import SequentialAgent

    root = SequentialAgent(name="R", sub_agents=[
        _Falso(name="OnePager", key="one_pager", text=_one_pager(f"| `EF06CO09` | B | — |", "`EF06CO09`")),
        RastroCheckAgent(name="A0xxEvidenciaOnePager", modo="evidencia_one_pager", rotulo="Contrato de evidência (§12a)",
                         report_key="evidencia_one_pager_report", status_key="evidencia_one_pager_status", estrito=False),
    ])
    state = asyncio.run(_rodar(root))
    assert state["evidencia_one_pager_status"] == "bloqueado"
    assert "canal-b-removido" in state["evidencia_one_pager_report"]


# --------------------------------------------------------------------------- callbacks dos comitês
class _Ctx:
    """O que os callbacks usam do CallbackContext: o estado."""

    def __init__(self, state):
        self.state = state


def test_nucleo_so_e_mantido_quando_nenhum_comite_aponta_para_o_a004():
    from agents.callbacks import manter_nucleo_sem_achado_do_a004 as manter

    def env(*autores):
        return {"status": "bloqueado", "achados": [{"severidade": "bloqueio", "autor": a} for a in autores]}

    base = {"nucleo_narrativo": "# Núcleo", "evidencia_one_pager_status": "aprovado"}
    assert manter(_Ctx({**base, "comite_canal_a_status_envelope": env("A014")})) is not None
    assert manter(_Ctx({**base, "comite_canal_a_status_envelope": env("A014", "A004")})) is None
    assert manter(_Ctx({**base, "comite_final_status_envelope": env("")})) is None, "sem autor: o núcleo roda"
    assert manter(_Ctx(base)) is None, "primeira passada: nenhum comitê reprovou"
    assert manter(_Ctx({**base, "evidencia_one_pager_status": "bloqueado",
                        "comite_canal_a_status_envelope": env("A014")})) is None, "§12a fora de forma: o núcleo roda"
    assert manter(_Ctx({"comite_canal_a_status_envelope": env("A014")})) is None, "sem núcleo ainda: roda"


# --------------------------------------------------------------------------- a fábrica, de ponta a ponta
class _JuizFalso(BaseAgent):
    """Reprova até o one-pager chegar à versão `aprova_na`, com um achado para `autor`."""

    key: str
    aprova_na: int = 1
    autor: str = "A014"

    @override
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        versao = int(ctx.session.state.get("versao_one_pager", 0) or 0)
        texto = _rel() if versao >= self.aprova_na else _rel("reprova", [{**BLOQ, "autor": self.autor}])
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    actions=EventActions(state_delta={self.key: texto}))


def test_comites_da_fabrica_devolvem_a_missao_a_quem_a_escreve(monkeypatch):
    """O painel A reprova a 1ª versão por um achado do A014; o comitê final reprova a 2ª por um do A004.

    O núcleo só reescreve quando há achado para ele; a cadeia inteira roda de novo quando o comitê final reprova; e a
    missão termina aprovada pelos dois comitês."""
    from google.adk.agents import SequentialAgent

    from agents import comite as fabrica
    from agents.checkers import DocumentoObrigatorioAgent

    regras = {"comite_canal_a_medida": (2, "A014"), "comite_final_qualidade": (3, "A004")}

    def juizes(painel, numero, letras, **kw):
        return [_JuizFalso(name=f"A{numero:03d}{letra}Falso", key=chave, aprova_na=regras.get(chave, (1,))[0],
                           autor=regras.get(chave, (1, "A014"))[1])
                for letra, (_, _, chave, _, _) in zip(letras, fabrica.JUIZES[painel])]

    monkeypatch.setattr(fabrica, "_juizes", juizes)
    one_pager = (_one_pager(f"| `EF06CO09` | A | {_REGRA} |", "`EF06CO09`") + DOC
                 + "\n### 1.3 Conta da virada\n**Não se aplica:** a missão não tem recomendação de máquina nem ranking.\n")

    def loop_simples(nome, chave, marcador):
        return LoopAgent(name=nome, max_iterations=1, sub_agents=[_Falso(name=f"{nome}G", key=chave, text="aprovado",
                                                                          marker_key=marcador)])

    nucleo = LoopAgent(name="NucleoNarrativoLoop", max_iterations=2, sub_agents=[
        _Falso(name="A004Falso", key="nucleo_narrativo", text=DOC, marker_key="escritas_nucleo"),
        _Falso(name="MicroGateFalso", key="micro_gate_status", text="aprovado"),
        SaidaDeLoopAgent(name="A013Falso", status_keys=["micro_gate_status"], rodada_key="nucleo_rodada", max_rounds=2)])
    apoio = LoopAgent(name="SecoesApoioLoop", max_iterations=2, sub_agents=[
        _Falso(name="A014Falso", key="one_pager", text=one_pager, marker_key="versao_one_pager"),
        _Falso(name="PoFalso", key="one_pager_po_status", text="aprovado"),
        SaidaDeLoopAgent(name="A016Falso", status_keys=["one_pager_po_status"], rodada_key="secoes_apoio_rodada",
                         max_rounds=2, autor_keys=["one_pager"])])
    canais = fabrica.build_comite_canais_loop(
        [nucleo, apoio, DocumentoObrigatorioAgent(name="A017Falso", chave="one_pager", autor="A014Falso")])
    final = fabrica.build_comite_final_loop([
        canais, loop_simples("GateEstruturalLoop", "gate_estrutural_status", "passadas_gate"),
        loop_simples("AvaliacoesLoop", "avaliacao_status", ""), loop_simples("OnePagerPoLoop", "one_pager_po_rodada_ok", "")])
    state = asyncio.run(_rodar(SequentialAgent(name="Produto", sub_agents=[final])))

    assert state["comite_canal_a_status"] == "aprovado" and state["comite_final_status"] == "aprovado"
    assert state["versao_one_pager"] == 3, "as seções de apoio reescreveram a cada reprovação"
    assert state["escritas_nucleo"] == 2, "o núcleo pulou a rodada do achado do A014 e reescreveu na do A004"
    assert state["passadas_gate"] == 2, "o comitê final reprovado refez a cadeia de produto"
    # o one-pager deste teste não tem fichas de interação na seção 4: a mecânica sai 🟡 só por isso (29/10/2026)
    assert state["evidencia_one_pager_status"] == "aprovado" and state["mecanica_one_pager_status"] in ("aprovado",
                                                                                                         "amarelo")


def test_teto_do_comite_nao_recusa_o_de_acordo_e_o_12a_fora_de_forma_recusa():
    from pipeline.passagem import AGUARDANDO, DE_ACORDO, acoes_possiveis

    fluxo = {"etapa": "produto", "situacao": AGUARDANDO}
    amarelo = {"comite_canal_a_status": "amarelo", "comite_final_status": "amarelo",
               "evidencia_one_pager_status": "aprovado"}
    assert DE_ACORDO in acoes_possiveis(fluxo, "produto", amarelo)
    vermelho = {**amarelo, "evidencia_one_pager_status": "bloqueado"}
    assert DE_ACORDO not in acoes_possiveis(fluxo, "produto", vermelho)
