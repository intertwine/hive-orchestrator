# Homebrew Packaging

This directory holds the generated Homebrew formula for Agent Hive.

What matters:

- The formula is generated from published PyPI artifacts, not from the local source tree.
- The release workflow updates the tap after PyPI publish succeeds.
- Everyday users should install with `brew tap intertwine/tap && brew install intertwine/tap/agent-hive`.

Local maintainer commands:

```bash
make brew-formula
make release-homebrew HOMEBREW_TAP_DIR=../homebrew-tap
```

For the full release sequence and verification checklist, see [docs/RELEASING.md](/Users/bryanyoung/experiments/hive-orchestrator-v2-distribution/docs/RELEASING.md).
