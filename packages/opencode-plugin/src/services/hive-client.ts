import { execFile } from "node:child_process"
import { promisify } from "node:util"
import type { HiveTask } from "../types/index.js"
import { logger } from "../utils/logger.js"

const execFileAsync = promisify(execFile)

/** Run a hive CLI command with --json and return the parsed output. */
async function hive<T>(args: string[], cwd?: string): Promise<T> {
  const { stdout } = await execFileAsync("hive", [...args, "--json"], { cwd })
  return JSON.parse(stdout) as T
}

/** Return ready tasks from the workspace. */
export async function getReadyTasks(cwd?: string): Promise<HiveTask[]> {
  try {
    return await hive<HiveTask[]>(["task", "ready"], cwd)
  } catch (err) {
    logger.warn("Could not fetch ready tasks from hive CLI")
    logger.debug(String(err))
    return []
  }
}

/** Claim a task for the given owner. */
export async function claimTask(taskId: string, owner: string, cwd?: string): Promise<void> {
  await hive<unknown>(["work", taskId, "--owner", owner], cwd)
}

/** Mark a task as done (finish the active run). */
export async function finishTask(runId: string, cwd?: string): Promise<void> {
  await hive<unknown>(["finish", runId], cwd)
}
