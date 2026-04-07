import { useState } from "react";

import { createConsoleClient } from "../api/client";
import { useConsoleEventBus } from "../components/ConsoleEventBus";
import { ConsoleLink } from "../components/ConsoleLink";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import { useConsoleConfig } from "../components/ConsoleLayout";
import { useConsoleQuery } from "../hooks/useConsoleQuery";

export function InboxPage() {
  const { apiBase, workspacePath } = useConsoleConfig();
  const client = createConsoleClient(apiBase, workspacePath);
  const { requestRefresh } = useConsoleEventBus();
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const { data, loading, error } = useConsoleQuery(
    `inbox:${apiBase}:${workspacePath}`,
    () => client.getInbox(),
  );
  const items = Array.isArray(data?.items) ? data.items : [];

  async function handleApproval(
    runId: string,
    approvalId: string,
    resolution: "approve" | "reject",
  ) {
    setPendingAction(`${resolution}:${approvalId}`);
    setActionMessage(null);
    setActionError(null);
    try {
      if (resolution === "approve") {
        await client.approveRunApproval(runId, approvalId, { actor: "console-operator" });
      } else {
        await client.rejectRunApproval(runId, approvalId, { actor: "console-operator" });
      }
      setActionMessage(`${resolution === "approve" ? "Approved" : "Rejected"} ${approvalId}.`);
      requestRefresh();
    } catch (caught) {
      setActionError(
        caught instanceof Error ? caught.message : `Unable to ${resolution} approval.`,
      );
    } finally {
      setPendingAction(null);
    }
  }

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
                {entry.run_id ? (
                  <p className="list-card__meta">
                    <ConsoleLink to={`/runs/${String(entry.run_id)}`}>Open run</ConsoleLink>
                  </p>
                ) : null}
                {entry.kind === "approval-request" && entry.run_id && entry.approval_id ? (
                  <div className="action-grid">
                    <button
                      className="primary-button"
                      type="button"
                      disabled={pendingAction !== null}
                      onClick={() =>
                        handleApproval(
                          String(entry.run_id),
                          String(entry.approval_id),
                          "approve",
                        )
                      }
                    >
                      Approve
                    </button>
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={pendingAction !== null}
                      onClick={() =>
                        handleApproval(
                          String(entry.run_id),
                          String(entry.approval_id),
                          "reject",
                        )
                      }
                    >
                      Reject
                    </button>
                  </div>
                ) : null}
              </article>
            );
          })
        ) : (
          <p>The inbox is clear.</p>
        )}
        {actionMessage ? <p>{actionMessage}</p> : null}
        {actionError ? <p className="error-copy">{actionError}</p> : null}
      </div>
    </Panel>
  );
}
