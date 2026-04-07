import { useParams } from "react-router-dom";

import { createConsoleClient } from "../api/client";
import { ConsoleLink } from "../components/ConsoleLink";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import { useConsoleConfig } from "../components/ConsoleLayout";
import { useConsoleQuery } from "../hooks/useConsoleQuery";

export function ProjectsPage() {
  const { apiBase, workspacePath } = useConsoleConfig();
  const client = createConsoleClient(apiBase, workspacePath);
  const { projectRef = "" } = useParams();
  const { data, loading, error } = useConsoleQuery(
    `projects:${apiBase}:${workspacePath}`,
    () => client.getProjects(),
  );
  const projects = Array.isArray(data?.projects) ? data.projects : [];
  const activeProject = projectRef || String((projects[0] as Record<string, unknown> | undefined)?.id ?? "");
  const doctor = useConsoleQuery(
    `doctor:${apiBase}:${workspacePath}:${activeProject}`,
    () =>
      activeProject
        ? client.getProjectDoctor(activeProject)
        : Promise.resolve({ ok: true, doctor: {} }),
    15000,
  );
  const context = useConsoleQuery(
    `context:${apiBase}:${workspacePath}:${activeProject}`,
    () =>
      activeProject
        ? client.getProjectContext(activeProject)
        : Promise.resolve({ ok: true, project: {}, rendered: "", context: {} }),
    15000,
  );

  return (
    <div className="page-grid">
      <Panel eyebrow="Project summaries" title="Projects">
        {loading ? <p>Loading Projects…</p> : null}
        {error ? <p className="error-copy">{error}</p> : null}
        <div className="stack">
          {projects.map((item) => {
            const project = item as Record<string, unknown>;
            const projectId = String(project.id ?? "");
            return (
              <ConsoleLink
                className={`list-card list-card--button${activeProject === projectId ? " list-card--selected" : ""}`}
                key={projectId}
                to={`/projects/${projectId}`}
              >
                <div className="list-card__header">
                  <h3>{String(project.title ?? projectId)}</h3>
                  <StatusPill tone={String(project.status ?? "healthy")}>
                    {String(project.status ?? "unknown")}
                  </StatusPill>
                </div>
                <p className="list-card__meta">
                  {projectId} • Priority {String(project.priority ?? "—")} • Owner{" "}
                  {String(project.owner ?? "—")}
                </p>
              </ConsoleLink>
            );
          })}
        </div>
      </Panel>

      <Panel eyebrow="Policy health" title="Program Doctor">
        {doctor.loading ? <p>Loading Doctor…</p> : null}
        {doctor.error ? <p className="error-copy">{doctor.error}</p> : null}
        {!doctor.loading && !doctor.error ? (
          <div className="stack">
            <p>
              Status:{" "}
              <strong>{String((doctor.data?.doctor as Record<string, unknown> | undefined)?.status ?? "—")}</strong>
            </p>
            <ul className="reason-list">
              {(
                ((doctor.data?.doctor as Record<string, unknown> | undefined)?.issues as
                  | Array<Record<string, unknown>>
                  | undefined) ?? []
              ).map((issue) => (
                <li key={String(issue.code ?? issue.message)}>
                  {String(issue.code ?? "issue")}: {String(issue.message ?? "Needs attention")}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </Panel>

      <Panel eyebrow="Compiled startup context" title="Context Preview">
        {context.loading ? <p>Loading Context…</p> : null}
        {context.error ? <p className="error-copy">{context.error}</p> : null}
        {!context.loading && !context.error ? (
          <pre className="inline-json">{String(context.data?.rendered ?? "")}</pre>
        ) : null}
      </Panel>
    </div>
  );
}
