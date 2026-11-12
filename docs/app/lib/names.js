/* Names: slugs, IDs, folder and file names. Pure functions; the same rules as scripts/eln.py. */

import { RE_EXP_ID, RE_SAMPLE_ID, RE_INITIALS } from './schema.js';
import { extname, stem, validDate, stripChars } from './text.js';

/** 'SNRPB chromatin retention: KCl' -> 'SNRPB-chromatin-retention-KCl'. Case kept; cut on a word boundary. */
export function slugify(text, maxLen = 60) {
  /* accents are dropped, not the letter: "Résumé" -> "Resume" */
  const plain = String(text === null || text === undefined ? '' : text).normalize('NFKD').replace(/\p{M}/gu, '');
  let slug = plain.replace(/[^A-Za-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  if (slug.length > maxLen) {
    const cut = slug.slice(0, maxLen + 1);
    slug = cut.includes('-') ? cut.slice(0, cut.lastIndexOf('-')) : slug.slice(0, maxLen);
  }
  return slug.replace(/^-+|-+$/g, '');
}

/** '' unless the text is 2 to 4 letters. */
export function cleanInitials(text) {
  const s = String(text === null || text === undefined ? '' : text).trim().toUpperCase();
  return RE_INITIALS.test(s) ? s : '';
}

export const pad4 = (n) => String(Math.max(1, Math.min(9999, Math.trunc(Number(n)) || 1))).padStart(4, '0');
export const experimentId = (initials, number) => `${initials}e${pad4(number)}`;

export function folderName(id, title) {
  const slug = slugify(title);
  return slug ? `${id}_${slug}` : id;
}

/** Highest existing number for these initials (and sample letter), plus one. */
export function nextNumber(existing, initials, letter = 'e') {
  let highest = 0;
  const pattern = letter === 'e' ? RE_EXP_ID : RE_SAMPLE_ID;
  for (const candidate of existing) {
    const m = pattern.exec(candidate);
    if (m && m[1] === initials && (letter === 'e' || m[2] === letter)) highest = Math.max(highest, parseInt(m[m.length - 1], 10));
  }
  return highest + 1;
}

/** The name a file should have inside an experiment folder:
    {ID}[_R]_{words-with-hyphens}[_{YYYYMMDD}].ext
    `description` falls back to the original file's name. */
export function fileNameFor(id, { originalName = '', description = '', result = false, date = '' } = {}) {
  const ext = extname(originalName).replace(/[^A-Za-z0-9.]/g, '');
  let words = slugify(description || stem(originalName));
  /* a file that already starts with the ID keeps the rest of its name */
  if (!description && (originalName.startsWith(id + '_') || originalName.startsWith(id + '.'))) return originalName;
  if (!words) words = 'file';
  const stamp = date ? '_' + date.replaceAll('-', '') : '';
  return `${id}${result ? '_R' : ''}_${words}${stamp}${ext}`;
}

export function yyyymmdd(d = new Date()) {
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`;
}

const RE_DATE_IN_NAME = /(?<!\d)((?:19|20)\d{2})[-_.]?(0[1-9]|1[0-2])[-_.]?(0[1-9]|[12]\d|3[01])(?!\d)/;

/** [title, date or ''] read from an old folder's name: '2019-03-04_PRMT5 western' -> ['PRMT5 western', '2019-03-04']. */
export function guessFromFolderName(input) {
  let name = String(input);
  let when = '';
  const m = RE_DATE_IN_NAME.exec(name);
  if (m && validDate(`${m[1]}-${m[2]}-${m[3]}`)) {
    when = `${m[1]}-${m[2]}-${m[3]}`;
    name = name.slice(0, m.index) + ' ' + name.slice(m.index + m[0].length);
  }
  return [stripChars(name.replace(/[\s_]+/g, ' '), ' -_.,'), when];
}
