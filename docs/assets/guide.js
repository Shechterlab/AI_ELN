/* guide.html: show one of the Markdown guides in this folder as a page.
   The guides stay plain .md files (the same ones GitHub shows); this fetches one and renders it with
   marked (assets/marked.min.js, MIT). Nothing is generated or copied, so the page cannot drift from the file. */
import { labReady } from './brand.js';

(function () {
  var REPO = 'https://github.com/Shechterlab/AI_ELN'; // replaced by repository_url from lab.yaml
  var BRANCH = 'main';
  var PRODUCT = 'Plain-text lab notebook';

  /* id = file name without .md. Order here is the order in the side menu. */
  var DOCS = [
    { id: 'getting-started', title: 'Getting started', group: 'Start here' },
    { id: 'CHEATSHEET', title: 'Cheat sheet (print me)', group: 'Start here' },
    { id: 'CONVENTIONS', title: 'Names, folders, labels', group: 'The rules' },
    { id: 'SOP', title: 'Lab data SOP', group: 'The rules' },
    { id: 'ai-agents', title: 'Using AI with it', group: 'AI' },
    { id: 'ai-briefing', title: 'Briefing to paste into ChatGPT', group: 'AI' },
    { id: 'design-notes', title: 'Why it is built this way', group: 'Background' },
    { id: 'AI_ELN_overview_and_spec', title: 'Overview and specification', group: 'Background' }
  ];
  var byId = {};
  DOCS.forEach(function (d) { byId[d.id] = d; });

  function $(sel) { return document.querySelector(sel); }

  function current() {
    var m = /[?&]d=([A-Za-z0-9_-]+)/.exec(location.search);
    return m && byId[m[1]] ? m[1] : DOCS[0].id;
  }

  function menu(active) {
    var nav = $('#guide-nav'), html = '', group = '';
    DOCS.forEach(function (d) {
      if (d.group !== group) { group = d.group; html += '<h2>' + group + '</h2>'; }
      html += '<a href="guide.html?d=' + d.id + '"' + (d.id === active ? ' aria-current="page"' : '') + '>' + d.title + '</a>';
    });
    nav.innerHTML = html;
    document.querySelectorAll('.site-nav a').forEach(function (a) {
      if (a.getAttribute('href') === 'guide.html?d=' + active) a.setAttribute('aria-current', 'page');
    });
  }

  /* GitHub-style heading anchors, so #links written for GitHub keep working here */
  function anchorFor(text, seen) {
    var a = text.trim().toLowerCase().replace(/[^\w\- ]+/g, '').replace(/ /g, '-');
    var n = seen[a] || 0;
    seen[a] = n + 1;
    return n ? a + '-' + n : a;
  }

  function fixLinks(root) {
    root.querySelectorAll('a[href]').forEach(function (a) {
      var href = a.getAttribute('href');
      if (/^(https?:|mailto:|#)/.test(href)) {
        if (/^https?:/.test(href)) { a.target = '_blank'; a.rel = 'noopener'; }
        return;
      }
      var m = /^([A-Za-z0-9_-]+)\.md(#.*)?$/.exec(href);
      if (m && byId[m[1]]) { a.setAttribute('href', 'guide.html?d=' + m[1] + (m[2] || '')); return; }
      /* anything else is a file in the repository that this site does not serve: send it to GitHub */
      var path = href.replace(/^(\.\.\/)+/, '').replace(/^\.\//, '');
      if (href.indexOf('../') !== 0) path = 'docs/' + path;
      a.setAttribute('href', REPO + '/blob/' + BRANCH + '/' + path);
      a.target = '_blank'; a.rel = 'noopener';
    });
  }

  function mermaid(root) {
    var blocks = root.querySelectorAll('pre > code.language-mermaid');
    if (!blocks.length) return;
    blocks.forEach(function (code) {
      var div = document.createElement('div');
      div.className = 'mermaid';
      div.textContent = code.textContent;
      code.parentNode.replaceWith(div);
    });
    var s = document.createElement('script');
    s.src = 'https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js';
    s.onload = function () {
      try {
        var dark = getComputedStyle(document.documentElement).colorScheme.indexOf('dark') === 0;
        window.mermaid.initialize({ startOnLoad: false, theme: dark ? 'dark' : 'neutral' });
        window.mermaid.run({ querySelector: '.mermaid' });
      } catch (e) { /* the diagram stays as text */ }
    };
    document.head.appendChild(s);
  }

  function show(id) {
    var doc = byId[id], out = $('#doc');
    document.body.setAttribute('data-doc', id);
    menu(id);
    $('#doc-source').href = REPO + '/blob/' + BRANCH + '/docs/' + id + '.md';
    fetch(id + '.md', { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error(r.status);
      return r.text();
    }).then(function (md) {
      out.innerHTML = window.marked.parse(md, { gfm: true });
      var seen = {};
      out.querySelectorAll('h1, h2, h3, h4').forEach(function (h) { if (!h.id) h.id = anchorFor(h.textContent, seen); });
      fixLinks(out);
      mermaid(out);
      var h1 = out.querySelector('h1');
      document.title = (h1 ? h1.textContent : doc.title) + ' · ' + PRODUCT;
      if (location.hash) {
        var target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
        if (target) target.scrollIntoView();
      }
    }).catch(function () {
      out.innerHTML = '<p class="doc-error">This guide could not be loaded here. ' +
        '<a href="' + REPO + '/blob/' + BRANCH + '/docs/' + id + '.md">Read it on GitHub</a> instead.</p>';
    });
  }

  var p = $('#doc-print');
  if (p) p.addEventListener('click', function () { window.print(); });
  labReady.then(function (r) {
    if (r.lab.repository_url) REPO = r.lab.repository_url;
    PRODUCT = r.lab.product_name || PRODUCT;
    show(current());
  });
})();
