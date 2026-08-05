# For Claude Code

Read [`AGENTS.md`](AGENTS.md) in this repo root first — it has the full
project context and the ground rules for AI-assisted work here (citation
requirements, what never to edit, how experiments get created). Everything
in it applies to you; this file only adds Claude-Code-specific notes.

- Use `Grep`/`Glob` to search `Experiments/`, `Projects/`, `Protocols/`,
  `Samples/` rather than reading every file — the vault is meant to grow
  well past what fits in one context window, and the YAML front matter is
  there so you can filter first.
- Use the `Bash` tool to run `scripts/new_experiment.py`; never create an
  experiment folder or inventory row by hand.
- If a task would touch many notes at once (bulk front-matter edits,
  renames), stop and confirm with the person you're working with before
  proceeding — see rule 7 in `AGENTS.md`.
