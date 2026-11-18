import fs from 'node:fs';
const report = JSON.parse(fs.readFileSync(process.argv[2] || 'check-result.json', 'utf8'));
console.log('ok:', report.ok);
for (const [name, section] of Object.entries(report)) {
  if (!section || !Array.isArray(section.findings)) continue;
  const groups = new Map();
  for (const finding of section.findings) {
    const key = `${finding.severity}:${finding.code}`;
    if (!groups.has(key)) groups.set(key, { count: 0, example: finding.message });
    groups.get(key).count++;
  }
  console.log(name, JSON.stringify(Object.fromEntries(groups)));
}
