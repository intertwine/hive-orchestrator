import { CONSOLE_PAGE_IDS } from "./consolePages";

export const CONSOLE_PREFERENCES_KEY = "hive-console-operator-preferences";

export const CONSOLE_THEMES = ["clay", "ledger"] as const;
export const CONSOLE_DENSITIES = ["comfortable", "compact"] as const;
export const CONSOLE_PAGES = CONSOLE_PAGE_IDS;
export const MAX_SAVED_RUNS_VIEWS = 50;
export const MAX_SAVED_ATTENTION_VIEWS = 30;
export const MAX_ATTENTION_TRIAGE_ITEMS = 200;
export const MAX_RECENT_WORKSPACES = 8;

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

export interface AttentionFiltersPreference {
  severity: string;
  decisionType: string;
  source: string;
  assignee: string;
  tier: string;
  showSnoozed: boolean;
}

export interface SavedAttentionView {
  id: string;
  name: string;
  filters: AttentionFiltersPreference;
  createdAt: string;
}

export type AttentionDisposition = "active" | "dismissed" | "resolved";

export interface AttentionTriagePreference {
  disposition: AttentionDisposition;
  assignee: string;
  snoozedUntil: string | null;
  updatedAt: string;
}

export interface AttentionPreferences {
  filters: AttentionFiltersPreference;
  savedViews: SavedAttentionView[];
  triageByItemId: Record<string, AttentionTriagePreference>;
}

export interface NotificationPreferences {
  showActionable: boolean;
  showInformational: boolean;
}

export interface KeyboardPreferences {
  showShortcutBadges: boolean;
}

export interface ConsolePreferences {
  version: 1;
  theme: ConsoleTheme;
  density: ConsoleDensity;
  defaultPage: ConsolePage;
  recentWorkspaces: string[];
  runs: RunsPreferences;
  attention: AttentionPreferences;
  notifications: NotificationPreferences;
  keyboard: KeyboardPreferences;
}

export const DEFAULT_RUNS_FILTERS: RunsFiltersPreference = {
  projectId: "",
  driver: "",
  health: "",
  campaignId: "",
};

export const DEFAULT_ATTENTION_FILTERS: AttentionFiltersPreference = {
  severity: "",
  decisionType: "",
  source: "",
  assignee: "",
  tier: "all",
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
  attention: {
    filters: DEFAULT_ATTENTION_FILTERS,
    savedViews: [],
    triageByItemId: {},
  },
  notifications: {
    showActionable: true,
    showInformational: true,
  },
  keyboard: {
    showShortcutBadges: true,
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

function readBoolean(value: unknown, fallback = false) {
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

export function normalizeAttentionFilters(value: unknown): AttentionFiltersPreference {
  if (!isRecord(value)) {
    return { ...DEFAULT_ATTENTION_FILTERS };
  }
  const tier = readString(value.tier, DEFAULT_ATTENTION_FILTERS.tier);
  return {
    severity: readString(value.severity),
    decisionType: readString(value.decisionType),
    source: readString(value.source),
    assignee: readString(value.assignee),
    tier: tier || DEFAULT_ATTENTION_FILTERS.tier,
    showSnoozed: readBoolean(value.showSnoozed),
  };
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

function normalizeSavedAttentionView(value: unknown): SavedAttentionView | null {
  if (!isRecord(value)) {
    return null;
  }
  const name = readString(value.name).trim();
  if (!name) {
    return null;
  }
  return {
    id: readString(value.id, `attention-view-${name.toLowerCase().replace(/\s+/g, "-")}`),
    name,
    filters: normalizeAttentionFilters(value.filters),
    createdAt: readString(value.createdAt, new Date(0).toISOString()),
  };
}

function normalizeAttentionTriagePreference(value: unknown): AttentionTriagePreference | null {
  if (!isRecord(value)) {
    return null;
  }
  const disposition = readString(value.disposition, "active");
  if (!["active", "dismissed", "resolved"].includes(disposition)) {
    return null;
  }
  return {
    disposition: disposition as AttentionDisposition,
    assignee: readString(value.assignee),
    snoozedUntil: readString(value.snoozedUntil) || null,
    updatedAt: readString(value.updatedAt, new Date(0).toISOString()),
  };
}

function limitAttentionTriageEntries(
  triageByItemId: Record<string, AttentionTriagePreference>,
): Record<string, AttentionTriagePreference> {
  const entries = Object.entries(triageByItemId);
  if (entries.length <= MAX_ATTENTION_TRIAGE_ITEMS) {
    return triageByItemId;
  }
  return Object.fromEntries(
    entries
      .sort((left, right) => left[1].updatedAt.localeCompare(right[1].updatedAt))
      .slice(-MAX_ATTENTION_TRIAGE_ITEMS),
  );
}

export function normalizeConsolePreferences(value: unknown): ConsolePreferences {
  if (!isRecord(value)) {
    return {
      ...DEFAULT_CONSOLE_PREFERENCES,
      runs: { ...DEFAULT_CONSOLE_PREFERENCES.runs, filters: { ...DEFAULT_RUNS_FILTERS } },
    };
  }

  const runs = isRecord(value.runs) ? value.runs : {};
  const savedViews = Array.isArray(runs.savedViews)
    ? runs.savedViews
      .map(normalizeSavedRunsView)
      .filter((entry): entry is SavedRunsView => entry !== null)
      .slice(-MAX_SAVED_RUNS_VIEWS)
    : [];
  const attention = isRecord(value.attention) ? value.attention : {};
  const attentionSavedViews = Array.isArray(attention.savedViews)
    ? attention.savedViews
      .map(normalizeSavedAttentionView)
      .filter((entry): entry is SavedAttentionView => entry !== null)
      .slice(-MAX_SAVED_ATTENTION_VIEWS)
    : [];
  const triageByItemId = isRecord(attention.triageByItemId)
    ? limitAttentionTriageEntries(
      Object.fromEntries(
        Object.entries(attention.triageByItemId)
          .map(([itemId, entry]) => [itemId, normalizeAttentionTriagePreference(entry)] as const)
          .filter((entry): entry is [string, AttentionTriagePreference] => entry[1] !== null),
      ),
    )
    : {};
  const notifications = isRecord(value.notifications) ? value.notifications : {};
  const keyboard = isRecord(value.keyboard) ? value.keyboard : {};

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
    attention: {
      filters: normalizeAttentionFilters(attention.filters),
      savedViews: attentionSavedViews,
      triageByItemId,
    },
    notifications: {
      showActionable: readBoolean(
        notifications.showActionable,
        DEFAULT_CONSOLE_PREFERENCES.notifications.showActionable,
      ),
      showInformational: readBoolean(
        notifications.showInformational,
        DEFAULT_CONSOLE_PREFERENCES.notifications.showInformational,
      ),
    },
    keyboard: {
      showShortcutBadges: readBoolean(
        keyboard.showShortcutBadges,
        DEFAULT_CONSOLE_PREFERENCES.keyboard.showShortcutBadges,
      ),
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

export function upsertSavedAttentionView(
  preferences: ConsolePreferences,
  name: string,
  filters: AttentionFiltersPreference,
): ConsolePreferences {
  const trimmedName = name.trim();
  if (!trimmedName) {
    return preferences;
  }

  const existing = preferences.attention.savedViews.find(
    (view) => view.name.toLowerCase() === trimmedName.toLowerCase(),
  );
  const nextView: SavedAttentionView = {
    id: existing?.id ?? makeSavedViewId(),
    name: trimmedName,
    filters: normalizeAttentionFilters(filters),
    createdAt: existing?.createdAt ?? new Date().toISOString(),
  };
  const nextSavedViews = existing
    ? preferences.attention.savedViews.map((view) => (view.id === existing.id ? nextView : view))
    : [...preferences.attention.savedViews, nextView].slice(-MAX_SAVED_ATTENTION_VIEWS);

  return {
    ...preferences,
    attention: {
      ...preferences.attention,
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

export function deleteSavedAttentionView(
  preferences: ConsolePreferences,
  viewId: string,
): ConsolePreferences {
  return {
    ...preferences,
    attention: {
      ...preferences.attention,
      savedViews: preferences.attention.savedViews.filter((view) => view.id !== viewId),
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

export function sameRunsFilters(left: RunsFiltersPreference, right: RunsFiltersPreference) {
  return left.projectId === right.projectId
    && left.driver === right.driver
    && left.health === right.health
    && left.campaignId === right.campaignId;
}

export function sameAttentionFilters(left: AttentionFiltersPreference, right: AttentionFiltersPreference) {
  return left.severity === right.severity
    && left.decisionType === right.decisionType
    && left.source === right.source
    && left.assignee === right.assignee
    && left.tier === right.tier
    && left.showSnoozed === right.showSnoozed;
}

export function setAttentionFilters(
  preferences: ConsolePreferences,
  filters: AttentionFiltersPreference,
): ConsolePreferences {
  return {
    ...preferences,
    attention: {
      ...preferences.attention,
      filters: normalizeAttentionFilters(filters),
    },
  };
}

export function updateAttentionTriage(
  preferences: ConsolePreferences,
  itemId: string,
  update: Partial<AttentionTriagePreference>,
): ConsolePreferences {
  const current = preferences.attention.triageByItemId[itemId] ?? {
    disposition: "active" as AttentionDisposition,
    assignee: "",
    snoozedUntil: null,
    updatedAt: new Date(0).toISOString(),
  };
  return {
    ...preferences,
    attention: {
      ...preferences.attention,
      triageByItemId: limitAttentionTriageEntries({
        ...preferences.attention.triageByItemId,
        [itemId]: {
          ...current,
          ...update,
          updatedAt: new Date().toISOString(),
        },
      }),
    },
  };
}
