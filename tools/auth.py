"""Login da aplicação: quatro contas fixas, senha com scrypt e sessão em JWT de 4 horas.

Sem provedor de identidade e sem IAP, por decisão do dono do projeto (23/09/2026). As contas são
papéis, não pessoas: `produto`, `design`, `dev` e `admin`. O `admin` age por qualquer papel, e o
registro diz "admin (como Produto)".

Tudo aqui é puro e testável sem Streamlit: o relógio entra por parâmetro, o armazenamento das
revogações é um caminho de arquivo. Quem grava o cookie no navegador é `tools/cookie_sessao.py`.

Formato do hash: `scrypt$<n>$<r>$<p>$<salt_b64>$<hash_b64>`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import jwt

PAPEIS = ("produto", "design", "dev", "admin")
ROTULO_PAPEL = {"produto": "Produto", "design": "Design", "dev": "Dev", "admin": "Admin"}

#: scrypt com custo de ~50 ms: caro para força bruta, imperceptível num login
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2 ** 14, 8, 1
_ALGORITMO = "HS256"

MAX_FALHAS = 5
TRAVA_SEGUNDOS = 5 * 60


class ConfiguracaoDeLoginAusente(RuntimeError):
    """Falta `AUTH_CREDENCIAIS` ou `AUTH_SEGREDO_JWT`, ou um deles está malformado."""


# ------------------------------------------------------------------ senhas
def gerar_hash(senha: str, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.scrypt(senha.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=32)
    b64 = lambda b: base64.b64encode(b).decode("ascii")
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${b64(salt)}${b64(dk)}"


def conferir_hash(senha: str, codificado: str) -> bool:
    try:
        esquema, n, r, p, salt_b64, hash_b64 = codificado.split("$")
        if esquema != "scrypt":
            return False
        esperado = base64.b64decode(hash_b64)
        dk = hashlib.scrypt(senha.encode("utf-8"), salt=base64.b64decode(salt_b64),
                            n=int(n), r=int(r), p=int(p), dklen=len(esperado))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk, esperado)


# ------------------------------------------------------------------ configuração
@dataclass(frozen=True)
class ConfigLogin:
    contas: Dict[str, Dict[str, str]]
    segredo: str
    horas: float = 4.0


def configuracao_de_login(credenciais_json: str, segredo: str, horas: float = 4.0) -> ConfigLogin:
    """Valida o que veio do ambiente. Levanta `ConfiguracaoDeLoginAusente` com o motivo exato."""
    if not (credenciais_json or "").strip():
        raise ConfiguracaoDeLoginAusente("AUTH_CREDENCIAIS não está definida")
    if len((segredo or "").strip()) < 32:
        raise ConfiguracaoDeLoginAusente("AUTH_SEGREDO_JWT ausente ou com menos de 32 caracteres")
    try:
        contas = json.loads(credenciais_json)
    except json.JSONDecodeError as exc:
        raise ConfiguracaoDeLoginAusente(f"AUTH_CREDENCIAIS não é JSON válido ({exc.msg})") from exc
    if not isinstance(contas, dict) or not contas:
        raise ConfiguracaoDeLoginAusente("AUTH_CREDENCIAIS precisa ser um objeto {usuario: {hash, papel}}")
    for usuario, conta in contas.items():
        if not isinstance(conta, dict) or not str(conta.get("hash", "")).startswith("scrypt$"):
            raise ConfiguracaoDeLoginAusente(f"conta {usuario!r} sem hash scrypt")
        if conta.get("papel") not in PAPEIS:
            raise ConfiguracaoDeLoginAusente(f"conta {usuario!r} com papel inválido {conta.get('papel')!r}")
    return ConfigLogin(contas=contas, segredo=segredo.strip(), horas=float(horas))


# ------------------------------------------------------------------ travamento
class Travas:
    """Falhas seguidas por usuário. Em memória: basta com uma instância só (`--max-instances 1`)."""

    def __init__(self) -> None:
        self._falhas: Dict[str, Tuple[int, float]] = {}
        self._lock = threading.Lock()

    def travado_ate(self, usuario: str, agora: float) -> Optional[float]:
        with self._lock:
            n, ultima = self._falhas.get(usuario, (0, 0.0))
            if n >= MAX_FALHAS and agora - ultima < TRAVA_SEGUNDOS:
                return ultima + TRAVA_SEGUNDOS
            if n >= MAX_FALHAS:
                self._falhas.pop(usuario, None)
            return None

    def falhou(self, usuario: str, agora: float) -> None:
        with self._lock:
            n, _ = self._falhas.get(usuario, (0, 0.0))
            self._falhas[usuario] = (n + 1, agora)

    def acertou(self, usuario: str) -> None:
        with self._lock:
            self._falhas.pop(usuario, None)


TRAVAS = Travas()


# ------------------------------------------------------------------ sessão
@dataclass(frozen=True)
class Sessao:
    usuario: str
    papel: str
    emitida_em: float
    expira_em: float
    jti: str

    @property
    def rotulo(self) -> str:
        return ROTULO_PAPEL.get(self.papel, self.papel)

    def pode_agir_como(self, papel: str) -> bool:
        return self.papel == "admin" or self.papel == papel

    def assinatura_de(self, papel: str) -> str:
        """Como a decisão fica registrada: "design", ou "admin (como Design)"."""
        if self.papel == papel or self.papel != "admin":
            return self.papel
        return f"admin (como {ROTULO_PAPEL.get(papel, papel)})"


#: hash de uma senha qualquer, para o login de usuário inexistente custar o mesmo scrypt
_HASH_FICTICIO = gerar_hash("usuario-inexistente", b"\x00" * 16)


def autenticar(cfg: ConfigLogin, usuario: str, senha: str, agora: Optional[float] = None,
               travas: Travas = TRAVAS) -> Tuple[Optional[Sessao], str]:
    """`(sessao, "")` ou `(None, motivo)`. O motivo não diz se o usuário existe."""
    agora = time.time() if agora is None else agora
    usuario = (usuario or "").strip().lower()
    ate = travas.travado_ate(usuario, agora)
    if ate:
        minutos = max(1, int((ate - agora + 59) // 60))
        return None, f"Muitas tentativas. Tente de novo em {minutos} min."
    conta = cfg.contas.get(usuario)
    ok = conferir_hash(senha or "", conta["hash"] if conta else _HASH_FICTICIO)
    if not (conta and ok):
        travas.falhou(usuario, agora)
        return None, "Usuário ou senha inválidos."
    travas.acertou(usuario)
    return Sessao(usuario=usuario, papel=conta["papel"], emitida_em=agora,
                  expira_em=agora + cfg.horas * 3600, jti=uuid.uuid4().hex), ""


def emitir_token(cfg: ConfigLogin, sessao: Sessao) -> str:
    payload = {"sub": sessao.usuario, "papel": sessao.papel, "iat": int(sessao.emitida_em),
               "exp": int(sessao.expira_em), "jti": sessao.jti}
    return jwt.encode(payload, cfg.segredo, algorithm=_ALGORITMO)


def validar_token(cfg: ConfigLogin, token: str, agora: Optional[float] = None,
                  revogados: Optional["Revogacoes"] = None) -> Optional[Sessao]:
    """Sessão do token, ou `None` se assinatura, validade, conta ou revogação não baterem."""
    if not token:
        return None
    agora = time.time() if agora is None else agora
    try:
        dados = jwt.decode(token, cfg.segredo, algorithms=[_ALGORITMO],
                           options={"verify_exp": False, "verify_iat": False,
                                    "require": ["sub", "papel", "exp", "iat", "jti"]})
    except jwt.PyJWTError:
        return None
    # expiração conferida aqui, contra o relógio injetado (o PyJWT só conhece o relógio real)
    if float(dados["exp"]) <= agora:
        return None
    conta = cfg.contas.get(dados["sub"])
    if not conta or conta.get("papel") != dados["papel"]:
        return None  # conta removida ou papel trocado depois da emissão
    if revogados and revogados.contem(dados["jti"], agora):
        return None
    return Sessao(usuario=dados["sub"], papel=dados["papel"], emitida_em=float(dados["iat"]),
                  expira_em=float(dados["exp"]), jti=dados["jti"])


class Revogacoes:
    """`jti` de sessões encerradas por "Sair", até o `exp` delas. Arquivo no bucket (`output/.auth/`)."""

    def __init__(self, caminho: Path) -> None:
        self.caminho = Path(caminho)
        self._lock = threading.Lock()

    def _ler(self) -> Dict[str, float]:
        try:
            dados = json.loads(self.caminho.read_text(encoding="utf-8"))
            return {str(k): float(v) for k, v in dados.items()} if isinstance(dados, dict) else {}
        except (OSError, ValueError):
            return {}

    def revogar(self, sessao: Sessao, agora: Optional[float] = None) -> None:
        agora = time.time() if agora is None else agora
        with self._lock:
            vigentes = {k: v for k, v in self._ler().items() if v > agora}
            vigentes[sessao.jti] = sessao.expira_em
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            self.caminho.write_text(json.dumps(vigentes), encoding="utf-8")

    def contem(self, jti: str, agora: float) -> bool:
        exp = self._ler().get(jti)
        return exp is not None and exp > agora


def gerar_credenciais(usuarios: Tuple[str, ...] = PAPEIS) -> Tuple[Dict[str, str], Dict[str, Any], str]:
    """`(senhas_em_claro, json_de_hashes, segredo_jwt)`. Usado por `scripts/gerar_credenciais.py`."""
    senhas = {u: secrets.token_urlsafe(18) for u in usuarios}
    contas = {u: {"hash": gerar_hash(s), "papel": u} for u, s in senhas.items()}
    return senhas, contas, secrets.token_urlsafe(48)
