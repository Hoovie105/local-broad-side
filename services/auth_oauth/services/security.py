"""
Auth/services/security.py

JWT issuance + validation.
Password hashing + verification.
No expiry on tokens for MVP — add timeout logic here later.
"""
from datetime import datetime
from typing import Optional

import jwt
from passlib.context import CryptContext

from services.auth_oauth.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ------------------------------------------------------------------ #
# Passwords                                                            #
# ------------------------------------------------------------------ #

def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain[:72], hashed)


# ------------------------------------------------------------------ #
# JWT                                                                   #
# ------------------------------------------------------------------ #

def create_token(user_id: str) -> str:
    """
    Issues a token with no expiry for MVP.
    To add timeout later: include 'exp' in the payload here.
    """
    payload = {
        "sub": user_id,
        "iat": datetime.utcnow(),
        # "exp": datetime.utcnow() + timedelta(days=30)  # uncomment to add expiry
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[str]:
    """
    Returns user_id if valid, None if invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": False},  # no expiry check for MVP
        )
        return payload.get("sub")
    except jwt.PyJWTError:
        return None