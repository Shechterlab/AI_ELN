# Getting started

No Obsidian, no plugins, no account required to try this. All you need is a
text editor and Python 3 (already on your Mac/lab computer).

## 1. Create your first experiment (one command)

```bash
python3 scripts/new_experiment.py \
  --initials ABC \
  --researcher "Your Name" \
  --title "Whatever you're doing today"
```

That's the only required information. Everything else — project, protocol,
notebook reference, samples — is optional and can be added later, either as
flags or by editing the note directly:

```bash
python3 scripts/new_experiment.py \
  --initials ABC \
  --researcher "Your Name" \
  --project PRMT5-ChromatinRelease \
  --type WesternBlot \
  --title "SNRPB chromatin retention after PRMT5 inhibition" \
  --protocol P_WesternBlot_v2026-07-16 \
  --notebook NB01-001
```

Run it with `--dry-run` first if you just want to see what it would do.

This gives you:

- a new experiment ID (`ABCe0001`, incrementing automatically per researcher)
- a standard folder: `Experiments/ABCe0001_.../{1-notes,2-data_raw,3-code,4-data_processed,5-figures}`
- a Markdown note in `1-notes/` with the metadata already filled in
- a new row in `Inventory/experiments.csv`

Open the note, fill in the **Objective**, and go run your experiment.
Everything else in the note can wait until you have something to write.

## 2. Write in it like a notebook, not a form

The note is plain Markdown. Write in whatever style you naturally would.
The only parts that matter for search and AI later are:

- the YAML block at the top (already filled in for you)
- the section headers (`## Results`, `## Interpretation`, etc. — keep them
  so notes stay comparable across the lab)

Everything else — how much detail, how many images, bullet points vs.
prose — is up to you.

## 3. Optional: open it in Obsidian

If you want backlinks, graph view, and Dataview tables, open this whole
repo folder as an Obsidian vault (`File → Open folder as vault`). Nothing
here requires it — it's just a nicer window onto the same Markdown files.
Nothing about the files changes if you never install Obsidian at all.

## 4. When you're done with an experiment

Update `status: complete` and `date_completed` in the note's YAML, fill in
**Results**, **Interpretation**, and **Decision**, and link the figures in
`5-figures/`. That note is now the thing you pull up in lab meeting —
same instinct as Jacob's `JSRe####-R` files, just one note instead of two.

## 5. Starting a project, protocol, or sample record

These aren't auto-numbered like experiments, so just copy the template:

```bash
cp templates/project.md  Projects/PRMT5-ChromatinRelease.md
cp templates/protocol.md Protocols/P_WesternBlot.md
cp templates/sample.md   Samples/JSRp072.md
```

## Where to read more

- [`docs/SOP.md`](SOP.md) — the short version of what's required vs. optional
- [`docs/design-notes.md`](design-notes.md) — why the system is shaped this way,
  how it fits with LabArchives, and where AI comes in
- [`reference/jacob-original-system/`](../reference/jacob-original-system/) —
  the original spreadsheet/folder system this is all based on
