import { useMemo } from "react";

import { createConsoleClient } from "../api/client";
import { AttentionBoard } from "../components/AttentionBoard";
import { Panel } from "../components/Panel";
import { useConsoleConfig } from "../components/ConsoleLayout";
import { useConsoleQuery } from "../hooks/useConsoleQuery";

export function NotificationsPage() {
  const { apiBase, workspacePath } = useConsoleConfig();
  const client = useMemo(
    () => createConsoleClient(apiBase, workspacePath),
    [apiBase, workspacePath],
  );
  const { data, loading, error } = useConsoleQuery(
    `notifications:${apiBase}:${workspacePath}`,
    () => client.getNotifications(),
    3000,
  );
  const items = Array.isArray(data?.items) ? data.items : [];
  const summary = (data?.summary ?? {}) as Record<string, unknown>;
  const byTier = (summary.by_notification_tier ?? {}) as Record<string, number>;
  const bySeverity = (summary.by_severity ?? {}) as Record<string, number>;

  return (
    <div className="page-grid">
      <AttentionBoard
        eyebrow="Persistent signals"
        title="Notifications"
        loading={loading}
        error={error}
        items={items}
        mode="notifications"
        emptyMessage="No notifications are queued right now."
      />

      <Panel eyebrow="Center of gravity" title="Notification mix">
        <div className="stack">
          <article className="list-card">
            <div className="list-card__header">
              <h3>Tier summary</h3>
            </div>
            <p className="list-card__meta">
              Actionable: {byTier.actionable ?? 0} • Informational: {byTier.informational ?? 0}
            </p>
            <p>
              Actionable items are inbox-worthy. Informational items stay visible here so operators
              can review important portfolio events without polluting the decision queue.
            </p>
          </article>
          <article className="list-card">
            <div className="list-card__header">
              <h3>Severity mix</h3>
            </div>
            <p className="list-card__meta">
              Critical: {bySeverity.critical ?? 0} • High: {bySeverity.high ?? 0} • Medium: {bySeverity.medium ?? 0} • Low: {bySeverity.low ?? 0} • Info: {bySeverity.info ?? 0}
            </p>
            <p>
              This summary makes it easy to tell whether the current queue is dominated by
              high-stakes approvals, stalled failures, or lower-stakes context.
            </p>
          </article>
        </div>
      </Panel>
    </div>
  );
}
