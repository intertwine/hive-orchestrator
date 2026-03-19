import { describe, it, expect, vi, beforeEach } from "vitest"
import { chatMessageHook } from "../src/hooks/chat.js"
import { onSessionStart, onSessionEnd } from "../src/hooks/session.js"
import { toolExecuteBefore, toolExecuteAfter } from "../src/hooks/tool.js"
import { permissionHook } from "../src/hooks/permission.js"
import { resolveConfig } from "../src/utils/config.js"

vi.mock("../src/services/hive-client.js", () => ({
  getReadyTasks: vi.fn().mockResolvedValue([]),
  claimTask: vi.fn(),
  finishTask: vi.fn(),
}))

const config = resolveConfig({ agentName: "test-agent", injectContext: true, logActions: true })

describe("chatMessageHook", () => {
  it("returns non-user messages unchanged", async () => {
    const msg = { role: "assistant", content: "hello" }
    expect(await chatMessageHook(msg, config)).toEqual(msg)
  })

  it("returns user message unchanged when no project mentioned", async () => {
    const msg = { role: "user", content: "what is the weather" }
    expect(await chatMessageHook(msg, config)).toEqual(msg)
  })
})

describe("onSessionStart", () => {
  it("runs without throwing", async () => {
    await expect(onSessionStart(config)).resolves.toBeUndefined()
  })
})

describe("onSessionEnd", () => {
  it("runs without throwing", async () => {
    await expect(onSessionEnd(config)).resolves.toBeUndefined()
  })
})

describe("toolExecuteBefore", () => {
  it("ignores non-modifying tools", async () => {
    await expect(
      toolExecuteBefore({ tool: "read", args: {} }, config)
    ).resolves.toBeUndefined()
  })
})

describe("toolExecuteAfter", () => {
  it("ignores non-loggable tools", async () => {
    await expect(
      toolExecuteAfter({ tool: "read", args: {} }, config)
    ).resolves.toBeUndefined()
  })
})

describe("permissionHook", () => {
  it("allows by default", async () => {
    const result = await permissionHook({ tool: "edit", args: {} }, config)
    expect(result).toBe(true)
  })
})
