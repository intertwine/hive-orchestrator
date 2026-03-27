---
name: hive-maintainer
description: Discipline for developing Hive itself — PR sizing, review handling, merge discipline, release workflow, delegation, and cleanup hygiene. Use this skill when working on Hive repo changes that span multiple PRs or review cycles.
---

# Hive Maintainer Discipline

Use this skill when you are developing Hive itself, not just using it. It covers the discipline needed for changes that span multiple PRs, subagents, review cycles, or release gates.

## Outcomes

- Keep `main` releasable at all times
- Move work forward in highest-value order
- Use subagents for bounded side lanes only
- Treat Claude review as part of the implementation loop
- Leave a compact restart trail after every merge or pause

## Ground Truth First

Before substantial work:

```bash
make workspace-status
hive doctor --json
```

Classify current work into:
- **Release blockers** — fix these first
- **Mergeable slices** — ship these next
- **Follow-up debt** — track but do not block on

Prefer the smallest slice that removes a real blocker.

## Precedence

When current state, docs, skills, and memory disagree, trust them in this order:

1. Current repo state and test results
2. Current GitHub PR/check state
3. AGENTS.md, CLAUDE.md, and the active project PROGRAM.md
4. Repo-local skills
5. Observational memory and older session summaries

## Default Autonomy Loop

1. Identify the next blocker on the critical path
2. Choose one mergeable slice that attacks it
3. Implement locally if it is blocking or tightly coupled
4. Delegate only bounded side work
5. Run local validation before asking for review
6. Treat review findings as new work, not commentary
7. Merge only when the slice is actually green
8. Record the new head and the next blocker

Do not stall on tiny cleanup once the next real blocker is known.
Do not keep adding unrelated work to an already-mergeable PR.

## PR Sizing

Prefer one subsystem or one risk cluster per PR.

Warning signs that a PR is too large:
- Multiple unrelated review themes
- Difficult-to-summarize purpose
- Repeated "while I'm here" changes
- Reviewer confusion about what is actually blocking

When that happens:
- Merge the safe foundation slice
- Reopen the next slice on top
- Keep the train moving in small reviewed steps

## Merge Discipline

"Literal green" means:
- Local validation passed (`make check`)
- Required GitHub checks passed
- No unresolved must-fix review findings remain
- Any requested Claude review has completed on the latest head, or has been explicitly waived

After merging, watch the `push` CI run on `main`. A red merge commit is new blocking work immediately, even if the PR checks were green.

## Claude Review Discipline

Before requesting review:
- Make the PR single-purpose
- Run the relevant local tests, or `make check` for broad slices
- Post a short summary of what changed and what was validated

After requesting review:
- Treat it as pending until GitHub shows a new Claude comment or review artifact on the latest PR head
- An `eyes` reaction alone is not completion
- If the latest Claude artifact predates the latest commit, the review is still pending
- If Claude never completes, record the missing artifact before asking to waive or retry

When review lands, classify each finding:

| Classification | Action |
|---|---|
| Confirmed bug | Must-fix before merge |
| Missing test / truthfulness gap | Must-fix before merge |
| False alarm disproven by current code | Respond with evidence, non-blocking |
| Valid follow-up but non-blocking | Track as debt, do not block merge |

Rules:
- Confirm findings against the current branch, not memory
- Respond with file paths, test names, and the exact commit that addressed each issue
- Do not merge because a PR is "probably fine"
- Do not ignore Claude because CI is green
- Do not merge while a requested re-review is still pending unless the user explicitly waives it

For a deterministic local fallback: `claude -p "/review <pr-number>"` works well when the GitHub-managed review is delayed.

## Delegation Rules

Delegate when the task is concrete, independent, and non-blocking for your next step.

**Good delegation targets:**
- Audit a subset of merged PRs
- Investigate one suspected bug and return evidence
- Implement a bounded patch with a disjoint file set
- Build focused tests for an already-designed fix

**Keep local ownership for:**
- Contract design
- Integration across multiple lanes
- PR triage and merge decisions
- Any task whose answer is needed before your next move

Every delegated task should include:
- Exact goal
- File ownership or read-only scope
- Required output format
- Reminder that other agents may be editing nearby code

After delegation:
- Do not wait by reflex — work another non-overlapping lane
- Review returned changes before trusting them
- Reconcile findings yourself before merge

## Release Workflow

### Version bump

`make bump-version BUMP=patch|minor|major` updates `pyproject.toml` and `src/hive/common.py` automatically. You must also update manually:

- **`docs/V2_3_STATUS.md`** — bump the `Status:` line, `Last updated:` date, add a row to the Release History table, and rewrite the Next Blocker section.
- **`tests/test_maintainer_surfaces.py`** — the `test_v23_status_doc_tracks_release_gates_and_next_blocker` test asserts the current version string in the status doc. Update the assertion and add one for the new version in the release history.
- **`uv.lock`** — run `uv sync` or `uv lock` after the pyproject.toml bump so the lockfile stays in sync (or let `uv run` do it implicitly).

### Validation

```bash
make check                              # lint + tests (must pass before commit)
make release-check                      # build, validate, smoke-test artifacts
```

### Commit, tag, and push

```bash
git add pyproject.toml src/hive/common.py docs/V2_3_STATUS.md tests/test_maintainer_surfaces.py uv.lock
git commit -m "chore: bump version to X.Y.Z"
git tag vX.Y.Z
git push && git push --tags
```

### Publish to PyPI

`uv publish` does **not** read `~/.pypirc`. Use twine, which does:

```bash
uv build                                # creates dist/mellona_hive-X.Y.Z.*
uv run twine upload dist/mellona_hive-X.Y.Z*   # reads ~/.pypirc [pypi] token
```

Alternatively, pass the token directly: `UV_PUBLISH_TOKEN=pypi-... uv publish`.

The `make publish` target wraps twine but has an interactive confirmation prompt and refuses to run in CI.

### GitHub release

After PyPI publish, create a GitHub release with the built artifacts:

```bash
gh release create vX.Y.Z dist/mellona_hive-X.Y.Z* \
  --title "vX.Y.Z" \
  --notes "release notes here"
```

### Post-release

- Watch the post-push CI run on `main` — a red merge commit is immediate blocking work.
- Verify the new version is installable: `uv tool install 'mellona-hive[console]'` (allow CDN propagation time).
- Keep `docs/V2_3_STATUS.md` current as the compact release ledger.

## Context Protection

After every merge, push, or major handoff, capture:
- Current branch and head
- Latest merged `main` head if relevant
- What is now complete
- What still blocks
- The next highest-value step

Keep this compact enough to survive a long session or context compaction.

## Cleanup Hygiene

Periodically check for:

```bash
git status --short
git worktree list
pgrep -fl "codex_app_server_worker.py|claude_sdk_worker.py|agent_dispatcher|hive "
```

Watch for:
- Orphan worker processes
- Stale temp worktrees
- Untracked `.hive/events/*.jsonl` noise
- Local changes on the wrong branch

Clean generated artifacts promptly so they do not masquerade as intentional work.

## Closeout Checklist

Before you stop or hand off:
- Checkout state matches your verbal summary
- No unpushed local commits (or they are noted)
- Unresolved blockers called out explicitly
- Claude review status stated (pending, clear, or blocking)
- Next step is clear
