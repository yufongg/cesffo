from fastapi import FastAPI, Request, status #, HTTPException, Body, Form, Depends,
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import HTMLResponse , JSONResponse #, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
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
        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS xp INTEGER NOT NULL DEFAULT 0',
        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS level INTEGER NOT NULL DEFAULT 1',
        'ALTER TABLE course ADD COLUMN IF NOT EXISTS xp_reward INTEGER NOT NULL DEFAULT 0',
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
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)



# --- Mount Static Files ---
# This tells FastAPI to serve files from the "static" directory
# under the URL path "/static".
# The `name="static"` argument is crucial as it creates the named route
# that Jinja2's `url_for` (or similar) will look for.




app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(course_router)


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