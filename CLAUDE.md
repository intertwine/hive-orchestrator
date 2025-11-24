# CLAUDE.md - AI Assistant Development Guide

> This document provides comprehensive context for AI assistants (Claude, GPT-4, Gemini, etc.) working on the Agent Hive project.

## Project Overview

**Agent Hive** is a vendor-agnostic orchestration operating system for autonomous AI agents. It enables coordination across different LLM providers using Markdown files with YAML frontmatter as shared memory.

### Core Philosophy

1. **Vendor Agnostic**: Works with any LLM provider (Claude, Grok, Gemini, OpenAI, etc.)
2. **Human-in-the-Loop**: Transparent orchestration, never fully autonomous
3. **Simple Primitives**: Markdown files serve as shared memory between humans and agents
4. **Git as Truth**: All state changes are version-controlled
5. **Free Infrastructure**: Designed to run on GitHub Actions free tier

## Technology Stack

### Package Management: uv

This project uses **[uv](https://github.com/astral-sh/uv)** - a fast, modern Python package installer and resolver written in Rust.

**Why uv?**
- 10-100x faster than pip
- Built-in virtual environment management
- Lockfile support for reproducible builds
- Modern pyproject.toml-based configuration
- No need for separate tools like pip-tools or poetry

### Core Dependencies

Defined in `pyproject.toml`:

- **openai** (>=1.12.0): OpenRouter API client (compatible with OpenAI SDK)
- **requests** (>=2.31.0): HTTP library for API calls
- **streamlit** (>=1.31.0): Web-based dashboard UI
- **python-frontmatter** (>=1.0.0): Parse Markdown files with YAML frontmatter
- **pyyaml** (>=6.0.1): YAML parsing and serialization
- **python-dotenv** (>=1.0.0): Environment variable management

### Development Tools

- **black**: Code formatting
- **pylint**: Linting and code quality
- **pytest**: Testing framework

## Project Structure

```
agent-hive/
├── .devcontainer/
│   └── devcontainer.json       # VS Code DevContainer + MCP support
├── .github/
│   └── workflows/
│       └── cortex.yml          # Automated 4-hour heartbeat
├── config/
│   └── app-manifest.json       # GitHub App configuration (future)
├── projects/
│   └── demo/
│       └── AGENCY.md           # Example project
├── scripts/
│   └── start_session.sh        # Deep Work session bootstrap
├── src/
│   ├── cortex.py               # Orchestration engine
│   └── dashboard.py            # Streamlit dashboard
├── GLOBAL.md                   # Root system state
├── pyproject.toml              # Project configuration
├── Makefile                    # Development commands
├── CLAUDE.md                   # This file
└── README.md                   # User documentation
```

## Development Setup

### Quick Start

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and enter the repository
git clone <repo-url>
cd agent-hive

# Install dependencies
make install

# Install dev dependencies (optional)
make install-dev

# Set up environment
make setup-env
# Edit .env and add your OPENROUTER_API_KEY
```

### Common Commands

```bash
# Install/sync dependencies
make install          # Install all dependencies
make sync             # Sync dependencies from pyproject.toml
make install-dev      # Install dev dependencies

# Run the application
make dashboard        # Launch Streamlit UI (port 8501)
make cortex           # Run orchestration engine

# Development
make format           # Format code with black
make lint             # Run pylint
make test             # Run tests
make clean            # Clean __pycache__ and temp files

# Deep Work sessions
make session PROJECT=projects/demo
```

### Using uv Directly

```bash
# Run commands in the uv environment
uv run python src/cortex.py
uv run streamlit run src/dashboard.py
uv run pytest tests/

# Add new dependencies
uv add requests
uv add --dev pytest

# Remove dependencies
uv remove requests
```

## Core Concepts

### 1. AGENCY.md - The Shared Memory Primitive

Every project has an `AGENCY.md` file with YAML frontmatter:

```markdown
---
project_id: example-project
status: active              # active, pending, blocked, completed
owner: null                 # null or agent name (e.g., "claude-3.5-sonnet")
last_updated: 2025-01-15T10:30:00Z
blocked: false
blocking_reason: null
priority: high              # low, medium, high, critical
tags: [feature, backend]
---

# Project Title

## Objective
What this project aims to achieve.

## Tasks
- [ ] Task 1
- [ ] Task 2
- [x] Completed task

## Agent Notes
- **2025-01-15 10:30 - Claude**: Started work on Task 1
```

**Key Fields:**

- `project_id`: Unique identifier
- `status`: Current state of the project
- `owner`: Which agent is currently working (set to your name when active)
- `blocked`: Set to `true` if you need human intervention
- `blocking_reason`: Explanation of what's blocking you
- `priority`: Task prioritization
- `tags`: Organizational labels

### 2. GLOBAL.md - System State

Root-level file tracking overall system state:

```yaml
---
last_cortex_run: 2025-01-15T14:00:00Z
total_projects: 5
active_projects: 2
blocked_projects: 1
---

# Agent Hive Global State
```

### 3. Cortex - The Orchestration Engine

`src/cortex.py` is the autonomous orchestrator that:

1. Reads all `AGENCY.md` files
2. Calls an LLM to analyze current state
3. Updates metadata (status, blocked flags, etc.)
4. Commits changes back to Git
5. **Never executes code directly** - only updates Markdown

**Safety guarantees:**
- Only modifies `AGENCY.md` and `GLOBAL.md` files
- All changes are Git-tracked
- Runs in read-analyze-update cycle
- Human review via Pull Requests

### 4. Dashboard - Human Oversight

`src/dashboard.py` provides a Streamlit web UI for:

- Viewing all projects and their status
- Manually triggering Cortex runs
- Generating Deep Work session contexts
- Monitoring system health

## Development Workflows

### Adding a New Feature

1. **Create an AGENCY.md file**
   ```bash
   mkdir -p projects/new-feature
   cp projects/demo/AGENCY.md projects/new-feature/AGENCY.md
   # Edit the file with your project details
   ```

2. **Update metadata**
   - Set `project_id`, `status`, `priority`, `tags`
   - Define tasks in the markdown content

3. **Run Cortex**
   ```bash
   make cortex
   ```

4. **Monitor in Dashboard**
   ```bash
   make dashboard
   # Open http://localhost:8501
   ```

### Deep Work Session Pattern

1. **Generate context** via Dashboard or script:
   ```bash
   make session PROJECT=projects/your-project
   ```

2. **Copy the generated context** to your AI agent

3. **Work on tasks** - the context includes:
   - Full AGENCY.md content
   - File tree
   - Handoff protocol
   - Your responsibilities

4. **Update AGENCY.md** before finishing:
   - Set `owner` to your model name while working
   - Update `last_updated` timestamp
   - Mark completed tasks with `[x]`
   - Add notes to "Agent Notes" section
   - Set `blocked: true` if you need help
   - Set `owner: null` when done

### Multi-Agent Collaboration

Agents coordinate through AGENCY.md updates:

1. **Agent A (Claude)**: Claims work by setting `owner: "claude-3.5-sonnet"`
2. **Agent A**: Completes research, updates AGENCY.md with findings
3. **Agent A**: Marks task complete, sets `owner: null`
4. **Cortex**: Detects completion, updates global state
5. **Agent B (Grok)**: Sees available task, claims ownership
6. **Agent B**: Continues work based on Agent A's notes

## Code Style & Standards

### Python Code

- **Format**: Use `black` with 100-char line length
- **Linting**: `pylint` for code quality
- **Type hints**: Encouraged but not required
- **Docstrings**: Google-style docstrings for functions

### Markdown Files

- Use YAML frontmatter for metadata
- Keep content human-readable
- Use task lists (`- [ ]`) for tracking
- Add timestamped agent notes

### Git Commits

- Descriptive commit messages
- Emoji prefixes optional but encouraged:
  - 🧠 Cortex updates
  - 🚀 Features
  - 🐛 Bugfixes
  - 📝 Documentation
  - 🔧 Configuration

## Testing

**CRITICAL: All code changes must include tests and all tests must pass before committing.**

### Test Coverage

The project has comprehensive test coverage for all major functionality:

- **tests/test_cortex.py**: Tests for the Cortex orchestration engine
  - Initialization and configuration
  - Environment validation
  - Reading and parsing GLOBAL.md and AGENCY.md files
  - Project discovery
  - LLM API calls and response handling
  - State updates and file modifications
  - Full end-to-end Cortex runs

- **tests/test_dashboard.py**: Tests for the Dashboard UI
  - Loading and parsing project files
  - Project discovery and sorting
  - File tree generation
  - Deep Work context generation
  - Integration workflows

- **tests/conftest.py**: Shared test fixtures and utilities
  - Temporary test directory structures
  - Mock environment variables
  - Sample API responses

### Running Tests

```bash
# Run all tests (REQUIRED before committing)
make test

# Run with verbose output
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_cortex.py -v

# Run specific test class or function
uv run pytest tests/test_cortex.py::TestCortexInitialization -v
```

### Writing Tests

**All new functionality must have corresponding tests.**

Place tests in `tests/` directory following pytest conventions:

```python
# tests/test_cortex.py
import pytest
from src.cortex import Cortex

class TestCortexInitialization:
    """Test Cortex initialization."""

    def test_cortex_initialization(self, temp_hive_dir):
        """Test that Cortex initializes correctly."""
        cortex = Cortex(temp_hive_dir)
        assert cortex.base_path == temp_hive_dir
```

**Test Requirements:**
- Use descriptive test names that explain what is being tested
- Organize tests into classes by functionality
- Use fixtures from `conftest.py` for common setup
- Test both success and failure cases
- Mock external dependencies (API calls, file I/O when appropriate)
- Ensure tests are isolated and don't depend on each other

### Running Linter

```bash
# Run pylint on all code (REQUIRED before committing)
make lint

# Run on specific directory
uv run pylint src/ --max-line-length=100
uv run pylint tests/ --max-line-length=100

# Target score: >9.0/10
```

## Deployment

### GitHub Actions

The `.github/workflows/cortex.yml` workflow:

- Runs every 4 hours
- Installs dependencies with `uv`
- Executes Cortex
- Commits changes if state updated
- Only modifies AGENCY.md and GLOBAL.md files

**Required Secrets:**
- `OPENROUTER_API_KEY`: Your OpenRouter API key

### Local Development

Use the DevContainer for consistent environment:

```bash
# In VS Code, use "Reopen in Container"
# Or with GitHub Codespaces
```

The DevContainer includes:
- Python 3.11
- Node.js LTS
- Git
- uv (installed automatically)
- MCP filesystem server (for Claude integration)

## API Integration

### OpenRouter

Agent Hive uses [OpenRouter](https://openrouter.ai/) to access multiple LLM providers through a unified API.

**Supported Models:**
- `anthropic/claude-3.5-sonnet` - Most capable
- `anthropic/claude-haiku-4.5` - Fast and cheap (default)
- `google/gemini-pro` - Google's model
- `x-ai/grok-beta` - X.AI's Grok

**Configuration:**

Set in `.env`:
```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENROUTER_MODEL=anthropic/claude-haiku-4.5
```

**Usage in Code:**

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

response = client.chat.completions.create(
    model=os.getenv("OPENROUTER_MODEL", "anthropic/claude-haiku-4.5"),
    messages=[{"role": "user", "content": "Hello"}]
)
```

## Troubleshooting

### uv not found

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (if needed)
echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Dependencies not syncing

```bash
# Force reinstall
uv sync --reinstall

# Clear cache
rm -rf .venv
uv sync
```

### Streamlit won't start

```bash
# Check if port is in use
lsof -i :8501

# Use different port
uv run streamlit run src/dashboard.py --server.port 8502
```

### Cortex not updating files

- Check that `OPENROUTER_API_KEY` is set
- Verify AGENCY.md files have valid YAML frontmatter
- Look for errors in console output
- Check Git status for uncommitted changes

## Contributing

### Code Changes

**IMPORTANT: All code must pass both linting and testing before committing.**

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Format code: `make format`
5. **Run linter and ensure it passes**: `make lint` (must achieve >9.0/10 rating)
6. **Run tests and ensure they all pass**: `make test` (all tests must pass)
7. Submit pull request

**Pre-commit Checklist:**
- [ ] Code is formatted with `black` (`make format`)
- [ ] All tests pass (`make test`)
- [ ] Pylint score is >9.0/10 (`make lint`)
- [ ] New functionality has corresponding tests
- [ ] Documentation is updated if needed

### Documentation

- Update README.md for user-facing changes
- Update this CLAUDE.md for development changes
- Keep examples current
- Document new configuration options

## Best Practices for AI Assistants

When working on this codebase:

1. **Always read AGENCY.md first** - Understand project context
2. **Claim ownership** - Set `owner` field when starting work
3. **Update frequently** - Keep AGENCY.md current with progress
4. **Be transparent** - Add detailed notes about your work
5. **Set blocked status** - Don't hide issues, flag them
6. **Follow handoff protocol** - Clean up state before finishing
7. **Test and lint before committing** - ALL code must pass `make test` and `make lint` (>9.0/10)
8. **Use uv commands** - Don't use pip directly
9. **Write tests for new code** - Every new feature needs corresponding tests

### Example Work Session

```bash
# 1. Review the project
cat projects/my-project/AGENCY.md

# 2. Generate context if needed
make session PROJECT=projects/my-project

# 3. Make changes
# ... edit files ...

# 4. Test changes
make test
make lint

# 5. Update AGENCY.md
# - Mark tasks complete
# - Add agent notes
# - Update timestamps
# - Set owner: null

# 6. Commit
git add .
git commit -m "✨ Complete feature X"
git push
```

## Security Notes

- **Never commit API keys** - Use `.env` file (git-ignored)
- **Validate frontmatter** - Ensure YAML is well-formed
- **Limit file modifications** - Cortex only touches specific files
- **Review all commits** - GitHub Actions runs are auditable
- **Use read-only tokens** - Where possible for integrations

## Resources

- [uv Documentation](https://github.com/astral-sh/uv)
- [OpenRouter Docs](https://openrouter.ai/docs)
- [Streamlit Docs](https://docs.streamlit.io/)
- [Python Frontmatter](https://python-frontmatter.readthedocs.io/)

## Maintenance

### Dependency Updates

```bash
# Update all dependencies
uv sync --upgrade

# Update specific package
uv add requests --upgrade

# Check for outdated packages
uv pip list --outdated
```

### Cleaning Up

```bash
# Remove cache and temp files
make clean

# Remove virtual environment
rm -rf .venv
uv sync
```

---

**Happy Hacking!** 🐝

Remember: Agent Hive is about coordination, not control. Work transparently, update shared memory, and help the collective achieve more than any single agent could alone.
