import { createContext, type PropsWithChildren, useCallback, useContext, useEffect, useRef, useState } from "react";

import {
  CONSOLE_PREFERENCES_KEY,
  DEFAULT_ATTENTION_FILTERS,
  DEFAULT_RUNS_FILTERS,
  deleteSavedAttentionView,
  deleteSavedRunsView,
  loadConsolePreferences,
  rememberRecentWorkspace,
  saveConsolePreferences,
  type ConsoleDensity,
  type ConsolePage,
  type ConsolePreferences,
  type ConsoleTheme,
  type AttentionFiltersPreference,
  type AttentionTriagePreference,
  type RunsFiltersPreference,
  setAttentionFilters,
  updateAttentionTriage,
  upsertSavedAttentionView,
  upsertSavedRunsView,
} from "../preferences";

interface ConsolePreferencesContextValue {
  preferences: ConsolePreferences;
  setDensity: (density: ConsoleDensity) => void;
  setTheme: (theme: ConsoleTheme) => void;
  setDefaultPage: (page: ConsolePage) => void;
  setRunsFilters: (filters: RunsFiltersPreference) => void;
  saveRunsView: (name: string, filters: RunsFiltersPreference) => void;
  deleteRunsView: (viewId: string) => void;
  resetRunsFilters: () => void;
  setAttentionFilters: (filters: AttentionFiltersPreference) => void;
  saveAttentionView: (name: string, filters: AttentionFiltersPreference) => void;
  deleteAttentionView: (viewId: string) => void;
  resetAttentionFilters: () => void;
  updateAttentionItem: (
    itemId: string,
    update: Partial<AttentionTriagePreference>,
  ) => void;
  clearAttentionItem: (itemId: string) => void;
  clearAttentionDisposition: (disposition: AttentionTriagePreference["disposition"]) => void;
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

  function setAttentionFiltersValue(filters: AttentionFiltersPreference) {
    setPreferences((current) => setAttentionFilters(current, filters));
  }

  function saveAttentionView(name: string, filters: AttentionFiltersPreference) {
    setPreferences((current) => upsertSavedAttentionView(current, name, filters));
  }

  function deleteAttentionView(viewId: string) {
    setPreferences((current) => deleteSavedAttentionView(current, viewId));
  }

  function resetAttentionFilters() {
    setAttentionFiltersValue({ ...DEFAULT_ATTENTION_FILTERS });
  }

  function updateAttentionItem(itemId: string, update: Partial<AttentionTriagePreference>) {
    setPreferences((current) => updateAttentionTriage(current, itemId, update));
  }

  function clearAttentionItem(itemId: string) {
    setPreferences((current) => {
      if (!current.attention.triageByItemId[itemId]) {
        return current;
      }
      const nextTriage = { ...current.attention.triageByItemId };
      delete nextTriage[itemId];
      return {
        ...current,
        attention: {
          ...current.attention,
          triageByItemId: nextTriage,
        },
      };
    });
  }

  function clearAttentionDisposition(disposition: AttentionTriagePreference["disposition"]) {
    setPreferences((current) => {
      const nextEntries = Object.entries(current.attention.triageByItemId).filter(
        ([, entry]) => entry.disposition !== disposition,
      );
      if (nextEntries.length === Object.keys(current.attention.triageByItemId).length) {
        return current;
      }
      return {
        ...current,
        attention: {
          ...current.attention,
          triageByItemId: Object.fromEntries(nextEntries),
        },
      };
    });
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
        setRunsFilters,
        saveRunsView,
        deleteRunsView,
        resetRunsFilters,
        setAttentionFilters: setAttentionFiltersValue,
        saveAttentionView,
        deleteAttentionView,
        resetAttentionFilters,
        updateAttentionItem,
        clearAttentionItem,
        clearAttentionDisposition,
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
