/* What a "store" is, and helpers that work on any store.

   A store is the notebook folder seen through five methods. Paths are POSIX, relative to the notebook
   folder, with no leading slash ('' is the folder itself).

     list(dir)            -> [{ name, kind: 'file' | 'dir' }], or null if dir is not a folder
     stat(path)           -> { kind, size, mtime (ms) }, or null if nothing is there
     readBytes(path)      -> Uint8Array
     writeBytes(path, u8) -> writes the file, creating parent folders
     mkdir(path)          -> creates the folder and its parents

   Optional: sha256(path) -> hex (a faster native hash), readChunks(path) -> async iterator of Uint8Array,
   existsOutside(text) -> boolean for a path that is not inside the notebook, remove(path), rmdir(path) for an
   empty folder, copy(from, to) and move(from, to) for one file without holding it in memory, lock() -> release
   so two programs do not create a record at the same moment, label. A list entry may carry link: true (a
   symbolic link) or kind 'other' (a link that leaves the notebook, a broken link, a pipe).

   Three stores ship: memory.js (tests, the try-it mode), fsaccess.js (a folder picked in Chrome or Edge),
   node.js (Node's fs, for the command line and the MCP server). A new backend (a sync service's API, a
   WebDAV share) is one more file with these five methods. */

import { decodeText, utf8, cmpPath, joinPath } from '../lib/text.js';

export const writeText = (store, path, text) => store.writeBytes(path, utf8(text));

/** Read text the forgiving way (bad bytes become U+FFFD). */
export const readText = async (store, path) => decodeText(await store.readBytes(path), false);

export async function exists(store, path) {
  return (await store.stat(path)) !== null;
}

export async function isDir(store, path) {
  const s = await store.stat(path);
  return s !== null && s.kind === 'dir';
}

export async function isFile(store, path) {
  const s = await store.stat(path);
  return s !== null && s.kind === 'file';
}

/** Every file under dir, recursively, as relative paths in pathlib order. [] if dir is not a folder. */
export async function walkFiles(store, dir, { links = true } = {}) {
  const out = [];
  async function visit(d) {
    const entries = await store.list(d);
    if (!entries) return;
    for (const e of entries) {
      if (e.link && !links) continue;
      const p = joinPath(d, e.name);
      if (e.kind === 'dir') await visit(p);
      else if (e.kind === 'file') out.push(p);
    }
  }
  await visit(dir);
  return out.sort(cmpPath);
}

/** Write only when the content differs, so a synced folder does not see a modified file for nothing.
    Returns true if the file was written. */
export async function writeTextIfChanged(store, path, text) {
  let old = null;
  try {
    if (await isFile(store, path)) old = decodeText(await store.readBytes(path), true);
  } catch (e) {
    old = null;
  }
  if (old === text) return false;
  await writeText(store, path, text);
  return true;
}

/** Copy one file. A store's own copy() is used when it has one (no need to hold the file in memory). */
export async function copyFile(store, from, to) {
  if (typeof store.copy === 'function') return store.copy(from, to);
  return store.writeBytes(to, await store.readBytes(from));
}

/** Move one file: the store's own move(), or copy and then remove. */
export async function moveFile(store, from, to) {
  if (typeof store.move === 'function') return store.move(from, to);
  await copyFile(store, from, to);
  return store.remove(from);
}

/** Remove a folder if it is empty. True when it is gone. */
export async function removeDir(store, path) {
  if (typeof store.rmdir !== 'function') return false;
  try {
    await store.rmdir(path);
  } catch (e) {
    return false;
  }
  return !(await exists(store, path));
}

/** Run fn while holding the store's lock, if it has one. */
export async function withLock(store, fn) {
  const release = typeof store.lock === 'function' ? await store.lock() : null;
  try {
    return await fn();
  } finally {
    if (release) await release();
  }
}

/** Every folder (parents first) and every file under dir, as paths relative to dir. Links are never walked
    through: they, and anything that is neither a file nor a folder, are returned in `others`. */
export async function walkTree(store, dir) {
  const dirs = [];
  const files = [];
  const others = [];
  async function visit(rel) {
    const entries = ((await store.list(joinPath(dir, rel))) || []).slice().sort((a, b) => cmpPath(a.name, b.name));
    for (const e of entries) {
      const p = joinPath(rel, e.name);
      if (e.link || (e.kind !== 'dir' && e.kind !== 'file')) others.push(p);
      else if (e.kind === 'dir') {
        dirs.push(p);
        await visit(p);
      } else files.push(p);
    }
  }
  await visit('');
  return { dirs, files: files.sort(cmpPath), others };
}

/** A folder inside a store, seen as a store of its own (an export folder, one notebook among several). */
export class SubStore {
  constructor(store, prefix) {
    this.store = store;
    this.prefix = prefix;
    this.label = `${store.label || ''}/${prefix}`;
  }

  at(path) { return path ? `${this.prefix}/${path}` : this.prefix; }
  list(dir) { return this.store.list(this.at(dir)); }
  stat(path) { return this.store.stat(this.at(path)); }
  readBytes(path) { return this.store.readBytes(this.at(path)); }
  writeBytes(path, bytes) { return this.store.writeBytes(this.at(path), bytes); }
  mkdir(path) { return this.store.mkdir(this.at(path)); }
}
