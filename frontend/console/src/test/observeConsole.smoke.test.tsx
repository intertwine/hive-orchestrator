import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";

interface MockRoute {
  method?: string;
  pathname: string;
  response: Response | ((url: URL, init?: RequestInit) => Response);
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function makeRun(
  id: string,
  projectId: string,
  driver: string,
  health: string,
  taskTitle: string,
): Record<string, unknown> {
  return {
    id,
    project_id: projectId,
    driver,
    health,
    status: health === "healthy" ? "running" : "waiting_input",
    started_at: "2026-03-17T05:00:00Z",
    metadata_json: { task_title: taskTitle },
  };
}

const MULTI_PROJECT_RUNS = [
  makeRun("run_alpha_local_1", "alpha", "local", "healthy", "Alpha local slice"),
  makeRun("run_alpha_codex_1", "alpha", "codex", "healthy", "Alpha codex slice"),
  makeRun("run_alpha_manual_1", "alpha", "manual", "paused", "Alpha manual handoff"),
  makeRun("run_alpha_claude_1", "alpha", "claude-code", "healthy", "Alpha Claude review"),
  makeRun("run_beta_codex_1", "beta", "codex", "healthy", "Beta codex pass"),
  makeRun("run_beta_local_1", "beta", "local", "blocked", "Beta local unblock"),
  makeRun("run_beta_manual_1", "beta", "manual", "paused", "Beta manual approval"),
  makeRun("run_gamma_local_1", "gamma", "local", "healthy", "Gamma launch page"),
  makeRun("run_gamma_claude_1", "gamma", "claude-code", "failed", "Gamma Claude retry"),
  makeRun("run_gamma_local_2", "gamma", "local", "healthy", "Gamma follow-up polish"),
];

function filterRuns(url: URL): Array<Record<string, unknown>> {
  return MULTI_PROJECT_RUNS.filter((run) => {
    if (url.searchParams.get("project_id") && run.project_id !== url.searchParams.get("project_id")) {
      return false;
    }
    if (url.searchParams.get("driver") && run.driver !== url.searchParams.get("driver")) {
      return false;
    }
    if (url.searchParams.get("health") && run.health !== url.searchParams.get("health")) {
      return false;
    }
    return true;
  });
}

function installFetchMock(routes: MockRoute[]) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(typeof input === "string" ? input : input instanceof URL ? input : input.url);
    const method = (init?.method ?? "GET").toUpperCase();
    const route = routes.find((candidate) => {
      return (candidate.method ?? "GET").toUpperCase() === method && candidate.pathname === url.pathname;
    });
    if (!route) {
      throw new Error(`Unhandled console request: ${method} ${url.pathname}`);
    }
    return typeof route.response === "function" ? route.response(url, init) : route.response.clone();
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderConsole(initialEntries: string[]) {
  window.localStorage.setItem("hive-console-api-base", "http://127.0.0.1:8787");
  window.localStorage.setItem("hive-console-workspace", "/tmp/hive-demo");
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <App />
    </MemoryRouter>,
  );
}

describe("Observe Console smoke", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lets one operator monitor ten runs across three projects with live filters", async () => {
    installFetchMock([
      {
        pathname: "/home",
        response: jsonResponse({
          ok: true,
          home: {
            workspace: "/tmp/hive-demo",
            active_runs: MULTI_PROJECT_RUNS,
            evaluating_runs: [MULTI_PROJECT_RUNS[1], MULTI_PROJECT_RUNS[8]],
            inbox: [
              { kind: "run-review", title: "Alpha review", reason: "Need evaluator signoff" },
              { kind: "run-input", title: "Gamma reroute", reason: "Driver blocked" },
            ],
            blocked_projects: [
              {
                project_id: "beta",
                in_cycle: false,
                blocking_reasons: ["Waiting on dependency graph review."],
              },
            ],
            campaigns: [
              {
                id: "campaign_daily",
                title: "North Star Daily Brief",
                status: "active",
                goal: "Keep the portfolio moving.",
                driver: "local",
                brief_cadence: "daily",
              },
            ],
            recent_events: [
              {
                event_id: "event_1",
                type: "steering.rerouted",
                ts: "2026-03-17T05:30:00Z",
                payload: { message: "Rerouted Gamma to Codex." },
              },
            ],
            recent_accepts: [],
            recommended_next: {
              task: {
                id: "task_alpha_next",
                title: "Investigate inbox routing",
                project_id: "alpha",
              },
              reasons: ["highest priority ready task", "campaign is waiting on this branch"],
            },
          },
        }),
      },
      {
        pathname: "/runs",
        response: (url) => jsonResponse({ ok: true, runs: filterRuns(url) }),
      },
    ]);

    const user = userEvent.setup();
    renderConsole(["/"]);

    await screen.findByRole("heading", { name: "Home" });
    expect(screen.getByText("Investigate inbox routing")).toBeInTheDocument();
    expect(screen.getByText("/tmp/hive-demo")).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Runs" }));

    await screen.findByRole("heading", { name: "Runs" });
    await waitFor(() => {
      expect(screen.getAllByRole("link", { name: /^run_/ })).toHaveLength(10);
    });

    await user.type(screen.getByRole("textbox", { name: "Project" }), "gamma");
    await waitFor(() => {
      expect(screen.getAllByRole("link", { name: /^run_/ })).toHaveLength(3);
    });
    expect(screen.getByRole("link", { name: "run_gamma_local_1" })).toBeInTheDocument();

    await user.clear(screen.getByRole("textbox", { name: "Project" }));
    await user.selectOptions(screen.getByRole("combobox", { name: "Driver" }), "codex");
    await waitFor(() => {
      expect(screen.getAllByRole("link", { name: /^run_/ })).toHaveLength(2);
    });

    await user.selectOptions(screen.getByRole("combobox", { name: "Driver" }), "");
    await user.selectOptions(screen.getByRole("combobox", { name: "Health" }), "paused");
    await waitFor(() => {
      expect(screen.getAllByRole("link", { name: /^run_/ })).toHaveLength(2);
    });
    expect(screen.getByRole("link", { name: "run_alpha_manual_1" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "run_beta_manual_1" })).toBeInTheDocument();
  });

  it("loads project doctor and search routes through the live app shell", async () => {
    installFetchMock([
      {
        pathname: "/projects",
        response: jsonResponse({
          ok: true,
          projects: [
            { id: "alpha", title: "Alpha Control Plane", status: "active", priority: 1, owner: "codex" },
            { id: "beta", title: "Beta Research Ops", status: "blocked", priority: 2, owner: null },
          ],
        }),
      },
      {
        pathname: "/projects/alpha/doctor",
        response: jsonResponse({
          ok: true,
          doctor: {
            status: "blocked_autonomous_promotion",
            issues: [{ code: "missing_required_evaluator", message: "Add at least one evaluator." }],
          },
        }),
      },
      {
        pathname: "/projects/alpha/context",
        response: jsonResponse({
          ok: true,
          project: { id: "alpha" },
          rendered: "Alpha context preview",
          context: {},
        }),
      },
      {
        pathname: "/projects/beta/doctor",
        response: jsonResponse({
          ok: true,
          doctor: {
            status: "healthy",
            issues: [],
          },
        }),
      },
      {
        pathname: "/projects/beta/context",
        response: jsonResponse({
          ok: true,
          project: { id: "beta" },
          rendered: "Beta context preview",
          context: {},
        }),
      },
      {
        pathname: "/search",
        response: jsonResponse({
          ok: true,
          results: [
            {
              kind: "task",
              title: "Program Doctor hardening",
              summary: "Tighten evaluator guardrails.",
              why: ["canonical task record", "matched title terms: program, doctor"],
            },
          ],
        }),
      },
    ]);

    const user = userEvent.setup();
    renderConsole(["/projects"]);

    await screen.findByRole("heading", { name: "Projects" });
    expect(
      await screen.findByText("missing_required_evaluator: Add at least one evaluator."),
    ).toBeInTheDocument();
    expect(await screen.findByText("Alpha context preview")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Beta Research Ops/i }));
    await waitFor(() => {
      expect(screen.getByText("Beta context preview")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("link", { name: "Search" }));
    await screen.findByRole("heading", { name: "Search" });
    await user.click(screen.getByRole("button", { name: "Search" }));
    expect(await screen.findByText("Program Doctor hardening")).toBeInTheDocument();
    expect(screen.getByText("canonical task record")).toBeInTheDocument();
  });

  it("sends typed live steering actions from run detail and refreshes the audit view", async () => {
    const steeringHistory: Array<Record<string, unknown>> = [];
    const timeline: Array<Record<string, unknown>> = [];
    const runId = "run_gamma_local_1";
    const eventTypeByAction: Record<string, string> = {
      pause: "steering.pause",
      note: "steering.note",
      cancel: "steering.cancel",
      reroute: "steering.rerouted",
    };

    const fetchMock = installFetchMock([
      {
        pathname: `/runs/${runId}`,
        response: () =>
          jsonResponse({
            ok: true,
            detail: {
              run: {
                id: runId,
                project_id: "gamma",
                driver: "local",
                status: "running",
                health: "healthy",
                started_at: "2026-03-17T05:20:00Z",
                finished_at: null,
                metadata_json: { task_title: "Gamma launch page" },
              },
              promotion_decision: {
                decision: "review",
                reasons: ["Waiting for typed operator signoff."],
              },
              artifact_preview: {
                run_brief: "Implement the launch page.",
                review_summary: "Waiting for reroute decision.",
                review_notes: "Need stronger repo-wide pass.",
                diff: "diff --git a/src/App.tsx b/src/App.tsx",
                stdout: "vite build",
                stderr: "",
              },
              inspector: {
                memory_entries: [{ source_path: ".hive/memory/project/profile.md" }],
                skill_entries: [{ source_path: ".agents/skills/writing-humanizer/SKILL.md" }],
                search_hits: [{ title: "Launch copy", why: ["matched title terms: launch"] }],
                outputs: ["SESSION_CONTEXT.md"],
              },
              capability_snapshot: {
                effective: {
                  launch_mode: "local",
                  session_persistence: "session",
                  event_stream: "status",
                  approvals: [],
                  artifacts: ["runpack", "transcript"],
                },
              },
              sandbox_policy: {
                backend: "podman",
                profile: "local-safe",
              },
              retrieval_trace: {
                selected_context: [
                  {
                    chunk_id: "program",
                    title: "PROGRAM.md",
                    explanation: "program policy outranked general docs",
                  },
                ],
              },
              context_manifest: {
                run_id: runId,
                generated_at: "2026-03-17T05:21:00Z",
              },
              approvals: [],
              steering_history: steeringHistory,
              timeline,
              evaluations: [{ evaluator_id: "pytest", status: "passed", command: "pytest -q" }],
              changed_files: { touched_paths: ["src/App.tsx"] },
              context_entries: [{ source_path: "AGENTS.md" }],
            },
          }),
      },
      {
        method: "POST",
        pathname: `/runs/${runId}/steer`,
        response: (_url, init) => {
          const payload = JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>;
          const eventType = eventTypeByAction[String(payload.action)];
          const event = {
            event_id: `event_${steeringHistory.length + 1}`,
            type: eventType,
            ts: "2026-03-17T05:25:00Z",
            payload,
          };
          steeringHistory.push(event);
          timeline.push(event);
          return jsonResponse({ ok: true, run: { id: runId } });
        },
      },
    ]);

    const user = userEvent.setup();
    renderConsole([`/runs/${runId}`]);

    await screen.findByRole("heading", { name: runId });
    const steeringPanel = screen.getByRole("heading", { name: "Steering History" }).closest("section");
    const timelinePanel = screen.getByRole("heading", { name: "Timeline" }).closest("section");
    expect(steeringPanel).not.toBeNull();
    expect(timelinePanel).not.toBeNull();

    const reasonBox = screen.getByRole("textbox", { name: "Reason" });

    async function triggerAction(action: string, reason: string, actionId: string) {
      await user.clear(reasonBox);
      await user.type(reasonBox, reason);
      await user.click(screen.getByRole("button", { name: action }));
      expect(await screen.findByText(`Sent ${actionId} for ${runId}.`)).toBeInTheDocument();
      expect(await within(steeringPanel as HTMLElement).findByText(eventTypeByAction[actionId])).toBeInTheDocument();
      expect(await within(timelinePanel as HTMLElement).findByText(eventTypeByAction[actionId])).toBeInTheDocument();
    }

    await triggerAction("Pause", "Need a pause before rerouting.", "pause");
    await triggerAction("Add Note", "Leave a note for the next turn.", "note");
    await triggerAction("Cancel", "Stop this run before reassigning it.", "cancel");

    const noteBox = screen.getByRole("textbox", { name: "Note" });
    await user.clear(reasonBox);
    await user.type(reasonBox, "Switch this run to Codex.");
    await user.type(noteBox, "Need stronger repo-wide reasoning.");
    await user.selectOptions(screen.getByRole("combobox", { name: "Reroute to" }), "codex");
    await user.click(screen.getByRole("button", { name: "Reroute" }));

    expect(await screen.findByText(`Sent reroute for ${runId}.`)).toBeInTheDocument();
    expect(await within(steeringPanel as HTMLElement).findByText("steering.rerouted")).toBeInTheDocument();
    expect(await within(timelinePanel as HTMLElement).findByText("steering.rerouted")).toBeInTheDocument();

    const postBodies = fetchMock.mock.calls
      .filter(([, init]) => (init?.method ?? "GET").toUpperCase() === "POST")
      .map(([, init]) => JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>);

    expect(postBodies).toEqual([
      {
        action: "pause",
        actor: "console-operator",
        reason: "Need a pause before rerouting.",
      },
      {
        action: "note",
        actor: "console-operator",
        reason: "Leave a note for the next turn.",
      },
      {
        action: "cancel",
        actor: "console-operator",
        reason: "Stop this run before reassigning it.",
      },
      {
        action: "reroute",
        actor: "console-operator",
        reason: "Switch this run to Codex.",
        note: "Need stronger repo-wide reasoning.",
        target: { driver: "codex" },
      },
    ]);
  });

  it("renders runtime inspectors and approval actions for staged runs without live controls", async () => {
    const runId = "run_alpha_codex_1";
    const approvals = [
      {
        approval_id: "approval_1",
        title: "Approve git status",
        summary: "Driver wants to run `git status`.",
        kind: "command",
        status: "pending",
        payload: { command: "git status" },
      },
      {
        approval_id: "approval_2",
        title: "Reject rm -rf /tmp/demo",
        summary: "Driver wants to remove a temp directory.",
        kind: "command",
        status: "pending",
        payload: { command: "rm -rf /tmp/demo" },
      },
    ];
    const fetchMock = installFetchMock([
      {
        pathname: `/runs/${runId}`,
        response: () =>
          jsonResponse({
            ok: true,
            detail: {
              run: {
                id: runId,
                project_id: "alpha",
                driver: "codex",
                status: "awaiting_input",
                health: "healthy",
                started_at: "2026-03-17T05:10:00Z",
                finished_at: null,
                metadata_json: { task_title: "Alpha codex slice" },
              },
              promotion_decision: {
                decision: "review",
                reasons: ["Waiting for operator approval."],
              },
              artifact_preview: {
                run_brief: "Follow the prepared Codex run brief.",
                review_summary: "Waiting for a final signoff.",
                review_notes: "This run is paused for review.",
                diff: "diff --git a/src/app.tsx b/src/app.tsx",
                stdout: "codex ready",
                stderr: "",
              },
              inspector: {
                memory_entries: [{ source_path: ".hive/memory/project/profile.md" }],
                skill_entries: [{ source_path: ".agents/skills/writing-humanizer/SKILL.md" }],
                search_hits: [{ title: "Alpha launch copy", why: ["matched title terms: alpha"] }],
                outputs: ["SESSION_CONTEXT.md"],
              },
              capability_snapshot: {
                effective: {
                  launch_mode: "staged",
                  session_persistence: "none",
                  event_stream: "none",
                  approvals: [],
                  artifacts: ["runpack"],
                },
              },
              sandbox_policy: {
                backend: "podman",
                profile: "local-safe",
              },
              retrieval_trace: {
                selected_context: [
                  {
                    chunk_id: "program",
                    title: "PROGRAM.md",
                    explanation: "program policy outranked general docs",
                  },
                ],
              },
              approvals,
              context_manifest: {
                run_id: runId,
                generated_at: "2026-03-17T05:12:00Z",
              },
              steering_history: [],
              timeline: [],
              evaluations: [{ evaluator_id: "pytest", status: "passed", command: "pytest -q" }],
              changed_files: { touched_paths: ["src/app.tsx"] },
              context_entries: [{ source_path: "AGENTS.md" }],
            },
          }),
      },
      {
        method: "POST",
        pathname: `/runs/${runId}/approvals/approval_1/approve`,
        response: () => {
          approvals[0] = { ...approvals[0], status: "approved" };
          return jsonResponse({ ok: true, approval: { approval_id: "approval_1", status: "approved" } });
        },
      },
      {
        method: "POST",
        pathname: `/runs/${runId}/approvals/approval_2/reject`,
        response: () => {
          approvals[1] = { ...approvals[1], status: "rejected" };
          return jsonResponse({ ok: true, approval: { approval_id: "approval_2", status: "rejected" } });
        },
      },
    ]);

    const user = userEvent.setup();
    renderConsole([`/runs/${runId}`]);

    await screen.findByText(/this run is staged rather than attached to a live driver session/i);
    expect(screen.queryByRole("button", { name: "Pause" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Resume" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add Note" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: runId })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Capability snapshot" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Sandbox policy" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Retrieval trace" })).toBeInTheDocument();
    expect(screen.getByText("Approve git status")).toBeInTheDocument();
    expect(screen.getByText("Reject rm -rf /tmp/demo")).toBeInTheDocument();
    expect(screen.getByText("PROGRAM.md — program policy outranked general docs")).toBeInTheDocument();

    const approveCard = screen.getByText("Approve git status").closest("article");
    const rejectCard = screen.getByText("Reject rm -rf /tmp/demo").closest("article");
    expect(approveCard).not.toBeNull();
    expect(rejectCard).not.toBeNull();

    await user.click(within(approveCard as HTMLElement).getByRole("button", { name: "Approve" }));
    expect(await screen.findByText(`Approved approval_1 for ${runId}.`)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText("Approve git status")).not.toBeInTheDocument();
    });

    await user.click(within(rejectCard as HTMLElement).getByRole("button", { name: "Reject" }));
    expect(await screen.findByText(`Rejected approval_2 for ${runId}.`)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText("Reject rm -rf /tmp/demo")).not.toBeInTheDocument();
    });

    const approvalCalls = fetchMock.mock.calls.filter(([input, init]) => {
      const url = new URL(
        typeof input === "string" ? input : input instanceof URL ? input : input.url,
      );
      return url.pathname.startsWith(`/runs/${runId}/approvals/`)
        && (init?.method ?? "GET").toUpperCase() === "POST";
    });
    expect(approvalCalls.map(([input]) => {
      const url = new URL(
        typeof input === "string" ? input : input instanceof URL ? input : input.url,
      );
      return url.pathname;
    })).toEqual([
      `/runs/${runId}/approvals/approval_1/approve`,
      `/runs/${runId}/approvals/approval_2/reject`,
    ]);
  });

  it("explains when live controls are hidden because capability snapshots are missing", async () => {
    const runId = "run_beta_local_1";
    installFetchMock([
      {
        pathname: `/runs/${runId}`,
        response: jsonResponse({
          ok: true,
          detail: {
            run: {
              id: runId,
              project_id: "beta",
              driver: "local",
              status: "running",
              health: "healthy",
              started_at: "2026-03-17T06:00:00Z",
              finished_at: null,
              metadata_json: { task_title: "Legacy local run" },
            },
            promotion_decision: {
              decision: "pending",
              reasons: [],
            },
            artifact_preview: {},
            inspector: {},
            approvals: [],
            context_manifest: {},
            steering_history: [],
            timeline: [],
            evaluations: [],
            changed_files: {},
            context_entries: [],
          },
        }),
      },
    ]);

    renderConsole([`/runs/${runId}`]);

    await screen.findByText(/predates capability snapshots or the snapshot is missing/i);
    expect(
      screen.getByText(/predates capability snapshots or the snapshot is missing/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: runId })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Pause" })).not.toBeInTheDocument();
  });

  it("lets the operator inspect campaign reasoning from the shipped console", async () => {
    installFetchMock([
      {
        pathname: "/campaigns",
        response: jsonResponse({
          ok: true,
          campaigns: [
            {
              id: "campaign_daily",
              title: "North Star Daily Brief",
              status: "active",
              goal: "Keep the portfolio moving.",
              driver: "local",
              cadence: "daily",
              brief_cadence: "daily",
              lane_quotas: { exploit: 60, explore: 20, review: 10, maintenance: 10 },
            },
          ],
        }),
      },
      {
        pathname: "/campaigns/campaign_daily",
        response: jsonResponse({
          ok: true,
          campaign: {
            id: "campaign_daily",
            title: "North Star Daily Brief",
            status: "active",
            goal: "Keep the portfolio moving.",
            type: "delivery",
            driver: "local",
            sandbox_profile: "local-safe",
            cadence: "daily",
            brief_cadence: "daily",
            max_active_runs: 2,
            lane_quotas: { exploit: 60, explore: 20, review: 10, maintenance: 10 },
          },
          active_runs: [],
          accepted_runs: [],
          decision_preview: {
            selected_candidate_id: "task_1",
            selected_lane: "exploit",
            selected_action: "launch",
            reason: "highest exploit score under current lane quotas",
            selected_candidate: {
              candidate_id: "task_1",
              title: "Ship the settings page",
            },
          },
          candidate_set_preview: {
            candidates: [
              {
                candidate_id: "task_1",
                title: "Ship the settings page",
                lane: "exploit",
                recommended_driver: "codex",
                recommended_sandbox: "local-safe",
                scores: { campaign_alignment: 0.9, harness_fit: 0.95 },
              },
              {
                candidate_id: "task_2",
                title: "Investigate a research spike",
                lane: "explore",
                recommended_driver: "claude",
                recommended_sandbox: "local-safe",
                scores: { campaign_alignment: 0.6, harness_fit: 0.7 },
              },
            ],
          },
          latest_candidate_set: { candidates: [] },
          latest_decision: { selected_candidate_id: "task_1" },
        }),
      },
    ]);

    const user = userEvent.setup();
    renderConsole(["/campaigns"]);

    await screen.findByRole("heading", { name: "Campaigns" });
    await user.click(await screen.findByRole("link", { name: "North Star Daily Brief" }));

    await screen.findByRole("heading", { name: "Decision Preview" });
    expect(screen.getByText("highest exploit score under current lane quotas")).toBeInTheDocument();
    expect(screen.getAllByText("Ship the settings page")).toHaveLength(2);
    expect(screen.getByText("Investigate a research spike")).toBeInTheDocument();
    expect(screen.getByText("selected")).toBeInTheDocument();
    expect(screen.getByText("rejected")).toBeInTheDocument();
  });

  it("recovers the run event view after a browser refresh", async () => {
    const runId = "run_alpha_codex_1";
    const fetchMock = installFetchMock([
      {
        pathname: `/runs/${runId}`,
        response: jsonResponse({
          ok: true,
          detail: {
            run: {
              id: runId,
              project_id: "alpha",
              driver: "codex",
              status: "awaiting_input",
              health: "healthy",
              started_at: "2026-03-17T05:10:00Z",
              finished_at: null,
              metadata_json: { task_title: "Alpha codex slice" },
            },
            promotion_decision: {
              decision: "review",
              reasons: ["Waiting for operator approval."],
            },
            artifact_preview: {
              run_brief: "Follow the prepared Codex run brief.",
              review_summary: "Waiting for a final signoff.",
              review_notes: "This run is paused for review.",
              diff: "diff --git a/src/app.tsx b/src/app.tsx",
              stdout: "codex ready",
              stderr: "",
            },
            inspector: {
              memory_entries: [{ source_path: ".hive/memory/project/profile.md" }],
              skill_entries: [{ source_path: ".agents/skills/writing-humanizer/SKILL.md" }],
              search_hits: [{ title: "Alpha launch copy", why: ["matched title terms: alpha"] }],
              outputs: ["SESSION_CONTEXT.md"],
            },
            context_manifest: {
              run_id: runId,
              generated_at: "2026-03-17T05:12:00Z",
            },
            steering_history: [
              {
                event_id: "event_1",
                type: "steering.rerouted",
                ts: "2026-03-17T05:11:00Z",
                payload: { target: { driver: "codex" } },
              },
            ],
            timeline: [
              {
                event_id: "event_1",
                type: "steering.rerouted",
                ts: "2026-03-17T05:11:00Z",
                payload: { target: { driver: "codex" } },
              },
              {
                event_id: "event_2",
                type: "run.awaiting_review",
                ts: "2026-03-17T05:12:00Z",
                payload: { decision: "review" },
              },
            ],
            evaluations: [{ evaluator_id: "pytest", status: "passed", command: "pytest -q" }],
            changed_files: { touched_paths: ["src/app.tsx"] },
            context_entries: [{ source_path: "AGENTS.md" }],
          },
        }),
      },
    ]);

    const first = renderConsole([`/runs/${runId}`]);

    await screen.findByRole("heading", { name: runId });
    // The reroute event is rendered once in Steering History and once again in the Timeline panel.
    expect(await screen.findAllByText("steering.rerouted")).toHaveLength(2);
    expect(screen.getByText("Follow the prepared Codex run brief.")).toBeInTheDocument();

    first.unmount();

    renderConsole([`/runs/${runId}`]);

    await screen.findByRole("heading", { name: runId });
    // The reroute event is rendered once in Steering History and once again in the Timeline panel.
    expect(await screen.findAllByText("steering.rerouted")).toHaveLength(2);
    expect(screen.getByText(/Alpha launch copy/)).toBeInTheDocument();

    const detailCalls = fetchMock.mock.calls.filter(([input]) => {
      const url = new URL(typeof input === "string" ? input : input instanceof URL ? input : input.url);
      return url.pathname === `/runs/${runId}`;
    });
    expect(detailCalls.length).toBeGreaterThanOrEqual(2);
  });
});
