import {
  type PropsWithChildren,
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export type ConsoleFreshnessTone = "idle" | "live" | "synced" | "stale";

interface ConsoleEventBusValue {
  connected: boolean;
  eventVersion: number;
  lastEventAt: number | null;
  lastHeartbeatAt: number | null;
  lastSyncAt: number | null;
  supportsStreaming: boolean;
  recordSync: (timestamp?: number) => void;
  requestRefresh: () => void;
}

const ConsoleEventBusContext = createContext<ConsoleEventBusValue>({
  connected: false,
  eventVersion: 0,
  lastEventAt: null,
  lastHeartbeatAt: null,
  lastSyncAt: null,
  supportsStreaming: false,
  recordSync: () => undefined,
  requestRefresh: () => undefined,
});

function buildEventStreamUrl(apiBase: string, workspacePath: string): URL {
  const root = apiBase.replace(/\/+$/, "") || window.location.origin;
  const url = new URL(`${root}/events/stream`);
  if (workspacePath.trim()) {
    url.searchParams.set("path", workspacePath.trim());
  }
  return url;
}

function formatFreshnessAge(ageMs: number): string {
  if (ageMs < 1_000) {
    return "just now";
  }
  if (ageMs < 60_000) {
    return `${Math.round(ageMs / 1_000)}s ago`;
  }
  return `${Math.round(ageMs / 60_000)}m ago`;
}

function parseTimestamp(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value !== "string" || !value.trim()) {
    return null;
  }
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function snapshotTimestamp(payload: unknown): number | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const record = payload as Record<string, unknown>;
  const explicitTimestamp = parseTimestamp(record.synced_at ?? record.emitted_at);
  if (explicitTimestamp !== null) {
    return explicitTimestamp;
  }
  const events = Array.isArray(record.events) ? record.events : [];
  const lastEvent = events.at(-1);
  if (!lastEvent || typeof lastEvent !== "object") {
    return null;
  }
  return parseTimestamp((lastEvent as Record<string, unknown>).ts);
}

function describeFreshness(
  connected: boolean,
  supportsStreaming: boolean,
  lastHeartbeatAt: number | null,
  lastSyncAt: number | null,
  now: number,
): { message: string; tone: ConsoleFreshnessTone } {
  if (lastSyncAt === null) {
    return {
      message: supportsStreaming ? "Waiting for first sync" : "Waiting for fallback sync",
      tone: "idle",
    };
  }

  const ageMs = Math.max(0, now - lastSyncAt);
  const heartbeatAgeMs = lastHeartbeatAt === null ? null : Math.max(0, now - lastHeartbeatAt);
  const streamHealthy = connected && heartbeatAgeMs !== null && heartbeatAgeMs <= 10_000;

  if (streamHealthy && ageMs <= 5_000) {
    return { message: "Live", tone: "live" };
  }
  if (streamHealthy) {
    return {
      message: `Live · synced ${formatFreshnessAge(ageMs)}`,
      tone: "synced",
    };
  }
  if (ageMs <= 15_000) {
    return {
      message: supportsStreaming
        ? `Stream offline · synced ${formatFreshnessAge(ageMs)}`
        : `Polling fallback · synced ${formatFreshnessAge(ageMs)}`,
      tone: "synced",
    };
  }
  return {
    message: supportsStreaming
      ? `Stream offline · stale ${formatFreshnessAge(ageMs)}`
      : `Polling fallback · stale ${formatFreshnessAge(ageMs)}`,
    tone: "stale",
  };
}

export function useConsoleEventBus() {
  return useContext(ConsoleEventBusContext);
}

export function ConsoleEventBusProvider({
  apiBase,
  workspacePath,
  children,
}: PropsWithChildren<{ apiBase: string; workspacePath: string }>) {
  const [connected, setConnected] = useState(false);
  const [supportsStreaming, setSupportsStreaming] = useState(
    () => typeof window.EventSource === "function",
  );
  const [eventVersion, setEventVersion] = useState(0);
  const [lastEventAt, setLastEventAt] = useState<number | null>(null);
  const [lastHeartbeatAt, setLastHeartbeatAt] = useState<number | null>(null);
  const [lastSyncAt, setLastSyncAt] = useState<number | null>(null);

  const recordSync = useCallback((timestamp = Date.now()) => {
    setLastSyncAt((current) => {
      if (current !== null && current > timestamp) {
        return current;
      }
      return timestamp;
    });
  }, []);

  const requestRefresh = useCallback(() => {
    setEventVersion((value) => value + 1);
  }, []);

  useEffect(() => {
    if (typeof window.EventSource !== "function") {
      setSupportsStreaming(false);
      setConnected(false);
      setLastHeartbeatAt(null);
      return;
    }

    setSupportsStreaming(true);
    const source = new window.EventSource(
      buildEventStreamUrl(apiBase, workspacePath).toString(),
    );

    source.onopen = () => {
      const timestamp = Date.now();
      setConnected(true);
      setLastHeartbeatAt(timestamp);
    };
    source.onerror = () => {
      setConnected(false);
    };

    const handleHeartbeat = (event: MessageEvent) => {
      const payload = JSON.parse(event.data ?? "{}") as Record<string, unknown>;
      const timestamp = snapshotTimestamp(payload) ?? Date.now();
      setConnected(true);
      setLastHeartbeatAt(timestamp);
    };

    const handleSnapshot = (event: MessageEvent) => {
      const payload = JSON.parse(event.data ?? "{}") as Record<string, unknown>;
      const timestamp = snapshotTimestamp(payload) ?? Date.now();
      setConnected(true);
      setLastEventAt(timestamp);
      setLastHeartbeatAt(timestamp);
      setEventVersion((value) => value + 1);
    };

    source.addEventListener("heartbeat", handleHeartbeat);
    source.addEventListener("snapshot", handleSnapshot);

    return () => {
      source.removeEventListener("heartbeat", handleHeartbeat);
      source.removeEventListener("snapshot", handleSnapshot);
      source.close();
    };
  }, [apiBase, workspacePath]);

  const value = useMemo<ConsoleEventBusValue>(() => {
    return {
      connected,
      eventVersion,
      lastEventAt,
      lastHeartbeatAt,
      lastSyncAt,
      supportsStreaming,
      recordSync,
      requestRefresh,
    };
  }, [
    connected,
    eventVersion,
    lastEventAt,
    lastHeartbeatAt,
    lastSyncAt,
    supportsStreaming,
    recordSync,
    requestRefresh,
  ]);

  return (
    <ConsoleEventBusContext.Provider value={value}>
      {children}
    </ConsoleEventBusContext.Provider>
  );
}

export function FreshnessIndicator() {
  const { connected, lastHeartbeatAt, lastSyncAt, supportsStreaming } = useConsoleEventBus();
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timerId = window.setInterval(() => {
      setNow(Date.now());
    }, 1_000);
    return () => {
      window.clearInterval(timerId);
    };
  }, []);

  const freshness = useMemo(
    () => describeFreshness(connected, supportsStreaming, lastHeartbeatAt, lastSyncAt, now),
    [connected, lastHeartbeatAt, lastSyncAt, now, supportsStreaming],
  );

  return (
    <span className={`hero-highlight freshness-pill freshness-pill--${freshness.tone}`}>
      {freshness.message}
    </span>
  );
}
