/* The conventions as data: folder names, ID patterns, required fields. Mirrors the constants at the
   top of scripts/eln.py; docs/CONVENTIONS.md is the written version. */

export const SUBFOLDERS = ['1-notes', '2-data_raw', '3-code', '4-data_processed', '5-figures'];
/** Subfolders where a file name must start with the experiment ID. 2-data_raw is exempt. */
export const NAMED_SUBFOLDERS = ['1-notes', '3-code', '4-data_processed', '5-figures'];
export const EXEMPT_FILENAMES = new Set(['readme.md', 'thumbs.db', 'desktop.ini', '__pycache__']);
export const SKIP_NAMES = new Set(['.ds_store', 'thumbs.db', 'desktop.ini', '__pycache__']);

export const KINDS = ['experiment', 'protocol', 'sample', 'project'];
export const KIND_DIR = { experiment: 'Experiments', protocol: 'Protocols', sample: 'Samples', project: 'Projects' };
export const VAULT_DIRS = [...Object.values(KIND_DIR), 'Inventory'];
export const ID_FIELD = { experiment: 'experiment_id', protocol: 'protocol_id', sample: 'sample_id', project: 'project_id' };

export const SAMPLE_LETTERS = {
  p: 'plasmid', i: 'oligo', a: 'antibody', c: 'cell-line', m: 'mouse-line',
  t: 'peptide', r: 'protein-prep', s: 'slide', g: 'gel',
};
export const SAMPLE_TYPES = Object.fromEntries(Object.entries(SAMPLE_LETTERS).map(([k, v]) => [v, k]));

export const STATUS = {
  experiment: ['active', 'complete', 'paused', 'abandoned'],
  protocol: ['current', 'archived'],
  sample: ['active', 'depleted', 'retired'],
  project: ['active', 'complete', 'paused'],
};

const INITIALS = '[A-Z]{2,4}';
export const RE_INITIALS = new RegExp(`^${INITIALS}$`);
export const RE_EXP_ID = new RegExp(`^(${INITIALS})e(\\d{4})$`);
export const RE_SAMPLE_ID = new RegExp(`^(${INITIALS})([${Object.keys(SAMPLE_LETTERS).join('')}])(\\d{4})$`);
export const RE_PROTOCOL_ID = /^P_[A-Za-z0-9][A-Za-z0-9-]*$/;
export const RE_PROTOCOL_NAME = /^[A-Za-z0-9][A-Za-z0-9-]*$/;
export const RE_PROJECT_ID = /^[A-Za-z][A-Za-z0-9-]*$/;
export const RE_EXP_FOLDER = new RegExp(`^(${INITIALS}e\\d{4})(?:_([A-Za-z0-9-]+))?$`);
export const RE_KEY = /^[a-z][a-z0-9_]*$/;

export const ID_PATTERN = { experiment: RE_EXP_ID, protocol: RE_PROTOCOL_ID, sample: RE_SAMPLE_ID, project: RE_PROJECT_ID };

export const REQUIRED = {
  experiment: ['experiment_id', 'title', 'researcher', 'date_started', 'status'],
  protocol: ['protocol_id', 'title', 'version', 'status'],
  sample: ['sample_id', 'sample_type', 'title', 'date_created', 'status'],
  project: ['project_id', 'title', 'lead', 'status', 'date_started'],
};
/** Fields that produce a warning when present but empty. */
export const SHOULD = {
  experiment: ['project', 'protocols', 'raw_data_path'],
  protocol: [],
  sample: ['source', 'storage_location'],
  project: [],
};
export const DATE_FIELDS = {
  experiment: ['date_started', 'date_completed'],
  protocol: ['version'],
  sample: ['date_created'],
  project: ['date_started'],
};
/** field -> the kind of note it refers to */
export const REF_FIELDS = {
  experiment: { project: 'project', protocols: 'protocol', samples: 'sample', related_experiments: 'experiment' },
  protocol: { supersedes: 'protocol' },
  sample: {},
  project: {},
};
export const REQUIRED_SECTIONS = {
  experiment: ['Objective', 'Experimental design', 'Methods', 'Deviations from protocol',
    'Results', 'Interpretation', 'Decision', 'Follow-up experiments', 'Files'],
  protocol: ['Purpose', 'Materials', 'Procedure', 'Known failure modes / troubleshooting', 'Change log'],
  sample: ['Description', 'Provenance', 'Validation', 'Notes'],
  project: ['Aim / hypothesis', 'Current state', 'Experiments', 'Reagents in use', 'Figures', 'Related protocols'],
};
export const MEETING_TAG = 'meeting';

export const EXPERIMENT_TYPES = ['WesternBlot', 'Fractionation', 'IP', 'IF', 'qPCR', 'RNAseq', 'ChIPseq', 'MassSpec',
  'Cloning', 'CellCulture', 'MouseWork', 'Microscopy', 'Purification', 'Kinetics'];

/** A message meant for the person using the tool. `code` lets a caller react without parsing text. */
export class ElnError extends Error {
  constructor(message, code = 'error', data = undefined) {
    super(message);
    this.name = 'ElnError';
    this.code = code;
    this.data = data;
  }
}
