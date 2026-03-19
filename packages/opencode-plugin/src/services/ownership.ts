import { claimTask, getReadyTasks } from "./hive-client.js"
import { logger } from "../utils/logger.js"
import type { HiveTask } from "../types/index.js"

/** Find ready tasks for a given project. */
export async function getProjectReadyTasks(projectId: string, cwd?: string): Promise<HiveTask[]> {
  const tasks = await getReadyTasks(cwd)
  return tasks.filter((t) => t.project_id === projectId)
}

/** Claim the first ready task in a project. Returns the task or null. */
export async function claimNextTask(
  projectId: string,
  agentName: string,
  cwd?: string
): Promise<HiveTask | null> {
  const ready = await getProjectReadyTasks(projectId, cwd)
  if (ready.length === 0) return null
  const task = ready[0]
  try {
    await claimTask(task.id, agentName, cwd)
    logger.info(`Claimed task ${task.id}: ${task.title}`)
    return task
  } catch (err) {
    logger.warn(`Failed to claim task ${task.id}`)
    logger.debug(String(err))
    return null
  }
}
