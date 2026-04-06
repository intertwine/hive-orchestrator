import { CONSOLE_PAGE_IDS } from "./consolePages";

export const CONSOLE_PREFERENCES_KEY = "hive-console-operator-preferences";

export const CONSOLE_THEMES = ["clay", "ledger"] as const;
export const CONSOLE_DENSITIES = ["comfortable", "compact"] as const;
export const CONSOLE_PAGES = CONSOLE_PAGE_IDS;
export const MAX_SAVED_RUNS_VIEWS = 50;

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

export interface ConsolePreferences {
  version: 1;
  theme: ConsoleTheme;
  density: ConsoleDensity;
  defaultPage: ConsolePage;
  runs: RunsPreferences;
}

export const DEFAULT_RUNS_FILTERS: RunsFiltersPreference = {
  projectId: "",
  driver: "",
  health: "",
  campaignId: "",
};

export const DEFAULT_CONSOLE_PREFERENCES: ConsolePreferences = {
  version: 1,
  theme: "clay",
  density: "comfortable",
  defaultPage: "home",
  runs: {
    filters: DEFAULT_RUNS_FILTERS,
    hiddenColumns: [],
    pinnedPanels: [],
    savedViews: [],
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
    };
  }

  const runs = isRecord(value.runs) ? value.runs : {};
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
    runs: {
      filters: normalizeRunsFilters(runs.filters),
      hiddenColumns: readStringArray(runs.hiddenColumns),
      pinnedPanels: readStringArray(runs.pinnedPanels),
      savedViews,
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

export function sameRunsFilters(left: RunsFiltersPreference, right: RunsFiltersPreference) {
  return left.projectId === right.projectId
    && left.driver === right.driver
    && left.health === right.health
    && left.campaignId === right.campaignId;
}
