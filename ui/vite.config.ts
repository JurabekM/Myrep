import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vitest/config";

// Port qat'iy: tauri.conf.json dagi build.devUrl shu portga qaraydi.
const DEV_PORT = 1420;

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Tauri o'zining terminal chiqishini ko'rsatadi; Vite ekranni tozalamasin.
  clearScreen: false,
  server: {
    port: DEV_PORT,
    strictPort: true,
    // Rust tomonidagi o'zgarishlar frontend qayta yuklanishiga sabab bo'lmasin.
    watch: { ignored: ["**/src-tauri/**"] },
  },
  build: {
    // WebView2 (Windows) va WKWebView (macOS) uchun maqsad versiyalar.
    target: ["chrome111", "safari16.4"],
    sourcemap: false,
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
