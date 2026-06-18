import React, { useMemo } from 'react';

// Renders server-stored rich text WITHOUT dangerouslySetInnerHTML.
//
// The HTML is parsed into an inert, detached document and rebuilt as real React
// elements, keeping only an allow-list of tags/attributes that mirrors the
// backend nh3 sanitizer (backend/common/sanitize.py). Content is already
// sanitized server-side at write time; doing it again here means:
//   1. the app never injects raw HTML into the live DOM, and
//   2. there is a second, independent sanitization layer (defence in depth) —
//      if the server allow-list were ever bypassed, nothing extra renders.

const ALLOWED_TAGS = new Set([
  'p', 'br', 'strong', 'em', 'u', 's', 'ul', 'ol', 'li',
  'h1', 'h2', 'h3', 'h4', 'blockquote', 'code', 'pre', 'a',
]);

// Elements that take no children.
const VOID_TAGS = new Set(['br']);

// Tags that are dropped together with their contents (rather than unwrapped),
// so a script/style body can never even surface as visible text.
const DROP_CONTENT_TAGS = new Set([
  'script', 'style', 'title', 'textarea', 'noscript', 'iframe', 'head',
]);

// Per-tag attribute allow-list. Everything else — style, class, and crucially
// any on* event handler — is dropped.
const ALLOWED_ATTRS = { a: ['href', 'title'] };

// Allow http(s)/mailto absolute URLs and same-origin relative paths or anchors.
// Reject protocol-relative ("//host") URLs and every explicit scheme we didn't
// allow (javascript:, data:, vbscript:, …).
export function isSafeHref(value) {
  if (typeof value !== 'string') return false;
  const v = value.trim();
  if (!v) return false;
  if (/^(https?:|mailto:)/i.test(v)) return true;
  if (v.startsWith('//')) return false;
  if (/^[a-z][a-z0-9+.-]*:/i.test(v)) return false; // any other explicit scheme
  return true; // relative path or #anchor
}

function pickSafeAttrs(node, tag, props) {
  for (const name of ALLOWED_ATTRS[tag] || []) {
    const raw = node.getAttribute(name);
    if (raw == null) continue;
    if (name === 'href') {
      if (isSafeHref(raw)) props.href = raw;
    } else {
      props[name] = raw;
    }
  }
}

// --- React-element renderer (used by <SafeHtml/>) ---------------------------
function nodeToReact(node, key) {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent;
  if (node.nodeType !== Node.ELEMENT_NODE) return null; // comments / others

  const tag = node.tagName.toLowerCase();
  if (DROP_CONTENT_TAGS.has(tag)) return null;

  const children = Array.from(node.childNodes)
    .map((child, i) => nodeToReact(child, i))
    .filter((c) => c !== null && c !== undefined && c !== '');

  // Disallowed wrapper: drop the tag, keep its (sanitized) children — matches
  // how nh3 unwraps unknown elements server-side.
  if (!ALLOWED_TAGS.has(tag)) {
    return <React.Fragment key={key}>{children}</React.Fragment>;
  }

  const props = { key };
  pickSafeAttrs(node, tag, props);

  if (tag === 'a') {
    // A link with no safe href becomes plain text rather than a dead/unsafe link.
    if (!props.href) return <React.Fragment key={key}>{children}</React.Fragment>;
    props.rel = 'noopener noreferrer nofollow';
    props.target = '_blank';
  }

  if (VOID_TAGS.has(tag)) return React.createElement(tag, props);
  return React.createElement(tag, props, children.length ? children : undefined);
}

function parseToReact(html) {
  if (!html || typeof html !== 'string') return null;
  // DOMParser builds a detached document: scripts never execute and no network
  // requests fire, so even hostile markup is inert while we walk it.
  const doc = new DOMParser().parseFromString(html, 'text/html');
  return Array.from(doc.body.childNodes)
    .map((node, i) => nodeToReact(node, i))
    .filter((c) => c !== null && c !== undefined && c !== '');
}

// --- HTML-string sanitizer (for the one contentEditable surface) -----------
function nodeToCleanDom(node, doc) {
  if (node.nodeType === Node.TEXT_NODE) return doc.createTextNode(node.textContent);
  if (node.nodeType !== Node.ELEMENT_NODE) return null;

  const tag = node.tagName.toLowerCase();
  if (DROP_CONTENT_TAGS.has(tag)) return null;

  const kids = Array.from(node.childNodes)
    .map((c) => nodeToCleanDom(c, doc))
    .filter(Boolean);

  const unwrap = () => {
    const frag = doc.createDocumentFragment();
    kids.forEach((k) => frag.appendChild(k));
    return frag;
  };

  if (!ALLOWED_TAGS.has(tag)) return unwrap();

  const el = doc.createElement(tag);
  const props = {};
  pickSafeAttrs(node, tag, props);
  Object.entries(props).forEach(([k, v]) => el.setAttribute(k, v));

  if (tag === 'a') {
    if (!el.getAttribute('href')) return unwrap();
    el.setAttribute('rel', 'noopener noreferrer nofollow');
    el.setAttribute('target', '_blank');
  }

  kids.forEach((k) => el.appendChild(k));
  return el;
}

// Returns a sanitized HTML *string* using the same allow-list. Only for the
// contentEditable composer, which must assign innerHTML directly.
export function sanitizeHtml(html) {
  if (!html || typeof html !== 'string') return '';
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const out = doc.createElement('div');
  Array.from(doc.body.childNodes).forEach((node) => {
    const cleaned = nodeToCleanDom(node, doc);
    if (cleaned) out.appendChild(cleaned);
  });
  return out.innerHTML;
}

// Drop-in replacement for `<div dangerouslySetInnerHTML={{ __html }} />`.
// Extra props (className, etc.) pass through to the wrapper element.
export default function SafeHtml({ html, as: Tag = 'div', ...rest }) {
  const tree = useMemo(() => parseToReact(html), [html]);
  return <Tag {...rest}>{tree}</Tag>;
}
