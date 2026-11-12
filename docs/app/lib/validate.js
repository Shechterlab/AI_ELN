/* Check: read every note and folder and list what does not follow the conventions.
   ERROR must be fixed; WARN is advice. Same rules and same wording as `eln.py validate`. */

import {
  KINDS, KIND_DIR, VAULT_DIRS, ID_FIELD, ID_PATTERN, REQUIRED, SHOULD, STATUS, DATE_FIELDS, REF_FIELDS,
  REQUIRED_SECTIONS, SUBFOLDERS, NAMED_SUBFOLDERS, EXEMPT_FILENAMES, SAMPLE_LETTERS, SAMPLE_TYPES,
  RE_EXP_FOLDER, RE_SAMPLE_ID,
} from './schema.js';
import { sections, sectionIsEmpty } from './vault.js';
import { templateKeys } from './templates.js';
import { strip, pyRepr, validDate, basename, stem, cmp, cmpPath } from './text.js';
import { walkFiles } from '../store/base.js';

const RE_SYNC_CONFLICT = /conflicted copy/i; // Dropbox's phrase; OneDrive copies fail the ID-prefix rule instead

/** Files a sync service made when two people edited the same file while offline. */
export async function syncConflictFiles(store) {
  const out = [];
  for (const d of VAULT_DIRS) {
    for (const p of await walkFiles(store, d)) {
      if (RE_SYNC_CONFLICT.test(basename(p))) out.push(p);
    }
  }
  return out.sort(cmpPath);
}

/** -> [{ level: 'ERROR' | 'WARN', path, message }] */
export async function validateVault(store, vault) {
  const issues = [];
  const E = (path, message) => issues.push({ level: 'ERROR', path, message });
  const W = (path, message) => issues.push({ level: 'WARN', path, message });

  for (const [folder, message] of vault.folderIssues) E(folder, message);
  for (const p of await syncConflictFiles(store)) {
    W(p, 'sync-conflict copy (two people edited the same file while offline): compare it with the '
      + 'original, keep one, delete the other' + (p.split('/').includes('Inventory') ? ', then re-run index' : ''));
  }

  const knownKeys = {};
  for (const kind of KINDS) knownKeys[kind] = new Set([...(await templateKeys(store, kind)), 'type']);
  const seenIds = new Map();

  for (const note of vault.allNotes()) {
    const rel = note.path;
    const kind = note.kind;
    for (const p of note.problems) E(rel, p);
    if (!Object.keys(note.fields).length) continue;

    const typ = note.get('type');
    if (typ !== kind) E(rel, `type is ${pyRepr(typ)}, expected ${pyRepr(kind)}`);

    for (const key of REQUIRED[kind]) {
      if (!strip(note.get(key))) E(rel, `required field '${key}' is missing or empty`);
    }
    for (const key of SHOULD[kind]) {
      if (key in note.fields && !strip(note.get(key))) W(rel, `'${key}' is empty`);
    }
    for (const key of Object.keys(note.fields)) {
      if (!knownKeys[kind].has(key)) W(rel, `unknown header key '${key}' (not in templates/${kind}.md - typo?)`);
    }

    const nid = note.id;
    if (nid) {
      if (!ID_PATTERN[kind].test(nid)) E(rel, `${ID_FIELD[kind]} ${pyRepr(nid)} does not match the ${kind} ID pattern`);
      if (seenIds.has(nid)) E(rel, `duplicate ID ${nid} (also in ${seenIds.get(nid)})`);
      else seenIds.set(nid, rel);
    }

    const status = note.get('status');
    if (status && !STATUS[kind].includes(status)) E(rel, `status ${pyRepr(status)} is not one of ${STATUS[kind].join(' | ')}`);
    for (const key of DATE_FIELDS[kind]) {
      const v = note.get(key);
      if (v && !validDate(v)) E(rel, `'${key}' must be YYYY-MM-DD (got ${pyRepr(v)})`);
    }

    for (const [key, targetKind] of Object.entries(REF_FIELDS[kind])) {
      for (const ref of note.getList(key)) {
        const target = vault.get(ref);
        if (target === null) W(rel, `'${key}' refers to ${ref}, which does not exist in ${KIND_DIR[targetKind]}/`);
        else if (target.kind !== targetKind) W(rel, `'${key}' refers to ${ref}, which is a ${target.kind}, not a ${targetKind}`);
      }
    }

    const secs = sections(note.body);
    for (const name of REQUIRED_SECTIONS[kind]) {
      if (!secs.has(name)) W(rel, `body is missing the '## ${name}' section`);
    }

    if (kind === 'experiment') await validateExperiment(store, note, secs, E, W);
    else if (kind === 'sample') {
      const m = nid ? RE_SAMPLE_ID.exec(nid) : null;
      const stype = note.get('sample_type');
      if (stype && !(stype in SAMPLE_TYPES)) E(rel, `sample_type ${pyRepr(stype)} is not one of ${Object.keys(SAMPLE_TYPES).join(', ')}`);
      else if (m && stype && SAMPLE_LETTERS[m[2]] !== stype) {
        E(rel, `ID letter '${m[2]}' means ${SAMPLE_LETTERS[m[2]]}, but sample_type is ${pyRepr(stype)}`);
      }
      if (nid && stem(note.path) !== nid) E(rel, `filename should be ${nid}.md`);
    } else if (nid && stem(note.path) !== nid) E(rel, `filename should be ${nid}.md`);
  }
  return issues;
}

async function validateExperiment(store, note, secs, E, W) {
  const rel = note.path;
  const folder = note.folder;
  const nid = note.id;
  if (folder !== null) {
    const name = basename(folder);
    const m = RE_EXP_FOLDER.exec(name);
    const folderId = m ? m[1] : null;
    if (folderId && nid && folderId !== nid) E(rel, `experiment_id ${nid} does not match folder ${name}`);
    const top = (await store.list(folder)) || [];
    const dirs = new Set(top.filter((e) => e.kind === 'dir').map((e) => e.name));
    const missing = SUBFOLDERS.filter((s) => !dirs.has(s));
    if (missing.length) E(folder, `missing subfolder(s): ${missing.join(', ')}`);
    const checkId = folderId || nid;
    if (checkId) {
      for (const sub of NAMED_SUBFOLDERS) {
        if (!dirs.has(sub)) continue;
        const entries = ((await store.list(`${folder}/${sub}`)) || []).sort((a, b) => cmp(a.name, b.name));
        for (const f of entries) {
          if (f.kind !== 'file' || f.name.startsWith('.') || EXEMPT_FILENAMES.has(f.name.toLowerCase())) continue;
          if (!(f.name.startsWith(checkId + '_') || f.name.startsWith(checkId + '.'))) {
            W(`${folder}/${sub}/${f.name}`, `filename should start with ${checkId}_ (see CONVENTIONS.md section 3)`);
          }
        }
      }
    }
  }
  if (note.get('status') === 'complete') {
    if (!note.get('date_completed')) W(rel, 'status is complete but date_completed is empty');
    for (const name of ['Results', 'Interpretation']) {
      if (secs.has(name) && sectionIsEmpty(secs.get(name))) W(rel, `status is complete but the '## ${name}' section is empty`);
    }
  }
}

const plural = (n, word) => `${n} ${word}${n !== 1 ? 's' : ''}`;

export function countIssues(vault, issues) {
  const errors = issues.filter((i) => i.level === 'ERROR').length;
  const warnings = issues.length - errors;
  const counts = KINDS.map((k) => plural(vault.notes[k].length, k)).join(', ');
  return { errors, warnings, counts };
}

/** The same text `eln.py validate` prints. -> { text, ok } */
export function formatIssues(vault, issues, strict = false) {
  const byPath = new Map();
  for (const i of issues) {
    if (!byPath.has(i.path)) byPath.set(i.path, []);
    byPath.get(i.path).push(i);
  }
  const lines = [];
  for (const path of [...byPath.keys()].sort(cmp)) {
    lines.push(path);
    for (const i of byPath.get(path)) lines.push(`  ${i.level.padEnd(5)}  ${i.message}`);
  }
  const { errors, warnings, counts } = countIssues(vault, issues);
  lines.push(`Checked ${counts}: ${plural(errors, 'error')}, ${plural(warnings, 'warning')}`
    + (strict && warnings ? ' (strict: warnings count as errors)' : ''));
  return { text: lines.join('\n') + '\n', ok: !(errors || (strict && warnings)) };
}
