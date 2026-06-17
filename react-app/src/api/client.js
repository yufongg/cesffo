
export function getToken() {
  return localStorage.getItem('access_token');
}

export function clearSession() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_role');
  localStorage.removeItem('user_id');
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
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

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

// Build a same-origin WebSocket URL carrying the JWT as a query param. Browsers
// cannot set Authorization headers on a WebSocket, so the backend authenticates
// the token from the query string before accepting the connection.
export function wsUrl(path) {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const token = getToken();
  const query = token ? `?token=${encodeURIComponent(token)}` : '';
  return `${proto}://${window.location.host}${path}${query}`;
}
