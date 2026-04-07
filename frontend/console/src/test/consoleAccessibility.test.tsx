import { screen } from "@testing-library/react";
import { axe } from "jest-axe";
import { afterEach, describe, expect, it, vi } from "vitest";

import { installFetchMock, jsonResponse, renderConsole, type MockRoute } from "./consoleTestHarness";

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

const ACTIVE_HOME_ROUTE: MockRoute = {
  pathname: "/home",
  response: jsonResponse({
    ok: true,
    home: {
      workspace: "/tmp/hive-demo",
      active_runs: [makeRun("run_alpha_local_1", "alpha", "local", "healthy", "Alpha local slice")],
      evaluating_runs: [],
      inbox: [{ kind: "run-review", title: "Alpha review", reason: "Need evaluator signoff" }],
      blocked_projects: [],
      campaigns: [],
      recent_events: [
        {
          event_id: "event_1",
          type: "steering.rerouted",
          ts: "2026-03-17T05:30:00Z",
          payload: { message: "Rerouted Gamma to Codex.", run_id: "run_alpha_local_1" },
        },
      ],
      recent_accepts: [],
      recommended_next: {
        task: {
          id: "task_alpha_next",
          title: "Investigate inbox routing",
          project_id: "alpha",
        },
        reasons: ["highest priority ready task"],
      },
    },
  }),
};

const GETTING_STARTED_HOME_ROUTE: MockRoute = {
  pathname: "/home",
  response: jsonResponse({
    ok: true,
    home: {
      workspace: "/tmp/hive-demo",
      active_runs: [],
      evaluating_runs: [],
      inbox: [],
      blocked_projects: [],
      campaigns: [],
      recent_events: [],
      recent_accepts: [],
      recommended_next: null,
    },
  }),
};

const INBOX_ROUTE: MockRoute = {
  pathname: "/inbox",
  response: jsonResponse({
    ok: true,
    items: [
      {
        kind: "approval-request",
        title: "Approve Gamma reroute",
        reason: "Driver needs operator approval.",
        project_id: "gamma",
        run_id: "run_gamma_local_1",
        approval_id: "approval_1",
      },
    ],
    summary: {
      total: 1,
      by_severity: { critical: 1 },
      by_decision_type: { approval: 1 },
      by_notification_tier: { actionable: 1 },
    },
  }),
};

const NOTIFICATIONS_ROUTE: MockRoute = {
  pathname: "/notifications",
  response: jsonResponse({
    ok: true,
    items: [
      {
        kind: "approval-request",
        title: "Approve Gamma reroute",
        reason: "Driver needs operator approval.",
        project_id: "gamma",
        run_id: "run_gamma_local_1",
        approval_id: "approval_1",
      },
      {
        kind: "accepted-run",
        title: "Accepted shell routing foundation",
        reason: "Shell routing landed on codex.",
        project_id: "gamma",
        run_id: "run_gamma_local_1",
        severity: "info",
        severity_label: "Info",
        decision_type: "informational",
        decision_label: "Informational",
        group_key: "info:informational",
        group_label: "Info · Informational",
        notification_tier: "informational",
        source: "run",
        bulk_actions: ["dismiss", "snooze", "assign"],
        deep_link: "/runs/run_gamma_local_1",
        project_label: "Gamma",
        run_label: "Gamma launch page",
        why_visible: "Accepted runs stay visible as informational notifications.",
        ignore_impact: "Ignoring this only hides it from the local queue.",
      },
    ],
    summary: {
      total: 2,
      by_severity: { critical: 1, info: 1 },
      by_decision_type: { approval: 1, informational: 1 },
      by_notification_tier: { actionable: 1, informational: 1 },
    },
  }),
};

const ACTIVITY_ROUTE: MockRoute = {
  pathname: "/activity",
  response: jsonResponse({
    ok: true,
    items: [
      {
        id: "activity_event_1",
        kind: "event",
        title: "Canonical /home route published.",
        summary: "Stable deep link shipped.",
        occurred_at: "2026-04-06T21:00:00Z",
        project_id: "gamma",
        project_label: "Gamma",
        run_id: "run_gamma_local_1",
        deep_link: "/runs/run_gamma_local_1",
      },
      {
        id: "activity_accept_1",
        kind: "accepted-run",
        title: "Accepted Publish the shell route contract",
        summary: "The shell route contract was accepted on codex.",
        occurred_at: "2026-04-06T20:30:00Z",
        project_id: "gamma",
        project_label: "Gamma",
        run_id: "run_gamma_local_1",
        deep_link: "/runs/run_gamma_local_1",
      },
    ],
    summary: { total: 2 },
  }),
};

const CAMPAIGNS_ROUTE: MockRoute = {
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
};

const RUNS_ROUTE: MockRoute = {
  pathname: "/runs",
  response: jsonResponse({
    ok: true,
    runs: [
      makeRun("run_alpha_local_1", "alpha", "local", "healthy", "Alpha local slice"),
      makeRun("run_beta_codex_1", "beta", "codex", "healthy", "Beta codex pass"),
    ],
  }),
};

const PROJECTS_ROUTE: MockRoute = {
  pathname: "/projects",
  response: jsonResponse({
    ok: true,
    projects: [
      {
        id: "alpha",
        title: "Alpha Project",
        status: "healthy",
        priority: 1,
        owner: "codex",
      },
    ],
  }),
};

const PROJECT_DOCTOR_ROUTE: MockRoute = {
  pathname: "/projects/alpha/doctor",
  response: jsonResponse({
    ok: true,
    doctor: {
      status: "fail",
      blocked_autonomous_promotion: true,
      issues: [
        {
          code: "missing_required_evaluator",
          message: "Program Doctor needs a required evaluator.",
        },
      ],
    },
  }),
};

const PROJECT_CONTEXT_ROUTE: MockRoute = {
  pathname: "/projects/alpha/context",
  response: jsonResponse({
    ok: true,
    project: { id: "alpha" },
    rendered: "Demo context preview",
    context: {},
  }),
};

const SEARCH_ROUTE: MockRoute = {
  pathname: "/search",
  response: jsonResponse({
    ok: true,
    results: [
      {
        id: "result_program",
        title: "PROGRAM.md",
        kind: "program",
        source: "docs",
        source_label: "Docs",
        summary: "Policy guidance for governed runs.",
        preview: "The program defines evaluator and promotion policy.",
        why: ["matched title terms: program"],
        project_id: "alpha",
        project_label: "Alpha Project",
        path: "projects/alpha/PROGRAM.md",
        deep_link: "/projects/alpha",
        open_label: "Open project",
      },
    ],
  }),
};

const RUN_DETAIL_ROUTE: MockRoute = {
  pathname: "/runs/run_gamma_local_1",
  response: jsonResponse({
    ok: true,
    detail: {
      run: {
        id: "run_gamma_local_1",
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
      approvals: [],
      steering_history: [],
      timeline: [],
      evaluations: [{ evaluator_id: "pytest", status: "passed", command: "pytest -q" }],
      changed_files: { touched_paths: ["src/App.tsx"] },
      context_entries: [{ source_path: "AGENTS.md" }],
    },
  }),
};

function actionExecutionRoute() {
  return {
    method: "POST",
    pathname: "/actions/execute",
    response: jsonResponse({ ok: true, run: { id: "run_gamma_local_1" } }),
  } satisfies MockRoute;
}

async function expectNoViolations(
  initialEntries: string[],
  headingName: string,
  routes: MockRoute[],
) {
  installFetchMock(routes);
  const { container } = renderConsole(initialEntries);
  await screen.findByRole("heading", { name: headingName });
  const results = await axe(container);
  expect(results.violations).toEqual([]);
}

describe("Console accessibility smoke", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("keeps the active Home surface free of automated violations", async () => {
    await expectNoViolations(["/"], "Home", [ACTIVE_HOME_ROUTE]);
  });

  it("keeps the getting-started Home surface free of automated violations", async () => {
    await expectNoViolations(["/"], "Home", [GETTING_STARTED_HOME_ROUTE]);
    expect(screen.getByRole("heading", { name: "Getting Started with Agent Hive" })).toBeInTheDocument();
  });

  it("keeps Inbox free of automated violations", async () => {
    await expectNoViolations(["/inbox"], "Inbox", [INBOX_ROUTE]);
  });

  it("keeps Runs free of automated violations", async () => {
    await expectNoViolations(["/runs"], "Runs", [RUNS_ROUTE]);
  });

  it("keeps Run Detail free of automated violations", async () => {
    await expectNoViolations(["/runs/run_gamma_local_1"], "run_gamma_local_1", [
      RUN_DETAIL_ROUTE,
      actionExecutionRoute(),
    ]);
  });

  it("keeps Projects free of automated violations", async () => {
    await expectNoViolations(["/projects"], "Projects", [
      PROJECTS_ROUTE,
      PROJECT_DOCTOR_ROUTE,
      PROJECT_CONTEXT_ROUTE,
    ]);
  });

  it("keeps Search free of automated violations after results load", async () => {
    installFetchMock([SEARCH_ROUTE]);
    const { container } = renderConsole(["/search"]);
    const button = await screen.findByRole("button", { name: "Search" });
    button.click();
    expect(await screen.findAllByText("PROGRAM.md")).toHaveLength(2);
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });

  it("keeps Settings free of automated violations", async () => {
    await expectNoViolations(["/settings"], "Settings", []);
  });

  it("keeps Campaigns free of automated violations", async () => {
    await expectNoViolations(["/campaigns"], "Campaigns", [CAMPAIGNS_ROUTE]);
  });

  it("keeps Notifications free of automated violations", async () => {
    await expectNoViolations(["/notifications"], "Notifications", [NOTIFICATIONS_ROUTE]);
  });

  it("keeps Activity free of automated violations", async () => {
    await expectNoViolations(["/activity"], "Activity", [ACTIVITY_ROUTE]);
  });
});
