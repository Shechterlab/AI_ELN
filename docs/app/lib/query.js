/* Finding notes, the lab-meeting brief, and the plain-text export for pasting into a chat. */

import { ElnError, MEETING_TAG, REF_FIELDS } from './schema.js';
import { sections, ciIn, sortedById } from './vault.js';
import { cmp, isoDate, daysBefore, validDate, strip, rstrip } from './text.js';

/** Notes of one kind that match every filter given. Matching ignores case. */
export function findNotes(vault, kind, { project, status, researcher, tag, sample, protocol, exp_type, text } = {}) {
  const out = [];
  for (const n of vault.notes[kind]) {
    if (!n.id) continue;
    if (project && !ciIn(project, n.getList('project'))) continue;
    if (status && n.get('status').toLowerCase() !== status.toLowerCase()) continue;
    if (researcher && !(n.get('researcher') + ' ' + n.get('lead')).toLowerCase().includes(researcher.toLowerCase())) continue;
    if (tag && !ciIn(tag, n.getList('tags'))) continue;
    if (sample && !ciIn(sample, n.getList('samples'))) continue;
    if (protocol && !ciIn(protocol, n.getList('protocols'))) continue;
    if (exp_type && !ciIn(exp_type, n.getList('experiment_type'))) continue;
    if (text && !(n.get('title') + '\n' + n.body).toLowerCase().includes(text.toLowerCase())) continue;
    out.push(n);
  }
  return out.sort((a, b) => cmp(a.id, b.id));
}

const clean = (text) => strip((text || '').replace(/<!--.*?-->/gs, '')) || '_(not written yet)_';

/** The lab-meeting brief as Markdown: flagged experiments, active ones by project, recent completions. */
export function buildReport(vault, { days = 30, today = isoDate() } = {}) {
  const exps = sortedById(vault.notes.experiment);
  const out = [`# Lab meeting brief - ${today}`, ''];

  const flagged = exps.filter((e) => ciIn(MEETING_TAG, e.getList('tags')));
  out.push(`## Flagged for discussion (\`tags: [${MEETING_TAG}]\`)`, '');
  if (!flagged.length) out.push(`_Nothing flagged. Add \`${MEETING_TAG}\` to an experiment's \`tags\` to put it here._`, '');
  for (const e of flagged) {
    const secs = sections(e.body);
    const proj = e.getList('project').join(', ') || '-';
    out.push(`### ${e.id} - ${e.get('title')}`);
    out.push(`${e.get('researcher')} | project: ${proj} | status: ${e.get('status')} | started ${e.get('date_started')} | \`${e.path}\``);
    out.push('');
    for (const name of ['Objective', 'Results', 'Interpretation', 'Decision']) {
      out.push(`**${name}.** ${clean(secs.get(name) || '')}`, '');
    }
  }

  out.push('## Active experiments by project', '');
  const active = exps.filter((e) => e.get('status') === 'active');
  const byProject = new Map();
  for (const e of active) {
    const projects = e.getList('project');
    for (const p of projects.length ? projects : ['(no project)']) {
      if (!byProject.has(p)) byProject.set(p, []);
      byProject.get(p).push(e);
    }
  }
  if (!active.length) out.push('_No active experiments._', '');
  for (const p of [...byProject.keys()].sort(cmp)) {
    out.push(`### ${p}`, '', '| ID | Title | Researcher | Started | Notebook |', '|---|---|---|---|---|');
    for (const e of byProject.get(p)) {
      out.push(`| ${e.id} | ${e.get('title')} | ${e.get('researcher')} | ${e.get('date_started')} | ${e.get('notebook_reference') || '-'} |`);
    }
    out.push('');
  }

  const cutoff = daysBefore(today, days);
  const recent = exps.filter((e) => e.get('status') === 'complete' && validDate(e.get('date_completed')) && e.get('date_completed') >= cutoff);
  out.push(`## Completed in the last ${days} days`, '');
  if (!recent.length) out.push('_None._');
  for (const e of recent) out.push(`- **${e.id}** ${e.get('title')} (${e.get('researcher')}, completed ${e.get('date_completed')})`);
  out.push('');
  const paused = exps.filter((e) => ['paused', 'abandoned'].includes(e.get('status')));
  if (paused.length) {
    out.push('## Paused / abandoned', '');
    for (const e of paused) out.push(`- **${e.id}** ${e.get('title')} - ${e.get('status')}`);
    out.push('');
  }
  return rstrip(out.join('\n')) + '\n';
}

export const EXPORT_PRIMER = `This is an export from a lab research record (AI_ELN, Shechter Lab). Each note
below is a Markdown file with a small YAML header; the file path is given on
the \`==== ... ====\` line above it.

How to read it:
- IDs: experiments are \`{INITIALS}e{NNNN}\` (e.g. JSRe0002); samples are
  \`{INITIALS}{letter}{NNNN}\` (p plasmid, i oligo, a antibody, c cell-line,
  m mouse-line, t peptide, r protein-prep, s slide, g gel); protocols are
  \`P_{Name}\`; projects are named. A bare ID anywhere is a reference.
- Experiment notes always have these sections: Objective, Experimental
  design, Methods, Deviations from protocol, Results, Interpretation,
  Decision, Follow-up experiments, Files.
- \`status\` is active | complete | paused | abandoned.

Rules for answering questions about this material:
1. Cite the experiment ID (e.g. "JSRe0002") for every factual claim about a result.
2. If the notes don't contain the answer, say so. Do not fill gaps with plausible guesses.
3. Never invent data, numbers, figures, or experiments that are not in the notes.
4. Treat a single experiment as preliminary unless a note says it was replicated.
`;

/** Which experiments an export covers: a project, a status, listed IDs, or everything. */
export function selectForExport(vault, { project = '', experiment_ids = [], status = '', all = false } = {}) {
  const exps = vault.notes.experiment.filter((n) => n.id);
  let chosen = [];
  if (all) chosen = exps;
  else {
    if (project) chosen.push(...findNotes(vault, 'experiment', { project }));
    if (status) chosen.push(...findNotes(vault, 'experiment', { status }));
    for (const id of experiment_ids) {
      const n = vault.get(id);
      if (n === null || n.kind !== 'experiment') throw new ElnError(`experiment ${id} not found`, 'not_found');
      chosen.push(n);
    }
  }
  const seen = new Set();
  return [...chosen].sort((a, b) => cmp(a.id, b.id)).filter((n) => !seen.has(n.id) && seen.add(n.id));
}

const KIND_ORDER = { project: 0, protocol: 1, sample: 2, experiment: 3 };

/** The projects, protocols, samples, and experiments that the chosen experiments refer to. */
export function relatedNotes(vault, experiments) {
  const seen = new Set(experiments.map((e) => e.id));
  const extras = [];
  for (const e of experiments) {
    for (const key of Object.keys(REF_FIELDS.experiment)) {
      for (const ref of e.getList(key)) {
        const t = vault.get(ref);
        if (t !== null && !seen.has(t.id)) {
          seen.add(t.id);
          extras.push(t);
        }
      }
    }
  }
  return extras.sort((a, b) => KIND_ORDER[a.kind] - KIND_ORDER[b.kind] || cmp(a.id, b.id));
}

/** One Markdown document: a primer on how to read the notes, a table of the experiments, then every note. */
export function buildExport(vault, experiments, { related = true, today = isoDate() } = {}) {
  const extras = related ? relatedNotes(vault, experiments) : [];
  const out = [`# AI_ELN export - ${today}`, '', EXPORT_PRIMER, '## Inventory of exported experiments', '',
    '| ID | Title | Researcher | Project | Status | Started | Completed |', '|---|---|---|---|---|---|---|'];
  for (const e of experiments) {
    out.push(`| ${e.id} | ${e.get('title')} | ${e.get('researcher')} | ${e.getList('project').join(', ') || '-'} | `
      + `${e.get('status')} | ${e.get('date_started')} | ${e.get('date_completed') || '-'} |`);
  }
  out.push('', '## Notes', '');
  for (const n of [...experiments, ...extras]) out.push(`==== ${n.path} ====`, rstrip(n.text), '');
  return rstrip(out.join('\n')) + '\n';
}

/** A short word for file names: the project, the first IDs, the status, or 'export'. */
export function exportScope({ project = '', experiment_ids = [], status = '' } = {}) {
  if (project) return project;
  if (experiment_ids.length) return experiment_ids.slice(0, 3).join('-');
  return status || 'export';
}
