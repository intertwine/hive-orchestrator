# Sandbox Doctor

Use `hive sandbox doctor` when you need to understand what sandbox backends Hive can
truthfully use on the current machine.

## Start Here

```bash
hive sandbox doctor --json
hive sandbox doctor podman --json
hive sandbox doctor e2b --json
hive sandbox doctor daytona --json
```

The doctor output is probe data, not marketing copy. It tells you:

- which backend Hive detected
- whether the backend is configured for non-interactive use
- which profile the backend can support
- what is missing when a backend is not ready

From a source checkout, prefer:

```bash
uv run hive sandbox doctor --json
```

That avoids accidentally reading an older globally installed CLI.

## Profiles And What They Mean

- `local-safe`: the stronger local path. Hive prefers rootless Podman first and Docker rootless second.
- `local-fast`: the lighter local wrapper path. Today that is Anthropic Sandbox Runtime (`srt`).
- `hosted-managed`: the managed remote path. Today that is E2B.
- `team-self-hosted`: the self-hosted remote path. Today that is Daytona.
- `experimental`: backend slots Hive can surface honestly without treating them as release-grade.

The important truthfulness rule for operators is simple:

- `local-fast` is weaker than `local-safe`
  `local-fast` wraps a subprocess with a process-level sandbox. `local-safe` is the container-backed path.

## Local Backends

### `local-safe`

Hive currently treats these as `local-safe` backends:

- rootless Podman
- Docker rootless

On Linux, rootless Podman is the default local-safe target. On macOS and Windows, use
`podman machine` and then re-run `hive sandbox doctor podman --json`.

### `local-fast`

Hive currently maps `local-fast` to Anthropic Sandbox Runtime (`srt`, `asandbox`, or
`anthropic-sandbox` on PATH).

This is useful when you want a faster wrapper around a bounded local command, but it is not
the same isolation boundary as `local-safe`.

## Hosted Backends

### E2B

Install the optional extra first if you want Hive to execute through E2B:

```bash
uv tool install --upgrade 'mellona-hive[sandbox-e2b]'
```

Hive looks for one of these non-interactive auth paths:

- `E2B_API_KEY`
- `E2B_ACCESS_TOKEN`

Current v2.3 behavior is intentionally specific:

- execution is ephemeral
- workspace sync is upload-only for the worktree and artifacts directories
- Hive returns stdout, stderr, and exit status, but it does not yet download remote artifact changes
- it supports network modes `deny` and `inherit` only
- allowlists are not wired yet
- session pause/resume is not wired yet and is deferred from the scope-locked v2.3 release bar

## Self-Hosted Backends

### Daytona

Install the optional extra first if you want Hive to execute through Daytona:

```bash
uv tool install --upgrade 'mellona-hive[sandbox-daytona]'
```

Hive currently expects:

- `DAYTONA_API_URL`
- either `DAYTONA_API_KEY`
- or `DAYTONA_JWT_TOKEN` with `DAYTONA_ORGANIZATION_ID`

Current v2.3 behavior is:

- execution is ephemeral
- workspace sync is upload-only for the worktree and artifacts directories
- Hive returns stdout, stderr, and exit status, but it does not yet download remote artifact changes
- sandboxes can be created from `HIVE_DAYTONA_SNAPSHOT` or from an image
- deny-mode CIDR allowlists are supported
- extra read-only mounts are not projected yet

For release validation in a credentialed environment, run the opt-in remote acceptance proofs from
[docs/RELEASING.md](../RELEASING.md).

## Operator Pattern

When a run fails before it really starts, check the doctor output before you assume the worker
harness is broken:

```bash
hive sandbox doctor --json
hive driver doctor --json
```

If `configured` is false, fix the backend credentials, SDK extra, or local runtime first.
If `available` is false, install or enable the backend binary/runtime before you debug Hive itself.
