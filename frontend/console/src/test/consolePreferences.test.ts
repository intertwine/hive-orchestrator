import { describe, expect, it } from "vitest";

import {
  CONSOLE_PREFERENCES_KEY,
  DEFAULT_RUNS_FILTERS,
  deleteSavedRunsView,
  loadConsolePreferences,
  normalizeConsolePreferences,
  saveConsolePreferences,
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
    expect(preferences.runs.filters).toEqual({
      projectId: "gamma",
      driver: "codex",
      health: "",
      campaignId: "",
    });
    expect(preferences.runs.hiddenColumns).toEqual(["campaign"]);
    expect(preferences.runs.pinnedPanels).toEqual(["filters"]);
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
});
