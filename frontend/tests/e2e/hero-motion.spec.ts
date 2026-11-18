import { test, expect } from '@playwright/test';

test('agent color flow runs automatically with distinct role palettes and keyboard details', async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1200 });
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.goto('/');
  const team = page.locator('#team');
  await team.scrollIntoViewIfNeeded();
  const cards = team.locator('.public-agent');
  await expect(cards).toHaveCount(6);
  const colors = await cards.evaluateAll((items) =>
    items.map((item) => getComputedStyle(item).getPropertyValue('--flow-a').trim()),
  );
  expect(new Set(colors).size).toBe(6);
  await expect(team.locator('.agent-color-flow').first()).toHaveCSS(
    'animation-play-state',
    'running',
  );
  await expect(team.getByRole('button', { name: /agent color flow/ })).toHaveCount(0);
  const flow = team.locator('.agent-color-flow').first();
  const firstTransform = await flow.evaluate((element) => getComputedStyle(element).transform);
  await expect.poll(() => flow.evaluate((element) => getComputedStyle(element).transform))
    .not.toBe(firstTransform);
  const summary = cards.first().locator('summary');
  await summary.focus();
  await page.keyboard.press('Enter');
  await expect(cards.first().locator('details')).toHaveAttribute('open', '');
  await expect(cards.first()).toContainText('Coordinates typed handoffs');
  await page.mouse.move(0, 0);
  await team.screenshot({ path: 'test-results/agent-color-flow-light.png' });
  await expect(team.locator('.agent-color-flow').first()).toHaveCSS(
    'animation-play-state',
    'running',
  );
  await page.getByRole('button', { name: 'Toggle theme' }).click();
  await team.scrollIntoViewIfNeeded();
  await team.screenshot({ path: 'test-results/agent-color-flow-dark.png' });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  for (const flow of await team.locator('.agent-color-flow').all())
    await expect(flow).toHaveCSS('animation-name', 'none');
  await cards.first().hover();
  await expect(cards.first()).toHaveCSS('transform', 'none');
});

test('workflow depth preserves keyboard stage selection and reduced motion', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.goto('/');
  const panel = page.locator('.workflow-section');
  await panel.scrollIntoViewIfNeeded();
  await page.mouse.move(0, 0);
  await expect
    .poll(() => panel.evaluate((element) => new DOMMatrix(getComputedStyle(element).transform).m42))
    .toBe(0);
  const rest = await panel.evaluate((element) => getComputedStyle(element).transform);
  const heading = (await panel.locator('h2').boundingBox())!;
  await page.mouse.move(heading.x + 20, heading.y + 20);
  await expect
    .poll(() => panel.evaluate((element) => getComputedStyle(element).transform))
    .not.toBe(rest);
  const diagnose = panel.getByRole('button', { name: /Diagnose/ });
  await diagnose.hover();
  await diagnose.focus();
  await page.keyboard.press('Enter');
  await expect(diagnose).toHaveAttribute('aria-pressed', 'true');
  await expect(panel.locator('.stage-explainer')).toContainText('Diagnosis Agent');
  await panel.screenshot({ path: 'test-results/workflow-depth-light.png' });
  await page.getByRole('button', { name: 'Toggle theme' }).click();
  await panel.scrollIntoViewIfNeeded();
  await panel.screenshot({ path: 'test-results/workflow-depth-dark.png' });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await expect(panel).toHaveCSS('transform', 'none');
  const report = panel.getByRole('button', { name: /Report/ });
  await report.focus();
  await page.keyboard.press('Enter');
  await expect(report).toHaveAttribute('aria-pressed', 'true');
  await expect(report).toHaveCSS('transform', 'none');
  await expect(panel.locator('.stage-explainer')).toContainText('Reporting Agent');
});

test('hero card and buttons respond to the pointer and settle after leaving', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.goto('/');
  const card = page.locator('.hero-preview-shell');
  await expect(card).toBeVisible();
  const restingTransform = await card.evaluate((element) => getComputedStyle(element).transform);
  const box = await card.boundingBox();
  expect(box).not.toBeNull();
  await page.mouse.move(box!.x + box!.width * 0.8, box!.y + box!.height * 0.3);
  await expect
    .poll(() => card.evaluate((element) => getComputedStyle(element).transform))
    .not.toBe(restingTransform);
  await page.mouse.move(0, 0);
  await expect
    .poll(() => card.evaluate((element) => getComputedStyle(element).transform))
    .toBe(restingTransform);

  const start = page.getByRole('link', { name: 'Get Started', exact: true });
  await start.hover();
  await expect
    .poll(() => start.evaluate((element) => getComputedStyle(element).transform))
    .not.toBe('none');
  await start.focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/onboarding/);
});

test('reduced motion keeps the hero steady and the demo button usable', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  const card = page.locator('.hero-preview-shell');
  await card.hover();
  await expect(card).toHaveCSS('transform', 'none');
  const demo = page.getByRole('link', { name: 'Explore Interactive Demo', exact: true });
  await demo.hover();
  await expect(demo).toHaveCSS('transform', 'none');
  await demo.click();
  await expect(page).toHaveURL(/demo/);
});

test('feature cards have distinct colors, signal motion and readable depth in both themes', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.goto('/');
  const card = page.locator('.benefit-card').first();
  await card.scrollIntoViewIfNeeded();
  await page.mouse.move(0, 0);
  await expect(card).toHaveCSS('transform', 'none');
  const colors = await page.locator('.benefit-signal').evaluateAll((cards) =>
    cards.map((item) => getComputedStyle(item).getPropertyValue('--benefit-color').trim()),
  );
  expect(new Set(colors).size).toBe(4);
  await expect
    .poll(() => card.evaluate((element) => new DOMMatrix(getComputedStyle(element).transform).m42))
    .toBe(0);
  const rest = await card.evaluate((element) => getComputedStyle(element).transform);
  const box = (await card.boundingBox())!;
  await page.mouse.move(box.x + box.width * 0.8, box.y + box.height * 0.3);
  await expect
    .poll(() => card.evaluate((element) => getComputedStyle(element).transform))
    .not.toBe(rest);
  await page.locator('#about').screenshot({ path: 'test-results/feature-cards-3d-light.png' });
  await page.mouse.move(0, 0);
  await expect
    .poll(() => card.evaluate((element) => getComputedStyle(element).transform))
    .toBe(rest);
  await page.getByRole('button', { name: 'Toggle theme' }).click();
  await page.locator('#about').scrollIntoViewIfNeeded();
  await page.locator('#about').screenshot({ path: 'test-results/feature-cards-3d-dark.png' });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  for (const feature of await page.locator('.benefit-card').all()) {
    await feature.hover();
    await expect(feature).toHaveCSS('transform', 'none');
    expect(await feature.locator('.feature-icon').evaluate((icon) =>
      getComputedStyle(icon, '::after').animationName,
    )).toBe('none');
  }
});
