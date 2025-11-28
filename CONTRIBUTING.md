# Contributing to Agent Hive

Thank you for your interest in contributing to Agent Hive! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Bugs

1. Check the [existing issues](https://github.com/intertwine/hive-orchestrator/issues) to avoid duplicates
2. Use the bug report template when creating a new issue
3. Include:
   - A clear description of the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Your environment (Python version, OS, etc.)

### Suggesting Features

1. Check existing issues and discussions for similar ideas
2. Use the feature request template
3. Explain the use case and why it would be valuable

### Pull Requests

1. Fork the repository
2. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/my-feature
   ```
3. Make your changes
4. Ensure all checks pass (see below)
5. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/hive-orchestrator.git
cd hive-orchestrator

# Install dependencies
make install

# Install dev dependencies
make install-dev

# Set up environment
make setup-env
# Edit .env with your OPENROUTER_API_KEY
```

## Code Quality Requirements

**All code must pass these checks before merging:**

### 1. Formatting

```bash
make format
```

Uses `black` with 100-character line length.

### 2. Linting

```bash
make lint
```

Must achieve a pylint score of **9.0/10 or higher**.

### 3. Tests

```bash
make test
```

All tests must pass. New features should include tests.

## Writing Tests

- Place tests in the `tests/` directory
- Follow pytest conventions
- Use fixtures from `conftest.py`
- Test both success and failure cases
- Mock external dependencies (API calls, etc.)

Example:

```python
# tests/test_cortex.py
import pytest
from src.cortex import Cortex

class TestCortexFeature:
    """Tests for a specific feature."""

    def test_feature_success(self, temp_hive_dir):
        """Test the happy path."""
        cortex = Cortex(temp_hive_dir)
        result = cortex.some_method()
        assert result is not None

    def test_feature_failure(self, temp_hive_dir):
        """Test error handling."""
        cortex = Cortex(temp_hive_dir)
        with pytest.raises(ValueError):
            cortex.some_method(invalid_input)
```

## Commit Guidelines

- Write clear, descriptive commit messages
- Keep commits focused on a single change
- Emoji prefixes are optional but welcomed:
  - `🚀` Features
  - `🐛` Bug fixes
  - `📝` Documentation
  - `🧪` Tests
  - `🔧` Configuration
  - `🧠` Cortex/orchestration changes

## Project Structure

```
agent-hive/
├── src/                    # Source code
│   ├── cortex.py          # Orchestration engine
│   ├── coordinator.py     # Real-time coordination server
│   ├── dashboard.py       # Streamlit UI
│   └── hive_mcp/          # MCP server
├── tests/                  # Test suite
├── projects/               # Project workspaces
├── examples/               # Example workflows
└── .claude/skills/         # Claude Code skills
```

## Documentation

- Update README.md for user-facing changes
- Update CLAUDE.md for development process changes
- Add docstrings to new functions (Google style)
- Keep examples current

## Questions?

- Open a [Discussion](https://github.com/intertwine/hive-orchestrator/discussions)
- Check existing documentation in README.md and CLAUDE.md

Thank you for contributing!
