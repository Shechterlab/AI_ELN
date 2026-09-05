# AI_ELN — the Shechter Lab research record

A lab notebook made of plain files in plain folders. Every experiment gets a
stable ID, the same five subfolders, and one Markdown note with a short
header. Because the structure never varies, a person can find anything in
seconds, a spreadsheet can index it, and an AI assistant can read it and
cite the exact experiment a claim came from.

No accounts, no plugins, no database, no API keys. If you can make a folder
and type in a text file, you can use this.

## What you actually do

1. **Double-click `launchers/New Experiment`.** It asks for a title (and a
   few optional things), then creates the experiment folder and opens the
   note. The first time, it also asks your initials and name.
2. **Write in the note.** Objective before you start, Results and
   Interpretation when you have them. The note is a text file; use any editor.
3. **Drop files into the subfolders**, named with the experiment ID in
   front: `JSRe0002_R_blot-quantification.png` into `5-figures/`. Raw
   instrument files go into `2-data_raw/` untouched.

That is the whole habit. Two more double-clicks are worth knowing:
`Check Everything` tells you if anything is misnamed or missing, and
`Lab Meeting Brief` writes the summary for the next meeting from whatever
you flagged.

Mac users: the first time you double-click a launcher, right-click it and
choose *Open* instead. Windows needs Python installed once; see
[`docs/getting-started.md`](docs/getting-started.md).

## The whole system on one screen

```
Experiments/
└── JSRe0002_SNRPB-chromatin-retention-KCl-titration/
    ├── 1-notes/            JSRe0002.md  +  JSRe0002_P_WesternBlot_20260901.md (protocol as run)
    ├── 2-data_raw/         instrument output, never renamed, never edited
    ├── 3-code/             JSRe0002_analysis.R
    ├── 4-data_processed/   JSRe0002_quantification.csv
    └── 5-figures/          JSRe0002_R_fractionation-KCl_20260904.png   <- the one you show in lab meeting
Protocols/    P_WesternBlot.md          one living file per protocol
Samples/      JSRp0001.md               plasmids, oligos, antibodies, cell lines, gels...
Projects/     PRMT5-ChromatinRelease.md rolled-up state of a research thread, citing experiment IDs
Inventory/    *.csv                     generated index of all of the above; open in Excel
```

| Thing | ID looks like | Made by |
|---|---|---|
| Experiment | `JSRe0002` | `New Experiment` |
| Sample | `JSRp0001` (p plasmid, i oligo, a antibody, c cell line, g gel, ...) | `New Sample` |
| Protocol | `P_WesternBlot` | `New Protocol` |
| Project | `PRMT5-ChromatinRelease` | `New Project` |

The initials are yours, so numbering never collides with anyone else's. An
ID written anywhere is a link. The complete rules fit on one page:
[`docs/CONVENTIONS.md`](docs/CONVENTIONS.md). The one-page version to pin
above your bench: [`docs/CHEATSHEET.md`](docs/CHEATSHEET.md).

Every note starts with a header like this, which is what makes the record
searchable and what the AI reads first:

```yaml
---
type: experiment
experiment_id: JSRe0002
title: SNRPB chromatin retention after PRMT5 inhibition
researcher: Jacob Roth
project: [PRMT5-ChromatinRelease]
date_started: 2026-09-01
status: active            # active | complete | paused | abandoned
protocols: [P_WesternBlot]
samples: [JSRp0001, JSRa0003]
tags: [meeting]           # flag for the next lab meeting
---
```

## Using AI with it

Everything here works with the ChatGPT site license or a Claude
subscription. Nothing needs an API key.

- **ChatGPT, copy and paste.** Double-click `launchers/Export for ChatGPT`,
  pick a project (or press Enter for everything active). It writes one file
  containing the notes plus a short primer on how to read them. Paste it
  into a chat and ask: *summarize what we know, citing experiment IDs*;
  *draft a results paragraph for JSRe0002*; *which experiments used
  JSRa0003?* Once, paste [`docs/ai-briefing.md`](docs/ai-briefing.md) as
  the instructions of a ChatGPT Project so every chat already knows the rules.
- **Codex, Claude Code, Cowork, Gemini CLI.** Open the tool inside this
  folder. It reads [`AGENTS.md`](AGENTS.md) (the lab's rules: cite IDs,
  never invent a result, create experiments only through the tool) and the
  skills in [`.agents/skills/`](.agents/skills/README.md): how to record an
  experiment, how to search and cite, how to synthesize a project page,
  plus vendored methodology skills from
  [K-Dense](https://github.com/K-Dense-AI/scientific-agent-skills)
  (experimental design, statistics, scientific writing, citations,
  LabArchives). Those are pinned to a release and updated only by a
  reviewed diff.

Details and the reasoning: [`docs/ai-agents.md`](docs/ai-agents.md).

## Keeping it honest

`launchers/Check Everything` (or `python3 scripts/eln.py validate`) reads
every note and folder and reports what breaks the conventions: a misnamed
folder, a missing subfolder, a `status` that isn't one of the four, a
sample ID that points at nothing, a figure without the experiment ID in
front. Errors fail; warnings are advice. Run it before lab meeting and
before handing a folder to anyone.

## For people who like a terminal

Everything the launchers do is one script with no dependencies:

```bash
python3 scripts/eln.py init                                  # once: initials, name, where files live
python3 scripts/eln.py new experiment --title "..." --project PRMT5-ChromatinRelease --protocol P_WesternBlot
python3 scripts/eln.py new sample --type plasmid --title "pcDNA3-FLAG-SNRPB"
python3 scripts/eln.py validate --strict
python3 scripts/eln.py find --status active --tag meeting
python3 scripts/eln.py index                                 # regenerate Inventory/*.csv
python3 scripts/eln.py report                                # Markdown brief for lab meeting
python3 scripts/eln.py export --project PRMT5-ChromatinRelease --out brief.md
```

`--help` on any command. The files can live in this folder (default) or
anywhere the lab already shares files — a synced OneDrive folder, a server
mount — set once with `init`. Tests: `python3 -m unittest discover -s tests`.

## Read more

- [`docs/getting-started.md`](docs/getting-started.md) — first day, step by step, including the Mac and Windows one-time setup
- [`docs/CHEATSHEET.md`](docs/CHEATSHEET.md) — one printable page
- [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) — the rules, precisely
- [`docs/SOP.md`](docs/SOP.md) — what's required, what's flexible, what happens when an experiment is done
- [`docs/ai-agents.md`](docs/ai-agents.md) / [`docs/ai-briefing.md`](docs/ai-briefing.md) — AI without API keys
- [`docs/design-notes.md`](docs/design-notes.md) — why it's shaped this way; where LabArchives fits
- [`reference/jacob-original-system/`](reference/jacob-original-system/) — the spreadsheet-and-folders system by Jacob Roth that this is a direct translation of

## Credits

The information architecture — one ID per experiment, five fixed
subfolders, IDs for every gel and plasmid, a results file you can find in
one search — is Jacob Roth's. This repo turns it into plain Markdown with a
header, adds a tool that enforces the conventions, and makes the whole
thing readable by AI.
