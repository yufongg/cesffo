from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from .auth import register, login, ExistingUserError, UserNotFoundError, PasswordsMismatchError
from model.response_model import ResponseModel

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


# Request Schema
class UserRegistrationSchema(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=10, description="Min length 10, mixed case")
    password_confirm: str

class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str

class AuthResponseSchema(ResponseModel):
    access_token: str
    user_id: str
    token_type: str = "bearer"

# --- Endpoints ---
@router.post("/register", response_model=AuthResponseSchema, status_code=status.HTTP_201_CREATED)
async def register_user(request: UserRegistrationSchema):
    try:
        access_token, user_id = await register(request.email, request.username, request.password, request.password_confirm)
    except PasswordsMismatchError:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    except ExistingUserError as e:
        raise HTTPException(status_code=409, detail=f"There is an existing user with the same {e.field_taken}") # username/email taken
    
    return AuthResponseSchema(access_token=access_token, user_id=user_id.hex)

@router.post("/login", response_model=AuthResponseSchema)
async def login_user(request: UserLoginSchema):
    try:
        access_token, user_id = await login(request.email, request.password)
    except (UserNotFoundError, PasswordsMismatchError):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return AuthResponseSchema(access_token=access_token, user_id=user_id.hex)

