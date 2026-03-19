import { Link } from "react-router-dom";

import { createConsoleClient } from "../api/client";
import { KeyValueGrid } from "../components/KeyValueGrid";
import { Panel } from "../components/Panel";
import { RunCard } from "../components/RunCard";
import { StatusPill } from "../components/StatusPill";
import { useConsoleConfig } from "../components/ConsoleLayout";
import { useConsoleQuery } from "../hooks/useConsoleQuery";

export function HomePage() {
  const { apiBase, workspacePath } = useConsoleConfig();
  const client = createConsoleClient(apiBase, workspacePath);
  const { data, loading, error } = useConsoleQuery(
    `home:${apiBase}:${workspacePath}`,
    () => client.getHome(),
  );

  const home = (data?.home ?? {}) as Record<string, unknown>;
  const recommended = (home.recommended_next ?? null) as
    | { task?: Record<string, unknown>; reasons?: string[] }
    | null;
  const activeRuns = Array.isArray(home.active_runs) ? home.active_runs : [];
  const evaluatingRuns = Array.isArray(home.evaluating_runs) ? home.evaluating_runs : [];
  const inbox = Array.isArray(home.inbox) ? home.inbox : [];
  const blocked = Array.isArray(home.blocked_projects) ? home.blocked_projects : [];
  const campaigns = Array.isArray(home.campaigns) ? home.campaigns : [];
  const recentEvents = Array.isArray(home.recent_events) ? home.recent_events : [];
  const recentAccepts = Array.isArray(home.recent_accepts) ? home.recent_accepts : [];

  return (
    <div className="page-grid">
      <Panel eyebrow="Portfolio overview" title="Home">
        {loading ? <p>Loading Home…</p> : null}
        {error ? <p className="error-copy">{error}</p> : null}
        {!loading && !error ? (
          <div className="stack">
            <KeyValueGrid
              values={[
                { label: "Workspace", value: String(home.workspace ?? "—") },
                { label: "Active runs", value: activeRuns.length },
                { label: "Awaiting review", value: evaluatingRuns.length },
                { label: "Inbox items", value: inbox.length },
                { label: "Campaigns", value: campaigns.length },
              ]}
            />

            <div className="hero-card">
              <p className="hero-card__eyebrow">Why this next?</p>
              {recommended?.task ? (
                <>
                  <h3>{String(recommended.task.title ?? recommended.task.id ?? "Next task")}</h3>
                  <p className="hero-card__subtle">
                    {String(recommended.task.project_id ?? "unknown project")}
                  </p>
                  <ul className="reason-list">
                    {(recommended.reasons ?? []).map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                </>
              ) : (
                <p>No recommendation available right now.</p>
              )}
            </div>
          </div>
        ) : null}
      </Panel>

      <Panel eyebrow="Live work" title="Active Runs">
        <div className="card-grid">
          {activeRuns.length ? (
            activeRuns.map((run) => <RunCard key={String((run as Record<string, unknown>).id)} run={run as Record<string, unknown>} />)
          ) : (
            <p>No active runs right now.</p>
          )}
        </div>
      </Panel>

      <Panel eyebrow="Exceptions" title="Inbox">
        <div className="stack">
          {inbox.length ? (
            inbox.map((item) => {
              const entry = item as Record<string, unknown>;
              return (
                <article className="list-card" key={String(entry.title)}>
                  <div className="list-card__header">
                    <h3>{String(entry.title ?? entry.kind ?? "Inbox item")}</h3>
                    <StatusPill tone={String(entry.kind ?? "info")}>
                      {String(entry.kind ?? "info")}
                    </StatusPill>
                  </div>
                  <p>{String(entry.reason ?? "Needs operator attention.")}</p>
                </article>
              );
            })
          ) : (
            <p>The inbox is clear.</p>
          )}
        </div>
      </Panel>

      <Panel eyebrow="Blockers" title="Blocked Projects">
        <div className="stack">
          {blocked.length ? (
            blocked.map((item) => {
              const project = item as Record<string, unknown>;
              return (
                <article className="list-card" key={String(project.project_id)}>
                  <div className="list-card__header">
                    <h3>{String(project.project_id ?? "project")}</h3>
                    <StatusPill tone={String(project.in_cycle ? "blocked" : "waiting")}>
                      {project.in_cycle ? "cycle" : "blocked"}
                    </StatusPill>
                  </div>
                  <ul className="reason-list">
                    {(Array.isArray(project.blocking_reasons) ? project.blocking_reasons : []).map(
                      (reason) => <li key={String(reason)}>{String(reason)}</li>,
                    )}
                  </ul>
                </article>
              );
            })
          ) : (
            <p>No blocked projects.</p>
          )}
        </div>
      </Panel>

      <Panel eyebrow="Portfolio loops" title="Campaigns">
        <div className="stack">
          {campaigns.length ? (
            campaigns.map((item) => {
              const campaign = item as Record<string, unknown>;
              return (
                <article className="list-card" key={String(campaign.id)}>
                  <div className="list-card__header">
                    <h3>
                      <Link to={`/campaigns/${String(campaign.id)}`}>
                        {String(campaign.title ?? campaign.id ?? "Campaign")}
                      </Link>
                    </h3>
                    <StatusPill tone={String(campaign.status ?? "healthy")}>
                      {String(campaign.status ?? "unknown")}
                    </StatusPill>
                  </div>
                  <p>{String(campaign.goal ?? "No campaign goal recorded.")}</p>
                  <p className="list-card__meta">
                    Driver: {String(campaign.driver ?? "—")} • Briefs:{" "}
                    {String(campaign.brief_cadence ?? "—")}
                  </p>
                </article>
              );
            })
          ) : (
            <p>No campaigns exist yet.</p>
          )}
        </div>
      </Panel>

      <Panel eyebrow="What changed" title="Recent Activity">
        <div className="stack">
          {recentEvents.length ? (
            recentEvents.slice(0, 6).map((item) => {
              const event = item as Record<string, unknown>;
              return (
                <article className="list-card" key={String(event.event_id ?? event.ts)}>
                  <div className="list-card__header">
                    <h3>{String(event.type ?? "event")}</h3>
                    <span className="list-card__meta">{String(event.ts ?? "—")}</span>
                  </div>
                  <p>{String((event.payload as Record<string, unknown> | undefined)?.message ?? "Audit event recorded.")}</p>
                </article>
              );
            })
          ) : recentAccepts.length ? (
            recentAccepts.map((run) => (
              <RunCard key={String((run as Record<string, unknown>).id)} run={run as Record<string, unknown>} />
            ))
          ) : (
            <p>No recent activity.</p>
          )}
        </div>
      </Panel>
    </div>
  );
}
