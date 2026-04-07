# Hive v2.5 Release Walkthrough

Status: maintainer walkthrough bundle
Last updated: 2026-04-07
Purpose: final walkthrough script and release-cut plan for the eventual `v2.5.0` public release

This document is for maintainers.
Use it to run the final v2.5 walkthrough, decide whether the draft release candidate is accepted, and then stage the
`v2.5.0` release cut intentionally.
Do not tag or publish from this document alone.

## Walkthrough Goal

Show that `main` already satisfies the scoped v2.5 command-center story and that the only remaining work after
walkthrough signoff is release execution:

- the browser-first command center is the primary operator experience
- the desktop shell exists and is truthfully still described as beta
- docs, launch collateral, and packaged search match the merged product
- the eventual `2.4.0` to `2.5.0` bump is a release operation, not unfinished feature work

## Preflight

Run these before the walkthrough:

```bash
make workspace-status
hive doctor --json
make check
make release-check
```

Stop if any of those fail.
The walkthrough assumes `main` is already green and the built artifacts install cleanly.

## Walkthrough Script

1. Confirm release-ledger truth

   Open [docs/V2_5_STATUS.md](./V2_5_STATUS.md) and verify the status line still reads `draft release candidate`, every scoped gate is either `Landed`, `Validated locally`, or `Prepared`, and the only blocker is walkthrough signoff before staging `v2.5.0`.

2. Run the browser-first command-center story

   Follow the browser path in [docs/DEMO_WALKTHROUGH.md](./DEMO_WALKTHROUGH.md).
   In the live UI, explicitly show:

   - Home, Runs, Inbox, Search, Notifications, Activity, and Settings in the v2.5 IA
   - the shared action model across visible controls and the command palette
   - saved views, deep links, and operator-local preferences
   - run-detail compare/explain surfaces, steering history, and review rails

3. Confirm realtime and review ergonomics

   Use the command-center demo to show that inbox state, notifications, and run freshness update without habitual
   full-page refreshes.
   Keep the evidence paths handy:

   - `frontend/console/src/components/ConsoleEventBus.tsx`
   - `frontend/console/src/routes/InboxPage.tsx`
   - `frontend/console/src/routes/RunDetailPage.tsx`
   - `tests/test_console_api.py`

4. Show the desktop beta truthfully

   Follow [docs/DESKTOP_BETA.md](./DESKTOP_BETA.md) and [frontend/console/README.md](../frontend/console/README.md).
   Confirm the walkthrough language stays honest:

   - Tauri shell exists and is dogfoodable
   - tray actions, native notifications, and deep links work
   - the shell is still beta, not GA

5. Prove docs and installed search match the release

   Use the built-artifact environment from `make release-check` or a fresh throwaway install and run:

   ```bash
   hive search "v2.5 draft release candidate" --scope api --limit 5 --json
   hive search "desktop beta" --scope api --limit 5 --json
   hive search "release walkthrough" --scope api --limit 5 --json
   ```

   The results should point at [docs/V2_5_STATUS.md](./V2_5_STATUS.md),
   [docs/V2_5_RELEASE_WALKTHROUGH.md](./V2_5_RELEASE_WALKTHROUGH.md),
   and the post-v2.4 RFC bundle rather than returning empty or checkout-only results.

6. Close the walkthrough with the release decision

   If the walkthrough is accepted, the next action is not more feature work.
   It is the explicit `v2.5.0` staging bump, tag, publish, and public verification sequence below.

## Evidence Map

| Area | Primary evidence |
|---|---|
| Command-center shell, IA, and design system | `frontend/console/src/App.tsx`, `frontend/console/src/components/ConsoleLayout.tsx`, `frontend/console/src/styles.css` |
| Shared actions, command palette, and explanations | `frontend/console/src/components/ConsoleActions.tsx`, `src/hive/console/actions.py`, `src/hive/console/api.py` |
| Preferences, saved views, and operator-local state | `frontend/console/src/preferences.ts`, `frontend/console/src/routes/RunsPage.tsx` |
| Review ergonomics, compare-runs, and explanations | `frontend/console/src/routes/RunDetailPage.tsx`, `tests/test_console_api.py` |
| Search, provenance, and packaged retrieval | `frontend/console/src/routes/SearchPage.tsx`, `src/hive/search.py`, `tests/test_hive_v2.py` |
| Desktop beta | [docs/DESKTOP_BETA.md](./DESKTOP_BETA.md), `frontend/console/src-tauri/tauri.conf.json`, `frontend/console/src/test/desktopShell.test.ts` |
| Launch collateral and walkthrough assets | [README.md](../README.md), [docs/DEMO_WALKTHROUGH.md](./DEMO_WALKTHROUGH.md), `images/launch/` |

## Release-Only Decisions

These items still require human signoff even though implementation is complete:

- release target stays `v2.5.0` unless a new blocker forces an explicit rescope
- desktop shell language stays beta for the public cut
- no further feature work should be folded into the release branch unless the walkthrough finds a real blocker

## Release Cut Plan

If the walkthrough is accepted, stage the `v2.5.0` cut from the released `2.4.0` line like this:

1. Refresh the working tree and rerun the maintainer gates

   ```bash
   make check
   make release-check
   ```

2. Stage the version bump

   ```bash
   make bump-version BUMP=minor
   uv lock
   ```

3. Update the v2.5 ledger so it points at release execution rather than walkthrough prep

   At minimum, revise [docs/V2_5_STATUS.md](./V2_5_STATUS.md) so:

   - `Status:` moves from `draft release candidate` to a release-staging state
   - `Current Read` says the walkthrough passed and tag/publish are now the only blockers
   - `Next Blocker` points at tag, publish, and public verification

4. Commit the staged release prep

   ```bash
   VERSION="$(uv run python - <<'PY'
   import tomllib
   from pathlib import Path

   print(tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]["version"])
   PY
   )"

   git add pyproject.toml src/hive/common.py uv.lock docs/V2_5_STATUS.md
   git commit -m "Stage v${VERSION} release"
   ```

5. Tag and push the release

   ```bash
   git tag "v${VERSION}"
   git push origin main --tags
   ```

6. Watch the tagged automation and verify public install paths

   Follow [docs/RELEASING.md](./RELEASING.md) for:

   - PyPI publish confirmation
   - Homebrew verification and formula update confirmation
   - throwaway `uv tool`, `pip`, `pipx`, and Homebrew install verification
   - installed-package `hive search` proof from a clean environment

## Signoff Checklist

- `main` CI is green on the walkthrough-approved head
- the maintainer walkthrough completed without uncovering a new blocker
- [docs/V2_5_STATUS.md](./V2_5_STATUS.md) still matches the real state
- the release operator is comfortable executing the `v2.5.0` bump, tag, and publish sequence
- tag and publish remain intentionally deferred until that explicit release step begins
