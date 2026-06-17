"""
Auth/routers/youtube_oauth.py

GET /auth/youtube           → redirect to Google consent screen
GET /auth/youtube/callback  → exchange code, store connection
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from services.auth_oauth.config import settings
from services.auth_oauth.database import get_db
from services.auth_oauth.models import PlatformConnection, User, TokenBlacklist
from services.auth_oauth.services.google_oauth import (
    GoogleOAuthError,
    build_authorization_url,
    exchange_code_for_tokens,
    get_youtube_channel_id,
)
from services.auth_oauth.services.security import decode_token
from services.auth_oauth.services.token_encryption import encrypt_token

router = APIRouter(prefix="/auth", tags=["YouTube OAuth"])


@router.get("/youtube")
def connect_youtube(
    db: Annotated[Session, Depends(get_db)],
    token: str = Query(...),
):
    if db.query(TokenBlacklist).filter_by(token=token).first():
        raise HTTPException(status_code=401, detail="Token invalidated.")

    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token.")

    user = db.query(User).filter_by(id=user_id, is_active=True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")

    url = build_authorization_url(state=user.id)
    return RedirectResponse(url)


@router.get("/youtube/callback")
async def youtube_callback(
    db: Annotated[Session, Depends(get_db)],
    code: str = Query(None),
    state: str = Query(...),
    error: str = Query(None),
):
    if error:
        return RedirectResponse(
            f"{settings.FRONTEND_ERROR_URL}?error=youtube_denied"
        )

    user = db.query(User).filter_by(id=state).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid state parameter.")

    try:
        tokens = await exchange_code_for_tokens(code)
        access_token = tokens["access_token"]
        channel_id = await get_youtube_channel_id(access_token)
    except GoogleOAuthError as exc:
        return RedirectResponse(
            f"{settings.FRONTEND_ERROR_URL}?error={exc}"
        )

    # Upsert
    existing = db.query(PlatformConnection).filter_by(
        user_id=user.id, platform="youtube"
    ).first()

    if existing:
        existing.access_token = encrypt_token(access_token)
        existing.platform_user_id = channel_id
        existing.is_active = True
    else:
        connection = PlatformConnection(
            id=str(uuid.uuid4()),
            user_id=user.id,
            platform="youtube",
            access_token=encrypt_token(access_token),
            platform_user_id=channel_id,
        )
        db.add(connection)

    db.commit()

    return RedirectResponse(
        f"{settings.FRONTEND_SUCCESS_URL}?connected=youtube"
    )