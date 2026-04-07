import { useLocation } from "react-router-dom";

import { ConsoleLink } from "../components/ConsoleLink";
import { KeyValueGrid } from "../components/KeyValueGrid";
import { ConsoleSettingsCard, useConsoleConfig } from "../components/ConsoleLayout";
import { useConsolePreferences } from "../components/ConsolePreferences";
import { Panel } from "../components/Panel";

export function SettingsPage() {
  const { apiBase, setWorkspacePath, workspacePath } = useConsoleConfig();
  const { preferences } = useConsolePreferences();
  const location = useLocation();
  const recentWorkspaces = preferences.recentWorkspaces;

  return (
    <div className="page-grid">
      <Panel eyebrow="Operator-local state" title="Settings">
        <ConsoleSettingsCard
          eyebrow="Connection and display"
          note="These settings stay local to the current operator. They shape the shell, density, and connection context without mutating canonical Hive workspace state."
        />
      </Panel>

      <Panel eyebrow="Workspace chooser" title="Recent Workspaces">
        <div className="stack">
          <KeyValueGrid
            values={[
              { label: "Current workspace", value: workspacePath || "Not selected yet" },
              { label: "Saved choices", value: recentWorkspaces.length },
              { label: "API base", value: apiBase },
              { label: "Default page", value: preferences.defaultPage },
            ]}
          />
          {recentWorkspaces.length ? (
            <div className="stack stack--compact">
              {recentWorkspaces.map((candidate) => (
                <button
                  aria-current={candidate === workspacePath ? "true" : undefined}
                  className={`list-card list-card--button${candidate === workspacePath ? " list-card--selected" : ""}`}
                  key={candidate}
                  onClick={() => setWorkspacePath(candidate)}
                  type="button"
                >
                  <div className="list-card__header">
                    <h3>{candidate}</h3>
                    <span className="status-pill status-pill--good">
                      {candidate === workspacePath ? "current" : "recent"}
                    </span>
                  </div>
                  <p className="list-card__meta">
                    Use this workspace path without touching canonical Hive state.
                  </p>
                </button>
              ))}
            </div>
          ) : (
            <p className="console-settings__note">
              Open at least one workspace and it will appear here for one-click switching.
            </p>
          )}
          <div className="hero-card">
            <p className="hero-card__eyebrow">Demo path</p>
            <h3>Need a safe first success?</h3>
            <p className="hero-card__subtle">
              A fresh demo workspace is still the shortest productized path from install to first
              action.
            </p>
            <pre className="inline-json">{`mkdir my-hive
cd my-hive
git init
hive onboard demo --title "Demo project"
hive console serve`}</pre>
          </div>
        </div>
      </Panel>

      <Panel eyebrow="Deep-link truth" title="Route Contract">
        <div className="stack">
          <KeyValueGrid
            values={[
              { label: "Path", value: location.pathname },
              { label: "Search", value: location.search || "—" },
              { label: "API base", value: apiBase },
              { label: "Workspace", value: workspacePath || "—" },
              { label: "Default page", value: preferences.defaultPage },
            ]}
          />
          <div className="hero-card">
            <p className="hero-card__eyebrow">Safe clicks</p>
            <h3>What to open first</h3>
            <ul className="reason-list">
              <li>
                <ConsoleLink to="/projects" className="getting-started__link">Open Projects</ConsoleLink>
                {" "}
                explains Program Doctor output and startup context.
              </li>
              <li>
                <ConsoleLink to="/inbox" className="getting-started__link">Open Inbox</ConsoleLink>
                {" "}
                is the right place to inspect approvals and exceptions.
              </li>
              <li>
                <ConsoleLink to="/runs" className="getting-started__link">Open Runs</ConsoleLink>
                {" "}
                becomes the live observe-and-steer view once work exists.
              </li>
              <li>
                <ConsoleLink to="/integrations" className="getting-started__link">Check Integrations</ConsoleLink>
                {" "}
                tells you whether Pi, OpenClaw, or Hermes are actually ready.
              </li>
            </ul>
          </div>
          <pre className="inline-json">{JSON.stringify(preferences, null, 2)}</pre>
        </div>
      </Panel>
    </div>
  );
}
