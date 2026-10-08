"""Toda tela do inventário está em todo artefato que a desenha? Conferido por ID, não por contagem.

A auditoria de 07/10/2026 contou, nas 7 sessões do bucket com design, cada ID de tela em cada
derivado. Jornada, fluxo, copy, cobertura e protótipo tinham 100% dos IDs — mas o Stitch tinha de 27%
a 68% (o prompt das telas mandava "priorize… declare o que ficou fora", e as telas do professor
`E0-PROF-01/03/05` caíam em quase todas), o protótipo tinha um quadro por tela e não um por estado, e
a `exp04ef1b` tinha duas telas `EREV-ALU-*` fora do padrão que nenhum gate via. As conferências que
existiam comparavam **contagem**: cinco quadros, três deles estados da mesma tela, aprovavam com três
IDs faltando.

Aqui a lista canônica sai da tabela «Seção 3 — Inventário de telas» da jornada, lida pelo nome das
colunas, e cada derivado é conferido contra ela por **conjunto de IDs**. Cada falta vira achado com o
dono do conserto (`agente_responsavel`), que o despacho de retrabalho executa.
"""
from __future__ import annotations

import json
import re
import unicodedata
from typing import Any, Dict, List, Optional

AGENTE = "cobertura-telas"

#: O ID canônico: `E<etapa>-<ator>-<nn>`. O fluxo escreve `E1_ALU_01` dentro do `stateDiagram`, e o
#: protótipo marca estado com sufixo de letra (`E0-PROF-03b`) — os dois contam como a tela base.
RE_ID = re.compile(r"\bE(\d)[-_](ALU|PROF|SIS)[-_](\d{2})([A-Za-z])?(?![\w])")
_RE_ID_CANONICO = re.compile(r"^E\d-(?:ALU|PROF|SIS)-\d{2}$")
#: As cinco telas do preparo do professor são obrigatórias (`prompts/design/22_jornada.md`).
PREPARO_DO_PROFESSOR = tuple(f"E0-PROF-0{n}" for n in range(1, 6))
_RE_COMENTARIO = re.compile(r"<!--.*?-->|/\*.*?\*/", re.S)
_RE_TAG_COM_QUADRO = re.compile(r"<[^>]*\bdata-screen-id\s*=[^>]*>", re.I)
_RE_ATRIBUTO = re.compile(r"\bdata-(screen-id|estado)\s*=\s*[\"']([^\"']*)[\"']", re.I)

#: Derivado → (chave do estado, rótulo, dono do conserto). O Stitch tem conferência própria
#: (`tools/afirmacoes.cobertura_stitch`), sobre a folha que o `list_screens` devolve.
DERIVADOS = (
    ("fluxo_arestas", "fluxo", "fluxo"),
    ("copy_strings_revisada", "copy revisada", "copy-ptbr-revisao"),
    ("wireframes_cobertura", "cobertura (wireframes)", "telas"),
)


def _norm(texto: str) -> str:
    sem = "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", sem).strip()


def normalizar(bruto: str) -> Optional[str]:
    """`E1_ALU_01`, `e1-alu-01`, `E0-PROF-03b` → `E1-ALU-01` / `E0-PROF-03`; o resto → None."""
    m = RE_ID.search((bruto or "").replace("`", "").strip().upper())
    if not m:
        return None
    return f"E{m.group(1)}-{m.group(2)}-{m.group(3)}"


def ids(texto: str) -> List[str]:
    """IDs de tela citados no texto, normalizados, sem repetição, na ordem em que aparecem."""
    vistos: List[str] = []
    for m in RE_ID.finditer(texto or ""):
        i = f"E{m.group(1)}-{m.group(2)}-{m.group(3)}"
        if i not in vistos:
            vistos.append(i)
    return vistos


def _celulas(linha: str) -> List[str]:
    return [c.strip() for c in linha.strip().strip("|").split("|")]


def inventario(jornada: str) -> Dict[str, Any]:
    """A tabela «Seção 3 — Inventário de telas»: `{telas: [{id, etapa, ator, peso, estados}], fora_do_padrao}`.

    Lida pelo nome da coluna, nunca pela posição. `fora_do_padrao` são os IDs da tabela que não seguem
    `E<etapa>-<ator>-<nn>` (`EREV-ALU-01`): invisíveis para qualquer conferência, por isso achado.
    """
    texto = jornada or ""
    m = re.search(r"^#{1,4}[^\n]*invent[áa]rio de telas[^\n]*$", texto, re.I | re.M)
    if not m:
        return {"telas": [], "fora_do_padrao": [], "tabela": False}
    cabecalho: Optional[List[str]] = None
    telas: List[Dict[str, Any]] = []
    fora: List[str] = []
    for linha in texto[m.end():].splitlines():
        s = linha.strip()
        if not s:
            if cabecalho and telas:
                break
            continue
        if s.startswith("#") or (cabecalho and not s.startswith("|")):
            break
        if not s.startswith("|") or re.fullmatch(r"\|[\s:|-]+\|?", s):
            continue
        celulas = _celulas(s)
        if cabecalho is None:
            cabecalho = [_norm(c).strip("*_` ") for c in celulas]
            continue
        linha_d = {cabecalho[i]: celulas[i] for i in range(min(len(cabecalho), len(celulas)))}
        bruto = linha_d.get("id", celulas[0] if celulas else "").strip("*_` ")
        if not bruto:
            continue
        canonico = bruto.upper().replace("_", "-")
        if not _RE_ID_CANONICO.match(canonico):
            fora.append(bruto)
            continue
        estados_txt = next((v for k, v in linha_d.items() if k.startswith("estado")), "")
        estados = [e.strip(" `*_.") for e in re.split(r"[,;·/]|\s\+\s", estados_txt)]
        estados = [e for e in estados if e and _norm(e) not in ("—", "-", "n/a", "nenhum", "unico")]
        telas.append({"id": canonico, "etapa": linha_d.get("etapa", ""), "ator": linha_d.get("ator", ""),
                      "peso": linha_d.get("peso", ""), "estados": estados})
    return {"telas": telas, "fora_do_padrao": fora, "tabela": cabecalho is not None}


def quadros_do_prototipo(html: str) -> Dict[str, List[str]]:
    """`{id da tela: [estados]}` pelos atributos `data-screen-id`/`data-estado` dos quadros do protótipo.

    Comentário não é quadro: a lint antiga contava qualquer menção do ID no arquivo, inclusive em
    comentário e no trilho de navegação.
    """
    quadros: Dict[str, List[str]] = {}
    for tag in _RE_TAG_COM_QUADRO.findall(_RE_COMENTARIO.sub("", html or "")):
        atributos = {k.lower(): v.strip() for k, v in _RE_ATRIBUTO.findall(tag)}
        i = normalizar(atributos.get("screen-id", ""))
        if not i:
            continue
        estados = quadros.setdefault(i, [])
        estado = atributos.get("estado") or "padrão"
        if estado not in estados:
            estados.append(estado)
    return quadros


def cobertura(state: Dict[str, Any]) -> Dict[str, Any]:
    """Matriz ID × derivado, com achados endereçados ao dono de cada conserto."""
    jornada = str(state.get("jornada_telas", "") or "")
    inv = inventario(jornada)
    esperadas = [t["id"] for t in inv["telas"]]
    achados: List[Dict[str, str]] = []

    def achado(severidade: str, codigo: str, dono: str, resumo: str) -> None:
        achados.append({"severidade": severidade, "codigo": codigo, "etapa": "design",
                        "agente_responsavel": dono, "resumo": resumo})

    # Jornada vazia não é "nada a conferir": é o autor que não respondeu, e todo derivado fica sem chão
    # (auditoria do padrão ouro, 08/10/2026 — este gate aprovava a jornada vazia).
    if not jornada.strip():
        achado("bloqueio", "jornada-vazia", "jornada",
               "A jornada chegou vazia: sem o inventário de telas, nenhum derivado pode ser conferido.")
        return {"status": "bloqueado", "achados": achados, "inventario": inv, "matriz": {}}
    if not esperadas:
        achado("bloqueio", "inventario-ausente", "jornada",
               "A jornada não tem a tabela «Seção 3 — Inventário de telas» com a coluna `ID`: sem ela nenhum derivado "
               "pode ser conferido, e tela que ninguém lista some sem aviso.")
        return {"status": "bloqueado", "achados": achados, "inventario": inv, "matriz": {}}
    if inv["fora_do_padrao"]:
        achado("bloqueio", "id-fora-do-padrao", "jornada",
               f"Tela(s) do inventário fora do padrão `E<etapa>-<ator>-<nn>`: {', '.join(inv['fora_do_padrao'])}. "
               "Nenhuma conferência as enxerga (a exp04ef1b teve `EREV-ALU-01/02` aprovadas assim). Renumere na etapa "
               "em que a tela acontece.")
    faltam_prof = [p for p in PREPARO_DO_PROFESSOR if p not in esperadas]
    if faltam_prof:
        achado("bloqueio", "preparo-do-professor-ausente", "jornada",
               f"O inventário não tem {', '.join(faltam_prof)}: as cinco telas do preparo do professor são obrigatórias "
               "(escolher a missão, recorte da aula, geração, curadoria, pôr no ar).")

    matriz: Dict[str, Dict[str, bool]] = {i: {} for i in esperadas}
    for chave, rotulo, dono in DERIVADOS:
        texto = str(state.get(chave, "") or "")
        if not texto.strip():
            # derivado obrigatório que não chegou: antes era pulado e o gate aprovava sem ele
            achado("bloqueio", "derivado-vazio", dono,
                   f"{rotulo.capitalize()} chegou vazio: as {len(esperadas)} telas do inventário não têm onde ser conferidas.")
            continue
        presentes = set(ids(texto))
        faltando = [i for i in esperadas if i not in presentes]
        for i in esperadas:
            matriz[i][rotulo] = i in presentes
        if faltando:
            achado("bloqueio", f"telas-fora-de-{chave}", dono,
                   f"{len(faltando)} de {len(esperadas)} tela(s) do inventário fora de «{rotulo}»: {', '.join(faltando)}. "
                   "Acrescente cada uma — sem priorizar nem resumir.")

    html = str(state.get("prototipo_arquivo", "") or "")
    if html.strip():
        quadros = quadros_do_prototipo(html)
        if not quadros:
            achado("bloqueio", "prototipo-sem-quadros-marcados", "prototipo",
                   "O protótipo não marca os quadros com `data-screen-id` (e `data-estado`): sem a marca, o que se "
                   "confere é menção do ID no arquivo — em comentário ou no trilho conta como tela.")
        else:
            faltando = [i for i in esperadas if i not in quadros]
            for i in esperadas:
                matriz[i]["protótipo"] = i in quadros
            if faltando:
                achado("bloqueio", "telas-fora-do-prototipo", "prototipo",
                       f"{len(faltando)} de {len(esperadas)} tela(s) do inventário sem quadro no protótipo: {', '.join(faltando)}.")
            curtos = []
            for t in inv["telas"]:
                pedidos, feitos = len(t["estados"]), len(quadros.get(t["id"], []))
                if t["id"] in quadros and pedidos > 1 and feitos < pedidos:
                    curtos.append(f"{t['id']} ({feitos} de {pedidos}: {', '.join(t['estados'])})")
            if curtos:
                achado("atencao", "estados-fora-do-prototipo", "prototipo",
                       "Telas com menos quadros que os estados declarados no inventário — o protótipo tem um quadro por "
                       "estado: " + "; ".join(curtos) + ".")

    status = ("bloqueado" if any(a["severidade"] == "bloqueio" for a in achados)
              else ("amarelo" if achados else "aprovado"))
    return {"status": status, "achados": achados, "inventario": inv, "matriz": matriz}


def relatorio(resultado: Dict[str, Any], missao: str = "") -> str:
    icone = {"aprovado": "🟢 TODAS AS TELAS EM TODO ARTEFATO", "amarelo": "🟡 COM RESSALVAS",
             "bloqueado": "🔴 TELA FALTANDO"}[resultado["status"]]
    telas = resultado["inventario"]["telas"]
    linhas = [f"# Cobertura de telas — {missao or 'missão'}", "", f"**Veredito: {icone}**", "",
              f"Inventário da jornada: **{len(telas)} tela(s)**, {sum(max(1, len(t['estados'])) for t in telas)} "
              "quadro(s) contando os estados. Conferência por ID, não por contagem.", ""]
    matriz = resultado.get("matriz") or {}
    colunas = sorted({c for v in matriz.values() for c in v})
    if matriz and colunas:
        linhas += ["| Tela | " + " | ".join(colunas) + " |", "|---|" + "---|" * len(colunas)]
        for i, v in matriz.items():
            linhas.append(f"| `{i}` | " + " | ".join("✅" if v.get(c) else "❌" for c in colunas) + " |")
        linhas.append("")
    if resultado["achados"]:
        linhas += ["## Achados", ""]
        for a in resultado["achados"]:
            marca = "⛔" if a["severidade"] == "bloqueio" else "⚠️"
            linhas.append(f"- {marca} **{a['codigo']}** (dono: `{a['agente_responsavel']}`) — {a['resumo']}")
        linhas.append("")
    linhas += ["```json", json.dumps({"agente": AGENTE, "missao": missao, "status": resultado["status"],
                                      "achados": resultado["achados"], "precisa_humano": False},
                                     ensure_ascii=False, indent=2), "```"]
    return "\n".join(linhas)
