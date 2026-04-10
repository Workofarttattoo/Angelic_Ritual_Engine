.PHONY: help up down build test lint clean logs shell fmt check db-init

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Docker ─────────────────────────────────────────────────────────────

up: ## Start all services in detached mode
	docker compose up -d --build

down: ## Stop and remove containers
	docker compose down

build: ## Build Docker images without starting
	docker compose build

logs: ## Tail logs from all services
	docker compose logs -f --tail=100

shell: ## Open a shell in the API container
	docker compose exec api bash

# ── Development ────────────────────────────────────────────────────────

install: ## Install project in editable mode with dev extras
	pip install -e ".[dev]"

db-init: ## Initialise / migrate the database
	python -m agentic_ritual_engine.main kb-init

run: ## Run the API server locally
	python -m agentic_ritual_engine.main run

run-ui: ## Run the Streamlit dashboard locally
	python -m agentic_ritual_engine.main run-pulse-map

test: ## Run the test suite
	python -m pytest tests/ -v --tb=short

lint: ## Run linter (ruff)
	ruff check agentic_ritual_engine/ tests/

fmt: ## Auto-format code (ruff)
	ruff format agentic_ritual_engine/ tests/
	ruff check --fix agentic_ritual_engine/ tests/

check: lint test ## Run lint + tests

clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ htmlcov/ .coverage
