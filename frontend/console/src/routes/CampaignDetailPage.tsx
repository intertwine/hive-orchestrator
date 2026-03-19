import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";

import { createConsoleClient } from "../api/client";
import { KeyValueGrid } from "../components/KeyValueGrid";
import { Panel } from "../components/Panel";
import { RunCard } from "../components/RunCard";
import { StatusPill } from "../components/StatusPill";
import { useConsoleConfig } from "../components/ConsoleLayout";
import { useConsoleQuery } from "../hooks/useConsoleQuery";

function jsonPreview(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  if (Array.isArray(value)) {
    return value.length ? JSON.stringify(value, null, 2) : "";
  }
  if (typeof value === "object") {
    return Object.keys(value as Record<string, unknown>).length
      ? JSON.stringify(value, null, 2)
      : "";
  }
  return String(value);
}

export function CampaignDetailPage() {
  const { campaignId = "" } = useParams();
  const { apiBase, workspacePath } = useConsoleConfig();
  const client = useMemo(
    () => createConsoleClient(apiBase, workspacePath),
    [apiBase, workspacePath],
  );
  const { data, loading, error } = useConsoleQuery(
    `campaign:${apiBase}:${workspacePath}:${campaignId}`,
    () => client.getCampaign(campaignId),
  );

  const payload = (data ?? {}) as Record<string, unknown>;
  const campaign = (payload.campaign ?? {}) as Record<string, unknown>;
  const decisionPreview = (payload.decision_preview ?? {}) as Record<string, unknown>;
  const candidateSetPreview = (payload.candidate_set_preview ?? {}) as Record<string, unknown>;
  const latestDecision = (payload.latest_decision ?? {}) as Record<string, unknown>;
  const latestCandidateSet = (payload.latest_candidate_set ?? {}) as Record<string, unknown>;
  const selectedCandidate = (decisionPreview.selected_candidate ?? {}) as Record<string, unknown>;
  const candidates = Array.isArray(candidateSetPreview.candidates)
    ? candidateSetPreview.candidates
    : [];
  const activeRuns = Array.isArray(payload.active_runs) ? payload.active_runs : [];
  const acceptedRuns = Array.isArray(payload.accepted_runs) ? payload.accepted_runs : [];

  return (
    <div className="page-grid page-grid--detail">
      <Panel eyebrow="Portfolio loops" title={String(campaign.title ?? campaignId)}>
        {loading ? <p>Loading Campaign Detail…</p> : null}
        {error ? <p className="error-copy">{error}</p> : null}
        {!loading && !error ? (
          <div className="stack">
            <div className="list-card__header">
              <h3>{String(campaign.title ?? campaign.id ?? "Campaign")}</h3>
              <StatusPill tone={String(campaign.status ?? "unknown")}>
                {String(campaign.status ?? "unknown")}
              </StatusPill>
            </div>
            <p>{String(campaign.goal ?? "No campaign goal recorded.")}</p>
            <KeyValueGrid
              values={[
                { label: "Type", value: String(campaign.type ?? "delivery") },
                { label: "Driver", value: String(campaign.driver ?? "—") },
                { label: "Sandbox", value: String(campaign.sandbox_profile ?? "default") },
                { label: "Cadence", value: String(campaign.cadence ?? "manual") },
                { label: "Briefs", value: String(campaign.brief_cadence ?? "—") },
                { label: "Max active runs", value: String(campaign.max_active_runs ?? "—") },
              ]}
            />
          </div>
        ) : null}
      </Panel>

      <Panel eyebrow="Why this next?" title="Decision Preview">
        <div className="stack">
          <article className="hero-card">
            <p className="hero-card__eyebrow">Selected candidate</p>
            <h3>{String(selectedCandidate.title ?? decisionPreview.selected_candidate_id ?? "No candidate selected")}</h3>
            <p className="hero-card__subtle">
              Lane: {String(decisionPreview.selected_lane ?? "—")} • Action:{" "}
              {String(decisionPreview.selected_action ?? "idle")}
            </p>
            <p>{String(decisionPreview.reason ?? "No decision reason recorded.")}</p>
          </article>
          <article className="list-card">
            <div className="list-card__header">
              <h3>Lane quotas</h3>
            </div>
            <pre className="inline-json">{jsonPreview(campaign.lane_quotas)}</pre>
          </article>
        </div>
      </Panel>

      <Panel eyebrow="Candidate reasoning" title="Candidate Set">
        <div className="stack">
          {candidates.length ? (
            candidates.map((item) => {
              const candidate = item as Record<string, unknown>;
              const isSelected =
                String(candidate.candidate_id ?? "") ===
                String(decisionPreview.selected_candidate_id ?? "");
              return (
                <article className="list-card" key={String(candidate.candidate_id ?? candidate.title)}>
                  <div className="list-card__header">
                    <h3>{String(candidate.title ?? candidate.candidate_id ?? "Candidate")}</h3>
                    <StatusPill tone={isSelected ? "healthy" : "info"}>
                      {isSelected ? "selected" : "rejected"}
                    </StatusPill>
                  </div>
                  <p className="list-card__meta">
                    Lane: {String(candidate.lane ?? "—")} • Driver:{" "}
                    {String(candidate.recommended_driver ?? "—")} • Sandbox:{" "}
                    {String(candidate.recommended_sandbox ?? "—")}
                  </p>
                  <pre className="inline-json">{jsonPreview(candidate.scores)}</pre>
                </article>
              );
            })
          ) : (
            <p>No candidate set has been previewed yet.</p>
          )}
        </div>
      </Panel>

      <Panel eyebrow="Runs under this campaign" title="Active Runs">
        <div className="card-grid">
          {activeRuns.length ? (
            activeRuns.map((run) => (
              <RunCard key={String((run as Record<string, unknown>).id)} run={run as Record<string, unknown>} />
            ))
          ) : (
            <p>No active campaign runs right now.</p>
          )}
        </div>
      </Panel>

      <Panel eyebrow="Recently accepted" title="Accepted Runs">
        <div className="card-grid">
          {acceptedRuns.length ? (
            acceptedRuns.map((run) => (
              <RunCard key={String((run as Record<string, unknown>).id)} run={run as Record<string, unknown>} />
            ))
          ) : (
            <p>No accepted campaign runs yet.</p>
          )}
        </div>
      </Panel>

      <Panel eyebrow="Machine-readable logs" title="Artifacts">
        <div className="stack">
          <article className="list-card">
            <div className="list-card__header">
              <h3>Preview candidate set</h3>
            </div>
            <pre className="inline-json">{jsonPreview(candidateSetPreview)}</pre>
          </article>
          <article className="list-card">
            <div className="list-card__header">
              <h3>Latest candidate set</h3>
            </div>
            <pre className="inline-json">{jsonPreview(latestCandidateSet)}</pre>
          </article>
          <article className="list-card">
            <div className="list-card__header">
              <h3>Latest decision</h3>
            </div>
            <pre className="inline-json">{jsonPreview(latestDecision)}</pre>
          </article>
          <p className="list-card__meta">
            <Link to="/campaigns">Back to campaigns</Link>
          </p>
        </div>
      </Panel>
    </div>
  );
}
