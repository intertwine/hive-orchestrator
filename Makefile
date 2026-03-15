SHELL := /bin/bash

.PHONY: help install install-dev install-tool run dashboard ready ready-json deps deps-json hive hive-init hive-doctor doctor sync-projections migrate-v2 session clean test lint format sync verify-claude check build bump-version publish-test publish brew-formula brew-check release-homebrew brew-install

BUMP ?= patch
HOMEBREW_TAP_DIR ?= ../homebrew-tap
HOMEBREW_INSTALL_TARGET ?= intertwine/tap/agent-hive

# Default target
help:
	@echo "╔════════════════════════════════════════════════════════╗"
	@echo "║            AGENT HIVE - MAKEFILE COMMANDS              ║"
	@echo "╚════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make install        Install Python dependencies with uv"
	@echo "  make install-dev    Install dev dependencies (black, pylint, pytest)"
	@echo "  make install-tool   Install the hive CLI as a uv-managed tool from this checkout"
	@echo "  make sync           Sync dependencies from pyproject.toml"
	@echo "  make setup-env      Create .env file template"
	@echo ""
	@echo "Runtime Commands:"
	@echo "  make dashboard      Launch Streamlit dashboard (UI)"
	@echo "  make ready          Find ready canonical tasks"
	@echo "  make ready-json     Find ready work as JSON"
	@echo "  make deps           Show dependency graph"
	@echo "  make deps-json      Show dependency graph as JSON"
	@echo "  make hive           Show Hive 2.0 doctor output"
	@echo "  make hive-init      Initialize the Hive 2.0 layout"
	@echo "  make doctor         Show Hive 2.0 doctor output"
	@echo "  make sync-projections  Rebuild cache and refresh generated sections"
	@echo "  make migrate-v2     Import v1 projects into the v2 substrate"
	@echo "  make session        Start a Hive v2 session (requires PROJECT=...)"
	@echo "  make verify-claude  Verify Claude Code GitHub App setup"
	@echo ""
	@echo "Development Commands:"
	@echo "  make lint           Run code linting (pylint)"
	@echo "  make format         Format code with black"
	@echo "  make test           Run tests (if available)"
	@echo "  make check          Run lint + tests"
	@echo "  make build          Build wheel and sdist"
	@echo "  make bump-version   Bump the package version (BUMP=patch|minor|major)"
	@echo "  make publish-test   Publish dist/* to TestPyPI with twine"
	@echo "  make publish        Publish dist/* to PyPI with twine"
	@echo "  make brew-formula   Generate the Homebrew formula"
	@echo "  make brew-check     Audit the generated Homebrew formula"
	@echo "  make release-homebrew  Copy the formula into a local Homebrew tap checkout"
	@echo "  make brew-install   Install from the configured Homebrew tap"
	@echo "  make clean          Clean up generated files"
	@echo ""
	@echo "Examples:"
	@echo "  make install"
	@echo "  make hive-init"
	@echo "  make session PROJECT=projects/demo"
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
	uv tool install --force --from . agent-hive
	@echo "✅ hive CLI installed. Verify with: hive doctor --json"

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

# Launch Streamlit dashboard
dashboard:
	@echo "🚀 Launching Agent Hive Dashboard..."
	@echo "   Open http://localhost:8501 in your browser"
	@echo ""
	uv run streamlit run src/dashboard.py

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
	@uv run hive doctor --json

hive-init:
	@uv run hive init --json

hive-doctor:
	@uv run hive doctor --json

doctor:
	@uv run hive doctor --json

sync-projections:
	@uv run hive cache rebuild --json
	@uv run hive sync projections --json

migrate-v2:
	@uv run hive migrate v1-to-v2 --json

# Start a Hive v2 session
session:
	@if [ -z "$(PROJECT)" ]; then \
		echo "❌ Error: PROJECT variable not set"; \
		echo "Usage: make session PROJECT=projects/demo"; \
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

publish: build
	@echo "🚀 Publishing to PyPI..."
	@echo "Requires TWINE_USERNAME=__token__ and TWINE_PASSWORD=<pypi-token>"
	@echo -n "Continue? [y/N] " && read ans && ( [ "$${ans}" = "y" ] || [ "$${ans}" = "Y" ] )
	uv run --extra dev twine upload dist/*

brew-formula:
	@echo "🍺 Generating Homebrew formula..."
	uv run --with pip python scripts/generate_homebrew_formula.py --output packaging/homebrew/agent-hive.rb

brew-check: brew-formula
	@if ! command -v brew >/dev/null 2>&1; then \
		echo "❌ Error: brew not found"; \
		echo "Install Homebrew first: https://brew.sh"; \
		exit 1; \
	fi
	brew style packaging/homebrew/agent-hive.rb
	@if brew info --formula $(HOMEBREW_INSTALL_TARGET) >/dev/null 2>&1; then \
		brew audit --strict --formula $(HOMEBREW_INSTALL_TARGET); \
	else \
		echo "ℹ️ Skipped brew audit by formula name; add the tap first with: brew tap intertwine/tap"; \
	fi

release-homebrew: brew-formula
	@if [ ! -d "$(HOMEBREW_TAP_DIR)/.git" ]; then \
		echo "❌ Error: $(HOMEBREW_TAP_DIR) is not a git repository"; \
		echo "Clone your tap repo first, for example:"; \
		echo "  git clone git@github.com:intertwine/homebrew-tap.git $(HOMEBREW_TAP_DIR)"; \
		exit 1; \
	fi
	@mkdir -p "$(HOMEBREW_TAP_DIR)/Formula"
	cp packaging/homebrew/agent-hive.rb "$(HOMEBREW_TAP_DIR)/Formula/agent-hive.rb"
	@echo "✅ Synced formula into $(HOMEBREW_TAP_DIR)/Formula/agent-hive.rb"

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
	find . -type d -name "__pycache__" -prune -exec rm -r {} \; 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	find . -type f -name "SESSION_CONTEXT.md" -delete 2>/dev/null || true
	@echo "✅ Cleanup complete!"

# Quick start (install + setup env + show help)
quickstart: install setup-env
	@echo ""
	@echo "╔════════════════════════════════════════════════════════╗"
	@echo "║              AGENT HIVE QUICK START                    ║"
	@echo "╚════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "✅ Dependencies installed"
	@echo "✅ .env template created"
	@echo ""
	@echo "Next steps:"
	@echo "1. Run: make hive-init"
	@echo "2. Run: uv run hive project create demo --title \"Demo project\" --json"
	@echo "3. Run: make dashboard"
	@echo ""
