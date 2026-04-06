import { createContext, type PropsWithChildren, useContext, useEffect, useState } from "react";

import {
  DEFAULT_RUNS_FILTERS,
  deleteSavedRunsView,
  loadConsolePreferences,
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
}

const ConsolePreferencesContext = createContext<ConsolePreferencesContextValue | null>(null);

export function ConsolePreferencesProvider({ children }: PropsWithChildren) {
  const [preferences, setPreferences] = useState<ConsolePreferences>(() => loadConsolePreferences());

  useEffect(() => {
    saveConsolePreferences(preferences);
  }, [preferences]);

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
