# AI_ELN — Shechter Lab Research Record System

A laboratory notebook built on plain Markdown files instead of a proprietary
ELN — designed to be searchable, linkable, AI-readable, and roughly zero
effort to start using today.

> **Status:** pilot. This is a small, working scaffold, not a finished
> product — the point is to try it on real experiments and let it evolve.

## Why

Our site-licensed LabArchives works, but its editing interface makes people
avoid writing things down until they have to. Meanwhile, one lab member
(Jacob Roth) independently built a better information architecture using
nothing but a spreadsheet and a folder-naming convention: every experiment
gets a stable ID, a standard folder layout, and a short results summary
written while it's still fresh. That system already works. What it's
missing is a format that's easy to search, link, and hand to an AI
assistant — which is exactly what plain Markdown + a little YAML metadata
is good at.

So this repo doesn't replace Jacob's system or LabArchives. It translates
the former into Markdown, and demotes the latter to an archival snapshot
instead of the daily working tool. The full reasoning is in
[`docs/design-notes.md`](docs/design-notes.md); the original spreadsheet and
folder system it's based on is preserved in
[`reference/jacob-original-system/`](reference/jacob-original-system/).

## Try it in one command

```bash
python3 scripts/new_experiment.py \
  --initials ABC \
  --researcher "Your Name" \
  --title "Whatever you're doing today"
```

That's it — no account, no plugin, no setup beyond Python 3, which is
already on every lab computer. It creates a new experiment ID, the standard
folder set, a Markdown note with the metadata already filled in, and an
entry in the lab-wide inventory. See
[`docs/getting-started.md`](docs/getting-started.md) for the full walkthrough,
or look at `Experiments/DSLe0001_.../1-notes/DSLe0001.md` to see exactly
what that command produces.

## Layout

```
AI_ELN/
├── Experiments/    one folder per experiment, auto-generated
├── Projects/       rolled-up current state of each research thread
├── Protocols/      living, versioned protocol documents
├── Samples/        plasmids, oligos, antibodies, cell lines, ...
├── Inventory/       experiments.csv — the lab-wide index
├── templates/       the four Markdown+YAML templates everything above is built from
├── scripts/         new_experiment.py — the one command that creates an experiment
├── docs/            getting-started, the data-management SOP, and the design rationale
└── reference/        Jacob's original spreadsheet/folder system, kept for provenance
```

Each experiment folder looks like this — same shape every time:

```
DSLe0123_short-slug-of-the-title/
├── 1-notes/           the experiment's Markdown note
├── 2-data_raw/        untouched instrument output (or a pointer to where it lives)
├── 3-code/            analysis
├── 4-data_processed/  derived data
└── 5-figures/         exported panels
```

## What's required, what's not

**Required:** an experiment ID, project, researcher, date, objective, where
the raw data lives, which protocol version was used, results, and an
interpretation. That's it — see [`docs/SOP.md`](docs/SOP.md).

**Everything else is yours to decide:** prose style, how many images you
embed, whether you analyze in R, Python, or Prism, how you take daily notes.
The system standardizes the interface between experiments, not how anyone
thinks or writes.

## Optional: open it in Obsidian

If you want backlinks, a graph view, and Dataview tables, open this repo
folder as an Obsidian vault. Nothing here depends on it — every file is
plain Markdown, readable and greppable with or without Obsidian installed.

## Where AI fits in

Structured, linked Markdown notes are far easier for an AI assistant to
search and reason over than PDFs or LabArchives pages — every answer can
cite the actual experiment ID it came from instead of being a free-floating
guess. Any AI coding agent (Claude Code, Codex CLI, Gemini CLI) already
works here today with zero setup beyond running it inside this folder —
[`AGENTS.md`](AGENTS.md) is what tells it the lab's own rules (cite
experiment IDs, never fabricate a result, always create experiments through
the script). See [`docs/ai-agents.md`](docs/ai-agents.md) for how that's
meant to stay vendor-agnostic, and
["AI integration, in stages"](docs/design-notes.md#ai-integration-in-stages)
for the fuller plan (semantic search, project synthesis, ingestion).

## Read more

- [`docs/getting-started.md`](docs/getting-started.md) — how to actually use this, today
- [`docs/SOP.md`](docs/SOP.md) — the two-page data-management SOP
- [`docs/design-notes.md`](docs/design-notes.md) — the full reasoning: why not
  just adopt an existing Obsidian ELN plugin, how LabArchives fits in, the
  collaboration model, and the staged AI plan
- [`docs/ai-agents.md`](docs/ai-agents.md) / [`AGENTS.md`](AGENTS.md) — how any
  AI coding agent (Claude Code, Codex CLI, Gemini CLI) gets lab-specific
  context without locking the lab into one vendor
- [`reference/jacob-original-system/`](reference/jacob-original-system/) —
  the spreadsheet, R Markdown, and slide deck this whole system is built from
