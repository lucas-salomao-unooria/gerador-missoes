"""Cookie da sessão de login, gravado pelo navegador.

O Streamlit só *lê* cookies (`st.context.cookies`, os da requisição que abriu a página) e não tem
API para gravá-los. Este componente CCv2 inline grava e apaga o cookie por JavaScript. O CCv2 não
roda em iframe: o JS executa no documento do app, e `document.cookie` vale para a origem dele.
(`components.v1.html` roda num iframe e está depreciado.)

Como o cookie nasce no JS, ele não pode ser `HttpOnly`. O risco é mitigado por três coisas: a
validade curta (a mesma do JWT), `SameSite=Strict` e a regra de o app nunca renderizar como HTML
conteúdo que venha dos artefatos.
"""

from __future__ import annotations

from typing import Optional

import streamlit as st

NOME_COOKIE = "gm_sessao"

_JS = """
export default function(component) {
    const { data } = component;
    if (!data) { return; }
    const seguro = window.location.protocol === "https:" ? "; Secure" : "";
    const base = "; Path=/; SameSite=Strict" + seguro;
    if (data.acao === "gravar") {
        document.cookie = data.nome + "=" + data.valor + "; Max-Age=" + data.max_age + base;
    } else if (data.acao === "apagar") {
        document.cookie = data.nome + "=; Max-Age=0" + base;
    }
}
"""

_componente = st.components.v2.component("gm_cookie_sessao", js=_JS)


def ler_cookie() -> Optional[str]:
    """Token do cookie que chegou quando a página abriu. `None` fora de um app Streamlit."""
    try:
        return st.context.cookies.get(NOME_COOKIE)
    except Exception:
        return None


def gravar_cookie(token: str, max_age_s: int) -> None:
    """Idempotente: montado a cada rerun enquanto há sessão, garante que o JS rodou ao menos uma vez."""
    _componente(data={"acao": "gravar", "nome": NOME_COOKIE, "valor": token, "max_age": max(0, int(max_age_s))},
                key="gm_cookie_gravar", height="content")


def apagar_cookie() -> None:
    _componente(data={"acao": "apagar", "nome": NOME_COOKIE}, key="gm_cookie_apagar", height="content")
