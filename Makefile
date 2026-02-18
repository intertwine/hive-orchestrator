.PHONY: help install install-dev run dashboard cortex ready ready-json deps deps-json session clean test lint format sync verify-claude yolo yolo-hive yolo-daemon yolo-status yolo-stop yolo-docker

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
	@echo "  make cortex         Run Cortex orchestration engine"
	@echo "  make ready          Find ready work (fast, no LLM)"
	@echo "  make ready-json     Find ready work as JSON"
	@echo "  make deps           Show dependency graph"
	@echo "  make deps-json      Show dependency graph as JSON"
	@echo "  make session        Start a Deep Work session (requires PROJECT=...)"
	@echo "  make verify-claude  Verify Claude Code GitHub App setup"
	@echo ""
	@echo "YOLO Loop Commands (Autonomous Agent Loops):"
	@echo "  make yolo PROMPT='...'   Run a single YOLO loop with a prompt"
	@echo "  make yolo-hive           Run YOLO loops on all ready projects (Loom mode)"
	@echo "  make yolo-daemon         Start YOLO daemon for continuous operation"
	@echo "  make yolo-status         Check YOLO daemon status"
	@echo "  make yolo-stop           Stop YOLO daemon"
	@echo "  make yolo-docker         Run YOLO loop in Docker sandbox"
	@echo ""
	@echo "Development Commands:
	@echo "  make lint           Run code linting (pylint)"
	@echo "  make format         Format code with black"
	@echo "  make test           Run tests (if available)"
	@echo "  make clean          Clean up generated files"
	@echo ""
	@echo "Examples:"
	@echo "  make dashboard"
	@echo "  make cortex"
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
		echo "OPENROUTER_API_KEY=your-api-key-here" > .env; \
		echo "OPENROUTER_MODEL=anthropic/claude-haiku-4.5" >> .env; \
		echo "HIVE_BASE_PATH=$(shell pwd)" >> .env; \
		echo "✅ .env file created. Please edit it and add your API key."; \
	else \
		echo "⚠️  .env file already exists. Not overwriting."; \
	fi

# Launch Streamlit dashboard
dashboard:
	@echo "🚀 Launching Agent Hive Dashboard..."
	@echo "   Open http://localhost:8501 in your browser"
	@echo ""
	uv run streamlit run src/dashboard.py

# Run Cortex orchestration
cortex:
	@echo "🧠 Running Cortex orchestration engine..."
	uv run python src/cortex.py

# Find ready work (fast, no LLM)
ready:
	@uv run python src/cortex.py --ready

# Find ready work as JSON (for programmatic use)
ready-json:
	@uv run python src/cortex.py --ready --json

# Show dependency graph
deps:
	@uv run python src/cortex.py --deps

# Show dependency graph as JSON (for programmatic use)
deps-json:
	@uv run python src/cortex.py --deps --json

# Start a Deep Work session
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
	@echo "1. Edit .env and add your OPENROUTER_API_KEY"
	@echo "2. Run: make dashboard"
	@echo "3. Or run: make cortex"
	@echo ""

# ═══════════════════════════════════════════════════════════════════
# YOLO LOOP COMMANDS - Autonomous Agent Loop Orchestration
# ═══════════════════════════════════════════════════════════════════

# Run a single YOLO loop with a prompt (Ralph Wiggum style)
yolo:
	@if [ -z "$(PROMPT)" ]; then \
		echo "❌ Error: PROMPT variable not set"; \
		echo "Usage: make yolo PROMPT='Fix all type errors in src/'"; \
		exit 1; \
	fi
	@echo "🔄 Starting YOLO loop..."
	uv run python -m src.yolo_loop --prompt "$(PROMPT)" --max-iterations $(or $(MAX_ITER),50)

# Run YOLO loops on all ready Hive projects (Loom mode)
yolo-hive:
	@echo "🕸️  Starting Loom Weaver (parallel YOLO loops)..."
	uv run python -m src.yolo_loop --hive --parallel $(or $(PARALLEL),3) --max-iterations $(or $(MAX_ITER),50)

# Start YOLO daemon for continuous unattended operation
yolo-daemon:
	@echo "🌙 Starting YOLO daemon (continuous operation)..."
	@echo "   Press Ctrl+C to stop"
	uv run python -m src.sandbox_runner daemon --poll-interval $(or $(POLL_INTERVAL),300)

# Check YOLO daemon status
yolo-status:
	@uv run python -m src.sandbox_runner status

# Stop YOLO daemon
yolo-stop:
	@uv run python -m src.sandbox_runner stop

# Run YOLO loop in Docker sandbox (isolated execution)
yolo-docker:
	@if [ -z "$(PROMPT)" ]; then \
		echo "❌ Error: PROMPT variable not set"; \
		echo "Usage: make yolo-docker PROMPT='Fix all bugs'"; \
		exit 1; \
	fi
	@echo "🐳 Starting YOLO loop in Docker sandbox..."
	uv run python -m src.yolo_loop --prompt "$(PROMPT)" --backend docker --max-iterations $(or $(MAX_ITER),50)

# Generate docker-compose.yml for cloud/VM deployment
yolo-compose:
	@echo "📝 Generating docker-compose.yml for YOLO deployment..."
	uv run python -m src.sandbox_runner compose --output docker-compose.yolo.yml
	@echo "✅ Generated docker-compose.yolo.yml"
	@echo ""
	@echo "To deploy:"
	@echo "  1. Copy docker-compose.yolo.yml to your server"
	@echo "  2. Set ANTHROPIC_API_KEY environment variable"
	@echo "  3. Run: docker-compose -f docker-compose.yolo.yml up -d"
