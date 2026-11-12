/* What a "store" is, and helpers that work on any store.

   A store is the notebook folder seen through five methods. Paths are POSIX, relative to the notebook
   folder, with no leading slash ('' is the folder itself).

     list(dir)            -> [{ name, kind: 'file' | 'dir' }], or null if dir is not a folder
     stat(path)           -> { kind, size, mtime (ms) }, or null if nothing is there
     readBytes(path)      -> Uint8Array
     writeBytes(path, u8) -> writes the file, creating parent folders
     mkdir(path)          -> creates the folder and its parents

   Optional: sha256(path) -> hex (a faster native hash), readChunks(path) -> async iterator of Uint8Array,
   existsOutside(text) -> boolean for a path that is not inside the notebook, remove(path), label.

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
export async function walkFiles(store, dir) {
  const out = [];
  async function visit(d) {
    const entries = await store.list(d);
    if (!entries) return;
    for (const e of entries) {
      const p = joinPath(d, e.name);
      if (e.kind === 'dir') await visit(p);
      else out.push(p);
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
