# Launchers

Double-click these instead of typing commands. Each one runs
`scripts/eln.py` with the right options and asks you questions in plain
language. `.command` files are for Mac, `.cmd` files for Windows.

| Launcher | Does |
|---|---|
| **New Experiment** | Asks for a title (and, optionally, project, type, protocol, samples, notebook page, meeting flag). Creates the folder, the note, a snapshot of the protocol, and re-indexes. Opens the note. First run also asks your initials and name. |
| **New Sample** | Asks type (plasmid, oligo, antibody, ...) and title. Creates `Samples/<ID>.md`. |
| **New Protocol** | Asks a short name. Creates `Protocols/P_<Name>.md`. |
| **New Project** | Asks a short ID. Creates `Projects/<ID>.md`. |
| **Check Everything** | Lists everything that breaks the conventions. `ERROR` = fix; `WARN` = advice. |
| **Lab Meeting Brief** | Writes `Inventory/meeting-brief_<date>.md` from experiments tagged `meeting` and opens it. |
| **Export for ChatGPT** | Asks what to export; writes one file to paste into ChatGPT and opens it. |

## First time

- **Mac:** right-click the launcher → **Open** → **Open**. macOS only asks
  once per launcher. If a dialog offers to install *command line developer
  tools*, accept; that is Python being installed.
- **Windows:** install Python from <https://www.python.org/downloads/> with
  **Add python.exe to PATH** ticked. Then double-click.

## If a `.command` opens in a text editor instead of running

The executable flag was lost (this happens when a folder is downloaded as a
ZIP or synced through some services). Fix once, in Terminal:

```bash
chmod +x launchers/*.command
```

(type `chmod +x `, drag the `launchers` folder into the Terminal window,
add `/*.command`, press Enter). Or just use the terminal commands in
[`../docs/getting-started.md`](../docs/getting-started.md) §7; the
launchers are a convenience, not a requirement.
