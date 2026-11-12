/* A small, safe Markdown renderer: headings, lists, tables, images, links, emphasis, code.
   Everything is escaped first, so nothing in a note can inject markup. Produces the same HTML as
   md_to_html in scripts/eln.py; it is used for the page, for HTML snapshots, and for .eln archives. */

import { esc, unesc, strip, stripChars, lstripChars, splitlines, normpath } from './text.js';

const W = '[\\p{L}\\p{N}_]';
/* \b that knows about non-ASCII letters, as Python's does */
const B = `(?:(?<=${W})(?!${W})|(?<!${W})(?=${W}))`;
const RE_ID_LINK = new RegExp(`${B}([A-Z]{2,4}[eipacmtrsg]\\d{4}|P_[A-Za-z0-9][A-Za-z0-9-]*)${B}`, 'gu');
const RE_STAR = new RegExp(`(?<![\\p{L}\\p{N}_*])\\*([^*\\n]+)\\*(?![\\p{L}\\p{N}_*])`, 'gu');
const RE_UNDER = new RegExp(`(?<!${W})_([^_\\n]+)_(?!${W})`, 'gu');

const joinBase = (base, src) => (base ? (base.endsWith('/') ? base + src : base + '/' + src) : src);

function inline(text, r) {
  let s = esc(text);
  s = s.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (_, alt, raw) => {
    const src = unesc(raw);
    if (/^(https?:\/\/|\/|data:)/.test(src)) return `<img alt="${alt}" src="${esc(src)}">`;
    const rel = normpath(joinBase(r.imgBase, src));
    return `<img alt="${alt}" src="${esc(r.imgSrc ? r.imgSrc(rel) : rel)}">`;
  });
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target=_blank rel=noopener>$1</a>');
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
  s = s.replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>');
  s = s.replace(RE_STAR, '<i>$1</i>');
  s = s.replace(RE_UNDER, '<i>$1</i>');
  if (r.linkIds) s = s.replace(RE_ID_LINK, (_, id) => `<a href="${r.linkHref(id)}">${id}</a>`);
  return s;
}

/** Markdown -> HTML.
    imgBase: folder the note's relative image paths start from.
    imgSrc(rel): what to put in src for a relative image (a route, a data URI, a path).
    linkIds: turn bare IDs (JSRe0002, P_WesternBlot) into links; linkHref(id) gives the address. */
export function mdToHtml(text, { imgBase = '', linkIds = true, imgSrc = null, linkHref = (id) => `/note/${id}` } = {}) {
  const r = { imgBase, linkIds, imgSrc, linkHref };
  const lines = splitlines((text || '').replace(/<!--.*?-->/gs, ''));
  const out = [];
  let para = [];
  const flush = () => {
    if (para.length) {
      out.push('<p>' + inline(para.join(' '), r) + '</p>');
      para = [];
    }
  };
  const n = lines.length;
  let i = 0;
  while (i < n) {
    const line = lines[i];
    const s = strip(line);
    if (s.startsWith('```')) {
      flush();
      i += 1;
      const buf = [];
      while (i < n && !strip(lines[i]).startsWith('```')) buf.push(lines[i++]);
      out.push('<pre>' + esc(buf.join('\n')) + '</pre>');
      i += 1;
      continue;
    }
    let m = /^(#{1,6})\s+(.*)$/.exec(s);
    if (m) {
      flush();
      out.push(`<h${m[1].length}>${inline(m[2], r)}</h${m[1].length}>`);
      i += 1;
      continue;
    }
    if (/^(-{3,}|\*{3,})$/.test(s)) {
      flush();
      out.push('<hr>');
      i += 1;
      continue;
    }
    if (s.startsWith('|') && i + 1 < n && /^\|?\s*:?-{2,}/.test(strip(lines[i + 1]))) {
      flush();
      const header = stripChars(s, '|').split('|').map(strip);
      out.push('<table><tr>' + header.map((c) => `<th>${inline(c, r)}</th>`).join('') + '</tr>');
      i += 2;
      while (i < n && strip(lines[i]).startsWith('|')) {
        const cells = stripChars(strip(lines[i]), '|').split('|').map(strip);
        out.push('<tr>' + cells.map((c) => `<td>${inline(c, r)}</td>`).join('') + '</tr>');
        i += 1;
      }
      out.push('</table>');
      continue;
    }
    if (/^\s*[-*]\s+(.*)$/.test(line)) {
      flush();
      out.push('<ul>');
      while (i < n && /^\s*[-*]\s+/.test(lines[i])) {
        let item = lines[i].replace(/^\s*[-*]\s+/, '');
        let box = '';
        m = /^\[([ xX])\]\s*(.*)$/.exec(item);
        if (m) {
          box = strip(m[1]) ? '&#9745; ' : '&#9744; ';
          item = m[2];
        }
        out.push(`<li>${box}${inline(item, r)}</li>`);
        i += 1;
      }
      out.push('</ul>');
      continue;
    }
    if (/^\s*\d+\.\s+/.test(line)) {
      flush();
      out.push('<ol>');
      while (i < n && /^\s*\d+\.\s+/.test(lines[i])) {
        out.push(`<li>${inline(lines[i].replace(/^\s*\d+\.\s+/, ''), r)}</li>`);
        i += 1;
      }
      out.push('</ol>');
      continue;
    }
    if (s.startsWith('>')) {
      flush();
      out.push(`<blockquote>${inline(lstripChars(s, '> '), r)}</blockquote>`);
      i += 1;
      continue;
    }
    if (!s) {
      flush();
      i += 1;
      continue;
    }
    para.push(s);
    i += 1;
  }
  flush();
  return out.join('\n');
}

/** The relative image paths a note's body refers to (after imgBase is applied). */
export function imagePaths(text, imgBase = '') {
  const found = [];
  mdToHtml(text, { imgBase, linkIds: false, imgSrc: (rel) => { found.push(rel); return rel; } });
  return found;
}
