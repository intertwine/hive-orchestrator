import { createConsoleClient } from "../api/client";
import { ConsoleLink } from "../components/ConsoleLink";
import { useConsoleConfig } from "../components/ConsoleLayout";
import { KeyValueGrid } from "../components/KeyValueGrid";
import { Panel } from "../components/Panel";
import { RunCard } from "../components/RunCard";
import { StatusPill } from "../components/StatusPill";
import { useConsoleQuery } from "../hooks/useConsoleQuery";

function RecommendedTaskCard({
  recommended,
}: {
  recommended: { task?: Record<string, unknown>; reasons?: string[] } | null;
}) {
  return (
    <div className="hero-card">
      <p className="hero-card__eyebrow">Recommended next move</p>
      {recommended?.task ? (
        <>
          <h3>{String(recommended.task.title ?? recommended.task.id ?? "Next task")}</h3>
          <p className="hero-card__subtle">
            {String(recommended.task.project_id ?? "unknown project")}
          </p>
          <ul className="reason-list">
            {(recommended.reasons ?? []).map((reason, index) => (
              <li key={`reason-${index}`}>{reason}</li>
            ))}
          </ul>
        </>
      ) : (
        <>
          <h3>No recommendation yet</h3>
          <p className="hero-card__subtle">
            Start in Projects to read Program Doctor, then return here once Hive has enough
            context to rank the next safe action.
          </p>
        </>
      )}
    </div>
  );
}

function SafeFirstChecklist({ workspacePath }: { workspacePath: string }) {
  return (
    <div className="hero-card">
      <p className="hero-card__eyebrow">Safe first actions</p>
      <h3>Inspect first. Mutate later.</h3>
      <ul className="reason-list">
        <li>
          <strong>Settings</strong>:{" "}
          {workspacePath.trim()
            ? `currently pointed at ${workspacePath.trim()}`
            : "pick an API base and workspace path before expecting the console to tell the truth"}
        </li>
        <li>
          <strong>Projects</strong>: read Program Doctor and startup context before you launch
          autonomous work.
        </li>
        <li>
          <strong>Inbox</strong>: inspect approvals, escalations, and blocked sessions without
          mutating the workspace.
        </li>
        <li>
          <strong>Runs</strong>: watch live work, freshness, and steering history once work exists.
        </li>
      </ul>
    </div>
  );
}

function ChooseYourPathCard() {
  return (
    <div className="hero-card">
      <p className="hero-card__eyebrow">First-contact success</p>
      <h3>Choose the shortest honest path</h3>
      <ul className="reason-list">
        <li>
          <strong>Fresh workspace</strong>: `hive onboard demo --title "Demo project"` creates a
          safe first project and task chain.
        </li>
        <li>
          <strong>Existing repo</strong>: `hive adopt app --title "App"` brings Hive into code you
          already own.
        </li>
        <li>
          <strong>Native harnesses</strong>: run `hive integrate doctor` first, then confirm the
          adapter truth in Integrations.
        </li>
      </ul>
      <pre className="inline-json">{`mkdir my-hive
cd my-hive
git init
hive onboard demo --title "Demo project"
hive console serve`}</pre>
    </div>
  );
}

function BuiltInHelpCard() {
  return (
    <div className="hero-card">
      <p className="hero-card__eyebrow">Built-in help</p>
      <h3>Safe clicks inside the command center</h3>
      <p className="hero-card__subtle">
        Start with the read-mostly surfaces, then move toward steering only when Hive asks for
        operator judgment.
      </p>
      <ul className="reason-list">
        <li>
          <ConsoleLink to="/settings" className="getting-started__link">Open Settings</ConsoleLink>{" "}
          keeps connection and operator-local display truth in one place.
        </li>
        <li>
          <ConsoleLink to="/projects" className="getting-started__link">Open Projects</ConsoleLink>{" "}
          shows Program Doctor output and startup context.
        </li>
        <li>
          <ConsoleLink to="/inbox" className="getting-started__link">Open Inbox</ConsoleLink>{" "}
          is where approvals and exceptions should feel explicit.
        </li>
        <li>
          <ConsoleLink to="/runs" className="getting-started__link">Open Runs</ConsoleLink>{" "}
          becomes the live review surface once work is in motion.
        </li>
      </ul>
    </div>
  );
}

function GettingStarted({
  recommended,
  workspacePath,
}: {
  recommended: { task?: Record<string, unknown>; reasons?: string[] } | null;
  workspacePath: string;
}) {
  const projectId = recommended?.task ? String(recommended.task.project_id ?? "demo") : "demo";

  return (
    <div className="page-grid getting-started">
      <Panel eyebrow="Welcome" title="Getting Started with Agent Hive">
        <div className="stack">
          <KeyValueGrid
            values={[
              { label: "Workspace", value: workspacePath.trim() || "Choose one in Settings" },
              { label: "Safe first page", value: "Projects" },
              { label: "Demo path", value: "hive onboard demo" },
              { label: "Observe first", value: "Inbox / Runs / Activity" },
            ]}
          />

          <div className="hero-card">
            <h3>What is this?</h3>
            <p>
              Agent Hive is a control plane for autonomous work. You keep your coding agent
              (Codex, Claude Code, or any local tool) and Hive governs what it works on,
              isolates its changes, and gates its output.
            </p>
          </div>

          <div className="hero-card">
            <h3>The manager loop</h3>
            <p>Everything in Hive runs through three steps:</p>
            <ol className="reason-list">
              <li>
                <strong>hive next</strong> — picks the highest-priority ready task
              </li>
              <li>
                <strong>hive work</strong> — claims it, creates an isolated worktree, starts a governed run
              </li>
              <li>
                <strong>hive finish</strong> — evaluates the run against your policy and promotes or rejects
              </li>
            </ol>
            <p className="hero-card__subtle">
              This console updates live as runs progress. Use it to observe, steer, approve, and
              understand why Hive made each decision.
            </p>
          </div>

          <SafeFirstChecklist workspacePath={workspacePath} />
          <BuiltInHelpCard />
          <ChooseYourPathCard />

          <div className="hero-card">
            <p className="hero-card__eyebrow">Quick start from your terminal</p>
            <h3>Move from install to first action</h3>
            <pre className="inline-json">{`hive next --project-id ${projectId}
hive work --owner <your-name>
# make changes inside the run worktree
hive finish <run-id>`}</pre>
          </div>

          <RecommendedTaskCard recommended={recommended} />

          <p className="hero-card__subtle">
            Explore the{" "}
            <ConsoleLink to="/projects" className="getting-started__link">Open Projects</ConsoleLink>{" "}
            page to see your tasks and governance policy, or check the{" "}
            <ConsoleLink to="/inbox" className="getting-started__link">Open Inbox</ConsoleLink>{" "}
            surface for items that need your attention.
          </p>
        </div>
      </Panel>
    </div>
  );
}

export function HomePage() {
  const { apiBase, workspacePath } = useConsoleConfig();
  const client = createConsoleClient(apiBase, workspacePath);
  const { data, loading, error } = useConsoleQuery(
    `home:${apiBase}:${workspacePath}`,
    () => client.getHome(),
    3000,
  );

  const home = (data?.home ?? {}) as Record<string, unknown>;
  const recommended = (home.recommended_next ?? null) as
    | { task?: Record<string, unknown>; reasons?: string[] }
    | null;
  const activeRuns = Array.isArray(home.active_runs) ? home.active_runs : [];
  const evaluatingRuns = Array.isArray(home.evaluating_runs) ? home.evaluating_runs : [];
  const inbox = Array.isArray(home.inbox) ? home.inbox : [];
  const blocked = Array.isArray(home.blocked_projects) ? home.blocked_projects : [];
  const campaigns = Array.isArray(home.campaigns) ? home.campaigns : [];
  const recentEvents = Array.isArray(home.recent_events) ? home.recent_events : [];
  const recentAccepts = Array.isArray(home.recent_accepts) ? home.recent_accepts : [];

  // Show getting-started view only when the workspace is truly empty — no runs,
  // no inbox items, no blocked projects, no campaigns, no recent events.
  const hasActivity = activeRuns.length > 0 || evaluatingRuns.length > 0 ||
    recentAccepts.length > 0 || recentEvents.length > 0 ||
    inbox.length > 0 || blocked.length > 0 || campaigns.length > 0;

  if (!loading && !error && !hasActivity) {
    return <GettingStarted recommended={recommended} workspacePath={workspacePath} />;
  }

  return (
    <div className="page-grid">
      <Panel eyebrow="Portfolio overview" title="Home">
        {loading ? <p>Loading Home…</p> : null}
        {error ? <p className="error-copy">{error}</p> : null}
        {!loading && !error ? (
          <div className="stack">
            <KeyValueGrid
              values={[
                { label: "Workspace", value: workspacePath.trim() || String(home.workspace ?? "—") },
                { label: "Active runs", value: activeRuns.length },
                { label: "Awaiting review", value: evaluatingRuns.length },
                { label: "Inbox items", value: inbox.length },
                { label: "Campaigns", value: campaigns.length },
              ]}
            />

            <div className="card-grid">
              <SafeFirstChecklist workspacePath={workspacePath} />
              <BuiltInHelpCard />
              <RecommendedTaskCard recommended={recommended} />
              <ChooseYourPathCard />
            </div>
          </div>
        ) : null}
      </Panel>

      <Panel eyebrow="Live work" title="Active Runs">
        <div className="card-grid">
          {activeRuns.length ? (
            activeRuns.map((run) => <RunCard key={String((run as Record<string, unknown>).id)} run={run as Record<string, unknown>} />)
          ) : (
            <p>No active runs right now.</p>
          )}
        </div>
      </Panel>

      <Panel eyebrow="Exceptions" title="Inbox">
        <div className="stack">
          {inbox.length ? (
            inbox.map((item) => {
              const entry = item as Record<string, unknown>;
              return (
                <article className="list-card" key={String(entry.title)}>
                  <div className="list-card__header">
                    <h3>{String(entry.title ?? entry.kind ?? "Inbox item")}</h3>
                    <StatusPill tone={String(entry.kind ?? "info")}>
                      {String(entry.kind ?? "info")}
                    </StatusPill>
                  </div>
                  <p>{String(entry.reason ?? "Needs operator attention.")}</p>
                </article>
              );
            })
          ) : (
            <p>The inbox is clear.</p>
          )}
        </div>
      </Panel>

      <Panel eyebrow="Blockers" title="Blocked Projects">
        <div className="stack">
          {blocked.length ? (
            blocked.map((item) => {
              const project = item as Record<string, unknown>;
              return (
                <article className="list-card" key={String(project.project_id)}>
                  <div className="list-card__header">
                    <h3>{String(project.project_id ?? "project")}</h3>
                    <StatusPill tone={String(project.in_cycle ? "blocked" : "waiting")}>
                      {project.in_cycle ? "cycle" : "blocked"}
                    </StatusPill>
                  </div>
                  <ul className="reason-list">
                    {(Array.isArray(project.blocking_reasons) ? project.blocking_reasons : []).map(
                      (reason) => <li key={String(reason)}>{String(reason)}</li>,
                    )}
                  </ul>
                </article>
              );
            })
          ) : (
            <p>No blocked projects.</p>
          )}
        </div>
      </Panel>

      <Panel eyebrow="Portfolio loops" title="Campaigns">
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
                    Driver: {String(campaign.driver ?? "—")} • Briefs:{" "}
                    {String(campaign.brief_cadence ?? "—")}
                  </p>
                </article>
              );
            })
          ) : (
            <p>No campaigns exist yet.</p>
          )}
        </div>
      </Panel>

      <Panel eyebrow="What changed" title="Recent Activity">
        <div className="stack">
          {recentEvents.length ? (
            recentEvents.slice(0, 6).map((item) => {
              const event = item as Record<string, unknown>;
              return (
                <article className="list-card" key={String(event.event_id ?? event.ts)}>
                  <div className="list-card__header">
                    <h3>{String(event.type ?? "event")}</h3>
                    <span className="list-card__meta">{String(event.ts ?? "—")}</span>
                  </div>
                  <p>{String((event.payload as Record<string, unknown> | undefined)?.message ?? "Audit event recorded.")}</p>
                </article>
              );
            })
          ) : recentAccepts.length ? (
            recentAccepts.map((run) => (
              <RunCard key={String((run as Record<string, unknown>).id)} run={run as Record<string, unknown>} />
            ))
          ) : (
            <p>No recent activity.</p>
          )}
        </div>
      </Panel>
    </div>
  );
}
