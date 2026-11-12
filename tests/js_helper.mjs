/* Used by tests/test_js_parity.py: run one library function on JSON read from stdin, print JSON.
     node tests/js_helper.mjs NAME < cases.json        cases.json is a list of argument lists */
import { mdToHtml } from '../docs/app/lib/markdown.js';
import { parseFrontMatter, formatValue, quoteIfNeeded, setHeaderField, csvItems } from '../docs/app/lib/frontmatter.js';
import { slugify, fileNameFor, nextNumber, cleanInitials, experimentId, folderName } from '../docs/app/lib/names.js';
import { renderTemplateText } from '../docs/app/lib/templates.js';
import { sections, sectionIsEmpty } from '../docs/app/lib/vault.js';
import { Sha256 } from '../docs/app/lib/sha256.js';
import { crc32 } from '../docs/app/lib/zip.js';
import { pyRepr, splitlines, normpath, toBase64, fromBase64, validDate, daysBefore } from '../docs/app/lib/text.js';
import { toCsv } from '../docs/app/lib/inventory.js';
import { SUBFOLDERS } from '../docs/app/lib/schema.js';

const bytes = (hex) => Uint8Array.from(hex.match(/../g) || [], (h) => parseInt(h, 16));
const FUNCTIONS = {
  mdToHtml: (text, imgBase = '', linkIds = true) => mdToHtml(text, { imgBase, linkIds, imgSrc: (rel) => '/file?p=' + rel }),
  parseFrontMatter: (text) => { const r = parseFrontMatter(text); return { fields: { ...r.fields }, body: r.body, problems: r.problems }; },
  formatValue, quoteIfNeeded, csvItems, slugify, fileNameFor, cleanInitials, experimentId, folderName,
  nextNumber, pyRepr, splitlines, normpath, validDate, daysBefore, toCsv,
  setHeaderField: (text, key, value) => setHeaderField(text, key, value),
  renderTemplateText: (text, values) => renderTemplateText(text, values),
  sections: (body) => [...sections(body)],
  sectionIsEmpty,
  sha256: (hex, chunk) => { const b = bytes(hex); const h = new Sha256(); for (let i = 0; i < b.length; i += chunk) h.update(b.subarray(i, i + chunk)); return h.hex(); },
  crc32: (hex) => crc32(bytes(hex)),
  base64: (hex) => { const b = bytes(hex); const s = toBase64(b); return [s, [...fromBase64(s)].map((x) => x.toString(16).padStart(2, '0')).join('')]; },
  subfolders: () => SUBFOLDERS,
};

process.stdin.setEncoding('utf8');
let input = '';
for await (const chunk of process.stdin) input += chunk;
const fn = FUNCTIONS[process.argv[2]];
if (!fn) throw new Error(`no helper named ${process.argv[2]}`);
process.stdout.write(JSON.stringify(JSON.parse(input).map((args) => fn(...args))));
