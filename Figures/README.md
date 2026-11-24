# Figures

In a notebook, `Figures/` holds one folder per assembled figure: a figure for
a paper, a grant, or a talk, usually with several panels from several
experiments. The result figure of a single experiment does not go here; it
stays in that experiment's `5-figures/`.

Create one with **New figure** on the page or
`python3 scripts/eln.py new figure --title "..." --experiments JSRe0002,JSRe0005`.
It gets an ID such as `JSRf0001` and this folder:

```
Figures/JSRf0001_short-title/
  1-notes/     JSRf0001.md: the figure note
  2-panels/    one file per panel: JSRf0001_a_what-it-shows.pdf
  3-source/    the file the figure is laid out in, in any program
  4-exports/   the finished figure, one file per version
```

The note has a **Panels** table with one row per panel: what it shows, the
experiment it came from, the data file that was plotted, what drew it, and
the panel file. It does not matter which program made the figure. The table
is what lets someone trace a panel back to an experiment.

Which figures use an experiment: `Inventory/figures.csv`, or
`python3 scripts/eln.py find --kind figure --experiment JSRe0002`.

This copy of the folder, in the tools folder, is empty unless the tools
folder itself is used as the notebook.
