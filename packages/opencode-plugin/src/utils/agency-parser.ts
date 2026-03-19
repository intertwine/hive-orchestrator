import { parse as parseYaml } from "yaml"
import { readFile } from "node:fs/promises"

export interface AgencyFrontmatter {
  project_id: string
  status: string
  owner: string | null
  blocked: boolean
  blocking_reason: string | null
  priority: string
  tags: string[]
  [key: string]: unknown
}

/** Parse YAML frontmatter from an AGENCY.md file. Returns null on failure. */
export async function parseAgencyFile(filePath: string): Promise<AgencyFrontmatter | null> {
  try {
    const content = await readFile(filePath, "utf-8")
    const match = content.match(/^---\r?\n([\s\S]*?)\r?\n---/)
    if (!match) return null
    return parseYaml(match[1]) as AgencyFrontmatter
  } catch {
    return null
  }
}
