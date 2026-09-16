<!-- CÓPIA SINCRONIZADA de plataforma-unooria@4578555 (2026-09-16) · origem: docs/regras/infra.md · não edite: rode scripts/sincronizar_plataforma.py · placeholders entre chaves aparecem como «nome» por limitação de interpolação do ADK; no código real use chaves -->

# Infra (repo separado)

Complementa o `AGENTS.md` da raiz, que vence em conflito.

## Infra (repo separado)

Terraform vive em outro repo. O contrato entre os repos está em `docs/INFRA.md`:
nomes de recursos esperados, variáveis de ambiente que a app consome, e o que o
CI deste repo publica (imagens no Artifact Registry, bundles no bucket).
Nunca criar recursos GCP imperativamente por script neste repo.
