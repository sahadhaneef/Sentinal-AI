import { test, expect } from '@playwright/test';

test('workspace tiles retain routes, distinct palettes and keyboard navigation', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.goto('/');
  const panel = page.locator('#platform');
  await panel.scrollIntoViewIfNeeded();
  const tiles = panel.locator('.workspace-tile');
  await expect(tiles).toHaveCount(8);
  const hrefs = await tiles.evaluateAll((items) => items.map((item) => item.getAttribute('href')));
  expect(hrefs).toEqual([
    '/dashboard',
    '/applications',
    '/agents',
    '/incidents',
    '/repair-testing',
    '/approval-recovery',
    '/history',
    '/incidents/inc_005?tab=report',
  ]);
  const tones = await tiles.evaluateAll((items) =>
    items.map((item) => getComputedStyle(item).getPropertyValue('--tile-color').trim()),
  );
  expect(new Set(tones).size).toBe(8);
  const dashboard = tiles.first();
  await dashboard.hover();
  await expect
    .poll(() =>
      dashboard
        .locator('.workspace-icon-reel')
        .evaluate((element) => new DOMMatrix(getComputedStyle(element).transform).m42),
    )
    .toBe(-48);
  await panel.screenshot({ path: 'test-results/workspace-explorer-light.png' });
  await page.getByRole('button', { name: 'Toggle theme' }).click();
  await panel.scrollIntoViewIfNeeded();
  await panel.screenshot({ path: 'test-results/workspace-explorer-dark.png' });
  await dashboard.focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/dashboard/);
});

test('workspace tiles stay steady with reduced motion on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  const tile = page.locator('.workspace-tile').first();
  await tile.focus();
  await expect(tile).toHaveCSS('transform', 'none');
  await expect(tile.locator('.workspace-icon-reel')).toHaveCSS('transform', 'none');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.locator('#platform').screenshot({ path: 'test-results/workspace-explorer-320.png' });
});
