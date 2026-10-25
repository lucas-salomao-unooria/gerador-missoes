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

As listas fechadas espelham a base da plataforma (`prompts/base_plataforma.py`: contrato-manifesto,
produtos-catalogo, series, perfis-claims); reconferir quando a plataforma mudar esses contratos.
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
#: Seções que existiam quando a lista era fixa. Hoje valem como LEGADAS: missão nova não reproduz a
#: identidade de app de terceiro (ADR-133 a 138) e usa `unooriaai`, `unoovista` ou `unoochat`. A lista
#: fixa aceitava só estas — e reprovava `unooriaai`, empurrando a missão do 9º ano (out/2026) para `chatgpt`.
SECOES_LEGADAS = ("instanooria", "unitube", "unootube", "chatgpt", "whatsappmobile")
#: Para qual seção cada legada foi (`ambientes.md`).
SUCESSORA_DA_LEGADA = {"chatgpt": "unooriaai", "instanooria": "unoovista", "whatsappmobile": "unoochat"}


#: Radicais que, no nome de uma seção `nova:<nome>`, apontam a coleção do DS que já cobre aquele app.
#: A exp01ef1b declarou `nova:galeriadefotos` e inventou oito componentes que a `unoogaleria` já tinha
#: (`AlbumCard`, `MediaGrid`, `MediaViewer` com zoom, `PhotoEditor` com recorte) — 07/10/2026.
RADICAIS_DA_COLECAO = {
    "unoogaleria": ("galeria", "foto", "album", "álbum"),
    "unoojornal": ("jornal", "noticia", "notícia", "manchete"),
    "unooblog": ("blog",),
    "unoovista": ("insta", "feed", "rede social"),
    "unoochat": ("whats", "mensageiro", "chat"),
    "unooriaai": ("gpt", "assistente"),
    "tiktooria": ("tiktok", "video curto", "vídeo curto"),
}


def secoes_ds() -> Dict[str, Optional[str]]:
    """`seção → ponte` (ou `None` sem ponte), do contrato da base da plataforma. Sem base, as legadas.

    Mais as coleções do inventário publicado do DS que a plataforma ainda não liga (`unoogaleria`,
    `unoojornal`, `unooblog`): `ambientes.md` manda usá-las, e a lista só do contrato as reprovava como
    "fora da lista" — empurrando a missão para `nova:<nome>` e componentes locais.
    """
    from prompts import base_plataforma

    try:
        secoes = (base_plataforma.contrato().get("design_system") or {}).get("secoes") or []
        mapa = {str(s.get("secao") or "").lower(): s.get("ponte") for s in secoes if s.get("secao")}
    except base_plataforma.BaseIndisponivel:
        mapa = {s: s for s in SECOES_LEGADAS}
    try:
        for marca in (base_plataforma.ds_componentes().get("marcas") or {}):
            mapa.setdefault(str(marca).lower(), None)
    except base_plataforma.BaseIndisponivel:
        pass
    mapa.setdefault("unitube", mapa.get("unootube"))  # nome antigo do UnooTube na esteira
    return mapa


def colecao_que_ja_cobre(nome: str, secoes: Dict[str, Optional[str]]) -> Optional[str]:
    """A coleção do DS cujo radical aparece no nome da seção nova (`galeriadefotos` → `unoogaleria`)."""
    nome = (nome or "").lower()
    for colecao, radicais in RADICAIS_DA_COLECAO.items():
        if colecao in secoes and any(r in nome for r in radicais):
            return colecao
    return None


_RE_SECAO_NO_BRIEFING = re.compile(r"^[\s>*-]*`?secao_ds`?\s*[:=]\s*`?([a-z][\w:-]*)", re.IGNORECASE | re.MULTILINE)
_RE_INTERFACE_FORCADA = re.compile(
    r"^[\s>*-]*interface\s+(?:for[çc]ada|obrigat[óo]ria|fixa)\s*[:=—–-]\s*(.+)$", re.IGNORECASE | re.MULTILINE)


def secao_travada(briefing: str, secoes: Optional[Dict[str, Optional[str]]] = None) -> Optional[Dict[str, Any]]:
    """A seção do DS que o briefing fixou: `{secao, explicita, trecho}`, ou `None`.

    `secao_ds: unoogaleria` é explícita. "Interface forçada: Galeria de Fotos" é lida pelo radical
    (`colecao_que_ja_cobre`) e por isso não é explícita: quem confere avisa, não bloqueia. As três
    gerações da exp03ef1b (07/10/2026) trocaram a `unoogaleria` do briefing por `unoochat`,
    `unoovista` e `whatsappmobile`, e nenhum código lia a seção que o briefing pedia.
    """
    m = _RE_SECAO_NO_BRIEFING.search(briefing or "")
    if m:
        return {"secao": m.group(1).lower(), "explicita": True, "trecho": m.group(0).strip(" >*-")}
    m = _RE_INTERFACE_FORCADA.search(briefing or "")
    if m:
        secao = colecao_que_ja_cobre(m.group(1), secoes if secoes is not None else secoes_ds())
        if secao:
            return {"secao": secao, "explicita": False, "trecho": m.group(0).strip(" >*-")}
    return None


def achado_secao_travada(declarada: str, briefing: str, onde: str,
                         secoes: Optional[Dict[str, Optional[str]]] = None) -> Optional[Dict[str, str]]:
    """Achado quando a seção declarada (`onde`: "a spec", "o one-pager") não é a que o briefing fixou."""
    trava = secao_travada(briefing, secoes)
    if not trava or (declarada or "").strip().strip("`").lower() == trava["secao"]:
        return None
    return {
        "severidade": "bloqueio" if trava["explicita"] else "atencao",
        "secao": trava["secao"],
        "resumo": (
            f"O briefing fixou a seção (“{trava['trecho']}”) e {onde} declara `{declarada or '—'}`. Seção fixada pelo "
            f"briefing é trava: a missão monta na `{trava['secao']}`, e a interação que a coleção não oferece é "
            "pré-requisito do DS, sinalizado — não troca de seção. Se a trava inviabiliza a mecânica, quem decide é o PO."
            + ("" if trava["explicita"] else
               " (Seção lida pelo nome da interface; se o PO quis outra, o briefing diz `secao_ds: <seção>`.)")
        ),
    }


def experiencias_existentes() -> frozenset:
    """Pastas de experiência que já existem: as do contrato da base, mais os nomes antigos (ADR-110)."""
    from prompts import base_plataforma

    try:
        atuais = {str(e.get("id") or "") for e in base_plataforma.contrato().get("experiencias") or []}
    except base_plataforma.BaseIndisponivel:
        atuais = set()
    return EXPERIENCIAS_EXISTENTES | frozenset(a for a in atuais if a)

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

#: Nome que um gate escreve → nome que o despacho de retrabalho conhece. Os juízes não
#: escrevem os slugs exatos (`wireframes`, `spec`, `copy`), e o despacho só casava o nome
#: literal: 33 tickets das 14 primeiras sessões iriam para lugar nenhum. A tabela vivia na
#: fonte única desde 23/09/2026 e nenhum código a lia.
SLUGS_ROTEAVEIS: Dict[str, str] = dict(_TAXONOMIA.get("slugs_roteaveis") or {})


def normalizar_dono(valor: Any) -> str:
    """`Wireframes`, `` `spec` ``, `copy` → o slug que o despacho roteia. Desconhecido passa como veio."""
    bruto = str(valor or "").strip().strip("`*_ ").lower()
    return SLUGS_ROTEAVEIS.get(bruto, bruto)

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
    # O contrato que produto deixou para o PO (`[PARÂMETRO — a definir por produto: …]`, `[PROPOSTA — validar com PO: …]`):
    # é pendência do PO, que o de acordo de produto fecha (`tools/fechar_contrato.py`). Até 23/10/2026 o rastro não os
    # contava, e a spec chegava ao design com 4–6 [PARÂMETRO] e 5–13 [PROPOSTA] em 🟢 (plano «Produto dono do contrato», PR 3)
    ("parametro", re.compile(r"\[PAR[ÂA]METRO\b\s*([^\]\n]*?)\s*\]")),
    ("proposta", re.compile(r"\[PROPOSTA\b\s*([^\]\n]*?)\s*\]")),
]
#: Marcadores do contrato aberto: a descrição que é só reticência ou `<placeholder>` cita o formato
#: («Aplicação do marcador `[PARÂMETRO — a definir por produto: …]`», one-pager da exp02em1b).
_RE_CONTRATO_CITADO = re.compile(r"(?::|^)\s*(?:…|\.\.\.|<[^>]*>)\s*$")
#: O marcador sem descrição logo depois da palavra «marcador» também é o nome dele citado na prosa: «Quatro propostas
#: pontuais submetidas ao PO registradas com marcador normativo `[PROPOSTA P0b — validar com PO]`» (spec da
#: exp01em1b-e3980485, 22/10/2026) virava item do cartão de produto. Só a palavra separa: na exp03ef1b e na exp05ef1b
#: há [PROPOSTA] sem descrição, fora de tabela, que é pendência de verdade («… 2 notícias") [PROPOSTA — validar com PO]»).
_RE_CITA_O_MARCADOR = re.compile(r"\bmarcador(?:es)?\b[^\n`\[\]]{0,30}`?\s*$", re.IGNORECASE)


def cita_o_marcador(antes_na_linha: str) -> bool:
    """O texto da linha antes do marcador termina em «marcador …»: o marcador é citado, não aberto."""
    return bool(_RE_CITA_O_MARCADOR.search(antes_na_linha or ""))

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


# ------------------------------------------------------------------ etapa corrente
#: Onde o rastro de lacunas lê, em cada etapa: o que ela escreve mais tudo o que veio antes.
#: `etapa_padrao` é a etapa DONA do documento — é por ela que `_severidade_na_etapa` separa o
#: que esta etapa escreveu do que herdou. Fonte única: produto, design, dev e o
#: `scripts/reavaliar_gates.py` leem daqui.
FONTES_SPEC: List[Dict[str, str]] = [
    {"chave": "spec_missao", "rotulo": "spec da missão", "etapa_padrao": "produto"},
]
FONTES_DESIGN: List[Dict[str, str]] = FONTES_SPEC + [
    # o bloco 13 (D0-UX) e o 14 (D9) moram no anexo de design desde o PR 6: a `spec_missao` é a de produto
    {"chave": "anexo_design_spec", "rotulo": "anexo de design da spec", "etapa_padrao": "design"},
    {"chave": "jornada_telas", "rotulo": "jornada", "etapa_padrao": "design"},
    {"chave": "fluxo_arestas", "rotulo": "fluxo", "etapa_padrao": "design"},
    {"chave": "copy_strings_revisada", "rotulo": "copy revisada", "etapa_padrao": "design"},
    {"chave": "wireframes_cobertura", "rotulo": "telas", "etapa_padrao": "design"},
    # A folha do Stitch registra `[LACUNA — dono: telas]` quando a visão do professor
    # (E0-PROF-*) não foi construída — sem esta fonte a lacuna existiria e ninguém a leria.
    {"chave": "stitch_links", "rotulo": "telas no Stitch", "etapa_padrao": "design"},
    {"chave": "camada_caa", "rotulo": "camada CAA", "etapa_padrao": "design"},
    {"chave": "ambiente_simulado", "rotulo": "ambiente simulado", "etapa_padrao": "design"},
]
FONTES_DEV: List[Dict[str, str]] = FONTES_DESIGN + [
    {"chave": "handoff_dev", "rotulo": "handoff de dev", "etapa_padrao": "dev"},
    {"chave": "brief_assets", "rotulo": "brief de assets", "etapa_padrao": "dev"},
    {"chave": "banco_conteudo", "rotulo": "banco de conteúdo", "etapa_padrao": "dev"},
]

#: Posição de cada etapa bloqueante na esteira. `input` fica com produto: a falta de insumo se
#: fecha refazendo produto com o material, e é no parecer de produto que isso se decide.
_POSICAO_NA_ESTEIRA = {"input": 0, "produto": 0, "design": 1, "dev": 2}

#: `— Resolvido em [D0-09]`: a marca que o fechamento de lacunas (D0) põe na linha do `[ABERTO]`
#: que ele fechou. O número é comparado sem zero à esquerda, porque o bloco 13 escreve `[D0-9]`.
#: Desde o PR 6 as decisões do passo de completude de produto (`[CP-n]`, bloco 15 da spec) fecham célula do mesmo jeito.
_RE_RESOLVIDO_D0 = re.compile(r"resolvid[oa]s?\s+(?:em|no|na|pel[oa])\s*\[?\s*(D0|CP)-0*(\d+)\s*\]?", re.IGNORECASE)
_RE_DECISAO_D0 = re.compile(r"\[\s*D0-0*(\d+)\s*\]")
_RE_DECISAO = re.compile(r"\[\s*(D0|CP)-0*(\d+)\s*\]", re.IGNORECASE)


def _id(prefixo: str, numero: str) -> str:
    return f"{prefixo.upper()}-{int(numero)}"


#: O título do mapa célula → D0, dentro do bloco 13: «### Mapa célula → D0».
_RE_TITULO_MAPA_D0 = re.compile(r"^#{2,4}\s*\**\s*Mapa\s+c[ée]lula\b.*$", re.IGNORECASE | re.MULTILINE)
_RE_TITULO_QUALQUER = re.compile(r"^#{1,4}\s", re.MULTILINE)


def marcadores_de_lacuna(texto: str) -> List[str]:
    """Os marcadores de lacuna (`[ABERTO …]`, `[LACUNA …]`, `[NEEDS CLARIFICATION …]`) do texto, na ordem."""
    saida: List[str] = []
    for tipo, regex in _MARCADORES:
        if tipo in ("lacuna", "aberto", "needs_clarification"):
            saida += [m.group(0).strip() for m in regex.finditer(texto or "") if m.group(0).strip() not in saida]
    return saida


def _norm_marcador(trecho: str) -> str:
    return " ".join(re.sub(r"[—–]", "-", (trecho or "").replace("`", "").replace("*", "")).lower().split())


def _linhas_do_mapa(texto: str) -> List[str]:
    """As linhas das seções «Mapa célula → D0» do texto (do título ao próximo título)."""
    linhas: List[str] = []
    for m in _RE_TITULO_MAPA_D0.finditer(texto or ""):
        prox = _RE_TITULO_QUALQUER.search(texto, m.end())
        linhas += texto[m.end(): prox.start() if prox else len(texto)].splitlines()
    return linhas


def mapa_celula_d0(texto: str) -> Dict[str, int]:
    """`{marcador normalizado: n}` do mapa célula → D0 do bloco 13.

    Desde 23/10/2026 a spec é a do Gate 0 + 13 + 14, montada em código: o D0 não escreve mais ` — Resolvido em [D0-n]`
    na linha do `[ABERTO]` que fechou (plano «Produto dono do contrato», PR 2). A marca passou a viver no bloco 13, numa
    tabela «marcador → decisão», e some com ele — nunca fica marcando o texto do Gate 0 sem a decisão que a sustenta."""
    return {k: int(v.split("-")[1]) for k, v in mapa_celula(texto).items() if v.startswith("D0-")}


def mapa_celula(texto: str) -> Dict[str, str]:
    """`{marcador normalizado: "D0-n" | "CP-n"}` dos mapas célula → decisão: o do bloco 13 (D0-UX, no anexo de design) e
    o do bloco 15 (completude de produto, na spec, PR 6)."""
    mapa: Dict[str, str] = {}
    for linha in _linhas_do_mapa(texto):
        ids = _RE_DECISAO.findall(linha)
        if not ids:
            continue
        for marcador in marcadores_de_lacuna(linha):
            mapa.setdefault(_norm_marcador(marcador), _id(*ids[-1]))
    return mapa


def _decisoes(textos: List[str]) -> set:
    """Os ids `D0-n` e `CP-n` que existem: citados numa linha que não é a marca de resolvido nem do mapa (`_decisoes_d0`)."""
    ids: set = set()
    for texto in textos:
        do_mapa = {l.strip() for l in _linhas_do_mapa(texto)}
        for linha in texto.splitlines():
            if not _RE_RESOLVIDO_D0.search(linha) and linha.strip() not in do_mapa:
                ids.update(_id(p, n) for p, n in _RE_DECISAO.findall(linha))
    return ids


def _decisoes_d0(textos: List[str]) -> set:
    """Números das decisões `[D0-n]` que existem: citadas numa linha que não é a marca de resolvido.

    A marca sozinha não fecha nada. Em 25/09/2026 (exp04ef1b) a linha `[ABERTO — dono: produto:
    Ratificação formal do teto de texto…] — Resolvido em [D0-09]` barrou o PRD, com o `[D0-9]`
    decidido no bloco 13 — mas uma marca que aponta para um D0 inexistente é pendência aberta. A linha do mapa célula
    → D0 também não define decisão: é a marca, só que no bloco 13.
    """
    numeros: set = set()
    for texto in textos:
        do_mapa = {l.strip() for l in _linhas_do_mapa(texto)}
        for linha in texto.splitlines():
            if not _RE_RESOLVIDO_D0.search(linha) and linha.strip() not in do_mapa:
                numeros.update(int(n) for n in _RE_DECISAO_D0.findall(linha))
    return numeros


def decisoes_do_bloco_13(spec: str) -> Optional[set]:
    """Os números [D0-n] que o bloco 13 da spec define (sem as linhas do mapa célula → D0), ou `None` sem o bloco."""
    return decisoes_do_bloco(spec, "13", "D0")


def decisoes_do_bloco(spec: str, numero: str, prefixo: str) -> Optional[set]:
    """Os números `[<prefixo>-n]` que o bloco `## <numero>` define (sem as linhas do mapa célula → decisão), ou `None`
    sem o bloco: o 13 (D0, no anexo de design) e o 15 (completude de produto, `CP`, na spec — PR 6)."""
    m = re.search(rf"^##\s*\**\s*{numero}\b.*$", spec or "", re.MULTILINE)
    if not m:
        return None
    fim = re.search(r"^## ", spec[m.end():], re.MULTILINE)
    bloco = spec[m.start(): m.end() + fim.start() if fim else len(spec)]
    do_mapa = {l.strip() for l in _linhas_do_mapa(bloco)}
    citado = re.compile(rf"\b{prefixo}-0*(\d+)\b")
    return {int(n) for linha in bloco.splitlines() if linha.strip() not in do_mapa for n in citado.findall(linha)}


#: Onde mora a decisão de cada prefixo citado a jusante (PR 6): o D0-UX no bloco 13 do anexo de design, a completude de
#: produto no bloco 15 da spec. `(prefixo, bloco, código do achado, dono quando o bloco falta, onde o bloco mora)`.
_DECISOES_CITAVEIS = (
    ("D0", "13", "d0-orfao", "fecha-lacunas", "no anexo de design (decisões do D0)"),
    ("CP", "15", "cp-orfao", "completude-spec", "na spec de produto (completude, passo 046)"),
)


def d0_orfaos(fontes: List[Dict[str, str]], state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Achado `d0-orfao` para cada documento que cita [D0-n] que o bloco 13 não define — e `cp-orfao` para [CP-n] que o
    bloco 15 da spec não define.

    O PRD da 4fd72a9a (exp02ef1b, 22/10/2026) citava D0-1 e D0-6 apontando para `produto/05-spec-missao.md`, que não
    tinha nenhum: o bloco 13 tinha caído na montagem (linhas-perdidas). O fluxo, a copy, as telas e a CAA dela e da
    60cfa7f4 (exp02em1b), e o handoff dela, citavam o mesmo vazio. Quem lê a citação abre a spec e não acha a decisão (plano «Produto dono do
    contrato», PR 2). Desde o PR 6 o bloco 13 mora no anexo de design, e a régua lê a spec de produto mais o anexo
    (`tools.anexo_design.spec_consolidada`); na sessão anterior, a `spec_missao` com os blocos dentro. O anexo do PRD não
    conta."""
    from tools.anexo_design import KEY_ANEXO, spec_consolidada
    from tools.conteudo_aprovado import remover_anexo

    spec = spec_consolidada(state)
    saida: List[Dict[str, Any]] = []
    for prefixo, numero, codigo, dono_do_bloco, onde in _DECISOES_CITAVEIS:
        definidos = decisoes_do_bloco(spec, numero, prefixo)
        citado = re.compile(rf"\b{prefixo}-0*(\d+)\b")
        for fonte in fontes:
            texto = state.get(fonte["chave"])
            if fonte["chave"] in ("spec_missao", KEY_ANEXO) or not isinstance(texto, str) or not texto:
                continue
            if fonte["chave"] == "prd_final":
                texto = remover_anexo(texto)
            elif fonte["chave"] == "ambiente_simulado":
                # o D9 recopia o bloco 13 inteiro, e o código descarta a cópia: só o bloco 14 é dele. Na exp03ef1b-317df247
                # a cópia trazia um D0-7 da rodada anterior do D0, que a spec montada já não tinha
                texto = "\n".join(m.group(0) for m in re.finditer(r"^##\s*(?:Bloco\s*)?14\b.*?(?=^## |\Z)", texto,
                                                                    re.MULTILINE | re.DOTALL))
            orfaos = sorted({int(n) for n in citado.findall(texto)} - (definidos or set()))
            if not orfaos:
                continue
            ids = ", ".join(f"{prefixo}-{n}" for n in orfaos)
            etapa = fonte.get("etapa_padrao", "dev")
            saida.append({
                "tipo": codigo.replace("-", "_"), "codigo": codigo, "trecho": ids,
                "contexto": (f"«{fonte['rotulo']}» cita {ids}, que " + (f"não existe: falta o bloco {numero} {onde}"
                             if definidos is None else f"o bloco {numero} {onde} não define")
                             + ". A decisão citada precisa existir no documento para o qual ele aponta."),
                "resumo": (f"«{fonte['rotulo']}» cita {ids} — " + (f"falta o bloco {numero} {onde}"
                           if definidos is None else f"decisão(ões) que o bloco {numero} {onde} não tem")
                           + f": confira a citação ou o bloco {numero}."),
                "documento": fonte["rotulo"],
                "dono": dono_do_bloco if definidos is None else fonte["rotulo"],
                "etapa": etapa,
            })
    return saida


def _severidade_na_etapa(severidade: str, dono: str, documento: str, etapa_corrente: Optional[str]) -> tuple:
    """`(severidade, motivo)` da lacuna vista pela etapa que está rodando.

    Cada etapa bloqueia pelo que é dela. Antes o rastro só rodava em dev, e uma pendência de
    produto na spec aprovada barrava o PRD numa etapa que não pode reescrever a spec (exp04ef1b,
    25/09/2026). Agora:

    - dono de uma etapa **seguinte** → `adiante`: registrada, e a etapa dela a cobra;
    - dono e documento de uma etapa **anterior** → `heranca`: já passou pelo rastro da etapa
      dona e pelo parecer dela, e quem está aqui não tem a caneta;
    - dono anterior num documento **desta** etapa continua bloqueando: foi esta etapa que o
      escreveu, e é ela que o reescreve.

    Sem `etapa_corrente` (reavaliação avulsa, chamada antiga), nada muda.
    """
    agora = _POSICAO_NA_ESTEIRA.get(etapa_corrente or "")
    pos_dono = _POSICAO_NA_ESTEIRA.get(dono)
    if severidade != "bloqueio" or agora is None or pos_dono is None:
        return severidade, ""
    if pos_dono > agora:
        return "atencao", "adiante"
    pos_doc = _POSICAO_NA_ESTEIRA.get(documento, agora)
    if pos_dono < agora and pos_doc < agora:
        return "atencao", "heranca"
    return severidade, ""


#: Outra cor de pictograma seguida de palavra na mesma linha: «🟡 Brincar, 🔵 Estudar, 🟢 Comer» é série, não pendência.
_RE_SERIE_DE_CORES = re.compile(r"[🟡🟢🔴🟠🟣🟤⚪⚫]️?\s*[\"“']?[A-Za-zÀ-ú]")
_CORES = set("🟡🟢🔴🟠🟣🟤⚪⚫🔵")
#: O que faz de um 🔵 uma pendência, logo depois dele: «🔵 a validar», «🔵 pendente», «🔵 confirmar com…» — e não o
#: rótulo de botão adiante na mesma frase («… "Confirmar Enquadramento"»).
_RE_PENDENCIA_AZUL = re.compile(r"^\W{0,3}(?:a\s+)?(?:validar|pend[eê]n|confirmar|definir|verificar|homologar|aguard)",
                                re.IGNORECASE)


def _e_pictograma_azul(texto: str, inicio: int) -> bool:
    """O 🔵 em `inicio` é conteúdo da missão (pictograma, rótulo de botão), não o marcador «🔵 a validar».

    Na exp02ef1b (23/10/2026) a intenção comunicativa se escolhe por «🟡 Brincar · 🔵 Estudar · 🟢 Comer»: o rastro achou
    13 pendências em spec, jornada, telas, copy, CAA e ambiente, e uma virou bloqueio de design. É pictograma o 🔵 entre
    aspas, numa série de cores na mesma linha, ou rótulo curto de célula de tabela — sempre sem palavra de pendência.
    """
    ini_linha = texto.rfind("\n", 0, inicio) + 1
    fim_linha = texto.find("\n", inicio)
    linha = texto[ini_linha:fim_linha if fim_linha >= 0 else len(texto)]
    pos = inicio - ini_linha
    depois = linha[pos + 1:]
    celula = depois.split("|", 1)[0] if linha.lstrip().startswith("|") else depois[:60]
    if _RE_PENDENCIA_AZUL.search(celula):
        return False
    if linha[pos - 1:pos] in ("\"", "“", "'", "‘", "`"):
        return True
    if _RE_SERIE_DE_CORES.search(linha):
        return True
    # cores encostadas: «Tocar (pictograma 🟡🔵🟢)»
    if _CORES & {linha[pos - 1:pos], linha[pos + 1:pos + 2]}:
        return True
    palavras = re.findall(r"[A-Za-zÀ-ú]+", celula)
    return linha.lstrip().startswith("|") and 1 <= len(palavras) <= 3


def varrer_lacunas(fontes: List[Dict[str, str]], state: Dict[str, Any],
                   etapa_corrente: Optional[str] = None) -> Dict[str, Any]:
    """`fontes` = [{"chave": <state key>, "rotulo": <nome legível>, "etapa_padrao": <etapa>}].

    `etapa_corrente` (`produto` · `design` · `dev`) é a etapa que roda o rastro: ela só bloqueia
    pelo que é dela (`_severidade_na_etapa`). O `etapa_padrao` de cada fonte diz de que etapa é
    o documento.
    """
    achados: List[Dict[str, Any]] = []
    documentos_lidos: List[str] = []
    vistos: Dict[tuple, Dict[str, Any]] = {}
    resolvidos: List[Dict[str, Any]] = []
    textos = [t for f in fontes if isinstance(t := state.get(f["chave"]), str) and t]
    # as decisões que fecham célula: [D0-n] do bloco 13 (anexo de design) e [CP-n] do bloco 15 (spec de produto, PR 6)
    decisoes = _decisoes(textos)
    mapa: Dict[str, str] = {}
    for texto_fonte in textos:
        for marcador, ident in mapa_celula(texto_fonte).items():
            mapa.setdefault(marcador, ident)
    etapa_do_documento = {f["rotulo"]: f.get("etapa_padrao", "dev") for f in fontes}
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
                # O nome do marcador entre crases, sem conteúdo, é citação e não pendência: "Todos os
                # marcadores `[NEEDS CLARIFICATION]` foram saneados" virava pendência humana e deixava
                # o PRD 🟡 (24/09/2026). Pendência de verdade vem sem crase, ou com a pergunta dentro.
                if not dono_raw and texto[m.start() - 1:m.start()] == "`" and texto[m.end():m.end() + 1] == "`":
                    continue
                if tipo == "a_validar" and _e_pictograma_azul(texto, m.start()):
                    continue
                if tipo in ("parametro", "proposta") and (not dono_raw or _RE_CONTRATO_CITADO.search(dono_raw)):
                    continue  # `[PROPOSTA]` sozinho, ou com «…», é o nome do marcador citado na prosa
                if (tipo in ("parametro", "proposta") and ":" not in dono_raw
                        and cita_o_marcador(texto[texto.rfind("\n", 0, m.start()) + 1:m.start()])):
                    continue  # «registradas com marcador normativo `[PROPOSTA P0b — validar com PO]`»
                linha, contexto = _linha_e_contexto(texto, m.start(), m.end())
                fechado = _RE_RESOLVIDO_D0.search(linha)
                ident = _id(*fechado.groups()) if fechado else mapa.get(_norm_marcador(trecho))
                if tipo in ("lacuna", "aberto", "needs_clarification") and ident is not None and ident in decisoes:
                    if not any(r["trecho"] == trecho[:160] for r in resolvidos):
                        resolvidos.append({"trecho": trecho[:160], "documento": fonte["rotulo"], "d0": ident})
                    continue
                if tipo in ("rs_pendente", "verificar_repositorio", "parametro", "proposta"):
                    # Dono fixo, do contrato: `RS-n pendente` é pedido ao Gate 0/PO que só
                    # pessoa fecha, e `[verificar no repositório]` é instrução para quem
                    # codifica — os agentes não têm o monorepo por desenho. Os dois eram
                    # roteados para `produto` e `dev`, bloqueantes, e os prompts mandavam
                    # escrevê-los: a esteira punia o agente por obedecer.
                    etapa = _DONO_DO_MARCADOR[tipo]
                elif tipo == "a_validar":
                    # Todo prompt que ensina o 🔵 o descreve como pendência externa a validar
                    # (criterios-pedagogicos.md:41 · 113_prd_writer.md:151 · 043_gate_final.md:30).
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
                severidade, motivo = _severidade_na_etapa(
                    "decisao_humana" if etapa == "humano" else "atencao" if etapa in ETAPAS_NAO_BLOQUEANTES else "bloqueio",
                    etapa, fonte.get("etapa_padrao", "dev"), etapa_corrente)
                # a linha e o marcador inteiros: vão ao cartão do PO, e o corte em 200/160 partia a palavra no meio
                # (as linhas «[ABERTO — dono: PO: …» das sessões de 24/10/2026 passam de 200 caracteres). A chave de
                # repetição acima e a lista de resolvidos não dependem deste campo.
                achado = {
                    "tipo": tipo,
                    "trecho": trecho,
                    "contexto": linha,
                    "documento": fonte["rotulo"],
                    "dono": dono_raw[:80] or "—",
                    "etapa": etapa,
                    "severidade": severidade,
                }
                if motivo:
                    achado["motivo"] = motivo
                vistos[chave] = achado
                achados.append(achado)
    for orfao in d0_orfaos(fontes, state):
        severidade, motivo = _severidade_na_etapa("bloqueio", orfao["etapa"], orfao["etapa"], etapa_corrente)
        achados.append({**orfao, "severidade": severidade, **({"motivo": motivo} if motivo else {})})
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
            # O defeito é de quem escreveu o documento. Sem etapa corrente, vale o de sempre: dev.
            dono_doc = etapa_do_documento.get(documento, "dev") if etapa_corrente else "dev"
            severidade, motivo = _severidade_na_etapa("bloqueio", dono_doc, dono_doc, etapa_corrente)
            achados.append({
                "tipo": "gabarito_desconhecido", "codigo": "gabarito-desconhecido",
                "trecho": f"{n}× [verificar no repositório]",
                "contexto": f"O documento «{documento}» adia {n} definições para o repositório. "
                            f"As cópias em `references/plataforma/` trazem o contrato: acima de "
                            f"{TETO_VERIFICAR_REPO} marcadores o documento não consultou o gabarito.",
                "documento": documento, "dono": "handoff-dev", "etapa": dono_doc, "severidade": severidade,
                **({"motivo": motivo} if motivo else {}),
            })

    # Nenhum documento com conteúdo não é "sem lacunas" — é ausência de documento. O relatório
    # saía 🟢 SEM LACUNAS com `documentos` vazio, que é o veredito mais perigoso que existe:
    # afirma que se leu tudo e nada havia.
    lidos = [d for d in documentos_lidos if d.get("chars", 0) > 0] if documentos_lidos and isinstance(documentos_lidos[0], dict) else documentos_lidos
    if not lidos:
        achados.append({
            "tipo": "fonte_vazia", "codigo": "fontes-vazias", "trecho": "—",
            "contexto": "Nenhum dos documentos varridos tinha conteúdo: não há como afirmar que não há lacunas.",
            "documento": "—", "dono": etapa_corrente or "dev", "etapa": etapa_corrente or "dev", "severidade": "bloqueio",
        })

    por_etapa = {e: sum(1 for a in achados if a["etapa"] == e) for e in ETAPAS}
    if any(a["severidade"] == "bloqueio" for a in achados):
        status = "bloqueado"
    elif achados:
        status = "amarelo"
    else:
        status = "aprovado"
    return {"status": status, "achados": achados, "por_etapa": por_etapa, "documentos": documentos_lidos,
            "resolvidos": resolvidos, "etapa_corrente": etapa_corrente}


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
    icone = {"aprovado": "🟢 NENHUM MARCADOR DE LACUNA", "amarelo": "🟡 SÓ PENDÊNCIAS HUMANAS", "bloqueado": "🔴 BLOQUEADO"}[r["status"]]
    linhas = [f"# {rotulo} — {missao or 'missão'}", "", f"**Veredito: {icone}**", ""]
    pe = r["por_etapa"]
    etapa_corrente = r.get("etapa_corrente")
    # O que esta etapa não entrega enquanto houver bloqueio: a spec em produto, o design, o PRD.
    alvo = {"produto": "A spec **não fecha**", "design": "O design **não fecha**"}.get(etapa_corrente or "", "O PRD **não sai**")
    linhas.append(
        f"**O que faltou:** input `{pe['input']}` · **produto `{pe['produto']}`** · **design `{pe['design']}`** · dev `{pe['dev']}` · "
        f"plataforma `{pe['plataforma']}` · externo `{pe['externo']}` · humano `{pe['humano']}` "
        f"_(plataforma, externo e humano são pendências de gente: ficam registradas e não impedem a etapa)_"
    )
    linhas.append(f"**Documentos lidos:** {', '.join(r['documentos']) or '— nenhum'}")
    linhas.append("")
    motivos = {a.get("motivo") for a in r["achados"]}
    if r["status"] == "bloqueado":
        faltou = [e for e in ("input", "produto", "design", "dev")
                  if any(a["etapa"] == e and a["severidade"] == "bloqueio" for a in r["achados"])]
        linhas.append(
            f"{alvo} enquanto houver lacuna de " + " e ".join(f"**{e}**" for e in faltou)
            + ". Cada linha abaixo diz o documento onde a lacuna está e quem tem de fechá-la. Lacuna de plataforma ou de dono externo fica registrada como pendência humana e não impede."
        )
    elif r["status"] == "amarelo":
        linhas.append("Nada aqui é desta etapa fechar. Restam pendências de gente — da **plataforma** (ADR nova, componente de DS, ponte), resolvidas na codificação; **externas** (coordenação pedagógica, rede parceira, consultoria) ou **humanas** (homologar, ratificar), resolvidas fora da esteira — e as de outras etapas, marcadas na tabela. A etapa segue 🟡, nunca 🟢.")
    else:
        linhas.append("Nenhum marcador de lacuna nos documentos lidos. Isto NÃO quer dizer que nada falta: este rastro só acha o que um agente marcou como pendente. A fidelidade ao pedido do PO e a coerência entre documentos são conferidas em outros gates.")
    if "heranca" in motivos:
        linhas.append("")
        linhas.append("_«de etapa anterior»: a lacuna é de uma etapa que já passou pelo próprio rastro e pelo parecer, num documento dela. Esta etapa não a reescreve; fica registrada para quem a aprovou._")
    if "adiante" in motivos:
        linhas.append("")
        linhas.append("_«fica para a etapa dela»: a lacuna é de uma etapa seguinte, que a cobra no rastro dela._")
    linhas.append("")
    linhas.append("## Lacunas")
    linhas.append("")
    rotulo_motivo = {"heranca": " _(de etapa anterior)_", "adiante": " _(fica para a etapa dela)_"}
    if r["achados"]:
        linhas.append("| Etapa | Documento | Tipo | Dono declarado | Linha do documento |")
        linhas.append("|---|---|---|---|---|")
        for a in sorted(r["achados"], key=lambda x: (ETAPAS.index(x["etapa"]), x["documento"])):
            # ⛔ só no que bloqueia: a decisão humana saía ⛔ e parecia impedimento (exp04ef1b).
            sev = "⛔" if a["severidade"] == "bloqueio" else "⚠️"
            # A linha inteira, e não só o marcador: é ela que justifica a etapa escolhida, e
            # `[ABERTO — dono: produto]` sozinho não diz a quem cobrar.
            trecho = (a.get("contexto") or a["trecho"]).replace("|", "\\|").replace("\n", " ")
            linhas.append(f"| {sev} **{a['etapa']}**{rotulo_motivo.get(a.get('motivo', ''), '')} | {a['documento']} | "
                          f"`{a['tipo']}` | {a['dono']} | {trecho} |")
    else:
        linhas.append("_Nenhuma._")
    if r.get("resolvidos"):
        linhas.append("")
        linhas.append("## Fechadas no fechamento de lacunas (não contam)")
        linhas.append("")
        for x in r["resolvidos"]:
            fechado = x["trecho"].replace("|", "\\|")
            linhas.append(f"- `{x['d0']}` fecha {fechado} ({x['documento']})")
    linhas.append("")
    envelope = {
        "agente": agente,
        "missao": missao or "",
        "rodada": 1,
        "status": "aprovado" if r["status"] == "aprovado" else ("apto_com_ressalvas" if r["status"] == "amarelo" else "bloqueado"),
        "veredito": {"aprovado": "verde", "amarelo": "amarelo", "bloqueado": "vermelho"}[r["status"]],
        "por_etapa": pe,
        "achados": [
            # o trecho inteiro: o corte em 120 caracteres partia a palavra («…EF15AR05 na gra») no cartão do PO, que
            # é onde esta pendência aparece (25/10/2026); a linha também sai inteira da varredura (`varrer_lacunas`)
            {"severidade": a["severidade"], "classe": a["tipo"], "codigo": a["etapa"], "agente_responsavel": _dono_roteavel(a), "documento": a["documento"], "resumo": a.get("contexto") or a["trecho"]}
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


def _legada_fixada_pelo_po(secao: str, briefing: str, one_pager_po: str) -> bool:
    """A seção legada está na linha «Seção do DS» do one-pager do PO, ou o briefing a fixa (`secao_ds: <seção>`)."""
    cab = re.search(r"Se[çc][ãa]o do DS\**\s*[:=]\s*\**\s*`?([a-z][\w:-]*)", (one_pager_po or "")[:6000], re.IGNORECASE)
    if cab and cab.group(1).lower() == secao:
        return True
    return bool(re.search(rf"secao_ds\W{{0,4}}{re.escape(secao)}\b", briefing or "", re.IGNORECASE))


def validar_manifesto(spec: str, briefing: str = "", one_pager_po: str = "", one_pager: str = "",
                      decisoes_do_po: Optional[List[Any]] = None) -> Dict[str, Any]:
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
    secoes = secoes_ds()
    if not v or not (v.lower() in secoes or re.match(r"^(nova|minijogo)\s*:\s*\S+", v, re.IGNORECASE)):
        # Desde o PR 8 (24/10/2026, decisão D8) a classe e o ambiente são decididos em produto: a spec que cala não é mais
        # do D9, que não cria ambiente — ele devolve a produto. Até aqui a mensagem dava o dono ao design.
        falta("secao_ds", f"`secao_ds` ausente ou fora de {sorted(secoes)} / `nova:<nome>` / `minijogo:<nome>` (lido: {v!r}). Dono: produto — a classe (app clonado | mini-jogo) e o ambiente são decididos em produto (`ambiente-e-minijogo.md`), e o D9 não os decide.")
    elif v.lower() in SECOES_LEGADAS and _legada_fixada_pelo_po(v.lower(), briefing, one_pager_po):
        # O PO escolheu a legada — no one-pager que anexou ou no briefing. A decisão é dele (a mensagem sempre disse
        # isso, e o código bloqueava assim mesmo): a exp06ef1b, missão já publicada em `instanooria`, era empurrada
        # para `unoovista` contra o one-pager aprovado (08/10/2026). Fica visível, não trava.
        sucessora = SUCESSORA_DA_LEGADA.get(v.lower())
        achados.append({"severidade": "atencao", "campo": "secao_ds", "etapa": "produto", "resumo": (
            f"`{v}` é seção legada, mantida por decisão do PO (está no one-pager que ele anexou ou no briefing)"
            + (f"; a sucessora é `{sucessora}`" if sucessora else "") + ".")})
    elif v.lower() in SECOES_LEGADAS:
        sucessora = SUCESSORA_DA_LEGADA.get(v.lower())
        achados.append({"severidade": "bloqueio", "campo": "secao_ds", "etapa": "produto", "resumo": (
            f"`{v}` é seção legada: missão nova não reproduz a identidade de app de terceiro (ADR-133 a 138)"
            + (f" e usa `{sucessora}`" if sucessora else "") + " — veja `ambientes.md`. Se o PO quer mesmo a legada, "
            "é decisão dele, registrada na spec antes de seguir.")})
    elif v.lower() in secoes and not secoes[v.lower()]:
        achados.append({"severidade": "atencao", "campo": "secao_ds", "etapa": "plataforma", "resumo": f"`{v}` existe no DS mas não tem ponte em `@edu/ui`; criar a ponte é pré-requisito de plataforma."})
    elif re.match(r"^nova\s*:", v, re.IGNORECASE) and colecao_que_ja_cobre(v.split(":", 1)[1], secoes):
        colecao = colecao_que_ja_cobre(v.split(":", 1)[1], secoes)
        ponte = secoes.get(colecao)
        achados.append({"severidade": "bloqueio", "campo": "secao_ds", "etapa": "produto", "resumo": (
            f"`{v}` cria uma seção que o DS já tem: a coleção `{colecao}`. Use `secao_ds: {colecao}` e os componentes "
            f"dela — seção nova vira componente local, que a plataforma não aceita."
            + ("" if ponte else f" A coleção ainda não tem ponte em `@edu/ui`: criar `@edu/ui/ds-{colecao}` é "
               f"pré-requisito de plataforma (PRD 🟡). O que faltar na coleção é pendência do DS, não componente local."))})
    elif re.match(r"^(nova|minijogo)\s*:", v, re.IGNORECASE):
        achados.append({"severidade": "atencao", "campo": "secao_ds", "etapa": "plataforma", "resumo": f"Seção de DS nova (`{v}`): componentes, responsável e prazo são pendência de plataforma."})
    trava = achado_secao_travada(v or "", briefing, "a spec", secoes)
    if trava:
        achados.append({"severidade": trava["severidade"], "campo": "secao_ds", "etapa": "produto", "resumo": trava["resumo"]})
    # PR 8 (decisão D8): a classe do ambiente coerente com a seção, o mini-jogo só no 1º–5º e com as regras e as fases na
    # spec, e o ambiente novo ou o mini-jogo como escolha do PO — nunca decidido em silêncio. A escolha do PO só quando a
    # seção nova não repete uma coleção do DS e o briefing não fixa outra com `secao_ds:` (aí o bloqueio é o de cima, mais
    # preciso; a trava lida pelo nome da interface só avisa, e a escolha continua cobrada): a regra é
    # `ambiente.escolha_a_conferir`, a mesma do de acordo e do D9
    from tools import ambiente as amb

    serie_do_manifesto = (series or [None])[0] if series else (id_decomposto or {}).get("serie")
    for a in amb.conferir_spec(spec or "", serie=serie_do_manifesto, briefing=briefing, one_pager=one_pager,
                               one_pager_po=one_pager_po, decisoes_do_po=decisoes_do_po):
        achados.append(a)
    campos["classe_ambiente"] = amb.classe_e_ambiente(spec or "")["classe"]
    # Várias seções do DS (15/10/2026): `secao_ds` é a principal; as extras, o mapa e as transições vêm do bloco 0 e
    # do bloco 14 — por isso a spec inteira, não só o bloco 0.
    from tools import secoes as sec

    campos["secoes_ds_extras"] = sec.extras(texto)
    serie = (series or [None])[0] if series else (id_decomposto or {}).get("serie")
    for a in sec.validar(texto + "\n\n" + (spec or ""), v or "", "a spec", briefing=briefing, serie=serie,
                         vocabulario=secoes):
        achados.append({k: a[k] for k in ("severidade", "campo", "etapa", "resumo")})

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
    r"pro[ií]b|vedad|nunca|jamais|evit[ae]|descartad|obsolet|legad|zero\s+|elimina|abol|"
    # "Ausência total de pistas de gabarito no bundle" e "atributos retidos no servidor" são
    # a spec CUMPRINDO a regra — e o detector de gabarito as lia como violação (23/09/2026).
    # `retid` sozinho é ambíguo — "retidos NO SERVIDOR" nega o cliente, "retidos EM
    # localStorage" o afirma. Só a forma com complemento entra.
    r"aus[êe]nci|retid[oa]s?\s+no servidor|isolad[oa]s?\s+no servidor|fora do (bundle|cliente)|"
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


#: Bloco JSON (o envelope que o próprio agente escreve) não é prosa: um handoff de 22/09/2026 foi
#: acusado de "propor WebSocket" pelo `"codigo": "websocket-mencao"` do próprio envelope.
_RE_BLOCO_JSON = re.compile(r"```json.*?```", re.DOTALL | re.IGNORECASE)


def _sem_json(texto: str) -> str:
    return _RE_BLOCO_JSON.sub(" ", texto or "")


def frases_afirmativas(texto: str, padrao: str) -> List[str]:
    """As linhas em que o termo aparece sem negação por perto — os candidatos que o juiz de achados
    julga. O regex é a rede larga (recall); decidir se a linha propõe ou cita para vedar é do juiz."""
    limpo, vistas = _sem_json(texto), []
    for m in re.finditer(padrao, limpo, re.IGNORECASE):
        linha = _linha_de(limpo, m.start()).strip()
        if linha and not _NEGACAO.search(linha) and linha not in vistas:
            vistas.append(linha)
    return vistas


#: `dados` como chave de objeto — o campo que o `track()` da api não tem.
RE_CAMPO_DADOS = r"[{,]\s*[`\"']?\bdados\b[`\"']?\s*:"


def _usado_afirmativamente(texto: str, padrao: str) -> bool:
    """O termo aparece propondo algo, e não numa frase que o proíbe."""
    return bool(frases_afirmativas(texto, padrao))


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
    # `dados` como CHAVE de objeto (`{ dados:` / `, dados:`) fora de `concluir()`: a SDK aceita
    # `concluir({ score, dados })` por contrato (packages/sdk/src/types.ts), e "…de dados:" é prosa.
    # O padrão antigo pegava qualquer "dados:" do documento e bloqueou um handoff certo (24/09/2026).
    if _usado_afirmativamente(texto, r"\|\s*`?dados`?\s*\|") or any(
            "concluir(" not in frase for frase in frases_afirmativas(texto, RE_CAMPO_DADOS)):
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
    # A spec declara `gabarito_servidor: sim` e o evidencia-check confere; mas quem descreve a
    # implementação é o handoff, e nada o lia: "o gabarito vai no bundle" passava aqui.
    if _usado_afirmativamente(texto, r"gabarito[^\n]{0,90}\b(no cliente|bundle|front-?end|navegador|localstorage)"):
        bloqueio("gabarito-no-cliente", "O handoff coloca o gabarito no cliente/bundle: gabarito no bundle é gabarito entregue ao estudante. Ele vive no servidor (PED-04).")

    # rota citada num módulo que a plataforma já tem precisa existir nela (tools/rotas_plataforma.py)
    from tools.rotas_plataforma import validar_rotas
    achados.extend(validar_rotas(texto))
    # o que o documento afirma da plataforma confere com o contrato da base (tools/conferir_prd_plataforma.py)
    from tools.conferir_prd_plataforma import validar_contrato
    achados.extend(validar_contrato(texto))

    status = "bloqueado" if any(a["severidade"] == "bloqueio" for a in achados) else ("amarelo" if achados else "aprovado")
    return {"status": status, "achados": achados, "tabelas_eventos": len(tabela_eventos)}


def relatorio_telemetria(resultado: Dict[str, Any], missao: str = "", rodada: int = 1) -> str:
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
        "agente": "telemetria-check", "missao": missao or "", "rodada": rodada,
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
#: A suíte de ponta a ponta percorre a jornada inteira: cobrir todos os RFs é a definição dela, não falta de
#: decomposição. Nas 13 execuções de dev de 25/09 a 23/10/2026 o `tarefa-nao-atomica` só acusou suíte E2E
#: («T-013 | Implementar suíte de testes de ponta a ponta (e2e Playwright) | RF-001..RF-013», exp02em1b).
#: A descrição é a suíte: começa por «suíte» ou «testes», com o verbo antes ou não («Implementar suíte de testes de
#: ponta a ponta», «Suíte E2E automatizada…»), e diz que é de ponta a ponta.
_RE_TAREFA_E_A_SUITE = re.compile(r"^[*_`\s]*(?:(?:escrever|construir|implementar|criar|montar|desenvolver)\s+"
                                  r"(?:a\s+|as\s+|os\s+|uma\s+)?)?(?:su[íi]te|testes?)\b", re.I)
_RE_E2E = re.compile(r"\be2e\b|ponta a ponta|end[- ]to[- ]end|playwright", re.I)
#: E não implementa também telas, módulo ou serviço: «Implementar todas as telas do aluno e testes e2e» não começa pela
#: suíte, e «Testes e2e e as telas do aluno» implementa as telas — continuam cobradas (revisão do PR #77, 24/10/2026).
_RE_IMPLEMENTA_TAMBEM = re.compile(
    r"(?:\b(?:implement\w*|constru\w*|cri(?:ar|a|e)|desenvolv\w*|e)\b|\+)\s+(?:\w+\s+){0,3}?"
    r"(?:telas?|m[óo]dulos?|servi[çc]os?|endpoints?|componentes?|rotas?|apis?)\b", re.I)


def _tarefa_e2e(linha: str) -> bool:
    """A descrição da tarefa (a célula logo depois do `T-NNN`) é a suíte E2E e nada mais. Só a descrição: a coluna de
    teste de uma tarefa de implementação também cita e2e, e essa continua sendo cobrada."""
    celulas = [c.strip() for c in linha.strip().strip("|").split("|")]
    i = next((k for k, c in enumerate(celulas) if re.search(r"\bT-\d{3}\b", c)), None)
    if i is None or i + 1 >= len(celulas):
        return False
    descricao = celulas[i + 1]
    m = _RE_TAREFA_E_A_SUITE.match(descricao)
    return bool(m and _RE_E2E.search(descricao) and not _RE_IMPLEMENTA_TAMBEM.search(descricao[m.end():]))


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


def validar_prd(prd: str, spec: str = "", banco: str = "", aprovado: str = "") -> Dict[str, Any]:
    """Confere se o PRD é coerente consigo mesmo (e, com `spec`, com ela) antes de ir para quem codifica.

    O gabarito já exige tudo isto em prosa — o que faltava era alguém conferir. Um PRD que
    declara dois prefixos de tabela, ou que deixa um requisito P0 sem teste, faz o agente de
    codificação escolher um caminho ao acaso; e a partir daí o resto do documento deixa de
    valer contra o que ele escreveu. São defeitos de consistência, não de conteúdo, e por
    isso dá para pegá-los em código.

    O anexo do one-pager aprovado fica de fora: é cópia literal do PO, não texto do redator — e o
    "ativar ou agendar" do §9 da exp01ef1b fazia o PRD ser acusado de agendamento (07/10/2026).
    """
    from tools.conteudo_aprovado import remover_anexo

    texto = remover_anexo(prd or "")
    achados: List[Dict[str, str]] = []
    if not texto.strip():
        return {"status": "bloqueado", "achados": [{
            "severidade": "bloqueio", "codigo": "prd-vazio", "etapa": "dev",
            "resumo": "O PRD chegou vazio. Sem documento não há consistência a conferir — e o "
                      "gate saía 🟡 por não encontrar defeito no que não existe.",
        }]}

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
            from tools.kpis import LEITOR_VALIDO, MENSAGEM_LEITOR
            if re.search(r"pub/?sub|telemetria_eventos", linha, re.I) and not re.search(LEITOR_VALIDO, linha, re.I):
                evt = re.search(r"\bEVT-\d+", linha)
                # O identificador do evento pode estar em qualquer coluna da linha, e a tabela é larga:
                # citar só o começo da linha escondia a evidência de quem vai corrigir.
                falha("evento-sem-leitor",
                      f"`{evt.group(0) if evt else 'evento'}` aponta Pub/Sub ou `telemetria_eventos` como leitor. "
                      f"{MENSAGEM_LEITOR} Linha: `{linha.strip()[:200]}`")

    # 4. tarefa não atômica
    for m in re.finditer(r"\b(T-\d{3})\b[^\n]*?(todos os RFs?|todas as RFs?|todos os requisitos)", texto, re.I):
        if _tarefa_e2e(texto[texto.rfind("\n", 0, m.start()) + 1:m.end()]):
            continue
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
        if not tarefa or "|" not in linha or _tarefa_e2e(linha):
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
    caminhos -= experiencias_existentes()
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

    # 8. o modelo de dados contra ele mesmo e contra a spec (`tools/consistencia.py`). Na exp09ef1b o
    # bloco 9 da spec declarava `escola_id UUID` e o PRD `escola_id TEXT`; a tabela de eventos citava
    # `exp09ef1b_sessoes.projeto_homologado`, que nenhum DDL declara. Quem codifica escolheria ao acaso.
    from tools.consistencia import conferir_colunas, validar as validar_glossario
    achados.extend(conferir_colunas(texto, referencia=spec))
    # 9. os nomes do PRD contra o glossário canônico da spec — o PRD é o último a escrever o nome do órgão
    if spec:
        achados.extend(validar_glossario(spec, {"PRD": texto}, exigir_glossario=False, etapa="dev",
                                         aprovado=aprovado)["achados"])
    # 10. tarefa que consome conteúdo que ninguém escreveu (`tools/conteudo.py`). Sem banco, não se acusa.
    from tools.conteudo import tarefas_sem_conteudo
    achados.extend(tarefas_sem_conteudo(texto, banco))

    # rota citada num módulo que a plataforma já tem precisa existir nela (tools/rotas_plataforma.py)
    from tools.rotas_plataforma import validar_rotas
    achados.extend(validar_rotas(texto))
    # o que o documento afirma da plataforma confere com o contrato da base (tools/conferir_prd_plataforma.py)
    from tools.conferir_prd_plataforma import validar_contrato
    achados.extend(validar_contrato(texto))

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
