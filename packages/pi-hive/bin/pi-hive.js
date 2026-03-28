#!/usr/bin/env node

import { spawnSync } from "node:child_process"
import { appendFileSync, mkdirSync, readFileSync, writeFileSync } from "node:fs"
import { dirname, join, resolve } from "node:path"

function printUsage() {
  console.log(`Usage: pi-hive <command> [args...]

Commands:
  connect                      Run \`hive integrate pi\`
  doctor                       Run \`hive integrate doctor pi\`
  next                         Run \`hive next\`
  search <query>               Run \`hive search <query>\`
  open <task-id>               Run \`hive run start <task-id> --driver pi\`
  attach <native-ref> --task-id <task-id>
                               Run \`hive integrate attach pi <native-ref> --task-id <task-id>\`
  finish <run-id>              Run \`hive finish <run-id>\`
  note <run-id> <message...>   Run \`hive steer note <run-id> --message ...\`
  status <run-id>              Run \`hive run status <run-id>\`
`)
}

function runHive(args) {
  const command = process.env.HIVE_BIN || "hive"
  const result = spawnSync(command, args, { stdio: "inherit" })
  if (result.error) {
    console.error(String(result.error))
    process.exit(1)
  }
  process.exit(result.status ?? 0)
}

function splitHiveGlobals(args) {
  const globals = []
  const locals = []
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index]
    if (arg === "--json") {
      globals.push(arg)
      continue
    }
    if (arg === "--path" && args[index + 1]) {
      globals.push(arg, args[index + 1])
      index += 1
      continue
    }
    locals.push(arg)
  }
  return { globals, locals }
}

function runHiveForward(baseArgs, passthroughArgs = []) {
  const { globals, locals } = splitHiveGlobals(passthroughArgs)
  runHive([...globals, ...baseArgs, ...locals])
}

function safeSessionRef(value) {
  return Array.from(value)
    .map((character) =>
      /[A-Za-z0-9_.-]/.test(character) ? character : "_"
    )
    .join("")
}

function writeJson(pathValue, payload) {
  mkdirSync(dirname(pathValue), { recursive: true })
  writeFileSync(pathValue, `${JSON.stringify(payload, null, 2)}\n`, "utf8")
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

function appendJsonl(pathValue, payload) {
  mkdirSync(dirname(pathValue), { recursive: true })
  appendFileSync(pathValue, `${JSON.stringify(payload)}\n`, "utf8")
}

function nextSeq(pathValue) {
  return readJsonl(pathValue).length
}

function startNativeSession(nativeSessionRef, rest) {
  let workspace = process.cwd()
  let autoExitMs = 8000
  for (let index = 0; index < rest.length; index += 1) {
    const arg = rest[index]
    if (arg === "--workspace" && rest[index + 1]) {
      workspace = resolve(rest[index + 1])
      index += 1
    } else if (arg === "--auto-exit-ms" && rest[index + 1]) {
      autoExitMs = Number(rest[index + 1]) || autoExitMs
      index += 1
    }
  }
  const sessionRoot = join(
    workspace,
    ".hive",
    "pi-native",
    "sessions",
    safeSessionRef(nativeSessionRef)
  )
  const manifestPath = join(sessionRoot, "manifest.json")
  const statePath = join(sessionRoot, "state.json")
  const steeringPath = join(sessionRoot, "steering.ndjson")
  const transcriptPath = join(sessionRoot, "transcript.jsonl")
  writeJson(manifestPath, {
    native_session_ref: nativeSessionRef,
    status: "running",
    workspace_root: workspace,
    transcript_path: transcriptPath,
    steering_path: steeringPath,
    started_at: new Date().toISOString(),
  })
  writeJson(statePath, {
    state: "running",
    health: "healthy",
    updated_at: new Date().toISOString(),
  })
  appendJsonl(transcriptPath, {
    seq: nextSeq(transcriptPath),
    kind: "session_start",
    harness: "pi",
    adapter_family: "worker_session",
    native_session_ref: nativeSessionRef,
    payload: { mode: "native" },
    ts: new Date().toISOString(),
    schema_version: "2.4.0",
  })
  appendJsonl(transcriptPath, {
    seq: nextSeq(transcriptPath),
    kind: "assistant_delta",
    harness: "pi",
    adapter_family: "worker_session",
    native_session_ref: nativeSessionRef,
    payload: { text: "Pi native session is ready for Hive attach." },
    ts: new Date().toISOString(),
    schema_version: "2.4.0",
  })
  console.log(
    JSON.stringify({
      ok: true,
      native_session_ref: nativeSessionRef,
      manifest: manifestPath,
    })
  )

  let steeringCursor = 0
  const interval = setInterval(() => {
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
      if (note) {
        appendJsonl(transcriptPath, {
          seq: nextSeq(transcriptPath),
          kind: "assistant_delta",
          harness: "pi",
          adapter_family: "worker_session",
          native_session_ref: nativeSessionRef,
          payload: { text: `Hive note: ${note}` },
          ts: new Date().toISOString(),
          schema_version: "2.4.0",
        })
      }
      if (action === "cancel") {
        appendJsonl(transcriptPath, {
          seq: nextSeq(transcriptPath),
          kind: "session_end",
          harness: "pi",
          adapter_family: "worker_session",
          native_session_ref: nativeSessionRef,
          payload: { reason: "cancel" },
          ts: new Date().toISOString(),
          schema_version: "2.4.0",
        })
        writeJson(statePath, {
          state: "cancelled",
          health: "cancelled",
          updated_at: new Date().toISOString(),
        })
        process.exit(0)
      }
    }
  }, 100)

  setTimeout(() => {
    clearInterval(interval)
    appendJsonl(transcriptPath, {
      seq: nextSeq(transcriptPath),
      kind: "session_end",
      harness: "pi",
      adapter_family: "worker_session",
      native_session_ref: nativeSessionRef,
      payload: { reason: "timeout" },
      ts: new Date().toISOString(),
      schema_version: "2.4.0",
    })
    writeJson(statePath, {
      state: "completed_candidate",
      health: "healthy",
      updated_at: new Date().toISOString(),
    })
    process.exit(0)
  }, autoExitMs)
}

const [command, ...rest] = process.argv.slice(2)

switch (command) {
  case undefined:
  case "--help":
  case "-h":
  case "help":
    printUsage()
    break
  case "connect":
    runHiveForward(["integrate", "pi"], rest)
    break
  case "doctor":
    runHiveForward(["integrate", "doctor", "pi"], rest)
    break
  case "next":
    runHiveForward(["next"], rest)
    break
  case "search":
    if (rest.length === 0) {
      console.error("search requires a query")
      process.exit(2)
    }
    runHiveForward(["search", rest[0]], rest.slice(1))
    break
  case "open":
    if (rest.length === 0) {
      console.error("open requires a task id")
      process.exit(2)
    }
    runHiveForward(["run", "start", rest[0], "--driver", "pi"], rest.slice(1))
    break
  case "attach":
    if (rest.length === 0) {
      console.error("attach requires a native session ref")
      process.exit(2)
    }
    runHiveForward(["integrate", "attach", "pi", rest[0]], rest.slice(1))
    break
  case "finish":
    if (rest.length === 0) {
      console.error("finish requires a run id")
      process.exit(2)
    }
    runHiveForward(["finish", rest[0]], rest.slice(1))
    break
  case "note":
    if (rest.length < 2) {
      console.error("note requires a run id and message")
      process.exit(2)
    }
    runHiveForward(["steer", "note", rest[0], "--message", rest.slice(1).join(" ")])
    break
  case "status":
    if (rest.length === 0) {
      console.error("status requires a run id")
      process.exit(2)
    }
    runHiveForward(["run", "status", rest[0]], rest.slice(1))
    break
  case "session-start":
    if (rest.length === 0) {
      console.error("session-start requires a native session ref")
      process.exit(2)
    }
    startNativeSession(rest[0], rest.slice(1))
    break
  default:
    console.error(`Unknown command: ${command}`)
    printUsage()
    process.exit(2)
}
