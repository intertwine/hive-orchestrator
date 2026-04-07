import { expect, test, type Page } from "@playwright/test";

const APP_BASE = "http://127.0.0.1:4174";
const API_BASE = "http://127.0.0.1:8787";
const WORKSPACE = "/tmp/hive-demo";

function consoleUrl(routePath: string) {
  const url = new URL(`/console${routePath}`, APP_BASE);
  url.searchParams.set("apiBase", API_BASE);
  url.searchParams.set("workspace", WORKSPACE);
  return url.toString();
}

async function configureBrowserShell(page: Page) {
  await page.addInitScript(({ apiBase, workspace }) => {
    window.localStorage.setItem("hive-console-api-base", apiBase);
    window.localStorage.setItem("hive-console-workspace", workspace);
    Object.defineProperty(window, "EventSource", {
      configurable: true,
      value: undefined,
    });
  }, { apiBase: API_BASE, workspace: WORKSPACE });
}

async function fulfillJsonRoute(page: Page, pathname: string, body: unknown) {
  const pattern = `${new URL(pathname, API_BASE).toString()}*`;
  await page.route(pattern, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      headers: {
        "access-control-allow-origin": "*",
      },
      body: JSON.stringify(body),
    });
  });
}

async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(() => {
    const root = document.scrollingElement ?? document.documentElement;
    return root.scrollWidth - window.innerWidth;
  });
  expect(overflow).toBeLessThanOrEqual(1);
}

test.beforeEach(async ({ page }) => {
  await configureBrowserShell(page);
});

test("preserves deep-link query params while navigating notifications, activity, and integrations", async ({
  page,
}) => {
  await fulfillJsonRoute(page, "/notifications", {
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
        project_id: "beta",
        run_id: "run_beta_codex_1",
        severity: "info",
        severity_label: "Info",
        decision_type: "informational",
        decision_label: "Informational",
        group_key: "info:informational",
        group_label: "Info · Informational",
        notification_tier: "informational",
        source: "run",
        bulk_actions: ["dismiss", "snooze", "assign"],
        deep_link: "/runs/run_beta_codex_1",
        project_label: "Beta",
        run_label: "Beta codex pass",
        why_visible: "Accepted runs stay visible as informational notifications.",
        ignore_impact: "Ignoring this only hides it locally.",
      },
    ],
    summary: {
      total: 2,
      by_severity: { critical: 1, info: 1 },
      by_decision_type: { approval: 1, informational: 1 },
      by_notification_tier: { actionable: 1, informational: 1 },
    },
  });
  await fulfillJsonRoute(page, "/activity", {
    ok: true,
    items: [
      {
        id: "activity_event_1",
        kind: "event",
        title: "Rerouted Gamma to Codex.",
        summary: "Operator rerouted the run to Codex.",
        occurred_at: "2026-03-17T05:30:00Z",
        project_id: "gamma",
        project_label: "Gamma",
        run_id: "run_gamma_local_1",
        deep_link: "/runs/run_gamma_local_1",
      },
      {
        id: "activity_accept_1",
        kind: "accepted-run",
        title: "Accepted Beta codex pass",
        summary: "Beta codex pass was accepted on codex.",
        occurred_at: "2026-03-17T05:10:00Z",
        project_id: "beta",
        project_label: "Beta",
        run_id: "run_beta_codex_1",
        deep_link: "/runs/run_beta_codex_1",
      },
    ],
    summary: { total: 2 },
  });
  await fulfillJsonRoute(page, "/integrations", {
    ok: true,
    backends: [
      {
        adapter: "local",
        available: true,
        adapter_family: "builtin",
        integration_level: "native",
        governance_mode: "managed",
      },
    ],
  });
  await fulfillJsonRoute(page, "/integrations/local", {
    ok: true,
    integration: {
      adapter: "local",
      adapter_family: "builtin",
      integration_level: "native",
      governance_mode: "managed",
      version: "1.0.0",
      notes: ["Native local driver is available."],
      next_steps: ["Proceed with confidence."],
    },
  });

  await page.goto(consoleUrl("/notifications"));

  await expect(page.getByRole("heading", { name: "Notifications" })).toBeVisible();
  await expect(page.getByText("Approve Gamma reroute")).toBeVisible();
  await expect(page.getByText("Accepted shell routing foundation")).toBeVisible();

  await page.getByRole("link", { name: "Activity" }).click();
  await expect(page).toHaveURL(new RegExp(`${encodeURIComponent(WORKSPACE)}`));
  await expect(page.getByRole("heading", { name: "Activity", exact: true })).toBeVisible();
  await expect(page.getByText("Rerouted Gamma to Codex.")).toBeVisible();

  await page.getByRole("link", { name: "Integrations" }).click();
  await expect(page).toHaveURL(new RegExp(`${encodeURIComponent(WORKSPACE)}`));
  await expect(page.getByRole("heading", { name: "Integrations" })).toBeVisible();
  await expect(page.locator("li").filter({ hasText: "Native local driver is available." })).toBeVisible();
});

test("submits typed run steering from the browser and preserves the payload contract", async ({
  page,
}) => {
  let latestPayload: Record<string, unknown> | null = null;

  await fulfillJsonRoute(page, "/runs/run_gamma_local_1", {
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
        memory_entries: [],
        skill_entries: [],
        search_hits: [],
        outputs: [],
      },
      capability_snapshot: {
        effective: {
          launch_mode: "local",
          session_persistence: "session",
          event_stream: "status",
          approvals: [],
          artifacts: ["runpack"],
        },
      },
      sandbox_policy: {
        backend: "podman",
        profile: "local-safe",
      },
      retrieval_trace: {
        selected_context: [],
      },
      approvals: [],
      steering_history: [],
      timeline: [],
      evaluations: [],
      changed_files: { touched_paths: [] },
      context_entries: [],
    },
  });

  await page.route("**/actions/execute*", async (route) => {
    latestPayload = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true, run: { id: "run_gamma_local_1" } }),
    });
  });

  await page.goto(consoleUrl("/runs/run_gamma_local_1"));

  await expect(page.getByRole("heading", { name: "run_gamma_local_1" })).toBeVisible();
  await page.getByRole("textbox", { name: "Reason" }).fill("Switch this run to Codex.");
  await page.getByRole("textbox", { name: "Note" }).fill("Need stronger repo-wide reasoning.");
  await page.getByRole("combobox", { name: "Reroute to" }).selectOption("codex");
  await page.getByRole("button", { name: "Reroute" }).click();

  await expect(page.getByText("Sent reroute for run_gamma_local_1.")).toBeVisible();
  expect(latestPayload).toEqual({
    action_id: "run.reroute",
    actor: "console-operator",
    note: "Need stronger repo-wide reasoning.",
    reason: "Switch this run to Codex.",
    run_id: "run_gamma_local_1",
    target: { driver: "codex" },
  });
});

test("keeps the primary v2.5 surfaces responsive on a mobile viewport", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });

  await fulfillJsonRoute(page, "/home", {
    ok: true,
    home: {
      workspace: WORKSPACE,
      active_runs: [],
      evaluating_runs: [],
      inbox: [
        { kind: "run-review", title: "Alpha review", reason: "Need evaluator signoff" },
      ],
      blocked_projects: [],
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
      recent_events: [],
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
  });
  await fulfillJsonRoute(page, "/inbox", {
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
  });
  await fulfillJsonRoute(page, "/campaigns", {
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
  });
  await fulfillJsonRoute(page, "/search", {
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
  });
  await fulfillJsonRoute(page, "/runs/run_gamma_local_1", {
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
        review_summary: "Waiting for reroute decision.",
        review_notes: "Operator review notes stay visible here.",
        diff: "diff --git a/src/App.tsx b/src/App.tsx",
        stdout: "console ready",
        stderr: "",
      },
      inspector: {
        memory_entries: [],
        skill_entries: [],
        search_hits: [],
        outputs: [],
      },
      capability_snapshot: {
        effective: {
          launch_mode: "local",
          session_persistence: "session",
          event_stream: "status",
          approvals: [],
          artifacts: ["runpack"],
        },
      },
      sandbox_policy: {
        backend: "podman",
        profile: "local-safe",
      },
      retrieval_trace: {
        selected_context: [],
      },
      approvals: [],
      steering_history: [],
      timeline: [],
      evaluations: [],
      changed_files: { touched_paths: [] },
      context_entries: [],
    },
  });
  await fulfillJsonRoute(page, "/runs/run_gamma_local_1/compare", {
    ok: true,
    comparison: {
      current: {
        run_id: "run_gamma_local_1",
        title: "Gamma launch page",
        driver: "local",
        status: "review",
        changed_paths: [],
        evaluation_summary: { total: 0, by_status: {} },
      },
      baseline: {},
      diff: {
        current_only: [],
        baseline_only: [],
        shared: [],
      },
      summary: {
        has_baseline: false,
        baseline_label: "",
        current_label: "Gamma launch page",
      },
    },
  });

  await page.goto(consoleUrl("/"));
  await expect(page.getByRole("heading", { name: "Home", exact: true })).toBeVisible();
  await expect(page.getByText("Investigate inbox routing")).toBeVisible();
  await expectNoHorizontalOverflow(page);

  await page.goto(consoleUrl("/inbox"));
  await expect(page.getByRole("heading", { name: "Inbox", exact: true })).toBeVisible();
  await expect(page.getByText("Approve Gamma reroute")).toBeVisible();
  await expectNoHorizontalOverflow(page);

  await page.goto(consoleUrl("/campaigns"));
  await expect(page.getByRole("heading", { name: "Campaigns", exact: true })).toBeVisible();
  await expect(page.getByText("North Star Daily Brief")).toBeVisible();
  await expectNoHorizontalOverflow(page);

  await page.goto(consoleUrl("/search"));
  await expect(page.getByRole("heading", { name: "Search", exact: true })).toBeVisible();
  const searchResultButton = page.getByRole("button", { name: /Docs PROGRAM\.md Docs/ });
  await expect(searchResultButton).toBeVisible();
  await searchResultButton.click();
  await expect(searchResultButton).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("#search-preview-panel")).toBeFocused();
  await expectNoHorizontalOverflow(page);

  await page.goto(consoleUrl("/runs/run_gamma_local_1"));
  await expect(page.getByRole("heading", { name: "run_gamma_local_1", exact: true })).toBeVisible();
  await page.getByRole("tab", { name: "Run brief" }).press("End");
  await expect(page.getByRole("tab", { name: "stderr" })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("tabpanel", { name: "stderr" })).toContainText("No stderr recorded yet.");
  await expectNoHorizontalOverflow(page);
});
