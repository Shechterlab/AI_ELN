# AI_ELN cheat sheet

Each experiment has an ID, a folder named with that ID, and one note in that
folder. **New experiment** makes them; never make the folder by hand.

## Start

Chrome or Edge: **shechterlab.github.io/AI_ELN/app** → **Open notebook folder**. Safari or Firefox: double-click **`launchers/Open ELN`**.
Then **New experiment** → title → **Create**.
Write with **Edit here**. To practise first: **Open the practice notebook** on the page, or **`launchers/Try the Sandbox`**.

## IDs

| | pattern | example |
|---|---|---|
| Experiment | `INITIALS` + `e` + 4 digits | `JSRe0002` |
| Sample | `INITIALS` + letter + 4 digits | `JSRp0001` |
| Protocol | `P_` + Name | `P_WesternBlot` |
| Project | Name | `PRMT5-ChromatinRelease` |
| Figure | `INITIALS` + `f` + 4 digits | `JSRf0001` |

Sample letters: **p** plasmid · **i** oligo · **a** antibody · **c** cell line ·
**m** mouse line · **t** peptide · **r** protein prep · **s** slide · **g** gel

Use three initials (first, middle, last). An ID written in a note is shown
as a link. A number is never used again. An ID with someone else's initials
is a record in that person's notebook.

## The folder

```
Experiments/JSRe0002_short-title/
  1-notes/           JSRe0002.md  (+ JSRe0002_P_Protocol_date.md, copied for you)
  2-data_raw/        instrument output: original names, never edited
  3-code/            JSRe0002_analysis.R
  4-data_processed/  JSRe0002_quantification.csv
  5-figures/         JSRe0002_R_what-it-shows_20260904.png   (R = the results figure)
```

A figure for a paper, a grant or a talk gets its own record, whatever program
it is made in. The note lists which experiment each panel came from.

```
Figures/JSRf0001_short-title/
  1-notes/    JSRf0001.md  (Panels table, legend, versions)
  2-panels/   JSRf0001_a_blot.pdf, one file per panel
  3-source/   JSRf0001_layout.ai  (or .cvx, .pzfx, .pptx, .R, .py)
  4-exports/  JSRf0001_v1_20260915.pdf, one file per version sent out
```

Each person has one notebook folder. `notebook.md` at its top says whose it
is and remembers the last IDs. **Adopt older folders** makes an experiment
from an older folder and moves it into `2-data_raw/` unchanged.

## Filenames

`ID` `_` `[R|P]` `_` `words-with-hyphens` `_` `[YYYYMMDD]` `.ext`

- Fields separated by `_`, words inside a field by `-`.
- `R` = results summary (the one you show in lab meeting). `P` = protocol as run.
- Everything in `2-data_raw/` keeps its instrument name. Everything else starts with the ID.

## The header (top of every note)

```yaml
status: active            # active | complete | paused | abandoned
project: [PRMT5-ChromatinRelease]
protocols: [P_WesternBlot]
samples: [JSRp0001, JSRa0003]
tags: [meeting]           # flag for the next lab meeting
date_completed: 2026-09-12
```

One `key: value` per line. Lists in `[square, brackets]`. Dates `YYYY-MM-DD`.

## Sections (keep all of them, in this order)

Objective · Experimental design · Methods · Deviations from protocol ·
Results · Interpretation · Decision · Follow-up experiments · Files

## Buttons on the page (and the matching double-clicks in `launchers/`)

**New experiment** · **New sample** · **New protocol** · **New project** · **New figure** ·
**Check** · **Meeting brief** · **Export** (one file for ChatGPT, or a folder of plain files) · **Adopt older folders** ·
on a note: **Edit here** · **Add files** · **Repeat this experiment** · **Print / save as PDF** · **Mark complete** · **Verify files**

Adopt, Add files, Repeat, Print, and the folder export are in the Chrome or
Edge page only. From a terminal: `python3 scripts/eln.py new experiment
--title "..."`, `validate`, `find`, `report`, `export`, `adopt`, `complete`,
`verify`, `index`, `init`; `python3 scripts/eln_web.py` for the launcher page.

## When you finish

Write Results and Interpretation, point `raw_data_path` at backed-up
storage, then click **Mark complete** on the note's page. It sets the status
and date and writes `{ID}_snapshot_{date}.html` (prints to PDF) and
`{ID}_MANIFEST.sha256` (for each file, a number computed from its content;
**Verify files** uses them to show later changes).

## With AI

Codex / Claude Code / Cowork: open it in the tools folder, which has the
rules. It works on the notebook named with `eln.py init --root`.
ChatGPT: **Export**, paste, ask. Every claim it makes should cite an ID.

Example questions: *do the numbers in JSRe0007's Results match its data file?* ·
*write that Results sentence in the standard format with effect size* ·
*check my `_R_` figure against the figure checklist* ·
*what would falsify this Interpretation?* Full list: **Ask the AI** on the page.

## Leaving, or sending to another ELN

The notebook is plain files; to take all of it, copy the folder. **Export →
Save as a folder of plain files** copies part of it, with a README and an
index. **Export → For another electronic notebook** makes a `.eln` archive: a
ZIP file in a standard format that eLabFTW, RSpace, Kadi4Mat, PASTA,
SampleDB, OpenSemanticLab, and SciLog import.
