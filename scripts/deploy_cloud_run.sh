#!/usr/bin/env bash
set -e

# ==============================================================================
# Script de Deploy do Gerador de Missões (Streamlit + Google ADK) no Cloud Run
# Projeto: entre-redes-dev
# Região: us-east1
# Volume GCS: gs://entre-redes-dev-adk-artifacts montado em /app/output
# ==============================================================================

SERVICE_NAME="gerador-missoes"
PROJECT_ID="entre-redes-dev"
REGION="us-east1"
ARTIFACT_BUCKET="entre-redes-dev-adk-artifacts"
# Base da plataforma: bucket próprio, criado e permissionado pelo Terraform da Fundação, montado só leitura.
BASE_BUCKET="entre-redes-dev-base-plataforma"
# A chave de API do Stitch NUNCA entra em arquivo: ela vive no Secret Manager, o
# recurso é declarado no Terraform (`gerador_missoes.tf`) e o valor é injetado por
# `gcloud secrets versions add`. Aqui só se referencia a versão mais recente.
STITCH_SECRET="plataforma-unooria-dev-stitch-api-key"
# Login da aplicação (`tools/auth.py`): hashes das 4 contas e chave que assina o JWT.
# Mesmo padrão do Stitch — recurso no Terraform, valor por `scripts/gerar_credenciais.py`.
AUTH_CREDENCIAIS_SECRET="plataforma-unooria-dev-gerador-credenciais"
AUTH_JWT_SECRET="plataforma-unooria-dev-gerador-jwt"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"

echo "=================================================================="
echo "🚀 1. Configurando contexto do gcloud para $PROJECT_ID ($REGION)"
echo "=================================================================="
gcloud config set project "$PROJECT_ID"

echo "=================================================================="
echo "🪣 2. Verificando bucket de artefatos (gs://$ARTIFACT_BUCKET)..."
echo "=================================================================="
if ! gcloud storage buckets describe "gs://$ARTIFACT_BUCKET" >/dev/null 2>&1; then
    echo "Criando bucket gs://$ARTIFACT_BUCKET em $REGION..."
    gcloud storage buckets create "gs://$ARTIFACT_BUCKET" --location="$REGION" --uniform-bucket-level-access
else
    echo "Bucket gs://$ARTIFACT_BUCKET pronto."
fi

echo "=================================================================="
echo "☁️ 3. Executando deploy no Cloud Run com montagem GCS..."
echo "=================================================================="
# `--env-vars-file` substitui todas as variáveis e não se combina com `--update-env-vars`: sem esta
# linha no .env.yaml, a revisão sobe lendo a base de <OUTPUT_DIR>/base-plataforma, que não existe mais.
if ! grep -Eq "^BASE_PLATAFORMA_DIR: *[\"']?/app/base-plataforma[\"']? *$" .env.yaml; then
    echo "✖ .env.yaml sem BASE_PLATAFORMA_DIR: /app/base-plataforma — acrescente a linha e rode de novo."
    exit 1
fi
echo "=================================================================="

# --max-instances 1 é obrigatório: o Streamlit guarda os arquivos de download na
# memória do processo, e um GET em /media que caia em outra instância responde 404
# mesmo com os artefatos íntegros no bucket.
# --min-instances 1 e --no-cpu-throttling: as etapas rodam em segundo plano
# (`pipeline/execucao_fundo.py`) e precisam de CPU fora de requisição. Espelham o Terraform.
# Acesso público, por decisão do dono do projeto (23/09/2026); quem barra é o login do app.
# Para fechar a rede: `--no-allow-unauthenticated` e
# `gcloud run services proxy "$SERVICE_NAME" --region "$REGION"`.
# Comentários ficam ACIMA do comando: um `#` no meio da continuação com `\` o encerra ali.
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --allow-unauthenticated \
  --port 8080 \
  --memory 4Gi \
  --cpu 2 \
  --timeout 3600 \
  --session-affinity \
  --min-instances 1 \
  --max-instances 1 \
  --no-cpu-throttling \
  --add-volume "name=artifacts-vol,type=cloud-storage,bucket=$ARTIFACT_BUCKET" \
  --add-volume-mount "volume=artifacts-vol,mount-path=/app/output" \
  --add-volume "name=base-plataforma-vol,type=cloud-storage,bucket=$BASE_BUCKET,readonly=true" \
  --add-volume-mount "volume=base-plataforma-vol,mount-path=/app/base-plataforma" \
  --env-vars-file .env.yaml \
  --update-secrets "STITCH_API_KEY=$STITCH_SECRET:latest,AUTH_CREDENCIAIS=$AUTH_CREDENCIAIS_SECRET:latest,AUTH_SEGREDO_JWT=$AUTH_JWT_SECRET:latest" \
  --quiet

echo "=================================================================="
echo "✅ Deploy no Cloud Run concluído com sucesso!"
echo "=================================================================="
