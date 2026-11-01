"""Build, auditoria, lint e captura do protótipo em alta fidelidade — só biblioteca padrão.

Roda nas duas venvs: na da esteira (scripts e testes) e na isolada do Antigravity SDK, que exige
protobuf 7 e por isso não convive com o `google-cloud-aiplatform` da esteira. As três funções que o
agente chama como ferramenta (`construir`, `auditar`, `capturar`) devolvem só JSON: o SDK não aceita
imagem como resultado de ferramenta, então a captura vai para um PNG no workspace e o agente o abre
com o `view_file` nativo.

Nada aqui chama shell com texto vindo do modelo: os argumentos são ID e estado, conferidos contra
`dados/missao.json` antes de qualquer subprocesso.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

#: Chrome headless: o do Mac na máquina de desenvolvimento, o `chromium` no contêiner.
CHROME = os.getenv("CHROME_BIN") or next(
    (c for c in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", shutil.which("chromium"),
                 shutil.which("google-chrome")) if c and os.path.exists(c)), "")

#: Imports que uma tela pode fazer além das pontes do DS: React, os blocos comuns e o mock da fundação, a
#: API da casca (navegação e sessão), a casca do hub e as imagens geradas em `assets/`.
IMPORTS_PERMITIDOS = ("react", "./_comum", "../casca-api", "../dados/mock", "../plataforma")
#: A ponte da plataforma (`@edu/ui/ds`, `@edu/ui/ds-unooriaai`): como no código de produção, a tela nunca
#: importa o pacote do DS direto (`packages/ui/AGENTS.md`).
_RE_PONTE = re.compile(r"^@edu/ui/(ds(?:-[a-z]+)?)$")
_RE_DS_DIRETO = re.compile(r"^@unooria/design-system(?:/|$)")
#: Ponte × seção do pacote, quando o nome não é o mesmo (`packages/ui/package.json`).
PONTE_SECAO = {"ds": "unooria", "ds-insta": "instanooria", "ds-whatsapp": "whatsappmobile"}
_RE_ASSET = re.compile(r"^\.\./assets/([a-z0-9-]+\.webp)$")
_RE_IMPORT = re.compile(r"""^\s*import\s+(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]""", re.M)
#: `ir("E3-SIS-01")` ou `ir("E3-SIS-01", "espera de gate ativa")`: o destino tem de existir no inventário.
_RE_IR = re.compile(r"""\bir\(\s*["'`]([^"'`]+)["'`]\s*(?:,\s*["'`]([^"'`]+)["'`])?""")
#: Sinal de que a tela responde a alguma coisa: handler de evento, temporizador ou navegação.
_RE_INTERACAO = re.compile(
    r"\bon(?:Click|Change|Submit|KeyDown|DragStart|Drop|PointerDown|Select|ValueChange|Send|Press|Input|Focus)\b"
    r"|\bsetTimeout\(|\bir\("
)
#: Cor escrita à mão. Token do DS (`var(--uai-…)`, `var(--unooria-…)`) é o caminho permitido.
_RE_COR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")
#: O fallback de token (`var(--uai-bg-primary, #fff)`) é a convenção da plataforma: cor só enquanto a folha carrega.
_RE_FALLBACK = re.compile(r"var\(\s*--[\w-]+\s*,[^()]*(?:\([^()]*\)[^()]*)*\)")
#: Identificador com cara de documento (protocolo, autos, processo, data, hora): tem de existir nos insumos.
_RE_IDENTIFICADOR = re.compile(r"\b[A-Z]{2,}(?:-[A-Z0-9]+)*-\d[\w-]*\b|\b\d{1,4}/\d{2,4}-[A-Z]{2,}\b"
                               r"|\b\d{2}/\d{2}/\d{4}\b|\b\d{2}:\d{2}(?::\d{2})?\b")
_RE_PROIBIDO = {
    "fonte-propria": re.compile(r"fontFamily|font-family|@font-face|fonts\.googleapis"),
    "armazenamento": re.compile(r"localStorage|sessionStorage"),
    "estilo-global": re.compile(r"<style\b|document\.head|insertRule"),
    "rede": re.compile(r"\bfetch\(|XMLHttpRequest|https?://"),
}

CSS_CASCA = """
*{box-sizing:border-box}html,body{margin:0;height:100%}body{background:#E9ECEF;font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;color:#1A1A1A}
.hifi-app{display:grid;grid-template-columns:280px minmax(0,1fr) 370px;grid-template-rows:56px minmax(0,1fr) auto;height:100vh}
.hifi-trilho{grid-row:1/4;overflow-y:auto;overflow-x:hidden;background:#fff;border-right:1px solid #D5D9DD;min-width:0}
.hifi-titulo{padding:16px;font-weight:700;font-size:16px;border-bottom:1px solid #D5D9DD}.hifi-titulo small{display:block;font-weight:400;color:#5F6B76;font-size:13px}
.hifi-etapa{padding:14px 16px 6px;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:#5F6B76}
.hifi-trilho button{display:block;width:100%;text-align:left;border:0;background:none;padding:8px 16px;font:inherit;cursor:pointer;overflow-wrap:anywhere}
.hifi-trilho button.ativo{background:#E3EAF7;box-shadow:inset 3px 0 #3B5BDB}.hifi-trilho button:focus-visible,.hifi-barra button:focus-visible{outline:2px solid #3B5BDB;outline-offset:-2px}
.hifi-trilho em{font-style:normal;font-size:11px;border:1px solid #AEB6BF;border-radius:4px;padding:0 4px;margin-left:4px}.hifi-trilho span{font-size:13px;color:#5F6B76}
.hifi-barra{grid-column:2/4;display:flex;align-items:center;gap:12px;padding:0 20px;background:#fff;border-bottom:1px solid #D5D9DD;min-width:0}
.hifi-chip{background:#E3EAF7;padding:4px 10px;border-radius:6px;font-weight:600;white-space:nowrap}.hifi-esp{flex:1}
.hifi-barra button{border:1px solid #AEB6BF;background:#fff;border-radius:6px;padding:6px 12px;font:inherit;cursor:pointer}.hifi-barra button:disabled{opacity:.4}
.hifi-palco{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;padding:16px;min-width:0;min-height:0;overflow:hidden}
.hifi-legenda{font-size:11px;color:#5F6B76}
.hifi-quadro{position:relative;overflow:hidden;background:#fff;box-shadow:0 0 0 1px #C7CDD3,0 8px 24px rgba(0,0,0,.12);border-radius:8px}
.hifi-faltando,.hifi-erro{display:grid;place-items:center;height:100%;text-align:center;padding:24px;font:600 18px system-ui;color:#5F6B76;background:repeating-linear-gradient(45deg,#F4F5F7 0 12px,#ECEEF1 12px 24px)}
.hifi-erro{color:#B42318;background:#FEF3F2}
.hifi-painel{overflow-y:auto;overflow-x:hidden;background:#fff;border-left:1px solid #D5D9DD;padding:20px;font-size:15px;min-width:0;overflow-wrap:anywhere}
.hifi-painel h2{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:#5F6B76;margin:16px 0 4px}.hifi-painel h3{margin:0 0 8px;font-size:18px}.hifi-painel small{font-size:13px;color:#5F6B76}
.hifi-rodape{grid-column:2/4;padding:10px 20px;background:#fff;border-top:1px solid #D5D9DD;font-size:13px;overflow-wrap:anywhere}.hifi-rodape b{font-size:11px;color:#5F6B76;margin:0 4px 0 12px}
.hifi-captura{position:fixed;inset:0}.hifi-captura .hifi-quadro{border-radius:0;box-shadow:none}
.hifi-auditoria{position:absolute;left:-200000px;top:0}
.hifi-experiencia{position:relative;height:100%;overflow:hidden}
/* o preflight do Tailwind do hub, só no chrome do hub: a experiência é um iframe e não o recebe */
.hifi-hub :where(h1,h2,h3,h4,p,ul,ol,figure,blockquote){margin:0}.hifi-hub :where(ul,ol){list-style:none;padding:0}
.hifi-hub :where(a){color:inherit;text-decoration:inherit}.hifi-hub :where(img){display:block;max-width:100%}
:where(.hifi-hub,.hifi-hub *,.hifi-hub ::before,.hifi-hub ::after){border-width:0;border-style:solid;border-color:#e5e7eb}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""


def _ler_missao(ws: Path) -> Dict[str, Any]:
    return json.loads((ws / "dados" / "missao.json").read_text(encoding="utf-8"))


def pacote_do_ds(ws: str | Path) -> Dict[str, Any]:
    """As seções do pacote e quais têm CSS e folha de fontes, lidas dos `exports` do `package.json` do DS.

    É o pacote completo, e não uma lista nossa: seção nova publicada no DS entra sem mudar este arquivo.
    """
    caminho = Path(ws) / "node_modules" / "@unooria" / "design-system" / "package.json"
    exports = json.loads(caminho.read_text(encoding="utf-8")).get("exports", {})
    secoes = sorted(k[2:] for k in exports if re.fullmatch(r"\./[a-z]+", k))
    return {"versao": json.loads(caminho.read_text(encoding="utf-8")).get("version"), "secoes": secoes,
            "css": {s for s in secoes if f"./{s}.css" in exports},
            "fontes": {s for s in secoes if f"./fonts/{s}.css" in exports}}


def pontes(ws: str | Path) -> List[str]:
    """As pontes que `@edu/ui` exporta (`ds`, `ds-unooriaai`…), lidas do `package.json` copiado da plataforma."""
    caminho = Path(ws) / "node_modules" / "@edu" / "ui" / "package.json"
    if not caminho.exists():
        return []
    return sorted(k[2:] for k in json.loads(caminho.read_text(encoding="utf-8")).get("exports", {})
                  if re.fullmatch(r"\./ds(?:-[a-z]+)?", k))


def secao_da_ponte(ponte: str) -> str:
    return PONTE_SECAO.get(ponte, ponte[3:] if ponte.startswith("ds-") else ponte)


def _secoes_usadas(ws: Path, ids: Optional[List[str]]) -> List[str]:
    """Seções das pontes importadas pelas telas (do lote, mais `_comum.tsx`), as dos quadros e a `unooria` do hub."""
    usadas = {"unooria"}
    for arq in (ws / "telas").glob("*.tsx"):
        if ids and arq.stem not in ids and arq.stem != "_comum":
            continue
        for mod in _RE_IMPORT.findall(arq.read_text(encoding="utf-8")):
            m = _RE_PONTE.match(mod)
            if m:
                usadas.add(secao_da_ponte(m.group(1)))
    usadas |= {q.get("secao") for q in _ler_missao(ws)["quadros"] if q.get("secao") and (not ids or q["id"] in ids)}
    return sorted(usadas)


def _tailwind(ws: Path, destino: Path) -> Optional[str]:
    """Compila as utilitárias de layout do hub (Tailwind 3 do `apps/hub`, sem preflight) para as classes usadas."""
    cli = ws / "node_modules" / "tailwindcss" / "lib" / "cli.js"
    config = ws / "tailwind.config.cjs"
    if not cli.exists() or not config.exists():
        return "Tailwind do hub ausente no workspace"
    entrada = destino.with_suffix(".in.css")
    entrada.write_text("@tailwind utilities;\n", encoding="utf-8")
    proc = subprocess.run(["node", str(cli), "-c", str(config), "-i", str(entrada), "-o", str(destino), "--minify"],
                          cwd=ws, capture_output=True, text=True, timeout=120)
    return None if proc.returncode == 0 else (proc.stderr or proc.stdout)[-800:]


def _estilos(ws: Path, destino: Path, ids: Optional[List[str]]) -> List[str]:
    """`estilos.ts`: CSS e fontes só das seções em uso, o `plataforma.css` do hub, o Tailwind do hub e o CSS da missão.

    As 12 seções juntas levariam todas as fontes ao HTML. O CSS da missão (`estilos/*.css`) entra por
    último, como o `globals.css` de uma experiência.
    """
    pacote = pacote_do_ds(ws)
    secoes = [s for s in _secoes_usadas(ws, ids) if s in pacote["secoes"]]
    linhas = [f'import "@unooria/design-system/{s}.css";' for s in secoes if s in pacote["css"]]
    linhas += [f'import "@unooria/design-system/fonts/{s}.css";' for s in secoes if s in pacote["fontes"]]
    if (ws / "node_modules" / "@edu" / "ui" / "styles" / "plataforma.css").exists():
        linhas.append('import "@edu/ui/styles/plataforma.css";')
    if _tailwind(ws, destino.parent / "tailwind.css") is None and (destino.parent / "tailwind.css").exists():
        linhas.append('import "./tailwind.css";')
    linhas += [f'import "{css.resolve().as_posix()}";' for css in sorted((ws / "estilos").glob("*.css"))]
    destino.write_text("\n".join(linhas) + "\nexport {};\n", encoding="utf-8")
    return secoes


def _registro(ws: Path, destino: Path, ids: Optional[List[str]]) -> None:
    """`registro.ts`: importa as telas que existem (só as do lote, quando há lote)."""
    linhas, mapa = [], []
    for n, arq in enumerate(sorted((ws / "telas").glob("E*.tsx"))):
        tela_id = arq.stem
        if ids and tela_id not in ids:
            continue
        linhas.append(f'import * as t{n} from "{arq.resolve().as_posix()}";')
        mapa.append(f'  "{tela_id}": t{n},')
    destino.write_text("\n".join(linhas) + "\nexport const telas: Record<string, any> = {\n" + "\n".join(mapa) + "\n};\n",
                       encoding="utf-8")


def _esbuild(ws: Path) -> str:
    local = ws / "node_modules" / ".bin" / "esbuild"
    return str(local) if local.exists() else (shutil.which("esbuild") or "esbuild")


def construir(ws: str | Path, ids: Optional[List[str]] = None, saida: Optional[str | Path] = None) -> Dict[str, Any]:
    """Empacota casca + telas + DS num HTML único. `ids` restringe às telas de um lote.

    Devolve `{ok, html, kb, erros}`. Com lote, o build vai para um diretório próprio por chamada:
    lotes em paralelo não pisam no build um do outro, e a tela quebrada de um lote não derruba o outro.
    """
    ws = Path(ws).resolve()
    (ws / ".build").mkdir(exist_ok=True)
    trabalho = Path(tempfile.mkdtemp(prefix="lote-", dir=ws / ".build")) if ids else ws / ".build" / "final"
    trabalho.mkdir(parents=True, exist_ok=True)
    _registro(ws, trabalho / "registro.ts", ids)
    secoes = _estilos(ws, trabalho / "estilos.ts", ids)
    entrada = trabalho / "casca.tsx"
    # a cópia da casca aponta para o MESMO arquivo da `casca-api` que as telas importam: dois módulos
    # seriam dois contextos React, e o `ir()` das telas chamaria o contexto vazio
    entrada.write_text((ws / "casca.tsx").read_text(encoding="utf-8")
                       .replace('"./dados/missao.json"', f'"{(ws / "dados" / "missao.json").as_posix()}"')
                       .replace('"./casca-api"', f'"{(ws / "casca-api.tsx").as_posix()}"')
                       .replace('"./plataforma"', f'"{(ws / "plataforma.tsx").as_posix()}"')
                       .replace('"./gerado/registro"', '"./registro"')
                       .replace('"./gerado/estilos"', '"./estilos"'), encoding="utf-8")
    cmd = [_esbuild(ws), str(entrada), "--bundle", "--minify", "--format=iife", "--jsx=automatic",
           f"--outdir={trabalho / 'out'}", "--log-level=error", "--define:process.env.NODE_ENV=\"production\"",
           f"--tsconfig={ws / 'tsconfig.json'}",
           "--loader:.woff2=dataurl", "--loader:.woff=dataurl", "--loader:.ttf=dataurl", "--loader:.png=dataurl",
           "--loader:.webp=dataurl", "--loader:.svg=dataurl", "--loader:.jpg=dataurl"]
    proc = subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=180,
                          env={**os.environ, "NODE_PATH": str(ws / "node_modules")})
    if proc.returncode != 0:
        erros = [l for l in (proc.stderr or proc.stdout).splitlines() if l.strip()][:60]
        return {"ok": False, "html": None, "kb": 0, "erros": erros}
    out = trabalho / "out"
    js = (out / "casca.js").read_text(encoding="utf-8").replace("</script", "<\\/script")
    css = (out / "casca.css").read_text(encoding="utf-8") if (out / "casca.css").exists() else ""
    missao = _ler_missao(ws)
    pagina = (f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
              f'<meta name="viewport" content="width=device-width,initial-scale=1">'
              f"<title>{html.escape(missao.get('titulo', 'Protótipo'))} — protótipo</title>"
              f"<style>{css}{CSS_CASCA}</style></head><body><div id=\"raiz\"></div><script>{js}</script></body></html>")
    destino = Path(saida) if saida else trabalho / "prototipo.html"
    destino.write_text(pagina, encoding="utf-8")
    return {"ok": True, "html": str(destino), "kb": round(len(pagina.encode("utf-8")) / 1024), "erros": [],
            "secoes": secoes}


def _chrome(args: List[str], timeout: int = 120) -> subprocess.CompletedProcess:
    if not CHROME:
        raise RuntimeError("Chrome/Chromium não encontrado: defina CHROME_BIN.")
    perfil = tempfile.mkdtemp(prefix="hifi-chrome-")
    base = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-sandbox", "--no-first-run",
            f"--user-data-dir={perfil}", "--allow-file-access-from-files", "--run-all-compositor-stages-before-draw"]
    try:
        return subprocess.run(base + args, capture_output=True, text=True, timeout=timeout)
    finally:
        shutil.rmtree(perfil, ignore_errors=True)


def auditar(ws: str | Path, html_path: Optional[str] = None) -> Dict[str, Any]:
    """Abre o protótipo em `#auditoria` e devolve, por quadro, se falta, se quebrou e o texto visível."""
    ws = Path(ws)
    alvo = Path(html_path) if html_path else ws / ".build" / "final" / "prototipo.html"
    proc = _chrome(["--virtual-time-budget=6000", "--window-size=1600,1000", "--dump-dom",
                    alvo.resolve().as_uri() + "#auditoria"])
    m = re.search(r'<pre id="auditoria">(.*?)</pre>', proc.stdout, re.S)
    if not m or not m.group(1).strip():
        return {"ok": False, "erro": "a página não montou (erro de JavaScript antes da casca)", "quadros": []}
    quadros = json.loads(html.unescape(m.group(1)))
    faltando = [f"{q['id']} · {q['estado']}" for q in quadros if q["faltando"]]
    com_erro = [f"{q['id']} · {q['estado']}: {q['erro']}" for q in quadros if q["erro"]]
    sobrepostos = [f"{q['id']} · {q['estado']}: {s}" for q in quadros for s in q.get("sobreposicoes") or []]
    return {"ok": not com_erro, "quadros": quadros, "faltando": faltando, "com_erro": com_erro,
            "sobreposicoes": sobrepostos, "excesso_de_etiquetas": excesso_de_etiquetas(quadros)}


#: Etiquetas por tela. As missões codadas usam 4 a 9 `Tag`/`Badge` na missão INTEIRA (exp09ef1b: 6); a primeira
#: geração com o Argon pôs de 6 a 19 por tela, e o protótipo ficou com «cara de IA» (usuário, 30/10/2026).
LIMITE_ETIQUETAS = 3


def excesso_de_etiquetas(quadros: List[Dict[str, Any]], limite: int = LIMITE_ETIQUETAS) -> List[str]:
    """`ID · estado: n etiquetas («…», «…»)` de cada quadro acima do limite."""
    saida = []
    for q in quadros:
        e = q.get("etiquetas") or []
        if len(e) > limite:
            saida.append(f"{q['id']} · {q['estado']}: {len(e)} etiquetas (" + ", ".join(f"«{x}»" for x in e[:8]) + ")")
    return saida


def indice(ws: str | Path, tela_id: str, estado: str) -> int:
    for n, q in enumerate(_ler_missao(Path(ws))["quadros"]):
        if q["id"] == tela_id and q["estado"] == estado:
            return n
    raise ValueError(f"({tela_id}, {estado}) não está no inventário: use o ID e o estado exatos de dados/missao.json")


def slug(texto: str) -> str:
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower() or "padrao"


def capturar(ws: str | Path, tela_id: str, estado: str, html_path: Optional[str] = None) -> Dict[str, Any]:
    """PNG do quadro no tamanho real, em `capturas/<ID>--<estado>.png`."""
    ws = Path(ws)
    n = indice(ws, tela_id, estado)
    q = _ler_missao(ws)["quadros"][n]
    alvo = Path(html_path) if html_path else ws / ".build" / "final" / "prototipo.html"
    (ws / "capturas").mkdir(exist_ok=True)
    png = ws / "capturas" / f"{tela_id}--{slug(estado)}.png"
    if png.exists():
        png.unlink()
    _chrome(["--virtual-time-budget=4000", f"--window-size={q['largura']},{q.get('altura_total', q['altura'])}",
             f"--screenshot={png}", alvo.resolve().as_uri() + f"#captura={n}"])
    return {"ok": png.exists(), "png": str(png), "largura": q["largura"], "altura": q.get("altura_total", q["altura"])}


def interagir(ws: str | Path, tela_id: str, estado: str, acoes: List[Dict[str, Any]],
              html_path: Optional[str] = None) -> Dict[str, Any]:
    """Abre o quadro, executa as ações (clicar, digitar, arrastar, tecla, esperar) e diz onde a tela foi parar.

    Devolve a tela antes e depois (`ID|estado`), o resultado de cada passo, os erros da página e um PNG
    do fim em `capturas/<ID>--<estado>--interacao.png`.
    """
    ws = Path(ws)
    n = indice(ws, tela_id, estado)
    q = _ler_missao(ws)["quadros"][n]
    alvo = Path(html_path) if html_path else ws / ".build" / "final" / "prototipo.html"
    (ws / "capturas").mkdir(exist_ok=True)
    png = ws / "capturas" / f"{tela_id}--{slug(estado)}--interacao.png"
    entrada = json.dumps({"html": str(alvo.resolve()), "n": n, "largura": q["largura"], "altura": q.get("altura_total", q["altura"]),
                          "chrome": CHROME, "png": str(png), "acoes": acoes[:30]})
    proc = subprocess.run(["node", str(ws / "interagir.mjs"), entrada], cwd=ws, capture_output=True, text=True, timeout=180)
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {"erro": (proc.stderr or proc.stdout)[-1500:]}


def lint(ws: str | Path, ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Conferência estática das telas.

    Imports só do DS, da casca, do mock e de `assets/`; nenhuma cor escrita à mão; nada de fonte, rede ou
    armazenamento; tela com ação no inventário tem de responder a alguma coisa; e todo `ir()` aponta para
    uma tela (e um estado) do inventário.
    """
    ws = Path(ws)
    achados: List[Dict[str, str]] = []
    try:
        quadros = _ler_missao(ws)["quadros"]
    except FileNotFoundError:
        quadros = []
    estados_por_id: Dict[str, List[str]] = {}
    for q in quadros:
        estados_por_id.setdefault(q["id"], []).append(q["estado"])
    acao_por_id = {q["id"]: q.get("acao", "") for q in quadros}
    pontes_ok = set(pontes(ws))
    for arq in sorted((ws / "telas").iterdir()) if (ws / "telas").exists() else []:
        if not re.fullmatch(r"E\d-(?:ALU|PROF|SIS)-\d{2}\.tsx|_comum\.tsx", arq.name):
            achados.append({"arquivo": arq.name, "codigo": "arquivo-fora-do-contrato",
                            "trecho": "em telas/ só entram <ID>.tsx e _comum.tsx"})
    for css in sorted((ws / "estilos").glob("*.css")) if (ws / "estilos").exists() else []:
        achados += _lint_css(css)
    for arq in sorted((ws / "telas").glob("*.tsx")):
        if ids and arq.stem not in ids and arq.stem != "_comum":
            continue
        fonte = arq.read_text(encoding="utf-8")
        sem_comentario = re.sub(r"/\*.*?\*/|(?<![:\w])//[^\n]*", "", fonte, flags=re.S)
        for mod in _RE_IMPORT.findall(sem_comentario):
            asset, ponte = _RE_ASSET.match(mod), _RE_PONTE.match(mod)
            if asset:
                if not (ws / "assets" / asset.group(1)).exists():
                    achados.append({"arquivo": arq.name, "codigo": "imagem-inexistente", "trecho": mod})
            elif ponte:
                if pontes_ok and ponte.group(1) not in pontes_ok:
                    achados.append({"arquivo": arq.name, "codigo": "ponte-inexistente", "trecho": mod})
            elif _RE_DS_DIRETO.match(mod):
                achados.append({"arquivo": arq.name, "codigo": "import-direto-do-ds", "trecho": mod})
            elif mod not in IMPORTS_PERMITIDOS:
                achados.append({"arquivo": arq.name, "codigo": "import-fora-do-ds", "trecho": mod})
        for destino, estado in _RE_IR.findall(sem_comentario):
            if estados_por_id and (destino not in estados_por_id or (estado and estado not in estados_por_id[destino])):
                achados.append({"arquivo": arq.name, "codigo": "ir-para-tela-inexistente",
                                "trecho": f'ir("{destino}"{", " + repr(estado) if estado else ""})'})
        acao = acao_por_id.get(arq.stem, "")
        if arq.stem.startswith("E") and acao and not re.search(r"aguardar", acao, re.I) and not _RE_INTERACAO.search(sem_comentario):
            achados.append({"arquivo": arq.name, "codigo": "tela-sem-interacao", "trecho": acao[:80]})
        for m in _RE_COR.finditer(_RE_FALLBACK.sub("", sem_comentario)):
            achados.append({"arquivo": arq.name, "codigo": "cor-escrita-a-mao", "trecho": m.group(0)})
        for codigo, rx in _RE_PROIBIDO.items():
            for m in rx.finditer(sem_comentario):
                achados.append({"arquivo": arq.name, "codigo": codigo, "trecho": m.group(0)})
        if arq.stem.startswith("E") and not re.search(r"export\s+const\s+estados\b", fonte):
            achados.append({"arquivo": arq.name, "codigo": "sem-export-estados", "trecho": ""})
    return {"ok": not achados, "achados": achados}


def _lint_css(css: Path) -> List[Dict[str, str]]:
    """O CSS da missão: só tokens (hex só como fallback de `var()`), nada de fonte, e todo seletor escopado.

    `.hifi-experiencia` é a área do iframe e `.hifi-hub` o chrome do hub: no protótipo as duas convivem
    na mesma página, e um seletor solto (`body`, `.app`) vazaria para a casca e para as outras telas.
    """
    achados = []
    texto = re.sub(r"/\*.*?\*/", "", css.read_text(encoding="utf-8"), flags=re.S)
    for m in _RE_COR.finditer(_RE_FALLBACK.sub("", texto)):
        achados.append({"arquivo": f"estilos/{css.name}", "codigo": "cor-escrita-a-mao", "trecho": m.group(0)})
    for m in re.finditer(r"@font-face|@import|font-family\s*:", texto):
        achados.append({"arquivo": f"estilos/{css.name}", "codigo": "fonte-propria", "trecho": m.group(0)})
    for bloco in re.findall(r"(?:^|})\s*([^{}@]+?)\s*{", texto):
        for seletor in (s.strip() for s in bloco.split(",")):
            if seletor and not re.match(r"\.hifi-(?:experiencia|hub)\b|from\b|to\b|\d+%", seletor):
                achados.append({"arquivo": f"estilos/{css.name}", "codigo": "seletor-sem-escopo", "trecho": seletor[:60]})
    return achados


def identificadores_sem_fonte(quadros: List[Dict[str, Any]], corpus: str) -> List[str]:
    """Códigos de protocolo, autos, datas e horas mostrados na tela que não aparecem nos insumos.

    Na exp09ef1b com o 3.8 a tela ganhou «CMAS-2026-EXP09», «Autos: 2026/09-EF» e «DOC-MUN-2026-0894»: dados
    com cara de documento oficial que ninguém decidiu. O mock é escrito pelo agente, então não conta como fonte.
    """
    base = corpus.lower()
    vistos: List[str] = []
    for q in quadros:
        for linha in q.get("texto", []):
            for m in _RE_IDENTIFICADOR.finditer(linha):
                if m.group(0).lower() not in base and m.group(0) not in vistos:
                    vistos.append(m.group(0))
    return vistos


def lacunas(quadros: List[Dict[str, Any]]) -> List[str]:
    """As `[[LACUNA: …]]` que o agente deixou visíveis: decisões que faltam nos documentos, uma vez cada."""
    vistas: List[str] = []
    for q in quadros:
        for m in re.finditer(r"\[\[LACUNA:?\s*([^\]]+)\]\]", " ".join(q.get("texto", []))):
            if m.group(1).strip() not in vistas:
                vistas.append(m.group(1).strip())
    return vistas


def _norm(texto: str) -> str:
    s = unicodedata.normalize("NFKD", texto.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def rastrear_texto(quadros: List[Dict[str, Any]], corpus: str, minimo: int = 12) -> Dict[str, Any]:
    """Quanto do texto visível (linhas com 12+ caracteres) aparece nos documentos de design.

    Informativo: um rótulo do chrome nativo pode não estar no sheet, e uma frase composta de duas
    chaves não casa inteira. Serve para achar o quadro que inventou texto.
    """
    base = _norm(corpus)
    por_quadro, total, achadas = [], 0, 0
    for q in quadros:
        # o nome do ícone de ligadura («account_balance») é texto no DOM, mas o estudante vê o glifo
        linhas = [l for l in q.get("texto", []) if len(l) >= minimo and not re.fullmatch(r"[a-z]+(?:_[a-z]+)+", l)]
        fora = [l for l in linhas if _norm(l) not in base]
        total += len(linhas)
        achadas += len(linhas) - len(fora)
        por_quadro.append({"id": q["id"], "estado": q["estado"], "linhas": len(linhas), "fora": fora})
    return {"percentual": round(100 * achadas / total, 1) if total else 100.0, "linhas": total, "por_quadro": por_quadro}
