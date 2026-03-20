# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 2.2.x   | yes       |
| 2.3.x   | yes       |

## Reporting a Vulnerability

Please do not open public issues for security problems.

Use one of these channels instead:

1. [GitHub private vulnerability reporting](https://github.com/intertwine/hive-orchestrator/security/advisories/new)
2. Maintainer email if you already have a private contact path

Include:

- affected commit, tag, or branch
- exact file paths
- reproduction steps
- expected impact
- proof of concept if you have one

We aim to acknowledge reports within 48 hours and provide a status update within 7 days.

## Security Model

Hive is built around a local, file-backed substrate and explicit policy files.

Core assumptions:

- canonical machine state lives under `.hive/`
- `AGENCY.md`, `GLOBAL.md`, and `AGENTS.md` are human-facing projections
- `PROGRAM.md` defines command, path, and evaluator policy
- execution surfaces should be bounded, auditable, and easy to disable

## Hardening Highlights

### Safe parsing

- YAML frontmatter is parsed through safe loaders in `src/security.py`
- path validation rejects traversal outside the configured workspace
- user-provided text is sanitized before it reaches prompts, issue bodies, or generated context

### Command and run policy

- evaluator commands are checked against `PROGRAM.md`
- run lifecycle transitions are validated before acceptance or rejection
- the run engine records artifacts, logs, and evaluator output for review

### Bounded execution

- `hive execute` runs with a timeout and a scrubbed environment
- the Python MVP uses a restricted runner and best-effort network denial
- oversize execute payloads are rejected before execution

### Service and workflow hardening

- coordinator access can require `HIVE_API_KEY`
- GitHub Actions workflows use minimal permissions and secret masking
- release automation supports trusted publishing for PyPI

## Operator Checklist

- never commit secrets
- keep `.env` local and out of version control
- keep `COORDINATOR_HOST` on localhost unless you intentionally expose it
- use `HIVE_REQUIRE_AUTH=true` for any reachable coordinator deployment
- review `PROGRAM.md` before enabling new evaluator commands
- treat imported or legacy markdown as untrusted input

## Security Environment Variables

| Variable | Purpose | Notes |
|----------|---------|-------|
| `HIVE_API_KEY` | Coordinator authentication | Required for non-local coordinator access |
| `HIVE_REQUIRE_AUTH` | Toggle coordinator auth | Keep enabled outside local development |
| `COORDINATOR_HOST` | Coordinator bind host | Prefer `127.0.0.1` unless you need remote access |
| `COORDINATOR_URL` | Optional coordinator client URL | Point agents only at trusted coordinator instances |
| `WANDB_API_KEY` | Optional Weave tracing | Store as a secret; not required for core CLI use |
| `HOMEBREW_TAP_GITHUB_TOKEN` | Homebrew tap publishing | Required only for release automation |

## Security Testing

Run the normal repo gates:

```bash
make check
```

Or run the focused suite:

```bash
uv run pytest tests/test_security.py -v
```

## Scope

This policy covers:

- this repository
- official GitHub Actions workflows
- shipped CLI and adapter surfaces

It does not cover:

- third-party forks
- self-hosted deployments you operate without following the guidance above
- external services you connect on top of Hive

Thanks for helping keep Hive easy to trust.
