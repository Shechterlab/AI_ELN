/* Applies docs/lab.yaml to a page: the lab's name, links, logo, colours, and fonts.
   To use this site for another lab, edit lab.yaml and replace the logo. No page needs editing.

   In the HTML:
     data-lab="lab_name"                       the element's text becomes that value
     data-lab="{product_name} · {lab_name}"    or a pattern with several values
     data-lab-href="lab_url"                   the link's address becomes that value
     data-lab-src="logo"                       the image's address (relative to docs/)
     <link data-lab-fonts>                     the font stylesheet
   Links to this lab's repository and site are rewritten to the ones in lab.yaml. */

import { parseLab } from '../app/lib/lab.js';
import { LAB_YAML } from '../app/lib/builtin_lab.js';

const ORIGINAL = parseLab(LAB_YAML); // what the pages say before lab.yaml is applied

const stack = (name, rest) => (name ? `'${name.replace(/['\\<>]/g, '')}', ${rest}` : rest);

export function brandCss(lab) {
  const light = `--teal-wash:${lab.color_wash};--accent:${lab.color_accent};--accent-dark:${lab.color_accent_dark};--brand-ink:${lab.color_primary};`;
  return `:root{--teal:${lab.color_primary};--teal-600:${lab.color_primary_bright};`
    + `--font-body:${stack(lab.font_body, "system-ui,-apple-system,'Segoe UI',sans-serif")};`
    + `--font-display:${stack(lab.font_heading, "Georgia,'Times New Roman',serif")};`
    + `--font-mono:${stack(lab.font_mono, "ui-monospace,'SFMono-Regular',Menlo,Consolas,monospace")};}`
    + `:root[data-theme="light"]{${light}}`
    + `@media (prefers-color-scheme: light){:root:not([data-theme="dark"]){${light}}}`;
}

const fill = (pattern, lab) => (pattern.includes('{') ? pattern.replace(/\{([a-z_]+)\}/g, (_, k) => lab[k] ?? '') : lab[pattern] ?? '');

export function applyLab(settings, root = document) {
  /* affiliation: ', Department, Institution', for a sentence that starts with the lab's name */
  const lab = { ...settings, affiliation: [settings.department, settings.institution].filter(Boolean).map((x) => ', ' + x).join('') };
  let style = document.getElementById('lab-style');
  if (!style) {
    style = document.createElement('style');
    style.id = 'lab-style';
    document.head.appendChild(style);
  }
  style.textContent = brandCss(lab);
  for (const el of root.querySelectorAll('[data-lab]')) el.textContent = fill(el.getAttribute('data-lab'), lab);
  for (const el of root.querySelectorAll('[data-lab-href]')) {
    const href = lab[el.getAttribute('data-lab-href')];
    if (href) el.setAttribute('href', href);
    else el.removeAttribute('href');
  }
  for (const el of root.querySelectorAll('[data-lab-src]')) {
    const src = lab[el.getAttribute('data-lab-src')];
    if (src) el.setAttribute('src', new URL('../' + src, import.meta.url).href);
  }
  for (const el of root.querySelectorAll('link[data-lab-fonts]')) {
    if (lab.font_stylesheet) el.setAttribute('href', lab.font_stylesheet);
    else el.remove();
  }
  for (const [from, to] of [[ORIGINAL.repository_url, lab.repository_url], [ORIGINAL.site_url, lab.site_url]]) {
    if (!from || !to || from === to) continue;
    for (const a of root.querySelectorAll(`a[href^="${from}"]`)) a.setAttribute('href', to + a.getAttribute('href').slice(from.length));
  }
  try {
    localStorage.setItem('ai-eln-lab-css', style.textContent);
    localStorage.setItem('ai-eln-lab-name', lab.lab_name);
  } catch (e) { /* private mode */ }
  document.documentElement.classList.remove('lab-pending');
}

async function load() {
  let text = null;
  try {
    const res = await fetch(new URL('../lab.yaml', import.meta.url), { cache: 'no-cache' });
    if (res.ok) text = (await res.text()).replace(/\r\n?/g, '\n');
  } catch (e) { /* offline or opened from a file: the built-in copy is used */ }
  const lab = parseLab(text === null ? LAB_YAML : text);
  applyLab(lab);
  return { lab, text: text === null ? LAB_YAML : text };
}

/** Resolves to { lab, text } once the page has been branded. */
export const labReady = load();
