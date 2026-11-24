# AI_ELN: the Shechter Lab research record

A lab notebook kept as plain files in ordinary folders. Each experiment has
an ID, a folder with the same five subfolders, and one Markdown note with a
short header. Every experiment is laid out the same way, so it can be
searched by ID, listed in a spreadsheet, and read by an AI assistant that
cites the experiment each statement comes from.

It needs no account, plugin, database, or API key. In Chrome or Edge nothing
is installed: a page in the browser works on the folder directly. The same
tools are also Python scripts with double-click launchers, and an MCP server
for AI clients.

Website: <https://shechterlab.github.io/AI_ELN/> (served from [`docs/`](docs/README.md)).

## Daily use

1. **Open the notebook.** In Chrome or Edge, go to
   <https://shechterlab.github.io/AI_ELN/app/>, click **Open notebook
   folder**, and choose the folder. Nothing is installed and nothing is
   uploaded. In Safari or Firefox, double-click `launchers/Open ELN`
   instead (needs Python).
2. **Click New experiment, type a title, click Create.** The folder, the
   note, the protocol copy, and the index row are created.
3. **Click Edit here and write.** Write the Objective before you start, and
   Results, Interpretation, and Decision when you have them.
4. **Add files.** In the browser page, **Add files** on the note puts a file
   in the right subfolder under the right name. Otherwise copy files into
   the subfolders with the experiment ID in front:
   `JSRe0002_R_blot-quantification.png` into `5-figures/`. Raw instrument
   files go into `2-data_raw/` with their original names.

When the experiment is done, click **Mark complete**. It checks that Results
and Interpretation are written, sets the date, and writes two files next to
the note: an HTML snapshot that prints to PDF, and a list of checksums.

The other buttons:

- **Check** lists files and folders that are misnamed or missing.
- **Meeting brief** writes the summary for lab meeting from the experiments
  you flagged.
- **Print / save as PDF** prints a note with page numbers and signature lines.
- **Repeat this experiment** starts a new experiment with the same title,
  project, protocols, and samples.
- **Adopt older folders** makes an experiment record from a folder you
  already have, without changing its files.
- **View a notebook (read-only)** opens someone's notebook so that nothing
  in it can be changed.

To practise on fictional data, click **Open the practice notebook** on the
page's first screen, or open the [`sandbox`](sandbox/README.md) folder.

![The home page](docs/img/home.png)

There are two versions of the page. One runs in the browser
([`docs/app/`](docs/app/README.md), JavaScript). The other is started by a
launcher (`scripts/eln_web.py`, Python) for Safari and Firefox, which cannot
open folders. They write the same files, and tests compare their output byte
for byte. The launcher page has the core jobs; adopting, adding files,
printing, and the folder export are in the browser page and the command
line. There are also terminal-window launchers (`New Experiment`, `Check
Everything`, ...) and a command line. On a Mac, right-click a launcher and
choose Open the first time; Windows needs Python installed once. See
[`docs/getting-started.md`](docs/getting-started.md).

## Using it in another lab

Edit [`docs/lab.yaml`](docs/lab.yaml): lab name, institution, links,
colours, fonts, and whether printouts carry signature lines. Replace the
logo in `docs/assets/`. The website, the notebook page, snapshots,
printouts, and exports all read that file; nothing else needs editing. A
notebook folder can carry its own `lab.yaml`, which is used in place of this
one for that notebook.

## Where it lives

A notebook is **one folder per person**. Keep it where you already keep
your work: your Dropbox or OneDrive, a lab share, or a drive. It holds
`notebook.md`, `Experiments/`, `Protocols/`, `Samples/`, `Projects/`,
`Figures/`, and `Inventory/`. Every file in it is plain text (Markdown with a small header,
CSV) or an ordinary data file, and the notes are complete and readable in
any editor without the tools. There is no server, no database, and no
central list of people or notebooks.

The tools are separate from the notebook. The browser page works on
whichever folder you open. The Python tools work on the folder you name
once with `eln.py init --root`, or on this folder itself if you name none.

- **Several people.** Each person keeps their own folder. If the folders
  sit next to each other in a shared folder, the page lists them when
  someone opens the shared folder, and **View a notebook** opens any of them
  read-only. IDs start with the owner's initials, so records from different
  notebooks never share an ID.
- **Old folders.** A notebook can be started in a folder that already holds
  work; nothing there is changed. **Adopt** turns an older folder into an
  experiment record when you want it to be one: it gets an ID and a note,
  and the folder is moved, exactly as it is, into the experiment's
  `2-data_raw/`.
- **Exports.** **Export** writes one Markdown file to paste into an AI chat,
  or a folder of plain files: the notes, their data files, a README, and an
  index, laid out like the notebook. For a hosted ELN there is also the
  standard [`.eln`](https://github.com/TheELNConsortium/TheELNFileFormat)
  archive (an RO-Crate ZIP) that eLabFTW, RSpace, Kadi4Mat, PASTA, SampleDB,
  OpenSemanticLab, and SciLog import.

A sync conflict produces two readable copies, and **Check** lists them.
This GitHub repository is only where the tools are developed; nobody needs
it day to day.

## Layout

```
Experiments/
└── JSRe0002_SNRPB-chromatin-retention-KCl-titration/
    ├── 1-notes/            JSRe0002.md  +  JSRe0002_P_WesternBlot_20260901.md (protocol as run)
    ├── 2-data_raw/         instrument output, never renamed, never edited
    ├── 3-code/             JSRe0002_analysis.R
    ├── 4-data_processed/   JSRe0002_quantification.csv
    └── 5-figures/          JSRe0002_R_fractionation-KCl_20260904.png   the result figure
Protocols/    P_WesternBlot.md          one file per protocol, edited in place
Samples/      JSRp0001.md               plasmids, oligos, antibodies, cell lines, gels...
Projects/     PRMT5-ChromatinRelease.md summary of a research project, citing experiment IDs
Figures/
└── JSRf0001_SNRPB-stays-on-chromatin/
    ├── 1-notes/            JSRf0001.md: which experiment each panel came from, the legend, the versions
    ├── 2-panels/           JSRf0001_a_blot.pdf, one file per panel
    ├── 3-source/           the layout file: Illustrator, CanvasX, Prism, PowerPoint, R, Python
    └── 4-exports/          JSRf0001_v1_20260915.pdf, the figure as it was sent out
Inventory/    *.csv                     index of everything above, made from the notes; opens in Excel
Exports/      export_.../               folders written by Export; copies, safe to delete
notebook.md                             whose notebook this is, and the last ID given out for each kind of record
```

| Thing | ID looks like | Made by |
|---|---|---|
| Experiment | `JSRe0002` | New experiment |
| Sample | `JSRp0001` (p plasmid, i oligo, a antibody, c cell line, g gel, ...) | New sample |
| Protocol | `P_WesternBlot` | New protocol |
| Project | `PRMT5-ChromatinRelease` | New project |
| Figure | `JSRf0001` | New figure |

A figure record is for an assembled figure that goes into a paper, a grant
or a talk and draws on one or more experiments. The result figure of a
single experiment stays in that experiment's `5-figures/`.

IDs start with your initials, so they cannot match anyone else's. An ID
written anywhere in a note is shown as a link. The full rules are in
[`docs/CONVENTIONS.md`](docs/CONVENTIONS.md). A one-page version to print is
[`docs/CHEATSHEET.md`](docs/CHEATSHEET.md).

Every note starts with a header like this. Search, the index, and AI tools
read it first:

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

![A filled-in note as the page shows it](docs/img/note.png)

## Using AI with it

Everything here works with the ChatGPT site license or a Claude
subscription. Nothing needs an API key.

- **ChatGPT, copy and paste.** Click **Export**, pick a project (or all
  active experiments), click **Copy all**, paste into a chat. The export
  contains the notes, the records they refer to, and a short explanation of
  how to read them. Ask: *summarize what we know, citing experiment IDs*;
  *draft a results paragraph for JSRe0002*; *which experiments used
  JSRa0003?* Once, paste [`docs/ai-briefing.md`](docs/ai-briefing.md) as
  the instructions of a ChatGPT Project so every chat already knows the rules.
- **MCP.** `node mcp/server.mjs` offers the notebook's operations (create,
  find, read, check, complete, export) as tools to any MCP client. Claude
  Code and Cowork pick it up from `.mcp.json` when opened in this (the tools) folder.
  See [`mcp/README.md`](mcp/README.md).
- **Codex, Claude Code, Cowork, Gemini CLI.** Open the tool inside this
  folder (the tools folder). It works on the notebook you named with
  `init --root`. A notebook folder itself holds only a short `AGENTS.md`
  with the rules, not the skills. Here it reads [`AGENTS.md`](AGENTS.md) (the lab's rules: cite IDs,
  never invent a result, create experiments only through the tool) and the
  skills in [`.agents/skills/`](.agents/skills/README.md): how to record an
  experiment, how to search and cite, how to synthesize a project page,
  plus fifteen vendored methodology skills from
  [K-Dense](https://github.com/K-Dense-AI/scientific-agent-skills)
  (statistics, experimental design, figures, EDA, writing, critical
  appraisal, literature search, slides, mass spec, RNA-seq, pathways,
  LabArchives, pre-registration, verification), pinned to a release and
  updated only by a reviewed diff.

[`sandbox/PILOT.md`](sandbox/PILOT.md) shows what those skills produced
when run against the fictional sandbox. Details and reasoning:
[`docs/ai-agents.md`](docs/ai-agents.md).

## Checking the record

**Check** (or `python3 scripts/eln.py validate`) reads every note and
folder and lists what does not follow the conventions: a misnamed folder, a
missing subfolder, a `status` that is not one of the four, a sample ID that
matches no sample, a figure without the experiment ID in front. An `ERROR`
has to be fixed; a `WARN` is advice. It also lists copies made by a sync
service. Run it before lab meeting and before giving a folder to anyone.
Every change to the tools is tested on macOS, Windows, and Linux, including
a strict check of the sandbox notebooks.

## Command line

The same jobs from a terminal. The script needs only Python:

```bash
python3 scripts/eln.py init                                  # once: initials, name, where files live
python3 scripts/eln.py new experiment --title "..." --project PRMT5-ChromatinRelease --protocol P_WesternBlot
python3 scripts/eln.py new sample --type plasmid --title "pcDNA3-FLAG-SNRPB"
python3 scripts/eln.py new figure --title "..." --experiments JSRe0002,JSRe0005 --label "Figure 2"
python3 scripts/eln.py validate --strict
python3 scripts/eln.py find --status active --tag meeting
python3 scripts/eln.py index                                 # regenerate Inventory/*.csv
python3 scripts/eln.py report                                # Markdown brief for lab meeting
python3 scripts/eln.py export --project PRMT5-ChromatinRelease --out brief.md
python3 scripts/eln.py export --project PRMT5-ChromatinRelease --format eln --out prmt5.eln   # for eLabFTW/RSpace/...
python3 scripts/eln.py complete JSRe0002                    # mark complete: snapshot + checksums
python3 scripts/eln.py adopt "/path/to/an old folder"        # make it an experiment record
python3 scripts/eln.py verify                               # anything changed since completion?
python3 scripts/eln_web.py                                   # the page, by hand
```

The same operations from Node, as JSON: `node mcp/call.mjs --list`.

`--help` on any command. The commands work on the notebook folder named
with `init --root` (or `--root` on one command); with neither, on the folder
the tools sit in.
Tests: `python3 -m unittest discover -s tests` (the JavaScript tests run when Node is installed).

## Read more

- [`docs/getting-started.md`](docs/getting-started.md): setup and first experiment, with screenshots
- [`docs/CHEATSHEET.md`](docs/CHEATSHEET.md): one printable page
- [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md): the rules, precisely
- [`docs/SOP.md`](docs/SOP.md): what is required, what is flexible, and what happens when an experiment is done
- [`docs/ai-agents.md`](docs/ai-agents.md) / [`docs/ai-briefing.md`](docs/ai-briefing.md): AI without API keys
- [`sandbox/`](sandbox/README.md): two fictional notebooks to practice on (`alex/`, `jordan/`); [`sandbox/PILOT.md`](sandbox/PILOT.md) is the AI features run against it
- [`docs/design-notes.md`](docs/design-notes.md): the reasons for the design, and where LabArchives fits
- [`reference/jacob-original-system/`](reference/jacob-original-system/): the spreadsheet-and-folders system by Jacob Roth that this is based on

## Credits

The design (one ID per experiment, five fixed subfolders, an ID for every
gel and plasmid, a result file that one search finds) is Jacob Roth's. This
repository keeps that design as Markdown notes with a header. It adds a tool
that creates the records and checks the naming, a page for doing the same by
clicking, and instructions for AI tools.
