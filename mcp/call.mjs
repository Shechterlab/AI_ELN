#!/usr/bin/env node
/* Run one notebook tool from a terminal or a script. JSON in, JSON out.

     node mcp/call.mjs --list                                    the tools and their arguments
     node mcp/call.mjs check_notebook                            run a tool on this folder
     node mcp/call.mjs --root sandbox find_notes '{"status":"active"}'
     node mcp/call.mjs create_experiment '{"title":"...","initials":"JSR"}'
     node mcp/call.mjs --text check_notebook                     print the result's text instead of JSON

   Options: --root DIR, --initials XX, --researcher "Name" (defaults: see mcp/config.mjs), --today YYYY-MM-DD,
   --text, --openai (print the tools as function definitions).
   Exit status: 0 ok, 1 the tool refused (message on stderr), 2 the result has ok: false. */

import { NodeStore } from '../docs/app/store/node.js';
import { TOOLS, callTool, mcpTools, openAiTools, resultToJson } from '../docs/app/lib/tools.js';
import { parseFlags, resolveConfig } from './config.mjs';

const { opt, rest } = parseFlags(process.argv.slice(2), ['--root', '--today', '--initials', '--researcher'], ['--list', '--openai', '--text']);
const config = resolveConfig(opt);

if (opt.openai) {
  console.log(JSON.stringify(openAiTools(), null, 2));
} else if (opt.list || !rest.length) {
  if (rest.length === 0 && !opt.list) console.log('usage: node mcp/call.mjs [--root DIR] TOOL [JSON arguments]\n');
  for (const t of mcpTools()) {
    const props = Object.entries(t.inputSchema.properties).map(([k]) => (t.inputSchema.required.includes(k) ? k : `[${k}]`)).join(' ');
    console.log(`${t.name}${props ? '  ' + props : ''}\n    ${t.description}`);
  }
  console.log(`\n${TOOLS.length} tools.`);
} else {
  const ctx = { store: new NodeStore(config.root), person: config.person, today: opt.today || undefined };
  try {
    const result = await callTool(ctx, rest[0], rest[1] ? JSON.parse(rest[1]) : {});
    if (opt.text) process.stdout.write(result.text ?? result.markdown ?? resultToJson(result) + '\n');
    else console.log(resultToJson(result));
    process.exitCode = result.ok === false ? 2 : 0;
  } catch (e) {
    console.error(e.name === 'ElnError' || e instanceof SyntaxError ? e.message : e.stack);
    process.exitCode = 1;
  }
}
