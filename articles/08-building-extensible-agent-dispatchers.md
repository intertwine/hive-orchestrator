# Building Extensible Agent Dispatchers

*This is the eighth article in a series exploring Agent Hive and AI agent orchestration.*

---

## The Vision: One Hive, Many Agents

Imagine a development team where work flows automatically to the best agent for each task. Research tasks go to GPT-4 with web browsing. Coding tasks go to Claude Code. Documentation goes to a fine-tuned model that knows your style guide. Review tasks go to a multi-agent ensemble.

This isn't science fiction—it's the natural extension of Agent Hive's architecture.

The key insight is that Agent Hive separates **work management** (finding and organizing tasks) from **work execution** (actually doing the tasks). This separation creates a powerful extension point: the agent dispatcher.

## The Dispatcher Pattern

A dispatcher is a bridge between the Hive and an agent platform. It has three responsibilities:

1. **Find work** - Query Cortex for ready projects
2. **Build context** - Assemble everything the agent needs
3. **Deliver work** - Hand off to the agent in its native format

The built-in Claude Code dispatcher implements this pattern by creating GitHub issues with `@claude` mentions. But the same pattern works for any agent.

```
┌─────────────────────────────────────────────────────────────┐
│                    Dispatcher Architecture                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────┐      ┌─────────────┐      ┌───────────┐  │
│   │   Cortex    │─────▶│   Context   │─────▶│  Deliver  │  │
│   │ ready_work()│      │  Assembly   │      │  to Agent │  │
│   └─────────────┘      └─────────────┘      └───────────┘  │
│                                                             │
│   Find projects        Build rich           GitHub Issue   │
│   that are:            context with:        Slack Message  │
│   - active             - AGENCY.md          API Call       │
│   - unblocked          - File tree          Webhook        │
│   - unowned            - Relevant files     Email          │
│                        - Instructions       Queue Message  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Why Dispatchers Matter

### 1. Vendor Independence

Today you might use Claude Code. Tomorrow you might want to try GPT-4's code interpreter, or a self-hosted model, or a specialized coding agent. With dispatchers, switching agents doesn't require changing your project structure, task definitions, or coordination logic.

### 2. Best-of-Breed Routing

Different agents excel at different tasks:

- **Claude**: Deep reasoning, complex code, nuanced analysis
- **GPT-4**: Web browsing, DALL-E integration, function calling
- **Gemini**: Large context windows, multimodal understanding
- **Specialized models**: Domain-specific tasks, cost optimization

A multi-agent dispatcher can route tasks to the best agent automatically.

### 3. Resilience

If one agent platform is down or rate-limited, a dispatcher can fall back to alternatives. The work doesn't stop just because one service is unavailable.

### 4. Human-in-the-Loop Options

Dispatchers don't have to send work only to AI agents. A Slack dispatcher might post work for human review. An email dispatcher might notify stakeholders. The pattern is the same.

## The Claude Code Dispatcher: A Deep Dive

Let's examine the built-in dispatcher to understand the pattern:

### Finding Work

```python
# The Cortex ready_work() method handles all the complex logic:
# - Is the project active?
# - Is it blocked?
# - Does it have an owner?
# - Are its dependencies satisfied?

ready_projects = self.cortex.ready_work()
```

This is intentionally a black box. Dispatchers don't need to understand blocking rules, dependency graphs, or priority algorithms. They just call `ready_work()` and get a list of actionable projects.

### Selecting Work

```python
# Priority order: critical > high > medium > low
# Tiebreaker: older projects first (by last_updated)

def select_work(self, projects):
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    def sort_key(project):
        priority = project["metadata"].get("priority", "medium")
        last_updated = project["metadata"].get("last_updated", "")
        return (priority_order.get(priority, 2), last_updated)

    return sorted(projects, key=sort_key)[0]
```

This logic could be customized per dispatcher. A cost-sensitive dispatcher might prefer medium-priority tasks for cheaper models. A time-sensitive dispatcher might prioritize recently-updated projects.

### Building Context

```python
# The context assembler creates a rich description for the agent

title = build_issue_title(project_id, next_task)
body = build_issue_body(project, base_path, next_task)
labels = build_issue_labels(project)
```

The issue body includes:
- Project metadata (priority, tags)
- Full AGENCY.md content
- Project file tree
- Relevant file contents (if specified)
- Explicit instructions for the agent
- Success criteria

### Delivering Work

```python
# Create GitHub issue with @claude mention
cmd = ["gh", "issue", "create", "--title", title, "--body", body]
result = subprocess.run(cmd, capture_output=True)
issue_url = result.stdout.strip()
```

Claude Code, installed as a GitHub App, sees the `@claude` mention and starts working on the issue.

### Claiming the Project

```python
# Update AGENCY.md to prevent double-assignment
post.metadata["owner"] = "claude-code"
post.metadata["last_updated"] = datetime.utcnow().isoformat() + "Z"

# Add note linking to the issue
note = f"- **{timestamp} - Agent Dispatcher**: Assigned to Claude Code. Issue: {issue_url}"
```

The `owner` field is the locking mechanism. Other dispatchers (or this one running again) will skip this project until ownership is released.

## Building Your Own Dispatcher

### Step 1: Choose Your Delivery Mechanism

How will your agent receive work?

| Agent Platform | Delivery Mechanism |
|----------------|-------------------|
| Claude Code | GitHub Issue with @claude |
| OpenAI Assistants | API call to create thread |
| Slack Bot | Message to channel |
| Custom Agent | Webhook POST |
| Human Review | Email notification |
| Task Queue | Redis/RabbitMQ message |

### Step 2: Implement the Dispatcher Class

```python
from cortex import Cortex
from context_assembler import build_issue_body, get_next_task

class MyDispatcher:
    AGENT_NAME = "my-custom-agent"

    def __init__(self, base_path, dry_run=False):
        self.base_path = Path(base_path)
        self.dry_run = dry_run
        self.cortex = Cortex(str(self.base_path))

    def validate_environment(self):
        """Check required credentials/connectivity."""
        # TODO: Verify your agent platform is accessible
        return True

    def select_work(self, projects):
        """Select highest priority project."""
        # Reuse or customize the selection logic
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return sorted(
            projects,
            key=lambda p: priority_order.get(p["metadata"]["priority"], 2)
        )[0]

    def build_context(self, project):
        """Build context for your agent."""
        return build_issue_body(project, self.base_path)

    def deliver(self, project, context):
        """Deliver work to your agent."""
        raise NotImplementedError("Implement your delivery mechanism")

    def claim_project(self, project, reference):
        """Mark project as claimed."""
        # Update AGENCY.md with owner and reference
        pass

    def run(self, max_dispatches=1):
        """Main execution loop."""
        if not self.validate_environment():
            return False

        ready = self.cortex.ready_work()
        if not ready:
            print("No work available")
            return False

        dispatched = 0
        for _ in range(max_dispatches):
            project = self.select_work(ready)
            context = self.build_context(project)

            if self.dry_run:
                print(f"Would dispatch: {project['project_id']}")
                dispatched += 1
            else:
                reference = self.deliver(project, context)
                if reference:
                    self.claim_project(project, reference)
                    dispatched += 1

            ready = [p for p in ready if p["path"] != project["path"]]
            if not ready:
                break

        return dispatched > 0
```

### Step 3: Implement Platform-Specific Logic

Here's a concrete example for a Slack dispatcher:

```python
class SlackDispatcher(MyDispatcher):
    AGENT_NAME = "slack-team"

    def __init__(self, base_path, channel, webhook_url, dry_run=False):
        super().__init__(base_path, dry_run)
        self.channel = channel
        self.webhook_url = webhook_url

    def validate_environment(self):
        return bool(self.webhook_url)

    def build_context(self, project):
        """Build Slack-friendly context."""
        meta = project["metadata"]
        next_task = get_next_task(project["content"])

        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"New Work: {meta['project_id']}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Priority:* {meta['priority']}"},
                        {"type": "mrkdwn", "text": f"*Tags:* {', '.join(meta.get('tags', []))}"}
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Next Task:*\n>{next_task}" if next_task else "*Ready for work*"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Claim This Work"},
                            "action_id": f"claim_{meta['project_id']}"
                        }
                    ]
                }
            ]
        }

    def deliver(self, project, context):
        """Post to Slack channel."""
        response = requests.post(
            self.webhook_url,
            json=context,
            headers={"Content-Type": "application/json"}
        )
        if response.ok:
            return f"slack-message-{datetime.utcnow().isoformat()}"
        return None
```

## Multi-Agent Routing

The most powerful pattern is a router that dispatches different work to different agents:

```python
class MultiAgentRouter:
    """Route work to appropriate agents based on project attributes."""

    ROUTING_RULES = [
        # (condition, dispatcher)
        (lambda p: "research" in p["metadata"].get("tags", []), "gpt4-researcher"),
        (lambda p: "review" in p["metadata"].get("tags", []), "gemini-reviewer"),
        (lambda p: "documentation" in p["metadata"].get("tags", []), "haiku-writer"),
        (lambda p: True, "claude-code"),  # Default fallback
    ]

    def __init__(self, base_path):
        self.dispatchers = {
            "claude-code": ClaudeCodeDispatcher(base_path),
            "gpt4-researcher": GPT4Dispatcher(base_path),
            "gemini-reviewer": GeminiDispatcher(base_path),
            "haiku-writer": HaikuDispatcher(base_path),
        }
        self.cortex = Cortex(base_path)

    def route(self, project):
        """Determine which dispatcher to use."""
        for condition, dispatcher_name in self.ROUTING_RULES:
            if condition(project):
                return self.dispatchers[dispatcher_name]
        return self.dispatchers["claude-code"]

    def run(self):
        ready = self.cortex.ready_work()
        for project in ready:
            dispatcher = self.route(project)
            dispatcher.dispatch(project)
```

## Completion Callbacks

When an agent finishes work, how does the Hive know? There are several patterns:

### Pattern 1: Agent Updates AGENCY.md Directly

The cleanest approach—used by Claude Code. The agent is instructed to:
1. Mark tasks complete
2. Add agent notes
3. Set `owner: null`
4. Create a PR

The PR serves as both the work product and the completion signal.

### Pattern 2: Webhook Callback

For agents that can't update git directly:

```python
@app.route("/callback/<project_id>", methods=["POST"])
def handle_completion(project_id):
    data = request.json
    # {
    #   "agent": "gpt4-researcher",
    #   "success": true,
    #   "completed_tasks": ["Research Python logging"],
    #   "summary": "Found 5 best practices for structured logging"
    # }

    update_agency_md(project_id, data)
    return {"status": "ok"}
```

### Pattern 3: Polling

For agents without callback support:

```python
def poll_for_completion(project_id, thread_id):
    while True:
        status = check_agent_status(thread_id)
        if status == "completed":
            result = get_agent_result(thread_id)
            update_agency_md(project_id, result)
            break
        time.sleep(60)
```

## Real-World Architecture

Here's how a production system might look:

```
┌─────────────────────────────────────────────────────────────────┐
│                     GitHub Actions (Scheduled)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐     ┌─────────┐     ┌──────────────────────┐     │
│  │ Cortex  │────▶│ Router  │────▶│    Dispatchers       │     │
│  │ (0:00)  │     │ (0:15)  │     │                      │     │
│  └─────────┘     └─────────┘     │ ┌──────────────────┐ │     │
│                                   │ │ Claude Code      │ │     │
│  Analyze state   Route work      │ │ (GitHub Issues)  │ │     │
│  Update metadata to agents       │ └──────────────────┘ │     │
│                                   │ ┌──────────────────┐ │     │
│                                   │ │ Slack           │ │     │
│                                   │ │ (Team channel)  │ │     │
│                                   │ └──────────────────┘ │     │
│                                   │ ┌──────────────────┐ │     │
│                                   │ │ OpenAI          │ │     │
│                                   │ │ (Assistants)    │ │     │
│                                   │ └──────────────────┘ │     │
│                                   └──────────────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Execution                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Claude Code      Slack Team       OpenAI Assistant             │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐                │
│  │ Sees     │     │ Human    │     │ Runs     │                │
│  │ @claude  │     │ claims   │     │ thread   │                │
│  │ mention  │     │ work     │     │          │                │
│  └────┬─────┘     └────┬─────┘     └────┬─────┘                │
│       │                │                │                       │
│       ▼                ▼                ▼                       │
│  Creates PR       Updates via      Webhook callback             │
│  with changes     Slack bot                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGENCY.md (Source of Truth)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  - Tasks marked complete                                        │
│  - Agent notes added                                            │
│  - Ownership released                                           │
│  - Dependencies unlocked                                        │
│  - Downstream work becomes ready                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Design Principles

When building dispatchers, keep these principles in mind:

### 1. Idempotency

Dispatchers might run multiple times. A well-designed dispatcher should handle this gracefully:
- Check if work is already claimed before dispatching
- Use the `owner` field as a lock
- Handle "already exists" errors gracefully

### 2. Observability

Every dispatch should be traceable:
- Log what was dispatched, when, and to whom
- Include references (issue URLs, thread IDs) in AGENCY.md
- Use consistent agent names in the `owner` field

### 3. Graceful Degradation

What happens if the agent platform is down?
- Validate connectivity before dispatching
- Retry with exponential backoff
- Fall back to alternatives if available
- Don't crash the whole system for one failed dispatch

### 4. Rate Limiting

Don't overwhelm agents or platforms:
- Dispatch one project at a time by default
- Respect API rate limits
- Leave time between dispatches for work to complete

## Conclusion

Agent Hive's dispatcher architecture transforms a simple orchestration system into a flexible agent routing layer. By separating work detection from work delivery, you can:

- Use different agents for different tasks
- Switch agents without changing project structure
- Build resilient multi-agent systems
- Keep humans in the loop when needed

The built-in Claude Code dispatcher is just the beginning. The architecture is ready for whatever agents come next.

---

## Further Reading

- [Example 8: Agent Dispatchers](../examples/8-agent-dispatchers/README.md) - Hands-on examples
- [Source: agent_dispatcher.py](../src/agent_dispatcher.py) - Built-in implementation
- [Source: context_assembler.py](../src/context_assembler.py) - Context building
- [Article 3: Multi-Agent Coordination](03-multi-agent-coordination-without-chaos.md) - Coordination patterns

---

*Next in the series: Coming soon...*
