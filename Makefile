.DEFAULT_GOAL := help
PY_VERSIONS := 3.12 3.13

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-14s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install Python toolchain + all deps from scratch (uv)
	uv python install $(PY_VERSIONS)
	uv sync --frozen --group dev || uv sync --group dev
	uv run pre-commit install
	@test -f .secrets.baseline || uv run detect-secrets scan > .secrets.baseline

.PHONY: lint
lint: ## ruff (lint+format), mypy strict, bandit
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src tests
	uv run bandit -q -r src -c pyproject.toml

.PHONY: format
format: ## Auto-fix lint + format
	uv run ruff check --fix .
	uv run ruff format .

.PHONY: test
test: ## Run the test suite with coverage
	uv run pytest

.PHONY: audit
audit: ## pip-audit for dependency CVEs
	uv run pip-audit

.PHONY: security
security: ## bandit + pip-audit + detect-secrets
	uv run bandit -q -r src -c pyproject.toml
	uv run pip-audit
	uv run detect-secrets scan --baseline .secrets.baseline

.PHONY: run
run: ## Run the FastAPI server (UI + API)
	uv run uvicorn --factory globeye.api.main:create_app --host 127.0.0.1 --port 8000 --reload

.PHONY: cli
cli: ## Run the GLOBEYE CLI (pass ARGS="...")
	uv run globeye $(ARGS)

.PHONY: build
build: ## Build the wheel/sdist
	uv build

.PHONY: docker
docker: ## Build the Docker image
	docker build -t globeye:local .

.PHONY: clean
clean: ## Remove caches and build artefacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage dist build
	find . -type d -name __pycache__ -exec rm -rf {} +
