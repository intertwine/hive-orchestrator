# Releasing Mellona Hive

Mellona is the package family. Agent Hive is the current product. The package you publish is `mellona-hive`, and it
installs the `hive` CLI.

This guide is for maintainers. If you are trying to install or use Hive, start with the public install section in the root [README.md](/README.md).

## Everyday User Path vs. Maintainer Path

Agent Hive has two different audiences:

- Everyday users should be able to install `hive`, run `hive doctor`, create a project, and get to work.
- Maintainers need the release workflow, PyPI setup, Homebrew tap update flow, and post-release checks.

Keep those paths separate. The README should stay focused on installation, onboarding, and daily use. Release mechanics belong here.

## One-Time Release Setup

Before the first public release:

1. Configure this repository as a trusted publisher for `mellona-hive` in PyPI.
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

For the scoped v2.3 release line, do not call the release ready until these additional truthfulness
checks are closed:

1. README, demo walkthrough, compare-harness, and operator docs match the shipped observe-and-steer story.
2. Installed-package `hive search` is proven useful from a throwaway install, not only from a source checkout.

For the active v2.4 implementation line, keep [docs/V2_4_STATUS.md](/docs/V2_4_STATUS.md) aligned with the
planning bundle in [docs/hive-v2.4-rfc/README.md](/docs/hive-v2.4-rfc/README.md) before calling any milestone
ready for broader review.

For the actual v2.3.0 release cut from this repo state, the expected version bump is:

```bash
make bump-version BUMP=minor
uv lock
```

Update [docs/V2_3_STATUS.md](/docs/V2_3_STATUS.md) at the same time so the ledger points at tag-and-publish as the only remaining blocker before you cut the tag.

## Cut A Release

Bump the version:

```bash
make bump-version BUMP=patch
```

Commit the version change, then tag it:

```bash
VERSION="$(uv run python - <<'PY'
import tomllib
from pathlib import Path

print(tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"])
PY
)"

git add pyproject.toml uv.lock
git commit -m "Release v${VERSION}"
git tag "v${VERSION}"
git push origin main --tags
```

That tag triggers the release workflow.

The release workflow only publishes from `v*` tags. `workflow_dispatch` is available for maintainers who need to re-drive an existing tagged release from the current workflow definition.

For example, after fixing PyPI trusted publishing or another release-automation issue, you can rerun the `v2.2.1` release from `main` without uploading duplicate files:

```bash
gh workflow run release.yml --ref main -f release_ref=v2.2.1 -f skip_existing=true
```

That path still builds from the tagged release, but it uses the latest workflow logic and tells PyPI to treat already-uploaded files as a clean no-op.

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

Once the release is live, verify the actual user-facing commands from throwaway directories. Do not run these
checks from your maintainer checkout.

```bash
release_verify_dir=$(mktemp -d)
cd "$release_verify_dir"

uv tool install --upgrade mellona-hive
hive --version
hive doctor
hive --path "$release_verify_dir" sandbox doctor --json

release_python="$(uv python find --no-project 3.11)"
"$release_python" -m venv pip-verify
./pip-verify/bin/python -m pip install --upgrade mellona-hive
./pip-verify/bin/hive --version
./pip-verify/bin/hive doctor --json
./pip-verify/bin/hive --path "$release_verify_dir" sandbox doctor --json

pipx install --force mellona-hive
pipx run --spec mellona-hive hive --version
pipx run --spec mellona-hive hive --path "$release_verify_dir" sandbox doctor --json

brew tap intertwine/tap
brew install intertwine/tap/mellona-hive
hive --version
```

Homebrew verifies the base CLI path. If you also want to smoke-test the observe console or MCP extras, use the `uv tool`,
`pipx`, or `pip` installs above.

Also check a real first-run flow in a clean workspace:

```bash
workspace_dir=$(mktemp -d)
cd "$workspace_dir"

hive onboard demo --prompt "Create a small React website about bees."
hive doctor --json
hive task ready --project-id demo --json
```

For the scoped v2.3 release line, the built-artifact smoke script now proves installed-package
retrieval usefulness automatically for the `uv tool` install lane. If you are verifying manually or
debugging a release candidate, run one API/RFC query and one packaged recipe query without a
source checkout on the `PYTHONPATH`:

```bash
hive search "runtime contract" --scope api --limit 5 --json
hive search "sandbox doctor" --scope examples --limit 5 --json
```

The result should show packaged docs or recipes, not empty results, and the returned hits should
include non-empty explanations. Record that proof before you call the retrieval gate complete.

## Optional Remote Sandbox Release Proofs

When you have real hosted or self-hosted sandbox credentials available, run the opt-in remote
acceptance proofs from a source checkout before you call the v2.3 sandbox story complete.
`make release-check` and the default install smoke scripts do not prove these sandbox extras.

Hosted-managed E2B proof:

```bash
uv run --extra sandbox-e2b pytest tests/test_remote_sandbox_acceptance.py -k e2b -q
```

Set `HIVE_RUN_E2B_ACCEPTANCE=1` and either `E2B_API_KEY` or `E2B_ACCESS_TOKEN` first.
This proves the scope-locked v2.3 hosted path: ephemeral upload-only execution with truthful
stdout/stderr/exit-status return, not pause/resume or downloaded artifact sync.

Team-self-hosted Daytona proof:

```bash
uv run --extra sandbox-daytona pytest tests/test_remote_sandbox_acceptance.py -k daytona -q
```

Set `HIVE_RUN_DAYTONA_ACCEPTANCE=1`, `DAYTONA_API_URL`, and either `DAYTONA_API_KEY` or the
`DAYTONA_JWT_TOKEN` + `DAYTONA_ORGANIZATION_ID` pair first. This proves the current v2.3 Daytona
shape: ephemeral upload-only execution from a snapshot or image with truthful network/mount limits.

## Local Maintainer Commands

Generate the Homebrew formula after a version is already on PyPI:

```bash
make brew-formula
```

Run the full local Homebrew release check:

```bash
make brew-release-check HOMEBREW_PACKAGE_VERSION=2.2.1
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
