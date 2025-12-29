.PHONY: help install install-dev clean format lint typecheck test test-cov security check-all run services-up services-down services-restart migrate migrate-create migrate-downgrade migrate-downgrade-base migrate-current migrate-history migrate-check seed db-reset

# Default Python interpreter
PYTHON := python3
UV := uv

# Source directories
SRC_DIR := src
TEST_DIR := tests

# Colors for output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@printf "$(CYAN)Available targets:$(NC)\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Install project dependencies
	@printf "$(CYAN)Installing project dependencies...$(NC)\n"
	$(UV) sync

install-dev: ## Install project dependencies including dev tools
	@printf "$(CYAN)Installing project dependencies with dev tools...$(NC)\n"
	$(UV) sync --extra dev
	@printf "$(GREEN)✓ Development dependencies installed$(NC)\n"

clean: ## Clean up generated files and caches
	@printf "$(CYAN)Cleaning up...$(NC)\n"
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -r {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -r {} + 2>/dev/null || true
	rm -f .coverage coverage.xml htmlcov/.gitkeep 2>/dev/null || true
	@printf "$(GREEN)✓ Cleanup complete$(NC)\n"

format: ## Format code with ruff
	@printf "$(CYAN)Formatting code with ruff...$(NC)\n"
	$(UV) run ruff format $(SRC_DIR)
	@printf "$(GREEN)✓ Code formatted$(NC)\n"

format-check: ## Check code formatting without making changes
	@printf "$(CYAN)Checking code formatting...$(NC)\n"
	$(UV) run ruff format --check $(SRC_DIR)

lint: ## Lint code with ruff
	@printf "$(CYAN)Linting code with ruff...$(NC)\n"
	$(UV) run ruff check $(SRC_DIR)
	@printf "$(GREEN)✓ Linting complete$(NC)\n"

lint-fix: ## Lint and auto-fix code with ruff
	@printf "$(CYAN)Linting and fixing code with ruff...$(NC)\n"
	$(UV) run ruff check --fix $(SRC_DIR)
	@printf "$(GREEN)✓ Linting and fixes complete$(NC)\n"

typecheck: ## Type check code with mypy
	@printf "$(CYAN)Type checking with mypy...$(NC)\n"
	$(UV) run mypy $(SRC_DIR)
	@printf "$(GREEN)✓ Type checking complete$(NC)\n"

test: ## Run tests with pytest
	@printf "$(CYAN)Running tests...$(NC)\n"
	$(UV) run pytest $(TEST_DIR) -v
	@printf "$(GREEN)✓ Tests complete$(NC)\n"

test-cov: ## Run tests with coverage report
	@printf "$(CYAN)Running tests with coverage...$(NC)\n"
	$(UV) run pytest $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=term-missing --cov-report=html -v
	@printf "$(GREEN)✓ Coverage report generated in htmlcov/$(NC)\n"

test-fast: ## Run tests without coverage (faster)
	@printf "$(CYAN)Running tests (fast mode)...$(NC)\n"
	$(UV) run pytest $(TEST_DIR) -v --no-cov

security: ## Run security checks with bandit
	@printf "$(CYAN)Running security checks with bandit...$(NC)\n"
	$(UV) run bandit -r $(SRC_DIR) -f json -o bandit-report.json || true
	$(UV) run bandit -r $(SRC_DIR)
	@printf "$(GREEN)✓ Security check complete$(NC)\n"

safety: ## Check dependencies for known vulnerabilities
	@printf "$(CYAN)Checking dependencies for vulnerabilities...$(NC)\n"
	$(UV) run safety check --json || true
	$(UV) run safety check
	@printf "$(GREEN)✓ Safety check complete$(NC)\n"

check-all: format-check lint typecheck test ## Run all checks (format, lint, typecheck, test)
	@printf "$(GREEN)✓ All checks passed!$(NC)\n"

fix-all: format lint-fix ## Format and fix all linting issues
	@printf "$(GREEN)✓ All fixes applied!$(NC)\n"

services-up: ## Start docker-compose services
	@printf "$(CYAN)Starting docker-compose services...$(NC)\n"
	docker-compose up -d
	@printf "$(GREEN)✓ Services started$(NC)\n"

services-down: ## Stop docker-compose services
	@printf "$(CYAN)Stopping docker-compose services...$(NC)\n"
	docker-compose down
	@printf "$(GREEN)✓ Services stopped$(NC)\n"

services-restart: services-down services-up ## Restart docker-compose services

services-logs: ## View docker-compose service logs
	docker-compose logs -f

run: ## Run the Discord bot
	@printf "$(CYAN)Starting Discord bot...$(NC)\n"
	$(UV) run python -m ds_discord_bot

run-dev: ## Run the Discord bot in development mode (with auto-reload if available)
	@printf "$(CYAN)Starting Discord bot in development mode with auto-reload...$(NC)\n"
	@printf "$(YELLOW)Note: Install dev dependencies with 'make install-dev' if watchfiles is missing$(NC)\n"
	$(UV) run python -m ds_discord_bot.dev_runner

pre-commit: clean format lint-fix typecheck test ## Run all pre-commit checks
	@printf "$(GREEN)✓ Pre-commit checks passed!$(NC)\n"

ci: install-dev format-check lint typecheck test-cov security ## Run CI pipeline checks
	@printf "$(GREEN)✓ CI checks passed!$(NC)\n"

seed: ## Seed the database with initial game data (character classes, stats, etc.)
	@printf "$(CYAN)Seeding database with initial game data...$(NC)\n"
	$(UV) run python -m ds_common.seed_data
	@printf "$(GREEN)✓ Database seeded!$(NC)\n"

seed-world: ## Seed world data (regions, factions, calendar events, baseline lore)
	@printf "$(CYAN)Seeding world data...$(NC)\n"
	$(UV) run python -m ds_common.world_seed_data
	@printf "$(GREEN)✓ World data seeded!$(NC)\n"

seed-all: seed seed-world ## Seed all data (game data + world data)
	@printf "$(GREEN)✓ All data seeded!$(NC)\n"

migrate: ## Apply all pending database migrations
	@printf "$(CYAN)Applying database migrations...$(NC)\n"
	$(UV) run alembic upgrade heads
	@printf "$(GREEN)✓ Migrations applied!$(NC)\n"

migrate-create: ## Create a new migration (usage: make migrate-create MSG="description")
	@printf "$(CYAN)Creating new migration...$(NC)\n"
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)Error: MSG parameter required. Usage: make migrate-create MSG=\"description\"$(NC)"; \
		exit 1; \
	fi
	$(UV) run alembic revision --autogenerate -m "$(MSG)"
	@printf "$(GREEN)✓ Migration created!$(NC)\n"

migrate-downgrade: ## Rollback the last migration
	@printf "$(CYAN)Rolling back last migration...$(NC)\n"
	$(UV) run alembic downgrade -1
	@printf "$(GREEN)✓ Migration rolled back!$(NC)\n"

migrate-current: ## Show current database migration revision
	@printf "$(CYAN)Current migration revision:$(NC)\n"
	$(UV) run alembic current

migrate-history: ## Show migration history
	@printf "$(CYAN)Migration history:$(NC)\n"
	$(UV) run alembic history

migrate-check: ## Check if database is up to date with migrations
	@printf "$(CYAN)Checking migration status...$(NC)\n"
	$(UV) run alembic check
	@printf "$(GREEN)✓ Database is up to date!$(NC)\n"

migrate-downgrade-base: ## Drop all database tables using migrations (downgrade to base)
	@printf "$(YELLOW)WARNING: This will drop all database tables using migrations!$(NC)\n"
	@read -p "Are you sure you want to continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		printf "$(CYAN)Dropping all database tables via migrations...$(NC)\n"; \
		$(UV) run alembic downgrade base; \
		printf "$(GREEN)✓ All tables dropped via migrations!$(NC)\n"; \
	else \
		printf "$(YELLOW)Cancelled.$(NC)\n"; \
		exit 1; \
	fi

db-reset: ## Fully reset database: drop database, create new empty database, run migrations, and seed all data
	@printf "$(YELLOW)WARNING: This will drop the entire database and recreate it from scratch!$(NC)\n"
	@read -p "Are you sure you want to continue? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		printf "$(CYAN)Purging Redis databases 0 and 1 (embedding caches)...$(NC)\n"; \
		if command -v redis-cli >/dev/null 2>&1; then \
			redis-cli -n 0 FLUSHDB >/dev/null 2>&1 && printf "$(GREEN)✓ Redis DB 0 flushed$(NC)\n" || printf "$(YELLOW)⚠ Could not flush Redis DB 0 (may not be running)$(NC)\n"; \
			redis-cli -n 1 FLUSHDB >/dev/null 2>&1 && printf "$(GREEN)✓ Redis DB 1 flushed$(NC)\n" || printf "$(YELLOW)⚠ Could not flush Redis DB 1 (may not be running)$(NC)\n"; \
		elif command -v valkey-cli >/dev/null 2>&1; then \
			valkey-cli -n 0 FLUSHDB >/dev/null 2>&1 && printf "$(GREEN)✓ Redis DB 0 flushed$(NC)\n" || printf "$(YELLOW)⚠ Could not flush Redis DB 0 (may not be running)$(NC)\n"; \
			valkey-cli -n 1 FLUSHDB >/dev/null 2>&1 && printf "$(GREEN)✓ Redis DB 1 flushed$(NC)\n" || printf "$(YELLOW)⚠ Could not flush Redis DB 1 (may not be running)$(NC)\n"; \
		else \
			printf "$(YELLOW)⚠ redis-cli or valkey-cli not found, skipping Redis flush$(NC)\n"; \
		fi; \
		printf "$(CYAN)Dropping database...$(NC)\n"; \
		if ! $(UV) run python scripts/drop_database.py; then \
			printf "$(RED)✗ Database drop failed!$(NC)\n"; \
			printf "$(YELLOW)Make sure the bot is not running and no other connections are active.$(NC)\n"; \
			exit 1; \
		fi; \
		printf "$(CYAN)Creating new empty database...$(NC)\n"; \
		if ! $(UV) run python scripts/create_database.py; then \
			printf "$(RED)✗ Database creation failed!$(NC)\n"; \
			exit 1; \
		fi; \
		printf "$(CYAN)Running migrations...$(NC)\n"; \
		set -e; \
		$(UV) run alembic upgrade heads || { \
			printf "$(RED)✗ Migration failed!$(NC)\n"; \
			printf "$(YELLOW)The database may be in an inconsistent state.$(NC)\n"; \
			printf "$(YELLOW)Run 'make db-reset' again to start fresh, or check the migration files.$(NC)\n"; \
			exit 1; \
		}; \
		printf "$(GREEN)✓ Migrations applied successfully$(NC)\n"; \
		printf "$(CYAN)Seeding database...$(NC)\n"; \
		$(UV) run python -m ds_common.seed_data; \
		$(UV) run python -m ds_common.world_seed_data; \
		printf "$(GREEN)✓ Database fully reset and seeded!$(NC)\n"; \
	else \
		printf "$(YELLOW)Cancelled.$(NC)\n"; \
		exit 1; \
	fi
