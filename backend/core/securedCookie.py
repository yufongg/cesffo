import os
from typing import Optional

from fastapi import Request, Response, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# Single source of truth for the access-token lifetime (auth.py imports this) so the
# JWT `exp` and the cookie `max_age` can never drift apart.
ACCESS_TOKEN_EXPIRE_MINUTES = 30

#$ Send the cookie over HTTPS only in production; stays off in dev so localhost works.
COOKIE_SECURE = os.getenv("APP_ENV", "development") == "production"


def set_auth_cookie(response: Response, token: str) -> None:
    #* Drop the JWT into an httpOnly cookie so client-side JS can never read it.
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        #! SR-05: SameSite=Strict stops the browser sending this on cross-site requests (CSRF defence).
        samesite="strict",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )


def clear_auth_cookie(response: Response) -> None:
    #! A browser only deletes a cookie when the delete matches the exact path/flags it was set with.
    #^ So every attribute here must mirror set_auth_cookie, or logout silently leaves the cookie in place.
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="strict",
    )


class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    #* Read the bearer token from our httpOnly cookie instead of the Authorization header.
    async def __call__(self, request: Request) -> Optional[str]:
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return token


oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="/api/v1/auth/login")
