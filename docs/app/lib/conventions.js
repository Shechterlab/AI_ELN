/* The conventions in one screen of text. Given to AI clients as instructions (MCP) and written as
   AGENTS.md into a notebook folder that the page sets up. docs/CONVENTIONS.md is the full version. */

export const SITE = 'https://shechterlab.github.io/AI_ELN/';

export const CONVENTIONS_SUMMARY = `This folder is a plain-text lab notebook (AI_ELN). Every record is a Markdown file with a flat YAML header.

Layout
  Experiments/{ID}_{short-title}/
    1-notes/           {ID}.md is the experiment note; {ID}_P_{Protocol}_{YYYYMMDD}.md is the protocol as run
    2-data_raw/        instrument output, original file names, never edited or renamed
    3-code/            {ID}_what-it-does.R / .py
    4-data_processed/  {ID}_what-it-is.csv
    5-figures/         {ID}_R_what-it-shows_{YYYYMMDD}.png is the result figure
  Protocols/P_{Name}.md      one file per protocol, edited in place, with a version date
  Samples/{ID}.md            plasmids, oligos, antibodies, cell lines, gels and so on
  Projects/{Name}.md         summary of a research project; conclusions cite experiment IDs
  Inventory/*.csv            index generated from the note headers; do not edit by hand
  notebook.md                whose notebook this is and the last IDs given out; kept by the tools
  Exports/                   folders written by Export: copies, never cite or edit them
  Other folders here are not records. An older folder becomes an experiment with the adopt tool:
  it gets an ID and is moved, unchanged, into that experiment's 2-data_raw/.

IDs
  Experiment  {INITIALS}e{NNNN}        JSRe0002
  Sample      {INITIALS}{letter}{NNNN} JSRp0001  (p plasmid, i oligo, a antibody, c cell-line, m mouse-line,
                                                  t peptide, r protein-prep, s slide, g gel)
  Protocol    P_{Name}                 P_WesternBlot
  Project     {Name}                   PRMT5-ChromatinRelease
  An ID written anywhere is a reference to that record. Numbers are never reused.
  A notebook belongs to one person. An experiment or sample ID with other initials (ALXc0001 in a note of
  JOR) is a record in that person's notebook, a different folder: it is not missing, and it is not created here.

File names
  {ID}[_R|_P]_{words-with-hyphens}[_{YYYYMMDD}].ext
  Fields are separated by "_", words inside a field by "-". Everything outside 2-data_raw starts with the ID.

Header
  One "key: value" per line, lists as [a, b], dates as YYYY-MM-DD, no nesting.
  Experiment status: active | complete | paused | abandoned. tags: [meeting] flags it for lab meeting.

Experiment sections, always in this order
  Objective, Experimental design, Methods, Deviations from protocol, Results, Interpretation, Decision,
  Follow-up experiments, Files

Rules for an AI assistant
  1. Cite the experiment ID for every factual claim about a result.
  2. If the notes do not contain the answer, say so. Never invent data, numbers, figures, or experiments.
  3. Create experiments, samples, protocols, and projects with the tools, not by making files by hand.
  4. Never change anything in 2-data_raw.
  5. Write into Results or Interpretation only what the researcher gave you or what the data files show.
  6. Treat a single experiment as preliminary unless a note says it was replicated.

Full conventions: ${SITE}guide.html?d=CONVENTIONS
`;

export const AGENTS_MD = `# Agent instructions: lab research record\n\n${CONVENTIONS_SUMMARY}`;
