from argon2 import PasswordHasher, exceptions
from pydantic import EmailStr
from sqlalchemy import select
from typing import Tuple
from uuid import UUID

from db.db import get_db_session
from model.models import User

class ExistingUserError(Exception):
    def __init__(self, field_taken):
        super().__init__()
        self.field_taken = field_taken
    def __str__(self):
        return f"Existing user with same {self.field_taken}"
class UserNotFoundError(Exception):
    pass
class PasswordsMismatchError(Exception):
    pass
class DatabaseError(Exception):
    pass

async def register(email: EmailStr, username: str, password: str, password_confirm: str) -> Tuple[str, UUID]:
    with get_db_session() as session:
        stmt = select(User).where(User.email == email)
        existing_user = session.scalar(stmt)
    if existing_user:
        raise ExistingUserError("email")
    with get_db_session() as session:
        stmt = select(User).where(User.username == username)
        existing_user = session.scalar(stmt)
    if existing_user:
        raise ExistingUserError("username")
    
    
    ph = PasswordHasher()
    hash = ph.hash(password)
    try:
        password_matches = ph.verify(hash, password_confirm)
    except exceptions.VerifyMismatchError:
        raise PasswordsMismatchError()
    except (exceptions.InvalidHashError, exceptions.VerificationError):
        pass

    if password_matches:
        try:
            with get_db_session() as session:
                user = User(
                    email=email,
                    username=username,
                    password=hash)
                session.add(user)
                session.commit()
                session.refresh(user)
                registered_id = user.user_id
        except Exception:
            raise DatabaseError()
    print(registered_id)
    return "", registered_id

async def login(email: EmailStr, password:str) -> Tuple[str, UUID]:
    
    with get_db_session() as session:
        stmt = select(User).where(User.email == email)
        existing_user: User = session.scalar(stmt)
    if not existing_user:
        raise UserNotFoundError()
    
    ph = PasswordHasher()
    try:
        password_matches = ph.verify(existing_user.password, password)
    except exceptions.VerifyMismatchError:
        raise PasswordsMismatchError()
    except (exceptions.InvalidHashError, exceptions.VerificationError):
        raise Exception()

    if password_matches:
        return "", existing_user.user_id