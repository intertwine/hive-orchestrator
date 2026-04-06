import { createConsoleClient } from "../api/client";
import { ConsoleLink } from "../components/ConsoleLink";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import { useConsoleConfig } from "../components/ConsoleLayout";
import { useConsoleQuery } from "../hooks/useConsoleQuery";

export function NotificationsPage() {
  const { apiBase, workspacePath } = useConsoleConfig();
  const client = createConsoleClient(apiBase, workspacePath);
  const { data, loading, error } = useConsoleQuery(
    `notifications:${apiBase}:${workspacePath}`,
    () => client.getInbox(),
    3000,
  );
  const items = Array.isArray(data?.items) ? data.items : [];

  return (
    <div className="page-grid">
      <Panel eyebrow="Attention routing" title="Notifications">
        {loading ? <p>Loading Notifications…</p> : null}
        {error ? <p className="error-copy">{error}</p> : null}
        <div className="stack">
          <article className="hero-card">
            <p className="hero-card__eyebrow">Shared event contract</p>
            <h3>Inbox-worthy signals already have a dedicated surface.</h3>
            <p className="hero-card__subtle">
              This route is the stable home for operator notifications now, while the richer
              notification center and preference model land in the next slice.
            </p>
          </article>
          {items.length ? (
            items.map((item) => {
              const entry = item as Record<string, unknown>;
              const notificationKey = [
                String(entry.kind ?? ""),
                String(entry.run_id ?? ""),
                String(entry.approval_id ?? ""),
                String(entry.title ?? ""),
              ].join(":");
              return (
                <article className="list-card" key={notificationKey}>
                  <div className="list-card__header">
                    <h3>{String(entry.title ?? entry.kind ?? "Notification")}</h3>
                    <StatusPill tone={String(entry.kind ?? "info")}>
                      {String(entry.kind ?? "signal")}
                    </StatusPill>
                  </div>
                  <p>{String(entry.reason ?? "Needs operator attention.")}</p>
                  <p className="list-card__meta">
                    Project: {String(entry.project_id ?? "—")}
                    {entry.run_id ? ` • Run: ${String(entry.run_id)}` : ""}
                  </p>
                  {entry.run_id ? (
                    <p className="list-card__meta">
                      <ConsoleLink to={`/runs/${String(entry.run_id)}`}>Open run</ConsoleLink>
                    </p>
                  ) : null}
                </article>
              );
            })
          ) : (
            <p>No notifications are queued right now.</p>
          )}
        </div>
      </Panel>

      <Panel eyebrow="Why this exists" title="Routing Promise">
        <div className="stack">
          <article className="list-card">
            <div className="list-card__header">
              <h3>Stable shell surface</h3>
            </div>
            <p>
              Notifications now have a first-class route in the app shell, so browser links and
              future desktop deep links can land on the same operator surface.
            </p>
          </article>
          <article className="list-card">
            <div className="list-card__header">
              <h3>Next slice</h3>
            </div>
            <p>
              Bulk triage, snooze, richer grouping, and provenance/explanation affordances belong
              to the dedicated notifications and inbox overhaul task.
            </p>
          </article>
        </div>
      </Panel>
    </div>
  );
}
