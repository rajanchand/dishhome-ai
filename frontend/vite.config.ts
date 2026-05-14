import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true, // listen on 0.0.0.0 so ngrok / phone-on-LAN can reach it
    strictPort: true,
  },
  preview: {
    port: 3000,
    host: true,
  },
});
