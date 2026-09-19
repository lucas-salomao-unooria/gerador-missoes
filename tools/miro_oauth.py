"""OAuth do MCP do Miro, conduzido pelo front Streamlit.

Por que não basta uma chave no `.env`: `https://mcp.miro.com/` é ele mesmo o
authorization server e só aceita clients que ele próprio emitiu por **registro dinâmico**
(RFC 7591). O `client_id` de um app do dev portal do Miro é recusado com
`invalid_request — Client ID '…' is not registered with this server` (verificado em
19/09/2026, mesma resposta que um client_id inventado). Por isso não há "cole o token
aqui": o fluxo é registrar o client uma vez, conduzir o authorization code com PKCE pelo
navegador de quem usa o app, e guardar access/refresh token em disco.

O parâmetro `resource` (RFC 8707) vai no `/authorize` e no `/token` porque o servidor
valida a audience: um token emitido para outro destino é recusado no `initialize`.

Atenção ao operar: o Miro **rotaciona o refresh token** a cada renovação. Dois processos
com o mesmo arquivo de tokens invalidam um ao outro — é mais uma razão para manter uma
instância só no Cloud Run.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import httpx

from config import PROJECT_ROOT, get_settings

logger = logging.getLogger("miro_oauth")

# Escopos mínimos: ler para conferir o board, escrever para publicar o espelho.
ESCOPOS = "boards:read boards:write"

# Margem antes do vencimento. O access token dura 60 min; renovar com dois minutos de
# folga evita a corrida entre a checagem e a chamada que vem logo depois.
MARGEM_RENOVACAO_S = 120

_endpoints_cache: Optional[Dict[str, str]] = None


# --------------------------------------------------------------------- descoberta
def descobrir_endpoints(timeout: int = 20) -> Dict[str, str]:
    """Lê o well-known do servidor MCP. Cacheado no processo: é metadado estável."""
    global _endpoints_cache
    if _endpoints_cache:
        return _endpoints_cache

    base = get_settings().miro_mcp_url.rstrip("/")
    resp = httpx.get(f"{base}/.well-known/oauth-authorization-server", timeout=timeout)
    resp.raise_for_status()
    meta = resp.json()

    faltando = [c for c in ("authorization_endpoint", "token_endpoint", "registration_endpoint") if not meta.get(c)]
    if faltando:
        raise RuntimeError(f"O well-known do Miro não trouxe {', '.join(faltando)}")

    _endpoints_cache = {
        "authorization_endpoint": meta["authorization_endpoint"],
        "token_endpoint": meta["token_endpoint"],
        "registration_endpoint": meta["registration_endpoint"],
        "issuer": meta.get("issuer", base + "/"),
    }
    return _endpoints_cache


# --------------------------------------------------------------------------- PKCE
def gerar_pkce() -> Tuple[str, str]:
    """Devolve `(code_verifier, code_challenge)` no método S256, o único que o Miro aceita."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).decode().rstrip("=")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge


# ----------------------------------------------------------------------- registro
def registrar_client(redirect_uri: str, timeout: int = 20) -> Dict[str, str]:
    """Registra um client novo no servidor MCP e devolve `client_id`/`client_secret`.

    É o passo que substitui "criar um app no dev portal": o `redirect_uri` é declarado
    aqui, então não há nada a configurar fora do código.
    """
    endpoints = descobrir_endpoints(timeout=timeout)
    corpo = {
        "client_name": f"{get_settings().app_name} (gerador de missões)",
        "redirect_uris": [redirect_uri],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "client_secret_post",
        "scope": ESCOPOS,
    }
    resp = httpx.post(endpoints["registration_endpoint"], json=corpo, timeout=timeout)
    resp.raise_for_status()
    dados = resp.json()
    if not dados.get("client_id"):
        raise RuntimeError("O registro no Miro não devolveu client_id")

    logger.info("Client registrado no MCP do Miro para %s", redirect_uri)
    return {
        "client_id": dados["client_id"],
        "client_secret": dados.get("client_secret", ""),
        "redirect_uri": redirect_uri,
        "registrado_em": _agora_iso(),
    }


# -------------------------------------------------------------------- autorização
def url_de_autorizacao(state: str, code_challenge: str, redirect_uri: Optional[str] = None) -> str:
    """Monta a URL que o usuário abre para autorizar, registrando o client se preciso."""
    s = get_settings()
    redirect_uri = redirect_uri or s.miro_redirect_uri
    store = token_store()

    client = store.client()
    if not client or client.get("redirect_uri") != redirect_uri:
        client = registrar_client(redirect_uri)
        store.gravar_client(client)

    endpoints = descobrir_endpoints()
    params = httpx.QueryParams(
        {
            "response_type": "code",
            "client_id": client["client_id"],
            "redirect_uri": redirect_uri,
            "scope": ESCOPOS,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "resource": s.miro_mcp_url,
        }
    )
    return f"{endpoints['authorization_endpoint']}?{params}"


def trocar_codigo(
    code: str,
    code_verifier: str,
    redirect_uri: Optional[str] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """Troca o código do retorno por tokens e grava a conexão. Devolve o status."""
    s = get_settings()
    redirect_uri = redirect_uri or s.miro_redirect_uri
    store = token_store()
    client = store.client()
    if not client:
        raise RuntimeError("Nenhum client registrado: comece pelo botão de conexão")

    endpoints = descobrir_endpoints()
    dados = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client["client_id"],
        "client_secret": client.get("client_secret", ""),
        "code_verifier": code_verifier,
        "resource": s.miro_mcp_url,
    }
    resp = httpx.post(endpoints["token_endpoint"], data=dados, timeout=timeout)
    resp.raise_for_status()
    store.gravar_tokens(resp.json())
    return store.status()


# ------------------------------------------------------------------- token store
class MiroTokenStore:
    """Conexão do Miro em disco: o client emitido no registro e os tokens em vigor.

    Gravação atômica e permissão 0600 porque o arquivo guarda um refresh token de 60
    dias — quem o tiver entra nos boards do time sem passar pelo navegador.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    # ---------------------------------------------------------------- leitura
    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            # Arquivo corrompido não pode derrubar a UI: vale como "não conectado".
            logger.warning("Arquivo de tokens do Miro ilegível (%s); tratando como sem conexão", exc)
            return {}

    def client(self) -> Optional[Dict[str, str]]:
        return self.load().get("client") or None

    # ---------------------------------------------------------------- escrita
    def _save(self, dados: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporario = self.path.with_suffix(self.path.suffix + ".tmp")
        temporario.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
        os.chmod(temporario, 0o600)
        os.replace(temporario, self.path)

    def gravar_client(self, client: Dict[str, str]) -> None:
        dados = self.load()
        dados["client"] = client
        self._save(dados)

    def gravar_tokens(self, resposta: Dict[str, Any]) -> None:
        """Guarda a resposta do `/token`, preservando o refresh token quando ele não vem."""
        dados = self.load()
        anteriores = dados.get("tokens", {})
        dados["tokens"] = {
            "access_token": resposta.get("access_token", ""),
            # Na rotação o servidor manda um refresh novo; se omitir, o antigo segue valendo.
            "refresh_token": resposta.get("refresh_token") or anteriores.get("refresh_token", ""),
            "token_type": resposta.get("token_type", "Bearer"),
            "scope": resposta.get("scope", ESCOPOS),
        }
        dados["expires_at"] = time.time() + int(resposta.get("expires_in", 3600))
        dados["obtido_em"] = _agora_iso()
        self._save(dados)

    def apagar(self) -> None:
        self.path.unlink(missing_ok=True)

    # ------------------------------------------------------- autorização em curso
    def gravar_pendente(self, state: str, code_verifier: str) -> None:
        """Guarda o PKCE da autorização em curso.

        Em disco, e não no `st.session_state`: ir ao Miro e voltar abre uma sessão nova
        do Streamlit, e o verifier guardado em memória se perde no caminho — o retorno
        falharia com `invalid_grant` sem explicação visível.
        """
        dados = self.load()
        dados["pendente"] = {"state": state, "code_verifier": code_verifier, "criado_em": time.time()}
        self._save(dados)

    def ler_pendente(self) -> Optional[Dict[str, Any]]:
        pendente = self.load().get("pendente")
        if not pendente:
            return None
        # Uma autorização abandonada não pode valer para sempre.
        if time.time() - float(pendente.get("criado_em", 0)) > 900:
            self.limpar_pendente()
            return None
        return pendente

    def limpar_pendente(self) -> None:
        dados = self.load()
        if dados.pop("pendente", None) is not None:
            self._save(dados)

    # ------------------------------------------------------------------- uso
    def access_token(self) -> str:
        """O token pronto para o header, renovando sozinho quando está por vencer."""
        dados = self.load()
        tokens = dados.get("tokens") or {}
        if not tokens.get("access_token"):
            raise RuntimeError("sem conexão com o Miro")

        if time.time() < float(dados.get("expires_at", 0)) - MARGEM_RENOVACAO_S:
            return tokens["access_token"]

        if not tokens.get("refresh_token"):
            raise RuntimeError("conexão com o Miro expirada — reconecte")
        return self._refresh(dados)

    def _refresh(self, dados: Dict[str, Any]) -> str:
        s = get_settings()
        client = dados.get("client") or {}
        endpoints = descobrir_endpoints()
        resp = httpx.post(
            endpoints["token_endpoint"],
            data={
                "grant_type": "refresh_token",
                "refresh_token": dados["tokens"]["refresh_token"],
                "client_id": client.get("client_id", ""),
                "client_secret": client.get("client_secret", ""),
                "resource": s.miro_mcp_url,
            },
            timeout=30,
        )
        resp.raise_for_status()
        self.gravar_tokens(resp.json())
        return self.load()["tokens"]["access_token"]

    # ---------------------------------------------------------------- status
    def status(self) -> Dict[str, Any]:
        dados = self.load()
        tokens = dados.get("tokens") or {}
        if not tokens.get("access_token"):
            return {"conectado": False, "registrado": bool(dados.get("client"))}
        restante = float(dados.get("expires_at", 0)) - time.time()
        return {
            "conectado": True,
            "registrado": True,
            "expira_em_min": int(restante // 60),
            "renovavel": bool(tokens.get("refresh_token")),
            "escopos": tokens.get("scope", ""),
            "obtido_em": dados.get("obtido_em", ""),
        }


# ------------------------------------------------------ fluxo pronto para o front
def iniciar_conexao(redirect_uri: Optional[str] = None) -> str:
    """Registra o client se preciso, guarda o PKCE e devolve a URL de autorização."""
    redirect_uri = redirect_uri or get_settings().miro_redirect_uri
    state = secrets.token_urlsafe(24)
    verifier, challenge = gerar_pkce()
    url = url_de_autorizacao(state, challenge, redirect_uri)
    token_store().gravar_pendente(state, verifier)
    return url


def concluir_conexao(code: str, state: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
    """Fecha o fluxo com o código que voltou na query string. Devolve o status."""
    store = token_store()
    pendente = store.ler_pendente()
    if not pendente:
        raise RuntimeError("Nenhuma autorização em curso — refaça a conexão")
    if not secrets.compare_digest(str(pendente.get("state", "")), state):
        # `state` diferente significa resposta que não veio do pedido que fizemos.
        store.limpar_pendente()
        raise RuntimeError("O `state` do retorno não confere — autorização descartada")

    try:
        estado = trocar_codigo(code, pendente["code_verifier"], redirect_uri)
    finally:
        store.limpar_pendente()
    return estado


def token_store() -> MiroTokenStore:
    s = get_settings()
    caminho = Path(s.miro_oauth_tokens_file)
    if not caminho.is_absolute():
        caminho = PROJECT_ROOT / caminho
    return MiroTokenStore(caminho)


def status_label() -> str:
    """Rótulo para a UI. Diferente de `AppSettings.miro_status_label`, este lê o disco."""
    s = get_settings()
    if not s.is_miro_enabled:
        return "⚪ Desligado (MIRO_MODE=off)"
    try:
        estado = token_store().status()
    except OSError as exc:
        return f"🔴 Erro ao ler a conexão ({exc})"

    if not estado["conectado"]:
        return "🟡 Sem conexão — clique em Conectar"
    if estado["expira_em_min"] < 0:
        return "🟡 Token vencido — renova na próxima publicação" if estado["renovavel"] else "🔴 Expirado — reconecte"
    return f"🟢 Conectado (expira em {estado['expira_em_min']} min)"


def _agora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
