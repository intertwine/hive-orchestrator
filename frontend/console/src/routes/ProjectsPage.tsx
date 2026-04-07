import { useParams } from "react-router-dom";

import { createConsoleClient } from "../api/client";
import { ConsoleLink } from "../components/ConsoleLink";
import { Panel } from "../components/Panel";
import { StatusPill } from "../components/StatusPill";
import { useConsoleConfig } from "../components/ConsoleLayout";
import { useConsoleQuery } from "../hooks/useConsoleQuery";

function doctorIssues(payload: unknown): Array<Record<string, unknown>> {
  const doctor = (payload as { doctor?: Record<string, unknown> } | undefined)?.doctor;
  const issues = doctor?.issues;
  return Array.isArray(issues) ? (issues as Array<Record<string, unknown>>) : [];
}

function doctorStatus(payload: unknown): string {
  const doctor = (payload as { doctor?: Record<string, unknown> } | undefined)?.doctor;
  return String(doctor?.status ?? "unknown");
}

function doctorBlocksAutonomousPromotion(payload: unknown): boolean {
  const doctor = (payload as { doctor?: Record<string, unknown> } | undefined)?.doctor;
  return Boolean(doctor?.blocked_autonomous_promotion);
}

function doctorGuidance(payload: unknown) {
  const status = doctorStatus(payload);
  const issues = doctorIssues(payload);
  const codes = new Set(issues.map((issue) => String(issue.code ?? "")));

  if (!issues.length && status === "healthy") {
    return {
      title: "Project looks ready",
      summary: "Program Doctor is healthy. Safe next move: inspect the compiled startup context, then launch or monitor work from Home and Runs.",
      steps: [
        "Read the context preview to confirm task, policy, and docs are aligned.",
        "Return to Home to follow the recommended next task.",
        "Use Runs or Inbox only when there is real work or operator input waiting.",
      ],
    };
  }

  if (codes.has("missing_required_evaluator") || doctorBlocksAutonomousPromotion(payload)) {
    return {
      title: "Program Doctor is blocking promotion",
      summary: "The project may be observable, but Hive is correctly warning that autonomous promotion is not yet safe.",
      steps: [
        "Add the missing evaluator or policy requirement in PROGRAM.md.",
        "Re-run Program Doctor after the policy change.",
        "Stay in read-mostly surfaces until the project health turns green.",
      ],
    };
  }

  return {
    title: status === "fail" ? "Doctor found blocking issues to resolve" : "Doctor found issues to resolve",
    summary: "Treat these findings as policy or setup work, not as a reason to force the run engine forward.",
    steps: [
      "Read each issue code and message carefully.",
      "Fix project policy or setup first, then refresh Doctor.",
      "Use the context preview to confirm the project story still matches the code.",
    ],
  };
}

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
  const guidance = doctor.loading ? null : doctorGuidance(doctor.data);

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
              Status: <strong>{doctorStatus(doctor.data)}</strong>
            </p>
            <ul className="reason-list">
              {doctorIssues(doctor.data).map((issue) => (
                <li key={String(issue.code ?? issue.message)}>
                  {String(issue.code ?? "issue")}: {String(issue.message ?? "Needs attention")}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </Panel>

      <Panel eyebrow="Safe next move" title="Doctor Guidance">
        {doctor.loading ? <p>Waiting for Doctor guidance…</p> : null}
        {doctor.error ? <p className="error-copy">{doctor.error}</p> : null}
        {!doctor.loading && !doctor.error && guidance ? (
          <div className="stack">
            <div className="hero-card">
              <p className="hero-card__eyebrow">Plain-language summary</p>
              <h3>{guidance.title}</h3>
              <p className="hero-card__subtle">{guidance.summary}</p>
              <ul className="reason-list">
                {guidance.steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ul>
            </div>
          </div>
        ) : null}
      </Panel>

      <Panel eyebrow="Compiled startup context" title="Context Preview">
        {context.loading ? <p>Loading Context…</p> : null}
        {context.error ? <p className="error-copy">{context.error}</p> : null}
        {!context.loading && !context.error ? (
          <div className="stack">
            <p className="console-settings__note">
              This is the exact startup context Hive would compile before a governed run. Read it
              before you blame the driver.
            </p>
            <pre className="inline-json">{String(context.data?.rendered ?? "")}</pre>
          </div>
        ) : null}
      </Panel>
    </div>
  );
}
