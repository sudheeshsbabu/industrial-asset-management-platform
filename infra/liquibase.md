Common Liquibase Commands
Action	Command
Check Pending Changes	docker compose run --rm liquibase status
Run Migrations	docker compose run --rm liquibase update
Rollback Last Change	docker compose run --rm liquibase rollbackCount 1
Validate Changelogs	docker compose run --rm liquibase validate
View SQL (Dry Run)	docker compose run --rm liquibase update-sql
Sync Changelog	docker compose run --rm liquibase changelog-sync