import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

function createMemoryStorage(): Storage {
  const values = new Map<string, string>();
  return {
    get length() {
      return values.size;
    },
    clear() {
      values.clear();
    },
    getItem(key: string) {
      return values.has(key) ? values.get(key)! : null;
    },
    key(index: number) {
      return Array.from(values.keys())[index] ?? null;
    },
    removeItem(key: string) {
      values.delete(key);
    },
    setItem(key: string, value: string) {
      values.set(String(key), String(value));
    },
  };
}

function ensureStorage(name: "localStorage" | "sessionStorage"): Storage {
  const current = window[name];
  if (
    current
    && typeof current.clear === "function"
    && typeof current.getItem === "function"
    && typeof current.setItem === "function"
    && typeof current.removeItem === "function"
  ) {
    return current;
  }

  const storage = createMemoryStorage();
  Object.defineProperty(window, name, {
    configurable: true,
    value: storage,
  });
  Object.defineProperty(globalThis, name, {
    configurable: true,
    value: storage,
  });
  return storage;
}

ensureStorage("localStorage");
ensureStorage("sessionStorage");

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  window.sessionStorage.clear();
});
