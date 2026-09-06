# Launchers

Double-click these instead of typing commands. `.command` files are for
Mac, `.cmd` files for Windows.

**Start with `Open ELN`.** It opens a page in your web browser with
buttons and forms for everything below: create an experiment, sample,
protocol, or project; browse and read notes (figures included); edit a
note right on the page; run the checker; build the lab-meeting brief;
build the ChatGPT export. It only talks to your own computer (nothing is
uploaded anywhere) and writes the same plain files as everything else.
Leave the small window it opens in the background; closing it stops the
page.

| Launcher | Does |
|---|---|
| **Open ELN** | The page described above, on the lab's record. |
| **Try the Sandbox** | The same page on the fictional practice record in `sandbox/`. Make a mess; `python3 sandbox/rebuild.py` resets it. |
| **New Experiment** | Terminal-window version: asks a few questions, creates the folder, note, and protocol snapshot, opens the note. First run also asks your initials and name. |
| **New Sample** / **New Protocol** / **New Project** | Terminal-window versions of the same forms. |
| **Check Everything** | Lists everything that breaks the conventions. `ERROR` = fix; `WARN` = advice. |
| **Lab Meeting Brief** | Writes `Inventory/meeting-brief_<date>.md` from experiments tagged `meeting` and opens it. |
| **Export for ChatGPT** | Asks what to export; writes one file to paste into ChatGPT and opens it. |

The terminal-window launchers exist for people who prefer them and for
computers where a browser page is awkward; everything they do, the page
does too.

## First time

- **Mac:** right-click the launcher → **Open** → **Open**. macOS only asks
  once per launcher (on the newest macOS the button is instead under
  *System Settings → Privacy & Security → Open Anyway*). If a dialog offers
  to install *command line developer tools*, accept; that is Python being
  installed. None of this happens if the folder arrived by OneDrive sync
  or `git clone` rather than a browser download.
- **Windows:** install Python from <https://www.python.org/downloads/> with
  **Add python.exe to PATH** ticked. Then double-click.

## If a `.command` opens in a text editor instead of running

The executable flag was lost (this happens when a folder is downloaded as a
ZIP or synced through some services). Fix once, in Terminal:

```bash
chmod +x launchers/*.command
```

(type `chmod +x `, drag the `launchers` folder into the Terminal window,
add `/*.command`, press Enter). Or use the terminal commands in
[`../docs/getting-started.md`](../docs/getting-started.md); the launchers
are a convenience, not a requirement.
