# Skills

A skill is a folder with a `SKILL.md`: a description of when it applies and
instructions for doing the task. AI agents that follow the
[Agent Skills](https://agentskills.io/specification) convention (Codex,
Claude Code, Cowork, Cursor, Gemini CLI and others) read the description,
and load the full file when a request matches. A skill is plain Markdown.
It needs no API key, and nothing runs unless an agent chooses to follow it.

```
lab/       written for this record; edit freely
vendor/    copies of upstream skill libraries at a fixed version; never edit here
```

## `lab/`

| skill | when it applies |
|---|---|
| `eln-record-experiment` | starting, writing up, or closing out an experiment; adding a sample, protocol, or project; adopting an older folder |
| `eln-search-and-cite` | any factual question about past lab work |
| `eln-project-synthesis` | updating a project page's *Current state* from its experiments |

They repeat the ground rules in `AGENTS.md` for each task: create records
only with `scripts/eln.py`, filter with `eln.py find` before reading, cite
experiment IDs, never invent a result. The agent is opened in the tools
folder (this repository) and works on the notebook named with
`eln.py init --root`.

## `vendor/`

Methodology skills from K-Dense. `skills.lock.json` at the top of this
repository names the version of each, and `scripts/sync_skills.py` copies
them here:

- `k-dense-scientific/` (from
  [scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills),
  release `v2.66.0`): `statistical-analysis`, `experimental-design`,
  `scientific-visualization`, `exploratory-data-analysis`,
  `scientific-writing`, `scientific-critical-thinking`,
  `citation-management`, `paper-lookup`, `scientific-slides`, `pyopenms`,
  `pydeseq2`, `pathway-enrichment`, `labarchive-integration`. What each
  needs to run its scripts is listed in
  [`../../docs/ai-agents.md`](../../docs/ai-agents.md#the-skills).
- `k-dense-superpowers/` (from
  [science-superpowers](https://github.com/K-Dense-AI/science-superpowers),
  at a fixed commit): `preregistering-analysis`,
  `verifying-results-before-claiming`.

Each `vendor/<source>/NOTICE.md` records the upstream, the commit, the sync
date, and each skill's license. Some bundled scripts need Python packages
(they say which). The guidance needs nothing installed.

**Updating.** A weekly GitHub Action (`skills-drift.yml`) fails when a
newer upstream release exists. A maintainer then runs

```bash
python3 scripts/sync_skills.py --check     # the version here and the newest one upstream
python3 scripts/sync_skills.py --update    # move to the newest release and copy again
git diff                                   # read it: these are instructions an agent will follow
```

and commits. To add another skill, add its folder name to the `skills`
list in `skills.lock.json` and run `sync_skills.py`. To change how a
vendored skill behaves here, do not edit it. Put the change in `AGENTS.md`
or a `lab/` skill.

## Where agents look

`.agents/skills/` is the location that the Agent Skills installers use for
every tool. If a tool reads a different project folder (for example
`.codex/skills/`), a link to this folder or a copy of it there is enough.
