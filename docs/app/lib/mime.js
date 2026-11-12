/* File name -> media type, for the types a lab folder usually holds. Anything else is
   application/octet-stream (in .eln archives) or "not an image" (in snapshots). */

const TYPES = {
  md: 'text/markdown', markdown: 'text/markdown', txt: 'text/plain', csv: 'text/csv', tsv: 'text/tab-separated-values',
  html: 'text/html', htm: 'text/html', css: 'text/css', xml: 'text/xml', json: 'application/json',
  py: 'text/x-python', sh: 'application/x-sh', pdf: 'application/pdf', zip: 'application/zip', tar: 'application/x-tar',
  rtf: 'application/rtf', eps: 'application/postscript', ps: 'application/postscript', ai: 'application/postscript',
  png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', jpe: 'image/jpeg', gif: 'image/gif', svg: 'image/svg+xml',
  tif: 'image/tiff', tiff: 'image/tiff', bmp: 'image/bmp', ico: 'image/vnd.microsoft.icon', webp: 'image/webp',
  doc: 'application/msword', xls: 'application/vnd.ms-excel', ppt: 'application/vnd.ms-powerpoint',
  docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  mp4: 'video/mp4', mov: 'video/quicktime', avi: 'video/x-msvideo', mp3: 'audio/mpeg', wav: 'audio/x-wav',
  h5: 'application/x-hdf5', hdf: 'application/x-hdf', nc: 'application/x-netcdf',
};

/** Images a snapshot embeds. The same table as IMAGE_TYPES in scripts/eln.py. */
export const IMAGE_TYPES = {
  png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg', jpe: 'image/jpeg', gif: 'image/gif', svg: 'image/svg+xml',
  webp: 'image/webp', bmp: 'image/bmp', ico: 'image/vnd.microsoft.icon', tif: 'image/tiff', tiff: 'image/tiff', avif: 'image/avif',
};

export function imageType(name) {
  const i = name.lastIndexOf('.');
  return i <= 0 ? null : IMAGE_TYPES[name.slice(i + 1).toLowerCase()] || null;
}

/** The media type for a file name, or null when it is not a known type. */
export function guessMime(name) {
  const i = name.lastIndexOf('.');
  if (i <= 0) return null;
  return TYPES[name.slice(i + 1).toLowerCase()] || null;
}
