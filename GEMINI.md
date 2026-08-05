# For Gemini CLI

Read [`AGENTS.md`](AGENTS.md) in this repo root first — it has the full
project context and the ground rules for AI-assisted work here (citation
requirements, what never to edit, how experiments get created). Everything
in it applies to you; this file only adds Gemini-CLI-specific notes.

- Use your file-search tools (`glob`, `search_file_content`) across
  `Experiments/`, `Projects/`, `Protocols/`, `Samples/` before answering —
  filter on the YAML front matter (`project`, `researcher`, `status`,
  `date`, `tags`) rather than reading every note.
- Use `run_shell_command` to run `scripts/new_experiment.py`; never create
  an experiment folder or inventory row by hand.
- If a task would touch many notes at once (bulk front-matter edits,
  renames), stop and confirm with the person you're working with before
  proceeding — see rule 7 in `AGENTS.md`.
