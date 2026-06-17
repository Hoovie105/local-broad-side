from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from services.auth_oauth.database import get_db
from services.auth_oauth.models import User, TokenBlacklist
from services.auth_oauth.services.security import decode_token

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    token = credentials.credentials

    # Check blacklist first
    if db.query(TokenBlacklist).filter_by(token=token).first():
        raise HTTPException(status_code=401, detail="Token has been invalidated. Please log in again.")

    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    user = db.query(User).filter_by(id=user_id, is_active=True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")

    return user