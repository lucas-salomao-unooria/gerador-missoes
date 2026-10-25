"""Histórico por rodada dos gates: o relatório e o veredito de cada rodada, não só os da última.

O `estado.json` guarda um valor por chave, e cada rodada de um loop regrava o relatório e o status do gate. A rodada que
reprovou e foi corrigida some — e com ela o porquê. No levantamento de 24/10/2026 isso deixou sem medida a taxa de falso
positivo das rodadas intermediárias:

- produto: o gate estrutural chegou ao teto (rodada 3) em 727a3c2d, 274a2e75, e3980485 e 76d9af6e, e o comitê dos canais
  teve rodada 2 em 4fd72a9a, 76d9af6e e 60cfa7f4, sem nada das rodadas reprovadas no estado;
- design: os achados de cerca de 15 execuções intermediárias (53e011b6 r1–r7, 4fd72a9a r1–r6) só se reconstruíram pelas
  mensagens de commit;
- dev: `prd_rodada = 2` em 10 de 13 execuções, e só o relatório da última rodada ficou.

O runner já vê cada `state_delta` que os gates emitem (`pipeline/runner.py`): aqui ele vira uma linha do tempo por
execução. Os textos dos relatórios ficam só em `historico-gates.json`, na pasta da sessão; o estado guarda o resumo
(`historico_gates`: vereditos, achados, tamanho e hash de cada relatório). O `estado.json` real já tem de 1 a 2,9 MB e é
carregado como estado da sessão do ADK a cada execução: com os textos, até 8 execuções de 400 mil caracteres iam junto
(revisão do PR #83, 25/10/2026). A execução corrente, com os textos, passa do runner ao gravador dos artefatos numa chave
`temp:` (fora do `estado.json`), e o arquivo segue as execuções que o estado lista, pelo `id`. Só entra o
que é de gate: relatórios (`*_report`, `relatorio_*`, `validacao_*`), status (`*_status`, com os achados do envelope) e
contadores de rodada (`*_rodada`). Documento (one-pager, spec, PRD…) não entra — já está nos artefatos e no backup de
cada correção. Relatório igual ao último registrado da mesma chave não se repete. Há teto por relatório, por execução e
no número de execuções guardadas; o que passa do teto é contado, não guardado.

Sessão gravada antes desta correção não tem a chave e é lida como sempre.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional

KEY = "historico_gates"
ARQUIVO = "historico-gates.json"
#: A execução corrente com os textos, do runner ao gravador dos artefatos. `temp:` não entra no `estado.json`.
KEY_EXECUCAO_COMPLETA = "temp:historico_gates_execucao"
#: Teto de caracteres de cada relatório guardado: o relatório do rastro de dev passa de 30 mil, e o que audita o falso
#: positivo é o veredito, os achados e o começo do relatório.
MAX_CARACTERES_RELATORIO = 12_000
#: Teto de caracteres de relatório por execução. Passou, o registro fica sem o texto (com o tamanho e o hash).
MAX_CARACTERES_POR_EXECUCAO = 400_000
#: Teto de registros por execução e de execuções guardadas por sessão (a mais antiga sai primeiro).
MAX_REGISTROS_POR_EXECUCAO = 600
MAX_EXECUCOES = 8
#: Achados guardados por veredito, com os campos que dizem o que o gate acusou e onde.
MAX_ACHADOS = 60
_CAMPOS_DO_ACHADO = ("id", "codigo", "severidade", "severidade_original", "etapa", "agente_responsavel", "dono",
                     "resumo", "citacao", "trecho", "linha_de_base", "citacao_nao_confere", "rota")
_MAX_CAMPO = 400


def e_relatorio(chave: str) -> bool:
    return chave.endswith("_report") or chave.startswith("relatorio_") or chave.startswith("validacao_")


def e_status(chave: str) -> bool:
    return chave.endswith("_status")


def e_rodada(chave: str) -> bool:
    return chave.endswith("_rodada")


def _achados(envelope: Any) -> List[Dict[str, Any]]:
    if not isinstance(envelope, dict):
        return []
    saida = []
    for a in (envelope.get("achados") or [])[:MAX_ACHADOS]:
        if isinstance(a, dict):
            saida.append({c: (str(a[c])[:_MAX_CAMPO] if isinstance(a[c], str) else a[c])
                          for c in _CAMPOS_DO_ACHADO if c in a and a[c] not in (None, "")})
    return saida


class Coletor:
    """Recebe os `state_delta` de uma execução, na ordem, e monta a linha do tempo dela."""

    def __init__(self, stages: Optional[Iterable[str]] = None, estado_inicial: Optional[Dict[str, Any]] = None):
        self.id = uuid.uuid4().hex[:12]
        self.inicio = time.strftime("%d/%m/%Y %H:%M:%S")
        self.stages = [str(s) for s in stages or []]
        self.registros: List[Dict[str, Any]] = []
        self.caracteres = 0
        self.omitidos = 0
        # o hash do último relatório de cada chave: o da execução anterior conta, para o primeiro não repetir o que já
        # estava no estado
        self._ultimo: Dict[str, str] = {}
        for chave, valor in (estado_inicial or {}).items():
            if e_relatorio(str(chave)) and isinstance(valor, str) and valor.strip():
                self._ultimo[str(chave)] = _hash(valor)

    def _registrar(self, registro: Dict[str, Any]) -> None:
        if len(self.registros) >= MAX_REGISTROS_POR_EXECUCAO:
            self.omitidos += 1
            return
        registro["seq"] = len(self.registros) + 1
        self.registros.append(registro)

    def observar(self, autor: str, delta: Optional[Dict[str, Any]]) -> None:
        if not delta:
            return
        quando = time.strftime("%H:%M:%S")
        for chave, valor in delta.items():
            chave = str(chave)
            if chave.startswith("temp:"):
                continue
            if e_relatorio(chave) and isinstance(valor, str) and valor.strip():
                h = _hash(valor)
                if self._ultimo.get(chave) == h:
                    continue
                self._ultimo[chave] = h
                registro: Dict[str, Any] = {"tipo": "relatorio", "chave": chave, "autor": autor, "quando": quando,
                                            "tamanho": len(valor), "hash": h}
                if self.caracteres + min(len(valor), MAX_CARACTERES_RELATORIO) <= MAX_CARACTERES_POR_EXECUCAO:
                    texto = valor[:MAX_CARACTERES_RELATORIO]
                    registro["texto"] = texto
                    registro["cortado"] = len(valor) > MAX_CARACTERES_RELATORIO
                    self.caracteres += len(texto)
                else:
                    registro["texto_omitido"] = "teto de caracteres da execução"
                self._registrar(registro)
            elif e_status(chave) and isinstance(valor, str):
                envelope = delta.get(f"{chave}_envelope")
                registro = {"tipo": "status", "chave": chave, "status": valor, "autor": autor, "quando": quando}
                if isinstance(envelope, dict):
                    registro["envelope_status"] = str(envelope.get("status") or envelope.get("veredito") or "")
                    if envelope.get("veredito_original"):
                        registro["veredito_original"] = envelope.get("veredito_original")
                    registro["achados"] = _achados(envelope)
                self._registrar(registro)
            elif e_rodada(chave) and isinstance(valor, int):
                self._registrar({"tipo": "rodada", "chave": chave, "valor": valor, "autor": autor, "quando": quando})

    def execucao(self) -> Dict[str, Any]:
        saida = {"id": self.id, "inicio": self.inicio, "fim": time.strftime("%d/%m/%Y %H:%M:%S"),
                 "stages": self.stages, "registros": self.registros}
        if self.omitidos:
            saida["registros_omitidos"] = self.omitidos
        return saida


def _hash(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]


def resumo(execucao: Dict[str, Any]) -> Dict[str, Any]:
    """A execução sem os textos dos relatórios, para o estado: o resto (vereditos, achados, tamanho e hash) fica."""
    registros = [{k: v for k, v in r.items() if k != "texto"} for r in execucao.get("registros") or []
                 if isinstance(r, dict)]
    return {**execucao, "registros": registros, "textos_em": ARQUIVO}


def acumular(anterior: Any, execucao: Dict[str, Any]) -> List[Dict[str, Any]]:
    """O histórico da sessão com a execução nova no fim, guardadas as `MAX_EXECUCOES` mais recentes. Execução sem nenhum
    registro não entra (a transversal que só refaz o dossiê, por exemplo, não tem gate)."""
    historico = [e for e in (anterior if isinstance(anterior, list) else []) if isinstance(e, dict)]
    if execucao.get("registros"):
        historico.append(execucao)
    return historico[-MAX_EXECUCOES:]


def rodadas_de(historico: Any, chave_status: str) -> List[Dict[str, Any]]:
    """Os vereditos de um gate em ordem, de todas as execuções guardadas: `[{execucao, status, achados, …}]`."""
    saida = []
    for i, execucao in enumerate(historico if isinstance(historico, list) else [], 1):
        for r in (execucao or {}).get("registros") or []:
            if r.get("tipo") == "status" and r.get("chave") == chave_status:
                saida.append({"execucao": i, **r})
    return saida


def _execucoes_do_arquivo(existente: Optional[str]) -> Dict[str, Dict[str, Any]]:
    try:
        dados = json.loads(existente) if existente else {}
    except ValueError:
        return {}
    execucoes = dados.get("execucoes") if isinstance(dados, dict) else None
    return {str(e["id"]): e for e in execucoes or [] if isinstance(e, dict) and e.get("id")}


def exportar(estado: Dict[str, Any], existente: Optional[str] = None) -> Optional[str]:
    """O conteúdo de `historico-gates.json`, ou `None` sem histórico.

    As execuções são as que o estado lista, na ordem dele; cada uma vem com os textos quando os há — da execução
    corrente (`KEY_EXECUCAO_COMPLETA`) ou do arquivo que já estava na sessão (`existente`). A execução que o estado não
    lista mais (saiu pelo teto, ou um backup restaurado a desfez) sai também do arquivo."""
    historico = estado.get(KEY)
    if not isinstance(historico, list) or not historico:
        return None
    completas = _execucoes_do_arquivo(existente)
    corrente = estado.get(KEY_EXECUCAO_COMPLETA)
    if isinstance(corrente, dict) and corrente.get("id"):
        completas[str(corrente["id"])] = corrente
    historico = [completas.get(str(e.get("id") or ""), e) if isinstance(e, dict) else e for e in historico]
    return json.dumps({"descricao": "Relatórios, vereditos e rodadas de cada gate, por execução, na ordem em que a "
                                    "esteira os gravou (tools/historico_gates.py).",
                       "execucoes": historico}, ensure_ascii=False, indent=1)
