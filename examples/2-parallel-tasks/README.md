# Parallel Tasks Workflow Example

## Overview

This example demonstrates **concurrent execution** where multiple agents work on independent tasks simultaneously. This pattern maximizes throughput when tasks have no dependencies.

## Pattern: Parallel Execution

```
    ┌──────────────┐
    │   Agent A    │
    │ (Validators) │
    └──────────────┘
           ║
    ┌──────────────┐
    │   Agent B    │────────▶  All complete  ─────▶ Project Done
    │ (Formatters) │
    └──────────────┘
           ║
    ┌──────────────┐
    │   Agent C    │
    │  (Parsers)   │
    └──────────────┘
           ║
    ┌──────────────┐
    │   Agent D    │
    │  (Strings)   │
    └──────────────┘
```

## Use Case

Perfect for:
- **Independent modules**: Each component has no dependencies
- **Speed**: Parallelization dramatically reduces completion time
- **Resource utilization**: Multiple AI sessions running concurrently
- **Team simulation**: Like having multiple developers working simultaneously

## How to Run

### Method 1: Fully Parallel (Recommended)

Launch 4 separate AI agent sessions simultaneously:

**Terminal 1: Agent A (Validators)**
```bash
# Generate context for Task A
make session PROJECT=examples/2-parallel-tasks

# In your AI interface:
# - Use Claude Haiku 4.5 or similar
# - Claim Task A in your notes
# - Build src/validators.py
# - Mark Task A complete
```

**Terminal 2: Agent B (Formatters)**
```bash
# Same project, different task
make session PROJECT=examples/2-parallel-tasks

# Use different AI session/window
# - Claim Task B
# - Build src/formatters.py
# - Mark Task B complete
```

**Terminal 3: Agent C (Parsers)**
```bash
make session PROJECT=examples/2-parallel-tasks
# Claim Task C, build src/parsers.py
```

**Terminal 4: Agent D (Strings)**
```bash
make session PROJECT=examples/2-parallel-tasks
# Claim Task D, build src/strings.py
```

### Method 2: Sequential Simulation

If you can't run parallel sessions, simulate it by switching between agents:

```bash
# Round 1: Each agent does 25% of work
# Agent A: Start validators.py
# Agent B: Start formatters.py
# Agent C: Start parsers.py
# Agent D: Start strings.py

# Round 2: Each continues
# (Repeat until all complete)
```

### Method 3: Automated Orchestration

```bash
# Cortex can dispatch to multiple agents
# (Requires multi-agent configuration)
uv run python src/cortex.py --parallel
```

## Expected Output

After completion:

1. **Four new modules**:
   - `src/validators.py` - Email validation
   - `src/formatters.py` - Date formatting
   - `src/parsers.py` - JSON parsing
   - `src/strings.py` - String utilities

2. **Updated AGENCY.md** showing:
   - All 4 tasks marked complete
   - Agent notes from each agent
   - Timestamps showing concurrent work

3. **Git commits** from each agent (possibly interleaved)

## Key Concepts Demonstrated

### 1. Task Independence

Each task touches different files:
```
validators.py  ← Agent A only
formatters.py  ← Agent B only
parsers.py     ← Agent C only
strings.py     ← Agent D only
```

No coordination needed!

### 2. Concurrent Progress Tracking

AGENCY.md is updated by multiple agents:
```yaml
# Agent A finishes first
- **10:30 - Agent A**: Completed validators

# Agent C finishes second
- **10:35 - Agent C**: Completed parsers

# Agent B finishes third
- **10:40 - Agent B**: Completed formatters

# Agent D finishes last
- **10:50 - Agent D**: Completed strings, project done!
```

### 3. No Blocking

Unlike Example 1 (sequential), agents don't wait:
- ✅ Agent A doesn't wait for anyone
- ✅ Agent B doesn't wait for anyone
- ✅ Agent C doesn't wait for anyone
- ✅ Agent D doesn't wait for anyone

All work simultaneously!

### 4. Completion Detection

Project completes when **all tasks** are done:
```markdown
- [x] Email Validator ✓
- [x] Date Formatter ✓
- [x] JSON Parser ✓
- [x] String Utilities ✓

Status: completed  ← All done!
```

## Benefits of Parallel Execution

### Speed
- **Sequential**: 4 tasks × 15 min = 60 minutes
- **Parallel**: max(15, 15, 15, 15) = 15 minutes
- **Speedup**: 4x faster! 🚀

### Cost Efficiency
- Use cheaper models (Haiku 4.5) for simple tasks (A, B, D)
- Use powerful model (Sonnet) only where needed (C)
- Total cost optimized vs. using Sonnet for everything

### Scalability
- Add 10 more tasks? Still completes in ~15 minutes
- Limited only by number of parallel sessions
- Mimics real team development

## Variations to Try

### Different Scales
- **Micro**: 2 parallel tasks
- **Medium**: 4 tasks (this example)
- **Large**: 10+ tasks (microservices architecture)

### Different Domains
- **Frontend components**: Header, Footer, Sidebar, Form components
- **API endpoints**: GET /users, POST /users, GET /products, etc.
- **Database migrations**: Create tables in parallel (independent schemas)
- **Documentation pages**: Each agent writes different doc section

### Mixed Models
- **All Haiku 4.5**: Simple, fast, cheap
- **Mixed**: Haiku 4.5 for simple, Sonnet for complex (this example)
- **Multi-vendor**: Claude + GPT-4 + Gemini + Grok all working together

## Handling Dependencies

What if Task C depends on Task A?

### Option 1: Split into Phases
```
Phase 1 (Parallel): A, B, D
Phase 2 (After A): C
```

### Option 2: Conditional Start
Agent C checks if Task A is complete before starting:
```markdown
- **Agent C**: Waiting for Task A completion...
- **Agent A**: Task A done!
- **Agent C**: Starting Task C now
```

### Option 3: Different Examples
Use Example 1 (Sequential) or Example 3 (Pipeline) for dependent tasks

## Troubleshooting

**Git conflicts when committing:**
- Ensure each agent works on **different files**
- If conflicts occur, pull before pushing:
  ```bash
  git pull --rebase origin main
  git push
  ```

**Hard to track which agent does what:**
- Use agent notes with clear timestamps
- Include agent identifier in commit messages
- Check Git log: `git log --oneline --graph`

**One task blocks others:**
- Check if tasks are truly independent
- Review file dependencies
- Consider if sequential pattern is better

**Agents interfere with each other:**
- Assign clear, non-overlapping responsibilities
- Use different files or modules
- Document boundaries in AGENCY.md

## Real-World Applications

### Microservices Development
- Service A: Auth service
- Service B: Payment service
- Service C: Notification service
- Service D: Analytics service

### Content Creation
- Agent A: Write blog post
- Agent B: Create social media posts
- Agent C: Design graphics
- Agent D: Write email newsletter

### Data Processing
- Agent A: Process dataset 1
- Agent B: Process dataset 2
- Agent C: Process dataset 3
- Agent D: Aggregate results

### Testing
- Agent A: Unit tests
- Agent B: Integration tests
- Agent C: E2E tests
- Agent D: Performance tests

## Next Steps

- Try **Example 3: Code Review Pipeline** for dependent tasks with iteration
- Try **Example 4: Multi-Model Ensemble** for competitive parallel approaches
- Try **Example 7: Complex Application** for mixed parallel + sequential

---

**Estimated time**: 15 minutes per agent (total: 15 min parallel, 60 min sequential)
**Difficulty**: Intermediate
**Models required**: 4 (can be mix of different models)
**Speedup vs Sequential**: 4x
