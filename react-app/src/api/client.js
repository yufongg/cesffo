// Thin fetch wrapper that attaches the JWT and normalizes errors.
// Note: the token lives in localStorage for simplicity. The REAL access control
// is server-side (require_admin on every admin endpoint); this header is just
// how we present the caller's identity.

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
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
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
