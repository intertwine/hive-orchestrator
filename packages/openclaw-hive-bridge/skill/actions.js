#!/usr/bin/env node
/**
 * ClawHub agent-hive skill — action implementations.
 *
 * Each action wraps a stable `hive` CLI command. The skill manifest
 * (manifest.json) declares the intents; this module executes them.
 *
 * Usage from ClawHub runtime:
 *   node actions.js <intent> [args...]
 *
 * Or as a library:
 *   const { executeAction } = require("./actions");
 *   const result = await executeAction("hive_next", { projectId: "demo" });
 */

"use strict";

const { spawnSync } = require("child_process");

function runHive(args) {
  const result = spawnSync("hive", args, {
    stdio: ["pipe", "pipe", "pipe"],
    encoding: "utf-8",
    timeout: 30000,
  });
  if (result.error) {
    return { ok: false, error: String(result.error) };
  }
  try {
    return JSON.parse(result.stdout);
  } catch {
    return {
      ok: result.status === 0,
      stdout: result.stdout.trim(),
      stderr: result.stderr.trim(),
    };
  }
}

const ACTIONS = {
  hive_next({ projectId } = {}) {
    const args = ["--json", "next"];
    if (projectId) args.push("--project-id", projectId);
    return runHive(args);
  },

  hive_search({ query } = {}) {
    if (!query) return { ok: false, error: "query is required" };
    return runHive(["--json", "search", query]);
  },

  hive_attach({ sessionKey, projectId, taskId } = {}) {
    if (!sessionKey) return { ok: false, error: "sessionKey is required" };
    const args = ["--json", "integrate", "attach", "openclaw", sessionKey];
    if (projectId) args.push("--project-id", projectId);
    if (taskId) args.push("--task-id", taskId);
    return runHive(args);
  },

  hive_finish({ runId } = {}) {
    if (!runId) return { ok: false, error: "runId is required" };
    return runHive(["--json", "finish", runId]);
  },

  hive_note({ runId, note } = {}) {
    if (!runId || !note) return { ok: false, error: "runId and note are required" };
    return runHive(["--json", "steer", "note", runId, "--message", note]);
  },

  hive_status({ runId } = {}) {
    if (!runId) {
      return runHive(["--json", "console", "home"]);
    }
    return runHive(["--json", "console", "run", runId]);
  },
};

function executeAction(intent, params) {
  const handler = ACTIONS[intent];
  if (!handler) {
    return { ok: false, error: `Unknown intent: ${intent}` };
  }
  return handler(params);
}

// CLI mode: node actions.js <intent> [json-params]
if (require.main === module) {
  const [intent, paramsJson] = process.argv.slice(2);
  if (!intent) {
    console.log(JSON.stringify({ ok: false, error: "Usage: actions.js <intent> [json-params]" }));
    process.exit(2);
  }
  let params = {};
  if (paramsJson) {
    try {
      params = JSON.parse(paramsJson);
    } catch {
      console.log(JSON.stringify({ ok: false, error: "Invalid JSON params" }));
      process.exit(2);
    }
  }
  const result = executeAction(intent, params);
  console.log(JSON.stringify(result));
}

module.exports = { executeAction, ACTIONS };
