from fastapi import Request, Response, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional


import os
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Only true if the env var of APP_ENV is prod
COOKIE_SECURE = os.getenv("APP_ENV", "development") == "production"

def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=COOKIE_SECURE, # False ONLY for dev
        samesite="strict",  # SR-05: Strict blocks the cookie on cross-site requests (CSRF defence)
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )


def clear_auth_cookie(response: Response) -> None:
    # Browsers only drop a cookie if the delete matches the same path / flags it
    # was set with, so mirror set_auth_cookie's attributes here.
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",  # must mirror set_auth_cookie so the browser drops it
    )



class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> Optional[str]:
        token = request.cookies.get("access_token")


        if not token:
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "Not authenticated",
                headers = {"WWW-Authenticate" : "Bearer"}
            )
        
        else:
            return token




oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="/api/v1/auth/login")