/**
 * openclaw-hive-bridge core module.
 *
 * Bridges the OpenClaw Gateway API to Agent Hive via NDJSON protocol.
 * Each stdin line is a JSON request; each stdout line is a JSON response.
 *
 * Gateway API integration points use the official OpenClaw CLI/gateway
 * surfaces. The stdio protocol is stable; HTTP mode remains deferred.
 */

"use strict";

const { execFileSync } = require("child_process");

class Bridge {
  constructor({ gatewayUrl, gatewayToken, gatewayPassword, cliBinary } = {}) {
    this.gatewayUrl = gatewayUrl;
    this.gatewayToken = gatewayToken || process.env.OPENCLAW_GATEWAY_TOKEN || "";
    this.gatewayPassword =
      gatewayPassword || process.env.OPENCLAW_GATEWAY_PASSWORD || "";
    this.cliBinary = cliBinary || process.env.OPENCLAW_CLI || "openclaw";
    this.sessions = new Map();
  }

  _authArgs() {
    const args = [];
    if (this.gatewayUrl) {
      args.push("--url", this.gatewayUrl);
    }
    if (this.gatewayToken) {
      args.push("--token", this.gatewayToken);
    } else if (this.gatewayPassword) {
      args.push("--password", this.gatewayPassword);
    }
    return args;
  }

  _parseJsonOutput(stdout) {
    const text = String(stdout || "").trim();
    if (!text) {
      return null;
    }

    try {
      return JSON.parse(text);
    } catch (_) {
      // Some gateway commands can emit JSONL. Keep the last parseable line.
      const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
      for (let idx = lines.length - 1; idx >= 0; idx -= 1) {
        try {
          return JSON.parse(lines[idx]);
        } catch (_) {
          continue;
        }
      }
    }
    return null;
  }

  _cliCall(command, extraArgs = []) {
    const argv = [command, ...extraArgs, "--json", ...this._authArgs()];
    try {
      const stdout = execFileSync(this.cliBinary, argv, {
        encoding: "utf8",
        stdio: ["ignore", "pipe", "pipe"],
      });
      return { ok: true, data: this._parseJsonOutput(stdout), raw: stdout };
    } catch (err) {
      return {
        ok: false,
        error: err.stderr ? String(err.stderr).trim() || err.message : err.message,
      };
    }
  }

  _invokeGateway(method, params = {}) {
    const result = this._cliCall("gateway", [
      "call",
      method,
      "--params",
      JSON.stringify(params),
    ]);
    if (!result.ok) {
      return { ok: false, error: result.error };
    }
    const data = result.data;
    if (!data) {
      return { ok: false, error: "No JSON response from OpenClaw gateway." };
    }
    if (data.ok === false) {
      const gatewayError =
        typeof data.error === "string"
          ? data.error
          : data.error?.message || "OpenClaw gateway call failed.";
      return { ok: false, error: gatewayError, data };
    }
    return { ok: true, data: data.result ?? data.payload ?? data };
  }

  probeGateway() {
    if (!this.gatewayUrl) {
      return { gateway_reachable: false, sessions_accessible: false };
    }

    const health = this._cliCall("health");
    const sessions = this._invokeGateway("sessions.list", {});
    const gatewayReachable = health.ok || sessions.ok;
    const sessionRows = sessions.ok ? this._coerceSessionItems(sessions.data) : [];
    const rowCount = Array.isArray(sessionRows) ? sessionRows.length : 0;

    return {
      gateway_reachable: gatewayReachable,
      gateway_url: this.gatewayUrl,
      connection_mode: this._connectionMode(),
      connection_scope: this._connectionMode(),
      gateway_version: this._extractVersion(health.data),
      sessions_accessible: sessions.ok,
      session_count: rowCount,
      attach_supported: sessions.ok,
      steering_supported: sessions.ok,
    };
  }

  _coerceSessionItems(data) {
    if (Array.isArray(data)) {
      return data;
    }
    if (data && Array.isArray(data.items)) {
      return data.items;
    }
    return [];
  }

  _coerceTranscriptItems(data) {
    if (Array.isArray(data)) {
      return data;
    }
    if (data && Array.isArray(data.events)) {
      return data.events;
    }
    if (data && Array.isArray(data.items)) {
      return data.items;
    }
    if (data && Array.isArray(data.history)) {
      return data.history;
    }
    return [];
  }

  _parsePositiveInt(value, fallback) {
    const parsed = Number.parseInt(String(value ?? ""), 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
  }

  _streamConfig(overrides = {}) {
    return {
      follow: overrides.follow !== false,
      pollIntervalMs: this._parsePositiveInt(
        overrides.pollIntervalMs ?? process.env.OPENCLAW_HIVE_STREAM_POLL_MS,
        250
      ),
      idleTimeoutMs: this._parsePositiveInt(
        overrides.idleTimeoutMs ?? process.env.OPENCLAW_HIVE_STREAM_IDLE_MS,
        1500
      ),
      limit: this._parsePositiveInt(
        overrides.limit ?? process.env.OPENCLAW_HIVE_STREAM_LIMIT,
        200
      ),
    };
  }

  _sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  _hashText(value) {
    let hash = 0;
    for (let idx = 0; idx < value.length; idx += 1) {
      hash = (hash * 31 + value.charCodeAt(idx)) >>> 0;
    }
    return hash.toString(16);
  }

  _eventFingerprint(event) {
    return String(event.raw_ref || "");
  }

  _extractVersion(payload) {
    if (!payload || typeof payload !== "object") {
      return "unknown";
    }
    return (
      payload.version ||
      payload.gatewayVersion ||
      payload.buildVersion ||
      payload.appVersion ||
      "unknown"
    );
  }

  _connectionMode() {
    if (!this.gatewayUrl) {
      return "unknown";
    }
    try {
      const host = new URL(this.gatewayUrl).hostname;
      return ["localhost", "127.0.0.1", "::1"].includes(host)
        ? "local"
        : "remote";
    } catch (_) {
      return "unknown";
    }
  }

  listSessions() {
    const response = this._invokeGateway("sessions.list", {});
    if (!response.ok) {
      return { ok: false, error: response.error };
    }
    const items = this._coerceSessionItems(response.data);
    return Array.isArray(items) ? { ok: true, items } : { ok: true, items: [] };
  }

  attachSession(sessionKey, { projectId } = {}) {
    if (!this.gatewayUrl) {
      return { ok: false, error: "OPENCLAW_GATEWAY_URL is not configured." };
    }
    const sessions = this.listSessions();
    if (!sessions.ok) {
      return sessions;
    }
    const matched = sessions.items.find(
      (item) =>
        item.sessionKey === sessionKey ||
        item.key === sessionKey ||
        item.sessionId === sessionKey
    );
    if (!matched) {
      return {
        ok: false,
        error: `Session not found in gateway: ${sessionKey}`,
      };
    }
    this.sessions.set(sessionKey, {
      projectId,
      attachedAt: new Date().toISOString(),
      gatewaySession: matched,
    });
    return {
      ok: true,
      session_key: sessionKey,
      status: "attached",
      gateway_session: matched,
    };
  }

  async streamEvents(sessionKey, options = {}, onEvent = null) {
    const { follow, pollIntervalMs, idleTimeoutMs, limit } = this._streamConfig(options);
    const afterRawRef = String(options.afterRawRef || "");
    const events = [];
    const seen = new Set();
    let emittedCount = 0;
    let idleDeadline = Date.now() + idleTimeoutMs;
    let cursorSatisfied = !afterRawRef;
    let hasPolled = false;

    while (true) {
      if (hasPolled && Date.now() >= idleDeadline) {
        return follow
          ? { ok: true, event_count: emittedCount }
          : { ok: true, events, event_count: emittedCount };
      }
      hasPolled = true;
      const response = this._invokeGateway("sessions.history", {
        sessionKey,
        limit,
        includeTools: false,
      });
      if (!response.ok) {
        return { ok: false, error: response.error };
      }

      const transcript = this._coerceTranscriptItems(response.data);
      let newCount = 0;
      for (const [idx, message] of transcript.entries()) {
        const event = this._normalizeMessage(sessionKey, message, idx);
        const fingerprint = this._eventFingerprint(event);
        if (!cursorSatisfied) {
          seen.add(fingerprint);
          if (event.raw_ref === afterRawRef) {
            cursorSatisfied = true;
          }
          continue;
        }
        if (seen.has(fingerprint)) {
          continue;
        }
        seen.add(fingerprint);
        emittedCount += 1;
        newCount += 1;
        if (onEvent) {
          onEvent(event);
        } else {
          events.push(event);
        }
      }
      if (!cursorSatisfied && transcript.length > 0) {
        cursorSatisfied = true;
      }

      if (!follow) {
        return { ok: true, events, event_count: emittedCount };
      }
      if (newCount > 0) {
        idleDeadline = Date.now() + idleTimeoutMs;
      }
      await this._sleep(pollIntervalMs);
    }
  }

  _normalizeMessage(sessionKey, message, seq) {
    const kind =
      message.kind ||
      message.type ||
      (message.role === "assistant" ? "assistant_delta" : "session_event");
    const payload =
      message.payload ||
      message.content ||
      (typeof message.text === "string" ? { text: message.text } : {});
    const ts = message.ts || message.createdAt || new Date().toISOString();
    const rawRef =
      message.raw_ref ||
      message.id ||
      message.messageId ||
      `synthetic:${sessionKey}:${kind}:${ts}:${this._hashText(JSON.stringify(payload || {}))}`;
    return {
      seq,
      kind,
      ts,
      harness: "openclaw",
      adapter_family: "delegate_gateway",
      native_session_ref: sessionKey,
      raw_ref: rawRef,
      payload,
    };
  }

  detachSession(sessionKey) {
    this.sessions.delete(sessionKey);
    return { ok: true, session_key: sessionKey, status: "detached" };
  }

  sendSteer(sessionKey, action, payload) {
    const message = JSON.stringify({
      action,
      payload,
    });
    const response = this._invokeGateway("chat.send", {
      sessionKey,
      message,
      idempotencyKey: `openclaw-hive-bridge:${sessionKey}:steer:${action}:${Date.now()}`,
    });
    if (!response.ok) {
      return response;
    }
    return { ok: true, session_key: sessionKey, action, result: response.data };
  }

  publishNote(sessionKey, note) {
    const response = this._invokeGateway("chat.inject", {
      sessionKey,
      message: note,
    });
    if (!response.ok) {
      return response;
    }
    return { ok: true, session_key: sessionKey, note, result: response.data };
  }

  serveStdio() {
    const readline = require("readline");
    const rl = readline.createInterface({ input: process.stdin });
    let queue = Promise.resolve();

    rl.on("line", (line) => {
      queue = queue.then(() => this._processLine(line));
    });

    // Exit cleanly when stdin closes (single-request mode from Python subprocess).
    rl.on("close", () => {
      queue.finally(() => process.exit(0));
    });
  }

  async _processLine(line) {
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
  }

  serveHttp(port) {
    console.log(`openclaw-hive-bridge listening on http://127.0.0.1:${port}`);
    console.log(
      "HTTP mode remains deferred for v2.4; use --stdio for gateway-backed bridge calls."
    );
  }

  async _handleMessage(msg) {
    switch (msg.type) {
      case "probe": {
        const status = await this.probeGateway();
        return { type: "probe_ok", ...status };
      }
      case "list_sessions":
        {
          const result = this.listSessions();
          return result.ok
            ? { type: "sessions", items: result.items }
            : { type: "error", message: result.error };
        }
      case "attach":
        {
          const result = this.attachSession(msg.native_session_ref, msg);
          return result.ok
            ? { type: "attach_ok", ...result }
            : { type: "error", message: result.error };
        }
      case "stream_events": {
        const result = await this.streamEvents(
          msg.native_session_ref,
          {
            follow: msg.follow,
            pollIntervalMs: msg.poll_interval_ms,
            idleTimeoutMs: msg.idle_timeout_ms,
            afterRawRef: msg.after_raw_ref,
            limit: msg.limit,
          },
          (event) => {
            process.stdout.write(JSON.stringify({ type: "stream_event", event }) + "\n");
          }
        );
        if (!result.ok) {
          return { type: "error", message: result.error };
        }
        process.stdout.write(
          JSON.stringify({
            type: "stream_events_end",
            event_count: result.event_count || 0,
          }) + "\n"
        );
        return null;
      }
      case "detach":
        return {
          type: "detach_ok",
          ...(this.detachSession(msg.native_session_ref)),
        };
      case "steer":
        {
          const result = this.sendSteer(msg.session_key, msg.action, msg.payload);
          return result.ok
            ? { type: "steer_ok", ...result }
            : { type: "error", message: result.error };
        }
      case "note":
        {
          const result = this.publishNote(msg.session_key, msg.note);
          return result.ok
            ? { type: "note_ok", ...result }
            : { type: "error", message: result.error };
        }
      default:
        return { type: "error", message: `Unknown message type: ${msg.type}` };
    }
  }
}

module.exports = { Bridge };
