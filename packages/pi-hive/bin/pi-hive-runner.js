#!/usr/bin/env node

import { mkdirSync, writeFileSync } from "node:fs"
import { dirname, join, resolve } from "node:path"

function usage() {
  console.log(`Usage: pi-hive-runner --run-id <id> --task-id <id> --project-id <id> --worktree <path> --artifacts <path> --context <path>`)
}

function parseArgs(argv) {
  const parsed = {}
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index]
    const value = argv[index + 1]
    if (!key || !key.startsWith("--") || value === undefined) {
      return null
    }
    parsed[key.slice(2)] = value
  }
  return parsed
}

const args = parseArgs(process.argv.slice(2))
if (!args || !args["run-id"] || !args.artifacts) {
  usage()
  process.exit(2)
}

const artifactsRoot = resolve(args.artifacts)
const manifestPath = join(artifactsRoot, "pi-runner-manifest.json")
mkdirSync(dirname(manifestPath), { recursive: true })
writeFileSync(
  manifestPath,
  JSON.stringify(
    {
      harness: "pi",
      run_id: args["run-id"],
      task_id: args["task-id"] ?? null,
      project_id: args["project-id"] ?? null,
      worktree: args.worktree ?? null,
      context: args.context ?? null,
      ts: new Date().toISOString(),
      status: "scaffolded",
    },
    null,
    2
  ) + "\n",
  "utf8"
)
console.log(JSON.stringify({ ok: true, manifest: manifestPath }))
