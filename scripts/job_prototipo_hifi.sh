#!/bin/sh
# Entrada do Job do Cloud Run `prototipo-hifi` (Terraform: `gerador_missoes.tf` na fundação).
#
# O gerador dispara o Job com as variáveis da execução:
#   SESSAO      pasta da missão no bucket montado em $OUTPUT_DIR (ex.: 20261028-154851-session_f4caa98a)
#   MODELO      modelo do agente de código (padrão: gemini-4-argon)
#   VERIFICAR=1 só confere o ambiente (imagem, bucket, Chromium, Vertex), sem gerar
#   CORRECAO    rodada de correção sobre o protótipo publicado (texto da revisão)
#
# O resultado vai para $OUTPUT_DIR/$SESSAO/design/hifi; o workspace de trabalho fica em /tmp e morre com a tarefa.
set -eu
: "${SESSAO:?defina SESSAO, a pasta da missão no bucket}"
SESSAO_DIR="$OUTPUT_DIR/$SESSAO"
[ -d "$SESSAO_DIR" ] || { echo "sessão não encontrada: $SESSAO_DIR" >&2; exit 2; }
set -- --sessao "$SESSAO_DIR" --destino /tmp/prototipo-hifi --ds "$PROTOTIPO_HIFI_DS" \
       --plataforma "$PROTOTIPO_HIFI_PLATAFORMA" --modelo "${MODELO:-gemini-4-argon}"
if [ "${VERIFICAR:-0}" = "1" ]; then
  exec python scripts/prototipo_hifi.py "$@" --verificar-ambiente
fi
if [ -n "${CORRECAO:-}" ]; then
  set -- "$@" --correcao "$CORRECAO"
fi
exec python scripts/prototipo_hifi.py "$@" --publicar "$SESSAO_DIR/design/hifi"
