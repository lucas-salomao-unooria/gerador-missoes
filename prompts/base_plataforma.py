"""A base da plataforma e do design system que a esteira lê — no bucket, não no git.

Até 06/10/2026 o retrato da plataforma era uma cópia em `prompts/references/plataforma/`, feita à mão
por `scripts/sincronizar_plataforma.py`. Ela parou em 16/09 (commit 29afc8f) e ficou 320 commits atrás
sem ninguém ver: a missão do 9º ano saiu pedindo a seção `chatgpt`, a ADR-108 "proposta" (a última era
a 148) e o DS 0.2.2 (era o 0.2.18). O inventário do DS tinha as marcas fixas no código e nunca viu
`unooriaai`, `unoovista` nem `unoochat`.

Agora quem conhece a plataforma a publica:

- o CI da plataforma, a cada push em `dev-local`, grava `plataforma/<commit>/` e só depois troca
  `plataforma/atual.json` (`scripts/base-do-gerador/extrair.mjs`);
- o CI do storybook, a cada versão publicada, grava `design-system/<versao>/` e
  `design-system/atual.json` (`scripts/inventario-para-o-gerador.mjs`).

Os dois escrevem em `gs://entre-redes-dev-base-plataforma`, um bucket só da base, que o Cloud Run do
gerador monta **só para leitura** em `/app/base-plataforma` (`BASE_PLATAFORMA_DIR`). Até 07/10/2026 ela
morava em `base-plataforma/` do bucket das sessões: a barra lateral a listava como missão e o botão de
excluir a apagou duas vezes. Sem `BASE_PLATAFORMA_DIR`, a base é `<OUTPUT_DIR>/base-plataforma` — o
caminho local, baixado do bucket ou gerado pelos dois scripts com `--saida` (o README diz como).

**Uma execução lê uma base só.** `run_orchestrator_pipeline_stream` chama `fixar(ler_atual())` antes de
montar os agentes; os prompts são expandidos nessa hora e os verificadores que leem arquivo durante a
execução (`tools/componentes_ds.py`, `tools/rotas_plataforma.py`) consultam a mesma base fixada. Um
merge na `dev-local` no meio da execução não muda nada nela. O commit e a versão do DS vão para o
estado e para o cabeçalho do diagnóstico.

**Sem base, a execução não começa.** Cair numa cópia velha em silêncio foi exatamente o que aconteceu.
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

#: Prefixo virtual dos includes das cópias da plataforma: `<!-- include: references/plataforma/x.md -->`.
PREFIXO_PLATAFORMA = "references/plataforma/"
#: Includes gerados na hora a partir dos JSONs da base.
INCLUDE_CONTRATO = "references/plataforma/contrato-plataforma.md"
INCLUDE_DS = "references/ds-componentes.md"

#: Um par de chaves sem chave dentro. Quem decide se ele vira variável é `_o_adk_interpolaria`, com o critério do ADK.
_VAR = re.compile(r"\{([^{}]*)\}")
_PREFIXOS_DE_ESTADO = ("app", "user", "temp")


class BaseIndisponivel(RuntimeError):
    """A base da plataforma ou do DS não está onde deveria. A mensagem diz onde procurou e o que fazer."""


@dataclass(frozen=True)
class Base:
    raiz: Path
    commit: str
    branch: str
    data_commit: str
    gerado_em: str
    pasta_plataforma: Path
    ds_versao: str
    ds_commit: str
    pasta_ds: Path

    @property
    def assinatura(self) -> str:
        """Chave de cache: muda quando a plataforma ou o DS mudam."""
        return f"{self.commit}|{self.ds_versao}"

    def resumo(self) -> str:
        return (f"Base da plataforma: plataforma-unooria@{self.commit} ({self.branch}, {self.data_commit}) · "
                f"design system {self.ds_versao} (storybook-unooria@{self.ds_commit})")

    def para_estado(self) -> Dict[str, str]:
        return {"base_plataforma_commit": self.commit, "base_plataforma_data": self.data_commit,
                "base_plataforma_branch": self.branch, "ds_versao": self.ds_versao}


def _o_adk_interpolaria(nome: str) -> bool:
    """O critério de `google.adk.utils.instructions_utils._is_valid_state_name`, mais `artifact.`: `str.isidentifier`
    aceita acento. Até 26/10/2026 a troca só via ASCII, e o `{espaço}` do `openapi-indice.md` (plataforma@74755cfa)
    derrubou a banca de produto da exp03ef1b com «Context variable not found»."""
    if nome.startswith("artifact."):
        return True
    prefixo, _, resto = nome.rpartition(":")
    return resto.isidentifier() and prefixo in ("", *_PREFIXOS_DE_ESTADO)


def neutralizar_chaves(texto: str) -> str:
    """`{turmaId}` → `«turmaId»`. O ADK interpolaria a forma original como variável de estado e
    derrubaria o agente em execução. As cópias chegam cruas do bucket; a troca é feita aqui, na carga."""
    def _troca(m: re.Match[str]) -> str:
        nome = m.group(1).strip().removesuffix("?")
        return f"«{nome}»" if _o_adk_interpolaria(nome) else m.group()

    return _VAR.sub(_troca, texto)


def diretorio_base() -> Path:
    explicito = os.getenv("BASE_PLATAFORMA_DIR", "").strip()
    if explicito:
        return Path(explicito)
    from config import get_settings  # import tardio: config não pode depender de prompts

    return get_settings().output_path / "base-plataforma"


def _ler_json(caminho: Path) -> Dict[str, Any]:
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise BaseIndisponivel(
            f"não encontrei {caminho}. A base da plataforma é publicada no bucket pelo CI da plataforma "
            f"(push em dev-local) e do storybook (versão publicada). Localmente: "
            f"`gcloud storage rsync -r gs://entre-redes-dev-base-plataforma output/base-plataforma`, "
            f"ou aponte BASE_PLATAFORMA_DIR para uma base gerada com `--saida` (veja o README)."
        ) from None
    except json.JSONDecodeError as exc:
        raise BaseIndisponivel(f"{caminho} não é JSON válido ({exc})") from None


def ler_atual(raiz: Optional[Path] = None) -> Base:
    """Lê os dois ponteiros (`atual.json`) e confere que as pastas apontadas existem e estão completas."""
    raiz = Path(raiz) if raiz else diretorio_base()
    plat = _ler_json(raiz / "plataforma" / "atual.json")
    ds = _ler_json(raiz / "design-system" / "atual.json")
    pasta_plat = raiz / str(plat.get("pasta") or "").strip("/")
    pasta_ds = raiz / str(ds.get("pasta") or "").strip("/")
    for pasta, nome in ((pasta_plat, "plataforma"), (pasta_ds, "design-system")):
        if pasta == raiz or not pasta.is_dir():
            raise BaseIndisponivel(f"o atual.json de {nome} aponta para {pasta}, que não existe")
    for exigido in (pasta_plat / "contrato-plataforma.json", pasta_plat / "openapi-rotas.json",
                    pasta_ds / "ds-componentes.json"):
        if not exigido.exists():
            raise BaseIndisponivel(f"falta {exigido} — base pela metade?")
    return Base(
        raiz=raiz,
        commit=str(plat.get("commit") or "?"),
        branch=str(plat.get("branch") or "?"),
        data_commit=str(plat.get("data_commit") or "?"),
        gerado_em=str(plat.get("gerado_em") or "?"),
        pasta_plataforma=pasta_plat,
        ds_versao=str(ds.get("versao") or "?"),
        ds_commit=str(ds.get("commit") or "?"),
        pasta_ds=pasta_ds,
    )


# --------------------------------------------------------------------------- base da execução
#: Cada execução roda na própria thread (`pipeline/execucao_fundo.py`), com o próprio event loop.
_fixada = threading.local()
_ultima_lida: Dict[str, Any] = {"quando": 0.0, "base": None}
_TTL_SEM_FIXAR = 5.0


def fixar(base: Optional[Base]) -> None:
    """Fixa (ou solta, com `None`) a base desta thread — a execução inteira lê a mesma."""
    _fixada.base = base


def ativa() -> Base:
    """A base fixada nesta thread; fora de execução (editor de prompts, testes), a atual da pasta.

    Fora de execução a leitura dos ponteiros fica em cache por alguns segundos: a construção dos ~40
    agentes resolve centenas de includes em sequência.
    """
    base = getattr(_fixada, "base", None)
    if base is not None:
        return base
    agora = time.monotonic()
    if _ultima_lida["base"] is not None and agora - _ultima_lida["quando"] < _TTL_SEM_FIXAR:
        return _ultima_lida["base"]
    base = ler_atual()
    _ultima_lida.update(quando=agora, base=base)
    return base


def esquecer_cache() -> None:
    _ultima_lida.update(quando=0.0, base=None)


# --------------------------------------------------------------------------- leitura
def arquivo_plataforma(nome: str, base: Optional[Base] = None) -> Path:
    """Caminho de uma cópia (`agents-raiz.md`, `regras-design-system.md`...) na base."""
    base = base or ativa()
    caminho = base.pasta_plataforma / "arquivos" / nome
    if not caminho.exists():
        raise BaseIndisponivel(
            f"a base da plataforma ({base.commit}) não tem `{nome}`. Ou a plataforma deixou de publicá-lo "
            f"(confira scripts/base-do-gerador/extrair.mjs na plataforma) ou o prompt inclui um nome antigo."
        )
    return caminho


def contrato(base: Optional[Base] = None) -> Dict[str, Any]:
    base = base or ativa()
    return _ler_json(base.pasta_plataforma / "contrato-plataforma.json")


def rotas(base: Optional[Base] = None) -> Dict[str, Any]:
    base = base or ativa()
    return _ler_json(base.pasta_plataforma / "openapi-rotas.json")


def ds_componentes(base: Optional[Base] = None) -> Dict[str, Any]:
    base = base or ativa()
    return _ler_json(base.pasta_ds / "ds-componentes.json")


def _normalizar(rel: str) -> str:
    return rel if rel.endswith(".md") else f"{rel}.md"


def eh_da_base(rel: str) -> bool:
    rel = _normalizar(rel)
    return rel == INCLUDE_DS or rel.startswith(PREFIXO_PLATAFORMA)


def ler_include(rel: str) -> str:
    """Conteúdo de um include que mora na base (`eh_da_base(rel)` verdadeiro).

    `references/plataforma/contrato-plataforma.md` e `references/ds-componentes.md` são gerados na hora
    a partir dos JSONs; o resto de `references/plataforma/` é a cópia publicada pela plataforma.
    """
    rel = _normalizar(rel)
    # o contrato e o inventário também trazem texto da plataforma (descrições, exemplos de rota)
    if rel == INCLUDE_DS:
        return neutralizar_chaves(render_ds_componentes(ds_componentes()))
    if rel == INCLUDE_CONTRATO:
        base = ativa()
        return neutralizar_chaves(render_contrato(contrato(base), base))
    if rel.startswith(PREFIXO_PLATAFORMA):
        nome = rel[len(PREFIXO_PLATAFORMA):]
        return neutralizar_chaves(arquivo_plataforma(nome).read_text(encoding="utf-8"))
    raise ValueError(f"{rel} não é da base da plataforma")


def listar_copias(base: Optional[Base] = None) -> List[str]:
    """Nomes das cópias da base, para o visualizador de referências."""
    base = base or ativa()
    return sorted(p.name for p in (base.pasta_plataforma / "arquivos").glob("*.md"))


# --------------------------------------------------------------------------- renderização
def render_ds_componentes(dados: Dict[str, Any]) -> str:
    """O que os prompts de telas e de ambiente incluem: os nomes que existem, por seção."""
    marcas = dados.get("marcas") or {}
    linhas = [
        f"<!-- GERADO da base: storybook-unooria@{dados.get('commit', '?')} ({dados.get('data_commit', '?')}, "
        f"{dados.get('pacote', '?')} {dados.get('versao', '?')}) · não edite -->",
        "",
        "## Componentes que existem no design system, por seção",
        "",
        "Só estes nomes vão na coluna **Componentes do DS**. O que não está aqui é **componente local** "
        "(coluna própria, registrado como candidato), nunca \"do DS\". Todo componente da marca `unooria` "
        "vale em qualquer seção.",
        "",
    ]
    mapa = dados.get("secao_para_marca") or {}
    if mapa:
        linhas += ["Nome antigo da seção (missão antiga) → pasta no DS: "
                   + " · ".join(f"`{s}` → `{m}`" for s, m in sorted(mapa.items())), ""]
    for marca, nomes in sorted(marcas.items()):
        linhas.append(f"**`{marca}`** ({len(nomes)}): " + " · ".join(f"`{n}`" for n in nomes))
        linhas.append("")
    return "\n".join(linhas)


def _numero_adr(chave: str) -> int:
    return int(re.sub(r"\D", "", chave) or 0)


def render_contrato(c: Dict[str, Any], base: Optional[Base] = None) -> str:
    """As listas fechadas da plataforma, em Markdown, para o prompt. Extraídas do código pela plataforma;
    nada aqui é escrito à mão. O que não estiver aqui não existe na plataforma."""
    ds = c.get("design_system") or {}
    man = c.get("manifesto") or {}
    portas = c.get("portas") or {}
    adr = c.get("adr") or {}
    equipes = c.get("equipes") or {}
    evid = c.get("evidencia") or {}
    ia = c.get("ia") or {}
    origem = f"plataforma-unooria@{c.get('commit', '?')} ({c.get('data_commit', '?')})"
    if base is not None:
        origem += f" · design system {base.ds_versao}"
    linhas = [
        f"<!-- GERADO da base: {origem} · não edite -->",
        "",
        "## Contrato da plataforma (listas fechadas, extraídas do código)",
        "",
        f"Retrato de {origem}. **O que não estiver nestas listas não existe na plataforma**: citar é "
        "erro; propor é `[PENDÊNCIA PLATAFORMA]` com dono.",
        "",
        "### Design system",
        "",
        f"- Versão: **a última publicada** (dependência atual `{ds.get('dependencia', '?')}`; versão única, "
        "ADR-139). Não crave número de versão do DS no documento.",
        "- Pontes em `@edu/ui`: " + " · ".join(f"`{p.get('ponte')}`" for p in ds.get("pontes") or []),
        "",
        "Seções (linha da tabela de `docs/regras/design-system.md`):",
        "",
    ]
    for s in ds.get("secoes") or []:
        linhas.append(f"- `{s.get('secao')}` → `{s.get('ponte', '')}` — {str(s.get('linha', '')).strip()}")
    linhas += [
        "",
        "### Manifesto (`public/experiencia.json`)",
        "",
        "- Chaves aceitas: " + ", ".join(f"`{k}`" for k in man.get("chaves") or []),
        "- `capabilities`: " + ", ".join(f"`{k}`" for k in man.get("capabilities") or []),
        "- `permissoes` do iframe: " + ", ".join(f"`{k}`" for k in man.get("permissoes_iframe") or []),
        "- `publico`: " + ", ".join(f"`{k}`" for k in man.get("publico") or []),
        "",
        "### Experiências existentes e portas de dev",
        "",
        "| Id | Série · unidade | Produto | Versão | Porta |",
        "|---|---|---|---|---|",
    ]
    for e in c.get("experiencias") or []:
        series = ", ".join(e.get("series") or [])
        linhas.append(f"| `{e.get('id')}` | {series} · {e.get('unidade', '')} | {e.get('produto', '')} | "
                      f"{e.get('versao', '')} | {e.get('porta', '')} |")
    linhas += [
        "",
        f"Próxima porta livre: **{portas.get('proxima_livre', '?')}**. Missão nova declara a porta dela.",
        "",
        "### Decisões (ADR)",
        "",
        f"Última ADR: **ADR-{adr.get('ultima', '?')}**. Decisão nova desta missão é a "
        f"**ADR-{adr.get('proxima', '?')}** (o número final é conferido na hora do commit). "
        "Não cite ADR com número fora desta lista, nem com outro título.",
        "",
    ]
    titulos = sorted((adr.get("titulos") or {}).items(), key=lambda kv: _numero_adr(kv[0]), reverse=True)
    for chave, titulo in titulos[:40]:
        linhas.append(f"- {chave}: {titulo}")
    linhas += [
        "",
        "### Equipes, atividades e evidência",
        "",
        "- Missões com equipe: " + ", ".join(f"`{x}`" for x in equipes.get("com_equipe") or []),
        "- Missões com atividade: " + ", ".join(f"`{x}`" for x in equipes.get("com_atividade") or []),
        "- Evidência pedagógica: ficha do módulo genérico `evidencias/`; não crie tabela própria de "
        "enquete nem de nota por missão. Fichas registradas: "
        + ", ".join(f"`{x}`" for x in evid.get("fichas") or []),
        "- Níveis: " + ", ".join(f"`{x}`" for x in evid.get("niveis") or []),
        "",
        "### IA",
        "",
        f"- Modelo padrão do provedor: `{ia.get('modelo_padrao', '?')}` (vem de `VERTEX_MODEL`; não "
        "crave o nome do modelo no documento).",
        "",
    ]
    return "\n".join(linhas)
