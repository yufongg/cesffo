from fastapi import FastAPI, status, Request #, HTTPException, Body, Form, Depends,
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import JSONResponse #, RedirectResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
    """Idempotently add columns that create_all() cannot add to existing tables.

    Base.metadata.create_all() only creates *missing tables* — it never ALTERs a
    table that already exists in the persisted Postgres volume. So when a new
    column is added to a model, queries fail with 'column ... does not exist'.
    These ADD COLUMN IF NOT EXISTS statements are safe to run on every startup
    (idempotent, no data loss) and keep the live schema in sync with the models.

    NOTE: this is a lightweight stand-in. For production use Alembic migrations.
    """
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


# Defence-in-depth: stop browsers MIME-sniffing responses (notably the
# user-uploaded forum images served from /uploads) into something executable.
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
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