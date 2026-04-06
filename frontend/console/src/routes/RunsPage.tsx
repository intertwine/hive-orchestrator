import { useState } from "react";

import { createConsoleClient } from "../api/client";
import { useConsolePreferences } from "../components/ConsolePreferences";
import { Panel } from "../components/Panel";
import { RunCard } from "../components/RunCard";
import { useConsoleConfig } from "../components/ConsoleLayout";
import { useConsoleQuery } from "../hooks/useConsoleQuery";
import {
  sameRunsFilters,
  type RunsFiltersPreference,
} from "../preferences";

export function RunsPage() {
  const { apiBase, workspacePath } = useConsoleConfig();
  const {
    preferences,
    deleteRunsView,
    resetRunsFilters,
    saveRunsView,
    setRunsFilters,
  } = useConsolePreferences();
  const [viewName, setViewName] = useState("");
  const filters = preferences.runs.filters;
  const client = createConsoleClient(apiBase, workspacePath);
  const { data, loading, error } = useConsoleQuery(
    `runs:${apiBase}:${workspacePath}:${filters.driver}:${filters.health}:${filters.projectId}:${filters.campaignId}`,
    () =>
      client.getRuns({
        driver: filters.driver || undefined,
        health: filters.health || undefined,
        projectId: filters.projectId || undefined,
        campaignId: filters.campaignId || undefined,
      }),
    3000,
  );
  const runs = Array.isArray(data?.runs) ? data.runs : [];
  const activeView = preferences.runs.savedViews.find((view) =>
    sameRunsFilters(view.filters, filters)
  ) ?? null;

  function updateFilters(partial: Partial<RunsFiltersPreference>) {
    setRunsFilters({ ...filters, ...partial });
  }

  function applySavedView(viewId: string) {
    const view = preferences.runs.savedViews.find((entry) => entry.id === viewId);
    if (!view) {
      return;
    }
    setRunsFilters(view.filters);
    setViewName(view.name);
  }

  function handleSaveView() {
    const fallbackName = activeView?.name ?? [
      filters.projectId || "all-projects",
      filters.driver || "all-drivers",
      filters.health || "any-health",
    ].join(" · ");
    const nextName = viewName.trim() || fallbackName;
    saveRunsView(nextName, filters);
    setViewName(nextName);
  }

  function handleResetFilters() {
    resetRunsFilters();
  }

  return (
    <Panel eyebrow="Unified runs board" title="Runs">
      <div className="saved-views">
        <div className="saved-views__header">
          <div>
            <p className="eyebrow">Saved views</p>
            <p className="saved-views__copy">
              Persist run filters locally so one operator can bounce between review queues without
              rebuilding the same view every time.
            </p>
          </div>
          <div className="saved-views__actions">
            <label className="console-field saved-views__field">
              <span>View name</span>
              <input
                placeholder="Gamma incidents"
                value={viewName}
                onChange={(event) => setViewName(event.target.value)}
              />
            </label>
            <button className="primary-button" type="button" onClick={handleSaveView}>
              Save current view
            </button>
            <button className="secondary-button" type="button" onClick={handleResetFilters}>
              Reset filters
            </button>
          </div>
        </div>

        <div className="saved-views__list">
          {preferences.runs.savedViews.length ? (
            preferences.runs.savedViews.map((view) => (
              <article
                className={`saved-view-card${activeView?.id === view.id ? " saved-view-card--active" : ""}`}
                key={view.id}
              >
                <div>
                  <p className="saved-view-card__title">{view.name}</p>
                  <p className="saved-view-card__meta">
                    {view.filters.projectId || "all projects"} ·{" "}
                    {view.filters.driver || "all drivers"} ·{" "}
                    {view.filters.health || "any health"}
                  </p>
                </div>
                <div className="saved-view-card__actions">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => applySavedView(view.id)}
                  >
                    {activeView?.id === view.id ? "Active" : "Apply"}
                  </button>
                  <button
                    className="danger-button"
                    type="button"
                    onClick={() => deleteRunsView(view.id)}
                  >
                    Delete
                  </button>
                </div>
              </article>
            ))
          ) : (
            <p className="saved-views__empty">
              No saved views yet. Save the filters you revisit most.
            </p>
          )}
        </div>
      </div>

      <div className="filters">
        <label className="console-field">
          <span>Project</span>
          <input
            placeholder="demo"
            value={filters.projectId}
            onChange={(event) => updateFilters({ projectId: event.target.value })}
          />
        </label>
        <label className="console-field">
          <span>Driver</span>
          <select
            value={filters.driver}
            onChange={(event) => updateFilters({ driver: event.target.value })}
          >
            <option value="">All drivers</option>
            <option value="local">local</option>
            <option value="manual">manual</option>
            <option value="pi">pi</option>
            <option value="codex">codex</option>
            <option value="claude-code">claude-code</option>
            <option value="openclaw">openclaw</option>
            <option value="hermes">hermes</option>
          </select>
        </label>
        <label className="console-field">
          <span>Campaign</span>
          <input
            placeholder="campaign_..."
            value={filters.campaignId}
            onChange={(event) => updateFilters({ campaignId: event.target.value })}
          />
        </label>
        <label className="console-field">
          <span>Health</span>
          <select
            value={filters.health}
            onChange={(event) => updateFilters({ health: event.target.value })}
          >
            <option value="">Any health</option>
            <option value="healthy">healthy</option>
            <option value="paused">paused</option>
            <option value="blocked">blocked</option>
            <option value="failed">failed</option>
          </select>
        </label>
      </div>

      {loading ? <p>Loading Runs…</p> : null}
      {error ? <p className="error-copy">{error}</p> : null}
      <div className="card-grid">
        {runs.length ? (
          runs.map((run) => <RunCard key={String((run as Record<string, unknown>).id)} run={run as Record<string, unknown>} />)
        ) : (
          <p>No runs match the current filters.</p>
        )}
      </div>
    </Panel>
  );
}
