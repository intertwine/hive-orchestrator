---
blocked: false
blocking_reason: null
last_updated: '2025-12-02T04:06:55.017815Z'
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