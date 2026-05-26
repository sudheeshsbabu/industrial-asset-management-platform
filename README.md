# Industrial Asset Management Platform

AssetOps is a full-stack industrial asset management application for tracking machines, robots, devices, sites, configuration, and operational metadata across facilities.

The project currently includes an async Python backend, a React dashboard frontend, PostgreSQL schema management, Docker-based local development, and Kubernetes deployment assets with a Helm chart for local Minikube review.

## Reviewer Summary

This repository demonstrates:

- An `aiohttp` backend with layered handlers, services, repositories, middleware, and async PostgreSQL access.
- A React + Vite frontend for listing, viewing, creating, and managing assets.
- PostgreSQL 16 as the primary relational database.
- Runtime configuration layering from database rows, `.env`, and `.env.local`.
- Background tasks that refresh configuration and watch environment files.
- Liquibase database changesets for Kubernetes and Docker workflows.
- Docker Compose for local service orchestration.
- Kubernetes manifests and a Helm chart for deploying backend, frontend, Postgres, and Liquibase.

## Architecture

```text
React + Vite frontend
        |
        | HTTP
        v
aiohttp backend
  - routes and handlers
  - middleware: request id, request logging, error handling
  - services: business logic
  - repositories: asyncpg SQL access
  - config manager and background refresh tasks
        |
        v
PostgreSQL 16
  - assets
  - app_config
  - audit/config support tables and triggers
```

For local Kubernetes, the same application is deployed as:

```text
frontend Deployment + Service
backend Deployment + Service
postgres Deployment + Service + PVC + Secret
liquibase Kubernetes Job
```

## Technology Stack

| Area | Tools |
|---|---|
| Backend | Python 3.14, aiohttp, aiohttp-cors, asyncpg, pydantic, pydantic-settings |
| Frontend | React 19, Vite, TypeScript, MUI, React Router, React Query, Zustand, Axios |
| Database | PostgreSQL 16 |
| Migrations | Liquibase changesets |
| Local runtime | Docker, Docker Compose, uv |
| Kubernetes | kubectl, Minikube, Helm |
| Tests | pytest, pytest-asyncio |

## Key Capabilities

- `GET /health` health check endpoint.
- `GET /assets` paginated asset listing.
- `GET /assets/{id}` asset detail endpoint.
- `POST /assets` asset creation endpoint.
- Centralized JSON error handling.
- Request correlation with `X-Request-ID`.
- Structured request logging.
- Runtime configuration sync from `.env`, `.env.local`, and the `app_config` table.
- Frontend screens for asset list, asset detail, and asset creation.

## Project Structure

```text
.
|-- app/                         # aiohttp backend
|   |-- api/                     # request handlers and route registration
|   |-- core/                    # config, logging, exceptions, protocols
|   |-- db/                      # asyncpg pool setup
|   |-- middleware/              # request id, logging, error handling
|   |-- models/                  # pydantic domain models
|   |-- repositories/            # database access
|   `-- services/                # business logic
|
|-- frontend/                    # React + Vite dashboard
|   |-- src/components/          # asset and common UI components
|   |-- src/hooks/               # React Query hooks
|   |-- src/pages/               # routed pages
|   |-- src/services/            # API clients
|   `-- src/store/               # frontend state
|
|-- infra/                       # database and Liquibase infrastructure
|   |-- changesets/              # Liquibase YAML changesets
|   |-- liquibase/               # Liquibase Docker config
|   |-- postgres/                # local Postgres initialization
|   |-- procedures/              # SQL procedures
|   |-- tables/                  # SQL table definitions
|   `-- triggers/                # SQL triggers
|
|-- k8s/                         # Kubernetes manifests and Helm chart
|   |-- helm/assetops/           # Helm chart
|   `-- README.md                # Kubernetes deployment guide
|
|-- tests/                       # unit and integration tests
|-- docker-compose.yml           # local Postgres/Liquibase workflow
|-- Dockerfile                   # backend image
`-- pyproject.toml               # backend package and test config
```

## Local Development

### Prerequisites

- Docker Desktop
- Python 3.14
- `uv`
- Node.js and npm

### Backend

Start local services:

```bash
docker compose up -d
```

Install Python dependencies:

```bash
uv sync
```

Start the backend:

```bash
uv run python -m app.main
```

The backend runs on `http://localhost:8080` by default.

### Frontend

Install frontend dependencies:

```bash
cd frontend
npm install
```

Run the Vite dev server:

```bash
npm run dev
```

Build the frontend:

```bash
npm run build
```

## Configuration

Configuration is layered in priority order:

| Priority | Source | Purpose |
|---|---|---|
| Highest | `.env.local` | Local developer overrides |
| Medium | `.env` | Base environment configuration |
| Lowest | `app_config` table | Database-backed runtime configuration |

On startup, the backend loads settings, syncs base environment values to the database, and starts background tasks that keep runtime configuration refreshed.

For the deeper implementation notes, see [docs/config-env-db-sync.md](docs/config-env-db-sync.md).

## Database and Migrations

The project contains two migration-oriented workflows:

- Liquibase under [infra/](infra/) for containerized and Kubernetes deployment flows.

Useful Liquibase commands through Docker Compose:

```bash
docker compose run --rm liquibase validate
docker compose run --rm liquibase update-sql
```

## Kubernetes and Helm

The Kubernetes guide has been updated with the current local deployment workflow:

[k8s/README.md](k8s/README.md)

It covers:

- Running the app locally on Minikube.
- Building backend, frontend, and Liquibase images inside Minikube's Docker daemon.
- Deploying with raw Kubernetes manifests or the Helm chart at [k8s/helm/assetops](k8s/helm/assetops).
- Using `helm upgrade --install` with [k8s/helm/assetops/values-local.yaml](k8s/helm/assetops/values-local.yaml).
- Why `imagePullPolicy: Never` requires exact local image tags inside the Minikube node.
- How to troubleshoot `ErrImageNeverPull`.
- When to use Helm versus kubectl.

Short version for the Helm local path:

```powershell
minikube start
minikube docker-env | Invoke-Expression

docker build -t assetops-backend:v1 .
docker build -t assetops-frontend:v1 ./frontend
docker build -f infra/liquibase/Dockerfile -t assetops-liquibase:v1 .

helm upgrade --install assetops ./k8s/helm/assetops `
  -n assetops `
  -f ./k8s/helm/assetops/values-local.yaml `
  --create-namespace

kubectl get pods -n assetops
helm status assetops -n assetops
```

After rebuilding the same image tag, restart the affected Deployment:

```powershell
kubectl rollout restart deployment/backend -n assetops
kubectl rollout restart deployment/frontend -n assetops
```

Helm manages release configuration. kubectl is still used to inspect and operate the live Kubernetes resources created by that release.

## Tests

Run backend tests:

```bash
uv run pytest
```

Run frontend checks:

```bash
cd frontend
npm run lint
npm run build
```

## Documentation

| Topic | Link |
|---|---|
| Kubernetes, Minikube, Helm, and image troubleshooting | [k8s/README.md](k8s/README.md) |
| Runtime config sync from env files and database | [docs/config-env-db-sync.md](docs/config-env-db-sync.md) |
| Liquibase infrastructure notes | [infra/liquibase.md](infra/liquibase.md) |
