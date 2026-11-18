import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  timeout: 30000,
  expect: { timeout: 7000 },
  use: { baseURL: 'http://127.0.0.1:5183', headless: true, trace: 'retain-on-failure' },
  projects: [
    { name: 'mock', testIgnore: '**/http-mode.spec.ts' },
    { name: 'http', testMatch: '**/http-mode.spec.ts', use: { baseURL: 'http://127.0.0.1:5184' } },
  ],
  webServer: [
    {
      command: 'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5183 --strictPort',
      url: 'http://127.0.0.1:5183',
      env: { VITE_DATA_SOURCE: 'mock' },
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5184 --strictPort',
      url: 'http://127.0.0.1:5184',
      env: { VITE_DATA_SOURCE: 'api', VITE_API_BASE_URL: 'http://localhost:8000/api/v1' },
      reuseExistingServer: !process.env.CI,
    },
  ],
  reporter: 'list',
});
