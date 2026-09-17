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

# `permissoes` do manifesto: o que a plataforma concede HOJE, por declaração.
PERMISSOES = ("pointer-lock", "forms", "downloads")

# Já delegadas a TODAS as experiências pelo `allow` do `ExpFrame`. Declarar uma
# delas derruba o `PUT /experiencias/:expId` do deploy com 400, depois de os
# bundles terem subido — o vocabulário do manifesto não as aceita.
PERMISSOES_JA_DELEGADAS = {
    "autoplay": "tocar áudio ou vídeo começando sozinho",
    "fullscreen": "tela cheia",
    "clipboard-write": "copiar texto para a área de transferência",
}

# Capacidade real do navegador que a plataforma ainda NÃO concede. A missão pode
# pedir: vira pré-requisito de plataforma (🟡) com o caminho em
# `references/capacidades-plataforma.md`, e o PRD sai amarelo em vez de barrar.
CAPACIDADES_DE_EXTENSAO = {
    "microphone": "gravar a voz do estudante",
    "camera": "usar a câmera (foto, vídeo, leitura de código)",
    "display-capture": "gravar a tela",
    "geolocation": "localização do aparelho",
    "accelerometer": "sensor de aceleração",
    "gyroscope": "giroscópio",
    "magnetometer": "bússola",
    "screen-wake-lock": "manter a tela acesa",
    "web-share": "compartilhar pelo aparelho",
    "picture-in-picture": "vídeo em janela flutuante",
    "midi": "instrumento MIDI",
    "xr-spatial-tracking": "realidade aumentada ou virtual",
    "encrypted-media": "mídia protegida por DRM",
    "idle-detection": "detectar que a pessoa parou",
    "local-fonts": "fontes instaladas no aparelho",
    "window-management": "várias janelas",
    "usb": "dispositivo USB",
    "serial": "porta serial",
    "bluetooth": "Bluetooth",
    "hid": "dispositivo de entrada",
    "payment": "pagamento",
    "publickey-credentials-get": "chave de segurança",
}

# Capturar mídia do estudante não é só permissão de iframe: é contrato de dados.
CAPTURA_DE_MIDIA = ("microphone", "camera", "display-capture")
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

# Os prompts citam o formato do marcador para ensinar o agente a usá-lo — e a citação
# tem a mesma forma do marcador. Um documento que diz "Lista de pendências
# `[ABERTO — dono]` consolidada:" seguido de "Nenhuma pendência em aberto" era lido
# como pendência de produto e barrava o PRD. O que separa a citação da pendência é o
# conteúdo: aqui está o rótulo do campo, não quem tem de fechá-lo.
_PLACEHOLDERS = frozenset({
    "dono", "x", "y", "…", "...", "quem", "etapa", "nome", "responsavel", "responsável",
    "dono: x", "dono: …", "dono: ...", "dono: nome", "dono: etapa",
})


def _e_citacao_do_formato(dono_raw: str) -> bool:
    return dono_raw.strip().strip("`*_ ").lower() in _PLACEHOLDERS


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
                if tipo in ("lacuna", "aberto", "needs_clarification") and _e_citacao_do_formato(dono_raw):
                    continue
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
    extensoes: List[str] = []
    if perms is None:
        falta("permissoes", f"`permissoes` ausente ou fora do formato `[forms]` / `[]` (lido: {v!r}).")
    else:
        for bruto in perms:
            p_ = bruto.lower().strip()
            if p_ in PERMISSOES:
                continue
            if p_ in PERMISSOES_JA_DELEGADAS:
                achados.append({
                    "severidade": "atencao", "campo": "permissoes", "etapa": "dev",
                    "resumo": (
                        f"`{p_}` ({PERMISSOES_JA_DELEGADAS[p_]}) **já é concedido a todas as experiências** pelo `allow` do `ExpFrame`. "
                        f"Declará-lo no manifesto derruba o `PUT /experiencias/:expId` do deploy com 400, depois de os bundles subirem. Remova da lista."
                    ),
                })
            elif p_ in CAPACIDADES_DE_EXTENSAO:
                extensoes.append(p_)
                achados.append({
                    "severidade": "atencao", "campo": "permissoes", "etapa": "plataforma",
                    "resumo": (
                        f"`{p_}` ({CAPACIDADES_DE_EXTENSAO[p_]}) é capacidade que a plataforma ainda não concede ao iframe. "
                        f"**Pré-requisito de plataforma**, não impedimento: o PRD sai 🟡 e leva o caminho de implementação "
                        f"(contrato da api, migration do CHECK, `allow` derivado do manifesto no `ExpFrame`, teste, repasse nas rotas do hub) "
                        f"de `references/capacidades-plataforma.md`."
                    ),
                })
            else:
                falta("permissoes", (
                    f"`{bruto}` não é permissão de iframe reconhecida. As concedidas hoje são {list(PERMISSOES)}; "
                    f"capacidade nova do navegador vai na seção 3 de `references/capacidades-plataforma.md`."
                ), etapa="dev")

    v = _campo(texto, "capabilities"); campos["capabilities"] = v
    caps = _lista(v) if v else None
    if caps is None:
        falta("capabilities", f"`capabilities` ausente ou fora do formato `[telemetria, progresso]` (lido: {v!r}).")
    else:
        for c in caps:
            if c.lower().strip() not in CAPABILITIES:
                achados.append({
                    "severidade": "atencao", "campo": "capabilities", "etapa": "plataforma",
                    "resumo": (
                        f"`{c}` não está no vocabulário de capabilities da plataforma ({list(CAPABILITIES)}). "
                        f"Se a missão precisa mesmo dela, é capability nova: pré-requisito de plataforma (contrato da api, hub, seed), com ADR."
                    ),
                })

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

    # Capturar voz ou imagem de criança é contrato de dados, não só permissão de
    # iframe: o bloco 9 tem de dizer onde a mídia fica, por quanto tempo e quem lê.
    capturas = [p for p in extensoes if p in CAPTURA_DE_MIDIA]
    if capturas:
        bloco9 = secao_bloco(spec or "", 9) or ""
        # Detectores amplos de propósito: o gate pega a ausência gritante, não julga
        # a qualidade do contrato de dados — isso é da banca (DAD-07/08). Regex
        # estreito aqui produz falso positivo e barra missão que declarou tudo.
        menciona_midia = bool(re.search(r"[áa]udio|voz|oralidade|foto|imagem|v[íi]deo|grava[çc]|grava[dç]", bloco9, re.IGNORECASE))
        tem_destino = bool(re.search(r"\bexp_\d{2}_[a-z][a-z0-9_]*|bucket|-assets|tabela", bloco9, re.IGNORECASE))
        tem_leitor = bool(re.search(r"quem l[êe]|lid[ao]|restrit[oa]|acesso|professor", bloco9, re.IGNORECASE))
        tem_retencao = bool(re.search(r"reten[çc][ãa]o|expurgo|apagad[ao]|prazo|\b\d+\s*(dias|meses|anos)\b", bloco9, re.IGNORECASE))
        if not menciona_midia:
            falta("permissoes", (
                f"A missão captura mídia do estudante ({', '.join(capturas)}) e o bloco 9 não fala dela. "
                f"Voz e imagem de criança são dado pessoal e não são coletados por padrão: o bloco 9 declara onde a mídia é gravada, "
                f"quanto tempo fica, quem lê e o que acontece sem o recurso."
            ))
            faltando = []
        else:
            faltando = [r for r, ok in (("onde a mídia é gravada", tem_destino), ("quem lê", tem_leitor), ("retenção", tem_retencao)) if not ok]
        if faltando:
            falta("permissoes", (
                f"A missão captura mídia do estudante ({', '.join(capturas)}), e o bloco 9 não declara: {', '.join(faltando)}. "
                f"Voz e imagem de criança são dado pessoal e não são coletados por padrão — sem destino, leitor e prazo escritos, a banca de dados reprova."
            ))
        elif menciona_midia:
            achados.append({
                "severidade": "atencao", "campo": "permissoes", "etapa": "plataforma",
                "resumo": (
                    f"Captura de mídia ({', '.join(capturas)}) exige, além da permissão: componente de gravação no design system (não existe hoje) "
                    f"e caminho alternativo para quem não tem o recurso ou não autoriza. Os dois vão ao PRD como pré-requisito."
                ),
            })

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
    if r["status"] == "amarelo":
        linhas.append("")
        linhas.append(
            "As pendências acima **não impedem o PRD**: capacidade que a plataforma ainda não concede é pré-requisito, "
            "e o documento sai `aprovado-com-pendencias-de-plataforma` com o caminho de implementação escrito "
            "(`references/capacidades-plataforma.md`). Quem constrói a missão estende a plataforma junto."
        )
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
# Um bloco de tabela markdown inteiro: cabeçalho, separador e linhas, até a primeira
# linha que não começa com `|`.
_BLOCO_TABELA = re.compile(r"(?:^\|[^\n]*$\n?){2,}", re.MULTILINE)


def _tabelas_de_evento(texto: str) -> List[str]:
    """Blocos de tabela que descrevem eventos de telemetria.

    Olha o BLOCO, não só o cabeçalho: o contrato é `track(verbo, objeto, resultado,
    contexto)`, mas nada obriga o handoff a dar uma coluna a cada campo — é comum
    `| Evento | Verbo | ... | Campos |` com `objeto`/`resultado`/`contexto` dentro da
    célula de campos. Exigir tudo no cabeçalho reprovava handoff correto.
    """
    blocos = []
    for m in _BLOCO_TABELA.finditer(texto):
        bloco = m.group(0)
        cabecalho = bloco.split("\n", 1)[0].lower()
        if ("verbo" in cabecalho or "evento" in cabecalho) and "objeto" in bloco.lower():
            blocos.append(bloco)
    return blocos


# Handoff bom REPETE a proibição para o dev não errar ("Proibido campo `dados`",
# "nunca WebSocket", "papel `admin-contrato` não existe mais"). Procurar só o termo
# transformava a regra citada em violação e barrava o PRD por cumpri-la.
_NEGACAO = re.compile(
    r"proibid|vedado|nunca|jamais|evit[ae]|descartad|obsolet|legad|"
    r"n[ãa]o\s+(existe|existem|use|usar|usamos|h[áa]|aceita|pode|deve|ser[áa]|suporta)|"
    r"em vez de|ao inv[ée]s|fora de escopo|removid|deprecia|"
    r"sem\s+(campo|coluna|chave|payload|uso)|nada de|dispensa",
    re.IGNORECASE,
)


def _linha_de(texto: str, pos: int) -> str:
    inicio = texto.rfind("\n", 0, pos) + 1
    fim = texto.find("\n", pos)
    return texto[inicio : fim if fim != -1 else len(texto)]


def _usado_afirmativamente(texto: str, padrao: str) -> bool:
    """O termo aparece propondo algo, e não numa frase que o proíbe."""
    for m in re.finditer(padrao, texto, re.IGNORECASE):
        if not _NEGACAO.search(_linha_de(texto, m.start())):
            return True
    return False


def validar_telemetria(handoff: str) -> Dict[str, Any]:
    texto = handoff or ""
    achados: List[Dict[str, str]] = []
    tabela_eventos = _tabelas_de_evento(texto)

    def bloqueio(codigo: str, resumo: str) -> None:
        achados.append({"severidade": "bloqueio", "codigo": codigo, "etapa": "dev", "resumo": resumo})

    def atencao(codigo: str, resumo: str) -> None:
        achados.append({"severidade": "atencao", "codigo": codigo, "etapa": "dev", "resumo": resumo})

    if not tabela_eventos:
        bloqueio("tabela-eventos", "Nenhuma tabela de eventos com as colunas `verbo` e `objeto`. O contrato real é `track(verbo, objeto, resultado, contexto)`.")
    elif not any(("resultado" in b.lower() or "contexto" in b.lower()) for b in tabela_eventos):
        bloqueio("resultado-contexto", "A tabela de eventos não tem coluna `resultado` nem `contexto` — são os dois únicos campos de payload que a api aceita.")
    if _usado_afirmativamente(texto, r"\|\s*`?dados`?\s*\|") or _usado_afirmativamente(texto, r"[`\"']?\bdados\b[`\"']?\s*:"):
        bloqueio("campo-dados", "Evento com campo `dados`: a api não tem esse campo e descarta a chave em silêncio. Use `resultado` e `contexto`.")
    if not re.search(r"\bexp_\d{2}_[a-z][a-z0-9_]*", texto):
        bloqueio("tabela-leitura", "Nenhuma tabela `exp_NN_*` nomeada. Toda medida que a professora vê nasce de tabela própria do módulo — sem tabela de leitura, a medida não existe (`telemetria_eventos` não tem leitor).")
    # O que importa é o canal DECLARADO, não a palavra. Handoff correto cita WebSocket
    # justamente para descartá-lo ("Cloud Run não sustenta WebSocket, ADR-93/94") ou
    # para colocá-lo como futuro fora de escopo — e era bloqueado por isso.
    canal_correto = bool(re.search(r"polling", texto, re.IGNORECASE) and re.search(r"exp_\d{2}_gates_turma", texto))
    if _usado_afirmativamente(texto, r"websocket|socket\.io|hub:pause"):
        if canal_correto:
            atencao("websocket-mencao", "WebSocket ou `hub:pause` aparece no texto. O canal de sala declarado é o correto (polling em `exp_NN_gates_turma`), então é só conferir se a menção é mesmo comparativa e não uma segunda via de sincronização.")
        else:
            bloqueio("websocket", "WebSocket ou `hub:pause` como canal de sala, sem polling em `exp_NN_gates_turma` declarado: a plataforma sincroniza por polling HTTP curto (ADR-93/94).")
    if _usado_afirmativamente(texto, r"admin-contrato|@Roles\([^)]*[\"']gestor[\"']"):
        bloqueio("papeis", "Papel antigo (`admin-contrato`, `gestor`): a plataforma tem seis papéis — `estudante · professor · gestor_escola · gestor_regional · gestor_contrato · admin` (ADR-80).")
    if _usado_afirmativamente(texto, r"/runs/(:id|\{?\w*[iI]d\}?)/eventos"):
        atencao("rota-motor", "`POST /runs/:id/eventos` é a rota do motor da exp-01, não um canal genérico. Missão nova grava trilha na rota do próprio módulo.")
    if _usado_afirmativamente(texto, r"AI_DAILY_TOKEN_QUOTA"):
        atencao("quota-env", "Quota de IA por env não existe mais: é linha em `ia_quotas` por perfil (ADR-105).")
    if _usado_afirmativamente(texto, r"\benum\b[^\n]{0,60}\b(estado|status)\b"):
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
