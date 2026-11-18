import fs from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
const scenes = JSON.parse(await fs.readFile('scenes.json', 'utf8'));
const spoken = [
  'Sentinel A I turns sample application errors into evidence and reviewable fixes. This walkthrough uses simulated data.',
  'The Manager coordinates every handoff. Visit A I Agents to explore each role and its activity.',
  'Monitoring recognizes supported errors in sample logs. Applications shows sample health and monitoring controls.',
  'Diagnosis explains a likely cause with source evidence. Check the cited file, lines, and revision.',
  'Repair proposes a focused change. Compare the exact diff with the original before deciding.',
  'Testing checks that exact candidate. Repair and Testing shows results. Failed or missing checks block approval.',
  'You approve or reject in Approval and Recovery. Applying requires separate confirmation. Verification checks the outcome.',
  'Reporting records decisions, tests, and recovery outcomes, including failures and unresolved issues. No success is assumed.',
  'The Dashboard summarizes application health, incident counts, and pending reviews. Open recent incidents to investigate.',
  'Search and filter in Incidents. Open an issue for its overview, diagnosis, patch, tests, timeline, and report.',
  'Incident History keeps closed examples easy to revisit, including rejected, resolved, and unresolved outcomes.',
  'Settings controls appearance, motion, and refresh preferences. Documentation explains boundaries and links to features.',
  'Start the introduction for orientation, or practice decisions in the interactive demo. No real code is executed.',
];
scenes.forEach((scene, i) => { scene.narration = spoken[i]; });
await fs.writeFile('scenes.json', JSON.stringify(scenes, null, 2));
await fs.mkdir('assets/fonts', { recursive: true });
await fs.mkdir('compositions', { recursive: true });
await fs.copyFile('node_modules/gsap/dist/gsap.min.js', 'assets/gsap.min.js');
await fs.copyFile('C:/Windows/Fonts/segoeui.ttf', 'assets/fonts/segoeui.ttf');
await fs.copyFile('C:/Windows/Fonts/seguisb.ttf', 'assets/fonts/seguisb.ttf');
execFileSync('powershell', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'narrate.ps1'], { stdio: 'inherit' });

function wavDuration(bytes) {
  let rate = 0, size = 0;
  for (let offset = 12; offset + 8 <= bytes.length;) {
    const type = bytes.toString('ascii', offset, offset + 4), length = bytes.readUInt32LE(offset + 4);
    if (type === 'fmt ') rate = bytes.readUInt32LE(offset + 16);
    if (type === 'data') size = length;
    offset += 8 + length + length % 2;
  }
  if (!rate || !size) throw new Error('Invalid narration WAV');
  return size / rate;
}
const escape = (text) => text.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');
const stamp = (value) => { const ms = Math.round(value * 1000); return `${String(Math.floor(ms / 3600000)).padStart(2, '0')}:${String(Math.floor(ms / 60000) % 60).padStart(2, '0')}:${String(Math.floor(ms / 1000) % 60).padStart(2, '0')}.${String(ms % 1000).padStart(3, '0')}`; };
let cursor = 0;
for (const scene of scenes) {
  scene.voiceDuration = wavDuration(await fs.readFile(`assets/voice-${scene.id}.wav`));
  scene.duration = Math.ceil((scene.voiceDuration + 1.2) * 100) / 100;
  scene.start = Math.round(cursor * 100) / 100;
  cursor += scene.duration - 0.4;
}
const total = Math.round((cursor + 0.4) * 100) / 100;
const style = `
@font-face{font-family:TourUI;src:url('assets/fonts/segoeui.ttf')}@font-face{font-family:TourUI;src:url('assets/fonts/seguisb.ttf');font-weight:700}
*{box-sizing:border-box;margin:0}#root{width:1920px;height:1080px;color:#10172f;font-family:TourUI,sans-serif}
.scene-body{width:100%;height:100%;padding:64px 96px;background:#f7f9fc;display:flex;flex-direction:column;gap:28px}
.scene-header{display:flex;justify-content:space-between;align-items:center;min-height:48px;font-size:30px;font-weight:700;letter-spacing:-.6px}.disclosure{font-size:28px;font-weight:400;color:#526078;letter-spacing:0}
.scene-main{flex:1;min-height:0;display:grid;grid-template-columns:480px minmax(0,1fr);gap:64px;align-items:center}
.scene-copy{display:flex;flex-direction:column;gap:30px}.eyebrow{font-size:30px;letter-spacing:1.5px;color:var(--role);font-weight:700;line-height:1.4}
h1{font-size:66px;line-height:1.08;letter-spacing:-2px;font-weight:700;max-width:480px}.scene-note{font-size:32px;line-height:1.45;max-width:460px;color:#526078}
.bds-device{border:1px solid #e3eaf3;border-radius:22px;padding:8px;background:#ffffff;box-shadow:0 18px 48px -24px #1261d84a;overflow:hidden}
.bds-bar{height:46px;display:flex;align-items:center;padding:0 18px;color:#526078;font-size:30px;border-bottom:1px solid #e3eaf3;margin-bottom:8px}
.screen-viewport{aspect-ratio:1.6;overflow:hidden;border-radius:10px;background:#ffffff}.screen-image{display:block;width:100%;height:100%;object-fit:contain;transform-origin:center}
.scene-footer{display:flex;justify-content:space-between;gap:24px;min-height:34px;font-size:28px;color:#526078;line-height:1.3}.scene-footer span:first-child{max-width:1420px;overflow-wrap:anywhere}.scene-footer strong{color:var(--role)}
`;
for (let i = 0; i < scenes.length; i++) {
  const s = scenes[i], id = s.id;
  const html = `<!doctype html><html lang="en"><body><template><div id="root" data-composition-id="${id}" data-start="0" data-duration="${s.duration}" data-width="1920" data-height="1080" style="--role:${s.color}">
<style>${style}</style>
<div class="scene-body" id="${id}-body">
<header class="scene-header"><span>SENTINEL <span style="color:#1261d8">AI</span></span><span class="disclosure">Local prototype · Simulated data</span></header>
<main class="scene-main"><div class="scene-copy"><p class="eyebrow" id="${id}-label">${escape(s.label)}</p><h1 id="${id}-title">${escape(s.title)}</h1><p class="scene-note" id="${id}-note">${escape(s.note)}</p></div>
<!-- Browser chrome adapted from the installed browser-device-stage registry component. -->
<div class="bds-device" id="${id}-frame"><div class="bds-bar">${escape(s.route)}</div><div class="screen-viewport" data-layout-allow-overflow><img id="${id}-screen" class="screen-image" src="assets/${s.image}.png" alt="Captured SENTINEL AI ${s.title}" /></div></div></main>
<footer class="scene-footer"><span>${escape(s.note)}</span><strong>${i + 1} / ${scenes.length}</strong></footer></div>
<script>
const tl=gsap.timeline({paused:true});
tl.fromTo('#${id}-body',{opacity:${id === 'intro' ? 1 : 0}},{opacity:1,duration:.4,ease:'power2.out'},0);
tl.fromTo('#${id}-label',{opacity:0,y:12},{opacity:1,y:0,duration:.4,ease:'power2.out'},.2);
tl.fromTo('#${id}-title',{opacity:0,x:-24},{opacity:1,x:0,duration:.6,ease:'power3.out'},.3);
tl.fromTo('#${id}-frame',{opacity:0,y:24,scale:.99},{opacity:1,y:0,scale:1,duration:.65,ease:'expo.out'},.25);
tl.fromTo('#${id}-note',{opacity:0,y:10},{opacity:1,y:0,duration:.45,ease:'sine.out'},.65);
tl.to('#${id}-screen',{scale:1.025,duration:${Math.max(1, s.duration - 1)},ease:'sine.inOut'},.8);
window.__timelines=window.__timelines||{};window.__timelines['${id}']=tl;
</script></div></template></body></html>`;
  await fs.writeFile(`compositions/${id}.html`, html);
}
const hosts = scenes.map((s, i) => `<div id="scene-${s.id}" class="clip" data-composition-id="${s.id}" data-composition-src="compositions/${s.id}.html" data-start="${s.start}" data-duration="${s.duration}" data-track-index="${i % 2}" data-track-kind="graphics" style="position:absolute;inset:0;z-index:${i + 1}"></div>`).join('\n');
const audio = scenes.map((s) => `<audio id="voice-${s.id}" class="clip" src="assets/voice-${s.id}.wav" data-start="${(s.start + .45).toFixed(2)}" data-duration="${s.voiceDuration.toFixed(3)}" data-track-index="2" data-volume="1"></audio>`).join('\n');
await fs.writeFile('index.html', `<!doctype html><html lang="en"><head><meta charset="UTF-8"><title>SENTINEL AI · Agent and workspace tour</title><script src="assets/gsap.min.js"></script><style>*{box-sizing:border-box}html,body{margin:0;width:1920px;height:1080px;overflow:hidden;background:#f7f9fc}#root{position:relative;width:1920px;height:1080px}.clip{position:absolute;inset:0}</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="${total}" data-width="1920" data-height="1080" data-fps="30">${hosts}\n${audio}</div><script>window.__timelines=window.__timelines||{};window.__timelines.main=gsap.timeline({paused:true});</script></body></html>`);
await fs.writeFile('SCRIPT.md', '# Narration\n\n' + scenes.map((s) => `## ${s.title}\n${s.narration}`).join('\n\n'));
await fs.writeFile('narration.txt', scenes.map((s) => s.narration).join('\n\n'));
await fs.writeFile('STORYBOARD.md', `# ${total}-second product walkthrough\n\nVoice: local Microsoft Zira Desktop. Timings measured from generated WAV data, not estimates. Each scene uses a real captured route, a 0.4s overlapping dissolve, staggered title/frame entrances, and a 2.5% screenshot push. No music, to keep instructional speech clear.\n\n` + scenes.map((s) => `- ${s.start.toFixed(2)}–${(s.start+s.duration).toFixed(2)}s: ${s.title}; assets/${s.image}.png; assets/voice-${s.id}.wav; route ${s.route}`).join('\n'));
await fs.writeFile('SPEC.md', `GOAL: Understand all six roles and know where to review evidence and decisions.\nOUTPUT: 1920×1080, 30fps, ${total}s.\nLOOK: DESIGN.md; 66px headings, 32px explanations, 24px disclosure.\nSAFE: 96px horizontal and 64px vertical padding. Screenshot is the main subject.\nMOTION: 0.4s dissolves, 0.4–0.65s entrances, 2.5% screenshot camera push.\nBANNED: invented metrics, fake controls, production claims, automated approval, stock imagery.\n`);
await fs.writeFile('transcript.json', JSON.stringify(scenes.map((s) => ({text:s.narration,start:s.start+.45,end:s.start+.45+s.voiceDuration})),null,2));
await fs.writeFile('tour.vtt', 'WEBVTT\n\n' + scenes.map((s,i) => `${i+1}\n${stamp(s.start+.45)} --> ${stamp(s.start+.45+s.voiceDuration)}\n${s.narration}\n`).join('\n'));
await fs.writeFile('chapters.json', JSON.stringify(scenes.map((s)=>({title:s.title,start:s.start})),null,2));
await fs.writeFile('timing.json', JSON.stringify({duration:total,scenes},null,2));
console.log(`Built ${scenes.length} scenes; duration ${total}s; ${spoken.join(' ').split(/\s+/).length} spoken words.`);

