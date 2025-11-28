# Getting Started: Your First Agent Hive Project

*This is the sixth article in a series exploring Agent Hive and AI agent orchestration.*

---

## From Zero to Orchestration

You've read about the theory. You understand why agent memory matters, how dependencies work, and what protocols to follow. Now let's build something.

In this guide, we'll set up Agent Hive from scratch and create your first orchestrated project.

## Prerequisites

Before starting, you'll need:

- **Python 3.11+** installed
- **Git** for version control
- **[uv](https://github.com/astral-sh/uv)** - Fast Python package installer
- **OpenRouter API key** (for Cortex LLM calls) - [Get one here](https://openrouter.ai/)

Install uv if you haven't:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Step 1: Clone and Install

```bash
# Clone the repository
git clone https://github.com/intertwine/hive-orchestrator.git
cd hive-orchestrator

# Install dependencies
make install

# Create environment file
make setup-env
```

Edit `.env` with your API key:

```bash
OPENROUTER_API_KEY=your-api-key-here
OPENROUTER_MODEL=anthropic/claude-haiku-4.5
HIVE_BASE_PATH=/path/to/hive-orchestrator
```

## Step 2: Explore the Structure

Take a look at what's included:

```
hive-orchestrator/
├── projects/           # Your projects live here
│   └── demo/
│       └── AGENCY.md   # Example project
├── src/
│   ├── cortex.py       # Orchestration engine
│   ├── dashboard.py    # Web UI
│   └── hive_mcp/       # MCP server
├── GLOBAL.md           # System-wide state
└── .claude/skills/     # Agent skills
```

Read the demo project:

```bash
cat projects/demo/AGENCY.md
```

This shows the AGENCY.md format in action.

## Step 3: Run the Dashboard

Launch the web interface:

```bash
make dashboard
```

Open http://localhost:8501 in your browser. You'll see:

- **Project list** in the sidebar
- **Project details** in the main area
- **System status** showing last Cortex run
- **Deep Work context generator** for agent sessions

Explore the demo project to see how information is displayed.

## Step 4: Create Your First Project

Let's create a real project. We'll make a simple one: implementing a configuration system.

### Create the Directory

```bash
mkdir -p projects/config-system
```

### Create AGENCY.md

Create `projects/config-system/AGENCY.md`:

```markdown
---
project_id: config-system
status: active
owner: null
last_updated: null
blocked: false
blocking_reason: null
priority: high
tags: [feature, infrastructure]
dependencies:
  blocked_by: []
  blocks: []
  parent: null
  related: []
---

# Configuration System

## Objective

Implement a configuration management system that supports:
- Environment-based configuration (dev, staging, prod)
- YAML configuration files
- Environment variable overrides
- Type validation

## Tasks

- [ ] Research existing configuration libraries
- [ ] Design configuration schema
- [ ] Implement configuration loader
- [ ] Add environment variable override support
- [ ] Write unit tests
- [ ] Document usage

## Success Criteria

- Configuration loads from YAML files
- Environment variables override file values
- Invalid configurations raise clear errors
- 90%+ test coverage

## Agent Notes

*No notes yet*
```

### Verify It's Discovered

```bash
uv run python -m src.cortex --ready
```

You should see your new project listed as ready work.

## Step 5: Generate Deep Work Context

In the dashboard:

1. Select "config-system" from the sidebar
2. Click "Generate Context"
3. Copy the generated context

This context package contains everything an agent needs to start working: the AGENCY.md content, file structure, protocols, and instructions.

## Step 6: Work on the Project

Now you can either:

### Option A: Work Manually

Edit files directly, updating AGENCY.md as you progress:

```markdown
## Tasks
- [x] Research existing configuration libraries
- [ ] Design configuration schema
...

## Agent Notes
- **2025-01-15 14:30 - human**: Researched pydantic-settings, dynaconf,
  and python-dotenv. Recommending pydantic-settings for type safety.
```

### Option B: Use an AI Agent

Paste the Deep Work context into Claude, GPT-4, or your agent of choice. The context instructs the agent to:

1. Claim ownership
2. Work on highest priority tasks
3. Update progress
4. Document decisions
5. Follow handoff protocol

### Option C: Use MCP Tools (Advanced)

If you have the MCP server configured:

```bash
# Start the MCP server
uv run python -m hive_mcp
```

Agents with MCP integration can then use tools like:
- `claim_project("config-system", "claude-sonnet-4")`
- `add_note("config-system", "claude-sonnet-4", "Starting research...")`
- `update_status("config-system", "active")`

## Step 7: Run Cortex

After some work has been done, run the orchestration engine:

```bash
make cortex
```

Cortex will:
1. Read all AGENCY.md files
2. Analyze project states
3. Identify blocked tasks
4. Update metadata where appropriate
5. Report findings

This is what runs automatically every 4 hours via GitHub Actions.

## Step 8: Add Dependencies

Let's say your config system will be used by an API project. Create the dependency:

### Create the Dependent Project

```bash
mkdir -p projects/api-server
```

Create `projects/api-server/AGENCY.md`:

```markdown
---
project_id: api-server
status: active
owner: null
last_updated: null
blocked: false
blocking_reason: null
priority: high
tags: [feature, api]
dependencies:
  blocked_by: [config-system]
  blocks: []
---

# API Server

## Objective

Build REST API server using the configuration system.

## Tasks

- [ ] Set up FastAPI application
- [ ] Integrate configuration system
- [ ] Implement health endpoint
- [ ] Add authentication middleware
- [ ] Write API tests

## Agent Notes

*Waiting for config-system to complete*
```

### Check the Dependency Graph

```bash
uv run python -m src.cortex --deps
```

Output shows:

```
BLOCKED PROJECTS:
----------------------------------------
*** api-server
    Status: active
    Blocked by: config-system
    Reason: Blocked by uncompleted: config-system

UNBLOCKED PROJECTS:
----------------------------------------
    config-system [active]
      Blocks: api-server
```

The api-server won't appear in ready work until config-system is completed.

## Step 9: Complete and Hand Off

When config-system is done, update its status:

```yaml
---
project_id: config-system
status: completed
owner: null
last_updated: 2025-01-15T16:30:00Z
---
```

Now check ready work again:

```bash
uv run python -m src.cortex --ready
```

api-server should now appear as ready!

## Step 10: Enable GitHub Actions (Optional)

To run Cortex automatically:

1. Push your fork to GitHub
2. Add `OPENROUTER_API_KEY` as a repository secret
3. Enable Actions in your repository settings

The `.github/workflows/cortex.yml` workflow runs Cortex every 4 hours, analyzing your projects and committing any state updates.

## Common Patterns

### Pattern: Sequential Feature Development

```
research → design → implement → test → deploy
```

Create five projects with linear `blocked_by` dependencies.

### Pattern: Parallel Workstreams

```
frontend-feature (no deps)
backend-feature (no deps)
mobile-feature (no deps)
integration-tests (blocked_by: all above)
```

Three independent projects, then one that waits for all.

### Pattern: Epic with Sub-Projects

```
user-epic (parent)
├── user-auth (parent: user-epic)
├── user-profile (parent: user-epic)
└── user-settings (parent: user-epic)
```

Group related work under a parent for organization.

## Troubleshooting

### "OPENROUTER_API_KEY not set"

Edit `.env` and add your API key:

```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxx
```

### "No projects found"

Ensure AGENCY.md files are in subdirectories of `projects/`:

```
projects/
└── my-project/
    └── AGENCY.md  ← Must be named exactly this
```

### Dashboard won't start

Reinstall dependencies:

```bash
make install
make dashboard
```

### Cortex finds cycles

Review your dependencies. Cycles can't be resolved automatically:

```bash
uv run python -m src.cortex --deps
# Look for "CYCLES DETECTED" in output
```

Break the cycle by removing or restructuring dependencies.

### Agent not following protocol

Ensure the Deep Work context was fully copied. The protocol instructions tell the agent how to behave—without them, agents may not know to update AGENCY.md.

## Next Steps

You now have a working Agent Hive setup. Here's where to go next:

1. **Read the other articles** in this series for deeper understanding
2. **Explore the examples/** directory for more patterns
3. **Try the MCP server** for programmatic agent integration
4. **Set up the coordinator** for real-time multi-agent work
5. **Contribute** - PRs and issues welcome!

## Quick Reference

```bash
# Install
make install

# Dashboard
make dashboard

# Find ready work
make ready          # Human-readable
make ready-json     # JSON

# View dependencies
make deps           # Human-readable
make deps-json      # JSON

# Run Cortex (LLM analysis)
make cortex

# Start coordinator (optional)
uv run python -m src.coordinator

# Start MCP server (for agents)
uv run python -m hive_mcp
```

---

*Welcome to Agent Hive. We're excited to see what you build.*

*Agent Hive is open source at [github.com/intertwine/hive-orchestrator](https://github.com/intertwine/hive-orchestrator).*
