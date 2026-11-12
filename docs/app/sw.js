/* Keeps the notebook page usable without a connection: the page's own files are saved in the browser
   the first time it is opened, refreshed whenever the network is there, and served from that copy when
   it is not. Only this site's files are handled; the notebook folder is never touched from here. */

const CACHE = 'ai-eln-1';
/* every file the page loads; tests/test_site.py checks this list against docs/app/ */
const FILES = [
  "./",
  "app.css",
  "ui.js",
  "manifest.webmanifest",
  "../assets/site.css",
  "../assets/shechterlab-icon.svg",
  "lib/builtin_templates.js",
  "lib/closeout.js",
  "lib/conventions.js",
  "lib/create.js",
  "lib/elnfile.js",
  "lib/frontmatter.js",
  "lib/inventory.js",
  "lib/markdown.js",
  "lib/mime.js",
  "lib/names.js",
  "lib/query.js",
  "lib/schema.js",
  "lib/sha256.js",
  "lib/templates.js",
  "lib/text.js",
  "lib/tools.js",
  "lib/validate.js",
  "lib/vault.js",
  "lib/zip.js",
  "store/base.js",
  "store/fsaccess.js",
  "store/memory.js"
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== self.location.origin) return;
  event.respondWith(
    fetch(req).then((res) => {
      if (res.ok) {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
      }
      return res;
    }).catch(() => caches.match(req, { ignoreSearch: true }).then((hit) => hit || Response.error())),
  );
});
