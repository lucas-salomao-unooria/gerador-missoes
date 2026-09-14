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

# --max-instances 1 é obrigatório: o Streamlit guarda os arquivos de download na
# memória do processo, e um GET em /media que caia em outra instância responde 404
# mesmo com os artefatos íntegros no bucket.
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
  --max-instances 1 \
  --add-volume "name=artifacts-vol,type=cloud-storage,bucket=$ARTIFACT_BUCKET" \
  --add-volume-mount "volume=artifacts-vol,mount-path=/app/output" \
  --env-vars-file .env.yaml \
  --quiet

echo "=================================================================="
echo "✅ Deploy no Cloud Run concluído com sucesso!"
echo "=================================================================="
