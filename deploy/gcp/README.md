# Open Wearables on Google Cloud Run

## Scope

This folder prepares the Sandtuari deployment of Open Wearables on Google Cloud Run.

Phase 1 deploys only the API service:

- Cloud Run service: `open-wearables-api`
- Region: `europe-west1`
- Artifact Registry: `open-wearables`
- Cloud SQL instance: `app-seguimiento-nutricion:europe-west1:medical-companion-db`
- Database: `open_wearables`
- Runtime service account: `open-wearables-run@app-seguimiento-nutricion.iam.gserviceaccount.com`

Workers, beat, Redis/Memorystore and Svix are intentionally separate follow-up steps.

## Preflight

Required infrastructure:

- Artifact Registry repo `open-wearables`.
- Cloud SQL database `open_wearables`.
- Cloud SQL database `svix`.
- Cloud SQL user `open_wearables_app`.
- Secret Manager secrets:
  - `open-wearables-db-instance-connection-name`
  - `open-wearables-db-name`
  - `open-wearables-db-user`
  - `open-wearables-db-password`
  - `open-wearables-secret-key`
  - `open-wearables-admin-email`
  - `open-wearables-admin-password`
  - `open-wearables-api-key`
  - `open-wearables-redis-host`
  - `open-wearables-redis-port`
  - `open-wearables-redis-password`

The runtime service account needs:

- `roles/cloudsql.client`
- secret-level `roles/secretmanager.secretAccessor` on the `open-wearables-*` secrets

## Deploy API

Default deploy is private. That is deliberate until OAuth callbacks and domain mapping are ready.

The API is attached to the `default` VPC/subnet and sends private-range traffic through Direct VPC egress so it can reach Memorystore Redis.

```bash
./deploy/gcp/deploy-cloud-run-api.sh
```

To expose the service publicly later:

```bash
ALLOW_UNAUTHENTICATED=true ./deploy/gcp/deploy-cloud-run-api.sh
```

`CORS_ORIGINS` must be JSON because `pydantic-settings` treats list fields as complex values:

```bash
CORS_ORIGINS='["https://sandtuari.fit","https://wearables.sandtuari.fit"]' ./deploy/gcp/deploy-cloud-run-api.sh
```

## Cloud SQL

The app supports Cloud SQL Unix sockets through:

```text
DB_INSTANCE_CONNECTION_NAME=app-seguimiento-nutricion:europe-west1:medical-companion-db
```

When this variable is set, the app builds its PostgreSQL URL with:

```text
host=/cloudsql/app-seguimiento-nutricion:europe-west1:medical-companion-db
```

Do not use public IP access as the default production path.

## Deploy worker and beat

The Celery worker and beat are deployed as private Cloud Run services with min/max instances fixed to 1.

```bash
./deploy/gcp/deploy-cloud-run-workers.sh
```

Both services expose a tiny local HTTP health listener because Cloud Run services require listening on `PORT`, while Celery itself does not expose HTTP.

## Svix decision

Svix is disabled in Phase 1 with:

```text
SVIX_ENABLED=false
```

Reason:

- Sandtuari does not yet have the final webhook receiver for wearable events.
- API/worker/beat can run without outgoing webhooks.
- Enabling Svix now would add another public/internal service and event surface before it is used clinically.

When Sandtuari is ready to consume events, deploy self-hosted Svix privately first, then set `SVIX_ENABLED=true` and `SVIX_SERVER_URL` to the internal Svix URL.

## Known follow-up

Before enabling provider OAuth:

- Map `wearables.sandtuari.fit`.
- Set `API_BASE_URL=https://wearables.sandtuari.fit`.
- Register exact OAuth callback URLs with each provider.
- Implement Sandtuari-side patient consent gate.
