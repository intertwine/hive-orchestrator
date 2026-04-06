import { NavLink } from "react-router-dom";
import { type ChangeEvent, type PropsWithChildren, createContext, useContext, useEffect, useState } from "react";

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

export function ConsoleLayout({ children }: PropsWithChildren) {
  const queryApiBase = queryParamValue("apiBase");
  const queryWorkspacePath = queryParamValue("workspace");
  const [apiBase, setApiBase] = useState(
    queryApiBase ?? window.localStorage.getItem(API_BASE_KEY) ?? DEFAULT_API_BASE,
  );
  const [workspacePath, setWorkspacePath] = useState(
    queryWorkspacePath ?? window.localStorage.getItem(WORKSPACE_KEY) ?? "",
  );

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

  function handleApiBaseChange(event: ChangeEvent<HTMLInputElement>) {
    setApiBase(event.target.value);
  }

  function handleWorkspaceChange(event: ChangeEvent<HTMLInputElement>) {
    setWorkspacePath(event.target.value);
  }

  return (
    <ConsoleConfigContext.Provider value={{ apiBase, workspacePath }}>
      <div className="console-shell">
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
            <p className="console-settings__note">
              Point the UI at a local daemon and workspace without losing deep-linkability.
            </p>
          </div>
        </header>

        <nav className="top-nav">
          <TopNavLink to="/" label="Home" />
          <TopNavLink to="/inbox" label="Inbox" />
          <TopNavLink to="/runs" label="Runs" />
          <TopNavLink to="/campaigns" label="Campaigns" />
          <TopNavLink to="/projects" label="Projects" />
          <TopNavLink to="/search" label="Search" />
        </nav>

        <main className="console-content">{children}</main>
      </div>
    </ConsoleConfigContext.Provider>
  );
}
