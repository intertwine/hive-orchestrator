# Hive v2.5 Command Center Demo Walkthrough

This is the shortest path to a truthful v2.5 command-center demo.

The demo is browser-first, because that is still the primary supported product path. If you want to
add the desktop beta story, treat it as a short add-on after the browser walkthrough rather than as
the main event.

It still builds on the existing multi-project launch fixture from the older line, so one helper
script keeps its historical `v22` filename. The point of this walkthrough is to show the v2.5
command-center release on top of that stable fixture, not to replace the fixture itself.

If you just want to review the current launch story, start with the checked-in screenshots and clip
under `images/launch/`. You only need the fixture builder when you want to regenerate the demo
locally.

It builds the same north-star operator shape we use in acceptance:

- three projects
- a Pi-managed lane, plus OpenClaw and Hermes attach-oriented lanes
- ten runs across local, Codex, Claude, and manual flows
- a reroute with preserved lineage
- a campaign-generated daily brief
- accepted runs with evaluator evidence and context manifests
- home, inbox, and run detail that feel like one real command center instead of separate tools
- run detail with capability truth, sandbox policy, retrieval trace, steering history, and live attach visibility
- an optional desktop beta epilogue that uses the same frontend and API contract

## 1. Build the demo workspace

Use a throwaway directory outside this repository:

```bash
uv run python scripts/build_v22_demo_workspace.py /tmp/hive-v25-demo --force
```

That writes the fixture manifest to:

```bash
/tmp/hive-v25-demo/.hive/demo/north_star_manifest.json
```

## 2. Serve the command center

In a second terminal:

```bash
uv run hive --path /tmp/hive-v25-demo console serve --host 127.0.0.1 --port 8787
```

Then open:

```text
http://127.0.0.1:8787/console/?workspace=/tmp/hive-v25-demo
```

The browser console will prefill the workspace path from the URL so the demo opens ready to use.

## 3. Regenerate screenshots and the short walkthrough clip

The capture helper lives with the React console package at
`frontend/console/scripts/captureDemoAssets.mjs`:

```bash
cd frontend/console
pnpm install
pnpm exec playwright install chromium
pnpm capture-demo -- \
  --manifest /tmp/hive-v25-demo/.hive/demo/north_star_manifest.json \
  --base-url http://127.0.0.1:8787 \
  --output-dir ../../images/launch
```

That generates:

- `images/launch/console-home.png`
- `images/launch/console-inbox.png`
- `images/launch/console-runs.png`
- `images/launch/console-run-detail.png`
- `images/launch/command-center-demo.webm`

The latest generated assets are checked into this repository, so you can review the exact launch
views without recreating the fixture first.

![Command Center Home](../images/launch/console-home.png)

![Command Center Runs](../images/launch/console-runs.png)

![Command Center Run Detail](../images/launch/console-run-detail.png)

## 4. Optional desktop beta add-on

If you want to show the desktop shell after the browser walkthrough:

```bash
cd frontend/console
pnpm install
pnpm run tauri:dev
```

Use that moment to show only the delta from the browser path:

- tray behavior
- native notifications
- `agent-hive://` deep links

Keep the framing explicit: the desktop shell is the same command center in a thin beta wrapper, not
a separate product line. The browser walkthrough should still carry the main story.

## 5. Suggested live narration

1. Start on Home and show the recommendation, active runs, inbox summary, blockers, and campaign snapshot.
2. Open Inbox and point out that approvals and escalations land in one place, while the adjacent notifications surface keeps lower-stakes signals visible without mutating the inbox.
3. Jump to Runs and show that one operator can monitor the whole portfolio in one board, then open the rerouted showcase run.
4. In run detail, show the capability snapshot, sandbox policy, retrieval inspector, steering history, evaluator evidence, compare/explain surfaces, and diff preview.
5. Close on the idea that Hive is the browser-first command center above the worker harness, with the desktop beta as an optional shell around the same control plane.

## 6. What this proves

This walkthrough is meant to make the launch checklist concrete:

- the operator can monitor multiple projects and runs in one browser-first command center
- steering is typed and visible in the audit trail
- Pi managed truth, OpenClaw attach truth, and Hermes attach truth are visible without opening raw artifacts
- capability truth, sandbox truth, and retrieval explanations are visible without opening raw artifacts
- accepted work can explain why it passed
- campaigns, notifications, and review flows sit inside one coherent control surface
- the desktop beta is additive, not divergent, because it rides the same frontend and API contract
- the same control plane can sit above Codex, Claude, local execution, manual handoffs, and native harnesses
