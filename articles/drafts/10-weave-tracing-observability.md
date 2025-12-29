# Observability with Weave Tracing

_How to monitor, debug, and gain visibility into Agent Hive's LLM operations._

---

![Hero: The Observability Dashboard](images/weave-tracing/img-01_v1.png)
_Complete visibility: Weave tracing shows every LLM call, its latency, token usage, and success status. No more black-box AI operations._

---

## Introduction

When orchestrating multiple AI agents, visibility into what's happening is crucial. How long do LLM calls take? How many tokens are being used? Which calls are failing and why? Agent Hive integrates with [Weights & Biases Weave](https://docs.wandb.ai/weave) to provide comprehensive observability for all LLM operations.

## What is Weave?

Weave is W&B's toolkit for tracking and evaluating LLM applications. Unlike traditional logging, Weave provides:

- **Automatic tracing** of LLM calls with latency and token metrics
- **Cost tracking** across different models
- **Call hierarchies** showing nested operations
- **Comparison tools** for debugging and optimization
- **Dataset management** for evaluation

## Quick Start

### 1. Get a W&B API Key

Sign up at [wandb.ai](https://wandb.ai) and get your API key from settings.

### 2. Configure Environment

```bash
# Add to .env
WANDB_API_KEY=your-wandb-api-key
WEAVE_PROJECT=agent-hive        # Optional, defaults to "agent-hive"
```

### 3. Run Agent Hive

Tracing is automatic - just run Cortex or any component:

```bash
make cortex
# ✓ Weave tracing initialized (project: agent-hive)
```

### 4. View Traces

Open your project at `https://wandb.ai/<your-username>/agent-hive/weave`

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    Agent Hive Components                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│    Cortex ──────┐                                           │
│                 │                                            │
│    Dashboard ───┼──▶ traced_llm_call() ──▶ OpenRouter API   │
│                 │           │                                │
│    Dispatcher ──┘           │                                │
│                             ▼                                │
│                      ┌─────────────┐                        │
│                      │   Weave     │                        │
│                      │  (tracing)  │                        │
│                      └──────┬──────┘                        │
│                             │                                │
└─────────────────────────────┼───────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   W&B Cloud     │
                    │ (visualization) │
                    └─────────────────┘
```

![Tracing Architecture Flow](images/weave-tracing/img-02_v1.png)
_Tracing architecture: All LLM calls flow through traced_llm_call(), which captures metrics and sends them to Weave for analysis._

## Using the Tracing Module

### Initialization

Initialize tracing at application startup:

```python
from src.tracing import init_tracing, is_tracing_enabled

# Check if tracing is available
if is_tracing_enabled():
    init_tracing()  # Returns True if successful
```

### Making Traced LLM Calls

Use `traced_llm_call()` for all LLM API calls:

```python
from src.tracing import traced_llm_call

result = traced_llm_call(
    api_url="https://openrouter.ai/api/v1/chat/completions",
    headers={"Authorization": f"Bearer {api_key}"},
    payload={
        "model": "anthropic/claude-haiku-4.5",
        "messages": [{"role": "user", "content": "Hello!"}]
    },
    model="anthropic/claude-haiku-4.5",
    timeout=60
)

# Access the response
response = result["response"]
print(response["choices"][0]["message"]["content"])

# Access metadata
metadata = result["metadata"]
print(f"Latency: {metadata.latency_ms}ms")
print(f"Tokens: {metadata.total_tokens}")
print(f"Success: {metadata.success}")
```

### The LLMCallMetadata Class

Every traced call returns rich metadata:

```python
@dataclass
class LLMCallMetadata:
    model: str              # Model identifier
    api_url: str            # API endpoint
    prompt_tokens: int      # Input tokens
    completion_tokens: int  # Output tokens
    total_tokens: int       # Total tokens
    latency_ms: float       # Call latency in milliseconds
    success: bool           # Whether the call succeeded
    error: str              # Error message if failed
    timestamp: str          # ISO timestamp
```

![LLMCallMetadata Visualization](images/weave-tracing/img-03_v1.png)
_Rich metadata for every call: Model, latency, token counts, success status, and timestamps - all captured automatically._

### Custom Operation Tracing

Trace your own functions with the `@trace_op` decorator:

```python
from src.tracing import trace_op

@trace_op("process_project")
def process_project(project_id: str) -> dict:
    # Your code here
    return {"status": "processed"}
```

This creates a trace entry for each invocation with:

- Function name
- Arguments
- Return value
- Duration
- Success/failure status

### Checking Tracing Status

```python
from src.tracing import get_tracing_status, print_tracing_status

# Get status as dict
status = get_tracing_status()
print(status)
# {
#     'weave_available': True,
#     'tracing_enabled': True,
#     'tracing_initialized': True,
#     'project': 'agent-hive',
#     'disabled_by_env': False
# }

# Print formatted status
print_tracing_status()
# ========================================
# WEAVE TRACING STATUS
# ========================================
#   Weave Available: True
#   Tracing Enabled: True
#   Initialized:     True
#   Project:         agent-hive
#   Disabled by Env: False
# ========================================
```

## Security: Automatic Header Sanitization

Agent Hive automatically redacts sensitive headers in traces:

```python
# Your actual headers
headers = {
    "Authorization": "Bearer sk-or-v1-actual-api-key",
    "Content-Type": "application/json"
}

# What gets logged to Weave
{
    "Authorization": "***REDACTED***",
    "Content-Type": "application/json"
}
```

This prevents API keys from appearing in your traces while still providing full visibility into request/response data.

![Automatic Header Sanitization](images/weave-tracing/img-04_v1.png)
_Security by default: API keys and sensitive headers are automatically redacted before being sent to Weave traces._

## Graceful Degradation

Tracing is designed to never break your application:

### When Weave is Not Installed

```python
# Works fine - just no tracing
result = traced_llm_call(...)
```

### When WANDB_API_KEY is Not Set

```python
# Works fine - just no remote logging
result = traced_llm_call(...)
```

### When WEAVE_DISABLED=true

```bash
WEAVE_DISABLED=true make cortex
# Cortex runs normally, no tracing
```

### When Weave Fails to Initialize

```python
init_tracing()  # Returns False, prints warning
# ⚠ Could not initialize Weave tracing: <error>

# Subsequent calls work normally
result = traced_llm_call(...)  # No tracing, but works
```

![Graceful Degradation](images/weave-tracing/img-05_v1.png)
_Graceful degradation: If Weave isn't available, isn't configured, or fails to initialize, Agent Hive continues working normally._

## Viewing Traces in W&B

### The Traces View

Navigate to your project's Weave tab to see:

1. **Call List**: All traced operations with timestamps
2. **Latency Distribution**: Histogram of call times
3. **Token Usage**: Prompt vs. completion tokens
4. **Error Rate**: Percentage of failed calls

### Filtering Traces

Filter by:

- Time range
- Operation name (e.g., `llm_call`, `cortex_run`)
- Success/failure status
- Model name

### Inspecting a Single Trace

Click on a trace to see:

- Full request payload (with redacted headers)
- Complete response body
- Token breakdown
- Latency timeline
- Error details (if failed)

![Trace Inspection View](images/weave-tracing/img-06_v1.png)
_Drilling into traces: See the full request, response, token breakdown, and timing for any LLM call._

## Common Patterns

### Tracing Cortex Runs

Cortex automatically traces its runs:

```python
@traced_cortex_run
def run(self) -> Dict[str, Any]:
    # The entire run is traced as "cortex_run"
    ...
```

This creates a parent trace containing all child LLM calls.

### Tracing Analysis Prompts

The analysis phase is traced separately:

```python
@traced_analysis
def build_analysis_prompt(self, projects: List[dict]) -> str:
    # Traced as "build_analysis_prompt"
    ...
```

### Custom Metrics

Add custom attributes to traces:

```python
@trace_op("my_operation")
def my_operation():
    result = do_something()
    # Weave captures the return value
    return {
        "status": "success",
        "items_processed": 42,
        "custom_metric": 3.14
    }
```

![Custom Operation Tracing](images/weave-tracing/img-07_v1.png)
_Trace any operation: Use @trace_op to add observability to your own functions, creating hierarchical trace records._

## Debugging with Traces

### Slow LLM Calls

1. Open the Weave dashboard
2. Sort by latency (descending)
3. Click on slow calls to see:
   - Prompt length (tokens)
   - Model used
   - Response time breakdown

### Failed Calls

1. Filter by `success: false`
2. Check error messages
3. Look for patterns (timeouts, rate limits, etc.)

### Token Usage Analysis

1. Group by model
2. Sum total tokens
3. Identify cost-heavy operations

![Debugging with Traces](images/weave-tracing/img-08_v1.png)
_Debug with data: Filter by latency, success status, or model to identify issues. Traces provide the evidence you need._

## Configuration Reference

### Environment Variables

| Variable         | Purpose             | Default                     |
| ---------------- | ------------------- | --------------------------- |
| `WANDB_API_KEY`  | W&B authentication  | Required for remote logging |
| `WEAVE_PROJECT`  | Project name in W&B | `agent-hive`                |
| `WEAVE_DISABLED` | Disable tracing     | `false`                     |

### Disabling Tracing

```bash
# Completely disable tracing
WEAVE_DISABLED=true

# Or unset the API key
unset WANDB_API_KEY
```

## Best Practices

### 1. Always Trace in Production

Tracing helps you:

- Debug issues faster
- Track costs
- Identify optimization opportunities

### 2. Use Meaningful Operation Names

```python
# Good
@trace_op("analyze_project_dependencies")
def analyze_deps(): ...

# Less useful
@trace_op("step_1")
def analyze_deps(): ...
```

### 3. Include Context in Returns

```python
@trace_op("process_project")
def process_project(project_id: str):
    # Include useful context in the return value
    return {
        "project_id": project_id,
        "status": "completed",
        "tasks_processed": 5,
        "duration_ms": 1234
    }
```

### 4. Monitor Error Rates

Set up alerts in W&B when:

- Error rate exceeds threshold
- Latency spikes
- Token usage unexpectedly increases

## Integration with Cortex

Cortex uses tracing automatically:

```python
class Cortex:
    def __init__(self, base_path: Path):
        # Initialize tracing if available
        if is_tracing_enabled():
            init_tracing()

    def run(self) -> Dict[str, Any]:
        # All LLM calls are automatically traced
        result = traced_llm_call(...)
        return result
```

## Troubleshooting

### "Weave not available"

```bash
# Install weave
uv add weave
# Or
pip install weave
```

### "Could not initialize Weave"

Check:

1. `WANDB_API_KEY` is set correctly
2. Network connectivity to wandb.ai
3. API key has correct permissions

### Traces not appearing

1. Check `get_tracing_status()` returns `initialized: True`
2. Wait a few seconds for W&B sync
3. Verify you're looking at the correct project

### High latency from tracing

Weave tracing adds minimal overhead (<1ms per call). If you see issues:

1. Check network latency to W&B
2. Consider batching traces (automatic in Weave)
3. Disable tracing for high-frequency, low-value operations

## Conclusion

Weave tracing provides essential observability for Agent Hive:

- **Visibility**: See every LLM call with full context
- **Security**: Automatic API key redaction
- **Reliability**: Graceful degradation when unavailable
- **Simplicity**: Just set `WANDB_API_KEY` and go

For production deployments, always enable tracing to maintain visibility into your orchestration system's behavior.

---

**Previous**: [Security in Agent Hive](09-agent-hive-security.md) - Security hardening and best practices

**Back to**: [Article Index](README.md)
