import { useLocation } from "react-router-dom";

import { ConsoleLink } from "../components/ConsoleLink";
import { KeyValueGrid } from "../components/KeyValueGrid";
import { ConsoleSettingsCard, useConsoleConfig } from "../components/ConsoleLayout";
import { useConsolePreferences } from "../components/ConsolePreferences";
import { Panel } from "../components/Panel";

const SHORTCUT_GUIDE = [
  {
    keys: "Ctrl/Cmd+K",
    action: "Open the command palette",
    note: "Search pages, actions, and run controls from anywhere in the shell.",
  },
  {
    keys: "?",
    action: "Open Settings and shortcut help quickly",
    note: "Works from anywhere outside a text field, so help stays one keypress away.",
  },
  {
    keys: "Enter",
    action: "Run the first command-palette match",
    note: "Useful when the right action is already at the top of the results list.",
  },
  {
    keys: "Escape",
    action: "Close the command palette",
    note: "Back out of palette search without touching the mouse.",
  },
] as const;

export function SettingsPage() {
  const { apiBase, setWorkspacePath, workspacePath } = useConsoleConfig();
  const {
    clearAttentionDisposition,
    preferences,
    rememberWorkspace,
    setShowActionableNotifications,
    setShowInformationalNotifications,
    setShowShortcutBadges,
  } = useConsolePreferences();
  const location = useLocation();
  const recentWorkspaces = preferences.recentWorkspaces;
  const triageEntries = Object.values(preferences.attention.triageByItemId);
  const dismissedCount = triageEntries.filter((entry) => entry.disposition === "dismissed").length;
  const resolvedCount = triageEntries.filter((entry) => entry.disposition === "resolved").length;
  const snoozedCount = triageEntries.filter((entry) => entry.snoozedUntil).length;

  return (
    <div className="page-grid">
      <Panel eyebrow="Operator-local state" title="Settings">
        <ConsoleSettingsCard
          eyebrow="Connection and display"
          note="These settings stay local to the current operator. They shape the shell, density, and connection context without mutating canonical Hive workspace state."
        />
      </Panel>

      <Panel eyebrow="Notifications" title="Notification preferences">
        <div className="stack">
          <KeyValueGrid
            values={[
              {
                label: "Actionable visible",
                value: preferences.notifications.showActionable ? "Yes" : "No",
              },
              {
                label: "Informational visible",
                value: preferences.notifications.showInformational ? "Yes" : "No",
              },
              { label: "Dismissed locally", value: dismissedCount },
              { label: "Resolved locally", value: resolvedCount },
            ]}
          />
          <article className="list-card">
            <div className="list-card__header">
              <div>
                <h3>Actionable notifications</h3>
                <p className="list-card__meta">Approvals, escalations, and inbox-worthy work.</p>
              </div>
              <input
                aria-label="Show actionable notifications"
                checked={preferences.notifications.showActionable}
                onChange={(event) => setShowActionableNotifications(event.target.checked)}
                type="checkbox"
              />
            </div>
            <p>
              Keep high-signal operator decisions visible in Notifications when you want a compact
              mirror of the inbox, or hide them when you are already living inside Inbox.
            </p>
          </article>
          <article className="list-card">
            <div className="list-card__header">
              <div>
                <h3>Informational notifications</h3>
                <p className="list-card__meta">Accepted runs and lower-stakes portfolio movement.</p>
              </div>
              <input
                aria-label="Show informational notifications"
                checked={preferences.notifications.showInformational}
                onChange={(event) => setShowInformationalNotifications(event.target.checked)}
                type="checkbox"
              />
            </div>
            <p>
              Informational signals stay useful when you want portfolio movement in view without
              mixing it into decision-heavy surfaces.
            </p>
          </article>
          <article className="list-card">
            <div className="list-card__header">
              <h3>Local queue cleanup</h3>
              <span className="status-pill status-pill--good">Snoozed: {snoozedCount}</span>
            </div>
            <p className="list-card__meta">
              Clear local triage state without mutating canonical Hive task or run truth.
            </p>
            <div className="stack stack--compact">
              <button
                className="secondary-button"
                onClick={() => clearAttentionDisposition("dismissed")}
                type="button"
              >
                Clear dismissed
              </button>
              <button
                className="secondary-button"
                onClick={() => clearAttentionDisposition("resolved")}
                type="button"
              >
                Clear resolved
              </button>
            </div>
          </article>
        </div>
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
                  onClick={() => {
                    setWorkspacePath(candidate);
                    rememberWorkspace(candidate);
                  }}
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
              {workspacePath
                ? "Switch to another workspace once and it will appear here for one-click return."
                : "Open at least one workspace and it will appear here for one-click switching."}
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

      <Panel eyebrow="Saved state" title="Saved views and shortcut help">
        <div className="stack">
          <KeyValueGrid
            values={[
              { label: "Saved run views", value: preferences.runs.savedViews.length },
              { label: "Saved inbox views", value: preferences.attention.savedViews.length },
              {
                label: "Shortcut badges",
                value: preferences.keyboard.showShortcutBadges ? "Visible" : "Hidden",
              },
              { label: "Default landing page", value: preferences.defaultPage },
            ]}
          />
          <article className="list-card">
            <div className="list-card__header">
              <div>
                <h3>Shortcut hints in the shell</h3>
                <p className="list-card__meta">
                  Keep in-product keyboard guidance visible without relying on docs.
                </p>
              </div>
              <input
                aria-label="Show keyboard shortcut badges"
                checked={preferences.keyboard.showShortcutBadges}
                onChange={(event) => setShowShortcutBadges(event.target.checked)}
                type="checkbox"
              />
            </div>
            <p>
              Turning shortcut badges off keeps the shell quieter. The full cheat sheet stays here
              in Settings either way.
            </p>
          </article>
          <article className="list-card">
            <div className="list-card__header">
              <div>
                <h3>Keyboard shortcut help</h3>
                <p className="list-card__meta">
                  The command center should teach its own shortcut vocabulary.
                </p>
              </div>
              <span className="status-pill status-pill--good">In product</span>
            </div>
            <ul className="reason-list">
              {SHORTCUT_GUIDE.map((shortcut) => (
                <li key={shortcut.keys}>
                  <strong>{shortcut.keys}</strong>: {shortcut.action}. {shortcut.note}
                </li>
              ))}
            </ul>
          </article>
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
