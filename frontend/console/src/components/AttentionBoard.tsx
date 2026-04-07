import { startTransition, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import type { JsonRecord } from "../api/client";
import { createConsoleClient } from "../api/client";
import {
  type AttentionItem,
  groupAttentionItems,
  matchesAttentionFilters,
  normalizeAttentionItem,
} from "../attention";
import {
  ConsoleActionButton,
  type ConsoleActionDescriptor,
  createConsoleActionDescriptor,
  normalizeConsoleActionRecord,
  useRegisterConsoleActions,
} from "./ConsoleActions";
import { ConsoleLink, preserveConsoleSearch } from "./ConsoleLink";
import { Panel } from "./Panel";
import { StatusPill } from "./StatusPill";
import { useConsoleConfig } from "./ConsoleLayout";
import { useConsoleEventBus } from "./ConsoleEventBus";
import { useConsolePreferences } from "./ConsolePreferences";
import { sameAttentionFilters } from "../preferences";

const ASSIGNEE_OPTIONS = [
  { value: "me", label: "Me" },
  { value: "release-captain", label: "Release captain" },
  { value: "ops-review", label: "Ops review" },
] as const;

const SNOOZE_OPTIONS = [
  { value: "3600", label: "1 hour" },
  { value: "14400", label: "4 hours" },
  { value: "86400", label: "1 day" },
] as const;

function makeSnoozedUntil(seconds: string) {
  return new Date(Date.now() + Number.parseInt(seconds, 10) * 1000).toISOString();
}

function uniqueValues(items: AttentionItem[], key: keyof AttentionItem) {
  return Array.from(
    new Set(items.map((item) => String(item[key] ?? "")).filter(Boolean)),
  ).sort();
}

function selectionLabel(count: number) {
  return count === 1 ? "1 item selected" : `${count} items selected`;
}

function supportsAction(item: AttentionItem, action: string) {
  return item.bulkActions.includes(action);
}

interface AttentionBoardProps {
  mode: "inbox" | "notifications";
  title: string;
  eyebrow: string;
  loading: boolean;
  error: string | null;
  items: JsonRecord[];
  emptyMessage: string;
}

export function AttentionBoard({
  mode,
  title,
  eyebrow,
  loading,
  error,
  items,
  emptyMessage,
}: AttentionBoardProps) {
  const { apiBase, workspacePath } = useConsoleConfig();
  const client = useMemo(
    () => createConsoleClient(apiBase, workspacePath),
    [apiBase, workspacePath],
  );
  const location = useLocation();
  const navigate = useNavigate();
  const { requestRefresh } = useConsoleEventBus();
  const {
    preferences,
    setAttentionFilters,
    saveAttentionView,
    deleteAttentionView,
    resetAttentionFilters,
    updateAttentionItem,
    clearAttentionDisposition,
  } = useConsolePreferences();
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [assignTarget, setAssignTarget] = useState("me");
  const [snoozeSeconds, setSnoozeSeconds] = useState("3600");
  const [viewName, setViewName] = useState("");

  const attentionFilters = preferences.attention.filters;
  const effectiveFilters = useMemo(() => (
    mode === "inbox"
      ? { ...attentionFilters, tier: "actionable" }
      : attentionFilters
  ), [attentionFilters, mode]);
  const triageByItemId = preferences.attention.triageByItemId;

  const normalizedItems = useMemo(
    () => items.map((item) => normalizeAttentionItem(item)),
    [items],
  );

  const visibleItems = useMemo(() => {
    const now = Date.now();
    return normalizedItems.filter((item) => {
      const triage = triageByItemId[item.id];
      if (triage?.disposition === "dismissed" || triage?.disposition === "resolved") {
        return false;
      }
      return matchesAttentionFilters(item, effectiveFilters, triage, now);
    });
  }, [effectiveFilters, normalizedItems, triageByItemId]);

  const groupedItems = useMemo(
    () => groupAttentionItems(visibleItems),
    [visibleItems],
  );

  const selectedItems = useMemo(
    () => visibleItems.filter((item) => selectedIds.includes(item.id)),
    [selectedIds, visibleItems],
  );
  const canResolveSelection = selectedItems.length > 0
    && selectedItems.every((item) => supportsAction(item, "resolve"));

  const hiddenCounts = useMemo(() => {
    const entries = Object.values(triageByItemId);
    return {
      dismissed: entries.filter((entry) => entry.disposition === "dismissed").length,
      resolved: entries.filter((entry) => entry.disposition === "resolved").length,
    };
  }, [triageByItemId]);

  const severityOptions = useMemo(() => uniqueValues(normalizedItems, "severity"), [normalizedItems]);
  const decisionOptions = useMemo(
    () => uniqueValues(normalizedItems, "decisionType"),
    [normalizedItems],
  );
  const sourceOptions = useMemo(() => uniqueValues(normalizedItems, "source"), [normalizedItems]);

  const activeView = preferences.attention.savedViews.find((view) =>
    sameAttentionFilters(view.filters, effectiveFilters),
  ) ?? null;

  useEffect(() => {
    setSelectedIds((current) => {
      const next = current.filter((itemId) => visibleItems.some((item) => item.id === itemId));
      if (next.length === current.length && next.every((itemId, index) => itemId === current[index])) {
        return current;
      }
      return next;
    });
  }, [visibleItems]);

  function updateFilters(update: Partial<typeof attentionFilters>) {
    setAttentionFilters({
      ...attentionFilters,
      ...update,
    });
  }

  function toggleSelection(itemId: string) {
    setSelectedIds((current) =>
      current.includes(itemId)
        ? current.filter((candidate) => candidate !== itemId)
        : [...current, itemId],
    );
  }

  function clearSelection() {
    setSelectedIds([]);
  }

  function applyBulkDisposition(disposition: "dismissed" | "resolved") {
    const targetIds = disposition === "resolved"
      ? selectedItems.filter((item) => supportsAction(item, "resolve")).map((item) => item.id)
      : selectedIds;
    if (!targetIds.length) {
      setActionError("The current selection does not support that triage action.");
      setActionMessage(null);
      return;
    }
    for (const itemId of targetIds) {
      updateAttentionItem(itemId, {
        disposition,
        snoozedUntil: null,
      });
    }
    setActionMessage(
      `${disposition === "resolved" ? "Resolved" : "Dismissed"} ${targetIds.length} attention item(s).`,
    );
    setActionError(null);
    clearSelection();
  }

  function applyBulkAssignee() {
    for (const itemId of selectedIds) {
      updateAttentionItem(itemId, {
        assignee: assignTarget,
        disposition: "active",
      });
    }
    setActionMessage(`Assigned ${selectedIds.length} attention item(s) to ${assignTarget}.`);
    setActionError(null);
    clearSelection();
  }

  function applyBulkSnooze() {
    const snoozedUntil = makeSnoozedUntil(snoozeSeconds);
    for (const itemId of selectedIds) {
      updateAttentionItem(itemId, {
        disposition: "active",
        snoozedUntil,
      });
    }
    setActionMessage(
      `Snoozed ${selectedIds.length} attention item(s) until ${new Date(snoozedUntil).toLocaleString()}.`,
    );
    setActionError(null);
    clearSelection();
  }

  async function resolveApproval(
    item: AttentionItem,
    actionId: "approval.approve" | "approval.reject",
  ) {
    if (!item.runId || !item.approvalId) {
      return;
    }
    setPendingAction(`${actionId}:${item.id}`);
    setActionMessage(null);
    setActionError(null);
    try {
      await client.executeAction({
        action_id: actionId,
        run_id: item.runId,
        approval_id: item.approvalId,
        actor: "console-operator",
      });
      updateAttentionItem(item.id, {
        disposition: "resolved",
        snoozedUntil: null,
      });
      setActionMessage(`${actionId === "approval.approve" ? "Approved" : "Rejected"} ${item.title}.`);
      requestRefresh();
    } catch (caught) {
      setActionError(
        caught instanceof Error ? caught.message : `Unable to ${actionId === "approval.approve" ? "approve" : "reject"} approval.`,
      );
    } finally {
      setPendingAction(null);
    }
  }

  function openAttentionLink(item: AttentionItem) {
    if (!item.deepLink) {
      return;
    }
    startTransition(() => {
      navigate(preserveConsoleSearch(item.deepLink, location.search));
    });
  }

  const normalizedItemActions = useMemo(
    () =>
      visibleItems.map((item) => ({
        itemId: item.id,
        actions: item.actions.map((entry) => normalizeConsoleActionRecord(entry)),
      })),
    [visibleItems],
  );

  const registryActionIdsByItem = useMemo(() => {
    return new Map(
      normalizedItemActions.map(({ itemId, actions }) => [
        itemId,
        new Set(actions.map((action) => action.id)),
      ]),
    );
  }, [normalizedItemActions]);

  const registryActions = useMemo<ConsoleActionDescriptor[]>(() => {
    return normalizedItemActions.flatMap(({ actions }) =>
      actions.map((action) =>
        createConsoleActionDescriptor(action, {
          actor: "console-operator",
          busy: pendingAction !== null,
          busyReason: "Another operator action is already in flight.",
          client,
          locationSearch: location.search,
          navigate,
          requestRefresh,
          setActionError,
          setActionMessage,
          setPendingAction,
        }),
      ),
    );
  }, [
    client,
    location.search,
    navigate,
    normalizedItemActions,
    pendingAction,
    requestRefresh,
  ]);

  const pageActions = useMemo<ConsoleActionDescriptor[]>(() => {
    const actions: ConsoleActionDescriptor[] = [];
    if (selectedItems.length) {
      if (canResolveSelection) {
        actions.push(
          {
            id: `attention.resolve.selected:${mode}`,
            title: `Resolve ${selectionLabel(selectedItems.length)}`,
            buttonLabel: "Resolve selected",
            description: "Clear the current selection from the actionable queue.",
            group: "Inbox triage",
            tone: "primary",
            enabled: pendingAction === null,
            availabilityReason: "Available because the current selection supports resolve.",
            availabilitySource: "operator selection",
            perform: () => applyBulkDisposition("resolved"),
          },
        );
      }
      actions.push(
        {
          id: `attention.dismiss.selected:${mode}`,
          title: `Dismiss ${selectionLabel(selectedItems.length)}`,
          buttonLabel: "Dismiss selected",
          description: "Hide the current selection from this operator queue without changing canonical state.",
          group: "Inbox triage",
          enabled: pendingAction === null,
          availabilityReason: "Available because one or more triage items are selected.",
          availabilitySource: "operator selection",
          perform: () => applyBulkDisposition("dismissed"),
        },
        {
          id: `attention.assign.selected:${mode}`,
          title: `Assign ${selectionLabel(selectedItems.length)} to ${assignTarget}`,
          buttonLabel: "Assign selected",
          description: "Tag the selected items with a local operator assignee label.",
          group: "Inbox triage",
          enabled: pendingAction === null,
          availabilityReason: "Available because one or more triage items are selected.",
          availabilitySource: "operator selection",
          perform: () => applyBulkAssignee(),
        },
        {
          id: `attention.snooze.selected:${mode}`,
          title: `Snooze ${selectionLabel(selectedItems.length)}`,
          buttonLabel: "Snooze selected",
          description: "Temporarily hide the selected items until the chosen snooze window expires.",
          group: "Inbox triage",
          enabled: pendingAction === null,
          availabilityReason: "Available because one or more triage items are selected.",
          availabilitySource: "operator selection",
          perform: () => applyBulkSnooze(),
        },
      );
    }

    actions.push(...registryActions);

    for (const item of visibleItems) {
      const itemRegistryActionIds = registryActionIdsByItem.get(item.id) ?? new Set<string>();
      if (item.deepLink && !itemRegistryActionIds.has(`attention.open:${item.id}`)) {
        actions.push({
          id: `attention.open:${item.id}`,
          title: `Open ${item.title}`,
          description: `Jump from ${mode} into the canonical detail surface for ${item.title}.`,
          group: "Inbox triage",
          enabled: true,
          availabilityReason: "Available because this item has a canonical deep link.",
          availabilitySource: "attention item",
          keywords: [item.title, item.projectLabel, item.decisionType],
          perform: () => openAttentionLink(item),
        });
      }
      if (item.approvalId && item.runId) {
        for (const actionId of ["approval.approve", "approval.reject"] as const) {
          if (itemRegistryActionIds.has(`${actionId}:${item.id}`)) {
            continue;
          }
          actions.push({
            id: `${actionId}:${item.id}`,
            title: `${actionId === "approval.approve" ? "Approve" : "Reject"} ${item.title}`,
            buttonLabel: actionId === "approval.approve" ? "Approve" : "Reject",
            description: item.summary,
            group: "Inbox approvals",
            tone: actionId === "approval.approve" ? "primary" : "secondary",
            enabled: pendingAction === null,
            availabilityReason: "Available because this attention item is a pending approval.",
            availabilitySource: "pending approval",
            keywords: [item.title, item.projectLabel, item.runLabel],
            perform: () => resolveApproval(item, actionId),
          });
        }
      }
    }
    return actions;
  }, [
    assignTarget,
    canResolveSelection,
    client,
    location.search,
    mode,
    navigate,
    pendingAction,
    registryActionIdsByItem,
    registryActions,
    requestRefresh,
    selectedItems,
    visibleItems,
  ]);

  useRegisterConsoleActions(pageActions);

  return (
    <Panel eyebrow={eyebrow} title={title}>
      {loading ? <p>{`Loading ${title}…`}</p> : null}
      {error ? <p className="error-copy">{error}</p> : null}
      <div className="stack">
        <div className="saved-views">
          <div className="saved-views__header">
            <div>
              <p className="eyebrow">Saved filters</p>
              <p className="saved-views__copy">
                Keep a stable triage lens for severity, decision type, source, and assignee.
              </p>
            </div>
            <div className="saved-views__actions">
              <label className="console-field saved-views__field">
                <span>View name</span>
                <input
                  placeholder="Critical approvals"
                  value={viewName}
                  onChange={(event) => setViewName(event.target.value)}
                />
              </label>
              <button
                className="primary-button"
                type="button"
                onClick={() => saveAttentionView(viewName || activeView?.name || `${title} view`, effectiveFilters)}
              >
                Save current view
              </button>
              <button className="secondary-button" type="button" onClick={() => resetAttentionFilters()}>
                Reset filters
              </button>
            </div>
          </div>
          <div className="saved-views__list">
            {preferences.attention.savedViews.length ? (
              preferences.attention.savedViews.map((view) => (
                <article
                  className={`saved-view-card${activeView?.id === view.id ? " saved-view-card--active" : ""}`}
                  key={view.id}
                >
                  <div>
                    <p className="saved-view-card__title">{view.name}</p>
                    <p className="saved-view-card__meta">
                      {view.filters.severity || "all severities"}
                      {" · "}
                      {view.filters.decisionType || "all decisions"}
                      {" · "}
                      {view.filters.assignee || "any assignee"}
                    </p>
                  </div>
                  <div className="saved-view-card__actions">
                    <button
                      className="secondary-button"
                      type="button"
                      onClick={() => setAttentionFilters(view.filters)}
                    >
                      {activeView?.id === view.id ? "Active" : "Apply"}
                    </button>
                    <button
                      className="danger-button"
                      type="button"
                      onClick={() => deleteAttentionView(view.id)}
                    >
                      Delete
                    </button>
                  </div>
                </article>
              ))
            ) : (
              <p className="saved-views__empty">No saved attention views yet.</p>
            )}
          </div>
        </div>

        <div className="filters">
          <label className="console-field">
            <span>Severity</span>
            <select
              value={attentionFilters.severity}
              onChange={(event) => updateFilters({ severity: event.target.value })}
            >
              <option value="">All severities</option>
              {severityOptions.map((severity) => (
                <option key={severity} value={severity}>{severity}</option>
              ))}
            </select>
          </label>
          <label className="console-field">
            <span>Decision</span>
            <select
              value={attentionFilters.decisionType}
              onChange={(event) => updateFilters({ decisionType: event.target.value })}
            >
              <option value="">All decision types</option>
              {decisionOptions.map((decisionType) => (
                <option key={decisionType} value={decisionType}>{decisionType}</option>
              ))}
            </select>
          </label>
          <label className="console-field">
            <span>Source</span>
            <select
              value={attentionFilters.source}
              onChange={(event) => updateFilters({ source: event.target.value })}
            >
              <option value="">All sources</option>
              {sourceOptions.map((source) => (
                <option key={source} value={source}>{source}</option>
              ))}
            </select>
          </label>
          <label className="console-field">
            <span>Assignee</span>
            <input
              placeholder="me"
              value={attentionFilters.assignee}
              onChange={(event) => updateFilters({ assignee: event.target.value })}
            />
          </label>
          {mode === "notifications" ? (
            <label className="console-field">
              <span>Tier</span>
              <select
                value={attentionFilters.tier}
                onChange={(event) => updateFilters({ tier: event.target.value })}
              >
                <option value="all">All notifications</option>
                <option value="actionable">Inbox-worthy</option>
                <option value="informational">Informational</option>
              </select>
            </label>
          ) : null}
          <label className="console-field attention-board__checkbox">
            <span>Show snoozed</span>
            <input
              aria-label="Show snoozed"
              checked={attentionFilters.showSnoozed}
              onChange={(event) => updateFilters({ showSnoozed: event.target.checked })}
              type="checkbox"
            />
          </label>
        </div>

        <div className="attention-board__summary">
          <p className="list-card__meta">
            Visible: {visibleItems.length} • Selected: {selectedIds.length} • Hidden dismissed: {hiddenCounts.dismissed} • Hidden resolved: {hiddenCounts.resolved}
          </p>
          {hiddenCounts.dismissed ? (
            <button
              className="secondary-button"
              type="button"
              onClick={() => clearAttentionDisposition("dismissed")}
            >
              Clear dismissed memory
            </button>
          ) : null}
          {hiddenCounts.resolved ? (
            <button
              className="secondary-button"
              type="button"
              onClick={() => clearAttentionDisposition("resolved")}
            >
              Clear resolved memory
            </button>
          ) : null}
        </div>

        {selectedItems.length ? (
          <div className="filters attention-board__bulk">
            <p className="list-card__meta">{selectionLabel(selectedItems.length)}</p>
            <div className="filters__actions">
              {canResolveSelection ? (
                <button className="primary-button" type="button" onClick={() => applyBulkDisposition("resolved")}>
                  Resolve selected
                </button>
              ) : null}
              <button className="secondary-button" type="button" onClick={() => applyBulkDisposition("dismissed")}>
                Dismiss selected
              </button>
              <label className="console-field">
                <span>Assign to</span>
                <select value={assignTarget} onChange={(event) => setAssignTarget(event.target.value)}>
                  {ASSIGNEE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <button className="secondary-button" type="button" onClick={() => applyBulkAssignee()}>
                Assign selected
              </button>
              <label className="console-field">
                <span>Snooze</span>
                <select value={snoozeSeconds} onChange={(event) => setSnoozeSeconds(event.target.value)}>
                  {SNOOZE_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </label>
              <button className="secondary-button" type="button" onClick={() => applyBulkSnooze()}>
                Snooze selected
              </button>
              <button className="secondary-button" type="button" onClick={() => clearSelection()}>
                Clear selection
              </button>
            </div>
          </div>
        ) : null}

        {groupedItems.length ? (
          groupedItems.map((group) => (
            <section className="stack stack--compact" key={group.key}>
              <div className="list-card__header">
                <h3>{group.label}</h3>
                <p className="list-card__meta">{group.items.length} item(s)</p>
              </div>
              {group.items.map((item) => {
                const triage = triageByItemId[item.id];
                return (
                  <article className="list-card" key={item.id}>
                    <div className="list-card__header">
                      <div>
                        <h3>{item.title}</h3>
                        <p className="list-card__meta">
                          {item.projectLabel}
                          {item.runId ? ` • ${item.runLabel}` : ""}
                          {triage?.assignee ? ` • Assigned: ${triage.assignee}` : ""}
                        </p>
                      </div>
                      <div className="filters__actions">
                        <StatusPill tone={item.severity}>{item.severityLabel}</StatusPill>
                        <StatusPill tone={item.decisionType}>{item.decisionLabel}</StatusPill>
                      </div>
                    </div>
                    <p>{item.summary}</p>
                    <div className="filters__actions">
                      <label className="list-card__meta">
                        <input
                          aria-label={`Select ${item.title}`}
                          checked={selectedIds.includes(item.id)}
                          onChange={() => toggleSelection(item.id)}
                          type="checkbox"
                        />
                        {" "}
                        Select
                      </label>
                      {item.deepLink ? (
                        <ConsoleLink to={item.deepLink}>
                          {item.runId ? "Open run" : "Open details"}
                        </ConsoleLink>
                      ) : null}
                      {item.approvalId && item.runId ? (
                        <div className="action-grid">
                          {pageActions
                            .filter(
                              (action) => {
                                const itemRegistryActionIds = registryActionIdsByItem.get(item.id);
                                if (itemRegistryActionIds) {
                                  return itemRegistryActionIds.has(action.id);
                                }
                                return (
                                  action.id === `approval.approve:${item.id}`
                                  || action.id === `approval.reject:${item.id}`
                                );
                              },
                            )
                            .map((action) => (
                              <ConsoleActionButton action={action} key={action.id} />
                            ))}
                        </div>
                      ) : null}
                      {supportsAction(item, "resolve") ? (
                        <button
                          className="primary-button"
                          type="button"
                          onClick={() => updateAttentionItem(item.id, { disposition: "resolved", snoozedUntil: null })}
                        >
                          Resolve
                        </button>
                      ) : null}
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => updateAttentionItem(item.id, { disposition: "dismissed", snoozedUntil: null })}
                      >
                        Dismiss
                      </button>
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => updateAttentionItem(item.id, { disposition: "active", assignee: "me" })}
                      >
                        Assign to me
                      </button>
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => updateAttentionItem(item.id, { disposition: "active", snoozedUntil: makeSnoozedUntil("3600") })}
                      >
                        Snooze 1h
                      </button>
                    </div>
                    <details className="list-card__details">
                      <summary>Why am I seeing this?</summary>
                      <p>{item.whyVisible}</p>
                    </details>
                    <details className="list-card__details">
                      <summary>What happens if I ignore it?</summary>
                      <p>{item.ignoreImpact}</p>
                    </details>
                  </article>
                );
              })}
            </section>
          ))
        ) : (
          <p>{emptyMessage}</p>
        )}
        {actionMessage ? <p>{actionMessage}</p> : null}
        {actionError ? <p className="error-copy">{actionError}</p> : null}
      </div>
    </Panel>
  );
}
