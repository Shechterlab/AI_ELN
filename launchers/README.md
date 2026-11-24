# Launchers

Double-click these instead of typing commands. `.command` files are for
Mac, `.cmd` files for Windows. They need Python.

Each launcher runs one of the Python tools from the tools folder (the
folder that contains `launchers/`). `Open ELN` and `Try the Sandbox` start
a page in your web browser; the others run in a terminal window. They work
on the notebook folder you named once with
`python3 scripts/eln.py init --root "/path/to/notebook"`. If you named
none, they keep the records in the tools folder itself. `Try the Sandbox`
is the exception: it always opens `sandbox/alex`.

In Chrome or Edge you do not need a launcher: the browser page at
<https://shechterlab.github.io/AI_ELN/app/> opens the notebook folder
itself. Safari and Firefox cannot open folders, so there the page is
started by `Open ELN`.

**Start with `Open ELN`.** It runs `scripts/eln_web.py` and opens the
launcher page in your web browser. The page has buttons and forms to
create an experiment, sample, protocol, or project; to list and read notes
with their figures; to edit a note; and for **Check**, **Meeting brief**,
**Export** (one file to paste into a chat, or a `.eln` archive for other
electronic notebooks), **Mark complete**, and **Verify files**. The page is
served from your own computer (its address starts with `127.0.0.1`) and
nothing is uploaded. It writes the same plain files as the other tools.
Leave the small window it opens in the background; closing it stops the
page.

The launcher page does not have these jobs: **Adopt older folders**, **Add
files**, **Repeat this experiment**, **Print / save as PDF**, **Flag for
lab meeting**, **View a notebook (read-only)**, and the export as a folder
of plain files. They are in the browser page (Chrome or Edge). The command
line has three of them: `eln.py adopt`, `eln.py export --format folder`,
and `eln.py render`, which writes a note as one HTML file that can be
printed.

| Launcher | Does |
|---|---|
| **Open ELN** | Opens the launcher page on your notebook. |
| **Try the Sandbox** | Opens the same page on `sandbox/alex`, a fictional practice notebook. Change anything in it; `python3 sandbox/rebuild.py` puts it back. |
| **New Experiment** | In a terminal window: asks a few questions, creates the folder, the note, and the protocol copy, and opens the note. The first run also asks for your initials and name. |
| **New Sample** / **New Protocol** / **New Project** | The same in a terminal window for a sample, a protocol, or a project. |
| **Check Everything** | Lists what breaks the conventions. An `ERROR` must be fixed; a `WARN` is advice. |
| **Lab Meeting Brief** | Writes `Inventory/meeting-brief_<date>.md` from experiments tagged `meeting` and opens it. |
| **Export for ChatGPT** | Asks what to export, writes one file to paste into ChatGPT (`Inventory/export_<scope>_<date>.md`), and opens it. |

The launcher page does everything the terminal-window launchers do. They
are there for people who prefer them and for computers where a browser
page is awkward to use.

## First time

- **Mac:** right-click the launcher → **Open** → **Open**. macOS asks
  once per launcher (on the newest macOS the button is under *System
  Settings → Privacy & Security → Open Anyway*). If a dialog offers to
  install *command line developer tools*, accept; that installs Python.
  macOS does not ask if the folder arrived by OneDrive sync or `git clone`
  and was not downloaded with a browser.
- **Windows:** install Python from <https://www.python.org/downloads/> with
  **Add python.exe to PATH** ticked. Then double-click.

## If a `.command` opens in a text editor instead of running

The file has lost the setting that marks it as a program. Dropbox keeps
that setting on Mac; a ZIP download or some other sync services may not.
Fix it once, in Terminal:

```bash
chmod +x launchers/*.command
```

(type `chmod +x `, drag the `launchers` folder into the Terminal window,
add `/*.command`, press Enter). Or use the terminal commands in
[`../docs/getting-started.md`](../docs/getting-started.md), which do
everything the launchers do.
