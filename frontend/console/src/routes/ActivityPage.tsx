import { createConsoleClient } from "../api/client";
import { ConsoleLink } from "../components/ConsoleLink";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import { useConsoleConfig } from "../components/ConsoleLayout";
import { useConsoleQuery } from "../hooks/useConsoleQuery";

export function ActivityPage() {
  const { apiBase, workspacePath } = useConsoleConfig();
  const client = createConsoleClient(apiBase, workspacePath);
  const { data, loading, error } = useConsoleQuery(
    `activity:${apiBase}:${workspacePath}`,
    () => client.getHome(),
    3000,
  );

  const home = (data?.home ?? {}) as Record<string, unknown>;
  const recentEvents = Array.isArray(home.recent_events) ? home.recent_events : [];
  const recentAccepts = Array.isArray(home.recent_accepts) ? home.recent_accepts : [];

  return (
    <div className="page-grid">
      <Panel eyebrow="What changed" title="Activity">
        {loading ? <p>Loading Activity…</p> : null}
        {error ? <p className="error-copy">{error}</p> : null}
        <div className="stack">
          {recentEvents.length ? (
            recentEvents.map((item) => {
              const event = item as Record<string, unknown>;
              const payload = (event.payload ?? {}) as Record<string, unknown>;
              const runId = String(payload.run_id ?? payload.runId ?? "");
              return (
                <article className="list-card" key={String(event.event_id ?? event.ts ?? event.type)}>
                  <div className="list-card__header">
                    <h3>{String(event.type ?? "event")}</h3>
                    <span className="list-card__meta">{String(event.ts ?? "—")}</span>
                  </div>
                  <p>{String(payload.message ?? "Audit event recorded.")}</p>
                  {runId ? (
                    <p className="list-card__meta">
                      <ConsoleLink to={`/runs/${runId}`}>Open run</ConsoleLink>
                    </p>
                  ) : null}
                </article>
              );
            })
          ) : (
            <p>No recent events have been recorded yet.</p>
          )}
        </div>
      </Panel>

      <Panel eyebrow="Recent accepts" title="Promotion Feed">
        <div className="stack">
          {recentAccepts.length ? (
            recentAccepts.map((item) => {
              const run = item as Record<string, unknown>;
              const metadata = (run.metadata_json ?? {}) as Record<string, unknown>;
              return (
                <article
                  className="list-card"
                  key={String(run.id ?? run.run_id ?? metadata.task_title ?? "accepted-run")}
                >
                  <div className="list-card__header">
                    <h3>{String(metadata.task_title ?? run.id ?? "Accepted run")}</h3>
                    <StatusPill tone={String(run.status ?? "accepted")}>
                      {String(run.status ?? "accepted")}
                    </StatusPill>
                  </div>
                  <p className="list-card__meta">
                    Project: {String(run.project_id ?? "—")} • Driver: {String(run.driver ?? "—")}
                  </p>
                  {run.id ? (
                    <p className="list-card__meta">
                      <ConsoleLink to={`/runs/${String(run.id)}`}>Open run</ConsoleLink>
                    </p>
                  ) : null}
                </article>
              );
            })
          ) : (
            <p>No accepted runs are visible in the recent feed yet.</p>
          )}
        </div>
      </Panel>
    </div>
  );
}
