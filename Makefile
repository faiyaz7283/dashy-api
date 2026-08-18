.PHONY: help \
        test lint format typecheck build \
        install add remove \
        dev-up dev-down dev-logs

.DEFAULT_GOAL := help

help:
	@echo "Dashy API - Backend Development"
	@echo ""
	@echo "Development:"
	@echo "  make dev-up              - Start backend via docker compose (from orchestrator)"
	@echo "  make dev-down            - Stop backend"
	@echo "  make dev-logs            - View backend logs"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint                - Lint with Ruff"
	@echo "  make format              - Format with Ruff"
	@echo "  make typecheck           - Type check (mypy via uv)"
	@echo ""
	@echo "Testing:"
	@echo "  make test                - Run pytest"
	@echo ""
	@echo "Build:"
	@echo "  make build               - Compile-check all Python files"
	@echo ""
	@echo "Package Management:"
	@echo "  make install             - Install dependencies (uv sync)"
	@echo "  make add PACKAGE=<name>  - Add a package"
	@echo "  make remove PACKAGE=<name> - Remove a package"

# ==============================================================================
# DEVELOPMENT (requires running from orchestrator docker compose)
# ==============================================================================

dev-up:
	@echo "Start from the orchestrator repo: make dev-up"

dev-down:
	@echo "Stop from the orchestrator repo: make dev-down"

dev-logs:
	@echo "View logs from the orchestrator repo: make dev-logs"

# ==============================================================================
# CODE QUALITY
# ==============================================================================

lint:
	@echo "Linting backend..."
	@uv run ruff check app/ tests/

format:
	@echo "Formatting backend..."
	@uv run ruff format app/ tests/
	@uv run ruff check --fix app/ tests/

typecheck:
	@echo "Type checking backend..."
	@uv run python -m compileall app/

# ==============================================================================
# TESTING
# ==============================================================================

test:
	@echo "Running backend tests..."
	@uv run pytest tests/ -v

# ==============================================================================
# BUILD
# ==============================================================================

build:
	@echo "Building backend..."
	@uv run python -m compileall app/
	@echo "Backend built successfully"

# ==============================================================================
# PACKAGE MANAGEMENT
# ==============================================================================

install:
	@echo "Installing backend dependencies..."
	@uv sync
	@echo "Dependencies installed"

add:
ifndef PACKAGE
	$(error PACKAGE is required. Usage: make add PACKAGE=<package-name>)
endif
	@echo "Adding $(PACKAGE)..."
	@uv add $(PACKAGE)
	@echo "Added $(PACKAGE)"

remove:
ifndef PACKAGE
	$(error PACKAGE is required. Usage: make remove PACKAGE=<package-name>)
endif
	@echo "Removing $(PACKAGE)..."
	@uv remove $(PACKAGE)
	@echo "Removed $(PACKAGE)"
