# Shechter Lab Data Management SOP

**Scope:** how experiments, protocols, samples, and data are recorded and
stored in the lab, day to day. Two pages, on purpose. The precise rules are
in [`CONVENTIONS.md`](CONVENTIONS.md); the reasoning is in
[`design-notes.md`](design-notes.md).

## 1. When to create an experiment ID

Create one (`launchers/New Experiment`, or `python3 scripts/eln.py new
experiment`) as soon as you start planning a distinct piece of
experimental work, before you generate data. "Distinct" means: if you'd
file it under a different section in a paper or explain it as a separate
thing in lab meeting, it's a separate experiment ID.

Never create an experiment folder by hand and never reuse an ID. The tool
assigns the next number for your initials and re-indexes the inventory.

## 2. Minimum required metadata

In the header, from day one: `experiment_id`, `title` (specific enough to
identify it out of context), `researcher`, `date_started`, `status`.

By the time it's complete: `project`, `protocols` (which protocol was
followed; the tool snapshots the file for you), `raw_data_path`, and
`date_completed`.

In the body: **Objective** before you start; **Results**, **Interpretation**,
and **Decision** when you have them. Keep every section header even if the
section just says "None", so notes stay comparable across the lab.

## 3. Canonical folder structure

Every experiment gets the same five subfolders, created automatically:
`1-notes`, `2-data_raw`, `3-code`, `4-data_processed`, `5-figures`. Don't
rename, reorder, or add to them per experiment. The value of the system is
that every experiment looks the same.

## 4. Raw vs. processed data

- **Raw** = untouched instrument/acquisition output. Never edited, never
  renamed. `2-data_raw/` is the only folder where filenames don't start
  with the experiment ID, precisely because the instrument named them.
- **Processed** = anything derived from raw by a script or a manual step
  (quantification tables, cropped images, normalized values).

If you can't answer "what raw file did this come from," it isn't
processed data yet; it's an orphan.

## 5. Filenames

Every file you make inside an experiment folder starts with that
experiment's ID; words are joined with hyphens; the results summary gets
`_R_` after the ID (`JSRe0002_R_fractionation-KCl_20260904.png`).
Recurring physical things (gels, plasmids, oligos, antibodies, cell lines)
get their own sample ID (`JSRg0012`, `JSRp0003`) and that ID is reused in
every filename and every note that touches them. Grammar and examples:
[`CONVENTIONS.md`](CONVENTIONS.md) §3.

## 6. Where data physically lives

- Markdown notes, small tables, protocol snapshots, compressed
  representative images → the record folder.
- Everything large (microscopy datasets, sequencing, mass spec, raw
  Western scans, Illustrator/Prism source files) → institutionally
  backed-up storage (OneDrive/SharePoint or a departmental server). The
  note's `raw_data_path` records where; the file itself stays there.

Never: a personal laptop desktop, an un-backed-up external drive, or
"I'll move it later."

## 7. Checking your work

`launchers/Check Everything` (`eln.py validate`) reports every convention
that's broken: misnamed folders, missing subfolders, bad `status` values,
IDs that point at nothing, files without the ID prefix, complete
experiments with empty Results. Run it before lab meeting, before marking
anything complete, and before handing a folder to anyone. `ERROR` must be
fixed; `WARN` is advice.

## 8. Completion and archival

When an experiment is marked `status: complete`:

1. `date_completed` is set; Results, Interpretation, and Decision are written.
2. `raw_data_path` points to a real, backed-up location.
3. **Check Everything** reports no errors for the note.
4. (Once the LabArchives bridge exists; see `design-notes.md`) the note is
   deposited as a timestamped snapshot in LabArchives under the same ID.

Archival is a snapshot of the record, not the working copy. Keep working
in the note afterward if you revisit the experiment.

## 9. Ownership and offboarding

Before a trainee leaves the lab:

- Every experiment is `complete`, `paused`, or `abandoned`, with one honest
  sentence in Decision for anything unfinished.
- Every `raw_data_path` resolves to lab-accessible storage, not a personal
  account.
- Their active projects have a current-state summary another lab member
  could read cold (`launchers/New Project` if it doesn't exist; the AI
  skill `eln-project-synthesis` can draft it from the experiments).
- **Check Everything** is clean.

## 10. What's flexible

Daily notes, prose style, how many images you embed, which analysis tool
you use (R, Python, Prism, whatever), and personal task management are all
yours. The SOP standardizes the interface between experiments, not how any
one person thinks.
