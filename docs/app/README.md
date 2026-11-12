# docs/app/: the notebook in the browser

Open <https://shechterlab.github.io/AI_ELN/app/> in Chrome or Edge, click
**Open notebook folder**, and choose the folder. The page reads and writes
the files in that folder. It uploads nothing, needs no installation, and
works without a connection after the first visit.

It does everything `scripts/eln.py` and the Python page do, on the same
folders and with the same results: tests run each operation through both and
compare the files byte for byte.

## Layout

```
app/
  index.html, app.css   the page
  ui.js                 screens and buttons; calls the tools, nothing else
  sw.js                 keeps the page's own files for use without a connection
  lib/                  the notebook logic; no browser and no Node code in here
    schema.js           the conventions as data (folders, ID patterns, required fields)
    text.js             text, path, date helpers
    frontmatter.js      the note header (flat YAML subset): parse, format, set a field
    names.js            slugs, IDs, file names
    templates.js        note templates (the notebook's templates/ folder, or the built-in copy)
    vault.js            read every note in the notebook
    validate.js         Check
    inventory.js        Inventory/*.csv
    create.js           new experiment, sample, protocol, project; add a file
    query.js            find, lab-meeting brief, Markdown export
    markdown.js         Markdown to HTML
    closeout.js         mark complete, HTML snapshot, sha256 manifest, verify
    elnfile.js, zip.js  the .eln archive (RO-Crate in a ZIP)
    sha256.js, mime.js  hashing, media types
    conventions.js      the rules as one page of text, given to AI clients
    tools.js            every operation as a named tool with a JSON Schema
  store/                where the files are
    base.js             what a store is (five methods) and helpers
    fsaccess.js         a folder picked in the browser (File System Access API)
    memory.js           in memory, for practice mode and tests
    node.js             Node's fs, for mcp/server.mjs and mcp/call.mjs
```

## Extending it

- **A new operation:** write the function in `lib/`, add one entry to `TOOLS`
  in `lib/tools.js` (name, description, argument schema, handler). The MCP
  server and `mcp/call.mjs` pick it up with no other change. Add a button in
  `ui.js` if people need it.
- **A new place to keep files** (a WebDAV share, a sync service's API): one
  file in `store/` with `list`, `stat`, `readBytes`, `writeBytes`, `mkdir`.
  Nothing in `lib/` changes.
- **A new AI integration:** an adapter over `TOOLS`. `mcpTools()` and
  `openAiTools()` in `lib/tools.js` are the two that exist.
- **A change to a convention:** change `scripts/eln.py` and the matching
  file in `lib/` together. `tests/test_js_parity.py` fails until they agree.
- **A template change:** edit `templates/*.md`, then run
  `python3 scripts/build_js_templates.py`.

There is no build step and no dependency. The files here are the files the
browser loads.

## Browser support

Opening a folder needs the File System Access API, which Chrome and Edge
have on Windows, macOS, and Linux. Safari and Firefox do not; there the page
offers the practice notebook only, and the notebook itself runs from the
Python launcher. Dropbox and OneDrive both work, because the page writes
ordinary files into the folder that their desktop apps sync.

## Tests

```bash
python3 -m unittest tests.test_js_parity   # each operation, Python against JavaScript
python3 -m unittest tests.test_mcp         # the MCP server
python3 -m unittest tests.test_app_e2e     # the page in headless Chromium (needs the playwright package)
node tests/e2e_app.mjs                     # the same, with one line per step
```

`index.html?store=opfs` opens the page on a private folder inside the
browser instead of asking for one. The tests use it, because a folder
picker cannot be automated.
