# Getting started

Ten minutes, once. After that, creating an experiment is one double-click.

## 0. Get the folder onto your computer

Either the lab's shared copy (a synced OneDrive/Dropbox folder — ask
whoever set it up), or download this repository (green **Code** button →
**Download ZIP**, then unzip), or `git clone` it if you know what that is.
Wherever it ends up, that folder is your notebook. Don't move things inside
it around by hand.

## 1. One-time setup for your computer

**Mac.** Python is already there. The first time you double-click a
launcher, macOS will say it's from an unidentified developer: right-click
(or Control-click) the launcher, choose **Open**, then **Open** again. Only
needed once per launcher. If a window offers to install *command line
developer tools*, click **Install**; that is Python being set up and takes
a few minutes.

**Windows.** Install Python once from <https://www.python.org/downloads/>
and tick **Add python.exe to PATH** on the first screen of the installer.
Then the launchers just work.

**Linux.** Python 3 is already there; run the `.command` files from a
terminal or use the commands in §6.

## 2. Create your first experiment

Double-click **`launchers/New Experiment`**. A small window asks:

```
First time here. Two quick questions (asked only once):
  Your initials (2-4 letters, e.g. JSR): JSR
  Your full name: Jacob Roth

New experiment. Only the title is required; press Enter to skip the rest.
  Title (what are you doing?): SNRPB chromatin retention after PRMT5 inhibition
  Project ID (existing: PRMT5-ChromatinRelease):
  Experiment type (e.g. WesternBlot, IF, qPCR): WesternBlot
  Protocol ID (existing: P_WesternBlot): P_WesternBlot
  Sample IDs, comma-separated (existing: DSLp0001):
  Physical notebook page (e.g. NB02-153): NB02-153
  Flag this for the next lab meeting? (y/N): y

Created JSRe0001
  Experiments/JSRe0001_SNRPB-chromatin-retention-after-PRMT5-inhibition/1-notes/JSRe0001.md
  Experiments/JSRe0001_.../1-notes/JSRe0001_P_WesternBlot_20260901.md  (snapshot of P_WesternBlot)
Opening the note. Fill in the Objective; everything else can wait.
```

You now have a folder with the five standard subfolders, a note with the
header filled in, a copy of the protocol as it was on that day, and a row
in `Inventory/experiments.csv`. The note opens in whatever your computer
uses for `.md` files.

## 3. Write in the note

It's a text file. The header at the top is filled in for you; the parts
that matter are the `##` section titles — keep them so every experiment in
the lab reads the same way. Between them, write however you like.

Fill in **Objective** before you start. Fill in **Results**,
**Interpretation**, and **Decision** when you have them. Leave a section as
"None" rather than deleting it.

Any editor works, including TextEdit (Mac: Format → Make Plain Text once)
or Notepad. A free Markdown editor such as VS Code or Typora shows
headings and images nicely; none of them is required.

## 4. Put files where they belong, named with the ID

```
2-data_raw/         instrument output. Original filenames. Never edit, never rename.
3-code/             JSRe0001_analysis.R
4-data_processed/   JSRe0001_quantification.csv
5-figures/          JSRe0001_R_fractionation-KCl_20260904.png   <- the results figure (R = "results")
```

Start every file you make with the experiment ID; join words with hyphens.
That single habit is what makes "find me the blot from that experiment" a
one-second search forever. Full grammar: [`CONVENTIONS.md`](CONVENTIONS.md) §3.

If the raw data is too large to keep here (microscopy, sequencing), leave
it on the institutional storage and put its location in the note's
`raw_data_path` line.

## 5. The other launchers

| Launcher | What it does |
|---|---|
| **New Sample** | A record for a plasmid, oligo, antibody, cell line, mouse line, peptide, protein prep, slide, or gel. Gets an ID like `JSRp0001`. Reuse that ID in every experiment that touches it. |
| **New Protocol** | One living file per protocol, e.g. `Protocols/P_WesternBlot.md`. Edit it in place as it improves; bump the `version` date and add a Change log line. |
| **New Project** | The rolled-up state of a research thread; conclusions cite experiment IDs. |
| **Check Everything** | Reads every note and folder and lists what breaks the conventions. `ERROR` = fix it; `WARN` = advice. |
| **Lab Meeting Brief** | Writes `Inventory/meeting-brief_<date>.md` from everything tagged `meeting`, plus the active-experiments table. |
| **Export for ChatGPT** | Bundles a project (or all active experiments) into one file to paste into ChatGPT. See [`ai-agents.md`](ai-agents.md). |

## 6. When an experiment is finished

Open the note and change two header lines:

```yaml
status: complete
date_completed: 2026-09-12
```

Make sure Results and Interpretation are written and `raw_data_path` is
somewhere backed up. Then run **Check Everything**; it will tell you if
you forgot one of those.

## 7. The same thing from a terminal

The launchers just run one script. If you prefer typing:

```bash
python3 scripts/eln.py init                                # initials, name, where files live
python3 scripts/eln.py new experiment --title "..."         # add --project, --protocol, --samples, --tags meeting ...
python3 scripts/eln.py new experiment --interactive         # the same questions the launcher asks
python3 scripts/eln.py new sample --type plasmid --title "..."
python3 scripts/eln.py validate                            # --strict makes warnings fail too
python3 scripts/eln.py find --status active --project PRMT5-ChromatinRelease
python3 scripts/eln.py report
python3 scripts/eln.py export --project PRMT5-ChromatinRelease --out brief.md
```

## 8. Where the files live

By default, inside this folder — simplest, and fine for a synced OneDrive
or Dropbox copy of the whole folder. If the lab keeps notes somewhere else
(a server mount, a different shared folder), tell the tool once:

```bash
python3 scripts/eln.py init --root "/path/to/ShechterLab/ELN"
```

That writes `~/.ai_eln.json`; the launchers and every command use it from
then on. `AI_ELN_ROOT` in the environment or `--root` on a command
overrides it for one shell or one call.

## If something doesn't work

- **Mac: "cannot be opened because it is from an unidentified developer"** —
  right-click → Open (once per launcher).
- **Mac: double-clicking opens the file in a text editor instead of running
  it** — the executable bit was lost in a download or sync. In Terminal:
  `chmod +x` followed by a space, then drag the `launchers` folder into the
  window, add `/*.command`, press Enter. Or use the commands in §7.
- **Windows: a window flashes and closes, or "python is not recognized"** —
  install Python (§1) with *Add to PATH* ticked, then try again.
- **"No initials"** — run `launchers/New Experiment` once (it asks), or
  `python3 scripts/eln.py init`.
- **Check Everything says a folder "does not match {ID}_{slug}"** — someone
  made or renamed an experiment folder by hand. Rename it to
  `{ID}_{words-with-hyphens}` or recreate it with the launcher.
