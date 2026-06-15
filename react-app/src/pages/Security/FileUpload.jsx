// Client-side image upload validation for the forums / discussion section.
export const MAX_UPLOAD_BYTES = 5 * 1024 * 1024; // 5 MB
export const MAX_FILENAME_LENGTH = 120;

//? Allow-list, not block-list. SVG is deliberately excluded
export const ALLOWED_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp'];
export const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];

//? File signatures ("magic bytes") check
//? Can delete the ones that we dont want to accept
const MAGIC_SIGNATURES = [
  { mime: 'image/jpeg', offset: 0, bytes: [0xff, 0xd8, 0xff] },
  { mime: 'image/png', offset: 0, bytes: [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a] },
  { mime: 'image/gif', offset: 0, bytes: [0x47, 0x49, 0x46, 0x38] }, // "GIF8"
  {
    mime: 'image/webp',
    offset: 0,
    bytes: [0x52, 0x49, 0x46, 0x46], // "RIFF"
    also: { offset: 8, bytes: [0x57, 0x45, 0x42, 0x50] }, // "WEBP" at byte 8
  },
];

const HEADER_BYTES_NEEDED = 12;


// --- Filename hygiene ---
// Strip directory components, control chars and anything outside a safe set so a
// crafted name can never traverse paths or inject markup. We never trust the
// client filename for storage anyway (the server should assign its own name),
// but a clean name is still nicer for display and logging.
export function sanitizeFilename(raw) {
  if (typeof raw !== 'string') return '';
  // Drop any path the browser/OS may have included, keep the last segment only.
  const base = raw.split(/[\\/]/).pop() || '';
  return base
    // eslint-disable-next-line no-control-regex
    .replace(/[\x00-\x1f\x7f]/g, '')      // control chars (incl. NUL)
    .replace(/[^a-zA-Z0-9._-]/g, '_')      // collapse anything exotic to underscore
    .replace(/^\.+/, '')                   // no leading dots -> no ".htaccess" / hidden files
    .slice(0, MAX_FILENAME_LENGTH)
    .trim();
}

// Lower-cased extension without the dot, or '' if there isn't a real one.
export function getExtension(filename) {
  const name = sanitizeFilename(filename);
  const dot = name.lastIndexOf('.');
  if (dot <= 0 || dot === name.length - 1) return '';
  return name.slice(dot + 1).toLowerCase();
}

// --- Individual checks (each returns true/false) ---
export function checkSize(file) {
  return file && file.size > 0 && file.size <= MAX_UPLOAD_BYTES;
}

export function checkExtension(filename) {
  return ALLOWED_EXTENSIONS.includes(getExtension(filename));
}

// The browser-declared Content-Type. Easily forged, so it's a *necessary* but
// not *sufficient* signal — magic bytes are the real arbiter.
export function checkContentType(file) {
  return !!file && ALLOWED_MIME_TYPES.includes(file.type);
}

// Read just the first chunk of the file as raw bytes.
function readHeaderBytes(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(new Uint8Array(reader.result));
    reader.onerror = () => reject(reader.error || new Error('Could not read file'));
    reader.readAsArrayBuffer(file.slice(0, HEADER_BYTES_NEEDED));
  });
}

function bytesMatch(buffer, offset, expected) {
  if (buffer.length < offset + expected.length) return false;
  return expected.every((b, i) => buffer[offset + i] === b);
}

// Inspect the actual file header and return the detected MIME, or null if it
// matches none of our allowed signatures (i.e. it is not really an image).
export async function detectMimeFromMagic(file) {
  const header = await readHeaderBytes(file);
  for (const sig of MAGIC_SIGNATURES) {
    if (!bytesMatch(header, sig.offset, sig.bytes)) continue;
    if (sig.also && !bytesMatch(header, sig.also.offset, sig.also.bytes)) continue;
    return sig.mime;
  }
  return null;
}


// --- The one call sites should use ---
// Runs every layer and returns a structured result. `errors` is empty when the
// file passes. `detectedType` is the magic-byte verdict so callers can show it.
//
//   const { valid, errors } = await validateImageUpload(file);
//   if (!valid) { setError(errors[0]); return; }
//
export async function validateImageUpload(file) {
  const errors = [];

  if (!file) {
    return { valid: false, errors: ['No file selected'], detectedType: null, safeName: '' };
  }

  const safeName = sanitizeFilename(file.name);

  if (!checkSize(file)) {
    errors.push(`File must be between 1 byte and ${Math.floor(MAX_UPLOAD_BYTES / (1024 * 1024))} MB`);
  }
  if (!checkExtension(file.name)) {
    errors.push(`Extension not allowed. Use: ${ALLOWED_EXTENSIONS.join(', ')}`);
  }
  if (!checkContentType(file)) {
    errors.push('Declared file type is not an allowed image type');
  }

  // Magic-byte sniffing is the strongest signal, so do it last and let it fail
  // loudly. It also cross-checks the declared type against the real bytes — a
  // mismatch means someone renamed/relabelled the file.
  let detectedType = null;
  try {
    detectedType = await detectMimeFromMagic(file);
    if (!detectedType) {
      errors.push('File content does not look like a supported image (failed signature check)');
    } else if (file.type && file.type !== detectedType) {
      errors.push(`Content-Type "${file.type}" does not match actual file content "${detectedType}"`);
    }
  } catch {
    errors.push('Could not read file contents to verify it');
  }

  return { valid: errors.length === 0, errors, detectedType, safeName };
}
