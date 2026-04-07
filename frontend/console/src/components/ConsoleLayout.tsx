import {
  type ChangeEvent,
  type PropsWithChildren,
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import {
  ConsoleActionsProvider,
  useConsoleActions,
} from "./ConsoleActions";
import { ConsolePreferencesProvider, useConsolePreferences } from "./ConsolePreferences";
import { ConsoleEventBusProvider, FreshnessIndicator } from "./ConsoleEventBus";
import { ConsoleNavLink, preserveConsoleSearch } from "./ConsoleLink";
import {
  CONSOLE_PAGE_DESCRIPTIONS,
  CONSOLE_PAGE_LABELS,
  describeConsolePath,
} from "../consolePages";
import {
  CONSOLE_DENSITIES,
  CONSOLE_PAGES,
  CONSOLE_THEMES,
  normalizeConsoleDensity,
  normalizeConsolePage,
  normalizeConsoleTheme,
} from "../preferences";

const DEFAULT_API_BASE = window.location.pathname.startsWith("/console")
  ? window.location.origin
  : "http://127.0.0.1:8787";
const API_BASE_KEY = "hive-console-api-base";
const WORKSPACE_KEY = "hive-console-workspace";

interface ConsoleConfig {
  apiBase: string;
  workspacePath: string;
  setApiBase: (value: string) => void;
  setWorkspacePath: (value: string) => void;
}

const ConsoleConfigContext = createContext<ConsoleConfig>({
  apiBase: DEFAULT_API_BASE,
  workspacePath: "",
  setApiBase: () => undefined,
  setWorkspacePath: () => undefined,
});
const THEME_LABELS = {
  clay: "Clay",
  ledger: "Ledger",
} as const;
const DENSITY_LABELS = {
  comfortable: "Comfortable",
  compact: "Compact",
} as const;

export function useConsoleConfig() {
  return useContext(ConsoleConfigContext);
}

function TopNavLink({ to, label }: { to: string; label: string }) {
  return (
    <ConsoleNavLink
      className={({ isActive }) => `top-nav__link${isActive ? " top-nav__link--active" : ""}`}
      to={to}
    >
      {label}
    </ConsoleNavLink>
  );
}

function ConsoleShell({
  activePage,
  children,
  density,
  theme,
}: PropsWithChildren<{
  activePage: ReturnType<typeof describeConsolePath>;
  density: string;
  theme: string;
}>) {
  const {
    openPalette,
    primaryNavigationActions,
    secondaryNavigationActions,
  } = useConsoleActions();

  return (
    <div className="console-shell" data-density={density} data-theme={theme}>
      <header className="console-hero">
        <div>
          <p className="eyebrow">Agent Hive 2.5 Command Center</p>
          <h1>Command the work. Keep the truth in view.</h1>
          <p className="hero-copy">
            A browser-first operator console for live runs, approvals, campaigns, search traces,
            and the native companion surfaces introduced in v2.4.
          </p>
          <div className="hero-route-copy">
            <p className="hero-card__eyebrow">Current surface</p>
            <p className="hero-route-copy__title">{activePage.label}</p>
            <p className="hero-card__subtle">{CONSOLE_PAGE_DESCRIPTIONS[activePage.id]}</p>
          </div>
          <div className="hero-highlights" aria-label="Command center highlights">
            <span className="hero-highlight">Browser-first</span>
            <span className="hero-highlight">Review-ready</span>
            <span className="hero-highlight">Truthful state</span>
            <FreshnessIndicator />
          </div>
          <div className="hero-command-actions">
            <button className="secondary-button" onClick={openPalette} type="button">
              Open Command Palette
              <span className="hero-command-actions__shortcut">Ctrl/Cmd+K</span>
            </button>
          </div>
        </div>
        <ConsoleSettingsCard />
      </header>

      <nav className="top-nav">
        {primaryNavigationActions.map((action) => (
          <TopNavLink key={action.id} to={action.href ?? "/home"} label={action.title} />
        ))}
        {secondaryNavigationActions.map((action) => (
          <TopNavLink key={action.id} to={action.href ?? "/settings"} label={action.title} />
        ))}
      </nav>

      <main className="console-content">{children ?? <Outlet />}</main>
    </div>
  );
}

export function ConsoleSettingsCard({
  eyebrow = "Operator setup",
  note = "Point the UI at a local daemon and workspace without losing deep-linkability, then tune operator-local preferences without touching canonical Hive state.",
}: {
  eyebrow?: string;
  note?: string;
}) {
  const { apiBase, setApiBase, setWorkspacePath, workspacePath } = useConsoleConfig();
  const { preferences, setDefaultPage, setDensity, setTheme } = useConsolePreferences();

  function handleApiBaseChange(event: ChangeEvent<HTMLInputElement>) {
    setApiBase(event.target.value);
  }

  function handleWorkspaceChange(event: ChangeEvent<HTMLInputElement>) {
    setWorkspacePath(event.target.value);
  }

  return (
    <div className="console-settings">
      <p className="eyebrow">{eyebrow}</p>
      <label className="console-field">
        <span>API base</span>
        <input value={apiBase} onChange={handleApiBaseChange} />
      </label>
      <label className="console-field">
        <span>Workspace path</span>
        <input
          placeholder="/path/to/repo"
          value={workspacePath}
          onChange={handleWorkspaceChange}
        />
      </label>
      <label className="console-field">
        <span>Theme</span>
        <select
          aria-label="Theme"
          value={preferences.theme}
          onChange={(event) => setTheme(normalizeConsoleTheme(event.target.value))}
        >
          {CONSOLE_THEMES.map((theme) => (
            <option key={theme} value={theme}>
              {THEME_LABELS[theme]}
            </option>
          ))}
        </select>
      </label>
      <label className="console-field">
        <span>Density</span>
        <select
          aria-label="Density"
          value={preferences.density}
          onChange={(event) => setDensity(normalizeConsoleDensity(event.target.value))}
        >
          {CONSOLE_DENSITIES.map((density) => (
            <option key={density} value={density}>
              {DENSITY_LABELS[density]}
            </option>
          ))}
        </select>
      </label>
      <label className="console-field">
        <span>Default page</span>
        <select
          aria-label="Default page"
          value={preferences.defaultPage}
          onChange={(event) => setDefaultPage(normalizeConsolePage(event.target.value))}
        >
          {CONSOLE_PAGES.map((page) => (
            <option key={page} value={page}>
              {CONSOLE_PAGE_LABELS[page]}
            </option>
          ))}
        </select>
      </label>
      <p className="console-settings__note">{note}</p>
    </div>
  );
}

function ConsoleLayoutBody({ children }: PropsWithChildren) {
  const { preferences, rememberWorkspace } = useConsolePreferences();
  const [apiBase, setApiBase] = useState(
    window.localStorage.getItem(API_BASE_KEY) ?? DEFAULT_API_BASE,
  );
  const [workspacePath, setWorkspacePath] = useState(
    window.localStorage.getItem(WORKSPACE_KEY) ?? "",
  );
  const location = useLocation();
  const navigate = useNavigate();
  const explicitConfigQuery = useRef(false);
  const configTouched = useRef(false);
  const searchParams = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const queryApiBase = searchParams.get("apiBase");
  const queryWorkspacePath = searchParams.get("workspace");
  const previousQueryApiBase = useRef(queryApiBase);
  const previousQueryWorkspacePath = useRef(queryWorkspacePath);
  const activePage = describeConsolePath(location.pathname);
  const rememberedInitialWorkspace = useRef(false);

  useEffect(() => {
    explicitConfigQuery.current = explicitConfigQuery.current
      || queryApiBase !== null
      || queryWorkspacePath !== null;
  }, [queryApiBase, queryWorkspacePath]);

  useEffect(() => {
    const queryChanged = previousQueryApiBase.current !== queryApiBase;
    previousQueryApiBase.current = queryApiBase;
    if (queryApiBase === null || queryApiBase === apiBase) {
      return;
    }
    if (!configTouched.current || queryChanged) {
      // Fresh explicit deep links should retake control even after local edits.
      configTouched.current = false;
      setApiBase(queryApiBase);
    }
  }, [apiBase, queryApiBase]);

  useEffect(() => {
    const queryChanged = previousQueryWorkspacePath.current !== queryWorkspacePath;
    previousQueryWorkspacePath.current = queryWorkspacePath;
    if (queryWorkspacePath === null || queryWorkspacePath === workspacePath) {
      return;
    }
    if (!configTouched.current || queryChanged) {
      // Fresh explicit deep links should retake control even after local edits.
      configTouched.current = false;
      setWorkspacePath(queryWorkspacePath);
    }
  }, [queryWorkspacePath, workspacePath]);

  useEffect(() => {
    if (queryApiBase !== null && apiBase === queryApiBase) {
      return;
    }
    window.localStorage.setItem(API_BASE_KEY, apiBase);
  }, [apiBase, queryApiBase]);

  useEffect(() => {
    if (queryWorkspacePath !== null && workspacePath === queryWorkspacePath) {
      return;
    }
    window.localStorage.setItem(WORKSPACE_KEY, workspacePath);
  }, [queryWorkspacePath, workspacePath]);

  useEffect(() => {
    const trimmedWorkspacePath = workspacePath.trim();
    const shouldRememberInitialWorkspace = (
      !rememberedInitialWorkspace.current
      && !configTouched.current
      && queryWorkspacePath === null
      && !!trimmedWorkspacePath
    );
    const shouldRememberQueryWorkspace = (
      !configTouched.current
      && queryWorkspacePath !== null
      && queryWorkspacePath === trimmedWorkspacePath
      && !!trimmedWorkspacePath
    );
    if (!shouldRememberInitialWorkspace && !shouldRememberQueryWorkspace) {
      return;
    }
    if (shouldRememberInitialWorkspace) {
      rememberedInitialWorkspace.current = true;
    }
    rememberWorkspace(trimmedWorkspacePath);
  }, [queryWorkspacePath, rememberWorkspace, workspacePath]);

  useEffect(() => {
    if (!explicitConfigQuery.current && !configTouched.current) {
      return;
    }
    const timeoutId = window.setTimeout(() => {
      // Debounce typed config edits so we do not churn router state on every keystroke.
      const params = new URLSearchParams(searchParams);
      const currentApiBase = params.get("apiBase");
      const trimmedApiBase = apiBase.trim();
      const trimmedWorkspacePath = workspacePath.trim();
      const shouldKeepApiBase = currentApiBase !== null || trimmedApiBase !== DEFAULT_API_BASE;

      if (shouldKeepApiBase) {
        params.set("apiBase", trimmedApiBase);
      } else {
        params.delete("apiBase");
      }

      if (trimmedWorkspacePath) {
        params.set("workspace", trimmedWorkspacePath);
      } else {
        params.delete("workspace");
      }

      const nextSearch = params.toString();
      const normalizedSearch = nextSearch ? `?${nextSearch}` : "";
      if (normalizedSearch === location.search) {
        return;
      }
      navigate(
        preserveConsoleSearch({ pathname: location.pathname }, normalizedSearch),
        { replace: true },
      );
    }, 120);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [apiBase, location.pathname, location.search, navigate, searchParams, workspacePath]);

  return (
    <ConsoleConfigContext.Provider
      value={{
        apiBase,
        workspacePath,
        setApiBase: (value) => {
          configTouched.current = true;
          setApiBase(value);
        },
        setWorkspacePath: (value) => {
          configTouched.current = true;
          setWorkspacePath(value);
        },
      }}
    >
      <ConsoleEventBusProvider apiBase={apiBase} workspacePath={workspacePath}>
        <ConsoleActionsProvider>
          <ConsoleShell
            activePage={activePage}
            density={preferences.density}
            theme={preferences.theme}
          >
            {children}
          </ConsoleShell>
        </ConsoleActionsProvider>
      </ConsoleEventBusProvider>
    </ConsoleConfigContext.Provider>
  );
}

export function ConsoleLayout({ children }: PropsWithChildren) {
  return (
    <ConsolePreferencesProvider>
      <ConsoleLayoutBody>{children}</ConsoleLayoutBody>
    </ConsolePreferencesProvider>
  );
}
