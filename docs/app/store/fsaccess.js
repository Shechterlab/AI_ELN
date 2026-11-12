/* The notebook folder through the browser's File System Access API (Chrome and Edge on a computer).
   The person picks the folder once; the browser asks for permission; this page then reads and writes
   the files in it directly. Nothing is uploaded. */

export class FsAccessStore {
  constructor(handle) {
    this.root = handle;
    this.label = handle.name;
  }

  async dir(path, create = false) {
    let h = this.root;
    for (const part of path.split('/').filter(Boolean)) h = await h.getDirectoryHandle(part, { create });
    return h;
  }

  async file(path, create = false) {
    const i = path.lastIndexOf('/');
    const parent = await this.dir(i < 0 ? '' : path.slice(0, i), create);
    return parent.getFileHandle(path.slice(i + 1), { create });
  }

  async list(dir) {
    try {
      const h = await this.dir(dir);
      const out = [];
      for await (const [name, child] of h.entries()) out.push({ name, kind: child.kind === 'directory' ? 'dir' : 'file' });
      return out;
    } catch (e) {
      if (e.name === 'NotAllowedError') throw e;
      return null;
    }
  }

  async stat(path) {
    if (path === '') return { kind: 'dir', size: 0, mtime: 0 };
    try {
      const f = await (await this.file(path)).getFile();
      return { kind: 'file', size: f.size, mtime: f.lastModified };
    } catch (e) {
      if (e.name === 'NotAllowedError') throw e;
    }
    try {
      await this.dir(path);
      return { kind: 'dir', size: 0, mtime: 0 };
    } catch (e) {
      if (e.name === 'NotAllowedError') throw e;
      return null;
    }
  }

  async readBytes(path) {
    const f = await (await this.file(path)).getFile();
    return new Uint8Array(await f.arrayBuffer());
  }

  async* readChunks(path) {
    const f = await (await this.file(path)).getFile();
    const reader = f.stream().getReader();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) return;
      yield value;
    }
  }

  async writeBytes(path, bytes) {
    const w = await (await this.file(path, true)).createWritable();
    await w.write(bytes);
    await w.close();
  }

  async mkdir(path) {
    await this.dir(path, true);
  }

  async remove(path) {
    const i = path.lastIndexOf('/');
    const parent = await this.dir(i < 0 ? '' : path.slice(0, i));
    await parent.removeEntry(path.slice(i + 1));
  }
}

export const canPickFolders = () => typeof window !== 'undefined' && typeof window.showDirectoryPicker === 'function';

/** Ask the person to choose the notebook folder. Returns a handle, or null if they cancelled. */
export async function pickFolder() {
  try {
    return await window.showDirectoryPicker({ id: 'ai-eln-notebook', mode: 'readwrite' });
  } catch (e) {
    if (e.name === 'AbortError') return null;
    throw e;
  }
}

/** True once the browser lets this page read and write the folder. Must follow a click when it has to ask. */
export async function allowed(handle, ask = false) {
  const opts = { mode: 'readwrite' };
  if (typeof handle.queryPermission !== 'function') return true;
  if ((await handle.queryPermission(opts)) === 'granted') return true;
  return ask ? (await handle.requestPermission(opts)) === 'granted' : false;
}

/* The chosen folder is remembered in this browser (IndexedDB), so next time it is one click to reopen. */
const DB = 'ai-eln';
const KEY = 'notebook-folder';

function db() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore('handles');
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function withStore(mode, fn) {
  const d = await db();
  return new Promise((resolve, reject) => {
    const tx = d.transaction('handles', mode);
    const req = fn(tx.objectStore('handles'));
    tx.oncomplete = () => resolve(req ? req.result : undefined);
    tx.onerror = () => reject(tx.error);
  });
}

export const rememberFolder = (handle) => withStore('readwrite', (s) => s.put(handle, KEY)).catch(() => {});
export const recallFolder = () => withStore('readonly', (s) => s.get(KEY)).catch(() => null);
export const forgetFolder = () => withStore('readwrite', (s) => s.delete(KEY)).catch(() => {});
