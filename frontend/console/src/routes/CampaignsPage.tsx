import { createConsoleClient } from "../api/client";
import { ConsoleLink } from "../components/ConsoleLink";
import { Panel } from "../components/Panel";
import { StateNotice } from "../components/StateNotice";
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
      {loading ? (
        <StateNotice
          detail="Hive is loading campaign loops, cadence, and lane quotas for the current workspace."
          title="Loading Campaigns"
        />
      ) : error ? (
        <StateNotice
          detail={`Verify the API base and workspace path in Settings, then retry once the daemon is reachable again. (${error})`}
          title="Unable to load Campaigns"
          tone="error"
        />
      ) : (
        <div className="stack">
          {campaigns.length ? (
            campaigns.map((item) => {
              const campaign = item as Record<string, unknown>;
              return (
                <article className="list-card" key={String(campaign.id)}>
                  <div className="list-card__header">
                    <h3>
                      <ConsoleLink to={`/campaigns/${String(campaign.id)}`}>
                        {String(campaign.title ?? campaign.id ?? "Campaign")}
                      </ConsoleLink>
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
            <StateNotice
              detail="Create or import a campaign once you want Hive to keep a portfolio loop moving for you."
              title="No campaigns exist yet"
            />
          )}
        </div>
      )}
    </Panel>
  );
}
