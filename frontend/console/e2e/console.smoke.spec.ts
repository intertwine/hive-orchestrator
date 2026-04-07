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
