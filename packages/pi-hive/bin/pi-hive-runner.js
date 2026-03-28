#!/usr/bin/env node

import { appendFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs"
import { dirname, join, resolve } from "node:path"

function usage() {
  console.log(
    "Usage: pi-hive-runner --run-id <id> --task-id <id> --project-id <id> --worktree <path> --artifacts <path> --context <path> --state <path> --steering <path> --trajectory <path> --last-message <path> --native-session-ref <ref>"
  )
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

function ensureDir(pathValue) {
  mkdirSync(dirname(pathValue), { recursive: true })
}

function writeJson(pathValue, payload) {
  ensureDir(pathValue)
  writeFileSync(pathValue, `${JSON.stringify(payload, null, 2)}\n`, "utf8")
}

function appendJsonl(pathValue, payload) {
  ensureDir(pathValue)
  appendFileSync(pathValue, `${JSON.stringify(payload)}\n`, "utf8")
}

function readJsonl(pathValue) {
  try {
    return readFileSync(pathValue, "utf8")
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
  } catch {
    return []
  }
}

function nextSeq(pathValue) {
  return readJsonl(pathValue).length
}

function appendTrajectory(pathValue, args, kind, payload) {
  appendJsonl(pathValue, {
    seq: nextSeq(pathValue),
    kind,
    harness: "pi",
    adapter_family: "worker_session",
    native_session_ref: args["native-session-ref"],
    run_id: args["run-id"],
    project_id: args["project-id"] ?? null,
    task_id: args["task-id"] ?? null,
    payload,
    ts: new Date().toISOString(),
    schema_version: "2.4.0",
  })
}

const args = parseArgs(process.argv.slice(2))
if (
  !args ||
  !args["run-id"] ||
  !args.artifacts ||
  !args.state ||
  !args.steering ||
  !args.trajectory ||
  !args["last-message"] ||
  !args["native-session-ref"]
) {
  usage()
  process.exit(2)
}

const artifactsRoot = resolve(args.artifacts)
const manifestPath = join(artifactsRoot, "pi-runner-manifest.json")
const statePath = resolve(args.state)
const steeringPath = resolve(args.steering)
const trajectoryPath = resolve(args.trajectory)
const lastMessagePath = resolve(args["last-message"])

function updateManifest(status, extra = {}) {
  writeJson(manifestPath, {
    harness: "pi",
    run_id: args["run-id"],
    task_id: args["task-id"] ?? null,
    project_id: args["project-id"] ?? null,
    worktree: args.worktree ?? null,
    context: args.context ?? null,
    steering_path: steeringPath,
    trajectory_path: trajectoryPath,
    native_session_ref: args["native-session-ref"],
    ts: new Date().toISOString(),
    status,
    ...extra,
  })
}

function updateState(state, message, extra = {}) {
  writeJson(statePath, {
    state,
    health: state === "failed" ? "failed" : state === "cancelled" ? "cancelled" : "healthy",
    message,
    updated_at: new Date().toISOString(),
    wall_minutes: 0,
    ...extra,
  })
}

function finish(state, message) {
  writeFileSync(lastMessagePath, `${message}\n`, "utf8")
  appendTrajectory(
    trajectoryPath,
    args,
    "assistant_delta",
    { text: message }
  )
  appendTrajectory(
    trajectoryPath,
    args,
    "session_end",
    { state }
  )
  updateState(state, message, { finished_at: new Date().toISOString() })
  updateManifest(state, { finished_at: new Date().toISOString() })
  process.exit(state === "failed" ? 1 : 0)
}

updateState("running", "Pi managed session is active.")
updateManifest("running", { state_path: statePath })

let steeringCursor = 0
let interval = null
let autoFinish = null

function stopAndFinish(state, message) {
  if (interval !== null) {
    clearInterval(interval)
  }
  if (autoFinish !== null) {
    clearTimeout(autoFinish)
  }
  finish(state, message)
}

function processSteering() {
  const lines = readJsonl(steeringPath)
  const nextLines = lines.slice(steeringCursor)
  if (!nextLines.length) {
    return
  }
  steeringCursor = lines.length
  for (const line of nextLines) {
    let payload
    try {
      payload = JSON.parse(line)
    } catch {
      continue
    }
    const action = String(payload.action ?? "")
    const note = String(payload.note ?? "")
    if (action === "cancel") {
      stopAndFinish("cancelled", "Pi managed session cancelled by Hive.")
    }
    if (action === "pause") {
      updateState("running", "Pi managed session paused by Hive.")
      appendTrajectory(trajectoryPath, args, "assistant_delta", {
        text: "Pi managed session acknowledged pause.",
      })
      continue
    }
    if (action === "resume") {
      updateState("running", "Pi managed session resumed by Hive.")
      appendTrajectory(trajectoryPath, args, "assistant_delta", {
        text: "Pi managed session acknowledged resume.",
      })
      continue
    }
    if (note) {
      stopAndFinish("completed_candidate", `Pi received Hive steering: ${note}`)
    }
  }
}

interval = setInterval(processSteering, 100)
autoFinish = setTimeout(() => {
  stopAndFinish("completed_candidate", "Pi managed session finished without additional steering.")
}, 5000)

process.on("SIGINT", () => stopAndFinish("cancelled", "Pi managed session interrupted."))
process.on("SIGTERM", () => stopAndFinish("cancelled", "Pi managed session terminated."))

console.log(JSON.stringify({ ok: true, manifest: manifestPath, state: statePath }))
