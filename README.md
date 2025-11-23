# 🧠 Agent Hive - Vendor-Agnostic Agent Orchestration OS

**Agent Hive** is a production-ready orchestration operating system for autonomous AI agents. It enables seamless coordination across different LLM providers (Claude, Grok, Gemini, etc.) using shared memory stored in Markdown files.

## 🎯 Core Concept

Instead of building vendor-specific workflows, Agent Hive uses a simple but powerful primitive: **AGENCY.md** - a Markdown file with YAML frontmatter that serves as shared memory between AI agents, humans, and automation.

### The Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      GLOBAL.md                              │
│                  (Root System State)                        │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
         ┌──────▼─────┐         ┌──────▼─────┐
         │ AGENCY.md  │         │ AGENCY.md  │
         │ (Project 1)│         │ (Project 2)│
         └──────┬─────┘         └──────┬─────┘
                │                       │
    ┌───────────┼───────────┐          │
    │           │           │          │
┌───▼──┐   ┌───▼──┐   ┌───▼──┐   ┌───▼──┐
│Claude│   │ Grok │   │Gemini│   │Human │
└──────┘   └──────┘   └──────┘   └──────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- OpenRouter API key ([Get one here](https://openrouter.ai/))

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/agent-hive.git
cd agent-hive

# Install dependencies
make install

# Create .env file
make setup-env

# Edit .env and add your API key
nano .env
```

### Your `.env` file should look like:

```bash
OPENROUTER_API_KEY=your-api-key-here
OPENROUTER_MODEL=anthropic/claude-3.5-haiku
HIVE_BASE_PATH=/path/to/agent-hive
```

### Run the Dashboard

```bash
make dashboard
```

Open http://localhost:8501 in your browser.

### Run Cortex (CLI)

```bash
make cortex
```

This runs the orchestration engine that analyzes all projects and updates state.

## 📁 Repository Structure

```
agent-hive/
├── .devcontainer/
│   └── devcontainer.json       # DevContainer config (Codespaces/Cursor ready)
├── .github/
│   └── workflows/
│       └── cortex.yml          # Automated 4-hour heartbeat
├── config/
│   └── app-manifest.json       # GitHub App definition (for SaaS)
├── projects/
│   └── demo/
│       └── AGENCY.md           # Example project
├── scripts/
│   └── start_session.sh        # Deep Work session bootstrap
├── src/
│   ├── cortex.py               # Orchestration logic
│   └── dashboard.py            # Streamlit UI
├── GLOBAL.md                   # Root system state
├── Makefile                    # Convenience commands
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## 🧩 Core Components

### 1. AGENCY.md - The Shared Memory

Every project has an `AGENCY.md` file with:

```markdown
---
project_id: my-project
status: active
owner: null
last_updated: 2025-01-15T10:30:00Z
blocked: false
blocking_reason: null
priority: high
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

### 2. Cortex - The Orchestration Engine

`cortex.py` reads all AGENCY.md files, calls an LLM to analyze the state, and updates files accordingly. It:

- ✅ Never executes code blindly
- ✅ Only updates Markdown frontmatter
- ✅ Identifies blocked tasks
- ✅ Suggests new project creation
- ✅ Runs every 4 hours via GitHub Actions

### 3. Dashboard - The UI

`dashboard.py` is a Streamlit app that:

- 📊 Visualizes all projects
- 🚀 Generates "Deep Work" contexts
- 🧠 Triggers Cortex manually
- 📋 Displays task lists and metadata

## 🎓 Usage Patterns

### Pattern 1: Autonomous Orchestration

Let GitHub Actions run Cortex every 4 hours. It will:
1. Read all AGENCY.md files
2. Identify blocked tasks
3. Update project statuses
4. Commit changes back to the repo

```bash
# Enable the workflow
git push origin main

# Monitor runs
gh workflow view cortex.yml
```

### Pattern 2: Deep Work Sessions

Use the bootstrap script to generate context for manual agent work:

```bash
make session PROJECT=projects/demo
```

This creates a `SESSION_CONTEXT.md` file with:
- Full AGENCY.md content
- File tree
- Handoff instructions
- Persona guidelines

Copy this to your AI agent (Claude, Cursor, etc.) and let it work.

### Pattern 3: Multi-Agent Collaboration

Different agents can work on the same project:

1. **Agent A (Claude)**: Does research, updates AGENCY.md
2. **Cortex**: Detects completion, marks next task
3. **Agent B (Grok)**: Picks up next task, continues work
4. **Human**: Reviews in Dashboard, adds new tasks

## 🔧 Configuration

### OpenRouter Models

Edit `.env` to change the model:

```bash
# Fast and cheap (default)
OPENROUTER_MODEL=anthropic/claude-3.5-haiku

# More capable
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# Alternative providers
OPENROUTER_MODEL=google/gemini-pro
OPENROUTER_MODEL=x-ai/grok-beta
```

### GitHub Actions Schedule

Edit `.github/workflows/cortex.yml`:

```yaml
schedule:
  # Run every 2 hours instead of 4
  - cron: '0 */2 * * *'
```

### GitHub App Deployment (Optional)

To deploy Agent Hive as a GitHub App:

1. Go to GitHub Settings > Developer > GitHub Apps > New GitHub App
2. Use `config/app-manifest.json` as the base configuration
3. Set webhook URL to your server
4. Install on repositories

## 🛠️ Development

### Project Structure

- `src/cortex.py` - Core orchestration logic
- `src/dashboard.py` - Streamlit UI
- `scripts/start_session.sh` - Session bootstrap
- `.devcontainer/` - DevContainer configuration

### Running Tests

```bash
make test
```

### Code Formatting

```bash
make format
```

### Linting

```bash
make lint
```

## 📖 Creating a New Project

1. Create a directory in `projects/`:

```bash
mkdir projects/my-new-project
```

2. Create an `AGENCY.md` file (copy from `projects/demo/AGENCY.md`):

```bash
cp projects/demo/AGENCY.md projects/my-new-project/AGENCY.md
```

3. Edit the frontmatter and content:

```yaml
---
project_id: my-new-project
status: active
owner: null
last_updated: null
blocked: false
priority: high
tags: [new-feature]
---

# My New Project

## Objective
Build a new feature that...
```

4. Run Cortex:

```bash
make cortex
```

The project will now be tracked automatically.

## 🌐 Deployment Options

### Option 1: GitHub Actions (Free Tier)

Already configured! Just push to GitHub and enable Actions.

### Option 2: Local Cron Job

```bash
# Add to crontab
0 */4 * * * cd /path/to/agent-hive && python src/cortex.py
```

### Option 3: Cloud VM

Deploy to AWS/GCP/Azure with:
- Cron job running Cortex
- Nginx serving Dashboard
- GitHub App webhook receiver

### Option 4: Codespaces

Open in GitHub Codespaces for instant MCP-enabled environment:

```bash
# The DevContainer is pre-configured
# Just open in Codespaces and run:
make dashboard
```

## 🧪 Advanced: MCP Integration

The DevContainer includes Model Context Protocol (MCP) filesystem server. This allows agents like Claude to:

- Read/write files safely
- Execute within sandboxed environment
- Access project context directly

When using Cursor/Claude Code in the DevContainer, agents automatically have filesystem access via MCP.

## 📚 Philosophy

Agent Hive is built on these principles:

1. **Vendor Agnostic**: Works with any LLM provider
2. **Human-in-the-Loop**: Always transparent, never autonomous
3. **Simple Primitives**: Markdown files as shared memory
4. **Git as Source of Truth**: All state is versioned
5. **Free Infrastructure**: Runs on GitHub Actions free tier

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Troubleshooting

### "OPENROUTER_API_KEY not set"

Edit your `.env` file and add your API key from https://openrouter.ai/

### "No projects found"

Make sure you have at least one `AGENCY.md` file in a subdirectory of `projects/`.

### GitHub Actions not running

1. Check that the workflow is enabled in your repo settings
2. Ensure `OPENROUTER_API_KEY` is set as a repository secret
3. Verify the cron schedule in `.github/workflows/cortex.yml`

### Streamlit dashboard won't start

```bash
# Reinstall dependencies
pip install -r requirements.txt

# Check for port conflicts
lsof -i :8501
```

## 🎯 Roadmap

- [ ] Web-based Dashboard (hosted version)
- [ ] Multi-repository support
- [ ] Slack/Discord integration
- [ ] Agent performance metrics
- [ ] Custom LLM provider support
- [ ] Visual workflow builder

## 📞 Support

- GitHub Issues: https://github.com/your-org/agent-hive/issues
- Discussions: https://github.com/your-org/agent-hive/discussions

---

Built with ❤️ by the Agent Hive community.

**Happy orchestrating!** 🚀
