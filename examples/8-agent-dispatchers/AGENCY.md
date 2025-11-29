---
project_id: agent-dispatchers-example
status: active
owner: null
last_updated: '2025-11-29T12:00:00Z'
blocked: false
blocking_reason: null
priority: medium
tags:
- example
- architecture
- extensibility
relevant_files:
- src/agent_dispatcher.py
- src/context_assembler.py
- examples/8-agent-dispatchers/README.md
dependencies:
  blocked_by: []
  blocks: []
  parent: null
  related:
  - demo
---

# Agent Dispatchers Example

## Objective

Demonstrate how Agent Hive's architecture enables building custom agent dispatchers that can route work to different agent platforms (Claude Code, OpenAI Assistants, Slack bots, etc.).

## Key Concepts

This example showcases:

1. **Separation of Concerns** - Work detection vs. context assembly vs. dispatch
2. **Extensibility** - How to build new dispatchers using core components
3. **Routing** - How to route different work types to different agents
4. **Callbacks** - How agents report completion back to the Hive

## Tasks

### Understanding Phase
- [ ] Read the built-in dispatcher: `src/agent_dispatcher.py`
- [ ] Read the context assembler: `src/context_assembler.py`
- [ ] Run the dispatcher in dry-run mode: `uv run python -m src.agent_dispatcher --dry-run`

### Implementation Phase (Choose One)
- [ ] Build a Slack bot dispatcher
- [ ] Build an email notification dispatcher
- [ ] Build a webhook-based dispatcher
- [ ] Build an OpenAI Assistants dispatcher
- [ ] Build a multi-agent router

### Integration Phase
- [ ] Add GitHub Actions workflow for your dispatcher
- [ ] Test end-to-end with a real agent
- [ ] Document your implementation

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                    Your Dispatcher                    │
├──────────────────────────────────────────────────────┤
│                                                      │
│  1. cortex.ready_work()     # Find available work    │
│            │                                         │
│            ▼                                         │
│  2. select_work(projects)   # Choose priority        │
│            │                                         │
│            ▼                                         │
│  3. build_context(project)  # Assemble context       │
│            │                                         │
│            ▼                                         │
│  4. dispatch_to_agent()     # YOUR CUSTOM CODE       │
│            │                                         │
│            ▼                                         │
│  5. claim_project()         # Update AGENCY.md       │
│                                                      │
└──────────────────────────────────────────────────────┘
```

## Example Dispatcher Template

```python
from cortex import Cortex
from context_assembler import build_issue_body, get_next_task

class MyDispatcher:
    def __init__(self, base_path):
        self.cortex = Cortex(base_path)
        self.base_path = base_path

    def run(self):
        # 1. Find ready work
        ready = self.cortex.ready_work()
        if not ready:
            return False

        # 2. Select highest priority
        project = self.select_work(ready)

        # 3. Build context
        context = build_issue_body(project, self.base_path)

        # 4. Dispatch (YOUR CODE HERE)
        success = self.send_to_my_agent(context)

        # 5. Claim project
        if success:
            self.claim_project(project)

        return success
```

## Workflow Protocol

### For Humans Learning This Pattern

1. **Read** the README.md thoroughly
2. **Study** the built-in dispatcher source code
3. **Choose** a target agent platform
4. **Implement** your dispatcher using the template
5. **Test** with dry-run mode first
6. **Deploy** as GitHub Action or webhook

### For AI Agents

If you're an AI agent working on this project:

1. Claim ownership: set `owner` field to your identifier
2. Work through the Understanding Phase tasks
3. Choose one Implementation Phase task
4. Complete the Integration Phase
5. Update this file: mark tasks `[x]`, add notes
6. Release ownership: set `owner: null`

## Agent Notes

_Add timestamped notes here as you work on this project._

**Example:**
- **2025-11-29 12:00 - System**: Created example to demonstrate dispatcher extensibility

## Resources

- Source: `src/agent_dispatcher.py`
- Source: `src/context_assembler.py`
- Article: `articles/08-building-extensible-agent-dispatchers.md`
- Cortex API: `src/cortex.py` - `ready_work()` method

## Success Criteria

- [ ] Understand the dispatcher architecture
- [ ] Successfully run the built-in dispatcher (dry-run)
- [ ] Implement at least one custom dispatcher
- [ ] Test the dispatcher with a real agent
