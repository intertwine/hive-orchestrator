---
name: hive-mcp
description: Use the Hive MCP server for the thin v2 search and execute tool surface. Use this skill when configuring MCP access to Hive or when an agent needs workspace search and bounded local execution.
---

# Hive MCP Server

The MCP surface is intentionally small — two tools for agent integration:

- `search` — query workspace state
- `execute` — run bounded Python code

Everything durable still goes through the `hive` CLI and the `.hive/` substrate.

## Setup

Example MCP config:

```json
{
  "mcpServers": {
    "hive": {
      "command": "hive-mcp",
      "env": {
        "HIVE_BASE_PATH": "/path/to/workspace"
      }
    }
  }
}
```

`HIVE_BASE_PATH` should point at the workspace you want the server to search and execute against.

If running from a local checkout instead of an installed package, `uv run hive-mcp` is the equivalent launch command.

## Available Tools

### `search`

Search workspace state, API docs, examples, schemas, and project summaries.

Arguments:

- `query` required
- `scopes` optional — filter to specific indexes (api, examples, project, workspace)
- `limit` optional, defaults to `8`

Example:

```json
{
  "name": "search",
  "arguments": {
    "query": "run acceptance",
    "scopes": ["api", "workspace"],
    "limit": 5
  }
}
```

### `execute`

Run bounded local code with a typed Hive client.

Arguments:

- `code` required
- `language` optional, Python only for now
- `profile` optional
- `timeout_seconds` optional

Example:

```json
{
  "name": "execute",
  "arguments": {
    "language": "python",
    "profile": "default",
    "code": "result = hive.task.ready(limit=3)"
  }
}
```

## Important Limits

- `execute` is intentionally bounded and time-limited
- Oversized execute payloads are rejected
- The Python runner is the only supported language today
- This MCP surface is not a substitute for the CLI

## When To Prefer The CLI

Use the CLI for:

- Task creation, updates, claims, and releases
- Run lifecycle actions (start, finish, promote, steer)
- Evaluator configuration and PROGRAM.md management
- Projection sync and cache management
- Campaign and portfolio operations
- Memory observe, reflect, and search
- Migration and workspace bootstrap

Use MCP when an agent needs fast search or a local execution sandbox inside a host application.
