# Getting started

Setup is done once per computer. After that, you open the notebook page and
create an experiment by filling in a form.

## 0. Where the record lives

Your notebook is one folder, and it is yours. Keep it where you keep your
work, usually inside Dropbox or OneDrive so it is backed up and on your
other computers. It holds `notebook.md` (whose notebook it is, and the last
IDs given out) and the folders `Experiments/`, `Protocols/`, `Samples/`,
`Projects/`, and `Inventory/`. There is no server, account, or central
copy, and the files are plain text.

A lab does not need one shared notebook. Each person keeps their own folder.
If the folders sit next to each other in a shared lab folder, opening the
shared folder in the page lists the notebooks in it.

You can start a notebook in a folder that already has work in it. Nothing
already there is changed. See "Adopting older folders" below for turning old
folders into experiment records.

**For the browser page** (§1) you need nothing else.

**For the launchers and the command line** you need the tools: download this
repository from GitHub (green **Code** button → **Download ZIP**, unzip) and
put the folder anywhere. Then tell the tools once where your notebook is:

```bash
python3 scripts/eln.py init --root "/path/to/My Notebook"
```

That writes `~/.ai_eln.json` and puts your name and initials into the
notebook's `notebook.md`. If you skip this, the tools keep the records inside
the tools folder itself. If you put the tools folder in Dropbox or OneDrive
and it came from `git clone`, delete the hidden `.git` folder inside it; git
and sync services corrupt each other.

Do not move or rename experiment folders or notes by hand. Use the page or
the launchers. Putting your own files into an experiment's subfolders is
fine.

## 1. Open the notebook

**In Chrome or Edge (nothing to install).** Go to
<https://shechterlab.github.io/AI_ELN/app/>, click **Open notebook folder**,
choose your notebook folder, and allow the page to edit it. The page works
on the files in that folder and does not upload them. Next time, click
**Reopen**. If the folder has no notebook in it yet, the page offers to set
one up there. If it holds several people's notebooks, the page lists them
and can start a new one next to them. Then click **settings**, enter your
initials and name (saved in this browser, and in the notebook's
`notebook.md` if it does not name an owner yet), and go to §3.

**In Safari or Firefox, or if you prefer the launchers.** These browsers
cannot open folders, so the notebook starts from a launcher and needs
Python. Set that up once:

**Mac.** The first time you double-click a
launcher, macOS will say it's from an unidentified developer: right-click
(or Control-click) the launcher, choose **Open**, then **Open** again
(on the newest macOS: *System Settings → Privacy & Security → Open
Anyway*). Only needed once per launcher, and not at all if the folder came
by OneDrive sync or `git clone`. If a window offers to install *command
line developer tools*, click **Install**. This installs Python and takes a
few minutes. It happens once.

**Windows.** Install Python once from <https://www.python.org/downloads/>
and tick **Add python.exe to PATH** on the first screen of the installer.
The launchers then work by double-click.

**Linux.** Python 3 is already there; run `python3 scripts/eln_web.py`.

## 2. Open the page with the launcher

Double-click **`launchers/Open ELN`**. A small window appears and your
browser opens a page like this:

![The home page: buttons for the common jobs, above the recent experiments](img/home.png)

The page runs on your own computer (the address starts with `127.0.0.1`);
and does not upload anything. Keep the small window open; closing it stops
the page. The first time, it asks for your initials and name under
**settings**. Your initials become your ID prefix (`JSRe0001`, `JSRe0002`,
…), so two people cannot get the same ID.

To practice without touching a real notebook, double-click
**`launchers/Try the Sandbox`**. It opens the same page on fictional data
that can be reset. In the browser version, click **Open the practice
notebook** on the first screen; it is kept in memory and is gone when you
close the tab.

## 3. Create your first experiment

Click **New experiment**. Only the title is required. The other
fields can be added later.

![The new-experiment form](img/new-experiment.png)

Click **Create experiment**. You now have a folder with the five standard
subfolders, a note with the header filled in, a copy of the protocol as it
stood today, and a row in the inventory. The page shows the new note.

## 4. Write in the note

Click **Edit here** on the note's page, write under the section titles,
and click **Save**. The note is a plain text file, so you can also edit it
in a plain-text editor (Notepad, TextEdit in plain-text mode, VS Code; not
Word). In the launcher version, **Open in your editor** opens it in whatever your
computer uses for `.md` files.

![A filled-in note as the page shows it](img/note.png)

Keep the `##` section titles so that every experiment has the same
structure. Write freely under them. Fill in **Objective**
before you start; **Results**, **Interpretation**, and **Decision** when
you have them. Leave a section as "None" rather than deleting it.

## 5. Put files where they belong, named with the ID

In the browser version, use **Add files** on the note's page: choose or drop
the files, pick the subfolder, and they are named for you. In the launcher
version, **Show folder** opens the experiment folder and you put the files
in yourself.

```
2-data_raw/         instrument output. Original filenames. Never edit, never rename.
3-code/             JSRe0001_analysis.R
4-data_processed/   JSRe0001_quantification.csv
5-figures/          JSRe0001_R_fractionation-KCl_20260904.png   <- the results figure (R = "results")
```

Start every file you make with the experiment ID; join words with hyphens.
A search for the experiment ID then finds every file you made for it (raw
instrument files keep their own names and are found by opening `2-data_raw`). Each subfolder has a short README saying what
goes in it. Full grammar: [`CONVENTIONS.md`](CONVENTIONS.md) §3.

If the raw data is too large to keep here (microscopy, sequencing), leave
it on the institutional storage and put its location in the note's
`raw_data_path` line. A figure in `5-figures/` is shown on the note's page when the
note links to it. In the note, type a line like this, with your file's name:

```
![Blot, treated and control](../5-figures/JSRe0001_R_blot_20260904.png)
```

## 6. The rest of the page

| Button | What it does |
|---|---|
| **New sample** | A record for a plasmid, oligo, antibody, cell line, mouse line, peptide, protein prep, slide, or gel. Gets an ID like `JSRp0001`. Tick it in the experiment form from then on. |
| **New protocol** | One file per protocol, e.g. `Protocols/P_WesternBlot.md`. Edit it in place as it improves; bump the `version` date and add a Change log line. |
| **New project** | A summary of a research project. Conclusions cite experiment IDs. |
| **Check** | Reads every note and folder and lists what breaks the conventions. `ERROR` = fix it; `WARN` = advice. |
| **Meeting brief** | The lab-meeting document from everything tagged `meeting`, plus the active-experiments table. **Save into Inventory** saves it in the notebook; **Download** saves it to your Downloads folder. |
| **Export** | Bundles a project (or all active experiments) into one file to paste into ChatGPT, or into a folder of plain files. See "Exports" below and [`ai-agents.md`](ai-agents.md). |
| **Adopt older folders** | Shown on Home when the notebook folder holds folders that are not records. See "Adopting older folders" below. |
| **Experiments / Samples / Protocols / Projects** | Browse and filter. Every ID on every page is a link. |
| **Ask the AI** | Example questions for an AI assistant, and which of the three ways (pasting an export into ChatGPT, an agent opened in the folder, or an MCP client) each one works with. |

## 7. When an experiment is finished

Click **Mark complete** on the note's page. It checks that Results and
Interpretation are written (and says so if not), sets the status and date,
and writes two files next to the note. The first is a snapshot: one HTML
file with the whole experiment and its figures, which you can print to PDF
for LabArchives. The second is a manifest: a list of every file in the
folder with its checksum (a fingerprint of the file's content), so **Verify
files** can later show whether anything changed. The note is not locked. If you edit the
experiment later, click **Refresh snapshot & manifest**; the completion date
stays the same and the page tells you which files changed. If Results or
Interpretation is empty, Mark complete refuses and offers **Complete
anyway**, for an experiment that ended without a result.

## 8. Command line

Each launcher and each button of the launcher page does the same job as one
of these commands. (The browser version does the same jobs in JavaScript; see
`docs/app/README.md`.)

```bash
python3 scripts/eln.py init                                # initials, name, where files live
python3 scripts/eln.py new experiment --title "..."         # add --project, --protocol, --samples, --tags meeting ...
python3 scripts/eln.py new experiment --interactive         # asks questions instead
python3 scripts/eln.py new sample --type plasmid --title "..."
python3 scripts/eln.py validate                            # --strict makes warnings fail too
python3 scripts/eln.py find --status active --project PRMT5-ChromatinRelease
python3 scripts/eln.py report
python3 scripts/eln.py export --project PRMT5-ChromatinRelease --out brief.md
python3 scripts/eln.py export --project PRMT5-ChromatinRelease --format folder   # plain files in Exports/
python3 scripts/eln.py adopt "/path/to/an old folder"       # make it an experiment; files move in unchanged
python3 scripts/eln_web.py                                 # the page, by hand
```

The terminal-window launchers (`New Experiment`, `Check Everything`, and
so on) run the same commands and prompt for the values.

## 9. More than one notebook, or a different folder for one command

`eln.py init --root` sets the notebook the tools use by default.
`AI_ELN_ROOT` in the environment, or `--root` on a command, overrides it for
one shell or one call:

```bash
python3 scripts/eln.py --root "/path/to/another notebook" find --status active
```

A notebook that names its owner in `notebook.md` gives new records that
person's initials, whatever is saved on the computer. `--initials` on a
command overrides both. The tools refuse a `--root` that is not a notebook
but holds notebooks (a lab folder with one folder per person), and name the
notebooks in it.

## Adopting older folders

Work you did before the notebook can be taken in without redoing it.

- **In the browser page:** put the old folder into the notebook folder (into
  `Experiments/`, or next to it) and reload the page. **Home** then shows
  **Adopt older folders**; the Experiments screen always has **Adopt an older
  folder**. The screen lists each folder with a title and start date read
  from its name; correct them and click **Adopt this folder**.
- **From the command line:** `python3 scripts/eln.py adopt "/path/to/old
  folder"`. The folder can be anywhere. `eln.py adopt` with no folder lists
  the ones in the notebook folder that are not records yet. `--copy` leaves
  the original where it is.

The launcher page does not have Adopt; in Safari or Firefox use the command.

Adopting makes an experiment record with the next ID. The old folder is
moved, whole, into the new experiment's `2-data_raw/`. No file in it is
renamed or changed. `1-notes/{ID}_adopted-files.csv` lists every file with
its size and the time it was last modified. The dates in the header come from
the folder name or the file dates, and Results and Interpretation say "Not
written". Open the note, write what the experiment was for, and correct the
title or dates if they are wrong. Folders you do not adopt are left alone.

The record is marked complete, with a snapshot and a manifest of checksums,
unless you tick **Still in progress** (`--status active`). `eln.py find
--tag adopted` lists every adopted experiment.

## Exports

**Export** offers three forms of the same selection (a project, some
experiments, everything active, or everything):

- **One Markdown file**, with a short explanation of the IDs and sections at
  the top. This is the one to paste into, or attach to, an AI chat.
- **A folder of plain files** (browser page and command line) in `Exports/`
  inside the notebook folder: the
  experiments with their files, the protocols, samples, and projects they
  refer to, a `README.md`, `all-notes.md` (the single file above), and an
  index. It is laid out like a notebook, so the page can open it for viewing.
  "The same, without raw data" leaves out what is in `2-data_raw/`. A second
  export on the same day gets `-2` at the end of its name. Copy the folder
  wherever it is needed; it can be deleted afterwards. From the command
  line: `eln.py export --project NAME --format folder [--no-raw] [--out DIR]`.
- **A `.eln` archive**, under "For another electronic notebook", for import
  into eLabFTW, RSpace, Kadi4Mat, PASTA, SampleDB, OpenSemanticLab, or SciLog.

## More on the note's page

These are in the browser page. The launcher page (Safari, Firefox) has the
core jobs only: create, edit, Check, the meeting brief, Export as one file or
`.eln`, Mark complete, and Verify. For the rest, use Chrome or Edge, or the
command line (`eln.py adopt`, `eln.py export --format folder`, `eln.py render`).

- **Repeat this experiment** starts a new experiment with the same title,
  project, type, protocols, and samples. It gets its own ID and today's
  date, and lists the first one as related. Change the title if you like.
- **Print / save as PDF** prints the note with its figures, the list of
  files, the note's checksum, page numbers, and lines for signatures. In the
  print window choose *Save as PDF* to keep a copy.
- **Flag for lab meeting** puts the experiment in the next meeting brief.
  **Remove lab-meeting flag** takes it out again.

## Viewing someone else's notebook

On the first screen of the browser version, click **View a notebook
(read-only)** and choose the folder. If you choose a folder that holds
several notebooks, the page lists them by owner. The page asks only for
permission to view. You can read, search, print, and export; every button that changes
something is hidden. To make a folder view-only for other people no matter
which program they use, share it as *can view* in Dropbox or OneDrive.

## Offline work and sync copies

Dropbox and OneDrive sync files, not edits. If the same file changes on two
computers before they sync, the service keeps one version and saves the
other as a copy, with a name such as `JSRe0004 (Ana's conflicted copy
2026-11-12).md`, `JSRe0004-DESKTOP-AB12CD3.md`, or `JSRe0004 (1).md`.
**Check** lists these copies.

- **Two versions of the same note:** open both, paste anything you need from
  the copy into the original, then delete the copy.
- **A copy of a file in `Inventory/`:** delete the copy. Those files are
  rebuilt from the notes.
- **You created records on two computers while both were offline:** the two
  computers may have given two different experiments the same ID. Do not
  delete either one. Tell whoever looks after the notebook; one of them needs
  a new ID. To avoid this, let the folder finish syncing before you create an
  experiment on a second computer.
- **A folder with no note, or a note with no subfolders:** the folder may
  still be syncing. Wait until Dropbox or OneDrive shows it is up to date and
  run Check again.

`notebook.md` at the top of the notebook folder remembers the last ID given
out for each kind of record. A number written there is not given out again,
even if a folder is deleted. If Check lists a copy of `notebook.md`, records
were created on two computers before they synced: look for two records with
the same ID, then delete the copy.

## If you made an experiment by mistake

Do not delete it and do not reuse its number. Click **Edit here**, change
`status: active` to `status: abandoned`, write one sentence under
**Decision** saying why, and save.

## If something doesn't work

- **Mac: "cannot be opened because it is from an unidentified developer"**:
  right-click → Open (once per launcher), or Privacy & Security → Open Anyway.
- **Mac: double-clicking opens the file in a text editor instead of running
  it**: the executable bit was lost in a download or sync. In Terminal:
  `chmod +x` followed by a space, then drag the `launchers` folder into the
  window, add `/*.command`, press Enter. Or run
  `python3 scripts/eln_web.py` directly.
- **Windows: a window flashes and closes, or "python is not recognized"**:
  install Python (§1) with *Add to PATH* ticked, then try again.
- **The page says "First time here: enter your initials and name"**: click
  the link next to it and enter them.
- **"could not open a port"**: the page tries several port numbers first.
  If you still see this, close the other notebook windows and try again.
- **Check says a folder "does not match {ID}_{slug}"**: a folder in
  `Experiments/` was made or renamed by hand. If it is older work, adopt it
  (see "Adopting older folders"): it gets an ID and its files move in
  unchanged. If it is an experiment folder someone renamed, give it back the
  name that starts with its ID.
- **The browser says it no longer has permission**: click **Reopen** on the
  first screen and allow it again.
- **Check lists a "copy made by a sync service"**: see the next section.
