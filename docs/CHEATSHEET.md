# AI_ELN cheat sheet

**One experiment = one ID = one folder = one note.** Never make the folder by hand.

## Start

Double-click **`launchers/Open ELN`** → a page opens in your browser → **New experiment** → title → **Create**.
Write with **Edit here**. Practice first on **`launchers/Try the Sandbox`**.

## IDs

| | pattern | example |
|---|---|---|
| Experiment | `INITIALS` + `e` + 4 digits | `JSRe0002` |
| Sample | `INITIALS` + letter + 4 digits | `JSRp0001` |
| Protocol | `P_` + Name | `P_WesternBlot` |
| Project | Name | `PRMT5-ChromatinRelease` |

Sample letters: **p** plasmid · **i** oligo · **a** antibody · **c** cell line ·
**m** mouse line · **t** peptide · **r** protein prep · **s** slide · **g** gel

Write an ID anywhere and it's a link. Never reuse a number.

## The folder

```
Experiments/JSRe0002_short-title/
  1-notes/           JSRe0002.md  (+ JSRe0002_P_Protocol_date.md, copied for you)
  2-data_raw/        instrument output: original names, never edited
  3-code/            JSRe0002_analysis.R
  4-data_processed/  JSRe0002_quantification.csv
  5-figures/         JSRe0002_R_what-it-shows_20260904.png   (R = the results figure)
```

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

**New experiment** · **New sample** · **New protocol** · **New project** ·
**Check** · **Meeting brief** · **Export** for ChatGPT

Same from a terminal: `python3 scripts/eln.py new experiment --title "..."`,
`validate`, `find`, `report`, `export`, `index`, `init`; `python3 scripts/eln_web.py` for the page.

## When you finish

`status: complete`, `date_completed:`, Results and Interpretation written,
`raw_data_path` points at backed-up storage. Then **Check**.

## With AI

Codex / Claude Code / Cowork: open it in this folder; it already knows the rules.
ChatGPT: **Export**, paste, ask. Every claim it makes should cite an ID.
