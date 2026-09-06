# Using AI with the record — without API keys

Everything here runs on subscriptions the lab already has (the ChatGPT
site license, or a Claude plan). There is no server, no vector database,
no key to manage, and nothing to install beyond the AI tool itself.

[`../sandbox/PILOT.md`](../sandbox/PILOT.md) is a transcript of every path
below run against the fictional sandbox record, so you can see what the
answers look like before trying it on real notes.

## Why the record is already AI-ready

Three properties do all the work:

1. **Plain Markdown with a fixed header.** Any model can read it cold. The
   header (`project`, `researcher`, `status`, `samples`, `tags`) lets a
   tool filter before it reads, so a vault of hundreds of notes is still
   navigable.
2. **Fixed section titles.** `## Results` means the same thing in every
   note, so "draft a results paragraph from JSRe0002" is unambiguous.
3. **IDs everywhere.** Every claim the AI makes can name the experiment it
   came from. That is the rule this whole setup exists to enforce: AI is
   for retrieving and citing what the record already says, never for
   producing a conclusion.

## Path A — ChatGPT, copy and paste

Works with the ChatGPT web app or desktop app, no terminal.

1. **Once:** open ChatGPT, create a Project called something like
   *Shechter Lab ELN*, and paste the contents of
   [`ai-briefing.md`](ai-briefing.md) into its instructions. (If your
   ChatGPT doesn't offer Projects or the instruction box is too small,
   paste the briefing as the first message of each new chat instead.)
2. **Each time:** on the page (`launchers/Open ELN`) click **Export**, pick
   a project or all active experiments, click **Copy all**, paste into the
   chat. (Or double-click `launchers/Export for ChatGPT`, which writes the
   same thing to `Inventory/export_<scope>_<date>.md` and opens it.) The
   export contains the selected notes, everything they reference
   (protocols, samples, project page), and a short primer on how to read them.
3. **Ask.** Things that work well:
   - *Summarize what these experiments established, one bullet per
     conclusion, citing experiment IDs. Flag anything based on a single
     experiment.*
   - *Draft the Results paragraph for JSRe0002 using only its Results and
     Interpretation sections.*
   - *Which experiments used sample JSRa0003, and what did each find?*
   - *Write the "Current state" section of the project page from these
     notes.* Then paste the answer into `Projects/<ID>.md` yourself.
   - *What is missing from JSRe0007 before it can be marked complete?*

The export is a snapshot; regenerate it when notes change. If the file is
very large, export one project at a time. What you paste goes to a hosted
model, so apply the same judgement you would to emailing it.

## Path B — Codex CLI

OpenAI's Codex CLI signs in with a ChatGPT account and works directly in a
folder. Open a terminal in this repository (or your synced copy) and start
it. It reads [`AGENTS.md`](../AGENTS.md) automatically: the lab's rules,
the `eln.py` commands, and where the skills are. Then talk to it:

- *Create an experiment for the KCl titration repeat, project
  PRMT5-ChromatinRelease, protocol P_Fractionation.* (It runs `eln.py`,
  never makes a folder by hand.)
- *What do we know about SNRPB retention? Cite experiment IDs.*
- *Update the PRMT5-ChromatinRelease project page from its experiments.*
- *Run the validator and fix the warnings in my notes.*

Skills live in `.agents/skills/` (see below). Codex reads project skills
from the folder its documentation names for your version; if that is
`.codex/skills/`, a symlink or copy of `.agents/skills/` there is enough.

## Path C — Claude Code and Cowork

Claude Code (terminal) and Cowork (desktop) read [`CLAUDE.md`](../CLAUDE.md),
which points at `AGENTS.md`, and pick up the skills in `.agents/skills/`.
Same conversations as Path B. Gemini CLI reads
[`GEMINI.md`](../GEMINI.md) the same way.

## The skills

A skill is a folder with a `SKILL.md`: instructions an agent reads when a
task matches the skill's description. They are plain Markdown, work across
Codex, Claude Code, Cowork, and Cursor, and cost nothing to run. Two groups:

**`.agents/skills/lab/`** — written for this record.

| skill | what it teaches the agent |
|---|---|
| `eln-record-experiment` | create records only through `eln.py`; what goes in each section; file naming; closing out |
| `eln-search-and-cite` | filter with `eln.py find` and the CSV index first; answer with IDs; say when nothing is there |
| `eln-project-synthesis` | rewrite a project page's *Current state* from its experiments, every conclusion cited |

**`.agents/skills/vendor/`** — pinned copies from
[K-Dense's scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills)
(v2.66.0) and [science-superpowers](https://github.com/K-Dense-AI/science-superpowers):
`experimental-design`, `statistical-analysis`, `scientific-writing`,
`citation-management`, `labarchive-integration`, `preregistering-analysis`,
`verifying-results-before-claiming`. These are methodology, not lab rules:
how to lay out a factorial design, which test and effect size to report,
how to write a manuscript section with provenance, how to talk to the
LabArchives API when the archival bridge is built.

They are **pinned, not tracked**. `skills.lock.json` names the upstream
release; `scripts/sync_skills.py` copies exactly those skill folders (a
sparse checkout, about 1 MB, not the 500 MB repository); a weekly GitHub
Action reports when a newer release exists. Updating is a maintainer
running `sync_skills.py --update`, reading `git diff`, and committing. A
skill is instructions an agent will follow against the lab's data, so it
gets reviewed like code. Nothing under `vendor/` is ever hand-edited;
lab-specific behaviour goes in `AGENTS.md` or a `lab/` skill.

## What this deliberately doesn't do

- **No API keys.** Usage is covered by the subscriptions people already
  have; nothing here bills per token.
- **No server, no embeddings index.** Coding agents already search files
  well, and the header fields let them filter first. Revisit when the
  vault is large enough that keyword search misses things
  (`design-notes.md`, *AI integration, in stages*).
- **No editor-specific AI plugins.** The record is files; every tool above
  reads the same files.
- **No AI-written conclusions.** The AI cites; people conclude.
