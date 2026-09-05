# Skills

A skill is a folder with a `SKILL.md`: a description of when it applies and
instructions for doing the task. AI agents that support the
[Agent Skills](https://agentskills.io/specification) convention (Codex,
Claude Code, Cowork, Cursor, Gemini CLI and others) read the description,
and load the full file when a request matches. Plain Markdown; no API
keys; nothing runs unless an agent chooses to follow it.

```
lab/       written for this record; edit freely
vendor/    pinned copies of upstream skill libraries; never edit here
```

## `lab/`

| skill | when it applies |
|---|---|
| `eln-record-experiment` | starting, writing up, or closing out an experiment; adding a sample, protocol, or project |
| `eln-search-and-cite` | any factual question about past lab work |
| `eln-project-synthesis` | updating a project page's *Current state* from its experiments |

They restate the ground rules in `AGENTS.md` in task-specific form: create
records only with `scripts/eln.py`, filter with `eln.py find` before
reading, cite experiment IDs, never invent a result.

## `vendor/`

Methodology skills from K-Dense, pinned by `skills.lock.json` at the repo
root and copied here by `scripts/sync_skills.py`:

- `k-dense-scientific/` (from
  [scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills),
  release `v2.66.0`): `experimental-design`, `statistical-analysis`,
  `scientific-writing`, `citation-management`, `labarchive-integration`.
- `k-dense-superpowers/` (from
  [science-superpowers](https://github.com/K-Dense-AI/science-superpowers),
  pinned commit): `preregistering-analysis`,
  `verifying-results-before-claiming`.

Each `vendor/<source>/NOTICE.md` records the upstream, the exact commit,
the sync date, and each skill's license. Some bundled scripts need Python
packages (they say which); the guidance itself needs nothing.

**Updating.** A weekly GitHub Action (`skills-drift.yml`) turns red when a
newer upstream release exists. A maintainer then runs

```bash
python3 scripts/sync_skills.py --check     # what changed upstream
python3 scripts/sync_skills.py --update    # move pins to the newest release and re-copy
git diff                                   # read it - these are instructions an agent will follow
```

and commits. To vendor another skill, add its folder name to the `skills`
list in `skills.lock.json` and run `sync_skills.py`. To change how a
vendored skill behaves here, don't edit it; override in `AGENTS.md` or a
`lab/` skill.

## Where agents look

`.agents/skills/` is the cross-tool location used by the Agent Skills
installers. If a particular tool reads a different project folder (for
example `.codex/skills/`), a symlink or copy of this folder there is
sufficient; the files are identical.
