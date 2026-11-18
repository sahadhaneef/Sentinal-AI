import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwind from '@tailwindcss/vite';
export default defineConfig({
  plugins: [react(), tailwind()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/tests/setup.ts'],
    exclude: ['**/node_modules/**', '.npm-cache/**', 'tests/e2e/**'],
  },
});
