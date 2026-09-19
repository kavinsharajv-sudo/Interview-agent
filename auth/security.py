# auth/security.py
import os
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv

from auth.models import TokenData, User, UserInDB

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────
SECRET_KEY     = os.getenv("JWT_SECRET_KEY")
ALGORITHM      = os.getenv("JWT_ALGORITHM",       "HS256")
EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# ── OAuth2 scheme ──────────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ── Password hashing — using bcrypt directly ──────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── Fake user database ─────────────────────────────────────────────────────
USERS_DB = {
    "senior_hr": UserInDB(
        username        = "senior_hr",
        role            = "senior_hr",
        hashed_password = hash_password("senior123"),
    ),
    "junior_hr": UserInDB(
        username        = "junior_hr",
        role            = "junior_hr",
        hashed_password = hash_password("junior123"),
    ),
    "admin": UserInDB(
        username        = "admin",
        role            = "admin",
        hashed_password = hash_password("admin123"),
    ),
}


# ── Core functions ─────────────────────────────────────────────────────────

def get_user(username: str) -> Optional[UserInDB]:
    return USERS_DB.get(username)


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict) -> str:
    payload = data.copy()
    expiry  = datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES)
    payload.update({"exp": expiry})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ── Dependencies ───────────────────────────────────────────────────────────

def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail      = "Invalid or expired token",
        headers     = {"WWW-Authenticate": "Bearer"},
    )

    try:
        payload  = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role     = payload.get("role")

        if username is None:
            raise credentials_exception

        token_data = TokenData(username=username, role=role)

    except JWTError:
        raise credentials_exception

    user = get_user(token_data.username)
    if user is None:
        raise credentials_exception

    return User(username=user.username, role=user.role)


def require_senior_hr(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("senior_hr", "admin"):
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Only Senior HR can perform this action"
        )
    return current_user


def require_any_hr(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("junior_hr", "senior_hr", "admin"):
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "HR access required"
        )
    return current_user
