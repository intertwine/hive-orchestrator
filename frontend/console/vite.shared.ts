import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export function createConsoleViteConfig({
  base,
  outDir,
  port,
}: {
  base: string;
  outDir: string;
  port: number;
}) {
  return defineConfig({
    base,
    plugins: [react()],
    test: {
      environment: "jsdom",
      setupFiles: "./src/test/setup.ts",
      include: ["src/test/**/*.test.ts", "src/test/**/*.test.tsx"],
      exclude: ["e2e/**"],
    },
    server: {
      host: "127.0.0.1",
      port,
    },
    build: {
      outDir,
      emptyOutDir: true,
    },
  });
}
