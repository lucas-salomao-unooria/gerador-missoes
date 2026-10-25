"""C5 do backlog de deficiências (24/10/2026): infra da esteira — envelope fora do documento, catálogo e diagnóstico fiéis
ao parecer humano, histórico por rodada dos gates, rota dos achados, ajuste exigido à vista, decisão do refazer e
aprendizado conferido.

Os casos são os do levantamento (`analises-esteira/2026-10-24/deficiencias/{produto,design,dev}`), com os estados do
acervo (`tests/acervo`) ou, quando a sessão não está nele, o trecho do estado bruto copiado aqui com a data. Cada item tem
o mutante que o teste pega: a correção desligada faz o teste falhar.
"""
from __future__ import annotations

import asyncio
import copy
import json
import warnings
from pathlib import Path
from typing import Any, Dict, List

import pytest
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.loop_agent import LoopAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.events import Event, EventActions
from google.adk.runners import InMemoryRunner
from google.genai import types
from typing_extensions import override

from agents.callbacks import extrair_envelope
from tools import aprendizado, catalogo, diagnostico, liberacao, rota_achados
from tools import fechar_contrato as fc
from tools import historico_gates as hg
from tools.envelope_relatorio import categoria_do_envelope, concordam, envelope_do_gate, relatorio_com_envelope

warnings.filterwarnings("ignore", category=DeprecationWarning)

ACERVO = Path(__file__).resolve().parent / "tests" / "acervo"


def _estado(missao: str) -> Dict[str, Any]:
    return json.loads((ACERVO / missao / "estado.json").read_text(encoding="utf-8"))


async def _executar(raiz: BaseAgent, estado: Dict[str, Any]) -> Dict[str, Any]:
    runner = InMemoryRunner(agent=raiz, app_name="t")
    await runner.session_service.create_session(app_name="t", user_id="u", session_id="s", state=estado)
    async for _ in runner.run_async(user_id="u", session_id="s",
                                    new_message=types.Content(role="user", parts=[types.Part(text="go")])):
        pass
    final = await runner.session_service.get_session(app_name="t", user_id="u", session_id="s")
    return dict(final.state)


def _rodar(agente: BaseAgent, estado: Dict[str, Any]) -> Dict[str, Any]:
    return asyncio.run(_executar(SequentialAgent(name="R", sub_agents=[agente]), copy.deepcopy(estado)))


# =========================================================================== 1. envelope fora do one-pager resumido
ASSINATURA_RESUMIDO = '"agente": "one-pager-resumido"'
COM_RESUMIDO = [p.parent.name for p in sorted(ACERVO.glob("*/estado.json"))
                if (json.loads(p.read_text(encoding="utf-8")).get("one_pager_resumido") or "").strip()]


def test_o_resumido_de_cada_sessao_do_acervo_termina_no_envelope():
    """O defeito existe: nas sessões do acervo o resumido termina no envelope do agente (24/10/2026: 15 de 15 no bucket)."""
    assert len(COM_RESUMIDO) >= 14
    for missao in COM_RESUMIDO:
        texto = _estado(missao)["one_pager_resumido"]
        assert ASSINATURA_RESUMIDO in texto[-400:], missao


@pytest.mark.parametrize("missao", COM_RESUMIDO)
def test_o_resumido_gravado_sai_sem_o_envelope(missao):
    from pipeline.artifacts import documento_para_gravar

    estado = _estado(missao)
    gravado = documento_para_gravar(estado, "one_pager_resumido")
    assert ASSINATURA_RESUMIDO not in gravado and "```json" not in gravado[-300:]
    assert not gravado.rstrip().endswith("---"), "a divisória que anunciava o envelope sai junto"
    # o resto do documento fica como estava
    assert estado["one_pager_resumido"].startswith(gravado.rstrip())


def test_md_html_e_docx_do_resumido_sem_o_envelope(tmp_path, monkeypatch):
    """O `.md` que o time de produto lê e as exportações: o `.html` e o `.docx` já filtravam pelo `markdown_blocos`, o
    `.md` não (`pipeline/artifacts.py`, 24/10/2026)."""
    from pipeline.artifacts import save_run_artifacts

    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "saida"))
    estado = {k: v for k, v in _estado("exp02ef1b-4fd72a9a").items() if k in ("one_pager_resumido", "spec_missao")}
    pasta = save_run_artifacts(estado, "s", run_dir=tmp_path / "sessao")
    md = (pasta / "produto/00d-one-pager-resumido.md").read_text(encoding="utf-8")
    html = (pasta / "produto/00d-one-pager-resumido.html").read_text(encoding="utf-8")
    assert ASSINATURA_RESUMIDO not in md and "one-pager-resumido&quot;" not in html and "habilidades_pendentes" not in html
    assert (pasta / "produto/00d-one-pager-resumido.docx").exists()


def test_json_citado_no_corpo_e_envelope_sem_assinatura_ficam():
    from pipeline.artifacts import sem_envelope_do_agente

    citado = "# Resumido\n\n```json\n{\"agente\": \"x\", \"status\": \"y\"}\n```\n\nO texto continua depois.\n"
    assert sem_envelope_do_agente(citado) == citado
    sem_assinatura = "# Resumido\n\nTexto.\n\n```json\n{\"status\": \"concluido\"}\n```\n"
    assert sem_envelope_do_agente(sem_assinatura) == sem_assinatura


def test_o_callback_do_autor_tira_o_envelope_do_estado():
    """O resumido entra no estado sem o envelope: a correção pontual e o refazer o recebem limpo como base."""
    from agents.callbacks import tirar_envelope_do_documento
    from agents.produto import get_one_pager_resumido_agent

    class Ctx:
        def __init__(self, state):
            self.state = state

    texto = _estado("exp05ef1b")["one_pager_resumido"]
    ctx = Ctx({"one_pager_resumido": texto})
    tirar_envelope_do_documento("one_pager_resumido")(ctx)
    assert ASSINATURA_RESUMIDO not in ctx.state["one_pager_resumido"]
    callbacks = get_one_pager_resumido_agent().after_agent_callback
    callbacks = callbacks if isinstance(callbacks, list) else [callbacks]
    assert any(getattr(c, "__name__", "") == "tirar_envelope_one_pager_resumido" for c in callbacks)


def test_mutante_sem_o_filtro_o_envelope_volta(monkeypatch):
    import pipeline.artifacts as art

    monkeypatch.setattr(art, "DOCUMENTOS_SEM_ENVELOPE", ())
    assert ASSINATURA_RESUMIDO in art.documento_para_gravar(_estado("exp05ef1b"), "one_pager_resumido")


# =========================================================================== 2 e 3. catálogo e diagnóstico × parecer
#: Os pareceres da exp02ef1b (4fd72a9a) como estavam no conversa.json em 23/10/2026: o admin liberou o design com
#: exceção às 15:57:54 vendo o QA de entregáveis e o D0 em 🔴 (só os gates em 🔴 do semáforo gravado).
PARECERES_4FD72A9A = [
    {"etapa": "produto", "acao": "de_acordo", "autor": "design", "como": "design (como Produto)",
     "quando": "22/10/2026 15:27:27", "valido": True, "gates": {}},
    {"etapa": "design", "acao": "refazer", "autor": "admin", "como": "admin (como Design)",
     "quando": "23/10/2026 15:42:14", "valido": True,
     "gates": {"design_status": "🔴", "fidelidade_design_status": "🔴", "lacunas_status": "🔴"}},
    {"etapa": "design", "acao": "excecao", "autor": "admin", "como": "admin (como Design)",
     "quando": "23/10/2026 15:57:54", "valido": True,
     "gates": {"design_status": "🔴", "lacunas_status": "🔴", "fidelidade_design_status": "🟡"}},
]


def test_r13_o_dev_comeca_sem_a_reprovacao_que_o_admin_liberou():
    """4fd72a9a, 23/10/2026: o dev rodou com `pipeline_bloqueado` e «QA de entregáveis (design) reprovado» herdados da
    exceção do admin, e o conversa.json gravou `status: blocked`. Agora a etapa começa com a liberação no estado."""
    from pipeline.reexecucao import _com_liberacoes, preparar_estado

    estado = _estado("exp02ef1b-4fd72a9a")
    assert estado["pipeline_bloqueado"] and estado["pipeline_bloqueio_motivo"] == "QA de entregáveis (design) reprovado"
    limpo, _ = preparar_estado(estado, "dev")
    conversa = {"fluxo": {"etapa": "dev", "situacao": "gerando", "versao": 9, "pareceres": PARECERES_4FD72A9A}}
    _com_liberacoes(limpo, conversa)
    assert limpo["pipeline_bloqueado"] is False and limpo["pipeline_bloqueio_motivo"] == ""
    assert limpo["degradacoes"] == [] and limpo["heranca_degradada"] == ""
    [lib] = limpo[liberacao.KEY_LIBERADAS]
    assert lib["gate"] == "QA de entregáveis (design)" and lib["acao"] == "excecao" and lib["quando"].startswith("23/10")
    # de novo, sem mudar nada: idempotente
    antes = copy.deepcopy(limpo)
    _com_liberacoes(limpo, conversa)
    assert limpo == antes


def test_r13_mutantes_parecer_invalido_e_vermelho_nao_visto_continuam_bloqueando():
    from pipeline.reexecucao import _com_liberacoes, preparar_estado

    limpo, _ = preparar_estado(_estado("exp02ef1b-4fd72a9a"), "dev")
    invalido = copy.deepcopy(PARECERES_4FD72A9A)
    invalido[-1]["valido"] = False  # um refazer de design o invalidou
    _com_liberacoes(limpo, {"fluxo": {"etapa": "dev", "situacao": "gerando", "pareceres": invalido}})
    assert limpo["pipeline_bloqueado"] is True
    limpo, _ = preparar_estado(_estado("exp02ef1b-4fd72a9a"), "dev")
    sem_ver = copy.deepcopy(PARECERES_4FD72A9A)
    sem_ver[-1]["gates"]["lacunas_status"] = "🟡"  # o D0 ficou vermelho depois da exceção, sem ninguém ver
    _com_liberacoes(limpo, {"fluxo": {"etapa": "dev", "situacao": "gerando", "pareceres": sem_ver}})
    assert limpo["pipeline_bloqueado"] is True and limpo["degradacoes"]


def test_r12_diagnostico_e_catalogo_seguem_a_excecao_e_o_de_acordo():
    """60cfa7f4 (exp02em1b, 22/10/2026): «🔴 há impedimentos · 4 impedimento(s)» com a exceção do admin no design e o de
    acordo de dev, e o catálogo registrou `bloqueada`. O estado do acervo traz os pareceres que a rodada final copiou."""
    estado = _estado("exp02em1b-60cfa7f4")
    d = diagnostico.coletar(estado)
    assert d["veredito"] == "amarelo" and d["bloqueios"] == [] and len(d["liberadas"]) == 1
    qa = next(g for g in d["gates"] if g["rotulo"] == "QA de entregáveis")
    assert qa["icone"] == "🔴" and qa["liberado"].startswith("liberação com exceção — admin")
    texto = diagnostico.relatorio_markdown(d, "exp02em1b", state=estado)
    assert "Reprovações que uma pessoa liberou no parecer" in texto and "há impedimentos" not in texto
    assert diagnostico.envelope(d)["liberadas_por_pessoa"] == 1
    ficha = catalogo.ficha_da_execucao(estado)
    assert ficha["status"] == "em criação" and ficha["parecer_humano"] == "dev: de acordo — dev, 22/10/2026 13:48:49"
    assert "Parecer humano em vigor" in catalogo.relatorio_markdown({"ficha": ficha, "total": 1})


def test_r12_mutante_sem_os_pareceres_volta_a_bloquear():
    estado = {k: v for k, v in _estado("exp02em1b-60cfa7f4").items() if k != "pareceres_humanos"}
    assert diagnostico.coletar(estado)["veredito"] == "bloqueado"
    assert catalogo.ficha_da_execucao(estado)["status"] == "bloqueada"


def test_vermelho_depois_do_de_acordo_continua_impedimento():
    """exp01ef1b (4e6cf385): o de acordo de dev é de 05/10 sem 🔴; o dev rodou de novo em 07/10 e reprovou telemetria,
    PRD e KPI sem parecer novo. Ninguém viu esses 🔴: a missão segue bloqueada."""
    estado = _estado("exp01ef1b")
    assert diagnostico.coletar(estado)["veredito"] == "bloqueado"
    assert catalogo.ficha_da_execucao(estado)["status"] == "bloqueada"


def test_r03_de_acordo_para_codificacao_nao_registra_bloqueada():
    """8ce9c32d (exp04ef1b, 25/09/2026): «Registrada como: `bloqueada`» depois do «De acordo para codificacao». A
    reprovação que sustentava o bloqueio era do rastro de dev, que estava 🟡 no semáforo quando o PO deu de acordo."""
    estado = {"pipeline_bloqueado": True, "gate_final_status": "amarelo", "rastro_lacunas_status": "amarelo",
              "degradacoes": [{"gate": "Rastro de lacunas antes do PRD",
                               "motivo": "Rastro de lacunas antes do PRD reprovado (4 lacuna(s))"}],
              "pareceres_humanos": [
                  {"etapa": "dev", "acao": "refazer", "autor": "dev", "como": "dev", "quando": "25/09/2026 15:44:32",
                   "valido": True, "gates": {"kpis_status": "🔴", "rastro_lacunas_status": "🔴"}},
                  {"etapa": "dev", "acao": "de_acordo", "autor": "dev", "como": "dev", "quando": "25/09/2026 16:14:33",
                   "valido": True, "gates": {"kpis_status": "🟢", "rastro_lacunas_status": "🟡"}}]}
    assert liberacao.bloqueada(estado) is False
    assert catalogo.ficha_da_execucao(estado)["status"] == "em criação"
    assert liberacao.bloqueada({**estado, "pareceres_humanos": []}) is True


# =========================================================================== 4. envelope e relatório: fonte única
#: 8ce9c32d (exp04ef1b), estado de 25/09/2026 16:14: o relatório do rastro de dev gravado dizia 🟡 com 1 lacuna; o
#: envelope gravado continuava 🔴 com 4 (resumos encurtados).
_ACHADO_HUMANO = {"severidade": "decisao_humana", "classe": "aberto", "codigo": "humano", "agente_responsavel": "humano",
                  "documento": "spec da missão",
                  "resumo": "- Registro formal de decisões paramétricas sob responsabilidade do Product Owner"}
ENVELOPE_R03 = {"agente": "rastro-lacunas", "missao": "exp04ef1b", "rodada": 1, "status": "bloqueado",
                "veredito": "vermelho", "achados": [
                    _ACHADO_HUMANO,
                    {**_ACHADO_HUMANO, "agente_responsavel": "fluxo", "resumo": "- Homologação dos 6, 7, 8 ou 9 toques"},
                    {**_ACHADO_HUMANO, "resumo": "- Homologação dos limiares H1 (>50%) e H2 (>85%)"},
                    {"severidade": "bloqueio", "classe": "aberto", "codigo": "produto", "agente_responsavel": "produto",
                     "documento": "ambiente simulado", "resumo": "- Ratificação do teto de 25 a 35 palavras"}],
                "precisa_humano": True}
RELATORIO_R03 = ("# Rastro de lacunas antes do PRD — exp04ef1b\n\n**Veredito: 🟡 SÓ PENDÊNCIAS HUMANAS**\n\n"
                 "| ⛔ **humano** | spec da missão | `aberto` | dono: produto | - Registro formal |\n\n```json\n"
                 + json.dumps({"agente": "rastro-lacunas", "missao": "exp04ef1b", "rodada": 1,
                               "status": "apto_com_ressalvas", "veredito": "amarelo", "achados": [_ACHADO_HUMANO],
                               "precisa_humano": True}, ensure_ascii=False) + "\n```\n")


def test_r03_o_dossie_le_o_envelope_que_concorda_com_o_status():
    estado = {"rastro_lacunas_status": "amarelo", "rastro_lacunas_status_envelope": ENVELOPE_R03,
              "rastro_lacunas_report": RELATORIO_R03}
    assert not concordam(RELATORIO_R03, ENVELOPE_R03)
    env = envelope_do_gate(estado, "rastro_lacunas_status")
    assert env["status"] == "apto_com_ressalvas" and len(env["achados"]) == 1
    d = diagnostico.coletar(estado)
    rastro = next(g for g in d["gates"] if g["rotulo"] == "Rastro de lacunas")
    assert rastro["achados"] == 1, "eram as 4 do envelope velho"
    # sessão em que os dois concordam: o gravado, como sempre
    igual = {**estado, "rastro_lacunas_status": "bloqueado"}
    assert envelope_do_gate(igual, "rastro_lacunas_status") is ENVELOPE_R03


def test_linha_de_base_regrava_o_relatorio_com_o_envelope_novo():
    """e89e91b3 e 60cfa7f4 (21/10/2026): a linha de base rebaixou a fidelidade a 🟡 no status e no envelope, e o relatório
    seguiu com «**Veredito: 🔴**» e o envelope antigo no fim. Agora o relatório termina no envelope gravado."""
    from tools import linha_de_base

    citacao = "Canal B removido por completo das perguntas de encerramento da missão"
    envelope = {"agente": "fidelidade", "status": "bloqueado", "achados": [
        {"id": "F2", "severidade": "bloqueio", "codigo": "pedido-sem-prova", "citacao": citacao,
         "resumo": "o pedido do PO não aparece aplicado"}]}
    relatorio = ("# Fidelidade\n\n**Veredito: 🔴** · 1 item\n\n- F2 sem prova\n\n```json\n"
                 + json.dumps(envelope, ensure_ascii=False) + "\n```\n")
    estado = {"fidelidade_status": "bloqueado", "fidelidade_status_envelope": envelope, "fidelidade_report": relatorio}
    delta, linhas = linha_de_base.aplicar(estado, {}, [{"de": "texto antigo da etapa 3", "para": "texto novo"}],
                                          ["fidelidade_status"])
    assert delta["fidelidade_status"] == "amarelo" and linhas[0]["origem"] == linha_de_base.TEXTO_INALTERADO
    novo = delta["fidelidade_report"]
    assert extrair_envelope(novo) == delta["fidelidade_status_envelope"]
    assert concordam(novo, delta["fidelidade_status_envelope"]) and "**Veredito: 🟡" in novo and "Veredito: 🔴" not in novo
    assert "Linha de base da correção pontual" in novo
    # mutante: o comportamento de antes (só a nota no fim) deixa relatório e envelope discordando
    antigo = relatorio + "\n\n---\n> 📏 **Linha de base da correção pontual:** 1 bloqueio(s) rebaixados. Veredito: 🟡."
    assert not concordam(antigo, delta["fidelidade_status_envelope"])


def test_mapa_do_relatorio_cobre_cada_gate_da_arvore_do_orquestrador():
    """Cada par (status, relatório) dos agentes da árvore real ou bate com `relatorio_do_gate`, ou é de um gate sem
    relatório próprio. Na revisão do PR #83 (25/10/2026), `stitch_status` (relatório `prototipo_relatorio`) e
    `completude_status` divergiam."""
    from pipeline.orchestrator import create_mission_orchestrator
    from tools.envelope_relatorio import SEM_RELATORIO_PROPRIO, relatorio_do_gate

    pares: Dict[str, set] = {}

    def andar(agente):
        status = getattr(agente, "status_key", None)
        relatorio = getattr(agente, "report_key", None) or getattr(agente, "relatorio_key", None)
        if isinstance(status, str) and isinstance(relatorio, str) and relatorio:
            pares.setdefault(status, set()).add(relatorio)
        for filho in getattr(agente, "sub_agents", None) or []:
            andar(filho)

    andar(create_mission_orchestrator(stages=["produto", "design", "dev"]))
    assert len(pares) > 30
    divergem = {k: v for k, v in pares.items() if v != {relatorio_do_gate(k)} and k not in SEM_RELATORIO_PROPRIO}
    assert divergem == {}
    assert relatorio_do_gate("stitch_status") == "", "o prototipo_relatorio termina no envelope do protótipo, não no do Stitch"


def test_linha_de_base_sem_relatorio_proprio_mantem_a_nota_e_o_envelope_do_agente():
    """`completude_status`: o relatório é a resposta do agente. A nota «Veredito: 🟡» entra no fim, como na main, e o
    envelope do agente fica; sem a nota, relatório 🔴 com status 🟡 (revisão do PR #83)."""
    from tools import linha_de_base

    citacao = "Canal B removido por completo das perguntas de encerramento da missão"
    envelope = {"agente": "completude", "status": "bloqueado", "achados": [
        {"id": "C1", "severidade": "bloqueio", "codigo": "lacuna", "citacao": citacao, "resumo": "falta o Canal B"}]}
    do_agente = {"agente": "completude-agente", "status": "bloqueado"}
    relatorio = "# Completude\n\n**Veredito: 🔴**\n\n```json\n" + json.dumps(do_agente) + "\n```\n"
    estado = {"completude_status": "bloqueado", "completude_status_envelope": envelope, "completude_report": relatorio,
              "stitch_status": "bloqueado", "prototipo_relatorio": "# Protótipo\n\n```json\n{\"agente\": "
              "\"prototipo-navegavel\", \"status\": \"concluido\"}\n```\n",
              "stitch_status_envelope": {"agente": "stitch-cobertura", "status": "bloqueado", "achados": [
                  {"severidade": "bloqueio", "codigo": "stitch", "citacao": citacao, "resumo": "faltam telas"}]}}
    delta, _ = linha_de_base.aplicar(estado, {}, [{"de": "texto antigo da etapa 3", "para": "texto novo"}],
                                     ["completude_status", "stitch_status"])
    assert delta["completude_status"] == "amarelo"
    novo = delta["completude_report"]
    assert novo.startswith(relatorio) and novo.rstrip().endswith("Veredito: 🟡."), "a nota no fim"
    assert extrair_envelope(novo)["agente"] == "completude-agente", "o envelope do agente fica"
    assert "prototipo_relatorio" not in delta and "stitch_report" not in delta


def test_relatorio_com_envelope_sem_bloco_acrescenta_no_fim():
    novo = relatorio_com_envelope("# Gate\n\nSem envelope.\n", {"status": "amarelo", "achados": []}, "nota")
    assert novo.rstrip().endswith("```") and categoria_do_envelope(extrair_envelope(novo)) == "amarelo"


# =========================================================================== 5. histórico por rodada dos gates
def _rodada(n: int, status: str, codigos: List[str]) -> Dict[str, Any]:
    return {"gate_estrutural_report": f"# Gate estrutural — rodada {n}\n\n**Veredito: {status}**\n",
            "gate_estrutural_status": status, "gate_estrutural_rodada": n,
            "gate_estrutural_status_envelope": {"status": status, "achados": [
                {"codigo": c, "severidade": "bloqueio", "resumo": f"achado {c}", "citacao": "trecho"} for c in codigos]}}


def test_coletor_guarda_cada_rodada_e_nao_repete_relatorio():
    """O gate estrutural no teto (rodada 3) em 727a3c2d, 274a2e75, e3980485 e 76d9af6e: só a última rodada ficava."""
    c = hg.Coletor(["produto"], {"gate_estrutural_report": "# rodada da execução anterior"})
    c.observar("A026GateEstrutural", {"gate_estrutural_report": "# rodada da execução anterior"})  # igual: não repete
    r1, r2 = _rodada(1, "bloqueado", ["2.1"]), _rodada(2, "aprovado", [])
    for delta in ({"gate_estrutural_report": r1["gate_estrutural_report"]},
                  {k: v for k, v in r1.items() if k != "gate_estrutural_report"},
                  {"gate_estrutural_report": r2["gate_estrutural_report"]},
                  {k: v for k, v in r2.items() if k != "gate_estrutural_report"},
                  {"one_pager": "# documento não entra", "temp:x": "1"}):
        c.observar("autor", delta)
    execucao = c.execucao()
    tipos = [(r["tipo"], r["chave"]) for r in execucao["registros"]]
    assert tipos == [("relatorio", "gate_estrutural_report"), ("status", "gate_estrutural_status"),
                     ("rodada", "gate_estrutural_rodada"), ("relatorio", "gate_estrutural_report"),
                     ("status", "gate_estrutural_status"), ("rodada", "gate_estrutural_rodada")]
    historico = hg.acumular(None, execucao)
    vereditos = hg.rodadas_de(historico, "gate_estrutural_status")
    assert [v["status"] for v in vereditos] == ["bloqueado", "aprovado"]
    assert vereditos[0]["achados"][0]["codigo"] == "2.1" and "rodada 1" in execucao["registros"][0]["texto"]


def test_coletor_respeita_os_tetos(monkeypatch):
    monkeypatch.setattr(hg, "MAX_CARACTERES_RELATORIO", 10)
    monkeypatch.setattr(hg, "MAX_CARACTERES_POR_EXECUCAO", 15)
    monkeypatch.setattr(hg, "MAX_REGISTROS_POR_EXECUCAO", 3)
    c = hg.Coletor()
    c.observar("a", {"x_report": "a" * 50})
    c.observar("a", {"y_report": "b" * 50})
    c.observar("a", {"x_status": "aprovado", "y_status": "amarelo"})
    e = c.execucao()
    assert e["registros"][0]["cortado"] and len(e["registros"][0]["texto"]) == 10
    assert "texto" not in e["registros"][1] and e["registros"][1]["texto_omitido"]
    assert len(e["registros"]) == 3 and e["registros_omitidos"] == 1
    historico: List[Dict[str, Any]] = []
    for _ in range(hg.MAX_EXECUCOES + 3):
        historico = hg.acumular(historico, e)
    assert len(historico) == hg.MAX_EXECUCOES
    assert hg.acumular(historico, {"registros": []}) == historico, "execução sem gate não entra"


class _GateDeMentira(BaseAgent):
    """Um gate que reprova na primeira rodada e aprova na segunda, como o estrutural da e3980485."""

    @override
    async def _run_async_impl(self, ctx):
        n = int(ctx.session.state.get("gate_estrutural_rodada", 0) or 0) + 1
        delta = _rodada(n, "bloqueado" if n == 1 else "aprovado", ["2.1"] if n == 1 else [])
        yield Event(invocation_id=ctx.invocation_id, author=self.name, actions=EventActions(
            state_delta=delta, escalate=True if n == 2 else None))


def test_runner_grava_as_rodadas_no_estado_e_no_arquivo_da_sessao(tmp_path, monkeypatch):
    import pipeline.runner as runner_mod

    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "saida"))
    monkeypatch.setattr(runner_mod, "create_mission_orchestrator",
                        lambda **kw: LoopAgent(name="Laco", max_iterations=3, sub_agents=[_GateDeMentira(name="G")]))
    anterior = hg.acumular(None, {"inicio": "x", "registros": [{"tipo": "status", "chave": "a_status", "status": "x"}]})

    async def _rodar_runner():
        async for evento in runner_mod.run_orchestrator_pipeline_stream(
                prompt="p", stages=["produto"], initial_state={hg.KEY: anterior}, run_dir=tmp_path / "sessao",
                registrar_conversa=False, com_transversal=False):
            if evento["type"] == "pipeline_error":
                raise AssertionError(evento)

    asyncio.run(_rodar_runner())
    estado = json.loads((tmp_path / "sessao/estado.json").read_text(encoding="utf-8"))
    assert len(estado[hg.KEY]) == 2, "a execução anterior fica, a nova entra no fim"
    assert [v["status"] for v in hg.rodadas_de(estado[hg.KEY], "gate_estrutural_status")] == ["bloqueado", "aprovado"]
    assert estado["gate_estrutural_status"] == "aprovado", "o estado continua com o valor da última rodada"
    # o estado leva o resumo, sem os textos; o arquivo da sessão leva os textos (revisão do PR #83)
    assert not any("texto" in r for e in estado[hg.KEY] for r in e["registros"])
    assert hg.KEY_EXECUCAO_COMPLETA not in estado
    exportado = json.loads((tmp_path / "sessao" / hg.ARQUIVO).read_text(encoding="utf-8"))["execucoes"]
    assert [e.get("id") for e in exportado] == [e.get("id") for e in estado[hg.KEY]]
    textos = [r["texto"] for r in exportado[-1]["registros"] if r["tipo"] == "relatorio"]
    assert len(textos) == 2 and "rodada 1" in textos[0] and "rodada 2" in textos[1]
    # o arquivo regravado sem a execução corrente em mãos (artefatos refeitos depois) mantém os textos que já tinha
    from pipeline.artifacts import save_run_artifacts

    save_run_artifacts(estado, "s", run_dir=tmp_path / "sessao")
    de_novo = json.loads((tmp_path / "sessao" / hg.ARQUIVO).read_text(encoding="utf-8"))["execucoes"]
    assert de_novo == exportado
    # mutante: sem o arquivo existente, só o resumo do estado sobra e os textos se perdem
    assert "texto" not in json.loads(hg.exportar(estado))["execucoes"][-1]["registros"][0]


def test_estado_restaurado_leva_o_historico_da_execucao_que_falhou_embora(tmp_path):
    """A execução que falha cria o `historico-gates.json` que não existia: a restauração o apaga, como os demais ausentes."""
    from pipeline.reexecucao import ARQUIVO_AUSENTES_NO_BACKUP, fazer_backup, restaurar_backup

    sessao = tmp_path / "sessao"
    sessao.mkdir()
    (sessao / "estado.json").write_text("{}", encoding="utf-8")
    backup = fazer_backup(sessao, "dev", [])
    assert hg.ARQUIVO in json.loads((backup / ARQUIVO_AUSENTES_NO_BACKUP).read_text(encoding="utf-8"))
    (sessao / hg.ARQUIVO).write_text('{"execucoes": [{"id": "falhou"}]}', encoding="utf-8")
    restaurar_backup(sessao, backup)
    assert not (sessao / hg.ARQUIVO).exists()
    # com o arquivo antes do backup, ele volta como estava
    (sessao / hg.ARQUIVO).write_text('{"execucoes": [{"id": "antes"}]}', encoding="utf-8")
    backup = fazer_backup(sessao, "dev", [])
    (sessao / hg.ARQUIVO).write_text('{"execucoes": [{"id": "falhou"}]}', encoding="utf-8")
    restaurar_backup(sessao, backup)
    assert "antes" in (sessao / hg.ARQUIVO).read_text(encoding="utf-8")


def test_sessao_antiga_sem_historico_e_lida_como_sempre(tmp_path, monkeypatch):
    from pipeline.artifacts import save_run_artifacts

    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "saida"))
    estado = _estado("exp09ef1b")
    assert hg.KEY not in estado and hg.exportar(estado) is None
    pasta = save_run_artifacts(estado, "s", run_dir=tmp_path / "sessao")
    assert not (pasta / hg.ARQUIVO).exists()
    assert diagnostico.coletar(estado)["veredito"] in ("aprovado", "amarelo", "bloqueado")


# =========================================================================== 6. o achado vai a quem pode consertá-lo
def test_ped06_da_76d9af6e_vai_ao_po_e_nao_gasta_a_rodada_do_autor_da_spec():
    """76d9af6e (exp01em1b, 23/10/2026): o PED-06 cita o §7 do one-pager; o SpecLoop o devolveu ao autor da spec, que não
    pode contrariar o one-pager, e chegou ao teto com a banca 🔴."""
    from agents.checkers import SaidaDeLoopAgent
    from agents.rota import RotaDeAchadosAgent

    estado = _estado("exp01em1b-76d9af6e")
    base = {"one_pager": estado["one_pager"], "spec_missao": estado["spec_missao"],
            "banca_produto_status": "bloqueado", "banca_produto_status_envelope": estado["banca_produto_status_envelope"],
            "banca_produto_report": estado["banca_produto_report"], "bncc_status": "aprovado", "spec_rodada": 0}
    marcado = _rodar(RotaDeAchadosAgent(name="Rota", status_keys=["banca_produto_status"]), base)
    env = marcado["banca_produto_status_envelope"]
    assert [a["id"] for a in env["achados"] if a.get("rota") == rota_achados.ROTA_PO] == ["PED-06"]
    assert marcado["banca_produto_status"] == "bloqueado", "o veredito do gate não muda"
    assert concordam(marcado["banca_produto_report"], env) and "Rota dos achados" in marcado["banca_produto_report"]

    saida = SaidaDeLoopAgent(name="Saida", status_keys=["bncc_status", "banca_produto_status"], rodada_key="spec_rodada",
                             max_rounds=2, autor_keys=["spec_missao"])
    depois = _rodar(saida, marcado)
    assert depois["spec_rodada"] == 1 and not depois.get("retrabalho_spec_missao"), "o loop sai na primeira rodada"
    # mutante: sem a rota, o achado volta ao autor da spec e a rodada se gasta
    sem_rota = _rodar(SaidaDeLoopAgent(name="Saida", status_keys=["bncc_status", "banca_produto_status"],
                                       rodada_key="spec_rodada", max_rounds=2, autor_keys=["spec_missao"]), base)
    assert "PED-06" in sem_rota["retrabalho_spec_missao"]


def test_ped06_misto_chega_ao_autor_como_contexto_quando_o_loop_roda_por_outro_gate():
    """O resumo do PED-06 também aponta «faltar a definição explícita de zero e none na tabela 9b da spec». Quando o loop
    roda por outro bloqueio, o achado do PO vai ao autor como contexto, sem decidir a rodada (revisão do PR #83)."""
    from agents.checkers import SaidaDeLoopAgent, motivos_do_retrabalho
    from agents.rota import RotaDeAchadosAgent

    estado = _estado("exp01em1b-76d9af6e")
    base = {"one_pager": estado["one_pager"], "spec_missao": estado["spec_missao"],
            "banca_produto_status": "bloqueado", "banca_produto_status_envelope": estado["banca_produto_status_envelope"],
            "banca_produto_report": estado["banca_produto_report"], "spec_rodada": 0,
            "bncc_status": "bloqueado", "bncc_report": "EF06CO10 citada fora do ano."}
    marcado = _rodar(RotaDeAchadosAgent(name="Rota", status_keys=["banca_produto_status"]), base)
    depois = _rodar(SaidaDeLoopAgent(name="Saida", status_keys=["bncc_status", "banca_produto_status"],
                                     rodada_key="spec_rodada", max_rounds=2, autor_keys=["spec_missao"]), marcado)
    pedido = depois["retrabalho_spec_missao"]
    assert depois["spec_rodada"] == 1 and "Gate `bncc_status`" in pedido, "o loop roda pelo bncc"
    assert "Gate `banca_produto_status`" not in pedido, "a banca reprovou só pelo PO: não decide a rodada"
    contexto = pedido[pedido.index("### Contexto: achados que vão ao PO"):]
    assert "PED-06" in contexto and "tabela 9b" in contexto and "Não altere o que o one-pager decide" in contexto
    # mutante: sem os gates do PO no pedido, a parte da spec do achado misto some do retrabalho
    assert "PED-06" not in motivos_do_retrabalho(marcado, ["bncc_status"])


def test_achado_que_a_spec_reproduz_e_o_sem_citacao_ficam_com_o_autor():
    one_pager = "O Canal A registra a escolha da criança na etapa 3 e grava o nível no servidor."
    env = {"achados": [
        {"id": "A", "severidade": "bloqueio", "citacao": "registra a escolha da criança na etapa 3"},
        {"id": "B", "severidade": "bloqueio", "resumo": "sem citação"},
        {"id": "C", "severidade": "atencao", "citacao": "grava o nível no servidor"}]}
    assert rota_achados.marcar(env, one_pager, "A spec: registra a escolha da criança na etapa 3, igual.") == []
    assert rota_achados.so_do_po(env) is False and len(rota_achados.bloqueios_do_autor(env)) == 2
    assert [a["id"] for a in rota_achados.marcar(env, one_pager, "spec sem o trecho")] == ["A"]
    assert rota_achados.so_do_po(env) is False, "o B continua com o autor"


def test_rota_confere_citacao_pela_funcao_publica():
    """A rota não importa o que `tools/fidelidade.py` tem de privado (revisão do PR #83): usa `tools.citacoes.existe`."""
    import inspect

    from tools import citacoes

    assert "_citacao_confere" not in inspect.getsource(rota_achados) and "_norm" not in inspect.getsource(rota_achados)
    doc = citacoes.normalizar("O Canal A registra a «escolha» da criança na etapa 3.")
    assert citacoes.existe("registra a escolha da criança na etapa 3", doc)
    assert not citacoes.existe("registra a nota do professor na etapa 9", doc)


# =========================================================================== 7. ajuste exigido que o loop não aplicou
#: 274a2e75 (exp03ef1b, 07/10/2026): o envelope da adequação no estado, com `avaliacoes_rodada` = 1.
ENVELOPE_274A2E75 = {"agente": "adequacao-pedagogica", "missao": "exp03ef1b", "status": "aprovado_com_ressalvas",
                     "placar": 16, "ajustes_exigidos": 1, "achados": [
                         {"id": "E2-A1", "severidade": "bloqueio", "codigo": "demanda_cognitiva",
                          "resumo": "ícone de raio isolado para ação/o quê exige abstração semiótica incompatível com 3º "
                                    "ano", "padrao": "repertorio-nao-declarado"},
                         {"id": "E1-A1", "severidade": "atencao", "codigo": "alinhamento_curricular",
                          "resumo": "habilidade EF03CO08 figura como foco primário", "padrao": "verbo-desalinhado"}],
                     "precisa_humano": False}


def _saida_avaliacoes(max_rounds: int):
    from agents.checkers import SaidaDeLoopAgent

    return SaidaDeLoopAgent(name="A033AdequacaoCheck", status_keys=["adequacao_status", "avaliacao_status"],
                            rodada_key="avaliacoes_rodada", max_rounds=max_rounds,
                            aceitos=["aprovado", "aprovado_com_ressalvas", "amarelo"],
                            envelope_exige={"adequacao_status": "ajustes_exigidos"})


def _estado_274a2e75() -> Dict[str, Any]:
    return {"adequacao_status": "amarelo", "adequacao_status_envelope": copy.deepcopy(ENVELOPE_274A2E75),
            "adequacao_report": "# Parecer de adequação pedagógica\n\n**Placar:** 16/18\n\n```json\n"
                                + json.dumps(ENVELOPE_274A2E75, ensure_ascii=False) + "\n```\n",
            "avaliacao_status": "aprovado", "avaliacoes_rodada": 0}


def test_274a2e75_ajuste_exigido_sem_rodada_fica_a_vista():
    depois = _rodar(_saida_avaliacoes(1), _estado_274a2e75())
    env = depois["adequacao_status_envelope"]
    ajuste = [a for a in env["achados"] if a.get("codigo") == "ajuste-exigido-nao-aplicado"]
    assert len(ajuste) == 1 and ajuste[0]["severidade"] == "decisao_humana" and env["precisa_humano"] is True
    assert depois["adequacao_status"] == "amarelo" and concordam(depois["adequacao_report"], env)
    d = diagnostico.coletar(depois)
    assert any(a["codigo"] == "ajuste-exigido-nao-aplicado" for a in d["humanos"])


def test_com_rodada_sobrando_o_ajuste_vira_retrabalho_real():
    """Teto 2 (o padrão desde 07/10/2026): na rodada 1 o loop repete e o revisor aplica — nada é anotado ainda."""
    depois = _rodar(_saida_avaliacoes(2), _estado_274a2e75())
    assert depois["avaliacoes_rodada"] == 1
    assert not any(a.get("codigo") == "ajuste-exigido-nao-aplicado"
                   for a in depois["adequacao_status_envelope"]["achados"])


# =========================================================================== 8. decisão do PO num refazer
def _estado_de_produto() -> Dict[str, Any]:
    e = _estado("exp02em1b-60cfa7f4")
    base = {k: e[k] for k in ("one_pager", "spec_missao_gate0", "nucleo_narrativo") if k in e}
    base["spec_missao"] = e["spec_missao_gate0"]
    return base


def test_refazer_com_marcador_e_seta_responde_o_marcador():
    """R11/R12 da exp02em1b: as propostas que o PO aprovou seguiam `[PROPOSTA]` a jusante. O de acordo escrito à mão com
    «→» já voltava ao cartão (PR 3); a mesma linha num pedido de refazer não voltava. «Título → outro título» é pedido de
    mudança, não resposta."""
    estado = _estado_de_produto()
    itens = fc.itens_em_aberto(estado)
    refazer = {"etapa": "dev", "acao": "refazer", "autor": "dev", "como": "dev", "quando": "22/10/2026 12:01:57",
               "valido": True, "comentario": (
                   "[PROPOSTA: validar com PO: Preservação de duas seções do DS (unooriaai + unoovista) em sessão de 50 "
                   "minutos] → aprovado\nPreservação de duas seções → trocar o título da tela")}
    anteriores = fc.respostas_anteriores(estado, {"pareceres": [refazer]}, itens)
    item = next(i for i in itens if "Preservação de duas seções" in i.assunto)
    assert anteriores[item.id]["resposta"] == fc.ACEITAR and anteriores[item.id]["origem"].startswith("refazer de")
    assert len(anteriores) == 1, "a linha sem marcador não responde nada"
    # mutante: sem o marcador no lado esquerdo, a mesma decisão não é lida
    sem_marcador = {**refazer, "comentario": "Preservação de duas seções do DS → aprovado"}
    assert fc.respostas_anteriores(estado, {"pareceres": [sem_marcador]}, itens) == {}


# =========================================================================== 9. aprendizado conferido em código
#: A linha do §1 do aprendizado real da 53e011b6 (exp06ef1b, 08/10/2026), copiada do `aprendizado_registro` do acervo:
#: sozinha num bloco ```markdown, sem cabeçalho de tabela.
LINHA_R10 = ('| exp06ef1b | 6º EF | 1º | O Júri Estadual de Projetos | unoovista | Cultura Digital / Sistemas de '
             'Recomendação | "O que aparece no meu feed não é tudo o que existe: minhas próprias curtidas ensinaram o '
             'aplicativo a esconder projetos inteiros da minha tela." | Avaliar projetos escolares curtindo publicações e '
             'elegendo o vencedor da mostra | explicar | EF06CO10 | em produção |')


def test_r10_status_do_catalogo_e_fatos_em_codigo():
    """53e011b6 (exp06ef1b, R10), com o aprendizado literal da sessão: «em produção» numa linha sem cabeçalho, dentro de
    um bloco ```markdown, e repetida em código inline na proposta de atualizar o catálogo; «Nenhuma» sem conferir."""
    estado = _estado("exp06ef1b-53e011b6")
    real = estado["aprendizado_registro"]
    assert "```markdown\n" + LINHA_R10 + "\n```" in real, "o formato real: linha sozinha no bloco, sem cabeçalho"
    novo = aprendizado.conferir(real, estado)
    status = catalogo.ficha_da_execucao(estado)["status"]
    assert f"| {status} (o agente propôs «em produção»: promover é ato humano) |" in novo
    assert f"| {status} (o agente propôs «em produção»: promover é ato humano) |`" in novo, "a linha em código inline"
    assert "| em produção |" not in novo, "nenhum status de promoção sobra no documento"
    fatos = novo[novo.index(aprendizado.TITULO_FATOS):]
    assert "o agente propôs «em produção»; promover é ato humano" in fatos
    assert fatos.count("em produção") == 1, "a proposta repetida aparece uma vez"
    assert "não foi conferida" in novo and "| Status no catálogo |" in fatos and "| Rodadas |" in fatos
    assert novo.index(aprendizado.TITULO_FATOS) < novo.rindex("```json"), "os fatos entram antes do envelope"
    assert extrair_envelope(novo)["agente"] == "aprendizado"
    assert aprendizado.conferir(novo, estado) == novo, "idempotente"
    # a linha sem cabeçalho também é lida pela ficha do catálogo (antes, ficha_lida=False nesta sessão)
    proposta = catalogo._linha_do_aprendizado(real, "exp06ef1b")
    assert proposta["nome"] == "O Júri Estadual de Projetos" and proposta["porta_abstracao"] == "explicar"
    assert proposta["tipo_decisao"].startswith("Avaliar projetos escolares")
    assert catalogo._linha_do_aprendizado(novo, "exp06ef1b")["habilidade_primaria"] == "EF06CO10"


def test_r10_mutante_sem_o_cabecalho_fixo_o_em_producao_passa(monkeypatch):
    estado = _estado("exp06ef1b-53e011b6")
    monkeypatch.setattr(catalogo, "cabecalho_fixo_da_linha", lambda celulas, slug: None)
    texto, trocados = aprendizado.corrigir_status_do_catalogo(estado["aprendizado_registro"], "em criação", "exp06ef1b")
    assert trocados == [] and LINHA_R10 in texto, "a correção desligada deixa o «em produção» da sessão real intacto"


def test_linha_sem_cabecalho_de_outra_missao_ou_com_outra_forma_nao_e_trocada():
    """Comparação literal: sem o slug da missão na primeira célula, ou fora das 11 colunas, a linha não é a do catálogo."""
    for texto, slug in ((LINHA_R10, "exp05ef1b"), (LINHA_R10, ""),
                        (LINHA_R10.replace("| EF06CO10 |", "|"), "exp06ef1b")):
        novo, trocados = aprendizado.corrigir_status_do_catalogo(texto, "em criação", slug)
        assert trocados == [] and novo == texto


#: A forma com o cabeçalho literal do prompt 128 (texto sintético, não de sessão): a coluna é achada pelo nome.
APRENDIZADO_COM_CABECALHO = """# Aprendizado — exp06ef1b — 10/10/2026

## 1. Catálogo (linha proposta + teste de diferenciação)
|Slug|Ano|Bim|Nome|Ambiente|Eixo temático|Descoberta central (aha)|Tipo de decisão|Porta de abstração|Habilidade primária|Status|
|---|---|---|---|---|---|---|---|---|---|---|
|exp06ef1b|6º EF|1|Vozes|instanooria|Algoritmos|O feed escolhe quem aparece|curadoria|criticar com apoio|EF06CO07|em produção|

```json
{"agente": "aprendizado", "missao": "exp06ef1b", "status": "concluido", "lacunas_abertas": 0, "devolucoes_ao_gate": 0, "candidatos_a_criterio": 0, "documentos_provisorios": 0, "precisa_humano": false}
```
"""


def test_tabela_com_cabecalho_status_trocado_pelo_nome_da_coluna():
    estado = _estado("exp06ef1b-53e011b6")
    novo = aprendizado.conferir(APRENDIZADO_COM_CABECALHO, estado)
    status = catalogo.ficha_da_execucao(estado)["status"]
    assert f"| {status} (o agente propôs «em produção»: promover é ato humano) |" in novo
    assert "|em produção|" not in novo
    assert catalogo._linha_do_aprendizado(novo)["descoberta"] == "O feed escolhe quem aparece"


def test_status_automatico_proposto_fica_e_promocao_com_formatacao_e_trocada():
    texto, trocados = aprendizado.corrigir_status_do_catalogo(
        APRENDIZADO_COM_CABECALHO.replace("em produção", "em criação"), "em criação")
    assert trocados == [] and "|em criação|" in texto
    _, trocados = aprendizado.corrigir_status_do_catalogo(
        APRENDIZADO_COM_CABECALHO.replace("em produção", "`Aprovada`"), "bloqueada")
    assert trocados == ["Aprovada"]


def test_o_callback_do_a128_aplica_a_conferencia():
    from agents.transversal import conferir_aprendizado, get_aprendizado_agent

    class Ctx:
        def __init__(self, state):
            self.state = state

    estado = _estado("exp06ef1b-53e011b6")
    ctx = Ctx(dict(estado))
    conferir_aprendizado(ctx)
    assert aprendizado.TITULO_FATOS in ctx.state["aprendizado_registro"]
    assert get_aprendizado_agent().after_agent_callback is conferir_aprendizado
