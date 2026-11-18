import { afterEach, expect, it, vi } from 'vitest';
afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});
it('defaults to the explicit mock adapter when data source is absent', async () => {
  vi.stubEnv('VITE_DATA_SOURCE', undefined);
  vi.resetModules();
  const client = await import('../api/client');
  expect(client.isDemo).toBe(true);
  expect(client.api.constructor.name).toBe('MockSentinelApi');
  expect(client.demoControls?.reset).toBeTypeOf('function');
});
it('selects the HTTP adapter without mock reset capability when API mode is requested', async () => {
  vi.stubEnv('VITE_DATA_SOURCE', 'api');
  vi.resetModules();
  const client = await import('../api/client');
  expect(client.isDemo).toBe(false);
  expect(client.api.constructor.name).toBe('HttpSentinelApi');
  expect(client.demoControls).toBeNull();
});
it('rejects an invalid source instead of silently falling back to mock', async () => {
  vi.stubEnv('VITE_DATA_SOURCE', 'invalid');
  vi.resetModules();
  await expect(import('../api/client')).rejects.toThrow('VITE_DATA_SOURCE must be mock or api');
});
