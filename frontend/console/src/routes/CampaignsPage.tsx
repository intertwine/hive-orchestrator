import { Link } from "react-router-dom";

import { createConsoleClient } from "../api/client";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import { useConsoleConfig } from "../components/ConsoleLayout";
import { useConsoleQuery } from "../hooks/useConsoleQuery";

export function CampaignsPage() {
  const { apiBase, workspacePath } = useConsoleConfig();
  const client = createConsoleClient(apiBase, workspacePath);
  const { data, loading, error } = useConsoleQuery(
    `campaigns:${apiBase}:${workspacePath}`,
    () => client.getCampaigns(),
  );
  const campaigns = Array.isArray(data?.campaigns) ? data.campaigns : [];

  return (
    <Panel eyebrow="Portfolio loops" title="Campaigns">
      {loading ? <p>Loading Campaigns…</p> : null}
      {error ? <p className="error-copy">{error}</p> : null}
      <div className="stack">
        {campaigns.length ? (
          campaigns.map((item) => {
            const campaign = item as Record<string, unknown>;
            return (
              <article className="list-card" key={String(campaign.id)}>
                <div className="list-card__header">
                  <h3>
                    <Link to={`/campaigns/${String(campaign.id)}`}>
                      {String(campaign.title ?? campaign.id ?? "Campaign")}
                    </Link>
                  </h3>
                  <StatusPill tone={String(campaign.status ?? "healthy")}>
                    {String(campaign.status ?? "unknown")}
                  </StatusPill>
                </div>
                <p>{String(campaign.goal ?? "No campaign goal recorded.")}</p>
                <p className="list-card__meta">
                  Driver: {String(campaign.driver ?? "—")} • Cadence:{" "}
                  {String(campaign.cadence ?? "manual")} • Briefs:{" "}
                  {String(campaign.brief_cadence ?? "—")}
                </p>
                <p className="list-card__meta">
                  Lane quotas: {JSON.stringify(campaign.lane_quotas ?? {})}
                </p>
              </article>
            );
          })
        ) : (
          <p>No campaigns exist yet.</p>
        )}
      </div>
    </Panel>
  );
}
