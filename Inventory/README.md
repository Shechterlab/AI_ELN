# Inventory

Generated. Don't edit these by hand; edit the note and run
`python3 scripts/eln.py index` (every `new ...` command does it for you).

| file | one row per | includes |
|---|---|---|
| `experiments.csv` | experiment | id, title, researcher, project, type, protocols, samples, notebook page, dates, status, tags, folder |
| `samples.csv` | sample | id, type, title, source, storage, date, status, **which experiments used it** |
| `protocols.csv` | protocol | id, title, version, status, **which experiments used it** |
| `projects.csv` | project | id, title, lead, status, date, **its experiments** |

The "which experiments" columns are computed from the experiment notes, so
they are always right. Lists inside a cell are separated by `;`.

Open them in Excel or Numbers to sort and filter; read them from R with
`read.csv`; feed them to a dashboard. This is the direct descendant of
Jacob's `InventorySheet_jsr.xlsx` `NB-Index` sheet
([`reference/jacob-original-system/`](../reference/jacob-original-system/)),
now derived from the notes instead of maintained alongside them.

`meeting-brief_<date>.md` and `export_<scope>_<date>.md` files also land
here when you use the *Lab Meeting Brief* and *Export for ChatGPT*
launchers. They are snapshots; regenerate rather than edit.
