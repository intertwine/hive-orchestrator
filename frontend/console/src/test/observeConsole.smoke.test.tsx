import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import { CONSOLE_PREFERENCES_KEY } from "../preferences";
import { installFetchMock, jsonResponse, renderConsole } from "./consoleTestHarness";

class MockEventSource {
  static instances: MockEventSource[] = [];

  onerror: ((event: Event) => void) | null = null;
  onopen: ((event: Event) => void) | null = null;
  readonly url: string;
  private readonly listeners = new Map<string, Set<(event: MessageEvent) => void>>();

  constructor(url: string | URL) {
    this.url = String(url);
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    const listeners = this.listeners.get(type) ?? new Set<(event: MessageEvent) => void>();
    listeners.add(listener);
    this.listeners.set(type, listeners);
  }

  removeEventListener(type: string, listener: (event: MessageEvent) => void) {
    this.listeners.get(type)?.delete(listener);
  }

  close() {
    return undefined;
  }

  emit(type: string, payload: unknown) {
    const event = new MessageEvent(type, {
      data: JSON.stringify(payload),
    });
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event);
    }
  }

  open() {
    this.onopen?.(new Event("open"));
  }

  static reset() {
    MockEventSource.instances = [];
  }
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

function makeRunComparisonResponse(options?: {
  currentRunId?: string;
  currentTitle?: string;
  currentDriver?: string;
  currentStatus?: string;
  currentChangedPaths?: string[];
  baselineRunId?: string;
  baselineTitle?: string;
  baselineDriver?: string;
  baselineStatus?: string;
  baselineChangedPaths?: string[];
  currentOnly?: string[];
  baselineOnly?: string[];
  shared?: string[];
  hasBaseline?: boolean;
  evaluationSummary?: Record<string, unknown>;
}) {
  const hasBaseline = options?.hasBaseline ?? false;
  const baselineTitle = options?.baselineTitle ?? "Accepted baseline";
  const currentTitle = options?.currentTitle ?? "Current run";
  return jsonResponse({
    ok: true,
    comparison: {
      current: {
        run_id: options?.currentRunId ?? "",
        title: currentTitle,
        driver: options?.currentDriver ?? "codex",
        status: options?.currentStatus ?? "review",
        changed_paths: options?.currentChangedPaths ?? [],
        evaluation_summary: options?.evaluationSummary ?? { total: 0, by_status: {} },
      },
      baseline: hasBaseline
        ? {
            run_id: options?.baselineRunId ?? "run_baseline_accepted",
            title: baselineTitle,
            driver: options?.baselineDriver ?? "codex",
            status: options?.baselineStatus ?? "accepted",
            changed_paths: options?.baselineChangedPaths ?? [],
          }
        : {},
      diff: {
        current_only: options?.currentOnly ?? [],
        baseline_only: options?.baselineOnly ?? [],
        shared: options?.shared ?? [],
      },
      summary: {
        has_baseline: hasBaseline,
        baseline_label: hasBaseline ? baselineTitle : "",
        current_label: currentTitle,
      },
    },
  });
}

async function expectKeyValue(container: HTMLElement, label: string, value: string) {
  const row = within(container).getByText(label).closest(".key-value-grid__row");
  expect(row).not.toBeNull();
  expect(await within(row as HTMLElement).findByText(value)).toBeInTheDocument();
}

describe("Observe Console smoke", () => {
  beforeEach(() => {
    MockEventSource.reset();
  });

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
    expect(screen.queryByText("Inspect first. Mutate later.")).not.toBeInTheDocument();
    expect(screen.queryByText("Choose the shortest honest path")).not.toBeInTheDocument();

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

  it("refreshes the runs board within one 3-second cycle so attached delegate sessions appear", async () => {
    let attached = false;
    let pollRuns: (() => Promise<void>) | null = null;
    const delegateRun = {
      id: "del_openclaw_live",
      project_id: "alpha",
      driver: "openclaw",
      health: "healthy",
      status: "attached",
      started_at: "2026-03-29T15:40:00Z",
      metadata_json: {
        task_title: "OpenClaw attached session",
        entry_kind: "delegate_session",
      },
    };
    const fetchMock = installFetchMock([
      {
        pathname: "/runs",
        response: () => jsonResponse({ ok: true, runs: attached ? [delegateRun] : [] }),
      },
    ]);
    const setIntervalMock = vi.spyOn(window, "setInterval").mockImplementation(((handler, timeout) => {
      if (timeout === 3000 && typeof handler === "function") {
        pollRuns = handler as () => Promise<void>;
      }
      return 1;
    }) as typeof window.setInterval);
    vi.spyOn(window, "clearInterval").mockImplementation(() => undefined);

    renderConsole(["/runs"]);

    await screen.findByRole("heading", { name: "Runs" });
    expect(await screen.findByText("No runs match the current filters.")).toBeInTheDocument();
    expect(setIntervalMock).toHaveBeenCalledWith(expect.any(Function), 3000);
    expect(pollRuns).not.toBeNull();

    attached = true;
    await act(async () => {
      await pollRuns?.();
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(await screen.findByRole("link", { name: "del_openclaw_live" })).toBeInTheDocument();
  });

  it("refreshes the runs board immediately when the shared event stream emits a snapshot", async () => {
    let attached = false;
    const delegateRun = {
      id: "del_openclaw_live",
      project_id: "alpha",
      driver: "openclaw",
      health: "healthy",
      status: "attached",
      started_at: "2026-03-29T15:40:00Z",
      metadata_json: {
        task_title: "OpenClaw attached session",
        entry_kind: "delegate_session",
      },
    };
    const fetchMock = installFetchMock([
      {
        pathname: "/runs",
        response: () => jsonResponse({ ok: true, runs: attached ? [delegateRun] : [] }),
      },
    ]);
    vi.stubGlobal("EventSource", MockEventSource as unknown as typeof EventSource);

    renderConsole(["/runs"]);

    await screen.findByRole("heading", { name: "Runs" });
    expect(await screen.findByText("No runs match the current filters.")).toBeInTheDocument();
    expect(MockEventSource.instances).toHaveLength(1);
    expect(screen.getByText(/Stream offline · synced/)).toBeInTheDocument();

    attached = true;
    await act(async () => {
      MockEventSource.instances[0]?.open();
      MockEventSource.instances[0]?.emit("snapshot", {
        workspace: "/tmp/hive-demo",
        events: [{ event_id: "evt_console_1" }],
      });
    });

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2);
      expect(screen.getByRole("link", { name: "del_openclaw_live" })).toBeInTheDocument();
    });
    expect(screen.getByText("Live")).toBeInTheDocument();
  });

  it("surfaces safe-first onboarding, workspace switching, and plain-language doctor guidance", async () => {
    window.localStorage.setItem(CONSOLE_PREFERENCES_KEY, JSON.stringify({
      version: 1,
      theme: "clay",
      density: "comfortable",
      defaultPage: "home",
      recentWorkspaces: ["/tmp/release-demo", "/tmp/existing-repo"],
      runs: {
        filters: { projectId: "", driver: "", health: "", campaignId: "" },
        hiddenColumns: [],
        pinnedPanels: [],
        savedViews: [],
      },
    }));

    installFetchMock([
      {
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
            recommended_next: {
              task: {
                id: "task_demo_1",
                title: "Inspect the demo doctor output",
                project_id: "demo",
              },
              reasons: ["first guided task", "safe way to learn the command center"],
            },
          },
        }),
      },
      {
        pathname: "/projects",
        response: jsonResponse({
          ok: true,
          projects: [
            { id: "demo", title: "Demo Project", status: "active", priority: 1, owner: "codex" },
          ],
        }),
      },
      {
        pathname: "/projects/demo/doctor",
        response: jsonResponse({
          ok: true,
          doctor: {
            status: "blocked_autonomous_promotion",
            issues: [{ code: "missing_required_evaluator", message: "Add at least one evaluator." }],
          },
        }),
      },
      {
        pathname: "/projects/demo/context",
        response: jsonResponse({
          ok: true,
          project: { id: "demo" },
          rendered: "Demo context preview",
          context: {},
        }),
      },
    ]);

    const user = userEvent.setup();
    renderConsole(["/"]);

    await screen.findByRole("heading", { name: "Getting Started with Agent Hive" });
    expect(screen.getByText("Inspect first. Mutate later.")).toBeInTheDocument();
    expect(screen.getByText("Choose the shortest honest path")).toBeInTheDocument();
    expect(screen.getAllByText(/hive onboard demo --title "Demo project"/)).toHaveLength(2);
    expect(screen.getByText("Inspect the demo doctor output")).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Settings" }));
    await screen.findByRole("heading", { name: "Recent Workspaces" });
    await user.click(screen.getByRole("button", { name: /\/tmp\/release-demo/i }));
    expect(screen.getByRole("button", { name: /\/tmp\/release-demo/i })).toHaveAttribute("aria-current", "true");
    expect(screen.getAllByDisplayValue("/tmp/release-demo")).toHaveLength(2);
    expect(screen.getByText("What to open first")).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Projects" }));
    await screen.findByRole("heading", { name: "Projects" });
    expect(await screen.findByText("Program Doctor is blocking promotion")).toBeInTheDocument();
    expect(await screen.findByText("Demo context preview")).toBeInTheDocument();
  });

  it("persists saved runs views across remounts and reapplies them", async () => {
    installFetchMock([
      {
        pathname: "/runs",
        response: (url) => jsonResponse({ ok: true, runs: filterRuns(url) }),
      },
    ]);

    const user = userEvent.setup();
    const firstRender = renderConsole(["/runs"]);

    await screen.findByRole("heading", { name: "Runs" });
    await user.type(screen.getByRole("textbox", { name: "Project" }), "gamma");
    await waitFor(() => {
      expect(screen.getAllByRole("link", { name: /^run_/ })).toHaveLength(3);
    });

    await user.type(screen.getByRole("textbox", { name: "View name" }), "Gamma incidents");
    await user.click(screen.getByRole("button", { name: "Save current view" }));

    firstRender.unmount();

    renderConsole(["/runs"]);
    await screen.findByRole("heading", { name: "Runs" });
    expect(screen.getByDisplayValue("gamma")).toBeInTheDocument();
    expect(screen.getByText("Gamma incidents")).toBeInTheDocument();

    await user.clear(screen.getByRole("textbox", { name: "Project" }));
    await waitFor(() => {
      expect(screen.getAllByRole("link", { name: /^run_/ })).toHaveLength(10);
    });

    const savedViewCard = screen.getByText("Gamma incidents").closest(".saved-view-card");
    expect(savedViewCard).not.toBeNull();
    await user.click(within(savedViewCard as HTMLElement).getByRole("button", { name: "Apply" }));

    expect(screen.getByDisplayValue("gamma")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getAllByRole("link", { name: /^run_/ })).toHaveLength(3);
    });
  });

  it("surfaces attached delegate exceptions in the home and inbox views", async () => {
    const inboxItems = [
      {
        kind: "delegate-blocked",
        title: "Blocked OpenClaw attached session",
        reason: "Native session requested operator review before proceeding.",
        project_id: "alpha",
        run_id: "del_openclaw_attention",
      },
      {
        kind: "delegate-note",
        title: "Note from OpenClaw attached session",
        reason: "Need operator review before continuing.",
        project_id: "alpha",
        run_id: "del_openclaw_attention",
      },
    ];
    installFetchMock([
      {
        pathname: "/home",
        response: jsonResponse({
          ok: true,
          home: {
            workspace: "/tmp/hive-demo",
            active_runs: [
              makeRun("run_alpha_pi_1", "alpha", "pi", "healthy", "Alpha Pi slice"),
              {
                id: "del_openclaw_attention",
                project_id: "alpha",
                driver: "openclaw",
                health: "blocked",
                status: "blocked",
                started_at: "2026-03-29T15:40:00Z",
                metadata_json: {
                  task_title: "OpenClaw attached session",
                  entry_kind: "delegate_session",
                },
              },
            ],
            evaluating_runs: [],
            inbox: inboxItems,
            blocked_projects: [],
            campaigns: [],
            recent_events: [],
            recent_accepts: [],
            recommended_next: {
              task: {
                id: "task_alpha_next",
                title: "Investigate delegate inbox routing",
                project_id: "alpha",
              },
              reasons: ["delegate session requested attention"],
            },
          },
        }),
      },
      {
        pathname: "/inbox",
        response: jsonResponse({
          ok: true,
          items: inboxItems,
        }),
      },
    ]);

    const user = userEvent.setup();
    renderConsole(["/"]);

    await screen.findByRole("heading", { name: "Home" });
    expect(await screen.findByText("Blocked OpenClaw attached session")).toBeInTheDocument();
    expect(
      await screen.findByText("Native session requested operator review before proceeding."),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Inbox" }));
    await screen.findByRole("heading", { name: "Inbox" });
    const blockedCard = screen
      .getByText("Blocked OpenClaw attached session")
      .closest("article");
    expect(blockedCard).not.toBeNull();
    expect(
      within(blockedCard as HTMLElement).getByRole("link", { name: "Open run" }),
    ).toHaveAttribute("href", "/runs/del_openclaw_attention");
    expect(screen.getByText("Note from OpenClaw attached session")).toBeInTheDocument();
  });

  it("executes inbox approval actions through the shared action endpoint", async () => {
    const item = {
      id: "approval-request::run_gamma_codex_2::approval_gamma_1",
      kind: "approval-request",
      title: "Approve deploy step",
      reason: "Driver requested approval before deployment.",
      project_id: "gamma",
      run_id: "run_gamma_codex_2",
      approval_id: "approval_gamma_1",
      actions: [
        {
          id: "approval.approve:approval-request::run_gamma_codex_2::approval_gamma_1",
          action_id: "approval.approve",
          title: "Approve Approve deploy step",
          button_label: "Approve",
          description: "Driver requested approval before deployment.",
          group: "Inbox approvals",
          operation: "execute",
          tone: "primary",
          enabled: true,
          availability_reason: "Available because this attention item is a pending approval.",
          availability_source: "pending approval",
          run_id: "run_gamma_codex_2",
          approval_id: "approval_gamma_1",
          input_mode: "note",
          success_message: "Approved Approve deploy step.",
        },
        {
          id: "approval.reject:approval-request::run_gamma_codex_2::approval_gamma_1",
          action_id: "approval.reject",
          title: "Reject Approve deploy step",
          button_label: "Reject",
          description: "Driver requested approval before deployment.",
          group: "Inbox approvals",
          operation: "execute",
          enabled: true,
          availability_reason: "Available because this attention item is a pending approval.",
          availability_source: "pending approval",
          run_id: "run_gamma_codex_2",
          approval_id: "approval_gamma_1",
          input_mode: "note",
          success_message: "Rejected Approve deploy step.",
        },
      ],
    };
    const items = [item];
    const fetchMock = installFetchMock([
      {
        pathname: "/inbox",
        response: () =>
          jsonResponse({
            ok: true,
            items,
          }),
      },
      {
        method: "POST",
        pathname: "/actions/execute",
        response: (_url, init) => {
          const payload = JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>;
          items.splice(0, items.length);
          return jsonResponse({
            ok: true,
            action_id: payload.action_id,
            approval: {
              approval_id: payload.approval_id,
              status: payload.action_id === "approval.approve" ? "approved" : "rejected",
            },
          });
        },
      },
    ]);

    const user = userEvent.setup();
    renderConsole(["/inbox"]);

    await screen.findByRole("heading", { name: "Inbox" });
    const approvalCard = (await screen.findByText("Approve deploy step")).closest("article");
    expect(approvalCard).not.toBeNull();
    expect(
      within(approvalCard as HTMLElement).getByRole("link", { name: "Open run" }),
    ).toHaveAttribute("href", "/runs/run_gamma_codex_2");

    await user.click(within(approvalCard as HTMLElement).getByRole("button", { name: "Approve" }));

    expect(await screen.findByText("Approved Approve deploy step.")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Inbox is clear" })).toBeInTheDocument();
    });

    const postBodies = fetchMock.mock.calls
      .filter(([, init]) => (init?.method ?? "GET").toUpperCase() === "POST")
      .map(([, init]) => JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>);

    expect(postBodies).toEqual([
      {
        action_id: "approval.approve",
        approval_id: "approval_gamma_1",
        actor: "console-operator",
        run_id: "run_gamma_codex_2",
      },
    ]);
  });

  it("groups inbox attention, supports filters, and snoozes items in bulk", async () => {
    installFetchMock([
      {
        pathname: "/inbox",
        response: jsonResponse({
          ok: true,
          items: [
            {
              id: "approval-request::run_gamma_local_1::approval_gamma_1",
              kind: "approval-request",
              title: "Approve Gamma reroute",
              reason: "Driver needs operator approval.",
              severity: "critical",
              severity_label: "Critical",
              decision_type: "approval",
              decision_label: "Approval",
              group_key: "critical:approval",
              group_label: "Critical · Approval",
              notification_tier: "actionable",
              source: "approval",
              bulk_actions: ["resolve", "dismiss", "snooze", "assign"],
              deep_link: "/runs/run_gamma_local_1",
              project_id: "gamma",
              project_label: "Gamma",
              run_id: "run_gamma_local_1",
              run_label: "Gamma launch page",
              approval_id: "approval_gamma_1",
              why_visible: "Gamma launch page is waiting on an explicit operator approval.",
              ignore_impact: "Ignoring this keeps the run blocked.",
            },
            {
              id: "run-blocked::run_gamma_local_2",
              kind: "run-blocked",
              title: "Blocked Gamma polish",
              reason: "Driver hit a release packaging blocker.",
              severity: "high",
              severity_label: "High",
              decision_type: "failure",
              decision_label: "Failure",
              group_key: "high:failure",
              group_label: "High · Failure",
              notification_tier: "actionable",
              source: "run",
              bulk_actions: ["resolve", "dismiss", "snooze", "assign"],
              deep_link: "/runs/run_gamma_local_2",
              project_id: "gamma",
              project_label: "Gamma",
              run_id: "run_gamma_local_2",
              run_label: "Gamma polish pass",
              why_visible: "The run surfaced a failure-level alert.",
              ignore_impact: "Ignoring this can leave the run stalled.",
            },
          ],
          summary: {
            total: 2,
            by_severity: { critical: 1, high: 1 },
            by_decision_type: { approval: 1, failure: 1 },
            by_notification_tier: { actionable: 2 },
          },
        }),
      },
    ]);

    const user = userEvent.setup();
    renderConsole(["/inbox"]);

    await screen.findByRole("heading", { name: "Inbox" });
    expect(await screen.findByRole("heading", { name: "Critical · Approval" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "High · Failure" })).toBeInTheDocument();

    await user.selectOptions(screen.getByRole("combobox", { name: "Severity" }), "high");
    expect(screen.getByText("Blocked Gamma polish")).toBeInTheDocument();
    expect(screen.queryByText("Approve Gamma reroute")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Reset filters" }));
    expect(await screen.findByText("Approve Gamma reroute")).toBeInTheDocument();

    await user.click(screen.getByRole("checkbox", { name: "Select Approve Gamma reroute" }));
    await user.click(screen.getByRole("checkbox", { name: "Select Blocked Gamma polish" }));
    await user.click(screen.getByRole("button", { name: "Snooze selected" }));

    expect(await screen.findByText(/Snoozed 2 attention item\(s\) until/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Inbox is clear" })).toBeInTheDocument();

    await user.click(screen.getByRole("checkbox", { name: "Show snoozed" }));
    expect(await screen.findByText("Approve Gamma reroute")).toBeInTheDocument();
    expect(screen.getByText("Blocked Gamma polish")).toBeInTheDocument();
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
        response: (url) => {
          expect(url.searchParams.get("query")).toBe("program doctor");
          return jsonResponse({
            ok: true,
            results: [
              {
                id: "task_program_doctor",
                kind: "task",
                source: "task",
                source_label: "Tasks",
                title: "Program Doctor hardening",
                summary: "Tighten evaluator guardrails.",
                preview: "Program Doctor requires at least one required evaluator before promotion.",
                why: ["canonical task record", "matched title terms: program, doctor"],
                project_label: "Alpha Project",
                project_id: "alpha",
                path: ".hive/tasks/task_program_doctor.md",
                deep_link: "/projects/alpha",
                open_label: "Open project context",
              },
            ],
          });
        },
      },
    ]);

    const user = userEvent.setup();
    renderConsole(["/projects"]);

    await screen.findByRole("heading", { name: "Projects" });
    expect(
      await screen.findByText("missing_required_evaluator: Add at least one evaluator."),
    ).toBeInTheDocument();
    expect(await screen.findByText("Alpha context preview")).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: /Beta Research Ops/i }));
    await waitFor(() => {
      expect(screen.getByText("Beta context preview")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("link", { name: "Search" }));
    await screen.findByRole("heading", { name: "Search" });
    await user.click(screen.getByRole("button", { name: "Search" }));
    expect(await screen.findAllByText("Program Doctor hardening")).toHaveLength(2);
    expect(screen.getByRole("button", { name: /Program Doctor hardening/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getAllByText("canonical task record")).toHaveLength(2);
    expect(screen.getByRole("link", { name: "Open project context" })).toHaveAttribute(
      "href",
      "/projects/alpha?query=program+doctor",
    );
    expect(
      screen.getByText("Program Doctor requires at least one required evaluator before promotion."),
    ).toBeInTheDocument();
  });

  it("exposes the full v2.5 shell surfaces with stable deep-link navigation", async () => {
    installFetchMock([
      {
        pathname: "/notifications",
        response: jsonResponse({
          ok: true,
          items: [
            {
              kind: "approval-request",
              title: "Review the shell route contract",
              reason: "A fresh operator signoff is needed.",
              project_id: "hive-v25",
              run_id: "run_shell_contract",
              approval_id: "approval_shell_contract",
            },
            {
              kind: "accepted-run",
              title: "Accepted shell routing foundation",
              reason: "Shell routing landed on codex.",
              project_id: "hive-v25",
              run_id: "run_shell_contract",
              severity: "info",
              severity_label: "Info",
              decision_type: "informational",
              decision_label: "Informational",
              group_key: "info:informational",
              group_label: "Info · Informational",
              notification_tier: "informational",
              source: "run",
              bulk_actions: ["dismiss", "snooze", "assign"],
              deep_link: "/runs/run_shell_contract",
              project_label: "Hive v2.5",
              run_label: "Publish the shell route contract",
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
        }),
      },
      {
        pathname: "/activity",
        response: jsonResponse({
          ok: true,
          items: [
            {
              id: "activity_event_shell",
              kind: "event",
              title: "Canonical /home route published.",
              summary: "Stable browser deep link shipped.",
              occurred_at: "2026-04-06T21:00:00Z",
              project_id: "hive-v25",
              project_label: "Hive v2.5",
              run_id: "run_shell_contract",
              deep_link: "/runs/run_shell_contract",
            },
            {
              id: "activity_accept_shell",
              kind: "accepted-run",
              title: "Accepted Publish the shell route contract",
              summary: "Publish the shell route contract was accepted on codex.",
              occurred_at: "2026-04-06T20:30:00Z",
              project_id: "hive-v25",
              project_label: "Hive v2.5",
              run_id: "run_shell_contract",
              deep_link: "/runs/run_shell_contract",
            },
          ],
          summary: { total: 2 },
        }),
      },
      {
        pathname: "/integrations",
        response: jsonResponse({
          ok: true,
          backends: [
            {
              adapter: "openclaw",
              adapter_type: "delegate_gateway",
              integration_level: "attach",
              governance_mode: "governed",
              available: true,
            },
          ],
        }),
      },
      {
        pathname: "/integrations/openclaw",
        response: jsonResponse({
          ok: true,
          integration: {
            adapter: "openclaw",
            adapter_family: "delegate_gateway",
            integration_level: "attach",
            governance_mode: "governed",
            version: "2.4.0",
            available: true,
            notes: ["OpenClaw gateway is attached and ready."],
            next_steps: ["Open a native session from the run detail page."],
          },
        }),
      },
    ]);

    const user = userEvent.setup();
    renderConsole([
      "/settings?apiBase=http://127.0.0.1:8787&workspace=/tmp/hive-demo",
    ]);

    await screen.findByRole("heading", { name: "Settings" });
    expect(screen.getByRole("link", { name: "Runs" })).toHaveAttribute(
      "href",
      expect.stringContaining(
        "/runs?apiBase=http://127.0.0.1:8787&workspace=/tmp/hive-demo",
      ),
    );
    expect(screen.getByText("Keyboard shortcut help")).toBeInTheDocument();
    expect(screen.getByLabelText("Show informational notifications")).toBeChecked();

    await user.click(screen.getByLabelText("Show informational notifications"));
    expect(screen.getByLabelText("Show informational notifications")).not.toBeChecked();

    await user.click(screen.getByRole("link", { name: "Notifications" }));
    await screen.findByRole("heading", { name: "Notifications" });
    expect(await screen.findByText("Review the shell route contract")).toBeInTheDocument();
    expect(screen.queryByText("Accepted shell routing foundation")).not.toBeInTheDocument();
    expect(screen.getByText("Actionable: 1 • Informational: 1")).toBeInTheDocument();
    expect(screen.getByText(/Filtered by local preferences/i)).toBeInTheDocument();
    expect(screen.getByText(/Hidden items: 1/i)).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Activity" }));
    await screen.findByRole("heading", { name: "Activity" });
    expect(await screen.findByText("Canonical /home route published.")).toBeInTheDocument();
    expect(await screen.findByText("Accepted Publish the shell route contract")).toBeInTheDocument();
    expect(screen.getByText("Events: 1 • Accepted runs: 1")).toBeInTheDocument();
    expect(screen.getByText("Hive v2.5 • 2 items")).toBeInTheDocument();

    fireEvent.keyDown(window, { key: "?" });
    await screen.findByRole("heading", { name: "Settings" });
    expect(screen.getByText("Keyboard shortcut help")).toBeInTheDocument();

    await user.click(screen.getByRole("link", { name: "Integrations" }));
    await screen.findByRole("heading", { name: "Integrations" });
    expect(await screen.findByText("OpenClaw gateway is attached and ready.")).toBeInTheDocument();
    expect(screen.getByText("Open a native session from the run detail page.")).toBeInTheDocument();
  });

  it("sends typed live steering actions from run detail and refreshes the audit view", async () => {
    const steeringHistory: Array<Record<string, unknown>> = [];
    const timeline: Array<Record<string, unknown>> = [];
    const runId = "run_gamma_local_1";
    const eventTypeByAction: Record<string, string> = {
      "run.pause": "steering.pause",
      "run.note": "steering.note",
      "run.cancel": "steering.cancel",
      "run.reroute": "steering.rerouted",
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
              actions: [
                {
                  id: `run.pause:${runId}`,
                  action_id: "run.pause",
                  title: "Pause",
                  description: "Pause a live attached run without losing the current execution context.",
                  group: "Run controls",
                  operation: "execute",
                  tone: "primary",
                  enabled: true,
                  visible: true,
                  availability_reason: "Available because the run is live, steerable, and not already paused.",
                  availability_source: "run capability snapshot",
                  run_id: runId,
                  input_mode: "reason_note",
                  success_message: `Sent pause for ${runId}.`,
                },
                {
                  id: `run.note:${runId}`,
                  action_id: "run.note",
                  title: "Add Note",
                  description: "Append an operator note to the live run audit trail.",
                  group: "Run controls",
                  operation: "execute",
                  enabled: true,
                  visible: true,
                  availability_reason: "Available because the run supports live annotations.",
                  availability_source: "run capability snapshot",
                  run_id: runId,
                  input_mode: "reason_note",
                  success_message: `Sent note for ${runId}.`,
                },
                {
                  id: `run.cancel:${runId}`,
                  action_id: "run.cancel",
                  title: "Cancel",
                  description: "Cancel the run from Hive's side and record the operator intent.",
                  group: "Run controls",
                  operation: "execute",
                  tone: "danger",
                  enabled: true,
                  visible: true,
                  availability_reason: "Available because the run is not yet terminal.",
                  availability_source: "run status",
                  run_id: runId,
                  input_mode: "reason_note",
                  success_message: `Sent cancel for ${runId}.`,
                },
                {
                  id: `run.reroute:${runId}`,
                  action_id: "run.reroute",
                  title: "Reroute",
                  description: "Reroute this run to a different driver.",
                  group: "Run controls",
                  operation: "execute",
                  tone: "primary",
                  enabled: true,
                  visible: true,
                  availability_reason: "Available because the run can still move to a different driver.",
                  availability_source: "run status",
                  run_id: runId,
                  input_mode: "reroute",
                  success_message: `Sent reroute for ${runId}.`,
                },
              ],
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
        pathname: `/runs/${runId}/compare`,
        response: makeRunComparisonResponse({
          currentRunId: runId,
          currentTitle: "Gamma launch page",
          currentDriver: "local",
          currentChangedPaths: ["src/App.tsx"],
          evaluationSummary: { total: 1, by_status: { passed: 1 } },
        }),
      },
      {
        method: "POST",
        pathname: "/actions/execute",
        response: (_url, init) => {
          const payload = JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>;
          const eventType = eventTypeByAction[String(payload.action_id)];
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
    const runBriefTab = screen.getByRole("tab", { name: "Run brief" });
    runBriefTab.focus();
    fireEvent.keyDown(runBriefTab, { key: "ArrowRight" });
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "Summary" })).toHaveAttribute("aria-selected", "true");
    });
    expect(screen.getByRole("tabpanel", { name: "Summary" })).toHaveTextContent(
      "Waiting for reroute decision.",
    );
    fireEvent.keyDown(screen.getByRole("tab", { name: "Summary" }), { key: "End" });
    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "stderr" })).toHaveAttribute("aria-selected", "true");
    });
    expect(screen.getByRole("tabpanel", { name: "stderr" })).toHaveTextContent(
      "No stderr recorded yet.",
    );
    const steeringPanel = screen.getByRole("heading", { name: "Steering History" }).closest("section");
    const timelinePanel = screen.getByRole("heading", { name: "Timeline" }).closest("section");
    expect(steeringPanel).not.toBeNull();
    expect(timelinePanel).not.toBeNull();

    async function triggerAction(action: string, reason: string, actionId: string) {
      const reasonBox = await screen.findByRole("textbox", { name: "Reason" });
      fireEvent.change(reasonBox, { target: { value: reason } });
      await user.click(screen.getByRole("button", { name: action }));
      expect(
        await screen.findByText(`Sent ${actionId.split(".").at(-1)} for ${runId}.`),
      ).toBeInTheDocument();
      expect(
        await within(steeringPanel as HTMLElement).findByText(eventTypeByAction[actionId]),
      ).toBeInTheDocument();
      expect(
        await within(timelinePanel as HTMLElement).findByText(eventTypeByAction[actionId]),
      ).toBeInTheDocument();
    }

    await triggerAction("Pause", "Need a pause before rerouting.", "run.pause");
    await triggerAction("Add Note", "Leave a note for the next turn.", "run.note");
    await triggerAction("Cancel", "Stop this run before reassigning it.", "run.cancel");

    const reasonBox = await screen.findByRole("textbox", { name: "Reason" });
    const noteBox = await screen.findByRole("textbox", { name: "Note" });
    fireEvent.change(reasonBox, { target: { value: "Switch this run to Codex." } });
    fireEvent.change(noteBox, { target: { value: "Need stronger repo-wide reasoning." } });
    await user.selectOptions(await screen.findByRole("combobox", { name: "Reroute to" }), "codex");
    await user.click(await screen.findByRole("button", { name: "Reroute" }));

    expect(await screen.findByText(`Sent reroute for ${runId}.`)).toBeInTheDocument();
    expect(await within(steeringPanel as HTMLElement).findByText("steering.rerouted")).toBeInTheDocument();
    expect(await within(timelinePanel as HTMLElement).findByText("steering.rerouted")).toBeInTheDocument();

    const postBodies = fetchMock.mock.calls
      .filter(([, init]) => (init?.method ?? "GET").toUpperCase() === "POST")
      .map(([, init]) => JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>);

    expect(postBodies).toEqual([
      {
        action_id: "run.pause",
        actor: "console-operator",
        reason: "Need a pause before rerouting.",
        run_id: runId,
      },
      {
        action_id: "run.note",
        actor: "console-operator",
        reason: "Leave a note for the next turn.",
        run_id: runId,
      },
      {
        action_id: "run.cancel",
        actor: "console-operator",
        reason: "Stop this run before reassigning it.",
        run_id: runId,
      },
      {
        action_id: "run.reroute",
        actor: "console-operator",
        reason: "Switch this run to Codex.",
        note: "Need stronger repo-wide reasoning.",
        run_id: runId,
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
        pathname: `/runs/${runId}/compare`,
        response: makeRunComparisonResponse({
          currentRunId: runId,
          currentTitle: "Alpha codex slice",
          currentChangedPaths: ["src/app.tsx"],
          currentOnly: ["src/app.tsx"],
          baselineRunId: "run_alpha_codex_accepted",
          baselineTitle: "Accepted alpha baseline",
          baselineChangedPaths: ["src/app.tsx", "README.md"],
          baselineOnly: ["README.md"],
          hasBaseline: true,
          evaluationSummary: { total: 1, by_status: { passed: 1 } },
        }),
      },
      {
        method: "POST",
        pathname: "/actions/execute",
        response: (_url, init) => {
          const payload = JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>;
          const approvalId = String(payload.approval_id);
          const resolution =
            payload.action_id === "approval.approve" ? "approved" : "rejected";
          const approvalIndex = approvals.findIndex(
            (approval) => approval.approval_id === approvalId,
          );
          approvals[approvalIndex] = { ...approvals[approvalIndex], status: resolution };
          return jsonResponse({
            ok: true,
            action_id: payload.action_id,
            approval: { approval_id: approvalId, status: resolution },
          });
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
    expect(screen.getByRole("heading", { name: "Capability and Sandbox" })).toBeInTheDocument();
    expect(screen.getByText("Capability snapshot")).toBeInTheDocument();
    expect(screen.getByText("Sandbox policy")).toBeInTheDocument();
    expect(screen.getByText("Retrieval trace")).toBeInTheDocument();
    expect(screen.getByText("Approve git status")).toBeInTheDocument();
    expect(screen.getByText("Reject rm -rf /tmp/demo")).toBeInTheDocument();
    expect(screen.getByText("PROGRAM.md — program policy outranked general docs")).toBeInTheDocument();
    expect(screen.getByText("Accepted alpha baseline")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open baseline run" })).toBeInTheDocument();
    expect(screen.getAllByText("Approval payload")).toHaveLength(2);

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

    const approvalCalls = fetchMock.mock.calls
      .filter(([, init]) => (init?.method ?? "GET").toUpperCase() === "POST")
      .map(([, init]) => JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>);
    expect(approvalCalls).toEqual([
      {
        action_id: "approval.approve",
        approval_id: "approval_1",
        actor: "console-operator",
        run_id: runId,
      },
      {
        action_id: "approval.reject",
        approval_id: "approval_2",
        actor: "console-operator",
        run_id: runId,
      },
    ]);
  });

  it("renders delegate detail truth surfaces for attached advisory sessions", async () => {
    const runId = "del_openclaw_live";
    installFetchMock([
      {
        pathname: `/runs/${runId}`,
        response: jsonResponse({
          ok: true,
          detail: {
            detail_kind: "delegate_session",
            run: {
              id: runId,
              project_id: "alpha",
              driver: "openclaw",
              status: "attached",
              health: "healthy",
              started_at: "2026-03-29T15:40:00Z",
              finished_at: null,
              metadata_json: { task_title: "OpenClaw attached session" },
            },
            promotion_decision: {},
            artifact_preview: {
              trajectory: '[{"kind":"assistant_message"}]',
              steering: '[{"action":"note"}]',
            },
            inspector: {
              capability_snapshot: {
                driver: "openclaw",
                adapter_family: "delegate_gateway",
                governance_mode: "advisory",
                integration_level: "attach",
                effective: {
                  launch_mode: "gateway_bridge",
                  session_persistence: "persistent",
                  event_stream: "structured_deltas",
                  approvals: [],
                  artifacts: ["trajectory", "session-history"],
                },
              },
            },
            capability_snapshot: {
              driver: "openclaw",
              adapter_family: "delegate_gateway",
              governance_mode: "advisory",
              integration_level: "attach",
              effective: {
                launch_mode: "gateway_bridge",
                session_persistence: "persistent",
                event_stream: "structured_deltas",
                approvals: [],
                artifacts: ["trajectory", "session-history"],
              },
            },
            sandbox_policy: {},
            retrieval_trace: {},
            context_manifest: {},
            approvals: [],
            steering_history: [
              {
                event_id: "steering-1",
                type: "steering.note_added",
                ts: "2026-03-29T15:41:00Z",
                payload: { note: "Note from Hive" },
              },
            ],
            trajectory: [
              {
                seq: 0,
                kind: "assistant_message",
                harness: "openclaw",
                adapter_family: "delegate_gateway",
                native_session_ref: "oc-session-001",
                payload: { text: "delta" },
                ts: "2026-03-29T15:40:30Z",
              },
            ],
            timeline: [
              {
                event_id: "trajectory-0",
                type: "trajectory.assistant_message",
                ts: "2026-03-29T15:40:30Z",
                payload: { text: "delta" },
              },
            ],
            evaluations: [],
            changed_files: {},
            context_entries: [],
            harness: "openclaw",
            integration_level: "attach",
            governance_mode: "advisory",
            adapter_family: "delegate_gateway",
            native_session_handle: "oc-session-001",
            sandbox_owner: "openclaw",
          },
        }),
      },
      {
        pathname: `/runs/${runId}/compare`,
        response: makeRunComparisonResponse({
          currentRunId: runId,
          currentTitle: "OpenClaw attached session",
          currentDriver: "openclaw",
          currentChangedPaths: [],
        }),
      },
    ]);

    renderConsole([`/runs/${runId}`]);

    await screen.findByRole("heading", { name: runId });
    const runtimePanel = screen
      .getByRole("heading", { name: "Capability and Sandbox" })
      .closest("section");
    expect(runtimePanel).not.toBeNull();
    await expectKeyValue(runtimePanel as HTMLElement, "Harness", "openclaw");
    await expectKeyValue(runtimePanel as HTMLElement, "Integration level", "attach");
    await expectKeyValue(runtimePanel as HTMLElement, "Governance mode", "advisory");
    await expectKeyValue(runtimePanel as HTMLElement, "Native session", "oc-session-001");
    expect(screen.getByText("Capability snapshot")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Steering History" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Normalized history" })).toBeInTheDocument();
    expect(screen.getByText(/attached delegate session/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Pause" })).not.toBeInTheDocument();
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
      {
        pathname: `/runs/${runId}/compare`,
        response: makeRunComparisonResponse({
          currentRunId: runId,
          currentTitle: "Legacy local run",
          currentDriver: "local",
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
      {
        pathname: `/runs/${runId}/compare`,
        response: makeRunComparisonResponse({
          currentRunId: runId,
          currentTitle: "Alpha codex slice",
          currentChangedPaths: ["src/app.tsx"],
          currentOnly: ["src/app.tsx"],
          baselineRunId: "run_alpha_codex_accepted",
          baselineTitle: "Accepted alpha baseline",
          baselineChangedPaths: ["src/app.tsx", "README.md"],
          baselineOnly: ["README.md"],
          hasBaseline: true,
          evaluationSummary: { total: 1, by_status: { passed: 1 } },
        }),
      },
    ]);

    const first = renderConsole([`/runs/${runId}`]);

    await screen.findByRole("heading", { name: runId });
    // The reroute event is rendered in Steering History, Timeline, and the selected timeline event rail.
    expect(await screen.findAllByText("steering.rerouted")).toHaveLength(3);
    expect(screen.getByText("Follow the prepared Codex run brief.")).toBeInTheDocument();
    expect(screen.getByText("Accepted alpha baseline")).toBeInTheDocument();

    first.unmount();

    renderConsole([`/runs/${runId}`]);

    await screen.findByRole("heading", { name: runId });
    // The reroute event is rendered in Steering History, Timeline, and the selected timeline event rail.
    expect(await screen.findAllByText("steering.rerouted")).toHaveLength(3);
    expect(screen.getByText(/Alpha launch copy/)).toBeInTheDocument();

    const detailCalls = fetchMock.mock.calls.filter(([input]) => {
      const url = new URL(typeof input === "string" ? input : input instanceof URL ? input : input.url);
      return url.pathname === `/runs/${runId}`;
    });
    expect(detailCalls.length).toBeGreaterThanOrEqual(2);
  });
});
