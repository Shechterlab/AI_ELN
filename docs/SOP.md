# Shechter Lab Data Management SOP

**Scope:** how experiments, protocols, samples, and data are recorded and
stored in the lab, day to day. The precise rules are
in [`CONVENTIONS.md`](CONVENTIONS.md); the reasoning is in
[`design-notes.md`](design-notes.md).

## 1. When to create an experiment ID

Create one as soon as you start planning a distinct piece of experimental
work, before you generate data: **New experiment** on the notebook page,
`launchers/New Experiment`, or `python3 scripts/eln.py new experiment`.
Work is distinct if you would put it in a different section of a paper or
present it as a separate item in lab meeting.

Never create an experiment folder by hand and never reuse an ID. The tool
assigns the next number for your initials and updates the index in
`Inventory/`. A folder made before the notebook existed becomes an
experiment with **Adopt older folders** (`eln.py adopt`).

## 2. Minimum required metadata

In the header (the `key: value` lines at the top of the note), from day
one: `experiment_id`, `title` (specific enough to identify it out of
context), `researcher`, `date_started`, `status`.

By the time it is complete: `project`, `protocols` (which protocol was
followed; the tool copies the protocol file into the experiment for you),
`raw_data_path`, and `date_completed`.

In the body: **Objective** before you start; **Results**, **Interpretation**,
and **Decision** when you have them. Keep every section heading even if the
section only says "None", so that notes can be compared across the lab.

## 3. Canonical folder structure

Every experiment gets the same five subfolders, created by the tool:
`1-notes`, `2-data_raw`, `3-code`, `4-data_processed`, `5-figures`. Do not
rename them, reorder them, or add others. The note, the raw data, and the
figures of every experiment are then in the same place, and Check reports
a missing subfolder as an error.

## 4. Raw vs. processed data

- **Raw** is instrument or acquisition output as the instrument wrote it.
  It is never edited and never renamed. `2-data_raw/` is the only folder
  where filenames do not start with the experiment ID, because the
  instrument named them.
- **Processed** is anything derived from raw by a script or a manual step
  (quantification tables, cropped images, normalized values).

For every processed file, the note or the script should say which raw file
it came from.

## 5. Filenames

Every file you make inside an experiment folder starts with that
experiment's ID. Words are joined with hyphens. The results summary gets
`_R_` after the ID (`JSRe0002_R_fractionation-KCl_20260904.png`).
Physical things that are kept and used again (gels, plasmids, oligos,
antibodies, cell lines) get their own sample ID (`JSRg0012`, `JSRp0003`).
Write that ID in every note and filename that refers to the thing. Grammar
and examples: [`CONVENTIONS.md`](CONVENTIONS.md) §3.

## 6. Where data physically lives

- Each person has one notebook folder of their own, kept where that person
  keeps their work, usually inside Dropbox or OneDrive so that it is backed
  up. There is no shared lab notebook folder and no server. Markdown notes,
  small tables, protocol copies, and compressed representative images go in
  the notebook folder.
- Everything large (microscopy datasets, sequencing, mass spec, raw
  Western scans, Illustrator/Prism source files) goes on institutionally
  backed-up storage (OneDrive/SharePoint or a departmental server). The
  note's `raw_data_path` records where; the file itself stays there.

Do not leave data on a laptop's desktop or on an external drive that is
not backed up, even for a short time.

## 7. Checking your work

**Check everything** on the page, `launchers/Check Everything`, or
`eln.py validate` lists what breaks the conventions: misnamed folders,
missing subfolders, `status` values that are not allowed, IDs that match no
record, files without the ID in front, and complete experiments with empty
Results. An experiment or sample ID with someone else's initials is a
record in that person's notebook and is not reported as missing. Run Check
before lab meeting, before marking anything complete, and before giving a
folder to anyone. An `ERROR` must be fixed; a `WARN` is advice.

## 8. Completion and archival

When an experiment is finished, click **Mark complete** on its page (or
run `eln.py complete ID`). That:

1. Refuses if Results or Interpretation is still empty, and warns if
   `raw_data_path` cannot be found from your computer.
2. Sets `status: complete` and `date_completed`.
3. Writes `1-notes/{ID}_snapshot_{date}.html`: the note with its figures
   as one file that opens in any browser and prints to PDF. This file is
   the snapshot, and it is what goes to LabArchives.
4. Writes `1-notes/{ID}_MANIFEST.sha256`, the manifest: a checksum of every
   file in the experiment folder, in the standard `sha256sum` format. A
   checksum is a number computed from a file's content, so a file that has
   changed gives a different number. **Verify files** (or `eln.py verify
   ID`) later shows anything that changed. Without the tools, run
   `sha256sum -c 1-notes/{ID}_MANIFEST.sha256` from inside the experiment
   folder (on a Mac, `shasum -a 256 -c ...`).

Nothing is locked. If you return to the experiment, edit the note, then
click **Refresh snapshot & manifest**. For LabArchives, upload the snapshot
(or its PDF) under the experiment ID. The upload is done by hand; there is
no automatic upload yet. To move a project to another electronic notebook
(eLabFTW, RSpace, Kadi4Mat, and others), use **Export** and save the `.eln`
archive (in the browser page it is under **For another electronic
notebook**). To give a project to a collaborator as ordinary files, use
**Export**, then **Save as a folder of plain files** in the browser page,
or `eln.py export --format folder`.

## 9. Ownership and offboarding

Each notebook folder belongs to one person, named in its `notebook.md`.
Before a trainee leaves the lab:

- Every experiment is `complete`, `paused`, or `abandoned`. Anything
  unfinished has one sentence in Decision saying why it was not finished.
- Every `raw_data_path` points at storage the lab can reach. None points at
  a personal account.
- Each of their active projects has a current-state summary that another
  lab member can follow without having done the work (`launchers/New
  Project` if the project page does not exist; the AI skill
  `eln-project-synthesis` can draft it from the experiments).
- **Check everything** lists no problems.
- Their notebook folder is copied, whole, to lab storage that the PI
  controls. There is no server and no central copy, so this copy is the
  lab's record of their work. An ID with their initials in someone else's
  note refers to a record in it. Check that the copy opens with **View a
  notebook (read-only)**.

## 10. What's flexible

Daily notes, prose style, how many images you embed, which analysis tool
you use (R, Python, Prism, or another), and personal task management are
yours to decide. The SOP fixes only what other people and the tools depend
on: the IDs, the folder layout, the filenames, and the header fields and
section names of a note.
