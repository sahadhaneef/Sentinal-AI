import fs from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const base = new URL('../../frontend/', import.meta.url);
const timing = JSON.parse(await fs.readFile(new URL('./timing.json', import.meta.url), 'utf8'));
await fs.mkdir(new URL('public/media/', base), {recursive:true});
if (!process.argv.includes('--metadata-only')) {
  await fs.copyFile(new URL('./renders/sentinel-tour-web.mp4', import.meta.url), new URL('public/media/sentinel-tour.mp4', base));
  await fs.copyFile(new URL('./tour.vtt', import.meta.url), new URL('public/media/sentinel-tour.vtt', base));
  await fs.copyFile(new URL('./poster.jpg', import.meta.url), new URL('public/media/sentinel-tour-poster.jpg', base));
}
const chapters = timing.scenes.map(({id,title,start,narration})=>({id,title,start,narration}));
await fs.writeFile(new URL('src/content/videoTour.ts', base), `// Generated from media/sentinel-tour/timing.json. Keep captions and chapters in sync.\nexport const tourDuration = ${timing.duration};\nexport const tourChapters = ${JSON.stringify(chapters,null,2)} as const;\n`);
console.log(`Published the video, captions, poster and ${chapters.length} chapters to ${fileURLToPath(base)}.`);
