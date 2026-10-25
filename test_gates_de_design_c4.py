"""C4 do backlog de correções de 24/10/2026: falsos positivos dos gates de design e a falha silenciosa do Miro.

O gabarito com os estados reais está em `tests/gabarito_achados/test_design_*.py`. Aqui, cada regra nova em texto mínimo, e
os mutantes que provam que ela é estreita: a exceção que tira o falso positivo não esconde o verdadeiro vizinho.
"""
from __future__ import annotations

import pytest

from tools import afirmacoes, consistencia
from tools import conteudo_aprovado as ca
from tools import miro_cliente as mc

GLOSSARIO = ("# Spec — O Porta-Voz dos Dados v1.1\n\n## Glossário canônico\n\n| Ação | Rótulo canônico |\n|---|---|\n"
             "| Acessar ações diretas da postagem | Configuração da Publicação |\n"
             "| Confirmar e publicar no feed da rede | Publicar no Unoovista |\n"
             "| Encaminhar situação para suporte | Encaminhar relato |\n"
             "| Confirmar assunção do papel de Porta-Voz | Assumir Função de Porta-Voz |\n"
             "| Confirmar aposta e rodar simulação | Disparar Simulação |\n")

INVENTARIO = ("| ID | Etapa | Elementos na tela | Ação (verbo nativo) | Resultado da ação |\n"
              "|---|---|---|---|---|\n")


def _rotulos(documento: str, texto: str, spec: str = GLOSSARIO):
    achados = consistencia.validar(spec, {documento: texto})["achados"]
    return [a["resumo"] for a in achados if a["codigo"] == "rotulo-divergente"]


def _cita(rotulos, candidato: str) -> bool:
    return any(f"aparece como «{candidato}»" in r for r in rotulos)


# --------------------------------------------------------------------------- 1. rotulo-divergente
def test_verbo_entre_crases_na_coluna_de_gesto_nao_e_rotulo():
    linha = "| `E1-ALU-01` | 1 | Topbar, botão iniciar | `Acessar` / `Digitar` · `Encaminhar` relato | Inicializa |\n"
    assert _rotulos("jornada", INVENTARIO + linha) == []


@pytest.mark.parametrize("celula, candidato", [
    ('Clicar em `Publicar no feed`', "Publicar no feed"),       # o gesto aciona um botão citado
    ('Toca "Publicar no feed"', "Publicar no feed"),            # entre aspas duplas é texto de tela
    ("`Publicar` (botão `Publicar no feed`)", "Publicar no feed"),
])
def test_mutante_botao_citado_na_coluna_de_gesto_continua_acusado(celula, candidato):
    linha = f"| `E3-ALU-01` | 3 | Card do post | {celula} | Grava |\n"
    assert _cita(_rotulos("jornada", INVENTARIO + linha), candidato)


def test_mutante_crase_fora_da_coluna_de_gesto_continua_acusada():
    linha = "| `E3-ALU-01` | 3 | Card do post, botão `Publicar no feed` | `Publicar` | Grava |\n"
    rotulos = _rotulos("jornada", INVENTARIO + linha)
    assert _cita(rotulos, "Publicar no feed") and not _cita(rotulos, "Publicar")


def test_mutante_coluna_de_gesto_so_vale_na_jornada(monkeypatch):
    """Só a jornada tem a coluna e a raia do verbo nativo (071): a mesma tabela no PRD continua conferida. Desde a C7
    (25/10/2026), conferida quer dizer que o candidato chega ao «é botão?» do classificador de sentido — e, com o
    cabeçalho «Ação (verbo nativo)», ele lê o gesto e o tira; lendo botão, o achado fica."""
    from tools import classificador

    linha = "| `E3-ALU-01` | 3 | Card do post, botão publicar | `Publicar no feed` | Grava |\n"
    assert _rotulos("jornada", INVENTARIO + linha) == []
    assert not _cita(_rotulos("PRD", INVENTARIO + linha), "Publicar no feed")
    lidos = []
    original = classificador.ler

    def ler(pergunta, entradas):
        lidos.extend(e["candidato"] for e in entradas)
        return [classificador.Leitura("rotulo_de_botao", e["candidato"], "modelo") for e in entradas]

    monkeypatch.setattr(classificador, "ler", ler)
    assert _rotulos("jornada", INVENTARIO + linha) == [] and lidos == []
    assert _cita(_rotulos("PRD", INVENTARIO + linha), "Publicar no feed") and lidos == ["Publicar no feed"]
    monkeypatch.setattr(classificador, "ler", original)


def test_raia_estudante_faz_e_coluna_de_gesto():
    mapa = ("| Raia | Desafiar | Navegar |\n|---|---|---|\n"
            "| **Estudante — faz (verbo nativo)** | `Encaminhar` relato, toca no botão | `Publicar` |\n")
    assert _rotulos("jornada", mapa) == []


FLUXO = ("## Grafo\n\n```mermaid\nstateDiagram-v2\n  E3_ALU_01 --> E4_ALU_01: Publicar Unoovista\n"
         "  E4_ALU_02 --> E4_ALU_03: Abrir apoio\n```\n\n```mermaid\nflowchart TD\n  A -->|\"Toca modulo teste\"| B\n"
         "  B -- Disparar simulacao latch --> C\n```\n\n")


def test_rotulos_de_aresta_do_mermaid():
    assert consistencia.rotulos_de_aresta(FLUXO) == {"publicar unoovista", "abrir apoio", "toca modulo teste",
                                                      "disparar simulacao latch"}


def test_rotulo_de_aresta_citado_no_fluxo_nao_e_botao():
    texto = FLUXO + ("- 'E3-ALU-01': saída via A05 (toca 'Publicar Unoovista').\n"
                     "- **Maior rótulo no Mermaid:** 3 palavras (ex.: \"Toca modulo teste\", \"Publicar no Unoovistas\").\n")
    assert _rotulos("fluxo", texto) == []


def test_mutante_botao_na_tabela_de_arestas_continua_acusado():
    texto = FLUXO + "| A05 | `E3-ALU-01` | `E4-ALU-01` | Estudante clica no botão \"Publicar no feed\" | principal |\n"
    assert _cita(_rotulos("fluxo", texto), "Publicar no feed")


@pytest.mark.parametrize("linha", [
    "- Na tela de publicação, o estudante toca o botão \"Publicar Unoovista\".\n",  # outra linha do fluxo
    "| `E3-ALU-01` | Card do post | Estudante clica no botão \"Publicar Unoovista\" |\n",  # tabela sem id de aresta
])
def test_mutante_rotulo_de_aresta_fora_da_linha_de_aresta_continua_acusado(linha):
    """A dispensa do rótulo de aresta vale na linha do desenho e na que cita a aresta pelo id, não no documento todo."""
    assert _cita(_rotulos("fluxo", FLUXO + linha), "Publicar Unoovista")
    assert _cita(_rotulos("PRD", FLUXO + linha), "Publicar Unoovista")


def test_mutante_linha_do_mermaid_so_dispensa_rotulo_de_aresta():
    """A linha que fala do Mermaid não é ignorada inteira: o botão que não é rótulo de aresta continua conferido."""
    texto = FLUXO + "- O botão \"Publicar Unoovista no feed\" leva ao estado E4 do diagrama Mermaid.\n"
    assert _cita(_rotulos("fluxo", texto), "Publicar Unoovista no feed")


def test_nome_da_missao_no_card_nao_e_botao():
    texto = "| P02 | `E0-PROF-01` | `E0-PROF-02` | Professor clica no card da missão \"O Porta-Voz dos Dados\" |\n"
    assert _rotulos("fluxo", texto) == []
    assert consistencia.nomes_da_missao(GLOSSARIO, "Nome que o estudante vê: O Porta-Voz dos Dados\n") == {
        "o porta-voz dos dados"}


def test_mutante_botao_com_o_nome_da_missao_e_mais_texto_continua_acusado():
    texto = "| P03 | `E1-ALU-01` | `E1-ALU-02` | Estudante clica em \"Assumir o Porta-Voz dos Dados\" |\n"
    assert _cita(_rotulos("fluxo", texto), "Assumir o Porta-Voz dos Dados")


def test_miolo_entre_duas_citacoes_nao_e_rotulo():
    linha = ("| **Estudante — vê** | Registrar aposta (`Button` `\"Confirmar e Disparar Teste\"`) | Disparar simulação "
             "(`Button` `\"Disparar Simulação\"`) |\n")
    rotulos = _rotulos("jornada", "| Raia | A | B |\n|---|---|---|\n" + linha)
    assert not [r for r in rotulos if "aparece como «)" in r]
    # o botão de verdade entre aspas duplas continua conferido (ambíguo no levantamento: pode ser outro botão)
    assert _cita(rotulos, "Confirmar e Disparar Teste")


def test_mutante_rotulo_com_parenteses_continua_acusado():
    texto = "| A07 | `E2-ALU-03` | `E2-ALU-04` | Estudante toca o botão \"Disparar (Simulação rápida)\" |\n"
    assert _cita(_rotulos("fluxo", texto), "Disparar (Simulação rápida)")


# --------------------------------------------------------------------------- 3. texto de tela
@pytest.mark.parametrize("documento", [
    "Chamado #101: Tentei entrar na trilha avançada para estudar para a prova, mas o bot me bloqueou.",
    "Chamado #101: Tentei entrar na Trilha Avançada do recorte da aula para estudar para a prova, mas o bot me bloqueou.",
    "Chamado #101: Tentei entrar na Trilha Avançada do [recorte da aula] para estudar para a prova, mas o bot me bloqueou.",
])
def test_lacuna_do_texto_aprovado_e_curinga(documento):
    aprovado = "Tentei entrar na Trilha Avançada do [recorte da aula] para estudar para a prova, mas o bot me bloqueou"
    assert ca.literais_ausentes(documento, [aprovado]) == []


@pytest.mark.parametrize("documento", [
    "Tentei entrar na trilha avançada para estudar para a prova, mas o bot me liberou.",       # o fim trocado
    "Tentei entrar na trilha básica para estudar para a prova, mas o bot me bloqueou.",       # o pedaço de antes
    "Tentei entrar na trilha avançada para estudar para a prova, mas o bot não me bloqueou.",  # negação
])
def test_mutante_pedaco_entre_lacunas_trocado_continua_acusado(documento):
    aprovado = "Tentei entrar na Trilha Avançada do [recorte da aula] para estudar para a prova, mas o bot me bloqueou"
    assert ca.literais_ausentes(documento, [aprovado]) == [aprovado]


@pytest.mark.parametrize("aprovado, documento", [
    ("Olá, [nome]!", "Tchau, Ana! Boas-vindas à missão."),          # só pedaço de uma palavra fora da lacuna
    ("[Opção votada]", "O estudante vê a opção que escolheu."),       # só lacuna
    ("{nome}, vote!", "Ana, escolha a sua opção."),
])
def test_mutante_texto_so_de_lacuna_nao_confere_por_vacuidade(aprovado, documento):
    """Sem pedaço de duas palavras para conferir, o curinga não dá o texto como presente: confere inteiro, sem lacuna."""
    assert ca.literais_ausentes(documento, [aprovado]) == [aprovado]


def test_texto_so_de_lacuna_confere_quando_esta_literal():
    assert ca.literais_ausentes("Na tela: Olá, [nome]! Vamos começar.", ["Olá, [nome]!"]) == []


def _s4(*linhas: str) -> str:
    return "# One-pager\n\n## 4. Etapas\n\n### Etapa 4: Resultado\n" + "\n".join(linhas) + "\n\n## 5. Outra\n"


def test_pergunta_disparadora_e_fala_hipotetica_nao_sao_texto_de_tela():
    one_pager = _s4('3. Pergunta disparadora: *"Vocês acham que a rede entregou essa postagem de madrugada?"*',
                    '4. Desmonta o descarte: se alguém disser *"aconteceu isso porque eu errei na IA"*, o professor aponta.',
                    '- Tela: o banner mostra *"Sua postagem foi entregue às 2h da manhã"*.')
    assert ca.textos_de_tela(one_pager) == ["Sua postagem foi entregue às 2h da manhã"]


def test_mutante_feedback_por_ramo_continua_texto_de_tela():
    """«Se o estudante previu (A): "…"» é o texto que a tela mostra ao ramo A (exp01em1b-76d9af6e): não é fala hipotética."""
    one_pager = _s4('- *Se o estudante previu (A):* *"Você previu: todos receberão o nível avançado. Por quê?"*')
    assert ca.textos_de_tela(one_pager) == ["Você previu: todos receberão o nível avançado. Por quê?"]


# --------------------------------------------------------------------------- 2. arquivo-inexistente
RELATO = ("- **Ticket 'QA-A1' ('arquivo-inexistente'):** Resolvido. Na rodada 1, o relatório citou a chave de caminho "
          "'design/06-copy-revisada.md', arquivo não gravado na esteira conforme 'pipeline/artifacts.py'.")


def _acusa(texto: str, apontados=()):
    return [a for a in afirmacoes.conferir_qa(texto, ja_apontados=apontados)["achados"]
            if a["codigo"] == "arquivo-inexistente"]


def test_relato_com_aposto_do_caminho_ja_apontado_nao_e_acusado():
    assert _acusa(RELATO, ["design/06-copy-revisada.md"]) == []


@pytest.mark.parametrize("texto, apontados", [
    (RELATO, []),                                                                       # sem rodada anterior
    (RELATO.replace("não gravado", "gravado"), ["design/06-copy-revisada.md"]),         # sem negação
    (RELATO.replace("06-copy-revisada", "07-copy-final"), ["design/06-copy-revisada.md"]),  # outro caminho
    ("Ver o sheet de copy em `design/06-copy-revisada.md`, arquivo da passada 2.", ["design/06-copy-revisada.md"]),
])
def test_mutante_citacao_como_real_continua_acusada(texto, apontados):
    assert _acusa(texto, apontados)


# --------------------------------------------------------------------------- 5. Miro
def test_conferir_espelho():
    ok = {"url_board": "https://miro.com/app/board/x=/", "diagramas": [{"id": "jornada"}, {"id": "fluxo"}], "recusados": 0}
    assert mc.conferir_espelho(True, "j", "f", dados=ok)["status"] == "aprovado"
    assert mc.conferir_espelho(False, "j", "f")["status"] == mc.DESLIGADO
    falhou = mc.conferir_espelho(True, "j", "f", motivo="tempo esgotado ao falar com o Miro",
                                 board_anterior={"url_board": "https://miro.com/app/board/velho=/"})
    assert falhou["status"] == "amarelo" and "board da execução anterior (https://miro.com/app/board/velho=/)" in \
        falhou["achados"][0]["resumo"]
    # nunca 🟢 sem board: nem sem motivo, nem com o board sem um dos diagramas
    assert mc.conferir_espelho(True, "j", "f")["status"] == "amarelo"
    assert mc.conferir_espelho(True, "j", "f", dados={**ok, "diagramas": [{"id": "jornada"}]})["status"] == "amarelo"
    assert mc.conferir_espelho(True, "j", "", dados={**ok, "diagramas": [{"id": "jornada"}]})["status"] == "aprovado"


@pytest.mark.parametrize("texto, segredo", [
    ("Authorization: Bearer abc.def.ghi-123", "abc.def.ghi-123"),
    ("POST /token falhou: access_token=AAA111&refresh_token=BBB222", "AAA111"),
    ("refresh_token=BBB222", "BBB222"),
    ("client_secret: 'sss-999'", "sss-999"),
    ("segredo 0123456789abcdef0123456789abcdef01 no corpo", "0123456789abcdef0123456789abcdef01"),
])
def test_sem_segredo(texto, segredo):
    limpo = mc.sem_segredo(texto)
    assert segredo not in limpo and "[oculto]" in limpo
    assert segredo not in mc.motivo_de_indisponibilidade(RuntimeError(texto))
    assert segredo not in mc.folha_de_indisponibilidade(texto)


def test_motivo_legivel_continua_legivel():
    assert mc.sem_segredo("token expirado ao publicar; board uXjVHhWyjBg=") == "token expirado ao publicar; board uXjVHhWyjBg="


def test_gate_do_miro_no_semaforo_no_dossie_e_no_refazer():
    from pipeline.reexecucao import CHAVES_DESIGN, preparar_estado
    from pipeline.runner import STATUS_KEYS
    from tools.diagnostico import GATES

    assert {mc.KEY_STATUS, mc.KEY_REPORT, f"{mc.KEY_STATUS}_envelope"} <= CHAVES_DESIGN
    assert mc.KEY_STATUS in STATUS_KEYS
    assert [g["rotulo"] for g in GATES if g["status"] == mc.KEY_STATUS] == [mc.ROTULO_GATE]
    limpo, _ = preparar_estado({"spec_missao": "# Spec — x v1\n", mc.KEY_STATUS: "amarelo",
                                "miro_board": {"url_board": "https://miro.com/app/board/x=/"}}, "design")
    # o veredito é refeito; o board fica, para o espelho atualizar o mesmo em vez de abrir outro
    assert mc.KEY_STATUS not in limpo and limpo["miro_board"]["url_board"].endswith("x=/")
