# CLAUDE.md - AI Assistant Development Guide

> This document provides comprehensive context for AI assistants (Claude, GPT-4, Gemini, etc.) working on the Agent Hive project.

## Project Overview

**Agent Hive** now runs on the Hive 2.0 model. The old v1 Cortex runtime is gone; this repository is centered on:

1. **`hive` CLI first**: `uv run hive ... --json` is the stable machine interface.
2. **`.hive/` as canonical state**: task files, runs, memory, events, and derived cache live there.
3. **Markdown projections for humans**: `GLOBAL.md`, `AGENCY.md`, `PROGRAM.md`, and `CLAUDE.md` stay readable and are regenerated where appropriate.
4. **`PROGRAM.md`-gated autonomy**: autonomous runs are limited by project-local policy, evaluators, and path/command budgets.
5. **Thin compatibility only**: `src/cortex.py` and the MCP server exist only as v2 adapters, not as primary orchestration surfaces.

## Technology Stack

### Package Management: uv

This project uses **[uv](https://github.com/astral-sh/uv)** for dependency management, virtual environments, and reproducible lockfile-based installs.

### Core Dependencies

Defined in `pyproject.toml`:

- **requests**: HTTP utilities for optional integrations
- **streamlit**: dashboard UI
- **python-frontmatter** and **pyyaml**: markdown/frontmatter parsing
- **python-dotenv**: optional environment loading
- **weave**: optional tracing hooks

### Development Tools

- **black**
- **pylint**
- **pytest**

## Project Structure

```text
agent-hive/
├── .github/workflows/
│   ├── projection-sync.yml    # Regenerates projections and cache
│   └── agent-assignment.yml   # Ready-work snapshots / dispatcher support
├── projects/*/
│   ├── AGENCY.md              # Narrative project document
│   └── PROGRAM.md             # Autonomous work contract
├── .hive/
│   ├── tasks/                 # Canonical task files
│   ├── runs/                  # Run artifacts and evaluator outputs
│   ├── memory/                # Project-local memory docs
│   ├── events/                # Append-only audit logs
│   └── cache/                 # Derived SQLite cache
├── src/
│   ├── hive/                  # Hive 2.0 core implementation
│   ├── cortex.py              # Thin v2 compatibility facade
│   ├── agent_dispatcher.py    # Optional GitHub issue dispatcher
│   ├── context_assembler.py   # Startup / handoff context helpers
│   ├── dashboard.py           # Streamlit UI
│   └── hive_mcp/              # Thin search/execute MCP adapter
├── GLOBAL.md                  # Root narrative / generated project rollup
├── CLAUDE.md                  # This file
└── README.md                  # User-facing guide
```

## Development Setup

### Quick Start

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone <repo-url>
cd agent-hive
make install
make install-dev
uv run hive doctor --json
```

### Common Commands

```bash
make dashboard
make sync-projections
make ready
make deps
make test
make lint

uv run hive task ready --json
uv run hive sync projections --json
uv run hive context startup --project <project-id> --json
uv run hive migrate v1-to-v2 --dry-run --json
```

## Core Concepts

### 1. `AGENCY.md` is narrative, not canonical task state

Each project keeps a readable `AGENCY.md` with goals, notes, and generated task/run rollups. Legacy checkbox lists may still appear as imported context, but canonical task state lives in `.hive/tasks/*.md`.

### 2. `PROGRAM.md` is the autonomous contract

Each project can define allowed paths, commands, evaluators, budgets, and promotion/escalation rules. Autonomous runs should read `PROGRAM.md` before making changes.

### 3. `.hive/tasks/*.md` is the machine source of truth

Each canonical task file contains:

- stable immutable task ID
- project ID and title
- status / priority / claim info
- typed edges such as `blocks`, `duplicates`, and `supersedes`
- summary, notes, history, and preserved import metadata

### 4. `src/cortex.py` is only a compatibility wrapper

Use it only for compatibility entrypoints like ready/deps/sync. Do not extend it as a new orchestration engine.

### 5. The dashboard and dispatcher are adapters on top of v2

`src/dashboard.py` reads the canonical substrate and projections. `src/agent_dispatcher.py` optionally turns ready tasks into GitHub issues, but the scheduler and task store live in Hive 2.0, not in legacy markdown mutation logic.

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

3. **Sync projections**
   ```bash
   make sync-projections
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

- **tests/test_agent_dispatcher.py**: Tests for the Agent Dispatcher
  - Work selection and prioritization
  - Project claiming and ownership
  - GitHub issue creation
  - Environment validation
  - Full dispatch workflow

- **tests/test_context_assembler.py**: Tests for context building
  - File tree generation
  - Relevant file content extraction
  - Issue title and body building
  - Label generation

- **tests/test_tracing.py**: Tests for Weave observability integration
  - Tracing enable/disable logic
  - LLMCallMetadata class
  - Token usage extraction
  - Traced LLM calls (success, error, timeout)
  - Cortex integration with tracing

- **tests/conftest.py**: Shared test fixtures and utilities
  - Temporary test directory structures
  - Mock environment variables
  - Sample API responses

### Running Tests

**IMPORTANT:** Test dependencies (pytest, etc.) are in the `dev` optional dependencies.
You must install them first before running tests:

```bash
# Install dev dependencies (REQUIRED before running tests)
make install-dev
# Or directly: uv sync --extra dev

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

**Projection Sync** (`.github/workflows/projection-sync.yml`)

- rebuilds the v2 cache
- refreshes generated projection markers in `GLOBAL.md`, `AGENCY.md`, and `AGENTS.md`
- keeps the readable docs aligned with canonical `.hive/` state

**Agent Assignment** (`.github/workflows/agent-assignment.yml`)

- captures ready-work snapshots from the v2 scheduler
- can support manual dispatcher-driven GitHub issue creation
- does not depend on the removed v1 Cortex runtime

**Claude / Codex review flows**

- use the repository’s review workflows and PR comment triggers
- should treat `hive` CLI output and canonical task files as the source of truth

**Required secrets**

- `ANTHROPIC_API_KEY` for Claude GitHub actions or review bots
- `GITHUB_TOKEN` for issue / PR automation

### Local Development

The DevContainer remains a good default local environment. The important runtime assumption is simply: this repo expects Python 3.11+ and `uv`.

## API Integration

### Hive 2.0 core is deterministic

The core `hive` CLI does not require OpenRouter or any other LLM API to function. Migration, scheduling, projections, memory, runs, search, and execute all work locally against repository state.

### Optional tracing

`src/tracing.py` still provides optional Weave instrumentation for custom integrations. If you use it, the environment knobs are:

```bash
WANDB_API_KEY=...
WEAVE_PROJECT=agent-hive
WEAVE_DISABLED=false
```

If tracing is unavailable or disabled, the rest of Hive continues normally.

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
