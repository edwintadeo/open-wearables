#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-app-seguimiento-nutricion}"
REGION="${REGION:-europe-west1}"
SERVICE_NAME="${SERVICE_NAME:-open-wearables-frontend}"
API_SERVICE_NAME="${API_SERVICE_NAME:-open-wearables-api}"
REPOSITORY="${REPOSITORY:-open-wearables}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-open-wearables-run@${PROJECT_ID}.iam.gserviceaccount.com}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TAG="${TAG:-$(git -C "${ROOT_DIR}" rev-parse --short HEAD)-frontend-$(date -u +%Y%m%d%H%M%S)}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}:${TAG}"
VITE_API_URL="${VITE_API_URL:-$(gcloud run services describe "${API_SERVICE_NAME}" --project="${PROJECT_ID}" --region="${REGION}" --format='value(status.url)')}"

gcloud builds submit "${ROOT_DIR}/frontend" \
  --project="${PROJECT_ID}" \
  --config="${ROOT_DIR}/deploy/gcp/cloudbuild-frontend.yaml" \
  --substitutions="_IMAGE=${IMAGE},_VITE_API_URL=${VITE_API_URL}"

gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --image="${IMAGE}" \
  --service-account="${SERVICE_ACCOUNT}" \
  --port=3000 \
  --cpu=1 \
  --memory=512Mi \
  --min-instances=0 \
  --max-instances=2 \
  --concurrency=80 \
  --timeout=300 \
  --allow-unauthenticated \
  --set-env-vars="NODE_ENV=production,HOST=0.0.0.0,VITE_API_URL=${VITE_API_URL}"

FRONTEND_URL="$(gcloud run services describe "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --format='value(status.url)')"

gcloud run services update "${API_SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --update-env-vars="^|^FRONTEND_URL=${FRONTEND_URL}|CORS_ORIGINS=[\"https://sandtuari.fit\",\"https://wearables.sandtuari.fit\",\"${FRONTEND_URL}\"]"

echo "${FRONTEND_URL}"
