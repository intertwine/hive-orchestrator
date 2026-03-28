#!/usr/bin/env node

import { spawnSync } from "node:child_process"

function printUsage() {
  console.log(`Usage: pi-hive <command> [args...]

Commands:
  connect            Run \`hive integrate pi\`
  doctor             Run \`hive integrate doctor pi\`
  next               Run \`hive next\`
  search <query>     Run \`hive search <query>\`
  finish <run-id>    Run \`hive finish <run-id>\`
  note <run-id> <message...>
                     Run \`hive steer note <run-id> --message ...\`
  status <run-id>    Run \`hive run status <run-id>\`
  open               Reserved for the forthcoming Pi live-open flow
  attach             Reserved for the forthcoming Pi live-attach flow
`)
}

function notYetWired(command) {
  console.error(
    `${command} is reserved for the forthcoming Pi live session flow. Use \`pi-hive connect\` and \`hive integrate doctor pi\` for now.`
  )
  process.exit(2)
}

function runHive(args) {
  const result = spawnSync("hive", args, { stdio: "inherit" })
  if (result.error) {
    console.error(String(result.error))
    process.exit(1)
  }
  process.exit(result.status ?? 0)
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
    runHive(["integrate", "pi", ...rest])
    break
  case "doctor":
    runHive(["integrate", "doctor", "pi", ...rest])
    break
  case "next":
    runHive(["next", ...rest])
    break
  case "search":
    if (rest.length === 0) {
      console.error("search requires a query")
      process.exit(2)
    }
    runHive(["search", rest[0], ...rest.slice(1)])
    break
  case "finish":
    if (rest.length === 0) {
      console.error("finish requires a run id")
      process.exit(2)
    }
    runHive(["finish", rest[0], ...rest.slice(1)])
    break
  case "note":
    if (rest.length < 2) {
      console.error("note requires a run id and message")
      process.exit(2)
    }
    runHive(["steer", "note", rest[0], "--message", rest.slice(1).join(" ")])
    break
  case "status":
    if (rest.length === 0) {
      console.error("status requires a run id")
      process.exit(2)
    }
    runHive(["run", "status", rest[0], ...rest.slice(1)])
    break
  case "open":
  case "attach":
    notYetWired(command)
    break
  default:
    console.error(`Unknown command: ${command}`)
    printUsage()
    process.exit(2)
}
