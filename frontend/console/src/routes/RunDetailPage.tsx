import { type FormEvent, useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { createConsoleClient } from "../api/client";
import { KeyValueGrid } from "../components/KeyValueGrid";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import { useConsoleConfig } from "../components/ConsoleLayout";
import { useConsoleQuery } from "../hooks/useConsoleQuery";

function PreviewBlock({
  title,
  content,
}: {
  title: string;
  content: string | null | undefined;
}) {
  return (
    <article className="list-card">
      <div className="list-card__header">
        <h3>{title}</h3>
      </div>
      <pre className="inline-json">{content?.trim() ? content : "No content recorded yet."}</pre>
    </article>
  );
}

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

export function RunDetailPage() {
  const { runId = "" } = useParams();
  const { apiBase, workspacePath } = useConsoleConfig();
  const client = useMemo(
    () => createConsoleClient(apiBase, workspacePath),
    [apiBase, workspacePath],
  );
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [reason, setReason] = useState("");
  const [note, setNote] = useState("");
  const [rerouteDriver, setRerouteDriver] = useState("claude");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const { data, loading, error } = useConsoleQuery(
    `run:${apiBase}:${workspacePath}:${runId}:${refreshNonce}`,
    () => client.getRunDetail(runId),
    5000,
  );

  const detail = (data?.detail ?? {}) as Record<string, unknown>;
  const run = (detail.run ?? {}) as Record<string, unknown>;
  const promotion = (detail.promotion_decision ?? {}) as Record<string, unknown>;
  const artifactPreview = (detail.artifact_preview ?? {}) as Record<string, unknown>;
  const inspector = (detail.inspector ?? {}) as Record<string, unknown>;
  const contextManifest = (detail.context_manifest ?? {}) as Record<string, unknown>;
  const steeringHistory = Array.isArray(detail.steering_history) ? detail.steering_history : [];
  const timeline = Array.isArray(detail.timeline) ? detail.timeline : [];
  const evaluations = Array.isArray(detail.evaluations) ? detail.evaluations : [];
  const changedFiles = (detail.changed_files ?? {}) as Record<string, unknown>;
  const contextEntries = Array.isArray(detail.context_entries) ? detail.context_entries : [];
  const memoryEntries = Array.isArray(inspector.memory_entries) ? inspector.memory_entries : [];
  const skillEntries = Array.isArray(inspector.skill_entries) ? inspector.skill_entries : [];
  const searchHits = Array.isArray(inspector.search_hits) ? inspector.search_hits : [];
  const outputs = Array.isArray(inspector.outputs) ? inspector.outputs : [];
  const approvals = Array.isArray(detail.approvals) ? detail.approvals : [];
  const pendingApprovals = approvals.filter((item) => {
    return (item as Record<string, unknown>).status === "pending";
  });
  const capabilitySnapshot = (
    detail.capability_snapshot ?? inspector.capability_snapshot ?? {}
  ) as Record<string, unknown>;
  const sandboxPolicy = (
    detail.sandbox_policy ?? inspector.sandbox_policy ?? {}
  ) as Record<string, unknown>;
  const retrievalTrace = (
    detail.retrieval_trace ?? inspector.retrieval_trace ?? {}
  ) as Record<string, unknown>;
  const effective = (capabilitySnapshot.effective ?? {}) as Record<string, unknown>;
  const retrievalContext = Array.isArray(retrievalTrace.selected_context)
    ? retrievalTrace.selected_context
    : [];
  const runStatus = String(run.status ?? "");
  const runHealth = String(run.health ?? "");
  const launchMode = String(effective.launch_mode ?? "");
  const sessionPersistence = String(effective.session_persistence ?? "none");
  const canLiveSteer = launchMode !== "" && launchMode !== "staged" && sessionPersistence !== "none";
  const canPause = canLiveSteer && runHealth !== "paused";
  const canResume = canLiveSteer && runHealth === "paused";
  const canAnnotate = canLiveSteer;
  const canCancel = !["accepted", "cancelled", "failed", "rejected"].includes(runStatus);
  const canReroute = !["accepted", "cancelled", "failed"].includes(runStatus);

  async function handleAction(
    action: string,
    payload?: { note?: string; target?: Record<string, unknown> },
  ) {
    setPendingAction(action);
    setActionError(null);
    setActionMessage(null);
    try {
      await client.steerRun(runId, {
        action,
        reason: reason.trim() || undefined,
        note: payload?.note ?? (note.trim() || undefined),
        target: payload?.target,
        actor: "console-operator",
      });
      setActionMessage(`Sent ${action} for ${runId}.`);
      setReason("");
      setNote("");
      setRefreshNonce((value) => value + 1);
    } catch (caught) {
      setActionError(caught instanceof Error ? caught.message : `Unable to ${action} run.`);
    } finally {
      setPendingAction(null);
    }
  }

  async function handleApproval(approvalId: string, resolution: "approve" | "reject") {
    setPendingAction(`${resolution}:${approvalId}`);
    setActionError(null);
    setActionMessage(null);
    try {
      if (resolution === "approve") {
        await client.approveRunApproval(runId, approvalId, {
          actor: "console-operator",
          note: note.trim() || undefined,
        });
      } else {
        await client.rejectRunApproval(runId, approvalId, {
          actor: "console-operator",
          note: note.trim() || undefined,
        });
      }
      setActionMessage(
        `${resolution === "approve" ? "Approved" : "Rejected"} ${approvalId} for ${runId}.`,
      );
      setNote("");
      setRefreshNonce((value) => value + 1);
    } catch (caught) {
      setActionError(
        caught instanceof Error ? caught.message : `Unable to ${resolution} approval.`,
      );
    } finally {
      setPendingAction(null);
    }
  }

  async function handleReroute(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await handleAction("reroute", {
      target: { driver: rerouteDriver },
    });
  }

  return (
    <div className="page-grid page-grid--detail">
      <Panel eyebrow="Run detail" title={runId}>
        {loading ? <p>Loading Run Detail…</p> : null}
        {error ? <p className="error-copy">{error}</p> : null}
        {!loading && !error ? (
          <div className="stack">
            <div className="list-card__header">
              <h3>
                {String(
                  (run.metadata_json as Record<string, unknown> | undefined)?.task_title ??
                    run.task_id ??
                    "Run",
                )}
              </h3>
              <StatusPill tone={String(run.status ?? "unknown")}>
                {String(run.status ?? "unknown")}
              </StatusPill>
            </div>
            <KeyValueGrid
              values={[
                { label: "Project", value: String(run.project_id ?? "—") },
                { label: "Driver", value: String(run.driver ?? "—") },
                { label: "Health", value: String(run.health ?? "—") },
                { label: "Campaign", value: String(run.campaign_id ?? "—") },
                { label: "Started", value: String(run.started_at ?? "—") },
                { label: "Finished", value: String(run.finished_at ?? "—") },
              ]}
            />
            <article className="hero-card">
              <p className="hero-card__eyebrow">Promotion decision</p>
              <h3>{String(promotion.decision ?? "pending")}</h3>
              <ul className="reason-list">
                {((promotion.reasons as string[] | undefined) ?? []).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </article>
          </div>
        ) : null}
      </Panel>

      <Panel eyebrow="Runtime truth" title="Driver and Sandbox">
        <div className="stack">
          <KeyValueGrid
            values={[
              { label: "Launch mode", value: String(effective.launch_mode ?? "—") },
              {
                label: "Session persistence",
                value: String(effective.session_persistence ?? "—"),
              },
              { label: "Event stream", value: String(effective.event_stream ?? "—") },
              {
                label: "Approvals",
                value: Array.isArray(effective.approvals)
                  ? (effective.approvals as string[]).join(", ") || "none"
                  : "none",
              },
              {
                label: "Artifacts",
                value: Array.isArray(effective.artifacts)
                  ? (effective.artifacts as string[]).join(", ") || "none"
                  : "none",
              },
              { label: "Sandbox backend", value: String(sandboxPolicy.backend ?? "—") },
            ]}
          />
          <PreviewBlock
            title="Capability snapshot"
            content={jsonPreview(capabilitySnapshot)}
          />
          <PreviewBlock title="Sandbox policy" content={jsonPreview(sandboxPolicy)} />
        </div>
      </Panel>

      <Panel eyebrow="Operator controls" title="Steer This Run">
        <div className="stack">
          <label className="console-field">
            <span>Reason</span>
            <input
              placeholder="Why are you steering this run?"
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
          </label>
          <label className="console-field">
            <span>Note</span>
            <input
              placeholder="Optional note to add to the audit trail"
              value={note}
              onChange={(event) => setNote(event.target.value)}
            />
          </label>
          <div className="action-grid">
            {canPause ? (
              <button
                className="primary-button"
                type="button"
                disabled={pendingAction !== null}
                onClick={() => handleAction("pause")}
              >
                Pause
              </button>
            ) : null}
            {canResume ? (
              <button
                className="secondary-button"
                type="button"
                disabled={pendingAction !== null}
                onClick={() => handleAction("resume")}
              >
                Resume
              </button>
            ) : null}
            {canAnnotate ? (
              <button
                className="secondary-button"
                type="button"
                disabled={pendingAction !== null}
                onClick={() => handleAction("note")}
              >
                Add Note
              </button>
            ) : null}
            {canCancel ? (
              <button
                className="danger-button"
                type="button"
                disabled={pendingAction !== null}
                onClick={() => handleAction("cancel")}
              >
                Cancel
              </button>
            ) : null}
          </div>
          {canReroute ? (
            <form className="filters" onSubmit={handleReroute}>
              <label className="console-field">
                <span>Reroute to</span>
                <select
                  value={rerouteDriver}
                  onChange={(event) => setRerouteDriver(event.target.value)}
                >
                  <option value="local">local</option>
                  <option value="manual">manual</option>
                  <option value="codex">codex</option>
                  <option value="claude">claude</option>
                </select>
              </label>
              <div className="filters__actions">
                <button
                  className="primary-button"
                  type="submit"
                  disabled={pendingAction !== null}
                >
                  Reroute
                </button>
              </div>
            </form>
          ) : null}
          {!canLiveSteer ? (
            <p className="list-card__meta">
              Live pause, resume, and note controls stay hidden because this run is currently
              staged or otherwise not attached to a live driver session.
            </p>
          ) : null}
          {actionMessage ? <p>{actionMessage}</p> : null}
          {actionError ? <p className="error-copy">{actionError}</p> : null}
        </div>
      </Panel>

      <Panel eyebrow="Approval broker" title="Pending Approvals">
        <div className="stack">
          {pendingApprovals.length ? (
            pendingApprovals.map((item) => {
              const approval = item as Record<string, unknown>;
              const approvalId = String(approval.approval_id ?? "approval");
              return (
                <article className="list-card" key={approvalId}>
                  <div className="list-card__header">
                    <h3>{String(approval.title ?? approvalId)}</h3>
                    <StatusPill tone={String(approval.kind ?? "approval")}>
                      {String(approval.kind ?? "approval")}
                    </StatusPill>
                  </div>
                  <p>{String(approval.summary ?? "Driver requested approval.")}</p>
                  <pre className="inline-json">{jsonPreview(approval.payload)}</pre>
                  <div className="action-grid">
                    <button
                      className="primary-button"
                      type="button"
                      disabled={pendingAction !== null}
                      onClick={() => handleApproval(approvalId, "approve")}
                    >
                      Approve
                    </button>
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={pendingAction !== null}
                      onClick={() => handleApproval(approvalId, "reject")}
                    >
                      Reject
                    </button>
                  </div>
                </article>
              );
            })
          ) : (
            <p>No pending approvals for this run.</p>
          )}
        </div>
      </Panel>

      <Panel eyebrow="Context inspector" title="What Shaped This Run">
        <div className="stack">
          <KeyValueGrid
            values={[
              { label: "Manifest entries", value: contextEntries.length },
              { label: "Memory docs", value: memoryEntries.length },
              { label: "Skills", value: skillEntries.length },
              { label: "Search hits", value: searchHits.length },
              { label: "Outputs", value: outputs.length },
            ]}
          />
          <article className="list-card">
            <div className="list-card__header">
              <h3>Memory</h3>
            </div>
            <ul className="reason-list">
              {memoryEntries.length ? (
                memoryEntries.map((item) => {
                  const entry = item as Record<string, unknown>;
                  return (
                    <li key={String(entry.id ?? entry.source_path)}>
                      {String(entry.source_path ?? entry.id)}
                    </li>
                  );
                })
              ) : (
                <li>No project memory files were loaded.</li>
              )}
            </ul>
          </article>
          <article className="list-card">
            <div className="list-card__header">
              <h3>Skills</h3>
            </div>
            <ul className="reason-list">
              {skillEntries.length ? (
                skillEntries.map((item) => {
                  const entry = item as Record<string, unknown>;
                  return (
                    <li key={String(entry.id ?? entry.source_path)}>
                      {String(entry.source_path ?? entry.id)}
                    </li>
                  );
                })
              ) : (
                <li>No repo-local skills matched this run.</li>
              )}
            </ul>
          </article>
          <article className="list-card">
            <div className="list-card__header">
              <h3>Search hits</h3>
            </div>
            <ul className="reason-list">
              {searchHits.length ? (
                searchHits.map((item) => {
                  const hit = item as Record<string, unknown>;
                  return (
                    <li key={String(hit.path ?? hit.title)}>
                      {String(hit.title ?? hit.path ?? "search hit")}
                      {Array.isArray(hit.why) && (hit.why as string[]).length
                        ? ` — ${(hit.why as string[]).join("; ")}`
                        : ""}
                    </li>
                  );
                })
              ) : (
                <li>No search hits were bundled for this run.</li>
              )}
            </ul>
          </article>
          <article className="list-card">
            <div className="list-card__header">
              <h3>Compiled outputs</h3>
            </div>
            <ul className="reason-list">
              {outputs.length ? (
                outputs.map((item) => <li key={String(item)}>{String(item)}</li>)
              ) : (
                <li>No compiled outputs recorded.</li>
              )}
            </ul>
          </article>
          <p className="list-card__meta">
            Generated: {String(contextManifest.generated_at ?? "—")}
          </p>
        </div>
      </Panel>

      <Panel eyebrow="Retrieval inspector" title="Why This Context">
        <div className="stack">
          <article className="list-card">
            <div className="list-card__header">
              <h3>Selected context</h3>
            </div>
            <ul className="reason-list">
              {retrievalContext.length ? (
                retrievalContext.map((item) => {
                  const entry = item as Record<string, unknown>;
                  return (
                    <li key={String(entry.chunk_id ?? entry.path ?? entry.title)}>
                      {String(entry.title ?? entry.path ?? entry.chunk_id ?? "context chunk")}
                      {entry.explanation ? ` — ${String(entry.explanation)}` : ""}
                    </li>
                  );
                })
              ) : (
                <li>No retrieval trace has been selected for this run yet.</li>
              )}
            </ul>
          </article>
          <PreviewBlock title="Retrieval trace" content={jsonPreview(retrievalTrace)} />
        </div>
      </Panel>

      <Panel eyebrow="Evaluator evidence" title="Review and Eval">
        <div className="stack">
          {evaluations.length ? (
            evaluations.map((item) => {
              const evaluation = item as Record<string, unknown>;
              return (
                <article
                  className="list-card"
                  key={String(evaluation.evaluator_id ?? evaluation.command)}
                >
                  <div className="list-card__header">
                    <h3>{String(evaluation.evaluator_id ?? "evaluator")}</h3>
                    <StatusPill tone={String(evaluation.status ?? "unknown")}>
                      {String(evaluation.status ?? "unknown")}
                    </StatusPill>
                  </div>
                  <p>{String(evaluation.command ?? "No command recorded.")}</p>
                </article>
              );
            })
          ) : (
            <p>No evaluator results recorded yet.</p>
          )}
          <PreviewBlock title="Run brief" content={String(artifactPreview.run_brief ?? "")} />
          <PreviewBlock title="Summary" content={String(artifactPreview.review_summary ?? "")} />
          <PreviewBlock title="Review" content={String(artifactPreview.review_notes ?? "")} />
        </div>
      </Panel>

      <Panel eyebrow="Workspace diff" title="Diff and Changed Files">
        <div className="stack">
          <article className="list-card">
            <div className="list-card__header">
              <h3>Changed files</h3>
            </div>
            <pre className="inline-json">{JSON.stringify(changedFiles, null, 2)}</pre>
          </article>
          <PreviewBlock title="Patch diff" content={String(artifactPreview.diff ?? "")} />
        </div>
      </Panel>

      <Panel eyebrow="Driver logs" title="Logs">
        <div className="stack">
          <PreviewBlock title="stdout" content={String(artifactPreview.stdout ?? "")} />
          <PreviewBlock title="stderr" content={String(artifactPreview.stderr ?? "")} />
        </div>
      </Panel>

      <Panel eyebrow="Typed interventions" title="Steering History">
        <div className="stack">
          {steeringHistory.length ? (
            steeringHistory.map((item) => {
              const event = item as Record<string, unknown>;
              return (
                <article className="timeline__item" key={String(event.event_id ?? event.ts)}>
                  <div className="timeline__meta">
                    <span>{String(event.type ?? "steering event")}</span>
                    <span>{String(event.ts ?? "—")}</span>
                  </div>
                  <pre className="inline-json">{JSON.stringify(event.payload ?? {}, null, 2)}</pre>
                </article>
              );
            })
          ) : (
            <p>No steering actions recorded for this run.</p>
          )}
        </div>
      </Panel>

      <Panel eyebrow="Audit trail" title="Timeline">
        <div className="timeline">
          {timeline.length ? (
            timeline.map((item) => {
              const event = item as Record<string, unknown>;
              return (
                <article className="timeline__item" key={String(event.event_id ?? event.ts)}>
                  <div className="timeline__meta">
                    <span>{String(event.type ?? "event")}</span>
                    <span>{String(event.ts ?? "—")}</span>
                  </div>
                  <pre className="inline-json">{JSON.stringify(event.payload ?? {}, null, 2)}</pre>
                </article>
              );
            })
          ) : (
            <p>No timeline events yet.</p>
          )}
        </div>
      </Panel>
    </div>
  );
}
