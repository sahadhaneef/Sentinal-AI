import { test, expect, type Page } from '@playwright/test';
import { MockSentinelApi } from '../../src/api/mockAdapter';
import { ApiClientError } from '../../src/api/errors';
import { incidentFiltersSchema } from '../../src/contracts/schemas';
import type { AgentType } from '../../src/contracts/types';
const runtimeErrors = new WeakMap<Page, string[]>();
test.beforeEach(({ page }) => {
  const errors: string[] = [];
  runtimeErrors.set(page, errors);
  page.on('pageerror', (error) => errors.push(error.message));
});
test.afterEach(({ page }) => expect(runtimeErrors.get(page)).toEqual([]));

type Control = { failure?: number; hold?: Promise<void>; offline?: boolean };
async function interceptApi(page: Page, control: Control = {}) {
  const service = new MockSentinelApi(0),
    mutations: { path: string; body: unknown; headers: Record<string, string> }[] = [];
  await page.route('http://localhost:8000/api/v1/**', async (route) => {
    if (control.offline) {
      await route.abort('failed');
      return;
    }
    const request = route.request(),
      url = new URL(request.url()),
      path = url.pathname.replace('/api/v1', ''),
      method = request.method();
    const headers = {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': 'http://127.0.0.1:5184',
      'Access-Control-Allow-Credentials': 'true',
      'Access-Control-Allow-Headers': 'content-type,idempotency-key,x-csrf-token',
      'Access-Control-Allow-Methods': 'GET,POST,PATCH,OPTIONS',
    };
    if (method === 'OPTIONS') {
      await route.fulfill({ status: 204, headers });
      return;
    }
    try {
      if (path === '/incidents' && control.hold) await control.hold;
      if (path === '/incidents' && control.failure)
        throw new ApiClientError(
          'FORBIDDEN',
          'Access is required to view incidents.',
          control.failure,
        );
      if (method !== 'GET')
        mutations.push({ path, body: request.postDataJSON(), headers: request.headers() });
      const parts = path.split('/').filter(Boolean),
        id = parts[1];
      let result: unknown;
      if (path === '/health') result = await service.getHealth();
      else if (path === '/dashboard/summary') result = await service.getDashboardSummary();
      else if (path === '/applications') result = await service.listApplications();
      else if (parts[0] === 'applications') result = await service.getApplication(id);
      else if (path === '/incidents') {
        const raw = Object.fromEntries(url.searchParams);
        result = await service.listIncidents(
          incidentFiltersSchema.parse({ ...raw, limit: raw.limit ? Number(raw.limit) : undefined }),
        );
      } else if (parts[0] === 'incidents' && parts[2] === 'decision')
        result = await service.decide(id, request.postDataJSON());
      else if (parts[0] === 'incidents' && parts[2] === 'apply')
        result = await service.applyApprovedPatch(id, request.postDataJSON());
      else if (parts[0] === 'incidents' && parts[2] === 'events')
        result = await service.getIncidentEvents(id);
      else if (parts[0] === 'incidents') result = await service.getIncident(id);
      else if (path === '/agents') result = await service.listAgents();
      else if (parts[0] === 'agents') result = await service.getAgent(id as AgentType);
      else if (path === '/settings') result = await service.getSettings();
      else throw new ApiClientError('NOT_FOUND', 'This item could not be found.', 404);
      await route.fulfill({ status: 200, headers, body: JSON.stringify(result) });
    } catch (error) {
      const failure =
        error instanceof ApiClientError
          ? error
          : new ApiClientError('INTERNAL_ERROR', 'Test transport failed.', 500);
      await route.fulfill({
        status: failure.status || 500,
        headers,
        body: JSON.stringify(failure.toEnvelope()),
      });
    }
  });
  return mutations;
}
test('HTTP mode renders actual adapter responses and sends exact separate approval/apply requests', async ({
  page,
  context,
}) => {
  const mutations = await interceptApi(page);
  await context.addCookies([
    { name: 'csrf_token', value: 'review-token', url: 'http://127.0.0.1:5184' },
  ]);
  await page.goto('/incidents/inc_001?tab=patch%20%26%20tests');
  await expect(page.getByRole('heading', { name: 'Isolated validation' })).toBeVisible();
  await expect(
    page.getByText('API mode — backend session required', { exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Approve candidate', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm approval', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Apply approved patch to local demo', exact: true }),
  ).toBeEnabled();
  expect(mutations).toHaveLength(1);
  expect(mutations[0].path).toBe('/incidents/inc_001/decision');
  expect(mutations[0].body).toMatchObject({
    candidate_id: 'patch_001',
    base_revision: 'abc123',
    decision: 'approve',
  });
  expect(mutations[0].headers['x-csrf-token']).toBe('review-token');
  expect(mutations[0].headers['idempotency-key']).toBeTruthy();
  await page
    .getByRole('button', { name: 'Apply approved patch to local demo', exact: true })
    .click();
  await expect(page.getByRole('dialog')).not.toContainText('No real files are changed');
  await page.getByRole('button', { name: 'Confirm local apply', exact: true }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  expect(mutations).toHaveLength(2);
  expect(mutations[1].path).toBe('/incidents/inc_001/apply');
  expect(mutations[1].body).toMatchObject({ candidate_id: 'patch_001', base_revision: 'abc123' });
  await expect(
    page.getByRole('status').filter({ hasText: 'Apply request accepted.' }),
  ).toBeVisible();
  await page.getByRole('link', { name: 'AI Agents', exact: true }).click();
  await expect(page.getByText('BACKEND AGENT ACTIVITY', { exact: true })).toBeVisible();
  await expect(page.getByText('SIMULATED AGENT ACTIVITY', { exact: true })).toHaveCount(0);
});
test('HTTP loading, access errors and retry preserve search and filter inputs', async ({
  page,
}) => {
  let release!: () => void;
  const control: Control = {
    hold: new Promise<void>((resolve) => {
      release = resolve;
    }),
    failure: 403,
  };
  await interceptApi(page, control);
  await page.goto('/incidents?search=registration&severity=high');
  await expect(page.getByRole('status', { name: 'Loading content' })).toBeVisible();
  release();
  await expect(page.getByRole('alert')).toContainText('Access required');
  await expect(page.getByLabel('Search incidents')).toHaveValue('registration');
  await expect(page.getByLabel('Filter severity')).toHaveValue('high');
  control.failure = undefined;
  await page.getByRole('button', { name: 'Retry', exact: true }).click();
  await expect(page.locator('.incident-row')).toHaveCount(1);
  await expect(page.getByLabel('Search incidents')).toHaveValue('registration');
  await page.goto('/incidents/does-not-exist');
  await expect(page.getByRole('alert')).toContainText('Item not found');
});
test('HTTP offline state remains visible on mobile and never silently falls back to demo', async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 760 });
  await interceptApi(page, { offline: true });
  await page.goto('/agents');
  await expect(page.getByText('Backend unavailable', { exact: true })).toBeVisible({
    timeout: 15000,
  });
  await expect(page.getByText('Demo mode — simulated data', { exact: true })).toHaveCount(0);
  await expect(page.locator('.agent-card')).toHaveCount(0);
});
