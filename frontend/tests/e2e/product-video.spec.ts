import { test, expect } from '@playwright/test';

test('product video loads, plays, seeks by chapter and provides captions and transcript', async ({
  page,
}) => {
  await page.goto('/');
  const video = page.locator('.product-tour-video video');
  await video.scrollIntoViewIfNeeded();
  const chapters = page.getByRole('combobox', { name: 'Video chapter' });
  await expect(chapters).toBeEnabled({ timeout: 15000 });
  const metadata = await video.evaluate((element: HTMLVideoElement) => ({
    duration: element.duration,
    paused: element.paused,
    autoPlay: element.autoplay,
  }));
  expect(metadata.duration).toBeGreaterThan(93);
  expect(metadata.duration).toBeLessThan(96);
  expect(metadata.paused).toBe(true);
  expect(metadata.autoPlay).toBe(false);
  await chapters.selectOption('1');
  await expect
    .poll(() => video.evaluate((element: HTMLVideoElement) => element.currentTime))
    .toBeGreaterThan(7);
  await video.evaluate(async (element: HTMLVideoElement) => {
    element.muted = true;
    await element.play();
  });
  await expect
    .poll(() => video.evaluate((element: HTMLVideoElement) => element.currentTime))
    .toBeGreaterThan(8);
  await video.evaluate((element: HTMLVideoElement) => element.pause());
  await expect
    .poll(() =>
      video.evaluate((element: HTMLVideoElement) => element.textTracks[0]?.cues?.length ?? 0),
    )
    .toBe(13);
  await page.getByText('Read the video transcript', { exact: true }).click();
  const transcript = page.locator('.tour-video-transcript');
  await expect(transcript).toContainText('The Manager coordinates every handoff');
  await expect(transcript).toContainText('Applying requires separate confirmation');
  await expect(transcript).toContainText('Settings controls appearance');
  await expect(
    page.getByRole('link', { name: 'Open the interactive walkthrough' }),
  ).toHaveAttribute('href', '/demo');
});

test('video transcript remains useful if media cannot be downloaded', async ({ page }) => {
  await page.route('**/media/sentinel-tour.mp4', (route) => route.abort());
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto('/');
  await page.getByText('Read the video transcript', { exact: true }).click();
  await expect(page.locator('.tour-video-transcript')).toContainText('No real code is executed');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
