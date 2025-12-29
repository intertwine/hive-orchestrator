# @agent-hive/opencode-plugin

OpenCode plugin for deep integration with Agent Hive's orchestration system.

## Overview

This plugin provides automated enforcement and lifecycle integration for OpenCode agents working with Agent Hive projects. It goes beyond the Skills + MCP approach by adding:

- 🔍 **Automated project discovery** - Find ready work on session start
- 🔒 **Ownership enforcement** - Prevent conflicts with automatic claiming
- 📝 **Context injection** - Load project details automatically
- 📊 **Action tracking** - Log all modifications to Agent Notes
- 🤝 **Handoff protocol** - Ensure clean transitions between sessions

## Installation

```bash
npm install @agent-hive/opencode-plugin
```

## Configuration

Add to your `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugins": [
    ["@agent-hive/opencode-plugin", {
      "basePath": ".",
      "autoClaimOnEdit": true,
      "enforceOwnership": false,
      "injectContext": true,
      "logActions": true,
      "agentName": "opencode-claude"
    }]
  ]
}
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `basePath` | `string` | `process.cwd()` | Path to hive root directory |
| `autoClaimOnEdit` | `boolean` | `true` | Automatically claim projects when editing files |
| `enforceOwnership` | `boolean` | `false` | Block edits if project not owned (strict mode) |
| `injectContext` | `boolean` | `true` | Inject AGENCY.md context on session start |
| `logActions` | `boolean` | `true` | Log actions to Agent Notes section |
| `coordinatorUrl` | `string` | `""` | Optional coordinator server URL |
| `agentName` | `string` | `"opencode-agent"` | Agent identifier for ownership |

## Features

### Session Start Hook

When you start an OpenCode session, the plugin:

1. Discovers all projects in the hive
2. Identifies ready work (unblocked, unclaimed projects)
3. Displays available projects with priority indicators
4. Shows any projects you currently own

```
🐝 Agent Hive: 3 project(s) ready for work:

   🔴 critical-bug (critical)
   🟠 new-feature (high)
   🟡 documentation (medium)

🔒 You currently own: my-current-project
```

### Automatic Project Claiming

When `autoClaimOnEdit: true` (default), the plugin automatically claims projects when you edit files within them:

```
🐝 Auto-claimed project: new-feature
```

### Ownership Enforcement

When `enforceOwnership: true`, the plugin blocks file edits in projects you don't own:

```
🚫 Cannot edit files in project "new-feature" - not claimed.
Use: claim_project("new-feature", "your-agent-name")
```

### Context Injection

When a project is mentioned in your message, the plugin injects its AGENCY.md content:

```
User: "Work on the authentication feature"

[Plugin injects AGENCY.md for authentication project]
```

### Action Logging

All significant actions are logged to the project's Agent Notes:

```markdown
## Agent Notes
- **2025-01-15 10:30 - opencode-claude**: Modified src/auth.ts
- **2025-01-15 10:45 - opencode-claude**: Created tests/auth.test.ts
```

### Session End Hook

When ending a session, the plugin reminds you about the handoff protocol:

```
🐝 Agent Hive Handoff Protocol:

   Project: new-feature
   - Update last_updated timestamp
   - Mark completed tasks with [x]
   - Add closing notes
   - Release ownership (owner: null) or keep if continuing
```

## Usage with MCP

The plugin works alongside the Hive MCP server. Use MCP tools for explicit operations:

```typescript
// MCP tools still available
await claim_project("project-id", "agent-name")
await release_project("project-id")
await get_ready_work()
```

## Development Status

### ✅ Phase 1: Project Setup (Complete)

- [x] Directory structure created
- [x] TypeScript configuration
- [x] Build process setup
- [x] Package.json with dependencies
- [x] Type definitions
- [x] Test scaffolding

### 🚧 Phase 2: Core Services (Planned)

- [ ] AGENCY.md parser implementation
- [ ] Hive client (read/write operations)
- [ ] Ownership management
- [ ] Project context building
- [ ] Unit tests

### 🚧 Phase 3: Hook Implementations (Planned)

- [ ] Session start/end hooks
- [ ] Tool execution hooks (before/after)
- [ ] Chat message hooks
- [ ] Permission request hooks
- [ ] Integration tests

### 🚧 Phase 4: MCP Integration (Planned)

- [ ] Coordinator API client
- [ ] Fallback logic
- [ ] Combined workflows

### 🚧 Phase 5: Polish & Documentation (Planned)

- [ ] Comprehensive examples
- [ ] Migration guide
- [ ] API documentation
- [ ] Publishing workflow

## Contributing

Contributions welcome! Please see the main [Agent Hive repository](https://github.com/intertwine/hive-orchestrator) for contribution guidelines.

## License

MIT License - see LICENSE file for details.

## Resources

- [Agent Hive Documentation](https://github.com/intertwine/hive-orchestrator)
- [OpenCode Documentation](https://opencode.ai/docs)
- [OpenCode Plugin Guide](https://opencode.ai/docs/plugins)
- [MCP Server](https://github.com/intertwine/hive-orchestrator/tree/main/src/hive_mcp)

---

Built with ❤️ by the Agent Hive community.
