/* The note header: a flat subset of YAML. `key: value` or `key: [a, b]`, one per line, no nesting.
   Same grammar as scripts/eln.py (see docs/CONVENTIONS.md, section 4). */

import { RE_KEY } from './schema.js';
import { strip, rstrip, lstrip, splitlines, pyRepr } from './text.js';

/** -> { header: string[] | null, body, error } */
export function splitFrontMatter(text) {
  const lines = splitlines(text);
  if (!lines.length || strip(lines[0]) !== '---') {
    return { header: null, body: text, error: "no YAML header (file must start with a '---' line)" };
  }
  for (let i = 1; i < lines.length; i++) {
    if (strip(lines[i]) === '---') return { header: lines.slice(1, i), body: lines.slice(i + 1).join('\n'), error: null };
  }
  return { header: null, body: text, error: "unterminated YAML header (missing closing '---')" };
}

/** Drop a trailing ' # comment' that is outside quotes. */
export function stripComment(s) {
  let quote = null;
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (quote) {
      if (ch === quote) quote = null;
    } else if (ch === '"' || ch === "'") quote = ch;
    else if (ch === '#' && (i === 0 || s[i - 1] === ' ' || s[i - 1] === '\t')) return rstrip(s.slice(0, i));
  }
  return s;
}

function unquote(raw) {
  const s = strip(raw);
  if (s.length >= 2 && s[0] === s[s.length - 1] && (s[0] === '"' || s[0] === "'")) {
    const inner = s.slice(1, -1);
    return s[0] === '"' ? inner.replaceAll('\\"', '"').replaceAll('\\\\', '\\') : inner;
  }
  return s;
}

/** Split 'a, b, "c, d"' on commas that are outside quotes. */
function splitList(inner) {
  const items = [];
  let buf = '', quote = null;
  for (const ch of inner) {
    if (quote) {
      buf += ch;
      if (ch === quote) quote = null;
    } else if (ch === '"' || ch === "'") {
      quote = ch;
      buf += ch;
    } else if (ch === ',') {
      items.push(buf);
      buf = '';
    } else buf += ch;
  }
  items.push(buf);
  return items.filter((x) => strip(x)).map(unquote);
}

export function parseValue(raw) {
  const s = strip(raw);
  return s.startsWith('[') && s.endsWith(']') ? splitList(s.slice(1, -1)) : unquote(s);
}

/** -> { fields, problems }. `fields` keeps the order of the lines. */
export function parseHeaderLines(lines) {
  const fields = Object.create(null);
  const problems = [];
  for (const line of lines) {
    const raw = rstrip(line);
    if (!strip(raw) || lstrip(raw).startsWith('#')) continue;
    if (raw[0] === ' ' || raw[0] === '\t') {
      problems.push(`indented line in header (nesting is not allowed): ${pyRepr(strip(raw))}`);
      continue;
    }
    if (raw.startsWith('- ')) {
      problems.push(`block list in header (use [a, b] instead): ${pyRepr(raw)}`);
      continue;
    }
    const colon = raw.indexOf(':');
    if (colon < 0) {
      problems.push(`header line is not 'key: value': ${pyRepr(raw)}`);
      continue;
    }
    const key = strip(raw.slice(0, colon));
    if (!RE_KEY.test(key)) {
      problems.push(`bad header key ${pyRepr(key)} (use snake_case)`);
      continue;
    }
    if (key in fields) problems.push(`duplicate header key ${pyRepr(key)}`);
    fields[key] = parseValue(stripComment(raw.slice(colon + 1)));
  }
  return { fields, problems };
}

/** -> { fields, body, problems } */
export function parseFrontMatter(text) {
  const { header, body, error } = splitFrontMatter(text);
  if (header === null) return { fields: Object.create(null), body, problems: [error || 'bad header'] };
  const { fields, problems } = parseHeaderLines(header);
  return { fields, body, problems };
}

export function quoteIfNeeded(input) {
  const value = input === null || input === undefined ? '' : String(input);
  if (value === '') return '';
  const needs = value.includes(': ') || value.includes(' #') || value.includes(',')
    || '[]{}#&*!|>\'"%@`'.includes(value[0]) || value !== strip(value) || value.endsWith(':');
  return needs ? '"' + value.replaceAll('\\', '\\\\').replaceAll('"', '\\"') + '"' : value;
}

export function formatValue(value) {
  if (Array.isArray(value)) {
    return '[' + value.filter((v) => strip(String(v))).map((v) => quoteIfNeeded(String(v))).join(', ') + ']';
  }
  return quoteIfNeeded(String(value));
}

/** 'a, b,c' -> ['a', 'b', 'c'] */
export function csvItems(text) {
  if (!text) return [];
  return String(text).split(',').map(strip).filter(Boolean);
}

/** 'active   # a | b' -> ['active', '   # a | b'] */
export function splitValueComment(rest) {
  const stripped = stripComment(rest);
  return [strip(stripped), rest.startsWith(stripped) ? rest.slice(stripped.length) : ''];
}

/** Replace one header line's value, keeping its trailing comment; add the key if it is absent.
    Works on lines, so nothing else in the file changes. Returns the new text. */
export function setHeaderField(text, key, value, what = 'the note') {
  const lines = splitlines(text);
  if (!lines.length || strip(lines[0]) !== '---') throw new Error(`${what} has no YAML header`);
  let end = -1;
  for (let i = 1; i < lines.length; i++) {
    if (strip(lines[i]) === '---') { end = i; break; }
  }
  if (end < 0) throw new Error(`${what} has an unterminated YAML header`);
  let done = false;
  for (let i = 1; i < end; i++) {
    if (lines[i].startsWith(key + ':')) {
      const comment = splitValueComment(lines[i].slice(key.length + 1))[1];
      lines[i] = rstrip(`${key}: ${formatValue(value)}${comment}`);
      done = true;
      break;
    }
  }
  if (!done) lines.splice(end, 0, rstrip(`${key}: ${formatValue(value)}`));
  return lines.join('\n') + '\n';
}
