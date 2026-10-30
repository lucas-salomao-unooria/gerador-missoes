"""Motor de código do protótipo hi-fi sobre o Google Antigravity SDK — roda na venv `.venv-antigravity`.

Uso: `.venv-antigravity/bin/python tools/prototipo_hifi/motor_antigravity.py --ws <workspace> --lote etapa-2 --ids E2-ALU-01,E2-ALU-02`

Por que uma venv separada: o `google-antigravity` exige `protobuf>=7.35`, e o `google-cloud-aiplatform` e
o `opentelemetry-proto` da esteira exigem protobuf < 7. Este arquivo só importa a biblioteca padrão, o
SDK e o `ferramentas.py` vizinho.

O agente usa as ferramentas nativas de arquivo do SDK (ler, criar, editar), mas o `run_command` fica
desligado: build, lint, auditoria e captura são as quatro funções abaixo, que nunca passam texto do modelo
para um shell. O laço é fechado por gate: quando o agente encerra com estado faltando, tela quebrada,
achado de lint ou estado sem captura, recebe uma mensagem de continuação com o que falta, até
`--max-rodadas`.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ferramentas  # noqa: E402

from google.antigravity import Agent, AgentBehavior, CapabilitiesConfig, LocalAgentConfig  # noqa: E402
from google.antigravity.models import DEFAULT_MODEL  # noqa: E402
from google.antigravity.types import BudgetConfig, CompactionConfig  # noqa: E402

#: Teto do histórico antes de o SDK compactar. Sem ele, a fundação da exp09ef1b (2 telas, 4 estados)
#: reenviou o contexto inteiro a cada passo: 13 milhões de tokens de prompt em 22 minutos.
LIMITE_CONTEXTO = 120_000
#: Modelo de imagem (o padrão do SDK) e o teto de imagens novas por lote: cada uma leva ~5 s e entra
#: no HTML único como WebP de 20 a 60 KB.
MODELO_IMAGEM = "gemini-3.1-flash-lite-image"
MAX_IMAGENS_POR_LOTE = 8
ESTILO_IMAGEM = ("Imagem para o protótipo de uma atividade escolar brasileira (estudantes de 11 a 15 anos). "
                 "Fotografia realista ou ilustração limpa, conforme pedido. Sem texto legível, sem logotipo, "
                 "sem marca d'água, sem rosto de pessoa famosa. Pedido: ")


def _gerar_imagem(ws: Path, nome: str, descricao: str, largura: int) -> dict:
    """Gera com o Gemini Image e grava `assets/<nome>.webp` reduzido — o HTML único leva a imagem embutida."""
    import io
    from google import genai
    from google.genai import types as gtypes
    from PIL import Image

    cliente = genai.Client(api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    resposta = cliente.models.generate_content(model=MODELO_IMAGEM, contents=ESTILO_IMAGEM + descricao,
                                               config=gtypes.GenerateContentConfig(response_modalities=["IMAGE"]))
    for parte in resposta.candidates[0].content.parts:
        if parte.inline_data:
            imagem = Image.open(io.BytesIO(parte.inline_data.data)).convert("RGB")
            imagem.thumbnail((largura, largura))
            destino = ws / "assets" / f"{nome}.webp"
            destino.parent.mkdir(exist_ok=True)
            imagem.save(destino, "WEBP", quality=72)
            return {"ok": True, "import": f"../assets/{nome}.webp", "tamanho": list(imagem.size),
                    "kb": round(destino.stat().st_size / 1024)}
    return {"ok": False, "erro": "o modelo não devolveu imagem"}

#: Ferramentas nativas liberadas. Sem `run_command`, sem web, sem subagente: o agente lê, escreve e olha.
NATIVAS = ["list_directory", "search_directory", "find_file", "view_file", "create_file", "edit_file", "finish"]


def _instrucoes(ws: Path) -> str:
    return (ws / "AGENTS.md").read_text(encoding="utf-8")


def _tarefa(ws: Path, lote: str, ids: list[str], fundacao: bool) -> str:
    missao = json.loads((ws / "dados" / "missao.json").read_text(encoding="utf-8"))
    linhas = [f"- `{q['id']}` · estado «{q['estado']}» · {q['ator']} · seção `{q.get('secao', '?')}` · "
              f"{q['largura']}×{q['altura']} · {q['proposito']}" for q in missao["quadros"] if q["id"] in ids]
    secoes = sorted({q.get("secao", "unooria") for q in missao["quadros"]})
    if fundacao:
        papel = ("Você está no **lote de fundação**: define a cara que as outras telas vão seguir. Antes de "
                 "qualquer tela, leia em `referencias/` as experiências codadas da plataforma que usam as mesmas "
                 f"seções desta missão ({', '.join(secoes)}) e as telas do hub do professor. Depois crie:\n"
                 "1. `dados/mock.ts`: os dados mockados da missão INTEIRA, tirados dos `insumos/`, tipados e "
                 "exportados. É a base de dados do protótipo.\n"
                 "2. `estilos/missao.css`: o CSS da missão no molde do `src/estilos/globals.css` das experiências de "
                 "referência (mesma estrutura de `.app`, `.app__tela` e das classes de layout), com todo seletor "
                 "começando por `.hifi-experiencia`.\n"
                 "3. `telas/_comum.tsx`: a moldura de cada clone que a missão usa, montada como as experiências de "
                 "referência montam a delas (pela ponte `@edu/ui/ds-<clone>`), e os blocos que se repetem entre "
                 "telas. A casca do hub NÃO entra aqui: o professor usa `CascaProfessor` de `../plataforma`, e o "
                 "header do estudante a casca já desenha.\n"
                 "4. As imagens que a missão inteira vai usar (`gerar_imagem`), com nomes estáveis.\n"
                 "Depois construa as telas âncora abaixo, comparando cada captura com a referência da plataforma. "
                 "Os outros lotes vão rodar em paralelo e só poderão LER `_comum.tsx`, `dados/mock.ts` e "
                 "`estilos/missao.css`: eles precisam ficar estáveis e completos.")
    else:
        papel = ("Use `dados/mock.ts`, `estilos/missao.css`, os blocos de `telas/_comum.tsx`, a casca do hub de "
                 "`plataforma.tsx` e as imagens de `assets/`. Leia esses arquivos, as telas âncora em `telas/` e a "
                 "referência da plataforma equivalente a cada tela sua em `referencias/` antes de começar: todas "
                 "as telas têm de ser da mesma família e ter a cara da plataforma. **Não edite `_comum.tsx`, "
                 "`dados/mock.ts` nem `estilos/missao.css`**, nem as telas de outros lotes: outros agentes estão "
                 "trabalhando agora. Dado que falta no mock vai numa constante local da tela, citada no resumo.")
    return (f"Workspace: `{ws}`. Lote `{lote}` da missão {missao['missao']} ({missao['titulo']}).\n\n{papel}\n\n"
            f"Leia `AGENTS.md` primeiro. Telas e estados deste lote ({len(linhas)} quadros):\n" + "\n".join(linhas) +
            "\n\nConstrua todas as telas como componentes interativos, com as interações da mecânica (ficha de "
            "interação da seção 4 do one-pager e fluxo de arestas), exercite cada tela com `interagir_tela`, veja "
            "a captura de cada estado e corrija o que estiver errado. Ao terminar, chame `finish` com o resumo.")


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


async def rodar(ws: Path, lote: str, ids: list[str], fundacao: bool, modelo: str | None, max_rodadas: int,
                max_chamadas: int, saida: Path) -> dict:
    chamadas: list[dict] = []
    estado = {"html": None}
    capturadas: dict[tuple[str, str], float] = {}
    exercitadas: dict[str, float] = {}
    imagens: list[str] = []
    t0 = time.time()

    def registrar(nome: str, args: dict, ok: bool) -> None:
        chamadas.append({"t": round(time.time() - t0, 1), "ferramenta": nome, "args": args, "ok": ok})

    def construir_lote() -> dict:
        """Empacota as telas deste lote com a casca e o Design System num HTML. Devolve ok, tamanho em KB e erros de build."""
        r = ferramentas.construir(ws, ids)
        estado["html"] = r["html"]
        registrar("construir_lote", {}, r["ok"])
        return {"ok": r["ok"], "kb": r["kb"], "erros": r["erros"]}

    def conferir_lint() -> dict:
        """Lint estático das telas deste lote e de _comum.tsx: imports só do DS, sem cor escrita à mão, sem fonte, rede ou armazenamento."""
        r = ferramentas.lint(ws, ids)
        registrar("conferir_lint", {}, r["ok"])
        return r

    def auditar_lote() -> dict:
        """Abre o último build e diz, por estado deste lote, se falta, se deu erro ao montar e quantas linhas de texto mostra."""
        if not estado["html"]:
            return {"ok": False, "erro": "rode construir_lote antes"}
        r = ferramentas.auditar(ws, estado["html"])
        quadros = [q for q in r.get("quadros", []) if q["id"] in ids]
        sem_fonte = ferramentas.identificadores_sem_fonte(quadros, corpus)
        registrar("auditar_lote", {}, r.get("ok", False))
        return {"ok": r.get("ok", False) and not sem_fonte and not any(q["faltando"] or q["erro"] for q in quadros),
                "erro_geral": r.get("erro"),
                "identificadores_sem_fonte": sem_fonte,
                "sobreposicoes": [f"{q['id']} · {q['estado']}: {s}" for q in quadros for s in q.get("sobreposicoes") or []],
                "estados": [{"id": q["id"], "estado": q["estado"], "faltando": q["faltando"], "erro": q["erro"],
                             "linhas_de_texto": len(q["texto"])} for q in quadros]}

    def capturar_tela(tela_id: str, estado_da_tela: str) -> dict:
        """Gera o PNG do quadro (tela_id, estado_da_tela) no tamanho real, a partir do último build. Abra o PNG com view_file para ver a tela."""
        if not estado["html"]:
            return {"ok": False, "erro": "rode construir_lote antes"}
        if tela_id not in ids:
            return {"ok": False, "erro": f"{tela_id} não é deste lote"}
        try:
            r = ferramentas.capturar(ws, tela_id, estado_da_tela, estado["html"])
        except ValueError as e:
            registrar("capturar_tela", {"tela_id": tela_id, "estado": estado_da_tela}, False)
            return {"ok": False, "erro": str(e)}
        if r["ok"]:
            capturadas[(tela_id, estado_da_tela)] = time.time()
        registrar("capturar_tela", {"tela_id": tela_id, "estado": estado_da_tela}, r["ok"])
        return {**r, "proximo_passo": f"abra {r['png']} com view_file e confira a tela"}

    def interagir_tela(tela_id: str, estado_da_tela: str, acoes: list[dict]) -> dict:
        """Abre o quadro (tela_id, estado_da_tela) do último build e executa as ações em ordem, como um estudante.

        Cada ação é um objeto com uma chave: {"clicar": alvo}, {"digitar": [alvo, texto]},
        {"arrastar": [origem, destino]}, {"tecla": "Enter"} ou {"esperar": ms}. O alvo é um seletor do
        Playwright: "text=Começar Análise", "role=button[name=\\"Registrar Decisão\\"]" ou CSS. Devolve a tela
        antes e depois ("ID|estado"), o resultado de cada passo, os erros da página e um PNG do fim.
        """
        if not estado["html"]:
            return {"ok": False, "erro": "rode construir_lote antes"}
        if tela_id not in ids:
            return {"ok": False, "erro": f"{tela_id} não é deste lote"}
        try:
            r = ferramentas.interagir(ws, tela_id, estado_da_tela, acoes, estado["html"])
        except ValueError as e:
            return {"ok": False, "erro": str(e)}
        ok = not r.get("erro") and all(p.get("ok") for p in r.get("passos", []))
        if ok:
            exercitadas[tela_id] = time.time()
        registrar("interagir_tela", {"tela_id": tela_id, "estado": estado_da_tela, "acoes": len(acoes)}, ok)
        return {**r, "proximo_passo": "abra o png com view_file se quiser ver o fim da interação"}

    def gerar_imagem(nome: str, descricao: str, largura: int = 800) -> dict:
        """Gera uma imagem para a missão e grava em assets/<nome>.webp, pronta para `import x from "../assets/<nome>.webp"`.

        nome: minúsculas, números e hífen (ex.: "caderno-de-frequencia"). Se já existir, devolve a existente.
        descricao: o que a imagem mostra, em português, com enquadramento e estilo (foto realista ou ilustração).
        largura: maior lado em pixels (até 1024). Use o tamanho em que ela aparece na tela.
        """
        if not re.fullmatch(r"[a-z0-9-]{3,48}", nome):
            return {"ok": False, "erro": "nome: só minúsculas, números e hífen, de 3 a 48 caracteres"}
        destino = ws / "assets" / f"{nome}.webp"
        if destino.exists():
            return {"ok": True, "import": f"../assets/{nome}.webp", "reaproveitada": True}
        if len(imagens) >= MAX_IMAGENS_POR_LOTE:
            return {"ok": False, "erro": f"teto de {MAX_IMAGENS_POR_LOTE} imagens novas por lote: reaproveite as de assets/"}
        try:
            r = _gerar_imagem(ws, nome, descricao, max(160, min(int(largura), 1024)))
        except Exception as e:  # cota, filtro de segurança, rede: a tela segue sem a imagem
            r = {"ok": False, "erro": str(e)[:300]}
        if r["ok"]:
            imagens.append(nome)
        registrar("gerar_imagem", {"nome": nome}, r["ok"])
        return r

    config = LocalAgentConfig(
        api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"),
        model=modelo,
        workspaces=[str(ws)],
        system_instructions=_instrucoes(ws),
        tools=[construir_lote, conferir_lint, auditar_lote, capturar_tela, interagir_tela, gerar_imagem],
        capabilities=CapabilitiesConfig(agent_behavior=AgentBehavior.AUTONOMOUS, enabled_tools=NATIVAS),
        budget_config=BudgetConfig(max_model_calls=max_chamadas),
        compaction_config=CompactionConfig(token_threshold=LIMITE_CONTEXTO),
        save_dir=str(ws / ".build" / f"sdk-{lote}"),
    )
    comum = [ws / "telas" / "_comum.tsx", ws / "dados" / "mock.ts", ws / "estilos" / "missao.css"]
    corpus = "\n".join(p.read_text(encoding="utf-8") for p in sorted((ws / "insumos").glob("*.md")))
    hash_comum = [_hash(p) for p in comum]
    missao = json.loads((ws / "dados" / "missao.json").read_text(encoding="utf-8"))
    #: Tela que espera o professor ou o sistema (ação «Aguardar…») não tem o que exercitar.
    interativas = [i for i in ids if not any(q["id"] == i and "aguardar" in q.get("acao", "").lower()
                                             for q in missao["quadros"])]
    uso = {"prompt": 0, "cache": 0, "saida": 0, "pensamento": 0, "total": 0}
    textos: list[str] = []
    gates: dict = {}
    rodadas = 0
    async with Agent(config) as agente:
        mensagem = _tarefa(ws, lote, ids, fundacao)
        while rodadas < max_rodadas:
            rodadas += 1
            resposta = await agente.chat(mensagem)
            textos.append(await resposta.text())
            u = resposta.usage_metadata
            if u:
                uso["prompt"] += u.prompt_token_count or 0
                uso["cache"] += u.cached_content_token_count or 0
                uso["saida"] += u.candidates_token_count or 0
                uso["pensamento"] += u.thoughts_token_count or 0
                uso["total"] += u.total_token_count or 0
            # gate: o veredito é do código, não do resumo do agente
            build = ferramentas.construir(ws, ids)
            estado["html"] = build["html"]
            audit = ferramentas.auditar(ws, build["html"]) if build["ok"] else {"quadros": []}
            meus = [q for q in audit.get("quadros", []) if q["id"] in ids]
            lint = ferramentas.lint(ws, ids)
            mtime = max((p.stat().st_mtime for i in ids for p in [ws / "telas" / f"{i}.tsx"] if p.exists()), default=0)
            sem_captura = [f"{q['id']} · {q['estado']}" for q in meus
                           if capturadas.get((q["id"], q["estado"]), 0) < mtime - 1]
            gates = {"build": build["ok"], "erros_build": build["erros"][:10],
                     "faltando": [f"{q['id']} · {q['estado']}" for q in meus if q["faltando"]],
                     "com_erro": [f"{q['id']} · {q['estado']}: {q['erro']}" for q in meus if q["erro"]],
                     "lint": lint["achados"][:20], "sem_captura": sem_captura,
                     "sem_interacao": [i for i in interativas if i not in exercitadas],
                     "identificadores_sem_fonte": ferramentas.identificadores_sem_fonte(meus, corpus),
                     "sobreposicoes": [f"{q['id']} · {q['estado']}: {s}" for q in meus for s in q.get("sobreposicoes") or []],
                     "comum_alterado": (not fundacao) and [_hash(p) for p in comum] != hash_comum}
            pendente = (not gates["build"] or gates["faltando"] or gates["com_erro"] or gates["lint"]
                        or gates["sem_captura"] or gates["sem_interacao"] or gates["identificadores_sem_fonte"]
                        or gates["sobreposicoes"]
                        or gates["comum_alterado"])
            if not pendente:
                break
            mensagem = ("O lote ainda não passou nos gates da esteira. Corrija e confira de novo:\n"
                        + json.dumps({k: v for k, v in gates.items() if v and k != "build"}, ensure_ascii=False, indent=1)
                        + "\n\n`sem_captura` lista estados cujo arquivo mudou depois da última captura: capture e olhe."
                        + "\n`sem_interacao` lista telas que você ainda não exercitou com `interagir_tela`."
                        + "\n`sobreposicoes` são elementos de uma grade ou flex que invadem o vizinho: componente do DS "
                          "com largura fixa numa coluna mais estreita, por exemplo. Corrija o layout da tela."
                        + "\n`identificadores_sem_fonte` são códigos, datas ou horas na tela que não estão nos insumos: "
                          "use o dos documentos ou `[[LACUNA: …]]`."
                        + ("\n`_comum.tsx`, `dados/mock.ts` ou `estilos/missao.css` foi alterado por este lote: desfaça, eles são só para leitura."
                           if gates["comum_alterado"] else ""))
    relatorio = {"lote": lote, "ids": ids, "fundacao": fundacao, "modelo": modelo or f"{DEFAULT_MODEL} (padrão do SDK)",
                 "rodadas": rodadas, "segundos": round(time.time() - t0), "uso": uso, "gates": gates,
                 "imagens": imagens,
                 "aprovado": not (not gates.get("build") or gates.get("faltando") or gates.get("com_erro")
                                  or gates.get("lint") or gates.get("identificadores_sem_fonte") or gates.get("sobreposicoes")
                                  or gates.get("comum_alterado")),
                 "chamadas": chamadas, "resumo": textos[-1] if textos else ""}
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(relatorio, ensure_ascii=False, indent=1), encoding="utf-8")
    return relatorio


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ws", required=True)
    ap.add_argument("--lote", required=True)
    ap.add_argument("--ids", required=True, help="IDs de tela separados por vírgula")
    ap.add_argument("--fundacao", action="store_true")
    ap.add_argument("--modelo", default=None)
    ap.add_argument("--max-rodadas", type=int, default=4)
    ap.add_argument("--max-chamadas", type=int, default=250, help="teto de chamadas ao modelo no lote")
    ap.add_argument("--saida", default=None)
    a = ap.parse_args()
    ws = Path(a.ws).resolve()
    saida = Path(a.saida) if a.saida else ws / "relatorios" / f"{a.lote}.json"
    r = asyncio.run(rodar(ws, a.lote, a.ids.split(","), a.fundacao, a.modelo, a.max_rodadas, a.max_chamadas, saida))
    print(json.dumps({k: r[k] for k in ("lote", "aprovado", "rodadas", "segundos", "uso")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
