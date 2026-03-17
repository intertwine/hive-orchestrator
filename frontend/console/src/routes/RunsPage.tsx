import { type ChangeEvent, useState } from "react";

import { createConsoleClient } from "../api/client";
import { Panel } from "../components/Panel";
import { RunCard } from "../components/RunCard";
import { useConsoleConfig } from "../components/ConsoleLayout";
import { useConsoleQuery } from "../hooks/useConsoleQuery";

export function RunsPage() {
  const { apiBase, workspacePath } = useConsoleConfig();
  const [driver, setDriver] = useState("");
  const [health, setHealth] = useState("");
  const [projectId, setProjectId] = useState("");
  const [campaignId, setCampaignId] = useState("");
  const client = createConsoleClient(apiBase, workspacePath);
  const { data, loading, error } = useConsoleQuery(
    `runs:${apiBase}:${workspacePath}:${driver}:${health}:${projectId}:${campaignId}`,
    () =>
      client.getRuns({
        driver: driver || undefined,
        health: health || undefined,
        projectId: projectId || undefined,
        campaignId: campaignId || undefined,
      }),
  );
  const runs = Array.isArray(data?.runs) ? data.runs : [];

  function handleChange(setter: (value: string) => void) {
    return (event: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setter(event.target.value);
  }

  return (
    <Panel eyebrow="Unified runs board" title="Runs">
      <div className="filters">
        <label className="console-field">
          <span>Project</span>
          <input placeholder="demo" value={projectId} onChange={handleChange(setProjectId)} />
        </label>
        <label className="console-field">
          <span>Driver</span>
          <select value={driver} onChange={handleChange(setDriver)}>
            <option value="">All drivers</option>
            <option value="local">local</option>
            <option value="manual">manual</option>
            <option value="codex">codex</option>
            <option value="claude-code">claude-code</option>
          </select>
        </label>
        <label className="console-field">
          <span>Campaign</span>
          <input placeholder="campaign_..." value={campaignId} onChange={handleChange(setCampaignId)} />
        </label>
        <label className="console-field">
          <span>Health</span>
          <select value={health} onChange={handleChange(setHealth)}>
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
