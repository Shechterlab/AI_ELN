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
check('with nothing to adopt, Home does not offer it', !(await text()).includes('Adopt older folders'));

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
await page.fill('textarea[name="text"]', original.replace('status: active', 'status: done').replace(/^title: .*$/m, 'title:'));
await click('Save');
check('a header the checker would reject is not saved', (await text()).includes('Not saved') && (await text()).includes("'title' is missing or empty") && (await text()).includes("status 'done'"));
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

check('print and repeat are offered on the note', (await page.getByRole('button', { name: 'Print / save as PDF', exact: true }).count()) === 1
  && (await page.getByRole('link', { name: 'Repeat this experiment' }).count()) === 1);
await page.getByRole('link', { name: 'Repeat this experiment' }).click();
await page.waitForSelector('#n-title');
check('repeating an experiment copies its title, project, protocol and samples',
  (await page.inputValue('#n-title')) === 'SNRPB chromatin retention: KCl titration' && (await page.inputValue('#n-project')) === 'PRMT5-ChromatinRelease'
  && (await page.inputValue('#n-protocol')) === 'P_WesternBlot' && (await page.isChecked('input[name="samples"][value="JSRa0001"]'))
  && (await page.inputValue('#n-related')) === 'JSRe0001');
await page.fill('#n-title', 'SNRPB chromatin retention: KCl titration, repeat 2');
await click('Create experiment');
check('the repeat gets the next ID', (await text('h1')).includes('JSRe0002'));
await open('#/note/JSRe0001');

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
await open('#/experiments');
check('the experiment list is newest first', (await page.locator('#main table tr td a').first().textContent()) === 'JSRe0002');
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
await click('Save as a folder of plain files');
check('export as a folder of plain files', (await text()).includes('Exports/export_all_') && (await text()).includes('Start with the README.md'), (await text()).slice(0, 300));
await page.locator('summary', { hasText: 'For another electronic notebook' }).click();
const [dl] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Download .eln archive', exact: true }).click()]);
const elnPath = await dl.path();
const zip = fs.readFileSync(elnPath);
check('.eln download is a zip archive', zip.readUInt32LE(0) === 0x04034b50 && dl.suggestedFilename().endsWith('.eln'), dl.suggestedFilename());
await settle();
if (flag('--dump')) fs.copyFileSync(elnPath, path.join(flag('--dump'), '..', 'e2e-export.eln'));

await open('#/export');
await page.selectOption('#x-scope', 'ids');
await page.fill('#x-ids', 'JSRe0001, JSRe9999');
await click('Build export');
check('a wrong ID in Export shows the message above the form', (await text()).includes('JSRe9999 not found') && (await page.locator('#x-ids').count()) === 1);
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

/* the same notebook opened for viewing only */
await page.goto(`${base}/app/?store=opfs&name=${name}&view=1#/note/JSRe0001`);
await page.waitForSelector('#note-body');
body = await text();
check('viewer mode shows the note without anything that changes it',
  body.includes('rose from 0.31 to 0.58') && (await page.getByRole('link', { name: 'Edit here' }).count()) === 0
  && (await page.getByRole('button', { name: 'Mark complete' }).count()) === 0 && (await page.locator('form[data-form="add-files"]').count()) === 0
  && (await page.getByRole('button', { name: 'Print / save as PDF', exact: true }).count()) === 1 && (await text('#where')).includes('view only'));
const refused = await page.evaluate(async () => {
  try { await window.AIELN.call('create_experiment', { title: 'x', initials: 'JSR' }); return 'created'; } catch (e) { return e.message; }
});
check('viewer mode refuses a change made through the tools', refused.includes('viewing only'), refused);
await open('#/');
check('viewer home has no New buttons', !(await text()).includes('New experiment') && (await text()).includes('viewing only'));
await open('#/edit/JSRe0001');
check('viewer cannot reach the editor', (await text()).includes('View only') && (await page.locator('textarea').count()) === 0);

/* one folder per person, side by side in a parent folder; an older folder waiting in one of them */
const labDir = `lab-${Date.now()}`;
await page.evaluate(async ({ root, files }) => {
  const top = await navigator.storage.getDirectory();
  for (const [p, content] of Object.entries(files)) {
    let dir = await top.getDirectoryHandle(root, { create: true });
    const parts = p.split('/');
    for (const part of parts.slice(0, -1)) dir = await dir.getDirectoryHandle(part, { create: true });
    const w = await (await dir.getFileHandle(parts[parts.length - 1], { create: true })).createWritable();
    await w.write(content);
    await w.close();
  }
  localStorage.removeItem('ai-eln-person');
}, { root: labDir, files: {
  'Ana Lopez/notebook.md': '---\ntype: notebook\nowner: Ana Lopez\ninitials: AL\nlast_ids: [ALe0006]\n---\n\n# Lab notebook\n',
  'Ana Lopez/Experiments/2019-03-04_PRMT5 western/scans/gel 1.tif': 'gel',
  'Ana Lopez/Experiments/2019-03-04_PRMT5 western/notes.txt': 'ran it',
  'Jorge/Protocols/README.md': 'protocols',
  'not a notebook/readme.txt': 'x',
} });
await page.goto(`${base}/app/?store=opfs&name=${labDir}&view=1`);
await page.waitForSelector('text=holds 2 notebooks');
check('a folder of notebooks lists them for viewing, with the owner from notebook.md',
  (await text()).includes('Ana Lopez (AL)') && (await text()).includes('Jorge/') && !(await text()).includes('not a notebook') && (await page.locator('#c-name').count()) === 0);
await page.goto(`${base}/app/?store=opfs&name=${labDir}`);
await page.waitForSelector('text=holds 2 notebooks');
await shot('choose-notebook');
await page.locator('a.tile', { hasText: 'Ana Lopez (AL)' }).click();
await settle();
await page.waitForSelector('text=Recent experiments');
check('opening one of them uses the owner named in its notebook.md', (await text()).includes('You are Ana Lopez (AL)') && (await text('#where')).includes('Ana Lopez'), (await text()).slice(0, 200));
check('Home says an older folder is waiting', (await text()).includes('Adopt older folders') && (await text()).includes('1 folder here is not a record yet'));
await open('#/check');
check('Check points an older folder to Adopt', (await text()).includes('Adopt it') && (await page.getByRole('link', { name: 'Adopt older folders' }).count()) === 1);
await open('#/adopt');
check('the adopt screen reads the title and date from the folder name',
  (await page.inputValue('input[name="title"]')) === 'PRMT5 western' && (await page.inputValue('input[name="date"]')) === '2019-03-04');
await shot('adopt');
await click('Adopt this folder');
body = await text();
await shot('adopted-note');
check('an adopted folder becomes the next experiment, after the last ID in notebook.md',
  (await text('h1')).includes('ALe0007') && body.includes('Adopted as ALe0007') && body.includes('is the date in the folder name') && body.includes('2019-03-04') && body.includes('Not written.'), body.slice(0, 300));
check('its files are listed where they now are, names unchanged', body.includes('2019-03-04_PRMT5 western/scans/gel 1.tif') && body.includes('ALe0007_adopted-files.csv'));
const adopted = await page.evaluate(async () => {
  const gone = await window.AIELN.call('adopt_folder', {});
  const raw = await window.AIELN.call('read_file', { path: 'Experiments/ALe0007_PRMT5-western/2-data_raw/2019-03-04_PRMT5 western/scans/gel 1.tif' });
  const check = await window.AIELN.call('check_notebook', {});
  const book = await window.AIELN.call('read_file', { path: 'notebook.md' });
  return { waiting: gone.folders.length, raw: raw.text, errors: check.errors, book: book.text };
});
check('the old folder is gone, the file is intact, the check has no errors, and notebook.md has the new last ID',
  adopted.waiting === 0 && adopted.raw === 'gel' && adopted.errors === 0 && adopted.book.includes('last_ids: [ALe0007]') && adopted.book.includes('owner: Ana Lopez'), JSON.stringify(adopted));
await page.goto(`${base}/app/?store=opfs&name=${labDir}`);
await page.waitForSelector('text=holds 2 notebooks');
await page.fill('#c-name', 'bad/name');
await click('Create');
check('a new notebook folder needs a usable name', (await text()).includes('A folder name cannot'));
await page.fill('#c-name', 'New Person');
await click('Create');
check('a new notebook can be started next to the others', (await text()).includes('The notebook “New Person” is ready') && (await text('#where')).includes('New Person'));
await page.goto(`${base}/app/?store=opfs&name=${labDir}`);
await page.waitForSelector('text=holds 3 notebooks');
check('the new notebook is listed with the others', (await text()).includes('New Person/'));

/* another lab: only lab.yaml differs */
/* a fresh context without the offline cache, so the substituted lab.yaml is what the page gets */
const otherContext = await browser.newContext({ serviceWorkers: 'block' });
const other = await otherContext.newPage();
await other.route('**/lab.yaml', (route) => route.fulfill({ contentType: 'text/yaml', body:
  "lab_name: Example Lab\ninstitution: Example University\nproduct_name: Bench notes\nrecord_name: notebook\nrepository_url: https://example.org/repo\ncolor_primary: '#7c2d12'\ncolor_accent: '#1d4ed8'\nprint_signatures: no\n" }));
await other.goto(`${base}/index.html`);
await other.waitForFunction(() => !document.documentElement.classList.contains('lab-pending'));
const brand = await other.evaluate(() => ({
  title: document.title, name: document.querySelector('.brand b').textContent, lab: document.querySelector('.brand small').textContent,
  teal: getComputedStyle(document.documentElement).getPropertyValue('--teal').trim(),
  repo: [...document.querySelectorAll('a')].filter((a) => a.href.includes('Shechterlab/AI_ELN')).length,
  footer: document.querySelector('footer').textContent,
}));
check('editing lab.yaml rebrands the site: names, colours, links',
  brand.title === 'Bench notes · Example Lab' && brand.name === 'Bench notes' && brand.lab === 'Example Lab' && brand.teal === '#7c2d12'
  && brand.repo === 0 && brand.footer.includes('Example Lab, Example University'), JSON.stringify(brand));
await other.goto(`${base}/app/`);
await other.waitForSelector('text=Open your notebook');
await other.getByRole('button', { name: 'Open the practice notebook', exact: true }).click();
await other.waitForSelector('text=Example Lab notebook');
check('the notebook page uses the lab name from lab.yaml', (await other.textContent('#main h1')) === 'Example Lab notebook');
await otherContext.close();

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
