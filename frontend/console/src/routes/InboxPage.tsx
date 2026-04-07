import { startTransition, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { createConsoleClient } from "../api/client";
import {
  ConsoleActionButton,
  type ConsoleActionDescriptor,
  useRegisterConsoleActions,
} from "../components/ConsoleActions";
import { useConsoleEventBus } from "../components/ConsoleEventBus";
import { ConsoleLink, preserveConsoleSearch } from "../components/ConsoleLink";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import { useConsoleConfig } from "../components/ConsoleLayout";
import { useConsoleQuery } from "../hooks/useConsoleQuery";

function inboxApprovalSuccessMessage(
  actionId: "approval.approve" | "approval.reject",
  approvalId: string,
): string {
  return `${actionId === "approval.approve" ? "Approved" : "Rejected"} ${approvalId}.`;
}

export function InboxPage() {
  const { apiBase, workspacePath } = useConsoleConfig();
  const client = useMemo(
    () => createConsoleClient(apiBase, workspacePath),
    [apiBase, workspacePath],
  );
  const location = useLocation();
  const navigate = useNavigate();
  const { requestRefresh } = useConsoleEventBus();
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const { data, loading, error } = useConsoleQuery(
    `inbox:${apiBase}:${workspacePath}`,
    () => client.getInbox(),
  );
  const items = useMemo(
    () => (Array.isArray(data?.items) ? data.items : []),
    [data?.items],
  );

  const pageActions = useMemo<ConsoleActionDescriptor[]>(() => {
    return items.flatMap((item) => {
      const entry = item as Record<string, unknown>;
      const runId = String(entry.run_id ?? "");
      const approvalId = String(entry.approval_id ?? "");
      const title = String(entry.title ?? entry.kind ?? "Inbox item");
      const reason = String(entry.reason ?? "Needs operator attention.");
      const actions: ConsoleActionDescriptor[] = [];

      if (runId) {
        actions.push({
          id: `open.run:${runId}`,
          title: `Open run ${runId}`,
          description: `Jump from the inbox into the full run detail for ${runId}.`,
          group: "Inbox",
          enabled: true,
          availabilityReason: "Available because this inbox item is attached to a run.",
          availabilitySource: "inbox item",
          keywords: ["open", "run", runId, title, reason],
          perform: () => {
            startTransition(() => {
              navigate(preserveConsoleSearch(`/runs/${runId}`, location.search));
            });
          },
        });
      }

      if (entry.kind === "approval-request" && runId && approvalId) {
        const availabilityReason = pendingAction === null
          ? `Available because ${title} is still pending operator review.`
          : "Another inbox action is already in flight.";
        for (const actionId of ["approval.approve", "approval.reject"] as const) {
          actions.push({
            id: `${actionId}:${approvalId}`,
            title: `${actionId === "approval.approve" ? "Approve" : "Reject"} ${title}`,
            buttonLabel: actionId === "approval.approve" ? "Approve" : "Reject",
            description: reason,
            group: "Inbox approvals",
            tone: actionId === "approval.approve" ? "primary" : "secondary",
            enabled: pendingAction === null,
            availabilityReason,
            availabilitySource: "pending inbox approval",
            keywords: [
              actionId === "approval.approve" ? "approve" : "reject",
              approvalId,
              runId,
              title,
            ],
            perform: async () => {
              setPendingAction(`${actionId}:${approvalId}`);
              setActionMessage(null);
              setActionError(null);
              try {
                await client.executeAction({
                  action_id: actionId,
                  run_id: runId,
                  approval_id: approvalId,
                  actor: "console-operator",
                });
                setActionMessage(inboxApprovalSuccessMessage(actionId, approvalId));
                requestRefresh();
              } catch (caught) {
                setActionError(
                  caught instanceof Error
                    ? caught.message
                    : `Unable to ${actionId === "approval.approve" ? "approve" : "reject"} approval.`,
                );
              } finally {
                setPendingAction(null);
              }
            },
          });
        }
      }

      return actions;
    });
  }, [client, items, location.search, navigate, pendingAction, requestRefresh]);

  useRegisterConsoleActions(pageActions);

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
                    {pageActions
                      .filter(
                        (action) =>
                          action.id === `approval.approve:${String(entry.approval_id)}`
                          || action.id === `approval.reject:${String(entry.approval_id)}`,
                      )
                      .map((action) => (
                        <ConsoleActionButton action={action} key={action.id} />
                      ))}
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
