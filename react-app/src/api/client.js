// The JWT now lives in an httpOnly cookie that the browser attaches
// automatically (see `credentials: 'include'` below); JavaScript cannot read
// it. We keep only non-sensitive role/id *hints* in localStorage so the SPA can
// render the right nav and route guards without a round-trip — the backend
// re-verifies the cookie on every request, so these are never trusted for auth.

export function getRole() {
  return localStorage.getItem('user_role');
}

export function isAuthenticated() {
  return Boolean(localStorage.getItem('user_role'));
}

// Persist the non-sensitive UI hints the SPA uses to render nav/route guards.
// The real session is the httpOnly cookie the backend set on the same response.
export function setSession({ user_role, user_id }) {
  localStorage.setItem('user_role', user_role);
  localStorage.setItem('user_id', user_id);
}

export function clearSession() {
  localStorage.removeItem('user_role');
  localStorage.removeItem('user_id');
}

// Tell the backend to clear the httpOnly cookie (JS can't), then drop the local
// hints. Always clears local state even if the network call fails.
export async function logout() {
  try {
    await apiFetch('/api/v1/auth/logout', { method: 'POST' });
  } catch {
    /* ignore — still clear local UI state below */
  }
  clearSession();
}

// FastAPI's `detail` is either a string (HTTPException) or an array (422).
function messageFromDetail(data, fallback) {
  if (!data || data.detail == null) return fallback;
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.detail) && data.detail.length) {
    return data.detail[0].msg || fallback;
  }
  return fallback;
}

export async function apiFetch(path, { method = 'GET', body } = {}) {
  const headers = {};

  // FormData (file uploads): let the browser set the multipart Content-Type +
  // boundary itself. Everything else is sent as JSON.
  let payload;
  if (body instanceof FormData) {
    payload = body;
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  const res = await fetch(path, {
    method,
    headers,
    body: payload,
    credentials: 'include', // send the httpOnly auth cookie
  });

  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty / non-JSON body */
  }

  if (!res.ok) {
    if (res.status === 401) clearSession();
    const error = new Error(messageFromDetail(data, `Request failed (${res.status})`));
    error.status = res.status;
    throw error;
  }

  return data;
}

// Build a same-origin WebSocket URL. The auth cookie is sent automatically on
// the handshake (same origin), so no token is placed in the URL.
export function wsUrl(path) {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";

  if (process.env.NODE_ENV === "development") {
    return `${proto}://${window.location.hostname}:5000${path}`;
  }

  return `${proto}://${window.location.host}${path}`;
}