/* lab.yaml: who the notebook belongs to and how its pages and printouts look.
   Layering, later wins: neutral defaults < the tool's lab.yaml (docs/lab.yaml) < lab.yaml in the
   notebook folder. A key that is present wins even when it is empty. Same rules as load_lab in
   scripts/eln.py. */

import { LAB_YAML } from './builtin_lab.js';
import { parseHeaderLines } from './frontmatter.js';
import { splitlines, decodeText, strip } from './text.js';
import { isFile } from '../store/base.js';

export const LAB_DEFAULTS = {
  lab_name: 'Lab', institution: '', department: '', lab_url: '',
  product_name: 'Plain-text lab notebook', record_name: 'research record',
  repository_url: '', site_url: '', logo: '',
  color_primary: '#155e75', color_primary_bright: '#0e7490', color_wash: '#ecf7f9',
  color_accent: '#c2410c', color_accent_dark: '#9a3412',
  font_body: 'Inter', font_heading: 'IBM Plex Serif', font_mono: 'IBM Plex Mono', font_stylesheet: '',
  print_signatures: 'yes',
};
const RE_COLOR = /^(#[0-9A-Fa-f]{3,8}|[A-Za-z]{3,20})$/;

/** Defaults with each text applied in order. Colours that are not colours fall back to the default. */
export function parseLab(...texts) {
  const lab = { ...LAB_DEFAULTS };
  for (const text of texts) {
    if (typeof text !== 'string') continue;
    for (const [key, value] of Object.entries(parseHeaderLines(splitlines(text)).fields)) {
      lab[key] = Array.isArray(value) ? value.join(', ') : value;
    }
  }
  for (const key of Object.keys(lab)) {
    if (key.startsWith('color_') && !RE_COLOR.test(lab[key])) lab[key] = LAB_DEFAULTS[key] || '#155e75';
  }
  return lab;
}

/** The lab settings for a notebook. baseText is the tool's own lab.yaml when the caller has it
    (the page fetches it, Node reads it); the built-in copy is used otherwise. */
export async function loadLab(store, baseText = null) {
  const texts = [typeof baseText === 'string' ? baseText : LAB_YAML];
  if (store && await isFile(store, 'lab.yaml')) {
    try {
      texts.push(decodeText(await store.readBytes('lab.yaml'), true));
    } catch (e) { /* not UTF-8: ignore the file, as Python does */ }
  }
  return parseLab(...texts);
}

/** 'Shechter Lab, Department of Biochemistry, Albert Einstein College of Medicine' */
export const labLine = (lab) => [lab.lab_name, lab.department, lab.institution].filter(Boolean).join(', ');
/** 'Shechter Lab research record' */
export const recordTitle = (lab) => strip(`${lab.lab_name} ${lab.record_name}`);
export const wantsSignatures = (lab) => !['no', 'false', '0', 'off', ''].includes(strip(lab.print_signatures).toLowerCase());
