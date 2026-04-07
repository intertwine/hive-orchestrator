import { useLocation } from "react-router-dom";

import { KeyValueGrid } from "../components/KeyValueGrid";
import { ConsoleSettingsCard, useConsoleConfig } from "../components/ConsoleLayout";
import { useConsolePreferences } from "../components/ConsolePreferences";
import { Panel } from "../components/Panel";

export function SettingsPage() {
  const { apiBase, workspacePath } = useConsoleConfig();
  const { preferences } = useConsolePreferences();
  const location = useLocation();

  return (
    <div className="page-grid">
      <Panel eyebrow="Operator-local state" title="Settings">
        <ConsoleSettingsCard
          eyebrow="Connection and display"
          note="These settings stay local to the current operator. They shape the shell, density, and connection context without mutating canonical Hive workspace state."
        />
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
          <pre className="inline-json">{JSON.stringify(preferences, null, 2)}</pre>
        </div>
      </Panel>
    </div>
  );
}
