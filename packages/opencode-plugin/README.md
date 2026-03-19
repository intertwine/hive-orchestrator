# @agent-hive/opencode-plugin

OpenCode plugin for [Agent Hive](https://github.com/intertwine/hive-orchestrator) v2 orchestration.

## What it does

- **Session start** — lists projects with ready tasks so you know what to pick up
- **Tool hooks** — optionally enforces task ownership before file edits
- **Chat hook** — injects task context when you mention a project by name
- **Session end** — reminds you to sync projections before handoff

All substrate operations delegate to the `hive` CLI (`--json`) — no direct file parsing.

## Install

```bash
npm install @agent-hive/opencode-plugin
```

Requires `hive` CLI v2 to be installed and available on `PATH`.

## Usage

```typescript
import { register } from "@agent-hive/opencode-plugin"

export default register({
  agentName: "opencode-claude",
  autoClaimOnEdit: true,
  enforceOwnership: false,
  injectContext: true,
  logActions: true,
})
```

Or in `opencode.json`:

```json
{
  "plugins": [
    ["@agent-hive/opencode-plugin", {
      "agentName": "opencode-claude",
      "autoClaimOnEdit": true
    }]
  ]
}
```

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `basePath` | `string` | `cwd()` | Hive workspace root |
| `autoClaimOnEdit` | `boolean` | `true` | Auto-claim task when editing files |
| `enforceOwnership` | `boolean` | `false` | Block edits without a claim |
| `injectContext` | `boolean` | `true` | Inject task context into chat |
| `logActions` | `boolean` | `true` | Log tool calls to debug output |
| `agentName` | `string` | `opencode-<model>` | Identifier used in claims |
| `coordinatorUrl` | `string` | `""` | Optional coordinator server URL |

## Development

```bash
npm install
npm run build
npm test
```
