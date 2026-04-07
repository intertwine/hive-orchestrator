import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import App from "../App";

export interface MockRoute {
  method?: string;
  pathname: string;
  response: Response | ((url: URL, init?: RequestInit) => Response);
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export function installFetchMock(routes: MockRoute[]) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(typeof input === "string" ? input : input instanceof URL ? input : input.url);
    const method = (init?.method ?? "GET").toUpperCase();
    const route = routes.find((candidate) => {
      return (candidate.method ?? "GET").toUpperCase() === method && candidate.pathname === url.pathname;
    });
    if (!route) {
      throw new Error(`Unhandled console request: ${method} ${url.pathname}`);
    }
    return typeof route.response === "function" ? route.response(url, init) : route.response.clone();
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function renderConsole(initialEntries: string[]) {
  window.localStorage.setItem("hive-console-api-base", "http://127.0.0.1:8787");
  window.localStorage.setItem("hive-console-workspace", "/tmp/hive-demo");
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <App />
    </MemoryRouter>,
  );
}
