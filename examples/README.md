# Agent Hive Examples

Welcome to the Agent Hive examples! This directory contains diverse, production-ready examples demonstrating how to orchestrate multi-agent workflows using simple primitives: **Markdown files as shared memory**.

## 🎯 Quick Start

**New to Agent Hive?** Start here:
1. Read [Example 1: Simple Sequential](#1-simple-sequential) to understand basic handoffs
2. Try [Example 2: Parallel Tasks](#2-parallel-tasks) to see concurrent execution
3. Explore others based on your use case

**Want to build something real?** Jump to:
- [Example 7: Complex Application](#7-complex-application) for a complete full-stack project

## 📚 Examples Overview

| # | Example | Pattern | Difficulty | Time | Models | Best For |
|---|---------|---------|------------|------|--------|----------|
| 1 | [Simple Sequential](#1-simple-sequential) | A→B | ⭐ Beginner | 15-30m | 2 | Learning basics |
| 2 | [Parallel Tasks](#2-parallel-tasks) | A‖B‖C‖D | ⭐⭐ Intermediate | 15m | 4 | Speed, scalability |
| 3 | [Code Review Pipeline](#3-code-review-pipeline) | A→B→A→B | ⭐⭐⭐ Advanced | 60-90m | 2 | Quality assurance |
| 4 | [Multi-Model Ensemble](#4-multi-model-ensemble) | A‖B‖C‖D→Judge | ⭐⭐⭐ Advanced | 90-120m | 4-5 | Critical decisions |
| 5 | [Data Pipeline](#5-data-pipeline) | A→B→C→D→E→F | ⭐⭐⭐ Advanced | 60-90m | 6 | ETL workflows |
| 6 | [Creative Collaboration](#6-creative-collaboration) | Sequential+Parallel | ⭐⭐ Intermediate | 2-4h | 6 | Creative projects |
| 7 | [Complex Application](#7-complex-application) | All patterns | ⭐⭐⭐⭐ Expert | 2.5-4h | 12 | Production apps |

## 📖 Detailed Examples

### 1. Simple Sequential

**Pattern**: A → B (Basic handoff)

```
Research → Implementation
```

**What you'll learn**:
- How agents hand off work via AGENCY.md
- Using the `owner` field for coordination
- Shared memory through Markdown
- Model selection (cheap vs. powerful)

**Use cases**:
- Research → Code
- Design → Implementation
- Analysis → Report

**→ [View Example 1](1-simple-sequential/README.md)**

---

### 2. Parallel Tasks

**Pattern**: A ‖ B ‖ C ‖ D (Concurrent execution)

```
    ┌─ Task A ─┐
    ├─ Task B ─┤
    ├─ Task C ─┤→ All Complete
    └─ Task D ─┘
```

**What you'll learn**:
- Running independent tasks simultaneously
- 4x speedup vs. sequential
- No-coordination workflows
- Resource utilization

**Use cases**:
- Independent modules
- Microservices development
- Parallel data processing
- Content creation at scale

**→ [View Example 2](2-parallel-tasks/README.md)**

---

### 3. Code Review Pipeline

**Pattern**: A → B → A → B (Iterative refinement)

```
Write → Review → Fix → Approve
```

**What you'll learn**:
- Feedback loops between agents
- Quality gates and standards
- Security review workflows
- Role specialization (developer vs. reviewer)

**Use cases**:
- Security-critical code
- Production code review
- Compliance requirements
- Learning from feedback

**→ [View Example 3](3-code-review-pipeline/README.md)**

---

### 4. Multi-Model Ensemble

**Pattern**: A ‖ B ‖ C ‖ D → Judge (Competitive analysis)

```
Claude ─┐
GPT-4  ─┤
Gemini ─┤→ Judge → Best Solution
Grok   ─┘
```

**What you'll learn**:
- Leveraging different models' strengths
- Objective evaluation criteria
- Hybrid solutions (combining best ideas)
- When to use which model

**Use cases**:
- Critical architectural decisions
- Algorithm selection
- Security design
- Performance optimization

**→ [View Example 4](4-multi-model-ensemble/README.md)**

---

### 5. Data Pipeline

**Pattern**: A → B → C → D → E → F (ETL workflow)

```
Extract → Validate → Transform → Enrich → Load → Verify
```

**What you'll learn**:
- Multi-stage data processing
- Quality gates at each stage
- Error propagation and handling
- Data transformation patterns

**Use cases**:
- ETL pipelines
- Data migration
- Log processing
- Analytics preparation

**→ [View Example 5](5-data-pipeline/README.md)**

---

### 6. Creative Collaboration

**Pattern**: Sequential + Parallel (Creative workflow)

```
World Building → Characters → Plot → Draft → Polish → Edit
```

**What you'll learn**:
- Multi-agent creative work
- Building on each other's ideas
- Creative specialization
- Iterative refinement for art

**Use cases**:
- Fiction writing
- Content marketing
- Game development (quests, lore)
- Documentation

**→ [View Example 6](6-creative-collaboration/README.md)**

---

### 7. Complex Application

**Pattern**: All patterns combined (Production workflow)

```
Phase 1: Foundation (Sequential)
Phase 2: Features (Parallel)
Phase 3: QA (Review Pipeline)
Phase 4: Documentation (Sequential)
```

**What you'll learn**:
- Real-world development workflow
- Combining multiple patterns
- Production-ready practices
- Complete application lifecycle

**Use cases**:
- Full-stack applications
- Microservices
- Internal tools
- SaaS products

**→ [View Example 7](7-complex-application/README.md)**

---

## 🎓 Learning Path

### Beginner Track
1. **Example 1** - Understand Agent Hive basics
2. **Example 2** - See parallel execution
3. **Example 6** - Try creative collaboration (fun!)

**Time**: 2-3 hours
**Outcome**: Understand core concepts

### Intermediate Track
1. **Example 1** - Quick basics
2. **Example 3** - Learn review workflows
3. **Example 5** - Build data pipeline
4. **Example 7** - Complete application

**Time**: 6-8 hours
**Outcome**: Build production-ready projects

### Advanced Track
1. **Example 4** - Multi-model ensemble
2. **Example 7** - Complex application
3. **Extend Example 7** - Add your own features

**Time**: 8-12 hours
**Outcome**: Master Agent Hive patterns

## 🏗️ Pattern Reference

### Sequential Pattern

**When to use**: Tasks have dependencies

```markdown
Phase A: Research
- [ ] Task 1
  ↓ (must complete before Phase B)
Phase B: Implementation
- [ ] Task 2 (depends on Phase A output)
```

**Coordination**: `owner` field + task completion + `dependencies.blocked_by`

**Using Dependencies:** Add explicit dependency tracking in frontmatter:

```yaml
dependencies:
  blocked_by: [research-project]  # Wait for this to complete
  blocks: [deployment-project]    # These wait on us
```

**Examples**: 1, 3, 5, 6, 7

---

### Parallel Pattern

**When to use**: Independent tasks

```markdown
Task A: Build auth module
Task B: Build CRUD module  (all independent)
Task C: Build models
```

**Coordination**: Agent notes, different files

**Examples**: 2, 4, 7 (Phase 2)

---

### Review Pattern

**When to use**: Quality-critical work

```markdown
Write → Review → Fix → Review (loop until approved)
```

**Coordination**: Review findings, iteration count

**Examples**: 3, 7 (Phase 3)

---

### Ensemble Pattern

**When to use**: Critical decisions, want best solution

```markdown
Multiple models solve same problem → Judge selects best
```

**Coordination**: Independent work, then comparison

**Examples**: 4

---

## 🛠️ Running Examples

### Option 1: Manual Deep Work Sessions

```bash
# Generate context for an example
make session PROJECT=examples/1-simple-sequential

# Copy context to your AI interface
# Agent works on tasks, updates AGENCY.md
# Repeat for each agent
```

### Option 2: Find Ready Work (Fast)

```bash
# Find projects ready for work (no LLM, instant)
make ready

# Get JSON output for scripting
make ready-json

# View dependency graph
make deps
```

Ready work detection finds projects that are:
- `status: active`
- `blocked: false`
- `owner: null`
- No incomplete `blocked_by` dependencies

### Option 3: Automated with Cortex

```bash
# Cortex orchestrates agents automatically
uv run python src/cortex.py

# Checks all examples/*/AGENCY.md files
# Assigns agents based on status and owner
# Updates files and commits changes
```

### Option 4: Dashboard

```bash
# Start web UI
make dashboard

# Open http://localhost:8501
# View all examples
# Generate contexts
# Monitor progress
# See dependency graphs
```

### Option 5: MCP Server (AI Agents)

```bash
# Run MCP server for Claude Desktop integration
uv run python -m hive_mcp

# Claude can then use tools like:
# - get_ready_work()
# - claim_project("example-1")
# - add_note("example-1", "agent", "Started work")
```

## 📊 Comparison Matrix

### By Use Case

| Use Case | Recommended Example |
|----------|---------------------|
| Learning Agent Hive | 1, 2 |
| Building APIs | 7 |
| Data processing | 5 |
| Code quality | 3 |
| Creative work | 6 |
| Critical decisions | 4 |
| Team simulation | 2, 7 |

### By Complexity

| Complexity | Examples |
|------------|----------|
| Simple (1-2 agents) | 1 |
| Medium (3-4 agents) | 2, 6 |
| Complex (5-6 agents) | 3, 4, 5 |
| Very Complex (10+ agents) | 7 |

### By Time Investment

| Time Available | Try This |
|----------------|----------|
| 30 minutes | 1 |
| 1 hour | 2 |
| 2 hours | 3 or 6 |
| 4+ hours | 4, 5, or 7 |

### By Pattern Focus

| Pattern to Learn | Example |
|------------------|---------|
| Sequential | 1, 5 |
| Parallel | 2, 4 |
| Iterative | 3 |
| Mixed | 6, 7 |

## 🎨 Customization Ideas

### Modify Existing Examples

**Example 1**: Change to different tech
- Research Rust → Implement in Rust
- Research Go → Implement in Go

**Example 2**: Add more parallel tasks
- 4 tasks → 10 tasks
- Test scalability

**Example 3**: Add more review stages
- Write → Security Review → Code Review → Performance Review

**Example 4**: Try different problems
- UI design choices
- Algorithm selection
- Architecture patterns

**Example 5**: Different data sources
- APIs instead of files
- Real-time streams
- Database migration

**Example 6**: Different creative projects
- Poetry instead of story
- Game quest instead of story
- Marketing copy

**Example 7**: Different application types
- GraphQL API
- WebSocket server
- CLI tool

### Create New Examples

Use patterns from these examples to build:
- **E-commerce site**: Products, cart, checkout
- **Analytics dashboard**: Data ingestion, processing, visualization
- **Chat application**: WebSocket, auth, message storage
- **CI/CD pipeline**: Test, build, deploy, monitor
- **Game**: Mechanics, art, sound, testing

## 🔧 Troubleshooting

### Example won't start

**Issue**: AGENCY.md has invalid YAML

**Fix**:
```bash
# Validate YAML frontmatter
python -c "import frontmatter; frontmatter.load('examples/1-simple-sequential/AGENCY.md')"
```

### Agents don't coordinate

**Issue**: Not checking `owner` field or task completion

**Fix**: Review "Workflow Protocol" section in AGENCY.md

### Too many agents needed

**Issue**: Don't have access to multiple AI sessions

**Fix**:
- Use same agent for multiple phases
- Run sequentially instead of parallel
- Simulate agents by switching contexts

### Example takes too long

**Issue**: Underestimated time commitment

**Fix**:
- Start with Example 1 or 2 (simpler)
- Use faster models (Haiku 4.5)
- Reduce scope (fewer tasks)

## 📈 Success Metrics

Track your learning:

```markdown
## My Progress
- Examples completed: ?/7
- Patterns mastered: Sequential ✓, Parallel ?, Review ?, Ensemble ?
- Applications built: ?
- Lines of code generated: ?
- Agents coordinated: ?
- Most valuable learning: ?
```

## 🤝 Contributing

Want to add your own example?

1. **Create directory**: `examples/8-your-example/`
2. **Add AGENCY.md**: Define project, tasks, workflow
3. **Add README.md**: Explain pattern, use case, instructions
4. **Test it**: Run through the workflow
5. **Submit PR**: Share with community!

**Good example ideas**:
- Real-world applications you've built
- Unique coordination patterns
- Industry-specific workflows
- Creative use cases

## 📚 Additional Resources

- **Main README**: [../README.md](../README.md) - Agent Hive overview
- **CLAUDE.md**: [../CLAUDE.md](../CLAUDE.md) - Development guide
- **Dashboard**: `make dashboard` - Visual interface
- **OpenRouter**: [openrouter.ai](https://openrouter.ai/) - Multi-model API

## 🎯 Next Steps

1. **Pick an example** based on your goal
2. **Read its README** to understand the pattern
3. **Follow the instructions** step by step
4. **Experiment and modify** to make it your own
5. **Build something real** using these patterns

---

**Happy orchestrating!** 🐝

Remember: Agent Hive is about **coordination, not control**. Let agents work transparently, update shared memory, and achieve more together than any single agent could alone.
