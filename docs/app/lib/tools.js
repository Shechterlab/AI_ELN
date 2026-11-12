/* The tool registry: everything the notebook can do, as named operations with JSON in and JSON out.

   The page calls these. The MCP server (mcp/server.mjs) lists and calls these. A function-calling
   model can be handed these (see openAiTools). A new integration is an adapter over this list;
   the operations themselves live in the other lib/ files and do not change.

     callTool(ctx, name, args) -> result object      ctx = { store, person: { initials, researcher }, today }

   Each tool has a JSON Schema for its arguments, so any client can validate or describe it. */

import { ElnError, KINDS, ID_FIELD, SUBFOLDERS, STATUS, SAMPLE_TYPES, MEETING_TAG } from './schema.js';
import { parseFrontMatter, setHeaderField, csvItems } from './frontmatter.js';
import { loadVault, ciIn, sortedById } from './vault.js';
import { validateVault, formatIssues, countIssues } from './validate.js';
import { writeIndex, formatIndexResult } from './inventory.js';
import { createExperiment, createSample, createProtocol, createProject, addFile } from './create.js';
import { findNotes, buildReport, buildExport, selectForExport, exportScope } from './query.js';
import { completeExperiment, verifyExperiments, formatVerify, renderSnapshot } from './closeout.js';
import { buildEln } from './elnfile.js';
import { CONVENTIONS_SUMMARY } from './conventions.js';
import { cleanInitials } from './names.js';
import { isoDate, splitlines, strip, normpath, decodeText, fromBase64, toBase64, utf8, cmp } from './text.js';
import { writeText } from '../store/base.js';

const str = (description, extra = {}) => ({ type: 'string', description, ...extra });
const bool = (description) => ({ type: 'boolean', description });
const list = (description) => ({ type: 'array', items: { type: 'string' }, description });
const obj = (properties, required = []) => ({ type: 'object', properties, required, additionalProperties: false });

function person(ctx, args) {
  const initials = cleanInitials(args.initials || (ctx.person && ctx.person.initials) || '');
  if (!initials) throw new ElnError('initials are needed (2 to 4 letters, e.g. JSR): set them in Settings or pass "initials"', 'no_initials');
  return { initials, researcher: args.researcher || (ctx.person && ctx.person.researcher) || initials };
}

function insidePath(path) {
  const p = normpath(String(path || '').replaceAll('\\', '/'));
  if (p === '.' || p.startsWith('..') || p.startsWith('/') || /^[A-Za-z]:/.test(p)) throw new ElnError(`path must be inside the notebook folder: ${path}`, 'bad_path');
  return p;
}

function noteOrThrow(vault, id, kind = '') {
  const note = vault.get(id);
  if (note === null || (kind && note.kind !== kind)) throw new ElnError(`no ${kind || 'note'} ${id}`, 'not_found');
  return note;
}

const brief = (n) => ({
  id: n.id, kind: n.kind, title: n.get('title'), status: n.get('status'), path: n.path,
  ...(n.kind === 'experiment' ? {
    researcher: n.get('researcher'), project: n.getList('project'), date_started: n.get('date_started'),
    date_completed: n.get('date_completed'), tags: n.getList('tags'), folder: n.folder,
  } : {}),
  ...(n.kind === 'sample' ? { sample_type: n.get('sample_type'), storage_location: n.get('storage_location') } : {}),
  ...(n.kind === 'protocol' ? { version: n.get('version') } : {}),
  ...(n.kind === 'project' ? { lead: n.get('lead') } : {}),
});

/** The files of an experiment, by subfolder (READMEs and hidden files left out). */
export async function experimentFiles(store, note) {
  const out = {};
  for (const sub of SUBFOLDERS) {
    const entries = (await store.list(`${note.folder}/${sub}`)) || [];
    out[sub] = entries.filter((e) => e.kind === 'file' && !e.name.startsWith('.') && e.name.toLowerCase() !== 'readme.md')
      .map((e) => e.name).sort(cmp);
  }
  return out;
}

/** Save the whole text of a note after checking the header still parses and the ID did not change. */
export async function saveNoteText(store, vault, id, input) {
  const note = noteOrThrow(vault, id);
  const text = String(input).replace(/\r\n?/g, '\n');
  const { fields, problems } = parseFrontMatter(text);
  if (problems.length) throw new ElnError('Header problem: ' + problems.join('; '), 'bad_header');
  if (fields[ID_FIELD[note.kind]] !== id) throw new ElnError(`The header's ${ID_FIELD[note.kind]} must stay ${id}.`, 'id_changed');
  await writeText(store, note.path, text.endsWith('\n') ? text : text + '\n');
  await writeIndex(store, await loadVault(store));
  return note.path;
}

/** Replace or extend the text under one '## ' heading. Returns the new note text. */
export function writeSection(text, section, content, mode = 'replace') {
  const lines = splitlines(text);
  const start = lines.findIndex((l) => l.startsWith('## ') && strip(l.slice(3)) === section);
  if (start < 0) throw new ElnError(`the note has no '## ${section}' section`, 'no_section');
  let end = lines.findIndex((l, i) => i > start && l.startsWith('## '));
  if (end < 0) end = lines.length;
  const fresh = splitlines(strip(String(content)));
  let middle;
  if (mode === 'append') {
    const kept = lines.slice(start + 1, end);
    while (kept.length && !strip(kept[kept.length - 1])) kept.pop();
    middle = [...kept, '', ...fresh, ''];
    if (!strip(kept.join(''))) middle = ['', ...fresh, ''];
  } else middle = ['', ...fresh, ''];
  return [...lines.slice(0, start + 1), ...middle, ...lines.slice(end)].join('\n').replace(/\n+$/, '') + '\n';
}

const CREATE_COMMON = {
  initials: str('Initials of the researcher (2 to 4 letters). Defaults to the configured person.'),
  researcher: str('Full name of the researcher. Defaults to the configured person.'),
};

export const TOOLS = [
  {
    name: 'get_conventions',
    title: 'Conventions',
    description: 'The notebook\'s layout, ID patterns, file-name grammar, and the rules an AI assistant follows. Read this first.',
    readOnly: true,
    inputSchema: obj({}),
    handler: async () => ({ text: CONVENTIONS_SUMMARY }),
  },
  {
    name: 'notebook_overview',
    title: 'Overview',
    description: 'Counts of experiments, samples, protocols, and projects; the project and protocol IDs; experiments flagged for lab meeting.',
    readOnly: true,
    inputSchema: obj({}),
    handler: async (ctx) => {
      const v = await loadVault(ctx.store);
      const exps = sortedById(v.notes.experiment);
      const byStatus = {};
      for (const e of exps) byStatus[e.get('status') || '(none)'] = (byStatus[e.get('status') || '(none)'] || 0) + 1;
      return {
        folder: ctx.store.label || '',
        person: ctx.person || null,
        counts: Object.fromEntries(KINDS.map((k) => [k + 's', v.notes[k].filter((n) => n.id).length])),
        experiments_by_status: byStatus,
        projects: sortedById(v.notes.project).map((n) => ({ id: n.id, title: n.get('title'), status: n.get('status') })),
        protocols: sortedById(v.notes.protocol).map((n) => ({ id: n.id, title: n.get('title'), version: n.get('version') })),
        researchers: [...new Set(exps.map((e) => e.get('researcher')).filter(Boolean))].sort(cmp),
        flagged_for_meeting: exps.filter((e) => ciIn(MEETING_TAG, e.getList('tags'))).map((e) => e.id),
      };
    },
  },
  {
    name: 'find_notes',
    title: 'Find notes',
    description: 'List notes of one kind that match every filter given. Matching ignores case. Returns IDs, titles, status, and paths; use read_note for the content.',
    readOnly: true,
    inputSchema: obj({
      kind: str('Which records to search.', { enum: KINDS, default: 'experiment' }),
      project: str('Project ID the experiment belongs to.'),
      status: str('Status, e.g. active, complete, paused, abandoned.'),
      researcher: str('Part of the researcher\'s (or project lead\'s) name.'),
      tag: str('A tag, e.g. meeting.'),
      sample: str('A sample ID the experiment used.'),
      protocol: str('A protocol ID the experiment followed.'),
      exp_type: str('An experiment type, e.g. WesternBlot.'),
      text: str('Words to look for in the title or body.'),
    }),
    handler: async (ctx, a) => {
      const v = await loadVault(ctx.store);
      const hits = findNotes(v, a.kind || 'experiment', a);
      return { count: hits.length, notes: hits.map(brief) };
    },
  },
  {
    name: 'read_note',
    title: 'Read a note',
    description: 'One note by ID: its header fields, its full Markdown text, and for an experiment the files in each subfolder.',
    readOnly: true,
    inputSchema: obj({ id: str('The ID, e.g. JSRe0002, JSRp0001, P_WesternBlot, or a project ID.') }, ['id']),
    handler: async (ctx, a) => {
      const v = await loadVault(ctx.store);
      const n = noteOrThrow(v, a.id);
      const out = { id: n.id, kind: n.kind, path: n.path, folder: n.folder, fields: { ...n.fields }, text: n.text };
      if (n.kind === 'experiment' && n.folder) out.files = await experimentFiles(ctx.store, n);
      else out.used_in = findNotes(v, 'experiment', { [n.kind]: n.id }).map((e) => e.id);
      return out;
    },
  },
  {
    name: 'read_file',
    title: 'Read a file',
    description: 'The text of a file inside the notebook folder (a CSV in 4-data_processed, a script, a protocol copy). Text files up to 400 kB.',
    readOnly: true,
    inputSchema: obj({ path: str('Path relative to the notebook folder, e.g. Experiments/JSRe0002_title/4-data_processed/JSRe0002_quant.csv') }, ['path']),
    handler: async (ctx, a) => {
      const path = insidePath(a.path);
      const s = await ctx.store.stat(path);
      if (!s || s.kind !== 'file') throw new ElnError(`no file at ${path}`, 'not_found');
      if (s.size > 400000) throw new ElnError(`${path} is ${s.size} bytes; too large to return as text`, 'too_large');
      try {
        return { path, bytes: s.size, text: decodeText(await ctx.store.readBytes(path), true) };
      } catch (e) {
        throw new ElnError(`${path} is not a text file`, 'not_text');
      }
    },
  },
  {
    name: 'create_experiment',
    title: 'New experiment',
    description: 'Create an experiment: assigns the next ID for the researcher, makes the folder with its five subfolders and the note, copies each named protocol next to the note, and updates the index. Only the title is required.',
    inputSchema: obj({
      title: str('What the experiment is, in a phrase. Becomes the folder name.'),
      project: str('Project ID(s), comma-separated.'),
      exp_type: str('Experiment type(s), comma-separated, e.g. WesternBlot, Fractionation.'),
      protocol: str('Protocol ID(s), comma-separated, e.g. P_WesternBlot.'),
      samples: str('Sample ID(s), comma-separated.'),
      related: str('Related experiment ID(s), comma-separated.'),
      notebook: str('Paper notebook page, e.g. NB02-153.'),
      tags: str('Tags, comma-separated. "meeting" flags it for the next lab meeting.'),
      raw_data_path: str('Where the raw data is, if not in 2-data_raw.'),
      ...CREATE_COMMON,
    }, ['title']),
    handler: async (ctx, a) => createExperiment(ctx.store, { ...a, ...person(ctx, a), today: ctx.today || isoDate() }),
  },
  {
    name: 'create_sample',
    title: 'New sample',
    description: 'Create a sample record (plasmid, oligo, antibody, cell-line, mouse-line, peptide, protein-prep, slide, gel) with the next ID for the researcher.',
    inputSchema: obj({
      sample_type: str('The kind of sample.', { enum: Object.keys(SAMPLE_TYPES) }),
      title: str('Name of the sample, e.g. pcDNA3-FLAG-SNRPB.'),
      source: str('Vendor and catalog number, the experiment that made it, or who gave it.'),
      storage: str('Where it is kept, e.g. Freezer B, box 3, A7.'),
      tags: str('Tags, comma-separated.'),
      ...CREATE_COMMON,
    }, ['sample_type', 'title']),
    handler: async (ctx, a) => createSample(ctx.store, { ...a, initials: person(ctx, a).initials, today: ctx.today || isoDate() }),
  },
  {
    name: 'create_protocol',
    title: 'New protocol',
    description: 'Create Protocols/P_{name}.md from the protocol template.',
    inputSchema: obj({
      name: str('Short name: letters, digits, hyphens, e.g. WesternBlot.'),
      title: str('Full title.'),
      tags: str('Tags, comma-separated.'),
    }, ['name']),
    handler: async (ctx, a) => createProtocol(ctx.store, { ...a, today: ctx.today || isoDate() }),
  },
  {
    name: 'create_project',
    title: 'New project',
    description: 'Create Projects/{project_id}.md from the project template.',
    inputSchema: obj({
      project_id: str('Short ID: starts with a letter; letters, digits, hyphens, e.g. PRMT5-ChromatinRelease.'),
      title: str('Full title.'),
      lead: str('Who leads it. Defaults to the configured person.'),
      tags: str('Tags, comma-separated.'),
    }, ['project_id']),
    handler: async (ctx, a) => createProject(ctx.store, {
      ...a, lead: a.lead || (ctx.person && ctx.person.researcher) || '', today: ctx.today || isoDate(),
    }),
  },
  {
    name: 'update_note',
    title: 'Save a note',
    description: 'Replace the whole text of a note. The header must still parse and the ID must not change. Prefer write_section or set_field for small changes.',
    inputSchema: obj({ id: str('The note\'s ID.'), text: str('The complete new file content, header included.') }, ['id', 'text']),
    handler: async (ctx, a) => ({ id: a.id, path: await saveNoteText(ctx.store, await loadVault(ctx.store), a.id, a.text) }),
  },
  {
    name: 'write_section',
    title: 'Write a section',
    description: 'Replace or append to the text under one "## " heading of a note (for example Results). Record only what the researcher provided or what the data files show.',
    inputSchema: obj({
      id: str('The note\'s ID.'),
      section: str('The heading without "## ", e.g. Results.'),
      text: str('Markdown to put under the heading.'),
      mode: str('replace the section, or append to it.', { enum: ['replace', 'append'], default: 'replace' }),
    }, ['id', 'section', 'text']),
    handler: async (ctx, a) => {
      const v = await loadVault(ctx.store);
      const n = noteOrThrow(v, a.id);
      return { id: a.id, section: a.section, path: await saveNoteText(ctx.store, v, a.id, writeSection(n.text, a.section, a.text, a.mode || 'replace')) };
    },
  },
  {
    name: 'set_field',
    title: 'Set a header field',
    description: 'Set one header field of a note, for example status, tags, notebook_reference, or storage_location. Other lines are untouched.',
    inputSchema: obj({
      id: str('The note\'s ID.'),
      field: str('Header key in snake_case.'),
      value: { description: 'The new value: text, or a list of texts for list fields such as tags.', anyOf: [{ type: 'string' }, { type: 'array', items: { type: 'string' } }] },
    }, ['id', 'field', 'value']),
    handler: async (ctx, a) => {
      const v = await loadVault(ctx.store);
      const n = noteOrThrow(v, a.id);
      if (!/^[a-z][a-z0-9_]*$/.test(a.field)) throw new ElnError('field must be snake_case', 'bad_field');
      if (a.field === ID_FIELD[n.kind] || a.field === 'type') throw new ElnError(`${a.field} cannot be changed`, 'bad_field');
      if (a.field === 'status' && !STATUS[n.kind].includes(a.value)) {
        throw new ElnError(`status must be one of ${STATUS[n.kind].join(' | ')}`, 'bad_status');
      }
      const wasList = Array.isArray(n.fields[a.field]);
      const value = wasList && !Array.isArray(a.value) ? csvItems(a.value) : a.value;
      return { id: a.id, field: a.field, path: await saveNoteText(ctx.store, v, a.id, setHeaderField(n.text, a.field, value, n.path)) };
    },
  },
  {
    name: 'add_file',
    title: 'Add a file',
    description: 'Put a file into an experiment subfolder under a conforming name ({ID}[_R]_{description}[_{date}].ext). In 2-data_raw the original name is kept. Never overwrites.',
    inputSchema: obj({
      id: str('Experiment ID.'),
      subfolder: str('Which subfolder.', { enum: SUBFOLDERS }),
      original_name: str('The file\'s current name, with its extension.'),
      text: str('The content, for a text file.'),
      base64: str('The content, base64-encoded, for any other file.'),
      description: str('A few words for the name; defaults to the original name.'),
      result: bool('True for the result figure or table (adds _R).'),
      date: str('YYYY-MM-DD to put in the name.'),
    }, ['id', 'subfolder', 'original_name']),
    handler: async (ctx, a) => {
      if ((a.text === undefined) === (a.base64 === undefined)) throw new ElnError('give the content as "text" or as "base64" (one of them)', 'bad_content');
      const bytes = a.text !== undefined ? utf8(a.text) : fromBase64(a.base64);
      return addFile(ctx.store, await loadVault(ctx.store), { ...a, bytes });
    },
  },
  {
    name: 'check_notebook',
    title: 'Check',
    description: 'Read every note and folder and list what does not follow the conventions: misnamed folders and files, missing fields, bad dates, IDs that point at nothing, sync-conflict copies. ERROR must be fixed; WARN is advice.',
    readOnly: true,
    inputSchema: obj({ strict: bool('Count warnings as failures.') }),
    handler: async (ctx, a) => {
      const v = await loadVault(ctx.store);
      const issues = await validateVault(ctx.store, v);
      const { text, ok } = formatIssues(v, issues, !!a.strict);
      return { ok, ...countIssues(v, issues), issues, text };
    },
  },
  {
    name: 'rebuild_index',
    title: 'Rebuild the index',
    description: 'Regenerate Inventory/*.csv from the note headers. Files are rewritten only when their content changed.',
    inputSchema: obj({}),
    handler: async (ctx) => {
      const files = await writeIndex(ctx.store, await loadVault(ctx.store));
      return { files, text: formatIndexResult(files) };
    },
  },
  {
    name: 'meeting_brief',
    title: 'Lab meeting brief',
    description: 'The lab-meeting brief as Markdown: experiments tagged "meeting" with their Objective, Results, Interpretation, and Decision; active experiments by project; recent completions.',
    inputSchema: obj({
      days: { type: 'integer', description: 'How far back "recently completed" goes. Default 30.', minimum: 1 },
      save: bool('Also save it as Inventory/meeting-brief_{YYYYMMDD}.md.'),
    }),
    handler: async (ctx, a) => {
      const today = ctx.today || isoDate();
      const markdown = buildReport(await loadVault(ctx.store), { days: a.days || 30, today });
      const out = { markdown };
      if (a.save) {
        out.path = `Inventory/meeting-brief_${today.replaceAll('-', '')}.md`;
        await writeText(ctx.store, out.path, markdown);
      }
      return out;
    },
  },
  {
    name: 'export_notes',
    title: 'Export',
    description: 'Bundle experiments and the notes they refer to. format "md" gives one Markdown document to paste into a chat. format "eln" writes a .eln archive (RO-Crate) that eLabFTW, RSpace, Kadi4Mat, PASTA, SampleDB, OpenSemanticLab, and SciLog import. Choose what to export with project, experiment_ids, status, or all.',
    inputSchema: obj({
      project: str('Export every experiment of this project.'),
      experiment_ids: list('Export these experiments.'),
      status: str('Export every experiment with this status, e.g. active.'),
      all: bool('Export every experiment.'),
      related: bool('Include the protocols, samples, and projects the experiments refer to. Default true.'),
      format: str('md or eln.', { enum: ['md', 'eln'], default: 'md' }),
      save: bool('Save into Inventory/ (always true for eln unless return_bytes is set).'),
      return_bytes: bool('For eln: return the archive as base64 instead of saving it.'),
    }),
    handler: async (ctx, a) => runExport(ctx, a),
  },
  {
    name: 'complete_experiment',
    title: 'Mark complete',
    description: 'Close out an experiment: checks Results and Interpretation are written, sets status and date_completed, writes a self-contained HTML snapshot and a sha256 manifest next to the note, and updates the index. Running it again refreshes the snapshot and manifest.',
    inputSchema: obj({
      id: str('Experiment ID.'),
      date: str('Completion date, YYYY-MM-DD. Default today.'),
      force: bool('Complete even if Results or Interpretation is empty.'),
    }, ['id']),
    handler: async (ctx, a) => completeExperiment(ctx.store, a.id, { when: a.date || '', force: !!a.force, today: ctx.today || isoDate() }),
  },
  {
    name: 'verify_files',
    title: 'Verify files',
    description: 'Compare an experiment folder with the manifest written at completion and list files that were modified, removed, or added. Without an ID, checks every completed experiment.',
    readOnly: true,
    inputSchema: obj({ id: str('Experiment ID. Leave out to check all.') }),
    handler: async (ctx, a) => {
      const r = await verifyExperiments(ctx.store, await loadVault(ctx.store), a.id || '');
      return { ok: r.drift === 0, ...r, text: formatVerify(r) };
    },
  },
  {
    name: 'render_snapshot',
    title: 'Save HTML snapshot',
    description: 'Write a self-contained HTML rendering of a note next to it (images embedded). Open it in a browser and print to PDF.',
    inputSchema: obj({ id: str('The note\'s ID.') }, ['id']),
    handler: async (ctx, a) => ({
      id: a.id, path: await renderSnapshot(ctx.store, await loadVault(ctx.store), a.id, { when: ctx.today || isoDate() }),
    }),
  },
];

async function runExport(ctx, a) {
  const today = ctx.today || isoDate();
  const v = await loadVault(ctx.store);
  const choice = { project: a.project || '', experiment_ids: a.experiment_ids || [], status: a.status || '', all: !!a.all };
  if (!(choice.project || choice.experiment_ids.length || choice.status || choice.all)) {
    throw new ElnError('choose what to export: project, experiment_ids, status, or all', 'no_scope');
  }
  const experiments = selectForExport(v, choice);
  if (!experiments.length) throw new ElnError('nothing matched', 'empty');
  const related = a.related !== false;
  const stem = `export_${exportScope(choice)}_${today.replaceAll('-', '')}`;
  const ids = experiments.map((e) => e.id);
  if ((a.format || 'md') === 'eln') {
    const { bytes, files } = await buildEln(ctx.store, v, experiments, { related, today, rootName: stem });
    if (a.return_bytes) return { experiments: ids, files, bytes, name: `${stem}.eln` };
    const path = `Inventory/${stem}.eln`;
    await ctx.store.writeBytes(path, bytes);
    return { experiments: ids, files, size: bytes.length, path };
  }
  const markdown = buildExport(v, experiments, { related, today });
  const out = { experiments: ids, characters: markdown.length, markdown };
  if (a.save) {
    out.path = `Inventory/${stem}.md`;
    await writeText(ctx.store, out.path, markdown);
  }
  return out;
}

const BY_NAME = new Map(TOOLS.map((t) => [t.name, t]));

function checkArgs(tool, args) {
  const schema = tool.inputSchema;
  for (const key of schema.required) {
    if (args[key] === undefined || args[key] === null || args[key] === '') throw new ElnError(`${tool.name}: "${key}" is required`, 'bad_arguments');
  }
  for (const [key, value] of Object.entries(args)) {
    const spec = schema.properties[key];
    if (!spec) throw new ElnError(`${tool.name}: unknown argument "${key}" (it takes: ${Object.keys(schema.properties).join(', ') || 'nothing'})`, 'bad_arguments');
    if (value === undefined || value === null) continue;
    const ok = !spec.type
      || (spec.type === 'string' && typeof value === 'string')
      || (spec.type === 'boolean' && typeof value === 'boolean')
      || (spec.type === 'integer' && Number.isInteger(value))
      || (spec.type === 'array' && Array.isArray(value) && value.every((x) => typeof x === 'string'));
    if (!ok) throw new ElnError(`${tool.name}: "${key}" must be ${spec.type === 'array' ? 'a list of strings' : 'a ' + spec.type}`, 'bad_arguments');
    if (spec.enum && !spec.enum.includes(value)) throw new ElnError(`${tool.name}: "${key}" must be one of ${spec.enum.join(', ')}`, 'bad_arguments');
  }
}

export const getTool = (name) => BY_NAME.get(name) || null;

/** Run one tool. Throws ElnError for anything the caller got wrong. */
export async function callTool(ctx, name, args = {}) {
  const tool = BY_NAME.get(name);
  if (!tool) throw new ElnError(`unknown tool: ${name}`, 'unknown_tool');
  const clean = Object.fromEntries(Object.entries(args || {}).filter(([, v]) => v !== undefined));
  checkArgs(tool, clean);
  return tool.handler(ctx, clean);
}

/** The list in the shape MCP's tools/list returns. */
export function mcpTools() {
  return TOOLS.map((t) => ({
    name: t.name, title: t.title, description: t.description, inputSchema: t.inputSchema,
    annotations: { readOnlyHint: !!t.readOnly, destructiveHint: false, openWorldHint: false },
  }));
}

/** The list as function-calling tool definitions.
    style 'responses': { type: 'function', name, description, parameters }
    style 'chat':      { type: 'function', function: { name, description, parameters } } */
export function openAiTools(style = 'responses') {
  return TOOLS.map((t) => {
    const fn = { name: t.name, description: t.description, parameters: t.inputSchema };
    return style === 'chat' ? { type: 'function', function: fn } : { type: 'function', ...fn };
  });
}

/** A result as JSON text, with byte arrays shown as base64. */
export function resultToJson(result, indent = 2) {
  return JSON.stringify(result, (k, v) => (v instanceof Uint8Array ? { base64: toBase64(v), bytes: v.length } : v), indent);
}
