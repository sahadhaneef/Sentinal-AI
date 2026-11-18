import { test, expect } from '@playwright/test';

test('feature story stacks with scroll and reverses without trapping navigation', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.goto('/');
  const cards = page.locator('.scroll-stack-card');
  await expect(cards).toHaveCount(4);
  await expect(cards.first()).toHaveCSS('position', 'sticky');
  const start = await page.locator('.scroll-feature-stack').evaluate((element) =>
    element.getBoundingClientRect().top + window.scrollY,
  );
  await page.evaluate((position) => window.scrollTo({ top: position, behavior: 'instant' }), start + 400);
  await expect.poll(async () => (await cards.nth(1).boundingBox())!.y).toBeLessThan(150);
  const stacked = await cards.first().evaluate((element) => getComputedStyle(element).transform);
  await expect(page.locator('#about')).toHaveCSS('opacity', '1');
  for (const card of await page.locator('#about .benefit-card').all())
    await expect(card).toHaveCSS('opacity', '1');
  await page.screenshot({ path: 'test-results/scroll-story-desktop.png' });
  await page.evaluate((position) => window.scrollTo({ top: position - 200, behavior: 'instant' }), start);
  await expect.poll(() => cards.first().evaluate((element) => getComputedStyle(element).transform)).not.toBe(stacked);
  await page.getByRole('link', { name: 'FAQ', exact: true }).click();
  await expect(page).toHaveURL(/#faq/);
  await expect(page.locator('#faq h2')).toBeInViewport();
});

test('mobile and reduced motion keep feature cards in ordinary document flow', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  for (const card of await page.locator('.scroll-stack-card').all()) {
    await expect(card).toHaveCSS('position', 'relative');
    await expect(card).toHaveCSS('transform', 'none');
  }
  await page.setViewportSize({ width: 320, height: 800 });
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  for (const card of await page.locator('.scroll-stack-card').all())
    await expect(card).toHaveCSS('position', 'relative');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
