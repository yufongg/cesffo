from fastapi import FastAPI, Request, status #, HTTPException, Body, Form, Depends,
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import JSONResponse #, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from core.rate_limit import limiter

import uvicorn
from sqlalchemy import text

from db.db import engine, Base, get_db_session
import model.models  


#! IMPORT YOUR ROUTERS HERE

from user.auth_router import router as auth_router
from user.admin_router import router as admin_router
from course.course_router import router as course_router
from course.instructor_router import router as instructor_router
from course.learn_router import router as learn_router
from forum.forum_router import router as forum_router
from pathlib import Path
# Generates all tables defined via 'Base' if they don't already exist in Postgres

cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://react_frontend",
]


def ensure_schema():
    #! I added this incase to prevent model mismatch, this will only run on my branch.
    migrations = [
        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE',
        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS force_password_reset BOOLEAN NOT NULL DEFAULT FALSE',
        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS lockout_timestamp TIMESTAMPTZ',
        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS xp INTEGER NOT NULL DEFAULT 0',
        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS level INTEGER NOT NULL DEFAULT 1',
        'ALTER TABLE course ADD COLUMN IF NOT EXISTS xp_reward INTEGER NOT NULL DEFAULT 0',
        # Forum: column added to the pre-existing post table by the merged
        # discussion-forum feature (new forum tables are made by create_all()).
        'ALTER TABLE post ADD COLUMN IF NOT EXISTS is_edited BOOLEAN NOT NULL DEFAULT FALSE',
    ]
    with engine.begin() as conn:
        for statement in migrations:
            conn.execute(text(statement))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database
    model.models
    Base.metadata.create_all(bind=engine)
    ensure_schema()  # bring existing tables up to date with the current models
    yield
    # Clean up
    # close_database_connection()

app = FastAPI(lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# Security headers applied to everything FastAPI serves (API JSON + the
# user-uploaded files under /uploads). The React SPA is served by a separate
# frontend service, so its document-level CSP / X-Frame-Options must be set
# there (see README / reverse-proxy config); these headers harden the backend
# surface — especially the uploaded-content directory.
_DOCS_PATHS = {"/docs", "/redoc", "/openapi.json"}


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Stop browsers MIME-sniffing a response (notably user uploads) into
    # something executable.
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Anti-clickjacking: nothing the API serves should ever be framed.
    response.headers["X-Frame-Options"] = "DENY"
    # Don't leak full URLs (which can carry ids) via the Referer header.
    response.headers["Referrer-Policy"] = "no-referrer"
    # Pin HTTPS for a year once the site is seen over TLS. Browsers ignore this
    # on plain-HTTP responses, so it is safe to send in local development too.
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    path = request.url.path
    if path.startswith("/uploads"):
        # User-uploaded content: deny everything. Even a file that somehow
        # slipped past the image validation cannot run script, fetch resources,
        # or be framed when accessed directly.
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; img-src 'self'; frame-ancestors 'none'; "
            "base-uri 'none'; form-action 'none'; sandbox"
        )
    elif path not in _DOCS_PATHS:
        # API responses are JSON, never a rendered document — lock the CSP all
        # the way down. (Swagger/ReDoc are skipped so the docs keep loading.)
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
        )

    return response


# Serve uploaded forum attachments. Files are stored under server-generated
# UUID names with extensions derived from validated image magic bytes, so the
# directory only ever contains real, allow-listed images.
UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")





app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(course_router)
app.include_router(instructor_router)
app.include_router(learn_router)
app.include_router(forum_router)



# --- 
@app.get("/healthcheck", tags=["Health"]) 
async def healthcheck():
    try: 
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "healthy", "database": "connected"}
        )
    except Exception: # as e: 
        # TODO: configure Logger and log exception
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy"}
        )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000)