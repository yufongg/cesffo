// I cap length and strip bracket characters
export const MAX_SEARCH_LENGTH = 80;

//! Block Control characters and bracket
const CONTROL_CHARS = /[\x00-\x1F\x7F]/g;
const ANGLE_BRACKETS = /[<>]/g;


// Sanitizes user input like special characters
export function sanitizeSearch(raw) {
  if (typeof raw !== 'string') return '';
  return raw
    .replace(CONTROL_CHARS, '')
    .replace(ANGLE_BRACKETS, '')
    .replace(/\s+/g, ' ')
    .trimStart()
    .slice(0, MAX_SEARCH_LENGTH);
}
