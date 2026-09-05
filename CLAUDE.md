# For Claude Code and Cowork

Read [`AGENTS.md`](AGENTS.md) first: it has the layout, the `eln.py`
commands, and the ground rules (cite experiment IDs, never fabricate a
result, create records only through the tool, never touch `2-data_raw/`).
Everything there applies. This file only adds tool-specific notes.

- Skills for this record are in `.agents/skills/lab/` and pinned
  methodology skills in `.agents/skills/vendor/`; read a `SKILL.md` when a
  task matches its description.
- Use `Grep`/`Glob` (or `python3 scripts/eln.py find ...` via `Bash`) to
  filter on the YAML header before reading notes; don't read the whole vault.
- Use `Bash` to run `scripts/eln.py`. Never create an experiment folder or
  an inventory row by hand.
- If a task would touch many notes at once, stop and confirm with the
  person first (rule 7 in `AGENTS.md`).
- Do not edit anything under `.agents/skills/vendor/`; it is replaced by
  `scripts/sync_skills.py`.
