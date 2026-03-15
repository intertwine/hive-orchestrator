.PHONY: help install install-dev run dashboard ready ready-json deps deps-json hive hive-init hive-doctor sync-projections migrate-v2 session clean test lint format sync verify-claude

# Default target
help:
	@echo "╔════════════════════════════════════════════════════════╗"
	@echo "║            AGENT HIVE - MAKEFILE COMMANDS              ║"
	@echo "╚════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make install        Install Python dependencies with uv"
	@echo "  make install-dev    Install dev dependencies (black, pylint, pytest)"
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
	@echo "  make sync-projections  Rebuild cache and refresh generated sections"
	@echo "  make migrate-v2     Import v1 projects into the v2 substrate"
	@echo "  make session        Start a Hive v2 session (requires PROJECT=...)"
	@echo "  make verify-claude  Verify Claude Code GitHub App setup"
	@echo ""
	@echo "Development Commands:"
	@echo "  make lint           Run code linting (pylint)"
	@echo "  make format         Format code with black"
	@echo "  make test           Run tests (if available)"
	@echo "  make clean          Clean up generated files"
	@echo ""
	@echo "Examples:"
	@echo "  make dashboard"
	@echo "  make sync-projections"
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
	uv sync --dev
	@echo "✅ Dev dependencies installed!"

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
	@echo "1. Edit .env if you want custom paths or optional services"
	@echo "2. Run: make dashboard"
	@echo "3. Or run: make sync-projections"
	@echo ""
