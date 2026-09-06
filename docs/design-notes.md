# Design notes: why this is shaped the way it is

This explains the reasoning behind the system in this repo. If you just
want to use it, see [`getting-started.md`](getting-started.md) instead;
this document is for when you're curious, or deciding whether to change
something.

## The decision this repo makes

There were three tempting, wrong defaults: adopt an ELN app or an editor
plugin wholesale, keep using LabArchives as the daily working tool, or
"just use folders" with no conventions. This repo does none of them:

> **Jacob's experiment-centric model + plain Markdown files with a small
> header + a tool that enforces the naming + institutional storage for
> data + LabArchives as the archival record.**

```mermaid
flowchart LR
    subgraph Daily["Daily work"]
        A["Experiment note<br/>(Markdown + header)"]
        B["Raw / processed data<br/>(institutional storage)"]
        C["Protocols, Samples,<br/>Projects (Markdown)"]
        V["eln.py validate<br/>(keeps the conventions honest)"]
    end
    subgraph Archive["At completion"]
        D["Rendered snapshot<br/>(PDF/HTML)"]
        E["LabArchives entry<br/>(timestamped, audited)"]
    end
    A -- links to --> B
    A -- references --> C
    V -.checks.- A
    A -- "on status: complete" --> D --> E
```

## What Jacob's system already solved

Every experiment gets, from the start: a unique ID, a standardized folder
(`1-notes / 2-data_raw / 3-code / 4-data_processed / 5-figures`), explicit
separation of raw vs. processed data, stable IDs for recurring physical
objects (gels, plasmids, oligos, slides), and a short results summary
written while the experiment is still fresh and findable with one search
(`JSRe####-R`). That's the hard part of an ELN — the information
architecture — and it was solved with a spreadsheet and a folder-naming
convention, not software. See
[`reference/jacob-original-system/`](../reference/jacob-original-system/).

This repo's job is narrower than it sounds: **represent that structure in
Markdown with a header, and enforce it with a tool**, so it becomes
searchable, linkable, and AI-readable without asking anyone to give up
the parts that already work.

## Conventions are the product

The metadata and the naming grammar are what everything else hangs on.
Three decisions follow from taking that seriously:

- **The header is a flat YAML subset** (`key: value`, `key: [a, b]`,
  nothing nested). It's parseable by `grep`, by ten lines of R or Python,
  by every YAML library, and by a language model reading a file cold.
  Every "we'll just add a nested field" would cost that.
- **IDs are the links.** A bare `JSRe0002` anywhere means that experiment.
  No wiki-link syntax, no paths, no editor feature required; the validator
  resolves them.
- **The tool assigns IDs and enforces the rules; it doesn't own the
  files.** `eln.py` is a few hundred lines of dependency-free Python. If it
  vanished, the files would still be a complete, readable record, and the
  one-page [`CONVENTIONS.md`](CONVENTIONS.md) is enough to rewrite it.

The validator (`eln.py validate`) is where "convention" becomes
"enforcement" — but as advice, run when you choose, with errors reserved
for things that actually break the system (a misnamed folder, a duplicate
ID) and warnings for everything else. Nothing blocks you from writing.

## Why flat files and not an app

Friction is the enemy. Every ELN the lab has tried was abandoned not
because it couldn't store things but because putting things in it felt
like work. Plain files in plain folders are the lowest-friction store
there is: Finder and Explorer are the interface, any text editor writes
the notes, and there is nothing to log into, update, or migrate. An editor
that renders Markdown nicely (VS Code, Typora, Obsidian if someone likes
it) is a view on the same files, not a requirement, and this repo avoids
editor-specific syntax so nobody is locked to one.

The cost of flat files is that nothing stops you from misnaming a folder,
and that "open the .md file" is a real barrier for some people. That's
exactly what the local web page (a form; you don't name anything; the tool
does; you can write the note on the page) and the validator (it tells you
when something's off) are for. The page owns nothing: stop it and the files
are exactly as they were.

## Data lives outside the notebook

The record should contain Markdown, small tables, compressed
representative images, protocol snapshots, and analysis code. It should
not contain microscopy datasets, sequencing files, mass spec output, or
Illustrator/Prism source files duplicated across locations. Text and code
belong in files people sync and diff; large binaries belong on
institutionally backed-up storage, with the experiment note recording the
canonical path (`raw_data_path`).

A per-experiment manifest (which raw file produced which processed file
produced which figure, with checksums) is what makes "what data supports
this figure" answerable later. This repo doesn't build it yet (Phase 4).

## The role of LabArchives

LabArchives is kept, but demoted from working environment to archival
layer. What it provides — institutional authentication, controlled
permissions, audit trails, timestamps, a defensible record — has nothing
to do with day-to-day usability, and its interface cost shouldn't be paid
for every note. Intended flow:

1. Work happens in Markdown, all week, with zero LabArchives interaction.
2. When an experiment is `status: complete`, its note is rendered to
   PDF/HTML and deposited in LabArchives under the same experiment ID.
3. LabArchives is a timestamped snapshot; Markdown stays the actively
   edited source of truth.

One-directional by design (Markdown → LabArchives, never back).
Bidirectional sync creates ambiguity about which copy is authoritative; a
snapshot doesn't. The bridge isn't built yet: it needs institutional API
access enabled first. When it is, the vendored `labarchive-integration`
skill (`.agents/skills/vendor/`) already documents the signed-request
flow, regional endpoints, and the ELN vs. Inventory API split.

## Collaboration model

The simplest deployment is one shared folder (OneDrive/SharePoint or a
server mount) containing everything — this repo's tooling and the
`Experiments/`, `Protocols/`, `Samples/`, `Projects/` folders — synced to
each person's machine. Per-researcher initials mean two people can create
experiments at the same time without a central counter. `eln.py init
--root` supports the alternative where notes live in a separate location
from the tooling.

Where it makes sense to split: protocols, samples, project pages, and
completed experiments are shared; in-progress notes can be personal until
completion. Sync goes through institutionally managed storage or a
private institutional git host, not a public repository.

## AI integration, in stages

AI is valuable here because the header is structured enough to filter
before reading, the sections are fixed enough to ask precise questions
about, and every claim can cite an experiment ID instead of floating free.
The rule throughout: **AI retrieves and cites; people conclude.**

1. **Grounded assistants, no infrastructure** — *built.* `AGENTS.md` gives
   any coding agent (Codex, Claude Code, Cowork, Gemini CLI) the lab's
   rules the moment it's opened in the folder; `.agents/skills/lab/` teaches
   the three recurring tasks (record, search-and-cite, synthesize); `eln.py
   export` plus `docs/ai-briefing.md` do the same for plain ChatGPT by copy
   and paste. No API keys — everything runs on subscriptions the lab has.
   Pinned methodology skills from K-Dense add design, statistics, writing,
   and citation guidance; see [`ai-agents.md`](ai-agents.md).
2. **Lab-wide search** — `eln.py find` and the CSV index cover filtering
   by every header field plus free text today. A semantic index only earns
   its keep when keyword search starts missing things; revisit at a few
   hundred notes.
3. **Automated project synthesis** — the `eln-project-synthesis` skill
   drafts *Current state*; a person reviews before it lands. Scheduling it
   (nightly, per project) is a small step once the pilot has notes.
4. **Instrument/data ingestion** — scripts that watch a drop folder,
   checksum and rename files by experiment ID, and write the manifest.
   Start with Western blots or microscopy.

Deliberately in that order: AI can't fix inconsistent IDs or missing
metadata, only compound them, so the conventions and the validator came
first.

## What this repo builds now vs. later

**Now (Phase 1):** conventions, the four templates, `scripts/eln.py`
(create, validate, index, find, report, export), a local web page
(`scripts/eln_web.py`) so nobody needs a terminal or a Markdown editor, the
double-click launchers, a fictional sandbox to practice on, the agent
instruction files and skills, tests on three operating systems. Enough for
a pilot to run on.

**Later:** *Phase 2* — lab-wide rollout with the SOP once the pilot's kinks
are out. *Phase 3* — the LabArchives bridge (needs institutional API
access). *Phase 4* — ingestion and manifests; a semantic index if the vault
outgrows `find`.

## Non-negotiables vs. flexible choices

**Required:** experiment ID, project, researcher, date, objective, raw-data
location, protocol, results, interpretation, status; files named with the
ID; raw data untouched.

**Flexible:** daily-note style, prose vs. bullets, how many images, which
editor, which analysis tool (R/Python/Prism/whatever), personal task
management.

The system standardizes the interface between experiments, not how any one
person thinks or writes.
