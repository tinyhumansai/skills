/**
 * mime polyfill for V8 runtime.
 * gramjs uses mime for determining file types.
 */

const mimeTypes = {
  // Images
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  png: 'image/png',
  gif: 'image/gif',
  webp: 'image/webp',
  svg: 'image/svg+xml',
  ico: 'image/x-icon',
  bmp: 'image/bmp',
  tiff: 'image/tiff',
  tif: 'image/tiff',

  // Video
  mp4: 'video/mp4',
  webm: 'video/webm',
  ogv: 'video/ogg',
  avi: 'video/x-msvideo',
  mov: 'video/quicktime',
  mkv: 'video/x-matroska',
  flv: 'video/x-flv',
  wmv: 'video/x-ms-wmv',

  // Audio
  mp3: 'audio/mpeg',
  wav: 'audio/wav',
  ogg: 'audio/ogg',
  flac: 'audio/flac',
  aac: 'audio/aac',
  m4a: 'audio/mp4',
  wma: 'audio/x-ms-wma',

  // Documents
  pdf: 'application/pdf',
  doc: 'application/msword',
  docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  xls: 'application/vnd.ms-excel',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  ppt: 'application/vnd.ms-powerpoint',
  pptx: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',

  // Text
  txt: 'text/plain',
  html: 'text/html',
  htm: 'text/html',
  css: 'text/css',
  js: 'text/javascript',
  json: 'application/json',
  xml: 'application/xml',
  csv: 'text/csv',
  md: 'text/markdown',

  // Archives
  zip: 'application/zip',
  rar: 'application/vnd.rar',
  '7z': 'application/x-7z-compressed',
  tar: 'application/x-tar',
  gz: 'application/gzip',

  // Other
  exe: 'application/x-msdownload',
  apk: 'application/vnd.android.package-archive',
  dmg: 'application/x-apple-diskimage',
};

// Reverse mapping for getExtension
const extensions = {};
for (const [ext, mime] of Object.entries(mimeTypes)) {
  if (!extensions[mime]) {
    extensions[mime] = ext;
  }
}

export function getType(path) {
  if (!path) return null;
  const ext = String(path).split('.').pop()?.toLowerCase();
  return mimeTypes[ext] || 'application/octet-stream';
}

export function getExtension(mimeType) {
  if (!mimeType) return null;
  // Handle mimeType with charset
  const base = mimeType.split(';')[0].trim().toLowerCase();
  return extensions[base] || null;
}

export function lookup(path) {
  return getType(path);
}

export function extension(mimeType) {
  return getExtension(mimeType);
}

export default { getType, getExtension, lookup, extension };
