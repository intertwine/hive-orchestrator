---
blocked: false
blocking_reason: null
dependencies:
  blocked_by: []
  blocks: []
  parent: null
  related: []
last_updated: '2026-03-08T00:02:24.981460Z'
owner: claude-code
priority: high
project_id: opencode-plugin
relevant_files:
- .opencode/opencode.json
- .opencode/skill/hive-mcp/SKILL.md
- src/hive_mcp/server.py
- README.md
status: active
tags:
- plugin
- opencode
- integration
- typescript
---

# OpenCode Plugin for Agent Hive

> Design note: this project started before the final v2 cutover. Treat the legacy references below to project ownership and direct `AGENCY.md` parsing as historical design material, not current product guidance. New integrations should claim canonical tasks, build startup context through `hive context startup --task ...`, and keep `AGENCY.md` as narrative context rather than machine state.

## Objective

Create a full OpenCode plugin (`@agent-hive/opencode-plugin`) that provides deep integration with Agent Hive's orchestration system. The plugin will hook into OpenCode's execution lifecycle to automate project claiming, enforce the handoff protocol, inject context, and provide a seamless multi-agent coordination experience.

This goes beyond the current Skills + MCP approach by adding automated enforcement and lifecycle integration.

---

## Background

### Current State (Skills + MCP)

Agent Hive already has OpenCode support via:
- **Skills** (`.opencode/skill/`) - Instructions that teach the agent workflows
- **MCP Server** - Tools for project management (claim, release, status, etc.)

This covers ~80% of use cases but requires the agent to manually follow protocols.

### Target State (Full Plugin)

A TypeScript plugin that:
1. **Automates** task discovery and claiming
2. **Enforces** task-claim or policy checks before file edits
3. **Injects** startup context automatically
4. **Tracks** meaningful actions in Hive notes or artifacts
5. **Ensures** clean handoff and projection sync on session end

---

## Technical Specification

### Package Structure

```
packages/opencode-plugin/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts              # Main plugin export
│   ├── hooks/
│   │   ├── session.ts        # Session start/end hooks
│   │   ├── tool.ts           # Tool before/after hooks
│   │   ├── chat.ts           # Message hooks
│   │   └── permission.ts     # Permission request hooks
│   ├── services/
│   │   ├── hive-client.ts    # API client for Hive operations
│   │   ├── project-context.ts # Context injection logic
│   │   └── ownership.ts      # Ownership management
│   ├── utils/
│   │   ├── agency-parser.ts  # Parse AGENCY.md files
│   │   ├── config.ts         # Plugin configuration
│   │   └── logger.ts         # Logging utilities
│   └── types/
│       └── index.ts          # TypeScript type definitions
├── tests/
│   ├── hooks.test.ts
│   ├── services.test.ts
│   └── utils.test.ts
└── README.md
```

### Plugin Interface

```typescript
import type { Plugin } from "@opencode-ai/plugin"

export interface AgentHiveConfig {
  basePath?: string           // Path to hive root (default: cwd)
  autoClaimOnEdit?: boolean   // Auto-claim when editing files (default: true)
  enforceOwnership?: boolean  // Block edits if not owner (default: false)
  injectContext?: boolean     // Inject AGENCY.md on session start (default: true)
  logActions?: boolean        // Log actions to Agent Notes (default: true)
  coordinatorUrl?: string     // Optional coordinator server URL
  agentName?: string          // Agent identifier (default: "opencode-{model}")
}

export const AgentHivePlugin: Plugin<AgentHiveConfig> = async (context, config) => {
  // Plugin implementation
}
```

### Hook Implementations

#### 1. Session Start Hook

```typescript
// hooks/session.ts
export const sessionStartHook = async (context: PluginContext, config: AgentHiveConfig) => {
  // 1. Discover all projects
  const projects = await discoverProjects(config.basePath)

  // 2. Find ready work
  const readyWork = projects.filter(p =>
    p.status === 'active' &&
    !p.blocked &&
    p.owner === null
  )

  // 3. Display ready work to user
  if (readyWork.length > 0) {
    console.log(`\n🐝 Agent Hive: ${readyWork.length} project(s) ready for work:\n`)
    readyWork.forEach(p => {
      const priority =
        p.priority === 'critical' ? '🔴' :
        p.priority === 'high' ? '🟠' :
        p.priority === 'medium' ? '🟡' : '🟢'
      console.log(`   ${priority} ${p.project_id} (${p.priority})`)
    })
    console.log(`\nUse "claim <project>" or ask me to work on one.\n`)
  }

  // 4. Check for already claimed projects
  const claimed = projects.filter(p => p.owner === config.agentName)
  if (claimed.length > 0) {
    console.log(`\n🔒 You currently own: ${claimed.map(p => p.project_id).join(', ')}\n`)
  }
}
```

#### 2. Tool Execute Before Hook

```typescript
// hooks/tool.ts
export const toolExecuteBeforeHook = async (
  input: ToolInput,
  context: PluginContext,
  config: AgentHiveConfig
) => {
  // Only check for file-modifying tools
  const modifyingTools = ['edit', 'write', 'multiEdit', 'notebookEdit']
  if (!modifyingTools.includes(input.tool)) return

  // Find which project this file belongs to
  const project = await findProjectForFile(input.args.filePath, config.basePath)
  if (!project) return // File not in a project

  // Check ownership
  if (project.owner === null) {
    if (config.autoClaimOnEdit) {
      // Auto-claim the project
      await claimProject(project.project_id, config.agentName, config.basePath)
      console.log(`\n🐝 Auto-claimed project: ${project.project_id}\n`)
    } else if (config.enforceOwnership) {
      throw new Error(
        `🚫 Cannot edit files in project "${project.project_id}" - not claimed.\n` +
        `Use: claim_project("${project.project_id}", "${config.agentName}")`
      )
    }
  } else if (project.owner !== config.agentName && config.enforceOwnership) {
    throw new Error(
      `🚫 Project "${project.project_id}" is owned by "${project.owner}".\n` +
      `Wait for them to release it or contact them.`
    )
  }
}
```

#### 3. Tool Execute After Hook

```typescript
// hooks/tool.ts
export const toolExecuteAfterHook = async (
  input: ToolInput,
  output: ToolOutput,
  context: PluginContext,
  config: AgentHiveConfig
) => {
  if (!config.logActions) return

  // Log significant actions to Agent Notes
  const loggableTools = ['edit', 'write', 'bash', 'multiEdit']
  if (!loggableTools.includes(input.tool)) return

  const project = await findProjectForFile(input.args.filePath, config.basePath)
  if (!project || project.owner !== config.agentName) return

  // Add note about the action
  const action =
    input.tool === 'edit' ? 'Modified' :
    input.tool === 'write' ? 'Created' :
    input.tool === 'bash' ? 'Executed command in' : 'Updated'

  const note = `${action} ${input.args.filePath || 'files'}`
  await addAgentNote(project.project_id, config.agentName, note, config.basePath)
}
```

#### 4. Session End Hook

```typescript
// hooks/session.ts
export const sessionEndHook = async (context: PluginContext, config: AgentHiveConfig) => {
  // Find projects we own
  const projects = await discoverProjects(config.basePath)
  const owned = projects.filter(p => p.owner === config.agentName)

  if (owned.length === 0) return

  console.log(`\n🐝 Agent Hive Handoff Protocol:\n`)

  for (const project of owned) {
    console.log(`   Project: ${project.project_id}`)
    console.log(`   - Update last_updated timestamp`)
    console.log(`   - Mark completed tasks with [x]`)
    console.log(`   - Add closing notes`)
    console.log(`   - Release ownership (owner: null) or keep if continuing\n`)
  }

  // Add automatic closing note
  for (const project of owned) {
    await addAgentNote(
      project.project_id,
      config.agentName,
      'Session ended. Review handoff protocol before next session.',
      config.basePath
    )
  }
}
```

#### 5. Chat Message Hook (Context Injection)

```typescript
// hooks/chat.ts
export const chatMessageHook = async (
  message: ChatMessage,
  context: PluginContext,
  config: AgentHiveConfig
) => {
  if (!config.injectContext) return message

  // Only inject on first user message or when project is mentioned
  const projects = await discoverProjects(config.basePath)
  const mentionedProject = projects.find(p =>
    message.content.toLowerCase().includes(p.project_id.toLowerCase())
  )

  if (mentionedProject && mentionedProject.owner === config.agentName) {
    // Inject project context
    const agencyContent = await readAgencyFile(mentionedProject.path)

    return {
      ...message,
      content: message.content + `\n\n---\n**Project Context (${mentionedProject.project_id}):**\n${agencyContent}`
    }
  }

  return message
}
```

### Configuration in opencode.json

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
  ],
  "mcp": {
    "hive": {
      "type": "local",
      "command": ["uv", "run", "python", "-m", "src.hive_mcp"],
      "enabled": true
    }
  }
}
```

---

## Tasks

### Phase 1: Project Setup

- [ ] Create `packages/opencode-plugin/` directory structure
- [ ] Initialize package.json with correct dependencies
- [ ] Configure TypeScript (tsconfig.json)
- [ ] Set up build process (esbuild or tsup)
- [ ] Create base plugin skeleton in `src/index.ts`

### Phase 2: Core Services

- [ ] Implement `agency-parser.ts` - Parse AGENCY.md YAML frontmatter
- [ ] Implement `hive-client.ts` - Read/write project files
- [ ] Implement `ownership.ts` - Claim/release/check ownership
- [ ] Implement `project-context.ts` - Build context strings
- [ ] Implement `config.ts` - Load and validate configuration
- [ ] Add unit tests for all services

### Phase 3: Hook Implementations

- [ ] Implement `session.start` hook - Display ready work
- [ ] Implement `session.end` hook - Handoff reminder
- [ ] Implement `tool.execute.before` hook - Ownership enforcement
- [ ] Implement `tool.execute.after` hook - Action logging
- [ ] Implement `chat.message` hook - Context injection
- [ ] Add integration tests for hooks

### Phase 4: MCP Integration

- [ ] Ensure MCP tools work alongside plugin hooks
- [ ] Add fallback to MCP when plugin operations fail
- [ ] Test combined plugin + MCP workflows
- [ ] Document interaction between plugin and MCP

### Phase 5: Polish & Documentation

- [ ] Write comprehensive README.md for the package
- [ ] Add inline documentation (TSDoc)
- [ ] Create example configurations
- [ ] Write migration guide from Skills-only approach
- [ ] Update main README.md with plugin documentation

### Phase 6: Publishing

- [ ] Set up npm publishing workflow
- [ ] Create GitHub release process
- [ ] Publish to npm as `@agent-hive/opencode-plugin`
- [ ] Update Agent Hive documentation with install instructions
- [ ] Announce in project discussions

---

## Implementation Notes

### Dependencies

```json
{
  "dependencies": {
    "yaml": "^2.3.0",
    "glob": "^10.0.0"
  },
  "peerDependencies": {
    "@opencode-ai/plugin": "^1.0.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "tsup": "^8.0.0",
    "vitest": "^1.0.0",
    "@types/node": "^20.0.0"
  }
}
```

### Key Design Decisions

1. **Non-blocking by default**: `enforceOwnership: false` allows gradual adoption
2. **Auto-claim convenience**: Reduces friction for single-agent workflows
3. **MCP fallback**: Plugin enhances but doesn't replace MCP tools
4. **Graceful degradation**: If plugin fails, OpenCode continues normally
5. **Minimal dependencies**: Only `yaml` and `glob` required

### Testing Strategy

1. **Unit tests**: Test each service in isolation
2. **Integration tests**: Test hook combinations
3. **E2E tests**: Test with actual OpenCode (manual initially)
4. **Snapshot tests**: Verify AGENCY.md modifications

### Error Handling

- All hooks should catch errors and log warnings (not crash)
- Ownership conflicts should be clear and actionable
- Network errors (coordinator) should fall back gracefully
- Parse errors should identify the problematic file

---

## Success Criteria

1. Plugin installs via `npm install @agent-hive/opencode-plugin`
2. Session start shows ready work without configuration
3. File edits auto-claim projects (when enabled)
4. Session end reminds about handoff protocol
5. All actions logged to Agent Notes (when enabled)
6. No performance degradation (hooks complete in <100ms)
7. Works alongside existing MCP tools
8. Zero breaking changes to existing Skills

---

## Resources

- [OpenCode Plugin Docs](https://opencode.ai/docs/plugins/)
- [oh-my-opencode](https://github.com/code-yeongyu/oh-my-opencode) - Reference implementation
- [OpenCode Source](https://github.com/sst/opencode)
- [Agent Hive MCP Server](../src/hive_mcp/server.py)

---

## Agent Notes
- **2025-12-29 07:47 - Agent Dispatcher**: Assigned to Claude Code. Issue: https://github.com/intertwine/hive-orchestrator/issues/71

- **2025-12-29 00:00 - human**: Project created with full specification for OpenCode plugin development. Ready for implementation.

<!-- hive:begin task-rollup -->
## Task Rollup

| ID | Status | Priority | Owner | Title |
|---|---|---:|---|---|
| task_01KKQGXZWZ960PX3AEWFFYT98Q | ready | 1 |  | Add fallback to MCP when plugin operations fail |
| task_01KKQGXZX2K9Y5S9Q0NAK3T7A7 | ready | 1 |  | Add inline documentation (TSDoc) |
| task_01KKQGXZWX4AXX7SJQE3VE0VQ0 | ready | 1 |  | Add integration tests for hooks |
| task_01KKQGXZWPB7QDHW6C2D4924EM | ready | 1 |  | Add unit tests for all services |
| task_01KKQGXZXDR35RC9YPV9M0AKMW | ready | 1 |  | Announce in project discussions |
| task_01KKQGXZWEY7391DWNSYQK5SD1 | ready | 1 |  | Configure TypeScript (tsconfig.json) |
| task_01KKQGXZWCAKVEPSZV0P22QV67 | ready | 1 |  | Create `packages/opencode-plugin/` directory structure |
| task_01KKQGXZWG8FMBTCX2YXGYWE9D | ready | 1 |  | Create base plugin skeleton in `src/index.ts` |
| task_01KKQGXZX53ZFSVXYQ4A6ZQ9EC | ready | 1 |  | Create example configurations |
| task_01KKQGXZX9SSY9V65AZRB16ZVH | ready | 1 |  | Create GitHub release process |
| task_01KKQGXZX1NYYVPSWD2JZFSMD7 | ready | 1 |  | Document interaction between plugin and MCP |
| task_01KKQGXZWYB0ANZPFEVYYBQWQS | ready | 1 |  | Ensure MCP tools work alongside plugin hooks |
| task_01KKQGXZWH52F2K2ANF3ZNAVCF | ready | 1 |  | Implement `agency-parser.ts` - Parse AGENCY.md YAML frontmatter |
| task_01KKQGXZWWRZSCZGPPF7R5ZK6X | ready | 1 |  | Implement `chat.message` hook - Context injection |
| task_01KKQGXZWNPFTT335WX5XWAK13 | ready | 1 |  | Implement `config.ts` - Load and validate configuration |
| task_01KKQGXZWJP5AVV4T91PJS2E97 | ready | 1 |  | Implement `hive-client.ts` - Read/write project files |
| task_01KKQGXZWKG926GC2Q2DXT44CA | ready | 1 |  | Implement `ownership.ts` - Claim/release/check ownership |
| task_01KKQGXZWME5GD01T4KXE3T892 | ready | 1 |  | Implement `project-context.ts` - Build context strings |
| task_01KKQGXZWRYNCNFMBNDQKAMMDK | ready | 1 |  | Implement `session.end` hook - Handoff reminder |
| task_01KKQGXZWQZA21YV74S4ZZVR2J | ready | 1 |  | Implement `session.start` hook - Display ready work |
| task_01KKQGXZWTEPJFXWVHA58PHP38 | ready | 1 |  | Implement `tool.execute.after` hook - Action logging |
| task_01KKQGXZWSE1JQVJR3EARRQEKH | ready | 1 |  | Implement `tool.execute.before` hook - Ownership enforcement |
| task_01KKQGXZWD66WDGB93TJV9FEY4 | ready | 1 |  | Initialize package.json with correct dependencies |
| task_01KKQGXZXA82CR749WAJ875XJH | ready | 1 |  | Publish to npm as `@agent-hive/opencode-plugin` |
| task_01KKQGXZWFQPPP5G89WK2DYSWQ | ready | 1 |  | Set up build process (esbuild or tsup) |
| task_01KKQGXZX8Q9Y06822RZCW05F3 | ready | 1 |  | Set up npm publishing workflow |
| task_01KKQGXZX0CWEYY20F8HDY31NW | ready | 1 |  | Test combined plugin + MCP workflows |
| task_01KKQGXZXBVGP8M7NJ9MQH23B7 | ready | 1 |  | Update Agent Hive documentation with install instructions |
| task_01KKQGXZX7DQNGW0VNZSRMYAVV | ready | 1 |  | Update main README.md with plugin documentation |
| task_01KKQGXZX2201HVWDPRJEP0FCN | ready | 1 |  | Write comprehensive README.md for the package |
| task_01KKQGXZX6MYAD8PE4QGAM3G1K | ready | 1 |  | Write migration guide from Skills-only approach |
<!-- hive:end task-rollup -->

<!-- hive:begin recent-runs -->
## Recent Runs

| Run | Status | Task |
|---|---|---|
| No runs | - | - |
<!-- hive:end recent-runs -->
