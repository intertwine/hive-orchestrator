import { getReadyTasks } from "./hive-client.js"
import type { HiveProjectContext, HiveTask } from "../types/index.js"

/** Build a summary context block for a set of tasks. */
export function buildContextBlock(projectId: string, tasks: HiveTask[]): string {
  const ready = tasks.filter((t) => t.status === "ready")
  const active = tasks.filter((t) => t.status === "active")
  const lines: string[] = [
    `## Project: ${projectId}`,
    `Ready tasks: ${ready.length}  Active tasks: ${active.length}`,
  ]
  for (const t of ready.slice(0, 5)) {
    lines.push(`- [ready] ${t.title}`)
  }
  for (const t of active) {
    lines.push(`- [active] ${t.title}`)
  }
  return lines.join("\n")
}

/** Fetch all ready tasks and group them by project. */
export async function buildWorkspaceContext(cwd?: string): Promise<HiveProjectContext[]> {
  const tasks = await getReadyTasks(cwd)
  const byProject = new Map<string, HiveTask[]>()
  for (const task of tasks) {
    const list = byProject.get(task.project_id) ?? []
    list.push(task)
    byProject.set(task.project_id, list)
  }
  return Array.from(byProject.entries()).map(([projectId, pts]) => ({
    projectId,
    tasks: pts,
    readyCount: pts.filter((t) => t.status === "ready").length,
    activeCount: pts.filter((t) => t.status === "active").length,
  }))
}
