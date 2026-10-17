import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { fileURLToPath } from "node:url";

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],

  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,

    proxy: {
      "/api": {
        target: "http://127.0.0.1:8765",
        changeOrigin: true,
      },
    },
  },

  build: {
    outDir: path.resolve(
      currentDirectory,
      "../src/accessmatrix/resources/gui",
    ),
    emptyOutDir: true,
    sourcemap: true,
  },
});