import { createContext, type PropsWithChildren, useCallback, useContext, useEffect, useRef, useState } from "react";

import {
  CONSOLE_PREFERENCES_KEY,
  DEFAULT_RUNS_FILTERS,
  deleteSavedRunsView,
  loadConsolePreferences,
  rememberRecentWorkspace,
  saveConsolePreferences,
  type ConsoleDensity,
  type ConsolePage,
  type ConsolePreferences,
  type ConsoleTheme,
  type RunsFiltersPreference,
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
