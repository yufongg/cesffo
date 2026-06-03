from fastapi import FastAPI, Request, status #, HTTPException, Body, Form, Depends, 
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import HTMLResponse , JSONResponse #, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
# from fastapi.middleware.cors import CORSMiddleware


# import json
# import os
# import re
# import requests
import uvicorn
from sqlalchemy import text

from db.db import engine, Base, get_db_session
import model.models  # Must import models to register them on the metadata space
from user.auth_router import router as auth_router
# Generates all tables defined via 'Base' if they don't already exist in Postgres

# cors_origins = [
#     "http://localhost:3000",
#     "localhost:3000","http://127.0.0.1:3000",
#     "172.23.0.4",
#     "http://react_frontend"
# ]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database
    model.models
    Base.metadata.create_all(bind=engine)
    yield
    # Clean up
    # close_database_connection()

app = FastAPI(lifespan=lifespan)



# --- Mount Static Files ---
# This tells FastAPI to serve files from the "static" directory
# under the URL path "/static".
# The `name="static"` argument is crucial as it creates the named route
# that Jinja2's `url_for` (or similar) will look for.
app.mount("/static", StaticFiles(directory="./static"), name="static")


# Configure Jinja2 templates for rendering HTML
templates = Jinja2Templates(directory="./templates")


app.include_router(auth_router)

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
            conetent={"status": "unhealthy",}
        )


@app.get("/test", response_class=HTMLResponse)
async def test(request: Request):
    """
    Renders a minified version of the app to test
    """
    return templates.TemplateResponse("test.html", {"request": request})

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000)