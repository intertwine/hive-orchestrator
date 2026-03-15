# Releasing Agent Hive

This guide is for maintainers. If you are trying to install or use Hive, start with the public install section in the root [README.md](/README.md).

## Everyday User Path vs. Maintainer Path

Agent Hive has two different audiences:

- Everyday users should be able to install `hive`, run `hive doctor`, create a project, and get to work.
- Maintainers need the release workflow, PyPI setup, Homebrew tap update flow, and post-release checks.

Keep those paths separate. The README should stay focused on installation, onboarding, and daily use. Release mechanics belong here.

## One-Time Release Setup

Before the first public release:

1. Configure this repository as a trusted publisher in PyPI.
2. Set the repository variable `HOMEBREW_TAP_REPO` to your tap repo, for example `intertwine/homebrew-tap`.
3. Set the repository secret `HOMEBREW_TAP_GITHUB_TOKEN` with push access to that tap repo.
4. Confirm the tap already has a `Formula/` directory or can accept one.

The tagged release workflow at [release.yml](/.github/workflows/release.yml) publishes to PyPI first, then regenerates the Homebrew formula from the published artifacts and pushes the tap update.

## Pre-Release Checklist

Run the normal quality gates:

```bash
make check
```

Then run the release smoke checks:

```bash
make release-check
```

That does five things:

1. builds the wheel and sdist
2. runs `twine check` on the artifacts
3. installs the built wheel through `uv tool`
4. installs the same wheel through `pip install`
5. installs the same wheel through `pipx`

If `make release-check` fails, fix that before you tag anything.

## Cut A Release

Bump the version:

```bash
make bump-version BUMP=patch
```

Commit the version change, then tag it:

```bash
git add pyproject.toml uv.lock
git commit -m "Release v0.1.1"
git tag v0.1.1
git push origin main --tags
```

That tag triggers the release workflow.

The release workflow only publishes from `v*` tags. `workflow_dispatch` is still available for retries, but it must run against a tag ref instead of an arbitrary branch.

## Watch The Automation

After pushing the tag:

1. Confirm the PyPI publish job succeeds.
2. Confirm the Homebrew verification job succeeds on macOS.
3. Confirm the Homebrew update job succeeds.
4. Check that the formula commit lands in the configured tap repo.

Useful commands:

```bash
gh run list --workflow release.yml --limit 5
gh run watch
```

## Verify The Public Install Paths

Once the release is live, verify the actual user-facing commands:

```bash
uv tool install --upgrade agent-hive
hive --version

python -m pip install --upgrade agent-hive
hive --version

pipx install --force agent-hive
hive --version

brew tap intertwine/tap
brew install intertwine/tap/agent-hive
hive --version
```

Also check a real first-run flow:

```bash
hive init --json
hive doctor --json
hive project create demo --title "Demo project" --json
```

## Local Maintainer Commands

Generate the Homebrew formula after a version is already on PyPI:

```bash
make brew-formula
```

Run the full local Homebrew release check:

```bash
make brew-release-check HOMEBREW_PACKAGE_VERSION=0.1.0
```

That command only works after the target version is already live on PyPI, because the formula generator resolves published artifacts instead of local files. For a brand-new release, the tagged GitHub workflow is the thing that proves the Homebrew path before it updates the tap.

Copy the generated formula into a local tap checkout:

```bash
make release-homebrew HOMEBREW_TAP_DIR=../homebrew-tap
```

For TestPyPI smoke work:

```bash
make publish-test
```
