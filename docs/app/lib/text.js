/* Text helpers that behave like the Python ones scripts/eln.py uses, so both tools read and write
   the same bytes. Pure functions, no I/O. */

const WS = '\\t\\n\\v\\f\\r\\x1c\\x1d\\x1e\\x1f \\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000';
const RE_LEFT = new RegExp(`^[${WS}]+`);
const RE_RIGHT = new RegExp(`[${WS}]+$`);
const RE_WS_RUN = new RegExp(`[${WS}]+`);

export const lstrip = (s) => s.replace(RE_LEFT, '');
export const rstrip = (s) => s.replace(RE_RIGHT, '');
export const strip = (s) => lstrip(rstrip(s));

/** str.strip(chars): remove any of `chars` from both ends. */
export function stripChars(s, chars) {
  let a = 0, b = s.length;
  while (a < b && chars.includes(s[a])) a++;
  while (b > a && chars.includes(s[b - 1])) b--;
  return s.slice(a, b);
}

export function lstripChars(s, chars) {
  let a = 0;
  while (a < s.length && chars.includes(s[a])) a++;
  return s.slice(a);
}

const RE_LINE_BREAKS = /[\r\n\v\f\x1c\x1d\x1e\x85\u2028\u2029]+/g;
/** A header value is one line: any line break inside it becomes a space. */
export const oneLine = (value) => String(value === null || value === undefined ? '' : value).replace(RE_LINE_BREAKS, ' ');
/** Text without a leading byte-order mark (Windows Notepad writes one). */
export const stripBom = (text) => (text.charCodeAt(0) === 0xfeff ? text.slice(1) : text);

/** str.splitlines(): no trailing empty line, and '' gives []. */
export function splitlines(s) {
  if (s === '') return [];
  const parts = s.split(/\r\n|[\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029]/);
  if (parts[parts.length - 1] === '') parts.pop();
  return parts;
}

/** str.split() with no argument: on runs of whitespace, no empty strings. */
export const words = (s) => strip(s).split(RE_WS_RUN).filter(Boolean);

/** repr() of a string, as Python prints it inside validator messages. */
export function pyRepr(value) {
  const s = String(value);
  const q = s.includes("'") && !s.includes('"') ? '"' : "'";
  let out = '';
  for (const ch of s) {
    const c = ch.codePointAt(0);
    if (ch === '\\') out += '\\\\';
    else if (ch === q) out += '\\' + q;
    else if (ch === '\n') out += '\\n';
    else if (ch === '\r') out += '\\r';
    else if (ch === '\t') out += '\\t';
    else if (ch !== ' ' && /[\p{Cc}\p{Cf}\p{Cs}\p{Co}\p{Cn}\p{Zl}\p{Zp}\p{Zs}]/u.test(ch)) {
      out += c <= 0xff ? '\\x' + c.toString(16).padStart(2, '0')
        : c <= 0xffff ? '\\u' + c.toString(16).padStart(4, '0')
          : '\\U' + c.toString(16).padStart(8, '0');
    } else out += ch;
  }
  return q + out + q;
}

const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#x27;' };
/** html.escape(s, quote=True) */
export const esc = (s) => String(s === null || s === undefined ? '' : s).replace(/[&<>"']/g, (c) => ESC[c]);
const UNESC = { amp: '&', lt: '<', gt: '>', quot: '"', '#x27': "'" };
export const unesc = (s) => s.replace(/&(amp|lt|gt|quot|#x27);/g, (_, n) => UNESC[n]);

/** Plain code-unit ordering, the same order Python gives ASCII and BMP text. */
export const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

/** Order paths the way Python orders pathlib.Path objects: component by component. */
export function cmpPath(a, b) {
  const pa = a.split('/'), pb = b.split('/');
  for (let i = 0; i < Math.min(pa.length, pb.length); i++) {
    if (pa[i] !== pb[i]) return cmp(pa[i], pb[i]);
  }
  return pa.length - pb.length;
}

export const thousands = (n) => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');

/* ---- paths: always POSIX, relative to the notebook folder, no leading slash ---- */

export function joinPath(...parts) {
  return parts.filter((p) => p !== '' && p !== null && p !== undefined).join('/').replace(/\/{2,}/g, '/');
}

export function dirname(p) {
  const i = p.lastIndexOf('/');
  return i < 0 ? '' : p.slice(0, i);
}

export function basename(p) {
  return p.slice(p.lastIndexOf('/') + 1);
}

/** Path.stem: the name without its last extension. */
export function stem(p) {
  const name = basename(p);
  const i = name.lastIndexOf('.');
  return i > 0 ? name.slice(0, i) : name;
}

/** The last extension including the dot, or ''. */
export function extname(p) {
  const name = basename(p);
  const i = name.lastIndexOf('.');
  return i > 0 ? name.slice(i) : '';
}

/** os.path.normpath for POSIX paths. */
export function normpath(p) {
  if (p === '') return '.';
  const absolute = p.startsWith('/');
  const out = [];
  for (const part of p.split('/')) {
    if (part === '' || part === '.') continue;
    if (part === '..') {
      if (out.length && out[out.length - 1] !== '..') out.pop();
      else if (!absolute) out.push('..');
    } else out.push(part);
  }
  const joined = out.join('/');
  return absolute ? '/' + joined : joined || '.';
}

/* ---- dates: always local, always YYYY-MM-DD ---- */

const pad = (n, w = 2) => String(n).padStart(w, '0');

export function isoDate(d = new Date()) {
  return `${pad(d.getFullYear(), 4)}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function validDate(s) {
  if (typeof s !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
  const [y, m, d] = s.split('-').map(Number);
  if (y < 1 || m < 1 || m > 12 || d < 1) return false;
  const days = [31, (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0 ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return d <= days[m - 1];
}

/** ISO date `days` before `iso`. */
export function daysBefore(iso, days) {
  const [y, m, d] = iso.split('-').map(Number);
  const t = new Date(Date.UTC(y, m - 1, d) - days * 86400000);
  return `${pad(t.getUTCFullYear(), 4)}-${pad(t.getUTCMonth() + 1)}-${pad(t.getUTCDate())}`;
}

/* ---- bytes ---- */

const B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';

export function toBase64(bytes) {
  let out = '';
  for (let i = 0; i < bytes.length; i += 3) {
    const a = bytes[i], b = bytes[i + 1], c = bytes[i + 2];
    out += B64[a >> 2] + B64[((a & 3) << 4) | ((b ?? 0) >> 4)];
    out += i + 1 < bytes.length ? B64[((b & 15) << 2) | ((c ?? 0) >> 6)] : '=';
    out += i + 2 < bytes.length ? B64[c & 63] : '=';
  }
  return out;
}

export function fromBase64(text) {
  const clean = text.replace(/[^A-Za-z0-9+/]/g, '');
  const out = new Uint8Array(Math.floor((clean.length * 3) / 4));
  let n = 0;
  for (let i = 0; i < clean.length; i += 4) {
    const v = [0, 1, 2, 3].map((k) => (i + k < clean.length ? B64.indexOf(clean[i + k]) : 0));
    const word = (v[0] << 18) | (v[1] << 12) | (v[2] << 6) | v[3];
    if (n < out.length) out[n++] = (word >> 16) & 255;
    if (n < out.length) out[n++] = (word >> 8) & 255;
    if (n < out.length) out[n++] = word & 255;
  }
  return out;
}

export const utf8 = (s) => new TextEncoder().encode(s);

/** Decode UTF-8 the way Python's read_text does: keep a BOM, turn CRLF and CR into LF.
    With fatal=true, bytes that are not UTF-8 throw. */
export function decodeText(bytes, fatal = false) {
  const text = new TextDecoder('utf-8', { fatal, ignoreBOM: true }).decode(bytes);
  return text.replace(/\r\n?/g, '\n');
}
