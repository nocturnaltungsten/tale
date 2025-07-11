# Makefile for tale development
# Alternative to using shell scripts directly

.PHONY: help setup test lint format clean benchmark install dev-install hooks hooks-test hooks-status

help: ## Show this help message
	@echo "Tale Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Set up development environment
	@./scripts/setup-dev.sh

test: ## Run all tests with coverage
	@./scripts/test.sh

lint: ## Run code quality checks
	@./scripts/lint.sh

format: ## Format code automatically
	@./scripts/format.sh

clean: ## Clean temporary files and caches
	@./scripts/clean.sh

benchmark: ## Run performance benchmarks
	@./scripts/benchmark.sh

install: ## Install package in development mode
	@uv pip install -e .

dev-install: ## Install package with development dependencies
	@uv pip install -e ".[dev]"

# Advanced targets
check: lint test ## Run both linting and tests

ci: clean format check ## Full CI pipeline (clean, format, check)

quick-test: ## Run tests without coverage for speed
	@python3 -m pytest tests/ -x --tb=short

type-check: ## Run only type checking
	@mypy src/

unit-tests: ## Run only unit tests
	@python3 -m pytest tests/unit/ -v

integration-tests: ## Run only integration tests
	@python3 -m pytest tests/integration/ -v

watch-tests: ## Run tests in watch mode (requires pytest-watch)
	@ptw tests/ src/

# Documentation targets
docs-serve: ## Serve documentation locally (when implemented)
	@echo "Documentation serving not yet implemented"

docs-build: ## Build documentation (when implemented)
	@echo "Documentation building not yet implemented"

# Development utility targets
hooks: ## Install and configure git hooks (pre-commit + pre-push)
	@./scripts/setup-hooks.sh install

hooks-test: ## Test git hooks without committing/pushing
	@./scripts/setup-hooks.sh test

hooks-status: ## Show git hooks status and dependencies
	@./scripts/setup-hooks.sh status

install-hooks: ## Install git pre-commit hooks (legacy - use 'hooks' instead)
	@echo "⚠️  Use 'make hooks' for comprehensive hook setup"
	@pre-commit install

update-deps: ## Update all dependencies
	@uv pip install -e ".[dev]" --upgrade

freeze-deps: ## Show current dependency versions
	@uv pip freeze

# Docker targets (for future use)
docker-build: ## Build Docker image (when implemented)
	@echo "Docker build not yet implemented"

docker-test: ## Run tests in Docker (when implemented)
	@echo "Docker testing not yet implemented"
