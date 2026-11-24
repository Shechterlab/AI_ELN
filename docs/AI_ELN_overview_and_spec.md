# AI_ELN: system overview and specification

*An overview for a person, or to paste into a new conversation with an AI
that has seen nothing else from this repository (`Shechterlab/AI_ELN`). The
rules themselves are in `docs/CONVENTIONS.md`.*

---

## 1. The problem this is solving

The Shechter Lab has a site-licensed LabArchives account, but its editing
interface is cumbersome enough that people put off writing things down. One
lab member (Jacob Roth, PhD student) had built a better way to organize the
record with a folder-naming convention and a spreadsheet. Every experiment
gets a stable ID, the same folder layout, raw data kept apart from processed
data, and a short results summary written soon after the experiment.

Jacob's system already solves the hard part. It lacked a format that can be
searched, that lets records refer to each other, and that an AI assistant
can read. It also lacked a check on the naming as more people use it. This
project writes his system as Markdown notes with a flat header, adds tools
that assign the IDs and check the conventions, lets people use it without
opening a terminal, and lets any AI the lab already pays for read the
result. No API key is needed.

## 2. Core design decisions

1. **Plain Markdown files with a flat header are the record.** The header
   is the `key: value` lines at the top of a note. Any editor, `grep`, a
   spreadsheet, or an AI reads and writes the same files. There is no
   proprietary format, no database, and no required app.
2. **The experiment is the unit.** One ID, one folder, one note.
3. **The header fields and the naming rules are written down in one
   document** (`CONVENTIONS.md`). The tools follow it, and **Check** lists
   what does not. Check advises; it does not stop anyone from writing.
4. **No terminal is needed.** A page in the browser has forms for every
   job. The tool names the folders and files. Notes can be written on the
   page or in any text editor.
5. **Large binary data lives outside the record**, on institutional
   storage. The note records where it is.
6. **A notebook is one folder per person**, kept wherever that person keeps
   their work (Dropbox, OneDrive, a lab share). The tools are separate from
   it. There is no shared lab notebook, no server, no git, and no central
   list of people. Every file is plain text (Markdown, CSV) or an ordinary
   data file.
7. **LabArchives is the archive.** A finished experiment is printed to PDF
   and uploaded by hand. An automatic bridge is not built.
8. **The AI finds and cites what the notes say. It is never the source of
   a conclusion.** It runs on the ChatGPT site license or a Claude
   subscription by reading files and pasted exports. Nothing uses a metered
   API.

## 3. Architecture

The flow from the daily note to the LabArchives copy is drawn in
`docs/design-notes.md`. Everything that creates or reads the notes works on
the same files in the notebook folder:

```
browser page   docs/app/            (Chrome, Edge; nothing installed)  ─┐
launcher page  scripts/eln_web.py   (Safari, Firefox; needs Python)     │
launchers/*.command|.cmd            (double-click)                      ├──► the same files in
scripts/eln.py                      (terminal)                          │    the notebook folder
MCP server     mcp/server.mjs       (AI programs that call tools)       │
Codex / Claude Code / Cowork / Gemini CLI, opened in the tools folder   │
ChatGPT, with a pasted Export and docs/ai-briefing.md                  ─┘
```

There are two pages. The browser page
(<https://shechterlab.github.io/AI_ELN/app/>) does everything and works on
whichever folder is opened. The launcher page is started by `launchers/Open
ELN` on the person's own computer (`127.0.0.1` only) and has the core jobs:
create, edit, Check, meeting brief, export as one file or `.eln`, Mark
complete, and Verify. Adopt, Add files, Repeat this experiment, Print / save
as PDF, Flag for lab meeting, View a notebook (read-only), and the folder
export are in the browser page only. The Python and JavaScript tools write
the same files, and `tests/test_js_parity.py` compares their output.

## 4. Specification (summary; `CONVENTIONS.md` is authoritative)

### 4.1 Layout

A notebook folder:

```
<notebook>/
├── Experiments/{ID}_{title-with-hyphens}/{1-notes,2-data_raw,3-code,4-data_processed,5-figures}/
├── Protocols/P_{Name}.md
├── Samples/{ID}.md
├── Projects/{ID}.md
├── Inventory/{experiments,samples,protocols,projects}.csv   (generated from the notes)
├── Exports/          folders written by Export; copies, safe to delete
├── notebook.md       whose notebook this is (owner, initials) and the last ID given out per kind
├── AGENTS.md         the rules in short, for AI tools
└── lab.yaml          optional: lab name and house style for printouts
```

The tools folder (this repository):

```
├── scripts/eln.py, scripts/eln_web.py, scripts/sync_skills.py
├── docs/app/                                  the browser page and the JavaScript tools
├── mcp/                                       server.mjs (MCP server), call.mjs (one tool from a terminal)
├── templates/{experiment,protocol,sample,project}.md, experiment.{Type}.md for one experiment type
├── launchers/                                 double-click files for Mac and Windows; Open ELN starts the launcher page
├── sandbox/alex/, sandbox/jordan/             two fictional notebooks to practice on; rebuild.py regenerates them
├── AGENTS.md, CLAUDE.md, GEMINI.md, .mcp.json instructions and settings for AI tools
├── .agents/skills/{lab,vendor}/               skills; vendor/ pinned by skills.lock.json
├── docs/                                      CONVENTIONS, CHEATSHEET, getting-started, SOP, ai-*, design-notes
└── tests/                                     run on Ubuntu, macOS, and Windows on every change
```

### 4.2 Identifiers

| thing | pattern | example |
|---|---|---|
| experiment | `{INITIALS}e{NNNN}` | `JSRe0002` |
| sample | `{INITIALS}{letter}{NNNN}`; the letter is the kind of sample: p i a c m t r s g | `JSRp0001` |
| protocol | `P_{Name}` | `P_WesternBlot` |
| project | `{Name}` | `PRMT5-ChromatinRelease` |

Initials are two to four uppercase letters; three are recommended (first,
middle, last). A person's IDs start with their initials, so they do not
match the IDs of someone with different initials. Numbers are counted per
researcher and per kind of record and are never reused. An ID written
anywhere is a reference to that record. An experiment or sample ID with
someone else's initials refers to a record in that person's notebook, and
Check does not report it as missing.

### 4.3 Filenames

`{EXPERIMENT_ID}[_{R|P}]_{words-with-hyphens}[_{YYYYMMDD}].{ext}` for every
file a person creates inside an experiment folder. `R` marks the results
summary. `P` marks a copy of a protocol as it was run (written by the
tool). `2-data_raw/` is exempt: instrument output is never renamed.

### 4.4 Header

One `key: value` per line (a small, flat part of the YAML format), lists as
`[a, b]`, no nesting, dates as `YYYY-MM-DD`, optional `# comment`.
`CONVENTIONS.md` §4 has, for each kind of note, the required fields, the
fields Check warns about when empty, the allowed values of `status` and
`sample_type`, and the fixed body sections. The template for each kind
lists the allowed keys, and Check warns about any other.

### 4.5 `scripts/eln.py`

Python 3.9 or later, standard library only. Every command takes `--root`.
Without it, the notebook is the folder in `AI_ELN_ROOT`, then the one saved
by `init` (in `~/.ai_eln.json`), then the tools folder itself.

| command | does |
|---|---|
| `init` | saves initials, name, and the notebook folder (`--root`); creates the folders; writes the owner into `notebook.md` and a short `AGENTS.md` into a notebook outside the tools folder |
| `new experiment/sample/protocol/project` | assigns the ID, fills in the template, copies the protocols as run, rebuilds the index; `--interactive` asks questions (used by the launchers), `--open` opens the note |
| `adopt [FOLDER]` | makes an experiment record from an older folder and moves the folder, unchanged, into its `2-data_raw/`; with no folder, lists the folders in the notebook that are not records; `--copy` leaves the original in place |
| `validate [--strict]` | Check: every rule in `CONVENTIONS.md` §6; errors fail, warnings advise |
| `index` | regenerates the five CSV files from the notes, including which experiments used each sample and protocol |
| `find` | filters by project, status, researcher, tag, sample, protocol, type, or free text; `--ids`, `--json` |
| `report` | the lab-meeting brief in Markdown: experiments flagged with `tags: [meeting]`, active experiments by project, recently completed, paused or abandoned |
| `export` | the chosen experiments and the records they refer to: one Markdown file with a short explanation for the AI (default), `--format folder` for a folder of plain files in `Exports/`, `--format eln` for a `.eln` archive that other electronic notebooks import |
| `complete` | Mark complete: refuses if Results or Interpretation is empty (unless `--force`), sets `status` and `date_completed`, writes `{ID}_snapshot_{date}.html` (one HTML file with the whole experiment, for printing) and `{ID}_MANIFEST.sha256` (a list of checksums: numbers computed from each file's content, used to detect changes), rebuilds the index |
| `verify` | compares a completed experiment's files with its list of checksums (missing, modified, added) |
| `render` | writes one note as a single HTML file with the images embedded |

While a record is created the tools hold a lock (an empty `.eln-lock`
folder at the top of the notebook, there for a moment), so two programs
working in the same notebook cannot give out the same ID.

### 4.6 AI contract

`AGENTS.md` in the tools folder carries the rules (Codex and others read it
on their own); `CLAUDE.md` and `GEMINI.md` point at it. An AI tool is
opened in the tools folder and works on the notebook named with `init
--root`. `.agents/skills/lab/` holds three lab skills (record an
experiment, search and cite, project synthesis). `.agents/skills/vendor/`
holds fifteen methodology skills from K-Dense, pinned by
`skills.lock.json`, copied by `scripts/sync_skills.py`, checked weekly
against upstream, and updated only as a reviewed diff. `mcp/server.mjs`
offers the notebook's operations as tools to AI programs that support MCP
(a way for AI programs to call tools); `.mcp.json` tells Claude Code and
Cowork where it is. For ChatGPT, `docs/ai-briefing.md` is pasted once as
Project instructions, and **Export** produces the text to paste. Details:
`docs/ai-agents.md`.

No API key or vector database is involved.

## 5. What's built vs. not

**Built and tested:**
- `CONVENTIONS.md`, `CHEATSHEET.md`, the templates
- `scripts/eln.py` with all commands above
- The browser page (`docs/app/`) and the launcher page
  (`scripts/eln_web.py`)
- Double-click launchers for Mac and Windows, including `Open ELN` and `Try
  the Sandbox`
- The MCP server and `mcp/call.mjs`
- `sandbox/alex` and `sandbox/jordan`: two fictional notebooks with ten
  experiments between them, generated by `sandbox/rebuild.py`, with the AI
  skills run against them (`sandbox/PILOT.md`)
- `scripts/sync_skills.py`, `skills.lock.json`, fifteen vendored skills
- `AGENTS.md`/`CLAUDE.md`/`GEMINI.md`, three lab skills, ChatGPT briefing
- GitHub Actions: tests on Ubuntu, macOS, and Windows with Python 3.9 and
  3.12; a strict Check of the sandbox notebooks; the notebook page in a
  headless browser; a weekly check of the vendored skills against upstream
- `.eln` export checked with the reference library for the format it is
  built on (RO-Crate)

**Not built (discussed):**
- The LabArchives archival bridge (needs institutional API access)
- Scheduled project synthesis
- Instrument ingestion, and a record of which raw file produced which
  processed file and figure
- A search-by-meaning index

## 6. Staged rollout

The phases (pilot, lab-wide rollout with the SOP, LabArchives bridge,
ingestion) are in `docs/design-notes.md` under "What this repo builds now
vs. later". The pilot is 2–3 people, one project, and about 20 experiments,
to collect what Check reports and what people skip.

## 7. Open questions

- **ID scheme longevity.** Initials plus a number is readable and matches
  the existing habit. Two people with the same initials would get the same
  IDs. Is that ever a problem here?
- **Searching across notebooks.** Each person has their own notebook and
  index. The page lists the notebooks in a shared folder, but each tool
  searches one notebook at a time. Is a search across all of them needed?
- **Which file came from which.** What is the smallest record of raw file
  to processed file to figure that is worth keeping by hand before
  ingestion writes it?
- **Limit of keyword search.** At how many notes do `find` and `grep`
  start missing things, and is a keyword index a sufficient next step?
- **LabArchives snapshot shape.** Is a rendered PDF/HTML enough for the
  institution's definition of an adequate record?
