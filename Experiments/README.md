# Experiments

One subfolder per experiment, created by `launchers/New Experiment` or
`python3 scripts/eln.py new experiment`, never by hand.

```
{ID}_{slug-of-title}/
├── 1-notes/          {ID}.md, plus {ID}_P_{Protocol}_{date}.md snapshots the tool copies in
├── 2-data_raw/       untouched instrument output, original filenames, never edited
├── 3-code/           {ID}_analysis.R and the like
├── 4-data_processed/ {ID}_quantification.csv and the like
└── 5-figures/        {ID}_R_{what-it-shows}_{YYYYMMDD}.png is the results summary
```

`DSLe0001_SNRPB-chromatin-retention-after-PRMT5-inhibition/` is a worked
example: exactly what the tool produces, unedited apart from one sentence
in Objective saying so. It is not real data.

Large raw data (microscopy, sequencing, mass spec) does not live in
`2-data_raw/` here; it stays on institutional storage and the note's
`raw_data_path` says where. A short `README.md` in `2-data_raw/` pointing
there is welcome.

This folder may live somewhere other than inside this repo; see
`--root` / `init` in [`docs/getting-started.md`](../docs/getting-started.md) §8.
Rules: [`docs/CONVENTIONS.md`](../docs/CONVENTIONS.md).
