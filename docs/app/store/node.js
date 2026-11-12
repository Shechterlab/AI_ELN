/* The notebook folder through Node's fs. Used by mcp/server.mjs and mcp/call.mjs. Not loaded in a browser. */

import fs from 'node:fs';
import fsp from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';

export class NodeStore {
  constructor(root) {
    this.root = path.resolve(root);
    this.label = this.root;
  }

  /** Absolute path for a notebook-relative one; refuses anything that leaves the folder. */
  abs(rel) {
    const full = path.resolve(this.root, ...String(rel).split('/'));
    if (full !== this.root && !full.startsWith(this.root + path.sep)) throw new Error(`path leaves the notebook folder: ${rel}`);
    return full;
  }

  async list(dir) {
    try {
      const entries = await fsp.readdir(this.abs(dir), { withFileTypes: true });
      const out = [];
      for (const e of entries) {
        let kind = e.isDirectory() ? 'dir' : e.isFile() ? 'file' : null;
        if (kind === null && e.isSymbolicLink()) {
          const s = await fsp.stat(path.join(this.abs(dir), e.name)).catch(() => null);
          kind = s ? (s.isDirectory() ? 'dir' : 'file') : null;
        }
        if (kind) out.push({ name: e.name, kind });
      }
      return out;
    } catch (e) {
      return null;
    }
  }

  async stat(rel) {
    try {
      const s = await fsp.stat(this.abs(rel));
      return { kind: s.isDirectory() ? 'dir' : 'file', size: s.size, mtime: s.mtimeMs };
    } catch (e) {
      return null;
    }
  }

  async readBytes(rel) {
    return new Uint8Array(await fsp.readFile(this.abs(rel)));
  }

  async writeBytes(rel, bytes) {
    const full = this.abs(rel);
    await fsp.mkdir(path.dirname(full), { recursive: true });
    await fsp.writeFile(full, bytes);
  }

  async mkdir(rel) {
    await fsp.mkdir(this.abs(rel), { recursive: true });
  }

  async remove(rel) {
    await fsp.rm(this.abs(rel), { force: true });
  }

  sha256(rel) {
    return new Promise((resolve, reject) => {
      const h = createHash('sha256');
      fs.createReadStream(this.abs(rel)).on('data', (c) => h.update(c)).on('end', () => resolve(h.digest('hex'))).on('error', reject);
    });
  }

  /** Does a path written in a note (absolute, or starting with ~) exist on this computer? */
  async existsOutside(text) {
    const p = text.startsWith('~') ? path.join(os.homedir(), text.slice(1)) : text;
    return path.isAbsolute(p) && fs.existsSync(p);
  }
}
