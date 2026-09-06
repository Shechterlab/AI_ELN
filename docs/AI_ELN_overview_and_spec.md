# AI_ELN — System Overview & Specification

*A briefing document, written to be read cold by a person or pasted into a
fresh conversation with another AI without any other context from this
repo. Reflects the `claude/k-dense-ai-integration-d2spl5` branch of
`shechterlab/ai_eln`. The precise rules live in `docs/CONVENTIONS.md`; this
document is the overview.*

---

## 1. The problem this is solving

The Shechter Lab has a site-licensed LabArchives account, but its editing
interface is cumbersome enough that people put off writing things down. At
the same time, one lab member (Jacob Roth, PhD student) independently built
a better information architecture using nothing but a folder-naming
convention and a spreadsheet: every experiment gets a stable ID, a
standardized folder layout, explicit separation of raw vs. processed data,
and a short results summary written while it's still fresh.

Jacob's system already solves the hard part. What it lacked was a format
that's easy to search, link across entities, and hand to an AI assistant,
plus something that keeps the naming honest as more people use it. That's
what this project is: translate his system into Markdown with a flat
header, add one dependency-free tool that assigns IDs and validates the
conventions, make it usable by people who never open a terminal, and make
the result readable by any AI the lab already pays for — with no API keys.

## 2. Core design decisions

1. **Plain Markdown files with a flat YAML header are the canonical
   record.** Any editor, `grep`, a spreadsheet, or an AI reads and writes
   the same files. No proprietary format, no database, no required app.
2. **The experiment is the atomic unit.** One ID, one folder, one note.
3. **Metadata and naming conventions are the product.** They are specified
   on one page (`CONVENTIONS.md`), implemented by one tool, and enforced by
   a validator that advises rather than blocks.
4. **Low friction for people without computer skills.** One double-click
   opens a local web page with forms; the tool names everything; notes can
   be written on the page itself or in any editor.
5. **Large binary data lives outside the record**, on institutional
   storage, referenced by path.
6. **Where the record lives is a lab decision.** Default: this folder,
   synced. Alternative: a separate root, set once.
7. **LabArchives is the archival layer**, fed one-directionally on
   completion. Not yet built.
8. **AI is retrieval-and-citation, never the source of a conclusion.** It
   runs on the ChatGPT site license or a Claude subscription by reading
   files and pasted exports; nothing uses a metered API.

## 3. Architecture at a glance

```
Daily work                                  At completion
──────────                                  ─────────────
Experiment note (MD + header) ────┐
Raw/processed data (storage)      ├──►  Rendered snapshot (PDF/HTML)
Protocols/Samples/Projects (MD)   ┘            │
        ▲                                      ▼
   eln.py validate                    LabArchives entry (timestamped, audited)
```

Everything that creates or reads the Markdown layer goes through the same
files on disk:

```
launchers/*.command|.cmd  (double-click)  ─┐
scripts/eln.py            (terminal)        ├──► same files, same folder
Codex / Claude Code / Cowork / Gemini CLI  │     (AGENTS.md + .agents/skills/)
ChatGPT via eln.py export + ai-briefing.md ┘
```

## 4. Specification (summary; `CONVENTIONS.md` is authoritative)

### 4.1 Layout

```
<root>/
├── Experiments/{ID}_{slug}/{1-notes,2-data_raw,3-code,4-data_processed,5-figures}/
├── Protocols/P_{Name}.md
├── Samples/{ID}.md
├── Projects/{ID}.md
├── Inventory/{experiments,samples,protocols,projects}.csv   (generated)
├── templates/{experiment,protocol,sample,project}.md
├── scripts/eln.py, scripts/eln_web.py, scripts/sync_skills.py
├── launchers/                                 double-click entry points (Mac + Windows); Open ELN starts the page
├── sandbox/                                   fictional record to practice on; rebuild.py regenerates it
├── AGENTS.md, CLAUDE.md, GEMINI.md            AI agent contract
├── .agents/skills/{lab,vendor}/               skills; vendor/ pinned by skills.lock.json
├── docs/                                      CONVENTIONS, CHEATSHEET, getting-started, SOP, ai-*, design-notes
└── tests/                                     unittest, run on ubuntu/macos/windows in CI
```

### 4.2 Identifiers

| thing | pattern | example |
|---|---|---|
| experiment | `{INITIALS}e{NNNN}` | `JSRe0002` |
| sample | `{INITIALS}{t}{NNNN}`, `t` ∈ p i a c m t r s g | `JSRp0001` |
| protocol | `P_{Name}` | `P_WesternBlot` |
| project | `{Name}` | `PRMT5-ChromatinRelease` |

Initials are 2–4 uppercase letters and form a per-researcher namespace;
numbers are sequential per researcher and per type and never reused. A
bare ID anywhere is a reference.

### 4.3 Filenames

`{EXPERIMENT_ID}[_{R|P}]_{words-with-hyphens}[_{YYYYMMDD}].{ext}` for every
file a person creates inside an experiment folder. `R` = results summary,
`P` = protocol snapshot (written by the tool). `2-data_raw/` is exempt:
instrument output is never renamed.

### 4.4 Header schema

A flat YAML subset: one `key: value` per line, lists as `[a, b]`, no
nesting, dates `YYYY-MM-DD`, optional `# comment`. Per-type required
fields, "should" fields (warned when empty), enumerations (`status`,
`sample_type`), and fixed body sections are tabulated in `CONVENTIONS.md`
§4. The template for each type defines the allowed key set; the validator
warns on anything else.

### 4.5 `scripts/eln.py`

Standard-library Python 3.9+. `--root` on every command; `AI_ELN_ROOT`,
then `~/.ai_eln.json`, then this repo, decide where the record lives.

| command | does |
|---|---|
| `init` | saves initials, name, root; creates the folders; writes a pointer `AGENTS.md` into a separate root |
| `new experiment/sample/protocol/project` | assigns the ID, renders the template, snapshots protocols, re-indexes; `--interactive` asks questions (used by the launchers), `--open` opens the note |
| `validate [--strict]` | every rule in `CONVENTIONS.md` §6; errors fail, warnings advise |
| `index` | regenerates the four CSVs from the notes; usage columns derived |
| `find` | filter by project/status/researcher/tag/sample/protocol/type/free text; `--ids`, `--json` |
| `report` | Markdown lab-meeting brief: flagged (`tags: [meeting]`) with sections, active by project, recently completed, paused |
| `export` | one Markdown bundle of selected experiments plus what they reference, with a primer for the model |

`scripts/eln_web.py` serves the same operations as a local web page (127.0.0.1 only, standard-library
`http.server`): forms for the four `new` commands, browse and filter, a rendered note view with figures
and auto-linked IDs, in-browser editing that re-checks the header on save, the checker, the meeting
brief, and the export with a copy button. `launchers/Open ELN` starts it.

Explicitly not implemented: file locking around ID assignment. Two people
sharing initials creating an experiment in the same instant could collide;
per-researcher initials make this a non-issue in practice.

### 4.6 AI contract

`AGENTS.md` (read natively by Codex and others) carries the rules; `CLAUDE.md`
and `GEMINI.md` point at it. `.agents/skills/lab/` holds three lab skills
(record, search-and-cite, project synthesis). `.agents/skills/vendor/`
holds seven methodology skills from K-Dense pinned by `skills.lock.json`,
copied by `scripts/sync_skills.py` via sparse checkout, checked weekly for
upstream drift by CI, and updated only as a reviewed diff. For ChatGPT
without a terminal, `docs/ai-briefing.md` is pasted once as Project
instructions and `eln.py export` produces the material to paste.

No server, API key, or vector database is involved.

## 5. What's built vs. not

**Built and tested (this branch):**
- `CONVENTIONS.md`, `CHEATSHEET.md`, the four templates
- `scripts/eln.py` with all commands above; 50 unit tests
- A local web page (`scripts/eln_web.py`) with forms, browsing, in-browser editing, checker, brief, export; 10 tests
- Double-click launchers for Mac and Windows, including `Open ELN` and `Try the Sandbox`
- `sandbox/`: a fictional seven-experiment record generated by `sandbox/rebuild.py`, validated in CI, with the AI skills piloted against it (`sandbox/PILOT.md`)
- `scripts/sync_skills.py`, `skills.lock.json`, seven vendored skills, 9 tests
- `AGENTS.md`/`CLAUDE.md`/`GEMINI.md`, three lab skills, ChatGPT briefing
- GitHub Actions: tests on ubuntu/macos/windows × Python 3.9/3.12; strict
  validation of the example vault; inventory freshness; weekly skills drift
- A worked example (`DSLe0001`, `P_WesternBlot`, `DSLp0001`,
  `PRMT5-ChromatinRelease`) produced by the tool, validating clean

**Not built (discussed):**
- The LabArchives archival bridge (needs institutional API access)
- Scheduled project synthesis
- Instrument ingestion, per-experiment manifests with checksums
- A semantic-search index

## 6. Staged rollout

1. **Pilot** — 2–3 people, one project, ~20 experiments, using what's built.
   Collect what the validator complains about and what people skip.
2. **Lab standardization** — SOP training, everyone's initials in config,
   shared root decided.
3. **LabArchives bridge** — automated snapshots on `status: complete`.
4. **Ingestion and synthesis automation** — last, on purpose.

## 7. Open questions

- **ID scheme longevity.** Per-researcher initials + sequence is
  human-friendly and matches the existing habit; it is not machine-safe
  across labs. Is that ever a problem here?
- **Multi-root aggregation.** If people keep personal roots, a lab-wide
  view needs a merge of several `Inventory/` sets. One shared root avoids
  it entirely; is that acceptable to everyone?
- **Manifest depth.** What's the smallest raw→processed→figure manifest
  worth maintaining by hand before ingestion automates it?
- **Retrieval ceiling.** At what vault size does `find` + grep start
  missing things, and is a keyword index a sufficient middle step?
- **LabArchives snapshot shape.** Is a rendered PDF/HTML enough for the
  institution's definition of an adequate record?
