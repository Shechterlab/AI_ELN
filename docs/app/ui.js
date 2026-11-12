/* The notebook page. Everything it does goes through the tools in lib/tools.js, the same list the
   MCP server exposes; this file is only screens and buttons. No framework, no build step. */

import { TOOLS, callTool, experimentFiles, isReadOnlyCall, openAiTools, mcpTools } from './lib/tools.js';
import { loadVault, ciIn, sortedById } from './lib/vault.js';
import { findNotes, exportScope } from './lib/query.js';
import { mdToHtml } from './lib/markdown.js';
import { splitFrontMatter, csvItems } from './lib/frontmatter.js';
import { ensureVaultDirs, addFile, readNotebook, setNotebookOwner, notebookPerson, NOTEBOOK_FILE, knownInitials, initialsOf, inAnotherNotebook } from './lib/create.js';
import { manifestPath, renderSnapshotHtml } from './lib/closeout.js';
import { loadLab, recordTitle } from './lib/lab.js';
import { labReady } from '../assets/brand.js';
import { cleanInitials } from './lib/names.js';
import { guessMime } from './lib/mime.js';
import { AGENTS_MD } from './lib/conventions.js';
import { ElnError, KIND_DIR, SUBFOLDERS, STATUS, SAMPLE_LETTERS, EXPERIMENT_TYPES, MEETING_TAG } from './lib/schema.js';
import { esc, cmp, dirname, isoDate } from './lib/text.js';
import { exists, isDir, writeText, SubStore } from './store/base.js';
import { MemoryStore } from './store/memory.js';
import { FsAccessStore, canPickFolders, pickFolder, allowed, rememberFolder, recallFolder, forgetFolder } from './store/fsaccess.js';

const $ = (sel) => document.querySelector(sel);
const main = $('#main');
const state = {
  store: null, kind: '', readOnly: false, pending: null, vault: null, person: readPerson(), flash: '', draft: null, urls: [], drawn: null,
  labText: null, lab: null, dirty: false, owner: null,
};

const NAV = [['#/', 'Home'], ['#/experiments', 'Experiments'], ['#/samples', 'Samples'], ['#/protocols', 'Protocols'],
  ['#/projects', 'Projects'], ['#/check', 'Check'], ['#/brief', 'Meeting brief'], ['#/export', 'Export'], ['#/ai', 'Ask the AI']];

const ASKS = [
  ['Check that a Results section matches its data', 'Re-analyse 4-data_processed/JSRe0007_quant.csv the way the note describes and tell me whether the numbers in Results match.', 'Codex / Claude Code'],
  ['Report a test properly', 'Which test fits this design? Write the Results sentence in the standard format with effect size and CI.', 'both'],
  ['Audit the lab-meeting figure', 'Check 5-figures/JSRe0007_R_....png against the figure checklist: axes, colour, what it can and cannot support.', 'Codex / Claude Code'],
  ['Draft a paragraph from a note', 'Draft the Results paragraph for JSRe0007 from its Results and Interpretation only, experiment ID after each claim.', 'both'],
  ['Push back on an interpretation', 'What would falsify the Interpretation in JSRe0007? What is the strongest alternative explanation?', 'both'],
  ['Plan before starting', 'Lay out the design for a 3-condition, 3-replicate fractionation and write the pre-registration: predictions and the decision rule.', 'both'],
  ['Ground a project page in the literature', 'Find recent papers on PRMT5 and snRNP chromatin release and add them, with DOIs, to the project page\'s references.', 'Codex / Claude Code'],
  ['Turn the meeting brief into slides', 'Make a five-slide deck from Inventory/meeting-brief_20260912.md.', 'Codex / Claude Code'],
  ['Start an RNA-seq or mass-spec analysis', 'Set up the DESeq2 analysis for ALXe0004, DMSO vs PRMT5i, three vs three.', 'Codex / Claude Code, with uv'],
];

/* ---------- small helpers ---------- */

function readPerson() {
  try {
    const p = JSON.parse(localStorage.getItem('ai-eln-person') || '{}');
    return { initials: cleanInitials(p.initials || ''), researcher: String(p.researcher || '') };
  } catch (e) {
    return { initials: '', researcher: '' };
  }
}

const ctx = () => ({ store: state.store, person: state.person, labText: state.labText });
function run(name, args = {}) {
  if (state.readOnly && !isReadOnlyCall(name, args)) throw new ElnError('This notebook is open for viewing only. Nothing was changed.', 'read_only');
  return callTool(ctx(), name, args);
}
const canWrite = () => !state.readOnly;
const msg = (kind, html) => `<div class="msg ${kind}" role="status">${html}</div>`;
const pill = (s) => `<span class="pill ${esc(s)}">${esc(s || '-')}</span>`;
const noteLink = (id) => `<a href="#/note/${encodeURIComponent(id)}">${esc(id)}</a>`;
const options = (items, selected = '') => items.map((x) => `<option value="${esc(x)}"${x === selected ? ' selected' : ''}>${esc(x)}</option>`).join('');
const datalist = (id, items) => `<datalist id="${id}">${items.map((x) => `<option value="${esc(x)}">`).join('')}</datalist>`;

/** Go to a screen and wait until it is drawn. */
async function go(hash) {
  if (location.hash !== hash) location.hash = hash;
  await render();
}

function route() {
  const raw = location.hash.replace(/^#/, '') || '/';
  const [path, query = ''] = raw.split('?');
  return { parts: path.split('/').filter(Boolean).map(decodeURIComponent), q: new URLSearchParams(query) };
}

function download(name, content, type = 'application/octet-stream') {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = Object.assign(document.createElement('a'), { href: url, download: name });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (e) {
    const t = Object.assign(document.createElement('textarea'), { value: text });
    document.body.appendChild(t);
    t.select();
    const ok = document.execCommand('copy');
    t.remove();
    return ok;
  }
}

function fail(e) {
  if (e && e.name === 'ElnError') {
    state.flash = msg('err', esc(e.message)
      + (e.code === 'sections_empty' ? ` <button class="btn small" data-act="complete" data-force="1" data-id="${esc(e.data.id)}">Complete anyway</button>` : ''));
  } else if (e && (e.name === 'NotAllowedError' || e.name === 'SecurityError')) {
    state.store = null;
    state.flash = msg('warn', 'The browser no longer has permission to use the folder. Open it again.');
  } else {
    console.error(e);
    state.flash = msg('err', `Something went wrong: ${esc(e && e.message ? e.message : e)}`);
  }
}

/** Run something that changes the notebook, then draw the page again. */
async function work(fn) {
  main.setAttribute('aria-busy', 'true');
  try {
    await fn();
  } catch (e) {
    fail(e);
    await render();
  } finally {
    main.removeAttribute('aria-busy');
  }
}

/* ---------- opening a notebook ---------- */

async function looksLikeNotebook(store) {
  if (await exists(store, NOTEBOOK_FILE)) return true;
  for (const d of Object.values(KIND_DIR)) {
    if (await isDir(store, d)) return true;
  }
  return false;
}

const text1 = (v) => (typeof v === 'string' ? v : '');

/** The notebooks directly inside a folder that is not one itself: one folder per person, side by side. */
async function childNotebooks(store) {
  const out = [];
  const dirs = ((await store.list('')) || []).filter((e) => e.kind === 'dir' && !e.name.startsWith('.')).map((e) => e.name).sort(cmp);
  for (const name of dirs) {
    const sub = new SubStore(store, name);
    if (!(await looksLikeNotebook(sub))) continue;
    const known = await readNotebook(sub);
    out.push({ name, owner: text1(known.owner), initials: text1(known.initials) });
  }
  return out;
}

/** Who is writing: the owner named in the notebook's notebook.md, or else the initials saved in this
    browser. A notebook that names its owner is that person's, whoever used this browser last. */
async function usePerson(store) {
  const [initials, owner] = await notebookPerson(store);
  state.owner = initials ? { initials, researcher: owner || initials } : null;
  state.person = state.owner || readPerson();
}

async function setUp(store) {
  await ensureVaultDirs(store);
  if (!(await exists(store, 'AGENTS.md'))) await writeText(store, 'AGENTS.md', AGENTS_MD);
  await setNotebookOwner(store, state.person.researcher, state.person.initials);
}

async function attach(store, kind, { handle = null, readOnly = false, keepScreen = false } = {}) {
  state.store = store;
  state.kind = kind;
  state.readOnly = readOnly;
  state.pending = null;
  await usePerson(store);
  if (handle) {
    await rememberFolder(handle);
    try { localStorage.setItem('ai-eln-view-only', readOnly ? '1' : ''); } catch (e) { /* private mode */ }
  }
  await go(keepScreen && location.hash.length > 2 ? location.hash : '#/');
}

async function openHandle(handle, kind = 'folder', { readOnly = false, keepScreen = false } = {}) {
  const store = new FsAccessStore(handle);
  if (await looksLikeNotebook(store)) return attach(store, kind, { handle: kind === 'folder' ? handle : null, readOnly, keepScreen });
  const children = await childNotebooks(store);
  if (readOnly && !children.length) {
    state.flash = msg('warn', `“${esc(store.label)}” is not a notebook folder: it has no Experiments, Protocols, Samples, or Projects folder. Choose the folder that contains them.`);
    return render();
  }
  state.pending = { store, kind, handle, readOnly, children, names: ((await store.list('')) || []).map((e) => e.name).sort(cmp) };
  return render();
}

async function seedPractice(store) {
  const c = { store, person: { initials: 'ALX', researcher: 'Alex Example' } };
  await callTool(c, 'create_project', { project_id: 'Example-Project', title: 'Example project (practice data)' });
  await callTool(c, 'create_protocol', { name: 'WesternBlot', title: 'Western blot' });
  const s = await callTool(c, 'create_sample', { sample_type: 'antibody', title: 'anti-example antibody', source: 'practice data', storage: 'Fridge 1, door' });
  const e = await callTool(c, 'create_experiment', {
    title: 'Example blot: treated versus control', project: 'Example-Project', exp_type: 'WesternBlot',
    protocol: 'P_WesternBlot', samples: s.id, tags: MEETING_TAG,
  });
  await callTool(c, 'write_section', { id: e.id, section: 'Objective', text: 'Practice entry. Does the treatment change the band intensity?' });
  await callTool(c, 'write_section', { id: e.id, section: 'Results', text: 'Practice entry, not real data. Replace this with what you saw.' });
  await callTool(c, 'write_section', { id: e.id, section: 'Interpretation', text: 'Practice entry, not real data.' });
  await callTool(c, 'create_experiment', { title: 'Second example experiment', project: 'Example-Project' });
}

async function viewConnect() {
  if (state.pending) {
    const { store, names, children, readOnly } = state.pending;
    const newHere = readOnly ? '' : `<form class="stack" data-form="new-child"><label for="c-name">Start another notebook here, in a new folder</label>
        <div class="inline"><input type="text" id="c-name" name="name" required maxlength="80" placeholder="folder name, e.g. Ana Lopez"><button class="btn">Create</button></div></form>`;
    if (children.length) {
      return `<div class="connect"><h1>“${esc(store.label)}” holds ${children.length} notebook${children.length !== 1 ? 's' : ''}</h1>
        <p>Each notebook is a folder of its own. Choose the one to ${readOnly ? 'view' : 'open'}.</p>
        <div class="grid">${children.map((c) => `<a class="tile" href="#" data-act="open-child" data-name="${esc(c.name)}"><b>${esc(c.owner || c.name)}${c.initials ? ` (${esc(c.initials)})` : ''}</b><span>${esc(c.name)}/</span></a>`).join('')}</div>
        ${newHere}
        <div class="actions"><button class="btn" data-act="cancel-pending">Choose a different folder</button></div></div>`;
    }
    return `<div class="connect"><h1>Set up a notebook in “${esc(store.label)}”?</h1>
      <p>This folder has no notebook in it yet. Setting one up creates five folders (<code>Experiments</code>, <code>Protocols</code>,
      <code>Samples</code>, <code>Projects</code>, <code>Inventory</code>), a <code>notebook.md</code> that says whose notebook it is, and a short <code>AGENTS.md</code> that tells AI tools the rules. Nothing already in the folder is changed.</p>
      ${names.length ? `<p class="hint">Already in this folder: ${names.slice(0, 10).map(esc).join(', ')}${names.length > 10 ? ', ...' : ''}</p>` : '<p class="hint">The folder is empty.</p>'}
      <div class="actions"><button class="btn primary" data-act="setup-here">Set up the notebook here</button>
      <button class="btn" data-act="cancel-pending">Choose a different folder</button></div>
      <p class="hint">Folders already here stay as they are. Afterwards the notebook can adopt them one at a time as experiments.
        If several people will keep notebooks side by side in this folder, give each a folder of its own instead:</p>${newHere}</div>`;
  }
  const can = canPickFolders();
  const remembered = can ? await recallFolder() : null;
  return `<div class="connect"><h1>Open your notebook</h1>
    <p>A notebook is one folder on this computer, one per person, usually inside Dropbox or OneDrive. This page reads and writes the files in that folder. Nothing is uploaded.</p>
    ${can ? `<div class="actions">
        ${remembered ? `<button class="btn primary" data-act="reopen">Reopen “${esc(remembered.name)}”</button>` : ''}
        <button class="btn${remembered ? '' : ' primary'}" data-act="pick">${remembered ? 'Open a different folder' : 'Open notebook folder'}</button>
        <button class="btn" data-act="pick-view">View a notebook (read-only)</button></div>
      <p class="hint">The browser asks once whether this page may view and edit the folder. Choose your notebook folder (the one that contains <code>Experiments</code>), a folder that holds several people's notebooks, or any folder to start a new notebook in.
        <b>View</b> opens someone's notebook for reading: the page asks only for permission to view, and every button that changes something is hidden.</p>`
    : msg('warn', 'This browser cannot open folders. Use Chrome or Edge on a computer. In Safari or Firefox, start the notebook with the <b>Open ELN</b> launcher instead (<a href="../guide.html?d=getting-started">how</a>).')}
    <div class="card"><h2>Practice first</h2>
      <p>A practice notebook with two example experiments. It is kept in this tab's memory and is gone when you close the tab.</p>
      <div class="actions"><button class="btn" data-act="practice">Open the practice notebook</button></div></div>
    <div class="card"><h2>What this page does</h2>
      <ul><li>Creates experiments, samples, protocols, and projects with the right IDs, folders, and file names.</li>
      <li>Shows and edits notes, adds files under the right names, checks the conventions.</li>
      <li>Adopts older folders as experiments, without changing what is in them.</li>
      <li>Writes the lab-meeting brief and exports: one file for ChatGPT, or a folder of plain files.</li>
      <li>Works on the same folder as the Python tools and the AI tools. Use whichever you like.</li></ul></div></div>`;
}

/* ---------- screens ---------- */

function needSetup() {
  return state.person.initials ? '' : msg('warn', 'First time here: enter your initials and name. <a href="#/settings">Set up initials and name</a>.');
}

function expTable(exps) {
  const rows = exps.map((e) => `<tr><td>${noteLink(e.id)}</td><td>${esc(e.get('title'))}</td><td>${esc(e.get('researcher'))}</td>`
    + `<td>${esc(e.getList('project').join(', '))}</td><td>${esc(e.get('date_started'))}</td><td>${pill(e.get('status'))}</td></tr>`).join('');
  return `<div class="table-wrap"><table><tr><th>ID</th><th>Title</th><th>Who</th><th>Project</th><th>Started</th><th>Status</th></tr>${rows}</table></div>`;
}

async function viewHome() {
  const v = state.vault;
  const waiting = canWrite() ? (await run('adopt_folder', {})).folders.length : 0;
  const exps = sortedById(v.notes.experiment).reverse();
  const active = exps.filter((e) => e.get('status') === 'active');
  const flagged = exps.filter((e) => ciIn(MEETING_TAG, e.getList('tags')));
  const who = state.person.initials ? `${esc(state.person.researcher)} (${esc(state.person.initials)})` : 'not set up yet';
  const tiles = [
    ...(canWrite() ? [['#/new/experiment', 'New experiment', 'Creates the folder, the note, and the protocol copy.'],
      ['#/new/sample', 'New sample', 'Plasmid, oligo, antibody, cell line, gel...'],
      ['#/new/protocol', 'New protocol', 'A reusable procedure, one file each.'],
      ['#/new/project', 'New project', 'A summary page for a research project.']] : []),
    ['#/check', 'Check everything', 'Lists naming and metadata problems.'],
    ['#/brief', 'Lab meeting brief', 'Summary of experiments flagged for the meeting.'],
    ['#/export', 'Export', 'One file to paste into a chat, or a folder of plain files.'],
    ...(waiting ? [['#/adopt', 'Adopt older folders', `${waiting} folder${waiting !== 1 ? 's' : ''} here ${waiting !== 1 ? 'are' : 'is'} not a record yet.`]] : []),
  ];
  return `${canWrite() ? needSetup() : msg('warn', 'This notebook is open for viewing only. Nothing here can change it.')}<h1>${esc(recordTitle(state.lab))}</h1>
    <p>${canWrite() ? `You are <b>${who}</b> · ` : ''}${exps.length} experiments, ${active.length} active, ${flagged.length} flagged for lab meeting · <a href="#/settings">settings</a></p>
    <div class="grid">${tiles.map(([h, t, d]) => `<a class="tile" href="${h}"><b>${esc(t)}</b><span>${esc(d)}</span></a>`).join('')}</div>
    ${flagged.length ? `<h2>Flagged for lab meeting</h2>${expTable(flagged)}` : ''}
    <h2>Recent experiments</h2>${exps.length ? expTable(exps.slice(0, 12)) : `<p class="hint">None yet.${canWrite() ? ' Start with <a href="#/new/experiment">New experiment</a>.' : ''}</p>`}`;
}

function viewExperiments(q) {
  const v = state.vault;
  const f = Object.fromEntries(['q', 'project', 'status', 'researcher', 'tag'].map((k) => [k, q.get(k) || '']));
  const hits = findNotes(v, 'experiment', { project: f.project, status: f.status, researcher: f.researcher, text: f.q, tag: f.tag }).reverse(); // newest first, as on Home
  const projects = [...new Set(v.notes.experiment.flatMap((e) => e.getList('project')))].sort(cmp);
  return `<h1>Experiments</h1>
    <form class="filters" data-form="filter">
      <div><label for="f-q">Search text</label><input id="f-q" name="q" value="${esc(f.q)}"></div>
      <div><label for="f-p">Project</label><select id="f-p" name="project"><option value="">any</option>${options(projects, f.project)}</select></div>
      <div><label for="f-s">Status</label><select id="f-s" name="status"><option value="">any</option>${options(STATUS.experiment, f.status)}</select></div>
      <div><label for="f-r">Researcher</label><input id="f-r" name="researcher" value="${esc(f.researcher)}"></div>
      <div><label for="f-t">Tag</label><input id="f-t" name="tag" value="${esc(f.tag)}" placeholder="meeting"></div>
      <div><button class="btn small">Filter</button></div></form>
    <div class="actions">${canWrite() ? '<a class="btn primary" href="#/new/experiment">New experiment</a><a class="btn" href="#/adopt">Adopt an older folder</a>' : ''}<span class="hint">${hits.length} shown, newest first</span></div>
    ${hits.length ? expTable(hits) : '<p>No matches.</p>'}`;
}

function viewList(kind, title, cols) {
  const notes = sortedById(state.vault.notes[kind]);
  const head = cols.map(([, label]) => `<th>${esc(label)}</th>`).join('');
  const rows = notes.map((n) => '<tr>' + cols.map(([field]) => (field === 'id' ? `<td>${noteLink(n.id)}</td>`
    : field === 'status' ? `<td>${pill(n.get('status'))}</td>` : `<td>${esc(n.get(field))}</td>`)).join('') + '</tr>').join('');
  return `<h1>${esc(title)}</h1>${canWrite() ? `<div class="actions"><a class="btn primary" href="#/new/${kind}">New ${kind}</a></div>` : ''}
    ${notes.length ? `<div class="table-wrap"><table><tr>${head}</tr>${rows}</table></div>` : '<p>None yet.</p>'}`;
}

async function viewNote(id) {
  const v = state.vault;
  const n = v.get(id);
  if (!n) {
    const elsewhere = inAnotherNotebook(id, await knownInitials(state.store));
    return `<h1>Not in this notebook</h1><p>There is no note with the ID ${esc(id)} here.${elsewhere
      ? ` Its initials are ${esc(initialsOf(id))}, so it is a record in that person's notebook, which is a different folder. To read it, open that folder with <a href="#/settings">Open a different folder</a>.` : ''}</p>`;
  }
  const body = mdToHtml(splitFrontMatter(n.text).body, {
    imgBase: dirname(n.path), imgSrc: (rel) => 'eln-file:' + rel, linkHref: (x) => `#/note/${x}`,
  });
  const meta = Object.entries(n.fields).filter(([k]) => k !== 'type')
    .map(([k, val]) => `<div>${esc(k)}</div><div>${esc(Array.isArray(val) ? val.join(', ') : val) || '-'}</div>`).join('');
  const w = canWrite();
  let actions = `<div class="actions">${w ? `<a class="btn primary" href="#/edit/${encodeURIComponent(n.id)}">Edit here</a>` : ''}`;
  let filesHtml = '';
  let usage = '';
  if (n.kind === 'experiment' && n.folder) {
    const flagged = ciIn(MEETING_TAG, n.getList('tags'));
    if (w) actions += `<button class="btn" data-act="flag" data-id="${esc(n.id)}">${flagged ? 'Remove lab-meeting flag' : 'Flag for lab meeting'}</button>`;
    if (n.get('status') !== 'complete') {
      if (w) actions += `<button class="btn" data-act="complete" data-id="${esc(n.id)}">Mark complete</button>`;
    } else {
      const has = await exists(state.store, manifestPath(n.folder, n.id));
      actions += `<button class="btn" data-act="verify" data-id="${esc(n.id)}"${has ? '' : ' disabled title="No manifest yet: mark the experiment complete first"'}>Verify files</button>`;
      if (w) actions += `<button class="btn" data-act="complete" data-force="1" data-id="${esc(n.id)}">Refresh snapshot &amp; manifest</button>`;
    }
    if (w) actions += `<a class="btn" href="#/new/experiment?from=${encodeURIComponent(n.id)}">Repeat this experiment</a>`;
    actions += `<button class="btn" data-act="print" data-id="${esc(n.id)}">Print / save as PDF</button>`;
    if (w) actions += `<button class="btn" data-act="snapshot" data-id="${esc(n.id)}">Save HTML snapshot</button>`;
    const files = await experimentFiles(state.store, n);
    filesHtml = `<h2>Files</h2><div class="card files">${SUBFOLDERS.map((sub) => `<div><b>${esc(sub)}/</b> `
      + (files[sub].length ? files[sub].map((name) => `<a href="#" data-act="open-file" data-path="${esc(`${n.folder}/${sub}/${name}`)}">${esc(name)}</a>`).join(', ') : '<i class="hint">empty</i>')
      + '</div>').join('')}
      ${w ? `<form class="drop" data-form="add-files" data-id="${esc(n.id)}">
        <div class="inline"><b>Add files</b><input type="file" name="files" multiple required aria-label="Files to add">
          <select name="subfolder" aria-label="Subfolder">${options(SUBFOLDERS, '5-figures')}</select></div>
        <div class="inline" style="margin-top:8px"><input type="text" name="description" placeholder="what it shows (optional, one file)" size="34" aria-label="Description">
          <label><input type="checkbox" name="result"> result (adds <code>_R</code>)</label>
          <label><input type="checkbox" name="dated"> add today's date</label>
          <button class="btn small">Add</button></div>
        <div class="hint" style="margin-top:6px">Files are named <code>${esc(n.id)}_description.ext</code> for you. Files added to <code>2-data_raw</code> keep their original names. You can also drop files here.</div>
      </form>` : ''}</div>`;
  } else {
    const used = findNotes(v, 'experiment', { [n.kind]: n.id });
    usage = `<h2>Used in</h2>${used.length ? expTable(used) : '<p>No experiment yet.</p>'}`;
    actions += `<button class="btn" data-act="print" data-id="${esc(n.id)}">Print / save as PDF</button>`;
    if (w) actions += `<button class="btn" data-act="snapshot" data-id="${esc(n.id)}">Save HTML snapshot</button>`;
  }
  actions += `<span class="path">${esc(n.path)}</span></div>`;
  return `<h1>${esc(n.id)} <small>${esc(n.get('title'))}</small></h1>${actions}
    <div class="card"><div class="meta">${meta}</div></div><div class="card note" id="note-body">${body}</div>${filesHtml}${usage}`;
}

const SHORT_INITIALS = "Two-letter initials are more likely to be the same as someone else's. Three letters (first, middle, last name) are recommended.";
const VIEW_ONLY = '<h1>View only</h1><p>This notebook is open for viewing. To change it, open the folder with <b>Open notebook folder</b> (settings, Open a different folder).</p>';

function viewEdit(id) {
  if (!canWrite()) return VIEW_ONLY;
  const n = state.vault.get(id);
  if (!n) return `<h1>Not found</h1><p>There is no note with the ID ${esc(id)}.</p>`;
  const text = state.draft && state.draft.id === id ? state.draft.text : n.text;
  state.draft = null;
  return `<h1>Edit ${esc(n.id)}</h1>
    <p class="hint">This box shows the whole file. Keep the header between the <code>---</code> lines and the <code>##</code> section titles. Write under them. Saving checks the header and updates the index.</p>
    <form data-form="edit" data-id="${esc(n.id)}"><textarea name="text" class="text tall" spellcheck="true" aria-label="Note text">${esc(text)}</textarea>
    <div class="actions"><button class="btn primary">Save</button><a class="btn" href="#/note/${encodeURIComponent(n.id)}">Cancel</a><span class="path">${esc(n.path)}</span></div></form>`;
}

function viewNew(kind, q = new URLSearchParams()) {
  if (!canWrite()) return VIEW_ONLY;
  const v = state.vault;
  if (kind === 'experiment') {
    /* "Repeat this experiment": start from another experiment's title, project, type, protocols, and samples */
    const src = q.get('from') ? v.get(q.get('from')) : null;
    const from = src && src.kind === 'experiment' ? src : null;
    const pre = (key) => (from ? esc(from.getList(key).join(', ')) : '');
    const chosen = new Set(from ? from.getList('samples') : []);
    const samples = sortedById(v.notes.sample);
    const projects = sortedById(v.notes.project).map((n) => n.id);
    const protocols = sortedById(v.notes.protocol).map((n) => n.id);
    return `<h1>New experiment</h1>${needSetup()}
      ${from ? msg('ok', `Repeating <b>${esc(from.id)}</b>. The fields below are copied from it. The new experiment gets its own ID and today's date, and lists ${esc(from.id)} as related.`) : ''}
      <form class="stack" data-form="new-experiment">
        <label for="n-title">Title <span class="hint">(the only required field)</span></label>
        <input type="text" id="n-title" name="title" required autofocus value="${from ? esc(from.get('title')) : ''}" placeholder="e.g. SNRPB chromatin retention after PRMT5 inhibition: KCl titration">
        <div class="row"><div><label for="n-project">Project</label><input type="text" id="n-project" name="project" list="projects" value="${pre('project')}">${datalist('projects', projects)}
            <div class="hint">Pick an existing one or type a new ID. ${projects.length} exist.</div></div>
          <div><label for="n-type">Experiment type</label><input type="text" id="n-type" name="exp_type" list="types" value="${pre('experiment_type')}">${datalist('types', EXPERIMENT_TYPES)}
            <div class="hint">Separate several with commas: WesternBlot, Fractionation</div></div></div>
        <div class="row"><div><label for="n-protocol">Protocol</label><input type="text" id="n-protocol" name="protocol" list="protocols" value="${pre('protocols')}">${datalist('protocols', protocols)}
            <div class="hint">A dated copy is placed next to your note.</div></div>
          <div><label for="n-notebook">Paper notebook page</label><input type="text" id="n-notebook" name="notebook" placeholder="NB02-153"></div></div>
        <label>Samples used</label>
        ${samples.length ? `<div class="checks">${samples.map((s) => `<label><input type="checkbox" name="samples" value="${esc(s.id)}"${chosen.has(s.id) ? ' checked' : ''}> ${esc(s.id)} <span class="path">${esc(s.get('title'))}</span></label>`).join('')}</div>`
    : '<div class="hint">No samples recorded yet. <a href="#/new/sample">Add one</a>.</div>'}
        <label class="check" style="margin-top:16px"><input type="checkbox" name="meeting" value="1"> Flag for the next lab meeting</label>
        <details style="margin-top:12px"${from ? ' open' : ''}><summary class="hint">More fields</summary>
          <label for="n-related">Related experiments</label><input type="text" id="n-related" name="related" value="${from ? esc(from.id) : ''}" placeholder="JSRe0002, JSRe0004">
          <label for="n-raw">Raw data location (leave blank to use 2-data_raw)</label><input type="text" id="n-raw" name="raw_data_path" placeholder="leave blank to use 2-data_raw/"></details>
        <div class="actions" style="margin-top:18px"><button class="btn primary">Create experiment</button><a href="#/" class="btn">Cancel</a></div></form>`;
  }
  if (kind === 'sample') {
    return `<h1>New sample</h1>${needSetup()}
      <form class="stack" data-form="new-sample">
        <label for="n-stype">Type</label><select id="n-stype" name="sample_type">${Object.entries(SAMPLE_LETTERS).map(([l, t]) => `<option value="${t}">${t} (${l})</option>`).join('')}</select>
        <label for="n-title">Title</label><input type="text" id="n-title" name="title" required autofocus placeholder="e.g. pcDNA3-FLAG-SNRPB">
        <div class="row"><div><label for="n-source">Source</label><input type="text" id="n-source" name="source" placeholder="vendor and catalog no., or the experiment that made it, or who gave it"></div>
          <div><label for="n-storage">Storage location</label><input type="text" id="n-storage" name="storage" placeholder="Freezer B, box 3, A7"></div></div>
        <div class="actions" style="margin-top:18px"><button class="btn primary">Create sample</button><a href="#/samples" class="btn">Cancel</a></div></form>`;
  }
  if (kind === 'protocol') {
    return `<h1>New protocol</h1>
      <form class="stack" data-form="new-protocol">
        <label for="n-name">Short name</label><input type="text" id="n-name" name="name" required autofocus placeholder="WesternBlot">
        <div class="hint">Letters, digits, hyphens. Becomes <b>P_Name</b>. One file per protocol; update its version date when the procedure changes.</div>
        <label for="n-title">Full title</label><input type="text" id="n-title" name="title" placeholder="Western blot (wet transfer, PVDF)">
        <div class="actions" style="margin-top:18px"><button class="btn primary">Create protocol</button><a href="#/protocols" class="btn">Cancel</a></div></form>`;
  }
  return `<h1>New project</h1>
    <form class="stack" data-form="new-project">
      <label for="n-id">Short ID</label><input type="text" id="n-id" name="project_id" required autofocus placeholder="PRMT5-ChromatinRelease">
      <div class="hint">Letters, digits, hyphens; starts with a letter. Experiments join it by listing this ID.</div>
      <label for="n-title">Full title</label><input type="text" id="n-title" name="title">
      <label for="n-lead">Lead</label><input type="text" id="n-lead" name="lead" value="${esc(state.person.researcher)}">
      <div class="actions" style="margin-top:18px"><button class="btn primary">Create project</button><a href="#/projects" class="btn">Cancel</a></div></form>`;
}

async function viewAdopt() {
  if (!canWrite()) return VIEW_ONLY;
  const { folders } = await run('adopt_folder', {});
  const projects = sortedById(state.vault.notes.project).map((n) => n.id);
  const cards = folders.map((f, i) => `<form class="card stack" data-form="adopt" data-folder="${esc(f.path)}" data-date="${esc(f.date)}">
      <div class="path">${esc(f.path)}/</div>
      <div class="row"><div><label for="a-title-${i}">Title</label><input type="text" id="a-title-${i}" name="title" value="${esc(f.title)}"></div>
        <div><label for="a-date-${i}">Start date</label><input type="text" id="a-date-${i}" name="date" value="${esc(f.date)}" placeholder="YYYY-MM-DD, or blank to use the oldest file date"></div></div>
      <div class="row"><div><label for="a-project-${i}">Project</label><input type="text" id="a-project-${i}" name="project" list="projects"></div>
        <div><label class="check" style="margin-top:28px"><input type="checkbox" name="open" value="1"> Still in progress (leave the record open)</label></div></div>
      <div class="actions"><button class="btn primary">Adopt this folder</button></div></form>`).join('');
  return `<h1>Adopt older folders</h1>
    <p>These folders are in the notebook folder but are not records. Adopting one makes an experiment record for it: it gets the next ID and a note, and the folder is moved,
      exactly as it is, into the new experiment's <code>2-data_raw</code>. Nothing inside it is renamed or changed. A list of its files, with sizes and dates, is saved next to the note.</p>
    <p class="hint">To adopt a folder that is somewhere else, move or copy it into the notebook folder first (into <code>Experiments</code>, or next to it), then reload this page. Folders you do not adopt are left alone.</p>
    ${datalist('projects', projects)}${folders.length ? cards : '<p>No folder is waiting.</p>'}`;
}

async function viewCheck() {
  const r = await run('check_notebook');
  const byPath = new Map();
  for (const i of r.issues) {
    if (!byPath.has(i.path)) byPath.set(i.path, []);
    byPath.get(i.path).push(i);
  }
  const plural = (n, w) => `${n} ${w}${n !== 1 ? 's' : ''}`;
  const summary = msg(r.errors ? 'err' : r.warnings ? 'warn' : 'ok', `Checked ${esc(r.counts)}: <b>${plural(r.errors, 'error')}</b>, ${plural(r.warnings, 'warning')}. `
    + (r.issues.length ? 'ERROR must be fixed; WARN is advice.' : 'Everything follows the conventions.'));
  const blocks = [...byPath.keys()].sort(cmp).map((p) => `<div class="card"><div class="path">${esc(p)}</div>`
    + byPath.get(p).map((i) => `<div class="issue"><span class="lvl ${i.level}">${i.level}</span>${esc(i.message)}`
      + `${canWrite() && i.message.includes('Adopt it') ? ' <a href="#/adopt">Adopt older folders</a>' : ''}</div>`).join('') + '</div>').join('');
  return `<h1>Check everything</h1>${summary}${blocks}`;
}

async function viewBrief() {
  const { markdown } = await run('meeting_brief');
  state.lastText = markdown;
  return `<h1>Lab meeting brief</h1>
    <div class="actions">${canWrite() ? '<button class="btn primary" data-act="brief-save">Save into Inventory</button>' : ''}
      <button class="btn" data-act="download-text" data-name="meeting-brief_${isoDate().replaceAll('-', '')}.md">Download</button>
      <button class="btn" data-act="copy-text">Copy</button>
      <span class="hint">Built from every experiment with <code>meeting</code> in its tags.</span></div>
    <div class="card note">${mdToHtml(markdown, { imgBase: 'Inventory', imgSrc: (rel) => 'eln-file:' + rel, linkHref: (x) => `#/note/${x}` })}</div>`;
}

async function viewExport(q) {
  const projects = sortedById(state.vault.notes.project).map((n) => n.id);
  const scope = q.get('scope') || '';
  const form = `<form class="stack" data-form="export">
      <label for="x-scope">What to export</label>
      <select id="x-scope" name="scope">
        <option value="active"${scope === 'active' ? ' selected' : ''}>All active experiments</option>
        <option value="project"${scope === 'project' ? ' selected' : ''}>One project</option>
        <option value="ids"${scope === 'ids' ? ' selected' : ''}>Specific experiments</option>
        <option value="all"${scope === 'all' ? ' selected' : ''}>Everything</option></select>
      <div class="row"><div><label for="x-project">Project (for "One project")</label><select id="x-project" name="project">${options(projects, q.get('project') || '')}</select></div>
        <div><label for="x-ids">Experiment IDs (for "Specific experiments")</label><input type="text" id="x-ids" name="ids" value="${esc(q.get('ids') || '')}" placeholder="JSRe0002, JSRe0004"></div></div>
      <label class="check"><input type="checkbox" name="related" value="1"${q.get('related') === '0' ? '' : ' checked'}> Include the protocols, samples, and projects they refer to</label>
      <div class="actions"><button class="btn primary">Build export</button></div></form>`;
  let result = '';
  if (scope) {
    const args = exportArgs(q);
    let r;
    try {
      r = await run('export_notes', args);
    } catch (e) {
      if (e.name !== 'ElnError') throw e;
      const text = e.code === 'no_scope' ? 'Choose a project, or type at least one experiment ID.' : e.code === 'empty' ? 'No experiment matched that choice.' : e.message;
      return `<h1>Export</h1>${msg('err', esc(text))}${form}`;
    }
    state.lastText = r.markdown;
    state.lastExport = args;
    const name = `export_${exportScope(args)}_${isoDate().replaceAll('-', '')}`;
    result = `<h2>${r.experiments.length} experiment${r.experiments.length !== 1 ? 's' : ''}, ${r.characters.toLocaleString('en-US')} characters</h2>
      <div class="actions"><button class="btn primary" data-act="copy-text">Copy all</button>
        <button class="btn" data-act="download-text" data-name="${esc(name)}.md">Download .md</button>
        ${canWrite() ? '<button class="btn" data-act="export-save">Save .md into Inventory</button>' : ''}
        ${canWrite() ? `<button class="btn" data-act="folder-save">Save as a folder of plain files</button>
        <button class="btn" data-act="folder-save" data-raw="0">The same, without raw data</button>` : ''}</div>
      <p class="hint">Paste the text into a ChatGPT conversation, or attach the .md file. The folder goes into <code>Exports/</code> in the notebook folder: the notes and their files as they are,
        a README, one file with every note, and an index. Copy it wherever it is needed.</p>
      <details><summary class="hint">For another electronic notebook</summary>
        <div class="actions"><button class="btn" data-act="eln-download">Download .eln archive</button>
        ${canWrite() ? '<button class="btn" data-act="eln-save">Save .eln into Inventory</button>' : ''}</div>
        <p class="hint">The <code>.eln</code> archive is for importing into eLabFTW, RSpace, Kadi4Mat, PASTA, SampleDB, OpenSemanticLab, or SciLog.</p></details>
      <textarea class="text" readonly aria-label="Export text">${esc(r.markdown)}</textarea>`;
  }
  return `<h1>Export</h1><p>The notes you choose and the records they refer to, as one document with a short explanation of how to read them, or as a folder of plain files.</p>${form}${result}`;
}

function exportArgs(q) {
  const scope = q.get('scope');
  const args = { related: q.get('related') !== '0' };
  if (scope === 'project') args.project = q.get('project') || '';
  else if (scope === 'ids') args.experiment_ids = csvItems((q.get('ids') || '').replaceAll(' ', ','));
  else if (scope === 'all') args.all = true;
  else args.status = 'active';
  return args;
}

function viewAi() {
  return `<h1>Ask the AI</h1>
    <div class="card"><p><b>ChatGPT:</b> click <a href="#/export">Export</a>, copy, and paste into a chat. Once, paste
      <a href="../guide.html?d=ai-briefing">the briefing</a> as the chat's instructions. It can reason about the notes but cannot see data files or run anything.</p>
      <p><b>Codex, Claude Code, Cowork:</b> open the tool in the notebook folder. It reads the lab's rules and skills itself, and can read files and run analyses.</p>
      <p><b>MCP clients:</b> the notebook's own operations (create, find, check, complete, export) are available as tools through <code>node mcp/server.mjs</code>. See <a href="../guide.html?d=ai-agents">Using AI</a>.</p>
      <p>None of these needs an API key. Every factual claim an assistant makes should carry an experiment ID. If it does not, ask for one.</p></div>
    <div class="table-wrap"><table><tr><th>You want</th><th>Say something like</th><th>Works in</th></tr>
    ${ASKS.map(([want, say, where]) => `<tr><td><b>${esc(want)}</b></td><td><i>${esc(say)}</i></td><td>${esc(where)}</td></tr>`).join('')}</table></div>
    <p class="hint">The first three rows check work that already exists, so start there. "Both" means ChatGPT and the agents.</p>`;
}

function viewSettings() {
  const p = state.owner ? readPerson() : state.person;
  return `<h1>Settings</h1>
    ${state.owner ? msg('ok', `This notebook belongs to <b>${esc(state.owner.researcher)} (${esc(state.owner.initials)})</b>, as its <code>notebook.md</code> says. Records made here get ${esc(state.owner.initials)} IDs. The initials below are this browser's own, used in notebooks that do not name an owner.`) : ''}
    <form class="stack" data-form="settings">
      <label for="s-initials">Your initials (three letters)</label><input type="text" id="s-initials" name="initials" required value="${esc(p.initials)}" placeholder="JSR" maxlength="4">
      <div class="hint">Your IDs will look like ${esc(p.initials || 'JSR')}e0001. Use first, middle, and last initial: three letters are less likely to be the same as someone else's than two. Two to four letters are accepted.</div>
      <label for="s-name">Your full name</label><input type="text" id="s-name" name="researcher" value="${esc(p.researcher)}">
      <div class="hint">Saved in this browser. If <code>notebook.md</code> in the notebook folder does not name an owner yet, they are written there too.</div>
      <div class="actions" style="margin-top:18px"><button class="btn primary">Save</button><a href="#/" class="btn">Back</a></div></form>
    <h2>Notebook folder</h2>
    <p><span class="path">${esc(state.store.label || '')}</span> ${state.kind === 'practice' ? '(practice notebook, kept in memory, not saved)' : ''}${state.readOnly ? '(open for viewing only)' : ''}</p>
    <div class="actions"><button class="btn" data-act="switch">Open a different folder</button></div>`;
}

/* ---------- drawing ---------- */

async function hydrateImages(root) {
  for (const img of root.querySelectorAll('img')) {
    const src = img.getAttribute('src') || '';
    if (!src.startsWith('eln-file:')) continue;
    const rel = src.slice('eln-file:'.length);
    img.removeAttribute('src');
    if (rel.startsWith('..')) continue;
    try {
      const bytes = await state.store.readBytes(rel);
      const url = URL.createObjectURL(new Blob([bytes], { type: guessMime(rel) || 'application/octet-stream' }));
      state.urls.push(url);
      img.src = url;
    } catch (e) {
      img.alt = `${img.alt || 'image'} (file not found: ${rel})`;
    }
  }
}

async function render() {
  state.drawn = location.hash;
  const flash = state.flash;
  state.flash = '';
  for (const url of state.urls.splice(0)) URL.revokeObjectURL(url);
  const { parts, q } = route();
  const [section = '', arg = ''] = parts;
  $('#nav').innerHTML = state.store ? NAV.map(([h, t]) => `<a href="${h}"${h === '#/' + section ? ' aria-current="page"' : ''}>${t}</a>`).join('') : '';
  $('#where').innerHTML = state.store ? `<a href="#/settings" title="Notebook folder and your initials">${esc(state.store.label || 'notebook')}${state.readOnly ? ' · view only' : state.person.initials ? ' · ' + esc(state.person.initials) : ''}</a>` : '';
  let html;
  let title = 'Lab notebook';
  try {
    if (!state.store) html = await viewConnect();
    else {
      state.vault = await loadVault(state.store);
      state.lab = await loadLab(state.store, state.labText);
      const views = {
        '': () => viewHome(),
        experiments: () => viewExperiments(q),
        samples: () => viewList('sample', 'Samples', [['id', 'ID'], ['sample_type', 'Type'], ['title', 'Title'], ['storage_location', 'Storage'], ['status', 'Status']]),
        protocols: () => viewList('protocol', 'Protocols', [['id', 'ID'], ['title', 'Title'], ['version', 'Version'], ['status', 'Status']]),
        projects: () => viewList('project', 'Projects', [['id', 'ID'], ['title', 'Title'], ['lead', 'Lead'], ['status', 'Status']]),
        note: () => viewNote(arg),
        edit: () => viewEdit(arg),
        new: () => viewNew(arg, q),
        check: () => viewCheck(),
        adopt: () => viewAdopt(),
        brief: () => viewBrief(),
        export: () => viewExport(q),
        ai: () => viewAi(),
        settings: () => viewSettings(),
      };
      html = await (views[section] || views[''])();
      title = (arg || (NAV.find(([h]) => h === '#/' + section) || [])[1] || 'Home') + ' · Lab notebook';
    }
  } catch (e) {
    fail(e);
    html = state.store ? '' : await viewConnect();
  }
  const tpl = document.createElement('template');
  tpl.innerHTML = (state.flash || flash) + html;
  state.flash = '';
  if (state.store) await hydrateImages(tpl.content);
  main.replaceChildren(tpl.content);
  state.dirty = false;
  document.title = title;
  const first = main.querySelector('[autofocus]');
  if (first) first.focus();
}

/* ---------- forms ---------- */

function formData(form) {
  const out = {};
  for (const [k, v] of new FormData(form)) {
    if (v instanceof File) continue;
    out[k] = k in out ? `${out[k]}, ${v}` : String(v).trim();
  }
  return out;
}

const created = (r, what) => msg('ok', `Created ${what} <b>${esc(r.id)}</b>. <span class="path">${esc(r.path)}</span>`
  + r.extra.map((p) => `<br><span class="path">${esc(p)}</span> (protocol copy)`).join(''))
  + r.warnings.map((w) => msg('warn', esc(w))).join('');

const FORMS = {
  'new-child': async (d) => {
    const { handle, kind } = state.pending;
    const name = (d.name || '').trim();
    if (!name || name.startsWith('.') || /[\\/:*?"<>|\x00-\x1f]/.test(name) || /[ .]$/.test(name)) {
      state.flash = msg('err', 'A folder name cannot be empty, start with a dot, end with a dot or space, or contain \\ / : * ? " < > |');
      return render();
    }
    if ([...Object.values(KIND_DIR), 'Inventory', 'Exports', 'templates'].some((x) => x.toLowerCase() === name.toLowerCase())) {
      state.flash = msg('err', `“${esc(name)}” is the name of a folder inside every notebook. Choose another name, such as the person's name.`);
      return render();
    }
    const child = await handle.getDirectoryHandle(name, { create: true });
    const store = new FsAccessStore(child);
    const existed = await looksLikeNotebook(store);
    if (!existed) await setUp(store);
    state.flash = existed ? msg('ok', `There already is a notebook named “${esc(name)}”. It is open now; nothing in it was changed.`)
      : msg('ok', `The notebook “${esc(name)}” is ready.${state.person.initials ? '' : ' Enter your initials under settings, then create your first experiment.'}`);
    return attach(store, kind, { handle: kind === 'folder' ? child : null });
  },
  adopt: async (d, form) => {
    /* a date left as it was read from the folder name is not "given": the note then says where it came from */
    const date = d.date && d.date !== form.dataset.date ? d.date : '';
    const r = await run('adopt_folder', { folder: form.dataset.folder, title: d.title || '', date, project: d.project || '', status: d.open ? 'active' : 'complete' });
    state.flash = msg('ok', `Adopted as <b>${esc(r.id)}</b>. The old folder is now in <span class="path">${esc(r.folder)}/2-data_raw/</span>. Write what the experiment was for, and correct the title or dates if they are wrong.`)
      + r.warnings.map((w) => msg('warn', esc(w))).join('');
    await go(`#/note/${r.id}`);
  },
  filter: (d) => go('#/experiments?' + new URLSearchParams(Object.entries(d).filter(([, v]) => v))),
  export: (d) => go('#/export?' + new URLSearchParams({ scope: d.scope, project: d.project || '', ids: d.ids || '', related: d.related ? '1' : '0' })),
  settings: async (d) => {
    const initials = cleanInitials(d.initials);
    if (!initials) {
      state.flash = msg('err', 'Initials are 2 to 4 letters, like JSR.');
      return render();
    }
    const saved = { initials, researcher: d.researcher || initials };
    try { localStorage.setItem('ai-eln-person', JSON.stringify(saved)); } catch (e) { /* private mode */ }
    if (canWrite() && state.kind !== 'practice') await setNotebookOwner(state.store, saved.researcher, initials);
    await usePerson(state.store);
    state.flash = msg('ok', 'Saved.') + (initials.length === 2 ? msg('warn', `${SHORT_INITIALS} You can change them here before you create your first record.`) : '')
      + (state.owner && state.owner.initials !== initials ? msg('warn', `This notebook belongs to ${esc(state.owner.researcher)} (${esc(state.owner.initials)}), so records made here still get ${esc(state.owner.initials)} IDs. What you saved is used in notebooks that do not name an owner. To change this notebook's owner, edit <code>notebook.md</code> in its folder.`) : '');
    return go('#/');
  },
  'new-experiment': async (d) => {
    const tags = d.meeting ? MEETING_TAG : '';
    const { meeting, ...args } = d;
    const r = await run('create_experiment', { ...args, tags });
    state.flash = created(r, 'experiment');
    await go(`#/note/${r.id}`);
  },
  'new-sample': async (d) => {
    const r = await run('create_sample', d);
    state.flash = created(r, 'sample');
    await go(`#/note/${r.id}`);
  },
  'new-protocol': async (d) => {
    const r = await run('create_protocol', d);
    state.flash = created(r, 'protocol');
    await go(`#/note/${r.id}`);
  },
  'new-project': async (d) => {
    const r = await run('create_project', d);
    state.flash = created(r, 'project');
    await go(`#/note/${r.id}`);
  },
  edit: async (d, form) => {
    const id = form.dataset.id;
    const text = form.elements.text.value;
    try {
      await run('update_note', { id, text });
    } catch (e) {
      state.draft = { id, text };
      throw e;
    }
    state.flash = msg('ok', 'Saved.');
    await go(`#/note/${id}`);
  },
  'add-files': async (d, form) => {
    const id = form.dataset.id;
    const files = [...form.elements.files.files];
    const added = [];
    for (const f of files) {
      /* straight to the library, so a large instrument file is not turned into base64 on the way */
      const r = await addFile(state.store, state.vault, {
        id, subfolder: d.subfolder, original_name: f.name, bytes: new Uint8Array(await f.arrayBuffer()),
        description: files.length === 1 ? d.description || '' : '', result: !!d.result, date: d.dated ? isoDate() : '',
      });
      added.push(r.path);
    }
    state.flash = msg('ok', `Added ${added.length} file${added.length !== 1 ? 's' : ''}:<br>` + added.map((p) => `<span class="path">${esc(p)}</span>`).join('<br>'));
    await go(`#/note/${id}`);
  },
};

/* ---------- buttons ---------- */

const ACTS = {
  pick: async () => {
    const handle = await pickFolder();
    if (handle) await openHandle(handle);
  },
  'pick-view': async () => {
    const handle = await pickFolder('read');
    if (handle) await openHandle(handle, 'folder', { readOnly: true });
  },
  reopen: async () => {
    const handle = await recallFolder();
    const readOnly = viewOnlyRemembered();
    if (handle && await allowed(handle, true, readOnly ? 'read' : 'readwrite')) await openHandle(handle, 'folder', { readOnly });
  },
  print: async ({ id }) => {
    /* the same HTML a snapshot holds, sent to the printer without saving a file */
    const html = await renderSnapshotHtml(state.store, state.vault.get(id), isoDate(), state.lab);
    const old = document.getElementById('print-frame');
    if (old) old.remove();
    const frame = Object.assign(document.createElement('iframe'), { id: 'print-frame', title: 'Print view' });
    frame.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0';
    frame.srcdoc = html;
    frame.onload = () => { frame.contentWindow.focus(); frame.contentWindow.print(); };
    document.body.appendChild(frame);
  },
  practice: async () => {
    const store = new MemoryStore();
    await seedPractice(store);
    await attach(store, 'practice');
  },
  'setup-here': async () => {
    const { store, kind, handle } = state.pending;
    await setUp(store);
    state.flash = msg('ok', `The notebook is set up.${state.person.initials ? '' : ' Enter your initials under settings, then create your first experiment.'}`);
    await attach(store, kind, { handle: kind === 'folder' ? handle : null });
  },
  'open-child': async ({ name }) => {
    const { handle, kind, readOnly } = state.pending;
    await openHandle(await handle.getDirectoryHandle(name), kind, { readOnly });
  },
  'cancel-pending': async () => {
    state.pending = null;
    await render();
  },
  switch: async () => {
    state.store = null;
    await forgetFolder();
    await go('#/');
  },
  flag: async ({ id }) => {
    const n = state.vault.get(id);
    const tags = n.getList('tags');
    const next = ciIn(MEETING_TAG, tags) ? tags.filter((t) => t.toLowerCase() !== MEETING_TAG) : [...tags, MEETING_TAG];
    await run('set_field', { id, field: 'tags', value: next });
    await render();
  },
  complete: async ({ id, force }) => {
    const r = await run('complete_experiment', { id, force: !!force });
    state.flash = msg('ok', `<b>${esc(id)}</b> is complete. Snapshot: <span class="path">${esc(r.snapshot)}</span> (open it and print to PDF for LabArchives). `
      + `Manifest: ${r.files} files hashed.`) + r.warnings.map((w) => msg('warn', esc(w))).join('');
    await go(`#/note/${id}`);
  },
  verify: async ({ id }) => {
    const r = (await run('verify_files', { id })).results[0];
    if (r.ok) state.flash = msg('ok', `All ${r.files} files match the manifest written at completion.`);
    else {
      const lines = [...r.modified.map((p) => `modified ${p}`), ...r.missing.map((p) => `missing ${p}`), ...r.added.map((p) => `added ${p}`)];
      state.flash = msg('warn', `${r.error ? esc(r.error) : 'Changed since completion:'}<br>` + lines.map((l) => `<span class="path">${esc(l)}</span>`).join('<br>')
        + '<br>Changes after completion are allowed. Use Refresh snapshot &amp; manifest to record the current state.');
    }
    await render();
  },
  snapshot: async ({ id }) => {
    const r = await run('render_snapshot', { id });
    state.flash = msg('ok', `Saved <span class="path">${esc(r.path)}</span>. <a href="#" data-act="open-file" data-path="${esc(r.path)}">Open it</a> and print to PDF.`);
    await render();
  },
  'open-file': async ({ path }) => {
    const bytes = await state.store.readBytes(path);
    const type = guessMime(path) || 'application/octet-stream';
    const url = URL.createObjectURL(new Blob([bytes], { type: /^text\/(markdown|csv|x-python)/.test(type) ? 'text/plain;charset=utf-8' : type }));
    window.open(url, '_blank', 'noopener');
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  },
  'copy-text': async (_, el) => {
    const ok = await copyText(state.lastText || '');
    el.textContent = ok ? 'Copied' : 'Could not copy';
    setTimeout(() => { el.textContent = el.dataset.label || 'Copy'; }, 1500);
  },
  'download-text': async ({ name }) => download(name, state.lastText || '', 'text/markdown;charset=utf-8'),
  'brief-save': async () => {
    const r = await run('meeting_brief', { save: true });
    state.flash = msg('ok', `Saved to <span class="path">${esc(r.path)}</span>.`);
    await render();
  },
  'export-save': async () => {
    const r = await run('export_notes', { ...state.lastExport, save: true });
    state.flash = msg('ok', `Saved to <span class="path">${esc(r.path)}</span>.`);
    await render();
  },
  'folder-save': async ({ raw }) => {
    const r = await run('export_notes', { ...state.lastExport, format: 'folder', raw: raw !== '0' });
    state.flash = msg('ok', `Saved <span class="path">${esc(r.path)}/</span> (${r.files} files, ${r.bytes.toLocaleString('en-US')} bytes). Start with the README.md in it.`);
    await render();
  },
  'eln-save': async () => {
    const r = await run('export_notes', { ...state.lastExport, format: 'eln' });
    state.flash = msg('ok', `Saved <span class="path">${esc(r.path)}</span> (${r.files} files, ${r.size.toLocaleString('en-US')} bytes).`);
    await render();
  },
  'eln-download': async () => {
    const r = await run('export_notes', { ...state.lastExport, format: 'eln', return_bytes: true });
    download(r.name, r.bytes, 'application/vnd.eln+zip');
  },
};

main.addEventListener('submit', (e) => {
  const form = e.target.closest('form[data-form]');
  if (!form) return;
  e.preventDefault();
  work(() => FORMS[form.dataset.form](formData(form), form));
});

main.addEventListener('click', (e) => {
  const el = e.target.closest('[data-act]');
  if (!el) return;
  e.preventDefault();
  if (el.dataset.act === 'copy-text' && !el.dataset.label) el.dataset.label = el.textContent;
  work(() => ACTS[el.dataset.act](el.dataset, el));
});

for (const type of ['dragover', 'dragleave', 'drop']) {
  main.addEventListener(type, (e) => {
    const zone = e.target.closest('.drop');
    if (!zone) return;
    e.preventDefault();
    zone.classList.toggle('over', type === 'dragover');
    if (type === 'drop' && e.dataTransfer.files.length) zone.elements.files.files = e.dataTransfer.files;
  });
}

/* typing in the editor and then closing or reloading the tab asks first */
main.addEventListener('input', (e) => {
  if (e.target.closest('form[data-form="edit"]')) state.dirty = true;
});
window.addEventListener('beforeunload', (e) => {
  if (state.dirty) e.preventDefault();
});

$('#theme-btn').addEventListener('click', () => {
  const cur = document.documentElement.getAttribute('data-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  const next = cur === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  try { localStorage.setItem('ai-eln-theme', next); } catch (e) { /* private mode */ }
});

window.addEventListener('hashchange', () => {
  if (state.drawn !== location.hash) work(render); // go() has already drawn the screen it navigated to
});

/* For scripts, browser extensions, and the console: the same tools the page uses.
     await AIELN.call('find_notes', { status: 'active' })                                   */
window.AIELN = {
  tools: TOOLS,
  call: (name, args) => run(name, args),
  mcpTools,
  openAiTools,
  get folder() { return state.store ? state.store.label : null; },
};

function viewOnlyRemembered() {
  try { return localStorage.getItem('ai-eln-view-only') === '1'; } catch (e) { return false; }
}

async function start() {
  const params = new URLSearchParams(location.search);
  state.labText = (await labReady).text;
  try {
    if (params.get('store') === 'opfs') {
      /* test hook: a private folder inside the browser, with the same interface as a picked folder */
      const rootDir = await navigator.storage.getDirectory();
      await openHandle(await rootDir.getDirectoryHandle(params.get('name') || 'ai-eln-test', { create: true }), 'test',
        { readOnly: params.get('view') === '1', keepScreen: true });
      return;
    }
    if (canPickFolders()) {
      const handle = await recallFolder();
      const readOnly = viewOnlyRemembered();
      if (handle && await allowed(handle, false, readOnly ? 'read' : 'readwrite')) {
        state.store = new FsAccessStore(handle);
        state.kind = 'folder';
        state.readOnly = readOnly;
        await usePerson(state.store);
      }
    }
  } catch (e) {
    console.warn(e);
  }
  await render();
}

if ('serviceWorker' in navigator && (location.protocol === 'https:' || ['localhost', '127.0.0.1'].includes(location.hostname))) {
  navigator.serviceWorker.register('sw.js').catch(() => {});
}

start();
