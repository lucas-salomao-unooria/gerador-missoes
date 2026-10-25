"""Memória das missões já geradas — índice persistente, ficha por execução e vizinhas.

**Por que existe.** A esteira não se lembrava do que já tinha gerado. O catálogo oficial
(`references/catalogo-missoes.md`) é escrito à mão e ninguém o aplica; as sessões em `output/`
contêm toda missão já produzida e nada as lia entre execuções. O resultado é que duas missões
parecidas só eram percebidas por uma pessoa, ou nunca — e o agente que **inventa** a missão nunca
via o catálogo: o primeiro a consultá-lo rodava três agentes depois, com o one-pager inteiro escrito.

**Onde o dado vive.** `output/_catalogo.json`. É o único caminho que persiste: `/app/output` é o
bucket montado no Cloud Run, enquanto `prompts/` vem da imagem e some a cada revisão. A instância é
única (`--max-instances=1`), então não há concorrência; ainda assim a gravação é atômica.

**As sessões são a memória; este índice é cache.** `scripts/catalogo.py reconstruir` o refaz do zero
varrendo `output/*/estado.json`. Perder o índice não perde nada.

**Semelhança sem embeddings, de propósito.** A recuperação é mecânica (ano, ambiente, eixo, e
sobreposição de palavras da descoberta); o *julgamento* fica com o micro-gate, que já tem o teste de
2 frases escrito. Com ~10 missões hoje e ~200 no limite (12 anos × 4 bimestres), embeddings seriam
infraestrutura sem ganho. Revisar esta decisão se o índice passar de 200 missões.
"""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

AGENTE = "registro-catalogo"
VERSAO_INDICE = 1
NOME_INDICE = "_catalogo.json"

#: Vocabulário de status do catálogo. A esteira só escreve os dois primeiros — os demais são ato
#: humano (`scripts/catalogo.py promover`), porque são juízo, e o registro automático é fato.
STATUS_AUTOMATICOS = ("em criação", "bloqueada")
STATUS_HUMANOS = ("validada", "aprovada", "em produção", "descartada")

#: Seções do design system que nomeiam o ambiente simulado (`references/ambientes.md`).
AMBIENTES = ("instanooria", "unootube", "chatgpt", "whatsappmobile", "tiktooria", "mini-jogo")
#: Nome antigo → nome do DS. Fichas e specs antigas dizem `unitube`; comparar sem normalizar
#: separava duas missões do mesmo ambiente.
APELIDOS_DE_AMBIENTE = {"unitube": "unootube"}
#: Escala de abstração de `literatura-cognitiva.md` §4, usada pelo critério 2.8.
PORTAS = ("descrever", "explicar", "criticar com apoio", "criticar")

#: Acima disto, duas missões são parecidas o bastante para o registro avisar. Não bloqueia nada:
#: quem reprova é o micro-gate (V5), por julgamento, não por número.
LIMIAR_PARECIDA = 0.60

_RE_SLUG_ANO = re.compile(r"^exp(\d{2})(ef|em)(\d)b$", re.IGNORECASE)
_RE_LINHA_TABELA = re.compile(r"^\|(?!\s*[-:]+\s*\|).+\|\s*$")
_STOPWORDS = {
    "para", "pelo", "pela", "pelos", "pelas", "como", "mais", "menos", "muito", "sobre", "entre",
    "quando", "onde", "porque", "cada", "todo", "toda", "todos", "todas", "isso", "esse", "essa",
    "aquilo", "seu", "sua", "seus", "suas", "que", "com", "sem", "dos", "das", "nos", "nas", "uma",
    "ele", "ela", "eles", "elas", "voce", "voces", "estudante", "aluno", "alunos", "missao", "app",
    "nao", "sim", "ser", "ter", "fazer", "faz", "tem", "vai", "esta", "estao", "foi", "sao",
}


# --------------------------------------------------------------------- caminho e carga
def caminho_indice(base: Optional[Path] = None) -> Path:
    """`output/_catalogo.json`. `base` só existe para teste — em produção vem do settings."""
    if base is not None:
        return Path(base) / NOME_INDICE
    from config import get_settings  # import tardio: `OUTPUT_DIR` muda em tempo de execução

    return get_settings().output_path / NOME_INDICE


def indice_vazio() -> Dict[str, Any]:
    return {"versao": VERSAO_INDICE, "gerado_em": "", "missoes": []}


def carregar(base: Optional[Path] = None) -> Dict[str, Any]:
    """Lê o índice. Ausente, ilegível ou de versão futura devolve vazio — nunca levanta."""
    caminho = caminho_indice(base)
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        if not isinstance(dados, dict) or int(dados.get("versao", 0)) > VERSAO_INDICE:
            return indice_vazio()
        dados.setdefault("missoes", [])
        return dados
    except Exception:
        return indice_vazio()


def gravar(indice: Dict[str, Any], base: Optional[Path] = None) -> Path:
    """Gravação atômica (`.tmp` + `os.replace`), como os tokens do Miro."""
    caminho = caminho_indice(base)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    indice["versao"] = VERSAO_INDICE
    indice["gerado_em"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    tmp = caminho.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(indice, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, caminho)
    return caminho


# --------------------------------------------------------------------- extração da ficha
def _limpar(valor: str) -> str:
    v = re.sub(r"\s+", " ", (valor or "")).strip()
    v = re.sub(r"^[*_`]+|[*_`]+$", "", v).strip()
    return v


def _primeira_frase(bloco: str, maximo: int = 220) -> str:
    """Primeira linha de conteúdo de um bloco, sem heading, bullet ou rótulo em negrito."""
    for linha in (bloco or "").splitlines():
        t = _limpar(re.sub(r"^\s*[-*>]+\s+", "", linha))
        if not t or t.startswith("#") or t.startswith("|"):
            continue
        # Rótulo em negrito à frente do valor: `**Frase-síntese da descoberta:** "…"`.
        t = re.sub(r"^\*{0,2}[^:*]{3,60}:\*{0,2}\s*", "", t).strip()
        t = _limpar(t.strip('"“”'))
        if len(t) < 12:
            continue
        return t[:maximo]
    return ""


def _campo_rotulado(texto: str, *rotulos: str) -> str:
    """Valor de `**Rótulo:** valor` ou `Rótulo: valor`, no primeiro rótulo que casar."""
    for rotulo in rotulos:
        m = re.search(rf"\*?\*?{re.escape(rotulo)}\*?\*?\s*[:—-]\s*(.+)", texto or "", re.IGNORECASE)
        if m:
            valor = _limpar(m.group(1).split("·")[0]).lstrip("*").strip().strip('"“”')
            if valor and not valor.startswith("<"):
                return valor[:220]
    return ""


def _ano_bimestre(slug: str, textos: str) -> Tuple[str, Optional[int]]:
    """Do slug (`exp06ef1b` → 6EF, 1). Sem slug legível, cai na série declarada no texto."""
    m = _RE_SLUG_ANO.match(slug or "")
    if m:
        return f"{int(m.group(1))}{m.group(2).upper()}", int(m.group(3))
    from tools.bncc import extrair_serie

    serie = extrair_serie(textos or "")
    if serie["anos"]:
        return f"{min(serie['anos'])}EF", None
    return ("EM", None) if serie["em"] else ("", None)


def _ambiente(textos: str) -> str:
    baixo = (textos or "").lower()
    for amb in (*AMBIENTES, *APELIDOS_DE_AMBIENTE):
        if amb in baixo:
            return _canonico(amb)
    return ""


def _canonico(ambiente: str) -> str:
    """O nome do DS para o ambiente: `unitube` (nome antigo na esteira) é `unootube`."""
    valor = (ambiente or "").strip().lower()
    return APELIDOS_DE_AMBIENTE.get(valor, valor)


def _habilidade_primaria(spec: str, nucleo: str) -> str:
    """Primeiro código de Cultura Digital do bloco 11 — o foco primário da Regra 12."""
    from tools.bncc import extrair_codigos, habilidades, secao_bloco

    for texto, bloco in ((spec, 11), (nucleo, 1)):
        if not texto:
            continue
        alvo = secao_bloco(texto, bloco) or texto
        for codigo in extrair_codigos(alvo):
            hab = habilidades().get(codigo)
            if hab and (hab.get("eixo") == "CD" or hab.get("letramento_digital")):
                return codigo
        codigos = extrair_codigos(alvo)
        if codigos:
            return codigos[0]
    return ""


#: Cabeçalho normalizado → campo da ficha. A ordem das colunas NÃO importa, e é esse o ponto.
_COLUNAS_CATALOGO = (
    ("tipo de decis", "tipo_decisao"), ("descoberta", "descoberta"), ("habilidade", "habilidade_primaria"),
    ("porta", "porta_abstracao"), ("ambiente", "ambiente"), ("eixo", "eixo"), ("slug", "slug"),
    ("bim", "bimestre"), ("nome", "nome"), ("status", "status"), ("ano", "ano"),
)


def _norm_cab(celula: str) -> str:
    sem = "".join(c for c in unicodedata.normalize("NFD", celula.lower()) if unicodedata.category(c) != "Mn")
    return sem.strip(" `*_")


#: O cabeçalho literal da linha de catálogo que o prompt 128 fixa, nas 11 colunas. O agente às vezes escreve só a linha de
#: dados, num bloco ```markdown e sem cabeçalho: na 53e011b6 (exp06ef1b, 08/10/2026) a linha
#: «| exp06ef1b | 6º EF | … | EF06CO10 | em produção |» não era lida, e o «em produção» passava sem troca.
CABECALHO_DA_LINHA_PROPOSTA = ("Slug", "Ano", "Bim", "Nome", "Ambiente", "Eixo temático", "Descoberta central (aha)",
                               "Tipo de decisão", "Porta de abstração", "Habilidade primária", "Status")


def cabecalho_fixo_da_linha(celulas: List[str], slug: str) -> Optional[List[str]]:
    """O cabeçalho fixo (normalizado) para uma linha de tabela sem cabeçalho, quando ela é a linha de catálogo desta missão:
    a primeira célula é o slug, literalmente, e são as 11 colunas do prompt. Fora disso, None."""
    if not slug or len(celulas) != len(CABECALHO_DA_LINHA_PROPOSTA):
        return None
    if _norm_cab(_limpar(celulas[0])) != _norm_cab(slug):
        return None
    return [_norm_cab(c) for c in CABECALHO_DA_LINHA_PROPOSTA]


def _linha_do_aprendizado(aprendizado: str, slug: str = "") -> Dict[str, str]:
    """Campos de julgamento da linha que o agente 51 propõe no formato do catálogo.

    Lida pelo NOME da coluna. A versão anterior lia por posição, com o slug na primeira: o prompt
    pede `|Slug|Ano|…|` e o modelo escreve `|Ano|Bim|Nome|…|` — o formato antigo de
    `catalogo-missoes.md`. A linha era descartada em todas as execuções, a ficha caía no núcleo,
    e o núcleo não tem rótulo de tipo de decisão: 13 das 14 fichas reconstruídas em 23/09/2026
    saíam com `tipo_decisao` vazio, o V5 as ignorava, e o registro automático repetia o defeito
    a cada missão nova. Campo `[preencher…]` volta vazio, para a extração do núcleo tentar.

    Sem cabeçalho, a linha cuja primeira célula é o `slug` da missão e que tem as 11 colunas do prompt é lida pelo
    cabeçalho fixo (`cabecalho_fixo_da_linha`).
    """
    cabecalho: Optional[List[str]] = None
    for bruta in (aprendizado or "").splitlines():
        linha = bruta.strip()
        # Pela forma, e não por `_RE_LINHA_TABELA`: aquele regex exclui a linha separadora de
        # propósito, e tratar "não casou" como "a tabela acabou" zerava o cabeçalho justo antes
        # da linha de dados.
        if not (linha.startswith("|") and linha.endswith("|") and len(linha) > 2):
            cabecalho = None
            continue
        if set(linha) <= set("|-: "):
            continue
        celulas = [_limpar(c) for c in linha.strip("|").split("|")]
        normal = [_norm_cab(c) for c in celulas]
        if any("descoberta" in c for c in normal) and any("tipo de decis" in c for c in normal):
            cabecalho = normal
            continue
        colunas = cabecalho if cabecalho is not None else cabecalho_fixo_da_linha(celulas, slug)
        if colunas is None:
            continue
        ficha: Dict[str, str] = {}
        for i, nome_col in enumerate(colunas):
            if i >= len(celulas):
                break
            campo = next((c for chave, c in _COLUNAS_CATALOGO if chave in nome_col), None)
            valor = celulas[i].strip()
            if campo and campo not in ficha and valor and "preencher" not in valor.lower():
                ficha[campo] = valor
        if ficha.get("descoberta") or ficha.get("tipo_decisao"):
            return ficha
    return {}


_RE_SECAO_DS = re.compile(r"secao_ds[`*_]*\s*:\s*[`*_]*\s*([a-z0-9:_\-]+)", re.IGNORECASE)


def _ambiente_da_spec(bloco0: str) -> str:
    """O ambiente pelo campo `secao_ds` do bloco 0 — vocabulário fechado, conferido por gate.

    Ambiente novo é `nova:<nome>` e fica assim: vazio, ele fazia a ficha sair cega em todas as
    missões com seção de DS nova (5 das 14 em 23/09/2026), embora a spec dissesse qual era.
    """
    m = _RE_SECAO_DS.search(bloco0 or "")
    if not m:
        return ""
    valor = m.group(1).lower().strip("`")
    # Também as coleções do DS que a esteira já conhece e a base ainda não publica (`unoogaleria`, `unoojornal`,
    # `unooblog`): as tentativas da exp03ef1b em `unoogaleria` saíam com o ambiente em branco (08/10/2026).
    from tools.rastro import RADICAIS_DA_COLECAO

    conhecida = valor in _secoes_validas() or valor in RADICAIS_DA_COLECAO or valor.startswith("nova:")
    return _canonico(valor) if conhecida else ""


def _secoes_validas() -> set:
    """As seções do DS que existem hoje (contrato da base) mais os ambientes legados.

    A lista fixa `AMBIENTES` não conhecia `unooriaai`, `unoovista` nem `unoochat`: a ficha de uma
    missão nova numa dessas seções saía com o ambiente em branco.
    """
    from prompts import base_plataforma

    try:
        secoes = {str(s.get("secao") or "").lower() for s in
                  (base_plataforma.contrato().get("design_system") or {}).get("secoes") or []}
    except base_plataforma.BaseIndisponivel:
        secoes = set()
    return set(AMBIENTES) | set(APELIDOS_DE_AMBIENTE) | {s for s in secoes if s}


def _nome(textos: str) -> str:
    m = re.search(r"^#\s*(?:N[úu]cleo narrativo|Spec|One-?pager)\s*[—–-]\s*(.+?)(?:\s+v\d|\s*$)", textos or "", re.MULTILINE | re.IGNORECASE)
    if m:
        return _limpar(m.group(1))[:120]
    m = re.search(r"^#\s+(.+)$", textos or "", re.MULTILINE)
    return _limpar(m.group(1))[:120] if m else ""


def _porta(valor: str) -> str:
    """Só a palavra da escala de §4. O agente costuma escrever a justificativa junto, e a coluna
    do catálogo é comparada por igualdade — texto livre ali não compara com nada."""
    baixo = (valor or "").lower()
    for porta in sorted(PORTAS, key=len, reverse=True):  # "criticar com apoio" antes de "criticar"
        if porta in baixo:
            return porta
    return ""


def ficha_da_execucao(state: Dict[str, Any], sessao: str = "") -> Dict[str, Any]:
    """A ficha de catálogo desta execução, extraída do estado. Campo ausente sai vazio, nunca inventado."""
    from agents.callbacks import extrair_slug
    from tools import governanca
    from tools.bncc import secao_bloco

    spec = str(state.get("spec_missao") or "")
    nucleo = str(state.get("nucleo_narrativo") or "")
    one_pager = str(state.get("one_pager") or "")
    aprendizado = str(state.get("aprendizado_registro") or "")
    juntos = "\n".join(t for t in (spec, nucleo, one_pager) if t)

    slug = extrair_slug(spec) or extrair_slug(nucleo) or extrair_slug(one_pager)
    proposta = _linha_do_aprendizado(aprendizado, slug)
    bloco1 = secao_bloco(nucleo, 1) or secao_bloco(spec, 1) or secao_bloco(one_pager, 1) or ""
    bloco0 = secao_bloco(spec, 0) or secao_bloco(nucleo, 0) or ""

    ano, bimestre = _ano_bimestre(slug, bloco0 or juntos[:3000])
    gates = {
        chave.removesuffix("_status"): str(state.get(chave) or "")
        for chave in ("gate_estrutural_status", "gate_final_status", "bncc_status", "design_status", "dev_status")
        if state.get(chave)
    }
    # O status segue o parecer humano em vigor (`tools/liberacao.py`): reprovação que uma pessoa viu e liberou não bloqueia
    # a missão. A exp04ef1b (8ce9c32d, 25/09/2026) foi registrada `bloqueada` depois do «De acordo para codificação», e a
    # exp02em1b (60cfa7f4, 22/10/2026) depois da exceção do admin no design e do de acordo de dev. Promover continua ato
    # humano: com o parecer, a ficha sai `em criação` e diz qual é o parecer em vigor.
    from tools import liberacao

    pareceres = [p for p in state.get("pareceres_humanos") or [] if isinstance(p, dict)]
    bloqueada = liberacao.bloqueada(state, pareceres)

    return {
        "sessao": sessao,
        "slug": slug,
        "nome": proposta.get("nome") or _nome(nucleo or spec or one_pager),
        "ano": proposta.get("ano") or ano,
        "bimestre": bimestre,
        # A spec primeiro: `secao_ds` é vocabulário fechado. A linha do aprendizado traz o nome de
        # vitrine ("InstaNooria (Instagram)") e só serve canonizada.
        "ambiente": (_ambiente_da_spec(bloco0) or _ambiente(proposta.get("ambiente", ""))
                     or _ambiente(bloco0) or _ambiente(juntos[:6000])).lower(),
        # as outras seções do DS da missão (15/10/2026): entram na comparação de ambiente
        "ambientes_extras": _extras(bloco0 or one_pager),
        "eixo": proposta.get("eixo") or _campo_rotulado(bloco1, "Eixo temático", "Eixo"),
        "descoberta": proposta.get("descoberta") or _campo_rotulado(bloco1, "Descoberta central") or _primeira_frase(bloco1),
        "tipo_decisao": proposta.get("tipo_decisao") or _campo_rotulado(bloco1, "Tipo de decisão"),
        "porta_abstracao": _porta(proposta.get("porta_abstracao") or _campo_rotulado(bloco1, "Porta de abstração")),
        "habilidade_primaria": proposta.get("habilidade_primaria") or _habilidade_primaria(spec, nucleo),
        "status": "bloqueada" if bloqueada else "em criação",
        "gates": gates,
        # «🟡 liberado sem a conta produto — design (como Produto), <data>», ou vazio (PR 9 do plano «Produto dono do
        # contrato», D9): o catálogo diz quem liberou produto, sem mudar o status — é governança, não veredito
        "liberacao_produto": governanca.marca(governanca.da_sessao(state)),
        # o parecer em vigor da etapa mais adiantada («dev: de acordo — dev, 25/09/2026 16:14:33»), ou vazio sem parecer
        "parecer_humano": liberacao.parecer_em_vigor(pareceres),
        "gerada_em": time.strftime("%Y-%m-%d"),
        "origem": "esteira",
        # Achados dos pareceres pedagógicos, com o slug de padrão, para `recorrencias()`
        # perceber o que volta. Sem isto cada execução redescobria o mesmo defeito com um id
        # novo: 40 achados de conteúdo em 14 execuções, nenhum fechado.
        "achados_pedagogicos": [
            {"padrao": a["padrao"], "resumo": str(a.get("resumo") or "")[:200]}
            for chave in ("adequacao_status_envelope", "avaliacao_status_envelope", "experiencia_status_envelope")
            for a in ((state.get(chave) or {}).get("achados") or [])
            if isinstance(a, dict) and a.get("padrao")
        ],
    }


# --------------------------------------------------------------------- semelhança
def _tokens(texto: str) -> Set[str]:
    sem_acento = "".join(c for c in unicodedata.normalize("NFD", (texto or "").lower()) if unicodedata.category(c) != "Mn")
    return {t for t in re.findall(r"[a-z0-9]{4,}", sem_acento) if t not in _STOPWORDS}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# --------------------------------------------------------------------- missões publicadas na plataforma
#: Origem das fichas que vêm da grade publicada (`apps/hub/lib/entre-redes/catalogo.ts`), não de uma sessão.
ORIGEM_PLATAFORMA = "plataforma"
_RE_CONSTANTE = re.compile(r"^export const (MISSAO_\w+): Missao = \{(.*?)^\};", re.S | re.M)


def _campo_ts(bloco: str, nome: str) -> str:
    """O valor de `nome: "…"` (string simples ou concatenada em várias linhas) no primeiro nível em que aparece."""
    m = re.search(rf"\b{nome}:\s*((?:\"(?:[^\"\\]|\\.)*\"\s*\+?\s*)+)", bloco)
    if not m:
        return ""
    return "".join(re.findall(r"\"((?:[^\"\\]|\\.)*)\"", m.group(1))).replace('\\"', '"').strip()


def _ano_da_plataforma(ano_slug: str) -> str:
    m = re.match(r"(\d+)-(ano|serie)", ano_slug or "")
    if not m:
        return ""
    return f"{m.group(1)}º EF" if m.group(2) == "ano" else f"{m.group(1)}ª EM"


def fichas_da_plataforma(catalogo_ts: str) -> List[Dict[str, Any]]:
    """Uma ficha por missão publicada (`MISSOES_PUBLICADAS` do catálogo do hub), com status «em produção».

    O índice só conhecia o que o gerador produziu: as missões que estão na grade da plataforma e nasceram fora dele
    (o Unoovista do 8º ano, a UnooGPT, o Rastro do Boato, o Manifesto IA) não entravam na verificação de semelhança
    (V5), e uma missão nova podia repetir uma que a escola já usa. Ambiente, eixo e descoberta saem do que a grade
    mostra — o app que o estudante vê, a competência e o resumo —; o resto fica vazio, nunca inventado.
    """
    texto = catalogo_ts or ""
    publicadas_bloco = re.search(r"const MISSOES_PUBLICADAS[^=]*=\s*\{(.*?)^\};", texto, re.S | re.M)
    publicadas = set(re.findall(r"\b(MISSAO_\w+)\b", publicadas_bloco.group(1))) if publicadas_bloco else set()
    fichas: List[Dict[str, Any]] = []
    for m in _RE_CONSTANTE.finditer(texto):
        nome, bloco = m.group(1), m.group(2)
        if nome not in publicadas:
            continue
        exp_id = _campo_ts(bloco, "expId")
        estudante = re.search(r"\bestudante:\s*\{(.*?)\}", bloco, re.S)
        ficha_bloco = re.search(r"\bficha:\s*\{(.*)", bloco, re.S)
        unidade = re.search(r"\bunidade:\s*(\d+)", bloco)
        fichas.append({
            "sessao": f"{ORIGEM_PLATAFORMA}:{exp_id}",
            "slug": exp_id,
            "nome": _campo_ts(bloco, "titulo"),
            "ano": _ano_da_plataforma(_campo_ts(bloco, "anoSlug")),
            "bimestre": f"{unidade.group(1)}º bimestre" if unidade else "",
            # o título que o estudante vê só vale quando é o nome de uma seção do DS; senão, vem do código da
            # experiência (`ambiente_da_fonte`, preenchido por quem importa)
            "ambiente": _MARCAS_DO_DS.get(_campo_ts(estudante.group(1), "titulo").lower(), "") if estudante else "",
            "eixo": _campo_ts(ficha_bloco.group(1), "competencia") if ficha_bloco else "",
            "descoberta": _campo_ts(bloco, "resumo"),
            # o que o estudante faz, como a grade o chama para a missão — é a frase que o teste de 2 frases do V5 compara;
            # vazio, a ficha "não sustenta reprovação" e a missão publicada não protegia nada (08/10/2026)
            "tipo_decisao": _campo_ts(estudante.group(1), "chamada") if estudante else "",
            "porta_abstracao": "",
            "habilidade_primaria": "",
            "status": "em produção",
            "origem": ORIGEM_PLATAFORMA,
            "gerada_em": time.strftime("%Y-%m-%d"),
        })
    return fichas


#: Marcas do DS que um import ou uma classe da experiência pode nomear, e a seção que cada uma é.
_MARCAS_DO_DS = {"unoovista": "unoovista", "unoochat": "unoochat", "unooriaai": "unooriaai", "tiktooria": "tiktooria",
                 "unoogaleria": "unoogaleria", "unoojornal": "unoojornal", "unooblog": "unooblog", "unooria": "unooria",
                 "instanooria": "instanooria", "insta": "instanooria", "chatgpt": "chatgpt",
                 "whatsappmobile": "whatsappmobile", "unootube": "unootube", "unitube": "unitube"}


def ambiente_da_fonte(fonte: str) -> str:
    """A seção do DS que o código da experiência usa: a marca mais importada (`@unooria/design-system/<marca>`,
    `@edu/ui/<marca>`) ou nomeada em classe (`ds-<marca>`). O manifesto da experiência não traz a seção, e o título
    que o estudante vê às vezes é o nome da missão, não o app. Sem marca reconhecida, vazio."""
    contagem: Dict[str, int] = {}
    for m in re.finditer(r"(?:@unooria/design-system/|@edu/ui/|\bds-)([a-z]+)\b", fonte or ""):
        secao = _MARCAS_DO_DS.get(m.group(1))
        if secao:
            contagem[secao] = contagem.get(secao, 0) + 1
    return max(contagem, key=lambda s: (contagem[s], s != "unooria")) if contagem else ""


def _ano_num(ano: str) -> Optional[int]:
    m = re.match(r"(\d)\s*EF", (ano or "").upper())
    return int(m.group(1)) if m else None


def _extras(texto: str) -> List[str]:
    from tools.secoes import SECAO_DA_PLATAFORMA, extras

    return [s for s in extras(texto) if s != SECAO_DA_PLATAFORMA]


def _ambientes(ficha: Dict[str, Any]) -> set:
    """Todas as seções do DS da missão, canonizadas: a principal e as extras."""
    todas = [ficha.get("ambiente") or "", *(ficha.get("ambientes_extras") or [])]
    return {_canonico(a) for a in todas if a}


def mesmo_ambiente(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """Alguma seção em comum — com várias seções, uma missão de `unoovista` + `unoochat` é vizinha das duas."""
    return bool(_ambientes(a) & _ambientes(b))


def semelhanca(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    """0 a 1 — as quatro dimensões que os critérios 2.5 e 2.8 comparam.

    **O score recupera e ordena; não decide.** Ele é lexical: duas missões que dizem a mesma coisa
    com outras palavras ("segui uma conta e o feed afunilou" × "minhas escolhas escondem posts")
    pontuam médio, não alto. Quem reprova é o micro-gate (V5), que aplica o teste de 2 frases sobre
    as vizinhas que este score trouxe. Por isso o limiar abaixo serve a um aviso, nunca a um veto.
    """
    score = 0.35 * _jaccard(_tokens(a.get("descoberta", "")), _tokens(b.get("descoberta", "")))
    if mesmo_ambiente(a, b):
        score += 0.25
    if a.get("eixo") and _jaccard(_tokens(a.get("eixo", "")), _tokens(b.get("eixo", ""))) >= 0.5:
        score += 0.20
    if a.get("ano") and _ano_num(a.get("ano", "")) is not None and _ano_num(a.get("ano", "")) == _ano_num(b.get("ano", "")):
        score += 0.10  # mesmo ano é onde a repetição mais dói: é a trilha que o estudante vive
    score += 0.10 * _jaccard(_tokens(a.get("tipo_decisao", "")), _tokens(b.get("tipo_decisao", "")))
    return round(min(score, 1.0), 3)


def vizinhas(ficha: Dict[str, Any], indice: Optional[Dict[str, Any]] = None, n: int = 5, base: Optional[Path] = None) -> List[Dict[str, Any]]:
    """As missões do índice mais próximas desta, já ordenadas. Exclui a própria sessão.

    Filtro: mesmo ano (ou vizinho), mesmo ambiente ou mesmo eixo. Missão descartada fica de fora.
    """
    indice = indice if indice is not None else carregar(base)
    ano_alvo = _ano_num(ficha.get("ano", ""))
    candidatas: List[Dict[str, Any]] = []
    for m in indice.get("missoes", []):
        if m.get("sessao") and m.get("sessao") == ficha.get("sessao"):
            continue
        # Outra versão da MESMA missão não é repetição: o id da plataforma é ano + bimestre, então mesmo slug é a
        # mesma vaga — a versão nova substitui a anterior (ou a publicada). Sem isto, regerar a exp06ef1b a
        # comparava com a exp06ef1b publicada e com cada tentativa anterior (08/10/2026).
        if ficha.get("slug") and str(m.get("slug") or "").lower() == str(ficha["slug"]).lower():
            continue
        # A própria missão, quando já está no índice (reexecução da mesma sessão): a esteira rodando
        # de novo não pode ver a si mesma como repetição.
        if ficha.get("descoberta") and m.get("descoberta") == ficha.get("descoberta"):
            continue
        if str(m.get("status", "")).lower() == "descartada":
            continue
        ano_m = _ano_num(m.get("ano", ""))
        perto = ano_alvo is not None and ano_m is not None and abs(ano_alvo - ano_m) <= 1
        ambiente_comum = mesmo_ambiente(ficha, m)
        mesmo_eixo = bool(ficha.get("eixo")) and _jaccard(_tokens(ficha.get("eixo", "")), _tokens(m.get("eixo", ""))) >= 0.5
        if not (perto or ambiente_comum or mesmo_eixo):
            continue
        candidatas.append({**m, "semelhanca": semelhanca(ficha, m)})
    candidatas.sort(key=lambda m: (-m["semelhanca"], m.get("slug", "")))
    return candidatas[:n]


def _rotulo_semelhanca(score: float) -> str:
    return "alta" if score >= LIMIAR_PARECIDA else ("média" if score >= 0.35 else "baixa")


def _celula(valor: Any) -> str:
    texto = _limpar(str(valor if valor not in (None, "") else "—")).replace("|", "/")
    return texto[:160]


def tabela_markdown(missoes: List[Dict[str, Any]], com_semelhanca: bool = False) -> str:
    """As colunas que os critérios 2.5 e 2.8 comparam. Vazio devolve o aviso, nunca tabela oca."""
    if not missoes:
        return "_Nenhuma missão registrada ainda — o índice está vazio, e nenhuma comparação é possível._"
    cabecalho = ["Slug", "Ano", "Ambiente", "Eixo", "Descoberta central", "Tipo de decisão", "Porta", "Status"]
    if com_semelhanca:
        cabecalho.append("Semelhança")
    linhas = ["| " + " | ".join(cabecalho) + " |", "|" + "---|" * len(cabecalho)]
    for m in missoes:
        celulas = [m.get("slug"), m.get("ano"), m.get("ambiente"), m.get("eixo"), m.get("descoberta"),
                   m.get("tipo_decisao"), m.get("porta_abstracao"), m.get("status")]
        if com_semelhanca:
            celulas.append(f"{_rotulo_semelhanca(m.get('semelhanca', 0.0))} ({m.get('semelhanca', 0.0):.2f})")
        linhas.append("| " + " | ".join(_celula(c) for c in celulas) + " |")
    return "\n".join(linhas)


def tem_lacuna(missao: Dict[str, Any]) -> bool:
    """Linha que não sustenta reprovação em V5: campo de comparação vazio ou por preencher."""
    for campo in ("descoberta", "tipo_decisao", "ambiente"):
        valor = str(missao.get(campo) or "")
        if not valor or valor == "—" or "preencher" in valor.lower():
            return True
    return False


# --------------------------------------------------------------------- registro
def colisao_de_slug(ficha: Dict[str, Any], missoes: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, str]]:
    """O achado de slug colidido, se houver. É decisão de produto, então é `decisao_humana`.

    Até 06/10/2026 nascia `atencao` com `precisa_humano: false` fixo no envelope, e o registro no
    catálogo roda depois do diagnóstico: a colisão da missão do 9º ano nunca chegou ao dossiê. O
    diagnóstico agora chama esta função antes de fechar.
    """
    if missoes is None:
        missoes = carregar().get("missoes", [])
    for m in missoes:
        # Mesma descoberta = mesma missão registrada de novo (reexecução), não colisão. O agente
        # que roda dentro da esteira ainda não sabe o nome da pasta, então a sessão não basta.
        mesma_missao = bool(ficha.get("descoberta")) and m.get("descoberta") == ficha.get("descoberta")
        if m.get("slug") and m.get("slug") == ficha.get("slug") and m.get("sessao") != ficha.get("sessao") \
                and not mesma_missao and str(m.get("status", "")).lower() != "descartada":
            return [{"severidade": "decisao_humana", "codigo": "slug-colidido",
                     "resumo": f"O slug `{ficha['slug']}` já é da sessão `{m.get('sessao')}` — o id da plataforma deriva de ano e bimestre, então duas missões do mesmo bimestre colidem. Decisão de produto."}]
    return []


def registrar(ficha: Dict[str, Any], indice: Optional[Dict[str, Any]] = None, base: Optional[Path] = None, gravar_arquivo: bool = True) -> Dict[str, Any]:
    """Insere ou atualiza a missão no índice, pela sessão. Devolve status e achados."""
    indice = indice if indice is not None else carregar(base)
    achados: List[Dict[str, str]] = []
    missoes: List[Dict[str, Any]] = indice.setdefault("missoes", [])

    if not ficha.get("slug") and not ficha.get("nome"):
        achados.append({"severidade": "atencao", "codigo": "sem-identificacao",
                        "resumo": "A execução não produziu slug nem nome — a missão não entra no índice."})
        return {"status": "amarelo", "achados": achados, "ficha": ficha, "total": len(missoes), "vizinhas": []}

    proximas = vizinhas(ficha, indice, n=3)
    for m in proximas:
        if m["semelhanca"] >= LIMIAR_PARECIDA and not tem_lacuna(m):
            achados.append({"severidade": "atencao", "codigo": "missao-parecida",
                            "resumo": f"Parecida com `{m.get('slug') or m.get('sessao')}` ({m['semelhanca']:.2f}): {m.get('descoberta', '')[:90]}"})

    achados += colisao_de_slug(ficha, missoes)

    anterior = next((m for m in missoes if m.get("sessao") and m.get("sessao") == ficha.get("sessao")), None)
    if anterior:
        # Status humano já atribuído vence o derivado: promover é ato de pessoa.
        if str(anterior.get("status", "")) in STATUS_HUMANOS:
            ficha = {**ficha, "status": anterior["status"]}
        missoes[missoes.index(anterior)] = ficha
    else:
        missoes.append(ficha)

    if gravar_arquivo:
        gravar(indice, base)
    return {"status": "amarelo" if achados else "aprovado", "achados": achados, "ficha": ficha,
            "total": len(missoes), "vizinhas": proximas}


def recorrencias(indice: Optional[Dict[str, Any]] = None, minimo: int = 3, janela: int = 20,
                 base: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Padrões de achado pedagógico que voltaram — a base para virar regra do prompt.

    Recorrente = aparece em `minimo` sessões DE PELO MENOS DUAS MISSÕES distintas, dentro das
    últimas `janela`. Duas missões é o que separa "defeito daquela missão" de "defeito que a
    esteira produz": reexecutar a mesma missão não conta como recorrência.

    Existe porque em 14 execuções os pareceres emitiram 40 achados de conteúdo e nenhum foi
    fechado — cada execução redescobria o mesmo problema com um id novo.
    """
    idx = indice if indice is not None else carregar(base)
    fichas = (idx.get("missoes") or [])[-janela:]
    por_padrao: Dict[str, Dict[str, Any]] = {}
    for f in fichas:
        slug = f.get("slug") or "—"
        for achado in f.get("achados_pedagogicos") or []:
            padrao = str(achado.get("padrao") or "outro")
            reg = por_padrao.setdefault(padrao, {"padrao": padrao, "sessoes": 0, "slugs": set(), "exemplo": ""})
            reg["sessoes"] += 1
            reg["slugs"].add(slug)
            if not reg["exemplo"]:
                reg["exemplo"] = str(achado.get("resumo") or "")[:160]
    fora = []
    for reg in por_padrao.values():
        if reg["sessoes"] >= minimo and len(reg["slugs"]) >= 2:
            fora.append({**reg, "slugs": sorted(reg["slugs"]), "missoes": len(reg["slugs"])})
    return sorted(fora, key=lambda r: -r["sessoes"])


_RE_PASTA_SESSAO = re.compile(r"^\d{8}-\d{6}-(exp\d{2}(?:ef|em)\d+b)$", re.IGNORECASE)


def slugs_das_sessoes(base: Optional[Path] = None) -> Set[str]:
    """Slugs das missões que têm sessão gravada ao lado do índice — pelo NOME da pasta.

    Só lista diretórios e confere que `estado.json` existe: em produção `output/` é o bucket
    montado, e abrir cada estado (1–2 MB) a cada execução custaria mais que o próprio gate.
    """
    raiz = caminho_indice(base).parent
    if not raiz.is_dir():
        return set()
    achados: Set[str] = set()
    for pasta in raiz.iterdir():
        m = _RE_PASTA_SESSAO.match(pasta.name)
        if m and pasta.is_dir() and (pasta / "estado.json").exists():
            achados.add(m.group(1).lower())
    return achados


def saude_do_indice(indice: Optional[Dict[str, Any]] = None, base: Optional[Path] = None) -> Dict[str, Any]:
    """Quantas linhas do índice sustentam uma reprovação em V5 — e quantas não.

    A verificação de semelhança só reprova contra uma linha COMPLETA: `004_nucleo_narrativo.md`
    instrui que "linha com campo `—` ou `[preencher…]` não serve de comparação". Com o índice
    majoritariamente incompleto, o V5 **se autodesliga** — e em silêncio, que é o problema: o
    dossiê continua mostrando o gate verde. Em 23/09/2026, 10 das 14 fichas (71%) estavam
    assim, e nenhuma execução avisou.
    """
    idx = indice if indice is not None else carregar(base)
    missoes = idx.get("missoes", [])
    cegas = [m for m in missoes if tem_lacuna(m)]
    total = len(missoes)
    # A outra metade da cegueira, que a contagem de linhas não vê: missão GERADA que nunca
    # entrou no índice. Em 23/09/2026 o bucket tinha 14 sessões e 1 missão indexada — zero
    # linhas furadas, fração cega 0%, nenhum aviso, e o V5 comparando contra uma só.
    no_indice = {str(m.get("slug") or "").lower() for m in missoes}
    fora = sorted(slugs_das_sessoes(base) - no_indice)
    return {
        "total": total,
        "cegas": len(cegas),
        "uteis": total - len(cegas),
        "fracao_cega": (len(cegas) / total) if total else 0.0,
        "slugs_cegos": [m.get("slug") or "—" for m in cegas],
        "fora_do_indice": fora,
    }


def aviso_de_indice_cego(saude: Dict[str, Any]) -> Optional[str]:
    """Frase para o dossiê quando o gate de semelhança perdeu a base de comparação.

    Os dois defeitos convivem — fichas furadas E missões geradas fora do índice — e o aviso diz
    os dois: um não pode esconder o outro.
    """
    partes: List[str] = []
    fora = saude.get("fora_do_indice") or []
    if fora:
        partes.append(
            f"> ⚠️ **O índice não conhece {len(fora)} missão(ões) já gerada(s)** "
            f"({', '.join(f'`{s}`' for s in fora[:8])}{'…' if len(fora) > 8 else ''}): elas têm "
            f"sessão gravada e não estão no catálogo, então a verificação de semelhança (V5) não as "
            f"compara. Rode `python scripts/catalogo.py reconstruir` onde as sessões estão.")
    if saude["total"] == 0 and not fora:
        partes.append("> ⚠️ O índice está vazio: a verificação de semelhança (V5) não tem contra o que "
                      "comparar e **não reprovará nada** nesta execução.")
    elif saude["total"] and saude["fracao_cega"] >= 0.5:
        partes.append(
            f"> ⚠️ **A verificação de semelhança está praticamente desligada**: "
            f"{saude['cegas']} das {saude['total']} fichas do índice ({saude['fracao_cega']:.0%}) "
            f"não têm campo de comparação preenchido, e o V5 não reprova contra linha incompleta. "
            f"Rode `python scripts/catalogo.py reconstruir` e preencha `tipo_decisao` e "
            f"`porta_abstracao` das fichas antigas — sem isso o gate segue verde sem julgar nada.")
    return "\n>\n".join(partes) or None


def relatorio_markdown(resultado: Dict[str, Any], missao: str = "") -> str:
    """Relatório legível + envelope JSON, no padrão dos demais gates determinísticos."""
    f = resultado.get("ficha", {})
    linhas = [f"# Registro no catálogo de missões — {missao or f.get('slug') or 'missão'}", ""]
    linhas.append(f"**Registrada como:** `{f.get('status', '—')}` · índice com **{resultado.get('total', 0)}** missão(ões).")
    linhas.append("")
    if f.get("parecer_humano"):
        linhas.append(f"**Parecer humano em vigor:** {f['parecer_humano']}. O status segue o parecer: a reprovação que "
                      "quem responde pela etapa viu e liberou não bloqueia a missão.")
        linhas.append("")
    if f.get("liberacao_produto"):
        linhas.append(f"**Liberação de produto:** {f['liberacao_produto']}. O status não muda: é registro de "
                      "governança (plano «Produto dono do contrato», D9).")
        linhas.append("")
    linhas.append("O registro é fato, não juízo: toda execução entra, inclusive a bloqueada — senão a mesma ideia volta a ser gerada. Promover para `validada`, `aprovada` ou `em produção` é ato humano (`scripts/catalogo.py promover`).")
    linhas.append("")
    linhas.append("## Ficha desta missão")
    linhas.append("")
    linhas.append(tabela_markdown([f]))
    linhas.append("")
    if f and tem_lacuna(f):
        linhas.append("> ⚠️ Campo de comparação vazio nesta ficha: o critério 2.5 e a verificação V5 não conseguem julgar contra ela nas próximas execuções. Preencher no núcleo narrativo ou na seção 1 do catálogo proposto pelo agente 51.")
        linhas.append("")
    aviso = aviso_de_indice_cego(saude_do_indice())
    if aviso:
        linhas.append(aviso)
        linhas.append("")
    linhas.append("## Missões mais próximas no índice")
    linhas.append("")
    linhas.append(tabela_markdown(resultado.get("vizinhas", []), com_semelhanca=True))
    linhas.append("")
    linhas.append("## Achados")
    linhas.append("")
    if resultado.get("achados"):
        for a in resultado["achados"]:
            marca = "🔵" if a.get("severidade") == "decisao_humana" else "⚠️"
            linhas.append(f"- {marca} **{a['codigo']}** — {a['resumo']}")
    else:
        linhas.append("- Nenhum. A missão entrou no índice sem colisão de slug nem semelhança alta.")
    linhas.append("")
    envelope = {
        "agente": AGENTE,
        "missao": missao or f.get("slug", ""),
        "rodada": 1,
        "status": resultado.get("status", "aprovado"),
        "registrada": bool(f.get("slug") or f.get("nome")),
        "total_no_indice": resultado.get("total", 0),
        "achados": resultado.get("achados", []),
        "precisa_humano": any(a.get("severidade") == "decisao_humana" for a in resultado.get("achados", [])),
    }
    linhas.append("```json")
    linhas.append(json.dumps(envelope, ensure_ascii=False))
    linhas.append("```")
    return "\n".join(linhas)
