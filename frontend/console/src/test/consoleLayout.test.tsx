import { useMemo } from "react";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ConsoleActionButton,
  type ConsoleActionDescriptor,
  useRegisterConsoleActions,
} from "../components/ConsoleActions";
import { ConsoleLayout } from "../components/ConsoleLayout";
import { CONSOLE_PREFERENCES_KEY } from "../preferences";

function DeepLinkOverrideButton() {
  const navigate = useNavigate();

  return (
    <button
      onClick={() =>
        navigate("/settings?apiBase=http://127.0.0.1:7777&workspace=/tmp/external-workspace")
      }
      type="button"
    >
      Open external deep link
    </button>
  );
}

function PaletteActionRegistrar({ onAction }: { onAction: () => void }) {
  const actions = useMemo<ConsoleActionDescriptor[]>(
    () => [
      {
        id: "review.approve-demo",
        title: "Approve demo approval",
        description: "Approve the demo review request from the shared palette.",
        group: "Page actions",
        enabled: true,
        availabilityReason: "Available because the demo request is still pending review.",
        availabilitySource: "test harness",
        keywords: ["approve", "demo"],
        perform: onAction,
      },
      {
        id: "run.pause-demo",
        title: "Pause demo run",
        description: "Pause the demo run.",
        group: "Page actions",
        enabled: false,
        availabilityReason: "Unavailable because the demo run is already paused.",
        availabilitySource: "test harness",
        keywords: ["pause", "demo"],
        perform: () => undefined,
      },
    ],
    [onAction],
  );

  useRegisterConsoleActions(actions);

  return <div>child</div>;
}

describe("ConsoleLayout query-param behavior", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("uses deep-link config without overwriting saved console defaults until the user changes them", async () => {
    window.localStorage.setItem("hive-console-api-base", "http://127.0.0.1:9999");
    window.localStorage.setItem("hive-console-workspace", "/tmp/persisted-workspace");

    render(
      <MemoryRouter
        initialEntries={[
          "/settings?apiBase=http://127.0.0.1:8787&workspace=/tmp/demo-workspace",
        ]}
      >
        <ConsoleLayout>
          <div>child</div>
        </ConsoleLayout>
      </MemoryRouter>,
    );

    expect(screen.getByDisplayValue("http://127.0.0.1:8787")).toBeInTheDocument();
    expect(screen.getByDisplayValue("/tmp/demo-workspace")).toBeInTheDocument();
    expect(window.localStorage.getItem("hive-console-api-base")).toBe("http://127.0.0.1:9999");
    expect(window.localStorage.getItem("hive-console-workspace")).toBe("/tmp/persisted-workspace");

    const user = userEvent.setup();
    await user.clear(screen.getByLabelText("Workspace path"));
    await user.type(screen.getByLabelText("Workspace path"), "/tmp/operator-workspace");
    await user.clear(screen.getByLabelText("API base"));
    await user.type(screen.getByLabelText("API base"), "http://127.0.0.1:9998");
    await user.selectOptions(screen.getByLabelText("Theme"), "ledger");
    await user.selectOptions(screen.getByLabelText("Density"), "compact");
    await user.selectOptions(screen.getByLabelText("Default page"), "runs");

    expect(window.localStorage.getItem("hive-console-api-base")).toBe("http://127.0.0.1:9998");
    expect(window.localStorage.getItem("hive-console-workspace")).toBe("/tmp/operator-workspace");

    await waitFor(() => {
      expect(JSON.parse(window.localStorage.getItem(CONSOLE_PREFERENCES_KEY) ?? "{}")).toMatchObject({
        theme: "ledger",
        density: "compact",
        defaultPage: "runs",
      });
    });
    expect(document.querySelector(".console-shell")).toHaveAttribute("data-theme", "ledger");
    expect(document.querySelector(".console-shell")).toHaveAttribute("data-density", "compact");
  });

  it("debounces preference persistence before writing to localStorage", () => {
    vi.useFakeTimers();

    render(
      <MemoryRouter initialEntries={["/settings"]}>
        <ConsoleLayout>
          <div>child</div>
        </ConsoleLayout>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("Theme"), { target: { value: "ledger" } });
    expect(window.localStorage.getItem(CONSOLE_PREFERENCES_KEY)).toBeNull();

    vi.advanceTimersByTime(250);

    expect(JSON.parse(window.localStorage.getItem(CONSOLE_PREFERENCES_KEY) ?? "{}")).toMatchObject({
      theme: "ledger",
    });
  });

  it("syncs operator preferences when another tab updates the same storage key", async () => {
    render(
      <MemoryRouter initialEntries={["/settings"]}>
        <ConsoleLayout>
          <div>child</div>
        </ConsoleLayout>
      </MemoryRouter>,
    );

    const nextPreferences = {
      version: 1,
      theme: "ledger",
      density: "compact",
      defaultPage: "runs",
      runs: {
        filters: {
          projectId: "",
          driver: "codex",
          health: "",
          campaignId: "",
        },
        hiddenColumns: [],
        pinnedPanels: [],
        savedViews: [],
      },
    };

    act(() => {
      window.localStorage.setItem(CONSOLE_PREFERENCES_KEY, JSON.stringify(nextPreferences));
      window.dispatchEvent(new StorageEvent("storage", {
        key: CONSOLE_PREFERENCES_KEY,
        newValue: JSON.stringify(nextPreferences),
      }));
    });

    await waitFor(() => {
      expect(document.querySelector(".console-shell")).toHaveAttribute("data-theme", "ledger");
      expect(document.querySelector(".console-shell")).toHaveAttribute("data-density", "compact");
      expect(screen.getByLabelText("Default page")).toHaveValue("runs");
    });
  });

  it("preserves explicit deep-link config across shell navigation links", () => {
    render(
      <MemoryRouter
        initialEntries={[
          "/settings?apiBase=http://127.0.0.1:8787&workspace=/tmp/demo-workspace",
        ]}
      >
        <ConsoleLayout>
          <div>child</div>
        </ConsoleLayout>
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Runs" })).toHaveAttribute(
      "href",
      expect.stringContaining(
        "/runs?apiBase=http://127.0.0.1:8787&workspace=/tmp/demo-workspace",
      ),
    );
    expect(screen.getByRole("link", { name: "Notifications" })).toHaveAttribute(
      "href",
      expect.stringContaining(
        "/notifications?apiBase=http://127.0.0.1:8787&workspace=/tmp/demo-workspace",
      ),
    );
    expect(screen.getByRole("link", { name: "Integrations" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Activity" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Settings" })).toBeInTheDocument();
  });

  it("lets a fresh explicit deep link retake control after local config edits", async () => {
    render(
      <MemoryRouter
        initialEntries={[
          "/settings?apiBase=http://127.0.0.1:8787&workspace=/tmp/demo-workspace",
        ]}
      >
        <ConsoleLayout>
          <DeepLinkOverrideButton />
        </ConsoleLayout>
      </MemoryRouter>,
    );

    const user = userEvent.setup();
    await user.clear(screen.getByLabelText("API base"));
    await user.type(screen.getByLabelText("API base"), "http://127.0.0.1:9998");
    await user.clear(screen.getByLabelText("Workspace path"));
    await user.type(screen.getByLabelText("Workspace path"), "/tmp/operator-workspace");

    expect(screen.getByDisplayValue("http://127.0.0.1:9998")).toBeInTheDocument();
    expect(screen.getByDisplayValue("/tmp/operator-workspace")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open external deep link" }));

    await waitFor(() => {
      expect(screen.getByDisplayValue("http://127.0.0.1:7777")).toBeInTheDocument();
      expect(screen.getByDisplayValue("/tmp/external-workspace")).toBeInTheDocument();
    });
  });

  it("only remembers hydrated workspace paths instead of recording every typed edit as recent", async () => {
    window.localStorage.setItem("hive-console-workspace", "/tmp/persisted-workspace");

    render(
      <MemoryRouter initialEntries={["/settings"]}>
        <ConsoleLayout>
          <div>child</div>
        </ConsoleLayout>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(JSON.parse(window.localStorage.getItem(CONSOLE_PREFERENCES_KEY) ?? "{}")).toMatchObject({
        recentWorkspaces: ["/tmp/persisted-workspace"],
      });
    });

    const user = userEvent.setup();
    await user.clear(screen.getByLabelText("Workspace path"));
    await user.type(screen.getByLabelText("Workspace path"), "/tmp/operator-workspace");

    expect(JSON.parse(window.localStorage.getItem(CONSOLE_PREFERENCES_KEY) ?? "{}")).toMatchObject({
      recentWorkspaces: ["/tmp/persisted-workspace"],
    });
  });

  it("remembers explicit deep-link workspace paths as recent console workspaces", async () => {
    render(
      <MemoryRouter
        initialEntries={[
          "/settings?apiBase=http://127.0.0.1:8787&workspace=/tmp/demo-workspace",
        ]}
      >
        <ConsoleLayout>
          <div>child</div>
        </ConsoleLayout>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(JSON.parse(window.localStorage.getItem(CONSOLE_PREFERENCES_KEY) ?? "{}")).toMatchObject({
        recentWorkspaces: ["/tmp/demo-workspace"],
      });
    });
  });

  it("offers a skip link before the repeated shell chrome", async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={["/settings"]}>
        <ConsoleLayout>
          <div>child</div>
        </ConsoleLayout>
      </MemoryRouter>,
    );

    const skipLink = screen.getByRole("link", { name: "Skip to main content" });
    expect(skipLink).toHaveAttribute("href", "#console-main");
    expect(screen.getByRole("main")).toHaveAttribute("id", "console-main");

    await user.tab();
    expect(skipLink).toHaveFocus();
  });

  it("opens the shared command palette and surfaces route-local action provenance", async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();

    render(
      <MemoryRouter initialEntries={["/settings"]}>
        <ConsoleLayout>
          <PaletteActionRegistrar onAction={onAction} />
        </ConsoleLayout>
      </MemoryRouter>,
    );

    fireEvent.keyDown(window, { ctrlKey: true, key: "k" });
    expect(screen.getByRole("dialog", { name: "Command palette" })).toBeInTheDocument();

    const searchBox = screen.getByRole("textbox", { name: "Search actions" });
    await user.type(searchBox, "approve");
    expect(screen.getByRole("button", { name: /Approve demo approval/i })).toBeInTheDocument();
    expect(screen.getByText(/test harness/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Approve demo approval/i }));
    expect(onAction).toHaveBeenCalledTimes(1);
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Command palette" })).not.toBeInTheDocument();
    });

    fireEvent.keyDown(window, { metaKey: true, key: "k" });
    const pauseSearch = screen.getByRole("textbox", { name: "Search actions" });
    await user.type(pauseSearch, "pause");
    expect(screen.getByRole("button", { name: /Pause demo run/i })).toBeDisabled();
    expect(screen.getByText(/Unavailable because the demo run is already paused\./i)).toBeInTheDocument();
  });

  it("restores focus to the opener and hides the shell from assistive tech while the palette is open", async () => {
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={["/settings"]}>
        <ConsoleLayout>
          <PaletteActionRegistrar onAction={() => undefined} />
        </ConsoleLayout>
      </MemoryRouter>,
    );

    const openPaletteButton = screen.getByRole("button", { name: /Open Command Palette/i });
    await user.click(openPaletteButton);

    expect(await screen.findByRole("dialog", { name: "Command palette" })).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("textbox", { name: "Search actions" })).toHaveFocus();
    });
    expect(document.querySelector(".console-shell")).toHaveAttribute("aria-hidden", "true");

    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: "Command palette" })).not.toBeInTheDocument();
    });

    expect(openPaletteButton).toHaveFocus();
    expect(document.querySelector(".console-shell")).not.toHaveAttribute("aria-hidden");
  });

  it("renders disabled action reasons inline for non-focusable controls", () => {
    render(
      <ConsoleActionButton
        action={{
          id: "run.pause-demo",
          title: "Pause demo run",
          description: "Pause the demo run.",
          group: "Page actions",
          enabled: false,
          availabilityReason: "Unavailable because the demo run is already paused.",
          availabilitySource: "test harness",
          keywords: ["pause", "demo"],
          perform: () => undefined,
        }}
      />,
    );

    expect(screen.getByRole("button", { name: "Pause demo run" })).toBeDisabled();
    expect(screen.getByText("Unavailable because the demo run is already paused.")).toBeInTheDocument();
  });

  it("hides the hero shortcut badge when operators turn shortcut badges off", async () => {
    window.localStorage.setItem(
      CONSOLE_PREFERENCES_KEY,
      JSON.stringify({
        version: 1,
        theme: "clay",
        density: "comfortable",
        defaultPage: "home",
        notifications: {
          showActionable: true,
          showInformational: true,
        },
        keyboard: {
          showShortcutBadges: false,
        },
        runs: {
          filters: {
            projectId: "",
            driver: "",
            health: "",
            campaignId: "",
          },
          hiddenColumns: [],
          pinnedPanels: [],
          savedViews: [],
        },
        attention: {
          filters: {
            severity: "",
            kind: "",
            projectId: "",
            assignee: "",
            disposition: "",
            query: "",
          },
          savedViews: [],
          triageByItemId: {},
        },
        recentWorkspaces: [],
      }),
    );

    render(
      <MemoryRouter initialEntries={["/settings"]}>
        <ConsoleLayout>
          <div>child</div>
        </ConsoleLayout>
      </MemoryRouter>,
    );

    const paletteButton = screen.getByRole("button", { name: /Open Command Palette/i });
    expect(within(paletteButton).queryByText("Ctrl/Cmd+K")).not.toBeInTheDocument();
  });
});
