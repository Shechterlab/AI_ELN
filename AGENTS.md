# Agent instructions: Shechter Lab AI_ELN

If you are an AI agent (Codex CLI, Claude Code, Cowork, Gemini CLI, Cursor,
or similar) working in this folder, read this first. It applies to every
model and every tool, so it is a plain file at the top of the folder and is
not part of one vendor's configuration.

## What this is

This folder holds the tools for the lab's research record. The record itself
is a notebook: one folder per person, kept wherever that person keeps their
work. A notebook has one Markdown file per experiment, project, protocol,
and sample, in a fixed folder layout. Each file starts with a header of
`key: value` lines (flat YAML). The complete rules are in
`docs/CONVENTIONS.md`. The tool that follows them is `scripts/eln.py`. The
Markdown notes are the record you work from. Large raw data stays on
institutional storage and the note gives its path. LabArchives is the
archival record.

## Layout

In this folder (the tools):

```
scripts/eln.py          creates and checks records (Python)
docs/app/, mcp/         the same operations in JavaScript: the browser page, `mcp/call.mjs`, a server for AI clients
templates/              the note templates; Check warns about a header key that is not in the template
docs/lab.yaml           lab name and house style for the pages and printouts (a notebook's own lab.yaml wins)
.agents/skills/lab/     skills for working with this record (read the SKILL.md when a task matches)
.agents/skills/vendor/  pinned methodology skills from K-Dense; never edit, see skills.lock.json
sandbox/alex, sandbox/jordan   two fictional notebooks for practice
```

In a notebook folder:

```
Experiments/{ID}_{short-title}/{1-notes,2-data_raw,3-code,4-data_processed,5-figures}/
Protocols/P_{Name}.md   Samples/{ID}.md   Projects/{ID}.md
Inventory/*.csv         index made by `eln.py index`; never edit by hand
notebook.md             whose notebook this is and the last ID given out per kind; kept by the tools
Exports/                folders written by `export --format folder`: copies, never cite or edit them
AGENTS.md               the rules in short, written at setup
```

**Which notebook the commands work on.** In this order: the folder given
with `--root`; the environment variable `AI_ELN_ROOT`; the `root` saved in
`~/.ai_eln.json` by `eln.py init --root "/path/to/notebook"`; and with none
of these, this folder. The notebook is normally a different folder from
this one. Find out which folder it is (check `AI_ELN_ROOT` and
`~/.ai_eln.json`) before you read or write a file by path. The paths that
`eln.py find` prints are relative to the notebook folder.

**IDs.** Experiments `{INITIALS}e{NNNN}` (`JSRe0002`), samples
`{INITIALS}{p|i|a|c|m|t|r|s|g}{NNNN}` (`JSRp0001`; the letter is the kind of
sample), protocols `P_{Name}`, projects by name. Initials are two to four
letters; three are recommended. A notebook that names its owner in
`notebook.md` gives new records that person's initials, and `--initials`
overrides that.

**IDs with someone else's initials.** A notebook belongs to one person. A
note may cite a record from another person's notebook by its ID (a sample
`ALXc0001` in a note of `JOR`). That record is not in this notebook, and
Check does not report it as missing. Do not create it here; say that it is
in the other notebook if asked.

**Older folders.** Any other folder in a notebook is not a record.
`eln.py adopt PATH` makes an experiment record from one: the experiment gets
the next ID, and the folder is moved unchanged into that experiment's
`2-data_raw/`. Adopt a folder only when the person asks.

**`Exports/` holds copies.** Export writes them. Do not cite or edit them;
use the notes they were copied from.

**`sandbox/` is fictional.** It holds two made-up notebooks for practice
(`sandbox/alex` for "Alex Example", `sandbox/jordan` for "Jordan Example").
Never cite anything in it as a lab result, and do not search it when the
question is about the lab's work. Work there only when the person asks for
the sandbox (`--root sandbox/alex` or `--root sandbox/jordan`).

## The tool

```bash
python3 scripts/eln.py find [--project X] [--status s] [--researcher r] [--tag t] [--sample ID] [--protocol ID] [--type T] [--text q] [--kind sample|protocol|project] [--ids|--json]
python3 scripts/eln.py new experiment --title "..." [--project ID] [--type T] [--protocol P_X] [--samples ID,ID] [--notebook NB..] [--tags meeting]
python3 scripts/eln.py new sample --type plasmid --title "..."   |  new protocol --name X  |  new project --id X
python3 scripts/eln.py adopt ["/path/to/old folder"]   # an older folder becomes an experiment; with no folder, lists the candidates
python3 scripts/eln.py validate [--strict]      # Check: every rule in CONVENTIONS.md; ERROR fails, WARN advises
python3 scripts/eln.py index                    # regenerate Inventory/*.csv
python3 scripts/eln.py report                   # lab-meeting brief from tags: [meeting]
python3 scripts/eln.py export --project X       # the notes as one Markdown text to paste into a chat; --out FILE saves it
python3 scripts/eln.py export --project X --format folder   # a folder of plain files in Exports/
python3 scripts/eln.py export --project X --format eln --out X.eln   # a .eln archive that other electronic notebooks import
python3 scripts/eln.py complete ID [--date D]   # mark complete: checks Results/Interpretation, sets status, writes the snapshot and the list of checksums (rule 9)
python3 scripts/eln.py verify [ID]              # compare a completed experiment's files with that list of checksums
python3 scripts/eln.py render ID                # one note as a single HTML file, for printing
```

`--root DIR` works on any command, before or after it.

If Python is not available but Node is, the same operations are
`node mcp/call.mjs TOOL '{json}'` (`node mcp/call.mjs --list` shows them).
`mcp/server.mjs` offers them over MCP (a way for AI programs to call
tools). If the `ai-eln` MCP server is connected, its tools
(`create_experiment`, `find_notes`, `write_section`, `check_notebook`, ...)
are the same operations again. All three write the same files; use
whichever is available.

While a record is being created the tools hold a lock: an empty `.eln-lock`
folder at the top of the notebook, there for a moment.

## Ground rules

1. **Cite experiment IDs.** Every factual claim about a lab result names
   the experiment(s) it comes from. If no note supports it, say so; do not
   fill the gap with a plausible guess.
2. **Never fabricate data, figures, numbers, or experiments.** Drafts of
   Results, summaries, and project pages use only what is written in the
   notes you were pointed at or found.
3. **Filter before reading.** Use `eln.py find` and `Inventory/*.csv` to
   narrow by header fields, then open only the matching notes. A notebook
   grows larger than an AI tool can read at once.
4. **Create records only with `eln.py new ...`** (or `eln.py adopt` for an
   older folder). It assigns the ID, makes the folders, copies the protocol
   as run, and updates the index. A folder made by hand breaks the ID
   sequence. If the tool says "No initials", ask the person for their
   initials, name, and notebook folder, then run
   `eln.py init --initials XXX --researcher "Name" --root "/path/to/notebook"`.
5. **Never change anything in `2-data_raw/`.** Do not edit, rename, or
   reorganize what is in it. Derived files go in `4-data_processed/`, named
   `{ID}_{description}`.
6. **Keep to the templates.** New notes follow `templates/*.md`. Check
   warns about a header key that is not in the template. If a field is
   missing, propose a change to the template and do not add a key of your
   own.
7. **Ask before bulk edits.** Rewriting headers across many notes,
   renaming folders, or restructuring needs a human's confirmation first.
8. **Run `eln.py validate` after editing** and fix what it reports for the
   notes you touched.
9. **Mark an experiment complete with `eln.py complete ID`.** Do not edit
   `status` by hand. The command checks that Results and Interpretation
   are written, writes the snapshot (one HTML file with the whole
   experiment, for printing) and the manifest (a list of checksums: a
   number computed from each file's content, used to detect later
   changes), and updates the index.
10. **Vendored skills' scripts need packages.** Run them as
    `uv run --python 3.12 --with <pkg> ... python <script>`; never install
    into the system Python. If `uv` is missing, say so and do not install
    anything globally.

## Common requests

| request | do |
|---|---|
| "Create an experiment for ..." | `eln.py new experiment` with what was given; ask for a title if missing; check `--project`/`--protocol`/`--samples` exist first. Skill: `eln-record-experiment`. |
| "What do we know about X" / "which experiments used Y" | `eln.py find`, read the matches, answer with IDs, say plainly if nothing turned up. Skill: `eln-search-and-cite`. |
| "Summarize / update project X" | Read `Projects/X.md` and every experiment with X in `project`; rewrite *Current state* in place, every conclusion cited. Skill: `eln-project-synthesis`. |
| "Write up my results" / "mark it complete" | Fill the named sections from what the person tells you; then `eln.py complete ID`. Skill: `eln-record-experiment`. |
| "Make a record of this old folder" | `eln.py adopt "PATH"`; then tell the person the new ID and that the title and dates were read from the folder and may need correcting. Skill: `eln-record-experiment`. |
| "Send this to eLabFTW / RSpace / the core" | `eln.py export --format eln --project X --out X.eln`; the archive imports there directly. For a folder of plain files, `--format folder`. |
| "Analyse the data in 4-data_processed" | Read the `statistical-analysis` / `exploratory-data-analysis` skill first; run scripts via `uv run --with ...`; write results into the note's Results section, never as a new conclusion. |
| "Prepare lab meeting" | `eln.py report`; expand from the flagged notes only. |
| Design, statistics, writing, citations | The vendored skills under `.agents/skills/vendor/` apply; they are methodology, and rules 1-2 still hold. |

## More

`docs/CONVENTIONS.md` (the rules), `docs/getting-started.md`,
`docs/SOP.md`, `docs/ai-agents.md` (how each tool connects),
`docs/design-notes.md` (why), `.agents/skills/README.md`.
