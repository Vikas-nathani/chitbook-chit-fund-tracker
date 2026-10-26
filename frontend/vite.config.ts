import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In dev, /api is proxied to the backend so the app and API share one origin.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3500,
    proxy: {
      '/api': 'http://localhost:8080',
    },
  },
});
