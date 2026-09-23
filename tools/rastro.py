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

#: Experiências que já existem na plataforma (espelha `references/plataforma/`). O PRD as cita
#: como exemplar a imitar (`apps/experiencias/exp-08-manifesto-ia/`) ou para não repetir porta —
#: citar não é declarar o diretório da missão nova, e contar as duas coisas juntas reprovava o PRD
#: justamente por seguir a referência (2026-09-22, exp08ef2b).
EXPERIENCIAS_EXISTENTES = frozenset({
    "exp-01-instanooria", "exp-02-unootube", "exp-03-unoogpt", "exp-04-o-que-a-foto-conta",
    "exp-06-rastro-boato", "exp-07-o-eco-no-grupo", "exp-08-manifesto-ia", "exp-12-fracoes",
    "exp-70-vila-do-lume", "exp-90-plano-de-aula", "exp-91-bem-estar", "exp-92-plano-de-ensino",
})
PUBLICOS = ("estudante", "professor")


def _carregar_taxonomia() -> Dict[str, Any]:
    """Lê `references/donos-e-etapas.md` — a mesma fonte que os prompts leem em prosa.

    Enquanto a lista de tokens vivia só aqui, o prompt mandava escrever um marcador que este
    classificador reprovava, e a lista acumulou cinco correções datadas (uma por sessão
    quebrada). Com a cerca JSON no mesmo arquivo da prosa, quem muda a regra muda as duas
    metades de uma vez. Mesmo padrão de `tools/bncc.py`, que lê o anexo da BNCC.
    """
    from prompts import REFERENCES_DIR

    texto = (REFERENCES_DIR / "donos-e-etapas.md").read_text(encoding="utf-8")
    cerca = re.search(r"```json\s*(\{.*?\})\s*```", texto, re.DOTALL)
    if not cerca:  # pragma: no cover - o arquivo é versionado com a cerca
        raise ValueError("donos-e-etapas.md sem a cerca ```json com o contrato de etapas")
    return json.loads(cerca.group(1))


_TAXONOMIA = _carregar_taxonomia()
ETAPAS = tuple(_TAXONOMIA["ordem_precedencia"])
# Etapas cuja pendência é resolvida por gente, fora da esteira: registram 🟡 e o PRD sai.
#: Etapas cujo achado não impede a construção: ou é pré-requisito de plataforma, ou é
#: ato humano. Bloquear por elas trava a esteira em algo que nenhum agente resolve.
ETAPAS_NAO_BLOQUEANTES = tuple(e for e, d in _TAXONOMIA["etapas"].items() if not d["bloqueia"])

# ------------------------------------------------------------------ marcadores de lacuna
_MARCADORES = [
    ("lacuna", re.compile(r"\[LACUNA\s*[—–-]\s*dono:\s*([^\]]+?)\s*\]", re.IGNORECASE)),
    ("aberto", re.compile(r"\[ABERTO\s*[—–-]\s*([^\]]+?)\s*\]", re.IGNORECASE)),
    ("needs_clarification", re.compile(r"\[NEEDS CLARIFICATION:?\s*([^\]]*?)\]", re.IGNORECASE)),
    ("verificar_repositorio", re.compile(r"\[verificar no reposit[oó]rio:?\s*([^\]]*?)\]", re.IGNORECASE)),
    ("rs_pendente", re.compile(r"\b(RS-\d+)\s+pendente\b", re.IGNORECASE)),
    # O 🔵 precedido de contagem é PLACAR, não pendência: "Nenhuma pendência técnica aberta
    # (`0 ❌ / 0 🔵`)" reprovou a sessão exp06ef1b inteira em 22/09/2026 — o gate leu como
    # pendência de produto a frase que afirma justamente a ausência delas, e 13 artefatos a
    # jusante saíram `[PROVISÓRIO]`. Um 🔵 de verdade abre a pendência, não a conta.
    ("a_validar", re.compile(r"(?<![0-9])(?<![0-9] )🔵[^\n]{0,120}")),
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
    bruto = dono_raw.strip().strip("`*_ ").lower()
    # `<dono>`, `<agente>`: o agente citou o formato do marcador em vez de abrir uma pendência —
    # tipicamente numa frase de conformidade ("nenhuma pendência [ABERTO — <dono>] sobrevive").
    # Placeholder entre sinais de menor/maior nunca é dono real.
    if bruto.startswith("<") and bruto.endswith(">"):
        return True
    return bruto in _PLACEHOLDERS


#: Tokens por etapa, na ordem de precedência — ambos vêm de `references/donos-e-etapas.md`.
#: A prosa do mesmo arquivo é o que os prompts leem, então a regra que o agente segue e a que
#: o classificador aplica não podem mais divergir. O histórico das correções (coordenação em
#: 2026-09-20, especialista e pedagógico em 2026-09-21, dados e PO em 2026-09-23) está lá.
_TOKENS_ETAPA: Dict[str, tuple] = {
    etapa: tuple(dados["tokens"]) for etapa, dados in _TAXONOMIA["etapas"].items()
}

#: Marcadores cujo dono é fixo porque o prompt que os cria já sabe quem fecha.
_DONO_DO_MARCADOR: Dict[str, str] = dict(_TAXONOMIA["marcadores"])


def _etapa_por_tokens(texto: str) -> Optional[str]:
    """Primeira etapa cujos tokens aparecem em `texto`, na ordem de precedência. None se nenhuma."""
    t = (texto or "").lower()
    # O hífen conta como letra para que `design-system` não vire "design" e `handoff-dev` não
    # vire "dev". Mas o redator também escreve donos como slug — `coordenador-pedagogico`,
    # `estudio-audio` — e aí o hífen escondia a palavra (2026-09-21, PRD de correção da
    # exp06ef1b: três pendências externas viraram lacuna de dev). Cada token é testado no
    # texto cru e na variante com hífens trocados por espaço; a ordem das etapas continua
    # decidindo, então `design-system` ainda casa `plataforma` antes de chegar a `design`.
    variantes = (t, t.replace("-", " ")) if "-" in t else (t,)
    for etapa in ("humano", "externo", "plataforma", "dev", "design", "produto", "input"):
        for tok in _TOKENS_ETAPA[etapa]:
            # tokens com classe de caractere (ex.: `licen[çc]a`) entram crus; os demais, escapados
            padrao = tok if ("[" in tok or "(" in tok) else re.escape(tok)
            regex = r"(?<![a-z0-9-])" + padrao + r"s?(?![a-z0-9-])"
            if any(re.search(regex, v) for v in variantes):
                return etapa
    return None


def classificar_dono(texto_dono: str, etapa_padrao: str, contexto: str = "") -> str:
    """Mapeia o texto de dono de um marcador para uma etapa da esteira.

    `contexto` é a linha inteira onde o marcador apareceu. O campo `dono:` decide primeiro, como
    sempre; a linha só é consultada quando esse campo resultaria em bloqueio, e só é capaz de
    **aliviar** o achado — nunca de agravá-lo. É o que separa o dono nominal de quem de fato
    fecha a pendência: `[ABERTO — dono: produto]: confirmar a semana letiva junto à coordenação
    pedagógica da rede parceira` tem dono `produto` escrito, mas quem fecha é gente fora da
    esteira, e barrar a missão por isso trava a construção em algo que nenhuma rodada resolve.
    """
    t = (texto_dono or "").lower()
    corpo = t
    m = re.search(r"dono:\s*([a-z0-9_@/\-\. ]+)", t)
    if m:
        t = m.group(1)
    pelo_dono = _etapa_por_tokens(t)
    if pelo_dono in ETAPAS_NAO_BLOQUEANTES:
        return pelo_dono
    # O `dono:` cabe em duas palavras; o que se pede está no resto do marcador:
    # `[NEEDS CLARIFICATION: Homologação cadastral do slug, dono: produto]`. Homologar é ato de
    # gente, e o gate estrutural e o gate final já registravam o mesmo item como decisão humana —
    # só o prd-check, lendo apenas `dono:`, bloqueava (sessão 8f76, 2026-09-21). O corpo do
    # marcador entra com a mesma regra da linha: só alivia, nunca agrava.
    for alternativa in ((corpo if m else ""), contexto):
        if alternativa:
            pela_alternativa = _etapa_por_tokens(alternativa)
            if pela_alternativa in ETAPAS_NAO_BLOQUEANTES:
                return pela_alternativa
    if pelo_dono:
        return pelo_dono
    return etapa_padrao if etapa_padrao in ETAPAS else "dev"


def _linha_e_contexto(texto: str, inicio: int, fim: int) -> tuple:
    """Devolve ``(linha inteira, prosa ao redor do marcador)``.

    O marcador raramente diz tudo: `[ABERTO — dono: produto]` cabe num colchete, e quem fecha a
    pendência está na frase ao lado. Mas a linha crua não serve de contexto quando carrega mais
    de um marcador — o `dono: plataforma` de um vizinho aliviaria indevidamente o marcador desta
    iteração. A prosa é a linha com **todos** os marcadores removidos: sobra o texto que o autor
    escreveu em volta, que é o que diz quem tem a caneta.
    """
    ini = texto.rfind("\n", 0, inicio) + 1
    fim_linha = texto.find("\n", fim)
    linha = texto[ini : fim_linha if fim_linha != -1 else len(texto)].strip()
    prosa = linha
    for _, regex in _MARCADORES:
        prosa = regex.sub(" ", prosa)
    return linha, prosa


def varrer_lacunas(fontes: List[Dict[str, str]], state: Dict[str, Any]) -> Dict[str, Any]:
    """`fontes` = [{"chave": <state key>, "rotulo": <nome legível>, "etapa_padrao": <etapa>}]."""
    achados: List[Dict[str, Any]] = []
    documentos_lidos: List[str] = []
    vistos: Dict[tuple, Dict[str, Any]] = {}
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
                linha, contexto = _linha_e_contexto(texto, m.start(), m.end())
                if tipo in ("rs_pendente", "verificar_repositorio"):
                    # Dono fixo, do contrato: `RS-n pendente` é pedido ao Gate 0/PO que só
                    # pessoa fecha, e `[verificar no repositório]` é instrução para quem
                    # codifica — os agentes não têm o monorepo por desenho. Os dois eram
                    # roteados para `produto` e `dev`, bloqueantes, e os prompts mandavam
                    # escrevê-los: a esteira punia o agente por obedecer.
                    etapa = _DONO_DO_MARCADOR[tipo]
                elif tipo == "a_validar":
                    # Todo prompt que ensina o 🔵 o descreve como pendência externa a validar
                    # (criterios-pedagogicos.md:41 · 47_prd_writer.md:151 · 11_gate_final.md:30).
                    # O default era `produto`, bloqueante — o código contradizia o prompt. Um 🔵
                    # que nomeie produto, design ou dev no texto continua bloqueando.
                    etapa = classificar_dono(trecho, "externo", contexto=contexto)
                else:
                    etapa = classificar_dono(dono_raw or trecho, fonte.get("etapa_padrao", "dev"), contexto=contexto)
                chave = (tipo, " ".join(trecho.split()).lower())
                if chave in vistos:
                    # Mesma pendência propagada para outro documento: conta uma vez, no
                    # documento de origem, e os demais ficam registrados ao lado.
                    vistos[chave].setdefault("tambem_em", []).append(fonte["rotulo"])
                    continue
                achado = {
                    "tipo": tipo,
                    "trecho": trecho[:160],
                    "contexto": linha[:200],
                    "documento": fonte["rotulo"],
                    "dono": dono_raw[:80] or "—",
                    "etapa": etapa,
                    "severidade": ("decisao_humana" if etapa == "humano"
                                   else "atencao" if etapa in ETAPAS_NAO_BLOQUEANTES else "bloqueio"),
                }
                vistos[chave] = achado
                achados.append(achado)
    # Marcador de repositório é pendência de plataforma — mas um documento cravejado deles não
    # consultou o gabarito que a esteira já tem nas cópias sincronizadas, e isso é defeito de
    # construção. O teto separa "não tenho como conferir este nome" de "não li a referência".
    TETO_VERIFICAR_REPO = 8
    por_documento: Dict[str, int] = {}
    for a in achados:
        if a.get("tipo") == "verificar_repositorio":
            por_documento[a.get("documento", "?")] = por_documento.get(a.get("documento", "?"), 0) + 1
    for documento, n in sorted(por_documento.items()):
        if n >= TETO_VERIFICAR_REPO:
            achados.append({
                "tipo": "gabarito_desconhecido", "codigo": "gabarito-desconhecido",
                "trecho": f"{n}× [verificar no repositório]",
                "contexto": f"O documento «{documento}» adia {n} definições para o repositório. "
                            f"As cópias em `references/plataforma/` trazem o contrato: acima de "
                            f"{TETO_VERIFICAR_REPO} marcadores o documento não consultou o gabarito.",
                "documento": documento, "dono": "handoff-dev", "etapa": "dev", "severidade": "bloqueio",
            })

    por_etapa = {e: sum(1 for a in achados if a["etapa"] == e) for e in ETAPAS}
    if any(a["severidade"] == "bloqueio" for a in achados):
        status = "bloqueado"
    elif achados:
        status = "amarelo"
    else:
        status = "aprovado"
    return {"status": status, "achados": achados, "por_etapa": por_etapa, "documentos": documentos_lidos}


#: Slugs de agente que um despacho sabe acionar. O texto do marcador é livre
#: (`[LACUNA — dono: wireframes]`), então normalizamos para o slug do envelope.
_DONOS_ROTEAVEIS = {
    "jornada": "jornada", "jornada": "jornada",
    "fluxo": "fluxo", "fluxo": "fluxo",
    "copy": "copy-ptbr-revisao", "copy-ptbr": "copy-ptbr-revisao", "copy-ptbr-revisao": "copy-ptbr-revisao",
    "wireframe": "telas", "wireframes": "telas", "telas": "telas",
    "caa": "caa",
    "ambiente": "ambiente-simulado", "ambiente-simulado": "ambiente-simulado",
    "lacunas": "fecha-lacunas", "fecha-lacunas": "fecha-lacunas",
    "handoff": "handoff-dev", "handoff-dev": "handoff-dev",
    "assets": "brief-assets", "brief-assets": "brief-assets",
    "spec": "spec-missao", "spec-missao": "spec-missao",
    "gate-estrutural": "gate-estrutural",
}


def _dono_roteavel(achado: Dict[str, Any]) -> str:
    """Slug do agente quando dá para reconhecer; senão a etapa, que ao menos nomeia o time."""
    bruto = str(achado.get("dono") or "").strip().lower()
    for chave, slug in _DONOS_ROTEAVEIS.items():
        if chave in bruto:
            return slug
    return str(achado.get("etapa") or "produto")


def relatorio_lacunas(resultado: Dict[str, Any], rotulo: str, missao: str = "", agente: str = "rastro-lacunas") -> str:
    r = resultado
    icone = {"aprovado": "🟢 SEM LACUNAS", "amarelo": "🟡 SÓ PENDÊNCIAS HUMANAS", "bloqueado": "🔴 BLOQUEADO"}[r["status"]]
    linhas = [f"# {rotulo} — {missao or 'missão'}", "", f"**Veredito: {icone}**", ""]
    pe = r["por_etapa"]
    linhas.append(
        f"**O que faltou:** input `{pe['input']}` · **produto `{pe['produto']}`** · **design `{pe['design']}`** · dev `{pe['dev']}` · "
        f"plataforma `{pe['plataforma']}` · externo `{pe['externo']}` · humano `{pe['humano']}` "
        f"_(plataforma, externo e humano são pendências de gente: ficam registradas e não impedem o PRD)_"
    )
    linhas.append(f"**Documentos lidos:** {', '.join(r['documentos']) or '— nenhum'}")
    linhas.append("")
    if r["status"] == "bloqueado":
        faltou = [e for e in ("input", "produto", "design", "dev") if pe[e]]
        linhas.append(
            "O PRD **não sai** enquanto houver lacuna de " + " e ".join(f"**{e}**" for e in faltou)
            + ". Cada linha abaixo diz o documento onde a lacuna está e quem tem de fechá-la. Lacuna de plataforma ou de dono externo fica registrada como pendência humana e não impede."
        )
    elif r["status"] == "amarelo":
        linhas.append("Só restam pendências humanas: da **plataforma** (ADR nova, componente de DS, ponte), resolvidas na codificação, e/ou **externas** (coordenação pedagógica, rede parceira, consultoria), resolvidas fora da esteira. O PRD sai `aprovado-com-pendencias` (🟡), nunca `aprovado`.")
    else:
        linhas.append("Nenhum marcador de lacuna nos documentos lidos.")
    linhas.append("")
    linhas.append("## Lacunas")
    linhas.append("")
    if r["achados"]:
        linhas.append("| Etapa que falhou | Documento | Tipo | Dono declarado | Linha do documento |")
        linhas.append("|---|---|---|---|---|")
        for a in sorted(r["achados"], key=lambda x: (ETAPAS.index(x["etapa"]), x["documento"])):
            sev = "⚠️" if a["severidade"] == "atencao" else "⛔"
            # A linha inteira, e não só o marcador: é ela que justifica a etapa escolhida, e
            # `[ABERTO — dono: produto]` sozinho não diz a quem cobrar.
            trecho = (a.get("contexto") or a["trecho"]).replace("|", "\\|").replace("\n", " ")
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
            {"severidade": a["severidade"], "classe": a["tipo"], "codigo": a["etapa"], "agente_responsavel": _dono_roteavel(a), "documento": a["documento"], "resumo": (a.get("contexto") or a["trecho"])[:120]}
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
    # A ficha tem uma linha por campo, em item de lista: `- \`viewport: 375x812\``. A prosa do
    # mesmo bloco repete o nome do campo com dois-pontos ("Por que este viewport: Viewport
    # mobile…") e, por vir antes, era devolvida no lugar do valor — a spec estava certa e o
    # gate reprovava (sessão 8f76, 2026-09-21). A linha de ficha manda; a busca solta é fallback.
    valor = r"\s*:\s*[`*_]*\s*([^`\n|]+?)`?\s*(?:$|\||\(|—|·)"
    ficha = re.search(r"^\s*[-*]\s*[`*_]*" + nome + valor, texto, re.IGNORECASE | re.MULTILINE)
    if ficha:
        return ficha.group(1).strip().strip("*_ ")
    m = re.search(r"`?\b" + nome + valor, texto, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else None


def _lista(valor: str) -> Optional[List[str]]:
    m = re.search(r"\[(.*?)\]", valor or "", re.DOTALL)
    if not m:
        return None
    itens = [i.strip().strip('"').strip("'").strip("`") for i in m.group(1).split(",")]
    return [i for i in itens if i]


#: `expNNefNb`: NN = ano, `ef`/`em` = etapa, dígito antes do `b` = bimestre.
#: O identificador passou a carregar ano e bimestre porque a ordem da grade da sala saía
#: errada quando caía no número da experiência — o 7º ano vinha depois do 8º.
RE_ID = re.compile(r"^exp(0[1-9])(ef|em)([1-4])b$")
#: Transversal (`series: []`) e ferramenta de professor não têm ano nem bimestre: seguem
#: no formato antigo, que é o único que comporta a ausência dos dois.
RE_ID_TRANSVERSAL = re.compile(r"^exp-\d{2}-[a-z0-9][a-z0-9-]*$")


def decompor_id(identificador: str) -> Optional[Dict[str, Any]]:
    """Devolve `{"serie": "5EF", "unidade": 3}` a partir de `exp05ef3b`, ou None."""
    m = RE_ID.match((identificador or "").strip().lower())
    if not m:
        return None
    ano, etapa, bimestre = int(m.group(1)), m.group(2).upper(), int(m.group(3))
    if etapa == "EF" and not 1 <= ano <= 9:
        return None
    if etapa == "EM" and not 1 <= ano <= 3:
        return None
    return {"serie": f"{ano}{etapa}", "unidade": bimestre}


def validar_manifesto(spec: str) -> Dict[str, Any]:
    from tools.bncc import secao_bloco  # bloco 0 da spec, mesmo parser

    texto = secao_bloco(spec or "", 0) or (spec or "")[:4000]
    achados: List[Dict[str, str]] = []
    campos: Dict[str, Any] = {}

    def falta(campo: str, motivo: str, etapa: str = "produto") -> None:
        achados.append({"severidade": "bloqueio", "campo": campo, "etapa": etapa, "resumo": motivo})

    v = _campo(texto, "id")
    campos["id"] = v
    id_decomposto = decompor_id(v or "")
    if not v:
        falta("id", "`id` ausente no bloco 0.")
    elif not id_decomposto and not RE_ID_TRANSVERSAL.match(v):
        falta(
            "id",
            f"`id` fora de `expNNefNb` / `expNNemNb` (lido: {v!r}). "
            "O número é o ANO e o dígito antes do `b` é o BIMESTRE: `exp01ef1b` = 1º ano do "
            "Fundamental, 1º bimestre; `exp02em2b` = 2º ano do Médio, 2º bimestre. "
            "Missão transversal ou ferramenta de professor, que não têm ano nem bimestre, "
            "usam o formato antigo `exp-NN-<slug>`."
        )

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

    # O formato antigo existe só para quem não tem ano nem bimestre. Missão de estudante
    # com série declarada tem os dois — e precisa carregá-los no id.
    # `v` é reutilizado por cada campo lido acima — o id vive em `campos["id"]`.
    identificador = campos.get("id") or ""
    if identificador and not id_decomposto and RE_ID_TRANSVERSAL.match(identificador):
        if series and (campos.get("publico") or "").lower() == "estudante":
            falta(
                "id",
                f"`id: {identificador}` está no formato antigo, mas a missão declara série {series} e público estudante. "
                "Use `expNNefNb` — por exemplo, 5º ano do Fundamental no 3º bimestre é `exp05ef3b`.",
            )

    # O id carrega ano e bimestre, e `series`/`unidade` continuam campos próprios porque é
    # assim que a plataforma os lê. Duas fontes para o mesmo fato só servem se concordarem.
    if id_decomposto:
        esperada = id_decomposto["serie"]
        if series is not None and [s.upper() for s in series] != [esperada]:
            falta(
                "series",
                f"`id: {campos['id']}` diz {esperada}, mas `series` traz {series}. "
                "Um dos dois está errado — e o id é o que nomeia arquivos, tabelas e branch.",
            )
        u = (campos.get("unidade") or "").strip()
        if u and u != str(id_decomposto["unidade"]):
            falta(
                "unidade",
                f"`id: {campos['id']}` diz bimestre {id_decomposto['unidade']}, mas `unidade` traz {u!r}.",
            )

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

    # `por-turma` é o único valor que a plataforma aceita (ADR-69), então ausência é
    # default, não defeito: cobrar uma linha que só pode ter um valor é cerimônia.
    # O que ainda importa é denunciar quem declara OUTRA coisa — aí há divergência real.
    v = _campo(texto, "liberacao"); campos["liberacao"] = v or "por-turma"
    if v and "por-turma" not in v.lower():
        falta("liberacao", f"`liberacao` declarada como {v!r}: a plataforma só abre missão liberada por turma (ADR-69).")

    # Capturar voz ou imagem de criança é contrato de dados, não só permissão de
    # iframe: o bloco 9 tem de dizer onde a mídia fica, por quanto tempo e quem lê.
    capturas = [p for p in extensoes if p in CAPTURA_DE_MIDIA]
    if capturas:
        bloco9 = secao_bloco(spec or "", 9) or ""
        # Detectores amplos de propósito: o gate pega a ausência gritante, não julga
        # a qualidade do contrato de dados — isso é da banca (DAD-07/08). Regex
        # estreito aqui produz falso positivo e barra missão que declarou tudo.
        menciona_midia = bool(re.search(r"[áa]udio|voz|oralidade|foto|imagem|v[íi]deo|grava[çc]|grava[dç]", bloco9, re.IGNORECASE))
        tem_destino = bool(re.search(r"\bexp\d{2}e[fm]\db_[a-z][a-z0-9_]*|bucket|-assets|tabela", bloco9, re.IGNORECASE))
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
    # Radical curto e conjugação completa: `proibid` não casava "proibição", e a lista
    # de verbos do "não" tinha `use|usar` mas não `usa`, `suporta` mas não `sustenta`.
    # As 8 menções a WebSocket das 14 primeiras execuções eram TODAS negações escritas
    # assim — "Cloud Run não sustenta", "Não usa WebSocket", "proibição de WebSockets",
    # "eliminando qualquer dependência". Nenhuma era proposta (corte A4, 23/09/2026).
    r"proibi|vedad|nunca|jamais|evit[ae]|descartad|obsolet|legad|zero\s+|elimina|abol|"
    r"n[ãa]o\s+(existe|existem|usa|use|usar|usamos|utiliza|h[áa]|aceita|pode|deve|ser[áa]|"
    r"suporta|sustenta|emprega|requer|depende|precisa|mant[ée]m|abre)|"
    r"em vez de|ao inv[ée]s|fora de escopo|removid|deprecia|"
    # "sem custos de WebSocket", "(sem WebSockets)", "sem suporte a WebSockets": três jeitos de
    # descartar o canal que o handoff da sessão 8f76 usou e que viravam aviso (2026-09-21).
    r"sem\s+(campo|coluna|chave|payload|uso|custos?|suporte|depend[êe]ncia|conex[õo]es?|websockets?|sockets?)|nada de|dispensa|"
    # Menção CONDICIONAL ou de roadmap não é proposta: "WebSocket só se a infra mudar",
    # "fica para a fase 2", "se um dia a plataforma suportar". Era a forma de 5 dos 8
    # achados de WebSocket das 14 primeiras execuções, todos em handoffs cujo canal
    # declarado já era o polling correto — o achado pedia a um humano o julgamento que
    # o regex não fazia, e nunca apontou defeito. Proposta afirmativa continua pega.
    r"s[óo]\s+se|somente se|apenas se|caso\s+(a|o|venha|haja)|se\s+(a|o)\s+(infra|plataforma|arquitetura)|"
    r"futur|fase\s*2|pr[óo]xima\s+vers[ãa]o|fora do mvp|n[ãa]o nesta|um dia|hipot[ée]tic|se um dia",
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
    # A tabela é reconhecida nas DUAS grafias, e a errada vira achado próprio. Escrever
    # `exp_04ef1b_gates_turma` com underscore é defeito real — o id já carrega ano e bimestre,
    # e quebrá-lo desalinha migration, Prisma e `@@map`. Mas é defeito de NOME, não de
    # arquitetura: quando os detectores exigiam a grafia certa para reconhecer a tabela, o
    # handoff da exp04ef1b saía com "nenhuma tabela nomeada" e "WebSocket como canal de sala"
    # — duas acusações falsas — enquanto o erro que existia de fato não era nomeado por
    # ninguém. Um defeito, um achado, com o nome que ele tem.
    tabelas_certas = re.findall(r"\bexp\d{2}e[fm]\db_[a-z][a-z0-9_]*", texto)
    tabelas_tortas = re.findall(r"\bexp_\d{2}_?e[fm]\d?b?_[a-z][a-z0-9_]*", texto)
    if not tabelas_certas and not tabelas_tortas:
        bloqueio("tabela-leitura", "Nenhuma tabela `expNNefNb_*` nomeada. Toda medida que a professora vê nasce de tabela própria do módulo — sem tabela de leitura, a medida não existe (`telemetria_eventos` não tem leitor).")
    elif tabelas_tortas:
        exemplo = sorted(set(tabelas_tortas))[0]
        bloqueio("prefixo-tabela", f"Tabela com underscore no identificador (`{exemplo}`): o prefixo é o id inteiro, sem separador interno (`expNNefNb_…`). O id já carrega ano e bimestre, e quebrá-lo desalinha migration, Prisma e `@@map`.")
    # O que importa é o canal DECLARADO, não a palavra. Handoff correto cita WebSocket
    # justamente para descartá-lo ("Cloud Run não sustenta WebSocket, ADR-93/94") ou
    # para colocá-lo como futuro fora de escopo — e era bloqueado por isso.
    # "o canal certo está declarado?" exige polling E a tabela de gates nomeada — só a palavra
    # `polling` viraria escudo para quem propõe WebSocket ao lado. A tabela conta nas duas
    # grafias: quem a nomeou declarou o canal, e o erro de grafia já tem achado próprio acima.
    canal_correto = bool(
        re.search(r"polling", texto, re.IGNORECASE)
        and re.search(r"\bexp_?\d{2}_?e[fm]\d?b?_gates_turma", texto)
    )
    if _usado_afirmativamente(texto, r"websocket|socket\.io|hub:pause"):
        if canal_correto:
            atencao("websocket-mencao", "WebSocket ou `hub:pause` proposto como segunda via de sincronização, apesar de o canal de sala declarado ser o correto (polling em `expNNefNb_gates_turma`). Duas vias de sincronia é uma a mais.")
        else:
            bloqueio("websocket", "WebSocket ou `hub:pause` como canal de sala, sem polling em `expNNefNb_gates_turma` declarado: a plataforma sincroniza por polling HTTP curto (ADR-93/94).")
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


# ------------------------------------------------------------------ consistência interna do PRD
#: Requisitos que uma única tarefa pode cobrir antes de deixar de ser tarefa. Convenção de
#: produto para forçar decomposição — não há achado de literatura atrás deste número.
TETO_RF_POR_TAREFA = 6

#: `RF-001..RF-014`, `RF-001 a RF-014`, `RF-001 até RF-014`, `RF-001–RF-014`.
_RE_INTERVALO_RF = re.compile(r"\bRF-(\d{3})\s*(?:\.\.\.?|--?|–|—|a|at[ée])\s*(?:RF-)?(\d{3})\b", re.I)


def _rfs_da_linha(linha: str) -> set[str]:
    """Todos os requisitos que a linha menciona, com os intervalos já expandidos.

    Cobertura de requisito é escrita das duas formas — `RF-003, RF-004` e `RF-001..RF-014` — e ler
    só a primeira faz o verificador acusar ausência de rastro onde o rastro existe, e deixar passar
    a tarefa que engole a missão inteira.
    """
    rfs = {f"RF-{n}" for n in re.findall(r"\bRF-(\d{3})\b", linha)}
    for ini, fim in _RE_INTERVALO_RF.findall(linha):
        a, b = int(ini), int(fim)
        if a <= b and b - a <= 200:
            rfs.update(f"RF-{n:03d}" for n in range(a, b + 1))
    return rfs


def validar_prd(prd: str) -> Dict[str, Any]:
    """Confere se o PRD é coerente consigo mesmo antes de ir para quem codifica.

    O gabarito já exige tudo isto em prosa — o que faltava era alguém conferir. Um PRD que
    declara dois prefixos de tabela, ou que deixa um requisito P0 sem teste, faz o agente de
    codificação escolher um caminho ao acaso; e a partir daí o resto do documento deixa de
    valer contra o que ele escreveu. São defeitos de consistência, não de conteúdo, e por
    isso dá para pegá-los em código.
    """
    texto = prd or ""
    achados: List[Dict[str, str]] = []

    def falha(codigo: str, resumo: str, severidade: str = "bloqueio", etapa: str = "dev") -> None:
        achados.append({"severidade": severidade, "codigo": codigo, "etapa": etapa, "resumo": resumo})

    # 1. um prefixo de tabela só, e no formato do identificador
    prefixos = {m.lower() for m in re.findall(r"\b(exp_?\d{2}_?e[fm]\d?b?)_[a-z][a-z0-9_]*", texto, re.I)}
    fora = {p for p in prefixos if not re.fullmatch(r"exp\d{2}e[fm]\db", p)}
    if fora:
        falha("prefixo-tabela",
              f"Prefixo de tabela fora do padrão: {sorted(fora)}. O prefixo é o id inteiro, sem separador "
              f"interno (`exp05ef3b_sessoes`). Misturar formatos faz a migration divergir do Prisma.")
    elif len(prefixos) > 1:
        falha("prefixo-tabela", f"Mais de um prefixo de tabela no mesmo PRD: {sorted(prefixos)}.")

    # 2. requisito P0 sem tarefa que o implemente
    #
    # Contar ocorrências do identificador não serve: um PRD bem escrito lista o requisito uma vez na
    # declaração e outra na matriz, e a matriz é justamente quem nomeia as tarefas. Além disso a
    # cobertura costuma vir por intervalo (`RF-001..RF-014`), que não repete o identificador do meio.
    # O que importa é se existe alguma linha que ligue o requisito a uma tarefa.
    p0 = set(re.findall(r"\b(RF-\d{3})\b[^\n]*\bP0\b", texto))
    for rf in sorted(p0):
        coberto = any(rf in _rfs_da_linha(linha) and re.search(r"\bT-\d{3}\b", linha)
                      for linha in texto.splitlines())
        if not coberto:
            falha("rf-sem-rastro",
                  f"`{rf}` é P0 e nenhuma linha do PRD o liga a uma tarefa `T-NNN`. Requisito bloqueante "
                  f"precisa aparecer na matriz de rastreabilidade ou no escopo de uma tarefa — por "
                  f"identificador ou por intervalo.")

    # 3. evento sem tabela de leitura nomeada
    for linha in texto.splitlines():
        if re.search(r"\bEVT-\d+", linha) and "|" in linha:
            if re.search(r"pub/?sub|telemetria_eventos", linha, re.I) and not re.search(r"exp\d{2}e[fm]\db_", linha, re.I):
                evt = re.search(r"\bEVT-\d+", linha)
                # O identificador do evento pode estar em qualquer coluna da linha, e a tabela é larga:
                # citar só o começo da linha escondia a evidência de quem vai corrigir.
                falha("evento-sem-leitor",
                      f"`{evt.group(0) if evt else 'evento'}` aponta Pub/Sub ou `telemetria_eventos` como origem da "
                      f"leitura, em vez da tabela `expNNefNb_*` do módulo. Toda medida que a professora vê nasce de "
                      f"tabela própria do módulo. Linha: `{linha.strip()[:200]}`")

    # 4. tarefa não atômica
    for m in re.finditer(r"\b(T-\d{3})\b[^\n]*?(todos os RFs?|todas as RFs?|todos os requisitos)", texto, re.I):
        falha("tarefa-nao-atomica",
              f"`{m.group(1)}` cobre \"{m.group(2)}\". Tarefa que fecha tudo não é verificável nem divisível.",
              severidade="atencao")

    # 4b. a mesma ausência de decomposição escrita como intervalo
    #
    # `T-005 | RF-001..RF-014` diz o mesmo que "todos os RFs" sem usar a palavra, e escapava da regra
    # acima. O teto é convenção de produto, não achado de literatura: serve para separar tarefa de
    # lista de tarefas.
    for linha in texto.splitlines():
        tarefa = re.search(r"\bT-\d{3}\b", linha)
        if not tarefa or "|" not in linha:
            continue
        cobertos = _rfs_da_linha(linha)
        if len(cobertos) > TETO_RF_POR_TAREFA:
            falha("tarefa-nao-atomica",
                  f"`{tarefa.group(0)}` cobre {len(cobertos)} requisitos "
                  f"({min(cobertos)}…{max(cobertos)}). Tarefa que implementa a missão inteira não é "
                  f"estimável nem verificável: divida por entrega.",
                  severidade="atencao")

    # 5. identificador de código inválido
    for m in re.finditer(r"`?([A-Za-z0-9_-]*-[A-Za-z0-9_-]*(?:Module|Service|Controller))`?", texto):
        falha("identificador-invalido",
              f"`{m.group(1)}` tem hífen e não é identificador válido em TypeScript — o agente vai "
              f"inventar um nome e divergir do módulo registrado.")

    # 6. caminho de experiência declarado de duas formas. O que se procura é a missão NOVA com dois
    # nomes de pasta (o velho `exp-NN-<slug>` ao lado do `expNNefNb`); experiência que já existe na
    # plataforma é referência, não declaração.
    caminhos = {m.rstrip("/") for m in re.findall(r"apps/experiencias/([a-z0-9][a-z0-9-]*)/?", texto)}
    caminhos -= EXPERIENCIAS_EXISTENTES
    if len(caminhos) > 1:
        falha("caminho-divergente",
              f"O PRD declara mais de um diretório para a mesma experiência: {sorted(caminhos)}.")

    # 7. o plano de implementação nomeia o que só ele pode nomear. Estes quatro itens eram
    # cobrados pela banca de dev sobre o HANDOFF (TEC-07/08/09/10) — e a banca roda ANTES do
    # PRD, que é justamente quem os escreve: 24 dos 283 achados das 14 primeiras execuções
    # apontavam ausência de algo que o PRD da mesma sessão já continha. Aqui a pergunta é
    # verificável e cai no documento certo. Atenção, nunca bloqueio: a missão não está errada,
    # o plano é que está incompleto, e quem codifica precisa saber disso sem travar a esteira.
    plano = [
        ("plano-sem-porta", r"experiencias-dev\.ts|strictPort|CORS_ORIGINS",
         "porta de dev da missão (`apps/hub/lib/experiencias-dev.ts`, `strictPort`, `CORS_ORIGINS`)"),
        ("plano-sem-versao", r"EXP_VERSION|versao\.test\.ts",
         "amarração da versão nos três lugares (`experiencia.json`, `package.json`, `EXP_VERSION`)"),
        ("plano-sem-e2e", r"scripts/e2e|rodar\.mjs|walkthrough|playwright",
         "roteiro do smoke walkthrough (`node scripts/e2e/rodar.mjs`)"),
        ("plano-sem-invariantes", r"invariantes\.ts|lista única de invariantes|invariantes de produto",
         "lista única de invariantes de produto (padrão `unoogpt/invariantes.ts`)"),
    ]
    for codigo, padrao, o_que in plano:
        if not re.search(padrao, texto, re.IGNORECASE):
            falha(codigo, f"O plano de implementação não nomeia {o_que} — quem codifica vai decidir sozinho.",
                  severidade="atencao")

    bloqueios = [a for a in achados if a["severidade"] == "bloqueio"]
    status = "bloqueado" if bloqueios else ("amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados}


def relatorio_prd(resultado: Dict[str, Any], missao: str = "") -> str:
    icone = {"aprovado": "🟢 CONSISTENTE", "amarelo": "🟡 COM RESSALVAS", "bloqueado": "🔴 INCONSISTENTE"}[resultado["status"]]
    linhas = [f"# Consistência interna do PRD — {missao or 'missão'}", "",
              f"**Veredito: {icone}** · o PRD conferido contra o que ele mesmo declara.", ""]
    if not resultado["achados"]:
        linhas.append("- Nenhuma contradição interna: prefixo único, requisitos P0 rastreados, eventos com leitor nomeado.")
    for a in resultado["achados"]:
        marca = "⛔" if a["severidade"] == "bloqueio" else "⚠️"
        linhas.append(f"- {marca} `{a['codigo']}` — {a['resumo']}")
    envelope = {
        "agente": "prd-consistencia", "missao": missao or "", "status": resultado["status"],
        "achados": [{"severidade": a["severidade"], "classe": "consistencia", "codigo": a["codigo"],
                     "agente_responsavel": "prd-writer", "resumo": a["resumo"]} for a in resultado["achados"]],
        "precisa_humano": False,
    }
    return "\n".join(linhas) + "\n\n```json\n" + json.dumps(envelope, ensure_ascii=False) + "\n```\n"
