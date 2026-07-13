import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy API calls to the backend in dev so the frontend can use relative URLs.
    proxy: {
      "/brands": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
