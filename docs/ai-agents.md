# Using AI with the record, without API keys

Everything here runs on subscriptions the lab already has (the ChatGPT
site license, or a Claude plan). There is no server to maintain, no
separate search database, and no key to manage. Nothing is installed
except the AI tool itself (and Node, for Path D).

[`../sandbox/PILOT.md`](../sandbox/PILOT.md) is a transcript of a Claude
Code session and an export, run on the fictional sandbox data. It shows what
the answers look like before you try this on real notes.

## What to ask

You do not need to know a skill's name. Ask for the task, and the agent
reads the skill that matches. The table lists requests that are useful in
this lab and where each one works. "Codex / Claude Code" means an agent
opened in the tools folder, which can read files and run scripts. "ChatGPT"
means the pasted export: ChatGPT can reason about the notes, but it cannot
see the data files or run anything. "Both" means either.

| You want | Say something like | Skills it uses | Works in |
|---|---|---|---|
| Check that a Results section matches its data | *Re-analyse `4-data_processed/JSRe0007_quant.csv` the way the note describes and tell me whether the numbers in Results match.* | `statistical-analysis`, `verifying-results-before-claiming` | Codex / Claude Code |
| Report a test properly | *Which test fits this design? Write the Results sentence in the standard format with effect size and CI.* | `statistical-analysis` | both |
| Audit the lab-meeting figure | *Check `5-figures/JSRe0007_R_....png` against the figure checklist: axes, colour, what it can and cannot support.* | `scientific-visualization` | Codex / Claude Code |
| Draft a paragraph from a note | *Draft the Results paragraph for JSRe0007 from its Results and Interpretation only, experiment ID after each claim.* | `scientific-writing`, `eln-search-and-cite` | both |
| Push back on an interpretation | *What would falsify the Interpretation in JSRe0007? What is the strongest alternative explanation?* | `scientific-critical-thinking` | both |
| Plan before starting | *Lay out the design for a 3-condition, 3-replicate fractionation and write the pre-registration: predictions and the decision rule.* | `experimental-design`, `preregistering-analysis` | both |
| Ground a project page in the literature | *Find recent papers on PRMT5 and snRNP chromatin release and add them, with DOIs, to the project page's references.* | `paper-lookup`, `citation-management` | Codex / Claude Code |
| Turn the meeting brief into slides | *Make a five-slide deck from `Inventory/meeting-brief_20260912.md`.* | `scientific-slides` | Codex / Claude Code |
| Start an RNA-seq or mass-spec analysis | *Set up the DESeq2 analysis for ALXe0004, DMSO vs PRMT5i, three vs three.* | `pydeseq2`, `pathway-enrichment`, `pyopenms` | Codex / Claude Code, with `uv` |

The same list is on the page under **Ask the AI**, and four of the requests
are on the cheat sheet. Try the first three rows first: they check work
that already exists. Check each answer against the note and its data file.

## Why AI tools can read the notes

AI tools rely on three properties of the record:

1. **Plain Markdown with a fixed header.** Any model can read it without
   preparation. The header (`project`, `researcher`, `status`, `samples`,
   `tags`) lets a tool filter before it reads, so it can find the right
   notes among hundreds.
2. **Fixed section titles.** `## Results` means the same thing in every
   note, so "draft a results paragraph from JSRe0002" has one meaning.
3. **IDs everywhere.** Every claim the AI makes can name the experiment it
   came from. In every path below the AI retrieves and cites what the
   record says, and people draw the conclusions.

## Path A: ChatGPT, copy and paste

Works with the ChatGPT website or desktop app. No terminal is needed.

1. **Once:** open ChatGPT, create a Project called something like
   *Shechter Lab ELN*, and paste the contents of
   [`ai-briefing.md`](ai-briefing.md) into its instructions. (If your
   ChatGPT doesn't offer Projects or the instruction box is too small,
   paste the briefing as the first message of each new chat instead.)
2. **Each time:** on the page, click **Export**, choose one project or all
   active experiments, click **Build export**, then **Copy all**, and paste
   into the chat. (Or double-click `launchers/Export for ChatGPT`, which
   writes the same text to `Inventory/export_<scope>_<date>.md` and opens
   it.) The export contains the selected notes, the records they refer to
   (protocols, samples, project page), and a short explanation of how to
   read them.
3. **Ask.** Examples:
   - *Summarize what these experiments established, one bullet per
     conclusion, citing experiment IDs. Flag anything based on a single
     experiment.*
   - *Draft the Results paragraph for JSRe0002 using only its Results and
     Interpretation sections.*
   - *Which experiments used sample JSRa0003, and what did each find?*
   - *Write the "Current state" section of the project page from these
     notes.* Then paste the answer into `Projects/<ID>.md` yourself.
   - *What is missing from JSRe0007 before it can be marked complete?*

The export is a copy made at one moment. Make a new one when the notes
change. If the export is too long for one chat, export one project at a
time. What you
paste goes to a hosted model, so use the same judgement as you would for
sending it by email.

## Path B: Codex CLI

OpenAI's Codex CLI signs in with a ChatGPT account and works in a folder on
your computer. Open a terminal in the tools folder (this repository) and
start it. It works on the notebook you named with
`python3 scripts/eln.py init --root "/path/to/notebook"`. When it starts it
reads [`AGENTS.md`](../AGENTS.md): the lab's rules, the `eln.py` commands,
and where the skills are. Then type requests:

- *Create an experiment for the KCl titration repeat, project
  PRMT5-ChromatinRelease, protocol P_Fractionation.* (It runs `eln.py`,
  never makes a folder by hand.)
- *What do we know about SNRPB retention? Cite experiment IDs.*
- *Update the PRMT5-ChromatinRelease project page from its experiments.*
- *Run Check and fix the warnings in my notes.*

The skills are in `.agents/skills/` (see below). Codex reads project skills
from the folder that its documentation names for your version. If that is
`.codex/skills/`, a link to `.agents/skills/` or a copy of it there is
enough.

## Path C: Claude Code and Cowork

Claude Code (terminal) and Cowork (desktop) read [`CLAUDE.md`](../CLAUDE.md),
which points at `AGENTS.md` and at the skills in `.agents/skills/`. Open
them in the tools folder as well. The requests are the same as in Path B.
Gemini CLI reads [`GEMINI.md`](../GEMINI.md) the same way.

## Path D: MCP

MCP (the [Model Context Protocol](https://modelcontextprotocol.io)) is a
way for AI programs to call tools. The notebook's operations are available
as MCP tools: create an experiment, find and read notes, write a section,
check the conventions, mark complete, export. The server is
`node mcp/server.mjs` (Node 18 or later, no other dependency), and the AI
program starts it. It runs on your computer, opens no network port, and
reads and writes only inside the notebook folder.

Claude Code and Cowork find it through `.mcp.json` when opened in the tools
folder, and ask before using it. It works on the notebook named with
`init --root`. Codex, Claude Desktop, and other clients need one entry in
their configuration; the lines are in [`mcp/README.md`](../mcp/README.md).
With `--read-only` the server offers only the tools that change nothing.

This is useful when the assistant should create or update records, since
the tools apply the naming rules themselves. It is not required: an agent
opened in the tools folder (Paths B and C) can already read the notes and
run `scripts/eln.py`. ChatGPT on the web cannot reach a server on your
computer, so Path A stays copy and paste.

## The skills

A skill is a folder with a `SKILL.md`: instructions that an agent reads
when a task matches the skill's description. Skills are plain Markdown,
work in Codex, Claude Code, Cowork, and Cursor, and cost nothing to use.
There are two groups.

**`.agents/skills/lab/`**: written for this record.

| skill | what it teaches the agent |
|---|---|
| `eln-record-experiment` | create records only through `eln.py`; what goes in each section; file naming; closing out |
| `eln-search-and-cite` | filter with `eln.py find` and the CSV index first; answer with IDs; say when nothing is there |
| `eln-project-synthesis` | rewrite a project page's *Current state* from its experiments, every conclusion cited |

**`.agents/skills/vendor/`**: copies from
[K-Dense's scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills)
(release v2.66.0; the library has more than 160 skills, and these are the
ones that fit this lab) and
[science-superpowers](https://github.com/K-Dense-AI/science-superpowers),
each kept at one fixed version. They describe methods and are not lab
rules. Each has guidance: the `SKILL.md` and its reference files, which an
agent reads and applies, and which need nothing installed. Most also have
bundled scripts: optional helpers that need a Python environment.

| skill | what the agent gets | bundled scripts need |
|---|---|---|
| `statistical-analysis` | which test for which design, assumption checks, effect sizes, the reporting format | numpy, pandas, scipy, matplotlib, seaborn |
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

The guidance is what an agent uses most. Opened in the tools folder, Codex
or Claude Code reads a skill when a task matches it.
[`../sandbox/PILOT.md`](../sandbox/PILOT.md) §6 shows
`statistical-analysis` guiding a re-analysis of sandbox data that caught a
mismatch between a note's stated p-value and its data file.

**Running a skill's scripts.** Most need Python 3.11 or later and one or
more packages. The Python that comes with macOS is 3.9 and has no packages.
[uv](https://docs.astral.sh/uv/) handles both without changing the system
Python. Install it once, then run any script with its packages in a
temporary environment:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh          # Mac/Linux, once
uv run --python 3.12 --with numpy --with pandas --with scipy --with matplotlib --with seaborn \
    python .agents/skills/vendor/k-dense-scientific/statistical-analysis/scripts/assumption_checks.py
```

(On Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`.)
`uv` downloads Python 3.12 and the packages the first time and keeps them
for later runs. Nothing is installed globally. `AGENTS.md` tells agents to
run scripts this way. The statistical-analysis script ran unchanged this
way in the pilot.

**Other K-Dense tools, and why they are not used here.**
[`k-dense-byok`](https://github.com/K-Dense-AI/k-dense-byok) is a desktop
"AI co-scientist" app (TypeScript, needs Node.js). It can run on an
OpenRouter key or, according to its configuration file, on a connected
ChatGPT Plus/Pro or Claude subscription. It is a separate application, and
it has not been tried here. `agentic-data-scientist` and
`claude-scientific-writer` require an Anthropic API key and an OpenRouter
key, which bill by use, so they are not used. `claude-skills-mcp` is
deprecated by its authors now that agents read skills themselves. K-Dense
Web is their paid hosted product. The skills are free, are plain text, and
work in every tool above, so they are the part copied here.

The vendored skills stay at one release until a maintainer updates them.
`skills.lock.json` names the upstream release. `scripts/sync_skills.py`
copies only those skill folders (about 2.5 MB; the full repository is
500 MB). A weekly GitHub Action reports when a newer release exists. To
update, a maintainer runs `sync_skills.py --update`, reads `git diff`, and
commits. A skill is a set of instructions that an agent will follow on the
lab's data, so a change to one is reviewed the way a change to code is.
Nothing under `vendor/` is edited by hand; lab-specific behaviour goes in
`AGENTS.md` or a `lab/` skill. To add one of the other 150 skills (the
[catalogue](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills)
covers most bioinformatics, chemistry, imaging, and database tasks), add
its folder name to `skills.lock.json` and run the sync.

## What this does not do

- **No API keys.** Use is covered by the subscriptions people already
  have. Nothing here bills by use.
- **No server to maintain and no search index.** Coding agents already search
  files well, and the header fields let them filter first. This can be
  reconsidered when a notebook is large enough that keyword search misses
  things (`design-notes.md`, *AI integration, in stages*).
- **No AI plugins for one editor.** The record is files, and every tool
  above reads the same files.
- **No AI-written conclusions.** The AI finds and cites what the notes
  say. People draw the conclusions.
