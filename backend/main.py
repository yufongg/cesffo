from fastapi import FastAPI, Request, status #, HTTPException, Body, Form, Depends,
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import HTMLResponse , JSONResponse #, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware


# import json
# import os
# import re
# import requests
import uvicorn
from sqlalchemy import text

from db.db import engine, Base, get_db_session
import model.models  # Must import models to register them on the metadata space
from user.auth_router import router as auth_router
from user.admin_router import router as admin_router
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
app.mount("/static", StaticFiles(directory="./static"), name="static")


# Configure Jinja2 templates for rendering HTML
templates = Jinja2Templates(directory="./templates")


app.include_router(auth_router)
app.include_router(admin_router)

# Forum endpoints
@app.get("/forum", response_class=HTMLResponse)
async def getForumHome(request: Request):
    """
    Renders a minified version of the app to test
    """
    return templates.TemplateResponse("test.html", {"request": request})



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


@app.get("/test", response_class=HTMLResponse)
async def test(request: Request):
    """
    Renders a minified version of the app to test
    """
    return templates.TemplateResponse("test.html", {"request": request})



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000)