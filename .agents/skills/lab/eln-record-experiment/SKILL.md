---
name: eln-record-experiment
description: Create or fill in an experiment record in the lab's Markdown research record (AI_ELN). Use whenever someone wants to start, log, write up, update, or close out an experiment - "new experiment", "record this", "write up my results", "mark it complete", "add a sample/protocol/project", "make a record of this old folder". Records are always created through scripts/eln.py, never by hand.
---

# Recording an experiment

The lab's research record is a notebook: one folder per person, holding
plain Markdown files. Each file starts with a short header of `key: value`
lines. The rules are in `docs/CONVENTIONS.md`. This skill is the short
version for doing the work.

## 1. Creating a record

Never create an experiment folder or note by hand. Run the tool. It assigns
the ID, makes the five subfolders, fills in the header, copies the protocol
as run, and updates the index:

```bash
python3 scripts/eln.py new experiment --title "..." [--project ID] [--type WesternBlot] \
    [--protocol P_Name] [--samples ID,ID] [--notebook NB02-153] [--tags meeting]
python3 scripts/eln.py new sample   --type plasmid --title "..." [--source "..."] [--storage "..."]
python3 scripts/eln.py new protocol --name WesternBlot
python3 scripts/eln.py new project  --id PRMT5-ChromatinRelease --title "..."
python3 scripts/eln.py adopt ["/path/to/old folder"]
```

- The title is the only thing you must have. Ask for it if it is missing;
  everything else can be added to the header later.
- Before passing `--project`, `--protocol`, or `--samples`, check that they
  exist (`eln.py find --kind project`, `--kind protocol`, `--kind sample`).
  The tool does not check. If a protocol does not exist yet, offer to
  create it first, so that its copy is put next to the note.
- A sample or experiment ID with someone else's initials (`ALXc0001` in a
  notebook of `JOR`) is a record in that person's notebook. Pass it as it
  is. Do not create it here.
- New records get the initials of the notebook's owner, named in
  `notebook.md`; `--initials` overrides that. If the tool says "No
  initials", ask the person for their initials, name, and notebook folder,
  then run
  `eln.py init --initials XXX --researcher "Full Name" --root "/path/to/notebook"`.
- The commands work on the notebook named with `eln.py init --root`, or
  with `AI_ELN_ROOT`, or with `--root` on one command. That folder is
  normally not the tools folder; find out which it is before assuming a
  path. The practice notebooks are `--root sandbox/alex` and
  `--root sandbox/jordan`.
- `eln.py adopt "PATH"` makes an experiment record from an older folder:
  the experiment gets the next ID and the folder is moved unchanged into
  its `2-data_raw/`. With no path, it lists the folders in the notebook
  that are not records yet. The title and dates are read from the folder
  name and the file dates; tell the person to correct them if needed.
  Results and Interpretation say "Not written" until someone writes them.

## 2. Filling in the note

The note is `Experiments/{ID}_{short-title}/1-notes/{ID}.md` in the
notebook folder. Keep every `##` section, in order, even if it only says
"None". Write what the person tells you into the right section:

| Section | What goes there |
|---|---|
| Objective | The question, in one or two sentences |
| Experimental design | Conditions, groups, replicates, controls |
| Methods | Only what is *not* in the protocol copy next to the note |
| Deviations from protocol | What was done differently on the day |
| Results | What happened: observations, numbers, links to figures. Not what it means. |
| Interpretation | What it means. Does it support, contradict, or refine the hypothesis? |
| Decision | What happens next because of this |
| Follow-up experiments | Checklist |

**Never write a result, number, or figure that the person did not give you.**
If a section has no content yet, leave the template hint in place.

## 3. Files the person adds

Tell them (or do it for them) to name files inside the experiment folder
starting with the experiment ID, words joined by hyphens:

```
{ID}_R_short-description_YYYYMMDD.png     the one results figure for lab meeting  ->  5-figures/
{ID}_quantification.csv                    ->  4-data_processed/
{ID}_analysis.R                            ->  3-code/
```

`2-data_raw/` is the exception: instrument output keeps its original name
and is never edited. If raw data is kept somewhere else, set `raw_data_path`
in the header to that location.

## 4. Closing out

When asked to mark an experiment complete, run the command. Do not edit
the header by hand:

```bash
python3 scripts/eln.py complete JSRe0002 [--date YYYY-MM-DD]
```

It refuses if Results or Interpretation is still empty. Tell the person
what is missing; do not use `--force`. Otherwise it sets `status: complete`
and `date_completed`, and writes two files:

- `1-notes/{ID}_snapshot_{date}.html`, a snapshot: one HTML file with the
  whole experiment, images included, for printing to PDF.
- `1-notes/{ID}_MANIFEST.sha256`, a list of checksums. A checksum is a
  number computed from a file's content; `eln.py verify ID` uses the list
  later to show which files changed.

It then updates the index. It warns if `raw_data_path` cannot be found
from this computer; pass that warning on to the person.

`paused` and `abandoned` are set by editing the header. Add one sentence
in Decision saying why.

## 5. Lab meeting

`tags: [meeting]` in the header flags the experiment for the next meeting.
`python3 scripts/eln.py report` builds the brief from those flags.

## Don'ts

- Don't rename, move, or "clean up" anything under `2-data_raw/`.
- Don't add header keys that aren't in `templates/experiment.md`; propose a
  template change instead.
- Don't rewrite many notes at once without confirming with the person first.
- Don't cite or edit anything in `Exports/`. Those folders are copies
  written by Export.
