import type { AttentionItem } from "./attention";

const DESKTOP_APP_SCHEME = "agent-hive:";
const DESKTOP_NAVIGATE_EVENT = "desktop:navigate";
const DESKTOP_NOTIFICATIONS_POLICY_EVENT = "desktop:notifications-policy";
const DESKTOP_OPEN_URL_EVENT = "desktop:open-url";

export interface DesktopBootstrapState {
  notificationsPaused: boolean;
  pendingUrls: string[];
}

export interface DesktopNotificationCandidate {
  body: string;
  href: string;
  id: number;
  title: string;
}

type RuntimeCleanup = () => void | Promise<void>;

export interface DesktopShellRuntime {
  bootstrap: () => Promise<DesktopBootstrapState>;
  ensureNotificationPermission: () => Promise<boolean>;
  focusApp: () => Promise<void>;
  onNavigate: (handler: (href: string) => void) => Promise<RuntimeCleanup>;
  onNotificationAction: (handler: (notificationId: string) => void) => Promise<RuntimeCleanup>;
  onNotificationsPolicy: (handler: (paused: boolean) => void) => Promise<RuntimeCleanup>;
  onOpenUrl: (handler: (urls: string[]) => void) => Promise<RuntimeCleanup>;
  sendNotification: (candidate: DesktopNotificationCandidate) => Promise<void>;
}

export interface DesktopNotificationSnapshot {
  candidates: DesktopNotificationCandidate[];
  initialized: boolean;
  knownKeys: Set<string>;
}

declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown;
  }
}

function appendSearch(pathname: string, searchParams: URLSearchParams) {
  const search = searchParams.toString();
  return search ? `${pathname}?${search}` : pathname;
}

function deepLinkPathname(rawPath: string) {
  if (!rawPath || rawPath === "/") {
    return "/home";
  }
  if (rawPath === "/console") {
    return "/home";
  }
  if (rawPath.startsWith("/console/")) {
    return rawPath.slice("/console".length);
  }
  return rawPath;
}

function notificationKey(item: AttentionItem) {
  return item.id || item.deepLink || `${item.title}:${item.occurredAt}`;
}

function notificationIdForKey(key: string) {
  let hash = 0;
  for (const character of key) {
    hash = ((hash << 5) - hash + character.charCodeAt(0)) | 0;
  }
  return Math.abs(hash) || 1;
}

function actionableNotificationCandidate(item: AttentionItem): DesktopNotificationCandidate | null {
  if (item.notificationTier !== "actionable" || !item.deepLink) {
    return null;
  }
  const key = notificationKey(item);
  return {
    id: notificationIdForKey(key),
    href: item.deepLink,
    title: item.title,
    body: item.summary || item.reason,
  };
}

export function collectDesktopNotificationSnapshot(
  items: AttentionItem[],
  knownKeys: ReadonlySet<string>,
  initialized: boolean,
): DesktopNotificationSnapshot {
  const nextKnownKeys = new Set<string>();
  const candidates: DesktopNotificationCandidate[] = [];

  for (const item of items) {
    const candidate = actionableNotificationCandidate(item);
    if (!candidate) {
      continue;
    }
    const key = notificationKey(item);
    nextKnownKeys.add(key);
    if (initialized && !knownKeys.has(key)) {
      candidates.push(candidate);
    }
  }

  return {
    candidates,
    initialized: true,
    knownKeys: nextKnownKeys,
  };
}

export function externalConsoleHrefFromUrl(rawUrl: string): string | null {
  let url: URL;
  try {
    url = new URL(rawUrl);
  } catch {
    return null;
  }

  if (![DESKTOP_APP_SCHEME, "http:", "https:"].includes(url.protocol)) {
    return null;
  }

  let pathname = url.pathname;
  if (url.protocol === DESKTOP_APP_SCHEME) {
    if (url.host && url.host !== "console") {
      pathname = pathname === "/" ? `/${url.host}` : `/${url.host}${pathname}`;
    }
  }
  pathname = deepLinkPathname(pathname);

  if (/^\/tasks?\/[^/]+$/.test(pathname)) {
    const taskId = decodeURIComponent(pathname.split("/").at(-1) ?? "").trim();
    if (!taskId) {
      return null;
    }
    const searchParams = new URLSearchParams(url.search);
    const nextParams = new URLSearchParams();
    nextParams.set("source", "task");
    nextParams.set("query", taskId);
    for (const [key, value] of searchParams.entries()) {
      nextParams.set(key, value);
    }
    return `/search?${nextParams.toString()}`;
  }

  const knownPrefixes = [
    "/home",
    "/runs",
    "/inbox",
    "/campaigns",
    "/projects",
    "/search",
    "/integrations",
    "/notifications",
    "/activity",
    "/settings",
  ];
  const knownPath = knownPrefixes.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
  if (!knownPath) {
    return null;
  }

  return appendSearch(pathname, url.searchParams);
}

export function isDesktopShellEnvironment() {
  return typeof window !== "undefined" && typeof window.__TAURI_INTERNALS__ !== "undefined";
}

export async function loadDesktopShellRuntime(): Promise<DesktopShellRuntime | null> {
  if (!isDesktopShellEnvironment()) {
    return null;
  }

  const [{ invoke }, { listen }, { getCurrentWindow }, notification] = await Promise.all([
    import("@tauri-apps/api/core"),
    import("@tauri-apps/api/event"),
    import("@tauri-apps/api/window"),
    import("@tauri-apps/plugin-notification"),
  ]);

  return {
    bootstrap() {
      return invoke<DesktopBootstrapState>("desktop_bootstrap");
    },

    async ensureNotificationPermission() {
      let permissionGranted = await notification.isPermissionGranted();
      if (!permissionGranted) {
        permissionGranted = (await notification.requestPermission()) === "granted";
      }
      return permissionGranted;
    },

    async focusApp() {
      const currentWindow = getCurrentWindow();
      await currentWindow.show();
      await currentWindow.setFocus();
    },

    async onNavigate(handler) {
      const unlisten = await listen<{ href?: unknown }>(
        DESKTOP_NAVIGATE_EVENT,
        (event) => {
          if (typeof event.payload?.href === "string") {
            handler(event.payload.href);
          }
        },
      );
      return () => unlisten();
    },

    async onNotificationAction(handler) {
      const listener = await notification.onAction((event) => {
        const notificationId = event?.id;
        if (typeof notificationId === "string" || typeof notificationId === "number") {
          handler(String(notificationId));
        }
      });
      return () => listener.unregister();
    },

    async onNotificationsPolicy(handler) {
      const unlisten = await listen<{ paused?: unknown }>(
        DESKTOP_NOTIFICATIONS_POLICY_EVENT,
        (event) => {
          handler(Boolean(event.payload?.paused));
        },
      );
      return () => unlisten();
    },

    async onOpenUrl(handler) {
      const unlisten = await listen<{ urls?: unknown }>(DESKTOP_OPEN_URL_EVENT, (event) => {
        if (!Array.isArray(event.payload?.urls)) {
          return;
        }
        const urls = event.payload.urls.filter(
          (value): value is string => typeof value === "string" && value.trim().length > 0,
        );
        if (urls.length) {
          handler(urls);
        }
      });
      return () => unlisten();
    },

    async sendNotification(candidate) {
      notification.sendNotification({
        body: candidate.body,
        id: candidate.id,
        title: candidate.title,
      });
    },
  };
}
