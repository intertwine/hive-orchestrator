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
        kind: "project-doc",
        summary: "Policy guidance for governed runs.",
        why: ["matched title terms: program"],
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
    await screen.findByText("PROGRAM.md");
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });

  it("keeps Settings free of automated violations", async () => {
    await expectNoViolations(["/settings"], "Settings", []);
  });

  it("keeps Notifications free of automated violations", async () => {
    await expectNoViolations(["/notifications"], "Notifications", [INBOX_ROUTE]);
  });

  it("keeps Activity free of automated violations", async () => {
    await expectNoViolations(["/activity"], "Activity", [ACTIVE_HOME_ROUTE]);
  });
});
