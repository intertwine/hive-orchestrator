import { act, render, screen } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ConsoleEventBusProvider,
  FreshnessIndicator,
  useConsoleEventBus,
} from "../components/ConsoleEventBus";

class MockEventSource {
  static instances: MockEventSource[] = [];

  onerror: ((event: Event) => void) | null = null;
  onopen: ((event: Event) => void) | null = null;
  private readonly listeners = new Map<string, Set<(event: MessageEvent) => void>>();

  constructor(_url: string | URL) {
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: (event: MessageEvent) => void) {
    const listeners = this.listeners.get(type) ?? new Set<(event: MessageEvent) => void>();
    listeners.add(listener);
    this.listeners.set(type, listeners);
  }

  removeEventListener(type: string, listener: (event: MessageEvent) => void) {
    this.listeners.get(type)?.delete(listener);
  }

  close() {
    return undefined;
  }

  emit(type: string, payload: unknown) {
    const event = new MessageEvent(type, {
      data: JSON.stringify(payload),
    });
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event);
    }
  }

  emitRaw(type: string, data: string) {
    const event = new MessageEvent(type, { data });
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event);
    }
  }

  fail() {
    this.onerror?.(new Event("error"));
  }

  open() {
    this.onopen?.(new Event("open"));
  }

  static reset() {
    MockEventSource.instances = [];
  }
}

function SyncProbe() {
  const { recordSync } = useConsoleEventBus();

  useEffect(() => {
    recordSync();
  }, [recordSync]);

  return <FreshnessIndicator />;
}

describe("ConsoleEventBus", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-04-07T00:45:00Z"));
    MockEventSource.reset();
    vi.stubGlobal("EventSource", MockEventSource as unknown as typeof EventSource);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("reports offline, live, and stale freshness truthfully", async () => {
    render(
      <ConsoleEventBusProvider
        apiBase="http://127.0.0.1:8787"
        workspacePath="/tmp/hive-demo"
      >
        <SyncProbe />
      </ConsoleEventBusProvider>,
    );

    await act(async () => {});
    expect(screen.getByText("Stream offline · synced just now")).toBeInTheDocument();
    expect(MockEventSource.instances).toHaveLength(1);

    act(() => {
      MockEventSource.instances[0]?.open();
      MockEventSource.instances[0]?.emit("heartbeat", {
        synced_at: "2026-04-07T00:45:00Z",
        last_event_id: "evt_1",
      });
    });
    expect(screen.getByText("Live")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(16_000);
      MockEventSource.instances[0]?.fail();
    });
    expect(screen.getByText("Stream offline · stale 16s ago")).toBeInTheDocument();
  });

  it("ignores malformed stream frames", async () => {
    render(
      <ConsoleEventBusProvider
        apiBase="http://127.0.0.1:8787"
        workspacePath="/tmp/hive-demo"
      >
        <SyncProbe />
      </ConsoleEventBusProvider>,
    );

    await act(async () => {});

    act(() => {
      MockEventSource.instances[0]?.emitRaw("heartbeat", "{not-json");
      MockEventSource.instances[0]?.emitRaw("snapshot", "{still-bad");
    });

    expect(screen.getByText("Stream offline · synced just now")).toBeInTheDocument();
  });
});
