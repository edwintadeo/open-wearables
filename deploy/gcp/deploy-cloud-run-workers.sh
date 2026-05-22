#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-app-seguimiento-nutricion}"
REGION="${REGION:-europe-west1}"
API_SERVICE_NAME="${API_SERVICE_NAME:-open-wearables-api}"
SERVICE_ACCOUNT="${SERVICE_ACCOUNT:-open-wearables-run@${PROJECT_ID}.iam.gserviceaccount.com}"
INSTANCE_CONNECTION_NAME="${INSTANCE_CONNECTION_NAME:-app-seguimiento-nutricion:europe-west1:medical-companion-db}"
NETWORK="${NETWORK:-default}"
SUBNET="${SUBNET:-default}"
VPC_EGRESS="${VPC_EGRESS:-private-ranges-only}"
IMAGE="${IMAGE:-$(gcloud run services describe "${API_SERVICE_NAME}" --project="${PROJECT_ID}" --region="${REGION}" --format='value(spec.template.spec.containers[0].image)')}"

COMMON_ENV="ENVIRONMENT=production,REDIS_DB=0,SVIX_ENABLED=false"
COMMON_SECRETS="DB_INSTANCE_CONNECTION_NAME=open-wearables-db-instance-connection-name:latest,DB_NAME=open-wearables-db-name:latest,DB_USER=open-wearables-db-user:latest,DB_PASSWORD=open-wearables-db-password:latest,SECRET_KEY=open-wearables-secret-key:latest,OPEN_WEARABLES_API_KEY=open-wearables-api-key:latest,REDIS_HOST=open-wearables-redis-host:latest,REDIS_PORT=open-wearables-redis-port:latest,REDIS_PASSWORD=open-wearables-redis-password:latest"

deploy_background_service() {
  local service_name="$1"
  local command="$2"
  local cpu="${3:-1}"
  local memory="${4:-1Gi}"

  gcloud run deploy "${service_name}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --image="${IMAGE}" \
    --service-account="${SERVICE_ACCOUNT}" \
    --add-cloudsql-instances="${INSTANCE_CONNECTION_NAME}" \
    --command="${command}" \
    --port=8080 \
    --cpu="${cpu}" \
    --memory="${memory}" \
    --min-instances=1 \
    --max-instances=1 \
    --concurrency=1 \
    --timeout=3600 \
    --no-cpu-throttling \
    --network="${NETWORK}" \
    --subnet="${SUBNET}" \
    --vpc-egress="${VPC_EGRESS}" \
    --no-allow-unauthenticated \
    --set-env-vars="${COMMON_ENV}" \
    --set-secrets="${COMMON_SECRETS}"

  gcloud run services remove-iam-policy-binding "${service_name}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --member="allUsers" \
    --role="roles/run.invoker" \
    --quiet || true
}

deploy_background_service open-wearables-worker scripts/start/cloud-run-worker.sh 1 1Gi
deploy_background_service open-wearables-beat scripts/start/cloud-run-beat.sh 1 512Mi

gcloud run services list \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --filter='metadata.name:(open-wearables-worker OR open-wearables-beat)' \
  --format='table(metadata.name,status.url,status.conditions[0].status,status.latestReadyRevisionName)'
