# AI_ELN — System Overview & Specification

*A briefing document, written to be pasted into a fresh conversation with
another AI (or read cold by a person) without any other context from this
repo. Reflects the state of the `claude/lab-eln-markdown-obsidian-gu5hd7`
branch of `shechterlab/ai_eln`.*

---

## 1. The problem this is solving

The Shechter Lab has a site-licensed LabArchives account, but its editing
interface is cumbersome enough that people put off writing things down. At
the same time, one lab member (Jacob Roth, PhD student) independently built
a better information architecture using nothing but a folder-naming
convention and a spreadsheet: every experiment gets a stable ID, a
standardized folder layout, explicit separation of raw vs. processed data,
and a short results summary written while it's still fresh.

Jacob's system already solves the hard part — the information architecture.
What it lacks is a format that's easy to search, link across entities, and
hand to an AI assistant. That gap is what this project fills: translate his
system into Markdown + YAML, keep LabArchives as an archival/compliance
layer instead of the daily tool, and make the result something any AI
coding agent can already work with, with zero custom infrastructure.

A secondary influence, considered and mostly *not* adopted: the Obsidian
community plugin [`fcskit/obsidian-eln`](https://github.com/fcskit/obsidian-eln).
Its structured-note-plus-Dataview-dashboard pattern is a reasonable source
of ideas, but it's built for analytical/materials-science workflows, not
molecular biology, and depends on a fairly large plugin stack. Individual
ideas were borrowed; the vault and taxonomy were not.

## 2. Core design decisions

1. **Markdown + YAML front matter is the canonical record**, not any
   particular editor. Obsidian, a text editor, `grep`, or an AI agent can
   all read and write the same files — nothing is stored in a proprietary
   format or database.
2. **The experiment is the atomic unit.** Every piece of lab work gets one
   Markdown note, one stable ID, one standardized folder.
3. **Large binary data lives outside the vault.** Markdown, small tables,
   and compressed representative images live in the tracked record; raw
   microscopy/sequencing/mass-spec files live on institutional storage,
   referenced by path, not duplicated in.
4. **Where the *whole vault* lives is a lab decision, not a tool decision.**
   The tooling doesn't assume Git, doesn't assume any particular cloud
   provider, and doesn't need to know which one a lab picked — see §4.4.
5. **LabArchives is demoted from working tool to archival layer.** The
   intended flow is one-directional: Markdown → rendered snapshot →
   LabArchives, on completion, never the reverse. Not yet built (see §6).
6. **No single official front end.** Instead, publish a stable contract
   (folder shape, a scriptable CLI, a YAML schema) and let any interface —
   an AI agent, Obsidian, a shell, eventually a custom GUI — be a client of
   that contract. See §4.6.
7. **AI is retrieval-and-citation, never the source of a conclusion.** Every
   scientific claim an AI assistant makes about lab results should cite the
   experiment_id(s) behind it.

## 3. Architecture at a glance

```
Daily work                          At completion
───────────                         ─────────────
Experiment note (MD+YAML)  ────┐
Raw/processed data (storage)   ├──►  Rendered snapshot (PDF/HTML)
Protocols/Samples/Projects(MD) ┘            │
                                             ▼
                                   LabArchives entry (timestamped, audited)
```

Any of these can create/read the Markdown layer:

```
AI agent (Claude Code / Codex CLI / Gemini CLI)  ─┐
Obsidian (+ Templater / Dataview / Shell Commands) ├──►  same files, same
Raw shell / new_experiment.py directly             │     folder, on whatever
A future custom GUI                                ┘     storage the lab picked
```

## 4. Specification

### 4.1 Directory layout

```
<root>/                          # location is configurable, see §4.4
├── Experiments/
│   └── {ID}_{slug-of-title}/
│       ├── 1-notes/             # the Markdown note lives here
│       ├── 2-data_raw/          # untouched instrument output (or a pointer)
│       ├── 3-code/              # analysis scripts
│       ├── 4-data_processed/    # derived/quantified data
│       └── 5-figures/           # exported panels
├── Projects/                    # one .md file per project
├── Protocols/                   # one living .md file per protocol
├── Samples/                     # one .md file per plasmid/oligo/antibody/etc.
├── Inventory/
│   └── experiments.csv          # lab-wide index, machine-generated
├── templates/                   # the 4 schemas below
├── scripts/
│   └── new_experiment.py        # the only way experiments get created
├── AGENTS.md / CLAUDE.md / GEMINI.md   # AI agent contract, see §4.6
└── docs/                        # SOP, getting-started, design rationale
```

### 4.2 Note schemas

All four are Markdown files with a YAML front-matter block followed by a
fixed set of `##` section headers. Placeholders below (`{{X}}`) are what
`new_experiment.py` fills in; the other three templates are copied and
filled in by hand.

**Experiment** (`templates/experiment.md`)
```yaml
---
type: experiment
experiment_id: {{EXPERIMENT_ID}}       # e.g. JSRe0293 — {initials}e{4-digit}
title: {{TITLE}}
researcher: {{RESEARCHER}}
project: [{{PROJECT}}]
date_started: {{DATE}}
date_completed:
status: active            # active | complete | paused | abandoned
experiment_type: [{{EXPERIMENT_TYPE}}]
protocols: [{{PROTOCOL}}]
samples: [{{SAMPLES}}]
notebook_reference: {{NOTEBOOK_REF}}
raw_data_path: {{RAW_DATA_PATH}}
related_experiments: [{{RELATED}}]
tags: []
---
```
Body sections: `Objective`, `Experimental design`, `Methods`,
`Deviations from protocol`, `Results`, `Interpretation`, `Decision`,
`Follow-up experiments`, `Files`.

**Project** (`templates/project.md`)
```yaml
---
type: project
project_id: {{PROJECT_ID}}
title: {{TITLE}}
lead: {{LEAD}}
contributors: []
status: active            # active | complete | paused
date_started: {{DATE}}
grants: []
publications: []
tags: []
---
```
Body sections: `Aim / hypothesis`, `Current state` (with `Supported
conclusions`, `Open questions / conflicting observations`, `Experiments
needing replication` — each conclusion is expected to cite experiment
IDs), `Experiments`, `Reagents in use`, `Figures`, `Related protocols`.

**Protocol** (`templates/protocol.md`)
```yaml
---
type: protocol
protocol_id: P_{{NAME}}_v{{DATE}}
title: {{TITLE}}
status: current           # current | archived
supersedes:
references: []
tags: []
---
```
Body sections: `Purpose`, `Materials`, `Procedure`, `Known failure modes /
troubleshooting`, `Change log`. Convention: edit this file in place as the
protocol improves; when an experiment actually uses it, copy the version
followed into that experiment's `1-notes/`, don't fork this file per use.

**Sample** (`templates/sample.md`) — one schema covers every durable
physical/biological asset (plasmid, oligo, antibody, cell line, mouse
line, peptide, protein prep, slide, gel); `sample_type` distinguishes them.
```yaml
---
type: sample
sample_id: {{SAMPLE_ID}}
sample_type: {{SAMPLE_TYPE}}    # plasmid | oligo | antibody | cell-line | mouse-line | peptide | protein-prep | slide | gel
title: {{TITLE}}
source:
date_created: {{DATE}}
storage_location:
status: active            # active | depleted | retired
used_in_experiments: []
tags: []
---
```
Body sections: `Description`, `Provenance`, `Validation`, `Notes`.

### 4.3 `scripts/new_experiment.py` — CLI reference

Pure standard-library Python 3, no dependencies.

| Flag | Required | Notes |
|---|---|---|
| `--initials` | yes | Researcher initials, e.g. `JSR`. Forms the ID prefix. |
| `--title` | yes | Only other hard requirement. |
| `--researcher` | no | Full name; defaults to initials. |
| `--project` | no | Project ID. |
| `--type` | no | Experiment type, e.g. `WesternBlot`. |
| `--protocol` | no | Protocol ID used. |
| `--samples` | no | Comma-separated sample IDs. |
| `--related` | no | Comma-separated related experiment IDs. |
| `--notebook` | no | Physical notebook page reference, e.g. `NB06-051`. |
| `--root` | no | Data location override — see §4.4. |
| `--dry-run` | no | Print what would happen; create nothing. |

Behavior: reads `Inventory/experiments.csv` under the resolved root, finds
the highest existing number for that `{initials}e` prefix, assigns
`number + 1` (4-digit, zero-padded), slugifies the title for the folder
name, creates the 5-subfolder set, renders `templates/experiment.md` into
`1-notes/{ID}.md`, and appends one row to the inventory CSV.

**Explicitly not implemented:** file locking around ID assignment. Two
people (or a person and an AI agent) creating an experiment with the same
initials in the same instant could theoretically collide. This is treated
as acceptable — a documented convention, not a guaranteed invariant — since
it shouldn't come up in normal single-researcher-per-prefix lab use.

### 4.4 Data root resolution

`new_experiment.py` never assumes it's colocated with the data it writes.
Resolution order:

1. `--root PATH` (per-invocation override)
2. `AI_ELN_ROOT` environment variable (set once per machine/shell)
3. This repository's own location (default — nothing to configure to try
   it out)

This is deliberate: *which* shared storage a lab uses (synced OneDrive,
Dropbox, a shared Obsidian vault, a departmental server mount, or just this
Git repo) is the lab's decision, made once, by whoever runs the lab.
`templates/experiment.md` itself is always read from this repo's own
`templates/` — only the *data* location is redirectable, not the schema.

### 4.5 Inventory CSV schema

`Inventory/experiments.csv`, columns in order:

```
experiment_id, title, researcher, project, experiment_type, protocol,
samples, notebook_reference, date, status, folder
```

Machine-generated (one row appended per `new_experiment.py` call). Direct
descendant of Jacob's original `InventorySheet_jsr.xlsx` `NB-Index` sheet.
Intended as a derived view for filtering/dashboards (a Dataview table, an
Rmd check-in report like Jacob's original one, a future web dashboard) —
not meant to be hand-maintained beyond bookkeeping fields like `status`.

### 4.6 AI agent contract

`AGENTS.md` at the repo root is the canonical, tool-agnostic instructions
file: what this repository is, the directory layout, and seven ground
rules (cite experiment IDs for any factual claim; never fabricate data;
search before answering, using the YAML front matter to filter first;
never hand-create an experiment folder — always call the script; treat
`2-data_raw/` as immutable; match the existing schema rather than inventing
ad hoc fields; ask before bulk edits across many notes).

`CLAUDE.md` (auto-loaded by Claude Code) and `GEMINI.md` (auto-loaded by
Gemini CLI) are a few lines each: "read `AGENTS.md` first," plus notes on
which of that tool's own primitives to use (Claude Code's `Grep`/`Glob`/
`Bash`; Gemini CLI's `search_file_content`/`run_shell_command`). OpenAI's
Codex CLI reads `AGENTS.md` directly, no extra file needed. The intent is
one rules file, not three drifting copies — and if a fourth agent tool
adopts the `AGENTS.md` convention later, it needs no new work here.

No server, API key management, or vector database is involved. Any of
these tools already does its own agentic file search (grep/glob) over
local files; that's judged sufficient at current vault scale (see §7).

## 5. What's actually built vs. not

**Built and tested** (this branch, as of the last push):
- Full directory scaffold, all four templates
- `scripts/new_experiment.py`, including `--root`/`AI_ELN_ROOT` resolution
  (tested against default/env-var/flag paths, including a real write to a
  simulated OneDrive-style folder)
- `Inventory/experiments.csv` generation
- `AGENTS.md` / `CLAUDE.md` / `GEMINI.md`
- Docs: `README.md`, `docs/getting-started.md`, `docs/SOP.md`,
  `docs/design-notes.md`, `docs/ai-agents.md`
- Jacob's original spreadsheet/Rmd/slide deck preserved under
  `reference/jacob-original-system/` for provenance
- One worked example experiment (`Experiments/DSLe0001_.../`) showing
  exactly what the script produces, unedited

**Not built yet** (discussed, not implemented):
- The LabArchives archival bridge (needs institutional API access granted
  first; would use the NIMH-supported `labapi` Python client)
- Any semantic-search/embeddings layer
- Project-synthesis automation (an AI-maintained "current state" rollup)
- Instrument/data ingestion scripts (checksumming, auto-renaming, manifest
  generation)
- A GUI/web front end (discussed conceptually: a folder-generation form +
  a note viewer that resolves `raw_data_path` to clickable/openable links;
  concluded that OneDrive/Dropbox need no API integration since they're
  just locally-synced folders on disk)
- A lab-wide multi-user dashboard when individual researchers' data lives
  in separate personal cloud accounts rather than one shared root
  (unsolved — see open questions)

## 6. Staged rollout plan (as discussed, not started)

1. **Pilot** — 2–3 people, one project, ~20 experiments, using what's built now.
2. **Lab standardization** — SOP training, wider rollout.
3. **LabArchives bridge** — automated archival snapshots on `status: complete`.
4. **AI layer** — semantic search, project synthesis, ingestion — deliberately
   last, since AI can't fix inconsistent IDs or missing metadata, only
   compound them.

## 7. Open questions worth exploring further

These are the genuinely unresolved design questions — good material for
further conceptual exploration:

- **ID scheme longevity.** Per-researcher-initials + sequential number
  (`JSRe0293`) is human-friendly and matches Jacob's existing system, but
  is unlocked/uncoordinated. Is that the right long-term scheme, or should
  IDs be closer to UUID/timestamp-based (machine-safe) with initials
  demoted to a metadata field? What actually breaks first at lab scale?
- **Multi-user aggregation.** If each researcher's `--root` points at their
  own personal OneDrive/Dropbox, there's no single filesystem a dashboard
  or an AI agent can scan for a lab-wide view. Does this require a shared
  institutional root (SharePoint/server) as a hard requirement, or can a
  periodic merge step reconcile N personal `experiments.csv` files into
  one index without that?
- **Provenance/manifest depth.** A per-experiment manifest (raw file →
  processed file → figure, with checksums) was proposed but not built.
  What's the minimum version that's worth the added friction of
  maintaining it by hand, before it's worth automating?
- **Where the line is between "convention" and "enforcement."** Several
  things are currently pure convention (schema fields, folder shape, no ID
  locking). At what point, if ever, does it become worth adding a linter/
  pre-commit hook that actually validates front matter against the
  templates, versus trusting the AGENTS.md-documented discipline?
- **Retrieval ceiling.** Grep/glob-based agent search is judged sufficient
  for "dozens to low hundreds" of notes. What's the actual failure mode
  when a vault outgrows that — missed matches, slow responses, both — and
  is there a middle step before a full embeddings index (e.g., a
  precomputed tag/keyword index) worth building first?
- **GUI front end, if built.** Given OneDrive/Dropbox don't need API
  integration (they're just synced local folders), is a GUI's main value
  the *creation* form (a nicer wrapper on the same CLI) or the *viewing*
  experience (rendered notes + resolved data links)? Are these worth
  building as one app or two separate, smaller tools?
- **LabArchives bridge shape.** One-directional Markdown → LabArchives
  snapshot was the design decision (to avoid dual-authority ambiguity).
  Is a PDF/HTML render-and-upload sufficient for what LabArchives is
  actually being kept around for (audit trail, institutional compliance),
  or does the institution's definition of an adequate record require more
  structure than a flattened snapshot preserves?

---
*Source repository: `shechterlab/ai_eln`, branch
`claude/lab-eln-markdown-obsidian-gu5hd7`.*
