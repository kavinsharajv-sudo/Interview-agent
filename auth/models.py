# auth/models.py
from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    """What login returns to the browser."""
    access_token: str
    token_type:   str = "bearer"


class TokenData(BaseModel):
    """What we extract from inside the JWT."""
    username: Optional[str] = None
    role:     Optional[str] = None


class User(BaseModel):
    """User object passed around inside the app."""
    username: str
    role:     str


class UserInDB(User):
    """User as stored in database — includes hashed password."""
    hashed_password: str
