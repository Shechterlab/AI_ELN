/* Where the notebook is and who is using it, for the Node entry points.
   Order: command-line flag, environment (AI_ELN_ROOT, AI_ELN_INITIALS, AI_ELN_RESEARCHER),
   ~/.ai_eln.json (the file `python3 scripts/eln.py init` writes), then the folder this repository is in.
   labText is this repository's docs/lab.yaml, the layer under a notebook's own lab.yaml. */

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

export function parseFlags(argv, valueFlags, boolFlags = []) {
  const opt = {};
  const rest = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (valueFlags.includes(a)) opt[a.slice(2).replaceAll('-', '_')] = argv[++i];
    else if (boolFlags.includes(a)) opt[a.slice(2).replaceAll('-', '_')] = true;
    else rest.push(a);
  }
  return { opt, rest };
}

export function resolveConfig(opt = {}) {
  let saved = {};
  const configFile = process.env.AI_ELN_CONFIG || path.join(os.homedir(), '.ai_eln.json');
  try {
    saved = JSON.parse(fs.readFileSync(configFile, 'utf8').replace(/^\uFEFF/, ''));
  } catch (e) {
    /* no settings file is normal; a damaged one must not send the tools to a different folder */
    if (e.code !== 'ENOENT') throw new Error(`the settings file ${configFile} is damaged (${e.message}). Delete it and run init again`);
  }
  const initials = String(opt.initials || process.env.AI_ELN_INITIALS || saved.initials || '').toUpperCase();
  let labText = null;
  try {
    labText = fs.readFileSync(path.join(REPO, 'docs', 'lab.yaml'), 'utf8').replace(/\r\n?/g, '\n');
  } catch (e) { /* the built-in copy is used */ }
  return {
    labText,
    root: path.resolve(opt.root || process.env.AI_ELN_ROOT || saved.root || REPO),
    person: { initials, researcher: opt.researcher || process.env.AI_ELN_RESEARCHER || saved.researcher || initials },
  };
}
