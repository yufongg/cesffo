# cesffo

A financial-literacy learning platform: a **React** single-page app talking to a
**FastAPI** backend backed by **PostgreSQL**, all orchestrated with Docker Compose.
This README is the on-ramp for collaborators — it covers how to run the stack, how
the security primitives in `react-app/src/pages/Security/` work, how to add
admin-only routes, how the frontend talks to the backend, and how file uploads are
locked down for the upcoming forums section.

> For Git workflow, testing, linting (ruff/bandit), and running GitHub Actions
> locally with `act`, see [`docs/development-guide.md`](docs/development-guide.md).

---

## 1. Running the app

```bash
docker compose up --build -d   # build images and start in the background
```

| Service        | URL                     | Notes                                  |
| -------------- | ----------------------- | -------------------------------------- |
| React frontend | http://localhost:3000   | Dev server, proxies API calls          |
| FastAPI backend| http://localhost:5000   | Swagger UI at `/docs`                  |
| PostgreSQL     | localhost:5432          | Dev only; internal-only in production  |

`docker-compose.override.yml` is loaded automatically in development (hot-reload
volumes, exposed debug ports). `docker-compose.yml` alone is the production shape
(read-only source, ports kept inside the mesh network).

Seed some demo data once the DB is up:

```bash
docker compose exec -T backend python seed.py
```

---

## 2. Architecture at a glance

```
react-app/                     backend/
  src/
    api/client.js   ───────►     main.py            (app, CORS, routers, lifespan)
    pages/                       user/
      Security/                    auth.py          (hashing, JWT, password policy)
        RoleCheck.jsx              auth_router.py   (/register /login /getProfile, deps)
        Sanitize.jsx               admin_router.py  (/api/v1/admin/* — admin only)
        FileUpload.jsx           course/
      Admin/                       course_router.py (/api/v1/courses)
      Marketplace.jsx            forum/             (forums + uploads — in progress)
    App.js  (routes)             model/models.py    (SQLAlchemy ORM)
```

**Golden rule:** the browser is never trusted. Every access-control and validation
check that matters is enforced **server-side**. The frontend mirrors those checks
only for UX (faster feedback, fewer round-trips). Bypassing the React layer must
never grant anything the backend wouldn't independently allow.

---

## 3. Talking to the backend from React (`api/client.js`)

All requests go through one thin wrapper, `apiFetch`, so auth headers and error
handling stay consistent. Never call `fetch()` directly from a page.

```js
import { apiFetch } from '../api/client';

// GET (default)
const profile = await apiFetch('/api/v1/auth/getProfile');

// POST / PATCH / DELETE with a JSON body
const updated = await apiFetch(`/api/v1/admin/users/${id}/role`, {
  method: 'PATCH',
  body: { role: 'instructor' },   // object — the wrapper JSON.stringifies it
});
```

What `apiFetch` does for you (`react-app/src/api/client.js`):

- Attaches `Authorization: Bearer <token>` from `localStorage` when present.
- Sets `Content-Type: application/json` and serialises the `body` object.
- Normalises FastAPI errors: it throws an `Error` whose `.message` is the API's
  `detail` (string or the first `422` validation message) and whose `.status` is
  the HTTP code — so callers can `try/catch` and show `e.message`.
- On `401`, clears the stored session automatically.

### The standard page pattern

```jsx
const [data, setData] = useState([]);
const [error, setError] = useState('');
const [loading, setLoading] = useState(true);

useEffect(() => {
  let active = true;                       // guard against setState after unmount
  apiFetch('/api/v1/courses?sort=name')
    .then((list) => { if (active) setData(list || []); })
    .catch((e) => { if (active) setError(e.message); })
    .finally(() => { if (active) setLoading(false); });
  return () => { active = false; };
}, []);
```

`AdminUsers` (`pages/Admin/Users.jsx`) and `Marketplace.jsx` are good, current
references for list/mutate flows.

---

## 4. Security primitives — `react-app/src/pages/Security/`

This folder holds the reusable, client-side security helpers. Three files today:

### `RoleCheck.jsx` — session + route gating

| Export                | Purpose                                                                 |
| --------------------- | ----------------------------------------------------------------------- |
| `RoleCheck`           | Top-level provider. Validates the session against the backend (which validates the JWT) and exposes the user via context. Wrap the app once in `App.js`. |
| `useAuth()`           | Hook to read the authenticated user inside any component.               |
| `ProtectedRoute`      | Route guard. Redirects unauthenticated users to `/`; with `adminOnly` it sends non-admins to `/NotFound`. |

`ProtectedRoute` gates the *UI* only (it reads `access_token` / `user_role` from
`localStorage`). It stops a normal user from *seeing* an admin screen, but it is
**not** the security boundary — a user can edit `localStorage`. The real boundary
is `require_admin` on the backend, which rejects the API calls that screen would
make. Always pair an admin route with admin-only endpoints.

### `Sanitize.jsx` — input filtering

`sanitizeSearch(raw)` caps length (`MAX_SEARCH_LENGTH = 80`), strips control
characters and `< >` angle brackets, and collapses whitespace. Use it on
free-text inputs **as the user types** and again before sending, as `Marketplace.jsx`
does:

```jsx
import { sanitizeSearch, MAX_SEARCH_LENGTH } from './Security/Sanitize';

<input
  value={search}
  maxLength={MAX_SEARCH_LENGTH}
  onChange={(e) => setSearch(sanitizeSearch(e.target.value))}
/>
```

> React already escapes any value rendered as JSX text, so this is defence-in-depth,
> not your only XSS guard. Keep avoiding `dangerouslySetInnerHTML`. The backend
> separately escapes SQL `LIKE` wildcards (`course_router._like_escape`) and uses
> parameterised queries — sanitising on the client never replaces that.

### `FileUpload.jsx` — image upload validation

New module for the forums. See §6.

---

## 5. Adding a secure, admin-only route

Two halves; do **both**. The frontend hides the page, the backend enforces access.

### a) Frontend route (`react-app/src/App.js`)

```jsx
import AdminReports from './pages/Admin/Reports';

<Route
  path="/admin/reports"
  element={
    <ProtectedRoute adminOnly={true}>
      <AdminReports />
    </ProtectedRoute>
  }
/>
```

Keep the catch-all `<Route path="*">` last — anything above it is a real route,
everything else falls through to `NotFound`.

### b) Backend endpoint (the actual gate)

Depend on `require_admin` (in `user/auth_router.py`). It chains off
`get_current_user`, which decodes/validates the JWT, then asserts the `admin` role —
returning `403` otherwise. Add new admin endpoints to `user/admin_router.py`
(prefix `/api/v1/admin`) or a new router that uses the same dependency:

```python
from fastapi import APIRouter, Depends
from .auth_router import require_admin

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])

@router.get("/reports")
async def list_reports(admin: dict = Depends(require_admin)):
    # `admin` is {"user_id": ..., "role": "admin"} — reaching here means the
    # caller proved a valid admin JWT. Non-admins never get this far.
    ...
```

Register any brand-new router in `main.py` with `app.include_router(...)`.

### c) Call it from the page

Because the admin's JWT is attached automatically, the page just uses `apiFetch`:

```jsx
const reports = await apiFetch('/api/v1/admin/reports');
```

**Server-side authz checklist for new admin features**

- Every endpoint uses `Depends(require_admin)` (or `get_current_user` for any
  logged-in user) — never rely on the route being "hidden".
- Validate path/body params with Pydantic models and explicit allow-lists
  (see `validate_role`, `ALLOWED_SORTS`).
- Don't leak existence in errors where it enables enumeration (login returns a
  generic "Incorrect email or password"; mirror that intent).
- Guard destructive/irreversible actions (e.g. "can't demote the last admin",
  "can't ban your own account") — see `admin_router.py` for the pattern.

---

## 6. Securing file uploads (forums / discussion images)

Uploads are the highest-risk feature here: a single mis-validated file can become
stored XSS, remote code execution (a `.php`/`.jsp` served from the upload dir), or
a storage-exhaustion DoS. We validate in **two layers** and trust only the second.

### Layer 1 — client (`react-app/src/pages/Security/FileUpload.jsx`)

UX guard for instant feedback. One call runs every check:

```jsx
import { validateImageUpload } from './Security/FileUpload';

async function onPick(e) {
  const file = e.target.files[0];
  const { valid, errors, detectedType, safeName } = await validateImageUpload(file);
  if (!valid) { setError(errors[0]); return; }
  // safe to queue/preview; send via FormData (see below)
}
```

It enforces, in order:

| Check                 | Function                | Defends against                              |
| --------------------- | ----------------------- | -------------------------------------------- |
| Size (1 byte–5 MB)    | `checkSize`             | storage abuse / cheap DoS                    |
| Extension allow-list  | `checkExtension`        | `image.php`, `image.svg`, double extensions  |
| Declared Content-Type | `checkContentType`      | obviously wrong MIME                          |
| **Magic bytes**       | `detectMimeFromMagic`   | a `.jpg` that is really HTML/SVG/an executable |
| Type cross-check      | inside `validateImageUpload` | renamed/relabelled files (declared ≠ actual) |
| Filename hygiene      | `sanitizeFilename`      | path traversal (`../`), NUL bytes, hidden files |

Allowed types: `jpg/jpeg, png, gif, webp`. **SVG is intentionally excluded** — it is
XML and can carry `<script>`, making it an inline-XSS vector. The knobs
(`MAX_UPLOAD_BYTES`, `ALLOWED_EXTENSIONS`, `ALLOWED_MIME_TYPES`) live at the top of
the file and must stay in lock-step with the backend.

Send the file as multipart (not JSON) so it isn't base64-bloated:

```jsx
const form = new FormData();
form.append('file', file, safeName);
await fetch('/api/v1/forum/upload', {
  method: 'POST',
  headers: { Authorization: `Bearer ${getToken()}` }, // no Content-Type — browser sets the boundary
  body: form,
});
```

### Layer 2 — server (the real gate; implement in `backend/forum/`)

The client checks are bypassable; the backend **must repeat all of them** before
writing anything. Recommended server-side policy:

- **Re-check size** with `UploadFile` + a hard byte cap (don't read unbounded).
- **Re-sniff magic bytes** server-side (Pillow `Image.open(...).verify()`, or
  `python-magic`). Reject anything that isn't a real raster image.
- **Ignore the client filename for storage.** Generate your own name —
  `f"{uuid4().hex}.{ext}"` where `ext` is derived from the *verified* type — so a
  crafted name can never traverse paths or set the extension.
- **Re-encode the image** (load with Pillow, save out fresh). This strips EXIF,
  embedded scripts, and polyglot tricks far more reliably than inspection alone.
- **Store outside the web root / served as static, never executable.** The
  upload dir must not be able to run code; serve with a fixed safe `Content-Type`
  and `Content-Disposition` where appropriate.
- **Require auth + rate-limit** the endpoint (`Depends(get_current_user)`), and
  scope ownership so users can only attach to their own posts.

The existing `backend/uploads/forum/` directory is the intended storage location;
keep it non-executable and consider serving uploads from a separate origin/CDN.

---

## 7. Other hardening worth doing in this iteration

Quick wins that fit the current codebase:

1. **Shorten JWT lifetime + add refresh.** Access tokens last 30 min
   (`ACCESS_TOKEN_EXPIRE_MINUTES`) and there's no revocation. Consider short
   access tokens + a refresh flow, and a server-side denylist for logout/ban so a
   banned user's existing token stops working immediately.
2. **Move the token off `localStorage` to an `HttpOnly`, `Secure`, `SameSite`
   cookie.** `localStorage` is readable by any XSS. An `HttpOnly` cookie isn't,
   though it then needs CSRF protection (SameSite + a CSRF token).
3. **Add security headers** (via middleware or the reverse proxy):
   `Content-Security-Policy` (biggest XSS lever), `X-Content-Type-Options: nosniff`,
   `X-Frame-Options: DENY`, `Referrer-Policy`, and HSTS in production.
4. **Tighten CORS for production.** `allow_origins` currently lists localhost; make
   it environment-driven so prod only allows the real origin.
5. **Rate-limit auth and upload endpoints** (e.g. slowapi). The login lockout
   counter (`MAX_AUTH_ATTEMPTS = 5`) helps per-account; add per-IP limits too.
6. **Server-side input length/shape caps everywhere**, mirroring the Pydantic
   `Field(max_length=...)` already used in the auth/admin schemas, especially for
   forum post bodies (`Post.content` is unbounded `String` today).
7. **Sanitise/limit rich text in forum posts** before render. Keep avoiding
   `dangerouslySetInnerHTML`; if Markdown is rendered (`marked-react` is a
   dependency), disable raw HTML so user posts can't inject markup.
8. **Centralise structured logging + audit trails** for admin actions (role
   changes, bans, password resets) — `main.py` already has `# TODO: configure Logger`.
9. **Keep the secret management discipline.** `JWT_SECRET_KEY` is required in
   production and never falls back to a hard-coded value (see `auth.py`) — make
   sure DB credentials and any future API keys follow the same env-only pattern.
10. **Run the quality gates before pushing** — `ruff`, `bandit`, `pytest`, and the
    frontend tests, as documented in the development guide.
