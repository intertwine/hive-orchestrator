# Agent Dispatchers: Extending the Hive

## Overview

This example demonstrates how Agent Hive's architecture enables building **custom agent dispatchers** - components that proactively find ready work and assign it to different agent platforms. The built-in Claude Code dispatcher is just one implementation; the same pattern can be extended to other agents.

## Pattern: Dispatcher → Agent

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Dispatchers                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   GitHub    │    │    Slack    │    │   Custom    │     │
│  │ Issue + @cl │    │ Bot + Cmd   │    │  Webhook    │     │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘     │
│         │                  │                   │            │
│         └────────────┬─────┴───────────────────┘            │
│                      │                                      │
│                      ▼                                      │
│            ┌─────────────────┐                              │
│            │  Ready Work     │                              │
│            │  (Cortex API)   │                              │
│            └────────┬────────┘                              │
│                     │                                       │
│         ┌───────────┼───────────┐                          │
│         │           │           │                          │
│    ┌────▼────┐ ┌────▼────┐ ┌────▼────┐                    │
│    │Project A│ │Project B│ │Project C│                    │
│    │AGENCY.md│ │AGENCY.md│ │AGENCY.md│                    │
│    └─────────┘ └─────────┘ └─────────┘                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Key Concept: Separation of Concerns

Agent Hive's architecture separates three concerns:

1. **Work Detection** - Cortex identifies ready work (no LLM needed)
2. **Context Assembly** - Build rich context for the agent
3. **Agent Dispatch** - Deliver work to the agent via its native interface

This separation means you can swap out the dispatch mechanism while keeping the same work detection and context assembly logic.

## Built-in: Claude Code Dispatcher

The built-in dispatcher (`src/agent_dispatcher.py`) creates GitHub issues with `@claude` mentions:

```python
# How it works:
# 1. Find ready work using Cortex
ready_projects = cortex.ready_work()

# 2. Select highest priority
project = select_work(ready_projects)

# 3. Build context
title = build_issue_title(project_id, next_task)
body = build_issue_body(project, base_path, next_task)

# 4. Create GitHub issue (Claude Code picks it up)
gh issue create --title "$title" --body "$body"

# 5. Claim project
project.metadata["owner"] = "claude-code"
```

## Extension Examples

### Example 1: Slack Bot Dispatcher

Send work to a Slack channel where multiple agents or humans can claim it:

```python
class SlackDispatcher:
    """Dispatch work to a Slack channel."""

    def dispatch(self, project):
        # Build message
        message = self.build_slack_message(project)

        # Post to channel
        self.slack_client.chat_postMessage(
            channel="#agent-work",
            text=f"New work available: {project['project_id']}",
            blocks=message
        )

        # Note: Don't claim yet - let agents claim via reaction
        return True
```

### Example 2: Email Dispatcher

Send work summaries to a mailing list for human review:

```python
class EmailDispatcher:
    """Dispatch work summaries via email."""

    def dispatch(self, project):
        subject = f"[Agent Hive] Ready: {project['project_id']}"
        body = self.build_email_body(project)

        self.send_email(
            to="team@example.com",
            subject=subject,
            body=body
        )
        return True
```

### Example 3: API Webhook Dispatcher

Trigger external systems (CI/CD, task queues, etc.):

```python
class WebhookDispatcher:
    """Dispatch work to external systems via webhook."""

    def dispatch(self, project):
        payload = {
            "project_id": project["project_id"],
            "priority": project["metadata"]["priority"],
            "context": self.build_context(project),
            "callback_url": f"{self.base_url}/callback/{project['project_id']}"
        }

        response = requests.post(
            self.webhook_url,
            json=payload,
            headers={"Authorization": f"Bearer {self.api_key}"}
        )

        if response.ok:
            self.claim_project(project, webhook_id=response.json()["id"])

        return response.ok
```

### Example 4: Multi-Agent Dispatcher

Route different work types to different agents:

```python
class MultiAgentDispatcher:
    """Route work to appropriate agents based on project attributes."""

    AGENT_ROUTING = {
        "research": "gpt-4-researcher",
        "coding": "claude-code",
        "review": "gemini-reviewer",
        "documentation": "haiku-docs",
    }

    def dispatch(self, project):
        # Determine work type from tags
        tags = project["metadata"].get("tags", [])
        work_type = self.classify_work(tags)

        # Route to appropriate agent
        agent = self.AGENT_ROUTING.get(work_type, "claude-code")

        return self.dispatch_to_agent(project, agent)

    def dispatch_to_agent(self, project, agent):
        if agent == "claude-code":
            return self.create_github_issue(project)
        elif agent == "gpt-4-researcher":
            return self.send_to_openai_assistant(project)
        elif agent == "gemini-reviewer":
            return self.send_to_gemini_api(project)
        # ... etc
```

### Example 5: OpenAI Assistants Dispatcher

Dispatch to OpenAI's Assistants API:

```python
class OpenAIAssistantsDispatcher:
    """Dispatch work to OpenAI Assistants."""

    def dispatch(self, project):
        # Create a thread with context
        thread = self.client.beta.threads.create()

        # Add the work context as a message
        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=self.build_context(project)
        )

        # Run the assistant
        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant_id
        )

        # Claim with thread reference
        self.claim_project(project, thread_id=thread.id)
        return True
```

## Building Your Own Dispatcher

### Step 1: Reuse Core Components

```python
from cortex import Cortex
from context_assembler import (
    build_issue_title,
    build_issue_body,
    get_next_task,
)

class MyDispatcher:
    def __init__(self, base_path):
        self.cortex = Cortex(base_path)

    def find_work(self):
        """Find ready work using Cortex."""
        return self.cortex.ready_work()

    def select_work(self, projects):
        """Select highest priority project."""
        # Reuse the priority logic
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return sorted(
            projects,
            key=lambda p: priority_order.get(p["metadata"]["priority"], 2)
        )[0]
```

### Step 2: Implement Your Dispatch Method

```python
class MyDispatcher:
    # ... (step 1 code) ...

    def dispatch(self, project):
        """Dispatch work to your agent."""
        # Build context using shared assembler
        next_task = get_next_task(project["content"])
        title = build_issue_title(project["project_id"], next_task)
        body = build_issue_body(project, self.base_path)

        # YOUR CUSTOM DISPATCH LOGIC HERE
        result = self.send_to_my_agent(title, body)

        # Claim the project
        if result:
            self.claim_project(project)

        return result
```

### Step 3: Handle Completion Callbacks

```python
class MyDispatcher:
    # ... (steps 1-2 code) ...

    def handle_completion(self, project_id, result):
        """Handle agent completion callback."""
        project_path = self.find_project(project_id)

        with open(project_path, "r") as f:
            post = frontmatter.load(f)

        # Update based on result
        if result["success"]:
            # Mark tasks complete
            for task in result["completed_tasks"]:
                post.content = self.mark_task_complete(post.content, task)

            # Add agent notes
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
            note = f"\n- **{timestamp} - {result['agent']}**: {result['summary']}"
            post.content = self.add_note(post.content, note)

        # Release ownership
        post.metadata["owner"] = None
        post.metadata["last_updated"] = datetime.utcnow().isoformat() + "Z"

        with open(project_path, "w") as f:
            f.write(frontmatter.dumps(post))
```

## AGENCY.md Fields for Dispatchers

Dispatchers can use these AGENCY.md fields:

```yaml
---
project_id: my-project
status: active
owner: null                    # Who currently owns (null = available)
priority: high                 # Dispatch order: critical > high > medium > low
blocked: false                 # If true, skip in dispatch
tags: [coding, backend]        # Can be used for routing
relevant_files:                # Files to include in context
  - src/api/routes.py
  - tests/test_api.py
---
```

## Workflow Integration

### GitHub Actions for Scheduled Dispatch

```yaml
# .github/workflows/my-dispatcher.yml
name: My Agent Dispatch

on:
  schedule:
    - cron: '30 */4 * * *'  # Run 30 min after Cortex
  workflow_dispatch:

jobs:
  dispatch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: |
          uv sync
          uv run python -m my_dispatcher
```

### Event-Driven Dispatch

```python
# Trigger dispatch on external events
@app.route("/webhook/new-work", methods=["POST"])
def handle_new_work():
    dispatcher = MyDispatcher(base_path)
    ready = dispatcher.find_work()

    if ready:
        project = dispatcher.select_work(ready)
        dispatcher.dispatch(project)

    return {"status": "ok"}
```

## Why This Architecture?

### 1. Vendor Agnostic

The core primitives (AGENCY.md, Cortex, context assembly) work with any agent. Only the dispatch mechanism needs to change.

### 2. Simple to Extend

Adding a new dispatcher is ~100 lines of code. You don't need to understand the whole system.

### 3. Composable

You can combine dispatchers:
- Route different work to different agents
- Fall back to alternatives if primary agent is busy
- Fan out to multiple agents for ensemble work

### 4. Observable

All state lives in AGENCY.md files. You can see exactly what's been dispatched, to whom, and when.

## Next Steps

1. **Try the built-in dispatcher**: `uv run python -m src.agent_dispatcher --dry-run`
2. **Read the source**: `src/agent_dispatcher.py` and `src/context_assembler.py`
3. **Build your own**: Start from the examples above
4. **Contribute**: PRs for new dispatchers welcome!

## Related

- [Article: Building Extensible Agent Dispatchers](../../articles/08-building-extensible-agent-dispatchers.md)
- [Example 3: Code Review Pipeline](../3-code-review-pipeline/README.md) - Multi-agent handoffs
- [Example 4: Multi-Model Ensemble](../4-multi-model-ensemble/README.md) - Routing to different models

---

**Estimated time**: Varies by implementation
**Difficulty**: Intermediate to Advanced
**Agents required**: At least one target agent platform
