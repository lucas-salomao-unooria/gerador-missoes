"""Correção pontual: o pedido vira trocas trecho a trecho, e o código as aplica. Nada de LLM aqui.

Até 19/10/2026 toda correção reexecutava a etapa: cada autor reescrevia o seu documento a partir do anterior
(`anterior_<chave>`), e os gates julgavam a missão inteira com as regras do dia. No acervo do bucket, a troca de um
número ("mais de 70%" → "≈47%") devolveu a spec com 49% das linhas iguais, o DS migrado, os conceitos renomeados e
dois 🔴 que a missão não tinha (exp03em1b, 13/10/2026). Quanto mais o PO escrevia "não mexa no resto", mais itens sem
prova a fidelidade acusava.

Aqui a correção é uma edição: o editor (`prompts/transversal/editor_pontual.md`) devolve uma lista de trocas
`{documento, de, para}`, e `aplicar` as executa sobre o texto. O que nenhuma troca toca fica idêntico por construção — e
`reaplicar` prova isso depois, refazendo as trocas sobre a versão anterior e comparando com a atual.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Tuple, Union

#: Documentos que o editor pode trocar, por etapa da correção. São os autorais da etapa: os gates não escrevem
#: documento, e os de outras etapas são de outro dono. A ordem é a da esteira, para o editor ler na ordem certa.
DOCUMENTOS_POR_ETAPA: Dict[str, Tuple[str, ...]] = {
    "produto": ("nucleo_narrativo", "one_pager", "spec_missao", "one_pager_resumido"),
    "spec": ("spec_missao", "one_pager_resumido"),
    # o pedagógico fecha o design desde o PR 10 (24/10/2026): o pedido do PO sobre ele é editado aqui, e o dev não o toca
    "design": ("fechamento_lacunas", "ambiente_simulado", "brief_oficio", "jornada_telas", "fluxo_arestas",
               "copy_strings", "copy_strings_revisada", "camada_caa", "wireframes_cobertura", "prototipo_html",
               "one_pager_pedagogico"),
    "dev": ("handoff_dev", "brief_assets", "banco_conteudo", "prd_final"),
}
#: Documentos autorais que a etapa tem e o editor não toca: ficam travados como estão (o autor não roda). O mapa e a
#: ideação são a origem do núcleo; refazê-los numa correção pontual sortearia outro mecanismo. A resposta do passo de
#: completude (PR 6) já está dentro da spec, no bloco 15, e é lá que o editor a troca: refazê-la desfaria a troca.
TRAVADOS_SEM_EDICAO: Dict[str, Tuple[str, ...]] = {"produto": ("mapa_conceitual", "ideacao_mecanismos", "completude_spec"),
                                                   "spec": ("completude_spec",)}
#: Documento maior que isto não vai ao editor. É folga, não corte: os protótipos HTML do acervo têm de 110 a 135 KB, e
#: 1 milhão de caracteres (~250 mil tokens) ainda cabe no contexto do modelo com os outros documentos da etapa.
MAX_CARACTERES_DOCUMENTO = 1_000_000

MODO_PONTUAL = "pontual"
MODO_ESTRUTURAL = "estrutural"


@dataclass
class Edicao:
    """Uma troca: `de` aparece exatamente uma vez em `documento` e vira `para`."""

    documento: str
    de: str
    para: str
    motivo: str = ""


@dataclass
class Proposta:
    """O que o editor devolveu: as trocas, ou o motivo de o pedido não caber numa edição."""

    modo: str
    motivo: str = ""
    edicoes: List[Edicao] = field(default_factory=list)
    #: Partes do pedido que o editor não aplicou e por quê (conflito com regra, decisão do PO).
    pendencias: List[str] = field(default_factory=list)
    bruto: str = ""

    @property
    def pontual(self) -> bool:
        return self.modo == MODO_PONTUAL


@dataclass
class Resultado:
    documentos: Dict[str, str]
    aplicadas: List[Edicao] = field(default_factory=list)
    falhas: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.falhas


def documentos_da_etapa(estado: Dict[str, Any], etapa: str, versao_anterior: bool = False) -> Dict[str, str]:
    """`{chave: texto}` dos documentos que o editor pode trocar, na versão que o autor escreveu.

    A spec é a do Gate 0 quando existe: na sessão anterior ao PR 6, `spec_missao` pode já trazer a consolidação do D0, e
    a base de um refazer é a do autor (`pipeline.reexecucao._guardar_versoes_anteriores`). Na sessão nova a `spec_missao`
    é a de produto, com o bloco 15 da completude. Documento vazio fica de fora.

    `versao_anterior`: o documento que falta no estado vem de `versao_anterior_<chave>`. É o passo de design (ou de dev)
    de uma cascata: a correção de produto que veio antes apagou design e dev do estado e guardou a versão deles ali.
    """
    from tools.conteudo_aprovado import remover_anexo
    from tools.governanca import SECAO_DE_PENDENCIAS, sem_bloco

    docs: Dict[str, str] = {}
    for chave in DOCUMENTOS_POR_ETAPA.get(etapa, ()):
        texto = estado.get("spec_missao_gate0") if chave == "spec_missao" and etapa in ("produto", "spec") else None
        texto = str(texto or estado.get(chave) or "")
        if versao_anterior and not texto.strip():
            texto = str(estado.get(f"versao_anterior_{chave}") or "")
        if chave in ("prd_final", "one_pager_pedagogico"):
            # o anexo literal é da esteira (`AnexoAprovadoAgent`), que o põe de novo depois
            texto = remover_anexo(texto)
        if chave in SECAO_DE_PENDENCIAS:
            # as pendências de governança também (PR 9): o documento travado as recebe de novo, como estão agora
            # (`agents.callbacks.travar_documento_na_correcao_pontual`)
            texto = sem_bloco(texto)
        if texto.strip():
            docs[chave] = texto
    return docs


def travados(etapa: str) -> Tuple[str, ...]:
    """Documentos cujo autor não roda numa correção pontual da etapa."""
    return tuple(DOCUMENTOS_POR_ETAPA.get(etapa, ())) + TRAVADOS_SEM_EDICAO.get(etapa, ())


def renderizar(documentos: Dict[str, str]) -> str:
    """Os documentos para o editor, cada um entre marcas com a chave — é a chave que ele usa em `documento`."""
    blocos = []
    for chave, texto in documentos.items():
        if len(texto) > MAX_CARACTERES_DOCUMENTO:
            blocos.append(f'<documento chave="{chave}">\n(documento com {len(texto)} caracteres: grande demais para '
                          "a edição pontual — não o edite; se o pedido exige mudá-lo, responda modo estrutural)\n</documento>")
            continue
        blocos.append(f'<documento chave="{chave}">\n{texto}\n</documento>')
    return "\n\n".join(blocos)


_RE_JSON = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.S)


def ler_proposta(texto: str) -> Proposta:
    """O último bloco JSON com `modo`. Sem ele, ou com modo desconhecido, é estrutural: na dúvida, refaz."""
    dados: Dict[str, Any] = {}
    candidatos = _RE_JSON.findall(texto or "") or ([texto.strip()] if (texto or "").strip().startswith("{") else [])
    for bruto in reversed(candidatos):
        try:
            carregado = json.loads(bruto)
        except json.JSONDecodeError:
            continue
        if isinstance(carregado, dict) and "modo" in carregado:
            dados = carregado
            break
    modo = str(dados.get("modo") or "").strip().lower()
    if modo not in (MODO_PONTUAL, MODO_ESTRUTURAL):
        return Proposta(modo=MODO_ESTRUTURAL, motivo="o editor não devolveu uma proposta legível", bruto=texto or "")
    edicoes = [_como_edicao(e) for e in dados.get("edicoes") or [] if isinstance(e, dict)]
    pendencias = [str(p) for p in (dados.get("pendencias") or []) if str(p).strip()]
    return Proposta(modo=modo, motivo=str(dados.get("motivo") or "").strip(), edicoes=edicoes,
                    pendencias=pendencias, bruto=texto or "")


def _localizar(texto: str, trecho: str) -> List[int]:
    posicoes, inicio = [], 0
    while True:
        i = texto.find(trecho, inicio)
        if i < 0:
            return posicoes
        posicoes.append(i)
        inicio = i + 1


def aplicar(documentos: Dict[str, str], edicoes: Iterable[Edicao]) -> Resultado:
    """Aplica as trocas na ordem. Tudo ou nada: com uma falha, os documentos voltam intactos.

    Cada `de` tem de existir **uma** vez no documento (já com as trocas anteriores aplicadas). Zero vezes é trecho
    inventado ou parafraseado; duas ou mais, ambíguo — o editor recebe a falha e inclui mais contexto. A comparação é
    exata: tolerar diferença de espaço aqui seria trocar um trecho que o editor não leu.
    """
    novos = dict(documentos)
    aplicadas: List[Edicao] = []
    falhas: List[str] = []
    for n, e in enumerate(edicoes, 1):
        if e.documento not in novos:
            falhas.append(f"edição {n}: documento `{e.documento}` não existe nesta etapa "
                          f"(use um de: {', '.join(f'`{k}`' for k in novos)})")
            continue
        if not e.de.strip():
            falhas.append(f"edição {n} (`{e.documento}`): `de` vazio — para acrescentar, use como `de` o trecho "
                          "depois do qual o texto entra e repita-o no começo de `para`")
            continue
        if e.de == e.para:
            falhas.append(f"edição {n} (`{e.documento}`): `de` e `para` são iguais")
            continue
        achadas = _localizar(novos[e.documento], e.de)
        if not achadas:
            falhas.append(f"edição {n} (`{e.documento}`): o trecho `de` não existe, letra por letra: «{e.de[:160]}»")
            continue
        if len(achadas) > 1:
            falhas.append(f"edição {n} (`{e.documento}`): o trecho `de` aparece {len(achadas)} vezes — inclua contexto "
                          f"até ele ser único: «{e.de[:160]}»")
            continue
        i = achadas[0]
        novos[e.documento] = novos[e.documento][:i] + e.para + novos[e.documento][i + len(e.de):]
        aplicadas.append(e)
    if falhas:
        return Resultado(documentos=dict(documentos), aplicadas=[], falhas=falhas)
    return Resultado(documentos=novos, aplicadas=aplicadas)


def reaplicar(anterior: str, atual: str, documento: str, edicoes: Iterable[Union[Edicao, Dict[str, Any]]]) -> bool:
    """O documento atual é a versão anterior mais as trocas dele, e nada além? É a prova das ordens de não mexer.

    Compara sem o anexo da esteira (o PRD e o pedagógico ganham o anexo literal depois do autor), sem as pendências de
    governança que a esteira escreve no handoff e no PRD (PR 9: o A119 as atualiza também na correção pontual) e sem
    espaço nas pontas de cada linha.
    """
    from tools.conteudo_aprovado import remover_anexo
    from tools.governanca import sem_bloco

    proprias = [e for e in (_como_edicao(x) for x in edicoes) if e.documento == documento]
    resultado = aplicar({documento: sem_bloco(remover_anexo(anterior or ""))}, proprias)
    if not resultado.ok:
        return False
    return _linhas(resultado.documentos[documento]) == _linhas(sem_bloco(remover_anexo(atual or "")))


def _linhas(texto: str) -> List[str]:
    return [l.strip() for l in (texto or "").strip().splitlines() if l.strip()]


def _como_edicao(e: Union[Edicao, Dict[str, Any]]) -> Edicao:
    if isinstance(e, Edicao):
        return e
    para = e.get("para")
    return Edicao(documento=str(e.get("documento") or "").strip(), de=str(e.get("de") or ""),
                  para="" if para is None else str(para), motivo=str(e.get("motivo") or "").strip())


def como_dicts(edicoes: Iterable[Edicao]) -> List[Dict[str, str]]:
    return [asdict(e) for e in edicoes]


def resumo(edicoes: Iterable[Union[Edicao, Dict[str, Any]]], limite: int = 160) -> str:
    """As trocas em markdown, para o registro da correção e o relatório da linha de base."""
    linhas = []
    for n, e in enumerate((_como_edicao(x) for x in edicoes), 1):
        de = re.sub(r"\s+", " ", e.de).strip()
        para = re.sub(r"\s+", " ", e.para).strip()
        linhas.append(f"{n}. `{e.documento}` — «{de[:limite]}» → «{para[:limite] or '(removido)'}»"
                      + (f" — {e.motivo}" if e.motivo else ""))
    return "\n".join(linhas) or "Nenhuma troca."


def trocas_por_linhas(documento: str, antes: str, depois: str, motivo: str = "") -> List[Edicao]:
    """As trocas, linha a linha, que levam `antes` a `depois`: cada bloco de linhas que mudou vira uma troca, com as
    linhas vizinhas como contexto até o `de` ser único no texto da hora (como `aplicar` exige).

    É como um passo determinístico registra o que mudou num documento travado da correção pontual: `reaplicar` refaz as
    trocas do pedido e estas, e a prova das ordens de não mexer continua de pé. A cópia dos textos-chave (A078b, PR 7)
    mexia na copy depois do editor, e a fidelidade de design ganhava `preservacao-sem-prova` (exp02ef1b, 24/10/2026).
    Vazio quando não há diferença, ou quando as trocas não reproduzem `depois` letra por letra.
    """
    import difflib

    a, b = (antes or "").split("\n"), (depois or "").split("\n")
    if a == b:
        return []
    edicoes: List[Edicao] = []
    atual = list(a)
    deslocamento = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        ini, fim, novo = i1 + deslocamento, i2 + deslocamento, b[j1:j2]
        acima = abaixo = 0
        while True:
            de = "\n".join(atual[ini - acima: fim + abaixo])
            if de.strip() and len(_localizar("\n".join(atual), de)) == 1:
                break
            if ini - acima > 0 and (acima <= abaixo or fim + abaixo >= len(atual)):
                acima += 1
            elif fim + abaixo < len(atual):
                abaixo += 1
            else:
                return []
        para = "\n".join(atual[ini - acima: ini] + novo + atual[fim: fim + abaixo])
        edicoes.append(Edicao(documento=documento, de=de, para=para, motivo=motivo))
        atual = atual[:ini] + novo + atual[fim:]
        deslocamento += (j2 - j1) - (i2 - i1)
    resultado = aplicar({documento: antes or ""}, edicoes)
    if not resultado.ok or resultado.documentos[documento] != (depois or ""):
        return []
    return edicoes
