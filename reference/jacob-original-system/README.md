# Reference: Jacob Roth's original system

These are the source materials this whole repo is built from. Jacob (PhD student,
Shechter Lab) independently solved the hard part of a lab notebook — a coherent
ID and folder scheme that links a physical notebook page to raw data, analysis,
figures, and a written interpretation — using nothing but folder names, a
spreadsheet, and an R Markdown file. Everything in `../../templates`,
`../../scripts`, and `../../docs` is a direct translation of these ideas into
Markdown + YAML.

Kept here unmodified, for provenance:

| File | What it is |
|---|---|
| `20251119_DataManagement_JSR.pptx` | Jacob's slide deck walking through his system |
| `InventorySheet_jsr.xlsx` | His master experiment index (`NB-Index` sheet) — one row per experiment, with a pre-built `mkdir -p ... {1-notes,2-data_raw,3-code,4-data_processed,5-figures}` command in the last column |
| `ProjectOverviewAndDataPresentationFile.Rmd` / `.pdf` | His "living document" — an R Markdown file that knits together only the experiments flagged `active` in the inventory into a PI check-in report |
| `JSRe0002-R_FractionationA549-PRMTi-KCl-Titration_20230204.png` | Example results figure, named with his `JSRe####-R_...` convention |

## The naming system, as Jacob wrote it

- **`JSRe####-T_`** — the "Top" folder for an experiment. Search `JSRe####-T` to jump straight to it.
- **`JSRe####-R_`** — the "Results" file. Search `JSRe####-R` to jump straight to the summary, which also carries the notebook page reference (`NB##-###`) back to the physical page.
- **`JSRg###`** — every gel/blot ever run (agarose, Western, Coomassie), one ID each.
- **`JSRp###`** — every plasmid.
- **`JSRi###`** — every oligo (primers, DNA/RNA sequences).
- **`JSRs####`** — immunofluorescence slides, cross-referenced to a metadata spreadsheet.
- **`JSRe####-I_`** — the Illustrator file for an experiment's figure.
- **`JSRe####-G_`** — the GraphPad Prism file for a project.
- **`P_...`** — protocols, kept as one living/updated file per protocol, with dated archive copies; copied into an experiment's `1-notes/` and renamed `JSRe####-P_...` when actually used.

The prefix (`JSR`) is just Jacob's initials — the new system in this repo keeps
the same shape but makes the prefix per-researcher (see `../../templates` and
`../../scripts/eln.py`).
