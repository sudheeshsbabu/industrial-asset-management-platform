# Local Kubernetes Deployment Guide

This guide explains how to run the Industrial Asset Management Platform locally with Minikube, kubectl, and the included Helm chart.

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
helm version
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

This is important because Minikube runs Kubernetes inside its own node. Images built with your normal Docker Desktop daemon are stored on your host machine, but Pods run inside the Minikube node. When a Deployment uses `imagePullPolicy: Never`, Kubernetes will not pull the image from Docker Hub or another registry. It will only start the Pod if the exact image name and tag already exist inside the node's container runtime.

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

Run the `docker-env` command again when you open a new terminal session.

## Build Local Images

From the project root:

```bash
docker build -t assetops-backend:local .
docker build -t assetops-frontend:local ./frontend
docker build -f infra/liquibase/Dockerfile -t assetops-liquibase:local .
```

The raw Kubernetes manifests in `k8s/` use the `:local` tag. The Helm local values file uses the `:v1` tag by default, so build matching tags before installing with Helm:

```bash
docker build -t assetops-backend:v1 .
docker build -t assetops-frontend:v1 ./frontend
docker build -f infra/liquibase/Dockerfile -t assetops-liquibase:v1 .
```

If the Liquibase image needs access to `infra/changesets`, `infra/tables`, `infra/procedures`, and related files, make sure those files are copied into the image. Docker Compose mounts `./infra` at runtime, but Kubernetes usually needs the files baked into the image or mounted through a ConfigMap.

## Deploy with Helm

The Helm chart lives at:

```bash
k8s/helm/assetops
```

The local override file is:

```bash
k8s/helm/assetops/values-local.yaml
```

It sets local image names and `imagePullPolicy: Never` for backend, frontend, and Liquibase:

```yaml
backend:
  image:
    repository: assetops-backend
    tag: v1
    pullPolicy: Never

frontend:
  image:
    repository: assetops-frontend
    tag: v1
    pullPolicy: Never

liquibase:
  image:
    repository: assetops-liquibase
    tag: v1
    pullPolicy: Never
```

Install or upgrade the release:

```bash
helm upgrade --install assetops ./k8s/helm/assetops -n assetops -f ./k8s/helm/assetops/values-local.yaml --create-namespace
```

Check the Helm release:

```bash
helm status assetops -n assetops
helm list -n assetops
```

Check the Kubernetes resources created by Helm:

```bash
kubectl get all -n assetops
kubectl get pods -n assetops
```

Helm manages the release and renders Kubernetes objects. kubectl inspects and operates the actual live Kubernetes resources created by that release.

Use Helm when you change chart templates or values:

```bash
helm upgrade assetops ./k8s/helm/assetops -n assetops -f ./k8s/helm/assetops/values-local.yaml
```

Use kubectl when you need to inspect Pods, view logs, describe failures, restart Deployments, or port-forward Services:

```bash
kubectl describe pod <pod-name> -n assetops
kubectl logs deployment/backend -n assetops
kubectl rollout restart deployment/backend -n assetops
kubectl port-forward service/frontend 80:80 -n assetops
```

## Helm Local Development Loop

When rebuilding images with the same tag, such as `assetops-backend:v1`, Helm does not automatically know the image contents changed because the chart values are unchanged. Rebuild the image inside Minikube and restart the Deployment:

```powershell
minikube docker-env | Invoke-Expression

docker build -t assetops-backend:v1 .
docker build -t assetops-frontend:v1 ./frontend

kubectl rollout restart deployment/backend -n assetops
kubectl rollout restart deployment/frontend -n assetops

kubectl rollout status deployment/backend -n assetops
kubectl rollout status deployment/frontend -n assetops
```

For a Helm-only application update, build a new image tag and pass that tag to `helm upgrade`:

```powershell
docker build -t assetops-backend:v2 .
docker build -t assetops-frontend:v2 ./frontend

helm upgrade assetops ./k8s/helm/assetops `
  -n assetops `
  -f ./k8s/helm/assetops/values-local.yaml `
  --set backend.image.tag=v2 `
  --set frontend.image.tag=v2
```

Newer Helm 3 versions do not support the old `--recreate-pods` flag. Use `kubectl rollout restart` after rebuilding the same tag, or use a new image tag with `helm upgrade`.

To rerun the Liquibase Job with Helm after rebuilding the same tag:

```bash
docker build -f infra/liquibase/Dockerfile -t assetops-liquibase:v1 .

helm upgrade assetops ./k8s/helm/assetops -n assetops -f ./k8s/helm/assetops/values-local.yaml
kubectl logs job/liquibase-update -n assetops
```

The Helm chart runs Liquibase as a `pre-install,pre-upgrade` hook and deletes the
previous hook Job before creating the next one.

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
kubectl delete job liquibase-update -n assetops --ignore-not-found
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
docker build -f infra/liquibase/Dockerfile -t assetops-liquibase:local .
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
docker build -f infra/liquibase/Dockerfile -t assetops-liquibase:local .

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

## Useful Helm Commands

Show release status:

```bash
helm status assetops -n assetops
```

List releases in the namespace:

```bash
helm list -n assetops
```

Preview rendered manifests without applying them:

```bash
helm template assetops ./k8s/helm/assetops -n assetops -f ./k8s/helm/assetops/values-local.yaml
```

Preview an upgrade:

```bash
helm upgrade assetops ./k8s/helm/assetops -n assetops -f ./k8s/helm/assetops/values-local.yaml --dry-run
```

Uninstall the Helm release:

```bash
helm uninstall assetops -n assetops
```

## Troubleshooting Image Errors

If `helm status` or `kubectl get pods` shows `ErrImageNeverPull`, the Pod is configured with `imagePullPolicy: Never` and the exact image is missing inside the Kubernetes node.

Check the image name and tag in the Pod:

```bash
kubectl describe pod <pod-name> -n assetops
```

Then build the matching image tag inside Minikube:

```powershell
minikube docker-env | Invoke-Expression
docker build -t assetops-backend:v1 .
docker build -t assetops-frontend:v1 ./frontend
```

Restart the affected Deployments:

```bash
kubectl rollout restart deployment/backend -n assetops
kubectl rollout restart deployment/frontend -n assetops
```

Common causes:

- Built `assetops-backend:local` but Helm is deploying `assetops-backend:v1`
- Built the image before running `minikube docker-env | Invoke-Expression`
- Opened a new terminal and forgot to run `minikube docker-env | Invoke-Expression` again
- Changed code but reused the same image tag without restarting the Deployment

If you use a real image registry instead of local Minikube images, push the images to that registry and change `pullPolicy` to `IfNotPresent` or `Always`.

## Helm vs kubectl

Use Helm to manage the release:

- Install the app
- Upgrade chart templates
- Change values such as image tags, ports, or configuration
- Uninstall the release

Use kubectl to operate the live cluster:

- Inspect Pods, Services, Jobs, and Deployments
- Read logs
- Describe failing resources
- Restart Deployments after rebuilding the same local image tag
- Port-forward Services for local access

Both tools are part of the workflow. Helm owns the desired release configuration; kubectl talks directly to Kubernetes resources that are running now.

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
