import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { ConsoleLayout } from "../components/ConsoleLayout";
import { CONSOLE_PREFERENCES_KEY } from "../preferences";

describe("ConsoleLayout query-param behavior", () => {
  const originalUrl = window.location.href;

  beforeEach(() => {
    window.localStorage.clear();
  });

  afterEach(() => {
    window.history.replaceState({}, "", originalUrl);
  });

  it("uses deep-link config without overwriting saved console defaults until the user changes them", async () => {
    window.localStorage.setItem("hive-console-api-base", "http://127.0.0.1:9999");
    window.localStorage.setItem("hive-console-workspace", "/tmp/persisted-workspace");
    window.history.replaceState(
      {},
      "",
      "/console?apiBase=http://127.0.0.1:8787&workspace=/tmp/demo-workspace",
    );

    render(
      <MemoryRouter>
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

    expect(JSON.parse(window.localStorage.getItem(CONSOLE_PREFERENCES_KEY) ?? "{}")).toMatchObject({
      theme: "ledger",
      density: "compact",
      defaultPage: "runs",
    });
    expect(document.querySelector(".console-shell")).toHaveAttribute("data-theme", "ledger");
    expect(document.querySelector(".console-shell")).toHaveAttribute("data-density", "compact");
  });
});
