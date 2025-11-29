---
Pending tasks - Configure OpenRouter API key: Remove or clarify requirement - this
  appears to be a stale task with no context
last_cortex_run: '2025-11-29T16:01:25.606438Z'
last_updated: '2025-11-29T16:01:25.604986Z'
orchestrator: agent-hive
status: active
version: 1.0.0
---

# Agent Hive - Global Context

## Overview

Agent Hive is a vendor-agnostic agent orchestration operating system. It enables autonomous coordination of AI agents across different models (Claude, Grok, Gemini) using shared memory stored in Markdown files.

## System Architecture

### Core Primitives
- **AGENCY.md**: Project-level shared memory with YAML frontmatter for machine state
- **GLOBAL.md**: Root-level context and system state (this file)
- **Cortex**: Python-based orchestration logic that reads/writes state
- **Dashboard**: Streamlit UI for human oversight and bootstrapping

### Execution Modes
1. **Automated Mode**: GitHub Actions runs Cortex every 4 hours
2. **Deep Work Mode**: Local/cloud sessions via MCP with bootstrapped context
3. **Interactive Mode**: Manual trigger via Dashboard

## Current System State

### Active Projects
- `projects/demo` - Example project demonstrating the Agent Hive pattern

### Blocked Tasks
None currently.

### System Health
- GitHub Actions: Not yet configured
- MCP Server: Available in DevContainer
- Dashboard: Ready to launch

## Context for AI Agents

When you (an AI agent) read this file, you are part of the Agent Hive ecosystem. Your role is to:

1. **Read before acting**: Always check GLOBAL.md and relevant AGENCY.md files
2. **Update state**: Modify AGENCY.md frontmatter to reflect progress
3. **Coordinate**: Respect task ownership and blocking states set by other agents
4. **Bootstrap properly**: Use scripts/start_session.sh for Deep Work sessions

## Tasks

### Pending
- [ ] Configure OpenRouter API key
- [ ] Run initial Cortex cycle
- [ ] Deploy GitHub Actions workflow
- [ ] Create additional projects as needed

### In Progress
None.

### Completed
- [x] Initialize repository structure
- [x] Create core files (GLOBAL.md, AGENCY.md template)
- [x] Set up DevContainer with MCP

## Notes

This is the central nervous system of your agent swarm. All agents—regardless of vendor—should treat this file as the source of truth for system-wide context.