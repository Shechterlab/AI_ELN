/* Creating records. This is the only way an experiment, sample, protocol, or project comes into
   existence, so IDs, folder names, and headers are always right. */

import {
  ElnError, SUBFOLDERS, VAULT_DIRS, RE_INITIALS, RE_EXP_FOLDER, RE_PROTOCOL_NAME, RE_PROJECT_ID,
  SAMPLE_LETTERS, SAMPLE_TYPES, NAMED_SUBFOLDERS,
} from './schema.js';
import { parseFrontMatter, parseHeaderLines, formatValue, csvItems } from './frontmatter.js';
import { renderTemplate } from './templates.js';
import { slugify, nextNumber, fileNameFor } from './names.js';
import { loadVault } from './vault.js';
import { writeIndex } from './inventory.js';
import { isoDate, pyRepr, strip, rstrip, stem, validDate, utf8, oneLine, stripBom, splitlines, decodeText } from './text.js';
import { writeText, writeTextIfChanged, readText, exists, isFile, isDir } from '../store/base.js';

export const SUBFOLDER_READMES = {
  '1-notes': 'Your experiment note `{ID}.md` lives here, next to the protocol snapshot(s) `{ID}_P_...md`\n'
    + 'the tool copied in. Extra notes are welcome; name them `{ID}_something.md`.\n',
  '2-data_raw': 'Instrument output goes here **with its original filename**. Never edit, rename, or\n'
    + 'reorganize anything in this folder. If the data is too large to live here, leave it on\n'
    + 'institutional storage and put that location in `raw_data_path` in the note.\n',
  '3-code': 'Analysis scripts and notebooks, named `{ID}_what-it-does.R` / `.py` / `.ipynb`.\n',
  '4-data_processed': 'Anything derived from the raw data by a script or by hand (quantification tables,\n'
    + 'cropped images, normalized values), named `{ID}_what-it-is.csv` and the like.\n',
  '5-figures': 'Exported panels. The results summary you show in lab meeting is\n'
    + '`{ID}_R_what-it-shows_YYYYMMDD.png` (the `R` is what makes it findable in one search).\n',
};

/** A mistyped path, or a drive or synced folder that is not there, must not quietly start a second notebook. */
export async function requireFolder(store) {
  if (!(await isDir(store, ''))) {
    throw new ElnError(`there is no folder at ${store.label || 'that path'}. Check the path: is the drive or the synced folder available?`, 'no_folder');
  }
}

export async function ensureVaultDirs(store) {
  await requireFolder(store);
  for (const d of VAULT_DIRS) await store.mkdir(d);
}

const WINDOWS_RESERVED = new Set(['con', 'prn', 'aux', 'nul', ...[1, 2, 3, 4, 5, 6, 7, 8, 9].flatMap((i) => [`com${i}`, `lpt${i}`])]);
export const MAX_NAME = 80;

/** Refuse a protocol or project name that cannot live on every computer the folder syncs to. */
async function checkNewName(store, folder, name, what) {
  if (name.length > MAX_NAME) throw new ElnError(`${what} is too long: ${MAX_NAME} characters at most`, 'bad_name');
  if (WINDOWS_RESERVED.has(name.toLowerCase())) throw new ElnError(`${name} cannot be a file name on Windows; choose another ${what}`, 'bad_name');
  for (const f of (await store.list(folder)) || []) {
    const existing = f.name.endsWith('.md') ? f.name.slice(0, -3) : null;
    if (existing !== null && existing.toLowerCase() === name.toLowerCase() && existing !== name) {
      throw new ElnError(`${existing} already exists. Names that differ only in capital letters are the same file `
        + 'on Windows and macOS; use the existing one or choose another name', 'exists');
    }
  }
}

function checkInitials(initials) {
  if (!RE_INITIALS.test(initials || '')) throw new ElnError(`initials must be 2-4 letters, e.g. JSR (got ${pyRepr(initials || '')})`, 'bad_initials');
}

async function headerId(store, path, key) {
  const v = parseFrontMatter(await readText(store, path)).fields[key];
  return typeof v === 'string' ? v : null;
}

/* ---- People/{INITIALS}.yaml: who the initials are, and the last serial numbers they used ---- */

const PERSON_HEAD = '# One file per person: who these initials are, and the last serial numbers used.\n'
  + '# The notebook tools update it when a record is created. A number recorded here is not\n'
  + '# given out again, even if the folder it belonged to is deleted. You may add lines of\n'
  + '# your own (orcid, email, role); they are kept.\n';
const PERSON_KEYS = ['initials', 'name', 'last_experiment', ...Object.keys(SAMPLE_LETTERS).map((l) => `last_sample_${l}`)];
export const personPath = (initials) => `People/${initials}.yaml`;

export async function readPerson(store, initials) {
  try {
    if (!(await isFile(store, personPath(initials)))) return {};
    return { ...parseHeaderLines(splitlines(stripBom(decodeText(await store.readBytes(personPath(initials)), true)))).fields };
  } catch (e) {
    return {};
  }
}

async function lastSerial(store, initials, key) {
  const value = (await readPerson(store, initials))[key];
  return typeof value === 'string' && /^[0-9]+$/.test(value) ? parseInt(value, 10) : 0;
}

/** Write the serial just used into the person's file. Returns a warning when the file says these
    initials belong to someone with a different name. */
export async function recordSerial(store, initials, key, number, rawName = '') {
  const person = await readPerson(store, initials);
  let warning = null;
  const known = typeof person.name === 'string' ? person.name : '';
  const name = strip(oneLine(rawName));
  if (name && name !== initials && known && known !== initials && known.toLowerCase() !== name.toLowerCase()) {
    warning = `the initials ${initials} belong to ${known} (People/${initials}.yaml), and this record was made as ${name}. `
      + 'If you are two people, one of you needs different initials';
  }
  person.initials = initials;
  person.name = known && known !== initials ? known : (name || known || initials);
  person[key] = String(Math.max(number, await lastSerial(store, initials, key)));
  const keys = [...PERSON_KEYS.filter((k) => k in person), ...Object.keys(person).filter((k) => !PERSON_KEYS.includes(k))];
  const text = PERSON_HEAD + keys.map((k) => rstrip(`${k}: ${formatValue(person[k])}`) + '\n').join('');
  await writeTextIfChanged(store, personPath(initials), text);
  return warning;
}

export async function nextExperimentId(store, initials) {
  const seen = [];
  for (const folder of (await store.list('Experiments')) || []) {
    if (folder.kind !== 'dir') continue;
    const m = RE_EXP_FOLDER.exec(folder.name);
    if (m) seen.push(m[1]);
    for (const f of (await store.list(`Experiments/${folder.name}/1-notes`)) || []) {
      if (f.kind !== 'file' || !f.name.endsWith('.md')) continue;
      const id = await headerId(store, `Experiments/${folder.name}/1-notes/${f.name}`, 'experiment_id');
      if (id) seen.push(id);
    }
  }
  const number = Math.max(nextNumber(seen, initials), (await lastSerial(store, initials, 'last_experiment')) + 1);
  return `${initials}e${String(number).padStart(4, '0')}`;
}

export async function nextSampleId(store, initials, letter) {
  const seen = [];
  for (const f of (await store.list('Samples')) || []) {
    if (f.kind !== 'file' || !f.name.endsWith('.md')) continue;
    seen.push(stem(f.name));
    const id = await headerId(store, `Samples/${f.name}`, 'sample_id');
    if (id) seen.push(id);
  }
  const number = Math.max(nextNumber(seen, initials, letter), (await lastSerial(store, initials, `last_sample_${letter}`)) + 1);
  return `${initials}${letter}${String(number).padStart(4, '0')}`;
}

/** A one-paragraph README in each subfolder: says what goes there, and keeps the folder from being empty. */
export async function writeSubfolderReadmes(store, folder, expId) {
  for (const [sub, text] of Object.entries(SUBFOLDER_READMES)) {
    const p = `${folder}/${sub}/README.md`;
    if (!(await exists(store, p))) await writeText(store, p, `# ${sub}\n\n${text.replaceAll('{ID}', expId)}`);
  }
}

const reindex = async (store) => writeIndex(store, await loadVault(store));

/** -> { id, path, folder, extra: [paths], warnings: [text] } */
export async function createExperiment(store, {
  initials, researcher = '', title, project = '', exp_type = '', protocol = '', samples = '', related = '',
  notebook = '', tags = '', raw_data_path = '', today = isoDate(), index = true,
}) {
  const cleanTitle = strip(title || '');
  if (!cleanTitle) throw new ElnError('an experiment needs a title', 'no_title');
  checkInitials(initials);
  await requireFolder(store);
  for (const p of csvItems(project)) {
    if (!RE_PROJECT_ID.test(p)) {
      throw new ElnError(`project ID ${pyRepr(p)} is not valid: letters, digits, and hyphens only, starting with a letter, `
        + 'no spaces (e.g. PRMT5-ChromatinRelease)', 'bad_name');
    }
  }
  /* a protocol typed without its P_ prefix means the protocol of that name */
  const protocols = [];
  for (const x of csvItems(protocol)) {
    const bare = !x.startsWith('P_') && !(await exists(store, `Protocols/${x}.md`)) && await exists(store, `Protocols/P_${x}.md`);
    protocols.push(bare ? `P_${x}` : x);
  }
  const protocolList = protocols.join(', ');
  const expId = await nextExperimentId(store, initials);
  const slug = slugify(cleanTitle);
  const folderName = slug ? `${expId}_${slug}` : expId;
  const folder = `Experiments/${folderName}`;
  if (await exists(store, folder)) throw new ElnError(`${folder} already exists. Aborting.`, 'exists');
  await ensureVaultDirs(store);
  for (const sub of SUBFOLDERS) await store.mkdir(`${folder}/${sub}`);
  await writeSubfolderReadmes(store, folder, expId);

  /* A per-type template (templates/experiment.WesternBlot.md) may add prompts to the body;
     the header keys stay those of templates/experiment.md, which is what Check compares against. */
  const firstType = csvItems(exp_type)[0] || '';
  const notePath = `${folder}/1-notes/${expId}.md`;
  await writeText(store, notePath, await renderTemplate(store, 'experiment', {
    EXPERIMENT_ID: expId, TITLE: cleanTitle, RESEARCHER: researcher || initials, PROJECT: project || '',
    DATE: today, EXPERIMENT_TYPE: exp_type || '', PROTOCOL: protocolList, SAMPLES: samples || '',
    NOTEBOOK_REF: notebook || '', RAW_DATA_PATH: raw_data_path || `Experiments/${folderName}/2-data_raw`,
    RELATED: related || '', TAGS: tags || '',
  }, firstType));
  const result = { id: expId, path: notePath, folder, extra: [], warnings: [] };
  const sameInitials = await recordSerial(store, initials, 'last_experiment', parseInt(expId.slice(-4), 10), researcher || '');
  if (sameInitials) result.warnings.push(sameInitials);
  for (const p of csvItems(project)) {
    if (!(await exists(store, `Projects/${p}.md`))) result.warnings.push(`project ${p} has no page in Projects/ yet (create it with New project)`);
  }
  for (const s of csvItems(samples)) {
    if (!(await exists(store, `Samples/${s}.md`))) result.warnings.push(`sample ${s} is not in Samples/ (check the ID, or create it with New sample)`);
  }

  for (const pid of protocols) {
    const src = `Protocols/${pid}.md`;
    const name = pid.startsWith('P_') ? pid.slice(2) : pid;
    if (!(await isFile(store, src))) {
      result.warnings.push(`${pid} not found in Protocols/, no snapshot copied (create it with New protocol, name ${name})`);
      continue;
    }
    const bytes = await store.readBytes(src);
    const v = parseFrontMatter(await readText(store, src)).fields.version;
    const version = (typeof v === 'string' && v ? v : today).replaceAll('-', '');
    const dst = `${folder}/1-notes/${expId}_P_${name}_${version}.md`;
    await store.writeBytes(dst, bytes);
    result.extra.push(dst);
  }
  if (index) await reindex(store);
  return result;
}

export async function createSample(store, { initials, sample_type, title, source = '', storage = '', tags = '', today = isoDate(), index = true }) {
  checkInitials(initials);
  let stype = strip(sample_type || '').toLowerCase();
  let letter;
  if (stype in SAMPLE_LETTERS) [letter, stype] = [stype, SAMPLE_LETTERS[stype]];
  else if (stype in SAMPLE_TYPES) letter = SAMPLE_TYPES[stype];
  else {
    throw new ElnError(`type must be one of ${Object.keys(SAMPLE_TYPES).join(', ')} (or a letter ${Object.keys(SAMPLE_LETTERS).join(', ')})`, 'bad_type');
  }
  if (!strip(title || '')) throw new ElnError('a sample needs a title', 'no_title');
  const sampleId = await nextSampleId(store, initials, letter);
  const path = `Samples/${sampleId}.md`;
  await ensureVaultDirs(store);
  await writeText(store, path, await renderTemplate(store, 'sample', {
    SAMPLE_ID: sampleId, SAMPLE_TYPE: stype, TITLE: strip(title), DATE: today,
    SOURCE: source || '', STORAGE: storage || '', TAGS: tags || '',
  }));
  await recordSerial(store, initials, `last_sample_${letter}`, parseInt(sampleId.slice(-4), 10));
  if (index) await reindex(store);
  return { id: sampleId, path, extra: [], warnings: [] };
}

export async function createProtocol(store, { name, title = '', tags = '', today = isoDate(), index = true }) {
  let short = strip(name || '');
  if (short.startsWith('P_')) short = short.slice(2);
  if (!RE_PROTOCOL_NAME.test(short)) {
    throw new ElnError('a protocol name is letters, digits, and hyphens, e.g. WesternBlot or Cellular-Fractionation', 'bad_name');
  }
  const pid = `P_${short}`;
  await checkNewName(store, 'Protocols', pid, 'protocol name');
  const path = `Protocols/${pid}.md`;
  if (await exists(store, path)) throw new ElnError(`${path} already exists. Edit it in place and bump its version instead.`, 'exists');
  const fullTitle = strip(title || '') || short.replace(/(?<=[a-z])(?=[A-Z])/g, ' ').replaceAll('-', ' ');
  await ensureVaultDirs(store);
  await writeText(store, path, await renderTemplate(store, 'protocol', { NAME: short, TITLE: fullTitle, DATE: today, TAGS: tags || '' }));
  if (index) await reindex(store);
  return { id: pid, path, extra: [], warnings: [] };
}

export async function createProject(store, { project_id, title = '', lead = '', tags = '', today = isoDate(), index = true }) {
  const pid = strip(project_id || '');
  if (!RE_PROJECT_ID.test(pid)) {
    throw new ElnError('a project ID starts with a letter and contains only letters, digits, and hyphens', 'bad_name');
  }
  await checkNewName(store, 'Projects', pid, 'project ID');
  const path = `Projects/${pid}.md`;
  if (await exists(store, path)) throw new ElnError(`${path} already exists.`, 'exists');
  await ensureVaultDirs(store);
  await writeText(store, path, await renderTemplate(store, 'project', {
    PROJECT_ID: pid, TITLE: strip(title || '') || pid, LEAD: lead || '', DATE: today, TAGS: tags || '',
  }));
  if (index) await reindex(store);
  return { id: pid, path, extra: [], warnings: [] };
}

/** Put a file into an experiment's subfolder under the right name. Never overwrites.
    In 2-data_raw the original name is kept; everywhere else the name starts with the experiment ID.
    -> { path, name } */
export async function addFile(store, vault, {
  id, subfolder, original_name, bytes, description = '', result = false, date = '',
}) {
  const note = vault.get(id);
  if (!note || note.kind !== 'experiment' || !note.folder) throw new ElnError(`no experiment ${id}`, 'not_found');
  if (!SUBFOLDERS.includes(subfolder)) throw new ElnError(`subfolder must be one of ${SUBFOLDERS.join(', ')}`, 'bad_subfolder');
  /* the name as the computer had it: no folders, no control characters, no trailing dots or spaces */
  const original = String(original_name || '').split(/[\\/]/).pop().replace(/[\x00-\x1f\x7f\u2028\u2029]/g, '').replace(/[ .]+$/, '');
  if (!original || original.startsWith('.')) throw new ElnError('the file needs a name', 'bad_name');
  if (date && !validDate(date)) throw new ElnError(`date must be YYYY-MM-DD (got ${pyRepr(date)})`, 'bad_date');
  const raw = !NAMED_SUBFOLDERS.includes(subfolder);
  const name = raw ? original : fileNameFor(id, { originalName: original, description, result, date });
  if (/[\\/:*?"<>|\x00-\x1f]/.test(name) && !raw) throw new ElnError(`"${name}" is not a usable file name`, 'bad_name');
  if (name.includes('/') || name.includes('\\') || name === '..' || name === '.') throw new ElnError(`"${name}" is not a usable file name`, 'bad_name');
  if (utf8(name).length > 200) throw new ElnError('the file name is too long: shorten the description (200 characters at most)', 'bad_name');
  const dir = `${note.folder}/${subfolder}`;
  if (!(await isDir(store, dir))) await store.mkdir(dir);
  const path = `${dir}/${name}`;
  if (await exists(store, path)) {
    throw new ElnError(`${path} already exists. Nothing was overwritten. `
      + (raw ? 'Raw files keep their own names: rename the file on your computer and add it again.' : 'Choose another description.'), 'exists');
  }
  await store.writeBytes(path, bytes);
  return { path, name };
}
