.DEFAULT_GOAL := help
COMPOSE = docker compose
EXEC_WEB = $(COMPOSE) exec web
MANAGE = $(EXEC_WEB) python manage.py

.PHONY: help
help: ## Show available commands
	@echo "Drone Academy Examination Platform (Docker)"
	@echo "=========================================="
	@echo "Usage: make [target]"
	@echo ""
	@echo "Container Lifecycle:"
	@echo "  up              Start containers in background (runs migrations; no demo credentials)"
	@echo "  down            Stop and remove containers"
	@echo "  restart         Restart containers"
	@echo "  build           Rebuild Docker images"
	@echo "  logs            Follow container logs"
	@echo "  ps              List running containers"
	@echo ""
	@echo "Application & Operations (inside Docker):"
	@echo "  test            Run automated test suite"
	@echo "  check           Run Django system and security checks"
	@echo "  superuser       Create an admin account interactively"
	@echo "  migrate         Apply database migrations manually"
	@echo "  audit           Verify cryptographic audit trail chain integrity"
	@echo "  shell           Open interactive Django shell in web container"
	@echo "  bash            Open shell in web container"
	@echo ""
	@echo "Backups & Maintenance:"
	@echo "  backup-db       Dump PostgreSQL database to backup-db.dump"
	@echo "  backup-media    Archive media volume to backups/ directory"
	@echo "  clean           Stop containers and remove volumes"

# --- Container Lifecycle ---
.PHONY: up
up: ## Start containers in background
	$(COMPOSE) up -d --build

.PHONY: down
down: ## Stop containers
	$(COMPOSE) down

.PHONY: restart
restart: ## Restart containers
	$(COMPOSE) restart

.PHONY: build
build: ## Rebuild containers
	$(COMPOSE) build

.PHONY: logs
logs: ## Tail container logs
	$(COMPOSE) logs -f

.PHONY: ps
ps: ## Show running containers
	$(COMPOSE) ps

# --- App Operations ---
.PHONY: test
test: ## Run test suite inside container
	$(MANAGE) test

.PHONY: check
check: ## Run security & deploy checks inside container
	$(MANAGE) check --deploy

.PHONY: superuser
superuser: ## Create an admin user inside container
	$(MANAGE) createsuperuser

.PHONY: migrate
migrate: ## Run migrations manually inside container
	$(MANAGE) migrate

.PHONY: audit
audit: ## Verify audit trail chain integrity inside container
	$(MANAGE) verify_audit_chain

.PHONY: shell
shell: ## Django shell inside web container
	$(MANAGE) shell

.PHONY: bash
bash: ## Shell inside web container
	$(EXEC_WEB) sh

# --- Backups & Maintenance ---
.PHONY: backup-db
backup-db: ## Dump PostgreSQL database
	$(COMPOSE) exec -T db sh -c 'pg_dump -Fc -U "$$POSTGRES_USER" "$$POSTGRES_DB"' > backup-db.dump
	@echo "Saved backup-db.dump"

.PHONY: backup-media
backup-media: ## Archive media volume
	mkdir -p backups
	$(COMPOSE) exec -T web tar czf - -C /app/media . > backups/media-backup.tgz
	@echo "Saved backups/media-backup.tgz"

.PHONY: clean
clean: ## Remove containers and anonymous volumes
	$(COMPOSE) down -v
