"""Protótipo em alta fidelidade com o Design System real, escrito por um agente de código.

O A079 escreve o protótipo lo-fi inteiro numa resposta só (cerca de 170 KB, perto do teto de saída),
sem compilar e sem ver o resultado. Aqui o modelo escreve uma tela por arquivo (`telas/<ID>.tsx`),
com os componentes de `@unooria/design-system`, e o código faz o resto. O esbuild empacota casca,
telas, React, CSS e fontes num HTML único e offline. A casca de revisão é fixa (`modelo/casca.tsx`),
e as conferências (build, cobertura, lint, captura) são determinísticas (`ferramentas.py`).

O motor é o Antigravity SDK (`motor_antigravity.py`), que roda numa venv isolada porque exige
protobuf 7. Estudo e decisões: `docs/planos/2026-10-30-prototipo-alta-fidelidade.md`.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools import telas as _telas

MODELO = Path(__file__).parent / "modelo"

#: Documentos de design e de produto que o agente lê, pelo nome do arquivo na sessão.
INSUMOS = (
    "design/00-anexo-design-spec.md", "design/00b-ambiente-simulado.md", "design/01-briefing-oficio.md",
    "design/02-jornada-telas.md", "design/03-fluxo-arestas.md", "design/04b-camada-caa.md",
    "design/05-wireframes-cobertura.md", "design/06-copy-strings-revisada.md",
    "produto/00-one-pager.md", "produto/05-spec-missao.md",
)
#: Desde 29/10/2026 a missão não tem Etapa 6 (PR #98): tela `E6-*` num inventário é resto de versão antiga.
ETAPAS_FORA = {"6"}
#: Tamanho do quadro quando o cenário de dispositivo não traz medidas: o hub é desktop, e a experiência
#: do estudante é a área útil do iframe do hub.
TAMANHO_PADRAO = {"PROF": (1366, 768), "ALU": (1024, 768), "SIS": (1024, 768)}
_RE_MEDIDA = re.compile(r"(\d{3,4})\s*[×x]\s*(\d{3,4})")
#: O header do hub acima da área do iframe (`apps/hub/components/header-plataforma.tsx`: h-16 + borda).
ALTURA_HEADER_HUB = 65
#: Onde mora o código da plataforma nesta máquina; no Job, o preparo baixa o repositório.
PLATAFORMA_PADRAO = Path("/Volumes/Documentos/Unooria/plataforma-unooria")
#: Referências da cara do hub para as telas do professor, relativas a `apps/hub/` da plataforma.
REFERENCIAS_HUB = (
    "components/header-plataforma.tsx", "components/casca-plataforma.tsx", "components/menu-da-conta.tsx",
    "components/trilha.tsx", "components/cartao-missao.tsx", "components/cartao-atividade.tsx",
    "components/instrucao-da-experiencia.tsx", "app/(plataforma)/professor/layout.tsx",
    "app/(plataforma)/professor/page.tsx", "app/(plataforma)/professor/entre-redes/[ano]/[unidade]/page.tsx",
    "app/(plataforma)/professor/entre-redes/[ano]/[unidade]/atividades-da-missao.tsx",
    "app/(plataforma)/professor/atividades/nova/page.tsx",
    "app/(plataforma)/professor/atividades/nova/formulario-atividade.tsx",
    "app/(plataforma)/professor/atividades/[id]/page.tsx",
    "app/(plataforma)/professor/atividades/[id]/painel-revisao.tsx",
    "app/(plataforma)/professor/atividades/[id]/painel-etapas.tsx",
    "app/(plataforma)/professor/atividades/[id]/painel-progresso.tsx",
)
#: Regras de DS e de experiência da plataforma, relativas à raiz do monorepo.
REFERENCIAS_REGRAS = ("docs/regras/design-system.md", "packages/ui/AGENTS.md", "packages/ui/styles/AGENTS.md",
                      "apps/experiencias/AGENTS.md", "apps/experiencias/_template/src/App.tsx",
                      "apps/experiencias/_template/src/estilos/globals.css")
#: Atributo de tema de cada seção do DS, lido dos tokens do pacote 0.2.26. O WhatsApp só tem o escuro;
#: `unooria` e `tiktooria` não usam atributo. Seção nova sem entrada aqui abre no tema padrão dela.
TEMAS = {
    "chatgpt": ("data-gpt-theme", "light"), "instanooria": ("data-insta-theme", "light"),
    "unooblog": ("data-ubl-theme", "light"), "unoochat": ("data-unc-theme", "light"),
    "unoogaleria": ("data-ugl-theme", "light"), "unoojornal": ("data-ujn-theme", "light"),
    "unooriaai": ("data-uai-theme", "light"), "unootube": ("data-uni-theme", "light"),
    "unoovista": ("data-unv-theme", "light"), "whatsappmobile": ("data-wa-theme", "dark"),
}
#: Nome da seção na missão × nome do módulo no pacote (`secao_para_marca` da base da plataforma).
APELIDOS = {"unitube": "unootube"}


def secao_do_ambiente(ambiente: str, secoes: List[str]) -> str:
    """A seção do DS de um quadro, pela coluna «Ambiente» do inventário. Hub, plataforma e professor são `unooria`."""
    nome = _telas._norm(ambiente).strip("*_` ")
    nome = APELIDOS.get(nome, nome)
    if nome in secoes:
        return nome
    achada = next((s for s in sorted(secoes, key=len, reverse=True) if s in nome.replace(" ", "")), None)
    return achada or "unooria"


def _colunas_do_inventario(jornada: str) -> Dict[str, Dict[str, str]]:
    """Por ID, as colunas que o `tools.telas.inventario` não guarda: propósito, ação, resultado e dispositivo."""
    m = re.search(r"^#{1,4}[^\n]*invent[áa]rio de telas[^\n]*$", jornada, re.I | re.M)
    if not m:
        return {}
    cabecalho, linhas = None, {}
    for s in (l.strip() for l in jornada[m.end():].splitlines()):
        if s.startswith("#"):
            break
        if not s.startswith("|") or re.fullmatch(r"\|[\s:|-]+\|?", s):
            continue
        celulas = [c.strip() for c in s.strip("|").split("|")]
        if cabecalho is None:
            cabecalho = [_telas._norm(c).strip("*_` ") for c in celulas]
            continue
        d = dict(zip(cabecalho, celulas))
        i = _telas.normalizar(d.get("id", "").strip("*_` "))
        if i:
            linhas[i] = d
    return linhas


def _coluna(d: Dict[str, str], prefixo: str) -> str:
    return next((v.replace("*", "").strip() for k, v in d.items() if k.startswith(prefixo)), "")


def _etapas(one_pager: str, inventario: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """Texto do painel por etapa: a seção 4 do one-pager (`### Etapa N — Nome`); a Etapa 0 vem do 0.2."""
    etapas: Dict[str, Dict[str, str]] = {}
    for m in re.finditer(r"^###\s+Etapa\s+(\d+)\s*[—–-]\s*(.+?)\s*$(.*?)(?=^##|\Z)", one_pager, re.M | re.S):
        texto = re.sub(r"\s+", " ", re.sub(r"[*_`>#|]", "", m.group(3))).strip()
        etapas[m.group(1)] = {"nome": f"Etapa {m.group(1)} — {m.group(2).strip()}",
                              "texto": texto[:1200] + ("…" if len(texto) > 1200 else ""),
                              "fonte": "One-pager §4"}
    preparo = re.search(r"^###\s+\d+\.\s+O professor prepara[^\n]*\n(.*?)(?=^###|^##|\Z)", one_pager, re.M | re.S)
    if any(t["etapa"] == "0" for t in inventario):
        etapas["0"] = {"nome": "Etapa 0 — Preparo do professor",
                       "texto": re.sub(r"\s+", " ", preparo.group(1)).strip() if preparo else "",
                       "fonte": "One-pager §0.2" if preparo else ""}
    return etapas


def dados_da_missao(sessao: Path, secoes: Optional[List[str]] = None) -> Dict[str, Any]:
    """`dados/missao.json`: um quadro por (tela, estado) do inventário, com a seção do DS de cada um, mais o
    texto do painel por etapa. `secoes` são as do pacote do DS; sem elas, vale o que a coluna «Ambiente» disser."""
    jornada = (sessao / "design" / "02-jornada-telas.md").read_text(encoding="utf-8")
    one_pager = (sessao / "produto" / "00-one-pager.md").read_text(encoding="utf-8")
    inventario = [t for t in _telas.inventario(jornada)["telas"] if t["etapa"].strip() not in ETAPAS_FORA]
    colunas = _colunas_do_inventario(jornada)
    quadros = []
    for t in inventario:
        d = colunas.get(t["id"], {})
        medida = _RE_MEDIDA.search(_coluna(d, "cenario"))
        ator = t["ator"].strip().upper()
        largura, altura = (int(medida.group(1)), int(medida.group(2))) if medida else TAMANHO_PADRAO.get(ator, (1024, 768))
        for estado in t["estados"] or ["padrão"]:
            # o estudante vê a missão dentro do hub: o quadro soma o header acima da área do iframe
            altura_total = altura + (0 if ator == "PROF" else ALTURA_HEADER_HUB)
            quadros.append({"id": t["id"], "estado": estado, "etapa": t["etapa"].strip(), "ator": ator,
                            "altura_total": altura_total,
                            "ambiente": t["ambiente"],
                            "secao": secao_do_ambiente(t["ambiente"], secoes or list(TEMAS) + ["unooria"]),
                            "proposito": _coluna(d, "proposito"),
                            "acao": _coluna(d, "acao"), "resultado": _coluna(d, "resultado"),
                            "largura": largura, "altura": altura})
    titulo = re.search(r"^#\s+.*?\(([^)]+)\)", jornada, re.M)
    slug = re.search(r"\bexp\d{2}[a-z]{2}\d[a-z]\b", jornada)
    return {"missao": slug.group(0) if slug else sessao.name, "titulo": titulo.group(1) if titulo else sessao.name,
            "quadros": quadros, "etapas": _etapas(one_pager, inventario), "temas": TEMAS}


def _ligar(origem: Path, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.is_symlink() or destino.exists():
        destino.unlink()
    destino.symlink_to(origem)


def _copiar(origem: Path, destino: Path) -> None:
    if origem.is_dir():
        shutil.copytree(origem, destino, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("node_modules", "dist", ".turbo", "*.test.*", "*.map"))
    elif origem.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(origem, destino)


def _experiencias_de_referencia(plataforma: Path, secoes: List[str], excluir: str) -> Dict[str, List[str]]:
    """Por seção, as experiências codadas que importam a ponte dela — o padrão que a missão nova deve seguir.

    A missão que está sendo prototipada fica de fora: copiar o código dela seria responder à prova com o gabarito.
    """
    raiz = plataforma / "apps" / "experiencias"
    achadas: Dict[str, List[str]] = {s: [] for s in secoes}
    # missão primeiro (`exp*`), depois os outros produtos (`app-*`): a referência é como uma MISSÃO se parece
    for exp in sorted(raiz.iterdir(), key=lambda p: (not p.name.startswith("exp"), p.name)) if raiz.exists() else []:
        if not exp.is_dir() or exp.name.startswith(("_", "backup")) or exp.name == excluir or not (exp / "src").exists():
            continue
        fonte = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in (exp / "src").rglob("*.tsx"))
        for s in secoes:
            ponte = next((k for k, v in {"ds": "unooria", "ds-insta": "instanooria", "ds-whatsapp": "whatsappmobile"}.items()
                          if v == s), f"ds-{s}")
            if re.search(rf"""["']@edu/ui/{re.escape(ponte)}["']""", fonte):
                achadas[s].append(exp.name)
    return achadas


def montar_referencias(ws: Path, plataforma: Path, secoes: List[str], excluir: str) -> Dict[str, Any]:
    """`referencias/`: regras, a cara do hub e as experiências codadas que usam as mesmas seções. Só leitura."""
    ref = ws / "referencias"
    for rel in REFERENCIAS_REGRAS:
        _copiar(plataforma / rel, ref / "regras" / rel.replace("/", "__"))
    for rel in REFERENCIAS_HUB:
        _copiar(plataforma / "apps" / "hub" / rel, ref / "hub" / rel)
    por_secao = _experiencias_de_referencia(plataforma, secoes, excluir)
    for nomes in por_secao.values():
        for nome in nomes[:4]:
            _copiar(plataforma / "apps" / "experiencias" / nome / "src", ref / "experiencias" / nome / "src")
            _copiar(plataforma / "apps" / "experiencias" / nome / "AGENTS.md", ref / "experiencias" / nome / "AGENTS.md")
    return {"experiencias_por_secao": {s: v[:4] for s, v in por_secao.items()}, "excluida": excluir}


def montar_workspace(sessao: str | Path, destino: str | Path, ds: str | Path,
                     plataforma: Optional[str | Path] = None) -> Path:
    """Monta o projeto em que o agente trabalha. `ds` é a raiz do pacote do DS (com `dist/`, `src/` e `node_modules/`).

    O DS e o React entram por link simbólico: o build resolve `@unooria/design-system/<seção>` pelos
    `exports` do pacote, e uma única cópia do React serve casca, telas e DS.
    """
    sessao, ws, ds = Path(sessao), Path(destino), Path(ds).resolve()
    ws.mkdir(parents=True, exist_ok=True)
    for nome in ("casca.tsx", "casca-api.tsx", "plataforma.tsx", "interagir.mjs", "AGENTS.md", "tsconfig.json"):
        shutil.copy(MODELO / nome, ws / nome)
    for pasta in ("telas", "dados", "insumos", "capturas", "assets", "estilos", "referencias", ".build"):
        (ws / pasta).mkdir(exist_ok=True)
    for rel in INSUMOS:
        if (sessao / rel).exists():
            shutil.copy(sessao / rel, ws / "insumos" / Path(rel).name)
    _ligar(ds, ws / "node_modules" / "@unooria" / "design-system")
    from tools.prototipo_hifi.ferramentas import pacote_do_ds
    pacote = pacote_do_ds(ws)
    dados = dados_da_missao(sessao, pacote["secoes"])
    dados["ds"] = {"versao": pacote["versao"], "secoes": pacote["secoes"]}
    plataforma = Path(plataforma) if plataforma else PLATAFORMA_PADRAO
    if plataforma.exists():
        # a ponte `@edu/ui` é COPIADA (não ligada): ligada, os imports dela resolveriam no node_modules do
        # pnpm da plataforma e o bundle levaria um segundo React e um segundo DS
        for parte in ("package.json", "src", "styles"):
            _copiar(plataforma / "packages" / "ui" / parte, ws / "node_modules" / "@edu" / "ui" / parte)
        # o pacote do Tailwind do hub (o real, não o shim do pnpm: ele acha o `cli.js` relativo a si mesmo)
        tailwind = plataforma / "apps" / "hub" / "node_modules" / "tailwindcss"
        if tailwind.exists():
            _ligar(tailwind.resolve(), ws / "node_modules" / "tailwindcss")
        (ws / "tailwind.config.cjs").write_text(
            "// O Tailwind do hub (apps/hub/tailwind.config.ts): só utilitárias de layout. Sem preflight: a\n"
            "// experiência é um iframe e não o recebe; o reset do chrome do hub está na casca (.hifi-hub).\n"
            f"module.exports = {{ content: [{json.dumps(str(ws / 'telas') + '/**/*.tsx')}, "
            f"{json.dumps(str(ws / 'plataforma.tsx'))}], theme: {{ extend: {{}} }}, "
            "corePlugins: { preflight: false }, plugins: [] };\n", encoding="utf-8")
        secoes_missao = sorted({q["secao"] for q in dados["quadros"]})
        dados["referencias"] = montar_referencias(ws, plataforma, secoes_missao, dados["missao"])
    (ws / "dados" / "missao.json").write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    for pacote in ("react", "react-dom", "scheduler", "playwright-core"):
        _ligar(ds / "node_modules" / pacote, ws / "node_modules" / pacote)
    _ligar((ds / "node_modules" / ".bin" / "esbuild").resolve(), ws / "node_modules" / ".bin" / "esbuild")
    return ws


def lotes(missao: Dict[str, Any], ancoras: Optional[List[str]] = None, por_lote: int = 2) -> List[Dict[str, Any]]:
    """Fundação primeiro (âncoras + `_comum.tsx`), depois lotes de até `por_lote` telas da mesma etapa.

    A fundação fixa a moldura de cada ambiente; os lotes seguintes rodam em paralelo e só leem `_comum.tsx`.
    Lote pequeno é conversa curta: o custo de um agente cresce com o histórico que ele reenvia a cada
    passo, e um lote com a etapa inteira acumula documentos e capturas de todas as telas dela.
    """
    ids = list(dict.fromkeys(q["id"] for q in missao["quadros"]))
    if ancoras is None:
        prof = next((i for i in ids if "-PROF-" in i), None)
        alu = next((i for i in ids if "-ALU-" in i), None)
        ancoras = [i for i in (prof, alu) if i]
    resultado = [{"nome": "fundacao", "ids": ancoras, "fundacao": True}]
    por_etapa: Dict[str, List[str]] = {}
    for q in missao["quadros"]:
        if q["id"] not in ancoras:
            por_etapa.setdefault(q["etapa"], [])
            if q["id"] not in por_etapa[q["etapa"]]:
                por_etapa[q["etapa"]].append(q["id"])
    for e, v in por_etapa.items():
        for n in range(0, len(v), por_lote):
            parte = v[n:n + por_lote]
            nome = f"etapa-{e}" if len(v) <= por_lote else f"etapa-{e}{chr(ord('a') + n // por_lote)}"
            resultado.append({"nome": nome, "ids": parte, "fundacao": False})
    return resultado
