import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
const runtimeErrors = new WeakMap<Page, string[]>();
test.beforeEach(({ page }) => {
  const errors: string[] = [];
  runtimeErrors.set(page, errors);
  page.on('pageerror', (error) => errors.push(error.message));
});
test.afterEach(({ page }) => expect(runtimeErrors.get(page)).toEqual([]));
test('full approval, separate application, simulated verification and history', async ({
  page,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/incidents/inc_001');
  await expect(
    page.getByRole('heading', { name: 'Registration fails on missing profile' }),
  ).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Apply approved patch to local demo', exact: true }),
  ).toBeDisabled();
  await page.getByRole('button', { name: 'Diagnosis', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'src/registration.py:42–49' })).toBeVisible();
  await page.getByRole('button', { name: 'Patch & tests', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Isolated validation' })).toBeVisible();
  await page.getByRole('button', { name: 'Approve candidate', exact: true }).click();
  await page
    .getByLabel('Review comment (optional)')
    .fill('Reviewed exact diff and reproduction evidence.');
  await page.getByRole('button', { name: 'Confirm approval', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Apply approved patch to local demo', exact: true }),
  ).toBeEnabled();
  await page
    .getByRole('button', { name: 'Apply approved patch to local demo', exact: true })
    .click();
  await page.getByRole('button', { name: 'Confirm simulated apply', exact: true }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await page.getByRole('button', { name: 'Report', exact: true }).click();
  await expect(
    page.getByText('No recurrence in one simulated observation cycle.', { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Report v1', exact: true })).toBeVisible();
  await page.getByRole('link', { name: 'Incident History', exact: true }).click();
  await expect(
    page.getByText('Registration fails on missing profile', { exact: true }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
test('reject, failed tests, manual review and stale candidate are safe', async ({ page }) => {
  await page.goto('/approval-recovery?incident=inc_001');
  await page.getByRole('button', { name: 'Reject candidate', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm rejection', exact: true }).click();
  await expect(
    page.getByText('Candidate rejected. No patch was applied.', { exact: true }),
  ).toBeVisible();
  await page.goto('/incidents/inc_002');
  await expect(page.getByRole('button', { name: 'Approve candidate', exact: true })).toBeDisabled();
  await expect(
    page.getByText(/Failed validation. A candidate revision is required/).first(),
  ).toBeVisible();
  await page.goto('/incidents/inc_003?tab=diagnosis');
  await expect(
    page.getByRole('heading', { name: 'Needs manual review. No supported diagnosis.' }),
  ).toBeVisible();
  await page.goto('/approval-recovery?incident=inc_006');
  await page.getByRole('button', { name: 'Approve candidate', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm approval', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Review required: Candidate changed.');
  await expect(page.getByRole('button', { name: 'Approve candidate', exact: true })).toBeDisabled();
  await expect(
    page.getByRole('button', { name: 'Apply approved patch to local demo', exact: true }),
  ).toBeDisabled();
});
test('all sidebar pages, deep links, search, monitoring, preferences and reset', async ({
  page,
}) => {
  const routes = [
    ['/dashboard', 'A clearer view. A calmer workflow.'],
    ['/applications', 'Applications'],
    ['/incidents', 'Incidents'],
    ['/agents', 'AI Agents'],
    ['/repair-testing', 'Repair & Testing'],
    ['/approval-recovery', 'Approval & Recovery'],
    ['/history', 'Incident History'],
    ['/settings', 'Settings'],
  ];
  for (const [route, name] of routes) {
    await page.goto(route);
    await expect(page.getByRole('heading', { name, exact: true })).toBeVisible();
  }
  await page.getByLabel('Theme', { exact: true }).selectOption('dark');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.getByLabel('Motion preference').selectOption('reduce');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-motion', 'reduce');
  await page.goto('/incidents');
  await page.getByLabel('Search incidents').fill('unsupported');
  await expect(page.locator('.incident-row')).toHaveCount(1);
  await page.goto('/applications/app_demo');
  await page.getByRole('button', { name: 'Stop monitoring', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm monitoring change' }).click();
  await expect(page.getByRole('button', { name: 'Start monitoring', exact: true })).toBeVisible();
  await page.goto('/agents');
  await expect(page.locator('.agent-card')).toHaveCount(6);
  await page.locator('.agent-card').first().click();
  await expect(page.getByRole('heading', { name: 'Manager Agent', exact: true })).toBeVisible();
  await page.goto('/settings');
  await page.getByRole('button', { name: 'Reset demo data', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm reset', exact: true }).click();
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await page.goto('/missing');
  await expect(page.getByRole('heading', { name: 'Page not found' })).toBeVisible();
});
for (const width of [320, 360, 768, 1024, 1440])
  test(`responsive ${width}px, keyboard and screenshots`, async ({ page }) => {
    test.setTimeout(60000);
    await page.setViewportSize({ width, height: 1000 });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/agents');
    await expect(page.locator('.agent-card')).toHaveCount(6);
    await expect(page.getByRole('heading', { name: 'AI Agents', exact: true })).toBeVisible();
    await expect(page.locator('.agent-grid>div').last()).toHaveCSS('opacity', '1');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
      true,
    );
    await page.screenshot({ path: `test-results/agents-${width}.png`, fullPage: true });
    if (width < 801) {
      await page.getByRole('button', { name: 'Open navigation' }).click();
      await expect(page.getByRole('dialog')).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(page.getByRole('dialog')).not.toBeVisible();
      await expect(page.getByRole('button', { name: 'Open navigation' })).toBeFocused();
    }
    for (const route of [
      '/dashboard',
      '/applications',
      '/applications/app_demo',
      '/incidents',
      '/incidents/inc_001?tab=patch%20%26%20tests',
      '/approval-recovery',
      '/repair-testing',
      '/history',
      '/agents/manager',
      '/settings',
    ]) {
      await page.goto(route);
      await expect(page.locator('h1')).toBeVisible();
      await expect(page.locator('.skeleton')).toHaveCount(0);
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
        route,
      ).toBe(true);
      if (width === 320 || width === 1440)
        await page.screenshot({
          path: `test-results/audit${route.split('?')[0].replaceAll('/', '-')}-${width}.png`,
          fullPage: true,
        });
    }
    await page.screenshot({ path: `test-results/settings-${width}.png`, fullPage: true });
  });
test('accessible landmarks, controls and contrast in light and dark', async ({ page }) => {
  test.setTimeout(90000);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  for (const theme of ['light', 'dark']) {
    await page.addInitScript((value) => localStorage.setItem('sentinel.theme', value), theme);
    for (const route of [
      '/agents',
      '/dashboard',
      '/applications',
      '/applications/app_demo',
      '/incidents',
      '/incidents/inc_001?tab=patch%20%26%20tests',
      '/incidents/inc_007?tab=report',
      '/repair-testing',
      '/approval-recovery',
      '/history',
      '/settings',
    ]) {
      await page.goto(route);
      await expect(page.locator('.skeleton')).toHaveCount(0);
      if (route === '/agents')
        await expect(page.locator('.agent-grid>div').last()).toHaveCSS('opacity', '1');
      const result = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
        .analyze();
      expect(
        result.violations.map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) })),
        `${theme} ${route}`,
      ).toEqual([]);
    }
  }
});
test('review dialogs trap keyboard focus, validate comments and prevent dismissal while submitting', async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 760 });
  await page.goto('/incidents/inc_001?tab=patch%20%26%20tests');
  const approve = page.getByRole('button', { name: 'Approve candidate', exact: true });
  await approve.click();
  await expect(page.getByRole('dialog')).toBeVisible();
  for (let index = 0; index < 8; index++) {
    await page.keyboard.press('Tab');
    expect(await page.evaluate(() => !!document.activeElement?.closest('dialog[open]'))).toBe(true);
  }
  await page.getByLabel('Review comment (optional)').fill('x'.repeat(2001));
  await page.getByRole('button', { name: 'Confirm approval', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Keep the comment under 2,000 characters.');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(approve).toBeFocused();
  await approve.click();
  await page.getByRole('button', { name: 'Confirm approval', exact: true }).click();
  await expect(
    page.getByRole('button', { name: 'Apply approved patch to local demo', exact: true }),
  ).toBeEnabled();
  await page
    .getByRole('button', { name: 'Apply approved patch to local demo', exact: true })
    .click();
  await page.getByRole('button', { name: 'Confirm simulated apply', exact: true }).click();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.getByRole('dialog')).not.toBeVisible();
});
test('quick actions move focus, dismiss, and navigate without hiding active filters', async ({
  page,
}) => {
  await page.goto('/dashboard');
  const toggle = page.getByRole('button', { name: 'Quick actions', exact: true });
  await toggle.click();
  await expect(
    page.getByRole('link', { name: 'View active incidents', exact: true }),
  ).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(toggle).toBeFocused();
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await toggle.click();
  await page.getByRole('link', { name: 'View active incidents', exact: true }).click();
  await expect(page.getByRole('combobox', { name: 'Incident scope' })).toHaveValue('open');
  await expect(page.locator('#main')).toBeFocused();
  await toggle.click();
  await page.getByRole('link', { name: 'Review pending approvals', exact: true }).click();
  await expect(page.getByRole('combobox', { name: 'Review queue' })).toHaveValue('pending');
  await toggle.click();
  await page.getByRole('link', { name: 'Recent reports', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Incident History', exact: true })).toBeVisible();
  await toggle.click();
  await page.getByRole('heading', { name: 'Incident History', exact: true }).click();
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
});
test('sorting, cursor pagination, browser history and unresolved reports remain accurate', async ({
  page,
}) => {
  await page.goto('/incidents');
  await expect(page.locator('.incident-row')).toHaveCount(5);
  const first = await page.locator('.incident-row').first().textContent();
  await page.getByRole('button', { name: 'Next', exact: true }).click();
  await expect(page.locator('.incident-row')).toHaveCount(2);
  await page.reload();
  await page.getByRole('button', { name: 'Previous', exact: true }).click();
  await expect(page.locator('.incident-row').first()).toHaveText(first!);
  await page.getByLabel('Sort incidents').selectOption('detected_asc');
  await expect(page.locator('.incident-row').first()).toContainText(
    'Verification failed; sample restored',
  );
  await page.goBack();
  await expect(page.getByLabel('Sort incidents')).toHaveValue('detected_desc');
  await page.goto('/incidents/inc_007?tab=report');
  await expect(page.getByText('Verification Failed', { exact: true })).toBeVisible();
  await expect(page.getByText(/Restore: Restored/)).toBeVisible();
  await expect(
    page.getByText(/snapshot was restored; the incident remains unresolved/),
  ).toBeVisible();
});
