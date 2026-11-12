/* Finishing an experiment: a self-contained HTML snapshot, a checksum manifest, and the check that
   compares the folder with that manifest later. Nothing is locked; changes after completion are
   allowed and detectable. Same files, byte for byte, as `eln.py complete` writes. */

import { ElnError, SKIP_NAMES } from './schema.js';
import { splitFrontMatter, setHeaderField } from './frontmatter.js';
import { loadVault, sections, sectionIsEmpty } from './vault.js';
import { mdToHtml, imagePaths } from './markdown.js';
import { writeIndex } from './inventory.js';
import { hashFile, sha256Hex } from './sha256.js';
import { loadLab, labLine, wantsSignatures } from './lab.js';
import { imageType } from './mime.js';
import {
  esc, cmp, thousands, toBase64, isoDate, validDate, pyRepr, strip, splitlines, dirname, basename, joinPath, normpath, decodeText, stripBom,
} from './text.js';
import { walkFiles, writeText, exists } from '../store/base.js';

/** Text as a CSS string literal. */
export function cssString(s) {
  return '"' + String(s).replace(/[\r\n]+/g, ' ').replaceAll('\\', '\\\\').replaceAll('"', '\\"').replaceAll('<', '\\3c ') + '"';
}

/** The snapshot's whole stylesheet: readable on screen, laid out for paper when printed
    (page margins, page numbers, no broken tables or figures, signature lines). */
export function snapshotCss(lab, noteId) {
  const primary = lab.color_primary, accent = lab.color_accent;
  return "body{max-width:860px;margin:32px auto;padding:0 20px;font:15px/1.5 -apple-system,BlinkMacSystemFont,"
    + "'Segoe UI',Helvetica,Arial,sans-serif;color:#1f2933}"
    + '.lab{display:flex;justify-content:space-between;gap:16px;font-size:13px;color:#5f6b7a;'
    + `border-bottom:3px solid ${accent};padding-bottom:6px;margin-bottom:18px}.lab b{color:${primary}}`
    + `h1{font-size:22px;margin:0 0 6px;color:${primary}}`
    + 'h2{border-bottom:1px solid #e3e8ee;padding-bottom:4px;margin-top:24px;font-size:18px}'
    + 'table{border-collapse:collapse;margin:8px 0;max-width:100%}th,td{text-align:left;padding:5px 9px;border-bottom:1px solid #e3e8ee;'
    + 'vertical-align:top;overflow-wrap:anywhere}p,li{overflow-wrap:anywhere}.meta td:first-child{color:#5f6b7a;white-space:nowrap}img{max-width:100%;border:1px solid #e3e8ee}'
    + 'code{background:#f1f5f9;padding:1px 4px;border-radius:4px;overflow-wrap:anywhere}pre{background:#f1f5f9;padding:10px;overflow-x:auto}'
    + '.sub{color:#5f6b7a;font-weight:400}.sign{display:none}'
    + '.foot{color:#5f6b7a;font-size:13px;margin-top:40px;border-top:1px solid #e3e8ee;padding-top:10px}'
    + '@page{margin:16mm 15mm 18mm}'
    + `@page{@bottom-left{content:${cssString(labLine(lab))};font:8pt Helvetica,Arial,sans-serif;color:#5f6b7a}`
    + `@bottom-right{content:${cssString(noteId)} "  page " counter(page) " of " counter(pages);`
    + 'font:8pt Helvetica,Arial,sans-serif;color:#5f6b7a}}'
    + '@media print{body{max-width:none;margin:0;padding:0;font-size:10.5pt}a{color:inherit;text-decoration:none}'
    + 'h1{font-size:16pt}h2{font-size:12.5pt;break-after:avoid}h3,h4{break-after:avoid}'
    + 'tr,img,pre,blockquote,.sign,.prov{break-inside:avoid}pre{white-space:pre-wrap}code,pre{background:none;padding:0}'
    + '.sign{display:grid;grid-template-columns:1fr 1fr;gap:10mm 12mm;margin-top:14mm;font-size:9.5pt;color:#5f6b7a}'
    + '.sign div{border-top:1px solid #1f2933;padding-top:3px}.foot{margin-top:8mm;font-size:8.5pt}}';
}

/** Every regular file under an experiment folder, in order, skipping what the operating system leaves behind. */
/** Files the operating system, Office, or a half-finished save leaves around. Everything else counts,
    hidden files included: .RData is data. */
export const isLitter = (name) => SKIP_NAMES.has(name.toLowerCase()) || name.startsWith('~$') || name.startsWith('._')
  || name.endsWith('.crswap') || (name.startsWith('.') && name.endsWith('.tmp'));

export async function folderFiles(store, folder) {
  return (await walkFiles(store, folder, { links: false })).filter((p) => !isLitter(basename(p))
    && !p.split('/').some((part) => part === '__pycache__' || part === '.eln-lock'));
}

async function dataUri(store, path, limit = 8000000) {
  if (path === '.' || path.startsWith('..')) return null;
  const mime = imageType(basename(path));
  if (!mime) return null;
  const s = await store.stat(path);
  if (!s || s.kind !== 'file' || s.size === 0 || s.size > limit) return null;
  return `data:${mime};base64,` + toBase64(await store.readBytes(path));
}

/** One note as a single HTML file: lab line, header table, body with images embedded, list of
    files, provenance (path and SHA-256 of the note). It opens in any browser and prints to PDF with
    page numbers and signature lines. `lab` comes from loadLab. */
export async function renderSnapshotHtml(store, note, generated = isoDate(), lab = null) {
  const settings = lab || await loadLab(store);
  const raw = await store.readBytes(note.path);
  const bodyMd = splitFrontMatter(decodeText(raw, false)).body;
  const noteDir = dirname(note.path);
  const embedded = new Map();
  for (const rel of imagePaths(bodyMd)) {
    if (!embedded.has(rel)) embedded.set(rel, await dataUri(store, normpath(joinPath(noteDir, rel))));
  }
  const meta = Object.entries(note.fields)
    .map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(Array.isArray(v) ? v.join(', ') : v) || '-'}</td></tr>`).join('');
  let filesHtml = '';
  const provenance = [['Record', `<code>${esc(note.path)}</code>`],
    ['SHA-256 of the note', `<code>${sha256Hex(raw)}</code>`],
    ['Snapshot generated', esc(generated)]];
  if (note.folder !== null) {
    const rows = [];
    const own = new RegExp(`^1-notes/${note.id}_(MANIFEST\\.sha256|snapshot_\\d{8}\\.html)$`);
    for (const p of await folderFiles(store, note.folder)) {
      if (own.test(p.slice(note.folder.length + 1))) continue; // the snapshot and the manifest describe the folder; they are not listed in it
      const size = (await store.stat(p)).size;
      rows.push(`<tr><td>${esc(p.slice(note.folder.length + 1))}</td><td>${thousands(size)}</td></tr>`);
    }
    filesHtml = '<h2>Files in this experiment folder</h2><table><tr><th>path</th><th>bytes</th></tr>' + rows.join('') + '</table>';
    provenance.push(['Checksums of every file', `<code>1-notes/${esc(note.id)}_MANIFEST.sha256</code> (written when the experiment is marked complete)`]);
  }
  const provHtml = '<h2>Provenance</h2><table class="meta prov">' + provenance.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join('') + '</table>';
  const signHtml = wantsSignatures(settings)
    ? '<div class=sign><div>Recorded by (signature, date)</div><div>Reviewed by (signature, date)</div></div>' : '';
  return '<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">'
    + `<title>${esc(note.id)} ${esc(note.get('title'))}</title>`
    + `<style>${snapshotCss(settings, note.id)}</style></head><body>`
    + `<div class=lab><span><b>${esc(settings.lab_name)}</b>${esc([settings.department, settings.institution].filter(Boolean).map((x) => ', ' + x).join(''))}</span>`
    + `<span>${esc(note.id)}</span></div>`
    + `<h1>${esc(note.id)} <span class=sub>${esc(note.get('title'))}</span></h1>`
    + `<table class=meta>${meta}</table>`
    + mdToHtml(bodyMd, { imgBase: '', linkIds: false, imgSrc: (rel) => embedded.get(rel) || rel })
    + filesHtml + provHtml + signHtml
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

/** { path: sha256 } from the manifest, or null when there is none. With strict, a manifest that is
    empty or has lines that are not `<hash>  <path>` is an error instead of being read as far as it goes. */
export async function readManifest(store, folder, expId, strict = false) {
  const path = manifestPath(folder, expId);
  if (!(await exists(store, path))) return null;
  const out = {};
  let bad = 0;
  for (const line of splitlines(stripBom(decodeText(await store.readBytes(path), false)))) {
    const m = /^([0-9a-f]{64})[ \t]+\*?(.+)$/.exec(line);
    if (m) out[m[2]] = m[1];
    else if (strip(line)) bad += 1;
  }
  const entries = Object.keys(out).length;
  if (strict && (bad || !entries)) {
    throw new ElnError(`${expId}: the manifest is damaged (${bad} unreadable line${bad !== 1 ? 's' : ''}, ${entries} `
      + 'entries). Mark the experiment complete again to write a new one', 'bad_manifest');
  }
  return out;
}

/** What changed since the manifest was written. -> { missing, modified, added, files } */
export async function verifyManifest(store, folder, expId) {
  const recorded = await readManifest(store, folder, expId, true);
  if (recorded === null) throw new ElnError(`${expId} ${NO_MANIFEST}`, 'no_manifest');
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
const NO_MANIFEST_COMPLETE = 'is complete, but there is no manifest to compare with. Mark it complete again to write one';
const NO_MANIFEST = 'has no manifest yet (one is written when the experiment is marked complete)';

export async function verifyExperiments(store, vault, id = '') {
  let targets;
  if (id) {
    const note = vault.get(id);
    if (note === null || note.kind !== 'experiment') throw new ElnError(`no experiment ${id}`, 'not_found');
    targets = [note];
  } else {
    targets = [];
    for (const n of vault.notes.experiment) {
      if (n.folder && n.id && (n.get('status') === 'complete' || await exists(store, manifestPath(n.folder, n.id)))) targets.push(n);
    }
  }
  const results = [];
  for (const n of targets) {
    if (!(await exists(store, manifestPath(n.folder, n.id)))) {
      results.push({ id: n.id, ok: false, missing: [], modified: [], added: [], files: 0, error: n.get('status') === 'complete' ? NO_MANIFEST_COMPLETE : NO_MANIFEST });
      continue;
    }
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
export async function renderSnapshot(store, vault, id, { when = isoDate(), out = '', lab = null } = {}) {
  const note = vault.get(id);
  if (note === null) throw new ElnError(`no note ${id}`, 'not_found');
  const path = out || snapshotPath(note, when);
  await writeText(store, path, await renderSnapshotHtml(store, note, when, lab));
  return path;
}

/** The close-out: check the note is written up, set status and date_completed, write a snapshot and
    a manifest, rebuild the index. -> { snapshot, manifest, warnings, files } */
export async function completeExperiment(store, id, { when = '', force = false, today = isoDate(), lab = null, generated = '' } = {}) {
  let vault = await loadVault(store);
  let note = vault.get(id);
  if (note === null || note.kind !== 'experiment' || note.folder === null) throw new ElnError(`no experiment ${id}`, 'not_found');
  /* completing again refreshes the snapshot and manifest; the completion date stays unless one is given */
  const already = note.get('status') === 'complete' && validDate(note.get('date_completed'));
  const date = when || (already ? note.get('date_completed') : today);
  if (!validDate(date)) throw new ElnError(`date must be YYYY-MM-DD (got ${pyRepr(date)})`, 'bad_date');
  const secs = sections(note.body);
  const empty = ['Results', 'Interpretation'].filter((s) => sectionIsEmpty(secs.get(s) || ''));
  if (empty.length && !force) {
    throw new ElnError(`${id}: the ${empty.join(' and ')} section${empty.length > 1 ? 's are' : ' is'} still empty. `
      + `Write ${empty.length > 1 ? 'them' : 'it'} first, or complete anyway (force).`, 'sections_empty', { empty, id });
  }
  const warnings = [];
  if (note.get('status') === 'abandoned') warnings.push('the status was abandoned; it is now complete');
  if (validDate(note.get('date_started')) && date < note.get('date_started')) {
    warnings.push(`the completion date ${date} is before the start date ${note.get('date_started')}`);
  }
  if (already && await exists(store, manifestPath(note.folder, id))) {
    try {
      const r = await verifyManifest(store, note.folder, id);
      const changed = [...r.modified.map((p) => `modified ${p}`), ...r.missing.map((p) => `missing ${p}`), ...r.added.map((p) => `added ${p}`)];
      if (changed.length) {
        warnings.push(`${changed.length} file${changed.length !== 1 ? 's' : ''} changed since the previous manifest `
          + `(${changed.slice(0, 5).join('; ')}${changed.length > 5 ? '; ...' : ''}). The new manifest records the current state`);
      }
    } catch (e) {
      if (!(e instanceof ElnError)) throw e;
      warnings.push(e.message);
    }
  }
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
  /* the snapshot may carry another date than the completion: an adopted folder is dated the day it was adopted */
  const snapshot = snapshotPath(note, generated || date);
  await writeText(store, snapshot, await renderSnapshotHtml(store, note, generated || date, lab));
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
