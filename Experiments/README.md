# Experiments

In a notebook, `Experiments/` holds one subfolder per experiment. The tools
create each one: **New experiment** on the page, `launchers/New Experiment`, or
`python3 scripts/eln.py new experiment`. Never make one by hand. An older
folder becomes an experiment with **Adopt older folders** (`eln.py adopt`).

```
{ID}_{short-title}/
├── 1-notes/          {ID}.md, plus the protocol copies {ID}_P_{Protocol}_{date}.md that the tool puts in;
│                     after Mark complete: {ID}_snapshot_{date}.html and {ID}_MANIFEST.sha256
├── 2-data_raw/       instrument output, original filenames, never edited
├── 3-code/           {ID}_analysis.R and the like
├── 4-data_processed/ {ID}_quantification.csv and the like
└── 5-figures/        {ID}_R_{what-it-shows}_{YYYYMMDD}.png is the results summary
```

The tool puts a one-paragraph `README.md` in each subfolder that says what
belongs in it. The file also keeps the subfolder from disappearing in git,
which ignores empty folders. `README.md` is exempt from the filename rule
everywhere.

Large raw data (microscopy, sequencing, mass spec) is not kept in
`2-data_raw/`. It stays on institutional storage, and the note's
`raw_data_path` says where. You can also add a line to the `README.md` in
`2-data_raw/` that says where the data is.

This copy of the folder, in the tools folder, is empty. Experiments are
written here only if you use the tools folder itself as your notebook.
Once you have named your notebook folder with `eln.py init --root`, they
go into its `Experiments/` folder; see
[`docs/getting-started.md`](../docs/getting-started.md) §0 and §9. For
filled-in examples, open the fictional notebooks in
[`sandbox/`](../sandbox/README.md) (`launchers/Try the Sandbox`);
`sandbox/alex/Experiments/ALXe0002_*` is the best example.

Rules: [`docs/CONVENTIONS.md`](../docs/CONVENTIONS.md).
