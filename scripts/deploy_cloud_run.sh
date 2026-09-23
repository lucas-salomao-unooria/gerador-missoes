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
# A chave de API do Stitch NUNCA entra em arquivo: ela vive no Secret Manager, o
# recurso é declarado no Terraform (`gerador_missoes.tf`) e o valor é injetado por
# `gcloud secrets versions add`. Aqui só se referencia a versão mais recente.
STITCH_SECRET="plataforma-unooria-dev-stitch-api-key"

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
# ACESSO FECHADO (auditoria de 23/09/2026): a app não tem autenticação própria.
# Depois do deploy, acesse por:
#   gcloud run services proxy "$SERVICE_NAME" --region "$REGION" --project "$PROJECT_ID"
# e abra http://localhost:8080. Para liberar outra pessoa:
#   gcloud run services add-iam-policy-binding "$SERVICE_NAME" --region "$REGION" \
#     --member=user:<email> --role=roles/run.invoker
  --no-allow-unauthenticated \
  --port 8080 \
  --memory 4Gi \
  --cpu 2 \
  --timeout 3600 \
  --session-affinity \
  --max-instances 1 \
  --add-volume "name=artifacts-vol,type=cloud-storage,bucket=$ARTIFACT_BUCKET" \
  --add-volume-mount "volume=artifacts-vol,mount-path=/app/output" \
  --env-vars-file .env.yaml \
  --update-secrets "STITCH_API_KEY=$STITCH_SECRET:latest" \
  --quiet

echo "=================================================================="
echo "✅ Deploy no Cloud Run concluído com sucesso!"
echo "=================================================================="
