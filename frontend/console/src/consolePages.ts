export const CONSOLE_PAGE_IDS = [
  "home",
  "runs",
  "inbox",
  "campaigns",
  "projects",
  "search",
  "integrations",
  "notifications",
  "activity",
  "settings",
] as const;

export type ConsolePage = (typeof CONSOLE_PAGE_IDS)[number];
export type ConsoleNavGroup = "primary" | "secondary";

export interface ConsolePageDefinition {
  id: ConsolePage;
  label: string;
  path: string;
  navGroup: ConsoleNavGroup;
  description: string;
}

export const CONSOLE_PAGE_PATHS: Record<ConsolePage, string> = {
  home: "/home",
  runs: "/runs",
  inbox: "/inbox",
  campaigns: "/campaigns",
  projects: "/projects",
  search: "/search",
  integrations: "/integrations",
  notifications: "/notifications",
  activity: "/activity",
  settings: "/settings",
};

export const CONSOLE_PAGE_LABELS: Record<ConsolePage, string> = {
  home: "Home",
  runs: "Runs",
  inbox: "Inbox",
  campaigns: "Campaigns",
  projects: "Projects",
  search: "Search",
  integrations: "Integrations",
  notifications: "Notifications",
  activity: "Activity",
  settings: "Settings",
};

export const CONSOLE_PAGE_DESCRIPTIONS: Record<ConsolePage, string> = {
  home: "Attention-first portfolio view for exceptions, live work, and the next action.",
  runs: "Shared runs board for active work, review queues, and saved operator views.",
  inbox: "Operator inbox for approvals, escalations, and exception handling.",
  campaigns: "Portfolio loops, campaign health, and recent candidate decisions.",
  projects: "Project summaries, program doctor status, and compiled startup context.",
  search: "Unified search across Hive records with explainable match reasons.",
  integrations: "Capability truth for legacy drivers and v2.4 adapter integrations.",
  notifications: "Persistent operator notifications and inbox-worthy signals.",
  activity: "Compact feed of recent accepts, events, and command-center movement.",
  settings: "Operator-local connection, theme, density, and default-page preferences.",
};

export const CONSOLE_PAGE_DEFINITIONS: readonly ConsolePageDefinition[] = CONSOLE_PAGE_IDS.map(
  (id) => ({
    id,
    label: CONSOLE_PAGE_LABELS[id],
    path: CONSOLE_PAGE_PATHS[id],
    navGroup:
      id === "integrations" || id === "notifications" || id === "activity" || id === "settings"
        ? "secondary"
        : "primary",
    description: CONSOLE_PAGE_DESCRIPTIONS[id],
  }),
);

export const PRIMARY_CONSOLE_PAGES = CONSOLE_PAGE_DEFINITIONS.filter(
  (page) => page.navGroup === "primary",
);
export const SECONDARY_CONSOLE_PAGES = CONSOLE_PAGE_DEFINITIONS.filter(
  (page) => page.navGroup === "secondary",
);

export function consolePathForPage(page: ConsolePage): string {
  return CONSOLE_PAGE_PATHS[page];
}

export function describeConsolePath(pathname: string): ConsolePageDefinition {
  const canonicalPath = pathname === "/" ? CONSOLE_PAGE_PATHS.home : pathname;
  const matched =
    CONSOLE_PAGE_DEFINITIONS.find(
      (page) => canonicalPath === page.path || canonicalPath.startsWith(`${page.path}/`),
    ) ?? CONSOLE_PAGE_DEFINITIONS[0];
  return matched;
}
