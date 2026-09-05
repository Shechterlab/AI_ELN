---
name: eln-project-synthesis
description: Rewrite a project page's "Current state" section from the experiments in the lab's Markdown research record (AI_ELN), every conclusion citing experiment IDs. Use for "summarize project X", "update the project page", "what's the state of the PRMT5 work", "prepare the project overview for the grant".
---

# Synthesizing a project page

A project page (`Projects/{ID}.md`) is the rolled-up, always-current state
of one research thread. It is *derived* from experiment notes - it never
contains a claim that isn't backed by an experiment ID.

## 1. Gather

```bash
python3 scripts/eln.py find --project {PROJECT_ID}            # every experiment in the project
python3 scripts/eln.py find --project {PROJECT_ID} --status complete
```

Read `Projects/{PROJECT_ID}.md` and every matching experiment note in full
(`Experiments/{ID}_*/1-notes/{ID}.md`), paying most attention to
`## Results`, `## Interpretation`, and `## Decision`.

## 2. Rewrite "Current state" in place

Replace the contents of the three subsections under `## Current state`.
Do not append a dated copy below the old one; the page is the current
state, and git history keeps the old versions.

**Supported conclusions** - one line each, only where at least one
`complete` experiment supports it, citing every supporting ID:

```
- PRMT5 inhibition increases SNRPB chromatin retention in A549 cells (JSRe0002, JSRe0007).
```

**Open questions / conflicting observations** - where experiments disagree,
where an `active` experiment is still running, or where an interpretation
is explicitly hedged. Cite IDs on both sides.

**Experiments needing replication** - every conclusion that rests on a
single experiment. Name the experiment.

## 3. Keep the rest short

- `## Experiments`: one line per key experiment (ID - title - status).
  The exhaustive list is `Inventory/projects.csv`; don't duplicate it.
- `## Reagents in use`: sample IDs the project depends on, from the
  experiments' `samples` fields.
- `## Related protocols`: protocol IDs from the experiments' `protocols`.

## 4. Check

Run `python3 scripts/eln.py validate` afterwards. Then tell the person, in
two or three sentences, what changed and which conclusions are
single-experiment.

## Don'ts

- Don't edit experiment notes while synthesizing. If a note is unclear,
  say so in *Open questions* and ask.
- Don't promote an `active` or `paused` experiment's early observations to
  a supported conclusion.
- Don't write a conclusion without an ID after it.
