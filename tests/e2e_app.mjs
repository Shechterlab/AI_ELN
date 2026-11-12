/* Drive the browser notebook (docs/app/) in headless Chromium, the way a person would.

     node tests/e2e_app.mjs [--dump DIR] [--shots DIR]

   The folder picker cannot be automated, so the page is opened with ?store=opfs: a private folder
   inside the browser that has the same interface as a picked folder (the same FsAccessStore code runs).
   --dump writes the resulting notebook to DIR so the Python validator can check it.
   Needs the `playwright` package and its Chromium. Prints one line per step; exits 1 on any failure. */

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const { chromium } = createRequire(import.meta.url)('playwright');
const DOCS = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'docs');
const args = process.argv.slice(2);
const flag = (name) => (args.includes(name) ? args[args.indexOf(name) + 1] : '');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.md': 'text/markdown',
  '.png': 'image/png', '.webmanifest': 'application/manifest+json', '.json': 'application/json' };

const server = http.createServer((req, res) => {
  let rel = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  if (rel.endsWith('/')) rel += 'index.html';
  const file = path.join(DOCS, rel);
  if (!file.startsWith(DOCS) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404).end('not found');
    return;
  }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(file)] || 'application/octet-stream' }).end(fs.readFileSync(file));
});
await new Promise((r) => server.listen(0, '127.0.0.1', r));
const base = `http://127.0.0.1:${server.address().port}`;

const failures = [];
let step = 0;
function check(label, ok, detail = '') {
  step += 1;
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${String(step).padStart(2)} ${label}${ok || !detail ? '' : ' -> ' + detail}`);
  if (!ok) failures.push(label);
}

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
const page = await context.newPage();
const errors = [];
page.on('pageerror', (e) => errors.push(String(e)));
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
const shot = async (name) => { if (flag('--shots')) await page.screenshot({ path: path.join(flag('--shots'), `${name}.png`), fullPage: true }); };
const text = async (sel = '#main') => (await page.textContent(sel)) || '';
const settle = () => page.waitForFunction(() => !document.querySelector('#main').hasAttribute('aria-busy'));
const click = async (name) => { await page.getByRole('button', { name, exact: true }).click(); await settle(); };
const open = async (hash) => { await page.evaluate((h) => { location.hash = h; }, hash); await page.waitForTimeout(150); await settle(); };

const name = `e2e-${Date.now()}`;
await page.goto(`${base}/app/?store=opfs&name=${name}`);
await page.waitForSelector('text=Set up a notebook in');
check('an empty folder offers to set up a notebook', (await text()).includes('The folder is empty'));
await click('Set up the notebook here');
check('home asks for initials on first use', (await text()).includes('First time here'));

await open('#/settings');
await page.fill('#s-initials', 'jsr');
await page.fill('#s-name', 'Jacob Roth');
await click('Save');
check('settings are saved', (await text()).includes('Jacob Roth (JSR)'));

await open('#/new/project');
await page.fill('#n-id', 'PRMT5-ChromatinRelease');
await page.fill('#n-title', 'PRMT5 and chromatin release');
await click('Create project');
check('project created', (await text('h1')).includes('PRMT5-ChromatinRelease'));

await open('#/new/protocol');
await page.fill('#n-name', 'WesternBlot');
await click('Create protocol');
check('protocol created', (await text('h1')).includes('P_WesternBlot'));

await open('#/new/sample');
await page.selectOption('#n-stype', 'antibody');
await page.fill('#n-title', 'anti-SNRPB (Y12)');
await page.fill('#n-source', 'in-house, lot 3');
await page.fill('#n-storage', 'Fridge 2, door');
await click('Create sample');
check('sample gets the next ID for its type', (await text('h1')).includes('JSRa0001'));

await open('#/new/experiment');
await page.fill('#n-title', 'SNRPB chromatin retention: KCl titration');
await page.fill('#n-project', 'PRMT5-ChromatinRelease');
await page.fill('#n-type', 'WesternBlot');
await page.fill('#n-protocol', 'P_WesternBlot');
await page.check('input[name="samples"][value="JSRa0001"]');
await page.check('input[name="meeting"]');
await click('Create experiment');
let body = await text();
check('experiment created with ID, folder and protocol copy',
  (await text('h1')).includes('JSRe0001') && body.includes('Experiments/JSRe0001_SNRPB-chromatin-retention-KCl-titration/1-notes/JSRe0001.md') && body.includes('JSRe0001_P_WesternBlot_'), body.slice(0, 300));
check('the per-type template was used', body.includes('Objective'));
await shot('note-new');

await page.getByRole('button', { name: 'Mark complete', exact: true }).click();
await settle();
check('completing an unwritten experiment is refused', (await text()).includes('still empty'));

await page.getByRole('link', { name: 'Edit here' }).click();
await page.waitForSelector('textarea[name="text"]');
const original = await page.inputValue('textarea[name="text"]');
await page.fill('textarea[name="text"]', original.replace('experiment_id: JSRe0001', 'experiment_id: JSRe0009'));
await click('Save');
check('changing the ID in the header is refused and the text is kept',
  (await text()).includes('must stay JSRe0001') && (await page.inputValue('textarea[name="text"]')).includes('JSRe0009'));
const written = original
  .replace(/(## Results\n)/, '$1\nThe chromatin fraction rose from 0.31 to 0.58 (n = 3).\n\n![blot](../5-figures/JSRe0001_R_blot-summary.png)\n')
  .replace(/(## Interpretation\n)/, '$1\nConsistent with the hypothesis; see JSRa0001 and P_WesternBlot.\n');
await page.fill('textarea[name="text"]', written);
await click('Save');
body = await text();
check('edited note is shown rendered, with IDs as links', body.includes('rose from 0.31 to 0.58') && (await page.locator('#note-body a[href="#/note/JSRa0001"]').count()) === 1);

const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==', 'base64');
await page.setInputFiles('input[name="files"]', { name: 'Screen Shot 12.png', mimeType: 'image/png', buffer: png });
await page.fill('input[name="description"]', 'blot summary');
await page.check('input[name="result"]');
await click('Add');
check('an added file is renamed to the convention', (await text()).includes('5-figures/JSRe0001_R_blot-summary.png'));
await page.waitForFunction(() => { const i = document.querySelector('#note-body img'); return i && i.naturalWidth > 0; });
check('the figure linked from Results is displayed', true);
await page.setInputFiles('input[name="files"]', [{ name: 'ChemiDoc 2026-09-04.scn', mimeType: 'application/octet-stream', buffer: Buffer.from('raw') },
  { name: 'second.scn', mimeType: 'application/octet-stream', buffer: Buffer.from('raw2') }]);
await page.selectOption('select[name="subfolder"]', '2-data_raw');
await click('Add');
check('raw data keeps its original name', (await text()).includes('2-data_raw/ChemiDoc 2026-09-04.scn'));
await page.setInputFiles('input[name="files"]', { name: 'Screen Shot 12.png', mimeType: 'image/png', buffer: png });
await page.fill('input[name="description"]', 'blot summary');
await page.check('input[name="result"]');
await click('Add');
check('adding a file never overwrites', (await text()).includes('already exists'));

await click('Mark complete');
check('experiment marked complete with snapshot and manifest', (await text()).includes('JSRe0001 is complete') && (await text()).includes('_snapshot_'));
await click('Verify files');
check('files verify against the manifest', (await text()).includes('files match the manifest'));
await click('Remove lab-meeting flag');
await click('Verify files');
check('a change after completion is detected', (await text()).includes('modified 1-notes/JSRe0001.md'));
await click('Refresh snapshot & manifest');
await click('Flag for lab meeting');
await click('Refresh snapshot & manifest');
await shot('note-complete');

await open('#/check');
check('Check finds no problems', (await text()).includes('0 errors') && (await text()).includes('0 warnings'), (await text()).slice(0, 400));
await open('#/brief');
check('meeting brief lists the flagged experiment', (await text()).includes('JSRe0001 - SNRPB chromatin retention: KCl titration') && (await text()).includes('rose from 0.31 to 0.58'));
await click('Save into Inventory');
check('brief saved into Inventory', (await text()).includes('Inventory/meeting-brief_'));

await open('#/export');
await page.selectOption('#x-scope', 'all');
await click('Build export');
const exported = await page.inputValue('textarea.text');
check('export holds the experiment and what it refers to',
  exported.includes('==== Experiments/JSRe0001_') && exported.includes('==== Protocols/P_WesternBlot.md ====') && exported.includes('==== Samples/JSRa0001.md ===='));
const [dl] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Download .eln archive', exact: true }).click()]);
const elnPath = await dl.path();
const zip = fs.readFileSync(elnPath);
check('.eln download is a zip archive', zip.readUInt32LE(0) === 0x04034b50 && dl.suggestedFilename().endsWith('.eln'), dl.suggestedFilename());
await settle();
if (flag('--dump')) fs.copyFileSync(elnPath, path.join(flag('--dump'), '..', 'e2e-export.eln'));

await open('#/experiments?status=complete');
check('experiment list filters by status', (await text()).includes('1 shown'));
await open('#/samples');
check('sample list', (await text()).includes('JSRa0001') && (await text()).includes('antibody'));
await open('#/note/JSRa0001');
check('a sample shows the experiments that used it', (await text()).includes('Used in') && (await text()).includes('JSRe0001'));
await open('#/ai');
check('Ask the AI page', (await text()).includes('Say something like'));

const api = await page.evaluate(async () => {
  const found = await window.AIELN.call('find_notes', { status: 'complete' });
  return { tools: window.AIELN.tools.length, found: found.notes.map((n) => n.id), mcp: window.AIELN.mcpTools()[0].name };
});
check('the same tools are callable from window.AIELN', api.tools >= 20 && api.found.join() === 'JSRe0001' && api.mcp === 'get_conventions', JSON.stringify(api));

if (flag('--dump')) {
  const files = await page.evaluate(async (dirName) => {
    const out = {};
    const root = await (await navigator.storage.getDirectory()).getDirectoryHandle(dirName);
    async function walk(dir, prefix) {
      for await (const [n, h] of dir.entries()) {
        if (h.kind === 'directory') await walk(h, prefix + n + '/');
        else out[prefix + n] = [...new Uint8Array(await (await h.getFile()).arrayBuffer())];
      }
    }
    await walk(root, '');
    return out;
  }, name);
  for (const [rel, bytes] of Object.entries(files)) {
    const dst = path.join(flag('--dump'), rel);
    fs.mkdirSync(path.dirname(dst), { recursive: true });
    fs.writeFileSync(dst, Buffer.from(bytes));
  }
  check('notebook written to disk for the Python validator', Object.keys(files).length > 15, String(Object.keys(files).length));
}

/* practice notebook, narrow screen, offline */
await page.goto(`${base}/app/`);
await page.waitForSelector('text=Open your notebook');
check('start page explains what the page does', (await text()).includes('Nothing is uploaded'));
await click('Open the practice notebook');
check('practice notebook opens with example experiments', (await text()).includes('2 experiments'));
await shot('home-practice');
await page.setViewportSize({ width: 390, height: 800 });
await open('#/new/experiment');
check('no sideways scrolling on a phone-width screen', await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
await page.setViewportSize({ width: 1280, height: 900 });

await page.evaluate(() => navigator.serviceWorker.ready);
await page.waitForFunction(async () => (await caches.keys()).length > 0);
await context.setOffline(true);
await page.reload();
await page.waitForSelector('text=Open your notebook');
await click('Open the practice notebook');
check('the page works with no network after the first visit', (await text()).includes('2 experiments'));
await context.setOffline(false);

const real = errors.filter((e) => !/fonts\.g|ERR_INTERNET_DISCONNECTED|Failed to load resource/.test(e));
check('no script errors', real.length === 0, real.join(' | '));

await browser.close();
server.close();
console.log(failures.length ? `\n${failures.length} failed` : '\nall passed');
process.exit(failures.length ? 1 : 0);
