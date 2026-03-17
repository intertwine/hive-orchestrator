import { createConsoleClient } from "../api/client";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import { useConsoleConfig } from "../components/ConsoleLayout";
import { useConsoleQuery } from "../hooks/useConsoleQuery";

export function InboxPage() {
  const { apiBase, workspacePath } = useConsoleConfig();
  const client = createConsoleClient(apiBase, workspacePath);
  const { data, loading, error } = useConsoleQuery(
    `inbox:${apiBase}:${workspacePath}`,
    () => client.getInbox(),
  );
  const items = Array.isArray(data?.items) ? data.items : [];

  return (
    <Panel eyebrow="Operator attention" title="Inbox">
      {loading ? <p>Loading Inbox…</p> : null}
      {error ? <p className="error-copy">{error}</p> : null}
      <div className="stack">
        {items.length ? (
          items.map((item) => {
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
                <p className="list-card__meta">
                  Project: {String(entry.project_id ?? "—")}
                  {entry.run_id ? ` • Run: ${String(entry.run_id)}` : ""}
                </p>
              </article>
            );
          })
        ) : (
          <p>The inbox is clear.</p>
        )}
      </div>
    </Panel>
  );
}
