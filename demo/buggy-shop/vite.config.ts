import { defineConfig } from "vite";

export default defineConfig({
  server: { port: 5174, strictPort: true },
  // Unminified until source-map symbolication lands (phase 3), so stack traces
  // stay readable and grouping stays stable across builds (ADR 0007).
  build: { minify: false, sourcemap: true },
});
