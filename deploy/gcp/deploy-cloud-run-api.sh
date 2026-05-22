#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-app-seguimiento-nutricion}"
REGION="${REGION:-europe-west1}"
SERVICE_NAME="${SERVICE_NAME:-open-wearables-api}"
REPOSITORY="${REPOSITORY:-open-wearables}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-open-wearables-run@${PROJECT_ID}.iam.gserviceaccount.com}"
INSTANCE_CONNECTION_NAME="${INSTANCE_CONNECTION_NAME:-app-seguimiento-nutricion:europe-west1:medical-companion-db}"
API_BASE_URL="${API_BASE_URL:-https://wearables.sandtuari.fit}"
FRONTEND_URL="${FRONTEND_URL:-https://sandtuari.fit}"
CORS_ORIGINS="${CORS_ORIGINS:-[\"https://sandtuari.fit\"]}"
ALLOW_UNAUTHENTICATED="${ALLOW_UNAUTHENTICATED:-false}"
NETWORK="${NETWORK:-default}"
SUBNET="${SUBNET:-default}"
VPC_EGRESS="${VPC_EGRESS:-private-ranges-only}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TAG="${TAG:-$(git -C "${ROOT_DIR}" rev-parse --short HEAD)-$(date -u +%Y%m%d%H%M%S)}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}:${TAG}"
AUTH_FLAG="--no-allow-unauthenticated"
if [[ "${ALLOW_UNAUTHENTICATED}" == "true" ]]; then
  AUTH_FLAG="--allow-unauthenticated"
fi

gcloud builds submit "${ROOT_DIR}/backend" \
  --project="${PROJECT_ID}" \
  --tag="${IMAGE}"

gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --image="${IMAGE}" \
  --service-account="${SERVICE_ACCOUNT}" \
  --add-cloudsql-instances="${INSTANCE_CONNECTION_NAME}" \
  --command="scripts/start/app.sh" \
  --port=8000 \
  --cpu=1 \
  --memory=1Gi \
  --min-instances=0 \
  --max-instances=2 \
  --concurrency=40 \
  --timeout=300 \
  --no-cpu-throttling \
  --network="${NETWORK}" \
  --subnet="${SUBNET}" \
  --vpc-egress="${VPC_EGRESS}" \
  "${AUTH_FLAG}" \
  --set-env-vars="^|^ENVIRONMENT=production|API_PORT=8000|API_BASE_URL=${API_BASE_URL}|FRONTEND_URL=${FRONTEND_URL}|CORS_ORIGINS=${CORS_ORIGINS}|CORS_ALLOW_ALL=false|EMAIL_FROM_NAME=Sandtuari|REDIS_DB=0|SVIX_ENABLED=false" \
  --set-secrets="DB_INSTANCE_CONNECTION_NAME=open-wearables-db-instance-connection-name:latest,DB_NAME=open-wearables-db-name:latest,DB_USER=open-wearables-db-user:latest,DB_PASSWORD=open-wearables-db-password:latest,SECRET_KEY=open-wearables-secret-key:latest,ADMIN_EMAIL=open-wearables-admin-email:latest,ADMIN_PASSWORD=open-wearables-admin-password:latest,OPEN_WEARABLES_API_KEY=open-wearables-api-key:latest,REDIS_HOST=open-wearables-redis-host:latest,REDIS_PORT=open-wearables-redis-port:latest,REDIS_PASSWORD=open-wearables-redis-password:latest"

if [[ "${ALLOW_UNAUTHENTICATED}" == "true" ]]; then
  gcloud run services add-iam-policy-binding "${SERVICE_NAME}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --member="allUsers" \
    --role="roles/run.invoker" \
    --quiet
else
  gcloud run services remove-iam-policy-binding "${SERVICE_NAME}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --member="allUsers" \
    --role="roles/run.invoker" \
    --quiet || true
fi

gcloud run services describe "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --format="value(status.url)"
