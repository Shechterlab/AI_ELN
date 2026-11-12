/* Note templates: the files in the notebook's templates/ folder, or the built-in copies when the
   folder has none. A template's header keys are the keys a note of that kind may have. */

import { TEMPLATES } from './builtin_templates.js';
import { ElnError } from './schema.js';
import { splitFrontMatter, parseFrontMatter, splitValueComment, formatValue, quoteIfNeeded, csvItems } from './frontmatter.js';
import { rstrip, strip, oneLine } from './text.js';
import { isFile, readText } from '../store/base.js';

const PLACEHOLDER = /\{\{([A-Z_]+)\}\}/;
const PLACEHOLDER_G = /\{\{([A-Z_]+)\}\}/g;
const fill = (s, values) => s.replace(PLACEHOLDER_G, (_, name) => (name in values ? values[name] : ''));

/** The text of templates/{name}.md from the notebook, else the built-in copy, else null. */
export async function templateText(store, name) {
  if (/^[A-Za-z0-9_.-]+$/.test(name)) {
    const path = `templates/${name}.md`;
    if (await isFile(store, path)) return readText(store, path);
  }
  return Object.prototype.hasOwnProperty.call(TEMPLATES, name) ? TEMPLATES[name] : null;
}

/** The header keys a note of this kind is allowed to have. */
export async function templateKeys(store, kind) {
  return Object.keys(parseFrontMatter(await templateText(store, kind)).fields);
}

export function renderHeaderLine(line, values) {
  const m = /^([a-z][a-z0-9_]*):(.*)$/.exec(line);
  if (!m) return line;
  const key = m[1];
  const [value, comment] = splitValueComment(m[2]);
  if (!PLACEHOLDER.test(value)) return line;
  const rendered = value.startsWith('[') && value.endsWith(']')
    ? formatValue(csvItems(fill(value.slice(1, -1), values)))
    : quoteIfNeeded(fill(value, values));
  let out = rstrip(`${key}: ${rendered}`);
  if (strip(comment)) out = rendered ? `${out}${comment}` : `${out} ${strip(comment)}`;
  return out;
}

/** Fill a template's {{PLACEHOLDERS}}. Header values are quoted when YAML needs it. */
export function renderTemplateText(text, input, what = 'template') {
  const { header, body, error } = splitFrontMatter(text);
  if (header === null) throw new ElnError(`${what} is broken: ${error}`);
  const values = Object.fromEntries(Object.entries(input).map(([k, v]) => [k, oneLine(v)]));
  return '---\n' + header.map((line) => renderHeaderLine(line, values)).join('\n') + '\n---\n'
    + fill(body, values).replace(/\n+$/, '') + '\n';
}

/** Render templates/{kind}.md, or templates/{kind}.{variant}.md when that exists. */
export async function renderTemplate(store, kind, values, variant = '') {
  let text = variant && /^[A-Za-z0-9_-]+$/.test(variant) ? await templateText(store, `${kind}.${variant}`) : null;
  let what = `templates/${kind}.${variant}.md`;
  if (text === null) {
    text = await templateText(store, kind);
    what = `templates/${kind}.md`;
  }
  return renderTemplateText(text, values, what);
}
