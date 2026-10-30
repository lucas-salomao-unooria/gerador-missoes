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
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ferramentas  # noqa: E402

from google.antigravity import Agent, AgentBehavior, CapabilitiesConfig, LocalAgentConfig  # noqa: E402
from google.antigravity.types import BudgetConfig, CompactionConfig  # noqa: E402

#: Teto do histórico antes de o SDK compactar. Sem ele, a fundação da exp09ef1b (2 telas, 4 estados)
#: reenviou o contexto inteiro a cada passo: 13 milhões de tokens de prompt em 22 minutos.
LIMITE_CONTEXTO = 120_000

#: Ferramentas nativas liberadas. Sem `run_command`, sem web, sem subagente: o agente lê, escreve e olha.
NATIVAS = ["list_directory", "search_directory", "find_file", "view_file", "create_file", "edit_file", "finish"]


def _instrucoes(ws: Path) -> str:
    return (ws / "AGENTS.md").read_text(encoding="utf-8")


def _tarefa(ws: Path, lote: str, ids: list[str], fundacao: bool) -> str:
    missao = json.loads((ws / "dados" / "missao.json").read_text(encoding="utf-8"))
    linhas = [f"- `{q['id']}` · estado «{q['estado']}» · {q['ator']} · {q['largura']}×{q['altura']} · {q['proposito']}"
              for q in missao["quadros"] if q["id"] in ids]
    if fundacao:
        papel = ("Você está no **lote de fundação**. Antes das telas, crie `telas/_comum.tsx` com as molduras que "
                 "todas as telas vão reutilizar: `JanelaUnooriaAI` (o cliente UnooriaAI do estudante, composto como "
                 "nas telas de exemplo do Storybook; recebe `children` para a área da conversa e `aside` opcional "
                 "para um painel lateral) e `JanelaHub` (o painel do professor no Unooria Hub, com `titulo` e "
                 "`children`). Exporte também os blocos que você prevê repetidos (cartão de projeto, por exemplo). "
                 "Depois construa as telas âncora abaixo usando essas molduras. Os outros lotes vão rodar em "
                 "paralelo e só poderão LER `_comum.tsx`: ele precisa ficar estável e bem pensado.")
    else:
        papel = ("Use as molduras e os blocos de `telas/_comum.tsx` (leia o arquivo e as telas âncora já prontas em "
                 "`telas/` antes de começar) para que todas as telas pareçam da mesma família. **Não edite "
                 "`_comum.tsx`** nem os arquivos de tela de outros lotes: outros agentes estão trabalhando neles agora.")
    return (f"Workspace: `{ws}`. Lote `{lote}` da missão {missao['missao']} ({missao['titulo']}).\n\n{papel}\n\n"
            f"Leia `AGENTS.md` primeiro. Telas e estados deste lote ({len(linhas)} quadros):\n" + "\n".join(linhas) +
            "\n\nConstrua todos, veja a captura de cada estado e corrija o que estiver errado. Ao terminar, chame `finish` com o resumo.")


def _hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


async def rodar(ws: Path, lote: str, ids: list[str], fundacao: bool, modelo: str | None, max_rodadas: int,
                max_chamadas: int, saida: Path) -> dict:
    chamadas: list[dict] = []
    estado = {"html": None}
    capturadas: dict[tuple[str, str], float] = {}
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
        registrar("auditar_lote", {}, r.get("ok", False))
        return {"ok": r.get("ok", False) and not any(q["faltando"] or q["erro"] for q in quadros),
                "erro_geral": r.get("erro"),
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

    config = LocalAgentConfig(
        api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"),
        model=modelo,
        workspaces=[str(ws)],
        system_instructions=_instrucoes(ws),
        tools=[construir_lote, conferir_lint, auditar_lote, capturar_tela],
        capabilities=CapabilitiesConfig(agent_behavior=AgentBehavior.AUTONOMOUS, enabled_tools=NATIVAS),
        budget_config=BudgetConfig(max_model_calls=max_chamadas),
        compaction_config=CompactionConfig(token_threshold=LIMITE_CONTEXTO),
        save_dir=str(ws / ".build" / f"sdk-{lote}"),
    )
    comum = ws / "telas" / "_comum.tsx"
    hash_comum = _hash(comum)
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
                     "comum_alterado": (not fundacao) and _hash(comum) != hash_comum}
            pendente = (not gates["build"] or gates["faltando"] or gates["com_erro"] or gates["lint"]
                        or gates["sem_captura"] or gates["comum_alterado"])
            if not pendente:
                break
            mensagem = ("O lote ainda não passou nos gates da esteira. Corrija e confira de novo:\n"
                        + json.dumps({k: v for k, v in gates.items() if v and k != "build"}, ensure_ascii=False, indent=1)
                        + "\n\n`sem_captura` lista estados cujo arquivo mudou depois da última captura: capture e olhe."
                        + ("\n`_comum.tsx` foi alterado por este lote: desfaça a alteração, ele é só para leitura."
                           if gates["comum_alterado"] else ""))
    relatorio = {"lote": lote, "ids": ids, "fundacao": fundacao, "modelo": modelo or "padrão do SDK",
                 "rodadas": rodadas, "segundos": round(time.time() - t0), "uso": uso, "gates": gates,
                 "aprovado": not (not gates.get("build") or gates.get("faltando") or gates.get("com_erro")
                                  or gates.get("lint") or gates.get("comum_alterado")),
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
