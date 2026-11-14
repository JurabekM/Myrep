import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Tauri dev server uchun qat'iy port: tauri.conf.json dagi devUrl bilan bir xil.
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: { port: 1430, strictPort: true },
  build: { target: "es2022", outDir: "dist" },
});
