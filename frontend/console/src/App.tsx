import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { ConsoleLayout } from "./components/ConsoleLayout";
import { consolePathForPage } from "./consolePages";
import { useConsolePreferences } from "./components/ConsolePreferences";
import { ActivityPage } from "./routes/ActivityPage";
import { CampaignDetailPage } from "./routes/CampaignDetailPage";
import { CampaignsPage } from "./routes/CampaignsPage";
import { HomePage } from "./routes/HomePage";
import { InboxPage } from "./routes/InboxPage";
import { IntegrationsPage } from "./routes/IntegrationsPage";
import { NotificationsPage } from "./routes/NotificationsPage";
import { ProjectsPage } from "./routes/ProjectsPage";
import { RunDetailPage } from "./routes/RunDetailPage";
import { RunsPage } from "./routes/RunsPage";
import { SearchPage } from "./routes/SearchPage";
import { SettingsPage } from "./routes/SettingsPage";

function ConsoleLandingRoute() {
  const { preferences } = useConsolePreferences();
  const location = useLocation();

  return (
    <Navigate
      replace
      to={{
        pathname: consolePathForPage(preferences.defaultPage),
        search: location.search,
      }}
    />
  );
}

function ConsoleFallbackRoute() {
  const location = useLocation();
  return (
    <Navigate
      replace
      to={{ pathname: consolePathForPage("home"), search: location.search }}
    />
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<ConsoleLayout />}>
        <Route index element={<ConsoleLandingRoute />} />
        <Route path="home" element={<HomePage />} />
        <Route path="inbox" element={<InboxPage />} />
        <Route path="runs" element={<RunsPage />} />
        <Route path="runs/:runId" element={<RunDetailPage />} />
        <Route path="campaigns" element={<CampaignsPage />} />
        <Route path="campaigns/:campaignId" element={<CampaignDetailPage />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="projects/:projectRef" element={<ProjectsPage />} />
        <Route path="search" element={<SearchPage />} />
        <Route path="integrations" element={<IntegrationsPage />} />
        <Route path="integrations/:integrationName" element={<IntegrationsPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="activity" element={<ActivityPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<ConsoleFallbackRoute />} />
      </Route>
    </Routes>
  );
}
