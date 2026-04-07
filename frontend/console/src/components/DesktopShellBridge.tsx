import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { normalizeAttentionItem } from "../attention";
import { createConsoleClient } from "../api/client";
import { useConsolePreferences } from "./ConsolePreferences";
import { preserveConsoleSearch } from "./ConsoleLink";
import { useConsoleConfig } from "./ConsoleLayout";
import {
  collectDesktopNotificationSnapshot,
  externalConsoleHrefFromUrl,
  loadDesktopShellRuntime,
  type DesktopShellRuntime,
} from "../desktopShell";
import { useConsoleQuery } from "../hooks/useConsoleQuery";

type RuntimeCleanup = () => void | Promise<void>;

export function DesktopShellBridge() {
  const { apiBase, workspacePath } = useConsoleConfig();
  const { preferences } = useConsolePreferences();
  const location = useLocation();
  const navigate = useNavigate();
  const [runtime, setRuntime] = useState<DesktopShellRuntime | null>(null);
  const [notificationsPaused, setNotificationsPaused] = useState(false);
  const notificationTargetsRef = useRef(new Map<string, string>());
  const notificationSnapshotRef = useRef({
    initialized: false,
    knownKeys: new Set<string>(),
  });
  const locationSearchRef = useRef(location.search);

  useEffect(() => {
    locationSearchRef.current = location.search;
  }, [location.search]);

  const client = useMemo(
    () => createConsoleClient(apiBase, workspacePath),
    [apiBase, workspacePath],
  );
  const notifications = useConsoleQuery(
    `desktop-notifications:${apiBase}:${workspacePath}:${runtime ? "desktop" : "browser"}`,
    () =>
      runtime
        ? client.getNotifications()
        : Promise.resolve({ ok: true, items: [], summary: {} }),
    15000,
  );

  const normalizedItems = useMemo(
    () =>
      Array.isArray(notifications.data?.items)
        ? notifications.data.items.map((item) => normalizeAttentionItem(item))
        : [],
    [notifications.data],
  );

  const navigateToConsoleHref = useCallback(
    (href: string, replace = false) => {
      navigate(preserveConsoleSearch(href, locationSearchRef.current), { replace });
    },
    [navigate],
  );

  useEffect(() => {
    notificationTargetsRef.current.clear();
    notificationSnapshotRef.current = {
      initialized: false,
      knownKeys: new Set<string>(),
    };
  }, [apiBase, workspacePath]);

  useEffect(() => {
    let alive = true;
    const cleanups: RuntimeCleanup[] = [];

    void (async () => {
      const nextRuntime = await loadDesktopShellRuntime();
      if (!alive || !nextRuntime) {
        return;
      }

      setRuntime(nextRuntime);
      const bootstrap = await nextRuntime.bootstrap();
      if (!alive) {
        return;
      }

      setNotificationsPaused(bootstrap.notificationsPaused);
      for (const rawUrl of bootstrap.pendingUrls) {
        const href = externalConsoleHrefFromUrl(rawUrl);
        if (href) {
          navigateToConsoleHref(href, true);
        }
      }

      cleanups.push(await nextRuntime.onNavigate((href) => navigateToConsoleHref(href)));
      cleanups.push(
        await nextRuntime.onNotificationsPolicy((paused) => setNotificationsPaused(paused)),
      );
      cleanups.push(
        await nextRuntime.onOpenUrl((urls) => {
          for (const rawUrl of urls) {
            const href = externalConsoleHrefFromUrl(rawUrl);
            if (href) {
              navigateToConsoleHref(href, true);
            }
          }
        }),
      );
      cleanups.push(
        await nextRuntime.onNotificationAction((notificationId) => {
          const href = notificationTargetsRef.current.get(notificationId);
          if (!href) {
            return;
          }
          void nextRuntime.focusApp().finally(() => {
            navigateToConsoleHref(href);
          });
        }),
      );
    })();

    return () => {
      alive = false;
      setRuntime(null);
      for (const cleanup of cleanups) {
        void cleanup();
      }
    };
  }, [navigateToConsoleHref]);

  useEffect(() => {
    if (!runtime) {
      return;
    }

    const snapshot = collectDesktopNotificationSnapshot(
      normalizedItems,
      notificationSnapshotRef.current.knownKeys,
      notificationSnapshotRef.current.initialized,
    );
    notificationSnapshotRef.current = {
      initialized: snapshot.initialized,
      knownKeys: snapshot.knownKeys,
    };

    if (!preferences.notifications.showActionable || notificationsPaused || !snapshot.candidates.length) {
      return;
    }

    let cancelled = false;

    void (async () => {
      const permissionGranted = await runtime.ensureNotificationPermission();
      if (!permissionGranted || cancelled) {
        return;
      }

      for (const candidate of snapshot.candidates) {
        notificationTargetsRef.current.set(String(candidate.id), candidate.href);
        await runtime.sendNotification(candidate);
        if (cancelled) {
          return;
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    normalizedItems,
    notificationsPaused,
    preferences.notifications.showActionable,
    runtime,
  ]);

  return null;
}
