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

  /** The path of an entry whose folder is inside the notebook. The entry itself is not followed if it is a link. */
  absEntry(rel) {
    const parts = String(rel).split('/').filter(Boolean);
    const name = parts.pop();
    if (!name || name === '.' || name === '..') throw new ElnError(`path leaves the notebook folder: ${rel}`, 'bad_path');
    return path.join(this.abs(parts.join('/')), name);
  }

  /** Held while an ID is chosen and its record written, so two programs cannot give out the same ID.
      An empty folder, the same one scripts/eln.py uses. One left by a crash is taken over after a minute.
      -> a function that releases it */
  async lock(wait = 20000) {
    const dir = path.join(this.root, '.eln-lock');
    const started = Date.now();
    for (;;) {
      try {
        await fsp.mkdir(dir);
        return async () => { await fsp.rmdir(dir).catch(() => {}); };
      } catch (e) {
        if (e.code !== 'EEXIST') return async () => {}; // a folder that cannot be written to: the creation itself will say so
        const s = await fsp.stat(dir).catch(() => null);
        if (s && Date.now() - s.mtimeMs > 60000) {
          await fsp.rmdir(dir).catch(() => {});
        } else if (Date.now() - started > wait) {
          throw new ElnError(`another program is creating a record in this notebook (${dir} is there). Try again in a moment. If nothing else is running, delete that folder.`, 'locked');
        } else await new Promise((r) => setTimeout(r, 30));
      }
    }
  }

  async list(dir) {
    try {
      const entries = await fsp.readdir(this.abs(dir), { withFileTypes: true });
      const out = [];
      for (const e of entries) {
        let kind = e.isDirectory() ? 'dir' : e.isFile() ? 'file' : null;
        const link = e.isSymbolicLink();
        if (kind === null && link) {
          /* a link is listed only when it points to something inside the notebook folder */
          let target = null;
          try {
            target = this.abs(dir ? `${dir}/${e.name}` : e.name);
          } catch (err) { /* outside: skipped */ }
          const s = target ? await fsp.stat(target).catch(() => null) : null;
          kind = s ? (s.isDirectory() ? 'dir' : 'file') : null;
        }
        /* a link is marked, so that nothing walks through it into another folder; a link that leaves the
           notebook, a broken link, a pipe: kind 'other', which only moving a whole folder looks at */
        out.push({ name: e.name, kind: kind || 'other', ...(link ? { link: true } : {}) });
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
      for (let attempt = 0; ; attempt++) {
        try {
          await fsp.rename(tmp, full);
          break;
        } catch (e) {
          /* Windows refuses while another program has the old file open; that lasts a moment */
          if (attempt >= 39 || !['EPERM', 'EACCES', 'EBUSY'].includes(e.code)) throw e;
          await new Promise((r) => setTimeout(r, 25));
        }
      }
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

  async rmdir(rel) {
    await fsp.rmdir(this.abs(rel));
  }

  /** Copy a file without reading it into memory; the modified time is kept. */
  async copy(from, to) {
    const src = this.abs(from);
    const dst = this.abs(to);
    await fsp.mkdir(path.dirname(dst), { recursive: true });
    this.abs(to);
    await fsp.copyFile(src, dst, fs.constants.COPYFILE_EXCL);
    const s = await fsp.stat(src);
    await fsp.utimes(dst, s.atime, s.mtime);
  }

  /** Move a file. A rename when both places are on the same drive, otherwise copy and delete. */
  async move(from, to) {
    const src = this.absEntry(from); // a link is moved as a link, never followed
    const dst = this.absEntry(to);
    if (fs.existsSync(dst)) throw new ElnError(`${to} already exists. Nothing was overwritten.`, 'exists');
    await fsp.mkdir(path.dirname(dst), { recursive: true });
    this.abs(to);
    try {
      await fsp.rename(src, dst);
    } catch (e) {
      if (e.code !== 'EXDEV') throw e;
      await this.copy(from, to);
      await fsp.rm(src);
    }
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
