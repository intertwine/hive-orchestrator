SHELL := /bin/bash

.PHONY: help install install-dev install-tool install-pipx run console dashboard ready ready-json deps deps-json hive hive-init hive-doctor doctor sync-projections migrate-v2 session clean test lint format sync verify-claude check build bump-version publish-test publish brew-formula brew-check release-homebrew brew-install release-check dev-quickstart quickstart

BUMP ?= patch
RELEASE_PYTHON_VERSION ?= 3.11
DIST_PACKAGE_NAME ?= mellona-hive
HOMEBREW_FORMULA_NAME ?= mellona-hive
HOMEBREW_TAP_DIR ?= ../homebrew-tap
HOMEBREW_INSTALL_TARGET ?= intertwine/tap/$(HOMEBREW_FORMULA_NAME)
HOMEBREW_PACKAGE_VERSION ?=

# Default target
help:
	@echo "╔════════════════════════════════════════════════════════╗"
	@echo "║         AGENT HIVE - MAINTAINER COMMANDS               ║"
	@echo "╚════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "This Makefile is for maintainers working from a source checkout."
	@echo 'Installed users should use the `hive` CLI directly.'
	@echo ""
	@echo "Maintainer Setup:"
	@echo "  make install        Install Python dependencies with uv"
	@echo "  make install-dev    Install dev dependencies (black, pylint, pytest)"
	@echo "  make install-tool   Install the hive CLI as a uv-managed tool from this checkout"
	@echo "  make install-pipx   Install the hive CLI from this checkout with pipx"
	@echo "  make sync           Sync dependencies from pyproject.toml"
	@echo "  make setup-env      Create .env file template"
	@echo ""
	@echo "Checkout Workflow:"
	@echo "  make console        Launch the observe-and-steer console"
	@echo "  make ready          Find ready canonical tasks"
	@echo "  make ready-json     Find ready work as JSON"
	@echo "  make deps           Show dependency graph"
	@echo "  make deps-json      Show dependency graph as JSON"
	@echo "  make hive           Show Hive 2.2 doctor output"
	@echo "  make hive-init      Initialize the Hive 2.2 layout"
	@echo "  make doctor         Show Hive 2.2 doctor output"
	@echo "  make sync-projections  Rebuild cache and refresh generated sections"
	@echo "  make migrate-v2     Import v1 projects into the v2 substrate"
	@echo "  make session        Save a Hive v2 startup bundle (PROJECT=<project-id> or path)"
	@echo "  make verify-claude  Verify Claude Code GitHub App setup"
	@echo ""
	@echo "Release And Packaging:"
	@echo "  make lint           Run code linting (pylint)"
	@echo "  make format         Format code with black"
	@echo "  make test           Run tests (if available)"
	@echo "  make check          Run lint + tests"
	@echo "  make build          Build wheel and sdist"
	@echo "  make release-check  Build, validate, and smoke-test release artifacts"
	@echo "  make bump-version   Bump the package version (BUMP=patch|minor|major)"
	@echo "  make publish-test   Publish dist/* to TestPyPI with twine"
	@echo "  make publish        Publish dist/* to PyPI with twine"
	@echo "  make brew-formula   Generate the Homebrew formula"
	@echo "  make brew-check     Audit the generated Homebrew formula"
	@echo "  make release-homebrew  Copy the formula into a local Homebrew tap checkout"
	@echo "  make brew-install   Install from the configured Homebrew tap"
	@echo "  make dev-quickstart Checkout-only bootstrap for Hive maintainers"
	@echo "  make clean          Clean up generated files"
	@echo ""
	@echo "Examples:"
	@echo "  make install-dev"
	@echo "  make sync-projections"
	@echo "  make session PROJECT=demo"
	@echo "  make release-check"
	@echo ""

# Install dependencies
install:
	@echo "📦 Installing dependencies with uv..."
	@command -v uv >/dev/null 2>&1 || { echo "❌ Error: uv not found. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
	uv sync
	@echo "✅ Installation complete!"

# Install dev dependencies
install-dev:
	@echo "📦 Installing dev dependencies with uv..."
	@command -v uv >/dev/null 2>&1 || { echo "❌ Error: uv not found. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
	uv sync --extra dev
	@echo "✅ Dev dependencies installed!"

install-tool:
	@echo "🛠️ Installing hive as a uv tool from this checkout..."
	@command -v uv >/dev/null 2>&1 || { echo "❌ Error: uv not found. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
	uv tool install --force --from . $(DIST_PACKAGE_NAME)
	@echo "✅ hive CLI installed. Verify with: hive doctor"

install-pipx:
	@echo "🛠️ Installing hive as a pipx app from this checkout..."
	@command -v uv >/dev/null 2>&1 || { echo "❌ Error: uv not found. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
	uvx --from pipx pipx install --force .
	@echo "✅ hive CLI installed via pipx. Verify with: hive doctor"

# Sync dependencies
sync:
	@echo "🔄 Syncing dependencies..."
	uv sync
	@echo "✅ Sync complete!"

# Create .env template
setup-env:
	@if [ ! -f .env ]; then \
		echo "Creating .env template..."; \
		echo "HIVE_BASE_PATH=$(shell pwd)" > .env; \
		echo "# Optional: real-time coordination" >> .env; \
		echo "# COORDINATOR_URL=http://localhost:8080" >> .env; \
		echo "# Optional: Weave tracing" >> .env; \
		echo "# WANDB_API_KEY=your-wandb-api-key" >> .env; \
		echo "# WEAVE_PROJECT=agent-hive" >> .env; \
		echo "✅ .env file created. Edit it only if you want custom paths or optional services."; \
	else \
		echo "⚠️  .env file already exists. Not overwriting."; \
	fi

# Launch observe console
console:
	@echo "🚀 Launching Agent Hive Observe Console..."
	@echo "   Open http://localhost:8787/console/ in your browser"
	@echo ""
	uv run hive console serve

# Backward-compatible alias for maintainers who still reach for the old target name.
dashboard: console

# Find ready work
ready:
	@uv run hive task ready

# Find ready work as JSON (for programmatic use)
ready-json:
	@uv run hive task ready --json

# Show dependency graph
deps:
	@uv run hive deps

# Show dependency graph as JSON (for programmatic use)
deps-json:
	@uv run hive deps --json

hive:
	@uv run hive doctor

hive-init:
	@uv run hive init

hive-doctor:
	@uv run hive doctor

doctor:
	@uv run hive doctor

sync-projections:
	@uv run hive cache rebuild
	@uv run hive sync projections

migrate-v2:
	@uv run hive migrate v1-to-v2

# Start a Hive v2 session
session:
	@if [ -z "$(PROJECT)" ]; then \
		echo "❌ Error: PROJECT variable not set"; \
		echo "Usage: make session PROJECT=demo"; \
		echo "   or: make session PROJECT=projects/demo"; \
		exit 1; \
	fi
	@./scripts/start_session.sh $(PROJECT)

# Verify Claude Code GitHub App installation
verify-claude:
	@echo "🔍 Verifying Claude Code GitHub App setup..."
	@uv run python scripts/verify_claude_app.py

# Run linting
lint:
	@echo "🔍 Running pylint..."
	uv run pylint src/ tests/ --max-line-length=100 --fail-under=9.0

# Format code
format:
	@echo "🎨 Formatting code with black..."
	uv run black src/ tests/

# Run tests
test:
	@echo "🧪 Running tests..."
	uv run pytest tests/ -v

check: lint test
	@echo "✅ Lint and tests passed!"

build: clean
	@echo "📦 Building wheel and sdist..."
	uv run --extra dev python -m build
	@ls -lh dist/

release-check: build
	@echo "🔎 Validating release artifacts..."
	uv run --extra dev twine check dist/*
	@DIST_PACKAGE_NAME="$(DIST_PACKAGE_NAME)" RELEASE_PYTHON_VERSION="$(RELEASE_PYTHON_VERSION)" ./scripts/smoke_release_install.sh
	@echo "✅ Release artifacts passed build, metadata, and install smoke checks."

bump-version:
	@if [ "$(BUMP)" != "patch" ] && [ "$(BUMP)" != "minor" ] && [ "$(BUMP)" != "major" ]; then \
		echo "❌ Error: BUMP must be patch, minor, or major"; \
		exit 1; \
	fi
	@uv run python scripts/bump_version.py pyproject.toml $(BUMP)

publish-test: build
	@echo "🚀 Publishing to TestPyPI..."
	@echo "Requires TWINE_USERNAME=__token__ and TWINE_PASSWORD=<testpypi-token>"
	uv run --extra dev twine upload --repository testpypi dist/*
	@echo "Smoke-test with:"
	@echo "  uv tool install --default-index https://test.pypi.org/simple --index https://pypi.org/simple $(DIST_PACKAGE_NAME)"

publish: build
	@echo "🚀 Publishing to PyPI..."
	@echo "Requires TWINE_USERNAME=__token__ and TWINE_PASSWORD=<pypi-token>"
	@if [ -n "$$CI" ]; then \
		echo "❌ Refusing to run interactive publish in CI. Use the tagged GitHub release workflow instead."; \
		exit 1; \
	fi
	@echo -n "Continue? [y/N] " && read ans && ( [ "$${ans}" = "y" ] || [ "$${ans}" = "Y" ] )
	uv run --extra dev twine upload dist/*

brew-formula:
	@echo "🍺 Generating Homebrew formula..."
	uv run --with pip python scripts/generate_homebrew_formula.py \
		--formula-name "$(HOMEBREW_FORMULA_NAME)" \
		--package-name "$(DIST_PACKAGE_NAME)" \
		$(if $(HOMEBREW_PACKAGE_VERSION),--package-version "$(HOMEBREW_PACKAGE_VERSION)",) \
		--output packaging/homebrew/$(HOMEBREW_FORMULA_NAME).rb

brew-check: brew-formula
	@HOMEBREW_FORMULA_NAME="$(HOMEBREW_FORMULA_NAME)" ./scripts/smoke_brew_formula.sh packaging/homebrew/$(HOMEBREW_FORMULA_NAME).rb

brew-release-check: brew-check
	@echo "✅ Homebrew formula passed style, audit, install, and test."

release-homebrew: brew-formula
	@if [ ! -d "$(HOMEBREW_TAP_DIR)/.git" ]; then \
		echo "❌ Error: $(HOMEBREW_TAP_DIR) is not a git repository"; \
		echo "Clone your tap repo first, for example:"; \
		echo "  git clone git@github.com:intertwine/homebrew-tap.git $(HOMEBREW_TAP_DIR)"; \
		exit 1; \
	fi
	@mkdir -p "$(HOMEBREW_TAP_DIR)/Formula"
	cp packaging/homebrew/$(HOMEBREW_FORMULA_NAME).rb "$(HOMEBREW_TAP_DIR)/Formula/$(HOMEBREW_FORMULA_NAME).rb"
	@echo "✅ Synced formula into $(HOMEBREW_TAP_DIR)/Formula/$(HOMEBREW_FORMULA_NAME).rb"

brew-install:
	@if ! command -v brew >/dev/null 2>&1; then \
		echo "❌ Error: brew not found"; \
		echo "Install Homebrew first: https://brew.sh"; \
		exit 1; \
	fi
	brew install $(HOMEBREW_INSTALL_TARGET)

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	rm -rf dist build ./*.egg-info
	find . -type d -name "__pycache__" -prune -exec rm -r {} \; 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	find . -type f -name "SESSION_CONTEXT.md" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete!"

# Checkout-only quick start (install + setup env + show help)
dev-quickstart: install setup-env
	@echo ""
	@echo "╔════════════════════════════════════════════════════════╗"
	@echo "║        AGENT HIVE CHECKOUT QUICK START                 ║"
	@echo "╚════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "✅ Dependencies installed"
	@echo "✅ .env template created"
	@echo ""
	@echo "This path is for maintainers working from the repository checkout."
	@echo "Installed users should start with: hive quickstart demo --title \"Demo project\""
	@echo ""
	@echo "Maintainer next steps:"
	@echo "1. Run: make sync-projections"
	@echo "2. Run: make session PROJECT=demo"
	@echo "3. Run: make check"
	@echo ""

quickstart:
	@echo "⚠️  make quickstart is a maintainer shortcut from a source checkout."
	@echo "Use the installed product path for everyday work: hive quickstart demo --title \"Demo project\""
	@echo "Maintainers can use: make dev-quickstart"
