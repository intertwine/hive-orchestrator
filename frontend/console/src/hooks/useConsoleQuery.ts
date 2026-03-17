import { useEffect, useState } from "react";

interface QueryState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function useConsoleQuery<T>(
  key: string,
  fetcher: () => Promise<T>,
  refreshMs = 10000,
): QueryState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;

    async function load() {
      if (!alive) {
        return;
      }
      if (data === null) {
        setLoading(true);
      }
      try {
        const next = await fetcher();
        if (!alive) {
          return;
        }
        setData(next);
        setError(null);
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

    load();
    const intervalId = window.setInterval(load, refreshMs);
    return () => {
      alive = false;
      window.clearInterval(intervalId);
    };
  }, [key, refreshMs]);

  return { data, loading, error };
}
