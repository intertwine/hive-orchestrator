/** Configuration for the Agent Hive OpenCode plugin. */
export interface AgentHiveConfig {
  /** Path to hive root directory. Defaults to cwd. */
  basePath?: string
  /** Auto-claim a task when editing files in its project. Default: true. */
  autoClaimOnEdit?: boolean
  /** Block file edits when task is not claimed. Default: false. */
  enforceOwnership?: boolean
  /** Inject startup context on session start. Default: true. */
  injectContext?: boolean
  /** Log significant actions to Hive notes. Default: true. */
  logActions?: boolean
  /** Optional coordinator server URL. */
  coordinatorUrl?: string
  /** Agent identifier injected into claims. Default: "opencode-<model>". */
  agentName?: string
}

/** A Hive task as returned by `hive task ready --json`. */
export interface HiveTask {
  id: string
  title: string
  status: "ready" | "active" | "done" | "blocked"
  priority: number
  project_id: string
  owner: string | null
  claimed_until: string | null
}

/** Lightweight project context built from task metadata. */
export interface HiveProjectContext {
  projectId: string
  tasks: HiveTask[]
  readyCount: number
  activeCount: number
}
