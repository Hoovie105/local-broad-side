"""
Auth/routers/users.py

POST /auth/register  — create a new Boardside account
POST /auth/login     — returns a JWT on valid credentials
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from services.auth_oauth.database import get_db
from services.auth_oauth.models import User
from services.auth_oauth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from services.auth_oauth.services.security import create_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, db: Annotated[Session, Depends(get_db)]):
    existing = db.query(User).filter_by(email=payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    user = User(
        id=str(uuid.uuid4()),
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()

    return UserResponse(id=user.id, email=user.email)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    user = db.query(User).filter_by(email=payload.email).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    return TokenResponse(access_token=create_token(user.id))


@router.post("/logout", status_code=200)
def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Blacklists the token so it can't be reused.
    Client should also delete the token from local storage.
    """
    from Auth.models import TokenBlacklist
    token = credentials.credentials
    db.merge(TokenBlacklist(token=token))
    db.commit()
    return {"message": "Logged out successfully."}