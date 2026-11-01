"""Classificador de sentido: uma pergunta estreita por regra, lida por um LLM e conferida em código (C7).

Os gates determinísticos de produto tinham 59% de falso positivo no levantamento de 24/10/2026, e a maior parte vinha de
regex que interpreta sentido em texto livre: a porcentagem é meta ou mecânica? o texto entre aspas é botão? a frase do
pedido é exigência ou contexto? Cada revisão da C1 e da C3 achou um furo novo nessas regras. A fase A da C7 (25/10/2026,
`analises-esteira/2026-10-25/c7/relatorio-fase-a.md`) mediu regex × classificador nos casos reais, nos mutantes que os
revisores escreveram e num held-out rotulado às cegas: toda regra afinada no gabarito caiu no caso seguinte (meta ×
mecânica da 1ª versão da C1: revocação 0,12 nas 17 paráfrases; «é botão?» da main: precisão 0,15), e o classificador
acertou 0,97–1,00 de precisão e 0,93–1,00 de revocação onde a pergunta é a leitura de um trecho.

Como o classificador pergunta (o mesmo protótipo que a fase A mediu, sem mudar uma palavra do prompt):

- **uma função por pergunta** (`numero_da_hipotese`, `rotulo_de_botao`, `item_do_pedido_classe`,
  `decisao_do_po_confirmada`, `ressalva_repete_decisao_do_po`), com prompt curto e versionado. Mudar o texto da
  instrução exige subir a versão: a versão entra no hash do cache (`test_classificador.py` trava o texto pela versão);
- **resposta JSON** com rótulo de lista fechada (`enum` no schema) e a citação literal do trecho que decide. O código
  confere que a citação está na entrada; se não está, a resposta vale «nao_sei»;
- **parâmetros do juiz determinístico** (`agents/base.py`): modelo, `temperatura_juiz` e `seed_juiz` da configuração do
  app. Com eles, a fase A teve o mesmo rótulo em 407/407 casos com e sem cache;
- **cache pelo hash** (pergunta, versão, modelo, entrada): a reexecução do mesmo trecho responde igual e não custa nada.
  O da sessão vive no estado (`KEY`), compacto — rótulo e citação curta, ~250 bytes por leitura, com teto de
  `MAX_ENTRADAS` (o `estado.json` real tem de 1 a 2,9 MB): sobrevive à reexecução (nenhuma etapa o apaga) e ao Cloud Run
  (o estado vai ao bucket). O de teste é versionado (`fixtures/classificador-cache.json`): o CI e a regressão rodam sem
  chamar o modelo (`CLASSIFICADOR_SENTIDO=so_cache`);
- **nunca derruba a esteira**: erro, timeout, sem chave, fora do cache de teste ou acima do limite de chamadas do gate
  (`LIMITE_POR_GATE`) → «nao_sei», com o motivo. A chave nunca é impressa nem gravada; do erro só sai o tipo.

O que o rótulo faz com o achado é da política de severidade (`tools/severidade.py`): interpretação — regex heurística ou
LLM — nunca bloqueia sozinha. Onde o classificador não ganhou na fase A (texto de tela × fala, lacuna, «é o mesmo botão
do glossário?», mesma hipótese) ele não entra.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

#: A chave do estado com o cache da sessão e o custo: `{cache: {hash: {p, v, r, c}}, custo: {...}}`.
KEY = "classificador_sentido"
NAO_SEI = "nao_sei"
#: Leituras guardadas no estado por sessão; a mais antiga sai primeiro. Na fase A, a missão mais cara do acervo pedia 15
#: números de hipótese, 7 linhas atribuídas ao PO e uns 40 itens do pedido.
MAX_ENTRADAS = 500
#: Chamadas ao modelo por gate (leituras do cache não contam). Acima disso, «nao_sei» com o motivo: o achado vira 🟡.
LIMITE_POR_GATE = 40
#: Chamadas simultâneas num lote (a fase A rodou com 8 sem 429).
PARALELO = 8
#: Segundos por tentativa; as tentativas são as do app (`TENTATIVAS_MODELO`).
TIMEOUT_S = 60
#: Caracteres da citação guardados no cache: ela já foi conferida contra a entrada.
MAX_CITACAO = 300

#: `ligado` (padrão: cache da sessão, depois o modelo) · `so_cache` (CI e regressão: cache da sessão e o de teste;
#: o que não está nele é «nao_sei») · `desligado` (tudo «nao_sei»).
ENV_MODO = "CLASSIFICADOR_SENTIDO"
#: O cache versionado de teste, lido além do da sessão (o `conftest.py` e a regressão o apontam).
ENV_CACHE_FIXO = "CLASSIFICADOR_CACHE_FIXO"
#: `1` grava no cache de teste o que o modelo responder — só para regravá-lo com rede e chave
#: (`scripts/gravar_cache_classificador.py`).
ENV_GRAVAR_CACHE_FIXO = "CLASSIFICADOR_GRAVAR_CACHE_FIXO"
CACHE_FIXO_PADRAO = Path(__file__).resolve().parent.parent / "fixtures" / "classificador-cache.json"


# ------------------------------------------------------------------ as perguntas
def _bloco(titulo: str, texto: str) -> str:
    return f"--- {titulo} ---\n{texto}\n"


@dataclass(frozen=True)
class Pergunta:
    id: str
    versao: str
    rotulos: Tuple[str, ...]
    instrucao: str
    montar: Callable[[Dict[str, Any]], str]

    @property
    def rotulos_com_nao_sei(self) -> List[str]:
        return list(self.rotulos) + [NAO_SEI]

    def prompt(self, entrada_texto: str) -> str:
        return (self.instrucao.strip() + "\n\nRótulos possíveis: " + ", ".join(self.rotulos_com_nao_sei)
                + ".\nResponda só o JSON {\"citacao\": …, \"rotulo\": …}. A citação é copiada letra por letra da ENTRADA; "
                  "se não houver trecho que decida, use \"nao_sei\".\n\n=== ENTRADA ===\n" + entrada_texto)


#: `hipotese-diverge` (`tools/montagem.py`). Fase A: P 1,00 R 1,00 em 60 casos (29 reais, 17 paráfrases da H1 30×25 da
#: exp02ef1b e 14 do held-out, em que o regex perdia 4 de 13 metas pela isenção «duração que o contrato tem»).
NUMERO_DA_HIPOTESE = Pergunta(
    "numero_da_hipotese", "v1", ("meta", "mecanica"), """
A HIPÓTESE DO DOCUMENTO é uma hipótese de validação de uma missão educacional. O NÚMERO aparece nela.
- meta: o número é o critério da hipótese — a proporção, o limiar ou a duração que diz se ela se confirma ou falha
  («pelo menos N% dos estudantes…», «indica falha se menos de N%…», «em até N s»).
- mecanica: o número descreve um parâmetro do jogo, da interface ou do conteúdo citado na hipótese — peso de pontuação,
  duração de animação, taxa embutida no material, quantidade de itens — e não é o critério de sucesso ou falha.
A HIPÓTESE APROVADA (§17) é só referência. A citação é o trecho da HIPÓTESE DO DOCUMENTO que contém o número e decide.""",
    lambda e: (_bloco("HIPÓTESE DO DOCUMENTO", e["hipotese_no_documento"])
               + _bloco("HIPÓTESE APROVADA (§17)", e["hipotese_aprovada_no_17"]) + _bloco("NÚMERO", e["numero"])))

#: `rotulo-divergente` (`tools/consistencia.py`), como filtro do candidato em prosa sem chave de copy. Fase A: P 1,00
#: R 1,00 em 55 (15 reais e 40 do held-out, em que a C4 tinha precisão 0,53).
ROTULO_DE_BOTAO = Pergunta(
    "rotulo_de_botao", "v1", ("rotulo_de_botao", "outro"), """
Num documento de design de uma missão (jornada de telas, fluxo, copy, PRD), o CANDIDATO foi recortado da LINHA como se
fosse o texto de um botão. Diga o que ele é ali.
- rotulo_de_botao: o texto visível de um botão, link ou controle que o estudante ou o professor toca na interface.
- outro: qualquer outra coisa — o verbo que descreve o gesto do usuário, nome de estado, de tela, de seção ou
  identificador de código, rótulo de seta de diagrama, nome da missão ou título, pedaço cortado entre duas citações,
  fala ou frase de conteúdo.
Use o CABEÇALHO DA TABELA, quando houver, para saber o que a coluna guarda. A citação é o trecho da LINHA que decide.""",
    lambda e: (_bloco("DOCUMENTO", e["documento"])
               + (_bloco("CABEÇALHO DA TABELA", e["cabecalho_da_tabela"]) if e.get("cabecalho_da_tabela") else "")
               + _bloco("LINHA", e["linha"]) + _bloco("CANDIDATO", e["candidato"])))

_INSTRUCAO_ITEM_DO_PEDIDO = """
Classifique um ITEM recortado do pedido de correção que chega ao agente que reescreve os documentos de uma missão.
- exigencia: o item pede que o documento passe a ter, mude, tire ou troque algo — inclusive quando o PO dita um texto,
  uma regra ou um critério sem verbo de ordem (o documento tem de conter aquilo).
- preservacao: o item só manda manter, não mexer ou preservar algo como está.
- contexto: o item não pede nada ao documento — justificativa, explicação de um porquê, título que só anuncia os itens
  seguintes, comentário ou exemplo.
- texto_da_esteira: instrução genérica do sistema ao agente, que não foi escrita pelo PO (cabeçalho automático sobre
  como agir na reexecução).
A citação é o trecho do ITEM que decide."""

#: `exigencia-dispensada` (`tools/fidelidade.py`), como segunda leitura quando o juiz diz «contexto». A v2 lê o item com as
#: duas linhas que o antecedem no pedido: o checklist recorta o critério do título que o anuncia. Fase A: v1 P 1,00 R 0,74;
#: v2 P 1,00 R 0,93 em 53 (o `_RE_ACAO` tinha revocação 0,26).
ITEM_DO_PEDIDO_CLASSE = Pergunta(
    "item_do_pedido_classe", "v2", ("exigencia", "preservacao", "contexto", "texto_da_esteira"),
    _INSTRUCAO_ITEM_DO_PEDIDO + """
As LINHAS ANTERIORES NO PEDIDO são só contexto (o título ou a frase que introduz o item): classifique o ITEM. Um
critério, texto ou regra ditado sob um título que manda substituir, escrever ou corrigir é exigencia.""",
    lambda e: ((_bloco("LINHAS ANTERIORES NO PEDIDO", e["linhas_anteriores_no_pedido"])
                if e.get("linhas_anteriores_no_pedido") else "") + _bloco("ITEM", e["item"])))

#: `decisao-atribuida-ao-po` (`tools/decisoes.py`): só PISTA que ordena e explica o 🟡 «a conferir» — a confirmação é do
#: registro estruturado do PO (C3). Fase A: P 1,00 R 1,00 em 53 (a 3ª revisão da C3 tem precisão 0,35 nos reais), mas
#: com 0 erro em 38 positivos o limite superior do erro a 95% ainda é ~8%: um falso «confirmada» esconderia atribuição
#: falsa ao PO.
DECISAO_DO_PO_CONFIRMADA = Pergunta(
    "decisao_do_po_confirmada", "v1", ("confirmada", "nao_confirmada"), """
Você confere se um documento da esteira atribui ao PO (o dono do produto) uma decisão que o próprio PO registrou.
A LINHA do documento diz que o PO aprovou, homologou, ratificou ou decidiu algo. Os REGISTROS DO PO são tudo o que o PO
escreveu na sessão: pedidos numerados («Pedido N»), pareceres e decisões gravadas no cartão do de acordo.
- confirmada: um registro do PO decide aquilo que a linha atribui a ele — o mesmo assunto, os mesmos valores (números,
  itens, IDs) e o mesmo sentido (aceitar). Se a linha cita «Pedido N», é o Pedido N que tem de dizer aquilo.
- nao_confirmada: nenhum registro decide aquilo; ou o PO recusou, adiou, mandou tirar, trocar, reduzir ou mudar; ou o
  valor da linha é outro; ou o PO só citou aquele texto para pedir que mudasse; ou a linha estende a decisão a itens que
  o registro não cobre.
A citação é o trecho dos REGISTROS DO PO que decide; se não houver registro nenhum sobre aquilo, cite a LINHA.""",
    lambda e: _bloco("LINHA (" + e["documento"] + ")", e["linha"]) + _bloco("REGISTROS DO PO", e["registros_do_po"]))

#: Recontagem dos juízes de produto (`tools/juizes_produto.py`): também só PISTA do «a conferir». Fase A: P 0,97 R 1,00
#: em 37 (o erro, P096, é discutível).
RESSALVA_REPETE_DECISAO_DO_PO = Pergunta(
    "ressalva_repete_decisao_do_po", "v1", ("repete_decisao_do_po", "aponta_problema"), """
Um juiz de produto escreveu a RESSALVA abaixo sobre um documento, e ela menciona uma decisão do PO (o dono do produto).
Os REGISTROS DO PO são tudo o que o PO escreveu na sessão.
- repete_decisao_do_po: a ressalva só registra algo que o PO já decidiu — o valor que ela cita é o que o PO aceitou nos
  registros — e não aponta nada a corrigir no documento além disso.
- aponta_problema: a ressalva pede correção ou conferência: o documento descumpre, excede ou não implementa a decisão;
  cita um valor diferente do decidido; traz outra pendência junto; ou os registros do PO não contêm a decisão que ela
  diz (ou o PO a recusou).
A citação é o trecho da RESSALVA (ou dos REGISTROS) que decide.""",
    lambda e: _bloco("RESSALVA", e["ressalva"]) + _bloco("REGISTROS DO PO", e["registros_do_po"]))

#: `alteracao-sem-pedido` (`tools/one_pager_po.py`): verifica se uma alteração declarada na tabela «Alterações sobre o
#: one-pager do PO» foi autorizada pelo briefing, pedido do PO ou voto de comitê quando a citação não bate por regex literal.
ALTERACAO_PO_AUTORIZADA = Pergunta(
    "alteracao_po_autorizada", "v1", ("autorizada", "sem_pedido"), """
A ALTERAÇÃO DECLARADA está na tabela «Alterações sobre o one-pager do PO» de um one-pager gerado. Os REGISTROS E VOTOS
reúnem o briefing, os pedidos do PO e os votos dos comitês pedagógicos da sessão.
- autorizada: há nos REGISTROS E VOTOS uma ordem, decisão ou recomendação de comitê que pede ou justifica essa alteração
  de trecho, mesmo que o autor tenha resumido ou parafraseado o pedido na tabela.
- sem_pedido: nenhum trecho dos REGISTROS E VOTOS pede ou autoriza mudar aquele ponto do one-pager do PO, ou o pedido
  citado na tabela foi inventado.
A citação é o trecho dos REGISTROS E VOTOS que autoriza a mudança; se não houver, cite a ALTERAÇÃO DECLARADA.""",
    lambda e: _bloco("ALTERAÇÃO DECLARADA", e["alteracao_declarada"]) + _bloco("REGISTROS E VOTOS", e["registros_do_po"]))

#: `gesto-fora-da-lista` (`tools/ficha_interacao.py`): verifica se um verbo de gesto da ficha de interação equivale a um
#: dos 12 gestos canônicos da plataforma quando não está no dicionário determinístico de sinônimos.
GESTO_EQUIVALENTE_FICHA = Pergunta(
    "gesto_equivalente_ficha", "v1", ("equivalente", "invalido"), """
Na ficha de interação de um momento da missão, o campo GESTO descreve a ação física ou cognitiva que o estudante ou o
professor realiza na tela. Os gestos canônicos são: tocar, arrastar, deslizar, digitar, escolher, ordenar, marcar,
rolar, ler, ouvir, esperar, falar.
- equivalente: o GESTO descreve claramente uma ação concreta na interface que equivale a um dos 12 gestos canônicos.
- invalido: o GESTO não descreve ação observável do usuário na tela ou está vazio/abstrato demais para desenhar a tela.
A citação é o trecho do GESTO que decide.""",
    lambda e: _bloco("GESTO", e["gesto"]))

#: `papel-divergente` (`tools/consistencia.py`): verifica se a menção ao personagem na LINHA contradiz o PAPEL CANÔNICO
#: do glossário ou se é compatível / refere-se a outra pessoa na mesma frase.
PAPEL_EQUIVALENTE_GLOSSARIO = Pergunta(
    "papel_equivalente_glossario", "v1", ("compativel", "contradiz"), """
A LINHA menciona o PERSONAGEM, cujo papel canônico no glossário da missão é PAPEL CANÔNICO.
- compativel: a LINHA mantém o mesmo papel semântico do glossário (ou usa sinônimo compatível), ou a palavra de gestão/
  coordenação na frase refere-se a outro ator/órgão e não ao PERSONAGEM.
- contradiz: a LINHA atribui diretamente ao PERSONAGEM um cargo ou função incompatível com o PAPEL CANÔNICO.
A citação é o trecho da LINHA que decide.""",
    lambda e: (_bloco("PERSONAGEM", e["candidato"]) + _bloco("PAPEL CANÔNICO", e["papel_canonico"])
               + _bloco("LINHA", e["linha"])))

#: `fala-reescrita` (`tools/one_pager_completo.py`): distingue fala literal inventada de personagem/tela vs termo,
#: conceito ou rótulo curto destacado entre aspas no resumo 0.1/0.2.
ASPAS_CONCEITO_OU_FALA = Pergunta(
    "aspas_conceito_ou_fala", "v1", ("termo_ou_conceito", "fala_de_tela"), """
Na LINHA das seções 0.1 ou 0.2 do one-pager, o TRECHO ENTRE ASPAS apareceu sem correspondência literal palavra por
palavra no restante do one-pager.
- termo_ou_conceito: o trecho entre aspas destaca um conceito pedagógico, nome de mecanismo, expressão figurada,
  parâmetro ou rótulo resumido na prosa, e não uma frase inteira dita por um personagem ou copiada como fala de tela.
- fala_de_tela: a LINHA apresenta o trecho entre aspas como uma fala literal de personagem, mensagem de chat ou frase
  completa lida na tela que foi reescrita em relação ao one-pager.
A citação é o trecho da LINHA que decide.""",
    lambda e: _bloco("LINHA", e["linha"]) + _bloco("TRECHO ENTRE ASPAS", e["candidato"]))

PERGUNTAS: Dict[str, Pergunta] = {p.id: p for p in (
    NUMERO_DA_HIPOTESE, ROTULO_DE_BOTAO, ITEM_DO_PEDIDO_CLASSE, DECISAO_DO_PO_CONFIRMADA,
    RESSALVA_REPETE_DECISAO_DO_PO,
)}

PERGUNTAS_EXTRAS: Dict[str, Pergunta] = {p.id: p for p in (
    ALTERACAO_PO_AUTORIZADA, GESTO_EQUIVALENTE_FICHA,
    PAPEL_EQUIVALENTE_GLOSSARIO, ASPAS_CONCEITO_OU_FALA,
)}

TODAS_AS_PERGUNTAS: Dict[str, Pergunta] = {**PERGUNTAS, **PERGUNTAS_EXTRAS}


# ------------------------------------------------------------------ a leitura
@dataclass(frozen=True)
class Leitura:
    rotulo: str
    citacao: str = ""
    #: `sessao` · `cache_de_teste` · `modelo` · `sem_resposta`
    origem: str = "sem_resposta"
    #: por que é «nao_sei» (sem chave, erro, fora do cache, limite, citação que não confere…); vazio quando respondeu
    motivo: str = ""

    @property
    def nao_sei(self) -> bool:
        return self.rotulo == NAO_SEI

    def explicada(self, nomes: Optional[Dict[str, str]] = None) -> str:
        """A leitura em uma frase, para o 🟡 que o PO lê: «o classificador lê «meta» em «…»», ou por que não leu."""
        if self.nao_sei:
            return "o classificador não respondeu" + (f" ({self.motivo})" if self.motivo else "")
        nome = (nomes or {}).get(self.rotulo, self.rotulo.replace("_", " "))
        return f"o classificador lê «{nome}»" + (f" em «{self.citacao[:160]}»" if self.citacao.strip() else "")


def _plano(texto: str) -> str:
    t = unicodedata.normalize("NFKC", texto or "").lower()
    t = re.sub(r"[“”«»\"'‘’`*_]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def citacao_confere(citacao: str, entrada_texto: str) -> bool:
    """A citação está na entrada, a menos de aspas, ênfase, caixa e espaços — com ao menos 3 caracteres."""
    c = _plano(citacao)
    return len(c) >= 3 and c in _plano(entrada_texto)


def chave(pergunta: Pergunta, entrada_texto: str, modelo: str) -> str:
    """O hash do cache: pergunta, versão, modelo e a entrada como o prompt a mostra."""
    bruto = json.dumps({"p": pergunta.id, "v": pergunta.versao, "m": modelo, "e": entrada_texto},
                       ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def _modo() -> str:
    modo = os.getenv(ENV_MODO, "ligado").strip().lower()
    return modo if modo in ("ligado", "so_cache", "desligado") else "ligado"


# ------------------------------------------------------------------ o cache de teste (versionado)
_LOCK_FIXO = threading.Lock()
_FIXO: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def _caminho_fixo() -> Optional[Path]:
    bruto = os.getenv(ENV_CACHE_FIXO, "").strip()
    return Path(bruto) if bruto else None


def _cache_fixo() -> Dict[str, Any]:
    caminho = _caminho_fixo()
    if caminho is None or not caminho.exists():
        return {}
    with _LOCK_FIXO:
        mtime = caminho.stat().st_mtime
        lido = _FIXO.get(str(caminho))
        if lido is None or lido[0] != mtime:
            try:
                dados = json.loads(caminho.read_text(encoding="utf-8"))
            except ValueError:
                dados = {}
            lido = (mtime, dados.get("leituras") if isinstance(dados.get("leituras"), dict) else {})
            _FIXO[str(caminho)] = lido
        return lido[1]


def _gravar_no_fixo(h: str, registro: Dict[str, Any]) -> None:
    caminho = _caminho_fixo()
    if caminho is None:
        return
    with _LOCK_FIXO:
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else {}
        except ValueError:
            dados = {}
        leituras = dados.get("leituras") if isinstance(dados.get("leituras"), dict) else {}
        leituras[h] = registro
        dados = {"descricao": "Leituras do classificador de sentido (tools/classificador.py) para o CI e a regressão "
                              "rodarem sem chamar o modelo. Regravar: scripts/gravar_cache_classificador.py.",
                 "leituras": dict(sorted(leituras.items()))}
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        _FIXO.pop(str(caminho), None)


# ------------------------------------------------------------------ a sessão (cache do estado e custo por gate)
class Sessao:
    """O cache e o custo de um gate: lidos do estado ao abrir; o que mudou volta ao estado pelo `delta` do gate."""

    def __init__(self, estado: Optional[Dict[str, Any]] = None, gate: str = "", limite: Optional[int] = None):
        registro = (estado or {}).get(KEY) if isinstance(estado, dict) or hasattr(estado, "get") else None
        registro = registro if isinstance(registro, dict) else {}
        self._anterior = registro
        self.cache: Dict[str, Dict[str, Any]] = dict(registro.get("cache") or {})
        self.gate = gate or "sem gate"
        self.limite = LIMITE_POR_GATE if limite is None else limite
        self.chamadas = 0
        self.do_cache = 0
        self.nao_sei = 0
        self.novas = 0
        self.tokens = {"entrada": 0, "saida": 0, "pensamento": 0}
        self.usd = 0.0
        self._lock = threading.Lock()

    def _reservar_chamada(self) -> bool:
        with self._lock:
            if self.chamadas >= self.limite:
                return False
            self.chamadas += 1
            return True

    def _contar(self, leitura: Leitura, tokens: Optional[Dict[str, int]] = None, usd: float = 0.0) -> None:
        with self._lock:
            if leitura.origem in ("sessao", "cache_de_teste"):
                self.do_cache += 1
            if leitura.nao_sei:
                self.nao_sei += 1
            for k, v in (tokens or {}).items():
                self.tokens[k] = self.tokens.get(k, 0) + int(v or 0)
            self.usd += usd

    def _guardar(self, h: str, registro: Dict[str, Any]) -> None:
        with self._lock:
            self.cache.pop(h, None)
            self.cache[h] = registro
            self.novas += 1

    def registro(self) -> Optional[Dict[str, Any]]:
        """O valor novo de `estado[KEY]`, ou `None` se o gate não chamou o modelo nem guardou leitura nova.

        O `state_delta` troca a chave inteira (até `MAX_ENTRADAS` leituras, ~125 KB): o gate que só leu do cache — ou só
        ganhou «nao_sei» sem chamar (sem chave, desligado, fora do cache de teste) — não a regrava a cada passagem, e
        os contadores dele (`do_cache`, `nao_sei`) ficam fora do custo. Revisão do PR #85 (25/10/2026)."""
        if not (self.chamadas or self.novas):
            return None
        cache = dict(list(self.cache.items())[-MAX_ENTRADAS:])
        custo = dict(self._anterior.get("custo") or {})
        tokens = {k: int((custo.get("tokens") or {}).get(k, 0) or 0) + self.tokens.get(k, 0)
                  for k in ("entrada", "saida", "pensamento")}
        por_gate = dict(custo.get("por_gate") or {})
        g = dict(por_gate.get(self.gate) or {})
        g.update({"chamadas": int(g.get("chamadas", 0)) + self.chamadas,
                  "do_cache": int(g.get("do_cache", 0)) + self.do_cache,
                  "nao_sei": int(g.get("nao_sei", 0)) + self.nao_sei,
                  "usd": round(float(g.get("usd", 0.0)) + self.usd, 6),
                  "ultima": time.strftime("%d/%m/%Y %H:%M")})
        por_gate[self.gate] = g
        return {"descricao": "Leituras do classificador de sentido (tools/classificador.py), pelo hash da pergunta, "
                             "versão, modelo e entrada; e o custo das chamadas por gate.",
                "cache": cache,
                "custo": {"chamadas": int(custo.get("chamadas", 0) or 0) + self.chamadas, "tokens": tokens,
                          "usd": round(float(custo.get("usd", 0.0) or 0.0) + self.usd, 6), "por_gate": por_gate}}

    def delta(self) -> Dict[str, Any]:
        """`{KEY: registro}` para o `state_delta` do gate; vazio se nada mudou."""
        r = self.registro()
        return {KEY: r} if r is not None else {}


_SESSAO: ContextVar[Optional[Sessao]] = ContextVar("classificador_sessao", default=None)


def abrir(estado: Optional[Dict[str, Any]], gate: str) -> Tuple[Sessao, Any]:
    """Abre a sessão do gate: as leituras de dentro dele usam o cache do estado e contam no custo do gate. Devolve
    `(sessao, token)`; o gate chama `fechar(token)` antes de emitir o evento e soma `sessao.delta()` ao `state_delta`."""
    s = Sessao(estado, gate)
    return s, _SESSAO.set(s)


def fechar(token: Any) -> None:
    _SESSAO.reset(token)


@contextmanager
def sessao(estado: Optional[Dict[str, Any]], gate: str) -> Iterator[Sessao]:
    s, token = abrir(estado, gate)
    try:
        yield s
    finally:
        fechar(token)


# ------------------------------------------------------------------ o modelo
_CLIENTES: Dict[str, Any] = {}


def _cliente(chave_api: str) -> Any:
    from google import genai
    from google.genai import types

    from config import get_settings

    h = hashlib.sha256(chave_api.encode("utf-8")).hexdigest()  # a chave não fica como chave do dicionário
    if h not in _CLIENTES:
        tentativas = max(1, int(get_settings().tentativas_modelo))
        opcoes = types.HttpOptions(timeout=TIMEOUT_S * 1000, retry_options=types.HttpRetryOptions(
            attempts=tentativas, initial_delay=1.0, max_delay=30.0, exp_base=2.0, jitter=1.0,
            http_status_codes=[408, 429, 500, 502, 503, 504]) if tentativas > 1 else None)
        _CLIENTES[h] = genai.Client(api_key=chave_api, http_options=opcoes)
    return _CLIENTES[h]


def _chamar_modelo(pergunta: Pergunta, prompt: str, modelo: str) -> Tuple[str, Dict[str, int]]:
    """`(texto da resposta, tokens)`. Os parâmetros são os do juiz determinístico (`agents/base.py`, `deterministico`)."""
    from google.genai import types

    from config import get_settings

    settings = get_settings()
    schema = {
        "type": "object",
        "properties": {
            "rotulo": {"type": "string", "enum": pergunta.rotulos_com_nao_sei},
            "citacao": {"type": "string",
                        "description": "trecho copiado letra por letra da ENTRADA que justifica o rótulo"},
        },
        "required": ["rotulo", "citacao"],
        "propertyOrdering": ["citacao", "rotulo"],
    }
    cfg = types.GenerateContentConfig(
        temperature=settings.temperatura_juiz, seed=settings.seed_juiz,
        response_mime_type="application/json", response_schema=schema,
        thinking_config=types.ThinkingConfig(thinking_budget=settings.thinking_budget),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    resp = _cliente(settings.google_api_key).models.generate_content(model=modelo, contents=prompt, config=cfg)
    um = getattr(resp, "usage_metadata", None)
    tokens = {"entrada": int(getattr(um, "prompt_token_count", 0) or 0),
              "saida": int(getattr(um, "candidates_token_count", 0) or 0),
              "pensamento": int(getattr(um, "thoughts_token_count", 0) or 0)}
    return (getattr(resp, "text", "") or "").strip(), tokens


def _interpretar(pergunta: Pergunta, bruto: str, entrada_texto: str) -> Leitura:
    try:
        dado = json.loads(bruto)
    except ValueError:
        return Leitura(NAO_SEI, "", "modelo", "resposta sem JSON")
    if not isinstance(dado, dict):
        return Leitura(NAO_SEI, "", "modelo", "resposta sem JSON")
    rotulo = str(dado.get("rotulo") or NAO_SEI)
    citacao = str(dado.get("citacao") or "")
    if rotulo not in pergunta.rotulos_com_nao_sei:
        return Leitura(NAO_SEI, citacao, "modelo", f"rótulo fora da lista: {rotulo[:40]}")
    if rotulo != NAO_SEI and not citacao_confere(citacao, entrada_texto):
        # a citação é a prova: sem ela no trecho, o rótulo não vale (na fase A, a 3ª rodada com temperatura 1,0 teve 4
        # citações que não conferiam, e aqui viraram «nao_sei»)
        return Leitura(NAO_SEI, citacao, "modelo", "a citação não está no trecho")
    return Leitura(rotulo, citacao, "modelo", "")


def _ler_um(pergunta: Pergunta, entrada: Dict[str, Any], sessao_: Sessao, modelo: str) -> Leitura:
    from config import get_settings

    texto = pergunta.montar(entrada)
    modo = _modo()
    if modo == "desligado":
        leitura = Leitura(NAO_SEI, "", "sem_resposta", "classificador desligado")
        sessao_._contar(leitura)
        return leitura
    h = chave(pergunta, texto, modelo)
    guardado = sessao_.cache.get(h) or _cache_fixo().get(h)
    if guardado:
        leitura = Leitura(str(guardado.get("r") or NAO_SEI), str(guardado.get("c") or ""),
                          "sessao" if h in sessao_.cache else "cache_de_teste")
        if h not in sessao_.cache:
            sessao_._guardar(h, guardado)
        sessao_._contar(leitura)
        return leitura
    gravar_fixo = os.getenv(ENV_GRAVAR_CACHE_FIXO, "").strip().lower() in ("1", "true", "sim")
    if modo == "so_cache" and not gravar_fixo:
        leitura = Leitura(NAO_SEI, "", "sem_resposta", "fora do cache")
        sessao_._contar(leitura)
        return leitura
    if not get_settings().is_gemini_configured():
        leitura = Leitura(NAO_SEI, "", "sem_resposta", "sem chave do modelo")
        sessao_._contar(leitura)
        return leitura
    if not sessao_._reservar_chamada():
        leitura = Leitura(NAO_SEI, "", "sem_resposta", f"limite de {sessao_.limite} chamadas do gate")
        sessao_._contar(leitura)
        return leitura
    try:
        bruto, tokens = _chamar_modelo(pergunta, pergunta.prompt(texto), modelo)
    except Exception as exc:  # noqa: BLE001 — erro, timeout ou cota: «nao_sei», nunca derruba a esteira
        # só o tipo: a mensagem de erro do cliente pode trazer a requisição
        logger.warning("classificador %s: %s", pergunta.id, type(exc).__name__)
        leitura = Leitura(NAO_SEI, "", "sem_resposta", f"erro do modelo ({type(exc).__name__})")
        sessao_._contar(leitura)
        return leitura
    from tools.custo import custo_usd

    leitura = _interpretar(pergunta, bruto, texto)
    sessao_._contar(leitura, tokens, custo_usd(tokens, modelo) or 0.0)
    if not leitura.motivo:  # a resposta do modelo, conferida (o erro e a citação que não confere não ficam)
        registro = {"p": pergunta.id, "v": pergunta.versao, "r": leitura.rotulo, "c": leitura.citacao[:MAX_CITACAO]}
        sessao_._guardar(h, registro)
        if gravar_fixo:
            _gravar_no_fixo(h, registro)
    return leitura


def ler(pergunta: Pergunta, entradas: Sequence[Dict[str, Any]]) -> List[Leitura]:
    """As leituras de `entradas`, na ordem. O que não está no cache vai ao modelo em paralelo (`PARALELO`), dentro do
    limite do gate. Sem sessão aberta, a leitura usa uma sessão só dela (sem estado, sem custo registrado)."""
    from config import get_settings

    if not entradas:
        return []
    sessao_ = _SESSAO.get() or Sessao(None, "sem gate")
    modelo = get_settings().gemini_model
    if len(entradas) == 1:
        return [_ler_um(pergunta, entradas[0], sessao_, modelo)]
    with ThreadPoolExecutor(max_workers=min(PARALELO, len(entradas))) as ex:
        return list(ex.map(lambda e: _ler_um(pergunta, e, sessao_, modelo), entradas))


# ------------------------------------------------------------------ uma função por pergunta
def numero_da_hipotese(hipotese_no_documento: str, hipotese_aprovada_no_17: str, numero: str) -> Leitura:
    """`meta` · `mecanica` · `nao_sei`: o NÚMERO é o critério da hipótese ou um parâmetro que ela cita?"""
    return ler(NUMERO_DA_HIPOTESE, [{"hipotese_no_documento": hipotese_no_documento,
                                     "hipotese_aprovada_no_17": hipotese_aprovada_no_17, "numero": numero}])[0]


def rotulo_de_botao(documento: str, linha: str, candidato: str, cabecalho_da_tabela: str = "") -> Leitura:
    """`rotulo_de_botao` · `outro` · `nao_sei`: o CANDIDATO, recortado da LINHA, é o texto de um botão?"""
    return ler(ROTULO_DE_BOTAO, [{"documento": documento, "cabecalho_da_tabela": cabecalho_da_tabela, "linha": linha,
                                  "candidato": candidato}])[0]


def item_do_pedido_classe(item: str, linhas_anteriores_no_pedido: str = "") -> Leitura:
    """`exigencia` · `preservacao` · `contexto` · `texto_da_esteira` · `nao_sei`: o que o ITEM do pedido pede?"""
    return ler(ITEM_DO_PEDIDO_CLASSE, [{"item": item, "linhas_anteriores_no_pedido": linhas_anteriores_no_pedido}])[0]


def decisao_do_po_confirmada(documento: str, linha: str, registros_do_po: str) -> Leitura:
    """`confirmada` · `nao_confirmada` · `nao_sei`: algum registro do PO decide o que a LINHA atribui a ele?"""
    return ler(DECISAO_DO_PO_CONFIRMADA, [{"documento": documento, "linha": linha,
                                           "registros_do_po": registros_do_po}])[0]


def ressalva_repete_decisao_do_po(ressalva: str, registros_do_po: str) -> Leitura:
    """`repete_decisao_do_po` · `aponta_problema` · `nao_sei`: a ressalva só repete a decisão do PO?"""
    return ler(RESSALVA_REPETE_DECISAO_DO_PO, [{"ressalva": ressalva, "registros_do_po": registros_do_po}])[0]


def alteracao_po_autorizada(alteracao_declarada: str, registros_do_po: str) -> Leitura:
    """`autorizada` · `sem_pedido` · `nao_sei`: os registros/votos autorizam a alteração declarada na tabela?"""
    return ler(ALTERACAO_PO_AUTORIZADA, [{"alteracao_declarada": alteracao_declarada,
                                          "registros_do_po": registros_do_po}])[0]


def gesto_equivalente_ficha(gesto: str) -> Leitura:
    """`equivalente` · `invalido` · `nao_sei`: o gesto descrito equivale a um dos 12 gestos canônicos?"""
    return ler(GESTO_EQUIVALENTE_FICHA, [{"gesto": gesto}])[0]


def papel_equivalente_glossario(candidato: str, papel_canonico: str, linha: str) -> Leitura:
    """`compativel` · `contradiz` · `nao_sei`: o papel na linha é compatível com o glossário?"""
    return ler(PAPEL_EQUIVALENTE_GLOSSARIO, [{"candidato": candidato, "papel_canonico": papel_canonico,
                                              "linha": linha}])[0]


def aspas_conceito_ou_fala(linha: str, candidato: str) -> Leitura:
    """`termo_ou_conceito` · `fala_de_tela` · `nao_sei`: o trecho entre aspas é conceito/termo ou fala reescrita?"""
    return ler(ASPAS_CONCEITO_OU_FALA, [{"linha": linha, "candidato": candidato}])[0]


# ------------------------------------------------------------------ os registros do PO, como a fase A os mediu
def _palavras(texto: str) -> List[str]:
    return re.findall(r"[a-záàâãéêíóôõúç0-9]{4,}", (texto or "").lower())


def registros_do_po(estado: Dict[str, Any], linha_alvo: str = "") -> str:
    """O que o PO escreveu na sessão, numerado como a esteira numera («Pedido N»): os pedidos de refazer, os pareceres
    com comentário que não são refazer, as decisões gravadas no cartão do de acordo e, do one-pager que o PO anexou, só
    as 6 linhas que dividem 3+ palavras de conteúdo com a linha em exame (o anexo tem até 65 mil caracteres). É a entrada
    que a fase A mediu (`c7/casos/comum.py`), até 60 mil caracteres."""
    partes: List[str] = []
    for i, p in enumerate(estado.get("pedidos_do_po") or [], 1):
        if isinstance(p, dict):
            partes.append(f"### Pedido {i} · {p.get('origem', '')}\n{p.get('texto', '')}")
    for p in estado.get("pareceres_humanos") or []:
        if not isinstance(p, dict) or p.get("acao") == "refazer" or not str(p.get("comentario") or "").strip():
            continue
        partes.append(f"### Parecer {p.get('acao')} · {p.get('etapa')} · {p.get('quando')}\n{p.get('comentario')}")
    for d in estado.get("decisoes_do_po") or []:
        partes.append("### Decisão gravada no de acordo\n" + json.dumps(d, ensure_ascii=False))
    anexo = str(estado.get("one_pager_po") or "")
    if anexo and linha_alvo:
        alvo = set(_palavras(linha_alvo))
        pont = sorted(((len(alvo & set(_palavras(l))), l) for l in anexo.splitlines() if l.strip()), reverse=True)
        linhas = [l for n, l in pont[:6] if n >= 3]
        if linhas:
            partes.append("### One-pager anexado pelo PO (linhas mais próximas)\n" + "\n".join(linhas))
    texto = "\n\n".join(partes)
    return texto[:60000] if texto else "(a sessão não tem nenhum registro do PO)"


def custo_da_sessao(estado: Dict[str, Any]) -> Dict[str, Any]:
    """O custo acumulado do classificador no estado: `{chamadas, tokens, usd, por_gate}` (vazio sem leitura)."""
    registro = estado.get(KEY) if isinstance(estado, dict) else None
    return dict((registro or {}).get("custo") or {}) if isinstance(registro, dict) else {}
