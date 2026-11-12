/* Export as a folder of plain files: the chosen experiments and the records they refer to, copied in the
   notebook's own layout, with a README, one file holding every note, and an index. Same result as
   `eln.py export --format folder`. */

import { ElnError, SUBFOLDERS, VAULT_DIRS } from './schema.js';
import { loadVault } from './vault.js';
import { writeIndex } from './inventory.js';
import { folderFiles } from './closeout.js';
import { buildExport, exportReadme, relatedNotes } from './query.js';
import { isoDate } from './text.js';
import { writeText, copyFile, SubStore } from '../store/base.js';

/** -> { path, experiments: [ids], notes, files, bytes } */
export async function exportFolder(store, vault, experiments, { dest, related = true, raw = true, today = isoDate(), lab = null } = {}) {
  const there = await store.list(dest);
  if (there === null ? (await store.stat(dest)) !== null : there.length > 0) {
    throw new ElnError(`${dest} already exists. Delete it, or export to another place.`, 'exists');
  }
  const extras = related ? relatedNotes(vault, experiments) : [];
  const labName = (lab && lab.lab_name) || 'Lab';
  for (const d of VAULT_DIRS) await store.mkdir(`${dest}/${d}`);
  let files = 0;
  let bytes = 0;
  const copy = async (path) => {
    await copyFile(store, path, `${dest}/${path}`);
    files += 1;
    bytes += (await store.stat(path)).size;
  };
  for (const n of [...experiments, ...extras]) {
    if (n.kind !== 'experiment' || n.folder === null) {
      await copy(n.path);
      continue;
    }
    for (const sub of SUBFOLDERS) await store.mkdir(`${dest}/${n.folder}/${sub}`);
    for (const f of await folderFiles(store, n.folder)) {
      const rel = f.slice(n.folder.length + 1);
      if (!raw && rel.startsWith('2-data_raw/') && rel !== '2-data_raw/README.md') continue;
      await copy(f);
    }
  }
  await writeText(store, `${dest}/all-notes.md`, buildExport(vault, experiments, { related, today, labName }));
  await writeText(store, `${dest}/README.md`, exportReadme(experiments, extras, { raw, today, labName }));
  const sub = new SubStore(store, dest);
  await writeIndex(sub, await loadVault(sub));
  return { path: dest, experiments: experiments.map((e) => e.id), notes: experiments.length + extras.length, files, bytes };
}
