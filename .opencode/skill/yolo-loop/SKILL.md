---
name: yolo-loop
description: Run autonomous YOLO loops using Ralph Wiggum style iteration and Loom-style parallel weaving. Use this skill when setting up unattended agent loops, running continuous development sessions, or orchestrating parallel agents across multiple projects.
---

# YOLO Loop - Autonomous Agent Loop Orchestration

YOLO loops enable autonomous, unattended agent operation using the Ralph Wiggum technique (persistent iteration) and Loom-style parallel weaving.

## Core Concepts

### Ralph Wiggum Pattern

Named after The Simpsons character, Ralph Wiggum is a persistent iteration pattern where an agent works on a task repeatedly until completion or safety limits are reached. Instead of stopping when an agent thinks it's done, the loop re-injects the prompt to verify and continue work.

**Key features:**
- Persistent iteration until true completion
- Safety limits (max iterations, timeouts, circuit breakers)
- Completion detection via markers (LOOP_COMPLETE, EXIT_SIGNAL)
- State persistence via AGENCY.md files

### Loom Pattern (Parallel Weaving)

The Loom pattern enables multiple agents to work in parallel on different projects, "weaving" their work together through shared state in AGENCY.md files.

**Key features:**
- Parallel execution of multiple YOLO loops
- Automatic work discovery via Cortex
- Project claiming/release with ownership tracking
- Coordinated state updates

## Commands

### Single YOLO Loop

Run an autonomous loop on a specific task:

```bash
# Basic usage
make yolo PROMPT="Fix all TypeScript errors in src/"

# With iteration limit
make yolo PROMPT="Implement user authentication" MAX_ITER=30

# Direct CLI
uv run python -m src.yolo_loop --prompt "Build feature X" --max-iterations 50
```

### Loom Mode (All Ready Projects)

Run parallel loops on all Hive projects ready for work:

```bash
# Default: 3 parallel agents
make yolo-hive

# Custom parallelism
make yolo-hive PARALLEL=5 MAX_ITER=30

# Direct CLI
uv run python -m src.yolo_loop --hive --parallel 5 --max-iterations 50
```

### Single Project Loop

Run a loop on a specific project's AGENCY.md:

```bash
uv run python -m src.yolo_loop --project projects/my-feature/AGENCY.md
```

### Docker Sandbox (Isolated)

Run loops in Docker containers for complete isolation:

```bash
# Single loop in Docker
make yolo-docker PROMPT="Refactor the API layer"

# Or via CLI
uv run python -m src.yolo_loop --prompt "Fix security issues" --backend docker
```

## Daemon Mode (Continuous Operation)

For unattended 24/7 operation without GitHub Actions:

```bash
# Start daemon
make yolo-daemon

# Custom poll interval (seconds)
make yolo-daemon POLL_INTERVAL=600

# Check status
make yolo-status

# Stop daemon
make yolo-stop
```

The daemon periodically checks for ready work and automatically runs YOLO loops.

## Cloud/Server Deployment

Generate a docker-compose.yml for deployment on any server:

```bash
make yolo-compose
```

Then on your server:

```bash
# Set credentials
export ANTHROPIC_API_KEY="your-key"
export GITHUB_TOKEN="your-token"

# Start
docker-compose -f docker-compose.yolo.yml up -d

# Check logs
docker-compose -f docker-compose.yolo.yml logs -f
```

## Safety Mechanisms

### 1. Iteration Limits

Always set a maximum number of iterations:

```bash
# Recommended: 20-50 for most tasks
uv run python -m src.yolo_loop --prompt "..." --max-iterations 30
```

### 2. Timeout

Set a timeout for the entire loop:

```bash
# 1 hour timeout (default)
uv run python -m src.yolo_loop --prompt "..." --timeout 3600

# 15 minutes for quick tasks
uv run python -m src.yolo_loop --prompt "..." --timeout 900
```

### 3. Circuit Breaker

Automatically stops after consecutive failures (default: 5):

```python
# In LoopConfig
circuit_breaker_threshold: int = 5
```

### 4. Rate Limiting

Prevents runaway API usage:

```python
# Default: 100 calls per hour
rate_limit_per_hour: int = 100
```

### 5. Completion Markers

Loops stop when the agent outputs specific markers:

- `LOOP_COMPLETE` - All tasks finished
- `ALL_TASKS_DONE` - Alternative completion signal
- `EXIT_SIGNAL` - Explicit exit request
- `BLOCKED` - Needs human intervention

## State Management

### AGENCY.md Integration

YOLO loops automatically update project state:

```yaml
# When claiming a project
owner: yolo-loop:yolo-20250117-abc12345
last_updated: 2025-01-17T10:30:00Z

# Agent notes are added automatically
## Agent Notes
- **2025-01-17 10:30 - YOLO Loop**: Started autonomous loop yolo-20250117-abc12345
- **2025-01-17 11:45 - YOLO Loop**: Loop completed with status: completed
```

### State Directory

Loop state is persisted in `.yolo-state/`:

```
.yolo-state/
├── daemon.pid           # PID file for daemon
└── daemon_state.json    # Daemon run history
```

## Programmatic Usage

```python
from src.yolo_loop import YoloLoop, LoopConfig, YoloRunner, LoomWeaver

# Single loop
config = LoopConfig(
    prompt="Fix all bugs in the codebase",
    max_iterations=50,
    timeout_seconds=3600,
)
loop = YoloLoop(config)
state = loop.run()

print(f"Status: {state.status.value}")
print(f"Iterations: {state.current_iteration}")

# High-level runner
state = YoloRunner.run_single(
    prompt="Implement feature X",
    max_iterations=30,
)

# Loom weaver for parallel execution
weaver = LoomWeaver(
    base_path="/path/to/hive",
    max_parallel_agents=3,
)
results = weaver.weave(max_iterations_per_loop=50)
```

## Best Practices

### 1. Start Small

Begin with low iteration limits and increase as needed:

```bash
# Test run
make yolo PROMPT="Fix the login bug" MAX_ITER=5
```

### 2. Use Docker for Untrusted Code

When working on unfamiliar codebases, use Docker isolation:

```bash
make yolo-docker PROMPT="..."
```

### 3. Monitor Token Usage

YOLO loops can consume significant tokens. Monitor usage:

```bash
# Check Weave traces if configured
# Or review API usage dashboard
```

### 4. Set Explicit Completion Criteria

Be specific about what "done" means:

```bash
make yolo PROMPT="Fix all TypeScript errors. When tsc compiles with no errors, output LOOP_COMPLETE"
```

### 5. Use Daemon for Continuous Projects

For long-running projects, the daemon ensures work continues:

```bash
make yolo-daemon POLL_INTERVAL=300  # Check every 5 minutes
```

## Troubleshooting

### "claude CLI not found"

Install Claude Code CLI:

```bash
npm install -g @anthropic-ai/claude-code
```

### "Docker is not running"

Start Docker Desktop or the Docker daemon:

```bash
# macOS/Windows: Start Docker Desktop
# Linux: sudo systemctl start docker
```

### "Rate limit reached"

Wait for the hourly reset or reduce parallel agents:

```bash
make yolo-hive PARALLEL=1  # Reduce parallelism
```

### "Circuit breaker triggered"

Review error logs and fix the underlying issue:

```bash
# Check .yolo-state/daemon_state.json for errors
cat .yolo-state/daemon_state.json | jq '.last_error'
```

### Loop runs forever

Ensure your prompt includes completion criteria:

```bash
# Bad: "Work on the feature"
# Good: "Implement login. When tests pass, output LOOP_COMPLETE"
```

## Security Considerations

1. **Sandboxing**: Use Docker backend for isolation from host system
2. **Network**: Docker runs with `--network=none` by default
3. **Credentials**: API keys are passed via environment variables only
4. **Git safety**: Loops claim/release ownership via AGENCY.md
5. **Resource limits**: Docker containers have memory/CPU limits

## Integration with Agent Hive

YOLO loops integrate seamlessly with Agent Hive:

1. **Cortex**: Uses Cortex to discover ready work
2. **AGENCY.md**: Updates project state automatically
3. **Dependencies**: Respects project dependencies
4. **Multi-agent**: Multiple loops coordinate via ownership
5. **Observability**: Works with Weave tracing

## Example Workflows

### Overnight Feature Development

```bash
# Before bed
make yolo-daemon

# Morning: check results
make yolo-status
git log --oneline -20
```

### Batch Refactoring

```bash
# Process all ready projects
make yolo-hive MAX_ITER=100 PARALLEL=5
```

### CI/CD Integration

```yaml
# In .github/workflows/yolo.yml
- name: Run YOLO loops
  run: make yolo-hive MAX_ITER=30
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```
