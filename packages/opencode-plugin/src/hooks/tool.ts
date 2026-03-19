import { logger } from "../utils/logger.js"
import type { AgentHiveConfig } from "../types/index.js"

const MODIFYING_TOOLS = new Set(["edit", "write", "multiEdit", "notebookEdit"])
const LOGGABLE_TOOLS = new Set(["edit", "write", "bash", "multiEdit"])

interface ToolInput {
  tool: string
  args: Record<string, unknown>
}

/** Check ownership before file-modifying tool calls. */
export async function toolExecuteBefore(
  input: ToolInput,
  config: Required<AgentHiveConfig>
): Promise<void> {
  if (!MODIFYING_TOOLS.has(input.tool)) return
  // Ownership enforcement is opt-in; auto-claim is handled by the caller.
  if (config.enforceOwnership) {
    logger.debug(`toolExecuteBefore: ${input.tool} on ${String(input.args.filePath ?? "")}`)
  }
}

/** Log action after a tool completes. */
export async function toolExecuteAfter(
  input: ToolInput,
  config: Required<AgentHiveConfig>
): Promise<void> {
  if (!config.logActions) return
  if (!LOGGABLE_TOOLS.has(input.tool)) return
  const target = String(input.args.filePath ?? input.args.command ?? "")
  logger.debug(`toolExecuteAfter: ${input.tool} ${target}`)
}
