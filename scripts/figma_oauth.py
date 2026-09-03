"""Obtém tokens OAuth 2.1 para o servidor MCP remoto do Figma (https://mcp.figma.com/mcp).

O servidor oficial do Figma exige OAuth (não aceita Personal Access Token). Este script
executa o fluxo completo do MCP — descoberta de metadados, registro dinâmico de cliente,
PKCE, código de autorização via navegador — usando o SDK `mcp`, e grava os tokens em
`.figma_mcp_tokens.json` (configurável por FIGMA_MCP_OAUTH_TOKENS_FILE).

Uso:
    source .venv/bin/activate
    python scripts/figma_oauth.py            # abre o navegador e aguarda o callback
    python scripts/figma_oauth.py --port 8765

Depois, defina FIGMA_MCP_MODE=remote no .env. O toolset (tools/figma_mcp.py) lê o arquivo
e renova o access token automaticamente com o refresh token.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp import ClientSession  # noqa: E402
from mcp.client.auth import OAuthClientProvider, TokenStorage  # noqa: E402
from mcp.client.streamable_http import streamablehttp_client  # noqa: E402
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken  # noqa: E402

from config import PROJECT_ROOT, get_settings  # noqa: E402


class FileTokenStorage(TokenStorage):
    """Persistência dos tokens e do registro do cliente em um único JSON."""

    def __init__(self, path: Path):
        self.path = path
        self.data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def _flush(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

    async def get_tokens(self) -> Optional[OAuthToken]:
        raw = self.data.get("tokens")
        return OAuthToken.model_validate(raw) if raw else None

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self.data["tokens"] = tokens.model_dump(exclude_none=True)
        if tokens.expires_in:
            self.data["expires_at"] = time.time() + float(tokens.expires_in)
        self._flush()

    async def get_client_info(self) -> Optional[OAuthClientInformationFull]:
        raw = self.data.get("client_info")
        return OAuthClientInformationFull.model_validate(raw) if raw else None

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self.data["client_info"] = json.loads(client_info.model_dump_json(exclude_none=True))
        self._flush()


class _CallbackServer:
    """Servidor HTTP mínimo que captura `code` e `state` do redirect OAuth."""

    def __init__(self, port: int):
        self.port = port
        self.result: Optional[Tuple[str, Optional[str]]] = None
        self._event = threading.Event()
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                qs = parse_qs(urlparse(self.path).query)
                code = (qs.get("code") or [""])[0]
                state = (qs.get("state") or [None])[0]
                if code:
                    server.result = (code, state)
                    body = "<h2>Autorização concluída. Pode fechar esta aba.</h2>"
                else:
                    body = f"<h2>Falha: {qs.get('error', ['sem código'])[0]}</h2>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body.encode("utf-8"))
                server._event.set()

            def log_message(self, *_):  # silencia o log padrão
                return

        self.httpd = HTTPServer(("127.0.0.1", port), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def wait(self, timeout: float = 300) -> Tuple[str, Optional[str]]:
        if not self._event.wait(timeout) or not self.result:
            raise TimeoutError("Nenhum callback OAuth recebido a tempo.")
        return self.result

    def stop(self) -> None:
        self.httpd.shutdown()


async def main(port: int) -> None:
    settings = get_settings()
    tokens_path = PROJECT_ROOT / settings.figma_mcp_oauth_tokens_file
    server_url = settings.figma_mcp_remote_url
    redirect_uri = f"http://127.0.0.1:{port}/callback"

    callback = _CallbackServer(port)
    callback.start()

    async def redirect_handler(url: str) -> None:
        print(f"\n🔗 Abra no navegador (abrindo automaticamente):\n{url}\n")
        webbrowser.open(url)

    async def callback_handler() -> Tuple[str, Optional[str]]:
        return await asyncio.get_running_loop().run_in_executor(None, callback.wait)

    storage = FileTokenStorage(tokens_path)
    provider = OAuthClientProvider(
        server_url=server_url,
        client_metadata=OAuthClientMetadata(
            client_name="Gerador de Missões Unooria",
            redirect_uris=[redirect_uri],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            token_endpoint_auth_method="none",
        ),
        storage=storage,
        redirect_handler=redirect_handler,
        callback_handler=callback_handler,
    )

    print(f"➡️  Conectando em {server_url} …")
    try:
        async with streamablehttp_client(server_url, auth=provider) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                nomes = sorted(t.name for t in tools.tools)
                print(f"✅ Autenticado. {len(nomes)} ferramentas disponíveis:")
                print("   " + ", ".join(nomes))
    finally:
        callback.stop()

    # registra o token_endpoint para a renovação feita em tools/figma_mcp.py
    try:
        import httpx

        meta_urls = [
            f"{server_url.rstrip('/')}/.well-known/oauth-authorization-server",
            "https://mcp.figma.com/.well-known/oauth-authorization-server",
            "https://www.figma.com/.well-known/oauth-authorization-server",
        ]
        for meta_url in meta_urls:
            resp = httpx.get(meta_url, timeout=15)
            if resp.status_code == 200 and resp.json().get("token_endpoint"):
                storage.data["token_endpoint"] = resp.json()["token_endpoint"]
                storage._flush()
                break
    except Exception as exc:  # pragma: no cover
        print(f"⚠️  Não foi possível registrar o token_endpoint para renovação automática: {exc}")

    print(f"\n💾 Tokens gravados em {tokens_path}")
    print("   Defina FIGMA_MCP_MODE=remote no .env e reinicie a aplicação.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OAuth do MCP remoto do Figma")
    parser.add_argument("--port", type=int, default=8765, help="porta local do callback OAuth")
    args = parser.parse_args()
    asyncio.run(main(args.port))
