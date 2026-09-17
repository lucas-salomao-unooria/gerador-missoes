"""Toolset MCP que conserta o schema antes de ele chegar ao modelo.

Servidor MCP não é obrigado a publicar schema que um validador aceite, e o do
Stitch publica `$ref` para `$defs` que ele mesmo omite — o SDK oficial dele carrega
um módulo só para remendar isso. Sem o remendo, o ADK entrega o schema cru ao
Gemini e a requisição inteira volta com 400:

    reference to undefined schema at properties.variantScreenInstance

O erro aparece no agente que **está no ar quando a lista de ferramentas é montada**,
que pode não ser o agente que usa a ferramenta — foi assim que ele surgiu na camada
CAA, um agente que não tem ferramenta nenhuma.

Duas coisas são feitas aqui:

- **o schema de resposta é descartado.** O ADK o repassa como `response_json_schema`,
  e o modelo não precisa dele para chamar a ferramenta: ele serve para validar o
  retorno, que esta esteira já poda em `agents/callbacks.py`. Descartar mata a classe
  inteira de erro e ainda economiza contexto, porque esses schemas trazem enums de
  centenas de valores;
- **referência órfã no schema de entrada vira um objeto livre.** Ali o schema é
  necessário, então ele é remendado em vez de removido.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset

logger = logging.getLogger("mcp_saneado")


def _referencias(no: Any, achadas: Set[str]) -> None:
    if isinstance(no, dict):
        ref = no.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            achadas.add(ref.split("/")[-1])
        for valor in no.values():
            _referencias(valor, achadas)
    elif isinstance(no, list):
        for item in no:
            _referencias(item, achadas)


def remendar_entrada(schema: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Dá um `$defs` de objeto livre a toda referência que o servidor esqueceu de definir."""
    if not isinstance(schema, dict):
        return schema
    achadas: Set[str] = set()
    _referencias(schema, achadas)
    faltando = achadas - set((schema.get("$defs") or {}).keys())
    if not faltando:
        return schema
    defs = dict(schema.get("$defs") or {})
    for nome in faltando:
        defs[nome] = {"type": "object", "description": f"{nome} (definição não publicada pelo servidor)"}
    remendado = dict(schema)
    remendado["$defs"] = defs
    return remendado


def _sanear(ferramenta: Any) -> List[str]:
    """Sanea o `Tool` do MCP no lugar. Devolve o que foi mexido, para o log."""
    mexidos: List[str] = []
    for campo in ("outputSchema", "output_schema"):
        if getattr(ferramenta, campo, None) is not None:
            try:
                setattr(ferramenta, campo, None)
                mexidos.append("schema de resposta descartado")
            except Exception:  # pragma: no cover - modelo imutável
                pass
            break
    for campo in ("inputSchema", "input_schema"):
        atual = getattr(ferramenta, campo, None)
        if isinstance(atual, dict):
            remendado = remendar_entrada(atual)
            if remendado is not atual:
                try:
                    setattr(ferramenta, campo, remendado)
                    mexidos.append("referências órfãs remendadas na entrada")
                except Exception:  # pragma: no cover
                    pass
            break
    return mexidos


class McpToolsetSaneado(McpToolset):
    """`McpToolset` que sanea o schema de cada ferramenta antes de entregá-la ao agente."""

    async def get_tools(self, readonly_context: Optional[ReadonlyContext] = None) -> List[BaseTool]:
        ferramentas = await super().get_tools(readonly_context)
        for t in ferramentas:
            bruta = getattr(t, "raw_mcp_tool", None) or getattr(t, "_mcp_tool", None)
            if bruta is None:
                continue
            mexidos = _sanear(bruta)
            if mexidos:
                logger.debug("%s: %s", getattr(t, "name", "?"), "; ".join(mexidos))
        return ferramentas
