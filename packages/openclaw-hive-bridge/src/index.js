/**
 * openclaw-hive-bridge core module.
 *
 * This is a v2.4 scaffold. The full implementation will:
 * - Authenticate to the OpenClaw Gateway
 * - List active sessions and delegates
 * - Map sessionKey to Hive delegate session ID
 * - Subscribe to session history / live transcript
 * - Normalize events into Hive Link format
 * - Accept steering and notes from Hive and forward to Gateway
 */

"use strict";

class Bridge {
  constructor({ gatewayUrl }) {
    this.gatewayUrl = gatewayUrl;
    this.sessions = new Map();
  }

  async listSessions() {
    // TODO: fetch from Gateway API
    return [];
  }

  async attachSession(sessionKey, { projectId } = {}) {
    // TODO: subscribe to Gateway session history stream
    this.sessions.set(sessionKey, { projectId, attachedAt: new Date().toISOString() });
    return { ok: true, sessionKey, status: "attached" };
  }

  async detachSession(sessionKey) {
    this.sessions.delete(sessionKey);
    return { ok: true, sessionKey, status: "detached" };
  }

  async sendSteer(sessionKey, action, payload) {
    // TODO: forward to Gateway steering endpoint
    return { ok: true, sessionKey, action };
  }

  async publishNote(sessionKey, note) {
    // TODO: forward to Gateway notes endpoint
    return { ok: true, sessionKey, note };
  }

  serveStdio() {
    const readline = require("readline");
    const rl = readline.createInterface({ input: process.stdin });

    rl.on("line", async (line) => {
      try {
        const msg = JSON.parse(line);
        const response = await this._handleMessage(msg);
        if (response) {
          process.stdout.write(JSON.stringify(response) + "\n");
        }
      } catch (err) {
        process.stdout.write(JSON.stringify({ type: "error", message: err.message }) + "\n");
      }
    });
  }

  serveHttp(port) {
    // TODO: HTTP server for remote bridge access
    console.log(`openclaw-hive-bridge listening on http://127.0.0.1:${port}`);
    console.log("HTTP mode is a v2.4 scaffold — use --stdio for local integration.");
  }

  async _handleMessage(msg) {
    switch (msg.type) {
      case "list_sessions":
        return { type: "sessions", items: await this.listSessions() };
      case "attach":
        return { type: "attach_ok", ...(await this.attachSession(msg.native_session_ref, msg)) };
      case "detach":
        return { type: "detach_ok", ...(await this.detachSession(msg.native_session_ref)) };
      case "steer":
        return { type: "steer_ok", ...(await this.sendSteer(msg.session_key, msg.action, msg.payload)) };
      case "note":
        return { type: "note_ok", ...(await this.publishNote(msg.session_key, msg.note)) };
      default:
        return { type: "error", message: `Unknown message type: ${msg.type}` };
    }
  }
}

module.exports = { Bridge };
