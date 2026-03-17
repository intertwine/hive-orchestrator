import { Route, Routes } from "react-router-dom";

import { ConsoleLayout } from "./components/ConsoleLayout";
import { CampaignsPage } from "./routes/CampaignsPage";
import { HomePage } from "./routes/HomePage";
import { InboxPage } from "./routes/InboxPage";
import { ProjectsPage } from "./routes/ProjectsPage";
import { RunDetailPage } from "./routes/RunDetailPage";
import { RunsPage } from "./routes/RunsPage";
import { SearchPage } from "./routes/SearchPage";

export default function App() {
  return (
    <ConsoleLayout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/inbox" element={<InboxPage />} />
        <Route path="/runs" element={<RunsPage />} />
        <Route path="/runs/:runId" element={<RunDetailPage />} />
        <Route path="/campaigns" element={<CampaignsPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/search" element={<SearchPage />} />
      </Routes>
    </ConsoleLayout>
  );
}
