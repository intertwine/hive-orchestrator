/**
 * @agent-hive/opencode-plugin
 *
 * OpenCode plugin that integrates with the Agent Hive v2 orchestration system.
 * Delegates all substrate operations to the `hive` CLI (--json).
 */

import { resolveConfig } from "./utils/config.js"
import { onSessionStart, onSessionEnd } from "./hooks/session.js"
import { toolExecuteBefore, toolExecuteAfter } from "./hooks/tool.js"
import { chatMessageHook } from "./hooks/chat.js"
import { permissionHook } from "./hooks/permission.js"
import type { AgentHiveConfig } from "./types/index.js"

export type { AgentHiveConfig, HiveTask, HiveProjectContext } from "./types/index.js"
export { resolveConfig } from "./utils/config.js"
export { getReadyTasks, claimTask, finishTask } from "./services/hive-client.js"
export { buildWorkspaceContext, buildContextBlock } from "./services/project-context.js"
export { claimNextTask, getProjectReadyTasks } from "./services/ownership.js"
export { parseAgencyFile } from "./utils/agency-parser.js"

/**
 * Register the Agent Hive plugin.
 * Call this from your opencode plugin entry point.
 */
export function register(partial: AgentHiveConfig = {}) {
  const config = resolveConfig(partial)
  return {
    name: "@agent-hive/opencode-plugin",
    onSessionStart: () => onSessionStart(config),
    onSessionEnd: () => onSessionEnd(config),
    toolExecuteBefore: (input: Parameters<typeof toolExecuteBefore>[0]) =>
      toolExecuteBefore(input, config),
    toolExecuteAfter: (input: Parameters<typeof toolExecuteAfter>[0]) =>
      toolExecuteAfter(input, config),
    chatMessage: (msg: Parameters<typeof chatMessageHook>[0]) => chatMessageHook(msg, config),
    permission: (req: Parameters<typeof permissionHook>[0]) => permissionHook(req, config),
  }
}
