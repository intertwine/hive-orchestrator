import { describe, it, expect } from "vitest"
import { resolveConfig } from "../src/utils/config.js"

describe("resolveConfig", () => {
  it("applies defaults for empty input", () => {
    const config = resolveConfig()
    expect(config.autoClaimOnEdit).toBe(true)
    expect(config.enforceOwnership).toBe(false)
    expect(config.injectContext).toBe(true)
    expect(config.logActions).toBe(true)
  })

  it("overrides defaults with user values", () => {
    const config = resolveConfig({ enforceOwnership: true, logActions: false })
    expect(config.enforceOwnership).toBe(true)
    expect(config.logActions).toBe(false)
    expect(config.autoClaimOnEdit).toBe(true) // default preserved
  })

  it("accepts a custom agentName", () => {
    const config = resolveConfig({ agentName: "my-bot" })
    expect(config.agentName).toBe("my-bot")
  })
})
