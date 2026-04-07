import { useEffect, useRef, useState } from "react";

import { useConsoleEventBus } from "../components/ConsoleEventBus";

interface QueryState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  lastUpdated: number | null;
}

export function useConsoleQuery<T>(
  key: string,
  fetcher: () => Promise<T>,
  refreshMs = 10000,
): QueryState<T> {
  const { connected, eventVersion, recordSync, supportsStreaming } = useConsoleEventBus();
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);
  const fetcherRef = useRef(fetcher);
  const hasLoadedRef = useRef(false);

  useEffect(() => {
    fetcherRef.current = fetcher;
  }, [fetcher]);

  useEffect(() => {
    let alive = true;

    async function load() {
      if (!alive) {
        return;
      }
      if (!hasLoadedRef.current) {
        setLoading(true);
      }
      try {
        const next = await fetcherRef.current();
        if (!alive) {
          return;
        }
        const timestamp = Date.now();
        setData(next);
        setError(null);
        setLastUpdated(timestamp);
        hasLoadedRef.current = true;
        recordSync(timestamp);
      } catch (caught) {
        if (!alive) {
          return;
        }
        setError(caught instanceof Error ? caught.message : "Unknown console error");
      } finally {
        if (alive) {
          setLoading(false);
        }
      }
    }

    void load();
    if (refreshMs <= 0 || (supportsStreaming && connected)) {
      return () => {
        alive = false;
      };
    }

    const intervalId = window.setInterval(() => {
      void load();
    }, refreshMs);
    return () => {
      alive = false;
      window.clearInterval(intervalId);
    };
  }, [connected, eventVersion, key, recordSync, refreshMs, supportsStreaming]);

  return { data, loading, error, lastUpdated };
}
