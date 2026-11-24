/* Screenshots for the docs: the browser notebook page on the two sandbox notebooks.
   node shoot.mjs REPO OUTDIR */
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');
const [REPO, OUT] = process.argv.slice(2);
const DOCS = path.join(REPO, 'docs');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.md': 'text/markdown',
  '.png': 'image/png', '.webmanifest': 'application/manifest+json', '.json': 'application/json', '.yaml': 'text/yaml' };
const server = http.createServer((req, res) => {
  let rel = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  if (rel.endsWith('/')) rel += 'index.html';
  const file = path.join(DOCS, rel);
  if (!file.startsWith(DOCS) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) return res.writeHead(404).end('not found');
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' }).end(fs.readFileSync(file));
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${server.address().port}`;

function walk(dir, prefix = '') {
  const out = {};
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name === '__pycache__') continue;
    if (e.isDirectory()) Object.assign(out, walk(path.join(dir, e.name), prefix + e.name + '/'));
    else out[prefix + e.name] = fs.readFileSync(path.join(dir, e.name)).toString('base64');
  }
  return out;
}
const files = { ...walk(path.join(REPO, 'sandbox', 'alex'), 'alex/'), ...walk(path.join(REPO, 'sandbox', 'jordan'), 'jordan/') };

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1180, height: 1010 }, deviceScaleFactor: 2, colorScheme: 'light', serviceWorkers: 'block' });
const page = await context.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(String(e)));
const lab = 'Lab notebooks';
await page.goto(`${base}/app/`);
await page.evaluate(async ({ root, files }) => {
  const top = await navigator.storage.getDirectory();
  for (const [p, b64] of Object.entries(files)) {
    let dir = await top.getDirectoryHandle(root, { create: true });
    const parts = p.split('/');
    for (const part of parts.slice(0, -1)) dir = await dir.getDirectoryHandle(part, { create: true });
    const w = await (await dir.getFileHandle(parts[parts.length - 1], { create: true })).createWritable();
    await w.write(Uint8Array.from(atob(b64), (c) => c.charCodeAt(0)));
    await w.close();
  }
  localStorage.removeItem('ai-eln-person');
  localStorage.setItem('ai-eln-theme', 'light');
}, { root: lab, files });
const settle = async () => { await page.waitForFunction(() => !document.querySelector('#main').hasAttribute('aria-busy')); await page.waitForTimeout(250); };
const open = async (hash) => { await page.evaluate((h) => { location.hash = h; }, hash); await page.waitForTimeout(200); await settle(); };
const shot = async (name, height) => { await page.mouse.move(1170, 5); await page.waitForTimeout(150); return page.screenshot({ path: path.join(OUT, name), clip: { x: 0, y: 0, width: 1180, height } }); };

await page.goto(`${base}/app/?store=opfs&name=${encodeURIComponent(lab)}`);
await page.waitForSelector('text=holds 2 notebooks');
await settle();
await shot('notebooks.png', 560);
await page.locator('a.tile', { hasText: 'Alex Example' }).click();
await page.waitForSelector('text=Recent experiments');
await settle();
await shot('home.png', 1010);
await open('#/new/experiment');
await page.fill('#n-title', 'SNRPB chromatin retention after PRMT5 inhibition: KCl titration');
await page.fill('#n-project', 'PRMT5-ChromatinRelease');
await page.fill('#n-type', 'Fractionation, WesternBlot');
await page.fill('#n-protocol', 'P_CellularFractionation, P_WesternBlot');
await page.fill('#n-notebook', 'NB03-066');
await page.check('input[name="samples"][value="ALXc0001"]');
await page.check('input[name="samples"][value="ALXa0001"]');
await page.evaluate(() => document.activeElement && document.activeElement.blur());
await shot('new-experiment.png', 800);
await open('#/note/ALXe0002');
await page.waitForFunction(() => { const i = document.querySelector('#note-body img'); return i && i.naturalWidth > 0; });
const noteHeight = await page.evaluate(() => document.documentElement.scrollHeight);
await page.setViewportSize({ width: 1180, height: Math.min(noteHeight, 1760) });
await shot('note.png', Math.min(noteHeight, 1760));
await page.setViewportSize({ width: 1180, height: 1010 });
await open('#/adopt');
await shot('adopt.png', 640);
console.log(errors.length ? 'errors: ' + errors.join(' | ') : 'ok', 'note height', noteHeight);
await browser.close();
server.close();
