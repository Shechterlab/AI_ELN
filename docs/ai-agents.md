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
(release v2.66.0; the library has 160+ skills, these are the ones that
fit this lab) and [science-superpowers](https://github.com/K-Dense-AI/science-superpowers).
They are methodology, not lab rules. Each has two layers: **guidance** (the
`SKILL.md` and its references, which an agent reads and applies with
whatever it has; instant, free) and, in most, **bundled scripts** (optional
helpers that need a Python environment).

| skill | what the agent gets | bundled scripts need |
|---|---|---|
| `statistical-analysis` | which test for which design, assumption checks, effect sizes, the exact reporting format | numpy, pandas, scipy, matplotlib, seaborn |
| `experimental-design` | design types, factorial/DOE layouts, randomization and blocking | Python 3.10+, numpy, pandas, pyDOE3 |
| `scientific-visualization` | truthful, accessible, publication-ready figures; audits of existing ones | Python 3.11+, Matplotlib, Pillow |
| `exploratory-data-analysis` | bounded, provenance-tracked EDA of CSV and table files | Python 3.11+ (standard library) |
| `scientific-writing` | manuscript sections with claim-to-evidence manifests and reporting guidelines | Python 3.11+ (standard library) |
| `scientific-critical-thinking` | evaluating claims and evidence quality | nothing |
| `citation-management` | DOI to BibTeX, PubMed and OpenAlex search, formatting | Python 3.9+, requests, network |
| `paper-lookup` | 11 literature APIs, preprints, open-access full text | Python 3.11+ (standard library), network |
| `scientific-slides` | research-talk decks | see its SKILL.md |
| `pyopenms` | mass-spectrometry proteomics and metabolomics workflows | Python 3.9+, pyopenms 3.5 |
| `pydeseq2` | bulk RNA-seq differential expression | Python 3.11+, pydeseq2 0.5 |
| `pathway-enrichment` | gene-set enrichment and its interpretation | see its SKILL.md |
| `labarchive-integration` | the LabArchives ELN and Inventory APIs, signed requests; for the archival bridge | Python 3.11+, uv, LabArchives Enterprise keys |
| `preregistering-analysis` | lock predictions and decision rules before looking at outcomes | nothing (a shell helper) |
| `verifying-results-before-claiming` | re-run, check, reproduce before repeating a result | nothing |

The guidance layer is what an agent uses most, and it needs nothing:
opened in this folder, Codex or Claude Code reads a skill when a task
matches it. [`../sandbox/PILOT.md`](../sandbox/PILOT.md) §6 shows
`statistical-analysis` guiding a re-analysis of sandbox data that caught a
mismatch between a note's stated p-value and its data file.

**Running a skill's scripts.** They mostly need Python 3.11+ and a package
or two; stock macOS Python is 3.9 with nothing installed. The one tool that
handles both, without touching the system Python, is
[uv](https://docs.astral.sh/uv/): install it once, then run any script
with its dependencies in a throwaway environment:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh          # Mac/Linux, once
uv run --python 3.12 --with numpy --with pandas --with scipy --with matplotlib --with seaborn \
    python .agents/skills/vendor/k-dense-scientific/statistical-analysis/scripts/assumption_checks.py
```

(On Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`.)
`uv` downloads a Python 3.12 and the packages the first time and caches
them; nothing is installed globally. This is also what `AGENTS.md` tells
agents to do. The statistical-analysis script ran unchanged this way in the
pilot.

**Other K-Dense tools, and why they are not wired in.**
[`k-dense-byok`](https://github.com/K-Dense-AI/k-dense-byok) is a desktop
"AI co-scientist" app (TypeScript, needs Node.js) that can run on an
OpenRouter key or, per its configuration file, on a connected ChatGPT
Plus/Pro or Claude subscription; it is a separate application rather than
files, and it has not been tried here. `agentic-data-scientist` and
`claude-scientific-writer` require an Anthropic API key and an OpenRouter
key: metered, so out. `claude-skills-mcp` is deprecated by its authors now
that agents read skills natively. K-Dense Web is their paid hosted product.
The skills are the part that is free, plain text, and portable, which is
why they are the part vendored here.

They are **pinned, not tracked**. `skills.lock.json` names the upstream
release; `scripts/sync_skills.py` copies exactly those skill folders (a
sparse checkout, about 2.5 MB, not the 500 MB repository); a weekly GitHub
Action reports when a newer release exists. Updating is a maintainer
running `sync_skills.py --update`, reading `git diff`, and committing. A
skill is instructions an agent will follow against the lab's data, so it
gets reviewed like code. Nothing under `vendor/` is ever hand-edited;
lab-specific behaviour goes in `AGENTS.md` or a `lab/` skill. To add one of
the other 150 skills (the
[catalogue](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills)
covers most bioinformatics, chemistry, imaging, and database tasks), add
its folder name to `skills.lock.json` and run the sync.

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
