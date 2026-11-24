# Projects

In a notebook, `Projects/` holds one Markdown file per project, made from
[`templates/project.md`](../templates/project.md). Create one with **New
project** on the page, `launchers/New Project`, or
`python3 scripts/eln.py new project --id PRMT5-ChromatinRelease --title "..."`.

A project page is a summary of where one research project stands now:
supported conclusions, open questions, what needs replication, and
reagents in use. Every conclusion cites the experiment IDs that support
it. The page refers to experiments, protocols, and samples by ID and does
not repeat their content. When the state changes, rewrite **Current
state**; do not add to the end of it.

An experiment belongs to a project when its header (the `key: value` lines
at the top of the note) lists the project:
`project: [PRMT5-ChromatinRelease]`. The current list of a project's
experiments is in `Inventory/projects.csv`, or run
`python3 scripts/eln.py find --project PRMT5-ChromatinRelease`.

An AI agent can draft the *Current state* section from the experiments
(skill `eln-project-synthesis`); a person reads it before it goes in.

This copy of the folder, in the tools folder, is empty unless the tools
folder itself is used as the notebook.
