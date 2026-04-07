import { describe, expect, it } from "vitest";

import {
  CONSOLE_PREFERENCES_KEY,
  DEFAULT_ATTENTION_FILTERS,
  DEFAULT_RUNS_FILTERS,
  MAX_ATTENTION_TRIAGE_ITEMS,
  MAX_RECENT_WORKSPACES,
  MAX_SAVED_ATTENTION_VIEWS,
  MAX_SAVED_RUNS_VIEWS,
  deleteSavedAttentionView,
  deleteSavedRunsView,
  loadConsolePreferences,
  normalizeConsolePreferences,
  rememberRecentWorkspace,
  saveConsolePreferences,
  setAttentionFilters,
  updateAttentionTriage,
  upsertSavedAttentionView,
  upsertSavedRunsView,
} from "../preferences";

describe("console preferences", () => {
  it("falls back to defaults when the saved payload is invalid", () => {
    window.localStorage.setItem(CONSOLE_PREFERENCES_KEY, "{not-json");

    const preferences = loadConsolePreferences();

    expect(preferences.theme).toBe("clay");
    expect(preferences.density).toBe("comfortable");
    expect(preferences.defaultPage).toBe("home");
    expect(preferences.runs.filters).toEqual(DEFAULT_RUNS_FILTERS);
  });

  it("normalizes partial payloads without leaking unknown values", () => {
    const preferences = normalizeConsolePreferences({
      theme: "ledger",
      density: "compact",
      defaultPage: "runs",
      runs: {
        filters: {
          projectId: "gamma",
          driver: "codex",
        },
        hiddenColumns: ["campaign"],
        pinnedPanels: ["filters"],
      },
    });

    expect(preferences.theme).toBe("ledger");
    expect(preferences.density).toBe("compact");
    expect(preferences.defaultPage).toBe("runs");
    expect(preferences.recentWorkspaces).toEqual([]);
    expect(preferences.runs.filters).toEqual({
      projectId: "gamma",
      driver: "codex",
      health: "",
      campaignId: "",
    });
    expect(preferences.runs.hiddenColumns).toEqual(["campaign"]);
    expect(preferences.runs.pinnedPanels).toEqual(["filters"]);
    expect(preferences.attention.filters).toEqual(DEFAULT_ATTENTION_FILTERS);
  });

  it("saves, updates, and deletes saved views by name", () => {
    const first = upsertSavedRunsView(
      loadConsolePreferences(),
      "Gamma incidents",
      { ...DEFAULT_RUNS_FILTERS, projectId: "gamma" },
    );
    const second = upsertSavedRunsView(
      first,
      "Gamma incidents",
      { ...DEFAULT_RUNS_FILTERS, projectId: "gamma", health: "failed" },
    );

    saveConsolePreferences(second);
    const reloaded = loadConsolePreferences();
    expect(reloaded.runs.savedViews).toHaveLength(1);
    expect(reloaded.runs.savedViews[0]?.filters.health).toBe("failed");

    const deleted = deleteSavedRunsView(reloaded, reloaded.runs.savedViews[0]!.id);
    expect(deleted.runs.savedViews).toHaveLength(0);
  });

  it("caps saved views to the newest fifty entries", () => {
    let preferences = loadConsolePreferences({ getItem: () => null });

    for (let index = 0; index < MAX_SAVED_RUNS_VIEWS + 5; index += 1) {
      preferences = upsertSavedRunsView(
        preferences,
        `View ${index}`,
        { ...DEFAULT_RUNS_FILTERS, projectId: `project-${index}` },
      );
    }

    expect(preferences.runs.savedViews).toHaveLength(MAX_SAVED_RUNS_VIEWS);
    expect(preferences.runs.savedViews[0]?.name).toBe("View 5");
    expect(preferences.runs.savedViews.at(-1)?.name).toBe("View 54");
  });

  it("normalizes attention filters, saved views, and triage state", () => {
    const preferences = normalizeConsolePreferences({
      attention: {
        filters: {
          severity: "critical",
          decisionType: "approval",
          showSnoozed: true,
        },
        savedViews: [
          {
            name: "Critical approvals",
            filters: {
              severity: "critical",
              decisionType: "approval",
              tier: "actionable",
            },
          },
        ],
        triageByItemId: {
          attention_1: {
            disposition: "dismissed",
            assignee: "me",
            snoozedUntil: "2026-04-07T12:00:00Z",
            updatedAt: "2026-04-07T11:00:00Z",
          },
          broken: {
            disposition: "unknown",
          },
        },
      },
    });

    expect(preferences.attention.filters).toEqual({
      ...DEFAULT_ATTENTION_FILTERS,
      severity: "critical",
      decisionType: "approval",
      showSnoozed: true,
    });
    expect(preferences.attention.savedViews).toHaveLength(1);
    expect(preferences.attention.savedViews[0]?.name).toBe("Critical approvals");
    expect(preferences.attention.triageByItemId).toEqual({
      attention_1: {
        disposition: "dismissed",
        assignee: "me",
        snoozedUntil: "2026-04-07T12:00:00Z",
        updatedAt: "2026-04-07T11:00:00Z",
      },
    });
  });

  it("saves, caps, and deletes attention views while persisting triage state", () => {
    let preferences = loadConsolePreferences({ getItem: () => null });

    preferences = setAttentionFilters(preferences, {
      ...DEFAULT_ATTENTION_FILTERS,
      severity: "high",
      source: "delegate",
    });
    preferences = updateAttentionTriage(preferences, "attention_1", {
      disposition: "resolved",
      assignee: "release-captain",
      snoozedUntil: "2026-04-07T12:00:00Z",
    });

    for (let index = 0; index < MAX_SAVED_ATTENTION_VIEWS + 4; index += 1) {
      preferences = upsertSavedAttentionView(
        preferences,
        `Attention ${index}`,
        { ...DEFAULT_ATTENTION_FILTERS, severity: index % 2 === 0 ? "high" : "critical" },
      );
    }

    expect(preferences.attention.filters.source).toBe("delegate");
    expect(preferences.attention.triageByItemId.attention_1?.disposition).toBe("resolved");
    expect(preferences.attention.savedViews).toHaveLength(MAX_SAVED_ATTENTION_VIEWS);
    expect(preferences.attention.savedViews[0]?.name).toBe("Attention 4");

    const deleted = deleteSavedAttentionView(
      preferences,
      preferences.attention.savedViews[0]!.id,
    );
    expect(deleted.attention.savedViews).toHaveLength(MAX_SAVED_ATTENTION_VIEWS - 1);
  });

  it("caps persisted attention triage state to the newest entries", () => {
    let preferences = loadConsolePreferences({ getItem: () => null });

    for (let index = 0; index < MAX_ATTENTION_TRIAGE_ITEMS + 5; index += 1) {
      preferences = updateAttentionTriage(preferences, `attention_${index}`, {
        disposition: index % 2 === 0 ? "dismissed" : "resolved",
      });
    }

    expect(Object.keys(preferences.attention.triageByItemId)).toHaveLength(MAX_ATTENTION_TRIAGE_ITEMS);
    expect(preferences.attention.triageByItemId.attention_0).toBeUndefined();
    expect(preferences.attention.triageByItemId[`attention_${MAX_ATTENTION_TRIAGE_ITEMS + 4}`]?.disposition)
      .toBe("dismissed");
  });

  it("keeps a unique, capped recent-workspace list", () => {
    let preferences = loadConsolePreferences({ getItem: () => null });

    for (let index = 0; index < MAX_RECENT_WORKSPACES + 3; index += 1) {
      preferences = rememberRecentWorkspace(preferences, `/tmp/workspace-${index}`);
    }
    preferences = rememberRecentWorkspace(preferences, "/tmp/workspace-3");

    expect(preferences.recentWorkspaces).toHaveLength(MAX_RECENT_WORKSPACES);
    expect(preferences.recentWorkspaces[0]).toBe("/tmp/workspace-3");
    expect(preferences.recentWorkspaces).not.toContain("/tmp/workspace-0");
  });
});
