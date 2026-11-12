/* The naming rules, in JavaScript, for the "try it" box on the site.
   They mirror scripts/eln.py (slugify, the ID patterns); tests/test_site.py checks that the two agree.
   Works in a browser (window.ElnNames) and in Node (require). */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) { module.exports = factory(); } else { root.ElnNames = factory(); }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  var SUBFOLDERS = ['1-notes', '2-data_raw', '3-code', '4-data_processed', '5-figures'];

  /* 'SNRPB retention: KCl' -> 'SNRPB-retention-KCl'. Case kept; cut on a word boundary at maxLen. */
  function slugify(text, maxLen) {
    maxLen = maxLen || 60;
    var slug = String(text || '').replace(/[^A-Za-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
    if (slug.length > maxLen) {
      var cut = slug.slice(0, maxLen + 1);
      slug = cut.indexOf('-') >= 0 ? cut.slice(0, cut.lastIndexOf('-')) : slug.slice(0, maxLen);
    }
    return slug.replace(/^-+|-+$/g, '');
  }

  /* Initials are 2-4 letters. Returns the cleaned initials, or '' if they are not valid. */
  function cleanInitials(text) {
    var s = String(text || '').trim().toUpperCase();
    return /^[A-Z]{2,4}$/.test(s) ? s : '';
  }

  function pad4(n) {
    n = Math.max(1, Math.min(9999, parseInt(n, 10) || 1));
    return ('000' + n).slice(-4);
  }

  function experimentId(initials, n) { return initials + 'e' + pad4(n); }

  function folderName(id, title) {
    var slug = slugify(title);
    return slug ? id + '_' + slug : id;
  }

  function yyyymmdd(d) {
    d = d || new Date();
    return '' + d.getFullYear() + ('0' + (d.getMonth() + 1)).slice(-2) + ('0' + d.getDate()).slice(-2);
  }

  return { SUBFOLDERS: SUBFOLDERS, slugify: slugify, cleanInitials: cleanInitials, pad4: pad4,
           experimentId: experimentId, folderName: folderName, yyyymmdd: yyyymmdd };
});
