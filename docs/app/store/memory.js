/* A notebook held in memory. Used by the tests and by the app's "try it without saving" mode. */

export class MemoryStore {
  constructor(label = 'practice notebook (not saved)') {
    this.label = label;
    this.files = new Map(); // path -> { bytes, mtime }
    this.dirs = new Set(['']);
    this.clock = () => Date.now();
  }

  async list(dir) {
    if (!this.dirs.has(dir)) return null;
    const prefix = dir ? dir + '/' : '';
    const seen = new Map();
    for (const d of this.dirs) {
      if (d && d.startsWith(prefix) && !d.slice(prefix.length).includes('/')) seen.set(d.slice(prefix.length), 'dir');
    }
    for (const f of this.files.keys()) {
      if (f.startsWith(prefix) && !f.slice(prefix.length).includes('/')) seen.set(f.slice(prefix.length), 'file');
    }
    return [...seen].map(([name, kind]) => ({ name, kind }));
  }

  async stat(path) {
    if (this.dirs.has(path)) return { kind: 'dir', size: 0, mtime: 0 };
    const f = this.files.get(path);
    return f ? { kind: 'file', size: f.bytes.length, mtime: f.mtime } : null;
  }

  async readBytes(path) {
    const f = this.files.get(path);
    if (!f) throw new Error(`no such file: ${path}`);
    return f.bytes;
  }

  async writeBytes(path, bytes) {
    const i = path.lastIndexOf('/');
    if (i > 0) await this.mkdir(path.slice(0, i));
    this.files.set(path, { bytes: bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes), mtime: this.clock() });
  }

  async mkdir(path) {
    const parts = path.split('/').filter(Boolean);
    for (let i = 1; i <= parts.length; i++) this.dirs.add(parts.slice(0, i).join('/'));
  }

  async remove(path) {
    this.files.delete(path);
  }

  async rmdir(path) {
    const prefix = path + '/';
    if ([...this.files.keys(), ...this.dirs].some((p) => p.startsWith(prefix))) throw new Error(`folder is not empty: ${path}`);
    this.dirs.delete(path);
  }

  async move(from, to) {
    const f = this.files.get(from);
    if (!f) throw new Error(`no such file: ${from}`);
    const i = to.lastIndexOf('/');
    if (i > 0) await this.mkdir(to.slice(0, i));
    this.files.set(to, f);
    this.files.delete(from);
  }
}
