# Experiments

One subfolder per experiment, created by `scripts/new_experiment.py` — never by hand.
(This folder may just be a local, in-repo example — a real lab deployment can
point the script at shared storage instead; see `--root`/`AI_ELN_ROOT` in
[`docs/getting-started.md`](../docs/getting-started.md#0-where-does-your-data-actually-live).)

```
{ID}_{slug-of-title}/
├── 1-notes/          the experiment .md note lives here
├── 2-data_raw/       untouched instrument/acquisition output
├── 3-code/           analysis scripts
├── 4-data_processed/ derived data (quantification tables, etc.)
└── 5-figures/        exported panels
```

`DSLe0001_SNRPB-chromatin-retention-after-PRMT5-inhibition/` is a worked
example — it's exactly what running the command in
[`docs/getting-started.md`](../docs/getting-started.md) produces. Open its
note to see the shape; it's intentionally still blank so it doesn't get
mistaken for real data.

Large raw data (microscopy, sequencing, mass spec) should not actually live
in `2-data_raw/` inside this repo — see
[`docs/design-notes.md`](../docs/design-notes.md#data-lives-outside-the-notebook)
for where it belongs instead. `2-data_raw/` can hold a pointer file if the
data lives elsewhere.
