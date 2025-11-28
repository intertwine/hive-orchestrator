# 🧠 Agent Hive - Vendor-Agnostic Agent Orchestration OS

**Agent Hive** is a production-ready orchestration operating system for autonomous AI agents. It enables seamless coordination across different LLM providers (Claude, Grok, Gemini, etc.) using shared memory stored in Markdown files.

> **Inspiration**: Some patterns in Agent Hive were inspired by [beads](https://github.com/steveyegge/beads), particularly the ready work detection, dependency tracking, and MCP integration concepts. We've adapted these ideas for our Markdown-first, vendor-agnostic approach.

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
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer
- OpenRouter API key ([Get one here](https://openrouter.ai/))

### Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/your-org/agent-hive.git
cd agent-hive

# Install dependencies with uv
make install

# Create .env file
make setup-env

# Edit .env and add your API key
nano .env
```

### Your `.env` file should look like:

```bash
OPENROUTER_API_KEY=your-api-key-here
OPENROUTER_MODEL=anthropic/claude-haiku-4.5
HIVE_BASE_PATH=/path/to/agent-hive

# Optional: Real-time coordination server
COORDINATOR_URL=http://localhost:8080
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
├── .claude/
│   └── skills/                 # Claude Code skills for Agent Hive
│       ├── hive-project-management/
│       ├── cortex-operations/
│       ├── deep-work-session/
│       ├── multi-agent-coordination/
│       └── hive-mcp/
├── .devcontainer/
│   └── devcontainer.json       # DevContainer config (Codespaces/Cursor ready)
├── .github/
│   └── workflows/
│       └── cortex.yml          # Automated 4-hour heartbeat
├── config/
│   └── app-manifest.json       # GitHub App definition (for SaaS)
├── examples/
│   └── */                      # Example workflows (7 patterns)
├── projects/
│   └── */                      # Your project workspaces
│       └── AGENCY.md           # Project shared memory
├── scripts/
│   └── start_session.sh        # Deep Work session bootstrap
├── src/
│   ├── cortex.py               # Orchestration logic
│   ├── coordinator.py          # Real-time coordination server (optional)
│   ├── coordinator_client.py   # Coordinator client library
│   ├── dashboard.py            # Streamlit UI
│   └── hive_mcp/               # MCP server for AI agents
│       ├── __init__.py
│       ├── __main__.py
│       └── server.py           # MCP tool implementations
├── tests/                      # Test suite (150+ tests)
├── GLOBAL.md                   # Root system state
├── Makefile                    # Convenience commands
├── pyproject.toml              # Python project configuration & dependencies
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
dependencies:
  blocked_by: [other-project]  # This project waits for these
  blocks: [downstream-project]  # These projects wait for us
  parent: epic-project          # Part of a larger epic (optional)
  related: [context-project]    # Related but non-blocking (optional)
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

| Field | Description |
|-------|-------------|
| `project_id` | Unique identifier for the project |
| `status` | `active`, `pending`, `blocked`, or `completed` |
| `owner` | Agent currently working (or `null` if unclaimed) |
| `blocked` | `true` if blocked on external dependency |
| `priority` | `low`, `medium`, `high`, or `critical` |
| `dependencies.blocked_by` | Projects that must complete before this one |
| `dependencies.blocks` | Projects waiting on this one |

### 2. Cortex - The Orchestration Engine

`cortex.py` reads all AGENCY.md files, calls an LLM to analyze the state, and updates files accordingly. It:

- ✅ Never executes code blindly
- ✅ Only updates Markdown frontmatter
- ✅ Identifies blocked tasks
- ✅ Suggests new project creation
- ✅ Runs every 4 hours via GitHub Actions
- ✅ **Ready Work Detection** - Find actionable projects without LLM calls
- ✅ **Dependency Tracking** - Build and analyze dependency graphs
- ✅ **Cycle Detection** - Prevent deadlocks from circular dependencies

**CLI Commands:**

```bash
# Full orchestration run (uses LLM)
make cortex

# Fast ready work detection (no LLM, instant)
make ready              # Human-readable output
make ready-json         # JSON for programmatic use

# Dependency analysis (no LLM, instant)
make deps               # Human-readable dependency graph
make deps-json          # JSON for programmatic use
```

### 3. Dashboard - The UI

`dashboard.py` is a Streamlit app that:

- 📊 Visualizes all projects
- 🚀 Generates "Deep Work" contexts
- 🧠 Triggers Cortex manually
- 📋 Displays task lists and metadata
- 🔗 Shows dependency graphs and blocking status
- ⚠️ Alerts on dependency cycles

### 4. Hive MCP Server - AI Agent Integration

The `hive-mcp` server enables AI agents like Claude to interact with Agent Hive programmatically via the [Model Context Protocol](https://modelcontextprotocol.io/).

**Available Tools:**

| Tool | Description |
|------|-------------|
| `list_projects` | List all discovered projects with metadata |
| `get_ready_work` | Get projects ready for an agent to claim |
| `get_project` | Get full details of a specific project |
| `claim_project` | Set owner field to claim work |
| `release_project` | Set owner to null |
| `update_status` | Change project status |
| `add_note` | Append to agent notes section |
| `get_dependencies` | Get dependency info for a project |
| `get_dependency_graph` | Get full dependency graph |
| `coordinator_status` | Check if coordination server is available |
| `coordinator_claim` | Claim project via coordination server |
| `coordinator_release` | Release project via coordination server |
| `coordinator_reservations` | Get all active reservations |

**Claude Desktop Configuration:**

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hive": {
      "command": "uv",
      "args": ["run", "python", "-m", "hive_mcp"],
      "env": {
        "HIVE_BASE_PATH": "/path/to/your/agent-hive"
      }
    }
  }
}
```

**Run Standalone:**

```bash
uv run python -m hive_mcp
```

### 5. Coordinator Server - Real-time Conflict Prevention (Optional)

The Coordinator Server provides an optional real-time coordination layer for scenarios where multiple agents need to work concurrently without git conflicts.

> **Note**: This is fully optional. Agent Hive works perfectly with git-only coordination. The Coordinator is for teams wanting faster real-time conflict resolution.

**Start the server:**

```bash
# Default: localhost:8080
uv run python -m src.coordinator

# Custom host/port
COORDINATOR_HOST=0.0.0.0 COORDINATOR_PORT=9000 uv run python -m src.coordinator
```

**Configure clients:**

```bash
# Add to .env
COORDINATOR_URL=http://localhost:8080
```

**API Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with active claim count |
| `/claim` | POST | Claim a project (returns 409 if already claimed) |
| `/release/{project_id}` | DELETE | Release a project claim |
| `/status/{project_id}` | GET | Check claim status of a project |
| `/reservations` | GET | List all active reservations |
| `/extend/{project_id}` | POST | Extend claim TTL |

**Claim Request Example:**

```bash
curl -X POST http://localhost:8080/claim \
  -H "Content-Type: application/json" \
  -d '{"project_id": "my-project", "agent_name": "claude-opus", "ttl_seconds": 3600}'
```

**Response (Success - 200):**
```json
{
  "success": true,
  "claim_id": "uuid-here",
  "project_id": "my-project",
  "agent_name": "claude-opus",
  "expires_at": "2025-01-01T12:00:00Z"
}
```

**Response (Conflict - 409):**
```json
{
  "success": false,
  "error": "Project already claimed",
  "current_owner": "grok-beta",
  "claimed_at": "2025-01-01T10:00:00Z",
  "expires_at": "2025-01-01T11:00:00Z"
}
```

**Features:**
- Automatic claim expiration (configurable TTL, default 1 hour)
- Force-claim option for admin override (`?force=true`)
- Background cleanup of expired claims
- Graceful degradation (clients fall back to git-only when unavailable)
- OpenAPI documentation at `/docs`

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
OPENROUTER_MODEL=anthropic/claude-haiku-4.5

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

Agent Hive provides two levels of MCP integration:

### Hive MCP Server (Recommended)

The built-in `hive-mcp` server gives AI agents direct access to Agent Hive operations:

```bash
# Install and run
uv run python -m hive_mcp
```

This enables agents to:
- 📋 List and query projects programmatically
- 🎯 Find ready work without scanning files
- 🔒 Claim/release projects atomically
- 📝 Update status and add notes
- 🔗 Navigate dependency graphs

See [Hive MCP Server](#4-hive-mcp-server---ai-agent-integration) for configuration.

### DevContainer Filesystem MCP

The DevContainer also includes a generic filesystem MCP server for lower-level file operations. When using Cursor/Claude Code in the DevContainer, agents have filesystem access for reading/writing files directly.

## 🎯 Claude Code Skills

Agent Hive includes a set of [Claude Code Skills](https://www.anthropic.com/news/skills) that teach Claude how to work effectively with the orchestration system. Skills are modular instruction sets that Claude loads automatically when relevant to your task.

### Available Skills

| Skill | Description | Use When |
|-------|-------------|----------|
| **hive-project-management** | Managing AGENCY.md files, frontmatter fields, task tracking | Creating/updating projects, managing ownership |
| **cortex-operations** | Running Cortex CLI, dependency analysis, ready work detection | Finding work, analyzing dependencies, running orchestration |
| **deep-work-session** | Focused work sessions, handoff protocol, session lifecycle | Starting/ending work sessions, following protocols |
| **multi-agent-coordination** | Multi-agent patterns, conflict prevention, coordination server | Working with other agents, preventing conflicts |
| **hive-mcp** | MCP server tools, programmatic project access | Using MCP tools for project management |

### How Skills Work

Skills use **progressive disclosure** - Claude loads only the skill name and description at startup, then loads full instructions when needed:

```
1. Startup: Load skill metadata (name + description)
2. Task Match: Claude detects relevant skill from your request
3. Activation: Full skill instructions loaded into context
4. Execution: Claude follows skill guidance for the task
```

### Skill Location

Skills are stored in `.claude/skills/` with this structure:

```
.claude/skills/
├── hive-project-management/
│   └── SKILL.md
├── cortex-operations/
│   └── SKILL.md
├── deep-work-session/
│   └── SKILL.md
├── multi-agent-coordination/
│   └── SKILL.md
└── hive-mcp/
    └── SKILL.md
```

### Using Skills

Skills activate automatically based on your request. Examples:

```
# Activates: hive-project-management
"Create a new project for the authentication feature"

# Activates: cortex-operations
"Find projects that are ready for me to work on"

# Activates: deep-work-session
"Start a deep work session on the demo project"

# Activates: multi-agent-coordination
"How do I coordinate with other agents on this project?"

# Activates: hive-mcp
"Use the MCP tools to claim project demo"
```

### What Skills Teach Claude

Each skill provides comprehensive guidance:

- **hive-project-management**: AGENCY.md structure, all frontmatter fields, task management, ownership rules, dependency configuration
- **cortex-operations**: CLI commands (`--ready`, `--deps`, `--json`), output interpretation, troubleshooting, programmatic usage
- **deep-work-session**: Session lifecycle (enter → claim → work → update → handoff), checklist, blocking protocol
- **multi-agent-coordination**: Ownership protocol, dependency flow, coordinator API, conflict resolution patterns
- **hive-mcp**: All 12 MCP tools with arguments, response formats, workflow examples

### Installing Additional Skills

You can add custom skills or install from the [Anthropic Skills repository](https://github.com/anthropics/skills):

```bash
# Create a new skill
mkdir .claude/skills/my-custom-skill
cat > .claude/skills/my-custom-skill/SKILL.md << 'EOF'
---
name: my-custom-skill
description: Description of what this skill does and when to use it
---

# My Custom Skill

Instructions for Claude to follow...
EOF
```

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
make install

# Or sync dependencies
make sync

# Check for port conflicts
lsof -i :8501
```

## 🎯 Roadmap

**Completed:**
- [x] Ready work detection (fast, no LLM required)
- [x] Dependency tracking with cycle detection
- [x] MCP server for AI agent integration
- [x] JSON output mode for programmatic access
- [x] Dashboard dependency visualization
- [x] Real-time agent coordination layer (HTTP API)
- [x] Claude Code Skills for guided AI workflows

**Planned:**
- [ ] Web-based Dashboard (hosted version)
- [ ] Multi-repository support
- [ ] Slack/Discord integration
- [ ] Agent performance metrics
- [ ] Visual workflow builder
- [ ] Docker deployment for coordinator

## 📞 Support

- GitHub Issues: https://github.com/your-org/agent-hive/issues
- Discussions: https://github.com/your-org/agent-hive/discussions

---

Built with ❤️ by the Agent Hive community.

**Happy orchestrating!** 🚀
