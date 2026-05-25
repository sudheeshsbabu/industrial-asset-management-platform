# Local Kubernetes Deployment Guide

This guide explains how to run the Industrial Asset Management Platform locally with Minikube and kubectl.

The expected local Kubernetes setup is:

- PostgreSQL 16 as the database
- Liquibase as a Kubernetes Job for migrations
- aiohttp backend as a Deployment and Service
- React frontend as a Deployment and Service

## Prerequisites

Install and verify:

```bash
docker --version
kubectl version --client
minikube version
```

Start Docker Desktop before starting Minikube.

## Start Minikube

```bash
minikube start
kubectl get nodes
```

The Minikube node should show `Ready`.

## Use Minikube Docker

For local images with `imagePullPolicy: Never`, build images inside Minikube's Docker daemon.

PowerShell:

```powershell
minikube docker-env | Invoke-Expression
```

Bash:

```bash
eval $(minikube docker-env)
```

Verify Docker is now pointing at Minikube:

```bash
docker images
```

## Build Local Images

From the project root:

```bash
docker build -t assetops-backend:local .
docker build -t assetops-frontend:local ./frontend
docker build -t assetops-liquibase:local ./infra/liquibase
```

If the Liquibase image needs access to `infra/changesets`, `infra/tables`, `infra/procedures`, and related files, make sure those files are copied into the image. Docker Compose mounts `./infra` at runtime, but Kubernetes usually needs the files baked into the image or mounted through a ConfigMap.

## Apply Kubernetes Manifests

Apply resources in dependency order:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres-secret.yaml
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/backend-configmap.yaml
```

Wait for Postgres:

```bash
kubectl get pods -n assetops
kubectl logs deployment/postgres -n assetops
```

Run migrations:

```bash
kubectl apply -f k8s/liquibase-job.yaml
kubectl logs job/liquibase-update -n assetops
```

Deploy the app:

```bash
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml
```

## Access Services

Backend:

```bash
minikube service backend -n assetops
```

Or:

```bash
kubectl port-forward service/backend 8080:8080 -n assetops
```

Frontend:

```bash
minikube service frontend -n assetops
```

Or:

```bash
kubectl port-forward service/frontend 80:80 -n assetops
```

## Deploy Backend Code Changes

After changing backend code:

```bash
docker build -t assetops-backend:local .
kubectl rollout restart deployment/backend -n assetops
kubectl rollout status deployment/backend -n assetops
kubectl logs deployment/backend -n assetops
```

Because the image tag stays `assetops-backend:local`, restarting the Deployment is required so Kubernetes starts a new Pod using the rebuilt local image.

If the Pod still appears to use old code, delete it and let the Deployment recreate it:

```bash
kubectl delete pod -l app=backend -n assetops
kubectl get pods -n assetops
```

## Deploy Frontend Code Changes

After changing frontend code:

```bash
docker build -t assetops-frontend:local ./frontend
kubectl rollout restart deployment/frontend -n assetops
kubectl rollout status deployment/frontend -n assetops
kubectl logs deployment/frontend -n assetops
```

If the browser still shows old frontend assets, hard refresh the page or reopen the Minikube service URL.

## Deploy Liquibase Migration Changes

After adding or editing Liquibase changesets:

```bash
docker build -t assetops-liquibase:local ./infra/liquibase
kubectl delete job liquibase-update -n assetops --ignore-not-found
kubectl apply -f k8s/liquibase-job.yaml
kubectl logs job/liquibase-update -n assetops
```

Check whether the Job succeeded:

```bash
kubectl get jobs -n assetops
kubectl get pods -n assetops
```

For a dry-run SQL preview, run Liquibase locally with Docker Compose:

```bash
docker compose run --rm liquibase update-sql
```

For validation:

```bash
docker compose run --rm liquibase validate
```

## Full Redeploy Flow

Use this when backend, frontend, and migrations all changed:

```bash
docker build -t assetops-backend:local .
docker build -t assetops-frontend:local ./frontend
docker build -t assetops-liquibase:local ./infra/liquibase

kubectl delete job liquibase-update -n assetops --ignore-not-found
kubectl apply -f k8s/liquibase-job.yaml
kubectl logs job/liquibase-update -n assetops

kubectl rollout restart deployment/backend -n assetops
kubectl rollout restart deployment/frontend -n assetops

kubectl rollout status deployment/backend -n assetops
kubectl rollout status deployment/frontend -n assetops
```

## Useful kubectl Commands

List all app resources:

```bash
kubectl get all -n assetops
```

List Pods:

```bash
kubectl get pods -n assetops
```

Watch Pods:

```bash
kubectl get pods -n assetops -w
```

View backend logs:

```bash
kubectl logs deployment/backend -n assetops
```

View frontend logs:

```bash
kubectl logs deployment/frontend -n assetops
```

View Postgres logs:

```bash
kubectl logs deployment/postgres -n assetops
```

View Liquibase Job logs:

```bash
kubectl logs job/liquibase-update -n assetops
```

Describe a failing Pod:

```bash
kubectl describe pod <pod-name> -n assetops
```

Open a shell in the backend Pod:

```bash
kubectl exec -it deployment/backend -n assetops -- sh
```

Open a Postgres shell:

```bash
kubectl exec -it deployment/postgres -n assetops -- psql -U postgres -d assetops
```

Check Services:

```bash
kubectl get svc -n assetops
```

Check Deployments:

```bash
kubectl get deployments -n assetops
```

Check rollout history:

```bash
kubectl rollout history deployment/backend -n assetops
kubectl rollout history deployment/frontend -n assetops
```

Restart a Deployment:

```bash
kubectl rollout restart deployment/backend -n assetops
kubectl rollout restart deployment/frontend -n assetops
```

Delete recreated Pods manually:

```bash
kubectl delete pod -l app=backend -n assetops
kubectl delete pod -l app=frontend -n assetops
```

## Configuration Notes

Inside Kubernetes, the backend must connect to Postgres through the Kubernetes Service name:

```env
DB_HOST=postgres
```

Do not use:

```env
DB_HOST=localhost
```

Inside a backend Pod, `localhost` means the backend container itself, not the Postgres Pod.

Recommended split:

- Non-sensitive values in ConfigMaps
- Passwords and secrets in Secrets
- Database schema changes through Liquibase Jobs

## Cleanup

Delete only this application:

```bash
kubectl delete namespace assetops
```

Stop Minikube:

```bash
minikube stop
```

Delete the entire local cluster:

```bash
minikube delete
```

