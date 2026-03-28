#!/usr/bin/env node
/**
 * openclaw-hive-bridge — Gateway ↔ Hive Link bridge.
 *
 * Connects to an OpenClaw Gateway and exposes session listing, attach,
 * event streaming, and steering via Hive Link NDJSON on stdio or HTTP.
 *
 * Usage:
 *   openclaw-hive-bridge --gateway http://localhost:3000 --stdio
 *   openclaw-hive-bridge --gateway http://localhost:3000 --http 8800
 */

"use strict";

const { Bridge } = require("../src/index");

const args = process.argv.slice(2);

const gatewayIdx = args.indexOf("--gateway");
const gatewayUrl = gatewayIdx >= 0 ? args[gatewayIdx + 1] : process.env.OPENCLAW_GATEWAY_URL;

if (!gatewayUrl) {
  console.error("Usage: openclaw-hive-bridge --gateway <url> [--stdio|--http <port>]");
  console.error("  or set OPENCLAW_GATEWAY_URL environment variable");
  process.exit(1);
}

const bridge = new Bridge({ gatewayUrl });

if (args.includes("--stdio")) {
  bridge.serveStdio();
} else {
  const httpIdx = args.indexOf("--http");
  const port = httpIdx >= 0 ? parseInt(args[httpIdx + 1], 10) : 8800;
  bridge.serveHttp(port);
}
