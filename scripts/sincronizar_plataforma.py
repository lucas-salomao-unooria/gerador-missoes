"""Sincroniza, por cópia, a doutrina e os contratos canônicos da plataforma Unooria.

Os agentes de Dev (handoff, banca, PRD) leem a plataforma pelas cópias em
``prompts/references/plataforma/`` — nunca por resumo escrito à mão, que deriva sem
ninguém perceber. Quando a plataforma mudar, rode de novo:

    python scripts/sincronizar_plataforma.py            # usa ../plataforma-unooria
    PLATAFORMA_UNOORIA_DIR=/caminho python scripts/sincronizar_plataforma.py

O que o script faz:
1. copia os arquivos listados em ``FONTES`` (Markdown como está; código dentro de cerca);
2. recorta do ``schema.prisma`` só os modelos ``exp_0{4,6,7,8}_*`` (moldes de missão nova);
3. gera um índice de rotas a partir de ``docs/openapi.json``;
4. troca ``{identificador}`` por ``«identificador»`` — o ADK interpolaria ``{turmaId}`` como
   variável de estado e derrubaria o agente em execução;
5. grava ``versao-lida.json`` com o commit, a data e o SHA-256 de cada cópia.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESTINO = ROOT / "prompts" / "references" / "plataforma"
PLATAFORMA = Path(os.getenv("PLATAFORMA_UNOORIA_DIR", str(ROOT.parent / "plataforma-unooria"))).resolve()

# (origem relativa à plataforma, destino em prompts/references/plataforma/, linguagem da cerca ou None p/ Markdown)
FONTES: list[tuple[str, str, str | None]] = [
    ("AGENTS.md", "agents-raiz.md", None),
    ("CONTEXT.md", "contexto.md", None),
    ("apps/api/AGENTS.md", "agents-api.md", None),
    ("apps/experiencias/AGENTS.md", "agents-experiencias.md", None),
    ("apps/hub/AGENTS.md", "agents-hub.md", None),
    ("packages/sdk/AGENTS.md", "agents-sdk.md", None),
    ("packages/ui/AGENTS.md", "agents-ui.md", None),
    ("apps/api/src/telemetry/AGENTS.md", "agents-api-telemetry.md", None),
    ("apps/api/src/salas/AGENTS.md", "agents-api-salas.md", None),
    ("apps/api/src/ai/AGENTS.md", "agents-api-ai.md", None),
    ("apps/api/src/experiencias/AGENTS.md", "agents-api-experiencias.md", None),
    ("apps/api/src/recursos/AGENTS.md", "agents-api-recursos.md", None),
    ("scripts/e2e/AGENTS.md", "agents-e2e.md", None),
    ("docs/agents/domain.md", "glossario-dominio.md", None),
    ("docs/DECISOES.md", "decisoes-adr.md", None),
    ("docs/ARQUITETURA.md", "arquitetura.md", None),
    ("docs/INFRA.md", "infra.md", None),
    # contratos e código canônico (entram dentro de cerca)
    ("apps/api/src/telemetry/contrato-de-rotas.ts", "contrato-telemetria.md", "ts"),
    ("apps/api/src/experiencias/contrato-de-rotas.ts", "contrato-manifesto.md", "ts"),
    ("apps/api/src/progress/contrato-de-rotas.ts", "contrato-progresso.md", "ts"),
    ("apps/api/src/comum/liberacao.ts", "guarda-liberacao.md", "ts"),
    ("apps/api/src/auth/claims.ts", "perfis-claims.md", "ts"),
    ("apps/api/src/recursos/catalogo.ts", "produtos-catalogo.md", "ts"),
    ("apps/api/src/comum/series.ts", "series.md", "ts"),
    ("packages/sdk/src/types.ts", "sdk-types.md", "ts"),
    ("apps/hub/lib/experiencias-dev.ts", "experiencias-dev-portas.md", "ts"),
    # exemplar de missão nova (exp-08, a mais recente com preparação docente e gate de turma)
    ("apps/experiencias/exp-08-manifesto-ia/public/experiencia.json", "exemplo-manifesto-exp-08.md", "json"),
    ("apps/api/src/manifesto-ia/contrato-de-rotas.ts", "exemplo-contrato-rotas-exp-08.md", "ts"),
    ("apps/api/src/manifesto-ia/invariantes.ts", "exemplo-invariantes-exp-08.md", "ts"),
    ("apps/experiencias/exp-08-manifesto-ia/src/lib/telemetria.ts", "exemplo-telemetria-exp-08.md", "ts"),
    ("apps/api/prisma/migrations/20260910150000_exp_04_o_que_a_foto_conta/migration.sql", "exemplo-migration-exp-04.md", "sql"),
]
REGRAS_GLOB = "docs/regras/*.md"  # cada uma vira regras-<nome>.md
SCHEMA_PRISMA = "apps/api/prisma/schema.prisma"
OPENAPI = "docs/openapi.json"
MODELOS_EXEMPLO = re.compile(r'@@map\("exp_0[4678]_')

_VAR = re.compile(r"\{\s*([A-Za-z_][A-Za-z0-9_]*)\??\s*\}")


def neutralizar_chaves(texto: str) -> str:
    """`{turmaId}` → `«turmaId»`. O ADK interpolaria a forma original como variável de estado."""
    return _VAR.sub(lambda m: f"«{m.group(1)}»", texto)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=PLATAFORMA, text=True).strip()


def cabecalho(origem: str, commit: str, data: str) -> str:
    return (
        f"<!-- CÓPIA SINCRONIZADA de plataforma-unooria@{commit} ({data}) · origem: {origem} · "
        f"não edite: rode scripts/sincronizar_plataforma.py · placeholders entre chaves aparecem como «nome» "
        f"por limitação de interpolação do ADK; no código real use chaves -->\n\n"
    )


def copiar(origem: str, destino: str, cerca: str | None, commit: str, data: str) -> dict:
    src = PLATAFORMA / origem
    texto = src.read_text(encoding="utf-8")
    if cerca:
        texto = f"# `{origem}`\n\n```{cerca}\n{texto.rstrip()}\n```\n"
    texto = neutralizar_chaves(texto)
    conteudo = cabecalho(origem, commit, data) + texto
    (DESTINO / destino).write_text(conteudo, encoding="utf-8")
    return {"origem": origem, "destino": destino, "sha256": hashlib.sha256(conteudo.encode("utf-8")).hexdigest()[:16], "bytes": len(conteudo)}


def recortar_schema(commit: str, data: str) -> dict:
    texto = (PLATAFORMA / SCHEMA_PRISMA).read_text(encoding="utf-8")
    blocos = re.findall(r"(?:///[^\n]*\n)*model\s+\w+\s*\{.*?\n\}", texto, re.DOTALL)
    escolhidos = [b for b in blocos if MODELOS_EXEMPLO.search(b)]
    corpo = (
        f"# `{SCHEMA_PRISMA}` — só os modelos das missões-molde (exp-04, exp-06, exp-07, exp-08)\n\n"
        f"{len(escolhidos)} modelos. Padrões a imitar: `@@map(\"exp_NN_…\")`, `escola_id` em toda tabela sob RLS, "
        f"PK composta da sessão, `turma_id` denormalizado, `versao_instrumento`, `tentativa`, estado como string "
        f"(CHECK na migration, nunca enum), texto livre de menor em tabela própria com `chars_count`.\n\n```prisma\n"
        + "\n\n".join(escolhidos)
        + "\n```\n"
    )
    conteudo = cabecalho(SCHEMA_PRISMA, commit, data) + neutralizar_chaves(corpo)
    (DESTINO / "exemplo-schema-exp.md").write_text(conteudo, encoding="utf-8")
    return {"origem": SCHEMA_PRISMA, "destino": "exemplo-schema-exp.md", "sha256": hashlib.sha256(conteudo.encode()).hexdigest()[:16], "bytes": len(conteudo), "modelos": len(escolhidos)}


def indice_openapi(commit: str, data: str) -> dict:
    doc = json.loads((PLATAFORMA / OPENAPI).read_text(encoding="utf-8"))
    linhas = [f"# `{OPENAPI}` — índice de rotas (método · caminho · resumo · tags)", "", f"{len(doc['paths'])} caminhos. O contrato completo (Zod → OpenAPI) está no repositório; aqui só o mapa.", "", "| Método | Caminho | Resumo | Tags |", "|---|---|---|---|"]
    for caminho in sorted(doc["paths"]):
        for metodo, op in doc["paths"][caminho].items():
            if metodo.lower() not in ("get", "post", "put", "patch", "delete"):
                continue
            resumo = (op.get("summary") or "").replace("|", "\\|").strip()
            tags = ", ".join(op.get("tags") or [])
            linhas.append(f"| {metodo.upper()} | `{caminho}` | {resumo} | {tags} |")
    conteudo = cabecalho(OPENAPI, commit, data) + neutralizar_chaves("\n".join(linhas) + "\n")
    (DESTINO / "openapi-indice.md").write_text(conteudo, encoding="utf-8")
    return {"origem": OPENAPI, "destino": "openapi-indice.md", "sha256": hashlib.sha256(conteudo.encode()).hexdigest()[:16], "bytes": len(conteudo), "caminhos": len(doc["paths"])}


def main() -> int:
    if not PLATAFORMA.exists():
        print(f"plataforma não encontrada em {PLATAFORMA} (defina PLATAFORMA_UNOORIA_DIR)", file=sys.stderr)
        return 1
    DESTINO.mkdir(parents=True, exist_ok=True)
    for antigo in DESTINO.glob("*.md"):
        antigo.unlink()
    commit = git("rev-parse", "--short", "HEAD")
    data = git("log", "-1", "--format=%cs")
    branch = git("branch", "--show-current")
    arquivos = []
    for origem, destino, cerca in FONTES:
        if not (PLATAFORMA / origem).exists():
            print(f"  ⚠️ origem ausente, pulada: {origem}")
            continue
        arquivos.append(copiar(origem, destino, cerca, commit, data))
    for regra in sorted(PLATAFORMA.glob(REGRAS_GLOB)):
        arquivos.append(copiar(str(regra.relative_to(PLATAFORMA)), f"regras-{regra.stem}.md", None, commit, data))
    arquivos.append(recortar_schema(commit, data))
    arquivos.append(indice_openapi(commit, data))
    manifesto = {
        "plataforma_dir": str(PLATAFORMA),
        "commit": commit,
        "branch": branch,
        "data_commit": data,
        "sincronizado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "arquivos": arquivos,
    }
    (DESTINO / "versao-lida.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(a["bytes"] for a in arquivos)
    print(f"ok → {len(arquivos)} arquivos, {total/1024:.0f} KB, plataforma-unooria@{commit} ({branch}, {data})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
