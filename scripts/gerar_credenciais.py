#!/usr/bin/env python3
"""Gera as senhas das 4 contas do gerador (produto, design, dev, admin) e a chave do JWT.

Uso:
  python scripts/gerar_credenciais.py                 # imprime senhas e os comandos gcloud
  python scripts/gerar_credenciais.py --env           # também imprime as linhas para o .env local
  python scripts/gerar_credenciais.py --publicar      # grava direto como nova versão no Secret Manager

As senhas aparecem UMA vez, aqui. O que vai para o Secret Manager é só o hash scrypt de cada uma
(`AUTH_CREDENCIAIS`) e a chave que assina as sessões (`AUTH_SEGREDO_JWT`). Os recursos dos segredos
nascem no Terraform (`gerador_missoes.tf`); o valor não, para não ir ao tfstate — o mesmo padrão da
chave do Stitch. Gerar de novo troca todas as senhas e, pela chave nova, derruba todas as sessões.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from tools.auth import PAPEIS, gerar_credenciais  # noqa: E402

PROJETO = "entre-redes-dev"
SEGREDO_CREDENCIAIS = "plataforma-unooria-dev-gerador-credenciais"
SEGREDO_JWT = "plataforma-unooria-dev-gerador-jwt"


def publicar(segredo: str, valor: str) -> None:
    subprocess.run(
        ["gcloud", "secrets", "versions", "add", segredo, f"--project={PROJETO}", "--data-file=-"],
        input=valor.encode("utf-8"), check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env", action="store_true", help="imprime AUTH_CREDENCIAIS e AUTH_SEGREDO_JWT para o .env")
    parser.add_argument("--publicar", action="store_true", help="adiciona as versões no Secret Manager via gcloud")
    args = parser.parse_args()

    senhas, contas, segredo_jwt = gerar_credenciais(PAPEIS)
    credenciais = json.dumps(contas, separators=(",", ":"))

    print("Senhas (guarde agora — não aparecem de novo):\n")
    for usuario in PAPEIS:
        print(f"  {usuario:<8} {senhas[usuario]}")
    print()

    if args.env:
        print("Linhas para o .env local:\n")
        print(f"AUTH_CREDENCIAIS='{credenciais}'")
        print(f"AUTH_SEGREDO_JWT='{segredo_jwt}'\n")

    if args.publicar:
        publicar(SEGREDO_CREDENCIAIS, credenciais)
        publicar(SEGREDO_JWT, segredo_jwt)
        print(f"Versões novas em {SEGREDO_CREDENCIAIS} e {SEGREDO_JWT}. O próximo deploy as pega (:latest).")
    else:
        print("Para publicar sem rodar de novo (as senhas acima valem para estes valores):\n")
        print(f"printf %s '{credenciais}' | gcloud secrets versions add {SEGREDO_CREDENCIAIS} --project={PROJETO} --data-file=-")
        print(f"printf %s '{segredo_jwt}' | gcloud secrets versions add {SEGREDO_JWT} --project={PROJETO} --data-file=-")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
