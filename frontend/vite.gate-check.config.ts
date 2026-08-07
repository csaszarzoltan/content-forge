import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// Temporary gate-verification config: proxy /api to the contentforge backend on 8099
// (the default config targets 8000, which is occupied by the LLM Budget Gateway on this host).
export default defineConfig({
  plugins: [react()],
  test: { globals: true, setupFiles: ["./src/test-setup.ts"] },
  server: { proxy: { "/api": "http://127.0.0.1:8099" } },
});
