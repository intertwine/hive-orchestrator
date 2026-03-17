import { Link } from "react-router-dom";

import { StatusPill } from "./StatusPill";

export function RunCard({ run }: { run: Record<string, unknown> }) {
  const metadata = (run.metadata_json ?? {}) as Record<string, unknown>;

  return (
    <article className="run-card">
      <div className="run-card__meta">
        <StatusPill tone={String(run.health ?? "healthy")}>{String(run.status ?? "unknown")}</StatusPill>
        <span>{String(run.driver ?? "local")}</span>
      </div>
      <h3>
        <Link to={`/runs/${String(run.id)}`}>{String(run.id)}</Link>
      </h3>
      <p className="run-card__title">{String(metadata.task_title ?? run.task_id ?? "Untitled run")}</p>
      <dl className="run-card__facts">
        <div>
          <dt>Project</dt>
          <dd>{String(run.project_id ?? "—")}</dd>
        </div>
        <div>
          <dt>Started</dt>
          <dd>{String(run.started_at ?? "—")}</dd>
        </div>
        <div>
          <dt>Health</dt>
          <dd>{String(run.health ?? "healthy")}</dd>
        </div>
      </dl>
    </article>
  );
}
