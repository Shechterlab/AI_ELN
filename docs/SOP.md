# Shechter Lab Data Management SOP

**Scope:** how experiments, protocols, samples, and data are recorded and
stored in the lab, day to day. Two pages, on purpose — the full rationale
is in [`design-notes.md`](design-notes.md), not here.

## 1. When to create an experiment ID

Create one (`scripts/new_experiment.py`) as soon as you start planning a
distinct piece of experimental work — before you generate data, not after.
"Distinct" means: if you'd file it under a different section in a paper or
explain it as a separate thing in lab meeting, it's a separate experiment ID.

## 2. Minimum required metadata

Every experiment note must eventually have, in its YAML front matter:

- `experiment_id`, `researcher`, `date_started`, `status`
- `title` — specific enough to identify the experiment out of context
- `project` — which project(s) this supports
- `protocols` — which protocol version was actually followed

And in the body: **Objective**, **Results**, **Interpretation**, **Status**
(via the `status` field). Everything else in the template
(`Deviations`, `Follow-up experiments`, etc.) is filled in as relevant —
leave a section as `None` or blank rather than deleting it, so notes stay
comparable across the lab.

## 3. Canonical folder structure

Every experiment gets the same five subfolders, created automatically:
`1-notes`, `2-data_raw`, `3-code`, `4-data_processed`, `5-figures`. Don't
rename or reorganize them per-experiment — the value of the system is that
every experiment looks the same.

## 4. Raw vs. processed data

- **Raw** = untouched instrument/acquisition output. Never edited in place.
- **Processed** = anything derived from raw data by a script or manual step
  (quantification tables, cropped images, normalized values).

If you can't answer "what raw file did this come from," it isn't
processed data yet — it's an orphan.

## 5. Filenames

Prefix files that belong to an experiment with that experiment's ID
(`DSLe0123_...`). Give recurring physical objects (gels, blots, plasmids,
oligos, slides) their own stable ID (see [`Samples/README.md`](../Samples/README.md))
and reuse it in every filename and every experiment note that touches it.

## 6. Where data physically lives

- Markdown notes, small tables, protocol PDFs, compressed representative
  images → this repo.
- Everything else (microscopy datasets, sequencing files, mass spec, raw
  Western scans, GraphPad/Illustrator source files) → institutionally
  backed-up storage (OneDrive/SharePoint or departmental server). The
  experiment note records the path; the file itself does not live in the
  vault or in Git.

Never: a personal laptop desktop, an un-backed-up external drive, or "I'll
move it later."

## 7. Completion and archival

When an experiment is marked `status: complete`:

1. Confirm `raw_data_path` points to a real, backed-up location.
2. Fill in Results, Interpretation, and Decision.
3. (Once the LabArchives bridge exists — see `design-notes.md`) the note
   gets archived as a timestamped snapshot in LabArchives under the same
   experiment ID.

Archival is a snapshot of the record, not the working copy — keep working
in Markdown afterward if you revisit the experiment.

## 8. Ownership and offboarding

Before a trainee leaves the lab:

- All their experiment notes are `status: complete` or `status: paused`
  with an honest note explaining what's unfinished.
- Every `raw_data_path` in their experiments resolves to lab-accessible
  storage, not a personal account.
- Their active projects have a current-state summary another lab member
  could read cold.

## 9. What's flexible

Daily notes, prose style, how many images you embed, what tool you analyze
data in (R, Python, Prism — doesn't matter), and personal task management
are all up to you. The SOP standardizes the interface between experiments,
not how any one person thinks.
