# Conventions — IDs, folders, filenames, metadata

This is the contract. Everything else in the repo (the `eln.py` tool, the
templates, the validator, the AI instructions) implements what's written
here. If the tool and this page ever disagree, this page wins and the tool
has a bug.

It is deliberately short. A convention people can hold in their head is one
they'll follow.

## 0. The whole system in five lines

1. **One folder per experiment**, five fixed subfolders, same shape every time.
2. **One Markdown note** per experiment, protocol, sample, and project, with a
   small YAML header on top.
3. **IDs are assigned by the tool**, never typed by hand, never reused.
4. **Filenames start with the ID they belong to.** Raw instrument output is
   never renamed.
5. **The YAML header is flat**: `key: value` and `key: [a, b]`. Nothing else.

## 1. Identifiers

| Thing | Pattern | Example | Who assigns it |
|---|---|---|---|
| Experiment | `{INITIALS}e{NNNN}` | `JSRe0002` | `eln.py new experiment` |
| Sample | `{INITIALS}{t}{NNNN}` | `JSRp0001` | `eln.py new sample` |
| Protocol | `P_{Name}` | `P_WesternBlot` | `eln.py new protocol` |
| Project | `{Name}` | `PRMT5-ChromatinRelease` | `eln.py new project` |

- **`INITIALS`** — 2 to 4 uppercase letters, one set per researcher (`JSR`,
  `DSL`). Your initials are your namespace: your numbering never collides
  with anyone else's, so no central counter is needed.
- **`NNNN`** — four digits, zero-padded, sequential *per researcher and per
  type*. `JSRe0002` and `JSRp0002` are unrelated. Numbers are never reused,
  even if an experiment is abandoned.
- **`e`** marks an experiment. The sample type letter `t` is one of:

  | letter | `sample_type` | letter | `sample_type` |
  |---|---|---|---|
  | `p` | plasmid | `m` | mouse-line |
  | `i` | oligo (primer, gRNA, RNA) | `t` | peptide |
  | `a` | antibody | `r` | protein-prep |
  | `c` | cell-line | `s` | slide |
  | `g` | gel / blot | | |

  A gel is a "sample" here in the sense that matters: a durable physical
  thing with its own ID that several experiments may refer to.

- **Protocol names** are PascalCase or kebab-case, letters/digits/hyphens
  only (`P_WesternBlot`, `P_Cellular-Fractionation`). The `P_` prefix makes
  every protocol findable with one search. There is **one file per
  protocol**, edited in place; the `version` date in its header is bumped
  when the procedure changes (see §4).
- **Project IDs** are a short name: letters, digits, hyphens; starts with a
  letter.

An ID is the link. To refer to something, write its bare ID —
`JSRe0002`, `P_WesternBlot`, `DSLp0003` — in the relevant header field or
in prose. No wiki-link syntax, no paths. The validator resolves every
reference and tells you if one points nowhere.

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
└── Inventory/    experiments.csv, samples.csv, protocols.csv, projects.csv  (generated)
```

- The **slug** is the title with anything that isn't a letter or digit
  turned into `-`, trimmed to 60 characters. Case is kept so gene names stay
  readable (`SNRPB-chromatin-retention`). The tool makes it; you don't.
- The five subfolders are created by the tool and are never renamed,
  reordered, or added to per experiment. The value of the system is that
  every experiment looks the same.
- `<root>` is the folder these tools sit in: the one the lab syncs with
  Dropbox or OneDrive. Tools and record travel together; there is no
  server and no central copy. (`eln.py init --root` exists for the unusual
  case of keeping the notes somewhere else. See `docs/getting-started.md`.)
- `Inventory/` is **generated** by `eln.py index` from the notes. Never
  hand-edit it; edit the note and re-index.

## 3. Filenames

Every file that belongs to an experiment starts with that experiment's ID.
The full grammar:

```
{EXPERIMENT_ID}[_{KIND}]_{description}[_{YYYYMMDD}].{ext}
```

- Fields are separated by `_`. Words *inside* a field are joined with `-`.
- `{KIND}` is optional and is one uppercase letter:
  - **`R`** — the results summary: the one figure or document you'd pull up
    in lab meeting. Searching `JSRe0002_R` jumps straight to it.
  - **`P`** — a snapshot of a protocol as it was actually run. The tool
    writes these for you when you pass `--protocol`.
- `{YYYYMMDD}` is optional; use it when a file gets regenerated over time.
- Everything else (Illustrator, Prism, notebooks, tables) is just
  `{EXPERIMENT_ID}_{description}.{ext}` — the extension already says what
  it is.

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

**The one exemption: `2-data_raw/`.** Instrument output keeps whatever name
the instrument gave it. Renaming raw data breaks the chain back to the
acquisition and is exactly the kind of "cleanup" that later can't be
undone. If the raw data is too big to live here (microscopy, sequencing,
mass spec), it stays on institutional storage and the note's
`raw_data_path` points at it; a short `README.md` in `2-data_raw/` saying
where it went is welcome.

`README.md` and dotfiles are exempt everywhere.

## 4. The YAML header (front matter)

Every note starts with a header between two `---` lines. It uses a **flat
subset** of YAML on purpose, so that it's parseable by `grep`, by a
ten-line function in R or Python, by every YAML library, and by any AI
model reading the file cold:

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
- No nesting, no multi-line values, no anchors. If you feel the need for
  any of those, the information belongs in the note body instead.
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
| `experiment_type` | no | list; free vocabulary — see suggestions below |
| `protocols` | should | list of protocol IDs |
| `samples` | no | list of sample IDs |
| `notebook_reference` | no | physical notebook page, e.g. `NB02-153` |
| `raw_data_path` | should | where the raw data actually lives |
| `related_experiments` | no | list of experiment IDs |
| `tags` | no | list. `meeting` = flag for the next lab meeting |

"Should" means the validator warns if it's empty; it's required by the SOP
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

One living file per protocol. When you change the *procedure*, bump
`version` and add a line to the **Change log** section. When an experiment
uses a protocol, the tool copies the current file into the experiment's
`1-notes/` as `{EXPERIMENT_ID}_P_{Name}_{YYYYMMDD}.md` — that copy is the
permanent record of what was actually followed. Deviations on the day go in
the experiment note, never in the living protocol.

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

Which experiments used a sample is **derived** — it's in
`Inventory/samples.csv` and from `eln.py find --sample ID` — not stored in
the sample note, so it can't go stale.

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
needing replication* — every conclusion cites experiment IDs) **·
Experiments · Reagents in use · Figures · Related protocols.**

## 5. Dates and statuses

- Dates in headers: `YYYY-MM-DD`. Dates in filenames: `YYYYMMDD` (sorts
  correctly, no separators to argue about).
- `status` is the one field you're expected to keep current. An experiment
  is `complete` when Results and Interpretation are written and
  `raw_data_path` points at backed-up storage. Set it with **Mark
  complete** on the page or `eln.py complete ID`: that checks those
  conditions, sets `status` and `date_completed`, and writes two standard
  files next to the note, a self-contained HTML snapshot and a
  `sha256sum`-format manifest, so the state of the folder at completion is
  recorded and later changes are detectable (`eln.py verify`). Nothing is
  locked. `paused` and `abandoned` both need one honest sentence in the
  note saying why.

## 6. What the validator enforces

`eln.py validate` reads the whole vault and reports. Errors fail; warnings
are advice unless you pass `--strict`.

**Errors** — things that break the system:

- Experiment folder name doesn't match `{ID}_{slug}`; a subfolder is
  missing; there's no `1-notes/{ID}.md`; the note's `experiment_id`
  doesn't match the folder.
- A header that doesn't parse, a missing required field, a `status` or
  `sample_type` outside the allowed set, a date that isn't `YYYY-MM-DD`.
- A protocol / sample / project whose filename doesn't match its ID, or a
  sample whose type letter doesn't match its `sample_type`.
- The same ID appearing twice anywhere.

**Warnings** — things worth fixing before you forget:

- A reference (`project`, `protocols`, `samples`, `related_experiments`,
  `supersedes`) that points at nothing.
- `project`, `protocols`, or `raw_data_path` still empty.
- A file in `1-notes/`, `3-code/`, `4-data_processed/`, or `5-figures/`
  that doesn't start with the experiment ID.
- An experiment marked `complete` with an empty Results or Interpretation
  section, or no `date_completed`.
- A required body section missing, or a header key that isn't in the
  template (usually a typo).

Run it before lab meeting, before archiving anything, and any time you're
about to hand a folder to someone else.
