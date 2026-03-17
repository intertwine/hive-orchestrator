# Homebrew Packaging

This directory holds the generated Homebrew formula for Agent Hive.

The formula name follows the Mellona package family, so users install `mellona-hive` and then run `hive`.

What matters:

- The formula is generated from published PyPI artifacts, not from the local source tree.
- The release workflow updates the tap after PyPI publish succeeds.
- Everyday users should install with `brew tap intertwine/tap && brew install intertwine/tap/mellona-hive`.

Local maintainer commands:

```bash
make brew-formula
make release-homebrew HOMEBREW_TAP_DIR=../homebrew-tap
```

For the full release sequence and verification checklist, see [docs/RELEASING.md](/docs/RELEASING.md).
