"""Rastro determinístico de falta de informação na esteira.

Três verificações mecânicas, todas sem LLM:

- ``varrer_lacunas``: conta os marcadores de lacuna que os agentes deixam nos documentos
  (`[LACUNA — dono: x]`, `[ABERTO — x]`, `[NEEDS CLARIFICATION: …]`,
  `[verificar no repositório: …]`, `RS-n pendente`, `🔵`) e atribui cada um a uma etapa
  (`input · produto · design · dev · plataforma`). Lacuna de plataforma é pendência humana
  (🟡); as outras impedem o PRD.
- ``validar_manifesto``: lê a ficha do manifesto no bloco 0 da spec (formato fixo de
  `references/formato-spec.md`) e confere cada campo contra as listas fechadas da plataforma.
- ``validar_telemetria``: confere no handoff de dev o contrato real de evento
  (`verbo · objeto · resultado · contexto`, sem campo `dados`), a tabela de leitura das medidas
  e as proibições de arquitetura (WebSocket, rota do motor da exp-01, papéis antigos).

As listas fechadas espelham `references/plataforma/` (contrato-manifesto, produtos-catalogo,
series, perfis-claims); reconferir quando `versao-lida.json` mudar.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ------------------------------------------------------------------ listas fechadas (plataforma)
PRODUTOS = ("entre-redes", "plano-de-aula", "plano-de-ensino", "bem-estar")
SERIES = ("1EF", "2EF", "3EF", "4EF", "5EF", "6EF", "7EF", "8EF", "9EF", "1EM", "2EM", "3EM")
CAPABILITIES = ("telemetria", "progresso", "ia", "avaliacao", "tempo-real")
PERMISSOES = ("pointer-lock", "forms", "downloads")
SECOES_DS = ("instanooria", "unitube", "chatgpt", "whatsappmobile", "tiktooria")
PUBLICOS = ("estudante", "professor")
ETAPAS = ("input", "produto", "design", "dev", "plataforma")

# ------------------------------------------------------------------ marcadores de lacuna
_MARCADORES = [
    ("lacuna", re.compile(r"\[LACUNA\s*[—–-]\s*dono:\s*([^\]]+?)\s*\]", re.IGNORECASE)),
    ("aberto", re.compile(r"\[ABERTO\s*[—–-]\s*([^\]]+?)\s*\]", re.IGNORECASE)),
    ("needs_clarification", re.compile(r"\[NEEDS CLARIFICATION:?\s*([^\]]*?)\]", re.IGNORECASE)),
    ("verificar_repositorio", re.compile(r"\[verificar no reposit[oó]rio:?\s*([^\]]*?)\]", re.IGNORECASE)),
    ("rs_pendente", re.compile(r"\b(RS-\d+)\s+pendente\b", re.IGNORECASE)),
    ("a_validar", re.compile(r"🔵[^\n]{0,120}")),
]

_TOKENS_ETAPA: Dict[str, tuple] = {
    "plataforma": ("plataforma", "adr", "design-system", "storybook", "infra", "ponte", "@edu/ui", "componente do ds", "componente de ds"),
    "dev": ("handoff-dev", "handoff", "brief-assets", "banca", "tech", "arquitetura", "dev"),
    "design": ("jornada", "fluxo", "copy", "wireframe", "caa", "ambiente-simulado", "ambiente", "brief-oficio", "briefing de ofício", "qa-entregaveis", "figma", "design"),
    "produto": ("gate-estrutural", "gate estrutural", "gate 0", "gate0", "spec", "produto", "one-pager", "pm", "gate-final", "gate final", "pedagog", "experiencia-aluno", "fecha-lacunas", "responsável de dados", "dados"),
    "input": ("input", "briefing", "insumo", "solicitante"),
}


def classificar_dono(texto_dono: str, etapa_padrao: str) -> str:
    """Mapeia o texto de dono de um marcador para uma etapa da esteira."""
    t = (texto_dono or "").lower()
    m = re.search(r"dono:\s*([a-z0-9_@/\-\. ]+)", t)
    if m:
        t = m.group(1)
    for etapa in ("plataforma", "dev", "design", "produto", "input"):
        for tok in _TOKENS_ETAPA[etapa]:
            if re.search(r"(?<![a-z0-9-])" + re.escape(tok) + r"s?(?![a-z0-9-])", t):
                return etapa
    return etapa_padrao if etapa_padrao in ETAPAS else "dev"


def varrer_lacunas(fontes: List[Dict[str, str]], state: Dict[str, Any]) -> Dict[str, Any]:
    """`fontes` = [{"chave": <state key>, "rotulo": <nome legível>, "etapa_padrao": <etapa>}]."""
    achados: List[Dict[str, Any]] = []
    documentos_lidos: List[str] = []
    for fonte in fontes:
        texto = state.get(fonte["chave"])
        if not texto or not isinstance(texto, str):
            continue
        documentos_lidos.append(fonte["rotulo"])
        for tipo, regex in _MARCADORES:
            for m in regex.finditer(texto):
                trecho = m.group(0).strip()
                dono_raw = m.group(1).strip() if m.groups() and m.group(1) else ""
                if tipo == "rs_pendente":
                    etapa = "produto"
                elif tipo == "verificar_repositorio":
                    etapa = "dev"
                elif tipo == "a_validar":
                    etapa = classificar_dono(trecho, "produto")
                else:
                    etapa = classificar_dono(dono_raw or trecho, fonte.get("etapa_padrao", "dev"))
                achados.append({
                    "tipo": tipo,
                    "trecho": trecho[:160],
                    "documento": fonte["rotulo"],
                    "dono": dono_raw[:80] or "—",
                    "etapa": etapa,
                    "severidade": "atencao" if etapa == "plataforma" else "bloqueio",
                })
    por_etapa = {e: sum(1 for a in achados if a["etapa"] == e) for e in ETAPAS}
    if any(a["severidade"] == "bloqueio" for a in achados):
        status = "bloqueado"
    elif achados:
        status = "amarelo"
    else:
        status = "aprovado"
    return {"status": status, "achados": achados, "por_etapa": por_etapa, "documentos": documentos_lidos}


def relatorio_lacunas(resultado: Dict[str, Any], rotulo: str, missao: str = "", agente: str = "rastro-lacunas") -> str:
    r = resultado
    icone = {"aprovado": "🟢 SEM LACUNAS", "amarelo": "🟡 SÓ PENDÊNCIAS DE PLATAFORMA", "bloqueado": "🔴 BLOQUEADO"}[r["status"]]
    linhas = [f"# {rotulo} — {missao or 'missão'}", "", f"**Veredito: {icone}**", ""]
    pe = r["por_etapa"]
    linhas.append(
        f"**O que faltou:** input `{pe['input']}` · **produto `{pe['produto']}`** · **design `{pe['design']}`** · dev `{pe['dev']}` · "
        f"plataforma (pendência humana, não bloqueia) `{pe['plataforma']}`"
    )
    linhas.append(f"**Documentos lidos:** {', '.join(r['documentos']) or '— nenhum'}")
    linhas.append("")
    if r["status"] == "bloqueado":
        faltou = [e for e in ("input", "produto", "design", "dev") if pe[e]]
        linhas.append(
            "O PRD **não sai** enquanto houver lacuna de " + " e ".join(f"**{e}**" for e in faltou)
            + ". Cada linha abaixo diz o documento onde a lacuna está e quem tem de fechá-la. Lacuna de plataforma fica registrada como pendência humana e não impede."
        )
    elif r["status"] == "amarelo":
        linhas.append("Só restam pendências cuja dona é a **plataforma** (ADR nova, componente de DS, ponte). Elas são resolvidas na codificação; o PRD sai `aprovado-com-pendencias-de-plataforma` (🟡), nunca `aprovado`.")
    else:
        linhas.append("Nenhum marcador de lacuna nos documentos lidos.")
    linhas.append("")
    linhas.append("## Lacunas")
    linhas.append("")
    if r["achados"]:
        linhas.append("| Etapa que falhou | Documento | Tipo | Dono declarado | Trecho |")
        linhas.append("|---|---|---|---|---|")
        for a in sorted(r["achados"], key=lambda x: (ETAPAS.index(x["etapa"]), x["documento"])):
            sev = "⚠️" if a["severidade"] == "atencao" else "⛔"
            trecho = a["trecho"].replace("|", "\\|").replace("\n", " ")
            linhas.append(f"| {sev} **{a['etapa']}** | {a['documento']} | `{a['tipo']}` | {a['dono']} | {trecho} |")
    else:
        linhas.append("_Nenhuma._")
    linhas.append("")
    envelope = {
        "agente": agente,
        "missao": missao or "",
        "rodada": 1,
        "status": "aprovado" if r["status"] == "aprovado" else ("apto_com_ressalvas" if r["status"] == "amarelo" else "bloqueado"),
        "veredito": {"aprovado": "verde", "amarelo": "amarelo", "bloqueado": "vermelho"}[r["status"]],
        "por_etapa": pe,
        "achados": [
            {"severidade": a["severidade"], "classe": a["tipo"], "codigo": a["etapa"], "agente_responsavel": a["dono"], "documento": a["documento"], "resumo": a["trecho"][:120]}
            for a in r["achados"]
        ],
        "precisa_humano": r["status"] != "aprovado",
    }
    linhas.append("```json")
    linhas.append(json.dumps(envelope, ensure_ascii=False))
    linhas.append("```")
    return "\n".join(linhas)


# ------------------------------------------------------------------ manifesto (bloco 0 da spec)
def _campo(texto: str, nome: str) -> Optional[str]:
    m = re.search(r"`?\b" + nome + r"\s*:\s*`?\s*([^`\n|]+?)`?\s*(?:$|\||\(|—|·)", texto, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else None


def _lista(valor: str) -> Optional[List[str]]:
    m = re.search(r"\[(.*?)\]", valor or "", re.DOTALL)
    if not m:
        return None
    itens = [i.strip().strip('"').strip("'").strip("`") for i in m.group(1).split(",")]
    return [i for i in itens if i]


def validar_manifesto(spec: str) -> Dict[str, Any]:
    from tools.bncc import secao_bloco  # bloco 0 da spec, mesmo parser

    texto = secao_bloco(spec or "", 0) or (spec or "")[:4000]
    achados: List[Dict[str, str]] = []
    campos: Dict[str, Any] = {}

    def falta(campo: str, motivo: str, etapa: str = "produto") -> None:
        achados.append({"severidade": "bloqueio", "campo": campo, "etapa": etapa, "resumo": motivo})

    v = _campo(texto, "id")
    campos["id"] = v
    if not v or not re.match(r"^exp-\d{2}-[a-z0-9][a-z0-9-]*$", v):
        falta("id", f"`id` ausente ou fora de `exp-NN-<slug>` (lido: {v!r}).")

    v = _campo(texto, "produto"); campos["produto"] = v
    if not v or v.lower() not in PRODUTOS:
        falta("produto", f"`produto` ausente ou fora da lista {list(PRODUTOS)} (lido: {v!r}). Sem ele o CI recusa o manifesto (ADR-87).")

    v = _campo(texto, "series"); campos["series"] = v
    series = _lista(v) if v else None
    if series is None:
        falta("series", f"`series` ausente ou fora do formato `[\"5EF\"]` / `[]` (lido: {v!r}).")
    elif any(s.upper() not in SERIES for s in series):
        falta("series", f"`series` com valor fora de {list(SERIES)}: {series}.")

    v = _campo(texto, "unidade"); campos["unidade"] = v
    if not v or v.lower() not in ("1", "2", "3", "4", "nenhuma"):
        falta("unidade", f"`unidade` ausente ou fora de 1–4 / `nenhuma` (lido: {v!r}). Sem ela a grade da sala não ordena (ADR-69).")

    v = _campo(texto, "publico"); campos["publico"] = v
    if not v or v.lower() not in PUBLICOS:
        falta("publico", f"`publico` ausente ou fora de {list(PUBLICOS)} (lido: {v!r}).")

    if campos.get("unidade") and campos["unidade"].lower() == "nenhuma" and series and (campos.get("publico") or "").lower() == "estudante":
        falta("unidade", "`unidade: nenhuma` só vale para transversal (`series: []`) ou ferramenta de professor; missão de estudante com série precisa de unidade 1–4.")

    v = _campo(texto, "viewport"); campos["viewport"] = v
    if not v or not re.match(r"^(desktop|\d{3,4}\s*[x×]\s*\d{3,4})$", v.replace(" ", ""), re.IGNORECASE):
        falta("viewport", f"`viewport` ausente ou fora de `375x812` / `desktop` / `<largura>x<altura>` (lido: {v!r}).")

    v = _campo(texto, "permissoes"); campos["permissoes"] = v
    perms = _lista(v) if v else None
    if perms is None:
        falta("permissoes", f"`permissoes` ausente ou fora do formato `[forms]` / `[]` (lido: {v!r}).")
    elif any(p.lower() not in PERMISSOES for p in perms):
        falta("permissoes", f"`permissoes` com valor fora de {list(PERMISSOES)}: {perms}.")

    v = _campo(texto, "capabilities"); campos["capabilities"] = v
    caps = _lista(v) if v else None
    if caps is None:
        falta("capabilities", f"`capabilities` ausente ou fora do formato `[telemetria, progresso]` (lido: {v!r}).")
    elif any(c.lower() not in CAPABILITIES for c in caps):
        falta("capabilities", f"`capabilities` com valor fora de {list(CAPABILITIES)}: {caps}.")

    v = _campo(texto, "secao_ds"); campos["secao_ds"] = v
    if not v or not (v.lower() in SECOES_DS or re.match(r"^(nova|minijogo)\s*:\s*\S+", v, re.IGNORECASE)):
        falta("secao_ds", f"`secao_ds` ausente ou fora de {list(SECOES_DS)} / `nova:<nome>` / `minijogo:<nome>` (lido: {v!r}). Dono: design (D9 ambiente-simulado) quando a spec cala; produto quando a spec errou.", etapa="design")
    elif v.lower() == "tiktooria":
        achados.append({"severidade": "atencao", "campo": "secao_ds", "etapa": "plataforma", "resumo": "`tiktooria` existe no DS mas não tem ponte em `@edu/ui`; criar a ponte é pré-requisito de plataforma."})
    elif re.match(r"^(nova|minijogo)\s*:", v, re.IGNORECASE):
        achados.append({"severidade": "atencao", "campo": "secao_ds", "etapa": "plataforma", "resumo": f"Seção de DS nova (`{v}`): componentes, responsável e prazo são pendência de plataforma."})

    v = _campo(texto, "liberacao"); campos["liberacao"] = v
    if not v or "por-turma" not in v.lower():
        falta("liberacao", f"`liberacao: por-turma` ausente (lido: {v!r}). Sem liberação por turma a missão não abre (ADR-69).")

    status = "bloqueado" if any(a["severidade"] == "bloqueio" for a in achados) else ("amarelo" if achados else "aprovado")
    return {"status": status, "campos": campos, "achados": achados, "bloco0_encontrado": secao_bloco(spec or "", 0) is not None}


def relatorio_manifesto(resultado: Dict[str, Any], missao: str = "") -> str:
    r = resultado
    icone = {"aprovado": "🟢 CONFORME", "amarelo": "🟡 CONFORME COM PENDÊNCIA DE PLATAFORMA", "bloqueado": "🔴 BLOQUEADO"}[r["status"]]
    linhas = [f"# Ficha do manifesto — {missao or 'missão'}", "", f"**Veredito: {icone}** · bloco 0 da spec × listas fechadas da plataforma (`references/plataforma/contrato-manifesto.md`).", ""]
    linhas.append(f"**Bloco 0 encontrado:** {'sim' if r['bloco0_encontrado'] else 'não — campos lidos do início da spec'}")
    linhas.append("")
    linhas.append("| Campo | Lido |")
    linhas.append("|---|---|")
    for k, v in r["campos"].items():
        linhas.append(f"| `{k}` | {('`' + str(v) + '`') if v else '— ausente'} |")
    linhas.append("")
    linhas.append("## Achados")
    linhas.append("")
    if r["achados"]:
        for a in r["achados"]:
            linhas.append(f"- {'⛔' if a['severidade']=='bloqueio' else '⚠️'} **{a['campo']}** (dono: {a['etapa']}) — {a['resumo']}")
    else:
        linhas.append("- Nenhum. O manifesto `experiencia.json` é derivável da spec (TEC-01).")
    linhas.append("")
    envelope = {
        "agente": "manifesto-check", "missao": missao or "", "rodada": 1,
        "status": "aprovado" if r["status"] == "aprovado" else ("apto_com_ressalvas" if r["status"] == "amarelo" else "bloqueado"),
        "veredito": {"aprovado": "verde", "amarelo": "amarelo", "bloqueado": "vermelho"}[r["status"]],
        "campos": r["campos"],
        "achados": [{"severidade": a["severidade"], "classe": "manifesto", "codigo": a["campo"], "agente_responsavel": a["etapa"], "resumo": a["resumo"]} for a in r["achados"]],
        "precisa_humano": r["status"] != "aprovado",
    }
    linhas.append("```json"); linhas.append(json.dumps(envelope, ensure_ascii=False)); linhas.append("```")
    return "\n".join(linhas)


# ------------------------------------------------------------------ telemetria (handoff de dev)
_CABECALHO_TABELA = re.compile(r"^\|[^\n]*\|\s*$", re.MULTILINE)


def validar_telemetria(handoff: str) -> Dict[str, Any]:
    texto = handoff or ""
    achados: List[Dict[str, str]] = []
    cabecalhos = [l.lower() for l in _CABECALHO_TABELA.findall(texto)]
    com_verbo = [c for c in cabecalhos if "verbo" in c]
    tabela_eventos = [c for c in com_verbo if "objeto" in c]

    def bloqueio(codigo: str, resumo: str) -> None:
        achados.append({"severidade": "bloqueio", "codigo": codigo, "etapa": "dev", "resumo": resumo})

    def atencao(codigo: str, resumo: str) -> None:
        achados.append({"severidade": "atencao", "codigo": codigo, "etapa": "dev", "resumo": resumo})

    if not tabela_eventos:
        bloqueio("tabela-eventos", "Nenhuma tabela de eventos com as colunas `verbo` e `objeto`. O contrato real é `track(verbo, objeto, resultado, contexto)`.")
    elif not any(("resultado" in c or "contexto" in c) for c in tabela_eventos):
        bloqueio("resultado-contexto", "A tabela de eventos não tem coluna `resultado` nem `contexto` — são os dois únicos campos de payload que a api aceita.")
    if re.search(r"\|\s*`?dados`?\s*\|", texto, re.IGNORECASE) or re.search(r"campos?\s+`dados`", texto, re.IGNORECASE):
        bloqueio("campo-dados", "Evento com campo `dados`: a api não tem esse campo e descarta a chave em silêncio. Use `resultado` e `contexto`.")
    if not re.search(r"\bexp_\d{2}_[a-z][a-z0-9_]*", texto):
        bloqueio("tabela-leitura", "Nenhuma tabela `exp_NN_*` nomeada. Toda medida que a professora vê nasce de tabela própria do módulo — sem tabela de leitura, a medida não existe (`telemetria_eventos` não tem leitor).")
    if re.search(r"websocket|socket\.io|hub:pause", texto, re.IGNORECASE):
        bloqueio("websocket", "WebSocket ou `hub:pause` como canal de sala: a plataforma sincroniza por polling HTTP curto em `exp_NN_gates_turma` (ADR-93/94).")
    if re.search(r"admin-contrato|@Roles\([^)]*[\"']gestor[\"']", texto):
        bloqueio("papeis", "Papel antigo (`admin-contrato`, `gestor`): a plataforma tem seis papéis — `estudante · professor · gestor_escola · gestor_regional · gestor_contrato · admin` (ADR-80).")
    if re.search(r"/runs/(:id|\{?\w*[iI]d\}?)/eventos", texto):
        atencao("rota-motor", "`POST /runs/:id/eventos` é a rota do motor da exp-01, não um canal genérico. Missão nova grava trilha na rota do próprio módulo.")
    if re.search(r"AI_DAILY_TOKEN_QUOTA", texto):
        atencao("quota-env", "Quota de IA por env não existe mais: é linha em `ia_quotas` por perfil (ADR-105).")
    if re.search(r"\benum\b[^\n]{0,60}\b(estado|status)\b", texto, re.IGNORECASE):
        atencao("enum-estado", "Estado como enum: na plataforma é string com CHECK na migration, nunca enum Prisma.")

    status = "bloqueado" if any(a["severidade"] == "bloqueio" for a in achados) else ("amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados, "tabelas_eventos": len(tabela_eventos)}


def relatorio_telemetria(resultado: Dict[str, Any], missao: str = "") -> str:
    r = resultado
    icone = {"aprovado": "🟢 CONFORME", "amarelo": "🟡 CONFORME COM AVISOS", "bloqueado": "🔴 BLOQUEADO"}[r["status"]]
    linhas = [f"# Contrato de telemetria e arquitetura — {missao or 'missão'}", "", f"**Veredito: {icone}** · handoff de dev × contrato real da plataforma (`references/plataforma/contrato-telemetria.md`, ADR-80/93/94/105).", "", f"Tabelas de eventos com `verbo` e `objeto` encontradas: {r['tabelas_eventos']}", "", "## Achados", ""]
    if r["achados"]:
        for a in r["achados"]:
            linhas.append(f"- {'⛔' if a['severidade']=='bloqueio' else '⚠️'} **{a['codigo']}** (dono: {a['etapa']}) — {a['resumo']}")
    else:
        linhas.append("- Nenhum. Eventos no contrato real, medidas com tabela de leitura, sem WebSocket, papéis e quota atuais.")
    linhas.append("")
    envelope = {
        "agente": "telemetria-check", "missao": missao or "", "rodada": 1,
        "status": "aprovado" if r["status"] == "aprovado" else ("apto_com_ressalvas" if r["status"] == "amarelo" else "bloqueado"),
        "veredito": {"aprovado": "verde", "amarelo": "amarelo", "bloqueado": "vermelho"}[r["status"]],
        "achados": [{"severidade": a["severidade"], "classe": "telemetria", "codigo": a["codigo"], "agente_responsavel": "handoff-dev", "resumo": a["resumo"]} for a in r["achados"]],
        "precisa_humano": r["status"] == "bloqueado",
    }
    linhas.append("```json"); linhas.append(json.dumps(envelope, ensure_ascii=False)); linhas.append("```")
    return "\n".join(linhas)
