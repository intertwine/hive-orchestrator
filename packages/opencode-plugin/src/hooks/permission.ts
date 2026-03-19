import { logger } from "../utils/logger.js"
import type { AgentHiveConfig } from "../types/index.js"

interface PermissionRequest {
  tool: string
  args: Record<string, unknown>
}

/**
 * Permission hook — runs before the agent is granted permission to use a tool.
 * Returns true to allow, false to deny. Defaults to allow.
 */
export async function permissionHook(
  request: PermissionRequest,
  config: Required<AgentHiveConfig>
): Promise<boolean> {
  // By default, allow everything. Enforcement is done in toolExecuteBefore.
  logger.debug(`permissionHook: ${request.tool}`)
  return true
}
