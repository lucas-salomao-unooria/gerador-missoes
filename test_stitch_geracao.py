"""O Stitch gera toda (tela, estado) do inventário, fora do modelo, com o screenId que ele devolve.

Até 07/10/2026 o agente de telas gerava dentro da própria resposta: o Stitch saía com 27% a 68% das
telas e a exp09ef1b declarou dez screenIds que o projeto não tinha. Aqui um Stitch falso registra cada
chamada, para provar: todas as linhas geradas, a linha esquecida pelo agente vinda do inventário, o
timeout conciliado sem gerar de novo, o retrabalho gerando só o que mudou, e nenhum id escrito por modelo.
"""
import asyncio
import itertools
import threading

from google.adk.agents.sequential_agent import SequentialAgent

from test_conteudo_aprovado import JORNADA_TELAS, _rodar
from tools import stitch_geracao as sg

RELATORIO = """# Wireframes

## Geração no Stitch
| ID | Estado | Dispositivo | Prompt |
|---|---|---|---|
| E1-ALU-01 | primeira vez | MOBILE | E1-ALU-01 — Galeria, primeira vez. Topo: barra. |
| E1-ALU-01 | padrão | MOBILE | E1-ALU-01 — Galeria, estado padrão. Topo: barra. |
| E0-PROF-01 | padrão | DESKTOP | E0-PROF-01 — Catálogo de missões. |
"""


class StitchFalso:
    def __init__(self, timeout_em=(), sempre_falha=()):
        self.chamadas = []
        self.telas = {}
        self.timeout_em, self.sempre_falha = set(timeout_em), set(sempre_falha)
        self._ids = itertools.count(1)
        self._trava = threading.Lock()

    def __call__(self, ferramenta, argumentos):
        with self._trava:
            self.chamadas.append((ferramenta, dict(argumentos)))
        if ferramenta == "create_project":
            return {"name": "projects/4044680601076201931", "title": argumentos["title"]}
        if ferramenta == "list_design_systems":
            return {"designSystems": [{"name": "assets/15996705518239280238"}]}
        if ferramenta == "list_screens":
            return {"screens": [{"name": f"projects/4044680601076201931/screens/{i}", "title": t} for t, i in self.telas.items()]}
        if ferramenta == "generate_screen_from_text":
            titulo = argumentos["prompt"].split(". ")[0]
            if titulo in self.sempre_falha:
                raise TimeoutError("timeout")
            with self._trava:
                tela = f"{next(self._ids):032x}"
                self.telas[titulo] = tela
            if titulo in self.timeout_em:
                self.timeout_em.discard(titulo)  # gerou, mas a resposta não chegou
                raise TimeoutError("timeout")
            return {"outputComponents": [{"design": {"screens": [{"name": f"projects/4044680601076201931/screens/{tela}"}]}}]}
        return {}


def _gerar(stitch, itens, registro=None, projeto=None):
    return sg.gerar(itens, registro or {}, projeto=projeto, design_system=None, titulo_projeto="exp — wireframes",
                    chamar=stitch, paralelo=3, esperar=lambda s: None)


def test_toda_tela_e_estado_e_gerada_com_o_id_que_o_stitch_devolve():
    itens = sg.completar(sg.itens_do_relatorio(RELATORIO), JORNADA_TELAS)
    chaves = {(i["id"], i["estado"]) for i in itens}
    # o inventário tem E0-PROF-01..05 e E1-ALU-01 com três estados: o agente esqueceu sete linhas
    assert len(itens) == 9 and ("E1-ALU-01", "degradado") in chaves and ("E0-PROF-04", "padrão") in chaves
    esquecida = next(i for i in itens if i["id"] == "E0-PROF-04")
    assert esquecida["origem"] == "inventario" and esquecida["dispositivo"] == "DESKTOP"
    assert esquecida["prompt"].startswith("E0-PROF-04 — curadoria, estado padrão.")

    stitch = StitchFalso()
    saida = _gerar(stitch, itens)
    ferramentas = [f for f, _ in stitch.chamadas]
    assert ferramentas[:3] == ["create_project", "upload_design_md", "list_design_systems"]
    geracoes = [a for f, a in stitch.chamadas if f == "generate_screen_from_text"]
    assert len(geracoes) == 9 and all(a["designSystem"] == "assets/15996705518239280238" for a in geracoes)
    assert all(r["screen_id"] == stitch.telas[sg.titulo(r)] for r in saida["resultado"]), "id é o que o Stitch devolveu"
    assert "9 de 9" in sg.relatorio(saida)


def test_timeout_e_conciliado_sem_gerar_de_novo_e_falha_fica_registrada():
    itens = sg.completar(sg.itens_do_relatorio(RELATORIO), JORNADA_TELAS)
    stitch = StitchFalso(timeout_em={"E1-ALU-01 — padrão"}, sempre_falha={"E0-PROF-03 — carregando"})
    saida = _gerar(stitch, itens)
    titulos = [a["prompt"].split(". ")[0] for f, a in stitch.chamadas if f == "generate_screen_from_text"]
    assert titulos.count("E1-ALU-01 — padrão") == 1, "a ferramenta pede para não repetir em timeout: achou relendo o projeto"
    assert titulos.count("E0-PROF-03 — carregando") == 2, "o que a conciliação não acha tem uma nova tentativa, só uma"
    falhou = next(r for r in saida["resultado"] if r["id"] == "E0-PROF-03")
    assert falhou["screen_id"] == "" and "timeout" in falhou["erro"]
    assert "FALTOU — timeout" in sg.relatorio(saida)


def test_retrabalho_gera_no_mesmo_projeto_so_o_que_mudou():
    itens = sg.completar(sg.itens_do_relatorio(RELATORIO), JORNADA_TELAS)
    stitch = StitchFalso()
    primeira = _gerar(stitch, itens)
    mudou = [dict(i, prompt=i["prompt"] + " Com o botão Voltar.") if i["id"] == "E0-PROF-01" else i for i in itens]
    stitch.chamadas.clear()
    segunda = _gerar(stitch, mudou, registro=primeira["registro"], projeto=primeira["projeto"])
    ferramentas = [f for f, _ in stitch.chamadas]
    assert "create_project" not in ferramentas
    # a tela refeita nasce como v2 no mesmo projeto: o Stitch não renomeia nem apaga a v1 (decisão de 08/10/2026)
    assert [a["prompt"].split(". ")[0] for f, a in stitch.chamadas if f == "generate_screen_from_text"] == ["E0-PROF-01 — padrão · v2"]
    assert segunda["registro"]["E0-PROF-01|padrão"]["versao"] == 2
    assert segunda["registro"]["E1-ALU-01|padrão"] == primeira["registro"]["E1-ALU-01|padrão"]
    assert sg.rotulos(segunda["registro"])[segunda["registro"]["E0-PROF-01|padrão"]["screen_id"]] == "E0-PROF-01 — padrão · v2"


def test_agente_anexa_a_secao_e_reaproveita_o_projeto(monkeypatch):
    from config import get_settings
    from agents.checkers import StitchGeracaoAgent
    import tools.stitch_cliente as cliente

    stitch = StitchFalso()
    monkeypatch.setattr(cliente, "chamar", lambda f, a, timeout=0: stitch(f, a))
    monkeypatch.setattr(type(get_settings()), "is_stitch_enabled", property(lambda self: True))
    estado = {"wireframes_cobertura": RELATORIO, "jornada_telas": JORNADA_TELAS, "spec_missao": "id: exp03ef1b"}
    final = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[StitchGeracaoAgent(name="G")]), estado))
    assert final["stitch_project_id"] == "4044680601076201931"
    assert final["wireframes_cobertura"].count("## Telas geradas no Stitch (esteira)") == 1
    assert len(final["stitch_geracao"]) == 9
    # segunda passada (retrabalho): a seção antiga sai, o projeto é o mesmo, nada é gerado de novo
    stitch.chamadas.clear()
    de_novo = asyncio.run(_rodar(SequentialAgent(name="R", sub_agents=[StitchGeracaoAgent(name="G")]), final))
    assert de_novo["wireframes_cobertura"].count("## Telas geradas no Stitch (esteira)") == 1
    assert not [f for f, _ in stitch.chamadas if f in ("create_project", "generate_screen_from_text")]


def test_agente_de_telas_nao_tem_mais_as_ferramentas_de_geracao():
    from agents.design import build_design_stage
    from prompts import get_prompt_raw

    estagio = build_design_stage()
    telas_agente = next(a for a in estagio.sub_agents if a.name == "A26Telas")
    assert not telas_agente.tools
    nomes = [a.name for a in estagio.sub_agents]
    assert nomes.index("A26Telas") + 1 == nomes.index("A26bStitchGeracao")
    prompt = get_prompt_raw("design/26_telas.md")
    assert "## Geração no Stitch" in prompt and "Você não chama o Stitch" in prompt and "`create_project`" not in prompt


def test_id_da_resposta_em_qualquer_formato_conhecido():
    projeto = "4044680601076201931"
    tela = "966431a057a342238a77393e9f75c8d0"
    assert sg._screen_id({"x": f"projects/{projeto}/screens/{tela}"}, projeto) == tela
    assert sg._screen_id({"screen": {"name": f"screens/{tela}"}}, projeto) == tela
    assert sg._screen_id({"screenId": tela}, projeto) == tela
    assert sg._screen_id({"texto": "pronto"}, projeto) is None
