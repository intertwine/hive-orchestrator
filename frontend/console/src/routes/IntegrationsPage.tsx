import { useMemo } from "react";
import { useParams } from "react-router-dom";

import { createConsoleClient } from "../api/client";
import { ConsoleLink } from "../components/ConsoleLink";
import { Panel } from "../components/Panel";
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

export function IntegrationsPage() {
  const { integrationName = "" } = useParams();
  const { apiBase, workspacePath } = useConsoleConfig();
  const client = useMemo(
    () => createConsoleClient(apiBase, workspacePath),
    [apiBase, workspacePath],
  );
  const integrations = useConsoleQuery(
    `integrations:${apiBase}:${workspacePath}`,
    () => client.getIntegrations(),
    15000,
  );
  const backends = Array.isArray(integrations.data?.backends) ? integrations.data.backends : [];
  const activeIntegration =
    integrationName || String((backends[0] as Record<string, unknown> | undefined)?.adapter ?? "");
  const detail = useConsoleQuery(
    `integration-detail:${apiBase}:${workspacePath}:${activeIntegration}`,
    () =>
      activeIntegration
        ? client.getIntegration(activeIntegration)
        : Promise.resolve({ ok: true, integration: {} }),
    15000,
  );
  const integrationDetail = (detail.data?.integration ?? {}) as Record<string, unknown>;

  return (
    <div className="page-grid">
      <Panel eyebrow="Harness truth" title="Integrations">
        {integrations.loading ? <p>Loading Integrations…</p> : null}
        {integrations.error ? <p className="error-copy">{integrations.error}</p> : null}
        <div className="stack">
          {backends.length ? (
            backends.map((item) => {
              const backend = item as Record<string, unknown>;
              const adapter = String(backend.adapter ?? backend.name ?? "");
              const available = Boolean(backend.available ?? true);
              return (
                <ConsoleLink
                  className={`list-card list-card--button${activeIntegration === adapter ? " list-card--selected" : ""}`}
                  key={adapter}
                  to={`/integrations/${adapter}`}
                >
                  <div className="list-card__header">
                    <h3>{adapter || "integration"}</h3>
                    <StatusPill tone={available ? "healthy" : "failed"}>
                      {available ? "available" : "unavailable"}
                    </StatusPill>
                  </div>
                  <p className="list-card__meta">
                    Family: {String(backend.adapter_type ?? backend.adapter_family ?? "unknown")}
                  </p>
                  <p className="list-card__meta">
                    Level: {String(backend.integration_level ?? "—")} • Governance:{" "}
                    {String(backend.governance_mode ?? "—")}
                  </p>
                </ConsoleLink>
              );
            })
          ) : (
            <p>No integrations were reported by the console API.</p>
          )}
        </div>
      </Panel>

      <Panel eyebrow="Capability probe" title={activeIntegration || "Integration Detail"}>
        {detail.loading && activeIntegration ? <p>Loading Integration Detail…</p> : null}
        {detail.error ? <p className="error-copy">{detail.error}</p> : null}
        {!activeIntegration ? <p>Select an integration to inspect its capability truth.</p> : null}
        {activeIntegration ? (
          <div className="stack">
            <article className="hero-card">
              <p className="hero-card__eyebrow">Selected backend</p>
              <h3>{String(integrationDetail.adapter ?? activeIntegration)}</h3>
              <p className="hero-card__subtle">
                Family: {String(integrationDetail.adapter_family ?? "—")} • Level:{" "}
                {String(integrationDetail.integration_level ?? "—")}
              </p>
              <p>
                Governance: {String(integrationDetail.governance_mode ?? "—")} • Version:{" "}
                {String(integrationDetail.version ?? "—")}
              </p>
            </article>
            <article className="list-card">
              <div className="list-card__header">
                <h3>Notes and next steps</h3>
              </div>
              <ul className="reason-list">
                {[
                  ...((integrationDetail.notes as string[] | undefined) ?? []),
                  ...((integrationDetail.next_steps as string[] | undefined) ?? []),
                ].map((entry) => (
                  <li key={entry}>{entry}</li>
                ))}
              </ul>
            </article>
            <article className="list-card">
              <div className="list-card__header">
                <h3>Raw probe</h3>
              </div>
              <pre className="inline-json">{jsonPreview(integrationDetail)}</pre>
            </article>
          </div>
        ) : null}
      </Panel>
    </div>
  );
}
