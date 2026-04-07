import type { JsonRecord } from "./api/client";
import type {
  AttentionFiltersPreference,
  AttentionTriagePreference,
} from "./preferences";

export interface AttentionItem {
  id: string;
  title: string;
  summary: string;
  reason: string;
  severity: string;
  severityLabel: string;
  decisionType: string;
  decisionLabel: string;
  groupKey: string;
  groupLabel: string;
  notificationTier: string;
  source: string;
  status: string;
  bulkActions: string[];
  deepLink: string | null;
  occurredAt: string;
  projectId: string;
  projectLabel: string;
  runId: string;
  runLabel: string;
  approvalId: string;
  whyVisible: string;
  ignoreImpact: string;
}

export interface AttentionGroup {
  key: string;
  label: string;
  severity: string;
  decisionType: string;
  items: AttentionItem[];
}

function readString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function capitalize(value: string) {
  return value ? `${value[0]!.toUpperCase()}${value.slice(1)}` : value;
}

function fallbackDecisionType(kind: string) {
  if (kind === "approval-request" || kind === "delegate-approval") {
    return "approval";
  }
  if (kind === "run-review" || kind === "delegate-blocked") {
    return "review";
  }
  if (kind === "run-input") {
    return "input";
  }
  if (kind === "run-blocked" || kind === "run-failed" || kind === "run-escalated" || kind === "delegate-error") {
    return "failure";
  }
  if (kind === "project-blocked") {
    return "blocker";
  }
  if (kind === "delegate-note") {
    return "delegate";
  }
  return "informational";
}

function fallbackSeverity(kind: string) {
  if (kind === "approval-request" || kind === "delegate-approval" || kind === "run-review") {
    return "critical";
  }
  if (kind === "run-blocked" || kind === "run-failed" || kind === "run-escalated" || kind === "delegate-error") {
    return "high";
  }
  if (kind === "run-input" || kind === "delegate-blocked" || kind === "project-blocked") {
    return "medium";
  }
  if (kind === "delegate-note") {
    return "low";
  }
  return "info";
}

function fallbackDecisionLabel(decisionType: string) {
  return capitalize(decisionType.replace(/-/g, " "));
}

export function normalizeAttentionItem(value: JsonRecord): AttentionItem {
  const kind = readString(value.kind, "attention-item");
  const runId = readString(value.run_id);
  const projectId = readString(value.project_id);
  const severity = readString(value.severity, fallbackSeverity(kind));
  const decisionType = readString(value.decision_type, fallbackDecisionType(kind));
  const decisionLabel = readString(value.decision_label, fallbackDecisionLabel(decisionType));
  return {
    id: readString(value.id, readString(value.title, "attention-item")),
    title: readString(value.title, "Attention item"),
    summary: readString(value.summary, readString(value.reason, "Needs operator attention.")),
    reason: readString(value.reason, "Needs operator attention."),
    severity,
    severityLabel: readString(value.severity_label, capitalize(severity)),
    decisionType,
    decisionLabel,
    groupKey: readString(value.group_key, `${severity}:${decisionType}`),
    groupLabel: readString(value.group_label, `${capitalize(severity)} · ${decisionLabel}`),
    notificationTier: readString(
      value.notification_tier,
      kind === "accepted-run" || kind === "event-notification" ? "informational" : "actionable",
    ),
    source: readString(value.source, kind.startsWith("delegate") ? "delegate" : "workspace"),
    status: readString(value.status, "pending"),
    bulkActions: Array.isArray(value.bulk_actions)
      ? value.bulk_actions.filter((entry): entry is string => typeof entry === "string")
      : [],
    deepLink: readString(value.deep_link) || (runId ? `/runs/${runId}` : projectId ? `/projects/${projectId}` : null),
    occurredAt: readString(value.occurred_at),
    projectId,
    projectLabel: readString(value.project_label, readString(value.project_id, "Project")),
    runId,
    runLabel: readString(value.run_label, readString(value.run_id, "Run")),
    approvalId: readString(value.approval_id),
    whyVisible: readString(value.why_visible, "This item was surfaced for operator attention."),
    ignoreImpact: readString(value.ignore_impact, "Ignoring this only changes your local queue state."),
  };
}

export function isAttentionItemSnoozed(
  triage: AttentionTriagePreference | undefined,
  now = Date.now(),
) {
  if (!triage?.snoozedUntil) {
    return false;
  }
  const snoozedUntil = Date.parse(triage.snoozedUntil);
  if (Number.isNaN(snoozedUntil)) {
    return false;
  }
  return snoozedUntil > now;
}

export function matchesAttentionFilters(
  item: AttentionItem,
  filters: AttentionFiltersPreference,
  triage: AttentionTriagePreference | undefined,
  now = Date.now(),
) {
  if (filters.severity && item.severity !== filters.severity) {
    return false;
  }
  if (filters.decisionType && item.decisionType !== filters.decisionType) {
    return false;
  }
  if (filters.source && item.source !== filters.source) {
    return false;
  }
  if (filters.tier && filters.tier !== "all" && item.notificationTier !== filters.tier) {
    return false;
  }
  if (filters.assignee && readString(triage?.assignee) !== filters.assignee) {
    return false;
  }
  if (!filters.showSnoozed && isAttentionItemSnoozed(triage, now)) {
    return false;
  }
  return true;
}

export function groupAttentionItems(items: AttentionItem[]) {
  const groups = new Map<string, AttentionGroup>();
  for (const item of items) {
    const existing = groups.get(item.groupKey);
    if (existing) {
      existing.items.push(item);
      continue;
    }
    groups.set(item.groupKey, {
      key: item.groupKey,
      label: item.groupLabel,
      severity: item.severity,
      decisionType: item.decisionType,
      items: [item],
    });
  }
  return Array.from(groups.values());
}
