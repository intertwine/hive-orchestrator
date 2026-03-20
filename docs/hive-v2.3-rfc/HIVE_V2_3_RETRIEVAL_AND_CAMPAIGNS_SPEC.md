# Agent Hive v2.3 Retrieval and Campaigns Spec

Status: Historical design reference  
Date: 2026-03-17

Current scoped release truth lives in `docs/V2_3_STATUS.md`. This spec is kept as packaged design context even though
the shipped v2.3 line deliberately narrowed parts of the proposed retrieval and campaign depth.

## 1. Purpose

This spec completes the last two product gaps in Hive 2.2:

1. **search/retrieval must become explainable infrastructure**
2. **campaigns must become policy-driven portfolio control**

Both systems must also produce artifacts that v2.3 can mine for backtesting and continual improvement.

## 2. Retrieval architecture

## 2.1 Goals

The retrieval system must:

- work well in a fresh local install
- not require a running external vector database by default
- combine lexical and semantic signals
- understand code/project/task/run/memory provenance
- explain why each result matched
- log enough detail for later tuning

## 2.2 Chosen default local stack

- lexical / metadata store: **SQLite FTS5**
- semantic store: **LanceDB**
- embeddings + rerankers: **FastEmbed**
- graph neighbors: **Hive task/run/project links**

## 2.3 Chosen optional remote stack

- **Qdrant** for team/shared hybrid search

This is optional, not required for a good local user experience.

## 3. Retrieval data model

Index these source families separately.

### 3.1 Source families

- `task` — canonical task markdown under `.hive/tasks/*.md`
- `run_summary` — accepted and rejected run summaries
- `run_transcript` — transcript chunks
- `memory` — observations, reflections, profile, active
- `project_doc` — `AGENCY.md`, `PROGRAM.md`, design docs, onboarding docs
- `skill` — skill instructions and examples
- `code_context` — selected code/document chunks when explicitly indexed
- `brief` — campaign and portfolio briefs

### 3.2 Chunk metadata

Every chunk must carry:

```json
{
  "chunk_id": "chunk_...",
  "source_type": "task",
  "project_id": "proj_...",
  "task_id": "task_..." ,
  "run_id": null,
  "path": ".hive/tasks/task_....md",
  "section": "acceptance_criteria",
  "git_sha": "abc123",
  "accepted": null,
  "created_at": "2026-03-17T12:00:00Z",
  "updated_at": "2026-03-17T12:05:00Z",
  "trust_level": "canonical",
  "hash": "sha256:..."
}
```

`trust_level` values:
- `canonical`
- `derived`
- `observational`
- `provisional`
- `rejected`

## 4. Chunking rules

### 4.1 Tasks
- split by logical sections: title, summary, acceptance, dependencies, notes
- keep chunk size modest and section-aware
- canonical task chunks always outrank projections

### 4.2 Runs
- summary and review chunks separate from raw transcript chunks
- accepted summaries carry a strong prior
- rejected or escalated runs remain searchable but with lower default ranking

### 4.3 Memory
- `profile.md` and `active.md` indexed as high-signal compact docs
- reflections chunked by synthesis section
- raw observations indexed but lower-ranked than reflections/profile when both match

### 4.4 Project docs
- `PROGRAM.md` sections are indexed separately and carry policy priority
- onboarding/guide docs are indexed for operator and agent help

### 4.5 Skills
- index `SKILL.md`, examples, trigger conditions, and deterministic helpers

## 5. Retrieval pipeline

The retrieval pipeline is frozen.

1. classify query intent
2. gather lexical candidates from SQLite FTS5
3. gather dense semantic candidates from LanceDB
4. optionally add sparse candidates when available
5. add graph-neighbor expansions
6. fuse candidate lists
7. rerank fused candidates
8. dedupe by provenance hash
9. apply source-priority and trust rules
10. return explanations and selected context

## 5.1 Query intent classes

- `policy`
- `task`
- `history`
- `memory`
- `how_to`
- `code`
- `brief`
- `mixed`

The intent class changes weighting and allowed source families.

## 5.2 Fusion

Default local fusion:
- SQLite lexical rank
- LanceDB dense rank
- graph-neighbor bonus
- optional recency boost
- optional accepted-run bonus
- optional canonical-source bonus

Use rank fusion, not score averaging.

## 5.3 Reranking

Use FastEmbed-compatible cross-encoder reranking on a limited candidate set.

Default reranker:
- `Xenova/ms-marco-MiniLM-L-6-v2` when available

Rationale:
- lightweight local footprint
- Apache-2.0 license
- sufficient for first-stage productization

Allow config override for heavier or multilingual rerankers, but do not require them for default installs.

## 6. Ranking policy rules

These rules are product behavior, not mere heuristics.

1. canonical task files outrank projections
2. `PROGRAM.md` outranks general docs for policy questions
3. accepted run summaries outrank rejected-run chatter
4. `profile.md` and `active.md` outrank raw observations when both answer the query
5. exact path/ID hits get a meaningful lexical boost
6. duplicate content across projection and canonical sources collapses to one displayed result
7. recent memory gets a recency boost, but not enough to bury durable reflections
8. results from a different project need either explicit query mention or high semantic confidence to outrank in-project results

## 7. Retrieval explanations

Every displayed result must include:
- why it matched
- source type
- trust level
- project/task/run attribution
- freshness
- whether it was included in final context

Example:

```json
{
  "chunk_id": "chunk_123",
  "score": 0.82,
  "why": [
    "semantic match to 'approval policy'",
    "source is PROGRAM.md",
    "same project as active run"
  ],
  "included": true
}
```

## 8. Retrieval traces

Every run must persist retrieval traces.

```json
{
  "query": "how should this run handle network access?",
  "intent": "policy",
  "candidate_counts": {
    "lexical": 12,
    "dense": 20,
    "graph": 5
  },
  "fused": [
    {"chunk_id": "c1", "sources": ["lexical", "dense"], "pre_rerank_rank": 1},
    {"chunk_id": "c2", "sources": ["dense"], "pre_rerank_rank": 2}
  ],
  "reranked": [
    {"chunk_id": "c1", "rank": 1, "score": 0.91},
    {"chunk_id": "c2", "rank": 2, "score": 0.81}
  ],
  "selected_context": ["c1", "c2"],
  "dropped": [
    {"chunk_id": "c7", "reason": "duplicate_provenance"}
  ]
}
```

This is required for v2.3.

## 9. Packaging requirements

The installed package must include:
- operator docs
- harness guides
- examples
- recipes
- RFC/spec corpus needed by `search`

The installed experience must not materially degrade relative to source checkout.

## 10. Campaign model

## 10.1 Campaign types

Freeze these types:

- `delivery`
- `research`
- `maintenance`
- `review`

Each campaign type comes with a default policy template.

## 10.2 Lanes

Every campaign schedules work across four lanes:

- `exploit`
- `explore`
- `review`
- `maintenance`

### Default lane quotas

| Campaign type | exploit | explore | review | maintenance |
|---|---:|---:|---:|---:|
| delivery | 70 | 10 | 20 | 0 |
| research | 40 | 40 | 20 | 0 |
| maintenance | 20 | 0 | 20 | 60 |
| review | 10 | 0 | 80 | 10 |

Quotas are defaults, not hardcoded constants. They can be overridden in campaign policy.

## 10.3 Candidate generation

For each tick/rebalance, Hive builds a candidate pool from:
- ready tasks
- blocked tasks with potential unlock value
- escalations awaiting review
- paused runs eligible for resume
- recurring maintenance work
- brief generation or review obligations

Each candidate is assigned a lane and scored.

## 10.4 Scoring model

Use a transparent weighted model in v2.3.

```text
score =
  campaign_alignment
+ readiness
+ blocker_unlock_value
+ evaluator_pass_probability
+ harness_fit
+ sandbox_fit
+ context_freshness
+ learning_value
- estimated_cost_penalty
- overlap_penalty
- review_backlog_penalty_if_wrong_lane
```

All component scores must be logged.

## 10.5 Required score components

### campaign_alignment
How directly the task advances the campaign objective.

### readiness
Whether prerequisites, worktree state, and policy are ready.

### blocker_unlock_value
Whether completing this candidate unlocks more downstream work.

### evaluator_pass_probability
Estimated chance of satisfying evaluators based on task shape, repo state, and similar past runs.

### harness_fit
How suitable a driver is for the candidate.
Examples:
- Codex stronger for implementation/refactoring
- Claude stronger for synthesis, broad repo search, and narrative handoff
- Pi potentially stronger for minimal scripted agent flows

### sandbox_fit
Whether the chosen sandbox backend satisfies runtime needs with acceptable cost/latency.

### context_freshness
Whether retrieval/memory/context for this area is already warm and coherent.

### learning_value
Whether the run would produce useful information or resolve uncertainty.

### estimated_cost_penalty
Expected token/compute/sandbox cost.

### overlap_penalty
Penalize launching near-duplicate work in parallel.

## 10.6 Decision logging

Every campaign launch decision must be persisted.

```json
{
  "ts": "2026-03-17T15:00:00Z",
  "campaign_id": "camp_123",
  "candidates": [
    {
      "candidate_id": "task_1",
      "lane": "exploit",
      "scores": {
        "campaign_alignment": 0.9,
        "readiness": 1.0,
        "blocker_unlock_value": 0.7,
        "evaluator_pass_probability": 0.8,
        "harness_fit": 0.9,
        "sandbox_fit": 0.8,
        "context_freshness": 0.6,
        "learning_value": 0.3,
        "estimated_cost_penalty": -0.2,
        "overlap_penalty": -0.1
      },
      "total": 5.7,
      "recommended_driver": "codex",
      "recommended_sandbox": "podman"
    }
  ],
  "selected_candidate_id": "task_1",
  "reason": "highest exploit score and unlock value under current campaign quotas"
}
```

## 10.7 Rebalance triggers

A rebalance happens on:
- run completion
- escalation
- approval timeout
- budget threshold crossing
- operator steering event
- scheduled tick
- brief generation

## 10.8 Campaign briefs

Every campaign must be able to generate:
- daily brief
- weekly brief
- launch brief
- review/inbox brief

Briefs must answer:
- what changed
- what is blocked
- what needs attention
- what Hive recommends next
- why that recommendation was made

## 11. Console requirements derived from this spec

The observe console must surface:

### 11.1 Retrieval inspector
- query text
- sources used
- explanations
- selected context
- dropped chunks and why

### 11.2 Campaign inspector
- lane quotas
- active runs by lane
- candidate scores
- chosen candidate
- selected driver/sandbox
- brief history

### 11.3 Operator steering
- move a task into a different lane
- raise/lower campaign exploration level
- force driver preference
- force sandbox preference
- pause/resume a lane
- review queued escalations

## 12. Acceptance metrics

## 12.1 Retrieval quality

A release candidate should show:
- canonical tasks outranking projections on exact task queries
- policy docs outranking general docs on policy queries
- accepted summaries outranking raw transcript snippets on history queries
- fewer duplicate hits than current search
- evidence of improved NDCG / top-k precision on a small benchmark set

## 12.2 Campaign quality

A release candidate should show:
- delivery campaigns biasing toward exploitation
- research campaigns sustaining meaningful exploration
- review backlogs being surfaced quickly
- duplicate parallel work being reduced compared with naive next-task launch

## 13. v2.3 hooks

This spec is intentionally structured so v2.3 can improve:
- reranker choice
- fusion weights
- context selection
- harness routing
- campaign score weights

without changing the artifact contracts.
