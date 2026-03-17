import { NavLink } from "react-router-dom";
import { type ChangeEvent, type PropsWithChildren, createContext, useContext, useEffect, useState } from "react";

const DEFAULT_API_BASE = window.location.pathname.startsWith("/console")
  ? window.location.origin
  : "http://127.0.0.1:8787";
const API_BASE_KEY = "hive-console-api-base";
const WORKSPACE_KEY = "hive-console-workspace";

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
  const [apiBase, setApiBase] = useState(
    window.localStorage.getItem(API_BASE_KEY) ?? DEFAULT_API_BASE,
  );
  const [workspacePath, setWorkspacePath] = useState(
    window.localStorage.getItem(WORKSPACE_KEY) ?? "",
  );

  useEffect(() => {
    window.localStorage.setItem(API_BASE_KEY, apiBase);
  }, [apiBase]);

  useEffect(() => {
    window.localStorage.setItem(WORKSPACE_KEY, workspacePath);
  }, [workspacePath]);

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
            <p className="eyebrow">Agent Hive 2.2</p>
            <h1>Observe and steer the work, not the folders.</h1>
            <p className="hero-copy">
              One operator view for live runs, approvals, reroutes, and why Hive picked each next
              move.
            </p>
          </div>

          <div className="console-settings">
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
