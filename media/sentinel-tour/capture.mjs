import { chromium } from '../../frontend/node_modules/playwright-core/index.mjs';
import fs from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const scenes = JSON.parse(await fs.readFile(new URL('./scenes.json', import.meta.url), 'utf8'));
await fs.mkdir(new URL('./assets', import.meta.url), { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, reducedMotion: 'reduce' });
await page.addInitScript(() => { localStorage.setItem('sentinel.theme', 'light'); localStorage.setItem('sentinel.motion', 'reduce'); });
const captured = [];
for (const scene of scenes) {
  await page.goto(`http://127.0.0.1:5190${scene.route}`);
  await page.locator('h1').waitFor();
  await page.waitForFunction(() => !document.querySelector('.skeleton'));
  await page.waitForTimeout(550);
  await page.screenshot({ path: fileURLToPath(new URL(`./assets/${scene.image}.png`, import.meta.url)) });
  captured.push({ route: scene.route, title: await page.locator('h1').innerText(), text: (await page.locator('main').innerText()).slice(0, 3000) });
}
await fs.writeFile(new URL('./capture/source-pages.json', import.meta.url), JSON.stringify(captured, null, 2));
await browser.close();
console.log(`Captured ${captured.length} real frontend screens.`);
