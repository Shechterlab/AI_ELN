---
name: eln-record-experiment
description: Create or fill in an experiment record in the lab's Markdown research record (AI_ELN). Use whenever someone wants to start, log, write up, update, or close out an experiment - "new experiment", "record this", "write up my results", "mark it complete", "add a sample/protocol/project". Records are always created through scripts/eln.py, never by hand.
---

# Recording an experiment

The lab's research record is a folder of plain Markdown files with a small
YAML header each. The rules are in `docs/CONVENTIONS.md`; this skill is the
short version for doing the work.

## 1. Creating a record

Never create an experiment folder or note by hand. Run the tool - it
assigns the ID, builds the five subfolders, fills the header, snapshots the
protocol, and re-indexes:

```bash
python3 scripts/eln.py new experiment --title "..." [--project ID] [--type WesternBlot] \
    [--protocol P_Name] [--samples ID,ID] [--notebook NB02-153] [--tags meeting]
python3 scripts/eln.py new sample   --type plasmid --title "..." [--source "..."] [--storage "..."]
python3 scripts/eln.py new protocol --name WesternBlot
python3 scripts/eln.py new project  --id PRMT5-ChromatinRelease --title "..."
```

- The title is the only thing you must have. Ask for it if it's missing;
  everything else can be added to the header later.
- Before passing `--project`, `--protocol`, or `--samples`, check they exist
  (`eln.py find --kind project`, `--kind protocol`, `--kind sample`). If a
  protocol doesn't exist yet, offer to create it first so the snapshot gets
  copied.
- If the person has no config yet, the tool will say "No initials" - run
  `eln.py init --initials XXX --researcher "Full Name"` with their details.
- If files live somewhere other than this repo, `AI_ELN_ROOT` is set or
  `--root` is needed; check the environment before assuming paths.

## 2. Filling in the note

The note is `Experiments/{ID}_{slug}/1-notes/{ID}.md`. Keep every `##`
section, in order, even if it just says "None". Write what the person tells
you into the right section:

| Section | What goes there |
|---|---|
| Objective | The question, in one or two sentences |
| Experimental design | Conditions, groups, replicates, controls |
| Methods | Only what is *not* in the snapshotted protocol |
| Deviations from protocol | What was done differently on the day |
| Results | What happened - observations, numbers, links to figures. Not what it means. |
| Interpretation | What it means. Supports / contradicts / refines the hypothesis? |
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
and is never edited. If raw data lives elsewhere, set `raw_data_path` in the
header to that location.

## 4. Closing out

When asked to mark an experiment complete:

1. Confirm Results and Interpretation are written (not just the template hint).
2. Set `status: complete` and `date_completed: YYYY-MM-DD` in the header.
3. Confirm `raw_data_path` points at a real, backed-up location.
4. Run `python3 scripts/eln.py validate` and fix anything it reports for this note.

`paused` and `abandoned` are also valid; add one honest sentence in
Decision saying why.

## 5. Lab meeting

`tags: [meeting]` in the header flags the experiment for the next meeting.
`python3 scripts/eln.py report` builds the brief from those flags.

## Don'ts

- Don't rename, move, or "clean up" anything under `2-data_raw/`.
- Don't add header keys that aren't in `templates/experiment.md`; propose a
  template change instead.
- Don't rewrite many notes at once without confirming with the person first.
