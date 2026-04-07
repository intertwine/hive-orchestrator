import { describe, expect, it } from "vitest";

import {
  collectDesktopNotificationSnapshot,
  externalConsoleHrefFromUrl,
} from "../desktopShell";
import type { AttentionItem } from "../attention";

function attentionItem(overrides: Partial<AttentionItem> = {}): AttentionItem {
  return {
    actions: [],
    approvalId: "",
    bulkActions: [],
    decisionLabel: "Approval",
    decisionType: "approval",
    deepLink: "/runs/run_demo",
    groupKey: "critical:approval",
    groupLabel: "Critical · Approval",
    id: "attention-demo",
    ignoreImpact: "Ignoring this only changes local queue state.",
    notificationTier: "actionable",
    occurredAt: "2026-04-07T09:30:00Z",
    projectId: "demo",
    projectLabel: "Demo",
    reason: "Needs attention",
    runId: "run_demo",
    runLabel: "Demo run",
    severity: "critical",
    severityLabel: "Critical",
    source: "workspace",
    status: "pending",
    summary: "Approval needed",
    title: "Demo approval",
    whyVisible: "Approval is pending.",
    ...overrides,
  };
}

describe("externalConsoleHrefFromUrl", () => {
  it("maps custom-scheme run links to console routes", () => {
    expect(externalConsoleHrefFromUrl("agent-hive://runs/run_demo?workspace=/tmp/demo")).toBe(
      "/runs/run_demo?workspace=%2Ftmp%2Fdemo",
    );
  });

  it("maps task deep links onto the search surface", () => {
    expect(
      externalConsoleHrefFromUrl("agent-hive://tasks/task_123?workspace=/tmp/demo"),
    ).toBe("/search?source=task&query=task_123&workspace=%2Ftmp%2Fdemo");
  });

  it("normalizes browser console links into browser-parity routes", () => {
    expect(
      externalConsoleHrefFromUrl(
        "http://127.0.0.1:8787/console/campaigns/campaign_demo?apiBase=http://127.0.0.1:8787",
      ),
    ).toBe("/campaigns/campaign_demo?apiBase=http%3A%2F%2F127.0.0.1%3A8787");
  });

  it("ignores unknown paths and unsupported protocols", () => {
    expect(externalConsoleHrefFromUrl("mailto:demo@example.com")).toBeNull();
    expect(externalConsoleHrefFromUrl("agent-hive://unknown/path")).toBeNull();
  });
});

describe("collectDesktopNotificationSnapshot", () => {
  it("treats the first actionable snapshot as baseline without spamming", () => {
    const first = collectDesktopNotificationSnapshot(
      [attentionItem({ id: "attention-1" })],
      new Set<string>(),
      false,
    );

    expect(first.initialized).toBe(true);
    expect(first.candidates).toEqual([]);
    expect(Array.from(first.knownKeys)).toEqual(["attention-1"]);
  });

  it("emits only newly actionable items after baseline", () => {
    const baseline = collectDesktopNotificationSnapshot(
      [attentionItem({ id: "attention-1" })],
      new Set<string>(),
      false,
    );

    const next = collectDesktopNotificationSnapshot(
      [
        attentionItem({ id: "attention-1" }),
        attentionItem({ id: "attention-2", deepLink: "/campaigns/campaign_demo" }),
        attentionItem({
          id: "attention-3",
          deepLink: "/runs/run_info",
          notificationTier: "informational",
        }),
      ],
      baseline.knownKeys,
      baseline.initialized,
    );

    expect(next.candidates).toHaveLength(1);
    expect(next.candidates[0]).toMatchObject({
      href: "/campaigns/campaign_demo",
      title: "Demo approval",
    });
  });
});
