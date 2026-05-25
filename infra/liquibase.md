Common Liquibase Commands
Action	Command
Check Pending Changes	docker compose run --rm liquibase status
Run Migrations	docker compose run --rm liquibase update
Rollback Last Change	docker compose run --rm liquibase rollbackCount 1
Validate Changelogs	docker compose run --rm liquibase validate
View SQL (Dry Run)	docker compose run --rm liquibase update-sql
Sync Changelog	docker compose run --rm liquibase changelog-sync

Kubernetes / Minikube
Build Image	docker build -f infra/liquibase/Dockerfile -t assetops-liquibase:local .
Load Image	minikube image load assetops-liquibase:local
Re-run Job	kubectl delete job liquibase-update -n assetops --ignore-not-found; kubectl apply -f k8s/liquibase-job.yaml
View Logs	kubectl logs job/liquibase-update -n assetops
