#!/usr/bin/env node
/* An MCP server for the notebook: the tools in docs/app/lib/tools.js over stdio.
   No dependencies; Node 18 or later.

     node mcp/server.mjs                      serve the folder this repository is in
     node mcp/server.mjs --root /path/to/notebook --initials JSR --researcher "Jacob Roth"
     node mcp/server.mjs --read-only          only the tools that change nothing

   The client (Codex, Claude Code, Claude Desktop, Cowork, or anything else that speaks MCP) starts this
   process and talks JSON-RPC 2.0 on stdin and stdout, one message per line. Nothing listens on a network
   port and nothing leaves the computer. See mcp/README.md for the lines to add to each client. */

import readline from 'node:readline';
import { NodeStore } from '../docs/app/store/node.js';
import { callTool, getTool, mcpTools, resultToJson } from '../docs/app/lib/tools.js';
import { CONVENTIONS_SUMMARY } from '../docs/app/lib/conventions.js';
import { parseFlags, resolveConfig } from './config.mjs';

const VERSIONS = ['2025-06-18', '2025-03-26', '2024-11-05'];
const { opt } = parseFlags(process.argv.slice(2), ['--root', '--initials', '--researcher', '--today'], ['--read-only']);
const config = resolveConfig(opt);
const ctx = { store: new NodeStore(config.root), person: config.person, today: opt.today || undefined };
const tools = mcpTools().filter((t) => !opt.read_only || t.annotations.readOnlyHint);
const allowed = new Set(tools.map((t) => t.name));
let version = VERSIONS[0];

const send = (message) => process.stdout.write(JSON.stringify(message) + '\n');
const reply = (id, result) => send({ jsonrpc: '2.0', id, result });
const fail = (id, code, message) => send({ jsonrpc: '2.0', id, error: { code, message } });

async function handle(msg) {
  const { id, method, params = {} } = msg;
  const wantsReply = id !== undefined && id !== null;
  if (typeof method !== 'string') return; // a response to something we never asked
  if (method === 'initialize') {
    version = VERSIONS.includes(params.protocolVersion) ? params.protocolVersion : VERSIONS[0];
    return reply(id, {
      protocolVersion: version,
      capabilities: { tools: { listChanged: false } },
      serverInfo: { name: 'ai-eln', title: 'Plain-text lab notebook', version: '1.0.0' },
      instructions: CONVENTIONS_SUMMARY,
    });
  }
  if (!wantsReply) return; // notifications (notifications/initialized, cancelled, ...) need no answer
  if (method === 'ping') return reply(id, {});
  if (method === 'tools/list') return reply(id, { tools });
  if (method === 'tools/call') {
    if (!getTool(params.name) || !allowed.has(params.name)) return fail(id, -32602, `Unknown tool: ${params.name}`);
    try {
      const result = await callTool(ctx, params.name, params.arguments || {});
      const text = resultToJson(result);
      const out = { content: [{ type: 'text', text }], isError: false };
      if (version >= '2025-06-18') out.structuredContent = JSON.parse(text);
      return reply(id, out);
    } catch (e) {
      if (e.name !== 'ElnError') process.stderr.write(`${e.stack}\n`);
      return reply(id, { content: [{ type: 'text', text: e.name === 'ElnError' ? e.message : `internal error: ${e.message}` }], isError: true });
    }
  }
  return fail(id, -32601, `Method not found: ${method}`);
}

process.stderr.write(`ai-eln MCP server: ${config.root}${opt.read_only ? ' (read-only)' : ''}, ${tools.length} tools\n`);
let queue = Promise.resolve();
readline.createInterface({ input: process.stdin, crlfDelay: Infinity }).on('line', (line) => {
  if (!line.trim()) return;
  let msg;
  try {
    msg = JSON.parse(line);
  } catch (e) {
    return fail(null, -32700, 'Parse error');
  }
  /* one message at a time, so two calls never write the same file at once */
  queue = queue.then(() => handle(msg)).catch((e) => process.stderr.write(`${e.stack}\n`));
});
