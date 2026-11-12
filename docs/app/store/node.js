/* The notebook folder through Node's fs. Used by mcp/server.mjs and mcp/call.mjs. Not loaded in a browser. */

import fs from 'node:fs';
import fsp from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { ElnError } from '../lib/schema.js';

export class NodeStore {
  constructor(root) {
    this.root = path.resolve(root);
    this.label = this.root;
  }

  /** Absolute path for a notebook-relative one; refuses anything that leaves the folder, by its
      spelling or through a symbolic link. */
  abs(rel) {
    const full = path.resolve(this.root, ...String(rel).split('/'));
    if (full !== this.root && !full.startsWith(this.root + path.sep)) throw new ElnError(`path leaves the notebook folder: ${rel}`, 'bad_path');
    /* follow links in the part of the path that already exists */
    let existing = full;
    while (existing !== this.root && !fs.existsSync(existing)) existing = path.dirname(existing);
    let real;
    let realRoot;
    try {
      real = fs.realpathSync(existing);
      realRoot = fs.realpathSync(this.root);
    } catch (e) {
      return full; // the notebook folder itself is missing; the caller reports that
    }
    if (real !== realRoot && !real.startsWith(realRoot + path.sep)) throw new ElnError(`${rel} is a link to a place outside the notebook folder; it is not followed`, 'bad_path');
    return full;
  }

  async list(dir) {
    try {
      const entries = await fsp.readdir(this.abs(dir), { withFileTypes: true });
      const out = [];
      for (const e of entries) {
        let kind = e.isDirectory() ? 'dir' : e.isFile() ? 'file' : null;
        if (kind === null && e.isSymbolicLink()) {
          /* a link is listed only when it points to something inside the notebook folder */
          let target = null;
          try {
            target = this.abs(dir ? `${dir}/${e.name}` : e.name);
          } catch (err) { /* outside: skipped */ }
          const s = target ? await fsp.stat(target).catch(() => null) : null;
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
    let full;
    try {
      full = this.abs(rel);
    } catch (e) {
      return null; // a link that leaves the folder is treated as not there
    }
    try {
      const s = await fsp.stat(full);
      return { kind: s.isDirectory() ? 'dir' : 'file', size: s.size, mtime: s.mtimeMs };
    } catch (e) {
      return null;
    }
  }

  async readBytes(rel) {
    return new Uint8Array(await fsp.readFile(this.abs(rel)));
  }

  /** Written to a temporary file first and then renamed, so an interrupted write never leaves half a note. */
  async writeBytes(rel, bytes) {
    const full = this.abs(rel);
    await fsp.mkdir(path.dirname(full), { recursive: true });
    this.abs(rel); // again, now that the parent exists
    const tmp = path.join(path.dirname(full), `.${path.basename(full).slice(0, 80)}.${process.pid}.tmp`);
    try {
      await fsp.writeFile(tmp, bytes);
      await fsp.rename(tmp, full);
    } catch (e) {
      await fsp.rm(tmp, { force: true }).catch(() => {});
      throw e;
    }
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
