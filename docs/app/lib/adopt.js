/* Adopting an older folder: it becomes an experiment record, and the folder goes, exactly as it is, into
   the new experiment's 2-data_raw/. Nothing in it is renamed or changed. Same result as `eln.py adopt`. */

import { ElnError, KIND_DIR, RE_EXP_FOLDER } from './schema.js';
import { createExperiment } from './create.js';
import { completeExperiment } from './closeout.js';
import { guessFromFolderName } from './names.js';
import { loadVault, writeSection } from './vault.js';
import { writeIndex, toCsv } from './inventory.js';
import { basename, cmp, decodeText, isoDate, pyRepr, strip, thousands, validDate } from './text.js';
import { writeText, exists, isDir, copyFile, moveFile, removeDir, walkTree } from '../store/base.js';

export const ADOPTED_TAG = 'adopted';
const NOTEBOOK_TOP = new Set([...Object.values(KIND_DIR), 'Inventory', 'Exports', 'templates']);

/** Folders in the notebook folder that are not records: anything in Experiments/ without an ID in its name,
    and other folders at the top (not offered when the notebook folder is the tool's own repository).
    -> [{ path, title, date }] with the title and date read from the folder name */
export async function adoptableFolders(store) {
  const dirs = async (parent) => ((await store.list(parent)) || []).filter((e) => e.kind === 'dir' && !e.name.startsWith('.'))
    .map((e) => e.name).sort(cmp);
  const out = (await dirs('Experiments')).filter((name) => !RE_EXP_FOLDER.test(name)).map((name) => `Experiments/${name}`);
  if (!(await exists(store, 'scripts/eln.py'))) out.push(...(await dirs('')).filter((name) => !NOTEBOOK_TOP.has(name)));
  return out.map((path) => {
    const [title, date] = guessFromFolderName(basename(path));
    return { path, title, date };
  });
}

const utcStamp = (ms) => new Date(Math.floor(ms / 1000) * 1000).toISOString().slice(0, 19) + 'Z';

/** -> { id, path, folder, extra: [paths], warnings: [text] } */
export async function adoptFolder(store, {
  folder: source, initials, researcher = '', title = '', date = '', project = '', status = 'complete', copy = false,
  today = isoDate(), lab = null,
}) {
  if (!['complete', 'active'].includes(status)) throw new ElnError(`status must be complete or active (got ${pyRepr(status)})`, 'bad_status');
  if (date && !validDate(date)) throw new ElnError(`date must be YYYY-MM-DD (got ${pyRepr(date)})`, 'bad_date');
  if (!(await isDir(store, source))) throw new ElnError(`there is no folder at ${source}`, 'not_found');
  const parts = source.split('/');
  if (NOTEBOOK_TOP.has(parts[0]) && (parts[0] !== 'Experiments' || parts.length < 2)) {
    throw new ElnError(`${source} is part of the notebook, not an older folder`, 'bad_path');
  }
  if (parts[0] === 'Experiments' && RE_EXP_FOLDER.test(parts[1])) {
    throw new ElnError(`${source} is already in an experiment record (${parts[1]})`, 'bad_path');
  }
  if (!copy && typeof store.remove !== 'function' && typeof store.move !== 'function') {
    throw new ElnError('files cannot be moved here; adopt with copy instead', 'cannot_move');
  }
  const name = basename(source);
  const { dirs, files } = await walkTree(store, source);
  const found = [];
  for (const rel of files) {
    const s = await store.stat(`${source}/${rel}`);
    if (s) found.push({ rel, size: s.size, mtime: s.mtime });
  }
  if (!found.length) throw new ElnError(`${name} has no files in it; there is nothing to adopt`, 'empty');
  const [guessedTitle, nameDate] = guessFromFolderName(name);
  const times = found.map((f) => f.mtime);
  const oldest = isoDate(new Date(Math.min(...times)));
  const newest = isoDate(new Date(Math.max(...times)));
  const started = date || nameDate || oldest;
  const startedFrom = date ? 'the date given' : nameDate ? 'the date in the folder name' : 'the oldest file date';
  const finished = started > newest ? started : newest;

  const result = await createExperiment(store, {
    initials, researcher, title: strip(title || '') || guessedTitle || name, project, tags: ADOPTED_TAG, today: started, index: false,
  });
  const { id, folder } = result;
  const listing = `${folder}/1-notes/${id}_adopted-files.csv`;
  await writeText(store, listing, toCsv(['path', 'bytes', 'modified'],
    found.map((f) => ({ path: `2-data_raw/${name}/${f.rel}`, bytes: String(f.size), modified: utcStamp(f.mtime) }))));
  result.extra.push(listing);

  const dest = `${folder}/2-data_raw/${name}`;
  try {
    await store.mkdir(dest);
    for (const d of dirs) await store.mkdir(`${dest}/${d}`);
    for (const rel of files) await (copy ? copyFile : moveFile)(store, `${source}/${rel}`, `${dest}/${rel}`);
    if (!copy) {
      for (const d of [...dirs].reverse()) await removeDir(store, `${source}/${d}`);
      if (!(await removeDir(store, source)) && await exists(store, source)) {
        result.warnings.push(`the old folder ${source} could not be removed (something in it could not be moved, or this place does not allow it). Its files are in ${dest}; delete the old folder by hand`);
      }
    }
  } catch (e) {
    if (e instanceof ElnError) throw e;
    throw new ElnError(`${id} was created, but the files could not be ${copy ? 'copied' : 'moved'} (${e.message}). `
      + `Put what is left of ${source} into ${dest} by hand, or delete the folder of ${id} and try again.`, 'move_failed');
  }

  const shown = name.replaceAll('`', "'");
  const total = found.reduce((sum, f) => sum + f.size, 0);
  const said = `Adopted on ${today} from an older folder named \`${shown}\`. The folder was ${copy ? 'copied' : 'moved'}, `
    + `as it was, into \`2-data_raw/${shown}/\`: ${found.length} file${found.length !== 1 ? 's' : ''}, ${thousands(total)} bytes. `
    + `\`1-notes/${id}_adopted-files.csv\` lists each file with its size and the time it was last modified `
    + `before that.\n\n\`date_started\` is ${startedFrom}`
    + (status === 'complete' ? '; `date_completed` is the newest file date' : '')
    + '. Correct the header if a date or the title is wrong.';
  let text = writeSection(decodeText(await store.readBytes(result.path), true), 'Files', said, 'append');
  if (status === 'complete') {
    text = writeSection(text, 'Results', 'Not written. This record was made by adopting an older folder; see Files.');
    text = writeSection(text, 'Interpretation', 'Not written.');
  }
  await writeText(store, result.path, text);
  if (status === 'complete') {
    const done = await completeExperiment(store, id, { when: finished, today, lab });
    result.extra.push(done.snapshot, done.manifest);
    result.warnings.push(...done.warnings);
  } else await writeIndex(store, await loadVault(store));
  return result;
}
