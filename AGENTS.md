# Agent instructions — Shechter Lab AI_ELN

If you are an AI coding/agent assistant (Claude Code, OpenAI Codex CLI,
Gemini CLI, Cursor, or similar) opened inside this repository, read this
file before doing anything else. It applies regardless of which underlying
model or tool is running you — that's the point of it living in a plain
file at the repo root instead of any one vendor's config format.

## What this repository is

The lab's research record: one Markdown file per experiment, project,
protocol, and durable sample/reagent, with YAML front matter for structured
fields. See `README.md` for the full pitch and `docs/design-notes.md` for
the reasoning. In short: Markdown is the source of truth, large raw data
lives outside this repo on institutional storage, and LabArchives (not
this repo) is the compliance/archival record.

## Layout

- `Experiments/` — one folder per experiment (`1-notes/2-data_raw/3-code/4-data_processed/5-figures`)
- `Projects/`, `Protocols/`, `Samples/` — one Markdown file each
- `Inventory/experiments.csv` — lab-wide index, generated, not hand-maintained
- `templates/` — the four note schemas everything above is built from
- `scripts/new_experiment.py` — the only way experiments get created

**Where the data actually lives is configurable.** `Experiments/` and
`Inventory/` above may not be inside this checkout at all — a lab can point
`new_experiment.py` at whatever shared storage it has already chosen (a
synced OneDrive/Dropbox folder, a shared Obsidian vault, a server mount)
via `--root PATH` or the `AI_ELN_ROOT` environment variable. Check for
`AI_ELN_ROOT` in the environment before assuming paths are repo-relative;
if it's set, that's where `Experiments/` and `Inventory/` are, not here.

## Ground rules

1. **Cite experiment IDs.** Any factual claim about a lab result must name
   the experiment_id(s) it comes from (e.g. "DSLe0412, DSLe0431"). If you
   can't find a supporting note, say so — don't fill the gap with a
   plausible-sounding guess.
2. **Never fabricate data, figures, or numbers.** If asked to draft a
   Results section, summary, or figure legend, use only what's actually
   written in the linked note(s) and files.
3. **Search before answering.** The YAML front matter (`project`,
   `researcher`, `status`, `date`, `tags`) exists specifically so you can
   filter before reading full notes — grep/glob across `Experiments/`,
   `Projects/`, `Protocols/`, `Samples/` rather than guessing from one file.
4. **Never create an experiment folder by hand.** Always run
   `python3 scripts/new_experiment.py ...` — it assigns the ID and appends
   the inventory row. A hand-made folder won't show up in the inventory
   and risks reusing an ID. IDs are assigned per researcher initials by
   scanning the inventory for the highest existing number, which is fine
   in practice — it's not lock-protected against two people creating an
   experiment with the same initials in the same instant, which shouldn't
   come up in normal use.
5. **Treat `2-data_raw/` as immutable.** Don't edit, rename, or "clean up"
   raw data. Processed/derived data goes in `4-data_processed/`.
6. **Match the existing schema.** New notes should follow `templates/*.md`.
   If a field is genuinely missing, propose adding it to the template
   rather than inventing an ad hoc one-off field in a single note.
7. **Ask before bulk edits.** Rewriting front matter across many notes,
   renaming folders, or restructuring the vault needs a human to confirm
   first — these are exactly the changes that are annoying to undo across
   a shared, git-tracked lab record.

## Common requests and how to handle them

- **"Create an experiment for ___"** → run `scripts/new_experiment.py`
  with whatever flags were given; ask for `--title` if nothing else, since
  it's the only hard requirement.
- **"What do we know about X"** → search experiment/project notes for X,
  answer with citations to the matching experiment_ids, and say plainly if
  nothing turned up rather than speculating.
- **"Summarize project X"** → read `Projects/X.md` plus every experiment
  whose `project` field includes X, and update the project note's
  "Current state" section in place (don't append a second copy) following
  `templates/project.md`'s structure, each claim citing its experiment ID.
- **"Draft a lab meeting summary / results section"** → pull only from
  notes the person points you at (or that you found and can cite); flag
  anything that looks like a single-replicate result rather than
  presenting it as settled.

## Full background

`docs/getting-started.md` (quickstart), `docs/SOP.md` (what's required vs.
flexible), `docs/design-notes.md` (full rationale), `docs/ai-agents.md`
(why this file exists and how it's meant to be used across tools).
