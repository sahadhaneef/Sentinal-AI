import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
test('landing navigation, interactive workflow, agents, FAQ and product video', async ({
  page,
}) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Understand the issue.');
  await page.getByRole('button', { name: /Diagnose/ }).click();
  await expect(page.locator('.stage-explainer')).toContainText('Diagnosis Agent');
  await page.locator('.public-agent').first().getByText('Behind the scenes').click();
  await expect(page.getByText(/Coordinates typed handoffs/)).toBeVisible();
  await page.getByText('Does it automatically change my application?', { exact: true }).click();
  await expect(page.locator('.faq-item[open]')).toContainText(/no real files/i);
  const faqSummary = page.locator('.faq-item[open] summary');
  await faqSummary.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('.faq-item[open]')).toHaveCount(0);
  await page.keyboard.press('Space');
  await expect(page.locator('.faq-item[open]')).toHaveCount(1);
  await expect(page.locator('.faq-cards > .faq-item')).toHaveCount(8);
  await expect(page.locator('#faq')).toHaveCSS('opacity', '1');
  await page.locator('#faq').screenshot({ path: 'docs/screenshots/faq-cards.png' });
  await expect(page.locator('video')).toHaveCount(1);
  await expect(page.getByRole('heading', { name: 'Six agents. A guided tour.' })).toBeVisible();
  await expect(page.locator('video track[kind="captions"]')).toHaveCount(1);
  await page.getByRole('link', { name: 'Get Started', exact: true }).click();
  await expect(page).toHaveURL(/onboarding/);
  await page.getByRole('button', { name: 'Skip introduction' }).click();
  await expect(page).toHaveURL(/dashboard/);
});
test('workflow loops automatically and lets visitors inspect each stage', async ({ page }) => {
  test.setTimeout(60000);
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.goto('/');
  const panel = page.locator('.workflow-experience');
  await panel.scrollIntoViewIfNeeded();
  await page.mouse.move(0, 0);
  await expect(panel.getByRole('button', { name: /Play workflow/ })).toHaveCount(0);
  await expect(panel.locator('.stage-explainer')).toContainText('Diagnosis Agent', { timeout: 8000 });
  const report = panel.getByRole('button', { name: /Report/ });
  await report.click();
  await expect(panel.locator('.stage-explainer')).toContainText('Reporting Agent');
  await page.mouse.move(0, 0);
  await report.evaluate((element) => element.blur());
  await expect(panel.locator('.stage-explainer')).toContainText('Monitoring Agent', { timeout: 8000 });
  const approve = panel.getByRole('button', { name: /Approve/ });
  await approve.click();
  await expect(panel.locator('.workflow-safety')).toContainText('does not approve or apply');
  await page.mouse.move(0, 0);
  await approve.evaluate((element) => element.blur());
  await expect(panel.locator('.stage-explainer')).toContainText('Manager Agent', { timeout: 8000 });
});

test('reduced-motion workflow keeps all stages available on mobile', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto('/');
  await expect(page.locator('.workflow-experience')).toHaveAttribute('data-running', 'false');
  await page.getByRole('button', { name: /Local apply/ }).click();
  await expect(page.locator('.stage-explainer')).toContainText('separate confirmation');
  await page.getByRole('button', { name: /Verify/ }).click();
  await expect(page.locator('.stage-explainer')).toContainText('unresolved outcome');
  await expect(page.locator('.workflow-safety')).toContainText('Reduced motion');
});
for (const decision of ['approve', 'reject'])
  test(`guided demo ${decision} keeps application separate and can restart`, async ({ page }) => {
    await page.goto('/demo');
    await expect(page.getByText(/Simulated Demo ·/)).toBeVisible();
    for (let i = 0; i < 6; i++)
      await page.getByRole('button', { name: 'Next', exact: true }).click();
    await expect(page.getByRole('button', { name: 'Next', exact: true })).toBeDisabled();
    await page
      .getByRole('button', {
        name: decision === 'approve' ? 'Approve candidate' : 'Reject candidate',
        exact: true,
      })
      .click();
    await expect(page.getByRole('button', { name: 'Next', exact: true })).toBeEnabled();
    await page.getByRole('button', { name: 'Next', exact: true }).click();
    if (decision === 'approve') {
      await expect(page.getByRole('button', { name: 'Next', exact: true })).toBeDisabled();
      await page.getByRole('button', { name: 'Apply approved patch in simulation' }).click();
      await expect(page.getByRole('button', { name: 'Next', exact: true })).toBeEnabled();
      await page.getByRole('button', { name: 'Next', exact: true }).click();
      await page.getByRole('button', { name: 'Next', exact: true }).click();
    }
    await expect(page.locator('.demo-evidence')).toContainText(
      decision === 'approve' ? 'verified outcome' : 'decision to stop',
    );
    await page.getByRole('button', { name: 'Previous', exact: true }).click();
    await page.getByRole('button', { name: 'Restart', exact: true }).click();
    await expect(page.getByText('Step 1 of 10')).toBeVisible();
    await page.getByRole('link', { name: 'Exit demo' }).click();
    await expect(page).toHaveURL(/\/$/);
  });
test('onboarding resumes, restarts, completes and persists completion', async ({ page }) => {
  await page.goto('/onboarding');
  await page.getByRole('button', { name: 'Next', exact: true }).click();
  await page.reload();
  await expect(page.getByText('Step 2 of 6')).toBeVisible();
  await page.getByRole('button', { name: 'Back', exact: true }).click();
  await page.getByRole('button', { name: 'Restart introduction' }).click();
  for (let i = 0; i < 5; i++) await page.getByRole('button', { name: 'Next', exact: true }).click();
  await page.getByRole('button', { name: 'Enter dashboard' }).click();
  await expect(page).toHaveURL(/dashboard/);
  expect(
    await page.evaluate(() => JSON.parse(localStorage.getItem('sentinel.onboarding')!).done),
  ).toBe(true);
});
for (const width of [320, 768, 1440])
  test(`public experience responsive ${width}px and screenshots`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    for (const [path, name] of [
      ['/', 'landing'],
      ['/demo', 'interactive-demo'],
      ['/onboarding', 'onboarding'],
      ['/dashboard', 'dashboard'],
    ]) {
      await page.goto(path);
      await expect(page.locator('h1')).toBeVisible();
      await expect(page.locator('.skeleton')).toHaveCount(0);
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
        path,
      ).toBe(true);
      if (width !== 768)
        await page.screenshot({
          path: `test-results/redesign-${name}-${width}.png`,
          fullPage: true,
        });
      if (path === '/' && width !== 768)
        await page.screenshot({ path: `test-results/premium-hero-${width}.png` });
    }
  });
test('public theme switching and accessibility', async ({ page }) => {
  test.setTimeout(90000);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await page.getByRole('button', { name: 'Toggle theme' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.screenshot({ path: 'test-results/redesign-dark.png', fullPage: true });
  for (const theme of ['light', 'dark']) {
    await page.evaluate((value) => localStorage.setItem('sentinel.theme', value), theme);
    for (const path of ['/', '/onboarding', '/demo']) {
      await page.goto(path);
      await expect(page.locator('h1')).toBeVisible();
      await expect(page.locator('.skeleton')).toHaveCount(0);
      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
        .analyze();
      expect(
        results.violations.map((v) => ({ id: v.id, targets: v.nodes.map((n) => n.target) })),
        `${theme} ${path}`,
      ).toEqual([]);
    }
  }
});
