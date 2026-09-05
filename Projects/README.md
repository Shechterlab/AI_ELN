# Projects

One Markdown file per project, from [`templates/project.md`](../templates/project.md).
Create one with `launchers/New Project` or
`python3 scripts/eln.py new project --id PRMT5-ChromatinRelease --title "..."`.

A project page is the rolled-up, continuously updated state of a research
thread: supported conclusions, open questions, what needs replication,
reagents in use — every conclusion citing the experiment IDs that back it.
It links out to experiments, protocols, and samples; it doesn't duplicate
their content. Update **Current state** in place rather than appending.

Experiments join a project by listing it in their header:
`project: [PRMT5-ChromatinRelease]`. The live list is
`Inventory/projects.csv` or `python3 scripts/eln.py find --project PRMT5-ChromatinRelease`.

An AI agent can draft the *Current state* section from the experiments
(skill `eln-project-synthesis`); a person reads it before it goes in.
