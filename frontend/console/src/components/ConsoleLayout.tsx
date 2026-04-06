import { NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  type ChangeEvent,
  type PropsWithChildren,
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

import { ConsolePreferencesProvider, useConsolePreferences } from "./ConsolePreferences";

const DEFAULT_API_BASE = window.location.pathname.startsWith("/console")
  ? window.location.origin
  : "http://127.0.0.1:8787";
const API_BASE_KEY = "hive-console-api-base";
const WORKSPACE_KEY = "hive-console-workspace";

function queryParamValue(name: string): string | null {
  return new URLSearchParams(window.location.search).get(name);
}

interface ConsoleConfig {
  apiBase: string;
  workspacePath: string;
}

const ConsoleConfigContext = createContext<ConsoleConfig>({
  apiBase: DEFAULT_API_BASE,
  workspacePath: "",
});

export function useConsoleConfig() {
  return useContext(ConsoleConfigContext);
}

function TopNavLink({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      className={({ isActive }) => `top-nav__link${isActive ? " top-nav__link--active" : ""}`}
      to={to}
    >
      {label}
    </NavLink>
  );
}

function ConsoleLayoutBody({ children }: PropsWithChildren) {
  const queryApiBase = queryParamValue("apiBase");
  const queryWorkspacePath = queryParamValue("workspace");
  const [apiBase, setApiBase] = useState(
    queryApiBase ?? window.localStorage.getItem(API_BASE_KEY) ?? DEFAULT_API_BASE,
  );
  const [workspacePath, setWorkspacePath] = useState(
    queryWorkspacePath ?? window.localStorage.getItem(WORKSPACE_KEY) ?? "",
  );
  const { preferences, setDefaultPage, setDensity, setTheme } = useConsolePreferences();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectedDefaultPage = useRef(false);

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
    if (redirectedDefaultPage.current || preferences.defaultPage === "home") {
      return;
    }
    if (location.pathname !== "/") {
      return;
    }
    redirectedDefaultPage.current = true;
    navigate(`/${preferences.defaultPage}`, { replace: true });
  }, [location.pathname, navigate, preferences.defaultPage]);

  function handleApiBaseChange(event: ChangeEvent<HTMLInputElement>) {
    setApiBase(event.target.value);
  }

  function handleWorkspaceChange(event: ChangeEvent<HTMLInputElement>) {
    setWorkspacePath(event.target.value);
  }

  return (
    <ConsoleConfigContext.Provider value={{ apiBase, workspacePath }}>
      <div
        className="console-shell"
        data-density={preferences.density}
        data-theme={preferences.theme}
      >
        <header className="console-hero">
          <div>
            <p className="eyebrow">Agent Hive 2.5 Command Center</p>
            <h1>Command the work. Keep the truth in view.</h1>
            <p className="hero-copy">
              A browser-first operator console for live runs, approvals, campaigns, search traces,
              and the native companion surfaces introduced in v2.4.
            </p>
            <div className="hero-highlights" aria-label="Command center highlights">
              <span className="hero-highlight">Browser-first</span>
              <span className="hero-highlight">Review-ready</span>
              <span className="hero-highlight">Truthful state</span>
            </div>
          </div>

          <div className="console-settings">
            <p className="eyebrow">Operator setup</p>
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
                onChange={(event) => setTheme(event.target.value as "clay" | "ledger")}
              >
                <option value="clay">Clay</option>
                <option value="ledger">Ledger</option>
              </select>
            </label>
            <label className="console-field">
              <span>Density</span>
              <select
                aria-label="Density"
                value={preferences.density}
                onChange={(event) => setDensity(event.target.value as "comfortable" | "compact")}
              >
                <option value="comfortable">Comfortable</option>
                <option value="compact">Compact</option>
              </select>
            </label>
            <label className="console-field">
              <span>Default page</span>
              <select
                aria-label="Default page"
                value={preferences.defaultPage}
                onChange={(event) => {
                  setDefaultPage(
                    event.target.value as
                      | "home"
                      | "runs"
                      | "inbox"
                      | "campaigns"
                      | "projects"
                      | "search",
                  );
                }}
              >
                <option value="home">Home</option>
                <option value="runs">Runs</option>
                <option value="inbox">Inbox</option>
                <option value="campaigns">Campaigns</option>
                <option value="projects">Projects</option>
                <option value="search">Search</option>
              </select>
            </label>
            <p className="console-settings__note">
              Point the UI at a local daemon and workspace without losing deep-linkability, then
              tune operator-local preferences without touching canonical Hive state.
            </p>
          </div>
        </header>

        <nav className="top-nav">
          <TopNavLink to="/" label="Home" />
          <TopNavLink to="/runs" label="Runs" />
          <TopNavLink to="/inbox" label="Inbox" />
          <TopNavLink to="/campaigns" label="Campaigns" />
          <TopNavLink to="/projects" label="Projects" />
          <TopNavLink to="/search" label="Search" />
        </nav>

        <main className="console-content">{children}</main>
      </div>
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
