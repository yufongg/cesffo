export function formatDate(value) {
  if (!value) return '';

  const normalizedValue =
    value.endsWith('Z') || value.includes('+')
      ? value
      : `${value}Z`;

  const date = new Date(normalizedValue);

  return date.toLocaleString('en-SG', {
    timeZone: 'Asia/Singapore',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  });
}

export function insertAroundSelection(textarea, before, after = '') {
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const selected = textarea.value.substring(start, end) || 'text';
  const nextValue = textarea.value.substring(0, start) + before + selected + after + textarea.value.substring(end);
  const nextCursor = start + before.length + selected.length + after.length;
  return { nextValue, nextCursor };
}
