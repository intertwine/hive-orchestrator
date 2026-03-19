import { describe, it, expect, vi } from "vitest"
import { buildWorkspaceContext, buildContextBlock } from "../src/services/project-context.js"
import { getProjectReadyTasks } from "../src/services/ownership.js"
import type { HiveTask } from "../src/types/index.js"

vi.mock("../src/services/hive-client.js", () => ({
  getReadyTasks: vi.fn().mockResolvedValue([
    {
      id: "task_001",
      title: "Do something",
      status: "ready",
      priority: 1,
      project_id: "my-project",
      owner: null,
      claimed_until: null,
    } satisfies HiveTask,
  ]),
  claimTask: vi.fn(),
  finishTask: vi.fn(),
}))

describe("buildWorkspaceContext", () => {
  it("groups tasks by project", async () => {
    const ctxs = await buildWorkspaceContext()
    expect(ctxs).toHaveLength(1)
    expect(ctxs[0].projectId).toBe("my-project")
    expect(ctxs[0].readyCount).toBe(1)
  })
})

describe("buildContextBlock", () => {
  it("returns a non-empty string", () => {
    const tasks: HiveTask[] = [
      {
        id: "t1",
        title: "First task",
        status: "ready",
        priority: 1,
        project_id: "proj",
        owner: null,
        claimed_until: null,
      },
    ]
    const block = buildContextBlock("proj", tasks)
    expect(block).toContain("proj")
    expect(block).toContain("First task")
  })
})

describe("getProjectReadyTasks", () => {
  it("filters by project", async () => {
    const tasks = await getProjectReadyTasks("my-project")
    expect(tasks).toHaveLength(1)
    expect(tasks[0].project_id).toBe("my-project")
  })

  it("returns empty for unknown project", async () => {
    const tasks = await getProjectReadyTasks("unknown-project")
    expect(tasks).toHaveLength(0)
  })
})
