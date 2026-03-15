# Observability with Weave Tracing

_Hive already gives you local artifacts. Weave is the optional layer that helps when you want richer visibility into model-heavy paths._

---

![Hero: Observability in Practice](images/weave-tracing/img-01_v1.png)
_Good observability makes agent systems less mysterious. You should be able to inspect what ran, what it cost, where it slowed down, and why it failed._

---

## Start With What Hive Already Records

Before you add any external tracing, Hive already gives you a useful baseline:

- `.hive/runs/*` for run artifacts
- `.hive/events/*.jsonl` for append-only events
- canonical task history in `.hive/tasks/*.md`
- generated rollups in `GLOBAL.md` and `AGENCY.md`

That means you can answer a surprising number of questions locally:

- what task was worked on
- which run produced the patch
- whether evaluation passed
- what got accepted or rejected
- what context and notes were left behind

This is worth emphasizing because many agent systems jump straight to remote tracing dashboards before they even have durable local artifacts.

Hive does not.

## Where Weave Fits

Weave is the optional layer for the parts of your system that still involve model calls or adapter behavior you want to inspect in more detail.

Typical examples:

- a dispatcher that summarizes project context before delivery
- a custom evaluator that calls a model
- a memory reflection step
- a harness bridge that uses an LLM to compress or rank context

In those cases, local artifacts tell you what happened. Weave helps you understand how the model call behaved.

## Why Add Weave At All

Because the hard questions are rarely just "did it run."

They are usually:

- why did this take so long
- why did cost spike
- why did the model miss the obvious issue
- why does one harness produce better summaries than another
- why did the same task work yesterday and fail today

Those are observability questions, not just logging questions.

## Enabling Weave

Weave is optional. The core Hive CLI works without it.

When you do want it, set the normal environment variables:

```bash
WANDB_API_KEY=your-key
WEAVE_PROJECT=agent-hive
```

If you need to turn it off:

```bash
WEAVE_DISABLED=true
```

That is the right shape for a launch-ready system:

- no tracing requirement for everyday use
- a clear on-ramp for teams that want it
- graceful degradation when it is off

## What To Trace

Not everything deserves a trace.

The best candidates are the calls that are expensive, failure-prone, or hard to reason about after the fact.

Good choices:

- model-backed summarization
- task-ranking experiments
- memory reflection passes
- evaluator calls that influence run acceptance
- adapter code that reformats or filters context

Bad choices:

- trivial local helpers
- every tiny pure function
- noisy operations you will never inspect

The goal is signal, not trace-shaped clutter.

## The Most Useful Metrics

When you look at traces, start with the boring questions:

### Latency

Which operations are actually slow?

Agent systems often feel "unpredictable" when the real issue is that one hidden call adds 18 seconds to every loop.

### Token and cost usage

If a workflow suddenly gets expensive, traces are one of the fastest ways to see whether the problem is:

- larger prompts
- more retries
- different models
- duplicate calls

### Error rates

Repeated model failures, timeout spikes, or provider instability are much easier to spot when they are visible as a pattern instead of buried in logs.

### Outcome quality

If two adapters both succeed technically but one produces much better context or summaries, traces help you compare the real input and output shape.

## Pair Weave With Run Artifacts

The strongest debugging loop in Hive is not "use Weave instead of local artifacts."

It is:

- inspect the run artifacts
- inspect the event trail
- inspect the relevant trace

That combination usually tells a much fuller story:

- the run artifact tells you what the system accepted
- the event trail tells you when state changed
- the trace tells you what the model-heavy step actually did

This layered view is much better than relying on a single logging system to do every job.

## A Simple Mental Model

Use local Hive artifacts for:

- ground truth
- reviews
- reproduction
- auditability

Use Weave for:

- latency analysis
- cost analysis
- prompt and response inspection
- adapter debugging

That division keeps observability practical.

## Security And Tracing

Tracing is useful, but it is also a data surface.

That means you should be deliberate:

- avoid sending secrets
- sanitize headers and tokens
- trace only what you are prepared to store
- review what leaves the machine

This is one reason Hive's default posture is optional tracing rather than mandatory remote telemetry.

## Where Teams Usually Get Value First

The first useful Weave deployment is rarely "trace the whole platform."

It is usually one of these:

1. trace a model-backed dispatcher or summarizer
2. trace a memory reflection path
3. trace evaluator calls that decide whether runs are accepted

That is enough to start learning where the system is expensive or brittle.

## Bottom Line

Hive gives you durable local observability by default.
Weave gives you richer visibility when your workflows include model-heavy steps that need inspection.

That is the right order.

You want a system that is understandable even without remote tracing, and more diagnosable when you choose to turn tracing on.

Hive plus Weave gets you there without making basic use depend on a cloud dashboard.
