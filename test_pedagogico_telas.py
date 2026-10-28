"""O one-pager pedagógico com as telas do Stitch debaixo de cada passo, e o `.docx` que não se desfaz.

Pedido do usuário (07/10/2026): o pedagógico explica a mecânica passo a passo, e quem aprova não abre
as telas por fora — então cada passo leva a imagem das telas dele, e o fim do passo a passo leva o
desenho da jornada e do fluxo, quando houver como desenhá-lo sem mandar a missão a terceiros.

Nenhum teste vai à rede: o download das imagens, o renderizador de Mermaid e a sessão do Miro são falsos.
"""

import io
import zipfile
from pathlib import Path

import docx
import httpx
import pytest
from docx.oxml.ns import qn
from PIL import Image

from tools import ilustracoes as il
from tools import markdown_blocos as mb

# --------------------------------------------------------------------------- insumos
URL = "https://lh3.googleusercontent.com/aida/{}"

FOLHA_STITCH = f"""# Telas no Stitch — exp01ef1b

**Projeto:** [https://stitch.withgoogle.com/projects/1369](https://stitch.withgoogle.com/projects/1369) · `1369`

| Tela | Dispositivo | Medidas | Prévia |
|---|---|---|---|
| E3-ALU-02 — Aposta travada com cadeado | DESKTOP | 2560×2048 | [abrir imagem]({URL.format('e3alu02')}) |
| E0-PROF-02 — Preparação da aula | DESKTOP | 2560×2824 | [abrir imagem]({URL.format('e0prof02')}) |
| E3-ALU-01 — Apresentação da aposta | DESKTOP | 2560×2048 | [abrir imagem]({URL.format('e3alu01')}) |
| E9-ALU-01 — Tela que nenhum passo cita | DESKTOP | 2560×2048 | [abrir imagem]({URL.format('e9alu01')}) |

4 tela(s).

## Visão do professor

| Tela | Dispositivo | Prévia |
|---|---|---|
| E0-PROF-02 — Preparação da aula | DESKTOP | [abrir imagem]({URL.format('e0prof02')}) |
"""

JORNADA = """# Jornada — exp01ef1b

## Seção 1b — Diagrama da jornada

```mermaid
journey
  title Detetive da Foto
  section Desafiar
    Abre a pasta: 5: Criança
```

## Seção 3 — Inventário de telas

| ID | Etapa | Ator | Propósito | Peso |
|---|---|---|---|---|
| `E0-PROF-01` | Preparo | Professor | Selecionar missão no catálogo | serviço |
| `E0-PROF-02` | Preparo | Professor | Definir recorte e tema da aula | alta |
| `E1-ALU-01` | E1: Desafiar | Estudante | Abertura do álbum misterioso | média |
| `E3-ALU-01` | E3: Decidir | Estudante | Apresentação da aposta | alta |
| `E3-ALU-02` | E3: Decidir | Estudante | Aposta travada | pico |
"""

FLUXO = """# Fluxo — exp01ef1b

```mermaid
stateDiagram-v2
  E1_ALU_01 --> E3_ALU_01
  E3_ALU_01 --> E3_ALU_02
```

## Fluxo do professor

```mermaid
stateDiagram-v2
  E0_PROF_01 --> E0_PROF_02
```
"""

PEDAGOGICO = """# O Detetive da Foto Misteriosa

> **O que pedimos a você:** aprovar o início da construção.

## Em uma frase
A criança investiga uma foto tirada muito de perto.

## Como a missão acontece, passo a passo

### Antes da aula — o preparo da professora
- **O que você vê:** o catálogo de missões e o botão do tema pronto.
- **O que você faz:** escolhe a turma e usa o tema pronto.
- **O que acontece:** o sistema prepara as fotos.

**Telas deste passo:** `E0-PROF-01` · `E0-PROF-02`

### Passo 1 — Desafiar
- **O que a criança vê:** a pasta misteriosa.
- **O que a criança faz:** toca na pasta.
- **O que acontece:** a missão começa.

**Telas deste passo:** `E1-ALU-01`

### Passo 3 — Decidir
- **O que a criança vê:** duas carinhas, susto e festa.
- **O que a criança faz:** toca numa delas.
- **O que acontece:** um cadeado guarda a aposta.

**Telas deste passo:** `E3-ALU-01` · `E3-ALU-02`

## O que sua sala precisa ter
- Um tablet por criança.

---

```json
{"agente": "one-pager-pedagogico", "missao": "exp01ef1b", "status": "concluido"}
```

---

# Anexo — conteúdo aprovado pelo PO

## Tempos — one-pager §10

| Etapa | Em tela |
|---|---|
| E1 | 2 min |
"""


def _png(cor, tamanho=(1200, 960)) -> bytes:
    saida = io.BytesIO()
    Image.new("RGB", tamanho, cor).save(saida, "PNG")
    return saida.getvalue()


def _estado(**extra):
    estado = {"one_pager_pedagogico": PEDAGOGICO, "stitch_links": FOLHA_STITCH, "jornada_telas": JORNADA,
              "fluxo_arestas": FLUXO, "diagramas_html": "<html>diagramas</html>"}
    estado.update(extra)
    return estado


def _sequencia(caminho: Path):
    """Títulos de passo e imagens do `.docx`, na ordem do documento."""
    d = docx.Document(str(caminho))
    saida = []
    for p in d.element.body.iterchildren():
        if p.tag != qn("w:p"):
            continue
        par = docx.text.paragraph.Paragraph(p, d)
        estilo = par.style.name if par.style is not None else ""
        doc_pr = p.find(".//" + qn("wp:docPr"))
        if doc_pr is not None:
            saida.append(("imagem", doc_pr.get("descr")))
        elif estilo.startswith("Heading"):
            saida.append((estilo, par.text.strip()))
    return saida, "\n".join(p.text for p in d.paragraphs)


@pytest.fixture
def sem_rede(monkeypatch):
    """Qualquer tentativa de ir à rede falha o teste."""
    def proibido(*_a, **_k):
        raise AssertionError("o teste foi à rede")

    monkeypatch.setattr(httpx, "get", proibido)
    monkeypatch.setattr(httpx, "post", proibido)
    monkeypatch.setattr(httpx.Client, "send", proibido)
    monkeypatch.delenv("DIAGRAMA_IMAGEM_FONTE", raising=False)
    monkeypatch.delenv("MERMAID_RENDER_URL", raising=False)
    return proibido


# --------------------------------------------------------------------------- 1. leitura do Markdown
def test_analisar_desembrulha_o_documento_e_pareia_as_cercas():
    """O agente embrulha o documento em ```markdown e abre ```sql dentro: a leitura antiga alternava código
    e texto a cada cerca, e o `.docx` saía com o documento inteiro num bloco de código."""
    documento = (
        "Segue o documento:\n\n```markdown\n# Missão\n\n## Seção A\nTexto da seção.\n\n"
        "```sql\nselect 1;\n```\n\n## Seção B\n| a | b |\n|---|---|\n| 1 | 2 |\n\n"
        "```typescript\nconst x = 1\n```\n\n## Seção C\nFim.\n```\n"
    )
    blocos = mb.analisar(documento)
    titulos = [mb.texto_puro(b.trechos) for b in blocos if b.tipo == "titulo"]
    assert titulos == ["Missão", "Seção A", "Seção B", "Seção C"]
    codigos = [(b.idioma, b.texto) for b in blocos if b.tipo == "codigo"]
    assert codigos == [("sql", "select 1;"), ("typescript", "const x = 1")]
    assert any(b.tipo == "tabela" for b in blocos)
    assert not any("```" in mb.texto_puro(b.trechos) for b in blocos)

    # ```typescript dentro de um bloco nu não o fecha: só a cerca nua fecha (CommonMark)
    aninhado = mb.analisar("Antes.\n\n````\n```typescript\nx\n```\n````\n\nDepois.")
    assert [b.tipo for b in aninhado] == ["paragrafo", "codigo", "paragrafo"]
    # cerca órfã no fim seguida de markdown some, e o markdown continua markdown
    orfa = mb.analisar("Texto.\n\n```\n## Título que vinha depois\n")
    assert [b.tipo for b in orfa] == ["paragrafo", "titulo"]


def test_envelope_antes_do_anexo_sai_do_documento():
    """No pedagógico o anexo vem DEPOIS do envelope: o `.docx` da exp01ef1b mostrava o JSON no meio."""
    blocos = mb.analisar(PEDAGOGICO)
    assert not any(b.tipo == "codigo" for b in blocos), "o envelope do agente vazou para o documento"
    assert any(b.tipo == "titulo" and mb.texto_puro(b.trechos).startswith("Anexo") for b in blocos)
    # um ```json citado no corpo, sem a assinatura do agente, continua lá
    citado = "# Doc\n\n```json\n{\"a\": 1}\n```\n\n# Anexo — conteúdo aprovado pelo PO\n\nx\n"
    assert any(b.tipo == "codigo" for b in mb.analisar(citado))


def test_linha_das_telas_vira_bloco_com_os_ids():
    blocos = mb.analisar(PEDAGOGICO)
    telas = [b.ids for b in blocos if b.tipo == "telas"]
    assert telas == [["E0-PROF-01", "E0-PROF-02"], ["E1-ALU-01"], ["E3-ALU-01", "E3-ALU-02"]]
    variantes = ["- Telas deste passo: E2-ALU-01, E2_ALU_02", "Telas desta etapa: `E4-PROF-01b`"]
    assert [b.ids for v in variantes for b in mb.analisar(v)] == [["E2-ALU-01", "E2-ALU-02"], ["E4-PROF-01"]]
    # ID citado em prosa não é âncora de imagem
    assert [b.tipo for b in mb.analisar("A tela E2-ALU-01 mostra a foto.")] == ["paragrafo"]


# --------------------------------------------------------------------------- 2. folha do Stitch e jornada
def test_folha_do_stitch_e_inventario_da_jornada():
    telas = il.telas_da_folha(FOLHA_STITCH)
    assert [(t.id, t.titulo) for t in telas] == [
        ("E3-ALU-02", "Aposta travada com cadeado"), ("E0-PROF-02", "Preparação da aula"),
        ("E3-ALU-01", "Apresentação da aposta"), ("E9-ALU-01", "Tela que nenhum passo cita"),
    ], "a tabela da visão do professor repete a tela: sai uma só"
    assert il.propositos_da_jornada(JORNADA)["E1-ALU-01"] == "Abertura do álbum misterioso"


def test_folha_montada_pelo_stitch_cliente_e_lida_de_volta():
    """O contrato com `tools.stitch_cliente.montar_folha_de_links`: o que ele escreve, a exportação lê."""
    from tools.stitch_cliente import montar_folha_de_links

    folha = montar_folha_de_links({"project_id": "1", "url_projeto": "https://stitch.withgoogle.com/projects/1", "telas": [
        {"id": "a", "titulo": "E2-ALU-01 — Foto de perto", "largura": 1, "altura": 1, "dispositivo": "DESKTOP",
         "url_imagem": URL.format("x")},
        {"id": "b", "titulo": "E0-PROF-04 — Curadoria", "largura": 1, "altura": 1, "dispositivo": "DESKTOP",
         "url_imagem": None},
    ]}, "exp")
    telas = {t.id: t for t in il.telas_da_folha(folha)}
    assert telas["E2-ALU-01"].url_imagem == URL.format("x") and telas["E2-ALU-01"].titulo == "Foto de perto"
    assert telas["E0-PROF-04"].url_imagem is None


# --------------------------------------------------------------------------- 3. o .docx com as telas
def test_pedagogico_sai_com_a_imagem_de_cada_tela_debaixo_do_passo(tmp_path, monkeypatch, sem_rede):
    from pipeline.artifacts import exportar_one_pagers

    pedidos = []
    cores = {"e0prof02": "red", "e3alu01": "green", "e3alu02": "blue"}

    def baixar(url):
        pedidos.append(url)
        chave = url.rsplit("/", 1)[-1].split("=")[0]
        return _png(cores[chave])

    monkeypatch.setattr(il, "baixar_http", baixar)
    gerados = exportar_one_pagers(_estado(), tmp_path, "exp01ef1b")
    # na pasta de design desde o PR 10 (24/10/2026)
    assert {p.relative_to(tmp_path).as_posix() for p in gerados} == {"design/14-one-pager-pedagogico.docx",
                                                                     "design/14-one-pager-pedagogico.html"}

    sequencia, texto = _sequencia(tmp_path / "design/14-one-pager-pedagogico.docx")
    passos = [s for s in sequencia if s[0] in ("Heading 3", "imagem")]
    assert passos == [
        ("Heading 3", "Antes da aula — o preparo da professora"),
        ("imagem", "E0-PROF-02 — Preparação da aula"),
        ("Heading 3", "Passo 1 — Desafiar"),
        ("Heading 3", "Passo 3 — Decidir"),
        ("imagem", "E3-ALU-01 — Apresentação da aposta"),  # a ordem é a da linha, não a da folha
        ("imagem", "E3-ALU-02 — Aposta travada com cadeado"),
        ("Heading 3", "O mapa da missão: jornada e fluxo"),
    ]
    assert "E0-PROF-01 — Selecionar missão no catálogo" in texto, "tela sem desenho no Stitch fica nomeada"
    assert "E1-ALU-01 — Abertura do álbum misterioso" in texto
    assert "Telas deste passo" not in texto, "a âncora vira imagem; não aparece escrita"
    assert '"agente"' not in texto
    # só as telas citadas são baixadas, na largura de leitura
    assert sorted(pedidos) == sorted(URL.format(k) + "=w1200" for k in cores)
    with zipfile.ZipFile(tmp_path / "design/14-one-pager-pedagogico.docx") as z:
        midias = [n for n in z.namelist() if n.startswith("word/media/")]
    assert len(midias) >= 3

    # o .html leva as mesmas imagens, embutidas (o endereço do Stitch vence em dias), na mesma ordem
    pagina = (tmp_path / "design/14-one-pager-pedagogico.html").read_text(encoding="utf-8")
    posicoes = [pagina.index(f'alt="{r}"') for r in ("E0-PROF-02 — Preparação da aula",
                                                      "E3-ALU-01 — Apresentação da aposta",
                                                      "E3-ALU-02 — Aposta travada com cadeado")]
    assert posicoes == sorted(posicoes) and pagina.count("data:image/png;base64,") >= 4

    # a segunda exportação lê do cache da sessão: o endereço do Stitch pode já ter vencido
    pedidos.clear()
    monkeypatch.setattr(il, "baixar_http", lambda url: (_ for _ in ()).throw(AssertionError("baixou de novo")))
    exportar_one_pagers(_estado(), tmp_path, "exp01ef1b")
    assert ("imagem", "E3-ALU-02 — Aposta travada com cadeado") in _sequencia(tmp_path / "design/14-one-pager-pedagogico.docx")[0]
    from pipeline.artifacts import generate_artifact_manifest

    assert not any(m["path"].startswith(".cache") for m in generate_artifact_manifest(tmp_path))


def test_falha_de_download_nao_derruba_a_exportacao(tmp_path, monkeypatch, sem_rede):
    from pipeline.artifacts import exportar_one_pagers

    tentativas = []

    def baixar(url):
        tentativas.append(url)
        if "e3alu01" in url:
            raise httpx.ConnectTimeout("tempo esgotado")
        return _png("blue")

    monkeypatch.setattr(il, "baixar_http", baixar)
    gerados = exportar_one_pagers(_estado(), tmp_path, "exp01ef1b")
    assert len(gerados) == 2
    sequencia, texto = _sequencia(tmp_path / "design/14-one-pager-pedagogico.docx")
    assert ("imagem", "E3-ALU-02 — Aposta travada com cadeado") in sequencia
    assert "E3-ALU-01 — Apresentação da aposta: imagem indisponível" in texto
    documento = zipfile.ZipFile(tmp_path / "design/14-one-pager-pedagogico.docx").read("word/_rels/document.xml.rels").decode()
    assert URL.format("e3alu01") in documento, "a legenda leva o link para abrir a imagem fora"
    # rede fora não se resolve com outro endereço: a versão original não é tentada depois do timeout
    assert sum("e3alu01" in t for t in tentativas) == 1


def test_rede_fora_desiste_depois_de_tres_falhas(tmp_path, sem_rede):
    tentativas = []

    def baixar(url):
        tentativas.append(url)
        raise httpx.ConnectError("sem rede")

    folha = "\n".join(f"| E2-ALU-0{n} — Tela {n} | DESKTOP | — | [abrir imagem]({URL.format(n)}) |" for n in range(1, 7))
    doc = "Telas deste passo: " + " · ".join(f"`E2-ALU-0{n}`" for n in range(1, 7))
    ilustracoes = il.montar_ilustracoes({"stitch_links": folha}, doc, tmp_path, baixar=baixar, renderizador=None)
    figuras, _ = ilustracoes.do_passo([f"E2-ALU-0{n}" for n in range(1, 7)])
    assert len(tentativas) == il.FALHAS_ATE_DESISTIR
    assert all(f.aviso == il.INDISPONIVEL and f.link for f in figuras)


def test_outros_one_pagers_nao_ganham_imagem(tmp_path, monkeypatch, sem_rede):
    """A linha das telas só vira imagem no pedagógico; nos outros, é um parágrafo."""
    from pipeline.artifacts import exportar_one_pagers

    monkeypatch.setattr(il, "baixar_http", lambda url: (_ for _ in ()).throw(AssertionError("baixou")))
    produto = "# One-pager\n\nTelas deste passo: `E3-ALU-01`\n"
    exportar_one_pagers({"one_pager": produto, "stitch_links": FOLHA_STITCH}, tmp_path, "exp")
    _, texto = _sequencia(tmp_path / "produto/00-one-pager.docx")
    assert "Telas deste passo: E3-ALU-01" in texto


# --------------------------------------------------------------------------- 4. diagramas
def test_renderizador_desligado_nao_faz_requisicao(tmp_path, monkeypatch, sem_rede):
    """Padrão: nada sai daqui. O texto do fluxo da missão não vai a serviço nenhum, e o documento aponta
    o `09-diagramas.html`. `url` sem endereço também é desligado."""
    from config import get_settings
    from pipeline.artifacts import exportar_one_pagers
    from tools import miro_cliente

    def miro_proibido(*_a, **_k):
        raise AssertionError("abriu sessão no Miro")

    monkeypatch.setattr(miro_cliente.SessaoMiro, "__enter__", miro_proibido)
    assert get_settings().diagrama_imagem_fonte == "off"
    monkeypatch.setenv("DIAGRAMA_IMAGEM_FONTE", "url")
    assert get_settings().diagrama_imagem_fonte == "off", "url sem MERMAID_RENDER_URL não envia nada"
    monkeypatch.delenv("DIAGRAMA_IMAGEM_FONTE")

    estado = _estado(stitch_links="", miro_board={"url_board": "https://miro.com/app/board/abc=/", "widgets": {}})
    exportar_one_pagers(estado, tmp_path, "exp01ef1b")
    sequencia, texto = _sequencia(tmp_path / "design/14-one-pager-pedagogico.docx")
    assert ("Heading 3", "O mapa da missão: jornada e fluxo") in sequencia
    assert "design/09-diagramas.html" in texto and "https://miro.com/app/board/abc=/" in texto
    assert not any(s[0] == "imagem" and "Jornada" in (s[1] or "") for s in sequencia)
    # sem Stitch na sessão, a linha das telas fica como texto
    assert "Telas deste passo: E1-ALU-01" in texto


def test_renderizador_por_url_mermaid_ink_e_kroki(tmp_path):
    from tools.diagrama_imagem import Diagrama, RenderizadorUrl

    class Resposta:
        def __init__(self, conteudo, tipo="image/png"):
            self.content, self.headers = conteudo, {"content-type": tipo}

        def raise_for_status(self):
            return None

    class Cliente:
        def __init__(self):
            self.chamadas = []

        def get(self, url, **kw):
            self.chamadas.append(("GET", url, kw.get("params")))
            return Resposta(_png("white", (1600, 900)))

        def post(self, url, **kw):
            self.chamadas.append(("POST", url, kw.get("content")))
            return Resposta(_png("white", (1600, 900)))

    d = Diagrama("jornada", "Jornada do estudante", "journey\n  title X")
    cliente = Cliente()
    assert RenderizadorUrl("https://mermaid.ink/img/", cliente)(d).png
    assert RenderizadorUrl("https://kroki.io/mermaid/png", cliente)(d).png
    assert RenderizadorUrl("https://render.interno/m?c={codigo}", cliente)(d).png
    (m1, u1, p1), (m2, u2, c2), (m3, u3, _) = cliente.chamadas
    assert m1 == "GET" and u1.startswith("https://mermaid.ink/img/am91cm5leQ") and p1 == {"type": "png"}
    assert m2 == "POST" and u2 == "https://kroki.io/mermaid/png" and c2 == b"journey\n  title X"
    assert m3 == "GET" and u3.startswith("https://render.interno/m?c=am91cm5leQ")

    # com o renderizador ligado, a figura entra no fim do passo a passo do .docx
    from tools.docx_export import markdown_para_docx

    ilustracoes = il.montar_ilustracoes(_estado(), PEDAGOGICO, tmp_path / il.PASTA_CACHE,
                                        baixar=lambda url: _png("gray"),
                                        renderizador=RenderizadorUrl("https://kroki.io/mermaid/png", cliente))
    assert [f.rotulo for f in ilustracoes.diagramas] == ["Jornada do estudante", "Fluxo de telas", "Fluxo do professor"]
    assert ilustracoes.aviso_diagramas == ""
    markdown_para_docx(PEDAGOGICO, tmp_path / "p.docx", ilustracoes=ilustracoes)
    sequencia, _ = _sequencia(tmp_path / "p.docx")
    i = sequencia.index(("Heading 3", "O mapa da missão: jornada e fluxo"))
    assert sequencia[i + 1:i + 4] == [("imagem", "Jornada do estudante"), ("imagem", "Fluxo de telas"),
                                      ("imagem", "Fluxo do professor")]
    assert sequencia[i + 4] == ("Heading 2", "O que sua sala precisa ter")


def test_renderizador_falho_cai_na_frase(tmp_path):
    def quebrado(_d):
        raise httpx.ConnectError("fora do ar")

    ilustracoes = il.montar_ilustracoes(_estado(), PEDAGOGICO, tmp_path, baixar=lambda url: _png("gray"),
                                        renderizador=quebrado)
    assert ilustracoes.diagramas == [] and "design/09-diagramas.html" in ilustracoes.aviso_diagramas


class _SessaoFalsa:
    def __init__(self, svg):
        self.svg, self.chamadas = svg, []

    def __call__(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def chamar(self, ferramenta, argumentos):
        self.chamadas.append((ferramenta, argumentos))
        return {"svg": self.svg}


def test_miro_so_com_o_mermaid_devolve_nada():
    """O board guarda o Mermaid num `foreignObject`: se é isso que volta, não há desenho a aproveitar."""
    from tools.diagrama_imagem import Diagrama, RenderizadorMiro
    from tools.miro_cliente import montar_svg

    # o mesmo documento que a esteira publica (`canvas_create_from_svg`), como se voltasse igual
    publicado = montar_svg([{"id": "jornada", "titulo": "Jornada do estudante", "mermaid": "journey\n  title X"}],
                           {"jornada": "3458", "titulo-jornada": "3457"})
    sessao = _SessaoFalsa(publicado)
    r = RenderizadorMiro("https://miro.com/app/board/abc=/", {"jornada": "3458"}, sessao)
    assert r(Diagrama("jornada", "Jornada do estudante", "journey")) is None
    assert sessao.chamadas == [("canvas_read_as_svg", {"miro_url": "https://miro.com/app/board/abc=/"})]


def test_miro_desenhado_vira_figura(tmp_path):
    """Se o `canvas_read_as_svg` devolver o widget desenhado, ele é recortado pelo `data-miro-id`. Sem
    `cairosvg`, vai só para o `.html` (como SVG, por <img>), e o `.docx` mantém a frase."""
    from tools.diagrama_imagem import Diagrama, RenderizadorMiro

    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 3200 2000">'
           '<g data-miro-id="3458" x="0" y="0" width="1600" height="900"><rect width="100" height="40"/>'
           '<path d="M0 0 L10 10"/><text>Abre a pasta</text></g>'
           '<foreignObject data-miro-id="9999" data-type="diagram">stateDiagram-v2</foreignObject></svg>')
    sessao = _SessaoFalsa(svg)
    r = RenderizadorMiro("https://miro.com/app/board/abc=/", {"jornada": "3458", "fluxo": "9999"}, sessao)
    desenho = r(Diagrama("jornada", "Jornada do estudante", "journey"))
    assert desenho is not None and "<rect" in desenho.svg and 'viewBox="0 0 1600 900"' in desenho.svg
    assert "ns0:" not in desenho.svg
    assert r(Diagrama("fluxo", "Fluxo de telas", "stateDiagram-v2")) is None, "o fluxo só tem o Mermaid"
    assert len(sessao.chamadas) == 1, "o board é lido uma vez só"

    from tools.onepager_html import markdown_para_html

    estado = _estado(miro_board={"url_board": "https://miro.com/app/board/abc=/", "widgets": {"jornada": "3458"}})
    ilustracoes = il.montar_ilustracoes(estado, PEDAGOGICO, tmp_path, baixar=lambda url: _png("gray"),
                                        renderizador=RenderizadorMiro(estado["miro_board"]["url_board"],
                                                                      {"jornada": "3458"}, _SessaoFalsa(svg)))
    pagina = markdown_para_html(PEDAGOGICO, ilustracoes=ilustracoes)
    assert "data:image/svg+xml;base64," in pagina and 'alt="Jornada do estudante"' in pagina
    assert "design/09-diagramas.html" in pagina, "o fluxo não veio desenhado: a frase continua"


# --------------------------------------------------------------------------- 5. o prompt
def test_prompt_do_pedagogico_pede_o_passo_a_passo_com_as_telas():
    from prompts import load_prompt

    ped = load_prompt("dev/120_one_pager_pedagogico.md")
    for trecho in ("## Como a missão acontece, passo a passo", "### Antes da aula — o preparo da professora",
                   "### Passo 1 — Desafiar", "### Passo 6 — Refletir", "**Telas deste passo:**",
                   "Seção 3 — Inventário de telas", "Teste do passo a passo",
                   # o que o prompt já exigia continua lá
                   "## O podcast do fechamento", "## Como a gente sabe que a criança aprendeu",
                   "{conteudo_aprovado_pedagogico_report?}"):
        assert trecho in ped, trecho


def test_uma_imagem_por_tela_o_estado_padrao():
    """Desde que a esteira gera todos os estados no Stitch, cada tela tem várias imagens; o pedagógico mostra uma."""
    from tools.ilustracoes import Figura, Ilustracoes

    ilus = Ilustracoes(telas={"E2-ALU-01": [Figura("E2-ALU-01 — vazio"), Figura("E2-ALU-01 — padrão"),
                                            Figura("E2-ALU-01 — degradado")]})
    figuras, sem = ilus.do_passo(["E2-ALU-01", "E3-ALU-01"])
    assert [f.rotulo for f in figuras] == ["E2-ALU-01 — padrão"] and sem == ["E3-ALU-01"]


# --------------------------------------------------------------------------- 5. telas do protótipo, sem Stitch
PROTOTIPO_COM_QUADROS = """```html
<!DOCTYPE html><html><head><style>.quadro-tela:not(.tela-ativa) { display: none !important; }</style>
<script>alert(1)</script></head><body><div class="moldura-mobile">
<section class="quadro-tela" data-screen-id="E3-ALU-01" data-estado="erro"><p>Erro</p></section>
<section class="quadro-tela" data-screen-id="E3-ALU-01" data-estado="padrão">
  <div><p>Escolha a escala</p><button onclick="go()">Publicar</button></div></section>
</div><script>go()</script></body></html>
```"""


def test_sem_stitch_a_tela_vem_do_quadro_padrao_do_prototipo(tmp_path, sem_rede):
    """O Stitch está desligado por padrão (22/10/2026): sem ele, a tela do passo é o quadro do protótipo — o do estado
    padrão, ativo, sem script nem `onclick` —, no `.html` num iframe isolado e no `.docx` como legenda com o link."""
    from pipeline.artifacts import exportar_one_pagers

    quadros = il.quadros_do_prototipo(PROTOTIPO_COM_QUADROS)
    assert list(quadros) == ["E3-ALU-01"]
    quadro = quadros["E3-ALU-01"]
    assert "Escolha a escala" in quadro and "Erro" not in quadro and "tela-ativa" in quadro
    assert "<script" not in quadro and "onclick" not in quadro and ".quadro-tela:not(.tela-ativa)" in quadro

    documento = "# Ped\n\n### Passo 3 — Decidir\n\nA criança escolhe.\n\n**Telas deste passo:** `E3-ALU-01`\n"
    ilustracoes = il.montar_ilustracoes({"prototipo_html": PROTOTIPO_COM_QUADROS}, documento, tmp_path / "cache")
    assert ilustracoes.tem_telas and not ilustracoes.tem_stitch
    exportar_one_pagers({"one_pager_pedagogico": documento, "prototipo_html": PROTOTIPO_COM_QUADROS}, tmp_path, "exp")
    pagina = (tmp_path / "design/14-one-pager-pedagogico.html").read_text(encoding="utf-8")
    assert pagina.count('<iframe sandbox=""') == 1 and "Escolha a escala" in pagina and "abrir o protótipo" in pagina
    _, texto = _sequencia(tmp_path / "design/14-one-pager-pedagogico.docx")
    assert "tela do protótipo navegável" in texto and "Telas deste passo" not in texto


def test_prototipo_sem_marca_de_quadro_nao_da_tela():
    assert il.quadros_do_prototipo("<html><body><section>tela</section></body></html>") == {}
