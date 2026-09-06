import { createContext, type PropsWithChildren, useCallback, useContext, useEffect, useRef, useState } from "react";

import {
  CONSOLE_PREFERENCES_KEY,
  DEFAULT_INBOX_FILTERS,
  DEFAULT_RUNS_FILTERS,
  clearInboxTriageEntries,
  deleteSavedRunsView,
  loadConsolePreferences,
  rememberRecentWorkspace,
  saveConsolePreferences,
  sameInboxFilters,
  type ConsoleDensity,
  type ConsolePage,
  type ConsolePreferences,
  type ConsoleTheme,
  type InboxFiltersPreference,
  type InboxTriageEntry,
  type RunsFiltersPreference,
  upsertInboxTriageEntries,
  upsertSavedRunsView,
} from "../preferences";

interface ConsolePreferencesContextValue {
  preferences: ConsolePreferences;
  setDensity: (density: ConsoleDensity) => void;
  setTheme: (theme: ConsoleTheme) => void;
  setDefaultPage: (page: ConsolePage) => void;
  setInboxFilters: (filters: InboxFiltersPreference) => void;
  setRunsFilters: (filters: RunsFiltersPreference) => void;
  setInboxTriage: (itemIds: string[], entry: InboxTriageEntry) => void;
  clearInboxTriage: (itemIds: string[]) => void;
  resetInboxFilters: () => void;
  saveRunsView: (name: string, filters: RunsFiltersPreference) => void;
  deleteRunsView: (viewId: string) => void;
  resetRunsFilters: () => void;
  rememberWorkspace: (workspacePath: string) => void;
}

const ConsolePreferencesContext = createContext<ConsolePreferencesContextValue | null>(null);
const PREFERENCES_SAVE_DEBOUNCE_MS = 250;

export function ConsolePreferencesProvider({ children }: PropsWithChildren) {
  const [preferences, setPreferences] = useState<ConsolePreferences>(() => loadConsolePreferences());
  const latestPreferencesRef = useRef(preferences);

  useEffect(() => {
    latestPreferencesRef.current = preferences;
  }, [preferences]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      saveConsolePreferences(preferences);
    }, PREFERENCES_SAVE_DEBOUNCE_MS);
    return () => window.clearTimeout(timeoutId);
  }, [preferences]);

  useEffect(() => {
    return () => {
      saveConsolePreferences(latestPreferencesRef.current);
    };
  }, []);

  useEffect(() => {
    function handleStorage(event: StorageEvent) {
      if (event.key !== CONSOLE_PREFERENCES_KEY) {
        return;
      }
      // JSDOM and some synthetic storage events omit storageArea entirely, so accept null
      // here as long as the event targets the console preferences key.
      if (event.storageArea !== null && event.storageArea !== window.localStorage) {
        return;
      }
      setPreferences(loadConsolePreferences());
    }

    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  function setDensity(density: ConsoleDensity) {
    setPreferences((current) => ({ ...current, density }));
  }

  function setTheme(theme: ConsoleTheme) {
    setPreferences((current) => ({ ...current, theme }));
  }

  function setDefaultPage(defaultPage: ConsolePage) {
    setPreferences((current) => ({ ...current, defaultPage }));
  }

  function setInboxFilters(filters: InboxFiltersPreference) {
    setPreferences((current) => {
      if (sameInboxFilters(current.inbox.filters, filters)) {
        return current;
      }
      return {
        ...current,
        inbox: {
          ...current.inbox,
          filters,
        },
      };
    });
  }

  function setRunsFilters(filters: RunsFiltersPreference) {
    setPreferences((current) => ({
      ...current,
      runs: {
        ...current.runs,
        filters,
      },
    }));
  }

  function saveRunsView(name: string, filters: RunsFiltersPreference) {
    setPreferences((current) => upsertSavedRunsView(current, name, filters));
  }

  function deleteRunsView(viewId: string) {
    setPreferences((current) => deleteSavedRunsView(current, viewId));
  }

  function resetRunsFilters() {
    setRunsFilters({ ...DEFAULT_RUNS_FILTERS });
  }

  function setInboxTriage(itemIds: string[], entry: InboxTriageEntry) {
    setPreferences((current) => upsertInboxTriageEntries(current, itemIds, entry));
  }

  function clearInboxTriage(itemIds: string[]) {
    setPreferences((current) => clearInboxTriageEntries(current, itemIds));
  }

  function resetInboxFilters() {
    setInboxFilters({ ...DEFAULT_INBOX_FILTERS });
  }

  const rememberWorkspace = useCallback((workspacePath: string) => {
    setPreferences((current) => rememberRecentWorkspace(current, workspacePath));
  }, []);

  return (
    <ConsolePreferencesContext.Provider
      value={{
        preferences,
        setDensity,
        setTheme,
        setDefaultPage,
        setInboxFilters,
        setRunsFilters,
        setInboxTriage,
        clearInboxTriage,
        resetInboxFilters,
        saveRunsView,
        deleteRunsView,
        resetRunsFilters,
        rememberWorkspace,
      }}
    >
      {children}
    </ConsolePreferencesContext.Provider>
  );
}

export function useConsolePreferences() {
  const context = useContext(ConsolePreferencesContext);
  if (!context) {
    throw new Error("useConsolePreferences must be used inside ConsolePreferencesProvider");
  }
  return context;
}
