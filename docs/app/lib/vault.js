/* Reading the notebook: every note, parsed, plus what is wrong with the folder layout. */

import { KINDS, KIND_DIR, ID_FIELD, RE_EXP_FOLDER, ElnError } from './schema.js';
import { parseFrontMatter } from './frontmatter.js';
import { cmp, decodeText, splitlines, strip } from './text.js';

export class Note {
  constructor(kind, path, folder = null) {
    this.kind = kind;
    this.path = path; // relative to the notebook folder
    this.folder = folder; // the experiment folder, for experiments
    this.fields = Object.create(null);
    this.body = '';
    this.text = '';
    this.problems = [];
  }

  get id() {
    const v = this.fields[ID_FIELD[this.kind]];
    return typeof v === 'string' ? v : '';
  }

  /** A field as text; a list is joined with ', '. */
  get(key, fallback = '') {
    const v = key in this.fields ? this.fields[key] : fallback;
    if (Array.isArray(v)) return v.join(', ');
    return typeof v === 'string' ? v : fallback;
  }

  /** A field as a list. */
  getList(key) {
    const v = key in this.fields ? this.fields[key] : [];
    if (Array.isArray(v)) return v.map(String);
    return v ? [v] : [];
  }

  /** Plain data, for JSON. */
  toJSON() {
    return { kind: this.kind, id: this.id, path: this.path, folder: this.folder, fields: { ...this.fields } };
  }
}

export class Vault {
  constructor() {
    this.notes = { experiment: [], protocol: [], sample: [], project: [] };
    this.byId = new Map();
    this.folderIssues = []; // [path, message]
  }

  allNotes() {
    return KINDS.flatMap((k) => this.notes[k]);
  }

  get(id) {
    return this.byId.get(id) || null;
  }
}

export function isNoteName(name) {
  return name.endsWith('.md') && name.length > 3 && !/^[._~]/.test(name) && name.toLowerCase() !== 'readme.md';
}

export async function readNote(store, kind, path, folder = null) {
  const note = new Note(kind, path, folder);
  let bytes;
  try {
    bytes = await store.readBytes(path);
  } catch (e) {
    note.problems.push(`cannot read: ${e.message}`);
    return note;
  }
  try {
    note.text = decodeText(bytes, true);
  } catch (e) {
    note.text = decodeText(bytes, false);
    note.problems.push('file is not UTF-8 text');
    return note;
  }
  const parsed = parseFrontMatter(note.text);
  note.fields = parsed.fields;
  note.body = parsed.body;
  note.problems.push(...parsed.problems);
  return note;
}

export async function loadVault(store) {
  const vault = new Vault();
  const pending = [];
  const expEntries = await store.list(KIND_DIR.experiment);
  if (expEntries) {
    const folders = expEntries.filter((e) => e.kind === 'dir' && !e.name.startsWith('.')).map((e) => e.name).sort(cmp);
    for (const name of folders) {
      const folder = `${KIND_DIR.experiment}/${name}`;
      const m = RE_EXP_FOLDER.exec(name);
      const folderId = m ? m[1] : null;
      if (!m) vault.folderIssues.push([folder, 'folder name does not match {ID}_{slug} (an older folder? Adopt it: the tool gives it an ID and moves its files in)']);
      const notesDir = `${folder}/1-notes`;
      const listing = await store.list(notesDir);
      let noteName = folderId ? `${folderId}.md` : null;
      if (noteName === null || !listing || !listing.some((e) => e.name === noteName)) {
        /* fall back to any note in 1-notes so its problems are still reported */
        const candidates = listing ? listing.filter((e) => e.kind === 'file' && isNoteName(e.name)).map((e) => e.name).sort(cmp) : [];
        if (noteName !== null && !candidates.length) {
          vault.folderIssues.push([folder, `no note at 1-notes/${folderId}.md (if this folder was just made on another computer, wait for the sync to finish and check again)`]);
          continue;
        }
        if (!candidates.length) continue;
        noteName = candidates[0];
        if (folderId) vault.folderIssues.push([folder, `note should be named 1-notes/${folderId}.md, found ${noteName}`]);
      }
      pending.push(['experiment', readNote(store, 'experiment', `${notesDir}/${noteName}`, folder)]);
    }
  }
  for (const kind of ['protocol', 'sample', 'project']) {
    const entries = await store.list(KIND_DIR[kind]);
    if (!entries) continue;
    const names = entries.filter((e) => e.kind === 'file' && isNoteName(e.name)).map((e) => e.name).sort(cmp);
    for (const name of names) pending.push([kind, readNote(store, kind, `${KIND_DIR[kind]}/${name}`)]);
  }
  for (const [kind, promise] of pending) vault.notes[kind].push(await promise);
  for (const note of vault.allNotes()) {
    if (note.id && !vault.byId.has(note.id)) vault.byId.set(note.id, note);
  }
  return vault;
}

/** Map of '## ' section title -> text, in order. */
export function sections(body) {
  const out = new Map();
  let current = null;
  let buf = [];
  for (const line of splitlines(body)) {
    if (line.startsWith('## ')) {
      if (current !== null) out.set(current, strip(buf.join('\n')));
      current = strip(line.slice(3));
      buf = [];
    } else if (current !== null) buf.push(line);
  }
  if (current !== null) out.set(current, strip(buf.join('\n')));
  return out;
}

/** Replace or extend the text under one '## ' heading. Returns the new note text. */
export function writeSection(text, section, content, mode = 'replace') {
  const lines = splitlines(text);
  const wanted = strip(String(section)).toLowerCase();
  const start = lines.findIndex((l) => l.startsWith('## ') && strip(l.slice(3)).toLowerCase() === wanted);
  if (start < 0) {
    throw new ElnError(`the note has no '## ${strip(String(section))}' section. Its sections are: ${[...sections(text).keys()].join(', ')}`, 'no_section');
  }
  if (splitlines(String(content)).some((l) => /^#{1,2}\s/.test(l))) {
    throw new ElnError("the text contains a line starting with '# ' or '## ', which would start a new section. Use '### ' for a sub-heading", 'bad_content');
  }
  let end = lines.findIndex((l, i) => i > start && l.startsWith('## '));
  if (end < 0) end = lines.length;
  const fresh = splitlines(strip(String(content)));
  let middle;
  if (mode === 'append') {
    const kept = lines.slice(start + 1, end);
    while (kept.length && !strip(kept[kept.length - 1])) kept.pop();
    middle = [...kept, '', ...fresh, ''];
    if (!strip(kept.join(''))) middle = ['', ...fresh, ''];
  } else middle = ['', ...fresh, ''];
  return [...lines.slice(0, start + 1), ...middle, ...lines.slice(end)].join('\n').replace(/\n+$/, '') + '\n';
}

/** True when a section holds only comments, sub-headers, or empty bullets. */
export function sectionIsEmpty(text) {
  let t = (text || '').replace(/<!--.*?-->/gs, '');
  t = t.replace(/^#+\s.*$/gm, '');
  t = t.replace(/[-*]\s*(\[ \])?\s*$/gm, '');
  return !strip(t);
}

export const ciIn = (needle, items) => items.map((x) => x.toLowerCase()).includes(needle.toLowerCase());

export function sortedById(notes) {
  return notes.filter((n) => n.id).sort((a, b) => cmp(a.id, b.id));
}
