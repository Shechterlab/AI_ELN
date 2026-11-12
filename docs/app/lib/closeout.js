/* Finishing an experiment: a self-contained HTML snapshot, a checksum manifest, and the check that
   compares the folder with that manifest later. Nothing is locked; changes after completion are
   allowed and detectable. Same files, byte for byte, as `eln.py complete` writes. */

import { ElnError, SKIP_NAMES } from './schema.js';
import { splitFrontMatter, setHeaderField } from './frontmatter.js';
import { loadVault, sections, sectionIsEmpty } from './vault.js';
import { mdToHtml, imagePaths } from './markdown.js';
import { writeIndex } from './inventory.js';
import { hashFile } from './sha256.js';
import { guessMime } from './mime.js';
import {
  esc, cmp, thousands, toBase64, isoDate, validDate, pyRepr, strip, splitlines, dirname, basename, joinPath, normpath, decodeText,
} from './text.js';
import { walkFiles, writeText, exists } from '../store/base.js';

export const SNAPSHOT_CSS = "body{max-width:860px;margin:32px auto;padding:0 20px;font:15px/1.5 -apple-system,BlinkMacSystemFont,"
  + "'Segoe UI',Helvetica,Arial,sans-serif;color:#1f2933}h1{font-size:22px;margin-bottom:4px}"
  + 'h2{border-bottom:1px solid #e3e8ee;padding-bottom:4px;margin-top:24px;font-size:18px}'
  + 'table{border-collapse:collapse;margin:8px 0}th,td{text-align:left;padding:5px 9px;border-bottom:1px solid #e3e8ee;'
  + 'vertical-align:top}.meta td:first-child{color:#5f6b7a;white-space:nowrap}img{max-width:100%;border:1px solid #e3e8ee}'
  + 'code{background:#f1f5f9;padding:1px 4px;border-radius:4px}pre{background:#f1f5f9;padding:10px;overflow-x:auto}'
  + '.sub{color:#5f6b7a}.foot{color:#5f6b7a;font-size:13px;margin-top:40px;border-top:1px solid #e3e8ee;padding-top:10px}';

/** Every regular file under an experiment folder, in order, skipping what the operating system leaves behind. */
export async function folderFiles(store, folder) {
  return (await walkFiles(store, folder)).filter((p) => {
    const name = basename(p);
    return !SKIP_NAMES.has(name.toLowerCase()) && !name.startsWith('.') && !p.split('/').includes('__pycache__');
  });
}

async function dataUri(store, path, limit = 8000000) {
  if (path === '.' || path.startsWith('..')) return null;
  const mime = guessMime(basename(path));
  if (!mime || !mime.startsWith('image/')) return null;
  const s = await store.stat(path);
  if (!s || s.kind !== 'file' || s.size > limit) return null;
  return `data:${mime};base64,` + toBase64(await store.readBytes(path));
}

/** One note as a single HTML file: header table, body with images embedded, list of files.
    It opens in any browser and prints to PDF. */
export async function renderSnapshotHtml(store, note, generated = isoDate()) {
  const text = decodeText(await store.readBytes(note.path), false);
  const bodyMd = splitFrontMatter(text).body;
  const noteDir = dirname(note.path);
  const embedded = new Map();
  for (const rel of imagePaths(bodyMd)) {
    if (!embedded.has(rel)) embedded.set(rel, await dataUri(store, normpath(joinPath(noteDir, rel))));
  }
  const meta = Object.entries(note.fields)
    .map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(Array.isArray(v) ? v.join(', ') : v) || '-'}</td></tr>`).join('');
  let filesHtml = '';
  if (note.folder !== null) {
    const rows = [];
    for (const p of await folderFiles(store, note.folder)) {
      const size = (await store.stat(p)).size;
      rows.push(`<tr><td>${esc(p.slice(note.folder.length + 1))}</td><td>${thousands(size)}</td></tr>`);
    }
    filesHtml = '<h2>Files in this experiment folder</h2><table><tr><th>path</th><th>bytes</th></tr>' + rows.join('') + '</table>';
  }
  return `<!doctype html><html><head><meta charset=utf-8><title>${esc(note.id)} ${esc(note.get('title'))}</title>`
    + `<style>${SNAPSHOT_CSS}</style></head><body>`
    + `<h1>${esc(note.id)} <span class=sub>${esc(note.get('title'))}</span></h1>`
    + `<table class=meta>${meta}</table>`
    + mdToHtml(bodyMd, { imgBase: '', linkIds: false, imgSrc: (rel) => embedded.get(rel) || rel })
    + filesHtml
    + `<div class=foot>Snapshot of <code>${esc(note.path)}</code> generated ${esc(generated)} by AI_ELN. `
    + 'The Markdown file is the record; this rendering is for reading, printing, and archiving.</div>'
    + '</body></html>';
}

export const snapshotPath = (note, when) => `${dirname(note.path)}/${note.id}_snapshot_${when.replaceAll('-', '')}.html`;
export const manifestPath = (folder, expId) => `${folder}/1-notes/${expId}_MANIFEST.sha256`;

/** { path relative to the experiment folder: sha256 } for every file except the manifest itself. */
export async function hashFolder(store, folder, expId) {
  const out = {};
  const skip = manifestPath(folder, expId);
  for (const p of await folderFiles(store, folder)) {
    if (p !== skip) out[p.slice(folder.length + 1)] = await hashFile(store, p);
  }
  return out;
}

/** sha256sum format, `<hash>  <path>` per line, so `sha256sum -c` can check it with no tool of ours. */
export async function writeManifest(store, folder, expId) {
  const hashes = await hashFolder(store, folder, expId);
  const path = manifestPath(folder, expId);
  await writeText(store, path, Object.keys(hashes).sort(cmp).map((rel) => `${hashes[rel]}  ${rel}\n`).join(''));
  return path;
}

export async function readManifest(store, folder, expId) {
  const path = manifestPath(folder, expId);
  if (!(await exists(store, path))) return null;
  const out = {};
  for (const line of splitlines(decodeText(await store.readBytes(path), false))) {
    const m = /^([0-9a-f]{64})\s+\*?(.+)$/.exec(strip(line));
    if (m) out[m[2]] = m[1];
  }
  return out;
}

/** What changed since the manifest was written. -> { missing, modified, added, files } */
export async function verifyManifest(store, folder, expId) {
  const recorded = await readManifest(store, folder, expId);
  if (recorded === null) throw new ElnError(`${expId} has no manifest (it has not been marked complete)`, 'no_manifest');
  const now = await hashFolder(store, folder, expId);
  return {
    missing: Object.keys(recorded).filter((p) => !(p in now)).sort(cmp),
    modified: Object.keys(recorded).filter((p) => p in now && now[p] !== recorded[p]).sort(cmp),
    added: Object.keys(now).filter((p) => !(p in recorded)).sort(cmp),
    files: Object.keys(recorded).length,
  };
}

/** Verify one experiment, or every experiment that has a manifest.
    -> { results: [{ id, ok, missing, modified, added, files, error }], drift } */
export async function verifyExperiments(store, vault, id = '') {
  let targets;
  if (id) {
    const note = vault.get(id);
    if (note === null || note.kind !== 'experiment') throw new ElnError(`no experiment ${id}`, 'not_found');
    targets = [note];
  } else {
    targets = [];
    for (const n of vault.notes.experiment) {
      if (n.folder && n.id && await exists(store, manifestPath(n.folder, n.id))) targets.push(n);
    }
  }
  const results = [];
  for (const n of targets) {
    try {
      const r = await verifyManifest(store, n.folder, n.id);
      results.push({ id: n.id, ok: !(r.missing.length || r.modified.length || r.added.length), ...r });
    } catch (e) {
      if (!(e instanceof ElnError)) throw e;
      results.push({ id: n.id, ok: false, missing: [], modified: [], added: [], files: 0, error: e.message });
    }
  }
  return { results, drift: results.filter((r) => !r.ok).length };
}

/** Write (or rewrite) the HTML snapshot of any note. -> path */
export async function renderSnapshot(store, vault, id, { when = isoDate(), out = '' } = {}) {
  const note = vault.get(id);
  if (note === null) throw new ElnError(`no note ${id}`, 'not_found');
  const path = out || snapshotPath(note, when);
  await writeText(store, path, await renderSnapshotHtml(store, note, when));
  return path;
}

/** The close-out: check the note is written up, set status and date_completed, write a snapshot and
    a manifest, rebuild the index. -> { snapshot, manifest, warnings, files } */
export async function completeExperiment(store, id, { when = '', force = false, today = isoDate() } = {}) {
  let vault = await loadVault(store);
  let note = vault.get(id);
  if (note === null || note.kind !== 'experiment' || note.folder === null) throw new ElnError(`no experiment ${id}`, 'not_found');
  const date = when || today;
  if (!validDate(date)) throw new ElnError(`date must be YYYY-MM-DD (got ${pyRepr(date)})`, 'bad_date');
  const secs = sections(note.body);
  const empty = ['Results', 'Interpretation'].filter((s) => sectionIsEmpty(secs.get(s) || ''));
  if (empty.length && !force) {
    throw new ElnError(`${id}: the ${empty.join(' and ')} section${empty.length > 1 ? 's are' : ' is'} still empty. `
      + `Write ${empty.length > 1 ? 'them' : 'it'} first, or complete anyway (force).`, 'sections_empty', { empty, id });
  }
  const warnings = [];
  const raw = note.get('raw_data_path');
  if (raw && !/^[A-Za-z][A-Za-z0-9+.-]*:\/\//.test(raw) && !raw.startsWith('\\\\')) {
    const outside = /^(\/|~|[A-Za-z]:[\\/])/.test(raw);
    const rel = normpath(raw);
    let found = !outside && !rel.startsWith('..') && await exists(store, rel === '.' ? '' : rel);
    if (!found && typeof store.existsOutside === 'function') found = await store.existsOutside(raw);
    /* a store that cannot look outside the notebook folder says nothing about an outside path */
    const canTell = !outside || typeof store.existsOutside === 'function';
    if (!found && canTell) {
      warnings.push(`raw_data_path ${pyRepr(raw)} was not found from this machine; fine if it is on a mounted drive, `
        + 'but make sure the data is somewhere backed up');
    }
  }
  let text = decodeText(await store.readBytes(note.path), true);
  text = setHeaderField(text, 'status', 'complete', note.path);
  text = setHeaderField(text, 'date_completed', date, note.path);
  await writeText(store, note.path, text);
  vault = await loadVault(store);
  note = vault.get(id);
  const snapshot = snapshotPath(note, date);
  await writeText(store, snapshot, await renderSnapshotHtml(store, note, date));
  const manifest = await writeManifest(store, note.folder, id);
  await writeIndex(store, vault);
  return { snapshot, manifest, warnings, files: Object.keys((await readManifest(store, note.folder, id)) || {}).length };
}

/** The text `eln.py verify` prints. */
export function formatVerify({ results, drift }) {
  if (!results.length) return 'No experiment has a manifest yet (manifests are written when an experiment is marked complete).\n';
  const lines = [];
  for (const r of results) {
    if (r.error) lines.push(`${r.id}: ${r.error}`);
    else if (r.ok) lines.push(`${r.id}: OK, all ${r.files} files match the manifest`);
    else {
      lines.push(`${r.id}: changed since completion`);
      for (const p of r.modified) lines.push(`  modified  ${p}`);
      for (const p of r.missing) lines.push(`  missing   ${p}`);
      for (const p of r.added) lines.push(`  added     ${p}`);
    }
  }
  if (drift) lines.push('Changes after completion are allowed; mark the experiment complete again to refresh the snapshot and manifest.');
  return lines.join('\n') + '\n';
}
