/* Inventory/*.csv: an index of every note, generated from the note headers. Open it in Excel.
   The notes are the record; these four files can always be rebuilt from them. */

import { sortedById } from './vault.js';
import { dirname } from './text.js';
import { writeTextIfChanged } from '../store/base.js';

export const INDEX_COLUMNS = {
  experiments: ['experiment_id', 'title', 'researcher', 'project', 'experiment_type', 'protocols',
    'samples', 'notebook_reference', 'date_started', 'date_completed', 'status', 'tags', 'folder'],
  samples: ['sample_id', 'sample_type', 'title', 'source', 'storage_location', 'date_created', 'status', 'used_in_experiments'],
  protocols: ['protocol_id', 'title', 'version', 'status', 'used_in_experiments'],
  projects: ['project_id', 'title', 'lead', 'status', 'date_started', 'experiments'],
};

const join = (items) => items.join(';');

export function buildIndex(vault) {
  const exps = sortedById(vault.notes.experiment);
  const usedBy = new Map();
  for (const e of exps) {
    for (const key of ['protocols', 'samples', 'project']) {
      for (const ref of e.getList(key)) {
        if (!usedBy.has(ref)) usedBy.set(ref, []);
        usedBy.get(ref).push(e.id);
      }
    }
  }
  const used = (id) => join(usedBy.get(id) || []);
  return {
    experiments: exps.map((e) => ({
      experiment_id: e.id, title: e.get('title'), researcher: e.get('researcher'),
      project: join(e.getList('project')), experiment_type: join(e.getList('experiment_type')),
      protocols: join(e.getList('protocols')), samples: join(e.getList('samples')),
      notebook_reference: e.get('notebook_reference'), date_started: e.get('date_started'),
      date_completed: e.get('date_completed'), status: e.get('status'), tags: join(e.getList('tags')),
      folder: e.folder || dirname(e.path),
    })),
    samples: sortedById(vault.notes.sample).map((s) => ({
      sample_id: s.id, sample_type: s.get('sample_type'), title: s.get('title'), source: s.get('source'),
      storage_location: s.get('storage_location'), date_created: s.get('date_created'), status: s.get('status'),
      used_in_experiments: used(s.id),
    })),
    protocols: sortedById(vault.notes.protocol).map((p) => ({
      protocol_id: p.id, title: p.get('title'), version: p.get('version'), status: p.get('status'),
      used_in_experiments: used(p.id),
    })),
    projects: sortedById(vault.notes.project).map((p) => ({
      project_id: p.id, title: p.get('title'), lead: p.get('lead'), status: p.get('status'),
      date_started: p.get('date_started'), experiments: used(p.id),
    })),
  };
}

/** One CSV field, quoted only when it has to be (the csv module's QUOTE_MINIMAL). */
const csvField = (v) => (/[",\r\n]/.test(v) ? '"' + v.replaceAll('"', '""') + '"' : v);

export function toCsv(columns, rows) {
  return [columns, ...rows.map((r) => columns.map((c) => r[c] ?? ''))].map((r) => r.map(csvField).join(',') + '\n').join('');
}

/** Rewrite Inventory/*.csv. A file is written only when its content changed.
    -> [{ path, rows, written }] */
export async function writeIndex(store, vault) {
  await store.mkdir('Inventory');
  const rows = buildIndex(vault);
  const out = [];
  for (const [name, columns] of Object.entries(INDEX_COLUMNS)) {
    const path = `Inventory/${name}.csv`;
    const written = await writeTextIfChanged(store, path, toCsv(columns, rows[name]));
    out.push({ path, rows: rows[name].length, written });
  }
  return out;
}

export function formatIndexResult(result) {
  return result.map((r) => `${r.written ? 'Wrote' : 'Up to date'} ${r.path} (${r.rows} row${r.rows !== 1 ? 's' : ''})\n`).join('');
}
