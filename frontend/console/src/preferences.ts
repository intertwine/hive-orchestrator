import { CONSOLE_PAGE_IDS } from "./consolePages";

export const CONSOLE_PREFERENCES_KEY = "hive-console-operator-preferences";

export const CONSOLE_THEMES = ["clay", "ledger"] as const;
export const CONSOLE_DENSITIES = ["comfortable", "compact"] as const;
export const CONSOLE_PAGES = CONSOLE_PAGE_IDS;
export const MAX_SAVED_RUNS_VIEWS = 50;
export const MAX_RECENT_WORKSPACES = 8;
export const MAX_INBOX_TRIAGE_ITEMS = 400;

export type ConsoleTheme = (typeof CONSOLE_THEMES)[number];
export type ConsoleDensity = (typeof CONSOLE_DENSITIES)[number];
export type ConsolePage = (typeof CONSOLE_PAGES)[number];

export interface RunsFiltersPreference {
  projectId: string;
  driver: string;
  health: string;
  campaignId: string;
}

export interface SavedRunsView {
  id: string;
  name: string;
  filters: RunsFiltersPreference;
  createdAt: string;
}

export interface RunsPreferences {
  filters: RunsFiltersPreference;
  hiddenColumns: string[];
  pinnedPanels: string[];
  savedViews: SavedRunsView[];
}

export interface InboxFiltersPreference {
  severity: string;
  decisionType: string;
  projectId: string;
  sourceType: string;
  notificationLevel: string;
  showSnoozed: boolean;
}

export type InboxTriageStatus = "dismissed" | "resolved" | "snoozed";

export interface InboxTriageEntry {
  status: InboxTriageStatus;
  updatedAt: string;
  snoozedUntil?: string;
}

export interface InboxPreferences {
  filters: InboxFiltersPreference;
  triage: Record<string, InboxTriageEntry>;
}

export interface ConsolePreferences {
  version: 1;
  theme: ConsoleTheme;
  density: ConsoleDensity;
  defaultPage: ConsolePage;
  recentWorkspaces: string[];
  runs: RunsPreferences;
  inbox: InboxPreferences;
}

export const DEFAULT_RUNS_FILTERS: RunsFiltersPreference = {
  projectId: "",
  driver: "",
  health: "",
  campaignId: "",
};

export const DEFAULT_INBOX_FILTERS: InboxFiltersPreference = {
  severity: "",
  decisionType: "",
  projectId: "",
  sourceType: "",
  notificationLevel: "",
  showSnoozed: false,
};

export const DEFAULT_CONSOLE_PREFERENCES: ConsolePreferences = {
  version: 1,
  theme: "clay",
  density: "comfortable",
  defaultPage: "home",
  recentWorkspaces: [],
  runs: {
    filters: DEFAULT_RUNS_FILTERS,
    hiddenColumns: [],
    pinnedPanels: [],
    savedViews: [],
  },
  inbox: {
    filters: DEFAULT_INBOX_FILTERS,
    triage: {},
  },
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function readString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function readStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((entry): entry is string => typeof entry === "string");
}

function readBoolean(value: unknown, fallback = false): boolean {
  return typeof value === "boolean" ? value : fallback;
}

export function normalizeConsoleTheme(value: unknown): ConsoleTheme {
  return CONSOLE_THEMES.includes(value as ConsoleTheme) ? (value as ConsoleTheme) : "clay";
}

export function normalizeConsoleDensity(value: unknown): ConsoleDensity {
  return CONSOLE_DENSITIES.includes(value as ConsoleDensity)
    ? (value as ConsoleDensity)
    : "comfortable";
}

export function normalizeConsolePage(value: unknown): ConsolePage {
  return CONSOLE_PAGES.includes(value as ConsolePage) ? (value as ConsolePage) : "home";
}

export function normalizeRunsFilters(value: unknown): RunsFiltersPreference {
  if (!isRecord(value)) {
    return { ...DEFAULT_RUNS_FILTERS };
  }
  return {
    projectId: readString(value.projectId),
    driver: readString(value.driver),
    health: readString(value.health),
    campaignId: readString(value.campaignId),
  };
}

export function normalizeInboxFilters(value: unknown): InboxFiltersPreference {
  if (!isRecord(value)) {
    return { ...DEFAULT_INBOX_FILTERS };
  }
  return {
    severity: readString(value.severity),
    decisionType: readString(value.decisionType),
    projectId: readString(value.projectId),
    sourceType: readString(value.sourceType),
    notificationLevel: readString(value.notificationLevel),
    showSnoozed: readBoolean(value.showSnoozed),
  };
}

function normalizeInboxTriageEntry(value: unknown): InboxTriageEntry | null {
  if (!isRecord(value)) {
    return null;
  }
  const status = readString(value.status) as InboxTriageStatus;
  if (!["dismissed", "resolved", "snoozed"].includes(status)) {
    return null;
  }
  const updatedAt = readString(value.updatedAt, new Date(0).toISOString());
  const snoozedUntil = readString(value.snoozedUntil);
  return snoozedUntil
    ? { status, updatedAt, snoozedUntil }
    : { status, updatedAt };
}

function normalizeInboxTriageMap(value: unknown): Record<string, InboxTriageEntry> {
  if (!isRecord(value)) {
    return {};
  }
  const entries = Object.entries(value)
    .map(([key, entry]) => {
      const normalized = normalizeInboxTriageEntry(entry);
      return normalized ? [key, normalized] : null;
    })
    .filter((entry): entry is [string, InboxTriageEntry] => entry !== null)
    .sort((left, right) => left[1].updatedAt.localeCompare(right[1].updatedAt))
    .slice(-MAX_INBOX_TRIAGE_ITEMS);
  return Object.fromEntries(entries);
}

function normalizeSavedRunsView(value: unknown): SavedRunsView | null {
  if (!isRecord(value)) {
    return null;
  }
  const name = readString(value.name).trim();
  if (!name) {
    return null;
  }
  return {
    id: readString(value.id, `saved-view-${name.toLowerCase().replace(/\s+/g, "-")}`),
    name,
    filters: normalizeRunsFilters(value.filters),
    createdAt: readString(value.createdAt, new Date(0).toISOString()),
  };
}

export function normalizeConsolePreferences(value: unknown): ConsolePreferences {
  if (!isRecord(value)) {
    return {
      ...DEFAULT_CONSOLE_PREFERENCES,
      runs: { ...DEFAULT_CONSOLE_PREFERENCES.runs, filters: { ...DEFAULT_RUNS_FILTERS } },
      inbox: {
        ...DEFAULT_CONSOLE_PREFERENCES.inbox,
        filters: { ...DEFAULT_INBOX_FILTERS },
        triage: {},
      },
    };
  }

  const runs = isRecord(value.runs) ? value.runs : {};
  const inbox = isRecord(value.inbox) ? value.inbox : {};
  const savedViews = Array.isArray(runs.savedViews)
    ? runs.savedViews
      .map(normalizeSavedRunsView)
      .filter((entry): entry is SavedRunsView => entry !== null)
      .slice(-MAX_SAVED_RUNS_VIEWS)
    : [];

  return {
    version: 1,
    theme: normalizeConsoleTheme(value.theme),
    density: normalizeConsoleDensity(value.density),
    defaultPage: normalizeConsolePage(value.defaultPage),
    recentWorkspaces: readStringArray(value.recentWorkspaces)
      .map((workspace) => workspace.trim())
      .filter(Boolean)
      .slice(0, MAX_RECENT_WORKSPACES),
    runs: {
      filters: normalizeRunsFilters(runs.filters),
      hiddenColumns: readStringArray(runs.hiddenColumns),
      pinnedPanels: readStringArray(runs.pinnedPanels),
      savedViews,
    },
    inbox: {
      filters: normalizeInboxFilters(inbox.filters),
      triage: normalizeInboxTriageMap(inbox.triage),
    },
  };
}

export function loadConsolePreferences(storage: Pick<Storage, "getItem"> = window.localStorage) {
  const raw = storage.getItem(CONSOLE_PREFERENCES_KEY);
  if (!raw) {
    return normalizeConsolePreferences(null);
  }
  try {
    return normalizeConsolePreferences(JSON.parse(raw));
  } catch {
    return normalizeConsolePreferences(null);
  }
}

export function saveConsolePreferences(
  preferences: ConsolePreferences,
  storage: Pick<Storage, "setItem"> = window.localStorage,
) {
  storage.setItem(CONSOLE_PREFERENCES_KEY, JSON.stringify(preferences));
}

function makeSavedViewId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `saved-view-${Math.random().toString(36).slice(2, 10)}`;
}

export function upsertSavedRunsView(
  preferences: ConsolePreferences,
  name: string,
  filters: RunsFiltersPreference,
): ConsolePreferences {
  const trimmedName = name.trim();
  if (!trimmedName) {
    return preferences;
  }

  const existing = preferences.runs.savedViews.find(
    (view) => view.name.toLowerCase() === trimmedName.toLowerCase(),
  );
  const nextView: SavedRunsView = {
    id: existing?.id ?? makeSavedViewId(),
    name: trimmedName,
    filters: normalizeRunsFilters(filters),
    createdAt: existing?.createdAt ?? new Date().toISOString(),
  };
  const nextSavedViews = existing
    ? preferences.runs.savedViews.map((view) => (view.id === existing.id ? nextView : view))
    : [...preferences.runs.savedViews, nextView].slice(-MAX_SAVED_RUNS_VIEWS);

  return {
    ...preferences,
    runs: {
      ...preferences.runs,
      savedViews: nextSavedViews,
    },
  };
}

export function deleteSavedRunsView(preferences: ConsolePreferences, viewId: string): ConsolePreferences {
  return {
    ...preferences,
    runs: {
      ...preferences.runs,
      savedViews: preferences.runs.savedViews.filter((view) => view.id !== viewId),
    },
  };
}

export function rememberRecentWorkspace(
  preferences: ConsolePreferences,
  workspacePath: string,
): ConsolePreferences {
  const trimmedWorkspace = workspacePath.trim();
  if (!trimmedWorkspace) {
    return preferences;
  }

  const existing = preferences.recentWorkspaces.filter(
    (workspace) => workspace !== trimmedWorkspace,
  );
  const nextRecentWorkspaces = [trimmedWorkspace, ...existing].slice(0, MAX_RECENT_WORKSPACES);
  const isUnchanged = nextRecentWorkspaces.length === preferences.recentWorkspaces.length
    && nextRecentWorkspaces.every((workspace, index) => workspace === preferences.recentWorkspaces[index]);
  if (isUnchanged) {
    return preferences;
  }

  return {
    ...preferences,
    recentWorkspaces: nextRecentWorkspaces,
  };
}

export function sameInboxFilters(left: InboxFiltersPreference, right: InboxFiltersPreference) {
  return left.severity === right.severity
    && left.decisionType === right.decisionType
    && left.projectId === right.projectId
    && left.sourceType === right.sourceType
    && left.notificationLevel === right.notificationLevel
    && left.showSnoozed === right.showSnoozed;
}

export function upsertInboxTriageEntries(
  preferences: ConsolePreferences,
  itemIds: string[],
  entry: InboxTriageEntry,
): ConsolePreferences {
  const nextTriage = { ...preferences.inbox.triage };
  for (const itemId of itemIds.map((value) => value.trim()).filter(Boolean)) {
    nextTriage[itemId] = entry;
  }
  const capped = normalizeInboxTriageMap(nextTriage);
  return {
    ...preferences,
    inbox: {
      ...preferences.inbox,
      triage: capped,
    },
  };
}

export function clearInboxTriageEntries(
  preferences: ConsolePreferences,
  itemIds: string[],
): ConsolePreferences {
  if (!itemIds.length) {
    return preferences;
  }
  const nextTriage = { ...preferences.inbox.triage };
  for (const itemId of itemIds) {
    delete nextTriage[itemId];
  }
  return {
    ...preferences,
    inbox: {
      ...preferences.inbox,
      triage: nextTriage,
    },
  };
}

export function sameRunsFilters(left: RunsFiltersPreference, right: RunsFiltersPreference) {
  return left.projectId === right.projectId
    && left.driver === right.driver
    && left.health === right.health
    && left.campaignId === right.campaignId;
}
