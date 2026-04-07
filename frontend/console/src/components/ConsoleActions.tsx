import {
  type FormEvent,
  type PropsWithChildren,
  createContext,
  startTransition,
  useContext,
  useDeferredValue,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { preserveConsoleSearch } from "./ConsoleLink";
import {
  CONSOLE_PAGE_DEFINITIONS,
  type ConsoleNavGroup,
} from "../consolePages";

export type ConsoleActionTone = "primary" | "secondary" | "danger";

export interface ConsoleActionDescriptor {
  id: string;
  title: string;
  buttonLabel?: string;
  description: string;
  group: string;
  tone?: ConsoleActionTone;
  visible?: boolean;
  keywords?: string[];
  shortcut?: string;
  navGroup?: ConsoleNavGroup;
  href?: string;
  enabled: boolean;
  availabilityReason: string;
  availabilitySource: string;
  perform: () => Promise<void> | void;
}

interface ConsoleActionsContextValue {
  actions: ConsoleActionDescriptor[];
  navigationActions: ConsoleActionDescriptor[];
  primaryNavigationActions: ConsoleActionDescriptor[];
  secondaryNavigationActions: ConsoleActionDescriptor[];
  paletteOpen: boolean;
  openPalette: () => void;
  closePalette: () => void;
  setPageActions: (actions: ConsoleActionDescriptor[]) => void;
}

const ConsoleActionsContext = createContext<ConsoleActionsContextValue>({
  actions: [],
  navigationActions: [],
  primaryNavigationActions: [],
  secondaryNavigationActions: [],
  paletteOpen: false,
  openPalette: () => undefined,
  closePalette: () => undefined,
  setPageActions: () => undefined,
});

function buttonClassName(tone: ConsoleActionTone = "secondary"): string {
  if (tone === "primary") {
    return "primary-button";
  }
  if (tone === "danger") {
    return "danger-button";
  }
  return "secondary-button";
}

function CommandPalette({
  actions,
  open,
  onClose,
}: {
  actions: ConsoleActionDescriptor[];
  open: boolean;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!open) {
      setQuery("");
      return;
    }
    const timeoutId = window.setTimeout(() => {
      inputRef.current?.focus();
      inputRef.current?.select();
    }, 0);
    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [open]);

  const filteredActions = useMemo(() => {
    const normalizedQuery = deferredQuery.trim().toLowerCase();
    if (!normalizedQuery) {
      return actions;
    }
    return actions.filter((action) => {
      const haystack = [
        action.title,
        action.description,
        action.group,
        action.availabilityReason,
        action.availabilitySource,
        ...(action.keywords ?? []),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(normalizedQuery);
    });
  }, [actions, deferredQuery]);

  const groups = useMemo(() => {
    const grouped = new Map<string, ConsoleActionDescriptor[]>();
    for (const action of filteredActions) {
      const items = grouped.get(action.group) ?? [];
      items.push(action);
      grouped.set(action.group, items);
    }
    return Array.from(grouped.entries());
  }, [filteredActions]);

  async function handleAction(action: ConsoleActionDescriptor) {
    if (!action.enabled) {
      return;
    }
    onClose();
    await action.perform();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const firstEnabled = filteredActions.find((action) => action.enabled);
    if (!firstEnabled) {
      return;
    }
    await handleAction(firstEnabled);
  }

  if (!open) {
    return null;
  }

  return (
    <div className="command-palette" role="presentation">
      <button
        aria-label="Close command palette"
        className="command-palette__backdrop"
        onClick={onClose}
        type="button"
      />
      <div
        aria-label="Command palette"
        aria-modal="true"
        className="command-palette__dialog"
        role="dialog"
      >
        <form className="command-palette__search" onSubmit={handleSubmit}>
          <input
            aria-label="Search actions"
            placeholder="Search actions, pages, and run controls"
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button className="secondary-button" type="submit">
            Run first match
          </button>
        </form>
        <p className="command-palette__hint">
          Top operator actions, page controls, and deep links all share this same action model.
        </p>
        <div className="command-palette__results">
          {groups.length ? (
            groups.map(([group, groupActions]) => (
              <section className="command-palette__group" key={group}>
                <p className="command-palette__group-title">{group}</p>
                <div className="stack stack--compact">
                  {groupActions.map((action) => (
                    <button
                      className={`command-palette__item${action.enabled ? "" : " command-palette__item--disabled"}`}
                      disabled={!action.enabled}
                      key={action.id}
                      onClick={() => void handleAction(action)}
                      type="button"
                    >
                      <div className="command-palette__item-header">
                        <span>{action.title}</span>
                        {action.shortcut ? (
                          <span className="command-palette__shortcut">{action.shortcut}</span>
                        ) : null}
                      </div>
                      <p>{action.description}</p>
                      <p className="command-palette__meta">
                        {action.enabled ? "Available" : action.availabilityReason}
                        {" • "}
                        {action.availabilitySource}
                      </p>
                    </button>
                  ))}
                </div>
              </section>
            ))
          ) : (
            <p className="command-palette__empty">
              No matching actions. Try a run status, page name, or action verb like pause,
              reroute, approve, or settings.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export function ConsoleActionButton({
  action,
}: {
  action: ConsoleActionDescriptor;
}) {
  return (
    <button
      className={buttonClassName(action.tone)}
      disabled={!action.enabled}
      onClick={() => void action.perform()}
      title={action.availabilityReason}
      type="button"
    >
      {action.buttonLabel ?? action.title}
    </button>
  );
}

export function useConsoleActions() {
  return useContext(ConsoleActionsContext);
}

export function useRegisterConsoleActions(actions: ConsoleActionDescriptor[]) {
  const { setPageActions } = useConsoleActions();

  useEffect(() => {
    setPageActions(actions);
    return () => {
      setPageActions([]);
    };
  }, [actions, setPageActions]);
}

export function ConsoleActionsProvider({ children }: PropsWithChildren) {
  const location = useLocation();
  const navigate = useNavigate();
  const [pageActions, setPageActions] = useState<ConsoleActionDescriptor[]>([]);
  const [paletteOpen, setPaletteOpen] = useState(false);

  const navigationActions = useMemo(() => {
    return CONSOLE_PAGE_DEFINITIONS.map((page) => ({
      id: `navigate.${page.id}`,
      title: page.label,
      description: page.description,
      group: page.navGroup === "primary" ? "Navigate" : "Utilities",
      keywords: [page.id, page.label.toLowerCase()],
      navGroup: page.navGroup,
      href: page.path,
      enabled: true,
      availabilityReason: "Always available from the command center shell.",
      availabilitySource: "console route contract",
      perform: () => {
        startTransition(() => {
          navigate(preserveConsoleSearch(page.path, location.search));
        });
      },
    }));
  }, [location.search, navigate]);

  const actions = useMemo(
    () => [...navigationActions, ...pageActions],
    [navigationActions, pageActions],
  );

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((current) => !current);
        return;
      }
      if (event.key === "Escape") {
        setPaletteOpen(false);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  const value = useMemo(() => ({
    actions,
    navigationActions,
    primaryNavigationActions: navigationActions.filter((action) => action.navGroup === "primary"),
    secondaryNavigationActions: navigationActions.filter(
      (action) => action.navGroup === "secondary",
    ),
    paletteOpen,
    openPalette: () => setPaletteOpen(true),
    closePalette: () => setPaletteOpen(false),
    setPageActions,
  }), [actions, navigationActions, paletteOpen, setPageActions]);

  return (
    <ConsoleActionsContext.Provider value={value}>
      {children}
      <CommandPalette actions={actions} open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </ConsoleActionsContext.Provider>
  );
}
