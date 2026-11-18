import { test, expect } from '@playwright/test';

test('theme toggle updates the globe shader and landing surfaces even with motion reduced', async ({ page }) => {
  test.setTimeout(60000);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.addInitScript(() => localStorage.setItem('sentinel.theme', 'dark'));
  await page.goto('/');
  const canvas = page.locator('.planet-canvas');
  await expect(canvas).toHaveAttribute('data-renderer', 'webgl');
  const mode = () => canvas.evaluate((element) => {
    const gl = (element as HTMLCanvasElement).getContext('webgl')!;
    const program = gl.getParameter(gl.CURRENT_PROGRAM) as WebGLProgram;
    return Number(gl.getUniform(program, gl.getUniformLocation(program, 'lightMode')!));
  });
  await expect.poll(mode).toBe(0);
  await expect(page.locator('.landing-atmosphere')).toHaveCSS('background-color', 'rgb(6, 13, 29)');
  const dark = await canvas.evaluate((element) => (element as HTMLCanvasElement).toDataURL());
  await page.getByRole('button', { name: 'Toggle theme' }).click();
  await expect.poll(mode).toBe(1);
  await expect(page.locator('.landing-atmosphere')).toHaveCSS('background-color', 'rgb(247, 249, 252)');
  await expect(page.locator('.product-visual')).toHaveCSS('background-color', 'rgb(255, 255, 255)');
  expect(await canvas.evaluate((element) => (element as HTMLCanvasElement).toDataURL())).not.toBe(dark);
  await page.screenshot({ path: 'test-results/planet-theme-light.png' });
  await page.getByRole('button', { name: 'Toggle theme' }).click();
  await expect.poll(mode).toBe(0);
  await expect(page.locator('.product-visual')).toHaveCSS('background-color', 'rgb(17, 32, 57)');
  await page.screenshot({ path: 'test-results/planet-theme-dark.png' });
});

test('landing background runs automatically without blocking content and is absent from the workspace', async ({
  page,
}) => {
  test.setTimeout(60000);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.goto('/');
  const background = page.locator('.landing-atmosphere');
  await expect(background).toHaveAttribute('aria-hidden', 'true');
  await expect(background).toHaveCSS('pointer-events', 'none');
  await expect(page.getByRole('button', { name: /background animation/ })).toHaveCount(0);
  await expect(page.locator('.agent-signal-backdrop')).toHaveCount(0);
  const field = page.locator('.planet-canvas');
  await expect(field).toHaveAttribute('data-renderer', 'webgl');
  const initial = await field.evaluate((element) => (element as HTMLCanvasElement).toDataURL());
  await expect.poll(() => field.evaluate((element) => (element as HTMLCanvasElement).toDataURL())).not.toBe(initial);
  const spotlight = page.locator('.hero-cursor-light');
  const hero = await page.locator('.hero-scene').boundingBox();
  await page.mouse.move(hero!.x + 180, hero!.y + 180);
  await expect(spotlight).toHaveCSS('opacity', '1');
  const position = await spotlight.evaluate((element) => getComputedStyle(element).transform);
  await page.mouse.move(hero!.x + 500, hero!.y + 240);
  await expect.poll(() => spotlight.evaluate((element) => getComputedStyle(element).transform)).not.toBe(position);
  await page.mouse.move(0, 0);
  await expect(spotlight).toHaveCSS('opacity', '0');
  await expect(page.locator('.hero-preview-shell .visual-human')).toHaveCSS('opacity', '1');
  await page.screenshot({ path: 'test-results/atmosphere-hero-light.png' });
  await page.locator('#platform').scrollIntoViewIfNeeded();
  await expect.poll(() => field.evaluate((element) => {
    const gl = (element as HTMLCanvasElement).getContext('webgl')!;
    const program = gl.getParameter(gl.CURRENT_PROGRAM) as WebGLProgram;
    return Number(gl.getUniform(program, gl.getUniformLocation(program, 'progress')!));
  })).toBeGreaterThan(0.4);
  await expect.poll(() => field.evaluate((element) => (element as HTMLCanvasElement).toDataURL())).not.toBe(initial);
  await expect(page.locator('#platform')).toHaveCSS('opacity', '1');
  await expect(page.locator('.workspace-tile-slot').last()).toHaveCSS('opacity', '1');
  await page
    .locator('#platform')
    .screenshot({ path: 'test-results/atmosphere-workspace-light.png' });
  await page.getByRole('button', { name: 'Toggle theme' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.screenshot({ path: 'test-results/atmosphere-hero-dark.png' });
  await page.getByRole('link', { name: 'Get Started', exact: true }).click();
  await expect(page).toHaveURL(/onboarding/);
  await expect(background).toHaveCount(0);
});

test('a static planet remains visible when WebGL is unavailable', async ({ page }) => {
  await page.addInitScript(() => {
    const getContext = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (this: HTMLCanvasElement, ...args: Parameters<typeof getContext>) {
      if (String(args[0]).includes('webgl')) return null;
      return getContext.apply(this, args);
    } as typeof getContext;
  });
  await page.goto('/');
  await expect(page.locator('.planet-canvas')).toHaveAttribute('data-renderer', 'fallback');
  await expect(page.locator('.planet-fallback')).toBeVisible();
  await page.getByRole('link', { name: 'Get Started', exact: true }).click();
  await expect(page).toHaveURL(/onboarding/);
});

test('mobile background stays static with reduced motion and preserves viewport width', async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 900 });
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await expect(page.locator('.hero-cursor-light')).toHaveCSS('display', 'none');
  await expect(page.getByRole('button', { name: /background animation/ })).toHaveCount(0);
  const field = page.locator('.planet-canvas');
  const initial = await field.evaluate((element) => (element as HTMLCanvasElement).toDataURL());
  await page.waitForTimeout(200);
  expect(await field.evaluate((element) => (element as HTMLCanvasElement).toDataURL())).toBe(initial);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/atmosphere-hero-320.png' });
});
