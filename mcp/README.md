# mcp/: the notebook as tools for AI clients

The notebook's operations (create an experiment, find notes, read a note,
check the conventions, mark complete, export) are defined once, in
[`docs/app/lib/tools.js`](../docs/app/lib/tools.js), each with a name, a
description, and a JSON Schema for its arguments. Three things use that list:

| | what it is | needs |
|---|---|---|
| the notebook page (`docs/app/`) | the buttons and forms call the tools | Chrome or Edge |
| `mcp/server.mjs` | an [MCP](https://modelcontextprotocol.io) server over stdio | Node 18 or later |
| `mcp/call.mjs` | runs one tool from a terminal or a script | Node 18 or later |

There are no dependencies and nothing to install besides Node. The server
does not open a network port. It reads and writes only inside the notebook
folder.

## The tools

`node mcp/call.mjs --list` prints them with their arguments.

- Read: `get_conventions`, `notebook_overview`, `find_notes`, `read_note`,
  `read_file`, `check_notebook`, `verify_files`
- Create: `create_experiment`, `create_sample`, `create_protocol`, `create_project`,
  `adopt_folder` (an older folder becomes an experiment; with no folder it lists the candidates)
- Edit: `write_section`, `set_field` (with `mode` add or remove for one tag), `update_note`, `add_file`
- Finish and export: `complete_experiment`, `render_snapshot`,
  `meeting_brief`, `export_notes` (one Markdown file, a folder of plain files, or `.eln`), `rebuild_index`

While a record is being created the server holds the notebook's lock (an
empty `.eln-lock` folder, shared with `scripts/eln.py`), so two programs
cannot give out the same ID.

The server sends the lab's rules (cite experiment IDs, never invent a
result, never touch `2-data_raw`) to the client as its instructions.

## Connecting a client

The server takes `--root DIR` (the notebook folder; default: the one saved by
`python3 scripts/eln.py init --root`, or else the folder this repository is in),
`--initials` and `--researcher` (default: what `python3 scripts/eln.py init`
saved, or the environment variables `AI_ELN_INITIALS` and
`AI_ELN_RESEARCHER`, or else the owner named in the notebook's `notebook.md`), and `--read-only` (offer only the tools that change
nothing; the brief and the export are included and refuse to save).

In the examples, `/path/to/AI_ELN` is the tools folder (this repository) and
`/path/to/notebook` is your own notebook folder.

**Claude Code and Cowork.** The repository includes `.mcp.json`, so opening
the tool in the tools folder offers the `ai-eln` server and asks whether to
use it; it works on the notebook saved by `init --root`. To add it for a
particular notebook:

```bash
claude mcp add ai-eln -- node /path/to/AI_ELN/mcp/server.mjs --root /path/to/notebook
```

**Claude Desktop.** In `claude_desktop_config.json`:

```json
{ "mcpServers": { "ai-eln": { "command": "node", "args": ["/path/to/AI_ELN/mcp/server.mjs", "--root", "/path/to/notebook"] } } }
```

**Codex.** In `~/.codex/config.toml`:

```toml
[mcp_servers.ai-eln]
command = "node"
args = ["/path/to/AI_ELN/mcp/server.mjs", "--root", "/path/to/notebook"]
```

**Any other MCP client.** The command is `node /path/to/notebook/mcp/server.mjs`,
transport stdio.

**ChatGPT on the web** connects only to MCP servers that are reachable over
the internet. This one runs on your computer, so for ChatGPT use
**Export** and paste, as described in
[`docs/ai-agents.md`](../docs/ai-agents.md).

## What the server will not do

- Read or write outside the notebook folder, including through a symbolic
  link that points outside it.
- Overwrite a file with `add_file`, or accept a file name that carries a
  path.
- Save a note whose header is broken, whose ID or type changed, or whose
  status or dates are not valid.
- Put a line break into a header value. It becomes a space.

Two servers started on the same folder at the same moment can give two new
experiments the same ID. Check reports that as an error. Run one server per
notebook folder.

## Without MCP

A model that supports function calling can be given the same tools:
`node mcp/call.mjs --openai` prints them as function definitions, and
`callTool(ctx, name, args)` in `tools.js` runs one. An agent with a shell can
call a tool directly:

```bash
node mcp/call.mjs find_notes '{"status": "active"}'
node mcp/call.mjs create_experiment '{"title": "SNRPB chromatin retention: KCl titration", "initials": "JSR"}'
node mcp/call.mjs --text check_notebook
```

In the notebook page, the browser console and extensions can use
`await AIELN.call('find_notes', { status: 'active' })`.

## Tests

`tests/test_mcp.py` starts the server and speaks the protocol to it.
`tests/test_js_parity.py` checks that every tool produces the same files and
messages as `scripts/eln.py`.
