import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "/console/",
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    include: ["src/test/**/*.test.ts", "src/test/**/*.test.tsx"],
    exclude: ["e2e/**"],
  },
  server: {
    host: "127.0.0.1",
    port: 4174,
  },
  build: {
    outDir: "../../src/hive/resources/console",
    emptyOutDir: true,
  },
});
