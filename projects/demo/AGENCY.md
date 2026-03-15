---
blocked: false
blocking_reason: null
last_updated: '2025-12-27T12:01:33.982990Z'
owner: claude-code
priority: medium
project_id: demo
relevant_files:
- projects/demo/AGENCY.md
status: active
tags:
- example
- tutorial
---

# Demo Project - Agent Collaboration Example

## Project Context

This is a demonstration project showing how Agent Hive coordinates multiple AI agents using shared memory. The project simulates a simple content creation pipeline where different agents contribute to building a blog post.

## Objective

Create a well-researched blog post about "The Future of AI Agent Orchestration" with the following components:
- Research phase (gather sources)
- Outline phase (structure content)
- Writing phase (draft sections)
- Review phase (polish and finalize)

## Current Phase

**Phase**: Initialization
**Status**: Waiting for agent assignment

## Tasks

### Research Phase
- [ ] Find 5 credible sources about AI agent orchestration
- [ ] Summarize key trends and predictions
- [ ] Identify unique angles or insights

### Outline Phase
- [ ] Create blog post structure (intro, 3-4 main sections, conclusion)
- [ ] Allocate research findings to appropriate sections
- [ ] Define key takeaways for each section

### Writing Phase
- [ ] Write introduction (hook + thesis)
- [ ] Write main sections with supporting evidence
- [ ] Write conclusion with actionable insights
- [ ] Add relevant examples or case studies

### Review Phase
- [ ] Check for clarity and coherence
- [ ] Verify all sources are properly referenced
- [ ] Polish language and tone
- [ ] Final proofread

## Agent Coordination

### Handoff Protocol
When you complete your assigned task(s):
1. Update the task status above (mark completed items with [x])
2. Update the `status` and `last_updated` fields in frontmatter
3. Set `blocked: true` if you're waiting for another agent
4. Add notes in the "Agent Notes" section below

### Agent Notes
- **2025-12-03 08:24 - Agent Dispatcher**: Assigned to Claude Code. Issue: https://github.com/intertwine/hive-orchestrator/issues/25
- **2025-12-01 08:24 - Agent Dispatcher**: Assigned to Claude Code. Issue: https://github.com/intertwine/hive-orchestrator/issues/22
- **2025-11-29 08:23 - Agent Dispatcher**: Assigned to Claude Code. Issue: https://github.com/intertwine/hive-orchestrator/issues/19

**[Timestamp] - [Agent Name]**: Add your notes here when you work on this project.

Example:
- **2025-01-15 14:30 - Claude**: Initialized project structure and created task list.

## Project Files

This project will generate:
- `research_notes.md` - Collected sources and insights
- `outline.md` - Blog post structure
- `draft.md` - First draft of the blog post
- `final.md` - Polished final version

## Success Criteria

- [ ] All phases completed
- [ ] Final blog post is 1200-1500 words
- [ ] At least 5 sources cited
- [ ] Content is original and insightful
- [ ] Ready for publication

## Notes

This demo project illustrates the Agent Hive workflow. In a real scenario:
- Different AI models could handle different phases
- The Cortex would automatically detect blocking and reassign tasks
- The Dashboard would visualize progress in real-time
- Deep Work sessions would use this file as bootstrapping context

<!-- hive:begin task-rollup -->
## Task Rollup

| ID | Status | Priority | Owner | Title |
|---|---|---:|---|---|
| task_01KKQGXZTZ5M0YWW1TM4EA16BX | ready | 2 |  | Add relevant examples or case studies |
| task_01KKQGXZV42GJC64G4JS43XHKB | ready | 2 |  | All phases completed |
| task_01KKQGXZTTYD6BJJH8KV7V4Q5W | ready | 2 |  | Allocate research findings to appropriate sections |
| task_01KKQGXZV6R15NE6MQC5KGCWFY | ready | 2 |  | At least 5 sources cited |
| task_01KKQGXZV01X6JHH023Y333TW2 | ready | 2 |  | Check for clarity and coherence |
| task_01KKQGXZV7ZQRYRR24V1YRA9M2 | ready | 2 |  | Content is original and insightful |
| task_01KKQGXZTSAKTARYB35S51HRT1 | ready | 2 |  | Create blog post structure (intro, 3-4 main sections, conclusion) |
| task_01KKQGXZTVMSQH14SYDM5BS80J | ready | 2 |  | Define key takeaways for each section |
| task_01KKQGXZV5W0CG2QE2P2CK0ZR8 | ready | 2 |  | Final blog post is 1200-1500 words |
| task_01KKQGXZV3Q3Z4GQ3M9A5CZZFW | ready | 2 |  | Final proofread |
| task_01KKQGXZTN0F580PVYBYQC8T0H | ready | 2 |  | Find 5 credible sources about AI agent orchestration |
| task_01KKQGXZTQHPPF6M9DAAZSPPGE | ready | 2 |  | Identify unique angles or insights |
| task_01KKQGXZV22VDFAJ2T5PE68XT1 | ready | 2 |  | Polish language and tone |
| task_01KKQGXZV7CKZ3HS70PEQK99GN | ready | 2 |  | Ready for publication |
| task_01KKQGXZTPGSHZ5EKFWKR98KES | ready | 2 |  | Summarize key trends and predictions |
| task_01KKQGXZV19XJAZFS8DTBF9B35 | ready | 2 |  | Verify all sources are properly referenced |
| task_01KKQGXZTY16XTV99WNVQCBJB4 | ready | 2 |  | Write conclusion with actionable insights |
| task_01KKQGXZTW5FXPZ0NETBF14PCX | ready | 2 |  | Write introduction (hook + thesis) |
| task_01KKQGXZTXBPBMKB44RET43FP9 | ready | 2 |  | Write main sections with supporting evidence |
<!-- hive:end task-rollup -->

<!-- hive:begin recent-runs -->
## Recent Runs

| Run | Status | Task |
|---|---|---|
| No runs | - | - |
<!-- hive:end recent-runs -->
