import { useMemo } from "react";

import { createConsoleClient } from "../api/client";
import { ConsoleLink } from "../components/ConsoleLink";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import { useConsoleConfig } from "../components/ConsoleLayout";
import { useConsoleQuery } from "../hooks/useConsoleQuery";

export function ActivityPage() {
  const { apiBase, workspacePath } = useConsoleConfig();
  const client = useMemo(
    () => createConsoleClient(apiBase, workspacePath),
    [apiBase, workspacePath],
  );
  const { data, loading, error } = useConsoleQuery(
    `activity:${apiBase}:${workspacePath}`,
    () => client.getActivity(),
    3000,
  );

  const items = Array.isArray(data?.items) ? data.items : [];
  const summary = (data?.summary ?? {}) as Record<string, unknown>;
  const byKind = useMemo(() => {
    return items.reduce<Record<string, number>>((counts, item) => {
      const entry = item as Record<string, unknown>;
      const kind = String(entry.kind ?? entry.source ?? "event");
      counts[kind] = (counts[kind] ?? 0) + 1;
      return counts;
    }, {});
  }, [items]);
  const byProject = useMemo(() => {
    return items.reduce<Record<string, number>>((counts, item) => {
      const entry = item as Record<string, unknown>;
      const project = String(entry.project_label ?? entry.project_id ?? "Workspace");
      counts[project] = (counts[project] ?? 0) + 1;
      return counts;
    }, {});
  }, [items]);
  const busiestProject = useMemo(
    () => Object.entries(byProject).sort((left, right) => right[1] - left[1])[0],
    [byProject],
  );

  return (
    <div className="page-grid">
      <Panel eyebrow="What changed" title="Activity">
        {loading ? <p>Loading Activity…</p> : null}
        {error ? <p className="error-copy">{error}</p> : null}
        <div className="stack">
          {items.length ? (
            items.map((item) => {
              const entry = item as Record<string, unknown>;
              const deepLink = String(entry.deep_link ?? "");
              const runId = String(entry.run_id ?? "");
              return (
                <article className="list-card" key={String(entry.id ?? entry.title ?? "activity-item")}>
                  <div className="list-card__header">
                    <div>
                      <h3>{String(entry.title ?? entry.kind ?? "Workspace activity")}</h3>
                      <p className="list-card__meta">
                        {String(entry.project_label ?? entry.project_id ?? "Workspace")}
                        {runId ? ` • ${runId}` : ""}
                      </p>
                    </div>
                    <StatusPill tone={String(entry.kind ?? entry.source ?? "event")}>
                      {String(entry.kind ?? entry.source ?? "event")}
                    </StatusPill>
                  </div>
                  <p>{String(entry.summary ?? "Recent workspace activity was recorded.")}</p>
                  <p className="list-card__meta">{String(entry.occurred_at ?? "—")}</p>
                  {deepLink ? (
                    <p className="list-card__meta">
                      <ConsoleLink to={deepLink}>{runId ? "Open run" : "Open details"}</ConsoleLink>
                    </p>
                  ) : null}
                </article>
              );
            })
          ) : (
            <p>No recent activity has been recorded yet.</p>
          )}
        </div>
      </Panel>

      <Panel eyebrow="Feed shape" title="Activity summary">
        <div className="stack">
          <article className="list-card">
            <div className="list-card__header">
              <h3>Recent volume</h3>
            </div>
            <p className="list-card__meta">Items visible: {String(summary.total ?? items.length)}</p>
            <p>
              The activity feed stays compact and chronological so operators can reconstruct what
              changed without wading through the heavier inbox decision surface.
            </p>
          </article>
          <article className="list-card">
            <div className="list-card__header">
              <h3>Event mix</h3>
            </div>
            <p className="list-card__meta">
              Events: {byKind.event ?? 0} • Accepted runs: {byKind["accepted-run"] ?? 0}
            </p>
            <p>
              Activity is intentionally lighter than Notifications: it answers “what moved?” while
              Inbox and Notifications stay focused on decisions and persistent signals.
            </p>
          </article>
          <article className="list-card">
            <div className="list-card__header">
              <h3>Where movement is concentrated</h3>
            </div>
            <p className="list-card__meta">
              {busiestProject ? `${busiestProject[0]} • ${busiestProject[1]} items` : "Workspace-wide"}
            </p>
            <p>
              Use <ConsoleLink to="/notifications">Notifications</ConsoleLink> for persistent
              signals and <ConsoleLink to="/inbox">Inbox</ConsoleLink> for approvals, exceptions,
              and actions that still need an operator decision.
            </p>
          </article>
        </div>
      </Panel>
    </div>
  );
}
