"""O esquema real da plataforma: tabelas, colunas e tipos depois de aplicar todas as migrations em ordem.

Fonte dos tipos que o PRD tem de seguir (plano padrão ouro, 2.2 e 4.1). Até 12/10/2026 a única referência era
a migration da Júri e uma lista fixa de três colunas; uma chave estrangeira para outra tabela, ou uma tabela de
missão já publicada, não tinha contra o que ser conferida.

`ler_migrations(sql)` é puro (o SQL das migrations concatenadas na ordem do nome da pasta); o extrator
`scripts/extrair_fichas_plataforma.py` grava o resultado em `references/plataforma/fichas-tecnicas.json`, e
`carregar()` o lê para os gates.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple

ARQUIVO_FICHAS = Path(__file__).resolve().parent.parent / "references" / "plataforma" / "fichas-tecnicas.json"

_NOME = r'"?(\w+)"?'
_ESQUEMA = r'(?:"?public"?\.)?'
_RE_CREATE = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?" + _ESQUEMA + _NOME + r"\s*\((.*?)\)\s*;",
                        re.S | re.I)
_RE_ALTER = re.compile(r"ALTER\s+TABLE\s+(?:ONLY\s+)?(?:IF\s+EXISTS\s+)?" + _ESQUEMA + _NOME + r"\s+(.*?);",
                       re.S | re.I)
_RE_DROP_TABLE = re.compile(r"DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?" + _ESQUEMA + _NOME, re.I)
_RE_FK = re.compile(r"FOREIGN\s+KEY\s*\(\s*" + _NOME + r"\s*\)\s*REFERENCES\s+" + _ESQUEMA + _NOME
                    + r"\s*\(\s*" + _NOME, re.I)
_RE_REF_INLINE = re.compile(r"REFERENCES\s+" + _ESQUEMA + _NOME + r"\s*\(\s*" + _NOME, re.I)
_RE_TIPO_COL = re.compile(r"^\s*" + _NOME + r"\s+(\w+(?:\s*\(\s*\d+(?:\s*,\s*\d+)?\s*\))?(?:\s*\[\])?)", re.I)
_RESERVADAS = {"constraint", "primary", "unique", "foreign", "check", "exclude", "like"}


def _sem_comentarios(sql: str) -> str:
    return re.sub(r"--[^\n]*", "", re.sub(r"/\*.*?\*/", "", sql or "", flags=re.S))


def _partes(corpo: str) -> Iterator[str]:
    """Itens separados por vírgula de nível zero (vírgula dentro de parênteses não separa)."""
    nivel, atual = 0, []
    for ch in corpo:
        if ch == "(":
            nivel += 1
        elif ch == ")":
            nivel -= 1
        if ch == "," and nivel == 0:
            yield "".join(atual)
            atual = []
        else:
            atual.append(ch)
    if "".join(atual).strip():
        yield "".join(atual)


def _coluna(cols: Dict[str, str], fks: Dict[str, Tuple[str, str]], item: str) -> bool:
    c = _RE_TIPO_COL.match(item)
    if not c or c.group(1).lower() in _RESERVADAS:
        return False
    cols[c.group(1).lower()] = c.group(2).upper()
    ref = _RE_REF_INLINE.search(item)
    if ref:
        fks[c.group(1).lower()] = (ref.group(1).lower(), ref.group(2).lower())
    return True


def ler_migrations(sql: str) -> Tuple[Dict[str, Dict[str, str]], Dict[str, Dict[str, Tuple[str, str]]]]:
    """`(tabelas, fks)`: `{tabela: {coluna: TIPO}}` e `{tabela: {coluna: (alvo, coluna_alvo)}}`."""
    tabelas: Dict[str, Dict[str, str]] = {}
    fks: Dict[str, Dict[str, Tuple[str, str]]] = {}
    texto = _sem_comentarios(sql)
    eventos = sorted([(m.start(), "create", m) for m in _RE_CREATE.finditer(texto)]
                     + [(m.start(), "alter", m) for m in _RE_ALTER.finditer(texto)]
                     + [(m.start(), "drop", m) for m in _RE_DROP_TABLE.finditer(texto)], key=lambda e: e[0])
    for _, tipo, m in eventos:
        tabela = m.group(1).lower()
        if tipo == "drop":
            tabelas.pop(tabela, None)
            fks.pop(tabela, None)
            continue
        if tipo == "create":
            cols: Dict[str, str] = {}
            refs = fks.setdefault(tabela, {})
            for item in _partes(m.group(2)):
                fk = _RE_FK.search(item)
                if fk:
                    refs[fk.group(1).lower()] = (fk.group(2).lower(), fk.group(3).lower())
                    continue
                _coluna(cols, refs, item.strip())
            tabelas[tabela] = cols
            continue
        acao = m.group(2).strip()
        nova = re.match(r"RENAME\s+TO\s+" + _NOME, acao, re.I)
        if nova:
            tabelas[nova.group(1).lower()] = tabelas.pop(tabela, {})
            fks[nova.group(1).lower()] = fks.pop(tabela, {})
            continue
        cols = tabelas.setdefault(tabela, {})
        refs = fks.setdefault(tabela, {})
        for item in _partes(acao):
            s = item.strip()
            fk = _RE_FK.search(s)
            if fk:
                refs[fk.group(1).lower()] = (fk.group(2).lower(), fk.group(3).lower())
                continue
            add = re.match(r"ADD\s+(?:COLUMN\s+)?(?:IF\s+NOT\s+EXISTS\s+)?(.*)$", s, re.I | re.S)
            if add:
                if not re.match(r"(?:CONSTRAINT|PRIMARY|UNIQUE|CHECK|EXCLUDE)\b", add.group(1), re.I):
                    _coluna(cols, refs, add.group(1))
                continue
            mudou = re.match(r"ALTER\s+(?:COLUMN\s+)?" + _NOME + r"\s+(?:SET\s+DATA\s+)?TYPE\s+(\w+(?:\s*\([^)]*\))?)",
                             s, re.I)
            if mudou:
                cols[mudou.group(1).lower()] = mudou.group(2).upper()
                continue
            saiu = re.match(r"DROP\s+(?:COLUMN\s+)?(?:IF\s+EXISTS\s+)?" + _NOME, s, re.I)
            if saiu and saiu.group(1).lower() not in ("constraint", "not", "default"):
                cols.pop(saiu.group(1).lower(), None)
                refs.pop(saiu.group(1).lower(), None)
                continue
            renomeou = re.match(r"RENAME\s+(?:COLUMN\s+)?" + _NOME + r"\s+TO\s+" + _NOME, s, re.I)
            if renomeou and renomeou.group(1).lower() in cols:
                cols[renomeou.group(2).lower()] = cols.pop(renomeou.group(1).lower())
    return tabelas, {t: r for t, r in fks.items() if r}


_CACHE: Dict[str, Any] = {}


def carregar(caminho: Optional[Path] = None) -> Dict[str, Any]:
    """O conteúdo de `fichas-tecnicas.json` (`{}` se não existir: o gate cai na lista mínima do núcleo)."""
    alvo = Path(caminho) if caminho else ARQUIVO_FICHAS
    if str(alvo) not in _CACHE:
        try:
            _CACHE[str(alvo)] = json.loads(alvo.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            _CACHE[str(alvo)] = {}
    return _CACHE[str(alvo)]


def tabelas(caminho: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    return carregar(caminho).get("tabelas_plataforma") or {}


def chaves_estrangeiras(caminho: Optional[Path] = None) -> Dict[str, Dict[str, list]]:
    return carregar(caminho).get("chaves_estrangeiras") or {}
