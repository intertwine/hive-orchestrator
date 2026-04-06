import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ConsoleLayout } from "../components/ConsoleLayout";
import { CONSOLE_PREFERENCES_KEY } from "../preferences";

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
        storageArea: window.localStorage,
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
});
