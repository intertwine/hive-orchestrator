import { buildWorkspaceContext } from "../services/project-context.js"
import { logger } from "../utils/logger.js"
import type { AgentHiveConfig } from "../types/index.js"

/** Display ready work at session start. */
export async function onSessionStart(config: Required<AgentHiveConfig>): Promise<void> {
  if (!config.injectContext) return
  try {
    const contexts = await buildWorkspaceContext(config.basePath)
    const ready = contexts.filter((c) => c.readyCount > 0)
    if (ready.length === 0) return
    logger.info(`${ready.length} project(s) have ready work:`)
    for (const ctx of ready) {
      logger.info(`  ${ctx.projectId} — ${ctx.readyCount} task(s) ready`)
    }
  } catch (err) {
    logger.warn("onSessionStart: could not fetch workspace context")
    logger.debug(String(err))
  }
}

/** Remind about the handoff protocol at session end. */
export async function onSessionEnd(config: Required<AgentHiveConfig>): Promise<void> {
  if (!config.logActions) return
  logger.info("Session ending — remember to run `hive sync projections --json` before handoff.")
}
