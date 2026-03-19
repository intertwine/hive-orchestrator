import type { AgentHiveConfig } from "../types/index.js"

const DEFAULTS: Required<AgentHiveConfig> = {
  basePath: process.cwd(),
  autoClaimOnEdit: true,
  enforceOwnership: false,
  injectContext: true,
  logActions: true,
  coordinatorUrl: "",
  agentName: `opencode-${process.env.OPENCODE_MODEL ?? "agent"}`,
}

/** Merge user-supplied config with defaults. */
export function resolveConfig(partial: AgentHiveConfig = {}): Required<AgentHiveConfig> {
  return { ...DEFAULTS, ...partial }
}
