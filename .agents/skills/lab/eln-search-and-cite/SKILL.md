---
name: eln-search-and-cite
description: Answer questions about the lab's results from its Markdown research record (AI_ELN), citing experiment IDs for every claim. Use for "what do we know about X", "which experiments used antibody Y", "has anyone tried Z", "when did we last run a fractionation", "summarize what happened with...", or any factual question about past lab work.
---

# Searching the record and citing what you find

Every experiment, protocol, sample, and project is one Markdown file that
starts with a header of `key: value` lines. Filter on the header first,
then read, then answer with IDs.

## 1. Filter before reading

A notebook grows larger than an AI tool can read at once. Use the tool's
filters and the CSV index before opening files:

```bash
python3 scripts/eln.py find --project PRMT5-ChromatinRelease         # by project
python3 scripts/eln.py find --status active --researcher Roth        # by status / person
python3 scripts/eln.py find --sample DSLa0003                        # every experiment that used a sample
python3 scripts/eln.py find --protocol P_WesternBlot                 # every experiment that used a protocol
python3 scripts/eln.py find --type Fractionation --text "KCl"        # by type + free text in title/body
python3 scripts/eln.py find --kind sample --text "SNRPB"             # search samples / protocols / projects
python3 scripts/eln.py find ... --ids                                # IDs only, for scripting
python3 scripts/eln.py find ... --json                               # full headers as JSON
```

The search covers one notebook: the one named with `eln.py init --root`,
with `AI_ELN_ROOT`, or with `--root` on the command. That is one person's
records. To search another person's notebook, run the command again with
`--root` set to that folder.

`Inventory/experiments.csv`, `samples.csv`, `protocols.csv`, `projects.csv`
in the notebook folder are regenerated from the notes and can be read
directly (lists inside a cell are separated by `;`).

Then open only the notes that matched:
`Experiments/{ID}_*/1-notes/{ID}.md` in the notebook folder. Grep works
too. The section headings are fixed (`## Results`, `## Interpretation`),
so `grep -A20 "## Results"` across notes works.

## 2. Answer with IDs

- Every factual claim about a result names the experiment ID(s) it comes
  from: "SNRPB retention increased with KCl up to 300 mM (JSRe0002); this
  was not replicated (no related experiment marked complete)."
- Quote or closely paraphrase the note's own Results / Interpretation.
  Don't upgrade a hedged interpretation into a firm conclusion.
- One experiment is preliminary. Say so unless a note records replication
  (`related_experiments`, or a project page listing it under *Supported
  conclusions* with multiple IDs).
- If the notes don't contain the answer, say that. Do not fill the gap
  with what would be plausible. "Nothing in the record addresses X" is a
  correct and useful answer.
- Where it helps, give the path so the person can open the note.

## 3. Things to know about the IDs

- `JSRe0002` = experiment; `JSRp0001` plasmid, `JSRi` oligo, `JSRa`
  antibody, `JSRc` cell line, `JSRm` mouse line, `JSRt` peptide, `JSRr`
  protein prep, `JSRs` slide, `JSRg` gel; `P_WesternBlot` = protocol;
  projects are named. The initials are the researcher.
- An ID written anywhere in a note is a reference to that record.
- An experiment or sample ID with initials other than the notebook
  owner's (`ALXc0001` in a note of `JOR`) is a record in that person's
  notebook. It is not in this folder and it is not missing. If you cannot
  read that notebook, say that the record is in the other person's
  notebook and that you have not read it.
- `status` is `active | complete | paused | abandoned`. Weight `complete`
  notes over `active` ones when summarizing what is known.

## Don'ts

- Don't search or cite `sandbox/`. It holds two fictional practice
  notebooks (`sandbox/alex`, `sandbox/jordan`). `eln.py find` does not
  look there unless `--root` points at one of them, and a grep should not
  either, unless the person asked to work in the sandbox.
- Don't search or cite `Exports/` in a notebook. Those folders are copies
  written by Export; cite the notes they were copied from. `eln.py find`
  does not look there. A grep does, so leave `Exports/` out of it.
- Don't modify notes while answering a question. Searching is read-only.
- Don't invent an experiment, number, figure, or reagent that isn't in a note.
- Don't summarize from the CSV alone when the question is about *what was
  found*. The CSV has the header fields; the note has the result.
