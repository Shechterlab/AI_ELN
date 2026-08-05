# Inventory

`experiments.csv` is the lab-wide index — one row per experiment, appended
automatically by `scripts/new_experiment.py`. This is the direct
descendant of Jacob's `InventorySheet_jsr.xlsx` `NB-Index` sheet
(see [`reference/jacob-original-system/`](../reference/jacob-original-system/)),
generated from the Markdown notes instead of maintained by hand.

Don't hand-edit rows other than `status` and `date_completed`-style
bookkeeping — the experiment note is the source of truth; this CSV is a
derived view for sorting, filtering, and building dashboards (a
"which experiments are still active" report, an Rmd check-in doc like
Jacob's, a Dataview table in Obsidian, etc.).
