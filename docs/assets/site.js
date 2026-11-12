/* Small behaviours for the site: theme button, the "try it" naming box, Mac/Windows tabs. No dependencies. */
(function () {
  'use strict';
  var $ = function (sel, el) { return (el || document).querySelector(sel); };

  /* theme: follows the system until the button is used, then remembers the choice */
  function theme() {
    var btn = $('#theme-btn');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var cur = document.documentElement.getAttribute('data-theme') ||
        (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      var next = cur === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('ai-eln-theme', next); } catch (e) { /* private mode */ }
    });
  }

  /* "try it": type initials and a title, see exactly what New experiment would create */
  function tryIt() {
    var N = window.ElnNames, form = $('#try-form');
    if (!N || !form) return;
    var ini = $('#try-initials'), title = $('#try-title'), num = $('#try-number');
    var outId = $('#try-id'), outTree = $('#try-tree'), hint = $('#try-initials-hint'), foot = $('#try-foot');
    function esc(s) { return String(s).replace(/[&<>]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]; }); }
    function render() {
      var initials = N.cleanInitials(ini.value);
      if (!initials) {
        hint.textContent = 'Initials are 2 to 4 letters, like JSR.';
        hint.className = 'hint bad';
        initials = 'JSR';
      } else {
        hint.textContent = 'IDs start with your initials, so two people cannot get the same ID.';
        hint.className = 'hint';
      }
      var id = N.experimentId(initials, num.value);
      var folder = N.folderName(id, title.value);
      var d = N.yyyymmdd();
      outId.innerHTML = esc(id) + '<small>experiment ID</small>';
      outTree.innerHTML =
        'Experiments/\n' +
        '\u2514\u2500 <span class="h">' + esc(folder) + '</span>/\n' +
        '   \u251C\u2500 1-notes/           <span class="k">' + esc(id) + '.md</span>  <span class="c">the note</span>\n' +
        '   \u251C\u2500 2-data_raw/        <span class="c">instrument files, unedited</span>\n' +
        '   \u251C\u2500 3-code/            <span class="k">' + esc(id) + '_analysis.R</span>\n' +
        '   \u251C\u2500 4-data_processed/  <span class="k">' + esc(id) + '_quantification.csv</span>\n' +
        '   \u2514\u2500 5-figures/         <span class="k">' + esc(id) + '_R_summary_' + d + '.png</span>  <span class="c">result figure</span>';
      foot.innerHTML = 'A search for <code>' + esc(id) + '</code> finds all of these files. ' +
        'A search for <code>' + esc(id) + '_R</code> finds the result figures.';
    }
    [ini, title, num].forEach(function (el) { el.addEventListener('input', render); });
    form.addEventListener('submit', function (e) { e.preventDefault(); });
    render();
  }

  /* Mac / Windows tabs in "Start" */
  function tabs() {
    var buttons = document.querySelectorAll('[data-os]');
    if (!buttons.length) return;
    function show(os) {
      buttons.forEach(function (b) { b.setAttribute('aria-selected', b.getAttribute('data-os') === os ? 'true' : 'false'); });
      document.querySelectorAll('[data-os-panel]').forEach(function (p) { p.hidden = p.getAttribute('data-os-panel') !== os; });
    }
    buttons.forEach(function (b) { b.addEventListener('click', function () { show(b.getAttribute('data-os')); }); });
    show(/Win/i.test(navigator.platform || navigator.userAgent || '') ? 'windows' : 'mac');
  }

  document.addEventListener('DOMContentLoaded', function () { theme(); tryIt(); tabs(); });
})();
