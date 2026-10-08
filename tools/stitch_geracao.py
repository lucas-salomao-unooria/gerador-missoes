"""Gera no Stitch, FORA do modelo, uma tela por (ID, estado) do inventário — todas, sempre.

Até 07/10/2026 quem chamava o Stitch era o agente de telas, dentro da própria resposta. Ele decidia
quantas gerar, e o prompt mandava "priorizar": o Stitch saía com 27% a 68% do inventário, as telas do
professor no preparo caíam em quase todas as missões, e na exp09ef1b o agente declarou dez screenIds
que o projeto não tinha. Mesmo sem a ordem de priorizar, havia um teto: o orçamento de resposta de
ferramenta por agente (cerca de 25 respostas) não cabe em 25 a 46 estados de tela.

Aqui o modelo só especifica — a tabela «Geração no Stitch», uma linha por (tela, estado) com o prompt
— e o código gera: cria (ou reaproveita) o projeto, sobe o DESIGN.md com os nove tokens do lo-fi, chama
`generate_screen_from_text` para cada linha, em paralelo, e registra o screenId que o Stitch DEVOLVEU.
Linha que o modelo esqueceu sai do inventário da jornada, com um prompt montado das colunas dele. O que
já existe no projeto não é gerado de novo; o que mudou de prompt é.

Contrato da ferramenta (lido do `tools/list` do servidor em 07/10/2026): a geração leva minutos; em
timeout NÃO se repete — procura-se a tela depois. Por isso a conciliação relê o projeto antes de tentar
de novo o que faltou, e tenta uma vez só.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional

from tools import telas

logger = logging.getLogger("stitch_geracao")

#: Os nove tokens do lo-fi — os mesmos nomes da coleção `wireframe-cinza` e do protótipo.
TOKENS = (
    ("superficie-base", "#FFFFFF"), ("superficie-elevada", "#FAFAFA"), ("superficie-midia", "#E0E0E0"),
    ("borda-padrao", "#C7C7C7"), ("borda-foco", "#1A1A1A"), ("texto-primario", "#1A1A1A"),
    ("texto-secundario", "#6B6B6B"), ("acao-primaria", "#1A1A1A"), ("acao-secundaria", "#EDEDED"),
)
_RE_TELA = re.compile(r"projects/(\d+)/screens/([0-9a-f]{32})", re.I)
_RE_PROJETO = re.compile(r"projects/(\d{6,})")
_RE_ASSET = re.compile(r"assets/\d+")


def design_md() -> str:
    """O DESIGN.md do lo-fi: nove tokens e as regras que o Stitch precisa para não inventar cor."""
    linhas = ["# DESIGN.md — wireframe lo-fi (escala de cinza)", "", "## Tokens", ""]
    linhas += [f"- `{nome}`: {valor}" for nome, valor in TOKENS]
    linhas += ["", "## Regras", "",
               "- Escala de cinza apenas: sem cor, sem sombra, sem gradiente, sem imagem decorativa.",
               "- Mídia é um retângulo `superficie-midia` com um X grande em `borda-padrao` e legenda curta.",
               "- Alvo de toque mínimo de 64 px (88 px na projeção). Uma família tipográfica.",
               "- Seleção é `borda-foco` com 4 px; desabilitado é `acao-secundaria` com `texto-secundario`."]
    return "\n".join(linhas) + "\n"


def _norm(texto: str) -> str:
    sem = "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", sem).strip(" `*_")


def titulo(item: Dict[str, str], versao: int = 1) -> str:
    """O título da tela no Stitch. A partir da segunda versão leva `· vN`: o Stitch não renomeia nem apaga tela, e a
    refeita convive no projeto com a anterior — é o título que diz qual é a atual (decisão do usuário, 08/10/2026)."""
    base = f"{item['id']} — {item['estado']}"
    return base if versao <= 1 else f"{base} · v{versao}"


def _hash(item: Dict[str, str]) -> str:
    return hashlib.sha1(f"{item['dispositivo']}|{item['prompt']}".encode("utf-8")).hexdigest()[:12]


def _tabela_apos(texto: str, titulo_rx: str) -> List[Dict[str, str]]:
    """As linhas da primeira tabela depois do título que casa `titulo_rx`, com as colunas normalizadas."""
    m = re.search(rf"^#{{1,4}}[^\n]*{titulo_rx}[^\n]*$", texto or "", re.I | re.M)
    if not m:
        return []
    cabecalho: List[str] = []
    linhas: List[Dict[str, str]] = []
    for linha in texto[m.end():].splitlines():
        s = linha.strip()
        if not s:
            if linhas:
                break
            continue
        if s.startswith("#") or (cabecalho and not s.startswith("|")):
            break
        if not s.startswith("|") or re.fullmatch(r"\|[\s:|-]+\|?", s):
            continue
        celulas = [c.strip() for c in s.strip("|").split("|")]
        if not cabecalho:
            cabecalho = [_norm(c) for c in celulas]
            continue
        linhas.append(dict(zip(cabecalho, celulas)))
    return linhas


def itens_do_relatorio(relatorio: str) -> List[Dict[str, str]]:
    """As linhas da tabela «Geração no Stitch» do agente de telas, lidas pelo nome das colunas."""
    itens: List[Dict[str, str]] = []
    for d in _tabela_apos(relatorio, r"gera[çc][ãa]o no stitch"):
        ident = telas.normalizar(d.get("id", "") or d.get("id tela", ""))
        prompt = next((v for k, v in d.items() if k.startswith("prompt")), "")
        if not ident or not prompt.strip():
            continue
        dispositivo = next((v for k, v in d.items() if k.startswith(("dispositivo", "device"))), "")
        itens.append({"id": ident, "estado": (d.get("estado") or "").strip(" `*_") or "padrão",
                      "dispositivo": "DESKTOP" if "desk" in dispositivo.lower() else "MOBILE",
                      "prompt": prompt.strip()})
    return itens


def completar(itens: List[Dict[str, str]], jornada: str, desktop_padrao: bool = False) -> List[Dict[str, str]]:
    """Toda (tela, estado) do inventário tem linha: a que o modelo esqueceu é montada das colunas da jornada.

    Tela de professor e de projeção é sempre DESKTOP; a de estudante segue o viewport (casca → MOBILE).
    """
    vistos = {(i["id"], _norm(i["estado"])) for i in itens}
    saida = list(itens)
    colunas = {telas.normalizar(d.get("id", "")): d for d in _tabela_apos(jornada, r"invent[áa]rio de telas")}
    for t in telas.inventario(jornada)["telas"]:
        for estado in (t["estados"] or ["padrão"]):
            if (t["id"], _norm(estado)) in vistos:
                continue
            d = colunas.get(t["id"], {})
            partes = [f"{t['id']} — {d.get('proposito', '').strip() or 'tela'}, estado {estado}."]
            for rotulo, chave in (("Elementos", "elementos na tela"), ("Ação", "acao (verbo nativo)"),
                                  ("Resultado", "resultado da acao"), ("Ambiente", "ambiente")):
                if d.get(chave):
                    partes.append(f"{rotulo}: {d[chave]}.")
            professor = "PROF" in t["id"] or "projec" in _norm(d.get("cenario de dispositivo", ""))
            saida.append({"id": t["id"], "estado": estado, "prompt": " ".join(partes), "origem": "inventario",
                          "dispositivo": "DESKTOP" if professor or desktop_padrao else "MOBILE"})
            vistos.add((t["id"], _norm(estado)))
    return saida


def _telas_no_projeto(chamar: Callable, projeto: str) -> Dict[str, str]:
    """`título → screenId` do que já existe no projeto (o `list_screens` às vezes volta vazio: tudo bem)."""
    try:
        dados = chamar("list_screens", {"projectId": projeto}) or {}
    except Exception as exc:  # leitura é conveniência: sem ela, gera-se o que não tem registro
        logger.warning("list_screens falhou em %s: %s", projeto, exc)
        return {}
    saida = {}
    for t in dados.get("screens") or []:
        m = _RE_TELA.search(str(t.get("name") or ""))
        if m and t.get("title"):
            saida[str(t["title"]).strip()] = m.group(2).lower()
    return saida


_RE_SO_TELA = re.compile(r"screens/([0-9a-f]{32})\b", re.I)
_RE_CAMPO_ID = re.compile(r'"(?:screenId|screen_id|id)"\s*:\s*"([0-9a-f]{32})"', re.I)


def _screen_id(resposta: Any, projeto: str) -> Optional[str]:
    """O screenId que a geração devolveu, procurado em qualquer parte da resposta.

    O formato da resposta não está no esquema da ferramenta, e nenhuma sessão guardou uma crua; o que se
    sabe (pensamento do agente na exp02em1b: "screen `966431a0…` is done") é que ela traz o id de 32
    hexadecimais. Em ordem de confiança: o nome completo do recurso, `screens/<id>`, um campo de id.
    Sem nenhum, a conciliação relê o projeto.
    """
    texto = json.dumps(resposta, ensure_ascii=False)
    for p, s in _RE_TELA.findall(texto):
        if p == projeto:
            return s.lower()
    m = _RE_SO_TELA.search(texto) or _RE_CAMPO_ID.search(texto)
    return m.group(1).lower() if m else None


def gerar(itens: List[Dict[str, str]], registro: Dict[str, Dict[str, str]], *, projeto: Optional[str],
          design_system: Optional[str], titulo_projeto: str, chamar: Callable, paralelo: int = 4,
          esperar: Callable[[float], None] = time.sleep, tentativas_de_conciliacao: int = 3) -> Dict[str, Any]:
    """Gera o que falta e devolve `{projeto, design_system, registro, resultado}`.

    `registro` é o que já foi gerado nesta missão: `"ID|estado" → {screen_id, hash}`. Item com o mesmo hash
    e screenId conhecido não é gerado de novo; item com prompt novo é (o retrabalho mudou a tela).
    """
    if not projeto:
        criado = chamar("create_project", {"title": titulo_projeto}) or {}
        m = _RE_PROJETO.search(str(criado.get("name") or "")) or _RE_PROJETO.search(json.dumps(criado))
        if not m:
            raise RuntimeError(f"create_project não devolveu o projeto: {str(criado)[:200]}")
        projeto = m.group(1)
    if not design_system:
        chamar("upload_design_md", {"projectId": projeto,
                                    "designMdBase64": base64.b64encode(design_md().encode("utf-8")).decode("ascii")})
        achado = _RE_ASSET.findall(json.dumps(chamar("list_design_systems", {"projectId": projeto}) or {}))
        design_system = achado[0] if achado else None

    existentes = _telas_no_projeto(chamar, projeto)
    registro = {k: dict(v) for k, v in (registro or {}).items()}
    pendentes = []
    #: a versão que cada item pendente vai ter: a tela que muda (hash novo sobre um screenId conhecido) sobe uma
    versao: Dict[int, int] = {}
    for item in itens:
        chave, h = f"{item['id']}|{item['estado']}", _hash(item)
        anterior = registro.get(chave) or {}
        if anterior.get("screen_id") and anterior.get("hash") == h:
            continue
        if not anterior and titulo(item) in existentes:  # gerado numa execução anterior, sem registro
            registro[chave] = {"screen_id": existentes[titulo(item)], "hash": h, "versao": 1}
            continue
        atual = int(anterior.get("versao") or 1)
        versao[id(item)] = atual + 1 if anterior.get("screen_id") else atual
        pendentes.append(item)

    def um(item: Dict[str, str]) -> Dict[str, Any]:
        argumentos = {"projectId": projeto, "prompt": f"{titulo(item, versao.get(id(item), 1))}. {item['prompt']}",
                      "deviceType": item["dispositivo"]}
        if design_system:
            argumentos["designSystem"] = design_system
        try:
            return {"item": item, "screen_id": _screen_id(chamar("generate_screen_from_text", argumentos), projeto) or "",
                    "erro": ""}
        except Exception as exc:  # timeout ou queda: a geração pode ter dado certo — concilia depois
            return {"item": item, "screen_id": "", "erro": str(exc)[:200]}

    feitos: List[Dict[str, Any]] = []
    if pendentes:
        with ThreadPoolExecutor(max_workers=max(1, paralelo)) as pool:
            feitos = list(pool.map(um, pendentes))
    sem_id = [f for f in feitos if not f["screen_id"]]
    # conciliação: relê o projeto antes de tentar de novo (a ferramenta pede para não repetir em timeout)
    for _ in range(tentativas_de_conciliacao if sem_id else 0):
        esperar(30)
        existentes = _telas_no_projeto(chamar, projeto)
        for f in sem_id:
            f["screen_id"] = existentes.get(titulo(f["item"], versao.get(id(f["item"]), 1)), "")
        sem_id = [f for f in sem_id if not f["screen_id"]]
        if not sem_id:
            break
    if sem_id:  # uma nova tentativa, só para o que a conciliação não achou
        with ThreadPoolExecutor(max_workers=max(1, paralelo)) as pool:
            refeitos = list(pool.map(um, [f["item"] for f in sem_id]))
        for f, r in zip(sem_id, refeitos):
            f["screen_id"], f["erro"] = r["screen_id"], r["erro"] or f["erro"]
    for f in feitos:
        if f["screen_id"]:
            registro[f"{f['item']['id']}|{f['item']['estado']}"] = {"screen_id": f["screen_id"], "hash": _hash(f["item"]),
                                                                     "versao": versao.get(id(f["item"]), 1)}

    falhas = {id(f["item"]): f for f in feitos if not f["screen_id"]}
    resultado = []
    for item in itens:
        falha = falhas.get(id(item))
        resultado.append({"id": item["id"], "estado": item["estado"], "origem": item.get("origem", "telas"),
                          "screen_id": "" if falha else (registro.get(f"{item['id']}|{item['estado']}") or {}).get("screen_id", ""),
                          "erro": (falha["erro"] or "sem resposta do Stitch") if falha else ""})
    return {"projeto": projeto, "design_system": design_system, "registro": registro, "resultado": resultado}


def relatorio(saida: Dict[str, Any], url_projeto: str = "") -> str:
    """A seção que vai para o fim da cobertura dos wireframes: o que existe no Stitch, com o screenId real."""
    res = saida["resultado"]
    ok = [r for r in res if r["screen_id"]]
    linhas = ["## Telas geradas no Stitch (esteira)", "",
              f"Projeto: `projects/{saida['projeto']}`" + (f" — {url_projeto}" if url_projeto else ""),
              f"Design system: `{saida.get('design_system') or '—'}` · **{len(ok)} de {len(res)}** (tela, estado) gerados. "
              "O screenId é o que o Stitch devolveu; nenhum é escrito por modelo.", "",
              "| ID tela | Estado | screenId | Origem do prompt | Situação |", "|---|---|---|---|---|"]
    for r in res:
        situacao = "gerada" if r["screen_id"] else f"FALTOU — {r['erro']}"
        origem = "inventário (a tabela do agente não trazia)" if r["origem"] == "inventario" else "agente de telas"
        linhas.append(f"| {r['id']} | {r['estado']} | {r['screen_id'] or '—'} | {origem} | {situacao} |")
    return "\n".join(linhas) + "\n"


def rotulos(registro: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    """`screenId → "ID — estado"`: a folha de links nomeia a tela pelo inventário, não pelo título do Stitch."""
    return {v["screen_id"]: k.replace("|", " — ") + (f" · v{v['versao']}" if int(v.get("versao") or 1) > 1 else "")
            for k, v in (registro or {}).items() if v.get("screen_id")}
