# Conventions: IDs, folders, filenames, metadata

These are the rules. The `eln.py` tool, the templates, Check, and the
instructions for AI tools all follow this page. If a tool and this page
disagree, this page is right and the tool has a bug.

## 0. Summary

1. **One folder per experiment**, five fixed subfolders, same shape every time.
2. **One Markdown note** per experiment, protocol, sample, project, and figure,
   with a small YAML header on top.
3. **IDs are assigned by the tool**, never typed by hand, never reused.
4. **Filenames start with the ID they belong to.** Raw instrument output is
   never renamed.
5. **The YAML header is flat**: `key: value` and `key: [a, b]`. Nothing else.

## 1. Identifiers

| Thing | Pattern | Example | Who assigns it |
|---|---|---|---|
| Experiment | `{INITIALS}e{NNNN}` | `JSRe0002` | `eln.py new experiment` |
| Sample | `{INITIALS}{letter}{NNNN}` | `JSRp0001` | `eln.py new sample` |
| Protocol | `P_{Name}` | `P_WesternBlot` | `eln.py new protocol` |
| Project | `{Name}` | `PRMT5-ChromatinRelease` | `eln.py new project` |
| Figure | `{INITIALS}f{NNNN}` | `JSRf0001` | `eln.py new figure` |

- **`INITIALS`**: uppercase letters, one set per researcher (`JSR`, `DSL`).
  Use three: first, middle, and last initial. Two to four are accepted, but
  two-letter initials are more likely to be the same as someone else's, and
  the tools say so when you set them. Because your IDs start with your
  initials, nobody else's IDs can match yours, and no shared counter is
  needed.
- **An ID with someone else's initials** refers to a record in that person's
  notebook (`samples: [ALXc0001]` in a note of `JOR`). Check cannot see that
  record and does not report it as missing. It does report a missing record
  whose initials are the notebook's own. A mistyped set of initials therefore
  goes unnoticed; read them once when you write them.
- **`NNNN`**: four digits with leading zeros, counted separately for each
  researcher and each kind of record. `JSRe0002` and `JSRp0002` have nothing
  to do with each other. A number is never used again, even if the
  experiment is abandoned.
- **`e`** marks an experiment. For a sample, the letter says what kind:

  | letter | `sample_type` | letter | `sample_type` |
  |---|---|---|---|
  | `p` | plasmid | `m` | mouse-line |
  | `i` | oligo (primer, gRNA, RNA) | `t` | peptide |
  | `a` | antibody | `r` | protein-prep |
  | `c` | cell-line | `s` | slide |
  | `g` | gel / blot | | |

  A gel gets a sample ID because it is a physical thing that is kept, and
  several experiments can refer to the same gel.

- **Protocol names** are written as words run together with a capital at the
  start of each (`WesternBlot`), or joined with hyphens
  (`Cellular-Fractionation`). Letters, digits, and hyphens only. Every
  protocol ID starts with `P_`, so a search for `P_` finds them all. There
  is **one file per protocol**, edited in place. When the procedure changes,
  the `version` date in its header is changed too (see §4).
- **Project IDs** are a short name: letters, digits, hyphens; starts with a
  letter.

To refer to a record, write its ID (`JSRe0002`, `P_WesternBlot`, `DSLp0003`)
in the header field for it, or in the text. Nothing else is needed: no link
syntax and no path. Check looks up every ID written in a header field and
reports any that match no record.

## 2. Folders

```
<root>/
├── Experiments/
│   └── {EXPERIMENT_ID}_{slug}/
│       ├── 1-notes/            {EXPERIMENT_ID}.md lives here, plus protocol snapshots
│       ├── 2-data_raw/         instrument output, untouched (or a pointer to where it is)
│       ├── 3-code/             analysis scripts and notebooks
│       ├── 4-data_processed/   anything derived from raw by a script or by hand
│       └── 5-figures/          exported panels; the results summary lives here
├── Protocols/    P_{Name}.md
├── Samples/      {SAMPLE_ID}.md
├── Projects/     {PROJECT_ID}.md
├── Figures/
│   └── {FIGURE_ID}_{slug}/
│       ├── 1-notes/            {FIGURE_ID}.md lives here
│       ├── 2-panels/           one file per panel, as it goes into the figure
│       ├── 3-source/           the file the figure is laid out in, whatever the program
│       └── 4-exports/          the finished figure, one file per version sent out
├── Inventory/    experiments.csv, samples.csv, protocols.csv, projects.csv, figures.csv  (generated)
├── AGENTS.md     the rules in short, for AI tools opened in this folder; written at setup
├── Exports/      folders written by Export: copies, safe to delete
├── notebook.md   whose notebook this is and the last IDs given out; kept by the tool
└── lab.yaml      optional: lab name and house style for printouts
```

- The **slug** is the title with accents removed (`Résumé` becomes
  `Resume`) and anything that still isn't a letter or digit turned into
  `-`, trimmed to 60 characters. Case is kept so gene names stay
  readable (`SNRPB-chromatin-retention`). The tool makes the slug.
- The five subfolders are created by the tool. Do not rename them, reorder
  them, or add others to one experiment: search, Check, and the index
  rely on every experiment having the same five.
- `<root>` is the notebook folder: one per person, kept wherever that
  person keeps their work (Dropbox, OneDrive, a lab share, a drive). There
  is no server, no central copy, and no list of people. The browser page
  works on the folder you open; the Python tools work on the folder named
  with `eln.py init --root`, or on the folder the tools sit in if none is
  named. Other folders may sit in `<root>` next to these, and the tools
  leave them alone. A folder inside `Experiments/` without an ID in its name
  is different: Check reports it, and it should be adopted or moved out.
- `Inventory/` holds the index tables, which the tool makes from the notes.
  Do not edit them by hand; edit the note and the index follows. The meeting
  brief and single-file exports are saved in `Inventory/` too.

### notebook.md and lab.yaml

`notebook.md` is a short note at the top of the notebook folder. Its header
says whose notebook it is and remembers the last ID given out for each kind
of record:

```yaml
---
type: notebook
owner: Jacob Roth
initials: JSR
last_ids: [JSRa0003, JSRe0012, JSRp0004]
---
```

The tool writes it. The next ID is one more than the higher of the number
here and what is in the folders, so a number is not given out again when a
folder is deleted or has not synced yet. You may correct `owner` and
`initials`, and write anything you like below the header. Do not lower a
number in `last_ids`. Keep the header in the form shown: one `key: value`
per line and the list in square brackets. If the header cannot be read, the
tools leave the file alone and Check says what is wrong with it. If the file
is deleted, the next record makes it again from the IDs the folders show.

**Whose initials a new record gets.** In this order: initials given with the
command (`--initials`), then the `initials` in `notebook.md`, then the
initials saved on the computer or in the browser. A notebook that names its
owner is that person's: someone else's saved settings do not put their
initials into it. A notebook that several people write in leaves `owner`
and `initials` empty, and each person's saved initials are used.

**One record at a time.** While a record is being created the tools hold a
lock: an empty folder named `.eln-lock` at the top of the notebook, there
for a moment. Two programs working in the same notebook at once (two
windows, a person and an AI tool) therefore cannot give out the same ID. If
a crash leaves it behind it is taken over after a minute; it can also be
deleted by hand.

### Adopted folders

An older folder becomes a record with **Adopt** (`eln.py adopt`). The
experiment gets the next ID and the tag `adopted`. The old folder is moved,
whole and unchanged, to `2-data_raw/{old folder name}/`.
`1-notes/{ID}_adopted-files.csv` lists every file with its size and the time
it was last modified before the move (in UTC). The title and `date_started`
are read from the folder name where it holds a date (`2019-03-04_PRMT5
western`), otherwise from the oldest file date; `date_completed` is the
newest file date. Links inside the folder are moved as links and never
followed. A folder that is itself a link, is named `README.md`, or has a
line break in its name is refused: rename it or adopt the real folder.
Results and Interpretation say "Not written" until someone writes them.

`lab.yaml` (optional, at the top of the notebook folder) holds the lab's
name, institution, and house style in the same flat `key: value` form. It
overrides `docs/lab.yaml` from the tools for this notebook's snapshots,
printouts, and exports.

## 3. Filenames

Every file that belongs to an experiment starts with that experiment's ID.
The full grammar:

```
{EXPERIMENT_ID}[_{KIND}]_{description}[_{YYYYMMDD}].{ext}
```

- Fields are separated by `_`. Words *inside* a field are joined with `-`.
- `{KIND}` is optional and is one uppercase letter:
  - **`R`**: the result summary, the one figure or document you would show
    in lab meeting. A search for `JSRe0002_R` finds it.
  - **`P`**: a copy of a protocol as it was run. The tool writes these when
    an experiment is created with a protocol.
- `{YYYYMMDD}` is optional. Use it when a file is made again later.
- Every other file (Illustrator, Prism, notebooks, tables) is
  `{EXPERIMENT_ID}_{description}.{ext}`. The extension says what kind of
  file it is.

Examples:

```
JSRe0002_R_fractionation-KCl-titration_20230204.png
JSRe0002_P_CellularFractionation_20220119.md
JSRe0002_quantification.csv
JSRe0002_analysis.R
JSRe0002_figure-1.ai
JSRe0002_snapshot_20230210.html      written by the tool at completion: the note as one printable file
JSRe0002_MANIFEST.sha256             written by the tool at completion: every file's checksum
```

**The one exception: `2-data_raw/`.** Instrument output keeps the name the
instrument gave it. A renamed raw file can no longer be matched to the
instrument's own records, and that cannot be undone later. If the raw data is too big to live here (microscopy, sequencing,
mass spec), it stays on institutional storage and the note's
`raw_data_path` points at it; a short `README.md` in `2-data_raw/` saying
where it went is welcome.

`README.md` and dotfiles are exempt from the naming rule everywhere.

**What the manifest covers.** Every file in the experiment folder, hidden
files included (`.RData` is data). Left out: what the operating system and
Office leave around (`.DS_Store`, `._*`, `Thumbs.db`, `desktop.ini`, `~$*`),
and links. A link is never followed, in a manifest, a snapshot, or an
export, so a file outside the notebook cannot end up in one by accident.

## 4. The YAML header (front matter)

Every note starts with a header between two `---` lines. It uses a small,
**flat** part of the YAML format, so that it can be read by `grep`, by a
short function in R or Python, by any YAML library, and by an AI model that
has never seen the file before:

```yaml
---
key: value                 # a plain scalar
another_key: [a, b, c]     # a flat list, comma-separated, in square brackets
empty_key:                 # empty is fine
---
```

Rules:

- One `key: value` per line. Keys are `snake_case`.
- Lists are always the inline `[a, b]` form. Never the `- item` block form.
- No nesting, no values that run over several lines, no anchors. Anything
  that needs those belongs in the body of the note.
- Dates are `YYYY-MM-DD`. Booleans are `true` / `false`.
- A `# comment` after a value is allowed (the templates use them as hints).
- Quotes are only needed if a value contains `:` or `#` or starts with `[`.

### 4.1 Experiment

| field | required | type / allowed values |
|---|---|---|
| `type` | yes | `experiment` |
| `experiment_id` | yes | matches the folder |
| `title` | yes | specific enough to identify it out of context |
| `researcher` | yes | full name |
| `project` | should | list of project IDs |
| `date_started` | yes | date |
| `date_completed` | when complete | date |
| `status` | yes | `active` · `complete` · `paused` · `abandoned` |
| `experiment_type` | no | list; any words, see the suggestions below |
| `protocols` | should | list of protocol IDs |
| `samples` | no | list of sample IDs |
| `notebook_reference` | no | physical notebook page, e.g. `NB02-153` |
| `raw_data_path` | should | where the raw data actually lives |
| `related_experiments` | no | list of experiment IDs |
| `tags` | no | list. `meeting` = flag for the next lab meeting |

"Should" means Check warns if it is empty; it is required by the SOP
by the time the experiment is complete, but you don't have to know it on
day one.

Suggested `experiment_type` vocabulary (free text, but sticking to a
shared list makes filtering work): `WesternBlot`, `Fractionation`,
`IP`, `IF`, `qPCR`, `RNAseq`, `ChIPseq`, `MassSpec`, `Cloning`,
`CellCulture`, `MouseWork`, `Microscopy`, `Purification`, `Kinetics`.

Body sections, in this order, always present even if a section only says
"None" (keeping them makes notes comparable across the lab):
**Objective · Experimental design · Methods · Deviations from protocol ·
Results · Interpretation · Decision · Follow-up experiments · Files.**

In *Interpretation*, mark what is tentative as such ("Preliminary:",
"n = 1", "suggests"). An AI reading the note later is told to keep those
hedges; it can only keep what is there.

A per-type template may add prompts to the body: if
`templates/experiment.{Type}.md` exists for the first `experiment_type`
given, it is used instead of `templates/experiment.md`. It must keep the
same header keys and section titles; only the hints change.
`templates/experiment.WesternBlot.md` is the example to copy.

### 4.2 Protocol

| field | required | type / allowed values |
|---|---|---|
| `type` | yes | `protocol` |
| `protocol_id` | yes | `P_{Name}`, matches the filename |
| `title` | yes | |
| `version` | yes | date of the last procedural change |
| `status` | yes | `current` · `archived` |
| `supersedes` | no | ID of an older protocol this one replaces |
| `references` | no | list (DOIs, URLs, paper IDs) |
| `tags` | no | list |

One file per protocol, edited in place. When you change the *procedure*,
change `version` to the date and add a line to the **Change log** section.
When an experiment uses a protocol, the tool copies the current file into
the experiment's `1-notes/` as `{EXPERIMENT_ID}_P_{Name}_{YYYYMMDD}.md`.
That copy is the record of what was followed. Deviations on the day go in
the experiment note, not in the protocol file.

Body sections: **Purpose · Materials · Procedure · Known failure modes /
troubleshooting · Change log.**

### 4.3 Sample

| field | required | type / allowed values |
|---|---|---|
| `type` | yes | `sample` |
| `sample_id` | yes | `{INITIALS}{t}{NNNN}`, matches the filename; letter matches `sample_type` |
| `sample_type` | yes | one of the types in §1 |
| `title` | yes | |
| `source` | should | vendor, in-house (which experiment?), gift from whom |
| `date_created` | yes | date |
| `storage_location` | should | freezer / box / position |
| `status` | yes | `active` · `depleted` · `retired` |
| `tags` | no | list |

Which experiments used a sample is not written in the sample note. It is
worked out from the experiment notes each time: see `Inventory/samples.csv`
or `eln.py find --sample ID`. So it is always current.

Body sections: **Description · Provenance · Validation · Notes.**

### 4.4 Project

| field | required | type / allowed values |
|---|---|---|
| `type` | yes | `project` |
| `project_id` | yes | matches the filename |
| `title` | yes | |
| `lead` | yes | |
| `contributors` | no | list |
| `status` | yes | `active` · `complete` · `paused` |
| `date_started` | yes | date |
| `grants` | no | list |
| `publications` | no | list |
| `tags` | no | list |

Body sections: **Aim / hypothesis · Current state** (with *Supported
conclusions*, *Open questions / conflicting observations*, *Experiments
needing replication*; every conclusion cites experiment IDs) **·
Experiments · Reagents in use · Figures · Related protocols.**

### 4.5 Figure

A figure record is for an assembled figure that goes out: into a paper, a
grant, a talk, a thesis. It draws on one or more experiments and says which
experiment each panel came from. The result figure of a single experiment is
not a figure record; it stays in that experiment's `5-figures/`.

The record does not depend on the program the figure is made in. Panels can
come from R, Python, Prism, or an instrument's own software, and the layout
can be an Illustrator, CanvasX, PowerPoint, or Inkscape file, or a script.
The record holds the files and says where each one came from.

| field | required | type / allowed values |
|---|---|---|
| `type` | yes | `figure` |
| `figure_id` | yes | matches the folder name |
| `title` | yes | |
| `researcher` | yes | |
| `project` | no | list of project IDs |
| `experiments` | should | list of experiment IDs the panels come from |
| `label` | no | what it is called where it is used: `Figure 2`, `Fig. S3` |
| `target` | no | where it is going: a journal, a grant, a talk |
| `tools` | no | list: `R`, `Prism`, `Illustrator`, ... |
| `width_mm`, `height_mm` | no | the finished size |
| `date_started` | yes | date |
| `date_final` | when final | date |
| `status` | yes | `draft` · `final` · `published` · `retired` |
| `tags` | no | list |

The ID does not change. The `label` does, whenever figures are renumbered,
so refer to a figure by its ID in notes and by its label in the manuscript.

Body sections: **Purpose · Panels · Legend · Size and format · Versions ·
Files.** *Panels* is a table with one row per panel:

```
| Panel | Shows | From | Data | Made with | File |
|---|---|---|---|---|---|
| a | SNRPB in each fraction, DMSO vs PRMT5i | JSRe0002 | 2-data_raw (replicate 1 scan) | Image Studio export | `JSRf0001_a_blot.png` |
| b | chromatin-bound fraction, n = 3 | JSRe0002 | `4-data_processed/JSRe0002_quantification.csv` | `3-code/JSRe0002_plot.R` | `JSRf0001_b_quantification.pdf` |
```

*From* is the experiment ID. *Data* is the file that was plotted and *Made
with* is the script or program that drew it, both as paths inside that
experiment. *File* is the panel as it sits in `2-panels/`. A panel file is a
copy; the original stays in its experiment. Every file in a figure folder
starts with the figure ID. In `4-exports/` keep one file per version that
was sent to anyone (`JSRf0001_v2_20260930.pdf`), do not overwrite an old
one, and add a line under *Versions* saying who got it and what changed.

## 5. Dates and statuses

- Dates in headers: `YYYY-MM-DD`. Dates in filenames: `YYYYMMDD`, which
  sorts in date order.
- Keep `status` up to date; it is the one field that needs it. An experiment
  is `complete` when Results and Interpretation are written and
  `raw_data_path` points at backed-up storage. Set it with **Mark
  complete** on the page or `eln.py complete ID`: that refuses if Results
  or Interpretation is empty, warns if `raw_data_path` cannot be found (it
  cannot check that the place is backed up; that is yours to know), sets
  `status` and `date_completed`, and writes two standard
  files next to the note, a self-contained HTML snapshot and a
  `sha256sum`-format manifest, so the state of the folder at completion is
  recorded and later changes are detectable (`eln.py verify`). Nothing is
  locked. Completing an experiment again rewrites the snapshot and the
  manifest, keeps the original `date_completed`, and reports which files
  changed since the last manifest. `paused` and `abandoned` both need one
  sentence in the note saying why.

## 6. What Check reports

**Check** (`eln.py validate`) reads every note and folder in the notebook
and lists what it finds. An error makes the command fail. A warning is
advice, unless you pass `--strict`.

**Errors**, which have to be fixed:

- Experiment folder name doesn't match `{ID}_{slug}`; a subfolder is
  missing; there's no `1-notes/{ID}.md`; the note's `experiment_id`
  doesn't match the folder.
- The same four for a figure folder under `Figures/`.
- A header that doesn't parse, a missing required field, a `status` or
  `sample_type` outside the allowed set, a date that isn't `YYYY-MM-DD`.
- A protocol / sample / project whose filename doesn't match its ID, or a
  sample whose type letter doesn't match its `sample_type`.
- The same ID appearing twice anywhere. (A copy that a sync service made of
  a file is reported as a warning with what to do about it; see "Offline
  work and sync copies" in the getting-started guide.)

**Warnings**, which are worth fixing soon:

- An ID in `project`, `protocols`, `samples`, `related_experiments`,
  `supersedes`, or a figure's `experiments` that matches no record (an experiment or sample ID with
  someone else's initials is not reported; see §1).
- Something wrong with `notebook.md` (see §2).
- `project`, `protocols`, or `raw_data_path` still empty (not reported for
  `project` and `protocols` on a record adopted from an older folder).
- A file in `1-notes/`, `3-code/`, `4-data_processed/`, or `5-figures/`
  that doesn't start with the experiment ID.
- An experiment marked `complete` with an empty Results or Interpretation
  section, or no `date_completed`.
- In a figure: a file that doesn't start with the figure ID; an experiment
  named in the Panels table but not in `experiments`; a panel file named in
  the table that is not in `2-panels/`; `final` or `published` with no
  `date_final` or nothing in `4-exports/`.
- A required body section missing, or a header key that isn't in the
  template (usually a typo).

Run it before lab meeting, before archiving anything, and before giving a
folder to someone else.
