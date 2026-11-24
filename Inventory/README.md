# Inventory

In a notebook, `Inventory/` holds the index: five tables that the tools
make from the notes. Do not edit them by hand. Edit the note instead. The
tools rebuild the index each time they create or change a record; after
editing a note in another program, run `python3 scripts/eln.py index`.

| file | one row per | includes |
|---|---|---|
| `experiments.csv` | experiment | id, title, researcher, project, type, protocols, samples, notebook page, dates, status, tags, folder |
| `samples.csv` | sample | id, type, title, source, storage, date, status, **which experiments used it** |
| `protocols.csv` | protocol | id, title, version, status, **which experiments used it** |
| `projects.csv` | project | id, title, lead, status, date, **its experiments** |
| `figures.csv` | figure | id, title, label, researcher, project, experiments, target, tools, dates, status, tags, folder |

The "which experiments" columns are worked out from the experiment notes
each time the index is rebuilt. Lists inside a cell are separated by `;`.

Open the tables in Excel or Numbers to sort and filter, or read them in R
with `read.csv`. They take the place of the `NB-Index` sheet in Jacob
Roth's `InventorySheet_jsr.xlsx`
([`reference/jacob-original-system/`](../reference/jacob-original-system/)).
That sheet was kept up by hand next to the notes; these tables are made
from the notes.

The meeting brief and the single-file exports are saved here too:

- `meeting-brief_<date>.md`, from **Lab meeting brief** on the page or the
  *Lab Meeting Brief* launcher;
- `export_<scope>_<date>.md`, the one Markdown file to paste into an AI
  chat, from **Export** on the page or the *Export for ChatGPT* launcher;
- `export_<scope>_<date>.eln`, the archive for other electronic notebooks,
  from **Export**.

Each of these is a copy made on that date. Do not edit one; make a new
one. The export as a folder of plain files goes into `Exports/`.

This copy of the folder, in the tools folder, holds empty tables unless
the tools folder itself is used as the notebook.
