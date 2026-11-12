/* The .eln archive: RO-Crate 1.1 in a ZIP, per TheELNConsortium/TheELNFileFormat.
   eLabFTW, RSpace, Kadi4Mat, PASTA, SampleDB, OpenSemanticLab, and SciLog import it. */

import { splitFrontMatter } from './frontmatter.js';
import { relatedNotes } from './query.js';
import { folderFiles } from './closeout.js';
import { mdToHtml } from './markdown.js';
import { sha256Hex } from './sha256.js';
import { guessMime } from './mime.js';
import { zipStore } from './zip.js';
import { isoDate, strip, words, basename, dirname, utf8 } from './text.js';

export const ELN_MEDIA_TYPE = 'application/vnd.eln+zip';

function personNode(name) {
  const parts = words(name || '');
  const given = parts.length > 1 ? parts.slice(0, -1).join(' ') : '';
  const family = parts.length > 1 ? parts[parts.length - 1] : parts[0] || 'unknown';
  const slug = strip(name || 'unknown').replace(/[^A-Za-z0-9]+/g, '-').replace(/^-+|-+$/g, '').toLowerCase() || 'unknown';
  return { '@id': `#person-${slug}`, '@type': 'Person', name: strip(name || 'unknown'), givenName: given, familyName: family };
}

export const elnRootName = (name, stamp) => (name || `ai-eln-export-${stamp}`).replace(/[^A-Za-z0-9._-]+/g, '-').replace(/^-+|-+$/g, '') || 'eln-export';

/** -> { bytes, metadata, files }. The archive holds the chosen experiments (whole folders) and, when
    `related` is set, the notes of the protocols, samples, and projects they refer to.
    rootName should match the archive's file name without .eln, as the specification prefers. */
export async function buildEln(store, vault, experiments, {
  related = true, today = isoDate(), rootName = '',
  publisher = 'Shechter Lab research record (AI_ELN)', publisherUrl = 'https://github.com/Shechterlab/AI_ELN',
} = {}) {
  const root = elnRootName(rootName, today.replaceAll('-', ''));
  const notes = [...experiments, ...(related ? relatedNotes(vault, experiments) : [])];
  const persons = new Map();
  const graph = [];
  const parts = [];
  const entries = [];
  for (const n of notes) {
    const dsDir = `./${n.kind}s/${n.id}/`;
    let files;
    let noteRel;
    if (n.kind === 'experiment' && n.folder !== null) {
      files = (await folderFiles(store, n.folder)).map((p) => [p, p.slice(n.folder.length + 1)]);
      noteRel = n.path.slice(n.folder.length + 1);
    } else {
      files = [[n.path, basename(n.path)]];
      noteRel = basename(n.path);
    }
    const fileNodes = [];
    let latest = '';
    for (const [path, rel] of files) {
      const bytes = await store.readBytes(path);
      entries.push({ name: `${root}/${n.kind}s/${n.id}/${rel}`, bytes });
      const mtime = isoDate(new Date((await store.stat(path)).mtime));
      if (mtime > latest) latest = mtime;
      fileNodes.push({
        '@id': dsDir + rel, '@type': 'File', name: basename(path),
        encodingFormat: guessMime(basename(path)) || 'application/octet-stream',
        contentSize: String(bytes.length), sha256: sha256Hex(bytes), dateModified: mtime,
      });
    }
    const person = personNode(n.get('researcher') || n.get('lead') || 'unknown');
    if (!persons.has(person['@id'])) persons.set(person['@id'], person);
    const keywords = [n.kind, ...n.getList('tags'), ...n.getList('experiment_type'), ...n.getList('project')];
    const dataset = {
      '@id': dsDir, '@type': 'Dataset',
      name: strip(`${n.id} ${n.get('title')}`), identifier: n.id,
      author: { '@id': person['@id'] },
      dateCreated: n.get('date_started') || n.get('date_created') || n.get('version') || latest,
      dateModified: n.get('date_completed') || latest,
      keywords: keywords.filter(Boolean).join(', '),
      text: mdToHtml(splitFrontMatter(n.text).body, { imgBase: dirname(noteRel), linkIds: false, imgSrc: (rel) => rel }),
      hasPart: fileNodes.map((f) => ({ '@id': f['@id'] })),
    };
    if (n.get('status')) dataset.creativeWorkStatus = n.get('status');
    graph.push(dataset, ...fileNodes);
    parts.push({ '@id': dsDir });
  }
  const metadata = {
    '@context': 'https://w3id.org/ro/crate/1.1/context',
    '@graph': [
      {
        '@id': 'ro-crate-metadata.json', '@type': 'CreativeWork', about: { '@id': './' },
        conformsTo: { '@id': 'https://w3id.org/ro/crate/1.1' }, dateCreated: today,
        sdPublisher: { '@id': '#publisher' }, version: '1.0',
      },
      { '@id': './', '@type': 'Dataset', name: publisher, datePublished: today, hasPart: parts },
      { '@id': '#publisher', '@type': 'Organization', name: publisher, url: publisherUrl },
      ...graph, ...persons.values(),
    ],
  };
  entries.push({ name: `${root}/ro-crate-metadata.json`, bytes: utf8(JSON.stringify(metadata, null, 2)) });
  return { bytes: zipStore(entries), metadata, files: entries.length };
}
