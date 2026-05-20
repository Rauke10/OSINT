import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// The built SPA is emitted into the Python package so FastAPI serves it.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "../src/globeye/api/static",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
