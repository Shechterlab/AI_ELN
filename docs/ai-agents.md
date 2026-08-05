# Getting AI features without picking a vendor

The question this answers: how does anyone in the lab actually get AI to
read and reason over this vault, in a way that still works in two years if
today's favorite tool isn't the one everyone's using?

## The trick: the vault is already agent-ready

Claude Code, OpenAI's Codex CLI, and Gemini CLI are all, underneath,
the same shape of tool: a coding agent that can read, search, and edit
local files, and run shell commands, in whatever directory you point it
at. None of them need this repo to expose an API, a database, or a plugin.
Any of them already works today if a lab member with a license for one
just runs it from inside this folder (or their synced copy of it) and
asks a question. That's the entire integration — there is no server to
stand up.

What's missing without any extra work is *context*: an agent dropped into
an unfamiliar folder doesn't know that experiments are created with
`scripts/new_experiment.py` and never by hand, or that every scientific
claim needs to cite an experiment ID. That's what `AGENTS.md` fixes.

## One instructions file, not three

`AGENTS.md` is an emerging convention — the same idea as a `README` but
addressed to an agent instead of a human, and it's already read by
multiple tools (OpenAI's Codex CLI, Cursor, and others). Claude Code
separately auto-loads a file named `CLAUDE.md`; Gemini CLI auto-loads
`GEMINI.md`. Rather than maintaining three copies of the same rules and
watching them drift, this repo keeps one canonical file —
[`../AGENTS.md`](../AGENTS.md) — and `CLAUDE.md` / `GEMINI.md` are a few
lines each, pointing back at it plus any tool-specific tool-name notes
(Claude Code's `Grep`/`Glob`/`Bash` vs. Gemini CLI's `search_file_content`/
`run_shell_command`).

That's the future-proofing: the investment is in one plain-text file
describing the lab's own rules (cite experiment IDs, never fabricate
results, don't touch raw data, always use the script to create
experiments), not in a config format that only works with whichever tool
is popular this year. If a fourth agent shows up next year and adopts
`AGENTS.md` too — increasingly likely, since that's the direction this is
converging — it gets the same grounding for free. If it doesn't, adding
a three-line pointer file for it costs nothing.

## What this does and doesn't require

**Doesn't require:** a shared server, an API key the lab manages centrally,
a vector database, or picking one AI tool for everyone. Each person uses
whatever CLI they already have a license/subscription for, pointed at
their own clone or their synced copy of the vault.

**Does require:** the vault actually being on each person's machine (or a
synced folder), and — same as any AI tool — attention to data
classification before pasting anything sensitive into a hosted model. That
consideration is orthogonal to which of these three tools is used.

## Why no retrieval/embeddings layer yet

Coding agents already do their own file search (grep/glob) well enough to
answer questions over a vault of dozens to low hundreds of well-tagged
Markdown notes — that's the same mechanism they use to navigate any
codebase. A dedicated semantic-search index only starts earning its keep
once the vault is large enough that keyword/tag search misses relevant
notes, which is a "revisit this later" problem, not a day-one one. See
["AI integration, in stages"](design-notes.md#ai-integration-in-stages) in
`design-notes.md` for where that fits into the overall plan.

## For lab members who don't want a terminal

Not everyone wants to run a CLI. Two lower-effort on-ramps, in rough order
of effort:

- **Obsidian AI plugins** (e.g. Smart Connections, Copilot for Obsidian) —
  read the same local Markdown files, no separate sync or export step, and
  give a chat panel inside the same app used for editing.
- **A small hosted chat app** — worth building only once there's a clear,
  recurring query pattern (e.g. "search the whole lab's history") that
  outgrows what an individual pointed-at-a-folder CLI session comfortably
  handles. Not needed for the pilot.
