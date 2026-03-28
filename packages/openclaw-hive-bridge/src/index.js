/**
 * openclaw-hive-bridge core module.
 *
 * Bridges the OpenClaw Gateway API to Agent Hive via NDJSON protocol.
 * Each stdin line is a JSON request; each stdout line is a JSON response.
 *
 * Gateway API integration points are marked with TODO — the protocol
 * and message shapes are stable, the HTTP calls to the real Gateway
 * are the remaining wire.
 */

"use strict";

class Bridge {
  constructor({ gatewayUrl }) {
    this.gatewayUrl = gatewayUrl;
    this.sessions = new Map();
  }

  async probeGateway() {
    if (!this.gatewayUrl) {
      return { gateway_reachable: false, sessions_accessible: false };
    }
    // TODO: HTTP GET to gatewayUrl/health or equivalent
    // For now, report the URL is configured but not verified.
    return {
      gateway_reachable: false,
      gateway_url: this.gatewayUrl,
      sessions_accessible: false,
      version: "0.1.0",
      attach_supported: true,
      steering_supported: true,
    };
  }

  async listSessions() {
    // TODO: GET gatewayUrl/api/sessions
    return [];
  }

  async attachSession(sessionKey, { projectId } = {}) {
    // TODO: POST gatewayUrl/api/sessions/:key/attach
    // Stateless: the Python client owns session state via SessionHandle
    // and delegate persistence. The bridge just validates the request
    // against the Gateway.
    if (!this.gatewayUrl) {
      return { ok: false, error: "OPENCLAW_GATEWAY_URL is not configured." };
    }
    this.sessions.set(sessionKey, {
      projectId,
      attachedAt: new Date().toISOString(),
    });
    return { ok: true, session_key: sessionKey, status: "attached" };
  }

  async streamEvents(sessionKey) {
    // TODO: GET gatewayUrl/api/sessions/:key/history (streaming)
    // Stateless: each call fetches from the Gateway directly using the
    // session key. Does not depend on in-memory attach state.
    if (!this.gatewayUrl) {
      return [];
    }
    // Until real Gateway HTTP is wired, return a minimal session_start
    // so the protocol round-trip is testable.
    return [
      { kind: "session_start", ts: new Date().toISOString(), payload: {} },
    ];
  }

  async detachSession(sessionKey) {
    this.sessions.delete(sessionKey);
    return { ok: true, session_key: sessionKey, status: "detached" };
  }

  async sendSteer(sessionKey, action, payload) {
    // TODO: POST gatewayUrl/api/sessions/:key/steer
    return { ok: true, session_key: sessionKey, action };
  }

  async publishNote(sessionKey, note) {
    // TODO: POST gatewayUrl/api/sessions/:key/notes
    return { ok: true, session_key: sessionKey, note };
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
        process.stdout.write(
          JSON.stringify({ type: "error", message: err.message }) + "\n"
        );
      }
    });

    // Exit cleanly when stdin closes (single-request mode from Python subprocess).
    rl.on("close", () => process.exit(0));
  }

  serveHttp(port) {
    // TODO: HTTP server for remote bridge access
    console.log(`openclaw-hive-bridge listening on http://127.0.0.1:${port}`);
    console.log("HTTP mode is a v2.4 scaffold — use --stdio for local integration.");
  }

  async _handleMessage(msg) {
    switch (msg.type) {
      case "probe": {
        const status = await this.probeGateway();
        return { type: "probe_ok", ...status };
      }
      case "list_sessions":
        return { type: "sessions", items: await this.listSessions() };
      case "attach":
        return {
          type: "attach_ok",
          ...(await this.attachSession(msg.native_session_ref, msg)),
        };
      case "stream_events": {
        const events = await this.streamEvents(msg.native_session_ref);
        return { type: "stream_events_ok", events };
      }
      case "detach":
        return {
          type: "detach_ok",
          ...(await this.detachSession(msg.native_session_ref)),
        };
      case "steer":
        return {
          type: "steer_ok",
          ...(await this.sendSteer(
            msg.session_key,
            msg.action,
            msg.payload
          )),
        };
      case "note":
        return {
          type: "note_ok",
          ...(await this.publishNote(msg.session_key, msg.note)),
        };
      default:
        return { type: "error", message: `Unknown message type: ${msg.type}` };
    }
  }
}

module.exports = { Bridge };
