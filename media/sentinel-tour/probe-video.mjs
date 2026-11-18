import { chromium } from '../../frontend/node_modules/playwright-core/index.mjs';
for (const channel of [undefined, 'chrome']) {
  const browser = await chromium.launch({ headless:true, ...(channel ? {channel} : {}) });
  const page = await browser.newPage({viewport:{width:1440,height:1100},reducedMotion:'reduce'});
  await page.goto('http://127.0.0.1:5190/');
  const video = page.locator('video');
  await video.waitFor();
  await page.waitForTimeout(2500);
  console.log(channel || 'chromium', await video.evaluate((v)=>({ready:v.readyState,network:v.networkState,duration:v.duration,error:v.error?.message,code:v.error?.code,currentSrc:v.currentSrc,mp4:v.canPlayType('video/mp4; codecs="avc1.64001f, mp4a.40.2"')})));
  if (!channel) {
    await page.locator('.product-tour-video').screenshot({path:'../../frontend/docs/screenshots/product-tour-player-1440.png'});
    await page.setViewportSize({width:320,height:900});
    await page.locator('.product-tour-video').screenshot({path:'../../frontend/docs/screenshots/product-tour-player-320.png'});
  }
  await browser.close();
}
